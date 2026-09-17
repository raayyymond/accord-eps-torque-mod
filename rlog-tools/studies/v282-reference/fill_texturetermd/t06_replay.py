"""t06: OPEN-LOOP REPLAY.  Drive an identified V293 plant with the LOGGED command and ask whether it reproduces the
measured 1.5-3.5 Hz wheel-rate texture.

Plant (+left, torque in [-1,1] command units, 1 kHz substeps, Karnopp stick-slip as s5sim):
    J th'' + b th' + s(v) hold0(th - aoff, v) + friction(F) + anchor = u(t - d)
anchor = ka * LP_0.25Hz(th_meas - th_sim), ka = hold slope (removes slow drift from unmodelled road torque / bias; its gain
at 2.5 Hz is < 1/100 of the spring, so it cannot create or remove in-band content -- checked by the ka = 0 variant).
Plants:
  IV    J 1.03e-4, b 1.2e-3, F 0 (friction folded into b), d 5 frames   (t05: FF-instrumented FRF at <15 m/s, large angles)
  IVF   J 1.03e-4, b 6e-4,  F 0.015, d 5
  S5    s5_02 per speed stratum J, b, s, F, d  (nominal)      S5Jlo / S5Jhi  = its J CI ends
  NOM   J 8e-5, b 7e-4, F 0.015, d 6  (s5sim nominal)
Drives: u_e4 (delivered), FF-only (hold+move+hyst+rl_ff+p_sp), FB-only (p_meas+i+rl_fb+dob).
Metrics per stratum on band-passed rate: corr(sim, meas), rms ratio sim/meas, regression gain meas-on-sim; run bootstrap.
A PASS for "the command drives the texture": corr >= 0.7 and rms ratio 0.7-1.4 with the delivered command, in the stratum.
A FAIL: corr < 0.5 (the texture is not in the command -> road / sensor / something else), or FF-only reproduces it while
FB-only does not (planner injection) -- written before running.
"""
import sys, json, math
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
import s5ctl as C  # noqa: E402
V = ttd.V
S5 = json.load(open(ttd.BASE + 's5_mechanism/s5_02_plant_ident.json'))
S5_BP = [(3, 8, '3-8'), (8, 15, '8-15'), (15, 22, '15-22'), (22, 99, '22-40')]


def s5par(v, which='nom'):
    for lo, hi, key in S5_BP:
        if v < hi:
            break
    d = S5[key]
    J = d['J'] if which == 'nom' else (d['ci']['J'][0] if which == 'lo' else d['ci']['J'][1])
    return J, max(d['b'], 1e-5), d['s'], d['F'], int(round(d['d'] * 100))


def plants(v):
    J5, b5, s5, F5, d5 = s5par(v)
    sIV = s5
    return {'IV': (1.03e-4, 1.2e-3, sIV, 0.0, 5), 'IVF': (1.03e-4, 6e-4, sIV, 0.015, 5), 'S5': (J5, b5, s5, F5, d5),
            'S5Jlo': (s5par(v, 'lo')[0], b5, s5, F5, d5), 'S5Jhi': (s5par(v, 'hi')[0], b5, s5, F5, d5),
            'NOM': (8e-5, 7e-4, float(np.interp(v, [5.0, 11.5, 18.5, 26.0], [1.0, 1.28, 1.44, 1.25])), 0.015, 6),
            'IVd3': (1.03e-4, 1.2e-3, sIV, 0.0, 3), 'IVd8': (1.03e-4, 1.2e-3, sIV, 0.0, 8), 'IVnoanchor': (1.03e-4, 1.2e-3, sIV, 0.0, 5)}


LPA = signal.butter(2, 0.25, fs=100, output='ba')


def sim(u, thm, v, aoff, plant_key, n_sub=10):
    n = len(u); th = float(thm[0]); om = 0.0
    out_om = np.zeros(n)
    b_lp, a_lp = LPA
    zx1 = zx2 = zy1 = zy2 = 0.0
    P0 = plants(float(np.median(v)))[plant_key]
    J, b, s, F, d = P0
    anchor_on = plant_key != 'IVnoanchor'
    ul = u.tolist(); vl = v.tolist(); al = aoff.tolist(); tml = thm.tolist()
    h = 0.01 / n_sub
    for j in range(n):
        vj = vl[j]
        if j % 50 == 0:
            J, b, s, F, d = plants(vj)[plant_key]
        k = float(np.interp(vj, C.HOLD_V_BP, C.HOLD_K_V)) * s if j % 10 == 0 or j == 0 else k
        sat = C.SAT[0] + C.SAT[1] * math.exp(-max(vj, 0.0) / C.SAT[2])
        ud = ul[j - d] if j >= d else ul[0]
        e = tml[j] - th
        y = b_lp[0] * e + b_lp[1] * zx1 + b_lp[2] * zx2 - a_lp[1] * zy1 - a_lp[2] * zy2
        zx2, zx1, zy2, zy1 = zx1, e, zy1, y
        anc = (k * 1.0 * y) if anchor_on else 0.0
        a0 = al[j]
        for _ in range(n_sub):
            spring = k * sat * math.tanh((th - a0) / sat)
            net = ud + anc - spring - b * om
            if F > 0:
                if abs(om) < 0.05:
                    if abs(net) <= F:
                        om = 0.0
                        continue
                    net -= F * math.copysign(1.0, net)
                else:
                    net -= F * math.copysign(1.0, om)
            om_new = om + net / J * h
            if F > 0 and om != 0.0 and om * om_new < 0 and abs(ud + anc - spring) <= F:
                om_new = 0.0
            om = om_new
            th += om * h
        out_om[j] = om
    return out_om


PK = ['IV', 'IVF', 'S5', 'S5Jlo', 'S5Jhi', 'NOM', 'IVd3', 'IVd8', 'IVnoanchor']
DRIVES = ['u_e4', 'ff', 'fb']
acc = []   # rows: route, run, stratum-frame arrays
store = {}
for ri, (rk, g) in enumerate(ttd.TORQUE.items()):
    R = ttd.red(rk)
    t = R['t']; v = R['v'].astype(float); thm = R['ang'].astype(float) + 0.0
    aoff = (R['sa'] - R['ang']).astype(float)
    m = R['usable'].astype(bool) & np.isfinite(v) & (v >= 3.0) & np.isfinite(R['u_e4']) & np.isfinite(R['sa'])
    FF = sum(np.nan_to_num(R[k].astype(float)) for k in ttd.TERMS_FF)
    FBt = sum(np.nan_to_num(R[k].astype(float)) for k in ttd.TERMS_FB)
    drives = dict(u_e4=R['u_e4'].astype(float), ff=FF, fb=FBt)
    inturn = np.zeros(len(t), bool)
    for w0, w1, _, _ in json.load(open(ttd.OUT + 't03_turns.json'))[rk]:
        inturn[int(w0):int(w1)] = True
    for run_id, (a, b) in enumerate(V.runs(m, t, min_s=10.0)):
        meas = ttd.bp(R['sr'][a:b].astype(float))
        row = dict(route=ri, run=ri * 100000 + run_id, v=v[a:b], ang=np.abs(R['ang'][a:b]).astype(float), turn=inturn[a:b], meas=meas)
        for pk in PK:
            for dv in DRIVES:
                if pk not in ('IV', 'S5', 'NOM') and dv != 'u_e4':
                    continue
                om = sim(drives[dv][a:b], thm[a:b], v[a:b], aoff[a:b], pk)
                row[f'{pk}|{dv}'] = ttd.bp(om)
        # trim filter edges
        e = 150
        if b - a > 2 * e + 100:
            for kk in list(row):
                if isinstance(row[kk], np.ndarray):
                    row[kk] = row[kk][e:-e]
            acc.append(row)
    print(rk, g, 'runs', len(acc), flush=True)
    del R


def strat(row):
    v, aa, tu = row['v'], row['ang'], row['turn']
    return {'lt15_small': (v < 15) & (aa < 15), 'lt15_large': (v < 15) & (aa >= 15), 'turns_s3': tu, 'v3_8': v < 8,
            'v8_15': (v >= 8) & (v < 15), 'ge15': v >= 15}


def metr(rows, key, sn):
    x = []; y = []
    for r in rows:
        mk = strat(r)[sn]
        if mk.sum() < 50:
            continue
        x.append(r[key][mk]); y.append(r['meas'][mk])
    if not x:
        return None
    x = np.concatenate(x); y = np.concatenate(y)
    return dict(corr=float(np.corrcoef(x, y)[0, 1]), rms_ratio=float(np.std(x) / np.std(y)),
                gain=float(np.dot(x, y) / np.dot(x, x)), meas_rms=float(np.std(y)), sec=len(x) / 100)


keys = [k for k in acc[0] if '|' in k]
RES = {}
rng = np.random.default_rng(5)
groups = {'ALL': [0, 1, 2, 3, 4], 'T64': [0, 1], 'T64B': [2], 'T5': [3], 'T4': [4]}
for sn in ('lt15_small', 'lt15_large', 'turns_s3', 'v3_8', 'v8_15', 'ge15'):
    RES[sn] = {}
    for gn, rr in groups.items():
        rows = [r for r in acc if r['route'] in rr]
        RES[sn][gn] = {}
        for k in keys:
            mm = metr(rows, k, sn)
            if mm is None:
                continue
            if gn == 'ALL' and k in ('IV|u_e4', 'IV|ff', 'IV|fb', 'S5|u_e4', 'NOM|u_e4', 'IVF|u_e4'):
                bs = []
                for _ in range(150):
                    pick = [rows[i] for i in rng.integers(0, len(rows), len(rows))]
                    q = metr(pick, k, sn)
                    if q:
                        bs.append((q['corr'], q['rms_ratio']))
                bs = np.array(bs)
                mm['ci_corr'] = [float(np.percentile(bs[:, 0], 2.5)), float(np.percentile(bs[:, 0], 97.5))]
                mm['ci_rms'] = [float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5))]
            RES[sn][gn][k] = mm
json.dump(RES, open(ttd.OUT + 't06_replay.json', 'w'), indent=1)
for sn in RES:
    for gn in ('ALL', 'T64', 'T64B', 'T5', 'T4'):
        d = RES[sn].get(gn, {})
        if not d:
            continue
        s0 = next(iter(d.values()))
        print(f"\n== {sn} / {gn}  meas band rms {s0['meas_rms']:.2f} deg/s  {s0['sec']:.0f} s")
        for k, mm in d.items():
            ci = mm.get('ci_corr'); cr = mm.get('ci_rms')
            print(f"   {k:18s} corr {mm['corr']:+.3f} rms_ratio {mm['rms_ratio']:.2f} gain {mm['gain']:+.2f}" +
                  (f"  CI corr [{ci[0]:+.2f},{ci[1]:+.2f}] rms [{cr[0]:.2f},{cr[1]:.2f}]" if ci else ''))
# keep one example for the figure
np.savez_compressed(ttd.OUT + 't06_example.npz', **{k: v for k, v in max(acc, key=lambda r: float(np.std(r['meas'])) * len(r['meas']) ** 0.5).items() if isinstance(v, np.ndarray)})
