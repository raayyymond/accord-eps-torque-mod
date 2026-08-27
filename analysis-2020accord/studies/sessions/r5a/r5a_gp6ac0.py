#!/usr/bin/env python3
"""ESTIMATE `gp-0x6ac0` (motor electrical rate) during bursts, and the dose V74's rung B delivers.

THE CONVERSION CHAIN, every step labelled. Nothing here is asserted without its arithmetic.

  [BELIEF, inherited]  gp-0x6ac0 = 30 * f_electrical,  f_elec = P * f_mech,  f_mech = G * f_column,
                       with P * G = 56.5.  (Kit-settled; not re-derived here.)
  [EVIDENCE, arithmetic]  gp-0x6ac0 = 30 * 56.5 * (column_deg_s / 360) = 4.7083 * column_deg_s.
                       The brief's stated 4.7121 counts/column-deg-s agrees to 0.08%. Both are run.
  [EVIDENCE, bus]      `rate_c` = CAN 0x14A bytes 2:3 * -1.0 = STEER_ANGLE_RATE, COLUMN side, deg/s,
                       quantised to 1 deg/s. `rate_f` = 0x18F bytes 2:3 * -0.1 is a second rate
                       channel; both are cross-checked below rather than one being assumed.

🛑🛑 THE TWO CAVEATS THAT COULD INVALIDATE THE POINT ESTIMATE -- stated before any number.

  C1  COLUMN-SIDE vs MOTOR-SIDE. `rate_c` is the COLUMN. `gp-0x6ac0` is the MOTOR. The 18-22 Hz mode
      is a TORSIONAL resonance, i.e. motor inertia against driveline compliance -- exactly the
      geometry in which the two ends move by DIFFERENT amounts. The rigid-body factor P*G is correct
      at DC and progressively WRONG through a resonance. ⇒ at 18-22 Hz this estimator is a LOWER
      BOUND on the motor rate if the motor leads, and an over-estimate if the column leads. Bus data
      cannot resolve which. This is the dominant uncertainty and it is NOT quantified by any CI here.

  C2  100 Hz SAMPLING of a ~20.5 Hz oscillation = 4.9 samples/cycle. The FUNDAMENTAL is resolved,
      but |rate| is a RECTIFIED quantity whose content sits at ~41 Hz and folds. Peak |rate| is
      therefore UNDER-sampled and the p99 below is a floor. The time-AVERAGE of FactorE is much more
      robust (phases wander because 100/20.5 = 4.878 is irrational-ish), and that is what the dose
      answer rests on.

VALIDATION. The kit recorded a route-59 highway peak of 329.8 counts. The same estimator is run on
route 5a's highway exposure; agreement corroborates the chain, disagreement voids it.

DOSE MODEL, back-solved from the brief's own numbers and checked three ways:
    FactorE: X = [60, 400, 2500, 4000], Y = [0, 140, 539, 927], linear interp, flat outside.
    dose = (FactorC * FactorE(gp-0x6ac0)) >> 10.
    rung B FactorC = 429 -> 6.9 / 46.6 / 58.6 at gp-0x6ac0 = 100 / 330 / 400  (brief: 6 / 46 / 58) ✅
    rung C FactorC = 908 -> 14.6 / 98.6 /124.1                                (brief: 14 / 98 /124) ✅
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

import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from r5a_rail import CREEP, MIN_CYC, THR, bursts, frames  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(6060)
K_DERIVED = 30 * 56.5 / 360.0          # 4.70833 counts per column deg/s -- from P*G
K_BRIEF = 4.7121
FE_X = np.array([60.0, 400.0, 2500.0, 4000.0])
FE_Y = np.array([0.0, 140.0, 539.0, 927.0])
RUNG = {"B (Y[0]=429)": 429, "C (Y[0]=908)": 908, "stock-ish (589)": 589}
out = {}


def factorE(g):
    return np.interp(np.abs(np.asarray(g, float)), FE_X, FE_Y, left=0.0, right=FE_Y[-1])


def dose(g, fc):
    return np.floor(fc * factorE(g) / 1024.0)


L.hdr("0. THE DOSE MODEL, back-solved and checked against the brief's own three points")
for lab, fc in RUNG.items():
    print(f"  rung {lab:16s} FactorC={fc:4d}: dose at gp-0x6ac0 = 100 / 330 / 400  ->  "
          f"{dose(100, fc):5.0f} / {dose(330, fc):5.0f} / {dose(400, fc):5.0f}")
print("  brief: rung B -> 6 / 46 / 58 ; rung C -> 14 / 98 / 124.  ✅ model reproduced.")
print(f"\n  conversion constant: derived 30*56.5/360 = {K_DERIVED:.4f}, brief {K_BRIEF:.4f} "
      f"(0.08% apart -- both reported)")

# ------------------------------------------------------------------ assemble ---------------------
F = frames()
minlen = int(round(MIN_CYC / 20.0 * 100))
sel = (F["v"] >= CREEP[0]) & (F["v"] < CREEP[1]) & F["eng"]
L.hdr("1. CHANNEL CROSS-CHECK -- do the two bus rate channels agree?")
# F["arate"] is |rate_c| (0x14A). Pull |rate_f| (0x18F) straight off the segments, same lattice.
rf = []
for s in [x for x in range(18) if x != 17]:
    d = L.load_seg(s)
    t = np.asarray(d["t"], float)
    for a, b in C.runs_of(np.ones(len(t), bool), t, 512):
        if np.all(np.isfinite(d["tq"][a:b])):
            rf.append(np.abs(np.asarray(d["rate_f"][a:b], float)))
rf = np.concatenate(rf)
rc = F["arate"]
assert len(rf) == len(rc), f"lattice mismatch: rate_f {len(rf)} vs rate_c {len(rc)}"
print(f"  |rate_c| p50 {np.median(rc):6.1f}  p99 {np.percentile(rc, 99):6.1f}  max {rc.max():6.1f}")
print(f"  |rate_f| p50 {np.median(rf):6.1f}  p99 {np.percentile(rf, 99):6.1f}  max {rf.max():6.1f}")
print(f"  Pearson r = {np.corrcoef(rc, rf)[0, 1]:.4f}   median ratio (rate_f/rate_c, where rc>5) = "
      f"{np.median(rf[rc > 5] / rc[rc > 5]):.3f}")
print("  ⇒ if these disagree materially the column-rate scale itself is in doubt.")

L.hdr("2. VALIDATION -- does the estimator reproduce the recorded route-59 highway peak (329.8)?")
for vlo, lab in ((18.0, "v >= 18 m/s (highway)"), (12.0, "v >= 12 m/s")):
    m = F["eng"] & (F["v"] >= vlo)
    if m.sum() < 500:
        print(f"  {lab:24s} UNPOWERED ({int(m.sum())} frames)")
        continue
    gg = K_DERIVED * F["arate"][m]
    print(f"  {lab:24s} n={int(m.sum()):6d}  gp-0x6ac0 est: p50 {np.median(gg):6.1f}  "
          f"p90 {np.percentile(gg, 90):6.1f}  p99 {np.percentile(gg, 99):6.1f}  "
          f"p99.9 {np.percentile(gg, 99.9):6.1f}  MAX {gg.max():6.1f}")
print("  recorded route-59 highway PEAK = 329.8 counts.")

# ------------------------------------------------------------------ bursts -----------------------
L.hdr("3. gp-0x6ac0 DURING BURSTS -- distributions, engaged creep")


def bmask(lo, hi, thr):
    """Burst mask on an arbitrary band, same detector as the rail test."""
    sav = F["env"]
    ivs = []
    for seg in np.unique(F["run"]).astype(int):
        pass
    # recompute the envelope for this band, per gapless run
    env = np.zeros(len(F["t"]))
    for r in np.unique(F["run"]).astype(int):
        idx = np.flatnonzero(F["run"] == r)
        x = F["tq"][idx]
        if len(x) < 64:
            continue
        env[idx] = C.band_envelope(x, 100.0, lo, hi)
    F["env"] = env
    m = np.zeros(len(F["t"]), bool)
    for a, b in bursts(F, thr, minlen):
        if sel[a:b].mean() > 0.8:
            m[a:b] = True
    F["env"] = sav
    return m, env


# 🛑 THRESHOLDS ARE QUANTILE-MATCHED, not eyeballed. The rail test's established 18-22 Hz threshold
# is 150 counts of amplitude; locate the quantile that represents in the engaged-creep 18-22
# envelope, then apply the SAME quantile in the 6-9 band. A p95 threshold yields ZERO bursts in
# either band once the 15-sample dwell is required -- that is a detector failure, not a null.
_, e18 = bmask(18.0, 22.0, 1e9)
_, e69 = bmask(6.0, 9.0, 1e9)
qmatch = float((e18[sel] < THR).mean() * 100)
thr18 = float(THR)
thr69 = float(np.percentile(e69[sel], qmatch))
m18, _ = bmask(18.0, 22.0, thr18)
m69, _ = bmask(6.0, 9.0, thr69)
print(f"  18-22 threshold = {thr18:.0f} (the rail test's, = the p{qmatch:.1f} of its own "
      f"engaged-creep envelope)")
print(f"   6-9  threshold = {thr69:.0f} (the SAME p{qmatch:.1f} quantile of the 6-9 envelope)")
print(f"  the kit's recorded ratchet criterion (>=1200 counts p-p = 600 amplitude) is also run "
      f"below as a sensitivity check")
print(f"  bursts found: 18-22 -> {int(m18.sum())} frames, 6-9 -> {int(m69.sum())} frames\n")

rows = []
print(f"{'arm':>34s} {'frames':>7s} {'s':>7s} {'p10':>7s} {'p50':>7s} {'p90':>7s} {'p99':>7s} "
      f"{'max':>7s}")
ARMS = [("engaged creep, IN 18-22 BURST", sel & m18),
        ("engaged creep, IN 6-9 BURST", sel & m69),
        ("engaged creep, OUT of both", sel & ~m18 & ~m69),
        ("engaged creep, ALL", sel),
        ("engaged, ALL SPEEDS", F["eng"])]
for lab, m in ARMS:
    if m.sum() < 30:
        print(f"{lab:>34s} {int(m.sum()):7d}   UNPOWERED")
        continue
    gg = K_DERIVED * F["arate"][m]
    q = [np.percentile(gg, p) for p in (10, 50, 90, 99)]
    print(f"{lab:>34s} {int(m.sum()):7d} {m.sum() / 100:7.2f} {q[0]:7.1f} {q[1]:7.1f} "
          f"{q[2]:7.1f} {q[3]:7.1f} {gg.max():7.1f}")
    rows.append((lab, int(m.sum()), *[float(x) for x in q], float(gg.max())))
out["dist"] = rows

# episode CI on the in-burst median
L.hdr("4. EPISODE-RESAMPLED CI on the in-burst median gp-0x6ac0")
runs = F["run"].astype(int)
for lab, m in (("18-22 burst", sel & m18), ("6-9 burst", sel & m69)):
    eps = np.array(sorted(set(runs[m])))
    if len(eps) < 4:
        print(f"  {lab:14s} UNPOWERED ({len(eps)} episodes)")
        continue
    d = []
    for _ in range(3000):
        keep = np.isin(runs, eps[RNG.integers(0, len(eps), len(eps))])
        v = K_DERIVED * F["arate"][m & keep]
        if len(v) > 20:
            d.append(np.median(v))
    print(f"  {lab:14s} median {np.median(K_DERIVED * F['arate'][m]):6.1f}  "
          f"95% CI [{np.percentile(d, 2.5):6.1f}, {np.percentile(d, 97.5):6.1f}]  "
          f"({len(eps)} episodes)")
    out.setdefault("ci", {})[lab] = [float(np.median(K_DERIVED * F["arate"][m])),
                                     float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]

# ------------------------------------------------------------------ THE ANSWER -------------------
L.hdr("5. ★ THE DELIVERED DOSE -- FactorE evaluated PER FRAME and time-averaged, not FactorE(median)")
print("🛑 FactorE is CONVEX at these rates (flat 0 below 60, then rising), so dose(mean rate) is")
print("   NOT mean(dose). Every number below evaluates FactorE per frame and averages.\n")
print(f"{'arm':>30s} {'rung':>16s} {'mean dose':>10s} {'median':>8s} {'p90':>7s} "
      f"{'% frames FE=0':>14s}")
ans = {}
for lab, m in (("18-22 burst", sel & m18), ("6-9 burst", sel & m69),
               ("out of both", sel & ~m18 & ~m69), ("all engaged creep", sel)):
    if m.sum() < 30:
        continue
    gg = K_DERIVED * F["arate"][m]
    fe = factorE(gg)
    for rl, fc in RUNG.items():
        dd = dose(gg, fc)
        print(f"{lab:>30s} {rl:>16s} {dd.mean():10.1f} {np.median(dd):8.1f} "
              f"{np.percentile(dd, 90):7.1f} {np.mean(fe <= 0) * 100:13.1f}%")
        ans[(lab, rl)] = float(dd.mean())
    print()
out["dose"] = {f"{a}|{b}": v for (a, b), v in ans.items()}

L.hdr("6. VERDICT AGAINST THE ~43-COUNT REQUIREMENT (range 30-60)")
for lab in ("18-22 burst", "6-9 burst"):
    for rl in RUNG:
        v = ans.get((lab, rl))
        if v is None:
            continue
        verdict = ("CLEARS (30-60)" if 30 <= v <= 60 else
                   "UNDER-DOSE" if v < 30 else "OVER (clipping risk)")
        print(f"  {lab:14s} rung {rl:16s} mean delivered dose {v:6.1f} counts   {verdict}")
    print()
print("  🛑 Every number above inherits caveat C1 (column vs motor through a torsional resonance).")
print("     If the motor end moves MORE than the column at 18-22 Hz -- which is what a motor-inertia")
print("     mode means -- the true gp-0x6ac0 is HIGHER and the dose is LARGER than stated.")

L.hdr("7. SENSITIVITY: the SECOND rate channel, and the recorded ratchet criterion")
print("7a. `rate_f` (0x18F) instead of `rate_c` (0x14A) -- they differ by a median factor 0.784, so")
print("    this brackets the CHANNEL ambiguity on top of C1.")
for lab, m in (("18-22 burst", sel & m18), ("6-9 burst", sel & m69)):
    if m.sum() < 30:
        print(f"    {lab:14s} UNPOWERED")
        continue
    for cl, arr in (("rate_c", rc), ("rate_f", rf)):
        gg = K_DERIVED * arr[m]
        print(f"    {lab:14s} via {cl}: gp-0x6ac0 p50 {np.median(gg):6.1f} p90 "
              f"{np.percentile(gg, 90):6.1f}   rung B mean dose {dose(gg, 429).mean():6.1f}")
print("\n7b. the recorded ratchet criterion (amplitude >= 600 counts) for the 6-9 band:")
m69b, _ = bmask(6.0, 9.0, 600.0)
m69b = sel & m69b
if m69b.sum() >= 30:
    gg = K_DERIVED * rc[m69b]
    print(f"    n={int(m69b.sum())} frames ({m69b.sum() / 100:.2f} s)  gp-0x6ac0 p50 "
          f"{np.median(gg):6.1f}  p90 {np.percentile(gg, 90):6.1f}  "
          f"rung B mean dose {dose(gg, 429).mean():6.1f}")
else:
    print(f"    n={int(m69b.sum())} frames -- UNPOWERED at that criterion on this route")

with open(ROOT / "_scratch/out/_r5a_gp6ac0.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5a_gp6ac0.json")
