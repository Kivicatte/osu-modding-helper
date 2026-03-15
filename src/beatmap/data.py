from dataclasses import dataclass
from collections import namedtuple


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
        'md5',
        'id',
        'setid'
    ]
)


@dataclass
class BeatmapInfo:
    metadata: BeatmapMetadata
    strains: StrainsData
