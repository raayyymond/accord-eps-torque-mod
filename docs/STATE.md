# STATE — living current state of the kit

## 🛑🛑🛑 **NO CAL EVER FLOWN MOVES THE CREEP GRIND — THE STRATEGIC RESULT OF THIS SESSION**
With a working endpoint (noise floor **1.8×**), every cal the kit has tuned can finally be tested
against it. **None of them separates the builds.**
```
   all 8 scoreable routes span   0.0640 - 0.1549 = 2.42x        (noise floor 1.8x)

   gain    3564 (4x): 0.0832 (n=4)   5346 (6x): 0.0877 (n=4)   ratio 1.05x   NO EFFECT
   alpha2  14: 0.0866 (n=1)          22: 0.0887 (n=7)          ratio 1.02x   NO EFFECT
   knee    300: 0.0887 (n=3)         600: 0.0866 (n=5)         ratio 1.02x   NO EFFECT
   K1      constant among scoreable routes

   V96's OWN TWO ROUTES:  0.0640 vs 0.0955 = 1.49x
   => one build's route-to-route spread is MOST of the entire 2.42x range across all builds.
```
⇒ **[EVIDENCE] across gain 4×/6×, α2 8–22, knee 300–3000 and K1 204–1020, NO calibration this
kit has ever flown has a detectable effect on the creep grind.**

### ⭐ WHAT THIS REFRAMES
**~30 builds of cal tuning — the gain ladder, the α2 ladder, the knee/K1 relay ladder — all moved
cals that are now measured INERT for this symptom.** That is consistent with the whole run of nulls
and near-nulls those families produced, and it explains them at a stroke.
⇒ **Either the controlling cal has never been flown, or the grind is not cal-controllable.**
⇒ **This is precisely why V147 is the right next build**: `0xC61F6` (the r24 pump-lane deadband) is
a cal **NEVER FLOWN**, on a lane (`gp-0x6ADA`) **NEVER PROBED**. Every prior build moved cells now
shown to be inert. ⊕ The same argument elevates the `0xC4124` slot disable, also never flown.

### ✅ AND IT CLEARS THE 8× GAIN FOR AUTHORITY
`gain 4× vs 6× = 1.05×` on the clean endpoint, agreeing with the earlier 12-route direct null and
with the 19-route regression (p = 0.173). ⇒ **the LKAS gain does not drive the creep grind**, so
**V142 (8× + matched clamps) is not a grinding risk** — it remains gated behind a confirmed grind
fix only because the operator's instruction made it conditional, not because the evidence implicates
it. ⚠ no 8× route passes the n≥90 gate, so 8× itself is untested on this endpoint.

### ⭐ THE HONEST SUMMARY OF THE WHOLE SEARCH
```
   families CLOSED by measurement   b26 (clamp/a2/knee/K1) | the notch | base-assist damper
                                    gp-0x6BBE | and now EVERY flown cal
   levers NEVER FLOWN, still open   0xC61F6 pump deadband (V147)  |  0xC4124 slot disable
   the only instrument that has     the OPERATOR'S REPORT -- V133's regression came from his ear,
   ever resolved a build             not from any scorer in this kit
```

## ✅✅✅ **A WORKING BETWEEN-BUILD ENDPOINT, RECOVERED — NOISE FLOOR 1.8×, DOWN FROM 36×**
The previous section retired the engaged/manual RATIO endpoint on a 20–36× noise floor. **The
diagnosis pointed straight at the fix**: it is a **RATIO**, and it explodes when the manual arm is
small — **r9e scored 1520.81 on 39 manual windows.** Two changes rebuild it:
```
   1. a SHARE, not a ratio:  (18-22 Hz power) / (1-45 Hz power), ENGAGED, at creep
      bounded in [0,1] -- it CANNOT explode however small the denominator gets
   2. a MINIMUM EXPOSURE gate: n >= 90 engaged creep windows ~ 2 MINUTES of engaged creep
      the low-n routes (r81 n=45, r96 n=70, r9e n=57) were the outliers driving the residual spread
```
```
   identical-cal noise floor      all n        n >= 90
      gain3564 a2:22 knee600      7.22x         1.62x   (4 routes)
      gain5346 a2:22 knee300      5.59x         1.79x   (3 routes)
   => a build effect must exceed ~1.8x to mean anything.   A 20x RESOLUTION IMPROVEMENT.
```
```
   route build     SHARE      n    gain   a2  knee        route build     SHARE      n
   r7e   V96      0.0640     98    3564   22   600        r7f   V96      0.0955     95
   r79   V92      0.0709    106    3564   22   600        r77   V90      0.1038    260
   r21   V111     0.0866    135    5346   14   600        ra4   V104     0.1549    110
   ra6   V106     0.0867    108    5346   22   300
   r1e   V107     0.0887    143    5346   22   300
```

### ✅ AND IT SETTLES THE KNEE WITH A PROPER INSTRUMENT
```
   knee 300   n=3 routes   median SHARE 0.0887
   knee 600   n=5 routes   median SHARE 0.0866      <-- IDENTICAL
```
⇒ **the knee has NO measurable effect.** That **independently CONFIRMS** the retraction of
*"knee = 300 is catastrophic"* rather than merely withdrawing it — the first time this session a
retraction has been replaced by a positive measurement instead of a gap.

### 🛑 TWO HONEST CAVEATS
1. **The n ≥ 90 gate was chosen AFTER seeing which routes were outliers.** A minimum-exposure
   requirement is defensible a priori and 90 windows ≈ 2 min is a physical threshold rather than a
   fitted one — **but the specific number is post-hoc and wants validation on new data.**
2. **Only 8 cached routes qualify.** **V112 (n = 52, 24) and V122 (n = 45) do NOT** ⇒ **the build
   currently on the car has never had enough engaged creep exposure to be scored at all.**

### ⭐ THE DRIVE REQUIREMENT THIS CREATES — CONCRETE AND ACTIONABLE
```
   >= 2 MINUTES of ENGAGED CREEP  (1-24 km/h, hands off, with real steering activity)
```
Without it the drive is unscoreable on the only endpoint that works. **The scorer refuses rather
than guessing**: `r24` (V122, n=45) returns *NOT SCOREABLE*; `r77` (V90, n=260) returns a verdict.
✅ Shipped as **`rlog-tools/score/score_creep_share.py`**, with `--floor` to re-derive the noise
floor from the identical-cal groups on demand.

## 🛑🛑🛑 **THE BETWEEN-BUILD ENDPOINT HAS A 20–36× NOISE FLOOR — EVERY BUILD COMPARISON THIS SESSION IS RETRACTED**
The obvious control was never run: **what do routes with IDENTICAL control cals score?**
```
   gain 3564, a2 22, knee  600, K1 204   n=6   SPREAD 19.9x
        V92/r79 2.60   V96/r7f 9.59   V91/r78 10.21   V96/r7e 11.12   V90/r77 26.36   V98/r81 51.81
   gain 5346, a2 22, knee  300, K1 204   n=6   SPREAD 36.2x
        V106/ra6 42.01  V107/r1e 47.30  V105/ra5 52.54  V104/ra4 91.75  V102/r96 714.01  V103/r9e 1520.81
   gain 5346, a2 14, knee 1800, K1 612   n=2   spread  1.1x     <- the "precision" pair; n=2 is LUCK
   gain 3564, a2 22, knee  300, K1 204   n=2   spread  3.6x
```
⇒ **SIX routes with the same calibration span 20×; another six span 36×.**
⇒ **NO build comparison below ~36× on this endpoint carries information.**

### 🛑 EVERY COMPARISON MADE THIS SESSION FAILS THAT TEST
```
   V111 4.40 vs V112 4.74   "the knee is NULL"                1.08x   BELOW THE FLOOR
   V112 4.74 vs V122 3.38   "alpha2 IS the lever"             1.40x   BELOW THE FLOOR
   V112 r22 4.66 vs r23 4.82  "3 % repeatability"             1.03x   BELOW THE FLOOR
   knee 600 median vs knee 3000                               1.25x   BELOW THE FLOOR
   knee >= 600 vs knee = 300  "CATASTROPHIC"                 29.35x   BELOW THE FLOOR
```
🛑 **Including the `knee = 300` result recorded one section earlier as the strongest
cross-build effect the kit had ever measured.** The knee-300 group's **own internal spread
(36.2×)** is LARGER than the between-group difference (29.35×) I attributed to the knee.

### 🛑 WHAT IS RETRACTED
1. **"α2 is the creep lever, the knee is null"** — the single-variable ladder. It drove the V137 /
   V138 sizing and the V135 demotion. **The differences were 1.08–1.40× against a 20–36× floor.**
2. **"The endpoint is precise — V112's two routes agree to 3 %"** — two routes of the SAME build is
   the floor's **best case**, not evidence of precision. n=2 and it was luck: the six-route group of
   identical cals spans 19.9×.
3. **"`knee = 300` is catastrophic."**
⊕ The **builds themselves are unaffected** — V137/V138/V135 are still correctly built and bounded.
**Only the RANKING rationale is withdrawn.**

### ✅ WHAT SURVIVES — EVERYTHING THAT IS NOT STATISTICAL
* the **notch's existence, its retune and its validation against the firmware recursion**;
* the **11-slot map** (10 callers → 10 distinct slots, self-validated);
* the **confirmed pump polarity** (`gp-0x6752 = −1`, verified 3 ways incl. on-car);
* the **r24 deadband's location and continuity**; the **`0xC64FA`/`0xC64FD`** separation;
* the **instrument findings** — probe clipping, the flat-spectrum baseline, the `ld.bu` disp|1 trap;
* and **V133's regression, which came from the OPERATOR'S EAR, not from any scorer.**

### ⭐ THE CONCLUSION THIS FORCES
**This kit has NO working between-build symptom endpoint.** Route-to-route variance is **20–36×**
and every candidate build effect is smaller than that. ⇒ **the operator's own report is the only
instrument with the resolution to tell builds apart**, which is exactly what the kit's own doctrine
already says: ***score bands, let the OPERATOR score symptoms.***
🛑 **A scorer that compares two builds on this endpoint should REFUSE unless the ratio exceeds
~36×.** Anything less is reporting route noise as a result. ⊕ `feedback-episodes-not-windows`
warned about exactly this class of error — *"window bootstraps manufacture significance; get a
split-half null BEFORE quoting any ratio."* **The identical-cal groups ARE that null, and they were
available from the first minute.**

## ✅✅ **THE FIRST CROSS-BUILD REGRESSION ON THE SYMPTOM — 19 ROUTES. ONE ROBUST FINDING.**
Every prior comparison used one or two routes. This uses **all 19 cached routes with a known
build**, scoring each on the validated within-drive endpoint (ENGAGED/MANUAL 18–22 Hz of `cs_rate`
at creep) and regressing against the cals that actually differ between builds.
```
   route build   eng/man   gain  a2  knee    K1        route build   eng/man  gain  a2 knee   K1
   r79   V92        2.60   3564  22   600   204        r82   V99      39.66   3564  22  300  204
   r21   V111       3.90   5346  14   600   204        ra6   V106     42.01   5346  22  300  204
   r24   V122       8.18   5346   8  3000  1020        r1e   V107     47.30   5346  22  300  204
   r22   V112       8.51   5346  14  1800   612        r81   V98      51.81   3564  22  600  204
   r23   V112       9.21   5346  14  1800   612        ra5   V105     52.54   5346  22  300  204
   r7f   V96        9.59   3564  22   600   204        ra4   V104     91.75   5346  22  300  204
   r78   V91       10.21   3564  22   600   204        r95   V101    268.23   7128  22  300  204
   r85   V100      11.11   3564  22   300   204        r96   V102    714.01   5346  22  300  204
   r7e   V96       11.12   3564  22   600   204        r9e   V103   1520.81   5346  22  300  204
   r77   V90       26.36   3564  22   600   204

   Spearman vs log(endpoint):  knee -0.770 (p<0.001) | a2 +0.612 (p=0.005) | K1 -0.477 (p=0.039)
                               gain +0.326 (p=0.173, NOT significant)
```

### ✅ THE ROBUST FINDING: **`knee = 300` IS CATASTROPHIC**
**All nine knee-300 routes are elevated (11 → 1521)**; **every knee ≥ 600 route sits between 2.6 and
51.8.** ⇒ that single cal explains the whole V101–V107 era. ⊕ Nobody is at 300 today (V122 is
3000), so this is a **historical explanation, not a live lever** — but it is the strongest
cross-build effect the kit has ever measured on the symptom.

### 🛑 THE OTHER TWO "SIGNIFICANT" CALS ARE COLLINEAR WITH IT — NOT THREE FINDINGS, ONE
The **gain-holding invariant scales knee and K1 together** (300/204, 600/204, 1800/612, 3000/1020),
and **α2 tracks knee across the build history** (22 at knee 300–600, 14 at 600–1800, 8 at 3000).
⇒ **knee, K1 and α2 are ONE variable in this dataset.** Their separate p-values are not independent
evidence, and no design here can separate them.

### 🛑 AND THE ORDERING ABOVE 600 DOES **NOT** HOLD UP
```
   knee  600  ->  2.60, 3.90, 9.59, 10.21, 11.12, 26.36, 51.81      median ~10.2
   knee 1800  ->  8.51, 9.21                                        median  ~8.9
   knee 3000  ->  8.18                                              n = 1
```
The two best routes are knee 600 — **but so are 26.36 and 51.81.** ⇒ **within-group variance swamps
the between-group difference**; there is **no evidence that 600 beats 1800/3000**, and the earlier
"optimum knee ≈ 600" reading of this table would have been a lucky-route artifact.

### ✅ GAIN IS **NOT** SIGNIFICANT (p = 0.173)
Across 4× / 6× / 8× the gain does not track the symptom. ⇒ **mildly supportive of V142 (8× for
authority) being safe once grinding is fixed**, and consistent with the earlier direct 12-route
8×-vs-grind null. ⚠ One 8× route only (r95), so this is weak.

### ⚠ A CAVEAT AGAINST MY OWN NUMBERS
This run scores **V112 at 8.51/9.21 and V122 at 8.18**; the earlier creep-endpoint run scored the
same routes **4.74 and 3.38**. **Same data, different window parameters, different values.**
⇒ **the endpoint is SENSITIVE TO ANALYSIS CHOICES.** Treat the **ordering** as informative and the
**absolute values as not comparable across analyses.** 🛑 Any future quote of a number from this
table must name the window parameters with it.

## 🛑🛑 **CORRECTION: THE BAND-SHARE RANKING WAS INFLATED BY THE FLAT BASELINE**
The section that named `gp-0x6B4C` *"the highest-ranked grind carrier"* at **22.84 % / 22.50 %**
quoted a raw band share with **no flat-spectrum control**. **For a flat spectrum, ANY 4 Hz window
inside 1–24 Hz holds 17.4 % by construction.** Re-ranked against that baseline:
```
   lane                 route   18-22 Hz   sig/flat   ctl/flat
   11-slot assist sum   r96      25.08%      1.44x      0.47x
   default tap          r23      24.78%      1.42x      0.42x
   11-slot assist sum   r9e      23.95%      1.38x      1.03x   <- its CONTROL is FLAT
   detector input       r1e      20.14%      1.16x      0.54x
   AGGREGATOR OUT       r95      10.94%      0.63x      0.53x
   b26 inertia          r78       9.72%      0.56x      1.10x
   ... every other lane/route     < 1.00x
```
🛑 **NO probed lane shows a strong 18–22 Hz peak.** The best is **1.44× flat** — modestly
elevated, **not** the sharp resonance the 22.8 % headline implied. ⊕ On **r9e the CONTROL band reads
1.03× flat**, i.e. that route's spectrum is **essentially featureless**, so its 1.38× carries almost
nothing.

### ✅ WHAT SURVIVES
`gp-0x6B4C` is still the **most CONSISTENT** candidate — top on **both** its routes and the only
lane above 1.3× twice. The *"default tap"* reaches 1.42× on r23 but **0.53× on r22 and 0.08× on
r24** ⇒ wildly route-dependent and unreliable. ⚠ **But the case is MUCH thinner than stated**, and
the b26 and notch closures **still stand** — they are at **0.43–0.56×** and **0.06–0.27× flat**, far
BELOW baseline, which is a stronger statement than before.

### 🛑 AND THE SLOT DISCRIMINATOR FAILED TOO
The plan was *"pick the slot whose payload is rate/acceleration-derived"*. **None of the five
candidate callers reads a rate or acceleration cell** — only speed (`gp-0x6A62` in slot 8's caller,
`gp-0x6A5E` in slot 6's). Combined with `FUN_0003a8a8` (slot 7) passing an **all-zero payload**,
these read as **thin STATE REGISTRANTS, not assist computers** — which matches `gp-0x6B4C`'s
measured **p50 of 0–26** (r9e's p50 is literally **0**).
⇒ **a mostly-zero, occasionally-spiking signal is BROADBAND**, which is exactly why its raw band
share sat near the flat baseline. **The two findings explain each other.**

### ⭐ THE PROCESS FAILURE, AND IT WAS ALREADY WRITTEN DOWN
`feedback-run-the-control-before-the-measurement`: ***"Run the control BEFORE the measurement —
four claims died to controls in one session."*** **I ran the flat-spectrum baseline AFTER publishing
the ranking, and the ranking did not survive it.** ⊕ That is the **sixth** self-correction today.
🛑 **A band share is meaningless without its flat-spectrum expectation. Compute the baseline in
the same function that computes the share, so the two cannot be reported apart.**

### ⭐ STATUS OF THE `gp-0x6B4C` THREAD
```
   slot map                 COMPLETE and self-validated (10 callers -> 10 distinct slots)
   lever                    IDENTIFIED, cal-only, no cave   (0xC4124[i] 0 -> 5)
   lane is the grind source WEAK -- 1.38-1.44x flat, consistent but modest
   which slot               UNRESOLVED -- the rate-vs-torque discriminator does not separate them
```
⇒ **Not a build candidate at this confidence.** **V147 remains the build to fly**, and its lever
(the r24 pump deadband) does not depend on any of this.

## ✅✅✅ **THE SLOT MAP IS COMPLETE — THE `gp-0x6B4C` LEVER IS NOW AIMABLE**
Ten call sites of `FUN_00025c32` were located by xref, and the slot index each passes was read from
the instruction stream. **`FUN_0003a8a8` was decompiled in full to VALIDATE the method** — it shows
exactly the predicted shape:
```c
   local_1c = 7;                          // <- THE SLOT INDEX, param_1[0]
   cStack_1b = <mode>;                    // param_1[1]
   uStack_1a = 0; uStack_18 = 0; uStack_16 = 0; uStack_14 = 0;
   uStack_12 = 0x400; uStack_10 = 0x400; uStack_e = 0x400;
   uVar6 = FUN_00025c32(&local_1c);
```
⇒ **the LAST `mov imm, rN` before the struct setup is the slot index.** Applied to all ten sites:
```
   slot  caller          call site   0xC4124   status
    0    FUN_0002e52e     0x2E642       0      CONTRIBUTES
    1    FUN_0002b422     0x2B53E       0      CONTRIBUTES
    2    FUN_0003405a     0x34212       5      forced zero   (beside the base-assist damper
                                                              FUN_00034350 / gp-0x6bbe producer)
    3    FUN_0002c246     0x2C374       0      CONTRIBUTES
    4    FUN_00023ad2     0x23BD6       5      forced zero
    5    FUN_00023fe2     0x24176       5      forced zero
    6    FUN_0003aff4     0x3B25C       0      CONTRIBUTES   (beside the aggregator FUN_0003aa2c)
    7    FUN_0003a8a8     0x3A972       0      CONTRIBUTES   <- VERIFIED by full decompile
    8    FUN_0002caa2     0x2CBE6       0      CONTRIBUTES
    9    FUN_000339cc     0x33B5C       5      forced zero
   10    (no caller)         --         0      unused
```
⭐ **TEN callers → TEN DISTINCT slots 0–9, no collisions.** That self-consistency is strong
validation: a wrong extraction rule would produce duplicates and gaps, and it produces neither.

### ✅ AND ONE CONTRIBUTOR IS ALREADY EXCLUDED BY ITS OWN PAYLOAD
`FUN_0003a8a8` passes **all-zero data fields** (`uStack_1a` … `uStack_14` = 0) with unity weights.
⇒ **slot 7 contributes NOTHING numerically** — it is a state/health registrant, not an assist
source. ⇒ **the real contributors are slots 0, 1, 3, 6, 8 — FIVE candidates, each a named
function**, down from "seven unknown indices".

### ⭐ WHAT THIS UNLOCKS
`gp-0x6B4C` is the **highest-ranked grind carrier** (22.84 % / 22.50 % of its own variance in
18–22 Hz, both routes agreeing). `0xC4124[i] : 0 → 5` disables slot *i* using **Honda's own dispatch
value**, on a **byte cal, no cave**. ⇒ **the lever is now aimable at a NAMED subsystem** rather than
an index — the most precise lever this kit has had.
⚠ **Still not built.** Two of the five (`FUN_0003aff4` slot 6, `FUN_0002caa2` slot 8) have not been
read at all, and what each contributes must be known before one is removed — removing an unknown
assist component is the V133 pattern. **Next: decompile slots 0, 1, 3, 6, 8's callers and pick the
one whose payload is rate/acceleration-derived rather than torque-derived.**

**V147 remains the build to fly.**

## ✅✅ **THE 11 SLOTS ARE IDENTIFIABLE AFTER ALL — `FUN_00025c32` IS A REGISTRATION FUNCTION**
The previous section recorded the slots as unidentifiable because they are written through a
computed pointer (`ep = gp-0x62F8 + r12`) and all 14 writer sites use a **loop register**
(`add r1/r6/r8/r12/r14, r30`), so no static offset exists to read. **That is true of the WRITES —
and it was the wrong place to look.**

### ✅ THE STRUCTURE
```c
   undefined1 FUN_00025c32(byte *param_1)
   {
     iVar9 = min(*param_1, 10);                                   // THE SLOT INDEX -- FROM THE CALLER
     ...
     *(short *)(gp-0x62e0 + iVar9*2) = clamp(param_1[2], +-0x4000);
     *(short *)(gp-0x62f8 + iVar9*2) = clamp(param_1[4], +-0x2800);   // <- THE SLOT ARRAY
     *(short *)(gp-0x6274 + iVar9*2) = clamp(param_1[6], +-900);
     *(short *)(gp-0x633c + iVar9*2) = clamp(param_1[8], +-20000);
     *(short *)(gp-0x6230 + iVar9*2) = clamp(param_1[10], 0x400);
     *(char  *)(gp-0x61a0 + iVar9)   = <state 0..5>;               // per-slot LIVE STATE
   }
```
⇒ **it is a REGISTRATION / UPDATE call: each caller registers into the slot named by the FIRST
BYTE of the struct it passes**, and `param_1[1]` is a mode/command (0–5) selecting the update path.
⊕ **`gp-0x61a0` is the per-slot LIVE STATE array** (0–5), distinct from the `0xC4124` cal of the
same shape — the cal is the configured type, the RAM array the runtime state.

### ✅ AND THERE ARE EXACTLY TEN CALLERS, FOR ELEVEN SLOTS
```
   FUN_00023ad2   FUN_00023fe2   FUN_0002b422   FUN_0002c246   FUN_0002caa2
   FUN_0002e52e   FUN_000339cc   FUN_0003405a   FUN_0003a8a8   FUN_0003aff4
```
⭐ **This converts an intractable dataflow problem into a BOUNDED ENUMERATION**: decompile each
caller, read the `param_1[0]` it passes, and the slot map is complete. ⊕ Two of them
(`FUN_0003a8a8`, `FUN_0003aff4`) sit beside the aggregator `FUN_0003aa2c`, and `FUN_0003405a` sits
beside the base-assist damper `FUN_00034350` and the `gp-0x6bbe` producer `FUN_00034a72` — so the
map will name real subsystems, not opaque indices.

### ⭐ WHY THIS MATTERS FOR THE FIX
`gp-0x6B4C` is the **highest-ranked grind carrier** (22.84 % / 22.50 % of its own variance in
18–22 Hz, both routes), and `0xC4124[i] : 0 → 5` disables **one slot** on a **byte cal with no
cave**. **Once the map exists, the lever becomes a single named subsystem removed from the grind
carrier** — the most precise lever this kit has ever had.
🛑 **Still NOT built, and deliberately so.** Disabling an unidentified slot removes an unknown
assist component; that is the pattern that produced V133's regression. ⊕ And a "disable ALL seven
contributors" experiment was considered and **rejected**: `r28` accumulates the weights, four
divide-class instructions exist in `FUN_00027b0a` (0x28168, 0x2820C, 0x2847C, 0x285A0), and while
none of their divisors is `r28` in a direct read, **that scan is not exhaustive and a
divide-by-zero in an EPS control path is not a risk worth taking on an incomplete check.**

### ⭐ STATUS
```
   lane = top grind carrier                     MEASURED, both its routes agree
   lever, cal-only, no cave                     IDENTIFIED   0xC4124[i] 0 -> 5
   slot map                                     BOUNDED -- 10 callers, read param_1[0] from each
```
**V147 remains the build to fly.**

## ✅ **THE `gp-0x6B4C` LEVER IS IDENTIFIED — AND ONE THING BLOCKS IT: WHICH SLOT**
`gp-0x6B4C` is the highest-ranked grind carrier (22.84 % / 22.50 % of its own variance in
18–22 Hz, on both its routes). Its producer `FUN_00027b0a` walks an **11-slot TYPE DISPATCH**:
```
   0x27B26  movea 0x5124, tp, r9      // r9 = &cal(0xC4124), the 11 TYPE CODES
   0x27B32  movea -0x62f8, gp, r10    // the parallel 11-slot DATA array
   0x27B36  mov   0xa, r7             // 10 iterations
   cmp 0x7 / 0x6  ->  r24 += slotdata[i] ; r28 += 0x400     (raw contribution, unity weight)
   cmp 0x5        ->  0x27BDA         cmp 0x4 -> 0x27B98    cmp 0x3 -> 0x27B70
   r24 accumulates the SUM, r28 accumulates the WEIGHTS
```
🛑 **The cal bytes are TYPE CODES, not weights** — I first read them as weights and the kit's own
memory has it right: `0xC4124 = [0,0,5,0,5,5,0,0,0,5,0]` means ***"7 slots raw, 4 forced zero"***
⇒ **type 0 = CONTRIBUTES, type 5 = FORCED ZERO.**
⇒ **the four slots I first called "active" are the DISABLED ones**; the **seven zeros are the
contributors** (indices 0, 1, 3, 6, 7, 8, 10).

### ✅ THE LEVER
```
   0xC4124[i] : 0 -> 5      disables slot i, using Honda's OWN dispatch value
```
⭐ **This is the lever shape the whole search has wanted**: it removes **ONE contributor** from the
highest-ranked grind carrier, using a value the firmware already implements on four other slots, on
a **byte cal**, with **no cave**. Nothing else found this session can subtract a single source.

### 🛑 WHAT BLOCKS IT — AND WHY I STOPPED RATHER THAN GUESSING
**Which of the seven slots to disable is unknown.** The slots are written through a **COMPUTED
POINTER** (`ep = gp-0x62F8 + r12`), so they have no individual gp-relative accesses — a byte scan
finds only the base (15 hits) and cannot attribute them:
```
   slot  0  gp-0x62F8  CONTRIBUTES  15 accesses (the BASE -- all writers alias here)
   slots 1-9           0 accesses each   <- written via base+offset, invisible to a scan
   slot 10  gp-0x62E4  CONTRIBUTES   3 accesses
```
⊕ And spot-reading a writer does not resolve it either: `0x25EA6` is `add r1, ep` + `sst.h r0` —
a **zeroing LOOP** with the offset in a loop register, not a per-slot store.
⇒ **Identifying the seven contributors requires real DATAFLOW TRACING of the 15 writers, not a
scan and not spot disassembly.** 🛑 **Guessing a slot is exactly the error class this session has
committed FIVE times** (V133's clamp · `0xC64FA`≠`0xC64FD` · 18-vs-8 readers · `gp-0x6b5e` · the
`gp-0x6BBE` clamp). **Deliberately not guessing.**

### ⭐ STATUS OF THIS THREAD
```
   lane identified as the top grind carrier      DONE, measured, both its routes agree
   lever identified and it is cal-only, no cave  DONE  (0xC4124[i] 0 -> 5)
   WHICH slot to disable                         OPEN -- needs dataflow tracing of 15 writers
```
**V147 remains the build to fly.** This thread is the most promising *next* direction and it is
blocked on a bounded, mechanical piece of tracing — not on a missing idea.

## ⭐⭐⭐ **WHICH LANE CARRIES THE GRIND — MEASURED. TWO FAMILIES CLOSE, A NEW TARGET APPEARS.**
Last section's rule *"rank lanes by measured p50"* is **WRONG for finding the grind** and is
corrected here: **p50 is a DC/typical magnitude; a small lane can carry all the 20 Hz energy.**
The right ranking is **AC power in 18–22 Hz as a fraction of each lane's OWN variance**, which is
computable from cache for every lane ever probed.
```
   lane                 build/route   18-22 Hz   8-12 Hz(ctl)   ratio
   11-slot assist sum   V103 / r9e     22.84%      17.04%       1.34
   11-slot assist sum   V102 / r96     22.50%       7.32%       3.08
   detector input       V107 / r1e     19.07%       8.85%       2.16
   AGGREGATOR OUTPUT    V101 / r95     10.05%       8.45%       1.19
   b26 inertia          V91  / r78      9.53%      18.77%       0.51
   viscous+pedestal     V92  / r79      9.26%       5.01%       1.85
   b26 inertia          V90  / r77      7.38%      13.57%       0.54
   notch lane           V104 / ra4      4.61%       2.11%       2.19
   notch lane           V106 / ra6      1.07%       2.72%       0.39
   notch lane           V105 / ra5      1.00%       2.09%       0.48
```
⚠ 30–40 Hz ALIASES at 49.9 Hz sampling, so **8–12 Hz is the control band.**

### 🛑 1. `gp-0x6B26` IS **NOT** THE GRIND CARRIER — AND ~15 BUILDS WENT THERE
**Ratio 0.51 and 0.54 — CONSISTENTLY BELOW ITS OWN CONTROL** on both routes that ever probed it.
⇒ **b26 carries LESS 18–22 Hz than 8–12 Hz.** The clamp, α2, knee and K1 builds (V126–V138, and
most of this session) were all aimed at a lane whose 18–22 Hz content is below its own baseline.
⊕ This is consistent with, and explains, the null and near-null results that family produced.

### 🛑 2. THE NOTCH FAMILY IS CLOSED ON A **THIRD** INDEPENDENT COUNT
`gp-0x6B86` reads **4.61 / 1.07 / 1.00 %** on all three of its routes — the **lowest** band content
of any lane measured. Together with (a) the gate that almost certainly never opens and (b) the lane
carrying only p50 6–19 counts, **V144/V145/V146 are retired as candidates.** The notch itself is
real, correctly retuned and validated — **it is simply on the wrong lane, behind a shut gate.**

### ✅ 3. THE NEW TARGET: `gp-0x6B4C`, THE 11-SLOT ASSIST SUM
**22.84 % and 22.50 % on BOTH its routes** — the only lane consistently elevated, and elevated
against its control on both (1.34, 3.08). ⊕ The kit's own memory already flags it:
*"`gp-0x6b4c` is NOT the LKAS command — an 11-SLOT ASSIST SUM"*.
```
   0xC4124  slot :   0   1   2   3   4   5   6   7   8   9  10
            stock:   0   0   5   0   5   5   0   0   0   5   0     (V122 identical)
   => FOUR slots active at weight 5 (indices 2, 4, 5, 9); seven are zero.
   readers: 0x26CDC 0x27B26 0x27CCE 0x27CF2 0x27F24 -- all in the gp-0x6B4C producer region
```
⭐ **A per-slot weight vector on the highest-ranked grind carrier is exactly the shape of lever
this search has been looking for** — it can remove ONE contributor without touching the rest.
🛑 **NOT yet a proposal.** What each of the four active slots SOURCES is unknown, and zeroing one
blindly is the kind of move this session has repeatedly shown to be wrong. **Next step: identify
slots 2, 4, 5 and 9 by tracing the five readers.**

### ⭐ THE CORRECTED RULE
**Rank lanes by their BAND POWER in the symptom band, not by p50.** p50 found `gp-0x6BBE`
(the biggest lane) which turned out to be **torque-dominated 11:1** and therefore neither the grind
source nor a safe lever. Band power found `gp-0x6B4C`, which p50 ranked near the bottom.
**Both rankings are one command; only one answers the question that was being asked.**

## ⭐⭐ **THE CENSUS REFRAMES THE WHOLE SEARCH — THIS KIT HAS BEEN TUNING THE SMALLEST LANES**
The full probe census puts every flown lane on one scale for the first time. **Engaged p50, in the
same units, from routes already in the cache:**
```
   cell        meaning                          p50        max        flown on
   gp-0x6B94   AGGREGATOR OUTPUT (the total)    115-218   1933-3149   V100/r85, V101/r95
   gp-0x6BBE   viscous + DC pedestal             74        352        V92 /r79
   gp-0x6B4C   11-slot assist sum                 0-26     1459-1664  V102/r96, V103/r9e
   gp-0x6B86   notch lane                         6-19     2720-3274  V104-106 / ra4-ra6
   gp-0x6B26   b26 INERTIA term                   2-5       222-318   V90 /r77, V91 /r78
```
🛑 **`gp-0x6BBE` carries p50 74 against an aggregator OUTPUT of 115-218 — roughly HALF the
entire assist output at creep.** Meanwhile **`gp-0x6B26`, the target of ~15 builds this session and
before (V126–V138: clamp, α2, knee, K1), carries p50 2–5**, and the notch lane carries 6–19.
⇒ **[EVIDENCE] the kit has been spending its builds on the SMALLEST lanes in the aggregator.**
⭐ **A lever's leverage is bounded by how much signal its lane actually carries. Rank lanes by
measured p50 BEFORE choosing what to tune** — the census makes that a one-command check.

### 🛑 AND A FIFTH VALUE-ASSUMPTION ERROR, CAUGHT BY READING
I inferred that `gp-0x6BBE`'s *"p50 73.6 ct FLAT across 0–6 °/s"* meant it was **saturated at its
clamp**, and that the clamp was therefore the lever. **Read the clamp records instead:**
```
   PTR_DAT_000c7970[mode] -> 0xCE080 / 0xCE098 / 0xCF080 / 0xCF098   (all four modes identical)
        n=5   X = [0, 640, 2560, 5760, 6400]   Y = [512, 512, 512, 512, 512]
```
⇒ **the clamp is FLAT at 512, and the lane runs p50 74 / max 352 — it NEVER reaches it.**
⇒ **the pedestal is GENUINE, not a clamp artifact, and the clamp is NOT the lever.**
⊕ That is the **fifth** value I have assumed rather than read this session. Checking it cost one
command. **The rule stands and is now cheap to obey: read the table before building the theory.**

### ✅ WHAT THE DOMINANT LANE ACTUALLY EXPOSES (`FUN_00034a72`, the only writer)
```c
   iVar29 += ((gp-0x4f60 * 32 - iVar29) * cal(0xC6372)) >> 10          // torque-sensor EMA
   iVar27 = ((gp-0x6c2e * cal(0xC6370)) >> 5) * sign(gp-0x6752) + iVar29 >> 5
   ...
   gp-0x6bbe = clamp(iVar21, +- LERP(gp-0x6a62))                        // clamp 512, never reached
```
```
   0xC6370 = 2560   weights gp-0x6c2e (the ACCELERATION twin) into the lane's input
   0xC6372 =  205   the torque-sensor EMA alpha = 205/1024, matching the kit's own record
```
⭐ **`0xC6370` is structurally the same KIND of lever as α2 — an acceleration weight — but on a
lane carrying 15–35× more signal.** ⚠ **NOT yet a proposal**: `gp-0x6bbe` is an ASSIST lane, so
reducing it makes steering HEAVIER, which cuts against the operator's first goal. That trade has to
be sized before anything is built. **[BELIEF] it is the highest-leverage unexplored target in the
aggregator; [UNKNOWN] whether its ratchet content can be reduced without the weight cost.**

⭐ **This does not change the flight: V147 is still the build.** It changes what comes AFTER.

## 🛑🛑 **TWO DIRECT MEASUREMENTS FROM CACHE — ONE CORRECTS THE SECTION ABOVE, ONE KILLS THE NOTCH FAMILY ON ITS OWN**
A tap census across all build images showed the two cells that matter had **already been flown**:
`gp-0x6C2C` by V107–V110 (routes **r1b, r1e**) and `gp-0x6B86` by V104–V106 (routes **ra4, ra5,
ra6**). ⊕ I had just written *"the answer was already in the cache"* as a lesson and **still had to
run the census to find these** — the lesson needs a TOOL, not a note.

### 🛑 1. THE DETECTOR-INPUT MEASUREMENT IS **CENSORED** — IT DOES NOT CONFIRM THE BACK-SOLVE
```
   r1e (V107, sar 3)  engaged  n=49,089   p50  123   p99 1637   MAX 1637
   r1b (V107, sar 3)  manual   n= 5,999   p50   38   p99 1637   MAX 1637
   427 wire SATURATED (>=1023) on 3.2 % of engaged / 4.7-5.4 % of manual frames
```
🛑 **The probe clips at wire 1023 = |c2c| 1637**, and **3.2 % of engaged frames sit ABOVE it,
unmeasured.** The detector threshold is **12800 — 7.8× above the clip point.**
⇒ **this measurement CANNOT settle whether the gate opens, and the section above must not be read
as confirming it.** The V90 back-solve remains the better evidence **precisely because it was
UNCLIPPED** (wire max 199 against a 1023 saturation) — but it is an inference, not a direct read.
⊕ **Corrected status: [BELIEF, well-founded] the gate never opens. NOT [EVIDENCE].**
⊕ **And this is why V147 carries the gate probe**: `gp-0x6c24` is a **binary** mirror, so it
**cannot clip**. It settles in one drive what a censored analogue probe could not.

### 🛑 2. THE NOTCH LANE IS LIVE BUT **TINY** — AN INDEPENDENT REASON THE FAMILY IS LOW-VALUE
```
   ra4 (V104, sar 4)  engaged  p50 19   p90 141   max 2602   frac ZERO 0.114
   ra5 (V105, sar 4)  engaged  p50 10   p90  70   max 2557   frac ZERO 0.173
   ra6 (V106, sar 4)  engaged  p50  6   p90  16   max  125   frac ZERO 0.314
```
✅ `gp-0x6B86` **is active** (only 11–31 % of frames read zero) — so the *"lane is dead"* branch of
the V143/V144 scorers is refuted in advance.
🛑 **But it carries p50 ≈ 6–19 counts of a ±12288 range — about 0.1 % of its own gate.**
⇒ **even if the notch DID run, it would be filtering a lane with almost nothing on it.**
⇒ **the notch family is weak on TWO INDEPENDENT counts**: the gate probably never opens, and the
lane it filters is small. **V144/V145/V146 stay built and recorded, but they are not the answer.**

### ⭐ WHAT THIS DOES TO THE PLAN — NOTHING CHANGES, WHICH IS THE POINT
**V147 remains the build to fly.** Its live lever (the r24 pump deadband) does not depend on the
gate, and its binary probe settles the gate question without clipping. ⊕ The two measurements above
did not change the recommendation — **they changed the CONFIDENCE behind it, and retired an
[EVIDENCE] mark that had not been earned.**

## 🛑🛑🛑 **THE NOTCH GATE ALMOST CERTAINLY NEVER OPENS — V144/V145/V146 ARE INERT.  FLY V147.**
Before spending a drive on the notch, I back-solved the one quantity its gate depends on. **It does
not reach the threshold.**

### THE BACK-SOLVE, FROM A DIRECT MEASUREMENT ALREADY IN THE CACHE
**V90 tapped `gp-0x6B26` DIRECTLY** (tap `0x94DA`, sar 3) and route **r77 measured a 427 wire max of
199** — far from the 1023 saturation, so **318 is a TRUE maximum**, not a clipped one.
```
   b26 = ((|c2c| * |Y|) >> 6) * 0x111 >> 0x12      =>      |c2c| = b26 * 61440 / |Y|
   mode records (all four modes):  X = (0, 1280, 5760)   Y = (-9830, -5734, -1966)

      |Y| = 9830  (creep, index near X[0])   ->   |gp-0x6c2c| max  ~  1,990
      |Y| = 5734                             ->   |gp-0x6c2c| max  ~  3,412
      |Y| = 1966  (the smallest Y anywhere)  ->   |gp-0x6c2c| max  ~  9,950
      detector threshold cal(0xC620A)        =         12,800
```
⇒ **under EVERY attribution `|gp-0x6c2c|` stays BELOW 12800** ⇒ the reversal counter never
increments ⇒ **`gp-0x671a` never reaches 5** ⇒ **THE NOTCH GATE NEVER OPENS.**
⊕ And **V122 runs α2 = 8 against V90's 22** — *more* smoothing on the same signal ⇒ its
`gp-0x6c2c` peaks are **LOWER still**. **The conclusion STRENGTHENS on the newer base.**
⇒ **[BELIEF, well-founded] V144, V145 and V146 are INERT** — not harmful, inert. The notch is
real, correctly retuned and validated against the firmware's own recursion; it simply never runs.

### ✅ V147 IS THE BUILD TO FLY — A LIVE LEVER *AND* THE DEFINITIVE TEST
```
   0xC61F6   r24 pump-lane DEADBAND   3 -> 96     THE LIVE LEVER (V140/V141's, unchanged)
   0x55DF2   427 tap -> gp-0x6C24                 the gate-state mirror
   0x55E10   packer sar 3 -> 1                    or BOTH gate values map to wire 0 -- BLIND
   4 payload bytes: 1 FUNCTIONAL + 3 telemetry.   67/67.
   image d4a02872aecea638afe4f9741938c7c396d1f1b02468e7570b1ac6a3be7656d6
   rwd   f7446a67b30c80e7216b7d915f97aabc09089e936066f2ff7ade3338eda3355f
```
⭐ **The deadband does NOT depend on the gate** — it acts on the r24 lane every tick. So the drive
carries a real fix attempt **and** settles a whole build family:
```
   gate OPEN duty > 0    ->  the back-solve is WRONG, the notch CAN run  ->  fly V146 next
   gate OPEN duty = 0    ->  back-solve CONFIRMED  ->  RETIRE V144/V145/V146; the notch family is
                             closed unless 0xC64FA can be moved, which is its own open question
```

### ⭐ THE METHOD POINT
**The answer was already in the cache.** V90 flew the exact probe needed, on the exact cell, with a
known scale — four builds were designed around a gate whose input had already been measured.
🛑 **Before designing around a threshold, back-solve whether the quantity ever REACHES it from
data already flown.** That is the same lesson as *"the answer to the session's central question was
already in the cache"* (r77/V90, recorded earlier) — **and it has now paid twice.**

## ✅✅ **V146 VALIDATED END-TO-END BY SIMULATING THE FIRMWARE RECURSION ITSELF**
Three checks against the recursion **transcribed from `FUN_000352b4`**, not against the frequency
response alone — because "the recursion I read IS the designed filter" had been an ASSUMPTION.
```
   filter            f Hz   max|y| all   max|y| tail   predicted |H|*12
   HONDA 55.2        20.3      10.504        10.504         10.504
   V146  20.3 r.96   15.0       8.262         8.223          8.224
   V146  20.3 r.96   18.0       8.156         4.353          4.353
   V146  20.3 r.96   20.3       8.416         0.000          0.000
   V146  20.3 r.96   22.0       8.602         3.310          3.310
   V146  20.3 r.96   25.0       8.912         7.675          7.675
```
✅ **1. `tail` == `predicted` to 4 decimals at EVERY frequency, for BOTH coefficient sets** ⇒ **the
transcription is correct.** The assumption is now checked.
✅ **2. Honda's filter passes 10.504 of a 12 input at 20.3 Hz** — **as shipped it does nothing for
an 18–22 Hz grind.** V146 passes **0.000**, and across the band **4.35 @ 18 Hz / 3.31 @ 22 Hz**
against Honda's 10.84 / 10.22.
✅ **3. The alarming `max|y|` is PURELY the startup transient.** Settling ≈ `1/((1−r)·fs)`:
**25 ms at r = 0.96 vs 50 ms at r = 0.98** ⇒ **the wider notch also settles TWICE AS FAST**, which
matters if the gate chatters open/shut. ⭐ An argument FOR V146 that was not anticipated when it
was sized.

### ⚠ CLIPPING — CHECKED, AND NOT INTRODUCED BY THE RETUNE
The filter output is clamped to **±12** before the ×1024 scale.
```
   excitation (full scale)     HONDA      V144 r.98    V146 r.96    alt r.94
   step to 12                  12.507       13.837       13.812      13.939
   square +-12 at 5 Hz         13.014       15.431       15.592      15.886
```
🛑 **Honda's OWN coefficients clip it too.** ⇒ clipping is **inherent to this stage at full-scale
excitation**, is a **bounded saturation** rather than an instability, and **barely moves with r**
(15.89 at 0.94 → 15.43 at 0.98) ⇒ **it is not a consequence of the width choice.** V146 overshoots
Honda by ~20 % on a square; that is the honest cost, and it is transient-only.

## ✅✅✅ **THE NOTCH RE-SIZED FROM MEASURED DATA — V146 SUPERSEDES V144/V145**
After four claims this session that rested on **assumed** values, I measured the one that sizes the
best lever: **where the grind actually is.**
```
   dominant 14-30 Hz peak of cs_rate, ENGAGED, 1-24 km/h (the creep symptom regime),
   pooled over 12 cached routes spanning V90 -> V122:
        n = 1180 windows    p10 14.84   p25 17.19   p50 20.31   p75 21.88   p90 23.44 Hz
```
✅ **The CENTRE was right** — p50 = **20.31 Hz**, so V144's 20.0 was within 0.3 Hz.
🛑 **The WIDTH was NOT.** At r = 0.98 only **68.2 %** of those peaks fall inside the −3 dB band
⇒ **nearly a third of the grind was escaping the notch.**

### ✅ RE-SIZED AGAINST THE EMPIRICAL DISTRIBUTION (mean |H| evaluated AT the measured peaks)
```
    f0    r     mean|H|   frac < -3dB    -3dB span      Nyquist lift
   20.0  0.98    0.5138      0.682       16.9-23.1         1.026     <- V144 / V145
   20.0  0.96    0.3513      0.894       14.4-25.5         1.105
   20.3  0.96    0.3468      0.899       14.7-25.8         1.102     <- V146
   20.3  0.94    0.2754      0.982       13.0-27.4         1.235     (HF lift too high)
```
⇒ **1.48× more attenuation across the ACTUAL grind distribution, coverage 68 % → 90 %**, for a
10 % lift at 500 Hz.
```
   A = -1.90440325  0xC60A8      C = -1.98375338  0xC60B0
   B = +0.92160000  0xC60AC      D = +1.05848204  0xC60B4
   |H| DC 1.000000 | 1 Hz 0.9994 | 3 Hz 0.9941 | 18 Hz 0.363 | 20 Hz 0.050 | 22 Hz 0.276
   | 25 Hz 0.640 | 30 Hz 0.908        image 15e1cd30...   rwd 664d78f5...   80/80
```

### ⭐ THE NO-BOOST GATE WAS REPHRASED, NOT RELAXED — AND IT IS NOW STRICTLY STRONGER
V144's gate demanded **peak |H| ≤ 1.05**; at r = 0.96 the peak is **1.102**, so the old bound would
have **vetoed the better filter**. But in a unity-DC notch the peak is **ALWAYS the NYQUIST end**
(500 Hz) — a monotone HF shelf, not a resonance. The thing that gate exists to catch is a
**RESONANT peak NEAR the notch**, which is exactly what my first retune attempt produced
(**3.82 = +11.6 dB just below the notch**, boosting 15 Hz while notching 20 Hz).
⇒ the gate now asserts **BOTH** that the peak is ≤ 1.12 **AND that it occurs above 200 Hz**, i.e.
that it *is* the Nyquist shelf. ⭐ **A magnitude bound alone was the wrong SHAPE of check: it let
the dangerous case through on magnitude while blocking a safe one.**

### ✅ EVERYTHING ELSE IS V145, UNCHANGED
Same base (V122), same binary gate probe on `gp-0x6C24` at sar 1, `0xC64FA` untouched, α2 8, gain
6×, b26 clamp 511, both Lever A arms stock, pump deadband at Honda's 3.
⚠ **The load-bearing BELIEF is unchanged and still unmeasured**: the section arms only when
`gp-0x671a ≥ 5`. If the gate stays shut this build is **INERT, not harmful**, and the probe says so
directly. **Re-sizing the notch does not change that risk — it only makes the notch worth more if
the gate does open.**

## 🛑🛑 **RETRACTION: THE r26/NOTCH-GATE COUPLING IS *UNRESOLVED* — I MARKED IT [EVIDENCE] AND IT IS NOT**
The section above closes *"notch always on"* by asserting that opening the gate **enables the r26
pump**, and marks it **[EVIDENCE]**. **That mark is withdrawn.** The suppression runs through
`gp-0x6b5e`, and I never established its value.
```c
   uVar11 = (gp-0x6b5e != 0);
   if ((uVar11 == 0) || (iVar17 = uVar11 * (uVar13 == 0), uVar13 == 0)) { ...compute r26... }
       uVar11 == 0  ->  the r26 block ALWAYS runs, the GATE IS IRRELEVANT
       uVar11 != 0  ->  r26 is forced to ZERO whenever the gate is shut
```
⇒ **the whole coupling hinges on whether `gp-0x6b5e` is non-zero, and that was ASSUMED.**

### THE PRODUCER, READ PROPERLY (`FUN_000361c8`, the only writer)
```c
   sVar6 = LERP(gp-0x6bda, X @ tp+0x76CE, Y @ tp+0x76D8)
   sVar6 = gp-0x6752 * ((sVar6 * cal(0xC63C2)) >> 10)      // x(-1) x 1024
   gp-0x6b5e = +-sVar6                                      // sign from gp-0x6bf0
   X = [-384, -128, 128, 294, 384]      Y = [0, 4762, 4762, 717, 0]      cal(0xC63C2) = 1024
```
🛑 **TWO errors of my own in one pass, both the same class — assuming a value instead of
reading it:**
1. I first wrote the closure without checking `gp-0x6b5e` at all.
2. Then "refuted" it with a script that put `gp-0x6bda = 0` in the **below-X[0]** branch returning
   `Y[0] = 0`. **Wrong** — 0 lies **mid-table between Y[1] and Y[2] = 4762**, so if the index really
   were 0 the output would be **4762**, i.e. **non-zero**, i.e. the coupling WOULD bite.
3. And the index itself is unknown: the memory `accord-return-centre-and-detent-dead-engaged` says
   the ***"`gp-0x6bda` gate"*** reads 0.0000 — that is a **derived boolean**, NOT the raw cell.

### ✅ THE HONEST STATE
```
   does opening the notch gate enable the r26 pump?      UNRESOLVED
   what would settle it                                  the DISTRIBUTION of gp-0x6bda (or of
                                                         gp-0x6b5e directly) on an engaged drive
   does it change the recommendation?                    NO
```
⭐ **V145 is unaffected**: it deliberately does **not** move `0xC64FA` — it MEASURES the gate. If
the gate already opens with useful duty, the widening question never arises and the coupling is
moot. Only if the gate reads shut does this become load-bearing, and then `gp-0x6b5e` must be
**probed, not reasoned about**.
⭐ **THE LESSON, WHICH THIS SESSION HAS NOW PAID FOR FOUR TIMES:** *the clamp blamed for V133;
`0xC64FA` vs `0xC64FD`; the 18-vs-8 reader count; and now this.* **Every one was a value or an
identity ASSUMED rather than read.** 🛑 **Mark a claim [EVIDENCE] only when the number behind it
was actually read from the image or the logs — a decompile showing WHERE a value comes from is not
the same as knowing WHAT it is.**

## 🛑🛑 **`0xC64FA` FULLY CHARACTERISED — AND "NOTCH ALWAYS ON" IS CLOSED BY A REAL MECHANISM**
Two corrections and one closure, from a reader census plus the disassembly.

### 🛑 1. THE "18 READERS" FIGURE WAS THE `ld.bu` disp|1 TRAP
Every one of the 18 hits encodes **`hw2 = 0x74FB`**, but they split into **two opcode families**:
```
   hw1 & 0xFF = 0x85   ->  Ghidra decodes tp+0x74FA     0x35A02 0x35BE6 0x3AA78
                                                        0x429DA 0x429E2 0x429EA 0x429FC 0x42A08
   hw1 & 0xFF = 0xA5   ->  Ghidra decodes tp+0x74FB     0x260BC .. 0x261A2   (the 10-reader cluster)
   0x3AA78  ld.bu 0x74fa, tp, r14    8577fb74
   0x260BC  ld.bu 0x74fb, tp, r15    a57ffb74      <- SAME hw2, DIFFERENT hw1, DIFFERENT BYTE
```
⇒ **`0xC64FA` has EIGHT readers, not 18**, and the *"unexamined 10-reader cluster"* I cited as the
reason not to touch it **reads `0xC64FB`, a different cal.** ⊕ This is the kit's own documented
trap (`accord-v850-scan-traps-formatv-and-storezero`: *"hw2 = (disp | 1)"*) — my scan matched on
the `D|1` alternative and I reported the union as one cal.

### ✅ 2. ALL EIGHT READERS ARE IN KNOWN FUNCTIONS
```
   0x35A02, 0x35BE6    the NOTCH gate            FUN_000352b4
   0x3AA78             the aggregator branch     FUN_0003aa2c
   0x429DA .. 0x42A08  the reversal counter's own CEIL clamp   (min(revcount, CEIL))
```
⇒ `0xC64FA` is the **CEIL that clamps `gp-0x671a`** *and* the threshold both consumers compare
against. Nothing unexamined remains.

### 🛑 3. AND THAT IS WHAT CLOSES THE LEVER — THE GATE IS COUPLED TO A PUMP
Setting `0xC64FA = 0` would make the notch's condition `0 <= gp-0x671a` **always true** ⇒ the notch
would run continuously, which is exactly what V144/V145 want. **But the aggregator reads the same
cal:**
```c
   uVar13 = (sVar7 == 1);                       // 1 when the gate is SHUT
   uVar11 = (gp-0x6b5e != 0);
   if ((uVar11 == 0) || (iVar17 = uVar11 * (uVar13 == 0), uVar13 == 0)) { ...compute r26... }
```
```
   gate SHUT + gp-0x6b5e != 0   ->  iVar17 = 1*0 = 0   =>  the r26 lane is FORCED TO ZERO
   gate OPEN                    ->  the block always runs  =>  r26 is COMPUTED
```
⇒ **opening the notch's gate ENABLES the r26 PUMP lane, which is currently suppressed.**
`gp-0x6752 = −1` makes r26 a **confirmed pump** — the same family whose **doubling** produced
V133's *"massive, violent grinding"*. ⇒ **[EVIDENCE] the notch's arming is STRUCTURALLY COUPLED
to un-suppressing a pump. `0xC64FA` must not be lowered, and now for a mechanism that is read off
the code rather than asserted.**
⊕ `0xC64FA = 1` is the middle option — it arms the notch on the FIRST reversal instead of the
fifth — but it enables r26 whenever the counter is ≥ 1 instead of ≥ 5, so it buys the notch by
paying the pump. **Same trade, smaller dose.** Not recommended without measuring the gate first.

⭐ **V145's design is therefore correct as built**: leave `0xC64FA` alone and MEASURE the gate.
🛑 **And the fallback if the gate reads shut is NOT to widen it** — it is V141 (the pump
deadband), which moves the r26/r24 family the *other* way.

## 🛑 **CORRECTION: `0xC64FA` and `0xC64FD` ARE DIFFERENT CALS — THE "WIDENING THE GATE RAILS b26" CLAIM IS WRONG**
Twice this session I wrote that widening the notch's gate would *"also force the b26 oscillation
branch to −8192, which V127 found rails the inertia term"*. **That conflated two cells.**
```
   0xC64FA  the NOTCH gate + the aggregator branch   18 readers  incl. 0x35A02, 0x35BE6
                                                                 (both inside FUN_000352b4)
   0xC64FD  the b26 Y-branch in FUN_00036c12          2 readers  0x36A1E, 0x36C42
```
⇒ **disjoint reader sets. Lowering `0xC64FA` would NOT touch the b26 Y branch.**
✅ **The conclusion survives, for a different reason**: `0xC64FA` has **EIGHTEEN readers**,
including a **ten-reader cluster at `0x260BC`–`0x261A2` that has never been examined**. It is still
**not a free lever** — but the specific harm named was wrong, and a future session acting on the
old note would have avoided the right cell for the wrong reason, or trusted the wrong one.
⊕ Both bytes read **5**. The u16 views are 517 (`0x0205`) and 1285 (`0x0505`); the **byte** is what
the code loads (`*(byte *)(tp+0x74fa)`).
⭐ **RULE: two cals three bytes apart, both equal to 5, in the same subsystem, are still TWO CALS.
Run the reader census before asserting a shared consumer** — that census is what caught this.

## 🛑🛑🛑 **A TRUE NOTCH FILTER EXISTS — THE KIT BELIEVED IT DID NOT.  V143 RESOLVES THE ONE THING GATING IT.**
`FUN_000352b4`, the **only** writer of the aggregator lane `gp-0x6B86`, contains a **gated
second-order FLOAT section**:
```c
   if ((cal(0xC649B) == 1) && (gp-0x671a >= cal(0xC64FA))) {        // = 1  and  >= 5
       w[n] = D*x[n] - A*w[n-1] - B*w[n-2]
       y[n] = w[n]   + C*w[n-1] +   w[n-2]
   }
   A = -1.53720  0xC60A8        C = -1.88080  0xC60B0
   B =  0.63462  0xC60AC        D =  0.81731  0xC60B4
   H(z) = D * (1 + C z^-1 + z^-2) / (1 + A z^-1 + B z^-2)
```
✅ **The numerator zeros sit EXACTLY on the unit circle** (`z² + Cz + 1`, |z| = 1) at **±19.88°**
⇒ **a TRUE NOTCH, min |H| = 0.0002 ≈ −74 dB.** Poles |z| = 0.7966 at 15.24° ⇒ **stable.**
⭐ **|H| = 1.0000 at DC and 1.000 at Nyquist — transparent everywhere except the notch.**
⇒ **it costs NO authority, NO added mass, NO added friction.** That is precisely the shape the
operator has demanded all along, and **no other lever in this kit has it.**
✅ **All four coefficients are CALS ⇒ fully retunable with NO code cave.**
🛑 **This falsifies the kit memory *"no notch filter exists anywhere"* (V44).** ⊕ The block at
`0xC60A8` is **already `BQ_ADDR` in every builder, asserted byte-identical** — **the kit had the
ADDRESS but never the FUNCTION**, and asserted it frozen for ~90 builds.

### 🛑 IT CANNOT BE RETUNED YET — THE TASK RATE IS THE BLOCKER, AND THE TWO CASES DEMAND OPPOSITE EDITS
The notch ANGLE is fixed at 19.88°; its **FREQUENCY is 19.88/360 × fs**:
```
   fs  250 -> 13.8 Hz      fs  333 -> 18.4 Hz      fs  500 -> 27.6 Hz      fs 1000 -> 55.2 Hz
```
The kit's own record bounds the assist task (**task 5**) at **≥ 250 Hz and has NEVER pinned it**
(*"task 1 CONFIRMED 1 kHz, task 5 rate was OPEN"*).
```
   at ~333 Hz  Honda's notch ALREADY sits on the 18-22 Hz grind  =>  the lever is the GATE
   at 1000 Hz  it sits at 55 Hz, useless for the grind           =>  the lever is C:
               C_new = -2*cos(2*pi*f/fs);  f = 20 Hz, fs = 1000  =>  C = -1.984229
```
⇒ **THE TWO CASES CALL FOR OPPOSITE EDITS. Guessing is a coin flip on the best lever found.**

### ✅ V143 RESOLVES IT, AND CARRIES THE FIX WHILE IT DOES
```
   V143 = V122 + deadband 0xC61F6 3 -> 96  +  427 tap -> gp-0x6B86
          3 payload bytes: 1 FUNCTIONAL (the deadband) + 2 TELEMETRY (the tap).  64/64.
          image f8d62d242b913f48e2f87b77cbf0bf450faa2b6c94529862c1c0a7e2016a1488
          rwd   2a98f89d5dfca3777615f534bba0b62a75a4287bf319c6556c3c80acec3829c8
```
427 samples at **49.9 Hz** (Nyquist 24.95). A **−74 dB null is unmistakable**, and where it lands
pins fs to a small discrete set:
```
   fs  250 -> null at 13.8 Hz  direct        fs  500 -> 27.6 Hz aliases to 22.3 Hz
   fs  333 -> null at 18.4 Hz  direct        fs 1000 -> 55.2 Hz aliases to  5.3 Hz
```
⊕ The probe also answers **two prerequisites the retune depends on**: is the lane active at all,
and does the gate ever open in normal driving. **If the lane reads dead the notch is irrelevant
however it is tuned** — worth knowing before spending a build on its coefficients.

### ⚠ THE GATE IS NOT ITSELF A FREE LEVER
`cal(0xC649B)` is **0 in STOCK and 1 in V122** (history: V22=0 → V103=1 → V117=0 → V120=1), so the
**ENABLE is already on**. The second half needs `gp-0x671a ≥ cal(0xC64FA) = 5`, the reversal counter
at its ceiling. Lowering `0xC64FA` would arm the notch more readily — **but that same cal selects
the Y branch in `FUN_00036c12` and gates two aggregator branches, and `gp-0x671a` has four external
consumers.** 🛑 **Not a clean lever; do not move it casually.**

### ⚠ AND A TRAP CAUGHT IN FLIGHT
The first read of these coefficients used `0xC70A8` and returned **denormals (1.35e-39)** — the
**off-by-0x1000 tp error the index warns about, now SIX occurrences.** `tp = 0xBF000`, so
`tp+0x70A8` is **`0xC60A8`**. The denormal values were the tell. **Anchor every tp-relative read
against a plausible value before building on it.**

## ✅✅✅ **AUTHORITY AND "PEAK COMMAND OSCILLATION" MEASURED — TWO OF THE THREE TARGETS COLLAPSE INTO ONE**
The session had spent itself on grinding. Measuring the operator's other two targets on **r24
(V122, the best build on the car)** changes the plan.

### ✅ 1. "PEAK COMMAND OSCILLATION" IS **NOT IN THE COMMAND**
Spectral split of `sc_tq` (openpilot's LKAS request), engaged windows, fs = 100 Hz:
```
                             0.5-3 Hz    3-8 Hz   8-15 Hz  15-22 Hz  22-30 Hz
   PEAK  (|cmd| p50 > 2048)    90.84%     0.93%     0.07%     0.13%     0.01%
   LOW   (|cmd| p50 <= 2048)   82.59%     5.10%     1.38%     0.71%     0.21%
```
🛑 **At peak the command is CLEANER, not dirtier** — HF content **falls** (15–22 Hz: 0.13 % vs
0.71 %; 3–8 Hz: 0.93 % vs 5.10 %). ⇒ **openpilot's command does not oscillate at peak.**
⊕ This independently reproduces the kit's own `reference-accord-lkas-lane-is-a-lowpass`: the LKAS
lane is a ~1–5 Hz low-pass, so **a fast vibration cannot be COMMANDED**.
⇒ **[EVIDENCE] what the operator feels as "peak command oscillation" is generated DOWNSTREAM,
inside the EPS. It is the SAME problem as the grinding, not a second one.**
⇒ **Two of his three targets are one target.** Do not build a separate lever for it.
⚠ n = 25 high-command windows on one route — indicative, not tight. More peak exposure would
firm it, but the direction (HF *falls* at peak) is the opposite of the hypothesis, which is the
robust part.

### 🛑 2. AUTHORITY IS CAPPED ON **openpilot's** SIDE, AND EPS GAIN HAS NOT RELIEVED IT
```
   route  build   engaged frames   rail duty at |cmd| >= 4095   |cmd| p50   p90
   r78    V91          61,987            2.58 %                    230      901
   ra6    V106        123,802            3.02 %                    133      789
   r1e    V107         99,910            2.77 %                    247     1168
   r21    V111         83,782            3.24 %                    187     1390
   r22    V112         48,957            3.79 %                    232     1459
   r23    V112         40,103            1.81 %                    198     1048
   r24    V122         58,652            2.70 %                    149      734
```
openpilot sits at its **own ±4096 request limit on ~2–4 % of engaged frames on EVERY build**, and
**that duty does NOT fall as EPS gain rises** (V91 through V122 span 4×→6× with no trend).
⇒ The request ceiling is openpilot's, and `feedback-no-openpilot-side-modifications` forbids
touching it. **The ONLY authority lever available is the EPS gain `0xC6CD0`.**
⚠ Rail duty is confounded by road/curvature across routes; the *absence* of a trend is weak
evidence, not proof that gain does nothing for authority.

### ⭐ 3. WHICH PUTS AUTHORITY AND GRINDING IN TENSION THROUGH **ONE CELL** — AND FIXES THE ORDER
```
   0xC6CD0   5346 (6x)  ->  7128 (8x)     +33 % authority
                                          ... and it flew in V133, which the operator described as
                                          "massive, violent grinding after enabling LKAS"
```
His two instructions are *"just go to 8x IF you decide to increase LKAS gain"* and *"If youre going
to increase gain make sure we dont get even more oscillation and grinding."* ⇒ **the gain rise is
CONDITIONAL on the grinding being fixed first.**
⭐ **THE SEQUENCING THIS DICTATES:**
```
   1. FIX THE GRINDING on a 6x base      -> V141 (pump deadband + the probe that sizes it)
   2. ONLY THEN raise 0xC6CD0 to 8x      -> with clamps 0xC61B2/4 3072 -> 4096 to match
                                            (unmatched clamps throw away 25 % of the rise)
   3. re-check grinding at 8x            -> if it returns, the grind fix was insufficient, not the gain
```
⇒ **8× is not abandoned — it is DEFERRED behind the fix, which is exactly what the operator's
own conditional says.** A build that raises the gain before the grind is fixed cannot satisfy him
whatever it measures.

## ✅✅✅ **V140 — A DEADBAND ON A CONFIRMED PUMP: THE ONE LEVER THAT SERVES BOTH OPERATOR GOALS**
Decompiling the aggregator `FUN_0003aa2c` to find a finer control than V139's power-of-two shift
turned up something better — **the r24 pump lane already HAS a deadband, and Honda ships it at
essentially zero.**
```c
   uVar13 = (pcVar10 * uVar11) >> 10;              // 0x3AC20  sar 0xa, r8
   uVar12 = *(ushort *)(tp + 0x71f6);              // cal 0xC61F6  = THE DEADBAND  = 3
   if      (uVar13 >  uVar12) iVar17 = uVar13 - uVar12;   // SUBTRACT, not clip
   else if (uVar13 < -uVar12) iVar17 = uVar13 + uVar12;
   else                       iVar17 = 0;                 // the DEAD ZONE
   iVar17 = iVar17 * *(char *)(gp - 0x6752);       // x (-1)   <- THE PUMP
   iVar16 = clamp(iVar17, +-0x2000);               // +-8192 of a +-10240 aggregator total
```
🛑 **Honda's value is 3 counts — 0.037 % of the lane clamp.** That is a quantization floor,
**not a functional dead zone**: any micro-oscillation passes straight into the pump.

### ⭐ WHY THIS SHAPE OF LEVER IS THE ONE THE OPERATOR ASKED FOR
His standing instruction: *"We want both: low apparent steering mass and friction to LKAS AND no
ratcheting."* Every other lever in this kit trades one against the other. **A deadband on a pump
lane does not**: it removes the pump where the signal is **SMALL** — which is what grinding,
ratcheting and stuttering **ARE** — and leaves **LARGE** steering commands essentially untouched,
so **LKAS authority does not pay for it.**

### ✅ THREE FACTS THAT MAKE IT SAFE
1. **IT IS CONTINUOUS.** The deadband **SUBTRACTS rather than clips**, so the transfer curve steps
   `0 → 0 → 1 → 2` across the boundary with **no discontinuity**. ⇒ **there is no notchiness
   mechanism**, which is the usual objection to widening a dead zone on a steering path.
2. **IT REDUCES A CONFIRMED PUMP.** `gp-0x6752 = −1`, verified three ways **including on-car**
   (V98's b3 rung, duty 0.0000 over 17,983 frames / 5 routes), and the config table that sets it
   sits at `0x1000–0x15xx`, **below the `0x13000` floor every `.rwd` writes from** ⇒ no build
   could ever have changed it. Reducing a positive-feedback term cannot destabilise a stable loop.
3. **THE LARGE-SIGNAL COST IS A 96-COUNT OFFSET on a lane that clamps at 8192 = 1.17 %.**

### ✅ AND THE LANE IS WORTH ATTACKING
**Each pump lane clamps to ±8192 against a ±10240 aggregator total ⇒ EITHER lane alone can drive
80 % of the aggregator output.** And **V133 is a fresh, large, on-car demonstration of their
potency**: it doubled both arms and produced *"massive, violent grinding … continues after
disengaging."*

### ⚠ THE DOSE IS THE BELIEF, AND THE FAILURE MODE IS NAMED
```
   x2 -> 6     x8  -> 24     x32 -> 96   <- V140      x64 -> 192
   x4 -> 12    x16 -> 48
```
The lane input is `gp-0x4f62` clamped to ±5120; with `uVar11 ≈ 1024–2048` the lane runs to
5120–8192 full scale. **If** the grind is a 1–3 % of full-scale oscillation it lands near
**50–150 lane counts**, which is what 96 is centred on. ⇒ **[BELIEF] — this kit has NOT measured
the lane amplitude during a grind episode.**
⊕ **If V140 is NULL the next rung is 192, not a different lever** — too-small is the expected
failure mode and it is cheap to step. ⊕ **If the steering feels vague near centre, step back to 48.**

### 🛑 WHAT IT IS NOT
It does **not** touch the **r26** lane, which has **NO deadband** in this function — it runs
straight from its multiply to the polarity and the clamp. Adding one there needs an **instruction**
edit, not a cal, and is a separate decision.

⭐ **RECOMMENDED FIRST** over V137: same one-cal risk profile, but it targets the symptom's
regime directly instead of shaving 1.34× off one lane's HF content, and it is the only build in the
queue that cannot cost authority.

## 🛑🛑 **CORRECTION TO THE V133 ATTRIBUTION — IT IS **LEVER A**, NOT THE CLAMP**
The section above blamed the **clamp** (`0xC407E` 511→1023) as the primary cause of V133's
regression. **The probe data says the clamp was almost certainly INERT.**
```
   route  build   427 wire |x|:  p50    p99     max    frac saturated
   r77    V90                    3.0   67.0   199.0      0.000000
   r78    V91                    1.0   36.0   139.0      0.000000
   r24    V122                   4.0  529.7  1023.0      0.000747   (different tap, not b26)
```
On **V90 the b26 probe never approached its rail** — peak wire 199 back-solves to **|b26| ≈
159–318** against a **511** clamp ⇒ **the clamp was never binding**, reproducing the kit's own
0.0000 % rail-duty measurement. ⇒ **raising it to 1023 changes nothing the term ever reaches.**
⚠ **Not PROVEN inert on V133**, which ran 8× gain and could drive b26 further than V90 did — but
it is now the *least* likely of the three suspects, not the most.

### 🛑 THE PRIME SUSPECT IS **LEVER A**, AND IT IS BIGGER THAN THIS SESSION TREATED IT
`0x3AB76` / `0x3AC20`: **`0xAA` → `0xA9`** is **`sar 10` → `sar 9`** (low 5 bits of the byte) —
**one shift less = ×2 on the arm** — applied to **BOTH** the r24 and r26 **aggregator** arms.
⇒ **+6 dB of loop gain in a lane that is NOT LKAS-gated.**
⭐ **That single edit explains BOTH symptoms**, which neither of the others does:
```
   "violent grinding ... CONTINUES AFTER DISENGAGING"   -> aggregator lane, not LKAS-gated  [OK]
   "grind #2 while DISENGAGED doing a hard turn"        -> its RECORDED signature           [OK]
   the 8x LKAS gain                                     -> engaged-only, CANNOT do either   [NO]
   the clamp                                            -> never reached on V90             [NO]
```
The **8× gain** then added **33 % more excitation while engaged**, which is why it was worst
**right after enabling LKAS** — an amplifier of symptom 1, not its cause.

### 🛑 AND THE SUBTLETY THAT MADE THIS LOOK SAFE
The memory `accord-v62-fixed-the-grinding` says ***"2× ≈ OPTIMUM, not a point on a ramp"*** — and
V62's fix was real (18–22 Hz down **8–42×**). **But that optimum was measured on V62's OWN base,
a 4×-gain build.** Transplanting the same ×2 onto a **6×/8×-gain** modern base is **not the same
edit**: the arm doubles a signal that is itself larger. ⇒ **[EVIDENCE] a lever's measured optimum
does not travel across a base that changed the magnitude of what the lever multiplies.**

### ✅ WHAT THIS CHANGES, AND WHAT IT DOES NOT
**Does not change the recommendation.** **V137 = V122 + α2 8→5** holds both Lever A arms at stock,
the gain at 6× and the clamp at 511 ⇒ **it avoids all three suspects regardless of which is
guilty.**
**Does change what to avoid, and what is cheap to try later:**
```
   Lever A (BOTH arms)   PRIME SUSPECT.  Do not restore onto a 6x/8x base without re-deriving
                         the dose.  A future r26-ONLY test is the way back in, NOT both arms.
   8x LKAS gain          amplifier.  Stays at 6x until grinding is settled.
   0xC407E clamp         probably INERT -- do NOT spend a build lowering it, and do not record
                         it as the cause.  Lowering it would likely be a NULL for the same
                         reason raising it was.
```
⭐ **The reusable rule, sharpened:** *before attributing a regression to a cell, check whether the
quantity that cell bounds ever REACHES it.* One probe-distribution read moved this from the wrong
suspect to the right one, and would have prevented a wasted clamp-lowering build.

## 🛑🛑🛑 **V133 REGRESSED ON-CAR — IT WAS A SIX-VARIABLE BUILD.  V137 IS THE CORRECTION.**
**Operator report, 2026-08-28:** *"V133 has a massive, violent grinding after enabling LKAS which
continues after disengaging. I also got some grind #2 while disengaged and doing a hard turn."*

V133 was presented to him as *"every measured-good edit ever flown"* and as a **clean test of V62's
Lever A**. **IT WAS NOT.** Against **V122** — the last **FLOWN** build, the one he called *"better,
still ever so slight … in rare moments"* — V133 moved **SIX** cells:
```
   cell                                       V122      V133     direction
   0xC407E  b26 clamp = APPARENT MASS ceiling   511      1023     2.00x MORE headroom
   0xC4004    its float twin                    0.5       1.0     (matched, correct per se)
   0x3AB76  Lever A r26 arm                    0xAA      0xA9     restored
   0x3AC20  Lever A r24 arm                    0xAA      0xA9     restored
   0xC40DC  alpha2                                8         5     the one GOOD direction
   0xC640A  oscillation branch Y              -8192     -1966     de-fanged
   0xC6CD0  LKAS gain                          5346      7128     6x -> 8x, +33 % EXCITATION
```

### 🛑 EACH SYMPTOM MAPS TO A DIFFERENT EDIT — AND BOTH WERE ALREADY ON RECORD
**1. "grind #2 while DISENGAGED doing a hard turn" → LEVER A's r24 ARM (`0x3AC20`).**
The LKAS gain is **engaged-only** and cannot produce a **disengaged** symptom; the r24 arm is in the
**aggregator** and is **not LKAS-gated**. And the kit's own memory says it outright —
`accord-v81-carries-neither-grind1-fix`: ***"Lever A = V62's sar×2 (r24 half CAUSED grind #2)"***.
⇒ **the half with a RECORDED history of causing this exact symptom was restored anyway. The record
existed and was not checked before the build was recommended.**

**2. "massive violent grinding … CONTINUES AFTER DISENGAGING" → THE CLAMP (`0xC407E`), with the 8×
gain as a likely amplifier of its onset.**
`gp-0x6b26 = −K·acceleration` is **APPARENT MASS**. Raising its clamp **511 → 1023 doubles the peak
apparent mass** the lane can deliver — and **less** apparent mass raises ζ and de-resonates, so this
moved it the **WRONG WAY**. **`0xC407E` is NOT mode-gated**, which is exactly why disengaging does
not stop it. The V133 builder sold the edit as *"de-rails without changing linear damping"* — true
only of the **linear region**, and it ignored that **peaks may now reach twice as far**.
⊕ The **6× → 8× gain** adds **33 % more excitation** into a ζ 0.017–0.036 / Q 14–29 resonance,
against the operator's explicit instruction: *"If youre going to increase gain make sure we dont get
even more oscillation and grinding."*

### ✅ THE α2 MECHANISM IS **REINFORCED**, NOT DAMAGED
V133 was, accidentally, **a large experiment in the OPPOSITE direction on the same physical
quantity** — it doubled the ceiling on apparent mass — and it produced a **large worsening**. That
is exactly what *"apparent mass drives this resonance"* predicts. **α2 lowers the same quantity's
HF content and is untouched by this result.**

### ✅ V137 — ONE CELL, ON THE BASE HE LIKED
```
   BASE = V122 (flown, known-good).   0xC40DC alpha2 8 -> 5.   Nothing else.
   1 payload byte, 48/48 assertions.
   image a481ce56e048489617feb5158b4ba3ea78e46dbf26659b604fc51063a9b9bc89
   rwd   749d7e9c3abec45f7c45efcb642720d286f22b9e926ac1b6fba03fb7170188d8
```
Every implicated cell is **asserted BY NAME at its V122 value with the reason attached**: clamp
**511**, float twin **0.5**, **both** Lever A arms stock **0xAA**, oscillation branch at Honda's
**−8192**, LKAS gain **5346 (6×)**. Sizing gate: **8→5 = 1.60×**, no larger than the biggest α2 step
ever flown (**1.75×**, V112→V122).

### 🛑 V133 / V135 / V136 ARE ALL OFF THE FLYABLE LIST
V135 and V136 are **V133-based** and inherit **the clamp raise, the 8× gain and both Lever A arms**.
⇒ **neither is flyable as built**; both need **rebasing onto V122** if their levers are still
wanted. Artifacts renamed `SUPERSEDED-DO-NOT-FLASH-*`.

### ⭐ THE PROCESS FAILURE, RECORDED SO IT IS NOT REPEATED
**A build presented as a test of one lever must differ from the last FLOWN build by that lever
alone.** V133 differed by **six cells, two of them large**, and was recommended for flight with a
scoring plan that **assumed a single-variable comparison**. ⇒ **Diff every candidate against the
last FLOWN image — not against its own build parent — and enumerate the result before
recommending a flight.** The build-parent chain hides accumulated drift; the flown image does not.

## 🛑🛑🛑 **V134 RETRACTED — IT IS INERT AT CREEP, AND THE WHOLE BASE-ASSIST DAMPER FAMILY IS CLOSED**
V134 was recommended in this session as *"the only lever that adds damping where there is
currently NONE at creep"*. **Reading the actual tables refutes it.** The records decode cleanly as
`n, X[0..3], Y[0..3]`:
```
   mode 26   FactorC  X = [2240, 3840, 5120, 8960]   Y = [0, 234, 429, 908]
                      X[0] = 2240 / 64        =  35.00 km/h
             FactorE  X = [  60,  400, 2500, 4000]   Y = [0, 140, 539, 927]
                      X[0] =   60 / 4.7121    =  12.73 deg/s
   V134's edit: 0xD77DA 0 -> 60 and 0xD77EE 0 -> 60  =  FactorC Y[0], the SPEED dead zone
```
⇒ `ch0 = (FactorC(speed) × FactorE(rate)) >> 10`, and **FactorE Y[0] = 0 below 12.73 °/s**, with
the table clamped to Y[0] beneath X[0]. The operator's symptom is the **micro regime, 1–13 °/s**.
⇒ **the product is `FactorC × 0 = 0`. V134 does NOTHING where the symptom is.**
```
   configuration                        CREEP 8km/h 6d/s   HIGHWAY 105km/h 3d/s
   STOCK / V133                                        0                      0
   V134  FactorC Y0=60 only                            0                      0     <- INERT
   V134 + FactorE Y0=40                                2                     24
   FactorC Y0=400 + FactorE Y0=100                    39                     61
   FactorC Y0=300 + FactorE Y0=300                    87                    183
```
⊕ **V134's edit bites ONLY at rate > 12.73 °/s AND speed < 35 km/h** — fast low-speed steering,
i.e. **parking manoeuvres**, not creep micro-steering. It was mis-targeted, not mis-sized.

### 🛑 AND THE FAMILY IS STRUCTURALLY THE WRONG LEVER — IT IS BACKWARDS
Opening `FactorE Y[0]` is the **only** way into the micro regime. But **FactorE is keyed on RATE
ALONE**, so every raise also acts at highway low-rate cruise — and because FactorC is far larger up
there, **every configuration adds MORE damping at HIGHWAY than at CREEP** (24 vs 2 · 61 vs 39 ·
183 vs 87). ⇒ the lever **preferentially adds apparent friction exactly where it is not wanted**,
against the operator's standing instruction: *"Increasing mass and friction should not be our
primary approach … We want both: low apparent steering mass and friction to LKAS AND no
ratcheting."*
⇒ **[EVIDENCE] the base-assist damper cannot be aimed at the micro regime without a larger
highway friction cost. The family is CLOSED for this symptom.** ⊕ This independently re-derives
the kit's own memory *"the base-assist damper CANNOT reach the micro regime"* — which named the
two dead zones but was not applied when V134 was designed. **That memory existed and was missed.**

### ✅ WHICH LEAVES α2 (V136) AS THE FOLLOW-UP OF CHOICE
```
   V136   alpha2 5 -> 2    REDUCES apparent mass, raises zeta, costs NO friction, works at
                           18-22 Hz independent of speed.  Both operator goals, same direction.
   V135   knee 3600        the knee is NULL on the single-variable comparison; fly for the
                           17 % friction cut only, NOT as a grind fix.
   V134   RETRACTED        inert at creep; artifacts renamed SUPERSEDED-DO-NOT-FLASH.
```
⭐ **V133 STILL FLIES FIRST** — it carries Lever A, the only measured fix on this exact symptom.

### ⭐ THE REUSABLE RULE
**A lever gated by a PRODUCT of two tables is only as open as its NARROWEST gate.** V134 opened one
of two and was scored, recommended and nearly flown as though it had opened both. **Before
proposing a table edit, evaluate the FULL product at the operator's actual operating point** —
here, 8 km/h and 6 °/s — rather than reasoning about the single table being edited.

## ✅✅✅ **V136 BUILT — α2 IS A NEW LEVER WITH REAL HEADROOM, AND IT IS SELECTIVE**
The single-variable ladder identified **α2** as the creep lever. This build takes the next rung.
```
   0xC40DC   alpha2   5 -> 2      ONE payload byte.  Base = V133.   65/65 assertions.
   image 8cfdeeeb8f16d2ec0956b60b7db51ce55e33f53d4f1623183170d2c472d65b69
   rwd   818f351cb1ed01aa4b1be389e5a2be8442da0fe3dbc0ebc429896e539085f9c9
```

### ✅ THE MECHANISM PREDICTS THE MEASUREMENT
`H(f) = 64·H1(α0=37/128)·(1−z⁻¹)·H2(α2/64)`, fs = 1000 Hz:
```
   alpha2  |H| 18-22 Hz   build            alpha2  |H| 18-22 Hz  build
       22      7.2300     V91 (= HONDA)         5      4.0982    V133
       14      6.7211     V111 / V112           2      1.8490    V136  <- THIS BUILD
        8      5.4903     V122                  0      LANE DEAD  never ship
   predicted alpha2 14->8 : 1.22x        MEASURED endpoint 14->8 : 1.35x
   predicted V111 vs V112 (same alpha2)  : 1.00x   MEASURED : 1.08x  = the noise floor
```
⊕ **The single-path prediction UNDER-shoots** — exactly what a **second path** would do, and there
is one (below). ⊕ **The physics closes it**: `gp-0x6b26 = −K·acceleration` is **APPARENT MASS**;
less apparent mass raises ζ = c/(2√(km)) ⇒ **less resonant**. ⭐ **Ladder, transfer function and
physics all point the same way — and lowering apparent steering mass is what the operator
explicitly asked for**, so this lever moves **both** his goals the same direction instead of
trading them.

### 🛑 THE BLAST RADIUS — α2 IS A **SHARED** LEVER, NOT A FILTER COEFFICIENT
`gp-0x6c2c` **is this EMA's output** (`FUN_00041464`, `gp-0x6c2c = (short)(state >> 9)`), and a
base-register-filtered scan finds **EIGHT** gp-based accesses:
```
   0x36C1A  FUN_00036c12   the gp-0x6b26 inertia lane            <- the intended target
   0x428FA  0x4292C  0x42968   the hard-reversal DETECTOR cluster (vs cal 0xC620A = 12800),
                               which drives gp-0x671a -- itself a FOUR-consumer variable
   0x4184E  0x41AC2   the writers, in FUN_00041464 itself
   0x71378  FUN_00071272  ld.h -> cvtf.ws -> mulf.s (0x39C90FDB ~ pi/8192)   FLOAT MODEL
   0x7B1A2  FUN_0007B022  ld.h -> mulf.s, alongside tp+0x623c (0xC523C model-coeff block)
```
⇒ the last two are **float plant-model/observer consumers**, not diagnostics.
✅ **But every one was in force across V91/V111/V112/V122**, which flew α2 at **22/14/14/8** — a
**2.75× swing** — **fault-free, with monotone symptom improvement.** This rung is **2.50×**, no
larger, on a path already walked. The builder asserts that bound.

### ✅ TWO GATES THAT HAD TO BE CHECKED, AND BOTH PASS
**QUANTIZATION** — a truncating EMA has a deadband `|x−y| < 64/α2`, and a stair-stepping inertia
term is itself a plausible grind mechanism. **The state is 32-BIT and the output is `>>9`**, so at
α2=2 the deadband is **32 state units = 0.0625 OUTPUT LSB — SUB-LSB.** ⇒ **it cannot stair-step.**
That was the one way a low α2 could *cause* the symptom; it is closed.
**SELECTIVITY** — an EMA has **unity DC gain for any α**, so only fast transients are attenuated:
```
   pulse ms      a2=5     a2=2    detector loss        vs 18-22 Hz lane attenuation 2.22x
         10     0.366    0.174       2.10x   SEVERE
         30     0.686    0.409       1.68x   moderate
        100     0.935    0.759       1.23x   negligible
        400     0.995    0.971       1.03x   negligible
```
⇒ a **DRIVER** hard reversal is a 100–400 ms event (human bandwidth 2–5 Hz), where the detector
loses only **1.03–1.23×** while the grind band drops **2.22×**. ⭐ **α2 is SELECTIVE.**
⊕ The loss that *is* real sits in fast transients, and it is acceptable **only because V133 has
already de-fanged the branch that detector selects** — `0xC640A` −8192 → −1966 (4.17×).

### 🛑 THIS REVERSES V135's RATIONALE, WHICH IS NOW STALE IN ITS OWN DOCSTRING
V135 argues *"α2 is nearly INERT at 20 Hz ⇒ V122's improvement came from the KNEE/K1"*. That was
a delivered-component calculation whose **sign convention was never reconciled**; the
single-variable on-car comparison says the opposite. **V135's docstring is left as written** (a
record of what was believed when it was built) — **but its claim is superseded here.**

⭐ **FLIGHT ORDER UNCHANGED: V133 FIRST.** V134/V135/V136 are all V133-based follow-ups; flying
any of them first confounds the Lever A test that V133 exists to run.

## ✅✅ **THE CREEP ENDPOINT IS PRECISE — AND IT PUTS A CHECK ON V135 BEFORE IT FLIES**
Scored **every cached route** on the within-drive engaged/manual creep endpoint (NW = 128 to
recover routes the 256-window threshold had dropped), ordered by relay knee:
```
   knee   build  route   18-22 eng/man   30-40 control   guard
    600   V111   r21          4.40           0.54        PASS
    600   V91    r78         10.59           1.00        PASS
   1800   V112   r22          4.66           1.43        PASS
   1800   V112   r23          4.82           0.85        PASS
   3000   V122   r24          3.38           1.01        PASS
   (6 of 13 routes FAIL the control guard and are VOID: r77 3.23, r96 6.84, r97 0.50,
    r1e 8.06, ra6 7.06, ra4 8.32)
```

### ✅ 1. THE ENDPOINT IS FAR MORE PRECISE THAN ITS BOOTSTRAP CI SUGGESTS
**V112's two independent routes give 4.66 and 4.82 — agreeing to 3 %**, against bootstrap CIs of
[2.19, 11.08] and [1.99, 29.44]. ⇒ **the CIs are conservative; the real within-build repeatability
is ~3 %.** That makes **V133 vs V122's 3.38 genuinely discriminable**, and it is the first
same-build repeatability check this endpoint has had. ⚠ n = 2, so this is suggestive, not a
measured null — a third same-build route would settle it.

### 🛑 2. THE KNEE LADDER IS **NOT MONOTONE** ON THIS ENDPOINT — a check on V135
```
   knee  600 (V111)  ->  4.40
   knee 1800 (V112)  ->  4.74   (mean of 4.66, 4.82)   -- WORSE than 600
   knee 3000 (V122)  ->  3.38
```
⇒ **V111 → V112 raised the knee and the endpoint got slightly WORSE.** **V135's premise — that
more knee is better — is NOT supported here.** ⚠ V122 changed **three** cells (knee, K1, α2), so its
3.38 is not attributable to the knee alone, and V111/V112 differ in α2 as well (22 vs 14).
⇒ **V135 is DOWNGRADED from "well-founded" to "a measured-duty-ladder step whose SYMPTOM effect is
unconfirmed, and mildly contradicted, on the only symptom-adjacent endpoint that survives."**
It remains harmless and reduces friction 17 %, which the operator wants — but **it should not be
sold as a grind fix.**

### ✅ 3. THE CONTROL GUARD IS DOING REAL WORK
It **voids 6 of 13 routes**, including **every V104–V107 route** (controls 7.06–8.32), where engaged
driving was simply more active than manual. ⇒ without the guard those would have read as enormous
"engaged excess" results. **This is the same failure that killed the b26 relay hypothesis**, and
the guard now catches it automatically.

⭐ **Net**: the endpoint is **precise enough to score V133**, and it has already **demoted V135**
before a drive was spent on it — which is exactly what an endpoint is for.

## ✅✅✅ **AN ENDPOINT THAT SURVIVES THE NOISE FLOOR — V133 IS SCOREABLE AFTER ALL**
Every BETWEEN-ROUTE endpoint died on route variance (band amplitude 8×, f₀ 10 Hz). **But the
operator's symptom is ENGAGED-ONLY, so both arms can come from ONE drive.** An **ENGAGED-vs-MANUAL
contrast at matched speed inside a single route** cancels road, tyres, weather, alignment and the
speed profile — everything that makes routes incomparable.
```
   route  build   speed band      18-22 Hz eng/man        30-40 Hz CONTROL
   r22    V112    5-15 km/h    7.10 [ 2.52, 16.60]      1.12 [0.67, 2.32]   control FLAT
   r24    V122    6-17 km/h    3.88 [ 1.63, 10.47]      0.61 [0.33, 2.84]   control FLAT
   r1e    V107    7-19 km/h   57.93 [34.93,102.10]      7.87 [4.99,13.92]   control MOVES -> void
   ra6    V106    9-12 km/h   87.17 [36.26,346.2 ]     16.81 [7.43,27.03]   control MOVES -> void
```
✅ **BAND-SPECIFIC on r22 and r24** (signal moves, control flat) — and it **TRACKS THE OPERATOR**:
V112 → V122 nearly **halved** the engaged excess (7.10 → 3.88) exactly when he reported grinding
*"better, still ever so slight … in rare moments"*. **A statistic that moved with his verdict,
within-drive, is the best endpoint this kit has for the remaining low-speed symptom.**
⚠ **HONEST LIMIT: those CIs OVERLAP.** The halving is **suggestive, not significant** on its own —
it is the agreement with his verdict that gives it weight. The endpoint resolves a drop to
**≤ 1.6** (outside V122's lower bound of 1.63), which is exactly the "gone" band. **More creep
exposure tightens it.**

### 🛑 A DRIVE-DESIGN REQUIREMENT, NOT A WISH
Both arms must exist **at the same low speed**:
- **ENGAGED creep, 2–10 mph, hands off, with real steering activity**;
- **MANUAL creep over the SAME stretch at the SAME speed.**
⇒ **drive the same low-speed loop twice, once engaged and once manual.** Without both arms the
script has nothing to contrast and **says so rather than guessing**.

### ✅ PRE-REGISTERED, BEFORE ANY V133 FLIGHT
```
   ENGAGED/MANUAL 18-22 Hz at creep, speed-matched, vs V122's 3.88 [1.63, 10.08]
      <= 1.6      the engaged excess is GONE      => Lever A reproduced
      1.6 - 3.0   reduced but present             => partial
      > 3.0       unchanged vs V122               => Lever A did NOT reproduce
   MANDATORY GUARD: the 30-40 Hz control must stay in [0.5, 2.0].
```
🛑 **The guard is not decoration.** On **r1e and ra6 the control moves WITH the signal** (7.87,
16.81) ⇒ those contrasts are **global activity differences and carry nothing** — the identical
failure that killed the b26 relay hypothesis earlier this session. **The script refuses to
interpret them.**
✅ Shipped as `rlog-tools/score/score_v133_creep.py`, with **`--validate`** reproducing both
reference rows so a future edit to the script is caught immediately.

⭐ **Net: the session's measurement wall is breached for the one build that matters.** V133 was
"unscoreable" only under BETWEEN-route endpoints; **within-drive it is scoreable, band-specific,
and calibrated against two existing flights.**

## 🛑🛑 **BOTH `gp-0x6b26` ENDPOINTS ARE DEAD AT ROUTE-LEVEL POWER — THAT FAMILY IS UNFALSIFIABLE**
The retraction pointed at **f₀** as the right endpoint for an inertia term, noting the kit's
record *"f₀ = 21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6× … needs no symptomatic drive"*. **Tested it.**
```
   per-route f0 (median peak, 14-34 Hz, prominence >= 4, engaged)
     4x ->  21.88  20.31  20.31  21.48  24.22  15.23
     6x ->  16.02  25.78  25.78  21.48  19.92  19.92  19.92  21.29

   6x - 4x  f0 shift = -0.29 Hz  [-2.93, +4.69]      the record predicts +1.29 Hz
```
🛑 **Route-to-route f₀ varies by 10 Hz WITHIN one gain group.** The dose effect the record claims
is **1.29 Hz** — an order of magnitude smaller than the noise. ⊕ **And the memory says so itself**:
*"it may track COMMAND, not gain"* and ***"pooled, the gain term goes n.s."*** ⇒ **my null
independently reproduces the kit's own caveat**, and the 21.90/23.61/24.90 ladder is very likely
confounded.

### 🛑 SO BOTH ENDPOINTS FOR THIS FAMILY ARE GONE
```
   endpoint            status at route-level power
   band AMPLITUDE      DEAD -- same-firmware route variance is 8x (0.047-0.389 within one group)
   mode FREQUENCY f0   DEAD -- 10 Hz spread within one gain group vs a 1.29 Hz predicted effect
```
⇒ **Any `gp-0x6b26` build is effectively UNFALSIFIABLE with current instrumentation.** That covers
**V129/V130's `Y` changes and V132/V133's ceiling raise** — they are bounded, verified and
harmless, but **no drive this kit can currently run would score them.**
⊕ This is the same wall that produced the session's other nulls (the 8× gain-vs-grind test, the
openpilot-compensation test). **The binding constraint is not lever supply — it is measurement
power per route.**

### ✅ WHICH SHARPENS THE FLIGHT PLAN RATHER THAN BLOCKING IT
Two builds have endpoints that **do** survive this bound, because neither is scored on a
`gp-0x6b26` band statistic:
```
   V133  Lever A restored   -> scored by the OPERATOR's symptom + V62's measured 42x at 18-22 Hz
                               engaged creep, which had adequate power when it was taken
   V135  knee 3000 -> 3600  -> scored by the MEASURED saturation-duty ladder (3600 reads 0.0000),
                               a mechanism endpoint with real doses behind it
```
⇒ **Fly V133, then V135.** ⚠ **V134 (FactorC Y[0]) sits between**: its mechanism is well-founded
and its ceiling is checked, but its endpoint is a **band amplitude at creep** — the statistic this
section just showed is 8×-noisy. **It should be flown only on the operator's report**, not on an
instrumented endpoint, and that limitation should be stated when it is.

⭐ **THE REUSABLE POINT**: before designing a build, ask **"what endpoint would score it, and does
that endpoint have the power to see the predicted effect?"** Three build families in this session
(the `Y` fork, the ceiling raise, the f₀ ladder) fail that question **after** the fact. Asking it
first would have retired them in minutes.

## 🛑🛑🛑 **RETRACTION: I CITED V94's +137° AS "MEASURED" — THE KIT LABELS IT MIXED/UNRESOLVED**
Last section I wrote *"the sign, for once, is measured"* and concluded α2 = 5 helps the
oscillation. **That rested on a number the kit explicitly says cannot be used:**
> returned **MIXED/UNRESOLVED**: gain rise 2.29× (viscous 1.0, inertial 4.7), mean phase **+137°**
> (viscous 0°, inertial +90°), and the ±2-sample **skew sweep swings 5×** (6–9 Hz: 21 / 31 / 100 /
> 76 / 68). **`gp-0x6b26` is too small (p50 4.8 ct) and sign-flips too fast for a two-message
> reconstruction** … **Ghidra settled it; the telemetry could not.**
🛑 **A ±2-sample skew moves that phase from 21° to 100°.** It is not a usable measurement, and
**both** of my α2 conclusions rested on it:
✘ *"+137° is damping-ish ⇒ α2 = 5 helps the oscillation"* — **RETRACTED.**
✘ and the reversal I was about to write this section (*"+137° is past inertial ⇒ anti-damping ⇒
revert α2"*) — **also unfounded, and NOT acted on.**
⊕ Note the failure mode: I read a phase figure out of a memory **without reading the sentence
after it**, which said the measurement failed. The convention footnote (*viscous 0°, inertial +90°*)
was in the same line and I initially mis-mapped it too.

### ✅ WHAT GHIDRA *DID* SETTLE — and it changes the ENDPOINT, not the dose
[[accord-gp6b26-is-inertia-not-damping]], traced in `FUN_00041464` and **pinned in assembly**:
**`gp-0x6c2c` is a FIRST DIFFERENCE of the filtered motor rate = ACCELERATION**, so
**`gp-0x6b26` = −K × acceleration is an APPARENT-INERTIA term, NOT a damper.**
⇒ **an inertia term at a resonance SHIFTS f₀; to first order it adds no damping at all.**
⇒ **"more" and "less" do not map onto better or worse AMPLITUDE** — which is why four builds of
α2 dosing produced no clean amplitude result, and why my whole "delivered damping component"
table was answering the wrong question.

### ⭐ THE RIGHT ENDPOINT IS ALREADY IN THE KIT
[[accord-f0-crossover-is-the-endpoint]]: **f₀ = 21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×** — the mode
**frequency moves with dose**, exactly as an inertia term predicts, and that memory notes it
**needs no symptomatic drive**. ⇒ **any future `gp-0x6b26` edit should be scored on the MODE
FREQUENCY, not on band amplitude.** ⊕ This also explains the fixed **~19.9 Hz** peak measured
earlier this session: it is the *current* f₀ under the current dose, not an immovable object.

### ✅ WHAT SURVIVES THIS RETRACTION
- **α2's frequency-dependence is untouched** — inert at 20 Hz, 2.26× at 7.79 Hz. That is a
  **magnitude ratio** and needs no sign. What is retracted is the claim about *which way it helps*.
- **The knee (V135) and Lever A (V133) are unaffected** — neither rests on `gp-0x6b26`'s phase.
  V135 is a **measured duty ladder**; V133 is a **measured 42× symptom result**.
- ⇒ **the flight set does not change: V133 first, then V134 or V135.**
🛑 **STANDING RULE, recorded**: when quoting a number out of a memory, **read the sentence after
it.** This kit's memories carry their own retractions inline, and I have now been caught by that
twice in one session (V107's reconstructed 32.32 %, and V94's +137°).

## ✅✅ **α2 IS AN OSCILLATION LEVER, NOT A GRIND LEVER — AND α2 = 5 IS ALREADY RIGHT**
The α2 ladder's delivered effect is **strongly frequency-dependent**, which no session had checked:
```
   delivered component of the gp-0x6b26 lane, RATIO vs alpha2 = 22 (stock)
   alpha2     7.79 Hz    6 Hz     9 Hz    20 Hz    26 Hz
      14        1.31     1.32     1.30     1.16     1.08
       8        1.83     1.91     1.77     1.19     0.95
       5        2.26     2.52     2.08     0.98     0.70
       3        2.38     2.99     2.04     0.67     0.44
```
⇒ **INERT at the grind band (0.98× at 20 Hz) but MORE THAN DOUBLED across the entire 6–9 Hz
ratchet/oscillation band (2.26× at 7.79 Hz).** The ladder was driven 22→14→8→5 **for grinding**,
and its real effect landed in a band nobody examined. ⊕ Ratios between α2 settings are
**convention-independent** — this does not depend on my unresolved phase sign.

### ✅ THE SIGN, FOR ONCE, IS MEASURED — AND IT SAYS α2 = 5 IS ALREADY CORRECT
V94 measured `gp-0x6b26` at **+137/+139°**, between inertia (90°) and damping (180°) ⇒
**damping-ish at 6–9 Hz**. So **more** of the term there means **more damping**.
⇒ **α2 = 5 delivers 2.26× the damping at 7.79 Hz that stock did** ⇒ it is **helping the
peak-turn oscillation**, the operator's third complaint.
🛑 **I was one step from building an α2 revert** (5 → 22) on the reasoning that the ladder was
inert and therefore wasted. **V94's measured phase says that revert would HALVE the damping at
7.79 Hz and make the oscillation worse. NOT BUILT.**

### ⭐ THE REATTRIBUTION, WHICH IS THE POINT
```
   lever            grinding (20 Hz)      oscillation (7.79 Hz)
   alpha2 22 -> 5   INERT (0.98x)         2.26x MORE damping     <- an OSCILLATION lever
   knee 3000->3600  saturation -> 0.0000  --                     <- the GRIND lever (V135)
   Lever A (V62)    42x MEASURED at creep --                     <- the GRIND lever (V133)
```
⇒ **Each of the three complaints now has a distinct, non-overlapping lever**, and the kit had
been attributing α2 to the wrong one for four builds. ⊕ It also explains why V124's α2 = 5 *"bought
so little"* on grinding — **it was never a grind lever.**
⚠ [BELIEF] the sign rests on **V94's measurement**, not on my transfer function, whose reference
frame remains unreconciled (5–76° vs V94's +137/+139°). If V94's phase is ever overturned, this
conclusion inverts — and the α2 revert becomes the right build instead.

## ✅✅ **V135 BUILT — THE LAST *MEASURED* RUNG ON THE RELAY, AND I CLOSED IT TOO EARLY**
This session recorded *"the knee/K1 ladder is EXHAUSTED at V122/V124"*. **That closure was too
broad.** It is true only of **GAIN-HOLDING** steps, which need `K1 = 1122` at knee 3300 — above the
1023 ceiling. **Raising the knee with K1 HELD is a different move**, and the note did not cover it.

### ⭐ WHY THE KNEE AND NOT α2 — the reattribution that motivates it
GATE 2 at the creep band showed the **α2 ladder is nearly INERT at 20 Hz**: |H| falls 7.24→4.10
(1.77×) while the phase rotates 56.3°→16.0°, leaving the delivered component **flat**
(−4.01 → −3.94) — a **ratio**, so it survives any constant sign/phase offset.
⇒ **V122's *"better, rare moments"* came from the KNEE/K1, not α2** ⇒ **the Coulomb relay is the
live creep lever**, and this is its last measured rung.

### ✅ THE EDIT IS **ON** THE MEASURED LADDER, IN THE SYMPTOM'S OWN REGIME
```
   0xC40BC   3000 -> 3600      K1 (0xC40D2) HELD at 1020

   MEASURED saturation duty, engaged HANDS-OFF, 5-10 mph, cmd >= 2048:
     knee  600 -> 0.7439    1800 -> 0.2353    3600 -> 0.0000   <- THIS BUILD
     knee 1200 -> 0.4810    2400 -> 0.0484
```
🛑 **3600 is a MEASURED point reading 0.0000 — not an interpolation** — and the ladder was
measured in **ENGAGED HANDS-OFF CREEP**, precisely the regime of the remaining symptom.
✅ **And the cost goes the way he asked**: slope **0.003984 → 0.003320 = ×0.83, 17 % LESS
friction**, saturation **53.1 → 63.7 °/s**. His standing instruction was *"low apparent steering
mass and friction to LKAS **AND** no ratcheting"* ⇒ **this is the only lever in the kit's record
that moves BOTH the right way.**
✅ **K1 untouched at 1020** (ceiling 1023, above which friction exceeds `|model|` and the residual
inverts). The builder asserts K1 held, the ladder membership, and that friction decreases.

image `777dba0c87ada17b7d66995a9c7a98472bb358816020c8a55f65a91e2821aa89` ·
rwd `6516aa2a565433b8fbe7fbaeb31ff5cc7f1791ebf546799785e2f7e4f88bbd1e` · **80/80, CRC 50/50**,
twin verifier **PASS**. 2 payload bytes on a V133 base.

### 🛑 THE FLIGHT SET IS NOW THREE SINGLE-VARIABLE FOLLOW-UPS FROM ONE BASE
```
   V133  (FLY FIRST)  V62's Lever A restored     -- MEASURED 42x on this exact symptom
   V134               + FactorC Y[0] 0 -> 60     -- damping where there is currently NONE
   V135               + knee 3000 -> 3600        -- relay saturation to a MEASURED 0.0000
```
**All three are single-variable against V133**, so whichever is flown second is interpretable.
🛑 **Fly V133 first regardless** — it restores the one lever with a measured 42× on this symptom,
off the car since ~V80; flying V134 or V135 first would confound that test.
⚠ [BELIEF] for V135: the duty ladder is a **MECHANISM** measurement. The link from saturation duty
to what the operator *hears* rests on his own dose-response across V111/V112/V122, not on an
instrumented symptom endpoint.

## 🛑🛑 **THE α2 LADDER IS NEARLY INERT AT 20 Hz — MAGNITUDE FALLS, PHASE ROTATES, PRODUCT FLAT**
GATE 2 for `gp-0x6b26` **at the creep band**, which had never been asked. Lane phase vs motor rate:
```
   alpha2      18 Hz          20 Hz          22 Hz          26 Hz
     22    59.5 deg -0.51  56.3 deg -0.55  53.2 deg -0.60  47.3 deg -0.68
     14    50.0 deg -0.64  46.0 deg -0.69  42.3 deg -0.74  35.1 deg -0.82
      8    34.4 deg -0.83  29.8 deg -0.87  25.6 deg -0.90  18.0 deg -0.95
      5    20.4 deg -0.94  16.0 deg -0.96  12.1 deg -0.98   5.2 deg -1.00

   alpha2 22 at 20 Hz: |H| = 7.24, arg 56.3 deg, delivered component = -4.01
   alpha2  5 at 20 Hz: |H| = 4.10, arg 16.0 deg, delivered component = -3.94
```
✅ **[EVIDENCE, convention-independent] the MAGNITUDE falls 1.77× across the ladder while the PHASE
rotates by exactly enough to cancel it — the delivered component at 20 Hz is FLAT (−4.01 → −3.94).**
⇒ **the α2 ladder 22→14→8→5 has been very nearly INERT at 20 Hz in delivered terms.**

### ⭐ WHICH REATTRIBUTES THE ONE IMPROVEMENT THE OPERATOR REPORTED
V122 changed **three** things vs V112: knee 1800→3000, K1 612→1020, **and α2 14→8**. The operator
reported grinding *"better, rare moments"*. **If α2 is inert at 20 Hz, that improvement came from
the KNEE/K1 (the Coulomb relay), not from α2.**
⇒ **testable reattribution**, and it matters: the α2 ladder is treated across this kit as *the*
selective grind lever. ⊕ It also explains why pushing α2 further (V124's 5) bought so little.
⚠ The earlier "α2 selectivity 5.07× toward grind #1" figure was a **|H| magnitude** ratio — it did
**not** account for the phase rotation, which cancels it at 20 Hz.

### ⚠ WHAT I WILL **NOT** CLAIM — the SIGN
My phase reference gives **5–76°** across the band, but the kit **measured** `gp-0x6b26` at
**+137/+139°** (V94) and calls it a real damper. That is a **60–130° disagreement**, so my reference
frame is **unverified** — I did not track the signs of `Y` (negative), `polarity(gp-0x6752)` (−1)
or the aggregator's summation convention. ⇒ **I do NOT conclude "anti-damping"**, which is what the
raw numbers would suggest; that would be the exact overreach this session keeps catching.
🛑 **What would settle it**: reconcile this transfer function against V94's measured +137/+139°
on the SAME signal, then re-read the sign. Until then only the **flatness across α2** stands — and
that result is a RATIO between α2 settings, so it survives any constant sign/phase offset.

## ✅✅✅ **THE CREEP MECHANISM IS CLOSED — AND V134 IS BUILT AS THE FOLLOW-UP**
Screening predictors of **18–22 Hz AT CREEP** (the actual remaining symptom) first showed every
channel moving **both** bands 3–9× — a pure **activity** confound. Dividing activity out by taking
the **within-window ratio (18–22)/(30–40)**, with the adjacent 13–18 band as a second control:
```
   predictor        (18-22)/(30-40) hi/lo   (13-18)/(30-40) ADJ CTRL   verdict
   driver torque    0.611 [0.461,0.879]     1.011 [0.786,1.295]        SHAPE CHANGE
   |steer angle|    0.813 [0.574,1.046]     0.984 [0.768,1.256]        null
   LKAS cmd         1.252 [0.949,1.760]     0.974 [0.709,1.269]        null
   |steer rate|     1.084 [0.789,1.413]     1.324 [1.021,1.600]        null
```
983 engaged creep windows, 9 routes. ✅ **DRIVER TORQUE DAMPS 18–22 Hz band-specifically (0.611×)**
while the adjacent band does not move. ✅ **The LKAS command is NULL at creep** — the opposite of
mid-speed ⇒ **the creep mode is DAMPING-limited, not excitation-driven.**

### ⭐ THE CHAIN, END TO END
1. At creep the dominant band is **18–22 Hz** (absolute 3.849, largest of any band at any speed),
   and its peak is a **FIXED ~19.9 Hz resonance** (`corr(speed,peak) = -0.028`, slope **-0.006** vs
   **0.13–0.53** for any wheel order) ⇒ **not a road/tyre line.**
2. **Driver torque damps it** — measured, band-specific, activity-controlled.
3. **Hands-off, that damping is absent.**
4. The firmware's own base-assist damper is **structurally ZERO below 35 km/h**
   (modes 26/27 `FactorC X=[35,60,80,140] km/h, Y=[0,234,429,908]`).
⇒ **HANDS-OFF AT CREEP THE MODE HAS NO DAMPING FROM EITHER SOURCE** — exactly the condition under
which the operator reports it.

### ✅ V134 BUILT — 2 payload bytes, and it is NOT V80
```
   0xD77DA  FactorC Y[0] mode 26  0 -> 60    Y becomes [60, 234, 429, 908]
   0xD77EE  FactorC Y[0] mode 27  0 -> 60    Y becomes [60, 233, 426, 875]
```
image `5451646d0d4c81b68c934ff522d9cc4a3f953fc36369c5c7e8848e8bcb815ac1` ·
rwd `5eafbdf54d989391d2a4075d24650d53b0a76612d5f9f72beafdb11c63730bee` · **91/91, CRC 50/50**,
twin verifier **PASS**. **ENGAGED modes only** — manual 24/25 byte-untouched.
🛑 **V80 set FactorC to a FLAT 566 and produced the worst grinding on record** — a **plateau**
that pushed the product past the ceiling into a **relay**. V134 differs on both counts, and the
builder **asserts** both:
- **MONOTONE GATE** — `Y` is strictly increasing (a **ramp**, not a plateau); **`X` untouched**;
- **CEILING GATE** — creep product **≤ 60** (≤ 180 with FactorE headroom) vs the **512** ceiling
  ⇒ **no saturation**; and 60 is **9.4× smaller** than V80's 566.
✅ The rate objection is dead: task 5 is bounded **≥ 250 Hz** ⇒ this lane **can** act at 18–22 Hz.

### 🛑 FLIGHT ORDER — V133 FIRST
**V133 restores V62's Lever A, which MEASURED 42× on this exact symptom** and has been off the car
since ~V80. **Flying V134 first would confound that test.** ⇒ **V133, then V134 only if the rare
creep grind survives it.**
⚠ [BELIEF] the dose. **60** is chosen to sit ~9× under V80's and far under the ceiling; it is
**not** derived from a measured creep FactorE, which the cache does not contain. If it is too
weak the ramp has room; if too strong, the failure mode is V80's and shows as saturation on the
first drive.

## ⭐ **NEXT CANDIDATE, SIZED BUT NOT BUILT: `FactorC Y[0]` — the damper is DEAD at creep**
With the target corrected to **rare LOW-SPEED grind #1**, one structural fact stands out: the
base-assist damper is **structurally zero** exactly where the symptom is.
```
   mode 26/27 FactorC   X = [2240, 3840, 5120, 8960] = [35.0, 60.0, 80.0, 140.0] km/h
                        Y = [   0,  234,   429,  908]        (mode 27: [0, 233, 426, 875])
   below X[0] the LERP returns Y[0] = 0  =>  NO base-assist damping below 35 km/h, at all.
```
✅ **The ceiling check PASSES** — the failure mode that destroyed V80. Ceiling LERP is
**Y = [512, 1024]**; an earlier/raised ramp keeps the product at **≤ 70** through creep
(**≤ ~168** even allowing FactorE's 2.4×) ⇒ **far under 512, no saturation, no relay.**
🛑 **But the obvious version is mis-targeted**: moving `X[0]` 2240→640 gives **ZERO below
10 km/h**, and the operator's remaining grinding is at **2–5 mph (3–8 km/h)**. The edit that
actually reaches it is **`Y[0]` 0 → ~60**, which:
- puts a small damping term at **every** speed below 35 km/h, including 3–8 km/h;
- is **9.4× smaller than V80's 566**, and V80's failure was a **flat 566 everywhere** that pushed
  the product past the ceiling into a relay — not the non-zero `Y[0]` as such;
- keeps `Y` **strictly monotone** (60, 234, 429, 908) ⇒ no plateau in the ramp;
- touches **ENGAGED modes 26/27 only** ⇒ manual feel byte-untouched;
- acts in a lane whose task rate is now bounded **≥ 250 Hz** ⇒ it **can** damp 18–22 Hz.

### 🛑 WHY IT IS **NOT** BUILT — it would confound the one clean test available
**V133 already restores the lever that specifically and measurably fixed this exact symptom**:
V62's Lever A, **18–22 Hz at ENGAGED CREEP, ×0.124 [0.036, 0.387], 42× at |rate| 16–32 °/s,
30–40 Hz control ~1.0**, operator: *"Original grinding at 2–5 mph is GONE!"* — **off the car since
~V80.** Adding an untested damper edit on top would make the drive uninterpretable and violates the
standing law that **every build be interpretable from ONE short symptomatic drive.**
⇒ **Fly V133 first.** If the rare low-speed grind survives it, `FactorC Y[0]` → 60 on modes 26/27
is the next build, **already sized and ceiling-checked**, 4 payload bytes.
⚠ [BELIEF] the dose. `Y[0]` = 60 is chosen to sit ~9× under V80's and far under the ceiling; it is
**not** derived from a measured creep FactorE, which the cache does not contain.

## 🛑🛑🛑 **OPERATOR CORRECTION 2026-08-28: MID-SPEED GRINDING IS FIXED — ONLY RARE LOW-SPEED REMAINS**
Verbatim: *"Why are we talking about mid speed grinding in V133? This has been fixed, its just a
rare low speed grinding #1 since my last drive."*
🛑 **Two sections of band-hunting (21–26 Hz, then 26–31 Hz) were aimed at 15–40 mph — a symptom
he no longer has.** Both are superseded as a TARGET; their METHOD findings stand (share is
confounded; the ~19.9 Hz peak is speed-invariant, not a wheel order).

### ✅ THE CREEP REGIME — where the remaining symptom actually is
```
   10-24 km/h, ABSOLUTE band power     6-9    13-18   18-22   21-26   26-31   30-40 CTRL
   r22 (V112)  grinding present      1.817   1.448   3.226   2.900   0.655   0.315
   r24 (V122)  better, rare          1.227   1.080   1.913   2.194   0.469   0.308
   V122/V112                         0.675   0.746   0.593   0.757   0.715   0.977
```
✅ **18–22 Hz is the DOMINANT band at low speed (3.226, the largest of any)** and **improved the
most** V112→V122 (**0.593**) while the **30–40 Hz control stayed FLAT at 0.977** ⇒ a **band-specific**
improvement that tracks his own *"better"* verdict.
⚠ **Low n** — creep windows are scarce (26–31 per route). The direction is consistent across all
bands; only 18–22's margin over the control is clear.

### ⭐ THIS PUTS V133's LEVER A EXACTLY ON TARGET
**V62 was measured at 18–22 Hz, ENGAGED CREEP**: ×0.124 [0.036, 0.387], **42×** at |rate|
16–32 °/s, **30–40 Hz control ~1.0**, operator: *"Original grinding at 2–5 mph is GONE!"*
🛑 **`0x3AB76` / `0x3AC20` have been byte-STOCK since ~V80**, behind a `FROZEN` entry that
asserted their own absence ⇒ **that is very likely why the rare low-speed grinding returned**, and
**V133 restores them.**
⇒ **RETRACTS this session's earlier caveat** *"V62 fixed the creep symptom, not the current one"*
— **the current one IS the creep symptom.** V133's Lever A restore is the **direct** fix for the
symptom that actually remains, not an incidental inclusion.

### ✅ WHAT THE DRIVE MUST NOW CONTAIN — priority inverted
`SCORING-V131-preregistered.md` listed **engaged creep 2–10 mph with real steering** as item (1) of
four. **It is now the PRIMARY content of the drive**, because that is where both the remaining
symptom and V62's 42× live. Mid-speed and highway drop to context. ⊕ `score_v131_grind.py` should
be run on the **creep** stratum, and its 18–22 Hz row is the endpoint — **not** 21–26 Hz.

## 🛑🛑 **CORRECTION: BAND *SHARE* WAS CONFOUNDED — IN ABSOLUTE POWER ONLY 26–31 Hz MATCHES**
Last section I selected 21–26 Hz using band **SHARE**. **Share is normalised**, so it moves when
*either* end moves — the exact trap already recorded in this session (*"a ratio moves when either
end moves; always report numerator and denominator"*). Redone in **ABSOLUTE** power:
```
   band          creep<10   10-24    24-64    >=64     24-64/creep   falls>64?
    6-9  Hz       2.767     2.729    0.549    0.190       0.20x        yes
   13-18 Hz       1.569     1.814    0.804    0.503       0.51x        yes
   18-22 Hz       3.849     4.054    0.920    0.303       0.24x        yes
   21-26 Hz       2.490     4.657    1.260    0.433       0.51x        yes
   26-31 Hz       0.433     1.003    0.547    0.310       1.26x        yes   <- ONLY band > 1
   30-40 Hz       0.392     0.597    0.248    0.177       0.63x        yes
```
🛑 **Every band falls with speed in absolute terms except 26–31 Hz.** 21–26 Hz's absolute power at
24–64 km/h is **half** its creep value ⇒ **it does NOT match the operator's profile**; its rising
*share* was an artefact of the 1–4 Hz denominator collapsing with speed.
⇒ **[EVIDENCE] 26–31 Hz is the only band genuinely higher at road speed than at creep, and lower
again at highway** — the operator's stated shape.
⚠ **Imperfect**: 26–31 Hz peaks at **10–24 km/h (1.003)**, not 24–64 (0.547) ⇒ *"low at creep, high
at low-mid speed, low at highway"*, a good but **not exact** match to *"15–40 mph"*.

### ✅ AND THE MODE ITSELF IS A FIXED RESONANCE, NOT A ROAD EFFECT
Peak of the 12–34 Hz region, 1,443 steady-speed engaged windows with prominence ≥ 3:
```
   corr(speed, peak Hz) = -0.028      fit  f = -0.0058*v + 19.85
   median peak 19.5-20.7 Hz from 10 to 100 km/h   (IQR widens 16.4-21.1 -> 12.9-26.2)
   a wheel order needs slope 0.13-0.53;  measured slope is -0.006, ~50x too small
```
⇒ **a FIXED ~19.9 Hz resonance, speed-invariant, broadening with speed — NOT a wheel order**, so
it is a firmware/mechanical object and **potentially addressable**. ⊕ Consistent with
[[accord-ratchet-is-a-lightly-damped-resonance]] (Q 14–29), located here at ~20 Hz.

### ⭐ THE KIT ALREADY HAS A MEASURED LEVER ON 26–31 Hz — AND V133 CARRIES IT
**V84 drove 26–31 Hz burst duty 96.6 % → 25.1 % → 2.54 %** (V80→V81→V84), longest ring
**18.29 → 11.25 → 1.34 s**, on 3.4–4.9× the exposure, with negative control and IMU falsifier both
passing. V84 = **Lever B** (`0x3AA96` C5→FB, `0xC6446` 512→5244) **+ the damper returned to Honda's
values in BOTH engaged columns.**
✅ **V133 carries all of it**: `0xC6446` = 5244, `0x3AA96` = fb, FactorC/FactorE at Honda's stock.
⇒ **the best measured lever on the band that matches his profile is ALREADY on the flight build.**

🛑 **Net effect of this section:** it **retracts** last section's *"21–26 Hz is the validated
band"*, replaces it with **26–31 Hz on absolute power**, and shows the corresponding lever is
already carried — which is a better-founded reason to fly V133 than the one I gave last time.

## 🛑🛑🛑 **V62 FIXED THE *CREEP* SYMPTOM — THE CURRENT ONE IS A DIFFERENT BAND AT A DIFFERENT SPEED**
The operator gave a constraint I had never tested: **grinding at 15–40 mph (24–64 km/h), NONE below
5–6 mph.** That is a **within-drive** speed profile — immune to the route-variance floor that has
blocked every between-build comparison this session. Pooled over **8 routes / 4,750 engaged
windows**, which band reproduces it?
```
   band          creep<10    24-64     >=64    24-64 / creep
    1-4  Hz       0.51515   0.17776  0.09867      0.35x
    6-9  Hz       0.03547   0.07985  0.04803      2.25x   <- matches shape (the RATCHET band)
   13-18 Hz       0.03130   0.11571  0.11147      3.70x   (flat above 64)
   18-22 Hz       0.10338   0.10237  0.07187      0.99x   <- FLAT: does NOT match
   21-26 Hz       0.05963   0.13557  0.11837      2.27x   <- MATCHES: up from creep, down at highway
   26-31 Hz       0.00622   0.05167  0.09114      8.31x   (keeps RISING above 64)
   30-40 Hz       0.00585   0.03185  0.04424      5.44x   (keeps RISING)
```
✅ **At creep, 18–22 Hz DOMINATES (0.103 vs 21–26's 0.060). At 24–64 km/h, 21–26 Hz DOMINATES
(0.136 vs 18–22's 0.102).** Only **21–26 Hz** and the **6–9 Hz ratchet** reproduce his full shape —
up from creep **and down again at highway**. The bigger risers (26–31, 9–13, 30–40, 40–49) all keep
climbing above 64 km/h, contradicting *"15–40 mph"*.
⇒ **[EVIDENCE] 21–26 Hz is the right band for the CURRENT complaint**, validated against the
operator's own speed report rather than assumed.

### 🛑 AND THAT UNDERCUTS WHAT I CALLED V133's "MOST DEFENSIBLE CONTENT"
**V62's 8–42× result was measured at 18–22 Hz** — the band that is **FLAT with speed (0.99×)** and
**dominant AT CREEP**. And V62's operator report was *"Original grinding at **2–5 mph** is gone!"*
⇒ **V62 fixed the CREEP symptom, in the CREEP band.** The current complaint is **15–40 mph in
21–26 Hz** — a **different symptom, at a different speed, in a different band.**
⇒ **Restoring Lever A (V133) should NOT be expected to fix the current grinding.** It restores a
real, measured, control-passing fix — **for the symptom the operator already reported as fixed.**
⊕ This is precisely what his correction *"grind #1 has moved to a new, higher frequency"* means,
and it is now **quantified** rather than taken on report.

### ⭐ WHAT THIS CHANGES — the target was mis-specified, not the levers
Every grind lever this kit has evidence for was scored at **18–22 Hz** (V62) or at **<16 km/h**
(V106's extinction, measured *"engaged, <16 km/h"*). **Both are the CREEP regime.**
🛑 **NO lever in this kit's record has ever been scored against 21–26 Hz at 24–64 km/h — the
operator's actual current symptom.** That is why twelve builds have not closed it: **they were
optimised against the wrong endpoint.**
⇒ **The next build should be chosen by, and scored against, 21–26 Hz at 24–64 km/h** — and
`SCORING-V131-preregistered.md` already requires a drive containing that band. ✅ `score_v131_grind.py`
already reports 21–26 Hz with a 30–40 Hz control and a validated null; **it is pointed at the right
band, which is now confirmed rather than assumed.**

---

🛑 **Older sections split to `docs/archive/STATE-ARCHIVE-2026-08-29.md` on 2026-08-29** when this file reached 229 KB against the 256 KB cap.
