---
name: reference-accord-op-0e4-steer-command-full-path
description: Full verified path of the openpilot CAN 0x0E4 STEER_TORQUE command through the 2020 Accord EPS -- intake at 0x0BB640, handler FUN_00052676, exactly 3 readers of gp-0x69ae. CORRECTED 2026-09-01 -- the clamped command MAGNITUDE DOES reach the motor: r22 is the multiplicand at 0x29CBC. An earlier version of this note claimed it did not.
metadata:
  type: reference
---

Stock `code.bin` (39990-TVA-A160). All addresses are absolute file/program offsets.

## Intake (EVIDENCE)
- CAN dispatch-table entry at **`0x0BB640`**: bytes `... 0100 e400 01000000 d86bdffe 0f000000 76260500 08000000 ...`
  → **ID `0x0E4`**, RX buffer **`0xFEDF6BD8` = `gp-0x1428`**, handler **`FUN_00052676`**, DLC 8.
  (Found by Python search for LE `0x00052676`.)
- `FUN_00021724` (@0x21724, sole caller FUN_00052676) reads `gp-0x1428`/`gp-0x1427` under
  FUN_0001fa42/FUN_0001fa72 → `CONCAT11(b0,b1)` = raw big-endian STEER_TORQUE.
- `FUN_00052676`: `FUN_00049a90(raw * -4, 0xffffc000, 0x4000)` → **`gp-0x69ae`** (st.h @0x5268c).
  Fault/timeout paths write sentinel `0x7FFF` (@0x526f2, 0x52726, 0x527c6).
  Byte 2 of the frame (`gp-0x1426`) is split into `gp-0x6803` (bits3:2), `gp-0x6804` (bit6),
  `gp-0x6805` (bit7), `gp-0x6802` (bits1:0).

## Reader census of `gp-0x69ae` (= 0xFEDF1652) — EVIDENCE, two independent methods
`search_instructions` and an uncontrolled-free Python LE scan for hw2 ∈ {0x9652,0x9653} over the
whole 1 MB image both return **exactly 7 sites, identical set** (positive control: the scan finds all
4 known writers). Also checked: no `ld.w`/`st.w` at `gp-0x69b0` (enc 0x9651 op 0x39) that would alias
the cell as the high half of a word — every 0x9651 hit is `ld.hu` of `gp-0x69b0` itself.
- Writers: 0x5268c, 0x526f2, 0x52726, 0x527c6 (all FUN_00052676).
- Readers: **0x29032**, **0x29124** (FUN_00028ea6) and **0x4e840** (FUN_0004e82e, the UDS/telemetry
  frame packer — reports `cmd*13/4` clamped ±0x7FFF).

## What FUN_00028ea6 does with it — it is a GATE, not a summand (EVIDENCE)
- `0x29032 ld.h -0x69ae,gp,r13` → clamped against a speed-interpolated limit from
  `(&PTR_LAB_000cb844)[gp-0x674e]` (x-axis `gp-0x6a5e`): `0x2903a cmp r22,r13` / `0x2903e bgt` /
  `0x29044 cmovle r16,r13,r22` ⇒ **r22 = clamp(cmd, ±Lim(speed))**.
  🛑 **r22 IS THE MULTIPLICAND AT `0x29CBC`. Its magnitude propagates.** The zero tests
  `cmp r0,r22` at **0x291f6** / **0x29224** are REAL but are ADDITIONAL uses (they feed the
  driver-override debounce counter `gp-0x6758`/`gp-0x6757`, with `gp-0x682f` = |`gp-0x4f60`|>>5 vs
  threshold `tp+0x74b8` = 0xC64B8). They are not the only uses. `r22` is live for ~0xC90 bytes.
- `0x29124 ld.h -0x69ae,gp,r9` → `addi 0x4000,r9,r7; cmp 0x8001,r7; setfc r8` ⇒ validity gate
  "cmd ∈ [-0x4000,+0x4000]" (i.e. not the 0x7FFF sentinel).
🛑🛑 **CORRECTED 2026-09-01 — THE OPENPILOT TORQUE MAGNITUDE *DOES* PROPAGATE TO THE MOTOR.**
An earlier revision of this note concluded the opposite. It was wrong, and the error is instructive:
**two different agents in one session tracked `r22`, found the zero-tests first, stopped, and declared
the magnitude dead.** `r22` is consumed roughly `0xC90` bytes after it is set. Fresh
`disassemble_bytes(0x29CB0, 96)`, EVIDENCE:

```
00029cb4  mulu  r6, r10, r0      ; r10 = surfaceA × surfaceB  (the two driver-torque LERPs)
00029cb8  andi  0xffff, r10, r7  ; r7  = low 16 bits of that product
00029cbc  mul   r22, r7, r0      ; r7  = r7 × r22        <-- THE CLAMPED COMMAND, AS A MULTIPLICAND
00029cc0  sar   0x10, r7         ; >>16
00029cd6  sar   0x6, r7          ; >>6
00029cdc..00029cf4               ; clamp to ±cal(tp+0x74f0 / 0x74f1) = 240
00029cfc  mov   0xc9a88, r16     ; index the ASSIST MAP with the result
```

So: `index = clamp( taper(|driver torque|) × 255 × clamp(cmd, ±Lim(speed)) >> 16 >> 6 , 240 )`, and
the assist-map output is the rate setpoint `gp-0x6a32`. The decompiler corroborates — the variable
Ghidra names `uVar33` holds the clamped command and is the third operand of
`iVar31 = (int)((iVar31 * uVar30 & 0xffff) * uVar33) >> 0x10`. There IS an intervening `uVar33 = 0`,
but it sits in the other arm of `if (*(char *)(gp - 0x680a) == '\x01')` and does not reach the multiply.

⚠ **METHOD RULE THIS COST US:** a register's uses are not exhausted by the first branch you walk.
Before asserting "value X never propagates", scan the WHOLE function body for that register as a
source operand — and treat a null here as load-bearing, so positive-control it.

⊕ The taper direction also matters and is easy to invert: `0xCBA04`/`0xCBA74` are X `70 72 78 80` →
Y `254 234 12 0`, indexed by `|gp-0x4f60|>>5`. Index 0 (hands off) is BELOW X[0], so it returns
Y[0] = 254 = **FULL authority**. It is a driver-OVERRIDE taper, not a driver-input requirement.

## Where the LKAS torque actually comes from
- The 0x0E4 request bits `gp-0x6803`/`gp-0x6805`/`gp-0x6807` drive the engagement state machine
  (states `gp-0x3d38`, `gp-0x679f`) which ramps **`gp-0x69b0`** (Q15, 0..0x8000).
- Tail of FUN_00028ea6: a first-order lag in `gp-0x3d3c` (cals `tp+0x73ec`=0xC63EC, `tp+0x73ee`=0xC63EE,
  mul sites **0x2a180** and **0x2a194**) → `r9 = state>>5`.
  **0x2a1e6 `mul r14,r9` then `sar 0xf`** = lag output × `gp-0x69b0` ⇒ **`gp-0x6b30`** (st.h @0x2a206)
  = the LKAS torque contribution. *This*, not 0x2a194, is the engagement multiplier.
- `(base_assist + gp-0x6b30) × gp-0x6752(=-1) × cal tp+0x746c` >>15, clamp ±`tp+0x71b4`
  ⇒ **`gp-0x6b38`** (0x2a1f2..0x2a23c).
- `0x2b418 ld.h -0x6b38` → gated copy → **`gp-0x6b3c`** (0x2b41c).
- `FUN_0002b422` (called by FUN_0002214a): clamp `gp-0x6b3c` to ±`tp+0x71b2` → `gp-0x6b3a`, builds a
  16-byte request struct {id=1, mode, [+2]=0, **[+4]=torque**, [+10]=`gp-0x697e`, [+12]=`gp-0x697c`,
  [+14]=0x400} and calls **`FUN_00025c32`**.
- `FUN_00025c32` = the **11-slot torque-request registry** (`iVar9 = min(id,10)`), storing per-slot:
  `gp-0x62e0`/`gp-0x4b70` (±0x4000, from [+2]), **`gp-0x62f8`/`gp-0x4b88` (±0x2800, from [+4] — the
  LKAS torque)**, `gp-0x6274` (±900), `gp-0x633c`/`gp-0x4ba0` (±20000), `gp-0x6230`/`gp-0x4b10`,
  `gp-0x6218`, `gp-0x6200` (Q10 gains ≤0x400); slot FSM in `gp-0x61a0+id`.
  This is the feed for the 11-slot assist sum `gp-0x6b4c` (see kit memory) → FOC `gp-0x6b98`.

## Gotchas hit here
- Ghidra resolves NO xrefs for gp-relative cells (`get_xrefs_to 0xFEDF1652` → "No references"), so the
  operand-text search + Python hw2 scan pair is mandatory.
- Ghidra has no function at 0x2b418 (`get_function_by_address` → none) although real code lives there;
  FUN_00028ea6's stores also continue past its stated 0x2a30d bound (0x2a934 writes `gp-0x6b38`).
