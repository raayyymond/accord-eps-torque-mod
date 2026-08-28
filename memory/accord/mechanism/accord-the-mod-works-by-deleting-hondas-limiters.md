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

## 🛑 RESTORING THE ARBITRATION CASCADE IS **ELIMINATED AS A FIX** — the debounce settles it
```
   0xC61C0 limit A   stock  1600 -> V112 65535   CHANGED
   0xC61C2 limit B   stock   896 -> V112 65535   CHANGED
   0xC61C4 limit C   stock  1280 -> V112 65535   CHANGED
   0xC64DF debounce  stock   100 -> V112   100   UNCHANGED
   tp+0x74B4/B6/B7 mode thresholds  34 / 14 / 0  UNCHANGED
```
⭐ I first judged this restore **expensive** (thresholds 896–1600 against a 15360 full scale ⇒ it
would fire constantly). **The debounce reverses that reasoning — and then kills the lever anyway.**
The latch needs the limit exceeded for **~100 consecutive calls**. A **7.42 Hz** oscillation has a
**135 ms period**, so it crosses the threshold *intermittently* and would essentially never
accumulate 100 consecutive exceedances.
🛑 **This cascade is a SUSTAINED-FAULT detector, not an oscillation damper. Restoring it cannot
address the 7–9 Hz symptom** — it would only re-arm a latch against long, one-directional excursions.
⇒ **Do not propose `0xC61C0/C2/C4` as a fix for the oscillation.** (Whether it should be restored on
*safety* grounds is a separate question and not one the oscillation data speaks to.)
⚠ **`0xC64DE` 17 → 27 is UNEXPLAINED** — a changed byte adjacent to the debounce cal, inside our diff,
whose function has not been traced. **Open.**

## 🛑 THE ARB OUTPUT CLAMP IS **NOT** THE AMPLITUDE MECHANISM — it was scaled correctly all along
`0xC61B2`/`0xC61B4` went **512 → 3072 (×6)**, and a clamp *bounds oscillation amplitude* without
touching `Re(Z)` in the linear regime — which made it look like a clean explanation for the 16–30×
line. **It is not.** Headroom above the steady full-command output, every build:
```
  build   GAIN   clamp   steady out   HEADROOM   headroom/steady
  stock    891     512        417          95       0.228
  v96     3564    2048       1670         378       0.226
  v100    3564    2048       1670         378       0.226
  v101    7128    4096       3341         755       0.226
  v102    5346    3072       2505         567       0.226
  v112    5346    3072       2505         567       0.226
```
🛑 **The headroom/steady ratio is 0.226–0.228 on EVERY build INCLUDING STOCK.** The clamp has been
scaled proportionally with the gain at every step. With 6× gain the same physical wheel excursion
costs 6× more counts, so **567 counts of room is the same PHYSICAL room as stock's 95.**
⇒ the oscillation has **no more room to grow than on stock**, and the "restore stock's proportional
headroom" build computes to clamp **3076** against the present **3072** — **no lever exists.**
⊕ A useful negative: **the kit's clamp scaling has been correct throughout**, including V14's
original 512→1024 and every raise since. Nothing to fix here.

## ✅ UPGRADED FROM "A REFRAME" TO **QUANTITATIVE EVIDENCE** — 2026-08-28
This note previously ended "🛑 A reframe, not a proof." **It now has its proof**, from a
**16-route natural experiment** across 15 builds using the route-offset-immune within-drive statistic
([[accord-the-oscillation-excess-is-ANGLE-GATED]]).

**Method.** Outcome = log(large-angle 6-9 Hz p90), regressed on log(small-angle p90) to remove each
drive's own baseline (fit r = 0.645). The residual is the angle-gated excess. Spearman that residual
against every cal that has actually **varied** across flown builds:
```
   predictor      levels   rho      p     builds spanned
   knee  0xC40BC     3    -0.158  0.546   300 / 600 / 1800
   K1    0xC40D2     3    +0.280  0.276   102 / 204 / 612
   a2    0xC40DC     2    +0.094  0.718   14 / 22
   gain  0xC6CD0     4    -0.206  0.429   3564 / 5346 / 7128 / 65535
   biq   0xC649B     2    -0.072  0.783   off / on
   fric_gain (K1/1024)(12/knee)  +0.297  0.247
   clamp 0xC407E     1     CONSTANT across every flown build — untestable
   kd    0xC6AE6     1     CONSTANT across every flown build — untestable
```
🛑 **NOTHING that has ever varied explains it.** |rho| < 0.30 and p > 0.24 for every one, across
enormous cal ranges. That is precisely the signature this note predicted: **the cause is the shared
SET of deletions, not any tunable cell.**

### ✅ THE INVARIANT SET IS NOW BYTE-EXACT AND COMPLETE
Bytes differing from stock **and identical across all 14 flown mod builds** (V90/91/92/96/100/101/
102/103/104/105/106/107/111/112), valid dump extent 0x10000-0x100000, excluding CRC words:
```
   0x454FE  CODE 1B  ba -> b5        bne -> br: state-4 governor jarl NEVER CALLED
   0xC61C0  CAL  6B  1600/896/1280 -> 65535/65535/65535   arbitration cascade REMOVED
   0xC64B4  CAL  5B  7060364070 -> ffffffffff             torque-tier thresholds REMOVED
   0xC62EA  CAL  2B  320 -> 0                             low-speed lockout REMOVED
   0xC674F/51/5B/5D  +-1024 -> +-5120                     direction corridor x5
   0xC659A/9E/AE/B2/C6/CA/CE  f32 1.0/-1.0/0.0/1.5 -> 5.0/-5.0/5.0/5.0   corridor table x5
   0xC64DE  CAL  1B  17 -> 27                             square-wave half-period (see below)
   0x2A1F0  CODE 2B  29804 -> 31952 | 0x12FF0 0x13109 0x14120 0x55C0E 0xC4B41  (cave/CRC/ID)
```
Tool: `analysis-2020accord/verify/invariant_mod_edits_vs_stock.py`,
regression: `rlog-tools/studies/peakturn/cal_vs_angle_excess_regression.py`.

### 🛑 `0xC64DE` IS A **DEAD LEVER** — struck from the candidate list
It was the one invariant edit that is **not** an authority limit, so it looked like the free move.
It is not. [[accord-c64de-extends-an-arbitration-table-9-to-14-knots]] and the lineage label
correction settle it: `0xC64DE` is the **hold count of a sign-flipping square-wave injector** whose
**amplitude LERP at `0xC6736` is Y = (0,0,0,0) in stock AND in every build**, with every other writer
of `gp-0x6b2c` a store-zero. ⇒ **structurally inert; restoring 27→17 moves an injector that emits
nothing.** Do not build it.

### ⇒ WHAT THIS LEAVES
Every remaining member of the invariant set is a **magnitude/authority limit**. Restoring any of them
trades oscillation against exactly the authority the operator has forbidden spending
(*"scaling of the LKAS command over the steering wheel ... must outpace any damping, friction, or
programmed additional inertia"*).
✅ **⇒ The next lever must be FREQUENCY-SELECTIVE** — damping added at 7-9 Hz only, leaving the DC
and low-frequency LKAS response (hence steering velocity and acceleration) untouched.
⊕ [[accord-factord-is-the-angle-error-lever]] refuted the *cal* route to that ("this firmware has no
frequency-selective lever"), **but the dormant biquad at `0x35A28`-`0x35A50` is a real second-order
section with editable coefficients**, already armed on V103-V112, currently tuned to pole angle
0.26565 rad ≈ **42.3 Hz at 1 kHz** — which is why `biq` scores rho = -0.072 here. **Retuning its pole
to the 7-9 Hz band is the open question.** ⚠ It is all-pole with **DC gain 8.39**, so as-is it would
AMPLIFY its centre frequency, not damp it; and it sits in a loop ⇒ **GATE 2 (magnitude AND phase)
applies.** NOT yet a build proposal.
