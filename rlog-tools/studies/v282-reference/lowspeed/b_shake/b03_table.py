"""b03: b_eq table per group x bin x term at tau 0/30/60 ms, block-bootstrap 95% CI and per-route values."""
import json
import numpy as np
import bs
rows = json.load(open(bs.OUT + 'b02_rows.json'))
TERMS = ['ctrl', 'u_log', 'u_e4', 'p_log', 'i_log', 'f_log', 'dob_log', 'hold', 'move', 'hyst', 'rl', 'rl_ff', 'rl_fb',
         'p_sp', 'p_meas', 'ffwd', 'fbk']
GROUPS = {'rev64(T64+T64B)': ('T64', 'T64B'), 'T64': ('T64',), 'T64B': ('T64B',), 'T5': ('T5',), 'T4': ('T4',),
          'obs-on(T64,T64B,T5)': ('T64', 'T64B', 'T5')}
rng = np.random.default_rng(0)
RES = {}


def est(sub):
    rr = sum(r['rr'] for r in sub)
    return {k: [-sum(r[k][i] for r in sub) / rr for i in range(3)] for k in TERMS}


lines = []
for gname, gs in GROUPS.items():
    for lo, hi, lab in bs.BINS:
        sub = [r for r in rows if r['g'] in gs and r['bin'] == lab]
        if len(sub) < 5:
            continue
        secs = sum(r['secs'] for r in sub)
        rms = np.sqrt(sum(r['rr'] for r in sub) / (secs * 100))
        E = est(sub)
        B = []
        for _ in range(500):
            pick = [sub[i] for i in rng.integers(0, len(sub), len(sub))]
            B.append(est(pick))
        ci = {k: [[float(np.percentile([b[k][i] for b in B], q)) for q in (2.5, 97.5)] for i in range(3)] for k in TERMS}
        per_route = {}
        for rk in sorted(set(r['route'] for r in sub)):
            s2 = [r for r in sub if r['route'] == rk]
            if sum(r['secs'] for r in s2) >= 20:
                per_route[rk[:8]] = {k: v[1] for k, v in est(s2).items()}
        RES[f'{gname}|{lab}'] = dict(secs=secs, band_rms=float(rms), nblk=len(sub), est=E, ci=ci, per_route=per_route)
        lines.append(f"\n=== {gname} | v {lab} m/s : {secs:.0f} s, {len(sub)} blocks, 1.5-3.5 Hz rate rms {rms:.2f} deg/s")
        lines.append(f"   {'term':8s} {'beq@0':>9s} {'beq@30':>9s} {'CI@30':>22s} {'beq@60':>9s}   per-route @30")
        for k in TERMS:
            pr = ' '.join(f"{x[k]*1e4:+.2f}" for x in per_route.values())
            lines.append(f"   {k:8s} {E[k][0]*1e4:+9.2f} {E[k][1]*1e4:+9.2f} [{ci[k][1][0]*1e4:+8.2f},{ci[k][1][1]*1e4:+8.2f}] {E[k][2]*1e4:+9.2f}   {pr}")
open(bs.OUT + 'b03_table.txt', 'w').write('units x1e-4 output per deg/s; >0 damps, <0 feeds\n' + '\n'.join(lines))
json.dump(RES, open(bs.OUT + 'b03_table.json', 'w'), indent=1)
print('\n'.join(lines))
