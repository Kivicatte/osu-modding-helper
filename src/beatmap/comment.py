from __future__ import annotations

import os
import json
import pyperclip

from ..ws import State, OsuState
from .data import BeatmapMetadata
from ..settings import settings
from ..playtest.base import CommentEditBase, CommentUIElement, CommentUIContainer, CommentType, timed_comment_types
from . import search
from ..utils import call_osu, to_osu_timestamp, display_popup

import logging


timed_osu_states = [
    OsuState.GAMEPLAY,
    OsuState.GAMEPLAY_PAUSE,
    OsuState.GAMEPLAY_FAIL,
    OsuState.EDIT
]


_ui_edit: CommentEditBase | None = None
_ui_containers: list[CommentUIContainer] = []


def set_ui(ui_edit: CommentEditBase, ui_containers: list[CommentUIContainer]):
    global _ui_edit
    _ui_edit = ui_edit
    _ui_containers.clear()
    _ui_containers.extend(ui_containers)


def _default_comment_filter(comment: Comment):
    if settings.save_options.ignore_empty_comments and not comment.text:
        return False
    if settings.save_options.ignore_default_miss_comments and comment.type == CommentType.MISS and comment.text == 'miss':
        return False
    return True


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
        self._ui_activation: list[CommentUIElement] = []

    @property
    def id(self):
        return self._id

    @property
    def active(self):
        return self._active

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        self._text = text
        if self.type == CommentType.MISS and text != 'miss':
            self.type = CommentType.TIMELINE

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

    def register_activation_ui(self, ui: CommentUIElement):
        self._ui_activation.append(ui)
        ui.activate_clicked.connect(self.on_activate)
        ui.deactivate_clicked.connect(self.on_deactivate)
        ui.delete_clicked.connect(self.on_delete)
        ui.move_requested.connect(self.on_move)
        ui.copy_requested.connect(self.copy_message)
        ui.set_type(self._type)

    def unregister_activation_ui(self, ui: CommentUIElement):
        try:
            self._ui_activation.remove(ui)
            ui.activate_clicked.disconnect(self.on_activate)
            ui.deactivate_clicked.disconnect(self.on_deactivate)
            ui.delete_clicked.disconnect(self.on_delete)
            ui.move_requested.disconnect(self.on_move)
            ui.copy_requested.disconnect(self.copy_message)
        except ValueError:
            logging.log(logging.WARNING, 'Attempted to unregister a comment UI element that was not registered')

    def delete_activation_ui(self):
        for ui in list(self._ui_activation):
            ui.activate_clicked.disconnect(self.on_activate)
            ui.deactivate_clicked.disconnect(self.on_deactivate)
            ui.delete_clicked.disconnect(self.on_delete)
            ui.deleteLater()
        self._ui_activation.clear()

    def on_activate(self):
        self.parent.activate_comment(self)

    def on_deactivate(self):
        self.parent.deactivate_comment(self)

    def on_move(self, time_ms: int = -1):
        self.parent.move_comment(self, time_ms)

    def on_delete(self):
        self.parent.delete_comment(self)

    def activate(self):
        self._active = True
        for ui in self._ui_activation:
            ui.activate()

    def deactivate(self):
        self._active = False
        for ui in self._ui_activation:
            ui.deactivate()

    def copy_message(self):
        if self._type in timed_comment_types:
            pyperclip.copy(f'{to_osu_timestamp(self._time_ms)} - {self._text.capitalize()}')
        else:
            pyperclip.copy(self._text.capitalize())
        display_popup('Copied!')

    def to_dict(self):
        return {'type': self._type, 'time_ms': self._time_ms, 'text': self._text}

    @staticmethod
    def from_dict(d: dict) -> Comment:
        return Comment(d['text'], d['time_ms'], CommentType(d['type']))


class BeatmapComments:
    def __init__(self, metadata: BeatmapMetadata):
        self.metadata = metadata

        self._ui_edit: CommentEditBase | None = None
        self._ui_containers: list[CommentUIContainer] = []

        self._comments: dict[int, Comment] = {}
        self._timestamps: dict[int, Comment] = {}
        self._active_comment: Comment | None = None

    def is_empty(self, strict: bool = False):
        if len(self._comments) == 0:
            return True
        if strict:
            return False

        return not any(filter(_default_comment_filter, self._comments.values()))

    def create_comment(self, text: str = '', type_: CommentType = CommentType.UNDEFINED) -> Comment | None:
        if State.time_ms in self._timestamps and type_ in timed_comment_types:
            return

        comment = Comment(text, State.time_ms, type_, self)
        self._add_comment(comment)
        self.activate_comment(comment)
        return comment

    def _add_comment(self, comment: Comment):
        if comment.type in timed_comment_types:
            self._timestamps[comment.time_ms] = comment
        self._comments[comment.id] = comment
        self._attach_comment(comment)

    def _attach_comment(self, comment):
        for ui_container in self._ui_containers:
            activation_ui = ui_container.create_ui_element(comment.time_ms, comment.type)
            if activation_ui is not None:
                comment.register_activation_ui(activation_ui)

    def attach(self):
        self._ui_edit = _ui_edit
        self._ui_edit.edit_finished.connect(self.on_comment_edit)
        self._ui_containers.extend(_ui_containers)

        for comment in self._comments.values():
            self._attach_comment(comment)

    def detach(self):
        self._ui_edit.edit_finished.disconnect(self.on_comment_edit)
        for comment in self._comments.values():
            comment.delete_activation_ui()
        self._ui_edit = None
        self._ui_containers.clear()

    def activate_comment(self, comment: Comment):
        if (
                State.osu_state == OsuState.EDIT and
                comment.type in timed_comment_types and
                State.time_ms != comment.time_ms
        ):
            call_osu(comment.time_ms)
        if self._active_comment is comment:
            return
        if self._active_comment is not None:
            self.deactivate_comment(self._active_comment)
        comment.activate()
        self._active_comment = comment
        self._ui_edit.set_text(comment.text)

    def deactivate_comment(self, comment: Comment = None):
        comment = comment or self._active_comment
        if self._active_comment is not comment or comment is None:
            return
        comment.deactivate()
        self._active_comment = None
        self._ui_edit.set_text('')

    def try_activate_at(self, time_ms: int, deactivate_on_fail: bool = False):
        comment = self._timestamps.get(time_ms)
        if comment is not None:
            self.activate_comment(comment)
        elif deactivate_on_fail:
            self.deactivate_comment()

    def copy_comment(self, comment: Comment | None = None):
        comment = comment or self._active_comment
        if comment is not None:
            comment.copy_message()

    def move_comment(self, comment: Comment | None = None, time_ms: int = -1):
        comment = comment or self._active_comment
        if comment is None:
            return

        if time_ms == -1:
            time_ms = State.time_ms

        self.delete_comment(comment)
        moved_comment = Comment(comment.text, time_ms, comment.type, self)
        self._add_comment(moved_comment)
        self.activate_comment(moved_comment)

        display_popup('Moved!')

    def on_comment_edit(self, text: str):
        if self._active_comment is None:
            self.create_comment(text, CommentType.TIMELINE)
        elif self._active_comment.type == CommentType.MISS:
            self.delete_comment(self._active_comment)
            comment = self.create_comment(text, CommentType.TIMELINE)
            self.activate_comment(comment)
        else:
            self._active_comment.text = text
        self._ui_edit.save()

    def delete_comment(self, comment: Comment):
        if comment.active:
            self.deactivate_comment(comment)
        if comment.type in timed_comment_types:
            self._timestamps.pop(comment.time_ms)
        self._comments[comment.id].delete_activation_ui()
        self._comments.pop(comment.id)

    @classmethod
    def from_dict(cls, d: dict) -> BeatmapComments:
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
                        comment = Comment.from_dict(comment_d)
                        comment.parent = obj
                        obj._add_comment(comment)
                except (KeyError, TypeError):
                    raise ValueError(f'Corrupted comment data: {comment_d}')

            case _:
                raise ValueError(f'Couldn\'t read beatmap comments from dictionary: {d}')
        return obj

    def to_dict(self) -> dict:
        return {
            'metadata': self.metadata._asdict(),
            'comments': [comment.to_dict() for comment in filter(_default_comment_filter, self._comments.values())]
        }


class BeatmapCommentsCollection:
    def __init__(self):
        self._current_map: BeatmapComments | None = None
        self._last_miss: int | None = None

    @property
    def current_map(self):
        return self._current_map

    def on_new_comment_request(self, type_: CommentType = CommentType.UNDEFINED) -> Comment | None:
        if self._current_map is None:
            return

        if type_ == CommentType.MISS:
            return self._current_map.create_comment('miss', type_)

        if type_ == CommentType.UNDEFINED:
            type_ = CommentType.TIMELINE if State.osu_state in timed_osu_states else CommentType.GENERAL
        return self._current_map.create_comment('', type_)

    def on_activate_request(self, time_ms: int, deactivate_on_fail: bool):
        if self._current_map is None:
            return

        self._current_map.try_activate_at(
            time_ms=time_ms,
            deactivate_on_fail=deactivate_on_fail
        )

    def on_miss(self, time_ms: int):
        if (
                self._last_miss is None or
                not settings.playtest_mode.merge_chain_misses or
                time_ms - self._last_miss > settings.playtest_mode.chain_miss_cooldown__ms
        ):
            self._current_map.create_comment('miss', CommentType.MISS)
            self._last_miss = time_ms

    def select_map(self, metadata: BeatmapMetadata, forget_current: bool = False):
        self._last_miss = None

        if self._current_map:
            self._current_map.deactivate_comment()
            self._current_map.detach()
            if not forget_current and not self._current_map.is_empty(strict=True):
                search.add(self._current_map)

        if comments := search.search(metadata):
            search.remove(comments)
            comments.metadata = metadata
        else:
            comments = BeatmapComments(metadata)

        self._current_map = comments
        comments.attach()

        return self._current_map

    def save(self, path_: str = settings.save_options.output_file, forget_current: bool = False):
        if self._current_map is not None and not forget_current and not self._current_map.is_empty():
            search.add(self._current_map)

        comments = [beatmap.to_dict() for beatmap in search.all_()]
        with open(path_, 'w') as f:
            json.dump(comments, f)

    def load(self, path_: str = settings.save_options.output_file):
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
