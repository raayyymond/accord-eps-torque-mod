#!/usr/bin/env python3
"""Route `65` (**V76**) registration into the grind harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` (sample-rate fix) unchanged, so a
ratio computed on route 65 is computed with the IDENTICAL instrument as every prior route this kit
has scored. This file adds the build entry and nothing else -- V76's probe cannot supply `state`/
`mode`/`damp`/`g6806`, so `mode`/`rpm` come back NaN by construction (`_r4f_lib._add_rpm` and
`_r5a_lib._add_mode` both degrade to NaN when the field is absent from the cache, which is exactly
what happens here) and `wrecs` falls back to `cc_lat` for engagement, the kit's standing convention.

Cache: `_scratch/cache/r65/r65s{0..10}.npz`, written by `extract/v77sizing_cache.py` from `studies/sessions/v77/v77sizing_extract.py`'s
route-global extract. 63,477 frames / 636.3 s, vEgo 0-26.87 m/s (0-96.7 km/h), engaged 489.8 s
(77.0% of driving time), dtc_active == 0 throughout (the drive never hard-faulted; V76's fix held).
seg0 and seg10 are PARKED (0% engaged) -- see PARKED below.

★ THE DAMPER DOSE LABEL. `k = (FactorC_Y0 * FactorE_Y1 >> 10) / (FactorE_X1 - FactorE_X0)`, this
kit's standard ramp-gain dose axis (`v78_symptom_lib.K_RAMP`, `docs/HANDOFF-2026-08-06-v75-faulted-
and-the-gate2-gain.md` s3). V76's own numbers (`docs/HANDOFF-2026-08-07-v76-v38base-and-the-
friction-ceiling.md` s3): FactorC flat Y=[566,566,566,908] (ReLU, no ramp -- `C_Y0` and `C_Y[1]` are
BOTH 566, not the usual `C_Y0` alone), FactorE X=[0,119,2500,4000] Y=[0,300,539,927]. Using the same
formula with `C_Y0=566`, `E_Y1=300`, `E_X1-E_X0=119`: k = (566*300>>10)/119 = 165/119 = 1.3866,
matching the handoff's own stated k exactly -- ★★ EVIDENCE, re-derived here, not just quoted.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r4f_lib as R4F  # noqa: E402  -- owns `fs_lattice` / `install_fs`
import _r50_lib as R50  # noqa: E402

install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

PKL = ROOT / "_scratch/data/_cache_r65_records.pkl"

# ------------------------------------------------------------------ the build entry ---------------
K_RAMP_V76 = (566 * 300 >> 10) / (119 - 0)
assert abs(K_RAMP_V76 - 1.3866) < 5e-4, f"k mismatch: derived {K_RAMP_V76}, handoff says 1.3866"
G.BUILDS["V76/r65"] = dict(cache=ROOT / "_scratch/cache/r65", pfx="r65s", segs=list(range(11)),
                           kd=K_RAMP_V76)

PARKED = {"V76/r65": [0, 10]}          # 0% engaged, vEgo <= 1.4 m/s throughout -- see r65_census_seg.json

VBINS = R50.VBINS_V70
VBIN_NAMES = R50.VBIN_NAMES
vbin = R50.vbin
CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order, engine_order = R4F.wheel_order, R4F.engine_order

RAIL_CHANNELS = {
    "friction_hit": "CAN 0x14A byte4 bit7 -- |gp-0x6b26| > 448, THE FRICTION-LANE MARGIN (the "
                    "DTC-0x1d root cause and V76's fix). A ONE-SIDED alarm bit, not a magnitude.",
    "mode_bit1": "CAN 0x14A byte4 bit4 -- gp+0x63fd & 0x2, ONE bit of the 5-bit mode index.",
    "state_eq5": "CAN 0x14A byte4 bit3 -- gp-0x67fa == 5, THE POSITIVE CONTROL (an equality test, "
                 "not the state value).",
    "tq":   "CAN 0x18F bytes 0:1 x -1 -- STEER_TORQUE_SENSOR, the TORSION BAR. The kit's standard "
            "analysis channel.",
    "sca":  "CAN 0x18F byte4 bit3 -- STEER_CONTROL_ACTIVE.",
    "sstat": "CAN 0x18F byte4 bits 7:4 -- STEER_STATUS. NOT gp-0x67fa.",
}
NOT_OBSERVABLE = ("gp-0x6b26's own MAGNITUDE (only a >448 alarm bit is on the bus), the full mode "
                  "index (only bit1 of 5), the full assist-chain state (only an ==5 test), "
                  "gp-0x6c2c, gp-0x6b98, and every mixer channel. V76 spent its whole 4-bit field "
                  "on the fault-fix margin, the mode bit and the positive control.")


def records(rebuild=False, order=None):
    """{build: [window records]} for V76/r65 alone, cached to its own pickle.

    🛑 Deliberately NOT merged into `_scratch/data/_cache_r5d_records.pkl` / `_scratch/data/_cache_r5e_sym_records.pkl` -- those
    are owned by sibling sessions' scripts and this file only ever READS them (see
    `studies/sessions/v77/v77sizing_dose.py`, which is where V74/V75/V76 are actually compared side by side).
    """
    install_fs()
    order = order or ["V76/r65"]
    stamp = ("lattice" if USE_LATTICE_FS else "legacy")
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if store.get("__fs__") == stamp and all(b in store for b in order):
            return {k: v for k, v in store.items() if not k.startswith("__")}
    store = {"__fs__": stamp}
    for b in order:
        rs = G.wrecs(b)
        rs = R47.augment(rs)
        R4F._add_rpm(b, rs)              # NaN -- route 65's cache carries no `rpm` field
        for r in rs:
            r["vb"] = vbin(r["v"])
            r["mode"] = np.nan            # NOT observable on this probe -- see module docstring
            r["state"] = np.nan
            r["damp"] = np.nan
        store[b] = rs
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return {k: v for k, v in store.items() if not k.startswith("__")}


avg_periodogram = R50.avg_periodogram
eng_mask, man_mask, all_mask, hdr = R50.eng_mask, R50.man_mask, R50.all_mask, R50.hdr


def load_seg(seg):
    import _r31_common as C
    B = G.BUILDS["V76/r65"]
    return C.load(seg, B["cache"], B["pfx"])
