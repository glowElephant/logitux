"""매핑(cid→키조합)을 Solaar 백엔드 설정으로 적용한다. (마일스톤 ③)

검증된 경로:
  버튼 누름 → HID++ notification → divert 인식 → rules.yaml 룰 매칭 → KeyPress emit

logitux는 이 동작을 사용자에게 감추고 자동화한다. 사용자는 그림과 클릭만 본다.

적용 절차(순서 중요 — 데몬이 떠 있으면 config.json을 종료 시 덮어쓰므로 먼저 멈춘다):
  1. solaar 데몬 정지
  2. ~/.config/solaar/config.json 의 divert-keys 갱신 (매핑된 버튼 = 1)
  3. ~/.config/solaar/rules.yaml 재생성 (logitux 관리 파일)
  4. solaar 데몬 재시작 (--window=hide)
  5. ~/.config/logitux/mappings.json 에 매핑 영구 저장 (다음 실행 시 복원)

한계: Solaar의 KeyPress는 X11(XTEST) 기반이라 Wayland 세션에서는 emit이 동작하지 않을
수 있다. `display_server()`로 감지해 상위에서 사용자에게 안내한다.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .buttons import ButtonInfo, list_buttons
from .detect import MouseDevice
from .keysyms import UnsupportedKey, qt_sequence_to_keysyms


def _config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config"


def solaar_config_path() -> Path:
    return _config_home() / "solaar" / "config.json"


def solaar_rules_path() -> Path:
    return _config_home() / "solaar" / "rules.yaml"


def logitux_mappings_path() -> Path:
    return _config_home() / "logitux" / "mappings.json"


def display_server() -> str:
    """현재 세션의 디스플레이 서버: "x11" | "wayland" | "unknown"."""
    st = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if st in ("x11", "wayland"):
        return st
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


@dataclass
class ApplyResult:
    """적용 결과 — 무엇이 반영됐고 무엇이 빠졌는지."""

    applied: dict[int, str] = field(default_factory=dict)        # cid → 키조합
    skipped: list[tuple[int, str]] = field(default_factory=list)  # (cid, 사유)
    daemon_restarted: bool = False
    display_warning: str | None = None


# ── 매핑 영구 저장 ────────────────────────────────────────────────

def load_saved_mappings(serial: str) -> dict[int, str]:
    """저장된 매핑을 불러온다. 없으면 빈 dict."""
    p = logitux_mappings_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
    except Exception:
        return {}
    dev = data.get(serial, {})
    return {int(cid): seq for cid, seq in dev.items()}


def _save_mappings(serial: str, mappings: dict[int, str]) -> None:
    p = logitux_mappings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text())
        except Exception:
            data = {}
    data[serial] = {str(cid): seq for cid, seq in mappings.items()}
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── 데몬 관리 ────────────────────────────────────────────────────

def _solaar_pids() -> list[int]:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "bin/solaar"], capture_output=True, text=True
        ).stdout
    except FileNotFoundError:
        return []
    return [int(x) for x in out.split() if x.strip().isdigit()]


def stop_daemon() -> None:
    """실행 중인 solaar 데몬을 모두 종료한다."""
    for pid in _solaar_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    # 종료 대기 (config.json flush 완료까지)
    for _ in range(20):
        if not _solaar_pids():
            break
        time.sleep(0.1)


def start_daemon() -> bool:
    """solaar 데몬을 트레이 숨김 모드로 시작한다. 성공 여부 반환.

    셸 자식이 아니라 독립 세션(start_new_session)으로 띄워 부모 프로세스
    종료에 영향받지 않게 한다.
    """
    exe = shutil.which("solaar")
    if not exe:
        return False
    try:
        subprocess.Popen(
            [exe, "--window=hide"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    except Exception:
        return False
    # 기동 확인
    for _ in range(30):
        time.sleep(0.2)
        if _solaar_pids():
            return True
    return False


def is_daemon_running() -> bool:
    return bool(_solaar_pids())


# ── config.json divert-keys ──────────────────────────────────────

def _find_device_key(cfg: dict, mouse: MouseDevice) -> str | None:
    """config.json에서 이 마우스의 entry 키를 찾는다 (시리얼 우선)."""
    for k, v in cfg.items():
        if not isinstance(v, dict):
            continue
        if mouse.serial and v.get("_serial") == mouse.serial:
            return k
    # 폴백: 코드네임 일치
    for k, v in cfg.items():
        if isinstance(v, dict) and v.get("_name") == mouse.codename:
            return k
    return None


def _update_divert(mouse: MouseDevice, mappable_cids: set[int], on_cids: set[int]) -> None:
    """divert-keys를 갱신: on_cids는 1, 나머지 mappable은 0."""
    p = solaar_config_path()
    if not p.is_file():
        return
    cfg = json.loads(p.read_text())
    key = _find_device_key(cfg, mouse)
    if key is None:
        return
    dk = cfg[key].setdefault("divert-keys", {})
    for cid in mappable_cids:
        dk[str(cid)] = 1 if cid in on_cids else 0
    cfg[key]["divert-keys"] = dk
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


# ── rules.yaml 생성 ──────────────────────────────────────────────

_RULES_HEADER = (
    "%YAML 1.3\n"
    "# 이 파일은 logitux가 자동 생성/관리합니다. 직접 편집하지 마세요.\n"
    "# (편집은 logitux GUI에서 — 버튼을 클릭해 단축키를 지정)\n"
)


def _build_rules_yaml(rules: list[tuple[str, list[str]]]) -> str:
    """(키이름, keysym리스트) 목록 → rules.yaml 텍스트.

    각 룰은 하나의 YAML 문서(--- 구분): Key 조건 + KeyPress 액션.
    """
    docs = []
    for keyname, keysyms in rules:
        keys = ", ".join(keysyms)
        docs.append(f"- Key: [{keyname}, pressed]\n- KeyPress: [{keys}]")
    body = "\n".join(f"---\n{d}" for d in docs)
    return _RULES_HEADER + body + "\n...\n"


def _write_rules(rules: list[tuple[str, list[str]]]) -> None:
    p = solaar_rules_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # 기존 사용자 파일이 logitux 관리 파일이 아니면 1회 백업
    if p.is_file():
        head = p.read_text()[:120]
        if "logitux" not in head and not (p.parent / "rules.yaml.bak").exists():
            shutil.copy2(p, p.parent / "rules.yaml.bak")
    p.write_text(_build_rules_yaml(rules))


# ── 공개 API ─────────────────────────────────────────────────────

def apply_mappings(mouse: MouseDevice, mappings: dict[int, str]) -> ApplyResult:
    """매핑을 Solaar 백엔드에 적용하고 데몬을 재시작한다.

    mappings: {cid: "Ctrl+Alt+S"}. 빈 값/없는 cid는 매핑 해제로 취급.
    이름 없는 버튼(예: unknown:01A0)이나 변환 불가 키는 skipped에 담아 반환한다.
    """
    result = ApplyResult()

    if display_server() == "wayland":
        result.display_warning = (
            "Wayland 세션입니다. Solaar의 키 입력(XTEST)은 X11에서만 동작하므로 "
            "버튼을 눌러도 단축키가 emit되지 않을 수 있습니다. X11 세션 사용을 권장합니다."
        )

    # 버튼 메타(cid → 키이름, mappable)
    buttons: list[ButtonInfo] = list_buttons(mouse)
    by_cid = {b.cid: b for b in buttons}
    mappable_cids = {b.cid for b in buttons if b.mappable}

    rules: list[tuple[str, list[str]]] = []
    for cid, seq in mappings.items():
        if not seq:
            continue
        info = by_cid.get(cid)
        if info is None or not info.mappable:
            result.skipped.append((cid, "매핑 불가 버튼"))
            continue
        keyname = info.name
        if not keyname or keyname.startswith("unknown"):
            result.skipped.append((cid, f"Solaar가 인식하는 버튼 이름이 없음 ({keyname})"))
            continue
        try:
            keysyms = qt_sequence_to_keysyms(seq)
        except UnsupportedKey as e:
            result.skipped.append((cid, f"변환 불가 키: {e}"))
            continue
        if not keysyms:
            continue
        rules.append((keyname, keysyms))
        result.applied[cid] = seq

    on_cids = set(result.applied.keys())

    # 데몬 정지 → 설정 기록 → 재시작 (config 충돌 방지)
    stop_daemon()
    _update_divert(mouse, mappable_cids, on_cids)
    _write_rules(rules)
    result.daemon_restarted = start_daemon()

    _save_mappings(mouse.serial, result.applied)
    return result
