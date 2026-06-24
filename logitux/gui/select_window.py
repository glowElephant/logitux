"""마우스 선택 화면 — 감지된 로지텍 마우스를 카드로 보여주고 하나를 선택한다.

마일스톤 ①의 UI. 선택이 끝나면 `mouse_selected` 시그널로 선택된 MouseDevice를
방출한다. 다음 마일스톤(도식 시각화)에서 이 시그널을 받아 매핑 화면으로 전환한다.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..backend.detect import MouseDevice, list_mice
from ..backend.solaar_env import SolaarNotFound


class MouseCard(QFrame):
    """마우스 한 대를 나타내는 클릭 가능한 카드."""

    clicked = Signal(object)  # MouseDevice

    def __init__(self, device: MouseDevice, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device = device
        self.setObjectName("mouseCard")
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        icon = QLabel("🖱️")
        icon.setObjectName("cardIcon")

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        name = QLabel(device.codename)
        name.setObjectName("cardName")
        meta = QLabel(f"무선 ID {device.wpid} · {device.receiver_path}")
        meta.setObjectName("cardMeta")
        text_box.addWidget(name)
        text_box.addWidget(meta)

        choose = QPushButton("선택 →")
        choose.setObjectName("cardChoose")
        choose.setCursor(Qt.PointingHandCursor)
        choose.clicked.connect(lambda: self.clicked.emit(self.device))

        layout.addWidget(icon)
        layout.addLayout(text_box, 1)
        layout.addWidget(choose)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 시그니처)
        self.clicked.emit(self.device)
        super().mousePressEvent(event)


class MouseSelectWindow(QWidget):
    """감지된 마우스 목록 화면."""

    mouse_selected = Signal(object)  # MouseDevice

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("logitux — 마우스 선택")
        self.setMinimumSize(460, 420)
        self.setStyleSheet(_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("연결된 로지텍 마우스")
        title.setObjectName("title")
        subtitle = QLabel("버튼을 매핑할 마우스를 선택하세요.")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # 카드들이 들어갈 스크롤 영역
        self._list_box = QVBoxLayout()
        self._list_box.setSpacing(10)
        self._list_box.addStretch(1)

        container = QWidget()
        container.setLayout(self._list_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        refresh = QPushButton("새로고침")
        refresh.setObjectName("refresh")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self.reload_devices)
        root.addWidget(refresh, 0, Qt.AlignRight)

        self.reload_devices()

    def reload_devices(self) -> None:
        """마우스를 다시 감지해 카드 목록을 갱신한다."""
        # 기존 카드 제거 (마지막 stretch는 유지)
        while self._list_box.count() > 1:
            item = self._list_box.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        try:
            mice = list_mice()
        except SolaarNotFound as exc:
            self._show_message(str(exc))
            return
        except Exception as exc:  # 예기치 못한 백엔드 오류
            self._show_message(f"마우스 감지 중 오류: {exc}")
            return

        if not mice:
            self._show_message(
                "연결된 로지텍 마우스가 없습니다.\n"
                "마우스를 켜고 리시버를 연결한 뒤 새로고침하세요."
            )
            return

        for device in mice:
            card = MouseCard(device)
            card.clicked.connect(self.mouse_selected.emit)
            self._list_box.insertWidget(self._list_box.count() - 1, card)

    def _show_message(self, text: str) -> None:
        msg = QLabel(text)
        msg.setObjectName("emptyMsg")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        self._list_box.insertWidget(self._list_box.count() - 1, msg)


_STYLE = """
QWidget { background: #1e1f26; color: #e6e6ea; font-size: 14px; }
#title { font-size: 22px; font-weight: 700; }
#subtitle { color: #9a9aa6; font-size: 13px; }
#mouseCard { background: #2a2b34; border: 1px solid #34353f; border-radius: 12px; }
#mouseCard:hover { border-color: #5b8cff; background: #2f313c; }
#cardIcon { font-size: 28px; }
#cardName { font-size: 16px; font-weight: 600; }
#cardMeta { color: #8a8a96; font-size: 12px; }
#cardChoose { background: #5b8cff; color: white; border: none; border-radius: 8px;
              padding: 8px 16px; font-weight: 600; }
#cardChoose:hover { background: #6f9bff; }
#refresh { background: #34353f; color: #cfcfd6; border: none; border-radius: 8px;
           padding: 8px 18px; }
#refresh:hover { background: #3d3e49; }
#emptyMsg { color: #9a9aa6; padding: 40px 20px; line-height: 1.5; }
"""
