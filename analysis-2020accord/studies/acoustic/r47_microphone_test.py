#!/usr/bin/env python3
"""studies/acoustic/r47_microphone_test.py -- the ONLY instrument in this kit with no ~50 Hz ceiling.

Both the EPS CAN grid (100.000 Hz) and the comma IMU (~101 Hz) have a Nyquist of ~50 Hz, so if the
operator's felt highway resonance is genuinely ABOVE 50 Hz, every vibration measurement here is
structurally blind to it and a null means nothing. `soundPressure` is computed on-device from audio
sampled at 16-48 kHz and logged as a LEVEL at ~10 Hz: it cannot give a spectrum, but it CAN answer
"is there more acoustic energy during the maneuver than during a speed-matched control", with no
frequency ceiling at all. Grind #2 was described as "makes the entire car vibrate, almost like I
have a subwoofer" -- an audible event.

🛑 A-WEIGHTING IS THE TRAP. The A curve is -30 dB at 50 Hz and -19 dB at 100 Hz, so
`soundPressureWeightedDb`/`soundPressureWeighted` deliberately SUPPRESS the band in question. The
UN-WEIGHTED `soundPressure` is the primary channel; the weighted one is kept as a contrast, because
un-weighted rising while weighted stays flat is itself evidence the energy is LOW-frequency.

⚠ CONFOUND, and it is the reason this test needs matched controls rather than a raw comparison:
road/wind noise dominates cabin sound and scales steeply with speed. The atlas controls are
speed-matched straight-line windows from the SAME route, which is what makes the contrast readable.

Usage:  python studies/acoustic/r47_microphone_test.py [--extract]
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "rlog-tools"))
RLOG = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000047--3e0b6134c0"
OUT = ROOT / "_scratch/cache/r47"


def extract():
    from rlog_parse import read_messages
    for s in range(26):
        f = OUT / f"r47s{s}_snd.npz"
        if f.exists():
            continue
        try:
            t0 = float(np.load(OUT / f"r47s{s}.npz")["t0_mono"][0])
        except Exception:
            continue
        t, u, w, db = [], [], [], []
        for evt in read_messages(RLOG / f"{ROUTE}--{s}--rlog.zst"):
            try:
                if evt.which() != "soundPressure":
                    continue
            except Exception:
                continue
            m = evt.soundPressure
            t.append(evt.logMonoTime * 1e-9 - t0)
            u.append(float(m.soundPressure))
            w.append(float(m.soundPressureWeighted))
            db.append(float(m.soundPressureWeightedDb))
        np.savez_compressed(f, t=np.array(t), unw=np.array(u), wt=np.array(w), db=np.array(db))
        print(f"  s{s:<3d} {len(t):5d} samples  {1/np.median(np.diff(t)):.2f} Hz")


KEYMAP = {"unw": ("unw", "sp"), "wt": ("wt", "spw"), "db": ("db", "spwdb")}


def _level(ep, key="unw"):
    """Max level inside an episode, cut per-segment via the atlas `spans` (never across a join)."""
    best = []
    for sp in ep["spans"]:
        f = OUT / f"r47s{sp['seg']}_snd.npz"
        if not f.exists():
            continue
        d = np.load(f)
        k = next((c for c in KEYMAP[key] if c in d), None)   # accept either extractor's naming
        if k is None:
            continue
        m = (d["t"] >= sp["t0"]) & (d["t"] <= sp["t1"])
        if m.sum() >= 3:
            best.append(np.percentile(d[k][m], 90))
    return float(np.max(best)) if best else np.nan


def report():
    A = json.load(open(OUT / "r47_maneuvers.json"))
    rng = np.random.default_rng(5)
    print(__doc__.split("Usage:")[0].rstrip())
    print("\n" + "=" * 96)
    print("HIGHWAY MANEUVER vs MATCHED STRAIGHT-LINE CONTROL -- p90 level per episode, paired")
    print(f"{'channel':>28s} {'maneuver':>10s} {'control':>10s} {'ratio':>7s}   {'paired [boot 95%]':>22s}")
    for key, lab in (("unw", "soundPressure (UN-weighted)"), ("wt", "soundPressureWeighted (A)"),
                     ("db", "soundPressureWeightedDb")):
        a = np.array([_level(e, key) for e in A["maneuvers"]])
        b = np.array([_level(e, key) for e in A["controls"]])
        ok = np.isfinite(a) & np.isfinite(b)
        a, b = a[ok], b[ok]
        if len(a) < 5:
            print(f"{lab:>28s}   too few paired episodes ({len(a)})")
            continue
        pr = a / b
        bs = [np.median(pr[rng.integers(0, len(pr), len(pr))]) for _ in range(4000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f"{lab:>28s} {np.median(a):10.4f} {np.median(b):10.4f} "
              f"{np.median(a)/np.median(b):7.3f}   {np.median(pr):6.3f} [{lo:5.3f}, {hi:5.3f}]  n={len(a)}")
    # split-half null inside the CONTROL set, same estimator
    print("\nSplit-half NULL inside the control set (identical estimator, no real contrast expected):")
    for key, lab in (("unw", "soundPressure (UN-weighted)"), ("wt", "soundPressureWeighted (A)")):
        b = np.array([_level(e, key) for e in A["controls"]])
        b = b[np.isfinite(b)]
        rr = []
        for _ in range(600):
            p = rng.permutation(len(b))
            h = len(b) // 2
            rr.append(np.median(b[p[:h]]) / max(np.median(b[p[h:2*h]]), 1e-12))
        print(f"{lab:>28s}   null [{np.percentile(rr,2.5):5.3f}, {np.percentile(rr,97.5):5.3f}]")
    print("\n\u21d2 READ IT THIS WAY: un-weighted ABOVE its null with A-weighted inside its own null would")
    print("  mean real acoustic energy concentrated at LOW frequency. Both inside their nulls means the")
    print("  microphone sees nothing the matched controls do not -- which, since it has NO frequency")
    print("  ceiling, is the only evidence in this kit that can speak to a >50 Hz event.")


if __name__ == "__main__":
    if "--extract" in sys.argv:
        extract()
    report()
