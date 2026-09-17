"""t06b: LINEAR open-loop replay with a delay scan and the FF / FB split (t06's nonlinear replay cannot take FF-only or
FB-only drives: with the saturating spring and no feedback the angle runs away and the anchor loop goes unstable).

Plant, +left, 100 Hz exact ZOH per frame with the LOCAL spring slope at the MEASURED angle:
   J th'' + b th' + k_loc(v, th_meas) th = u        k_loc = s(v) * k_map(v) * sech^2(th_meas / sat(v))
Because the plant is linear in u and k_loc varies slowly, a delay d is applied by shifting the simulated response by d
frames (exact for constant k).  Drives (high-passed 0.2 Hz): u_e4 (delivered), u_log (controller output, pre-limiter),
FF (planner-only terms), FB (measurement-driven terms), and each FB sub-term.
Per stratum: corr(band sim, band meas) vs d, the best d, rms ratio, and the projection of the measured band rate on each
drive's simulated response (sum over FF + FB = the u_log projection).
"""
import sys, json, math
import numpy as np
from scipy import signal, linalg
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
import s5ctl as C  # noqa: E402
V = ttd.V
S5 = json.load(open(ttd.BASE + 's5_mechanism/s5_02_plant_ident.json'))
HP = signal.butter(2, 0.2, btype='high', fs=100, output='sos')
DMAX = 20
PLANTS = {'J1e-4_b1.2e-3': (1.03e-4, 1.2e-3), 'J1e-4_b6e-4': (1.03e-4, 6e-4), 'J5e-5_b1.2e-3': (5e-5, 1.2e-3), 'J1.5e-4_b1.2e-3': (1.5e-4, 1.2e-3),
          'J3e-5_b5e-4(s5-like)': (3e-5, 5e-4)}
DRIVES = ['u_e4', 'u_log', 'ff', 'fb', 'p_meas', 'rl_fb', 'dob', 'i']


def s_of(v):
    key = '3-8' if v < 8 else '8-15' if v < 15 else '15-22' if v < 22 else '22-40'
    return S5[key]['s']


def sim_lin(u, v, th, J, b):
    n = len(u); x0 = 0.0; x1 = 0.0; out = np.zeros(n)
    cache = {}
    ul = u.tolist()
    for j in range(n):
        if j % 10 == 0:
            vj = float(v[j]); sat = C.SAT[0] + C.SAT[1] * math.exp(-max(vj, 0.0) / C.SAT[2])
            k = s_of(vj) * float(np.interp(vj, C.HOLD_V_BP, C.HOLD_K_V)) / math.cosh(min(float(th[j]) / sat, 20.0)) ** 2
            kq = round(k, 5)
            if kq not in cache:
                Ac = np.array([[0, 1], [-max(kq, 1e-6) / J, -b / J]]); Bc = np.array([[0], [1 / J]])
                M = linalg.expm(np.block([[Ac, Bc], [np.zeros((1, 3))]]) * 0.01)
                cache[kq] = (M[0, 0], M[0, 1], M[1, 0], M[1, 1], M[0, 2], M[1, 2])
            a00, a01, a10, a11, b0, b1 = cache[kq]
        out[j] = x1
        x0, x1 = a00 * x0 + a01 * x1 + b0 * ul[j], a10 * x0 + a11 * x1 + b1 * ul[j]
    return out


rows = []
turns = json.load(open(ttd.OUT + 't03_turns.json'))
for ri, (rk, g) in enumerate(ttd.TORQUE.items()):
    R = ttd.red(rk)
    t = R['t']; v = R['v'].astype(float); th = R['ang'].astype(float)
    m = R['usable'].astype(bool) & np.isfinite(v) & (v >= 3.0) & np.isfinite(R['u_e4']) & np.isfinite(R['sa'])
    X = {k: np.nan_to_num(R[k].astype(float)) for k in ttd.TERMS}
    drv = dict(u_e4=R['u_e4'].astype(float), u_log=R['u_log'].astype(float), ff=sum(X[k] for k in ttd.TERMS_FF),
               fb=sum(X[k] for k in ttd.TERMS_FB), p_meas=X['p_meas'], rl_fb=X['rl_fb'], dob=X['dob'], i=X['i'])
    inturn = np.zeros(len(t), bool)
    for w0, w1, _, _ in turns[rk]:
        inturn[w0:w1] = True
    for run_id, (a, b_) in enumerate(V.runs(m, t, min_s=10.0)):
        if b_ - a < 1300:
            continue
        e = 300
        row = dict(route=ri, run=ri * 1000 + run_id, v=v[a:b_][e + DMAX:-e], ang=np.abs(th[a:b_])[e + DMAX:-e], turn=inturn[a:b_][e + DMAX:-e],
                   meas=ttd.bp(R['sr'][a:b_].astype(float))[e + DMAX:-e])
        for pn, (J, b) in PLANTS.items():
            for dn in DRIVES:
                if pn != 'J1e-4_b1.2e-3' and dn not in ('u_e4',):
                    continue
                y = ttd.bp(sim_lin(signal.sosfiltfilt(HP, drv[dn][a:b_]), v[a:b_], th[a:b_], J, b))
                # store shifted versions for d = 0..DMAX: y(t - d)
                row[f'{pn}|{dn}'] = np.stack([y[e + DMAX - d: len(y) - e - d] for d in range(DMAX + 1)])
        rows.append(row)
    print(rk, g, len(rows), flush=True)
    del R, X, drv


def masks(r):
    v, aa, tu = r['v'], r['ang'], r['turn']
    return {'lt15_small': (v < 15) & (aa < 15), 'lt15_large': (v < 15) & (aa >= 15), 'turns_s3': tu, 'v3_8': v < 8,
            'v8_15': (v >= 8) & (v < 15), 'ge15': v >= 15, 'v15_22': (v >= 15) & (v < 22), 'v22p': v >= 22}


RES = {}
for sn in ('lt15_small', 'lt15_large', 'turns_s3', 'v3_8', 'v8_15', 'ge15', 'v15_22', 'v22p'):
    RES[sn] = {}
    for gname, rr in (('ALL', [0, 1, 2, 3, 4]), ('T64', [0, 1]), ('T64B', [2]), ('T5', [3]), ('T4', [4])):
        sel = [r for r in rows if r['route'] in rr]
        meas = np.concatenate([r['meas'][masks(r)[sn]] for r in sel]) if sel else np.array([])
        if len(meas) < 500:
            continue
        out = dict(sec=len(meas) / 100, meas_rms=float(np.std(meas)))
        for key in sel[0]:
            if '|' not in key:
                continue
            Y = np.concatenate([r[key][:, masks(r)[sn]] for r in sel], axis=1)
            corr = [float(np.corrcoef(Y[d], meas)[0, 1]) for d in range(DMAX + 1)]
            proj = [float(np.dot(Y[d], meas) / np.dot(meas, meas)) for d in range(DMAX + 1)]
            out[key] = dict(corr=corr, proj=proj, rms_ratio=[float(np.std(Y[d]) / np.std(meas)) for d in range(DMAX + 1)],
                            best_d=int(np.argmax(corr)), best_corr=float(np.max(corr)))
        RES[sn][gname] = out
json.dump(RES, open(ttd.OUT + 't06b_linear_replay.json', 'w'))
for sn, dd in RES.items():
    for gname, out in dd.items():
        print(f"\n== {sn} / {gname}  {out['sec']:.0f} s  meas band rms {out['meas_rms']:.2f}")
        for key, q in out.items():
            if '|' not in key:
                continue
            bd = q['best_d']
            print(f"   {key:28s} best d {bd*10:3d} ms corr {q['best_corr']:+.3f} rms_ratio {q['rms_ratio'][bd]:.2f} proj {q['proj'][bd]:+.3f} | corr@50 {q['corr'][5]:+.3f} @80 {q['corr'][8]:+.3f} @110 {q['corr'][11]:+.3f} | proj@50 {q['proj'][5]:+.3f} @80 {q['proj'][8]:+.3f}")
