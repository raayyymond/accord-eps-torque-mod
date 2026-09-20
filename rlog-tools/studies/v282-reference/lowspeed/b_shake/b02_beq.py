"""b02: energy attribution of each command term to the 1.5-3.5 Hz wheel rate, per route, per speed bin.
b_eq(tau) = -<T(t - tau), rate(t)> / <rate, rate>, both band-passed (4th-order Butterworth, zero-phase, whole run then 1 s
trimmed). >0 = the term opposes the rate after tau (damps); <0 = pushes with it (feeds). Units: output per deg/s.
POSITIVE CONTROL: ctrl = -1e-3 * steeringRateDeg must read +1.000e-3 at tau 0.
Replica validation per bin: logged P, I, F vs replica sums, and replica dob vs LOGGED observer (sign: contribution = -logged).
CIs: 5 s block bootstrap within group (blocks resampled), plus per-route values (route-cluster spread)."""
import json
import numpy as np
import bs
TAUS = [0, 3, 6]
TERMS = ['u_log', 'u_e4', 'p_log', 'i_log', 'f_log', 'dob_log', 'dob', 'hold', 'move', 'hyst', 'rl', 'rl_ff', 'rl_fb',
         'p_sp', 'p_meas', 'ffwd', 'fbk', 'ctrl']
acc = []   # rows: route, run, block, bin, secs, rr, {term: [Tr at taus]}
val = {}
for rk, g in bs.TORQUE.items():
    D = bs.load_torque(rk)
    D['rl'] = D['rl_ff'] + D['rl_fb']
    D['ctrl'] = -1e-3 * D['sr']
    if 'dob_log' not in D:
        D['dob_log'] = np.zeros_like(D['t'])
    D['ffwd'] = D['hold'] + D['move'] + D['hyst'] + D['rl_ff'] + D['p_sp']
    D['fbk'] = D['p_meas'] + D['i'] + D['rl_fb'] + D['dob_log']
    fin = np.ones(len(D['t']), bool)
    for k in TERMS + ['sr', 'v']:
        fin &= np.isfinite(D[k])
    m = (D['usable'] > 0.5) & fin & (D['v'] < 15)
    # replica validation accumulators per bin (band-passed)
    vv = {b[2]: {k: [0.0, 0.0, 0.0] for k in ('P', 'I', 'F', 'dob', 'sum')} for b in bs.BINS}
    for ri, (a, b) in enumerate(bs.V.runs(m, D['t'], min_s=4.0)):
        B = {k: bs.bp(D[k][a:b]) for k in TERMS + ['sr']}
        rep = {'P': (D['p_sp'][a:b] + D['p_meas'][a:b], D['p_log'][a:b]), 'I': (D['i'][a:b], D['i_log'][a:b]),
               'F': (D['hold'][a:b] + D['move'][a:b] + D['hyst'][a:b] + D['rl'][a:b] + D['dob_log'][a:b], D['f_log'][a:b]),
               'dob': (D['dob'][a:b], D['dob_log'][a:b]),
               'sum': (D['p_log'][a:b] + D['i_log'][a:b] + D['f_log'][a:b], D['u_log'][a:b])}
        repB = {k: (bs.bp(x), bs.bp(y)) for k, (x, y) in rep.items()}
        e = 100
        n = b - a
        if n - 2 * e < 100:
            continue
        v = D['v'][a:b]
        for j0 in range(e, n - e, 500):
            j1 = min(j0 + 500, n - e)
            if j1 - j0 < 100:
                continue
            for lo, hi, lab in bs.BINS:
                sel = np.arange(j0, j1)[(v[j0:j1] >= lo) & (v[j0:j1] < hi)]
                if len(sel) < 20:
                    continue
                r = B['sr'][sel]
                row = dict(route=rk, g=g, run=ri, blk=j0, bin=lab, secs=len(sel) / 100, rr=float(r @ r))
                for k in TERMS:
                    row[k] = [float(B[k][sel - tau] @ r) for tau in TAUS]
                acc.append(row)
                for k, (x, y) in repB.items():
                    vv[lab][k][0] += float(x[sel] @ y[sel]); vv[lab][k][1] += float(x[sel] @ x[sel]); vv[lab][k][2] += float(y[sel] @ y[sel])
    val[rk] = {lab: {k: dict(corr=c[0] / np.sqrt(max(c[1] * c[2], 1e-30)), slope=c[0] / max(c[1], 1e-30)) for k, c in d.items()} for lab, d in vv.items()}
    print(rk, g, {lab: {k: round(x['corr'], 3) for k, x in d.items()} for lab, d in val[rk].items()}, flush=True)
    del D
json.dump(val, open(bs.OUT + 'b02_validation.json', 'w'), indent=1)
json.dump(acc, open(bs.OUT + 'b02_rows.json', 'w'))
print('rows', len(acc))
