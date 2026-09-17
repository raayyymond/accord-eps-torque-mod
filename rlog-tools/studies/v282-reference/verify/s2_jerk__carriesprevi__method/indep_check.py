"""Independent re-derivation of the s2_jerk 'carries-previous-motion' finding, NOT reusing s2_extract's
cached npz event traces. Loads routes one at a time straight from v282cmp, re-detects jerk events with the
SAME thresholds documented in the finding's method (THR=0.4, vmin=3, pre=1.0, post=2.5, min_sep=2.0),
re-classifies onset/release the same way, and recomputes:
  - the [-0.6,-0.1] s normalised error (achieved-model)/step  ("pre")
  - the [-1.0,-0.4] s model/achieved slopes and wrong-way fraction, release events, >=15 m/s
one route at a time (RAM discipline). Prints per-route contributions so route pooling is visible.
"""
import sys, gc, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

FS = V.FS
THR, VMIN, PRE, POST = 0.4, 3.0, 1.0, 2.5
NPRE, NPOST = int(PRE * FS), int(POST * FS)
sos3 = signal.butter(2, 3.0, fs=100, output='sos')

V282_ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
T64_ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]


def classify(mlp, k):
    a0 = float(np.mean(mlp[k - 100:k - 60])); a1 = float(np.mean(mlp[k + 60:k + 100]))
    if np.sign(a0) != np.sign(a1) and abs(a0) >= 0.3 and abs(a1) >= 0.3:
        return 'reversal'
    if abs(a1) >= abs(a0):
        return 'onset'
    return 'release'


def process_route(rk):
    S = V.load(rk)
    ev, j = V.jerk_events(S, jerk_thr=THR, vmin=VMIN, pre=PRE, post=POST, min_sep=2.0)
    mlp = V.lowpass(np.nan_to_num(S['model']), 2.0)
    alp = np.nan_to_num(S['la_act'])  # RAW achieved (3 Hz LP applied per-event below, matching s2_stickslip)
    out = []
    for e in ev:
        k = e['idx']; v = e['v']
        if v < 15:
            continue
        i0, i1 = k - NPRE, k + NPOST
        if i0 - 100 < 0 or i1 + 100 > len(mlp):
            continue
        typ = classify(mlp, k)
        if typ != 'release':
            continue
        a0 = float(np.mean(mlp[k - 100:k - 60])); a1 = float(np.mean(mlp[k + 60:k + 100]))
        D = abs(a1 - a0)
        if D < 0.2:
            continue
        dsign = np.sign(a1 - a0) if a1 != a0 else np.sign(e['jerk_peak'])
        base_m = np.mean(mlp[k - 100:k - 60]); base_a = np.mean(alp[k - 100:k - 60])
        mseg = dsign * (mlp[i0:i1] - base_m) / D
        aseg_raw = dsign * (alp[i0:i1] - base_a)
        aseg_f = signal.sosfiltfilt(sos3, aseg_raw) / D
        # "pre": mean(a - m) over idx 40:90 (t=-0.6..-0.11)
        pre = float(np.mean((aseg_f - mseg)[40:90]))
        # slopes over idx [0:60) i.e. t in [-1.0,-0.4)
        tt = np.arange(60) / FS
        sm = np.polyfit(tt, mseg[0:60], 1)[0]
        sa = np.polyfit(tt, aseg_f[0:60], 1)[0]
        wrong = (sa < -0.2 and sm > -0.05)
        out.append(dict(route=rk, k=int(k), v=float(v), D=float(D), pre=pre, sm=float(sm), sa=float(sa), wrong=bool(wrong)))
    del S, ev, j, mlp, alp
    gc.collect()
    return out


def run(routes, label):
    rows = []
    for rk in routes:
        rows += process_route(rk)
    pres = np.array([r['pre'] for r in rows])
    sms = np.array([r['sm'] for r in rows])
    sas = np.array([r['sa'] for r in rows])
    wrong = np.array([r['wrong'] for r in rows])
    print(f"{label}: n={len(rows)}  pre median={np.median(pres):+.3f}  model_slope median={np.median(sms):+.2f}/s  "
          f"achieved_slope median={np.median(sas):+.2f}/s  wrong-way frac={wrong.mean():.2f} ({wrong.sum()}/{len(wrong)})")
    from collections import Counter
    print("   per-route n:", Counter(r['route'] for r in rows))
    return rows


if __name__ == '__main__':
    r1 = run(V282_ROUTES, 'V282 release >=15')
    r2 = run(T64_ROUTES, 'T64  release >=15')
    json.dump(dict(V282=r1, T64=r2), open('indep_check_out.json', 'w'), indent=1, default=float)
