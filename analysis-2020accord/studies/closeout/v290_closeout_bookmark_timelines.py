# -*- coding: utf-8 -*-
"""Bookmark timelines for the V290 close-out artifact: band envelopes of the driver-torque bar in the 28 s around each
operator bookmark, from the v280-format route caches (0x18F bar at 100 Hz, raw x 1.024).  Bands: 5-12 Hz (the 7.5 Hz
strong-turn ring), 13-18 Hz (V289's new line), 18-22 Hz (the V282/V288 line).  Plus |0xE4 cmd|, wheel angle, speed and
the slew-capped-frame flag.  Output: analysis-2020accord/_scratch/out/v290_closeout_marks.json (20 Hz decimated).
Run: python v290_closeout_bookmark_timelines.py"""
import os, json, numpy as np
from scipy import signal
KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CACHE = os.path.join(KIT, "_scratch", "cache", "v280")
OUT = os.path.join(KIT, "_scratch", "out", "v290_closeout_marks.json")
FS = 100.0; PRE, POST = 25.0, 3.0
BANDS = {"b5_12": (5, 12), "b13_18": (13, 18), "b18_22": (18, 22)}
ROUTES = {"r62_v289": "V289", "r63_v289": "V289", "r5e_v288": "V288", "r39": "V282"}

def env(x, lo, hi):
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
    return np.abs(signal.hilbert(signal.sosfiltfilt(sos, x)))

out = {}
for key, build in ROUTES.items():
    D = np.load(os.path.join(CACHE, key + ".npz"), allow_pickle=True)
    M = json.load(open(os.path.join(CACHE, key + "_marks.json")))
    t18 = D["t18"] - M["t0_mono"]; bar = D["tq"] * 1.024; ang = D["ang"]
    te4 = D["te4"] - M["t0_mono"]; cmd = D["cmd"]; tcs = D["tcs"] - M["t0_mono"]; v = D["vego"]
    # uniform 100 Hz grid on the 0x18F clock
    tg = np.arange(t18[0], t18[-1], 1 / FS)
    t14 = D["t14"] - M["t0_mono"]; barg = np.interp(tg, t18, bar); angg = np.interp(tg, t14, ang)
    cmdg = np.interp(tg, te4, cmd); vg = np.interp(tg, tcs, v)
    dcmd = np.abs(np.diff(cmd, prepend=cmd[0])); capg = np.interp(tg, te4, (dcmd >= 122).astype(float))
    E = {k: env(barg, *b) for k, b in BANDS.items()}
    marks = []
    for m in M["marks"]:
        tm = m["t_route"]; sel = (tg >= tm - PRE) & (tg <= tm + POST)
        idx = np.flatnonzero(sel)[::5]  # 20 Hz
        rec = {"t_mark": round(float(tm), 2), "seg": m["seg"], "t_rel": [round(float(x - tm), 2) for x in tg[idx]],
               "ang": [round(float(x), 1) for x in angg[idx]], "cmd": [int(round(x)) for x in cmdg[idx]],
               "v": [round(float(x), 1) for x in vg[idx]], "cap": [round(float(x), 2) for x in capg[idx]]}
        for k in BANDS:
            e = E[k]; rec[k] = [round(float(x), 1) for x in e[idx]]
            w = sel & (tg <= tm)
            j = np.argmax(e[w]); rec[k + "_pk"] = round(float(e[w][j]), 1); rec[k + "_pk_t"] = round(float(tg[w][j] - tm), 2)
        marks.append(rec); print(key, tm, {k: (rec[k + "_pk"], rec[k + "_pk_t"]) for k in BANDS})
    out[key] = {"build": build, "marks": marks}
json.dump(out, open(OUT, "w"))
print("wrote", OUT)
