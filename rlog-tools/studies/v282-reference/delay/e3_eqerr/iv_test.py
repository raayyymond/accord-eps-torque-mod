"""Can an INSTRUMENT rescue the equation-error delay sweep on closed-loop data?

Plain equation error fails here for two separate reasons, both shown in cl_test.py:
  (1) FEEDBACK -- u is computed from the measured motion with delay D_ctl, so the criterion can satisfy
      itself on the controller (apparent delay ~ -D_ctl) instead of the plant.
  (2) An unmeasured EQUATION disturbance d (the road torque) contaminates every regressor, and the
      errors-in-variables attenuation is frequency-dependent, so the fitted RHS acquires a phase error
      that D absorbs.  This one bites even OPEN loop (+85 ms at true 30 and 60).

Both vanish if the criterion is projected onto signals correlated with u but NOT with d.  The exogenous
reference (the vision model's desired path) is such a signal.  GMM/2SLS:

  moments  Z'(L(u_D) - X b) = 0,  W = (Z'Z)^-1,  J(D) = min_b q' W q
  Z        = the reference and its lags, band-passed with the same L

Tested against cl_test's closed-loop plant with a KNOWN D_act (30 and 60 ms), and the instrument strength
reported (the first-stage R2 of L(u) on Z), because a weak instrument makes the D curve flat, not wrong.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_test as C

FS = 100.0
T_SEND = C.T_SEND
LAGS_MS = [0, 20, 40, 60, 80, 120, 160, 200]


def build_Z(g, ref, sos):
    r = signal.sosfiltfilt(sos, ref)
    cols = [np.interp(g - L * 1e-3, g, r) for L in LAGS_MS]
    return np.column_stack(cols)


def iv_fit(g, sa, sr, ref, tc, uc, band, k, dwell=2.0, dgrid=np.arange(-80, 341, 2),
           zoh_corr=T_SEND * 500):
    sos = signal.butter(4, list(band), btype="band", fs=FS, output="sos")
    X = np.column_stack([np.gradient(signal.sosfiltfilt(sos, sr)) * FS,
                         signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, k * sa),
                         signal.sosfiltfilt(sos, np.sign(sr))])
    Z = build_Z(g, ref, sos)
    m = np.abs(sr) >= dwell
    m[:200] = m[-200:] = False
    Xb, Zb = X[m], Z[m]
    ZZ = Zb.T @ Zb
    W = np.linalg.pinv(ZZ)
    ZX = Zb.T @ Xb
    M = ZX.T @ W @ ZX
    Mi = np.linalg.pinv(M)
    J = np.empty(len(dgrid)); firstR2 = np.empty(len(dgrid))
    for q, d in enumerate(dgrid):
        ub = signal.sosfiltfilt(sos, np.interp(g - d * 1e-3, tc, uc))[m]
        Zu = Zb.T @ ub
        beta = Mi @ (ZX.T @ W @ Zu)
        e = Zu - ZX @ beta
        J[q] = e @ W @ e
        firstR2[q] = (Zu @ W @ Zu) / max(ub @ ub, 1e-30)
    i = int(np.argmin(J))
    return float(dgrid[i] - zoh_corr), float(firstR2[i]), J, dgrid


if __name__ == "__main__":
    out = {}
    print("IV (GMM) delay sweep against the CLOSED-LOOP control.  instrument = the exogenous desired angle,")
    print(f"lags {LAGS_MS} ms.  'strength' = fraction of L(u)'s power the instruments explain.\n")
    for tag, closed, dr, Kr in [("CLOSED + road d    ", True, 0.010, 0.0010),
                                ("CLOSED, no d       ", True, 0.000, 0.0010),
                                ("OPEN + road d      ", False, 0.010, 0.0010)]:
        for Dt in (30, 60):
            S = C.run_cl(Dt * 1e-3, closed=closed, d_rms=dr, Krate=Kr)
            # the instrument: the same smooth reference the controller used, on the 100 Hz grid
            rng = np.random.default_rng(0)
            nr = int(C.SEC * FS)
            ref = signal.sosfiltfilt(signal.butter(2, 0.35, fs=FS, output="sos"), rng.standard_normal(nr))
            ref = 8.0 * ref / np.std(ref)
            ref = np.interp(S["g"], np.arange(nr) / FS, ref)
            row = []
            for band in [(0.3, 8.0), (0.5, 4.0), (1.0, 6.0), (2.0, 10.0), (0.15, 2.0)]:
                D, st, _, _ = iv_fit(S["g"], S["sa"], S["sr"], ref, S["tc"], S["uc"], band, 0.0116)
                row.append((band, D - Dt, D, st))
            print(f"  {tag} true {Dt:3d} ms: " +
                  "  ".join(f"{b[0]:.2f}-{b[1]:.0f}:{D:+7.1f}({e:+6.1f},str {s:.2f})" for b, e, D, s in row),
                  flush=True)
            out[f"{tag}|{Dt}"] = [[list(b), e, D, s] for b, e, D, s in row]
    Path(Path(__file__).resolve().parent / "iv_test.json").write_text(json.dumps(out, indent=1, default=float))
