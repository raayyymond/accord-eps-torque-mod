#!/usr/bin/env python3
"""Route-`50` (V70) additions to the grind-#1 / grind-#2 harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` unchanged, so a ratio computed on
route 50 is computed with the identical instrument as every prior route. This file adds exactly
three things, mirroring `_r4f_lib`'s contract one-for-one.

1. THE BUILD ENTRY.  "V70/r50" is registered into `_grind2_lib.BUILDS` but deliberately NOT added
   to `G.ORDER` / `G.DOSE` -- every existing `analyze_grind2_*.py` iterates those, and mutating them
   would silently rewrite results already on record. `ORDER_50` / `DOSE_50` live here.

2. THE SAMPLE-RATE FIX, INHERITED NOT RE-DERIVED.  `_r4f_lib.install_fs()` monkey-patches
   `fs_lattice` into `_grind2_lib`, `_r31_common` and `_r47_lib` for ALL builds. 🛑 It is imported
   here, never re-implemented: an estimator applied to one arm of a contrast is a confound, not a
   fix. Route 50's own legacy `1/median(dt)` reads 100.44 / 100.52 / 101.37 Hz across its three
   segments -- a 0.9% spread WITHIN one route, which is larger than the whole between-route spread
   the lattice fix was written for. Do not run this route on the legacy estimator.

3. THE V70 SPEED BREAKPOINTS.  V70 is V69's TOPOLOGY AT HALF THE DOSE and is likewise a FUNCTION OF
   SPEED -- but on route 50 it applies in BOTH arms, because V70's gate points at the DEAD
   `gp-0x683c` and its arm is stock/unreachable. Re-derived from the shipped image by sweep, not
   quoted from prose (`build_v69_tva.gain_q10(_v70_plain_image, v_counts, rateKey=100)` against
   `_v68_plain_image` as the stock surface):

       km/h    0     5    7.2    10     15     20     25     30     35     40     45    >=50
       mult  2.000 2.000 2.000 2.000  1.886  1.769  1.649  1.526  1.399  1.270  1.136  1.0000

   ⚠ AND IT IS ALSO A FUNCTION OF THE RATE AXIS, which `VBINS_V70` cannot express. At 7.2 km/h the
   multiplier is 2.000 for rateKey <= 400, 1.836 @603, 1.362 @1126, and EXACTLY 1.000 at rateKey
   >= ~2000. So a speed bin's dose is an UPPER bound; a burst living at high rateKey got less.
   This is the whole design of the build (grind #2 lives at rateKey >= 1126) -- never quote
   `V70_DOSE` as the delivered dose for a specific burst without checking its rate axis.

🛑 THERE IS NO FIRMWARE ENGAGEMENT BIT ON ROUTE 50. V70 spends all four rungs on r24/r26/state, and
the LKAS gate is reverted, so `g6806` is NaN in this cache and `wrecs` falls back to `cc_lat` --
the kit's standing engagement convention and the only one available here.

⚠⚠ ROUTE 50 IS SHORT AND ITS FIRST SEGMENT IS STATIONARY. 181.6 s over three segments, of which
seg 0 is 61.6 s parked (gear = park, vEgo == 0.00 throughout, latActive 0%) with an unsynced wall
clock. Real driving is segments 1-2 only, ~120 s, topping out at 16.95 m/s (61 km/h). Highway
exposure at and above 50 km/h -- the band where V70 is byte-identical to stock -- is a few seconds.
Any cross-build highway contrast that leans on this route is underpowered; say so rather than
quoting the CI as if the exposure were comparable to route 4f's.
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
import _r4f_lib as R4F  # noqa: E402  -- registers V69/r4f (+ V68/r4e) and owns `fs_lattice`

PKL = ROOT / "_cache_r50_records.pkl"

# 🛑 Re-exported, NOT re-defined. `_r4f_lib` is the single owner of the sample-rate estimator; two
# copies would drift and a drifted estimator between arms of a contrast is exactly the confound the
# fix exists to remove.
fs_lattice = R4F.fs_lattice
install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

# ------------------------------------------------------------------ the V70 build entry ----------
# `kd=2.0` is a LABEL, not a dose -- V70's dose is a function of speed AND rate axis. See DOSE_50.
G.BUILDS["V70/r50"] = dict(cache=ROOT / "_cache_r50", pfx="r50s", segs=[0, 1, 2], kd=2.0)

ORDER_50 = R4F.ORDER_4F + ["V70/r50"]
# 🛑 V70 is entered at its CREEP dose (2.00x), which is where every prior 2.00x build sits, so the
# pool is honest at creep and WRONG above ~10 km/h. Never pool V70 across speed as one dose; bin it
# with `VBINS_V70` / `V70_DOSE` and compare bin-for-bin.
DOSE_50 = {k: list(v) for k, v in R4F.DOSE_4F.items()}
DOSE_50[2.00] = DOSE_50[2.00] + ["V70/r50"]

# The comparison pools the brief names, on the SAME channel and the SAME estimator.
POOL_KD2 = R4F.POOL_KD2                              # 2.00x everywhere, at every speed
POOL_KD1 = R4F.POOL_KD1                              # stock rate lane
POOL_GATED = R4F.POOL_GATED                          # 2.00x when LKAS applies, every speed
POOL_SPEEDSHAPED = ["V69/r4f", "V70/r50"]            # ★ the dose-response arm: 4x vs 2x, same shape

# ------------------------------------------------------------------ V70's own speed breakpoints ---
KMH = 1.0 / 3.6
# Same edges as V69 -- the two builds share a surface SHAPE, which is what makes them a clean pair.
VBINS_V70 = [(0.0, 10 * KMH), (10 * KMH, 15 * KMH), (15 * KMH, 20 * KMH), (20 * KMH, 30 * KMH),
             (30 * KMH, 40 * KMH), (40 * KMH, 50 * KMH), (50 * KMH, 1e9)]
VBIN_NAMES = R4F.VBIN_NAMES                          # ["0-10", ..., "50+"] -- identical edges
# V70's DELIVERED rate-lane multiplier at each bin's MIDPOINT on the LOW rate axis (rateKey 100),
# swept from the shipped `_v70_plain_image.bin` against `_v68_plain_image.bin`'s stock surface.
V70_DOSE = {"0-10": 2.000, "10-15": 1.943, "15-20": 1.828, "20-30": 1.649, "30-40": 1.399,
            "40-50": 1.136, "50+": 1.000}
# V69's, for the paired dose-response. Every bin is EXACTLY 2x V70's excess over 1.0 by design.
V69_DOSE = R4F.V69_DOSE

# Established wheel circumference for this car (memory: accord-v57-confirms-wheel-order-tyre-line).
CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order = R4F.wheel_order
engine_order = R4F.engine_order


def vbin(v):
    for i, (lo, hi) in enumerate(VBINS_V70):
        if lo <= v < hi:
            return i
    return len(VBINS_V70) - 1


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V70/r50, cached to a pickle.

    Records are built with whatever `fs_of` is installed, so the cache is invalidated by hand
    whenever `USE_LATTICE_FS` changes -- the stamp is stored alongside.
    """
    install_fs()
    order = order or ORDER_50
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


# ------------------------------------------------------------------ averaged periodogram ---------
def avg_periodogram(build, mask_fn=None, chan="tq", nfft=G.NFFT, hop=G.HOP, segs=None,
                    vlo=-1e9, vhi=1e9):
    """(f, mean P, K, per-window P stack, meta) averaged over DISJOINT engagement runs.

    ★ AVERAGE FIRST, PEAK-FIND AFTER, and 🛑 CENSUS THE SPEEDS. A median-of-per-window-argmax
    estimator manufactures a line at band centre when none exists. And a moving wheel order
    concentrates in a narrow-speed route and smears in a wide one, so an averaged spectrum is only
    comparable across builds when the SPEED DISTRIBUTIONS are matched -- `meta` carries each
    window's own mean speed for exactly that check. Route 50's speed span is narrow (0-17 m/s);
    against a route with highway this test is mandatory, not optional.
    """
    return R4F.avg_periodogram(build, mask_fn=mask_fn, chan=chan, nfft=nfft, hop=hop, segs=segs,
                               vlo=vlo, vhi=vhi)


eng_mask = R4F.eng_mask
man_mask = R4F.man_mask
all_mask = R4F.all_mask
hdr = R4F.hdr


# ------------------------------------------------------------------ the V70 probe ----------------
# Channel names as written by `extract_r50_cache.py`. Kept here so an analysis script never has to
# guess, and so a renamed field breaks loudly at import rather than silently reading zeros.
PROBE_FIELDS = {
    "b6_6ada": "bit6  gp-0x6ada >= +512   POSITIVE CONTROL, ONE-SIDED -- never quote as two-sided",
    "b5_st10": "bit5  gp-0x67fa == 10     THE STATE GATE (aggregator runs, detector does NOT)",
    "b4_6adc": "bit4  gp-0x6adc >= 0      r26 mirror SIGN -- read only against bit3",
    "b3_6ada": "bit3  gp-0x6ada >= 0      r24 mirror SIGN -- the keystone",
    "sign_agree": "bit4 == bit3, the r26-liveness decision statistic (vs its own chance baseline)",
    "order_viol": "bit6 & ~bit3 -- MUST be 0 everywhere; non-zero means the image is not V70",
}


def probe(seg, cache=None, pfx=None):
    """Load one segment's probe channels as a dict of float arrays, with the invariant asserted."""
    B = G.BUILDS["V70/r50"]
    d = C.load(seg, cache or B["cache"], pfx or B["pfx"])
    out = {k: np.asarray(d[k], float) for k in PROBE_FIELDS if k in d}
    if not out:
        raise AssertionError(f"seg {seg}: no probe channels in the cache -- wrong extractor ran")
    if "order_viol" in out and out["order_viol"].any():
        raise AssertionError(f"seg {seg}: bit6 => bit3 VIOLATED in "
                             f"{int(out['order_viol'].sum())} frames -- this image is not V70")
    return out
