import os
import json
from enum import IntEnum

from PySide6.QtCore import QObject, QThread, Signal, QUrl
from PySide6.QtWebSockets import QWebSocket

from .beatmap import BeatmapMetadata


class OsuState(IntEnum):
    MAIN_MENU = 0
    EDIT = 1
    GAMEPLAY = 2
    MAP_SELECT_EDIT = 4
    MAP_SELECT_PLAY = 5
    RESULT_SCREEN = 7

    GAMEPLAY_PAUSE = 100
    GAMEPLAY_FAIL = 101
    UNKNOWN = 1000


_url: str = 'ws://localhost:24050/ws'
_state: OsuState = OsuState.MAIN_MENU
_time_ms: int = -1000000


class WSWorker(QObject):
    message_received = Signal(object)       # dict
    finished = Signal()

    def __init__(self, url: str = _url):
        super().__init__()

        self._url = QUrl(url)
        self._ws = None

    def on_message(self, message: str):
        message = json.loads(message)
        self.message_received.emit(message)

    def on_error(self, error):
        raise ConnectionError(self._ws.errorString())

    def run(self):
        self._ws = QWebSocket()
        self._ws.textMessageReceived.connect(self.on_message)
        self._ws.errorOccurred.connect(self.on_error)
        self._ws.open(self._url)

    def stop(self):
        self._ws.close()
        self.finished.emit()


class WSProxy(QObject):
    time_updated = Signal(int)                      # emitted only while playing or editing
    player_missed = Signal(int)
    state_updated = Signal(int)
    map_selected = Signal(object, list, list)       # BeatmapMetadata, lists of timings and strain values

    def __init__(self):
        super().__init__()

        self._init_ws()

        self._state = OsuState.MAIN_MENU
        self._time_ms = -1000000
        self._combo = 0
        self._map_md5 = ''

    def _init_ws(self):
        self._wsthread = QThread()
        self._wsworker = WSWorker()
        self._wsworker.moveToThread(self._wsthread)

        self._wsthread.started.connect(self._wsworker.run)
        self._wsworker.message_received.connect(self.on_first_message)
        self._wsworker.finished.connect(self._wsthread.quit)

        self._wsthread.start()

    def update_state(self, state: OsuState | int):
        if state == OsuState.GAMEPLAY:
            self._combo = 0
        try:
            self._state = OsuState(state)
            self.state_updated.emit(int(state))
        except ValueError:
            if self._state != OsuState.UNKNOWN:
                self._state = OsuState.UNKNOWN
                print(f'Unknown osu state occurred: {state}')
                self.state_updated.emit(OsuState.UNKNOWN)

    def update_time(self, time_ms: int):
        if self._time_ms == time_ms:
            return

        self._time_ms = time_ms
        if self._state in [OsuState.GAMEPLAY, OsuState.EDIT]:
            self.time_updated.emit(time_ms)

    def update_combo(self, combo: int, time_ms: int):
        if self._combo > combo:
            self.player_missed.emit(time_ms)

        self._combo = combo

    def update_map(self, message: dict):
        bm = message['menu']['bm']
        md5 = bm['md5']
        self._map_md5 = md5

        metadata = {}
        metadata.update(bm['metadata'])
        metadata.update(bm['path'])
        metadata.pop('full')        # tosu doesn't handle this correctly
        metadata['bg'] = os.path.join(message['settings']['folders']['songs'], metadata['folder'], metadata['bg'])
        metadata['md5'] = md5
        metadata = BeatmapMetadata(**metadata)

        strains = message['menu']['pp']['strainsAll']
        timings = strains['xaxis'].copy()
        data = [d if d > 0 else 0 for d in strains['series'][0]['data']]    # change weird -100 points to 0
        self.map_selected.emit(metadata, timings, data)

    def on_first_message(self, message: dict):
        # making sure state and map (if applicable) are initialized before timings
        # otherwise this crashes when you start the program while playing or editing
        self._wsworker.message_received.disconnect(self.on_first_message)

        self.update_state(message['menu']['state'])
        if self._state != OsuState.UNKNOWN:
            self.update_map(message)

        self._wsworker.message_received.connect(self.on_message)

    def on_message(self, message: dict):
        state = message['menu']['state']
        time_ms = message['menu']['bm']['time']['current']

        # trackable state change
        if (state != self._state and
                (state != OsuState.GAMEPLAY or self._state not in [OsuState.GAMEPLAY_PAUSE, OsuState.GAMEPLAY_FAIL])):
            self.update_state(state)

        # pausing / failing
        elif state == OsuState.GAMEPLAY and self._time_ms == time_ms:
            if message['gameplay']['hp']['normal']:
                self.update_state(OsuState.GAMEPLAY_PAUSE)
            else:
                self.update_state(OsuState.GAMEPLAY_FAIL)

        # unpausing
        elif self._state == OsuState.GAMEPLAY_PAUSE and time_ms != self._time_ms:
            self.update_state(OsuState.GAMEPLAY)

        # selecting a map
        elif state in [OsuState.MAP_SELECT_PLAY, OsuState.MAP_SELECT_EDIT, OsuState.MAIN_MENU]:
            if message['menu']['bm']['md5'] != self._map_md5:
                self.update_map(message)

        self.update_time(time_ms)
        if self._state == OsuState.GAMEPLAY:
            self.update_combo(message['gameplay']['combo']['current'], time_ms)

    def deleteLater(self):
        self._wsworker.stop()
        super().deleteLater()
