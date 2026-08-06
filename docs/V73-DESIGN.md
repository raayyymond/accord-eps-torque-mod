# V73 — DESIGN

**Status: SPEC FROZEN. Build in progress.** Written 2026-08-05, from the V72 flight (route `59`).
Read with `docs/STATE.md`, `docs/BUILD-LINEAGE.md` (**RULES 3/4/5 first**), and `docs/V72-DESIGN.md`.

**Fleet:** 9 agents — 5 firmware (GhidraMCP), 4 data. **Six structural claims reversed under independent
checking this session, two of them the orchestrator's own.** The conclusions below are the ones that
survived a second pass; where something is still single-sourced it is marked.

---

## ★★★★★ THE HEADLINE — V72's DAMPING LEVERS WERE NEVER IN FORCE, AND WE CAN PROVE IT ARITHMETICALLY

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`, where `mode = *(byte)(gp + 0x63fd)`. **There are 13 mode variants.
V72 edited modes 10 and 11 only.**

On V72, mode 10/11 carry `FactorC = [430,430,430,877]` (so `C >= 430` at *every* speed — below
`X[0] = 2240` it clamps to `Y[0]`) and `FactorE = [927,927,927,927]` (so `E = 927` at *every* rate).
Therefore:
```
|gp-0x6bd0| = 1024 * (430/1024) * (927/1024) = 389 MINIMUM, unconditionally
```
⇒ **had the car been in mode 10 or 11, V72's `bit4` (`|gp-0x6bd0| >= 64`) would have fired on 100% of
frames. It fired on 0 of 87,940, including 0 of 34,275 above 35 km/h.**

> **[EVIDENCE] The car is NOT running mode 10 or 11. Levers B and C were INERT BY TABLE SELECTION.**
> Not a broken probe, not a vacuous seed, not a missing factor — all three were independently
> eliminated on the way to this. **The damping approach to the ratchet has never been tested.**

★ **Why it went unnoticed for a dozen builds:** the mode comes from a config lookup (`FUN_00057f8e`)
matching a 5-byte ASCII key at `gp+0x6408..0x640C` against 16 records at `0xCD000`. Row 2 is `'TVAA1'`,
and `39990-TVA-A160` "reads as" `TVA`+`A1` ⇒ index 2 ⇒ modes 10/11. **That mapping is an assumption in
`BUILD-LINEAGE.md`, never a measurement**, and `build_v44_tva.py` has patched modes 10 **and** 11 since
V44 *because of it*. The measurement says it is wrong.

⚠ **What is NOT established: which mode IS live.** See §4.

---

## 1. THE V72 FLIGHT — one fix real, one not, and a naming correction

| symptom | verdict | evidence |
|---|---|---|
| **creep grind #2** | ✅ **ESTABLISHED** | routes 58/59 have **identical 691.2 s** exposure; r59 has *more* in every burst-producing cell; **7 bursts vs 0**, exact Poisson **p = 0.0078**; vs V62/V65 **p = 0.00009**; pooled two-lane row (V67+V68+V72) **0 in 2,656 s vs 31, p = 6e-5** |
| **highway grind #2** | ❌ **NOT SUPPORTED** — strike it | 0 bursts in 253.4 s ⇒ **P(0) = 0.456**; no build in the corpus has *ever* produced a highway burst. The real result is a **non-regression**: V72 removed V71B/V71C's 40-49 Hz elevation (**0.448 vs V71C, outside null**) at an inaudible 91 counts |
| **micro ratchet (7.79 Hz)** | ❌ **NOT FIXED** — attenuation factor **1.0** | three independent instruments: D3 **1.269 [0.176, 1.936]**, D4 **0.80-1.18 all inside their own nulls**, D1 **1,261 p-p / 54%** vs **stock pool 1,267 / 51%**. Column moves **2.1-2.5x FURTHER** than on V71B/V71C |
| **macro ratchet** | ⚠ **FIXED per operator, UNMEASURABLE** | two purpose-built instruments, **64 of 65 comparisons inside their own nulls** — and both **fail their own positive control** (cannot separate V71B/V71C from V72, the arms the operator separates). **Uninterpretable in both directions** |
| **grind #1** | ❌ **614 [311, 1187] — the STOCK band** | consistent with stock **P = 0.985**; excluded HIGHER than V62/V65/V67/V68/V71C at **P < 0.0001** |

🛑 **NAMING, settled by the operator: there are TWO ratchets.** **MACRO** = the large-scale symptom he
reports fixed. **MICRO == the 7.79 Hz line** — *"not audible, felt in the column as steps"*, which is
exactly right: **7.7 Hz is below the ~20 Hz hearing threshold**, so it is felt and not heard. All three
data agents measured the MICRO one; nobody measured MACRO, because nobody knew to look separately.

🛑🛑 **THIS "CRUX" IS RETRACTED, 2026-08-06 — ITS PREMISE IS FALSE.** Quoted, not deleted, because it was
load-bearing for V73's design rationale:

> ~~**THE CRUX: at <= 10 km/h V72's delivered gain is BIT-IDENTICAL to V67/V68's** — the same absolute
> numbers 5244 / 512 at every rate index, not merely the same ratio — **and V72 scored stock's grind.**
> Restricted to that dose-matched stratum V72 is **consistent with stock (P = 0.874)** and excluded
> higher than V67+V68 at **P < 0.0001**; effort-matching runs *against* V72 twice. ⇒ *the creep
> rate-lane gain is not what separated them, and the rate lane is exhausted as a lever.*~~

**[EVIDENCE, byte-read]** At ≤ 10 km/h **V72 delivers r24 = 1.000× and V67/V68 deliver 1.707–2.048×**;
they match on **r26 only** (both 0.167×). ★ Both images contain the literal **5244** — V72 in the
**mode-10 `gain_B` surface (INERT** on a mode-24/26 car, RULE 7**)** and V67/V68 in the **`0xC6446` gated
arm (LIVE, mode-proof)**. *Same number, same lane, opposite delivery.* ⇒ **compare DELIVERED gains, never
cal values** (`analysis-2020accord/_grind2_delivered_lib.py`). The withdrawal is recorded in
`docs/STATE.md` and `memory/accord-grind1-is-a-limit-cycle.md`.

---

## 2. ROOT CAUSE — GRIND #1 IS A LIMIT CYCLE

**[EVIDENCE, 8 routes, D1's decomposition of each build's median into duty x in-burst amplitude]**

| | range across builds |
|---|---|
| **duty** | 0.015 -> 0.958 — **64x** |
| **in-burst amplitude** | 1232 -> 1533 — **1.24x** |

against a **5.62x** dose ladder. Amplitude is tight *within* build too (CV **0.17-0.26**), and `log10
e_18-22` is **two-moded on exactly the arms that have the cycle and one-moded on the arms that suppress
it**, with the high mode at **1073-1353** on three independent arms — the same place as the in-burst
amplitude. Latch and unlatch.

> **Successful builds stop the cycle STARTING. None makes it smaller.**

Priced as excess over its own in-window 24-28 Hz control (a fully eliminated mode reads 1.00):
V61 **12.42** · stock **8.77** · V72 **6.40** · V71C **4.17** · V62+V65 **2.82** · V67+V68 **2.21**.
**Nothing reaches 1.0 on any build**, and the last factor of dose buys almost nothing while the first
bought 4x. ⇒ that is a floor, not a dose-response — and it is why ten builds of rate-lane tuning stalled.

⊕ **Independently corroborated from the other direction:** F4 swept `a` (`gp-0x69a4`) from 0 to 32.0 in
both summed and differential models and **no value makes the cross-build ladder monotone** (best
|tau| = 0.429). **Grind #1 is not a scalar-gain phenomenon.**

### 2.1 The two symptoms share a driver but are DISTINCT MODES
- **Shared driver [EVIDENCE]:** partial `r(6-9, 18-22 | 24-28)` = **0.460**, circular-shift null
  [-0.102, +0.023], **p = 0.0002**, build-independent (within-episode r = 0.60-0.77 on *every* build).
  ⚠ The raw correlation would have fooled us — the control band tracks nearly as hard.
- **Distinct modes [EVIDENCE]:** **opposite-signed dependence on steering position.** Over 0-45 deg the
  ratchet's amplitude grows with distance from the sensed zero while grind #1's does not (window-level
  Spearman **+0.23 / +0.32** vs **+0.05 / +0.06**, two independent pipelines, n = 117 and 437; ratio of
  ratios ~**2.0-2.3** for any split between 3 and 20 deg; robust to leaving out any route or any block).
  **Two amplitudes of one oscillation cannot do that.**
⇒ **Anything that moves one should be expected to move the other. Score BOTH on every future build.**

⚠ **The angle result is DIAGNOSTIC, not a lever.** Two rounds of firmware search found no angle-indexed
structure of adequate magnitude (the best candidate, `0xC6B64`, moves only **3.8%** over the measured
0-45 deg range against a 3.2x measured effect, and is indexed by tracking *error*, not absolute
position). **Nothing in the corpus separates firmware from plant** — self-aligning torque, rack friction
or assist level varying with rack position fit equally well.

---

## 3. THE LEVERS

### 3.1 LEVER A — the rate lanes, CARRIED BYTE-IDENTICALLY
V72's configuration owns the one **established** fix (creep grind #2, p = 6e-5). 🛑 **It is not touched.**

### 3.2 LEVER D — grind #1, the friction lane de-saturated and raised
**`0xD2A44` Y-values x1.5** (`-9830/-5734/-1966` -> `-14745/-8601/-2949`) **paired with `0xC407E`
511 -> 850.**

`gp-0x6b26` (`FUN_00036c12`, **1 kHz**) is the only well-phased damper in the chain and it is **not** the
rate lane, so it cannot re-open the grind-#2 trap:

| | 20.9 Hz | 45 Hz |
|---|---|---|
| phase vs motor rate | **cos -0.63** | **cos -0.96** |
| delivered-torque ratio 45/21 | — | **1.5-2.9x at every amplitude and gain tested** |

⇒ 📋 **FALSIFIABLE PREDICTION: raising this lane suppresses 40-49 Hz at least as hard as 18-22 Hz. It
must NOT reproduce V62's grind-#2 regression.** That is the pass/fail on the next drive.

★ **Why the pairing:** at 1.5x the p99 pre-clamp reaches 846 against the stock 511 clamp; `0xC407E` -> 850
clears the entire p50-p99 range while staying under the aggregator's own `±0x400` = 1024 gate. ⚠ At 2.0x
the p90 clips even before the clamp raise, and clearing p99 would need 1128 — past the aggregator gate.
**1.5x is the clean rung.**

**Lineage [RULE 4, byte diff across all 67 built images]:** `0xD2A44`, `0xCBE74`, `0xC407E`, `0xC407C` —
**zero differences, all four regions. Virgin.** Monitor exposure is a **same-domain dual-store** check
(`gp-0x6b26`/`gp-0x4cd0`), **not** a cross-domain float twin like `gp-0x6bd0`'s DTC-0x1d pair — raising
the LERP writes both copies together and cannot trip it. Confirmed independently by two agents.

⚠ **FEEL COST, named in advance:** at hand-steering frequencies (0.3-5 Hz) this lane is **30-54 dB down**
and near 90 deg phase, so smooth parking manoeuvres feel essentially unchanged. What changes is a
**momentary extra resistance at the onset of a QUICK low-speed input** — a fast hand-over-hand flick or
sudden correction — **strongest at parking speed and gone by highway** (`Y_speed` peaks at 0 km/h and
falls ~5x by 90 km/h). **This is a different character from V72's friction/breakaway offset.**

### 3.3 LEVER E — the micro ratchet, damping delivered to the mode the car actually reads
For **every candidate mode** (0,1,2,3,4,5,12,14 — modes 10/11 keep V72's values):
```
FactorC Y[0] := that record's own Y[1]      FactorE Y[0] := that record's own Y[1]
```
★ **`Y[0] := Y[1]` is the largest value that keeps the curve MONOTONE, and it PRESERVES the rate/speed
proportionality** — only the dead first segment is lifted to meet the second.
🛑 **It deliberately does NOT flatten the row.** V72 set mode 10's FactorE `Y[0..2] -> 927`, making it
**flat across the whole rate axis** — converting a rate-proportional damper into a **near-bang-bang
relay**. A relay in a feedback loop at a lightly-damped resonance is a limit-cycle *generator*. **Had
Lever B been delivered, it could have made the ratchet worse.** That defect is not repeated.

**Why the damper is the right lever for THIS symptom, and only this one** — corrected sample rate,
`FUN_00041464` runs at **1 kHz** (not 312.5 Hz; the `andi 0xd30,r25` gate is a **state mask**, not a
phase counter, and this kit's own settled memory says there is no phase rotation in the control tasks):

| | 7.79 Hz (micro ratchet) | 20.9 Hz (grind #1) |
|---|---|---|
| base damper phase | **cos ~0.92** | cos ~0.5 |
| friction lane gain | **0.411x** its 21 Hz value | 1.000 |

⇒ **the base damper reaches the ratchet and the friction lane does not; the friction lane reaches grind
#1 and the base damper is mediocre there.** The two levers are matched to their targets and do not overlap.

**Safety:** the ECU runs **exactly one** mode, so every other edited mode is inert on this car.
No-clip asserted per mode against that mode's own ceiling record. ⚠ **The dose differs a lot by family**
— 106 counts for modes 0-3 but only **33** for 4/5 and **32** for 12. **If the live mode proves to be
4/5 or 12, this lever is weak and V74 must raise it against the mode now known to be real.**

### 3.4 THE PROBE — one question, asked properly
```
bit7      = 1                              liveness
bits 6:3  = (*(byte)(gp+0x63fd)) & 0xF     THE MODE (0-15 covers every reachable value)
bits 2:0  = stock STEER_SENSOR_STATUS, preserved
```
**Standing lesson, earned across six uninterpretable nulls (V64/V67/V68/V69/V70/V72): read the GATE, not
the lane output.** V72 spent a rung on `|gp-0x6bd0| >= 64` — the output — and got a null that took nine
agents to interpret. **V73 reads the selector.**
- **reads 10/11** ⇒ the structural chain holds, V72's edits *were* live, and the `bit4` null needs a
  fifth explanation.
- **reads 0-5 or 12** ⇒ confirmed, Lever E is aimed correctly, and V74 refines its magnitude.

---

## 4. WHAT IS OPEN, AND STATED HONESTLY

1. 🛑 **Which mode is live.** Modes **4/5 and 12 are fully consistent** with the `bit4` null (route 59's
   highway `gp-0x6ac0` peaked at **329.8 counts** against their **330-335** trip thresholds — never
   reached). **Modes 0-3 are marginally disfavoured** (11 of 34,277 frames exceeded their 270-count
   threshold) but that is within 100 Hz sampling slop. **Modes 10/11 are excluded.** The probe settles it.
2. ⚠ **Whether the HW-ID key is ever populated on a running vehicle.** Its only writer is a UDS service
   (`FUN_000508e8`); `gp+0x6408` is **`.bss`**, zero-cleared at boot and outside the `.data` restore
   range; **no boot-time NVM reload was found by two agents.** ⚠ But F3 flags honestly that the boot
   loops use `sst.w` with a **computed `ep`**, a pattern invisible to all four search methods used — so a
   restore path could exist and not have been found. **A production ECU would normally retain its
   identity in NVM, which is itself a reason to suspect a missed write path.** [OPEN]
3. ⚠ **The macro ratchet is unattributed** — every instrument built for it failed its own positive
   control. ⇒ **V73 carries all of V72 byte-identically and only ADDS.** Nothing in Levers A/B/C moves.
4. ⚠ **`gp-0x6bd0`'s null has no *fifth* explanation if the mode reads 10/11.** Seed pinned at 1024
   (two derivations, plus the `.data` boot image read at flash `0x86E80` = eleven 1024s), FactorB/D flat
   unity, no external writer (3 stores, all inside `FUN_00034350`), ceiling >= 512 everywhere, probe
   encoding hand-verified. **If the mode is 10/11 we are out of hypotheses.**
5. ⚠ **The friction-lane saturation estimate moved 2.4x** when the sample rate was corrected. The lever
   survives, but its "already pinned at the resonance" framing does **not** — only the p99 tail clips.

---

## 5. WHAT V73 DOES NOT DO
- It does **not** touch the r24/r26 rate lanes. **That is the point.** Every previous grind-#1 fix moved
  them and fed grind #2; Lever D is a different lane with the opposite frequency tilt.
- It does **not** claim to fix the macro ratchet — that symptom is unmeasured and unattributed, and V73
  preserves whatever fixed it by changing nothing.
- It does **not** address the angle-position gradient. No firmware structure of adequate magnitude was
  found, and plant cannot be excluded.
- It does **not** touch `0xC4124`, the mode-dispatch role table. Editing it would un-close the
  `gp-0x67ac` vacuity gate, whose REDUCED branch zeroes r24, r26 **and** damping — **making every lever
  this kit has ever flown vacuous by construction.**
- It does **not** touch `gp+0x63fd` or the selector logic. The fix is to write proven values into the
  live mode's records, not to force the selector.

---

## 6. FLIGHT INSTRUCTION
Ordinary driving is sufficient for the probe — **the mode reads out within seconds of the first
engagement.** For the levers: **creep with openpilot engaged, wheel working through moderate excursions
(25-75 deg p-p), near and away from centre**, plus some **quick low-speed hand-over-hand inputs** to feel
Lever D's named cost. ⚠ And **score BOTH bands on this drive** — 18-22 Hz and 6-9 Hz share a driver, so a
lever that moves one should move the other.
