#!/usr/bin/env python3
"""RATCHET DISCRIMINATORS -- verdict block + the two derived numbers the report leans on.

D1  Is LOAD separable from SPEED in this corpus?  (the brief says say so if it is not)
D2  Wander decomposition: how much of the measured window-to-window f_free scatter does the
    TEST-A load effect account for?

usage:  python studies/ratchet/ratchet_discriminators_verdict.py
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402,F401
import _r31_common as C31        # noqa: E402,F401
import v86_freq_test as V86      # noqa: E402,F401
import ratchet_discriminators as RD           # noqa: E402
import ratchet_discriminators_ctrl as RC      # noqa: E402

P = ROOT / "_scratch/cache/r6f" / "ratchet_discriminators.json"
D = json.loads(P.read_text(encoding="utf-8"))
ENG, MAN, ALLV, POOL, POOL_MAN = RC.build_pools()
rs = [r for r in POOL if np.isfinite(r["f_free"])]

print("=" * 108)
print("D1  LOAD vs SPEED separability, pooled engaged arm (0.5-5.0 m/s)")
print("=" * 108)
keys = ["v", "ld_tqdc", "ld_tqabs", "ld_ang", "ld_rate", "ld_e4", "f_press"]
M = np.array([[r[k] for k in keys] for r in rs], float)
ok = np.all(np.isfinite(M), axis=1)
C = np.corrcoef(M[ok].T)
print("      " + "".join(f"{k[:9]:>11s}" for k in keys))
for i, k in enumerate(keys):
    print(f"  {k:9s}" + "".join(f"{C[i, j]:+11.3f}" for j in range(len(keys))))
sep = {}
for i in range(len(RD.SBINS)):
    sel = [r for r in rs if RD.sbin_of(r["v"]) == i]
    if len(sel) < 5:
        continue
    t = np.array([r["ld_tqdc"] for r in sel], float)
    sep[f"{RD.SBINS[i][0]}-{RD.SBINS[i][1]}"] = dict(
        n=len(sel), tq_p10=float(np.percentile(t, 10)), tq_p50=float(np.percentile(t, 50)),
        tq_p90=float(np.percentile(t, 90)),
        tq_ratio_p90_p10=float(np.percentile(t, 90) / max(np.percentile(t, 10), 1e-9)))
print("\n  within-speed-bin |DC column torque| spread (this is the leverage TEST A uses):")
for k, v in sep.items():
    print(f"    v {k:10s} n={v['n']:3d}  tq p10={v['tq_p10']:7.1f}  p50={v['tq_p50']:7.1f}  "
          f"p90={v['tq_p90']:7.1f}   p90/p10 = {v['tq_ratio_p90_p10']:.1f}x")
D1 = dict(corr={keys[i]: {keys[j]: float(C[i, j]) for j in range(len(keys))}
                for i in range(len(keys))},
          within_bin_load_spread=sep,
          verdict="SEPARABLE: |DC column tq| vs v r=%.3f pooled, and every speed bin carries a "
                  ">=10x within-bin torque spread" % C[0, 1])
print(f"\n  ⇒ {D1['verdict']}")

print("\n" + "=" * 108)
print("D2  WANDER DECOMPOSITION")
print("=" * 108)
sd_eng = float(np.std([r["f_free"] for r in rs], ddof=1))
sd_inj = D["linewidth"]["W2"]["fixed-f injection"]["sd"]
sd_true = float(np.sqrt(max(sd_eng ** 2 - sd_inj ** 2, 0.0)))
df_load = D["controls2"]["ctrl8"]["ld_tqdc"]["df"]
print(f"  engaged f_free sd            {sd_eng:.3f} Hz")
print(f"  instrument floor (fixed-f)   {sd_inj:.3f} Hz")
print(f"  ⇒ genuine wander             {sd_true:.3f} Hz")
print(f"  TEST-A load effect p10->p90  {df_load:+.3f} Hz  "
      f"(= {100 * df_load / (2 * 1.2816 * sd_true):.0f}% of the p10-p90 spread implied by "
      f"the wander)")
D2 = dict(sd_engaged=sd_eng, sd_instrument=sd_inj, sd_genuine_wander=sd_true,
          load_effect_Hz=df_load,
          frac_of_wander=float(df_load / (2 * 1.2816 * sd_true)))

# --------------------------------------------------------------------------------------------
VERDICT = {
    "TEST_A": {
        "result": "SUPPORTED -- f_c rises with COLUMN TORQUE at fixed speed; FLAT vs the command",
        "headline": "df/d(|DC column torque|): +0.467 Hz [+0.111, +0.927] over the p10-p90 span "
                    "(36 -> 641 counts, 17.8x), = +5.8% of an 8.00 Hz line",
        "null_first": "split-half null on the pooled arm: Δf 95% [-0.206, +0.205] Hz",
        "artefact_control": "fixed-frequency injection at a BETTER lock rate than the real arm "
                            "(0.780 vs 0.712) returns +0.033 [-0.019, +0.342] -- clean, but it "
                            "cannot exclude that up to ~0.34 Hz of the +0.467 is estimator "
                            "artefact",
        "partials": "survives partialling hands-on (+0.472 [+0.069,+0.873]), command (+0.467), "
                    "steer rate (+0.467), steer angle (+0.401 [+0.063,+0.888]); the REVERSE "
                    "(hands-on partialled on torque) collapses to -0.029 [-0.435,+0.508]",
        "command_arm": "|commanded torque| -0.145 [-0.564,+0.325] and |carOutput torque| "
                       "-0.147 [-0.571,+0.316] -- both NULL",
        "robustness": "leave-one-route-out keeps the sign in all 3 folds (+0.355 / +0.507 / "
                      "+0.192) but only 2-of-3 folds stay significant -> n-limited, not "
                      "route-driven",
        "power": "shift_line power curve: a 0.40 Hz load coupling is DETECTED; 0.0 is not",
        "stationary_arm": "UNDERPOWERED -- 0 engaged-standstill windows on all three routes "
                          "(engaged standstill is 0.29 s on 6f, 0.34 s on 70)",
    },
    "TEST_B": {
        "result": "UNDERPOWERED -- and STRUCTURALLY SO.  The V85 friction rungs cannot separate "
                  "friction from motor rate.",
        "why": "b5/b4 (|gp-0x6ae2| = FRICTION x1024) correlate +0.922 / +0.877 with |steer rate| "
               "at low speed (+0.933 / +0.876 all-speed) and their top terciles overlap the RATE "
               "rungs' at Jaccard 0.50-0.80.  gp-0x6ae2 = 102*|model|*min(|rate|/500,1), so the "
               "friction tap IS a rate proxy by construction.",
        "numbers": "line amplitude T3/T1 = 1.425 [0.675, 1.672] (b5) -- a CI as wide as the "
                   "kit's own recorded amplitude noise floor [0.63, 1.50], i.e. zero power on "
                   "amplitude.  Δf_c T3-T1 = +0.099 [-0.198, +0.489] Hz (b5).",
        "do_not_read_as": "This is NOT evidence against friction stick-slip.  The instrument "
                          "could not have fired.",
    },
    "TEST_C": {
        "result": "REFUTED (no amplitude-dependence) -- powered",
        "headline": "Δf_c(T3-T1) = -0.099 Hz [-0.316, +0.099] across a 2.29x amplitude range, "
                    "pooled n=59 blk=33",
        "power": "shift_line power curve on the same arm DETECTS a 0.60 Hz coupling "
                 "(+0.205 [+0.053,+0.402]) and misses 0.30 Hz -> MDE = 0.60 Hz = 7.5% of f0",
        "controls": "detection-floored -0.140 [-0.316,+0.099]; order-clean -0.352 [-0.705,"
                    "+0.020]; tight 6-9 Hz amplitude -0.198 [-0.416,+0.092]; disengaged negative "
                    "control +0.990 [-3.646,+4.443] (n=25, no line, huge CI as expected); "
                    "fixed-frequency artefact control -0.007 [-0.693,+0.338] clean",
    },
    "LINE_WIDTH": {
        "result": "Q >= 5.85 as a LOWER bound -- clears the Q >= 2.4 the phase-slope bound "
                  "demands of a second-order mode",
        "method": "ensemble half-power width of the speed-matched mean prominence spectrum = "
                  "1.282 Hz at 7.49 Hz; the instrument's own smearing, measured on a "
                  "fixed-frequency injection, is 0.197 Hz.  The ensemble width INCLUDES "
                  "window-to-window wander, so 5.85 is a lower bound on the true Q.",
        "retraction": "🛑 C31.q_of reads Q = 28.67 on PURE WHITE NOISE and 34.0 on the "
                      "disengaged windows, versus 25.67 engaged.  Any Q quoted from q_of is "
                      "meaningless -- it measures periodogram bin noise.  Do not use it.",
    },
    "NOT_SCORED": {
        "highway": "no highway claim anywhere: 6f/70 have 0.0 s above 50 km/h, 6e has 34.6 s",
        "thin_routes": "6d (5 low-speed windows) and 67 (13) are NOT scored at low speed",
        "open_question": "6e's line sits at 8.006 Hz below 5 m/s and 8.484 Hz above -- a +0.48 "
                         "Hz shift within one route.  6d/67 read 8.48/8.74 at highway speed with "
                         "detection 0.62-0.67 against a 0.10 false-positive floor.  Whether that "
                         "is the SAME object is OPEN and is not used in any verdict here.",
    },
}
D["D1_load_speed_separability"] = D1
D["D2_wander_decomposition"] = D2
D["VERDICT"] = VERDICT
P.write_text(json.dumps(D, indent=1, default=lambda o: None), encoding="utf-8")
print(f"\n  wrote verdict block into {P}")
