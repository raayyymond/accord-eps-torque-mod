"""Shared loader for the A340 buzz study. Cache only (npz from a340_buzz_extract*.py). Seconds per route.

Signals on the 0x14A timebase (100 Hz, bus 1):
  ang  = -0.1*s16(14A b0-1) deg            rate = -s16(14A b2-3) deg/s
  rate8= -s16(18F b2-3)/8 deg/s (finer copy, fit slope -7.999, r 0.9999 on 3 routes)
  tq   = -s16(18F b0-1)  (== carState.steeringTorque, slope 0.995-1.000, r >= 0.998)
  cmd  = s16(E4 b0-1), req = E4 b2 bit7 (A340 only; A160 has no E4 on bus 1 -> latActive)
  m1ab = ((1AB b0 & 3)<<8)|b1  (50 Hz, unsigned magnitude field; layout BELIEF from opendbc-style MOTOR_TORQUE)
Buzz metric BZ = rms over 0.32 s of the >10 Hz (4th-order Butterworth, zero-phase) wheel rate, deg/s.
"""
import os, glob
import numpy as np
from scipy import signal

FS = 100.0
HB, HA = signal.butter(4, 10 / 50, "high")
L3B, L3A = signal.butter(2, 3 / 50, "low")
L2B, L2A = signal.butter(2, 2 / 50, "low")


def s16(d, i):
    return ((d[:, i].astype(np.int32) << 8) | d[:, i + 1]).astype(np.int16).astype(float)


def movrms(x, k=32):
    return np.sqrt(np.convolve(x * x, np.ones(k) / k, "same"))


def load(p):
    z = np.load(p)
    t0 = float(z["t0"])
    t = z["t_14a"] - t0
    n = len(t)
    n18 = len(z["t_18f"])
    d18 = z["d_18f"]
    t18 = z["t_18f"] - t0
    ang = -0.1 * s16(z["d_14a"], 0)
    rate = -s16(z["d_14a"], 2)
    tq = np.interp(t, t18, -s16(d18, 0))
    rate8 = np.interp(t, t18, -s16(d18, 2) / 8.0)
    cs = z["cs"]
    cc = z["cc"]
    v = np.interp(t, cs[:, 0] - t0, cs[:, 1])
    pressed = np.interp(t, cs[:, 0] - t0, cs[:, 6]) > 0.5
    lat = np.interp(t, cc[:, 0] - t0, cc[:, 1]) > 0.5 if len(cc) else np.zeros(n, bool)
    if len(z["t_e4"]) > 0.9 * n:
        te4 = z["t_e4"] - t0
        cmd = np.interp(t, te4, s16(z["d_e4"], 0))
        req = np.interp(t, te4, (z["d_e4"][:, 2] >> 7) & 1) > 0.5
        has_e4 = True
    else:
        cmd = np.full(n, np.nan)
        req = lat.copy()
        has_e4 = False
    d1 = z["d_1ab"]
    t1 = z["t_1ab"] - t0
    m1ab = (((d1[:, 0].astype(np.int32) & 3) << 8) | d1[:, 1]).astype(float)
    hr = signal.filtfilt(HB, HA, rate)
    ht = signal.filtfilt(HB, HA, tq)
    rlp = signal.filtfilt(L3B, L3A, rate)
    tlp = signal.filtfilt(L2B, L2A, tq)
    return dict(t=t, tabs=z["t_14a"], ang=ang, rate=rate, rate8=rate8, tq=tq, v=v, pressed=pressed, lat=lat,
                cmd=cmd, req=req, has_e4=has_e4, t1ab=t1, m1ab=m1ab, d1ab=d1, d18f=d18, d14a=z["d_14a"],
                hr=hr, ht=ht, rlp=rlp, tlp=tlp, bz=movrms(hr), bzt=movrms(ht))


def segs(C):
    out = []
    for p in sorted(glob.glob(os.path.join(C, "seg*.npz"))):
        out.append((int(os.path.basename(p)[3:5]), p))
    return out
