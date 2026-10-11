"""Latest game frame as plain text. Map.show is captured here, not printed."""

import re
import threading

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_lock = threading.Lock()
_frame = "Game has not started."


def set_frame(text: str) -> None:
    global _frame
    with _lock:
        _frame = text


def get_frame() -> str:
    with _lock:
        return _frame


def _visible(cell: str) -> str:
    text = _ANSI.sub("", cell)
    return text[-1] if text else " "


def _capture(game_map) -> None:
    lines = [
        "".join(_visible(cell) for cell in row) for row in game_map.map
    ]
    set_frame("\n".join(lines))


def install_show_patch(map_cls) -> None:
    def show(self, init=False):
        del init
        _capture(self)

    map_cls.show = show
