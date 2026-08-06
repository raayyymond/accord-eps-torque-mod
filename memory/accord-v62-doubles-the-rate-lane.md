> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** V62's `sar` edits are **CODE, therefore MODE-PROOF** — this build really did deliver x2 on both lanes, and it is one of the few that delivered anything at all. 🛑 **Strike every comparison against V69/V70 "doses"**, which were inert.

---

# ★★ V62 BUILT — double the torsion-bar rate lane via two `sar` immediates (6 bytes off V59)

Built 2026-07-31, **UNFLASHED**. The exact inverse of V61, which is what makes it a matched experiment:
V61 took `Kd` to 0 and the mode diverged; V62 takes `Kd` to 2× — the same-sized step the other way.
See [[accord-rate-lane-is-the-damper-not-the-amplifier]] for why the direction is up.

```
0x3AC20  42AA -> 42A9   sar 0xa,r8 -> sar 0x9,r8   r24: (dtorque * gain_B) >> 10 -> >> 9
0x3AB76  32AA -> 32A9   sar 0xa,r6 -> sar 0x9,r6   r26: (stage1  * gain_A) >> 10 -> >> 9
image SHA 80d9e1f721b741722a9d4b141a2d328fe8d999705765fedffab1ad23aa9264c7
RWD   SHA 1e0806a1eac69688e6d636fa02c5b1e864da40a65a4d3f8137d444d1ec5bff8e
```
6 bytes off V59 (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38. ⭐ **CAL CRC unchanged** and
⭐ **`0xD2000`-block CRC unchanged** = machine proof no calibration moved and V60's falsified blend is
absent. 50/50 CRC blocks pass; RWD round-trips with every gate re-run on the readback.

## 🛑 Why `sar` immediates and NOT the gain calibrations — three reasons, all found by tracing
1. **The gain is a PRIORITY CHAIN and the live arm cannot be pinned statically.**
   `assist_state gp-0x671a` is a bounded **[0,5] persistence ramp** tracking *consistent sign* of a rate
   signal — during a 21 Hz oscillation it plausibly never saturates. `gp-0x671d` is an **event/rising-edge
   counter** (not startup dwell) that may be self-excited by the oscillation. Editing a cal means betting
   on a branch.
2. **r24's default arm is MODE-INDEXED, not one location.** `FUN_0003ad74` reads a mode byte at
   `gp+0x63fd` (`0003ad88 ld.bu 0x63fd,gp,r16`) and indexes four ROM pointer arrays (`0xCBF5C`,
   `0xCC044`, `0xCC12C`, `0xCC214`). `0xD2AEC`←`0xCC154` = idx 10; `0xD2B28`←`0xCC23C` = idx 10;
   **`0xD6AEC`←`0xCC184` = idx 22.**
   ⚠ **CORRECTION of record:** `0xD6AEC` is **NOT a redundancy twin** of `0xD2AEC` and this is **not the
   V27 desync class** — an earlier reading this session called it that. They are **two different modes'
   records that happen to be byte-identical**, each reached through its own valid pointer slot.
   (Mode **10** is this car: PN `39990-TVA-A160` → key `TVAA1` → config row 2 → INDEX 10, the chain
   V44/V47 were confirmed on-car to hit. One-bit residual: the coded row is in EEPROM, not the dump.)
3. **`gp-0x683c` has ZERO writers image-wide** ⇒ the 512 arms `0xC6446`/`0xC6444` are dead calibration.
   ⚠ single-method — wants a raw LE byte scan of **both** gp-relative encodings before anything rests on it.

`sar 0xa → sar 0x9` doubles the lane **under every branch of the chain and every mode.** Immune to all three.

## 🛑 Why `0x3AB76` and not `0x3AB70` for r26 — an overflow argument
r26 is two chained multiplies: `stage1 = (dtorque*avg)>>10` @`0x3AB70`, `pre = (stage1*gain_A)>>10`
@`0x3AB76`. **V850 `mul r1,r6,r0` discards the HIGH word into `r0`** — a 32-bit overflow is silently
truncated into a garbage, possibly sign-flipped lane value. Worst case (`avg = 0xFFFF`, `dtorque = 5120`):

| edit | `stage1 * gain_A(3072)` | vs INT32_MAX |
|---|---|---|
| stock | 1.007e9 | 47% |
| @`0x3AB70` | 2.013e9 | **94% — 6% margin** |
| @`0x3AB76` | **unchanged** 1.007e9 | 47% — no new risk |

Doubling the **second** shift leaves every multiply operand at its stock magnitude.

## Headroom — doubling stays LINEAR (a saturating lead term would be worse than useless)
Producer `FUN_0007e74a`: `gp-0x4f62 = ((current − delayed) << 1) / dt`, D = 4 (`0xC6C42`), 1 kHz.
At the measured 1400 counts / 20.9 Hz, `peak dtorque ≈ 367` = **7% of the shared ±5120 clamp**.
r24 then sits at ~9% of its own ±8192 clamp on the `state≥5` arm. **Headroom is arm-dependent — quote the
range:** ~22× (`gate_671d`, 1024), ~11× (`state≥5`, 2048), **~7.3× (natural LERP at stock max 3072 — the
worst case)**. Doubling keeps ≥3.6× margin under every arm. Model: `analysis-2020accord/rate_lane_damping_model.py`.

## Gates
- **GATE 1 (RAM ownership): VACUOUS.** No cave, no new RAM cell, no new opcode. Caves are this kit's only
  bricking class (V24, V27, V48B).
- **GATE 2:** this *is* the gate-2 argument — it raises the damping coefficient of the mode in question,
  in the one lane fast enough to act on it (task 1, 1 kHz, ~3.8° lag vs task 5's 37.6–75.2°).
- ⚠ **RESIDUAL:** `avg(gp-0x69a4)` — r26's slope factor — has an **unmeasured magnitude** ([OPEN] across
  three sessions; its LERP axis `gp-0x6b4a` is a `FUN_00026c80` mixer output, possibly LKAS-adjacent, so
  r26's own gain may be command-driven — a second-order loop nobody has modelled). If r26 were already
  pinned at ±8192, doubling would deepen a saturation. **Bounding argument against:** a lane pinned at
  8192 would dominate the aggregator's own ±10240 sum clamp, and V61 (which zeroed it) would have
  produced a far more dramatic change than reported. Not proof. **r24 is fully bounded and immune to this.**
- ⚠ **Manual feel WILL change** — no LKAS-only decoupling point exists in this chain (traced). Risk
  direction is "nervous"/noise-sensitive, not heavy. This is the lane whose *removal* the operator felt
  immediately, so a feel change is itself confirmation the edit is live.
- Reversible by reflashing V59 (stock lane) or V61 (killed lane).

## ✅ RETRACTED reasoning worth not re-deriving
An earlier draft called `0xC6C42` (delay D) unsafe *because* `gp-0x4f62` is lockstep-shadowed to
`gp-0x4488`. **That is wrong.** `0xC6C42` has exactly **one reader** (`FUN_0007e74a` itself, 4 `ld.hu`),
and D feeds a **single computation broadcast to both cells in sync** — no desync mechanism exists.
The real reason it stays stock: D is the differentiator's **time window**, uncharacterised at other values.
⇒ **D is a legitimate future PHASE lever: 4→2 halves the lead's transport lag, 15.1° → 7.6° at 20.9 Hz.**
That is the natural V63 if V62's gain doubling is null.

## The drive
Repeat the V61 route so the comparison is like-for-like: parking-lot creep, LKAS on/off at matched speed
and angle, **plus the same manual-forward and manual-REVERSE passes**. 🛑 **Manual reverse is the
highest-information single test** — V61 introduced grinding there from nothing, with no LKAS in the loop
at all. Probe unchanged (`rlog-tools/decode_v59_boostindex.py`), secondary readout only.

Related: [[accord-rate-lane-is-the-damper-not-the-amplifier]], [[accord-task5-is-100hz-damper-cannot-damp-21hz]].
