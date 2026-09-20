"""classifier stage 2: positive controls, then the full confusion matrix of every classifier in play.

CLASSIFIERS (all evaluated on the SAME 145 torque-mode 2-8 m/s dwell episodes, and on 8-15 for context):
  E  extractor / ss_centring_fit.py:10   depart_E = (sjump == sign(aa_bk))            "the wheel jumped outward"
  R  risk / r_episodes.py:44             depart_R = (sign(aa_bk) == sdem) or |aa_bk|<0.5
  D  reach / reach_intercept.py:115      depart_D = (sign(angdes_bk) == sign(aa_bk))   the 77 % sign-agreement test
  T  the candidate's OWN test            fires_T  = gate(b3) > thr,  gate = max(0, tanh(angdes/1)*tanh(rate_des/2))
  Tm the candidate's own test, dwell-averaged: gate fires on >= 50 % of the dwell's frames
Positive controls, asserted: E reproduces ss_centring_fit's n_toward=93 (depart 52); R reproduces
r_episodes' 58/87; D reproduces reach_intercept's frac_sign_angdes_eq_sign_aa = 0.7655; the rebuilt
angdes_A matches the a_stickslip window channel to < 1e-3 deg rms.
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
sys.path.insert(0, SS)
PRE = 150
rows = json.load(open(f'{OUT}/c1_rows.json'))
N = len(rows)
col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); aa_bk = colf('aa_bk'); sj = colf('sj'); sdem = colf('sdem'); route = col('route')
kind = col('kind'); dwell = colf('dwell_s'); slip = colf('slip'); j30 = colf('j30')
TAG = os.environ.get('TAG', 'A')
ang_bk = colf(f'angdes_bk_{TAG}'); ang_i0 = colf(f'angdes_i0_{TAG}'); rd_bk = colf(f'rd_bk_{TAG}')
gate_bk = colf(f'gate_bk_{TAG}'); gate_frac = colf(f'gate_frac_{TAG}')
dose_bk = colf(f'dose_bk_{TAG}'); dose_mean = colf(f'dose_mean_{TAG}'); dose_out = colf(f'dose_out_{TAG}')

# ---------------- positive control 1: angdes_A vs the a_stickslip window channel ----------------
import glob
err = []
for f in sorted(glob.glob(f'{SS}/out/*_ss.npz')):
    rk = os.path.basename(f)[:-7]
    if not os.path.exists(f'{OUT}/{rk}_cls.npz'):
        continue
    D = np.load(f, allow_pickle=True); C = np.load(f'{OUT}/{rk}_cls.npz')
    EP = list(D['EP'])
    for q, e in enumerate(EP):
        bk = int(e['bk'])
        err.append(D['angdes'][q, PRE] - C['angdes_A'][bk])
err = np.array(err)
CTRL = {'angdes_A_vs_ss_window_rms_deg': float(np.sqrt(np.mean(err ** 2))), 'n': int(len(err))}
assert CTRL['angdes_A_vs_ss_window_rms_deg'] < 1e-3, CTRL  # tag-independent: always checks angdes_A

# ---------------- the classifiers ----------------
sgn_aa = np.sign(aa_bk)
dep = {
    'E': sj == sgn_aa,
    'R': (sgn_aa == sdem) | (np.abs(aa_bk) < 0.5),
    'D': np.sign(ang_bk) == sgn_aa,
    'T': gate_bk > 1e-3,
    'Tm': gate_frac >= 0.5,
    'T10': gate_bk > 0.10,
}
LOW = (v >= 2) & (v < 8)
MID = (v >= 8) & (v < 15)
CTRL['E_depart_2_8'] = int(dep['E'][LOW].sum()); CTRL['E_return_2_8'] = int((~dep['E'])[LOW].sum())
CTRL['R_depart_2_8'] = int(dep['R'][LOW].sum()); CTRL['R_return_2_8'] = int((~dep['R'])[LOW].sum())
CTRL['D_agree_2_8'] = float(dep['D'][LOW].mean()); CTRL['D_agree_8_15'] = float(dep['D'][MID].mean())
CTRL['n_2_8'] = int(LOW.sum()); CTRL['n_8_15'] = int(MID.sum())
assert (CTRL['E_depart_2_8'], CTRL['E_return_2_8']) == (52, 93), CTRL
assert (CTRL['R_depart_2_8'], CTRL['R_return_2_8']) == (58, 87), CTRL
assert TAG != 'A' or abs(CTRL['D_agree_2_8'] - 0.7655) < 0.002, CTRL
print('POSITIVE CONTROLS', json.dumps(CTRL, indent=1))

R = dict(controls=CTRL, tag=TAG)
BINS = [('2-5', 2.0, 5.0), ('5-8', 5.0, 8.0), ('2-8', 2.0, 8.0), ('8-15', 8.0, 15.0)]

R['marginals'] = {}
for bn, v0, v1 in BINS:
    m = (v >= v0) & (v < v1)
    R['marginals'][bn] = dict(n=int(m.sum()), **{f'depart_{k}': int(dep[k][m].sum()) for k in dep},
                              **{f'frac_{k}': float(dep[k][m].mean()) for k in dep})

R['confusion'] = {}
PAIRS = [('E', 'R'), ('E', 'D'), ('E', 'T'), ('E', 'Tm'), ('R', 'T'), ('R', 'Tm'), ('D', 'T'), ('R', 'D'), ('T', 'Tm')]
for bn, v0, v1 in BINS:
    m = (v >= v0) & (v < v1)
    for a, b in PAIRS:
        A, B = dep[a][m], dep[b][m]
        R['confusion'][f'{bn}|{a}_vs_{b}'] = dict(
            n=int(m.sum()), dep_dep=int((A & B).sum()), dep_ret=int((A & ~B).sum()),
            ret_dep=int((~A & B).sum()), ret_ret=int((~A & ~B).sum()),
            agree=float(np.mean(A == B)), kappa=None)


def kappa(A, B):
    po = np.mean(A == B)
    pe = np.mean(A) * np.mean(B) + (1 - np.mean(A)) * (1 - np.mean(B))
    return float((po - pe) / (1 - pe)) if pe < 1 else None


for k in R['confusion']:
    bn, pr = k.split('|'); a, b = pr.split('_vs_')
    v0, v1 = dict((x[0], (x[1], x[2])) for x in BINS)[bn]
    m = (v >= v0) & (v < v1)
    R['confusion'][k]['kappa'] = kappa(dep[a][m], dep[b][m])

# ---------------- dose the term actually puts on each class ----------------
R['dose'] = {}
for bn, v0, v1 in BINS:
    m = (v >= v0) & (v < v1)
    for cl in ['E', 'R']:
        for nm, sel in (('depart', dep[cl]), ('return', ~dep[cl])):
            mm = m & sel
            if mm.sum() < 3:
                continue
            R['dose'][f'{bn}|{cl}|{nm}'] = dict(
                n=int(mm.sum()),
                dose_bk_p50=float(np.median(dose_bk[mm])), dose_bk_p90=float(np.percentile(dose_bk[mm], 90)),
                dose_bk_p10=float(np.percentile(dose_bk[mm], 10)),
                dose_mean_p50=float(np.median(dose_mean[mm])),
                dose_out_p50=float(np.median(dose_out[mm])),
                frac_fires=float(np.mean(gate_bk[mm] > 1e-3)),
                frac_fires_hard=float(np.mean(gate_bk[mm] > 0.10)),
                frac_dose_ge_25pct=float(np.mean(dose_bk[mm] >= 0.25 * 0.020)),
                frac_dose_ge_50pct=float(np.mean(dose_bk[mm] >= 0.50 * 0.020)),
                frac_dose_le_m25pct=float(np.mean(dose_bk[mm] <= -0.25 * 0.020)),
                gate_frac_p50=float(np.median(gate_frac[mm])))

json.dump(R, open(f'{OUT}/c2_confusion_{TAG}.json', 'w'), indent=1)

W = 'n dep_dep dep_ret ret_dep ret_ret agree kappa'.split()
print(f'\n=== CONFUSION (tag {TAG}; dep=depart/fires, ret=return/silent) ===')
print(f'{"bin|pair":22s}' + ''.join(f'{x:>9s}' for x in W))
for k, d in R['confusion'].items():
    print(f'{k:22s}' + ''.join(f'{d[x]:9.3f}' if isinstance(d[x], float) else f'{d[x]:9d}' if d[x] is not None else f'{"-":>9s}' for x in W))
print('\n=== MARGINALS ===')
for bn, d in R['marginals'].items():
    print(bn, d['n'], {k[7:]: (d[k], round(d['frac_' + k[7:]], 3)) for k in d if k.startswith('depart_')})
print('\n=== DOSE ON EACH CLASS ===')
kk = 'n frac_fires frac_fires_hard dose_bk_p50 dose_bk_p90 dose_bk_p10 dose_mean_p50 frac_dose_ge_25pct frac_dose_ge_50pct'.split()
print(f'{"bin|cls|grp":22s}' + ''.join(f'{x:>12s}' for x in kk))
for k, d in R['dose'].items():
    print(f'{k:22s}' + ''.join(f'{d[x]:12.4f}' if isinstance(d[x], float) else f'{d[x]:12d}' for x in kk))
