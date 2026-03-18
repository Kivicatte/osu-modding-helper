from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from enum import IntEnum, StrEnum


class CommentType(StrEnum):
    UNDEFINED = 'undef'
    GENERAL = 'general'
    TIMELINE = 'timeline'
    MISS = 'miss'


timed_comment_types = [CommentType.TIMELINE, CommentType.MISS]


class CommentEditState(IntEnum):
    INIT = 0
    LOADED = 1
    EDITING = 2
    SAVED = 3


class CommentEditBase(QWidget):
    edit_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = CommentEditState.INIT
        self.on_state_change()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state: CommentEditState):
        if self._state != new_state:
            self._state = new_state
            self.on_state_change()

    def on_edit(self, text: str):
        self.state = CommentEditState.EDITING

    def on_save(self):
        self.edit_finished.emit(self.get_text())

    def on_state_change(self):
        raise NotImplementedError()

    def get_text(self) -> str:
        raise NotImplementedError()

    def set_text(self, text: str) -> None:
        self.state = CommentEditState.LOADED if text else CommentEditState.INIT

        # could use @abstractmethod but resolving metaclass conflict between ABC and QWidget is more pain
        if self.__class__ == CommentEditBase:
            raise NotImplementedError()

    def remove_text(self):
        self.set_text('')

    def save(self):
        self.state = CommentEditState.SAVED


class CommentUIElementBase(QWidget):
    activate_clicked = Signal()
    deactivate_clicked = Signal()
    delete_clicked = Signal()
    deleted = Signal()

    _ID = 0

    def __init__(self, type_: CommentType = CommentType.UNDEFINED, parent=None):
        super().__init__(parent)

        self._id = CommentUIElementBase._ID
        CommentUIElementBase._ID += 1

        self.setProperty('active', False)
        self.setProperty('type', type_)
        self._redraw()

    @property
    def id(self):
        return self._id

    def set_type(self, type_: CommentType):
        self.setProperty('type', type_)
        self._redraw()

    def activate(self):
        self.setProperty('active', True)
        self._redraw()

    def deactivate(self):
        self.setProperty('active', False)
        self._redraw()

    def on_activate(self):
        self.activate_clicked.emit()

    def on_toggle(self):
        if self.property('active'):
            self.on_deactivate()
        else:
            self.on_activate()

    def on_deactivate(self):
        self.deactivate_clicked.emit()

    def on_delete(self):
        self.delete_clicked.emit()
        self.deleteLater()

    def _redraw(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def deleteLater(self):
        self.deleted.emit()
        super().deleteLater()
