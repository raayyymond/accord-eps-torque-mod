"""Independent cross-check channel: la_yaw = carState.yawRate * vEgo (NOT the fork's la_act/la_pose, which
differ in definition between fork versions per the orchestrator's warning). Mirrors s4_extract.py's block
loop EXACTLY (same runs, same NB=512 blocks, same cell variables v/ang90/act) so cells line up with the
stored s4_texture/data cells, and adds:
  mode_rms_yaw : rms(bandpass(d/dt la_yaw, 1.8-3.0 Hz))   -- does the 2-3 Hz wheel mode show up in an
                 independently-sensed (yaw-rate x speed) vehicle-response channel, not just the wheel itself?
One route at a time, npz freed before the next (RAM discipline).
"""
import sys, json, gc
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__wheel23hztex__confound/data_layaw'
FS = V.FS
NB = 512


def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def route(rk):
    S = V.load(rk)
    t = S['t']; u = V.usable(S)
    sr = np.nan_to_num(S['sr']); sa = np.nan_to_num(S['sa']); v = np.nan_to_num(S['v'])
    la_yaw = np.nan_to_num(S['la_yaw'])
    rows = []
    for a, b in V.runs(u, t, min_s=NB / FS):
        if b - a < NB:
            continue
        s_sr = sr[a:b]
        sr_lp05 = V.lowpass(s_sr, 0.5)
        yaw_rate_of = V.deriv(la_yaw[a:b])          # d/dt of la_yaw = jerk-like signal, same op as jerk_rough
        yaw_md = bp(yaw_rate_of, 1.8, 3.0) if b - a > 60 else np.zeros(b - a)
        yaw_lp1 = V.lowpass(la_yaw[a:b], 1.0)
        for k0 in range(0, b - a - NB + 1, NB):
            k1 = k0 + NB; g = slice(a + k0, a + k1); l = slice(k0, k1)
            vv = float(np.median(v[g])); ang90 = float(np.percentile(np.abs(sa[g]), 90))
            act = float(np.mean(np.abs(sr_lp05[l])))
            rows.append(dict(v=vv, ang90=ang90, act=act, t0=float(t[a + k0]),
                             mode_rms_yaw=float(np.sqrt(np.mean(yaw_md[l] ** 2))),
                             la_yaw_rms=float(np.sqrt(np.mean(la_yaw[g] ** 2)))))
    keys = list(rows[0].keys())
    np.savez_compressed(f'{OUT}/{rk}.npz', keys=np.array(keys),
                        rows=np.array([[r[k] for k in keys] for r in rows], dtype=np.float64))
    print(rk, S['meta'].get('group'), 'blocks', len(rows), flush=True)
    del S, sr, sa, v, la_yaw, rows
    gc.collect()


if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)
    for rk in V.ROUTES:
        route(rk)
