---
name: reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain
description: "FUN_0003aa2c's full gp-cell enumeration (fresh decompile) shows r24/r26 read ZERO LKAS-domain inputs; gp-0x6b4c is the ONLY LKAS-sourced lane of 11. No V57-style cal fork is possible for r24's dtorque(gp-0x4f62) input because the torque sensor gp-0x4f60 is a single physical measurement of driver+motor-reaction torque combined -- there is no earlier tap that separates them, unlike 0xC646C's 6 independent read sites. gp-0x671d's producer FUN_00041d56 traced to inputs gp-0x501c/gp-0x4fd8, both RESOLVER/FOC domain (not LKAS) -- closes an old open question. gp-0x67fe's producer confirmed FUN_0003bd7c (4 st.b sites) and task-1 call order shows gp-0x67fe/gp-0x6806/gp-0x69b0 are all FRESH by FUN_0003aa2c's point in the 1kHz tick even though FUN_0003aa2c doesn't read them -- a code-level (not cal-level) LKAS gate is structurally feasible but unexplored. gp-0x4f62's producer FUN_0007e74a has no EMA/IIR anywhere -- the 'dirty derivative' low-pass does not exist in stock; D=4 (0xC6C42) sets only the differencing window, confirmed sole reader by 2 independent methods."
metadata:
  type: reference
---

# r24/r26 LKAS-decoupling feasibility -- traced 2026-08-01 for team-lead's "grind #2" investigation

Task: after V62 (flew, fixed the 20.9 Hz LKAS-engaged grind by doubling r24/r26's gain) reportedly
introduced a NEW ~38-46 Hz grind at low speed under significant MANUAL steering (LKAS-independent), find
whether r24's gain can be made LKAS-conditional -- either a V57-style cal fork, or an existing LKAS-state
signal already reachable inside `FUN_0003aa2c`. Builds on
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] and
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] (the V57 precedent).

## 1. Fresh full decompile of FUN_0003aa2c -- complete gp-cell enumeration [EVIDENCE, fresh 2026-08-01 decompile]

Every gp-relative cell FUN_0003aa2c reads: `-0x6b62`(return-centre), `-0x6b4c`(LKAS, the ONLY
LKAS-command-domain cell), `-0x6ade`(feedforward, dead), `-0x671a`(state ramp 0-5), `-0x4f62`(dtorque),
`-0x6b5e`(r26 zero-force gate), `-0x683c`(dead gate), `-0x6ac0`(motor resolver rate, LERP index for BOTH
r24/r26), `-0x6e22..-0x6e40`(static LERP tables, rebuilt from ROM by `FUN_0003ad74` keyed on mode byte
`gp+0x63fd`), `-0x69a4`(r26's avg-slope input), `-0x3670/-0x3672`(internal filter state), `-0x671d`(r24's
event-counter gate), `-0x67ac`(narrow/full path selector), `-0x6ad4`(resonance, eliminated V56),
`-0x6b26`(friction), `-0x6bbe`(boost), `-0x6bd0`(damping), `-0x6b86`(magnitude), `-0x6752`(polarity,
shared), `-0x4ce0`/`-0x6b94`(shadow-lockstep output pair), `-0x257c`/`-0x3e80`/`-0x3e78`(per-task DTC
counter, diagnostic only), `-0x6adc`/`-0x6ada`(r26/r24 telemetry stores). **None of these is
LKAS-engagement-domain except `gp-0x6b4c` itself.** In particular `gp-0x6806` (STEER_CONTROL_ACTIVE
source), `gp-0x6807` (STEER_STATUS), `gp-0x67fe` (LKAS engage-SM state), `gp-0x69b0` (LKAS forward ramp)
are ALL ABSENT from this function -- confirmed by reading the full decompile text, not by an xref null.

**Structural confirm: `FUN_0003aa2c` itself is gated, not unconditional.** Its caller `FUN_0002214a`
(0x2291e) only invokes it when `r22 = (gp-0x67fa-derived one-hot state) & 0xC30 != 0` (set at 0x2269e,
the SAME gate used immediately before for `FUN_0003a382`/resonance). This refines "runs unconditionally
every 1kHz cycle" (used loosely in older memory) to "runs when the ECU one-hot state is in mask 0xC30" --
consistent with [[reference_accord_0x930_masks_are_state_not_phase_settled]].

## 2. Q1b -- of the 11 aggregator lanes, exactly ONE carries LKAS [EVIDENCE, reproduces existing memory]

`gp-0x6b4c` (clamped +/-0x2800) is the sole LKAS-sourced summand of the 11
(see [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] for the full list). r24/r26 do not
read it, directly or indirectly, anywhere in their own computation.

## 3. Q1c -- LKAS-engagement indicators ARE fresh at FUN_0003aa2c's point in the tick, but nothing reads them there [EVIDENCE]

Full disassembly of `FUN_0002214a` (task 1, 1kHz) shows the call ORDER before `FUN_0003aa2c`@0x2291e
includes, in program order: `FUN_0003bd7c` (@~0x2224a, the EPS engage-SM function, SOLE writer of
`gp-0x67fe` -- 4 `st.b` sites freshly confirmed this session: `0x3bdb8`, `0x3be4e`, `0x3be5a`, `0x3be7a`,
resolving the "producer UNRESOLVED" note in
[[reference-accord-engage-sm-full-dispatcher-and-trump-exits]]); `FUN_00028ea6` (@0x22522, arbitration --
writes `gp-0x6806`'s ramp-FSM phase per [[reference_accord_gp6806_phase_flag_and_dead_writer_split]] and
snaps `gp-0x69b0` AUTHORITY on ramp-complete); `FUN_00026c80` (@0x225f6, the mixer -- writes BOTH
`gp-0x6b4c` and `gp-0x67ac`). **All three run strictly before `FUN_0003aa2c` in the same 1kHz cycle**, so
`gp-0x67fe`, `gp-0x6806`, and `gp-0x69b0` are all FRESH (this-cycle) values by the time r24/r26 execute --
but `FUN_0003aa2c` reads none of them (section 1). `gp-0x67fe`'s wide reader set (40 hits,
`search_instructions`, includes `FUN_00028ea6`, `FUN_00034350`/damping, `FUN_0003a382`/resonance,
`FUN_0003d4a2`/motor-off) confirms it is the LKAS engage-SM's own state flag (values gated `∈{1,2}` = assist
up, `==2` = a specific "trump"/override condition per [[reference-accord-engage-sm-full-dispatcher-and-trump-exits]]),
i.e. genuinely LKAS-engagement-domain, not generic EPS-assist-on.

**Practical consequence**: an LKAS-conditional r24 gain is NOT achievable as a pure calibration edit --
`FUN_0003aa2c` (or its call path) would need NEW instructions inserted to read `gp-0x67fe` (or `gp-0x6806`)
and gate/select the gain arm on it. This is structurally straightforward (the value is already computed
and fresh) but is a CODE edit in the 1kHz path, this kit's higher-risk class (per CLAUDE.md, code caves are
the only bricking class on record). Not designed or characterised further this session per the brief's
"don't propose a build" instruction.

## 4. Q2 -- no V57-style fork exists for gp-0x4f62 (r24's dtorque input) [EVIDENCE + physical reasoning]

V57's decoupling worked because `0xC646C` had SIX independent static READ SITES of one shared cal
constant, one of which (`FUN_00028ea6`'s CAN-setpoint path) was purely LKAS-forward-domain -- so the fix
was "give that one site its own cal word." `gp-0x4f62` has no analogous structure: it has exactly ONE
producer (`FUN_0007e74a`, see below) and traces to exactly ONE upstream signal, `gp-0x4f60` (the physical
torsion-bar/strain-gauge torque sensor). The sensor sits on the shaft between the driver's hands and the
point the motor applies assist torque -- it physically sums driver hand torque AND motor reaction torque
into one scalar. **There is no firmware tap point upstream of `gp-0x4f60` that isolates one component from
the other**; this is a physical/architectural fact about where the EPS sensor lives, not a firmware
limitation that a different address or a second read site could route around. Confirmed: `gp-0x4f62` has
exactly one producer and its inputs (`gp-0x4f60`, plus internal delay-buffer state) trace to nothing
LKAS-domain (see #5).

## 5. Q3a -- 0xC6C42 (delay D) re-verified, 2 independent methods, and it DOES feed gp-0x4f62 directly [EVIDENCE]

`read_memory(0xC6C42)` = `04 00 00 00` -> D=4, matches prior record. `search_instructions` on operand
"7c42": 6 raw hits, 2 are branch-target-address text collisions in `FUN_0007b022` (excluded, same false-
positive class as elsewhere in this kit), the other 4 are `ld.hu 0x7c42,tp,rX` at `0x7e7d8/0x7e7f6/0x7e7fa/
0x7e800`, all inside `FUN_0007e74a` -- `truncated:false` over the full 183,429-instruction corpus. **Second
method, raw Python byte scan of the whole 1,048,576-byte stock image** for the LE16 pattern `43 7c` (the
`hw2=disp|1` encoding for `ld.hu`/`ld.h`, per [[accord-gp4f60-two-encodings-enumeration-trap]]): exactly 4
hits, at file offsets `0x7e7da/0x7e7f8/0x7e7fc/0x7e802` (= instruction-start minus 2, consistent with the
Ghidra addresses). **Zero additional hits anywhere in the image for this encoding -- sole reader
`FUN_0007e74a` confirmed by 2 independent methods.** A parallel raw scan for the un-offset `42 7c` pattern
(the theoretical `ld.w`/`st.w` encoding, no +1) found 130 candidate byte pairs scattered through the image,
NONE of which `search_instructions` recognizes as a real instruction operand (Ghidra's own complete
183k-instruction analysis would show any real `ld.w tp+0x7c42` reference as operand text "0x7c42", exactly
as it does for the `ld.hu` form's effective address -- and none appear). This is strong circumstantial
evidence the 130 are coincidental data bytes, not code, but **not individually adjudicated hit-by-hit this
session** -- flagged open rather than asserted closed, per this kit's own standard for a load-bearing zero.

**D directly feeds gp-0x4f62 -- it's not a separate lever, it's a parameter of gp-0x4f62's OWN producer.**
`FUN_0007e74a` computes `gp-0x4f62 = 2*(torque[n] - torque[n-D]) / dt[n-D]`, a D-tick finite difference over
an 8-slot circular buffer (both torque samples and an elapsed-tick accumulator are buffered). D sets the
differencing WINDOW, i.e. the derivative's transport lag / phase, exactly as
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]]'s session-2 addendum already
characterised it (D: 4->2 halves the lead's lag, held as a V63 fallback phase lever).

## 6. Q3b -- NO low-pass/EMA exists anywhere on the dtorque signal, at the producer OR at r24's consumption [EVIDENCE, decisive negative]

Full decompile of `FUN_0007e74a` (gp-0x4f62's producer): the ONLY signal processing is the D-tick finite
difference above (section 5) plus a small state-transition table (`gp-0x4e9e`, 4 entries) used to compute
elapsed real ticks between samples for the `dt` denominator -- there is no IIR/EMA/state anywhere in this
function beyond the raw difference. `r24`'s consumption in `FUN_0003aa2c` is a straight
`clamp(dtorque,+/-5120) * gain_q10 >> 10` multiply against a STATIC gain (either a cal override or a
motor-rate-indexed LERP table lookup) -- no time-domain filtering downstream either. **A "dirty derivative"
low-pass that would keep the 21 Hz lead-shape while attenuating ~40 Hz does NOT currently exist in this
firmware; it would have to be newly ADDED (a code-cave-class change), not tuned via any existing cal.**
This is the single most decisive negative result for the team-lead's Q3b hypothesis.

## 7. gp-0x671d's producer FUN_00041d56 traced -- RESOLVER/FOC domain, not LKAS [EVIDENCE, closes an old open item]

`FUN_00041d56` (SOLE caller `FUN_0002214a`, 1kHz, confirmed via `get_function_callers`) computes a 3-state
float linear filter (15 coefficients, `tp+0x70e8..0x7120`) over two EXTERNAL inputs: `gp-0x501c` (a float,
producer `FUN_00070a98`) and `gp-0x4fd8` (an int, scaled by the constant `0.0015339808` -- close to
`2*pi/4096`, i.e. radians-per-count for a 4096-count/rev resolver, strongly suggesting a raw electrical
angle/counter). `gp-0x4fd8` has 27 static touches image-wide (`search_instructions`, truncated:false),
heavily concentrated in the `0x65xxx-0x69xxx` function range this kit's other memory already establishes as
FOC/resolver-rate territory (`FUN_00065eda`, `FUN_0006964c`, `FUN_00068cf4`) plus `FUN_0003bd7c` (the same
engage-SM function from section 3) and `FUN_0003debc`/`FUN_0003dff0`. **Neither input traces to anything
LKAS/CAN-domain.** This closes the open question in
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] ("whether `FUN_00041d56`'s filtered
rate signal is excited BY the 21 Hz grinding itself... plausible given the structural shape but NOT
confirmed") on the DOMAIN question specifically: it's resolver/motor-electrical-domain, not an LKAS state
or a torque-sensor-domain signal -- so `gp-0x671d`'s r24 priority-1 override arm is not itself an LKAS
excitation path, though whether it fires DURING a 21/40Hz mechanical event (because the resolver rate
itself oscillates then) remains open and is a physically plausible route regardless of domain label.

## Bottom line for the operator's requirement ("decidedly LKAS-dependent, not affecting base steering")

**No cal-only lever exists.** r24/r26 read zero LKAS-domain signals; their sole non-torque inputs
(`gp-0x671a` state-ramp, `gp-0x671d` resolver-domain event counter, `gp-0x6ac0` motor-rate LERP index,
`gp-0x6b5e` state-timing gate for r26) are all base-assist/resolver-domain, confirmed this session, not
LKAS-conditional and not usable as an LKAS proxy. The V57 cal-fork pattern does not generalize here because
`gp-0x4f62` has one producer and one physical source (`gp-0x4f60`), unlike `0xC646C`'s six independent read
sites. **A code-level gate is structurally feasible** -- `gp-0x67fe` (LKAS engage-SM state) and `gp-0x6806`
(arbitration ramp-FSM phase) are both already computed fresh, earlier in the same 1kHz tick, by functions
that run before `FUN_0003aa2c` -- but implementing it means new instructions in the 1kHz path (this kit's
higher bricking-risk class), not evaluated further here per the brief.

## Related
[[reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples]] -- the r24/r26 structure and gain-arm
priority chain this session's fresh decompile reproduces and extends (section 7 closes one of its OPEN items).
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] -- the V57 precedent this session's Q2
explains does NOT generalize to r24.
[[reference-accord-engage-sm-full-dispatcher-and-trump-exits]] -- gp-0x67fe's engage-SM semantics; this
session's fresh writer confirmation (FUN_0003bd7c, 4 st.b sites) resolves that memory's "producer
UNRESOLVED" flag.
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] -- gp-0x6806's FSM-phase identity, corroborated
as fresh-before-aggregator this session.
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] -- the 11-lane table this session's
fresh FUN_0003aa2c decompile reproduces exactly.
