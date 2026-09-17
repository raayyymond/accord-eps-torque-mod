"""t02: reduce each torque route to what this stream needs, and split the fork command into sub-terms.

Source of the sub-terms: the s5 controller replica (s5ctl.Ctl, transcribed from 84766cdc/e44b6cd3/08a5a706 and
validated open loop in s5_03 at corr >= 0.996 on output).  THIS script re-validates it IN THE 1.5-3.5 Hz BAND below
15 m/s (the pooled corr says nothing about 2-3 Hz) and then splits two mixed terms exactly (both are linear):
  P  = P_sp + P_meas   (the error notch and the low-speed factor are linear time-varying ops: run them on sp and meas separately)
  rl = rl_ff + rl_fb   (rl = g(v) * (adr - rm):  rl_fb = +g*rm*laf from the measured-rate filter, rl_ff = rl - rl_fb)
All terms saved as +LEFT torque (= -x/laf).
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
import s5ctl as C  # noqa: E402
V = ttd.V
val = {}
for rk, g in ttd.TORQUE.items():
    P_ = C.REV[ttd.GROUP_REV[g]]; laf = P_['laf']; kp = P_['kp']
    S = V.load(rk)
    R = np.load(ttd.BASE + f's5_mechanism/_replica_{rk}.npz')
    n = len(S['t'])
    p_sp = np.full(n, np.nan); rl_fb = np.full(n, np.nan)
    act = S['active'] & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['v'])
    assert np.allclose(R['t'], S['t'])
    for a, b in V.runs(act, S['t'], min_s=1.0):
        nt = C.Notch(); rm = float(S['sr'][a])
        for j in range(a, b):
            v = float(S['v'][j])
            lsf = (float(np.interp(v, C.LOW_SPEED_X, C.LOW_SPEED_Y)) / max(v, 1.0)) ** 2
            e_sp = float(S['setpoint'][j]) * (1 + lsf / max(kp, 1e-3))
            p_sp[j] = kp * nt.update(e_sp, C.mode_hz(v), P_['notch_q'])
            rm += (C.DT / (P_['rl_rc'] + C.DT)) * (float(S['sr'][j]) - rm)
            gl = P_['rl_gain'] * min(1.0, C.RATE_LOOP_TAPER_V / max(v, 0.1))
            rl_fb[j] = gl * rm * laf
    L = lambda x: -np.asarray(x) / laf
    comp = dict(hold=L(R['hold']), move=L(R['move']), hyst=L(R['hyst']), rl_ff=L(R['rl'] - rl_fb), p_sp=L(p_sp),
                p_meas=L(R['p'] - p_sp), i=L(R['i']), rl_fb=L(rl_fb), dob=L(R['dob']))
    tot = sum(comp[k] for k in ttd.TERMS)
    out = dict(t=S['t'], v=S['v'], ang=S['sa'] - np.nan_to_num(S['aoff']), sa=S['sa'], sr=S['sr'], usable=V.usable(S) & act,
               active=act, pressed=S['pressed'], sat=S['sat'], u_log=S['out'], u_e4=-S['e4'] / 4089.0, rep_out=R['out'],
               setpoint=S['setpoint'], model=S['model'], meas=R['meas'], la_pose=S['la_pose'], storque=S['storque'],
               p_log=L(S['p']), i_log=L(S['i']), f_log=L(S['f']), rep_total=tot, lat_delay=S['lat_delay'], **comp)
    m = out['usable'] & (S['v'] >= 3) & (S['v'] < 15) & np.isfinite(tot) & np.isfinite(out['u_log'])
    num = {k: [] for k in ('out', 'p', 'i', 'f', 'e4')}
    ffb = sum(comp[k] for k in ('hold', 'move', 'hyst', 'rl_ff', 'rl_fb', 'dob'))
    for a, b in V.runs(m, S['t'], min_s=5.0):
        pairs = dict(out=(tot, out['u_log']), p=(comp['p_sp'] + comp['p_meas'], out['p_log']), i=(comp['i'], out['i_log']),
                     f=(ffb, out['f_log']), e4=(out['u_log'], out['u_e4']))
        for k, (x, y) in pairs.items():
            if not (np.isfinite(x[a:b]).all() and np.isfinite(y[a:b]).all()):
                continue
            num[k].append((ttd.bp(x[a:b]), ttd.bp(y[a:b])))
    r = {}
    for k, lst in num.items():
        if not lst:
            continue
        x = np.concatenate([p[0] for p in lst]); y = np.concatenate([p[1] for p in lst])
        r[k] = dict(corr=float(np.corrcoef(x, y)[0, 1]), slope=float(np.dot(x, y) / np.dot(x, x)),
                    resid=float(np.std(y - x) / np.std(y)), y_rms=float(np.std(y)), sec=len(x) / 100)
    val[rk] = dict(group=g, **r)
    print(g, rk, {k: (round(v['corr'], 4), round(v['slope'], 3), round(v['resid'], 3), round(v['y_rms'], 5)) for k, v in r.items()}, flush=True)
    np.savez_compressed(ttd.OUT + f'red_{rk}.npz', **{k: np.asarray(v, dtype=np.float64 if k == 't' else np.float32) for k, v in out.items()})
    del S, R, out, comp
json.dump(val, open(ttd.OUT + 't02_band_validation.json', 'w'), indent=1)
