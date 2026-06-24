#!/usr/bin/env python3
"""logitux 진입점.

마일스톤 ①–②: 마우스 감지·선택 → 도식 매핑 화면.
선택한 마우스의 도식 위에서 버튼을 클릭해 단축키를 지정한다.
(실제 키 emit 적용은 마일스톤 ③.)
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from logitux.gui.mapping_window import MappingWindow
    from logitux.gui.select_window import MouseSelectWindow

    app = QApplication(sys.argv)
    select = MouseSelectWindow()
    state: dict[str, object] = {}

    def on_selected(device) -> None:
        win = MappingWindow(device)

        def go_back() -> None:
            win.close()
            select.show()

        win.back.connect(go_back)
        state["mapping"] = win  # 참조 유지 (GC 방지)
        select.hide()
        win.show()

    select.mouse_selected.connect(on_selected)
    select.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
