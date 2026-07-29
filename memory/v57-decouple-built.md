---
name: v57-decouple-built
description: "V57 = V55 + the 0xC646C decoupling: 0x2A1EE retargeted to a private gain word at 0xC6CD0 so the 4x hits the LKAS forward path ONLY, while the four feedback readers revert to stock 891. BUILT and verified, UNFLASHED. Correctness fix, expected NULL for the 20-25 Hz mode."
metadata:
  node_type: memory
  type: project
---

**Built 2026-07-29. UNFLASHED.** 14 bytes off V55 (6 edit + 8 CRC), 88 bytes off V38.

```
0x2A1F0  ld.h displacement  0x746C -> 0x7CD0   (tp+0x7CD0 = 0xC6CD0)   [MAIN block]
0xC6CD0  new private LKAS gain word  0xFFFF -> 3564                    [CAL block]
0xC646C  shared sensor scale         3564  -> 891 (stock)              [CAL block]

_v57_plain_image.bin  SHA 9a027e82c065d48721bd194e315528516ef6963fc4821511c7e7242676ab13ea
V57 .rwd              SHA 816d225522f7a327ee9b97bf096bec918e7e36c82f57a17225e0f5455216d019
```

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

- **GATE 1: vacuous.** No cave, no RAM, no register-indirect. `0xC6CD0` verified free by fresh full-image
  scan (0 disp16 loads, 0 stores, 0 extended-disp, 0 LE32 pointer hits); `0xFF` from `0xC6CA4` to
  `0xC6FEF`; preceding 4-point LERP at `0xC6C90` ends cleanly at `0xC6CA4`; footer resumes `0xC6FF0`.
- **GATE 2:** ✅ **no float mirror** — a fresh scan for ANY 32-bit tp-relative access in `[0x7440,0x74A0)`
  returned **zero hits**, so this cannot repeat the V27 mirror-desync brick. ✅ forward authority unchanged
  by construction (still 3564, new address). ⚠ **REASONED, not proven:** all four feedback readers move
  TOWARD factory 891; no plant model was used.
- ⚠ **EXPECTED: manual steering feel WILL change.** Readers #3-#6 are not gated on openpilot engagement.
  That is the point of the fix, but it is perceptible. V52C is the precedent.

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
