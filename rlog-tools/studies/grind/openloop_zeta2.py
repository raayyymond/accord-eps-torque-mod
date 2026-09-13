# -*- coding: utf-8 -*-
"""openloop_zeta2.py -- controls for E3b (background-aware line fit) INCLUDING the two artefacts that
the first cut of E3 walked into.  Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY.

Artefact 1  DEGENERATE EDGE FIT.  A bare Lorentzian + constant, fitted to a spectrum with no line,
            parks f0 on the window edge and uses the Lorentzian tail as the 1/f skirt.  E3b models
            the background as a power law and confines f0 to the interior, and reports `bump` =
            max(model/background) over the window.  bump ~ 1 means NO LINE and zeta UNIDENTIFIED.
Artefact 2  INHOMOGENEOUS BROADENING.  Pooling the PSD over segments whose f0 differs (the record:
            f0 falls 0.11-0.21 Hz per m/s of vehicle speed, and moves with demand) broadens the
            pooled line and inflates zeta.  Controlled here by synthesising segments whose f0 wanders
            by a known amount and measuring the inflation.
Run: python openloop_zeta2.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openloop_lib as L                       # noqa: E402
import openloop_zeta as Z                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    F0 = 20.0
    ZS = (0.005, 0.010, 0.020, 0.030, 0.050, 0.100, 0.200, 0.300, 0.500)
    pr("=" * 124)
    pr("CONTROLS FOR E3b -- BACKGROUND-AWARE LINE FIT  (fit window 16-26 Hz, nperseg 1024, 600 s in 20 s pieces)")
    pr("=" * 124)
    pr("  %-10s %-8s | %7s %8s %8s %7s %8s %9s %8s" %
       ("true z", "SNR dB", "z_hat", "bias", "f0_hat", "bump", "R2", "dAIC", "prom"))
    for snr in (10.0, 0.0, -6.0):
        for zt in ZS:
            x = Z.synth(zt, F0, 60000, snr, seed=int(zt * 1e5) + int(snr))
            r = Z.zeta_line(Z.chop(x, 20.0), 16.0, 26.0, 1024)
            pr("  %-10.4f %-8.1f | %7.4f %8.2f %8.3f %7.2f %8.3f %9.1f %8.2f"
               % (zt, snr, r["z"], r["z"] / zt, r["f0"], r["bump"], r["r2"], r["dAIC"], r["prom_data"]))
        rng = np.random.default_rng(4242 + int(snr))
        nz = signal.sosfiltfilt(signal.butter(4, (4.0, 45.0), btype="band", fs=FS, output="sos"),
                                rng.standard_normal(60000))
        r = Z.zeta_line(Z.chop(nz, 20.0), 16.0, 26.0, 1024)
        pr("  %-10s %-8.1f | %7.4f %8s %8.3f %7.2f %8.3f %9.1f %8.2f   <-- NEGATIVE CONTROL (no mode)"
           % ("NO MODE", snr, r["z"], "-", r["f0"], r["bump"], r["r2"], r["dAIC"], r["prom_data"]))
        pr()
    pr("-" * 124)
    pr("ARTEFACT 2 -- INHOMOGENEOUS BROADENING: 20 s segments whose f0 is drawn from f0 +- spread")
    pr("             (uniform), true zeta 0.020, SNR 10 dB.  This is what pooling a spectrum across")
    pr("             speeds and demands does to the fitted zeta.")
    pr("  %-14s | %7s %8s %8s %7s" % ("f0 spread Hz", "z_hat", "bias", "f0_hat", "bump"))
    for spread in (0.0, 0.25, 0.5, 1.0, 2.0, 3.0):
        rng = np.random.default_rng(5)
        segs_ = []
        for i in range(30):
            f0i = F0 + rng.uniform(-spread, spread)
            segs_.append(Z.synth(0.020, f0i, 2000, 10.0, seed=100 + i))
        r = Z.zeta_line(segs_, 16.0, 26.0, 1024)
        pr("  %-14.2f | %7.4f %8.2f %8.3f %7.2f" % (spread, r["z"], r["z"] / 0.020, r["f0"], r["bump"]))
    pr()
    pr("-" * 124)
    pr("SHORT-RECORD control: the same at nperseg 512 and 256, true zeta 0.02 / 0.10, no f0 spread")
    pr("  %-10s %-8s | %7s %8s %8s %7s" % ("true z", "nperseg", "z_hat", "bias", "f0_hat", "bump"))
    for zt in (0.02, 0.10):
        for nper in (1024, 512, 256):
            x = Z.synth(zt, F0, 60000, 10.0, seed=int(zt * 1e5))
            r = Z.zeta_line(Z.chop(x, 20.0), 16.0, 26.0, nper)
            pr("  %-10.4f %-8d | %7.4f %8.2f %8.3f %7.2f" % (zt, nper, r["z"], r["z"] / zt, r["f0"], r["bump"]))
    pr()
    pr("READ: the `bump` column is the falsifier.  On the NO-MODE rows it collapses to ~1 and dAIC")
    pr("goes positive (the resonance term does not pay for its 3 parameters).  A zeta from a row whose")
    pr("bump is ~1 is NOT a measurement of damping -- it is the fit shrugging.")


if __name__ == "__main__":
    main()
    with open(os.path.join(L.SCR, "openloop_zeta2_controls.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
