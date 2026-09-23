"""Import bootstrap for a git-archive extract of the fork (no symlinks on Windows): map `openpilot.X` -> ROOT/X and
put opendbc_repo on sys.path.  Nothing here edits fork code; stubs are only for native/OS modules that cannot load on
Windows (setproctitle, the tici hardware layer) and are listed in STUBS so the report can name them."""
import sys, types
from pathlib import Path
from types import SimpleNamespace

import os
ROOT = Path(__file__).resolve().parent / os.environ.get("FORK_ROOT", "fork_head")
STUBS = []


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    STUBS.append(name)
    return m


def setup():
    for p in (str(ROOT / "opendbc_repo"), str(ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)
    pkg = types.ModuleType("openpilot")
    pkg.__path__ = [str(ROOT)]
    sys.modules["openpilot"] = pkg
    _stub("setproctitle", getproctitle=lambda: "x", setproctitle=lambda *a: None)
    hw = SimpleNamespace(get_device_type=lambda: "pc", get_sound_card_online=lambda: True)
    m = _stub("openpilot.system.hardware", PC=True, TICI=False, AGNOS=False, HARDWARE=hw)
    m.__path__ = [str(ROOT / "system" / "hardware")]
    _stub("openpilot.selfdrive.locationd.helpers", Pose=object)
    return ROOT
