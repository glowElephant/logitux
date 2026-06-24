"""Solaar의 logitech_receiver 라이브러리를 import 경로에 올린다.

logitux는 Solaar를 백엔드 매핑 엔진으로 사용한다. Solaar는 배포판에 따라
시스템 패키지로 설치되며, 그 Python 라이브러리(`logitech_receiver`)가
`sys.path`에 기본 포함되지 않는 경로(예: /usr/share/solaar/lib)에 놓이는 경우가 많다.

경로는 하드코딩하지 않고 후보 목록을 탐색한다. 사용자가 다른 위치에
설치했다면 환경변수 SOLAAR_LIB로 지정할 수 있다.
"""
from __future__ import annotations

import os
import sys

# 배포판별 Solaar 라이브러리 후보 경로 (env > 표준 위치들)
_CANDIDATE_DIRS = [
    os.environ.get("SOLAAR_LIB"),
    "/usr/share/solaar/lib",
    "/usr/local/share/solaar/lib",
    "/usr/lib/python3/dist-packages",
    "/usr/lib/solaar",
]


class SolaarNotFound(RuntimeError):
    """Solaar(logitech_receiver) 라이브러리를 찾지 못했을 때."""


def ensure_solaar_on_path() -> str:
    """`logitech_receiver`를 import 가능하게 만들고, 사용된 경로를 반환.

    이미 import 가능하면 빈 문자열 반환. 끝까지 못 찾으면 SolaarNotFound.
    """
    try:
        import logitech_receiver  # noqa: F401

        return ""
    except ImportError:
        pass

    for path in _CANDIDATE_DIRS:
        if not path:
            continue
        if not os.path.isdir(os.path.join(path, "logitech_receiver")):
            continue
        if path not in sys.path:
            sys.path.insert(0, path)
        try:
            import logitech_receiver  # noqa: F401

            return path
        except ImportError:
            # 경로는 맞지만 import 실패 — 다음 후보로
            if path in sys.path:
                sys.path.remove(path)
            continue

    raise SolaarNotFound(
        "Solaar(logitech_receiver) 라이브러리를 찾을 수 없습니다.\n"
        "설치: sudo apt install solaar  (또는 배포판 패키지 매니저)\n"
        "비표준 위치라면 환경변수 SOLAAR_LIB로 lib 경로를 지정하세요."
    )
