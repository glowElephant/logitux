"""도식 매핑 화면 — 마우스 도식 위에 버튼 핫스팟·연결선·라벨을 그리고,
버튼을 클릭하면 단축키를 매핑한다. (마일스톤 ②)

"적용"을 누르면 backend(solaar_rules)가 매핑을 Solaar 백엔드 설정으로 변환해
실제 키가 emit되도록 한다. (마일스톤 ③)
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsObject,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.assets import cached_image
from ..backend.buttons import list_buttons
from ..backend.detect import MouseDevice
from ..backend.models import ButtonSpot, load_generic, match_model
from ..backend.solaar_rules import apply_mappings, load_saved_mappings
from .key_capture import KeyCaptureDialog

_BLUE = QColor("#5b8cff")
_GREEN = QColor("#3ddc84")
_GRAY = QColor("#5a5b66")
_CARD = QColor("#2a2b34")
_TEXT = QColor("#e6e6ea")
_MUTED = QColor("#8a8a96")


class ButtonLabelItem(QGraphicsObject):
    """버튼 라벨 박스 — 버튼명 + 현재 매핑 표시, 클릭 가능."""

    clicked = Signal(int)  # cid

    W = 128
    H = 42

    def __init__(self, spot: ButtonSpot, mappable: bool) -> None:
        super().__init__()
        self.spot = spot
        self.mappable = mappable
        self.mapping = ""
        if mappable:
            self.setCursor(Qt.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self._hover = False

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.W, self.H)

    def set_mapping(self, seq: str) -> None:
        self.mapping = seq
        self.update()

    def paint(self, p: QPainter, option, widget=None) -> None:
        p.setRenderHint(QPainter.Antialiasing)
        border = _GRAY
        if self.mappable:
            border = _GREEN if self.mapping else _BLUE
        p.setPen(QPen(border, 2 if self._hover else 1.5))
        p.setBrush(QBrush(_CARD))
        p.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 8, 8)

        # 버튼명
        p.setPen(QPen(_TEXT if self.mappable else _MUTED))
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(8, 4, self.W - 16, 18), Qt.AlignVCenter, self.spot.label)

        # 매핑값 / 안내
        p.setPen(QPen(_GREEN if self.mapping else _MUTED))
        f2 = QFont(); f2.setPointSize(8); p.setFont(f2)
        if not self.mappable:
            sub = "기본 클릭 (고정)"
        else:
            sub = self.mapping if self.mapping else "클릭해 단축키 설정"
        p.drawText(QRectF(8, 22, self.W - 16, 16), Qt.AlignVCenter, sub)

    def hoverEnterEvent(self, e) -> None:
        self._hover = True; self.update()

    def hoverLeaveEvent(self, e) -> None:
        self._hover = False; self.update()

    def mousePressEvent(self, e) -> None:
        if self.mappable:
            self.clicked.emit(self.spot.cid)
        super().mousePressEvent(e)


class MappingWindow(QWidget):
    """선택한 마우스의 도식 + 버튼 매핑 화면."""

    back = Signal()

    def __init__(self, mouse: MouseDevice, parent=None) -> None:
        super().__init__(parent)
        self.mouse = mouse
        self.mappings: dict[int, str] = {}
        self._labels: dict[int, ButtonLabelItem] = {}

        self.setWindowTitle(f"logitux — {mouse.codename}")
        self.setMinimumSize(620, 560)
        self.setStyleSheet(_WINDOW_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 헤더
        header = QWidget(); header.setObjectName("header")
        h = QHBoxLayout(header); h.setContentsMargins(16, 12, 16, 12)
        back_btn = QPushButton("← 뒤로"); back_btn.setObjectName("back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back.emit)
        title = QLabel(f"{mouse.codename}  ·  버튼을 눌러 단축키를 지정하세요")
        title.setObjectName("htitle")
        self._apply_btn = QPushButton("적용")
        self._apply_btn.setObjectName("apply")
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.clicked.connect(self._apply)
        h.addWidget(back_btn); h.addSpacing(8); h.addWidget(title, 1)
        h.addWidget(self._apply_btn)
        root.addWidget(header)

        # 도식 뷰
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setObjectName("diagram")
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        root.addWidget(self.view, 1)

        self._build_scene()
        self._restore_mappings()

    def _restore_mappings(self) -> None:
        """이전에 저장한 매핑을 불러와 라벨에 반영한다."""
        try:
            saved = load_saved_mappings(self.mouse.serial)
        except Exception:
            saved = {}
        for cid, seq in saved.items():
            self.mappings[cid] = seq
            label = self._labels.get(cid)
            if label:
                label.set_mapping(seq)

    def _build_scene(self) -> None:
        model = match_model(self.mouse)
        if model is None:
            self.scene.addText(
                f"{self.mouse.codename} 도식이 아직 없습니다.\n"
                "data/mice/ 에 모델 데이터를 추가하면 표시됩니다."
            ).setDefaultTextColor(_MUTED)
            return

        # 배경 도식: 실물 이미지(다운로드) 우선, 실패 시 generic SVG로 폴백
        if model.image_url:
            img = cached_image(model.image_url)
            if img:
                self.scene.addItem(QGraphicsPixmapItem(QPixmap(str(img))))
            else:
                generic = load_generic()
                if generic:
                    model = generic  # 좌표도 generic 것으로
        if not model.image_url and model.svg_path and model.svg_path.exists():
            self.scene.addItem(QGraphicsSvgItem(str(model.svg_path)))

        # 어떤 버튼이 매핑 가능한지 백엔드에서 조회 (cid → mappable)
        try:
            mappable = {b.cid: b.mappable for b in list_buttons(self.mouse)}
        except Exception:
            mappable = {}

        # 핫스팟 + 연결선 + 라벨
        for spot in model.spots:
            is_map = mappable.get(spot.cid, False)
            color = _BLUE if is_map else _GRAY

            # 연결선 (핫스팟 → 라벨 중심)
            pen = QPen(color, 1.4); pen.setStyle(Qt.DashLine)
            self.scene.addLine(spot.x, spot.y, spot.label_x, spot.label_y, pen)

            # 핫스팟 원
            r = 6
            self.scene.addEllipse(
                spot.x - r, spot.y - r, 2 * r, 2 * r,
                QPen(color, 2), QBrush(QColor(color.red(), color.green(), color.blue(), 90)),
            )

            # 라벨 박스 (label_x/y를 중심으로 배치)
            label = ButtonLabelItem(spot, is_map)
            label.setPos(spot.label_x - ButtonLabelItem.W / 2, spot.label_y - ButtonLabelItem.H / 2)
            label.clicked.connect(self._edit_mapping)
            self.scene.addItem(label)
            self._labels[spot.cid] = label

        margin = 20
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-margin, -margin, margin, margin))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if self.scene.items():
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def _edit_mapping(self, cid: int) -> None:
        label = self._labels.get(cid)
        if not label:
            return
        dlg = KeyCaptureDialog(label.spot.label, current=self.mappings.get(cid, ""), parent=self)
        if dlg.exec():
            seq = dlg.result_sequence
            if seq:
                self.mappings[cid] = seq
            else:
                self.mappings.pop(cid, None)
            label.set_mapping(seq)

    def _apply(self) -> None:
        """현재 매핑을 Solaar 백엔드에 적용하고 데몬을 재시작한다."""
        self._apply_btn.setEnabled(False)
        self._apply_btn.setText("적용 중…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            res = apply_mappings(self.mouse, self.mappings)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            self._apply_btn.setEnabled(True)
            self._apply_btn.setText("적용")
            QMessageBox.critical(self, "적용 실패", f"매핑 적용 중 오류가 발생했습니다.\n\n{e}")
            return
        QApplication.restoreOverrideCursor()
        self._apply_btn.setEnabled(True)
        self._apply_btn.setText("적용")

        lines = []
        if res.applied:
            names = ", ".join(
                f"{self._labels[c].spot.label}→{s}" for c, s in res.applied.items() if c in self._labels
            )
            lines.append(f"✅ 적용됨 ({len(res.applied)}): {names}")
        else:
            lines.append("적용된 매핑이 없습니다.")
        if res.skipped:
            sk = "\n".join(
                f"  · {self._labels[c].spot.label if c in self._labels else c}: {why}"
                for c, why in res.skipped
            )
            lines.append(f"\n⚠️ 건너뜀 ({len(res.skipped)}):\n{sk}")
        if not res.daemon_restarted:
            lines.append("\n❗ Solaar 데몬을 시작하지 못했습니다. solaar 설치를 확인하세요.")
        else:
            lines.append("\n버튼을 눌러 동작을 확인하세요.")
        if res.autostart_msg:
            lines.append(f"🔄 {res.autostart_msg}")
        if res.display_warning:
            lines.append(f"\n{res.display_warning}")

        box = QMessageBox(self)
        box.setWindowTitle("적용 결과")
        box.setIcon(QMessageBox.Warning if (res.skipped or not res.daemon_restarted) else QMessageBox.Information)
        box.setText("\n".join(lines))
        box.exec()


_WINDOW_STYLE = """
QWidget { background: #1e1f26; color: #e6e6ea; font-size: 14px; }
#header { background: #23242c; border-bottom: 1px solid #34353f; }
#htitle { color: #cfcfd6; font-size: 13px; }
#back { background: #34353f; color: #cfcfd6; border: none; border-radius: 8px;
        padding: 6px 14px; }
#back:hover { background: #3d3e49; }
#apply { background: #5b8cff; color: white; font-weight: 600; border: none;
         border-radius: 8px; padding: 6px 18px; }
#apply:hover { background: #6f9bff; }
#apply:disabled { background: #3a4156; color: #aab; }
#diagram { background: #1e1f26; border: none; }
"""
