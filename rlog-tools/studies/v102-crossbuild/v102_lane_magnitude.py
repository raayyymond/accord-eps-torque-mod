#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_lane_magnitude.py -- |L(f)| at 20-23 Hz: the MAGNITUDE half of `pole-hunt`'s cross-spectrum.

`studies/v102-crossbuild/v102_lane_phase2.py` gave arg(L).  This gives |L| = |Sxy| / Pxx -- the least-squares transfer gain
from the TORQUE SENSOR to the lane, in (lane counts) per (torque count), with the wire scale
applied so the number is physical rather than a wire code.

🛑 THE REASON THIS FILE EXISTS RATHER THAN A ONE-LINE ANSWER.
   The kit already has a standing warning that AMPLITUDE claims from these quantised 427 lanes do
   NOT travel (`accord-probe-underranges-to-one-bit-comparator`: *"a usable SPECTRAL probe, but
   amplitude claims do NOT travel -- '120.5 counts' is a bin-RMS, not an amplitude"*).  A phase is
   robust to under-ranging; a MAGNITUDE is exactly what under-ranging destroys.  So the decisive
   question is not "what is |L|" but **"is the lane's 20-23 Hz content above its own quantisation
   floor at all?"**  This file answers that FIRST and only reports |L| where it passes.

   QUANTISATION FLOOR, computed not assumed:  the wire is an integer code, so one LSB = WIRE_SCALE
   counts.  Uniform quantisation noise has power LSB^2/12 spread across the SAMPLED bandwidth
   0..fs/2 = 0..24.9 Hz, so the power landing in a 3 Hz band is (LSB^2/12) * (3/24.9), i.e. an RMS
   of LSB * sqrt(3/(12*24.9)) = LSB * 0.1002.  Measured band-RMS is compared against that.

WIRE SCALES (counts per LSB = 2^shift / 5, from `extract_r7d.WIRE_SCALE`):
   r7d sar 1 -> 0.4    r77/r78 sar 3 -> 1.6    r79 sar 4 -> 3.2    r96 sar 6 -> 12.8

UNITS NOTE for the requester: `tq` here is the cached channel, which is -1x the 0x18F wire value;
the firmware packer gives wire = -(gp-0x4f60 * 125/128), so tq = +0.977 * gp-0x4f60.  To refer |L|
to `gp-0x4f60` instead of `tq`, MULTIPLY the numbers below by 0.977.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_lane_phase2 as P2  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF, FS = P2.NF, P2.FS
WIN, F, BAND = P2.WIN, P2.F, P2.BAND
NYQ_427 = 49.8 / 2.0
BW = float(F[BAND].max() - F[BAND].min()) + float(F[1] - F[0])

SCALE = {"7d": 0.4, "77": 1.6, "78": 1.6, "79": 3.2, "96": 12.8}
ROUTES = {"77": ("V90  4x", "gp-0x6b26 INERTIA"), "78": ("V91  4x", "gp-0x6b26 INERTIA"),
          "79": ("V91  4x", "gp-0x6bbe VISCOUS"), "96": ("V102 6x", "gp-0x6b4c ASSIST SUM")}


def mag(route, vhi=65.0):
    """|Sxy|/Pxx over 20-23 Hz, plus the lane's own band-RMS and its quantisation floor."""
    sc = SCALE[route]
    Sxy, Pxx, Pyy, ep = [], [], [], []
    for e, b in enumerate(P2.build(route)):
        vv = b["v"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= 5.0) & (vv < vhi)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                Y = np.fft.rfft(P2.taper(b["lane"][i:i + NF] * sc))   # lane, in COUNTS
                X = np.fft.rfft(P2.taper(b["tq"][i:i + NF]))          # torque, in counts
                Sxy.append(Y * np.conj(X))
                Pxx.append(np.abs(X) ** 2)
                Pyy.append(np.abs(Y) ** 2)
                ep.append(e)
            i += NF // 2
    if len(Sxy) < 6:
        return None
    Sxy, Pxx, Pyy, ep = map(np.array, (Sxy, Pxx, Pyy, ep))
    norm = 2.0 / (NF ** 2) / np.mean(WIN ** 2)

    def est(sel):
        s, px, py = Sxy[sel].sum(0), Pxx[sel].sum(0), Pyy[sel].sum(0)
        g = float(np.abs(s[BAND].sum()) / max(px[BAND].sum(), 1e-30))
        coh = float(np.mean((np.abs(s) ** 2) / np.maximum(px * py, 1e-30)))
        lane_rms = float(np.sqrt((py[BAND].sum() / len(sel)) * norm))
        tq_rms = float(np.sqrt((px[BAND].sum() / len(sel)) * norm))
        return g, coh, lane_rms, tq_rms
    g, coh, lrms, trms = est(np.arange(len(Sxy)))
    rng = np.random.default_rng(11)
    keys = np.unique(ep)
    bs = [est(np.concatenate([np.nonzero(ep == keys[j])[0]
                              for j in rng.integers(0, len(keys), len(keys))]))[0]
          for _ in range(1500)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    qfloor = sc * np.sqrt(BW / (12.0 * NYQ_427))
    return dict(g=g, lo=float(lo), hi=float(hi), coh=coh, lane_rms=lrms, tq_rms=trms,
                qfloor=float(qfloor), snr=lrms / qfloor, nwin=len(Sxy), nep=len(keys))


if __name__ == "__main__":
    print("=" * 104)
    print("|L| at 20-23 Hz = |Sxy|/Pxx, lane COUNTS per torque count.  Engaged, 5-65 km/h.")
    print("band %.2f-%.2f Hz (BW %.2f Hz) | 427 Nyquist %.1f Hz | quant floor = LSB*%.4f counts"
          % (F[BAND].min(), F[BAND].max(), BW, NYQ_427, np.sqrt(BW / (12.0 * NYQ_427))))
    print("=" * 104)
    print("  %-5s %-9s %-22s %9s %-20s %9s %9s %7s %6s"
          % ("route", "build", "lane", "|L|", "95% CI", "lane RMS", "q-floor", "SNR", "coh2"))
    res = {}
    for rt, (lab, cell) in ROUTES.items():
        try:
            r = mag(rt)
        except Exception as exc:
            print("  r%-4s FAILED: %s" % (rt, exc))
            continue
        if r is None:
            print("  r%-4s %-9s %-22s  too thin" % (rt, lab, cell))
            continue
        res[rt] = r
        print("  r%-4s %-9s %-22s %9.4f [%7.4f,%7.4f] %9.2f %9.2f %7.2f %6.3f"
              % (rt, lab, cell, r["g"], r["lo"], r["hi"], r["lane_rms"], r["qfloor"],
                 r["snr"], r["coh"]))

    print("\n" + "=" * 104)
    print("🛑 DOES THE MAGNITUDE TRAVEL?  SNR = lane band-RMS / quantisation floor.")
    print("=" * 104)
    for rt, r in res.items():
        lab, cell = ROUTES[rt]
        if r["snr"] < 2.0:
            v = ("🛑 NO -- the lane's 20-23 Hz content is at or below its OWN QUANTISATION "
                 "FLOOR.\n            |L| is an artefact of the LSB, not a measurement. "
                 "DO NOT USE.")
        elif r["snr"] < 5.0:
            v = ("⚠ MARGINAL -- only %.1fx the quantisation floor.  Treat |L| as an ORDER OF\n"
                 "            MAGNITUDE; the quantisation noise biases |Sxy|/Pxx downward." % r["snr"])
        else:
            v = "✅ YES -- %.0fx the quantisation floor, the magnitude is real." % r["snr"]
        print("  r%-4s %-9s %-22s SNR %6.2f   %s" % (rt, lab, cell, r["snr"], v))
    print("""
  ⚠ THREE BIASES THAT ALL PUSH |L| THE SAME WAY (DOWN), and none is corrected here:
     1. QUANTISATION adds uncorrelated noise to the lane.  |Sxy|/Pxx is asymptotically unbiased
        for noise on the OUTPUT, so this one is mostly benign -- but it inflates Pyy and so
        DEFLATES the reported coherence.
     2. ZOH from 49.8 Hz applies a sinc envelope: |sinc(pi*f/49.8)| = %.3f at 21.5 Hz, so the
        true |L| is about %.0f %% HIGHER than the number printed above.
     3. ALIASING folds 26.8-29.8 Hz content into the band, adding power that is NOT L.
  ⇒ The printed |L| is a LOWER BOUND on the true gain, by roughly the factor in (2)."""
          % (np.sinc(21.5 / 49.8), 100.0 * (1.0 / np.sinc(21.5 / 49.8) - 1.0)))
