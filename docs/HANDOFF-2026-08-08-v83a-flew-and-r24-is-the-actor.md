# HANDOFF 2026-08-08 — V83a flew (route 68), and r24 is the grind-#1 actor

**Read `docs/STATE.md` first.** Predecessor:
`HANDOFF-2026-08-08-v81-flew-and-the-aggregator-reaches-the-motor.md`.

---

## ★★★★★ THE HEADLINE

**V83a flew as route 68. It is the worst modern build on both scored symptoms, its own pre-registered
falsifier fired, and the session's durable result is structural rather than a flight number:**

1. 🛑 **V83a is measurably WORSE than V81 on both scored symptoms** — 18–22 Hz grind #1
   **2.674× [1.956, 3.885]** against a split-half null of [0.63, 1.55], 6–9 Hz micro-ratchet **1.526×**.
2. 🛑 **V83a's OWN pre-registered falsifier fired.** Prediction 1 said *"if the ring is not below V76's,
   the dose model is wrong and the damper is not what drives it."* The 26–31 Hz ring came back
   **1.021 — FLAT** against V81. **The damper-dose model of the ring is dead, by V83a's own rule.**
3. ★★★★★ **r24, NOT r26, IS THE GRIND-#1 ACTOR.** Re-scoring the whole rate-lane corpus with the
   mode-10 builds correctly excluded resolves the tension the kit had carried as *"CARRY THIS
   UNEXPLAINED"* for weeks: **neither r26 direction helped.** r24 is monotone 0× → 1× → 2×; r26 swings
   **11.3× at fixed r24 and grind #1 barely moves.**
4. ★★★★ **"No progress since V38" is a BYTE FACT, not an impression.** V83A is byte-identical to V38 at
   **every** grind/ratchet-relevant site. Three sites differ in the whole lineage, and none of them is a
   grind lever.
5. **V84 is BUILT, VERIFIED, UNFLASHED** — Lever B restored, the engaged-only Coulomb damper deleted,
   and a probe repointed onto the lane that actually matters.

---

## 1. THE OPERATOR'S FRAMING — this is what started the session

> **"Feels just like V38, like we have made no progress since then."**

Four symptoms, **all LKAS-engaged-only**:

| # | symptom | regime |
|---|---|---|
| **S1** | **grind #1** | 4–5 mph, steering angle ≈ 0 |
| **S2** | **micro-ratcheting** | all speeds, whenever the wheel moves under command |
| **S3** | **macro ratcheting** | ≤ 30 mph under strong command |
| **S4** | **excess friction** | under max command |

And the constraint, verbatim, which is a design gate for every lever proposed from here:

> 🛑 **"I just want ratchet gone without limiting the max steering angle rate under strong LKAS
> command."**

---

## 2. ★★★★ THE BYTE FACT THAT VINDICATED IT

**V83A is byte-identical to V38 at every grind/ratchet-relevant site**, read out of both plain images:

| site | V38 | V83A | |
|---|---|---|---|
| `0x3AB76` / `0x3AC20` (V62's `sar` pair) | `AA` / `AA` | `AA` / `AA` | **same** |
| `0x3AA96` (the r24/r26 gate byte) | `C5` | `C5` | **same** |
| `0xC6446` (r24 engaged arm) | 512 | 512 | **same** |
| `0xC6444` (r26 engaged arm) | 512 | 512 | **same** |
| `gain_A` rec0/1/2/3 | stock | stock | **same** |
| `FactorE` m26 | Honda's | Honda's | **same** |
| `0xC63A0` | 1024 | 1024 | **same** |
| `0xC63AC` | 102 | 102 | **same** |
| `0xC407E` | 511 | 511 | **same** |
| `0xC61B2` / `0xC61B4` | 2048 | 2048 | **same** |
| `0xC64C8` | 0 | 0 | **same** |

**Only THREE sites differ at all across V38 → V83A**, and not one is a grind lever:

| site | V38 | V83A | |
|---|---|---|---|
| `0x454FE` | `0xBA` (stock) | `0xB5` | V42's macro-ratchet fix — the V84 lineage HAS it, V38 did not |
| `0xC62EA` | 320 | **0** | the low-speed steer lockout, removed |
| the 4× LKAS route | **shared** `0xC646C` = 3564 | V57's **private** `0xC6CD0` = 3564 (`0xC646C` stock 891) | same delivered 4×, different blast radius |

⇒ **The operator was reporting a byte fact.** Between V38 and V83A the car has been through 45 build
numbers and arrived at the same assist surface, with the low-speed lockout removed and one macro-ratchet
byte restored. Every grind-#1 lever the kit has ever measured was **off the car** on route 68.

---

## 3. ROUTE 68 — identification, then results

### 3a. Identification, from each image's own bytes, with NO free parameters
The build on route 68 was established by a **probe thermometer prediction**: for each candidate image,
the cave's rungs were evaluated against the surface that image would deliver, and the *predicted duty*
compared to the *observed duty*. No fitted parameter enters.

| | bit6 duty | bit5 duty |
|---|---|---|
| predicted **if V81** | **32.19%** | **14.60%** |
| predicted **if V83a** | **0.515%** | **0.000%** |
| **observed on route 68** | **0.508%** | **0.000%** |

**V83a, by three orders of magnitude on bit6 and unambiguously on bit5.** [EVIDENCE]
⊕ The same code, run against route 67, identifies **V81** correctly — a positive control on the method
itself, not just on this route.

### 3b. Flight health
**Fault-free.** No terminal fault, no DTC transition.

### 3c. The scored result — cell-stratified against V81

| band | V83a / V81 | split-half null | verdict |
|---|---|---|---|
| **18–22 Hz — grind #1** | **2.674 [1.956, 3.885]** | [0.63, 1.55] | 🛑 **WORSE, well outside the null** |
| **6–9 Hz — micro-ratchet** | **1.526** | — | worse |
| **26–31 Hz — the ring** | **1.021** | — | **FLAT** |

### 3d. 🛑 V83a's pre-registered falsifier fired
V83a's prediction 1, fixed before the flight, read:

> *"**26–31 Hz ring below V76's.** V83a's dose at the ring's operating point is 96 = 0.42× V76 … **If the
> ring is not below V76's, the dose model is wrong and the damper is not what drives it.**"*

The ring is **1.021 against V81**, i.e. unmoved by a 0.42×-of-V76 damper dose. **The falsifier fired.**
⇒ **The damper-dose model of the 26–31 Hz ring is falsified by the build's own rule.** This is the
pre-registration doing exactly its job, and it is why V84 spends no cell on the ring.

⊕ Scoring the other pre-registered predictions honestly: **#4 ("6–9 Hz slightly worse") was
directionally RIGHT** (1.526); **#5 ("18–22 Hz roughly unchanged") was WRONG** and badly so (2.674).
Predictions 2 (in-ring `MOTOR_TORQUE`) and 3 (impedance asymmetry above ~60 km/h) are not carried into
this handoff.

---

## 4. ★★★★★ THE DOSE TABLE — r24 is the actor, and this is the whole argument

Delivered dose at grind #1's operating point (7 km/h, 128 °/s, engaged), computed from each image's own
bytes at **mode 26**, with the mode-10 builds **correctly excluded**:

| build | r26 × | **r24 ×** | grind #1 median `e_18-22` |
|---|---|---|---|
| V61 | 0.000 | **0.000** | **2501** |
| stock / V69 / V70 | 1.000 | **1.000** | 879 / 746 / 729 |
| V72 | 0.177 | **1.000** | **unmoved** (0.953) |
| V62 / V65 | 2.000 | **2.000** | **168** |
| **V67 / V68** | 0.177 | **1.994** | **109** |

**Read it two ways and it says the same thing:**
- **r24 is monotone** across 0× → 1× → 2×: 2501 → 879 → 168/109.
- **r26 swings 11.3× at fixed r24** (V72's 0.177 vs stock's 1.000) and grind #1 **does not move**
  (0.953). And the two builds that fixed grind #1 sit at **opposite ends** of r26 (2.000 and 0.177) with
  the **same** r24 (≈2×).

### What this table KILLS

🛑 **1. The "r26 helped in BOTH directions" tension is RESOLVED — neither direction helped.**
The golden model carried this as *"⚠⚠ CARRY THIS UNEXPLAINED, DO NOT SMOOTH IT: r26 ×2 (V62/V65) AND
r26 ÷6.00 (V67/V68) BOTH HELPED."* The premise was wrong. What both of those builds share is **r24 at
≈2×**; r26 is the confound, not the cause. The golden model is corrected (§10a).

🛑 **2. The still-circulating "r24 is near-inert across a 4:1 dose range" claim is VOID.**
Its entire basis was the series **stock → V70 → V69** reading 879 → 729 → 746 with "r24 stepped
1× → 2× → 4×". **V69 and V70 wrote mode-10 `gain_B` on a mode-24/26 car** — they were **functionally
byte-stock**. So were V72's and V73's r24 edits. **The "4:1 dose range" was three byte-stock builds and
their mutually-overlapping CIs are exactly what byte-stock predicts.** [EVIDENCE — RULE 7]

⇒ Every conclusion that rested on "r24 is inert" must be re-priced. In particular, the corollary
**"grind #1 is BLIND to r24 gain, so it cannot be used as an in-force check"** is retracted along with
its premise.

---

## 5. 🛑 WHY THE LINEAGE WENT WRONG — three lessons, stated as lessons

**(a) Mode-10/11 edits on a mode-24/26 car made whole FAMILIES of builds inert.**
V44, V47, V69, V70, V72's entire r24 dose, V72's Levers B/C and both of V73's levers were **INERT BY
TABLE SELECTION** — they look flashed, verified and driven, and they were never read. This is RULE 7,
and its cost is not one build: it is a *dose axis* the kit reasoned from for eight builds.

**(b) The rate lanes are the mode's ONLY damping fast enough to act on a 20 Hz mode.**
The table damper `FUN_00034350` runs in **task 5 = 100 Hz**; the aggregator `FUN_0003aa2c` and the
residual lane `FUN_0003a382` run in **task 1 = 1 kHz**. A zero-order hold at 100 Hz costs 37.6° average
/ 75.2° worst-case phase at 20.9 Hz **before any plant phase**, and the ZOH crossover is **25 Hz** —
above which the 100 Hz damper can be sampled into an **anti-damping** force. ⇒ **r24/r26 are the only
damping in this firmware with the bandwidth to act on grind #1**, and **every** build that "cut the
derivative lane to stop the noise" (V39, V42, V56, V61, V72) pushed the one stabilising term **the wrong
way**. V61 — both lanes dead — is the worst grind #1 in the corpus at **2501**. That is the mechanism
behind the dose table, not a coincidence in it.

**(c) FIVE levers were silently reverted across the V38 rebase.**
`0x454FE` (V42's macro-ratchet fix), V62's `sar` pair, V67/V68's gate + arm, the V57 decouple, and —
**newly identified this session and never logged before** — **`gain_A` rec0/rec1**. Nobody decided any
of them. The kit's own record repeatedly reasoned from results produced by bytes that were no longer on
the car. ⇒ **RULE 3 exists for this and was still not enough**: the only reliable check is a
**value-anchored byte read of the CURRENT image**, per lever, before any reasoning from a recorded
result.

---

## 6. ✅ V84 — BUILT, VERIFIED, UNFLASHED

### 6a. The one-line design

> **RAISE THE DC-NEUTRAL DAMPING AND DELETE THE DC-OPPOSING DAMPING.**

- **Raise** the rate lane (r24), engaged-only via the `lp` gate. r24 is a **pure derivative** — at
  constant torque it contributes **nothing**, so raising it damps oscillation at **zero steady-state
  impedance cost**. That is the operator's constraint answered verbatim: neither lever touches the
  command path or any rate limit.
- **Delete** the mode-26/27 Coulomb damper. It is `−sign(motor rate) × M(|rate|)` — it opposes at
  *every* rate including a sustained slew, it fights the **driver** even turning WITH the command, **it
  is OURS** (Honda ships modes 24 ≡ 26 byte-identical across all six factor families), and it was first
  armed at **V74**.

### 6b. The edit set — 7 cells, one instruction byte and six calibration halfwords

| # | cell | addr | V83a | V84 | equals |
|---|---|---|---|---|---|
| 1 | r24/r26 gate repoint | `0x3AA96` | `C5` | `FB` | the FLOWN V67 **and** V68 |
| 2 | r24 engaged arm | `0xC6446` | 512 | **5244** | the FLOWN V67 **and** V68 |
| 3 | FactorC mode-26 `Y[0]` | `0xD77DA` | 566 | **0** | STOCK |
| 4 | FactorC mode-27 `Y[0]` | `0xD77EE` | 566 | **0** | STOCK |
| 5 | FactorE mode-27 `X[0]` | `0xD7822` | 12 | **60** | STOCK |
| 6 | FactorE mode-27 `X[1]` | `0xD7824` | 200 | **400** | STOCK |
| 7 | FactorE mode-27 `Y[1]` | `0xD782C` | 539 | **140** | STOCK |

**Every edit is asserted equal to something that has already been on this car.** 7 cells / 13 bytes
written / **12 bytes differ**.

🛑 **Mode 27 was NOT optional.** Row 11 `TVCA4` resolves to modes **[24, 25, 26, 27]** and mode 27 is a
genuinely separate engaged mode. V83a reverted mode 26 and left **mode 27 carrying V75's entire damper**
— a 297-count plateau, relay index `N(50)/N(500)` = **1.45** where Honda's is **0.00**. After V84 both
engaged modes read Honda's viscous surface.
⚠ **Honda's pairing is 24↔26 and 25↔27**, not "everything to 24" — stock FactorC m25/m27 is
`[0, 233, 426, 875]` while m24/m26 is `[0, 234, 429, 908]`. A gate holding mode 27 to mode 24 would fail
on Honda's own firmware.

### 6c. ★ The `lp` gate, stated exactly — one register, one writer, two opposite effects

`0x3AA96` repoints a single `ld.bu` from the **dead** cell `gp-0x683c` (1 reader — itself — 0 writers) to
`gp-0x6806`, the LKAS-active flag (99.899% / 99.943% agreement with `carControl.latActive` over 37,914
frames on V57's flown probe). The result is **one register**, `lp`, with **exactly one writer**:
`setfne lp` @`0x3AAA8`, and the first `jarl` is @`0x3ACDC` — **after both consumers**, so `lp` cannot be
clobbered.

🛑 **That one byte therefore gates BOTH lanes, in OPPOSITE directions:**

```
lp != 0  ->  r24 takes 0xC6446 = 5244   (RAISE, 1.766x at 2 km/h ... 2.000x at grind #1 ... 2.592x at 100 km/h)
lp != 0  ->  r26 takes 0xC6444 =  512   (CUT,   0.167-0.200x of Honda's gain_A LERP)
lp == 0  ->  both lanes take Honda's LERPs  =>  MANUAL IS BYTE-FOR-BYTE STOCK
```

🛑 **AND THE ARMS *REPLACE* THE LERP — THEY DO NOT SCALE IT.** This is the difference from V72 and it is
declared, not discovered later: **V84's engaged r26 cut holds at ~0.19× even at ≥ 50 km/h**, where
V72's `gain_A` cut **relaxes to exactly 1.000×** there. Below 10 km/h the two are *identical* — V84's
flat 512 equals V72's LERP point for point, which is the numerical basis of the S3 prediction. Above
10 km/h **V84 cuts deeper**. Not unflown: V67 and V68 carried this exact configuration at road speed,
fault-free.

⊕ `gain_A` is deliberately left alone: once the gate is armed, `gain_A` is the **manual-only** path and
cannot touch an engaged-only symptom.
⊕ `0xC643E` / `0xC6440` (the `gp-0x671a >= 5` arms) are **not spent** — `gp-0x67df` has **never been
non-zero in this kit** (0/53,991 on V68, 0/186,321 on V67), so those arms are **dead in practice**.

### 6d. Artifacts — verified from disk

| | |
|---|---|
| builder | `analysis-2020accord/build_v84_tva.py` |
| decoder | `analysis-2020accord/decode_v84_probe.py` |
| base | `_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin` sha `bb717ce8…` — **the cut that flew route 68** |
| image | `_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin` sha **`344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a`** |
| rwd | `39990-TVA,A160-V84-V83ABASE-LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10-0x13000-0x100000.rwd` sha **`5e830b2588b22fd6238c4bd376e602d603b5d25871368d08df7986519cda1bca`** |

🛑 **V84 WAS RE-CUT.** The first cut carried the V83a-lineage damper thermometer, which V84's own edits
drive to a structurally predictable zero — a probe spent on a quantity that cannot vary (the recorded
V64/V68/V69 failure mode). The control-only cut is **retained, renamed, and must not be flashed**:

| retained as | sha256 |
|---|---|
| `SUPERSEDED-DO-NOT-FLASH-2026-08-08-BY-V84-PROBE-…-magprobe-6bd0-thermo-6ac2-….rwd` | `54985b457125784b72c045da68069f2089a24a23da354a63c553a10f3206ac9e` |
| `SUPERSEDED-DO-NOT-FLASH-_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27_plain_image.bin` | `bdd857c942cab37a26b7d78e4c76cefeec054b33fc46d887d448291e15ab2825` |

**Exactly one flashable V84 `.rwd` on disk.**

### 6e. The probe — the existing 68-byte cave, repointed. No new cave, no second hook.

`0x14A` byte 4 bits 7:3, the field V55/V75/V81/V83a have proven end-to-end on the comma:

| bit | rung | why |
|---|---|---|
| `byte4[7]` | `gp-0x6ada >= +1024` | **the most important bit in the build** — delivered r24, positive |
| `byte4[6]` | `gp-0x6ada <= -1025` | delivered r24, negative. `bit7 OR bit6` = `\|r24\| >= 1024` at FULL duty |
| `byte4[5]` | `gp-0x67fe in {1,2}` | FactorD's liveness gate. **If this reads 0, every FactorD number in the kit is void.** |
| `byte4[4]` | `gp-0x6a10 >= 8` | FactorD's angle-error axis — converts the physics estimate to EVIDENCE |
| `byte4[3]` | hard-coded **1** | build fingerprint, so route-69 logs can never be confused with route-68's |

- **Rungs sized against the LANE's own reachable output**, not a downstream gate's width. Predicted duty
  for a sinusoid: **manual 0.24, engaged 0.64 — a 2.6× step at the engagement edge**, and the manual arm
  is byte-stock by construction ⇒ **the drive contains its own within-route A/B.**
- 🛑 **`sar` floors toward −∞ and the exhaustive self-check caught it**: the obvious `cmp -0x4` fires at
  `r24 <= -769`, a **255-count asymmetry**. The shipped immediates are `cmp 0x4`/`blt` and
  `cmp -0x5`/`bgt` — symmetric within **one count in 1024**, asserted over all 16,385 reachable values.
- **GATE 1**: `gp-0x6ada` 1 writer / 0 readers (blast-radius zero); `gp-0x6a10` 3w/14r all `ld.hu`;
  `gp-0x67fe` 5w/55r all `ld.bu`. The cave **reads** these and **writes none**. The `ld.h` `0x39` vs
  `st.h` `0x3B` one-bit trap is closed explicitly on both sides.
- **Sampling is 100 Hz** ⇒ **every rung is a DUTY-CYCLE statistic, never a peak**, and at 27.75 Hz it is
  under-sampled. Read the ring's numbers that way.

### 6f. Gates
**GATE 1 — PASS.** No RAM allocated, no instruction added, no cave byte moved, extent unchanged at 68.
The census is re-run **fresh on this image** by two independent decoders over both displacement parities
plus the disp23 form, on input, output and `.rwd` readback: after the edit `gp-0x683c` is
**unreferenced image-wide** and `gp-0x6806` gains exactly one reader. **A repoint cannot create a
writer, and the build fails if it did.**

**GATE 2 — phase literally unchanged** (no filter, pole, zero, delay, state, sample point or task-order
change). **Magnitude, honestly, in three directions that do not agree:** r24 **UP** 1.766–2.592× engaged
(justified not by "it is small" but by **this exact cell at this exact value having flown twice,
fault-free, at all speeds**, in a lane that saturates at |dtorque| ≥ 1601 against a measured max of
839); r26 **DOWN**; the damper **DOWN to Honda's**, with the relay index going **1.45 → 0.00** on mode
27. 🛑 RULE 12 applied as **shape**, not as a bound — V80 proved "does not clip" ≠ "is not a relay" with
a supremum that equalled the ceiling exactly.

⚠ **The honest costs, not buried:** engaged r26 damping is cut to 512 flat at all speeds (deeper than
V72 above 10 km/h); V84 gives up the **last** of the damper dose and runs **zero engaged damper below
35 km/h** — Honda's operating point, but not a tested one for *this* car's symptoms (if S2 gets worse,
edits 3–7 are the cause and reverting them is 10 bytes); and **the engaged wheel will feel LIGHTER at
every speed** because the added Coulomb drag is gone.

🛑 **What V84 does NOT address**, said plainly so it cannot be discovered later: **the highway grind**
(V67 and V68 both carried Lever B and the highway grind was still present — **Lever B is not the
highway answer**); the **~28 Hz lane-change transient** (measured dose-independent, full amplitude on
the stock rate lane ⇒ **excitation, not gain**); and **grind #2 under LKAS**.

---

## 7. 🛑🛑 THE FLIGHT INSTRUCTION — ship this WITH the flash

### 7a. Pre-registered predictions, fixed before the drive

| | prediction |
|---|---|
| **S1 — grind #1, 18–22 Hz engaged creep** | **≈ 0.40× V83A's level** — back toward V67/V68's median `e_18-22` ≈ **109** from V83A's stock-band level. 🛑 **IF IT DOES NOT IMPROVE, LEVER B IS FALSIFIED ON A THIRD INDEPENDENT FLIGHT AND THE RATE LANE SHOULD BE ABANDONED AS AN S1 LEVER.** |
| **S3 — macro ratchet ≤30 mph** | **improved.** The engaged r26 arm is *numerically* V72's cut, which the operator twice reported fixed it. **No instrument exists — the operator's report is the arbiter.** |
| **S2 — micro-ratchet, 6–9 Hz** | **GENUINELY UNCERTAIN, and this is its FIRST REAL TEST.** At 7.79 Hz r24's transfer is near-pure damping (`Re/\|G\|` ≈ −0.995), so a **1.766–2.592× raise adds real damping at zero DC cost.** No build has ever moved S2 except V80's unflyable `k` = 4.16. ⚠ **[BELIEF]**, a hypothesis, not a promise. |
| **S4 — impedance / friction** | engaged-vs-manual asymmetry **STRUCTURALLY ZERO** afterwards — all six factor families identical across modes 24/25/26/27. **Checkable from the bytes, and this build checks it.** |

### 7b. 🛑 THE GRIND-#2 DRIVE PROTOCOL — four builds in a row have failed to accumulate the exposure

> **Empty lot or wide low-traffic loop, openpilot ENGAGED THROUGHOUT.** Grind #2 follows the **firmware
> arm**, not the hands — **hands may stay on the wheel.**
>
> - Hold **4–11 km/h. Do not stop.**
> - Keep the wheel **≥ 100° from centre at all times**, sweeping **100–360°**.
> - **Reverse direction briskly enough to reach column rate 100–500 °/s** — **continuous figure-eights,
>   not isolated inputs.**
> - **Accumulate ≥ 166 s in-regime; target 255 s** ⇒ budget **6–9 minutes** of continuous
>   large-amplitude engaged creep cornering.
> - Then repeat **~60 s of the identical manoeuvre with LKAS OFF** as a within-drive control.
>
> **Scoring is fixed in advance:** 1.28 s windows, NFFT 256 / hop 128, 40–49 Hz p99 analytic envelope
> > 500, engaged, 0.3–4 m/s, |ang| ≥ 100°, merged into events.
> **0 events in ≥ 166 s ⇒ Lever B does not produce grind #2 at P(0) ≤ 0.05 against the V62/V65 rate.**

⚠ **RULE 9's "~90 s suffices" is OPTIMISTIC BY ~1.8×, AND ITS OWN TWO NUMBERS ARE MUTUALLY
INCONSISTENT.** RULE 9 states V67's 11.5 s gives P(0) = 0.80 **and** that ~90 s takes P(0) "from ~0.61
to < 0.05". Those cannot both hold: the 11.5 s / 0.80 pair fixes the burst rate at λ ≈ 0.0194/s, which
puts 90 s at P(0) ≈ 0.17 — not 0.61 — and puts the **P(0) < 0.05 threshold at ~155 s**, hence the
≥ 166 s floor with margin and the 255 s target. **Correct RULE 9 to the protocol above.**

⊕ Also ship the **≥ 60 s of MANUAL driving above 50 km/h** control that V83a asked for and route 68
under-supplied — the manual arm is byte-stock on V84 by construction, so it is a free within-drive
isolator.

🛑 **The flash decision and the bus are the operator's. Name the file back before proceeding.**

---

## 8. PROCESS — two failures worth more than the flight numbers

### 8a. 🛑🛑 Hashes were reported BEFORE the roll-call, and the artifact then changed underneath them
**The orchestrator quoted V84's artifact hashes to the operator before completing the agent roll-call.**
The builder subsequently **re-cut the artifact and renamed the files whose hashes had already been
reported.** **The operator caught it** — the kit's verification did not.

This is the exact failure CLAUDE.md's close-out section describes, and it recurred with the rule written
down. Two aggravating details worth recording:
- **`TaskList` returned nothing for in-process teammates.** Name-based roll-call — enumerating every
  agent spawned this session, by name, and confirming each has stopped — was therefore the **only
  available method**, and it was **skipped**.
- **Once reported, a hash is FROZEN.** A re-cut under the same build number is a legitimate engineering
  decision; re-cutting after the hash has been communicated is a **record defect** regardless of whether
  the new build is better. The correct order is: roll-call → freeze → re-hash from disk → report.

📋 **METHOD RULE: an agent's last message means it SENT a message — not that it finished, and not that
it stopped. Do not quote an artifact hash to the operator until every spawned agent is confirmed
stopped and the hash has been re-read from disk.**

### 8b. 🛑 The stale-memory-snapshot hazard
**`~/.claude/projects/…/memory/` is NOT the repo's `memory/`.** It is a separate, older snapshot. A
subagent this session grounded itself on that directory and reproduced **six corrections' worth of stale
conclusions** — including claims this kit had explicitly retracted.

📋 **Prime every subagent with the REPO path explicitly:
`C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\memory\`.** A memory that arrives inside a
`<system-reminder>` is a snapshot of what was true when it was written, not a current fact; if it names
a file, address or flag, **verify it still exists** before reasoning from it.

---

## 9. 🛑 RECORD DEFECTS FOUND THIS SESSION

| # | defect | where |
|---|---|---|
| 1 | **`STATE.md` calls V83a UNFLASHED.** It flew as route 68. | `docs/STATE.md` |
| 2 | **Route `5d`'s raw rlogs are missing** (V74's clean symptom-measurement flight, 17 segments) while `extract_r5d_cache.py` is its canonical extractor and `BUILD-LINEAGE.md` leans on that cache. **Every V74 conclusion runs against the cache, not the log.** | `analysis-2020accord/rlogs/` |
| 3 | **RULE 7's corollary "grind #2 is V62's `sar`" is STALE.** V67/V68 produced the best grind-#1 result in the kit **without** V62's `sar`, and the dose table shows the r24 half — not the `sar` route as such — is the active ingredient. | `docs/BUILD-LINEAGE.md` RULE 7 |
| 4 | **The V47 row's "falsified — do not resurrect" is FALSE.** V47 wrote modes 10/11 on a mode-24/26 car ⇒ **inert by table selection, uninterpretable, NOT falsified.** A "falsified" label on an inert build permanently closes a lever that was never tested. | `docs/BUILD-LINEAGE.md` Part 1 |
| 5 | **`0xC61B2`/`0xC61B4` are mislabelled as a "pre-gain deadband arm".** They are the **arbitration / LKAS output clamps**, and they have been at **4× Honda (2048) since V38**. Comment-only; changes no byte. | `build_v83a_tva.py:359-360`, `build_v84_tva.py:544-545` |
| 6 | **RULE 9's ~90 s grind-#2 exposure figure is optimistic by ~1.8× and self-inconsistent.** See §7b. | `docs/BUILD-LINEAGE.md` RULE 9 |

⊕ Route 68's scoring code and cache (`_cache_r68x/`, `score_r68.log`) currently live in the session
scratchpad, **not in `rlog-tools/`**. Every route-68 number in this handoff is reproducible only from
there until it is promoted.

---

## 10. GOLDEN-MODEL CORRECTIONS APPLIED

`analysis-2020accord/eps_lkas_chain_model.py`, eight corrections:

| | correction |
|---|---|
| **a** | **"CARRY THIS UNEXPLAINED — r26 ×2 AND r26 ÷6 BOTH HELPED" is RESOLVED.** Neither helped; **r24 is the actor**, with the dose table cited in place. The "r24 near-inert across 4:1" and "grind #1 is blind to r24" claims are retracted with their premise. |
| **b** | **`soft_eme_windup_shaper()`'s `gp-0x6acc` gate was WRONG.** It is `(x + 0x2000U) < 0x4001` — a **symmetric ±0x2000 zero-gate**, not a one-sided `x > +8192`. The "chatter can only appear on the positive side" corollary is **deleted**. |
| **c** | **"THE V57 DECOUPLE IS OFF THE CAR" is STALE for V81/V83A/V84** — those read disp `0x7CD0` (`0xC6CD0` = 3564, `0xC646C` = stock 891). True only of V76/V78/V79/V80. |
| **d** | **`governor_step_selector_bandwidth()` mislabelled `gp-0x67f5` as hands-off/hands-on.** It is **voted vehicle speed** crossing **16.6 km/h** (cal `0xC531E` = 1062, 10-cycle debounce `0xC64E7`, a **byte**). |
| **e** | **`gp-0x671a` is not "a bounded [0,5] persistence ramp tracking sign".** It is the **oscillation detector's** debounced authority level (`FUN_000428d4`, one writer @`0x42A12`, sourced from `gp-0x67df`/`gp-0x357c`) — and since `gp-0x67df` has **never** been non-zero in this kit, the `state >= 5` arms `0xC643E`/`0xC6440` are **dead in practice**, not merely rare. |
| **f** | **`gp-0x6c2c` is filtered motor ACCELERATION, not rate** (`FUN_00041464`: two cascaded IIRs on the one-cycle delta of the filtered rate) ⇒ the friction lane outputs **≈0 under steady motion** and responds only to oscillation. |
| **g** | **Task rates made load-bearing**: table damper `FUN_00034350` is **task 5 = 100 Hz** (sole caller `FUN_00022ca0`); aggregator `FUN_0003aa2c` and `FUN_0003a382` are **task 1 = 1 kHz**. **ZOH crossover 25 Hz**, above which the 100 Hz damper can be sampled into an anti-damping force. |
| **h** | **Factor-record layout rule made concrete**: `[npt][X × npt][Y × npt]`, **`Y` at `base + 2 + 2*npt`** — **`+0x0A`** for a 4-point record, **`+0x0C`** for 5-point FactorD — and **Honda's mode pairing is 24↔26 and 25↔27.** |

---

## ⇒ NEXT

1. **Fly V84** with §7's protocol attached. 🛑 The flash decision and the bus are the operator's; name
   the file back. Score against §7a's four pre-registered predictions **and** run the grind-#2 protocol
   to its ≥ 166 s floor — that number is the point of the drive, not a bonus.
2. **If S1 does not improve, stop proposing rate-lane levers for grind #1.** That is a pre-registered
   commitment, not a preference.
3. **Promote route 68's scoring code out of the scratchpad** into `rlog-tools/`, alongside a
   `decode_v84_probe.py` run, or route 68's numbers become another cache-only result like route `5d`'s.
4. **Fix the six record defects in §9** — particularly #4, because a false "falsified" permanently closes
   a lever, and #1, because a flown build recorded as unflashed will be re-proposed.
5. **The highway grind still has no candidate.** Lever B is explicitly not it (V67/V68 carried it and the
   highway grind persisted), and the damper-dose model of the ring is now falsified. `gain_A` rec2/rec3
   (`0xC6A90`/`0xC6AA4`) — the ≥50 km/h r26 records, **byte-stock in every image ever built** — remain
   the untouched cells that reach that regime, but note they are now the **manual-only** path once V84's
   gate is armed.
6. **FactorD stays gated on V84's own probe.** `byte4[5]` (`gp-0x67fe ∈ {1,2}`) and `byte4[4]`
   (`gp-0x6a10 >= 8`) are what convert every FactorD number in the kit from [BELIEF] to [EVIDENCE] — or
   void them.
