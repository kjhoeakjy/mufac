"""학습·검증·예측. LightGBM 이진 모델 2개(상한가·하한가) + 워크포워드 OOS 검증 + 등온 보정."""
from __future__ import annotations

import json
import time
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from stock.common import DATA
from stock.features import feature_cols

warnings.filterwarnings("ignore", category=UserWarning)

PARAMS = dict(
    objective="binary", learning_rate=0.03, num_leaves=63, min_data_in_leaf=200,
    feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0,
    max_bin=255, verbose=-1, num_threads=0, seed=7,
)
ROUNDS = 600
TRAIN_START = "20200101"
NEG_KEEP = 0.25  # 음성 다운샘플 비율(가중치로 보정)


def _xy(df: pd.DataFrame, target: str, cols: list[str], sample: bool):
    m = df[target] >= 0
    d = df.loc[m]
    y = d[target].to_numpy()
    w = np.ones(len(d), dtype="float32")
    if sample:
        rng = np.random.default_rng(0)
        keep = (y == 1) | (rng.random(len(d)) < NEG_KEEP)
        d, y = d.loc[keep], y[keep]
        w = np.where(y == 1, 1.0, 1.0 / NEG_KEEP).astype("float32")
    # 최근 가중(5년 전 0.5 → 지금 1.0)
    age = (pd.to_datetime(d["date"].max(), format="%Y%m%d") - pd.to_datetime(d["date"], format="%Y%m%d")).dt.days.to_numpy()
    w = w * (1.0 - 0.5 * np.clip(age / 1825.0, 0, 1)).astype("float32")
    return d[cols].to_numpy("float32"), y, w, d


def train_one(df, target, cols, rounds=ROUNDS, params=PARAMS):
    X, y, w, _ = _xy(df, target, cols, sample=True)
    ds = lgb.Dataset(X, y, weight=w, feature_name=cols, free_raw_data=True)
    return lgb.train(params, ds, num_boost_round=rounds)


def precision_at_k(d: pd.DataFrame, score: str, target: str, k: int) -> tuple[float, float]:
    """날짜별 상위 k의 적중률 평균, 하루 평균 적중 수."""
    hits, n = [], []
    for _, g in d.groupby("date"):
        top = g.nlargest(k, score)
        hits.append(top[target].sum())
        n.append(len(top))
    hits, n = np.array(hits), np.array(n)
    return float(hits.sum() / max(1, n.sum())), float(hits.mean())


def walk_forward(df: pd.DataFrame, target: str, cols: list[str], months: int = 12,
                 rounds: int = ROUNDS) -> pd.DataFrame:
    """월 단위 워크포워드: 각 달은 그 이전 데이터로만 학습한 모델로 예측."""
    df = df[df[target] >= 0]
    ym = df["date"].str[:6]
    test_months = sorted(ym.unique())[-months:]
    outs = []
    for m in test_months:
        tr = df[(ym < m) & (df["date"] >= TRAIN_START)]
        te = df[ym == m]
        if len(te) == 0 or tr[target].sum() < 50:
            continue
        # 엠바고: 테스트 달 첫날 직전 1거래일은 라벨이 테스트 기간과 겹치므로 제외
        last_tr_date = tr["date"].max()
        tr = tr[tr["date"] < last_tr_date]
        t0 = time.time()
        mdl = train_one(tr, target, cols, rounds)
        p = mdl.predict(te[cols].to_numpy("float32"))
        o = te[["code", "date", "next_date", target, "close"]].copy()
        o["p"] = p.astype("float32")
        outs.append(o)
        print(f"[wf {target}] {m} train={len(tr)} pos={int(tr[target].sum())} test={len(te)} "
              f"pos={int(te[target].sum())} ap={average_precision_score(te[target], p):.4f} {time.time()-t0:.0f}s", flush=True)
    return pd.concat(outs, ignore_index=True)


def summarize(oos: pd.DataFrame, target: str) -> dict:
    y, p = oos[target].to_numpy(), oos["p"].to_numpy()
    base = float(y.mean())
    res = {"n": int(len(y)), "pos": int(y.sum()), "base_rate": base,
           "ap": float(average_precision_score(y, p)), "auc": float(roc_auc_score(y, p)),
           "days": int(oos["date"].nunique())}
    for k in (3, 5, 10, 20):
        pr, cnt = precision_at_k(oos, "p", target, k)
        res[f"p@{k}"] = pr
        res[f"hits@{k}"] = cnt
    # 확률 구간별 실제 적중률(신뢰도 표기용)
    bins = [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.01]
    cut = pd.cut(p, bins, right=False)
    tab = pd.DataFrame({"y": y, "b": cut}).groupby("b", observed=True)["y"].agg(["mean", "size"])
    res["buckets"] = [{"lo": float(i.left), "hi": float(i.right), "rate": float(r["mean"]), "n": int(r["size"])}
                      for i, r in tab.iterrows()]
    # 최근 월별 p@10
    oos = oos.assign(ym=oos["date"].str[:6])
    res["monthly"] = [{"ym": m, "p@10": precision_at_k(g, "p", target, 10)[0], "pos": int(g[target].sum()),
                       "days": int(g["date"].nunique())} for m, g in oos.groupby("ym")]
    return res


def fit_calibrator(oos: pd.DataFrame, target: str) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(oos["p"].to_numpy(), oos[target].to_numpy())
    return iso


def run(panel: pd.DataFrame, months: int = 12, rounds: int = ROUNDS) -> dict:
    cols = feature_cols(panel)
    print(f"[model] {len(cols)} features, panel {panel.shape}")
    result = {"features": cols, "targets": {}}
    for target in ("y_up", "y_dn"):
        oos = walk_forward(panel, target, cols, months, rounds)
        stats = summarize(oos, target)
        print(f"[model] {target} OOS: {json.dumps({k: v for k, v in stats.items() if k not in ('buckets', 'monthly')}, ensure_ascii=False)}")
        iso = fit_calibrator(oos, target)
        full = panel[(panel[target] >= 0) & (panel["date"] >= TRAIN_START)]
        mdl = train_one(full, target, cols, rounds)
        imp = pd.Series(mdl.feature_importance("gain"), index=cols).sort_values(ascending=False)
        result["targets"][target] = {"model": mdl, "iso": iso, "oos": oos, "stats": stats,
                                     "importance": imp.head(40).to_dict()}
        oos.to_parquet(DATA / f"oos_{target}.parquet", index=False)
        mdl.save_model(str(DATA / f"model_{target}.txt"))
    return result
