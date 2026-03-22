from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

from .base import CommentEditBase, CommentEditState, CommentType
from .info import ImageContainer, Credits
from .graph import StrainGraph
from .marker import MarkerSection
from ..beatmap.comment import BeatmapComments, BeatmapMetadata
from ..beatmap.data import StrainsData


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


class PlaytestCommentsEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._init_ui()

        self.current_notes: BeatmapComments | None = None
        self._current_time: int = -1000000
        self._current_general_note: int | None = None
        self._last_miss: int = -1000000
        self._editor_mode = False

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

        self.note_input = CommentEditLine()
        layout.addWidget(self.note_input)

        self.markers = [
            MarkerSection('General', [CommentType.GENERAL]),
            MarkerSection('Timeline', [CommentType.TIMELINE]),
            MarkerSection('Miss', [CommentType.MISS])
        ]
        for marker in self.markers:
            layout.addWidget(marker)

        self.graph = StrainGraph()
        self.graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.graph, stretch=1)

    def on_map_update(self, metadata: BeatmapMetadata, strains: StrainsData):
        self.song_info.set_title(metadata.title)
        self.song_info.set_artist(metadata.artist)
        self.map_info.set_title(metadata.difficulty)
        self.map_info.set_artist(metadata.mapper)

        self.bg_image.setPixmap(QPixmap(QImage(metadata.bg)))

        self.graph.plot(strains)
