"""Run Pokete in this process without a terminal.

Keys are pushed into the game's event object. The map is captured as text.
Tracked game files are not modified; the terminal reader is never started.
"""

import os
import sys
import threading
import time
import traceback

from web import frames, keys
from web.mods_store import ensure_loader
from web.paths import ROOT, mods_dir, save_dir
from web.saves import enable_load_mods

_lock = threading.Lock()
_thread: threading.Thread | None = None
_state = "stopped"
_detail = ""
_pump_started = False


def status() -> dict[str, str]:
    with _lock:
        return {"state": _state, "detail": _detail}


def _set(state: str, detail: str = "") -> None:
    global _state, _detail
    with _lock:
        _state = state
        _detail = detail


def start(user_id: str) -> str:
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return "running"
        _thread = threading.Thread(
            target=_run, args=(user_id,), name="pokete", daemon=True
        )
        _thread.start()
        return "started"


def _patch_terminal_size() -> None:
    os.get_terminal_size = lambda *_args, **_kwargs: os.terminal_size((80, 24))


def _prepare_import(user_id: str) -> None:
    user = str(mods_dir(user_id).parent)
    src = str(ROOT / "src")
    for entry in (user, src):
        while entry in sys.path:
            sys.path.remove(entry)
    sys.path.insert(0, src)
    sys.path.insert(0, user)
    sys.argv = ["pokete", "--save_dir", str(save_dir(user_id)), "--no_audio"]


def _patch_context(cls) -> None:
    def enter(self):
        del self
        from pokete.base.single_event import single_event_periodic_event

        single_event_periodic_event.monitor()

    def exit(self, exc_type, exc_value, exc_tb):
        del self, exc_value, exc_tb
        import logging

        from pokete.classes.audio import audio

        audio.kill()
        if exc_type is KeyboardInterrupt:
            return True
        if exc_type is not None and exc_type is not SystemExit:
            logging.error("[General] Error occurend:", exc_info=True)
        return False

    cls.__enter__ = enter
    cls.__exit__ = exit


def _pump() -> None:
    from pokete.base.input import key
    from pokete.base.input.event import _ev

    named = {
        "up": key.UP,
        "down": key.DOWN,
        "left": key.LEFT,
        "right": key.RIGHT,
        "enter": key.ENTER,
        "esc": key.ESC,
        "backspace": key.BACKSPACE,
        "space": key.SPACE,
    }
    while True:
        token = keys.take(0.2)
        if token is None:
            continue
        event = named.get(token)
        if event is None and len(token) == 1:
            event = key.Key(token)
        if event is None:
            continue
        deadline = time.monotonic() + 1
        while _ev.get() is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        _ev.set(event)


def _has_mods(user_id: str) -> bool:
    folder = mods_dir(user_id)
    return any(
        path.suffix == ".py" and not path.name.startswith("_")
        for path in folder.glob("*.py")
    )


def _run(user_id: str) -> None:
    _set("running", "")
    frames.set_frame("Starting game…")
    try:
        ensure_loader(user_id)
        if _has_mods(user_id):
            enable_load_mods(user_id)
        _patch_terminal_size()
        _prepare_import(user_id)
        import scrap_engine as se

        frames.install_show_patch(se.Map)
        import pokete.classes.game_context as game_context
        from pokete.base.input.event import _ev
        from pokete.__main__ import main

        _patch_context(game_context.GameContext)
        if not hasattr(_ev, "emit_fn"):
            _ev.set_emit_fn(lambda: None)
        _start_pump()
        main()
    except (Exception, SystemExit):
        text = traceback.format_exc()
        frames.set_frame(text)
        _set("error", text.splitlines()[-1])
        return
    _set("stopped", "")


def _start_pump() -> None:
    global _pump_started
    if _pump_started:
        return
    _pump_started = True
    threading.Thread(target=_pump, name="pokete-keys", daemon=True).start()
