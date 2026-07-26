---
name: accord-c62ee-second-320-gate-is-can-commanded-assist-shutdown
description: The SECOND 320-count speed gate (cal 0xC62EE @0x2D84A) is NOT a low-speed lockout — it is a speed PERMISSIVE on a CAN-commanded assist-shutdown task; 0xC62EA-only is sufficient and 0xC62EE must not be touched.
metadata:
  type: reference
---

**Verdict: cal `0xC62EE` = 320 is NOT a second low-speed steering lockout. It is a "vehicle is slow
enough to safely remove assist" PERMISSIVE inside a CAN-commanded assist-shutdown task. A
`0xC62EA`-only edit IS sufficient to restore low-speed authority; `0xC62EE` must be left stock.**

## The chain (all disasm-verified on `code.bin`)

`gp-0x1413` (CAN RX byte, `0xFEDF6BED`, inside the `0xb7260` mailbox array)
→ `FUN_000524bc` @`0x524EA`/`0x524E6` extracts **bit 7 → `gp-0x6877`** and **bit 5 → `gp-0x6879`**
→ task@`0x22B24` → `jarl` @`0x22C80` → func@`0x2D78C`
→ state dispatch on `gp-0x680c` @`0x2D80A` (state 0 arm)
→ guards: `gp+0x6400 & 0x80 == 0` @`0x2D824`, `gp-0x6814 == 0` @`0x2D82E`,
  **AND (`gp-0x6879 == 1` @`0x2D83A` OR `gp-0x6877 == 1` @`0x2D842`)**
→ **speed gate @`0x2D84A`**: `ld.hu gp-0x6a62` vs `ld.hu tp+0x72EE` (=`0xC62EE`=320), `bc` taken when
  speed **< 320** → act; `jr 0x2D9A2` (exit) when speed ≥ 320
→ `st.b r10(=1), gp-0x680c` @`0x2D870`; `FUN_00045608(5, 0, 55, 164)` @`0x2D876`

**So the speed compare is a permissive, not a lockout**: the action arm is unreachable unless a CAN
request bit is set. In normal driving both flags are 0 (or `0xFF`, the invalid sentinel written by
`FUN_000524bc`'s init/else arms), so the gate's action never runs. ⇒ Lowering `0xC62EE` restores
nothing; **raising it would be actively unsafe** (it would let the commanded assist-kill fire at
higher road speed).

## Why the write matters — `FUN_00045608` is an AUTHORITY-SLOT setter, not motor-off

`FUN_00045608(idx, tgt, up, dn)` (guard `idx < 7`) writes slot `idx` of **three parallel 7-entry u16
arrays**: target `gp-0x652c+2i`, up-rate `gp-0x64fc+2i`, down-rate `gp-0x6514+2i`.
⚠ CLAUDE.md calls `FUN_00045608(3,0,0x8000,0x8000)` "motor off" — that is slot 3 with instant slew;
the function itself is generic.

`FUN_0004503c` (G1 governor) consumes them: base `movea -0x652c, gp, r20` @`0x450C6`. Its do-while
runs **3 passes × 2 elements = slots 0-5** (`bVar3 = iVar20 != 1` is evaluated AFTER the body — a
count of 2 passes is a misread), then an unrolled block handles **slot 6** (`gp-0x6538`/`gp-0x6520`/
`gp-0x6508`/`gp-0x64f0`). Each slot is rate-limited toward its target into the current array
`gp-0x6544+2i`, and `uVar10` (init `0x8000`) accumulates a **running MIN** via
`FUN_00049a78(a,b) = min(a,b)` (verified by decompile).

That MIN is a **Q15 authority scale on the TOTAL command**:
`iVar8 = (clamp(gp-0x6b94 /*aggregator*/, …) * MIN) >> 15` → `gp-0x6ace`.
⇒ slot-5 target `0` (cal `0xC6484` = 0, ramped at up 55 / down 164 = cals `0xC6482`/`0xC6480`) drives
the MIN to 0 and **multiplies the whole steering command by zero**. Real command-path effect — this
gate is not diagnostic. It is simply not reachable without the CAN request.

## `gp-0x680c` (`0xFEDF17F4`) — full enumeration, all encodings

**10 accesses: 5 readers + 5 writers.** ⚠ A prior "2 writers, 5 readers" figure was wrong — it missed
the three `st.b r0` store-zero writes (see [[v850e2-extended-disp23-encoding-solved]]).
- Writers: `0x2D870` (=1), `0x2D8A2` (=2), `0x2D948`/`0x2D980`/`0x2D990` (=0, `st.b r0`)
- Readers: `0x2D6DA`, `0x2D80A`, `0x2DA52`, `0x2DAC4` (all in-region state dispatch), plus
  **`0x2D5CA`, which is inside the LIVE `FUN_0002cc2a`** (body `0x2cc2a-0x2d5fd`, sole caller
  `FUN_00022ca0` = the assist-shaping task).
- It is a **tri-state** task variable (0 idle / 1 shutdown active / 2 alternate), not a boolean.

**The one out-of-region consumer is REPORT-ONLY.** `0x2D5CA` reads it, `cmp 0x1` + `setfe`, and
contributes **bit 6 (`0x40`)** to a packed status byte stored to `gp-0x3c9c` (2 accesses, both inside
`FUN_0002cc2a` → function-internal) and `gp-0x6813`. `gp-0x6813`'s only other access is `0x55FBC` in
`FUN_00055f2e`, which copies it to `gp-0x2f66` → `gp-0x1435`, a **CAN TX byte for ID 0x19F**
(`FUN_00057b24(gp-0x1438, 6, 0x19f)` checksum). No torque gating on this leg.

## ⚠ METHOD — Ghidra had NOT analysed this region, and it is NOT dead

`[0x2D5FE, 0x2DB93]` (1430 B) and `[0x22B20, 0x22C9F]` (384 B) are **undefined gaps** with real code in
them. `get_xrefs_to` returns "No references found" for `0x2D78C` / `0x2D7C6`, and `disassemble_function`
/ `get_assembly_context` return nothing — **all four Ghidra liveness signals give a FALSE DEAD.**

The region is reached by **table dispatch**: an **RTOS task-control-block array of stride `0x30`** whose
`+0x08` field is the task entry point:
```
0xBB928 -> 0x2214A  (1 kHz control task)   0xBB9B8 -> 0x22B24  <-- this chain
0xBB958 -> 0x22A88                         0xBB9E8 -> 0x22CA0  (assist-shaping task)
0xBB988 -> 0x22B20  (jr 0x861f2 = stub)    0xBBA18 -> 0x2351E   0xBBA48 -> 0x14C5C
```
`0x22B24` is a genuine `prepare {r20,r22,r24,r26,r28,lp}` prologue reading EPS state `gp-0x67fa`;
`FUN_00022a88` returns at `0x22b1c`, so it is a separate function, not a tail.
⇒ **An LE32 scan of the `0xBB9xx` task table is a required liveness method on this kit.** Precedent
`FUN_0002a30e`/`FUN_0002a93a` really are dead — but "in an undefined gap" alone does NOT imply dead.

## V850E2 Format V (`jr`/`jarl disp22`) — encoding solved, and it collides with `ld.bu`

```python
hw1 = u16(o); hw2 = u16(o+2)
if (hw1 >> 6) & 0x1F != 0x1E: not_a_branch      # bits 10..6 == 0b11110
if hw2 & 1: it_is_ld_bu_not_a_branch            # <== THE disambiguator
disp = ((hw1 & 0x3F) << 16) | hw2               # sign-extend bit 21
target = o + disp;  reg2 = hw1 >> 11            # 0 = jr, else jarl link reg
```
**`jr`/`jarl` and `ld.bu` share opcode field `0x3C` (bits 10..6 = `0b11110`).** They are told apart
only by `hw2` bit 0: `ld.bu` always stores `hw2 = (disp | 1)` — that `|1` documented in
[[v850e2-extended-disp23-encoding-solved]] IS the escape from Format V. Validated: `0x22F74`
`80 ff b6 9c` → `jarl 0x2CC2A, lp`, matching Ghidra's sole xref to `FUN_0002cc2a`.

🛑 **Adjudicate every Format-V byte hit on a real instruction boundary.** A scan hit at `0x28986`
"→ `0x2D7C6`" was a **false positive straddling two `movhi`** (`0x28984` `40 46 80 3f` + `0x28988`
`40 4e 40 40`; the window `80 3f 40 4e` decodes as a plausible `jarl …, r7`). An unusual link register
(`reg2` not `r31`/`r0`) is the tell. Likewise 10 LE32 "pointers" into the region were all coincidental
4-byte windows inside `FUN_00018f4a` code — none landed on a prologue.

Related: [[reference-accord-low-speed-lockout-window-c62ea]] (the real lockout),
[[reference-accord-g1-governor-total-scope-verdict]], [[reference-accord-b7260-io-mailbox-array]].
