"""CLOSED-LOOP positive control: why equation-error's minimum moves -42 -> +308 ms with the analysis band.

The open-loop positive control (eqerr.py --what pc) passes: with the command exogenous the estimator
recovers 30 and 60 ms to +1.4..+4.0 ms.  On REAL data the same estimator's minimum swings from -42 ms
(3-12 Hz) to +308 ms (0.5-4 Hz).  A negative delay cannot be causal, so something is wrong with the
IDENTIFIABILITY, not the arithmetic.  The candidate is the obvious one: the command is not exogenous, it
is computed FROM the measured wheel motion with its own delay D_ctl, so the fit can satisfy itself on the
CONTROLLER (motion -> command, apparent delay ~ -D_ctl) instead of the PLANT (command -> motion, +D_act).

This script closes the loop on the same plant with a known D_act and a known D_ctl and re-runs the
estimator band by band.  If the real data's band signature is reproduced, the mechanism is established and
the -42 ms / +308 ms numbers are explained rather than merely rejected.

  plant       J w' + b w + k th + F sign(w) = u(t - D_act) + d(t)        d = band-limited road torque
  controller  at 100 Hz, on measurement ONE FRAME OLD (D_ctl = 9.91 ms, measured in chain2.py):
              u = Kp*(th_des - th) + Krate*(w_des - lowpass(w, RC))      ZOH onto the plant
  reference   th_des: smooth, 0-0.5 Hz (a road's worth of lane curvature)
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))

FS = 100.0
T_SEND = 0.00991
BANDS = [(0.3, 8.0), (0.5, 4.0), (1.0, 6.0), (2.0, 10.0), (3.0, 12.0), (0.3, 20.0)]
SEC = 600.0


def run_cl(D_act, J=8e-5, b=6e-4, k=0.0116, F=0.011, Kp=0.010, Krate=0.0010, RC=0.01,
           d_rms=0.010, d_fc=(0.5, 12.0), dt=2e-4, seed=0, closed=True):
    """Integrate the closed loop.  Returns the 100 Hz sampled/quantised signals and the ZOH command."""
    rng = np.random.default_rng(seed)
    N = int(SEC / dt)
    tf = np.arange(N) * dt
    # exogenous reference: smooth desired angle
    nr = int(SEC * FS)
    th_des_c = signal.sosfiltfilt(signal.butter(2, 0.35, fs=FS, output="sos"), rng.standard_normal(nr))
    th_des_c = 8.0 * th_des_c / np.std(th_des_c)
    th_des = np.interp(tf, np.arange(nr) / FS, th_des_c)
    w_des = np.gradient(th_des) / dt
    # exogenous road disturbance torque, band-limited so it has the real data's HF content
    dn = signal.sosfiltfilt(signal.butter(2, list(d_fc), btype="band", fs=1 / dt, output="sos"),
                            rng.standard_normal(N))
    dn = d_rms * dn / np.std(dn)

    nsend = int(T_SEND / dt)                     # controller tick, in fine steps
    th = np.empty(N); rt = np.empty(N); uu = np.empty(N)
    x = r = 0.0
    wf = 0.0                                      # the controller's filtered rate state
    alpha = T_SEND / (RC + T_SEND)
    ucur = 0.0
    hist = [0.0] * (max(int(round(D_act / dt)), 0) + 1)   # transport delay line on u
    band = max(dt * F / J, 1e-3)
    th_m = w_m = 0.0                              # the measurement the controller saw LAST tick (D_ctl)
    for i in range(N):
        if i % nsend == 0:
            # one-frame-old measurement (D_ctl), quantised exactly as carState is
            wf += alpha * (w_m - wf)
            if closed:
                fine = Kp * (th_des[i] - th_m) + Krate * (w_des[i] - wf)
            else:
                fine = Kp * th_des[i] + Krate * w_des[i]      # open loop: reference only
            ucur = np.round(np.clip(fine, -1, 1) * 4096) / 4096.0
            th_m = round(x / 0.1) * 0.1                        # becomes "one frame old" next tick
            w_m = round(r / 1.0) * 1.0
        hist.append(ucur); ud = hist.pop(0)
        net = ud + dn[i] - k * x - b * r
        if F > 0 and abs(r) < band and abs(net) <= F:
            r = 0.0
        else:
            fr = F * (1.0 if r > 0 else -1.0 if r < 0 else (1.0 if net > 0 else -1.0))
            r += dt * (net - fr) / J
        x += dt * r
        th[i] = x; rt[i] = r; uu[i] = ucur
    g = np.arange(2.0, SEC - 2.0, 1 / FS)
    return dict(g=g, sa=np.round(np.interp(g, tf, th) / 0.1) * 0.1,
                sr=np.round(np.interp(g, tf, rt) / 1.0) * 1.0,
                tc=np.arange(0, SEC, T_SEND),
                uc=np.interp(np.arange(0, SEC, T_SEND), tf, uu),
                rate_rms=float(np.std(rt)), ang_rms=float(np.std(th)))


def fit_band(S, band, k, dwell=2.0, dgrid=np.arange(-80, 341, 2), zoh_corr=T_SEND * 500):
    sos = signal.butter(4, list(band), btype="band", fs=FS, output="sos")
    g, sa, sr = S["g"], S["sa"], S["sr"]
    X = np.column_stack([np.gradient(signal.sosfiltfilt(sos, sr)) * FS,
                         signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, k * sa),
                         signal.sosfiltfilt(sos, np.sign(sr))])
    m = np.abs(sr) >= dwell
    m[:100] = m[-100:] = False
    Xb = X[m]; Ai = np.linalg.inv(Xb.T @ Xb)
    sse = np.empty(len(dgrid))
    for q, d in enumerate(dgrid):
        ub = signal.sosfiltfilt(sos, np.interp(g - d * 1e-3, S["tc"], S["uc"]))[m]
        bb = Xb.T @ ub
        sse[q] = ub @ ub - bb @ (Ai @ bb)
    UU = None
    i = int(np.argmin(sse))
    ub0 = signal.sosfiltfilt(sos, np.interp(g - dgrid[i] * 1e-3, S["tc"], S["uc"]))[m]
    R2 = 1 - sse[i] / (ub0 @ ub0)
    return float(dgrid[i] - zoh_corr), float(R2)


if __name__ == "__main__":
    out = {}
    print("CLOSED-LOOP POSITIVE CONTROL: plant 1.92 Hz (k 0.0116, J 8e-5), D_ctl = 9.91 ms (1 frame)\n")
    for tag, closed, dr in [("OPEN loop, no road d", False, 0.0),
                            ("OPEN loop + road d  ", False, 0.010),
                            ("CLOSED loop, no d   ", True, 0.0),
                            ("CLOSED loop + road d", True, 0.010),
                            ("CLOSED, 3x rate gain", True, 0.010)]:
        Kr = 0.0030 if "3x" in tag else 0.0010
        for Dt in (30, 60):
            S = run_cl(Dt * 1e-3, closed=closed, d_rms=dr, Krate=Kr)
            row = []
            for band in BANDS:
                D, R2 = fit_band(S, band, 0.0116)
                row.append((band, D - Dt, D, R2))
            print(f"  {tag}  true D_act {Dt:3d} ms  (rate rms {S['rate_rms']:5.1f} deg/s, ang rms {S['ang_rms']:4.1f} deg)")
            print("     " + "  ".join(f"{b[0]:.1f}-{b[1]:.0f}:{D:+7.1f}({e:+6.1f},R2 {r:.2f})" for b, e, D, r in row),
                  flush=True)
            out[f"{tag}|{Dt}"] = [[list(b), e, D, r] for b, e, D, r in row]
    Path(Path(__file__).resolve().parent / "cl_test.json").write_text(json.dumps(out, indent=1, default=float))
