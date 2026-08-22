---
name: reference_accord_gp67fa_state5_is_unreachable_constant5_is_unsourced
description: "SETTLES a 3-way contradiction in the record about gp-0x67fa's value while driving. 'State is a constant 5' is an UNSOURCED RELAYED BELIEF and is NOT supported; the 4->5 transition is provably dead (gp-0x67ba has ONE access image-wide and ZERO writers, gp-0x437c ZERO writers -- both re-verified by raw byte scan 2026-08-22). Best-supported reachable set is {4, 11}. Likely origin of the '5': confusion with the BUS STEER_STATUS field, which is NOT gp-0x67fa."
metadata:
  type: reference
---

# `gp-0x67fa` while driving: the record said three different things. Settled.

Adjudicated 2026-08-22 during the governor-ceiling trace, after I flagged the discrepancy to the
orchestrator. Program: stock `code.bin`.

## The three conflicting claims
| claim | source | grade |
|---|---|---|
| reachable set = **{11} alone** | `memory/MEMORY_CONSTELLATION.md:1087` | steady-state simplification |
| reachable set = **{4, 11}**; **state 5 is DEAD CODE on the road** | `memory/accord-state4-cadence-refuted-state-is-sticky.md` | **instruction-level EVIDENCE + a flown 0.0000%** |
| **"state is a constant 5 while driving"** | `reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered.md:28` | ⚠ **relayed, UNSOURCED** |

**The third is the odd one out and it does not survive.** Read in context, that line does not report a
measurement its author made — it says *"Team-lead's independent on-car evidence: V70's flown probe for
`gp-0x67fa==10` read 0.0000%, and **the standing measurement is** 'state is a constant 5 while driving.'"*
No probe, no cache, no address, no build. It is a **repetition**, and it contradicts a mechanism.

## The mechanism — RE-VERIFIED INDEPENDENTLY (raw Python LE byte scan, both gp encodings)
`accord-state4-cadence-refuted-state-is-sticky.md` claims 4->5 can never fire because `gp-0x68ad` can
never be set. I re-derived the supporting cells from scratch rather than trusting it:

| cell | 4-byte hits | gp WRITERS | gp readers | 6-byte form | other-base |
|---|---|---|---|---|---|
| **`gp-0x67ba`** | 1 | **0** | 1 (`ld.bu` @`0x567C4`) | 0 | 0 |
| **`gp-0x437c`** | 4 | **0** | 4 | 0 | 0 |
| `gp-0x679d` | 44 | **1** (`st.b` @`0x567E2`) | 43 | 0 | 0 |
| `gp-0x68ad` | 9 | 4 (2 are `st.b r0` = CLEAR; 2 are SET) | 3 | 0 | 2 |

⇒ **`gp-0x67ba` has exactly ONE access image-wide and ZERO writers.** Its only reader (`0x567C4`) sits
**30 bytes before** the SOLE writer of `gp-0x679d` (`0x567E2`) — same basic block. So `gp-0x679d` is
driven by a permanently-constant input, and `gp-0x437c` is never written at all. Both gate the two
`gp-0x68ad` SET paths ⇒ `gp-0x68ad` is never set in the field ⇒ `FUN_00019970` returns early ⇒
**the 4->5 transition never fires.** The prior claim reproduces exactly. **EVIDENCE.**

Corroborated on-car: **V70's flown bit5 (the state gate) read 0.0000%**.

## ⚠ The honest limit of a static "zero writers"
A static scan proving zero writers does **not** prove the RAM holds zero — a bulk `.data`/`.bss`
initialiser or a register-indirect/table-dispatched write is invisible to it. **This kit has been burned
by exactly that**: `gp-0x1500` passed BOTH static methods and still FAILED on-car (it was a
table-dispatched I/O mailbox at `0xb7260`) — see [[reference-accord-b7260-io-mailbox-array]]. So read
this as *strong* but not absolute. **It points the same way as the flown 0.0000%, which is what makes it
safe to act on.**

## Verdict
- **Use {4, 11}.** 11 is the steady-state driving value; 4 is the entry/boot state. "{11} alone" is a fair
  steady-state shorthand and nothing depends on the difference.
- **Do NOT propagate "constant 5."**
- 🛑 **Nothing downstream changes either way** — masks `0x830` {4,5,11}, `0xC30` {4,5,10,11}, `0xD30`
  {4,5,8,10,11} and `0x820` {5,11} all contain bit 11, so every state-gated block in `FUN_0002214a`
  fires on every tick regardless. See [[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]].
  This matters for *record hygiene*, not for any live conclusion.

## ⭐ Likely origin of the "5" — a DOMAIN CONFUSION, and it is a repeat offender
The kit separately measures the **CAN bus `STEER_STATUS` field** (cal `0xC64DF` = 100 is the
"`STEER_STATUS=4` dwell", measured at 100.00 ms). `memory/MEMORY.md` already carries the warning
**"🛑 Bus STEER_STATUS is NOT `gp-0x67fa`"** (`accord-gp67fa-state-gate-on-assist-chain.md`). A bus
`STEER_STATUS` of 5 read as a `gp-0x67fa` of 5 explains the claim exactly. **BELIEF** — plausible and
consistent, not proven. When you see a bare state number in this kit, **ask which domain it is in.**

⚠ **STALE LINE, not yet edited:** `reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered.md`
line 28 still carries the "constant 5" phrasing. I did **not** edit that file — operator approval needed
before amending an existing memory. This file supersedes that line.
