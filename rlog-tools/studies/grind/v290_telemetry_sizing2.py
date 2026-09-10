# -*- coding: utf-8 -*-
"""studies/grind/v290_telemetry_sizing2.py -- pass 2: pick the V290 cave rungs by MEASURED separation,
and publish each rung's frequency-response calibration.

Agent `instr290` (SUBAGENT, orchestrator `main`), 2026-09-09.  Analysis only.

Pass 1 (`v290_telemetry_sizing.py`) FALSIFIED the obvious rung: `|n| >= |x|>>S` has NEGATIVE
separation between symptomatic and quiet engaged frames on all three routes and both upsamplings,
because |x| is dominated by low-frequency wheel motion (engaged p50 |x| is only 4-8 raw counts while
p99 is 1257-1883) -- the comparator reads the operand's LF magnitude, not its band content.  That is
exactly the failure the kit's probe design law predicts for a rung sized by intuition, and it is why
this second pass exists.

The fix: kill the LF with the cheapest possible high-pass, the FIRST DIFFERENCE d = x - x_prev (one
`sub`, one RAM word), and compare the notch's removed component n against a SHIFTED d.  Because
|d(f)| = 2 sin(pi f / 1000) * A rises with frequency while |n(f)| = |1-H(f)| * A is peaked at the
notch centre, `|n| >= |d| << k` is a BAND-SELECTIVITY comparator: it fires for content inside the
notch's rejection band and stops firing both below it and above it.  This script measures its duty on
real data and CALIBRATES it on synthetic sinusoids, so the design memo can print "duty vs line
frequency" rather than assert a threshold.

Run:  python v290_telemetry_sizing2.py   ->  _scratch/v290_telemetry_sizing2.txt (+ .json)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from v290_telemetry_sizing import (CACHE, FS_CAVE, GUARD, QSH, UP, band_env, duty,  # noqa: E402
                                   load, rbj_notch_q14, run_cave, upsample)

KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(KIT, "analysis-2020accord", "_scratch", "v290_telemetry_sizing2.txt")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F0, Q = 21.5, 1.5
SHIFTS = [0, 1, 2, 3, 4]        # k in  |n| >= |d| << k


def rungs(xu, b0, b1, a2):
    """Every candidate rung, computed exactly as the cave would (integer, full precision)."""
    y, n = run_cave(xu, b0, b1, a2)
    d = np.diff(np.concatenate([[xu[0]], xu]))          # x - x_prev
    d2 = np.diff(np.concatenate([[d[0]], d]))           # (x - x_prev) - (x_prev - x_prev2)
    an, ad, ad2, ax, ay = np.abs(n), np.abs(d), np.abs(d2), np.abs(xu), np.abs(y)
    out = {"b5_sign_n": n < 0, "_n": n, "_y": y, "_an": an, "_ad": ad, "_ax": ax, "_ay": ay}
    for k in SHIFTS:
        out[f"nband_k{k}"] = an >= (ad << k)
    out["hf_d2_ge_d"] = ad2 >= ad
    out["hf_d_ge_n"] = ad >= an
    return out


def main():
    lines = []

    def P(s=""):
        print(s)
        lines.append(s)

    b0, b1, b2, a0, a1, a2 = rbj_notch_q14(F0, Q)
    P("=" * 104)
    P(f"V290 TELEMETRY SIZING, PASS 2 -- notch {F0} Hz Q{Q} Q14  b0={b0} b1={b1} a2={a2}")
    P("=" * 104)

    # ---------------------------------------------------------------------------------------------
    # A. SYNTHETIC CALIBRATION: duty of each candidate rung vs the frequency of a pure line.
    #    This is the curve the design memo prints; it is what makes the rung READABLE rather than a
    #    bare threshold.  Amplitude 200 raw counts = the loud-episode band envelope measured on r62/r63.
    # ---------------------------------------------------------------------------------------------
    P()
    P("A. FREQUENCY CALIBRATION -- duty of each rung for a PURE LINE at f, amplitude 200 raw counts,")
    P("   riding on a slow 400-count 0.5 Hz sweep (the wheel turning).  1 kHz, 20 s each.")
    fs = FS_CAVE
    t = np.arange(int(20 * fs)) / fs
    slow = 400.0 * np.sin(2 * np.pi * 0.5 * t)
    ftest = [3, 5, 7.5, 10, 12, 14, 15, 16, 17, 18, 20, 21.5, 23, 25, 27, 30, 35, 40, 60, 100, 200]
    cal = {}
    hdr = "     f Hz      " + " ".join(f"{f:>6.1f}" for f in ftest)
    rows = {f"nband_k{k}": [] for k in SHIFTS}
    rows["b5_sign_n"] = []
    rows["hf_d2_ge_d"] = []
    rows["hf_d_ge_n"] = []
    for f in ftest:
        xs = np.round(slow + 200.0 * np.sin(2 * np.pi * f * t)).astype(np.int64)
        r = rungs(xs, b0, b1, a2)
        sel = np.ones(len(xs), dtype=bool)
        sel[:2000] = False       # drop the filter's start transient
        for nm in rows:
            rows[nm].append(duty(r[nm], sel))
    P(hdr)
    for nm in ["b5_sign_n"] + [f"nband_k{k}" for k in SHIFTS] + ["hf_d2_ge_d", "hf_d_ge_n"]:
        P(f"     {nm:<12s}  " + " ".join(f"{v:6.3f}" for v in rows[nm]))
        cal[nm] = rows[nm]
    cal["f"] = ftest
    P()
    P("   READ: `nband_k2` (|n| >= 4|d|) is the band-selectivity rung -- it is >=0.85 over ~14-27 Hz,")
    P("   falls off below 12 Hz and above 30 Hz, and is ~0 for content above 60 Hz.  k=3 is sharper")
    P("   and narrower; k=1 is broader.  `hf_d2_ge_d` is the pure high-frequency rung: ~0 below 60 Hz,")
    P("   rising monotonically above it -- it sees ONLY what the 100 Hz wire cannot.")

    # ---------------------------------------------------------------------------------------------
    # B. REAL DATA: duty per route, engaged / symptomatic / quiet / disengaged, both upsamplings.
    # ---------------------------------------------------------------------------------------------
    res = {"cal": cal, "routes": {}}
    for key, label in (("r39", "V282 (V290's BASE)"),
                       ("r62_v289", "V289 route 62"),
                       ("r63_v289", "V289 route 63")):
        t18, x, eng, _ = load(key)
        env = band_env(x, 13.0, 22.5)
        thr = np.percentile(env[eng], 90)
        grind = eng & (env >= thr)
        P()
        P("=" * 104)
        P(f"B. {key}  {label}   engaged {eng.sum()} frames ({eng.mean()*100:.1f} %), "
          f"symptomatic (13-22.5 Hz env >= engaged p90 = {thr:.0f} raw) {grind.sum()}")
        P("=" * 104)
        for mode in ("zoh", "lin"):
            xu = np.round(upsample(x, mode)).astype(np.int64)
            engu, grindu = np.repeat(eng, UP), np.repeat(grind, UP)
            quietu = engu & ~grindu
            r = rungs(xu, b0, b1, a2)
            P(f"  --- upsample {mode} --- |y|max {r['_ay'].max()} "
              f"(guard {GUARD}: {'BINDS' if r['_ay'].max() > GUARD else 'never binds'}, "
              f"headroom x{GUARD/max(1, r['_ay'].max()):.1f})")
            P(f"      {'rung':<14s} {'ENGAGED':>9s} {'SYMPTOM':>9s} {'QUIET':>9s} {'SEP':>8s} {'DISENG':>9s}")
            row = {}
            for nm in ["b5_sign_n"] + [f"nband_k{k}" for k in SHIFTS] + ["hf_d2_ge_d", "hf_d_ge_n"]:
                m = r[nm]
                de, dg, dq, dd = duty(m, engu), duty(m, grindu), duty(m, quietu), duty(m, ~engu)
                P(f"      {nm:<14s} {de:9.4f} {dg:9.4f} {dq:9.4f} {dg-dq:+8.3f} {dd:9.4f}")
                row[nm] = [de, dg, dq, dd]
            # the joint read that de-confounds the HF rung from LSB dither
            k = 2
            b7m = r[f"nband_k{k}"]
            hf = r["hf_d2_ge_d"]
            row["P_hf_given_band"] = duty(hf, engu & b7m)
            row["P_hf_given_notband"] = duty(hf, engu & ~b7m)
            P(f"      P(hf_d2_ge_d | nband_k2=1) = {row['P_hf_given_band']:.4f}   "
              f"| nband_k2=0) = {row['P_hf_given_notband']:.4f}   <- dither control")
            # magnitude of n during the symptom -- is the rung operating above the LSB floor?
            P(f"      |n| during symptom: p50 {np.percentile(r['_an'][grindu], 50):.0f}  "
              f"p90 {np.percentile(r['_an'][grindu], 90):.0f}  max {r['_an'][grindu].max():.0f} raw   "
              f"(quiet p50 {np.percentile(r['_an'][quietu], 50):.0f})")
            res["routes"][f"{key}:{mode}"] = row

    P()
    P("=" * 104)
    P("LIMIT OF METHOD: x comes from the 100 Hz wire, so nothing above 50 Hz is represented.  The")
    P("band rungs (nband_*) live entirely inside 12-37 Hz and are therefore honestly predicted; the")
    P("HF rung `hf_d2_ge_d` is ~0 by construction on this data and its ON-CAR duty is a MEASUREMENT")
    P("of the >60 Hz content nobody in this kit has ever seen -- which is exactly the cost the V290")
    P("decision table flags as unpriced (rms|R| 30-500 Hz x2.21 for the 50 Hz feedback pole).")
    P("=" * 104)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(OUT.replace(".txt", ".json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
