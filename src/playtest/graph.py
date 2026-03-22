from PySide6.QtCore import Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backend_bases import MouseEvent, PickEvent
import numpy as np

from enum import Enum
from dataclasses import dataclass, field
from typing import ClassVar

from ..beatmap.data import StrainsData
from .base import CommentUIElement, CommentUIContainer, CommentType, timed_comment_types


@dataclass
class LineStyle:
    default: ClassVar[dict] = {
        'linewidth': 1,
        'linestyle': '-',
        'alpha': 0.9
    }

    base: dict = field(default_factory=dict)
    active: dict = field(default_factory=dict)

    def __post_init__(self):
        self.base = self.default | self.base
        self.active = self.base | self.active


class LineStyles(Enum):
    PLOT = LineStyle(
        base={'color': '#ccaa33'}
    )
    CURSOR = LineStyle(
        base={'color': '#68c627', 'linewidth': 2}
    )
    BOOKMARK = LineStyle(
        base={'color': '#4a90e2'},
        active={'linewidth': 2}
    )
    MISS = LineStyle(
        base={'color': '#cc2222'},
        active={'linewidth': 2}
    )


comment_styles = {
    CommentType.TIMELINE: LineStyles.BOOKMARK.value,
    CommentType.MISS: LineStyles.MISS.value
}


class VLine(CommentUIElement):
    def __init__(self, time_ms: int, type_: CommentType, canvas: FigureCanvas):
        self._time_ms = time_ms
        self._canvas = canvas

        style = comment_styles[type_]
        self._style = style
        self._focused = False

        self._line = canvas.figure.axes[0].axvline(
            x=time_ms,
            zorder=9,
            picker=3,
            **self._style.base
        )

        self._cids = [
            canvas.mpl_connect('motion_notify_event', self._on_motion),
            canvas.mpl_connect('pick_event', self._on_pick)
        ]

        super().__init__(type_, parent=None)

    def set_type(self, type_: CommentType):
        style = comment_styles[type_]
        self._style = style

        super().set_type(type_)

    def _set_focus(self, focused: bool = True):
        if self._focused == focused:
            return
        self._focused = focused
        self._redraw()

    def _on_motion(self, event: MouseEvent):
        if event.inaxes != self._line.axes:
            self._set_focus(False)
            return

        contains, _ = self._line.contains(event)
        self._set_focus(contains)

    def _on_pick(self, event: PickEvent):
        if event.artist is self._line:
            self.on_toggle()

    def _redraw(self):
        style = self._style.active if self.property('active') or self._focused else self._style.base
        self._line.set(**style)
        self._canvas.draw_idle()

    def deleteLater(self):
        for cid in self._cids:
            self._canvas.mpl_disconnect(cid)
        self._line.remove()
        self._canvas.draw_idle()
        super().deleteLater()


class StrainGraph(CommentUIContainer, FigureCanvas):
    def __init__(self):
        self.figure = Figure(facecolor='none')

        FigureCanvas.__init__(self, self.figure)
        CommentUIContainer.__init__(
            self,
            factory=lambda *args: VLine(*args, canvas=self),
            filter_=lambda t, type_: type_ in timed_comment_types
        )

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

        self._plot_style = LineStyles.PLOT.value
        self._cursor_style = LineStyles.CURSOR.value
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
                zorder=10,
                **self._cursor_style.base
            )
        else:
            self._pointer.set_xdata([time, time])

        self.draw()

    def remove_pointer(self):
        if self._pointer is not None:
            self._pointer.remove()
            self._pointer = None

        self.draw()

    def plot(self, strains: StrainsData):
        if len(strains.xaxis) < 2:
            return
        time_points = strains.xaxis
        strains = strains.strains

        self.axes.cla()
        self.axes.plot(time_points, strains, **self._plot_style.base)

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
