#!/usr/bin/env python3
r"""V89 flight -- H2 read as a BAND CONTRAST, because the two arms are NOT exposure-matched.

🛑 THE CONFOUND THIS FILE EXISTS FOR.  `v89_e2` found the matching VALIDITY check failing:
   `e_1-4` (driver input) V89 pooled / V88 = 0.803 [0.636, 1.062], and the UPSTREAM openpilot
   request is roughly a third of route 73's (median |0x0E4| 224 / 219 ct vs 601).  Routes 75/76 are
   mostly straight highway; route 73 carried far more cornering.  **The whole column spectrum is
   being driven less hard on the V89 arm**, so a bare `e_6-9` ratio below 1.00 is exactly what a
   quieter drive produces with no firmware effect at all.

   The corpus's own answer to this is `v89_c2_powered_discriminator`'s BAND CONTRAST: the ratchet
   band's log-ratio MINUS a control band's log-ratio, both computed on the SAME resampled episodes
   so the draws are paired and the difference's CI is honest.  A uniform quieting cancels; a
   band-specific firmware effect does not.

CONTROL BANDS, all pre-declared elsewhere in the kit:
    32-38 Hz  the negative control `compare_v75_v76_v80_grind.NEGCTRL`
     1-4  Hz  the driver-input / exposure band
    18-22 Hz  grind #1 -- a second, independent "is this band-specific" reference

🛑 The contrast is the SAME estimator as the ratio (`boot_cellwise`'s stratified weighted mean of
   per-cell log-ratios); only the paired differencing is new, and its split-half null is computed
   the same way and printed first.
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
import pickle
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))

import _grind2_lib as G          # noqa: E402
import compare_v75_v76_v80_grind as M   # noqa: E402  -- installs BANDS_EXT
from v89_e2_h2h3 import BUILDS, ARMS, eng, order_hit, nblk, census  # noqa: E402

RNG = np.random.default_rng(89_3311)
PKL = ROOT / "_scratch/cache/r75" / "records_v89_score.pkl"
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e3_contrast.json"
KEYS = ["e_1-4", "e_6-9", "e_10-16", "e_18-22", "e_26-31", "e_32-38", "e_40-49"]
OUT = {}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def strat_multi(epA, epB, keys, min_ep=3, min_win=8):
    """`boot_cellwise`'s stratified weighted mean of per-cell log-ratios, for SEVERAL keys at once
    over ONE cell partition -- so the returned log-ratios are PAIRED and differencing them is legal.
    🛑 Cell admission uses the SAME cells for every key (the `e_6-9` admission rule), otherwise a
    contrast would be taken between two different window sets -- the `v89_a1` artefact."""
    A, B = {}, {}
    for e in epA:
        for r in e:
            A.setdefault(r["cell"], []).append(r)
    for e in epB:
        for r in e:
            B.setdefault(r["cell"], []).append(r)
    num = {k: 0.0 for k in keys}
    den = 0.0
    ncell = 0
    for c in sorted(set(A) & set(B)):
        ra, rb = A[c], B[c]
        nea = len({r[G.EPKEY] for r in ra})
        neb = len({r[G.EPKEY] for r in rb})
        if nea < min_ep or neb < min_ep or len(ra) < min_win or len(rb) < min_win:
            continue
        stats = {}
        ok = True
        for k in keys:
            sa, sb = G.cell_stat(ra, k), G.cell_stat(rb, k)
            if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 0 or sb <= 0:
                ok = False
                break
            stats[k] = np.log(sa / sb)
        if not ok:
            continue
        w = 1.0 / (1.0 / nea + 1.0 / neb)
        for k in keys:
            num[k] += w * stats[k]
        den += w
        ncell += 1
    if den == 0:
        return {k: np.nan for k in keys}, 0
    return {k: num[k] / den for k in keys}, ncell


def boot_contrast(A, B, keys, nboot=2000):
    """Paired bootstrap over EPISODES; returns per-key log-ratio draws on identical resamples."""
    epA, epB = G.episodes(A), G.episodes(B)
    pt, nc = strat_multi(epA, epB, keys)
    D = {k: np.full(nboot, np.nan) for k in keys}
    for i in range(nboot):
        ia = RNG.integers(0, len(epA), len(epA))
        ib = RNG.integers(0, len(epB), len(epB))
        v, _ = strat_multi([epA[j] for j in ia], [epB[j] for j in ib], keys)
        for k in keys:
            D[k][i] = v[k]
    return pt, D, nc, len(epA), len(epB)


def report(pt, D, nc, na, nb, subject, controls):
    print(f"    cells {nc}   episodes {na}/{nb}")
    print(f"    {'band':10s} {'ratio':>7s} {'[  2.5 %,  97.5 %]':>22s}")
    for k in KEYS:
        if not np.isfinite(pt.get(k, np.nan)):
            continue
        lo, hi = np.nanpercentile(D[k], [2.5, 97.5])
        mark = " <- SUBJECT" if k == subject else (" (control)" if k in controls else "")
        print(f"    {k:10s} {np.exp(pt[k]):7.3f} [{np.exp(lo):7.3f}, {np.exp(hi):7.3f}]{mark}")
    res = {k: dict(ratio=float(np.exp(pt[k])),
                   lo=float(np.exp(np.nanpercentile(D[k], 2.5))),
                   hi=float(np.exp(np.nanpercentile(D[k], 97.5))))
           for k in KEYS if np.isfinite(pt.get(k, np.nan))}
    print(f"\n    {'BAND CONTRAST vs':22s} {'ratio-of-ratios':>16s} {'[  2.5 %,  97.5 %]':>22s}"
          "   excludes 1.00?")
    for c in controls:
        if not (np.isfinite(pt.get(subject, np.nan)) and np.isfinite(pt.get(c, np.nan))):
            continue
        d = D[subject] - D[c]
        p, lo, hi = np.exp(pt[subject] - pt[c]), *np.exp(np.nanpercentile(d, [2.5, 97.5]))
        print(f"    {c:22s} {p:16.3f} [{lo:7.3f}, {hi:7.3f}]   "
              f"{'YES' if (lo > 1) or (hi < 1) else 'no'}")
        res[f"contrast_{subject}_vs_{c}"] = dict(ratio=float(p), lo=float(lo), hi=float(hi))
    return res


def split_half_contrast(recs, subject, control, nrep=300):
    """The arm's OWN noise floor on the CONTRAST -- halve its episodes and difference the bands."""
    eps = G.episodes(recs)
    out = []
    for _ in range(nrep):
        idx = RNG.permutation(len(eps))
        h = len(eps) // 2
        v, _ = strat_multi([eps[i] for i in idx[:h]], [eps[i] for i in idx[h:]],
                           [subject, control])
        if np.isfinite(v[subject]) and np.isfinite(v[control]):
            out.append(v[subject] - v[control])
    if not out:
        return np.nan, np.nan, np.nan
    o = np.array(out)
    return (float(np.exp(np.median(o))), float(np.exp(np.percentile(o, 2.5))),
            float(np.exp(np.percentile(o, 97.5))))


# =================================================================================================
if __name__ == "__main__":
    R = {k: v for k, v in pickle.load(open(PKL, "rb")).items() if not k.startswith("__")}
    E = {b: eng(R[b], b) for b in ARMS}
    V = {b: [r for r in E[b] if not order_hit(r["f_6-9"], r["v"])] for b in ARMS}

    hdr("★ THE EXPOSURE CONFOUND, STATED FIRST -- routes 75/76 are a QUIETER drive than route 73")
    for b in ARMS:
        rs = E[b]
        print(f"    {b:10s} n={len(rs):4d}  median |0x0E4 req| {np.median(G.col(rs,'e4')):7.1f}   "
              f"sustained |tq| {np.median(G.col(rs,'eff')):7.1f}   |rate| {np.median(G.col(rs,'rate')):6.2f}"
              f"   e_1-4 {np.median(G.col(rs,'e_1-4')):7.1f}   |ang| {np.median(G.col(rs,'ang')):6.1f}")
    print("    ⇒ every EXCITATION covariate is lower on the V89 arm.  A bare band ratio below 1.00")
    print("      is therefore uninterpretable on its own; the CONTRAST below is the instrument.")

    for tag, S in (("RAW (no wheel-order veto)", E), ("WHEEL-ORDER VETOED (orders 1-6, 0.8 Hz)", V)):
        hdr(f"H2 AS A BAND CONTRAST -- {tag}")
        for b in ARMS:
            census(S[b], b)
        sub("CONTROL FIRST -- each arm's own split-half null ON THE CONTRAST (6-9 minus 32-38)")
        for b in ARMS:
            md, lo, hi = split_half_contrast(S[b], "e_6-9", "e_32-38")
            OUT[f"{tag}/split_half_contrast/{b}"] = [md, lo, hi]
            print(f"    {b:10s} {md:6.3f} [{lo:6.3f}, {hi:6.3f}]")
        for a in ("V89/r75", "V89/r76", "POOLED"):
            A = S["V89/r75"] + S["V89/r76"] if a == "POOLED" else S[a]
            sub(f"{a} / V88/r73")
            pt, D, nc, na, nb = boot_contrast(A, S["V88/r73"], KEYS)
            OUT[f"{tag}/{a}"] = report(pt, D, nc, na, nb, "e_6-9",
                                       ["e_32-38", "e_1-4", "e_18-22"])

    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
