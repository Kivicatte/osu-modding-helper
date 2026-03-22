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

import sys

from .playtest.base import CommentType
from .playtest.comment import PlaytestCommentsEdit
from .ws import WSProxy, OsuState
from .beatmap.data import BeatmapMetadata, StrainsData
from .beatmap.comment import BeatmapCommentsCollection, set_ui, timed_osu_states


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
        self._wsproxy.player_missed.connect(lambda _: self._comment_collection.on_new_comment_request(CommentType.MISS))

        self._osu_state = OsuState.UNKNOWN

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

        self.title_label = QLabel('Modding Notes')
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

        grip = QSizeGrip(self.content)
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(grip)
        content_layout.addLayout(grip_layout)

        main_layout.addWidget(self.content)

    def on_state_update(self, state: OsuState):
        if self._osu_state in timed_osu_states:
            if state not in timed_osu_states:
                self.comments_edit.graph.remove_pointer()
        self._osu_state = state

    def on_map_update(self, metadata: BeatmapMetadata, strains: StrainsData):
        self._comment_collection.select_map(metadata)
        self.comments_edit.on_map_update(metadata, strains)

    def on_time_update(self, time_ms: int):
        if self._osu_state in timed_osu_states:
            self.comments_edit.graph.set_pointer(time_ms)
        self._comment_collection.on_activate_request(time_ms)

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

    def close(self):
        self._wsproxy.deleteLater()
        self._comment_collection.save(ignore_list=['miss'])
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
