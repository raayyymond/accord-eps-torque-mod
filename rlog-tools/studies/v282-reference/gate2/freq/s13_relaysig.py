"""STEP 13 -- is the relay LIVE on the wire? A per-route check independent of initData.

The SteerFriction relay adds +-friction * clip(arg/thr) to the controller OUTPUT. When it is
live it puts a switching component into `output` (and hence the CAN command) that the plant
then low-passes. So the relay's presence should be readable from the OUTPUT channel's
high-frequency content, with the wheel's own response attenuated by the plant.

Statistic: median over masked 8 s windows of (band power of `out` in 3-9 Hz) / (band power of
`out` in 0.2-1.0 Hz). The denominator normalises away "this route steered more". A relay-free
controller output is a smooth function of a smooth error; a live relay is not.

Cross-checked against each route's flown SteerFriction / AccordFrictionHyst / commit.

python s13_relaysig.py [vmin]
"""
import sys, json
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, runs, FS

PARAMS = ("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/"
          "v282-reference/hsurface/surface/params_all.json")
GUARD_COMMIT = "08a5a706498479679e1af2cc8fd565fe9faf04ad"   # rev 4: friction_torque = 0 if hyst > 0
ORDER = ["r71", "r73", "r72", "r75", "r74", "v282a", "v282b", "v282c"]


def stat(key, vmin, ch="out"):
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    nper = int(8.0 * FS)
    w = sig.get_window("hann", nper)
    f = np.fft.rfftfreq(nper, 1 / FS)
    hi = (f >= 3.0) & (f <= 9.0)
    lo = (f >= 0.2) & (f <= 1.0)
    r, hp = [], []
    for a, b in runs(m, min_s=8.0):
        for i in range(a, b - nper + 1, nper):
            P = np.abs(np.fft.rfft(sig.detrend(D[ch][i:i + nper], type="linear") * w)) ** 2 \
                / (FS * (w ** 2).sum())
            P[1:-1] *= 2
            h = float(np.trapezoid(P[hi], f[hi])); l = float(np.trapezoid(P[lo], f[lo]))
            if l > 0:
                r.append(h / l); hp.append(h)
    del D
    return np.array(r), np.array(hp)


if __name__ == "__main__":
    vmin = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    P = json.load(open(PARAMS))
    from freq_lib import ROUTES
    print(f"RELAY SIGNATURE on the controller OUTPUT, engaged hands-off v>={vmin}\n")
    print(f"{'route':7s} {'SteerFric':>9s} {'Hyst':>6s} {'commit':>9s} {'guard?':>7s} {'relay':>6s} "
          f"{'n':>4s} {'HF/LF med':>10s} {'HF/LF p90':>10s} {'HF power med':>12s}")
    for k in ORDER:
        rid = ROUTES[k]
        p = P[rid]
        sf = p.get("SteerFriction"); hy = p.get("AccordFrictionHyst"); c = p.get("GitCommit", "")
        guard = (c == GUARD_COMMIT) or False
        # guard exists only at rev 4 and later; the anchor set says pre-guard commits apply it
        # unconditionally, so live <=> SteerFriction > 0 and (not guard or hyst in (None,0,'ABSENT'))
        def num(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return None
        sfn, hyn = num(sf), num(hy)
        hy_num = hyn if hyn is not None else 0.0
        live = (sfn is not None and sfn > 0) and (not guard or hy_num <= 0)
        r, hp = stat(k, vmin)
        if not len(r):
            print(f"{k:7s} {str(sf):>9s} {str(hy):>6s} {c[:8]:>9s} {str(guard):>7s} "
                  f"{str(live):>6s}    0        --"); continue
        print(f"{k:7s} {str(sf)[:9]:>9s} {str(hy):>6s} {c[:8]:>9s} {str(guard):>7s} {str(live):>6s} "
              f"{len(r):4d} {np.median(r):10.4f} {np.percentile(r,90):10.4f} {np.median(hp):12.3e}")
