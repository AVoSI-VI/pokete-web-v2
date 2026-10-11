"""Upload and download one Pokete save. The shape matches read_save()."""

import json
from typing import Any

from web.paths import ensure_user, save_file

MAX_SAVE_BYTES = 1_000_000

# Keys from the default dict in pokete.classes.save.read_save.
REQUIRED: dict[str, type | tuple[type, ...]] = {
    "user": str,
    "represent_char": str,
    "ver": str,
    "map": str,
    "oldmap": str,
    "last_center_map": str,
    "x": int,
    "y": int,
    "achievements": list,
    "pokes": dict,
    "inv": dict,
    "settings": dict,
    "caught_poketes": list,
    "visited_maps": list,
    "used_npcs": list,
    "hotkeys": dict,
    "pokete_care": dict,
    "time": (int, float),
}


class SaveError(ValueError):
    pass


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_save(payload: bytes) -> dict[str, Any]:
    if len(payload) > MAX_SAVE_BYTES:
        raise SaveError("save is too large")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as err:
        raise SaveError("save is not JSON") from err
    if not isinstance(data, dict):
        raise SaveError("save must be a JSON object")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise SaveError("save is missing required keys")
    for key, expected in REQUIRED.items():
        value = data[key]
        if expected is int:
            if not _is_int(value):
                raise SaveError(f"save field {key} has the wrong type")
        elif not isinstance(value, expected):
            raise SaveError(f"save field {key} has the wrong type")
    return data


def store_save(payload: bytes, user_id: str) -> None:
    data = validate_save(payload)
    ensure_user(user_id)
    path = save_file(user_id)
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def read_save_bytes(user_id: str) -> bytes | None:
    path = save_file(user_id)
    if not path.is_file():
        return None
    return path.read_bytes()


def enable_load_mods(user_id: str) -> None:
    """Turn on mod loading in an existing save. No file is created here."""
    raw = read_save_bytes(user_id)
    if raw is None:
        return
    try:
        data = validate_save(raw)
    except SaveError:
        return
    settings = data.get("settings")
    if not isinstance(settings, dict):
        return
    if settings.get("load_mods") is True:
        return
    settings["load_mods"] = True
    data["settings"] = settings
    save_file(user_id).write_text(
        json.dumps(data, indent=4) + "\n", encoding="utf-8"
    )
