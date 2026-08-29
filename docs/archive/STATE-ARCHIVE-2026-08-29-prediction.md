# STATE archive — superseded during the prediction work

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **V158 BUILT — THE GOLDEN MODEL'S OWN DAMPER PRESCRIPTION. IT SUPERSEDES V156/V157.**
🛑 **A PROCESS FAILURE, FOUND AND CORRECTED.** V156 and V157 were designed from
`BUILD-LINEAGE` and V134's docstring, which model the damper as a **two-factor product**. The
**GOLDEN MODEL** — the reference `CLAUDE.md` says to read first — already carried the **full
five-factor structure** (`FactorB 0xC9CCC · FactorC 0xC9E9C · FactorD 0xC9DB4 · FactorE 0xC9F84 ·
ceiling 0xC77A0`) **and a specific, measured prescription.** My "four-factor discovery" last turn was
a **re-derivation of something the kit already had.**

### 🛑 WHAT IS WRONG WITH V157 — IT REPEATS V72's ERROR
The golden model states the rule and names the failure:
> *"only lifting Y[0] delivers, and **Y[0] := Y[1] is the largest MONOTONE lift** of Y[0] alone"*
> *"The lever is **FactorC Y[0]:=Y[2] + FactorE X[0]: 60 -> 12 + FactorE Y[1]:=Y[2]** … It **OPENS
> THE RATE DEAD ZONE** rather than raising a gain, so the damper becomes genuinely rate-proportional
> in the symptom's range — **the OPPOSITE of V72's flatten-to-relay error**."*
```
   stock   FactorE  X=[60,400,2500,4000]  Y=[  0,140,539,927]   MONOTONE
   V157             X unchanged           Y=[539,140,539,927]   NOT MONOTONE  <- FLATTENS the rate
                                                                                factor across the
                                                                                symptom's own range
   V158             X=[12,400,2500,4000]  Y=[  0,539,539,927]   MONOTONE
```
⇒ **V157 destroys rate-proportionality exactly where the symptom lives — V72's error, which the
golden model explicitly warns against.** **V156/V157 are SUPERSEDED.**

### ✅ V158, PRICED AT THE MEASURED OPERATING POINT
The model records the in-burst rate as **`gp-0x6ac0` = 99 counts [94, 113]**, which sits on FactorE's
**first rising segment** — not flat at `Y[0]`. The dose must be evaluated there:
```
   FactorE(99) = 539 * (99 - 12) / (400 - 12) = 120
   FactorC     = Y[0] = 429                      (creep is below X[0] = 2240)
   product     = (429 * 120) >> 10 = 50          <- the model's own "BOTH dead zones opened ~50"
   requirement = ~43 [30, 60]                    <- V158 lands INSIDE it
   ceiling     = 512 at creep  =>  50 is 9.8 %, a 10.2x margin to V80's bang-bang
```
⇒ **V157's 123 is 2.4x the requirement; V156's 31 is below it. Only V158 is inside the band the
model priced.**
```
   0xD77DA / 0xD77EE  FactorC Y[0]  0 -> 429 / 426   (each mode's own Y[2])
   0xD780E / 0xD7822  FactorE X[0]  60 -> 12
   0xD7818 / 0xD782C  FactorE Y[1]  140 -> 539       (its own Y[2])
   10 payload bytes, 67/67, CRC 50/50
   image 42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf
   rwd   511c4a71a0196353b8ef9e570a285704568fc0ee2688d6f5379d3bffef459d3d
```
⊕ **FactorE `Y[0]` stays 0** — the dead zone is opened by moving the **AXIS**, not by lifting `Y[0]`
into a flat shape. **L1 and L3 asserted still flat unity.**
⊕ **`X[0] = 12` is not a free parameter.** The model's reasoning is preserved in the builder: a
firmware review flagged `X0 < 30 with Y1 > 300` as unflyable without telemetry, **12 is the TOP of
its own 6–12 band**, and the rate conversion is **biased LOW** (measured at the COLUMN, indexed at
the MOTOR, 18–22 Hz torsional). **Do not re-optimise it downward.**

### ⚠ ONE SUBTLETY MY OWN GATE CAUGHT
`FactorC Y[0] := Y[2]` gives **`[429, 234, 429, 908]` — also NON-MONOTONE**, a damping **dip between
35 and 60 km/h**, while the model's own text says `Y[0] := Y[1]` is the largest monotone lift.
⇒ **accepted deliberately, and asserted as such in the builder**: **FactorC is a SPEED SCHEDULE,
not the damping law** — a dip there is a schedule oddity, not a physics violation, unlike FactorE
where monotonicity **is** the rate-proportionality.
⇒ and the monotone alternative (`Y[0]:=Y[1]=234`) yields **product 28, BELOW the [30,60]
requirement** — which is **why** the model prescribes `Y[2]`. **The trade is now explicit rather
than implicit.**

### 🛑 THE LESSON
**`CLAUDE.md` says to read `docs/STATE.md`, the lineage, and the GOLDEN MODEL. I read the first two
and built two wrong doses of the right lever.** The golden model had the structure, the measured
operating point, the priced requirement and the shape rule the whole time.
⇒ **for any damper or lane work, read `eps_chain_lanes.py` FIRST.**

## ✅ **THE DAMPER CEILING READ FROM ITS OWN RECORDS — V157's 24 % CONFIRMED, 3.7x HEADROOM LEFT**
V134 cited the ceiling as *"`(&PTR_DAT_000c77a0)[mode]` = Y[512, 1024]"* without reading it per mode.
Read now, completing the four-factor damper picture:
```
   CEILING records (PTR_DAT_000c77a0), engaged modes    X[] on gp-0x6ac2, Y[] the limit
     m25  base 0xD709C   X=[300, 800]   Y=[512, 1024]
     m26  base 0xD70A8   X=[300, 800]   Y=[512, 1024]
     m27  base 0xD70B4   X=[300, 800]   Y=[512, 1024]
   fallback when gp-0x6ac2 >= 0x32C9:  cal(tp+0x7158) = cal(0xC6158) = 512
```
⇒ **below `gp-0x6ac2` = 300 the ceiling is 512; it rises to 1024 only by 800.** At creep
`gp-0x6ac2` is low, so **the operative ceiling is 512.**
⇒ **[EVIDENCE] V157's creep product of 123 is 24.0 % of the operative ceiling** — confirming the
builder's assertion **from the records themselves**, not from a citation.

### ⭐ THE PRE-COMPUTED NEXT DOSE — SO A GOOD RESULT IS NOT FOLLOWED BY GUESSWORK
```
   ceiling 512    max safe product at 90 %  =  460
   V156           product   31   =   6.1 %      L2_Y0 = 60,  L4_Y0 = 539
   V157           product  123   =  24.0 %      L2_Y0 = own Y[1] (234/233), L4_Y0 = 539
   NEXT (unbuilt)  product  225   =  44.0 %     L2_Y0 = own Y[2] (429/426), L4_Y0 = own Y[2] (539)
                                                 margin to ceiling 2.3x
```
⊕ **Both proposed values remain the tables' OWN knots** — no invented numbers, the same discipline
V156/V157 used.
🛑 **NOT BUILT, deliberately.** Two doses of this lever are already queued and **neither has
flown**; a third artifact adds nothing a pre-computed recipe does not. **If V157 reads directionally
right, this is the next step and it needs no new analysis.**

### ✅ THE DAMPER IS NOW FULLY CHARACTERISED
```
   product   = ((((clamp(gp-0x698a,1024) * L1 >>10) * L2 >>10) * L3 >>10) * L4 >>10)
   L1 torque [1024 x4] unity   L2 SPEED [0,234,429,908]   L3 angle [1024 x4] unity
   L4 RATE   [0,140,539,927]
   sign      from gp-0x6abe
   ceiling   LERP on gp-0x6ac2, X=[300,800] Y=[512,1024], fallback cal(0xC6158)=512
   gates     L2: gp-0x6a5e <= 0x7D00 and gp-0x67f4 == 1
             L4: gp-0x6ac0 < 0x32C9 and |gp-0x6abe| <= 13000
```
⇒ **every term, every gate, every ceiling in the base damper is now read from the image.** The only
two zero-valued knots are the two V157 opens.

## ✅✅✅ **THE DAMPER IS A FOUR-FACTOR CASCADE, NOT TWO — AND V157 IS VALIDATED BY IT**
The kit models the base damper as **`ch0 = FactorC(speed) x FactorE(rate) >> 10`**. Decompiling its
actual writer `FUN_00034350` (stores at `0x34730`/`0x34744`/`0x34752`) shows that is **incomplete**:
```c
   uVar7 = ((((clamp(gp-0x698a, 1024) * L1 >>10) * L2 >>10) * L3 >>10) * L4 >>10);
      L1 = LERP[0xC9CCC][mode]  on a torque quantity
      L2 = LERP[0xC9E9C][mode]  on gp-0x6a5e   VEHICLE SPEED
      L3 = LERP[0xC9DB4][mode]  on gp-0x6a10   STEERING ANGLE
      L4 = LERP[0xC9F84][mode]  on gp-0x6ac0   MOTOR RATE
   if (0 < gp-0x6abe) uVar7 = -uVar7;                      // sign from the rate
   then clamped by LERP[PTR_DAT_000c77a0][mode] on gp-0x6ac2   // the 512/1024 ceiling
```
⇒ **FOUR LERP factors and a clamped scalar, not two.** Any one of them being zero in the micro
regime would zero the product **regardless of what V156/V157 open** — so this had to be checked
before recommending them further.

### ✅ THE CHECK — EXACTLY TWO FACTORS ARE ZERO, AND V157 OPENS BOTH
```
   factor        engaged-mode Y knots                  gates at creep?
   L1 torque     [1024, 1024, 1024, 1024]   FLAT UNITY   NO -- pass-through
   L2 SPEED      [   0,  234,  429,  908]   Y[0] = 0     YES  <-- V157 opens (0xD77DA / 0xD77EE)
   L3 angle      [1024, 1024, 1024, 1024]   FLAT UNITY   NO -- pass-through
   L4 mot. RATE  [   0,  140,  539,  927]   Y[0] = 0     YES  <-- V157 opens (0xD7816 / 0xD782A)
```
⇒ **[EVIDENCE] only L2 and L4 have a zero first knot, and V157 opens EXACTLY those two.** L1 and
L3 are **unity at every knot** and can never zero the product.
⇒ **the full four-factor arithmetic reproduces the builder's dose exactly:**
`((((1024*1024)>>10)*234>>10)*1024>>10)*539>>10 = 123` — **the same 123 the V157 builder asserts.**
⇒ **V157 is correctly and completely targeted.** The record's two-factor model gave the right answer
**by luck**, because the two factors it omitted are unity.

### ⚠ CORRECTIONS TO THE RECORD
⊕ **"FactorC" is L2, a SPEED factor selected via the pointer table at `0xC9E9C`; "FactorE" is L4, a
MOTOR-RATE factor via `0xC9F84`.** They are **not** a bare pair — they are two of four cascaded LERPs.
⊕ **The record layout is `X[0]` at base+2 and `Y[0]` at base+10** (L3 uses +0xC/+0x14). I initially
compared the pointer-table entries (record **bases**) against V157's `X[0]` addresses and got
**"NOT FOUND" on all four** — a **2-byte** off-by-one that would have condemned a correct build.
**Caught by re-deriving the layout from the decompile rather than trusting the first comparison.**
⊕ **The ceiling V134 cites is `LERP[PTR_DAT_000c77a0][mode]` on `gp-0x6ac2`**, and the damper's
**sign comes from `gp-0x6abe`** — neither was in the kit's two-factor model.

### ⭐ WHAT THIS ADDS TO V157'S CASE
⊕ The two factors it opens are the **only** two that gate, so **nothing else in the cascade can
silently zero it** — the failure mode that made V134 inert cannot recur here.
⊕ The gating conditions around the cascade are also now explicit: L4's branch requires
**`gp-0x6ac0 < 0x32C9`** and **`|gp-0x6abe| <= 13000`**, and L2's requires **`gp-0x6a5e <= 0x7D00`**
and **`gp-0x67f4 == 1`** — all satisfied at creep.
⇒ **V157 remains the recommended build, now on a verified four-factor structure rather than an
incomplete two-factor one.**

## ✅✅✅ **FIVE INDEPENDENT METRICS CONVERGE ON ~1.1x — THE MEASUREMENT SIDE IS EXHAUSTED**
The last open objection to the small measured effect was that **band power is the wrong perceptual
quantity**: grinding is perceived as **roughness**, which tracks **MODULATION DEPTH**, and 7.8 Hz
sits in the fluctuation-strength range. Depth normalises to the **mean level**; share normalises to
the **envelope's own spectrum** — they can genuinely diverge. Tested.
```
   metric                routes    engaged/manual [95 % CI]   matched on (speed x |rate| RMS)
   depth 6-9 Hz              25    1.161 [1.049, 1.284]       <- EXCLUDES 1
   depth 26-31 Hz CONTROL    25    1.086 [0.912, 1.292]       <- control CLEAN
   share 6-9 Hz              25    1.106 [0.998, 1.273]
```
=> depth is **marginally the better metric** and its CI excludes 1, but the **band-specific advantage
over its own control is only 1.161/1.086 = 1.07x.**
=> **[EVIDENCE] the perceptual-metric hypothesis does NOT explain the gap** between the measured
effect and the reported severity.

### ⭐⭐ THE CONVERGENCE — EVERY INSTRUMENT AND EVERY METRIC AGREES
```
   CAN band share, median       1.12 [1.01, 1.27]      24 routes, controls clean
   CAN band share, p95 tail     1.10 [1.04, 1.24]      23 routes, controls clean
   CAN line prominence          1.17 [0.86, 1.27]      => <= ~2 % of RMS, positive control PASSED
   CAN modulation depth         1.16 [1.05, 1.28]      25 routes, control clean
   AUDIO envelope AM            ~1.00 (all 8 bands)     5 routes, all 8 controls clean
```
=> **five independent statistics, on two independent instruments, all land between 1.0 and 1.2 with
clean controls.** Nothing measurable from this vehicle accounts for *"massive, violent grinding."*
=> **[CONCLUDED] the measurement side is EXHAUSTED.** Not "we haven't found the right statistic" —
**five have been tried, including the perceptually correct one, and they agree.**

### 🛑 WHAT THAT MEANS, STATED PLAINLY
The only reading consistent with all of it is the one the kit already reached structurally: **the
mode is on the motor / rack / tyre side, and no channel this vehicle exposes observes it.** A
symptom that reads ~1.1x on every available instrument while being unmistakable to the driver is
**not a measurement failure to be solved with a better statistic — it is an observability limit.**
=> **the operator's ear is the instrument, and that is now supported by five converging negative
results rather than by resignation.**
=> **no further metric should be attempted on cached data.** The next informative bit is a drive.

