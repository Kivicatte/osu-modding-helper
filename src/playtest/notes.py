from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

import os

from .base import CommentEditBase, CommentEditState
from .info import ImageContainer, Credits
from .graph import StrainGraph
from .marker import MarkerSection
from ..beatmap.comment import BeatmapComments
from ..beatmap.data import StrainsData
from ..utils import call_osu
from .. import settings


class CommentEditLine(CommentEditBase):
    _status_text = {
        CommentEditState.INIT: '',
        CommentEditState.EDITING: '...',
        CommentEditState.SAVED: '✔',
        CommentEditState.LOADED: ''
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

        self.line_edit.textChanged.connect(self.on_edit)
        self.line_edit.returnPressed.connect(self.on_save)

    def _init_ui(self):
        self.setFixedHeight(50)
        self.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(50)
        self.line_edit.setPlaceholderText('Enter your note...')
        layout.addWidget(self.line_edit)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(50, 50)
        self.status_icon.setObjectName('note-edit-status')
        self.status_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_icon)

    def get_text(self) -> str:
        return self.line_edit.text()

    def set_text(self, text: str) -> None:
        super().set_text(text)
        self.line_edit.setText(text)

    def on_state_change(self):
        self.status_icon.setText(self._status_text[self.state])


class PlaytestNotesEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._init_ui()

        self.current_notes: BeatmapComments | None = None
        self._current_time: int = -1000000
        self._current_general_note: int | None = None
        self._last_miss: int = -1000000
        self._editor_mode = False

        self.note_input.returnPressed.connect(self._on_note_edit)

        self.timeline.general_marker.add_clicked.connect(self._on_general_note_added)
        self.timeline.general_marker.remove_clicked.connect(self._on_general_note_removed)
        self.timeline.general_marker.activate_clicked.connect(self._on_general_activated)

        self.timeline.timestamp_marker.activate_clicked.connect(self._on_timestamp_activated)
        self.timeline.timestamp_marker.remove_clicked.connect(self._on_timestamp_removed)
        self.timeline.timestamp_marker.visibility_toggled.connect(self.graph.set_bookmark_visibility)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 0)
        layout.setSpacing(10)

        beatmap_info_container = QWidget()
        beatmap_info_container.setContentsMargins(0, 0, 0, 0)
        beatmap_info_layout = QHBoxLayout(beatmap_info_container)
        beatmap_info_layout.setContentsMargins(10, 0, 10, 0)
        beatmap_info_layout.setSpacing(10)

        self.song_info = Credits('Song', 'Title', 'Artist')
        beatmap_info_layout.addWidget(self.song_info, stretch=1)
        self.song_info.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        bg = QPixmap(QImage(r'resources/osu_logo.png'))
        self.bg_image = ImageContainer(pixmap=bg)
        self.bg_image.setScaledContents(True)
        self.bg_image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        beatmap_info_layout.addWidget(self.bg_image, stretch=2)

        self.map_info = Credits('Beatmap', 'Difficulty', 'Mapper')
        beatmap_info_layout.addWidget(self.map_info, stretch=1)
        self.map_info.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        layout.addWidget(beatmap_info_container, stretch=1)

        self.note_input = NoteEditLine()
        layout.addWidget(self.note_input)

        self.graph = StrainGraph()
        self.graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.graph, stretch=1)

        self.timeline = MarkerSection()
        layout.addWidget(self.timeline)

    def set_time(self, time_ms: int):
        self._current_time = time_ms

        comment = self.current_notes.get_timeline_note(time_ms) or ''
        self.note_input.setText(comment)

        self.timeline.deselect()
        self._current_general_note = None
        if self.timeline.timestamp_exists(time_ms):
            self.timeline.activate_timestamp_marker(time_ms)

        self.graph.set_pointer(time_ms)

    def _on_note_edit(self):
        note = self.note_input.text()
        if not note:
            return

        if self._current_general_note is not None:
            self.current_notes.add_general_note(note, self._current_general_note)
            return

        if not self.current_notes.get_timeline_note(self._current_time):
            self.graph.add_bookmark(self._current_time)
            self.timeline.add_timestamp_marker(self._current_time)
            self.timeline.activate_timestamp_marker(self._current_time)
            self._current_general_note = None

        self.current_notes.add_timeline_note(self._current_time, note)

    def _on_general_note_added(self, id_: int):
        self.current_notes.add_general_note('', id_)
        self._current_general_note = id_

    def _on_timestamp_activated(self, time_ms: int):
        self._current_time = time_ms
        self._current_general_note = None
        self.graph.set_pointer(time_ms)

        comment = self.current_notes.get_timeline_note(time_ms) or ''
        self.note_input.setText(comment)

    def _on_general_activated(self, id_: int):
        self._current_general_note = id_

        comment = self.current_notes.get_general_note(id_) or ''
        self.note_input.setText(comment)

    def _on_timestamp_removed(self, time_ms: int):
        self.current_notes.pop_timeline_note(time_ms)
        self.graph.remove_bookmark(time_ms)

    def _on_general_note_removed(self, id_: int):
        self.current_notes.pop_general_note(id_)

    def on_miss(self, time_ms: int):
        if self._last_miss + settings.MISS_MARK_COOLDOWN_MS > time_ms:
            return

        self.graph.add_miss_mark(time_ms)
        self.timeline.add_miss_marker(time_ms)
        self.current_notes.add_timeline_note(time_ms, 'miss')
        self._last_miss = time_ms

    def clear_notes(self):
        self.note_input.setText('')
        self.graph.clear_bookmarks()
        self.timeline.clear()
        self.current_notes = None

    def load_notes(self):
        if self.current_notes is None:
            return

        for t in self.current_notes:
            self.graph.add_bookmark(t)
            self.timeline.add_timestamp_marker(t)

        ids = [self.timeline.add_general_marker() for _ in self.current_notes.general_notes()]
        self.current_notes.set_general_ids(ids)

    def select_map(self, notes: BeatmapComments, strains: StrainsData):
        metadata = notes.metadata

        self.song_info.set_title(metadata.title)
        self.song_info.set_artist(metadata.artist)

        self.map_info.set_title(metadata.difficulty)
        self.map_info.set_artist(metadata.mapper)

        bg_path = os.path.join(metadata.bg)
        bg = QPixmap.fromImage(QImage(bg_path))
        self.bg_image.setPixmap(bg)

        self.clear_notes()
        self.current_notes = notes
        self.graph.plot(strains)
        self.load_notes()

    def init_gameplay(self):
        self._last_miss = -1000000
        self.timeline.clear_miss_markers()

    def set_editor_mode(self, editor_mode: bool = True):
        if editor_mode and not self._editor_mode:
            self.timeline.timestamp_marker.activate_clicked.connect(call_osu)
        elif not editor_mode and self._editor_mode:
            self.timeline.timestamp_marker.activate_clicked.disconnect(call_osu)

        self._editor_mode = editor_mode
