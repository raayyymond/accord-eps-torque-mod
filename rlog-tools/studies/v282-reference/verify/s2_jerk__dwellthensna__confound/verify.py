"""Adversarial CONFOUND check on s2_jerk finding 'dwell-then-snap-stick-slip-in-events'.

Claim under test: torque-mode (T64/T64B/T5/T4) jerk events show more dwell-then-snap travel
concentration ('conc', angle-based) and more dwell time than V282, and this is the operator's
ratchety/snapping symptom -- NOT an artifact of different roads/days/speeds/demand amplitude/
fork config/learned lateral delay/achieved-lat-accel definition.

This script does NOT touch s2_jerk's own files. It reuses s2_jerk's cached per-event extraction
(_out/events_*.npz) and its match()/boot_diff() machinery (imported, not copied logic-wise
except conc_of/dwell which must be recomputed because s2_stickslip.py does not persist them).

Confound probes run here, none of which the original stream ran:
  1. Leave-one-route-out on BOTH the conc and dwell metrics (original s2_analyze.py's LORO list
     does not include 'conc'/'dwell' -- only s2_results.json's METRICS, which are la_act/la_pose
     lag/gain/step timing, not the stick-slip metrics). Specifically: does the result survive
     dropping r6c 2bc842dbac, the 62-segment route that dominates the V282 side (3.8 MB cache vs
     <1 MB for the other two V282 routes)?
  2. Reference-fork-config swap: re-run the SAME comparison using V282old (independently tuned
     fork, LAF 2.1-4.0 Kp 0.8, three different routes/days/commits) as the reference instead of
     V282. If the torque-mode excess survives against a totally different V282-era fork tune,
     fork-config-as-the-real-cause is weakened.
  3. Demand-amplitude / speed match-quality audit: report the matched-pair jerk/step/v ratios
     (ref/tq) per stratum -- the caliper-based NN matcher already used by s2_jerk restricts these,
     but this script reports the realised balance explicitly rather than trusting the caliper.
  4. Cross-metric, cross-rev consistency: does conc/dwell replicate in sign across ALL FOUR
     independent torque revs (different fork commits: 84766cdc, e44b6cd3, 08a5a706)? A confound
     tied to one fork build would not.
  5. Achieved-signal swap for the jerk-roughness sub-claim: la_pose (independent yaw-rate-derived
     measure) vs la_act, both already computed per-event by s2_extract.py; report LORO for both
     and flag where la_pose's own coherence is too low to arbitrate (per the brief, >=15 m/s).

Usage: python verify.py   (loads all 11 cached event files, ~10 MB total, fine in one process)
"""
import sys, json, glob
import numpy as np
from scipy import signal

S2 = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__dwellthensna__confound'
sys.path.insert(0, S2)
from s2_common import load_all, match, boot_diff, vbin, VBINS  # noqa: E402 (shared, unedited)

rows, tr = load_all()
sos5 = signal.butter(2, 5.0, fs=100, output='sos')


def conc_of(sa):
    x = signal.sosfiltfilt(sos5, sa)[50:300]
    d = np.abs(np.diff(x)); tot = d.sum()
    if tot < 0.5:
        return np.nan
    k = max(1, int(0.15 * len(d)))
    return float(np.sort(d)[-k:].sum() / tot)


def _controls():
    t = np.arange(350) / 100
    ramp = 10 * np.clip((t - 1.0) / 1.5, 0, 1)
    steps = 10 * (np.floor(np.clip((t - 1.0) / 1.5, 0, 0.999) * 4) / 4 + 0.25 * (t > 2.5 - 1e-9))
    c_r, c_s = conc_of(ramp + 0.0), conc_of(steps)
    assert c_r < 0.30 and c_s > 0.6, (c_r, c_s)
    return dict(ramp=c_r, staircase=c_s)


print('positive/negative controls (ramp low, staircase high):', _controls())

for r in rows:
    u = r['uid']; Dd = max(abs(r['a1'] - r['a0']), 1e-3)
    r['conc'] = conc_of(tr['sa'][u])
    sr5 = signal.sosfiltfilt(sos5, tr['sr'][u]); m = tr['model'][u] / Dd
    ms = np.abs(np.gradient(m) * 100)
    w = slice(70, 200); moving = ms[w] > 0.15
    r['dwell'] = float(np.mean(np.abs(sr5[w][moving]) < 1.0)) if moving.sum() > 20 else np.nan

V282 = [r for r in rows if r['group'] == 'V282']
V282OLD = [r for r in rows if r['group'] == 'V282old']
TQGROUPS = ['T64', 'T64B', 'T5', 'T4']
STRATA = {'>=15': [2, 3], '8-15': [1], '<15': [0, 1]}

print(f"\nn events: V282 {len(V282)}, V282old {len(V282OLD)}, " +
      ', '.join(f'{g} {sum(r["group"]==g for r in rows)}' for g in TQGROUPS))
print("V282 routes:", sorted(set(r['route'] for r in V282)),
      "-- counts:", {rt: sum(r['route'] == rt for r in V282) for rt in sorted(set(r['route'] for r in V282))})

results = {}


def stratum_stats(ref_rows, tq_rows, key):
    """Matched pairs (fresh NN match on THESE two row sets) -> diff + event/route bootstrap CI,
    plus realised match balance (median ref/tq ratio for jerk, step, v -- the demand-amplitude
    and speed confound check)."""
    pairs_all = match(ref_rows, tq_rows)
    out = {}
    for sn, vbs in STRATA.items():
        P = [p for p in pairs_all if p[1]['vb'] in vbs]
        if len(P) < 4:
            out[sn] = dict(n_pairs=len(P))
            continue
        b = boot_diff(P, key)
        bal = dict(
            jerk_ref=float(np.median([p[0]['jerk'] for p in P])), jerk_tq=float(np.median([p[1]['jerk'] for p in P])),
            step_ref=float(np.median([p[0]['step'] for p in P])), step_tq=float(np.median([p[1]['step'] for p in P])),
            v_ref=float(np.median([p[0]['v'] for p in P])), v_tq=float(np.median([p[1]['v'] for p in P])))
        out[sn] = dict(n_pairs=len(P), ref=float(np.nanmedian([p[0][key] for p in P])),
                        tq=float(np.nanmedian([p[1][key] for p in P])), diff=b['med'],
                        ci_ev=b['ci_ev'], ci_rt=b['ci_rt'], n=b['n'], balance=bal)
    return out


# ---------------------------------------------------------------- probe 1: LORO for conc / dwell
print("\n===== PROBE 1: leave-one-route-out (V282 vs T64+T64B+T5+T4 pooled), conc + dwell =====")
TQ_ALL = [r for r in rows if r['group'] in TQGROUPS]
pairs_all = match(V282, TQ_ALL)
loro = {}
for key in ('conc', 'dwell'):
    loro[key] = {}
    for sn, vbs in STRATA.items():
        P = [p for p in pairs_all if p[1]['vb'] in vbs]
        base = boot_diff(P, key)['med'] if len(P) >= 3 else np.nan
        drops = {}
        for rt in sorted(set([p[0]['route'] for p in P] + [p[1]['route'] for p in P])):
            PP = [p for p in P if p[0]['route'] != rt and p[1]['route'] != rt]
            if len(PP) < 3:
                drops[rt] = None
                continue
            d = np.array([p[1].get(key, np.nan) - p[0].get(key, np.nan) for p in PP], float)
            d = d[np.isfinite(d)]
            drops[rt] = float(np.median(d)) if len(d) else None
        loro[key][sn] = dict(base=base, n_pairs=len(P), drops=drops)
        print(f"  {key:5s} {sn:5s} base_diff {base:+.3f} n={len(P)}  drop-one:",
              {rt.split('--')[0][-4:]: (round(v, 3) if v is not None else None) for rt, v in drops.items()})
results['probe1_loro'] = loro

# ---------------------------------------------------------------- probe 2: V282old as reference
print("\n===== PROBE 2: V282old (independent fork tune, LAF 2.1-4.0 Kp 0.8) as reference =====")
p2 = {}
for g in TQGROUPS:
    TQ = [r for r in rows if r['group'] == g]
    p2[g] = {}
    for key in ('conc', 'dwell'):
        p2[g][key] = stratum_stats(V282OLD, TQ, key)
        for sn, d in p2[g][key].items():
            if 'diff' in d:
                print(f"  {g:5s} {key:5s} {sn:5s} ref(V282old) {d['ref']:.3f} tq {d['tq']:.3f} "
                      f"d {d['diff']:+.3f} evCI[{d['ci_ev'][0]:+.3f},{d['ci_ev'][1]:+.3f}] "
                      f"rtCI[{d['ci_rt'][0]:+.3f},{d['ci_rt'][1]:+.3f}] n={d['n_pairs']}")
            else:
                print(f"  {g:5s} {key:5s} {sn:5s} too few pairs ({d['n_pairs']})")
results['probe2_v282old_ref'] = p2

# ---------------------------------------------------------------- probe 3: match balance, V282 ref, all strata/groups
print("\n===== PROBE 3: matched-pair demand/speed balance, V282 (proper) reference =====")
p3 = {}
for g in TQGROUPS:
    TQ = [r for r in rows if r['group'] == g]
    p3[g] = {}
    for key in ('conc', 'dwell'):
        p3[g][key] = stratum_stats(V282, TQ, key)
        for sn, d in p3[g][key].items():
            if 'diff' in d:
                bal = d['balance']
                jr = bal['jerk_tq'] / max(bal['jerk_ref'], 1e-9); sr_ = bal['step_tq'] / max(bal['step_ref'], 1e-9)
                vr = bal['v_tq'] / max(bal['v_ref'], 1e-9)
                print(f"  {g:5s} {key:5s} {sn:5s} d {d['diff']:+.3f} evCI[{d['ci_ev'][0]:+.3f},{d['ci_ev'][1]:+.3f}] "
                      f"n={d['n_pairs']}  balance jerk_tq/ref={jr:.2f} step_tq/ref={sr_:.2f} v_tq/ref={vr:.2f}")
results['probe3_balance'] = p3

# ---------------------------------------------------------------- probe 4: cross-rev sign consistency
print("\n===== PROBE 4: sign/magnitude across independent torque revs (different fork commits) =====")
p4 = {}
FORK_OF = {'T64': '84766cdc', 'T64B': '84766cdc', 'T5': 'e44b6cd3', 'T4': '08a5a706'}
for g in TQGROUPS:
    TQ = [r for r in rows if r['group'] == g]
    row = {}
    for key in ('conc', 'dwell'):
        d = stratum_stats(V282, TQ, key)
        row[key] = {sn: (v.get('diff'), v.get('ci_ev')) for sn, v in d.items()}
    p4[g] = dict(fork=FORK_OF[g], **row)
    print(f"  {g:5s} (fork {FORK_OF[g]}):",
          {k: {sn: (round(vv[0], 3) if vv[0] is not None else None) for sn, vv in v.items()} for k, v in row.items()})
results['probe4_crossrev'] = p4

# ---------------------------------------------------------------- probe 5: la_pose vs la_act jerk-roughness LORO
print("\n===== PROBE 5: achieved-signal swap (la_pose vs la_act) jerk-roughness, LORO =====")
p5 = {}
for key in ('la_act.jerk_rough', 'la_pose.jerk_rough'):
    p5[key] = {}
    for sn, vbs in STRATA.items():
        P = [p for p in pairs_all if p[1]['vb'] in vbs]  # reuse V282-vs-pooled-torque pairing from probe 1
        if len(P) < 4:
            continue
        b = boot_diff(P, key)
        drops = {}
        for rt in sorted(set([p[0]['route'] for p in P] + [p[1]['route'] for p in P])):
            PP = [p for p in P if p[0]['route'] != rt and p[1]['route'] != rt]
            if len(PP) < 3:
                continue
            d = np.array([p[1].get(key, np.nan) - p[0].get(key, np.nan) for p in PP], float)
            d = d[np.isfinite(d)]
            if len(d):
                drops[rt] = float(np.median(d))
        p5[key][sn] = dict(diff=b['med'], ci_ev=b['ci_ev'], n=b['n'], loro_range=(min(drops.values()), max(drops.values())) if drops else None)
        print(f"  {key:20s} {sn:5s} d {b['med']:+.3f} evCI[{b['ci_ev'][0]:+.3f},{b['ci_ev'][1]:+.3f}] n={b['n']}"
              f"  loro_range={p5[key][sn]['loro_range']}")
results['probe5_signal_swap'] = p5

json.dump(results, open(f'{OUT}/verify_results.json', 'w'), indent=1, default=float)
print(f"\nwrote {OUT}/verify_results.json")
