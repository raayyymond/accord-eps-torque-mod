#!/usr/bin/env python3
"""FINAL verdict block for the V86 ~8 Hz damping re-score, AFTER the control battery.

Supersedes the VERDICT written by studies/damping-q/qd_consolidate.py.  Two things changed once the controls ran:
  1. the linewidth family failed its control outright, so no Q ratio is reportable;
  2. my own "the line is a forest of >=8 coherent peaks" claim is RETRACTED -- a phase-randomised
     surrogate reproduces the forest with HIGHER prominence than the real data.

Usage:  python studies/damping-q/qd_verdict2.py
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2].parent
C = ROOT / "_scratch/cache/r6f"

blob = json.load(open(C / "q_damping_score.json"))
blob["qd_control"] = json.load(open(C / "qd_control.json"))
blob["VERDICT_SUPERSEDED_2026_08_09"] = blob.pop("VERDICT", None)

blob["VERDICT"] = {
    "question": "Did 0xC40D4 (command EMA alpha 573 -> 286) change the DAMPING of the ~8 Hz line?",
    "answer": "NOT MEASURABLE with this corpus. The linewidth family FAILS its own control, the "
              "one estimator that PASSES (ring-down) has n=1 on V86, and no damping ratio between "
              "builds is reportable. This is the underpowered case, not a null.",

    "CONTROLS_FIRST": {
        "protocol": "synthetic modes of known Q injected into REAL manual windows from these "
                    "routes, run through the exact pipelines that scored the car; two injection "
                    "conventions (fixed 40x band-power SNR; prominence-matched to 70x)",
        "T_10.1s_fixed_SNR": {
            "Q_true":  [1, 2, 3, 5, 10, 25, 50, 100, 250, "inf"],
            "linewidth": [38.7, 45.0, 44.1, 45.5, 43.0, 44.5, 47.4, 49.1, 53.0, 54.8],
            "welch":     [20.9, 19.7, 18.8, 14.4, 17.6, 18.0, 21.9, 24.0, 25.9, 27.4],
            "phase":     [132.8, 81.3, 64.7, 81.0, 143.7, 150.6, 269.0, 532.6, 1768.4, 98900.0],
            "env_CV":    [0.540, 0.521, 0.535, 0.538, 0.517, 0.508, 0.465, 0.443, 0.322, 0.112],
            "env_duty":  [0.208, 0.194, 0.203, 0.199, 0.195, 0.179, 0.176, 0.145, 0.060, 0.000],
        },
        "verdicts": {
            "linewidth": "FAIL. Returns 38.7 for a Q=1 mode. Readout span over Q_true = 1..inf is "
                         "1.37x, against a single-window p16-p84 spread of 1.79x -- the noise on "
                         "ONE window exceeds the estimator's ENTIRE dynamic range. Same family as "
                         "catA_linewidth.py and C31/_grind2/_r47 q_of.",
            "welch": "FAIL. 8-DOF averaging does not rescue it: span 1.80x vs spread 1.87x.",
            "phase": "FAIL in the relevant range. Span 27x (T=10.1 s) / 46x (T=20.3 s), but it "
                     "reads 132.8 for Q_true=1 and is NON-MONOTONE from Q=1 to Q=25 "
                     "(22.8, 11.8, 19.6, 17.8, 21.7, 39.1 at T=20.3 s). Usable only above Q~50.",
            "env_CV_duty": "CONDITIONAL. Monotone in log Q under fixed-SNR injection "
                           "(r = -0.86 to -0.90) but the correlation COLLAPSES under "
                           "amplitude-matched injection (CV r = -0.076). They track amplitude AND "
                           "coherence jointly; with amplitude itself unmeasured "
                           "(a779 = 1.196 [0.732,1.731]) the damping component cannot be "
                           "extracted.",
            "ringdown": "PASS in the regime that matters -- see below.",
        },
    },

    "RINGDOWN_IS_THE_ONE_THAT_WORKS": {
        "control": {"zeta_true": [0.005, 0.010, 0.020, 0.050, 0.100, 0.200],
                    "zeta_recovered": [0.0071, 0.0111, 0.0196, 0.0789, 0.0783, 0.0695],
                    "log_log_r": 0.937,
                    "reading": "accurate for zeta = 0.005-0.02 (bias +42%, +11%, -2%); saturates "
                               "above zeta ~ 0.05 because the decay finishes inside the 2 s fit"},
        "measured_on_car": {"V86": [0.0366], "V86B": [0.0476, 0.0164], "V85": [0.0473],
                            "note": "one further V86B edge had a RISING envelope and is not a "
                                    "ring-down"},
        "de_biased": "zeta ~ 0.017-0.036  =>  Q ~ 14-29",
        "consequence": "This is a controlled, non-spectral, physical measurement and it is "
                       "INCONSISTENT with zeta <= 0.007 / Q = 500-1500. It is fully consistent "
                       "with a lightly-damped structural resonance at Q ~ 15-30.",
        "why_it_cannot_answer_the_build_question": "usable falling edges: V86 = 1, V86B = 3, "
                                                   "V85 = 1. The single-variable pair is n=1 vs "
                                                   "n=3. V86 flew ONE unbroken 139.6 s engagement.",
        "caveat": "the falling edge switches mode 26 -> 24, so this measures the DISENGAGED "
                  "plant, not the engaged loop -- it bounds the mechanical mode, it does not "
                  "measure the loop gain that 0xC40D4 sits in",
    },

    "RETRACTION_OF_MY_OWN_CLAIM": {
        "retracted": "'The ~8 Hz line is a FOREST of >=8 coherent narrow peaks' -- reported by me "
                     "earlier this session. WITHDRAWN.",
        "why": "A PHASE-RANDOMISED SURROGATE of V86's engaged run -- identical power spectrum, "
               "destroyed phase structure -- returns 8 peaks at prominence "
               "171/127/105/104/93/86/86/60, i.e. MORE prominent than the real data's "
               "91/79/74/63/59/59/58/57. The census cannot tell a coherent line from speckle on a "
               "coloured, non-stationary background. White noise gives only 1-2 peaks at 8-13x, "
               "which is what made the forest look significant -- the wrong null.",
        "knock_on": "the 'line at 1.15x the window limit, coherent for ~1000 cycles' reading is "
                    "the same artefact: it is the tallest speckle bin of a 2-DOF periodogram. The "
                    "f0 scatter of 0.53 Hz inside one run is speckle too, so there is no paradox "
                    "left to explain.",
    },

    "WHAT_STILL_STANDS": {
        "zoh_refutation": "STANDS. It rests on arrival-rate arithmetic, not on periodogram peaks: "
                          "0x14A and 0x18F differ by 4.0-27.7 mHz, so any sample-and-hold beat is "
                          "at ~0.004-0.028 Hz. Hold age median 0.00 ms, sd 1.2-1.4 ms.",
        "q_of_defect": "STANDS -- direct test, independent of everything above. C31.q_of returns "
                       "median Q = 79.00 on PURE WHITE NOISE at nfft=1024, ABOVE its own 54.73 "
                       "window limit. _grind2_lib.q_of and _r47_imu_lib.q_of are identical in "
                       "logic and return 79.00 too; _r37_ratchet_lib.q_of delegates to C31. "
                       "25 files call one of them.",
        "underpowered_verdict": "STANDS and is now far better supported.",
        "engaged_only_line": "STANDS. Engaged prominence 34-72x vs manual 8-13x; engaged envelope "
                             "p99 957-1229 ct vs manual 96-188 ct.",
    },

    "PHYSICS": "The limit-cycle-vs-resonance question is now ANSWERED in the direction of "
               "RESONANCE, not by the spectra but by the ring-down: zeta ~ 0.017-0.036 (Q ~ 14-29) "
               "from a controlled estimator. [EVIDENCE, n=5 edges across 3 routes, disengaged "
               "plant.] No spectral evidence for high phase coherence survives its control.",

    "PROTOCOL_TO_SETTLE_THE_BUILD_QUESTION": {
        "do_this": "RING-DOWN, deliberately. 30 engage / hold-until-the-line-runs / disengage "
                   "cycles per arm at matched speed is ~10 min of driving per arm and yields 30 "
                   "independent zeta values from an estimator that PASSES its control at "
                   "zeta = 0.005-0.02.",
        "sample_size": "with the control's p16-p84 spread of ~1.3x at zeta = 0.01-0.02, 30 edges "
                       "per arm gives a per-arm zeta CI of roughly +-10%, enough to see a 1.25x "
                       "damping change in a DiD against the same-alpha pair",
        "do_not_do_this": "do NOT buy more parking-lot laps hoping the linewidth sharpens. The "
                          "linewidth estimator does not improve with n -- it has no dynamic range "
                          "to begin with. More windows buy precision on a number that is not "
                          "damping.",
        "fit_window": "shorten the ring-down fit from 2.0 s to ~0.8 s and raise the sample rate of "
                      "the envelope floor estimate, to push the saturation knee above zeta = 0.05 "
                      "-- the on-car values sit right at the current knee",
    },
}
json.dump(blob, open(C / "q_damping_score.json", "w"), indent=1, default=float)
print("wrote", C / "q_damping_score.json")
print("top keys:", sorted(blob.keys()))
