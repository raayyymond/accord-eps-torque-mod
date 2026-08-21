---
name: reference_accord_f0_dose_floor_and_common_path_structure_search
description: The f0 (Re(Z) zero-crossing frequency) dose-floor question -- route-stock measured f0 linear in gain across 3 disjoint-CI points (stock 21.90Hz, V100 4x 23.61Hz, V102 6x 24.90Hz; ~1.7x gain per 1Hz of f0), setting a 1.5Hz bar no branch-limited lever (incl. the V103 biquad) can plausibly clear. Traces the search for a non-gain lever capable of clearing it: a simple single-resonance retrodiction badly over-predicts the shift magnitude (right direction, ~8x too large); the two downstream "common path" candidates checked (governor FUN_0004503c, comp-add FUN_000456a4) are a nonlinear slew limiter and a static LERP respectively, neither a tunable linear filter. Working structural synthesis: gain's privileged position is not its place in the block diagram but that it is the only variable that changes the PHYSICAL delivered-torque amplitude, which re-linearizes multiple amplitude-dependent nonlinearities (f', plausibly the governor) system-wide at once -- something a fixed linear filter on one branch cannot replicate.
metadata:
  type: reference
---

# The f0 dose-floor -- is there ANY non-gain lever that moves it by >=1.5Hz? (task "damphunt round 4")

Briefed 2026-08-20 by team-lead, following the V103 biquad spec close-out. `route-stock` measured
`Re(Z)`'s zero-crossing frequency `f0` (top of the anti-damped region) across three arms, engaged
hands-off, 29-86km/h:

| arm | gain | f0 | 95% CI |
|---|---|---|---|
| STOCK | 1x | 21.90 Hz | [21.08,23.03] |
| V100 | 4x | 23.61 Hz | [23.22,23.95] |
| V102 | 6x | 24.90 Hz | [24.63,25.26] |

All three CIs disjoint; f0 ~= 21.3+0.60*gain, LINEAR. Power: one ~100s hands-off drive resolves a
~1.0Hz shift ⇒ **a lever must move f0 by >=1.5Hz to be reliably scoreable.** 1Hz of f0 ~= 1.7x of
LKAS gain, so a non-gain lever must do the work of a 6x->4.3x gain reduction to register. The V103
biquad's own predicted contribution (+2 to +13 ct·s/rad realistically, +50 at an extreme q=1.0,
against the -488 gap) translates to only **~0.06-0.3Hz of f0** -- 3-15x below the bar. Correctly
priced as "rides free, predicted below detection," not dropped (see
[[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]] §10 for that lever's own spec).

## 1. Theoretical retrodiction attempt -- gets the DIRECTION right, badly OVER-predicts the MAGNITUDE

Model: `L(f,gain) = gain * L_unit(f)`, `L_unit(f) = bare_plant(f) * e^(j*90deg)` (the anchor script's
own fixed-shape-carrier assumption, `ZETA_BARE=0.2944`, `F_ANCHOR=21.4Hz`, cited unchanged from
`eps_loop_gain_model.py`). `Re(Z)(f0,gain)=0` reduces to `Re(L_unit(f0)) = R/gain` for one free
constant R. **`Re(L_unit(f))` is genuinely DECREASING with f in this range (0.89 at 21Hz falling to
0.50 at 26Hz) — so the model correctly predicts f0 rises with gain, structurally.** But calibrating on
ONE point (stock, gain=1) and predicting the other two: **predicted f0 at 4x = 31.5Hz (measured
23.6Hz, error +7.9Hz); at 6x = 34.5Hz (measured 24.9Hz, error +9.6Hz).** The simple model over-shoots
by roughly 5-8x. [EVIDENCE for the calibration/computation; the CONCLUSION that the shape is wrong is
BELIEF]. **This means the real loop's `Re(L)` vs frequency curve near this region must be MUCH FLATTER
(less frequency-selective) than a single ζ=0.29 resonance implies** — either a lower effective Q, a
broader/multi-mode structure, or a partially-canceling second term I haven't modeled. Do not use this
model's specific Hz-per-gain numbers; the DIRECTION argument is the only part that survived.

Script: `scratchpad/f0_structural_test2.py` (search bounds must be restricted to the falling branch,
`f>21Hz` — the naive [15,45]Hz bracket straddles the peak near 20Hz and breaks `brentq`).

## 2. Checked two "common path" (downstream-of-aggregator) candidates — NEITHER is a tunable filter

Fresh `decompile_function` on both (full functions, not partial):

- **`FUN_0004503c` (the governor, `gp-0x6b94`→`gp-0x6ace`)**: a **nonlinear SLEW-RATE LIMITER** with a
  motor-rate-adaptive ceiling (LERP-keyed on `gp-0x6a64`), a fast/slow step selector
  (`gp-0x67f5`-gated, cal `0x7206`/`0x7208`), and a persistent RAM state (`gp-0x138a`) that ramps
  toward the clamped target by at most one step/tick. **No IIR/recursive-filter structure — its
  "phase" contribution is amplitude-dependent (only lags when the signal moves faster than the step
  allows), the SAME class of nonlinearity as `f′`, not a fixed linear pole.** Confirms
  `gp-0x69aa` (Q15 governor derate) is written here, matching the prior "MIN-only, unity-seeded"
  characterisation. Also confirms the state-4 override branch (`gp-0x67fa==4`, V42's ratchet fix).
- **`FUN_000456a4` (comp-add, `gp-0x6ace`→`gp-0x6acc`)**: a **static, memoryless nested-LERP**
  correction keyed on `gp-0x6a10` (absolute steering angle) and `gp-0x6ac0` (FOC electrical rate),
  added to the governor's output. **No persistent state, no recursion — a pure combinational shape
  each tick, zero dynamics of its own to retune.**

⇒ **Neither downstream candidate offers an existing linear filter whose pole/phase could simply be
adjusted** (unlike the biquad, which was a dormant but complete IIR). A genuine phase-shifting element
on the common path would have to be a NEW insertion (a real cave — now authorised, but GATE 1/2/3 all
apply fresh, no "Honda already validated this filter" shortcut).

## 3. Working structural synthesis [BELIEF, this session's own reasoning, not independently proven]

**Gain's privileged effect on f0 is probably not about WHERE `0xC6CD0` sits in the block diagram — it's
that gain is the only variable in this firmware that changes the PHYSICALLY DELIVERED TORQUE
AMPLITUDE**, and this firmware has *multiple* amplitude-dependent / gain-scheduled nonlinearities that
all re-linearize simultaneously as that amplitude rises: the observer's `f′` LERP (already
characterised, §9b-9d of the biquad file — local slope falls ~10x over the amplitude range gain
plausibly reaches) and *plausibly* the governor's own slew limiter (§2 above — if gain pushes the
signal into its active-limiting regime more often, that ALSO contributes amplitude-dependent phase
lag, additively). **A fixed LINEAR filter on ONE branch (biquad, a PID pole, any single aggregator
lane) touches only that branch's FIXED dynamics and — per the branch-fraction (`q`) argument already
proven for the biquad — is structurally too small to replicate a SYSTEM-WIDE, amplitude-driven
re-linearization.** The only way to move f0 by 1.5Hz+ without touching `0xC6CD0` would need to
artificially reproduce gain's amplitude-driven effect through a DIFFERENT channel — a genuinely novel
design problem, not a retune of an existing structure.

**This is a synthesis across this session's own findings, not a closed, quantitatively validated
proof** — the retrodiction in §1 could not nail the magnitude, so I cannot yet say with EVIDENCE-grade
confidence exactly how large a "common-path amplitude-dependent lever" would need to be to reach
1.5Hz. Flagged to team-lead as the honest state: direction/plausibility argument, not a completed
calculation.

## 3b. ⭐⭐ A data-anchored ct/Hz benchmark, AND a strong lead in `ratchet-inertia`'s r24/r26 work

**Local slope, derived directly from route-stock's own f0/Re(Z) numbers** (not the broken theoretical
shape): using each arm's own `f0` and its 22-26Hz band-average `Re(Z)` as two points on a locally-linear
`Re(Z)(f)`, stock gives ~177 ct·s/rad/Hz, V102 gives ~129, averaging **~153 ct·s/rad per Hz of f0**.
Cross-checked against the V103 biquad's own already-reported effect: its q=1.0 best case (+50 ct·s/rad)
converts to 0.33Hz, realistic range (+2 to +13) to 0.01-0.08Hz — consistent with team-lead's own
independent conversion. **⇒ clean benchmark: a candidate needs ~230 ct·s/rad of `Re(Z)` effect to clear
1.5Hz — ~4.6× the biquad's own best-case, deliberately-extreme number.** Script:
`scratchpad/f0_structural_test2.py` companion calc (inline, not separately saved).

**`ratchet-inertia`'s r24/r26 finding (`reference_accord_r24r26_driver_torque_lane_reZ_estimate.md`,
their file) is the most promising lead found this round — flagged to them and to team-lead, not yet
independently computed by me at 22-26Hz.** Key facts from their work, cited: `gp-0x6752` (polarity)
resolved **-1** two independent ways; r24/r26 (aggregator-inline, `±0x2000` window EACH — **8× the
biquad's `gp-0x6b86` window**) is now correctly-signed **PUMPING at 6-9Hz/9-12Hz** (-431 to -1294ct at
their G=1-3 range, matching the measured worst bands) and **flips to DAMPING at 12-31Hz** — which
covers the 22-26Hz f0 band. Two structural reasons this is more promising than a new filter:
(1) its input (`gp-0x4f62`, a difference of raw torque sensor `gp-0x4f60`) is a DIRECT, PHYSICAL
amplitude link to delivered torque — not something to invent, it may already BE part of the mechanism;
(2) **the torque SENSOR reading itself grows 5.35× (not the aggregate command's ~2×) from 4×→8× gain**
(V101 handoff §2.6, already-measured: `|driver torque|` p50 174→931ct, attributed to "the torsion bar
carries 5× more signal because it is buzzing") — meaning r24/r26's own magnitude, if small-signal-linear
in its input (their own deadband-negligible finding supports this), should scale with THIS bigger
factor, not a flat gain-cal ratio. **Asked `ratchet-inertia` directly to extend their exact 6-9Hz
`Z_r24(f)=G·H_diff(f)·Z_measured(f)` method to 22-26Hz** using the real 5.35× amplitude figure — I do
not have the full complex `Z_measured(22-26Hz)` (only the band-averaged real part team-lead relayed),
so I cannot replicate their method myself; this is a fast reuse of their own tooling, not new work for
them. **Not yet answered.**

## 3c. 🛑🛑 TEAM-LEAD CORRECTION: the `q`-limit was a PLACEMENT artifact, not structural — validated

Team-lead correctly identified a flaw in §3's synthesis: the biquad's `q≈0.10-0.25` is a property of
WHERE it sits (one of ~9-10 aggregator LANES), not of what a filter can do. **Downstream of the
aggregator sum, `q=1.0 BY CONSTRUCTION`** — confirmed structurally this session (governor + comp-add
both decompiled fresh, both single-input-single-output on the ONE serial chain `gp-0x6b94`→governor→
`gp-0x6ace`→comp-add→`gp-0x6acc`→shaper→`gp-0x6b08`→integrator→`gp-0x6b98`→FOC). Also corrected:
the biquad's `|H|≤1` design is a MAGNITUDE-only intervention with negligible phase authority — pricing
`f0` (a PHASE boundary, the 90° crossing) against a magnitude filter's own number was the wrong
comparison; a phase-shaping (lead/lag/allpass) element is the right instrument class.

**Recomputed properly**: for a downstream insertion, `L_new(f)=L_old(f)·H_insert(f)` (MULTIPLICATIVE,
not the additive "branch fraction" form used for the biquad). For a pure phase shift (`|H|=1`,
`φ` = inserted angle): `Q=1` PHASE-INSERTION result, computed with the same calibrated `L_total(f)`/
`C=144.2`/`~153ct·s/rad-per-Hz` apparatus:

```
phase inserted:  -10deg  -30deg  -60deg  -90deg(extreme)
avg d(f0), 22-26Hz band:  +0.05  +0.20  +0.51  +0.86 Hz
```
Phase LAG (negative φ) is the coherent, consistent-sign direction; phase LEAD gives inconsistent,
partly-cancelling sign across 22-26Hz (not a usable direction with a flat/uniform phase assumption).

**⇒ Validates team-lead's structural correction QUANTITATIVELY: q=1 delivers ~3-15× the biquad's own
best-case, matching their predicted "4-10× multiplier" order of magnitude.** But **even at an extreme
-90° flat-phase-lag dose, my model predicts only ~0.86Hz — short of the 1.5Hz bar**, though far closer
than the biquad ever got. 🛑 **Explicitly flagged as untrustworthy to better than ~2×**: this model's
own magnitude-vs-frequency SHAPE is known wrong (§1's retrodiction over-predicted the gain-driven f0
shift by 5-8×) — have NOT re-derived with a corrected (flatter) shape, and don't know whether that
correction would make the phase-sensitivity number bigger or smaller. **This is the single highest-
value next refinement if a tighter number is needed.**

Script: `scratchpad/phase_insertion_q1.py`.

## 3d. 🛑🛑 A SERIOUS, UNRESOLVED-ROOT-CAUSE HAZARD in the exact proposed insertion region — V40's brick

Checked before recommending any site (team-lead's explicit ask). **V40 (2026-07-19,
`docs/HANDOFF-2026-07-20-session-v40-fault-investigation.md`) bricked the car with a cal-only edit
INSIDE `FUN_0004503c` — the same governor function decompiled this session.** It set the slew steps
`0xC6206`/`0xC6208` (512/205 → 65535, defeating the rate limiter) and flattened the motor-rate cap
taper. **Result: power steering fully disabled at every start, stationary, untouched.**

🛑 **The root cause was never fully resolved** — the fault-investigation session's own record: THREE
retracted hypotheses in the same session (a CRC-bridge theory, a governor-`MIN`-location theory, a
`0xC6194`-slew theory — all disproven by their own premises), closing with *"V40's fault is NOT
root-caused."* **Not the same failure class as a new phase-filter insertion** (V40 removed an existing
PROTECTIVE CLAMP via cal edit; a filter would be new code, not a clamp removal) — but this functional
region carries a documented brick with an UNKNOWN mechanism, a different and arguably worse risk
profile than "we understand the failure mode here." **Any insertion in the governor/comp-add chain
needs explicit checking against whatever V40's real (still-unknown) mechanism was**, not just against
named failure modes.

## 3e. Ranked insertion points, current state of knowledge (NOT yet GATE 1/2/3-verified for any specific design)
- **Governor (`FUN_0004503c`)**: nonlinear slew limiter (see §2), carries the V40 history above.
- **Comp-add (`FUN_000456a4`)**: static memoryless LERP, no V40-specific history found, structurally
  simpler (no persistent state to corrupt) but same region/CRC neighborhood.
- **Shaper's own integrator (`gp-0x3570` inside `FUN_00042af8`)**: NOT checked this round for
  phase-tunability. A genuine accumulator (`integ += (cmd-envelope)*0x8000` per
  [[reference-accord-integrator-update-form]]) with real inherent phase content, but no obvious
  adjustable time-constant on record — needs a fresh look before ranking.

## 3f. r24/r26 as "the empty socket" (team-lead/pump-hunt's framing) — a DIFFERENT class, not q=1

Distinct from the q=1 common-path idea: r24/r26 is STILL lane-limited (one of several aggregator
inputs, not downstream of the sum) — pump-hunt found it has no phase-shaping element at all (memoryless
4-tap difference, no break frequency below 125Hz), so a cave COULD add the first one there, but its
case rests on its OWN size (±0x2000, 8× the biquad's window) and direct amplitude link, not on
placement advantage. Needs its own `L(f)` magnitude+phase at 22-26Hz to price — asked `ratchet-inertia`
to extend their 6-9Hz method (see §3b); not yet answered.

## 4. `pump-hunt`'s D-term answer — magnitude confirmed larger at 22-26Hz, but NO attribution fraction

`pump-hunt` answered fast, from their own already-verified closed form (`H_D(f)=(Kd/1024)·2·sin(πf/fs)`,
cross-checked to their own 21Hz table entry): **`|H_D|` at 22-26Hz (0.276-0.326) is 2.8-3.3× LARGER
than at 7.79Hz (0.098)** — real and structural, a derivative naturally grows with frequency. Phase is
a near-uniform ~85-86° across this band (matches my own earlier D-phase trace, unaffected by the
`gp-0x6752` sign resolution since that's a POST-combine multiply, not internal to D's own recursion).

**But they explicitly refused to supply an attribution fraction (`q`)** — citing the exact caution this
file already carries (the `gp-0x6b26` isolated-stage estimate that was ~227° wrong once the loop
closed) — rather than hand over an isolated-stage number dressed up as a loop-fraction. **Correct call,
not a gap in their work.** Also flagged: **`Kd` (`0xC6AE6`) is fully virgin, N=0/102** — genuinely
UNTESTED, not tried-and-failed, a different epistemic status from every branch-limited lever priced
this session. Proposed (not yet built): a V104 telemetry addition giving `gp-0x3680` (D_state) a real
magnitude channel at the existing cave hook, to MEASURE D's dose-response directly instead of deriving
it — cheap, not yet actioned.

## 5. 🛑🛑 THE DIRECTION QUESTION — genuinely unresolved, reported honestly rather than forced

Team-lead correctly caught two things in the r24/r26 thread: (1) I floated "a candidate lever if its
gain cal turns out separable" WITHOUT grepping `build_v*_tva.py` first — exactly the standing rule
violation this kit's own doc opens with. **Corrected in place, moving forward on phase framing only,
not gain dosing of `0xC6446`/etc.** — those cells are CLOSED per `docs/STATE.md` §5 (V61/V71c/V88
history: "rate lane closed at an optimum... Lever B removed from every shortlist, BOTH directions").
(2) The DIRECTION question: does r24/r26's damping-at-22-26Hz growing with gain predict `f0` moving
the WRONG way (down), contradicting the measured UP?

**Worked through it and concluded: NOT RESOLVABLE with current data, and said so plainly rather than
guess.** `ratchet-inertia` independently flagged the same gap from their own side: their method
(`Z_r24=G·H_diff(f)·Z_measured(f)`) uses the ALREADY-CLOSED-LOOP `Z_measured` as an input — if
`Z_measured` shifts with gain for ANY reason (including my own `f′` mechanism), their r24 number
reflects that shift PASSIVELY, with zero information about causation. **Two independent agents
(`ratchet-inertia` on r24/r26's method, `pump-hunt` on D's attribution fraction) both correctly
declined to guess the SAME missing piece — D's specific SIGN at 22-26Hz once the loop closes — for
the identical reason.** Resolving the direction needs that sign (or an equivalent multi-term
derivative decomposition near `f0`), which does not exist. **I did not force a third guess.**

**Checked one piece myself before concluding this**: the 4-tap differencer's OWN phase (`H_diff`)
moves only modestly across this range (84.4°→71-74° from 7.79Hz to 22-26Hz, still a strong lead
throughout, no sign change) — confirms the pump→damp flip in `ratchet-inertia`'s estimate comes from
`Z_measured`'s own phase shape, not from `H_diff` itself. Doesn't resolve the direction question, but
rules out one candidate explanation (a differencer sign-flip) cleanly.

**What actually closes it**: both `ratchet-inertia` and `pump-hunt` independently named the same fix —
direct, gain-matched ON-CAR telemetry (not another derived estimate). `gp-0x6ada`/`gp-0x6adc` (r24/r26)
and `gp-0x3680` (D_state) are BOTH already free telemetry (zero new RAM). Neither has a magnitude/phase
channel built yet. **This is the actual next step, not a modeling choice.**

**Comparison delivered anyway, honestly scoped**: q=1 common-path phase insertion prices at ~0.86Hz
(extreme dose, ~2× uncertain, §3c). r24/r26's phase lever CANNOT be priced — the sign of what dose is
even wanted is the open question — but its raw, undoctored magnitude (ratchet-inertia's 293-880ct·s/rad,
route-77/4×-era, not gain-matched) already EXCEEDS the ~230ct·s/rad benchmark before any phase-shaping
is added, meaning IF the direction resolves favorably this is structurally the most promising candidate
found this session — bigger than the common-path option. **That "if" is load-bearing; not collapsed
into a number.**

## 6. 🛑🛑 SIGN BUG FOUND AND FIXED — team-lead's challenge #1 was right to demand a re-derivation

`d(f0) = d(ReZ)/SLOPE_HZ` (what I coded/reported) was WRONG. Correct, re-derived from scratch and
checked against the one fact known to be right (f0 INCREASES with gain): **`d(f0) = -d(ReZ)/SLOPE_HZ`**
(a MINUS sign). Proof: `Re(Z)_new(f) ≈ S·(f-f0_old)+d(ReZ)`, set to zero at `f0_new`, solve. Sanity
check: gain raises f0 (measured) ⇒ needs `d(ReZ)<0` as gain rises ⇒ physically correct (more gain =
more anti-damping = Re(Z) more negative at a fixed frequency) — CONFIRMS the minus sign, not asserts it.

**Corrected reading of the q=1 phase-insertion result (§3c)**: phase LAG gives `d(ReZ)>0` (more
damping — this part of my earlier work was right), which via the CORRECTED formula gives **`d(f0)<0`
— f0 DECREASES, moving TOWARD stock.** My magnitude (0.86Hz at an extreme -90°) and my identification
of "lag is the coherent direction" were both right — the bug was a missing minus sign in the FINAL
Hz-conversion step, which mislabeled a GOOD, direction-correct result as if it were showing f0
increasing. Corrected: **-90° phase lag at q=1 predicts f0: 24.90→24.04Hz (-0.86Hz), the RIGHT
direction, still short of the ~3Hz needed to reach stock's 21.90Hz.**

Script: `scratchpad/sign_check_and_governor_df.py` Part A.

## 7. On team-lead's `Re(Z)=|Z|cos(φ)` critique (challenge #2) — valid core, but not quite my model

Their argument: if gain scales the WHOLE Z uniformly (`Z_new=gain·Z_unit(f)`), the crossing
(`cos(φ_unit(f))=0`) is gain-INDEPENDENT by construction — pure magnitude scaling literally cannot
move `f0`. **True, and a real trap for a naive model.** My actual model isn't quite that strawman: it
has a separate, gain-INDEPENDENT baseline (`D_bare`, physically the bare mechanical plant's own
damping, present even with the loop open) MINUS a gain-SCALED loop term — a genuinely different
structure that CAN move `f0` (a balance between a fixed and a scaled quantity, not one thing scaling
uniformly), and it did predict SOME shift, just the wrong magnitude (5-8× too much, §1). So the
critique's letter doesn't fully apply to what I built — but its SPIRIT is right: the over-prediction
itself shows the loop term's magnitude-vs-frequency SHAPE assumption is wrong, and that's exactly
consistent with (though doesn't strictly prove) their deeper claim that gain changes the loop's PHASE
profile, not just its magnitude. Did not resolve this fully — flagged as unclosed, not conceded on the
math alone.

## 8. 🛑🛑 GOVERNOR DESCRIBING-FUNCTION TEST (challenge #3) — NUMERICAL simulation, not a recalled formula

Built a direct time-domain simulation of the EXACT discrete slew limiter (`out[n]=clamp(target[n],
out[n-1]±S)`, S=512 fast/205 slow, 1kHz tick — both confirmed on record), extracting the fundamental
harmonic's magnitude/phase after reaching periodic steady state, swept across a realistic amplitude
range at 21.5/23/25Hz. **Deliberately avoided hand-deriving/recalling a textbook describing-function
closed form** — a numerical sim on the actual discrete structure is safer under time pressure.

**Result — clear, and it doesn't match the observed law's shape**:
- **FAST step (512, R=512,000ct/s)**: phase lag stays essentially ZERO (<1°) up to **A≈3000-4000ct**,
  only becoming meaningful (>10°) above **A≈6000ct**. Realistic command amplitudes in this firmware are
  nowhere near this (see below) — **the fast step (used below ~16.6km/h) cannot be a phase-lag source
  at 22-26Hz at any realistic amplitude.**
- **SLOW step (205, R=205,000ct/s, active above 16.6km/h or hard turns)**: onset of meaningful lag is
  **A≈1500-2000ct** — MUCH closer to realistic amplitudes. `STATE.md`'s own established figure:
  `|gp-0x6b94|` (the governor's own input) peaks at **2,188ct on V101 (8×)** — right AT this onset
  threshold. **Genuinely borderline, not clearly zero.**
- **Tested the actual hypothesis (linear amplitude scaling with gain, `A(gain)=A_ref·gain/4`,
  A_ref=400ct@4× as a rough proxy — FLAGGED, not a measured 22-26Hz-specific amplitude)**: at THIS
  amplitude range (100-800ct across gain 1×-8×), **phase lag is flat at -0.57° for BOTH steps across
  the ENTIRE gain range — no shift at all, from either step.**
- **⇒ At realistic amplitudes, the governor slew limiter predicts essentially NOTHING across most of
  the gain range — it's not a smooth, gain-proportional lag source.** Its own physics (real, textbook,
  amplitude-dependent lag) only turns on sharply once amplitude crosses a THRESHOLD (~1500-2000ct
  slow-step) — and **a threshold-crossing nonlinearity does NOT naturally produce the observed clean
  LINEAR law starting from gain=1×** (it would show near-zero effect at low gain then an ACCELERATING,
  convex onset near the threshold, not a straight line). **This is a real argument against the
  governor's slew limiter being the PRIMARY explanation for the LINEAR shape specifically**, even
  though the underlying nonlinear mechanism is legitimate and worth keeping on the list (the SLOW-step
  borderline-threshold finding, right at V101's own measured 2188ct peak, is a genuine, precise,
  checkable fact — not dismissed, just doesn't explain the LINEARITY).

⚠ **The one assumption that could flip this**: I do not have a measured 22-26Hz-SPECIFIC spectral
amplitude of the delivered command at each gain level — only a rough P50-based proxy. If the REAL
22-26Hz component is substantially larger than ~100-800ct (e.g., if most of the ~2188ct peak IS
concentrated at this exact resonant frequency, which is physically plausible for a resonance), the
slow-step borderline case becomes MORE relevant, though the FAST-step-inert and
linear-shape-mismatch findings would stand regardless.

Script: `scratchpad/governor_describing_function.py` / `sign_check_and_governor_df.py` Part B.

## 9. 🛑🛑 DIRECTION QUESTION RESOLVED — r24/r26 DAMPS at 22-26Hz, confirmed via a sign-convention-free comparison

`route-v102` extracted r24's real, on-car delivered phase from EXISTING V102 data (no build needed):
`arg(csd(sgn(gp-0x6ada), rate_c))` at 22-26Hz = **+164.4° [+137.4, +172.9]** (hands-light, speed-matched
30-85km/h), rigorously validated (internal-consistency check: `rate_c` is `cs_ang`'s derivative, so the
two references must differ by exactly -90° — measured -83.5°, agreement to 6.5°, which ALSO rules out a
pairing/timing error; three null controls all far below the signal's coherence; a full synthetic
phase-recovery sweep through the chain, bias -0.0° scatter 0.2°). `b6` confirms r26 contributes ≲1% at
the rates where the resonance lives, so this is effectively the r24/r26 PAIR's phase. **Phase only —
Bussgang (hard-limiting a sign) destroys amplitude, so this gives direction, never magnitude.**

**Team-lead's method for the sign conversion — sidesteps this kit's own recorded sign-convention trap
by not re-deriving/re-applying a Re(Z) formula at all**: COMPARE r24's angle directly against
`gp-0x6b26`'s independently-anchored value (+137-139° vs wheel rate, already tied to a measured
+518/+565ct POSITIVE Re(Z) via V96's on-car comparator) — since BOTH are measured in the SAME reference
frame (vs wheel rate), checking which side of the ±90° boundary they're on is a frame-invariant,
arithmetic question, not an interpretive one.

**Computed the boundary arithmetic**: r24's ENTIRE CI [137.4°,172.9°] and gp-0x6b26's anchor
[137°,139°] are BOTH in the same (90°,270°) arc — **no flip anywhere in the CI, including at its lower
bound which nearly touches the anchor's own value.** ⇒ **r24/r26 DAMPS at 22-26Hz, confidently, matching
`gp-0x6b26`'s sign.** Script: inline in this session (boundary-arithmetic one-liner, not separately saved).

**⇒ Resolves what I'd flagged as unresolvable in §5: r24/r26's damping (confirmed, not assumed) CANNOT
be the mechanism pushing `f0` upward with gain — if its contribution grows with amplitude/gain, that
would push `f0` DOWN, the opposite of measured. By elimination, r24/r26 drops out as a candidate
EXPLANATION for the upward march (though it may still be usable as a LEVER in its own right — a
phase-shaping cave there, per the "empty socket" idea, now rests on a known baseline sign, though its
absolute magnitude is still unpriceable from this phase-only measurement).**

## 10. `route-stock`'s amplitude finding — real, but a critical unit-match question is still open

`route-stock` confirmed team-lead's amplitude prediction: **within V102 at FIXED 6× gain, `f0` moves
-0.99Hz between low (p50=70) and high (p50=152) command-amplitude strata, speed-matched, CIs disjoint.**
**The SAME sensitivity exists on STOCK** (statistically indistinguishable regression slope, +252 vs
+211 ct per e-fold) — meaning whatever produces this is baked into Honda's own 1× firmware, not
introduced by any build in this kit. Pooled regression: **the GAIN term becomes non-significant
(ΔR²=0.0009) once amplitude is in the model** — command amplitude, not the gain cell, accounts for
most of the observed law. An out-of-sample test (fit stock+V102, predict V100) misses by +0.54Hz, just
outside the CI — **a real ~0.5Hz residual survives that amplitude alone doesn't explain.**

🛑 **Checked this against my own already-run governor describing-function simulation (§8) — and found
a potential UNIT MISMATCH that needs resolving before the comparison means anything.** `route-stock`'s
amplitudes (70-152) are in **CAN `0x0E4` units** (openpilot's own command message); my governor
simulation's amplitude axis is in **internal firmware `gp-0x6b94` counts** (the governor's actual
input). These are plausibly DIFFERENT SCALES — I have not established the conversion factor between
them. **IF they are roughly 1:1 (unverified)**, `route-stock`'s observed effect happens at amplitudes
(70-152) far BELOW where my simulation shows any meaningful slew-limiting onset (~1500-2000ct slow
step, ~4000-6000ct fast step) — which would argue AGAINST the governor specifically, again. But I am
NOT reporting that as a conclusion — the unit question has to be resolved first (whoever holds the
0x0E4 DBC/decoder scale factor, likely `route-stock`/`route-v102`, can close this directly).

## 11. Recommended path forward, given the above
1. **Resolve the `0x0E4`-to-`gp-0x6b94` scale factor** — the one thing standing between "real effect,
   wrong mechanism" and "can't yet compare."
2. **`route-stock`'s own proposed discriminator (single route, no build, no gain confound — sustained
   high-command vs low-command episode at fixed everything else) is the cleanest way to nail this**,
   sidesteps the unit-matching risk entirely (compares f0 directly, not through my simulation), and
   costs one drive. Endorsed as the next concrete step over more desk modelling.
3. **D's sign at 22-26Hz remains the one number that needs V103** (r24/r26 is now closed without a
   build; D is not currently on any existing wire the way r24/r26 turned out to be).

## 12. 🛑🛑 Governor re-test at MEASURED (non-monotone) amplitudes — decisive, scale-invariant NO

Team-lead's own proxy for the governor's input amplitude, "command×gain": `465×1=465 · 253×4=1012 ·
98×6=588` — **NOT monotone (peaks at 4×)**. Re-ran the governor DF simulation at these exact values —
phase lag is <0.3° at ALL THREE, confirming the earlier "flat at realistic amplitude" finding. **Then
checked whether an unknown 0x0E4-to-`gp-0x6b94` scale factor `K` could rescue it**: swept K=1 to 30 —
**the ordering `465<1012>588` is preserved under ANY positive scaling (monotonicity is scale-invariant
by construction)**, so no `K` exists that makes this trajectory monotone. **⇒ Under this specific
proxy ("command×gain"), the governor-slew-DF mechanism CANNOT explain the monotone f0 law, for ANY
unit conversion — a decisive, scale-invariant negative result, not just "flat at my assumed
amplitude."** Caveat carried: this depends on "command×gain" being the right physical proxy for the
governor's actual input, which is itself uncertain (not the delivered `gp-0x6b94` signal directly).

Script: `scratchpad/governor_retest_measured.py`.

## 13. 🛑🛑 Model-shape refit attempted — FAILED harder than expected: not a phase problem, a magnitude one

Attempted team-lead's request (fit the model to the 3 measured f0 points, re-price q=1) via the
cleanest non-arbitrary route: solve the INVERSE problem — what flat phase shift `φ`, applied at q=1 to
my calibrated `L_total(f)`, would exactly retrodict each measured f0 (using stock=21.90Hz as the
`φ=0` reference)? This reuses the EXACT forward map already built and validated (§3c), just solved
backward — no new assumptions.

**Result: NO `φ` in the FULL ±180° range reproduces either point.** 4× needs `d(ReZ)=-262 ct·s/rad`;
6× needs `-459.6`. But the MAXIMUM possible `|d(ReZ)|` from a pure phase rotation of a FIXED-MAGNITUDE
carrier is bounded by `2·|L_total(f)|·C ≈ 216` (at 23.6Hz) and `≈173` (at 24.9Hz) — **both smaller than
what's needed, even at the extreme 180° rotation that flips the carrier's sign entirely.**

**⇒ This is a harder, more informative failure than the earlier 5-8× magnitude over-prediction (§1).
It shows the problem isn't "my phase assumption is wrong" — it's that my calibrated `|L_total(f)|`
itself is too SMALL to reach the required `Re(Z)` swing via ANY phase manipulation whatsoever.** Fixing
this needs a genuinely LARGER loop-gain magnitude at 22-26Hz than my model provides, and **3 data
points cannot responsibly determine how much larger without real risk of an arbitrarily-fitted, not
validated, number** — a 3-point fit to a model with enough new free parameters to match is calibration,
not confirmation. **Did not force a fit.** Recommended instead: for any FURTHER pricing, lean on
`route-stock`'s DIRECTLY MEASURED `Re(Z)`-vs-log(amplitude) slope (§10, +211 to +252 ct per e-fold) —
real data, not a theory-dependent conversion — rather than continuing to patch a model that has now
failed at two different levels.

Script: `scratchpad/model_shape_refit.py`.

## 14. Allpass cascade — filter-intrinsic design delivered; Hz-of-f0 NOT priced, per §13's finding

Designed a standard 2nd-order allpass (`H(z)=(a2+a1·z⁻¹+z⁻²)/(1+a1·z⁻¹+a2·z⁻²)`, complex pole/zero
pair at radius `r`, angle `θ=2πfc/fs`) — **`|H|=1` EXACTLY at every frequency by construction**
(verified numerically, no exceptions found). Swept `fc∈[18,24]Hz`, `r∈[0.70,0.95]`:
- **`fc=21Hz, r=0.90`**: phase spans **-128.9° (20Hz) to -174.3° (26Hz)** — substantial in-band
  authority — while the **0.3-3Hz command band moves only -1.6° to -16.1°** (growing with frequency
  within that band). Group delay in the command band: **~10-15ms** depending on `r` (tighter/higher-r
  designs give LOWER low-band group delay here, a real design tradeoff to note, not obvious a priori).
- **Cost**: 2 states per section (same class as the V103 biquad, ~4-6 multiplies/tick, ~0.06% of a
  1kHz tick per `cave-engineer`'s own budget note) — a 2-section cascade (~-360° total range, "N=2" in
  team-lead's language) costs roughly 2× that, still cycle-cheap. **GATE 1 needs 4 states of verified-
  free RAM for a 2-section cascade — NOT yet matched to specific cells** (cave-engineer's own shortlist
  has candidates; not confirmed against this specific design).

🛑 **Deliberately NOT converting this to "Hz of f0"** — §13 shows my loop model cannot support that
conversion honestly at present (the magnitude, not just the phase, is the wrong scale). The filter's
OWN properties (pole/zero, Q, group delay, cost) are reported as designed and GATE-1/cost-checked;
the Hz-delivered number is the one thing this file will NOT state without a model that has earned it.

Script: `scratchpad/allpass_design.py`.

## Related
[[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]] — the V103 biquad spec this
question grew out of; §9b-9d's `f′` amplitude-dependence work is the load-bearing prior result behind
§3's synthesis here.
