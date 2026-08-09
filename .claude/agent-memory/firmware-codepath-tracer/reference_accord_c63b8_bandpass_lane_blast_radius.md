---
name: accord-c63b8-bandpass-lane-blast-radius
description: FUN_0003b66a's 8.13 Hz band-pass lane (cals 0xC63B4/B6/B8/BA) - full Rule-13 forward trace of gp-0x6b9a and gp-0x6ba6. Lockstep CANNOT be tripped by magnitude (structural proof). The lane has NO summing junction - its only live consumption is a boost LERP index. Two real risks - the +-10 clamp relay (V80 precedent) and the +-25600 gate cliff.
metadata:
  type: reference
---

# `0xC63B8` — the 8.13 Hz band-pass lane, full blast radius (2026-08-09, `INSERTION-BLAST-RADIUS`)

Stock `code.bin`, `program="code.bin"` explicit. Censuses = Python exact scan (disp16 + disp23).

## The lane (arithmetic verified against the decompile of `FUN_0003b66a`, `0x3b66a-0x3b8f2`)

```
fVar6  = rate-limited motor-rate chain value (+-2000 clamp, then +-565/cycle slew)
d      = (fVar6 - gp-0x3644) * 17.453293          # BACKWARD DIFFERENCE (deg->rad @1kHz)
e1    += (d  - e1) * cal(0xC63B4)/1024            # EMA1, state gp-0x3654, alpha 51/1024=0.0498
e2    += (e1 - e2) * cal(0xC63B4)/1024            # EMA2, state gp-0x3650, same alpha
bp     = e2 * cal(0xC63B8)/1024                   # GAIN 41/1024 = 0.0400
gp-0x6de8 = clamp(bp, -10, +10) * 1024            # 🛑 CLAMP IS *BEFORE* THE x1024 -> ceiling +-10240
gp-0x6de4 = (2x alpha=0.5 EMA of gp-0x4f60*4, cal 0xC63BA=512) >> 2   # ~= column torque, fc~110 Hz
gp-0x6b9a = (gp-0x6de8 + gp-0x6de4) * cal(0xC63B6)   # 0xC63B6 = 1
gp-0x6ba6 = |gp-0x6b9a|
```
**Response [EVIDENCE, computed from the real cals]:** peak `|H| = 0.0179 at 8.130 Hz`;
phase **+5.95° @7.50 · +2.41° @7.99 · +1.44° @8.13 · −0.84° @8.47 · −44.1° @21.09 · −52.1° @27.4**.
Cals: `0xC63B4`=51, `0xC63B6`=1, `0xC63B8`=41, `0xC63BA`=512. **None ever touched by any build.**

## 🛑 The lockstep CANNOT be tripped by magnitude [EVIDENCE — structural]

```c
if (gp-0x6ba6 == gp-0x4ce8) { gp-0x6ba6 = v; gp-0x4ce8 = v; } else FUN_0006b9fa(gp-0x4ce8);
if (gp-0x6b9a == gp-0x4ce4) { gp-0x6b9a = w; gp-0x4ce4 = w; } else FUN_0006b9fa(gp-0x4ce4);
```
The compare is **old cell vs old shadow, BEFORE the write**; both are then written from the **same
register**. The comparison never sees the new value ⇒ **magnitude is structurally irrelevant.** Only
real RAM corruption mismatches. `gp-0x4ce4`/`gp-0x4ce8`: exactly **1 writer + 1 reader each**, all
inside `FUN_0003b66a`. **Same idiom as the shaper's `gp-0x6b98`/`gp-0x4ce2` pair.**

**`FUN_0006b9fa` = LATCH then DTC, not an immediate shutdown:**
`FUN_0006b9fa(addr)` → `gp-0x4d6c = addr` → `FUN_0006ce7c(4)` → `gp-0x444f = 4` **and shadow
`gp-0x4e53 = 4`**. At `0x6ce98-0x6ceba`: `di` → compare the pair (mismatch → `jarl 0x6b9ee`) → `ei`
→ **nonzero ⇒ `0x6cf56`**, which calls `FUN_0005bb04(8,…)` / `FUN_0005ae6a(8,…)` and bumps a counter
at `gp-0x95f`. Fault-record/DTC path, id 8.

## 🛑 THERE IS NO SUMMING JUNCTION — the lane is a boost INDEX [EVIDENCE, Rule 13, both cells]

`gp-0x6b9a` — 1 writer `0x3b8b0`, **7 readers**; `gp-0x6ba6` — 1 writer `0x3b892`, **5 readers**:

| Reader | Function | Fate |
|---|---|---|
| `0x3b8a4`, `0x3b886` | own | internal shadow compare |
| `0x34414`, `0x3441e`, `0x34428`, `0x3443e` | **`FUN_00034350` = FactorC/E DAMPER** | **±25600 GATE only** |
| `0x34b5e`, `0x34b68`, `0x34b72`, `0x34cb6` | `FUN_00034a72` (boost) | **±25600 GATE only** |
| `0x34424` → `st.h r10,-0x6bcc` @`0x34438` | `FUN_00034350` | **`gp-0x6bcc` = 1 W, ZERO R — DEAD SINK** |
| **`0x34b6e`** | `FUN_00034a72` | **ONLY LIVE VALUE PATH — LERP index** |

⇒ Nothing adds/subtracts it from the assist demand. The one live use is `gp-0x6ba6` indexing boost
tables `0xD28DC`/`0xD2888`, whose Y curves **FALL**: `[16384,14657,11672,9365,8244,8187]` /
`[16384,14392,10265,8997,8176,8176]`.
⇒ **Sign IS correct for damping, but the mechanism is amplitude-dependent BOOST CUTBACK**, not a
damping torque. Sign-inversion risk is **not present**.
⊕ This **extends** [[reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism]], which covered
only `FUN_00034a72` and never examined the five `0x344xx` readers in `FUN_00034350`.

## 🛑 Two real risks

**(a) ±10 CLAMP ⇒ RELAY.** The clamp is **before** the ×1024, so raising `0xC63B8` never raises the
±10240 ceiling — it only reaches it at smaller inputs.

| `0xC63B8` | gain | \|H\|@8.13 | input amp to SATURATE |
|---|---|---|---|
| **41 (stock)** | 0.0400 | 0.0179 | **560** |
| 123 (3×) | 0.1201 | 0.0536 | 187 |
| 410 (10×) | 0.4004 | 0.1785 | **56** |

🛑 **This is the V80 failure mode** ([[accord-v80-damper-relay-and-grind1-inert]]): a proportional
term driven into its clamp becomes a relay and injects broadband HF. **Do not exceed ~3× without
measuring the operating-point amplitude first.**

**(b) ±25600 GATE CLIFF.** `gp-0x6de4` ≈ column torque (dominant term). Worst
`|gp-0x6b9a| = |gp-0x4f60| + 10240` ⇒ **trips above `|gp-0x4f60| ≈ 15360`.** Gate failure sets
`r21 = 0`, forcing `r24` (`gp-0x69ba`, LERP4 blend state) to **zero** — a discontinuous authority
drop. Higher gain ⇒ more time at the ±10240 rail ⇒ more time near the cliff.

## `0xC646E` is a SEPARATE lane — they do NOT multiply [EVIDENCE]
Exact tp-relative scan, whole image: **`0xC646E` = 1 access (`0x3bb92`, in `FUN_0003b8f6`)**;
**`0xC63B8` = 1 access (`0x3b80a`, in `FUN_0003b66a`)**. Disjoint adjacent functions, and **no reader
of `gp-0x6b9a`/`gp-0x6ba6` lies inside `FUN_0003b8f6`.** The +1.4° vs +14.7° similarity is coincidence.

## Tool note
`code.bin` **was** `is_current:true` throughout this session (verified 3×). A batch of 8
`get_function_by_address` calls returned **8/8 real functions** — impossible against the 3-function
v85 image ⇒ dispositive that calls hit the analysed program. Still pass `program=` explicitly.

Related: [[accord-shaper-float-twin-blocks-filter-insertion]],
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm.md]],
[[accord-gp6ba6-is-the-boost-amplitude-index]]
