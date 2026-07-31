---
name: reference_accord_boost_index_input_is_resolver_rate_not_torque
description: gp-0x6abc (FUN_0003b66a's FIR input, root of the boost-amplitude index gp-0x6ba6) is traced to the motor resolver electrical-angle rate, not driver torque or a command.
metadata:
  type: reference
---

**Q1 from the 2026-07-30 boost-index producer-chain task, ANSWERED with full byte-scan corroboration.**

`gp-0x6abc` — the value FUN_0003b66a (`0x3b66a`) FIR-filters (identity FIR, coeffs 1,0,0) into `r28` at
`0x3b874`, whose `abs()` becomes `gp-0x6ba6` (the boost-amplitude index indexing `0xD28DC`/`0xD2888`) — is
one of **FOUR sibling 16-bit cells, consecutive in RAM**: `gp-0x6abc` (0xFEDF1544), `gp-0x6abe`
(0xFEDF1542), `gp-0x6ac0` (0xFEDF1540, = the already-confirmed `motor_rate_raw`), `gp-0x6ac2`
(0xFEDF153E). **All four share ONE producer, `FUN_00041464`** (byte-scanned exhaustively across the full
1,048,576-byte `code.bin`: exactly 4 static `st.h` sites per cell, 16 total, zero elsewhere in the image).

**Producer chain, each hop Ghidra-decompiled/disassembled and cross-checked:**
1. `FUN_00065afe` — resolver sin/cos processing (`FUN_0006adfe`, an atan2/CORDIC-style call on two
   ADC-derived arguments) producing a 14-bit electrical angle (`& 0x3fff`), ending in
   `FUN_00068f52(uVar14)`.
2. `FUN_00068f52` (`0x68f52`) — takes the new electrical angle, subtracts the PREVIOUS sample
   (`gp-0x29c2`, wrap-corrected at ±0x2000 against the 0x4000 modulus — the textbook electrical-angle
   differentiator), scales by 120000 and `>>14`, 2-tap-averages with history `gp-0x4f4e`, clamps ±13000,
   and writes **`gp-0x29c4` = the resulting RATE**. This is unambiguously an angle-delta-per-sample
   (rate) computation, not a torque computation (no wraparound/modulus math exists anywhere in the
   torque-sensor path).
3. `FUN_00068fbe` (`0x68fbe`) — atomically copies `gp-0x29c4` under `__disable_irq()/__enable_irq()`
   (confirming `gp-0x29c4` is ISR-shared) into **`gp-0x4f50`**, lockstep-shadowed at `gp-0x4484`.
4. `FUN_00041464` (`0x41464`, called from the 1kHz dispatcher `FUN_0002214a` under phase-mask `0x830`,
   unconditional on LKAS engagement) reads `gp-0x4f50` and derives all FOUR sibling cells: a filtered
   value (`gp-0x6ac0`), a directly-scaled value (`gp-0x6abc`), a further EMA'd/derivative value
   (`gp-0x6abe`), and a "counter-torque" detector (`gp-0x6ac2` — nonzero only when `sign(filtered rate)
   != sign(gp-0x6b98`, the delivered motor command`)`). Each branch is gated by a per-channel
   config/CRC check (`0x49d6b173` + `tp+0x50e8..0x50ee` byte) selecting a linear gain/offset transform vs
   a raw pass-through/sentinel — a manufacturing-config selector, not a physical-domain distinction.
   `FUN_00041b8e` is a pure cross-tick FLOAT SHADOW re-derivation of the same 4 cells (fault-logs via
   `FUN_000462e6` on >5-count divergence) — a lockstep/ASIL check, not a second producer.

**⇒ Finding: the boost-amplitude index (`gp-0x6ba6`/`gp-0x6b9a`) is substantially a MOTOR-RESOLVER-RATE
derived quantity, not driver/torsion-bar torque and not a raw command.** Full arithmetic inside
FUN_0003b66a (see [[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]]) BLENDS (sums, Q10) a
filtered discrete-derivative of this resolver-rate lane with a separately-filtered driver-torque-sensor
(`gp-0x4f60`) term — so the index is a rate-plus-torque composite, weighted toward the rate side by
construction (the rate lane alone gates the whole computation: the top-of-function validity gate tests
`gp-0x6abc` directly with the same ±25600-ish window used for torque plausibility elsewhere).

**Consequence for the V58/V59 "index climbs only when driver applies torque" observation**: this is
consistent with either reading (driver torque directly, OR driver torque exciting motor rate through the
mechanical coupling) — the index being resolver-rate-based does NOT make "driver-effort-driven, weak
lever" the settled conclusion; it reframes what "driver effort" means at this cell (a rate/velocity
response of the coupled motor+column system, not a pure torque reading). Untested: whether the resolver
rate spikes purely from LKAS motor current commands with the driver's hands off (would require a
sustained hands-off capture, per V59's next-route recommendation).

Method: Ghidra decompile+disasm of `FUN_00065afe`/`FUN_00068f52`/`FUN_00068fbe`/`FUN_00041464`/
`FUN_00041b8e`, corroborated by an exhaustive Python raw-byte scan of ALL `st.h`/`st.w` (opcode 0x3B,
reg1=gp) instructions in `code.bin` (validated opcode/reg1/reg2 bit extraction against 3 known
instructions first) — 26 total ST hits found for the 10 target cells in this investigation, matching the
decompiled write-site counts exactly (gp-0x6abc/6abe/6ac0/6ac2 = 4 each, all in FUN_00041464;
gp-0x6b9a/6ba6 = 1 each in FUN_0003b66a; gp-0x6bbe = 3 in FUN_00034a72; gp-0x6bd0 = 3 in FUN_00034350;
gp-0x29c4/4f50 = 1 each). Zero hits anywhere else in the 1,048,576-byte image, including unanalyzed
regions (the byte scan does not depend on Ghidra's analysis state).

⚠ NOTE for the operator: this conflicts in framing (not necessarily in fact) with the older
`reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism.md` ("FUN_0003b66a is 2x cascaded IIR w/
±32767 sentinels, not FIR") — the 2026-07-30 V58 handoff and this trace both confirm FUN_0003b66a DOES
contain a genuine (if currently identity-coefficient) 3-tap FIR as its first stage, PLUS two separate
2-stage IIR/EMA cascades downstream of it. Both descriptions are partially right; the older memory should
be reconciled/superseded by the operator, not overwritten here.

Related: [[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]]
