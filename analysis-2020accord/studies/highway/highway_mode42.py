#!/usr/bin/env python3
"""THE ~42 Hz HIGHWAY MODE: does it pre-exist V67, and does its amplitude respond to the rate lane?

Established in this session, with a razor-sharp positive control (the 8-30 Hz line reads wheel
order 1.00-1.02 in every speed bin, free-order fit 1.07):

  * a line at 42-43 Hz on comma-IMU ay / gz / az / gx sits STILL while road speed runs 22->35 m/s
    (wheel order 3 would climb 33.3->47.9 Hz)  => ORDER 3 REFUTED, dBIC 249-460
  * it also sits still while engine rpm runs 1300->2400 (an aliased engine order 2 would sweep
    53.8->31.7 Hz)  => ENGINE ORDER REFUTED, slope vs rpm -0.0007 [-0.0025,+0.0008] Hz/rpm
    against the alias's required -0.0333

So it is a MODE, fixed in hertz -- which is what the operator reports feeling. This file asks the
only two questions that decide whether it is a FIRMWARE target:

  1. PRESENCE. Is the 42 Hz line on the stock-rate-lane builds too (V58/r2b Kd=1, V62/r37 and
     V65/r3b Kd=2), or only on V67? A mode present on every build is not something V67 created.
  2. AMPLITUDE. In a TRACKING band (f0 +/- 1.5 Hz) rather than the broad 40-49 Hz band, does its
     level respond to the rate-lane dose? Speed-matched, block-bootstrapped, quoted against a
     split-half null computed inside one dose with the identical estimator.

🛑 The broad-band 40-49 Hz null already on record (0.970 [0.787,1.154] and 0.938 [0.764,1.184])
   is not the same test: a 3 Hz tracking band around a Q~10 line has several times the
   signal-to-background of a 9 Hz band, so a broad-band null does not imply a tracking-band null.

Usage:  python studies/highway/highway_mode42.py
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r47_imu_lib as I         # noqa: E402
import highway_event_hunt as H   # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_scratch/out/_hwy_mode42.json"
NFFT = 256
TRACK = (41.0, 44.0)        # the tracking band around the measured 42.3 Hz line
NEG = (33.0, 36.0)          # pre-declared NEGATIVE control: same width, no line there
VB = [(22, 26), (26, 30), (30, 35)]


def vb(x):
    for i, (a, b) in enumerate(VB):
        if a <= x < b:
            return i
    return -1


def collect(vmin=22.0, engaged=True):
    """Per-window IMU records at v>=vmin with tracking-band and control-band envelopes."""
    out = []
    for rt, cd, pfx, segs, bld, kd in H.ROUTES:
        for s in segs:
            pim = ROOT / cd / f"{pfx}{s}_imu.npz"
            dc = H.load_seg(cd, pfx, s)
            if not pim.exists() or dc is None:
                continue
            di = dict(np.load(pim))
            v = np.abs(dc["cs_v"])
            lat = (dc["cc_lat"] > 0.5).astype(float)
            for ax in ("ay", "gz"):
                g = ax[0]
                u, odr, _, tu = I.uniform(di["at"] if g == "a" else di["gt"], di[ax])
                vi = I.lerp(tu, dc["t"], v)
                li = I.hold(tu, dc["t"], lat)
                f = np.fft.rfftfreq(NFFT, 1 / odr)
                taper = np.hanning(NFFT) + 1e-3
                cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
                for i in range(0, len(u) - NFFT + 1, NFFT // 2):
                    sl = slice(i, i + NFFT)
                    sp = float(np.mean(vi[sl]))
                    en = float(np.mean(li[sl]))
                    if sp < vmin or (engaged and en < 0.9) or (not engaged and en > 0.1):
                        continue
                    P = I.periodogram(u[sl], odr, NFFT, True)
                    if P is None:
                        continue
                    R = I.prom_spectrum(f, P)
                    f0, pr = I.locate(f, P, *TRACK, R=R)
                    fw, pw = I.locate(f, P, 30.0, 49.5, R=R)
                    out.append(dict(route=rt, build=bld, kd=kd, seg=int(s), axis=ax, i=i,
                                    v=sp, f0=f0, prom=pr, fwide=fw, promwide=pw,
                                    e_track=I.band_env(u[sl], odr, *TRACK, taper)[cw].max(),
                                    e_neg=I.band_env(u[sl], odr, *NEG, taper)[cw].max(),
                                    cell=(vb(sp), ax),
                                    blk=(rt, int(s), ax, i // 800)))
    return out


def ratio(A, B, key, rng, nboot=2000):
    """Speed-cell-stratified median log-ratio, resampling ~8 s blocks."""
    def est(X, Y):
        a, b = {}, {}
        for r in X:
            a.setdefault(r["cell"], []).append(r[key])
        for r in Y:
            b.setdefault(r["cell"], []).append(r[key])
        num = den = 0.0
        for c in set(a) & set(b):
            if len(a[c]) < 8 or len(b[c]) < 8:
                continue
            sa, sb = np.median(a[c]), np.median(b[c])
            if sa <= 0 or sb <= 0:
                continue
            w = 1.0 / (1.0 / len(a[c]) + 1.0 / len(b[c]))
            num += w * np.log(sa / sb)
            den += w
        return num / den if den else np.nan
    gA, gB = {}, {}
    for r in A:
        gA.setdefault(r["blk"], []).append(r)
    for r in B:
        gB.setdefault(r["blk"], []).append(r)
    LA, LB = list(gA.values()), list(gB.values())
    p = est(A, B)
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        dr[k] = est([r for i in rng.integers(0, len(LA), len(LA)) for r in LA[i]],
                    [r for i in rng.integers(0, len(LB), len(LB)) for r in LB[i]])
    if not np.isfinite(dr).any():
        return float(np.exp(p)), np.nan, np.nan, len(LA), len(LB)
    return (float(np.exp(p)), float(np.exp(np.nanpercentile(dr, 2.5))),
            float(np.exp(np.nanpercentile(dr, 97.5))), len(LA), len(LB))


def splithalf(P, key, rng, nrep=300):
    g = {}
    for r in P:
        g.setdefault(r["blk"], []).append(r)
    L = list(g.values())
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(L))
        h = len(L) // 2
        v = ratio([r for i in idx[:h] for r in L[i]], [r for i in idx[h:] for r in L[i]],
                  key, rng, nboot=0)[0]
        if np.isfinite(v) and v > 0:
            out.append(v)
    o = np.array(out)
    return (float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)),
            float(np.percentile(o, 97.5)), len(o))


def main():
    store = {}
    W = collect()
    print(f"[{len(W)} engaged IMU windows, v >= 22 m/s, axes ay+gz]")

    G.hdr("1.  PRESENCE -- is the 42 Hz line on every build, or only on V67?")
    print(f"    {'route':>7}{'build':>7}{'Kd':>6}{'n':>7}{'f0 (41-44 band)':>18}"
          f"{'prom p50':>11}{'prom p90':>11}{'wide f0 p50':>13}{'track env p50':>15}")
    for rt in ("2b", "2c", "37", "3a", "3b", "47"):
        s = [r for r in W if r["route"] == rt]
        if len(s) < 20:
            print(f"    {rt:>7}{H.BUILD.get(rt, ''):>7}{H.KD.get(rt, 0):>6.2f}{len(s):>7}"
                  f"   (no engaged exposure above 22 m/s)")
            continue
        f0 = np.array([r["f0"] for r in s])
        pr = np.array([r["prom"] for r in s])
        print(f"    {rt:>7}{H.BUILD[rt]:>7}{H.KD[rt]:>6.2f}{len(s):>7}{np.median(f0):>18.2f}"
              f"{np.median(pr):>11.2f}{np.percentile(pr, 90):>11.2f}"
              f"{np.median([r['fwide'] for r in s]):>13.2f}"
              f"{np.median([r['e_track'] for r in s]):>15.5g}")
        store.setdefault("presence", {})[rt] = dict(
            build=H.BUILD[rt], kd=H.KD[rt], n=len(s), f0=float(np.median(f0)),
            prom_p50=float(np.median(pr)), prom_p90=float(np.percentile(pr, 90)))
    print("\n    prominence = peak / its own local median floor. A value near 1 means NO line;\n"
          "    the kit treats > 4 as a real line. If every build reads the same f0 with a\n"
          "    comparable prominence, V67 did not create this mode.")

    G.hdr("2.  AMPLITUDE by dose, TRACKING band 41-44 Hz, speed-cell matched, block bootstrap")
    pools = {kd: [r for r in W if r["kd"] == kd] for kd in (1.0, 2.0, 2.44)}
    for key, lab in (("e_track", "41-44 Hz envelope (the mode)"),
                     ("e_neg", "33-36 Hz envelope (NEGATIVE control)"),
                     ("prom", "41-44 Hz prominence")):
        print(f"\n    {lab}")
        for a, b in ((2.0, 1.0), (2.44, 1.0), (2.44, 2.0)):
            r, lo, hi, na, nb = ratio(pools[a], pools[b], key, RNG)
            print(f"      Kd {a:g}/{b:g}   {r:7.3f}  [{lo:.3f}, {hi:.3f}]   "
                  f"blocks {na} vs {nb}")
            store.setdefault("dose", {}).setdefault(key, {})[f"{a:g}/{b:g}"] = [r, lo, hi]
        n = splithalf(pools[2.0], key, RNG)
        n2 = splithalf(pools[2.44], key, RNG)
        print(f"      SPLIT-HALF NULL  Kd=2 pool {n[0]:.3f} [{n[1]:.3f}, {n[2]:.3f}]   "
              f"Kd=2.44 pool {n2[0]:.3f} [{n2[1]:.3f}, {n2[2]:.3f}]")
        store["dose"][key]["null"] = [list(n[:3]), list(n2[:3])]

    G.hdr("2b. 🛑 THE NOISE FLOOR THAT MATTERS IS *BETWEEN ROUTES*, NOT WITHIN ONE.\n"
          "    Kd=1 is route 2b alone and Kd=2.44 is route 47 alone, so 'Kd 2.44/1' is also\n"
          "    'route 47 / route 2b' -- different road, tyres, weather and date. A split-half\n"
          "    null computed INSIDE one route cannot see any of that; it only measures\n"
          "    within-route sampling noise, which is why it came out [0.89, 1.12].\n"
          "    The Kd=2 dose is the only one with TWO routes, so it can supply the real floor:\n"
          "    route 37 (V62) vs route 3b (V65) -- byte-identical control path, same dose.")
    r37 = [r for r in W if r["route"] == "37"]
    r3b = [r for r in W if r["route"] == "3b"]
    for key, lab in (("e_track", "41-44 Hz envelope"), ("e_neg", "33-36 Hz envelope"),
                     ("prom", "41-44 Hz prominence")):
        rr, lo, hi, na, nb = ratio(r37, r3b, key, RNG)
        print(f"    {lab:>24}   route 37 / route 3b (SAME Kd=2 dose) = {rr:6.3f} "
              f"[{lo:.3f}, {hi:.3f}]   blocks {na} vs {nb}")
        store.setdefault("between_route_null", {})[key] = [rr, lo, hi]
    print("\n    Read every dose ratio in §2 against THIS spread, not against the within-route\n"
          "    split-half. A dose effect must clear the route-to-route floor to be a finding.")

    G.hdr("3.  IS THE MODE ROAD-EXCITED? f0 and prominence vs speed, pooled over builds")
    print(f"    {'speed':>10}{'n':>7}{'f0 p50':>10}{'prom p50':>11}{'prom p90':>11}"
          f"{'track env p50':>15}{'  neg env p50':>15}")
    for a, b in VB:
        s = [r for r in W if a <= r["v"] < b]
        if len(s) < 20:
            continue
        print(f"    {f'{a}-{b}':>10}{len(s):>7}{np.median([r['f0'] for r in s]):>10.2f}"
              f"{np.median([r['prom'] for r in s]):>11.2f}"
              f"{np.percentile([r['prom'] for r in s], 90):>11.2f}"
              f"{np.median([r['e_track'] for r in s]):>15.5g}"
              f"{np.median([r['e_neg'] for r in s]):>15.5g}")

    G.hdr("4.  DISENGAGED CONTROL -- the mode with LKAS OFF")
    D = collect(vmin=22.0, engaged=False)
    print(f"    disengaged windows above 22 m/s in the WHOLE corpus: {len(D)}")
    if len(D) < 20:
        print("    🛑 There is no disengaged highway driving anywhere in this corpus. The\n"
              "       operator's 'it only happens with LKAS on' cannot be tested on this data,\n"
              "       and neither can 'the mode is there anyway'. This is the single cheapest\n"
              "       missing measurement in the kit: one highway run with LKAS off.")
    D2 = collect(vmin=8.0, engaged=False)
    print(f"    disengaged windows above 8 m/s: {len(D2)}")
    if len(D2) >= 20:
        print(f"      f0 p50 {np.median([r['f0'] for r in D2]):.2f} Hz   prom p50 "
              f"{np.median([r['prom'] for r in D2]):.2f}   speed p50 "
              f"{np.median([r['v'] for r in D2]):.1f} m/s")
    store["disengaged_hwy_windows"] = len(D)

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
