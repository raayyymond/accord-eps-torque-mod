---
name: accord-levers-killed-2026-08-09
description: "Eight levers killed on evidence 2026-08-09: gain_A engaged-inert, Lever A do-not-restore, the 13-point LERP dead, FactorD structurally inert, 0xC63A0 inert, 0xC61F6 and 0xC61D6 forbidden, and gp-0x6b70 refuted."
metadata:
  node_type: memory
  type: reference
---

🛑 **EIGHT LEVERS KILLED ON EVIDENCE, 2026-08-09.** Each is a **structural or measured kill**, not a
null. `FALSIFIED` ≠ `INERT-BY-MODE` ≠ `NEVER-TRIED`, and *"the same lever pushed the other way"* is a
different claim from *"a new lever."*

| lever | status | why |
|---|---|---|
| **`gain_A` rec0/rec1 lowered** (`0xC6A72`–`78`, `0xC6A86`–`8C`) | 🛑 **ENGAGED-INERT — already run, twice failed** | Lever B's gate repoint (`0x3AA96`=`FB`) makes `lp = latActive`, and the armed path at **`0x3AB5E` OVERWRITES `gain_A` with `[0xC6444]` = 512**. ⇒ **V84 and V85 ALREADY deliver 512 engaged at EVERY speed**, deeper than V72/V73's 512/512/1050/2664/2560. This is V84's own §7a **pre-registered** experiment: **FAIL on V84, FAIL on V85.** ⚠ Still live in the MANUAL arm — but the symptom is engaged-only |
| **Lever A** `0x3AB76`/`0x3AC20` `sar` `AA`→`A9` | 🛑 **DO NOT RESTORE** | the `sar` is **UNGATED**, so it applies in the manual arm too ⇒ it reproduces **V62/V65 verbatim** there, where the operator reported *"makes the entire car vibrate, almost like I have a subwoofer… regardless of LKAS engagement."* Second leg: **`r24 ≥ ~2` is necessary for grind #2 in every build that produced it.** ⚠ **The int16-overflow leg is WITHDRAWN** — `mul` writes a full 32-bit low word and `sar 0xa` operates on 32 bits, so `5120 × 5244 >> 9 = 52,440` fits with headroom. **Do not cite an r24 overflow ceiling.** The verdict rests on the manual-arm leg alone |
| **the 13-point LERP `0xC6B66`/`0xC6B80`** | 🛑 **DEAD as a shaped lever** | its axis `gp-0x6a10` is **ABSOLUTE STEERING ANGLE**, not a tracking error — `b4` ≡ `\|angle\| ≥ 0.85°` at **99.94%**, the step sits **exactly on the threshold's own numeric value**, and the relation holds in the **MANUAL** arm where a tracking error is undefined. **88.6% of engaged driving sits in its flat first segment** ⇒ a near-constant **0.878× broadband trim** — the class that V56's mute and the `0xC646C` work both nulled |
| **FactorD** (`0xD778C` m26 / `0xD77A4` m27) | 🛑 **STRUCTURALLY INERT where the symptoms live** | FactorC multiplies in **BEFORE** FactorD and has `X[0]` = 2240 ct = **34.97 km/h**, `Y[0] = 0`, in **all four** of this car's modes. **Zero × anything = 0.** A third `gp-0x6a10` consumer — the boost LERP2 in `FUN_00034a72` — is **also** flat-zero in band0 (0–8 km/h) in all four modes. **Three independent confirmations** |
| **`0xC63A0` 1024 → 2048** | 🛑 **INERT — no mechanism** | `ch₀ = gp-0x6bd0 = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)`; Honda's shape has **two zero dead zones** (FactorC below 34.97 km/h, FactorE below 12.73 °/s, both `Y[0]=0`) and the product truncates ⇒ **`ch₀` is exactly ZERO on 98.8% of engaged frames on route `6e`** (p50 **and** p90 both 0.00 against a ±25600 clamp) |
| **`0xC61F6` 3 → 0** (rate-lane deadband) | 🛑 **DO NOT — it pushes the destabilising way** | a deadband is the **DUAL of a relay**: `N(A) → 0` as `A → 0` is precisely what *prevents* harmonic balance closing. **Deleting it ADDS small-signal gain.** It costs **0.4%** at the lane's ~1029-count full scale and **nothing** whenever the total sits >3 counts off zero. ⚠ This **reverses** the framing that opened it as a candidate |
| **`0xC61D6`** (shaper slew step, stock 0) | 🛑 **ALREADY REJECTED — do not revive** | an 11-round review labelled it *"highest-risk; last/never"*: it does **not** re-enable an anti-snap ramp, it **activates a dormant, uncalibrated speed × torque 2D map** onto the live command. `0xC6424` is separately confirmed **inert** (coupled to slew = 0). ⇒ 🛑 **There is NO usable cal-only rate-limiter lever on this path** |
| **`FUN_00038148`/`gp-0x6b70` as the ~8 Hz generator** | 🛑 **REFUTED** | see [[accord-ratchet-is-a-linear-loop-oscillation]] — no harmonic comb against a control that fires at 15% injection |

## 🛑 TWO CONSEQUENCES THAT REACH BEYOND THEIR OWN ROWS
1. **THIS FIRMWARE HAS NO FREQUENCY-SELECTIVE LEVER.** *"FactorD is the only frequency-selective lever"*
   is **REFUTED** — and with it goes the argument that FactorE cannot do what FactorD can. Correct
   [[accord-factord-is-the-angle-error-lever]] on both points.
2. **`0xC63A0` ledger corrections** (each from a byte read): reverted at **V83a**, not V84;
   **V76g also carried 2048**; **V76 and V80 are 1024**. ⇒ **V42 flew at 1024 with the ratchet called
   fixed, so 2048 is not necessary**; **V72/V73 also carried Honda's damper**, so `ch₀` was zero on them
   too ⇒ the **V72/V73 correlation has NO mechanism**; and **V84's own `0xC63A0` revert was itself
   INERT** and cannot explain the V84 step.

Related: [[accord-plant-model-residual-aggregator-chain]],
[[accord-v85-flew-lever-delivered-bands-are-null]], [[accord-c61d6-slew-is-rejected-not-fresh]],
[[accord-v81-carries-neither-grind1-fix]], [[accord-check-build-lineage-before-proposing-lever]].
