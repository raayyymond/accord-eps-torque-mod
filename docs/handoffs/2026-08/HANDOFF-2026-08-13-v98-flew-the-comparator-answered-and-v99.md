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

## 3. ⚠⚠ RETRACTED LATER THE SAME DAY — SEE §3b. THE CELL IDENTITY IS REAL; ITS CONSEQUENCE IS NOT.
🛑 **DO NOT QUOTE THE `0.111 / 0.136 / 0.151` "PHANTOM" NUMBERS BELOW.** They assume both arms filter a
**common input**, and the arms **do not share one**. Kept verbatim as a record of what was believed
mid-session. **The surviving claim is only that V97 moved the arms FURTHER APART (+7.82°, +5.4 %).**

## 3. ⭐⭐ STOCK ENCODES AN EXACT PHASE MATCH, AND V97 BROKE IT [⚠ SUPERSEDED — see §3b]

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

## 3b. 🛑🛑 THE SESSION'S REAL RESULT — `f′` COMPRESSION, AND V99 IS **NOT A FIX**

Full trace: `docs/traces/TRACE-2026-08-13-path2-authority.md` (sha256 `322003fb4bc6e57d…`).

**`f′`, the Stage-2 LERP's local slope, is a deterministic function of `|iVar6|`:**
```
|iVar6| ct : 0-178  178-356  356-719  719-1200  1200-1800  1800-3000  3000-5000
f'         : 2.539   2.174    1.496    0.948      0.488      0.346      0.248
```
| route 81, engaged | steeringPressed | D3 mask |
|---|---|---|
| `\|iVar6\|` p50 **hands-ON** | **2,829 ct** | **2,818 ct** |
| `\|iVar6\|` p50 hands-OFF | 188 ct | 337 ct |
| **f′ p50 hands-ON / hands-OFF** | **0.346 / 2.174** | **0.346 / 2.137** |

🛑 **THE FIRMWARE DESENSITISES THIS LANE 6.3× EXACTLY WHEN THE DRIVER PUSHES** — and pushing is how
the operator provokes the symptom. Two independent masks agree to **2 %**. **Every perturbation of
`iVar6` reaches the car through `f′`, and V89 and V97 BOTH argued their direction on hands-off data
(the steep part) while the symptom lives on the flat part.** ⇒ **ONE mechanism for both nulls**,
consistent with V98's comparable arms and the lively 427 lane, **requiring nothing unmeasured.**
[BELIEF — fits all the data; the test is the `gp-0x6ad6` rung in §8.]

🛑 **CONDITIONED 2026-08-13 (later), record-repair pass — this section used to read "PATH 2 IS
AUTHORITATIVE... no dilution anywhere" unconditionally.** `tracer-6ad6` found the PID's own reference
clamp `0xC6200` = 8192 sits inside this very chain (`FUN_0003a382` @ `0x3a7a2`, all three of P/I/D
driven from the clamped difference); crux verified by the team lead directly in Ghidra
(`read_memory(0xC6200)` = 8192, `disassemble_bytes` reproduces the listing instruction-for-instruction).
`d(gp-0x6b94)/d(gp-0x6b70)` = **0.2529 / 0.2565 / 0.2617** at 6 / 7.79 / 9 Hz **is the UNSATURATED
derivative, valid ONLY under the condition `|gp-0x6ad6| < 8192`.** "No dilution anywhere" (every link
unity, an enable byte = 1, a flat LERP = 1.000 at every speed, or the PID) is still correct as a
statement about the unsaturated chain — the numbers are not deleted, they are conditioned. When the
clamp binds, the true derivative is **0**, and its duty is UNMEASURED (V100's RUNG A targets it).
Positive control **run first and passed** (unaffected — it ran unsaturated): reproduces the recorded
*"+41.8° lead at 21 Hz, |D|≈|P|"* at **|D|/|P| = 1.055, arg H = +41.81°.** Both gates OPEN, incl.
**`gp-0x67ab` ≡ 0 STRUCTURALLY** (sticky-OR over roles {2,3,4}; `0xC4124` contains no 2/3/4 anywhere;
byte-identical across 65 images) — **closes an OPEN item from `HANDOFF-2026-07-27:287`.**

### ⭐ THE PERCEPTUAL BRACKET — the "underivable" step is now an interpolation
| build | measured in-band delivered change | operator | felt |
|---|---|---|---|
| V88 | 15–22 Hz **0.549 [0.407,0.844]** | *"grinding fixed"* | ✅ |
| V62 | 18–22 Hz **8–42× down** | *"grinding at 2–5 mph is gone!"* | ✅ |
| V85 | 6–9 Hz **1.088 [0.746,1.451]** | *"barely, perceptibly better (unsure)"* | ~✗ |
| V89 | **0.947 [0.827,0.979]** | *"fixed nothing"* | ✗ |

⇒ **~0.55× (−45 %) IS felt. ~1.09× (+9 %) IS NOT.**

### 🛑 EVERY CANDIDATE SCORED AGAINST THAT FLOOR — AND V99 FAILS IT
| lever | dose in his regime | verdict |
|---|---|---|
| `0xC63AC` 150→102 (V99 hygiene) | 1.1–3.6 ct = **0.8–2.5 %** of Path-2's 140.6 ct | **below ~20×** |
| **`0xC40BC` 600→300 (V99's LEVER)** | 0.7–1.7 ct = **0.5–1.2 %** | **below 8–18×** |
| `0xC63AE` 1024→**2048** | ≈ **+28 %** on the lane, ≈ +177 ct | ⭐ **the only one ABOVE** |

🛑 **`0xC40BC` is structurally dead in his regime [EVIDENCE, orchestrator-verified from `_scratch/cache/r81`]:
93.1 % of hands-on engaged frames sit ABOVE the 10.61 °/s knee, where 300 and 600 are ARITHMETICALLY
IDENTICAL.** Mean ramp ratio **1.050** — a ×1.05, not the ×2 the build assumed. Only **4.3 %** of
hands-on frames fall below 5.31 °/s where the full 2× applies. ⊕ Sensitivity is **one-directional**: a
larger motor-referred scale puts the knee *lower* ⇒ *more* frames inert, never fewer.
🛑 **And the structural kill: `friction = |fVar18| · ramp · K1/1024` ⇒ `0xC40BC` and `0xC40D2` are TWO
FACTORS OF THE SAME PRODUCT, not two levers. V99's perturbation is 0.096× V89's — and V89 measured
FLAT against a well-powered same-build placebo band (0.92 σ).**
🛑 **Direction right, dose unreachable:** V85's 600→6000 moved the knee *out* of the regime and the
ratchet got **worse** (2.89× → 6.58×) — but reaching his p50 of **83 °/s** needs `norm` ≈ 4,700–11,000,
**which IS 6000, which flew and was worse. The dose requirement and the flight result are in direct
conflict, and this cell cannot satisfy both.**

⇒ **V99 IS RETRACTED AS A FIX.** The `.rwd` is built, verified and pushed. **Fly it only as hygiene
riding on a build whose real content is something else, pre-registered as expected to be felt as
nothing on both cells.**

### 🛑 FIVE RETRACTIONS FROM THIS SESSION — do not re-cite any of them
1. **§3's "exact pole match ⇒ 13.6 % phantom".** The cell identity is real and probably deliberate
   (`round(0.1·4096) = 410`, but Honda shipped **408 = 4×102**; and `102` occurs 6×/12× in the two
   blocks against `408` **once** in each) — **but it is a match between two STAGES, not the ARMS.** The
   arms **do not share an input** (a plant model vs a six-lane weighted sum), `0xC40D0` is one stage of
   five on a sub-path, and **stock is already 84° and 0.557-vs-0.906 apart.** Survives: **V97 moved the
   arms further apart** (+7.82°, +5.4 %).
2. **"REQUEST is minor"** — see §2. The denominator is the **RESIDUAL** (`|iVar6|` p50 **389 ct**).
3. **427 "broadband ⇒ no band-specific claim" was an ARTEFACT** — 427 is transmitted at **49.835 Hz**;
   a ZOH images 5–15 Hz onto **35–45 Hz** (a pure 7.79 Hz tone reads 0.163 RMS there out of nothing).
   With a valid **20–24 Hz** control: 6–9 Hz excess **2.30× on 427, 1.97× on column — they agree.**
4. **V86's `gp-0x67ab < 2` rung could NEVER have fired** — `< 2` is true of the open (0) *and* closed
   (1) states, yet `BUILD-LINEAGE.md` cites it as *"lever in force three ways."* A falsifier that could
   not fire. **The gate is open; V86 is not why we know it.**
5. ⚠ **`0xC63A0` weights `gp-0x6bd0`**, not `gp-0x6b26` (that is `0xC63A6`). Its four-build null is
   explained by `gp-0x6bd0` ≈ 0 on 87,940 frames — **not** by the FactorC×FactorE dead-zone product.
   *(Orchestrator error: the right reconciliation was relayed against the wrong cell.)*

## 4. 🛑🛑 THE LIVE-8 ASYMMETRY — AND IT IS WORSE THAN SYMMETRIC

`builds/v80_v107/build_v97_tva.py:65-67` computed the Path-1 dilution — **"+2 %…+13 % of the TOTAL command"** — **and
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

## 5. V99 — CUT, VERIFIED, **NOT FLASHED**, and 🛑 **RETRACTED AS A FIX (see §3b)**
🛑 **Its lever `0xC40BC` delivers 0.5–1.2 % against a ~+9 % perceptual floor, and 93.1 % of his
hands-on frames are above the knee where the change is arithmetically nil.** The build below is
correct, verified and reproducible — **it is the AIM that is refuted, not the workmanship.**

```
39990-TVA,A160-V99-V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1-0x13000-0x100000.rwd
  image a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726
  rwd   b4a2d24ce51b4e643a091c9b393f356f92abd6a4aed2a123daa59141bbd45a87
  builder analysis-2020accord/builds/v80_v107/build_v99_tva.py   134/134   BASE = V98 (on the car)
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

## 8. ⇒ THE V100 SHAPE, AND WHAT IS STILL OPEN
✅ **CLOSED this session:** Path-2's authority in counts (**0.2565, authoritative — 🛑 CONDITIONED
2026-08-13 later: valid only while `|gp-0x6ad6| < 8192`, see item 1 immediately below, which this
session's own item-1 rung already anticipated**); the perceptual calibration against felt builds
(**~0.55× felt, ~1.09× not**); `gp-0x67ab` (**≡ 0 structurally**).

**V100, in order:**
1. ⭐⭐ **`|gp-0x6ad6| ≥ 8192` — ONE COMPARATOR RUNG, and it decides everything above.** The PID clamps
   its feedback at ±8192 (`0xC6200`) while `gp-0x6ad6` itself runs to ±25600, and **term 0
   (`gp-0x6b4a`) alone can rail it.** **If railed, Path-2's MARGINAL authority is exactly zero with
   every gain above unchanged.** Comparator ⇒ no LSB, no ceiling, no distribution — **its duty IS the
   answer**, and a null retroactively explains V89 *and* V97 with one mechanism. **This cell has never
   been on the wire.** 🛑 Pre-register that null sentence **before** the cut.
2. **`0xC63AE` 1024 → 2048** — the only lever scored today that clears the perceptual floor (**≈ +28 %
   on the lane, ≈ +177 ct**), and it attacks `f′` itself rather than a term inside the residual.
   🛑 **Direction is UP, not down** — the scale sits in the chain **twice**
   (`d(gp-0x6b70)/d(iVar6) = (scale/1024) × LERP′`), so 512 is **0.71× WORSE**.
   🛑 **Never 0** (flattens to a relay). 🛑 **Never far above 2048** — at 4096 the median index lands in
   the final segment and **pins at the ±8192 clamp; a clamped output IS a relay, V80 class.**
   🛑 **RULE 7 UNPROVEN** — knots are mode-indexed and `decompile_function(0x382d8)` has NOT been run.
   ⚠ **Must FOLLOW the rung in (1), not precede it** — raising `gp-0x6b70` pushes toward that clamp.
   ⚠ Predictable cost: changed steering weight, the V86B *"extra dampening at slow speed"* class —
   which he **felt**, and which is itself evidence the dose is in a felt range.
3. **A dedicated ≥3-bit IDENTITY build with its own `0x18F` hook** — `0x14A` byte7[7:6] is exhausted,
   all four codes burned. **As its OWN build**, never bundled with a measurement class (V24/V27/V48B).

**Still open:**
4. **Is `iVar6` cave-reachable?** Decides whether `|REQUEST| ≥ |iVar6|` — the comparator that *should*
   have flown — can ever be built. **REQUEST is now the most important unmeasured term in the chain**:
   zero cal cells, shadow-lockstep protected at `gp-0x4cfa`, and our own 4× `0xC6CD0` feeds it.
5. **The total arm-to-arm phase budget** including the six lanes' upstream dynamics. ⊕ The cheap route
   is two sign rungs (`gp-0x6bfe < 0` and `(gp-0x374c>>4) < 0`, the latter already built as `b4`) —
   the phase falls out of the cross-correlation of two 100 Hz sign sequences with **no scale
   assumption and no upstream trace.**
6. 🛑 A standing memory is **REFUTED from the images**:
   `accord-base-assist-damper-cannot-reach-the-micro-regime` — **five builds had both dead zones open;
   THREE FLEW** (V75 r5e, V76 r65, V80 r66). Four of its claims are false. **Needs correcting.**
7. 🛑 **`BUILD-LINEAGE.md` still cites V86's `gp-0x67ab < 2` rung as "lever in force three ways."**
   It could never have fired. **Needs correcting.**
