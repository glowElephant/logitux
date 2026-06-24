"""마우스 모델 도식 데이터(이미지/SVG + 버튼 좌표)를 로드하고 기기와 매칭한다.

모델은 코드가 아니라 `logitux/data/mice/<model>.json` 데이터로 외부화한다.
- 실물 이미지 모델: `image_url`(로지텍 CDN 등) — 런타임 다운로드·캐시.
- 폴백(generic) 모델: `svg` 파일 — 저장소에 번들된 일반 마우스 도식.
좌표는 모두 `canvas`(w,h) 좌표계 기준이며, 화면 렌더 시 스케일링한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .detect import MouseDevice

# __file__ 기준 — 절대경로 하드코딩 금지
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mice"
GENERIC_NAME = "_generic.json"


@dataclass
class ButtonSpot:
    """도식 위 버튼 한 개의 위치와 라벨 위치 (canvas 좌표계)."""

    cid: int
    x: float
    y: float
    label: str
    label_x: float
    label_y: float


@dataclass
class MouseModel:
    """한 마우스 모델의 도식 데이터."""

    model: str
    match: dict                       # {"wpid": ..., "codename": ...}
    canvas_w: int
    canvas_h: int
    spots: list[ButtonSpot]
    image_url: str = ""               # 실물 이미지 (런타임 다운로드)
    svg_path: Path | None = None      # 번들 SVG (generic)
    is_generic: bool = False


def _load_one(json_path: Path) -> MouseModel | None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    canvas = data.get("canvas", {})
    spots = [
        ButtonSpot(
            cid=int(b["cid"]),
            x=float(b["x"]),
            y=float(b["y"]),
            label=str(b["label"]),
            label_x=float(b["label_x"]),
            label_y=float(b["label_y"]),
        )
        for b in data.get("buttons", [])
    ]
    svg = data.get("svg")
    return MouseModel(
        model=str(data.get("model", json_path.stem)),
        match=dict(data.get("match", {})),
        canvas_w=int(canvas.get("width", 800)),
        canvas_h=int(canvas.get("height", 700)),
        spots=spots,
        image_url=str(data.get("image_url", "")),
        svg_path=(json_path.parent / str(svg)) if svg else None,
        is_generic=(json_path.name == GENERIC_NAME),
    )


def load_models() -> list[MouseModel]:
    """data/mice/ 의 모든 모델 데이터를 로드한다 (generic 포함)."""
    if not DATA_DIR.is_dir():
        return []
    out: list[MouseModel] = []
    for json_path in sorted(DATA_DIR.glob("*.json")):
        model = _load_one(json_path)
        if model:
            out.append(model)
    return out


def load_generic() -> MouseModel | None:
    """매칭 실패 시 사용할 generic 도식 모델."""
    path = DATA_DIR / GENERIC_NAME
    if not path.exists():
        return None
    return _load_one(path)


def match_model(mouse: MouseDevice) -> MouseModel | None:
    """감지된 마우스에 맞는 모델 도식을 찾는다.

    wpid(우선) 또는 codename으로 매칭. 못 찾으면 generic 모델(있으면), 그것도 없으면 None.
    """
    wpid = (mouse.wpid or "").upper()
    codename = (mouse.codename or "").strip().lower()
    for model in load_models():
        if model.is_generic:
            continue
        m_wpid = str(model.match.get("wpid", "")).upper()
        if m_wpid and m_wpid == wpid:
            return model
        # codename은 문자열 또는 문자열 리스트(여러 모델명) 허용
        raw = model.match.get("codename", "")
        names = [raw] if isinstance(raw, str) else list(raw)
        if codename and codename in (str(n).strip().lower() for n in names):
            return model
    return load_generic()
