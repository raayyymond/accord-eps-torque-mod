"""t10: natural experiment across flown configs, at MATCHED speed x |angle| x activity cells.

Per 2.56 s window (t03): band (1.5-3.5 Hz) rms of the wheel rate, of the setpoint (planner content that reaches the FF),
of FF torque, and of each FB term.  Cells: speed {3-8, 8-15, 15-22, 22+} x median |angle| {<5, 5-15, >=15} x activity
tercile (std of the <1 Hz wheel rate in the window, terciles over all windows).  For each group vs T64 (rev 6.4 as shipped):
per-cell ratio of median band-rate rms, combined as a count-weighted geometric mean over cells both groups populate
(>= 6 windows each), bootstrap over runs.

What each contrast can and cannot isolate (flown toggles, t01; code constants, git show):
  T64B vs T64 : AccordHoldLevel only (hold map x1.15-1.45 above 12.5 m/s, and the observer's model level).  Different day/roads.
  T5  vs T64  : AccordRefFilter 0.12 -> 0.06, jerk LP 1.2 -> 4.0 Hz (rev 6), hysteresis band scheduled, hold level on, rev 6.1-6.3 code.
  T4  vs T5   : observer OFF (AccordDobHz absent), rate loop 0.0006 with RC 0.03 s (vs 0.001 / 0.01), Ki 0.6 -> 2.5 schedule, Kp 0.85.
SteerFriction differs (0.212 on 6d and 75) but is INERT: friction_torque = 0 whenever AccordFrictionHyst > 0 (0.015 on all).
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402

D = np.load(ttd.OUT + 't03_win.npz')
f = D['f']; B = (f >= 1.5) & (f <= 3.55)
rms = lambda k: np.sqrt(np.sum(np.abs(D['X_' + k][:, B]) ** 2, 1)) * np.sqrt(2) / 256 * np.sqrt(8 / 3)
M = {k: rms(k) for k in ('r', 'setpoint', 'ff', 'fb', 'dob', 'rl_fb', 'p_meas', 'move', 'u_e4')}
route = D['L_route']; run = D['L_run']; v = D['L_v']; aa = D['L_absang']; act = D['L_lf_rate']
GROUP = np.array([{0: 'T64', 1: 'T64', 2: 'T64B', 3: 'T5', 4: 'T4'}[r] for r in route])
t1, t2 = np.percentile(act, [33.3, 66.7])
vb = np.digitize(v, [8, 15, 22]); ab = np.digitize(aa, [5, 15]); cb = np.digitize(act, [t1, t2])
cell = vb * 9 + ab * 3 + cb
VB = ['3-8', '8-15', '15-22', '22+']; AB = ['<5', '5-15', '>=15']; CB = ['low', 'mid', 'high']


def contrast(gA, gB, key='r', idxA=None, idxB=None):
    ia = np.where(GROUP == gA)[0] if idxA is None else idxA
    ib = np.where(GROUP == gB)[0] if idxB is None else idxB
    logs, ws = [], []
    for c in np.unique(cell):
        a = ia[cell[ia] == c]; b = ib[cell[ib] == c]
        if len(a) < 6 or len(b) < 6:
            continue
        logs.append(np.log(np.median(M[key][a]) / np.median(M[key][b]))); ws.append(min(len(a), len(b)))
    if not logs:
        return None, 0
    return float(np.exp(np.average(logs, weights=ws))), len(logs)


def boot(gA, gB, key, nb=300, seed=0, vsel=None):
    rng = np.random.default_rng(seed)
    base_a = np.where((GROUP == gA) & (vsel if vsel is not None else True))[0]
    base_b = np.where((GROUP == gB) & (vsel if vsel is not None else True))[0]
    ra = np.unique(run[base_a]); rb = np.unique(run[base_b])
    byr = {u: np.where(run == u)[0] for u in np.concatenate([ra, rb])}
    est, n = contrast(gA, gB, key, base_a, base_b)
    bs = []
    for _ in range(nb):
        ia = np.concatenate([np.intersect1d(byr[u], base_a) for u in rng.choice(ra, len(ra))])
        ib = np.concatenate([np.intersect1d(byr[u], base_b) for u in rng.choice(rb, len(rb))])
        q, _ = contrast(gA, gB, key, ia, ib)
        if q:
            bs.append(q)
    return dict(ratio=est, cells=n, ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else None)


RES = {}
for vs_name, vs in (('all', np.ones(len(v), bool)), ('lt15', v < 15), ('ge15', v >= 15)):
    RES[vs_name] = {}
    for gA, gB in (('T64B', 'T64'), ('T5', 'T64'), ('T4', 'T64'), ('T4', 'T5')):
        RES[vs_name][f'{gA}/{gB}'] = {k: boot(gA, gB, k, vsel=vs) for k in ('r', 'setpoint', 'ff', 'fb', 'move', 'dob', 'rl_fb', 'p_meas')}
        r = RES[vs_name][f'{gA}/{gB}']
        fmt = lambda q: f"{q['ratio']:.2f} [{q['ci'][0]:.2f},{q['ci'][1]:.2f}]" if q['ratio'] and q['ci'] else 'n/a'
        print(f"{vs_name:5s} {gA}/{gB}: cells {r['r']['cells']:2d}  RATE {fmt(r['r'])}  setpoint {fmt(r['setpoint'])}  FF {fmt(r['ff'])}  move {fmt(r['move'])}  FB {fmt(r['fb'])}  rl_fb {fmt(r['rl_fb'])}  p_meas {fmt(r['p_meas'])}")
# absolute per-cell table
TAB = []
for c in np.unique(cell):
    row = dict(v=VB[c // 9], ang=AB[(c // 3) % 3], act=CB[c % 3])
    for gname in ('T64', 'T64B', 'T5', 'T4'):
        i = np.where((cell == c) & (GROUP == gname))[0]
        row[gname] = dict(n=int(len(i)), rate=float(np.median(M['r'][i])) if len(i) else None, setpoint=float(np.median(M['setpoint'][i])) if len(i) else None,
                          ff=float(np.median(M['ff'][i])) if len(i) else None, fb=float(np.median(M['fb'][i])) if len(i) else None)
    TAB.append(row)
RES['cells'] = TAB
print(f"\n{'v':6s}{'ang':6s}{'act':5s}" + ''.join(f"{g:>26s}" for g in ('T64', 'T64B', 'T5', 'T4')) + "   (n, rate rms deg/s, setpoint rms m/s2)")
for row in TAB:
    print(f"{row['v']:6s}{row['ang']:6s}{row['act']:5s}" + ''.join(
        (f"{row[g]['n']:6d} {row[g]['rate']:7.2f} {row[g]['setpoint']:.4f}   " if row[g]['n'] else f"{'-':>26s}") for g in ('T64', 'T64B', 'T5', 'T4')))
json.dump(RES, open(ttd.OUT + 't10_natural_expt.json', 'w'), indent=1)
