# STATE — living current state of the kit

## 🛑🛑 **V154/V155 SUPERSEDED — `0xC63A6` IS A STRUCK CELL; AND THE EIGHT COEFFICIENTS ARE READ**
Continuing the queue audit against the golden model. Two results.

### 🛑 V154/V155 MOVE A CELL THE MODEL EXPLICITLY STRUCK
> 🛑🛑 *"**BUT NO WEIGHT MAY BE MOVED**: gp-0x6b70 is a PID **REFERENCE THAT GETS SUBTRACTED**,
> not an aggregator addend, so a weight change's SIGN is not determined by the forward path alone
> ... Path 2 **IS A REAL CLOSED LOOP** ... its loop gain lives in **EIGHT float coefficients** ...
> **NEVER BYTE-READ BY ANY SESSION** ... => **GATE 2 CANNOT BE CERTIFIED. `0xC63A6` was struck on
> exactly this.**"*

⊕ **My justification was right open-loop, and the model says so**: *"the two sign(iVar6) factors in
the chain rule SQUARE TO +1 AND CANCEL -- the unknown sign of iVar6 does NOT matter open-loop."*
🛑 **The flaw: I reasoned OPEN-LOOP about a CLOSED loop** -- precisely what GATE 2 exists to catch.
=> **V154/V155 SUPERSEDED, `.rwd` renamed.** This is the **same class of error as V156/V157**: built
from the lineage, contradicted by the golden model.

### ✅ THE EIGHT COEFFICIENTS -- BYTE-READ FOR THE FIRST TIME
```
   tp+0x504C  0xC404C   0.000000e+00  float   <-- EXACTLY ZERO
   tp+0x5050  0xC4050   0.000000e+00  float   <-- EXACTLY ZERO
   tp+0x50BC  0xC40BC   3000  the knee      tp+0x50D4  0xC40D4   573  model pre-filter (applied x2)
   tp+0x50D0  0xC40D0    408  bilinear EMA  tp+0x50D6  0xC40D6   246  rate-term EMA   (applied x2)
   tp+0x50D2  0xC40D2   1020  K1            tp+0x50D8  0xC40D8  3686  sensor pre-filter(applied x2)
```
=> **[EVIDENCE] two of the eight are EXACTLY 0.0, in stock and V122 alike -- and they are the two
multiplying the HISTORY terms.** In `FUN_0003b8f6`:
```c
   fVar14 = *(float*)(tp+0x5050) * gp-0xc9c8  +  fVar14 * fVar19  +  fVar15 * *(float*)(tp+0x504c)
          =        0.0 * gp-0xc9c8            +   10.0 * fVar19   +  fVar15 * 0.0
          =  10.0 * fVar19                                     (tp+0x5048 = 10.0)
```
=> **that three-tap structure is a PURE GAIN of 10.0 -- both memory taps are DEAD.**
=> **GATE 2 is NOT closed** (the RAM LERP's local slope is still unextracted, and `FUN_000389ec` has
defeated two attempts), **but the unknown loop gain now has TWO FEWER LIVE TERMS than the model
assumed**, and the eight values are on the record for the first time.

### ⭐ THE PATTERN ACROSS THIS AUDIT
```
   V156 / V157   mis-shaped   non-monotone FactorE, repeats V72's flatten-to-relay error
   V154 / V155   struck cell  0xC63A6, GATE 2 uncertifiable
   V158          CORRECT      built to the golden model's own measured prescription
```
=> **three of the builds I recommended this session were built from `BUILD-LINEAGE` rather than the
golden model, and two of them were wrong.** `CLAUDE.md` names the model as required reading; the cost
of skipping it was four superseded artifacts.

## ⭐⭐⭐ **THE AUTHORITY COMPLAINT HAS A SPECIFIC MECHANISM — AND THE OPERATOR DRIVES ON ITS KNEE**
Auditing the remaining queued builds against the golden model (the V158 lesson) surfaced the
authority answer, which was **already in the record** and which this session had not connected.
```
   the LKAS AUTHORITY COLLAPSE CURVE   0xE547C / 0xE5404 / 0xE52FC / 0xE5284, mode 7
   takes authority  254 -> 0  across raw driver torque  2240 -> 2560
   VIRGIN on all 90 images
   the OPERATOR's measured median override torque = 2235 = ONE COUNT BELOW the first knot
```
=> **[EVIDENCE] he drives on the knee of the authority collapse.** Any small increase in his input
takes authority from 254 toward 0 — which is exactly what *"LKAS authority"* would feel like when it
vanishes unpredictably under a push.
=> **this is a SECOND, DISTINCT mechanism from the +-4096 command rail** found earlier this session.
Both are real, both live at creep, and they are not the same thing:
```
   the +-4096 rail       the command hits its 13-bit PROTOCOL max, 6.4 % of frames at 2-8 km/h
   the collapse curve    authority is CUT BY THE FIRMWARE as driver torque crosses 2240
```

### 🛑 THE RULE THAT BLOCKS THE OBVIOUS FIX — AND IT IS A GOOD RULE
The golden model states it as a hard constraint:
> 🛑🛑 *"**Honda collapses authority BECAUSE the driver is pushing. Any change must be
> MONOTONE-NON-INCREASING: never more authority than stock at any torque.**"*

=> **moving the knee up** (so authority holds past 2240) **gives MORE than stock between 2240 and
the new knee => it violates the rule.**
=> the rule exists for a real reason: **raising this curve makes the car fight the driver harder
during an override.** That is a safety property, not a tuning preference.
=> **[DECISION] NOT proposed.** Like `0xC61BC`, this is an **operator decision about how hard the
car may resist him**, not an engineering call I should make.

### ⚠ AND IT WILL NOT HELP THE GRINDING
> 🛑 *"**NOT a 6-9 Hz lever — refuted five ways**; it drives the ~0.5-1 Hz SURGE."*

=> the collapse curve is a **surge** mechanism, not a ratchet mechanism. **Fixing it would address
LKAS authority and nothing else.**

### ☑ ALSO RE-CONFIRMED: `0xC64B8` IS DEAD, DO NOT RE-PROPOSE
The same memory records `0xC64B8` (V37's `0x70`->`0xFF`) as **structurally true, behaviourally
empty**: at mode 7 **both arms deliver 0 everywhere the branch could fire**, because all four curve
records clamp to `Y[last] = 0` above `X[last]` = 80 or 112, **below the gate's 113**. **Stock and V37
are bit-identical on this car.**
=> it *looks* compelling — non-stock for 66 builds, sitting exactly at high driver pushback — **and
it is empty.**

### ✅ WHERE THE THREE COMPLAINTS NOW STAND, MECHANISM BY MECHANISM
```
   grinding / ratchet   a mechanical resonance; firmware reaches EXCITATION and LOOP PHASE only
                        => V158, the golden model's own damper prescription, UNFLOWN
   LKAS authority       TWO mechanisms, both identified:
                          (a) the command rails at its 13-bit protocol max (6.4 % at 2-8 km/h)
                          (b) the collapse curve cuts authority above driver torque 2240,
                              and the operator's median override is 2235
                        => BOTH are barred from the obvious fix by safety rules the kit adopted
   peak command osc.    = (a) above, measured: sustained one-sided saturation
```
=> **every complaint now has a named mechanism.** Two of the three are blocked not by ignorance but
by **deliberate safety constraints**, and lifting either is **the operator's call to make
explicitly.**

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

## ✅✅ **THE RATCHET IS NOT EPISODIC IN BAND SHARE — THE TAIL LOOKS LIKE THE MEDIAN**
A flaw in my own method: every matched analysis this session took the **MEDIAN** over engaged
windows, and the kit's own characterisation says the ratchet appeared in **44 of 46 windows** on one
route — i.e. it may be **EPISODIC**, and a median would wash an episodic phenomenon out entirely.
**Tested by re-running the matched contrast at the TAIL.**
```
   statistic   6-9 Hz [95 % CI]        26-31 Hz CONTROL        23 routes, matched on
   median      1.067 [0.966, 1.226]    0.987 [0.870, 1.264]    (speed bin x |rate| RMS bin)
   p75         1.073 [0.954, 1.193]    1.082 [1.005, 1.263]
   p90         1.160 [0.993, 1.256]    1.022 [0.802, 1.317]
   p95         1.100 [1.039, 1.243]    1.065 [0.886, 1.276]    <- 6-9 Hz EXCLUDES 1
   p99         1.110 [0.963, 1.241]    1.024 [0.928, 1.224]
```
⇒ **[EVIDENCE] the tail is indistinguishable from the median.** If the ratchet were concentrated in
rare episodes, **p95/p99 would show a much larger contrast than the median.** They do not —
**1.10 vs 1.07.**
⇒ **the engagement effect is a UNIFORM ~10 % elevation of the 6-9 Hz band, not an episodic
concentration.** The kit's *"44/46 windows engaged"* figure was about detecting a **LINE**, a
different statistic from band share — **the two are not in conflict.**
✅ **AND IT FIRMS THE EFFECT UP**: at **p95 the 6-9 Hz CI EXCLUDES 1** (1.039–1.243) while its
control spans 1, converging with the independent median-based estimate **1.12 [1.01, 1.27]**.
⇒ **CONVERGED RESULT: engagement adds ~10 % to the 6-9 Hz band — real, small, robust across central
AND tail statistics, with controls clean at every percentile.**

⊕ **This also closes the last live objection to the ≤ ~2 % of RMS line bound**: that bound was
derived from a median-based prominence contrast, and the natural challenge was *"an episodic symptom
would be diluted."* **It would not be — the tail behaves like the centre.**

## ✅✅ **THE AUDIO AM NULL IS NOW CLEAN — AND THAT IS THE THIRD ARTEFACT KILLED BY A CONTROL**
Last turn's audio envelope-AM test was underpowered **and its 60–100 Hz control failed** (0.804,
excluding 1), because windows were matched on **creep speed only**. Re-ran it with the same
stratification that fixed the CAN-side analysis: **(speed bin x |rate| RMS bin)**.
```
   audio band     6-9 Hz AM [95 % CI]        20-28 Hz CONTROL         control status
   15-21          1.020 [0.767, 1.125]       0.931 [0.834, 1.318]     clean
   28-40          0.958 [0.854, 1.070]       1.081 [0.836, 1.390]     clean   <- was 1.309
   40-60          1.048 [0.878, 1.062]       0.882 [0.456, 1.511]     clean
   60-100         0.869 [0.840, 0.989]       1.044 [0.767, 1.298]     clean   <- control FIXED
   100-300        1.013 [0.815, 1.091]       1.057 [0.777, 1.268]     clean
   300-1000       1.004 [0.884, 1.675]       0.875 [0.719, 1.090]     clean
   1000-3000      1.038 [0.779, 1.426]       0.788 [0.473, 1.029]     clean
   3000-8000      1.058 [0.894, 1.362]       1.049 [0.897, 1.086]     clean
```
✅ **ALL EIGHT CONTROL BANDS NOW SPAN 1** — the stratification fix worked.
✅ **[EVIDENCE, clean controls] there is NO engagement-conditional 6–9 Hz AM in the audio, in any
band.** The previously "most suggestive" **28–40 Hz cell fell from 1.309 to 0.958** — it was **pure
matching artefact.**
⚠ 60–100 Hz reads **0.869 [0.840, 0.989]**, excluding 1 *below*. With **eight bands tested**, one
marginal exclusion is expected by chance; **not claimed.**
⇒ **the ratchet does not AM-modulate the cabin audio in a way engagement changes.** Combined with
the CAN-side bound (**≤ ~2 % of RMS**), **both available instruments now return clean nulls on
symptom A**, which is itself consistent with the mode being **motor/rack-side and unobservable**.

## 🛑🛑 **THE PATTERN: THREE TIMES THIS SESSION, THE CONTROL KILLED THE EFFECT**
```
   engagement contrast, 6-9 Hz     2.8x   ->  1.12 [1.01, 1.27]   when MATCHED on speed x activity
   post-disengage persistence      1.29x  ->  ratio 0.911         when a CONTROL BAND was added
   audio envelope AM, 28-40 Hz     1.309  ->  0.958               when matched on activity too
```
⇒ **every one of these was plausible, specific, and pointed at a real mechanism.** Each survived
until its control was computed, and none survived after.
⭐ **This is [[feedback-run-the-control-before-the-measurement]] earning its place three separate
times in one session, on three different instruments (CAN band power, CAN envelope, audio envelope).**
⇒ **RULE, stated for the record: on this kit, an uncontrolled engaged-vs-manual ratio is worth
nothing.** Operating point differs systematically between the arms — engaged is creep and steady,
manual is faster and more active — and that difference is **larger than every effect measured this
session.** **Compute the control first, or do not compute the number.**

## ⚠ **AUDIO ENVELOPE DEMODULATION FOR THE RATCHET — NEW METHOD, NO SIGNAL, IMPERFECT CONTROL**
The kit uses audio only for **symptom B's band power**. But **a ratchet is an impulse train**, so it
would not appear *at* 7.8 Hz in audio — it would appear as **7.8 Hz AMPLITUDE MODULATION of the audio
envelope**. That had never been tried. Tried it.

### ✅ THE INSTRUMENT EXISTS ALREADY
The audio caches store **per-band envelopes** sampled at **62.5 Hz** (`wide` x 10 bands with
`wide_lab`; the older `a20_100 ... a4k_7k` format is 100 Hz but only on r81/r82).
=> Nyquist **31.25 Hz** — 6–9 Hz is comfortably resolved; the control had to move to **20–28 Hz**.
=> **five routes carry substantial creep-engaged audio**: r9e 12,952 · r96 9,803 · r97 5,495 ·
r85 5,238 · ra4 4,312 samples.

### ⚠ THE RESULT — NO SIGNAL, AND THE CONTROL IS NOT CLEAN
```
   audio band     6-9 Hz AM [95 % CI]        20-28 Hz CONTROL
   15-21          0.971 [0.951, 1.142]       1.150 [0.822, 1.701]
   28-40          1.309 [0.978, 1.627]       0.977 [0.743, 1.313]
   40-60          1.110 [0.874, 1.238]       0.764 [0.392, 1.719]
   60-100         1.134 [0.912, 1.254]       0.804 [0.626, 0.923]   <-- CONTROL EXCLUDES 1
   100-300        1.020 [0.897, 1.269]       0.935 [0.686, 1.094]
   300-1000       0.969 [0.878, 1.121]       0.986 [0.810, 1.233]
   1000-3000      1.031 [0.872, 1.364]       0.957 [0.715, 1.183]
   3000-8000      1.030 [0.899, 1.190]       0.961 [0.782, 1.732]
```
=> **every 6–9 Hz CI spans 1 — no detectable ratchet AM in any audio band.**
🛑 **BUT ONE CONTROL BAND FAILS**: 60–100 Hz reads **0.804 [0.626, 0.923]**, excluding 1. The
windows were matched on **creep speed only, not on steering activity**, so residual confounding
remains.
=> **[NOT A CLEAN NULL]** — this is an **underpowered test (5 routes) with an imperfect control**,
and it must not be cited as evidence that the ratchet is acoustically silent.

### ⭐ WHAT IS WORTH KEEPING
⊕ **The METHOD**: audio-envelope AM demodulation is a legitimate, previously-unused instrument for
an impulse-train symptom, and the caches already contain what it needs. **Most suggestive cell:
the 28–40 Hz audio band at 1.309 [0.978, 1.627]** — not significant, but it is where a
mechanical ratchet's carrier would plausibly sit.
⊕ **What would close it**: more routes carrying audio **with matched creep engaged AND manual
exposure**, and matching on **steering activity** as well as speed — the same stratification the
CAN-side analysis needed. **Only 5 of ~230 routes have usable creep-engaged audio at all.**
=> **audio capture on every future drive is what makes this instrument usable** — already the
standing request for symptom B, and now for symptom A as well.

## 🛑 **"GRINDING CONTINUES AFTER DISENGAGING" — NO BAND-SPECIFIC PERSISTENCE ON THE BUS**
The operator's V133 report included *"which continues after disengaging."* That is a **structural**
claim — the command is gone, so the mechanism would have to have **memory** — and it had never been
tested. Tested now, on **139 creep-ish disengage events across 76 routes**, by aligning on the
engaged→manual edge and tracking the 6–9 Hz Hilbert envelope of `tq` normalised to its own engaged
baseline.

### ⚠ THE UNCONTROLLED VERSION LOOKED LIKE A RESULT
```
   engaged -3..0 s   1.000        after 2..3 s   1.225
   after 0..1 s      1.293        after 3..5 s   1.119
   after 1..2 s      1.212        (IQR 1.6-1.9 throughout)
```
⇒ read alone, *"the ratchet band stays ~25 % elevated for 5 s after disengage"* — which would have
supported the operator's report and pointed at a filter state with memory.

### ✅ THE CONTROL BANDS KILL IT
```
   band                  median    [95 % CI, 4000-draw bootstrap]
   6-9 Hz  (ratchet)      1.377    [0.918, 1.588]     CI INCLUDES 1
   26-31 Hz CONTROL       1.051    [0.948, 1.288]
   32-38 Hz CONTROL       1.117    [1.025, 1.249]

   RATIO 6-9 / 26-31      0.911    [0.795, 1.132]     BELOW 1, CI spans 1
```
⇒ **[EVIDENCE, with controls] there is NO band-specific persistence.** The post-disengage elevation
appears in the **control bands too**, so it is **general activity — the driver taking over — not
ratchet memory.** The band-specific ratio is **0.911**, i.e. if anything the ratchet band rises
*less* than the controls.

### ⭐ THE METHODOLOGICAL POINT, WHICH IS THE DURABLE PART
**The same 139 events read as *"grinding persists 25 % after disengage"* or *"no effect at all"*
depending ONLY on whether the control band is computed.** This is
[[feedback-run-the-control-before-the-measurement]] demonstrated on a fresh question, and it is worth
keeping because the uncontrolled number was **plausible, specific, and would have pointed at a real
mechanism** (a filter state with memory) that does not exist.

### 🛑 WHAT IT DOES **NOT** SETTLE
⚠ **This does not refute the operator's report.** Two readings survive:
```
   (a) the persistence is not real as a 6-9 Hz phenomenon on the column
   (b) it IS real but NOT OBSERVABLE ON THIS BUS
```
⇒ **(b) is the reading consistent with everything else this session established** — the mode is
**motor/rack/tyre side, which no channel on this bus observes**, and engagement adds **≤ ~2 % of RMS**
as a 7.8 Hz line on the column. **A symptom the bus can barely see engaged will not be visible
decaying after disengage either.**
⇒ **[NOT CLOSED] the operator's ear remains the only instrument for this**, and the honest record is
that the bus test came back null **with its control passing**, which is a statement about the
instrument as much as about the symptom.

## ✅✅✅ **CONTROL IS FULLY ACTIVE WHERE THE COMMAND RAILS — THE CREEP-AUTHORITY CHAIN IS CLOSED**
The memory's *"0 % control-active below 2 mph"* was measured when `0xC62EA` = 320. **It is 0 on
current builds**, so the measurement had to be redone. Redone — **227 routes, 1.88 M engaged
frames** — and it settles the authority question.
```
   STEER_STATUS while ENGAGED     distribution: {0: 1,901,564 | 3: 14,538 | 4: 92}

   speed band       engaged frames   STEER_STATUS=3     duty
   0-2   km/h             179,135           10,511    5.868 %
   2-8   km/h             175,039                0    0.000 %   <-- where the command rails 6.4 %
   8-16  km/h             470,173                0    0.000 %
   16-25 km/h             547,927                0    0.000 %
   25-40 km/h             506,512                0    0.000 %
```
⇒ **[EVIDENCE] `STEER_STATUS = 3` is EXACTLY ZERO at 2–8 km/h**, the band where the command rails
**6.4 %** of engaged frames.
⇒ **the lockout removal WORKED** — control-active is continuous through the whole creep band, and the
old *"0 % below 2 mph / 88 % at 3–4 mph"* figures are **obsolete for every build since**.

### ⭐⭐ WHAT THIS SETTLES — THE RAILING IS NOT A FIRMWARE DROPOUT
```
   lockout 0xC62EA          already 0            => not gating
   STEER_STATUS at 2-8 km/h exactly 0 duty       => control is FULLY ACTIVE
   the command rails anyway 6.4 % of frames      => the demand genuinely exceeds the field
```
⇒ **[EVIDENCE] the authority shortfall at creep is NOT a control dropout, a lockout, or a gating
failure. The firmware is fully engaged and openpilot is asking for more than a 13-bit signed field
can carry.**
⇒ **the ONLY remaining explanation is TORQUE PER COUNT** — which is the **gain `0xC6CD0`** (frozen
in both directions) or the **±15360 setpoint clamp `0xC61BC`** (virgin, binding unknown).
⇒ **every other hypothesis for creep authority loss is now eliminated by measurement.**

### ✅ TWO SIDE RESULTS WORTH KEEPING
⊕ **`STEER_STATUS = 3` survives only at 0–2 km/h (5.868 %)** — i.e. at standstill, where the
`gp-0x68b3` standstill bypass and the remaining conjuncts govern. **Expected, and not a concern:**
LKAS steering at 0–2 km/h is not a regime the operator is complaining about.
⊕ **`STEER_STATUS = 4` occurs 92 times in 1,878,786 engaged frames (0.005 %)** — the state-4
governor ratchet that V42 fixed. **The fix is holding across the whole corpus**, which is an
independent confirmation of [[reference-accord-state4-governor-ratchet]] and of
[[accord-v42-ratchet-fix-lost-since-v53]] being restored.

⇒ **The probe on `0xC61BC` is now the last standing question about creep authority**, and it is the
only one whose answer could break the authority/grinding tension.

## 🛑🛑 **THE CREEP-AUTHORITY CHAIN IS CLOSED — LOCKOUT ALREADY PULLED, NEXT CONJUNCT NOT A CAL**
All three complaints live at **2–8 km/h**, and the kit's most on-target lever for that band is the
**low-speed steer lockout**. Followed it to the end. **Both links are closed, and the record needed
two corrections.**

### 🛑 LINK 1 — THE LOCKOUT IS **ALREADY REMOVED** ON THE FLYING BUILD
```
   0xC62EA  low-speed lockout threshold   stock 320 (4.995 km/h)   V122 = 0   => NO LOCKOUT
   across 157 images: {0: 108, 320: 49}
```
⇒ **[EVIDENCE] `0xC62EA` = 0 on V122 — the lockout has been off for most of the arc.**
⇒ **the 6.4 % command railing at 2–8 km/h is NOT caused by the low-speed lockout.** That lever is
**spent, not available**, and must not be re-proposed.

### ✅ LINK 2 — THE MEMORY'S OWN PRE-REGISTERED NEXT SUSPECT, AND IT IS **NOT CAL-REACHABLE**
`accord-low-speed-lockout-window-c62ea` pre-registered the follow-up: *"If a lowered `0xC62EA`
doesn't work, `gp-0x69aa` is the next suspect."* **It doesn't work — it is already 0 — so the suspect
is activated.** Read at its site (`0x29000–0x29200` **byte-identical stock vs V122**):
```asm
   0x290fc  ld.hu -0x69aa, gp, r14      ; the governor Q15 derate
   0x2910c  ori   0x8000, r0, r9        ; 0x8000 built as an IMMEDIATE
   0x29110  cmp   r9, r14
   0x29112  bh    0x29138               ; UNSIGNED HIGHER -> the FAILURE path (STEER_STATUS = 3)
```
🛑 **The 0x8000 threshold is a HARD-CODED IMMEDIATE (`ori 0x8000, r0, r9`), NOT `cal(0xC63F2)`.**
`0xC63F2` = 32768 is read at `0x28ECE`, a **different site** with a different role.
⇒ **[EVIDENCE] the governor-derate conjunct is NOT reachable by any calibration.** Changing it would
need an in-place instruction edit. **The pre-registered next suspect is closed as a cal lever.**

### ⚠ CORRECTION 1 — THE COMPARISON IS `<=`, NOT `==`
The memory records the conjunct as **`gp-0x69aa == 0x8000`**. The instruction is `cmp r9,r14` then
**`bh`** (branch if unsigned HIGHER) to the failure path.
⇒ **the passing condition is `gp-0x69aa <= 0x8000`, not `== 0x8000`.** Any derate BELOW unity still
passes; only values ABOVE 0x8000 fail. **[CORRECTED in the record.]**

### ⚠ CORRECTION 2 — I HIT THE OFF-BY-0x1000 TRAP, AND CAUGHT IT
I first wrote `tp+0x73F2` as **`0xC73F2`**. `tp = 0xBF000`, so it is **`0xC63F2`**.
⇒ **that is the SIXTH recorded recurrence** of the trap `CLAUDE.md` calls out (it lists five).
⇒ caught by anchoring against the memory's own stated value (32768) — the wrong address read **14**,
the right one reads **32768**. **The anchor-against-a-known-value discipline is what caught it, and
it is worth keeping in front of every session.**

### ✅ WHAT REMAINS OF THE CREEP-AUTHORITY QUESTION
```
   0xC62EA  lockout threshold        ALREADY 0 -- spent
   gp-0x69aa governor derate         threshold is a HARD-CODED IMMEDIATE -- not a cal
   gp-0x67fe substate == 2           a state, not a cal
   gp-0x69ae within +-0x4000         not yet examined
   5-channel validity test           not yet examined
   0xC61BC  setpoint clamp +-15360   VIRGIN, binding UNKNOWN  <-- the only cal candidate left
```
⇒ **of the AND-chain that gates control-active at creep, the only remaining CAL-reachable candidate
is `0xC61BC`** — which is exactly the cell the `iVar31 ≥ 5482` probe would settle.
⇒ **the probe is now the last cal-reachable question in the entire creep-authority chain.**

## 🛑🛑🛑 **ALL THREE COMPLAINTS ARE CREEP PHENOMENA — AND SPEED-SCHEDULING THE GAIN IS DEAD**
Tried to **make** a new lever rather than find one: **schedule the gain by speed** — high where
authority saturates, low where grinding lives — which would break the authority/grinding tension
outright. **It only works if the two live at different speeds. They do not.**
```
   WHERE THE COMMAND RAILS  (engaged frames, all routes pooled, 1.6 M frames)
   speed band       engaged frames     railed    rail duty
   0-2   km/h            140,277          546      0.389 %
   2-8   km/h            156,381        9,956      6.367 %   <-- THE PEAK
   8-16  km/h            438,274        3,836      0.875 %
   16-25 km/h            498,164          842      0.169 %
   25-40 km/h            372,168           34      0.009 %

   CREEP (0-8 km/h)  3.540 %      HIGHWAY (>=16 km/h)  0.101 %      ratio 35x
```
⇒ **[EVIDENCE] authority saturation is a CREEP phenomenon** — **6.4 % of engaged frames at
2–8 km/h**, falling **35x** by highway speeds.
⇒ **🛑 SPEED-SCHEDULING THE GAIN IS DEAD AS A LEVER.** There is no band where authority is needed
and grinding is absent — they are **the same band**. A gain that is high where the command rails is
high exactly where the grinding is. **Lever class closed before any build was spent on it.**

### ⭐ BUT IT UNIFIES THE THREE COMPLAINTS
```
   peak command oscillation   the command rails at its 13-bit max, 6.4 % of frames at 2-8 km/h
   LKAS authority             saturated in that same 2-8 km/h band
   grinding / ratcheting      symptom A's micro regime (1-13 deg/s) and symptom B's <10 mph
                              acoustic excess are BOTH in that same band
```
⇒ **[EVIDENCE] all three of the operator's complaints are the SAME OPERATING POINT: engaged creep,
roughly 2–8 km/h.** They have been treated as three problems for the whole arc; they are three
observations of one regime.
⇒ **any real fix must act AT CREEP**, and a fix that only works above 16 km/h addresses none of them.

### ✅ WHICH SHARPENS THE FLIGHT ORDER — V157 IS THE ONLY BUILD TARGETED AT THE RIGHT PLACE
```
   V157 / V156   act ONLY at creep      FactorC opens below 35 km/h AND FactorE below 12.73 deg/s
                                        => the damper is non-zero EXACTLY in the 2-8 km/h band
   V153 / V152   act at ALL speeds      observer poles are not speed-gated
   V149 / V150   act at all speeds      switch removal, not speed-gated
   V139          acts at all speeds     pump arms, not speed-gated
   V155 / V154   act at all speeds      inertia-lane weight, not speed-gated
```
⇒ **V157 is the ONLY queued build whose effect is confined to the band where all three symptoms
live.** Every other lever spends its effect mostly outside it.
⇒ **This is now the strongest argument for V157 first**, and it is an argument from measurement
rather than from mechanism.

## ⚠ **THE RAILED-COMMAND NATURAL EXPERIMENT IS UNDERPOWERED — RECORDED SO IT IS NOT RE-RUN**
A rail episode freezes the command at ±4096, so it is a **natural experiment**: if the ratchet
persists while the command is constant, the command is not driving it. Ran it. **The cached data
cannot support it.**
```
   tq 6-9 Hz share, RAILED / FREE windows, matched on speed bin, 1.3 s windows
   route   n_rail  n_free   6-9 Hz ratio   26-31 Hz "control"
   r75          4     316        1.73            0.31
   r77          9     465        2.21            0.32
   r9e          3     180       19.05            0.04
```
🛑 **ONLY 3 ROUTES QUALIFY, with 3–9 railed windows each**, and the ratios span **1.73 to 19.05**.
🛑 **AND THE STATISTIC IS COMPOSITIONAL** — band *share* is normalised to 1–45 Hz, so 6–9 Hz rising
**forces** the control band down arithmetically. **The control here is NOT independent evidence**,
which is precisely the failure mode `feedback-run-the-control-before-the-measurement` warns about.
⇒ **[NOT CLAIMED] anything from these numbers.**
⊕ **Directionally** all three exceed 1 while the command is frozen, which is consistent with the
ratchet not being command-driven — and that is **already established independently** by V87 (the
7.8 Hz line has prominence **12.9 in the COLUMN but 4.0 = chance in the COMMAND**). **The experiment
adds nothing V87 did not already give.**
⇒ **What would close it: rail episodes are ~0.78 % of engaged frames and only 28 % of routes have
any. This needs a drive that DELIBERATELY sustains saturation** (a long steady curve at creep) — and
even then it only re-confirms a settled point. **Low value; recorded so it is not attempted again.**

## ⚠ **THE RAILED COMMAND IS SUSTAINED ONE-SIDED SATURATION, NOT A RAIL-TO-RAIL LIMIT CYCLE**
Follow-up to the ±4096 rail finding: **is the railing a limit cycle?** Tested, and the answer is
**no — and the test that would have said yes is underpowered, which I am recording rather than
dressing up.**
```
   route     n_eng    neg%   pos%   rail-to-rail alternations   median gap   implied freq
   r78       56230   0.70%  0.32%              6                  1.25 s       0.401 Hz
   r85       12000   1.23%  4.00%              4                  5.82 s       0.086 Hz
   r96       35048   0.37%  0.70%              4                  1.84 s       0.272 Hz
   r96s11     6000   2.18%  4.10%              4                  1.84 s       0.272 Hz
   pooled: 12 intervals, median 1.84 s, quartiles 1.37 / 1.84 / 2.23
```
🛑 **ONLY 4 OF 114 ROUTES EVER SWING RAIL-TO-RAIL, and they yield 12 intervals total with a 4.7×
spread in implied frequency (0.086–0.401 Hz).**
⇒ **[NOT CLAIMED] a limit-cycle frequency.** Twelve intervals across four routes that disagree by
4.7× is not a measurement; quoting "0.27 Hz" from it would be exactly the kind of number this kit
has had to retract before.

### ✅ WHAT IT DOES ESTABLISH — AND IT SHARPENS THE EARLIER RESULT
**The command overwhelmingly rails on ONE side and STAYS there** — up to **399 frames ≈ 4 s**
continuous — rather than alternating between rails.
⇒ **the operator's "peak command oscillation" is, in the data, SUSTAINED ONE-SIDED AUTHORITY
SATURATION**, not a controller limit cycle between limits.
⇒ **that is consistent with, and strengthens, the authority diagnosis**: openpilot asks for the
maximum the field can carry and holds it, because the plant is not delivering enough per count.
⇒ **it also means no "oscillation-damping" lever applies** — there is no cycle to damp. **The fix
is torque-per-count, which is the gain (frozen) or `0xC61BC` (binding unknown).**

⊕ **This turn produced a refinement, not a breakthrough**, and the analysis remains where it was:
**eleven verified builds unflown, and the binding constraint is a drive.**

## 🛑🛑🛑 **THE LKAS COMMAND RAILS AT ±4096 — “PEAK COMMAND OSCILLATION” IS AUTHORITY SATURATION**
The operator names **peak command oscillation** in every instruction and this kit had never measured
it. **It is measured now, from data already on disk, and it ties all three complaints together.**

### ✅ THE MEASUREMENT — 114 ROUTES, 1.37 M ENGAGED FRAMES
`co_tqcan`, the LKAS torque command **as sent on the bus**, engaged frames only:
```
   overall rail duty                    0.783 %
   routes that EVER hit the rail        32 of 114   (28 %)
   worst routes        r85s15 8.633 % | r75s10 6.901 % | r96s11 6.283 % | r73 5.470 % | r85 5.233 %
   LONGEST CONTINUOUS RAIL              399 frames  =  ~4 SECONDS at 100 Hz   (r9e)
   |max| on every railing route         EXACTLY 4096
```
⇒ **±4096 = 2^12 — a 13-bit signed field. That is the CAN signal's own PROTOCOL MAXIMUM.**
⇒ **[EVIDENCE] the command is pinned at the largest value the wire can carry, for up to four
seconds at a time, on 28 % of routes.** A signal that pins at a rail and comes off **is** peak
command oscillation. **The complaint is real, it is measured, and it is authority saturation.**

### 🛑🛑 WHY THIS IS HARD — THE THREE COMPLAINTS SHARE ONE KNOB
```
   1. the command field CANNOT carry more than +-4096          (protocol, not firmware, not openpilot)
   2. it is ALREADY railed up to 8.6 % of frames / 4 s at a time
   3. => more steering authority requires more TORQUE PER COMMAND COUNT, i.e. the firmware GAIN
   4. => but the gain is the grinding knob: MEASURED 6x = 1.13 dB, 8x = 2.24 dB acoustic excess
        and vibration scales m^1.74 while authority scales only m^0.88
```
⇒ **authority and grinding are in DIRECT tension through a single cell (`0xC6CD0`), and the command
field is already at its rail.** That is why authority has been stuck for the whole arc.
⇒ **🛑 raising the gain to 8× buys authority SUB-linearly (m^0.88) and buys grinding
SUPER-linearly (m^1.74) — it is the wrong direction, and it fails the operator's own condition.**
⊕ **No openpilot-side fix is available** — the standing instruction forbids it, **and it would not
help anyway: the field itself cannot represent a larger number.**

### ⭐⭐ THE ONE ESCAPE — AND IT IS THE PROBE ALREADY SPECIFIED
If the firmware's own setpoint clamp **`0xC61BC` / `0xC61BE` = ±15360 BINDS**, then raising it
delivers **more torque for the same command count** — i.e. **authority WITHOUT touching the gain, and
therefore WITHOUT the grinding penalty.**
⇒ **that is the only path off the gain tension that this firmware offers**, and it is exactly what
the `iVar31 ≥ 5482` rung would settle in one drive.
⇒ **the probe's value has gone UP**: it no longer serves only the authority complaint, it is the
**sole test of whether the authority/grinding tension can be broken at all.**
⚠ **[UNRESOLVED] whether `±15360` binds** — unchanged, and still not guessable statically because
`iVar31` is a 16-assignment decompiler temporary.
🛑 **Raising it remains a SAFETY decision for the operator** — it increases the maximum torque LKAS
can apply against the driver.

### ✅ WHAT IS NOW ANSWERED, AND WHAT IS NOT
```
   peak command oscillation   ANSWERED: the command rails at its 13-bit protocol max +-4096,
                              28 % of routes, up to 8.6 % duty, episodes to ~4 s.  MEASURED.
   LKAS authority             DIAGNOSED: limited by torque-per-count, and the only cal that
                              raises it without the grinding penalty is 0xC61BC IF it binds.
   grinding / ratcheting      A = mechanical resonance (V157 is the best lever, unflown)
                              B = broadband, unreachable by calibration
```
⊕ **This is the first measured answer to the operator's THIRD complaint**, and it came from cached
data — no drive, no build.

## ✅ **THE AUTHORITY CLAMP NOW HAS A CONCRETE THRESHOLD — BUT THE STATIC SHORTCUT FAILED**
I tried to settle *"does the ±15360 clamp bind?"* **without** spending a cave edit — the bricking
class — on a probe. **The shortcut failed, and that is worth recording as clearly as a success.**

### ✅ WHAT THE ATTEMPT DID ESTABLISH
The setpoint LERP is reached through a **pointer table at `0xCB994`**, indexed by mode:
`iVar41 = *(int *)(0xCB994 + iVar23)`, with `X` at `+2..+10` and `Y` at `+0xC..+0x14`. Following all
six pointers and decoding the records:
```
   0xE4360  X=[0,68,112,136,208]   Y=[205,461,614,696,696]   Ymax=696
   0xE4378  X=[0,68,112,136,208]   Y=[266,532,696,696,696]   Ymax=696
   0xE4390  X=[0,48,128,160,208]   Y=[205,410,717,717,717]   Ymax=717
   0xE43A8  X=[0,68,112,136,208]   Y=[248,512,645,696,696]   Ymax=696
   0xE43C0  X=[0,68,112,136,208]   Y=[205,461,614,696,696]   Ymax=696
   0xE43D8  X=[0,48,128,160,208]   Y=[205,410,717,717,717]   Ymax=717
```
⇒ **[EVIDENCE] the LERP output is bounded at 717.** With `uVar33 = (iVar31 × LERP) >> 8` clamped
to `±cal(0xC61BC)` = 15360:
```
   the clamp binds  <=>  iVar31 x 717 >> 8  >=  15360  <=>  iVar31 >= 15360 x 256 / 717 = 5482
```
⭐ **That is a single, concrete, testable threshold**, and it is a **cheaper probe than measuring the
clamp itself**: one comparison of `iVar31` against a constant, instead of instrumenting a clamp.

### 🛑 WHY IT DID **NOT** CLOSE STATICALLY
`iVar31` is **not one semantic variable** — the decompiler reuses it across **16 assignments** in
`FUN_00028ea6`. The one dominating the clamp is:
```c
   iVar31 = (int)(short)((ushort)!bVar4 - (ushort)bVar4) * (int)(short)uVar25;   // +-uVar25
   iVar31 = iVar31 * 0x20 - uVar35;                                              // x32, minus uVar35
```
⇒ bounding it needs `uVar25` **and** `uVar35`, each with their own provenance.
⇒ **[UNRESOLVED, and I am not going to guess it]** — `iVar31 × 32` could plausibly exceed 5482 by a
wide margin or not reach it, and **a wrong static bound here would be exactly the class of error the
kit records as its most expensive**: a mis-read that reads as a *fact* and propagates.
✅ **The probe remains the correct instrument.** The attempt was worth making — it cost no build and
it produced the threshold — but it does not replace the measurement.

### ✅ WHAT THIS CHANGES ABOUT THE PROBE
```
   BEFORE   instrument the clamp: capture uVar33 and compare against cal(0xC61BC)
   NOW      one rung:  iVar31 >= 5482     <- a comparison against a CONSTANT
            duty 0.0000 => the clamp CANNOT bind => 0xC61BC closes exactly as 0xC61B2/B4 did
            duty > 0    => it binds; the dose is real and the operator can decide knowingly
```
⇒ simpler rung, same answer, and it reuses the comparator pattern V98 already flew.
🛑 **Still NOT a fix and still needs the operator's call before any dose** — raising an authority
clamp **increases the maximum torque LKAS can apply against the driver**, unlike every other queued
lever, which only ever reduces.

## ⭐⭐⭐ **THE LKAS AUTHORITY LIMITER IS LOCATED — AND IT IS VIRGIN ON ALL 157 BUILDS**
The operator names **LKAS authority** in every single instruction, and this session had not served
it. It is now located, and the result is uncomfortable: **the kit has been moving the wrong clamps.**

### ✅ WHERE THE LIMIT ACTUALLY IS
`FUN_00028ea6`, upstream of the 6x gain multiply — a **symmetric ±clamp on the setpoint product**:
```c
   uVar13 = LERP(...);                                  // the setpoint LERP
   iVar26 = iVar31 * (uVar13 & 0xffff);
   uVar33 = iVar26 >> 8;
   uVar35 = *(ushort *)(unaff_tp + 0x71bc);             // 0xC61BC = 15360
   ...  clamp uVar33 to  +uVar35 / -uVar35  ...         // a SYMMETRIC +-15360 clamp
```
`0xC61BE` is its twin (the same shape, lines 1190–1203). **7 and 8 readers respectively.**

### 🛑🛑 THE KIT HAS BEEN ADJUSTING THE CLAMPS ITS OWN RECORD CALLS INERT
```
   cell        role                          values across 157 build images
   0xC61BC     THE setpoint clamp            {15360: 157}   <-- VIRGIN, never touched
   0xC61BE     its twin                      {15360: 157}   <-- VIRGIN, never touched
   0xC61B2     "fwd-path clamp"              {3072:43, 4096:11, 2048:81, 1024:21, 512:1}
   0xC61B4     its twin                      {3072:43, 4096:11, 2048:81, 1024:21, 512:1}
```
And the record already says of the pair that HAS been moved:
> **`0xC61B2` / `0xC61B4` — INERT, 0 % of the effect.** *Setpoint LERP-clipped to 15360 upstream of
> the gain ⇒ 81.5 % of rail on every build since V14.*

⇒ **[EVIDENCE] the cells the kit has moved across 5 distinct values on 157 builds are the ones it
knows are inert, and the cell the record names as the actual upstream limit has NEVER been touched.**
⇒ **`0xC61BC` / `0xC61BE` are the authority lever, and they are virgin.**

### 🛑 WHAT IS **NOT** ESTABLISHED — AND WHY I AM NOT BUILDING IT
⚠ **[UNRESOLVED] whether ±15360 actually BINDS.** The clamp sits on `(iVar31 × LERP) >> 8`, so it
binds only when that product reaches 15360. **The record's *"81.5 % of rail"* is consistent with
either reading** — a setpoint that saturates there, or a LERP whose own maximum is 15360 making the
clamp redundant. **No probe has ever measured its duty.** Raising an inert clamp does nothing.
🛑🛑 **AND THIS IS A SAFETY DECISION, NOT AN ENGINEERING ONE.** Raising a steering authority
clamp **increases the maximum torque LKAS can apply against the driver.** That is categorically
different from every other lever in this queue, all of which only ever *reduce* something.
⇒ **[DECISION] NOT BUILT. This needs the operator's explicit direction**, and it should be preceded
by a probe, because raising a clamp that does not bind is pure risk for zero benefit.

### ✅ THE SAFE NEXT ARTIFACT — a duty probe, not a dose
A cave rung reading **`|uVar33| ≥ cal(0xC61BC)`** converts the question into one number from one
drive, at **zero authority change**:
```
   duty 0.0000  =>  the clamp NEVER binds  =>  it is NOT the authority limit; look upstream at the
                    LERP itself, and 0xC61BC is closed the way 0xC61B2/B4 were
   duty > 0     =>  the clamp IS the binding limit, its dose is meaningful, and the operator can
                    then decide knowingly whether to raise it
```
⊕ Same class as V148, V98, V100 — **zero calibration bytes, cave only, an instrument not a fix.**
⊕ **This is the first genuinely NEW question in several turns**, and unlike the rest of the queue it
addresses the operator's **second** stated complaint rather than the first.

## ✅✅ **V157 BUILT — THE 4× DOSE OF V156, AND `MEMORY-PART4` SPLIT**
V156 puts the damper's creep product at **31 = 6.1 %% of the bang-bang ceiling**, which may simply be
too small to feel. V157 is the **same lever, same four cells, 4× the dose** — built so the choice
is available rather than laddered.
```
   V156   FactorC Y[0] 0 -> 60        FactorE Y[0] 0 -> 539    product  31   6.1 %% of ceiling
          rwd bc070cba9e195231337070e57cf228c4ac126f5e09dbc8e2c2e7f68aca37c24d   6 B, 60/60
   V157   FactorC Y[0] 0 -> OWN Y[1]  FactorE Y[0] 0 -> 539    product 123  24.0 %% of ceiling
          (234 on m26, 233 on m27)                             4.2x margin to 512
          rwd 65021b6d996ab1107d9dcf7a15667e1b321e2578a33e49572d27e92893785145   6 B, 62/62
```
⊕ **Both doses are the tables' OWN neighbouring knot values, not inventions** — V157 sets each
mode's FactorC `Y[0]` to **that mode's own `Y[1]`**, so the first segment becomes **FLAT** from 0 to
`X[1]`=3840 instead of ramping from zero, and FactorE `Y[0]` to its own `Y[2]`.
🛑 **The V80 distinction that makes this safe**: V80's catastrophe was FactorC **FLAT 566 across
ALL FOUR knots**. V157 flattens **only the FIRST segment** and leaves **`Y[1..3]` byte-identical**,
so **the high-speed ramp is untouched** — asserted in the builder, not argued.
⊕ **FLY ONE OF V156 / V157, not both.** Given the operator's *"I just want the best possible
results"*, **V157 is the better first flight**: V156's 31 counts has a real chance of being
inaudible, and V157 still holds a **4.2× margin** to the ceiling.

### ✅ HOUSEKEEPING — `memory/MEMORY-PART4.md` SPLIT AT 199.5 KB
```
   before   PART4  199.5 KB, 147 entries
   after    PART4  100.7 KB,  88 entries      PART5   99.3 KB,  59 entries
   integrity: 88 + 59 = 147, and the entry SETS are equal  => zero lost
```
⇒ **`CLAUDE.md` repointed: "PAGINATED IN FOUR" → "PAGINATED IN FIVE"**, naming `MEMORY-PART5.md`
so no agent reads a truncated index. PART4 carries a pointer to PART5 at its tail.

## ✅✅✅ **V156 BUILT — THE DAMPER REACHES THE MICRO REGIME FOR THE FIRST TIME**
A lightly-damped resonance (**ζ 0.017–0.036**) sits in a regime with **no added damping at all**,
and the reason is that `ch0 = (FactorC(speed) × FactorE(rate)) >> 10` is a **PRODUCT OF TWO DEAD
ZONES**. Below `X[0]` a LERP returns `Y[0]`, and **both `Y[0]` are ZERO**:
```
   FactorC  X = [2240,3840,5120,8960] = [35,60,80,140] km/h   Y[0]=0  => ZERO at ALL creep speeds
   FactorE  X = [  60, 400,2500,4000]                          Y[0]=0
            X[0]=60 <-> the recorded 12.73 deg/s dead zone => ~0.212 deg/s per count
            => the MICRO REGIME (1-13 deg/s) sits ENTIRELY BELOW X[0], exactly where Y[0] applies
```
⇒ measured **zero on 100 % of the micro regime** and 95.91 % of engaged frames.

### ⭐ NEITHER FACTOR ALONE CAN OPEN IT — AND THE KIT TRIED BOTH, SEPARATELY
```
   V134                    FactorC Y[0] 0 -> 60      MEASURED INERT at creep.  Its OWN header:
                           "FactorE Y[0] = 0 below this build raises FactorC Y[0] into a
                            product that is still zero there."
   FactorE X[0] 60 -> 12   WITHDRAWN before flight: "structurally vacuous at creep
                           (FactorC Y[0] = 0 below 34.97 km/h zeroes the product)"
```
⇒ **a product of two dead zones cannot be opened from one side. BOTH `Y[0]` must move together —
and that build had never existed.** V156 is it.

### ✅ THE BUILD
```
   mode 26   0xD77DA FactorC Y[0]  0 -> 60      mode 27   0xD77EE FactorC Y[0]  0 -> 60
   mode 26   0xD7816 FactorE Y[0]  0 -> 539     mode 27   0xD782A FactorE Y[0]  0 -> 539
   6 payload bytes, 60/60, CRC 50/50
   image 21a259ffeb0649bd390383f6280a512c9a9aa869cc4c92f2a601ff67a24e085f
   rwd   bc070cba9e195231337070e57cf228c4ac126f5e09dbc8e2c2e7f68aca37c24d
```
⊕ **Addresses resolved this session, two ways agreeing.** Walking the record block at stride
`0x14` shows it is **not** a mode-indexed array of one family but **three FactorC records then three
FactorE records** (`0xD77BE/D2/E6` then `0xD77FA/80E/822`, modes 25/26/27) — which puts **FactorE
m26 Y[0] at `0xD7816` and m27 at `0xD782A`**, and independently **matches the lineage's own
"FactorE m27 = `0xD7822`" anchor.**
⊕ **RULE 7 mode-proof**: `V106B.ENGAGED_MODES = (26, 27)`, `MANUAL_MODES = (24, 25)` — read from
the builder, not assumed. V134's 26/27 targeting was correct.

### 🛑 THE DOSE IS SIZED BY V80's CATASTROPHE
**V80 set FactorC FLAT 566, passed the per-mode ceiling, turned the damper into a BANG-BANG RELAY
and produced THE WORST GRINDING IN THE KIT'S HISTORY.** That bounds the dose:
```
   creep product = (60 x 539) >> 10 = 31        ceiling = 512      => 6.1 % of it
```
⊕ `FactorC Y[0] = 60` is **V134's own value**, chosen and safety-checked there.
⊕ `FactorE Y[0] = 539` is **FactorE's own `Y[2]`** — a value already in the table, not an invention.
⇒ **31 counts of damping where there are currently EXACTLY ZERO.** Small in absolute terms, but
**0 → non-zero is a change of KIND**, and the ladder above is bounded by 512 if the direction reads
right.

### ✅ WHY THIS RESPECTS THE OPERATOR'S STANDING CONSTRAINT
*"Increasing mass and friction should not be our primary approach … IF IT COMES AT THE COST OF max
steering angular velocity and acceleration."*
⇒ this build adds damping **only where `FactorE Y[0]` applies, i.e. BELOW 12.73 deg/s.** Above that
FactorE is **byte-unchanged**, so **maximum angular velocity and acceleration are untouched.** The
cost lands **entirely inside the regime that has the symptom.**

### 🛑 WHAT IS NOT ESTABLISHED
⚠ **[BELIEF] that 31 counts is enough to feel.** No dose-response exists because **no build has
ever had a live damper here** — that is precisely what makes it worth flying, and also why a null
would be uninformative about the mechanism rather than about the lever.
⊕ **`0xC63A0`, the damper's WEIGHT, is HELD at stock 1024.** It was 2048 on V72–V76 and is
**EXONERATED** of V74's fault (that was `0xC407E`), but it **multiplies whatever this build admits**,
so moving both at once would not be single-variable. **It is the natural second dose.**
⚠ `diff_vs_flown` reports **MULTI-VARIABLE** (6 bytes) — **expected**: four cells, but **two factors
× two engaged modes of ONE product**, and the product is the lever. **Do not reduce it.**

## 🛑🛑🛑 **`0xC4936` IDENTIFIED — A PWM HARDWARE-TIMING CAL. DO NOT TOUCH IT.**
`0xC4936` was the **only calibration operand anywhere in the FOC PI/SVPWM region** (0.25 cals/KB)
and the last open candidate for a symptom-B lever. **Identified, and it is a hard stop.**

### ✅ WHAT IT IS
Its single reader `0x6C486` sits inside **`FUN_0006c446`, a PERIPHERAL-INITIALISATION routine** that
writes the motor timer/PWM block. Region **byte-identical stock vs V122**, so this reads true for the
flying build:
```c
   _DAT_ffffcc58 = 0x1388;                                 // 5000   -- period-like
   _DAT_ffffcc5c = *(ushort *)(tp + 0x5936) * 2 + 0x50;    // cal(0xC4936)=250  ->  580
   _DAT_ffffcc6c = 0x50;   _DAT_ffffcc70 = 0x50;
   _DAT_ffffccb0 = _DAT_ffffccb4 = _DAT_ffffccb8 = 0x1428; // THREE IDENTICAL -> 3-phase compares
   _DAT_ff809220 = 0x801;  _DAT_ff809224 = 0x408;  _DAT_ff809228 = 0x515;
   _DAT_ff81c084 = 0x700;  _DAT_ff81c088 = 0x100;          // peripheral space
```
⇒ **[EVIDENCE] `0xC4936` is NOT a control-law gain. It is a PWM / timer HARDWARE CONFIGURATION
parameter**, written once at init into the inverter's timer block, as `2 × cal + 0x50`.
⊕ Three identical compare registers beside a period-like `5000` is the signature of a **3-phase PWM
generator** — consistent with the golden model's `TSG20` attribution.

### 🛑🛑🛑 WHY IT IS A HARD STOP — A FAILURE MODE WORSE THAN BRICKING
A `2×cal + offset` field in a 3-phase PWM timer block is most plausibly a **DEAD-TIME or phase
offset** register.
⇒ **Shortening inverter DEAD TIME causes SHOOT-THROUGH: both transistors of a leg conduct
simultaneously and the power stage is DESTROYED.**
⇒ **That is strictly worse than bricking the ECU.** This kit has bricked three times (V24, V27,
V48B) and recovered every time, because a bricked ECU is reflashable. **A destroyed inverter is
not.**
⇒ **[DECISION] `0xC4936` MUST NOT BE CHANGED, at any dose, for any reason short of a Honda service
document stating what the field is.** It is **virgin at 250 across all 155 images**, and it stays
that way.
⭐ **Recorded prominently because the trap is attractive**: a future session scanning for levers will
find *"a VIRGIN cal, single reader, inside the FOC region, never touched by 155 builds"* and read
that as opportunity. **It is the opposite.** Honda left the drive stage uncalibratable **on purpose**;
this one cell is not an oversight.

### ✅ SYMPTOM B — THE LAST CANDIDATE IS CLOSED, SO THE ANALYSIS IS COMPLETE
```
   1. engaged LKAS forward path       NO active switching nonlinearity (gate DORMANT, clamp INERT)
   2. cal(0xC6194)=3 in TASK 1, 1 kHz ~2 s full-scale => already smooth
   3. drive stage                     0.25 cals/KB => no calibration surface
   4. 0xC4936, the sole exception     PWM HARDWARE TIMING => must not be touched
```
⇒ **[CONCLUDED] symptom B is not reachable by any calibration edit this kit may safely make.**
The remaining explanation — the motor and inverter driven harder, ripple and commutation rising
with command amplitude, superlinear acoustics giving **m^1.74** — stands as **BELIEF**, and the only
cal that moves it is the **LKAS gain**, frozen in both directions.
⇒ **The falsifier stated last session is now down to ONE item**: a broadband source that is
engagement-conditional but **NOT** proportional to command amplitude. The forward path is traced end
to end and contains none.

### ⭐ A BYPRODUCT: THE PWM CARRIER CONFIGURATION IS NOW LOCATED
The golden model records **[OPEN] the PWM carrier frequency**. Its configuration is written in
`FUN_0006c446` — `_DAT_ffffcc58 = 5000` (period-like) with the 3-phase compares at `_DAT_ffffccb0/
b4/b8 = 0x1428`. **The register block is located; the absolute Hz still needs the clock tree** (the
kit records PCLK = 40 MHz, which would put a 5000-count period at 8 kHz edge-aligned or 4 kHz
centre-aligned — **arithmetic, NOT verified against the clock configuration**).
⇒ **pointer recorded for `eps_chain_delivery.py`; the [OPEN] is narrowed, not closed.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑 **THE SIGN-AGREEMENT GATE IS DORMANT WHEN ENGAGED — LEAD CLOSED, TWO SELF-CORRECTIONS**
Last turn I flagged a sign-agreement gate on the LKAS command path as the best-shaped symptom-B
mechanism, marked the behavioural reading **BELIEF**, and said *"read all of `FUN_00028ea6` before
proposing anything."* Done. **The lead collapses, exactly where it was flagged.**

### ✅ WHAT THE FULL DECOMPILE SHOWS — the test is NESTED INSIDE AN ENABLE GATE
```c
   if ((cVar15 == '\x01') && (*(char *)(unaff_gp + -0x6806) == '\0')) {    // <-- ENABLE GATE
       if ( (deadband test on cal(0xC61B8)) || (iVar34 * *(short *)(gp - 0x6b30) < 1) ) {
           iVar23 = 0;  goto LAB_0002a1ee;                                  // zero the command
       }
   }
   iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf);                     // otherwise pass
   LAB_0002a1ee:
   ...
   *(short *)(unaff_gp + -0x6b30) = (short)iVar23;                           // stores the OUTPUT
```
with `cVar15 = *(char *)(unaff_tp + 0x74a3)` = **`cal(0xC64A3)`**.

### 🛑 SELF-CORRECTION 1 — THERE **IS** A CAL ON THE GATE
I wrote *"no cal on the gate — `mul`+`cmp`+`bgt`, hard-coded."* **Wrong.** `0xC64A3` is a byte
enable on the whole block. **But it is `1` in stock and in ALL 155 build images**, so it is not a
free lever and disabling it is untested territory.

### ⭐ SELF-CORRECTION 2 — THE GATE IS **DORMANT WHEN ENGAGED**, PROVED BEHAVIOURALLY
With `cal(0xC64A3)` permanently 1, the gate's activity rests entirely on **`gp-0x6806 == 0`**
(37 loads / 20 stores — a state-machine flag in the `0x29xxx` region).
**The latch reading I flagged is CORRECT, and that is exactly what closes the lead:**
```
   the block stores iVar23 back to gp-0x6b30, so once the command is zeroed,
   prev = 0  =>  iVar34 * 0 = 0 < 1  =>  the test fires AGAIN  =>  a SELF-HOLDING ZERO
```
⇒ **if this gate were active while engaged, the FIRST zero-crossing of the command would latch
LKAS at zero PERMANENTLY.** It demonstrably does not — the operator steers on LKAS every drive.
⇒ **[EVIDENCE, behavioural] `gp-0x6806 ≠ 0` whenever LKAS is steering ⇒ the deadband and the
sign-agreement test are BOTH INACTIVE WHEN ENGAGED.**
⇒ **THE SIGN GATE IS NOT SYMPTOM B'S SOURCE. LEAD CLOSED.**
⊕ It also independently re-confirms [[reference-accord-pregain-deadband-c61b8]] — the 102-count
pre-gain deadband sits in this same dormant block, which is *why* it was filed ELIMINATED.

### 🛑 WHAT THIS IMPLIES FOR SYMPTOM B — AND IT IS NOT ENCOURAGING
The engaged LKAS forward path is now traced end to end with **no switching nonlinearity active**:
```
   command -> [deadband + sign gate: DORMANT when engaged] -> x gain -> x polarity -> >>15
           -> clamp cal(0xC61B4) (record: INERT) -> gp-0x6b30
```
⇒ **no discontinuity, no relay, no slew limit on the engaged command path.**
⇒ the gain-laddered broadband excess (**1× −0.04 · 4× 0.84 · 6× 1.13 · 8× 2.24 dB**) therefore
does **not** originate in a command-path discontinuity.
⇒ **[BELIEF, and the honest reading] what remains is the motor/inverter being driven harder** —
current ripple and commutation noise rising with command amplitude, with a superlinear acoustic
response giving the observed **m^1.74**. **That is physics, not a defect, and no cal reaches it
except the LKAS gain, which is frozen in both directions.**
⇒ **🛑 SYMPTOM B MAY BE IRREDUCIBLE IN FIRMWARE.** Stating it plainly is more useful than
generating another build that cannot touch it. **If that is wrong, the disproof would be a broadband
source that is engagement-conditional and NOT proportional to command amplitude — none has been
found in the forward path.**

## ⭐⭐ **A SIGN-AGREEMENT GATE SITS DIRECTLY ON THE LKAS COMMAND PATH — UPSTREAM OF THE GAIN**
Chasing symptom B's broadband source into the forward path found a **hard switching nonlinearity on
the LKAS command itself.** Disassembled from `0x2A1C0`; the region is **structurally identical to
V122** (only the 2 gain-cal bytes at `0x2A1F0-1` differ, `746c`→`7cd0`), so this reads true for the
flying build.
```asm
   0x2a1ca  ld.hu 0x71b8, tp, r8      ; cal(0xC61B8) = the pre-gain DEADBAND (102)
   0x2a1ce  subr  r0, r8              ; -deadband
   0x2a1d0  cmp   r8, r9
   0x2a1d2  bge   0x2a1e2             ; inside the deadband -> ZERO
   0x2a1d4  ld.h  -0x6b30, gp, r13    ; the PREVIOUS stored output
   0x2a1d8  mov   r9, r6
   0x2a1da  mul   r13, r6, r0         ; r6 = prev x current
   0x2a1de  cmp   r0, r6
   0x2a1e0  bgt   0x2a1e6             ; product > 0  -> pass through
   0x2a1e2  mov   0x0, r9             ; ELSE -> FORCE THE COMMAND TO ZERO
   0x2a1e6  mul   r14, r9, r0  / sar 0xf / sxh
   0x2a1ee  ld.h  <gain>, tp, r7      ; 0xC6CD0 on V122, 0xC646C on stock (V57 moved it)
   0x2a206  st.h  r9, -0x6b30, gp     ; stored back -> becomes next tick's `prev`
```
⇒ **[EVIDENCE] the LKAS command is FORCED TO ZERO whenever its sign disagrees with the previous
output's sign.** A signal zeroed on sign disagreement has **step discontinuities**, which is
precisely a broadband generator.
⇒ **⭐ AND THE GATE IS UPSTREAM OF THE GAIN MULTIPLY** (`0x2a1e2` precedes `0x2a1ee`), so the
**discontinuity amplitude scales with the gain** ⇒ **broadband ∝ gain**, which is the shape symptom B
shows (measured ladder 1× −0.04 · 4× 0.84 · 6× 1.13 · 8× 2.24 dB).
⊕ It is **engagement-conditional by construction** — there is no LKAS command when disengaged —
matching *stock does not fire, we do.*

### 🛑 WHAT I WILL NOT ASSERT — AND WHY NOBODY SHOULD BUILD ON THIS YET
**[UNRESOLVED] it READS as though it could latch.** If `prev` ever becomes 0 then `prev × current`
is 0, which fails the strict `> 0` test, forcing 0 again — a self-holding zero. **LKAS demonstrably
works**, so one of these must be true and I have not established which:
```
   (a) the SECOND store to gp-0x6b30 at 0x2A900 resets it on another path   (2 stores exist)
   (b) r14 / r6 are not what this 48-byte window implies
   (c) an entry branch (0x2a1c8 bgt -> 0x2a1d4) bypasses the deadband leg and changes the state
```
🛑 **Read the WHOLE of `FUN_00028ea6` before proposing anything here.** This is exactly the
*decompile-first* rule: I formed this claim from a 48-byte assembly window, which is the method the
kit has recorded as its most expensive mistake generator. **The instruction sequence is EVIDENCE;
the behavioural reading is BELIEF.**

### ⚠ AND THERE IS NO CAL ON THE GATE ITSELF
The sign test is `mul` + `cmp r0` + `bgt` — **hard-coded, no calibration operand.** Only the
**deadband** `0xC61B8` = 102 gates entry, and the record already files it
([[reference-accord-pregain-deadband-c61b8]], *"ELIMINATED — fixed 102-count deadband"*).
⇒ **removing or softening the sign gate would be an in-place instruction edit** — the class that
bricked V24, V27 and V48B — **and it is NOT proposed.**
⇒ **[NEXT STEP, cheap and safe] read `FUN_00028ea6` in full and settle the latching question.**
If it does not latch, this is the best-shaped symptom-B mechanism found so far; if it does, my
reading is wrong and the finding collapses.

### ✅ AND `0xC6194` IS CLOSED AS A SYMPTOM-B LEVER
`FUN_00026c80`'s **only caller is `FUN_0002214a` = TASK 1, the confirmed 1 kHz task.**
⇒ `cal(0xC6194)` = 3 counts/tick at **1 kHz** = 3000 counts/s, against a state clamped at
±cal(`0xC6192`)=2048 / ±cal(`0xC6198`)=3072 ⇒ **full-scale slew ≈ 2 s.**
⇒ **that path is ALREADY heavily smoothed and cannot be a broadband source. CLOSED.**
⊕ **This also softens my flag from last turn**: the memory's operative claim is *"no live
**LKAS-specific** slew limit"*, and this limit is on the **assist-arbitration sum**, not the LKAS
command ⇒ **the memory's claim stands**; only its *"output ×0"* phrasing mismatches the code.

## 🛑🛑 **GHIDRA'S `code.bin` IS THE *STOCK* IMAGE — EVERY DECOMPILE THIS SESSION WAS OF STOCK**
Chasing symptom B I hit a Python-vs-Ghidra disagreement and adjudicated it. **Both tools were
right; they were reading different images.**
```
   at 0x2A1EE:   Ghidra says  ld.h 0x746c, tp, r7   ->  tp+0x746C = 0xC646C
                 V122 bytes   25 3f d0 7c           ->  tp+0x7CD0 = 0xC6CD0
```
⇒ Ghidra's loaded program is `.../ghidra_project/code.bin`, **the STOCK dump** — and stock reads
`0xC646C` because **V57 is exactly the build that decoupled the forward reader onto `0xC6CD0`.**
The record predicted this ([[reference-accord-c646c-shared-gain-not-lkas-only]]); the tools agreed
all along.
✅ **THE SCAN METHOD IS VINDICATED** — the `reg1 == tp` filter reproduced the lineage's
independently-recorded *"sole reader `ld.hu 0x73ac,tp,r13` @`0x38202`"* for `0xC63AC`, and here it
read the V122 byte correctly where the stale program did not.

### ✅ WHICH OF THIS SESSION'S DECOMPILES SURVIVE — CHECKED, NOT ASSUMED
```
   FUN_0003b8f6  the PLANT MODEL   0x3B8F6-0x3BC30   IDENTICAL stock vs V122  (0 bytes)  VALID
   FUN_00038148  the ACTUAL arm    0x38148-0x38400   IDENTICAL stock vs V122  (0 bytes)  VALID
   FUN_0003aa2c  the AGGREGATOR    0x3AA2C-0x3AC60   DIFFERS   (1 byte  -- Lever B 0x3AA96)
   FUN_000352b4  the NOTCH         0x352B4-0x35C00   DIFFERS   (4 bytes)
```
⇒ **the two functions this session's structural conclusions rest on are byte-identical**, so the
`|model| × sat(angle)` correction and the signum-relay refutation **both stand.**
🛑 **STANDING RULE, ADD TO THE DECOMPILE SKILL: Ghidra holds STOCK. Before trusting any decompile
for a BUILD, diff that function's byte extent stock-vs-target in Python.** A cal that moved between
stock and the target (V57's `0xC646C`→`0xC6CD0`, V88's `0x3AA96`) will silently read wrong.

## ⚠ **A RECORDED CLAIM LOOKS WRONG: `0xC6194` IS NOT OBVIOUSLY "DEAD"**
[[reference-accord-lkas-only-rate-limiter-c6194]] says *"`0xC6194` is DEAD calibration — output ×0;
no live LKAS-specific slew limit exists."* Decompiling its reader's function, **`FUN_00026c80`**
(the 11-slot request-array processor, region `0x27500-0x27800` **byte-identical stock vs V122**),
shows `0xC6194` used as a **live ± slew step** on the state `gp-0x3d6c`:
```c
   iVar11 = *(int *)(gp - 0x3d6c);                          // the PREVIOUS value -- slew state
   ... uVar42 = cal(0xC6194)=3 + iVar11 ;                   // step UP   by <= 3
   ... iVar11 = iVar11 - cal(0xC6194)=3 ;                   // step DOWN by <= 3
   *(int *)(gp - 0x3d6c) = iVar11;                          // stored back
   iVar13 = *(int *)(gp - 0x3d80) + iVar11 + uVar42;        // -> gp-0x6b4a / gp-0x6b4c
```
⊕ the **×0 the memory refers to is `0xC6196` = 0**, a *different* cell, and it applies only in the
**`gp-0x6a62 > 0x7d00`** branch — not to `0xC6194` unconditionally.
⊕ `gp-0x6b4c`/`gp-0x6b4a` are the **DOMINANT** lanes of the observer sum (gated ±10240), so a slew
limit here is on a **major** path.
🛑 **[UNRESOLVED — DO NOT BUILD ON IT YET] the CALL RATE of `FUN_00026c80` is unknown to me.**
At 3 counts/tick and 1 kHz the path is **already** slew-limited to ~3.4 s full-scale, which would
make it far too smooth to be symptom B's broadband source; at a slow task rate the same cal is a
meaningful lever. **Resolve the task rate before proposing any dose.**
⇒ **flagged, NOT overturned** — the memory may be describing a different code path or a downstream
×0 I have not found. **But its blanket “no live LKAS slew limit exists” does not match this code.**

### ✅ WHAT THE FORWARD PATH ACTUALLY LOOKS LIKE (symptom B context)
```
   0x2A1E6  mul r14,r9,r0  /  sar 0xf  /  sxh        the command
   0x2A1EE  ld.h  0x7cd0,tp,r7                       the 6x gain      (STOCK reads 0x746c)
   0x2A1F2  ld.b -0x6752,gp,r13  /  mulh r7,r13      x polarity (-1)
   0x2A1F8  ld.hu 0x71b4,tp,r16                      the clamp 3072   (INERT per the record)
   0x2A1FE  mul r13,r11,r0  /  sar 0xf               >> 15
   0x2A206  st.h r9,-0x6b30,gp
```
⇒ **`(command × gain × polarity) >> 15`, clamped, stored — and NO SMOOTHING ANYWHERE on this
path.** Since openpilot's `STEER_DELTA` is not rescaled for gain, **each 1-count command step
becomes a 6-count firmware step at 6×** ⇒ the staircase amplitude scales with gain, which is the
right shape for a gain-laddered broadband excess (observed exponent **1.74**, so a linear staircase
term alone does not fully explain it).

## 🛑🛑🛑 **CORRECTION — AUDIO IS A WORKING INSTRUMENT, AND THERE ARE TWO SYMPTOMS**
Last turn I concluded *"no statistic can rank these builds."* **That was overstated, and the kit's
own record contains the counter-example.** The bound I proved is real but **narrower** than I wrote
it: it applies to **CAN-derived statistics at 6–9 Hz.**

### 🛑 THE OPERATOR'S REPORTED MODES ARE ABOVE EVERY CAN NYQUIST
```
   steering angle channel   Nyquist  50.0 Hz
   427 / 0x1AB              Nyquist  24.9 Hz     (measured from ab_t1ab this session)
   the reported low-speed grinding      ~90-110 Hz and above
```
⇒ **no CAN channel can observe it at all** ⇒ **audio is the only instrument**, and the kit built one.

### ✅ THE ACOUSTIC LADDER — IT DISCRIMINATES, WITH CONTROLS
Eleven routes, **fixed 90–110 Hz band, THREE adjacent control bands**, engaged-minus-manual,
matched speed, <10 mph:
```
   STOCK is the ONLY route that FAILS its null      -0.30 dB, p = 0.890
   9 of 10 gain-modified builds CLEAR theirs        p < 0.001
   broadband level vs LKAS gain:   1x -0.04 |  4x 0.84 |  6x 1.13 |  8x 2.24  dB
```
⇒ **[EVIDENCE] the engaged acoustic excess IS ours, and it LADDERS WITH GAIN.**
⚠ **The control bands rise equally** ⇒ after removing them the 100 Hz residual is ≤0 on 6 of 10
routes ⇒ **the excess is BROADBAND, not a mode.** (The kit's own recorded lesson: *a narrow-band
acoustic claim needs ADJACENT CONTROL BANDS; the third-octave caches cannot provide them.*)

### ⭐⭐ THIS ANSWERS THE OPERATOR'S OWN 8x CONDITIONAL, BY MEASUREMENT
His standing instruction: *"just go to 8x IF you decide to increase LKAS gain"* and *"if you're
going to increase gain make sure we don't get even more oscillation and grinding."*
```
   6x (what V122 and every queued build runs)   1.13 dB engaged acoustic excess
   8x                                           2.24 dB      => ~2x the excess
```
⇒ **[DECISION] 8x FAILS HIS OWN CONDITION. Do not propose it.** The conditional is now closed by an
11-route measurement rather than by argument.
⊕ And the trade is quantified in the lineage: **vibration scales m^1.74 while authority scales only
m^0.88** ⇒ raising gain buys authority **sub**-linearly and buys grinding **super**-linearly.
🛑 The converse remains barred by [[accord-4x-lkas-gain-is-the-frozen-variable]] — **do NOT lower
it either**; that memory is a standing instruction and this does not overturn it.

### 🛑🛑 THERE ARE **TWO** SYMPTOMS AND I HAVE BEEN CHASING ONLY ONE
The record states it plainly: the low-speed grinding is **"a DIFFERENT mechanism from the
command-gated 7.8 / 20–26 Hz pair — do not assume one fix covers both."**
```
   SYMPTOM A   the ~7.8 Hz ratchet        CAN-visible (barely), mechanical, motor/rack side,
                                          Q 14-29; engagement adds <= ~2 % of RMS  (this session)
   SYMPTOM B   the low-speed GRINDING     AUDIO-ONLY, above every CAN Nyquist, BROADBAND,
                                          scales as gain^1.74; STOCK does not fire, we do
```
⇒ **Every build reasoned about this session — V149–V155 — targets SYMPTOM A.** Their loop-pole,
switch and lane-weight arguments say nothing about B.
⇒ **✅ SYMPTOM B IS THE ONE WITH A WORKING INSTRUMENT AND A MEASURED DOSE-RESPONSE**, and it is
the one the operator describes as *grinding*. **It deserves the next build, and it is under-served
by this session's queue.**

### ✅ WHAT THIS CHANGES ABOUT THE NEXT DRIVE
⇒ **THE DRIVE MUST CAPTURE AUDIO.** Without it the drive can only be scored by ear; with it the
90–110 Hz + adjacent-control-band test applies and gives a signed, p-valued answer.
⇒ the tooling already exists: `rlog-tools/decode/extract_audio*.py`,
`analysis-2020accord/studies/acoustic/audio_matched.py`, `extract/extract_audio_cache.py`.
⇒ **[CORRECTED] my bound stands for CAN at 6–9 Hz and does NOT apply to the acoustic instrument.**

## ✅✅✅ **A CALIBRATED BOUND AT LAST — ENGAGEMENT ADDS ≤ ~2 % OF RMS AS A 7.8 Hz LINE**
The band-power statistic was the wrong instrument: the record's claim is about a **LINE**
(*"0 of 97 fully-manual windows carry a line"*), and at **Q ≈ 20** the linewidth is
**7.8/20 ≈ 0.39 Hz**, so a 3 Hz band **dilutes it ~8×**. Redone on **line prominence**
(peak-in-band / local median background), 20 s windows, **0.098 Hz resolution**:
```
   channel  routes    6-9 Hz prominence [95% CI]     26-31 Hz CONTROL
   tq         13          1.17 [0.86, 1.27]          1.03 [0.88, 1.16]
   cs_tq      13          1.01 [0.83, 1.53]          1.01 [0.87, 1.30]
   rate_f     13          1.08 [0.89, 1.50]          0.95 [0.85, 1.21]
   probe      10          0.89 [0.80, 1.14]          1.03 [0.93, 1.27]
```
⇒ **still null, every CI spanning 1** ⇒ **the dilution hypothesis is REFUTED** — it was a reasonable
idea and it is wrong. Prominence agrees with band power.

### ⭐⭐ THE POSITIVE CONTROL — WHICH IS WHAT MAKES THE NULL MEAN SOMETHING
A null with no positive control is uninterpretable (the V64 lesson). Injecting a **noise-driven
Q = 20 resonance at 7.8 Hz** into **real manual `tq` windows** (baseline prominence **9.82**):
```
   injected line      prominence      vs baseline
     2 % of RMS         13.25            1.35
     5 % of RMS         19.27            1.96
    10 % of RMS         38.26            3.90
    20 % of RMS         65.44            6.66
    80 % of RMS        150.59           15.34
```
✅ **THE INSTRUMENT WORKS** — it resolves a Q=20 line at **2 % of signal RMS**.
⇒ and the measured engagement contrast is **1.17, CI upper bound 1.27 — BELOW the 2 % response of
1.35.**
⇒ **[EVIDENCE, with a PASSING positive control] engagement adds AT MOST ~2 % of signal RMS as a
7.8 Hz line on the column torque channel.** This is the **first calibrated bound** the kit has on
the symptom's visibility, as opposed to an inference from a ratio.

### 🛑 WHICH SETTLES THE SCORING QUESTION WITH A NUMBER
If the **entire** engagement-conditional line is ≤ 2 % of RMS, a build that removes **half** of it
moves the column by **≤ 1 % of RMS** — a prominence change of roughly **1.2×**, inside the
route-to-route spread of every channel measured.
⇒ **🛑🛑 NO CAN-DERIVED STATISTIC CAN RANK THESE BUILDS.** Not band share, not line prominence,
not matched, not pooled over 24 routes. **The question is closed, quantitatively.**
⇒ **Corollary — stop spending drives on instrumented scoring for THIS symptom.** Probes remain
valuable for *mechanism* questions (does a gate fire, does a counter toggle, what is a cell's duty),
which are **binary and large**; they are useless for *amplitude* questions about the ratchet.

### ⚠ ONE RECORDED CLAIM DOES NOT REPLICATE
`accord-ratchet-is-a-lightly-damped-resonance` states **"0 of 97 fully-manual windows carry a
line."** On this corpus **manual windows carry a median 6–9 Hz prominence of 9.82**, against a
white-noise expectation of only **~ln(30) ≈ 3.4**.
⇒ **manual windows are NOT line-free here.** Either that count used a much stricter test than
peak/background, or it was drawn from a narrower regime than the 24-route corpus.
⇒ **⚠ flagged, NOT overturned** — I do not have that memory's exact line test. **But its companion
inference — *"engagement supplies the resonance, it does not amplify an existing tone"* — should be
treated as UNCONFIRMED until that test is restated**, because a manual baseline prominence near 10
is consistent with an existing tone.
✅ **Untouched** (none is a contrast or a line count): ring-down **Q 14–29 / ζ 0.017–0.036**, the
Welch-ladder **limit-cycle exclusion**, **not-rim-side**, and the **loop-pole** case for V152/V153.

## 🛑🛑🛑 **MATCHED, ENGAGEMENT ADDS ~12 % AT 6–9 Hz — NOT 2.8×. THE BUS CANNOT SEE THE SYMPTOM.**
Pooled the matched analysis over **every cached route with both arms** — 27 qualify, 24 yield matched
strata. 5.1 s pure-arm windows, stratified on (speed bin × |rate| RMS bin), per-route median over
strata, then **bootstrap over ROUTES** (4,000 draws), per `feedback-episodes-not-windows`.
```
   channel   routes    6-9 Hz  [95% CI]        26-31 Hz (control)   32-38 Hz (control)
   tq          24     1.12 [1.01, 1.27]        0.98 [0.87, 1.26]    0.97 [0.87, 1.07]
   cs_tq       24     1.13 [1.00, 1.28]        0.96 [0.84, 1.26]    0.94 [0.80, 1.12]
   rate_f      24     1.09 [0.95, 1.21]        1.06 [0.93, 1.24]    1.02 [0.97, 1.13]
   probe       19     1.04 [0.99, 1.18]        1.04 [0.98, 1.10]    0.98 [0.94, 1.11]
```
✅ **THE CONTROLS ARE NULL** (0.94–1.06, every CI spanning 1). **That validates the matching** — a
broken stratification would have leaked a spurious effect into the control bands too. This is the
positive control the estimate needed, run before the estimate was believed.

### 🛑 WHAT IT OVERTURNS
**[EVIDENCE] the matched engagement contrast at 6–9 Hz is ~1.12× — a 12 % effect.**
⇒ the kit's **2.8×** (`accord-engagement-amplifies-6-9hz`, 235 blocks) and the **11.7–13.4×**
(`accord-ratchet-is-a-lightly-damped-resonance`) **do NOT survive matching on speed and steering
activity.** Both were computed across arms that differ in operating point, and the artefact is large:
**unmatched, the same channels read 0.10–0.13×** (engagement appearing to *suppress* the band 8–10×).
⇒ **an unmatched engaged/manual ratio on this bus is uninterpretable in EITHER direction.**

### ⭐⭐ WHY THIS RECONCILES WITH THE PHYSICS — AND WHAT IT MEANS FOR EVERY FUTURE BUILD
`accord-ratchet-is-a-lightly-damped-resonance` already states the mode is **"on the motor / rack /
tyre side, which no channel on this bus observes."**
⇒ **A ~12 % residue is exactly what an UNOBSERVABLE mode leaks onto observable channels.** The two
results agree; they were never in conflict once the contrast was matched.
🛑🛑 **THEREFORE: CAN-derived band statistics CANNOT ARBITRATE BUILDS FOR THIS SYMPTOM.** If the
whole engagement-conditional effect visible on the bus is 12 %, then a build that removes *half* of
the engaged contribution moves a bus statistic by ~6 % — against a between-route noise floor the kit
measured at **19.9× and 36.2×** for identical cals.
⇒ **This is the quantitative reason every between-build ratio in this kit has been uninformative**,
and why `docs/STATE.md` already records that *every durable thing this kit knows about grinding came
from the operator's ear.* **That was an observation; this is its mechanism and its bound.**

### ✅ WHAT SURVIVES, AND WHAT TO DO WITH IT
✅ **Untouched**: the ring-down **Q 14–29 / ζ 0.017–0.036**, the Welch-ladder **limit-cycle exclusion**,
and the **not-rim-side** transfer function — each passed its own control and none is a contrast ratio.
✅ **Untouched**: the **loop-pole** justification for V152/V153, which never rested on a contrast.
🛑 **Retired as an instrument**: engaged/manual band ratios, matched or not, as a way to **score a
build**. Matched they are honest but ~12 % wide; unmatched they are artefacts.
⭐ **THE OPERATOR'S EAR IS THE INSTRUMENT, and that is now a measured conclusion rather than a
resignation.** Fly one build, judge by ear, report. **Do not ask for a scoring number that the bus
cannot carry.**

## 🛑🛑 **UNMATCHED ENGAGEMENT CONTRASTS ARE OPERATING-POINT ARTEFACTS — INCLUDING MINE**
I searched every cached channel for the symptom's carrier: the signature is **high 6–9 Hz engagement
contrast WITH flat control bands.** The search found nothing — and then showed why the question was
malformed as asked.

### 🛑 RAW, UNMATCHED CONTRASTS SAY ENGAGEMENT *REMOVES* THE BAND
```
   r7e / r7f, engaged/manual 6-9 Hz band power, NO matching:
      tq      0.13 / 0.10        rate_f  0.12 / 0.10        cs_rate 0.13 / 0.11
      probe   0.57 / 0.83        wang    1.18 / 0.31
   no channel on either route exceeds 2.0x, and the best SELECTIVITY is 2.10x (cs_brakev, irrelevant)
```
⇒ taken at face value this says engagement **suppresses** 6–9 Hz **8–10×** — which is obviously an
**operating-point artefact**: the manual arm is ordinary driving and simply moves the wheel far more.
⇒ **[EVIDENCE] an unmatched engaged/manual band ratio measures the DRIVING, not the firmware.**

### ✅ MATCHED ON SPEED **AND** STEERING ACTIVITY, THE EFFECT COLLAPSES AND FLIPS
5.1 s windows, pure-arm only, stratified on (speed bin × |rate| RMS bin), median over matched strata:
```
   route   channel   6-9 Hz share ratio   CONTROL 26-31 Hz   selectivity   strata
   r7e     tq              0.86                1.07              0.80         7
   r7e     rate_f          0.76                1.11              0.69         7
   r7e     probe           0.66                1.04              0.63         7
   r7f     tq              1.31                0.87              1.50         6
   r7f     rate_f          1.08                0.94              1.14         6
   r7f     probe           1.35                1.31              1.03         6
```
⇒ **SAME BUILD, SAME DRIVER, TWO ROUTES, OPPOSITE SIGNS.** Matched, the contrast sits in
**0.66–1.35** and does not replicate in direction, let alone magnitude.
⇒ **[EVIDENCE] these two routes do NOT independently confirm an engagement amplification at 6–9 Hz.**
They are **underpowered** (6–7 strata each) and cannot refute the corpus result either — but they
**do** demonstrate that the unmatched figures are artefacts.

### 🛑 A NUMBER IN A PROMOTED MEMORY NEEDS A CAVEAT
`accord-ratchet-is-a-lightly-damped-resonance` cites **"engaged/manual band power 11.7–13.4×"**.
That figure carries **no n and no CI, and no statement that it was matched.** The kit's other
engagement result, `accord-engagement-amplifies-6-9hz`, gives **2.8×** from **30 routes / 284 min /
235 blocks with a CI [+0.146, +0.667]** — blocked, and an order of magnitude smaller.
⇒ **⚠ Treat the 11.7–13.4× as UNMATCHED and therefore not comparable to any matched number.**
⇒ **The memory's OTHER results are untouched** — ring-down Q, the Welch-ladder limit-cycle exclusion
and the not-rim-side transfer function each passed their own control and stand.

### 🛑🛑 WHICH VOIDS THE **REASONING** OF MY OWN RETRACTION LAST TURN
Last turn I retracted *"`gp-0x6b70` is the carrier"* by comparing its **1.32–1.38×** against the
symptom's **11.7–13.4×**. **Both numbers are unmatched, so that comparison was not sound either.**
⇒ **[CORRECTED] `gp-0x6b70` is NOT REFUTED as a carrier — it is UNPROVEN.** The distinction matters:
refuted closes a lever, unproven leaves V152/V153 exactly where the loop-pole argument put them.
⇒ **The loop-pole justification for V152/V153 is unaffected** — it never rested on the contrast.

### ⭐ THE BINDING CONSTRAINT IS NOW A DRIVE, AND ITS DESIGN IS SPECIFIC
The kit cannot identify the carrier from existing data: **no cached route has matched engaged AND
manual exposure at the same speed and steering activity in the symptom's own regime.** This is the
same gap `accord-leverb-discriminator-underpowered` named — *"matched ENGAGED and MANUAL exposure."*
```
   THE DRIVE THAT UNBLOCKS THE ANALYSIS
   - one build, unchanged, one session
   - ALTERNATE arms every ~60 s:  engaged hands-off  <->  manual, at the SAME speed and the SAME
     gentle steering activity.  A parking-lot or quiet-road creep at a steady 5-15 km/h is ideal.
   - >= 8 alternations (>= 4 of each arm), >= 2 min engaged TOTAL
   - do NOT match a highway engaged arm against a city manual arm -- that is the artefact above
```
⇒ **This single protocol closes the carrier question for EVERY lever at once**, because every
channel is recorded on every route. **It is worth more than any additional build.**

## 🛑🛑 **RECONCILIATION — I HAVE BEEN SEARCHING A SPACE THE KIT ALREADY CLOSED**
`accord-ratchet-is-a-lightly-damped-resonance` is a **PROMOTED ★★★★★ memory** and it says, in its own
description: *"the firmware search on it is CLOSED."* Re-reading it in full against my last several
turns changes the ranking, and one of my own claims does not survive.

### ✅ WHAT THAT MEMORY ESTABLISHED — three methods, each past its own control
```
   Q 14-29, zeta 0.017-0.036   ring-down, the ONLY estimator that passes a control (r = +0.937)
   LIMIT CYCLE EXCLUDED        Welch ladder: car 20.9 vs pure tone 53.8, bursty AM 52.1-52.5
   NOT rim-side                |T/Omega| rises smoothly THROUGH the line; car 1.30x vs Q=10 -> 3.40x
   frequency tracks LOAD       +0.467 Hz over a 17.8x column-torque range at FIXED speed
   d log f / d log A = -0.034  kills rate-limit, backlash and classic stick-slip
   ENGAGEMENT SUPPLIES IT      0 of 97 fully-manual windows carry a line; engaged/manual 11.7-13.4x
```
🛑 **The closure is a SHAPE argument**: every gain-bearing element on the torque path is either a
**flat Q10 scalar** (which would lift the 26–31 and 32–38 Hz control bands too — they went *down*,
0.61–0.76) or a **differentiator** (favours HF, wrong direction). A band-limited lift at 6–9 Hz needs
a **resonant/biquad structure, and none exists in the chain.** It also states outright:
**"a 2-pole EMA has DC gain exactly 1 so no EMA can be the amplifier."**

### 🛑🛑 **MY "PREMISE SUPPORTED" CLAIM DOES NOT SURVIVE — RETRACTED**
Two turns ago I measured `gp-0x6b70`'s 6–9 Hz share at **8.7 % / 10.2 % engaged vs 6.6 % / 7.4 %
manual** and called V152/V153's premise *supported*, comparing against a **flat baseline**.
**That was the wrong comparator.** The symptom's own engagement contrast is **11.7–13.4×**.
```
   the SYMPTOM, engaged/manual band power      11.7 - 13.4 x
   gp-0x6b70,  engaged/manual 6-9 Hz share      1.32 -  1.38 x
```
⇒ **a carrier must show the carried signature. `gp-0x6b70` shows ~1.3× where the symptom shows
~12×** — and a Q 14–29 resonance cannot turn a 1.3× excitation change into a 12× output change.
⇒ **[RETRACTED] `gp-0x6b70` is NOT the carrier of the symptom.** The loop passes the band, which is
all my measurement showed; passing a band is not carrying a symptom.

### ⭐ THE ONE THING THE CLOSURE DOES **NOT** EXCLUDE — AND V152/V153 ARE EXACTLY IT
`memory/MEMORY.md` attaches this caveat to that very memory, and it is the whole opening:
> ⚠ *Its "no biquad ⇒ firmware search CLOSED" argument does **NOT exclude a loop pole**.*

⇒ **the shape argument excludes AMPLIFIERS; it does not exclude POLES.** A pole changes **phase**,
which changes how much the loop **re-excites** a mode that rings for ~Q ≈ 20 cycles (≈ 2.5 s at
7.8 Hz) after every kick.
⇒ **`0xC63AC` was V97 — recorded as *"the arc's FIRST loop-POLE lever"*.** **V152/V153 move that
same pole AND its byte-exact twin `0xC40D0`, matched, in the LOWERING direction.**
✅ **So V152/V153 sit in the ONE slot the kit's own closure leaves open** — not as carrier
attenuators (retracted above) but as **loop-pole/phase levers**. **That is a better justification
than the one I gave them, and it survives the shape argument.**
⚠ V97 moved `0xC63AC` **alone and UPWARD** and read **UNINTERPRETABLE**. V152/V153 move **both,
matched, downward** — a different move, and the only one that never breaks the arm-match.

### 🛑 HOW THE OTHER BUILDS FARE AGAINST THE SHAPE ARGUMENT
```
   V152/V153  loop POLES, matched          <- the ONE class the closure leaves open   SURVIVES
   V149       a SWITCH (5.12x step)        shape argument covers gains, not switches  SURVIVES
   V139       the r24/r26 PUMP arms        a pump is not a flat scalar in effect      SURVIVES
   V155/V154  inertia-lane WEIGHT          a flat Q10 scalar -- BUT on an omega^2 lane,
                                           so its EFFECT is frequency-shaped         PARTLY
   V151       the knee                     relay already ~99 % unsaturated            WEAK
```
⇒ **[DECISION] V153 stays first, for the loop-pole reason, not the transmission reason.**
⇒ **And the honest frame for the operator: the mode is MOTOR/RACK/TYRE side and no channel on this
bus observes it.** Firmware cannot remove a mechanical resonance — it can only change what excites
it and the phase with which the loop feeds it. **Every remaining build is an excitation or phase
lever. None of them can "eliminate" a mechanical mode**, and the record should say so.

## 🛑 **THE ADMISSION-GATE CLASS — HALF CLOSED FROM THE RECORD, AND V154/V155 DEMOTED**
Last turn I flagged the lane admission gates as a **third switching class** and called measuring
their duty *"the cheap next probe."* **Three of the six were already measured.** The kit's own rule
— *search the record before naming a cause* — applied to my own proposal.
```
   lane        gate     recorded magnitude                              gate trips?
   gp-0x6b26   +-1024   p50 5.5 / p90 39.1 / p99 114.3 / MAX 319.1      NO -- 3.2x margin
                        (+-511 clamp upstream, clamp duty 0.000000)
   gp-0x6b4c  +-10240   V101 b6: |gp-0x6b4c| >= 4096 duty 0.000000      NO -- 2.5x margin
   gp-0x6bbe   +-2048   p50 73.6 ct, flat across 0-6 deg/s              NO (large margin)
   gp-0x6b4e  +-10240   disjoint partition twin of gp-0x6b4c            NOT MEASURED
   gp-0x6b46   +-1024   unmapped lane                                   NOT MEASURED
   gp-0x6bd0   +-2048   the damper                                      NOT MEASURED
```
⇒ **[EVIDENCE] no gate that has ever been measured has EVER tripped.** For `gp-0x6b26` the gate is
**unreachable by construction** — an upstream `±cal(0xC407E)` = **±511** clamp binds first, and the
admission gate sits at **±1024**. ⇒ **the admission-gate class is NOT the ratchet's source on any
lane the kit has instrumented**, and only three lanes remain open.

### 🛑🛑 **AND IT DEMOTES MY OWN BUILD — V154/V155 ARE SMALLER THAN I RANKED THEM**
The same measurement that closes the gate also **sizes the lane**:
```
   gp-0x6b26 MAX 319.1        vs  gp-0x6b4c < 4096 (measured)      =>  <= ~8 % of the sum AT ITS MAX
   gp-0x6b26 p50 5.5                                               =>  a few tenths of a % typically
```
⇒ **halving this weight moves `sum6` by a few percent at most.** The ω² argument still holds — its
**share at 7.8 Hz is higher** than its share over all frames — but it starts from a **small base**,
and that share has **never been measured**.
⇒ **[CORRECTION to my own ranking last turn] V154/V155 drop BELOW V152. The mechanism is still the
cleanest in the kit — pure gain, no phase cancellation, zero DC cost — but the expected magnitude is
SMALL.** I ranked them second on mechanism quality without sizing the lane. **Sizing came first and
I skipped it.**
✅ **They remain SAFE on the one axis that matters**: `FUN_00036c12` carries an **int32 WRAPAROUND**
(`mul r13,r6,r0`, ×0x111, high half discarded, **unclamped and UPSTREAM of `0xC407E`**) that binds
at ≈**1.6005×** the present level and would deliver a **full-scale SIGN INVERSION**. **V154/V155
REDUCE the lane, moving AWAY from it.** Any build that RAISES `gp-0x6b26` moves toward it.

### ⭐ WHY THE OTHER LANES ARE NOT SELECTIVE LEVERS
**`gp-0x6b4c` and `gp-0x6b4e` are the DISJOINT PARTITION SUMS of the same 11-slot request array**
`gp-0x62c8[]`, split by the mode bytes — i.e. **they carry the assist request itself.** They are the
dominant terms and they carry **DC**, so cutting their weights (`0xC63AA`/`0xC63A8`) would reduce
authority broadly rather than selectively. **Not selective levers.**
⇒ **the inertia lane is the ONLY frequency-selective lane in the observer sum**, which is why it was
worth building even at a small expected magnitude.

### ✅ THE HONEST RE-RANKING
```
   1. V153   observer corner /4, BOTH arms matched   1.95x less at 7.8 Hz, no DC cost, CERTAIN   3 B
   2. V152   the same lever at /2                    1.26x less, conservative                    3 B
   3. V149   removes the 5.12x r24 switch            bigger IF it fires; may be INERT            2 B
   4. V139   both pump arms halved                   demonstrated on-car potency                 2 B
   5. V155   inertia lane /4     cleanest mechanism, SMALL magnitude (lane <= ~8 % of the sum)   1 B
   6. V154   inertia lane /2                                                                     1 B
   7. V150   r26 suppression switch removed          can only suppress the pump                  1 B
   8. V148   deadband + probe                        MEASURES whether gp-0x671d toggles          3 B
   9. V151   knee 3000 -> 3600                       MARGINAL, costs 17 % of the term            2 B
```
⇒ **V153 stays first**: it acts on the WHOLE residual path rather than one small lane, it is
**certain to act** (the EMA runs every 1 kHz tick), its reduction is **quantified**, and it costs
**nothing at DC**.

## ✅✅✅ **V154 / V155 BUILT — THE INERTIA LANE'S WEIGHT, THE CLEAN VERSION OF THE α2 LEVER**
```
   V154   0xC63A6  1024 -> 512    w(gp-0x6b26), the INERTIA lane   1 payload byte, 58/58, CRC 50/50
          image 15a9b902828028b17dca92b83098ba29ca267bf531c3c728a575e07849091d1f
          rwd   6fe3eceb410d13ecd56f02da09b1e37081818af9de8f501c306d7484f3015806
   V155   0xC63A6  1024 -> 256    the larger dose                  1 payload byte, 58/58, CRC 50/50
          image 4b9201b618f4fb37cdbe4aabc05e03e9aa348eae7c6b13664931ffee55f69b0e
          rwd   0d138c838ea505357ab414cce1685d0d758037823f334718daaba6c93dac1cb6
   diff_vs_flown: 1 payload byte vs V122 => SINGLE-VARIABLE, interpretable
```
### ⭐ THE SIGN AMBIGUITY THAT HELD THIS CELL BACK WAS A CATEGORY ERROR
The previous pass derived the direction twice and got **opposite answers**, and filed it unresolved.
**The error was asking about the DIRECTION OF ASSIST (sign-dependent) when the question is the
AMPLITUDE OF AN OSCILLATION (sign-independent).**
```
   gp-0x374c ~= -(sum6 * cal(0xC6468)/1024) * 16        because polarity gp-0x6752 = -1
   iVar5      = gp-0x6bfe - (gp-0x374c >> 4) = MODEL + sum6*2639/1024
   iVar6      = iVar5 + gp-0x6bfa
   gp-0x6b70  = sign(iVar6) * LERP(|iVar6|)             an ODD, MONOTONE function
```
⇒ **`polarity` sets the PHASE of the oscillating component, not its AMPLITUDE**, and an odd
monotone `g` maps smaller input amplitude to smaller output amplitude **regardless of sign**.
⇒ **[EVIDENCE] reducing this weight unambiguously reduces the 7.8 Hz amplitude reaching the PID
reference.** The ambiguity never applied to an amplitude claim.

### ⭐ WHY IT IS HF-SELECTIVE **BY CONSTRUCTION**
`gp-0x6b26` is `−K·α`, an **ACCELERATION** (`gp-0x6c2c` is a first difference of the filtered
EPS-motor rate). **Acceleration is EXACTLY zero at DC and scales as ω²:**
```
   influence at 7.8 Hz / influence at 1 Hz steering = (7.8/1)^2 = 61x
```
⇒ halving the weight removes **61× more at the ratchet than at normal steering**, and **nothing at
all in steady state** — the operator's *"low friction AND no ratcheting"* with **no steady-state
trade**, the same no-cost property as V152/V153 but on a different mechanism.

### ⭐ THIS IS THE LEVER FOUR α2 BUILDS WERE REACHING FOR
The **α2 ladder (22→14→8→5) scaled this SAME lane** and measured **nearly INERT at 20 Hz**: `|H|`
fell **7.24→4.10 (1.77×)** while the phase rotated **56.3°→16.0°**, leaving the delivered component
**FLAT (−4.01 → −3.94)**. **α2 is a POLE — it moves magnitude AND phase, and they cancelled.**
⇒ **`0xC63A6` is a PURE GAIN: magnitude only, ZERO phase rotation, so NOTHING CANCELS.**
⇒ **Virgin: 1024 in all 153 images.**

### 🛑 WHAT IS NOT ESTABLISHED — AND A NEW SWITCHING NONLINEARITY FOUND IN PASSING
⚠ **The lane's admission gate `|gp-0x6b26| ≤ 1024` is a HARD-CODED IMMEDIATE (`0x400`/`0x801`), not
a cal.** If `gp-0x6b26` crosses that bound during the ratchet the lane is **ZEROED, not clamped** —
**a genuine switching nonlinearity that no weight change can reach.** **Its duty has NEVER been
measured.** The same is true of every lane: `gp-0x6b4c`/`gp-0x6b4e` gate at `±10240`, `gp-0x6b46`
at `±1024`, `gp-0x6bd0`/`gp-0x6bbe` at `±2048`.
⭐ **THIS IS A NEW ENTRY ON THE SWITCHING CENSUS** — which previously covered only counter-gated and
sign-gated switches. **Admission gates are a THIRD class, and their bounds are immediates, so they
are code edits, not cal edits.** Measuring their duty is the cheap next probe.
⚠ **[BELIEF]** that a 2× (V154) or 4× (V155) cut on a lane bounded at ±1024, inside a sum whose
largest lanes are bounded at ±10240, is **audible**. Its worst-case share of the full sum is
**3.8 %**; its share **at 7.8 Hz** is higher because acceleration dominates at HF, but **by how much
is unmeasured.**
⊕ **V154 and V155 are one lever at two doses — fly ONE.**

## 🛑🛑 **THE PLANT MODEL HAS NO DAMPING TERM — `0xC646E` / `0xC40D6` CLOSED AS INERT**
`FUN_0003b8f6` computes `residual = model − (friction + rate_term)`. The **rate term** looked like
the ideal lever — a rate term has **exactly zero DC gain** and contributes ∝ω, so scaling it is
HF-selective **by construction**. It is not a lever, because it is **not there.**
```
   rate_term = fVar19[rad/s] * cal(0xC646E)=1428 * 2^-24  =  fVar19 * 8.5115e-05   (clamp +-10)
     saturates at fVar19 = 117,488 rad/s  =>  PHYSICALLY UNREACHABLE, it is always linear

   regime                              rate rad/s   rate_term   vs the +-10 clamp
   the RATCHET  7.8 Hz, 0.1 deg           0.0855    7.28e-06        0.0001 %
   the RATCHET  7.8 Hz, 1.0 deg           0.8554    7.28e-05        0.0007 %
   brisk lane change ~1 Hz, 30 deg        3.2899    2.80e-04        0.0028 %
   fast hand slew ~2 Hz, 90 deg          19.7392    1.68e-03        0.0168 %
   friction, same function, |model|=15:  14.94 -> CLAMPED to 10.00
```
⇒ **[EVIDENCE] the damping term is 4–6 ORDERS OF MAGNITUDE below the friction term it is summed
with.** ⇒ **and NO DOSE REVIVES IT**: at the u16 ceiling `cal = 65535` it still reaches
**3.34e-04 = 0.0033 %** of the clamp at ratchet amplitudes.
⇒ **`0xC646E` is STRUCTURALLY INERT and `0xC40D6` (its EMA pole) is inert by consequence. Both
CLOSED — do not propose either at any dose.** Both **virgin across all 153 images.**
⭐ **The structural fact worth keeping: Honda's observer models FRICTION but NOT DAMPING.** The
plant model is friction-only, so real viscous damping is un-modelled and lands in the residual.

### ✅ A METHOD FIX THAT MATTERS FOR EVERY FUTURE READER COUNT
My first scan reported **20 accesses** to `0xC646E`. **Most were ASCII.** `0x746E` is `"nt"`
little-endian, so `68 61 6c 74` (*"halt"*) at `0xBB222` and `73 79 6e 74` (*"synt"*) at `0xBB4A8`
matched as if they were `disp16`. **The missing filter is `reg1`:** a tp-relative load must carry
**`hw1 & 0x1F == 5`** (tp = r5), plus a Format-VII opcode `>= 0x38`.
```
   cell        loose scan   WITH reg1==tp filter    independent check
   0xC646C         8                5              memory says ~6 readers        OK
   0xC63AC         -                1  @0x38202    lineage: "sole reader ld.hu 0x73ac,tp,r13
                                                    @0x38202"                    EXACT MATCH
   0xC646E        20                1  @0x3BB92    single-reader, FUN_0003b8f6
   0xC40D0         -                1  @0x3BB22    0xC40BC -> 1 @0x3BAB4
```
⇒ **The `0xC63AC` result reproduces a fact recorded independently in the lineage, to the address.**
🛑 **Ghidra CANNOT answer this** — `get_xrefs_to 0xC646E` returns *"No references found"*, because
tp is a runtime register and Ghidra never resolves tp-relative loads to absolute cal addresses.
**For tp-relative cals, the filtered Python scan is the ONLY instrument. Add the `reg1` filter.**

### ⭐ ONE HF-SELECTIVE CANDIDATE REMAINS — AND ITS SIGN IS UNRESOLVED
`0xC63A6`, the weight on **`gp-0x6b26`, the INERTIA lane** (`−K·α`, an ACCELERATION) in
`FUN_00038148`. **Acceleration is exactly zero at DC and scales as ω²** ⇒ moving this weight is
**HF-selective by construction, with zero steady-state cost** — the same attractive property the
rate term had, but on a lane that is **not** negligible. **Virgin: 1024 in all 153 images.**
🛑 **NOT PROPOSED — I DERIVED THE DIRECTION TWICE AND GOT OPPOSITE ANSWERS.** The chain is
`lanes → ×polarity(−1) → ×2639 → IIR → gp-0x374c → MODEL − (gp-0x374c>>4) → iVar6 → gp-0x6b70 →
gp-0x6ad6 → error → assist`, and whether a bigger lane weight RAISES or LOWERS HF assist depends on
how the `−1` composes with *"residual ↓ ⇒ more assist"*. **An unresolved sign is not a build** — the
same rule that held `0xC40D0` back until the paired form closed its gate.
⇒ **To close it**: the flown `0x14A` comparator rungs already carry `sign(gp-0x6b70)`; one probe
that also carries `sign(gp-0x6b26)` on the same frame settles it.

## ✅ **V152/V153's PREMISE CHECKED — THE OBSERVER LOOP DOES CARRY 6–9 Hz, MODESTLY**
Before betting a drive on the matched-pole move, I asked whether the loop it attacks actually
carries the symptom band. **Control run FIRST** (the kit's own rule), same signal, same route,
LKAS-off arm:
```
   route  arm        n       6-9 Hz    18-22 Hz   share(6-9 Hz in 1-45 Hz)
   r7e    ENGAGED    17,689     183        281        8.7 %
   r7e    lkas-off   22,544     503        439        6.6 %
   r7f    ENGAGED    15,779     197        295       10.2 %
   r7f    lkas-off   26,036     447        383        7.4 %
   flat-spectrum baseline for a 3 Hz window in 1-45 Hz = 6.8 %
```
⇒ **engaging shifts `gp-0x6b70`'s spectrum toward 6–9 Hz by 1.32× (r7e) and 1.38× (r7f)** against
the manual arm, and to 1.28×/1.50× of the flat baseline. **Replicated on two routes.**
✅ **[EVIDENCE] the observer loop carries an engagement-elevated 6–9 Hz component** ⇒ V152/V153 are
aimed at a loop that demonstrably passes the symptom band.
⚠ **[NOT PROVEN] that reducing its transmission fixes the symptom.** The effect is **modest**
(1.3–1.4×) and **confounded by operating point** — the engaged arm is creep, the manual arm is not
speed-matched. Per [[accord-averaged-spectrum-needs-matched-speed-distributions]] this is
**supporting, not decisive**. Note also the ABSOLUTE 6–9 Hz power is **higher** in the manual arm
(503 vs 183) — manual steering simply moves more; **only the SHARE comparison is meaningful here.**

### 🛑 A SAMPLING FACT WORTH RECORDING FOR THE WHOLE KIT
**`0x1AB` (427) is transmitted at 49.8 Hz, NOT 100 Hz** — measured from `ab_t1ab` on both routes.
⇒ **Nyquist is 24.9 Hz.** 6–9 Hz is safely resolved, but **any 18–22 or 18–28 Hz claim derived from
`0x1AB` sits close to the fold** and can take aliased content from above 24.9 Hz.
⇒ **Check the source ID's rate before quoting a high-band number.** `0x14A` is the 100 Hz builder;
`0x1AB` is not.

## 🛑🛑 **THE SIGN-GATED RELAY IN `FUN_00038148` — FOUND, THEN REFUTED BY FLOWN DATA**
The switching census covered **counter** gates; the sign-gated class was never swept. Sweeping it
found a **real signum multiply** in the PID-reference path — and then closed it with measurement.

### ✅ THE STRUCTURE — a genuine relay candidate
`FUN_00038148`, the ACTUAL arm, ends:
```c
   iVar6  = (gp-0x6bfe MODEL - (gp-0x374c>>4) ACTUAL) + gp-0x6bfa REQUEST;
   uVar7  = |iVar6| * cal(0xC63AE) >> 10;                  // 0xC63AE = 1024, unity
   sVar8  = LERP(uVar7);                                    // 10-entry RAM table @ gp-0x641c
   iVar9  = ((iVar6 >= 0) - (iVar6 < 0)) * sVar8;           // <-- SIGNUM MULTIPLY
   gp-0x6b70 = clamp(iVar9, +-cal(0xC6200)=8192);
```
⇒ `gp-0x6b70 = sign(residual) × f(|residual|)` — **odd-symmetric, and continuous ONLY IF f(0)=0.**
If `values[0] ≠ 0`, `gp-0x6b70` **jumps by `2·values[0]` at every zero crossing** — a hard relay
feeding the PID reference, which is exactly the stick-slip generator the kit has been hunting.
⚠ The table is in **RAM (`gp-0x641c` values / `gp-0x64b8` axis, 10 entries each), 0 gp-relative
stores** ⇒ a `.data` section copied by **register-indirect** stores, which operand scans cannot see.
So `values[0]` is **not readable from the image** without tracing the startup copy table.

### ⭐ CLOSED BY MEASUREMENT INSTEAD — the flown 427 tap
**427 = 0x1AB, and V96–V99 repointed its `MOTOR_TORQUE` field to `gp-0x6b70`.** That data is cached.
**If `values[0] ≠ 0`, `|gp-0x6b70|` can NEVER enter a band around zero.** It does:
```
   route   engaged n   min  max  p50   zero-crossings   counts at mt = 0,1,2,3,4,5,6
   r7e     17,689        0  216    9        1,741       1048 1209 987 877 848 871 816
   r7f     15,779        0  200    9        1,490        911 1015 907 836 805 770 936
   r82        467        0  148   14           36         22   19  17  17  14  19  14
```
⇒ **`mt = 0` occurs on 5.9 % of engaged frames and every small bin is populated — NO forbidden
band**, across **1,741 zero crossings** on r7e alone.

### ⭐ THE BOUND IS INDEPENDENT OF THE PACKER'S SHIFT
The 427 packer applies some `sar k`, so `mt = 0` ⇺ `|gp-0x6b70| < 2^k`, and the worst-case jump is
`2·values[0] < 2^(k+1)`. The observed maximum is `216·2^k`. Therefore
```
   jump / range  <  2^(k+1) / (216 * 2^k)  =  2/216  =  0.93 %      <- k CANCELS
```
⇒ **[EVIDENCE] any discontinuity at zero is under 1 % of the signal's own observed range**, against
a ±8192 clamp. **That is not a relay in any meaningful sense.**
⇒ **THE SIGN-GATED RELAY HYPOTHESIS IS CLOSED.** `f(0) ≈ 0`; the signum multiply is continuous.
⭐ **Do not re-propose `gp-0x641c`, `0xC63AE` or the signum branch as a stick-slip source.** And note
`0xC63AE` is the WRONG direction anyway: shrinking it drives `uVar7 → 0` so `sVar8 → values[0]`
always, turning a continuous law INTO a pure relay.

### ✅ WHAT THIS LEAVES
Both sign-gated candidates in the assist chain are now closed — the `|model|×sat(angle)` term (soft
saturation, continuous, ~1 % duty) and this signum multiply (continuous, <1 % jump).
⇒ **V152/V153 — the matched observer-corner move — remains the strongest candidate**, and it is
strengthened by this: with no relay in the path, the ratchet is a **lightly-damped resonance being
excited through a loop that is 91 % transparent at 7.8 Hz**, which is precisely what those builds
attack.

## ✅✅✅ **V152 / V153 BUILT — THE OBSERVER CORNER, MOVED ON BOTH ARMS AT ONCE**
The GATE-2 objection to `0xC40D0` was that moving it alone **breaks Honda's byte-exact arm-match**.
**Moving BOTH cells together removes the objection entirely**, and that is these two builds.
```
   V152   0xC40D0 408 -> 204   AND   0xC63AC 102 -> 51    204 = 4 x 51  EXACT
          shared corner 16.70 -> 8.13 Hz   |H(7.8 Hz)| 0.906 -> 0.722 = 1.26x less
          3 payload bytes, 54/54, CRC 50/50
          image 9d154a876392f1a881a332daec08c89cf28ee382de36992d3b724907d4eff148
          rwd   2a5ceef7ba80809593c4b7f6aca4747235dcf30e9c2e442cf7ba3d0b1386e140

   V153   0xC40D0 408 -> 104   AND   0xC63AC 102 -> 26    104 = 4 x 26  EXACT
          shared corner 16.70 -> 4.09 Hz   |H(7.8 Hz)| 0.906 -> 0.465 = 1.95x less
          3 payload bytes, 54/54, CRC 50/50
          image 5b2c43b98e16331d46bb80fa40fdd5c4bd98b4d9d7c2247a4cffaf690777fac7
          rwd   c25fc1d64a3f0d8c291b37722db29a8847f037f127d11c304d0e956ef4bc50cb
```
### ⭐ WHY THIS IS THE STRONGEST CANDIDATE IN THE SET
1. **GATE 2 IS CLOSED, NOT ARGUED AROUND.** α stays **identical on both arms** (V152 0.049804688,
   V153 0.025390625) ⇒ **no RELATIVE phase is introduced anywhere in the observer residual.** Only
   the **shared** corner moves ⇒ a **pure added low-pass on the residual** ⇒ **HF loop gain DOWN**,
   the stabilising direction for a **Q 14–29** resonance.
2. **IT COSTS NO AUTHORITY.** An EMA has **DC gain EXACTLY 1** at any α ⇒ **steady-state friction
   and steady-state assist are UNCHANGED.** This is the operator's *"low friction AND no
   ratcheting"* with **no trade at all** — unlike V151, which scales the term at DC too.
3. **IT IS CERTAIN TO ACT.** The EMA runs every 1 kHz tick unconditionally. Contrast **V149**, which
   is **INERT if `gp-0x671d` never increments** (it is a fault counter, `|x| ≥ 5530`) — unknown.
4. **IT IS AIMED AT THE RATCHET FREQUENCY**, where the path was measured **91 % open**.
5. **The direction is the one the kit's OWN Bode sum favours**: `0xC63AC` was filed *"Predicted
   WORSE"* for being **RAISED** (cal 205 ⇒ 1.38× HF gain, `|L|` = 1.208). **Lowering moves HF gain
   DOWN** ⇒ `|L|` falls **below** 0.875, inside the edge.

### 🛑 WHAT TO KNOW BEFORE FLYING THEM
⚠ `diff_vs_flown` reports **"MULTI-VARIABLE"** for both — **expected and correct as a mechanical
check.** They are **two cells but ONE logical lever**: the cells *must* move together, because
holding one still is exactly the phase-error case being avoided. **Do not "simplify" either build to
a single cell.**
⚠ **`0xC63AC` = 102 is HONDA STOCK**, restored deliberately by V99 after V97 flew it at 150 and came
back **UNINTERPRETABLE**. Below stock is **new territory** for that cell.
⚠ **[BELIEF]** that 1.26× (V152) or 1.95× (V153) less transmission at 7.8 Hz is **audible**. The
mechanism is EVIDENCE; the audibility is not.
⊕ **V152 and V153 are the SAME lever at two doses — fly ONE, not both.** V153 is the larger step and
matches the operator's *"just want the best possible results"*; V152 is the conservative half-step
if a 4.09 Hz observer corner feels too slow.

### ✅ THE FLIGHT ORDER
```
   1. V153   observer corner /4, both arms matched   1.95x less at 7.8 Hz, NO authority cost  3 B
   2. V152   the same lever at /2                    1.26x less, conservative                 3 B
   3. V149   removes the 5.12x r24 switch            bigger IF it fires; may be INERT         2 B
   4. V139   both pump arms halved                   demonstrated on-car potency              2 B
   5. V150   r26 suppression switch removed          can only suppress the pump               1 B
   6. V148   deadband + probe                        MEASURES whether gp-0x671d toggles       3 B
   7. V151   knee 3000 -> 3600                       MARGINAL, and costs 17 % of the term     2 B
```

## ⭐⭐ **`0xC40D0` — THE BEST REMAINING STRUCTURAL LEVER, WITH ITS GATE OPEN**
Following the corrected `|model| × sat(angle)` structure to its filter found a **virgin, well-aimed
lever** — and then found the reason not to fire it yet. Both halves are recorded.

### ✅ WHY IT IS WELL-AIMED
The bilinear term is EMA-filtered by `cal(0xC40D0)`, `α = cal/4096`, in the **1 kHz** task:
```
   0xC40D0  the |model|xsat(angle) EMA   cal= 408  a=0.09961  fc= 16.70 Hz  |H(7.8Hz)| = 0.906
   0xC40D6  the rate term                cal= 246  a=0.06006  fc=  9.86 Hz  |H(7.8Hz)| = 0.784
   0xC40D4  model pre-filter             cal= 573  a=0.13989  fc= 23.98 Hz  |H(7.8Hz)| = 0.951
   0xC40D8  sensor pre-filter            cal=3686  a=0.89990  fc=366.31 Hz  |H(7.8Hz)| = 1.000
```
⇒ **the bilinear path passes the ratchet frequency at 91 %** — it is wide open at 7.8 Hz.
⭐ **And an EMA has DC gain EXACTLY 1**, so lowering the pole attenuates only the FAST component and
leaves steady-state friction **untouched** ⇒ **no assist cost**, unlike V151 which cuts the term at
every frequency including DC. That is precisely the operator's *"low friction AND no ratcheting"*.
✅ **VIRGIN: `0xC40D0` = 408 in ALL 151 build images.** Never touched.

### 🛑 WHY IT IS NOT BUILT — A BYTE-EXACT DESIGNED ARM-MATCH
`BUILD-LINEAGE.md` warns that `0xC63AC`'s α *"matches `0xC40D0` to the last bit — a genuine
disturbance-observer constraint, not hygiene."* **Confirmed arithmetically:**
```
   alpha(0xC63AC) = 102/1024 = 0.099609375        (>>10 in FUN_00038148)
   alpha(0xC40D0) = 408/4096 = 0.099609375        (x0.00024414062 in FUN_0003b8f6)
   408 = 4 x 102  EXACTLY  =>  the match is BY CONSTRUCTION, not coincidence
```
And these sit on **opposite arms of one observer residual** — V98's comparator established
`iVar6 = gp-0x6bfe (MODEL) + gp-0x6bfa (REQUEST) − (gp-0x374c>>4) (ACTUAL)`, where `0xC40D0` shapes
the **MODEL** arm and `0xC63AC` the **ACTUAL** arm.
⇒ **Honda gives both arms the same time constant so their phases cancel in the difference.
Moving one alone injects a phase error into the residual at every frequency, 7.8 Hz included.**
⇒ **[UNRESOLVED] the SIGN of that phase error in the residual.** Attenuating a term that is
*subtracted* can either remove or expose 7.8 Hz content depending on phase.
⚠ **Precedent is discouraging**: the matched twin `0xC63AC` **flew as V97** and came back
**UNINTERPRETABLE — a null with no positive control**, and the kit's own full-loop Bode sum filed it
**"Predicted WORSE"**. That was for *raising* it (faster pole, more HF gain); lowering `0xC40D0` is
the opposite direction, **which is a reason to think, not a reason to assume.**

### ⭐ WHAT WOULD CLOSE THE GATE — stated so it can be executed, not re-derived
1. **The residual's own phase at 7.8 Hz**, MODEL arm vs ACTUAL arm, from a flown probe — V98's
   comparator rungs already rank the arms and could be re-cut to carry phase.
2. **Or the paired move**: change `0xC40D0` and `0xC63AC` **together**, preserving `408 = 4×102`, so
   the match is never broken and only the shared corner moves. **That is the SAFE form of this
   lever** and it is the one to build first — but `0xC63AC` at 102 is Honda stock and V99 put it
   back deliberately, so it needs the operator's call.
⇒ **[DECISION] not built blind.** GATE 2 (phase, in every loop the signal is in) is **not closed**,
and this kit's rule is that an unclosed GATE 2 is not a build.

## 🛑🛑 **THE “COULOMB RELAY” IS NOT FRICTION AND NOT A RELAY — IT IS `|model| × sat(ANGLE)`**
**[EVIDENCE — `decompile_function 0x0003b8f6`, GhidraMCP]** The kit has described `0xC40BC` for
~40 builds as *"the relay knee"* in `friction = K1·min(|model|,knee)/knee`. **That formula is
wrong.** What `FUN_0003b8f6` actually computes:
```c
   iVar20 = polarity * gp-0x6abc * 12;                  // an ANGLE, NOT the model
   uVar8  = *(ushort *)(tp + 0x50bc);                   // tp+0x50BC = 0xC40BC = THE KNEE
   fVar13 = clamp((float)iVar20*0.5 / ((float)uVar8*0.5), -1.0, +1.0);   // sat(ANGLE / knee)
   fVar14 = |fVar18|;                                   // |model|
   fVar15 = (fVar14 * K1/1024  +  OFFSET/1024) * fVar13; // BILINEAR: |model| x sat(angle)
   ...EMA with pole cal(0xC40D0), then clamp to +-10.0
```
### ⭐ THE PROOF THAT `gp-0x6abc` IS AN ANGLE
`iVar20`'s own **first difference** is taken 20 lines later:
`(iVar20 - *(int*)(gp-0x3618)) * 0.5 * 17.453293` — and **17.453293 = 1000·π/180**, a **deg→rad
conversion at the confirmed 1 kHz task rate.** A quantity whose first difference is an angular
rate **is an angle.**

### 🛑 WHAT THIS OVERTURNS
```
   BELIEVED (~40 builds)                    ACTUAL
   knee normalises |model|                  knee normalises the ANGLE gp-0x6abc
   slope = K1/knee, one axis                K1 and knee are INDEPENDENT axes
   saturates at |model| >= knee             saturates at |gp-0x6abc| >= knee/12 = 250 counts
   Coulomb friction (velocity-sign relay)   an ANGLE-proportional, |model|-scaled BILINEAR term
   a hard relay => stick-slip generator     CONTINUOUS through zero => a SOFT saturation, no jump
```
⇒ **Coulomb friction switches on VELOCITY SIGN. This term does not switch at all** — it is a
linear ramp in angle through zero. **The stick-slip argument for it never applied.**
⊕ Independent corroboration: a byte census of the V850 sign-extract idiom (`sar 31`, encoding
`(X<<11)|0x2BF`) over `[0x30000,0x40000)` returns **6 hits, NONE inside the aggregator `0x3AA2C`
or the plant model `0x3B8F6`.** A true relay needs a sign switch; there is none here.

### ✅ WHAT SURVIVES, AND WHAT IT MEANS FOR V151
The **×0.8333 number survives, for a different reason**: in the **unsaturated** regime the term is
**exactly proportional to 1/knee**, so 3000→3600 is a **uniform 17 % reduction**; in the saturated
regime `sat()` is ±1 either way and the term is **unchanged**. ⇒ monotone reduction, as built.
⇒ But the term is **∝ steering angle**, and **engaged hands-off creep runs small angles**, so the
term is **already small there** — V151 reduces something that is already small in the symptom's own
regime. **V151 stays MARGINAL and stays ranked 5th.**
⭐ **The V151 builder docstring and one check message have been corrected in place.**

## ✅ **V151 BUILT — THE KNEE RAISE, REBASED ONTO V122 — AND THE RELAY IS LARGELY RETIRED**
The switching census covered **counter-gated** switches. It never covered the **sign-gated** class,
and the mechanism this kit has actually named is a **Coulomb relay** — a sign switch, the textbook
generator of stick-slip. Following that thread produced one build **and one retirement.**

### ✅ THE BUILD — a real gap in the flight set
**V135 made this exact edit and is SUPERSEDED** — not because the edit was wrong, but because it sat
on the **V133 base that regressed hard on-car**. Every V122-based build since (**V137–V150**) holds
the knee at 3000.
⇒ **the raise to 3600 had NEVER been built on a flyable base.** V151 is that build.
```
   0xC40BC  relay knee  3000 -> 3600   K1 HELD at 1020    2 payload bytes, 53/53, CRC 50/50
   image 0935460e0c6918f8c7cb27fa0c17f366ccc2f17e5a4c908d7400298838d9ebc0
   rwd   eb98eb6520f656523ca2db8438de0a3c5c072dbc31f8d35f09fcabebfe427287
   diff_vs_flown: 2 bytes vs V122 => SINGLE-VARIABLE, interpretable
```
`friction = K1 * min(|model|, knee) / knee`; with K1 held, friction is **lower-or-equal at every
`|model|` and never higher** — a monotone reduction, slope **0.340000 → 0.283333 = ×0.8333, 17 %
less**. **Gain-holding is unavailable**: slope 0.34 at knee 3600 needs **K1 = 1224**, above the
**1023 ceiling** past which friction exceeds `|model|` and the residual inverts.

### 🛑 THE RETIREMENT — THE RELAY IS ALREADY ~99 % OUT OF SATURATION ON WHAT IS FLYING
The measured duty ladder is a **survival function of `|model|`**, decaying **×0.206 per 600 counts**:
```
   knee  600 -> 0.7439   1800 -> 0.2353   3000 -> ~0.010  <- V122, WHAT IS ON THE CAR
   knee 1200 -> 0.4810   2400 -> 0.0484   3600 ->  0.0000 <- V151
```
⇒ **[EVIDENCE, from the kit's own measured ladder] V122 already runs the relay at ~1 % saturation
duty**, and **the operator still hears grinding on V122-family builds.**
⇒ **A nonlinearity active ~1 % of the time cannot be the cause of a continuous grinding symptom.**
⇒ **the Coulomb relay is LARGELY RETIRED as the cause of the REMAINING grinding.** It was the live
lever across V108→V122, when duty ran 0.74→0.01 — that arc is real — but **the ladder is spent.**
⭐ **This also corrects my own framing an hour ago**: V151's remaining effect is **the 17 % friction
cut, not relay removal.** By the verified polarity (*more modelled friction = MORE assist*) that
means **slightly LESS assist**, which is in tension with the LKAS-authority complaint.
⇒ **V151 is a MARGINAL build and is ranked accordingly — it does not displace V149.**

### ✅ THE FLIGHT ORDER, UPDATED
```
   1. V149   0xC6446 5244 -> 1024   removes the 5.12x r24 switch      2 B   52/52
             CAVEAT: inert IF gp-0x671d never increments (it is a FAULT counter, |x| >= 5530)
   2. V139   both pump arms halved  demonstrated on-car potency       2 B   49/49
   3. V150   0xC6136 0 -> 1         can only SUPPRESS the pump        1 B   51/51
   4. V148   deadband + probe       MEASURES whether gp-0x671d toggles 3 B  69/69
   5. V151   knee 3000 -> 3600      MARGINAL -- ~1 % duty left; 17 % less friction  2 B  53/53
```
⊕ **V149, V150 and V151 are independent single-lever builds and must not be stacked** — each
builder asserts the others' cells are held.

## 🛑 **FLATTENING THE LERP TO REMOVE THE REMAINING SWITCHES — CONSIDERED AND REJECTED**
The three `gp-0x671a` switches were called unremovable because one side is a **speed-varying LERP**.
That is only true while the LERP is a table. **If the table were flattened to the constant the
other branch uses, those switches would vanish too.** Checked whether that is reachable:
```
   gp-0x6E28  r26 LERP values   2 accesses   0x3AADE 0x3AAE4    ALL LOADS (24xx)
   gp-0x6E30  r26 LERP axis     3 accesses   0x3AAD0 0x3AAD8 0x3AF64
   gp-0x6E38  r24 LERP values   2 accesses   0x3ABAE 0x3ABB4
   gp-0x6E40  r24 LERP axis     3 accesses   0x3AB9C 0x3ABA4 0x3AE42
```
⇒ **NOT ONE gp-relative STORE.** These tables are a **`.data` section bulk-copied from flash at
startup**, so the flash source would have to be found through the startup copy table — doable, but
a real trace.

### 🛑 REJECTED ON MERIT, NOT ON DIFFICULTY
**Flattening a speed-scheduled multiplier to a constant does not merely remove the switch — it
removes SPEED SCHEDULING ENTIRELY.** The r24/r26 lanes would carry the same gain at 2 km/h and
120 km/h.
⇒ **the cure is far more invasive than the disease.** A build that changes assist at every speed to
eliminate a switch is not a targeted lever, and this kit's record (V133) is that broad changes to
these lanes produce large, hard-to-attribute regressions.
⇒ **[DECISION] not pursued. The `gp-0x671a` LERP-vs-const switches stay out of reach**, and the
switching class is closed at the two cal-removable members (V149, V150).
⭐ **Recorded so a future session does not re-derive the idea and mistake "reachable" for
"advisable".**

### ✅ HANDOFF INTEGRITY — VERIFIED
```
   V139  6cd7799d63cbd5feb424913761a8f7f387b9f65dc8bfd30e08013bfd9b57121f   49/49
   V148  815aec7e04a655ed13ec2f7e0fcd6ed906191b7f6f2a0345faf5079215879071   69/69
   V149  6c39034055503e6e2e61576f40096d31102e04493ec248e53f5d0930390f2a9f   52/52
   V150  d6aae5ee8b79f68bb52c040c82aa0f674e537818f23c1ba5081a9d56bc690ab3   51/51
   all four rebuild BIT-IDENTICALLY; both repos clean; every capped file under 256 KB
```


---

🛑 **1 older section(s) moved to `docs/archive/STATE-ARCHIVE-2026-08-28.md`** to hold this file under the 145 KB target.
