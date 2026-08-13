---
name: reference-accord-lkas-friction-is-viscous-not-a-rate-limit
description: The operator's "LKAS fights excess friction" is real and is in the EPS — three viscous rate-opposing terms, no live hard rate limiter, and an engaged-only amplification we ourselves added at V74.
metadata:
  type: reference
---

★★★★ **THE OPERATOR WAS RIGHT AND THE "IT'S AN OPENPILOT SAFETY FEATURE" ANSWER WAS WRONG.**

Complaint (2026-08-06, and he is explicit it predates V75 and is *not* the openpilot command rate limit):
*"peak torque is 4× higher, but it has to fight extra friction logic when turning the wheel, so it only
turns the wheel slowly."*

🛑 **THERE IS NO LIVE HARD RATE LIMITER ON THE STEERING ANGLE ANYWHERE IN THIS FIRMWARE.**
- The shaper's slew limiter `gp-0x356c` (step cal `0xC61D6`) is **0 = disabled in stock**. Re-enabling was
  already **rejected** (V16) — 0→14 activates an uncalibrated 2-D map, not a damper.
- `0xC6194` is architecturally **bypassed** — 🛑 **CORRECTED 2026-08-12: the long-standing reason
  *"output ×0"* is WRONG; that is `0xC6196`.** `0xC6194` is **REAL and calibrated** — 3 ct/tick =
  1.37 s full scale, which is *exactly* the shape the operator described — **but its input partition
  `0xC4118` is all-1, so 100 % of the request bypasses it.** ⚠ **Arming it goes the WRONG way.**
  The conclusion (no live rate limiter) is unchanged; the reason was wrong for ~2 weeks.
- A 45-site sweep of every `gp-0x6b98` access (4 writers, 41 readers) finds only static **magnitude**
  clamps (±0x2000 / ±0x2800 / ±8192), **no rate limiter**.

## What actually exists: three VISCOUS terms that oppose column rate

| term | arithmetic | on stock | status |
|---|---|---|---|
| **`gp-0x6b26`** (`FUN_00036c12`, 1 kHz) | `clamp((gate(gp-0x6c2c) × Y_speed(gp-0x6a5e))>>6 × 0x111 >>0x12, ±0xC407E)`; **−0.15995 counts out per count of rate at 0 km/h**, falling ~5× by 90 km/h | live, **identical in modes 24 and 26** | 🆕 **VIRGIN — never edited by any build.** *This is the always-there baseline the operator feels* |
| **`gp-0x6bd0`** base-assist damper | `(FactorC(speed) × FactorE(rate))>>10` | **exactly 0 below 35 km/h** (`FactorC Y[0]=0`) | opened at creep by V74, relay-ised — see [[reference-accord-v74-v75-damper-is-a-sampled-relay]] |
| return-to-centre S-term (`gp-0x6b62`) | `−Y(gp-0x6bda) × gp-0x6abc >>10 × 1024 >>10`, all `Y≥0` + one negation ⇒ always `−sign(rate)` | live, narrow driver-torque band | never touched; **unexplored lever** |

Full-torque passes; the viscous terms **consume a growing share of it as the wheel speeds up**. That is
exactly "strong torque commanded, wheel turns slowly" — and it is a damper signature, not a limiter's.

★ **Why it feels LKAS-specific with NO LKAS-specific code**: the drag is an **absolute** count of opposing
torque, but the LKAS command is **bounded** entering the aggregator while the driver's arms are not. The
same drag therefore eats a far larger fraction of an LKAS command. [BELIEF on the perceptual attribution;
EVIDENCE on the arithmetic and the speed schedule]

🛑 **THE ALTERNATIVE THE OPERATOR MIGHT EXPECT DOES NOT EXIST**: no term is indexed by *commanded torque*.
**`FactorB` — the one genuinely torque-domain factor — is FLAT UNITY (1024×4) in modes 24 AND 26.**
Opposition is mediated entirely through **motion**, never through demand. [EVIDENCE]

## ⊕ AND WE MADE IT WORSE, ENGAGED-ONLY, FOR THE FIRST TIME AT V74

| | mode 24 MANUAL | mode 26 ENGAGED |
|---|---|---|
| stock / V73 | `[-9830,-5734,-1966]` | **identical** |
| **V74 / V75** | **byte-stock** | **`[-14745,-8601,-2949]` (×1.5)** |

Plus **`0xC407E` 511 → 850** since V73 — **NOT mode-indexed**, so it raises the drag ceiling **in manual
too**. Delivered opposing torque at the lane's measured percentiles: p90 **284 → 426** engaged, p99
**511 → 846**.
★ **On stock, modes 24 and 26 carry byte-identical damping and friction rows** — engagement relabels the
table slot but selects the same numbers. **So the LKAS-vs-manual asymmetry now on the car is OURS,
introduced at V74.** V73's friction edit was mode 10 ⇒ inert (RULE 7).

## Levers, ranked — and the honest trade
1. **`0xD7A54`+8 (mode 26 friction Y) → stock** — 6 bytes, subtractive, engaged-only. ★ Friction ×1.5 was
   **already fully in force on V74, which did NOT fix the grind** ⇒ reverting it is unlikely to cost the
   grind result. **The clean single-variable feel test.**
2. **`0xC407E` 850 → 511** — MODE-PROOF, 2 bytes; also restores manual. ⚠ its recorded "null" is
   **spectral, never a feel result** — it does not falsify it against effort.
3. The damper itself (FactorC/FactorE) — but that is entangled with the grind fix and the V75 fault.
4. `0xD6A64` (mode 24 friction) — 🆕 never written by any build, if manual effort is ever the target.

⚠ RULE 7: everything except `0xC407E` is **mode-indexed** and must be written to the engaged column of all
16 rows (`{2,3,5,11,14,15,17,23,26,27,29,32,33}`) to be in force while leaving manual byte-stock.
