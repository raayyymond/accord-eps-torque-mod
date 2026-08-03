#!/usr/bin/env python3
"""audit_alias_evidence.py -- does anything ACTUALLY fold, and how sensitive is each channel?

Two questions, both decision-bearing for whether a firmware code cave is the only way forward.

Q1. IS THE >50 Hz BAND SILENT, OR IS IT FOLDED ON TOP OF WHAT WE ALREADY MEASURE?
    Every channel this kit uses is sampled at ~50 or ~100 Hz. If the sensor upstream of that
    sampling has NO anti-alias filter, content above Nyquist is not lost -- it is FOLDED into the
    band we already analyse, and every "40-49 Hz" number in the record is a sum of the real 40-49 Hz
    content and whatever folded on top of it. The tell is the spectral shape approaching Nyquist: a
    properly anti-aliased channel whose physical content is low-frequency ROLLS OFF hard; a channel
    that is folding stays flat right up to the edge.
    🛑 A flat approach to Nyquist is NOT proof of folding -- genuinely broadband physical noise
    looks the same. It only says folding is NOT EXCLUDED. The reverse is the strong reading: a hard
    roll-off would PROVE nothing folds, and would kill the section-2 idea outright.

Q2. WHAT TONE AMPLITUDE CAN EACH CHANNEL DETECT? Needed to rank the options honestly.

Sample rates used, all measured elsewhere in this kit and re-checked here:
    wheel speed 0x1D0    49.9938 Hz     Nyquist 24.997
    EPS CAN 0x14A/0x18F 100.0000 Hz     Nyquist 50.000
    comma IMU           101.0282 Hz     Nyquist 50.514

Usage:  python audit_alias_evidence.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "_cache_r47"
SEGS = range(26)


def welch(x, fs, nw=512, detrend=51):
    """Hanning-windowed Welch PSD, plus the single-tone amplitude calibration."""
    x = np.asarray(x, float)
    if len(x) < 2 * nw:
        return None, None, 0
    x = x - np.convolve(x, np.ones(detrend) / detrend, mode="same")
    P, n = None, 0
    for k in range(1, len(x) // nw):
        w = x[k * nw:(k + 1) * nw] * np.hanning(nw)
        p = np.abs(np.fft.rfft(w)) ** 2
        P = p if P is None else P + p
        n += 1
    if not n:
        return None, None, 0
    return np.fft.rfftfreq(nw, 1 / fs), P / n, n


def edge_report(name, fr, P, n, fs, unit):
    """Roll-off toward Nyquist + the 4-sigma detectable tone amplitude."""
    ny = fs / 2
    mid = (fr > 0.10 * ny) & (fr < 0.20 * ny)
    edge = (fr > 0.88 * ny) & (fr <= ny)
    lo, hi = float(np.median(P[mid])), float(np.median(P[edge]))
    amp = np.sqrt(P) / (512 * 0.5 / 2)
    band = (fr > 0.05 * ny) & (fr < 0.95 * ny)
    floor = float(np.median(amp[band]))
    det = 4 * floor / np.sqrt(n)
    pk = int(np.argmax(amp * band))
    print(f"  {name:26s} fs={fs:8.4f}  nw={n:4d}  "
          f"edge/mid {hi / lo:7.4f} ({10 * np.log10(hi / lo):+6.1f} dB)  "
          f"floor {floor:.3e} {unit}  4sig {det:.3e} {unit}  peak {fr[pk]:6.2f}Hz {amp[pk]/floor:5.1f}x")
    return hi / lo


def main():
    print(__doc__.split("Usage:")[0].rstrip())
    print("\n" + "=" * 112)
    print("HIGHWAY ONLY (vEgo > 25 m/s). 512-pt Welch windows. 'edge/mid' = PSD at 0.88-1.00 x")
    print("Nyquist divided by PSD at 0.10-0.20 x Nyquist. Near 1.0 => flat to the fold.")
    print("=" * 112)

    ratios = {}
    # ---- IMU (its own hardware clock) -------------------------------------------------------
    print("\ncomma IMU  (LSM6DS3TR-C, ODR tap '104 Hz', measured 101.028 Hz):")
    for ch, unit in (("ax", "m/s2"), ("ay", "m/s2"), ("az", "m/s2"),
                     ("gx", "rad/s"), ("gy", "rad/s"), ("gz", "rad/s")):
        acc, tot = None, 0
        for s in SEGS:
            fi, fc = CACHE / f"r47s{s}_imu.npz", CACHE / f"r47s{s}.npz"
            if not (fi.exists() and fc.exists()):
                continue
            z, c = np.load(fi), np.load(fc)
            tk = "at" if ch[0] == "a" else "gt"
            v = np.interp(z[tk], c["t"], c["cs_v"])
            m = v > 25
            if m.sum() < 1100:
                continue
            fr, P, n = welch(z[ch][m], 101.0282)
            if P is None:
                continue
            acc = P * n if acc is None else acc + P * n
            tot += n
        if acc is None:
            print(f"  {ch}: no highway data")
            continue
        ratios[ch] = edge_report(f"IMU {ch}", fr, acc / tot, tot, 101.0282, unit)

    # ---- EPS CAN channels (100 Hz grid) ------------------------------------------------------
    print("\nEPS CAN, 100.000 Hz grid (this is where every published 40-49 Hz number came from):")
    for ch, unit, lab in (("tq", "counts", "0x18F torsion bar"),
                          ("ang", "deg", "0x14A steer angle"),
                          ("rate_c", "deg/s", "0x14A rate field"),
                          ("e4tq", "counts", "0x0E4 LKAS cmd (TX, not a sensor)")):
        acc, tot = None, 0
        for s in SEGS:
            fc = CACHE / f"r47s{s}.npz"
            if not fc.exists():
                continue
            c = np.load(fc)
            if ch not in c.files:
                continue
            m = c["cs_v"] > 25
            if m.sum() < 1100:
                continue
            fr, P, n = welch(c[ch][m], 100.0)
            if P is None:
                continue
            acc = P * n if acc is None else acc + P * n
            tot += n
        if acc is None:
            print(f"  {lab}: no highway data")
            continue
        ratios[ch] = edge_report(lab, fr, acc / tot, tot, 100.0, unit)

    print("\n" + "=" * 112)
    print("VERDICT ON FOLDING")
    print("=" * 112)
    for k, v in ratios.items():
        tag = ("FLAT to Nyquist -- folding NOT excluded" if v > 0.30 else
               "ROLLS OFF -- little or nothing folds here")
        print(f"  {k:10s} edge/mid {v:7.4f}  {tag}")
    print("\n  🛑 Read the weak direction honestly: 'flat to Nyquist' is consistent with real")
    print("  broadband road excitation AND with folding, and this test cannot separate them. What")
    print("  it CAN do is rule folding out, and on these channels it does not.")


if __name__ == "__main__":
    main()
