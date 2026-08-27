#!/usr/bin/env python3
"""V68 routes `4c` (LKAS OFF) and `4e` (LKAS ON): the corpus's FIRST highway LKAS-off arm.

WHY THIS ROUTE PAIR IS DIFFERENT FROM EVERY PRIOR HIGHWAY COMPARISON
--------------------------------------------------------------------
docs/HANDOFF-2026-08-03 §4: the corpus held **1,177.4 s of engaged driving above 25 m/s and 0.0 s
disengaged**, at EVERY cut from 12 to 28 m/s, verified two ways. The operator's "it only happens
with LKAS engaged" had never been testable. Route `4c` supplies **234.8 s disengaged above 20 m/s**
and route `4e` supplies **160.6 s engaged above 20 m/s**, on the SAME firmware, the SAME day.

Operator report: `4c` -- "no grind vibration felt".  `4e` -- "definitely felt the grind #2-like
vibration when changing lanes, otherwise this highway was relatively straight".

🛑🛑 THE CONFOUND, STATED BEFORE ANY NUMBER. V68's control path is byte-identical to V67's, and
V67's rate-lane arm is CONDITIONAL on the firmware's own LKAS gate `gp-0x6806`: Kd = 2.00x while
the gate is open, stock Kd = 1 while it is closed. So on these two routes

    LKAS ON   ==  gate open   ==  Kd = 2.00x        (route 4e, 100.0% of frames)
    LKAS OFF  ==  gate closed ==  Kd = 1 (stock)    (route 4c, 96.9% of frames)

**ARM AND DOSE ARE THE SAME VARIABLE HERE.** A 4e-vs-4c difference is "engaged AND doubled" versus
"disengaged AND stock" and this design CANNOT separate them. That matters because the record cuts
both ways: V62's flat x2 RAISED 40-49 Hz by 11.7x at creep corners (it is grind #2's own cause),
while the three-dose HIGHWAY comparison found no 40-49 Hz dose response at all (0.970 [0.787,
1.154] and 0.938 [0.764, 1.184] against a split-half null of [0.73, 1.37]). The partial decoupling
available is to compare each arm against the PRIOR pool at its own dose, which this script does.

METHOD, all of it already paid for in blood by earlier sessions
---------------------------------------------------------------
ORDER VETO FIRST   Average the periodograms, THEN peak-find. A median-of-per-window-argmax
                   estimator manufactures a line at band centre and beat the alternative at
                   dBIC 249-460 before it was withdrawn (HANDOFF-2026-08-03 §5b).
EPISODES           Bootstrap over episodes/blocks, never windows (feedback-episodes-not-windows).
SPLIT-HALF NULL    Every ratio is quoted against a within-build null from the identical estimator.
ENVELOPE           p99 of the tapered, detrended analytic band envelope (`_grind2_lib.win_env`).
                   🛑 NEVER cross-compare against the untapered whole-record form -- they differ
                   by 2.3x (HANDOFF-2026-08-03 §9).
ENGAGEMENT         carControl.latActive, corroborated here by the firmware's own gate bit g6806.
fs                 🛑 `1/median(dt)` IS WRONG -- frames are timestamped per log packet, so median
                   dt reads 100.76 Hz on a grid that is 100.000 Hz to 2e-5. Use the MEAN rate.
                   This script overrides `_grind2_lib`'s `fs_of` for the new routes and reports
                   both so the size of the correction is visible.

Usage:  python studies/sessions/v68/analyze_v68_highway_arms.py [--json OUT]
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
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import periodogram, runs_of, sustained  # noqa: E402

CACHE = ROOT / "_scratch/cache/v68"
SEGS = {"4c": [4, 5, 6, 7, 8], "4e": [31, 32, 33, 34]}
NFFT, HOP = G.NFFT, G.HOP
HWY = 20.0          # m/s. 4c holds 234.8 s disengaged above this; 4e holds 160.6 s engaged.


# ------------------------------------------------------------------ loading ----------------------
def mean_fs(t):
    """The MEAN rate over the segment, not 1/median(dt). See the module docstring."""
    return (len(t) - 1) / (t[-1] - t[0])


def segs_of(route):
    for s in SEGS[route]:
        p = CACHE / f"{route}s{s}.npz"
        if p.exists():
            yield s, {k: v for k, v in np.load(p).items()}


def wrecs_v68(route, chan="tq", keep_P=False):
    """`_grind2_lib.wrecs` for the V68 caches, with the corrected fs and the blinker channel."""
    out = []
    for s, d in segs_of(route):
        fs = mean_fs(d["t"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        le = d["cc_lat"] > 0.5
        for eng, mask in ((1, le), (0, ~le)):
            for a, b in runs_of(mask, d["t"], NFFT):
                x = np.asarray(d[chan][a:b], float)
                xa = np.asarray(d["ang"][a:b], float)
                nwin = 0
                for i in range(0, len(x) - NFFT + 1, HOP):
                    P = periodogram(x[i:i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    sl = slice(a + i, a + i + NFFT)
                    xw = x[i:i + NFFT]
                    R = G.prom_spectrum(f, P)
                    r = dict(build=route, seg=int(s), eng=eng, fs=fs,
                             ep=(route, int(s), int(a), int(b)), t0=float(d["t"][a + i]))
                    for k, bd in G.BANDS.items():
                        r["e_" + k] = G.win_env(xw, fs, *bd, taper, cw)
                        r["f_" + k], r["p_" + k] = G.locate(f, P, *bd, R=R)
                    r["zig"], r["zigamp"] = G.zigzag(xw, 300.0)
                    r["ang_hf"] = G.win_env(xa[i:i + NFFT], fs, 30.0, 49.0, taper, cw)
                    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
                    r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
                    r["eff"] = float(np.mean(np.abs(sustained(d["tq"][sl], fs))))
                    r["rate"] = float(np.mean(np.abs(d["rate_c"][sl])))
                    r["ratep95"] = float(np.percentile(np.abs(d["rate_c"][sl]), 95))
                    r["ratepk"] = float(np.max(np.abs(d["rate_c"][sl])))
                    r["gate"] = float(np.mean(d["g6806"][sl]))
                    r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
                    r["blink"] = float(np.mean(d["cs_lchg"][sl]))
                    r["fsm"] = float(np.mean(d["fsm67df"][sl]))
                    r["det"] = float(np.mean(d["det671a"][sl]))
                    r["cell"] = (G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                                 G.binof(r["rate"], G.R_BINS))
                    r["blk"] = r["ep"] + (nwin // 8,)
                    nwin += 1
                    if keep_P:
                        r["f"], r["P"] = f, P
                    out.append(r)
    return out


# ------------------------------------------------------------------ stats -----------------------
def boot_ratio(rsA, rsB, key, rng, nboot=4000, agg=np.median):
    """Ratio agg(A)/agg(B), resampling EPISODES (G.EPKEY) with replacement in each arm."""
    epA, epB = G.episodes(rsA), G.episodes(rsB)
    if not epA or not epB:
        return np.nan, (np.nan, np.nan)
    point = agg(G.col(rsA, key)) / agg(G.col(rsB, key))
    out = []
    for _ in range(nboot):
        a = np.concatenate([G.col(epA[i], key) for i in rng.integers(0, len(epA), len(epA))])
        b = np.concatenate([G.col(epB[i], key) for i in rng.integers(0, len(epB), len(epB))])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    if not out:
        return point, (np.nan, np.nan)
    return float(point), (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def split_null(rs, key, rng, nrep=800, agg=np.median):
    """Split the SAME arm's episodes at random into halves and ratio them. The floor below which
    no ratio is a finding."""
    ep = G.episodes(rs)
    if len(ep) < 4:
        return (np.nan, np.nan)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(ep))
        h = len(ep) // 2
        a = np.concatenate([G.col(ep[i], key) for i in idx[:h]])
        b = np.concatenate([G.col(ep[i], key) for i in idx[h:]])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out else (np.nan,) * 2


def cell_matched(rsA, rsB, key, rng, nboot=4000):
    """Cell-stratified ratio: match on (speed, effort, |rate|) bins, weight cells by min(nA,nB)."""
    cells = sorted(set(r["cell"] for r in rsA) & set(r["cell"] for r in rsB))
    A = {c: [r for r in rsA if r["cell"] == c] for c in cells}
    B = {c: [r for r in rsB if r["cell"] == c] for c in cells}
    use = [c for c in cells if len(A[c]) >= 4 and len(B[c]) >= 4]
    if not use:
        return np.nan, (np.nan, np.nan), []
    w = np.array([min(len(A[c]), len(B[c])) for c in use], float)
    w /= w.sum()

    def stat(pick):
        ra = np.array([np.median(G.col(pick[0][c], key)) for c in use])
        rb = np.array([np.median(G.col(pick[1][c], key)) for c in use])
        return float(np.sum(w * ra) / np.sum(w * rb))

    point = stat((A, B))
    epA, epB = G.episodes(rsA), G.episodes(rsB)
    out = []
    for _ in range(nboot):
        sa = [r for i in rng.integers(0, len(epA), len(epA)) for r in epA[i]]
        sb = [r for i in rng.integers(0, len(epB), len(epB)) for r in epB[i]]
        Aa = {c: [r for r in sa if r["cell"] == c] for c in use}
        Bb = {c: [r for r in sb if r["cell"] == c] for c in use}
        if all(Aa[c] and Bb[c] for c in use):
            out.append(stat((Aa, Bb)))
    ci = ((float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out
          else (np.nan, np.nan))
    return point, ci, [(c, len(A[c]), len(B[c])) for c in use]


# ------------------------------------------------------------------ order veto -------------------
def order_veto(route, vlo, vhi, engmask=None):
    """AVERAGE the periodograms across all qualifying windows, THEN peak-find. §5b of the handoff:
    the reverse order manufactures a line at band centre with dBIC 249-460."""
    acc, n, fref, vs = None, 0, None, []
    for s, d in segs_of(route):
        fs = mean_fs(d["t"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        le = d["cc_lat"] > 0.5
        masks = [np.ones(len(le), bool)] if engmask is None else [le if engmask else ~le]
        for m in masks:
            for a, b in runs_of(m, d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    v = float(np.mean(d["cs_v"][sl]))
                    if not (vlo <= v < vhi):
                        continue
                    P = periodogram(d["tq"][a + i:a + i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    if acc is None:
                        acc, fref = np.zeros_like(P), f
                    if len(P) == len(acc):
                        acc += P; n += 1; vs.append(v)
    if not n:
        return None
    Pm = acc / n
    R = G.prom_spectrum(fref, Pm)
    hi = G.locate(fref, Pm, 30.0, 49.5, R=R)
    lo = G.locate(fref, Pm, 8.0, 30.0, R=R)
    return dict(n=n, vmean=float(np.mean(vs)), f_hi=hi[0], prom_hi=hi[1],
                f_lo=lo[0], prom_lo=lo[1])


# ------------------------------------------------------------------ main ------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_scratch/out/_v68_arms.json"))
    a = ap.parse_args()
    rng = np.random.default_rng(20260803)
    G.EPKEY = "blk"          # ~10.2 s blocks: `ep` gives only 5-9 units here, a degenerate null
    res = {}

    G.hdr("0. EXPOSURE AND THE fs CORRECTION")
    for route in ("4c", "4e"):
        for s, d in segs_of(route):
            fm, fmed = mean_fs(d["t"]), 1.0 / np.median(np.diff(d["t"]))
            print(f"  {route}s{s}: mean fs {fm:.4f} Hz   1/median(dt) {fmed:.4f} Hz   "
                  f"bias {100 * (fmed / fm - 1):+.2f}%")

    print()
    W = {r: wrecs_v68(r) for r in ("4c", "4e")}
    for r in ("4c", "4e"):
        print(f"  {r}: {len(W[r])} windows  "
              f"({sum(1 for w in W[r] if w['eng'])} engaged / "
              f"{sum(1 for w in W[r] if not w['eng'])} disengaged)")

    # the two analysis arms: 4c DISENGAGED highway, 4e ENGAGED highway
    OFF = [w for w in W["4c"] if not w["eng"] and w["v"] >= HWY]
    ON = [w for w in W["4e"] if w["eng"] and w["v"] >= HWY]
    print(f"\n  ARM OFF (4c, disengaged, v>={HWY:.0f}): {len(OFF)} windows, "
          f"{len(G.episodes(OFF))} blocks")
    print(f"  ARM ON  (4e, engaged,    v>={HWY:.0f}): {len(ON)} windows, "
          f"{len(G.episodes(ON))} blocks")
    for nm, arm in (("OFF", OFF), ("ON", ON)):
        if arm:
            print(f"    {nm}: gate {100 * np.mean(G.col(arm, 'gate')):.1f}%  "
                  f"v {np.mean(G.col(arm, 'v')):.1f} m/s  "
                  f"eff {np.median(G.col(arm, 'eff')):.0f}  "
                  f"|rate| {np.median(G.col(arm, 'rate')):.1f} deg/s  "
                  f"bit5 {100 * np.mean(G.col(arm, 'fsm')):.4f}%")

    G.hdr("1. THE ORDER VETO -- average the periodograms, THEN peak-find")
    print("  criterion: a real line needs prominence > 4. 8-30 Hz is the positive control")
    print("  (wheel order 1 = 0.4808*v Hz).\n")
    res["veto"] = {}
    for route, eng in (("4c", False), ("4e", True)):
        for vlo, vhi in ((20, 24), (24, 27), (27, 32)):
            o = order_veto(route, vlo, vhi, eng)
            if not o:
                continue
            pred = 0.4808 * o["vmean"]
            key = f"{route}_{vlo}-{vhi}"
            res["veto"][key] = o
            print(f"  {route} {'ON ' if eng else 'OFF'} v={vlo}-{vhi} (n={o['n']:4d}, "
                  f"mean {o['vmean']:.1f} m/s): "
                  f"30-49.5 Hz peak {o['f_hi']:5.2f} prom {o['prom_hi']:5.2f}"
                  f"{'  *** LINE' if o['prom_hi'] > 4 else ''}   |   "
                  f"8-30 Hz peak {o['f_lo']:5.2f} prom {o['prom_lo']:5.2f} "
                  f"(order-1 predicts {pred:.2f})")

    G.hdr("2. THE ARM CONTRAST -- ON (4e) / OFF (4c), by band")
    print("  🛑 arm and Kd dose are the SAME variable here; see the module docstring.")
    print("  ratio > 1 means the ENGAGED arm is louder.\n")
    res["arms"] = {}
    print(f"  {'band':8} {'ON med':>9} {'OFF med':>9} {'ratio [95% CI]':>26} "
          f"{'null(ON)':>16} {'null(OFF)':>16}")
    for band in ("1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49"):
        k = "e_" + band
        pt, ci = boot_ratio(ON, OFF, k, rng)
        nA, nB = split_null(ON, k, rng), split_null(OFF, k, rng)
        res["arms"][band] = dict(ratio=pt, ci=ci, null_on=nA, null_off=nB,
                                 med_on=float(np.median(G.col(ON, k))),
                                 med_off=float(np.median(G.col(OFF, k))))
        mark = ""
        if np.isfinite(ci[0]) and np.isfinite(nB[0]):
            if ci[0] > max(nA[1], nB[1]):
                mark = "  *** ON LOUDER, outside both nulls"
            elif ci[1] < min(nA[0], nB[0]):
                mark = "  *** ON QUIETER, outside both nulls"
        print(f"  {band:8} {np.median(G.col(ON, k)):9.1f} {np.median(G.col(OFF, k)):9.1f} "
              f"{pt:9.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}] "
              f"[{nA[0]:5.2f},{nA[1]:5.2f}] [{nB[0]:5.2f},{nB[1]:5.2f}]{mark}")

    G.hdr("3. THE SAME CONTRAST, CELL-MATCHED on (speed, effort, |rate|)")
    print("  The arms differ in exposure: an engaged highway run and a manual one are not the")
    print("  same driving. Matching on the covariate cell is the standing correction.\n")
    res["matched"] = {}
    for band in ("1-4", "18-22", "24-28", "30-40", "40-49"):
        pt, ci, cells = cell_matched(ON, OFF, "e_" + band, rng)
        res["matched"][band] = dict(ratio=pt, ci=ci, ncells=len(cells))
        print(f"  {band:8} {pt:8.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}]   ({len(cells)} cells "
              f"used: {[(c, na, nb) for c, na, nb in cells]})")

    G.hdr("4. THE MANEUVER CONTRAST, COMPUTED SEPARATELY INSIDE EACH ARM")
    print("  The operator felt it WHEN CHANGING LANES. A maneuver window is the top steering-rate")
    print("  decile; controls are the bottom half of the same arm, same speed cell. Because each")
    print("  arm is its OWN control, road/time/tyre differences between the routes cancel.\n")
    res["maneuver"] = {}
    for nm, arm in (("ON  (4e)", ON), ("OFF (4c)", OFF)):
        if len(arm) < 20:
            print(f"  {nm}: too few windows ({len(arm)})")
            continue
        rp = G.col(arm, "ratepk")
        hi_t, lo_t = np.percentile(rp, 90), np.percentile(rp, 50)
        mv = [w for w in arm if w["ratepk"] >= hi_t]
        ct = [w for w in arm if w["ratepk"] <= lo_t]
        print(f"  {nm}: {len(mv)} maneuver windows (|rate|pk >= {hi_t:.1f} deg/s) vs "
              f"{len(ct)} controls (<= {lo_t:.1f})")
        res["maneuver"][nm.split()[0]] = {}
        for band in ("1-4", "18-22", "24-28", "30-40", "40-49"):
            k = "e_" + band
            pt, ci = boot_ratio(mv, ct, k, rng)
            res["maneuver"][nm.split()[0]][band] = dict(ratio=pt, ci=ci)
            print(f"      {band:8} {pt:7.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}]")
        print()

    G.hdr("5. BLINKER-ANCHORED LANE CHANGES (4e) -- the operator's own trigger")
    lc = [w for w in ON if w["blink"] > 0.25]
    nolc = [w for w in ON if w["blink"] == 0.0]
    print(f"  {len(lc)} windows with the blinker on >25% of the window, {len(nolc)} with it off")
    res["blinker"] = {}
    if len(lc) >= 8 and len(nolc) >= 8:
        for band in ("1-4", "18-22", "24-28", "30-40", "40-49"):
            k = "e_" + band
            pt, ci = boot_ratio(lc, nolc, k, rng)
            res["blinker"][band] = dict(ratio=pt, ci=ci, n_lc=len(lc))
            print(f"      {band:8} {pt:7.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}]")
    else:
        print("      too few blinker windows for an episode bootstrap")

    G.hdr("6. THE DETECTOR -- bits 5 and 4, the kit's only above-50-Hz instrument")
    res["detector"] = {}
    for route in ("4c", "4e"):
        nf = nfsm = ndet = nov = 0
        for s, d in segs_of(route):
            nf += len(d["t"]); nfsm += int(d["fsm67df"].sum())
            ndet += int(d["det671a"].sum()); nov += int(d["ord_viol"].sum())
        res["detector"][route] = dict(frames=nf, fsm=nfsm, det=ndet, ord_viol=nov)
        print(f"  {route}: {nf:7d} frames   bit5 (gp-0x67df != 0, |gp-0x6c2c| crossed +-12800) "
              f"= {nfsm}   bit4 (gp-0x671a >= 1, reversed) = {ndet}   ord_viol = {nov}")
    tot = sum(v["frames"] for v in res["detector"].values())
    print(f"\n  POOLED: {tot} frames, {tot / 100.0:.0f} s. bit5 fired "
          f"{sum(v['fsm'] for v in res['detector'].values())} times.")

    Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
