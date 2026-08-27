#!/usr/bin/env python3
"""D5 ss1-2 -- does the 18-22 Hz band or the 6-9 Hz band carry the operator's SPEED/ANGLE story?

The operator (2026-08-05) says grind #1 and the micro ratchet are the SAME frequency in the wheel,
differing only in audibility; grind #1 is at ~5 mph near zero angle, the ratchet is speed-INDEPENDENT.
This kit records the opposite mapping (grind #1 = 18-22 Hz, ratchet = 7.79 Hz).

Two falsifiable predictions, run on the EXISTING window corpus with the EXISTING instrument:
  ss1  SPEED PROFILE, engaged.   operator => e_18-22 peaks at ~2.2 m/s and e_6-9 is FLAT.
                                 kit      => e_6-9 flat-ish is the ratchet, 18-22 is creep-peaked.
  ss2  ANGLE PROFILE at creep.   operator => e_18-22 maximal near ZERO angle.

Everything numeric is `_grind2_lib` / `_nearcentre_lib` unchanged: same p99 band envelope, same
`fs_lattice`, same EPISODE bootstrap, same split-half null.
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
import _nearcentre_lib as N  # noqa: E402

OUT = ROOT / "_scratch/out/_d5_speed_angle.json"
RNG = np.random.default_rng(20260805)

# The brief's speed bins, m/s.
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 1e9)]
VN = ["0-2", "2-4", "4-8", "8-15", "15-25", "25+"]
BANDS = ["6-9", "18-22", "24-28", "40-49"]

# |angle - route zero| bins, deg (the brief's).
AB = [(0.0, 3.0), (3.0, 10.0), (10.0, 25.0), (25.0, 45.0), (45.0, 1e9)]
AN = ["0-3", "3-10", "10-25", "25-45", "45+"]


def med_ci(rs, key, nboot=1500):
    """(median, lo, hi, n_win, n_ep) resampling EPISODES (`G.EPKEY`), never windows."""
    if not rs:
        return (np.nan,) * 3 + (0, 0)
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    per = [np.array([x[key] for x in e], float) for e in eps.values()]
    allv = np.concatenate(per)
    allv = allv[np.isfinite(allv)]
    if not len(allv):
        return (np.nan,) * 3 + (len(rs), len(per))
    draws = np.full(nboot, np.nan)
    for b in range(nboot):
        i = RNG.integers(0, len(per), len(per))
        v = np.concatenate([per[j] for j in i])
        v = v[np.isfinite(v)]
        if len(v):
            draws[b] = np.median(v)
    return (float(np.median(allv)), float(np.nanpercentile(draws, 2.5)),
            float(np.nanpercentile(draws, 97.5)), len(rs), len(per))


def split_half_null(rs, key, nrep=300):
    """The pool's OWN noise floor for a between-cell median ratio, same estimator, halved episodes."""
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    eps = list(eps.values())
    if len(eps) < 6:
        return np.nan, np.nan, np.nan
    out = []
    for _ in range(nrep):
        idx = RNG.permutation(len(eps))
        h = len(eps) // 2
        a = np.concatenate([[x[key] for x in eps[i]] for i in idx[:h]])
        b = np.concatenate([[x[key] for x in eps[i]] for i in idx[h:]])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and np.median(b) > 0:
            out.append(np.median(a) / np.median(b))
    out = np.array(out, float)
    if not len(out):
        return np.nan, np.nan, np.nan
    return (float(np.median(out)), float(np.percentile(out, 2.5)),
            float(np.percentile(out, 97.5)))


def vbin(v):
    for i, (lo, hi) in enumerate(VB):
        if lo <= v < hi:
            return i
    return len(VB) - 1


def main():
    store = N.records()
    res = {"builds": {}, "pooled": {}, "angle": {}, "meta": {}}

    # ---------------------------------------------------------------- ss0 route zeros -----------
    zeros = {}
    for b in N.LADDER:
        c, n, tier = N.route_zero(b, store)
        zeros[b] = dict(c=c, n=n, tier=tier)
    res["meta"]["route_zero"] = zeros
    N.hdr("ss0  ROUTE SENSOR ZERO (signed cs_ang at straight cruise) -- needed for the angle axis")
    for b in N.LADDER:
        z = zeros[b]
        print(f"  {b:<10} c = {z['c']:+7.2f} deg   n={z['n']:<5d} tier={z['tier']}")

    # ---------------------------------------------------------------- ss1 speed profile ---------
    eng = {b: [r for r in store.get(b, []) if r["eng"] == 1] for b in N.LADDER}
    pool = [r for b in N.LADDER for r in eng[b]]

    N.hdr("ss1  SPEED PROFILE, ENGAGED, ALL BUILDS POOLED -- median p99 band envelope (counts, tq)")
    print("  exposure census first; an empty bin is UNPOWERED, not null.\n")
    hdrline = f"  {'v (m/s)':<9}{'win':>7}{'ep':>6}{'sec':>8}{'builds':>8}  " + \
              "".join(f"{('e_'+k):>26}" for k in BANDS)
    print(hdrline)
    prof = {}
    for i, name in enumerate(VN):
        sub = [r for r in pool if vbin(r["v"]) == i]
        nb = len({r["build"] for r in sub})
        row = {"n": len(sub), "sec": len(sub) * 1.28, "nbuild": nb}
        s = f"  {name:<9}{len(sub):>7}"
        neps = len({r[G.EPKEY] for r in sub})
        s += f"{neps:>6}{len(sub)*1.28:>8.0f}{nb:>8}  "
        for k in BANDS:
            m, lo, hi, n, ne = med_ci(sub, "e_" + k)
            row[k] = dict(med=m, lo=lo, hi=hi, nwin=n, nep=ne)
            s += f"{m:>10.0f} [{lo:>6.0f},{hi:>6.0f}]" if np.isfinite(m) else f"{'--':>26}"
        prof[name] = row
        print(s)
    res["pooled"]["speed"] = prof

    # per-build, so a pooled shape cannot be a build-composition artefact
    N.hdr("ss1b  SPEED PROFILE PER BUILD -- median e_18-22 / e_6-9, and their RATIO to 24-28")
    for b in N.LADDER:
        rs = eng[b]
        if len(rs) < 20:
            continue
        cells = {}
        line = f"  {b:<10}"
        for i, name in enumerate(VN):
            sub = [r for r in rs if vbin(r["v"]) == i]
            if len(sub) < 8:
                cells[name] = None
                line += f"{name}:{'--':>17}  "
                continue
            m18 = float(np.median([r["e_18-22"] for r in sub]))
            m69 = float(np.median([r["e_6-9"] for r in sub]))
            cells[name] = dict(n=len(sub), e18=m18, e69=m69,
                               e24=float(np.median([r["e_24-28"] for r in sub])),
                               e40=float(np.median([r["e_40-49"] for r in sub])))
            line += f"{name}:{m18:>7.0f}/{m69:<7.0f}n{len(sub):<4d}"
        res["builds"].setdefault(b, {})["speed"] = cells
        print(line)
    print("\n  (each cell is  median e_18-22 / median e_6-9 , n windows)")

    # ---------------------------------------------------------------- ss1c normalised shape -----
    # The p99 envelope of `tq` falls with speed for EVERY band because driver effort falls.  The
    # SHAPE question is therefore asked on each band normalised to its own 15-25 m/s value, and on
    # the 18-22 / 24-28 ratio, which divides out any broadband effort term.
    N.hdr("ss1c  SHAPE, effort-normalised.  each band / its own value in the 15-25 m/s bin")
    base = {k: prof["15-25"][k]["med"] for k in BANDS}
    print(f"  {'v (m/s)':<9}" + "".join(f"{('e_'+k):>12}" for k in BANDS) +
          f"{'18-22 / 24-28':>16}{'6-9 / 24-28':>14}")
    for name in VN:
        r = prof[name]
        s = f"  {name:<9}"
        for k in BANDS:
            v = r[k]["med"] / base[k] if base[k] else np.nan
            s += f"{v:>12.2f}" if np.isfinite(v) else f"{'--':>12}"
        rr = r["18-22"]["med"] / r["24-28"]["med"] if r["24-28"]["med"] else np.nan
        r2 = r["6-9"]["med"] / r["24-28"]["med"] if r["24-28"]["med"] else np.nan
        print(s + f"{rr:>16.2f}{r2:>14.2f}")

    # null floor for the pooled speed contrast
    nl18 = split_half_null(pool, "e_18-22")
    nl69 = split_half_null(pool, "e_6-9")
    res["pooled"]["null"] = {"18-22": nl18, "6-9": nl69}
    print(f"\n  split-half null (pooled engaged, same estimator):  "
          f"e_18-22 {nl18[0]:.3f} [{nl18[1]:.3f},{nl18[2]:.3f}]   "
          f"e_6-9 {nl69[0]:.3f} [{nl69[1]:.3f},{nl69[2]:.3f}]")

    # ---------------------------------------------------------------- ss2 angle at creep --------
    N.hdr("ss2  ANGLE PROFILE at 1.5-3.0 m/s, ENGAGED -- |cs_ang - route zero|, signed-recentred")
    ang_rows = {}
    creep = []
    for b in N.LADDER:
        c = zeros[b]["c"]
        for r in eng[b]:
            if not (1.5 <= r["v"] < 3.0):
                continue
            if not np.isfinite(r.get("a_mean", np.nan)):
                continue
            q = dict(r)
            q["adev"] = abs(r["a_mean"] - c)
            creep.append(q)
    print(f"  pooled creep-engaged windows with signed angle: {len(creep)}"
          f"  ({len({r['build'] for r in creep})} builds, {len({r[G.EPKEY] for r in creep})} eps)\n")
    print(f"  {'|ang| deg':<10}{'win':>7}{'ep':>6}{'builds':>8}  " +
          "".join(f"{('e_'+k):>26}" for k in ("18-22", "6-9", "24-28")) +
          f"{'rate_lp':>10}")
    for i, name in enumerate(AN):
        lo_, hi_ = AB[i]
        sub = [r for r in creep if lo_ <= r["adev"] < hi_]
        row = {"n": len(sub), "nbuild": len({r["build"] for r in sub})}
        s = f"  {name:<10}{len(sub):>7}{len({r[G.EPKEY] for r in sub}):>6}{row['nbuild']:>8}  "
        for k in ("18-22", "6-9", "24-28"):
            m, l, h, n, ne = med_ci(sub, "e_" + k)
            row[k] = dict(med=m, lo=l, hi=h, nwin=n, nep=ne)
            s += f"{m:>10.0f} [{l:>6.0f},{h:>6.0f}]" if np.isfinite(m) else f"{'--':>26}"
        rl = float(np.median([r["rate_lp"] for r in sub])) if sub else np.nan
        row["rate_lp"] = rl
        ang_rows[name] = row
        print(s + (f"{rl:>10.1f}" if np.isfinite(rl) else f"{'--':>10}"))
    res["angle"]["creep"] = ang_rows

    # the same axis with the RAW |ang| the corpus used, as a second method
    N.hdr("ss2b  same, but on the corpus's own mean|ang| (no re-centring) -- second method")
    for i, name in enumerate(AN):
        lo_, hi_ = AB[i]
        sub = [r for r in creep if lo_ <= r["ang"] < hi_]
        if len(sub) < 8:
            print(f"  {name:<10}{len(sub):>7}   -- underpowered")
            continue
        m18 = float(np.median([r["e_18-22"] for r in sub]))
        m69 = float(np.median([r["e_6-9"] for r in sub]))
        print(f"  {name:<10}{len(sub):>7}   e_18-22 {m18:>8.0f}   e_6-9 {m69:>8.0f}")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
