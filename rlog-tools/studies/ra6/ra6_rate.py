r"""ROUTE `a6` == V106 -- Q6: THE STEERING-RATE COST, QUANTIFIED.

THE OPERATOR: *"Max steering angle rate during LKAS engagement is limited.  Max LKAS demand moves
the wheel SLOWER than it could before."*

=================================================================================================
THE TWO HYPOTHESES, AND WHY THEY HAVE DIFFERENT FIXES
=================================================================================================
(H-RATE)  a SLEW CEILING -- |rate| is capped at some value regardless of demand.  Signature: the
          demand -> achieved-rate curve PLATEAUS, and the rate histogram PILES UP at the cap.
(H-ACC)   an ACCELERATION PENALTY -- the wheel takes longer to get moving, but a SUSTAINED demand
          eventually reaches the same rate.  Signature: the ONSET transient is slower; the
          SUSTAINED-demand rate is unchanged; no pile-up.

⭐ V106's own arithmetic predicts H-ACC and FORBIDS H-RATE: `gp-0x6b26 = -K * alpha`, and the
   producer's differencer `32*(1 - z^-1)` gives **`H(f=0) = 0` EXACTLY** -- a held command sees
   nothing from this term at ANY multiplier.  That is a proof about the FIRMWARE.  It is NOT a
   proof about the closed loop, because the term still opposes every acceleration on the way to
   the steady state.  **This file tests the prediction rather than assuming it.**

=================================================================================================
🛑 WHAT IS AND IS NOT MEASURABLE
=================================================================================================
* `rate_c` (0x14A, `i16be(d,2) * -1.0`) is TRUE deg/s of STEERING ANGLE -- the operator's own
  quantity.  Directly measured, no reconstruction.
* LKAS demand is `e4tq` (CAN 0x0E4 from openpilot, src 129) -- the COMMAND, upstream of the EPS.
  🛑 It is a demand, not a delivered torque; the EPS's authority curve sits between them.
* 🛑 **THE HARD CONFOUND: the driver's own hands are in every engaged frame.**  A "max demand"
  frame with the driver resisting is not comparable to one with hands off.  Every table below is
  therefore ALSO cut by |driver torque| so the hands-off arm can be read separately.
* Route `73` (V88) lives in `_scratch/cache/r73` at the REPO ROOT, not under `analysis-2020accord`, so it
  is loaded by explicit path.  It has no `v_rear`; rear wheel speeds are averaged directly.

Usage:  python studies/ra6/ra6_rate.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NAMES = {'r73': 'V88  (route 73)', 'ra4': 'V104 (route a4)', 'ra5': 'V105 (route a5)',
         'ra6': 'V106 (route a6)'}
TAGS = ('r73', 'ra4', 'ra5', 'ra6')
OUT = {}


def load(tag):
    if tag == 'r73':
        d = dict(np.load(os.path.join(ROOT, '_scratch/cache/r73', 'r73.npz'), allow_pickle=True))
    else:
        d = dict(L.load(tag))
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    rc = np.asarray(d['rate_c'], float)
    dem = np.abs(np.asarray(d['e4tq'], float))
    tq = np.abs(np.asarray(d['tq'], float))
    return d, e, v, rc, dem, tq


DAT = {t: load(t) for t in TAGS}

# ================================================================== 0. demand scale control
print("=" * 124)
print("0.  🛑 CONTROL -- IS THE DEMAND AXIS THE SAME ON ALL FOUR ROUTES?")
print("    A demand->rate curve is meaningless if `e4tq` is scaled differently, or if one route")
print("    simply never asked for as much.  Percentiles of |e4tq| over ENGAGED frames:")
print("=" * 124)
print("%18s %10s %9s %9s %9s %9s %9s %12s"
      % ('build', 'n eng', 'p50', 'p90', 'p99', 'p99.9', 'max', 'sec engaged'))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    x = dem[e]
    print("%18s %10d %9.0f %9.0f %9.0f %9.0f %9.0f %12.1f"
          % (NAMES[t], len(x), *[np.percentile(x, p) for p in (50, 90, 99, 99.9)],
             x.max(), e.sum() / FS))
    OUT.setdefault('demand_scale', {})[NAMES[t]] = dict(
        n=int(len(x)), mx=float(x.max()), sec=float(e.sum() / FS),
        **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99, 99.9)})

# ================================================================== 1. rate distribution
print()
print("=" * 124)
print("1.  |d(steering angle)/dt| DURING ENGAGED FRAMES -- the operator's own quantity.")
print("    ⚠ Speed-stratified, because achievable rate is a strong function of speed.")
print("=" * 124)
VE = [0, 8, 16, 40, 70, 1e9]
VL = ['<8', '8-16', '16-40', '40-70', '70+']
for lbl, key in (('ALL ENGAGED', 'all'), ('ENGAGED, HANDS-OFF (|tq| < 200)', 'off')):
    print("\n  %s" % lbl)
    print("%18s %8s %9s %9s %9s %9s %9s %9s"
          % ('build', 'speed', 'n', 'p50', 'p90', 'p99', 'p99.9', 'MAX'))
    for t in TAGS:
        d, e, v, rc, dem, tq = DAT[t]
        base = e & (tq < 200) if key == 'off' else e
        for i, s in enumerate(VL):
            m = base & (v >= VE[i]) & (v < VE[i + 1])
            if m.sum() < 300:
                continue
            x = np.abs(rc[m])
            print("%18s %8s %9d %9.1f %9.1f %9.1f %9.1f %9.1f"
                  % (NAMES[t], s, int(m.sum()),
                     *[np.percentile(x, p) for p in (50, 90, 99, 99.9)], x.max()))
            OUT.setdefault('rate_dist', {}).setdefault(key, {}).setdefault(NAMES[t], {})[s] = dict(
                n=int(m.sum()), mx=float(x.max()),
                **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99, 99.9)})

# ================================================================== 2. demand -> rate
print()
print("=" * 124)
print("2.  ⭐ THE DEMAND -> ACHIEVED-RATE CURVE.  **THE RATE AT MAX LKAS DEMAND.**")
print("    H-RATE (slew ceiling) predicts a PLATEAU; H-ACC (acceleration penalty) predicts the")
print("    curve keeps climbing but the LOW-demand end is depressed.")
print("=" * 124)
DE = [0, 200, 400, 700, 1000, 1500, 2200, 1e9]
DL = ['<200', '200-400', '400-700', '700-1k', '1k-1.5k', '1.5k-2.2k', '2.2k+']
for lbl, vlo, vhi in (('engaged, <16 km/h', 0, 16), ('engaged, 16-70 km/h', 16, 70),
                      ('engaged, 70+ km/h', 70, 1e9)):
    print("\n  %s   -- p90 of |rate_c| (deg/s), then MAX in brackets" % lbl)
    print("%18s" % 'build' + "".join("%17s" % s for s in DL))
    for t in TAGS:
        d, e, v, rc, dem, tq = DAT[t]
        row, cells = [], {}
        for i, s in enumerate(DL):
            m = e & (v >= vlo) & (v < vhi) & (dem >= DE[i]) & (dem < DE[i + 1])
            if m.sum() < 150:
                row.append(None)
                continue
            x = np.abs(rc[m])
            row.append((float(np.percentile(x, 90)), float(x.max()), int(m.sum())))
            cells[s] = dict(p90=row[-1][0], mx=row[-1][1], n=row[-1][2])
        print("%18s" % NAMES[t] + "".join("        --       " if r is None
                                          else "%9.1f [%5.0f]" % (r[0], r[1]) for r in row))
        OUT.setdefault('demand_rate', {}).setdefault(lbl, {})[NAMES[t]] = cells

# ================================================================== 3. pile-up test
print()
print("=" * 124)
print("3.  THE PILE-UP TEST -- a SLEW CEILING is a rail, and a rail is a spike in the histogram.")
print("    Top distinct |rate_c| values, engaged, and the share of frames within 5 %% of the p99.9.")
print("    (V80's postmortem: 'does not clip' and 'is not a relay' are different statements --")
print("     so this looks for a PILE-UP, not for a clip.)")
print("=" * 124)
print("%18s %12s %12s %14s   %s"
      % ('build', 'p99.9', 'MAX', 'frac >=.95p999', 'top distinct values : count'))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    x = np.abs(rc[e])
    p999 = np.percentile(x, 99.9)
    u, c = np.unique(x, return_counts=True)
    top = np.argsort(u)[-6:]
    print("%18s %12.1f %12.1f %14.5f   %s"
          % (NAMES[t], p999, x.max(), float(np.mean(x >= 0.95 * p999)),
             "  ".join("%.0f:%d" % (u[k], c[k]) for k in top)))
    OUT.setdefault('pileup', {})[NAMES[t]] = dict(
        p999=float(p999), mx=float(x.max()), frac_near=float(np.mean(x >= 0.95 * p999)),
        top=[[float(u[k]), int(c[k])] for k in top])

# ================================================================== 4. onset transient
print()
print("=" * 124)
print("4.  ⭐⭐ THE DISCRIMINATOR -- THE ONSET TRANSIENT vs THE SUSTAINED VALUE.")
print("    Events: engaged, |e4tq| crosses 800 upward after >= 0.5 s below 300.  Aligned at the")
print("    crossing.  H-ACC => the RISE is slower but the PLATEAU is the same.  H-RATE => the")
print("    PLATEAU itself is lower.")
print("=" * 124)


def onsets(e, dem, rc, v, lo=300.0, hi=800.0, pre=0.5, post=1.5, vmin=0.0):
    npre, npost = int(pre * FS), int(post * FS)
    out = []
    above = dem >= hi
    below = dem < lo
    for i in np.flatnonzero(above[1:] & ~above[:-1]) + 1:
        if i - npre < 0 or i + npost >= len(dem):
            continue
        if not below[i - npre:i].all():
            continue
        if not e[i - npre:i + npost].all():
            continue
        if v[i] < vmin:
            continue
        out.append(i)
    return out


GRID = np.arange(0, int(1.5 * FS))
print("%18s %8s" % ('build', 'events')
      + "".join("%9s" % ("%.2fs" % (g / FS)) for g in GRID[::10]))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    ev = onsets(e, dem, np.abs(rc), v)
    if len(ev) < 8:
        print("%18s %8d   -- too few onset events --" % (NAMES[t], len(ev)))
        continue
    M = np.array([np.abs(rc[i:i + len(GRID)]) for i in ev])
    prof = np.median(M, 0)
    print("%18s %8d" % (NAMES[t], len(ev))
          + "".join("%9.2f" % prof[g] for g in GRID[::10]))
    OUT.setdefault('onset', {})[NAMES[t]] = dict(
        n=int(len(ev)), t=[float(g / FS) for g in GRID],
        median_rate=[float(x) for x in prof],
        rise_0_25=float(prof[:int(0.25 * FS)].mean()),
        plateau_1_0_1_5=float(prof[int(1.0 * FS):].mean()))
print("  ⇒ compare the FIRST 0.25 s (the rise) against the LAST 0.5 s (the plateau):")
print("%18s %14s %14s %14s" % ('build', 'rise 0-0.25 s', 'plateau 1.0-1.5 s', 'rise/plateau'))
for t in TAGS:
    r = OUT.get('onset', {}).get(NAMES[t])
    if not r:
        continue
    print("%18s %14.2f %14.2f %14.3f"
          % (NAMES[t], r['rise_0_25'], r['plateau_1_0_1_5'],
             r['rise_0_25'] / r['plateau_1_0_1_5'] if r['plateau_1_0_1_5'] else np.nan))

# ================================================================== 5. sustained-demand rate
print()
print("=" * 124)
print("5.  THE SUSTAINED-DEMAND TEST -- `H(f=0) = 0` SAYS A HELD COMMAND SEES NOTHING.")
print("    Frames where |e4tq| has been >= 800 CONTINUOUSLY for >= 0.4 s (so the transient is")
print("    over).  If V106 is an acceleration penalty ONLY, this row must be UNCHANGED.")
print("=" * 124)
print("%18s %10s %9s %9s %9s %9s" % ('build', 'n', 'p50', 'p90', 'p99', 'MAX'))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    k = int(0.4 * FS)
    held = np.convolve((dem >= 800).astype(float), np.ones(k), 'same') >= k - 0.5
    m = e & held
    if m.sum() < 200:
        print("%18s %10d   -- too few frames --" % (NAMES[t], m.sum()))
        continue
    x = np.abs(rc[m])
    print("%18s %10d %9.1f %9.1f %9.1f %9.1f"
          % (NAMES[t], int(m.sum()), *[np.percentile(x, p) for p in (50, 90, 99)], x.max()))
    OUT.setdefault('sustained', {})[NAMES[t]] = dict(
        n=int(m.sum()), mx=float(x.max()),
        **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_rate.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_rate.json")
