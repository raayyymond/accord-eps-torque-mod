# C2 verification notes (method lens)

## 1. Sign audit of the DOB reconstruction (cl_recon.py `dob_left = -dob_logged`)

Traced by hand through `latcontrol_torque.py` (@84766cdc):
- line 670: `inner_torque += -self.accord_dob_torque` -> the torque-frame contribution of the observer to `ff_torque` is `-ADT` (ADT = `accord_dob_torque`).
- line 850: `accordObserverTorque = -ADT` (this is `L`, the raw logged field) -- comment at 849 confirms: "the observer's term as added to the feedforward (torque frame)".
- so in the angle-frame equation `-f/LAF = hold+move+z+rate_t+dob_left`, `dob_left` should equal `ADT` (negating the torque-frame `-ADT` contribution back to angle frame) = `-L`.

Traced the actual data pipeline: `fsr_extract.py` writes `A["dob"] = s.accordObserverTorque = L` (raw, unmodified) into `fill_straightroad/cache/<route>_fsr.npz`. `fsr_reduce.py` reads that SAME cache file but writes its own negated copy to a DIFFERENT directory (`fill_straightroad/reduced/`), which `cl_recon.py` does NOT read. `cl_recon.py` reads `fill_straightroad/cache/<route>_fsr.npz` directly, i.e. `dob_logged = L`, then computes `dob_left = -dob_logged = -L`.

**Result: `dob_left = -L` matches the source-derived requirement exactly. No sign bug.** (I initially suspected a double-negation because `fsr_reduce.py` also negates `Fx["dob"]`, but it writes to a path `cl_recon.py` never reads, so there is no double negation in the actual pipeline.)

## 2. Independent re-derivation of the SHAKE-band b_eq (1.8-3.5 Hz, tau=30ms)

Method: per-run band-passed OLS slope (`term = b*rate`, `b_eq = -slope`) then a **weighted mean over runs + a bootstrap over RUNS (not frames)**, vs. the original's pooled dot-product over all frames. Route T64 (6c+6d).

| bin | rate_t (mine) | rate_t (orig) | out (mine) | out (orig) | out-rate_t (mine) | out-rate_t (orig, quoted) |
|---|---|---|---|---|---|---|
| 2.5-5 | +6.51 [5.33,7.46] | +6.27 | +2.84 [-0.12,5.39] | +1.86 | -3.67 | -4.4 |
| 5-8 | +5.94 [5.41,6.76] | +5.27 | +0.65 [0.09,2.98] | -0.46 | -5.29 | -5.7 |
| 8-15 | +7.32 [7.03,7.58] | +7.50 | +4.47 [3.56,5.29] | +4.89 | -2.85 | (n/a, not quoted <8m/s) |

`rate_t` reproduces closely (within ~10%) at all three bins with a structurally different estimator. `out - rate_t` is negative at every bin tested with either method -- **the core claim ("without the rate loop the command would feed the shake below 8 m/s") is confirmed, and I additionally confirm it stays negative up to 15 m/s.**

One genuine discrepancy: at 5-8 m/s the sign of the **whole command alone** (`out`) differs between methods -- original pooled estimator: -0.46 (feeds), mine: +0.65 [0.09, 2.98] (damps, CI excludes the original's point value). Both are small next to `rate_t`'s +5.3 to +5.9, so it doesn't change the dominant-term conclusion, but it's a real method-sensitivity on that one specific sub-number.

## 3. 3.5-6 Hz "pumping band", rate_t only, T64 pooled

Independent per-run OLS: **+4.38e-4 at tau=30ms, -2.95e-4 at tau=60ms.** Matches the claimed "+4.7 to +6.9 at 30ms, -2.1 to -4.2 at 60ms" (mine sits just under the low end at 30ms, inside the range at 60ms). The sign flip with lag -- damps at 30ms, feeds at 60ms -- is reproduced, supporting the claim that headroom "depends on the true effective delay" (flagged BELIEF).

## 4. Constants, read directly from `latcontrol_vehicle_tunes.py` (not from cl_recon's copies)

- `HONDA_ACCORD_RATE_LOOP_TAPER_V = 12.0` -- confirms "untapered below 12 m/s" and taper factor `min(1, 12/v)`: at v=20, 12/20=0.60; at v=26, 12/26=0.4615 -- matches claimed "0.46-0.6 of the gain at 20-26 m/s" exactly.
- `HONDA_ACCORD_DOB_FADE_V_BP = [3.0, 6.0]` -- confirms observer fade reaches fade=1.0 (full strength) at v=6, not 8.

## 5. Overshoot fraction (observer-on vs T4 observer-off), independently parameterized event detector

Detector changed: smoothing window 6 samples (not 10), low-rate threshold 0.8 deg/s (not 0.75), min dwell 10 frames (not 12), pre/post travel threshold 0.4 deg (not 0.5), post window 80 frames (not 100).

- T64 (observer on), pooled 6c+6d: n=104, overshoot>1deg fraction **0.37**
- T4 (observer off, `AccordDobHz=0.0`): n=133, overshoot>1deg fraction **0.22**

Original (finding's own detector): 0.61 (n=149, 6-15 m/s) vs 0.18 (n=66, 6-15 m/s).

**Direction reproduces** (observer-on overshoots more than observer-off) but the **gap shrinks** from ~3.4x to ~1.7x under a differently-but-reasonably parameterized detector. This is a legitimate caveat on the precision of "61% vs 18%" -- the number is sensitive to the dwell-detection recipe (a looser detector pulls in more small/noisy dwells that dilute both groups toward a common baseline). The qualitative causal-flagged claim ("keeps rising ... overshoots more") is not refuted, but the specific percentages should not be read as method-invariant.

## 6. "Rate-loop change over large jumps: -0.012 to -0.072 torque" -- located and reproduced

This number is the **`post_rate_t`** quantity in `cl_dwellpost.py` (change in `rate_t` 0-0.3s AFTER release, NOT the dwell-phase build before release, which is a different field `b_rate_t` in `cl_bigjumps.py`/`cl_reach.py` and behaves very differently -- see caveat below). Recomputing per-bin medians for T64 directly from `dwellpost.json` (jump >= 3 deg subset):

- T64 2.5-6 m/s: median -0.0349 (n=4)
- T64 6-8 m/s: median -0.0724 (n=2)
- T64 8-15 m/s: median -0.0124 (n=4)

**Reproduces the claimed range (-0.012 to -0.072) exactly.** Caveat: each of these medians comes from only 2-4 events -- the claim's own caveats section discloses small-N for the stick-slip p90 but does not separately flag the small N (2-4) behind this specific range.

I initially cross-checked the WRONG field (`b_rate_t`, the dwell-phase build) for the 18 large (>=7 deg) snaps and found it does NOT consistently oppose the jump (11/18 positive, median +0.0012) -- this is true but is a different quantity than what the claim describes ("opposes the jump ... over the jump"); it does not contradict the claim once the correct field (`post_rate_t`) is used.

## Bottom line

Every load-bearing quantity in C2 that I attempted to independently reproduce -- the rate loop's shake-band damping (1.8-3.5 Hz and 3.5-6 Hz, both lags), the untapered-below-12-m/s and DOB-fade-3-to-6 constants, the "-0.012 to -0.072" opposing-the-snap figure, and the direction of the observer/overshoot association -- reproduced under an independently-parameterized method, most within the claimed ranges. The two genuine soft spots are (a) the overshoot PERCENTAGES (61%/18%) being detector-parameter-sensitive (direction holds, magnitude does not), and (b) the whole-command sign at 5-8 m/s disagreeing between estimators on a small number next to a dominant rate_t term.
