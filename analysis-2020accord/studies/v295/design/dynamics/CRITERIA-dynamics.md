# CRITERIA — V295 design, lens "dynamics" (phase / lag of the command -> torque -> acceleration path)

Subagent `dynamics`, 2026-09-30 10:40 PDT. **Written BEFORE any candidate number was computed** (only the census,
harness, plant, metric, attribution and bands reports had been read; the harness had not yet been run by me).
Design only: nothing built, flashed, sent or committed.

## Knob families in this lens (all cal-only)
- **L** output lag pair `lag_a` 0xC63EC / `lag_b` 0xC63EE (5.05 Hz as built, never changed on 272 images).
  `lag_b` is re-held so the DC gain b/(16(1024-a)) does not exceed V294's 507/512 (the rail must not rise).
- **D** the Kd bank 0xCB7D4 (4 knots, flat — unschedulable above idx 32) + D clamp 0xC61B6, with the sum clamp
  0xC61BE lowered to 15240 if needed to hold the rail (I/D live otherwise lifts it 2461 -> 2481).
- **A** the fb pole `fb_a` 0xC63E8 as a phase knob: (i) `fb_b` held (HF trim gain unchanged), (ii) K_alpha held.

## Per-candidate measures (always as a DIFFERENCE from V294 in the same batch)
- M1 cmd -> T phase and equivalent delay at 1, 2, 3, 5, 8 Hz (linear 1 kHz, `ff_tf`), incl. the 100 Hz ZOH.
- M2 closed-form cmd -> alpha phase and |G| at 0.3-8 Hz on nominal, light_b, J_hi, b_lo (`alpha_per_cmd`).
- M3 fork outer loop (`outer_frf`, r1): Ms, PM_min, GM_min at 5/8/12/17/26.9 m/s on nominal, light_b, b_lo, J_hi,
  tau6 AND the stress members mode13 / mode20 / mode20_lo (the echo loop through the fork's P at 10-25 Hz).
- M4 trim opposing torque T/omega: damping component (|.|cos) at 2, 2.5, 3, 4, 5 Hz and at 13, 17, 20, 25 Hz.
- M5 HF: |T/x| 5-30 Hz vs V294 and V282; delivered 5-30 Hz torque under the recorded command (mode A full, mode B
  lp/full); the staircase response; sensor-noise torque (x white 1.93 counts, sp 0); the 100 Hz ripple (>30 Hz rms).
- M6 stress-mode damping (mode13, mode20, mode20_lo at 5/12/25 m/s) vs V294 and open.
- M7 mode B drive metrics on nominal and light_b under full AND lp: tracking gain, turn-hold, straight delivery,
  integrator share, r_mid (1-3 Hz rate), hard-turn 1.6-3 Hz, J_err, the 1-5 Hz limit-cycle line. Dwells not used.
- M8 M_SAFE: rail +/-, sub-rail slope, int32 margins, b/b_max, trim cap, restart pulse.
- M9 attributability: a synthetic flight — the candidate's byte-exact march on r71b's own command and rate, sampled
  and quantised like the 427 tap (50 Hz, 8 counts) plus the real tap's residual noise — must be separated from V294 by a
  pre-registered regression in <= 30 s of hands-off engaged frames.

## FAIL — a candidate that meets ANY of these is not recommendable
- F1 rail above 2461 on either sign, or sub-rail slope changed by more than 0.5 % (this lens moves phase, not static gain).
- F2 any `problems()` entry; any int32 margin < 2; b > b_max.
- F3 |T/x| at any of 9-30 Hz > 3.0x V294's (design rule 3), or |P(+D)/x| at 20 Hz > 3 x 2.079 = 6.24.
- F4 any stress member's least-damped 8-40 Hz closed-loop mode with zeta < 0.9 x V294's at 5/12/25 m/s, or any
  M_LOOP member/speed unstable, or inner GM_min < 6 anywhere (V294 minimum 16.3).
- F5 delivered torque (mode A full, and mode B lp) in any 9-30 Hz band > 2.0x V294's on nominal, light_b or any stress
  member. 1.3-2.0x is a RISK that must carry a margin argument against the on-car record (V282 ground at 44.90
  P-counts per x-count at 20 Hz; V294 clean at 2.079).
- F6 fork outer loop: on any plant/speed of M3, GM_min falls > 10 % below V294's or Ms rises > 10 % above V294's.
- F7 mode B: tracking gain or turn-hold falls by > 0.02 in any band (nominal or light_b, full or lp); r_mid or
  hard-turn 1.6-3 Hz rises by > 10 % in any band (same grid).
- F8 attributability: the synthetic-flight regression separates the candidate from V294 by < 3 SE in 30 s of
  hands-off engaged frames, OR the real r71b tap (a V294 flight) reads the candidate's coefficient as != 0 beyond 3 SE
  (the null control fails).

## Lens-level "NO CHANGE" sentence (the pass must be able to return it)
If no candidate passes F1-F8, OR if the best passing candidate moves NONE of:
  (a) cmd -> alpha phase by >= 5 deg at 2 Hz on nominal, (b) outer-loop GM_min on light_b at 17-27 m/s by >= +5 %,
  (c) mode-B hard-turn 1.6-3 Hz or r_mid by >= 3 % (either direction counted only if favourable on BOTH nominal and
  light_b under lp),
then this lens recommends **NO CHANGE**: the lever exists but is too small to spend the one short drive on.

## Pre-declared ceiling statements to be quantified (design rule 8)
- The output lag is ~31.5 ms of time constant; it is the only element of the cmd -> torque -> wheel -> fork round trip
  (~60 ms per the rev-4 record) that the firmware owns. The 20-22 ms pipeline, the 3 ms rate former, the 2 ms transport
  and the fork's own filters are out of reach.
- Phase moves at 1-8 Hz cannot change DC tracking gain / turn-hold (the 'loose / understeer' complaints) except through
  the outer loop's dynamics; a null there is expected and is not a failure of the lens.
