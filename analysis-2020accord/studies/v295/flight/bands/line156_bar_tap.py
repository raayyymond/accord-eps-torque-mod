# -*- coding: utf-8 -*-
"""line156_bar_tap.py -- in the one episode that carries the P2 line (r71b route time 41-47 s, ~1 m/s, near full lock,
hands on), which channels carry 15.6 Hz and how coherently: the driver-torque bar (0x18F), the wheel rate (0x18F),
the 0xE4 command, and the 427 tap.  A command without the line and a bar/rate/tap with it at high coherence says the
object is MECHANICAL (hand + column + motor) with the tap following it; whether the tap follows via the override
fade (bar) or via the acceleration trim (rate) is not separable here -- BELIEF, sized in the report from the design gain.
Subagent "bands", 2026-09-30.  EVIDENCE for the numbers.
"""
import os
import sys

import numpy as np
from scipy import signal as sg

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
for p in ("rlog-tools/studies/grind", "rlog-tools/studies/osc-highangle", "analysis-2020accord/studies/v280", "analysis-2020accord/lib"):
    sys.path.insert(0, os.path.join(KIT, p))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20   # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def lineamp(x, fs, lo=14.5, hi=16.8):
    sos = sg.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return float(np.sqrt(2) * sg.sosfiltfilt(sos, x - x.mean()).std())


def main():
    g = C20.load("r71b_v294")
    tr = g["t"] - g["t"][0]
    m = (tr >= 41.0) & (tr <= 47.0)
    pr("episode 41-47 s: eng share %.2f, v %.1f-%.1f m/s, |bar| p50 %.0f, |cmd| p50 %.0f (max %.0f), |angle| %.0f-%.0f deg"
       % (g["eng"][m].mean(), g["vego"][m].min(), g["vego"][m].max(), np.median(np.abs(g["bar"][m])),
          np.median(np.abs(g["cmd"][m])), np.abs(g["cmd"][m]).max(), np.abs(g["ang"][m]).min(), np.abs(g["ang"][m]).max()))
    a, b = np.flatnonzero(m)[0], np.flatnonzero(m)[-1]
    for nm, x in (("bar (driver torque, counts)", g["bar"][a:b]), ("wheel rate, deg/s", g["wire"][a:b] / 8),
                  ("0xE4 command, counts", g["cmd"][a:b])):
        f, P = sg.welch(x - x.mean(), fs=100, nperseg=256)
        s = (f >= 12) & (f <= 20)
        pr("  %-28s 14.5-16.8 Hz amplitude %7.2f   PSD peak in 12-20 Hz at %.2f Hz" % (nm, lineamp(x, 100), f[s][int(np.argmax(P[s]))]))
    tT = g["T_t"] - g["t"][0]
    mt = (tT >= 41) & (tT <= 47)
    T = g["T"][mt]
    f, P = sg.welch(T - T.mean(), fs=50, nperseg=128)
    s = (f >= 12) & (f <= 20)
    pr("  %-28s 14.5-16.8 Hz amplitude %7.2f   PSD peak in 12-20 Hz at %.2f Hz" % ("427 tap, counts", lineamp(T, 50), f[s][int(np.argmax(P[s]))]))
    Tz = np.interp(g["t"][a:b], g["T_t"], g["T"])
    f, C = sg.coherence(g["bar"][a:b], Tz, fs=100, nperseg=128)
    _, C2 = sg.coherence(g["wire"][a:b], Tz, fs=100, nperseg=128)
    _, C3 = sg.coherence(g["cmd"][a:b], Tz, fs=100, nperseg=128)
    s = (f >= 14) & (f <= 17)
    pr("  coherence 14-17 Hz: bar->tap %.2f   rate->tap %.2f   command->tap %.2f" % (C[s].mean(), C2[s].mean(), C3[s].mean()))
    open(os.path.join(HERE, "line156_bar_tap_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
