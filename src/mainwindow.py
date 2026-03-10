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

from .playtest.notes import PlaytestNotesEdit
from .ws import WSProxy, OsuState
from .beatmap import BeatmapMetadata, BeatmapNotesCollection, StrainsData


class MainWindow(QMainWindow):
    def __init__(self, wsproxy: WSProxy):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._init_ui()
        self.resize(800, 640)
        self._old_pos = None

        self._wsproxy = wsproxy
        self._wsproxy.state_updated.connect(self.on_state_update)
        self._wsproxy.map_selected.connect(self.on_map_update)
        self._wsproxy.time_updated.connect(self.notes_edit.set_time)
        self._wsproxy.player_missed.connect(self.notes_edit.on_miss)

        self._osu_state = OsuState.UNKNOWN

        self._note_collection = BeatmapNotesCollection()
        self._note_collection.load()

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

        self.notes_edit = PlaytestNotesEdit(self)
        self.notes_edit.setObjectName('notes-edit')
        content_layout.addWidget(self.notes_edit)

        grip = QSizeGrip(self.content)
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(grip)
        content_layout.addLayout(grip_layout)

        main_layout.addWidget(self.content)

    def on_state_update(self, state: OsuState):
        time_tracked_states = [OsuState.GAMEPLAY, OsuState.GAMEPLAY_PAUSE, OsuState.GAMEPLAY_FAIL, OsuState.EDIT]
        if self._osu_state in time_tracked_states:
            if state not in time_tracked_states:
                self.notes_edit.graph.remove_pointer()
        elif state == OsuState.GAMEPLAY:
            self.notes_edit.init_gameplay()

        self._osu_state = state

        self.notes_edit.set_editor_mode(state == OsuState.EDIT)

    def on_map_update(self, metadata: BeatmapMetadata, strains: StrainsData):
        notes = self._note_collection.select_map(metadata)
        self.notes_edit.select_map(notes, strains)

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
        self._note_collection.save(ignore_list=['miss'])
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
