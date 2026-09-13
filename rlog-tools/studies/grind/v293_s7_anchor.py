# -*- coding: utf-8 -*-
"""v293_s7_anchor.py -- THE EMPIRICAL ANCHOR: the operator's own DISENGAGED data is torque mode's
own 20 Hz condition, measured on the car, on the same routes.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

WHY THIS IS THE STRONGEST EVIDENCE IN THE WHOLE DESIGN.
With `STEER_REQUEST` = 0 the LKAS rate loop's output is gated to zero -- the servo contributes no
return ratio at all.  That is EXACTLY what 0xC62E6 = 0 does, for the 18-22 Hz question.  So the
engaged-to-disengaged band ratio on a V282 route is a DIRECT MEASUREMENT of what fraction of the ring
is the loop's own regeneration, and its reciprocal is the measured prediction for torque mode.

THREE DECLARED DIFFERENCES between disengaged and torque mode, all reported:
  1. disengaged also drops the r24 arm from 5244 to Honda's 2048/LERP (byte 0x3AA96 gates it to
     STEER_CONTROL_ACTIVE).  Torque mode keeps whatever 0xC6446 says.
  2. disengaged carries no LKAS excitation at all; torque mode still drives the plant with f(cmd).
  3. disengaged frames are mostly STATIONARY (flightread section 4.1 measured p50 0.0 m/s), so this
     is the car's noise floor with the loop open, not road input at speed.  A SPEED-MATCHED read is
     computed here as the control on (3).

THIS FILE RE-DERIVES THE NUMBER ITSELF rather than relaying `V292-FLIGHT-READ`'s table -- the crux of
a decision-bearing finding has to be verified first-hand.  The two must agree or the disagreement is
the finding.

Run: python v293_s7_anchor.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                       # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
OUT = []
BANDS = [(5.0, 9.0), (9.0, 13.0), (13.0, 17.0), (18.0, 22.0), (22.0, 30.0)]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band_rms(x, lo, hi, fs=FS):
    if len(x) < 200:
        return np.nan
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    y = signal.sosfiltfilt(sos, np.asarray(x, float))
    return float(np.sqrt(2.0) * np.sqrt(np.mean(y ** 2)))


def masked_band(x, m, lo, hi, minlen=256):
    """band rms over the CONTIGUOUS RUNS of a mask, pooled by run length (filtering across a gap
    would smear the two states into each other)."""
    acc, wts = [], []
    for a, b in C20.runs(m, minlen):
        v = band_rms(x[a:b], lo, hi)
        if np.isfinite(v):
            acc.append(v)
            wts.append(b - a)
    if not acc:
        return np.nan, 0
    acc, wts = np.array(acc), np.array(wts, float)
    return float(np.sqrt(np.sum(wts * np.array(acc) ** 2) / np.sum(wts))), int(wts.sum())


def main():
    pr("=" * 118)
    pr("THE EMPIRICAL ANCHOR -- engaged vs DISENGAGED on the operator's own V282 routes")
    pr("agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 118)
    pr("Channel: 0x18F wheel RATE, raw counts (CPD = 8 counts per deg/s).  Engaged = lateral engaged")
    pr("(the kit's own `eng`: 0xE4 STEER_REQUEST & 0x18F SCA).  Band rms x sqrt(2) over contiguous runs")
    pr("of >= 2.56 s, pooled by run length.")
    pr("")
    rows = {}
    for tag in ("r39", "r6c", "r35"):
        g = S2.route(tag, (18.0, 22.0))
        eng = g["eng"]
        dis = ~eng
        pr("-" * 118)
        pr("%s : %.0f s total, engaged %.0f s, disengaged %.0f s ; engaged v p50 %.1f m/s, disengaged v p50 %.1f"
           % (tag, g["t"][-1] - g["t"][0], eng.sum() / FS, dis.sum() / FS,
              np.median(g["vego"][eng]) if eng.any() else np.nan,
              np.median(g["vego"][dis]) if dis.any() else np.nan))
        pr("  %-12s %10s %10s %10s %14s" % ("band Hz", "engaged", "disengaged", "eng/dis", "1/(eng/dis)"))
        r = {}
        for lo, hi in BANDS:
            e, ne = masked_band(g["wire"], eng, lo, hi)
            d, nd = masked_band(g["wire"], dis, lo, hi)
            ratio = e / d if (np.isfinite(e) and np.isfinite(d) and d > 0) else np.nan
            r[(lo, hi)] = ratio
            pr("  %-12s %10.2f %10.2f %10.3f %14.3f" % ("%.0f-%.0f" % (lo, hi), e, d, ratio, 1.0 / ratio))
        rows[tag] = r
        # speed-matched control
        pr("")
        pr("  SPEED-MATCHED control (the flightread caveat: the disengaged reference is mostly at rest)")
        pr("  %-12s %10s %10s %10s %10s" % ("band Hz", "0-3 m/s", "3-8 m/s", "8-15 m/s", ">15 m/s"))
        for lo, hi in BANDS:
            cols = []
            for vlo, vhi in ((0.0, 3.0), (3.0, 8.0), (8.0, 15.0), (15.0, 99.0)):
                vm = (g["vego"] >= vlo) & (g["vego"] < vhi)
                e, ne = masked_band(g["wire"], eng & vm, lo, hi)
                d, nd = masked_band(g["wire"], dis & vm, lo, hi)
                cols.append(e / d if (np.isfinite(e) and np.isfinite(d) and d > 0 and ne > 512 and nd > 512)
                            else np.nan)
            pr("  %-12s %10s %10s %10s %10s" % ("%.0f-%.0f" % (lo, hi),
                                                *["%10.3f" % c if np.isfinite(c) else "         -" for c in cols]))
    pr("")
    pr("=" * 118)
    pr("THE ANCHOR, and how it compares with the byte-exact replay")
    pr("=" * 118)
    pr("  %-8s %14s %16s %16s" % ("route", "eng/dis 18-22", "=> torque mode", "replay predicted"))
    pred = {"r39": 0.284, "r6c": 0.403, "r35": None}
    for tag in ("r39", "r6c", "r35"):
        rr = rows[tag][(18.0, 22.0)]
        p = pred.get(tag)
        pr("  %-8s %14.3f %16.3f %16s" % (tag, rr, 1.0 / rr, ("%.3f" % p) if p else "not run"))
    pr("")
    pr("  The middle column is what the CAR says a fully open LKAS lane does to its own 18-22 Hz wheel")
    pr("  motion.  The right column is the byte-exact closed-loop replay's independent prediction.")
    pr("  These are two completely different methods: one is a ratio of measured band amplitudes on the")
    pr("  same route, the other is a marched integer simulation through a fitted plant.")
    pr("")
    pr("  🛑 THE THREE DIFFERENCES AGAIN, so the anchor is not over-read:")
    pr("  (1) disengaged also drops r24 to Honda's 2048 -- torque mode need not;")
    pr("  (2) disengaged has no LKAS excitation -- torque mode still drives f(cmd) into the plant;")
    pr("  (3) the disengaged reference is mostly stationary -- see the speed-matched control above.")

    open(os.path.join(SCR, "v293_s7_anchor.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s7_anchor.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
