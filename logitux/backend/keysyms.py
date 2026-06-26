"""Qt 키시퀀스 문자열("Ctrl+Alt+S") → Solaar KeyPress용 X11 keysym 이름 리스트.

Solaar의 KeyPress 액션은 각 항목을 ``Xlib.XK.string_to_keysym(name)`` 으로 해석한다.
따라서 변환 결과의 모든 이름은 그 함수가 0이 아닌 keysym을 돌려주는 유효한 이름이어야 한다.
(예: 공백은 Qt "Space" 가 아니라 X11 "space".)

X11(XTEST) 기반이라 Wayland 세션에서는 emit이 동작하지 않을 수 있다 — 이는 Solaar 백엔드의
한계이며, 디스플레이 서버 분기는 상위 적용 로직에서 처리한다.
"""
from __future__ import annotations

# Qt 수식어 토큰 → X11 keysym 이름 (왼쪽 키 기준)
_MODIFIERS = {
    "Ctrl": "Control_L",
    "Alt": "Alt_L",
    "Shift": "Shift_L",
    "Meta": "Super_L",  # Qt Meta == Super(윈도우 키)
}

# ASCII 기호 한 글자 → X11 keysym 이름 (string_to_keysym은 "+" 가 아니라 "plus" 를 받음)
_SYMBOLS = {
    "+": "plus", "-": "minus", "=": "equal", "/": "slash", "\\": "backslash",
    ".": "period", ",": "comma", ";": "semicolon", "'": "apostrophe",
    "`": "grave", "[": "bracketleft", "]": "bracketright", "_": "underscore",
    "*": "asterisk", "@": "at", "#": "numbersign", "$": "dollar", "%": "percent",
    "&": "ampersand", "(": "parenleft", ")": "parenright", "!": "exclam",
    "?": "question", "<": "less", ">": "greater", ":": "colon", '"': "quotedbl",
    "^": "asciicircum", "~": "asciitilde", "|": "bar", "{": "braceleft",
    "}": "braceright", " ": "space",
}

# Qt 비문자 키 이름 → X11 keysym 이름 (다를 때만 등록)
_SPECIAL = {
    "Space": "space",
    "Esc": "Escape",
    "Return": "Return",
    "Enter": "KP_Enter",
    "Tab": "Tab",
    "Backspace": "BackSpace",
    "Del": "Delete",
    "Ins": "Insert",
    "Home": "Home",
    "End": "End",
    "PgUp": "Prior",
    "PgDown": "Next",
    "Left": "Left",
    "Right": "Right",
    "Up": "Up",
    "Down": "Down",
}


class UnsupportedKey(ValueError):
    """변환할 수 없는 키 토큰."""


def _token_to_keysym_name(token: str) -> str:
    """단일 비수식 토큰(키 본체)을 X11 keysym 이름으로."""
    if token in _SPECIAL:
        return _SPECIAL[token]
    # F1..F24
    if len(token) >= 2 and token[0] == "F" and token[1:].isdigit():
        return token
    # 단일 영문자 → 소문자 (수식어는 별도 emit되므로 본체는 소문자 keysym)
    if len(token) == 1:
        if token.isalpha():
            return token.lower()
        if token in _SYMBOLS:
            return _SYMBOLS[token]
        # 숫자 한 글자는 그대로 (string_to_keysym이 "1" 해석)
        return token
    # 그 외(이름이 그대로 X11 keysym인 경우: "F5"는 위에서, "Menu" 등)
    return token


def qt_sequence_to_keysyms(seq: str) -> list[str]:
    """"Ctrl+Alt+S" → ["Control_L", "Alt_L", "s"].

    수식어를 먼저(누른 순서), 키 본체를 마지막에 둔다.
    빈 문자열이면 빈 리스트. 변환 불가 토큰은 UnsupportedKey.
    """
    seq = (seq or "").strip()
    if not seq:
        return []
    # Qt PortableText는 첫 시퀀스만 사용(다중 시퀀스 "A, B"는 미지원 → 첫 조합만)
    seq = seq.split(",", 1)[0].strip()

    parts = seq.split("+")
    mods: list[str] = []
    body: str | None = None
    for raw in parts:
        tok = raw.strip()
        if not tok:
            # "Ctrl++" 같은 경우의 마지막 '+' 키
            tok = "+"
        if tok in _MODIFIERS and body is None:
            mods.append(_MODIFIERS[tok])
        else:
            body = _token_to_keysym_name(tok)
    if body is None:
        raise UnsupportedKey(f"키 본체가 없습니다: {seq!r}")
    return mods + [body]
