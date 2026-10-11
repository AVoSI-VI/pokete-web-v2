"""Store an uploaded mod file. The web process does not import or run it."""

import ast
import re

from web.paths import ensure_user, mods_dir
from web.saves import enable_load_mods

MAX_MOD_BYTES = 256_000
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\.py")

_LOADER = '''"""Load stored mods. Imported by the game, not by the web server."""

import importlib
import os

from pokete.classes.mods import ModError

_here = os.path.dirname(__file__)
mod_names = [
    name[:-3]
    for name in os.listdir(_here)
    if name.endswith(".py") and not name.startswith("_")
]
mod_obs = [importlib.import_module("mods." + name) for name in mod_names]

for _name, _mod in zip(mod_names, mod_obs):
    try:
        [_mod.version, _mod.name, _mod.mod_p_data]
    except AttributeError as err:
        raise ModError(_name, err) from err

mod_info = {_mod.name: _mod.version for _mod in mod_obs}
'''


class ModError(ValueError):
    pass


def _filename(raw_name: str) -> str:
    name = raw_name.replace("\\", "/").strip()
    if "/" in name or name.startswith("."):
        raise ModError("mod file name is not allowed")
    if _NAME_RE.fullmatch(name) is None:
        raise ModError("mod file name is not allowed")
    if name == "__init__.py":
        raise ModError("mod file name is not allowed")
    return name


def _check_source(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        raise ModError("mod file is not valid Python") from err
    assigned: set[str] = set()
    functions: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
    if "version" not in assigned or "name" not in assigned:
        raise ModError("mod must assign version and name")
    if "mod_p_data" not in functions:
        raise ModError("mod must define mod_p_data")


def ensure_loader(user_id: str) -> None:
    ensure_user(user_id)
    loader = mods_dir(user_id) / "__init__.py"
    current = loader.read_text(encoding="utf-8") if loader.is_file() else ""
    if current != _LOADER:
        loader.write_text(_LOADER, encoding="utf-8")


def store_mod(raw_name: str, payload: bytes, user_id: str) -> str:
    if len(payload) > MAX_MOD_BYTES:
        raise ModError("mod is too large")
    name = _filename(raw_name)
    try:
        source = payload.decode("utf-8")
    except UnicodeError as err:
        raise ModError("mod file must be UTF-8 text") from err
    _check_source(source)
    ensure_loader(user_id)
    folder = mods_dir(user_id).resolve()
    dest = (folder / name).resolve()
    if dest.parent != folder:
        raise ModError("mod path is not allowed")
    dest.write_text(source, encoding="utf-8")
    enable_load_mods(user_id)
    return name
