from __future__ import annotations

import sys
from typing import ClassVar, Literal

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


Position = Literal[
    "center",
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]


class Notification(QWidget):
    _active_notifications: ClassVar[list["Notification"]] = []

    def __init__(
        self,
        message: str,
        duration: int = 4000,
        position: Position = "bottom-right",
        *,
        title: str = "تذكير",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not message.strip():
            raise ValueError("Notification message cannot be empty.")

        self.message = message.strip()
        self.title = title.strip()
        self.duration = max(1000, int(duration)) if duration else 0
        self.position = position
        self.margin = 24
        self.gap = 12
        self._closing = False

        self._setup_window()
        self._setup_ui()
        self._setup_timer()

        self._active_notifications.append(self)
        self._show_animated()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowOpacity(0)

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame(self)
        self.card.setObjectName("notificationCard")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.card.setStyleSheet(
            """
            #notificationCard {
                background-color: rgba(20, 24, 28, 238);
                border: 1px solid rgba(255, 255, 255, 38);
                border-radius: 14px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QPushButton#closeButton {
                background-color: rgba(255, 255, 255, 22);
                border: none;
                border-radius: 14px;
                color: white;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton#closeButton:hover {
                background-color: rgba(255, 255, 255, 45);
            }
            QPushButton#closeButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            """
        )

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 95))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.close_button = QPushButton("x")
        self.close_button.setObjectName("closeButton")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setToolTip("إغلاق")
        self.close_button.clicked.connect(self.fade_out)

        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.close_button, 0)

        self.message_label = QLabel(self.message)
        self.message_label.setFont(QFont("Segoe UI", 12))
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.message_label.setStyleSheet("color: rgba(255, 255, 255, 225);")

        card_layout.addLayout(header_layout)
        card_layout.addWidget(self.message_label)
        root_layout.addWidget(self.card)

    def _setup_timer(self) -> None:
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.fade_out)

    def _show_animated(self) -> None:
        width = self._notification_width()
        self.setFixedWidth(width)
        self.adjustSize()

        target_pos = self._target_position()
        start_pos = self._start_position(target_pos)
        self.move(start_pos)
        self.show()

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_animation.setDuration(220)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()

        self.slide_animation = QPropertyAnimation(self, b"pos", self)
        self.slide_animation.setDuration(260)
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(target_pos)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.start()

        if self.duration:
            self.close_timer.start(self.duration)

    def _screen_geometry(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No screen is available to show the notification.")
        return screen.availableGeometry()

    def _notification_width(self) -> int:
        geometry = self._screen_geometry()
        return max(280, min(420, geometry.width() - self.margin * 2))

    def _target_position(self) -> QPoint:
        geometry = self._screen_geometry()
        width = self.width()
        height = self.height()
        stack_offset = self._stack_offset()

        x_positions = {
            "left": geometry.left() + self.margin,
            "center": geometry.center().x() - width // 2,
            "right": geometry.right() - width - self.margin + 1,
        }
        y_positions = {
            "top": geometry.top() + self.margin + stack_offset,
            "center": geometry.center().y() - height // 2,
            "bottom": geometry.bottom() - height - self.margin - stack_offset + 1,
        }

        if self.position == "center":
            return QPoint(x_positions["center"], y_positions["center"])

        vertical, horizontal = self.position.split("-")
        return QPoint(x_positions[horizontal], y_positions[vertical])

    def _start_position(self, target_pos: QPoint) -> QPoint:
        if self.position.startswith("top"):
            return QPoint(target_pos.x(), target_pos.y() - 18)
        if self.position.startswith("bottom"):
            return QPoint(target_pos.x(), target_pos.y() + 18)
        return QPoint(target_pos.x(), target_pos.y() + 12)

    def _stack_offset(self) -> int:
        if self.position == "center":
            return 0

        return sum(
            notification.height() + self.gap
            for notification in self._active_notifications
            if notification is not self
            and not notification._closing
            and notification.position == self.position
        )

    def fade_out(self) -> None:
        if self._closing:
            return

        self._closing = True
        self.close_timer.stop()

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_animation.setDuration(220)
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()

    def closeEvent(self, event) -> None:
        self.close_timer.stop()
        self._forget()
        super().closeEvent(event)

    def _forget(self) -> None:
        if self in self._active_notifications:
            self._active_notifications.remove(self)


def main() -> int:
    app = QApplication(sys.argv)
    Notification(
        "حان الآن وقت أذكار المساء",
        title="أذكار المسلم",
        duration=4000,
        position="bottom-right",
    )
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
