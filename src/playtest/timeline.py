from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSizePolicy, QWidget, QPushButton, QButtonGroup, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QObject

from ..utils import to_short_timestamp


class TimelineMarkerBase(QWidget):
    _ID = 0
    checked = Signal(object)
    deleted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

        self._id = TimelineMarkerBase._ID       # same ID counter for all children
        TimelineMarkerBase._ID += 1

        self.setProperty('checked', False)
        self.button.toggled.connect(self._set_checked)
        self.button.clicked.connect(self._on_click)
        self.delete_button.clicked.connect(self._on_delete)

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

    def _set_checked(self, checked: bool):
        self.setProperty('checked', checked)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _on_click(self):
        if self.button.isChecked():
            self.checked.emit(self)

    def _on_delete(self):
        self.deleted.emit(self)             # actual deletion handled by the parent widget

    @property
    def id(self):
        return self._id

    def set_text(self, text: str):
        self.button.setText(text)


class TimestampMarker(TimelineMarkerBase):
    def __init__(self, time_ms: int, parent=None):
        super().__init__(parent)

        self.set_text(to_short_timestamp(time_ms))
        self._time_ms = time_ms

    @property
    def time_ms(self):
        return self._time_ms


class MissMarker(TimestampMarker):
    def __init__(self, time_ms: int, parent=None):
        super().__init__(time_ms, parent)

        self.setObjectName('miss-marker-container')


class GeneralMarker(TimelineMarkerBase):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_text('Note')


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


class GeneralSectionControls(SectionControls):
    def _init_ui(self):
        super()._init_ui()

        self.add_button = QPushButton('+')
        self.add_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.add_button.setObjectName('add')
        self.layout().addWidget(self.add_button)

        self.clear_button = QPushButton('\U0001F5D1')
        self.clear_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.clear_button.setObjectName('clear')
        self.layout().addWidget(self.clear_button)


class TimelineSectionControls(SectionControls):
    def _init_ui(self):
        super()._init_ui()

        self.track_misses_button = QPushButton('✔')
        self.track_misses_button.setCheckable(True)
        self.track_misses_button.setChecked(True)
        self.track_misses_button.setObjectName('miss')
        self.track_misses_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.layout().addWidget(self.track_misses_button)

        self.clear_button = QPushButton('\U0001F5D1')
        self.clear_button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        self.clear_button.setObjectName('clear')
        self.layout().addWidget(self.clear_button)

        self.track_misses_button.toggled.connect(self.set_misses_tracked)

    def set_misses_tracked(self, misses_tracked: bool):
        if misses_tracked:
            self.track_misses_button.setText('✔')
        else:
            self.track_misses_button.setText('✕')


class MarkerSignals(QObject):
    add_clicked = Signal(int)
    remove_clicked = Signal(int)
    activate_clicked = Signal(int)
    added = Signal(int)
    removed = Signal(int)
    activated = Signal(int)
    visibility_toggled = Signal(int, bool)


class Timeline(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

        self._general_markers = {}
        self._timestamp_markers = {}
        self._miss_markers = {}
        self._btngroup = QButtonGroup()
        self._btngroup.setExclusive(True)

        self.general_marker = MarkerSignals()
        self.timestamp_marker = MarkerSignals()

        self.general_controls.add_button.clicked.connect(self._on_general_marker_create)
        self.general_controls.clear_button.clicked.connect(self._on_general_clear)

        self.timeline_controls.track_misses_button.clicked.connect(self.toggle_miss_marker_visibility)
        self.timeline_controls.clear_button.clicked.connect(self._on_timeline_clear)

        self._general_id_shift = 1
        self._timeline_id_shift = 4

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

        self.general_label = QLabel('General:')
        self.general_label.setObjectName('timeline-section-label')
        self.layout.addWidget(self.general_label)

        self.general_controls = GeneralSectionControls()
        self.layout.addWidget(self.general_controls)

        self.separator = QWidget()
        self.separator.setObjectName('separator')
        self.separator.setFixedWidth(1)
        self.layout.addWidget(self.separator)

        self.timeline_label = QLabel('Timeline:')
        self.timeline_label.setObjectName('timeline-section-label')
        self.layout.addWidget(self.timeline_label)

        self.timeline_controls = TimelineSectionControls()
        self.layout.addWidget(self.timeline_controls)

        self.container.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

    def add_general_marker(self):
        marker = GeneralMarker()
        self.layout.insertWidget(self._general_id_shift + len(self._general_markers), marker)

        self._general_markers[marker.id] = marker
        self._btngroup.addButton(marker.button)

        marker.checked.connect(self._on_marker_activate)
        marker.deleted.connect(self._on_marker_remove)
        self.general_marker.added.emit(marker.id)

        return marker.id

    def add_timestamp_marker(self, time_ms: int, /, type_: type = TimestampMarker):
        if time_ms in self._timestamp_markers:
            return

        marker = type_(time_ms)
        index = (
            self._timeline_id_shift +
            len(self._general_markers) +
            sum(time_ms > t for t in self._timestamp_markers)
        )
        self.layout.insertWidget(index, marker)

        self._timestamp_markers[time_ms] = marker
        self._btngroup.addButton(marker.button)

        marker.checked.connect(self._on_marker_activate)
        marker.deleted.connect(self._on_marker_remove)
        self.timestamp_marker.added.emit(time_ms)

    def add_miss_marker(self, time_ms: int):
        self.add_timestamp_marker(time_ms, type_=MissMarker)
        if not self.timeline_controls.track_misses_button.isChecked():
            self._timestamp_markers[time_ms].hide()
            self.timestamp_marker.visibility_toggled.emit(time_ms, False)

    def remove_general_marker(self, id_: int):
        if id_ not in self._general_markers:
            raise ValueError(f'Attempted to remove non-existing general marker, id: {id_}')

        marker = self._general_markers.pop(id_)
        self.layout.removeWidget(marker)
        self._btngroup.removeButton(marker.button)
        marker.deleteLater()

        self.general_marker.removed.emit(id_)

    def remove_timestamp_marker(self, time_ms: int):
        if time_ms not in self._timestamp_markers:
            raise ValueError(f'Attempted to remove non-existing timestamp marker at {time_ms} ms')

        marker = self._timestamp_markers.pop(time_ms)
        self.layout.removeWidget(marker)
        self._btngroup.removeButton(marker.button)
        marker.deleteLater()

        self.timestamp_marker.removed.emit(time_ms)

    def activate_general_marker(self, id_: int):
        marker = self._general_markers[id_]
        if marker.button.isChecked:
            return

        marker.button.toggle()
        self.general_marker.activated.emit(id_)

    def activate_timestamp_marker(self, time_ms: int):
        marker = self._timestamp_markers[time_ms]
        if marker.button.isChecked():
            return

        marker.button.toggle()
        self.timestamp_marker.activated.emit(time_ms)

    def _on_general_marker_create(self):
        id_ = self.add_general_marker()
        self.general_marker.add_clicked.emit(id_)   # cannot get id earlier, so "added" will emit before "add_clicked"

    def _on_timestamp_marker_create(self, time_ms: int):
        self.timestamp_marker.add_clicked.emit(time_ms)
        self.add_timestamp_marker(time_ms)

    def _on_marker_remove(self, marker: TimelineMarkerBase):
        if isinstance(marker, TimestampMarker):
            self.timestamp_marker.remove_clicked.emit(marker.time_ms)
            self.remove_timestamp_marker(marker.time_ms)
        elif isinstance(marker, GeneralMarker):
            self.general_marker.remove_clicked.emit(marker.id)
            self.remove_general_marker(marker.id)
        else:
            raise TypeError(f'Unknown marker type: {marker.__class__}')

    def _on_marker_activate(self, marker: TimelineMarkerBase):
        if isinstance(marker, TimestampMarker):
            self.timestamp_marker.activate_clicked.emit(marker.time_ms)
            self.timestamp_marker.activated.emit(marker.time_ms)
        elif isinstance(marker, GeneralMarker):
            self.general_marker.activate_clicked.emit(marker.id)
            self.general_marker.activated.emit(marker.id)
        else:
            raise TypeError(f'Unknown marker type: {marker.__class__}')

    def _on_general_clear(self):
        for marker in list(self._general_markers.values()):
            self._on_marker_remove(marker)

    def _on_timeline_clear(self):
        for marker in list(self._timestamp_markers.values()):
            self._on_marker_remove(marker)

    def hide_miss_markers(self):
        for marker in self._timestamp_markers.values():
            if isinstance(marker, MissMarker):
                marker.hide()
                self.timestamp_marker.visibility_toggled.emit(marker.time_ms, False)

    def show_miss_markers(self):
        for marker in self._timestamp_markers.values():
            if isinstance(marker, MissMarker):
                marker.show()
                self.timestamp_marker.visibility_toggled.emit(marker.time_ms, True)

    def clear_miss_markers(self):
        for marker in list(self._timestamp_markers.values()):
            if isinstance(marker, MissMarker):
                self._on_marker_remove(marker)

    def toggle_miss_marker_visibility(self, visible: bool):
        if visible:
            self.show_miss_markers()
        else:
            self.hide_miss_markers()

    def timestamp_exists(self, time_ms):
        return time_ms in self._timestamp_markers

    def deselect(self):
        selected = self._btngroup.checkedButton()
        if selected:
            self._btngroup.setExclusive(False)
            selected.toggle()
            self._btngroup.setExclusive(True)

    def clear(self):
        i = 0
        while self.layout.count() > i:
            item = self.layout.itemAt(i)
            marker = item.widget()
            if not marker or not isinstance(marker, TimelineMarkerBase):
                i += 1
                continue

            if isinstance(marker, TimestampMarker):
                self.remove_timestamp_marker(marker.time_ms)
            elif isinstance(marker, GeneralMarker):
                self.remove_general_marker(marker.id)
            else:
                raise TypeError(f'Unknown marker type: {marker.__class__}')
