"""Bias audit of the equation-error core, with no logged data anywhere: a band-limited random command,
an exactly-integrated linear plant, a KNOWN delay.  Peels the estimator's own bias apart from the plant's.

Cases, in increasing realism:
  A  command sampled continuously (no ZOH), plant state continuous, fit with linear interp   -> expect 0
  B  command ZOH at 9.91 ms, fit with linear interp                                          -> expect +T/2
  C  as B, corrected by -T/2
  D  as C + rate/angle quantisation
  E  as D + Coulomb friction and stick
Each printed with the recovered D for true D = 0, 30, 60, 90 ms.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eqerr as E

FS = 100.0
T_SEND = 0.00991                      # measured sendcan interval
BAND = (0.3, 8.0)
SEC = 400.0


def cmd_series(seed=0, n=None, fc=4.0):
    """A 0xE4-like command: band-limited noise at the send cadence, in output-torque units."""
    rng = np.random.default_rng(seed)
    n = n or int(SEC / T_SEND)
    x = signal.sosfiltfilt(signal.butter(2, fc, fs=1 / T_SEND, output="sos"), rng.standard_normal(n))
    x = 0.12 * x / np.std(x)
    return np.arange(n) * T_SEND, np.round(x * 4096) / 4096.0    # 0xE4 integer LSB


def sim(tc, uc, D, J, b, k, F, zoh=True, dt=2e-4, stick=True):
    N = int((tc[-1] - 0.5) / dt)
    tf = np.arange(N) * dt
    if zoh:
        u = uc[np.clip(np.searchsorted(tc, tf - D) - 1, 0, len(uc) - 1)]
    else:
        u = np.interp(tf - D, tc, uc)
    th = np.empty(N); rt = np.empty(N)
    x = r = 0.0
    band = max(dt * F / J, 1e-3)
    for i in range(N):
        net = u[i] - k * x - b * r
        if stick and F > 0 and abs(r) < band and abs(net) <= F:
            r = 0.0
        else:
            fr = F * (1.0 if r > 0 else -1.0 if r < 0 else (1.0 if net > 0 else -1.0))
            r += dt * (net - fr) / J
        x += dt * r
        th[i] = x; rt[i] = r
    return tf, th, rt


def fit(tc, uc, tf, th, rt, k, quant=False, dwell=0.0, dgrid=np.arange(-20, 141, 1)):
    sos = signal.butter(4, list(BAND), btype="band", fs=FS, output="sos")
    g = np.arange(2.0, tf[-1] - 2.0, 1 / FS)
    sa = np.interp(g, tf, th); sr = np.interp(g, tf, rt)
    if quant:
        sa = np.round(sa / 0.1) * 0.1; sr = np.round(sr / 1.0) * 1.0
    X = np.column_stack([np.gradient(signal.sosfiltfilt(sos, sr)) * FS,
                         signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, k * sa),
                         signal.sosfiltfilt(sos, np.sign(sr))])
    m = np.abs(sr) >= dwell
    e = int(1.0 * FS)
    m[:e] = m[-e:] = False
    Xb = X[m]
    A = Xb.T @ Xb
    sse = np.empty(len(dgrid)); beta = np.empty((len(dgrid), 4))
    Ai = np.linalg.inv(A)
    for q, d in enumerate(dgrid):
        ub = signal.sosfiltfilt(sos, np.interp(g - d * 1e-3, tc, uc))[m]
        bb = Xb.T @ ub
        beta[q] = Ai @ bb
        sse[q] = ub @ ub - bb @ beta[q]
    i = int(np.argmin(sse))
    if 0 < i < len(sse) - 1:
        y0, y1, y2 = sse[i - 1], sse[i], sse[i + 1]
        den = y0 - 2 * y1 + y2
        sh = 0.5 * (y0 - y2) / den if den > 0 else 0.0
    else:
        sh = 0.0
    return float(dgrid[i] + sh), beta[i], 1 - sse[i] / (sse[i] + 0)  # R2 filled below


J, b, k = 8e-5, 6e-4, 0.0348            # 3.3 Hz, zeta 0.18 -- the fork's plant at 20 m/s with k x3
tc, uc = cmd_series()
print(f"command rms {np.std(uc):.4f}, send interval {T_SEND*1e3:.2f} ms, T/2 = {T_SEND*500:.3f} ms")
print(f"plant J {J:.0e} b {b:.0e} k {k:.4f} -> {np.sqrt(k/J)/2/np.pi:.2f} Hz, zeta {b/2/np.sqrt(k*J):.3f}\n")
for nm, zoh, quant, F, dwell, corr in [
        ("A no-ZOH, no quant, F=0", False, False, 0.0, 0.0, 0.0),
        ("B ZOH,    no quant, F=0", True, False, 0.0, 0.0, 0.0),
        ("C = B corrected -T/2   ", True, False, 0.0, 0.0, T_SEND * 500),
        ("D + quantisation        ", True, True, 0.0, 0.0, T_SEND * 500),
        ("E + friction F.02 stick ", True, True, 0.020, 2.0, T_SEND * 500),
        ("F = E, dwell mask off   ", True, True, 0.020, 0.0, T_SEND * 500)]:
    out = []
    for Dt in (0.0, 0.030, 0.060, 0.090):
        tf, th, rt = sim(tc, uc, Dt, J, b, k, F, zoh=zoh)
        Df, be, _ = fit(tc, uc, tf, th, rt, k, quant=quant, dwell=dwell)
        out.append((Dt * 1e3, Df - corr, be))
    print(f"  {nm}  " + "  ".join(f"D{d:.0f}->{f:6.2f}({f-d:+5.2f})" for d, f, _ in out)
          + f"   | J {out[1][2][0]:.2e} b {out[1][2][1]:+.2e} gk {out[1][2][2]:+.3f} F {out[1][2][3]:+.4f}")
