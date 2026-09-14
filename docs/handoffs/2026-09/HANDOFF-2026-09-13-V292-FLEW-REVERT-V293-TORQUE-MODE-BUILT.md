# HANDOFF 2026-09-13 (late) — V292 FLEW and is a REVERT; V293, TORQUE MODE, is BUILT and CLEARED over one dissent

> 🛑 **SUPERSEDED IN ONE RESPECT, later on 2026-09-13 — the fork side.** Every "Testing Ground 9 / variant B"
> statement below is history: the operator rejected that mechanism too (*"way too complicated for what
> should just be a toggle config file"*), fork commit `3d1a3d0c7` was force-removed (Dom is `4247cb09e`,
> carrying only the SR-map refit, the frpc deletions and one `import math`), and **the fork side is a Galaxy
> toggle config** — `analysis-2020accord/reference/toggle-config_V293_torque_mode.json` (rate-plant FF off,
> Kp 0.3, Ki 0.15, friction 0.00, LAF 6.0), no fork code. `starpilotLateralState.epsTorqueMode` never
> shipped; the scorer attributes the drive from `initData.params` and the 100 Hz `torqueState.p/error`
> read instead (r6f: Kp 0.9000 exactly). The `ModelCurvatureLead` patch that the same commit had swept in
> was never part of V292 or V293 and is preserved as `docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.patch`.
> Safe Mode DOES reset the config (all ten keys are managed). Current card:
> `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`; current state: `docs/STATE.md`.

**Read `docs/STATE.md`'s decision box first.** This is the narrative of the second half of 2026-09-13:
the session that put V292 on the car, measured that it re-armed the 7 Hz mode and did **not** touch the
20 Hz ring, and then answered the operator's goal with **torque mode** — V279's structure rebased onto
V282 — instead of another shaping of the loop. **Nothing was flashed by us and nothing was sent on any
bus; the operator flashed and drove V292 himself.**

## 0. One paragraph

The operator's goal, set this session: **a new firmware plus StarPilot changes with V282's authority
(×6 torque, ×6 rate setpoint, no EMEs), no grinding and no stutter — with the LKAS PID tracking angular
acceleration (≈ torque, what openpilot expects), OR StarPilot outputting a rate target, and the StarPilot
tuning updated to match.** He flew V292 first. **It is a REVERT by its own pre-registration**: two revert
signatures fired (the 6–9 Hz strong-turn ripple returned at F7 4.17/100 s against V282's 0.51, and the
9–18 Hz shoulder landed at ×1.8–2.1 with a new 14.84 Hz line at +6.3 dB), the 18–22 Hz ring did **not**
fall (the loop's own contribution went **UP ×1.20–2.00** by the drive-controlled measure), and the phase
moved **opposite in sign** to its prediction. His words: *grinding still present, stuttering worse, most
visible as an oscillation when holding the wheel at a high angle.* **V292's own null sentence therefore
fired** — the object's damping is not set by the rate loop's return ratio — which made the next build a
question about **method**, not dose: every prediction the kit has made about the ring runs through a
fitted plant family, and the one out-of-sample test of that family just failed. **Torque mode is the
model-independent test**: with the feedback clamp at zero there is no loop at any frequency, so no fit
family stands between the edit and the answer. **V293** was designed, the r24 dose was ruled by the
orchestrator **against the design agent's recommendation**, its adversarial pre-registration was written
before the image existed, and the builder is writing the image. The other two readings of the goal were
grounded and **recorded rather than built**: acceleration tracking is **dominated** (it contains torque
mode and adds electronic inertia on top, and the inertia term needs a cave — the kit's only bricking
class), and a StarPilot rate target **cannot remove the grinding** (V288 rev 2 flew exactly that class,
the cave was live, the D-bind duty fell ×0.03 as designed, and the grinding was unchanged). The fork gets
**one selection** — Testing Ground 9 "Accord EPS Torque Mode" variant B — instead of four toggles the
operator had to keep consistent by hand.

> 🛑 **THE VERDICT: V293 is CLEARED as the flight candidate over ONE DISSENT (B2 as written), with V282
> the fallback, the fork TOGGLE CONFIG (`toggle-config_V293_torque_mode.json`: rate-plant FF OFF /
> LAF 6.0 / friction 0.00 / Kp 0.3 / Ki 0.15 — existing sliders, no fork code) MANDATORY, the first drive an IDENTIFICATION drive, and the low-speed 1–4 Hz
> signature the first revert trigger. The decision to fly is the operator's. Nothing licenses any claim
> that the grinding or the stutter is fixed — he scores the symptom; the pre-registered read and the
> terminal null sentence stand.**

**Two of B's eight clauses failed as written and both were adjudicated.** **B6** by the kit's standing
broken-check rule: at the delay actually measured on this car it condemns the **FLOWN** V282 at its own
tune by the same count it condemns V293 (3 of 10 cells each; 35.6° vs 33.2° worst). **B2** could not be
settled that way — it condemns no flown build — so it was adjudicated on its intent, and **the dissent is
recorded rather than dissolved**: its calibration factor was measured on V292, a build that did **not**
open the loop, and transferred to the one fully-open-loop configuration the car has been measured in it
**over-predicts the measured ring by ×1.3–2.0**. 🛑 **The precedent is stated on the page: V292 was ALSO
cleared over one dissent and then failed on the wire on clauses the model had passed.**

## 1. How the session ran

Orchestrated. Opus for every substantive task, Sonnet for the trivial ones, **none on Fable** — the
operator's standing model policy. Nothing was built except the one image, on an explicit GO WRITE.

| agent | surface | outcome |
|---|---|---|
| `flightread` | attribute and read the three V292 routes | **V292 on all three, cave live** — and the prereg's b3 DUTY read **does not discriminate** (0.418–0.453 vs V282's 0.467); attribution came from the bit's *meaning* (b3 tracks `sign(rate)` at lag +1, split 0.642–0.764, four reference builds flat at every lag). **Two revert signatures FIRED; the ring did not fall; the phase moved the wrong way.** Built the drive-controlled ring measure (engaged ÷ same-route disengaged) that survives the driving-model change |
| `looptrace` | which quantity the LKAS PID actually tracks | **rate, not acceleration**, and acceleration tracking needs a cave. Pinned the feedback chain **sensor to error**; established that **the mute is `0xC62E6` ALONE** (`0xC63EA` only reaches an absorbing −1) and that `0xC61B6` is an **equivalent, independent D kill**. Four corrections of record from the bytes: the P/I register swap at `0x29F18`; `0x2A0C6` is a second (unreachable) delivery MODE, not a reset; the `gp-0x3d30`/`gp-0x3d2c` boot values are now **EVIDENCE** (both 0) from the `.data` copy loop; **the delivered rail is not 2481/2505** — it read 2462, since refined by the builder to **2461** (2462 is the linear DC). Left the C-vs-D speed-taper question **open** — the SELECTOR half has since been **closed against it** (adversary A: `gp-0x6803` picks B × **D**, so the kit memory was right and this agent's C reading was wrong), while the **axis-unit half is still open**. Left the **EME dwell census open** — the one clause that could return do-not-flash, and the one `advD3` then closed |
| `arc` | ground the three readings of the goal in the whole V38 → V292 record | **torque mode has been built exactly once (V279 rev 2) and was NEVER FLOWN — the class is never-tried, not falsified**; the nearest flown relative is **V276**, which limit-cycled at 2–4 Hz; *"×6 rate setpoint"* and *"torque mode"* are **not simultaneously satisfiable as written**; **`gate73` loses its servo arm entirely under torque mode**, which is what reopens the r24 question; the **Kp 119/120 arithmetic**; V56's "lane mute" is **not** evidence about the LKAS feedback (it muted a driver-torque PID) |
| `fork` | the fork's Accord lateral path, and two designs | **`AccordRatePlantFF` is already a measured inverse of the LKAS assist map** — the map's open-loop scale 141.4 deg/s per unit torque vs the fork's identified `G(v)` 120 → 70, i.e. 0.85× at 5 m/s and 0.49× at 28.5 m/s. Designs A and B written out; **live toggles read from the wire**, not from the code defaults; 🛑 **the panda applies NO limit to `0xE4`** — no magnitude, rate, driver-torque or RT window; `torqued` now reads `liveValid` **1** with `latAccelFactorRaw` 6.24 on route 6f and the record's toggle ceilings are stale. **Recommended Design B first, with the counter-argument recorded** rather than argued away. Fork HEAD had already moved past the brief's commit (`305732c85` → `a357cd2b5`) — flagged, nothing touched |
| `tmdesign` | design and price torque mode on the V282 base | The design doc plus **11 analysis scripts**. Ring **×0.285** on r39's loudest windows, **×0.40** on r6c, on-car anchor **×0.24–0.29**; **ζ(20 Hz) 0.03 → 0.16–0.33**; **the price is 5–9 Hz ×1.8** (×1.74–1.85 broadband, ×2.10 on loaded high-angle windows); **`gate73` = 1.19·k, so 4451 is the exact restore — the orchestrator took 2048**; ⭐ **in torque mode the r24 cut is FREE at 20 Hz** (removing r24 RAISES ζ once the servo is gone); ⭐ **~90 % of the ring benefit is Kd = 0 + the Kp re-level, not the clamp**; 🛑 **no intermediate clamp dose exists**; **the outer loop is NOT the risk**; and it **declared its own predictor's one out-of-sample failure on V292** rather than burying it |
| `builder293` | the V293 script and image | Script with **presets + `--grid`**, a **zero-edit control**, a full **assertion census** and **16/16 mutations caught**; corrected the **taper record** on the way; built at **`KP_SCOPE = all`**. **image `f75e77cf…`, rwd `ac472386…`**, 378 diff bytes over 6 CRC blocks, 242 assertions. **The pre-registration's A2 clause settled Kp at 120, not 119** (119 delivers 2504, one count below the rail) |
| `forkpatch` | the one-switch preset | `AccordEpsTorqueMode` built in the fork as a PARAM, **UNCOMMITTED, OFF by default**: **+306/−4 across 10 files plus a 487-line test file, 25 new tests passing**, suite **306 passed / 303 prior / 3 newly unblocked** — the two Accord rate-plant tests were freed by a **one-line `import math`**. `epsTorqueMode` published in `starpilotLateralState` so the mode is readable from cereal rather than from the params blob. Provisional four-number tune in one place; the checklist in `docs/guides/` encodes the **asymmetric** mismatch hazard as a step order. 🛑 **SUPERSEDED by `forkrework` — see the row below** |
| `forkrework` | the same switch, reworked onto **Testing Ground 9** | 🛑 **The operator rejected a toggle whose only job is to apply a preset of other toggles.** The fork already had the right mechanism: Testing Grounds, A = installed tune, B = experiment. **All five params deleted** (`params_keys.h`, `starpilot_variables.py`, `SAFE_MODE_MANAGED_KEYS`, the Galaxy layout and its test); **new slot 9 "Accord EPS Torque Mode"**, gate `testing_ground.use("9","B")`; the four tune numbers become **constants, not sliders**; `epsTorqueMode @8` KEPT. Test file rewritten to the slot gate — **26 tests, all passing**, including an end-to-end read of a real `slots.json` and a default-is-A safety test. **Two findings:** ⚠ **Safe Mode no longer forces the mode off** (it manages params; Testing Grounds are not params) and ⭐ **the selection IS logged**, as `customReserved9` on a 15 s heartbeat |
| `advC3` | build audit | ✅ **PASS.** Independent rebuild **byte-identical**. Four non-blocking findings, all of the class this audit exists to catch: the substantive census (63) is **overstated by 23**; **seven single-knot mutations are invisible to the assertions**; the tag **does not encode the D-clamp integer** (two builds differing only in `0xC61B6` would share a tag); two docstring errors. 🛑 **None of the four is in the artifact** |
| `advD3` | interlocks and downstream | ✅ **D1 PASS, with the number that makes it one** — this was the clause most likely to return do-not-flash. Found the mechanism and bounded it: the **soft-EME integrator `gp-0x3570` in the shaper `FUN_00042af8`** arms **SM2 at `\|I>>15\| ≥ 15361`** on the excess of `\|cmd\|` over `max(corridor, IIR, boost floor 5120)`; ⭐ **the LKAS lane's rail ≈ 2481 cannot reach the bound at all**; the only newly opened band is **`5120 < \|cmd\| ≤ 5325` needing 75 ms CONTINUOUS residency**; SM2/SM3 self-clear; the energy budget `FUN_0007b022` is unreachable; every interlock cal byte-identical. ⚠ **D5's wording is FALSE but INERT** — the dead island *does* read `0xC61B6`, and it is uncalled |
| `advA3` | arithmetic | ✅ **PASS on A1–A4.** The clamp block simulated from its own decoded bytes over **4,023 int32 states gives ZERO non-zero operands**, against a **capable-null control of 4,012 for V282 at 46080**; `D ≡ 0` by **each cell alone**; the `0x2A0C6` damper mode **unreachable by three methods** including **zero LE32 hits of `0xFEDF17F6`**, which closes `looptrace`'s residual on it; **rail 2461 = 2461** on matched cold-start trajectories; **P first rails at idx 239**; linear fit **10.336·idx − 1.89** (max residual 2.19 counts, accounted for); worst product ×495 inside int32; code region byte-identical; b3 confirmed as V282's aliased `ld.w gp-0x3680`; the tap under-reads by 0–7 counts. 🛑🛑 **CARRIED, NOT GATED — and it changes the language: the sub-rail slope is 10.34 counts/idx vs V282's 21.35 at fb = 0**, so below idx 116 **V293 delivers 0.47–0.49 of V282's STALLED-WHEEL torque** (idx 58: 598 vs 1236), meeting it only at idx 239–240. *"The peak is identical and needs twice the demand to reach."* **Never write "authority unchanged" about V293, and never show only the rail** |
| `advB3` | unit-scale + GATE 2 (first pass, **DIED**) | 🛑 **B6: FAIL on the build + PRESET PAIR as shipped — and the firmware is NOT the defect.** PM **22.8°** at 5 m/s / κ 1.00 / τ 0.20 s (Ms 4.32, crossover 0.82 Hz), because StarPilot feeds **`error_with_lsf`** into `get_friction` where upstream feeds the **raw** error ⇒ compensator gain **`(friction/0.30)·(1 + lsf/kp)` = ×17.9** at Kp 0.3 and 5 m/s. ⭐ **A lower Kp is WORSE** (loop gain minimised near Kp ≈ 1.0), inverting the preset's own rationale. **Repair is fork-side: preset friction 0.01 → 0.00** ⇒ PM 42.2°, Ms 2.06, GM ×1.40. ⚠ Conditional on **τ ≥ 0.18 s**, and τ = 0.20 is the operator's `SteerDelay` toggle **echoed, not identified** (Honda port prior 0.10 s). ✅ **The 1–4 Hz V276 signature does not reproduce on frequency** (cycles at 1.21–1.25 Hz). ⚠ The clause's literal "[0.5×, 2×]" wording is **broken** (V282 fails it at 28.5 m/s κ 2) but **the FAIL does not rest on it** — κ 1.00, where V282 reads 40.1°. **B3 PASS** before it went: rail **×1.000000 by three methods**, slope **0.641212 counts/CAN count**, P clamp binds at **idx 239**. 🛑 **Then it DIED of an OUT-OF-MEMORY error mid-run.** Two record defects found on the way down: **(a) the module-default `B(f)` fit is BAD** (`nb=1, nd=4` → rms `ln\|B\|` 0.54, phase 38°, **a spurious UNSTABLE 4.5 Hz root**; use the design's `nb=1, nd=3`) and **(b) `r24_plant_refit.py` cannot regenerate `r24_plant_refit.json`** — `fit_B(nb=4, nd=2)` now raises on the properness guard, so **the prereg's own named reference family for B1 is not reproducible from its own script**. Also the **r24 arm correction**: `0xC6440` = 2048 is the **DISENGAGED** arm on every image including stock, so V293 sets engaged = disengaged. **The rest of B was completed by `advB3b` (next row)** |
| `advB3b` | B's replacement | ✅ **COMPLETED the B table.** ✅ **B1 PASS at r24 2048** — 0 unstable fits on every family and κ, where **4451 has 5 unstable** on the broad family at κ 0.45; the literal `ζ < 0.05` clause is **broken** (condemns flown V282 on 250/250 and 12/12) so it was scored as "no unstable fit and no worse than V282"; ⚠ **the both-poles family at κ 1.45 is EMPTY (n = 0)**, unscoreable. ✅ **B5 PASS at 2048** — 5–9 Hz **×1.50–1.59 vs V282**, **×1.05–1.13 vs STOCK**, under both thresholds, where **4451 trips the first leg on r39**; ⭐ **the rise is BROADBAND, peakiness unchanged**. ⭐⭐ **B1 and B5 together vindicate the 2048 ruling** — the BELIEF is now EVIDENCE on those two clauses. 🛑 **B2 FAIL AS PRE-REGISTERED** — the mandated V292 calibration (×1.90–3.64) on the replay's ×0.285/×0.403 gives **×0.54–1.47 against a ≤ ×0.50 gate**, while **the uncalibrated replay and the on-car anchor both PASS**; the same agent shows that calibration **over-predicts ×1.3–2.0** against the car's own measured open-loop configuration, and that **the anchor is usable at 18–22 Hz but not at 5–9 Hz, where it and the replay disagree in SIGN**. ⚠ **Adjudication is the orchestrator's, pending the full B table — not resolved here.** Also resolved the `0xC6440` question (below). **B4 PASS — the THINNEST margin in the pass**: ripple/level 0.028/0.034/0.048 vs a 0.25 gate (**stock reads 0.044/0.033/0.087, so V293 sits BETWEEN stock and V282**), predicted F7 ≈ 1.24/100 s vs 2, **×1.6 only, through a nonlinear mapping**. **B7 PASS** — 0/250 plants with ζ < 0.10 in 10–18 Hz, 13–17 Hz ×1.058 vs a ×1.5 gate. **B8** — the command-driven 18–22 Hz torque is **×0.055–0.137 of V282's ring and has NO POLE: it cannot ring**. 🛑 **B6 re-scored at the measured τ and the repaired preset: still FAIL AS WRITTEN, but a BROKEN CHECK that fires cleanly** — V293 breaks 3/10 controller-loop cells (worst PM **33.2°**) and **flown V282 at its own tune breaks 3/10 too** (worst **35.6°**); both unstable inside [0.5×, 2×] on the path-following channel; friction repair worth ×1.58 on k30 ⇒ **PASS on intent**, residual: **creep margin ~10–20 % of plant gain on BOTH builds** |
| `taumeasure` | identify τ from the rlogs | ✅ **Done, and it retires "τ = 0.20 s" as a number.** Measured `controlsState.desiredCurvature` → steering-angle curvature on **six routes** (zero-lag and 200 ms controls pass; **the `0xE4` → rate pair is UNUSABLE** — the rate-plant FF makes the wheel **LEAD** by one round trip): **258 ms** [251, 264] at 3–8 m/s, **232** [219, 247] at 8–15, **211** [197, 231] at 15–25, **182** [175, 191] at 25+. ⭐ **V292's routes sit inside that scatter — V292 changed nothing; the TUNE did** (r39's older tune was 20–55 ms faster; LAF 6.0 cut P/I authority). 🛑 **Not a pure delay** — three estimators differ by **up to 100 ms** on the same data and the fitted pole is **1.4–4.3 Hz, the torque controller's bandwidth plus plant, NOT the EPS servo** ⇒ **use `tau_eq(f)` at the crossover**. The **dead-time/servo-lag split is not identified** (r39 puts the speed dependence in dead time 80 → 180 ms, r6c in the pole) — **quote totals**. At 3–8 m/s the wheel realises only **0.57–0.69 of commanded curvature at 1 Hz**; small-signal is **30–50 ms slower** (friction/deadband, not rate limiting). ⇒ **B6's τ ≥ 0.18 s premise holds at every band, with margin at the 5 m/s FAIL point** |
| `scriptfix` | adversary C's four hygiene fixes | ✅ **Done and stopped.** Applied to the build script (docstring 87 % → 14.5 %, the Kd *"128 on 8 / 64 on 20"* line, the D-clamp integer into the tag, a full-tuple assertion). Census now **64 substantive / 172 vacuous / 6 tautological**, **16/16 mutations caught** (was 63/172/6 and 13/13 at write time). **Script sha256 `27d6ff76…` is FINAL; the IMAGE hash did not move** — both re-hashed at close-out |
| `artifact3` | the close-out page | ✅ **v2 published** — https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565 (the A/C/D1 verdicts, the taper split, the authority callout) |
| `goldenmodel` | the golden-model contract | ✅ **Done, and it moved the contract: 90 → 94 symbols**, because the **LKAS rate PID itself was finally added** (`lkas_rate_pid_tick`, `lkas_rate_pid_surface`, `lkas_rate_lerp`, `lkas_output_lag`, SECTION 5D of `eps_chain_control.py`) — closing the gap that had left V288's and V289's mirrors with no caller. `_self_check()`+`_demo()` hash **unchanged**; V293's surface reproduced by an independent march. Refinement to the fb-lag trace: **with `b = 0` the state's absorbing set is `[−10, −1]`, not `{0}`**, so the operand would rest in `[−20, −2]` |
| `collateral` | STATE, lineage, handoff, memory | this file, the V292 verdict, the V293 entry, the lever-index rows, the memory notes and the constellation chain |

## 2. What changed our mind, and in what order

1. **The flight read refused to force its own attribution.** The pre-registered b3 DUTY read overlapped
   the reference build and its idle control read backwards. Rather than reporting a duty that did not
   separate the builds, the agent switched to the bit's **meaning** — a lagged-sign correlation with a lag
   profile and four reference builds. **That is the only reason the routes are attributed at all**, and it
   is the session's first process lesson.
2. **The half-peak decay is confounded, and we already knew.** Two V292 routes' decay ROSE and one fell —
   exactly what `V292-REPLAY-PREDICTION` §4.2 had said this metric would do. The ring answer came instead
   from the **route-normalised** measure, which cancels a quieter or rougher drive. r6e made it vivid:
   disengaged ×0.52–0.64 of r6c's in every band while engaged was up ×1.24–2.38 — **quieter road, louder
   loop.**
3. **The predictor failed out of sample, and that reframed the whole next step.** ×0.55 predicted, ×1.20–2.00
   measured. The V293 design agent reproduced the published V292 number with its own implementation, so it
   is **the method**, not an implementation bug. Once that landed, "which dose" stopped being the question
   and "which build can answer without a model" started being it.
4. **The 7 Hz episodes are not the V278 rev 3 stall class.** P is not railed on any of the seven, so the
   mechanism is the fb pole's phase lag at 7.3 Hz — the gate `DESIGN-V291-FBLP` predicted every dose at
   a ≥ 927 would pay, and V292 carries 962. The design had priced this correctly and the flight confirmed
   the price; what it got wrong was the benefit.
5. **The arc grounding moved torque mode from "new idea" to "never-tried class with a built precedent."**
   V279 rev 2 had already passed five attackers with `0xC62E6` = 0 on a V268 base, and the whole span
   `0x28F7C–0x28FC8` plus `0x29D78` is byte-identical V268 → V282, so that proof transfers. It also
   supplied the warning: **V276 is the nearest flown relative and it drove badly**, which is why the outer
   loop is gated (B6) rather than assumed.
6. **The design agent argued against its own brief twice, and both were kept.** *"Kp 119 is the right
   number for the wrong reason"* — its justification is that it reproduces V279 rev 2's delivered surface,
   not that it is peak-neutral — and *"~90 % of the benefit is Kd = 0 + Kp, not the clamp"*, which
   separates the two goals and belongs in the operator's hands before he decides.
7. 🛑🛑 **THE B2 CALIBRATION DILEMMA — and it is why the ring claim now rests on the CAR, not the replay.**
   B2 mandated calibrating the ring predictor on V292's measured miss (**×1.90–3.64**), which is exactly
   the discipline the V292 failure should have taught. Applied, it gives **×0.54–1.47 against a ≤ ×0.50
   gate — a FAIL.** The dilemma is that **the calibration itself is the wrong instrument here.** It was
   measured on **V292, a build that did NOT open the loop**; the fit family's error there is in how a
   feedback pole reshapes the return ratio at 20 Hz, and **that error has no channel when the operand is
   identically zero** — `|S| ≡ 1` is an **identity the code region's bytes prove**, not a fit. Transferred
   to the one fully-open-loop configuration the car has been measured in, the calibration
   **over-predicts the measured ring by ×1.3–2.0: the calibrated predictor fails a measured case.**
   ⇒ The ring claim was moved off the replay entirely and onto **the car's own open-loop measurement**
   (anchor **×0.237 / ×0.285 / ×0.265**) plus the **command-driven residual** (B8, ×0.055–0.137, no pole)
   — **both EVIDENCE rather than model.** 🛑 **And the precedent is stated rather than hidden: V292 was
   also cleared over one dissent, and then failed on the wire on clauses the model had passed.** That is
   the reason for the move, not a justification after it.
8. **The fork memo recommended Design B first; the session did not take it.** Its case is real (the
   rate-plant feedforward is already 80 % of a rate target). But **Design B cannot remove the grinding** —
   V288 rev 2 flew that class and was null — and **the operator's goal names torque** as what openpilot
   expects. Both positions are now written at the top of both research documents rather than one being
   edited to agree with the other.

## 3. Process lessons

- 🛑 **A DUTY IS NOT AN ATTRIBUTION.** Design the identity read on the *meaning* of the bit, with a lag
  profile and reference builds, and check before the drive that the predicted duty does not overlap the
  reference's. V292's did, and its idle control read backwards.
- 🛑 **PRE-REGISTER MARGINS, NOT POINTS.** The operator's revert threshold on the 7 Hz ripple was 0.25 and
  V292's own prediction was 0.22 — **13 % apart**. A build whose predicted value sits that close to its own
  revert line has not been designed, it has been hoped.
- 🛑 **SCORE A BAND AGAINST THE SAME ROUTE'S OWN DISENGAGED FLOOR.** The driving model changed between the
  reference route and the flight, which changes the excitation. The route-normalised measure and the `0xE4`
  excitation control are what let the flight say anything at all; the raw whole-route ratio did not
  separate the builds (r39, a V282 route, reads as far from r6c as two of the V292 routes do).
- 🛑 **AN ADVERSARY RUNNING FIVE FAMILY REBUILDS MUST WRITE RESULTS TO FILES AND READ SUMMARIES, NOT
  HOLD THEM IN CONTEXT.** `advB3` **died of an out-of-memory error mid-run**, after delivering B3 and two
  record defects but before B1, B2, B4, B5, B7 and B8. The cost was not just the rerun: **a crashed
  adversary looks exactly like a slow one**, and the orchestrator only learns the difference by asking.
  The B surface is the one that carries plant-family sweeps, so it is the one that will hit this again.
  **Make it structural — sweep to disk, summarise from disk** — rather than trusting an agent to budget
  its own context. (The replacement, `advB3b`, re-runs the missing clauses plus the B6 re-score at the
  repaired preset.)
- 🛑 **A `GO WRITE` IS VOID IF ANY MESSAGE CROSSED IT. RE-ISSUE IT EXPLICITLY AFTER ANY SPEC CHANGE.**
  The orchestrator's first GO WRITE to `builder293` **crossed in flight with a message carrying new facts**.
  **The builder did the right thing — it rebuilt against the new facts instead of writing the image it had
  been cleared to write.** That is the behaviour to keep, and it should not depend on the builder being
  careful: a GO authorises writing *a specific set of integers*, so **any spec change between the GO and
  the write invalidates it**, and the orchestrator must send a fresh one naming the new constants. This is
  the same class as the kit's frozen-report rule — once a build's constants are reported they are frozen —
  applied one step earlier, to the authorisation itself.
- 🛑 **WRITE THE PRE-REGISTRATION BEFORE THE DESIGN LANDS, NOT AFTER.** `ADVERSARIAL-V293-PREREG` was
  written before the image existed **and before the builder was briefed** — which is why the build script
  arrived carrying **two presets** and a section headed *"the build brief and the pre-registration
  disagree"* on three points, all three resolvable from the prereg's own clauses (A2 fixes Kp at 120; A1
  forces the D clamp to 0; the r24 ladder gains a rung). That disagreement is a **feature of the order**:
  the criteria could not be bent to the build because they existed first. **Keep the order.**
- 🛑 **A DOSE RULING AGAINST THE DESIGN AGENT MUST SAY WHY, AND MUST BE SCOREABLE.** The design recommended
  r24 = 4451, criterion-exact on gate73. The orchestrator took **2048** before any image existed, on three
  grounds — the same model under-predicted V292's measured 5–9 Hz cost three-fold, 2048 is the record's own
  priced lever, and the 20 Hz cost of a cut is nil in torque mode specifically — and marked it **BELIEF**,
  then briefed adversarial B to score **4451 and 2048 side by side**. A ruling that cannot be scored is a
  preference; this one can be falsified.
- **An agent that reports what its instrument cannot do is worth more than one that reports a number.**
  Three of this session's most load-bearing lines are of that form: *"the duty read does not discriminate
  and I am reporting that rather than forcing it"*, *"the one out-of-sample test of this predictor
  FAILED"*, and *"b5/b6 cannot confirm or refute the r24 cut at this dose."*

## 4. On disk

- **On the car:** **V292** — routes `75604b0a432fdc89_0000006d--5e7b4d2ceb`, `…6e--64b4a5fef4`,
  `…6f--d876c761bc`. 🛑 **REVERT by its own pre-registration. The fallback is V282** (rwd sha256
  `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22`).
  🛑 **The dongle counter was RESET — these are NOT August's `r6d`/`r6e`/`r6f`; caches carry a `_v292` suffix.**
- **Built, not flown, 🛑 CLEARED AS THE FLIGHT CANDIDATE OVER ONE DISSENT:** **V293** — rwd
  `$ACCORD_FIRMWARE_ROOT/flashing-2020accord/rwd/39990-TVA,A160-V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd`
  sha256 **`ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba`**; image
  `_v293_V293-V282BASE-TORQUEMODE.FB0-…_plain_image.bin` sha256
  **`f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17`**. **Exactly one V293 rwd on disk.**
  Both hashes **re-verified from the files themselves at close-out**, not taken from an agent's report, and
  the byte census re-derived independently from the two images: **378 differing bytes in 183 runs over
  6 CRC blocks** — 1 (`0xC62E7`) + 1 (`0xC61B7`) + 2 (`0xC6446–47`) + 112 Kd knots + 240 Kp knots = 356
  payload, + 22 trailer. Cells read back: `0xC62E6` = 0, `0xC61B6` = 0, `0xC6446` = 2048, Kd slot-7 record
  `0xE511C` Y = 0,0,0, Kp slot-7 record `0xE5378` Y = 120,120,120,120 with X unchanged.
  ⚠ **Two of the six CRC trailers differ in only 3 of their 4 bytes** (`0xE6FFC`, `0xE7FFC`) — a run-length
  scan that demands a full 4-byte trailer run finds only FOUR blocks and undercounts. **242 assertions**
  (63 substantive / 172 vacuous / 6 tautological), **16/16 mutations caught**, and the build-audit
  adversary's independent rebuild from the V282 image plus the prereg's edit list lands on the same two
  hashes. 🛑 **ZERO of the 378 differing bytes lie below `0xC0000`** — the cal-only claim is a byte fact,
  not a docstring claim.
- 🛑 **THE SCRIPT HASH MOVED AND THE IMAGE HASH DID NOT — quote the script hash with its moment.**
  `build_v293_tva.py` was sha256 **`8ffb29a9e192a7b37cc495df4e6829199d4854afe13200b9ac6588d5c0e4a21e`** at
  write time; `scriptfix` then applied adversary C's four hygiene fixes and it is now
  **`27d6ff7689227e7d21a1a59dfb4daaf8788ba8f359de6e0a95fd0757d753c964`** (123,435 B), and `scriptfix` has
  **stopped**, so that is final. **The image re-hashes to `f75e77cf…` unchanged**, which is the property
  that matters: the artifact is the invariant, the script is not. The kit's frozen-report rule should be
  read as freezing *the artifact and the integers*, not the file that produced them. Post-fix assertion
  census **64 substantive / 172 vacuous / 6 tautological**, **16/16 mutations caught**.
- 🛑🛑 **A STANDING FORK DEFECT, LIVE ON THE CAR TODAY AND NOT A V293 PROBLEM.** StarPilot feeds
  **`error_with_lsf`** (= `error·(1 + lsf/kp)`) into **`get_friction`**, where upstream openpilot feeds the
  **raw** error, so the friction compensator's gain is **`(friction/0.30)·(1 + lsf/kp)`** — **×6.6 at the
  operator's live Kp 0.9 on V282 right now**, and **×17.9** at the V293 preset's Kp 0.3 at 5 m/s.
  ⭐ **A lower Kp makes it worse, not safer** (loop gain minimised near Kp ≈ 1.0). **Fork-side repair:
  preset friction 0.01 → 0.00.** It does not depend on which image is in the ECU.
- **Golden model: the contract moved 90 → 94 symbols**, because the LKAS rate PID itself was added
  (`lkas_rate_pid_tick`, `lkas_rate_pid_surface`, `lkas_rate_lerp`, `lkas_output_lag`, SECTION 5D of
  `eps_chain_control.py`); a fifth new def, `_self_check_v293`, is deliberately **not** re-exported.
  `_golden_contract_syms.json` carries the four. `_self_check()`+`_demo()` stdout is **unchanged** at
  2,512 B / `740f4bcd…`. `CLAUDE.md`'s contract line was updated by `goldenmodel` and **independently
  re-verified at close-out** (94 / 2,512 B / `740f4bcd…`).
  Script `analysis-2020accord/builds/v108_plus/build_v293_tva.py`; design
  `docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md`; prereg
  `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`; lineage entry
  `docs/BUILD-LINEAGE-PART6-V291-ONWARD.md`; **page**
  https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565 (v2).
- 🛑 **THE DELIVERED RAIL IS 2461, AND THREE NUMBERS HAVE BEEN CALLED "THE RAIL".** **2461** is the
  byte-exact steady state through the fade and the output lag and it reads 2461 on the **V293 image AND the
  V282 image** (the residue is the output lag's integer fixed-point interval) ⇒ **peak authority is ×1.000,
  not the design doc's ×0.9992**. **2462** is the same chain's **linear DC** — the tracer's number.
  **2505** is the **structural ceiling**, the `T_ceil` convention the older docstrings print; **never quote
  it as delivered**, neither build reaches it at fade 254.
- **Flight read:** `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md` plus `extract_v292_routes.py`,
  `v292_flight_{params,attrib,b3sign,highangle,crux,creep,phase,decay,census}.py`. ⚠ `v292_flight_census.py`
  did **not** complete in the session's budget; its band answers are reproduced by `_creep.py` and its
  presence/decay answers by `_decay.py` on the identical predicate. Two scripts had an ordering defect on
  first run and are fixed in place.
- **V293 design scripts:** `rlog-tools/studies/grind/v293_lib.py` and `v293_s1_surface.py` …
  `v293_s10_clamp.py`.
- **Trace and research:** `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md`;
  `docs/research/ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md` and
  `FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md` — **each now carries a
  Reconciliation note at the top** pointing at the other and at the prereg's dispositions, with neither
  body edited. Operator card: `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.
- **Fork (`../openpilots/raayyymond-StarPilot/StarPilot` @ `Dom`):** the torque-mode preset applied as
  **Testing Ground 9 "Accord EPS Torque Mode" variant B**, **UNCOMMITTED, ships on A**; the earlier
  `ModelCurvatureLead` patch and the operator's own SR-map refit untouched (26 explicit content checks
  at close-out). **Not pushed.** ⚠ HEAD had moved past the brief's `305732c85` to `a357cd2b5`;
  the car on route 6f was on `305732c85`.
  🛑 **The five params that shipped earlier in this same session are DELETED** — `AccordEpsTorqueMode`,
  `AccordTorqueModeLatAccel`, `AccordTorqueModeFriction`, `AccordTorqueModeKp`, `AccordTorqueModeKi`.
  Any card, script or scorecard row still reading them is describing a **pre-rework fork**.
- **Lineage split, this close-out.** `docs/BUILD-LINEAGE.md` reached **240.9 KB** against the 256 KB `Read`
  cap, so **new per-build entries from V293 onward go in `docs/BUILD-LINEAGE-PART6-V291-ONWARD.md`**
  (18.9 KB). ⚠ **PART6, not PART5** — `BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md` already exists and is a
  different artifact. V291 and V292 keep their entries in the entry file, and **V293 has a one-line stub
  there so `grep V293` still lands.** `BUILD-LINEAGE-PART1-LEVER-INDEX.md` is **198.4 KB** and over the
  150 KB soft target — split it next.
- **STATE.md** is **26.7 KB**; the superseded V292 decision box is archived at
  `docs/archive/STATE-ARCHIVE-2026-09-13-v292-decision-box.md` (18.1 KB), kept verbatim because it is the
  pre-flight statement the flight was scored against.
- **Memories:** two new kit notes under `memory/accord/builds/`, pointers at the top of `memory/MEMORY.md`
  (143.6 KB before this close-out), and a new chain entry in `memory/MEMORY_CONSTELLATION.md`.
- **Golden model:** see the contract note above — **it was extended, not merely re-verified.**
- **No commit, no push.**

## 5. The operator's instructions this session

- **The goal, verbatim in substance:** a new firmware **and** StarPilot changes that keep **V282's
  authority (×6 torque, ×6 rate setpoint, no EME faults)** with **no grinding and no stutter**; the LKAS
  PID should track **angular acceleration (≈ torque, what openpilot expects)** **or** StarPilot should
  output a **rate target**; and the **StarPilot tuning updated** to match.
- **Subagent model policy:** never Fable; **Opus for hard tasks, Sonnet for trivial**, set explicitly on
  every `Agent` call.
- **Never record the two openpilot colleagues by name** — "colleague 1" / "colleague 2" only, in the repo,
  in commits, in docs and in artifacts alike.
- **His symptom report on V292, in his own words:** *grinding still present; stuttering is WORSE, most
  visible as an oscillation when holding the wheel at a high angle.* **This document scores bands; he
  scores symptoms. Nothing here calls anything fixed.**

## 6. Open items

1. **The V293 adversarial pass, and then the operator's decision.** The clause most likely to return
   do-not-flash is **D1, the sustained-effort census**: a torque-mode lane holds full commanded torque
   however fast the wheel already moves, so **dwell at the rail rises even though the peak does not**.
   Census every reader of `gp-0x6b94`, `gp-0x6ace` and `gp-0x6acc` for an accumulator or integrate-and-trip
   and decompile the governor `FUN_0004503c` / `FUN_000456a4`. **This gate has never been run, and every
   future torque-mode or authority build will need it.**
2. **Fill V293's hashes** into three places from `builder293`'s report, read back from the built image:
   the PART6 lineage entry, the STATE box, and the kit memory note.
3. **THE TAPER — the SELECTOR closed, the AXIS UNIT did not.** ✅ Closed: **one stage** at `0x2A13x`,
   `factor = ((tapAB·tapCD)&0xFFFF)>>8`, **`gp-0x6803` picks B × D (`0xCBBC4`)**, 254/256 at rest because
   both halves return 255 there. The kit memory was right about D; `looptrace`'s C reading was wrong.
   🛑 **Still open: what the C/D half's X axis is in.** Adversary A read it as speed and **assumed km/h —
   its own BELIEF** — which would derate the rail to **2151 at 10 m/s and 736 at ≥ 20 m/s**; the record's
   on-car tap numbers point the other way (V278 rev 3's `T_meas/T_sim` 0.42–0.51 at 3–9 m/s; the tap's 310
   rail on faster routes). **Do not treat the derated rails as established.** ⭐ Safe either way: **the
   table is identical on both builds, so the V282 : V293 ratio holds at every speed.** But 2461 is an
   AT-REST number — condition every on-car rail read on speed, and score "identical rail to V282" on
   matched trajectories from a cold-start state of 0 on both images.
4. **`gp-0x6806`'s engaged state** is still the open premise behind the sp = 3 deadband argument.
5. **The IMU** remains the top missing instrument — nothing so far separates road from rack from motor.
6. 🛑🛑 **NOTHING IN THE FORK MEASURES τ — three fields look like identifications and none is.**
   `liveDelay.lateralDelay = 0.2` is the operator's `SteerDelay` toggle **echoed back**;
   `lateralDelayEstimate` (0.2479) is **~99 % SEED from previous routes** (50 blocks all seeded, r39
   **frozen at 0.2272 for 948 s**), **gated to ≥ 15 m/s**, and reads **livePose yaw, which lags the gyro
   by 73–90 ms**; and ⚠ **a fork defect, reported not fixed** — `full_lateral_delay(x) = x + 0.2` while
   **the toggle branch in `lagd` SKIPS that wrapper**, so the field **mixes two conventions** depending on
   which branch wrote it. The operator's `SteerDelay` 0.2 is a **FULL** delay, implying a **vehicle part
   of 0.0** against stock Honda's 0.1 / 0.3. **Quote the measured totals and `tau_eq(f)`; never quote
   0.20 s as measured.**
7. **The r26 base-assist arm `0xC6444` also moves with the `0x3AA96` gate** — unresolved, and it is one of
   the three residuals that keep the on-car ring anchor an estimate rather than a measurement.
8. **Two record statements about `torqued` need updating, and this is a report, not a licence to edit
   them:** `liveValid` now reads 1 with `latAccelFactorRaw` 6.24 on route 6f (the "cannot validate" finding
   was measured at the port defaults, where it was 0 on every tick), and the toggle ceilings quoted there
   are stale. **Still do not identify LAF from `torqued` — its buckets do not fill on this car.**
9. 🛑 **THE B ADVERSARY'S DEFECT LIST (its §9) — SIX TOOL AND DOCUMENT DEFECTS, NONE IN THE ARTIFACT.**
   Each one can silently corrupt a later result, so they are open items, not footnotes:
   **(a)** the module-default `B(f)` fit is bad (`nb=1, nd=4` → rms `ln|B|` 0.54, phase 38°, **a spurious
   unstable 4.5 Hz root**) — use `nb=1, nd=3` and re-check anything fitted with the default;
   **(b)** **`r24_plant_refit.py` cannot regenerate `r24_plant_refit.json`** — `fit_B(nb=4, nd=2)` raises
   on the properness guard, so **the prereg's own named reference family for B1 has no working producer**;
   **(c)** **`v293_s3_gate7`'s unbanded `unst` column is meaningless** — do not quote it;
   **(d)** **the design scripts modelled Kp 119 while the image carries 120**, so every Kp-dependent
   design number is off by that count until re-run;
   **(e)** **`v293_s4` never ran the stock leg or F7** — those figures do not exist;
   **(f)** **`v293_s2` TASK 2C's V293 command leg reads ×2.5 below the second method** — unreconciled;
   **(g)** **the pre-registration's own anchor caveat (1) is void** and **the r26 sibling arm was omitted**.
10. **`0xC61C0`/`C2`/`C4`** still has no lineage entry.
