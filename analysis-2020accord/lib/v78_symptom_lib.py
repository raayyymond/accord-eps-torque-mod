#!/usr/bin/env python3
"""Register `V75/r5e` (PRE-FAULT ONLY) into the grind harness, and nothing else.

`_r5d_lib` transitively registers every build back to V59, and installs the lattice `fs`. This adds
the thirteenth entry, pointing at `_scratch/cache/r5e_sym/` (written by `extract/v78_symptom_cache.py`), so every
statistic `studies/sessions/r5d/r5d_ratchet.py` / `studies/sessions/r5d/r5d_falsifiers.py` computed for V74 is computed for V75 by the
IDENTICAL code path.

🛑 THREE THINGS THAT ARE NOT LIKE THE OTHER TWELVE, stated here so no downstream reader has to
   rediscover them:
   1. The route is TRUNCATED at t = 284.805 s, the single terminal `sstat` 0 -> 7 transition. Every
      number is a pre-fault number. 182.3 s engaged, against route 5d's 359 s.
   2. `kd` is a LABEL. V75's rate lane is byte-identical to V74/V73/V72 and, per RULE 7, inert on a
      mode-24/26 car. The damper dose is carried by `K_RAMP` below, not by `kd`.
   3. seg0 is PARKED (0.0% engaged, mean |v| 0.06 m/s) -- listed in `d6_events.PARKED`.

`K_RAMP` is the damper's ramp-regime incremental gain `k = (C_Y0 * Y[1] >> 10) / (X[1] - X[0])`,
byte-derived in `docs/handoffs/2026-08/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md` §3. It is the
frequency-independent scalar the whole damper path is multiplied by, so it is the only defensible
dose axis for a damper-ladder regression.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np  # noqa: F401

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r5d_lib as L  # noqa: E402  -- registers V59..V74 and owns install_fs
import d6_events as D  # noqa: E402

CACHE = ROOT / "_scratch/cache/r5e_sym"
G.BUILDS["V75/r5e"] = dict(cache=CACHE, pfx="r5es", segs=[0, 1, 2, 3, 4], kd=2.44)

D.PARKED["V74/r5d"] = [2, 3, 9]
D.PARKED["V75/r5e"] = [0]

install_fs = L.install_fs
hdr = L.hdr

# ------------------------------------------------------------------ the damper ladder ------------
# k = (C_Y0 * FactorE_Y[1] >> 10) / (E_X1 - E_X0).  Byte-derived; see the V75 handoff §3.
K_RAMP = {
    "V59/r2c":  0.0000, "V58/r2b": 0.0000, "V62/r37": 0.0000, "V65/r3b": 0.0000,
    "V67/r47":  0.0000, "V68/r4e": 0.0000, "V69/r4f": 0.0000, "V71B/r54": 0.0000,
    "V71C/r58": 0.0000,
    "V72/r59":  0.0000,          # levers present but mode-indexed to rows this car does not read
    "V73/r5a":  0.0000,          # ditto -- RULE 7; the damper was never in force
    "V74/r5d":  0.5799,          # C_Y0 429, E_X1 400   -> M 225
    "V75/r5e":  1.5798,          # C_Y0 566, E_X1 200   -> M 297
}
K_NEWCUT = 0.7655                # C_Y0 566, E_X1 400 -- built, unflashed

CORPUS = ["V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V68/r4e", "V69/r4f",
          "V71B/r54", "V71C/r58", "V72/r59", "V73/r5a", "V74/r5d", "V75/r5e"]

PKL = ROOT / "_scratch/data/_cache_r5e_sym_records.pkl"


def records(rebuild=False):
    """{build: [window records]} for the 13-build corpus.

    🛑 The twelve prior builds come out of `_scratch/data/_cache_r5d_records.pkl` READ-ONLY -- this never writes
    that file, because sibling sessions read it. V75/r5e is computed here and cached separately.
    """
    import pickle

    import _r47_lib as R47
    import _r4f_lib as R4F
    import _r50_lib as R50
    import _r5a_lib as R5A

    install_fs()
    base = L.records()                       # reads (and only reads) the route-5d pickle
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            mine = pickle.load(fh)
    else:
        rs = G.wrecs("V75/r5e")
        rs = R47.augment(rs)
        R4F._add_rpm("V75/r5e", rs)
        for r in rs:
            r["vb"] = R50.vbin(r["v"])
        R5A._add_mode("V75/r5e", rs)
        for r in rs:                          # V75's probe: bit7 == V74's `damp_nz`
            r.setdefault("damp", np.nan)
        mine = {"V75/r5e": rs}
        with open(PKL, "wb") as fh:
            pickle.dump(mine, fh)
    out = dict(base)
    out.update(mine)
    return out


# The operator's verbal report per build, for the perceptual mapping in `studies/sessions/v78/v78_symptom_perception.py`.
# 🛑 These are QUOTES, not scores. Any ordinal coding of them is an assumption and is marked as such
# wherever it is used.
VERBAL = {
    "V72/r59": "no change reported (damper never in force -- RULE 7)",
    "V73/r5a": "no change reported (damper never in force -- RULE 7)",
    "V74/r5d": "attenuated grinding and micro-ratcheting",
    "V75/r5e": "grinding imperceptible; micro-ratcheting barely still existing",
}
