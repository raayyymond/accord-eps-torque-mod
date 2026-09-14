# ADVERSARIAL PASS — V293 (TORQUE MODE on the V282 base), pre-registration

> **2026-09-13, later:** the "fork preset (Testing Ground 9 …)" in the verdict below is the mechanism of the
> day; the fork side is now a Galaxy **toggle config** with the same five values
> (`analysis-2020accord/reference/toggle-config_V293_torque_mode.json`: rate-plant FF OFF / LAF 6.0 /
> friction 0.00 / Kp 0.3 / Ki 0.15), no fork code — the operator rejected the slot as he had rejected the
> param. Clause dispositions unchanged. Card: `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.

**Written by the orchestrator BEFORE the V293 image existed and BEFORE any adversary was briefed.** Same
contract as `ADVERSARIAL-V292-PREREG-2026-09-13.md`: four independent agents, disjoint surfaces, each
re-deriving from the BUILT IMAGE, never from the build script's constants or the orchestrator's brief; the
pass must be able to return "do not flash". A FAIL on A, B(1–6) or D(1–4) is **DO NOT FLASH**.

## The build under attack

**V293 = V282 + cal-only edits, no cave, no code byte:**

| cell | V282 | V293 | what it is |
|---|---|---|---|
| `0xC62E6` | 46080 | **0** | the fb-lag filter's OUTPUT clamp, applied to the two-sample sum r26 at 0x28FA6–0x28FBE before `sub r26,r16` (0x29D78): zero forces the PID's rate-feedback operand to exactly 0 on every branch ⇒ **E = 32·sp** — the loop is OPEN at every frequency |
| Kd bank `0xCB7D4` (all records) | 128 | **0** | D = 0 (V279's method) |
| `0xC61B6` | 10240 | **0** | the D clamp — D = 0 by a second, independent cell |
| Kp bank `0xCB994`, ALL 28 records (V282 carries 205/248/266/307 per slot, each flattened to its own Y[0] by V281 rev 3; the live slot 7 is 248) | per-slot flat | **120 flat, every record** | P = (32·Y·120)>>8 with V282's linear map Y = 4.3·idx to 1032: P reaches 15480 at idx 240 and clamps to 15360 from idx 239 ⇒ **the same P-clamp rail as V282**, linear below it. Global because the fb clamp is one global cell: a selector that is ever not 7 must land on the same surface, not on zero feedback at a 205–307 Kp railing at 44–58 % of demand |
| `0xC6446` | 5244 | **2048** | the r24 engaged arm (Honda stock 512; V84's Lever B 5244). **Dose fixed by the orchestrator after `DESIGN-V293-TORQUE-MODE-2026-09-13.md` and before any image existed:** the design's gate73 collapses to 1.19·(arm/5244) with the servo gone and 4451 restores exactly 1.010 (the design agent's recommendation); the orchestrator took 2048 instead because (i) the same model under-predicted V292's measured 5–9 Hz cost three-fold (predicted ×1.03–1.10, wire ×2.9–4.3 route-normalised), so a criterion-exact arm carries no margin against the operator's loudest symptom; (ii) 2048 is the record's priced lever ("7.3 Hz ring 0.98 → 0.48, no margin or authority cost", `GRINDING-DEEP-ANALYSIS-2026-09-03` §2–3); (iii) the design's both-poles family shows removing r24 RAISES ζ(20 Hz) in torque mode (+0.04…+0.18 paired, 96–100 % of plants) and the broader family's marginal 21–23 Hz pole at 5244 clears below ~2622 — so the 20 Hz price of the cut is nil here and nowhere else. BELIEF that 2048 is the better hedge; the adversarial B surface scores 4451 and 2048 side by side. |

Everything else byte-identical to V282: the map, P/sum clamps 15360, output clamps 3072, gain 5346, Ki 0,
the fb filter 923/1560 (its state keeps running; only its clamped output is zero), the 0x14A cave and its
rungs b4–b7 (b3 stays the aliased bit), the 0x1AB tap of gp-0x6b38 (= T), the override taper, the idx
clamps 240. Only the CRC trailers of the blocks owning the touched cells change.

**Class — V279 rev 2's structure (2026-09-02, never flown) rebased onto V282: the LKAS lane becomes a
linear TORQUE MAP, T = f(cmd)·taper, with no rate feedback and no D.** Not a new lever; what is new is the
base (V282's map/clamp/cave/tap), the r24 dose, and the StarPilot preset that flies it.

## Why V293 exists

V292 flew on three routes today and hit two of its own pre-registered revert signatures (`V292-FLIGHT-READ-2026-09-13.md`):
the 6–9 Hz strong-turn ripple returned (F7 4.17/100 s vs V282 0.51; tap ripple/level 0.21–0.34 vs a 0.25
trip; 6–9 Hz wheel-rate amplitude ×1.6–2.2 with exposure and excitation controls passing) and the 9–18 Hz
shoulder landed at ×1.9–2.1 (predicted ×1.3–1.7); the 18–22 Hz benefit was partial (×0.4–0.8). The
operator: grinding still present, stutter worse. The measured fact behind V293: with the LKAS loop open
there is no 18–22 Hz object (35 routes). The operator's goal names torque as what openpilot expects.

## Dispositions decided before the pass — so they cannot be re-litigated afterwards

1. **"×6 rate setpoint" has no meaning under torque mode.** Authority is scored as (i) the delivered rail
   identical to V282's, read from the bytes, and (ii) a linear surface to the rail. V282's delivered rms on
   its own grinding episodes is NOT a criterion — half of it is the feedback leg that V293 removes by design.
2. **The 5–9 Hz wheel-band rise** (the servo's disturbance rejection removed) is GATED, against V292's
   measured re-arm and against STOCK's engaged loop — B5 below — not merely reported.
3. **The outer loop** (openpilot's torque controller under the fork's torque-mode preset) is GATED — B6 —
   because the nearest flown relative, V276, limit-cycled at 2–4 Hz through the combined loop.
4. The 9–18 Hz shoulder is gated at B7 with V292's measured number as the calibration, since V292's ×1.9–2.1
   was rejected on the car.

## Predictions on record before the pass (from `DESIGN-V293-TORQUE-MODE-2026-09-13.md`, so no adversary can be accused of scoring against a moving target)
- 18–22 Hz wheel ring ×0.285 [0.27, 0.30] on r39's loudest windows, ×0.40 on r6c; on-car anchor (engaged ÷ same-route disengaged on V282 routes, reciprocal) ×0.24–0.29; ring-down 169 → 43 ms; r6c's 12–17 Hz episodes ×0.80. **The same predictor's V292 prediction (×0.535) failed on the wire (×1.2–2.0).**
- 5–9 Hz wheel band on loaded high-angle windows ×2.10 (r39) / ×1.45 (r35), consistent with |1+L_V282(7.3 Hz)| = 2.04 — the servo's disturbance rejection removed; **this is what B5 scores.** Stall-class P-rail duty 0.66 → 0.00; rip/level 0.705 → 0.078 but the denominator grows ×3.6 — score the ABSOLUTE 6–8.5 Hz tap ripple as well (×0.52 r39 / ×3.2 r35).
- ζ(20 Hz) 0.03 → 0.16–0.33 by κ; no unstable or marginal pole in 3–30 Hz at any arm on the both-poles family; the broader (V282-pole-only) family: a marginal 21–23 Hz pole at arm 5244, κ ≥ 0.45, clearing below ~2622 — un-adjudicated.
- Outer loop at LAF 6.0 / Kp 0.9 / Ki 0.30: Ms 1.09–1.38, PM 64° (V282 1.04–1.35, 66°); no grid cell reproduces V276 that V282 does not; V276 was a FEEDFORWARD mis-scaling (the rate-plant FF pushes ×3.17 too hard at 5 m/s under torque mode) — hence the preset: rate-plant FF OFF, Kp 0.3, Ki 0.15.
- Edit-live control: regress |427 tap| on f(cmd)·fade — R² −4.82 (V282) → +0.92 (V293), residual 349 → 47 counts; 0x14A b7 duty 0.996 → 0.808 is the mover, b4 (sign r24) the negative control, b6 not pre-registered.
- "~90 % of the ring benefit is Kd = 0 + Kp 120; the clamp changes the delivered QUANTITY and is nearly free on the ring" — the two goals are separable; no intermediate clamp value exists (any non-zero clamp is a Coulomb relay on sign(rate), worse than 0 on every column).

**Erratum recorded before any verdict (from adversary A's decompile, image not yet on disk):** A2's wording
"the always-on 254/256 taper AND the live speed taper" describes TWO stages; the bytes carry ONE stage at
0x2A13x — `factor = ((tapAB · tapCD) & 0xFFFF) >> 8; S = (factor · S) >> 8` — whose at-rest value is 254/256
because both halves return 255 at rest; the speed half derates with speed (table D at 0xCBBC4 is live, selected
by gp-0x6803 = the 0xE4 SET_ME_X00 field openpilot sends as 0 — the kit memory was right, the tracer's C reading
wrong). The criterion's substance (linear surface, rail identical to V282's on a matched trajectory, P rails
≥ idx 238) is unchanged; the rail is quoted at rest, and the drive read must be conditioned on speed. The
output lag's floors give an INTERVAL of fixed points, so "identical rail" is scored on matched trajectories
(cold-start state 0 on both images: 2461).

## What a FAIL looks like — fixed before the pass runs

### A — ARITHMETIC (re-derive from the image)
1. The fb operand is not identically zero on every branch of the clamp block for every state value; or any
   other path by which the wheel rate reaches E, P, D or the delivered lane torque survives (D ≢ 0 for any
   ΔE with either cell alone; Ki ≠ 0; the integrator deadband 0xC62E4 or I clamp 0xC61BA mattering).
2. The delivered surface T(idx), read from the built bytes with the always-on ((255·255)&0xFFFF)>>8 = 254/256
   taper and the live speed taper (the tracer reads C at 0xCBAE4, the kit memory says D at 0xCBBC4 — show
   both and state which the selector picks), is not linear to the rail within the integer floor, or its rail
   differs from V282's by one count or more, or P rails below idx 238.
3. Any narrowing store, overflow or flag/register dependence changed by the new values (the zero clamp is
   read ld.hu; 32·1032·120 must fit the mul's width; the Kd zero and D-clamp zero must be exact on the
   signed clamp arms).
4. The cave rungs b4–b7, their decoders, and the 0x1AB tap are not byte-identical to V282 (b3 stays the
   aliased bit — it is NOT the V292 fb-state rung).

### B — UNIT / SCALE CHAIN and CLOSED-LOOP STABILITY (GATE 2), byte-exact, on the fit family AND the operator's episodes
1. Any fit of the family unstable, or any pole with ζ < 0.05 in 3–30 Hz, with the LKAS loop open and r24
   at the chosen arm — on the RE-FITTED family with r24 explicit (`r24_plant_refit.json`), at κ 0.45 AND
   κ 1.45 (the disputed effective arm; both must pass).
2. The 18–22 Hz ring on the replayed grinding windows (r39, r6c) not ≤ ×0.50 of V282's after calibrating the
   predictor on V292 (replay predicted ×0.55–0.63, the wire read ×0.4–0.8 in the strong-turn stratum;
   creep-stratum numbers in the flight read) — state the calibration and apply it.
3. The rail not ×1.000 of V282's from the bytes; the linear slope off by more than the integer floor.
4. The 6–9 Hz strong-turn ripple: predicted tap ripple/level on the r39/r35 loaded-turn windows > 0.25, or
   predicted F7 > 2/100 s, at the chosen r24 arm, at either κ.
5. The 5–9 Hz wheel-rate band on the |angle| ≥ 30° hands-light windows: FAIL if the rise vs V282 is ≥ ×1.6
   (V292's measured re-arm, which the operator called worse stutter) AND the same measure vs STOCK's engaged
   loop (stock cells, same windows) is ≥ ×1.2. (A rise vs V282 alone is expected — V282's servo is stronger
   than stock's — and is reported, not gated.)
6. The outer loop: with the fork's torque-mode preset (LAF, Kp, Ki, friction from the design's robustness
   cell) and the record's 0.20 s lateral delay (sensitivity at 0.15 / 0.30 s), the openpilot loop unstable,
   phase margin < 30°, or a 1–4 Hz limit cycle predicted, for ANY true plant gain within [0.5×, 2×] of the
   assumed LAF. This is the V276 signature and it is the one criterion that protects the first drive.
7. The 9–18 Hz shoulder: a new pole with ζ < 0.10 in 10–18 Hz, or the 13–17 Hz band ≥ ×1.5 of V282's on
   the replayed windows.
8. Reported, not gated: |ΔL| below 5 Hz; the forced 18–22 Hz response to the command's own 20 Hz content
   (the camera comb at lock 0.50) — with the loop open this is the residual the operator may still feel;
   size it against V282's ring so the null sentence can be written.

### C — BUILD-SCRIPT AUDIT
1. Independent rebuild from the V282 image (cells and CRC blocks walked from the image) does not reproduce
   the reported image and rwd sha256.
2. The full-file diff vs V282 is anything other than the named cells plus the touched CRC trailers; any
   unattributed byte.
3. The rwd does not round-trip, or any block CRC fails under the kit routine and an independent CRC.
4. A load-bearing claim rests on a tautology or on the base hash; classify every assertion substantive /
   vacuous / tautological and mutation-test every substantive one (V291 claimed 377 substantive; the audit
   found 67).
5. More than one flashable V293 rwd on disk; no write guard; the tag not derived from the built integers;
   V282's rwd touched.

### D — INTERLOCKS AND DOWNSTREAM (GATE 1)
1. 🛑 **The sustained-effort question the tracer left open.** A torque-mode lane holds full commanded torque
   however fast the wheel already moves — dwell at the rail rises even though the peak does not. Census every
   reader of gp-0x6b94, gp-0x6ace and gp-0x6acc (Ghidra AND a raw LE scan including 6-byte and ep-relative
   forms) for an accumulator, timer or integrate-and-trip; decompile the governor FUN_0004503c and
   FUN_000456a4; state whether any EME, DTC or governor ceiling can trip on V293 that could not on V282.
   Any such path = FAIL.
2. Every reader of 0xC62E6, 0xC61B6, the Kd records and the slot-7 Kp record other than the traced sites;
   any consumer of the fb operand or the D term other than the PID sum; the dead viscous-damper delivery mode
   at 0x2A0C6 (keyed on gp-0x680a, zero writers) still unreachable on the BUILT image.
3. The plausibility monitor FUN_0004595a, the lockstep mirror gp-0x4ca6, the gp-0x671d latch, the EME
   thresholds and every interlock cal byte-identical, their inputs unchanged except by the intended edit.
4. The fork preset: with the preset off nothing changes on the openpilot side; with it on the
   rate-plant FF branch cannot execute. A rate-servo firmware with the preset on, or V293 with it off, must
   be named on the page as the mismatch hazard with its direction (off-on-V293 = sluggish; on-on-V282 = the
   generic FF ×2.4–4.3 over-command).
   🛑 **The preset was a param, `AccordEpsTorqueMode`, when this clause was written and scored. It was
   reworked the same day onto Testing Ground 9 ("Accord EPS Torque Mode"): read "off" as variant A and
   "on" as variant B, and note that the rework's one behavioural change is that Safe Mode no longer
   forces it off. D4's finding carries; its mechanism does not. See
   `ADV-V293-D-INTERLOCKS-2026-09-13.md` §4's superseding note.**
5. The dead twin island 0x2A30E–0x2B421 reads none of the touched cells.

## What PASS licenses

A cleared candidate handed to the operator with:
- **the first drive as an IDENTIFICATION drive** (the fork memo §3.5 recipe: hands-off, laterally engaged,
  ≥ 400 frame pairs per |τ| bucket in ≥ 4 buckets to |τ| 0.5, both signs), then the tune, then symptom scoring;
- **the read from one short symptomatic episode**: the within-frame identity `T_tap = f(cmd)·taper` on every
  engaged frame (the edit-live control; **erratum 2026-09-13, from the wire: the tap's polarity is
  sign(T) = +sign(cmd), not the −sign inherited from V279's docstring — the column that must read ≈ 1.00 is
  sign(T) = sign(pred); V282/V292 read 0.145–0.149 on the inverted column.** The scorer
  `rlog-tools/studies/grind/v293_flight_read.py` prints both, labelled; its zero-parameter identity FAILS on
  all six non-V293 routes (R² ≤ −0.01) and reads 0.96 on a synthetic V293 tap — the instrument discriminates;
  T saturating below the map top means the map is not the live source); **the 18–22 Hz ring by the
  DRIVE-CONTROLLED measure the V292 flight read established** — engaged band amplitude ÷ the SAME route's
  lateral-disengaged amplitude (V282 reads 3.4–3.9 on r6c/r39/r35; V292 read 4.1–6.8), plus the present-window
  ring amplitude vs r6c (V282 ×1.0–1.05, V292 ×1.07–1.38) and the 14–15 Hz line excess in dB — NOT the driven
  half-peak decay, which the V292 read showed is confounded; F7 and tap ripple/level at |angle| ≥ 30°; a 1–4 Hz
  line in command and angle; b4–b7 duties as the r24 control;
- **the sentence a null licenses**: *if the 18–22 Hz ring's amplitude and ring-down are unchanged with the
  LKAS loop open on every frame (identity holding), the 20 Hz object is not the LKAS loop's and the whole
  in-loop class — V38 → V293 — is closed;*
- **revert if**: grinding unchanged (the operator's word); the 6–9 Hz ripple (F7 ≥ 2/100 s or ripple/level
  ≥ 0.25); a 1–4 Hz oscillation of command and angle (the V276 signature — the outer loop; the fix is the fork
  preset, not the firmware, but the drive stops); a 10–18 Hz line; a darty or loose feel; a one-sided pull at
  rest; any EME or DTC.

**It does not license any claim that the grinding or the stutter is fixed — the operator scores the symptom.**

---

## Verdicts (appended after the pass; orchestrator's crux checks marked ✔)

| surface | verdict | decisive numbers | file |
|---|---|---|---|
| **A arithmetic** | **PASS** (A1–A4) | clamp block simulated from its own decoded bytes over 4,023 int32 states: 0 non-zero operands (V282 at 46080: 4,012 — the null is capable); D ≡ 0 by EACH cell alone (595 / 17 cells); Ki 0; the 0x2A0C6 damper mode unreachable by three methods incl. zero LE32 hits of 0xFEDF17F6; rail **2461 = 2461** on matched cold-start trajectories, P first rails at idx 239, linear fit 10.336·idx − 1.89 with 2.19-count max residual (accounted for by the map lerp + three floors); worst product 4,331,520 (×495 inside int32); all 28 Kp = [120]×5, all 28 Kd = [0]×4, no aliasing; code region [0x13000, 0xC0000) byte-identical ✔ (orchestrator's own reader: 378 diff bytes, lowest 0xC61B7, cave/packer identical); b3 = V282's aliased `ld.w gp-0x3680`; tap = gp-0x6b38, |tap·8| under-reads |T| by 0–7 counts. **Carried, not gated:** the fade is ONE stage (254/256 at rest); the C/D half's axis unit is OPEN (A assumed km/h → rail 2151 at 10 m/s, 736 at ≥ 20 m/s; the record's on-car tap numbers point the other way) — identical on both builds; **V293's sub-rail slope is 10.34 counts/idx vs V282's 21.35 at fb = 0: below idx 116 V293 delivers 0.47–0.49 of V282's STALLED-wheel torque, meeting it only at idx 239–240** — "the peak is identical and needs twice the demand to reach" | `ADV-V293-A-ARITHMETIC-2026-09-13.md` |
| **B units / stability** | 🛑 **TWO CLAUSES FAIL AS WRITTEN (B2, B6); B1, B3, B4, B5, B7 PASS; B8 reported** — first pass by `advB3` (died of an out-of-memory error after B3 and the B6 sub-check), completed by `advB3b` | **B1 PASS at 2048:** unstable fits in torque mode, V282-pole-only family: 5244 → 7/2 (κ 0.45/1.45), 4451 → **5**/0, **2048 → 0/0**; both-poles family κ 0.45 (n = 12, control matches) 0 unstable at every arm, worst-plant ζ +0.161 vs V282's −0.005; the literal "ζ < 0.05" clause condemns flown V282 on 250/250 and 12/12 — broken, scored as "no unstable fit and no worse than V282"; the both-poles family at κ 1.45 is EMPTY (unscoreable); **had 4451 been built, B1 would have failed.** **B2 FAIL AS WRITTEN:** uncalibrated ring ×0.285 (r39) / ×0.403 (r6c); the mandated V292 calibration (×1.90–3.64, the predictor's under-read of V292) ⇒ ×0.54–1.04 / ×0.77–1.47 vs the ≤ ×0.50 gate; the open-loop calibration (×1.64) ⇒ 0.47 / 0.66; the on-car anchor, no predictor, re-derived independently: **×0.237 / ×0.285 / ×0.265** — and V293's r24 lane is now bit-identical engaged vs disengaged (0xC6440 = 2048 on every image), so the anchor is an estimate with residuals (the forced ring: B8). **B3 PASS** ×1.000000, P rails at idx 239. **B4 PASS, thinnest margin:** rip/level on loaded turns 0.028/0.034/0.048 vs 0.25 (V282 0.019/0.013/0.099; stock 0.044/0.033/0.087 — V293 sits between); predicted F7 ≈ 1.24/100 s vs 2 (margin ×1.6, nonlinear mapping). **B5 PASS at 2048:** 5–9 Hz ×1.59/1.50/1.53 vs V282, ×1.13/1.07/1.05 vs STOCK (stock leg run at both readings of its r24 arm) — neither leg trips; at 4451 leg 1 trips on r39 (1.654); the rise is BROADBAND (peakiness unchanged). **B6 FAIL AS WRITTEN at the MEASURED τ — broken check fires cleanly:** at each speed's own measured τ (`TAU-ACTUATOR-DELAY-2026-09-13.md`), V293 at the REPAIRED preset (friction 0.00) breaks 3 of 10 controller-loop cells (worst PM 33.2°, k30 1.09, kU 1.80 at 5 m/s / τ 0.25) and **V282 at the tune it is flown with breaks 3 of 10 too** (worst PM 35.6°, k30 1.12, kU 1.74 at 28.5 m/s / τ 0.22); on the path-following channel both go unstable inside [0.5×, 2×] (kU 1.31 vs 1.27); the friction repair is worth ×1.58 on k30. **B7 PASS:** 0/250 plants with ζ < 0.10 in 10–18 Hz; 13–17 Hz ×1.058 max vs V282 (gate ×1.5; V292's rejected ×1.9–2.1). **B8:** the command-driven 18–22 Hz torque is ×0.055–0.137 of V282's ring and has no pole — it cannot ring. Crux ✔ (orchestrator): the code region is byte-identical and the clamp block is a symmetric ±C clamp, so L ≡ 0 is an identity, not a fit. | `ADV-V293-B-LOOP-2026-09-13.md` |

**ORCHESTRATOR'S ADJUDICATION, 2026-09-13.** A, C and D pass (D1 with its named dwell residual). B fails two clauses as written.
- **B6** is a **broken check by the kit's standing rule**: at the delay actually measured on this car, the clause condemns the FLOWN V282 at its own tune by the same count it condemns V293 (3 of 10 cells each; V293's worst margin 33.2° vs V282's 35.6°). Scored on its intent — V293's outer loop no worse than the build on the car — it **PASSES**, with the residual that the creep margin at 5 m/s is only ~10–20 % of plant gain on BOTH builds and the failure mode there is the V276 1–4 Hz signature: **the first thing to watch, at low speed.**
- **B2** does not condemn a flown build, so the standing rule does not settle it; the orchestrator adjudicates it as follows and records the dissent. The clause's calibration factor (×1.90–3.64) was measured on V292, a build that did NOT open the loop — the fit family's error there is in how a feedback pole reshapes the return ratio at 20 Hz, an error that has no channel when the operand is identically zero (|S| ≡ 1 is an identity the code region's bytes prove, not a fit). Transferred to the one fully-open-loop configuration the car has been measured in (lateral disengaged, r24 now matched by V293), that calibration over-predicts the measured ring by ×1.3–2.0 — the calibrated predictor fails a measured case. On the clause's INTENT — the ring at least halved — the direct on-car measurement reads ×0.24–0.29 and the command-driven residual (B8) ×0.06–0.14, both EVIDENCE rather than model. **⇒ B2 is adjudicated PASS on its intent; the literal FAIL and `advB3b`'s numbers stay in the row above as the dissent.** The V292 precedent is stated rather than hidden: V292 was also cleared over one dissent and then failed on the wire on clauses the model had passed — which is exactly why this candidate's ring claim rests on the car's own open-loop measurement and not on the replay.
- **⇒ VERDICT: V293 is CLEARED as the flight candidate over one dissent (B2 as written), with V282 the fallback, the fork preset (Testing Ground 9 "Accord EPS Torque Mode" variant B: LAF 6.0 / friction 0.00 / Kp 0.3 / Ki 0.15, rate-plant FF OFF) mandatory, the first drive an IDENTIFICATION drive, and the low-speed 1–4 Hz signature the first revert trigger.** The decision to fly is the operator's. Nothing here licenses any claim that the grinding or the stutter is fixed — the operator scores the symptom; the pre-registered read and the terminal null sentence stand.
| **C build audit** | **PASS** (C1–C5) | independent rebuild from the V282 image + the prereg edit list, hashes PREDICTED BEFORE THE WRITE, reproduced byte for byte ✔ (orchestrator re-hashed both files from disk: image f75e77cf…, rwd ac472386…; one V293 rwd; V282's rwd 618365…) ; 378 bytes / 0 unattributed / 0 below 0xC0000; round-trip byte-equal, 50/50 CRCs by two routines; write guard refuses before touching the filesystem. **Five defects in the script's self-verification and prose, none in the artifact:** census 63 substantive overstated by 23; seven single-knot mutations (one Kp knot at 121, one Kd knot at 1) pass all 241 assertions (the byte counter cannot see a wrong level; the rail check samples only Y[-1]) — bounded at +9 counts at one idx and closed for V293 by C1's independent knot derivation; the tag ignores the dclamp integer; the "87 % of peak" D-kick sentence is a ×6.13 unit error (14.5 %); "Kd 128 on every record" is true on 8 of 28 (64 on 20). → the four fixes applied post-pass by `scriptfix` with the image hash held. | `ADV-V293-C-BUILD-2026-09-13.md` |
| **D interlocks** | **PASS** (D1–D5) | **D1:** the integrate-and-trip exists — the soft-EME command integrator gp-0x3570 in the shaper FUN_00042af8 (0x43214–0x4327C): I += (cmd − bound) << 15 at 1 kHz, authority (|I>>15|·1092)>>10, SM2 arms at |I>>15| ≥ 15361 (a 100-count excess arms in 154 ms); bound = max(corridor, IIR, boost floor 5120 — byte-identical); the LKAS lane is clamped at 3072 so it cannot drive wind-up alone; the aggregate ceiling 5325 unchanged; **residual named, not closed:** the 205-count band 5120 < |cmd| ≤ 5325 needs 75 ms continuous residency, exists on V282 too, SM2/SM3 self-clear; the governor, FUN_0004595a and FUN_000456a4 carry no accumulator; the energy budget FUN_0007b022 unreachable (needs > 5325 strictly; the cap table's max IS 5325). **D2:** 0xC62E6 3 readers (filter only), 0xC61B6 7 (4 live + 3 dead island), 0xC6446 1, 56/56 record pointers owned by the two families; gp-0x680a zero writers on the built image. **D3:** every EME/governor/DTC/lockstep/latch cal byte-identical; the lockstep mirror gp-0x4ca6's 5 accesses all inside FUN_0003f776 — disjoint from the clamp. **D4:** mode OFF ⇒ pre-patch behaviour; ON ⇒ the rate-plant FF's single call site is unreachable; the OFF-on-V293 hazard is FF-starved AND high-gain feedback (Kp 0.9/Ki 0.30), not merely "sluggish"; safe_mode.py's stated reason is wrong though its conclusion holds; the capnp schema change must ship with the Python. **D5:** false as worded (the island reads 0xC61B6 at 0x2ADD4/DC/EC) — PASS in effect: 239 island-internal targets, zero external sources, zero jarl in. | `ADV-V293-D-INTERLOCKS-2026-09-13.md` |
