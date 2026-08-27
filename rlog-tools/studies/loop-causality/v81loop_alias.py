#!/usr/bin/env python3
"""S0.6 -- the DERIVATIVE IDENTITY, used for two things the kit has not had.

The EPS transmits a steering ANGLE and a steering ANGLE RATE.  The rate is the derivative of the
angle, and that is computed INSIDE the EPS at its own ~1 kHz rate, BEFORE the 100 Hz CAN sampling
that aliases everything.  Two consequences, both exploited here:

  1. ALIAS RESOLUTION.  Sampling maps a true line at F to an observed bin f0 = |F mod 100| and
     aliases angle and rate IDENTICALLY.  So the observed MAGNITUDE RATIO is preserved:

         |Rate(f0)| / |Ang(f0)|  =  2 pi F      (F the TRUE frequency, not the observed bin)

     Reading that ratio therefore says whether the 27.5 Hz bin is a real 27.5 Hz line or the
     alias of a 72.5 Hz one.  🛑 The record says this ambiguity is "inherited from every prior
     analysis here" -- this is a direct measurement of it, not an assumption.

  2. TIMEBASE VALIDATION.  The rate must LEAD the angle by exactly +90 deg. Any departure is
     residual timebase error, so the departure measured as a FUNCTION OF FREQUENCY is a direct
     readout of the inter-message delay -- including whether 0x18F's payload is captured on a
     different instant from 0x14A's, which would bias every bar phase by the same amount.

`rate_c` is in the SAME MESSAGE as the angle (0x14A), so for it the capture instants are identical
by construction and any residual is EPS-internal.  `rate_f` is on 0x18F, the message the torsion
bar also rides -- so whatever offset shows up for rate_f applies to the BAR as well.  That is the
number needed to interpret cmd->bar.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import (CACHE, FS_NOM, coherence, lattice, load_route,  # noqa: E402
                         locate, native_18f, resamp, welch_cross, wrap)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF, HOP = 256, 64
RATE_FIX = 1.25


def dedup(t, *vs):
    t = np.asarray(t, float)
    keep = np.ones(len(t), bool)
    keep[1:] = np.diff(t) > 0
    return (t[keep],) + tuple(np.asarray(v, float)[keep] for v in vs)


def main():
    R = load_route()
    sb = {int(r[0]): (r[1], r[2]) for r in np.asarray(R["seg_bounds"], float)}
    t0, t1 = sb[8][0] + 38.0, sb[8][0] + 52.0
    tau = lattice(t0, t1, FS_NOM)
    a14 = dedup(np.asarray(R["t"], float), R["ang"], R["rate_c"])
    t18, v18, _ = native_18f(R, ("tq", "rate_f"))
    a18 = dedup(t18, v18["tq"], v18["rate_f"])
    ang = resamp(tau, a14[0], a14[1])
    rc = resamp(tau, a14[0], a14[2])
    bar = resamp(tau, a18[0], a18[1])
    rf = resamp(tau, a18[0], a18[2]) * RATE_FIX

    print("=" * 100)
    print("S0.6a  UNIT CHECK at LOW frequency, where a central difference is accurate")
    print("=" * 100)
    for fc in (1.0, 2.0, 3.0):
        def lp(x):
            X = np.fft.rfft(x - x.mean())
            f = np.fft.rfftfreq(len(x), 1 / FS_NOM)
            X[f > fc] = 0
            return np.fft.irfft(X, n=len(x))
        da = np.gradient(lp(ang), tau)
        for nm, r in (("rate_c", lp(rc)), ("rate_f*1.25", lp(rf))):
            print(f"  <{fc:.0f} Hz  d(ang)/dt = {np.dot(da, r) / np.dot(r, r):+.4f} x {nm:12s}"
                  f"   corr {np.corrcoef(da, r)[0, 1]:+.4f}")

    print()
    print("=" * 100)
    print("S0.6b  DERIVATIVE PHASE vs FREQUENCY -- must be +90 deg everywhere")
    print("=" * 100)
    f, Pxx, Pyy, Pxy, n = welch_cross(ang, rc, FS_NOM, NF, HOP)
    f2, Pxx2, Pyy2, Pxy2, _ = welch_cross(ang, rf, FS_NOM, NF, HOP)
    Cc, Cf = coherence(Pxx, Pyy, Pxy), coherence(Pxx2, Pyy2, Pxy2)
    print(f"  {'f (Hz)':>8} | {'rate_c (0x14A, same msg as angle)':>34} | "
          f"{'rate_f (0x18F, same msg as the BAR)':>36}")
    print(f"  {'':>8} | {'lead':>8} {'err':>8} {'=ms':>7} {'coh':>6} | "
          f"{'lead':>8} {'err':>8} {'=ms':>7} {'coh':>6}")
    for ftar in (1.5, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0, 24.0, 27.5, 30.0, 35.0, 40.0, 45.0):
        j = int(np.argmin(np.abs(f - ftar)))
        out = [f"  {f[j]:>8.2f} |"]
        for P, C in ((Pxy, Cc), (Pxy2, Cf)):
            ld = np.degrees(np.angle(P[j]))
            er = np.degrees(wrap(np.angle(P[j]) - np.pi / 2))
            out.append(f" {ld:>+8.1f} {er:>+8.1f} {er / 360 / f[j] * 1e3:>+7.2f} {C[j]:>6.3f} |")
        print("".join(out))
    print("  err in ms is (observed lead - 90 deg) expressed as a time. A CONSTANT ms across")
    print("  frequency is a pure timebase offset; a constant DEGREE error is a filter.")

    print()
    print("=" * 100)
    print("S0.6c  ALIAS RESOLUTION:  |Rate| / |Ang|  =  2*pi*F_true")
    print("=" * 100)
    print(f"  {'obs bin':>8} {'|rate_c|/|ang|':>15} {'F_true':>9} | {'|rate_f|/|ang|':>15} "
          f"{'F_true':>9} | {'coh':>6}   [obs bin f0, alias twin 100-f0]")
    for ftar in (1.5, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0, 27.5, 35.0, 45.0):
        j = int(np.argmin(np.abs(f - ftar)))
        A = np.sqrt(Pxx[j])
        r1, r2 = np.sqrt(Pyy[j]) / A, np.sqrt(Pyy2[j]) / A
        print(f"  {f[j]:>8.2f} {r1:>15.2f} {r1 / (2 * np.pi):>9.2f} | {r2:>15.2f} "
              f"{r2 / (2 * np.pi):>9.2f} | {Cc[j]:>6.3f}")
    j = int(np.argmin(np.abs(f - 27.53)))
    r1 = np.sqrt(Pyy[j]) / np.sqrt(Pxx[j])
    r2 = np.sqrt(Pyy2[j]) / np.sqrt(Pxx[j])
    print(f"\n  AT THE LINE (bin {f[j]:.2f} Hz):")
    print(f"    rate_c: implied F_true = {r1 / (2 * np.pi):6.2f} Hz     "
          f"rate_f: implied F_true = {r2 / (2 * np.pi):6.2f} Hz")
    print(f"    candidate readings: {f[j]:.2f} Hz  or  {100 - f[j]:.2f} Hz  or  {100 + f[j]:.2f} Hz")
    print(f"    2*pi*f for each:    {2 * np.pi * f[j]:.1f} / {2 * np.pi * (100 - f[j]):.1f} "
          f"/ {2 * np.pi * (100 + f[j]):.1f} rad/s")
    print("  🛑 The angle is quantised to 0.1 deg. Quantisation noise INFLATES |Ang| at high")
    print("     frequency, which DEFLATES the implied F_true -- so the estimate is a LOWER BOUND.")
    lsb = 0.1 / np.sqrt(12)                      # uniform quantiser rms, deg
    nbins = NF // 2
    qfloor = lsb * np.sqrt(2.0 / nbins)          # per-bin rms contribution, rough
    print(f"     angle rms at the line = {np.sqrt(Pxx[j] / (np.sum(np.hanning(NF) ** 2))):.4f} "
          f"(arb) ; quantiser lsb rms {lsb:.4f} deg spread over {nbins} bins ~ {qfloor:.5f} deg/bin")

    print()
    print("=" * 100)
    print("S0.6d  IS THE BAR ON THE SAME CLOCK AS THE ANGLE?  bar vs rate_f, both on 0x18F")
    print("=" * 100)
    fb, Pb1, Pb2, Pb, _ = welch_cross(bar, rf, FS_NOM, NF, HOP)
    Cb = coherence(Pb1, Pb2, Pb)
    fa, Pa1, Pa2, Pa, _ = welch_cross(bar, ang, FS_NOM, NF, HOP)
    Ca = coherence(Pa1, Pa2, Pa)
    print(f"  {'f (Hz)':>8} {'bar->rate_f lead':>18} {'coh':>7}   {'bar->ang lead':>15} {'coh':>7}")
    for ftar in (1.5, 3.0, 8.0, 16.0, 24.0, 27.5, 35.0):
        j = int(np.argmin(np.abs(fb - ftar)))
        print(f"  {fb[j]:>8.2f} {np.degrees(np.angle(Pb[j])):>+18.1f} {Cb[j]:>7.3f}   "
              f"{np.degrees(np.angle(Pa[j])):>+15.1f} {Ca[j]:>7.3f}")
    print("  If bar->rate_f and bar->ang differ by a constant, that constant IS the 0x14A-vs-0x18F")
    print("  capture offset, and it is exactly what must be subtracted from every cmd->bar phase.")


if __name__ == "__main__":
    main()
