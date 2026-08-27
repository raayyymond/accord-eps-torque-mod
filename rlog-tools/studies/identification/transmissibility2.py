#!/usr/bin/env python3
"""PART 2 -- perceptual weighting, the 12.8 Hz direction question, and the bottom line.

🛑 CONTEXT FROM PART 1: the bar -> chassis transmissibility curve CANNOT be measured from this
data.  With n = 667 Welch segments (95% chance floor 0.0045) the bar explains 0.3%-2.7% of IMU
variance over 8-25 Hz.  The positive control on the SAME estimator (`tq` <-> `rate_c`) returns
0.26-0.96, so the estimator works and the null is a property of the coupling, not the pipeline.
⇒ every number below that needs a transmissibility is an ASSUMPTION, and is labelled as one.
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
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402

ROOT = V.ROOT
O = json.loads((ROOT / "_scratch/cache/r6f" / "transmissibility.json").read_text())
TARGETS = [21.1, 23.7, 28.0, 35.0, 40.0]


def wh_iso(f):
    """ISO 5349-1 W_h. Band-limiting (f1=6.310, f2=1258.9, 2-pole) x acceleration-velocity
    transition (f3=f4=15.915, Q4=0.64).  ⚠ Implemented from the standard's parameter set; the
    20-40 Hz behaviour is ~1/f and that is the only part this analysis leans on."""
    f = np.asarray(f, float)
    f1, f2, f3, f4, Q4 = 6.310, 1258.9, 15.915, 15.915, 0.64
    hb = 1.0 / np.sqrt((1 + (f1 / f) ** 4) * (1 + (f / f2) ** 4))
    ht = np.abs((1 + 1j * f / f4) / (1 + 1j * f / (Q4 * f3) - (f / f3) ** 2))
    return hb * ht


def wh_simple(f):
    """The plain-language version: flat to 16 Hz, 1/f above.  Sanity check on wh_iso."""
    f = np.asarray(f, float)
    return np.where(f <= 16.0, 1.0, 16.0 / f)


def main():
    V.hdr("W1  PERCEPTUAL WEIGHTING.  Two forms -- the ISO 5349-1 W_h parameter set and the\n"
          "    plain 'flat to 16 Hz then 1/f'.  If they agree over 20-40 Hz the conclusion does\n"
          "    not depend on which is used.")
    fs = np.array(TARGETS)
    wi, ws = wh_iso(fs), wh_simple(fs)
    wi_n, ws_n = wi / wh_iso(21.1), ws / wh_simple(21.1)
    print("    %8s %10s %10s | %12s %12s | %s"
          % ("f (Hz)", "W_h ISO", "W_h 1/f", "rel to 21.1", "rel to 21.1", "agree?"))
    for i, f in enumerate(TARGETS):
        print("    %8.1f %10.4f %10.4f | %12.3f %12.3f | %s"
              % (f, wi[i], ws[i], wi_n[i], ws_n[i],
                 "yes" if abs(wi_n[i] - ws_n[i]) < 0.06 else "NO"))
    O["wh"] = dict(f=TARGETS, iso=[float(x) for x in wi], simple=[float(x) for x in ws],
                   iso_rel=[float(x) for x in wi_n], simple_rel=[float(x) for x in ws_n])

    V.hdr("W2  WHAT MOVING THE MODE BUYS, under each transmissibility assumption.\n"
          "    🛑 Column A is the only one supported by measurement (a flat/unknown curve is\n"
          "    what a null coherence leaves you with).  Column B is TEXTBOOK, NOT MEASURED.")
    print("    A = perceptual weighting only, transmissibility assumed FLAT  [defensible]")
    print("    B = A x a 1/f^2 roll-off above the recorded 12.8 Hz plant mode  [ASSUMED]\n")
    print("    %-28s %14s %14s %14s"
          % ("move", "A: perceived", "B: perceived", "B/A"))
    O["gain"] = {}
    for f in TARGETS[1:]:
        a = wh_iso(f) / wh_iso(21.1)
        roll = (21.1 / f) ** 2
        b = a * roll
        print("    %-28s %13.3f %14.3f %14.2f"
              % ("21.1 -> %.1f Hz" % f, a, b, b / a))
        O["gain"]["21.1->%.1f" % f] = dict(A_perceptual_only=float(a), B_with_1overf2=float(b))
    print("\n    Read: under the only assumption the data support (A), moving 21.1 -> 35 Hz\n"
          "    buys %.0f%% in perceived terms -- NOT the ~2.8x that a 1/f^2 plant would give."
          % (100 * (1 - wh_iso(35.0) / wh_iso(21.1))))

    V.hdr("W3  THE LANDING ZONE, from the bar-side spectrum (honest to ~45 Hz, no IMU needed).")
    rows = np.array(O["p3"]["rows"], float)
    f, S = rows[:, 0], rows[:, 1:]
    worst = S.max(axis=1)
    print("    %-16s %10s   %s" % ("window", "worst-route", "verdict"))
    for lo, hi, lab in ((20.0, 23.0, "the mode's origin"), (23.0, 25.0, "where V86 put it"),
                        (26.0, 31.0, "the sustained ring"), (31.0, 36.0, "above the ring"),
                        (36.0, 41.0, "the quietest region"), (41.0, 45.0, "top of honest range")):
        m = (f >= lo) & (f < hi)
        w = float(np.nanmean(worst[m])) if m.any() else np.nan
        verdict = "OCCUPIED" if w > 2.5 else ("marginal" if w > 1.6 else "QUIET")
        print("    %-16s %10.2f   %-9s %s" % ("%.0f-%.0f Hz" % (lo, hi), w, verdict, lab))
        O.setdefault("zones", {})["%.0f-%.0f" % (lo, hi)] = dict(prom=w, verdict=verdict,
                                                                 label=lab)
    print("\n    quietest 2 Hz window in 24-45 Hz: %.1f-%.1f Hz (worst-route prominence %.2f)"
          % (O["p3_landing"]["lo"], O["p3_landing"]["hi"], O["p3_landing"]["prom"]))

    V.hdr("W4  THE RATCHET'S DIRECTION.  🛑 This needs the transmissibility curve, which is NOT\n"
          "    measurable here.  What follows is REASONING FROM THE RECORD + textbook 2nd-order\n"
          "    mechanics, explicitly NOT a measurement.")
    print("    Recorded plant mode: 12.8 Hz [12.1, 13.6] (wheel on torsion bar).")
    print("    For a 2nd-order mode at f_n, transmissibility is ~1 below f_n, PEAKS at f_n, and")
    print("    falls ~1/f^2 above it.  The ~8 Hz ratchet sits BELOW that peak:\n")
    print("    %10s %16s %s" % ("move", "toward/away", "consequence [BELIEF]"))
    for f0, f1v, lab in ((8.0, 12.8, "8 -> 12.8"), (8.0, 10.0, "8 -> 10"),
                         (8.0, 6.0, "8 -> 6"), (8.0, 5.0, "8 -> 5")):
        toward = abs(f1v - 12.8) < abs(f0 - 12.8)
        print("    %10s %16s %s" % (lab, "TOWARD the peak" if toward else "AWAY from the peak",
                                    "amplification RISES" if toward else "amplification FALLS"))
    print("\n    ⇒ for the ratchet, UP is the wrong direction and DOWN is the right one --")
    print("      the OPPOSITE of the 21 Hz mode, which is already above 12.8 Hz.")
    print("    ⚠ Unverified: the 12.8 Hz mode's own amplification factor is unmeasured here, so")
    print("      'how much worse' cannot be quantified.  Only the SIGN is argued.")
    O["w4"] = dict(plant_mode_Hz=12.8, plant_ci=[12.1, 13.6],
                   ratchet_direction="down", hf_mode_direction="up",
                   basis="reasoning from record + 2nd-order mechanics; NOT measured")

    (ROOT / "_scratch/cache/r6f" / "transmissibility.json").write_text(json.dumps(O, indent=1,
                                                                         default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "transmissibility.json"))


if __name__ == "__main__":
    main()
