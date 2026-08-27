---
name: reference_accord_gp6b4a_is_speed_derived_and_c616c_is_a_fault_monitor_not_decoupler
description: "DECOUPLER SEARCH CLOSED, THREE CANDIDATES, ALL REFUTED. (1) gp-0x6b4a is Honda's dormant LKAS/torque decoupler on gp-0x4f60, gated by cal(0xC616C) -- REFUTED: gp-0x6b4a's writer FUN_00026c80 never reads gp-0x4f60 (built from a REQUEST-arbitration accumulator + gp-0x6a62-indexed LERPs; gp-0x6a62 is SPEED-voted, not torque-rate, correcting a prior memory). (2) cal(0xC616C)'s real chain (FUN_00033d10->gp-0x6b78/6b76->FUN_0003405a->FUN_0002cc2a->gp-0x699e) is a SELF-CLOSING diagnostic/fault-confirmation loop -- gp-0x699e gates FUN_00033d10 itself; never reaches the assist output. (3) The 'shared iVar13, sign-flipped via gp_0x6752' theory -- REFUTED pre-send by cal(0xC63CC)=0. The gp-0x6b4a injection gate at FUN_000352b4@0x354f6 is a NO-OP (always passes; corrected own backwards hand-derivation of cmovnc via Ghidra's decompile) -- but its effect is entirely INTERNAL to gp-0x6b86's own computation, the exact lane V104 proved gets rejected at the junction, so the sign question is MOOT regardless of resolution. ARCHITECTURAL SYNTHESIS: no decoupler exists likely because torsion-bar contamination is INHERENT to the sensing principle, not a firmware gap -- Honda's real answer is the closed-loop PID; contamination, if real, NESTS inside the already-measured loop gain rather than being separate. Adjudicates the H(s) handoff's reverse-causality kill (its e4~angle argument doesn't discriminate; the real discriminator, partial coherence gamma^2(e4,bar|angle), is UNRUN) and finds the reverse-causality dataset has ZERO gain variation (r73/75/76 all at identical 4.000x)."
metadata:
  type: reference
---

# `gp-0x6b4a` and `cal(0xC616C)` — two negative results, both EVIDENCE-grade

Traced 2026-08-22, task `compensator` (team-lead redirect: operator hypothesized LKAS motor torque
contaminates the driver-torque sensor `gp-0x4f60`, and a dormant decoupler might exist at `gp-0x6b4a`,
gated by `cal(0xC616C)`, currently 0). Both specific predictions checked by fresh decompile and refuted.
Full report sent to team-lead via SendMessage, 2 messages.

## [EVIDENCE] `gp-0x6b4a`'s sole writer (`FUN_00026c80`) never reads the torque sensor

Fresh `decompile_function(0x26c80)`, whole function read. Tail:
```c
iVar13 = gp_0x3d80[persistent accumulator] + iVar11[slew-limited term] + uVar42[2nd LERP term];
gp_0x6b4c = gp_0x3d88 + gp_0x6752*((iVar13*cal(0x73cc))>>10);   // SIBLING output, clamped +-0x2800
gp_0x6b4a = clamp(iVar13, +-0x6400);                             // stored directly, shadow gp-0x4cd2
```
`gp-0x4f60` (raw driver torque sensor) does not appear anywhere in `FUN_00026c80`. `gp-0x3d80` is itself
the sum of a 10-slot dispatch at the top of the function (Honda's own request/priority state machine,
matching prior "11-channel mixer/classifier" characterization — the function also writes `gp-0x67ab`,
`gp-0x67ac`, `gp-0x6b4c` per the same decompile). `iVar11` and `uVar42` are both indexed on `gp-0x6a62`,
slew step `cal(tp+0x7194)`, LERP table `tp+0x7700-0x770c`.

## [EVIDENCE, corrects a prior-session BELIEF] `gp-0x6a62` reads as SPEED-VOTED, not torque-rate

`gp-0x6a62`'s writer, `FUN_00041eec` (2 real `st.h` sites, `search_instructions` confirmed), decompiled
fresh. It fault-checks a rate quantity via `FUN_0004613e` (known diagnostic/fault-record function), then
reads `gp-0x6a5e` (the kit's own established **voted vehicle speed, x64 ct/km/h**) as a reference value
and selects the CLOSEST of 4 candidate readings (`aiStack_4c[0..3]`) to it — a classic redundant-sensor
voting pattern. The selected/voted result is stored to **`gp-0x6a62`, alongside `gp-0x6a5e` itself and
`gp-0x6a64`**, all three written together at function end.

⇒ `FUN_00041eec` is a wheel/vehicle-speed voting-and-plausibility routine. **This contradicts the
prior-session characterization of `gp-0x6a62` as "torque-rate-indexed"**
(`reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md`, never independently
closed there — flagged open, now resolved differently). [BELIEF on the EXACT physical unit of
`gp-0x6a62` specifically — which candidate/fallback path is live at the operating point not fully hand-
decoded — but EVIDENCE that the function's whole shape is speed-voting, not a torque derivative.]

⇒ **`gp-0x6b4a` reads structurally as a SPEED-SCHEDULED arbitration/request term** — not torque-sensor-
derived, not obviously LKAS-command-derived either (no LKAS-command read found in its chain this
session). A third category from either candidate the redirect hypothesis offered.

## [EVIDENCE] `cal(0xC616C)`'s real chain is a fault monitor, not an assist path — and does not reach `gp-0x6b4a`

`search_instructions(operand_pattern="716c")`: 8 raw hits, 5 excluded (branch-target text collisions,
unrelated larger immediates `0xb716c`/`0xc716c`). **The 3 real reads of `tp+0x716c`(=`0xC616C`) are all
inside `FUN_00033d10`**, called only by `FUN_00022ca0`. Decompiled fresh:
- Reads `gp-0x4f60` (torque sensor) directly, first line.
- Gated by a large OR of disable conditions.
- Computes a Coulomb-relay-shaped term (sign-selected between `+cal(0xC616C)`/`-cal(0xC616C)` by torque
  sign, zeroed when a slew counter is 0) and stores it to **`gp-0x6b78`** and **`gp-0x6b76`** — cells not
  previously named in this kit's record.

`gp-0x6b78`/`gp-0x6b76`'s only real reader (2nd `search_instructions` pass, one `6b76` hit excluded as a
`bne 0x0006b766` branch-target text collision — the documented trap, live example) is **`FUN_0003405a`**,
decompiled fresh:
- Uses `gp-0x6b76`/`gp-0x6b78` purely as **threshold conditions** feeding a boolean.
- Combines that into a **state-machine transition** (`gp-0x3820`, 0-7 states, explicit gated-`goto` block).
- Passes the result to **`FUN_00025c32`** — already on this kit's record, tied to `cal(0xC64FA)`, a
  **DTC/fault-gate cell** (`reference_accord_fun46ea6_dtc_gate_pid_flat_table_and_c64fa_census.md`).
- Outputs `gp-0x67e8`/`gp-0x67e9` — not any cell in the aggregator, PID, or reference chain.

**Full chain**: `cal(0xC616C) → FUN_00033d10(reads gp-0x4f60) → gp-0x6b78/gp-0x6b76 → FUN_0003405a
(state machine) → FUN_00025c32 (DTC-gate-adjacent) → gp-0x67e8/gp-0x67e9`. Structurally this is a
**torque-sensor plausibility/fault monitor**, matching `0xC616C`'s standing `"NEVER-RAISE"` comment for
a DIFFERENT reason than contamination-doubling: raising it changes a fault detector's sensitivity, not
the assist chain's gain. **Neither `gp-0x6b78`/`gp-0x6b76` nor `gp-0x67e8`/`gp-0x67e9` connect to
`gp-0x6b4a`, `FUN_0003aa2c` (aggregator), `FUN_0003a382` (PID), or `FUN_00037fe6` (reference producer)
anywhere traced this session.**

## Verdict
**`gp-0x6b4a` is not Honda's dormant LKAS/torque decoupler, and `cal(0xC616C)` does not gate any signal
reaching the assist chain.** Both were the concrete, checkable predictions of that specific hypothesis,
and both failed on direct decompile. **Does NOT settle whether LKAS-motor-torque-on-sensor contamination
is physically real** (a claim about the sensor/column, independent of whether firmware labels a fix for
it) — only that this specific candidate mechanism isn't it. `docs/HANDOFF-2026-08-22-hs-identification-
and-five-instrument-defects.md` is the place to look for the physical-contamination question; not fully
read this session.

## Open / unresolved
- `FUN_00022ca0` (common caller of `FUN_00033d10`/`FUN_0003405a`)'s own callers/task-rate — `get_function_
  callers` returned an anomalous `"No callers found for function: null"` rather than a clean empty list;
  not resolved, not blocking.
- `gp-0x6a62`'s exact physical unit (which of the 4 voted candidates, what its non-voting fallback path
  represents) — not fully hand-decoded.
- `FUN_0002cc2a`'s other outputs (`gp-0x6811`, `gp-0x6813`, `gp-0x67e7`, `gp-0x67ea`, `gp-0x6829`,
  `gp-0x6827`) — not traced further given the loop below already closes; residual gap if a future session
  wants it airtight.

## 🛑🛑 ADDENDUM, same session — THE LOOP CLOSES ON ITSELF: `gp-0x6b78`/`gp-0x6b76` do NOT reach the
assist output at all, confirming the NO-GO one more hop deep

`gp-0x67e8` (my dead-end above) has 5 real external readers, **all inside ONE function: `FUN_0002cc2a`**
(`search_instructions` confirmed; excluded 3 branch-target text collisions in unrelated `FUN_00066ab6`).
Decompiled fresh: a large multi-stage state machine (persistent bytes `gp-0x3ca4`-`gp-0x3caa`, `gp-0x3c99`),
gated in part by **`gp-0x67fa`** (the same state register gating `FUN_0003a382`/`FUN_0003aa2c`), reading
`gp-0x67e8` as a transition condition. **Its output is `gp-0x699e` — a 0-1024 ramp/envelope.**

🛑🛑 **`gp-0x699e` is EXACTLY the gate variable at the top of `FUN_00033d10`** (`uVar25=gp-0x699e;
bVar1=uVar25<0x401;` — the enable condition for the whole Coulomb-relay-on-`gp-0x4f60` computation this
trace started from). **The loop closes on itself:**
```
FUN_0002cc2a (gp-0x67fa-adjacent state machine) --writes--> gp-0x699e (0-1024 ramp)
   --gates--> FUN_00033d10 (reads gp-0x4f60, x cal(0xC616C)) --writes--> gp-0x6b78/gp-0x6b76
   --read by--> FUN_0003405a (fault state machine) --writes--> gp-0x67e8 --read by--> FUN_0002cc2a
```
**Self-contained diagnostic/detection loop. No exit found toward `gp-0x6b86`, `gp-0x6b94`, `gp-0x6ad4`,
`gp-0x6ad6`, or `gp-0x6b98` in any of the 4 functions now fully decompiled this session.**

[BELIEF, from structure] Given the ingredients (torque-sign relay vs magnitude threshold, a slow
multi-second ramp, gating tied to the SAME state register governing the whole assist chain, routing
toward a DTC-gate-adjacent function) — **this reads as Honda's own driver-override / torque-sensor-
plausibility CONFIRMATION TIMER** (debounce logic deciding "has the driver taken over" / "is this fault
confirmed"), a condition-evaluation subsystem, not a torque term summed anywhere.

`cal(0xC616C)`: 16-bit unsigned (`ld.hu`, 3 real sites, all in `FUN_00033d10`). Stock value **independently
re-confirmed via `read_memory`** = 0 (raw bytes `00 00 ae 0f`). Functionally dormant at stock regardless of
gating (the relay's own magnitude IS the cal cell; disabled branch stores a `0x7FFF` sentinel instead).

## Overall verdict, both candidates from the operator's LKAS-contamination reframe
**Both `gp-0x6b4a` and the `cal(0xC616C)`/`FUN_00033d10` chain are refuted as delivery-path decouplers.**
Neither reaches the assist output. No third candidate found this session.

## 🛑🛑 ADDENDUM — adjudicating `docs/handoffs/2026-08/HANDOFF-2026-08-22-hs-identification-and-five-instrument-defects.md`;
WHY no decoupler exists, and how contamination (if real) nests inside the already-measured loop gain

[BELIEF, architectural reasoning] A torsion bar measures the DIFFERENTIAL twist between the driver-input
side and the motor/rack-output side. Whenever the driver's hand impedance is finite (always), motor-side
torque MECHANICALLY, UNAVOIDABLY shows up in that differential — not a firmware oversight a decoupler
subtracts away, but the sensor's operating principle. You cannot cleanly subtract it without the exact
mechanical transfer function AND the instantaneous hand impedance (grip/driver/frame-dependent) —
getting the subtraction wrong is at least as dangerous as leaving it alone. **This is very likely WHY the
two-candidate trace above found nothing — there probably isn't supposed to be a discrete decoupler.**
Honda's actual answer is the closed-loop PID already mapped
([[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]]): rather than
subtracting contamination at the sensor, the loop is tuned to be stable and reject slow disturbances
despite reading a signal that inherently includes some of its own motor's contribution.

🛑 **The two hypotheses (compensator-loop, sensor-contamination) NEST rather than compete.** If sensor
contamination is real, it is very plausibly one of the physical channels producing the loop gain `L(f)`
already measured on-car (route `0x85`/`0x95`, `0.630∠−17.2°` at 6-9Hz, near-instability) — a contaminated
sensor reading means the loop regulates toward a target partly a function of its own output, which is
structurally a form of positive feedback INTERNAL to the loop, not an independent effect on top of it.

**Consequence for V104's "junction lanes are rejected" finding**: that result (85% raise on `gp-0x6b86`,
no felt change) is about a disturbance summed AT THE JUNCTION, downstream of the sensor — the loop's own
feedback path reads it and pushes back. Sensor-path contamination is architecturally different — it
corrupts the loop's ground truth, was never "inside the junction," so the rejection result doesn't
predict it would be treated the same way, but there is also no discrete injection point to decouple AT.
Practical consequence: **the only lever that changes the absolute magnitude of motor torque (and hence
its unavoidable mechanical footprint on the bar) is `0xC6CD0` itself — already the one variable proven
(same route 0x85/0x95 work) to move the loop's own `|κG|`.**

## Adjudicating the handoff's "reverse causality" kill — suggestive, not dispositive; a real discriminator identified, not run
The handoff's `γ²(e4,bar)` reverse-causality argument rests on 3 pieces. [BELIEF] Piece 1
(`γ²(e4,ANGLE) > γ²(e4,bar)`) does NOT discriminate the two hypotheses — openpilot's own controller
computes `e4` from measured ANGLE/curvature error, not torque, so `e4~angle` coherence exceeding
`e4~bar` is expected regardless of whether motor-torque contamination exists. Piece 2 (near-zero phase,
"a same-frame algebraic relation, not actuation") is the load-bearing one but not fully dispositive — a
STIFF MECHANICAL COUPLING (which a torsion bar inherently sits inside) could also show near-zero phase
at 6-9Hz; the session didn't test this alternative.

## 🛑🛑 ADDENDUM 2 — the gp-0x6b4a injection gate at FUN_000352b4@0x354f6, executed on the decompiled C;
the "shared-source decoupler" hypothesis raised and REFUTED in the same session

Team-lead relayed a claim (from `ceiling-trace`, later corrected by both) that `gp-0x6b4a` is written by
the SAME producer as `gp-0x6b4c` ("the LKAS lane") — true — and speculated it could be a sign-opposed
decoupler on the torque sensor. Traced fully via `decompile_function(0x352b4)` + full raw disassembly of
`FUN_00026c80` (`0x272f0-0x277fe`).

### [EVIDENCE, decompile] The injection gate at 0x354f6 is a NO-OP — always passes, not always-zero
```c
iVar33 = gp_0x6b4a * bool((gp_0x6b4a+25600) <u 51201) + clamp(gp_0x4f60,+-8192);
```
`gp-0x6b4a`'s own producer clamps it to exactly [-25600,+25600], so the bias+compare is ALWAYS true for
its full legitimate range. **I first hand-derived the OPPOSITE conclusion from the raw `cmovnc` bytes
(misread which branch the condition selects) — caught by pulling Ghidra's own decompile rather than
trusting the hand derivation.** `gp-0x6b4a` is added with coefficient +1, no cal multiply, every tick.

### 🛑 [EVIDENCE — self-correction, caught before reporting] `cal(0xC63CC)=0` kills the "shared source,
opposite sign" decoupler hypothesis
`gp-0x6b4a = clamp(iVar13,+-25600)` (raw, unscaled). `gp-0x6b4c = clamp(gp-0x3d88 + gp_0x6752*((iVar13*K)
>>10), +-10240)`, K=`cal(0xC63CC)`. **`read_memory(0xC63CC)`=0** (matches `docs/BUILD-LINEAGE.md`'s
"0xC6194 DEAD TWICE... reaches only gp-0x6b4a... (0xC63CC=0)"). With K=0, the `iVar13`-dependent term in
`gp-0x6b4c`'s formula is identically zero — **`gp-0x6b4c` in stock firmware is driven PURELY by the
persistent accumulator `gp-0x3d88`, with ZERO instantaneous dependence on `iVar13`/`gp-0x6b4a`.** The
"gp-0x6b4a ∝ −gp-0x6b4c" hypothesis (which looked compelling before this check) is REFUTED.

### [EVIDENCE, full raw disasm] `gp-0x3d88` and `gp-0x3d80` are structural cousins, not the same signal
Both accumulated in the SAME 10-slot REQUEST-arbitration loop, SAME per-slot gate (`tp+0x5118[slot]!=0`),
DIFFERENT source arrays:
```
gp-0x3d88 = SUM(gate) of gp-0x62b0[slot]   -> feeds gp-0x6b4c (LKAS lane)
gp-0x3d80 = SUM(gate) of gp-0x6298[slot]   -> ONE of gp-0x6b4a's 3 components
```
Whether `gp-0x62b0[]`/`gp-0x6298[]` carry correlated values depends on THEIR OWN writers — not traced
(a further hop, upstream request-builder code). `gp-0x6b4a`'s other 2 components (a `cal(0xC6194)`-stepped
slew, and a `gp-0x6a62`-indexed LERP — `gp-0x6a62` established SPEED-VOTED above) are separate again.

### Verdict: NOT confirmed (A) decoupler, NOT (B), genuinely (C)-leaning but not closed — AND a
structural fact that matters regardless of how the sign resolves
The addition at `0x354f6` happens BEFORE the LERP table walk that determines the friction/gain lookup
feeding `gp-0x6b86` — i.e. **entirely INTERNAL to `gp-0x6b86`'s own computation.** `gp-0x6b86` is exactly
the lane V104's 85% raise already measured REJECTED at the junction (no felt/symptom change). **This
addition does NOT reach the PID's own `ERR` computation** (which reads `gp-0x4f60` directly, unmodified).
⇒ **Even if `gp-0x3d80`/`gp-0x3d88` turn out correlated via their source tables, this term's effect is
scoped inside the SAME junction-rejected lane — not upstream of where the loop closes.** This holds
regardless of the sign question's eventual resolution.

🛑 **The clean discriminator: PARTIAL/CONDITIONAL COHERENCE `γ²(e4, bar_torque | angle)`** — coherence
between command and bar torque after removing what's linearly predictable from angle. Residual well above
null ⇒ a direct e4→bar channel exists (contamination-consistent); collapses to null ⇒ confirms the
angle-mediated-common-cause explanation. **Not run in the handoff, and not run by me** (needs
`rlog-tools/plant_*.py`/`studies/loop-causality/loop_op_t1_coherence.py` applied to existing captures — telemetry DSP, outside
this session's firmware-decompile scope).

## [EVIDENCE, checked from build scripts myself] The existing reverse-causality dataset has ZERO gain variation — cannot test the gain-scaling prediction
`grep 0xC6CD0 builds/v80_v107/build_v88_tva.py builds/v80_v107/build_v89_tva.py`: **r73(V88)=3564, r75/r76(V89)=3564 — all three routes
behind the handoff's `γ²(e4,bar)`=0.085/0.138/0.280 are at the IDENTICAL 4.000x gain.** The observed
spread is exposure/condition variation, not a gain effect. A genuine test of "does contamination scale
with `0xC6CD0`" needs the same computation on `r97`(stock,1x) vs 6x/8x routes — blocked by two hazards
already on record: 427's source cell changes by build (`r97` doesn't carry `gp-0x6b94`/`gp-0x6b98` on 427
the same way — described as "Honda's own MOTOR_TORQUE, approx 0"), and `r95`(8x) is confounded (Lever B
disarmed, no >80km/h exposure).

## Related
[[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]] — the broader
compensator-loop investigation this trace forked from. [[reference_accord_fun3a382_gp6ad6_model_closure_
and_bias_clamp_correction]] — source of the now-corrected "gp-0x6a62 = torque-rate" belief.
[[reference_accord_fun46ea6_dtc_gate_pid_flat_table_and_c64fa_census]] — `FUN_00025c32`/`0xC64FA`
context this trace reused.
