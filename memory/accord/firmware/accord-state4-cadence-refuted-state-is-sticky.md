---
name: accord-state4-cadence-refuted-state-is-sticky
description: "🛑 2026-08-04 [EVIDENCE, instruction level]: state 5 is DEAD CODE on the road (gp-0x68ad can never be set in the field) and 4→10 is a ONE-WAY latch with no clear anywhere image-wide ⇒ state 4 is STICKY then leaves permanently. There is NO periodic state-4 cadence — refuted structurally, not merely unconfirmed."
metadata:
  type: reference
---

# 🛑 THE STATE-4 CADENCE IS REFUTED AT INSTRUCTION LEVEL

**[EVIDENCE — gp-relative *and* absolute encodings both checked.]**

## `gp-0x68ad` can NEVER be set in the field ⇒ 4 → 5 never fires
Both SET paths need permanently-zero flags:
- **`gp-0x437c`** — a UDS artifact.
- **`gp-0x679d`** — **newly closed 2026-08-04.** Its sole writer `FUN_000567c0` @`0x567e2` reads
  `gp-0x67ba`, and **`gp-0x67ba` has exactly ONE access image-wide and ZERO writers.**

`FUN_00019970` opens with `if (gp-0x68ad != 1) return;` ⇒ **4 → 5 NEVER FIRES. State 5 is DEAD CODE on
the road.**

## `gp-0x6d78` bit 15 is a ONE-WAY, OR-ONLY latch ⇒ 4 → 10 is a one-shot drift
**15 sites, one writer** (`FUN_000197b8` @`0x197ca`, `|= 1 << n`), **no clear anywhere image-wide**.
⇒ **10 → 4 can never fire afterwards.**

⇒ 🛑 **State 4 is STICKY once entered, then leaves permanently. There is NO periodic cadence.**
Combined with V70's bit5 reading `gp-0x67fa == 10` at **0.0000%** of 18,010 frames
([[accord-gp67fa-state-gate-on-assist-chain]]), **the reachable set on a normal drive is {4, 11}.**

## ⚠ THE TENSION TO CARRY — do not resolve it by assertion
The V42 substitution at `0x454FE` is **ASYMMETRIC** (it clamps command-magnitude *increases* and passes
*decreases*), so continuously active it should print a **rectified** waveform. **Yet the ratchet
measures SYMMETRIC** — skew **−0.16 … +0.06**, crest **2.07–2.45** against a sine's 1.414.
⇒ **evidence AGAINST the state-4 substitution shaping the CURRENT ratchet.**
🛑 **That is not evidence that restoring `0x454FE` is wrong.** V71 restores it because it is a
**confirmed fix lost by accident** ([[accord-both-confirmed-fixes-were-off-the-car]]) — **not** because
this mechanism is established. Keep the two statements separate.

## ✅ Safety, re-verified 2026-08-04 against `_v70_plain_image.bin`
`FUN_0004595a` `[0x4595A, 0x45A1F)` and `FUN_000462e6` `[0x462E6, 0x46360)` are **0 diff bytes vs
stock**; the DTC-0x1d-no-debounce path is unchanged. The *"the substitution only ever makes `gp-0x6ace`
smaller ⇒ safe side"* argument **transfers**, but remains **[INFERRED]**, not verified.
`0x454FE` sits in the bridged main CRC block `[0x13000, 0xC4FFC)`.

## 🛑 [OPEN]
**What sets `gp-0x6d78` bits 15/16 mid-drive.** `FUN_000197b8` has **21 callers, untraced.** That
decides whether state 4 is sticky for a whole drive or only briefly.

See [[reference-accord-state4-governor-ratchet]], [[accord-ratchet-q-measured-40]],
[[reference_accord_override_snap_state_machines]].
