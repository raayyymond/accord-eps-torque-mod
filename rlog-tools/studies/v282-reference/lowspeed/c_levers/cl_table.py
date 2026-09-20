"""c_levers stage 3: tables from out/reach.json."""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
A = json.load(open(HERE / 'out' / 'reach.json'))
TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob', 'out']
GROUPS = ['T64', 'T64B', 'T5', 'T4']
SB = {'<8': (0, 1), '8-15': (2,)}
rng = np.random.default_rng(1)
lines = []
P = lambda s: (print(s), lines.append(s))


def boot_med(x, nb=2000):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return (np.nan, np.nan, np.nan)
    bs = [np.median(x[rng.integers(0, len(x), len(x))]) for _ in range(nb)]
    return (float(np.median(x)), *np.percentile(bs, [2.5, 97.5]))


P('=== DWELL (stick-slip) episodes: build = s*(term[end]-term[start]) torque; level = s*term[end]; median [95% CI] ===')
for g in GROUPS:
    for sn, bins in SB.items():
        DW = [d for rk, R in A.items() if R['g'] == g for d in R['DW'] if d['sb'] in bins]
        if not DW:
            continue
        big = [d for d in DW if d['jump'] >= 3.0]
        f = lambda k, L=DW: boot_med([d[k] for d in L])
        P(f"\n{g} {sn} m/s  n={len(DW)} (jump>=3deg: {len(big)})  dwell_s {f('dwell_s')[0]:.2f}  jump p50 {f('jump')[0]:.2f} p90 {np.percentile([d['jump'] for d in DW],90):.2f} deg"
          f"  |wheel angle| p50 {f('ang')[0]:.1f}  demand rate in dwell p50 {f('dem_rate')[0]:.1f} deg/s  err at break {f('err_deg')[0]:+.2f} deg")
        P(f"   out|end| p50 {f('out_end')[0]:.3f}  dither gate(end) p50 {f('gate_end')[0]:.2f}  gate>0.5 in {np.mean([d['gate_end']>0.5 for d in DW]):.0%}"
          f"  z saturated (dwell frac) p50 {f('z_sat')[0]:.2f}  z_end/F p50 {f('z_end')[0]:+.2f}  move clamp duty {np.mean([d['clamp'] for d in DW]):.2f}"
          f"  ratelim duty {np.mean([d['ratelim'] for d in DW]):.3f}  lsf p50 {f('lsf')[0]:.1f}  obs fade p50 {f('fade')[0]:.2f}")
        P('   term      build p50 [CI]                 level@break p50   share of |build out|')
        bo = np.array([d['b_out'] for d in DW])
        for x in TERMS:
            b = f('b_' + x); l_ = f('l_' + x)
            sh = np.median(np.array([d['b_' + x] for d in DW]) / np.where(np.abs(bo) > 1e-4, bo, np.nan)) if x != 'out' else 1.0
            P(f"   {x:7s}  {b[0]:+.4f} [{b[1]:+.4f},{b[2]:+.4f}]     {l_[0]:+.4f}          {sh:+.2f}")
        if big:
            P('   jump>=3deg subset build p50: ' + '  '.join(f"{x} {np.median([d['b_'+x] for d in big]):+.4f}" for x in TERMS)
              + f"  dwell_s {np.median([d['dwell_s'] for d in big]):.2f}  gate_end {np.median([d['gate_end'] for d in big]):.2f}  out_end {np.median([d['out_end'] for d in big]):.3f}")

P('\n=== SHAKE band 1.8-3.5 Hz, b_eq per term (torque per deg/s, >0 damps), tau 0/30/60 ms; and band rms of each term ===')
for g in GROUPS:
    for k, sn in ((0, '2.5-5'), (1, '5-8'), (2, '8-15')):
        row = {tau: {x: 0.0 for x in TERMS} for tau in ('0', '3', '6')}; den = {tau: 0.0 for tau in ('0', '3', '6')}
        rms = {x: 0.0 for x in TERMS + ['sr']}; sec = 0.0
        for rk, R in A.items():
            if R['g'] != g:
                continue
            for tau in ('0', '3', '6'):
                den[tau] += R['SH'][str(k)][tau]['den']
                for x in TERMS:
                    row[tau][x] += R['SH'][str(k)][tau]['num'][x]
            sec += R['SHrms'][str(k)]['sec']
            for x in TERMS + ['sr']:
                rms[x] += R['SHrms'][str(k)][x]
        if sec < 5:
            continue
        N = sec * 100
        P(f"{g} {sn} ({sec:.0f} s)  band rate rms {np.sqrt(rms['sr']/N):.2f} deg/s")
        P('   ' + '  '.join(f"{x}: b30 {-row['3'][x]/den['3']*1e4:+.2f} (b0 {-row['0'][x]/den['0']*1e4:+.2f}, b60 {-row['6'][x]/den['6']*1e4:+.2f}) rms {np.sqrt(rms[x]/N)*1e3:.2f}" for x in TERMS) + '   [b x1e-4, rms x1e-3]')

P('\n=== FRAME duty, hands-off, per speed bin ===')
for g in GROUPS:
    for k, sn in ((0, '2.5-5'), (1, '5-8'), (2, '8-15')):
        rows = [R['FR'][str(k)] for rk, R in A.items() if R['g'] == g]
        sec = sum(r['sec'] for r in rows)
        if sec < 5:
            continue
        w = lambda key: np.nansum([(r[key] if r[key] is not None else np.nan) * r['sec'] for r in rows]) / sec
        wt = lambda key: np.nansum([(r[key] if r[key] is not None else 0) * r['trans_sec'] for r in rows]) / max(sum(r['trans_sec'] for r in rows), 1e-9)
        P(f"{g} {sn}: {sec:.0f} s (turn |angle_des|>=15: {sum(r['turn_sec'] for r in rows):.0f} s, trans |rate_des|>=40: {sum(r['trans_sec'] for r in rows):.0f} s) "
          f"gate p50~{w('gate_med'):.2f} turn {w('gate_med_turn') if any(r['gate_med_turn'] is not None for r in rows) else float('nan'):.2f} trans {wt('gate_med_trans'):.2f}; gate>0.5 {w('gate_gt05'):.2f}; "
          f"z sat {w('zsat'):.2f} trans {wt('zsat_trans'):.2f}; clamp {w('clamp'):.3f} trans {wt('clamp_trans'):.3f}; ratelim {w('ratelim'):.3f} trans {wt('ratelim_trans'):.3f}; lsf {w('lsf_med'):.1f}; fade {w('fade_med'):.2f}")
        P('    rms all: ' + ' '.join(f"{x} {w('rms_'+x):.3f}" for x in TERMS) + ' | trans: ' + ' '.join(f"{x} {wt('rms_'+x+'_trans'):.3f}" for x in TERMS))
open(HERE / 'out' / 'tables.txt', 'w').write('\n'.join(lines))
