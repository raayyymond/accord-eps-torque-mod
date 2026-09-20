"""risk stream, stage 4: interactions and construction checks.

1. DITHER GATE.  get_honda_accord_dither_gate = clip(1 - |output_torque| / 0.15, 0, 1) and |output_torque| = |cs_out|.
   z enters the +left command additively (F_t = hold + move + z + rl + dob_left), so cmd_cand = cmd + dz.
   Measures the gate's mean/closed fraction, flown vs candidate, on low-speed engaged hands-off frames.
2. HIGHWAY LEAK, the STATE-CARRY part: a candidate whose parameters are identical above a knot still differs
   in z above it, because z is a carried state.  Reported as dz != 0 fraction and max |dz| per speed bin.
3. TRANSITION SLEW: with a speed-scheduled ceiling, accelerating through the knots drags z down at
   d(ceiling)/dv * dv/dt.  Measured from the logged dv/dt.
4. COMMAND HEADROOM: |cmd + dz| against the 1.0 rail and against the flown p99, at low speed.
"""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
CAND = ['C0_flown', 'C1_toggle_030', 'C2_lvl033_k12', 'C3_band110', 'C4_reach_k12', 'C5_half_k12', 'C6_reach_k68']
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
REF = 0.15
BINS = [('2-8', 2.0, 8.0), ('8-12', 8.0, 12.0), ('12-15', 12.0, 15.0), ('15-22', 15.0, 22.0), ('22+', 22.0, 99.0)]

A = {}
for rk in ROUTES:
    D = np.load(f'{OUT}/{rk}_z.npz')
    v, HO, cmd = D['v'], D['HO'], np.nan_to_num(D['cmd'])
    dvdt = np.gradient(v, 0.01)
    for bn, v0, v1 in BINS:
        m = HO & (v >= v0) & (v < v1)
        if m.sum() < 200:
            continue
        e = A.setdefault(bn, dict(sec=0.0, dvdt=[], cand={c: dict(gate=[], cmd=[], dz=[], dzdt=[]) for c in CAND}))
        e['sec'] += m.sum() / 100.0
        e['dvdt'].append(np.abs(dvdt[m]))
        for c in CAND:
            dz = D[c] - D['C0_flown']
            e['cand'][c]['gate'].append(np.clip(1.0 - np.abs(cmd[m] + dz[m]) / REF, 0.0, 1.0))
            e['cand'][c]['cmd'].append(np.abs(cmd[m] + dz[m]))
            e['cand'][c]['dz'].append(dz[m])
            e['cand'][c]['dzdt'].append(np.abs(np.gradient(dz, 0.01))[m])
    del D

res = {}
print(f'{"bin":7s}{"sec":>7s}{"cand":15s}{"gate_mean":>10s}{"gate=0 %":>9s}{"|cmd|p50":>9s}{"|cmd|p99":>9s}'
      f'{"dz!=0 %":>8s}{"|dz|max":>8s}{"|dz/dt|p99":>11s}')
for bn, e in A.items():
    dv = np.concatenate(e['dvdt'])
    for c in CAND:
        g = np.concatenate(e['cand'][c]['gate']); cm = np.concatenate(e['cand'][c]['cmd'])
        dz = np.concatenate(e['cand'][c]['dz']); dzdt = np.concatenate(e['cand'][c]['dzdt'])
        row = dict(sec=e['sec'], gate_mean=float(g.mean()), gate_closed=float(np.mean(g <= 0)),
                   cmd_p50=float(np.percentile(cm, 50)), cmd_p99=float(np.percentile(cm, 99)),
                   dz_nonzero=float(np.mean(np.abs(dz) > 1e-6)), dz_absmax=float(np.abs(dz).max()),
                   dzdt_p99=float(np.percentile(dzdt, 99)), dvdt_p95=float(np.percentile(dv, 95)))
        res[f'{bn}|{c}'] = row
        print(f'{bn:7s}{e["sec"]:7.0f}{c:15s}{row["gate_mean"]:10.3f}{100*row["gate_closed"]:9.1f}'
              f'{row["cmd_p50"]:9.4f}{row["cmd_p99"]:9.4f}{100*row["dz_nonzero"]:8.1f}{row["dz_absmax"]:8.4f}'
              f'{row["dzdt_p99"]:11.4f}')
    print(f'       dv/dt p95 = {np.percentile(dv,95):.2f} m/s^2')
json.dump(res, open(f'{OUT}/r_interact.json', 'w'), indent=1)
