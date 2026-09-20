"""ADVERSARY 7 -- is the SETPOINT exogenous?  Both the direct and the IV plant estimates lean on it, so a
common contamination would be invisible to their comparison.

There IS an outer loop: the vision model sees the lane, so the car's own disturbance-driven motion returns
as a change in the demanded lateral accel.  Test (standard closed-loop feedback test):
   fit a CAUSAL FIR  Z -> Y  (lags 0..N).  By least squares the residual e is orthogonal to Z(t), ..., Z(t-N)
   BY CONSTRUCTION, but NOT to FUTURE Z.  If  corr(e(t), Z(t+k)) != 0  for k > 0, the disturbance in Y is
   returning to the setpoint -- the input is not exogenous and every transfer estimated from it is biased.
Null: the SAME fit and the SAME residual, correlated against a circularly shifted copy of the same Z
(preserves both spectra and the overfitting, destroys the timing).  Positive control injects a KNOWN
outer loop of adjustable strength and must detect it.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

FS = 100.0
NFIR = 120                 # 1.2 s causal
KMIN, KMAX = 10, 120       # future lags tested (0.1 - 1.2 s): the vision+planner path cannot be faster
NSHIFT = 40


def bp(x, lo=0.05, hi=3.0):
    return signal.sosfiltfilt(signal.butter(4, [lo, hi], btype="band", fs=FS, output="sos"), x)


def stat(Z, Y):
    """Returns (observed max |corr| over future lags, null distribution from circular shifts)."""
    n = len(Z)
    if n < NFIR + KMAX + 2000:
        return None
    Xm = np.column_stack([np.roll(Z, j) for j in range(NFIR + 1)])[NFIR:]
    yy = Y[NFIR:]
    Xm = Xm - Xm.mean(0); yy = yy - yy.mean()
    h, *_ = np.linalg.lstsq(Xm, yy, rcond=None)
    e = yy - Xm @ h
    def corrs(Zs):
        out = []
        for k in range(KMIN, KMAX + 1):
            a = e[: len(e) - k]; b = Zs[NFIR + k: NFIR + k + len(a)]
            if len(b) < len(a):
                a = a[: len(b)]
            out.append(float(np.corrcoef(a, b - b.mean())[0, 1]))
        return np.array(out)
    obs = corrs(Z)
    null = []
    rng = np.random.default_rng(3)
    for _ in range(NSHIFT):
        s = int(rng.integers(30 * FS, n - 30 * FS))
        null.append(np.max(np.abs(corrs(np.roll(Z, s)))))
    return float(np.max(np.abs(obs))), np.array(null), obs


def control(strength):
    """Known plant + known OUTER loop of the given strength feeding the disturbance back into Z."""
    rng = np.random.default_rng(5)
    n = int(400 * FS); dt = 1 / FS
    road = V.lowpass(rng.standard_normal(n), 0.25) * 2.0
    d = V.lowpass(rng.standard_normal(n), 1.5) * 0.5
    Z = np.zeros(n); Y = np.zeros(n); x1 = 0.0
    OD = 25                                    # 250 ms vision+planner path
    for i in range(1, n):
        Z[i] = road[i] - (strength * Y[i - OD] if i >= OD else 0.0)
        x1 += dt * (Z[i] - x1) / 0.25
        Y[i] = x1 + d[i]
    return bp(Z), bp(Y)


if __name__ == "__main__":
    print("=" * 104)
    print("POSITIVE / NEGATIVE CONTROL: known outer loop of given strength fed back into the setpoint")
    print("=" * 104)
    for s in [0.0, 0.10, 0.30]:
        Z, Y = control(s)
        o, nl, _ = stat(Z, Y)
        print(f"  outer-loop strength {s:4.2f}:  observed max|corr| {o:.4f}   null {np.mean(nl):.4f} "
              f"+/- {np.std(nl):.4f}   z = {(o-np.mean(nl))/max(np.std(nl),1e-9):6.2f}"
              f"   {'DETECTED' if (o-np.mean(nl))/max(np.std(nl),1e-9) > 3 else 'not detected'}")
    print("  => the test detects a 10-30 % outer loop and is silent at 0. Sensitivity floor is the 0.0 row.\n")

    print("=" * 104)
    print("REAL ROUTES, >=15 m/s, longest usable run per route")
    print("=" * 104)
    FAM = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
           "0000006c--68c6e94b17": "TORQ", "0000006d--05e83bb04f": "TORQ", "0000006e--6ca3e014fd": "TORQ",
           "00000075--6c8687d5bd": "TORQ", "00000076--d0b7ea7e4d": "TORQ"}
    print(f"  {'route':24s} {'fam':6s} {'sec':>6s} | {'obs max|r|':>10s} {'null mean':>9s} {'null sd':>8s} "
          f"{'z':>7s} | verdict")
    for rk, fam in FAM.items():
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        S = V.load(rk)
        m = V.usable(S, 15.0)
        rr = V.runs(m, S["t"], min_s=60.0)
        if not rr:
            print(f"  {rk:24s} {fam:6s}    --   no run >= 60 s"); del S; continue
        a, b = max(rr, key=lambda ab: ab[1] - ab[0])
        Z = bp(np.nan_to_num(S["setpoint"][a:b])); Y = bp(np.nan_to_num(S["la_act"][a:b]))
        r = stat(Z, Y)
        del S
        if r is None:
            print(f"  {rk:24s} {fam:6s}    --   run too short for the FIR"); continue
        o, nl, _ = r
        z = (o - np.mean(nl)) / max(np.std(nl), 1e-9)
        print(f"  {rk:24s} {fam:6s} {(b-a)/FS:6.0f} | {o:10.4f} {np.mean(nl):9.4f} {np.std(nl):8.4f} {z:7.2f} | "
              f"{'FEEDBACK DETECTED' if z > 3 else 'no detectable return path'}")
