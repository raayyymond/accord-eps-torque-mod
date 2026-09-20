# -*- coding: utf-8 -*-
"""SUPPRESSOR stream, own library.

QUESTION: the 1.8-3.5 Hz wheel shake is the PLANT, and it is what caps the loop gain.  Can the fork
attenuate 1.8-3.5 Hz without spending 0.15-0.60 Hz -- and how much more loop gain does that buy?

Nodes (controlsState clock, cache from build_cache.py):
  X  model desired lateral accel   cs_des_curv * vEgo^2                 m/s^2
  Z  shaped setpoint               cs_la_des                            m/s^2
  M  fed-back measurement          cs_la_act (wheel angle, static map)  m/s^2
  Y  achieved lateral accel        livePose wz * vEgo                   m/s^2
  U  command                       -cs_out (= output_torque)            [-1,1]
  SR wheel rate                    carState.steeringRateDeg             deg/s
  E  LOGGED pid_log.error          cs_err  (= error_with_lsf AFTER the notch)   m/s^2

Every filter response here is the EXACT DISCRETE response of the fork's own code at dt = 0.01 s
(FirstOrderFilter: alpha = dt/(rc+dt); HondaAccordErrorNotch: the bilinear biquad in
latcontrol_vehicle_tunes.py:2679-2691), never a continuous-time approximation.

ANALYSIS ONLY.  Read-only on the fork and the logs; writes only under this folder.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402  (cache loader + run masking only)

FS = 100.0
DT = 0.01
OUT = HERE / "out"

GAP = (0.15, 0.60)        # where the tracking gap lives
SHAKE = (1.8, 3.5)        # where the shake lives
METRIC = (0.15, 2.40)     # the goal metric's band

# ---------------------------------------------------------------------------------------------
# fork constants, transcribed HERE from the source (so a transcription error cannot come in from
# another stream).  latcontrol_vehicle_tunes.py lines given.
# ---------------------------------------------------------------------------------------------
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]          # :230
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103,
            0.0116, 0.0133, 0.0160]                                                  # :236
EPS_INERTIA = 8e-5                                                                   # :279
RATE_LOOP_RC = 0.01                                                                  # :286
RATE_LOOP_TAPER_V = 12.0                                                             # :293
EPS_G_BP = [5.0, 12.5, 18.5, 28.5]                                                   # :175
EPS_G_V = [550.0, 271.0, 246.0, 167.0]                                               # :176
JERK_LP_HZ = 4.0                                                                     # :198 (84766cdc5 only)
LP_FILTER_CUTOFF_HZ = 1.2                                                            # generic, every other commit
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0.0, 10.0, 20.0, 30.0], [12.0, 10.5, 8.0, 5.0], 1.0

# per-route flown config, each from its OWN initData (hsurface/surface/params_all.json), transcribed here.
FLOWN = {
    "00000064--ce6b0b0ebb": dict(fam="V282", eps="V282", kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0,
                                 notch=False, rf=None, rlg=None, jerk=1.2, dob=0.0),
    "00000065--b9f78988bd": dict(fam="V282", eps="V282", kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0,
                                 notch=False, rf=None, rlg=None, jerk=1.2, dob=0.0),
    "0000006c--2bc842dbac": dict(fam="V282", eps="V282", kp=0.9, laf=6.0, ki=0.3, ki_hi=0.0,
                                 notch=False, rf=None, rlg=None, jerk=1.2, dob=0.0),
    "0000006c--68c6e94b17": dict(fam="T64", eps="V293", kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0,
                                 notch=True, rf=0.06, rlg=0.001, jerk=4.0, dob=0.6),
    "0000006d--05e83bb04f": dict(fam="T64", eps="V293", kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0,
                                 notch=True, rf=0.06, rlg=0.001, jerk=4.0, dob=0.6),
    "0000006e--6ca3e014fd": dict(fam="T64B", eps="V293", kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0,
                                 notch=True, rf=0.06, rlg=0.001, jerk=4.0, dob=0.6),
    "00000076--d0b7ea7e4d": dict(fam="T5", eps="V293", kp=1.0, laf=14.0, ki=0.3, ki_hi=0.0,
                                 notch=True, rf=0.12, rlg=0.001, jerk=1.2, dob=0.6),
    "00000075--6c8687d5bd": dict(fam="T4", eps="V293", kp=0.85, laf=14.0, ki=0.6, ki_hi=2.5,
                                 notch=True, rf=0.12, rlg=0.0006, jerk=1.2, dob=0.0),
    "00000072--8001fc3048": dict(fam="T3", eps="V293", kp=0.85, laf=14.0, ki=0.6, ki_hi=0.0,
                                 notch=True, rf=0.12, rlg=0.0006, jerk=1.2, dob=0.0),
    "00000071--f2c9d073a3": dict(fam="T2", eps="V293", kp=0.85, laf=14.0, ki=0.3, ki_hi=0.0,
                                 notch=False, rf=None, rlg=None, jerk=1.2, dob=0.0),
    "00000070--717f5a7866": dict(fam="RF00T", eps="V293", kp=0.3, laf=6.0, ki=0.15, ki_hi=0.0,
                                 notch=False, rf=None, rlg=None, jerk=1.2, dob=0.0),
}
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
TORQ = [r for r, d in FLOWN.items() if d["eps"] == "V293"]
V282R = [r for r, d in FLOWN.items() if d["eps"] == "V282"]


def lsf(v):
    """low_speed_factor, latcontrol_torque.py:339."""
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def mode_hz(v):
    """get_honda_accord_mode_hz: the error notch's CENTRE, sqrt(k(v)/J)/2pi  (tunes :2630)."""
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2.0 * np.pi)


def rate_loop_gain(v, g):
    """get_honda_accord_rate_loop_gain: tapered above 12 m/s (tunes :2644)."""
    return g * np.minimum(1.0, RATE_LOOP_TAPER_V / np.maximum(v, 0.1))


# ---------------------------------------------------------------------------------------------
# EXACT discrete responses of the fork's own filters
# ---------------------------------------------------------------------------------------------
def fof_H(f, rc, dt=DT):
    """One FirstOrderFilter (common/filter_simple.py): alpha = dt/(rc+dt)."""
    a = dt / (rc + dt)
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return a / (1.0 - (1.0 - a) * z)


def notch_H(f, f0, q=1.0, dt=DT):
    """HondaAccordErrorNotch.update's coefficients, exactly (tunes :2679-2691).
    q <= 0 or f0 <= 0 => pass-through (the code returns x and primes the state)."""
    f = np.asarray(f, float)
    if q <= 0.0 or f0 <= 0.0:
        return np.ones_like(f, dtype=complex)
    k = np.tan(np.pi * min(float(f0), 0.45 / dt) * dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(-2j * np.pi * f * dt)
    return (b0 + b1 * z + b0 * z * z) / (1.0 + b1 * z + a2 * z * z)


def notch_run(x, f_hz, q, dt=DT):
    """HondaAccordErrorNotch.update, frame by frame, with the fork's own state handling.
    f_hz may be an array (the fork recomputes coefficients EVERY frame from vEgo)."""
    x = np.asarray(x, float)
    f_hz = np.broadcast_to(np.asarray(f_hz, float), x.shape)
    y = np.empty_like(x)
    x1 = x2 = y1 = y2 = float(x[0]) if len(x) else 0.0
    for n in range(len(x)):
        xn = x[n]
        f0 = f_hz[n]
        if q <= 0.0 or f0 <= 0.0:
            x1 = x2 = y1 = y2 = xn
            y[n] = xn
            continue
        k = np.tan(np.pi * min(float(f0), 0.45 / dt) * dt)
        norm = 1.0 / (1.0 + k / q + k * k)
        b0 = (1.0 + k * k) * norm
        b1 = 2.0 * (k * k - 1.0) * norm
        a2 = (1.0 - k / q + k * k) * norm
        yn = b0 * xn + b1 * x1 + b0 * x2 - b1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xn, y1, yn
        y[n] = yn
    return y


def fof_run(x, rc, dt=DT, x0=None):
    """FirstOrderFilter.update frame by frame (rc may be an array)."""
    x = np.asarray(x, float)
    rc = np.broadcast_to(np.asarray(rc, float), x.shape)
    y = np.empty_like(x)
    s = float(x[0]) if x0 is None else float(x0)
    for n in range(len(x)):
        a = dt / (rc[n] + dt)
        s += a * (x[n] - s)
        y[n] = s
    return y


# ---------------------------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------------------------
def load(rk):
    """All nodes on the controlsState clock, plus the LOGGED pid error (cs_err)."""
    S = V.load(rk)
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    n = dict(rk=rk, meta=FLOWN.get(rk, {}), t=S["t"], v=S["v"],
             X=np.nan_to_num(S["model"]), Z=np.nan_to_num(S["setpoint"]),
             M=np.nan_to_num(S["la_act"]), Y=np.nan_to_num(S["la_pose"]),
             U=-np.nan_to_num(S["out"]), SR=np.nan_to_num(S["sr"]), SA=np.nan_to_num(S["sa"]),
             P=np.nan_to_num(S["p"]), I=np.nan_to_num(S["i"]), F=np.nan_to_num(S["f"]),
             E=np.nan_to_num(D["cs_err"]), sat=S["sat"],
             fin=np.isfinite(S["model"]) & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"])
                 & np.isfinite(S["la_pose"]) & np.isfinite(S["out"]) & np.isfinite(S["sr"]),
             usable=V.usable(S))
    del S, D
    return n


def runs_of(N, vmin=15.0, vmax=99.0, minrun=30.0):
    m = N["usable"] & N["fin"] & (N["v"] >= vmin) & (N["v"] < vmax)
    return V.runs(m, N["t"], min_s=minrun)


def spectra(N, keys, vmin=15.0, vmax=99.0, nperseg=2048, minrun=30.0, overlap=0.5):
    """Hann rFFT of each key over overlapping windows inside contiguous engaged hands-off runs."""
    hop = max(int(nperseg * (1 - overlap)), 1)
    w = np.hanning(nperseg)
    fr = np.fft.rfftfreq(nperseg, DT)
    out = {k: [] for k in keys}
    vs = []
    for a, b in runs_of(N, vmin, vmax, minrun):
        for k0 in range(a, b - nperseg + 1, hop):
            sl = slice(k0, k0 + nperseg)
            for k in keys:
                s = N[k][sl]
                out[k].append(np.fft.rfft((s - s.mean()) * w))
            vs.append(float(np.median(N["v"][sl])))
    if not vs:
        return fr, {k: np.zeros((0, len(fr)), complex) for k in keys}, np.zeros(0)
    return fr, {k: np.asarray(out[k]) for k in keys}, np.asarray(vs)


def band(fr, f1, f2):
    return (fr >= f1) & (fr <= f2)


def H_xy(Sx, Sy, sel=None):
    """H1 estimator per bin: Sxy/Sxx, pooled over windows.  Returns (H, coh) arrays over bins."""
    Sxx = np.mean(np.abs(Sx) ** 2, 0)
    Syy = np.mean(np.abs(Sy) ** 2, 0)
    Sxy = np.mean(np.conj(Sx) * Sy, 0)
    H = Sxy / np.maximum(Sxx, 1e-300)
    coh = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-300)
    if sel is not None:
        return H[sel], coh[sel]
    return H, coh


def metric_J(SX, SE, sel):
    """The goal metric, unchanged: sum|E|^2 / sum|X|^2 over the band, ONE denominator."""
    return float(np.sum(np.abs(SE[:, sel]) ** 2) / np.sum(np.abs(SX[:, sel]) ** 2))


def bandrms(x, f1, f2, fs=FS):
    from scipy import signal as sg
    sos = sg.butter(4, [f1, f2], btype="band", fs=fs, output="sos")
    return float(np.sqrt(np.mean(sg.sosfiltfilt(sos, np.asarray(x, float)) ** 2)))


# ---------------------------------------------------------------------------------------------
def _self_test():
    """Positive controls with closed-form answers."""
    msgs = []
    # 1. notch_H against notch_run on white noise: the measured transfer must equal the analytic one.
    #    (Welch H1 on the steady-state part; the frame-by-frame filter starts from x[0], not zero.)
    from scipy import signal as sg
    rng = np.random.default_rng(3)
    x = rng.standard_normal(1 << 17)
    y = notch_run(x, 2.0, 1.0)
    xs, ys = x[2000:], y[2000:]
    fr, Pxx = sg.welch(xs, FS, nperseg=8192)
    _, Pxy = sg.csd(xs, ys, FS, nperseg=8192)
    Hm = Pxy / Pxx
    Ha = notch_H(fr, 2.0, 1.0)
    s = (fr > 0.05) & (fr < 20)
    assert np.max(np.abs(Hm[s] - Ha[s])) < 0.02, np.max(np.abs(Hm[s] - Ha[s]))
    msgs.append("notch_run == notch_H to 0.02 over 0.05-20 Hz (Welch H1)")
    # 2. the notch is exactly ZERO at its centre and 1 at DC
    assert abs(notch_H(0.0, 2.0, 1.0)) > 0.999
    assert abs(notch_H(2.0, 2.0, 1.0)) < 2e-3, abs(notch_H(2.0, 2.0, 1.0))
    msgs.append("notch: |H(0)| = 1, |H(f0)| < 2e-3")
    # 3. fof_run == fof_H
    y2 = fof_run(x, 0.12, x0=0.0)
    _, Pxy2 = sg.csd(x[2000:], y2[2000:], FS, nperseg=8192)
    Hm2 = Pxy2 / Pxx
    Ha2 = fof_H(fr, 0.12)
    assert np.max(np.abs(Hm2[s] - Ha2[s])) < 0.02, np.max(np.abs(Hm2[s] - Ha2[s]))
    msgs.append("fof_run == fof_H to 0.02")
    # 4. H_xy (the windowed-FFT estimator used on the logs) recovers a known filter
    nn = 4096
    segs_x, segs_y = [], []
    for k0 in range(2000, len(x) - nn, nn // 2):
        segs_x.append(np.fft.rfft((x[k0:k0 + nn] - x[k0:k0 + nn].mean()) * np.hanning(nn)))
        segs_y.append(np.fft.rfft((y[k0:k0 + nn] - y[k0:k0 + nn].mean()) * np.hanning(nn)))
    H, coh = H_xy(np.asarray(segs_x), np.asarray(segs_y))
    frq = np.fft.rfftfreq(nn, DT)
    for fq in (0.5, 1.0, 3.0):
        j = int(np.argmin(np.abs(frq - fq)))
        assert abs(abs(H[j]) - abs(notch_H(frq[j], 2.0, 1.0))) < 0.03, (fq, abs(H[j]))
    msgs.append("H_xy recovers the known notch gain at 0.5/1/3 Hz to 0.03")
    # 5. mode_hz spot value: 8 m/s -> sqrt(0.0052/8e-5)/2pi
    assert abs(mode_hz(8.0) - np.sqrt(0.0052 / 8e-5) / (2 * np.pi)) < 1e-12
    msgs.append(f"mode_hz(8) = {mode_hz(8.0):.3f} Hz (the 1.28 Hz on the table)")
    return "suplib self-test OK: " + "; ".join(msgs)


if __name__ == "__main__":
    print(_self_test())
