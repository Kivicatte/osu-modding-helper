import os
import sys


def to_osu_timestamp(time_ms: int):
    s, ms = divmod(time_ms, 1000)
    m, s = divmod(s, 60)

    return f'{m:0>2}:{s:0>2}:{ms:0>3}'


def to_short_timestamp(time_ms: int):
    s = time_ms // 1000
    m, s = divmod(s, 60)

    return f'{m}:{s:0>2}'


def call_osu(time_ms: int):
    if sys.platform != 'win32':
        return

    timestamp = to_osu_timestamp(time_ms)
    uri = f'osu://edit/{timestamp}'
    os.startfile(uri)
