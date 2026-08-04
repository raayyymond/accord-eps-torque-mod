#!/usr/bin/env python3
"""Route-`4f` (V69) additions to the grind-#1 / grind-#2 harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` unchanged, so a ratio computed on route 4f is
computed with the identical instrument as every prior route. This file adds exactly three things.

1. THE BUILD ENTRY.  "V69/r4f" is registered into `_grind2_lib.BUILDS` but deliberately NOT added
   to `G.ORDER` / `G.DOSE` -- every existing `analyze_grind2_*.py` iterates those, and mutating them
   would silently rewrite results already on record. `ORDER_4F` / `DOSE_4F` live here.

2. ★ THE SAMPLE-RATE FIX, APPLIED TO EVERY BUILD.  `_r31_common.fs_of` is `1/median(dt)`. CAN frames
   are timestamped per LOG PACKET, so several frames share a timestamp (dt == 0 for 305-1551 samples
   per segment on 4f) and the surplus is repaid as a larger gap. The median is therefore biased HIGH
   and, worse, biased by a ROUTE-DEPENDENT amount:

       gapless mean rate   r4f 100.001   r37  99.979   r3b 100.022   r47  99.998   r35  99.997
       1/median(dt)        r4f 100.13    r37 100.40    r3b 100.67    r47 100.14    r35 101.42

   The true grid is 100.000 Hz on every route; the legacy estimator spreads 1.3% across routes, i.e.
   a 0.27 Hz systematic shift at 21 Hz -- three quarters of a bin, between arms of a cross-build
   contrast. `fs_lattice` uses the mean rate over the LONGEST GAPLESS STRETCH (gap > 50 ms, the same
   cut `runs_of` uses, so it is the rate on the lattice the windows are actually cut from).
   🛑 It is monkey-patched into BOTH modules for ALL builds, never for 4f alone: an estimator applied
   to one arm of a contrast is a confound, not a fix. `USE_LATTICE_FS = False` reverts, and the
   headline is reported both ways as a sensitivity check.

3. THE V69 SPEED BREAKPOINTS.  V69 is the first build since V62 whose rate-lane dose is a FUNCTION OF
   SPEED: 4.000x to 10 km/h, 3.658 @15, 3.307 @20, 2.578 @30, 1.808 @40, and EXACTLY 1.000x (stock,
   byte-identical -- rec2/rec3 untouched) at and above 50 km/h. V62/V65 were 2.00x everywhere;
   V67/V68 were 2.00x whenever LKAS applied, at every speed. `VBINS_V69` bins on those breakpoints.

🛑 There is NO firmware gate bit on route 4f. V69 re-spent bit6 on the r24 lane and REVERTED the
gate, so `g6806` does not exist in this cache and `wrecs` falls back to `cc_lat` -- the kit's
standing engagement convention and the only one available here.
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

PKL = ROOT / "_cache_r4f_records.pkl"

USE_LATTICE_FS = True


def fs_lattice(d):
    """Mean frame rate over the longest stretch with no gap > 50 ms -- the rate ON the lattice.

    The 50 ms cut is `_r31_common.runs_of`'s own `max_gap`, so this is the rate of exactly the
    sample lattice the analysis windows are cut from.
    """
    t = np.asarray(d["t"], float)
    if len(t) < 3:
        return 100.0
    dt = np.diff(t)
    brk = np.flatnonzero(dt > 0.05)
    edges = [0] + list(brk + 1) + [len(t)]
    a, b = max(zip(edges[:-1], edges[1:]), key=lambda ab: ab[1] - ab[0])
    if b - a < 3 or t[b - 1] <= t[a]:
        return float(1.0 / np.median(dt))
    return float((b - a - 1) / (t[b - 1] - t[a]))


def install_fs(lattice=None):
    """Patch `fs_of` in every module that imported it by name. Idempotent."""
    lattice = USE_LATTICE_FS if lattice is None else lattice
    fn = fs_lattice if lattice else _FS_LEGACY
    for mod in (G, C, R47):
        mod.fs_of = fn
    return fn


_FS_LEGACY = C.fs_of

# ------------------------------------------------------------------ the V69 build entry ----------
G.BUILDS["V69/r4f"] = dict(cache=ROOT / "_cache_r4f", pfx="r4fs", segs=list(range(8)), kd=4.0)

# 🛑 `G.ORDER` omits V58/r2b (it is defined in BUILDS but not in ORDER, which is how it sat unused
# while three sessions recorded "no Kd=1 highway sample exists"). It is the ONLY stock-rate-lane
# build with real highway exposure, so the >= 50 km/h question needs it. Include it explicitly.
ORDER_4F = G.ORDER + ["V58/r2b", "V69/r4f"]
# 🛑 `kd` is a LABEL on this route, not a dose. V69's dose is a FUNCTION OF SPEED and is 1.000x --
# i.e. STOCK, byte-identical -- at and above 50 km/h. Never pool V69 across speed as one dose.
DOSE_4F = {1.00: ["V58/r2b", "V59/r2c", "V64/r35"], 2.00: ["V62/r37", "V65/r3a", "V65/r3b"],
           2.44: ["V67/r47"], 4.00: ["V69/r4f"]}

# The comparison pools the brief names, on the SAME channel and the SAME estimator.
POOL_KD2 = ["V62/r37", "V65/r3a", "V65/r3b"]        # 2.00x everywhere
POOL_KD1 = ["V59/r2c", "V64/r35", "V58/r2b"]        # stock rate lane
POOL_GATED = ["V67/r47"]                            # 2.00x when LKAS applies, every speed
# V68 has no `_grind2_lib` cache (its extractor writes `_cache_v68/4e*.npz` with a different prefix
# convention); it is registered below only if that cache is present.
if (ROOT / "_cache_v68" / "4es31.npz").exists():
    G.BUILDS["V68/r4e"] = dict(cache=ROOT / "_cache_v68", pfx="4es", segs=[31, 32, 33, 34], kd=2.0)
    POOL_GATED = POOL_GATED + ["V68/r4e"]
    ORDER_4F = ORDER_4F + ["V68/r4e"]
    DOSE_4F[2.44] = DOSE_4F[2.44] + ["V68/r4e"]

# ------------------------------------------------------------------ V69's own speed breakpoints ---
KMH = 1.0 / 3.6
VBINS_V69 = [(0.0, 10 * KMH), (10 * KMH, 15 * KMH), (15 * KMH, 20 * KMH), (20 * KMH, 30 * KMH),
             (30 * KMH, 40 * KMH), (40 * KMH, 50 * KMH), (50 * KMH, 1e9)]
VBIN_NAMES = ["0-10", "10-15", "15-20", "20-30", "30-40", "40-50", "50+"]
# V69's DELIVERED rate-lane multiplier at each bin's midpoint, from the build's own sweep table
# (docs/HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md ss1).
V69_DOSE = {"0-10": 4.000, "10-15": 3.83, "15-20": 3.48, "20-30": 2.94, "30-40": 2.19,
            "40-50": 1.40, "50+": 1.000}

# Established wheel circumference for this car (memory: accord-v57-confirms-wheel-order-tyre-line).
CIRC_LO, CIRC_HI = 2.073, 2.088
CIRC = (CIRC_LO + CIRC_HI) / 2


def wheel_order(v, n=1, circ=CIRC):
    """Hz of the n-th wheel-rotation order at road speed v (m/s).  f = n * v / CIRC."""
    return n * np.asarray(v, float) / circ


def engine_order(rpm, n=1):
    """Hz of the n-th engine order.  f = n * rpm / 60."""
    return n * np.asarray(rpm, float) / 60.0


def vbin(v):
    for i, (lo, hi) in enumerate(VBINS_V69):
        if lo <= v < hi:
            return i
    return len(VBINS_V69) - 1


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V69/r4f, cached to a pickle.

    Records are built with whatever `fs_of` is installed, so the cache is invalidated by hand
    whenever `USE_LATTICE_FS` changes -- the stamp is stored alongside.
    """
    install_fs()
    order = order or ORDER_4F
    stamp = ("lattice" if USE_LATTICE_FS else "legacy")
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if store.get("__fs__") == stamp and all(b in store for b in order):
            return {k: v for k, v in store.items() if not k.startswith("__")}
    store = {"__fs__": stamp}
    for b in order:
        rs = G.wrecs(b)
        # `rpm` is only on the 4f cache; augment() does not touch it, so add the per-window mean here
        store[b] = R47.augment(rs)
        _add_rpm(b, store[b])
        for r in store[b]:
            r["vb"] = vbin(r["v"])
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return {k: v for k, v in store.items() if not k.startswith("__")}


def _add_rpm(build, recs):
    """Per-window mean ENGINE_RPM, for the engine-order veto. NaN where the cache has no rpm."""
    B = G.BUILDS[build]
    by = {}
    for r in recs:
        by.setdefault(r["seg"], []).append(r)
    for seg, rs in by.items():
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            for r in rs:
                r["rpm"] = np.nan
            continue
        d = np.load(p)
        if "rpm" not in d.files:
            for r in rs:
                r["rpm"] = np.nan
            continue
        t, rp = np.asarray(d["t"], float), np.asarray(d["rpm"], float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            sl = slice(i0, i0 + G.NFFT)
            v = rp[sl]
            r["rpm"] = float(np.mean(v)) if len(v) else np.nan


# ------------------------------------------------------------------ averaged periodogram ---------
def avg_periodogram(build, mask_fn=None, chan="tq", nfft=G.NFFT, hop=G.HOP, segs=None,
                    vlo=-1e9, vhi=1e9):
    """(f, mean P, K, per-window P stack) averaged over DISJOINT engagement runs.

    ★ AVERAGE FIRST, PEAK-FIND AFTER. A median-of-per-window-argmax estimator manufactures a line at
    band centre when none exists (it beat the alternative at dBIC 249-460 once, and was wrong).
    Windows are cut inside contiguous runs of the mask, never across a transition, and never spliced.
    Speed selection is applied PER WINDOW after cutting, for the same reason.
    """
    install_fs()
    B = G.BUILDS[build]
    acc, K, stack, meta = None, 0, [], []
    f = None
    for s in (segs if segs is not None else B["segs"]):
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        f = np.fft.rfftfreq(nfft, 1 / fs)
        m = mask_fn(d) if mask_fn else np.ones(len(d["t"]), bool)
        x = np.asarray(d[chan], float)
        v = np.abs(np.asarray(d["cs_v"], float))
        for a, b in C.runs_of(m, d["t"], nfft):
            for i in range(a, b - nfft + 1, hop):
                vm = float(np.mean(v[i:i + nfft]))
                if not (vlo <= vm < vhi):
                    continue
                P = C.periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                acc = P.copy() if acc is None else acc + P
                K += 1
                stack.append(P)
                meta.append(dict(seg=int(s), t0=float(d["t"][i]), v=vm,
                                 rpm=(float(np.mean(d["rpm"][i:i + nfft]))
                                      if "rpm" in d else np.nan)))
    if not K:
        return f, None, 0, np.zeros((0, 0)), []
    return f, acc / K, K, np.array(stack), meta


def eng_mask(d):
    return np.asarray(d["cc_lat"], float) > 0.5


def man_mask(d):
    return np.asarray(d["cc_lat"], float) <= 0.5


def all_mask(d):
    return np.ones(len(d["t"]), bool)


def hdr(s):
    print(f"\n{'=' * 108}\n{s}\n{'=' * 108}")
