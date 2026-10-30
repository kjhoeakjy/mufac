"""곡 분위기에 맞는 배경 그림(일러스트)을 구한다.

photo.jpg   가로 그림(본편 영상, 썸네일)
photo_v.jpg 세로 그림(쇼츠). 없으면 가로 그림 가운데를 잘라 쓴다.
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
    "Modern editorial illustration, flat shapes with soft textured shading and subtle grain, a restrained palette of four or five colors "
    "that follows the mood of the scene, clean composition with generous empty space in the lower third so lyrics can sit over it. "
    "Not photorealistic, not 3D render, not anime. "
    "No text, no letters, no signs with writing, no watermark, no faces looking at the viewer."
)


def fetch(song: Song, *, pick: int | None = None) -> dict:
    query = song.meta.get("photo_query") or "city night window rain"
    scene = song.meta.get("image_prompt") or f"Illustration of {query}."
    source = config().get("photo_source", "openai")
    has_openai, has_pexels = bool(os.environ.get("OPENAI_API_KEY")), bool(os.environ.get("PEXELS_API_KEY"))
    if source == "openai" and has_openai:
        info = _openai(song, scene)
    elif has_pexels:
        info = _pexels(song, query, pick)
    elif has_openai:
        info = _openai(song, scene)
    else:
        info = _gradient(song)
    song.meta["photo"] = info
    return info


def _openai(song: Song, scene: str) -> dict:
    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    prompt = f"{scene}\n\n{LOOK}"

    def one(size: str, path) -> None:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": model, "prompt": prompt, "size": size, "quality": "high", "n": 1},
            timeout=600,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"OpenAI 이미지 생성 실패 ({r.status_code}): {r.text[:500]}")
        item = r.json()["data"][0]
        raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else requests.get(item["url"], timeout=120).content
        _save(Image.open(io.BytesIO(raw)), path)

    # 가로·세로·정사각 세 장을 동시에 만든다
    jobs = (("1536x1024", song.photo_path), ("1024x1536", song.photo_v_path), ("1024x1024", song.cover_path))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in [pool.submit(one, size, path) for size, path in jobs]:
            f.result()
    return {"source": "openai", "model": model, "prompt": scene}


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
