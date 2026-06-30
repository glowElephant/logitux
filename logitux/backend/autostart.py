"""solaar 데몬의 로그인 자동 실행(autostart)을 보장한다. (마일스톤 ③-b)

MX 시리즈는 온보드 저장이 없어 매핑 변환 데몬이 항상 떠 있어야 한다.
대부분의 배포판에서 solaar 패키지는 시스템 autostart
(`/etc/xdg/autostart/solaar.desktop`, `Exec=solaar --window=hide`)를 이미 제공한다.

logitux의 역할은 이 autostart가 **꺼져 있거나 없는 PC에서도** 데몬 상시 실행을
보장하는 것이다. 그럴 때만 사용자 레벨 autostart 파일을 만들어 시스템 항목을
덮어쓴다(같은 파일명 → XDG 오버라이드 규칙).

X11/Wayland 무관하게 autostart 등록 자체는 동일하다(데몬 기동 방식만 동일).
"""
from __future__ import annotations

import os
from pathlib import Path

_DESKTOP_NAME = "solaar.desktop"  # 시스템 항목과 같은 이름 → 사용자 파일이 오버라이드

_USER_DESKTOP = (
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=Solaar (logitux)\n"
    "Comment=logitux가 등록 — 로지텍 버튼 매핑 데몬 상시 실행\n"
    "Exec=solaar --window=hide\n"
    "Icon=solaar\n"
    "Terminal=false\n"
    "X-GNOME-Autostart-enabled=true\n"
)


def _config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config"


def _user_autostart_path() -> Path:
    return _config_home() / "autostart" / _DESKTOP_NAME


def _system_autostart_path() -> Path:
    return Path("/etc/xdg/autostart") / _DESKTOP_NAME


def _is_enabled(path: Path) -> bool:
    """해당 .desktop이 autostart를 켜는 상태인지.

    Hidden=true 또는 X-GNOME-Autostart-enabled=false 이면 꺼진 것으로 본다.
    """
    if not path.is_file():
        return False
    try:
        text = path.read_text()
    except Exception:
        return False
    for raw in text.splitlines():
        line = raw.strip().lower().replace(" ", "")
        if line == "hidden=true":
            return False
        if line == "x-gnome-autostart-enabled=false":
            return False
    return True


def autostart_status() -> str:
    """현재 데몬 autostart 상태.

    "user"   — 사용자 autostart 파일이 활성 (logitux가 보장한 상태 포함)
    "system" — 시스템 autostart만 활성 (사용자 파일 없음)
    "disabled" — 사용자 파일이 명시적으로 꺼 둠
    "missing"  — 어디에도 활성 autostart가 없음
    """
    user = _user_autostart_path()
    if user.is_file():
        return "user" if _is_enabled(user) else "disabled"
    if _is_enabled(_system_autostart_path()):
        return "system"
    return "missing"


def ensure_daemon_autostart() -> tuple[bool, str]:
    """데몬 autostart를 보장한다.

    이미 켜져 있으면(시스템/사용자) 그대로 두고, 꺼져 있거나 없으면 사용자
    autostart 파일을 생성/수정해 켠다.

    반환: (변경했는지, 사람이 읽을 상태 메시지)
    """
    status = autostart_status()
    if status in ("user", "system"):
        where = "시스템" if status == "system" else "사용자 설정"
        return False, f"데몬 자동 실행이 이미 켜져 있습니다 ({where})."

    # disabled 또는 missing → 사용자 파일로 보장
    path = _user_autostart_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_USER_DESKTOP)
    except Exception as e:  # noqa: BLE001
        return False, f"자동 실행 등록 실패: {e}"
    reason = "꺼져 있던 자동 실행을 다시 켰습니다." if status == "disabled" else "데몬 자동 실행을 등록했습니다."
    return True, f"{reason} (다음 로그인부터 적용)"


def disable_daemon_autostart() -> bool:
    """logitux가 만든 사용자 autostart 파일을 제거한다(되돌리기용).

    시스템 autostart는 건드리지 않는다. 사용자 파일이 없으면 False.
    """
    path = _user_autostart_path()
    if not path.is_file():
        return False
    try:
        path.unlink()
        return True
    except Exception:
        return False
