#!/usr/bin/env python3
"""Routes `54` (V71B) and `58` (V71C) additions to the grind harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` + `_r50_lib` unchanged, so a ratio
computed on route 54 or 58 is computed with the IDENTICAL instrument as every prior route. This file
adds exactly the same three things `_r50_lib` adds, plus the two routes' delivered-dose surfaces.

1. THE BUILD ENTRIES.  "V71B/r54" and "V71C/r58" are registered into `_grind2_lib.BUILDS` but
   deliberately NOT added to `G.ORDER` / `G.DOSE` -- every existing `analyze_grind2_*.py` iterates
   those, and mutating them would silently rewrite results already on record.

2. THE SAMPLE-RATE FIX, INHERITED NOT RE-DERIVED.  `_r4f_lib.install_fs()` monkey-patches
   `fs_lattice` into `_grind2_lib`, `_r31_common` and `_r47_lib` for ALL builds. 🛑 Imported here,
   never re-implemented. Measured on these two routes: `fs_lattice` reads 99.917-100.016 Hz across
   all 37 segments (spread 0.10%), i.e. the true 100.000 Hz grid.

3. THE DELIVERED DOSE SURFACES, swept from the SHIPPED images, not quoted from prose.

   ★ ROUTE 54 / V71B -- r26 (`gain_A`) ALONE, speed-shaped, FLAT IN THE RATE AXIS.
     Swept `build_v71b_tva.gain_a_q10(_v71b_plain_image, kmh*64, rk)` against `_v70_plain_image`:

         km/h   0    5   10   12.5   15    20    25    30    35    40    45   >=50
         r26x 2.000 2.000 2.000 1.945 1.890 1.776 1.658 1.536 1.409 1.278 1.141 1.0000
         r24x 1.000 everywhere (gain_B surface reverted to STOCK)

     ⊕ UNLIKE V69/V70, the dose is FLAT ACROSS THE RATE AXIS: 2.0000 at rateKey 100, 400, 1126,
     2000 and 4000 alike at <=10 km/h. V69/V70 edited only `gain_B`'s [0,400] segment and were
     byte-identical to stock above rateKey ~1400 (memory: grind1-ladder-monotone-at-peak-velocity).
     V71B has no such escape -- a speed bin's dose IS the delivered dose at every rate index.
     ⇒ route 54 is the kit's FIRST rate-axis-complete dose on either lane.
     🛑 UNGATED: the dose applies in the MANUAL arm too. Route 54 has no stock control.

   ★ ROUTE 58 / V71C -- BOTH lanes, flat arms, ENGAGED ONLY (gate at gp-0x6806 is live).
     `r24` arm = 5244 @0xC6446, `r26` arm = 3072 @0xC6444, each REPLACING the stock LERP.

     🛑🛑 CORRECTED 2026-08-06 -- THE r24 ROW BELOW WAS WRONG, AND WRONG IN DIRECTION.
     WHAT IT SAID: *"THE DELIVERED r24 DOSE IS A **CUT** AT CREEP, not a boost -- the single most
     load-bearing arithmetic fact on this route"*, with `stock r24 = 6144 5633 5122 ...` and
     `r24x = 0.854 0.931 1.024 ...`.
     WHY IT WAS WRONG -- TWO COMPOUNDING ERRORS, both in the BASELINE, not in V71C:
       1. it swept V71C against **`_v70_plain_image.bin`**, not against stock; and
       2. it read `gain_B` at **mode 10**, which RULE 7 later showed is not this car's mode.
     V70's mode-10 edit DOUBLES rec0/rec1 (`Y[0]` 3072 -> 6144, 2561 -> 5122 -- byte-read), which is
     exactly the "stock r24" row that was recorded; the >=50 km/h entries (2305, 2213) are the
     UNDOUBLED rec2/rec3, because V70 edited only rec0/rec1. That signature identifies the defect
     unambiguously. ⇒ the denominator was ~2x too large below 50 km/h, turning a BOOST into a "CUT".

     THE CORRECT SURFACE -- vs TRUE STOCK at **mode 26** (engaged), byte-read via
     `lib/_grind2_delivered_lib.py`:

         km/h      0     5    10    15    20    30    40    50    80        (at rateKey 100)
         stock r24 3072 2816 2560  2528  2496  2432  2368  2303  2212
         r24x     1.707 1.862 2.048 2.074 2.101 2.156 2.215 2.277 2.371
         stock r26 3072 3072 3072  3021  2970  2868  2766  2664  2602     <-- these two rows were
         r26x     1.000 1.000 1.000 1.017 1.034 1.071 1.111 1.153 1.181       ALWAYS RIGHT

     ⇒ V71C ENGAGED at creep is a **BOOST on r24 (1.71x at low rate, rising to 3.41x at rateKey
     3000) and EXACTLY STOCK on r26**. It is NOT "~stock in both lanes". The r26 rows were never
     affected because `gain_A` is NOT mode-indexed and V70 did not touch it.
     ⊕ Nothing in this repo consumed `V71C_R24_DOSE` -- the damage was to READERS, via this
     docstring, which is why the wrong text is quoted above rather than deleted.
     ★ MANUAL ON ROUTE 58 IS BYTE-FOR-BYTE STOCK -- the only within-route, within-driver,
     within-day stock control in the corpus. `V71C_MANUAL_IS_STOCK = True` marks it.

🛑 BOTH ROUTES CARRY `0x454FE` (V42's state-4 governor ratchet kill) RESTORED. It has been off the
car since V53. These are the first two routes since V52 that carry it.

⚠ PARKED SEGMENTS. Route 58 segments 12-15 (208.4 s) are `gear == park`, `v == 0`, latActive 0% --
engine running, wheel unloaded. Route 54 segments 10-11 (120 s) are `gear == drive`, `v == 0`,
latActive 0%. `driving_mask()` cuts both; the census reports them separately.
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
import _r50_lib as R50  # noqa: E402  -- registers V70/r50

PKL = ROOT / "_scratch/data/_cache_r58_records.pkl"

# 🛑 Re-exported, NOT re-defined. One owner for the sample-rate estimator.
fs_lattice = R4F.fs_lattice
install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

# ------------------------------------------------------------------ the build entries ------------
# `kd` is a LABEL only. Neither build's dose is a scalar.
G.BUILDS["V71B/r54"] = dict(cache=ROOT / "_scratch/cache/r54", pfx="r54s", segs=list(range(21)), kd=2.0)
G.BUILDS["V71C/r58"] = dict(cache=ROOT / "_scratch/cache/r58", pfx="r58s", segs=list(range(16)), kd=2.44)

ORDER_58 = R50.ORDER_50 + ["V71B/r54", "V71C/r58"]

# 🛑 Dose pools are for the r24 (gain_B) lane, which is what every prior ladder entry moved.
# V71B is r24 = 1.000x EVERYWHERE, so it pools with the STOCK rate lane on that axis while being
# the corpus's only 2x on r26 alone. V71C is engaged-only and speed-dependent in both lanes; it is
# deliberately given its own key rather than being forced into an existing dose.
DOSE_58 = {k: list(v) for k, v in R50.DOSE_50.items()}
DOSE_58[1.00] = DOSE_58[1.00] + ["V71B/r54"]     # r24 axis. NOT the r26 axis -- see R26_DOSE.
DOSE_58["gated71c"] = ["V71C/r58"]

# ★ The r26 (gain_A) axis, which is the axis V71B is single-variable on.
R26_DOSE = {0.167: ["V67/r47", "V68/r4e"],       # 512/3072 arm, engaged only
            1.000: ["V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37",
                    "V65/r3a", "V65/r3b"],
            2.000: ["V71B/r54"]}                 # creep; tapers to 1.000 at >=50 km/h

POOL_KD2 = R50.POOL_KD2
POOL_KD1 = R50.POOL_KD1
POOL_GATED = R50.POOL_GATED
POOL_STOCK_R26 = ["V69/r4f", "V70/r50"]          # r24-dosed, r26 stock -- the r26 control arm

V71C_MANUAL_IS_STOCK = True

# ------------------------------------------------------------------ speed bins -------------------
KMH = 1.0 / 3.6
VBINS = R50.VBINS_V70                             # identical edges as V69/V70 -- comparability
VBIN_NAMES = R50.VBIN_NAMES
V70_DOSE, V69_DOSE = R50.V70_DOSE, R50.V69_DOSE
# 🛑🛑 ALL THREE DICTS RE-DERIVED 2026-08-06 from the SHIPPED IMAGES vs TRUE STOCK at **mode 26**,
# at rateKey 100 / bin midpoint (0-10 -> 5, 10-15 -> 12.5, 15-20 -> 17.5, 20-30 -> 25, 30-40 -> 35,
# 40-50 -> 45, 50+ -> 60 km/h). Regenerate with:
#     python -c "import _grind2_delivered_lib as D; B=D.load_all(); print(D.delivered(B['V71C'],B['stock'],5,100))"
# ⚠ ONLY `V71C_R24_DOSE` MOVED. The two r26 dicts were always right -- `gain_A` is not mode-indexed
# and V70 never touched it, so neither of this defect's two causes could reach them. Verified, not
# assumed: the re-derived r26 values reproduce the old ones to <= 0.03.
V71B_R26_DOSE = {"0-10": 2.000, "10-15": 1.945, "15-20": 1.833, "20-30": 1.658, "30-40": 1.409,
                 "40-50": 1.141, "50+": 1.000}
# 🛑 CORRECTED. WAS `{"0-10": 0.931, "10-15": 1.099, "15-20": 1.140, "20-30": 1.290, "30-40": 1.560,
#    "40-50": 1.995, "50+": 2.370}` with the comment "🛑 r24 is a CUT below ~10 km/h" -- computed
#    against `_v70_plain_image.bin` at **mode 10**, so the denominator was ~2x too large below
#    50 km/h and the direction INVERTED. V71C's engaged r24 is a BOOST everywhere. See the module
#    docstring for the full defect account. No script in this repo consumed these values.
V71C_R24_DOSE = {"0-10": 1.862, "10-15": 2.061, "15-20": 2.088, "20-30": 2.128, "30-40": 2.185,
                 "40-50": 2.245, "50+": 2.307}
# ⚠ rateKey 100 is the FLAT part of the rate axis. V71C's r24 arm is flat while stock's LERP rolls
# off, so the dose RISES with rate: at 0 km/h it is 1.707 / 1.707 / 2.258 / 2.586 / 3.414 at
# rateKey 100 / 400 / 1400 / 2000 / 3000. A single-number "r24 dose" for this build is meaningless.
V71C_R26_DOSE = {"0-10": 1.000, "10-15": 1.008, "15-20": 1.025, "20-30": 1.052, "30-40": 1.091,
                 "40-50": 1.131, "50+": 1.162}

CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order = R4F.wheel_order
engine_order = R4F.engine_order
vbin = R50.vbin


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V71B/r54 and V71C/r58."""
    install_fs()
    order = order or ORDER_58
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
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return {k: v for k, v in store.items() if not k.startswith("__")}


# ------------------------------------------------------------------ selectors --------------------
PARKED = {"V71B/r54": [10, 11], "V71C/r58": [12, 13, 14, 15]}


def driving(rs, build=None):
    """Drop the stationary/parked segments. `gear` is held-last so it is not sufficient alone."""
    bad = PARKED.get(build or (rs[0]["build"] if rs else ""), [])
    return [r for r in rs if r["seg"] not in bad]


avg_periodogram = R50.avg_periodogram
eng_mask, man_mask, all_mask, hdr = R50.eng_mask, R50.man_mask, R50.all_mask, R50.hdr


# ------------------------------------------------------------------ the V71 probes ---------------
# 🛑 THE TWO ROUTES CARRY DIFFERENT PROBE LAYOUTS. Route 54 mirrors gp-0x6adc (r26); route 58
# mirrors gp-0x6ada (r24). Reading one route's field name on the other silently returns nothing.
PROBE_FIELDS_54 = {"b6_671d": "bit6  gp-0x671d  the r24 trump flag",
                   "b5_st4": "bit5  gp-0x67fa == 4   the state-4 governor state",
                   "b4_6adc": "bit4  |gp-0x6adc| threshold  (r26 mirror MAGNITUDE)",
                   "b3_6adc": "bit3  gp-0x6adc >= 0        (r26 mirror SIGN)"}
PROBE_FIELDS_58 = {"b6_671d": "bit6  gp-0x671d  the r24 trump flag",
                   "b5_st4": "bit5  gp-0x67fa == 4   the state-4 governor state",
                   "b4_6ada": "bit4  |gp-0x6ada| threshold  (r24 mirror MAGNITUDE)",
                   "b3_6ada": "bit3  gp-0x6ada >= 0        (r24 mirror SIGN)"}


def probe(build, seg):
    B = G.BUILDS[build]
    d = C.load(seg, B["cache"], B["pfx"])
    fields = PROBE_FIELDS_54 if build == "V71B/r54" else PROBE_FIELDS_58
    out = {k: np.asarray(d[k], float) for k in fields if k in d}
    if not out:
        raise AssertionError(f"{build} seg {seg}: no probe channels -- wrong extractor ran")
    return out
