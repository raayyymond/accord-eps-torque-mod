#!/usr/bin/env python3
"""Route `59` (V72) additions to the grind harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` + `_r50_lib` + `_r58_lib` unchanged, so
a ratio computed on route 59 is computed with the IDENTICAL instrument as every prior route. This
file adds exactly what `_r58_lib` adds, and nothing else.

1. THE BUILD ENTRY.  "V72/r59" is registered into `_grind2_lib.BUILDS` but deliberately NOT added to
   `G.ORDER` / `G.DOSE` -- every existing `analyze_grind2_*.py` iterates those and mutating them
   would silently rewrite results already on record.

2. THE SAMPLE-RATE FIX, INHERITED NOT RE-DERIVED.  `_r4f_lib.install_fs()` monkey-patches
   `fs_lattice` into `_grind2_lib`, `_r31_common` and `_r47_lib` for ALL builds. 🛑 Imported here,
   never re-implemented. Measured on route 59: `fs_lattice` reads 99.988-100.019 Hz across all 15
   segments (spread 0.031%), i.e. the true 100.000 Hz grid.

3. ★★ THE DELIVERED DOSE SURFACE, SWEPT FROM THE SHIPPED IMAGE -- and it is NOT flat across creep.
   `v72_lane_model.effective(_v72_plain_image, lane, v_counts, rate, engaged)` against stock
   `code.bin`, i.e. the decompiled FUN_0003aa2c arithmetic, not prose:

       km/h        0     5    10    15    20    30   >=50      (rateKey 400 / 1400 in brackets)
       r24x     1.707 1.862 2.048 1.928 1.806 1.551 1.000   [1400: 2.258 2.271 2.305 2.150 1.992]
       r26x     0.167 0.167 0.167 0.259 0.354 0.554 1.000   [1400: 0.202 0.208 0.215 0.304 0.396]

   ★★ V72 REPRODUCES V67/V68 EXACTLY AT 0-10 km/h AND ONLY THERE. V67/V68 held the flat arm
   (r24 5244 / r26 512) at EVERY speed; V72 writes it into the 0 and 10 km/h records only and leaves
   the 50/100 km/h records byte-stock, so the speed LERP walks both lanes back to 1.000x by 50 km/h.
   Inside the kit's creep band (< 20 km/h) that is a REAL divergence on the r26 lane:
   V67/V68 deliver 0.167-0.172x throughout, V72 delivers 0.167x only below 10 km/h and 0.354x at
   20 km/h. ⇒ "V72 == V67/V68 at creep" is true for windows below 10 km/h and false above it, and
   the creep median speed therefore has to be reported beside every V72-vs-V67/V68 contrast.

🛑 V72 IS UNGATED (`0x3AA96` = 0xC5, the dead `gp-0x683c` cell -- read from the image here, not
quoted). The sweep confirms it end to end: the ENGAGED and MANUAL surfaces are IDENTICAL. So unlike
V67/V68/V71C, route 59's manual arm is NOT a stock control -- it carries the full dose. Any
engaged/manual contrast on this route is an ENGAGEMENT test, never a dose test.

⚠ PARKED SEGMENTS. Route 59 segments 12-14 (159.6 s) are `gear == park`, `v == 0`, latActive 0%.
`driving()` cuts them; the census reports them separately.

🛑 LEVERS B AND C ARE CONFOUNDED WITH LEVER A ON THIS ROUTE. V72 also opens the base-assist damper
below 35 km/h (FactorC/FactorE) and doubles 0xC63A0. Nothing in this file can separate them from the
rate-lane dose; a V72-vs-V67/V68 difference is a difference between BUILDS, not between lanes.
"""
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r4f_lib as R4F  # noqa: E402  -- owns `fs_lattice`
import _r50_lib as R50  # noqa: E402  -- registers V70/r50
import _r58_lib as R58  # noqa: E402  -- registers V71B/r54 and V71C/r58

PKL = ROOT / "_cache_r59_records.pkl"

# 🛑 Re-exported, NOT re-defined. One owner for the sample-rate estimator.
fs_lattice = R4F.fs_lattice
install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

# ------------------------------------------------------------------ the build entry --------------
# `kd` is a LABEL only. V72's dose is a function of speed AND rate axis in BOTH lanes.
G.BUILDS["V72/r59"] = dict(cache=ROOT / "_cache_r59", pfx="r59s", segs=list(range(15)), kd=2.44)

ORDER_59 = R58.ORDER_58 + ["V72/r59"]

DOSE_59 = {k: list(v) for k, v in R58.DOSE_58.items()}
DOSE_59["v72"] = ["V72/r59"]

POOL_KD2 = R58.POOL_KD2                          # V62/r37, V65/r3a, V65/r3b -- 2.00x everywhere
POOL_KD1 = R58.POOL_KD1                          # V59/r2c, V64/r35, V58/r2b -- stock rate lane
POOL_GATED = R58.POOL_GATED                      # V67/r47, V68/r4e -- the flat arm, engaged only
POOL_V72 = ["V72/r59"]

V71C_MANUAL_IS_STOCK = R58.V71C_MANUAL_IS_STOCK
# 🛑 The corresponding fact for route 59 is the OPPOSITE and must never be conflated with it.
V72_MANUAL_IS_STOCK = False

# ------------------------------------------------------------------ speed bins -------------------
KMH = 1.0 / 3.6
VBINS = R50.VBINS_V70                            # identical edges as V69/V70/V71 -- comparability
VBIN_NAMES = R50.VBIN_NAMES
vbin = R50.vbin
V70_DOSE, V69_DOSE = R50.V70_DOSE, R50.V69_DOSE
V71B_R26_DOSE, V71C_R24_DOSE, V71C_R26_DOSE = (R58.V71B_R26_DOSE, R58.V71C_R24_DOSE,
                                               R58.V71C_R26_DOSE)

# Swept from `_v72_plain_image.bin` at each bin's MIDPOINT, rateKey 400 (the plateau) -- see the
# module docstring for the rateKey-1400 column. Identical in the engaged and manual arms: UNGATED.
V72_R24_DOSE = {"0-10": 1.862, "10-15": 1.989, "15-20": 1.868, "20-30": 1.681, "30-40": 1.419,
                "40-50": 1.143, "50+": 1.000}
V72_R26_DOSE = {"0-10": 0.169, "10-15": 0.217, "15-20": 0.309, "20-30": 0.454, "30-40": 0.661,
                "40-50": 0.882, "50+": 1.000}
# V67/V68's, at the same bins, for the divergence check. Flat-armed => nearly speed-insensitive.
V67_R24_DOSE = {"0-10": 1.862, "10-15": 2.061, "15-20": 2.088, "20-30": 2.128, "30-40": 2.185,
                "40-50": 2.245, "50+": 2.307}
V67_R26_DOSE = {"0-10": 0.169, "10-15": 0.173, "15-20": 0.175, "20-30": 0.179, "30-40": 0.184,
                "40-50": 0.189, "50+": 0.194}
# The same sweep at rateKey 1400 -- the ratchet/grind peak-velocity index. The divergence has the
# SAME shape, so the "V72 == V67/V68 only below 10 km/h" conclusion is not a rate-axis artefact.
V72_R24_DOSE_RK1400 = {"0-10": 2.271, "10-15": 2.228, "15-20": 2.071, "20-30": 1.831,
                       "30-40": 1.505, "40-50": 1.170, "50+": 1.000}
V67_R24_DOSE_RK1400 = {"0-10": 2.271, "10-15": 2.313, "15-20": 2.328, "20-30": 2.348,
                       "30-40": 2.379, "40-50": 2.410, "50+": 2.448}

CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order = R4F.wheel_order
engine_order = R4F.engine_order


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V72/r59."""
    install_fs()
    order = order or ORDER_59
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
PARKED = dict(R58.PARKED)
PARKED["V72/r59"] = [12, 13, 14]


def driving(rs, build=None):
    """Drop the stationary/parked segments. `gear` is held-last so it is not sufficient alone."""
    bad = PARKED.get(build or (rs[0]["build"] if rs else ""), [])
    return [r for r in rs if r["seg"] not in bad]


avg_periodogram = R50.avg_periodogram
eng_mask, man_mask, all_mask, hdr = R50.eng_mask, R50.man_mask, R50.all_mask, R50.hdr


# ------------------------------------------------------------------ the V72 probe ----------------
# 🛑 V72's five rungs read THREE different cells. There is no scalar "mirror cell" on this build --
# a script that reaches for route 50/54/58's `probe_cell` gets an answer wrong for four of five.
PROBE_FIELDS_59 = {"b6_69a4": "bit6  gp-0x69a4 >= 512    `a`, the r26 weight (thermometer step 1)",
                   "b5_69a4": "bit5  gp-0x69a4 >= 1024   `a` >= 1.0 (thermometer step 2)",
                   "b4_6bd0": "bit4  |gp-0x6bd0| >= 64   IS LEVER B (the base damper) IN FORCE?",
                   "b3_6ac0": "bit3  gp-0x6ac0 >= 512    the rate index, pre-registered 2.750% duty",
                   "order_viol": "bit5 & ~bit6 -- MUST be 0 everywhere; non-zero falsifies V72"}


def probe(seg, cache=None, pfx=None):
    B = G.BUILDS["V72/r59"]
    d = C.load(seg, cache or B["cache"], pfx or B["pfx"])
    out = {k: np.asarray(d[k], float) for k in PROBE_FIELDS_59 if k in d}
    if not out:
        raise AssertionError(f"seg {seg}: no probe channels -- wrong extractor ran")
    return out
