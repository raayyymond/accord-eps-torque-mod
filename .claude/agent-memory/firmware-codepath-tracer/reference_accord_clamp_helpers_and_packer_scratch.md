---
name: reference-accord-clamp-helpers-and-packer-scratch
description: FUN_00049a90/49a78/49a5a are pure cmov leaves whose Ghidra "in_r10" is an artefact, and FUN_00055d80 saves r6/r7/r8 without ever restoring them
metadata:
  type: reference
---

🛑★★★★★ **Ghidra's `int in_r10` in the arithmetic leaf helpers is a `cmov` ARTEFACT, not a real
dependency — but you must read the assembly to know which.** Ghidra models `cmov cc,reg1,reg2,reg3`
as reading reg3, so any helper that cmovs into `r10` decompiles as if it consumed an incoming r10.

The three leaves (all pure: no memory, no calls, no `fa42`/`fa72`, so deleting a call to one has no
side effect and cannot unbalance the interrupt-depth counter at `gp-0x163c`):
- `FUN_00049a5a` = **abs(r6)** -> r10. 9 instructions.
- `FUN_00049a78` = **UNSIGNED min(r6,r7)** -> r10 (`cmovnc`). 3 instructions.
- `FUN_00049a90` = **clamp(r6, lo=r7, hi=r8)** -> r10:
  ```
  cmp r8,r7 / cmovgt r8,r10,r10 / cmovgt r7,r8,r8 / cmovgt r10,r7,r7   <- lo/hi SWAP, r10 is the TEMP
  cmp r7,r6 / cmovlt r7,r10,r10 / blt END / cmp r6,r8 / cmovge r6,r8,r10 / END: jmp [lp]
  ```
  **cmov always writes its destination**, so r10 is defined on BOTH return paths and incoming r10
  never leaks out. Incoming r10 is only *read* by the swap block, which fires only when `lo > hi` —
  impossible whenever lo/hi come from immediates at the call site. So a caller need NOT set r10.

★★★★ **`FUN_00055d80` (the CAN 0x1AB / 427 packer) SAVES r6, r7 and r8 to frame slots 0x8/0xC/0x10
and NEVER RESTORES THEM** — the epilogue reloads only `lp` (0x4) and `r28` (0x0), and there is no
`sld.w`/`ld.w` of those slots anywhere in the body (`ep` is set once at 0x55D84 and never
reassigned). Those three are therefore DEAD SCRATCH across the whole function: an in-place rewrite
of the value path may clobber r6/r7/r8 freely. Only r28 and lp are actually callee-saved here.

Frame layout it builds (buffer `gp-0x13CC`, DLC 3, ID 0x1AB, checksum `FUN_00057b24`):
byte0 `gp-0x13CC` bit3 <- gp-0x685b, bit4 <- gp-0x685a, bit7 <- the 0x6409 branch; byte1 `gp-0x13CB`
= the 10-bit value's low 8 (via `FUN_00021864`, which also puts bits 9:8 in byte0[1:0]); byte2
`gp-0x13CA` bit6 <- FUN_0004d0ac, bits[5:4] rolling counter (3-bit mod-8 in `gp-0xf47`[6:4], low 2
bits on the wire), bits[3:0] checksum. Dispatched from a function-pointer table entry at `0xB72C8`,
not by any `jarl`.

Also: `gp-0x674B` is written `abs`-then-**`zxb`** (`0x29CF8 bge/subr`, `0x29D12 zxb r22`,
`0x29D14 st.b`), so it is a MAGNITUDE, hard-bounded u8 — no sign wrap under `ld.bu`, but the steer
DIRECTION is not recoverable from it, and it holds its last value when the LKAS PID path does not run.

Related: [[reference_accord_can427_packer_tap_field_full_decode]] ·
[[reference-accord-v850-load-opcode-map-ldhu-0x3e]] · [[reference-accord-variant-selector-max-is-nine]]
