#!/usr/bin/env python3
"""PRIORITY 2 -- score V73 (route 5a) against the corpus, on the kit's standard battery.

Bands, estimator, windowing, episode bootstrap and split-half null are `_grind2_lib` UNCHANGED, so
every ratio here is computed with the identical instrument as every prior route.

  grind #1       18-22 Hz, engaged, creep, near-zero angle
  micro ratchet   6-9  Hz, all speeds
  grind #2       40-49 Hz
  control        24-28 Hz  (pre-declared negative control)

🛑 MODE IS NOT AN INDEPENDENT COVARIATE ON THIS ROUTE. Measured: mode 10 is 97.59% engaged, mode 8 is
3.50% engaged; mode 8 ENGAGED is 9.2 s and mode 10 MANUAL is 18.7 s, both far under any usable
threshold. So "mode 8 vs mode 10" IS "manual vs engaged" plus a 1-2 s hysteresis band. Both splits
are reported; the mode split is reported as CONFOUNDED, never as a second factor.

🛑 SPEED-MATCHED. Every cross-route ratio is stratified on `_grind2_lib`'s (eng, v, eff, rate) cell,
so a moving wheel order (0.489*v Hz) cannot manufacture a route effect. Per-cell exposure printed.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r5a_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(7331)
KEYS = [("e_18-22", "GRIND #1   18-22 Hz"), ("e_6-9", "MICRO RATCHET 6-9 Hz"),
        ("e_40-49", "GRIND #2   40-49 Hz"), ("e_24-28", "CONTROL    24-28 Hz")]
CMP = ["V72/r59", "V71C/r58", "V71B/r54", "V70/r50", "V69/r4f", "V67/r47", "V62/r37", "V59/r2c"]
out = {}

R = L.records()
print("builds loaded:", ", ".join(f"{b}({len(v)})" for b, v in R.items()))

v73 = L.R59.driving(R["V73/r5a"], "V73/r5a") if hasattr(L.R59, "driving") else R["V73/r5a"]
v73 = [r for r in v73 if r["seg"] != 17]
print(f"\nV73/r5a: {len(v73)} windows after dropping the parked segment 17")

# ------------------------------------------------------------------ 1. mode / engagement --------
L.hdr("1. THE MODE CHANNEL -- and why it is CONFOUNDED with engagement")
for m in (8.0, 10.0):
    for e in (1, 0):
        rs = [r for r in v73 if r.get("mode") == m and r["eng"] == e and r.get("mode_pure", 1) > .9]
        print(f"  mode {int(m):2d} {'engaged' if e else 'manual ':>7s}: {len(rs):5d} windows  "
              f"({len(rs) * 1.28:7.1f} s at hop 128)  "
              f"v median {np.median([r['v'] for r in rs]) if rs else float('nan'):6.2f} m/s")
print("\n⇒ the two off-diagonal cells are the only way to separate mode from engagement, and they")
print("  are tiny. Any 'mode effect' below is an ENGAGEMENT effect. Reported, not interpreted.")

# ------------------------------------------------------------------ 2. band scorecard ------------
L.hdr("2. V73 BAND SCORECARD -- medians with episode CIs, engaged vs manual, and by mode")
CREEP = (0.5, 4.0)


def sub(rs, eng=None, mode=None, creep=False, angmax=None):
    o = rs
    if eng is not None:
        o = [r for r in o if r["eng"] == eng]
    if mode is not None:
        o = [r for r in o if r.get("mode") == mode and r.get("mode_pure", 1) > 0.9]
    if creep:
        o = [r for r in o if CREEP[0] <= r["v"] < CREEP[1]]
    if angmax is not None:
        o = [r for r in o if r["ang"] < angmax]
    return o


ARMS = [("engaged, ALL speed", dict(eng=1)),
        ("engaged, CREEP 0.5-4", dict(eng=1, creep=True)),
        ("engaged, CREEP + |ang|<3", dict(eng=1, creep=True, angmax=3.0)),
        ("manual,  ALL speed", dict(eng=0)),
        ("manual,  CREEP 0.5-4", dict(eng=0, creep=True)),
        ("mode 10 engaged", dict(eng=1, mode=10.0)),
        ("mode 10 manual  (CONFOUNDED, n small)", dict(eng=0, mode=10.0)),
        ("mode  8 manual", dict(eng=0, mode=8.0)),
        ("mode  8 engaged (CONFOUNDED, n small)", dict(eng=1, mode=8.0))]
sc = {}
for lab, kw in ARMS:
    rs = sub(v73, **kw)
    print(f"\n  {lab}:  n={len(rs)} windows ({len(rs) * 1.28:.0f} s at hop 128), "
          f"{len({r['ep'] for r in rs})} episodes")
    if len(rs) < 12:
        print("     UNPOWERED (<12 windows) -- reported as EXPOSURE, not as a null")
        continue
    for k, kl in KEYS:
        p, lo, hi = G.boot_median_ci(rs, k, RNG, nboot=1200)
        print(f"     {kl:22s} median {p:9.1f}  [{lo:8.1f}, {hi:8.1f}]")
        sc[(lab, k)] = (p, lo, hi, len(rs))
out["scorecard"] = {f"{a}|{b}": list(v) for (a, b), v in sc.items()}

# ------------------------------------------------------------------ 3. vs corpus -----------------
L.hdr("3. V73 vs THE CORPUS -- stratified log-ratio, episode-resampled, split-half null FIRST")
print("ratio > 1 means V73 is WORSE (more band energy). Cells are `_grind2_lib`'s "
      "(eng, v, eff, rate).\n")
res = {}
for k, kl in KEYS:
    print(f"--- {kl} ---")
    nullp, nlo, nhi = G.split_half_null(v73, k, RNG, nrep=250)
    print(f"    V73's OWN split-half null: [{nlo:.3f}, {nhi:.3f}]  (median {nullp:.3f})")
    print(f"    {'vs build':>12s} {'ratio':>7s} {'95% CI':>18s} {'cells':>6s} {'epA':>5s} "
          f"{'epB':>5s}  clears?")
    for b in CMP:
        if b not in R:
            continue
        other = [r for r in R[b]]
        pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(v73, other, k, RNG, nboot=800)
        if not np.isfinite(pt):
            print(f"    {b:>12s}      -- no shared cell (UNPOWERED, not null)")
            continue
        cl = "YES" if (lo > nhi or hi < nlo) else "no"
        print(f"    {b:>12s} {pt:7.3f} [{lo:7.3f}, {hi:7.3f}] {nc:6d} {na:5d} {nb:5d}   {cl}")
        res[(k, b)] = (pt, lo, hi, nc, cl)
    print()
out["vs_corpus"] = {f"{a}|{b}": list(v) for (a, b), v in res.items()}

# ------------------------------------------------------------------ 4. LEVER D -------------------
L.hdr("4. ★ DID LEVER D (friction x1.5 @0xD2A44 + clamp 0xC407E 511->850) MOVE GRIND #1?")
print("V73 = V72 byte-identical + Lever D + Lever E. Lever E had ZERO exposure (0/104,061 frames).")
print("⇒ V73 vs V72 on route 59 IS the Lever D contrast, cleanly, with the rate lane held fixed.")
print("   Lever D's LERP half is mode-10 indexed and mode 10 covered 92.35% of the grind-#1")
print("   regime, so the lever was genuinely in force.\n")
if "V72/r59" in R:
    v72 = R["V72/r59"]
    for k, kl in KEYS:
        for lab, kw in (("ALL engaged", dict(eng=1)), ("engaged CREEP", dict(eng=1, creep=True)),
                        ("engaged CREEP |ang|<3", dict(eng=1, creep=True, angmax=3.0))):
            a, b = sub(v73, **kw), sub(v72, **kw)
            if len(a) < 12 or len(b) < 12:
                print(f"  {kl:22s} {lab:24s} UNPOWERED (nA={len(a)}, nB={len(b)})")
                continue
            pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(a, b, k, RNG, nboot=800,
                                                             min_ep=2, min_win=4)
            _, nlo, nhi = G.split_half_null(b, k, RNG, nrep=200, min_ep=2, min_win=4)
            if not np.isfinite(pt):
                print(f"  {kl:22s} {lab:24s} no shared cell -- UNPOWERED")
                continue
            cl = "CLEARS" if (lo > nhi or hi < nlo) else "inside null"
            print(f"  {kl:22s} {lab:24s} V73/V72 {pt:6.3f} [{lo:6.3f}, {hi:6.3f}] "
                  f"null [{nlo:5.3f}, {nhi:5.3f}] {nc:2d} cells  {cl}")
            out.setdefault("leverD", {})[f"{k}|{lab}"] = [pt, lo, hi, nlo, nhi, nc, cl]

with open(ROOT / "_scratch/out/_r5a_score.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5a_score.json")
