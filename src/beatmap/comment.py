from __future__ import annotations

import os
import json

from collections.abc import ValuesView
from typing import Callable, Iterable

from .data import BeatmapMetadata
from ..settings import NOTES_PATH
from ..playtest.base import CommentEditBase, CommentUIElementBase, CommentType
from . import search


def _default_comment_filter(comment: Comment):
    return comment.type != CommentType.MISS and bool(comment.text)


class Comment:
    _ID: int = 0

    def __init__(
            self,
            text: str = '',
            time_ms: int = 0,
            type_: CommentType = CommentType.UNDEFINED,
            parent: BeatmapComments = None
    ):
        self.parent = parent
        self._id: int = Comment._ID
        Comment._ID += 1

        self._type = type_
        self._time_ms = time_ms
        self._text = text

        self._active: bool = False
        self._ui_edit: CommentEditBase | None = None
        self._ui_activation: list[CommentUIElementBase] = []

    @property
    def id(self):
        return self._id

    @property
    def active(self):
        return self._active

    @property
    def text(self):
        return self._text

    @property
    def time_ms(self):
        return self._time_ms

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, new_type: CommentType):
        self._type = new_type

        for ui in self._ui_activation:
            ui.set_type(new_type)

    def __str__(self):
        return self.text

    def register_edit_ui(self, ui: CommentEditBase):
        if self._ui_edit:
            self.unregister_edit_ui()

        self._ui_edit = ui
        ui.edit_finished.connect(self._set_text)

    def unregister_edit_ui(self):
        self._ui_edit.edit_finished.disconnect(self._set_text)
        self._ui_edit = None

    def register_activation_ui(self, ui: CommentUIElementBase):
        self._ui_activation.append(ui)
        ui.activate_clicked.connect(self.on_activate)
        ui.deactivate_clicked.connect(self.on_deactivate)
        ui.delete_clicked.connect(self.delete_activation_ui)
        ui.set_type(self._type)

    def unregister_activation_ui(self, ui: CommentUIElementBase):
        try:
            self._ui_activation.remove(ui)
            ui.activate_clicked.disconnect(self.on_activate)
            ui.deactivate_clicked.disconnect(self.on_deactivate)
            ui.delete_clicked.disconnect(self.delete_activation_ui)
        except ValueError:
            print('Attempted to unregister a comment UI element that was already not registered')

    def delete_activation_ui(self):
        for ui in list(self._ui_activation):
            self.unregister_activation_ui(ui)
            ui.deleteLater()

    def on_activate(self):
        self.parent.activate_comment(self)

    def on_deactivate(self):
        self.parent.deactivate_comment(self)

    def on_delete(self):
        self.parent.delete_comment(self)

    def activate(self):
        self._active = True
        self._ui_edit.set_text(self.text)
        for ui in self._ui_activation:
            ui.activate()

    def deactivate(self):
        self._active = False
        self._ui_edit.set_text('')
        for ui in self._ui_activation:
            ui.deactivate()

    def __del__(self):
        self.unregister_edit_ui()
        self.delete_activation_ui()

    def _set_text(self, text: str):         # works as a Qt slot rather than a setter, so no setter decorator
        self._text = text
        if self.type == CommentType.MISS and text != 'miss':
            self.type = CommentType.TIMELINE

    def to_dict(self):
        return {'type': self._type, 'time_ms': self._time_ms, 'text': self._text}

    @staticmethod
    def kw_from_dict(d: dict):
        return {'text': d['text'], 'time_ms': int(d['time_ms']), 'type_': CommentType(d['type'])}


class BeatmapComments:
    def __init__(self, metadata: BeatmapMetadata):
        self.metadata = metadata

        self._comments: dict[int, Comment] = {}
        self._active_comment: Comment | None = None

    def __iter__(self) -> ValuesView[Comment]:
        return self._comments.values()

    def is_empty(self):
        return any(filter(_default_comment_filter, self._comments.values()))

    def create_comment(self, **kw):
        comment = Comment(**kw)
        self._comments[comment.id] = comment

    def activate_comment(self, comment: Comment):
        if self._active_comment is comment:
            return
        if self._active_comment is not None:
            self.deactivate_comment(self._active_comment)
        comment.activate()
        self._active_comment = comment

    def deactivate_comment(self, comment: Comment):
        if self._active_comment is not comment:
            return
        comment.deactivate()
        self._active_comment = None

    def delete_comment(self, comment: Comment):
        if comment.active:
            self.deactivate_comment(comment)
        del self._comments[comment.id]

    def attach(
            self,
            edit_ui_callback: Callable[[Comment], CommentEditBase],
            activate_ui_callbacks: Iterable[Callable[[Comment], CommentUIElementBase]]
    ):
        for comment in self:
            edit_ui = edit_ui_callback(comment)
            comment.register_edit_ui(edit_ui)

            for activate_ui_callback in activate_ui_callbacks:
                activate_ui = activate_ui_callback(comment)
                comment.register_activation_ui(activate_ui)

    def detach(self):
        for comment in self:
            comment.unregister_edit_ui()
            comment.delete_activation_ui()

    @classmethod
    def from_dict(cls, d: dict):
        match d:
            case {
                'metadata': metadata,
                'comments': comments
            }:
                try:
                    metadata = BeatmapMetadata(**metadata)
                except TypeError:
                    raise ValueError(f'Corrupted beatmap metadata: {metadata}')

                obj = cls(metadata)
                try:
                    for comment_d in comments:
                        kw = Comment.kw_from_dict(comment_d)
                        obj.create_comment(**kw)
                except (KeyError, TypeError):
                    raise ValueError(f'Corrupted comment data: {comment_d}')

            case _:
                raise ValueError(f'Couldn\'t read beatmap comments from dictionary: {d}')

    def to_dict(self) -> dict:
        return {
            'metadata': self.metadata._asdict(),
            'comments': [comment.to_dict() for comment in self]
        }


class BeatmapCommentsCollection:
    def __init__(
            self,
            edit_ui_callback: Callable[[Comment], CommentEditBase],
            activate_ui_callbacks: Iterable[Callable[[Comment], CommentUIElementBase]]
    ):
        self._edit_ui_callback = edit_ui_callback
        self._activate_ui_callbacks = activate_ui_callbacks

        self._current_map: BeatmapComments | None = None

    def select_map(self, metadata: BeatmapMetadata, forget_current: bool = False):
        if self._current_map:
            self._current_map.detach()
            if not forget_current and not self._current_map.is_empty():
                search.add(self._current_map)

        if comments := search.search(metadata):
            search.remove(comments)
            comments.metadata = metadata
        else:
            comments = BeatmapComments(metadata)

        self._current_map = comments
        comments.attach(self._edit_ui_callback, self._activate_ui_callbacks)

        return self._current_map

    def save(self, path_: str = NOTES_PATH, forget_current: bool = False, ignore_list: list[str] = None):
        if self._current_map is not None and not forget_current and not self._current_map.is_empty():
            search.add(self._current_map)

        comments = [beatmap.to_dict(ignore_list) for beatmap in search.all_()]
        with open(path_, 'w') as f:
            json.dump(comments, f)

    def load(self, path_: str = NOTES_PATH):
        if os.path.isfile(path_):
            with open(path_, 'r') as f:
                comments = json.load(f)
        else:
            comments = []

        search.clear()
        for beatmap in comments:
            beatmap = BeatmapComments.from_dict(beatmap)
            search.add(beatmap)

        if self._current_map is not None:
            self._current_map.detach()
        self._current_map = None
