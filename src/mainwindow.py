from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSizeGrip
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

import sys
from typing import Iterable, Callable

from .playtest.comment import PlaytestCommentsEdit
from .ws import WSProxy, OsuState
from .beatmap.data import BeatmapMetadata, StrainsData
from .beatmap.comment import BeatmapCommentsCollection, set_ui, timed_osu_states

from .settings import settings
from .settings.gui import SettingsWindow

from .logger import configure_logging

configure_logging()


class Modifier:
    def __init__(self, filter_: Callable[[], bool]):
        self._filter = filter_
        self._applied = False

    def _apply(self, obj):
        raise NotImplementedError()

    def apply(self, obj):
        if self._filter():
            self._apply(obj)
            self._applied = True

    def _revert(self, obj):
        raise NotImplementedError()

    def revert(self, obj):
        if self._applied:
            self._revert(obj)
            self._applied = False


class StayOnTopModifier(Modifier):
    def _apply(self, obj: MainWindow):
        obj.stay_on_top = True

    def _revert(self, obj):
        obj.stay_on_top = False


class DeactivateCommentModifier(Modifier):
    def _apply(self, obj: MainWindow):
        obj.deactivate_comment_on_cursor_move = True

    def _revert(self, obj):
        obj.deactivate_comment_on_cursor_move = False


class Mode:
    def __init__(self, parent, modifiers: Iterable[Modifier]):
        self._parent = parent
        self._modifiers = list(modifiers)

    def enter(self):
        for mod in self._modifiers:
            mod.apply(self._parent)

    def exit(self):
        for mod in self._modifiers:
            mod.revert(self._parent)


class MainWindow(QMainWindow):
    def __init__(self, wsproxy: WSProxy):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._init_ui()
        self.resize(800, 840)
        self._old_pos = None

        set_ui(
            ui_edit=self.comments_edit.note_input,
            ui_containers=[
                self.comments_edit.graph,
                *self.comments_edit.markers
            ]
        )

        self._comment_collection = BeatmapCommentsCollection()
        self._comment_collection.load()

        for marker in self.comments_edit.markers:
            marker.new_marker_requested.connect(self._comment_collection.on_new_comment_request)

        self._wsproxy = wsproxy
        self._wsproxy.state_updated.connect(self.on_state_update)
        self._wsproxy.map_selected.connect(self.on_map_update)
        self._wsproxy.time_updated.connect(self.on_time_update)
        self._wsproxy.player_missed.connect(self._comment_collection.on_miss)

        self._osu_state = OsuState.UNKNOWN

        self._stay_on_top: bool = False
        self._deactivate_comment_on_cursor_move: bool = False

        self._playtest_mode = Mode(
            self,
            [DeactivateCommentModifier(lambda: settings.playtest_mode.deactivate_comment_on_resume)]
        )
        self._edit_mode = Mode(
            self,
            [
                DeactivateCommentModifier(lambda: settings.edit_mode.deactivate_comment_on_scroll),
                StayOnTopModifier(lambda: settings.edit_mode.stay_on_top)
            ]
        )
        self._cur_mode: Mode | None = None

        self._settings_window = None

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName('central')
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(42)
        self.title_bar.setObjectName('titlebar')

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)
        title_layout.setSpacing(8)

        self.title_label = QLabel('Modding Helper')
        self.title_label.setObjectName('title')
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        for symbol, name, slot in [
            ('−', 'btnMin', self.showMinimized),
            ('☐', 'btnMax', self.toggle_maximize),
            ('✕', 'btnClose', self.close)
        ]:
            btn = QPushButton(symbol)
            btn.setFixedSize(28, 28)
            btn.setObjectName(name)
            btn.clicked.connect(slot)
            title_layout.addWidget(btn)

        main_layout.addWidget(self.title_bar)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setObjectName('title-separator')
        main_layout.addWidget(separator)

        self.content = QWidget()
        self.content.setObjectName('content')
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(10, 0, 10, 11)

        self.comments_edit = PlaytestCommentsEdit(self)
        self.comments_edit.setObjectName('notes-edit')
        content_layout.addWidget(self.comments_edit)

        self.settings_button = QPushButton('⚙️')
        self.settings_button.clicked.connect(self.open_settings)

        grip = QSizeGrip(self.content)
        grip_layout = QHBoxLayout()
        grip_layout.addWidget(self.settings_button)
        grip_layout.addStretch()
        grip_layout.addWidget(grip)
        content_layout.addLayout(grip_layout)

        main_layout.addWidget(self.content)

        copy_action = QAction('Copy to clipboard', central_widget)
        copy_action.setShortcut(QKeySequence('Ctrl+C'))
        copy_action.triggered.connect(self.copy_current_comment)
        central_widget.addAction(copy_action)

        move_action = QAction('Move to current time', central_widget)
        move_action.setShortcut(QKeySequence('Ctrl+M'))
        move_action.triggered.connect(self.move_current_comment)
        central_widget.addAction(move_action)

    @property
    def stay_on_top(self):
        return self._stay_on_top

    @stay_on_top.setter
    def stay_on_top(self, value: bool):
        if value == self._stay_on_top:
            return
        self._stay_on_top = value

        self.hide()
        if value:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.showMinimized()
            self.clearFocus()

    @property
    def deactivate_comment_on_cursor_move(self):
        return self._deactivate_comment_on_cursor_move

    @deactivate_comment_on_cursor_move.setter
    def deactivate_comment_on_cursor_move(self, value: bool):
        self._deactivate_comment_on_cursor_move = value

    def set_mode(self, mode: Mode | None):
        if self._cur_mode is not None:
            self._cur_mode.exit()

        if mode is not None:
            mode.enter()

        self._cur_mode = mode

    def on_state_update(self, state: OsuState):
        if self._osu_state in timed_osu_states:
            if state not in timed_osu_states:
                self.comments_edit.graph.remove_pointer()
        self._osu_state = state

        if state == OsuState.GAMEPLAY:
            self.set_mode(self._playtest_mode)
        elif state == OsuState.EDIT:
            self.set_mode(self._edit_mode)
        else:
            self.set_mode(None)

    def on_map_update(self, metadata: BeatmapMetadata, strains: StrainsData):
        self.comments_edit.on_map_update(metadata, strains)
        self._comment_collection.select_map(metadata)

    def on_time_update(self, time_ms: int):
        if self._osu_state in timed_osu_states:
            self.comments_edit.graph.set_pointer(time_ms)
        self._comment_collection.on_activate_request(time_ms, self._deactivate_comment_on_cursor_move)

    def open_settings(self):
        if self._cur_mode is not None:
            self._cur_mode.exit()
        self._settings_window = SettingsWindow()
        self._settings_window.form.quit_requested.connect(self.close_settings)
        self._settings_window.show()

    def close_settings(self):
        self._settings_window = None
        if self._cur_mode is not None:
            self._cur_mode.enter()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self._old_pos = event.globalPosition().toPoint()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._old_pos = None

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def copy_current_comment(self):
        if self._comment_collection.current_map is None:
            return
        self._comment_collection.current_map.copy_comment()

    def move_current_comment(self):
        if self._comment_collection.current_map is None:
            return
        self._comment_collection.current_map.move_comment()

    def close(self):
        self._wsproxy.deleteLater()
        self._comment_collection.save()
        super().close()


def main():
    app = QApplication(sys.argv)

    with open('resources/style.qss', 'r') as f:
        style = f.read()
    app.setStyleSheet(style)

    window = MainWindow(WSProxy())
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
