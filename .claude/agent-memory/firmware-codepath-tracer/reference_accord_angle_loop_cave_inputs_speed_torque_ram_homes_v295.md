---
name: reference-accord-angle-loop-cave-inputs-speed-torque-ram-homes-v295
description: For a speed-scheduled, driver-bled angle-loop cave on V295 — speed = ld.hu gp-0x6a5e (64 ct/km/h, 100 Hz task-5 voter, slew 16 up/27 down, fault slews to 5120) gated on gp-0x67f4 not Honda's r29; NO callable LERP helper (all inlined, template 0x28FC8); |driver torque| ready-made at gp-0x4f68; flight-proven free RAM gp-0x6c44..39 and gp-0x6d74..71, new gp-0x6d70/6d6c clean; 1048 B free flash at 0xC4BD8 dirties only CRC 0xC4FFC
metadata:
  type: reference
---

Traced 2026-09-30 for THE GOAL's angle-loop cave. Full record, encodings and tables:
`docs/traces/TRACE-2026-09-30-speed-driver-torque-lerp-and-ram-homes.md`.

## Speed
- **Read `gp-0x6a5e` via `ld.hu`** (r6 `e4 37 a3 95`, r10 `e4 57 a3 95`). It is an unsigned magnitude,
  0..32000, 64 counts per km/h. **EVIDENCE:** FUN_00028ea6 reads it at 0x28F0E.
- **Writer.** The sole writer is voter `FUN_00041eec` (`st.h` @0x42342), called only from task 5
  `FUN_00022ca0`. Task 5 is 100 Hz per kit memory, so the 1 kHz lane sees steps every ~10 ms.
- **Slew.** Up 16 counts per update below 86 km/h (LERP 0xC685A); down 27 per update (0xC6842).
- **Fault.** `gp-0x67f4 = 0` and the vote slews toward cal 0xC631C = 5120 (80 km/h), not to 0.
- 🛑 **Honda's `r29` speed-valid flag (0x28F16) requires ALL FOUR wheel channels in range.** Whether CAN
  0x1D0 is ingested is UNRESOLVED (descriptor enable [+0] = 0; the wheels boot 0x7FFF). Gate a cave on
  `gp-0x67f4`, never on `r29`.
- `gp-0x6a62` reads 0xFFFF unless at least 3 wheels and the 0x158 channel are valid. Avoid it for scheduling.

## LERP
- **There is no callable LERP helper.** Every table in FUN_00028ea6 is inlined. The template is
  0x28FC8–0x29030: 9-knot record `[count, X0..X8, Y0..Y8]`, unsigned walk, `divq r14,r16,r0`, uses `ep`.
- The only RAM-stored pure-speed words are `gp-0x6e28` / `gp-0x6e38`: Y[0] of FUN_0003ad74's r26/r24
  gain tables. They are 100 Hz, Q10, range 3072→2560 / 3072→2151, and coupled to the r24/r26 cal. Do not
  reuse them.
- The 0xCB844[7] envelope is flat (15360 on stock, 16384 on V295) and is not stored.

## Driver torque
- **`gp-0x4f60`** is signed, written by `FUN_0007f3f8` via `FUN_0006bb08` at task-1 0x221E0, **before**
  0x22522 → FUN_00028ea6, so it is fresh every tick.
- Wire 0x18F = −floor(t·125/128).
- ⭐ **`gp-0x4f68` = |gp-0x4f60| saturated at 0xFFFF** (one writer @0x7FECA). Read it with `ld.hu`,
  r6 `e4 37 99 b0`.
- The override index is `gp-0x682f` (odd `ld.bu`, r7 `a4 3f d1 97`).

## RAM (V295, five methods, positive-controlled on V288r2/V289/V292 images)
- **Flight-proven and free:**
  - `gp-0x6c44/-0x6c40/-0x6c3c`, exactly 12 B, bounded by `-0x6c48` and `-0x6c38`. V289 packed its FLAG
    `-0x6c3a` inside the `-0x6c3c` word.
  - `gp-0x6d74/-0x6d72`.
- **New and clean:** `gp-0x6d70`, `gp-0x6d6c`, inside the 72-byte run `gp-0x6d74..2d`. Its lower neighbour
  `gp-0x6d78` is LIVE, including `movhi 0xFEDF` + `clr1` absolute bit-ops at 0x197E4/0x19880.
- `gp-0x6a32` is **W1R0** (live writer 0x29D72), so it is usable only by replacing that store.
- All candidates are `.data` and boot 0.
- **Indexed idiom the plain gp scan misses:** `add gp,ep ; st.b r,-0x6e10[ep]` (0x52DC2). Sweep non-gp
  bases for band displacements.

## Code
- **V295 tap** = 0xC4B34–0xC4BD7 (164 B, no state RAM).
- **Free = 0xC4BD8–0xC4FEF, 1048 B.** It plus any app-code hook dirties only `0xC4FFC`. V295 passes
  49/49 and 50/50 (`verify_bootloader_crc.py`).
- ⚠ V295 changed `0x28FA4` from `add` to `subr r9,r26` and `0x29D76` from `shl 5` to `shl 2`, next to the
  V292/V288 hook sites.

Links: [[reference_accord_app_ram_layout_and_boot_init_loops]] ·
[[accord-gp6a5e-is-voted-vehicle-speed]] · [[reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram]] ·
[[accord-crc-block-lookup-and-cave-hook-template]] · [[feedback-shared-scratchpad-use-a-private-subdir]]
