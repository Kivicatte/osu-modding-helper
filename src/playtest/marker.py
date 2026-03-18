from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSizePolicy, QWidget, QPushButton, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from ..utils import to_short_timestamp
from .base import CommentUIElementBase, CommentType, timed_comment_types


class Marker(CommentUIElementBase):
    def __init__(self, time_ms: int, type_: CommentType = CommentType.UNDEFINED, parent=None):
        super().__init__(type_, parent)

        self._init_ui()

        self.button.clicked.connect(self.on_toggle)
        self.delete_button.clicked.connect(self.on_delete)

        self._time_ms = time_ms
        self.set_text(to_short_timestamp(time_ms))

    def _init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName('timeline-marker-container')

        self.setFixedSize(100, 40)
        self.setContentsMargins(10, 0, 10, 0)

        layout = QHBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QPushButton()
        self.button.setObjectName('timeline-marker-label')
        self.button.setCheckable(True)
        self.button.setFixedSize(49, 40)
        layout.addWidget(self.button)

        self.separator = QWidget()
        self.separator.setObjectName('separator')
        self.separator.setFixedSize(1, 36)
        layout.addWidget(self.separator)

        self.delete_button = QPushButton('✕')
        self.delete_button.setObjectName('timeline-marker-delete')
        self.delete_button.setFixedSize(20, 20)
        layout.addWidget(self.delete_button)

    @property
    def time_ms(self):
        return self._time_ms

    def set_text(self, text: str):
        self.button.setText(text)


class SectionControls(QWidget):
    _BUTTON_SIZE = 30

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

    def _init_ui(self):
        self.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.add_button = QPushButton('+')
        self.add_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.add_button.setObjectName('add')
        self.layout().addWidget(self.add_button)

        self.clear_button = QPushButton('\U0001F5D1')
        self.clear_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.clear_button.setObjectName('clear')
        self.layout().addWidget(self.clear_button)


class MarkerSection(QScrollArea):
    new_marker_requested = Signal(int)

    def __init__(self, name: str, types: list[CommentType] = None, parent=None):
        super().__init__(parent)

        self.name = name
        self.types = types or []
        self._markers = {}

        self._init_ui()
        self._id_shift = self.layout.count() - 1

        self.controls.add_button.clicked.connect(self.on_marker_add)
        self.controls.clear_button.clicked.connect(self.on_marker_clear)

    def _init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(96)
        self.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget()
        self.setWidget(self.container)

        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.label = QLabel(f'{self.name}:')
        self.label.setObjectName('section-label')
        self.layout.addWidget(self.label)

        self.separator = QWidget()
        self.separator.setObjectName('separator')
        self.separator.setFixedWidth(1)
        self.layout.addWidget(self.separator)

        self.controls = SectionControls()
        self.layout.addWidget(self.controls)

        self.container.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

    def on_marker_add(self):
        self.new_marker_requested.emit(self.types[0])       # TODO: check if auto-converted to int

    def on_marker_clear(self):
        for marker in self._markers.values():
            marker.on_delete()

    def _get_key_index(self, marker: Marker) -> tuple[int, int]:
        if marker.property('type') in timed_comment_types:
            index = self._id_shift + sum(marker.time_ms > t for t in self._markers)
            key = marker.time_ms
        else:
            index = self.layout.count() - 1
            key = marker.id

        return key, index

    def create_marker(self, time_ms: int, type_: CommentType = CommentType.UNDEFINED) -> Marker:
        marker = Marker(time_ms, type_)
        marker.deleted.connect(self.remove_marker)

        key, index = self._get_key_index(marker)
        self._markers[key] = marker
        self.layout.insertWidget(index, marker)

        return marker

    def remove_marker(self, marker: Marker):
        key, index = self._get_key_index(marker)
        self._markers.pop(key)
        self.layout.removeWidget(marker)

    def get(self, time_ms: int) -> Marker | None:
        if self.types[0] in timed_comment_types:
            return self._markers.get(time_ms)

    def clear(self):
        ...             # TODO: figure our if necessary
