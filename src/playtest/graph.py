from PySide6.QtCore import Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from enum import StrEnum


class GraphColors(StrEnum):
    PLOT = '#ccaa33'
    CURSOR = '#68c627'
    BOOKMARK = '#4a90e2'
    MISS = '#cc2222'


class StrainGraph(FigureCanvas):
    def __init__(self):
        self.figure = Figure(facecolor='none')
        super().__init__(self.figure)

        self.axes = self.figure.add_subplot()
        self.axes.set_facecolor('none')
        for spine in ['left', 'top', 'right', 'bottom']:
            self.axes.spines[spine].set_visible(False)
        self.axes.set_position([0.03, 0.11, 0.94, 0.85])
        self.axes.tick_params(
            axis='both',
            which='both',
            bottom=False, top=False, left=False, right=False,
            labelbottom=False, labelleft=False
        )
        self.axes.set_yticklabels([])

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet('background-color: transparent;')

        self._pointer = None
        self._bookmarks = {}

    @property
    def pointer_position(self):
        if self._pointer is None:
            return 0
        return self._pointer.get_xdata()[0]

    def set_pointer(self, time: int):
        if self._pointer is None:
            self._pointer = self.axes.axvline(
                x=time,
                color=GraphColors.CURSOR,
                linewidth=2,
                linestyle='-',
                alpha=0.9,
                zorder=10
            )
        else:
            self._pointer.set_xdata([time, time])

        self.draw()

    def remove_pointer(self):
        if self._pointer is not None:
            self._pointer.remove()
            self._pointer = None

        self.draw()

    def add_bookmark(self, time: int, /, color=GraphColors.BOOKMARK):
        bookmark = self.axes.axvline(
            x=time,
            color=color,
            linewidth=1.2,
            linestyle='-',
            alpha=0.9,
            zorder=9
        )

        self._bookmarks[time] = bookmark
        self.draw()

    def add_miss_mark(self, time: int):
        self.add_bookmark(time, color=GraphColors.MISS)

    def remove_bookmark(self, time: int = None):
        if time is None:
            time = self.pointer_position
        if time in self._bookmarks:
            self._bookmarks[time].remove()
            del self._bookmarks[time]
            self.draw()

    def set_bookmark_visibility(self, time: int = None, visible: bool = True):
        if time is None:
            time = self.pointer_position
        if time in self._bookmarks:
            self._bookmarks[time].set_visible(visible)
            self.draw()

    def clear_bookmarks(self):
        for bookmark in self._bookmarks.values():
            bookmark.remove()
        self._bookmarks.clear()

        self.draw()

    def plot(self, time_points: list[int], strains: list[float]):
        # tosu sometimes adds a bunch of 0s at the end
        for i in range(len(strains) - 1, 0, -1):
            if strains[i] > 0:
                break
        time_points = time_points[:i + 2]
        strains = strains[:i + 2]

        # ... and sometimes doesn't
        if strains[-1]:
            time_points.append(time_points[-1] * 2 - time_points[-2])
            strains.append(0)

        self.axes.cla()
        self.axes.plot(time_points, strains, color=GraphColors.PLOT)

        # TODO: handle loooooooooooooooooooong maps
        self.axes.set_xlim(-10, time_points[-1] + 10)
        self.axes.set_xticks(list(range(0, time_points[-1], 30000)))
        to_label = lambda x: f'{x // 2}:30' if x % 2 else f'{x // 2}:00'
        self.axes.set_xticklabels([to_label(x) for x in range(time_points[-1] // 30000 + 1)])

        ymin = -max(strains) * 0.005
        ymax = max(strains) * 1.01 + 0.0001
        self.axes.set_ylim(ymin, ymax)
        self.axes.set_yticks(np.linspace(0, ymax, 5))

        self.axes.minorticks_on()
        self.axes.grid(which='major', color='#888888', linestyle='-', linewidth=0.5, alpha=0.9)
        self.axes.grid(which='minor', color='#333333', linestyle='-', linewidth=0.4, alpha=0.7)

        self.axes.tick_params(
            axis='x',
            which='major',
            labelcolor='#aaaaaa',
            labelsize=10,
            labelbottom=True
        )

        self.draw()
