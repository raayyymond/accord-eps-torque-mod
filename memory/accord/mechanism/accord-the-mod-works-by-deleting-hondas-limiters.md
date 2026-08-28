---
name: accord-the-mod-works-by-deleting-hondas-limiters
description: "Four separate Honda limiters are disabled in every build that shows the 7-9 Hz anti-damped excess: the arbitration core's three-way limit cascade (0xC61C0/C2/C4 -> 65535), the low-speed steer lockout (0xC62EA -> 0), 0xC64B4 -> 0xFF, and Honda's state-4 governor call (0x454FE bne -> br, so FUN_00049A5A is never called). That is what the torque mod IS. It reframes the excess as the likely PRICE of the mod rather than a bug with a single culprit, and predicts that restoring any limiter trades oscillation against authority."
metadata:
  node_type: reference
  type: reference
---

# ⭐⭐★★★★★ THE MOD WORKS BY **DELETING HONDA'S LIMITERS** — and that may be the price

2026-08-28. Assembled from the verified V112-vs-**real-stock** diff (29 main-block runs) plus the
intersection across every build showing the 7–9 Hz excess.

## THE FOUR DELETED LIMITERS — all present in every affected build, none in stock
| what | edit | verified how |
|---|---|---|
| **the arbitration core's three-way limit cascade** | `0xC61C0`/`C2`/`C4` = **1600 / 896 / 1280 → 65535** | 4 readers, two inside `FUN_00028ea6` (the arb core). At `0x2924A`–`0x2926E`: `cmp limit,r28; bh 0x29276` ×3, selected by the mode byte `gp-0x682f`. **At 65535 `r28` can never exceed them, so the limit-exceeded path is NEVER taken.** |
| **the low-speed steer lockout** | `0xC62EA` **320 → 0** | ~5 km/h; failing it sets `STEER_STATUS = 3` and kills the authority ramp |
| **`0xC64B4`** | 5 bytes **→ 0xFF** | set to max/disabled |
| **Honda's state-4 governor call** | `0x454FE` `bne` → **unconditional `br`** | `jarl FUN_00049A5A` at `0x45500` is **never reached** ([[accord-v42-permanently-deletes-hondas-state4-governor]]) |

## ⭐ WHY THIS IS THE RIGHT FRAME
The 7–9 Hz excess has resisted attribution to any single cell: **stock measures −13.1 and all 16
modified routes measure −31.9 … −74.8, but they do not order by gain, by build date, or by the
biquad** ([[accord-we-add-a-new-7to9hz-antidamped-feature.md]]). That is exactly what you expect if
the cause is **the set of deletions all of them share**, not one tunable value.
⇒ **The excess is plausibly the PRICE OF THE MOD, not a bug with a culprit.** Honda's limiters are
what bounded the loop at 7–9 Hz; removing them is what buys the torque.
🛑 **This is a REFRAME, not a proof.** It is consistent with everything measured and it explains the
non-ordering, but no single deletion has been shown to produce the excess.

## ⚠ WHAT IT PREDICTS, AND THE UNCOMFORTABLE PART
**Restoring any limiter should reduce the oscillation AND cost authority.** The trade is structural,
not a tuning accident. Sizing the cheapest restoration first:
- `0xC61C0` cascade — thresholds **896–1600 against a 15360 full scale**, so the limit path would fire
  often. **Expensive in authority. Not the cheap one.**
- `0xC62EA` lockout — affects only **below ~5 km/h**, beneath grind #1's 8–16 km/h band.
  **Cheapest, but probably irrelevant to the symptom.**
- `0x454FE` state-4 — **duty UNMEASURED**; V118's probe settles it. **Do not revert blind** (it is a
  validated fix for the V38 macro ratchet).

## ✅ WHAT TO DO WITH IT
1. **Fly V118** — it disarms the biquad (the one candidate still testable by flying) and simultaneously
   measures state-4 duty, which decides whether `0x454FE` is live enough to matter.
2. **If the answer is "the price of the mod"**, the honest options are to accept the oscillation, or
   to restore the cheapest limiter and measure what authority it costs — a decision for the operator,
   not a build to make unilaterally.
🛑 **Do not keep hunting for a single culprit cell.** Eight candidates have now been eliminated with
their own controls; the non-ordering across builds is itself evidence against one existing.
