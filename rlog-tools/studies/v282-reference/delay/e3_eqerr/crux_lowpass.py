"""CRUX 2 -- THE DECIDING TEST.  The LOW-PASS, DC-retaining, constant-fitted parameterisation is the one
that returns D_act = 58-77 ms with physical coefficients on the five torque routes (pooled_rate_lp*.json).
Is IT unbiased on the closed-loop + road-disturbance control?

RESULT (2026-09-19): NO.  With a TRUE D_act of 30 ms it returns +61..+71 ms while J comes out 7.0e-5 to
8.1e-5 (truth 8e-5) and g_k 0.997-1.008 (truth 1.000).  So a 58-77 ms reading with textbook-physical
coefficients is EXACTLY what a true 30 ms delay looks like once the loop is closed and a road torque is
present.  The bias is +17..+41 ms, always positive, and it grows with the disturbance and shrinks with the
true delay -- so the real-data reading is an UPPER bound on D_act, not a measurement of it."""
import sys, numpy as np
from scipy import signal
sys.path.insert(0, ".")
import cl_test as C
FS = 100.0; T = C.T_SEND


def fit_lp(S, fc, k, dwell=2.0, dg=np.arange(-40, 241, 2), order=4):
    sos = signal.butter(order, fc, btype="low", fs=FS, output="sos")
    g, sa, sr = S["g"], S["sa"], S["sr"]
    X = np.column_stack([np.gradient(signal.sosfiltfilt(sos, sr)) * FS, signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, k * sa), signal.sosfiltfilt(sos, np.sign(sr)),
                         np.ones(len(g))])
    m = np.abs(sr) >= dwell; m[:200] = m[-200:] = False
    Xb = X[m]; Ai = np.linalg.inv(Xb.T @ Xb)
    sse = np.empty(len(dg)); B = np.empty((len(dg), 5))
    for q, d in enumerate(dg):
        ub = signal.sosfiltfilt(sos, np.interp(g - d * 1e-3, S["tc"], S["uc"]))[m]
        bb = Xb.T @ ub; B[q] = Ai @ bb; sse[q] = ub @ ub - bb @ B[q]
    i = int(np.argmin(sse))
    ub = signal.sosfiltfilt(sos, np.interp(g - dg[i] * 1e-3, S["tc"], S["uc"]))[m]
    return dg[i] - T * 500, B[i], 1 - sse[i] / ((ub - ub.mean()) ** 2).sum(), (sse.max() - sse.min()) / sse.max()


if __name__ == "__main__":
    print("TRUE plant: J 8.0e-05  b 6.0e-04  g_k 1.000  F 0.011")
    for tag, closed, dr in [("OPEN, no d ", False, 0.0), ("OPEN + d   ", False, 0.010),
                            ("CLOSED + d ", True, 0.010), ("CLOSED + 2d", True, 0.020)]:
        for Dt in (30, 60):
            S = C.run_cl(Dt * 1e-3, closed=closed, d_rms=dr, F=0.011)
            for fc in (4.0, 6.0):
                D, B, R2, dep = fit_lp(S, fc, 0.0116)
                print(f"  {tag} true {Dt:3d}  lp{fc:.0f}  argmin {D:+7.1f} ({D-Dt:+6.1f})  R2 {R2:.3f} "
                      f"depth {dep*100:4.1f}%  J {B[0]:.2e} b {B[1]:+.2e} gk {B[2]:+.3f} F {B[3]:+.4f}", flush=True)
