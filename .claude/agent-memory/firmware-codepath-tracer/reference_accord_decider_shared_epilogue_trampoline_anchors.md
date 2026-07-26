---
name: reference-accord-decider-shared-epilogue-trampoline-anchors
description: Byte-verified trampoline-anchor audit of Accord TVA-A160 engage-SM decider FUN_00040d58 gates A (gp-0x6a62/cal-0xC6312 torque) and B (gp-0x6a60/cal-0xC6310 rate). Both gates' "fire" edges (across all 5 physical copies: 3x gate A, 2x gate B) converge on shared 2-byte mov+branch epilogues that cannot host a >=4B non-branch anchor; the ONE clean relocatable anchor for BOTH gates is the shared final commit `st.b r12,-0x35b6[gp]` at 0x40e64 (4B, raw 44 67 4A CA), discriminated post-hoc by r12's value. Caller-side landing points are worse (bracketed by cmp/be/jarl only) -- no anchor there.
metadata:
  type: reference
---

# FUN_00040d58 (Accord TVA-A160 engage-SM decider) — trampoline-anchor audit, 2026-07-13

Read-only audit (Ghidra MCP, `program="master.bin"`, raw disasm + `read_memory` byte confirmation; gp=0xFEDF8000,
tp=0xBF000). Goal: find a >=4-byte, non-pc-relative instruction on the "gate fired" path for gate A
(`gp-0x6a62 >= cal 0xC6312`, mission's V33 target) and gate B (`gp-0x6a60 >= cal 0xC6310`, re-arm rate gate),
suitable to overwrite with a 4-byte `jr <cave>`. Builds on
[[reference-accord-lkas-engage-sm-disengage-trigger]] and [[reference-accord-engage-sm-full-dispatcher-and-trump-exits]]
(which established the signal identities and gate order) — this session adds byte-level branch polarity and the
trampoline feasibility analysis those memories didn't cover.

## Full body of FUN_00040d58, byte-verified [V]

Disassembled whole function (0x40d58-0x40e6a) via `disassemble_function`, then independently confirmed every
candidate instruction's raw bytes via `read_memory` (not just address deltas). Key structural fact: **the decider
has FIVE physical copies of gate-compare logic, not one each for A/B** — one per param context — and copies of
the SAME gate converge on a SHARED single-instance epilogue:

| gate | param context | block start | fire branch (addr: bytes mnemonic) | polarity |
|---|---|---|---|---|
| A | 1 (ENGAGING, precondition) | 0x40dae | `0x40dbe: f9 1d bnc 0x40dfc` | explicit taken=fire |
| A | 2 (ENGAGED) — **mission target** | 0x40dc6 | `0x40dd6: 1b 91 bnc 0x40dfc` | explicit taken=fire |
| A | 3 (HOLDING) — **mission target** | 0x40dea | `0x40dfa: b1 05 bc 0x40e00` | **inverted: taken=PASS, fall-through(not-taken)=fire** |
| B | 1 (ENGAGING, precondition) | 0x40d78 | `0x40d88: c9 55 bnc 0x40e30` | explicit taken=fire |
| B | 4 (RE-ARM) — **mission target** | 0x40e1e | `0x40e2e: b1 05 bc 0x40e34` | **inverted: taken=PASS, fall-through(not-taken)=fire** |

All 5 gate-A/B copies also have a paired sentinel check (`gp-0x6a62`/`gp-0x6a60 == 0xffff`) immediately before the
cal compare, which branches to the SAME fire target as the real threshold-cross (invalid-sensor and
threshold-exceeded are indistinguishable downstream — both commit the same return code).

**cmp semantics confirmed by cross-check, not assumed:** `cmp Rm,Rn` computes `Rn-Rm` and sets CY on unsigned
borrow (Rn<Rm). Verified self-consistent with the ALREADY-established ground truth in
`reference_accord_lkas_engage_sm_disengage_trigger.md` (gate A fires when `gp-0x6a62 >= cal`) at all 5 sites.

## Shared epilogues — the actual convergence points

- **Gate A family (codes converge on `mov 0x2,r12`):** target `0x40dfc` (raw `02 62`, 2 bytes) — reached from
  6 edges: 3 threshold-fire branches (0x40dbe, 0x40dd6 explicit; 0x40dfa implicit-fallthrough) + 3 paired
  sentinel branches (0x40db6, 0x40dce, 0x40df2).
- **Gate B family (codes converge on `mov 0x5,r12`):** target `0x40e30` (raw `05 62`, 2 bytes) — reached from
  2 threshold-fire branches (0x40d88 explicit, 0x40e2e implicit-fallthrough) + 2 paired sentinel branches
  (0x40d80, 0x40e26).
- Both 2-byte `mov` epilogues are IMMEDIATELY followed by a 2-byte `br 0x40e64` (0x40dfe raw `b5 35`; 0x40e32 raw
  `95 1d`) — a pc-relative branch, so **no >=4B non-branch run exists at the immediate fire point for either
  gate.** This rules out 0x40dfc/0x40dfe and 0x40e30/0x40e32 as anchor pairs (would require relocating a branch).
- **Both families re-converge on ONE further shared instruction: `0x40e64: st.b r12,-0x35b6[gp]`, raw bytes
  `44 67 4A CA` (4 bytes)** — this is the recommended anchor (see below). Immediately after it: `0x40e68: mov
  r12,r10` (raw `0c 50`, 2B, non-branch, reads r12→writes r10, no PSW dependency), then `0x40e6a: dispose
  0x0,{lp},[lp]` (function return).

## Caller side is WORSE, not better — checked and ruled out [V]

Traced the 3 mission-relevant callers (`FUN_00041054`@0x41054 state 2/ENGAGED, `FUN_00041304`@0x41304 state
8/HOLDING, `FUN_00041120`@0x41120 state 4/RE-ARM) past their `jarl FUN_00040d58,lp` call sites. All three have the
**identical 3-instruction bracket** around the "fired" landing: `cmp r0,r10` (2B, non-specific — runs on both
outcomes) / `be <pass-target>` (2B, branch) / `jarl FUN_00040e74,lp` (4B, but **pc-relative call**, disallowed) /
`br <exit>` (2B, branch). Byte-confirmed via `read_memory`:
- 0x410a6-0x410ae (state 2): `e0 51`(cmp) `c2 05`(be) `bf ff ca fd`(jarl, 4B) `95 0d`(br)
- 0x41368-0x41370 (state 8): `e0 51`(cmp) `c2 05`(be) `bf ff 08 fb`(jarl, 4B) `b5 0d`(br)
- 0x4115a-0x41162 (state 4): `e0 51`(cmp) `c2 05`(be) `bf ff 16 fd`(jarl, 4B) `c5 0d`(br)

No non-branch >=4B run exists here either. **Verdict: the decider-internal shared epilogue at 0x40e64 is the
best (and only) available anchor for both gates**, not a fallback.

## Recommended anchor: 0x40e64 — `st.b r12,-0x35b6[gp]`

- Raw bytes: `44 67 4A CA` (4 bytes total: opcode halfword `0x6744`, disp16 halfword `0xCA4A` = sign-extended
  `-0x35B6`, i.e. writes to `gp-13750` = `0xFEDF4A4A`).
- **Relocatable-safe:** addressing is `gp + disp16` (gp = r4, a runtime data-pointer register, not PC) — verbatim
  re-execution from a code cave produces the identical memory write regardless of the cave's address. Confirmed
  NOT a branch/jarl/jr/loop.
- **Discriminator:** r12 holds the numeric outcome code at this instruction: `2` = gate A fired (torque
  magnitude OR its paired sensor-invalid sentinel, from ANY of the 3 param-context copies), `5` = gate B fired
  (rate OR its sentinel, from either of the 2 param-context copies), `4` = the separate gp-0x6cc4 consensus gate
  (V34's target, out of this mission's scope), `6`/`7` = the other two pre-delivery refusal gates. **One
  physical trampoline at 0x40e64 serves BOTH gate A and gate B telemetry** — the stub just branches on r12.
- **PSW:** `st.b` does not read or write condition flags (V850 store instructions are flag-inert) and the
  instruction after (`mov r12,r10`) is unconditional — nothing downstream of this anchor consumes PSW state
  from at/before it. Standard save/restore is cheap insurance, not load-bearing here.
- **Register-preservation note (important, beyond the stub's stated r1/r2+PSW convention):** the anchor's operand
  is **r12**, not r1/r2. r12 is simultaneously (a) the telemetry payload the operator wants to read and (b) the
  operand the re-executed displaced instruction needs. The stub must NOT clobber r12 (or must explicitly
  save/restore it) — this is a gap in the stated "saves r1/r2+PSW" default and should be called out to the
  operator before this specific anchor is used. gp (r4) is untouched by essentially all code in this image and
  is not a practical risk.

## Alternative anchor option — per-gate-exclusive hook via branch re-encoding (precedent-matched)

Sibling audits done the same session (`reference_accord_deliver_commit_gate5_gate7_trampoline_anchors.md`,
`reference_accord_fun3c7fc_trampoline_anchor.md`) establish that this project already uses a **branch
re-encoding technique** for exactly this situation (see `reference_accord_telemetry_ram_hook_a160.md`'s
`0x4141E` hook, which relocates a 4-byte `jarl disp22`, and the Gate5/Gate7 memory's proposal to relocate a
2-byte `br disp9` by re-encoding its displacement for the cave's actual position, growing it to whatever size
the new displacement needs). If that technique is in scope (it was explicitly used elsewhere in this build),
a MORE surgical option exists than the shared 0x40e64 landing:
- **Gate A only:** anchor = `0x40dfc`+`0x40dfe` (`mov 0x2,r12` [2B, `02 62`] + `br 0x40e64` [2B, `b5 35`,
  RE-ENCODED for the cave's actual displacement to 0x40e64]) — reached by all 3 gate-A copies
  (ENGAGING-precondition + ENGAGED + HOLDING), fires unconditionally and ONLY for gate-A-family events, no
  in-stub r12 check needed.
- **Gate B only:** anchor = `0x40e30`+`0x40e32` (`mov 0x5,r12` [2B, `05 62`] + `br 0x40e64` [2B, `95 1d`,
  RE-ENCODED]) — reached by both gate-B copies (ENGAGING-precondition + RE-ARM), same benefit.
- Trade-off vs the 0x40e64 recommendation below: two separate cave stubs instead of one, and requires the
  displacement-recompute step (cheap, but not "zero-touch" like a verbatim relocation). Does NOT resolve the
  within-gate param-context ambiguity (still 3-copies-in-1 for A, 2-in-1 for B) — same residual as below.
- Same CRC-block caveat as the existing `0x4141E` hook: `0x40e64`/`0x40dfc`/`0x40e30` all fall inside the
  `[0x13000, 0xC4FFC)` code CRC block (per `reference_accord_telemetry_ram_hook_a160.md`), covering the
  `0xC4E00` cave — any patch here needs the same CRC recompute.

**Recommended default is still the 0x40e64 single shared anchor below** (zero branch-reencode risk, satisfies
the mission's literal "not pc-relative" constraint with no caveats) unless the operator specifically wants
gate-exclusive physical hooks matching the Gate5/Gate7 pattern.

## Residual ambiguity (accurately reported, not resolved this session)

The shared-epilogue design means **r12 alone cannot distinguish WHICH param context fired** — e.g. r12==2 could
be the ENGAGED-context real disengage (mission's actual concern) or the ENGAGING-context pre-delivery precondition
refusal (state 1, LKAS not yet delivering — a different, lower-stakes event). Same for r12==5 (RE-ARM vs
ENGAGING). **Not resolved/needed for this audit**, but the mechanism to resolve it if wanted: `FUN_00040d58` is
entered via `prepare {lp},0` (0x40d58), which pushes the caller's return address onto the stack; since the anchor
at 0x40e64 executes BEFORE `dispose` (0x40e6a) unwinds that frame, a stub could read the saved `lp` off the stack
and match it against the 7 known call-site return addresses (0x41000/0x4119a/0x411f6=ENGAGING x3,
0x410a2/0x41280=ENGAGED x2, 0x41156=RE-ARM, 0x41364=HOLDING, all listed in
[[reference-accord-engage-sm-caller-enumeration-v34]]) to recover context. Untested this session — flagged as
the next step if per-context (not just per-gate) telemetry is wanted. Exact `prepare`/`dispose` stack-slot layout
for a single-register `{lp}` list is stated at moderate confidence (standard V850E convention: push at entry,
pop+return at exit) — not independently byte-verified against the ISA manual this session.

## Related
[[reference-accord-lkas-engage-sm-disengage-trigger]] — gate A signal identity, V33 disable, cal addresses.
[[reference-accord-engage-sm-full-dispatcher-and-trump-exits]] — full param 1/4 gate chain enumeration (source
of the gate-order table this session re-verified byte-for-byte).
[[reference-accord-engage-sm-caller-enumeration-v34]] — all 7 caller sites/return addresses used above for the
lp-disambiguation proposal.
[[reference-accord-deliver-commit-gate5-gate7-trampoline-anchors]] [[reference-accord-fun3c7fc-trampoline-anchor]]
[[reference-accord-telemetry-ram-hook-a160]] — sibling same-day trampoline audits; source of the branch
re-encode precedent and the free-RAM/cave/CRC-block conventions cited above.

## FLAG (not resolved this session, surfaced as a side effect) — gp-0x679C vs gp-0x67DC contradiction

`reference_accord_telemetry_ram_hook_a160.md` states flatly "`gp-0x67DC` does NOT EXIST in the binary... the
engage-SM state is at `gp-0x679C`" (0xFEDF1864), while
`reference_accord_engage_sm_full_dispatcher_and_trump_exits.md` §1 claims the OPPOSITE ("disp -26524 = -0x67DC
exactly... independently reconfirms... the gp-0x679c anchor is WRONG"). Arithmetic check done this session:
**-26524 decimal = -0x679C, NOT -0x67DC** (0x679C=26524, 0x67DC=26588) — so the full-dispatcher memory's own
cited number (-26524) matches its REJECTED label (0x679C), not its claimed corrected one (0x67DC). This looks
like a transcription slip in that memory, consistent with the telemetry-hook memory being right, but **this
was NOT independently re-verified this session** (out of scope — my anchor, `gp-0x35b6`/0xFEDF4A4A, is
unrelated to either of these). Flagging per project convention (ask before overwriting an existing memory) —
next session should re-disassemble `0x413ba` directly and settle which offset is real before trusting either
claim for the OUTER dispatcher-state variable.
