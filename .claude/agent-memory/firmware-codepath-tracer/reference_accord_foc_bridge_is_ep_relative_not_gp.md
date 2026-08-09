---
name: accord-foc-bridge-is-ep-relative-not-gp
description: WHY the Iq/Id torque-magnitude bridge has never been found — the PWM duty array is filled by ep-relative sld.hu from a pointer in r24 at 0x61370, and EVERY method this kit has run was gp-relative. Also closes FUN_000757a2 as a bridge candidate with an exact 0-intersection test.
metadata:
  type: reference
---

# The FOC delivery bridge is `ep`-relative — that is why 11 methods missed it

2026-08-09, `INSERTION-BLAST-RADIUS`, stock `code.bin`. Python exact scan + GhidraMCP
`disassemble_bytes dry_run:true`.

## The finding [EVIDENCE]

Sole writers of the PWM duty array (`gp-0x4e1c … gp-0x4dee`, 24 halfwords = 12 lockstep pairs)
are `0x61372`–`0x613e4`. Two instructions earlier:

```
0x6136e  mov    r24, ep
0x61370  sld.hu 0x0, ep, r7
0x61372  st.h   r7, -0x4e1c, gp
```

**The duty values arrive via `ep`-relative `sld.hu` from a pointer held in `r24`.**
The only gp-relative *loads* in that whole block are `gp-0x4f42` (`0x6135c`) and `gp-0x2bc0`
(`0x61350`) — both control flags, not data.

⇒ **Every torque-magnitude bridge hunt this kit has run was gp-relative and was therefore
structurally blind to this path.** Same failure shape as the `gp-0x6acc` miss recorded in
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]], one level deeper.

## What is now CLOSED [EVIDENCE]

1. **`FUN_000757a2` is NOT the bridge.** Exact set intersection: its 98 distinct gp-write offsets
   ∩ `FUN_00071272`'s 112 distinct gp-read offsets = **0**. It reads `gp-0x6b98` at `0x7580c`
   (CAN-427 torque model) but writes nothing the core reads.
2. **Two-hop test over every writer of every core input**: all apparent candidates resolve to
   addresses **below `0x757a2`**, i.e. inside `FUN_00071272`'s own body (core-internal scratch).
   Clean null.
3. ⇒ **`FUN_00071272` genuinely takes NO torque-magnitude input.** Its only externally-written
   inputs remain `gp-0x6c2c` (filtered rotor-speed derivative), `gp-0x6abe` (filtered rotor speed),
   `gp-0x6762` (mode byte). **It is a motor model / observer, not the torque servo.**
   This CORROBORATES rather than overturns [[accord-below-gp6b98-foc-delivery-path-swept]].

## Still OPEN — the exact next step

Who sets `r24` before `0x6136e`, and which function fills the buffer it points to.
**Method:** disassemble backward from `0x61372` (the region has **no Ghidra function** — use
`disassemble_bytes dry_run:true`), find the `r24` def, then find the caller.
🛑 A gp-relative scan will not answer this. Scan for `sld.*`/`sst.*` and `mov …, ep` instead.

## Tool note
`0x61372`, `0x431c4`, `0x42af8` all have **no defined function** in the current Ghidra import
(reports `analyzed:true`, `function_count:2086`). `search_instructions` / `get_xrefs_to` undercount
badly on this import — Python byte scanning is mandatory for any load-bearing count or null.

Related: [[accord-below-gp6b98-foc-delivery-path-swept]],
[[reference_accord_foc_inner_current_loop_architecture]],
[[accord-shaper-float-twin-blocks-filter-insertion]]
