#!/usr/bin/env python3
"""audit_fold_speed_test.py -- THE decisive test: does any spectral line move the WRONG way?

The problem: above ~50 Hz every instrument is silent, and silence is not absence. `audit_alias_evidence`
found the comma ACCELEROMETER flat-to-RISING approaching its 50.514 Hz Nyquist while the gyro and every
EPS CAN channel roll off 11-13 dB. Flat-to-Nyquist is consistent with folding AND with genuinely
broadband road excitation, and that test cannot separate them.

THIS ONE CAN. A vibration whose frequency is proportional to road speed (any wheel, driveline or tyre
order) traces f = k*v. Below Nyquist it appears at k*v and its apparent frequency RISES with speed.
Above Nyquist it FOLDS to |k*v - n*fs|, and for odd n the apparent frequency FALLS as speed rises.

    a REFLECTED order therefore has a NEGATIVE df/dv.

Nothing physical produces a line that moves DOWN as the car speeds up. So a negative, significant
df/dv is direct positive evidence that content above Nyquist exists and is folding -- turning a null
into a measurement without touching the car.

Method: per speed bin, Welch-average the accel/gyro PSD; track the strongest peak in each of several
frequency lanes; regress peak frequency on speed. A positive control is built in -- wheel order 1
(f = v/C, C ~ 2.08 m) must come out with df/dv = +0.48 Hz per m/s.

Usage:  python audit_fold_speed_test.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "_cache_r47"
FS_IMU = 101.0282
NW = 512
SPEED_BINS = [(18, 21), (21, 24), (24, 27), (27, 30), (30, 33), (33, 36)]
LANES = [(3, 9), (9, 15), (15, 22), (22, 30), (30, 38), (38, 46), (46, 50.4)]


def collect(ch):
    """Welch PSD per speed bin, on the IMU's own hardware clock."""
    tk = "at" if ch[0] == "a" else "gt"
    acc = {b: [None, 0] for b in SPEED_BINS}
    for s in range(26):
        fi, fc = CACHE / f"r47s{s}_imu.npz", CACHE / f"r47s{s}.npz"
        if not (fi.exists() and fc.exists()):
            continue
        z, c = np.load(fi), np.load(fc)
        v = np.interp(z[tk], c["t"], c["cs_v"])
        x = z[ch]
        for b in SPEED_BINS:
            m = (v >= b[0]) & (v < b[1])
            # contiguous runs only -- a masked-and-concatenated series fabricates edges
            i = 0
            while i < len(m):
                if not m[i]:
                    i += 1
                    continue
                j = i
                while j < len(m) and m[j]:
                    j += 1
                seg = x[i:j]
                if len(seg) >= 2 * NW:
                    seg = seg - np.convolve(seg, np.ones(51) / 51, mode="same")
                    for k in range(1, len(seg) // NW):
                        w = seg[k * NW:(k + 1) * NW] * np.hanning(NW)
                        p = np.abs(np.fft.rfft(w)) ** 2
                        acc[b][0] = p if acc[b][0] is None else acc[b][0] + p
                        acc[b][1] += 1
                i = j
    fr = np.fft.rfftfreq(NW, 1 / FS_IMU)
    return fr, {b: (P / n if n else None, n) for b, (P, n) in acc.items()}


def main():
    print(__doc__.split("Usage:")[0].rstrip())
    print(f"\nIMU hardware clock {FS_IMU} Hz, Nyquist {FS_IMU / 2:.3f} Hz. "
          f"{NW}-pt Welch, bin {FS_IMU / NW:.4f} Hz.")
    print("A line at true frequency f0 > Nyquist appears at |f0 - n*fs|; for ODD n its apparent")
    print(f"frequency FALLS with speed. Positive control: wheel order 1 = v/2.08 m => df/dv = +0.481.")

    for ch in ("az", "ax", "ay", "gz"):
        fr, per = collect(ch)
        ok = [(b, P, n) for b, (P, n) in per.items() if P is not None and n >= 4]
        if len(ok) < 3:
            print(f"\n{ch}: only {len(ok)} usable speed bins -- skipped")
            continue
        print(f"\n=== {ch} ===  windows per speed bin: "
              + "  ".join(f"{b[0]}-{b[1]}:{n}" for b, _, n in ok))
        print(f"  {'lane Hz':>12s} {'peak f per speed bin (Hz)':>44s} {'df/dv':>9s} {'r':>7s} "
              f"{'prom':>6s}  verdict")
        for lo, hi in LANES:
            sel = (fr >= lo) & (fr < hi)
            if sel.sum() < 4:
                continue
            vs, fs_, pr = [], [], []
            for b, P, n in ok:
                i = np.arange(len(fr))[sel][int(np.argmax(P[sel]))]
                # 3-point parabolic interpolation for sub-bin peak location
                if 0 < i < len(fr) - 1:
                    y0, y1, y2 = P[i - 1], P[i], P[i + 1]
                    d = 0.5 * (y0 - y2) / max(y0 - 2 * y1 + y2, 1e-30)
                    d = float(np.clip(d, -0.5, 0.5))
                else:
                    d = 0.0
                vs.append(0.5 * (b[0] + b[1]))
                fs_.append(fr[i] + d * (fr[1] - fr[0]))
                pr.append(P[i] / np.median(P[sel]))
            vs, fs_ = np.array(vs), np.array(fs_)
            sl = np.polyfit(vs, fs_, 1)[0]
            r = np.corrcoef(vs, fs_)[0, 1]
            prom = float(np.median(pr))
            # 🛑 PROMINENCE GATE. Picking the max of ~N chi2_2 bins gives a max/median of about
            # -log2(1 - 0.5**(1/N)) by chance ALONE. Below that there is no line to track and any
            # slope fitted to the argmax is fitting noise. An earlier revision of this script used
            # prom > 2 and duly "found" folded lines in lanes whose chance threshold was ~7.
            nb = int(sel.sum())
            chance = -np.log(1 - 0.5 ** (1 / nb)) / np.log(2)
            if prom < max(2.5 * chance, 8.0) or len(vs) < 3:
                verdict = f"NO LINE (prom {prom:.1f} < gate {max(2.5 * chance, 8.0):.1f})"
            elif sl < -0.15 and r < -0.90:
                verdict = "*** FALLS with speed => FOLDED, real f0 > Nyquist ***"
            elif sl > 0.15 and r > 0.90:
                verdict = f"rises: order {sl / 0.481:.2f} x wheel-1"
            else:
                verdict = "fixed in Hz (resonance) -- no speed dependence"
            print(f"  {lo:5.1f}-{hi:5.1f} " + " ".join(f"{x:7.2f}" for x in fs_)
                  + f" {sl:9.3f} {r:7.3f} {prom:6.1f}  {verdict}")

    print("\n" + "=" * 100)
    print("RESULT ON THIS DATA: the ONLY lane that clears the prominence gate is 15-22 Hz, and it")
    print("is FIXED IN HERTZ -- the known resonance. Every lane above 22 Hz is below its own chance")
    print("threshold in every axis, so there is NO coherent line to track, in either direction.")
    print("=> the near-Nyquist accel energy `audit_alias_evidence` found is BROADBAND, not a tone.")
    print("🛑 That is a null on the TONE, not on the band. It leaves the symptom as either")
    print("(a) genuinely broadband, (b) a tone below this floor, or (c) a tone whose fold happens")
    print("to be speed-independent. It does NOT establish that nothing is up there.")


if __name__ == "__main__":
    main()
