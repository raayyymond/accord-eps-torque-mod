# B1 method verification (independent re-derivation)

Script: scripts/redo_b1.py (written fresh from red_<route>.npz + obs_<route>.npz, does NOT
import bs.py/b02_beq.py/b07_rank.py).

## Reproduced numbers (rev64 group, tau=30ms)
- Energy share of <8 m/s band-rate energy: <3=0.079, 3-6=0.408, 6-8=0.513 -- EXACT match to b07_rank.txt.
- dob_log b_eq @30ms: <3=-0.01, 3-6=-0.88, 6-8=-1.32(mine 1.315 vs 1.32), 3-8=-1.12(mine 1.123), <8=-1.03(mine 1.035), 8-15=-2.13(mine 2.134) -- all match the paper table to <0.02e-4.
- Per-route 6-8 m/s dob_log: 6c=-1.64, 6d=-1.70, 6e=-1.22 -- EXACT match to b07_rank.txt "routes -1.64 -1.70 -1.22".
- Sign/positive-control check: ctrl=-1e-3*sr read exactly +10.000e-4 at tau=0 in every bin -- confirms the b_eq formula sign.

## Sign of the observer term (dob_log = -logged) -- independently checked two ways
1. Read latcontrol_torque.py directly: inner_torque += -self.accord_dob_torque (prev frame) and
   accordObserverTorque (logged) = -self.accord_dob_torque (this frame) => contribution(t) = logged(t-1frame),
   i.e. contribution = +logged with a ~10ms lag. Read at face value this looked like it might contradict the
   "-logged" convention used throughout the study and stated in the orchestrator brief.
2. Resolved by the replica cross-check already in the pipeline: red_<route>.npz's 'dob' field is built by
   fill_texturetermd/t02_reduce.py from s5ctl.Ctl, an independent line-by-line Python transcription of the actual
   fork commits, itself validated against the REAL logged command u_log at corr>=0.996 (t02_reduce.py docstring).
   Its correlation with dob_log (=-logged telemetry) is 0.997-0.998 with slope ~0.98-1.04 in every route/bin
   (out/b02_validation.json, reproduced here). This is independent, non-circular confirmation that dob_log=-logged
   is the correct-signed contribution -- the one-frame-lag / torque-frame subtlety in the raw code does not flip it.
   CONCLUSION: sign convention holds.

## Arithmetic check on the "13% of total feed" sentence
Finding writes: "setpoint-driven terms -7.4e-4, observer -1.1e-4, friction hysteresis -0.4e-4" (implying a 3-bucket
sum to -8.9e-4, observer share 12.4%). But 'ffwd' (source of the -7.4 figure) is defined as
hold+move+hyst+rl_ff+p_sp -- it ALREADY INCLUDES hyst. So this decomposition double-counts hyst by ~0.4e-4.
- As displayed by the finding (double-counted): observer share = 1.1/8.9 = 12.4%, not quite 13%.
- Properly counted (ffwd once + dob_log, no double-count): -7.36 + -1.12 = -8.48e-4 total; observer share
  1.12/8.48 = 13.2% -- THIS matches the "about 13%" headline number.
Net effect: minor internal arithmetic inconsistency in the displayed breakdown, but the headline "~13%" figure is
actually right (matches the non-double-counted total, not the double-counted one as displayed). Does not change
the qualitative conclusion (observer is a minority feeder at 3-8 m/s).

## 6-8 m/s exception claim
"6c/6d ... observer (-1.64/-1.70e-4) is as large as or larger than the setpoint-driven terms (-0.9/-1.9e-4)":
- 6c: dob_log=-1.64 vs ffwd=-0.91 -> observer strictly LARGER. Confirmed.
- 6d: dob_log=-1.70 vs ffwd=-1.93 -> observer is actually SMALLER (87% of ffwd), not "as large as or larger than".
  Mild overstatement for 6d specifically, though the two are close in magnitude (same order).
"planner dominance there comes from 6e (-9.8e-4)": 6e ffwd(setpoint-side) = -9.82e-4 -- EXACT match. Confirmed.

## 8-15 m/s claim
dob_log @30ms = -2.134e-4 (paper: -2.13 [-2.26,-1.99]) -- match. ffwd (setpoint-side, incl hyst) = -0.05e-4,
essentially zero -- confirms "the observer is the only real feeder" there.

## Verdict
Core numerical claims reproduce closely under an independently-written script; sign convention holds under a
second independent check (replica-vs-telemetry correlation, itself anchored to the real logged command). Two
minor, non-conclusion-changing imprecisions found: (1) the "-7.4/-1.1/-0.4" breakdown double-counts hyst
(headline 13% is still right by coincidence/proper accounting), (2) "6c/6d ... as large as or larger than" is a
mild overstatement for 6d alone (observer ~87% of setpoint-driven there, not >=100%).
Not refuted. B1's central lever-reach conclusion (ARM-D observer-off will act mainly >=8 m/s; below 8 m/s it is a
minority feeder except on quiet 6-8 m/s driving) holds.
