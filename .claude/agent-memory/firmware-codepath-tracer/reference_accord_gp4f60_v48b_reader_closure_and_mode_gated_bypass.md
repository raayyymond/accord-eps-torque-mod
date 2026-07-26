---
name: reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass
description: V48B TASK-1/2 closure session -- resolves the ~20 previously-unclassified gp-0x4f60 readers, and discovers a MAJOR correction to the operator's confirmed-carrier list -- the FUN_00034350/FUN_00034a72 direct gp-0x4f60 reads are MODE-GATED DORMANT in stock cal; the true live upstream carriers are FUN_0003b66a and FUN_0003b49a, neither of which was in the original confirmed-carrier list. Also relocates the injection hook to the true universal convergence point 0x7feac (not 0x7fce6).
metadata:
  type: reference
---

# gp-0x4f60 V48B feasibility -- reader closure + mode-gated-bypass correction (2026-07-21)

Full GhidraMCP trace on stock `code.bin`, follow-on to [[reference-accord-gp4f60-notch-filter-feasibility-v48b]]. Dispatched
to classify the ~20 previously-unclassified readers as carrier(X)/monitor(Y)/dead(Z), and to nail down injection
mechanics. Found something bigger than the classification task: **two of the operator's five originally-confirmed
carrier sites are dormant in the stock calibration**, and the two functions that actually feed those slots live
were NOT on the original list.

## HEADLINE FINDING: FUN_00034350 (damping) and FUN_00034a72 (boost) bypass their OWN gp-0x4f60 read in stock cal

Both functions read raw `gp-0x4f60` directly (`FUN_00034350@0x34392`, `FUN_00034a72@0x34ace` -- these are the
operator's own originally-confirmed sites) into a **local single/dual-stage IIR** (gains `tp+0x736e`/`tp+0x7372`,
values not dumped). But **immediately after**, each function branches on a **mode byte**:
- `FUN_00034350`: `ld.bu 0x7498[tp],r7; cmp 0x1,r7; be 0x34424` (`tp+0x7498` = cal `0xC6498`)
- `FUN_00034a72`: `ld.bu 0x7499[tp],r15; cmp 0x1,r15; be 0x34b6e` (`tp+0x7499` = cal `0xC6499`)

**Both cal bytes = `0x01` in stock** -- byte-verified fresh this session: `read_memory(0xC6498, 8)` →
`01 01 00 00 00 00 01 01`. When mode==1 (true in stock), the branch target loads `gp-0x6ba6`/`gp-0x6b9a`
**directly as the Factor-A gain-schedule index**, completely bypassing the function's own local
IIR-of-raw-gp-0x4f60 (`puVar11`/`iVar18`) computed just above it. That local IIR's result (and by extension the
`0x34392`/`0x34ace` read itself) is **only consumed for state persistence** (written back to
`gp-0x6df8`/`gp-0x6df4` unconditionally at function exit) and the mode≠1 fallback path -- **neither of which
is live in the stock cal**. So: **repointing just the operator's originally-confirmed `0x34392`/`0x34ace` sites
to a filtered copy would have ZERO effect on the live damping/boost output in stock configuration.**

## The TRUE live upstream carrier: FUN_0003b66a → gp-0x6ba6/gp-0x6b9a

`gp-0x6ba6` (abs magnitude) and `gp-0x6b9a` (signed) -- the values BOTH `FUN_00034350`@`0x34424`/`0x34428` and
`FUN_00034a72`@`0x34b6e`/`0x34b72` read in the mode==1 branch -- are produced **exclusively** by `FUN_0003b66a`
(`search_instructions` for "6b9a"/"6ba6": only writer is `FUN_0003b66a`@`0x3b892`/`0x3b8b0`, only OTHER readers
are `FUN_00034350`/`FUN_00034a72` themselves -- confirmed exhaustive, `truncated:false`).

`FUN_0003b66a` reads raw `gp-0x4f60` at **`0x3b672`** (`ld.h -0x4f60[gp],r9`) and `gp-0x4f62` (torque rate) at
`0x3b6a8`. The `gp-0x4f60` path feeds a **TWO-STAGE cascaded IIR**, both stages using the **SAME gain constant**
`tp+0x73ba` = cal `0xC63BA` (loaded twice, at `0x3b7ba` and again at `0x3b7d4`) -- byte-verified fresh this
session: `read_memory(0xC63B0,16)` → u16@`0xC63BA` = **512**. Q10 form `state += (target-state)*512>>10` = alpha
0.5 per stage. Two alpha=0.5 poles cascaded barely attenuate 21.4 Hz (combined corner ≈110 Hz at the confirmed
1 kHz task rate -- 21 Hz is under 1/5 of corner, roughly -0.5 to -1 dB combined). **Caller confirmed
`FUN_0002214a`** (the same ~1 kHz control task as the producer and both monitors) -- so this is a near-unity,
effectively-unfiltered carrier feeding BOTH damping's and boost's Factor-A in the live stock path.
**Recommend ADDING `FUN_0003b66a`@`0x3b672` to the repoint set (X).**
Note: it also reads `gp-0x4f62` at `0x3b6a8` for a separate float branch (column-angle combination) -- out of
this design's stated scope (gp-0x4f60 filtered copy only), flagged as an existing accepted scope gap, same as
r24/r26.

## Second live upstream carrier: FUN_0003b49a → gp-0x6b2a → FUN_00037fe6 → gp-0x6ad6 → FUN_0003a382 (ALREADY a confirmed carrier)

`FUN_0003b49a` reads raw `gp-0x4f60` at **`0x3b4a8`** (`ld.h -0x4f60[gp],r13`) into a **single-stage IIR** with
gain `tp+0x7408` = cal `0xC6408` -- byte-verified fresh: `read_memory(0xC6406,8)` → u16@`0xC6408` = **1024**
(exact Q10 unity -- `state_new == target` every cycle, same "1024=2^10 divides the >>10 shift with zero rounding
loss" argument already established for `FUN_0003a382`'s Stage A pole). **Completely unfiltered.** Result is
interpolated through a "moving curve" LERP and written to **`gp-0x6b2a`**.

`gp-0x6b2a` has exactly one other reader: `FUN_00037fe6`@`0x38096` (confirmed via `search_instructions`, 4 total
hits, other 4 are unrelated branch-target substring false positives excluded with stated reason).
`FUN_00037fe6` is a **6-lane weighted summer** (`gp-0x6bc2`,`gp-0x6b60`,`gp-0x6b2a`,`gp-0x6bce`,`gp-0x6b6e`,
`gp-0x6bbc`,`gp-0x6b70`, each individually magnitude-gated and weighted by cal bytes `tp+0x74ad..0x74b3`) plus a
base term from `gp-0x6b4a`, scaled by a LERP(`tp+0x69aa`) and clamped ±0x6400 -- output **`gp-0x6ad6`**.

`gp-0x6ad6` is read **only by `FUN_0003a382`** (`0x3a6ba`, `0x3a7ba`... exact addrs `0x3a6ba`/`0x3a798`) --
**the operator's own already-confirmed "resonance" carrier**. So `FUN_0003b49a` is a genuine, fully-unfiltered
upstream feed into an already-confirmed carrier, via one intermediate summing stage. All three functions
(`FUN_0003b49a`, `FUN_00037fe6`, `FUN_0003a382`) confirmed called by `FUN_0002214a` (1 kHz task).
**Recommend ADDING `FUN_0003b49a`@`0x3b4a8` to the repoint set (X).** (`FUN_00037fe6` itself does not read
gp-0x4f60 directly -- no repoint needed there, it only consumes `FUN_0003b49a`'s already-filtered-copy-eligible
output once `FUN_0003b49a` is repointed.)

## Third candidate found and CLOSED (currently dormant, no action needed): FUN_0003fc16 → gp-0x6a10

`FUN_0003fc16` conditionally computes `gp-0x6a10` (Factor-C's index in BOTH `FUN_00034350`@`0x34582` and
`FUN_00034a72`@`0x34c20`, gated on `gp-0x67fe==1|2`) from `(gp-0x4f60*10)/gp-0x4ebc`, gated on
`*(char*)(tp+0x74cf)!=0 && gp-0x4ebc!=0`. Byte-verified fresh: `read_memory(0xC64CE,4)` → `tp+0x74cf` =
cal `0xC64CF` = **0x00** in stock. **Gate closed in stock -- this path is dormant**, `gp-0x6a10` instead sources
from `gp-0x6a02` (an angle-domain signal, not gp-0x4f60-derived) in the live branch. No repoint action needed;
flagged so a future cal change to `0xC64CF` would need re-review.

## Final classification table (all previously-unclassified readers resolved)

**X -- ADD to repoint set (carriers, confirmed this session):**
- `FUN_0003b66a`@`0x3b672` (`ld.h -0x4f60[gp],r9`) -- feeds damping+boost Factor-A via gp-0x6ba6/gp-0x6b9a
- `FUN_0003b49a`@`0x3b4a8` (`ld.h -0x4f60[gp],r13`) -- feeds FUN_0003a382 (confirmed carrier) via gp-0x6b2a→gp-0x6ad6

**Y -- keep RAW (monitor/diagnostic/dead-mode, confirmed this session):**
- `FUN_0001bf88`, `FUN_0001c1ce` -- periodic diagnostic/CAN snapshot dispatch (caller `FUN_0001c306` is a
  counter-gated periodic dispatcher calling `FUN_0001cd96`, a CAN/UDS record builder; `FUN_0001bf88` itself
  calls `FUN_00059912`, the already-known diagnostic packer)
- `FUN_0004d8f0`, `FUN_0004de0c` -- UDS/RDBI byte-packers (56-byte fixed records, `param_1+0xc=0x38` length
  field). `get_function_callers` FALSELY reported these as unreachable ("No callers") -- **corroborated as a
  misleading zero**: `search_byte_patterns` found their addresses as raw little-endian pointers in a dispatch
  table (`0xB7834`→FUN_0004ddfc→FUN_0004d8f0; `0xB7848`→FUN_0004e368→FUN_0004de0c), consistent with the known
  RDBI dispatch table region (`0xB77FC`). Second-method corroboration caught what direct-call xrefs missed.
- `FUN_00069b8e` -- multi-signal plausibility gate (`|gp-0x6b98|`,`|gp-0x6abc|`,`|gp-0x4f60|` vs thresholds
  `tp+0x590a/0x5912/0x590e`); failure path calls `FUN_0006b9ee` (the SAME shadow-fault latch used by gp-0x4f60's
  own shadow pair). Matches operator's own framing exactly.
- `FUN_0008159e` and `FUN_00080a54` -- **BOTH confirmed cross-channel plausibility monitors**, dual
  corroboration: (1) structural -- both recompute a position/angle from the raw torque value via a
  transform+LERP, compare against a stored/expected value with a tolerance window, and on repeated failure call
  a DTC-setter (`FUN_0006ce7c(6)` in `FUN_0008159e`; a full debounce/confirm DTC chain in `FUN_00080a54`,
  reaching `FUN_0006b9ee` for a wrap-consistency check at `0x505e/0x5062` and DTC dispatch via
  `FUN_0005ae6a`/`FUN_0005afba`/`FUN_0005b650`/`FUN_0005b68c`); (2) shared enable-gate -- both branches key off
  the SAME flag `gp-0x4e5f=='\x01'`. No literal "C1420" string exists in the image (confirmed, consistent with
  DTC text not stored on-ECU), but functionally this is exactly a Main/Sub torque-sensor correlation check.
  **Both MUST stay raw.**
- `FUN_0003fc16` -- gp-0x4f60 branch present but DEAD in stock cal (`tp+0x74cf`=0, see above). Not a live
  consumer either way; no repoint action, but do not repoint it either (would be a no-op that adds risk for
  zero benefit if the gate ever flips).
- `FUN_00028ea6` (`m_steer_torque_arbitration`) -- role already settled by prior verified memory
  ([[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]]): driver-override/engagement logic, not a
  base-assist carrier. Keep raw.
- `FUN_0003b8f6` -- MODERATE confidence Y. Computes a magnitude/validity-style value (`gp-0x6bf6` clamped
  ±20000, `gp-0x6bfc` sentinel-on-invalid) consumed by `FUN_0003bc20` → `gp-0x6bfe`/`gp-0x695c`, which are
  **bit-tested** (not multiplied) by several functions including dead code and status-flag consumers
  (`FUN_00052ade`, `FUN_00054764`, `FUN_00066ab6`) -- consistent with a plausibility/validity flag rather than a
  magnitude-carrying carrier. Not as rigorously closed as the others; flagged lower-confidence.

**Z -- dead code, confirmed via zero callers (no corroboration needed, genuinely orphaned, not table-dispatched):**
- `FUN_0004e378`, `FUN_0004e82e` -- zero callers via `get_function_callers`. (Not re-checked via byte-pattern
  scan for a pointer-table reference the way `FUN_0004d8f0`/`FUN_0004de0c` were -- residual risk, see Open
  Questions.)

**UNRESOLVED / BLOCKERS -- could not confidently classify this session, flag for dedicated follow-up:**
- `FUN_0002b62c`, `FUN_0002db94`, `FUN_00033d10` -- all called by `FUN_00022ca0` (the ~100 Hz assist-shaping
  task). `FUN_0002db94` in particular reads `gp-0x4f60` (negated, `sVar11 = -gp-0x4f60`) and structurally
  matches the "friction falls with torque" lane already noted in `memory/reference_accord_damping_friction_returncentre_torque_gates.md`
  -- i.e. this is very likely the FRICTION lane's producer function, parallel in role to `FUN_00034350`
  (damping). `FUN_0002b62c` looks like the return-centre/state-machine classifier from the same memory. Given
  their outputs (many `gp-0x6aXX`/`gp-0x6cXX` cells) were not traced to a final consumer within this session's
  budget, **do not assume these are inert** -- they are structurally parallel to the confirmed damping carrier
  and deserve the same scrutiny FUN_00034350 got.
- `FUN_0003f884`, `FUN_0004c780` -- both called by `FUN_0002351e` (the engage-SM state-bitmask dispatcher),
  gated on the SAME state-bit mask (`uVar2 & 0x930`). Not traced further.
- `FUN_0004fbde` -- called by `FUN_0002214a` (the 1 kHz task, same as the confirmed carriers) -- membership in
  this task makes it a real candidate, not traced further; reads gp-0x4f60 twice (`*-10` pattern, looks like a
  unit conversion, e.g. counts→Nm or similar).

## Injection hook -- CORRECTED from the prior session's proposal

The prior V48B memory proposed hooking "after `0x7fce6`, around `FUN_0007e74a()`" -- that address is real (one
of several branch-local `st.h -0x4f60[gp]` stores) but is **NOT the universal convergence point**. Fresh full
disassembly of `FUN_0007f3f8` this session found **~10 separate branches**, each ending in its own
`ld.h -0x4f60[gp],r8` immediately before a `jr`/fallthrough to a single shared address:

**`0x7feac`: `cmp r0,r8`** (2 bytes) followed by **`0x7feae`: `mov r8,r14`** should read **`0x7feac: cmp r0,r8`**
then **`mov r8,r14`** -- every one of the ~10 branch exits (`0x7f9e6`,`0x7fcb6`,`0x7fcc6`,`0x7fcfa`,`0x7fd06`,
`0x7fd34`,`0x7fdf2`,`0x7fe88`,`0x7fe9a`,`0x7fea8`) reloads `gp-0x4f60` fresh into `r8` and lands here. This is
the compiler's shared epilogue -- `r8` is GUARANTEED to hold the fully-settled `gp-0x4f60` value at `0x7feac`
regardless of which branch fired. **`cmp r0,r8`** (2B) + **`mov r8,r14`** (2B) = exactly 4 bytes = one `jarl`.
Trampoline: `jarl <cave>` at `0x7feac`, displacing those two instructions (relocate them verbatim into the
cave), run the biquad on `r8`, store to the new RAM cell, execute the displaced `cmp`/`mov`, `jr 0x7feb4`
(the original next instruction, `bge 0x7feb4`). Distance `0xC4B34 - 0x7feac` ≈ 0x44694 (~280 KB), well within
`jarl`'s ±2 MB range.

⚠ This is a genuine correction, not a restatement -- the old proposal named a real but non-universal store site;
this one is verified (by exhaustively following every branch) to be the true single reconvergence point.

## RAM + cave -- re-confirmed a third time, fresh this session

- `search_instructions` for `-0x1500` and `-0x14e0`: **0 matches each**, 186069 instructions scanned,
  `truncated:false` -- reproduces the zero-reference finding independently for a third session.
- `read_memory` at `0xFEDF6AF8` (adjacent to gp-0x1500/gp-0x14E0): **"Unable to read bytes"** -- confirms
  genuinely unbacked RAM (not flash-backed data Ghidra can show).
- Cave: `read_memory(0xC4B34, 64)` = all `0xFF`. `read_memory(0xC4FC0, 64)` = `0xFF` through `0xC4FEF`, then
  **`0xC4FF0` = `0x01`** (non-FF) -- confirms the cave's exact upper bound is `0xC4FEF` (1212 bytes total,
  `[0xC4B34,0xC4FF0)`), matching the previously-documented size exactly.

## Related
[[reference-accord-gp4f60-notch-filter-feasibility-v48b]] -- the prior session's initial classification this one extends/corrects.
[[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole]] -- source of the "1024=unity, zero rounding loss" argument reused here for FUN_0003b49a's gain.
[[control-task-tick-confirmed-1khz]] -- rate confirmation reused for FUN_0003b66a/FUN_0003b49a/FUN_00037fe6.
[[reference_accord_damping_friction_returncentre_torque_gates]] -- background for the FUN_0002db94/FUN_0002b62c blocker items.
