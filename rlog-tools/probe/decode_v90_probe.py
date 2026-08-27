#!/usr/bin/env python3
r"""V90 flight scorer (route 77) -- and D1, the cross-build question that needs no new data.

D1  🛑 DID V89's K1 DOSE (`0xC40D2` 102 -> 204) REGRESS THE GRINDING?
    V89's ONLY functional change from V88 is that one cell.  On route 73 (V88) the operator said the
    audible grinding was FIXED; he now says grind #1 still exists.  So: score the grinding band
    `e_18-22`, the ratchet band `e_6-9`, and the pre-declared 32-38 Hz negative control, V89
    (routes 75+76) against V88 (route 73), on speed- AND wheel-rate-matched windows.

    🛑 THE INSTRUMENT IS THE CORPUS'S.  `v89_e2_h2h3.build_records` (`_grind2_lib.wrecs`, NFFT 256 /
    hop 128, p99 analytic band envelope, ~10.2 s `blk` episode units), `v89_e3_contrast.strat_multi`
    /`boot_contrast` (cell-stratified log-ratios over (eng, SPEED bin, EFFORT bin, RATE bin) --
    speed- and rate-matching is BUILT INTO the estimator), and the bands are
    `compare_v75_v76_v80_grind.BANDS_EXT`.  Nothing is re-implemented.

    🛑 CONTROLS RUN BEFORE THE MEASUREMENT, three of them:
      1. each arm's own SPLIT-HALF null -- a ratio inside it is NOT RESOLVABLE;
      2. the pre-declared 32-38 Hz NEGATIVE CONTROL band, differenced against the subject on the
         SAME resampled episodes (so the contrast's CI is paired and honest);
      3. ★ the PLACEBO-PAIR NULL.  Episode block bootstraps understate CROSS-BUILD uncertainty by
         ~2.8x here (0.37 vs a 213-pair placebo's 1.03).  Routes 75 and 76 are two different drives
         on the SAME build, so random disjoint SEGMENT partitions of their union are genuine
         constant-build cross-drive pairs scored with the identical estimator.  Their spread IS the
         floor a V89-vs-V88 contrast must clear.  A CI that excludes 1.00 but sits inside its own
         placebo band is FLAT.

    🛑 THE WHEEL-ORDER VETO IS APPLIED SYMMETRICALLY OR NOT AT ALL.  Per-band vetoes build DIFFERENT
    window sets per band, which makes a contrast a comparison of two different window sets.  This
    file vetoes a window if ANY order 1-6 lands within the guard of ANY scored band's measured line,
    so every band is screened by the identical rule on the identical set.  Intrinsically clean
    speed strata are reported beside it, derived here rather than quoted:

        order k reaches [lo-GUARD, hi+GUARD] Hz for  v in [ (lo-G)*CIRC_LO/k , (hi+G)*CIRC_HI/k ]
          6-9   Hz : k=1 [10.78, 20.46]  k=2 [ 5.39, 10.23]  k=3 [3.59, 6.82] ...
        18-22   Hz : k=2 [17.83, 23.80]  k=3 [11.89, 15.87]  k=4 [8.92, 11.90] ...
        32-38   Hz : k=3 [21.60, 27.00]  k=4 [16.20, 20.25]  k=5 [12.96, 16.20] ...
    ⇒ NO single speed stratum is clean for all three bands at once: above ~21.6 m/s the 32-38 Hz
    CONTROL is the one order 3 can reach, which INVERTS the usual asymmetry.  Stated, not buried.

Usage:
    python probe/decode_v90_probe.py d1        # the cross-build K1 question (no new data needed)
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
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
sys.path.insert(0, str(ROOT / "_scratch/cache/r73"))

import _grind2_lib as G                                   # noqa: E402
import compare_v75_v76_v80_grind as M                     # noqa: E402  -- installs BANDS_EXT
from v89_e2_h2h3 import ARMS, BUILDS, build_records, eng, nblk   # noqa: E402
from v89_e3_contrast import boot_contrast, strat_multi    # noqa: E402

RNG = np.random.default_rng(90_1001)
OUTDIR = ROOT / "analysis-2020accord" / "_scratch/cache/r77"
OUT = {}

# ---- bands.  SUBJ1 is the operator's grinding band, SUBJ2 the ratchet band, CTRL the pre-declared
# ---- negative control, PLACEBO a second band with no hypothesis attached to it, EXPO the
# ---- driver-input matching-validity check.
SUBJ1, SUBJ2, CTRL, PLACEBO, EXPO = "e_18-22", "e_6-9", "e_32-38", "e_10-16", "e_1-4"
KEYS = [EXPO, SUBJ2, PLACEBO, SUBJ1, "e_26-31", CTRL, "e_40-49"]
BAND_OF = {"e_1-4": (1.0, 4.0), "e_6-9": (6.0, 9.0), "e_10-16": (10.0, 16.0),
           "e_18-22": (18.0, 22.0), "e_26-31": (26.0, 31.0), "e_32-38": (32.0, 38.0),
           "e_40-49": (40.0, 49.0)}
CIRC_LO, CIRC_HI, ORDERS, GUARD = 2.073, 2.088, (1, 2, 3, 4, 5, 6), 0.8
VETO_BANDS = [SUBJ2, SUBJ1, CTRL]          # the three bands the verdict rests on
V89POOL = ["V89/r75", "V89/r76"]


def hdr(s):
    print("\n" + "=" * 118 + f"\n{s}\n" + "=" * 118, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


# =================================================================================================
#  WHEEL ORDER -- derived, not quoted
# =================================================================================================
def order_windows(lo, hi):
    """Speed interval (m/s) in which order k can land within GUARD of the band, per order."""
    return {k: ((lo - GUARD) * CIRC_LO / k, (hi + GUARD) * CIRC_HI / k) for k in ORDERS}


def clean_above(lo, hi):
    """Lowest speed above which NO order 1-6 can reach the band."""
    return max(w[1] for w in order_windows(lo, hi).values())


def order_hit(f0, v):
    if not (np.isfinite(f0) and np.isfinite(v)):
        return False
    return any(abs(k * v / c - f0) < GUARD for k in ORDERS for c in (CIRC_LO, CIRC_HI))


def order_hit_any(r, keys=VETO_BANDS):
    """SYMMETRIC veto: drop the window if an order lands on ANY scored band's measured line."""
    return any(order_hit(r.get("f_" + k.split("_", 1)[1], np.nan), r["v"]) for k in keys)


def band_census(rs, keys=VETO_BANDS):
    return {k: int(sum(order_hit(r.get("f_" + k.split("_", 1)[1], np.nan), r["v"]) for r in rs))
            for k in keys}


# =================================================================================================
def census(rs, label):
    if not rs:
        print(f"      census {label}: EMPTY")
        return {}
    v = np.array([r["v"] for r in rs], float)
    rt = np.array([r["rate"] for r in rs], float)
    bins = [("<2.78", 0.0, 2.78), ("2.78-11.1", 2.78, 11.11), ("11.1-22.2", 11.11, 22.22),
            (">=22.2", 22.22, 1e9)]
    d = dict(n=len(rs), blk=nblk(rs),
             speed={nm: int(np.sum((v >= a) & (v < b))) for nm, a, b in bins},
             v_med=float(np.median(v)), rate_med=float(np.median(rt)),
             rate_p90=float(np.percentile(rt, 90)), order_hits=band_census(rs))
    print(f"      {label:26s} n={d['n']:4d} blk={d['blk']:3d}  " +
          " ".join(f"{nm} {c}" for nm, c in d["speed"].items()) +
          f"  | v med {d['v_med']:5.2f} m/s  rate med {d['rate_med']:5.1f} p90 {d['rate_p90']:5.1f}"
          f"  | order hits {d['order_hits']}")
    return d


def measured(A, B, tag, keys=KEYS, nboot=1500):
    """Cell-stratified log-ratios on paired episode resamples, + contrasts vs CTRL and PLACEBO."""
    pt, D, nc, na, nb = boot_contrast(A, B, keys, nboot=nboot)
    if not np.isfinite(pt.get(CTRL, np.nan)):
        print(f"    {tag}: no common cell -- NOT SCOREABLE")
        return None
    r = dict(cells=nc, epA=na, epB=nb, nA=len(A), nB=len(B))
    print(f"    {tag}   cells {nc}  episodes {na}/{nb}  windows {len(A)}/{len(B)}")
    print(f"      {'band':10s} {'ratio':>7s} {'[  2.5 %, 97.5 %]':>21s}   "
          f"{'vs 32-38 CONTRAST':>26s}  excl 1?")
    for k in keys:
        if not np.isfinite(pt.get(k, np.nan)):
            continue
        lo, hi = np.nanpercentile(D[k], [2.5, 97.5])
        dc = D[k] - D[CTRL]
        clo, chi = np.nanpercentile(dc, [2.5, 97.5])
        r[k] = dict(ratio=float(np.exp(pt[k])), ci=[float(np.exp(lo)), float(np.exp(hi))],
                    log_ratio=float(pt[k]),
                    contrast=float(np.exp(pt[k] - pt[CTRL])),
                    contrast_ci=[float(np.exp(clo)), float(np.exp(chi))],
                    log_contrast=float(pt[k] - pt[CTRL]))
        mark = "YES" if (clo > 0 or chi < 0) else "no"
        star = "  <-- SUBJECT" if k in (SUBJ1, SUBJ2) else ("  (control)" if k == CTRL else "")
        print(f"      {k:10s} {np.exp(pt[k]):7.3f} [{np.exp(lo):6.3f},{np.exp(hi):6.3f}]   "
              f"{np.exp(pt[k]-pt[CTRL]):7.3f} [{np.exp(clo):6.3f},{np.exp(chi):6.3f}]  {mark}{star}")
    return r


def split_half(pool, tag, keys=(SUBJ1, SUBJ2, CTRL)):
    out = {}
    for k in keys:
        md, lo, hi = G.split_half_null(pool, k, RNG, nrep=300)
        out[k] = [float(md), float(lo), float(hi)]
        print(f"      {tag:12s} {k:9s} split-half null [{lo:6.3f}, {hi:6.3f}]  median {md:.3f}")
    return out


def placebo_null(pool, tag, nrep=400, keys=KEYS):
    """Random disjoint SEGMENT partitions of a CONSTANT-BUILD pool -> the estimator's own
    cross-drive floor, for every key and for every key's contrast against CTRL."""
    by = {}
    for r in pool:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    segs = sorted(by)
    lr = {k: [] for k in keys}
    ct = {k: [] for k in keys}
    used = 0
    for _ in range(nrep):
        p = RNG.permutation(len(segs))
        h = len(segs) // 2
        A = [r for i in p[:h] for r in by[segs[i]]]
        B = [r for i in p[h:] for r in by[segs[i]]]
        v, nc = strat_multi(G.episodes(A), G.episodes(B), list(keys))
        if not nc or not np.isfinite(v.get(CTRL, np.nan)):
            continue
        used += 1
        for k in keys:
            if np.isfinite(v.get(k, np.nan)):
                lr[k].append(v[k])
                ct[k].append(v[k] - v[CTRL])
    if not used:
        print(f"    {tag}: no usable placebo partition")
        return None
    print(f"    {tag}: {used}/{nrep} usable partitions of {len(segs)} segments")
    print(f"      {'band':10s} {'sd(log ratio)':>14s} {'ratio 95 % band':>24s} "
          f"{'sd(log contrast)':>17s} {'contrast 95 % band':>24s}")
    out = {}
    for k in keys:
        a, b = np.array(lr[k]), np.array(ct[k])
        if not len(a):
            continue
        rl, rh = np.exp(np.percentile(a, [2.5, 97.5]))
        cl, ch = np.exp(np.percentile(b, [2.5, 97.5]))
        out[k] = dict(sd_log_ratio=float(a.std()), ratio_band=[float(rl), float(rh)],
                      sd_log_contrast=float(b.std()), contrast_band=[float(cl), float(ch)],
                      n=int(len(a)))
        print(f"      {k:10s} {a.std():14.3f} {f'[{rl:.3f}, {rh:.3f}]':>24s} "
              f"{b.std():17.3f} {f'[{cl:.3f}, {ch:.3f}]':>24s}")
    return out


def verdict(m, p, key, tag):
    """Is the measured effect on `key` outside its own constant-build placebo band?"""
    if not (m and p and key in m and key in p):
        print(f"    {tag}: not scoreable")
        return None
    lc, ratio = m[key]["log_contrast"], m[key]["ratio"]
    sd = p[key]["sd_log_contrast"]
    lo, hi = p[key]["contrast_band"]
    inside = lo <= m[key]["contrast"] <= hi
    ci = m[key]["contrast_ci"]
    sig = abs(lc) / sd if sd > 0 else np.nan
    v = dict(band=key, ratio=ratio, ratio_ci=m[key]["ci"], contrast=m[key]["contrast"],
             contrast_ci=ci, placebo_band=[lo, hi], placebo_sd=sd, sigma=float(sig),
             inside_placebo=bool(inside),
             verdict=("FLAT -- inside its own constant-build placebo band" if inside else
                      "RESOLVABLE -- outside the constant-build placebo band"))
    print(f"    {tag} [{key}]  ratio {ratio:.3f} [{m[key]['ci'][0]:.3f},{m[key]['ci'][1]:.3f}]   "
          f"contrast {m[key]['contrast']:.3f} [{ci[0]:.3f},{ci[1]:.3f}]")
    print(f"      placebo band [{lo:.3f}, {hi:.3f}]  sd(log) {sd:.3f}  =>  {sig:.2f} sigma   "
          f"{v['verdict']}")
    return v


# =================================================================================================
def d1():
    hdr("D1   DID V89's K1 (0xC40D2 102 -> 204) REGRESS THE GRINDING?\n"
        "     V89 (routes 75+76) vs V88 (route 73).  Subject: e_18-22 (the operator's grinding\n"
        "     band) and e_6-9 (micro-ratcheting/ratcheting).  Negative control: e_32-38.\n"
        "     A ratio ABOVE 1.00 on e_18-22 means V89 made the grinding band WORSE than V88.")

    sub("wheel-order arithmetic, DERIVED HERE (circumference 2.073-2.088 m, guard 0.8 Hz)")
    for k in VETO_BANDS:
        lo, hi = BAND_OF[k]
        w = order_windows(lo, hi)
        print(f"    {k:9s} clean above {clean_above(lo, hi):5.2f} m/s "
              f"({clean_above(lo, hi)*3.6:5.1f} km/h)   " +
              "  ".join(f"k{k_}[{a:.1f},{b:.1f}]" for k_, (a, b) in w.items() if a < 30))
    print("    🛑 There is NO speed stratum clean for all three at once: above 21.6 m/s order 3 can")
    print("       reach the 32-38 Hz CONTROL, which inverts the usual screening asymmetry.")

    R = build_records()
    E = {b: eng(R[b], b) for b in ARMS}
    P = E["V89/r75"] + E["V89/r76"]
    B = E["V88/r73"]

    sub("EXPOSURE, per arm (engaged windows, parked segments excluded)")
    OUT["census"] = {b: census(E[b], b) for b in ARMS}
    OUT["census"]["V89 pooled"] = census(P, "V89 pooled")

    sub("CONTROL 1 -- each arm's OWN split-half null.  A ratio inside it is NOT RESOLVABLE.")
    OUT["split_half"] = {b: split_half(E[b], b) for b in ARMS}

    strata = []
    strata.append(("ALL ENGAGED (no veto)", P, B))
    kp = [r for r in P if not order_hit_any(r)]
    kb = [r for r in B if not order_hit_any(r)]
    strata.append(("SYMMETRIC ORDER VETO (any order on any of the 3 bands)", kp, kb))
    for vmin, nm in ((20.46, "v >= 20.46 m/s (6-9 Hz intrinsically clean)"),
                     (22.2, "v >= 22.2 m/s (the brief's preferred highway stratum)")):
        strata.append((nm, [r for r in P if r["v"] >= vmin], [r for r in B if r["v"] >= vmin]))

    OUT["strata"] = {}
    for nm, A, Bs in strata:
        hdr(f"STRATUM: {nm}")
        ca, cb = census(A, "V89 pooled"), census(Bs, "V88/r73")
        if len(A) < 30 or len(Bs) < 30:
            print("    🛑 exposure too thin -- NOT SCOREABLE on this stratum")
            OUT["strata"][nm] = dict(census_A=ca, census_B=cb, scoreable=False)
            continue
        sub("CONTROL 3 -- the PLACEBO-PAIR NULL on this stratum "
            "(same-build segment partitions of r75+r76)")
        p = placebo_null(A, "V89 pool (r75+r76)", nrep=300)
        sub("THE MEASUREMENT, V89 pooled / V88 r73")
        m = measured(A, Bs, "V89 pooled / V88 r73")
        sub("VERDICT against the constant-build floor")
        vv = {k: verdict(m, p, k, "V89/V88") for k in (SUBJ1, SUBJ2, PLACEBO)}
        OUT["strata"][nm] = dict(census_A=ca, census_B=cb, scoreable=True,
                                 placebo=p, measured=m, verdict=vv)

    hdr("★ THE SINGLE CLEANEST PLACEBO -- whole r75 vs whole r76, SAME BUILD, different drives.\n"
        "  Whatever this reads is the estimator's honest cross-drive floor with no firmware change.")
    OUT["r75_vs_r76"] = measured(E["V89/r75"], E["V89/r76"], "r75 / r76 (SAME BUILD, V89)")

    hdr("PER-ROUTE, so a single-route artefact cannot hide inside the pool")
    OUT["per_route"] = {}
    for a in V89POOL:
        OUT["per_route"][a] = measured(E[a], B, f"{a} / V88 r73")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    json.dump(OUT, open(OUTDIR / "v90_d1_k1_regression.json", "w"), indent=1, default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d1_k1_regression.json'}")


# =================================================================================================
#  D3 -- THE `gp-0x6b26` DISTRIBUTION.  No build has ever telemetered this cell.
# =================================================================================================
#   CAN 427 (`0x1AB`) MOTOR_TORQUE = clamp(|gp-0x6b26| * 5 >> 3, 0, 0x3FF) at 50 Hz.
#   Inverting the integer shift EXACTLY:  wire = floor(|x| * 5 / 8)  =>  |x| in
#   [ 8*wire/5 , (8*wire + 7)/5 ]  -- a bracket 1.4 counts wide.  The midpoint estimator
#   |x|^ = (8*wire + 3.5)/5 has a worst-case error of +-0.7 counts.  Both are carried.
#   The lane is hard-clamped to +-511 by `0xC407E` (verified `ff01` on the V89 image), and
#   511*5>>3 = 319 < 1023, so the WIRE never clips: every wire value is an honest measurement.
LSB_LO, LSB_MID, LSB_HI = 8.0 / 5.0, 8.0 / 5.0, 8.0 / 5.0
LANE_CLAMP = 511
PIN_M = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0)
RATE_BINS_D3 = [("<1 °/s", 0.0, 1.0), ("micro 1-13", 1.0, 13.0), ("ratchet 13-50", 13.0, 50.0),
                ("macro >=50", 50.0, 1e9)]
SPEED_BINS_D3 = [("0-5 km/h", 0.0, 1.389), ("5-20", 1.389, 5.556), ("20-50", 5.556, 13.889),
                 ("50-80", 13.889, 22.222), (">=80", 22.222, 1e9)]
D3_BANDS_50 = [("2-4", 2.0, 4.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0), ("15-22", 15.0, 22.0)]
D3_BANDS_100 = [("6-9", 6.0, 9.0), ("15-22", 15.0, 22.0), ("26-31", 26.0, 31.0),
                ("32-38 (control)", 32.0, 38.0), ("40-49", 40.0, 49.0)]
NW50, HOP50 = 256, 128          # 5.12 s windows on the 50 Hz 427 grid
NW100, HOP100 = 512, 256        # 5.12 s windows on the 100 Hz 0x14A grid


def _load77():
    return np.load(OUTDIR / "r77.npz", allow_pickle=True)


def _b26_stream(z):
    """The signed `gp-0x6b26` reconstruction on the 427 timestamps, plus its context.

    🛑 The SIGN comes from the cave's b7 at 100 Hz, paired to each 427 frame by NEAREST 0x14A
    sample within 10 ms.  It is NEVER interpolated: `raw14_b4` is a BITFIELD, and
    `np.interp` on a bitfield returns fractional values whose bits are meaningless.
    (`v88_d1_exposure.grid` does interpolate it -- that column must not be used for bit tests.)
    """
    t = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    o = np.argsort(t, kind="stable")
    t, wire = t[o], wire[o]

    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    o14 = np.argsort(t14, kind="stable")
    t14, b4 = t14[o14], b4[o14]
    j = np.clip(np.searchsorted(t14, t), 1, len(t14) - 1)
    j = np.where(np.abs(t14[j - 1] - t) < np.abs(t14[j] - t), j - 1, j)
    paired = np.abs(t14[j] - t) <= 0.010
    neg = (b4[j] & B7_MASK) != 0

    absx_lo = 8.0 * wire / 5.0
    absx = (8.0 * wire + 3.5) / 5.0
    absx_hi = (8.0 * wire + 7.0) / 5.0
    signed = np.where(neg, -absx, absx)

    rt = np.asarray(z["t"], float)
    lat = np.interp(t, rt, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.abs(np.interp(t, rt, np.asarray(z["cs_v"], float)))
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0])
    rate = np.interp(t, rt, np.abs(np.gradient(ang) / dt))
    seg = np.round(np.interp(t, rt, np.asarray(z["seg"], float))).astype(int)
    press = np.interp(t, rt, np.asarray(z["cs_press"], float)) > 0.5
    return dict(t=t, wire=wire, absx=absx, absx_lo=absx_lo, absx_hi=absx_hi, signed=signed,
                neg=neg, paired=paired, lat=lat, v=v, rate=rate, seg=seg, press=press,
                fs=1.0 / float(np.median(np.diff(t))))


B7_MASK = 0x80


def _pct(x, ps=(50, 75, 90, 95, 99, 99.9)):
    return {f"p{p}": float(np.percentile(x, p)) for p in ps} | {"max": float(x.max()),
                                                                "n": int(len(x))}


def _dist_row(x, tag):
    if len(x) < 50:
        print(f"      {tag:26s} n={len(x):6,d}  -- too few, not reported")
        return None
    d = _pct(x)
    d["clamp_duty"] = float(np.mean(x >= LANE_CLAMP))
    d["pin"] = {f"m={m}": float(np.mean(x * m >= LANE_CLAMP)) for m in PIN_M}
    print(f"      {tag:26s} n={d['n']:7,d}  p50 {d['p50']:6.1f}  p75 {d['p75']:6.1f}  "
          f"p90 {d['p90']:6.1f}  p95 {d['p95']:6.1f}  p99 {d['p99']:6.1f}  "
          f"p99.9 {d['p99.9']:6.1f}  max {d['max']:6.1f}  | clamp duty {d['clamp_duty']:.6f}")
    return d


def _bandpow(x, fs, bands, nw, hop, runs, blocks):
    """Per-window band rms of a signed series, median + block bootstrap over segment blocks."""
    from scipy.signal import butter, filtfilt
    out = {}
    yb = {nm: filtfilt(*butter(2, [lo, hi], btype="band", fs=fs), x) for nm, lo, hi in bands}
    vals = {nm: [] for nm in yb}
    units = []
    for a, b in runs:
        for i in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + i, a + i + nw)
            units.append(int(np.median(blocks[sl])) * 1000 + (i // (hop * 8)))
            for nm, y in yb.items():
                vals[nm].append(float(np.std(y[sl])))
    if not units:
        return {}
    import v87_probe_6b98 as P87
    for nm in yb:
        out[nm] = P87.block_boot(vals[nm], units)
    out["_n_windows"] = len(units)
    return out


def _shuffle_runs(x, runs, seed=90_3003):
    """Permute the series WITHIN each engaged run: marginal preserved, temporal structure gone.
    This is the null a cross-band density comparison has to beat."""
    r = np.random.default_rng(seed)
    y = np.array(x, float, copy=True)
    for a, b in runs:
        y[a:b] = r.permutation(y[a:b])
    return y


def _density_table(label, bands, meas, ctrl):
    """Band rms is NOT comparable across bands of different width; density = rms/sqrt(BW) is."""
    print(f"      {label}")
    print(f"      {'band':18s} {'BW':>5s} {'rms':>9s} {'[  2.5 %, 97.5 %]':>21s} "
          f"{'DENSITY':>9s} {'shuffled':>9s} {'meas/shuf':>10s}")
    for nm, lo, hi in bands:
        m, c = meas.get(nm), ctrl.get(nm)
        if not m or not np.isfinite(m["v"]):
            continue
        bw = hi - lo
        dm, dc = m["v"] / np.sqrt(bw), (c["v"] / np.sqrt(bw) if c else np.nan)
        print(f"      {nm:18s} {bw:5.1f} {m['v']:9.4f} [{m['lo']:9.4f},{m['hi']:9.4f}] "
              f"{dm:9.4f} {dc:9.4f} {dm/dc if dc else np.nan:10.3f}")
        m["bandwidth"] = bw
        m["density"] = float(dm)
        m["density_shuffled"] = float(dc)
        m["density_ratio"] = float(dm / dc) if dc else float("nan")


def d3():
    z = _load77()
    S = _b26_stream(z)
    hdr("D3   THE `gp-0x6b26` DISTRIBUTION -- the cell V90 was built to measure.\n"
        "     427 carries clamp(|gp-0x6b26|*5>>3, 0, 0x3FF) at 50 Hz; the cave's b7 carries its\n"
        "     SIGN at 100 Hz.  The lane is hard-clamped to +-511 by `0xC407E`.")
    print(f"    427 frames {len(S['t']):,} at {S['fs']:.2f} Hz   "
          f"sign paired to a 0x14A frame within 10 ms on {100*S['paired'].mean():.3f} % "
          f"(median |dt| {1e3*np.median(np.abs(np.diff(S['t']))):.2f} ms between 427 frames)")
    print(f"    wire range [{S['wire'].min()}, {S['wire'].max()}]  "
          f"=> |gp-0x6b26| in [{S['absx_lo'].min():.1f}, {S['absx_hi'].max():.1f}] counts, "
          f"midpoint estimator +-0.7 ct")
    print(f"    🛑 WIRE SATURATION (>= 1023): {float(np.mean(S['wire'] >= 1023)):.6f}  "
          f"=> every sample is an honest measurement, none is a rail readout")
    OUT["stream"] = dict(n=len(S["t"]), fs=float(S["fs"]),
                         sign_paired_frac=float(S["paired"].mean()),
                         wire_min=int(S["wire"].min()), wire_max=int(S["wire"].max()),
                         wire_sat_frac=float(np.mean(S["wire"] >= 1023)))

    eng_m = S["lat"] & S["paired"]
    man_m = (~S["lat"]) & S["paired"]
    man_mv = man_m & (S["v"] > 0.5)

    sub("★ THE HEADLINE -- |gp-0x6b26| distribution and the duty AT the +-511 clamp")
    OUT["dist"] = {}
    for tag, m in (("ENGAGED", eng_m), ("MANUAL (all)", man_m), ("MANUAL moving >0.5 m/s", man_mv)):
        OUT["dist"][tag] = _dist_row(S["absx"][m], tag)

    sub("by |WHEEL RATE| (engaged) -- the operator's own regimes")
    OUT["dist_rate"] = {}
    for nm, lo, hi in RATE_BINS_D3:
        m = eng_m & (S["rate"] >= lo) & (S["rate"] < hi)
        OUT["dist_rate"][nm] = _dist_row(S["absx"][m], nm)

    sub("by SPEED (engaged)")
    OUT["dist_speed"] = {}
    for nm, lo, hi in SPEED_BINS_D3:
        m = eng_m & (S["v"] >= lo) & (S["v"] < hi)
        OUT["dist_speed"][nm] = _dist_row(S["absx"][m], nm)

    sub("🛑 PINNING DUTY AS A FUNCTION OF GAIN MULTIPLIER m -- P(|gp-0x6b26| * m >= 511)\n"
        "    A saturating lane is a RELAY, and V80 is what a relay in this class feels like.\n"
        "    ⚠ OPEN-LOOP extrapolation: it holds the observed distribution FIXED under the dose.\n"
        "      In closed loop more damping REDUCES the motion that drives `gp-0x6c2c`, so this\n"
        "      is a CONSERVATIVE bound (it over-states pinning), but it is still an extrapolation.")
    print(f"      {'stratum':26s} " + "".join(f"{'m='+str(m):>10s}" for m in PIN_M))
    OUT["pinning"] = {}
    rows = [("ENGAGED", eng_m)] + [(nm, eng_m & (S["rate"] >= lo) & (S["rate"] < hi))
                                   for nm, lo, hi in RATE_BINS_D3] + \
           [(nm, eng_m & (S["v"] >= lo) & (S["v"] < hi)) for nm, lo, hi in SPEED_BINS_D3]
    for nm, m in rows:
        x = S["absx"][m]
        if len(x) < 50:
            continue
        p = [float(np.mean(x * mm >= LANE_CLAMP)) for mm in PIN_M]
        OUT["pinning"][nm] = dict(zip([str(m) for m in PIN_M], p))
        print(f"      {nm:26s} " + "".join(f"{v:10.6f}" for v in p))
    x = S["absx"][eng_m]
    m1 = max([m for m in np.arange(1.0, 20.01, 0.05) if np.mean(x * m >= LANE_CLAMP) < 0.01],
             default=np.nan)
    m01 = max([m for m in np.arange(1.0, 20.01, 0.05) if np.mean(x * m >= LANE_CLAMP) < 0.001],
              default=np.nan)
    mzero = LANE_CLAMP / float(x.max())
    OUT["m_budget"] = dict(m_pin_lt_1pct=float(m1), m_pin_lt_0p1pct=float(m01),
                           m_never_pins=float(mzero), engaged_max=float(x.max()))
    print(f"\n      LARGEST m with pinning duty < 1.0 %  : {m1:5.2f}x")
    print(f"      LARGEST m with pinning duty < 0.1 %  : {m01:5.2f}x")
    print(f"      LARGEST m that NEVER pins (max = {x.max():.0f} ct): {mzero:5.2f}x")

    sub("BAND CONTENT of the SIGNED reconstruction, engaged, on the 50 Hz 427 grid\n"
        "    (Nyquist 24.9 Hz -- 26-31 Hz CANNOT be measured here; see the 100 Hz sign channel)\n"
        "    🛑 CONTROL FIRST: the bands have DIFFERENT WIDTHS, so a raw band rms cannot be\n"
        "      compared across them -- white noise alone gives rms proportional to sqrt(BW).\n"
        "      Every row therefore carries DENSITY = rms / sqrt(BW), and a WITHIN-RUN SHUFFLE of\n"
        "      the same series (marginal preserved, temporal structure destroyed) as the null.")
    import _r31_common as C31
    # 🛑 `runs_of` is a GENERATOR -- materialise it, or the first consumer eats it and
    # every later consumer silently sees ZERO windows (this cost the shuffled control once).
    runs = list(C31.runs_of(eng_m, S["t"], NW50, max_gap=0.10))
    OUT["bands_50"] = _bandpow(S["signed"], S["fs"], D3_BANDS_50, NW50, HOP50, runs, S["seg"])
    OUT["bands_50_shuffled"] = _bandpow(_shuffle_runs(S["signed"], runs), S["fs"], D3_BANDS_50,
                                        NW50, HOP50, runs, S["seg"])
    _density_table("signed gp-0x6b26 (counts)", D3_BANDS_50, OUT["bands_50"],
                   OUT["bands_50_shuffled"])

    sub("the 100 Hz SIGN channel (b7, +-1), the ONLY channel above 427's 24.9 Hz Nyquist\n"
        "    🛑 A 1-bit comparator is a SPECTRAL instrument only -- amplitude claims do NOT travel.\n"
        "    32-38 Hz is carried as the negative control so the 26-31 row has a reference.")
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    o = np.argsort(t14, kind="stable")
    t14, b4 = t14[o], b4[o]
    sgn = np.where((b4 & B7_MASK) != 0, -1.0, 1.0)
    rt = np.asarray(z["t"], float)
    lat14 = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
    seg14 = np.round(np.interp(t14, rt, np.asarray(z["seg"], float))).astype(int)
    fs14 = 1.0 / float(np.median(np.diff(t14)))
    runs14 = list(C31.runs_of(lat14, t14, NW100, max_gap=0.05))
    OUT["bands_100_sign"] = _bandpow(sgn, fs14, D3_BANDS_100, NW100, HOP100, runs14, seg14)
    OUT["bands_100_sign_shuffled"] = _bandpow(_shuffle_runs(sgn, runs14), fs14, D3_BANDS_100,
                                              NW100, HOP100, runs14, seg14)
    _density_table("b7 sign (+-1, dimensionless)", D3_BANDS_100, OUT["bands_100_sign"],
                   OUT["bands_100_sign_shuffled"])
    print(f"      fs(0x14A) {fs14:.2f} Hz, {OUT['bands_100_sign'].get('_n_windows', 0)} windows")

    json.dump(OUT, open(OUTDIR / "v90_d3_b26_distribution.json", "w"), indent=1, default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d3_b26_distribution.json'}")


# =================================================================================================
#  D5 -- THE (b6, b5) 2x2 AND THE OBSERVER GATE, conditioned on wheel rate
# =================================================================================================
#   b6 = |gp-0x6bf6| >= 512  (|MODEL|) ;  b5 = gp-0x6ae2 != 0  (FRICTION relay active).
#   Since gp-0x6ae2 ~ 0.0773 * |gp-0x6bf6| * relay, frames with b6 = 1 AND b5 = 0 are
#   *large model, zero friction* => relay ~ 0 (polarity zero or a rate crossing), NOT a small
#   model.  That is the |model|-vs-ratio confound read directly off a contingency table.
#   b4 = gp-0x6c00 < 0 is the observer gate FAILING.
def d5():
    z = _load77()
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    o = np.argsort(t14, kind="stable")
    t14, b4 = t14[o], b4[o]
    rt = np.asarray(z["t"], float)
    lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.abs(np.interp(t14, rt, np.asarray(z["cs_v"], float)))
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0])
    rate = np.interp(t14, rt, np.abs(np.gradient(ang) / dt))
    b6 = (b4 & 0x40) != 0
    b5 = (b4 & 0x20) != 0
    gate = (b4 & 0x10) != 0

    hdr("D5   THE (b6, b5) 2x2 AND THE OBSERVER GATE b4, CONDITIONED ON WHEEL RATE\n"
        "     b6 = |gp-0x6bf6| >= 512 (|MODEL|)   b5 = gp-0x6ae2 != 0 (FRICTION relay active)\n"
        "     (b6=1, b5=0) == large model with ZERO friction  =>  the relay is off, NOT a small\n"
        "     model.  b4 = gp-0x6c00 < 0 == the observer gate FAILED.")
    OUT["d5"] = {}
    for tag, base in (("ENGAGED", lat), ("MANUAL", ~lat), ("MANUAL moving", (~lat) & (v > 0.5))):
        print(f"\n    {tag}  (n={int(base.sum()):,})")
        print(f"      {'|wheel rate|':16s} {'n':>8s} {'b6=0,b5=0':>10s} {'b6=0,b5=1':>10s} "
              f"{'b6=1,b5=0':>10s} {'b6=1,b5=1':>10s} {'P(b5|b6=1)':>11s} {'GATE b4':>9s}")
        rows = [("ALL", 0.0, 1e9)] + [(nm, lo, hi) for nm, lo, hi in RATE_BINS_D3]
        for nm, lo, hi in rows:
            m = base & (rate >= lo) & (rate < hi)
            n = int(m.sum())
            if n < 100:
                print(f"      {nm:16s} {n:8,d}   -- too few")
                continue
            c = {f"b6={i},b5={j}": float(np.mean(m & (b6 == bool(i)) & (b5 == bool(j))) / m.mean())
                 for i in (0, 1) for j in (0, 1)}
            nb6 = (m & b6).sum()
            pb5 = float((m & b6 & b5).sum() / nb6) if nb6 else float("nan")
            g = float(gate[m].mean())
            OUT["d5"][f"{tag}/{nm}"] = dict(n=n, **c, p_b5_given_b6=pb5, gate_duty=g)
            print(f"      {nm:16s} {n:8,d} {c['b6=0,b5=0']:10.4f} {c['b6=0,b5=1']:10.4f} "
                  f"{c['b6=1,b5=0']:10.4f} {c['b6=1,b5=1']:10.4f} {pb5:11.4f} {g:9.6f}")

    tot_gate = int(gate.sum())
    OUT["d5"]["gate_total_failures"] = tot_gate
    OUT["d5"]["gate_total_frames"] = int(len(gate))
    print(f"\n    🛑 OBSERVER GATE: {tot_gate} failing frames out of {len(gate):,} "
          f"({100.0*tot_gate/len(gate):.6f} %) over {len(gate)/101.15/60:.2f} minutes.")
    print("       For a GATE question 0.000 IS the answer: `gp-0x6c00` never went negative on this")
    print("       drive, engaged or manual, in any wheel-rate bin.  The rung is railed and carries")
    print("       no further information -- but the question it was bought to answer is ANSWERED.")
    json.dump(OUT.get("d5", {}), open(OUTDIR / "v90_d5_gate_and_2x2.json", "w"), indent=1,
              default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d5_gate_and_2x2.json'}")


# =================================================================================================
#  D6 -- THE THREE SYMPTOMS ON ROUTE 77, AGAINST THE CORPUS
# =================================================================================================
#   ★ Route 77 is a THIRD drive on firmware that is FUNCTIONALLY IDENTICAL to V89 (V90 changes no
#     calibration cell).  So r77-vs-r75/r76 is a CONSTANT-BUILD placebo by construction, and
#     r77 can be folded into the V89 arm of D1 to enlarge its exposure.  Both are done here.
R77 = dict(cache=OUTDIR, pfx="r77s", segs=list(range(21)), parked=[], stem="r77", kd=9.89)


def _records77(rebuild=False):
    import pickle
    import _r47_lib as R47
    import _r4f_lib as R4F
    pkl = OUTDIR / "records_v90_score.pkl"
    if pkl.exists() and not rebuild:
        st = pickle.load(open(pkl, "rb"))
        if st.get("__bands__") == sorted(M.BANDS_EXT):
            return st["V90/r77"]
    R4F.install_fs()
    G.BUILDS["V90/r77"] = dict(cache=R77["cache"], pfx=R77["pfx"], segs=R77["segs"], kd=R77["kd"])
    print("  wrecs V90/r77 ...", flush=True)
    rec = M.augment2(R47.augment(G.wrecs("V90/r77")))
    print(f"    {len(rec)} windows", flush=True)
    pickle.dump({"__bands__": sorted(M.BANDS_EXT), "V90/r77": rec}, open(pkl, "wb"))
    return rec


def d6():
    hdr("D6   THE THREE SYMPTOMS ON ROUTE 77 (V90 == V89 functionally), AGAINST THE CORPUS\n"
        "     e_6-9 = micro-ratcheting / ratcheting · e_18-22 = grinding · 26-31 and 40-49 =\n"
        "     grind #2, which the operator feels ON HIGHWAY-SPEED CURVES AND LANE CHANGES,\n"
        "     so that regime is scored specifically and NOT as a route average.")
    R = build_records()
    E = {b: eng(R[b], b) for b in ARMS}
    r77 = [r for r in _records77() if r["eng"] == 1]
    E["V90/r77"] = r77
    BUILDS["V90/r77"] = R77
    ALL = ARMS + ["V90/r77"]

    sub("EXPOSURE, all four arms")
    OUT["d6_census"] = {b: census(E[b], b) for b in ALL}

    sub("ABSOLUTE band levels, engaged, per arm (block-bootstrap median CI over ~10.2 s units).\n"
        "    🛑 UNMATCHED -- the arms are not exposure-matched; these are for SCALE, and the\n"
        "      matched comparison is the ratio table below.")
    OUT["d6_levels"] = {}
    for b in ALL:
        row = {}
        for k in (SUBJ2, SUBJ1, "e_26-31", CTRL, "e_40-49", EXPO):
            m, lo, hi = G.boot_median_ci(E[b], k, RNG, nboot=1200)
            row[k] = [float(m), float(lo), float(hi)]
        OUT["d6_levels"][b] = row
        print(f"      {b:10s} n={len(E[b]):4d} blk={nblk(E[b]):3d}  " +
              "  ".join(f"{k.split('_')[1]} {row[k][0]:6.1f}[{row[k][1]:5.1f},{row[k][2]:6.1f}]"
                        for k in (SUBJ2, SUBJ1, "e_26-31", CTRL)))

    sub("★ CONSTANT-BUILD PLACEBO, by construction: r77 vs r75 and r77 vs r76 (V90 == V89).\n"
        "    Whatever these read is the floor. Any V90-vs-V88 claim must clear it.")
    OUT["d6_placebo"] = {}
    for b in V89POOL:
        OUT["d6_placebo"][f"r77/{b}"] = measured(r77, E[b], f"V90/r77 / {b}  (SAME FIRMWARE)")

    sub("THE CROSS-BUILD COMPARISON with r77 FOLDED INTO the V89 arm -- D1 with more exposure")
    pool3 = E["V89/r75"] + E["V89/r76"] + r77
    OUT["d6_pooled"] = {}
    for nm, A, B in (("all engaged", pool3, E["V88/r73"]),
                     ("symmetric order veto",
                      [r for r in pool3 if not order_hit_any(r)],
                      [r for r in E["V88/r73"] if not order_hit_any(r)]),
                     ("v >= 22.2 m/s",
                      [r for r in pool3 if r["v"] >= 22.2],
                      [r for r in E["V88/r73"] if r["v"] >= 22.2])):
        print(f"\n    stratum: {nm}")
        p = placebo_null([r for r in pool3 if (nm != "v >= 22.2 m/s" or r["v"] >= 22.2)
                          and (nm != "symmetric order veto" or not order_hit_any(r))],
                         "V89+V90 pool (r75+r76+r77)", nrep=250)
        m = measured(A, B, "V89/V90 pooled / V88 r73")
        OUT["d6_pooled"][nm] = dict(placebo=p, measured=m,
                                    verdict={k: verdict(m, p, k, "pooled/V88")
                                             for k in (SUBJ1, SUBJ2, PLACEBO)})

    sub("★ GRIND #2 REGIME -- the operator feels it on HIGHWAY-SPEED CURVES AND LANE CHANGES.\n"
        "    Regime = engaged AND v >= 22.2 m/s AND |wheel rate| >= 5 °/s (a curve or a lane\n"
        "    change at highway speed), scored on 26-31 and 40-49 Hz with the 32-38 control.")
    OUT["d6_grind2"] = {}
    for b in ALL:
        s = [r for r in E[b] if r["v"] >= 22.2 and r["rate"] >= 5.0]
        print(f"      {b:10s} n={len(s):4d} blk={nblk(s):3d}")
        if len(s) < 20:
            OUT["d6_grind2"][b] = dict(n=len(s), scoreable=False)
            continue
        row = {}
        for k in ("e_26-31", "e_40-49", CTRL, SUBJ1):
            m_, lo, hi = G.boot_median_ci(s, k, RNG, nboot=1200)
            row[k] = [float(m_), float(lo), float(hi)]
            print(f"         {k:9s} {m_:7.1f} [{lo:6.1f},{hi:7.1f}]")
        OUT["d6_grind2"][b] = dict(n=len(s), blk=nblk(s), levels=row, scoreable=True)

    json.dump({k: v for k, v in OUT.items() if k.startswith("d6")},
              open(OUTDIR / "v90_d6_symptoms.json", "w"), indent=1, default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d6_symptoms.json'}")


# =================================================================================================
#  D4 -- THE TRANSFER, AND THE CAVEAT THAT GOVERNS IT
# =================================================================================================
#  🛑 STATED FIRST, NOT BURIED.  `gp-0x6b26` is DERIVED FROM motor rate, and motor rate is CAUSED BY
#  column motion.  This is a CLOSED LOOP.  A naive `b26 -> column` transfer therefore measures
#  FEEDTHROUGH, not causality, and the record has already burned itself on exactly this: the
#  `cmd -> column` coherence read 0.254 ENGAGED against 0.544 MANUAL, where the LKAS command is
#  identically absent -- i.e. the "transfer" was largest where the input did not exist.
#  The controls run here, and what each can and cannot settle:
#    (i)  SHUFFLED PAIRS  -- window i's response against window j's input.  Kills only the
#         "any two band-limited series look coherent" artefact.  Necessary, nowhere near sufficient.
#    (ii) THE MANUAL ARM  -- LKAS absent, damping lane still running.  If the relation is pure
#         feedthrough it should SURVIVE in manual; if it needs the LKAS command it should collapse.
#    (iii) GROUP DELAY SIGN -- forward causation requires the response to LAG the input.  A
#         negative group delay is a positive proof of feedthrough/closed loop, not of causation.
#  None of these can turn the transfer into a plant gain.  If they all pass it is still a
#  correlation inside a loop.  That is reported as the answer, not worked around.
NW_Z, HOP_Z = 512, 256              # 5.12 s at 100 Hz
Z_BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
           ("12-16", 12.0, 16.0)]
DEG2RAD = np.pi / 180.0


def _xspec(x, y, fs, nw):
    """One-window cross spectrum, Hann-tapered, both series detrended."""
    w = np.hanning(nw)
    X = np.fft.rfft((x - x.mean()) * w)
    Y = np.fft.rfft((y - y.mean()) * w)
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    return f, X, Y


def _band_transfer(pairs, fs, nw, bands):
    """Welch-averaged Sxy/Sxx, coherence^2 and group delay, per band, over a list of (x, y)."""
    acc = None
    for x, y in pairs:
        f, X, Y = _xspec(x, y, fs, nw)
        Sxx, Syy, Sxy = np.abs(X) ** 2, np.abs(Y) ** 2, np.conj(X) * Y
        acc = (Sxx, Syy, Sxy) if acc is None else (acc[0] + Sxx, acc[1] + Syy, acc[2] + Sxy)
    if acc is None:
        return {}
    Sxx, Syy, Sxy = acc
    out = {}
    for nm, lo, hi in bands:
        m = (f >= lo) & (f <= hi)
        sxx, syy, sxy = Sxx[m].sum(), Syy[m].sum(), Sxy[m].sum()
        coh = float(np.abs(sxy) ** 2 / (sxx * syy)) if sxx * syy > 0 else np.nan
        ph = float(np.angle(sxy))
        out[nm] = dict(gain=float(np.abs(sxy) / sxx) if sxx > 0 else np.nan,
                       phase_deg=float(np.degrees(ph)), coh2=coh,
                       re_over_sxx=float(np.real(sxy) / sxx) if sxx > 0 else np.nan,
                       f_lo=lo, f_hi=hi, n_pairs=len(pairs))
    return out


def _wins(mask, t, nw, hop, arrays, max_gap=0.05):
    import _r31_common as C31
    out = []
    for a, b in list(C31.runs_of(mask, t, nw, max_gap=max_gap)):
        for i in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + i, a + i + nw)
            out.append(tuple(A[sl] for A in arrays))
    return out


def d4():
    z = _load77()
    hdr("D4   THE TRANSFER, AND THE CAVEAT THAT GOVERNS IT\n"
        "     🛑 `gp-0x6b26` is DERIVED FROM motor rate, which is CAUSED BY column motion.  This is\n"
        "     a CLOSED LOOP.  A naive b26->column transfer is FEEDTHROUGH, not causality.  Three\n"
        "     controls are run; none of them can turn the number into a plant gain.")
    OUT["d4"] = {}

    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)                    # column torque, 0x18F, counts
    rate = np.asarray(z["rate_f"], float) * DEG2RAD    # wheel rate -> rad/s (⚠ scale ~25 % low)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    fs = 1.0 / float(np.median(np.diff(t)))

    sub("Re(Z) = Re(S_Tω / S_ωω), the real part of the DRIVING-POINT IMPEDANCE.\n"
        "    Negative Re(Z) == negative damping.  Predicted phase: inertia +90°, damper 0°,\n"
        "    spring -90°, negative damping 180°.")
    arms = {
        "ENGAGED hands-off moving": lat & (~press) & (v > 0.5),
        "MANUAL hands-off moving": (~lat) & (~press) & (v > 0.5),
        "ENGAGED hands-ON moving": lat & press & (v > 0.5),
    }
    for nm, m in arms.items():
        W = _wins(m, t, NW_Z, HOP_Z, (rate, tq))
        print(f"\n      {nm}: {len(W)} windows of {NW_Z/fs:.2f} s  "
              f"({float(m.sum())/fs:.1f} s of frames)")
        if len(W) < 6:
            print("        🛑 TOO FEW WINDOWS -- the control does not exist on this route. "
                  "NOT SCOREABLE, and I am not manufacturing it.")
            OUT["d4"][f"Z/{nm}"] = dict(n_windows=len(W), scoreable=False)
            continue
        r = _band_transfer(W, fs, NW_Z, Z_BANDS)
        # shuffled-pairs control: window i's torque against window j's rate
        idx = RNG.permutation(len(W))
        Wsh = [(W[i][0], W[(idx[i] + 1) % len(W)][1]) for i in range(len(W))]
        rs = _band_transfer(Wsh, fs, NW_Z, Z_BANDS)
        print(f"        {'band':8s} {'Re(Z) ct·s/rad':>16s} {'|Z|':>10s} {'phase':>9s} "
              f"{'coh²':>7s} {'coh² shuf':>10s}")
        for b, _, _ in Z_BANDS:
            a_, s_ = r[b], rs[b]
            print(f"        {b:8s} {a_['re_over_sxx']:16.1f} {a_['gain']:10.1f} "
                  f"{a_['phase_deg']:8.1f}° {a_['coh2']:7.3f} {s_['coh2']:10.3f}")
        OUT["d4"][f"Z/{nm}"] = dict(n_windows=len(W), scoreable=True, bands=r, shuffled=rs)

    sub("THE b26 -> COLUMN TRANSFER.  Input = signed `gp-0x6b26` (427 + b7), output = column\n"
        "    torque, both resampled to the 50 Hz 427 grid.  🛑 Read the caveat above before using\n"
        "    any number here for sizing.")
    S = _b26_stream(z)
    tq50 = np.interp(S["t"], t, tq)
    rate50 = np.interp(S["t"], t, rate)
    fs50 = S["fs"]
    for nm, m in (("ENGAGED", S["lat"] & S["paired"]),
                  ("MANUAL moving", (~S["lat"]) & S["paired"] & (S["v"] > 0.5))):
        W = _wins(m, S["t"], NW50, HOP50, (S["signed"], tq50), max_gap=0.10)
        print(f"\n      {nm}: {len(W)} windows")
        if len(W) < 6:
            print("        🛑 TOO FEW WINDOWS -- NOT SCOREABLE")
            OUT["d4"][f"H/{nm}"] = dict(n_windows=len(W), scoreable=False)
            continue
        r = _band_transfer(W, fs50, NW50, [b for b in Z_BANDS] + [("15-22", 15.0, 22.0)])
        idx = RNG.permutation(len(W))
        Wsh = [(W[i][0], W[(idx[i] + 1) % len(W)][1]) for i in range(len(W))]
        rs = _band_transfer(Wsh, fs50, NW50, [b for b in Z_BANDS] + [("15-22", 15.0, 22.0)])
        print(f"        {'band':8s} {'|tq/b26| ct/ct':>15s} {'phase':>9s} {'coh²':>7s} "
              f"{'coh² shuf':>10s}  {'group delay':>12s}")
        for b, lo, hi in [x for x in Z_BANDS] + [("15-22", 15.0, 22.0)]:
            a_, s_ = r[b], rs[b]
            fc = 0.5 * (lo + hi)
            gd = -np.radians(a_["phase_deg"]) / (2 * np.pi * fc) * 1e3   # ms, sign convention below
            print(f"        {b:8s} {a_['gain']:15.3f} {a_['phase_deg']:8.1f}° {a_['coh2']:7.3f} "
                  f"{s_['coh2']:10.3f}  {gd:9.1f} ms")
        OUT["d4"][f"H/{nm}"] = dict(n_windows=len(W), scoreable=True, bands=r, shuffled=rs)

    print("\n    🛑 GROUP DELAY IS A ONE-SIDED TEST.  A POSITIVE delay is consistent with b26 "
          "driving\n       the column but does NOT establish it (a loop produces it too).  A "
          "NEGATIVE delay is\n       a POSITIVE PROOF of feedthrough.  Read the sign, not the "
          "magnitude.")
    json.dump(OUT.get("d4", {}), open(OUTDIR / "v90_d4_transfer.json", "w"), indent=1, default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d4_transfer.json'}")


# =================================================================================================
def d6b():
    """The grind-#2 regime, RE-CUT.  The strict definition (v>=22.2 m/s AND rate>=5 °/s) leaves
    6/7/1/33 windows across the four arms -- unscoreable.  This reports the exposure ladder so the
    operator can see WHAT WOULD BE NEEDED, and scores the loosest cut that is actually populated."""
    hdr("D6b  GRIND #2 REGIME -- THE EXPOSURE LADDER.  The operator feels it on HIGHWAY-SPEED\n"
        "     CURVES AND LANE CHANGES.  That conjunction is nearly ABSENT from this corpus and\n"
        "     the honest output is the census, not a number squeezed out of 6 windows.")
    R = build_records()
    E = {b: eng(R[b], b) for b in ARMS}
    E["V90/r77"] = [r for r in _records77() if r["eng"] == 1]
    BUILDS["V90/r77"] = R77
    ALL = ARMS + ["V90/r77"]
    OUT["d6b"] = {}
    cuts = [("v>=22.2 & rate>=5", 22.2, 5.0), ("v>=22.2 & rate>=2", 22.2, 2.0),
            ("v>=13.9 & rate>=5", 13.9, 5.0), ("v>=13.9 & rate>=10", 13.9, 10.0),
            ("v>=13.9 & rate>=2", 13.9, 2.0), ("v>=11.1 & rate>=5", 11.11, 5.0)]
    print(f"      {'cut':22s} " + "".join(f"{b:>14s}" for b in ALL))
    for nm, vmin, rmin in cuts:
        row = {}
        cells = []
        for b in ALL:
            s = [r for r in E[b] if r["v"] >= vmin and r["rate"] >= rmin]
            row[b] = dict(n=len(s), blk=nblk(s))
            cells.append(f"{len(s):6d}/{nblk(s):<3d}  ")
        OUT["d6b"][nm] = row
        print(f"      {nm:22s} " + "".join(f"{c:>14s}" for c in cells))
    print("      (cells are  windows/blocks)")

    best = "v>=13.9 & rate>=5"
    vmin, rmin = 13.9, 5.0
    sub(f"the loosest populated cut, {best} -- absolute levels, all four arms")
    OUT["d6b_levels"] = {}
    for b in ALL:
        s = [r for r in E[b] if r["v"] >= vmin and r["rate"] >= rmin]
        if len(s) < 20:
            print(f"      {b:10s} n={len(s)} -- NOT SCOREABLE")
            continue
        row = {}
        for k in ("e_26-31", "e_40-49", CTRL, SUBJ1, SUBJ2):
            m_, lo, hi = G.boot_median_ci(s, k, RNG, nboot=1200)
            row[k] = [float(m_), float(lo), float(hi)]
        OUT["d6b_levels"][b] = dict(n=len(s), blk=nblk(s), levels=row)
        print(f"      {b:10s} n={len(s):4d} blk={nblk(s):3d}  " +
              "  ".join(f"{k.split('_')[1]} {row[k][0]:6.1f}[{row[k][1]:5.1f},{row[k][2]:6.1f}]"
                        for k in ("e_26-31", "e_40-49", CTRL, SUBJ1)))
    sub("matched comparison on that cut, V90/r77 against each V89 route (SAME FIRMWARE = placebo)\n"
        "    and against V88/r73 (the cross-build question)")
    OUT["d6b_ratios"] = {}
    A = [r for r in E["V90/r77"] if r["v"] >= vmin and r["rate"] >= rmin]
    for b in ARMS:
        B = [r for r in E[b] if r["v"] >= vmin and r["rate"] >= rmin]
        if len(A) < 20 or len(B) < 20:
            print(f"    V90/r77 vs {b}: n={len(A)}/{len(B)} -- NOT SCOREABLE")
            continue
        OUT["d6b_ratios"][b] = measured(A, B, f"V90/r77 / {b}")
    json.dump({k: v for k, v in OUT.items() if k.startswith("d6b")},
              open(OUTDIR / "v90_d6b_grind2.json", "w"), indent=1, default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d6b_grind2.json'}")


# =================================================================================================
#  D7 -- IS THE 6-9 Hz MODE VISIBLE IN THE MOTOR RATE AT ALL?
# =================================================================================================
#  THE CLAIM UNDER TEST (orchestrator, BELIEF): `gp-0x6b26`'s band content looks like the lane's own
#  differentiator shape applied to a FEATURELESS input => the motor rate has no 7.8 Hz peak => the
#  mode lives on the far side of the torsion bar / worm mesh and NO motor-rate-derived term can damp
#  it at any gain.  I am asked to make it EVIDENCE or destroy it.  Below, I try to destroy it.
#
#  THE LANE, byte-exact, COPIED from `docs/traces/TRACE-2026-08-10-damping-axis-hunt.md` §1 (NOT re-derived):
#      # gp-0x6c2c producer, FUN_00041464, fs = 1000 Hz (caller FUN_0002214a)
#      valid = -13000 <= gp_4f50 <= 13000
#      x     = gp_4f50 * 1024
#      s1   += (x - s1) * 37 >> 7          # EMA1, cal 0xC643C = 37,  alpha = 37/128
#      d     = s1[n] - s1[n-1]             # TRUE backward difference
#      d32   = clamp(d * 32, +-0xfa0000)
#      s2   += (d32 - s2) * 22 >> 6        # EMA2, cal 0xC40DC = 22,  alpha = 22/64
#      gp_6c2c = s2 >> 9
#      gp_6b26 = clamp(-k * gp_6c2c, +-511)     k = |Y|*273/2^24 = 0.160 @0 km/h .. 0.032 @90
#  Published gains, which this file re-simulates and ASSERTS against:
#      |H(7.79)| = 3.078   |H(21.09)| = 7.542   |H(28.10)| = 9.260   (counts of 6c2c per count of 4f50)
#
#  🛑 THE THREAT THE CLAIM MUST SURVIVE, AND IT IS NOT QUANTISATION.  `gp-0x6c2c` is produced at
#  1 kHz; 427 samples `gp-0x6b26` at 50 Hz with NO anti-alias filter.  |H| is a DIFFERENTIATOR that
#  RISES to ~60 Hz, so the signal's largest content sits exactly where folding is worst: 41-44 Hz and
#  56-59 Hz both fold onto 6-9 Hz.  If the 2-12 Hz densities are an ALIAS FLOOR, then the absence of
#  a 7.8 Hz peak in this channel is an absence of EVIDENCE, not evidence of absence.
#  Three model shapes are therefore compared against the measured one:
#      (a) NO ALIASING, flat input      -> density(f) proportional to |H(f)|
#      (b) FULL ALIASING, flat input    -> density(f) proportional to sqrt(sum_k |H(50k +- f)|^2)
#      (c) measured
K_SPEED_KMH = np.array([0.0, 20.0, 90.0])      # doc §2: k = |Y|*273/2^24
K_SPEED_VAL = np.array([0.1600, 0.0933, 0.0320])
RATE_CT_PER_DPS = 4.7121                        # doc §1: gp-0x4f50 scale
D7_BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
            ("12-16", 12.0, 16.0), ("15-22", 15.0, 22.0)]


def _sim_lane(f, amp=1000.0, fs=1000.0, ncyc=240):
    """The integer cascade, run exactly.  Python `>>` is an arithmetic floor shift == V850 `sar`."""
    n = int(ncyc * fs / f)
    t = np.arange(n) / fs
    xin = np.round(amp * np.sin(2 * np.pi * f * t)).astype(np.int64)
    s1 = s2 = prev = 0
    out = np.zeros(n)
    LIM = 0xFA0000
    for i in range(n):
        x = int(xin[i]) * 1024
        s1 += ((x - s1) * 37) >> 7
        d = s1 - prev
        prev = s1
        d32 = LIM if d * 32 > LIM else (-LIM if d * 32 < -LIM else d * 32)
        s2 += ((d32 - s2) * 22) >> 6
        out[i] = s2 >> 9
    m = slice(n // 2, n)                                    # steady state only
    ref = np.exp(-2j * np.pi * f * t[m])
    H = 2.0 * np.sum(out[m] * ref) / (n - n // 2) / amp
    return float(np.abs(H)), float(np.degrees(np.angle(H)))


_HCACHE = {}


def lane_H(f):
    f = float(f)
    if f not in _HCACHE:
        _HCACHE[f] = _sim_lane(f)[0]
    return _HCACHE[f]


def k_of_speed(v_ms):
    return np.interp(np.asarray(v_ms, float) * 3.6, K_SPEED_KMH, K_SPEED_VAL)


def d7():
    hdr("D7   IS THE 6-9 Hz MODE VISIBLE IN THE MOTOR RATE AT ALL?\n"
        "     Claim under test: `gp-0x6b26`'s band shape = the lane's differentiator applied to a\n"
        "     FEATURELESS input => the mode is invisible to the motor => no motor-rate-derived term\n"
        "     can damp it.  I am trying to DESTROY this, not confirm it.")
    OUT["d7"] = {}

    # ---------------------------------------------------------------- 7.1 the lane, verified
    sub("7.1  THE LANE TRANSFER, re-simulated from the byte-exact cascade and ASSERTED against\n"
        "     the published figures (a check that prints nothing is not a check that passed)")
    checks = {7.79: 3.078, 21.09: 7.542, 28.10: 9.260}
    ok = True
    for f, want in checks.items():
        got = lane_H(f)
        good = abs(got - want) / want < 0.01
        ok &= good
        print(f"      |H({f:6.2f} Hz)| = {got:7.4f}   published {want:6.3f}   "
              f"{'MATCH' if good else '🛑 MISMATCH'}")
    assert ok, "the re-simulated lane transfer does not reproduce the documented gains"
    OUT["d7"]["H_check"] = {str(f): [lane_H(f), w] for f, w in checks.items()}
    print("      ✅ assertion passed -- the cascade below is the flown one")

    # ---------------------------------------------------------------- 7.2 aliasing
    sub("7.2  🛑 THE ALIASING TEST -- the threat that decides whether a 6-9 Hz null means anything.\n"
        "     `gp-0x6c2c` runs at 1 kHz; 427 samples at 50 Hz with NO anti-alias filter, and |H|\n"
        "     RISES to ~60 Hz.  41-44 Hz and 56-59 Hz both fold onto 6-9 Hz.\n"
        "     (a) no aliasing, flat input -> density ∝ |H(f)|\n"
        "     (b) full aliasing, flat input -> density ∝ sqrt(Σ_k |H(50k ± f)|²)\n"
        "     Both normalised to the 15-22 Hz band and compared with the MEASURED shape.")
    fs427 = 50.0
    fgrid = np.arange(0.25, 500.0, 0.25)
    Hg = np.array([lane_H(f) for f in fgrid])

    def band_mean_sq(lo, hi, arr, grid):
        m = (grid >= lo) & (grid <= hi)
        return float(np.mean(arr[m] ** 2))

    def alias_density(lo, hi):
        m = (fgrid >= lo) & (fgrid <= hi)
        acc = np.zeros(m.sum())
        base = fgrid[m]
        for kk in range(0, 11):
            for ff in (kk * fs427 + base, kk * fs427 - base):
                good = ff > 0.24
                h = np.zeros_like(ff)
                h[good] = np.interp(ff[good], fgrid, Hg)
                acc += h ** 2
        return float(np.sqrt(np.mean(acc)))

    meas = {b: OUT.get("bands_50", {}).get(b, {}).get("density") for b, _, _ in D3_BANDS_50}
    if not any(meas.values()):                      # d3 not run in this process -- read the JSON
        j = json.load(open(OUTDIR / "v90_d3_b26_distribution.json"))
        meas = {b: j["bands_50"][b]["density"] for b, _, _ in D3_BANDS_50}
    rows = []
    for nm, lo, hi in D3_BANDS_50:
        rows.append((nm, np.sqrt(band_mean_sq(lo, hi, Hg, fgrid)), alias_density(lo, hi), meas[nm]))
    ref = [r for r in rows if r[0] == "15-22"][0]
    print(f"      {'band':8s} {'|H| rms':>9s} {'(a) no-alias':>13s} {'(b) aliased':>12s} "
          f"{'MEASURED':>10s}   (all normalised to 15-22)")
    OUT["d7"]["alias"] = {}
    for nm, h, a, m_ in rows:
        print(f"      {nm:8s} {h:9.3f} {h/ref[1]:13.3f} {a/ref[2]:12.3f} {m_/ref[3]:10.3f}")
        OUT["d7"]["alias"][nm] = dict(H_rms=h, noalias_norm=h / ref[1], alias_norm=a / ref[2],
                                      measured_norm=m_ / ref[3])
    r_meas = meas["15-22"] / meas["6-9"]
    r_noal = ref[1] / [r for r in rows if r[0] == "6-9"][0][1]
    r_alia = ref[2] / [r for r in rows if r[0] == "6-9"][0][2]
    OUT["d7"]["ratio_15_22_over_6_9"] = dict(measured=r_meas, no_alias=r_noal, full_alias=r_alia)
    print(f"\n      15-22 / 6-9 density ratio:  MEASURED {r_meas:.3f}   "
          f"(a) no-alias {r_noal:.3f}   (b) full-alias {r_alia:.3f}")
    print("      🛑 Read this ratio as the model discriminator, and read the LOW bands separately:")
    print("         a pure |H|-shaped signal REQUIRES 2-4 Hz to be far BELOW 6-9 Hz "
          f"(predicted {rows[0][1]/rows[1][1]:.3f}); measured is "
          f"{meas['2-4']/meas['6-9']:.3f}.")

    # ---------------------------------------------------------------- 7.3 quantisation floor
    sub("7.3  THE QUANTISATION-FLOOR CONTROL.  Take the reconstruction, LOW-PASS it below 4 Hz (so\n"
        "     it has NO true 6-9 Hz content), push it back through the EXACT packer law\n"
        "     wire = floor(|x|*5/8) and invert it, and measure the 6-9 Hz density that the\n"
        "     quantiser alone MANUFACTURES.  If that equals the measured density, D7 dies here.")
    from scipy.signal import butter, filtfilt
    z = _load77()
    S = _b26_stream(z)
    eng_m = S["lat"] & S["paired"]
    import _r31_common as C31
    runs = list(C31.runs_of(eng_m, S["t"], NW50, max_gap=0.10))
    slow = filtfilt(*butter(2, 4.0, btype="low", fs=S["fs"]), S["signed"])
    wire_q = np.floor(np.abs(slow) * 5.0 / 8.0)
    requant = np.sign(slow) * (8.0 * wire_q + 3.5) / 5.0
    qfloor = _bandpow(requant, S["fs"], D3_BANDS_50, NW50, HOP50, runs, S["seg"])
    print(f"      {'band':8s} {'requantised slow signal':>24s} {'MEASURED':>10s}  {'meas/floor':>11s}")
    OUT["d7"]["qfloor"] = {}
    for nm, lo, hi in D3_BANDS_50:
        r = qfloor.get(nm)
        if not r:
            continue
        d = r["v"] / np.sqrt(hi - lo)
        OUT["d7"]["qfloor"][nm] = dict(density=float(d), measured=meas[nm],
                                       ratio=float(meas[nm] / d) if d else np.nan)
        print(f"      {nm:8s} {d:24.4f} {meas[nm]:10.4f}  {meas[nm]/d:11.2f}x")
    print("      ⇒ a ratio >> 1 means the measured content is NOT quantisation of a slow signal.")

    # ---------------------------------------------------------------- 7.4 the decisive control
    sub("7.4  ★ THE CONTROL THAT DECIDES IT.  T(f) = B26(f)/W(f) measured directly by cross-\n"
        "     spectrum (W = steering-wheel rate, the COLUMN side).  If the motor rate tracked the\n"
        "     column at all frequencies, |T(f)| would be exactly k·|H(f)|.  So\n"
        "         R(f) = |T(f)| / |H(f)|   ∝   motor rate / wheel rate\n"
        "     and a mode the motor CANNOT SEE must show a DIP in R.  R is normalised to 2-4 Hz,\n"
        "     where the column and motor are rigidly coupled, so k and every scale factor cancel.\n"
        "     🛑 A DIP AT 7.79 Hz ALONE IS THE SIGNATURE.  A FLAT R REFUTES THE WHOLE IDEA.")
    t = np.asarray(z["t"], float)
    wrate = np.interp(S["t"], t, np.asarray(z["rate_f"], float))     # °/s on the 427 grid
    tqc = np.interp(S["t"], t, np.asarray(z["tq"], float))
    W = _wins(eng_m, S["t"], NW50, HOP50, (wrate, S["signed"], tqc), max_gap=0.10)
    print(f"      {len(W)} engaged windows")
    pairs = [(w[0], w[1]) for w in W]
    r = _band_transfer(pairs, S["fs"], NW50, D7_BANDS)
    idx = RNG.permutation(len(pairs))
    rs = _band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                         for i in range(len(pairs))], S["fs"], NW50, D7_BANDS)
    base = None
    print(f"      {'band':8s} {'|T| ct/(°/s)':>13s} {'|H|':>8s} {'R = |T|/|H|':>12s} "
          f"{'R norm':>8s} {'coh²':>7s} {'coh² shuf':>10s}")
    OUT["d7"]["R"] = {}
    for nm, lo, hi in D7_BANDS:
        h = np.sqrt(band_mean_sq(lo, hi, Hg, fgrid))
        Rv = r[nm]["gain"] / h
        if nm == "2-4":
            base = Rv
        OUT["d7"]["R"][nm] = dict(T=r[nm]["gain"], H=h, R=float(Rv), R_norm=float(Rv / base),
                                  coh2=r[nm]["coh2"], coh2_shuf=rs[nm]["coh2"])
        print(f"      {nm:8s} {r[nm]['gain']:13.4f} {h:8.3f} {Rv:12.5f} {Rv/base:8.3f} "
              f"{r[nm]['coh2']:7.3f} {rs[nm]['coh2']:10.3f}")

    # ---------------------------------------------------------------- 7.5 free argmax + prominence
    sub("7.5  FREE-ARGMAX over 4-15 Hz and PROMINENCE, on the RECOVERED motor rate and on the\n"
        "     COLUMN TORQUE, same windows, same estimator, symmetric wheel-order veto on both.\n"
        "     ⚠ Deconvolution divides by |H|, which is SMALL at low f -- trustworthy above ~2 Hz,\n"
        "       and increasingly noisy below it.  The 4-15 Hz search window sits in the good region.")
    nw = NW50
    fax = np.fft.rfftfreq(nw, 1.0 / S["fs"])
    Hax = np.array([lane_H(max(f, 0.25)) for f in fax])
    Hax[0] = Hax[1]
    taper = np.hanning(nw)
    res = {"motor": [], "column": []}
    vw = []
    vsel = _wins(eng_m, S["t"], NW50, HOP50, (S["v"],), max_gap=0.10)
    assert len(vsel) == len(W), "window sets diverged -- speed and signal windows must align"
    for (wr, b26, tqw), (vv,) in zip(W, vsel):
        for tag, x, div in (("motor", b26, Hax), ("column", tqw, None)):
            P = np.abs(np.fft.rfft((x - x.mean()) * taper)) ** 2
            if div is not None:
                P = P / (div ** 2)
            R = G.prom_spectrum(fax, P, halfwin=3.0, exclude=0.6)
            m = (fax >= 4.0) & (fax <= 15.0) & np.isfinite(R)
            if not m.any():
                res[tag].append((np.nan, np.nan))
                continue
            j = int(np.argmax(np.where(m, R, -np.inf)))
            res[tag].append((float(fax[j]), float(R[j])))
        vw.append(float(np.mean(np.abs(vv))))
    OUT["d7"]["argmax"] = {}
    for tag in ("motor", "column"):
        f0 = np.array([a for a, _ in res[tag]])
        pr = np.array([b for _, b in res[tag]])
        keep = np.array([not order_hit(f, v) for f, v in zip(f0, vw)]) & np.isfinite(f0)
        for lbl, sel in (("all windows", np.isfinite(f0)), ("order-vetoed", keep)):
            if sel.sum() < 10:
                print(f"      {tag:7s} {lbl:14s} n={int(sel.sum())} -- too few")
                continue
            d = dict(n=int(sel.sum()), f0_med=float(np.median(f0[sel])),
                     prom_med=float(np.median(pr[sel])),
                     frac_in_6_9=float(np.mean((f0[sel] >= 6) & (f0[sel] <= 9))))
            OUT["d7"]["argmax"][f"{tag}/{lbl}"] = d
            print(f"      {tag:7s} {lbl:14s} n={d['n']:4d}  median f0 {d['f0_med']:5.2f} Hz  "
                  f"median prominence {d['prom_med']:6.2f}  "
                  f"fraction of windows arg-maxing INSIDE 6-9 Hz {d['frac_in_6_9']:.3f}")

    # ---------------------------------------------------------------- 7.6 power
    sub("7.6  POWER -- would a fully-transmitted column ring have been VISIBLE in this channel?\n"
        "     A null is only informative if the answer is yes.  Using the doc's own scale chain:\n"
        "       column amp A° at f  ->  rate amp 2πfA °/s  ->  ×4.7121 ct  ->  ×|H(f)|  ->  ×k(v)")
    vmed = float(np.median(S["v"][eng_m]))
    kmed = float(k_of_speed(vmed))
    print(f"      route 77 engaged median speed {vmed:.2f} m/s ({vmed*3.6:.1f} km/h) => "
          f"k = {kmed:.4f}")
    meas69_rms = OUT["d7"].get("qfloor", {}) and meas["6-9"] * np.sqrt(3.0)
    print(f"      MEASURED 6-9 Hz band rms of |gp-0x6b26| : {meas69_rms:.2f} counts")
    OUT["d7"]["power"] = dict(v_med=vmed, k=kmed, measured_69_rms=float(meas69_rms), rows={})
    print(f"      {'column ring amp':>16s} {'rate amp °/s':>13s} {'predicted |b26| rms':>21s} "
          f"{'vs measured':>12s}")
    for A in (0.10, 0.25, 0.645, 0.96):
        rate_amp = 2 * np.pi * 7.79 * A
        b26_amp = rate_amp * RATE_CT_PER_DPS * lane_H(7.79) * kmed
        b26_rms = b26_amp / np.sqrt(2)
        OUT["d7"]["power"]["rows"][str(A)] = dict(rate_amp=rate_amp, b26_rms=float(b26_rms),
                                                  ratio=float(b26_rms / meas69_rms))
        print(f"      {A:14.3f}°  {rate_amp:13.1f} {b26_rms:21.1f} "
              f"{b26_rms/meas69_rms:11.1f}x")
    print("      ⇒ if the predicted value FAR exceeds the measured one, the channel had the "
          "dynamic\n         range to see the ring and did not -- a null that MEANS something.")

    json.dump(OUT.get("d7", {}), open(OUTDIR / "v90_d7_motor_visibility.json", "w"), indent=1,
              default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d7_motor_visibility.json'}")


# =================================================================================================
#  D6c -- GRIND #2 AGAINST THE **LOAD** COVARIATE
# =================================================================================================
#  The operator feels grind #2 on HIGHWAY-SPEED CURVES AND LANE CHANGES -- both SUSTAINED-LOAD
#  regimes.  The standing mechanism says the symptom scales with MEAN |command| = mesh load (the
#  corpus measured +1.074 [+0.812, +1.445] on `e_6-9`, with the FLUCTUATION component contributing
#  exactly nothing).  If the load axis carries grind #2 the way it carries the ratchet, that is an
#  independent replication of the mechanism on a band nobody has tested it on.
#  🛑 The 32-38 Hz NEGATIVE CONTROL is carried on every regression, and every coefficient is
#  reported as a BAND CONTRAST against it -- a load effect that is uniform across the spectrum is
#  not a symptom mechanism, it is a louder drive.
D6C_BANDS = [("6-9", 6.0, 9.0), ("18-22", 18.0, 22.0), ("26-31", 26.0, 31.0),
             ("32-38", 32.0, 38.0), ("40-49", 40.0, 49.0)]
D6C_CTRL = "32-38"


def d6c():
    import _r31_common as C31
    from v89_e4_inertia import NFFT, HOP, fs_of, ols
    hdr("D6c  GRIND #2 vs THE LOAD COVARIATE.  Regression of log band energy on log mean |LKAS\n"
        "     command| (0x0E4, the mesh-load proxy), log |wheel rate|, log speed and log |lateral\n"
        "     accel|, with route fixed effects and a block bootstrap over ~10.2 s units.\n"
        "     EVERY coefficient is reported as a CONTRAST against the 32-38 Hz negative control.")
    BUILDS["V90/r77"] = R77
    arms = ARMS + ["V90/r77"]
    W = []
    taper = np.hanning(NFFT) + 1e-3
    cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
    for name in arms:
        cfg = BUILDS[name]
        for s in cfg["segs"]:
            if s in cfg.get("parked", []) or not (cfg["cache"] / f"{cfg['pfx']}{s}.npz").exists():
                continue
            d = C31.load(s, cfg["cache"], cfg["pfx"])
            fs = fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            e4 = np.asarray(d["e4tq"], float)
            tq = np.asarray(d["tq"], float)
            la = np.asarray(d["imu_lat"], float) if "imu_lat" in d else np.full(len(tq), np.nan)
            for a, b in list(C31.runs_of(lat, d["t"], NFFT)):
                nwin = 0
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    r = dict(build=name, blk=(name, s, a, nwin // 8),
                             cmd=float(np.mean(np.abs(e4[sl]))),
                             rate=float(np.mean(np.abs(d["rate_f"][sl]))),
                             v=float(np.mean(np.abs(d["cs_v"][sl]))),
                             latacc=float(np.mean(np.abs(la[sl]))))
                    for nm, lo, hi in D6C_BANDS:
                        r["e_" + nm] = G.win_env(tq[sl], fs, lo, hi, taper, cw)
                    W.append(r)
                    nwin += 1
    need = ["cmd", "rate", "v"] + ["e_" + nm for nm, _, _ in D6C_BANDS]
    W = [r for r in W if all(np.isfinite(r[k]) and r[k] > 0 for k in need)]
    print(f"    {len(W)} engaged windows over {len(arms)} routes, "
          f"{len({r['blk'] for r in W})} blocks")
    cmdv = np.array([r["cmd"] for r in W])
    print(f"    |0x0E4| p5 {np.percentile(cmdv,5):.0f} .. p95 {np.percentile(cmdv,95):.0f} ct "
          f"({np.percentile(cmdv,95)/max(np.percentile(cmdv,5),1):.1f}x range)   "
          f"latacc finite on {100*np.mean(np.isfinite([r['latacc'] for r in W])):.1f} %")
    OUT["d6c"] = {}

    def fit(sub_, tag, cols, names, nboot=2500):
        if len(sub_) < 120:
            print(f"\n    {tag}: n={len(sub_)} -- NOT SCOREABLE")
            return
        dum = [np.array([1.0 if r["build"] == n else 0.0 for r in sub_]) for n in arms]
        X = np.column_stack(dum + cols(sub_))
        k0 = len(dum)
        Y = {nm: np.log([r["e_" + nm] for r in sub_]) for nm, _, _ in D6C_BANDS}
        blks = np.array([str(r["blk"]) for r in sub_])
        ub = np.unique(blks)
        idxof = {b: np.where(blks == b)[0] for b in ub}
        pt = {nm: ols(Y[nm], X)[k0:] for nm in Y}
        D = {nm: np.empty((nboot, len(names))) for nm in Y}
        for i in range(nboot):
            pick = np.concatenate([idxof[ub[j]] for j in RNG.integers(0, len(ub), len(ub))])
            Xp = X[pick]
            for nm in Y:
                D[nm][i] = ols(Y[nm][pick], Xp)[k0:]
        print(f"\n    {tag}   n={len(sub_)} windows, {len(ub)} blocks")
        for j, term in enumerate(names):
            print(f"      term: {term}")
            print(f"        {'band':8s} {'coef':>8s} {'[  2.5 %, 97.5 %]':>20s} "
                  f"{'CONTRAST vs 32-38':>26s}  excl 0?")
            for nm, _, _ in D6C_BANDS:
                lo, hi = np.percentile(D[nm][:, j], [2.5, 97.5])
                dc = D[nm][:, j] - D[D6C_CTRL][:, j]
                clo, chi = np.percentile(dc, [2.5, 97.5])
                star = "  <-- GRIND #2" if nm in ("26-31", "40-49") else (
                    "  (control)" if nm == D6C_CTRL else "")
                print(f"        {nm:8s} {pt[nm][j]:+8.3f} [{lo:+6.3f},{hi:+6.3f}] "
                      f"{pt[nm][j]-pt[D6C_CTRL][j]:+9.3f} [{clo:+6.3f},{chi:+6.3f}]  "
                      f"{'YES' if (clo > 0 or chi < 0) else 'no'}{star}")
                OUT["d6c"][f"{tag}/{term}/{nm}"] = dict(
                    coef=float(pt[nm][j]), ci=[float(lo), float(hi)],
                    contrast=float(pt[nm][j] - pt[D6C_CTRL][j]),
                    contrast_ci=[float(clo), float(chi)], n=len(sub_), blocks=len(ub))

    base_cols = lambda s_: [np.log([r["cmd"] for r in s_]), np.log([r["rate"] for r in s_]),
                            np.log([np.maximum(r["v"], 0.05) for r in s_])]
    base_names = ["log|cmd| (LOAD)", "log|rate|", "log v"]
    sub("ALL ENGAGED WINDOWS, all four routes")
    fit(W, "all engaged", base_cols, base_names)

    sub("★ THE GRIND #2 REGIME -- v >= 13.9 m/s (50 km/h), the loosest highway cut with exposure")
    fit([r for r in W if r["v"] >= 13.9], "highway v>=13.9 m/s", base_cols, base_names)

    sub("with LATERAL ACCELERATION added -- a curve is a sustained lateral load, and it is the\n"
        "    covariate closest to what the operator describes")
    Wl = [r for r in W if np.isfinite(r["latacc"]) and r["latacc"] > 0]
    fit(Wl, "all engaged + latacc",
        lambda s_: base_cols(s_) + [np.log([r["latacc"] for r in s_])],
        base_names + ["log|lat accel|"])
    fit([r for r in Wl if r["v"] >= 13.9], "highway + latacc",
        lambda s_: base_cols(s_) + [np.log([r["latacc"] for r in s_])],
        base_names + ["log|lat accel|"])

    json.dump(OUT.get("d6c", {}), open(OUTDIR / "v90_d6c_grind2_load.json", "w"), indent=1,
              default=float)
    print(f"\n  wrote {OUTDIR / 'v90_d6c_grind2_load.json'}")


# =================================================================================================
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "d1":
        d1()
    elif args[0] == "d7":
        d7()
    elif args[0] == "d6c":
        d6c()
    elif args[0] == "d3":
        d3()
    elif args[0] == "d4":
        d4()
    elif args[0] == "d5":
        d5()
    elif args[0] == "d6":
        d6()
    elif args[0] == "d6b":
        d6b()
    else:
        raise SystemExit(__doc__)
