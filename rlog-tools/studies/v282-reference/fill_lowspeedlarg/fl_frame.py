"""fill_lowspeedlarg -- FRAME-LEVEL texture per demand cell (more hands-off data than the 1.28 s blocks) + dwell-then-jump.

Units = contiguous in-cell hands-off stretches (>= 10 frames) inside HO runs (run-level filtering, 0.2 s edge trim).
rms(x) over a group = sqrt(sum of squares / frames) pooled over units.  Two-level route-cluster bootstrap, B = 1000.
Metrics (steer rate = carState steeringRateDeg; 'ang' = derivative of the measured angle, an independent second measure):
  mode_rms      rms 1.8-3 Hz steer rate, deg/s          hf_rms     rms 2-10 Hz steer rate, deg/s
  mode_ang_rms  rms 1.8-3 Hz d(angle)/dt, deg/s         mode_ratio mode_rms / (rms <1 Hz rate + 2)
  dj_per100     dwell-then-jump (s4 definition) per 100 deg of hands-off travel in the cell (route bootstrap only)
Cells: A0 (|dem angle| < 15 and |dem rate| < 10 : quiet baseline), A15/A45/A90 (|dem angle| >= X), R10 (10-40), R40 (>40 deg/s).
"""
import sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE)
import v282cmp as V

HERE = BASE + '/fill_lowspeedlarg'
rng = np.random.default_rng(23)
B = 1000
CN = ['A0', 'A15', 'A45', 'A90', 'R10', 'R40']
VBN = ['2.5-5', '5-8', '8-15']; VB = [2.5, 5, 8, 15]
DOM = '0000006c--2bc842dbac'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
F = {}; DJ = {}
for rk in V.ROUTES:
    D = np.load(f'{HERE}/data/{rk}.npz', allow_pickle=False)
    F[rk] = D['FSEG']; DJ[rk] = D['DJ']
GR = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}
GR['V282pool'] = GR['V282'] + GR['V282old']
GR['V282_LOO'] = [rk for rk in GR['V282'] if rk != DOM]


def dj_count(rk, ci, sb):
    d = DJ[rk]
    if not len(d):
        return 0
    v, dang, drate = d[:, 0], d[:, 1], d[:, 2]
    m = (v >= VB[sb]) & (v < VB[sb + 1])
    cond = {0: (dang < 15) & (drate < 10), 1: dang >= 15, 2: dang >= 45, 3: dang >= 90, 4: (drate >= 10) & (drate < 40), 5: drate >= 40}[ci]
    return int((m & cond).sum())


MET = {  # name: (numerator col, 'rms' | 'ratio')
    'mode_rms': 3, 'hf_rms': 4, 'mode_ang_rms': 6, 'hf_ang_rms': 7, 'mode_ratio': None,
}


def gstat(U, name):
    n = U[:, 2].sum()
    if n <= 0:
        return np.nan
    if name == 'mode_ratio':
        return float(np.sqrt(U[:, 3].sum() / n) / (np.sqrt(U[:, 5].sum() / n) + 2.0))
    return float(np.sqrt(U[:, MET[name]].sum() / n))


res = {}
for ci, cn in enumerate(CN):
    for sb in range(3):
        cell = f'{cn}_{VBN[sb]}'
        R = {}
        for g in GR:
            arrs = [F[rk][(F[rk][:, 0] == ci) & (F[rk][:, 1] == sb)] for rk in GR[g]]
            secs = [float(a[:, 2].sum() / 100) for a in arrs]
            travel = [float(a[:, 8].sum()) for a in arrs]
            djc = [dj_count(rk, ci, sb) for rk in GR[g]]
            arrs_nz = [a for a in arrs if len(a)]
            gr = dict(sec=sum(secs), per_route_sec=dict(zip(GR[g], secs)), n_routes=sum(1 for s in secs if s >= 2), units=int(sum(len(a) for a in arrs)),
                      travel=sum(travel), dj=sum(djc))
            if sum(secs) >= 3 and arrs_nz:
                U = np.concatenate(arrs_nz)
                for name in MET:
                    est = gstat(U, name)
                    reps = np.empty(B)
                    for b in range(B):
                        pick = rng.integers(0, len(arrs_nz), len(arrs_nz))
                        reps[b] = gstat(np.concatenate([arrs_nz[p][rng.integers(0, len(arrs_nz[p]), len(arrs_nz[p]))] for p in pick]), name)
                    gr[name] = est; gr[name + '_reps'] = reps
                # dwell-jump per 100 deg: route bootstrap (single-route groups: Poisson on the count)
                tr = np.array(travel); dc = np.array(djc, float); ok = tr > 0
                gr['dj_per100'] = float(100 * dc.sum() / tr.sum()) if tr.sum() > 0 else np.nan
                if ok.sum() >= 2:
                    reps = []
                    for b in range(B):
                        p = rng.choice(np.where(ok)[0], ok.sum())
                        reps.append(100 * dc[p].sum() / tr[p].sum())
                    gr['dj_per100_reps'] = np.array(reps)
                elif tr.sum() > 0:
                    gr['dj_per100_reps'] = 100 * rng.poisson(max(dc.sum(), 0.5), B) / tr.sum()
            R[g] = gr
        out = {g: {k: v for k, v in gr.items() if not k.endswith('_reps')} for g, gr in R.items()}
        diffs = {}
        for t, r in [(t, r) for t in ['T64', 'T64B', 'T5', 'T4'] for r in ['V282', 'V282old', 'V282pool', 'V282_LOO']] + [('V282old', 'V282')]:
            for name in list(MET) + ['dj_per100']:
                if name + '_reps' in R[t] and name + '_reps' in R[r]:
                    dr = R[t][name + '_reps'] - R[r][name + '_reps']; dr = dr[np.isfinite(dr)]
                    if len(dr) < 100:
                        continue
                    se = float(np.std(dr)); diff = R[t][name] - R[r][name]
                    ratio = R[t][name] / R[r][name] if R[r][name] else np.nan
                    rr = R[t][name + '_reps'] / np.where(R[r][name + '_reps'] == 0, np.nan, R[r][name + '_reps'])
                    rr = rr[np.isfinite(rr)]
                    diffs[f'{t}-{r}|{name}'] = dict(diff=float(diff), ci=[float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))],
                                                     mde80=2.8 * se, effect_over_mde=float(abs(diff) / (2.8 * se)) if se > 0 else None,
                                                     ratio=float(ratio), ratio_ci=[float(np.percentile(rr, 2.5)), float(np.percentile(rr, 97.5))] if len(rr) > 100 else None,
                                                     ref_ok=bool(R[r]['sec'] >= 30 and R[r]['n_routes'] >= (1 if r == 'V282_LOO' else 2)))
        res[cell] = dict(groups=out, diffs=diffs)
        print(cell, {g: (round(out[g]['sec']), round(out[g].get('mode_rms', np.nan), 2), round(out[g].get('mode_ang_rms', np.nan), 2),
                         round(out[g].get('dj_per100', np.nan), 2)) for g in ['V282', 'V282old', 'V282_LOO', 'T64', 'T64B', 'T5', 'T4']}, flush=True)
json.dump(res, open(f'{HERE}/out/frame_texture.json', 'w'), indent=1, default=float)
