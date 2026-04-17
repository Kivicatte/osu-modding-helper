import os
import sys

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QCursor

from .settings import settings


def to_osu_timestamp(time_ms: int):
    s, ms = divmod(time_ms, 1000)
    m, s = divmod(s, 60)

    return f'{m:0>2}:{s:0>2}:{ms:0>3}'


def to_short_timestamp(time_ms: int):
    s = time_ms // 1000
    m, s = divmod(s, 60)

    return f'{m}:{s:0>2}'


def call_osu(time_ms: int):
    if sys.platform != 'win32':
        return

    timestamp = to_osu_timestamp(time_ms)
    uri = f'osu://edit/{timestamp}'
    os.startfile(uri)


def display_popup(message: str):
    if not settings.show_popup_messages:
        return

    popup = QWidget()
    popup.setObjectName('popup')
    popup.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.ToolTip
    )
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    layout = QVBoxLayout(popup)
    layout.setContentsMargins(0, 0, 0, 0)

    label = QLabel(message)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft)
    label.setContentsMargins(5, 5, 5, 5)
    layout.addWidget(label)

    pos = QCursor.pos()
    final_pos = QPoint(pos.x() + 5, pos.y() - 25)
    start_pos = QPoint(final_pos.x(), final_pos.y() + 8)
    popup.move(start_pos)

    opacity_effect = QGraphicsOpacityEffect(popup)
    opacity_effect.setOpacity(0.0)
    popup.setGraphicsEffect(opacity_effect)

    def fade_in():
        popup.show()

        fade_animation = QPropertyAnimation(opacity_effect, b'opacity')
        fade_animation.setDuration(200)
        fade_animation.setStartValue(0.0)
        fade_animation.setEndValue(1.0)
        fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_animation.start()

        slide_animation = QPropertyAnimation(popup, b"pos")
        slide_animation.setDuration(200)
        slide_animation.setStartValue(start_pos)
        slide_animation.setEndValue(final_pos)
        slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide_animation.start()

        popup._fade_in_animation = fade_animation
        popup._slide_animation = slide_animation

    def fade_out():
        animation = QPropertyAnimation(opacity_effect, b'opacity')
        animation.setDuration(200)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()
        popup._fade_out_animation = animation
        QTimer.singleShot(200, popup.close)

    fade_in()
    QTimer.singleShot(500, fade_out)
    popup.mousePressEvent = lambda event: fade_out()

    return popup
