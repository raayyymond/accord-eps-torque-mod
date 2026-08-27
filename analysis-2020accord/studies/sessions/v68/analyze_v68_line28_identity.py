#!/usr/bin/env python3
"""IDENTITY of the fixed ~28 Hz engaged-highway line: engine order, wheel order, or mode?

Three candidates, three slopes, one regression each. The line frequency is re-measured per
SPEED bin and per RPM bin from AVERAGED periodograms (average first, then peak-find -- the fix
that exposed the withdrawn 42 Hz mode), then regressed:

    engine order 1   f0 = rpm/60          slope +0.01667 Hz/rpm,  0 vs road speed
    engine order 2   f0 = rpm/30          slope +0.03333 Hz/rpm
    wheel order 2    f0 = 2*0.4808*v      slope +0.9616 Hz per m/s, ~0 vs rpm
    a chassis MODE   f0 fixed             slope 0 against BOTH

🛑 The CVT is what makes this necessary: it holds rpm near-constant at cruise (prior session,
corr(rpm, v) = +0.270), so an engine order LOOKS like a fixed mode when plotted against road
speed alone. Only the rpm axis separates them, and this kit has come close to publishing a wheel
order as a firmware effect three times.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import periodogram, runs_of  # noqa: E402
from analyze_v68_highway_arms import HWY, NFFT, HOP, mean_fs, segs_of  # noqa: E402

CACHE = ROOT / "_scratch/cache/v68"


def with_rpm(route):
    """Yield (seg, cache-dict) with an `rpm` channel interpolated onto the 0x14A grid."""
    for s, d in segs_of(route):
        p = CACHE / f"{route}s{s}_rpm.npz"
        if not p.exists():
            continue
        r = np.load(p)
        d["rpm"] = np.interp(d["t"], r["t"], r["rpm"])
        yield s, d


def binned_lines(route, eng, key, bins, lo=18.0, hi=40.0, vlo=HWY):
    """Averaged periodogram inside each bin of `key`, then peak-find in [lo,hi]."""
    out = []
    for blo, bhi in bins:
        acc, n, fref, ks, vs, rs = None, 0, None, [], [], []
        for _s, d in with_rpm(route):
            fs = mean_fs(d["t"])
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            for a, b in runs_of((d["cc_lat"] > 0.5) if eng else ~(d["cc_lat"] > 0.5),
                                d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    v = float(np.mean(d["cs_v"][sl]))
                    rp = float(np.mean(d["rpm"][sl]))
                    kv = {"v": v, "rpm": rp}[key]
                    if v < vlo or not (blo <= kv < bhi):
                        continue
                    # a window whose rpm swings wildly is not a clean bin member
                    if np.ptp(d["rpm"][sl]) > 250:
                        continue
                    P = periodogram(d["tq"][a + i:a + i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    if acc is None:
                        acc, fref = np.zeros_like(P), f
                    if len(P) == len(acc):
                        acc += P; n += 1; ks.append(kv); vs.append(v); rs.append(rp)
        if n < 8:
            out.append(dict(blo=blo, bhi=bhi, n=n))
            continue
        Pm = acc / n
        R = G.prom_spectrum(fref, Pm)
        f0, pr = G.locate(fref, Pm, lo, hi, R=R)
        out.append(dict(blo=blo, bhi=bhi, n=n, k=float(np.mean(ks)), v=float(np.mean(vs)),
                        rpm=float(np.mean(rs)), f0=f0, prom=pr))
    return out


def theil_sen(x, y):
    s = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(x)) for j in range(i + 1, len(x))
         if x[j] != x[i]]
    return (float(np.median(s)), float(np.percentile(s, 10)), float(np.percentile(s, 90))
            ) if s else (np.nan,) * 3


def main():
    res = {}

    G.hdr("0. THE CVT PROBLEM, MEASURED ON THESE ROUTES")
    for route, eng in (("4e", True), ("4c", False)):
        vs, rs = [], []
        for _s, d in with_rpm(route):
            m = (d["cs_v"] >= HWY) & (((d["cc_lat"] > 0.5)) == eng)
            if m.sum() > 100:
                vs.append(d["cs_v"][m]); rs.append(d["rpm"][m])
        if not vs:
            continue
        v = np.concatenate(vs); r = np.concatenate(rs)
        cc = float(np.corrcoef(v, r)[0, 1])
        res[route + "_corr"] = cc
        print(f"  {route} ({'engaged' if eng else 'manual'}): corr(rpm, v) = {cc:+.3f}   "
              f"rpm p5..p95 {np.percentile(r, 5):.0f}..{np.percentile(r, 95):.0f} "
              f"(median {np.median(r):.0f})   "
              f"⇒ engine order 1 spans {np.percentile(r, 5) / 60:.1f}..{np.percentile(r, 95) / 60:.1f} Hz")
    print("\n  ⇒ rpm is nearly decoupled from road speed, exactly as a CVT must be. So a speed")
    print("    sweep ALONE cannot distinguish an engine order from a fixed mode.")

    G.hdr("1. THE LINE AGAINST RPM -- the axis that separates engine from mode")
    print("  engine order 1 predicts slope +0.01667 Hz/rpm; order 2 +0.03333; a MODE 0.0000.\n")
    res["rpm"] = {}
    for route, eng in (("4e", True), ("4c", False)):
        rows = binned_lines(route, eng, "rpm",
                            [(1300, 1420), (1420, 1500), (1500, 1580), (1580, 1680),
                             (1680, 1800), (1800, 2100)])
        good = [r for r in rows if r.get("prom", 0) > 4]
        print(f"  --- {route} ({'ENGAGED' if eng else 'MANUAL'}) ---")
        for r in rows:
            if "f0" not in r:
                print(f"    rpm {r['blo']}-{r['bhi']}: n={r['n']} -- too few")
                continue
            print(f"    rpm {r['blo']}-{r['bhi']} (n={r['n']:3d}, mean {r['rpm']:6.0f}, "
                  f"v {r['v']:5.2f}): peak {r['f0']:6.2f} Hz prom {r['prom']:6.2f}"
                  f"{' ***' if r['prom'] > 4 else '    '}   "
                  f"order1 predicts {r['rpm'] / 60:5.2f}   order2 {r['rpm'] / 30:5.2f}")
        res["rpm"][route] = rows
        if len(good) >= 3:
            sl, l10, l90 = theil_sen([r["rpm"] for r in good], [r["f0"] for r in good])
            print(f"    Theil-Sen slope vs rpm: {sl:+.5f} Hz/rpm  [{l10:+.5f}, {l90:+.5f}]  "
                  f"(order1 +0.01667, order2 +0.03333, MODE 0)")
            res["rpm"][route + "_slope"] = [sl, l10, l90]
        else:
            print(f"    only {len(good)} bins carry a line (prom > 4) -- no slope quoted")
        print()

    G.hdr("2. THE SAME LINE AGAINST ROAD SPEED, rpm-controlled")
    print("  wheel order 2 predicts +0.9616 Hz per m/s; a MODE and an engine order both ~0.\n")
    res["speed"] = {}
    for route, eng in (("4e", True), ("4c", False)):
        rows = binned_lines(route, eng, "v",
                            [(19, 21), (21, 23), (23, 25), (25, 27), (27, 29), (29, 32)])
        good = [r for r in rows if r.get("prom", 0) > 4]
        print(f"  --- {route} ({'ENGAGED' if eng else 'MANUAL'}) ---")
        for r in rows:
            if "f0" not in r:
                continue
            print(f"    v {r['blo']}-{r['bhi']} (n={r['n']:3d}, mean {r['v']:5.2f}, "
                  f"rpm {r['rpm']:6.0f}): peak {r['f0']:6.2f} Hz prom {r['prom']:6.2f}"
                  f"{' ***' if r['prom'] > 4 else '    '}   "
                  f"wheel-order-2 predicts {2 * 0.4808 * r['v']:5.2f}   "
                  f"engine-order-1 {r['rpm'] / 60:5.2f}")
        res["speed"][route] = rows
        if len(good) >= 3:
            sl, l10, l90 = theil_sen([r["v"] for r in good], [r["f0"] for r in good])
            print(f"    Theil-Sen slope vs speed: {sl:+.4f} Hz per m/s  [{l10:+.4f}, {l90:+.4f}]  "
                  f"(wheel order 2 = +0.9616, MODE = 0)")
            res["speed"][route + "_slope"] = [sl, l10, l90]
        print()

    G.hdr("3. VERDICT INPUTS")
    print("  Collected so the reader can check the arithmetic rather than trust the label:")
    for route in ("4e", "4c"):
        rr = res["rpm"].get(route, [])
        gg = [r for r in rr if r.get("prom", 0) > 4]
        if gg:
            f0s = np.array([r["f0"] for r in gg]); rp = np.array([r["rpm"] for r in gg])
            print(f"  {route}: line at {f0s.mean():.2f} Hz (sd {f0s.std():.2f}) over rpm "
                  f"{rp.min():.0f}-{rp.max():.0f}; implied engine order "
                  f"{np.mean(f0s * 60 / rp):.3f} (sd {np.std(f0s * 60 / rp):.3f})")

    Path(HERE / "_scratch/out/_v68_line28_identity.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {HERE / '_scratch/out/_v68_line28_identity.json'}")


if __name__ == "__main__":
    main()
