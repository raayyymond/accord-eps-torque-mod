#!/usr/bin/env python3
r"""Route 95 (V101, the 8x LKAS gain) -- RECONNAISSANCE.

Finds the dominant oscillation in the engaged data before any hypothesis is scored.
Uses `analysis-2020accord/_cache_r95/r95.npz` written by `extract_r95.py`.
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
Z = dict(np.load(ROOT / "analysis-2020accord/_cache_r95/r95.npz", allow_pickle=True))

t = np.asarray(Z["t"], float)
n = len(t)
dt = np.diff(t)
print(f"rows {n:,}   t {t[0]:.2f}..{t[-1]:.2f} s   dt median {np.median(dt)*1e3:.3f} ms  "
      f"dt p99 {np.percentile(dt,99)*1e3:.3f} ms  max gap {dt.max()*1e3:.1f} ms  "
      f"n(dt>0.05) {int((dt>0.05).sum())}   n(dt==0) {int((dt<=0).sum())}")
FS = 1.0 / np.median(dt)
print(f"FS = {FS:.3f} Hz")

lat = np.asarray(Z["cc_lat"], float) > 0.5
vk = np.abs(np.asarray(Z["cs_v"], float)) * 3.6
vr = np.asarray(Z["v_rear"], float)
print(f"engaged {lat.sum():,} frames = {lat.sum()/FS:.1f} s")
print(f"v_rear vs cs_v*3.6: corr {np.corrcoef(vr, vk)[0,1]:.5f}  "
      f"median diff {np.median(vr-vk):+.3f} km/h")

# episode boundaries
d = np.diff(lat.astype(int))
starts = list(np.where(d == 1)[0] + 1)
ends = list(np.where(d == -1)[0] + 1)
if lat[0]:
    starts = [0] + starts
if lat[-1]:
    ends = ends + [n]
print("\nENGAGED EPISODES:")
for i, (a, b) in enumerate(zip(starts, ends)):
    print(f"  ep{i}: rows {a:6d}..{b:6d}  t {t[a]:7.2f}..{t[b-1]:7.2f} s  "
          f"dur {t[b-1]-t[a]:6.2f} s   v {vk[a:b].min():5.1f}..{vk[a:b].max():5.1f} km/h "
          f"(med {np.median(vk[a:b]):5.1f})")

CH = {
    "tq        driver torsion-bar (0x18F)": np.asarray(Z["tq"], float),
    "ang       steering angle deg (0x14A)": np.asarray(Z["ang"], float),
    "rate_f    fine angle rate deg/s     ": np.asarray(Z["rate_f"], float),
    "rate_c    coarse angle rate deg/s   ": np.asarray(Z["rate_c"], float),
    "wang      wheel/pinion angle deg    ": np.asarray(Z["wang"], float),
    "x6b94     AGGREGATOR OUT counts(427)": np.asarray(Z["x6b94"], float),
    "e4tq      openpilot LKAS cmd (rx)   ": np.asarray(Z["e4tq"], float),
    "sc_tq     openpilot LKAS cmd (tx)   ": np.asarray(Z["sc_tq"], float),
    "imu_lat   IMU lateral m/s2          ": np.asarray(Z["imu_lat"], float),
}


def welch(x, m, nfft=512, ov=2):
    """Non-overlapping-in-dof Hann Welch on the masked CONTIGUOUS runs only."""
    idx = np.where(m)[0]
    if len(idx) < nfft:
        return None, None, 0
    runs, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            runs.append((s, prev + 1))
            s = i
        prev = i
    runs.append((s, prev + 1))
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    P = np.zeros(len(f))
    K = 0
    step = nfft // ov
    for a, b in runs:
        for i in range(a, b - nfft + 1, step):
            seg = x[i:i + nfft]
            if not np.all(np.isfinite(seg)):
                continue
            X = np.fft.rfft((seg - seg.mean()) * win)
            P += np.abs(X) ** 2
            K += 1
    if K == 0:
        return None, None, 0
    P /= K * (win ** 2).sum() * FS
    return f, P, K


print("\n" + "=" * 100)
print("ENGAGED SPECTRA -- top 6 peaks above 2 Hz, per channel (Welch nfft=512, 50% overlap)")
print("=" * 100)
for name, x in CH.items():
    f, P, K = welch(x, lat)
    if f is None:
        print(f"  {name}: too few samples")
        continue
    band = (f >= 2.0) & (f <= 45.0)
    fb, Pb = f[band], P[band]
    # local maxima
    pk = [(Pb[i], fb[i]) for i in range(1, len(fb) - 1) if Pb[i] > Pb[i - 1] and Pb[i] > Pb[i + 1]]
    pk.sort(reverse=True)
    tot = np.trapezoid(Pb, fb)
    print(f"\n  {name}   K={K}  band-RMS(2-45Hz)={np.sqrt(tot):.4g}")
    for p, ff in pk[:6]:
        print(f"      {ff:6.2f} Hz  PSD {p:11.4g}   (x median PSD in band = "
              f"{p/np.median(Pb):6.1f})")
