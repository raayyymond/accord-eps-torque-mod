---
name: v57-decouple-built
description: "V57 = V55 + the 0xC646C decoupling (4x hits the LKAS forward path ONLY) + the DEADBAND-GATE PROBE (V55 cave payload replaced; 0x14A byte4 bit6 = the EXACT gp-0x6806==0 test the bus cannot give, because the packer transmits parity). BUILT and verified, UNFLASHED."
metadata:
  node_type: memory
  type: project
---

**Built 2026-07-29. UNFLASHED.** 58 bytes off V55, 88 off V38. TWO orthogonal changes.

```
(A) DECOUPLING
0x2A1F0  ld.h displacement  0x746C -> 0x7CD0   (tp+0x7CD0 = 0xC6CD0)   [MAIN block]
0xC6CD0  new private LKAS gain word  0xFFFF -> 3564                    [CAL block]
0xC646C  shared sensor scale         3564  -> 891 (stock)              [CAL block]

(B) DEADBAND-GATE PROBE -- V55's cave payload REPLACED, same base 0xC4B34, same hook 0x55C0E,
    same 68-byte extent (no widening). 0x14A byte4:
      bit7 = 1                    LIVENESS (field==0 => cave did not fire)
      bit6 = (gp-0x6806 == 0)     the gate is ENABLED -- EXACT equality
      bit5 = (gp-0x69b0 != 0)     ramp gain LIVE
      bit4 = (gp-0x6b30 == 0)     gate output EXACTLY ZERO
      bit3 = (gp-0x6b30 <  0)     gate output NEGATIVE
      bits 2:0 stock STEER_SENSOR_STATUS, preserved

_v57_plain_image.bin  SHA 351735984aa0ec43572e94a0592b2fe8758d9a8e93c9844fcc226dd091179125
V57 .rwd              SHA 6263acf185a00849c4dd0556f15bd834faf63a9795c610228d83d64eadb5dd3b
decoder               rlog-tools/probe/decode_v57_deadband.py
```

## 🛑 (B) WHY — the parity hole in this kit's own elimination

The deadband elimination measured `STEER_CONTROL_ACTIVE` (CAN 0x18F byte4 bit3), which the packer
sources from `gp-0x6806`:
```
0x55c76 ld.bu -0x6806,gp,r15 ; 0x55c7e andi 0x1,r15,r15 ; 0x55c82 shl 0x3,r15
```
**`andi 0x1` transmits PARITY. The gate tests EXACT EQUALITY** (`cmp r0,r12 ; bne`, `0x2a1ba`/`0x2a1bc`).
Four of the flag's eight live writers store a **register** (r6/r14/r11/r6), not a literal, so a value of 2
reads as bit0 = 0 while the gate is DISABLED -- and a 0<->2 toggle at 22 Hz would be wholly invisible
(bit3 flat at 0, zero transitions). Low probability, but the last step of the elimination rested on an
argument rather than a measurement. **Bit 6 closes it.** Bits 4/3 give the output's 3-state
{neg, zero, pos}: a chattering relay visits zero between sign flips, so bit4's spectrum carries a
20-25 Hz line if the mechanism is real. Bit 5 separates "zero because the ramp is zero" from "zero
because the gate fired".

⚠ **Expected result: NEGATIVE.** Recorded up front so a null is not re-litigated as a surprise.

Verified against the BUILT image (not the build script's own claims):
```
stock 25 3f 6c 74 -> ld.h 0x746c[tp],r7 -> 0xC646C = 891
V55   25 3f 6c 74 -> ld.h 0x746c[tp],r7 -> 0xC646C = 3564
V57   25 3f d0 7c -> ld.h 0x7cd0[tp],r7 -> 0xC6CD0 = 3564   <- forward path keeps 4x
the other five readers unchanged, all -> 0xC646C = 891
```

## Why

`0xC646C` is NOT an LKAS gain. It is the firmware's single shared Q15 sensor-to-command scale with
**exactly 6 readers** (independently re-enumerated by byte scan 2026-07-29, zero discrepancy with the
recorded figure):

| addr | function | class |
|---|---|---|
| `0x2A1EE` | `FUN_00028ea6` | **FORWARD** — the CAN LKAS setpoint path. 4x intended here |
| `0x2A904` | none | **DEAD** — not disassembled at all; sits above `FUN_00028ea6`'s end `0x2a30d`, in the known-dead `FUN_0002a30e`/`FUN_0002a93a` region |
| `0x2B656` | `FUN_0002b62c` | FEEDBACK (assist-shaping task) |
| `0x2C488` | `FUN_0002c478` | FEEDBACK (1 kHz task) — `(gp-0x4f60_RAW * GAIN) >> 15` |
| `0x36686` | `FUN_00036682` | FEEDBACK — and its RETURN is an aggregator summand |
| `0x3684A` | `FUN_00036828` | FEEDBACK — modulates `FUN_00036682`'s hysteresis dead-band WIDTH |

⇒ Raising it for LKAS authority silently quadrupled four in-loop feedback paths. Real defect, fixed here.

⚠ **Correction:** reader #6 is NOT a second independent additive path to the motor. Its output `gp-0x6b44`
is read back INSIDE #5 to size the half-width of a hysteresis dead-band
(`sVar9=(sVar12>>1)+sVar15`, `sVar10=sVar15-(sVar12>>1)`). Parametric modulation, not a summand.

## 🛑 It will NOT fix the grinding — expected null, stated up front

- `FUN_00036682` is `y[n] = y[n-1]*(1-2a) + a*K*x[n]`, `a = 6/1024` (`0xC63D2`, byte-read `06 00`)
  ⇒ `|H(21 Hz)|` = **-46.3 dB at 3564**, **-58.3 dB at 891**. Total loop-gain change across all four
  feedback readers at 22 Hz is **≤ 0.28 dB** against a measured sensor→command transfer of 0.221.
- Independent confirmation from the lane side: of the **11** aggregator summands, exactly ONE reads
  `0xC646C` (`FUN_00036682`), and it is the most deeply attenuated lane in the whole table.

## Gates

- **GATE 1 (A): vacuous.** No RAM, no register-indirect. **(B): INHERITED, not widened** -- same cave base,
  hook and 68-byte extent (four flashed builds), payload READ-ONLY, writes only the TX buffer byte stock
  writes anyway, no scratch RAM, r6/r7 already scratch at the hook. 🛑 **Still CODE in the 1 kHz TX path --
  a higher risk class than V57's cal-only half.** Cave re-decoded from the BUILT image: all 22
  instructions correct, all 4 branch targets exact, the two loads with real counterparts differ from them
  ONLY in the reg2 field (8437 vs 8467; 2437 vs 246f), tail 0xFF with no V55 remnants. `0xC6CD0` verified free by fresh full-image
  scan (0 disp16 loads, 0 stores, 0 extended-disp, 0 LE32 pointer hits); `0xFF` from `0xC6CA4` to
  `0xC6FEF`; preceding 4-point LERP at `0xC6C90` ends cleanly at `0xC6CA4`; footer resumes `0xC6FF0`.
- **GATE 2:** ✅ **no float mirror** — a fresh scan for ANY 32-bit tp-relative access in `[0x7440,0x74A0)`
  returned **zero hits**, so this cannot repeat the V27 mirror-desync brick. ✅ forward authority unchanged
  by construction (still 3564, new address). ⚠ **REASONED, not proven:** all four feedback readers move
  TOWARD factory 891; no plant model was used.
- ✅ **MANUAL FEEL: NO CHANGE EXPECTED — on-car evidence, not an argument.** The gain went **891
  (stock/V9) → 1782 (V22-V37) → 3564 (V38+)**, byte-verified across the plain-image archive, clamps
  tracking each step (512→1024→2048). **The operator has driven all three and reports no change in
  manual steering feel.** When disengaged the FORWARD reader `0x2A1EE` is idle, so manual feel depends
  only on readers #3-#6 — exactly the set V57 reverts. The experiment is already run, both directions,
  null. ⇒ It is also independent evidence those four readers sit **below perception across a 4× range**,
  corroborating the −46/−58 dB figure for #5 and extending it to #3/#4, never quantified.
  🛑 An earlier draft claimed feel WOULD change. That was an inference from "not engagement-gated",
  which establishes the readers are LIVE, not AUDIBLE. **Withdrawn.**

## Deliberately NOT included

- `0xC61B8` 102→26 (the un-rescaled pre-gain deadband) — real defect but lives on the engage ramp only,
  see [[reference-accord-deadband-signgate-eliminated-on-car]].
- `gp-0x6bbe` boost / the angle-rate lane — GATE 2 open, see [[accord-angle-rate-lane-gp6bbe-top-candidate]].
- r24/r26 — **already flashed and falsified** (V39, V42 ch.2). Re-proposed as "novel" by a subagent this
  session; see [[accord-check-build-lineage-before-proposing-lever]].

**How to apply:** flash **V55 first** to undo V56 cleanly — V57 is cut from V55, so flashing it reverts
the V56 mute AND changes feedback gains at once, confounding feel assessment and forfeiting the cleanest
test that V56's mute was live (the 8.69 Hz line should vanish on V55).
🛑 Flash only on explicit operator instruction naming the file and the bus.
