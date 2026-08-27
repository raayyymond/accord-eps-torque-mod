#!/usr/bin/env python3
"""Route `5a` (**V73**) additions to the grind harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` + `_r50_lib` + `_r58_lib` + `_r59_lib`
unchanged, so a ratio computed on route 5a is computed with the IDENTICAL instrument as every prior
route. This file adds the build entry, the mode channel, and nothing else.

★ THE MODE CHANNEL IS THE NEW THING. V73's probe reads `gp+0x63FD`, the base-assist damper's MODE
SELECTOR, into CAN 0x14A byte4 bits 6:3. Measured on this route: **mode 10 when engaged, mode 8 when
manual**, 18 transitions, all at engagement edges. `mode` is therefore NOT an independent covariate --
it is ~collinear with `cc_lat`, and a "mode 8 vs mode 10" contrast IS an engagement contrast plus a
~1-2 s hysteresis band. Report it as such; never as a separate lever.

🛑 V73 IS UNGATED, exactly as V72 (`0x3AA96` = 0xC5, the dead cell) ⇒ the manual arm carries the full
rate-lane dose. Any engaged/manual contrast on this route is an ENGAGEMENT test, never a dose test.

🛑 THERE IS NO INTERNAL-COMMAND PROBE ON THIS ROUTE. V73 spent its whole 4-bit field on the mode, so
`gp-0x6b98` (the shaped LKAS command, `FUN_00042af8`'s output, the cell the +-0x2000 mixer rail acts
on) is NOT observable here. The only command-side observable is `e4tq` = CAN 0x0E4 bytes 0:1 on
**sendcan src 1** -- openpilot's REQUEST, upstream of every EPS clamp. See `rail_channels()`.
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
import _r31_common as C  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r4f_lib as R4F  # noqa: E402  -- owns `fs_lattice`
import _r50_lib as R50  # noqa: E402
import _r58_lib as R58  # noqa: E402
import _r59_lib as R59  # noqa: E402  -- registers V72/r59

PKL = ROOT / "_scratch/data/_cache_r5a_records.pkl"

fs_lattice = R4F.fs_lattice
install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

# ------------------------------------------------------------------ the build entry --------------
# `kd` is a LABEL only. V73 carries V72's rate-lane surface byte-identically.
G.BUILDS["V73/r5a"] = dict(cache=ROOT / "_scratch/cache/r5a", pfx="r5as", segs=list(range(18)), kd=2.44)

ORDER_5A = R59.ORDER_59 + ["V73/r5a"]

POOL_KD2 = R59.POOL_KD2
POOL_KD1 = R59.POOL_KD1
POOL_GATED = R59.POOL_GATED
POOL_V72 = ["V72/r59"]
POOL_V73 = ["V73/r5a"]

V73_MANUAL_IS_STOCK = False      # UNGATED, same as V72
# V73's rate-lane dose surface IS V72's, byte for byte.
V73_R24_DOSE, V73_R26_DOSE = R59.V72_R24_DOSE, R59.V72_R26_DOSE

KMH = 1.0 / 3.6
VBINS = R50.VBINS_V70
VBIN_NAMES = R50.VBIN_NAMES
vbin = R50.vbin

CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order, engine_order = R4F.wheel_order, R4F.engine_order

PARKED = dict(R59.PARKED)        # route 5a's parked segments are filled in by census, below


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V73/r5a, with `mode` per window."""
    install_fs()
    order = order or ORDER_5A
    stamp = ("lattice" if USE_LATTICE_FS else "legacy")
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if store.get("__fs__") == stamp and all(b in store for b in order):
            return {k: v for k, v in store.items() if not k.startswith("__")}
    store = {"__fs__": stamp}
    for b in order:
        rs = G.wrecs(b)
        store[b] = R47.augment(rs)
        R4F._add_rpm(b, store[b])
        for r in store[b]:
            r["vb"] = vbin(r["v"])
        _add_mode(b, store[b])
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return {k: v for k, v in store.items() if not k.startswith("__")}


def _add_mode(build, recs):
    """Per-window MODAL `mode` + its purity, and the per-window mean |e4tq| rail fraction.

    🛑 `mode` is CATEGORICAL -- a mean over a window that straddles an 8->10 transition is a code
    that never occurred. Modal value + purity, so an impure window can be dropped rather than
    silently mislabelled.
    """
    B = G.BUILDS[build]
    by = {}
    for r in recs:
        by.setdefault(r["seg"], []).append(r)
    for seg, rs in by.items():
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            for r in rs:
                r["mode"], r["mode_pure"] = np.nan, np.nan
            continue
        d = np.load(p)
        if "mode" not in d.files:
            for r in rs:
                r["mode"], r["mode_pure"] = np.nan, np.nan
            continue
        t, mo = np.asarray(d["t"], float), np.asarray(d["mode"], float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            w = mo[i0:i0 + G.NFFT]
            if not len(w):
                r["mode"], r["mode_pure"] = np.nan, np.nan
                continue
            vals, cnt = np.unique(w, return_counts=True)
            j = int(np.argmax(cnt))
            r["mode"] = float(vals[j])
            r["mode_pure"] = float(cnt[j] / len(w))


# ------------------------------------------------------------------ the rail channels -------------
RAIL_CHANNELS = {
    "e4tq": ("CAN 0x0E4 bytes 0:1, sendcan src 1 -- OPENPILOT'S STEER_TORQUE REQUEST. The only "
             "command-side observable on this route. Upstream of every EPS clamp. Its own rail is "
             "openpilot's STEER_MAX, measured below, NOT the firmware's +-0x2000."),
    "tq":   ("CAN 0x18F bytes 0:1 x -1 -- STEER_TORQUE_SENSOR, the TORSION BAR. A plant sensor: it "
             "cannot clip at a firmware mixer rail, and it is the kit's standard analysis channel."),
    "sca":  ("CAN 0x18F byte4 bit3 -- STEER_CONTROL_ACTIVE."),
    "sstat": ("CAN 0x18F byte4 bits 7:4 -- STEER_STATUS. 🛑 NOT `gp-0x67fa`."),
}
NOT_OBSERVABLE = ("gp-0x6b98 (the shaped LKAS command the +-0x2000 mixer rail acts on), gp-0x6c2c "
                  "(the differentiator input), and the four mixer channel outputs. V73's probe is "
                  "spent on the mode byte; none of these is on the bus.")

avg_periodogram = R50.avg_periodogram
eng_mask, man_mask, all_mask, hdr = R50.eng_mask, R50.man_mask, R50.all_mask, R50.hdr


def load_seg(seg):
    B = G.BUILDS["V73/r5a"]
    return C.load(seg, B["cache"], B["pfx"])
