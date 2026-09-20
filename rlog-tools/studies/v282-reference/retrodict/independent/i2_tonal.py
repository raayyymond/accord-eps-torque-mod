# -*- coding: utf-8 -*-
"""i2 -- isolate NARROWBAND sustained oscillation (a limit cycle), not maneuver energy.

A limit cycle is (i) narrowband -- the peak carries a large share of the 1-6 Hz power, (ii) sustained
over several cycles, (iii) at a frequency that does not wander.  A hard steering maneuver is broadband
and its energy sits below ~1 Hz, so the tonality ratio separates them.

Per 5.12 s window (hop 1.28 s), on engaged hands-off frames:
    tonal = power in [f_pk +/- 0.35 Hz] / power in [1, 6] Hz   of the MEASURED steering rate
    amp   = sinusoid amplitude at f_pk, in DEGREES of wheel angle

Reported: every run of >= 3 consecutive windows with tonal >= TONAL and amp >= AMP.

ANALYSIS ONLY.  python i2_tonal.py <route> [...]
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
NPS, HOP = 512, 128
BAND = (1.0, 6.0)
HALF = 0.35
TONAL = 0.45
AMP = 0.30          # deg


def scan(route):
    S = V.load(route)
    t, v, sr, sa = S["t"], S["v"], S["sr"], S["sa"]
    eng, pressed = S["active"], S["pressed"]
    out_sig = S["out"]
    n = len(t)
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / FS)
    inb = (f >= BAND[0]) & (f <= BAND[1])
    rows = []
    for s in range(0, n - NPS + 1, HOP):
        e = s + NPS
        if np.any(np.diff(t[s:e]) > 4.0 / FS):
            continue
        if not eng[s:e].all() or pressed[s:e].any():
            continue
        x = np.nan_to_num(sr[s:e])
        if not np.isfinite(x).all():
            continue
        X = np.fft.rfft(signal.detrend(x) * w)
        P = np.abs(X) ** 2
        kk = int(np.where(inb)[0][0]) + int(np.argmax(P[inb]))
        fpk = f[kk]
        near = (f >= fpk - HALF) & (f <= fpk + HALF)
        tonal = float(P[near].sum() / max(P[inb].sum(), 1e-30))
        amp_rate = 2.0 * np.abs(X[kk]) / np.sum(w)
        rows.append(dict(i=s, t=float(t[s]), f=float(fpk), tonal=tonal,
                         amp=float(amp_rate / (2 * np.pi * max(fpk, 1e-6))),
                         v=float(np.median(v[s:e])), sa=float(np.median(np.abs(sa[s:e]))),
                         u=float(np.std(np.nan_to_num(out_sig[s:e]))),
                         lo=float(np.sqrt(np.mean(signal.sosfiltfilt(
                             signal.butter(4, 1.0, btype="low", fs=FS, output="sos"), x) ** 2)))))
    del S
    return rows


def runs_of(rows, tonal=TONAL, amp=AMP, minlen=3):
    ok = [r["tonal"] >= tonal and r["amp"] >= amp for r in rows]
    out, i = [], 0
    while i < len(rows):
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(rows) and ok[j + 1] and (rows[j + 1]["t"] - rows[j]["t"]) < 2.0:
            j += 1
        if j - i + 1 >= minlen:
            out.append(rows[i:j + 1])
        i = j + 1
    return out


if __name__ == "__main__":
    for route in sys.argv[1:]:
        rows = scan(route)
        if not rows:
            print(f"{route}: no engaged windows")
            continue
        R = runs_of(rows)
        tot = len(rows) * HOP / FS
        print(f"\n=== {route}  {len(rows)} windows ({tot:.0f} s)  tonal>={TONAL} amp>={AMP} deg ===")
        nw = sum(len(r) for r in R)
        print(f"    {len(R)} runs, {nw} windows ({nw*HOP/FS:.0f} s), "
              f"{100.0*nw/len(rows):.1f} % of engaged time")
        for r in R:
            fs_ = np.array([x["f"] for x in r]); a = np.array([x["amp"] for x in r])
            print(f"    t {r[0]['t']:7.1f} - {r[-1]['t']+NPS/FS:7.1f} s ({len(r)*HOP/FS+NPS/FS:5.1f} s)  "
                  f"f {fs_.mean():5.2f} +/- {fs_.std():4.2f} Hz  amp {a.max():6.3f} deg peak / "
                  f"{np.median(a):6.3f} med  v {np.median([x['v'] for x in r]):5.1f}  "
                  f"|sa| {np.median([x['sa'] for x in r]):6.1f}  tonal {np.median([x['tonal'] for x in r]):4.2f}")
