---
name: accord-shaper-float-twin-blocks-filter-insertion
description: The shaper has a FULL FLOAT TWIN (FUN_00043e44) branching at gp-0x6acc read 0x4467a with a +-5-count window -> DTC 0xF00049 in ~10ms. Blocks EVERY filter insertion at or below gp-0x6b08. Includes the complete 0x43206->0x43b52 hand-walk, the 7-node spine census, and the 8 Hz phase budget.
metadata:
  type: reference
---

# Filter-insertion blast radius on the assist spine (2026-08-09, `INSERTION-BLAST-RADIUS`)

Stock `code.bin`. All censuses from an exact Python 4-method scan (disp16 + disp23 + LE32),
validated by reproducing the prior independent 45/4/41 result for `gp-0x6b98`.
Scanner pattern is in [[v850e2-extended-disp23-encoding-solved]].

## 🛑 THE BLOCKING RESULT

**`FUN_00043e44` is a full FLOAT TWIN of the shaper, not merely a monitor.**
- Its input is **`gp-0x6acc`, read at `0x4467a`** (`ld.h -0x6acc,gp,r16 ; cvtf.ws ; cvtf.sd ;
  mulf.d 1/1024 ; cmpf.d lt vs 8.0`).
- **Proof it is a twin, not a coincidence:** it reads `tp+0x71d4` and `tp+0x74c8/74c9` — the
  *identical* cals the shaper loads at `0x431c8` / `0x431cc`.
- Output `gp-0x6dbc` (**1 writer `0x44a22`, 1 reader `0x43b24`** — a private twin channel).
- Compared against delivered `gp-0x6b98` with a **±5-count** window at three sites:
  `0x43b24-0x43b44` (tag 0x20), `0x448d6` (bit32, weight 32.0), `0x44662` (weight 2.0).
- Accumulator → 128.0 → `jarl 0x462e6` id `0x3f1b` → fault 0x1d → **DTC 0xF00049 (EPS-disabling),
  ~10 ms of sustained divergence.** At 8 Hz a half-cycle is 62 ms = 6× the trip dwell.

⇒ **`0x4467a` IS THE BRANCH POINT.** Filter above it → safe. Filter below it → hard fault.

## Spine census (W = writers, R = readers, image-wide)

| Node | abs | W | R | note |
|---|---|---|---|---|
| `gp-0x6b94` | `0xFEDF146C` | 3 | 5 | only ONE command-path reader: `0x453e0` |
| `gp-0x6ace` | `0xFEDF1532` | 4 | 7 | all inside `0x454xx-0x45bxx` |
| `gp-0x6acc` | `0xFEDF1534` | 2 | 4 | `0x4467a` = twin branch point |
| `gp-0x6b08` | `0xFEDF14F8` | 1 | 2 | 3 accesses TOTAL image-wide |
| `gp-0x6b98` | `0xFEDF1468` | 4 | 41 | 12 of the 41 are **disp23** ⇒ a disp16-only scan misses them |
| `gp-0x6ada` / `gp-0x6adc` | `0x…1526`/`1524` | 1 | **0** | still dead mirrors, free telemetry |

## The `0x43206` → `gp-0x6b98` hand-walk (was "inherited")

🛑 **`0x43226` is `br 0x43268` — a BRANCH inside a Q15 slew integrator, NOT a store.** The real
write is 2,300 bytes later at **`0x43b52`**.

```
0x431c4 ld.h -0x6acc,gp,r9      chain input
0x431cc ld.bu 0x74c8,tp,r15     cal 0xC64C8 MODE (0=pass,1=static cal 0xC61D4,2=blend)
0x431d8 cmovc 0x0,r9,r11        |gp-0x6acc|>0x2000 -> ZERO (fail-safe)
0x43206 st.h r11,-0x6b08,gp     "raw target"
0x4320a-0x43226 Q15 slew integrator, 32-bit state gp-0x3570
0x43a96 ld.h -0x6b08,gp,r11     raw target back; r20 = integrator output (r28)
0x43ab4 |slewed| > |raw|+5  -> FAULT TAG 0x10      (one-sided OVERSHOOT limit)
0x43ac4 sign(raw)!=sign(slewed), both |.|>5 -> TAG 0x10
0x43af4 add r20,r12             + gp-0x6afe (sole writer 0x42ad6)
0x43b0a clamp +-gp-0x4f64       governor ceiling
0x43b20 clamp +-0x2000          final rail
0x43b24 ld.w -0x6dbc,gp         *** FLOAT TWIN, x1024, vs prev gp-0x6b98, +-5 -> TAG 0x20 ***
0x43b48 ld.h -0x4ce2,gp         LOCKSTEP shadow; mismatch -> jarl 0x6b9fa HARD FAULT
0x43b52 st.h r8,-0x6b98,gp      *** THE WRITE ***  (+ shadow 0x43b56)
```
Second exit `0x43dfc` = same pattern behind fault logger (`movea 0x2a ; jarl 0x16de6`).

## NEW safety consumers (were in no kit memory)

- **`FUN_00041b8e`** `0x41b8e-0x41d55` — float redundancy recomputation of the rate chain. Reads
  `gp-0x6b98` at **`0x41bd8`** (ONE instruction, used twice in the decompile) and uses its **SIGN**
  as a motoring/regenerating quadrant discriminator. ±5.0 tolerance vs `gp-0x6ac2/6ac0/6abe/6abc`,
  reports `FUN_000462e6` ids `0x43b7`, `0x43b5`, `0x43b3`, `0x3f5e`.
- **`FUN_000370b6`** — `gp-0x6bb0 = EMA(gp-0x6b98)`, coefficient cal `tp+0x50c0` = **`0xC40C0`**,
  state `gp-0x6df0`, **two** lockstep shadows (`gp-0x4cee`, `gp-0x4d34`) → `FUN_0006b9fa`.
  Saturation sentinel `0x7fff` when `|gp-0x6b98| > 0x2000`.
- **`0x45b16`** — comp-add difference monitor: `(gp-0x6acc − gp-0x6ace)/1024` vs the independently
  computed term → `gp-0x68f4/68f8/68fa` → `FUN_0004613e` id `0x3c35`.
  ⇒ **you may not change `gp-0x6acc` relative to `gp-0x6ace`.**

## Ranking + PHASE BUDGET at 8 Hz

| Rank | Node | Monitor-clean | Sites |
|---|---|---|---|
| 1 | upstream estimator cals `0xC646E`/`0xC63AC` | ✅ | 0 (CAL ONLY) |
| 2 | `gp-0x6b94` read at **`0x453e0`** | ✅ all 3 monitors re-derive | **1** |
| 3 | `gp-0x6ace` stored value | ✅ difference preserved | 4 |
| 4-6 | `gp-0x6acc` / `gp-0x6b08` / `gp-0x6b98` | ❌ | reject |

- **Inside the shaper: budget ≈ 2.4° at 8 Hz** — `A·|1−H| < 5` with A≈120 counts ⇒ `|1−H| ≤ 0.042`,
  `|H| ≥ 0.958` (−0.37 dB). No useful filter exists there.
- **Above the twin: monitors impose no phase limit**; binding constraint is loop stability.
  First-order EMA @1 kHz: α=0.05 (fc 8.2 Hz) = −2.9 dB but **−43°** at 8 Hz; α=0.02 = −8.6 dB, **−67°**.
- 🛑 ζ = 0.017–0.036 ⇒ PM ≈ 100ζ ≈ **1.7–3.6°** IF the mode is a closed-loop pole ⇒ a low-pass at
  8 Hz would make the ratchet WORSE. Evidence leans to a passive mode (it *rings down*), but
  Reading B is **not excluded**. ⇒ **Recommended: spend ≤ 25° at 8 Hz (α ≥ 0.095, fc ≥ 16 Hz)** —
  kills 21/28 Hz, barely touches 8 Hz. **A filter cornered AT 8 Hz is not justified by the evidence.**
- Weakest input: A = 120 counts. Measuring `gp-0x6b98` p-p during a ratchet sets the budget AND
  discriminates passive-vs-loop.

## Firmware's own filter idiom (from `FUN_00036bec`, cal `0xC63D8` = 307, α = 0.2998, fc 56.7 Hz)
```
acc += ((x * 64) - acc) * cal_Q10 >> 10     # 32-bit state
out  = acc >> 6
```
⚠ `FUN_00036bec`'s output `gp-0x6b48` is NOT on the spine (readers `0x3668a`, `0x3682c`) — it is a
side lane. Do not mistake it for a ready-made command filter.

Related: [[reference_accord_shaper_fun42af8]], [[reference-accord-eme-bit32-float-monitor]],
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]], [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]
