---
name: accord-r24-gain-b-four-pointer-arrays
description: ★ r24's gain_B is mode-indexed through FOUR SEPARATE pointer arrays (0xCBF5C/0xCC044/0xCC12C/0xCC214), NOT four consecutive records -- reading them consecutively understates the motor-rate rolloff by 2x. gain_A is not mode-indexed at all.
metadata:
  type: reference
---

> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** ★ This file is **correct and now load-bearing**: because `gain_B` is mode-indexed, **every r24 edit V69/V70/V72/V73 made was written at mode 10 and was INERT** on a mode-24/26 car. Modes 24/26 live at `0xD6A9C`/`0xD6AD8` and `0xD7A88`/`0xD7AC4`.

# ★ `FUN_0003ad74`: r24's gain surface, resolved — and the trap in reading it

Orchestrator-verified 2026-08-01 from the `FUN_0003ad74` decompile plus byte reads of
`_v65_plain_image.bin`. Corrects a provenance gap in `eps_lkas_chain_model.py`.

## The structure

`FUN_0003ad74` builds BOTH runtime rate-gain LERPs each cycle, and **the two halves are not symmetric**:

| lane | records | mode-indexed? | runtime output |
|---|---|---|---|
| **gain_B (r24)** | **four SEPARATE pointer arrays**, each indexed `mode*4`: `0xCBF5C`, `0xCC044`, `0xCC12C`, `tp+0xD214` = `0xCC214` | **yes** (`gp+0x63fd`, = **10** on this car) | X → `gp-0x6e40`, Y → `gp-0x6e38` |
| **gain_A (r26)** | four FIXED records `tp+0x7a68/7a7c/7a90/7aa4` = `0xC6A68/7C/90/A4`, hard-coded | **no** | X → `gp-0x6e30`, Y → `gp-0x6e28` |

Cross axis = `tp+0x7010` = **`0xC6010`** = `[0, 640, 3200, 6400]` = 0 / 9.99 / 49.95 / 99.9 km/h at
64.0625 counts/km/h, keyed on `gp-0x6a5e` (voted vehicle **speed**), substituting cal `tp+0x7314`
when `gp-0x67f4 != 1`.

## 🛑 THE TRAP

For mode 10 the four pointers resolve to **`0xD2A74` / `0xD2AB0` / `0xD2AEC` / `0xD2B28`** — **NOT four
consecutive records at a stride.** Records for modes 10 and 11 are interleaved in that region, so
reading four consecutive 20-byte records from `0xD2AEC` picks up mode 11's rows and yields a nearly
**flat** surface (2305 → 1948), **understating the real rolloff by 2×**. I made exactly that error
before decompiling `FUN_0003ad74`, and it changed a lever's expected effect.

Records are **private per mode** (mode 11 → `0xD2A88`/`0xD2AC4`/`0xD2B00`/`0xD2B3C`), so a cal edit
touches one variant only.

⚠ **`build_v62_tva.py`'s `GAIN_B_LERP_MODE10` tripwire watches only `0xD2AEC` and `0xD2B28`** — it is
**blind** to an edit landing on `0xD2A74` or `0xD2AB0`. Widen it before any cal work on this lane.

## The real surface (mode 10, byte-read, Q10)

```
0xD2A74   X=(0,400,1400,3000)  Y=(3072,3072,2322,1536)     speed 0 km/h
0xD2AB0   X=(0,400,1500,3000)  Y=(2561,2561,2247,1947)     speed 10
0xD2AEC   X=(0,400,1500,3000)  Y=(2305,2304,2149,1948)     speed 50
0xD2B28   X=(0,400,1500,3000)  Y=(2151,2151,2049,1947)     speed 100
```

⇒ **At creep the gain is 3072 and FLAT out to motor rate 400 counts** (≈85 deg/s at 4.7121 counts per
deg/s), falling to **1536** at 3000 (≈637 deg/s) — a genuine **2× rolloff**. At road speed it flattens
(0.80× at 32 km/h). **Honda already de-escalates this lane when the wheel moves fast, and only at low
speed.**

🛑 The frequently-quoted *"r24 default arm = 2305"* is the **50 km/h** record. At the hands-off-creep
operating point — where grind #1 lives — it is **3072**. Any ×2 sizing must use 3072, not 2305.

⚠ `0x3AAC8`/`0x3AACC` folds a motor rate **≥ 13001** to **0** — and 0 is the LERP's *first*
breakpoint, so the fold lands on **MAXIMUM gain**. Confirmed from the decompiler rather than from
disassembly operand order (`rateKey = gp-0x6ac0 * (gp-0x6ac0 < 0x32c9)`), and one shared value feeds
**both** r24's and r26's LERP evaluations. 13001 counts = **2759 deg/s** (~7.7 wheel rev/s), so it is
fault/glitch-level rather than ordinary driving — but it is a **genuine 2× step discontinuity**
(array1 jumps 1.5× → 3.0× at that instant), and anyone moving breakpoints near the top of the axis
must know it exists. The load is `ld.hu` ⇒ the axis is a magnitude.

⚠ Two further structural facts from the same trace: **`FUN_0003aa2c` is itself state-gated** — its
caller invokes it only when the one-hot `gp-0x67fa` falls in mask `0xC30` — and **`gp-0x67ac`'s
trigger is unresolved**: if it is ever 1, r24/r26 **and six other lanes** silently drop out of the sum.

🛑 **And the mode-indexed LERP is only r24's gain when THREE override flags are all clear**
(`gp-0x671d == 0` ∧ `gp-0x683c == 0` ∧ `gp-0x671a ≤ cal 0xC64FA`). The interpolation is computed
unconditionally; only the *selector* is conditional. `gp-0x683c` is dead, but **`gp-0x671d` is live and
outranks everything** — see [[accord-gp683c-dead-gate-is-a-free-lkas-arm]].

✅ **`gp-0x6ac0`'s scale is now CONFIRMED, and the 4.7121 figure is exact.** `gp-0x6ac0` is
**`|gp-0x6abe|`** — both come from ONE EMA accumulator in `FUN_00041464` (`gp-0x6abe = state >> 10`,
`gp-0x6ac0 = abs(state) >> 10`), verified at instruction level. The counts-per-deg/s figure was
independently reproduced as an exact rational: **`2^18 / (48 × 1159) = 16384/3477 = 4.71210813…`**.
So the mode-10 breakpoints are **400 → 84.89 deg/s · 1400 → 297.11 · 1500 → 318.33 · 3000 → 636.66**.
⚠ Note the asymmetry: **array1 (the 10 km/h record) uses 1400, not 1500** — a slightly tighter knee at
low speed than the other three records.
⚠ The **other** CAN copy does not cross-check cleanly (the `0x18F` route implies ~5.89 counts/deg/s
against `0x14A`'s 4.7121 — a 0.1-vs-0.125 scale mismatch between the two packers, unreconciled).
**Use 4.7121**; it is the one reproduced through the cited chain. Flagged for whoever revisits `0x18F`.

See also [[accord-gp683c-dead-gate-is-a-free-lkas-arm]], [[accord-ratchet-is-a-saturated-resonance]],
[[accord-v62-fixed-the-grinding]].
