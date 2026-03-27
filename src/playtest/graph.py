from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backend_bases import MouseEvent, PickEvent
import numpy as np

from enum import Enum
from dataclasses import dataclass, field
from typing import ClassVar

from ..beatmap.data import StrainsData
from .base import CommentUIElement, CommentUIContainer, CommentType, timed_comment_types


_SCALE_MIN = 1.0
_SCALE_MAX = 20.0


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
    def __init__(self, time_ms: int, type_: CommentType, canvas: StrainGraph):
        self._time_ms = time_ms
        self._canvas = canvas
        self._canvas.add_line(self)

        style = comment_styles[type_]
        self._style = style
        self._focused = False

        self._line = canvas.figure.axes[0].axvline(
            x=time_ms,
            zorder=9,
            picker=2,
            **self._style.base
        )

        self._cids = [
            canvas.mpl_connect('pick_event', self._on_pick)
        ]

        super().__init__(type_, parent=None)

    @property
    def time_ms(self):
        return self._time_ms

    @property
    def line(self):
        return self._line

    def set_type(self, type_: CommentType):
        style = comment_styles[type_]
        self._style = style

        super().set_type(type_)

    def set_focus(self, focused: bool = True):
        if self._focused == focused:
            return
        self._focused = focused
        self._redraw()

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
        self._canvas.remove_line(self)

        try:
            self._line.remove()
        except NotImplementedError:         # already removed
            pass

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
        self.axes.set_position([0.03, 0.15, 0.94, 0.85])
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
        self._focus: VLine | None = None
        self._lines = set()
        self._scale = 1.0

        self._cids = [
            self.mpl_connect('motion_notify_event', self._on_motion),
            self.mpl_connect('scroll_event', self.on_scroll)
        ]

    def _on_motion(self, event: MouseEvent):
        if event.inaxes != self.axes:
            self.set_focus(None)
            return

        lines_contain = [line for line in self._lines if line.line.contains(event)[0]]
        match len(lines_contain):
            case 0:
                self.set_focus(None)
            case 1:
                self.set_focus(lines_contain[0])
            case _:
                line = min(lines_contain, key=lambda l: abs(l.time_ms - self._focus.time_ms)) if self._focus \
                    else lines_contain[0]
                self.set_focus(line)

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

    def set_focus(self, line: VLine | None):
        if self._focus is line:
            return

        if self._focus is not None:
            self._focus.set_focus(False)
        self._focus = line
        if line is not None:
            line.set_focus(True)

    def add_line(self, line: VLine):
        self._lines.add(line)

    def remove_line(self, line: VLine):
        if line in self._lines:
            self._lines.remove(line)

    def plot(self, strains: StrainsData):
        if len(strains.xaxis) < 2:
            return
        time_points = strains.xaxis
        strains = strains.strains

        self.axes.cla()
        self.axes.plot(time_points, strains, **self._plot_style.base)

        self.axes.set_xlim(-10, time_points[-1] + 10)
        self.axes.set_xticks(list(range(0, time_points[-1], 30000)))
        to_label = lambda x: f'{x // 2}:30' if x % 2 else f'{x // 2}:00'
        self.axes.set_xticklabels([to_label(x) for x in range(time_points[-1] // 30000 + 1)])

        ymin = -max(strains) * 0.01
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

        self._scale = 1.0
        self.draw()

    def set_scale(self, scale: float = 1.0, pivot: float | None = None):
        scale = min(
            max(
                _SCALE_MIN,
                scale
            ),
            _SCALE_MAX
        )

        mult = self._scale / scale
        if abs(mult - 1) < 0.001:
            return

        cur_x_min, cur_x_max = self.axes.get_xlim()
        center_x = (cur_x_max + cur_x_min) / 2
        new_x_max = cur_x_min + (cur_x_max - cur_x_min) * mult
        self.axes.set_xlim(cur_x_min, new_x_max)

        if pivot is None:
            self.center_at(center_x)
        else:
            new_center = pivot + (center_x - pivot) * mult
            self.center_at(new_center)

        self._scale = scale

    def zoom_in(self, factor: float = 1.2, pivot: float | None = None):
        self.set_scale(self._scale * factor, pivot)

    def zoom_out(self, factor: float = 1.2, pivot: float | None = None):
        self.set_scale(self._scale / factor, pivot)

    def center_at(self, center_x: float):
        xdata = self.axes.lines[0].get_xdata()
        x_min = xdata[0]
        x_max = xdata[-1]       # strains data is always ordered

        cur_x_min, cur_x_max = self.axes.get_xlim()
        cur_w = cur_x_max - cur_x_min
        center_x = min(
            max(
                x_min + cur_w / 2,
                center_x
            ),
            x_max - cur_w / 2
        )

        self.axes.set_xlim(center_x - cur_w / 2, center_x + cur_w / 2)
        self.draw_idle()

    def move_right(self, dx: float = 0.1):
        cur_x_min, cur_x_max = self.axes.get_xlim()
        new_center = cur_x_min + (cur_x_max - cur_x_min) * (0.5 + dx)
        self.center_at(new_center)

    def move_left(self, dx: float = 0.1):
        cur_x_min, cur_x_max = self.axes.get_xlim()
        new_center = cur_x_min + (cur_x_max - cur_x_min) * (0.5 - dx)
        self.center_at(new_center)

    def on_scroll(self, event):
        if event.inaxes != self.axes:
            return

        modifiers = event.guiEvent.modifiers() if hasattr(event, 'guiEvent') else None
        if not modifiers:
            return

        if modifiers & Qt.ControlModifier:
            if event.button == 'up':
                self.zoom_in(pivot=event.xdata)
            elif event.button == 'down':
                self.zoom_out(pivot=event.xdata)
        elif modifiers & Qt.ShiftModifier:
            if event.button == 'up':
                self.move_left()
            elif event.button == 'down':
                self.move_right()

    def __del__(self):
        for cid in self._cids:
            self._canvas.mpl_disconnect(cid)


class NavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(20)
        self.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        layout.addStretch()

        self.left_button = QPushButton('←')
        self.left_button.setToolTip('Shift + scroll up')
        self.left_button.setAutoRepeat(True)

        self.right_button = QPushButton('→')
        self.right_button.setToolTip('Shift + scroll down')
        self.right_button.setAutoRepeat(True)

        self.zoom_in_button = QPushButton('+')
        self.zoom_in_button.setToolTip('Ctrl + scroll up')

        self.zoom_out_button = QPushButton('-')
        self.zoom_out_button.setToolTip('Ctrl + scroll down')

        self.reset_zoom_button = QPushButton('☐')

        for button in [
                self.left_button,
                self.zoom_in_button,
                self.reset_zoom_button,
                self.zoom_out_button,
                self.right_button
        ]:
            button.setFixedSize(20, 20)
            button.setObjectName('graph-navigation-button')
            layout.addWidget(button)

        layout.addStretch()


class StrainGraphArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._init_ui()

        self.panel.left_button.clicked.connect(lambda: self.graph.move_left(0.25))
        self.panel.right_button.clicked.connect(lambda: self.graph.move_right(0.25))
        self.panel.zoom_in_button.clicked.connect(lambda: self.graph.zoom_in())
        self.panel.zoom_out_button.clicked.connect(lambda: self.graph.zoom_out())
        self.panel.reset_zoom_button.clicked.connect(lambda: self.graph.set_scale(1.0))

    def _init_ui(self):
        self.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.graph = StrainGraph()
        layout.addWidget(self.graph)

        self.panel = NavigationPanel()
        layout.addWidget(self.panel)
