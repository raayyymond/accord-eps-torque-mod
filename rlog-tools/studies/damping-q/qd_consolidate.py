#!/usr/bin/env python3
"""Consolidate the V86 ~8 Hz damping re-score into _scratch/cache/r6f/q_damping_score.json with a
top-level VERDICT block, so a reader gets the answer without traversing four files.

Usage:  python studies/damping-q/qd_consolidate.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2].parent
C = ROOT / "_scratch/cache/r6f"

blob = json.load(open(C / "q_damping_score.json"))
inner = blob.get("q_damping_score", blob)
for name in ("qd_power", "qd_phase", "qd_lines", "qd_sens"):
    p = C / f"{name}.json"
    if p.exists():
        blob[name] = json.load(open(p))

m10 = inner["matched"]["10.1 s"]
c10 = inner["contrasts"]["10.1 s"]["q_app"]

blob["VERDICT"] = {
    "question": "Did 0xC40D4 (command-branch EMA alpha, 573 -> 286) change the DAMPING of the "
                "~8 Hz line?",
    "answer": "UNDERPOWERED -- not a null. No estimator built here can resolve a Q change of the "
              "size at issue on these three routes.",
    "headline_Q_matched_T_10.13s": {
        "instrument_floor_Q": 54.7,
        "no_line_reference_Q": "29-34 (manual windows, prominence 8-13x)",
        "V86_alpha286": [m10["V86"]["q_app"]["pt"], m10["V86"]["q_app"]["lo"],
                         m10["V86"]["q_app"]["hi"], m10["V86"]["nblk"]],
        "V86B_alpha573": [m10["V86B"]["q_app"]["pt"], m10["V86B"]["q_app"]["lo"],
                          m10["V86B"]["q_app"]["hi"], m10["V86B"]["nblk"]],
        "V85_alpha573": [m10["V85"]["q_app"]["pt"], m10["V85"]["q_app"]["lo"],
                         m10["V85"]["q_app"]["hi"], m10["V85"]["nblk"]],
    },
    "same_alpha_null_V86B_over_V85": [c10["null"]["ratio"], c10["null"]["lo"], c10["null"]["hi"]],
    "single_variable_effect_V86_over_V86B": [c10["effect"]["ratio"], c10["effect"]["lo"],
                                             c10["effect"]["hi"]],
    "DiD": [c10["did"]["did"], c10["did"]["lo"], c10["did"]["hi"]],
    "sensitivity": "16 estimator variants (band x floor-subtraction x order-veto x median/mean): "
                   "effect ratio 0.790-1.044, 0/16 CIs exclude 1.00",
    "why_underpowered": "At T=10.13 s the linewidth readout maps Q_true=5 -> Q_app 44.5 and "
                        "Q_true=inf -> Q_app 55.1: the ENTIRE dynamic range over a 200x change "
                        "in true Q is 1.24x, against an effect CI of [0.53,1.41]. The estimator "
                        "cannot distinguish a heavily damped mode from a perfect tone.",
    "ringdown": "V86 supplies 1 usable latActive falling edge, V86B 3, V85 1 -- the "
                "single-variable pair has n=1 vs n=3, so the one damping measurement that is "
                "not window-limited cannot be run either.",
    "structural_finding": "The '~8 Hz line' is a FOREST, not a line: V86's 139.6 s engaged run "
                          "carries >=8 peaks between 7.41 and 8.41 Hz at 57-91x prominence, "
                          "several within 1.04-1.16x of the window limit. Per-window argmax hops "
                          "among them (f0 sd 0.53 Hz INSIDE the single run), which is why the "
                          "ensemble Q is 4.5-14 while a single peak reads 600+. 'Q of the 8 Hz "
                          "line' is ill-posed until the peak is named.",
    "zoh_artefact": "REFUTED. 0x14A and 0x18F arrive at rates differing by 4.0-27.7 mHz, so the "
                    "sample-and-hold beat is at ~0.004-0.028 Hz, not 7.5 Hz; hold age median "
                    "0.00 ms, sd 1.2-1.4 ms; the age sawtooth's own 4-12 Hz line sits 1.9-3.1 Hz "
                    "away from tq's and is 5-10x less prominent.",
    "q_of_flag": "C31.q_of returns median Q = 79.00 on PURE WHITE NOISE at nfft=1024 -- ABOVE the "
                 "54.73 window limit, i.e. physically impossible. It returns f0/bin-width whenever "
                 "the adjacent bin is higher. _grind2_lib.q_of and _r47_imu_lib.q_of are "
                 "byte-identical in logic and identically defective; _r37_ratchet_lib.q_of "
                 "delegates to C31. 25 files call one of them.",
    "protocol_to_settle": {
        "linewidth_needs": "T >= 2*1.4416*Q/f0 UNBROKEN engaged seconds per window: 37 s for "
                           "Q=100, 74 s for Q=200, 222 s for Q=600. V86B's longest engagement was "
                           "36.4 s, so no number of repeats could have resolved Q above ~100.",
        "precision_needs": "DiD SE(log) = 0.326 at blk 13/6/11; a +-20% DiD CI needs 10.2x the "
                           "blocks = ~10.3 min engaged speed-matched in the SMALLEST arm, and "
                           "+-15% needs ~18.4 min.",
        "combined": "~10 windows of >=222 s each per arm ~= 37 min of continuous engaged driving "
                    "per arm at matched speed -- a different route design, not a longer parking-"
                    "lot lap.",
        "cheaper_and_better": "RING-DOWN. 30 deliberate engage / hold-until-the-line-runs / "
                              "disengage cycles per arm is ~10 min of driving and yields 30 "
                              "independent zeta values, versus the 5 usable edges the three flown "
                              "routes contain between them.",
        "vs_the_amplitude_rule": "The session's rule '~5 engaged minutes per arm resolves a 1.2x "
                                 "amplitude effect' does NOT carry over: amplitude tolerates any "
                                 "window length, Q does not. For Q the equivalent is ~10 min per "
                                 "arm AND every minute of it in unbroken pieces longer than the "
                                 "coherence time.",
    },
}
json.dump(blob, open(C / "q_damping_score.json", "w"), indent=1, default=float)
print("wrote", C / "q_damping_score.json")
print(json.dumps(blob["VERDICT"]["headline_Q_matched_T_10.13s"], indent=1))
print("null", blob["VERDICT"]["same_alpha_null_V86B_over_V85"])
print("eff ", blob["VERDICT"]["single_variable_effect_V86_over_V86B"])
print("did ", blob["VERDICT"]["DiD"])
