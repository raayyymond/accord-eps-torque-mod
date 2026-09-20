"""classifier stage 7: separate the two disagreement MECHANISMS, and cost the recommended readout split.

MECHANISM 1  near-centre sign noise: |aa| is a few tenths of a degree, so sign(aa) -- and therefore
             "outward" in the wheel's frame, and the extractor's depart/return test itself -- is noise.
MECHANISM 2  genuine opposite-side geometry: the wheel is stuck several degrees one way while the demand
             has crossed centre the other way.  A firing term then adds torque INTO the reversal.

Then the recommended readout: a THREE-WAY partition that is exhaustive, defined on quantities the drive
logs anyway, and whose treated class is the term's own gate:
  DOSED   = gate(b3) > 1e-3 and |dose| >= 0.25 * level        (the term acted on this release)
  NULL    = gate silent through the whole dwell                (a true untouched control)
  MIXED   = gate fired somewhere in the dwell but not at release, or dose < 25 % of level
and, cross-cut, AMBIGUOUS = |aa_bk| < 1.0 deg (where depart/return has no physical content).
"""
import os, json, glob
import numpy as np
from scipy import signal, ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
PRE = 150
LEVEL = 0.020
rows = json.load(open(f'{OUT}/c1_rows.json'))
key = {(r['route'], r['i0'], r['bk']): q for q, r in enumerate(rows)}
N = len(rows)
os30 = np.full(N, np.nan)
for f in sorted(glob.glob(f'{SS}/out/*_ss.npz')):
    D = np.load(f, allow_pickle=True); EP = list(D['EP'])
    if not EP:
        continue
    for q, e in enumerate(EP):
        kk = (e['route'], int(e['i0']), int(e['bk']))
        if kk in key:
            os30[key[kk]] = float(e['sjump']) * (D['aa'][q, PRE + 30] - D['ad'][q, PRE + 30])
    del D
col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); aa_bk = colf('aa_bk'); sj = colf('sj'); sdem = colf('sdem'); dwell = colf('dwell_s')
route = col('route'); slip = colf('slip'); j30 = colf('j30'); pk = colf('pk_rate'); kind = col('kind')
ang_bk = colf('angdes_bk_A'); gate = colf('gate_bk_A'); gf = colf('gate_frac_A')
dose = colf('dose_bk_A'); dose_out = colf('dose_out_A')
sgn_aa = np.sign(aa_bk)
depE = sj == sgn_aa; depR = (sgn_aa == sdem) | (np.abs(aa_bk) < 0.5)
LOW = (v >= 2) & (v < 8)
FIRE = gate > 1e-3
R = {}


def boot(vals, clusters, fn, nb=2000, seed=0):
    vals = np.asarray(vals, float); clusters = np.asarray(clusters)
    ok = np.isfinite(vals); vals, clusters = vals[ok], clusters[ok]
    if len(vals) < 3:
        return None
    u = np.unique(clusters); rng = np.random.default_rng(seed)
    idx = {c: np.where(clusters == c)[0] for c in u}
    bs = [fn(vals[np.concatenate([idx[c] for c in rng.choice(u, len(u))])]) for _ in range(nb)]
    return [float(fn(vals)), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]]


p90 = lambda x: np.percentile(x, 90)
# ---------------- mechanism split ----------------
print('=== MECHANISM SPLIT of the firing episodes, 2-8 m/s ===')
R['mechanism'] = {}
for nm, m in (('fires & |aa|<1 (near-centre, sign meaningless)', LOW & FIRE & (np.abs(aa_bk) < 1.0)),
              ('fires & |aa|>=1 & same side', LOW & FIRE & (np.abs(aa_bk) >= 1.0) & (np.sign(ang_bk) == sgn_aa)),
              ('fires & |aa|>=1 & OPPOSITE side (dose INTO a reversal)',
               LOW & FIRE & (np.abs(aa_bk) >= 1.0) & (np.sign(ang_bk) != sgn_aa)),
              ('fires & |aa|>=2 & OPPOSITE side', LOW & FIRE & (np.abs(aa_bk) >= 2.0) & (np.sign(ang_bk) != sgn_aa)),
              ('silent', LOW & ~FIRE)):
    if m.sum() < 1:
        continue
    d = dict(n=int(m.sum()), routes=int(len(set(route[m]))), abs_aa_p50=float(np.median(np.abs(aa_bk[m]))),
             dose_p50=float(np.median(dose[m])), dose_out_p50=float(np.median(dose_out[m])),
             slip_p50=float(np.median(slip[m])), slip_p90=float(np.percentile(slip[m], 90)),
             pk_p50=float(np.median(pk[m])), dwell_p50=float(np.median(dwell[m])),
             os30_p50=float(np.median(os30[m])), os30_p90=float(np.percentile(os30[m], 90)),
             frac_depR=float(np.mean(depR[m])), frac_depE=float(np.mean(depE[m])),
             frac_rev=float(np.mean(kind[m] == 'rev')))
    R['mechanism'][nm] = d
    print(f'{nm:56s} n={d["n"]:3d} |aa|p50 {d["abs_aa_p50"]:5.2f} dose {d["dose_p50"]:+.4f} '
          f'dose_out {d["dose_out_p50"]:+.4f} slip p50/p90 {d["slip_p50"]:5.2f}/{d["slip_p90"]:6.2f} '
          f'pk {d["pk_p50"]:5.1f} os30 p50/p90 {d["os30_p50"]:+6.2f}/{d["os30_p90"]:+6.2f} '
          f'depR {d["frac_depR"]:.2f} depE {d["frac_depE"]:.2f} rev {d["frac_rev"]:.2f}')

# ---------------- recommended three-way partition ----------------
DOSED = FIRE & (np.abs(dose) >= 0.25 * LEVEL)
NULL = gf <= 1e-9
MIXED = ~DOSED & ~NULL
print('\n=== RECOMMENDED PARTITION (2-8 m/s, n=%d) ===' % LOW.sum())
R['partition'] = {}
for nm, m in (('DOSED', LOW & DOSED), ('NULL', LOW & NULL), ('MIXED', LOW & MIXED),
              ('NULL & |aa|>=1', LOW & NULL & (np.abs(aa_bk) >= 1.0)),
              ('DOSED & |aa|>=1', LOW & DOSED & (np.abs(aa_bk) >= 1.0)),
              ('AMBIGUOUS |aa|<1 (any)', LOW & (np.abs(aa_bk) < 1.0))):
    if m.sum() < 3:
        print(f'{nm:24s} n={int(m.sum())}  (too few)'); continue
    d = dict(n=int(m.sum()), frac=float(m.sum() / LOW.sum()), routes=int(len(set(route[m]))),
             dwell_p50=boot(dwell[m], route[m], np.median), os30_p90=boot(os30[m], route[m], p90),
             os30_p50=boot(os30[m], route[m], np.median), slip_p90=boot(slip[m], route[m], p90),
             pk_p50=boot(pk[m], route[m], np.median), dose_p50=float(np.median(dose[m])),
             frac_depR_labels_return=float(np.mean(~depR[m])), frac_depE_labels_return=float(np.mean(~depE[m])))
    R['partition'][nm] = d
    f_ = lambda x: f'{x[0]:6.3f}[{x[1][0]:6.3f},{x[1][1]:6.3f}]' if x else '        -       '
    print(f'{nm:24s} n={d["n"]:3d} ({d["frac"]:.2f}) rt={d["routes"]}  dwell {f_(d["dwell_p50"])}  '
          f'os30_p90 {f_(d["os30_p90"])}  slip_p90 {f_(d["slip_p90"])}  '
          f'"return" by R {d["frac_depR_labels_return"]:.2f} / by E {d["frac_depE_labels_return"]:.2f}')

# ---------------- time-weighted inward dose with an angle gate ----------------
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
SOS = signal.butter(2, 5.0, btype='low', fs=100.0, output='sos')
acc = {}
for rk in ROUTES:
    D = np.load(f'{OUT}/{rk}_cls.npz')
    C = np.load(f'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref/{rk}.npz', allow_pickle=True)
    press = np.interp(C['t_cs'], C['t_cst'], C['spress']) > 0.5
    HO = D['act'] & ~ndimage.binary_dilation(press, iterations=50)
    v_ = D['v']; aa = D['aa']; z = D['z_A']; ang = D['angdes_A']; g = D['gate_A']
    do = np.sign(aa) * z
    for bn, v0, v1 in (('2-5', 2, 5), ('5-8', 5, 8), ('2-8', 2, 8), ('8-12', 8, 12)):
        for an, a0 in (('all', 0.0), ('|aa|>=1', 1.0), ('|aa|>=2', 2.0), ('|aa|>=5', 5.0)):
            m = HO & (v_ >= v0) & (v_ < v1) & (np.abs(aa) >= a0)
            if m.sum() < 100:
                continue
            e = acc.setdefault(f'{bn}|{an}', dict(n=0, fire=0, inw=0, out=0, inw_big=0))
            e['n'] += int(m.sum()); e['fire'] += int((g[m] > 1e-3).sum())
            e['inw'] += int((do[m] < -1e-5).sum()); e['out'] += int((do[m] > 1e-5).sum())
            e['inw_big'] += int((do[m] <= -0.25 * LEVEL).sum())
    del D, C
print('\n=== TIME-WEIGHTED: does a firing term push the WHEEL inward, with a centre deadband? ===')
print(f'{"bin|gate":16s}{"sec":>9s}{"%fires":>9s}{"%push_out":>11s}{"%push_in":>10s}{"%in_of_fires":>14s}{"%in>=25%lvl":>13s}')
R['time_inward'] = {}
for k, e in acc.items():
    row = dict(sec=e['n'] / 100.0, frac_fires=e['fire'] / e['n'], frac_out=e['out'] / e['n'],
               frac_in=e['inw'] / e['n'], frac_in_of_fires=e['inw'] / max(e['fire'], 1),
               frac_in_big=e['inw_big'] / e['n'])
    R['time_inward'][k] = row
    print(f'{k:16s}{row["sec"]:9.1f}{row["frac_fires"]:9.3f}{row["frac_out"]:11.3f}{row["frac_in"]:10.3f}'
          f'{row["frac_in_of_fires"]:14.3f}{row["frac_in_big"]:13.3f}')
json.dump(R, open(f'{OUT}/c7_recommend.json', 'w'), indent=1)
