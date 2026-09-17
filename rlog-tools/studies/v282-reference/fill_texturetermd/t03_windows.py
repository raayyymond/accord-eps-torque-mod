"""t03: labelled short-window Fourier coefficients (0.8-5 Hz bins) of the wheel rate and every fork sub-term.

Windows: 2.56 s Hann (df 0.39 Hz), hop 0.64 s, fully inside usable (engaged, lateral active, not pressed), no clock gap.
Labels per window: route, run id, median v, median |angle| (sa - angleOffset), in-s3-turn flag (s3turns.find_turns,
default arguments, window fully inside [w0, w1]), fraction of frames at the Honda rate limiter (|du_e4| >= 0.029/frame).
Signals: r = carState.steeringRateDeg (+left), rd = d/dt(angle) as a cross-check, all sub-terms (+left torque), ff/fb
sums, replica total, logged output, delivered e4 torque, setpoint.
"""
import sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import ttd  # noqa: E402
import s3turns  # noqa: E402
V = ttd.V
NPS, HOP = 256, 64
f = np.fft.rfftfreq(NPS, 1 / ttd.FS)
KB = np.where((f >= 0.7) & (f <= 5.1))[0]
SIG = ['r', 'rd'] + ttd.TERMS + ['ff', 'fb', 'total', 'u_log', 'u_e4', 'setpoint']
win = signal.get_window('hann', NPS)
acc = {k: [] for k in SIG}
lab = {k: [] for k in ('route', 'run', 'v', 'absang', 'turn', 'limfrac', 'maxabsang', 'lf_rate')}
turn_list = {}
for ri, (rk, g) in enumerate(ttd.TORQUE.items()):
    R = ttd.red(rk)
    P = s3turns.prep(rk)
    evs, rej = s3turns.find_turns(P)
    del P
    turn_list[rk] = [(e['w0'], e['w1'], e['v'], e['P']) for e in evs]
    inturn = np.zeros(len(R['t']), bool)
    for e in evs:
        inturn[e['w0']:e['w1']] = True
    print(rk, g, 'turns', len(evs), rej, flush=True)
    X = {k: np.nan_to_num(R[k].astype(float)) for k in ttd.TERMS}
    X['ff'] = sum(X[k] for k in ttd.TERMS_FF); X['fb'] = sum(X[k] for k in ttd.TERMS_FB); X['total'] = X['ff'] + X['fb']
    X['u_log'] = R['u_log'].astype(float); X['u_e4'] = R['u_e4'].astype(float); X['setpoint'] = R['setpoint'].astype(float)
    X['r'] = R['sr'].astype(float); X['rd'] = np.gradient(R['ang'].astype(float)) * ttd.FS
    lim = np.abs(np.diff(X['u_e4'], prepend=X['u_e4'][0])) >= 0.029
    m = R['usable'].astype(bool) & np.isfinite(R['v']) & (R['v'] >= 3.0)
    for k in SIG:
        m &= np.isfinite(X[k])
    t = R['t']; v = R['v']; aa = np.abs(R['ang'])
    for run_id, (a, b) in enumerate(V.runs(m, t, min_s=NPS / ttd.FS)):
        for s in range(a, b - NPS + 1, HOP):
            e = s + NPS
            for k in SIG:
                acc[k].append(np.fft.rfft(signal.detrend(X[k][s:e]) * win)[KB].astype(np.complex64))
            lab['route'].append(ri); lab['run'].append(ri * 100000 + run_id); lab['v'].append(float(np.median(v[s:e])))
            lab['absang'].append(float(np.median(aa[s:e]))); lab['maxabsang'].append(float(np.max(aa[s:e])))
            lab['turn'].append(bool(inturn[s:e].all())); lab['limfrac'].append(float(lim[s:e].mean()))
            lab['lf_rate'].append(float(np.std(V.lowpass(X['r'][s:e], 1.0))))
    del R, X
np.savez_compressed(ttd.OUT + 't03_win.npz', f=f[KB], routes=np.array(list(ttd.TORQUE.keys())),
                    **{'X_' + k: np.array(v_) for k, v_ in acc.items()}, **{'L_' + k: np.array(v_) for k, v_ in lab.items()})
import json
json.dump(turn_list, open(ttd.OUT + 't03_turns.json', 'w'), default=float)
print('windows', len(lab['v']), 'turn windows', int(np.sum(lab['turn'])))
