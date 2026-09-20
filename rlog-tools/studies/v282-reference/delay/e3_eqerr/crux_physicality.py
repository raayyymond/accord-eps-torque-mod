"""CRUX 1: does the closed-loop/disturbance bias keep the fitted coefficients PHYSICAL?
If a +40..+90 ms-biased fit still returns J ~ 8e-5 and g_k ~ 1, then "the coefficients look right"
is NOT evidence that the argmin is the true delay.  Run with band-pass regressors (no constant).
RESULT (2026-09-19): OPEN+d biases +73..+87 ms while g_k stays 0.98-1.00 and J falls to 0.4x;
CLOSED+d biases +61..+91 ms at 0.3-8 Hz with J 0.1x, and reads -23..-25 ms at 1-6 Hz for BOTH
true 30 and true 60 -- i.e. at 1-6 Hz it reads the CONTROLLER, not the plant."""
import sys, numpy as np
from scipy import signal
sys.path.insert(0, ".")
import cl_test as C
FS = 100.0; T = C.T_SEND


def fit(S, band, k, dwell=2.0, dg=np.arange(-80, 341, 2)):
    sos = signal.butter(4, list(band), btype="band", fs=FS, output="sos")
    g, sa, sr = S["g"], S["sa"], S["sr"]
    X = np.column_stack([np.gradient(signal.sosfiltfilt(sos, sr)) * FS, signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, k * sa), signal.sosfiltfilt(sos, np.sign(sr))])
    m = np.abs(sr) >= dwell; m[:200] = m[-200:] = False
    Xb = X[m]; Ai = np.linalg.inv(Xb.T @ Xb)
    sse = np.empty(len(dg)); B = np.empty((len(dg), 4))
    for q, d in enumerate(dg):
        ub = signal.sosfiltfilt(sos, np.interp(g - d * 1e-3, S["tc"], S["uc"]))[m]
        bb = Xb.T @ ub; B[q] = Ai @ bb; sse[q] = ub @ ub - bb @ B[q]
    i = int(np.argmin(sse)); j = int(np.argmin(np.abs(dg - (30 + T * 500))))
    ub = signal.sosfiltfilt(sos, np.interp(g - dg[i] * 1e-3, S["tc"], S["uc"]))[m]
    return dg[i] - T * 500, B[i], B[j], 1 - sse[i] / (ub ** 2).sum()


if __name__ == "__main__":
    print("TRUE plant: J 8.0e-05  b 6.0e-04  g_k 1.000  F 0.011   (k 0.0116 in the regressor)")
    for tag, closed, dr in [("OPEN, no d ", False, 0.0), ("OPEN + d   ", False, 0.010), ("CLOSED + d ", True, 0.010)]:
        for Dt in (30, 60):
            S = C.run_cl(Dt * 1e-3, closed=closed, d_rms=dr, F=0.011)
            for band in [(0.3, 8.0), (0.5, 4.0), (1.0, 6.0)]:
                D, Bm, B30, R2 = fit(S, band, 0.0116)
                print(f"  {tag} true {Dt:3d}  band {band[0]}-{band[1]:<4} argmin {D:+7.1f} R2 {R2:.3f} "
                      f"beta@argmin J {Bm[0]:.2e} b {Bm[1]:+.2e} gk {Bm[2]:+.3f} F {Bm[3]:+.4f} | "
                      f"beta@30 J {B30[0]:.2e} b {B30[1]:+.2e} gk {B30[2]:+.3f} F {B30[3]:+.4f}", flush=True)
