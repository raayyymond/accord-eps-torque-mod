---
name: reference-accord-slot-array-asil-monitors-and-shadow-arrays
description: "GATE-1 expansion: the 11-slot assist channel arrays are protected by EIGHT shadow-lockstep array pairs (FUN_00028d22) AND by a floating-point plausibility monitor (FUN_00027b0a) that independently recomputes gp-0x6b4c / gp-0x6b4a / the gp-0x6afe sum and faults on a >3/1024 mismatch. Also records gp-0x4f64/gp-0x448a as a further shadow pair and the FUN_00038148 lane-weight map."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE ASSIST-CHANNEL LANE IS **REDUNDANTLY MONITORED IN FLOAT** — a cave that edits it will fault

Found 2026-08-22 while tracing the feedforward question. **This materially raises the Gate-1 bar for any
edit anywhere in the 11-slot channel machinery, and it was not in the kit's record.**

## 1. `FUN_00027b0a` @`0x27b0a` — the ASIL plausibility monitor (task 1, slot `0x16`, 1 kHz)
It walks the same 11 slots, dispatching on the **same cal `0xC4124`** (`movea 0x5124,tp,rX` at `0x27b26`,
`0x27cce`, `0x27cf2`, `0x27f24`), recomputes every accumulator **in IEEE float** (`× 0.0009765625` =
÷1024), and compares against the integer results. On a mismatch it calls
`FUN_0004613e(code, actual, expected, +tol, −tol)`:

| fault code | quantity checked | tolerance |
|---|---|---|
| `0x3ce6` | `gp-0x6b4a` | ±3/1024 |
| `0x3ce7` | **`gp-0x6b4c`** (the 11-slot assist sum) | ±3/1024 |
| `0x3ce8`/`0x3ce9`/`0x3cea`/`0x3ced` | the per-slot MIN accumulators `gp-0x698a`/`gp-0x6988`/`gp-0x6986` | ±3/1024, ≤0x400 |
| `0x3cfb`–`0x3cff`, `0x3d00`–`0x3d04`, `0x3d12`/`0x3d13` | the six raw slot sums incl. **`gp-0x62c8` → the `gp-0x6afe` lane** | ±3/1024 (±100 for the 0x633c sum) |
| `0x4157`/`0x4158` | slot-liveness counters | |

⇒ **Any cave that perturbs `gp-0x6b4c`, `gp-0x6b4a`, `gp-0x62b0[]`, `gp-0x62c8[]`, `gp-0x6298[]`,
`gp-0x625c[]`, `gp-0x6324[]`, `gp-0x61b8/61d0/61e8[]` or `gp-0x6afe` WITHOUT making the float
recomputation agree will trip a fault within one tick.**
⭐ The corollary is the good news: because the monitor dispatches on `0xC4124` too, **changing a channel's
routing mode keeps the monitor consistent by construction.**

## 2. EIGHT shadow-lockstep ARRAY pairs [EVIDENCE — `FUN_00028d22` @`0x28d22`, task 1 slot `0x14`]
It sweeps 11 slots × a rotating field index `gp-0x3d40` (0–3) and reports via `gp-0x690a`/`gp-0x6909` →
`FUN_0006b9fa`:
```
gp-0x62e0[] / gp-0x4b70[]      gp-0x62f8[] / gp-0x4b88[]
gp-0x633c[] / gp-0x4ba0[]      gp-0x6230[] / gp-0x4b10[]
gp-0x6298[] / gp-0x4b28[]      gp-0x62b0[] / gp-0x4b40[]
gp-0x62c8[] / gp-0x4b58[]      gp-0x61e8[] / gp-0x4af8[]
```
⊕ Also found: **`gp-0x4f64` / `gp-0x448a`** (`FUN_0007b022` `0x7c2de`–`0x7c2e6` → `FUN_0006b9ee`).
🛑 **The kit's "shadow-lockstep pairs are AT LEAST SIX" figure is badly stale — it is at least 8 arrays
(88 cells) plus the scalar pairs.** Treat any count as a floor and re-census before any cave.

## 3. `FUN_00038148` lane-weight map, resolved [EVIDENCE — `0x38148`–`0x3820c`]
Six zero-rejected addends, each `× cal >> 10`, summed, then `× gp-0x6752` (polarity) `× 0xC6468`(2639),
`>>10`, `<<4`, → `gp-0x6ad6` (clamped ±0x6400; `0xC6200`=8192 clamps it elsewhere):

| addend | zero-reject window | weight cal | stock/V106 value |
|---|---|---|---|
| `gp-0x6bbe` | ±0x800 | `0xC63A2` | 1024 |
| `gp-0x6bd0` | ±0x800 | `0xC63A0` | 1024 |
| `gp-0x6b46` | ±0x400 | `0xC63A4` | 1024 |
| `gp-0x6b26` | ±0x400 | `0xC63A6` | 1024 |
| **`gp-0x6b4c`** (governed lane) | ±0x2800 | **`0xC63AA`** | **1024** |
| **`gp-0x6b4e`** (direct lane) | ±0x2800 | **`0xC63A8`** | **1024** |

⭐ **`0xC63A8` == `0xC63AA` == unity ⇒ moving a channel between the two lanes is EXACTLY NEUTRAL for
`gp-0x6ad6`, the torque-tracking reference.** That is the decisive Gate check for a `0xC4124` re-route.

## 4. `0xC4124` ownership census — two methods, set-difference EMPTY
- Ghidra `search_instructions("0x512")`: 5 × `movea 0x5124,tp,rX` — `0x26cdc` (`FUN_00026c80`) and
  `0x27b26`/`0x27cce`/`0x27cf2`/`0x27f24` (`FUN_00027b0a`). Three further hits at `0x584f6`/`0x58ea6`/
  `0x5900a` are `ld.w -0x5124,r6|ep` — **different base register; adjudicated false positives.**
- Python raw LE scan of literal `0x5124` over `[0x13000, 0x100000)`: **exactly 5 hits**, at
  `0x26cde`/`0x27b28`/`0x27cd0`/`0x27cf4`/`0x27f26` = hw2 of those same 5 `movea`s. No `0x5125`
  literal, no `0x4124` literal ⇒ **no `movhi`/`movea` absolute form and no register-indirect route.**
- ⇒ **exactly two readers, zero writers — a pure build-time cal.**

## 5. `0xC4118` (tp+0x5118) census — same shape, also clean
- Ghidra `search_instructions("0x5118")`: **10 hits, all `movea 0x5118,tp,rX`** — `0x27222`/`0x272c2`/
  `0x272e0`/`0x2747e`/`0x2756c` (`FUN_00026c80`) and `0x280ac`/`0x281fe`/`0x28226`/`0x28252`/`0x2837a`
  (`FUN_00027b0a`). **Zero stores.**
- Python raw LE scan of `0x5118` over `[0x13000, 0x100000)`: **exactly 10 hits**, at hw2 of those same ten.
  **Set-difference empty.** `0x5119` = 0 hits ⇒ no odd-parity `ld.bu` form.
- Absolute form: literal `0x4118` has 2 raw hits (`0x7e550`, `0xbc958`) — **both false positives.**
  `0xbc958` is data surrounded by zeros; at `0x7e54c` the bytes are `01 32 80 ff | 18 41 e4 77`, the
  halfword before `0x4118` is `0xff80` whose opcode field is **`0x3c`, not `movea` (`0x31`)**, and the
  8-byte pattern repeats. Neither is preceded by the `movhi 0x000c` an absolute `0xC4118` would need.
- ⇒ **two readers, zero writers.** Bytes `[1]*11` on stock and V106.

## ⚠ THE `ld.hu` disp|1 TRAP, caught live
A raw scan for `0x50f4` (the per-slot authority thresholds `0xC40F4`) returns **0 hits** and looks like a
dead table. `ld.hu` encodes its displacement with bit 0 SET: the real literal is **`0x50f5`**, which has 6
hits — including `0x25c5e`, i.e. `ld.hu 0x50f4[ep],r12` at **`0x25c5c` inside `FUN_00025c32`**, a live and
load-bearing read. **Always scan `disp|1` as well as `disp` before calling a table dead.**

Related: [[reference-accord-c4124-channel-router-two-lanes-lkas-is-slot1]] ·
[[accord-v850-scan-traps-formatv-and-storezero]] · [[accord-task1-cave-precedent-and-telemetry-ceiling]]
