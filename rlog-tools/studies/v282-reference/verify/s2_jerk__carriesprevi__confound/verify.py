"""Adversarial verification of s2_jerk finding 'carries-previous-motion-into-next-event'.

Claim: above 15 m/s, in [-0.6,-0.1]s before the jerk peak, error/step is more negative for T64 (torque
mode) than V282 (rate-servo), and release events show a much higher wrong-way fraction on T64 (42%) vs
V282 (4%).

Lens: CONFOUND. Re-test with:
  A. la_pose instead of la_act (la_yaw is identically zero on this car per s2_extract.py comment -- use
     the actual independent measure the original stream stored, livePose-derived).
  B. Leave-one-route-out on the V282 side, in particular WITHOUT r6c--2bc842dbac (263/318 = 83% of all
     V282 events -- it can dominate the greedy 1:1 matcher's reference pool).
  C. Per-route breakdown of the wrong-way fraction and pre/step, both sides, to see if any single route
     drives the effect.
  D. A matching-free stratified check: bin by (type, vb, step-size tercile) directly and compare group
     means/medians in each stratum without the greedy nearest-neighbour matcher, to make sure the effect
     isn't an artifact of which reference event the matcher happens to pick.
  E. V282old (secondary reference: different fork commit/config, different days/roads, SAME rate-servo
     EPS) as a placebo -- if the "carries into next event" pattern is really about the EPS control mode,
     V282old should look like V282, not like T64.
"""
import json
import numpy as np
from scipy import signal
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, match, boot_diff, VBINS

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__carriesprevi__confound'

rows, tr = load_all()
sos3 = signal.butter(2, 3.0, fs=100, output='sos')

# ---- recompute 'pre' and slope/wrong-way metrics for BOTH achieved channels (la_act, la_pose) ----
for r in rows:
    u = r['uid']; Dd = max(abs(r['a1'] - r['a0']), 1e-3)
    m = tr['model'][u] / Dd
    for ch in ('la_act', 'la_pose'):
        a = signal.sosfiltfilt(sos3, tr[ch][u]) / Dd
        r[f'{ch}.pre'] = float(np.mean((a - m)[40:90])) if Dd >= 0.2 else np.nan
        if Dd >= 0.2:
            sm = np.polyfit(np.arange(60) / 100, m[0:60], 1)[0]
            sa = np.polyfit(np.arange(60) / 100, a[0:60], 1)[0]
            r[f'{ch}.slope_m'] = float(sm); r[f'{ch}.slope_a'] = float(sa)
            r[f'{ch}.wrong'] = bool(sa < -0.2 and sm > -0.05)
        else:
            r[f'{ch}.slope_m'] = np.nan; r[f'{ch}.slope_a'] = np.nan; r[f'{ch}.wrong'] = None

log = []


def say(s):
    print(s); log.append(s)


def wrongway_table(pool_v282, label):
    say(f"\n=== {label} : wrong-way fraction, release events, >=15 m/s, step>=0.2 (both channels) ===")
    out = {}
    for g in ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']:
        R = [r for r in rows if r['group'] == g and r['vb'] in (2, 3) and r['type'] == 'release'
             and abs(r['a1'] - r['a0']) >= 0.2 and (g != 'V282' or r['route'] in pool_v282)]
        if len(R) < 4:
            say(f"  {g:8s} n={len(R):3d} (too few)")
            continue
        for ch in ('la_act', 'la_pose'):
            w = np.mean([1.0 if r[f'{ch}.wrong'] else 0.0 for r in R])
            sm = np.median([r[f'{ch}.slope_m'] for r in R])
            sa = np.median([r[f'{ch}.slope_a'] for r in R])
            out[(g, ch)] = dict(n=len(R), wrong=float(w), slope_m=float(sm), slope_a=float(sa))
            say(f"  {g:8s} {ch:8s} n={len(R):3d} model_slope {sm:+.2f}/s achieved_slope {sa:+.2f}/s wrong-way {w:.2f}")
    return out


# A + C: full pool, both channels, per-group (route breakdown folded into group here; route-level next)
all_v282_routes = set(r['route'] for r in rows if r['group'] == 'V282')
wrongway_table(all_v282_routes, "FULL POOL (as in original finding)")

# B: leave r6c--2bc842dbac OUT of the V282 reference pool (it is 263/318 = 83% of V282 events)
reduced_v282_routes = {r for r in all_v282_routes if '2bc842dbac' not in r}
say(f"\nV282 routes: {sorted(all_v282_routes)}")
say(f"V282 routes EXCLUDING the dominant 2bc842dbac: {sorted(reduced_v282_routes)}")
wrongway_table(reduced_v282_routes, "V282 REF WITHOUT 2bc842dbac (83% of V282 events removed)")

# C: per-route breakdown, la_act and la_pose, release >=15 m/s
say("\n=== per-route breakdown, release events >=15 m/s, step>=0.2 ===")
per_route = {}
for rt in sorted(set(r['route'] for r in rows)):
    R = [r for r in rows if r['route'] == rt and r['vb'] in (2, 3) and r['type'] == 'release' and abs(r['a1'] - r['a0']) >= 0.2]
    if len(R) < 3:
        say(f"  {rt:24s} n={len(R):3d} (too few)")
        continue
    g = R[0]['group']
    wa = np.mean([1.0 if r['la_act.wrong'] else 0.0 for r in R])
    wp = np.mean([1.0 if r['la_pose.wrong'] else 0.0 for r in R])
    pa = np.median([r['la_act.pre'] for r in R])
    pp = np.median([r['la_pose.pre'] for r in R])
    per_route[rt] = dict(group=g, n=len(R), wrong_act=float(wa), wrong_pose=float(wp), pre_act=float(pa), pre_pose=float(pp))
    say(f"  {rt:24s} {g:8s} n={len(R):3d} wrong(act)={wa:.2f} wrong(pose)={wp:.2f} pre(act)={pa:+.3f} pre(pose)={pp:+.3f}")

# D: matching-free stratified check -- bin (type, vb, step tercile within group) and compare medians directly
say("\n=== D: matching-free, stratified by (type, vb, step-size within-group tercile) : pre/step, act channel ===")


def stratify(g_rows):
    R = [r for r in g_rows if abs(r['a1'] - r['a0']) >= 0.2]
    steps = np.array([abs(r['a1'] - r['a0']) for r in R])
    if len(R) < 6:
        return R
    terc = np.digitize(steps, np.percentile(steps, [33.3, 66.7]))
    for r, tt in zip(R, terc):
        r['step_terc'] = int(tt)
    return R


strat = {}
for g in ['V282', 'T64', 'T64B', 'T5', 'T4']:
    strat[g] = stratify([r for r in rows if r['group'] == g])

for typ in ('onset', 'release'):
    for vb, (lo, hi) in enumerate(VBINS):
        if vb not in (2, 3):
            continue
        for terc in (0, 1, 2):
            cells = {}
            for g in strat:
                C = [r for r in strat[g] if r['type'] == typ and r['vb'] == vb and r.get('step_terc') == terc]
                if len(C) >= 3:
                    cells[g] = dict(n=len(C), pre=float(np.median([r['la_act.pre'] for r in C])),
                                     step=float(np.median([abs(r['a1'] - r['a0']) for r in C])),
                                     v=float(np.median([r['v'] for r in C])))
            if 'V282' in cells and any(g in cells for g in ('T64', 'T64B', 'T5', 'T4')):
                say(f"  {typ:8s} vb={vb} terc={terc}  V282: n={cells['V282']['n']} step={cells['V282']['step']:.2f} v={cells['V282']['v']:.1f} pre={cells['V282']['pre']:+.3f}")
                for g in ('T64', 'T64B', 'T5', 'T4'):
                    if g in cells:
                        say(f"           {' '*10}       {g:5s}: n={cells[g]['n']} step={cells[g]['step']:.2f} v={cells[g]['v']:.1f} pre={cells[g]['pre']:+.3f}")

# E: V282old as placebo -- different fork config, different days/roads, SAME rate-servo EPS
say("\n=== E: V282old (secondary ref, different fork/days/roads, SAME EPS) as placebo, release >=15 m/s ===")
for g in ('V282', 'V282old'):
    R = [r for r in rows if r['group'] == g and r['vb'] in (2, 3) and r['type'] == 'release' and abs(r['a1'] - r['a0']) >= 0.2]
    if len(R) < 4:
        continue
    w = np.mean([1.0 if r['la_act.wrong'] else 0.0 for r in R])
    pre = np.median([r['la_act.pre'] for r in R])
    say(f"  {g:8s} n={len(R):3d} wrong-way={w:.2f} pre/step={pre:+.3f}")

# also redo the matched paired-difference (as original) but on la_pose, full pool and reduced pool
say("\n=== matched paired diff (as original s2_stickslip 'pre'), >=15 m/s, la_pose channel ===")
for pool, lbl in ((all_v282_routes, 'full'), (reduced_v282_routes, 'excl-2bc842dbac')):
    REF = [r for r in rows if r['group'] == 'V282' and r['route'] in pool]
    for g in ['T64', 'T64B', 'T5', 'T4']:
        P = match(REF, [r for r in rows if r['group'] == g])
        PP = [p for p in P if p[1]['vb'] in (2, 3)]
        if len(PP) < 4:
            say(f"  {lbl:18s} V282_vs_{g:5s} n_pairs={len(PP)} (too few)")
            continue
        b = boot_diff(PP, 'la_pose.pre')
        say(f"  {lbl:18s} V282_vs_{g:5s} n_pairs={len(PP):3d} d(pose.pre)={b['med']:+.3f} ev[{b['ci_ev'][0]:+.3f},{b['ci_ev'][1]:+.3f}] rt[{b['ci_rt'][0]:+.3f},{b['ci_rt'][1]:+.3f}]")

with open(f'{OUT}/verify_out.txt', 'w') as f:
    f.write('\n'.join(log))
print('\nwrote', f'{OUT}/verify_out.txt')
