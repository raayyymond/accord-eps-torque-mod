# HANDOFF 2026-08-13 — V98 FLEW, THE COMPARATOR ANSWERED, AND V99 IS CUT

**Session class: SCORE A FLIGHT → CORRECT THE RECORD → CUT A LEVER.**
Orchestrated. Five agents (`scorer-v98`, `arc-map`, `tracer-arms`, `builder-v99`, `path2-authority`)
plus one grandchild (the byte ledger). Every crux re-verified by the orchestrator from disk.

---

## 1. V98 FLEW AS ROUTE `0x81`, FAULT-FREE — AND THE COMPARATOR ANSWERED

**Identity is single-frame proof:** `0x14A` byte7[7:6] == **2** on **17,983 / 17,983 frames, duty
1.000000**. Fault-free: 0 sentinels, `CONFIG_VALID` 1.00000, `OUTPUT_DISABLED` 0.00178, DTC bit2
0.00000. **181.5 s / 65.9 s engaged in 3 episodes** (longest 29.8 s).

⭐ **The route carries a BACK-TO-BACK LKAS-OFF CONTROL.** Engaged ends 110.56 s; the operator's
deliberate *"this is how smooth it should be"* demonstration begins **110.57 s** — consecutive frames,
same lot, same tyres. **The kit had never obtained a within-drive matched control. Make it MANDATORY.**

### The comparator result — duties over 6,591 engaged frames [EVIDENCE, orchestrator-reproduced]
```
(b6=0,b5=0) 0.5765   (b6=1,b5=0) 0.4235   (b6=0,b5=1) 0.0000   (b6=1,b5=1) 0.0000
```
- **`b6` = 0.4235 ⇒ MODEL and ACTUAL are COMPARABLE.** 🛑 **REFUTES `STATE.md`'s "the arms may be
  wildly unequal, so whichever you move the residual barely notices."** ⇒ **V89 and V97 were both
  correctly aimed at live arms; their nulls are DOSE or DIRECTION, not REACH.**
- **`b3` = 0.0000 over all 17,983 frames ⇒ `sign(gp-0x6752)` = −1 CONSTANT.** Closes a multi-session
  blocker: `b4 = 1 ⇔ the six-lane sum is POSITIVE`.
- **The `0x7FFF` latch excluded ZERO frames** — never fired in **96,414 frames** across 7e/7f/80/81.

### ⭐⭐ THE BEST RESULT: the comparator moves DURING the symptom
98 engaged windows, terciles of their own 6–9 Hz RMS, partial Spearman with block-permutation null:
```
b6  r = -0.321  p = 0.0050   SURVIVES        <- the ACTUAL arm SWELLS as the grinding rises
b4  r = +0.087  p = 0.49     NULL  (control)
b7  r = +0.037  p = 0.77     NULL  (control)
```
**First time the kit has read a decomposition out DURING the symptom instead of scoring across drives.**

⊕ **It is in the ANGLE and it is NOT commanded:** engaged/manual 6–9 Hz is **2.66× in steering angle**
with a 0.99 negative control; within engaged frames the column is **43× more 6–9 Hz-rich than the
command driving it.** ⚠ **427 is BROADBAND-elevated (4.14× in the 35–45 Hz negative control) and
supports NO band-specific claim** — same wall V87 hit with `gp-0x6b98`.

---

## 2. 🛑 A PREMISE THE ORCHESTRATOR GOT WRONG — CAUGHT BY THE OPERATOR

The orchestrator wrote **"REQUEST ≈ 0 / REQUEST is the minor arm"** from `b5` = 0.0000. **That does
not follow.** `b5` tests `|REQUEST| ≥ |ACTUAL|`; it licenses only `|REQUEST| < |ACTUAL|`. Since MODEL
and ACTUAL **nearly cancel** (`|iVar6|` ≈ **130** median while each arm runs to hundreds/thousands),
**REQUEST can be many times the RESIDUAL and still be smaller than ACTUAL on every frame.**

🛑 **This is verbatim the error `STATE.md` already retracted** (*"the denominator is the RESIDUAL, not
the range"*), reproduced one day later with a different bit. ⇒ **THE REQUEST ARM IS OPEN.**
⊕ The operator's own reasoning is supported by the disassembly: `gp-0x6bfa = clamp(gp-0x3d90,
±20000)`, and `gp-0x3d90` is the **11-slot aggregator output — the LKAS + driver-torque demand
path.** **Our own 4× gain `0xC6CD0` feeds that arm.**
⇒ **The correct comparator was never built: `|REQUEST| ≥ |iVar6|`.** Whether `iVar6` is reachable by
a cave is **OPEN** — it may live only in a register inside `FUN_00038148`.

---

## 3. ⭐⭐ STOCK ENCODES AN EXACT PHASE MATCH, AND V97 BROKE IT [EVIDENCE, verified 3 ways]

```
0xC40D0 = 408/4096 = 51/512 = 0.099609375   MODEL-arm friction EMA
0xC63AC = 102/1024 = 51/512 = 0.099609375   ACTUAL-arm pole, HONDA STOCK   <- BIT-IDENTICAL
0xC63AC = 150/1024 = 75/512 = 0.146484375   V97/V98, ON THE CAR            <- MATCH BROKEN
```
Two differently-scaled cells carrying different numbers, chosen so α matches to the last bit. In a
**difference of two estimates**, identical filters **cancel**; different filters manufacture a
disturbance that is not there:

| f | `\|H_model − H_actual\|` STOCK | on the car (V97/V98) |
|---|---|---|
| DC | 0.000000 | 0.000000 |
| 6 Hz | **0.000000** | **0.111** |
| 7.79 Hz | **0.000000** | **0.136** |
| 9 Hz | **0.000000** | **0.151** |

⚠ **SCOPE, and it is load-bearing:** this compares **two filter stages on a common basis.** It assumes
both arms filter a **COMMON input** through only those stages — and **the MODEL arm carries SEVEN EMA
stages** (`0xC40D4`×2 −33.25°, `0xC40D0`×1 −23.63°, `0xC40D6`×2 −73.86°, `0xC40D8`×2 ≈ −0.62°).
⇒ **EVIDENCE about the two poles; BELIEF about the arms.** The honest arm-to-arm transfer is **OPEN**.
🛑 **`STATE.md`'s "MODEL is UNFILTERED" is FALSE** — true only of `FUN_00038148`.

---

## 4. 🛑🛑 THE LIVE-8 ASYMMETRY — THE MOST DAMNING FINDING OF THE SESSION

`build_v97_tva.py:65-67` computed the Path-1 dilution — **"+2 %…+13 % of the TOTAL command"** — **and
used it to argue V97's COST was acceptable. The identical dilution applies to the BENEFIT and was
never stated.** The 2026-08-12 audit caught this, tagged it *"the tracer should price Path-2's actual
share"*, and **it was never done.**

⇒ 🛑 **PATH-2'S AUTHORITY OVER THE DELIVERED COMMAND HAS NO SURVIVING NUMBER IN THE KIT.** The only
bound ever computed (*"≤ 9 % share"*) was **correctly retracted as invalid**. Precedent class:
`0xC63A4` died at **1.1 ct of a 342 ct signal**.
⇒ **If Path 2 controls only a few percent at 6–9 Hz, V97's felt-null needs no other explanation — and
neither would V99's `0xC63AC` revert.** `path2-authority` is bounding it; **result pending.**

⚠ **A stale `STATE.md` claim that must not be re-cited:** §A6b calls `0xC63A0`'s four-build null
*"unreconciled"* and it is **NOT** — the lane it weights has `ch₀` **zero on 98.8 % of engaged
frames**. It is a null on a **dead lane**, not evidence about Path-2's authority.

---

## 5. V99 — CUT, VERIFIED, **NOT FLASHED**

```
39990-TVA,A160-V99-V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1-0x13000-0x100000.rwd
  image a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726
  rwd   b4a2d24ce51b4e643a091c9b393f356f92abd6a4aed2a123daa59141bbd45a87
  builder analysis-2020accord/build_v99_tva.py   134/134   BASE = V98 (on the car)
```
**FOUR differing bytes + two CRC trailers (12 B in 5 runs). Orchestrator-verified from the images.**

| addr | V98 | V99 | what |
|---|---|---|---|
| `0xC40BC` | 600 | **300** | **THE LEVER** — Coulomb ramp knee **10.61 → 5.31 °/s** |
| `0xC63AC` | 150 | **102** | **REVERT TO HONDA** — restores the exact 51/512 match |
| `0xC4B52` | `00` | **`02`** | identity — `mov 0x0,r7`→`mov 0x2,r7` ⇒ byte4 `b5` ≡ 1 |

### 🛑 THE COMPOUNDED DOSE IS 4.00× HONDA BELOW 5.31 °/s, NOT 2× [EVIDENCE, reproduced independently]
`0xC40BC` multiplies with **V89's K1 = 204, still on the car**:
```
col deg/s :   1     2     3     5     8    10    13  |  20    30    60
STOCK      : 1.00  1.00  1.00  1.00  1.00  1.00  1.00 | 1.00  1.00  1.00
V98        : 2.00  2.00  2.00  2.00  2.00  2.00  2.00 | 2.00  2.00  2.00
V99        : 4.00  4.00  4.00  4.00  2.65  2.12  2.00 | 2.00  2.00  2.00
```

### ⭐ A NULL-BY-CONSTRUCTION CONTROL — a first for the kit
300 and 600 are **arithmetically identical wherever the ramp saturates** (≥ 10.61 °/s) and differ by
**exactly 2.00×** below 5.31 °/s. ⇒ **E1: `b6` duty must move in the low-rate bins and MUST NOT move
in the ≥ 25 °/s bins.** A change in all bins is an operating-point artefact, not the lever.
⚠ Prediction is **ORDINAL, not bin-exact** (`gp-0x6abc` is MOTOR rate; bins are COLUMN rate).

### The honest negatives, carried from the builder
1. 🛑 **GATE 2 NOT CLOSED** — needs `L`, unmeasured. A harder ramp raises small-signal
   describing-function gain = the limit-cycle setup. **V80 is the precedent: "worst grinding ever",
   vehicle instability, a 30 s 27.4 Hz limit cycle, and ZERO DTCs — invisible to the fault system.**
2. ⚠ **`0xC40BC` is NOT engagement-gated** — all four `FUN_0003b8f6` entry guards are plausibility
   checks. **It acts in MANUAL.** V65 precedent. **The LKAS-off arm should feel different; that is the
   lever, not a fault.**
3. **Identity is a DUTY, not a single frame** (`b5` ≥ 0.999 + byte7[7:6]==2). A real regression.
   🛑 **`0x14A` byte7[7:6] is EXHAUSTED — all four codes burned. V100 should be a dedicated ≥3-bit
   identity build with its own `0x18F` hook, as ITS OWN BUILD**, never bundled with a measurement.
4. **Not single-variable (two cells), and not a new lever** — `0xC40BC` flew at 6000; this is the same
   cell the other way, into virgin range (**only 600 and 6000 have ever existed on 94 images**).
5. ⭐ **After V99 the ACTUAL arm is byte-for-byte Honda.** The only non-Honda cells left on the whole
   observer structure are `0xC40D2` (V89) and `0xC40BC` (V99) — **both on the MODEL arm.**

---

## 6. RECORD DEFECT — **SIX** STALE FLIGHT-STATUS CLAIMS, CORRECTED

The eighth instance, and it was **nested three generations deep**. `STATE.md` ×3 (head said V97 on
car; §33 said V98 UNFLASHED; §2074 still said **V94 on the car and "still flashed"**) and
`BUILD-LINEAGE.md` ×3. All corrected in place with a note of what each used to claim.
🛑 **RUN THE GATE AT EVERY CLOSE-OUT:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`

---

## 7. NEW MEMORIES
`accord-steering-sign-convention-confirmed` · `accord-v98-comparator-ranked-the-observer-arms` ·
(tracer's) `reference_accord_request_arm_shadow_lockstep_and_no_cal_cells` ·
`reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap` ·
`reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it` ·
`reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness`

## 8. OPEN, IN PRIORITY ORDER
1. 🛑 **Path-2's authority in COUNTS** (`path2-authority`, running). The dose calc abandoned on
   2026-08-12 is **now doable** — both blockers closed (`f′` swings **1.000×**; `|iVar6|` ≈ 130).
2. **Is `iVar6` cave-reachable?** Decides whether `|REQUEST| ≥ |iVar6|` can ever be built.
3. **The total arm-to-arm phase budget** including the six lanes' upstream dynamics.
4. **Perceptual calibration against builds that WERE felt** — V86B, V80, V94 have known cell deltas
   *and* operator reports. Never used.
5. **RULE 7 for the LERP knots** (`decompile_function(0x382d8)`) before any knot-valued lever.
6. 🛑 A standing memory is **REFUTED from the images**:
   `accord-base-assist-damper-cannot-reach-the-micro-regime` — **five builds had both dead zones open;
   THREE FLEW** (V75 r5e, V76 r65, V80 r66). Four of its claims are false. **Needs correcting.**
