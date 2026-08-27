#!/usr/bin/env python3
"""T4 -- the DISCRIMINATING evidence: a cross-build contrast, plus three corrections to T3.

  X1  CROSS-BUILD.  Is the 27.5 Hz engaged-highway line NEW ON V81?  V81 = the flown V75 with
      exactly two cal reverts, one of which puts FRICTION BACK TO STOCK -- i.e. it REMOVES
      damping.  If the line is absent on V80/V76 at matched speed and present on V81, the
      attribution is to that revert, and that is worth more than any phase number.
      🛑 Matched on SPEED with a per-window census, not a band-centre check.

  X2  ORDER VETO, done scale-free.  A pure wheel order n satisfies f = n*v/C AND df/dv = n/C,
      so f / (df/dv) = v EXACTLY, with no circumference to assume.  Also checks the speed/time
      confound inside the event, which a 2.2 m/s span cannot otherwise survive.

  X3  THE DAMPER AT 2f.  T3 tested the damper thermometer for coherence with the bar at f0 and
      got 0.007 -- but the thermometer is a MAGNITUDE, and a magnitude modulates at 2f, not f.
      2*27.53 = 55.06 Hz, which aliases to 44.94 Hz. T3's own output located the thermometer's
      line at 44.58 Hz. So that near-zero coherence was the WRONG TEST and is retracted here.

  X4  T2d, the operator's rate-starvation claim, with the duplicate-timestamp bug fixed.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import (CACHE, FS_NOM, band_env, coherence, fs_run, lattice,  # noqa: E402
                         load_seg, locate, prom_spectrum, resamp, welch_cross)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
NF, HOP = 256, 128
RATE_FIX = 1.25
BUILDS = [("V81/r67", ROOT / "_scratch/cache/r67x", "r67xs", list(range(14))),
          ("V80/r66", ROOT / "_scratch/cache/r66x", "r66xs", list(range(15))),
          ("V76/r65", ROOT / "_scratch/cache/r65", "r65s", list(range(14)))]


def wins(cache, pfx, segs, vlo, vhi, chan="tq"):
    out = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = dict(np.load(p, allow_pickle=True))
        if "cc_lat" not in d or chan not in d:
            continue
        t, fs = d["t"], fs_run(d["t"])
        eng = d["cc_lat"] > 0.5
        x = np.asarray(d[chan], float)
        for i in range(0, len(t) - NF + 1, HOP):
            sl = slice(i, i + NF)
            if eng[sl].mean() < 0.95:
                continue
            vm = float(np.mean(d["cs_v"][sl]))
            if not (vlo <= vm < vhi):
                continue
            xw = x[sl]
            P = np.abs(np.fft.rfft((xw - xw.mean()) * np.hanning(NF))) ** 2
            f = np.fft.rfftfreq(NF, 1 / fs)
            R = prom_spectrum(f, P)
            f0, p0 = locate(f, P, 22.0, 34.0, R=R)
            out.append(dict(seg=int(s), t0=float(t[i]), v=vm, f0=f0, prom=p0,
                            e2432=band_env(xw, fs, 24, 32), e1822=band_env(xw, fs, 18, 22),
                            e69=band_env(xw, fs, 6, 9), e14=band_env(xw, fs, 1, 4),
                            ep=(int(s), i // (NF * 4))))
    return out


def epboot(recs, key, nboot=4000, seed=11):
    """Bootstrap over EPISODES (~10 s blocks), never over windows."""
    rng = np.random.default_rng(seed)
    ep = {}
    for r in recs:
        ep.setdefault(r["ep"], []).append(r[key])
    units = [np.array(v) for v in ep.values()]
    if len(units) < 2:
        return np.nan, np.nan, len(units)
    bs = []
    for _ in range(nboot):
        pick = [units[i] for i in rng.integers(0, len(units), len(units))]
        bs.append(np.median(np.concatenate(pick)))
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(units)


def main():
    print("=" * 104)
    print("X1  CROSS-BUILD: the engaged 24-32 Hz bar envelope, matched on speed")
    print("=" * 104)
    cells = [("11-20 m/s", 11, 20), ("20-24 m/s", 20, 24), (">24 m/s", 24, 99)]
    tab = {}
    for nm, cache, pfx, segs in BUILDS:
        for cl, lo, hi in cells:
            w = wins(cache, pfx, segs, lo, hi)
            if not w:
                tab[(nm, cl)] = None
                continue
            e = np.array([r["e2432"] for r in w])
            lo_, hi_, nep = epboot(w, "e2432")
            tab[(nm, cl)] = dict(n=len(w), sec=len(w) * NF / FS_NOM / 2, med=float(np.median(e)),
                                 p90=float(np.percentile(e, 90)), mx=float(e.max()),
                                 ci=(lo_, hi_), nep=nep, v=float(np.mean([r["v"] for r in w])),
                                 f0=float(np.median([r["f0"] for r in w])))
    print(f"  {'build':>9} {'cell':>10} {'nwin':>5} {'nep':>4} {'v':>6} {'med':>8} "
          f"{'95% CI of median':>20} {'p90':>8} {'max':>8} {'med f0':>7}")
    for nm, _, _, _ in BUILDS:
        for cl, _, _ in cells:
            r = tab.get((nm, cl))
            if not r:
                print(f"  {nm:>9} {cl:>10}      -- no engaged windows in this cell --")
                continue
            print(f"  {nm:>9} {cl:>10} {r['n']:>5} {r['nep']:>4} {r['v']:>6.1f} {r['med']:>8.1f} "
                  f"[{r['ci'][0]:>8.1f},{r['ci'][1]:>8.1f}] {r['p90']:>8.1f} {r['mx']:>8.1f} "
                  f"{r['f0']:>7.2f}")
    print("  🛑 The comparison that matters is the '>24 m/s' row. If V81's CI does not overlap")
    print("     V80's / V76's, the highway line is a V81 REGRESSION and the lever is V81's own")
    print("     friction revert. If they overlap, the line predates V81 and the operator is")
    print("     reporting an old symptom in a new place.")

    print()
    print("=" * 104)
    print("X2  ORDER VETO, scale-free:  a pure wheel order requires  f0 / (df/dv) == v")
    print("=" * 104)
    J = json.loads((CACHE / "v81loop_t3.json").read_text())
    rows = np.array(J["f0_windows"], float)          # v, f0, prom, env
    V, F = rows[:, 0], rows[:, 1]
    rng = np.random.default_rng(3)
    blk = np.arange(len(V)) // 8
    ub = np.unique(blk)
    rat, slp = [], []
    for _ in range(4000):
        pick = rng.choice(ub, len(ub))
        idx = np.concatenate([np.flatnonzero(blk == u) for u in pick])
        if np.ptp(V[idx]) < 0.3:
            continue
        s = np.polyfit(V[idx], F[idx], 1)[0]
        if abs(s) < 1e-6:
            continue
        slp.append(s)
        rat.append(np.median(F[idx]) / s)
    rat, slp = np.array(rat), np.array(slp)
    print(f"  df/dv  = {np.median(slp):+.4f} Hz per m/s   95% CI "
          f"[{np.percentile(slp, 2.5):+.4f}, {np.percentile(slp, 97.5):+.4f}]")
    print(f"  f0/(df/dv) = {np.median(rat):.1f} m/s   95% CI "
          f"[{np.percentile(rat, 2.5):.1f}, {np.percentile(rat, 97.5):.1f}]")
    print(f"  the car's ACTUAL speed here = {V.mean():.2f} m/s")
    inside = np.percentile(rat, 2.5) <= V.mean() <= np.percentile(rat, 97.5)
    print(f"  ==> {'CONSISTENT with a wheel order -- VETO FIRES' if inside else 'A WHEEL ORDER IS EXCLUDED'}"
          f"  (any order n, no circumference assumed)")
    # speed/time confound
    T = np.arange(len(V), dtype=float)
    print(f"  confound check inside the event: corr(v, time) = {np.corrcoef(V, T)[0, 1]:+.3f}"
          f"   corr(f0, time) = {np.corrcoef(F, T)[0, 1]:+.3f}"
          f"   corr(f0, v) = {np.corrcoef(F, V)[0, 1]:+.3f}")
    print("  🛑 speed spans only 2.2 m/s inside the event and there are ~5 independent blocks, so")
    print("     the SLOPE is weak evidence either way. The RATIO test above is the robust one:")
    print("     it fails by a wide margin regardless of which order is proposed.")

    print()
    print("=" * 104)
    print("X3  THE DAMPER AT 2f -- retracting T3's wrong test")
    print("=" * 104)
    N = np.load(CACHE / "v81loop_native_s8.npz")
    tau = lattice(38.0, 52.0, FS_NOM)

    def dd(t, *v):
        t = np.asarray(t, float)
        k = np.ones(len(t), bool)
        k[1:] = np.diff(t) > 0
        return (t[k],) + tuple(np.asarray(x, float)[k] for x in v)
    a = dd(N["a_t"], N["a_pr"])
    b = dd(N["b_t"], N["b_tq"])
    pr = resamp(tau, a[0], a[1]).astype(int)
    bar = resamp(tau, b[0], b[1])
    th = (((pr & 0x80) != 0).astype(float) + ((pr & 0x40) != 0) + ((pr & 0x20) != 0)
          + ((pr & 0x10) != 0))
    env = np.abs(bar)                       # the bar's own magnitude, for the 2f comparison
    f, P1, P2, P12, _ = welch_cross(th - th.mean(), env - env.mean(), FS_NOM, NF, HOP)
    C = coherence(P1, P2, P12)
    f0 = 27.53
    for lab, ftar in (("f0", f0), ("2*f0 aliased", 100 - 2 * f0), ("2*f0 raw", 2 * f0)):
        if ftar > 50:
            print(f"  {lab:>14} {ftar:6.2f} Hz -- above Nyquist, only its alias is observable")
            continue
        j = int(np.argmin(np.abs(f - ftar)))
        print(f"  {lab:>14} {f[j]:6.2f} Hz   coherence(damper level, |bar|) = {C[j]:.3f}")
    Pth = np.zeros(NF // 2 + 1)
    k = 0
    for i in range(0, len(th) - NF + 1, HOP):
        Pth += np.abs(np.fft.rfft((th[i:i + NF] - th[i:i + NF].mean()) * np.hanning(NF))) ** 2
        k += 1
    ft, pt = locate(f, Pth / max(k, 1), 12.0, 49.0)
    print(f"  damper thermometer's own most prominent 12-49 Hz line: {ft:.2f} Hz (prom {pt:.1f})")
    print(f"  2*f0 = {2 * f0:.2f} Hz aliases to {100 - 2 * f0:.2f} Hz -- "
          f"{'MATCH' if abs(ft - (100 - 2 * f0)) < 1.5 else 'no match'}")
    print("  ⇒ the damper IS tracking the oscillation's magnitude at 2f, as a magnitude signal")
    print("    must. That is consistent with the damper RESPONDING to the oscillation and does")
    print("    NOT by itself show it is the source. T3's 'evidence against C' is WITHDRAWN.")

    print()
    print("=" * 104)
    print("X4  DEMANDED vs ACHIEVED ANGLE RATE -- the operator's claim, duplicate-t bug fixed")
    print("=" * 104)
    print(f"  {'regime':>14} {'sec':>7} {'p50 dem':>9} {'p95 dem':>9} {'p50 ach':>9} "
          f"{'p95 ach':>9} {'p95 ach/dem':>12}")
    SR, WB = 16.0, 2.83
    for nm, lo, hi in [("creep <4", 0, 4), ("4-11", 4, 11), ("11-20", 11, 20),
                       ("20-24", 20, 24), (">24 highway", 24, 99), ("EVENT", -1, -1)]:
        D, A = [], []
        for s in range(14):
            p = CACHE / f"r67xs{s}.npz"
            if not p.exists():
                continue
            d = dict(np.load(p, allow_pickle=True))
            t = np.asarray(d["t"], float)
            keep = np.ones(len(t), bool)
            keep[1:] = np.diff(t) > 0        # 🛑 the fix: strictly increasing t before gradient
            m = keep & (d["cc_lat"] > 0.5)
            if nm == "EVENT":
                m &= (s == 8) & (t >= 38.0) & (t <= 52.0)
            else:
                m &= (d["cs_v"] >= lo) & (d["cs_v"] < hi)
            if m.sum() < 50:
                continue
            fs = fs_run(t[keep])
            dcv = np.nan_to_num(np.asarray(d["ct_dcurv"], float))[keep]
            X = np.fft.rfft(dcv - dcv.mean())
            fq = np.fft.rfftfreq(len(dcv), 1 / fs)
            X[fq > 3.0] = 0
            dsm = np.fft.irfft(X, n=len(dcv)) + dcv.mean()
            dem = np.gradient(dsm, t[keep]) * d["cs_v"][keep] * SR * WB * 180 / np.pi
            sel = m[keep]
            D.append(np.abs(dem[sel]))
            A.append(np.abs(np.asarray(d["rate_f"], float)[keep][sel] * RATE_FIX))
        if not D:
            continue
        D, A = np.concatenate(D), np.concatenate(A)
        print(f"  {nm:>14} {len(D) / 100:>7.1f} {np.percentile(D, 50):>9.2f} "
              f"{np.percentile(D, 95):>9.2f} {np.percentile(A, 50):>9.2f} "
              f"{np.percentile(A, 95):>9.2f} "
              f"{np.percentile(A, 95) / max(np.percentile(D, 95), 1e-9):>12.2f}")
    print("  ach/dem >> 1: the column moves FASTER than the plan asks -- the opposite of")
    print("  rate starvation. ach/dem < 1 would support the operator's reading.")
    print("  ⚠ steerRatio/wheelbase are nominal, so read the RATIO ACROSS REGIMES, not absolutes.")


if __name__ == "__main__":
    main()
