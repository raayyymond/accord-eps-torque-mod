# V294 — independent Ghidra redo: structure, signal chain, units, interlocks

**Agent:** redo-ghidra, an Opus subagent of `main`. 2026-09-23.
**Tools:** GhidraMCP for all disassembly and decompilation. All `disassemble_bytes` calls used `dry_run:true`. No rename, label or retype was made. Python (the `bin_decompile` env) did the byte scans and the integer mirror.
**Programs:** `code.bin` (stock, 2090 functions), the V294 image and the V293 image. Every call named its program explicitly.
**Images verified before any claim:**

| image | sha256 (first 16) | bytes at 0x28FA4 | bytes at 0x29D76 | 0xC62E6 | 0xC63E8 | 0xC63EA |
|---|---|---|---|---|---|---|
| stock | 3f1d55a98aac6e73 | c9d1 | c582 | 7680 | 923 | 1560 |
| V293 | f75e77cf0ba9d93b | c9d1 | c582 | 0 | 923 | 1560 |
| V294 | 3143616d5b79bdb7 | **89d1** | **c282** | **1024** | **1011** | **567** |

Ghidra's V294 memory at 0x28FA0 reads `aa4a c749 89d1 edd1`, which matches the file, so the open program is not a stale import.

**Scope boundary.** The V293→V294 diff is 314 bytes. The code bytes are 0x28FA4 and 0x29D76. The cal bytes are 0xC62E7, 0xC63E8, 0xC63EA–B and the 280 Kp Y-field bytes. The rest are the CRC words at 0x?FFC in 7 blocks. The CRC words belong to the other agent, so I did not check them.

## FAIL criteria, written before the first Ghidra call

They are also in `scratchpad/redo_ghidra_fail_criteria.md`.

- **F1.** The operand is s_old − s_new, or E adds r26 instead of subtracting it. That makes the torque assist acceleration, so FAIL.
- **F2.** The bytes give x outside 6 to 10 counts per deg/s. That is FAIL. If the chain at 0x55B48 does not hold, the scale is BELIEF.
- **F3.** Any governor, EME, lockstep or DTC reader of a changed or rescaled cell is FAIL.
- **F4.** Any instruction boundary in `FUN_00028ea6` that differs between V293 and V294 is FAIL.
- **F5.** A live second consumer of r26 whose meaning changes unsafely is FAIL.
- **F6.** A reachable kick larger than the ±1024 operand clamp is FAIL.
- **F7.** A 0x14A cave that reads P, I, D or S instead of the delivered torque is FAIL.

## VERDICT: **flash-eligible** on this surface

No FAIL criterion fired. There are three corrections to the record and one instrument hazard, listed in section F. None of them blocks the flash.

| claim | result |
|---|---|
| A — structure and integer chain | **PASS** |
| B — sign through the chain | **PASS**: negative feedback on acceleration, and the polarity flag cancels |
| C — unit and scale | **PASS**: x = 8.00 counts per deg/s of steering-wheel rate. EVIDENCE by bytes, DBC and wire |
| D — cell privacy and interlocks | **PASS**, with two stated residuals |
| E — do-not-flash hunt | nothing found; the bail transient is corrected (F1 below) |
| F4 — instruction boundaries | **PASS**: 1874 of 1874 identical, and only two instruction texts differ |

---

## A. Structure of FUN_00028ea6 — PASS

**Decompile (V294, `decompile_function 0x28ea6`, 54 KB, saved as `scratchpad/v294_28ea6_decomp.c`), the filter block.**

```c
if (*(char *)(gp-0x3d2c) == 1) { iVar23 = *(int*)(gp-0x3d34); iVar31 = *(int *)(gp-0x3d30); }   // s_old
else                           { iVar23 = 0;                 iVar31 = 0; }
uVar18 = uVar35 = *(ushort *)(tp+0x72e6);                                       // C = [0xC62E6]
iVar34 = (*(short *)(tp+0x73e8) * iVar31 >> 10) +
         ((int)(*(short *)(gp-0x6a56) * (uint)*(ushort *)(tp+0x73ea)) >> 10);  // s_new
uVar37 = iVar34 - iVar31;                                                       // s_new - s_old   <-- V294
*(int *)(gp-0x3d30) = iVar34;                                                    // state := s_new
... clamp uVar37 to +-C -> uVar35 ...
uVar18 = |((int)uVar35 >> 5) * 0x20|;  ...  *(short *)(gp-0x6a34) = uVar18 >> 5;
```

**Disassembly check (V294, dry run).** The instructions confirm which register holds which value.

```
28F7C  ld.w  -0x3d30,gp,r26     r26 = s_OLD  (or 28F84 mov 0,r26 when the sentinel != 1)
28F8A  ld.h  0x73e8,tp,r9       r9  = a = 1011 (signed ld.h)
28F8E  mul   r16,r7,r0          r7  = x*b      (r16 = b = 567, ld.hu @28F86)
28F92  mul   r26,r9,r0          r9  = a*s_old  (r26 is reg1 = a SOURCE; it is not written)
28F9A  sar   0xa,r7 ; 28FA0 sar 0xa,r9 ; 28FA2 add r7,r9      r9 = s_NEW
28FA4  subr  r9,r26   89d1      r26 := r9 - r26 = s_new - s_old
28FA8  st.w  r9,-0x3d30,gp      state := s_new
28FA6..28FBC  signed clamp to +-[0xC62E6] (ble/bge)
```

The encoding of `0xD189` is reg2 = 26, opcode field 0x0C (SUBR) and reg1 = 9. SUBR means GR[reg2] ← GR[reg1] − GR[reg2]. The decompiler computes the same thing on its own: `uVar37 = iVar34 - iVar31`.

⇒ **EVIDENCE: the operand is s_new − s_old.** The OLD state sits in r26 and the NEW state in r9.

**The state cell is `gp-0x3d30`,** not the "gp-0x6a5c-ish" cell the brief suggested. It is 32-bit, 0xFEDF42D0. The input x is `gp-0x6a56`.

**The rest of the chain, from the V294 decompile and the dry-run disassembly.**

| step | address | V294 |
|---|---|---|
| sp published | 0x29D72 `st.h r16,-0x6a32` | pre-shift, so its scale is unchanged |
| E | 0x29D76 `shl 0x2,r16`, 0x29D78 `sub r26,r16` (`ba81`: r16 ← r16 − r26) | decompile: `iVar31 = iVar31 * 4 - uVar35` |
| Kp | 0x29DC6 `mov 0xcb994,r10` … LERP … 0x29E32 `zxh r9` | all 28 records have Y = {960 ×5}, X = {0,48|64|68,112|128,136|160,208} |
| P | 0x29E36 `mul r9,r8`, 0x29E3E `sar 8`, clamp ±[0xC61BC] = 15360 | `uVar33 = iVar26 >> 8` then clamp |
| I | 0x29D9C Ki = [0xC63E6] = **0**. The integrator gp-0x6dd0 boots 0 and is stored as 0 on every skip | I ≡ 0 |
| D | Kd bank 0xCB7D4: all Y = 0. D clamp [0xC61B6] = **0** | D ≡ 0 |
| S | 0x29F18 `sar 0x7,r2`, 0x29F1E `add`, 0x29F24 `add` | `S = (I>>7) + P + D` |
| taper | 0x2A0B4 `mulu`, `andi 0xffff`, `sar 8`, 0x2A0BE `mul`, 0x2A0C2 `sar 8` | g = ((g1·g2) & 0xFFFF) >> 8, which is ≥ 0, so the sign is kept |
| sum clamp | 0x2A13E..0x2A160, ±[0xC61BE] = 15360 | unchanged |
| output lag | 0x2A174..0x2A1B0: y' = (992·y>>10) + (507·S>>10), o = (y + y')>>5 | a2 = 992 gives **5.05 Hz** |
| ramp | 0x2A1E6 `mul r14,r9`, `sar 0xf`, `sxh` | the ramp is `(uint)*(ushort*)(gp-0x69b0)`, which is ≥ 0 |
| gain and polarity | 0x2A1EE `ld.h 0x7cd0` (G = 5346), 0x2A1F2 `ld.b -0x6752` (pol), 0x2A1F6 `mulh`, 0x2A1FE `mul`, 0x2A202 `sar 0xf` | T = ((0 + T1)·pol·5346)>>15 |
| cap | ±[0xC61B4] = 3072, then 0x2A23C `st.h -0x6b38` | the delivered lane torque |

The pole a = 1011 gives **2.03 Hz**. The value Ts = 1 ms is inherited EVIDENCE-by-consistency and was not re-verified.

**The integer mirror** is in `scratchpad/v294_mirror.py`. Every line carries its instruction address. Every constant is byte-read little-endian from the V294 image, never from the build script. Its core:

```python
s_old = st.s if st.sent == 1 else 0                   # 0x28F72 / 0x28F7C | 0x28F84
s_new = ((1011 * s_old) >> 10) + ((x * 567) >> 10)   # 0x28F8E/92 mul, 0x28F9A/A0 sar 0xa, 0x28FA2 add
r26   = clamp(s_new - s_old, 1024)                    # 0x28FA4 subr ; 0x28FA6..0x28FBC
st.s  = s_new                                         # 0x28FA8
E     = (sp << 2) - r26                               # 0x29D76 / 0x29D78
P     = clamp((E * 960) >> 8, 15360)                  # 0x29E36..0x29E5C
S     = (0 >> 7) + P + 0                              # 0x29F18..0x29F24  (Ki = Kd = D-clamp = 0)
St    = sxh(clamp((g * S) >> 8, 15360))               # 0x2A0B4..0x2A160
y_new = ((992 * y) >> 10) + ((St * 507) >> 10); o = (y + y_new) >> 5; y = y_new   # 0x2A174..0x2A1B0
T1    = sxh((o * ramp) >> 15)                         # 0x2A1E6..0x2A1EC
T     = clamp((T1 * (pol * 5346)) >> 15, 3072)        # 0x2A1EE..0x2A23C -> gp-0x6b38
```

**Mirror results**, all EVIDENCE because they are arithmetic on byte-read constants:

- **Feedforward identity.** V294's P equals V293's P at r26 = 0 for all 65,536 values of the 16-bit sp. There are 0 violations. The sp operand is `(short)` at decompile line 1949.
- **Steady rate.** The operand settles to exactly 0 after 3000 ticks at every x in {±12000, ±800, ±80, ±5, ±1, 0, 3}.
- **Zero-command authority.** The peak |T| at zero command under a hard ramp is **616**, which reproduces adversary B.
- **Rail.** P and S clamp at 15360 in both builds, so the rail stays 2461. The trim cannot push the delivered torque past V293's rail. It can only lower |T| at the rail when it opposes, and it is clipped when it aids.
- **int32 headroom.** a·s_max is 1011 × 523,422 = 5.3e8, a margin of 4.06×. E·Kp is at most 1.27e8.

## B. Sign through the chain — PASS: negative feedback, the polarity flag cancels

1. **Producer, EVIDENCE.** `FUN_0003f776` in the `code.bin` decompile computes:

   `iVar4 = (int)*(char*)(gp-0x6752) * ((int)(*(short*)(gp-0x6abe) * 0x30 * (uint)*(ushort*)(tp+0x713a)) >> 0xf);`

   It then saturates to ±12000 and stores the result to gp-0x6a56 and its lockstep mirror gp-0x4ca6. If |raw| > 13000 it stores 0 instead. So **x = pol·((raw·48·1159)>>15)**. The cell [0xC613A] = 1159 is the same in all three images, and pol is the same cell `gp-0x6752`, a ±1 byte that boots `01` from `.data` 0x8695E.
2. **Operand, EVIDENCE (section A).** r26 = Δs, and s has a positive DC gain of 567/13 from x. So r26 has the sign of Δx, which is pol·Δraw.
3. **Error, EVIDENCE.** E = 4sp − r26, with Kp = 960 > 0. P therefore carries −3.75·r26.
4. **Everything after P preserves sign, EVIDENCE.** The taper g is unsigned 0..255. The lag has positive coefficients. The ramp is an unsigned halfword. The last step multiplies by **pol**·5346 (0x2A1F2 `ld.b -0x6752`, 0x2A1F6 `mulh`).
5. ⇒ **T_trim ∝ −pol·pol·Δraw = −Δraw for both polarities.** The mirror confirms it. When raw accelerates positively, T is between −59 and −7 for pol = +1 and also for pol = −1.
6. **Physical anchor.** The claim that +T accelerates +raw is EVIDENCE by function, not by bytes. Stock, V282 and V292 all ran this same r26 → torque path with the SUM operand, giving T ∝ −(s_old + s_new) ∝ −raw at a 30.9 DC gain. That loop is a working rate servo:
   - V282 and V292 flew.
   - V278r3 measured max rate equal to the reference.
   - A −38 T-count per deg/s positive feedback would be about 20× the wheel's own damping and would diverge.

   Everything from r26 onward is byte-identical to that loop, apart from the sp shift. So −Δraw opposes acceleration, which means added inertia plus damping through the lag.
7. **Corroboration, BELIEF about intent.** Honda's own damper lane at 0x2A0C6 outputs `-sign(r26)·LERP(|r26>>5|)`. That is r26 applied with the same negative sign.

## C. Unit and scale — PASS: **x = 8.00 counts per deg/s**, EVIDENCE

| link | method | result |
|---|---|---|
| gp-0x69ea = −gp-0x6a56 | `FUN_00040a50` decompile: `*(short *)(gp-0x69ea) = -*(short *)(gp-0x6a56);` on both valid paths, 0x7FFF on the invalid path. Ghidra and Python agree on 3 writers (0x40ACE, 0x40B4E, 0x40C50) and 1 reader (0x55B48) | EVIDENCE |
| rate field = gp-0x69ea >> 3 | `FUN_00055a98`: `uVar3 = (int)*(short*)(gp-0x69ea) >> 3 & 0xffff;` gated by the ±1500.0 float plausibility check (0x7FFF outside it), then `FUN_0002191e(uVar3)` | EVIDENCE |
| field lands in bytes 2–3 of 0x14A | `FUN_0002191e` writes `gp-0x1516` byte-swapped (big-endian). `FUN_000218fe` writes `gp-0x1518` (bytes 0–1). The checksum is `FUN_00057b24(gp-0x1518, 8, 0x14a)` | EVIDENCE |
| DBC | The operator's fork uses `honda_civic_hatchback_ex_2017_can_generated.dbc` for the 2018–22 Accord. Its line is `STEER_ANGLE_RATE : 23|16@0- (-1,0) "deg/s"`. **The factor is −1, not +1** | steeringRateDeg = −((−x)>>3) = **+x/8** |
| the bus field is physical steering-wheel deg/s | New measurement on the three V292 routes 6d/6e/6f: the least-squares slope of d(carState.steeringAngleDeg)/dt against steeringRateDeg is **1.007 / 1.002 / 1.004** (n about 20k per route, 5 < \|rate\| < 200) | EVIDENCE, if STEER_ANGLE's 0.1-degree unit holds (it is openpilot-validated) |
| ±1500 deg/s plausibility bound × 8 = 12000 | equals the x saturation in the producer | internal consistency |

**Rate former, BELIEF.** `FUN_00065afe` computes `FUN_0006adfe(sin−0x800, cos−0x800)`, an atan2 of two ADC channels centred on mid-scale. It masks the result to 14 bits and feeds the FOC electrical-angle cells. `FUN_00068f52` then differences that angle and writes `gp-0x29c4`. The chain continues to gp-0x4f50 (with mirror 0x4484) in `FUN_00068fbe`, then to gp-0x6abe through `FUN_00041464`. That last hop was found by operand search and its arithmetic was not decompiled. So the rate former is the **motor position sensor, not a separate steering-angle sensor**. STEER_ANGLE uses the same c = [0xC613A] and the same pol (`FUN_00040a50`), so both 0x14A fields come from one motor-position chain. **x no longer depends on the gear ratio or ISR split.**

## D. Cell privacy and interlocks — PASS

**Method.** Two scans were set against each other:

- a Python scanner covering the 4-byte and 6-byte gp/tp forms, absolute LE32 at every byte offset, and movhi/movea pairs;
- Ghidra `search_instructions` on `code.bin`.

The scanner's positive controls all passed:

- gp-0x6a56 gives 29 hits, matching the erratum count.
- gp-0x69ea gives 4, matching Ghidra.
- tp+0x73EC gives 2 (0x2A184, 0x2A8A2).
- The 6-byte gp-0x6752 hits at 0x48E56/68/76/88 are found.
- The 6-byte gp-0x6abe hits at 0x59A30/3A and 0x59BD4/DE are found.
- The branch scanner finds the callers 0x22522, 0x23276 and 0x2291E.

| cell | Python (stock = V294) | Ghidra (code.bin) | set difference |
|---|---|---|---|
| tp+0x72E6 fb clamp | 3 × ld.hu, 0x28F96/9C/B8 | same 3 | ∅ |
| tp+0x73E8 a | 1 × ld.h, 0x28F8A | same | ∅ |
| tp+0x73EA b | 1 × ld.hu, 0x28F86 | same | ∅ |
| Kp table 0xCB994 | `mov imm32` at 0x29DC6 (live) and 0x2ACB8 (dead twin). Each of the 28 records is referenced exactly once, from the table | same 2 | ∅ |
| gp-0x3d30 fb state | ld.w 0x28F7C, st.w 0x28FA8 | same | ∅ |
| gp-0x3d2c sentinel | ld.bu 0x28F66, st.b 0x290D4 | same | ∅ |
| gp-0x6a34 \|r26>>5\| (**rescaled**: V293 ≡ 0, V294 0..32) | st 0x290CA; ld 0x2A0CA (the damper lane); ld 0x2AFAE (dead twin) | same 3 | ∅ |
| gp-0x680a lane selector | 2 × ld.bu (0x29A68, 0x2A96A). **Zero writers** | same 2 | ∅ |
| gp-0x6cf8 E_prev (**rescaled** 32sp → 4sp) | live ld/st, plus ld/st in the dead twin | — | only D (≡ 0) reads it |
| gp-0x6b2e / 32 / 34 / 36 published output, P, S, D | stores only (live and island), plus 1 × ld.h at 0x2A896 inside the island | — | no live reader |
| gp-0x6b38 delivered torque (units unchanged) | st 0x2A23C; ld 0x2B418 (island); 0x4E8D2 / 0x4E8E2 (`FUN_0004e82e`, a pure `sst.b` record with no compare); 0x55DF0 (the 427 tap); 0xC4B40 (the 0x14A cave) | — | — |

- **No changed cal cell and no rescaled RAM cell has a reader outside** the filter and PID of `FUN_00028ea6`, the uncalled island, and the unreachable damper lane. No governor, EME, lockstep or DTC function appears among the accessors, so **F3 did not fire**.
- **Downstream consumers see only the delivered torque, in unchanged units.** They are the mixer at `FUN_0002b422` (0x2B42E reads gp-0x6b3c and clamps it to [0xC61B2]), the 427 tap, the 0x14A cave and the diagnostic record. The delivered torque is still bounded by the 2461 rail.
- **The island 0x2A30E–0x2B421 is uncalled.** No Format-V or 6-byte jr/jarl targets it from outside, in stock or V294. There are 13 LE32 hits into it; each was adjudicated:
  - 0x66DAA and 0x75B78/0x75C6E are coincidental instruction bytes (`ld.b` and `addi`).
  - Six are odd-offset cal data.
  - 0x5A366 is `mov 0x2b000,r8; st.w r8,0x1044[r17]`, which writes a constant to a peripheral register at 0xFF6C1044. It is not a call.
- **The damper lane 0x2A0C6 is unreachable.**
  - Its only entry is `0x29A70 jr 0x2A0C6`, gated on gp-0x680a == 1.
  - 0x2A0C4 is an unconditional `br`, so nothing falls through into it.
  - No LE32 value points to it.
  - gp-0x680a has zero writers and **boots 0**. The `.data` copy loop at 0x1475C–0x14794 (`mov 0x86260,r14` … `mov 0xfedf11b0,ep` … `mov 0x8ab18,r10`, `bc 0x1476c`) was confirmed by a dry-run disassembly. It loads the byte from flash 0x868A6, which is 00 in V294.
- **The 0x14A cave (0xC4B34–0xC4BD7, hook 0x55C0E `jarl 0xc4b34`)** reads gp-0x6ada, **gp-0x6b38** (the delivered torque), gp-0x6b94, gp-0x6b4c and gp-0x3680. It writes 0x14A byte 4 (gp-0x1514) and byte 7 bits 7:6. It reads **none** of P, I, D or S, so **F7 did not fire**. The 427 source at 0x55DF0 is `ld.h -0x6b38,gp` and also reads the delivered torque.
- **Cold boot is now EVIDENCE rather than BELIEF.** The sentinel gp-0x3d2c and the state gp-0x3d30 both boot 0 from `.data` (flash 0x89384 and 0x89380). The first tick therefore starts cold with s = 0.

**Residuals, stated honestly.** Neither changes the verdict.

1. **gp-0x680a.** A register-indirect store is invisible to operand scans. The only near-pointer is a `.data` word at gp-0x3454 = 0xFEDF1806, which points at gp-0x67FA, 16 bytes away from gp-0x680a. Nothing loads it by a gp-relative instruction. Reaching gp-0x680a through it would need a −16 offset. BELIEF: it is a scalar signal pointer.
2. **The cal cells.** A `.data` pointer family holds 0xC626C and 0xC626E, 19 each, at a 0x2C stride. They sit 0x78–0x7A below 0xC62E6. They would reach the clamp only with a +0x78/+0x7A offset. BELIEF: scalar pointers. The flown values of 0xC62E6 already span 0 (V293), 7680 (stock) and 46080 (V282), and V294's 1024 lies inside that range.

## E. The do-not-flash hunt — nothing found

**Second consumers of r26.** A full sweep of r26 over all 1874 instructions of V294 found three readers:

- **0x28FBE `mov r26,r16`.** This feeds the rectify step and the gp-0x6a34 publish. Its consumers are the unreachable lane and the dead twin.
- **0x29D78.** This forms E.
- **0x2A0C8.** This is the unreachable damper lane.

0x29F96 and 0x29FE8 read r26 only after `0x29F76 mov r13,r26` overwrites it with LERP scratch. No branch from outside [0x29F76, 0x29FE8] lands in (0x29F78, 0x29FE8], so the operand cannot reach them.

**Disengage and engage.**

- The filter runs every tick, so on re-engage at a steady rate the first five T values are 0 in the mirror.
- The E_prev sentinel gp-0x6cf8 feeds only D, and D is 0 because Kd = 0 and the D clamp is 0.
- The integrator is 0 because Ki = 0 and it is reset on every skip.
- The deadband branch at 0x2A1B6 is the same code as V293. tp+0x74A3 = 0xC64A3 = 1. It is bypassed while gp-0x6806 = 1 (set at engage) and applies to the feedforward and the trim alike.

**Bail — this corrects adversary B's "one tick".**

- A bail makes the sentinel 2 and forces a PID skip that tick.
- On the next tick s_old is 0. The operand then equals Δs of a state re-converging from 0 to 43.6·x, with a time constant of about 79 ticks.
- The result is **an 80–400 ms transient, not one tick**. It opposes the current direction of wheel motion, like a braking pulse.

| x | wheel rate | first operand ticks | peak T | duration with \|T\| > 10 |
|---|---|---|---|---|
| 80 | 10 deg/s | 44, 43, 42 … | −15 | 93 ms |
| 400 | 50 deg/s | 221, 218 … | −73 | 244 ms |
| 704 | 88 deg/s | 389 … | −128 | 290 ms |
| 1850 | 231 deg/s | 1024 (clamped) … | −336 | 366 ms |
| 12000 | 1500 deg/s | 1024 (clamped) … | −611 | 399 ms |

It is bounded by the same 616 limit. It fires only on the four bail conditions, which are fault-edge events: torque-sensor implausibility, the arm flag not ±1 or zero, or \|x\| > 12000, and the producer already saturates x. V293 shows T = 0 after a bail. **F6 did not fire.**

**F4.** A V293 dry-run and a V294 dry-run over 0x28EA6–0x2A30D both return 1874 instructions with identical addresses. The only instruction-text differences are:

- `0x28FA4 add r9,r26 → subr r9,r26`
- `0x29D76 shl 0x5,r16 → shl 0x2,r16`

## F. Corrections and reports — none blocks the flash

1. **The bail kick is not "one tick, smoothed by the 5 Hz lag".** It is an exponential with the 2 Hz pole, lasting 80–400 ms. It peaks around −0.18 T-counts per x-count below the clamp, and it opposes motion. The page sentence should change.
2. **`x_scale_from_v292_wire.py` is circular for the deg/s unit.** It divides the tap by carState.steeringRateDeg, which is x/8 by construction. So its 7.1–7.8 result tests the lane model (T = −4.80x), not the unit. The unit is independently EVIDENCE from the bytes plus d(angle)/dt = 1.00 (section C). **8 stands on these grounds.**
3. ⚠ **Instrument sign and scale hazard for the next drive's pre-registered test.** 0x18F, built by `FUN_00055c42` with checksum `FUN_00057b24(gp-0x1420, 7, 399)`, carries **−x at full resolution**: `FUN_000218de(-*(short*)(gp-0x6a56))` writes gp-0x141e, which is bytes 2–3.
   - **Scale.** The Accord DBC's 0x18F factor is −0.1 deg/s, so it decodes to 0.1x deg/s. The true rate is x/8, so **the DBC-decoded 0x18F rate is 0.8× the true rate**.
   - **Sign.** The kit's v280-cache `rate` column is the raw field, which is −x. On all three V292 routes it measured −8.00 × carState.steeringRateDeg.
   - **Consequence.** The pre-registered test regresses on −(0x18F rate, 2 Hz low-pass, differenced), expects slope > 0, and treats positive correlation as SIGN INVERTED. That test is correct **only if the rate carries the sign of x**, as carState.steeringRateDeg or DBC-decoded 0x18F do.
     - Run on the raw cached column, a correct build would read as SIGN INVERTED and cause a false revert. An inverted build would read as correct, which is the dangerous direction.
     - The predicted +1.85 per deg/s holds against true deg/s (carState.steeringRateDeg). Against DBC-decoded 0x18F it would read +2.31.
   - **Recommendation.** Pin the regressor to carState.steeringRateDeg, which is 0x14A.
4. **Trap hit and self-corrected.** I first read tp+0x7432 and tp+0x74A3 at 0xC7xxx, the recurring off-by-0x1000 error. I re-read them at 0xC6432 (900) and 0xC64A3 (1). Neither value is decision-bearing.

## Open, not verified here

- Ts = 1 ms, inherited EVIDENCE-by-consistency.
- The arithmetic of the `FUN_00041464` hop, gp-0x4f50 → gp-0x6abe.
- The EME and soft-EME consequences of 616 counts at zero command. These are inherited from adversary B and were not re-derived. The census shows the interlocks see only the delivered torque, which keeps the V293 rail.
- The CRC words, including the 0xC4FFC change with no other byte in 0xC4000–0xC4FFB changed. Those belong to the build and CRC agent.

**Files:**

- `scratchpad/redo_ghidra_report.md` (this report)
- `scratchpad/redo_ghidra_fail_criteria.md`
- `scratchpad/v294_mirror.py`
- `scratchpad/census.py`
- `scratchpad/v294_28ea6_decomp.c`
- `scratchpad/v294_28ea6_disasm.json`

**Proposed memory, not written** because the brief forbids repo edits. Proposed name: `reference_accord_0x18f_rate_is_minus_x_dbc_factor_25pct_off_and_x_is_8_by_dangle`. It would record:

- 0x18F bytes 2–3 = −x raw;
- the DBC −0.1 factor is 0.8× true;
- 0x14A rate = x/8, with d(ang)/dt ratio 1.00;
- the v280 cache `rate` = −x.
