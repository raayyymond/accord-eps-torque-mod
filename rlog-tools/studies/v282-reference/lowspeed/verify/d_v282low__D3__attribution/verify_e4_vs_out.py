"""Adversarial check on D3: does the finding's HF/LF 'command smoothness' ratio (built on the fork's
PRE-rate-limiter PID output, cs_out) survive when measured on the ACTUAL CAN command sent to the EPS
(0xE4 bytes, e4_cmd)? carcontroller.py applies a fixed slew-rate limiter (STEER_DELTA_UP/DOWN=3 per
0.33s, same constant for every Honda/Accord config) AFTER the PID output and before the CAN send.
If torque-mode's PID output has much larger 2-4 Hz swings (which d_analyze.py's own H values show:
several hundred vs V282's ~100), that limiter could disproportionately clip torque mode's HF content
on the wire, changing the 'command was not smoother' conclusion.

RAM: one route at a time.
"""
import sys
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

FS = 100.0
VMIN, VMAX = 2.5, 8.0  # the band the claim's '0.075 ... vs 0.056-0.13' A15 number lives in


def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)


def bp(x, f1, f2, order=4):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)


def fillnan(x):
    x = np.asarray(x, float).copy()
    ok = np.isfinite(x)
    if ok.sum() == 0:
        return np.zeros_like(x)
    idx = np.arange(len(x))
    x[~ok] = np.interp(idx[~ok], idx[ok], x[ok])
    return x


rows = []
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    u = V.usable(S, VMIN, VMAX)
    v = fillnan(S['v'])
    out = np.nan_to_num(S['out'])
    e4 = fillnan(S['e4'])
    sr = fillnan(S['sr'])
    n_e4_nan = float(np.mean(~np.isfinite(S['e4']))) if len(S['e4']) else 1.0
    hf_lf_out = hf_lf_e4 = coh_out = coh_e4 = h_out = h_e4 = np.nan
    sec = 0.0
    for a, b in V.runs(u, S['t'], min_s=3.0):
        n = b - a
        if n < 300:
            continue
        sec += n / FS
    if sec < 5.0:
        print(rk, meta['group'], 'not enough usable time', sec)
        del S
        continue
    # pooled HF/LF ratio over usable samples (simple mask-based, mirrors d_analyze's per-block RMS in spirit)
    m = u.copy()
    out_hf = bp(out, 2, 10); out_lf = lp(out, 1.0)
    e4_hf = bp(e4, 2, 10); e4_lf = lp(e4, 1.0)
    rms = lambda z: float(np.sqrt(np.mean(z[m] ** 2))) if m.sum() else np.nan
    hf_lf_out = rms(out_hf) / max(rms(out_lf), 1e-9)
    hf_lf_e4 = rms(e4_hf) / max(rms(e4_lf), 1e-9)
    # scale check: is e4 a static rescale of out, or does it diverge (saturation/rate-limit)?
    ok = m & np.isfinite(S['e4'] if len(S['e4']) == len(m) else np.zeros(len(m)))
    corr = np.nan
    if ok.sum() > 200 and np.std(out[ok]) > 1e-6 and np.std(e4[ok]) > 1e-6:
        corr = float(np.corrcoef(out[ok], e4[ok])[0, 1])
    rows.append(dict(route=rk, group=meta['group'], sec=round(sec, 1), n=int(m.sum()),
                      e4_nan_frac=round(n_e4_nan, 3), hf_lf_out=round(hf_lf_out, 4), hf_lf_e4=round(hf_lf_e4, 4),
                      ratio_e4_over_out=round(hf_lf_e4 / max(hf_lf_out, 1e-9), 3),
                      corr_out_e4=round(corr, 4) if np.isfinite(corr) else None))
    print(rows[-1], flush=True)
    del S

import json
json.dump(rows, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/d_v282low__D3__attribution/e4_vs_out.json', 'w'), indent=1)
