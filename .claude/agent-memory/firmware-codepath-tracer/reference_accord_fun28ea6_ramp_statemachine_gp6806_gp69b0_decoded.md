---
name: reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded
description: Full disassembly-level decode of the 9-state (gp-0x3d38, states 0-8) LKAS engage-ramp state machine inside FUN_00028ea6 that jointly owns gp-0x6806 (deadband/relay gate) and gp-0x69b0 (ramp gain). CONFIRMS the gate reaches 0 (deadband ACTIVE) while the ramp is at FULL SCALE (0x8000) via a shared exit block (LAB_000296c6) that never touches gp-0x69b0 -- refuting a same-cycle-adjacency assumption for that specific site while confirming it for three others. Rules out a direct 20-25Hz chopper on arithmetic grounds (fastest decay ~99 cycles/~99ms from full scale) but leaves the upstream trigger (gp-0x1426, a CAN-derived byte with zero found writers) as the one unresolved link.
metadata:
  type: reference
---

# `FUN_00028ea6`'s engage-ramp state machine -- decoded 2026-07-29 for team-lead's decision-bearing "is the LKAS forward-path deadband gate live-on-a-delivering-signal" question

Entry point: `FUN_00028ea6` (live arbitration), state variable `gp-0x3d38` (byte, 9 states 0-8), confirmed
PRIVATE to this function (whole-image `search_instructions` on "3d38": 11 hits, 9 real -- 1 read
`0x29322` + 8 writes, all inside `FUN_00028ea6`; the other 2, `movhi -0x3d38,r0,rX` at `0x2804e`/`0x28056`
in `FUN_00027b0a`, are 32-bit immediate-constant loads, NOT gp-relative accesses -- excluded, same
operand-text-collision false-positive class already on record in this kit). Sole caller of
`FUN_00028ea6` is `FUN_0002214a`, the confirmed 1kHz control task -- every cycle count below is ms.

## State dispatch table (`0x29322-0x29356`, byte-verified)
```
STATE 0 -> 0x2935a   STATE 1 -> 0x29362   STATE 2 -> 0x295b4   STATE 3 -> 0x29436
STATE 4 -> 0x294bc   STATE 5 -> 0x29408   STATE 6 -> 0x29514   STATE 7 -> 0x2965e
STATE 8 -> 0x2961c   (any other value, incl. implicit 0 at cold boot) -> 0x2935a
```
Two mirror-image ramp families, direction selected by `gp-0x6803` (0 or 2; 1=neutral):
- Direction 0: STATE1(idle)->STATE3(ramp +33/cyc)->STATE2(saturated hold, ramp=0x8000)->STATE5(decay
  -328/cyc)->STATE1(reset). STATE3 can shortcut to STATE4(decay -16/cyc) if the request drops mid-ramp.
- Direction 2: STATE1->STATE6(ramp +328/cyc)->STATE7(saturated hold)->STATE5(shared decay)->STATE1.
  STATE6 can shortcut to STATE8(decay -66/cyc).
Cals, fresh `read_memory`, LE: `tp+0x73f4`(`0xC63F4`)=**328** (ramp-down TRIGGER ceiling),
`tp+0x73f6`(`0xC63F6`)=**16** (dir-0 settle/decay step), `tp+0x73f8`(`0xC63F8`)=**33** (dir-0 ramp-up
step), `tp+0x73fa`(`0xC63FA`)=**66** (dir-2 settle/decay step), `tp+0x73fc`(`0xC63FC`)=**328** (dir-2
ramp-up step, 10x faster than dir-0's).

## Joint (`gp-0x6806`, `gp-0x69b0`) pairs -- adjacency CHECKED against real control flow, not assumed

**CONFIRMED adjacent, same basic block, unconditional:**
- `0x29724`(gate<-0) / `0x2972a`(ramp<-0) -- shared RESET (`LAB_0002971a`). Harmless.
- `0x293a6`(gate<-1) / `0x293ac`(ramp<-33), and `0x293e4`/`0x293fe` (dir-2, ramp<-328) -- STATE1 engage
  entry. Gate bypasses exactly as ramp becomes nonzero but TINY.
- `0x2948c`(gate<-1) / `0x29494`(ramp<-0x8000), and `0x2958c`/`0x29594` (dir-2 mirror) -- saturate
  branches. Gate stays bypassed at full scale.
- `0x2970e`(gate<-0) / `0x29714`(ramp<-ramp_old-16) -- `LAB_000296f8`, request drops mid-ramp. Ramp
  becomes `ramp_old-16`, nonzero unless the ramp had barely started.
- `0x29696`(gate<-0) / `0x2969c`(ramp<-ramp_old-66) -- `0x29680`'s settle entry (dir-2 mirror of 296f8).

**🛑 REFUTED for one site -- no adjacent ramp-write at all:** `0x296d2`(gate<-0), inside `LAB_000296c6`
(also entered via `0x296c6`/`0x29528`/`0x29538`/`0x29544`/`0x295c8`/`0x295d8`/`0x295e4`/`0x296b2`/
`0x296bc`), sets `STATE=5, gp-0x679f=7, gate=0` and **does NOT write `gp-0x69b0` at all**. Reached from
STATE2/STATE7 (the saturated-hold states, where ramp is verified `0x8000` -- set there by the saturate
branches and never rewritten before this exit). **Consequence: `gp-0x6806` flips from 1 (bypassed) to 0
(deadband/relay ACTIVE) at the exact instant `gp-0x69b0` is at FULL SCALE (32768, unity Q15), not a small
residual** -- the most severe version of the "gate live on a delivering path" concern. Triggered by
`gp-0x6803==1(neutral)&&gp-0x6805==0` (STATE2) or the direction-2-equivalent (STATE7), OR
`gp-0x6807∈{4,7}` (dead on the current build, see below).

## Runtime reachability on the CURRENT build

Every `gp-0x6807`(STEER_STATUS)==3/4/7 check in this state machine (`0x29444`, `0x2944c`/`0x29450`,
`0x294d2`/`0x294d6`, `0x2967a`, `0x296bc`, `0x296f0`, etc.) is **DEAD CODE on this car right now**, per
team-lead's already-established facts (`0xC62EA=0` since V53 => ST=3 unreachable; `0xC64B8=0xFF` since
V37 => ST=4/7 unreachable). **The `gp-0x6803`/`gp-0x6805`-gated paths do NOT depend on STEER_STATUS at
all and remain fully LIVE** -- they fire purely on `gp-0x6803==1(neutral)&&gp-0x6805==0`.

Traced both to their producer, `FUN_00052676`:
```c
bVar4 = *(byte *)(gp - 0x1426);
gp-0x6803 = bits[3:2] of bVar4;    // 2-bit direction field
gp-0x6805 = bit7 of bVar4;         // engage/request trigger
```
gated by `(gp+0x6400 & 8)==0` else pinned to a `0xFF` sentinel, plus a reset path on certain `param_1`
values. **`gp-0x1426` has ZERO writers found (both disp16 and extended-disp23 encodings via
`search_instructions`) and `FUN_00052676` itself has no static callers** (`get_function_callers`/
`get_xrefs_to` both null) -- the same register-indirect/RTOS-table blind spot this kit has hit before on
CAN RX payloads (e.g. the wheel-speed extractors). **NOT resolved this session: what CAN signal `gp-0x1426`
decodes, or `FUN_00052676`'s actual invocation rate.** This is the single open link.

## (A) inert vs (C) chopper -- neither, bounded quantitatively

**Not (A):** gate demonstrably reaches 0 while ramp is nonzero (two confirmed mechanisms above).

**Not a clean (C) either -- ruled out by the state machine's OWN rate constants.** Fastest decay is
STATE5 at `-328/cycle`, 1kHz confirmed. Full decay from `0x8000` to the reset threshold (328) takes
`(32768-328)/328 ≈ 99 cycles ≈ 99ms`. **A full up-ramp-decay-reset round trip completing within one
20-25Hz period (40-50ms) is arithmetically not achievable here** -- the numbers support roughly
low-single-digit-Hz to ~10Hz for a clean full cycle. If `gp-0x1426`'s underlying CAN signal itself
chatters at 20-25Hz, the gate would show PARTIAL, incomplete ramps (never fully saturating or resetting)
rather than a clean chopper -- a different, messier signature, and not evidenced either way this session.

**Verdict: reject a clean (C) as originally framed (arithmetically implausible from this SM's own
constants); reject (A) too (gate provably reaches 0 at full ramp, twice-confirmed). The real
characterization is "a genuine, reachable, ordinary-driving transition on every engage-state-adjacent
change, with a natural ~3-10Hz decay time constant" -- whether `gp-0x1426`'s source has its own fast
component is the open next question, not this state machine's arithmetic.**

## Section placement of `gp-0x6806`

No writer found anywhere outside `FUN_00028ea6` (21 total hits on "6806" whole-image: 8 writes + 1
in-function read inside `FUN_00028ea6`; 12 more are READS from 6 OTHER functions --
`FUN_0002eda8`(already on record as the live lane-9 command path), `FUN_0002fab6`, `FUN_00030c26`(5
reads), `FUN_00042746`, `FUN_0004fbde`, `FUN_00055c42` -- `gp-0x6806` has readers well beyond the one
consumer this task focused on, not chased further this session). No boot/init routine writes it directly.
Could not directly prove BSS-zero-at-reset from a section/loader table this session -- but it's moot in
practice: `gp-0x3d38`'s implicit cold-boot value of 0 dispatches to STATE 0, which unconditionally jumps
to the RESET handler and sets `gp-0x6806=0` on the very first call regardless of pre-existing RAM
content. **Observable gate value is 0 (deadband active) from the first control-task cycle either way.**

## Related
This is the block immediately upstream of `gp-0x6b4c`/LKAS lane's producer chain
([[reference-accord-gp6b4c-lane-chain]], [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]).
The consumer this task decoded (`0x2a1ae-0x2a206`) is the SAME site already established as
`0xC646C` reader #1 in [[reference_accord_c646c_gain_feedback_vs_forward_classification]] -- cross-
validated this session: `gp-0x6b30`'s stored value is NOT simply the ramp-multiplied deadband output, it's
further combined with the 4x-gain*polarity term before storage, matching that file's existing
characterization of this exact site exactly.
