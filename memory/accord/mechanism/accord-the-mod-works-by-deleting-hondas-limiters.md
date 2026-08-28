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

## ✅ WHAT THE ARBITRATION CASCADE ACTUALLY DOES — and a probe-invalidating trap that did NOT fire
Traced the limit-exceeded path at `0x29276` (the target of all three `bh` branches):
```
  0x29276  add 0x1, r12 / sxb r12        ; a DEBOUNCE COUNTER
  0x2927C  bge 0x29288                   ; not yet expired -> save and leave
  0x29288  ld.bu 0x74df,tp,r10           ; cal(0xC64DF) = the debounce reload
  0x2928C  mov 0x4, r8
  0x2928E  st.b r8, -0x6807, gp          ; ** ON EXPIRY, WRITE 4 TO gp-0x6807 **
  0x29296  st.b r10, -0x6757, gp         ; reload the counter
```
⇒ the cascade is a **debounced fault/mode latch**: exceed a mode-selected threshold for long
enough and the code **latches the value 4** into `gp-0x6807`. Setting the thresholds to 65535 means
**that latch can never arm.**

### 🛑 THE TRAP THAT DID NOT FIRE — checked before trusting V118/V119's probe
It looked as though we might have disabled **both ends of one protection**: the cascade never
latching *4*, and `0x454FE` never calling `FUN_00049A5A` when `gp-0x67fa == 4`. If `gp-0x6807` and
`gp-0x67fa` were the same state, **the probe would read zero because we made state 4 UNREACHABLE**,
not because it is rare — and the pre-registered "<1 % ⇒ eliminated" rule would have been **exactly
backwards**.
✅ **They are different cells, and `gp-0x67fa` has MANY writers** — `st.b` at `0x19816`, `0x19862`,
`0x198AC`, `0x198D8`, `0x19908`… in `FUN_000197ea` / `FUN_00019888`, a state machine in the 0x19xxx
region **that none of our builds touch**. ⇒ **state 4 remains reachable and the probe is valid.**
⚠ That `search_instructions` returned `truncated: true` after 19,615 of 183,671 instructions, so the
writer list is **partial** — but partial is enough here: finding writers we do not touch is what the
check needed.
