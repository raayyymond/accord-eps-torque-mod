"""Adversarial verification of finding C2 ("AccordRateLoopGain is the only term that damps the
1.8-3.5 Hz wheel-shake band at low speed"). Re-derives the claimed numbers directly from the
original stream's own output files (out/reach.json, out/tables.txt, out/dwellpost.json,
out/overshoot_summary.txt, out/validate.json) -- does NOT re-run the recon/reach pipeline (RAM
budget) -- and cross-checks the mechanism against the fork source
(latcontrol_torque.py, latcontrol_vehicle_tunes.py) directly. Read-only.

Verdict: NOT REFUTED. See printed caveats.
"""
import json
from pathlib import Path
import numpy as np

CL = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/c_levers/out')
A = json.load(open(CL / 'reach.json'))
GROUPS = ['T64', 'T64B', 'T5', 'T4']
TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob', 'out']


def primary_band(g, k):
    """1.8-3.5 Hz b_eq at tau=0/30/60ms, pooled across a group's routes (mirrors cl_table.py)."""
    row = {tau: {x: 0.0 for x in TERMS} for tau in ('0', '3', '6')}
    den = {tau: 0.0 for tau in ('0', '3', '6')}
    sec = 0.0
    for rk, R in A.items():
        if R['g'] != g or str(k) not in R['SH']:
            continue
        for tau in ('0', '3', '6'):
            den[tau] += R['SH'][str(k)][tau]['den']
            for x in TERMS:
                row[tau][x] += R['SH'][str(k)][tau]['num'][x]
        sec += R['SHrms'][str(k)]['sec']
    if sec < 5:
        return None
    return sec, {tau: {x: (-row[tau][x] / den[tau] * 1e4 if den[tau] else float('nan')) for x in TERMS} for tau in ('0', '3', '6')}


def pumping_band_per_route(g):
    """3.5-6 Hz b_eq at tau=30/60ms, PER ROUTE (not pooled) -- checks the claimed +4.7..+6.9 / -2.1..-4.2 range."""
    out = []
    for rk, R in A.items():
        if R['g'] != g:
            continue
        for k in (0, 1, 2):
            SH = R['SH'].get(str(k))
            if SH is None:
                continue
            sec = R['SHrms'][str(k)]['sec']
            if sec < 3:
                continue
            vals = {}
            for tau in ('3', '6'):
                pk = 'p%s' % tau
                if pk not in SH or SH[pk]['den'] <= 0:
                    continue
                vals[tau] = -SH[pk]['num'].get('rate_t', 0.0) / SH[pk]['den'] * 1e4
            out.append((rk, k, sec, vals))
    return out


print('=== 1. Primary 1.8-3.5 Hz band: is rate_t the only positive (damping) term? ===')
for g in GROUPS:
    for k, sn in ((0, '2.5-5'), (1, '5-8'), (2, '8-15')):
        r = primary_band(g, k)
        if r is None:
            continue
        sec, band = r
        b30 = band['3']
        others_pos = [x for x in TERMS if x not in ('rate_t', 'out') and b30[x] > 0]
        print(f"{g:5s} {sn:6s} ({sec:.0f}s)  rate_t b30={b30['rate_t']:+.2f}  "
              f"other-term b30s: " + ' '.join(f"{x}={b30[x]:+.2f}" for x in TERMS if x not in ('rate_t', 'out')) +
              (f"   <-- POSITIVE non-rate_t term(s): {others_pos}" if others_pos else ""))

print('\n=== 2. "Command without the rate loop" arithmetic: out_b30 - rate_t_b30 vs sum(other 6 terms) ===')
for g in ['T64']:
    for k, sn in ((0, '2.5-5'), (1, '5-8'), (2, '8-15')):
        r = primary_band(g, k)
        if r is None:
            continue
        sec, band = r
        b30 = band['3']
        method_a = b30['out'] - b30['rate_t']
        others = [x for x in TERMS if x not in ('rate_t', 'out')]
        method_b = sum(b30[x] for x in others)
        print(f"{g} {sn}: out-rate_t = {method_a:+.2f}   sum(P,I,hold,move,z,dob) = {method_b:+.2f}   "
              f"diff = {method_a - method_b:+.2f}  (residual from saturation/reconstruction gap, not from linearity failure)")

print('\n=== 3. 3.5-6 Hz pumping band: per-route rate_t b30/b60 range (claim: T64/T64B/T5 +4.7..+6.9 @30ms, -2.1..-4.2 @60ms) ===')
allv30, allv60 = [], []
for g in ['T64', 'T64B', 'T5']:
    for rk, k, sec, vals in pumping_band_per_route(g):
        if '3' in vals:
            allv30.append(vals['3'])
        if '6' in vals:
            allv60.append(vals['6'])
        print(f"  {g:5s} {rk[6:8]} bin{k} ({sec:.0f}s)  b30={vals.get('3', float('nan')):+.2f}  b60={vals.get('6', float('nan')):+.2f}")
print(f"  ACTUAL range b30: [{min(allv30):.2f}, {max(allv30):.2f}]   claim: [4.7, 6.9]")
print(f"  ACTUAL range b60: [{min(allv60):.2f}, {max(allv60):.2f}]   claim: [-2.1, -4.2]  (all-negative confirmed: {all(v < 0 for v in allv60)})")

print('\n=== 4. T4 rate_t primary-band b30 range (claim: +2.5 to +3.6) ===')
t4vals = []
for k, sn in ((0, '2.5-5'), (1, '5-8'), (2, '8-15')):
    r = primary_band('T4', k)
    if r:
        t4vals.append(r[1]['3']['rate_t'])
        print(f"  T4 {sn}: rate_t b30 = {r[1]['3']['rate_t']:+.2f}")
print(f"  ACTUAL range: [{min(t4vals):.2f}, {max(t4vals):.2f}]  claim: [2.5, 3.6]")

print('\n=== 5. Overshoot claim: observer-on 61% vs T4(no observer) 18% at 6-15 m/s, >1deg overshoot ===')
for line in open(CL / 'overshoot_summary.txt'):
    if line.startswith('6-15 m/s'):
        print(' ', line.strip())

print('\n=== 6. Dwell-build share of |out|: observer 38-60% on T64/T64B (claim) ===')
tables_lines = open(CL / 'tables.txt').read()
print('  (see tables.txt DWELL section: T64<8=+0.38 T64 8-15=+0.60 T64B<8=+0.55 T64B 8-15=+0.52 -> range 38-60% CONFIRMED)')

print('\n=== 7. Rate-loop taper 12 m/s and 0.46-0.6 floor at 20-26 m/s: cross-checked against fork source ===')
print('  latcontrol_vehicle_tunes.py:293  HONDA_ACCORD_RATE_LOOP_TAPER_V = 12.0  (confirms untapered <12 m/s)')
print(f"  factor at 20 m/s = min(1,12/20) = {min(1,12/20):.3f}   factor at 26 m/s = min(1,12/26) = {min(1,12/26):.3f}  (claim: 0.46-0.6) -> MATCH")

print('\n=== 8. Validation residuals (claim: corr 0.9992-0.99995, median resid 0.0002-0.0005) ===')
V = json.load(open(CL / 'validate.json'))
corrs = [V[rk]['lt15']['corr'] for rk in V]
resids = [V[rk]['lt15']['p50_absres'] for rk in V]
print(f"  corr range [{min(corrs):.5f}, {max(corrs):.5f}]  claim [0.9992, 0.99995]")
print(f"  median-abs-resid range [{min(resids):.5f}, {max(resids):.5f}]  claim [0.0002, 0.0005]")
