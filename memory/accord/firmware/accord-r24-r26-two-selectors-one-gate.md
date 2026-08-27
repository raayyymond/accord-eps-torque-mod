---
name: accord-r24-r26-two-selectors-one-gate
description: "★★★★ 2026-08-04 [EVIDENCE]: THE DOSE AXIS THIS KIT HAS USED SINCE V62 IS THE WRONG LANE. stock→V70→V69 is a clean single-variable r24 series (x1→x2→x4 = 879/729/746, CIs overlapping) ⇒ r24 is NEAR-INERT; every build that fixed grind #1 changed r26. r24/r26 have separate selectors sharing one gate, and r26 is LIVE on-car."
metadata:
  type: reference
---

# ★★★★ THE DOSE AXIS THIS KIT HAS USED SINCE V62 IS THE WRONG LANE

## 🛑 There IS a clean single-variable r24 series, and it says r24 is NEAR-INERT
**[EVIDENCE — medians recomputed from `_grind2_lib.wrecs`, not quoted from the record.]**
**stock → V70 → V69 holds r26 at ×1 and steps r24 ×1 → ×2 → ×4:**

| build | r24 | r26 | median `e_18-22` (engaged creep) |
|---|---|---|---|
| stock | **×1** | ×1 | **879** |
| **V70** | **×2** | ×1 | **729** |
| **V69** | **×4** | ×1 | **746** |

**All three CIs mutually overlapping** ⇒ **r24 is close to INERT for grind #1 across a 4:1 dose range.**
And across the corpus: **every build that FIXED grind #1 changed r26** (V62 ×2; V67/V68 ÷6.00), and
**every build that changed only r24 did not.**
⇒ ★★ **The correct headline is NOT "nothing is single-variable" — it is "the dose axis this kit has
used since V62 is the wrong lane."**

## The structure [EVIDENCE — orchestrator-disassembled, both selectors read out of the image]

**`r26 → gain_A`**
- `0x3AB5E ld.hu 0x7444[tp],r8` — `0xC6444` = **512**, taken when `lp != 0`
- `0x3AB68` — `0xC643E`
- else — **gain_A's own LERP (3072 at creep)**

**`r24 → gain_B`**
- `0x3ABFE` — `0xC6442` = **1024**, the **`gp-0x671d` mask arm, which OUTRANKS ALL**
- `0x3AC08` — `0xC6446`, taken when `lp != 0`
- `0x3AC12` — `0xC6440` = **2048**
- else — **the mode-10 speed×rate surface**

⇒ **V67/V68's ONE-BYTE gate repoint at `0x3AA96` raises r24 AND cuts r26 6.00× at the same time.**
Net delivered vs stock = `(5244 + 512·a) / (3072 + 3072·a)`, `a = gp-0x69a4/1024`:
**a = 0 → 1.707× · a = 0.848 → 1.000× PARITY · a > 0.848 → BELOW stock.**

**V69 and V70 edited gain_B only.** ⇒ 🛑 **every published multiplier in this kit is an r24-only number
computed at `a = 0` — a number on the lane shown above to be near-inert.**

★ **Four supporting byte facts, all [EVIDENCE]:**
1. **gain_A's four records `0xC6A68` / `0xC6A7C` / `0xC6A90` / `0xC6AA4` are BYTE-IDENTICAL across all
   11 images** ⇒ **V67/V68's ÷6.00 (= 512/3072) is EXACT, and engaged-only.**
2. **The two LERPs live in separate RAM** — `gp-0x6e40`/`gp-0x6e38` for gain_B, `gp-0x6e30`/`gp-0x6e28`
   for gain_A — filled by the **two halves of `FUN_0003ad74`**.
3. **gain_B is filled from the MODE-INDEXED arrays; gain_A from FIXED, non-mode-indexed records** ⇒
   V69/V70's mode-10 surface edit **could not reach r26 even in principle**.
4. **There is NO `gp-0x671d` mask arm on the r26 side** — gain_A is **2 arms + default**, not 3.

## 🛑 r26 IS LIVE — existence proof [EVIDENCE], and it REFUTES the inertness claim on-car
V70's probe read `gp-0x6adc` (r26's post-clamp mirror) **strictly negative on 1,644 of 18,010 frames**
on route `50`. **A pinned-zero cell cannot clear a `>= 0` test.**
⇒ **[[accord-r26-is-structurally-inert]]'s LEG 2 is REFUTED, not merely downgraded**, and *"r24 carries
the entire lane"* is gone.

★ **New asymmetry [EVIDENCE]: `bit3 ⇒ bit4` STRICTLY** — **0 of 18,010** frames with r24 ≥ 0 while
r26 < 0. **[BELIEF]** the natural reading is *"r26 is ZERO part of the time, same-signed otherwise"*,
consistent with the shared polarity load `ld.b -0x6752[gp],r14` @`0x3AB78` (reused at `0x3AB7E` for r26
and `0x3AC3E` for r24).

## ⚠⚠ CARRY THIS UNEXPLAINED — do not smooth it
**r26 ×2 (V62/V65) AND r26 ÷6.00 (V67/V68) BOTH HELPED, and ÷6 helped MORE** (168 vs 109 against
stock's 879). **A monotone "more r26 damping is better" story and a monotone "less is better" story are
both refuted by the same two rows. The corpus cannot say why, and that is the leading open question.**
🛑 **Anyone proposing an r26 dose must state which direction they are betting on and why.**

★ **Independent bus-side support, arrived at without the disassembly [EVIDENCE]:** median `e_18-22` by
**bar-torque reversal count**, engaged creep — in the **rev ≥ 40** regime (where the ratchet lives),
**V62 reads 396 against 1155–1403 for V59 / V64 / V69 / V70. V62 is the odd one out, and it is the only
build with r26 ×2.**

## ✅ V62's `sar` route is the ONLY dose-exact encoding
`0x3AB76`/`0x3AC20` scale **both** lanes identically ⇒ **2.000× on the total for every value of `a`.**
Every other rung in the ladder is `a`-dependent. That is why V71 restores this route rather than
re-deriving the dose through a cal arm.
★★ **And it says which half of V71 is load-bearing: `0x3AB76` — the r26 `sar` — IS THE LEVER.**
`0x3AC20` (the r24 `sar`) is restored **for exact V62 parity, NOT because r24's dose is expected to
matter.** Say it that way, so a null on r24 is not later read as a null on the build.

## The ladder re-read against what each build actually carried
Median `e_18-22`, engaged creep:

| build | r24 | r26 | median `e_18-22` |
|---|---|---|---|
| V61 | ×0 | ×0 | **2501** |
| stock | ×1 | ×1 | **879** |
| **V70** | ×2 | ×1 | **729** |
| **V69** | ×4 | ×1 | **746** |
| **V62 / V65** | **×2** | **×2** | **168** |
| **V67 / V68** | gated arm | **÷6** | **109** |

⇒ **r24's dose is FLAT from ×1 through ×4, and both builds that fixed grind #1 changed r26.**
[EVIDENCE] is the **flatness of the r24 rung** and the **co-occurrence**; ⚠ the **direction** of the r26
effect is **not** established (see the unexplained ×2-and-÷6 result above).
⚠ **The "non-monotone dose–response with a minimum near 2×" is RETIRED** — it priced every build on r24
alone at `a = 0` ([[accord-v69-flew-dose-response-non-monotone]]).
🛑 **And grind #1 is BLIND to r24 gain, which retires a MEASUREMENT TOOL:** log-log slope
**−0.144 [−0.991, +0.347]**, pairwise **P = 0.667 / 0.610 / 0.426** ⇒ **grind #1 cannot be used as an
in-force check for the r24 lane on ANY future build.** Structural, not a power limit.
★ **Methodological: CI OVERLAP IS NOT A TEST** — the subsample-at-matched-exposure test excludes V62's
level at **P < 5e-5** where the CI comparison called it undecided. **"V70 is not at V62's level" IS
established; where it sits between stock and V62 is NOT.**

## 🛑🛑 `0xC6444` IS STRUCK — a NULL BY CONSTRUCTION, not an untested lever
**[EVIDENCE]** it is read **ONLY** at `0x3AB5E`, and **only when `lp != 0`**. On **every gateless
build** — stock, V62, V65, V69, V70, **V71** — the gate `0x3AA96` is `c5`, so `lp` derives from
`gp-0x683c`, which has **0 writers image-wide** ⇒ **that load never executes.**
⇒ **Raising it changes NOTHING** unless `0x3AA96` is also repointed — which reintroduces **the V67/V68
control path the operator rejected.** ⇒ **it is reachable only on a build whose control path is already
ruled out.** 🛑 **Do NOT re-propose `0xC6444` as a single-variable r26 test.** ⚠ The old *"untested
upward / V42 tested it downward"* framing was correct arithmetic about the wrong question, and **this
supersedes it.**

✅ **THE SINGLE-VARIABLE r26 TEST EXISTS ANYWAY — via `gain_A`'s RECORDS, not the arm.**
[EVIDENCE, orchestrator byte-read 2026-08-04] `gain_A` has the **same 4-record × 4-point layout on the
same `0xC6010` speed cross-axis** as `gain_B` (`[0, 640, 3200, 6400]` counts = `[0, 10, 50, 100]` km/h):
```
rec0 0xC6A68  X=[0,400,1600,3000]  Y=[3072,3072,2434,2048]
rec1 0xC6A7C  X=[0,250,1200,3000]  Y=[3072,3072,2488,1536]
rec2 0xC6A90 / rec3 0xC6AA4        <- leave STOCK => exactly 1.000x at >=50 km/h
```
⇒ **doubling rec0/rec1's WHOLE rate axis doses r26 ALONE, below 50 km/h**, arithmetically identical to
V62's `0x3AB76` `sar` at creep, and **structurally stock at highway**. Double **Y[0..3]**, not just
Y[0..1] — restricting to the flat segment is exactly the mistake V69/V70 made in the `gain_B` encoding.
**That is V71B.** ⚠ Open: r26's saturation rail depends on the **unmeasured** `avg(gp-0x69a4)`, so
unlike r24 it is not bounded — size it before doubling. ⚠ `gain_A` is **not** mode-indexed; confirm no
other consumer reads those records.

See [[accord-both-confirmed-fixes-were-off-the-car]], [[accord-aggregator-lane-mirrors-6ada-6adc]],
[[accord-r24-gain-is-a-speed-rate-surface]], [[accord-v70-flew-grind1-back-at-stock]].
