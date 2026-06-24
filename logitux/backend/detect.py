"""연결된 로지텍 마우스를 감지·열거한다.

Solaar의 logitech_receiver API를 사용한다. (출력 파싱이 아니라 API 직접 호출 —
로케일/버전에 덜 취약하다.)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any

from .solaar_env import ensure_solaar_on_path


@dataclass
class MouseDevice:
    """감지된 마우스 한 대의 식별 정보."""

    codename: str          # 예: "MX Master 4"
    kind: str              # 항상 "mouse" (필터 결과)
    wpid: str              # 무선 제품 ID, 예: "B042"
    serial: str            # 시리얼/유닛 ID
    receiver_path: str     # 연결된 리시버의 hidraw 경로
    device_number: int     # 리시버 내 페어링 슬롯 번호

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _quiet_solaar_logging() -> None:
    """빈 페어링 슬롯 순회 시 발생하는 NoSuchDevice 로그 노이즈를 억제."""
    logging.getLogger("logitech_receiver").setLevel(logging.CRITICAL)


def list_mice() -> list[MouseDevice]:
    """현재 연결된 로지텍 마우스 목록을 반환한다.

    Solaar 라이브러리를 찾지 못하면 SolaarNotFound가 발생한다.
    리시버/슬롯 접근 중 개별 오류는 건너뛴다(빈 슬롯 등).
    """
    ensure_solaar_on_path()
    _quiet_solaar_logging()

    from logitech_receiver import Receiver, base  # 경로 설정 후 import

    mice: list[MouseDevice] = []
    for dev_info in base.receivers():
        try:
            receiver = Receiver.open(dev_info)
        except Exception:
            continue
        if not receiver:
            continue
        try:
            for dev in receiver:
                if not dev:
                    continue
                if str(getattr(dev, "kind", "")) != "mouse":
                    continue
                mice.append(
                    MouseDevice(
                        codename=str(dev.codename),
                        kind="mouse",
                        wpid=str(getattr(dev, "wpid", "") or ""),
                        serial=str(getattr(dev, "serial", "") or ""),
                        receiver_path=str(getattr(receiver, "path", "") or ""),
                        device_number=int(getattr(dev, "number", 0) or 0),
                    )
                )
        except Exception:
            # 슬롯 순회 중 개별 오류는 무시하고 다음 리시버로
            continue
    return mice
