---
name: reference-accord-v48b-notch-cave-build
description: V48B = the 21.4 Hz notch, BUILT as a code cave (2020 Accord EPS TVA-A160, V850E2). A 138-byte/41-instruction DF-I Q12 biquad at 0xC4B34 filters a copy of Sensor-B torque gp-0x4f60 to a new RAM cell gp-0x1500; a jr trampoline at 0x7FEAC; 7 live base-assist carrier reads repointed gp-0x4f60->gp-0x1500. Byte-exact addresses, RAM map, coefficients, and the full verification/safety record.
metadata:
  type: reference
---

# V48B notch code-cave build — addresses, RAM, verification (2026-07-21)

> 🛑 **OUTCOME: V48B was FLASHED and bricked violently** (full-authority steering oscillation on startup,
> parked, no LKAS; recovered by reflashing known-good). Root cause = a **RAM collision** (this build's
> `x2` cell `gp-0x14FA` high byte aliases a live monitor status byte — see below, the "clean run bounded by
> single flag bytes" claim was WRONG) **plus** the notch being a lightly-damped resonator dropped into the
> always-on base-assist loop with no closed-loop stability check. The "safety = CLOSED SAFE / UNFLASHED"
> framing in this file predates the flash and is **superseded** by
> [[reference-accord-v48b-flashed-catastrophic-ram-collision]] and
> [[feedback-cave-two-gates-ram-ownership-and-closed-loop]]. Retained below as the record of what shipped.

`analysis-2020accord/build_v48b_tva.py` + `v48b_cave_asm.py` (cave source of truth) +
`eps_v48b_cave_model.py` (bit-exact integer model) + `eps_v48b_notch_design.py` (DSP design). BUILT +
Ghidra-verified, **UNFLASHED**. V38 baseline + the confirmed state-4 ratchet fix (`0x454FE` bne→br) +
the notch. Read with [[project-v48-loopgain-v48a-failed-notch-next]] and `docs/VIBRATION-DOSSIER.md`.

## The filter
DF-I Q12 RBJ peaking-dip, f0=21.4 Hz, Q=5, −8 dB, fs=1000 Hz. int16 coeffs **`b0=4045 b1=-7949 b2=3977
a1=-7949 a2=3926`** (scale 4096). `acc = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2` (int32); `y =
clamp(acc>>12, ±25600)`. Folded to a uniform `mulhi`/`add` chain, immediates `[b0,b1,b2,-a1,-a2] =
[4045,-7949,3977,7949,-3926]`. **Exactly unity at DC** (73/73 → zero steady torque offset). Accumulator
provably < 2^31 with ≥2× margin even at full ±32767 input.

## The cave (`0xC4B34`, 138 bytes, 41 instrs) — inside the all-0xFF cave [0xC4B34,0xC4FEF], MAIN CRC block
Entered by `jr 0xC4B34` planted at `0x7FEAC` (producer `FUN_0007f3f8`'s shared epilogue; `r8` = settled
`gp-0x4f60`; that epilogue is `cmp r0,r8`+`mov r8,r14` = the front of an `abs()`). The cave: save
r10/r11/r12 to stack → biquad on a FRESH `ld.h -0x4f60[gp]` (not via r8) → `sar 12` + clamp ±25600 via
`movea 0x6400/0x9c00`+`cmp`+`ble/bge +4` → state shift (y1 = the output cell) → restore r10/r11/r12+sp →
**re-exec `cmp r0,r8`+`mov r8,r14` LAST** (so the `bge 0x7feb4` at the return sees correct flags) →
`jr 0x7FEB0`. **Return address = `0x7FEB0`, NOT `0x7feb4`** (the old handoff said 0x7feb4 — wrong; that
would skip the flag-consuming `bge`). Transparency invariant: only r10/r11/r12 (restored) and r14/flags
(reproduced) change vs. the original 2 instructions, plus the notch RAM write. Trampoline/CRC/cave
plumbing is the same class V31P flashed on-car (`jr`/`jarl` into `0xC4B34`) — proven; the NEW risk was the
cave arithmetic, which is why the built image was re-disassembled in Ghidra.

## RAM (gp = 0xFEDF8000)
- **y1 / OUTPUT = `gp-0x1500`** (0xFEDF6B00) — the cell the repointed carriers read; V31P flash-validated
  free (`.bss` map identical across V31/V38). See [[accord-free-ram-candidates-gp1500-gp14e0]].
- x1/x2/y2 = `gp-0x14FC` / `gp-0x14FA` / `gp-0x14F8` (0xFEDF6B04/06/08) — ⚠ **THIS "clean run" CLAIM WAS
  WRONG AND BRICKED THE CAR.** `gp-0x14FA` (x2)'s **high byte `0xFEDF6B07` aliases a live monitor/DTC status
  bitfield** (readers `FUN_00051fbc`/`FUN_00053f32` `case 8`). The scan missed it because the writer is
  register-indirect and the region `gp-0x1401..0x1502` is a sparse-flag map. x2 is multiplied by
  b2≈0.97 → near-unity corruption path. Use `gp-0x14E0` (`0xFEDF6B20`) instead. See
  [[reference-accord-v48b-flashed-catastrophic-ram-collision]].
- ⚠ Corrections found building it: the old `gp-0x14E0` "4 free bytes" record was partly wrong (3 bytes
  live; true free run 0xFEDF6B20–0x6B23). The 256-byte block at `gp-0x7F00` (0xFEDF0000) was REJECTED —
  page base, 433 `movhi 0xFEDF,r0,rX` sites, impractical to prove clean.

## Repoints (7 LIVE carriers; patch disp16 field ONLY: `a0 b0`→`00 eb`, opcode+dest-reg unchanged)
`FUN_0002c478`@`0x2c480` (type-8), `FUN_000352b4`@`0x354d2`+`0x35aa4` (magnitude), `FUN_0003a382`@`0x3a6ca`
+`0x3a7ca` (resonance), `FUN_0003b49a`@`0x3b4a8` (→FUN_0003a382), `FUN_0003b66a`@`0x3b672` (→damping+boost
Factor-A). `ld.h -0x4f60[gp],rX` → `ld.h -0x1500[gp],rX`. Producer runs before all carriers in the 1 kHz
task → filtered copy is same-cycle fresh. **NOT repointed:** 2 mode-gated DORMANT reads `FUN_00034350`
@`0x34392` / `FUN_00034a72`@`0x34ace` (bypassed in stock cal `0xC6498/99`=1; they're the dormant fallback
arm of a cal-gated MUX, not a comparator — correct to leave raw). The 6 other `gp-0x4f60` readers are all
classifier / return-center / UDS-diagnostic consumers → keep RAW.

## Verification
- 50/50 CRC (single MAIN block `[0x13000,0xC4FFC)` — every edit lives there) + RWD round-trip. Exact diff
  vs V38 = 160 bytes / 12 runs. 4× gain `0xC646C=3564` + DTC-0x1d clamp trap (`0xD209C`/`0xC6554`)
  byte-stock. RWD SHA-256 `0d25f022…`, image SHA-256 `a26b0571…`.
- **Every code edit independently decoded by Ghidra from the BUILT image** (`import_file` V850:LE:32:default
  base 0, `disassemble_bytes dry_run`): cave = 41 correct instrs (mulhi immediates = exact coeffs); hook =
  `jr 0x000c4b34`; return path `bge 0x7feb4`/`subr r0,r14` intact; repoint = `ld.h -0x1500,gp,rX`; ratchet
  = `br 0x000455c4`.

## Safety (adversarial, all monitor-asymmetry / V27 brick class CLOSED, SAFE)
Raw `gp-0x4f60`/shadow `gp-0x4486` never touched → zero interaction with shadow-lockstep (fault 0x17),
the 2 hard-shutdown monitors, 2 CAN, diagnostics. type-8 lockstep `FUN_00027b0a` = matched (both sides
trace to the one filtered read). All other repointed-lane consumers = 0 raw reads. **DTC-0x1c/0x1d pair
`FUN_00042af8`/`FUN_00043e44` = matched int/float lockstep** recomputing the same cal-gated (`0xC64CB`, 2
readers program-wide) formula from the same already-notched `gp-0x6b4a` (±5-count tol) → a shared-input
perturbation cannot erode agreement; strictly-attenuating notch only shrinks the per-tick delta. See
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_v48b_monitor1_dtc1c_notch_safety_closed.md`
and `..._repoint_asymmetry_review.md`. ⚠ CODE CAVE = the kit's only bricked class (V24/V27) — ultimate
check is first-minutes on-car observation; flash only on explicit operator instruction naming file + bus.

## Related
[[project-v48-loopgain-v48a-failed-notch-next]] — V48A null → why the notch is the lever.
[[reference-accord-collocation-motor-rate-damper-dead]] — why damper builds failed; notch is split-independent.
[[control-task-tick-confirmed-1khz]] — the 1 kHz task the cave and carriers run in.
[[accord-codecave-c4b34-c4fef-larger-than-documented]] — the cave region.
