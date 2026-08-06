#!/usr/bin/env python3
"""v75_step_cooccur.py -- do relay-plateau TRANSITIONS co-occur with high openpilot command?

🛑 PROXY, throughout. gp-0x6b04, gp-0x6b98 and Monitor 2's corridor are NOT observable on route 5d
   (V74's probe spent its field on the damper and the state). "Plateau transition" is a replayed
   property of the damper surface; "command" is CAN 0x0E4, openpilot's REQUEST at the panda TX echo.

🛑 UNITS GAP on §3 -- stated up front because it is load-bearing:
   openpilot's bus value is clamped at 4096. The firmware INTAKE (`FUN_00052676`) is
   `clamp(req x -4, +-0x4000)`, so the same command is 16384 internally -- 3.4x the 4762 governor
   ceiling on its own. Meanwhile gp-0x6b98's own clamp is +-8192 (= the +-0x2000 shaper-output rail).
   And gp-0x6bd0 (the relay step) is in AGGREGATOR units (own ceiling 512, gate window +-2048).
   THREE candidate scalings, none resolvable from telemetry. §3 is computed in the coordinator's own
   frame (bus counts, 1:1 with the 4762/8192 bounds) and is LABELLED AN ASSUMPTION, with a
   sensitivity sweep. Do not read §3 as a measurement.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

RNG = np.random.default_rng(20260806)
W = 1.0 / 100.0009
RAIL = 4096.0
SLEW_RAIL = 123.0
GOV, FINAL = 4762.0, 8192.0
STEP = {"V74": 450, "V75": 594}          # full relay reversal, flat-FactorC band
BUILDS = [("V74", 400), ("V75", 200)]


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


D = L.load_route()
n = len(D["t"])
r_cts = np.abs(np.trunc(np.rint(D["rate_f"] * 10.0) * 2048.0 / 3477.0).astype(np.int64))
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, _, _ = L.mode_masks(D["cc_lat"], D["t"])
cmd = np.abs(D["e4tq"])
dcmd = np.abs(np.r_[0.0, np.diff(D["e4tq"])])
at_amp = cmd >= RAIL - 0.5
at_slew = dcmd >= SLEW_RAIL - 0.5
at_rail = at_amp | at_slew

STRATA = [("ENGAGED overall", in26),
          ("ENGAGED 0-35 km/h", in26 & (sp_cts < 2240)),
          ("ENGAGED creep < 4 m/s", in26 & (D["cs_v"] < 4.0))]


def blocks(mask):
    m = mask & np.r_[True, np.diff(D["seg"]) == 0]
    idx = np.flatnonzero(m)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > 1)
    return [r for r in np.split(idx, brk + 1) if len(r)]


def transitions(mask, entry):
    """Global indices of every plateau entry and exit inside `mask`."""
    out = []
    for b in blocks(mask):
        occ = (r_cts[b] >= entry).astype(np.int8)
        d = np.diff(occ)
        for k in np.flatnonzero(d != 0) + 1:
            out.append(int(b[k]))
    return np.array(sorted(out), dtype=int)


hdr("0.  THE COMMAND CHANNEL, and the kit's rail census reproduced")
e = in26
print(f"  |0x0E4| over engaged frames: p50 {np.percentile(cmd[e],50):7.1f}  p90 "
      f"{np.percentile(cmd[e],90):7.1f}  p99 {np.percentile(cmd[e],99):7.1f}  max {cmd[e].max():7.1f}")
print(f"  AT the amplitude rail (|cmd| >= 4096): {at_amp[e].mean()*100:6.3f}% of engaged frames")
print(f"  AT the slew rail (|dcmd| >= 123)     : {at_slew[e].mean()*100:6.3f}%")
print(f"  AT either rail                       : {at_rail[e].mean()*100:6.3f}%   "
      f"(kit's recorded figure: 16.07%)")

# ---------------------------------------------------------------------------------------------------
hdr("1.  |COMMAND| AT PLATEAU TRANSITIONS vs OVER ALL ENGAGED FRAMES")
print(f"  {'stratum':22s} {'build':>5s} {'n_tr':>6s} | {'p50':>7s} {'p90':>7s} {'p99':>7s} "
      f"{'max':>7s} | {'baseline p50':>13s} {'p90':>7s} | {'ratio p50':>10s}")
tr_store = {}
for sname, smask in STRATA:
    base = cmd[smask]
    for bname, entry in BUILDS:
        ti = transitions(smask, entry)
        tr_store[(sname, bname)] = ti
        if not len(ti):
            continue
        c = cmd[ti]
        print(f"  {sname:22s} {bname:>5s} {len(ti):6d} | {np.percentile(c,50):7.1f} "
              f"{np.percentile(c,90):7.1f} {np.percentile(c,99):7.1f} {c.max():7.1f} | "
              f"{np.percentile(base,50):13.1f} {np.percentile(base,90):7.1f} | "
              f"{np.percentile(c,50)/max(np.percentile(base,50),1e-9):10.2f}")

print("\n  Same, using the MAX |command| in a +-2 sample (+-20 ms) window around each transition:")
for sname, smask in STRATA[:1]:
    base = cmd[smask]
    for bname, entry in BUILDS:
        ti = tr_store[(sname, bname)]
        if not len(ti):
            continue
        wmax = np.array([cmd[max(i - 2, 0):i + 3].max() for i in ti])
        print(f"    {sname:22s} {bname:>5s}  p50 {np.percentile(wmax,50):7.1f}  p90 "
              f"{np.percentile(wmax,90):7.1f}  max {wmax.max():7.1f}   "
              f"(engaged baseline p50 {np.percentile(base,50):.1f})")

# ---------------------------------------------------------------------------------------------------
hdr("2.  CO-OCCURRENCE RATE -- transitions near / at openpilot's rail   ** THE HEADLINE **")
print(f"  {'stratum':22s} {'build':>5s} {'n_tr':>6s} {'sec':>7s} | "
      f"{'>=70%':>6s} {'>=80%':>6s} {'>=90%':>6s} {'ATrail':>7s} | "
      f"{'ATrail/s':>9s} {'base%':>7s} {'lift':>6s}")
cooc = {}
for sname, smask in STRATA:
    secs = float(smask.sum()) * W
    base_rail = at_rail[smask].mean()
    for bname, entry in BUILDS:
        ti = tr_store[(sname, bname)]
        if not len(ti):
            continue
        c = cmd[ti]
        n70 = int((c >= 0.70 * RAIL).sum())
        n80 = int((c >= 0.80 * RAIL).sum())
        n90 = int((c >= 0.90 * RAIL).sum())
        nr = int(at_rail[ti].sum())
        lift = (nr / len(ti)) / base_rail if base_rail else float("nan")
        cooc[(sname, bname)] = dict(n=len(ti), n70=n70, n80=n80, n90=n90, nr=nr,
                                    rate=nr / secs, lift=lift)
        print(f"  {sname:22s} {bname:>5s} {len(ti):6d} {secs:7.1f} | {n70:6d} {n80:6d} {n90:6d} "
              f"{nr:7d} | {nr/secs:9.4f} {base_rail*100:7.3f} {lift:6.2f}")
print("\n  `lift` = P(at rail | transition) / P(at rail | any engaged frame). 1.0 = INDEPENDENT.")

# ---------------------------------------------------------------------------------------------------
hdr("3.  COMBINED-MAGNITUDE ESTIMATE  ** ASSUMPTION, NOT A MEASUREMENT **")
print("  |command| + relay_step, vs the 4762 governor ceiling and the 8192 final clamp.")
print("  🛑 THREE reasons this is a LOWER BOUND on the aggregate and therefore an UNDERESTIMATE of")
print("     clamp-binding frequency, and one reason it may be an OVERESTIMATE of the per-term size:")
print("     (a) the governor sees an 11-TERM SUM. I have openpilot's contribution + the replayed")
print("         damper only. Base assist, boost, friction, return-centre, resonance, r24, r26 and")
print("         FUN_00036682 are ALL MISSING -> underestimate.")
print("     (b) the damper OPPOSES velocity while LKAS drives it, so the two can partially CANCEL;")
print("         the sum below assumes worst-case alignment -> overestimate of THIS pair.")
print("     (c) UNITS: bus counts are assumed 1:1 with the 4762/8192 bounds. The intake scales x4")
print("         and gp-0x6b98's own clamp is +-8192; a different scaling changes everything.")
for sname, smask in STRATA:
    for bname, entry in BUILDS:
        ti = tr_store[(sname, bname)]
        if not len(ti):
            continue
        tot = cmd[ti] + STEP[bname]
        print(f"  {sname:22s} {bname:>5s} n {len(ti):5d} | > {GOV:.0f}: {int((tot>GOV).sum()):5d} "
              f"({100*(tot>GOV).mean():5.1f}%)   > {FINAL:.0f}: {int((tot>FINAL).sum()):5d}   "
              f"max {tot.max():7.1f}")
print("\n  SENSITIVITY to the units assumption (engaged overall, fraction of transitions > 4762):")
for k in (0.5, 1.0, 2.0, 4.0):
    row = []
    for bname, entry in BUILDS:
        ti = tr_store[("ENGAGED overall", bname)]
        tot = k * cmd[ti] + STEP[bname]
        row.append(f"{bname} {100*(tot>GOV).mean():5.1f}%")
    print(f"    command scaled x{k:<4}: " + "   ".join(row))

# ---------------------------------------------------------------------------------------------------
hdr("4.  THE LAUNCH STRATUM, and the six launch events (n = 6, zero of them engaged stops)")
LO, HI = 1.0 / 3.6, 20.0 / 3.6
v = D["cs_v"]
lat = D["cc_lat"] > 0.5
events = []
for s in np.unique(D["seg"]):
    idx = np.flatnonzero(D["seg"] == s)
    bb, aa = v[idx] < LO, v[idx] > HI
    j = 0
    while j < len(idx):
        if not bb[j]:
            j += 1
            continue
        k = j
        while k < len(idx) and bb[k]:
            k += 1
        p = k
        while p < len(idx) and not aa[p] and not bb[p]:
            p += 1
        if p < len(idx) and aa[p]:
            events.append((idx[k - 1], idx[p]))
        j = max(k, j + 1)
print(f"  {'#':>3s} {'seg':>4s} {'ramp s':>7s} {'lat%':>6s} {'cmd p50':>8s} {'cmd max':>8s} "
      f"{'railf%':>7s} | {'V74 tr':>7s} {'V75 tr':>7s} | {'V74 tr@rail':>12s} {'V75 tr@rail':>12s}")
for c, (b, p) in enumerate(events):
    sl = slice(b, p + 1)
    m = np.zeros(n, bool)
    m[b:p + 1] = True
    m &= in26
    row = []
    for bname, entry in BUILDS:
        ti = transitions(m, entry)
        row.append((len(ti), int(at_rail[ti].sum()) if len(ti) else 0))
    print(f"  {c:3d} {int(D['seg'][b]):4d} {D['t'][p]-D['t'][b]:7.2f} {lat[sl].mean()*100:6.1f} "
          f"{np.percentile(cmd[sl],50):8.1f} {cmd[sl].max():8.1f} {at_rail[sl].mean()*100:7.2f} | "
          f"{row[0][0]:7d} {row[1][0]:7d} | {row[0][1]:12d} {row[1][1]:12d}")

# ---------------------------------------------------------------------------------------------------
hdr("5.  EPISODE-LEVEL SIGN TEST -- is the transition sample biased toward high command?")
eps = L.episodes(D["cc_lat"], D["t"])
print("  Per episode: median |command| at V75 transitions vs median |command| over all engaged")
print("  frames of that episode. Sign test on the direction (the right statistic at n = 9).")
print(f"  {'ep':>3s} {'n_tr':>6s} {'med@tr':>8s} {'med@base':>9s} {'dir':>4s}")
ups = downs = 0
for i, ee in enumerate(eps):
    m = np.zeros(n, bool)
    m[ee] = True
    m &= in26
    ti = transitions(m, 200)
    if len(ti) < 3 or m.sum() < 10:
        print(f"  {i:3d} {len(ti):6d}  (skipped: too few)")
        continue
    a, b = float(np.median(cmd[ti])), float(np.median(cmd[m]))
    d = "UP" if a > b else "DOWN"
    ups += a > b
    downs += a <= b
    print(f"  {i:3d} {len(ti):6d} {a:8.1f} {b:9.1f} {d:>4s}")
tot = ups + downs
from math import comb
p = 2 * sum(comb(tot, k) for k in range(max(ups, downs), tot + 1)) / 2 ** tot if tot else float("nan")
print(f"\n  {ups} UP / {downs} DOWN of {tot} informative episodes.  two-sided sign test p = "
      f"{min(p,1.0):.4f}")
print(f"  POWER: with n = {tot} episodes the smallest detectable direction imbalance at p<0.05 is "
      f"{tot}/0 or {tot-1}/1. Magnitude ratios are NOT establishable at this n.")
