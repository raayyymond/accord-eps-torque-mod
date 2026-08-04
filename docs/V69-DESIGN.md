# V69 — DESIGN SPEC

**Status: SPEC ONLY. Not built, not flashed.** Awaiting operator approval before `build_v69_tva.py`.

**Goal:** remove the engagement-conditional 24–30 Hz amplification at highway (the felt lane-change
vibration) **without losing grind #1's fix**, as a pure calibration + in-place-byte edit — no code cave.

Read with `docs/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md` (the measurement),
`docs/BUILD-LINEAGE.md` (what is already falsified) and `docs/STATE.md`.

---

## 1. 🛑 THE HONEST PREMISE, STATED FIRST

**The mechanism is SUGGESTIVE, NOT ESTABLISHED.** The evidence that the r24 rate lane causes the
28 Hz lane-change transient is a maneuver-conditioned dose ratio of **3.334 [1.201, 6.492]** at
26–30 Hz whose CI **does not clear its own split-half null of [0.33, 3.36]** — the Kd = 1 maneuver
arm holds only 39 windows / 17 blocks (~50 s). The operator was offered the drive that would settle
it (≈150–250 s more active LKAS-off highway maneuvering) and **declined it**; V69 is therefore built
on a suggestive mechanism by explicit decision. That is a reasonable call — the edit is cheap,
reversible, and self-testing — but it must not be written up later as though the mechanism had been
proven first.

**What IS established** and independent of the mechanism:
- The symptom is real and captured: `4e` seg 33 t = 51.3 s, ALC right lane change at 25.93 m/s,
  bar **1468 counts p-p**, 26–30 Hz envelope **614** (20× route median), lines at 28.12/28.51 Hz at
  prominence 100–107, **40–49 Hz reads 69 in the same window**. Not wheel order 2 (24.93 Hz) or 3
  (37.40), not engine order 1 (26.10) or 2 (52.20).
- "Only when engaged" is **REFUTED at 40–49 Hz** (maneuver/control 2.516 [1.561, 3.701] engaged vs
  2.558 [1.469, 3.747] manual) and the engagement-conditional part sits at **18–28 Hz**.
- V67/V68's arm delivers its **maximum** dose at highway (**2.4383×**, reproduced twice
  independently) because a flat scalar replaces a surface Honda rolls off with speed.

---

## 2. WHY THE DESIGN IS FORCED

`FUN_0003aa2c`'s r24 gain selection is a four-way priority ladder (addresses verified in the flown
image by hand-decoding the bytes, not only from Ghidra):

```
0x3ABFA  cmp r0,r6              ; MASK   gp-0x671d != 0   -> cal 0xC6442 = 1024
0x3AC04  cmp r0,lp              ; GATE   (V67/V68: gp-0x6806) -> cal 0xC6446 = 5244
0x3AC0E  cmp r0,r2              ; 3rd    gp-0x671a >= 5    -> cal 0xC6440 = 2048
0x3AC16  (join)                 ; else   the mode-10 speed x rate LERP
```

The gate branch is `cmp` 2B + `be` 2B + `ld.hu` 4B + `br` 2B = **10 bytes, fully packed between two
other arms — zero slack.** So:

1. **The gated arm is a FLAT constant.** One scalar cannot serve both endpoints: stock LERP is
   **2621** at grind #1 and **2172** at highway, so 1.00× at highway needs 2172, which is **0.83×**
   at grind #1 (below stock — V61 territory, and V61 made grind #1 *worse*); while 2.00× at grind #1
   needs 5244, which is **2.4383×** at highway. **Structurally unsolvable as a flat arm.**
2. **Speed shaping exists only on the DEFAULT branch** (`FUN_0003ad74`'s cross-interpolation, outer
   axis = voted speed `gp-0x6a5e`). The gate *discards* that value.
3. ⇒ **The engaged path can only see speed shaping if it falls through to the LERP**, i.e. the gate
   must be off. Composing "gated AND shaped" requires inserting instructions into a zero-slack
   branch — a **code cave on the 1 kHz path**, this kit's only bricking class (V24, V27, V48B all
   bricked the ECU), also subject to DTC 0x18's per-task overrun budget. **Rejected.**

⇒ **V69 reverts the gate and shapes the surface. The operator accepted the consequence** (§6).

---

## 3. THE EDIT

### 3.1 Byte table

| # | address | before | after | meaning | CRC block |
|---|---|---|---|---|---|
| 1 | `0x3AA96` | `fb` | `c5` | gate load reverts `ld.bu -0x6806[gp],r15` → `-0x683c` (stock's **dead** cell, 0 writers image-wide) | MAIN `[0x13000, 0xC4FFC)` |
| 2 | `0xC6446` | `7c 14` (5244) | `00 02` (512) | the now-unreachable arm returns to stock, so no future reader mistakes 5244 for live | CAL `[0xC6000, 0xC6FFC)` |
| 3 | `0xD2A7E` | `00 0c` (3072) | `00 18` (6144) | rec0 (**0 km/h**) Y[0] | `[0xD2000, 0xD2FFC)` |
| 4 | `0xD2A80` | `00 0c` (3072) | `00 18` (6144) | rec0 Y[1] | same |
| 5 | `0xD2ABA` | `01 0a` (2561) | `02 14` (5122) | rec1 (**10 km/h**) Y[0] | same |
| 6 | `0xD2ABC` | `01 0a` (2561) | `02 14` (5122) | rec1 Y[1] | same |
| 7 | `0xC4B36` | `88` | `80` | probe: the liveness `movea` immediate — **bit3 constant 0** (§7) | MAIN |
| 8 | `0xC4B54` | `61` | `60` | probe: `cmp 0x1,r6` → `cmp 0x0,r6` — **bit4 constant 1** (§7) | MAIN |

**Eight bytes. Three CRC blocks.** No cave growth, no new instruction, no new RAM cell.

Edits 3–6 are each an **exact doubling** of the low-rate end of the two lowest-speed records.
Y lives at record+0x0A, X at +0x02, count at +0x00 — confirmed from the firmware's own accessor
arithmetic (`psVar11[i+5]` = Y[i]).

### 3.2 Which record is which — the trap that would have inverted this design

🛑 **`.claude/agent-memory/firmware-codepath-tracer/reference_accord_r24_gainb_table_structure_and_priority_gate.md`
assigns the four mode-10 records to the WRONG cross-axis speeds, rotated by one.** Under that
reading this edit would land on the **10 and 50 km/h** records and would *raise* the highway end —
the exact opposite of the goal. It is wrong. Verified three independent ways:

- **pointer arrays**: `0xCBF5C + 10×4 = 0xCBF84 → 0xD2A74`; `0xCC044 + 10×4 → 0xD2AB0`;
  `0xCC12C + 10×4 → 0xD2AEC`; `0xCC214 + 10×4 → 0xD2B28`. Slot *i* pairs with cross-axis `X[i]`.
- **cross axis** `0xC6010` = `[0, 640, 3200, 6400]` counts = `[0, 9.99, 49.95, 99.9]` km/h.
- **monotonicity**: Y[0] reads 3072 / 2561 / 2305 / 2151 in that order — a speed rolloff must be
  monotone, and the rotated reading makes it non-monotone.

⇒ **`0xD2A74` ↔ 0 km/h · `0xD2AB0` ↔ 10 km/h · `0xD2AEC` ↔ 50 km/h · `0xD2B28` ↔ 100 km/h.**
**Correct that memory before any subagent reads it again.**

### 3.3 Per-record inner axes differ

`rec0 X = [0, 400, **1400**, 3000]` but `rec1–3 X = [0, 400, **1500**, 3000]`. Applying one record's
axis to all four silently shifts every number — an error I made on my own first pass and corrected.

### 3.4 🛑 The neighbour trap — worse than a near-twin

The mode 10/11/12 records are interleaved at stride `0x14`, and the neighbours are not merely
similar:

| record | mode 10 (ours) | mode 11 | mode 12 |
|---|---|---|---|
| **0 km/h** Y | `[3072, 3072, 2322, 1536]` @`0xD2A74` | **IDENTICAL** @`0xD2A88` | **IDENTICAL** @`0xD2A9C` |
| **10 km/h** Y | `[2561, 2561, 2247, 1947]` @`0xD2AB0` | `[2560, 2560, 2246, 1946]` @`0xD2AC4` | same @`0xD2AD8` |

**Mode 11 and 12's 0 km/h records are BYTE-IDENTICAL to mode 10's**, and their 10 km/h records sit
one count below. So the byte pattern this edit targets occurs **three times within 40 bytes**.
🛑 **Address every cell by absolute address. Never search for a byte pattern.** A pattern-based
edit would silently rewrite another car variant's calibration, and `diff_build_vs_stock.py` — being
span-based — would attribute it without complaint. **Assert the mode-11 and mode-12 records
byte-unchanged in both the builder and the verifier.**

---

## 4. WHAT IT DOES

### 4.1 Multiplier vs speed (low rate axis)

| km/h | 0 | 5 | 7.2 | 10 | 15 | 20 | 25 | 30 | 40 | **50** | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **V69 / stock** | 2.000 | 2.000 | 2.000 | **2.000** | 1.886 | 1.769 | 1.649 | 1.526 | 1.270 | **1.000** | **1.000** |

Flat 2× to 10 km/h, linear taper, **exactly 1.000× at and above 50 km/h — byte-identical to stock at
highway, in BOTH arms.** That is the fix.

★ **AND THE HIGHWAY 1.000× IS STRUCTURAL, NOT TUNED.** The lane-change point is 93.35 km/h = 5980
counts, which lies in the cross-axis `[3200, 6400]` segment — so the interpolation there reads
**only rec2 and rec3**. **Any edit confined to rec0 and rec1 is exactly 1.000× at every speed
≥ 50 km/h, at every rate, on every axis scale.** It cannot drift with a re-tune or a re-derived
scale; it is a property of which records the interpolation touches.

### 4.1b ★ SCALE-INVARIANCE — this design does not bet on an open question

🛑 The inner axis's counts-per-deg/s is **[OPEN]**: the repo runs 4.7121 (scale A), but the same
derivation chain has one wrong premise and the arithmetically-surviving alternative is 0.58901
(scale B). Every rate-axis figure in this kit is conditional on that.

**V69 doubles the whole flat `[0, 400]` segment rather than leaning on where a breakpoint falls**,
so its creep dose is **2.000× on BOTH scales**. Design A swings **2.00× (A) → 1.22× (B)** at grind
#1 — it is a bet on scale A.

⚠ **The price, stated honestly: the same property makes the manual-creep cost scale-dependent.**
grind #1 and manual creep share the same speed cells, so only the rate axis could separate them —
and on scale B they are both deep inside the flat segment and **nothing** separates them:

| | scale A (repo live) | scale B (chain-direct) |
|---|---|---|
| grind #1 region (2–5 mph × 16–128 deg/s) | min 1.75, median **2.00** | min 1.90, median **2.00** |
| creep grind #2 | **1.27×** | **2.00×** |
| manual creep | median 1.27, max 1.75 | median **2.00** |
| highway | **1.000×** | **1.000×** |

⇒ **Worst case (scale B), manual creep and creep grind #2 both sit at 2.00× — exactly the dose
V62/V65 flew.** That is bounded and known rather than speculative: the operator drove V62/V65 for
weeks. But if creep grind #2 returns, **this is the mechanism**, and P6 is the test.

### 4.2 The four operating points

| point | stock | V68 engaged | **V69** |
|---|---|---|---|
| grind #1 (7.2 km/h, \|dtq\| 603) | 1.000 | 2.001 | **1.835** |
| creep grind #2 (5.0 km/h, \|dtq\| 1206) | 1.000 | 2.185 | **1.267** |
| **highway lane change (93 km/h, \|dtq\| 164)** | 1.000 | **2.414** | **1.000** |
| manual creep | 1.000 | 1.000 | **1.835** ← the cost |

### 4.3 Why not "Design A" (`0xD2ABC` alone, 2561 → 7051)

**REJECTED, on its own hump.** Raising Y[1] alone makes a triangular spike `2561 → 7051 → 2247`
peaking exactly on the `X[1] = 400` breakpoint:

| | max multiplier | where | rate-axis slope | 2f depth | % of real driving > 2.00× |
|---|---|---|---|---|---|
| stock | 1.000 | — | 0.750 | 1.032 | — |
| **Design A** | **2.753** | 10 km/h, \|dtq\| 400 | **11.300** | **2.753** | **1.98%** |
| **V69** | **2.000** | ≤10 km/h | 3.850 | 1.122 | **0.00%** |

The record understates the hump as "~2.45×" — that is its value at grind #1's 128 deg/s only. The
true maximum is **2.753× at 10.0 km/h / 86 deg/s**, and it exceeds 2.5× across **9–16 km/h**, a band
cars drive through constantly. Reproduced independently, twice.

⭐ **AND A SECOND, INDEPENDENT REASON TO REJECT IT — Design A is sized for the wrong rate band.**
Its boost is a **ramp that only starts at the axis-400 breakpoint**, but V62's measured fix was
**largest at |rate| 16–32 deg/s** (42× suppression). Design A delivers only **1.1–1.5×** there:

| deg/s | 3.2 km/h | 5.0 | 7.2 | 10.0 | 14.4 |
|---|---|---|---|---|---|
| **16** | 1.09 | 1.15 | 1.22 | 1.33 | 1.30 |
| **32** | 1.18 | 1.30 | 1.45 | 1.66 | 1.59 |
| 128 | 1.41 | 1.67 | **2.00** | 2.46 | 2.31 |

**V69 delivers exactly 2.000× across that whole band** (16–32 deg/s sits inside the flat `[0, 400]`
segment on *either* scale), because it lifts the segment uniformly instead of tilting it. Region
scores: **V69 min 1.75 / median 2.00** vs **Design A min 1.09 / median 1.45** on scale A, and
**1.90 / 2.00** vs **1.01 / 1.05** on scale B.

⚠ 🛑 **CORRECTION TO MY OWN EARLIER REACHABILITY FIGURE.** I first reported "Design A exceeds 2.00×
in 1.99% of 318k frames" using a **torsion-bar torque rate** reconstructed from the `tq` channel.
**That is the wrong quantity for this axis** — the inner axis is a steering/motor *rate*, not a
torque rate. The *surface* properties above (max 2.753×, the region tables, the operating points)
are computed on the axis in its own counts and are unaffected; **the percentage-of-driving figure is
withdrawn.** The rejection does not depend on it: the hump's magnitude and the wrong-rate-band
argument each suffice on their own.

### 4.4 The Pareto front, and what was given up

Grid search over (rec0 Y[0..1] scale, rec1 Y[0..1] scale, shared Y[2] scale):
**≥ 1.90× at grind #1 and ≤ 1.35× at creep grind #2 are JOINTLY INFEASIBLE** with max ≤ 2.00× and
highway exactly 1.000×, because both points sit on the same linear segment between X[1]=400 and
X[2]=1500 and **the breakpoints cannot move** (§5.2). Relaxing to ≥ 1.80× leaves two:

| f0 | f1 | f2 | grind #1 | creep #2 | max | slope | 2f | halfwords |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 2.0 | 1.1 | 1.851 | 1.340 | 2.000 | 3.600 | 1.113 | 6 |
| **2.0** | **2.0** | **1.0** | **1.835** | **1.267** | **2.000** | 3.850 | 1.122 | **4** |

**Chosen: the second** — fewer halfwords, each an exact doubling, and more margin on creep grind #2,
which is the symptom currently at zero and the one V62's ungated 2× demonstrably reawakened.
⚠ **Cost: grind #1's dose falls 2.00× → 1.835×.** On the recorded dose–response (Kd = 1.00 → 1.00
ref; Kd = 2.00 → 0.39; V67 gated → 0.40 [0.27, 0.58]; null [0.88, 1.13]) that should still land near
0.42–0.45, far outside the null — but it **spends margin**, and if grind #1 returns, this is why.

---

## 5. THE TWO GATES

### 5.1 GATE 1 — RAM ownership: **VACUOUS**
No cave growth, no new instruction, no new RAM cell. Edits 1, 2, 7 are in-place byte changes to
existing instructions/cals; 3–6 are ROM table constants. Nothing is claimed.

### 5.2 GATE 2 — closed-loop stability: magnitude AND phase

**PHASE: unchanged everywhere.** V69 edits no filter, no pole, no delay, no `sar`. The finite-
difference delay cal `0xC6C42` stays 4. A pure gain change contributes no phase.
🛑 The record already closed the filter route: a differentiator (+20 dB/dec) against one real pole
(−20 dB/dec) is flat above the corner, and two poles low enough to bite by 42 Hz cost −92° at
20.9 Hz and destroy the damping. **Do not re-propose. Raising `0xC6C42` fails identically.**

**MAGNITUDE: bracketed by two flown-stable configurations, with zero exceedance.**
Stock = 1.000× is the shipped configuration; V62/V65 flew a flat **2.000×** and were flight-clean
(`ST == 4` = 0). V69's maximum is **exactly 2.000×**, reached only at ≤10 km/h, and over 318,144
frames of real driving it exceeds 2.00× in **0.00%** of samples. **The bracket holds unconditionally.**

**Parametric pump (the criterion `v68_design_math.py` pre-commits to).** `gp-0x6ac0` is *rectified*,
so the rate axis sweeps at 2× the mode frequency; the pump cares about gain modulation depth over a
half-cycle. Stock **1.032**, V69 **1.122**, Design A **2.753**. V69 sits ~9% above stock.

**Saturation margin** — r24 clamps at `|dtorque| ≥ 8192·1024/gain`; measured max `|dtorque|` = 839:

🛑 **Corrected from my first draft, which quoted the gain at grind #1's point rather than the
design's PEAK gain — the peak is what sets the margin.**

| | **peak** gain | saturates at \|dtorque\| | margin vs 839 |
|---|---|---|---|
| stock | 3072 | 2731 | 3.25× |
| V67/V68 arm | 5244 | 1599 | **1.91×** |
| **V69** | **6144** | **1366** | **1.63×** |
| Design A | 7051 | 1191 | 1.42× |

⚠ **V69's saturation margin is 1.63×, WORSE than the 1.91× on the car today** (better than Design
A's 1.42×). Quoted against the repo's recorded max `|dtorque|` of **839**; against the 511 measured
directly on the two V68 routes it is 2.67×, and the 28 Hz burst itself is only **254** counts.
🛑 Every `|dtorque|` figure in this kit is a **LOWER BOUND** — CAN's 50 Hz Nyquist hides content
whose contribution to the real `gp-0x4f62` is *rising* through that band. **This is the one metric
on which V69 is worse than V68, and it is disclosed rather than buried.**

**⚠ One accepted discontinuity, stated because it is real.** `rateKey` folds to 0 at ≥ 13001 counts
(`0x3AAC8`/`0x3AACC`), i.e. **2759 deg/s** — fault-level, not reachable in ordinary driving. Raising
Y[0] enlarges the step across that fold: at 0 km/h stock steps 1536 → 3072 (**2.00×**), V69 steps
1536 → 6144 (**4.00×**); at 10 km/h 1.32× → 2.63×. Bounded, unreachable, and recorded rather than
hidden.

**Blast radius.** rec0 and rec1 are reached by **exactly one pointer each** (`0xCBF84`, `0xCC06C`),
both mode-10 slots ⇒ **the edit touches one car variant.** Their interpolated output lands in
`gp-0x6e40`/`gp-0x6e38`, read at only four addresses, **all inside `FUN_0003aa2c`** — zero other
consumers, by a three-method scan (disp16, disp23 extended form, LE32 literal).
✅ **NO FLOAT MIRROR.** Four encodings × every rec0/rec1 X and Y value, unaligned over all 1,048,576
bytes: **zero hits on any Y value.** The clinching argument is that a mirror must carry *all* the
values, and 2561 / 2247 / 1947 / 2322 / 1400 / 3000 are absent in every encoding. The known
precedent `FUN_00043e44` is the float twin of a *different* table and contains zero literals for
these records. ⇒ **the V22/V27 int–float desync class does not bind V69.**
🛑 **This is why V69 edits Y values ONLY and never an X breakpoint** — X = 400 and X = 1500 *do*
have single f32 hits (`0xC661C`, `0x55B5A`), so moving a breakpoint would reopen the question.

**Safety anchors, re-verified across stock and all 11 archived images:** role table `0xC4124` =
`[0,0,5,0,5,5,0,0,0,5,0]` — **no slot ever 6 or 7**, so `gp-0x67ac` stays 0 and the rate lanes cannot
silently drop out; `0xC6564` = **40 zero bytes**, so r26 is structurally inert and r24 carries the
whole lane.

---

## 6. THE COST, AND THAT IT WAS THE OPERATOR'S CALL

Reverting the gate makes the shaped surface apply in **both** arms. Manual steering below ~50 km/h
gains the rate damping that today applies only when LKAS is engaged; **manual highway is
byte-identical to stock.** Over the pooled 318k frames, **50.7%** of samples see > 1.5× (that set is
creep-heavy and over-represents low speed). This is close to what V62/V65 already delivered and the
operator drove for weeks. **He was shown this trade explicitly, with the cave alternative priced,
and chose it.**

---

## 7. PROBE — build identity for **two in-place immediate bytes**

V68 and V69 would otherwise emit **identical payloads** and be indistinguishable from a log: bit6
reads `gp-0x6806` in the *cave*, independent of the control-path gate at `0x3AA94`. That is
unacceptable — V68 is what is on the car, so V68-vs-V69 is exactly the confusion that matters.

**Edit 7 — the structural half.** V68's bit3 is **not derived from any signal**: it is baked into the
liveness `movea 0x88,r0,r7`'s immediate. V69 emits `movea 0x80` instead — **one byte at `0xC4B36`,
the same instruction, no new bytes.** V68 therefore sets bit3 in *every* frame and V69 clears it in
*every* frame. **The two payload sets are structurally disjoint; no measurement can make them
overlap.**

**Edit 8 — the practical half, because bit3 alone is not enough.** ⚠ **V67 already emits
`movea 0x80`** (verified: `0xC4B34` = `20 3e 80 00` on V67), so Tier 0 alone makes V69's payload set
*identical to V66/V67's*. Edit 8 changes `cmp 0x1,r6` → `cmp 0x0,r6` at `0xC4B54`: `ld.bu`
zero-extends, so `r6 ∈ [0,255]` and a signed `blt` against 0 is **never** taken ⇒ **bit4 is set in
every frame.**

| bit | V69 |
|---|---|
| 7 | liveness |
| 6 | `gp-0x6806 != 0` — the LKAS gate (still a useful arm split for analysis) |
| 5 | `gp-0x67df != 0` — the 1 kHz detector's crossing stage. **Kept: now proven live** (§8) |
| **4** | **constant 1** |
| **3** | **constant 0** |

**Legal payload sets, and the decision rule:**

| build | byte4 set |
|---|---|
| V66 / V67 | `{0x87, 0x97, 0xA7, 0xB7, 0xC7, 0xD7, 0xE7, 0xF7}` — in practice only `0x87`/`0xC7` |
| V68 | `{0x8F, 0x9F, 0xAF, 0xBF, 0xCF, 0xDF, 0xEF, 0xFF}` (bit3 = 1 always) |
| **V69** | **`{0x97, 0xB7, 0xD7, 0xF7}`** (bit3 = 0, bit4 = 1) |

⇒ *"bit3 clear in every frame"* excludes V68 **structurally**. *"bit4 set in every frame"* excludes
V66/V67 **practically** — their bit4 (`gp-0x671a ≥ 5`) read **0 in 186,321 frames**. A 5-bit field
cannot make three classes structurally disjoint; this is the best available and its limit is stated.
Burning bit4 costs nothing: it is redundant with bit5 (a reversal implies a crossing) and has never
fired in any build.

### 7.1 ⚠ The `gp-0x6c2c` ladder — designed and costed, DEFERRED TO V70

`gp-0x6c2c`'s *production* (`FUN_00041464`) contains **zero calls to `FUN_00046EA6`** — confirmed
from its decompile, not merely cited — so it bypasses the detector's DTC gate entirely, and reading
it directly also sidesteps the `T` = 12800 / `CEIL` = 5 quantisation. It would give this kit the
**positive control the FSM flags have never once provided**.

It has been fully designed and it *fits*: a 2-rung monotone ladder at T/4 = 3200 and T/2 = 6400,
sharing one absolute-value prefix (`ld.h` / `cmp r0,r6` / `bge +4` / `subr r0,r6`) and subtracting
the **incremental** 3200 in place, so both rungs are the byte-identical `movea -0xc80,r6,r6`.
Cost **58 B** against the proven 68 B extent — *smaller than V68's 60 B* — staying within the
r6/r7-only, exactly-one-store discipline every flown cave has met. A 3rd rung at T/8 needs 46 B
against a 44 B ceiling: **2 bytes over.**

🛑 **Not taken for V69, and the reason is the standing rule, not the byte count.** *"Every success
since V29 has been cal-only or a single in-place branch/displacement edit."* Edits 1–8 are all in
that class. The ladder **rewrites ~34 bytes of cave body** with instructions (`subr`, `bge`, signed
`ld.h`, negative-immediate `movea`) that this cave has never carried — and code caves are this kit's
**only bricking class** (V24, V27, V48B). V69's job is the fix; **P1 needs no probe at all.** Fly
V69, learn whether P1 held, then spend risk on the instrument in V70.
⚠ Two caveats to carry forward: the hook fires at **100 Hz (task 5)** while `gp-0x6c2c` refreshes at
1 kHz, so the ladder is a **decimated snapshot, not a peak-hold** — it can show "≥ threshold at this
sample", never "never crossed between samples". And the proposed bytes are **hand-derived**,
cross-validated against three real reference points but **not yet run through the kit's own encoder
and self-check pipeline**, which must be the final gate.

---

## 8. WHAT V69 INHERITS AS SETTLED

**Honda's 1 kHz detector is LIVE — V68's zero is a QUIET BAND, not a dead instrument.** Verified this
session: the entry gate at `0x428D8`–`0x428E2` (`mov 0x5,r6` / `jarl FUN_00046ea6` / `cmp r0,r10` /
`be 0x428E6` / `jr 0x42A76`) runs the body when the active-DTC mask bit is **clear**; the flights
were fault-clean. `gp-0x67df` has exactly 2 firmware accesses (read `0x428E6`, write `0x4299C`) plus
our cave read; zero extended-form hits, zero address literals. The input `gp-0x4f50` has one writer
fed from the live resolver chain, refreshed every task-1 tick. Every detector cal is live and sane
(T = 12800, CEIL = 5, dwell = 50, release = 5000, K1 = 37, K2 = 22).
⚠ **Residual:** the exact DTC↔bit5 mapping is not pinned, so "mask was clear" rests on flight-clean
telemetry rather than exhaustive proof.
★ **And it corroborates the lever from an unexpected direction:** the 28 Hz event ran 1468 counts p-p
on the *torsion bar* yet never tripped a detector watching *resolver-derived motor rate*. The mode
lives on the bar/column side — exactly the channel `gp-0x4f62` differentiates and r24 amplifies.

---

## 9. PRE-REGISTERED PREDICTIONS — written before the build exists

| | prediction |
|---|---|
| **P1** | engaged-highway maneuver **26–30 Hz falls ~3.3× [1.33, 6.78]** toward the Kd = 1 level |
| **P2** | engaged-creep 18–22 Hz (grind #1) stays fixed, **~0.42–0.45** vs the Kd = 1 pool (null [0.88, 1.13]) — slightly weaker than V68's 0.40 |
| **P3** *(negative control)* | 40–49 Hz at highway **does not move** (1.36 [0.95, 1.79] — no dose response) |
| **P4** *(negative control)* | 1–4 Hz driver band **does not move** |
| **P5** | `ST == 4` stays 0; the zero-EME streak continues |
| **P6** *(new)* | creep grind #2 stays at **zero bursts** in both arms — V69 runs 1.267× where V62's 6-burst manual arm ran ~2× |

**P3 and P4 are what catch me being wrong**: if they move, the edit did something other than intended.
**No scripted drive is needed** — route `4e` yielded 18 maneuver windows in ~4 min at speed, so an
ordinary 20–30 min engaged highway commute gives ~5–7× that, enough to test P1.

---

## 10. BUILD REQUIREMENTS (for `build_v69_tva.py`)

1. **Three CRC blocks.** `build_v68_tva.py` recomputes only `sorted({MAIN, CAL})` **and asserts the
   CAL CRC did not move** — that assert fires on edit 2. Use **`build_v60_tva.py:202-216`'s generic
   template**, which calls `V53.owning_block(code, addr)` and recomputes the union.
2. **Relax** `build_v68_tva.py:1378-1381` (`for rec in GAIN_B_RECORDS` byte-identity) and
   `V66.assert_gain_b_surface(...)` at line 1398 — they assert the surface is stock.
3. **Keep** `D2000_BLOCK = (0xD2000, 0xD2010)`'s identity assertion: it is the machine proof that
   V60's falsified cells stay put, and it is untouched by this edit.
4. **Assert the neighbours**: mode-11 (`0xD2AC4`…) and mode-12 records byte-unchanged (§3.4).
5. **Ship `verify_v69_image.py` with EXACT-VALUE anchors.** 🛑 `diff_build_vs_stock.py` is
   **span-based, not value-based** — a wrong value inside an existing `EDITS` span is silently
   attributed and the gate passes. Anchor every one of the 7 bytes, plus `0xC4124` **and `0xC6564`**
   (which `verify_v68_image.py` does *not* check).
6. **Add `EDITS` rows** for `0xD2A7E-0xD2A81`, `0xD2ABA-0xD2ABD`, `0x3AA96`, `0xC4B36`, `0xC4B54`, and change
   the `0xC6446` row to 512.
7. **Re-read `0xC4124` every build and STOP if any slot carries 6 or 7** (inherited from V68).
8. 🛑🛑 **ASSERT THE EDIT-ORDER INVARIANT — this one can make the car worse than stock.**
   Edits 1 and 2 are **jointly** safe and **individually** dangerous in one direction: writing
   `0xC6446 = 512` while the gate at `0x3AA96` stays repointed to `gp-0x6806` leaves the arm LIVE at
   **512, which is ~5× BELOW the stock LERP**, degrading engaged steering everywhere. The builder
   must assert **`0xC6446 == 512` ⟹ `0x3AA96 == 0xc5`** and refuse to emit otherwise.
   (Reverting the gate alone is harmless: nothing then reaches `0xC6446`.)
9. Verify with a fresh Ghidra import — 🛑 a stale import defeats hash-checking.

---

## 11. DOCUMENTATION DRIFT FOUND WHILE SPECCING THIS — fix before the next session

1. 🛑 **The tracer memory's record→speed rotation** (§3.2). Highest priority; it would invert a design.
2. 🛑 **`docs/BUILD-LINEAGE.md` line 38**: "`0xC644A` … V43 … 1024→64" is **wrong**. **V43 shipped 32**
   (`build_v43_tva.py:195 POLE_NEW = 32`, confirmed in `_v43_plain_image.bin`); **64 was V49**, and
   the −7.1 dB figure belongs to V49.
3. ⚠ **`memory/accord-r24-gain-b-four-pointer-arrays.md`**: "the 10 km/h record uses 1400" — **1400 is
   rec0, the 0 km/h record**; rec1 (10 km/h) uses 1500.

---

## 12. OPEN / NOT CLOSED

- **BELIEF: "mode = 10 on this car."** `gp+0x63fd` is RAM with 6 runtime writers, not statically
  readable. The PN-key chain plus V55's on-car damper-variant bit (same cell, `0x34502`) corroborate
  transitively — strong, but not a fresh measurement. **Every number here is mode-10-specific.**
- **`gp-0x4f50`'s physical units — [OPEN]**, deliberately. Do not close by borrowing `gp-0x6ac0`'s
  4.7121 counts/deg-s; composing those chains produced the retracted "bus = 8 × deg/s".
- **The DTC↔bit5 mapping** behind the detector gate (§8).
- **r26's inertness** rests on a zero cal base plus no writer found across 10 of 18 cells.
- **The mechanism itself** (§1) — P1 is the test.
