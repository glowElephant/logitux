"""마우스 모델 도식 데이터(SVG + 버튼 좌표)를 로드하고, 감지된 기기와 매칭한다.

모델은 코드가 아니라 `logitux/data/mice/<model>.json` + `.svg` 데이터로 외부화한다.
새 모델 추가 = 데이터 파일 추가 (코드 수정 불필요).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .detect import MouseDevice

# __file__ 기준 — 절대경로 하드코딩 금지
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mice"


@dataclass
class ButtonSpot:
    """도식 위 버튼 한 개의 위치와 라벨 위치."""

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
    match: dict           # {"wpid": ..., "codename": ...}
    svg_path: Path
    view_w: int
    view_h: int
    spots: list[ButtonSpot]


def _load_one(json_path: Path) -> MouseModel | None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    view = data.get("view", {})
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
    return MouseModel(
        model=str(data.get("model", json_path.stem)),
        match=dict(data.get("match", {})),
        svg_path=json_path.parent / str(data.get("svg", "")),
        view_w=int(view.get("width", 300)),
        view_h=int(view.get("height", 470)),
        spots=spots,
    )


def load_models() -> list[MouseModel]:
    """data/mice/ 의 모든 모델 데이터를 로드한다."""
    if not DATA_DIR.is_dir():
        return []
    out: list[MouseModel] = []
    for json_path in sorted(DATA_DIR.glob("*.json")):
        model = _load_one(json_path)
        if model:
            out.append(model)
    return out


def match_model(mouse: MouseDevice) -> MouseModel | None:
    """감지된 마우스에 맞는 모델 도식을 찾는다.

    wpid(우선) 또는 codename으로 매칭. 못 찾으면 None.
    """
    wpid = (mouse.wpid or "").upper()
    codename = (mouse.codename or "").strip().lower()
    for model in load_models():
        m_wpid = str(model.match.get("wpid", "")).upper()
        m_code = str(model.match.get("codename", "")).strip().lower()
        if m_wpid and m_wpid == wpid:
            return model
        if m_code and m_code == codename:
            return model
    return None
