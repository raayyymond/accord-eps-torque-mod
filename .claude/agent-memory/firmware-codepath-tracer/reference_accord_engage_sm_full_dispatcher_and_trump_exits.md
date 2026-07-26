---
name: reference-accord-engage-sm-full-dispatcher-and-trump-exits
description: Full byte-level walk of Accord TVA-A160 engage-SM dispatcher FUN_000413ae and ALL 9 state handlers (0-8). Confirms gp-0x67DC is the real dispatcher-state byte (not gp-0x679c). Finds THREE new independent (non-decider) exit mechanisms from the delivering states (2/7/8) never covered by V33/V34/V35: (1) a gp-0x67FE==2 "trump" that overrides ANY decider outcome and forces a transition into a non-delivering state-3/4 pocket -- UNCONDITIONAL in state 2, latch-gated (gp-0x138D/E or gp-0x1390) in states 7/8; (2) an FOC-mode mismatch gate (gp-0x6772 != 5) unique to states 2 and 7; (3) a fault-bit check FUN_00046ea6(13) unique to state 7 only. Also corrects caller attribution: decider call at 0x410a2 belongs to state-2 handler FUN_00041054, NOT FUN_00041222 (state 7) as implied by prior memory.
metadata:
  type: reference
---

# Full engage-SM dispatcher + state-handler walk (2020 Accord TVA-A160)

Session 2026-07-06, SEGMENT-C mapping task (V33/V34/V35 gentle-EME still reported after V35). Byte-level via
radare2 `v850.gnu`, stock `code.bin`, gp=0xFEDF8000, tp=0xBF000. Builds on and in places corrects
[[reference-accord-engage-sm-caller-enumeration-v34]], [[reference-accord-v34-state4-suppression-downstream]],
[[reference-accord-lkas-engage-sm-disengage-trigger]], [[reference-accord-engage-sm-second-gate-gp6cc4]].

## 1. Dispatcher FUN_000413ae -- state byte CONFIRMED gp-0x67DC (0xFEDF1824), not gp-0x679c [V]

`0x413ba: ld.bu -26524[gp],r14` -- disp -26524 = -0x67DC exactly. The mission boot card's "gp-0x679c" anchor is
WRONG; this independently reconfirms the correction already in `reference_accord_gp6cc4_tracking_pipeline.md`.

Full state dispatch table (byte-verified, 0x413ba-0x413e8), states are a `zxb` byte 0-8, else default:
| state | handler | role (this session) |
|---|---|---|
| 0 | `FUN_00040f42` @0x40f42 | init/idle entry; routes to 1/3/4/8 via gp+0x6470 sentinel + gp-0x67FE |
| 1 | `FUN_00040fda` @0x40fda | ENGAGING; decider(1) @0x41000 |
| 2 | `FUN_00041054` @0x41054 | **ENGAGED-context #1**; decider(2) @0x410a2; FUN_0003d04c(4,0) @0x410bc |
| 3 | `FUN_000410da` @0x410da | non-delivering bridge; NO decider call, NO (4,0) commit |
| 4 | `FUN_00041120` @0x41120 | RE-ARM; decider(4) @0x41156 |
| 5 | `FUN_0004117e` @0x4117e | ENGAGING retry #2; decider(1) @0x4119a |
| 6 | `FUN_000411c6` @0x411c6 | ENGAGING retry #3 (dwell/counter gated); decider(1) @0x411f6 |
| 7 | `FUN_00041222` @0x41222 | **ENGAGED "main"**; decider(2) @0x41280; FUN_0003d04c(4,0) @0x412ae |
| 8 | `FUN_00041304` @0x41304 | **HOLDING**; decider(3) @0x41364; FUN_0003d04c(4,0) @0x41382 |
| default (9+) | `FUN_00040a50` @0x4141e only | no per-state handler; common tail only |

After EVERY state's jarl (or the default fallthrough), the dispatcher tail (0x4141e-0x41460) unconditionally
calls `FUN_00040a50` then runs a per-state dwell-COUNTER/notifier block (table at gp-0x3E80 indexed by a value
read via pointer `gp-0x257C`+20, clamped 0-7; increments and compares against the dispatcher's own input param
r26; a second table at gp-0x3E78 conditionally calls `FUN_0001cba6`). **No reference to gp-0x6a62, gp-0x6cc4,
or FUN_0003d04c found in this tail** -- structurally a watchdog/telemetry counter, not a delivery gate. Not
traced further (out of segment priority).

## 2. CORRECTION: 0x410a2 (decider param=2 call) belongs to state-2 handler FUN_00041054, not FUN_00041222 [V]

Prior memory (`reference-accord-lkas-engage-sm-disengage-trigger`) attributed "the engaged handler
FUN_00041222... calls it with param=2" and a later memory flagged "a SECOND param=2 call at 0x41280 inside a
different handler (starting ~0x41222...)" without pinning 0x410a2's own enclosing function. **Byte-verified
this session: 0x410a2 is inside `FUN_00041054` (dispatcher state 2), a wholly separate function from
`FUN_00041222` (dispatcher state 7).** Both are legitimate, independent "ENGAGED-context" delivering-state
handlers, each running the *same* decider param=2 logic and each independently calling `FUN_0003d04c(4,0)` as
their own keep-deliver commit (0x410bc for state 2, 0x412ae for state 7). **This means the V33/V34 decider
patch protects BOTH state 2 and state 7 identically** (same callee, same NOP addresses) -- widens confirmed-safe
scope, but also means state 2 has its OWN, previously-unexamined set of state-handler-level gates (below).

## 3. NEW FINDING -- the gp-0x67FE==2 "trump" exit, asymmetric between state 2 and states 7/8 [V, HIGH PRIORITY]

All three delivering-context handlers (state 2, state 7, state 8/HOLDING) end with a COMMON TAIL that runs
**regardless of what the decider (or any other gate) decided that cycle**, and can OVERRIDE it:

- **State 2 tail (0x410c0-0x410d6):** `ld.bu -26622[gp],r12` (gp-0x67FE); if `r12>2` or `r12!=2` -> dispose
  (no override). **If `gp-0x67FE==2` EXACTLY -> unconditionally commits dispatcher state=3** via
  `FUN_00040d38(3)`, NO additional flag required. This OVERWRITES whatever the decider/independent-exit just
  committed in the same cycle (both paths `br 0x410c0` into this tail before returning).
- **State 7 tail (0x412b2-0x41300, matches `reference-accord-v34-state4-suppression-downstream` item 3):**
  same gp-0x67FE==2 gate, but ADDITIONALLY requires one of two latched request flags: `gp-0x138E`(-5006,
  0xFEDF6C7A)==1 -> commit state=8 (HOLDING), else `gp-0x138D`(-5005, 0xFEDF6C7B)==1 -> commit state=3, else
  no override (dwell). These flags are precomputed via `FUN_000405fe()` INSIDE the decider-stay branch only.
- **State 8/HOLDING tail (0x41386-0x413aa):** same gp-0x67FE==2 gate + single latch `gp-0x1390`(-5008,
  0xFEDF6C70)==1 -> commit state=3.

**Why state 3/4 matters:** state 3 (`FUN_000410da`) and state 4 (`FUN_00041120`, RE-ARM) form a pocket with
**NO `FUN_0003d04c(4,0)` call anywhere in either handler** (state 3 only calls `FUN_0003d04c(8,0)`, a
different first-param code seen throughout the cluster on every non-delivering transition -- working
hypothesis: 8 = "not delivering/standby" status, 4 = "active deliver", based on its exclusive association with
the decider-stay path in states 2/7/8). State 3 dwells (no commit) while gp-0x67FE==2, and only escapes to
state 4 when gp-0x67FE != 2; state 4 only promotes back to state 3 when gp-0x67FE == 2 (again). **Neither
state 3 nor state 4 transitions back to 2/7/8 directly in the code read this session** -- the only observed
escape from the 3/4 pocket is via the gp+0x6470 sentinel check (present in both handlers) forcing a demotion to
state 1 (ENGAGING), i.e. a FULL RE-ENGAGE CYCLE. **This matches the observable gentle-EME signature ("LKAS
drops and re-arms") exactly**, and is completely untouched by V33 (0xC6312 cal), V34 (2 decider NOPs), or V35
(0xC62FE cal in FUN_0003d04c) -- none of those touch FUN_000413ae, the state handlers, gp-0x67FE, or
FUN_00040d38's call sites in this cluster.

**Confidence:** structure/branch-targets/override behavior = [V], byte-level, reproducible. **gp-0x67FE's
physical identity and producer remain UNRESOLVED** -- same open item as
`reference-accord-v34-state4-suppression-downstream` item 8 (55 static readers, 0 `st.b` writers found by
pattern scan). Whether gp-0x67FE can transiently read 2 on a hard-turn+bump event is INFERENCE, not proven.
State 2's version is the more concerning candidate precisely because it requires NO additional latch (state
7/8 require a request flag that is itself sourced from an external accessor, less obviously bump-reactive).

## 4. NEW FINDING -- FOC-mode mismatch independent exit, states 2 and 7 only [V]

Both state 2 (0x41060-0x41082) and state 7 (0x41232-0x41254) contain an IDENTICAL-structure block, absent from
state 8: read `gp-0x6770`(-26480)==0 gate, then lockstep-shadow-check `gp-0x6772`(-26482, mode byte) against
shadow `gp-0x4C33`(-19507, 0xFEDF33CD) [mismatch -> `FUN_0006b9fa` fault report, side effect only], then test
`gp-0x6772 == 5`. **If mode != 5 (or the gp-0x6770/FUN_00040678 pre-gates aren't satisfied), the handler
demotes straight to state 1 (ENGAGING)** via the same commit-away sequence used for the request-cancel check
(`FUN_0003d04c(8,0)`, `FUN_00040d38(1)`) -- i.e. these two conditions are OR'd into one exit target:
`(gp-0x6772 != 5) OR (gp-0x138F(-5007, 0xFEDF6C71) == 2)`. `gp-0x138F==2` is plausibly a driver/upstream
cancel-request cache (used consistently this way across states 1/2/7/8) -- an INTENTIONAL disengage path, not a
suspect. `gp-0x6772` is a FOC/motor-controller MODE byte (per `reference-accord-gp6cc4-tracking-pipeline`,
already known to gate the still-unresolved-polarity gp-0x67FE writer region 0x3bd90-0x3bee0 alongside counter
gp-0x671D vs cal 0xC6500=3). Untouched by any build. Moderate-plausibility bump suspect (FOC controller directly
handles motor current, which spikes on hard mechanical events) but NOT proven bump-reactive this session.

## 5. NEW FINDING -- fault-bit check FUN_00046ea6(13), state 7 ONLY (state 2 does NOT have it) [V]

State 7 (0x4125e-0x41266), immediately before the gp-0x138F cancel-check's fallthrough: `mov 13,r6; jarl
FUN_00046ea6,lp; cmp r0,r10; be 0x4127e` -- if `FUN_00046ea6(13)` returns 0, continue to the normal decider(2)
path; **if non-zero, falls through into the SAME commit-away-to-state-1 sequence as the mode-mismatch/
cancel-request exits above.** `FUN_00046ea6` (0x46ea6) is confirmed by direct disasm to be a generic bit-test
accessor: `zxb r6` (bit index param); if index<32, extracts bit `index` from a 32-bit word at `gp-0x18D4`
(0xFEDF672C) via shift/mask; returns 0 or nonzero. Sibling calls elsewhere in the image use indices 0, 6, 7, 8
(seen in a fault-dispatch utility at 0x40906-0x40964 immediately following FUN_000406ae in the same code
region), and index 0 is independently identified in `reference_accord_consistency_monitor_hardshutdown.md` as
part of the hard-shutdown OR-condition (`FUN_00046ea6(0)`). **Bit 13's specific meaning/setter was NOT traced
this session** -- this is the single highest-value next hop: if bit 13 of gp-0x18D4 is set by anything
plausibly bump-reactive (a transient current/torque/vibration flag), this is a completely unexplored gentle-EME
path, structurally confirmed to force ENGAGED (state 7) back to ENGAGING with zero debounce, and outside the
scope of every build V32-V35.

## 6. Decider FUN_00040d58 -- full param 1 (ENGAGING) and param 4 (RE-ARM) gate chains, freshly decoded [V]

Not previously laid out instruction-by-instruction in prior memory (which only asserted the gate identities).
Confirmed exact order and unique return codes:

**Param 1 (ENGAGING), 0x40d78-0x40dc4, in order:**
1. `gp-0x6a60(0xFEDF15A0)==0xffff` @0x40d80 -> r12=5
2. `gp-0x6a60 >= cal 0xC6310(1600)` @0x40d88 (`bnl`) -> r12=5
3. `gp-0x4f68(0xFEDF3098)==0xffff` @0x40d92 -> r12=6
4. `gp-0x4f68 >= cal 0xC61CE(4096)` @0x40d9a (`bnl`) -> r12=6
5. `gp-0x6ba4(0xFEDF145C)==0xffff` @0x40da4 -> r12=7
6. `gp-0x6ba4 >= cal 0xC61CC(3584)` @0x40dac (`bnl`) -> r12=7
7. `gp-0x6a62(0xFEDF159E)==0xffff` @0x40db6 -> r12=2
8. `gp-0x6a62 >= cal 0xC6312(320, V33->65535)` @0x40dbe (`bnl`) -> r12=2
9. else r12=0 (ENGAGE SUCCESS)

**Param 4 (RE-ARM), 0x40e1e-0x40e64, REUSES gates 1-6 above verbatim (same signals, same cals), in order,
but has NO gp-0x6a62/cal-0xC6312 check at all** -- confirmed by direct disasm, matches (and here
instruction-verifies) the summary in `reference-accord-engage-sm-caller-enumeration-v34`. Else r12=0 (RE-ARM
SUCCESS). Return codes 5/6/7 are shared "engage-refusal" sub-codes across params 1 and 4, distinct from 2
(torque) and 4 (angle-consensus, params 2/3 only).

These are ENGAGE-ATTEMPT REFUSAL gates (pre-delivery states 1/4/5/6), not "leave delivering" gates -- included
for mandate completeness but ranked LOW priority for the gentle-EME (LKAS isn't yet delivering torque in these
states).

## 7. FUN_000406ae re-confirmed byte-identical to prior memory's characterization [V]

Full re-disasm 0x406ae-0x40880 matches `reference_accord_gp6cc4_tracking_pipeline.md` and
`reference_accord_engage_sm_second_gate_gp6cc4.md` exactly at every checked instruction: early-bypass sentinel
checks, gp-0x35AC write @0x40862, final `ABS(gp-0x6cc4 - gp-0x35AC) vs cal 0xC6354(4825)` @0x4086a-0x4087a,
`cmov h,1,r21,r21` polarity. No corrections needed. Function ends cleanly at 0x40880.

Also newly noted: **FUN_000406ae is called an EXTRA, side-effect-only time at the very top of both state 7
(0x41226) and state 8 (0x41308), before the decider's own internal call** -- return value discarded (r10
overwritten by the next instruction in both cases). Confirms V34 handoff's claim that "the call is retained,
its side effect runs every cycle" -- now confirmed for THREE call sites per delivering cycle, not one.

## 8. FUN_0003d04c(4,0) hand-off points -- THREE, not one [V]

The mandate's segment boundary stops at "the hand-off point where the decider return gates the
FUN_0003d04c(4,0) call." There are three, not the one previously documented:
- State 2 stay-path: `0x410bc jarl FUN_0003d04c,lp` (r6=4,r7=0), gated by decider(2) returning 0 AND
  `FUN_000405fe()==1` @0x410b0-0x410b6.
- State 7 stay-path: `0x412ae jarl FUN_0003d04c,lp`, gated by decider(2) returning 0 AND a 2-flag
  `FUN_000405fe()`-derived check @0x4128e-0x412ac (matches prior memory).
- State 8/HOLDING stay-path: `0x41382 jarl FUN_0003d04c,lp`, gated by decider(3) returning 0 AND
  `FUN_000405fe()==1` @0x41372-0x4137c.
All three are downstream of the SAME decider function and hence protected identically by V33/V34. `FUN_0003d04c`
internals (including V35's gate 7 @0x3d0a8 and gate 5 @0x3d08c) are out of this segment's scope per the
mission brief.

## Related
[[reference-accord-engage-sm-caller-enumeration-v34]] [[reference-accord-v34-state4-suppression-downstream]]
[[reference-accord-lkas-engage-sm-disengage-trigger]] [[reference-accord-engage-sm-second-gate-gp6cc4]]
[[reference-accord-gp6cc4-tracking-pipeline]] [[reference-accord-consistency-monitor-hardshutdown]]

## Next verification steps (in priority order)
1. **gp-0x67FE producer** -- who writes it, and can it read 2 transiently on a bump? (item 3 above; also open
   in prior memory item 8). Needs a broader instruction-form sweep (st.h, indexed/EP-relative store) or Ghidra
   data-flow trace, or a live-RAM capture of `0xFEDF1802` during a hard-turn+bump event.
2. **FUN_00046ea6(13) bit identity** -- trace who sets bit 13 of `gp-0x18D4` (0xFEDF672C). (item 5 above.)
3. **gp-0x6772 producer/polarity** -- the FOC-mode byte; prior memory already flagged its gating counter's
   polarity as unresolved ("conflicting conclusions... did NOT have budget to fully re-resolve").
