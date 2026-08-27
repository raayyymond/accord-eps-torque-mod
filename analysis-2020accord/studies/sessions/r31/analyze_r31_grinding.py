#!/usr/bin/env python3
"""V61 route `31` -- QUESTIONS B/C/D/E/G: the 18-26 Hz grinding line by arm.

🛑🛑 READ THIS BEFORE QUOTING ANY FREQUENCY FROM THIS SCRIPT. Its headline column is a STRICT 18-26 Hz
argmax, and on V61 that is a KNOWN ARTIFACT: the mode moved to ~18.3 Hz engaged and ~17.1 Hz manual, so
the argmax PINS TO THE 18.0 Hz BAND EDGE and reports sd 0.00. It looks like an extremely tight mode and
it is a truncation. The file is kept because `studies/sessions/r31/analyze_r31_spectra.py` exists to demonstrate exactly this
failure and needs the artifact to demonstrate it against.
⇒ For frequencies use `studies/sessions/r31/analyze_r31_spectra.py` (free 12-30 Hz argmax). For amplitudes use
  `studies/sessions/r31/analyze_r31_matched.py` / `studies/sessions/r31/analyze_r31_standstill.py`, which are free-band. Both are safe to quote.
⚠ Its AMPLITUDE columns understate V61 by 20-29% for the same reason -- the strict band clips the peak.

⚠ A second known limitation of this file, found 2026-07-31: its manual arms use a `|v| >= 0.3 m/s`
"moving" gate, which DROPS the loudest manual windows. The manual phenomenon on V61 lives at
|v| = 0.00-0.6 m/s with the wheel cranked (effort 2200-3300). With the gate removed the manual arm goes
from "median prominence 5.3x, mostly floor" to "median 317x, envelope p99 median 2495".
`studies/sessions/r31/analyze_r31_standstill.py` is the arm that gets this right.

Arms (gear is the only direction signal; vEgo is a magnitude on this platform):
    engaged FORWARD   gear==drive  & latActive
    manual  FORWARD   gear==drive  & !latActive
    manual  REVERSE   gear==reverse            (LKAS cannot engage in reverse)

Cross-build comparison runs the SAME pipeline over the route `2c` (V59) and `2b` (V58) caches
rather than quoting docs/STATE.md's recorded numbers -- a recorded number computed by a different
script is not a control.

Usage:  python studies/sessions/r31/analyze_r31_grinding.py
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[3]))
from _r31_common import (BAND, CACHE_2B, CACHE_2C, NFFT, RATCHET, SEGS_2B, SEGS_2C,  # noqa: E402
                         SEGS_31, avg_spectrum, band_envelope, fs_of, load, peak_prom,
                         q_of, sustained, windows)

CUTS = (5, 10, 20, 50)


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


# ------------------------------------------------------------------------------------- arm masks
def arm_mask(d, arm, vmax=5.0, vmin=0.3, hands=None):
    v = np.abs(d["cs_v"])
    m = (v <= vmax) & (v >= vmin)
    lat = d["cc_lat"] > 0.5
    if arm == "eng_fwd":
        m &= (d["cs_gear"] == 2) & lat
    elif arm == "man_fwd":
        m &= (d["cs_gear"] == 2) & ~lat
    elif arm == "man_rev":
        m &= (d["cs_gear"] == 4)
    elif arm == "any_eng":
        m &= lat
    elif arm == "any_man":
        m &= ~lat
    else:
        raise ValueError(arm)
    if hands is not None:
        fs = fs_of(d)
        sus = np.full(len(d["t"]), np.inf)
        if m.any():
            sus[m] = sustained(d["tq"][m], fs)
        m &= (sus <= 200) if hands else (sus > 200)
    return m


def collect(segs, arm, cache=None, pfx="r31s", **kw):
    """All per-window records for an arm, plus the run (episode) count."""
    recs, eps = [], 0
    for s in segs:
        d = load(s, cache, pfx) if cache is not None else load(s)
        m = arm_mask(d, arm, **kw)
        if not m.any():
            continue
        w = windows(d, m)
        for r in w:
            r["seg"] = s
        recs += w
        eps += len({r["run"] for r in w})
    return recs, eps


def summarise(tag, recs, eps):
    if not recs:
        print(f"   {tag:34s}  n=0 windows (no contiguous {NFFT}-sample run)")
        return None
    pr = np.array([r["prom"] for r in recs], float)
    f0 = np.array([r["f0"] for r in recs], float)
    ep = np.array([r["envp99"] for r in recs], float)
    ok = np.isfinite(pr) & np.isfinite(f0)
    pr, f0, ep = pr[ok], f0[ok], ep[ok]
    tight = f0[pr >= 10] if (pr >= 10).any() else f0
    print(f"   {tag:34s}  n={len(pr):3d} win / {eps:2d} ep   prom med {np.median(pr):8.1f}  "
          f"p90 {np.percentile(pr,90):8.1f}  max {pr.max():9.1f}   "
          f"f0 med {np.median(f0):5.2f} sd {f0.std(ddof=1) if len(f0)>1 else 0:5.2f} Hz  "
          f"[prom>=10: sd {tight.std(ddof=1) if len(tight)>1 else 0:5.2f}, n={len(tight)}]   "
          f"envp99 med {np.median(ep):7.1f}")
    print(f"   {'':34s}  presence: " + "  ".join(
        f">{c}x {100*(pr>=c).mean():5.1f}% ({int((pr>=c).sum())})" for c in CUTS))
    return dict(prom=pr, f0=f0, env=ep, n=len(pr), eps=eps)


# ------------------------------------------------------------------------------------------ main
def main():
    hdr("B/C/D OVERVIEW -- the three arms, |v| in [0.3, 5.0] m/s, strict 18-26 Hz band")
    print("   'ep' = independent episodes (contiguous runs) -- windows within one run are NOT "
          "independent.\n   f0 sd is the DISCRIMINATOR: a mode holds frequency, the argmax of a "
          "broadband floor wanders.\n")
    res = {}
    for arm, label in [("eng_fwd", "V61 engaged FORWARD"),
                       ("man_fwd", "V61 manual  FORWARD"),
                       ("man_rev", "V61 manual  REVERSE")]:
        for hands, hl in [(None, "any hands"), (True, "hands-off")]:
            recs, eps = collect(SEGS_31, arm, hands=hands)
            res[(arm, hands)] = summarise(f"{label}  [{hl}]", recs, eps)
        print()

    hdr("C. THE DISCRIMINATOR -- engaged vs manual, the V58 route-2b comparison redone")
    print("   V58 route 2b recorded: engaged prom median 122.7x (f0 sd 1.08 Hz) vs disengaged")
    print("   3.6x with the 'peak' wandering 15-29.9 Hz (sd 2.49 Hz) = the argmax of a floor.")
    print("   Same pipeline, three routes, engaged vs manual at matched creep:\n")
    for cache, pfx, segs, name in [(None, "r31s", SEGS_31, "V61 route 31"),
                                   (CACHE_2C, "r2cs", SEGS_2C, "V59 route 2c"),
                                   (CACHE_2B, "r2bs", SEGS_2B, "V58 route 2b")]:
        print(f"   -- {name} --")
        for arm, lbl in [("any_eng", "engaged (any gear)"), ("any_man", "manual  (any gear)")]:
            recs, eps = collect(segs, arm, cache=cache, pfx=pfx)
            r = summarise(f"{name}  {lbl}", recs, eps)
            res[(name, arm)] = r
        print()

    hdr("D. REVERSE -- manual reverse vs manual forward vs engaged forward")
    print("   Per-arm confounds first, because they decide which way an ambiguous result leans:\n")
    print(f"   {'arm':26s} {'win':>5s} {'ep':>4s} {'med|v|':>7s} {'med|ang|':>9s} "
          f"{'med eff':>8s} {'med|e4|':>8s}")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        recs, eps = collect(SEGS_31, arm)
        if not recs:
            continue
        print(f"   {lbl:26s} {len(recs):5d} {eps:4d} "
              f"{np.median([r['v'] for r in recs]):7.2f} "
              f"{np.median([r['ang'] for r in recs]):9.1f} "
              f"{np.median([r['eff'] for r in recs]):8.0f} "
              f"{np.median([r['e4'] for r in recs]):8.0f}")

    print("\n   -- speed-matched cells (|v| bins of 0.5 m/s, >=2 windows per cell) --")
    print(f"   {'|v| bin':>10s}  " + "  ".join(f"{k:>24s}" for k in
                                               ("engaged FWD", "manual FWD", "manual REV")))
    arms = {k: collect(SEGS_31, k)[0] for k in ("eng_fwd", "man_fwd", "man_rev")}
    for lo in np.arange(0.3, 5.0, 0.5):
        hi = lo + 0.5
        row = []
        for k in ("eng_fwd", "man_fwd", "man_rev"):
            sel = [r for r in arms[k] if lo <= r["v"] < hi and np.isfinite(r["prom"])]
            row.append(f"{np.median([r['prom'] for r in sel]):7.1f}x n={len(sel):<3d}"
                       f" f{np.median([r['f0'] for r in sel]):5.2f}" if len(sel) >= 2
                       else f"{'-':>24s}")
        print(f"   {lo:4.1f}-{hi:4.1f}  " + "  ".join(f"{c:>24s}" for c in row))

    hdr("E. FREQUENCY IDENTITY -- is the manual/reverse line the SAME 20.9 Hz mode?")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        recs, eps = collect(SEGS_31, arm)
        pr = np.array([r["prom"] for r in recs], float)
        f0 = np.array([r["f0"] for r in recs], float)
        qq = np.array([r["Q"] for r in recs], float)
        for cut in CUTS:
            m = np.isfinite(pr) & np.isfinite(f0) & (pr >= cut)
            if m.sum() < 2:
                print(f"   {lbl:20s} prom>{cut:2d}x : n={int(m.sum())}  (too few)")
                continue
            print(f"   {lbl:20s} prom>{cut:2d}x : n={int(m.sum()):3d}  "
                  f"f0 = {f0[m].mean():5.2f} +/- {f0[m].std(ddof=1):4.2f} Hz "
                  f"(median {np.median(f0[m]):5.2f}, range {f0[m].min():5.2f}-{f0[m].max():5.2f})  "
                  f"Q med {np.nanmedian(qq[m]):5.1f}")
        print()

    print("   -- pooled average spectrum per arm (DISJOINT runs averaged, never spliced) --")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        acc, K, nr, f = None, 0, 0, None
        for s in SEGS_31:
            d = load(s)
            m = arm_mask(d, arm)
            if not m.any():
                continue
            ff, P, k, n = avg_spectrum(d, m)
            if P is None:
                continue
            f = ff
            acc = P * k if acc is None else acc + P * k
            K += k
            nr += n
        if acc is None:
            print(f"   {lbl:20s} no windows")
            continue
        P = acc / K
        f0, pr = peak_prom(f, P, *BAND)
        rf0, rpr = peak_prom(f, P, *RATCHET)
        print(f"   {lbl:20s} K={K:3d} runs={nr:2d}   18-26Hz peak {f0:5.2f} Hz prom {pr:7.2f}x "
              f"Q {q_of(f, P, f0):5.1f}   |   6-9Hz peak {rf0:5.2f} Hz prom {rpr:7.2f}x")

    hdr("E2. THE RATCHET BAND (strict 6-9 Hz + presence test) -- did it move?")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        recs = []
        for s in SEGS_31:
            d = load(s)
            m = arm_mask(d, arm)
            if m.any():
                recs += windows(d, m, band=RATCHET)
        if not recs:
            print(f"   {lbl:20s} n=0")
            continue
        pr = np.array([r["prom"] for r in recs], float)
        f0 = np.array([r["f0"] for r in recs], float)
        ok = np.isfinite(pr) & np.isfinite(f0)
        pr, f0 = pr[ok], f0[ok]
        t = f0[pr >= 10]
        print(f"   {lbl:20s} n={len(pr):3d}  prom med {np.median(pr):7.1f} max {pr.max():8.1f}  "
              f"f0 med {np.median(f0):5.2f} sd {f0.std(ddof=1):4.2f}  "
              f"[prom>=10x: n={len(t)}, f0 {np.mean(t) if len(t) else np.nan:5.2f} "
              f"+/- {t.std(ddof=1) if len(t)>1 else 0:4.2f}]  "
              f"presence >10x {100*(pr>=10).mean():5.1f}%")

    hdr("G. TORSION-BAR OSCILLATION AMPLITUDE at engaged creep (18-26 Hz component)")
    print("   band_envelope is the analytic AMPLITUDE A of the band-limited component, so the")
    print("   peak-to-peak swing of the 21 Hz component is 2*A. Per-frame, over the arm mask.\n")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        for hands, hl in [(None, "any hands"), (True, "hands-off")]:
            env = []
            for s in SEGS_31:
                d = load(s)
                fs = fs_of(d)
                m = arm_mask(d, arm, hands=hands)
                for a, b in __import__("_r31_common").runs_of(m, d["t"], NFFT):
                    env.append(band_envelope(d["tq"][a:b], fs))
            if not env:
                print(f"   {lbl:18s} [{hl:9s}] n=0")
                continue
            e = np.concatenate(env)
            print(f"   {lbl:18s} [{hl:9s}] n={len(e):6d} frames   "
                  f"A: med {np.median(e):6.1f} p90 {np.percentile(e,90):6.1f} "
                  f"p99 {np.percentile(e,99):7.1f} max {e.max():7.1f}   "
                  f"=> PEAK-TO-PEAK counts: med {2*np.median(e):6.1f} "
                  f"p90 {2*np.percentile(e,90):6.1f} p99 {2*np.percentile(e,99):7.1f}")


if __name__ == "__main__":
    main()
