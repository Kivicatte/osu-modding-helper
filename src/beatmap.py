import os
import json
import itertools as it
from collections import namedtuple
from typing import Iterable

from .settings import NOTES_PATH


BeatmapMetadata = namedtuple(
    'BeatmapMetadata', [
        'artist',
        'artistOriginal',
        'title',
        'titleOriginal',
        'difficulty',
        'mapper',
        'folder',
        'file',
        'bg',
        'audio',
        'md5'
    ]
)


class StrainsData:
    def __init__(self, xaxis: list[int], strains: list[float]):
        self.xaxis = list(xaxis)
        self.strains = [max(d, 0) for d in strains]         # remove negative values

        if len(xaxis) < 2:
            return

        # add one trailing 0
        self.xaxis.append(self.xaxis[-1] * 2 - self.xaxis[-2])
        self.strains.append(0)

        # remove redundant trailing 0s (if there's more than one)
        for i in range(len(strains) - 1, 0, -1):
            if strains[i] > 0:
                break
        self.xaxis = self.xaxis[:i + 2]
        self.strains = self.strains[:i + 2]

    @classmethod
    def from_dict(cls, strains: dict):
        match strains:
            case {
                'series': [{
                               'name': 'strains',
                               'data': data
                           }],
                'xaxis': xaxis
            }:
                return cls(xaxis, data)
            case _:
                return cls([], [])


class BeatmapNotes:
    def __init__(self, metadata: BeatmapMetadata):
        self.metadata = metadata
        self._timeline = {}
        self._general = {}

    def add_timeline_note(self, time_ms: int, note: str):
        self._timeline[time_ms] = note

    def get_timeline_note(self, time_ms: int):
        return self._timeline.get(time_ms)

    def pop_timeline_note(self, time_ms: int):
        if time_ms in self._timeline:
            return self._timeline.pop(time_ms)

    def update_timeline(self, source: Iterable[tuple[int, str]]):
        for t, n in source:
            self.add_timeline_note(t, n)

    def add_general_note(self, note: str, id_: int = None):
        if id_ is None:
            id_ = max(self._general) + 1
        self._general[id_] = note
        return id_

    def get_general_note(self, id_: int):
        return self._general.get(id_)

    def pop_general_note(self, id_: int):
        if id_ not in self._general:
            return
        return self._general.pop(id_)

    def set_general_ids(self, ids: list[int]):
        if len(ids) != len(self._general):
            raise IndexError(f'Wrong number of ids provided: {len(ids)} ids for {len(self._general)} notes')

        self._general = dict(zip(ids, self._general.values()))

    def general_notes(self):
        return [n for n in self._general.values() if n]

    def clear(self):
        self._timeline.clear()
        self._general.clear()

    def __setitem__(self, key, value):
        self.add_timeline_note(key, value)

    def __getitem__(self, item):
        return self.get_timeline_note(item)

    def __delitem__(self, key):
        self.pop_timeline_note(key)

    def __iter__(self):
        return self._timeline.__iter__()

    def __bool__(self):
        return bool(self._timeline) or bool(self._general)

    def items_timeline(self):
        return self._timeline.items()

    def to_dict(self, ignore_list: list[str] = None):
        ignore_list = ignore_list or []
        d = self.metadata._asdict()
        d['notes'] = {t: n for t, n in self._timeline.items() if n not in ignore_list}
        d['notes']['general'] = self.general_notes()
        return d

    @classmethod
    def from_dict(cls, d: dict):
        notes_ = d.pop('notes')
        metadata = BeatmapMetadata(**d)
        notes = cls(metadata)
        if 'general' in notes_:
            notes._general = dict(zip(it.count(), notes_.pop('general')))
        for t, n in notes_.items():
            notes._timeline[int(t)] = n      # json converts int keys to str, have to convert back
        return notes


class BeatmapNotesCollection:
    def __init__(self):
        self._content = {}
        self._current_notes: BeatmapNotes = None

    def select_map(self, metadata: BeatmapMetadata, forget_current: bool = False):
        if self._current_notes and not forget_current:
            self._content[self._current_notes.metadata.md5] = self._current_notes

        if metadata.md5 in self._content:
            self._current_notes = self._content.pop(metadata.md5)
        else:
            self._current_notes = BeatmapNotes(metadata)

        return self._current_notes

    def save(self, path_: str = NOTES_PATH, forget_current: bool = False, ignore_list: list[str] = None):
        if self._current_notes and not forget_current:
            self._content[self._current_notes.metadata.md5] = self._current_notes

        notes = [n.to_dict(ignore_list) for n in self._content.values()]
        with open(path_, 'w') as f:
            json.dump(notes, f)

    def load(self, path_: str = NOTES_PATH):
        if os.path.isfile(path_):
            with open(path_, 'r') as f:
                notes = json.load(f)
        else:
            notes = []

        self._content.clear()
        for n in notes:
            n = BeatmapNotes.from_dict(n)
            self._content[n.metadata.md5] = n

        if not self._current_notes:
            return

        self._current_notes.clear()
        cur_md5 = self._current_notes.metadata.md5
        if cur_md5 in self._content:
            notes = self._content.pop(cur_md5)
            self._current_notes.update_timeline(notes.items_timeline())
