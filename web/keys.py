"""Allowlisted game keys. Anything else is dropped. No shell and no colon."""

import queue

NAMED = frozenset(
    {"up", "down", "left", "right", "enter", "esc", "backspace", "space"}
)
# Letters cover movement, menu, and name prompts. Colon opens the cheat entry.
TEXT = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ?#.,'-_"
)

_queue: queue.Queue[str] = queue.Queue(maxsize=64)


def accept(token: str) -> bool:
    if token in NAMED:
        return True
    return len(token) == 1 and token in TEXT


def push(token: str) -> bool:
    if not accept(token):
        return False
    try:
        _queue.put_nowait(token)
    except queue.Full:
        return False
    return True


def take(timeout: float = 0.2) -> str | None:
    try:
        return _queue.get(timeout=timeout)
    except queue.Empty:
        return None
