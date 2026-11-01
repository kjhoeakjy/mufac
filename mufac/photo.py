"""곡 분위기에 맞는 배경 그림(일러스트)을 구한다.

photo.jpg   가로 그림(본편 영상, 썸네일)
photo_v.jpg 세로 그림(쇼츠 도입). 없으면 가로 그림 가운데를 잘라 쓴다.
photo_v2~4.jpg 쇼츠 후렴·브릿지·엔딩용 세로 그림. 같은 이야기의 다른 순간. 영상 만들 때 없으면 그린다.
cover.jpg   정사각 커버(Suno 곡 이미지). 없으면 가로 그림 가운데를 잘라 만든다.

OpenAI 이미지(기본, 일러스트) → Pexels 실제 사진 → 둘 다 없으면 색 그라데이션 순서로 시도한다.
"""

from __future__ import annotations

import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor
import random
import zlib

import numpy as np
import requests
from PIL import Image

from .song import Song, config

MIN_WIDTH = 2400
LOOK = (
    "Premium painterly editorial illustration, like a New Yorker cover: confident brushwork, harmonious color, real light and shadow, "
    "believable people and objects. Calm lower third for lyrics. Not photorealistic, not 3D, not anime, not flat clip art. "
    "No text, no letters, no watermark, no faces looking straight at the viewer."
)


def fetch(song: Song, *, pick: int | None = None, shorts: bool = False) -> dict:
    """가로·세로·정사각 그림. shorts=True면 쇼츠용 세로 그림 세 장(photo_v2~4)도 함께 그린다."""
    query = song.meta.get("photo_query") or "city night window rain"
    scene = song.meta.get("image_prompt") or f"Illustration of {query}."
    source = config().get("photo_source", "openai")
    has_openai, has_pexels = bool(os.environ.get("OPENAI_API_KEY")), bool(os.environ.get("PEXELS_API_KEY"))
    if source == "openai" and has_openai:
        info = _openai(song, scene)
        if shorts:
            fetch_shorts(song)
    elif has_pexels:
        info = _pexels(song, query, pick)
    elif has_openai:
        info = _openai(song, scene)
        if shorts:
            fetch_shorts(song)
    else:
        info = _gradient(song)
    song.meta["photo"] = info
    return info


# 쓸 수 있는 모델을 차례로 시도한다(계정에 따라 없는 모델이 있다). OPENAI_IMAGE_MODEL로 맨 앞에 끼워 넣을 수 있다
# 2026-10 기준: gpt-image-1은 퇴역, gpt-image-1.5·1-mini는 2026-12-01 종료 예정, 현행은 gpt-image-2 계열
IMAGE_MODELS = ["gpt-image-2.5-flare", "gpt-image-2", "gpt-image-1.5", "gpt-image-1-mini", "gpt-image-1"]
# 모델별 크기 이름: (가로, 세로, 정사각)
SIZES = {"dall-e-3": ("1792x1024", "1024x1792", "1024x1024")}
DEFAULT_SIZES = ("1536x1024", "1024x1536", "1024x1024")


def _models() -> list[str]:
    wanted = os.environ.get("OPENAI_IMAGE_MODEL", "")
    return ([wanted] if wanted else []) + [m for m in IMAGE_MODELS if m != wanted]


def _openai(song: Song, scene: str) -> dict:
    prompt = f"{scene}\n\n{LOOK}"
    last = None
    for model in _models():
        try:
            _openai_model(song, model, prompt)
            return {"source": "openai", "model": model, "prompt": scene}
        except _NoModel as e:
            print(f"이미지 모델 {model} 사용 불가, 다음 모델로: {e}", flush=True)
            last = e
    raise RuntimeError(f"쓸 수 있는 OpenAI 이미지 모델이 없습니다: {last}")


# 쇼츠 세 장(후렴·브릿지·엔딩)의 장면. 작사 때 short_scenes가 나오면 그것을, 없으면 본 장면에 순간만 바꿔 붙인다
SHORT_MOMENTS = (
    "The peak of the story, the same person and place but the most charged moment, strongest light and color.",
    "A close view inside the same story: hands, one object, a small detail; shallow depth, quieter light.",
    "After it is over: the same place later, the person leaving or already gone, last light of the day.",
)


def short_scenes(song: Song) -> list[str]:
    base = song.meta.get("image_prompt") or f"Illustration of {song.meta.get('photo_query') or 'city night window rain'}."
    given = [s for s in (song.meta.get("short_scenes") or []) if isinstance(s, str) and s.strip()]
    if len(given) >= 3:
        return given[:3]
    return [f"{base}\n{m}" for m in SHORT_MOMENTS]


def fetch_shorts(song: Song, *, only_missing: bool = False) -> None:
    """쇼츠용 세로 그림 세 장(photo_v2~4). OpenAI 키가 없으면 아무것도 하지 않는다(영상은 앞 그림을 돌려 쓴다)."""
    if not os.environ.get("OPENAI_API_KEY"):
        return
    paths = song.photo_v_paths()[1:]
    jobs = [(scene, path) for scene, path in zip(short_scenes(song), paths) if not (only_missing and path.exists())]
    if not jobs:
        return
    last = None
    for model in _models():
        try:
            _openai_many(model, [(f"{scene}\n\n{LOOK}", path, SIZES.get(model, DEFAULT_SIZES)[1]) for scene, path in jobs])
            song.meta.setdefault("photo", {})["shorts"] = len(jobs)
            return
        except _NoModel as e:
            last = e
    raise RuntimeError(f"쓸 수 있는 OpenAI 이미지 모델이 없습니다: {last}")


class _NoModel(RuntimeError):
    """이 계정에서 그 모델을 쓸 수 없다(없거나 권한 없음)."""


def _openai_model(song: Song, model: str, prompt: str) -> None:
    sizes = SIZES.get(model, DEFAULT_SIZES)
    # 가로·세로·정사각 세 장을 동시에 만든다
    _openai_many(model, [(prompt, song.photo_path, sizes[0]), (prompt, song.photo_v_path, sizes[1]), (prompt, song.cover_path, sizes[2])])


def _openai_many(model: str, jobs: list[tuple[str, object, str]]) -> None:
    """(프롬프트, 저장 경로, 크기) 묶음을 동시에 그린다."""

    def one(prompt: str, size: str, path) -> None:
        body = {"model": model, "prompt": prompt, "size": size, "n": 1}
        if model.startswith("dall-e"):
            body.update(quality="hd", response_format="b64_json")
        else:
            body.update(quality="high")
        for _ in range(3):  # 모델이 모르는 size/quality 값이면 그 값만 빼고 한 번 더
            r = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json=body, timeout=600,
            )
            if r.status_code < 400:
                break
            text = r.text[:500]
            try:
                err = r.json().get("error") or {}
            except ValueError:
                err = {}
            param = err.get("param") or ""
            if r.status_code in (400, 403, 404) and (param == "model" or "does not exist" in text or "verified" in text):
                raise _NoModel(text)
            if r.status_code == 400 and param == "size" and body.get("size") != "auto":
                body["size"] = "auto"
                continue
            if r.status_code == 400 and param == "quality" and "quality" in body:
                body.pop("quality")
                continue
            raise RuntimeError(f"OpenAI 이미지 생성 실패 ({r.status_code}): {text}")
        else:
            raise RuntimeError(f"OpenAI 이미지 생성 실패: {r.text[:300]}")
        item = r.json()["data"][0]
        raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else requests.get(item["url"], timeout=120).content
        _save(Image.open(io.BytesIO(raw)), path)

    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        for f in [pool.submit(one, prompt, size, path) for prompt, path, size in jobs]:
            f.result()


def _pexels(song: Song, query: str, pick: int | None) -> dict:
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": os.environ["PEXELS_API_KEY"]},
        params={"query": query, "orientation": "landscape", "size": "large", "per_page": 30},
        timeout=30,
    )
    r.raise_for_status()
    photos = [p for p in r.json().get("photos", []) if p["width"] >= MIN_WIDTH]
    if not photos:
        short = " ".join(query.split()[:2])
        if short != query:
            return _pexels(song, short, pick)
        return _gradient(song)
    # 같은 검색어라도 곡마다 다른 사진이 나오도록 slug로 섞는다
    top = photos[:8]
    p = top[pick % len(top)] if pick is not None else random.Random(song.slug).choice(top)
    img = requests.get(p["src"]["original"], timeout=120)
    img.raise_for_status()
    _save(Image.open(io.BytesIO(img.content)), song.photo_path)
    song.photo_v_path.unlink(missing_ok=True)
    square_cover(song)
    return {
        "source": "pexels", "query": query, "id": p["id"], "page": p["url"],
        "photographer": p["photographer"], "photographer_url": p["photographer_url"],
    }


def _gradient(song: Song) -> dict:
    """키가 없을 때 쓰는 대체 이미지. 어두운 저녁 하늘 색."""
    rng = np.random.default_rng(zlib.crc32(song.slug.encode()))
    w, h = 2560, 1440
    y = np.linspace(0, 1, h)[:, None, None]
    top = np.array([18, 22, 40]) + rng.integers(-6, 6, 3)
    bottom = np.array([120, 84, 92]) + rng.integers(-20, 20, 3)
    img = np.broadcast_to(top * (1 - y) + bottom * y, (h, w, 3)).copy()
    img += rng.normal(0, 4, (h, w, 1))
    _save(Image.fromarray(np.clip(img, 0, 255).astype("uint8")), song.photo_path)
    song.photo_v_path.unlink(missing_ok=True)
    square_cover(song)
    return {"source": "gradient"}


def square_cover(song: Song) -> None:
    """가로 사진 가운데를 잘라 Suno용 정사각 커버를 만든다."""
    img = Image.open(song.photo_path).convert("RGB")
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img.crop((left, top, left + side, top + side)).resize((1024, 1024), Image.LANCZOS).save(song.cover_path, "JPEG", quality=90)


def _save(img: Image.Image, path) -> None:
    img = img.convert("RGB")
    # 너무 큰 원본은 4K 폭으로 줄여 저장소 용량을 아낀다
    if max(img.size) > 3840:
        s = 3840 / max(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=90)
