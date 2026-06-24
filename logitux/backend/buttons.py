"""선택한 마우스의 재할당 가능 버튼을 열거한다.

REPROG CONTROLS V4(0x1B04) 기능의 버튼 목록과 각 버튼의 flag를 추출한다.
실제로 키조합을 매핑할 수 있는 버튼은 `divertable`(소프트웨어로 우회 가능)이며
`virtual`이 아닌 물리 버튼이다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any

from .detect import MouseDevice
from .solaar_env import ensure_solaar_on_path


@dataclass
class ButtonInfo:
    """재할당 가능 버튼 한 개의 정보."""

    cid: int               # Control ID, 예: 195
    name: str              # 예: "Mouse Gesture Button"
    divertable: bool       # 소프트웨어로 우회 가능(= 키조합 매핑 가능)
    reprogrammable: bool   # 다른 버튼 기능으로 재할당 가능
    virtual: bool          # 물리 버튼이 아닌 가상 버튼
    mappable: bool         # logitux가 키조합을 걸 수 있는 버튼인지 (divertable & not virtual)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _quiet() -> None:
    logging.getLogger("logitech_receiver").setLevel(logging.CRITICAL)


def _extract(dev) -> list[ButtonInfo]:
    from logitech_receiver.hidpp20 import FEATURE

    if FEATURE.REPROG_CONTROLS_V4 not in dev.features:
        return []

    out: list[ButtonInfo] = []
    for k in dev.keys:
        names = set(k.flags)  # generator → set (한 번만 소비되므로 즉시 변환)
        divertable = "divertable" in names
        virtual = "virtual" in names
        out.append(
            ButtonInfo(
                cid=int(k.key),
                name=str(k.key),
                divertable=divertable,
                reprogrammable="reprogrammable" in names,
                virtual=virtual,
                mappable=divertable and not virtual,
            )
        )
    return out


def list_buttons(mouse: MouseDevice) -> list[ButtonInfo]:
    """주어진 마우스의 재할당 가능 버튼 목록을 반환한다.

    `mouse`의 receiver_path / device_number로 해당 기기를 다시 찾아 조회한다.
    기기를 못 찾으면 빈 리스트.
    """
    ensure_solaar_on_path()
    _quiet()

    from logitech_receiver import Receiver, base

    for dev_info in base.receivers():
        try:
            receiver = Receiver.open(dev_info)
        except Exception:
            continue
        if not receiver:
            continue
        if mouse.receiver_path and str(getattr(receiver, "path", "")) != mouse.receiver_path:
            continue
        try:
            for dev in receiver:
                if not dev:
                    continue
                if int(getattr(dev, "number", 0) or 0) != mouse.device_number:
                    continue
                return _extract(dev)
        except Exception:
            continue
    return []
