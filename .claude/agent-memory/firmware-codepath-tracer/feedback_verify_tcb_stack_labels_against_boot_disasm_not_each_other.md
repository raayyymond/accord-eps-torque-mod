---
name: feedback_verify_tcb_stack_labels_against_boot_disasm_not_each_other
description: TRACE-2026-09-06-lag-and-fb-pole-census-v282.md labels 0xBB920+0x00 (0xFEDF70C8) "stack pointer" and +0xC (0xFEDEC000) "stack base" for TCB record 0, without disassembly proof. Those two values bracket gp-0x86E4..gp-0xF38, which would swallow gp-0x6a32 (an already-relied-on RAM cell) if taken as the live stack range. The AUTHORITATIVE stack bound, from actual boot-code disassembly (reference_accord_app_ram_layout_and_boot_init_loops.md, 0x140A8-0x147F6), is gp-0xC000..gp-0x86E4 (sp=0xFEDEF91C at entry, canary-painted down to 0xFEDEC000) -- entirely BELOW (more negative than) the TCB-guess range and outside it. The TCB field labels are therefore either wrong or mean something other than "live stack pointer/base" for this record; do not use them for a stack-overlap exclusion.
metadata:
  type: feedback
---

# Don't take an unverified TCB field label as ground truth for a stack boundary — check the boot disassembly instead

2026-09-08, subagent `tracer`. Surfaced while re-censusing RAM for `loopshape`'s biquad-state request:
the systematic full-range free-cell scan found hundreds of "free" halfwords at large negative gp
displacements, and before reporting them I checked whether they could be live stack — using a labelled
field from an EARLIER trace (`TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` §"TASK 3.1", the RTOS TCB
dump at `0xBB920`) that calls `+0x00` "stack pointer" (`0xFEDF70C8`) and `+0xC` "stack base"
(`0xFEDEC000`) — **without any disassembly evidence backing those two specific labels**, just field
position in a 48-byte record whose OTHER fields (entry point, attribute word) WERE independently
verified.

## Why this mattered

Taking `0xFEDF70C8`/`0xFEDEC000` at face value as the live stack's bounds gives a range of
`gp-0x86E4..gp-0xF38` — which **would have swallowed `gp-0x6a32`** (this kit's own, already-relied-on
V288 setpoint-filter state cell, and dozens of other confirmed-real cal/state cells this session
independently verified in the same neighbourhood). That is a contradiction: a cell this kit already
trusts and uses cannot simultaneously be live stack memory. Something in the TCB-label chain was wrong.

## The resolution — an EXISTING, more authoritative memory already had the real answer

[[reference_accord_app_ram_layout_and_boot_init_loops]] derives the stack bound from actual disassembly
of the app's own entry code (`0x140A8`-`0x147F6`): `sp = 0xFEDEF91C` at entry, and the runtime paints
`0xFEDEC000..0xFEDEF920` with the `0xEBEBEBEB` canary — i.e. **the real stack is
`0xFEDEC000..0xFEDEF91C`, or `gp-0xC000..gp-0x86E4`**. This is a WHOLE DIFFERENT, much narrower and more
negative range than the TCB-guess, and it sits entirely BELOW (never overlaps) any displacement a
disp16 instruction can even encode (`gp-0x8000` is the disp16 floor). **`gp-0x6a32` and everything else
this kit works with via ordinary `ld.h -0xNNNN,gp,rX` is structurally impossible to be inside the real
stack** — the scare was real to raise, but resolved by evidence already on file, not asserted away.

**Why:** an unverified label on one field of a data structure, even when neighbouring fields in the SAME
structure were independently confirmed, is not itself confirmed — a plausible name is not evidence.
Two prior kit incidents share this shape: the `0x21` Format-V `jarl` mask bug (a plausible-looking bit
field that was wrong) and `gp-0x1500` (passed both static census methods and still failed on-car).

## How to apply

Before trusting ANY field label in a raw structure dump (a TCB, a descriptor table, a config record)
for a SAFETY-RELEVANT exclusion (stack overlap, mailbox range, poison range), check whether this kit
already has a DISASSEMBLY-DERIVED answer for the same question — `reference_accord_app_ram_layout_and_boot_init_loops.md`
is that answer for RAM layout/stack bounds specifically — and prefer it over a same-session guess from
an unverified structure field, even one from a prior trace. If no such memory exists, derive the bound
from disassembly directly (as that memory did) rather than from a labelled-but-unverified field.

Flagging `TRACE-2026-09-06-lag-and-fb-pole-census-v282.md`'s "stack pointer"/"stack base" labels as
suspect for whoever owns that file — NOT correcting them myself, per the operator's "ask before updating
a memory that looks stale" rule; this note documents the discrepancy and its resolution, not a fix to
that file.
