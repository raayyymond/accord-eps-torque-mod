# -*- coding: utf-8 -*-
"""studies/grind/v290_telemetry_sizing3.py -- pass 3: the MAGNITUDE channel for |n|, sized against the
distribution passes 1 and 2 measured, plus the operand-refresh control.

Agent `instr290` (SUBAGENT, orchestrator `main`), 2026-09-09.  Analysis only.

Passes 1 and 2 falsified both ratio families:
  * `|n| >= |x|>>S`  -- negative separation; reads the operand's LF magnitude, not its band content.
  * `|n| >= |d|<<k`  -- flat on real data.  Its synthetic calibration IS band-selective (k=3 peaks at
    0.50 at 20 Hz, half-max ~10 and ~30 Hz), but on the car both the numerator and the denominator are
    at the LSB floor on quiet frames (engaged p50 |x| = 4-8 raw counts) and the ratio becomes a coin
    flip; and a Q1.5 notch leaks 16 % at 5 Hz / 26 % at 7.5 Hz, so `n` is not a clean band indicator
    during the loaded turns where the operator's bookmarks sit.

What survives is the thing the kit's design law actually asks for -- a SIGN BIT PAIRED WITH A
MAGNITUDE CHANNEL -- with the magnitude channel's threshold now sized from a MEASURED distribution on
three routes instead of guessed.  `n = x - y` is band-limited by construction (|1-H| -> 0 at both DC
and Nyquist; it is >= 0.5 only over 12.4-37.1 Hz), so the 100 Hz wire predicts its magnitude honestly:
nothing above 50 Hz can inflate it.

Run:  python v290_telemetry_sizing3.py   ->  _scratch/v290_telemetry_sizing3.txt (+ .json)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from v290_telemetry_sizing import (UP, band_env, duty, load, rbj_notch_q14,  # noqa: E402
                                   run_cave, upsample)

KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(KIT, "analysis-2020accord", "_scratch", "v290_telemetry_sizing3.txt")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F0, Q = 21.5, 1.5
THRESH = [4, 8, 12, 16, 24, 32, 48, 64]
KSH = [0, 1, 2, 3, 4]


def main():
    lines = []

    def P(s=""):
        print(s)
        lines.append(s)

    b0, b1, b2, a0, a1, a2 = rbj_notch_q14(F0, Q)
    P("=" * 108)
    P(f"V290 TELEMETRY SIZING, PASS 3 -- the |n| magnitude channel.  notch {F0} Hz Q{Q} Q14 "
      f"b0={b0} b1={b1} a2={a2}")
    P("=" * 108)
    res = {}
    for key, label in (("r39", "V282 (V290's BASE)"),
                       ("r62_v289", "V289 r62"),
                       ("r63_v289", "V289 r63")):
        t18, x, eng, _ = load(key)
        env = band_env(x, 13.0, 22.5)
        thr = np.percentile(env[eng], 90)
        grind = eng & (env >= thr)
        P()
        P("=" * 108)
        P(f"{key}  {label}   engaged {eng.sum()}  symptomatic {grind.sum()} (13-22.5 Hz env >= p90 = {thr:.0f} raw)")
        P("=" * 108)
        for mode in ("zoh", "lin"):
            xu = np.round(upsample(x, mode)).astype(np.int64)
            engu, grindu = np.repeat(eng, UP), np.repeat(grind, UP)
            quietu = engu & ~grindu
            y, n = run_cave(xu, b0, b1, a2)
            an, ay = np.abs(n), np.abs(y)
            P(f"  --- upsample {mode} ---")
            P(f"      |n| distribution (raw counts):  engaged p50 {np.percentile(an[engu],50):.0f} "
              f"p90 {np.percentile(an[engu],90):.0f} p99 {np.percentile(an[engu],99):.0f} max {an[engu].max():.0f}"
              f"  |  SYMPTOM p50 {np.percentile(an[grindu],50):.0f} p90 {np.percentile(an[grindu],90):.0f} "
              f"max {an[grindu].max():.0f}  |  QUIET p50 {np.percentile(an[quietu],50):.0f} "
              f"p90 {np.percentile(an[quietu],90):.0f}  |  DISENG p50 {np.percentile(an[~engu],50):.0f} "
              f"p90 {np.percentile(an[~engu],90):.0f}")
            P(f"      {'|n| >= T':<12s} " + " ".join(f"{t:>6d}" for t in THRESH))
            row = {}
            for nm, sel in (("ENGAGED", engu), ("SYMPTOM", grindu), ("QUIET", quietu), ("DISENG", ~engu)):
                v = [duty(an >= t, sel) for t in THRESH]
                row["T_" + nm] = v
                P(f"      {nm:<12s} " + " ".join(f"{q:6.3f}" for q in v))
            sep = [row["T_SYMPTOM"][i] - row["T_QUIET"][i] for i in range(len(THRESH))]
            rat = [row["T_SYMPTOM"][i] / max(1e-9, row["T_QUIET"][i]) for i in range(len(THRESH))]
            P(f"      {'SEP':<12s} " + " ".join(f"{q:+6.3f}" for q in sep))
            P(f"      {'RATIO S/Q':<12s} " + " ".join(f"{q:6.1f}" for q in rat))
            row["T_SEP"], row["T_RATIO"] = sep, rat
            P(f"      {'|n|>=|y|>>k':<12s} " + " ".join(f"{k:>6d}" for k in KSH))
            for nm, sel in (("ENGAGED", engu), ("SYMPTOM", grindu), ("QUIET", quietu), ("DISENG", ~engu)):
                v = [duty(an >= (ay >> k), sel) for k in KSH]
                row["K_" + nm] = v
                P(f"      {nm:<12s} " + " ".join(f"{q:6.3f}" for q in v))
            res[f"{key}:{mode}"] = row

    P()
    P("=" * 108)
    P("CHOICE: the threshold that maximises SYMPTOM/QUIET contrast while keeping the engaged duty")
    P("well inside (0,1) on every route and both upsamplings.  See the design memo for the pick.")
    P("=" * 108)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(OUT.replace(".txt", ".json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
