"""classifier stage 3: the CONSEQUENCE for the readout.

The pre-registered FAIL numbers are REPRODUCED first, so it is certain which classifier and which
overshoot definition they came from:
  risk/r_overshoot.py            depart = (sign(aa_bk)==sdem) or |aa_bk|<0.5      [classifier R]
  os30 = sj * (aa[PRE+30] - ad[PRE+30])      ad = the group-identical model demand angle (NOT angdes)
  -> V293 2-8: depart n=58 dwell 0.415 os30_p90 1.681 ; return n=87 dwell 0.510 os30_p90 3.203
     V282 2-8: depart os30_p90 1.779 ; return os30_p90 1.058          (asserted below)
ss_analyze.py section 7's over30 (angdes-based, gap-subtracted) is also reported as os30_ss for contrast.

Then the same statistics on every classifier's return class, and on the return class SPLIT by whether the
candidate's own gate would have dosed the episode -- which is the question the null control turns on.
Route-cluster bootstrap, seed fixed.
"""
import os, sys, json, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
PRE = 150
TAG = os.environ.get('TAG', 'A')
LEVEL = 0.020

rows = json.load(open(f'{OUT}/c1_rows.json'))
key = {(r['route'], r['i0'], r['bk']): q for q, r in enumerate(rows)}
N = len(rows)
os30 = np.full(N, np.nan); os70 = np.full(N, np.nan); os30_ss = np.full(N, np.nan)
# V282 reference rows are NOT in c1_rows (no torque term there); collected separately
v282 = []
for f in sorted(glob.glob(f'{SS}/out/*_ss.npz')):
    D = np.load(f, allow_pickle=True)
    EP = list(D['EP'])
    if not EP:
        continue
    aa = D['aa']; ad = D['ad']; angd = D['angdes']
    for q, e in enumerate(EP):
        sj = float(e['sjump'])
        o30 = sj * (aa[q, PRE + 30] - ad[q, PRE + 30])
        o70 = sj * (aa[q, PRE + 70] - ad[q, PRE + 70])
        gapdes = (angd[q, PRE] - aa[q, PRE]) * sj
        oss = (aa[q, PRE + 30] - aa[q, PRE]) * sj - (angd[q, PRE + 30] - angd[q, PRE]) * sj - gapdes
        kk = (e['route'], int(e['i0']), int(e['bk']))
        if kk in key:
            i = key[kk]; os30[i] = o30; os70[i] = o70; os30_ss[i] = oss
        elif str(e['group']) == 'V282':
            v282.append(dict(v=float(e['v']), dwell=float(e['dwell_s']), os30=o30, os70=o70, route=str(e['route']),
                             depart=bool((np.sign(e['aa']) == e['sdem']) or abs(e['aa']) < 0.5)))
    del D

col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); aa_bk = colf('aa_bk'); sj = colf('sj'); sdem = colf('sdem'); dwell = colf('dwell_s')
slip = colf('slip'); j30 = colf('j30'); kind = col('kind'); route = col('route'); pk = colf('pk_rate')
ang_bk = colf(f'angdes_bk_{TAG}'); gate_bk = colf(f'gate_bk_{TAG}'); gate_frac = colf(f'gate_frac_{TAG}')
dose_bk = colf(f'dose_bk_{TAG}'); dose_out = colf(f'dose_out_{TAG}')
sgn_aa = np.sign(aa_bk)
dep = {'E': sj == sgn_aa, 'R': (sgn_aa == sdem) | (np.abs(aa_bk) < 0.5),
       'D': np.sign(ang_bk) == sgn_aa, 'T': gate_bk > 1e-3, 'Tm': gate_frac >= 0.5}
DOSED = np.abs(dose_bk) >= 0.25 * LEVEL

# ---------------- positive control: reproduce the pre-registered numbers ----------------
LOW = (v >= 2) & (v < 8)
p90 = lambda x: np.percentile(x, 90)
C = {}
for nm, m in (('depart', LOW & dep['R']), ('return', LOW & ~dep['R'])):
    C[f'V293_{nm}'] = dict(n=int(m.sum()), dwell_p50=round(float(np.median(dwell[m])), 4),
                           os30_p90=round(float(p90(os30[m])), 4), os30_p50=round(float(np.median(os30[m])), 4))
vv = np.array([r['v'] for r in v282]); vdep = np.array([r['depart'] for r in v282])
vo = np.array([r['os30'] for r in v282]); vd = np.array([r['dwell'] for r in v282])
vm = (vv >= 2) & (vv < 8)
for nm, m in (('depart', vm & vdep), ('return', vm & ~vdep)):
    C[f'V282_{nm}'] = dict(n=int(m.sum()), dwell_p50=round(float(np.median(vd[m])), 4),
                           os30_p90=round(float(p90(vo[m])), 4))
print('POSITIVE CONTROLS (pre-registered numbers reproduced):', json.dumps(C, indent=1))
assert C['V293_return']['n'] == 87 and abs(C['V293_return']['dwell_p50'] - 0.51) < 1e-6
assert abs(C['V293_return']['os30_p90'] - 3.203) < 0.002, C
assert abs(C['V293_depart']['os30_p90'] - 1.681) < 0.002, C
assert abs(C['V282_return']['os30_p90'] - 1.058) < 0.002 and abs(C['V282_depart']['os30_p90'] - 1.779) < 0.002, C


def boot(vals, clusters, fn, nb=2000, seed=0):
    vals = np.asarray(vals, float); clusters = np.asarray(clusters)
    ok = np.isfinite(vals); vals, clusters = vals[ok], clusters[ok]
    if len(vals) < 3:
        return None
    u = np.unique(clusters); rng = np.random.default_rng(seed)
    idx = {c: np.where(clusters == c)[0] for c in u}
    bs = [fn(vals[np.concatenate([idx[c] for c in rng.choice(u, len(u))])]) for _ in range(nb)]
    return [float(fn(vals)), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]]


p50 = np.median
GROUPS = []
for cl in ['E', 'R', 'D', 'T', 'Tm']:
    GROUPS += [(f'{cl}:depart', LOW & dep[cl]), (f'{cl}:return', LOW & ~dep[cl])]
GROUPS += [('R:return_CLEAN', LOW & ~dep['R'] & ~DOSED), ('R:return_DOSED', LOW & ~dep['R'] & DOSED),
           ('E:return_CLEAN', LOW & ~dep['E'] & ~DOSED), ('E:return_DOSED', LOW & ~dep['E'] & DOSED),
           ('R:depart_DOSED', LOW & dep['R'] & DOSED), ('R:depart_UNDOSED', LOW & dep['R'] & ~DOSED),
           ('ALL_low', LOW)]
R = {'tag': TAG, 'controls': C, 'groups': {}}
print(f'\n{"group":20s}{"n":>4s}{"frac_dosed":>11s}{"dwell_p50":>22s}{"os30_p90":>22s}{"os30_p50":>22s}{"os30ss_p90":>22s}')
for nm, m in GROUPS:
    if m.sum() < 3:
        print(f'{nm:20s}{int(m.sum()):4d}  (too few)'); continue
    d = dict(n=int(m.sum()), frac_dosed=float(np.mean(DOSED[m])),
             dwell_p50=boot(dwell[m], route[m], p50), os30_p90=boot(os30[m], route[m], p90),
             os30_p50=boot(os30[m], route[m], p50), os30ss_p90=boot(os30_ss[m], route[m], p90),
             os70_p50=boot(os70[m], route[m], p50), slip_p50=boot(slip[m], route[m], p50),
             pk_p50=boot(pk[m], route[m], p50), frac_past30=float(np.mean(os30[m] > 0)),
             dose_bk_p50=float(np.median(dose_bk[m])), dose_bk_p90=float(np.percentile(dose_bk[m], 90)),
             abs_aa_p50=float(np.median(np.abs(aa_bk[m]))), v_p50=float(np.median(v[m])),
             frac_kind=dict(rest=float(np.mean(kind[m] == 'rest')), cont=float(np.mean(kind[m] == 'cont')),
                            rev=float(np.mean(kind[m] == 'rev'))))
    R['groups'][nm] = d
    f_ = lambda x: f'{x[0]:7.3f} [{x[1][0]:6.3f},{x[1][1]:6.3f}]' if x else '         -            '
    print(f'{nm:20s}{d["n"]:4d}{d["frac_dosed"]:11.3f}  {f_(d["dwell_p50"])}  {f_(d["os30_p90"])}  {f_(d["os30_p50"])}  {f_(d["os30ss_p90"])}')

# ---- how much of the return class's p90 is carried by dosed episodes? ----
R['leverage'] = {}
for cl in ['R', 'E']:
    m = LOW & ~dep[cl]
    o = os30[m][np.isfinite(os30[m])]; dd = DOSED[m][np.isfinite(os30[m])]
    top = o >= np.percentile(o, 90)
    R['leverage'][cl] = dict(n=int(m.sum()), n_dosed=int(dd.sum()),
                             frac_of_top10pct_that_are_dosed=float(np.mean(dd[top])),
                             p90_all=float(np.percentile(o, 90)), p90_clean=float(np.percentile(o[~dd], 90)),
                             p90_dosed=float(np.percentile(o[dd], 90)) if dd.sum() >= 3 else None,
                             dwell_p50_all=float(np.median(dwell[m])),
                             dwell_p50_clean=float(np.median(dwell[m][~DOSED[m]])),
                             dwell_p50_dosed=float(np.median(dwell[m][DOSED[m]])))
print('\n=== LEVERAGE of the dosed episodes inside the return class ===')
print(json.dumps(R['leverage'], indent=1))
json.dump(R, open(f'{OUT}/c3_consequence_{TAG}.json', 'w'), indent=1)
