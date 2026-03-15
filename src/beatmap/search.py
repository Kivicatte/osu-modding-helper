from dataclasses import dataclass
from typing import Callable, Hashable, Protocol, ValuesView

from .data import BeatmapMetadata


@dataclass
class BeatmapSearchStrategy:
    name: str
    extract: Callable[[BeatmapMetadata], Hashable | None]
    on_hit: Callable[[BeatmapMetadata], None] = lambda m: None
    on_miss: Callable[[BeatmapMetadata], None] = lambda m: None


class HasMetadata(Protocol):
    metadata: BeatmapMetadata


@dataclass
class _MetadataContainer:
    metadata: BeatmapMetadata | None = None


_metadata_container = _MetadataContainer()


_search_strategies = [
    BeatmapSearchStrategy(
        'md5',
        lambda m: m.md5,
    ),
    BeatmapSearchStrategy(
        'ID',
        lambda m: m.id if m.id > 0 else None,
    ),
    BeatmapSearchStrategy(
        'path',
        lambda m: (m.folder, m.file),
    )
]


_dicts = [{} for strat in _search_strategies]


def add(beatmap: HasMetadata):
    for strat, d in zip(_search_strategies, _dicts):
        marker = strat.extract(beatmap.metadata)
        if marker is not None:
            d[marker] = beatmap


def remove(beatmap: HasMetadata):
    for strat, d in zip(_search_strategies, _dicts):
        marker = strat.extract(beatmap.metadata)
        if marker is not None:
            d.pop(marker)


def update(old_metadata: BeatmapMetadata, new_beatmap: HasMetadata):
    _metadata_container.metadata = old_metadata
    remove(_metadata_container)
    add(new_beatmap)


def search(metadata: BeatmapMetadata) -> HasMetadata | None:
    for strat, d in zip(_search_strategies, _dicts):
        if beatmap := d.get(strat.extract(metadata)):
            return beatmap


def all_() -> ValuesView[HasMetadata]:
    return _dicts[0].values()


def clear():
    for d in _dicts:
        d.clear()
