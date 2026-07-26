---
name: reference-accord-segmentD-fun3d04c-full-gate-map
description: 2020 Accord TVA-A160 SEGMENT D — full byte-verified decompile of FUN_0003d04c (0x3d04c-0x3d1f4), the per-cycle ENGAGED deliver-commit function called as FUN_0003d04c(4,0) from FUN_00041222 @0x412ae. Exactly 7 pre-gates confirmed (matches boot-card count). Gate 5 identity SOLVED: gp-0x4f68 = clamp(ABS(gp-0x4f60),0,65535), i.e. unsigned column/motor ANGULAR VELOCITY magnitude, NOT torque — re-derived fresh from disasm at 0x7fe80-0x7fedc, independently confirming the pre-existing reference_accord_gp6af8_fight_trigger.md claim. Also traces the commit chain one hop downstream (FUN_0003c4e2/FUN_0003c6a4/FUN_0003c7fc/FUN_0003fd8e) and finds an ADDITIONAL angle-deadband gate (cal 0xC6354=4825 / 0xC635C=7407, reusing the engage-SM's gp-0x6cc4 cal) inside FUN_0003c7fc that is NOT touched by V35 and can independently suppress the commit.
metadata:
  type: reference
---

# FUN_0003d04c (SEGMENT D deliver-commit) — full gate map, 2020 Accord TVA-A160

Session 2026-07-06. `code.bin` (39990-TVA-A160), gp=0xFEDF8000, tp=0xBF000. radare2 5.5.0, `v850.gnu` plugin
(default `v850` mis-decodes). All addresses/values below are r2-verified this session unless marked INFERRED.

## Function boundary [V]
`FUN_0003d04c` = `0x3d04c`–`0x3d1f4` (dispose). Prologue: `r6`(param_1)→`r28` via `zxb` (byte enum, values
0-9 handled); `r7`(param_2)→`r26` via `sxh` (signed 16-bit passthrough, used only by case 5).

## Callers [V — exhaustive for the two sites found; not a full-image caller enumeration]
- `0x412ae`: `mov 4,r6; jarl 0x3d04c,lp` — the boot-card-named site, reached from `FUN_00041222` (ENGAGED
  handler) ONLY when: (1) `FUN_00046ea6()==0` at `0x41266`; (2) `FUN_00040d58(2)` (engage-SM decider) returns 0
  ("stay") at `0x41284`; (3) `FUN_000405fe()` is called at `0x4128e` and its result + the latch byte
  `gp-0x138F`(-5007) / `gp-0x138D`(-5005) / `gp-0x138E`(-5006) trio gates through to `0x412ac`. This
  independently re-confirms `reference_accord_v34_state4_suppression_downstream.md`'s claim that
  `FUN_000405fe` + `gp-0x67FE` latch machinery is the real ENGAGED-path gate, now shown to ALSO gate entry to
  the deliver-commit, not just the decider's own exit.
- `0x41278`: `mov 8,r6; mov 0,r7; jarl 0x3d04c,lp` — a sibling call with param_1=8, reached when
  `FUN_00046ea6()!=0`. (case r28==8 handler; not deep-dived this session, out of primary scope.)
- Both call sites' return value (`r10`) is **discarded** — verified by reading every instruction from each
  call site to the next `dispose` and confirming `r10` is never read as a source register. **This is the key
  structural surprise:** none of FUN_0003d04c's 5 distinct return codes (0/2/3/5/6, or passthrough 1/4 from
  cases 1-9) change caller control flow at these two sites. The only externally-visible effect of an internal
  gate failure is that the case body's *side-effect calls* (writes to `gp-0x6770` etc., and for case 4 the
  `FUN_0003c4e2`/`FUN_0003c6a4`/`FUN_0003c7fc` chain) simply do not run that cycle.

## The 7 pre-gates [V — all 7, exact addresses, exact cal values where cal-driven]
Run unconditionally, in this order, for EVERY call regardless of param_1 (i.e. apply to all of ENGAGING/
ENGAGED/HOLDING/RE-ARM sub-states 1-9 uniformly — they gate the whole function, not just the `(4,0)` path):

| # | branch @addr | signal | condition (bail if true) | bail target / return | cal (stock) | live after V35? | bump-trippable? |
|---|---|---|---|---|---|---|---|
| 1 | 0x3d05e/0x3d060 | `FUN_00018ce8(13)` return (r10) | `==2` | 0x3d1f2 → return 5 | n/a (DTC status, runtime) | Y | LOW (needs an already-latched DTC) |
| 2 | 0x3d06c/0x3d06e | `FUN_00018ce8(14)` return (r10) | `==2` | 0x3d1f2 → return 5 | n/a | Y | LOW |
| 3 | 0x3d078/0x3d07a | `gp-0x67FA` (system-mode/EPS-state byte; known values 4=init-activate, 8=hard-shutdown per other memories) | `==10` (new, undocumented enum value) | 0x3d1ee → return 6 | n/a (runtime state byte) | Y | LOW-UNKNOWN |
| 4 | 0x3d084/0x3d086 | `gp-0x4E5F` (byte; identity UNRESOLVED — proximate to known gp-0x4e5a "branch selector"/gp-0x4e65 "assist-mode SM state" cluster, INFERRED-only by address proximity) | `!= 1` | 0x3d1ea → return 3 | n/a | Y | UNKNOWN |
| 5 | 0x3d094/0x3d096 | **`gp-0x4f68`** | `>= cal 0xC61EA` | 0x3d1ea → return 3 | **0xC61EA = 0x1000 = 4096** | Y | **HIGH — see verdict below** |
| 6 | 0x3d0a0/0x3d0a2 | `gp-0x67F4` (torque-channel plausibility flag, per `reference_accord_arb_input_cluster.md`, sole writer `FUN_00041eec`) | `!= 1` | 0x3d1e6 → return 2 | n/a | Y | LOW (per `reference_accord_arb_bvar1_full_enumeration.md`, only trips if ALL 5 channels fail wide 25600-32000-class range checks) |
| 7 | 0x3d0b0/0x3d0b2 | `gp-0x6a5e` (voter AVG torque, sensor A) | `>= cal 0xC62FE` | 0x3d0b4→0x3d1e6 → return 2 | **0xC62FE = 0x0140 = 320** — **V35's target, raised to 65535** | **N (V35-disabled)** | was HIGH pre-V35 |

Exactly 7 — matches the boot card's stated count precisely. Gates 5 and 7 addresses/cals match the boot card
verbatim (cross-confirms the boot card was itself accurate).

## Gate 5 verdict — SOLVED [V, high confidence]
`gp-0x4f68` = `clamp(ABS(gp-0x4f60), 0, 0xFFFF)`. Writer: `FUN_0007f3f8` at `0x7feca` (`st.h r14,-20328[gp]`),
lockstep-shadowed to `gp-0x449C` at `0x7fece`, fault path `FUN_0006b9ee` on mismatch (`0x7fed8`). `r14` is
built at `0x7fe88`-`0x7fec2`: `r8 = gp-0x4f60` (signed, `ld.h -20320[gp]`, read identically on all 3 converging
branches of a preceding state-check block that calls `FUN_0005b68c(11,3)` — a diagnostic side-report — on one
path but always resolves to the same `gp-0x4f60` read); `r14 = |r8|`; then clamped to `0xFFFF` via
`cmov nc/nl`. **This independently re-derives, from fresh disasm, exactly what
`reference_accord_gp6af8_fight_trigger.md` (a different session, different investigation) already
documented**: "`gp-0x4f68` is unsigned absolute value ... FUN_0007f3f8 writes gp-0x4f68 = ABS(computed_velocity)
at 0x7feca." Two independent derivations now agree.

⚠⚠ **FALSIFIED 2026-07-18 — the paragraph below is WRONG. `gp-0x4f60` = SENSOR-B (TAS) SIGNED DRIVER
COLUMN TORQUE, not angular velocity.** Decisive counter-evidence: the CAN-399 packer `FUN_00055c42`
emits `STEER_TORQUE_SENSOR (bytes[0:1]) = -(gp-0x4f60 × 0x7d >> 7)` = `-(gp-0x4f60 × 125/128)`. A value
transmitted on the bus *as* STEER_TORQUE_SENSOR is the torque sensor. Note how the three "evidences"
below are all **consumer-side inferences** (a threshold's units, a range gate's width, an SM's use) —
none of them looks at the producer or the packer. That is the exact inferential slip: reasoning from
how a signal is USED to what it IS. The Gate-5 finding above (`gp-0x4f68 = |gp-0x4f60|`) is unaffected
as *arithmetic*, but its label "angular velocity magnitude" must be read as "|column torque|".
This correction was ALSO made on 2026-07-07 (`docs/HANDOFF-2026-07-07`) and failed to propagate here.
Node of record: [[reference-accord-gp4f60-is-sensor-b-column-torque]].

~~`gp-0x4f60` itself (per that same prior memory, re-cited not re-derived this session) = **signed
column/motor angular velocity** (steering-column rotation rate), evidenced by:~~ (a) `FUN_00043e44` converts it
to float and compares against 25.0 (a deg/s-class threshold), (b) `m_steer_torque_arbitration` range-gates it
to ±0x6400=±25600 (signed velocity semantics, not torque), (c) the fight-trigger SM in `FUN_00042af8` uses it
as the column's own rotation direction/rate to detect LKAS-vs-road fights.

**So Gate 5 is a RATE gate, not a torque gate**, despite superficially resembling one in the boot card's
uncertain framing. Cal `0xC61EA=4096` sits at **16% of the ±25600 full-scale window** used elsewhere for this
exact signal's own plausibility gating — i.e. it is a comparatively tight threshold relative to the signal's
known dynamic range. **This directly matches the "+bump" half of the gentle-EME symptom**: a mechanical
shock/hard-turn transient plausibly spikes column angular velocity (steering wheel kicking rapidly) past 4096
well before it would approach the sensor's own ±25600 plausibility ceiling. Confidence: **HIGH** (two
independent disasm derivations of the writer + three independent usage-site derivations of the signal's
semantic identity, all consistent).

## One hop downstream — the commit chain and a SECOND, UNTOUCHED angle-deadband gate [V]
Case `r28==4` (the `(4,0)` call) body, `0x3d138`-`0x3d15c`, if none of gates 1-7 bailed: sets
`gp-0x6770`(-26480)=3 ["mode" byte], `gp-0x6858`(-26712)=0, `gp-0x69CE`(-27086)=cal `0xC6354`(=4825, cached),
then unconditionally calls `FUN_0003c4e2()` → `FUN_0003c6a4()` → `FUN_0003c7fc(0)`, then clears
`gp-0x6773`(-26483)=0. **`FUN_0003d04c`'s own return value for this path is simply whatever `FUN_0003c7fc`
returns** (case-4 body never re-sets r10 after the last jarl) — but per the caller finding above, this is
moot since the caller discards it anyway.

- `FUN_0003c4e2` (0x3c4e2-0x3c53a): lockstep min/max bounds-tracking on `gp-0x6cc4` (the SAME angle/position
  accumulator characterized in `reference_accord_engage_sm_second_gate_gp6cc4.md`) against shadows
  `gp-0x4D18`/`gp-0x4D14`, `FUN_0006b9fa` fault-report on mismatch; then a rate/dwell computation using cal
  `0xC6342`(tp+0x7342)=5790 and calls `FUN_0003f32c`/`FUN_0003c3c6`. Bookkeeping, not itself a bail.
- `FUN_0003c6a4` (0x3c6a4-0x3c6f8): propagates `gp-0x6770` into `gp-0x6772`(-26482, shadow `gp-0x4CD3`/-19507)
  **unless `gp-0x6772` is already 7 (sticky/terminal — won't be overwritten)**. Calls `FUN_0003c5ea()` on the
  "set" branches.
- **`FUN_0003c7fc(param)` — contains an INDEPENDENT deadband/consistency gate, NOT part of FUN_0003d04c's own
  7, and NOT touched by V35:**
  - Byte-cal `tp+0x74A7` = abs `0xC64A7` = **1** (stock, i.e. this particular feature-enable sub-check is
    always-pass in stock — `be 0x3c93a` bail only if this cal were 0).
  - Core check (both the `gp-0x6773==1` branch at `0x3c81c-0x3c838` AND the `gp-0x6773==0`/default branch at
    `0x3c8c6-0x3c8ec`): **`|low16(gp-0x6cc4) − r26(reference angle from FUN_0003c7ce)| <= cal`**, where cal is
    `0xC6354=4825` (case 4/6 path) or `0xC635C=7407` (case 2/5 path, freshly discovered this session — not
    previously documented anywhere). **BAIL if the delta exceeds the cal** → jumps to `0x3c920`/`0x3c93a`,
    which **resets `gp-0x6770` back to 0** (overwriting whatever FUN_0003d04c's case body set it to) and
    returns `r28=4` (a bail code, coincidentally reusing the value 4). On PASS: computes a
    direction-sign-scaled correction (cals `0xC613A`=1159, `0xC6432`=900, sign from `gp-0x6752`), sets
    `gp-0x6771`(-26481)=1 (a "committed" flag distinct from `gp-0x6770`), mirrors to `gp-0x6844`/`gp-0x684E`
    (-26692/-26702) and shadow `gp-0x4CD2`(-19506), stores the scaled value to `gp+0x6470`(+25712, a
    **positive**-displacement struct field on the other side of `gp`), then calls `FUN_0003fd8e()`.
  - `FUN_0003fd8e` (the call made on every successful commit) is a **tiny 4-instruction thunk**:
    `st.h r0,gp+0x641C; st.w r0,gp-0x4D1C; st.w r0,gp-0x6CDC; jmp[lp]` — it just **zeroes 3 bounds-tracking
    fields** (a "reset the angle-tracking window" operation). **It is NOT a torque/current write.** No
    torque-value store was found anywhere in this entire call chain (FUN_0003d04c → FUN_0003c4e2 →
    FUN_0003c6a4 → FUN_0003c7fc → FUN_0003fd8e).

**Conclusion on the "last hop": FUN_0003d04c and its immediate commit chain are pure state-machine
bookkeeping** (mode bytes `gp-0x6770/6771/6772/6773`, angle-tracking window `gp-0x6cc4` + bounds
`gp-0x4D14/18/1C`+`gp-0x6CC4/CCC/CD0/CDC`, and struct field `gp+0x6470`). **No direct write to a torque or
current command register was found in this segment.** The actual "does the motor get commanded to zero"
decision must be made by a DOWNSTREAM consumer reading `gp-0x6770`/`gp-0x6771`/`gp-0x6772`/`gp+0x6470` — this
is the hand-off to the arbitration/shaper segment. **Note:** Segment E's memory
(`reference_accord_segmentE_arbitration_shaper_dtc_gate_table.md`, this same session) pins the ENABLE byte
`gp-0x67a4` writer at `0x2b51e` in `FUN_00028ea6` — **I did not find any connection between that byte and the
`gp-0x6770`-cluster variables this segment writes.** This non-connection is flagged, not resolved: either
they're genuinely parallel/independent subsystems (angle-tracking dwell-gate vs. the actual command path), or
there's a link through a variable neither segment's session covered. Recommend the arbitration tracer check
for readers of `gp-0x6770`/`gp-0x6771`/`gp-0x6772`/`gp+0x6470` specifically.

## Gates 3/4/6 identity confidence notes
- Gate 6 (`gp-0x67F4`) identity is well-established from prior sessions (multiple independent memories:
  `reference_accord_arb_input_cluster.md`, `reference_accord_arb_bvar1_full_enumeration.md`,
  `reference_accord_init_sm_fun220ba_fun1a104.md`) — HIGH confidence, re-confirmed here via the read site.
- Gate 3 (`gp-0x67FA`) — the VARIABLE is well-established as a wide system-mode/EPS-state byte (values 4, 8
  documented elsewhere), but the SPECIFIC value 10 checked here is new/undocumented — MEDIUM confidence on
  variable identity, LOW confidence on what state "10" represents.
  Producer not searched exhaustively this session (would need whole-image wildcard byte scan, deferred).
- Gate 4 (`gp-0x4E5F`) — NO prior memory hits found. Producer NOT located this session (attempted a targeted
  wildcard byte search but did not resolve a definitive writer within budget). Its proximity in the gp offset
  space to the known `gp-0x4e5a` (governor branch selector) / `gp-0x4e65` (assist-mode SM state 0-4) cluster
  is suggestive but UNCONFIRMED — flagged explicitly as a weak positional inference, not a disasm-verified
  claim. **Next step to resolve:** whole-image wildcard scan for `84..a1b1` (read) and the corresponding
  store opcode pattern (needs deriving from a confirmed store example first, or brute-force `44/64` head bytes
  with 2-byte wildcard + manual pd verification of hits).
- Gates 1/2 (`FUN_00018ce8(13)`/`FUN_00018ce8(14)`): `FUN_00018ce8` is a generic fault-status getter
  (zxh's the fault_id param, calls `FUN_00058004` to fetch a status byte matching the "STATUS byte = from
  gp+0x634b+fault_id status array" pattern in `reference_accord_dtc_construction_mechanism.md`). Immediately
  adjacent function `FUN_00018d02` (starts right where `FUN_00018ce8` ends, `0x18d02`) is independently
  confirmed by that same DTC memory to be the **fault_id=7** specific checker — cross-confirms the fault-status
  mechanism's existence and location, though fault_id 13/14's specific physical meaning is unresolved this
  session. Bail condition is status`==2` (plausibly "confirmed/active" in typical DTC status encodings) —
  INFERRED, not proven.

## Related
[[reference-accord-gp6af8-fight-trigger]] — original gp-0x4f60/gp-0x4f68 identity derivation (prior session);
this session's fresh disasm at 0x7fe80-0x7fedc independently reproduces its conclusion.
[[reference-accord-engage-sm-second-gate-gp6cc4]] — the SAME gp-0x6cc4/cal-0xC6354 pairing found here inside
FUN_0003c7fc, previously found gating FUN_00040d58's ENGAGED/HOLDING branches. Two structurally independent
consumers of the identical accumulator+cal — reinforces that this consensus/deadband cal is a widely-reused
plausibility gate throughout the engage/deliver pipeline, and that V35 (which only touched `0xC62FE`) leaves
ALL of these reuses live.
[[reference-accord-arb-input-cluster]] — gp-0x67f4 plausibility flag identity (gate 6).
[[reference-accord-v34-state4-suppression-downstream]] — FUN_000405fe/gp-0x67FE as the real ENGAGED-exit
mechanism; this session shows the SAME machinery also gates entry to FUN_0003d04c(4,0), not just decider exit.
