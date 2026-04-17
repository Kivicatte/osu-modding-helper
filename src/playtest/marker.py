from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSizePolicy, QWidget, QPushButton, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, Signal

from ..utils import to_short_timestamp
from .base import CommentUIElement, CommentUIContainer, CommentType, timed_comment_types


class Marker(CommentUIElement):
    def __init__(self, time_ms: int, type_: CommentType = CommentType.UNDEFINED, parent=None):
        super().__init__(type_, parent)

        self._init_ui()

        self.button.clicked.connect(self.on_toggle)
        self.delete_button.clicked.connect(self.on_delete)

        self._time_ms = time_ms

        text = to_short_timestamp(time_ms) if type_ in timed_comment_types else '--:--'
        self.set_text(text)

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

        self.context_menu = QMenu(self)
        self.context_menu.addAction('Copy to clipboard').triggered.connect(self.copy_message)
        if self.property('type') in timed_comment_types:
            self.context_menu.addAction('Move to current time').triggered.connect(lambda: self.move_to_timestamp())

    @property
    def time_ms(self):
        return self._time_ms

    def set_text(self, text: str):
        self.button.setText(text)

    def copy_message(self):
        self.copy_requested.emit()

    def move_to_timestamp(self, time_ms: int = -1):
        self.move_requested.emit(time_ms)

    def contextMenuEvent(self, event):
        self.context_menu.exec(event.globalPos())


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


class MarkerSection(CommentUIContainer, QScrollArea):
    new_marker_requested = Signal(str)

    def __init__(self, name: str, types: list[CommentType] = None, parent=None):
        self.name = name
        self.types = types or []
        self._markers = {}

        QScrollArea.__init__(self, parent)
        CommentUIContainer.__init__(
            self,
            factory=Marker,
            filter_=lambda t, type_: type_ in self.types
        )

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
        self.label.setFixedWidth(60)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
        self.new_marker_requested.emit(self.types[0])

    def on_marker_clear(self):
        for marker in list(self._markers.values()):
            marker.on_delete()

    def _get_key_index(self, marker: Marker) -> tuple[int, int]:
        if marker.property('type') in timed_comment_types:
            index = self._id_shift + sum(marker.time_ms > t for t in self._markers)
            key = marker.time_ms
        else:
            index = self.layout.count() - 1
            key = marker.id

        return key, index

    def _add(self, ui_element: Marker):
        super()._add(ui_element)

        key, index = self._get_key_index(ui_element)
        self._markers[key] = ui_element
        self.layout.insertWidget(index, ui_element)

        ui_element.activated.connect(lambda: self.show_marker(ui_element))

    def _remove(self, ui_element: Marker):
        super()._remove(ui_element)

        key, index = self._get_key_index(ui_element)
        self._markers.pop(key)
        self.layout.removeWidget(ui_element)

    def show_marker(self, marker: Marker, margin: int = 20):
        rect = marker.geometry()
        x_left = rect.left() - margin
        x_right = rect.right() - self.viewport().width() + margin
        current_x = self.horizontalScrollBar().value()

        if current_x > x_left:
            self.horizontalScrollBar().setValue(max(x_left, 0))
        elif current_x < x_right:
            self.horizontalScrollBar().setValue(min(x_right, self.widget().width() - self.viewport().width()))
