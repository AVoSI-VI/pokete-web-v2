"""Save and mod locations for one local user, shaped for a later account id."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data"
USER_ID = "local"
_USER_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")


def user_root(user_id: str = USER_ID) -> Path:
    if _USER_RE.fullmatch(user_id) is None:
        raise ValueError("user id is not allowed")
    root = (DATA / user_id).resolve()
    if DATA.resolve() not in root.parents:
        raise ValueError("user path escaped the data root")
    return root


def save_dir(user_id: str = USER_ID) -> Path:
    return user_root(user_id) / "saves"


def save_file(user_id: str = USER_ID) -> Path:
    return save_dir(user_id) / "pokete.json"


def mods_dir(user_id: str = USER_ID) -> Path:
    return user_root(user_id) / "mods"


def ensure_user(user_id: str = USER_ID) -> None:
    save_dir(user_id).mkdir(parents=True, exist_ok=True)
    mods_dir(user_id).mkdir(parents=True, exist_ok=True)
