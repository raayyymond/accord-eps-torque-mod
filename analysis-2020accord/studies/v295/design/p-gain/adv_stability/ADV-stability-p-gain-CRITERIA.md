# ADVERSARY "stability" vs the p-gain candidate R1.3_8_100 -- FAIL criteria, written BEFORE computing

Subagent `adv-stability (p-gain)`, 2026-09-30 11:15 PDT. Design review only. Written before any number of mine
exists. My job is to make the candidate FAIL on dynamics. Default verdict REFUTED if I cannot reproduce its central
numbers.

Candidate: Kp bank 0xCB994, all 28 records, X [0,8,54,100,208], Y [1248,1248,1104,960,960]; everything else V294
(image sha256 3143616d...dbdd85).

## What I will compute with MY OWN code (not the designer's scripts, not score())
- M1 own integer lane from the census arithmetic + image bytes, spot-checked tick-for-tick vs the golden model.
- M2 own linear 1 kHz inner-loop (lane linearised exactly as z-transfer functions; plant continuous + delay,
  discretised by my own state-space) -> Nyquist GM/PM/Ms AND discrete closed-loop eigenvalues (two methods).
- M3 own V282 linear lane (sum op, shl 5, C 46080, Kp 248, Kd 128) -> must reproduce |S/x|@20 Hz = 44.90.
- M4 own fork outer-loop linearisation from the fork source (read-only), per speed band, relay on/off, DF.
- M5 own nonlinear closed-loop sim (byte-exact lane + Karnopp plant + fork law) for scenarios; plus the harness's
  mode-B replay on r71b AFTER a spot check (lane tick vs golden model; one retrodiction row).

## FAIL criteria (any one => the named verdict)

### Reproduction (=> REFUTED if it fails)
- R1 Kp(idx) from my listing-style LERP on the candidate bytes differs from the designer's surface table at any
  of idx 3/6/18/34/50/75/92/100 by > 1 count of Kp, or the static T(idx) by > 2 T.
- R2 |P/x| at 20 Hz: V294 not 2.079 +-1 %, candidate not 2.703 +-1 %, V282 |S/x| not 44.90 +-1 % (my M3).
- R3 rail not +2461/-2463 or first rail idx != 239 on my own march.

### (a) Inner acceleration loop (=> REFUTED)
- A1 any member (identified family, light_b, J x0.5..x2.5, b/Fc corners, delay x1.5..x3 i.e. up to 18 ms incl.
  the 3 ms rate former, stress modes 13/20 Hz) is stable on V294 but unstable on the candidate (Kp 1248 = worst idx).
- A2 any closed-loop pole with zeta < 0.3 whose zeta falls below 0.9 x its V294 value (the same pole tracked).
- A3 Ms > 2.0 on any identified member, or Ms up by > 25 % vs V294 on any member incl. light_b.

### (b) 20 Hz against the on-car record (=> REFUTED if B1 or B2)
- B1 after calibrating a two-mass 20 Hz stress member so that MY V282 lane gives zeta ~0.016 from zeta_open 0.05
  (the record), the candidate lowers that mode's zeta by more than 0.005 absolute below open, or by more than
  1.5 x V294's own shift, at any transport delay 0..9 ms.
- B2 the sign of the candidate's damping contribution at 13-25 Hz differs from V294's for some delay in 0..9 ms
  AND is anti-damping (i.e. the candidate is anti-damping where V294 is damping). Same sign as V294 with |.| = 1.3x
  is expected and is NOT a fail by itself; it is reported.
- B3 (report, not fail) where the candidate sits in gain AND phase vs V282 and V294 at 13, 16, 20, 25 Hz.

### (c) Outer loop, fork law unchanged (=> REFUTED on C1/C2; SURVIVES_WITH_CHANGES on C3)
- C1 on any identified member at any band operating point: candidate Ms > 1.6 or GM < 3 (where V294 passes).
- C2 on light_b: candidate GM < 1.5 at any operating point, or an operating point where my linearisation shows the
  candidate's Ms higher than the designer's s12 number by > 15 % AND above 1.25 x V294's.
- C3 describing-function: a -1/N(A) intersection (predicted limit cycle) exists for the candidate at some band
  / idx operating point but not for V294, on any member.
- C4 low-speed-factor region (0-5 m/s): candidate GM < 3 on identified members.

### (d) Nonlinear traps (=> REFUTED on D1-D3, SURVIVES_WITH_CHANGES on D4-D5)
- D1 my nonlinear sim shows a sustained oscillation (limit cycle: a spectral line > +6 dB over V294 in 0.5-8 Hz
  persisting over the last 30 s) that V294 does not show, in any scenario (on-centre crown, hard-turn 8-20 m/s,
  dither around the idx 100 kink, command crossing idx 8).
- D2 P clamp binds on > 0.1 % of r71b hands-off engaged ticks with the candidate (V294 0.058 % all driver frames).
- D3 torque reversal: T(idx) non-monotone, or the kink at idx 100 (local-slope jump) produces a measurable jerk
  (T step discontinuity) > 2 x V294's per-frame torque step at the same command slew.
- D4 on-centre stick-slip breakaway rate > 3 x V294 at any speed on any identified member AND a spectral line.
- D5 parametric pumping from Kp(idx(t)) modulating the trim: an HF line (> 8 Hz) or 1-5 Hz line > +3 dB vs V294.

### (e) Direction across the family (=> SURVIVES_WITH_CHANGES if E1, REFUTED if E2)
- E1 any claimed direction (22+ tracking up, 15-22 tracking/hold up, 5-10 hard16 down, 15-22 hard16 not up
  > 10 %) reverses on any member of the family (incl. J_hi2, b_lo, F_hi, tau6, light_b) under lp or full.
- E2 the central claim (22+ tracking/hold +0.05) holds on the nominal member only.
- E3 (report) the cmd -> alpha direction at 0.3-1 / 1-3 / 3-8 Hz by member.

## What a PASS looks like
Every reproduction matches; no A/B/C/D fail fires; directions hold across the family. Then SURVIVES (possibly with
report-only caveats). If only C3/D4/D5/E1 fire, SURVIVES_WITH_CHANGES with the change named.
