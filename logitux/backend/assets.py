"""모델 이미지 다운로드·캐시.

마우스 도식 이미지(로지텍 CDN 등)는 저작권 때문에 저장소에 번들하지 않고,
첫 실행 시 다운로드해 사용자 캐시(~/.cache/logitux/images/)에 저장한다.
오프라인이거나 다운로드 실패 시 None을 반환하고, 호출측이 generic 도식으로 폴백한다.
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "logitux" / "images"
_TIMEOUT = 8  # 초


def _cache_path(url: str) -> Path:
    ext = ".png"
    if "." in url.rsplit("/", 1)[-1]:
        tail = url.rsplit(".", 1)[-1].split("?")[0].lower()
        if tail in ("png", "jpg", "jpeg", "webp", "svg"):
            ext = "." + tail
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}{ext}"


def cached_image(url: str) -> Path | None:
    """url 이미지를 캐시에서 반환. 없으면 다운로드. 실패 시 None."""
    if not url:
        return None
    dest = _cache_path(url)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "logitux/0.1"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read()
        if not data:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:
        return None
