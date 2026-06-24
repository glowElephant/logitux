#!/usr/bin/env python3
"""logitux 진입점.

현재 마일스톤 ①: 연결된 로지텍 마우스를 감지해 선택 화면을 띄운다.
선택 시 콘솔에 출력한다(다음 마일스톤에서 도식/매핑 화면으로 전환 예정).
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from logitux.gui.select_window import MouseSelectWindow

    app = QApplication(sys.argv)
    window = MouseSelectWindow()

    def on_selected(device) -> None:
        # 마일스톤 ②에서 도식 매핑 화면으로 교체될 자리
        print(f"선택됨: {device.codename} (wpid={device.wpid}, {device.receiver_path})")

    window.mouse_selected.connect(on_selected)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
