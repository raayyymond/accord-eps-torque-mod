# -*- coding: utf-8 -*-
r"""e2_common.py -- designer E2 shared plumbing.  Loads THE common time scorer the brief names,
c2/rev2A/score_time.py, BY PATH (panel/score_time.py is a different file of the same module name that sits earlier on
some import paths), and the common frequency scorer panel/score_freq.py.  ANALYSIS ONLY."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "angle_loop" / "E2-integral-most-margin"
OUT.mkdir(parents=True, exist_ok=True)
for _p in (str(AL / "c2" / "rev2A"), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import r2a_common as R  # noqa: E402,F401


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


ST = _load("score_time_r2a", AL / "c2" / "rev2A" / "score_time.py")
