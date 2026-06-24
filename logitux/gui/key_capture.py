"""키조합 입력 다이얼로그 — 버튼에 걸 단축키를 캡쳐한다."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class KeyCaptureDialog(QDialog):
    """단축키 하나를 입력받는 모달 다이얼로그.

    `result_sequence`에 "Ctrl+Alt+S" 형식 문자열을 담는다(취소/비우기는 빈 문자열).
    """

    def __init__(self, button_label: str, current: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("단축키 설정")
        self.setMinimumWidth(360)
        self.result_sequence = ""
        self.setStyleSheet(_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel(f"‘{button_label}’ 버튼에 걸 단축키")
        title.setObjectName("title")
        hint = QLabel("입력란을 클릭하고 원하는 키 조합을 누르세요. (예: Ctrl+Alt+S)")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(hint)

        self._edit = QKeySequenceEdit()
        if current:
            self._edit.setKeySequence(QKeySequence(current))
        root.addWidget(self._edit)

        btn_row = QHBoxLayout()
        clear = QPushButton("매핑 해제")
        clear.setObjectName("clear")
        clear.clicked.connect(self._on_clear)
        cancel = QPushButton("취소")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("저장")
        ok.setObjectName("ok")
        ok.clicked.connect(self._on_ok)
        btn_row.addWidget(clear)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _on_clear(self) -> None:
        self.result_sequence = ""
        self.accept()

    def _on_ok(self) -> None:
        seq = self._edit.keySequence()
        self.result_sequence = seq.toString(QKeySequence.PortableText)
        self.accept()


_STYLE = """
QDialog { background: #1e1f26; color: #e6e6ea; }
#title { font-size: 16px; font-weight: 600; }
#hint { color: #9a9aa6; font-size: 12px; }
QKeySequenceEdit { background: #2a2b34; border: 1px solid #4a4b57; border-radius: 8px;
                   padding: 10px; font-size: 15px; }
QPushButton { background: #34353f; color: #cfcfd6; border: none; border-radius: 8px;
              padding: 8px 16px; }
QPushButton:hover { background: #3d3e49; }
#ok { background: #5b8cff; color: white; font-weight: 600; }
#ok:hover { background: #6f9bff; }
#clear { background: transparent; color: #d77; }
#clear:hover { background: #2a2b34; }
"""
