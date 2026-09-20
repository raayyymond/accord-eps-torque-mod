# -*- coding: utf-8 -*-
"""i1 -- FIND route 71's limit cycle IN THE LOG, independently.

No prior frequency is assumed.  The object is located by a spectrogram of the MEASURED steering
rate (carState.steeringRateDeg, the least-processed wheel signal in the cache), restricted to
laterally-engaged hands-off frames, and the dominant 1-6 Hz line is reported per window with its
amplitude in degrees (rate amplitude / 2*pi*f) and the driving conditions.

ANALYSIS ONLY.  python i1_findcycle.py [route]
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
NPS = 512          # 5.12 s -> df 0.195 Hz
HOP = 128          # 1.28 s


def spectro(route, band=(1.0, 6.0), require_engaged=True):
    S = V.load(route)
    t, v, sr, sa = S["t"], S["v"], S["sr"], S["sa"]
    eng = S["active"]
    pressed = S["pressed"]
    n = len(t)
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / FS)
    sel = (f >= band[0]) & (f <= band[1])
    rows = []
    for s in range(0, n - NPS + 1, HOP):
        e = s + NPS
        if np.any(np.diff(t[s:e]) > 4.0 / FS):
            continue
        if require_engaged and not eng[s:e].all():
            continue
        if require_engaged and pressed[s:e].any():
            continue
        x = np.nan_to_num(sr[s:e])
        if not np.isfinite(x).all():
            continue
        Xf = np.fft.rfft(signal.detrend(x) * w)
        # amplitude of a sinusoid: 2*|X|/(sum(w))
        amp_rate = 2.0 * np.abs(Xf) / np.sum(w)
        k = int(np.argmax(amp_rate[sel]))
        kk = int(np.where(sel)[0][0]) + k
        # parabolic interpolation on the log magnitude for a sub-bin frequency
        if 0 < kk < len(f) - 1:
            a, b, c = np.log(amp_rate[kk - 1] + 1e-30), np.log(amp_rate[kk] + 1e-30), np.log(amp_rate[kk + 1] + 1e-30)
            d = 0.5 * (a - c) / max(a - 2 * b + c, 1e-12) if (a - 2 * b + c) != 0 else 0.0
            d = float(np.clip(d, -0.5, 0.5))
        else:
            d = 0.0
        fpk = f[kk] + d * (f[1] - f[0])
        arate = float(amp_rate[kk])
        rows.append(dict(i=s, t=float(t[s]), f=float(fpk), amp_rate=arate,
                         amp_deg=arate / (2 * np.pi * max(fpk, 1e-6)),
                         v=float(np.median(v[s:e])), sa=float(np.median(sa[s:e])),
                         sa_abs=float(np.median(np.abs(sa[s:e]))),
                         band_rms=float(np.sqrt(np.mean(signal.sosfiltfilt(
                             signal.butter(4, band, btype="band", fs=FS, output="sos"), x) ** 2))),
                         tot_rms=float(np.std(x))))
    del S
    return rows


if __name__ == "__main__":
    routes = sys.argv[1:] or ["00000071--f2c9d073a3"]
    for r in routes:
        rows = spectro(r)
        if not rows:
            print(f"{r}: no engaged windows")
            continue
        fr = np.array([x["f"] for x in rows])
        ad = np.array([x["amp_deg"] for x in rows])
        br = np.array([x["band_rms"] for x in rows])
        vv = np.array([x["v"] for x in rows])
        print(f"\n=== {r}  {len(rows)} engaged windows ({len(rows)*HOP/FS:.0f} s of hop) ===")
        # histogram of the dominant line
        hist, edges = np.histogram(fr, bins=np.arange(1.0, 6.2, 0.2))
        for h, lo in zip(hist, edges[:-1]):
            if h:
                m = (fr >= lo) & (fr < lo + 0.2)
                print(f"   {lo:4.1f}-{lo+0.2:4.1f} Hz  n={h:4d}  med amp {np.median(ad[m]):6.3f} deg  "
                      f"med band-rms {np.median(br[m]):6.3f} deg/s  med v {np.median(vv[m]):5.1f}")
        # the biggest windows
        k = np.argsort(-br)[:15]
        print("   --- 15 loudest 1-6 Hz windows ---")
        print("      t(s)     f(Hz)  amp(deg)  bandRMS  totRMS   v   |sa|")
        for j in k:
            x = rows[j]
            print(f"   {x['t']:8.1f}  {x['f']:6.2f}  {x['amp_deg']:8.3f}  {x['band_rms']:7.3f} "
                  f"{x['tot_rms']:7.2f}  {x['v']:5.1f} {x['sa_abs']:6.1f}")
