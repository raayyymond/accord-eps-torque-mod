# TRACE 2026-08-20 — the driver-side feedback path, end to end

Subagent trace for the orchestrator, task `driver-side-feedback`. Entry context: operator drove route
`0x9e` on V103 and reports **ratcheting at high steer angle rate** and **low-speed audible grinding
(grind #1)**, both present. Operator's own hypothesis: *"driver-side steering wheel inertia feedback
issue driving the ratcheting."* Program: `code.bin` (stock, fully analysed, 2086 functions), GhidraMCP
only, read-only calls. `gp = 0xFEDF8000`, `tp = 0xBF000`.

⚠ **Timeline note, stated plainly and not resolved here**: `docs/STATE.md`'s latest block (read this
session) says *"ON THE CAR: STOCK (V9b) … V103 is BUILT AND NOT FLASHED — the operator has deferred the
decision on it"*, which conflicts with this task's brief that V103 was just driven on route `0x9e`. I
have not adjudicated this — it may simply be that STATE.md has not caught up with a concurrent session.
Treated the brief as ground truth for "what happened," flagged for the orchestrator to reconcile.

---

## 1. Method

Read (in order): `CLAUDE.md`, `firmware-decompile` skill, then targeted memory: `accord-gp6b26-is-inertia-not-damping.md`,
`accord-gp6bbe-is-viscous-plus-dc-pedestal.md`, `reference-accord-c646c-shared-gain-not-lkas-only.md`,
`accord-engagement-amplifies-6-9hz-via-coulomb-relay.md`, `accord-fun3b8f6-coulomb-relay-proportional-to-command.md`,
`accord-c616c-never-raise-driver-torque-relay.md`, `accord-firmware-adds-torque-to-bar-engaged-at-low-speed.md`,
`accord-mode-27-is-a-second-engaged-column.md`, `accord-ratchet-scales-with-wheel-rate.md`,
`accord-ratchet-is-engagement-required.md`, `accord-aggregator-reaches-motor-via-gp6acc-bridge.md`,
`accord-two-ratchets-micro-is-the-779hz-line.md`, `accord-f0-crossover-is-the-endpoint.md`,
`accord-gp6752-is-negative-one.md`, and from my own agent-memory:
`reference_accord_gp6ad6_eight_terms_and_the_reachability_budget.md`,
`reference_accord_r24r26_driver_torque_lane_reZ_estimate.md`,
`reference_accord_driver_side_inertia_hypothesis_refuted_synthesis.md`,
`reference_accord_pump_hunt_comparator_probe_candidates.md`,
`reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved.md`,
`reference_accord_gp6bbe_angle_rate_path_traced_net_damping.md`.
Then `docs/STATE.md` lines 1–294 (latest block), `analysis-2020accord/build_v103_tva.py` (header + cal
list) to confirm what V103 actually changed, and `docs/STATE.md`/memory for V39/V42 lineage.

Then Ghidra, this session, fresh (not relayed):
- `decompile_function(0x3aa2c)` + `disassemble_function(0x3aa2c)` — the aggregator, **full instruction
  listing**, independently reproducing the r24/r26 mux/deadband structure the r24r26 memory describes,
  and finding the exact `cmovc`-dropout admission idiom for **every** lane (not just the one STATE.md
  names).
- `get_xrefs_to`/`search_instructions` for `gp-0x6bbe`, `gp-0x6b30` — producer/consumer census.
- `decompile_function(0x34a72)` — `gp-0x6bbe`'s producer (partially; superseded by the two prior-session
  memories found immediately after, which had already fully disassembled it — used those as the
  authoritative structure and cross-checked my own partial read against them, no conflict).
- `decompile_function(0x28ea6)` (too large to hold in context — extracted only the `gp-0x6b30` region via
  a saved-output grep) to characterize the sign-latch STATE.md flags.
- Lineage greps of `build_v*_tva.py` for every cal cell named below, and full read of `build_v39_tva.py`'s
  header (the cave source, not just its cal table) — this changed my read of the V39 null materially (§6).

---

## 2. The driver-side feedback map

Four physically-distinct driver-side quantities exist in this firmware and each has its own path back
into the motor command:

```
RAW TORQUE SENSOR  gp-0x4f60  (Sensor B, column torque)
   │
   ├─► gp-0x4f62 = 0.5×(T[n]−T[n−N]), N=cal(0xC6C42)=4     4-TAP DIFFERENCE (a genuine driver "jerk")
   │      │
   │      ├─► clamped ±5120 → r24, r26  (FUN_0003aa2c, THE AGGREGATOR — direct lane, see §3)
   │      └─► (same clamped value) → gp-0x6bbe's rate_error baseline chain (§4)
   │
   ├─► 0xC646C-scaled feedback, 6 readers (§5) — incl. FUN_00036682/FUN_00036828, the ONLY pair that
   │     reaches the motor: ~0.93 Hz IIR, clamp ±512, 5%-authority trim loop
   │
   ├─► low-pass EMA (α=cal 0xC6372=205/1024, τ≈5 samples) inside gp-0x6bbe's producer (§4)
   │
   ├─► gp-0x6a02 = gp-0x4f60×10/gp-0x4ebc (a torque RATIO) — gates gp-0x6bbe's FSM override
   │
   └─► FUN_0003b66a Branch B: 2× EMA(α=0.5) → gp-0x6b9a/gp-0x6ba6 (only -1dB/-21.6° @21Hz) — indexes
         gp-0x6bbe's magnitude-LERP AND feeds FUN_0003b8f6's Path-2 plant model (gated, §6 mentions only)

STEERING-WHEEL RATE  gp-0x6a56  (raw angle rate, UNFILTERED)
   │
   └─► gp-0x6bbe's rate_error = baseline − gp-0x6a56, taken RAW (no EMA/IIR on this operand at all) (§4)

MOTOR/RESOLVER RATE  gp-0x4f50 → gp-0x6abc  (NOT literal driver torque — motor/pinion side)
   │
   ├─► gp-0x6c2c (fast EMA-of-difference) → gp-0x6b26 = −K·accel  (§7, CLOSED, do not re-open)
   ├─► gp-0x6c2e (slow tap, same producer) → gp-0x6bbe's "combine" chain — CONFIRMED DEAD on this car
   │     (cal 0xC6499=1 routes LERP1/LERP4's index to gp-0x6ba6 directly, bypassing this branch)
   └─► FUN_0003b8f6's 3rd differentiator → "INERTIA" term, cal 0xC646E=1428, dissipative, 1-6% of clamp

DELIVERED MOTOR COMMAND  gp-0x6b98  (fed back into itself — the Coulomb relay, §6)
```

## 3. `r24`/`r26` — the genuinely driver-torque-derived pump candidate

Fully re-derived independently this session in `FUN_0003aa2c` (`disassemble_function`, full listing in
the tool transcript) — **matches the existing agent-memory trace instruction-for-instruction**, a third
independent confirmation of its structure:

```
pcVar10 = clamp(gp-0x4f62, ±5120)                                            @0x3aaac-c0

# R26  (0x3aa9c-0x3ab98)
a_smoothed = ((gp-0x69a4)[this tick] + gp-0x69a4[prev tick]) >> 1             2-tap boxcar, |H|=0.9997@7.79Hz
gainB = mux{ gp-0x6b5e==0 or sVar7!=1 : recompute path below | else: LERP(gp-0x6e30 table) }
  recompute: gainB = (gp-0x683c==0) ? [!bVar1 ? cal(0xC643E)=1536 : LERP] : cal(0xC6444)=512
r26 = clamp( gp-0x6752 × (((pcVar10 × gainB) >> 10) × a_smoothed >> 10), ±0x2000 )  @0x3ab78-98
    → gp-0x6adc

# R24  (0x3ab98-0x3ac58)
gainA = mux{ gp-0x671d!=0 : cal(0xC6442)=1024
           | gp-0x683c==0 : cal(0xC6446)=512   [LEVER B'S CAL — 0x3AA96 is the ld.bu DISPLACEMENT of the
                                                 "gp-0x683c" read itself; Lever B patches THIS byte to
                                                 repoint the whole gate, not a separate flag cell]
           | !bVar1(reversal counter < cal 0xC64FA) : cal(0xC6440)=2048
           | else : LERP(gp-0x6e38 table, "curve-A", peaks 3.000x at creep) }
D = cal(0xC61F6)=3                                                             deadband, ~3ct, negligible
r24_raw = deadband(pcVar10 × gainA >> 10, D)
r24 = clamp( gp-0x6752 × r24_raw, ±0x2000 )                                    @0x3ac16-58 → gp-0x6ada
```

Both multiply `gp-0x6752` **exactly once** — odd parity, sign load-bearing for both. `gp-0x6752 = −1`
[EVIDENCE, verified 3 ways per `accord-gp6752-is-negative-one.md`, independently re-confirmed by a sister
task the same day]. Both feed the aggregator **directly**, at ±0x2000 (8192) **each** — 8× `gp-0x6b26`'s
window at the **same summing node** (`FUN_0003aa2c`'s final sum → `gp-0x6b94`).

**Re(Z) estimate at 6–9 Hz** [BELIEF — closed-form, not an on-car measurement; method: piggyback the
measured whole-car `Z(f) = S_Tw/S_ww` cross-spectrum since r24/r26's own input **is** that same physical
torque signal]: with `gp-0x6752=−1`, **r24 = −431 to −1294 ct (PUMPING)** at gain G=1–3×, matching the
measured pump's sign at 6–9 AND 9–12 Hz, flipping to damping (matching measured recovery) at 12–31 Hz.
This is "the single best-evidenced additive-term candidate for the 6–9 Hz pump found in this
investigation" per my own agent-memory — but it does **not** close the whole measured pump (−3073 to
−4890 ct); r24 alone covers roughly 9–40% of it depending on G, and r26's own magnitude was never
separately computed (shares r24's now-resolved sign, so it *adds*, not cancels).

**No editable phase structure exists on this lane** — r24 is memoryless (no state), r26's only averaging
is the 2-tap boxcar on the *gain schedule*, not the differenced signal (functionally irrelevant at
7.79 Hz). **The only lever here is magnitude, not phase.**

## 4. `gp-0x6bbe` — re-derived this session, and its sign conclusion is now STALE

Two prior-session agent-memory files (`reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved.md`,
`..._angle_rate_path_traced_net_damping.md`) had already fully disassembled `FUN_00034a72`. My own partial
decompile this session corroborates them (raw `gp-0x4f60` low-pass EMA feeding a magnitude-blend, `gp-0x6752`
multiply at the very end) — no conflict, used their addresses as authoritative:

```
rate_error = baseline(FSM-gated torque/motor-rate composite) − gp-0x6a56[RAW, unfiltered]   @0x34e96
term1 = (rate_error_clamped(±12000) × K1[cal 0xD200C=43]) >> 7                              @0x34f20-32
term2 = clamp((term1 × speedLERP1(gp-0x6a5e; 0xD2834 Y=[541,639,653,551,439,439]/1024))>>10, ±666)  @..-5c
blendedMagnitude = LERP(|gp-0x6ba6| torque-composite; 0xCA4F4-family) blended α=cal(0xCA06C)=102/1024
term3 = (term2_clamped × blendedMagnitude) >> 14                                            @0x34ffa-08
gp-0x6bbe = clamp(term3 × gp-0x6752, ± speedLERP2(gp-0x6a62; 0xD20C0, FLAT 512))            @0x35010-c2
```

🛑 **`reference_accord_gp6bbe_angle_rate_path_traced_net_damping.md`'s "NET DAMPING" conclusion was
computed under an explicit `polarity(gp-0x6752)=+1` assumption** ("established" — written before the
2026-08-20 sign resolution). With `gp-0x6752` now known to be **−1**, that structural derivation
**flips** and is **stale** — it needs re-running, exactly like the D-term and the original r24/r26
estimate did.

Countervailing: on-car V92 telemetry (`accord-gp6bbe-is-viscous-plus-dc-pedestal.md`) measured
`gp-0x6bbe` vs **wheel rate** directly — flat gain ≈90 ct/(rad/s), phase −29°→+58° across 2–22 Hz,
called "viscous," and used to **refute** "same-signed as torque sensor ⇒ reinforcing." This is a real
on-car cross-spectrum, so whatever `gp-0x6752` truly was at measurement time is already baked into the
wire data — it does not itself need correcting. **But** I could not confirm, in the time available,
that this telemetry's sign convention is directly comparable to the structural "damping vs pumping"
question without the same kind of convention-verification exercise that resolved `gp-0x6752` (run a
known-sign synthetic test signal through the actual measurement script). **[OPEN — see §8.]**
No change proposed on this lane this session; K1/speedLERP1/clampBound are virgin if it is ever cleared.

## 5. Torque sensor consumer census — `0xC646C`, 6 readers (relayed, `reference-accord-c646c-...md`)

`FUN_00028ea6`(#1, forward blend) · dead gap(#2) · `FUN_0002b62c`(#3, no torque path, corrected 2026-08-07)
· `FUN_0002c478`(#4, dead output) · **`FUN_00036682`(#5, FEEDBACK, reaches motor, ~0.93 Hz IIR
α=6/1024, ±512 clamp, contributes ≈2.2% of the measured 21 Hz sensor→command transfer)** · `FUN_00036828`
(#6, feeds #5). Cal stock 891, on-car 3564 (4× since the V57-era `0xC6CD0` decouple went off the car at
the V38 rebase — see that memory for the still-open decouple recommendation, unrelated to this brief).

## 6. The Coulomb relay — `FUN_0003b8f6` (relayed, well-established; spot-confirmed structure only)

`ratio = clamp(polarity × gp-0x6abc × 12 / cal(0xC40BC), ±1.0)` saturates at 50 ct against this
function's own 13000 ct valid range ⇒ **`ratio ≈ sign(motor rate)` 99.62% of the time** (relay index
7.87 at the shipped `0xC40BC=600`). `FRICTION ∝ |model| × ratio`, where `|model|` is the **delivered
motor command** — i.e. this relay's amplitude scales with whatever gain the car is running, with **no
separate engagement flag anywhere**; that is the mechanism record already assigns to the measured
2.8–6.58× engagement amplification of 6–9 Hz (`accord-engagement-amplifies-6-9hz-via-coulomb-relay.md`).
Measured: **raising `0xC40BC` 600→6000 (de-relaying) made the 6–9 Hz band 2.3–6.58× WORSE** — "column
friction DAMPS this mode," a genuine damper by measurement despite the relay's own harmonic-injection
character. **Not a lever for this brief** — it is dissipative-signed (helps), already at its
measured-better value, and any further change is a friction/damping change the operator's own
constraint (§7 below) rules out considering.

`gp-0x6b30` (STATE.md's other cited "latching zero-output dropout" example, `FUN_00028ea6`) — traced
this session: it is a **sign-continuity latch on the FORWARD LKAS blend** (`iVar34 × gp-0x6b30_prev < 1`
⇒ force to zero on any sign reversal or zero-crossing tick), storing this tick's own output for next
tick's comparison. **Confirmed real, confirmed a genuine dropout — but on the command/forward path, not
driver-side feedback.** Out of this brief's scope; not pursued further.

**A structural finding beyond STATE.md's naming**: `FUN_0003aa2c`'s admission gate is **not** unique to
one or two lanes — **every one of the 11 input lanes into the aggregator uses the identical
`addi lo; addi -hi; cmovc 0,x,dst` hard-reject-to-zero idiom** (gp-0x6b62, gp-0x6b4c, gp-0x6ade,
gp-0x6bd0, gp-0x6bbe, gp-0x6b86, gp-0x6b26, gp-0x6ad4 all confirmed at their own addresses in the
disassembly). This is GATE-3-relevant for any future cave near this function: a lane that glitches past
its own admission window does not saturate, it **vanishes for that tick.**

## 7. `gp-0x6b26` (motor-rate inertia) — the operator's LITERAL hypothesis, CLOSED, do not re-open

Relayed from `reference_accord_driver_side_inertia_hypothesis_refuted_synthesis.md` (fresh-verified by
that session, not re-derived here): `gp-0x6b26 = −K·accel(gp-0x6c2c)`, and `gp-0x6c2c` is confirmed
**motor/resolver-rate** derived, not literal driver torque. Dissipative-signed both by closed-form
re-derivation and an inherited on-car comparator (+518/+565 ct Re(Z), same convention as the −3073…
−4890 ct pump ⇒ opposite sign, ~15–18% magnitude). **Closed both directions on-car**: RAISE (V91/V92,
×1.5, engaged-only) measured INERT twice independently; LOWER (V93/V94, ×0.167–0.75) **operator
ABORTED**, verbatim *"made the stuttering and grinding worse, by a lot… vibrated the entire car… not
safe to drive."* 🛑 **Do not propose touching `0xCBE74` in either direction.**

## 8. Lineage check — V39/V42 already tested zeroing this family, re-read carefully

`analysis-2020accord/build_v39_tva.py` header (full read, not just its cal table): V39 was a **cave**
(hook `0x3ac78`, 44-byte guard) that conditionally forced **r24 to zero** whenever `|internal LKAS mixer
term| ≥ 417 AND voted driver torque < 320` — a broad, not narrow, hands-off/LKAS-dominant condition.
Flashed 2026-07-19: **neither symptom improved.** `build_v42_tva.py`/`v42-flashed-...md`: r26 zeroed
(bundled with the state-4 governor fix) — **r26 falsified as the active ingredient**, but not isolated
with its own telemetry (credit went to the governor byte `0x454FE`).

🛑 **Confound found this session, not previously stated**: **V39 was flashed BEFORE V42's `0x454FE`
governor fix.** V39's null was measured on a car whose *confirmed, dominant, later-fixed* ratchet cause
(the state-4 governor magnitude-suppression substitution) was **still live and unfixed**. A small r24
contribution would very plausibly have been invisible against that much larger, still-present mechanism,
and **no comparator telemetry existed on either V39 or V42 to confirm r24/r26 were even meaningfully
nonzero during the specific episodes tested** — the exact "single threshold rung, no measured
distribution, no positive control" failure class this kit's own design law names. `0x454FE` is confirmed
carried forward on the current lineage (`accord-v42-ratchet-fix-lost-since-v53.md`, restored V80-on).
**This tempers but does not erase V39/V42's evidential weight** — see §9 for how it is used.

---

*Full disassembly transcripts (aggregator `0x3aa2c`, `gp-0x6bbe` producer context, `gp-0x6b30` region)
are in the session's tool-call history, not reproduced in full here for length; addresses above are
sufficient to reproduce every claim via `disassemble_function`/`get_assembly_context`.*
