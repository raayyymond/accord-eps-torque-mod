# STATE — living current state of the kit

## ⭐⭐ **THE ASSIST CURVE IS IN THE IMAGE, THE 2.000 SLOPE CAP **BINDS**, AND GATE 2 PASSES**
The curve was never unreachable — it is **initialised-data copied ROM→RAM at boot**, which is why
only 3 `st.h` target the 20-knot block and 2 of those are clears. Found by searching the whole image
for the shape the decompile requires (10 ascending X bounded by the input clamp 8192, 10 ascending Y
bounded by the output clamp 12288):
```
   0xCE47A  X  0   25   60  100  150  250  450  900 1800 4150
            Y  0  154  338  460  549  635  702  766  824  857
            slope 6.16 5.26 3.05 1.78 0.86 0.34 0.14 0.06 0.01
            max 6.16  vs cap 2.000  =>  BINDS on 3 of 9, over X 0-100

   0xCF372  max slope 16.37  binds 4/9 over X 0-450
   0xCF3CA  max slope 11.97  binds 3/9 over X 0-150
   (+ 0xCE4A6 / 0xCF39E / 0xCF3F6 duplicates — the mode-selected pointer-table family)
```
✅ **[EVIDENCE] the cap is NOT inert — it clamps the steep low-torque segments on every record**,
pinning the map's **small-signal gain at exactly 2.000**, which is the **CEILING** value of `s` in the
loop census. The loop's largest single term therefore sits at its maximum, permanently.
✅ **[EVIDENCE] all six curve records are byte-identical across the 161 images**, and `0xC6384` reads
**2048 on all 161** (exact u16 read; an earlier 40-byte window check of mine spanned `0xC63A0`/
`0xC63AC`, which DID change, and wrongly suggested 5 variants — **that was my error, the cap is
untouched**).

### ✅ GATE 2 — ANCHORED ON THE MEASURED Q RATIO, NOT A CENSUS PHASE
⚠ My first pass used the census's `L` phase (−148°) with `P` real-positive. That puts `P·L` in the
third quadrant and gives `|1−P·L| = 1.92 > 1` — a loop that **ADDS** damping, contradicting the
measured 93 % cancellation. The phase cannot be pinned (the census says `P`'s phase *“is not in the
image”*) **and the sign of the whole result depends on it**, so anchor on the measurement instead.
```
   MEASURED Q_eff/Q_passive = 40/2.8 = 14.3  =>  |1-P.L| = 0.0700  =>  P.L = 0.9300 at stock
   [ASSUMPTION, stated] P.L real-positive at the peak -- what the measured ratio REQUIRES,
   and the standard form for a damping-cancelling loop.

   cap    s       |L|     |1-P.L|   Q ratio    vs stock
   2048   2.000   2.825   0.0700    14.29      stock
   1792   1.750   2.575   0.1523     6.57      2.2x MORE damped
   1536   1.500   2.325   0.2346     4.26      3.4x MORE damped
   1024   1.000   1.825   0.3992     2.50      5.7x MORE damped
```
✅ **MAGNITUDE: PASSES**, and the effect is large. ✅ **PHASE: PASSES** — the map term is a **real
gain**, so lowering the cap **scales `|L|` without rotating it**; under the real-positive `P·L` the
measurement requires, `|1−P·L|` can only move away from zero ⇒ **monotonically more damped at every
cap value, with no value at which it reverses.**
⚠ **What would falsify the assumption**: if `P·L` were not near the positive real axis, the measured
14.3x cancellation could not come from this loop at all. **The on-car test is the same either way** —
lower the cap and see whether the 8.64 Hz torque peak drops below its slope-matched null.

### 🛑 THE FEEL TRADE — AND WHY IT IS NARROWER THAN IT LOOKS
The cap binds over the **LOW-torque** segments (X 0–100 to 0–450 of a ±8192 range), so lowering it
means **less assist per unit driver torque near centre ⇒ heavier steering there** — the regime the
operator asked to keep light. **Stated plainly because it cuts against a standing constraint.**
⊕ But it is narrower than the constraint's wording suggests: the constraint is about *“max steering
angular velocity and acceleration”* and *“low apparent mass and friction **to LKAS**”*, and
- the curve is **UNCAPPED and unchanged above X≈450** ⇒ **peak authority and max rates are untouched**;
- the map is fed by `clamp(gp-0x4f60) + gp-0x6b4a`, i.e. the **driver torque sensor**, not the LKAS
  command lane (`gp-0x6b4c`) ⇒ **[BELIEF — `gp-0x6b4a`'s provenance is NOT yet established; if it
  carries an LKAS-derived offset this claim weakens.]**
⊕ **Recommended first dose 1536 (1.5x)** — predicted **3.4x** more damping, which clears the
one-episode detection margin comfortably, and is the smallest step that does. **Not the largest dose:
the feel cost is real and the operator should meet it in the smallest useful increment.**

## ⚠ **THE ASSIST-CURVE INITIALISER IS STILL UNLOCATED — TWO CANDIDATE PATHS RULED OUT**
Hunting the RAM-resident 10-knot curve (needed to finish GATE 2 on the slope cap `0xC6384`).
Both leads the byte scan produced are **not** the initialiser:
```
   0x38FD0 / 0x38FEE / 0x39522   st.h r0, -0x6430/-0x6444/-0x641c, gp
       -> STORE-ZERO with a lockstep shadow (shadow = knot - 0x184C; mismatch calls
          FUN_0006b9fa, the lockstep-fault handler).  A CLEAR path, carries no values.
          Exactly the documented store-zero trap.

   0x39A0C..                     blend each knot toward ep = tp+0x7564 = 0xC6564, in float
       ANCHOR CHECK: 0xC6384 reads 2048 (the slope cap) => tp = 0xBF000 CONFIRMED, so the
       0x1000 trap is not in play here.
       -> but 0xC6564 is ZERO, and zero on ALL 161 IMAGES  =>  this blends the curve toward
          zero: a FADE-OUT / degradation ramp, not an initialiser.
```
✅ **[EVIDENCE] `0xC6564` = 0 on all 161 images**, so nothing the kit has ever built changed it.
⊕ Region context: `0xC6520-0xC6560` is a **float32 array stored as (lo16,hi16) halfword pairs**
(`0 16840` = 25.0, `0 16968` = 50.0, `0 16256` = 1.0), which is why a naive u16 read of that
neighbourhood looks like noise. Recorded so the next pass does not mis-read it as integers.
❌ **No monotone 10-knot table bounded by the input clamp (8192) exists in `0xC6400-0xC6700`.**

### ⭐ A CHEAPER ROUTE TO THE SAME ANSWER — THE FIRMWARE ALREADY COMPUTES IT
The question GATE 2 needs is only *does the 2.000 cap BIND at the creep operating point?*, and
`FUN_000352b4` **already tracks that**: the map-build loop keeps a running maximum of the capped
per-segment slope in **`gp-0x69a6`** (`uVar40` in the decompile, written `*(short*)(gp-0x69a6)`).
⇒ **`gp-0x69a6` == 2048 means the cap is binding.** That is a **one-cell telemetry read**, not a
firmware-reconstruction problem, and it answers the gate directly on-car in a single episode.
⚠ **[BELIEF]** the cap does bind in the mid-torque range: the domain-average slope is
`12288/8192 = 1.5` against a cap of **2.000**, so the cap can only bite on segments steeper than 1.33x
the average — which is the normal shape of a power-assist curve, and is the loaded-wheel creep
regime. **Unverified until `gp-0x69a6` is read.**

### ✅ THE RECOMMENDATION IS UNCHANGED
**V158 still flies first.** It targets the GRIND, which is firmware-reachable and demonstrably
moving (post-V102 ρ = −0.94, p = 0.005, in three channels). The ratchet needs a different lever, and
that lever's gate is one telemetry cell away — **not** a reason to delay a build that addresses the
other symptom.

## ⭐ **THE RATCHET'S PRIME SUSPECT IS THE BASE-ASSIST MAP — AND ITS LANE IS NOT MEMORYLESS**
Two independent routes now point at the same lane. **From the DATA** (this session): the ratchet is
firmware-created, engaged-only, in **torque not angle**, and untouched by all 278 bytes the kit has
changed. **From the CODE** (a prior tracer's loop-topology census, re-read and confirmed):
```
   Z = (Z0 + P.F) / (1 - P.L)      every torque-fed lane is a DENOMINATOR term
   Q_eff / Q_passive = 40 / 2.8 = 14.3   =>  the loop cancels ~93 % of the mode's damping
   gp-0x6b86 (base assist map, FUN_000352b4) is the LARGEST torque-fed term: window
   +/-0x3000, the widest of all 11, and 5.8-7.8x the ENTIRE PID at 7.79 Hz
```
✅ **[EVIDENCE] its slope cap `0xC6384` = 2048 (2.000x) is byte-identical on ALL 161 IMAGES**, as
are `0xC6382` = 41 and the input clamp `0xC6200` = 8192. Independently confirmed by my own
untouched-cell scan, which found `0xC6384` absent from the 28 changed bytes in `0xC6000`.
⇒ **the largest available `L` lever has never been moved, which is exactly the profile of a cause
the kit's 30+ builds could not have touched.**

### 🛑 A CORRECTION TO THE CENSUS — THE LANE HAS STATE
The census priced this lane as **MEMORYLESS** (*“transfer at 7.79 Hz is real, 0°, magnitude = the
local slope”*). **The decompile shows otherwise.** `FUN_000352b4` ends with a **parallel lagged
branch** added to the direct path:
```
   iVar33 = clamp(gp-0x6b7a - sVar15, +/-0x3000) * (uVar25 < uVar18)     # a DIFFERENCE, comparator-gated
   iVar24 += (iVar33*0x80 - iVar24) * k >> 11                            # gp-0x381c, 32-bit state, 1 kHz
   gp-0x6b86 = clamp(iVar34 + (iVar24 -/+ 0x80) >> 7, +/-0x3000)         # direct + LAGGED, in PARALLEL
```
⊕ A difference passed through a lag and added back is a **lead-lag / dynamic-assist compensator**,
not a static curve ⇒ **the lane's transfer is NOT the memoryless slope the census assumed**, and any
`|L|` computed from the slope alone is incomplete.

### ⭐ AND ITS POLE IS SELECTED BY ENGAGEMENT — BUT THE EFFECT IS TOO SMALL
```
   k = cal(0xC6382) = 41        if (iVar14 != 0 && return-centre != 0)     <- MANUAL
     = LERP(0xC6906..) = 20     otherwise                                  <- ENGAGED
   (return-centre is DEAD ENGAGED, 0.0000 duty / 75,227 frames, so the arms genuinely differ)

   at 8.64 Hz, closed form AND the real integer recursion agreeing to 4 dp:
     ENGAGED k=20  corner 1.56 Hz   |H| 0.1779  arg -78.20 deg
     MANUAL  k=41  corner 3.22 Hz   |H| 0.3491  arg -68.02 deg
   => engaged lags 10.18 deg MORE, which moves 1-P.L the RIGHT way (1.798 -> 1.713)
```
🛑 **[EVIDENCE] but that is only a ~5 % change in the denominator, against an observed ~20x
presence-vs-absence contrast. The pole difference is REAL, points the right way, and is FAR TOO
SMALL to be the mechanism.** Recorded as a negative so it is not re-derived.

### ❌ AND THE FLOAT SECOND-ORDER BLOCK IS NOT IT EITHER
`FUN_000352b4` carries a genuine 2nd-order float section (states `gp-0x3814`/`gp-0x3818`, coeffs
`0xC60A8..0xC60B4`), gated on `0xC649B==1 && 0xC64FA <= gp-0x671a`.
✅ **[EVIDENCE] it is HONDA'S and ships DISABLED** — `0xC649B` stock = **0**, and the kit enabled it
on 58 of 161 images (V104 on; the V105/V106 notch work).
❌ **Enabling it did nothing to the ratchet**: `0xC649B` vs ratchet **ρ +0.26, p 0.500**; its
coefficients moved at V106/V107 with **ρ −0.31 to −0.45, all p ≥ 0.226.**

### 🛑 THE BLOCKER, STATED PRECISELY
The 10-knot curve itself is **RAM-resident** (`gp-0x641e..gp-0x6430` X, `gp-0x6444..` Y), so the
**local slope at the creep operating point — which is what sets `|L|` — is not readable from the
image**, and GATE 2 on `0xC6384` cannot be completed without it.
⊕ **`search_instructions` returned ZERO for stores to that block; a raw LE byte scan across BOTH gp
encodings found 27 accesses** (`0x38FD0`/`0x38FEE`/`0x39522` store-shaped; `0x43CBC-0x43CF6` touches
all ten X knots, but decompiles as a READER into stack locals). **Another instance of the documented
undercount — the null was false.** The initialiser is still unlocated.

## ✅✅ **THE RATCHET SCORES FROM ONE 15-SECOND EPISODE — THE 8-PASS SPEC WAS THE WRONG ENDPOINT**
Last tick's drive spec asked for **8 passes of 15 s** to resolve a 1.68–2.74x *ratio*. That is
**unbuildable** under the standing design law — *a spec needing matched episodes or minutes of
exposure is unbuildable, and the operator stops the drive the moment the symptom persists.*
✅ **And it was the wrong endpoint.** The engaged-vs-manual result is **PRESENCE/ABSENCE** (peak
clears its null on **7/7** engaged arms, **0/7** manual), so killing the ratchet is an **~8x** move
from excess ≈33 to below null ≈4 — not a 1.7x one.
```
   single continuous engaged-creep episodes from the existing corpus
     15 s ->  5 windows   11 episodes   RATCHET DETECTED 11/11 = 100 %
     20 s ->  6 windows    5 episodes                     5/5  = 100 %
     30 s -> 10 windows    4 episodes                     4/4  = 100 %
   excess 25.5-155.7  vs slope-matched null 1.9-4.9   =>  5-65x MARGIN
```
✅ **[EVIDENCE] ONE 15 s continuous engaged creep pass answers the primary question.** More passes
only sharpen the *graded* question (how much smaller), which is secondary to *is it fixed*.
⚠ The **grind's** margin on the flying build is smaller (V122 excess 14.0 vs null ≈4, i.e. 3.5x), so
a marginal grind read from one episode is **inconclusive, not negative**. The ratchet's is not.

## ⚠ **DRIVEN vs SELF-EXCITED: INCONCLUSIVE, LEANING DRIVEN — AND UNDERPOWERED FOR THE SAME REASON AS EVERYTHING ELSE**
The ratchet is engaged-only but absent from every command channel. Two mechanisms fit that:
**DRIVEN** (the command carries no 8.6 Hz line but the firmware's RESPONSE to it creates one
⇒ a forward-path nonlinearity, and the lever is in the forward path) or **SELF-EXCITED** (a
closed-loop instability running at its own frequency ⇒ the lever is in the feedback path).
That distinction decides which half of the chain to search, so it was worth a test.
```
   band-SPECIFIC coupling = coherence(7-10.5 Hz) - coherence(30-40 Hz control band),
   `co_tqcan` -> `cs_tq`, vs phase-shuffled surrogates (spectrum preserved, timing destroyed)

     r78  V91    -0.021 (shuf +0.091)  not specific     r1e  V107  +0.522 (+0.097)  SPECIFIC
     r7e  V96    +0.133 (+0.039)  SPECIFIC             r22  V112  +0.087 (+0.060)  SPECIFIC
     r7f  V96    +0.176 (+0.042)  SPECIFIC             r24  V122  +0.068 (+0.062)  SPECIFIC
     r96  V102   +0.019 (+0.047)  not specific         ra4  V104  +0.148 (+0.105)  SPECIFIC
     ra6  V106   -0.060 (+0.116)  not specific

   across routes: median +0.087   95 % CI [-0.021, +0.176]   <- CROSSES ZERO
```
⚠ **[INCONCLUSIVE]** 6/9 routes are individually specific and the pooled median is positive,
but **the CI includes zero**, so *driven* is not established. ⊕ **RAW coherence was worse than
useless**: the 30–40 Hz control band scored as high as the ratchet band on most routes, i.e.
command→torque coupling is **broadband**, so any coherence claim without the control-band
subtraction is meaningless. Recorded so it is not re-derived.
⭐ **The one informative detail**: `r1e` — the only route with **14** windows — shows by far the
largest specific effect (**+0.522** vs a shuffled p95 of +0.097, a 5x margin), while the seven-
window routes scatter around zero. That is the signature of a real effect seen at insufficient
power, not of a null.
⇒ **What would close it**: the same thing every open question here needs — **more continuous
engaged-creep windows.** At 14 windows the answer was unambiguous on the one route that had them.

## 🛑🛑 **THE COULOMB RELAY IS A *GRIND* LEVER, NOT A RATCHET LEVER — AND THE TWO SYMPTOMS DISSOCIATE**
The kit has blamed the command-proportional Coulomb relay (`FUN_0003b8f6`, knee `0xC40BC`)
for the engaged 6–9 Hz amplification since V80. **The nine scored routes span that knee over
10x, and the ratchet does not respond.**
```
   route build  knee  gain  friction | RATCHET  GRIND      (cs_tq excess, validated estimator)
   r78   V91     600  3564   204     |   9.8      6.1
   r7e   V96     600  3564   204     |  16.5     28.9
   r7f   V96     600  3564   204     |  32.9     14.3
   r96   V102    300  5346   204     |  49.4    248.2
   ra4   V104    300  5346   204     |  15.8     54.7
   ra6   V106    300  5346   204     |  67.8     25.3
   r1e   V107    300  5346   204     |  28.8     27.7
   r22   V112   1800  5346   612     |  35.8     15.0
   r24   V122   3000  5346  1020     |  33.2     14.0

   knee vs RATCHET   rho -0.06  p 0.874      <- NOTHING
   knee vs GRIND     rho -0.69  p 0.039      <- a real lever
```
✅ **[EVIDENCE] the clean GAIN-MATCHED comparison** (all four rows at gain 5346, so the
4x→6x step cannot explain it): knee 300 → 1800/3000 cuts the **grind 41.2 → 14.5 = 2.8x**
while the **ratchet moves 39.1 → 33.2 = 1.18x, inside its own 1.63x split-half floor.**
⚠ **[CONFOUND, stated]** knee and friction `0xC40D2` move together in that comparison
(204 → 612/1020), so the *grind* effect is knee-or-friction, not knee alone. **The ratchet
null is unaffected by that confound** — neither predictor moves it (friction ρ +0.30, p 0.44).
⇒ **the relay attribution for the RATCHET is withdrawn.** It remains a good grind lever.

### ⭐ EVERY LEVER THE KIT HAS PULLED IS A GRIND LEVER
Across **31 images V91→V122 only 278 bytes ever changed** — 0.027 % of the image:
```
   0x35A08-0x35A18 · 0x3AA96 · 0x55DF2-0x55E10 · 0xC40BC-0xC40DC · 0xC4B34-0xC4C03
   0xC4FFC-0xC4FFF · 0xC60A8-0xC60B6 · 0xC61B3-0xC61B5 · 0xC63AC · 0xC640B-0xC6447
   0xC649B · 0xC6AE7 · 0xC6CD0 · 0xC6FFC-0xC6FFF · 0xD6A6C-0xD6A71 · 0xD7A5C-0xD7A71
   untouched ENTIRELY: 0xC5000 model coeff · 0xC7000 · 0xC9000 damper tables · 0xCC000 gain arrays
```
Those 278 bytes include the **4x→6x LKAS gain**, **Lever B**, the **relay knee** and the
**friction** cells. They moved the **grind by 42x** and the **ratchet by nothing**.
✅ **[EVIDENCE] grind and ratchet are DISSOCIATED mechanisms** — same builds, same routes, same
estimator, opposite responses. They need separate levers, and every lever found so far is the
grind's.

### ⭐ THE SHARPEST REMAINING CLUE: TORQUE WITHOUT ANGLE
```
   ratchet margin over each channel's own slope-matched null
     tq 7.62 · cs_tq 7.42   <- the torsion bar
     ws_fr 4.41 · ws_fl 3.95
     cs_rate 1.03 · cs_ang 0.79 · ang 0.83 · wang 0.83   <- ANGLE: nothing
     sc_tq 0.56 · co_tqcan 0.59 · cc_req 0.67            <- COMMAND: nothing
```
✅ **[EVIDENCE] the ratchet is a TORQUE oscillation with no matching ANGLE oscillation.** It
twists the torsion bar without measurably moving the wheel — which is exactly how a driver
feels *ratcheting* rather than *shaking*, and it rules out anything that would have to move
the road wheels to be seen.
⇒ **[BELIEF] it is a motor-torque disturbance injected downstream of the command and upstream
of the bar, active only when engaged.** **What would close it**: a phase test at 8.64 Hz on
each engaged-gated contributor to the motor-torque sum, restricted to cells in the untouched
set above.

## 🛑🛑⭐ **THE RATCHET IS 100 % FIRMWARE-CAUSED — AND UNTOUCHED BY EVERY LEVER THE KIT HAS PULLED**
Three results that only make sense together, all from the validated slope-corrected excess
estimator with slope-matched nulls.

### ✅ 1. IT IS IN THE TORQUE CHANNEL, NOT WHEEL RATE — A 7x BETTER INSTRUMENT
```
   ratchet 5-12 Hz margin over each channel's OWN slope-matched null, mean of 4 routes
     tq        7.62      <- EPS/driver torque
     cs_tq     7.42
     ws_fr     4.41      <- front wheel speed, also real
     ws_fl     3.95
     cs_rate   1.03      <- THE INCUMBENT CHANNEL, AT CHANCE
     ang/wang/cs_ang  0.79-0.83
     sc_tq 0.56 · co_tqcan 0.59 · cc_req 0.67   <- the COMMAND: ratchet absent
```
✅ **[EVIDENCE] in `cs_tq` the ratchet is REAL on 9/9 routes** (excess 9.8–67.8 vs null 2.6–4.1).
✅ **[EVIDENCE] it is NOT in the command** — all three command channels sit below their nulls,
confirming the older *“not in openpilot's command”* claim with a validated estimator.
⚠ **This RETRACTS the “and ANGLE-RATE” half of that older claim**: wheel rate scores **1.03**,
i.e. chance. Every 6–9 Hz endpoint this kit has used was reading the wrong channel.

### 🛑 2. THIRTY-PLUS BUILDS HAVE NOT MOVED IT — AND THE TEST HAD THE POWER TO SEE IT
```
   band     channel   full-range rho    post-V102 rho        V102 vs rest
   GRIND    cs_tq     -0.02 (n.s.)      -0.94   p = 0.005    12.3x
   GRIND    tq        +0.03 (n.s.)      -0.94   p = 0.005    14.4x
   GRIND    cs_rate    0.00 (n.s.)      -0.83   p = 0.042    15.0x
   RATCHET  cs_tq     +0.50  p 0.168    -0.14   p = 0.787     1.6x
   RATCHET  tq        +0.42  p 0.262    -0.31   p = 0.544     1.9x

   ratchet PEAK FREQUENCY over nine builds: 8.64 +/- 0.64 Hz, CV 7.4 %, vs build rho -0.26 (p 0.51)
```
✅ **[EVIDENCE] the GRIND falls monotonically V102→V122 in THREE independent channels**
(ρ = −0.94, p = 0.005, replicated) ⇒ the kit's builds are measurably working on the grind.
🛑 **[EVIDENCE] the RATCHET does not move at all.** Observed spread is **6.9–8.3x** against a
split-half floor of **1.63–1.91x**, so a trend of ≥1.9x would have shown. Its frequency is pinned
at **8.64 Hz ± 7.4 %** across V91→V122. The weak full-range ρ is **POSITIVE** — if anything newer
builds ratchet slightly *more* — though not significantly.

### ⭐⭐ 3. AND YET IT EXISTS ONLY WHEN ENGAGED — SO FIRMWARE CREATES IT OUTRIGHT
```
   route build   engaged exc / null    manual exc / null    ratio    speed-matched?
   r78   V91     11.7 / 4.7            3.2 / 4.6            3.63     no (2.8 km/h)
   r7e   V96     11.5 / 4.7            2.4 / 4.7            4.82     YES
   r7f   V96     93.6 / 4.2            2.6 / 4.0           35.64     YES
   r96   V102    55.4 / 4.6            2.0 / 5.0           27.73     YES
   ra6   V106    48.0 / 4.5            2.7 / 4.1           17.90     no (5.0 km/h)
   r1e   V107    17.1 / 2.9            2.5 / 4.5            6.92     no (2.9 km/h)
   r24   V122    32.5 / 4.5            2.7 / 4.6           12.09     YES

   engaged arm beats its null on 7/7 routes ; manual arm on 0/7
   speed-matched ratio median 19.91x  [4.82, 35.64]
```
✅ **[EVIDENCE] there is NO ratchet peak in manual driving at the same speed** — the manual arm
sits *below* its own null on every route. This is not a mechanical resonance that engagement
amplifies; **engagement CREATES it.**
⚠ **SUPERSEDES the recorded “engaging amplifies 6–9 Hz by 2.8x”** — that figure came from the
tilt-confounded band ratio, which dilutes a peak into its neighbourhood. The validated
contrast is **~20x**, and the manual arm has no peak at all.

### 🛑 WHAT THIS MEANS FOR THE SEARCH — THE LEVER IS ONE WE HAVE NEVER TOUCHED
The three results are only consistent one way: **the ratchet is entirely firmware-caused, and
every calibration lever pulled between V91 and V122 is orthogonal to it.** So it is not
mechanical, not unreachable, and not a measurement failure — **it is a live firmware path at
8.6 Hz, engaged-only, that no build in this kit has yet modified.**
⇒ the question is no longer *“is there a lever?”* but **“which engaged-only path is live at
8.6 Hz that V91–V122 all left byte-identical?”** — answerable by intersecting the engaged-gated
code with the set of cells no build has touched.
⚠ **[BELIEF, not EVIDENCE]** that the responsible path is reachable by calibration at all; it may
need a structural edit. **What would close it**: the intersection above, then a phase test at
8.6 Hz on each candidate.

## 🛑🛑 **THE SPECTRAL TILT CONFOUNDED EVERY 6–9 Hz ENDPOINT — THREE MEASURES WITHDRAWN, ONE SURVIVES**
Chasing why the ratchet Q showed no build trend produced a chain of retractions and one
durable positive result. **The wheel-rate signal is RED**, slope **1/f^0.80 to 1/f^2.37**
across routes — and that tilt alone reproduces everything the old measures reported.
```
   CONTROL: coloured noise, NO resonance whatsoever, nperseg=512, 8 segments
     1/f^1.5  ->  prominence 27.4   fitted Q 1.00   fit r2 0.585
     1/f^2.0  ->  prominence 64.9   fitted Q 1.00   fit r2 0.710
   REAL ROUTES:   prominence 12.2-173.3   fitted Q 1.0-17.6   r2 0.28-0.87
```
❌ **WITHDRAWN — fixed-floor prominence**: comparing 5–12 Hz against a 28–40 Hz floor is large
by construction on any red spectrum. ❌ **WITHDRAWN — fitted Lorentzian Q**: returns Q≈1 with
r² 0.6–0.7 on pure coloured noise, which is exactly what the real routes gave. ❌ **WITHDRAWN
— long-window half-power Q**: white noise alone returns **Q 21.7–29.1** at nperseg=1024, the
same range as the "real" 15.8–21.4, and it **cannot separate true Q=5 from true Q=20**.
⇒ the 0.6×ceiling guard I added earlier is **insufficient** — it rejects white noise but not
coloured, and the routes are coloured.

### ✅ WHAT SURVIVES — SLOPE-CORRECTED EXCESS WITH A SLOPE-MATCHED NULL
Fit the route's **own** power law over 3–40 Hz using only bins **outside** the bands under
test, measure the peak's excess over it, and null it at **that route's measured slope**:
```
   band              excess        slope-matched null p95    verdict
   GRIND 15-25 Hz    9.9 - 421.9   2.6 - 4.1                 REAL on 9/9 routes  (3-100x margin)
   RATCHET 5-12 Hz   2.0 - 8.9     2.7 - 4.1                 real on only 6/9    (1.1-2.3x)
```
✅ **[EVIDENCE] the grind resonance is unambiguous; the ratchet is marginal IN THIS CHANNEL.**
That is the real reason every 6–9 Hz endpoint has underperformed — **the feature is 10–50x
weaker in wheel rate**, a signal-strength problem, not a noise problem. More episodes cannot
fix it; a different channel might.
✅ **[EVIDENCE] and the excess orders by build**: **V91 9.9 → V102 421.9 → V122 23.2**. The 42x
jump lands on the 4x→6x gain step, and the kit has clawed it back to **2.3x above V91's
4x-gain level** — independently matching the earlier Q ordering (9.00 at V102 → 4.50 at V122).

### 🛑 AND IT RETRACTS AN INFERENCE RULE I HAD ALREADY COMMITTED
The pre-registration said *“Q RISING above 4.50 falsifies the damping account → fly V167”*.
**Half-power Q is NON-MONOTONE**: its null sits **ABOVE** the data (real 13.7–34.7 vs null p95
**58–78**), because on a noisy median periodogram the half-power crossing lands on an adjacent
bin. Adding damping lowers Q, but once the peak weakens toward the floor **Q rises again
toward the noise value** ⇒ **a rise cannot distinguish “damping failed” from “damping
worked”**, which is precisely the discrimination the drive was for. **Corrected**: excess is
monotone in peak strength and carries the one-sided logic without the defect.

### ✅ THE DRIVE REQUIREMENT, NOW A MEASURED NUMBER
```
   split-half floor vs windows per half:  3 -> 2.23x    6 -> 1.57x   (extrapolates ~1.2-1.3x at 12-16)
   a continuous pass of T s yields floor((T-5.12)/2.56)+1 windows:  15 s -> 4,  10 s -> 2
   V158's predicted effect is 1.68-2.74x  =>  needs ~24-32 windows
   => 8 passes of 15 s = 32 windows (ADEQUATE);  8 of 10 s = 16 (marginal)
```
⊕ New tool `rlog-tools/score/score_band_excess.py` — the validated estimator, its
slope-matched null, and the split-half floor, with the window warning built in.

## 🛑🛑 **MY RATCHET Q WAS AN ARTEFACT OF THE WINDOW — AND IT EXPLAINS EVERY 6–9 Hz FAILURE**
Having found Q works at 21 Hz, I measured it at the ratchet's own 5–12 Hz. **There IS a resonance
there** — peak 5.5–8.6 Hz, prominence **17–68x** on all nine routes — but its Q showed no build trend,
which was suspicious given how cleanly the 21 Hz Q tracked. It is a **resolution artefact**.
```
   Welch nperseg = NW//2 = 128 at 100 Hz  =>  df = 0.781 Hz
   largest resolvable Q at frequency f  =  f / (2 * df)

   at  7.8 Hz  ceiling = 5.0    measured 1.17-5.50   <- PINNED AT THE CEILING
   at 21.0 Hz  ceiling = 13.4   measured 4.50-9.00   <- comfortably below, VALID
```
✅ **[EVIDENCE] memory's ring-down puts the ratchet at ζ 0.017–0.036, i.e. Q = 14–29.** At df = 0.78 Hz
that is **unmeasurable** — the half-power width would be 0.27–0.56 Hz, narrower than one bin.
⇒ **the 5–12 Hz Q values I reported are the WINDOW's width, not the resonance's. Withdrawn.**
✅ **The 15–25 Hz Q measurement STANDS** — 4.50–9.00 against a ceiling of 13.4, so it is measuring the
resonance and not the window. Everything built on it is unaffected.

### ⭐ AND THIS EXPLAINS A LONG-STANDING PUZZLE
Every 6–9 Hz endpoint this kit has tried has performed badly — the band ratio resolves **1 route in
9**, and the CIs are enormous. **The reason is structural: the ratchet is too NARROW to resolve in a
2.56 s window.** Its energy is smeared across bins, so band sums mix it with neighbouring content and
Q pins at the ceiling. **This is not a noise problem to be beaten with more episodes; it is a
resolution problem, and only a longer window fixes it.**

### ✅ THE DRIVE REQUIREMENT THAT FOLLOWS
```
   to resolve Q = 29 at 7.8 Hz needs df <= 0.134 Hz  =>  nperseg >= 744  =>  >= 7.4 s of
   CONTINUOUS engaged creep per analysis window
```
⇒ **the drive needs engaged creep passes of >= 10-15 s CONTINUOUS each**, not merely many short ones.
⊕ This sits alongside, not against, the existing *“8+ separate passes”* requirement — both are met by
**8+ passes of 10-15 s each**, which is also just a natural slow lap of a car park.
⊕ A resolution guard is now in `peak_q`: it returns **NaN when the measured Q exceeds 0.6x the
window's ceiling**, so the scorer can never again report a window artefact as a damping measurement.

## ✅ **Q's BUILD-ORDERING IS NOT GAIN-CONFOUNDED — AND THE GAIN COST ~2x IN DAMPING RATIO**
```
   build   Q      gain    knee   alpha2
   V91     5.20   3564     600     22      4.00x gain
   V96     4.67   3564     600     22      4.00x
   V102    9.00   5346     300     22      6.00x   <- Q JUMPS at the gain step
   V104    7.25   5346     300     22      6.00x
   V106    7.67   5346     300     22      6.00x
   V107    6.67   5346     300     22      6.00x
   V112    6.50   5346    1800     14      6.00x
   V122    4.50   5346    3000      8      6.00x
```
✅ **[EVIDENCE] the V102→V122 fall is NOT gain-confounded** — the gain is **constant at 5346 across the
whole run**, so the 9.00 → 4.50 decline is attributable to the other cals, not to the gain.
✅ **[EVIDENCE] V158 does not touch the gain** (`0xC6CD0` = 5346 on V122 and V158 alike), so the
V122→V158 comparison is clean on this axis too.
✅ **[EVIDENCE] V122's Q = 4.50 is BELOW the 4x baseline mean of 4.94** ⇒ the kit's builds have not
merely recovered the damping the gain raise cost, they have slightly exceeded it.

### ⚠ AND THIS CHALLENGES A STANDING CLAIM
Memory records: *“The 4x LKAS gain … scales **EXCITATION, not loop gain**.”* **Q disagrees.** Q is a
**shape** parameter: if the gain scaled only excitation, the resonance would grow in amplitude but
**Q would be unchanged**. Q went **4.67 → 9.00** at the gain step — the peak got **sharper**, not just
taller. **A gain that changes Q is acting inside the loop.**
⇒ that gives the operator's 8x experience (*more* grinding) a mechanism it did not previously have:
raising the gain **reduces the damping ratio** rather than merely amplifying what is there.
⚠ **[BELIEF, not EVIDENCE] — the step is CONFOUNDED**: V96→V102 spans several builds (V100, V101,
V102), not the gain alone, and there are only **two routes** at 4x. The Q jump lands exactly on the
gain change, which is suggestive, but this does **not** isolate it. **What would close it**: any route
at 4x gain with otherwise V122-like cals, or a deliberate single-variable gain build — which the
operator has already ruled out on other grounds.
⊕ It does **not** change the recommendation: the gain stays frozen at 6x, and **nothing here suggests
raising it.** If anything it strengthens the existing rule against 8x by supplying the missing why.

## ✅✅✅ **A BETTER ENDPOINT: Q OF THE 15–25 Hz RESONANCE — AND IT MAKES V158 DETECTABLE**
Testing the prediction's assumption (2) — *is the band resonance-limited?* — answered it and produced
a better instrument at the same time.

### ✅ THE BAND IS STRONGLY RESONANCE-LIMITED ON EVERY ROUTE
```
   route  build   peak Hz   prominence vs 28-40 Hz floor   Q
   r96    V102     21.09            610.3                 9.00
   ra4    V104     ~                 ~                    7.25
   ra6    V106     17.97             66.5                 7.67
   r1e    V107     15.62             53.3                 6.67
   r22    V112     20.31             35.5                 6.50
   r24    V122     21.09             32.2                 4.50
```
✅ **[EVIDENCE] assumption (2) HOLDS** — prominence 32–610x above the floor, so amplitude does scale
with 1/damping there and the V158 prediction's basis is sound.
✅ **[EVIDENCE] Q has FALLEN 9.00 → 4.50 across the build sequence** ⇒ ζ = 1/(2Q) rose **0.056 →
0.111, a 2x damping increase** — a direct measurement of the kit's builds adding damping, independent
of the engaged/manual ratio entirely.

### ⭐ AND Q IS A MUCH BETTER INSTRUMENT THAN THE BAND RATIO
```
   Q split-half reproducibility     median 1.20x   p90 1.50x   max 2.00x   (9 routes)
   band-ratio reproducibility       median 1.72x   p90 2.93x   max 3.60x
```
Q is a **SHAPE** parameter, so it is immune to the level shifts that inflate the ratio's noise — the
same level shifts the acoustic uniformity guard had to be built to catch.
```
   V122 reference Q = 4.50
   V158 predicts Q -> 1.64 .. 2.68   (the x1.68-2.74 damping increase)
   that is a x1.68-2.74 change against a 1.20x median / 1.50x p90 floor
   => DETECTABLE, where the band ratio was NOT
```
✅ **This converts V158's drive from “likely unresolvable” to “detectable with margin”.** Added to the
scorer as the PRIMARY instrumented endpoint, with its own split-half reproducibility printed per drive
and a prominence guard (Q is not reported when prominence < 3).

### ⚠ ONE HONEST WRINKLE
On r24 the **pooled** Q is **4.50** while its two halves give **6.00 and 6.75** — pooling more windows
shifts the half-power points, so the pooled estimate is not the average of its halves. The comparison
stays valid because **both sides use the same procedure**, but it means the split-half figure may
**understate** the pooled estimate's true uncertainty. Recorded rather than smoothed over.
⊕ The one-sided logic is unchanged and now sharper: **Q RISING above 4.50 falsifies the damping
account** and points at the Path-2 pumping branch, whose build (V167) already exists.

## ✅✅ **V158 DOES HAVE A FALSIFIABLE PREDICTION — IT IS JUST ONE-SIDED**
V158 had no instrumented prediction at all, which left the drive unfalsifiable on that axis. The
damping arithmetic supplies one, and its **asymmetry** is what makes it useful.
```
   Path-2 case          net added      total viscous     vs baseline 1.571
   worst  (39 % nom)      1.066           2.637              x1.68
   best   (72 % nom)      1.968           3.539              x2.25
   ignored (100 %)        2.733           4.304              x2.74

   IF firmware damping dominates AND the band is resonance-limited (amplitude ~ 1/damping):
       predicted 18-22 Hz   3.88  ->  1.42 .. 2.32
   IF mechanical damping dominates, the effect shrinks toward x1.00 (no change).
   => honest range: 3.88 -> 1.42 .. 3.88, i.e. a x1.00 to x2.74 REDUCTION
   => against a floor of 1.72x median / 2.93x p90 / 3.60x on r24 itself,
      A REDUCTION IS LIKELY UNRESOLVABLE.
```

### ⭐ BUT THE OTHER DIRECTION IS SHARP
**Nothing in the damping account predicts an INCREASE.** Every mechanism in V158 — FactorC lifted,
FactorE's dead zone opened — adds a term that opposes motion in Path 1. So:
```
   V158 reads clearly ABOVE 3.88  (outside [1.60, 10.87] high, or above r24's own half-split 7.56)
       => the damping account is FALSIFIED
       => and it is evidence for the ONE named risk: the Path-2 PUMPING copy dominating
       => which has a BUILT answer, V167 (0xC63A0 1024 -> 512), that halves exactly that term
```
✅ **So the drive is falsifiable even though the positive direction is underpowered.** An underpowered
two-sided test becomes a usable **one-sided discriminator**, and the branch it discriminates into
already has its build cut.
⚠ **[ASSUMPTIONS, stated because the range depends entirely on them]** (1) firmware viscous damping is
a non-trivial share of the plant's total damping — unmeasured; (2) the 18–22 Hz band is
resonance-limited so amplitude scales as 1/damping — plausible but unverified at that band;
(3) the Path-2 net is inside the stability-bounded 39–100 % window. **Any of these failing collapses
the predicted reduction toward x1.00; none of them can produce an increase.** That asymmetry is the
part worth trusting.

## ✅ **ALL 24 UNFLOWN BUILDS TRIAGED AGAINST THE DETECTION FLOOR — ONLY V138 CLEARS IT**
Swept every built-but-unflown image through `eps_closed_loop_sim.ratio_filter`.
```
   V137   alpha2 8->5    lane ratio @20Hz 0.7462   x1.34 reduction   BELOW the 1.72x floor
   V138   alpha2 8->2    lane ratio @20Hz 0.3364   x2.97 reduction   CLEARS
   the other 22 builds -- V139..V167, including V158/V160/V164/V165/V167 --
       no change on the gp-0x6b26 lane, so this simulator cannot price them
```
✅ That is a **limit of the tool, not a defect in those builds**: `ratio_filter` covers the b26 lane
only. V158's damper is `gp-0x6bd0`, Lever B is r24, the deadband builds are elsewhere. And the golden
model does not simulate the damper cascade either — it takes `gp-0x6bd0` as an *input* to the
aggregator. **So V158's prediction rests on the physical-units argument (0.000 → 1.05–1.96 ct/(deg/s)
net), and no tool in the kit can convert that into a predicted band ratio.**

### ⚠ WHICH EXPOSES A REAL TENSION, WORTH STATING RATHER THAN HIDING
```
                  mechanism                     instrumented outcome
   V158   STRONGEST -- broadband viscous        UNPREDICTABLE, and likely below the floor
          damping, quantified, targets the      (the 6-9 Hz band resolves 1/9 routes;
          actual symptom at the actual band)     18-22 Hz needs a ~3.6x move at V122)
   V138   WEAKER -- an EMA corner moved from    PREDICTED x2.97, tool-backed, CLEARS the floor
          19.9 Hz to 5.0 Hz
```
⇒ **For a drive meant to FIX the car, V158 is the better bet.** Its mechanism is the strongest in the
kit and it is the first build ever to deliver damping where the symptom lives.
⇒ **For a drive meant to LEARN something instrumented, V138 is more informative** — it is the only
unflown build whose predicted effect clears the measured floor.
✅ **This does not reopen the V137 question**: V137 is below the floor on the same arithmetic and stays
withdrawn. **V158 remains the recommendation**, because the pre-registration's PRIMARY endpoint is the
operator's report, not the instrument — and what he feels can move even when the band ratio cannot
resolve it. **V138 is the follow-up if he wants a number rather than a verdict.**

⭐ **THE GENERAL POINT**: *“which build should fly”* and *“which build will produce a readable
measurement”* are **different questions with different answers**, and this kit has been conflating
them. Naming both, per build, is more useful than ranking builds on one axis.

## ✅✅ **THE V158-vs-V137 AMBIGUITY IS RESOLVED — V137 IS PREDICTED BELOW THE INSTRUMENT FLOOR**
Last tick I handed the operator a choice between V158 and V137 and called it *“his call”*. **That was
premature** — the kit's own closed-loop simulator can price alpha2, and it says the two are not
comparable.

### ✅ alpha2 HAS A REAL MECHANISM: IT IS AN EMA COEFFICIENT, `>>6`, READ AT `0x41626`
```
   alpha2   a=al/64   corner Hz   |H|@20Hz   |H|@7.8Hz   flown as
     22      0.3438      54.7       0.959      0.993     V91-V107
     14      0.2188      34.8       0.892      0.981     V112
      8      0.1250      19.9       0.729      0.939     V122   <- corner INSIDE the 18-22 band
      5      0.0781      12.4       0.544      0.857     V137 (unflown)
      2      0.0312       5.0       0.245      0.544     V138 (unflown)
```
⚠ But the **open-loop** magnitude does not explain the history: alpha2 22→8 gives **x0.76** while the
measured excess fell **x0.067 (15x)**. A 1.3x open-loop change cannot produce a 15x drop ⇒ either the
loop amplifies it, or the collinear knee/K1 did the work.

### ✅ THE KIT'S OWN SIMULATOR PRICES IT — USING ONLY THE PART IT SAYS TO TRUST
`eps_closed_loop_sim.py`'s header is explicit: the **lane arithmetic is exact and validated against
Ghidra**, while **the plant is only identified 5–~13 Hz** and every routine that uses it above 13 Hz
raises. So I used `ratio_filter`, which is lane-only, and avoided the plant entirely.
```
   pair            lane ratio @20 Hz    measured 18-22 Hz change
   V112 -> V122         0.8172          7.10 -> 3.88 = x0.55     <- VALIDATES the method
   V122 -> V137         0.7462          (unflown)
   V122 -> V138         0.3364          (unflown)
```
✅ **The V112→V122 step validates it**: lane predicts 0.82, measured 0.55 — same direction, right
order, the measured change slightly larger than the lane alone, which is what a closed loop gives.

### ⛔ AND THAT SETTLES THE CHOICE
```
   detection floor (measured, 9 within-drive replicates)   median 1.72x   p90 2.93x

   V137   predicts x0.746  =  a 1.34x reduction   ->  BELOW THE FLOOR, not detectable
   V138   predicts x0.336  =  a 2.97x reduction   ->  at the p90 floor, MARGINAL
```
⇒ **V137 would most likely produce “not resolved” and teach nothing.** It is not a defensible
alternative to V158; **I overstated it last tick and am withdrawing that framing.**
✅ **V158 is the flight.** If the operator later wants the alpha2 axis, **V138 (alpha2 2) is the
version worth a drive**, because it is the one whose predicted effect clears the floor — and it is
already built.
⚠ **[NOTE] `ratio_filter` prices the `gp-0x6b26` LANE, not the measured `cs_rate` band.** The two are
coupled through the loop but are not the same signal, so these are **input-side predictions**, not
direct forecasts of the endpoint. The V112→V122 agreement is one point of empirical support, not a
calibration.

⭐ **THE LESSON**: I offered a choice where the kit already had the arithmetic to decide. **Before
handing the operator an “either/or”, check whether an existing tool can price both options** — here it
took one call to a simulator that was written for exactly this question.

## ⚠ **AN ALTERNATIVE FIRST FLIGHT EXISTS — V137, ALREADY BUILT AND UNFLOWN**
Correlating the measured 18–22 Hz excess against the kit's pre-specified load-bearing cals across the
eight builds with flown routes:
```
   build  18-22Hz   gain  LeverB  knee   K1   alpha2   path2w  b26clamp
   V91     11.81    3564   5244    600   204    22      1024      511
   V96     14.24    3564   5244    600   204    22      1024      511
   V102   742.19    5346    512    300   204    22      1024      511   <- Lever B OFF, worst
   V104   327.51    5346   5244    300   204    22      1024      511   <- Lever B restored
   V106    87.17    5346   5244    300   204    22      1024      511
   V107    57.93    5346   5244    300   204    22      1024      511
   V112     7.10    5346   5244   1800   612    14      1024      511
   V122     3.88    5346   5244   3000  1020     8      1024      511

   knee r = -0.730 | K1 r = -0.648 | alpha2 r = +0.657 | the rest are constant
```
🛑 **EXPLORATORY ONLY: n = 8, and knee/K1/alpha2 moved TOGETHER at V112 and V122.** They are
collinear and **cannot be separated by this data.** No causal claim is made for any one of them.

### ✅ WHAT IS SOLID ENOUGH TO ACT ON
Two things survive the confounding:
1. **Lever B off vs on**: V102 (512) reads **742**, the worst in the set; restoring it at V104 drops to
   **328**. Consistent with V88's measured single-variable result. Lever B stays.
2. **The knee/K1/alpha2 axis moved the endpoint twice**, 57.9 → 7.1 → 3.88. Whatever the split between
   the three, **that axis is the only one with a replicated on-car association with this endpoint.**

### ⚠ SO THERE IS A DEFENSIBLE ALTERNATIVE TO FLYING V158 FIRST
```
   V137   V122 + alpha2 8 -> 5    ONE halfword (5 bytes with CRC)   BUILT, UNFLOWN
   V138   V122 + alpha2 8 -> 2    ONE halfword                      BUILT, UNFLOWN
```
**The two builds answer different questions, and both are legitimate:**

| | V158 | V137 |
|---|---|---|
| rationale | the golden model's own damper prescription, sized at the measured operating point | continue the axis that has twice moved the endpoint on-car |
| mechanism | **strong** — broadband viscous damping, quantified in ct/(deg/s) | **weak/confounded** — collinear with knee and K1 |
| on-car history at creep | **none** | **two steps, both in the right direction** |
| size | 6 halfwords | 1 halfword |

✅ **V158 remains my recommendation**, because its rationale is mechanistic and its dose is sized
against a measured operating point, where V137's support is an n=8 correlation on collinear cals.
⚠ **But if the operator prefers to continue what has demonstrably been working rather than test a new
mechanism, V137 is the build for that, it is already built, and it is one halfword.** That is his call,
not mine, and it is cheap either way — both are cal-only and reversible.

## ⛔ **PAIRED SPEED-MATCHING IS WORSE — AND I AM STOPPING THE ESTIMATOR TUNING THERE**
The instrument's limit is its noise floor, so the obvious move is to lower it. The current speed match
is a percentile **filter**, not a **pairing**; matching each engaged window to a nearest-speed manual
window should cancel more variance. **Tested on the same nine routes, it does the opposite.**
```
   route  build   UNPAIRED A/B   PAIRED A/B
   r78    V91         1.72          1.08
   r7e    V96         1.44          3.63
   r7f    V96         1.29          1.01
   r96    V102        1.48          1.64
   ra4    V104        2.13          2.97
   ra6    V106        1.11          2.18
   r1e    V107        1.82          4.98
   r22    V112        2.76         11.43
   r24    V122        3.60          3.52
   ---------------------------------------------------------
   UNPAIRED   median 1.72x   p90 2.93x   max  3.60x
   PAIRED     median 2.97x   p90 6.27x   max 11.43x
```
✅ **[EVIDENCE] pairing is ~1.7x WORSE at the median and 2x worse at p90.** Two reasons: it **discards
every window without a partner within 0.75 km/h**, so *n* collapses; and a **median of individual
ratios** is a noisier statistic than a **ratio of medians**, because each individual ratio carries the
noise of two windows rather than of two pooled distributions. **The existing design stands.**

### ⭐ AND I AM STOPPING HERE, DELIBERATELY
There are more variants to try — a narrower 19–21 Hz band, log-space averaging, a trimmed mean. **I am
not going to try them.** With **nine routes**, differences below roughly 20 % in split-half scatter are
not distinguishable, and selecting the best of several estimators **by the same statistic used to judge
them** is exactly the selection that manufactures an apparent improvement. That is the tuning analogue
of the window bootstrap this session already had to remove.
✅ **One principled alternative was pre-specified, tested, and lost. The instrument is what it is:
median 1.72x, p90 2.93x, and 3.60x at the reference build.** Those are the numbers the V158 drive will
be judged against, and they were fixed before the drive rather than chosen after it.

## ⚠⚠ **THE INSTRUMENT IS RUNNING OUT OF RANGE — AND I MUST WALK BACK LAST TICK'S PREDICTION**
Replaced the single cross-route replicate with **nine within-drive split-half replicates**: split each
route's episodes in half, score each half independently, compare.
```
   route  build   half A    half B     A/B
   r78    V91      13.74      7.97    1.72x
   r7e    V96      10.49     15.15    1.44x
   r7f    V96      19.10     14.77    1.29x
   r96    V102    787.68    531.49    1.48x
   ra4    V104    321.67    150.78    2.13x
   ra6    V106    108.85     98.31    1.11x
   r1e    V107     46.16     83.92    1.82x
   r22    V112      4.95     13.65    2.76x
   r24    V122      2.10      7.56    3.60x   <- the REFERENCE build, and the WORST
   -------------------------------------------------------------
   median 1.72x    p90 2.93x    max 3.60x
```
✅ The old 1.84x was **accurate, not optimistic** — it sits at the median. But it was **the wrong
number to use**, because reproducibility is **worst where the excess is smallest**, and V122 is the
smallest. As the ratio approaches 1 the noise stops shrinking with it.

### ⚠ WHAT V158 WOULD ACTUALLY HAVE TO DO
```
   to clear the 1.72x median floor  ->  V158 must read <= 2.26
   to clear the 2.93x p90 floor     ->  V158 must read <= 1.32
   to clear r24's own 3.60x         ->  V158 must read <= 1.08
   and a ratio of 1.0 means engaged == manual: the excess is GONE
```
⇒ **V158 is instrumentally detectable only if it very nearly ELIMINATES the engaged excess.** Last
tick I wrote *“detectable if the move exceeds ~1.84x”*. **That was too generous** — it used the median
floor where V122's own route sits at 3.60x. **Corrected.**

### ✅ AND IT REFRAMES THE SIX-BUILD TREND HONESTLY
```
   V102 -> V104   2.27x   marginal
   V104 -> V106   3.76x   RESOLVED
   V106 -> V107   1.50x   BELOW FLOOR
   V107 -> V112   8.16x   RESOLVED
   V112 -> V122   1.83x   marginal
   cumulative     191x    far above the floor
```
✅ **Individual build steps are mostly NOT resolved; the CUMULATIVE trend is.** The monotone run is
carried by two large steps (V104→V106, V107→V112). ⚠ In particular **V112→V122 (1.83x) is marginal**,
so the endpoint did not independently confirm the operator's V122 verdict — it is consistent with it,
which is a weaker claim and the one that is supported.

⭐ **THE LESSON**: an instrument validated over a 191x range is not thereby validated at the bottom of
that range. **Calibrate the floor AT THE OPERATING POINT you will actually use it at.** I validated on
the full sweep and then quoted a detection threshold from the median, while the reference build sits
at the noisy end.

## ✅✅✅ **THERE IS A WORKING CROSS-BUILD INSTRUMENT AFTER ALL — AND IT HAS TRACKED THE KIT FOR SIX BUILDS**
The 18–22 Hz within-drive engaged/manual ratio, paired with each route's build tag from its own cache:
```
   route  build   18-22 Hz eng/man
   r78    V91          11.81
   r7e    V96          10.02
   r7f    V96          18.46          <- the ONLY within-build replicate
   r96    V102        742.19          <- peak
   ra4    V104        327.51
   ra6    V106         87.17
   r1e    V107         57.93
   r22    V112          7.10
   r24    V122          3.88          <- the build now on the car

   V102 -> V122: SIX consecutive builds, STRICTLY MONOTONE DECREASING, 191x total
   corr(build number, log10 excess) = -0.920
   within-build scatter (V96, two routes) = 1.84x   =>  signal/noise ~104x
```
✅ **[EVIDENCE] the endpoint tracks the operator's own verdict**: he called V112 *“the best firmware
yet … least ratcheting ever”* and V122 better still — and the statistic falls 7.10 → 3.88 across
exactly that pair, after falling 742 → 7.10 over the four builds before it.

### ⭐ WHY THIS DOES NOT CONTRADICT THE RECORDED 20–36x BETWEEN-BUILD FLOOR
That floor was measured on **absolute band amplitude between routes** — six routes with identical
control cals spanning 19.9x, another six spanning 36.2x. This is a **within-drive RATIO**, which
cancels road, tyre, weather, alignment and the speed profile before any cross-build comparison happens.
**Same lane, different quantity.** ⊕ This is the third time this session that two records looked
contradictory and turned out to measure different quantities (see also
`gp-0x6bbe` slope-vs-magnitude). **Check the quantity before calling it a contradiction.**

### ✅ SO V158 CAN BE SCORED AGAINST V122's 3.88
The pre-registration's *“expect NOT RESOLVED”* stands for **6–9 Hz**. For **18–22 Hz** there is now a
concrete reference and a concrete prediction:
```
   V122 reference        3.88   [1.60, 10.87]
   V158 predicts         LOWER -- the damper is broadband viscous and opposes motion at 18-22 Hz too
   detectable if         the move exceeds the ~1.84x within-build scatter
   no effect looks like  ~3.9, inside [1.60, 10.87]
```

### ⚠ WHAT THIS RESTS ON — STATED PLAINLY
**[BELIEF, not EVIDENCE] the 1.84x scatter figure rests on ONE within-build replicate** (V96's two
routes). It is the weakest link and everything downstream inherits it.
🛑 **TIME IS COLLINEAR WITH BUILD NUMBER.** Tyre wear, season, road surface and the operator's own
driving all advance monotonically with build order too. A monotone run of six has a chance probability
of ~1/360, so the ordering is unlikely to be coincidence — **but “the builds caused it” and “something
else that also advances with time caused it” are not separated by this data.** The V158 drive is a
genuine test precisely because V158 is a large, single, *known* change against V122.

## 🛑🛑 **SCORE V158 AT 18–22 Hz, NOT 6–9 Hz — THE INSTRUMENT CAN ONLY SEE ONE OF THEM**
Ran both bands through the null gate on every route with a computable null.
```
   route  manEp   6-9 Hz  eng/man         18-22 Hz eng/man          resolves
   r1e      5     3.19 [ 1.67,   6.84]    57.93 [ 28.82, 111.51]    18-22
   r22      4     0.57 [ 0.23,   2.45]     7.10 [  1.29,  17.21]    neither
   r24      5     0.20 [ 0.04,   0.86]     3.88 [  1.60,  10.87]    18-22
   r78      5     1.17 [ 0.44,   2.07]    11.81 [  3.52,  25.51]    neither
   r7e      6     2.19 [ 0.69,   5.26]    10.02 [  4.01,  38.80]    18-22
   r7f      6     1.76 [ 0.35,  19.03]    18.46 [  4.75,  30.64]    18-22
   r96      5     1.04 [ 0.54,   4.45]   742.19 [291.03,1422.98]    18-22
   ra4      4     4.83 [ 0.57,  13.59]   327.51 [ 22.53, 655.22]    18-22
   ra6      7    11.58 [ 3.53,  33.37]    87.17 [ 35.87, 404.97]    BOTH
   ------------------------------------------------------------------------
   6-9 Hz   resolved 1/9        18-22 Hz resolved 7/9
```
✅ **[EVIDENCE] the 18–22 Hz band is a ~7x more sensitive instrument than 6–9 Hz.**
✅ **[EVIDENCE] a large, REPLICATED phenomenon**: the engaged/manual ratio at 18–22 Hz is **> 1 on all
nine routes**, spanning **3.88 to 742** — engagement multiplies that band at creep on every drive
measured. 6–9 Hz scatters around 1 (0.20–11.58) with **no consistent direction**.

### ⚠ CORRECTION TO MY OWN PRE-REGISTRATION
I designated 18–22 Hz a *“built-in control that should not move”* because Lever B is unchanged
V122→V158. **That was wrong.** V158's damper is `-sign(rate) x f(|rate|)` — a **BROADBAND VISCOUS**
term whose LERP is on rate MAGNITUDE, not on frequency. It opposes motion at **all** frequencies, so
it should reduce 18–22 Hz as well as 6–9 Hz.
⇒ **18–22 Hz is an ENDPOINT for V158, not a control** — and it is the only endpoint the instrument
can actually resolve.

### ✅ THE REVISED SCORING PLAN
```
   PRIMARY (instrumented)   18-22 Hz engaged/manual at creep, null-gated   resolves 7/9
   SECONDARY                 6-9 Hz  -- the symptom's own band, but         resolves 1/9
                             expect NOT RESOLVED; that is the floor
   CONTROL                  30-40 Hz, unchanged
   PRIMARY OVERALL          the operator's report -- unchanged
```
⚠ **A caveat that must travel with this**: because Lever B also lives at 18–22 Hz and is unchanged
between V122 and V158, a move there is attributable to the damper **only because Lever B is
byte-identical across the pair** — verified. On any future build that touches BOTH, 18–22 Hz stops
being attributable.

## 🛑🛑 **POWER ANALYSIS ON REAL DATA — THE 6–9 Hz SCORER RESOLVES 1 ROUTE IN 23**
Ran the validated scorer over **every cached route** to answer, before the drive, whether the band
instrument can detect V158 at all.
```
   route  engEp  manEp   6-9 Hz  eng/man        verdict
   r1e     22      5     3.19  [ 1.67,   6.84]  not resolved
   r22      9      4     0.57  [ 0.23,   2.45]  not resolved
   r24     10      5     0.20  [ 0.04,   0.86]  not resolved
   r78     15      5     1.17  [ 0.44,   2.07]  not resolved
   r7e     16      6     2.19  [ 0.69,   5.26]  not resolved
   r7f     19      6     1.76  [ 0.35,  19.03]  not resolved
   r81      4      4     6.10  [ 3.27, 122.43]  no null (too few episodes)
   r96     16      5     1.04  [ 0.54,   4.45]  not resolved
   ra4     20      4     4.83  [ 0.57,  13.59]  not resolved
   ra6     15      7    11.58  [ 3.53,  33.37]  *** RESOLVED ***
   + 13 further routes: NO MATCHED CREEP ARMS AT ALL
```
✅ **[EVIDENCE] 10 of 23 routes are scoreable; 1 of those 10 resolves.** ⇒ **the 6–9 Hz band scorer
resolves roughly ONE DRIVE IN TWENTY-THREE.**

### 🛑 SO SET EXPECTATIONS HONESTLY, BEFORE THE DRIVE
**The band scorer is unlikely to detect V158's effect.** That is not a defect in V158 and not a defect
in the scorer — it is the noise floor of the endpoint, measured rather than assumed. **The operator's
report is the primary endpoint, and on most drives it is the ONLY one.** The pre-registration already
says this; now it has a number behind it.

### ⭐ AND THE BINDING CONSTRAINT IS IDENTIFIED EXACTLY
```
   engaged episodes   9-22   never the limit
   manual  episodes   3- 7   THE LIMIT, on every single scoreable route
```
Thirteen routes have **no matched creep arms at all**, and the ten that do average **5 manual
episodes**. The one route that resolved, ra6, has **the most manual episodes (7)**.
⇒ **the missing ingredient has always been MANUAL CREEP, and it is the cheapest thing to fix.**
**8+ separate manual creep passes** is the single change that would most improve the drive's power —
more than any extra engaged driving. This is now the headline requirement on the drive card.

⊕ Note r24's 0.20 [0.04, 0.86] would read as a strong engaged *reduction* at 6–9 Hz on a naive CI, and
the null correctly rejects it. Seven of the ten scoreable routes have CIs spanning 1.0; **the endpoint
is dominated by between-episode variance, not by firmware.**

## ⛔✅ **NO STABLE ACOUSTIC MARKER ACROSS ROUTES — AND SPEED-MATCHING ALONE IS NOT ENOUGH**
Two results from running the creep acoustic contrast across four existing routes.

### ⛔ THE HF CLUSTERS DO NOT REPLICATE — THE ENDPOINT MUST STAY WITHIN-DRIVE
r24's fallback threw up a coherent **2389–2688 Hz cluster at +4–5.5 dB**, which looked like it might be
an acoustic signature of the ratchet. It is not:
```
   r24  (fallback)  2389-2688 Hz  +4.2 .. +5.5
   r23  (primary)    408- 416 Hz  +5.2 .. +7.3
   ra6  (primary)    908- 920 Hz  +9.7 .. +10.5
   r22  (primary)    193/385/387/443/488/1885/2705 Hz  +3.0 .. +4.8
```
**Every route has a different cluster.** ⇒ there is **no stored acoustic signature to compare a V158
drive against**; the acoustic endpoint must be **within-drive** (V158's engaged arm vs its own manual
arm), exactly like the band scorer. Recorded so nobody builds a cross-route acoustic reference.

### ⛔ AND ra6 EXPOSED A HOLE IN MY OWN GUARD
```
   ra6   speed gap 1.18 km/h   -> PASSED the speed check
         20-50 Hz +3.00 dB  AND  2000-5000 Hz +3.21 dB  -- the WHOLE spectrum lifted together
```
A speed match does **not** exclude a global level difference (mic gain, window position, engine load,
surface). My tool checked the speed gap and then reported the spectrum as a result. **That is the same
class of error the 30–40 Hz negative control exists to catch in the band scorer** — I had built the
acoustic tool without its analogue.

✅ **THE UNIFORMITY GUARD**, now added and validated on real data:
```
   ra6   band spread 1.55 dB, median level +3.21 dB  ->  🛑 FAILED (global level shift)
   r22   band spread 1.23 dB, median level +0.34 dB  ->  ✅ PASSED (band-specific)
```
The test is **large level AND small spread**, not spread alone — which is why r22's similar spread
passes on a near-zero level while ra6's fails on +3.21 dB.
⭐ **EVERY CONTRAST NEEDS A NEGATIVE CONTROL, INCLUDING THE ONES YOU JUST BUILT.** I added the null
gate to the band scorer after it over-claimed, then built an acoustic tool with no equivalent and it
over-claimed the same way on the first route that could expose it.

## ✅✅ **THE AUDIO CHANNEL IS VALIDATED — AND IT WAS POINTED AT THE WRONG BAND AND SPEED**
Audio is the channel that has tracked the operator's report where the bus has not, so it was the last
drive-side dependency to audit. It runs: **16,364 blocks aligned to the CAN timebase on r24**, with
`zstandard`/`cereal` present and 635 rlog segments on disk.

### ⛔ BUT `audio_engaged_vs_manual.py` ANSWERS A DIFFERENT QUESTION
Its own comment explains why it abandoned the engaged/manual split on r24 — *“hopelessly
speed-confounded (52.8 vs 11.5 km/h median) … produces a uniform +10 dB”* — and substituted a
within-engaged **21–26 Hz** high-vs-low contrast, speed-matched at **28–82 km/h**. Sound for r24. But
for V158 that is **the vibration band, not the 6–9 Hz ratchet**, at **a speed where V158 is
architecturally inert.** Run as-is on the V158 drive it would report on the wrong band at the wrong
speed.

### ✅ `rlog-tools/decode/audio_creep_v158.py`
- **PRIMARY: engaged vs manual, restricted to CREEP (1–24 km/h), speed-matched.** The r24 confound came
  from engaged *highway* against manual *creep*; the drive card's matched manual creep segment is
  precisely what makes this contrast valid instead of confounded.
- **It REFUSES if the arm medians differ by more than 2 km/h**, naming the r24 +10 dB artefact as the
  reason — rather than reporting a speed difference as an acoustic result.
- **FALLBACK: within engaged creep, high-vs-low 6–9 Hz** — the kit's validated design, retargeted from
  21–26 Hz to the ratchet band — clearly labelled as unable to separate *“the damper worked”* from
  *“less ratchet happened to occur”*.
- Reports 20–2000 Hz so no band is pre-committed; refuses loudly at every insufficient-data point.

### 🛑 IT IMMEDIATELY CAUGHT A REAL CONFOUND ON r24 — AND THAT IS A DRIVE REQUIREMENT
```
   596 creep audio windows: 271 engaged, 325 manual
   speed-matched 3.4-17.8 km/h: engaged p50 10.3 vs manual p50 7.9, gap 2.43 km/h
   ⛔ REFUSED (gap > 2.0) -> fell back, and said so
```
r24 **has** creep audio in both arms, and the primary contrast was **still** invalid because the two
arms sat 2.43 km/h apart. ✅ **So it is not enough to drive “some creep engaged and some creep
manual”** — the two arms must be **the same stretch at the same speed**. That is now in the drive card.
⊕ The guard is what makes a null trustworthy: without it this route would have produced a confident
acoustic number built on a speed difference.

## ✅✅ **THE DRIVE-SIDE TOOLCHAIN IS COMPLETE AND DE-HARDCODED — THREE COMMANDS**
Every stage between the rlog and an answer has now been audited, fixed and run.
```
   1  python rlog-tools/decode/extract_route.py --route <N> --prefix <rlog prefix> \
                                                --segments <n> --build V158
      -> writes the cache AND verifies it is scoreable (fields present, creep windows in
         BOTH arms) -- it FAILS LOUDLY at extract time instead of after the drive is over

   2  python rlog-tools/score/score_v158_creep.py r<N>
      -> episode bootstrap, 6-9 Hz primary / 18-22 Hz secondary / 30-40 Hz control,
         speed census, and a SPLIT-HALF NULL that GATES every verdict

   3  python rlog-tools/decode/audio_engaged_vs_manual.py r<N>
      -> the acoustic channel: PCM aligned to the CAN timebase by logMonoTime, split on
         cc_lat, 20-2000 Hz so no band is pre-committed, speed-matched control
```
✅ **Dependencies verified present on this machine**: `zstandard`, `cereal`, numpy, scipy; **635 rlog
segments** on disk; **23 routes** have both rlogs and a cache.

### ✅ WHAT WAS WRONG WITH EACH, AND WHAT IT COST
```
   extract_r*.py    ONE FILE PER DRIVE (~125 lines, four real values).  extract_r24.py's own
                    docstring still reads "Cache routes 22 and 23".  A stale header is harmless;
                    a stale WIRE_SCALE or segment count is not.        -> generic extract_route.py
   score_v133       WINDOW bootstrap -- 2.6x too confident, measured.  -> score_v158_creep.py
                    Then MY replacement over-claimed until the null gated it.
   audio_..._manual HARDCODED ROUTES = {'r22', 'r23'} -- every new drive needed the file edited,
                    and a stale entry would silently analyse the WRONG drive.
                    -> resolves the prefix from the rlog FILENAMES; verified it reproduces both
                       hardcoded values exactly, and `--list` shows what is runnable.
```
⭐ **Three tools, three different failure modes, all of the same family: a per-drive constant that
nothing checks.** The fix in each case was to derive the constant from the data on disk, or to refuse
loudly when it cannot be derived. **A pipeline that cannot be run without editing it will eventually
be run after editing it wrong.**

## ✅✅✅ **THE SCORER IS VALIDATED ON REAL DATA — AND IT CAUGHT ITSELF OVER-CLAIMING**
Ran the new pipeline end-to-end on **r24, a real V122 creep drive**, before the V158 flight.

### ⛔ MY OWN SCORER OVER-CLAIMED, AND THE KIT ALREADY HAD THE RULE
```
   real run    6-9 Hz  0.20 [0.04, 0.86]   -> verdict printed: "RESOLVED"
   --null      6-9 Hz  0.41 [0.06, 17.06]  -> the endpoint resolves NOTHING on this route
```
The verdict tested only *does the CI exclude 1.0*. It ran the split-half null **only when asked**
and **never used it** — exactly what `feedback-run-the-control-before-the-measurement` forbids
(*“four claims died to controls in one session”*). **Fixed: the null is now computed automatically
and GATES the verdict.**

### ✅ VALIDATED THREE WAYS ON r24
```
   6-9 Hz    effect 0.20 [0.04,  0.86]   null 0.20 [0.00, 3.22]   NOT RESOLVED
   18-22 Hz  effect 3.88 [1.60, 10.87]   null 0.19 [0.02, 0.76]   RESOLVED
   30-40 Hz  control 0.61 [0.28, 5.91]   -> flat, guard passes
   speed census: engaged p50 11.3 / manual p50 11.2, median gap 0.14 km/h
```
1. **Reproduces the recorded reference**: r24's 18–22 Hz reads **3.88**, against the V133 script's
   recorded **3.88 [1.63, 10.08]** — same point estimate, slightly wider CI, as an episode bootstrap
   should give.
2. **Resolves what is known to be real** — the 18–22 Hz engaged excess, well outside its null.
3. **Refuses what a naive CI would have claimed** — the 6–9 Hz 0.20 [0.04, 0.86].

### 🛑 A CONCRETE DRIVE REQUIREMENT FALLS OUT OF THIS
**On r24 — 10 engaged episodes, 5 manual — the 6–9 Hz band CANNOT BE RESOLVED AT ALL**, and 6–9 Hz is
**V158's primary target**. The manual arm could not even support a split-half null (5 episodes, needs 8).
=> **a V158 drive shaped like r24 would produce NOTHING on the band that matters.**
✅ **The drive must ALTERNATE engaged and manual creep many more times** — not two long stretches but
**8+ separate engaged and 8+ separate manual passes** over the same low-speed loop. More *windows* do
not help; only more *episodes* do. This is now in the drive card, and the extractor checks it at
extract time rather than leaving it to be discovered after the drive.

⭐ **THE BROADER POINT**: I audited the tooling the pre-registration named, found a window bootstrap,
replaced it — and my replacement then over-claimed in a different way that only running it on **real
data** exposed. **A new instrument is not trustworthy because it fixed the old one's bug.** Run it on
a route whose answer you already know.

## ⛔✅ **THE PRE-REGISTERED SCORER HAD A WINDOW BOOTSTRAP — FIXED BEFORE THE DRIVE, NOT AFTER**
The V158 pre-registration told the operator to reuse `score_v133_creep.py`. Its contrast, control
guard and refusal logic are sound. **Its bootstrap violates this kit's own standing rule.**
```
   def boot(e, m, i, k=8000, seed=0):
       d = [np.median(rng.choice(e[:, i], len(e))) / ... for _ in range(k)]
```
`rng.choice(e[:, i], len(e))` resamples **INDIVIDUAL WINDOWS**. Windows overlap by `NW//2` and come
from a handful of contiguous stretches, so they are strongly correlated and nothing like `len(e)`
independent draws. The rule is explicit: *“Bootstrap over EPISODES, not windows — window bootstraps
manufacture significance.”*

### ✅ QUANTIFIED ON SYNTHETIC DATA — 6 EPISODES x 12 WINDOWS, TWO SAME-DISTRIBUTION ARMS
```
   EPISODE bootstrap   1.06 [0.23, 2.61]     spans 1.0
   WINDOW  bootstrap   1.06 [0.58, 1.48]     spans 1.0
   => the window CI is 0.38x as wide  ==  2.6x TOO CONFIDENT
```
Both span 1.0 here, but **an effect near the boundary would be declared significant when it is not**,
and a real creep drive has more windows per episode than this synthetic, so the error is larger.

### ✅ `rlog-tools/score/score_v158_creep.py` — THE CORRECTED SCORER
- **EPISODE bootstrap**: windows clustered into maximal runs of consecutive same-arm windows;
  resampling is over EPISODES, pooling their windows. Unit-tested: 3 episodes from runs
  0-9 / 30-37 / 60-65, sizes [10, 8, 6].
- **PRIMARY band 6–9 Hz** — V158 is a damper build and the ratchet is 6–9 Hz. 18–22 Hz kept as a
  secondary, since Lever B is unchanged V122→V158 and **should not move** (a built-in control).
- **30–40 Hz control guard** retained, and it now **returns without printing a verdict** if it fails.
- **Per-window speed census** printed, with a median-gap warning — the guard against a wheel order.
- **`--null` self-test**: split-halves ONE arm against itself. Same firmware, same arm ⇒ the CI must
  span 1.0. If it does not, the pipeline manufactures significance and nothing may be believed.
- **Refuses below 4 episodes per arm**, and says *more windows will not help — you need more separate
  engaged and manual STRETCHES*. That is a **drive-design instruction**, not a statistic.
⊕ Uses only `cc_lat` / `cs_v` / `cs_rate`, so it avoids the kit-wide `raw14` off-by-one cache trap.

⭐ **THE POINT**: the pre-registration is what makes a drive decisive, so **the tooling it names must
be audited BEFORE the drive, not after the numbers are in.** Auditing it afterwards is how a null
becomes a result.

## ✅ **THE CROSS-CHECK AUDIT IS COMPLETE — EVERY LOAD-BEARING NUMBER TRACED TO ITS SOURCE**
The audit that caught my P/D swap was run over the rest of this session's load-bearing figures.
Everything else traces to the authoritative source.
```
   figure                        used for                     source, verified verbatim
   6-9 Hz 0.859                  V160 power calculation       eps_chain_lanes.py, V88-vs-V87
   9-12 Hz 0.604 [0.465,0.943]   "                            same line
   15-22 Hz 0.549 [0.407,0.844]  "                            same line
   0.5-3 Hz 1.192 = NULL         "LKAS command untouched"     same block
   [0.18, 5.51] split-half       6-9 Hz detection floor       route-71 null, same file
   gp-0x6ac0 = 99 [94,113]       every dose in the ladder     model's MEASURED operating point
   ceiling 512                   the bang-bang margin         0xC77A0 + 0xC6158, byte-read
   dose 50 at 99 counts          V158's design target         model AND V74's flown measurement
   f' 2.174 / 0.346             Path-2 hands-off weighting   memory, on-car
```
✅ **Only ONE fresh derivation disagreed with the record, and the record was right** (the P/D swap).
Everything else reproduces. ⭐ **The pattern worth keeping: a fresh derivation is a HYPOTHESIS until
it is checked against the standing record.** One in nine of mine was wrong, and it was the one I had
already written into a handoff.

### ✅ WHAT REMAINS, STATED WITHOUT HEDGING
The calibration search is **complete**: every aggregator lane has a phase or structural verdict, every
pointer-table family is attributed, and all three complaints have a firmware answer or a reason there
is none. Six images cover every outcome of one drive, all verified cell-by-cell.
**The only remaining input is the drive.** Nothing further can be learned from the bytes.

## ✅✅ **FINAL VERIFICATION — ALL SIX FLYABLE BUILDS CHECK OUT, CELL BY CELL**
```
   build   sha   LeverB  0xC63A0  gate    FactorC[26]  dose@99   role
   V158    OK     5244    1024    0xfb       429          50     *** FLY FIRST ***
   V164    OK     5244    1024    0xfb       234          27     better but too heavy
   V160    OK     6553    1024    0xfb       429          50     better, effort fine
   V165    OK     5244    1024    0xfb       429          65     unchanged
   V167    OK     5244     512    0xfb       429          50     WORSE (not a bare revert)
   V161    OK     6553    1024    0xfb         0           0     Lever-B-only twin (no damper)
```
✅ Every SHA matches its build report; every cell is exactly as designed; the V67 gate repoint
(`0x3AA96 = 0xfb`) is present on all six, so Lever B is reachable everywhere. **V161's dose 0 is
correct** — it is the no-damper twin. All six `.rwd` files present and non-superseded. **No mandatory
file over 200 KB** (cap 256).

## ✅ **RECONCILED — `gp-0x6bbe`'s “76 % OF RAIL” DOES NOT CONTRADICT THE ×1.7–×2.7 FIGURE**
Two records describe the same lane in different units, and they invite a specific mistake:
```
   memory:  "VISCOUS + a DC pedestal -- flat ~90 ct/(rad/s); p50 73.6 ct flat across 0-6 deg/s"
   facade:  "-K1 x (column rate) DAMPER ... DEAD as a lever: flat +-512 bound, already at 76 % of rail"
```
76 % of the ±512 producer ceiling is **~389 counts of TOTAL magnitude** — but the **damping** part is
the **SLOPE** (90 ct/(rad/s) = 1.571 ct/(deg/s)); the **DC pedestal damps NOTHING.**
✅ So comparing V158 **by slope** (2.733 vs 1.571) is correct, and comparing **by absolute counts**
(50 vs ~389) would be **WRONG** — it would credit a constant offset as damping.
⭐ **When two records give different numbers for one lane, check they are the same QUANTITY before
calling it a contradiction — or before averaging them.** Here one is a slope and one is a magnitude.

## ⛔⛔ **I HAD THE PID's P AND D SWAPPED — THE STANDING RECORD CAUGHT ME**
Auditing older memory for claims this session overturned turned up two entries that **contradicted my
own phase computation**, and **they are right and I was wrong.**
```
   MEMORY-PART3: "Stage A = P (gain 153-256/1024) · Stage B = I (98/1024) · Stage C = D at 2048/1024 = 2.0"
   MEMORY.md:    "net phase lag -11 to -27 deg at 6-9 Hz · P:(I+D) ~2-5:1"

   my assignment (WRONG)            the record (RIGHT)
     0xC6B1E  256  = D                0xC6B1E  256  = P     matches "153-256/1024"
     0xC6B0A   98  = I                0xC6B0A   98  = I     matches "98/1024"
     0xC6ADE 2048  = P                0xC6ADE 2048  = D     matches "2048/1024 = 2.0"
```
I assigned the three gain LERPs from **Ghidra's variable numbering** (`uVar12/16/20`) instead of from
the record. Recomputed with the correct assignment:
```
                        |P|     |I|     |D|    P:(I+D)   net phase @7.8 Hz
   mine  (P,D swapped)  64.00   1.953   0.012   33.0:1     -1.7 deg
   CORRECT               8.00   1.953   0.098    4.3:1    -13.0 deg
   the standing record                          ~2-5:1    -11 to -27 deg
```
✅ **The corrected row lands inside BOTH recorded ranges.** ⭐ **Cross-check a fresh derivation against
the standing record before publishing it** — the record is a control, and here it was the only thing
between a wrong number and the handoff.

### ✅ WHAT THE CORRECTION DOES *NOT* CHANGE
**`gp-0x6ad4` is still not a damper, and V162/V163 stay superseded — the case is STRONGER.**
−1.7° was near-zero **stiffness**; **−13.0° is a LAG**, which is strictly *worse* for stability than
0°. Raising its ceiling adds loop gain **with negative phase** into a Q 14–29 resonance.
⚠ **But my "u16-bound, ~1300x too weak" margin was WRONG and must be restated:**
```
   Kd (Q10 Y at 0xC6AE6)   2048    8192   32768   65535 (u16 MAX)
   net phase @7.8 Hz     -12.97  -10.96   -2.72   +8.28 deg
```
=> the D gain would need **Kd ~ 163 (Q10 167,170)** to reach the P term, and **the u16 ceiling delivers
only +8.3°** — not the +1.06° I claimed. **The elimination stands** (real damping needs +90°), but the
honest margin is *"the D path tops out at +8° of lead"*, not *"1300x too weak"*.

### ✅ AND IT DOES NOT MOVE THE PATH-2 BOUND — WHICH IS THE POINT WORTH KEEPING
The bound is **invariant to the PID gain**, because the same `G_pid` appears in Path 2's route *and*
in the loop whose stability supplies the bound:
```
   Path2 = 0.615 x G_pid x s          L = G_gov x G_obs x G_pid x s < 1
   => Path2 <= 0.615 / (G_gov x G_obs)     -- G_pid CANCELS
```
✅ So **V158's net remains ×1.7–×2.7** and every downstream conclusion is unaffected. A bound built
from a *structural* relation survived an 8x error in one of its factors; a bound built from the
absolute number would not have.

## ⛔ **CORRECTION — THE PATH-2 THREE-TAP GAIN IS 1.0, NOT 10.0 (a 10x error in a loop gain)**
An audit of the memory index found an earlier entry claiming the observer's three-tap structure is
*“a PURE GAIN of 10.0, both memory taps DEAD”*. The taps-dead half is right; the 10.0 is not.
```
   FUN_0003b8f6:
      fVar14 = *(float *)(tp+0x5048);                   <- 1.0f   THE COEFFICIENT
      fVar14 = 0.0*hist + fVar14*fVar19 + fVar15*0.0;   => 1.0 * fVar19  IDENTITY PASSTHROUGH
      ...
      fVar14 = 10.0;                                    <- a CLAMP constant, LATER, same variable
```
✅ **[EVIDENCE] `tp+0x5048` = `0xC4048` reads 1.0f** (byte-verified, and it matches the long-standing
`c1 = 1.0f, c2 = 0.0f, c0 = 0.0f` memory). The earlier read grabbed the **clamp** where the
**coefficient** was wanted — Ghidra reuses `fVar14` for both.
⚠ **Why it matters**: the Path-2 stability bound divides by `G_gov × G_obs`. A 10x overstatement of
the observer's forward gain would have tightened the bound on `s` by 10x and made Path 2 look far
smaller than it is. The bound as computed used the correct 1.0.
⭐ **THE TRAP**: a decompiler reuses one local for unrelated values within a function. **Read the
assignment that feeds the expression you care about, not the last assignment to that name.**

## ⛔ **`0xC63AE` IS NOT A CLEAN LOOP-GAIN LEVER EITHER — SAME TRAP, DIFFERENT CELL**
The stability work suggested one more candidate, and it fails the rule written two ticks ago.

`FUN_00038148` computes `uVar7 = |iVar6| * cal(0xC63AE) >> 10` **before** the LERP, so `0xC63AE`
(**virgin, 1024 on all 142 images**) scales the **whole Path-2 forward path**. Unlike a per-term
weight it preserves the observer's relative weighting, so it looked like the clean loop-gain
reduction — and one that needs no V158 base.

⛔ **But `gp-0x6ad6` is the PID's FEEDBACK term, not a gain node:**
```
   uVar19 = *(short*)(gp-0x6ad6)              <- data read
   uVar24 = clamp(uVar19, +-cal 0xC6200)
   iVar30 = gp-0x4f60 - uVar24                <- THE ERROR
```
=> shrinking it **moves a SUBTRACTION**: `err = measured - feedback`, so a smaller feedback gives a
**LARGER** error and a **LARGER** PID output. The loop-gain reduction and the error growth push
**opposite ways**, and which wins depends on the same unknown `s`. **Net ambiguous => not built.**

⭐ **This is the rule from two ticks ago applied to myself**: *before lowering a scalar, ask what the
sum is FOR.* In an aggregator a scalar is a **gain**; here it feeds a **subtraction**, so it sets an
**operating point**. The observer-weight trap and this one are the same trap wearing a different cell.
⊕ **Path 2 now has no clean cal lever at all**: the per-term weights corrupt the model, and the
output scale moves an operating point. `0xC63A0` remains the sole exception, and only because
`gp-0x6bd0` was exactly 0 at creep before V158.

## ✅✅✅ **THE LAST UNKNOWN IS BOUNDED — V158 DELIVERS ×1.7 TO ×2.7, NOT 0 TO ×2.74**
The RAM-LERP slope `s` did **not** need extracting — the model records two failed attempts at exactly
that. **The loop's own stability bounds it.**

### ✅ THE PATH-2 LOOP IS CLOSED — ALL 13 HOPS VERIFIED BYTE-WISE
```
   FUN_0003a382 reads gp-0x6ad6 @0x3A6BA   writes gp-0x6ad4 @0x3A8A0
   FUN_0003aa2c reads gp-0x6ad4 @0x3ACA8   writes gp-0x6b94 @0x3ACFA
   FUN_0004503c reads gp-0x6b94 @0x453E0   writes gp-0x6ace @0x454D2      <- the governor hop
   FUN_0003b8f6 reads gp-0x6b98 @0x3B8F6   writes gp-0x6bfc @0x3BC1A      <- the observer
   FUN_00038148 reads gp-0x6bfe @0x38218   writes gp-0x6b70 @0x382D2
                reads gp-0x6bd0 @0x38150                                  <- THE DAMPER enters here
   FUN_00037fe6 reads gp-0x6b70 @0x38006   writes gp-0x6ad6 @0x38142
```
⚠ My first closure attempt failed on two hops because I assumed `FUN_0003a382` ended at `0x3A620`; its
real extent is `0x3A382-0x3A8A7`. **Ghidra had the extent; I guessed instead of asking.**

### ⭐ THE BOUND, AND WHY IT NEEDS NO EXTRACTION
The **same `0.332 × s` segment** sits in Path 2's route to the aggregator **and** in the loop's own
forward path, and the `gp-0x6bfe` entry coefficient is exactly **1** (`iVar5 = gp-0x6bfe - (iVar4>>4)`).
So:
```
   L = G_gov x G_obs x 0.332 x s      must be < 1, because the car is STABLE
                                      (the ratchet is a lightly-damped resonance, not divergence)

   G_gov*G_obs >= 1.0   => s < 3.01  => Path 2 <= 0.614 x Path 1  => net 0.39 of nominal
   G_gov*G_obs  = 2.174 => s < 1.39  => Path 2 <= 0.283 x Path 1  => net 0.72 of nominal
   (f' alone is 2.174 hands-off, and the governor is ~unity-passing, so G_gov*G_obs >= 1 holds)
```
✅ **[EVIDENCE] V158's net creep damping is bounded to 1.05–1.96 ct/(deg/s)**, i.e. a total of
**2.63–3.53 vs the measured 1.571 baseline = ×1.67 to ×2.25** — against the **×2.74** I quoted when I
ignored Path 2, and against the **×1.00** it would be if Path 2 cancelled the damping entirely.
=> **the pumping does NOT cancel the damping. V158 still delivers a real, substantial increase.**

### ✅ WHAT THIS SETTLES, AND WHAT IT DOES NOT
**SETTLED**: Path 2 cannot overturn V158. The worst admissible `s` still leaves **39 % of nominal**,
and the first non-zero creep damping this car has ever had. The ×2.74 headline should be **restated as
×1.7–×2.7**, and the pre-registration's predicted effect updated accordingly.
**NOT SETTLED**: the exact `s`, and the hand-traced net **sign** (three inversions) — still **[BELIEF]**.
⊕ **V167 keeps its role**: halving `0xC63A0` halves the `0.204 × s` term directly, moving the net from
0.39–0.72 of nominal up toward 0.69–0.86. It is the sharpest available test of this whole bound.

⭐ **THE METHOD WORTH KEEPING**: when a coefficient resists extraction, **ask what the system's
observed behaviour already implies about it.** A closed loop that demonstrably does not diverge bounds
every gain inside it. Two sessions failed to extract `s`; the stability argument bounds it in one step
and needs no bytes at all.

## ✅✅✅ **THE “UNRESOLVED HOP” IS CLOSED — AND V158's PATH-2 RISK IS NOW BOUNDED AT ~20 %**
The model's longest-standing open item on this chain (*“there is AT LEAST ONE UNRESOLVED HOP here…
gp-0x6b94's 4 unchecked readers … [OPEN]”*) resolves by triaging those four on what they **write**:
```
   FUN_00036bec   gp-0x6b48 = EMA(gp-0x6b94 x 64, cal tp+0x73d8) >> 6    SECONDARY -- feeds the
                                                                        backlash fn FUN_00036828
   FUN_0004503c   writes gp-0x6ace                                       *** THE GOVERNOR -- the hop ***
   FUN_0004595a   gp-0x6aca / gp-0x68c8..ce / gp-0x6d9c                   not the chain
   FUN_0007ff08   gp-0x4e62 / gp-0x4e3e / gp-0x2e10 / gp-0x2df6           not the chain
```
✅ **`FUN_0004503c` writing `gp-0x6ace` matches the byte-verified bridge already in memory**:
`gp-0x6b94 → governor → gp-0x6ace → comp-add → gp-0x6acc → shaper → gp-0x6b08 → gp-0x6b98 → FOC`.
=> **the model's note is STALE; memory had the answer.** ⊕ A second consumer is new: `gp-0x6b94` also
drives the **backlash** function through `gp-0x6b48`, which the model did not record.

### ⭐ THE CONSEQUENCE: PATH 2 DOES NOT REACH THE MOTOR INDEPENDENTLY
It feeds `gp-0x6ad4` **back into the SAME aggregator**, so **both routes exit through `gp-0x6b94`** and
can be compared directly:
```
   PATH 1 (direct)   gp-0x6bd0 -> FUN_0003aa2c -> gp-0x6b94                        gain 1.000
   PATH 2 (loop)     x w(0xC63A0)=1.0 · x pol(-1) · x double 9.6 Hz EMA (0.615)
                     x RAM-LERP slope s · err = 6b98-src - gp-0x6ad6 (-1)
                     x PID (64>>5 = 2) x ceiling 170/1024 (0.332) · x pol(-1)
                     -> gp-0x6ad4 -> the SAME aggregator -> gp-0x6b94        gain 0.204 x s
```
⚠ **[BELIEF] net sign** `(+1)(−1)(−1)(−1) = −1` ⇒ **opposite to Path 1 ⇒ pumping.** Hand-traced
through three inversions; not verified end-to-end, and note the model's claim is about the sign
*inside* Path 2, not the net at the aggregator.
✅ **[EVIDENCE] net magnitude 0.204 × s** ⇒ **Path 1 dominates unless the RAM-LERP local slope
s > 4.9.** That LERP is a **bounded shaping curve, not a gain stage**, so s > 4.9 is implausible.

### ✅ WHERE THIS LEAVES V158
**The named risk is now BOUNDED at roughly 20 % of the damping it buys**, not merely "unresolved".
Path 1 damping should dominate by ~5x. Combined with V74 having flown this dose fault-free and the
model having prescribed the edit knowing the architecture, **V158's risk profile is materially better
than it looked two ticks ago — and I should say so as plainly as I stated the risk.**
⊕ **V167 remains the right “worse” branch** — if the drive is worse anyway, halving `0xC63A0` is the
one edit that tests this bound directly, because it halves exactly the 0.204 term.
⚠ **[OPEN] the RAM-LERP slope `s`** is the last unknown. Closing it needs the `gp-0x64b8`/`gp-0x641c`
rows, which are built by `FUN_000389ec` from `FUN_000382d8`'s tables — the model records two failed
attempts at exactly this extraction.

## ⛔ **THE PATH-2 WEIGHTS ARE NOT A LEVER FAMILY — AND WHY `0xC63A0` IS THE ONE EXCEPTION**
Having found that `FUN_00038148` weights every Path-2 term, the obvious next move is to lower the
others. **It is wrong, and the reason sharpens V167's own justification.**

### THE TEMPTING READING
Every term gets the **extra `pol` multiply**, so a Path-1 **damper** arrives as a Path-2 **pumper**.
`gp-0x6bbe` is a **measured** viscous damper (1.571 ct/(deg/s), phase ~0° vs rate) and, unlike the
base damper, it is **LIVE ON STOCK at creep**. Its Path-2 weight `0xC63A2` is **VIRGIN on all 142
images**. So it reads as a standalone ratchet lever that needs no V158 base.

### ⛔ WHY IT IS NOT ONE
**Path 2 is a DISTURBANCE OBSERVER.** It sums the assist lanes to predict what the motor is doing and
compares that prediction against a measurement. Lowering a term's weight does **not** simply remove
pumping — **it makes the observer's model WRONG**, biasing the residual by exactly the amount removed.
The pumping-signed arrival is not a defect to be trimmed; it is **what an observer subtracting a
predicted contribution is supposed to look like.**
=> lowering `0xC63A2`, `0xC63A4`, `0xC63A6`, `0xC63A8` or `0xC63AA` corrupts a model of a term the
firmware has always included. **Not built. Not proposed.**
⊕ This also retro-justifies the **strike on `0xC63A6`** (the `gp-0x6b26` weight, moved on the
superseded V154/V155): the objection is not only that GATE 2 was uncertifiable, it is that the edit
**de-tunes an observer**.

### ⭐ WHY `0xC63A0` IS DIFFERENT — THE ARGUMENT V167 ACTUALLY RESTS ON
```
   on V122 the base damper gp-0x6bd0 is EXACTLY ZERO at creep (FactorC Y[0] = 0)
   => the observer's creep-band sum has NEVER contained a damper term
   => V158 introduces, at FULL weight, a term the observer was never tuned to see
```
✅ **V167's 512 is therefore CLOSER to the observer's pre-V158 behaviour than V158's 1024 is.** It is
not "de-tuning a working observer" — it is **partially withholding a term the observer has no history
with**, on the one lane where that argument holds. **On every other weight the argument fails**,
because those terms have always been in the sum.
⚠ It still cuts both ways: if the motor really does produce the damper torque, the observer *should*
see it, and halving it biases the residual. **That is why V167 is a DISCRIMINATOR for the “worse”
branch and NOT a predicted improvement** — exactly how it is filed.

⭐ **THE GENERAL RULE**: **before lowering a weight, ask what the sum is FOR.** In a torque
aggregator a weight is a gain and lowering it reduces a contribution. In an **observer** the same
edit changes a *model*, and "less of the bad-signed thing" is the wrong frame entirely.

## ✅✅✅ **V167 BUILT — THE KNOB FOR V158's ONE NAMED RISK. `0xC63A0` 1024 → 512.**
ONE HALFWORD on a V158 base, 56/56 assertions, CRC 50/50, **1 payload byte**.
```
   image 93970b6d65e10ff989b429efa1f387f52e48d7cba80938d1dd4f15dfa58ac61d
   rwd   b80180d89afdafb9579fc095dc254f7af8d7e9086c7abea35e36c81138ae53c4
```
### ⭐ `FUN_00038148` APPLIES PER-TERM WEIGHTS — AND ONE OF THEM IS THE DAMPER'S
```
   sum = (gp-0x6b4e * 0xC63A8 >>10) + (gp-0x6b4c * 0xC63AA >>10)   <- LKAS
       + (gp-0x6b26 * 0xC63A6 >>10) + (gp-0x6b46 * 0xC63A4 >>10)
       + (gp-0x6bd0 * 0xC63A0 >>10) + (gp-0x6bbe * 0xC63A2 >>10)   <- THE DAMPER
   sum = (sum * pol * cal) >> 10      <-- the EXTRA pol multiply that inverts the sign
```
✅ **[EVIDENCE] `0xC63A0` is `gp-0x6bd0`'s PATH-2 weight and nothing else.** Halving it halves the
**pumping** copy while **Path 1's damping is byte-for-byte untouched** — Path 1 reads the same cell in
a different function (`FUN_0003aa2c` @`0x3AC78`) with no such weight. The build asserts all five
sibling weights and both FactorC/FactorE records byte-identical.
✅ **[EVIDENCE] lowering is the safe direction**, in the model's own words for the sibling cell:
*“LOWERING is safe BY CONSTRUCTION — reducing a feedback magnitude cannot destabilise a stable loop
whatever its phase. RAISING is the classic destabiliser.”* History: **1024 on 137 images, 2048 on five
(V72/73/74/75/81) — raised and flown, NEVER lowered.**
✅ **[EVIDENCE] it is INERT without V158**: on V122 the damper is exactly 0 at creep, so `0xC63A0`
multiplies zero. That is why the base is V158.

### ⭐ IT REPLACES "REVERT" AS THE ANSWER TO V158's "WORSE" BRANCH
A bare revert to V122 discards **Path 1's damping along with Path 2's pumping** and tells you nothing
about which caused the regression. **V167 keeps the damping and removes half the pumping ⇒ it
DISCRIMINATES.** The decision tree is updated.

### ⚠ WHAT IS NOT ESTABLISHED
**[BELIEF]** that Path 2's pumping matters at all. Two effects push **opposite** ways and the net is
**not resolved**: Path 2 reaches the aggregator via `gp-0x6b70 → FUN_00037fe6 → gp-0x6ad6 → the PID
→ gp-0x6ad4`, whose ceiling is throttled to **170/1024 = 16.6 %** at creep by `0xC67C2` — but f′ is
**2.174 hands-off vs 0.346 hands-on**, so the observer is **6.3x MORE sensitive hands-off**, which is
where the ratchet lives.
**[NOTE]** the final linear gain also needs a **RAM LERP's local slope** (rows at `gp-0x64b8`/
`gp-0x641c`), which the model records as never successfully extracted. **512 is a HALVING, one notch
on a safe axis — NOT a computed optimum.**

## ⚠ **CORRECTION — `FUN_000382d8`/`FUN_000389ec` ARE NOT PURELY MONITOR-SIDE**
Earlier this session I filed both as monitor-side because they write no aggregator lane. **That test
was too narrow.** `FUN_000389ec` writes `gp-0x64b8`/`gp-0x64b6`/`gp-0x641c`/`gp-0x640a` — **exactly the
RAM LERP rows `FUN_00038148` reads** to shape Path 2's output — and `FUN_000382d8` feeds
`FUN_000389ec` through `gp-0x62fc..0x630c`.
=> **the chain is `FUN_000382d8` → `FUN_000389ec` → the RAM LERP → `FUN_00038148` (Path 2)**, so both
ARE in the torque path, via a RAM table rather than a direct lane write.
⭐ **A function can be in the loop without writing a lane cell.** "Writes no aggregator lane" proves
it is not a lane PRODUCER; it does **not** prove it is out of the loop. **Follow the RAM it writes.**

## ✅✅ **PATH 2's COEFFICIENTS ARE LOCATED — THE FIR CANNOT RING, AND THE MODEL'S NOTE IS STALE**
The model says Path 2's loop gain *“lives in EIGHT float coefficients … **NEVER BYTE-READ BY ANY
SESSION** … => **GATE 2 CANNOT BE CERTIFIED**”*. `FUN_0003b8f6`'s decompile settles it: **only THREE
are floats.** The rest are `ushort` reads converted and scaled in code — which is why reading them
as float32 returned denormals.
```
   GENUINE float32:              u16 EMA coefficients (read as ushort, scaled in code):
     c1 tp+0x5048 = 1.0f           tp+0x50D4 = 573   a=0.1399  fc  22.3 Hz  |H|0.951 lag 16.6 deg
     c0 tp+0x504C = 0.0f           tp+0x50D8 = 3686  a=0.8999  fc 143.2 Hz  |H|1.000 lag  0.3 deg
     c2 tp+0x5050 = 0.0f           tp+0x50D0 = 408   a=0.0996  fc  15.9 Hz  |H|0.906 lag 23.7 deg
                                   tp+0x50D6 = 246   a=0.0601  fc   9.6 Hz  |H|0.784 lag 37.0 deg
   y = 1.0*x + 0.0*x[n-1] + 0.0*x[n-2]      tp+0x50D2 = 1020  = K1, a GAIN not a pole
   = IDENTITY PASSTHROUGH                   tp+0x50BC = 3000  = the relay KNEE, a divisor
```
✅ **[EVIDENCE] the 3-tap FIR is an IDENTITY PASSTHROUGH with both history taps multiplied by 0.0**
⇒ **2 zeros, 0 poles, no feedback path — IT CANNOT RING, whatever the input.** This confirms the
existing `0xC4048` memory (`c1=1.0f, c2=0.0f, c0=0.0f`) from the consuming code rather than from bytes.
✅ **[EVIDENCE] every Path-2 pole is now located and quantified.** The model's *“never byte-read”*
and *“GATE 2 CANNOT BE CERTIFIED”* notes are **superseded for the DYNAMICS**: ringing is structurally
excluded and the cascade is known.

### ⚠ BUT THIS SHARPENS V158's RISK RATHER THAN CLEARING IT
`tp+0x50D6` = **246 ⇒ corner 9.6 Hz, sitting IN the ratchet band**, and the decompile applies it
**TWICE** (`fVar15` then `fVar19`) ⇒ a double EMA: **|H| = 0.784² = 0.615, lag = 2 × 37.0 = 74° at
7.8 Hz.**
🛑 **AND f′ RUNS THE WRONG WAY FOR US**: memory records `f′` p50 **2.174 hands-off vs 0.346
hands-ON** — the observer lane is **6.3x MORE sensitive hands-off**, and **the ratchet is a hands-off
creep phenomenon.** So Path 2's pumping-signed copy of `gp-0x6bd0` is at its **LARGEST exactly where
the ratchet lives.** I had earlier cited f′ compression as reassurance; **read in the correct
direction it is the opposite.**
⊕ What is still uncertifiable is the **relative WEIGHT** of Path 1's damping and Path 2's pumping into
the final motor command — Path 2's route runs through the hop the model flags as *“AT LEAST ONE
UNRESOLVED HOP”* (`gp-0x6b94`'s 4 unchecked readers: `FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`,
`FUN_0007ff08`). **[OPEN] closing it needs those four decompiles.**
⭐ **NET POSITION ON V158, STATED HONESTLY**: Path 1 damping is the primary and by design; Path 2
pumping is real, attenuated to 0.615 by the double 9.6 Hz EMA but amplified by hands-off f′; and V74
already flew this dose without an adverse report. **It remains the right build to fly — and the
“worse” branch of the pre-registered tree now has a quantified mechanism, not a hand-wave.**

## ⚠⚠ **V158's NAMED RISK — `gp-0x6bd0` FEEDS *BOTH* AGGREGATORS, AND PATH 2 INVERTS ITS SIGN**
Found in the golden model's **facade header** (`eps_lkas_chain_model.py`, "KNOWN MODELLING GAPS"),
which the four modules do not repeat — so a session that reads only `lanes`/`control` never sees it.

> *“`gp-0x6bd0` is called ‘damping’. **True for PATH 1 only.** `FUN_00038148` (Path 2) applies its
> **OWN extra `pol` multiply**, so with **pol = −1 the SAME cell arrives PUMPING-signed there.** The
> sign does not transfer between the two aggregators.”*

✅ **[EVIDENCE] byte-confirmed — `gp-0x6bd0` has 5 readers, and two are the two aggregators:**
```
   0x3AC78   FUN_0003aa2c   PATH 1 aggregator   -> DAMPS
   0x38150   FUN_00038148   PATH 2 consumer     -> extra pol multiply => PUMPS at pol = -1
   0x34726 / 0x347BC  its own writer function     0x1C114  (unattributed)
```
✅ **[EVIDENCE] `gp-0x6752` (pol) is −1 on this car** — verified three ways, ★★★★★ in memory.
=> **V158 raises a term that damps in Path 1 and pumps in Path 2.**

### ⊕ WHY THIS IS A CAVEAT, NOT A CANCELLATION
- Path 1 is the **primary** torque aggregator; Path 2 is the **disturbance-observer** loop.
- Path 2's contribution reaches the car through **f′, which is compressed 6.3x when the driver
  pushes** — the same mechanism that explained V89's and V97's nulls.
- **V74 already flew this cell's dose** (delivered 50 at the ratchet's operating point, 67.4 % duty
  at engaged creep, 0 frames at the ceiling) with no adverse report attributable to it.
- The golden model **prescribed this exact edit knowing the architecture.**
⚠ But it **cannot be certified**: the model states Path 2's loop gain is unlocated (below), so the
relative weight of the damping and pumping contributions is **unknown**.
⭐ **THIS IS THE NAMED MECHANISM FOR THE “WORSE” BRANCH.** The pre-registered decision tree already
routes *worse → revert to V122*; it now has a **specific predicted cause** rather than a bare
possibility, which makes the drive strictly more informative.

## ⛔ **CORRECTION TO THE GOLDEN MODEL — PATH 2's “EIGHT FLOAT COEFFICIENTS” ARE NOT AT THOSE ADDRESSES**
The model says Path 2's loop gain *“lives in EIGHT float coefficients at `tp+0x50d4/0x50d8/0x504c/
0x5050/0x50bc/0x50d0/0x50d2/0x50d6` — **NEVER BYTE-READ BY ANY SESSION**”*. Read now:
```
   tp+0x504C 0xC404C  0.0             tp+0x50D4 0xC40D4  2.2592335e-38
   tp+0x5050 0xC4050  0.0             tp+0x50D6 0xC40D6  2.8350151e-30
   tp+0x50BC 0xC40BC  6.7593616e-37   tp+0x50D8 0xC40D8  2.8067167e-40
   tp+0x50D0 0xC40D0  9.3677923e-39   tp+0x50D2 0xC40D2  1.3885641e-37
```
⛔ **Every one is a DENORMAL**, and three of the addresses are **the kit's own known u16 cals**:
`0xC40BC` = the relay knee (3000), `0xC40D0` = the friction EMA pole (408), `0xC40D2` = K1 (1020).
**No firmware uses denormals as filter coefficients.** => **the stated addresses are WRONG** —
consistent with the model's own admission that they were never verified, and with CLAUDE.md's
*“off-by-0x1000 on tp-relative cals has recurred FIVE times.”*
⭐ **THE TRAP THIS DEFUSES**: a future session reading those cells as floats gets ≈ 0 and could
conclude **“Path 2's loop gain is zero, so Path 2 is dead”** — a wrong and consequential inference,
because Path 2 demonstrably runs (V89/V97 measured f′ compression through it).
=> **Path 2's loop gain remains UNLOCATED. GATE 2 for Path 2 stays uncertifiable** — now for the
sharper reason that the coefficients have never actually been found, not merely never read.
**[OPEN] what would close it**: locate the real coefficient block from `FUN_0003b8f6`'s decompile
(float loads, not u16), then re-derive the loop gain.

## ⛔⛔ **PEAK COMMAND OSCILLATION HAS NO REMAINING FIRMWARE LEVER — THE LIMIT IS ALREADY OPEN**
V166 was designed, written, and **killed by its own base assertion before emitting an image.**

### THE CASCADE, AND WHY IT LOOKED LIKE A LEVER
```
   setpoint = STEER_TORQUE x -4      => openpilot's +-4096 rail is setpoint +-16384
   setpoint = clamp(setpoint, +-arb_setpoint_limit)      <-- the binding limit
   lkas_max = min((setpoint x gain) >> 15, forward_clamp 0xC61B2/B4 = 3072)
```
The golden model's `Calibration` default reads **15360**, and the model notes *"openpilot's
torqueBP*4=16384 clips the top 6.25 % at 15360; raising is safe."* At 6x gain
`(15360 x 5346)>>15 = 2505 < 3072`, so the clamp does NOT bind and the setpoint limit is the sole
binding limit. That looked like the one untouched lever for the third complaint.

### ⛔ IT IS ALREADY DONE ON THE FLYING BUILD
```
   record     stock    V122/V158/V160
   0xE4180    15360 -> 16384
   0xE41A8    15360 -> 16384    <-- THE A160 RECORD (gp-0x674e selector 1) -- OUR CAR
   0xE41F8 / 0xE4220 / 0xE5180 / 0xE51A8 / 0xE51D0 / 0xE51F8   also raised
   => exactly 8 of the 28 records, matching the model's "V38 patches all 8 reachable records"
   (16384 x 5346) >> 15 = 2673, still < 3072  =>  protocol reach 4096/4096, NOTHING is clipped
```
✅ **[EVIDENCE] the full +-4096 command range is already delivered.** The edit I designed is a
**no-op on this car.**

### ⭐ THE MISTAKE, AND THE RULE IT BREAKS
I read the **model's default Calibration field (15360 = STOCK)** and scanned the **stock image**,
then reasoned about the flying build. CLAUDE.md already carries the rule verbatim: *"Check build
lineage before proposing a cal lever — grep build_v*_tva.py + BUILD-LINEAGE.md before naming any
address; state its on-car result."*
⊕ **The build harness caught it**: the base assertion found **20** flat-15360 records where the stock
scan found 28, and refused to build. **That is the assertion doing exactly its job** — a base-value
check is not bureaucracy, it is the thing that stops a no-op reaching the car.
⭐ **A model's `Calibration` DEFAULTS ARE STOCK VALUES, NOT THE FLYING BUILD'S.** Read the image.

### ✅ SO THE THIRD COMPLAINT IS CLOSED, AND HERE IS WHY
Peak command oscillation is **sustained one-sided saturation at the 13-bit +-4096 rail** (6.4 % of
frames at 2–8 km/h, episodes to 4 s). With the setpoint limit already at openpilot's own rail:
- the firmware **delivers the entire command range**; there is nothing left to un-clip;
- openpilot rails because it wants **more than 4096**, and 4096 is the **CAN signal's 13-bit maximum**
  — a **protocol** limit, not a firmware one;
- the only firmware quantity that could deliver more torque per protocol count is the **GAIN**, and
  8x was measured **worse** (6x = 1.13 dB vs 8x = 2.24 dB acoustic excess) and rejected by the
  operator's own conditional instruction.
=> **the symptom is bounded by (protocol range x gain), the protocol is fixed, and the gain is frozen
by a measured result.** No firmware lever remains. Closing it needs either an openpilot-side change
(**barred by standing instruction**) or accepting the trade the 8x test already priced.

## ⛔ **THE AUTHORITY COLLAPSE CURVE ADMITS NO BENEFICIAL CHANGE WITHIN THE SAFETY RULE**
Open item closed by exhaustive test, not by argument.
```
   mode 7, ALL FOUR RECORDS VIRGIN on 90 images
     0xE547C / 0xE5404  primary  X = [70, 72, 78, 80]   Y = [254, 234, 12, 0]
     0xE52FC / 0xE5284  blend    X = [32, 42, 80, 112]  Y = [255, 255, 255, 0]
   authority 254 -> 0 across TEN byte-counts (raw torque 2240 -> 2560)
   🛑 measured MEDIAN OVERRIDE TORQUE = 2235 = byte 69 -- ONE COUNT below X[0] = 70
```
=> **the operator drives on the knee**, so a small road-load increase tips him over a cliff that
drops authority 254 -> 12 in eight byte-counts. That is the “authority disappears” mechanism.

### ⛔ EVERY RESHAPE THAT HELPS VIOLATES THE RULE
The rule is **MONOTONE-NON-INCREASING: never more authority than stock at any torque.** Tested:
```
   hold longer     X=[74,76,78,80]     VIOLATES (254 vs 234 at byte 72, and above stock to byte 79)
   gentler slope   X=[70,72,88,90]     VIOLATES (150.8 vs 12.0 at byte 78)
   raise mid Y     Y=[254,234,120,0]   VIOLATES (120.0 vs 12.0 at byte 78)
   collapse earlier X=[60,70,78,80]    LEGAL -- but gives LESS authority everywhere
```
✅ **[EVIDENCE] this is not an argument, it is an enumeration**: authority is a monotone-decreasing
function of torque, so *holding it up longer anywhere* IS *more than stock somewhere*. The two are the
same statement. **No legal change improves it.**

### ⚠ THE TRADE, STATED FOR THE OPERATOR — NOT DECIDED HERE
Honda collapses authority **because the driver is pushing**; the curve is a driver-in-control override.
Raising it means **the driver must push harder to take the wheel back.** That is a genuine safety
trade, and it is the operator's call, not the kit's. If he wants it, the minimal bounded form is
`X[0]/X[1]` **70,72 -> 72,74** (two byte-counts ≈ 64 torque counts of extra hold, nothing else moved),
which is the smallest change that moves the knee off his median override torque. **NOT BUILT.**

### ⛔ AND THE `0xC61BC` CAVE PROBE IS NOT WORTH IT RIGHT NOW
It is a **probe, not a fix** — diagnostic value only — and caves are this kit's **only bricking class**
(V24, V27, V48B all bricked the ECU). With the calibration search exhausted and V158 ready to fly,
spending a brick risk on a measurement before the cheap measurement (a drive) has been taken is the
wrong order. **Revisit only if the V158 drive is ambiguous AND the operator authorizes a cave.**

## ✅ **THE POINTER-TABLE MAP IS COMPLETE — ALL 37 ATTRIBUTED, NO NEW TORQUE-PATH LEVER**
The last large unexamined family is closed. Triaged by **what each function WRITES**, which is far
cheaper than decompiling and is decisive.
```
   FUN_000382d8  8 tables (0xCC9FC + 0xC7B40..0xC80B0)   writes gp-0x63e8..0x64a4, 0x62fc..0x630c
                 => ZERO aggregator-lane stores (strict scan).  gp-0x630c is read by FUN_000389ec,
                    the plausibility monitor that fires FUN_0004613e(0x4377) => MONITOR-SIDE.
   FUN_0003b338  0xC8198     writes gp-0x6b6e, gp-0x6a0a        not a lane
   FUN_0003b416  0xCA5DC     writes gp-0x6996                   not a lane
   FUN_0003b49a  0xCBCA4     writes gp-0x6b28 and gp-0x6b2a
                 gp-0x6b28 : **0 READERS image-wide => write-only telemetry, DEAD**
                 gp-0x6b2a : 1 reader, FUN_00037fe6 = the UNITY-weighted Path-2 term sum
                             => the plant-model / observer path. V89 already flew there and its
                                null is explained by f' COMPRESSION. Not new ground.
   FUN_00035154  0xC7888     writes gp-0x6bbe                   the boost lane, already characterised
```
✅ **[EVIDENCE] no unexamined pointer-table family reaches the torque path.**

### ✅ AND NO LOOP-WIDE LAG SOURCE AT THE SENSOR
`gp-0x4f60` (the torque sensor, feeding the PID error, r24's `dtorque` and the boost curve) has
**64 readers and 5 writers, all five in the 0x7Fxxx acquisition layer**. The model already confirmed
*“FUN_0007e74a has NO EMA/IIR anywhere, and gp-0x4f60 is a SINGLE physical measurement”* ⇒ **there is
no filter to de-lag.** The one remaining class of change that could add phase margin loop-wide does
not exist in this firmware. **CLOSED.**

### ⚠ SCANNER CORRECTION — V850 STORE OPCODES ARE 0x3A/0x3B ONLY
My triage scan treated **0x38–0x3B** as stores; **0x38/0x39 are LOADS**. That over-included, and it
briefly showed `FUN_0003b49a` “writing” `gp-0x4f60` when it only reads it.
⊕ The `FUN_000382d8` verdict is **unaffected**: an over-inclusive filter that found **no** lane
writes still finds none when tightened — the error was in the safe direction. **State which direction
a filter error runs before deciding whether a conclusion survives it.**

## ✅✅✅ **V164 / V165 BUILT — EVERY BRANCH OF THE DECISION TREE NOW HAS A FLYABLE IMAGE**
Both on the V158 base, cal-only, outside the cave/bricking class.
```
   V164  LOW dose   FactorC Y[0] := Y[1]      0xD77DA 429->234, 0xD77EE 426->233   55/55  4 payload B
         image ec5ce14fbdce81256e7c6babdad744dc0f841648228b89b0e5bad5c596a8cc73
   V165  HIGH dose  FactorE Y[1],Y[2] 539->700  0xD7818/1A + 0xD782C/2E            62/62  4 payload B
         image 41585a5f698cb341f749506f0162c2693f1620b10fa25da71d9c39b26bb9c30a
```
### ✅ THE DOSE LADDER, IN PHYSICAL UNITS
```
   build   FactorC  FactorE(99)  dose   viscous added   TOTAL creep viscous   vs stock-only
   V122        0         0          0     0.000            1.571                x1.00
   V164      234       120         27     1.476            3.047                x1.94
   V158      429       120         50     2.733            4.304                x2.74
   V165      429       156         65     3.553            5.124                x3.26
   (baseline: gp-0x6bbe measures 1.571 ct/(deg/s) ON-CAR; stock creep damping is EXACTLY 0.000)
```
✅ **V164 carries a free bonus**: setting Y[0] := Y[1] makes FactorC **MONOTONE** (`[234,234,429,908]`),
removing the 35-60 km/h dip V158 deliberately accepts — so it is lighter **and** better-shaped.
✅ **V165 holds Y[3] = 927 deliberately**: a rising segment must survive on X 2500..4000 or FactorE
flattens across the whole rate axis into a near-**BANG-BANG RELAY** (V72's error, a limit-cycle
generator at a lightly-damped resonance), and holding Y[3] keeps the build-time rule at V158's 388.
⚠ **V165's dose 65 sits just ABOVE the model's stated ~43 [30,60].** That is deliberate and
**conditional**: fly it ONLY if V158 measured as insufficient, in which case the data has contradicted
the requirement. Not a first choice — the model argues the true delivered dose is HIGHER than computed.

### ✅ THE COMPLETE FLIGHT PLAN
```
   FLY FIRST   V158   single-variable, the only change above the instrument floor
     better + effort OK          -> V160  (Lever B increment, unmeasurable but free)
     better + wheel too heavy    -> V164  (dose 50 -> 27, halves the drag, monotone shape)
     unchanged, effort unchanged -> V165  (dose 50 -> 65; overturns “err low” WITH DATA)
     worse                       -> V122  (revert; damper is destabilising, not damping)
     no creep episodes           -> re-drive (V158 is inert above ~35 km/h)
```
=> **no branch of the drive can now leave the kit without a prepared next step.**

## ✅✅✅ **V158 IS THE FLIGHT, NOT V160 — A POWER CALCULATION DEMOTED THE LEAD BUILD**
Pre-registered before the drive: `docs/scoring/SCORING-V158-preregistered.md`.

V88 measured Lever B single-variable across a **10.24x** step. V160 adds **1.2496x**. Extrapolating
log-linearly from V88's own measured ratios, against this kit's own same-firmware detection floor:
```
   band       V88 10.24x step    V160 1.25x predicts    floor (same-firmware null)
   6-9 Hz         0.859              0.986  (-1.4 %)     [0.18, 5.51]  ~3-5x
   9-12 Hz        0.604              0.953  (-4.7 %)
   15-22 Hz       0.549              0.944  (-5.6 %)     [0.59, 1.34]  ~40 %
```
=> **the Lever B increment is 4-30x BELOW the floor — unmeasurable on one drive.** It adds an untested
dose (V62: *“2x ≈ the OPTIMUM, not a point on a ramp”*) and **destroys attribution if the drive comes
back worse.** ✅ **FLY V158**: single-variable vs V122, and its change — creep damping **0 → 2.733
ct/(deg/s)** — is the only one large enough to resolve. V160 becomes the follow-up if V158 is good.

⭐ **THE GENERAL RULE**: *a build is only worth a drive if its predicted effect exceeds the instrument
floor.* Stacking a sub-floor increment onto a resolvable one buys nothing and costs attribution. This
is the first time this kit has run that calculation BEFORE flying rather than after.

## ⛔ **THE BACKLASH BAND IS CAL-REACHABLE — AND CLOSED BY THE LIMIT-CYCLE EXCLUSION**
`gp-0x6b44` has **exactly 1 reader (`0x36760`) and 1 writer (`0x36BB0`, in `FUN_00036828`)**, and the
writer is pure calibration arithmetic — so the band width IS cal-reachable, contrary to the previous
"RAM cell, no lever" note:
```
   sVar23 = (uVar20 - cal 0xC61A8[=102])  if uVar20 > 102 else 0,  scaled by cal 0xC63CE[=1024] >> 10
   clamp:  >= cal 0xC619E [=307]  ->  307          (upper)
           <  cal 0xC61A0 [=123]  ->  123          (LOWER FLOOR)
   fault path (bit 0x800000)      ->  cal 0xC619A [=102]
   gp-0x6b44 = sVar23   then  half-width = (gp-0x6b44 * uVar7) >> 15  in FUN_00036682
```
✅ **[EVIDENCE] the hysteresis half-width NEVER narrows below 123 counts**, even at zero excitation.
✅ **[EVIDENCE] all five cals are VIRGIN across all 163 build images.**
⭐ On the control-theory reading this looked like a real lever: a backlash's describing function has
**phase lag that is WORST at small input amplitude** — precisely the creep/micro regime — and narrowing
the band *reduces* lag rather than adding gain, so it does not repeat the V162 error.

### ⛔ WHY IT IS CLOSED ANYWAY
The kit's strongest ratchet characterisation settles it:
> *"The ratchet is a lightly-damped **RESONANCE**, Q 14–29 — ring-down ζ 0.017–0.036, the only
> estimator that passes its control; **limit cycle EXCLUDED**; motor/rack-side."*

**A backlash-driven oscillation IS a limit cycle.** The ring-down evidence excludes one, so the
backlash is **not generating the ratchet**; narrowing it would mainly admit more small-signal noise
(which is what a hysteresis band is FOR), and the lane is attenuated **8x** at 7.8 Hz by the following
0.93 Hz low-pass regardless. ⛔ **NOT a ratchet lever. Recorded so it is not re-proposed.**
⊕ The counter-risk is real and symmetric: a deadband exists to reject small-signal chatter, so
narrowing it can *increase* stutter. With the limit-cycle route excluded there is no argument that the
benefit outweighs that risk.

## ✅✅ **THE STATIC SEARCH IS NOW COMPLETE — EVERY LANE IN THE AGGREGATOR IS ADJUDICATED**
```
   lane / cal              phase or structure at 7.8 Hz            verdict
   r24  (Lever B 0xC6446)  K x d(torque)/dt, +90 deg               DAMPS -- at 6553 = int16 ceiling (V160)
   gp-0x6bd0 (V158)        -sign(rate) x f(|rate|), f near-linear   DAMPS -- dose 50, model's own [30,60]
   r26  (0xC6444)          same class as r24                       FALSIFIED -- flew as V71c, worse
   gp-0x6ad4               P 99.88 % @ -1.7 deg, D 0.02 %          STIFFNESS -- structurally eliminated
   gp-0x6b26               -K x acceleration                       ADDED INERTIA -- does not damp
   gp-0x6bbe               measured viscous, 1.571 ct/(deg/s)      already live; raising = more assist
   gp-0x6b46 / 0xC63D2     slow trim, |H| 0.119, 81.8 deg lag      NOT a lever either direction
   backlash band 0xC61A0   floor 123 ct, virgin                    CLOSED by limit-cycle exclusion
   gp-0x6b62 return-centre DEAD engaged (0.0000 / 75,227 frames)   inert
   gp-0x6ade               0 writers image-wide                    dead
   gp-0x6b4c LKAS          command lane                            EXCLUDED (a DC constant carries no 7.8 Hz)
```
=> **V160 carries the only two lanes that actually damp, each at or at the model's stated limit.**
✅ **[EVIDENCE] this is an exhaustive adjudication of the aggregator, not a survey** — every lane the
model lists now has a phase or a structural verdict.

### ⚠ WHAT THIS MEANS, STATED PLAINLY
Further progress is **measurement-limited, not analysis-limited.** The instrumented engaged-vs-manual
contrast collapses to **~1.1x** under controls (≤10 % of the 6–9 Hz band, ≤2 % of RMS as a 7.8 Hz line),
yet V88 demonstrably changed the felt symptom — **so the bus instrument is the weak link, not the
firmware model.** The next real information comes from a creep drive **with audio**, which is the one
input static analysis cannot supply.

## ⛔⛔ **TWO LEVERS CLOSED — r26's ARM AND THE FUN_00036682 FILTER POLE**
Both were about to be built. Both are negatives, recorded so they are never re-proposed.

### ⛔ 1. `0xC6444` (r26's LKAS-gated arm) — FALSIFIED, AND THE FALSIFICATION IS VALID
The golden model **strikes** this cell on the grounds that it *"is reachable only on a build whose
control path is already ruled out"*. **That premise is stale** — the repointed control path
(`0x3AA96 = 0xfb`) is exactly what has been flying since V88, so the cell IS reachable now:
```
   build  0x3AA96        r26 0xC6444   r24 0xC6446   reachable?
   71a    0xc5 (stock)         512          512      NO -- gp-0x683c has 0 writers
   71b    0xc5 (stock)         512          512      NO
   71c    0xfb (repointed)    3072         5244      YES  <-- IT WAS GENUINELY TESTED
   88     0xfb                 512         5244      YES
   122    0xfb                 512         5244      YES
   160    0xfb                 512         6553      YES
```
✅ **[EVIDENCE] V71c carried the REPOINTED gate, so `0xC6444 = 3072` really was read on-car.** The
falsification is **NOT void** — and memory records the **6x cut back to 512 as LOAD-BEARING**, i.e.
raising r26 was **WORSE** and cutting it was part of what made V88 good.
=> **raising r26 is the wrong direction, already flown.** I was one step from re-flying V71c.
⭐ The lineage check earned its keep again: the model's *strike* and the *reason* for the strike can
both be stale while the underlying verdict still stands. **Re-derive the reachability, then trust the
flight result.**

### ⛔ 2. `0xC63D2` — FUN_00036682's FILTER POLE IS A SLOW TRIM, NOT A RATCHET LEVER
`FUN_00036682` is a **backlash/hysteresis band followed by a one-pole low-pass**, writing `gp-0x6b46`
— both an aggregator lane and one of the six lanes EMA'd into ACTUAL:
```
   iVar8   = clamp(residual - ((lower + upper) >> 1), ±512)      backlash band
   iVar14 += ((iVar8*1024 - iVar14) * cal 0xC63D2) >> 10         one-pole IIR
   gp-0x6b46 = iVar14 >> 10
```
```
   0xC63D2 = 6  =>  a = 0.005859  =>  CORNER 0.93 Hz
      f      |H|      lag            raising the pole to cut the lag:
     2.0   0.4236   64.6 deg           cal   6  fc  0.93 Hz  |H| 0.119  lag 81.8 deg
     7.8   0.1191   81.8 deg           cal 128  fc 19.89 Hz  |H| 0.939  lag 18.8 deg
    21.0   0.0445   83.7 deg           cal 512  fc 79.58 Hz  |H| 0.998  lag  2.8 deg
```
⚠ **The lag looks damning (81.8°) but the MAGNITUDE is 0.119** — the lane is attenuated **8x** at the
ratchet. It is a **deliberately slow trim term** (0.93 Hz), separated from the fast dynamics by design.
⛔ **Raising the pole to cut lag would raise this lagging lane's gain 8x at 7.8 Hz — EXACTLY the V162
error** (more gain, no useful phase, into a Q 14–29 resonance). Lowering it changes almost nothing
(lag already asymptotic to 90°, magnitude already small). **Not a lever in either direction.**
⊕ History: `0xC63D2` = 6 on 154 images, 3 on nine (V124/125/127/129/131/133–136) — all inside the
8x-gain/regression cluster, i.e. never a clean test, and 3 makes the lane *less* present, not more.
⊕ **The BACKLASH element itself remains structurally interesting** — a hysteresis nonlinearity is the
textbook small-amplitude ratchet generator — **but it sits BEFORE the low-pass**, so whatever it
injects at 7.8 Hz is attenuated to 12 % before reaching the aggregator. **[OPEN]** its half-width is
`(gp-0x6b44 * uVar7) >> 15` with `gp-0x6b44` a computed RAM cell, not a cal, so there is no direct
calibration lever on the band width. What would close it: identify `gp-0x6b44`'s writer.

### ✅ THE DAMPING LEVERS ARE NOW GENUINELY EXHAUSTED WITHIN THE MODEL'S CONSTRAINTS
```
   r24  (Lever B 0xC6446)   at 6553 = the int16 ceiling in V160         EXHAUSTED
   gp-0x6bd0 (V158)         dose 50, inside the model's own ~43 [30,60] AT PRESCRIPTION
   r26  (0xC6444)           raising it FLEW as V71c and was worse       FALSIFIED
   gp-0x6ad4                stiffness, D path ~1300x too weak, u16-bound STRUCTURALLY ELIMINATED
   gp-0x6b26                -K x acceleration = added inertia            DOES NOT DAMP
   0xC63D2                  slow trim, |H| 0.119 at 7.8 Hz               NOT A LEVER
```
=> **V160 carries both mechanisms that actually damp, each at or at the model's stated limit.**

## ✅✅✅ **WHICH LANES ACTUALLY DAMP AT 7.8 Hz — AND V158 SIZED IN PHYSICAL UNITS**
The `gp-0x6ad4` result generalises into a method: **compute each lane's phase at the symptom's own
frequency before touching it.** Applied to every sensor-fed survivor:
```
   lane          structure                              phase @7.8 Hz     verdict
   gp-0x6ad4     P 99.88 % @0.0 deg (IIR pole = 1024    -1.7 deg          STIFFNESS -- ELIMINATED
                 => PASS-THROUGH), D 0.02 %                                (structural, u16-bound)
   gp-0x6b26     -K x ACCELERATION (gp-0x6c2c is a      +180 deg vs pos   ADDED INERTIA -- lowers f0,
                 first difference of filtered rate)                        does NOT damp
   gp-0x6bbe     MEASURED on-car: 90 ct/(rad/s),        ~0 deg vs RATE    TRUE VISCOUS DAMPING
                 phase ~0 vs rate, DC pedestal 73.6 ct
   gp-0x6bd0     -sign(gp-0x6abe) x f(|rate|, speed)    ~0 deg vs RATE    VISCOUS *if* f is linear
                 = odd-symmetric in rate                                   in |rate| -- V158's target
   r24           K x d(torque)/dt                       +90 deg vs torque DERIVATIVE -- damping,
                 (Lever B 0xC6446)                                         MEASURED by V88
```
⭐ **THE TWO LEVERS THIS KIT HAS ARE THE TWO THAT ACTUALLY DAMP** — V158 on `gp-0x6bd0` and Lever B on
r24. That is not luck; it is why they are the two that measured well.

### ✅ V158 IS GENUINELY VISCOUS, NOT A RELAY — MEASURED FROM ITS OWN BYTES
```
   rate_ct   deg/s    dose    dose/rate        a RELAY would fall 6.5x across this span
      40      8.5      15      0.3750
      99     21.0      50      0.5051          <- the ratchet's operating point
     260     55.2     144      0.5538
```
=> `dose/rate` is **near-CONSTANT (0.375 -> 0.554) across a 6.5x rate span.** ✅ **[EVIDENCE] GATE 2's
rate-proportionality requirement is satisfied empirically, not just by the monotone shape.**

### ⭐ V158 SIZED AGAINST AN INDEPENDENTLY MEASURED ON-CAR QUANTITY
```
   stock / V122 at creep        0.000 ct/(deg/s)     FactorC Y[0] = 0 kills the product
   gp-0x6bbe   (measured)       1.571 ct/(deg/s)     = 90 ct/(rad/s), on-car, independent
   V158 damper (from bytes)     2.733 ct/(deg/s)     local slope at the operating point
   ------------------------------------------------
   TOTAL creep viscous          1.571 -> 4.304       = x2.74
```
✅ **[EVIDENCE] V158 adds 1.74x the viscous damping the car already had at creep**, expressed in the
SAME aggregator counts as a quantity measured on the car. This turns "dose 50" from an abstract
number into a physical damping increment.
⚠ **[BELIEF] what that buys in ζ.** If the firmware's viscous term were the DOMINANT damping source,
ζ would scale with it: **0.017–0.036 -> 0.047–0.099**. If mechanical damping dominates, less. The
split cannot be resolved without a drive, so **treat 2.74x as the firmware-side increment, not a ζ
prediction.**

### ⚠ ONE OPEN DETAIL — SUB-LINEARITY AT THE VERY BOTTOM
`dose ∝ (rate − 12)` inside FactorE's first segment, so `dose/rate = k(1 − 12/rate)` → 0 as rate → 12:
the damping fades in the DEEPEST micro regime. Setting `X[0] = 0` would make it exactly linear through
the origin — **but the golden model argues X[0] = 12 deliberately** (*"a firmware review flagged X0 < 30
with Y1 > 300 as the zone it would not fly without telemetry; 12 is the TOP of its own 6–12 band"*).
**NOT changed.** Recorded as a known, deliberate limitation.
⊕ Headroom exists but is NOT taken: the build-time rule `(FactorC x FactorE[3])>>10 ≤ 512` reads **388**,
and FactorE `Y=[0,700,700,927]` would give dose 65. **The model's own requirement is ~43 [30,60] and
V158's 50 sits inside it** — exceeding a stated requirement without cause is what produced six
superseded builds this session. **Left at 50.**

## ⛔⛔ **V162/V163 SUPERSEDED — `gp-0x6ad4` IS STIFFNESS, NOT DAMPING. STRUCTURALLY ELIMINATED AT 6–9 Hz.**
Built, then killed by its own GATE 2 before it ever flew. **The rationale was FALSE.**

### ✅ THE PID'S TRANSFER FUNCTION, COMPUTED FROM THE BYTES
Structure (model, `FUN_0003a382`): `err = clamp(gp-0x4f60 - clamp(gp-0x6ad6), ±0x2800)`, then
`P: IIR((err*Kp)>>10 * 0x20, pole tp+0x7450)` · `I: ((Ki*err)>>10)+state` · `D: ((err-state)*Kd)>>10`,
summed as `gp-0x6ad4 = (((I+D+P)>>5) * LERP_out)>>10 * polarity`.
Gains at the ratchet's own operating point `gp-0x6ac0 = 99`, all three LERPs flat there:
```
   D  0xC6B1E  Y=256   => Kd = 0.2500
   I  0xC6B0A  Y=98    => Ki = 0.0957
   P  0xC6ADE  Y=2048  => Kp = 2.0, then x32 = 64.0
   🛑 IIR pole 0xC6450 = 1024 => a = 1.000000 => THE "IIR" IS A PASS-THROUGH. No smoothing at all.
```
```
   at 7.8 Hz, fs = 1 kHz:        |H|        phase      share of |sum|
       P                        64.000       0.0 deg      99.88 %
       I                         1.953     -88.6 deg       3.05 %
       D                         0.012     +88.6 deg       0.02 %
       SUM                      64.08       -1.7 deg
```
✅ **[EVIDENCE] `gp-0x6ad4` IS A NEARLY PURE PROPORTIONAL TERM AT THE RATCHET FREQUENCY** — phase
**−1.7°**, derivative contributing **0.02 %**. A 0°-phase term is **STIFFNESS, NOT DAMPING**.

### ⛔ WHY THAT KILLS THE BUILD
Raising the ceiling raises **loop gain with no phase lead** into a resonance the kit has measured at
**Q 14–29 (ζ 0.017–0.036)**. Raising proportional gain around a lightly-damped resonant plant
**reduces stability margin and increases resonant peaking** ⇒ V162/V163 would most likely make the
ratchet **WORSE**. Both are **SUPERSEDED**, artifacts renamed `SUPERSEDED-DO-NOT-FLASH-PSTIFFNESS-*`.

### ⭐ AND THE LANE IS ELIMINATED ON STRUCTURE, NOT ON A NULL
For D to matter at 7.8 Hz it needs `Kd · 2sin(ω/2) ≈ |P|`; with `2sin(ω/2) = 0.049` that demands
`Kd ≈ 1306`, i.e. a Q10 Y of ~1.34 MILLION. **The cell is a u16 — max 65535 gives Kd = 64, |D| = 3.14
against P's 64.0, a net phase of only +1.06°.** => **the derivative path is ~1300x too weak BY DESIGN
and the register width cannot close the gap.**
✅ **`gp-0x6ad4` IS STRUCTURALLY INCAPABLE OF DAMPING AT 6–9 Hz.** This properly closes one of the
model's five sensor-fed survivors — the model was right that V56's ~21 Hz null did not settle it, but
**structure settles it now.** Survivors remaining: **{r24/r26, gp-0x6b26, gp-0x6bbe, V89 plant-model}**.

### ⚠ THE MISREADING TO NOT REPEAT
The model calls it *"the most reachable **AUTHORITY** of any gated lane"* — **authority, not damping.**
It never claimed the lane damps at 6–9 Hz; it said the lane had never been **scored** there. I read
"resonance PID" and supplied "therefore it damps." ⭐ **A LANE'S NAME IS NOT ITS TRANSFER FUNCTION.**
Compute magnitude AND phase at the symptom's own frequency **before** building — which is exactly what
CLAUDE.md's GATE 2 requires, and it took ~20 lines of Python once the gains were located.
⊕ **V160/V161/V158 are UNAFFECTED** — independent lanes, and Lever B's rationale is a *measured*
single-variable result (6–9 Hz 0.859, 15–22 Hz 0.549, LF null), not a structural inference.

## ✅✅✅ **V162 / V163 BUILT — THE RESONANCE PID GETS ITS AUTHORITY BACK AT CREEP**
`0xC67C4` **1280 -> 512**, ONE HALFWORD, a **VIRGIN CELL**. 55/55 assertions each, CRC 50/50.
```
   V162  base V122  SINGLE VARIABLE   image 423711bf0f10b21f7ddce3e21d35cf390d93054c25ebed1075eb0572cb02d299
   V163  base V160  STACKED best-shot image 9487dc15f68a3a876ec70509d01167c9db9c8e328e9c003fa85dff94388ce0d6
```
### ⭐ THE GOLDEN MODEL NAMED THIS LEVER, AND IT IS AIMED AT THE RATCHET SPECIFICALLY
The model's elimination is explicit — *"for 52–70 % of the return the LKAS lane is a DC CONSTANT, yet
the 6–9 Hz |tq| envelope is unchanged … A constant cannot carry 7.8 Hz => **THE RINGING ENTERS THROUGH
A SENSOR-FED LANE, NOT THE COMMAND LANE.** Excludes every command-side lever and leaves {r24/r26,
gp-0x6ad4, gp-0x6b26, gp-0x6bbe, the V89 plant-model path}."* — and of those survivors it singles out:
> *"LIVE `gp-0x6ad4` resonance PID — **the most reachable authority of any gated lane HERE** … 🛑 V56's
> mute of this lane was scored at ~21 Hz — **the lane has NEVER been scored at 6–9 Hz, so it is OPEN,
> not eliminated.**"*
⚠ **THIS OVERTURNS A MEMORY.** `accord-v56-flashed-mute-null-and-costs-damping` records
`gp-0x6ad4`/`FUN_0003a382` as **eliminated**. An elimination scored at **21 Hz does not eliminate a
6–9 Hz role**, and the ratchet is 6–9 Hz. The model is the authoritative reference and it addresses
this directly. **Treat the memory's "eliminated" as scoped to ~21 Hz.**

### ✅ THE ARITHMETIC, READ FROM THE BYTES
`0xC67BE` = `(0, 3)` knot-count header; X@`0xC67C2`, Y@`0xC67C8`; axis = voted speed `gp-0x6a5e` @64 ct/km/h.
```
   stock  X = [128, 1280, 3200] = [2, 20, 50] km/h     Y = [0, 1024, 1024]

     speed     stock -> new     ratio     note
      2 km/h       0 ->    0    --        parking protection INTACT (X[0] untouched)
      3 km/h      56 ->  170    x3.00
      5 km/h     170 ->  512    x3.00     <- the ratchet's own band
      8 km/h     341 -> 1024    x3.00
     12 km/h     568 -> 1024    x1.80
     20 km/h    1024 -> 1024    --        UNCHANGED; edit confined to the creep band
```
=> **the lane whose job is to damp resonance is throttled to ~1/6 of its authority exactly where the
ratchet lives.** ✅ The model's own quoted 164–341 for the 4.9–8.0 km/h ratchet episodes **reproduces
from these bytes exactly** (170 at 5 km/h, 341 at 8 km/h) — two independent derivations agreeing.

### ✅ WHY THIS DIRECTION IS THE SAFE ONE
**[EVIDENCE]** It **RELEASES** authority and never removes any — the ceiling is ≥ stock at every speed.
**[EVIDENCE]** `X[0]=128` UNTOUCHED ⇒ at/below 2 km/h the ceiling stays **exactly 0**; Honda's
standstill/parking protection is byte-for-byte intact. **[EVIDENCE]** ≥20 km/h **nothing changes**.
**[EVIDENCE]** **Y is UNTOUCHED** — the ceiling's VALUE stays Honda's own 1024; only the SPEED at which
it is reached moves. **Honda already runs this lane at FULL authority above 20 km/h and the car does
not ratchet there**, so this moves creep TOWARD a known-good configuration rather than into new
territory. **[EVIDENCE]** the axis is **VEHICLE SPEED** — seconds-scale ⇒ **cannot modulate at 6–9 Hz**,
so the parametric-pump failure mode governing every rate-axis edit does not apply.
**[EVIDENCE]** `0xC67C4` is **VIRGIN**: `(128, 1280, 0)` on **all 161 build images** ⇒ no interaction
with any historical edit. **[EVIDENCE]** X stays strictly ascending, no collapsed knot (a zero-width
LERP segment divides by zero — asserted).

### ⚠ THE ONE REAL RISK
**[BELIEF]** that `gp-0x6ad4`'s **PHASE** is favourable at 6–9 Hz. It is a resonance controller, but its
design target may be the ~21 Hz mode, and **a controller phased for 21 Hz can have the wrong phase at
7.8 Hz — in which case MORE authority makes the ratchet WORSE.** This cannot be settled statically;
the lane has never been scored at 6–9 Hz, which is exactly why the model calls it OPEN.
⊕ **Mitigation**: the change is confined to 2–20 km/h and reverts to stock above, so any adverse effect
is **bounded to the creep band** and is felt immediately at low speed, not discovered at highway speed.
⊕ If worse, the diagnosis is unambiguous and the revert is one halfword; `X[1] = 768` (12 km/h) gives a
**2x** rather than 3x release.

## ✅✅ **`0xCC914` IS LIVE — IT IS A BREAKPOINT VECTOR, AND THE GOLDEN MODEL'S MAP WAS SHORT ONE ARRAY**

### ⛔ THE "DEAD TABLE" CLAIM IS FULLY RETRACTED
`0xCC914` is read at **`0x34936`**: `ld.w 0xd914[r16], r15` with **`r16 = tp + mode*4`** — the identical
idiom to `FUN_0003ad74`'s 4th gain_B array at `0x3ADC2` (`tp+0xD214`). Decoder validated against that
known-live cell before being trusted.
```
   disp23 = (sext(hw3) << 7) | ((hw2 >> 4) & 0x7F)          reg1 = hw1 & 0x1F
   0x3ADC2  90 07 49 79 a4 01  ->  0x01a4<<7 | 0x14 = 0xD214   base r16   (KNOWN LIVE, validates)
   0x34936                     ->                    0xD914   base r16   (0xCC914)
```
⭐ **WHY BOTH EARLIER SCANS MISSED IT — THE BASE REGISTER IS A *COMPUTED* REGISTER.** A `mov imm32`
literal scan misses it (the other five arrays ARE literals, this one is not) **and** a tp-relative scan
misses it (`reg1` is `r16`, not `tp`). This is the recorded *"operand-text search cannot see
register-indirect writes at all"* trap in a new form: **scanning by base-register identity is
structurally incomplete.** Three encoding traps have now bitten in one session — `hw2 = (disp|1)`,
`disp > 0x7FFF` cannot be disp16, and now a computed base register.

### ✅ WHAT IT ACTUALLY IS — THE SPEED BREAKPOINT VECTOR OF A SECOND BLENDED FAMILY
`FUN_000348e0` is structurally the SAME architecture as gain_B's blender:
```
   curves[1..5] = 0xC92F4[m], 0xC93DC[m], 0xC94C4[m], 0xC95AC[m], 0xC9694[m]      (10-knot each)
   bp           = 0xCC914[m]                    <- FIVE SPEED BREAKPOINTS, record+0..+8
   speed        = gp-0x6a5e (voted vehicle speed)
   i = walk(bp, speed);  frac = (speed - bp[i-1]) / (bp[i] - bp[i-1])
   gp-0x6394[j] = lerp(curves[i][j+1],   curves[i+1][j+1],   frac)      runtime X row
   gp-0x63a8[j] = lerp(curves[i][j+0xb], curves[i+1][j+0xb], frac)      runtime Y row
```
```
   0xCC914[24/26/27] -> 0xD6B7C / 0xD7B70 / 0xD7B7C
   bp = [0, 512, 2560, 5120, 8960] counts = [0, 8, 40, 80, 140] km/h   (identical on all three modes)
```
✅ record layout obeys the **knot-count header** invariant: `hdr@+0 = 10`, `X@+2..`, `Y@+0x16..`.

### ⚠ THE MODEL'S *"flat zero at creep"* IS ONLY TRUE AT A STANDSTILL
Curve 1 (0 km/h, `0xD74D0`) has **all-zero Y**, so across 0–8 km/h the whole term is scaled by
`frac = speed/512`:
```
   2 km/h -> 25.0 %      5 km/h -> 62.5 %      8 km/h -> 100 %      of curve 2
   mode 26 curve 2 (0xD7554)  X=[0,34,101,245,499,846,1888,2966,3656,4150]
                              Y=[0,677,1052,1391,1732,1911,2204,2321,2361,2355]
```
=> **a LINEAR RAMP through the entire creep band, not a dead zone.** The golden model has been
corrected in place (`eps_chain_lanes.py`), and its **VERIFICATION CONTRACT RE-RUN: 87 symbols,
stdout 2512 bytes, sha256 `740f4bcd…` EXACT.**
⚠ **[BELIEF, NOT A LEVER YET]** a steep near-centre slope (Y 0->677 over X 0->34) times a
speed-proportional creep ramp is *suggestive* for a creep-band feel symptom, but the axis is
`gp-0x6a10` ABSOLUTE steering angle, which the kit has already REFUTED as a frequency-selective
lever. **Not proposed as a build.** What would close it: identify the consumers of `gp-0x6394` /
`gp-0x63a8` and establish whether the term is inside the 6–9 Hz loop at all.

## ✅✅✅ **V160 BUILT — LEVER B TO ITS INT16 CEILING. THE NEW LEAD BUILD.**
`0xC6446` **5244 -> 6553**, ONE HALFWORD, base = V158. 51/51 assertions, CRC 50/50, **6 differing bytes
= 2 payload + 4 CRC, ZERO unattributed.**
```
   image  5277005735a5b2e42bf38860a7a82d1bed14126207cb376e16d0cf137f921594
   rwd    d512d8142d9f8bf9ff76919d8beb092cea8279d15b58d6535614374d48ea3096
```
### ⭐ WHY THIS LEVER — IT IS THE ONLY ONE MEASURED TO HELP BOTH SYMPTOMS AT ONCE
Lever B is the **r24 derivative-feedback gain used WHEN LKAS IS ENGAGED**:
```
   gain_q10 = <speed x rate LERP surface>
   elif assist_gate_683c != 0:   gain_q10 = 0xC6446      # stock 512 -> Lever B 5244
```
V88 vs V87, **single-variable** (5 changed bytes), speed-matched 2-4 m/s, engaged, unclipped,
episode-bootstrapped:
```
   0.5-3 Hz   1.192 [0.780, 1.812]  NULL   <- peak effective LKAS command, UNTOUCHED
   6-9 Hz     0.859                        <- the ratchet band
   9-12 Hz    0.604 [0.465, 0.943]
   15-22 Hz   0.549 [0.407, 0.844]         <- grind #1's band
```
✅ *"MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING = LESS HF EVERYWHERE, at zero LF cost."*
=> **the only lever in this kit measured to cut BOTH the ratchet band AND the grind band while
leaving the LKAS command statistically untouched** — exactly the operator's standing requirement.
V88 is also the route that flew with **"grinding FIXED"**.

### ⭐ WHY A THIRD DOSE, AND WHY EXACTLY 6553
Across **all 159 build images** `0xC6446` has taken **exactly THREE values**: 512 (stock, 85 builds),
5244 (73 builds, flown), 1024 (V149 only, superseded). **The dose-response has TWO points and the
flown step was 10.24x.** A third has never been tried.
```
   (RATE_CLAMP 5120 x 6553) >> 10 = 32765  <= 32767   fits
   (RATE_CLAMP 5120 x 6554) >> 10 = 32770             OVERFLOWS
```
=> **6553 is the EXACT int16 ceiling**, a 1.2496x increment landing on a hard arithmetic boundary
rather than a guess — small beside the 10.24x step already flown fault-free.

### ✅ WHY IT CANNOT COST LKAS AUTHORITY
**[EVIDENCE]** r24's own rail is +-8192, four 16-bit immediates at `0x3AC42-0x3AC54`, and V160 leaves
all 24 bytes **BYTE-IDENTICAL**. The model's warning is specific: raising the **RAIL** lets a
derivative lane eat the +-10240 aggregator headroom the LKAS command needs — *"the one change in this
path that could REDUCE peak effective LKAS steering."* **We raise the GAIN and leave the RAIL alone,
so that failure mode is STRUCTURALLY UNREACHABLE.** (+) measured: `gp-0x6b94` never comes within 20 %
of its +-10240 clip; and 0.5-3 Hz was NULL across the 10.24x step.
**[EVIDENCE]** `0xC6446` has **exactly ONE reader** — `ld.hu 0x7446[tp], r10` at `0x3AC08` — and
**ZERO writers**, confirmed two ways (a tp scan handling the `hw2=(disp|1)` encoding, which also
reproduced the model's `0xC6440`->`0x3AC12` and `0xC6442`->`0x3ABFE`; and the model's own record).

### ⚠ WHAT IS NOT ESTABLISHED
**[BELIEF]** that the dose-response stays monotone beyond 5244 — **only two points exist**, and V62's
lesson is explicit: *"2x is approximately the OPTIMUM, not a point on a ramp."* 5244 may already be at
or past optimum, so **V160 is a DOSE PROBE as much as a fix.** Mitigation: the step is 1.25x, not 2x.
**[NOTE]** r24 rails at `|col_torque_rate| > 1280` (was 1599); normal driving is 123-839 counts, so it
stays unrailed. **[NOTE]** V160 STACKS on V158's damper — two independent mechanisms, both adding
creep-band damping. If the drive is ambiguous, **V158 alone** and **V151** remain single-lever fallbacks.

### ✅✅ V160's PRECONDITION IS VERIFIED — LEVER B IS ACTUALLY REACHABLE
`0xC6446` is read **only** when `lp != 0`, and on a stock gate byte `lp` derives from `gp-0x683c`,
which has **ZERO writers image-wide** — so on stock that load NEVER EXECUTES and Honda's own 512 in
that cell is dead code. The V67 repoint `0x3AA96 c5 -> fb` rewires it to `gp-0x6806`:
```
   build   0x3AA96              0xC6446   Lever B reachable?
   stock   0xc5 (stock)             512   NO  -- gp-0x683c has 0 writers
   V122    0xfb (repointed)        5244   YES -- gp-0x6806
   V158    0xfb (repointed)        5244   YES
   V160    0xfb (repointed)        6553   YES
```
✅ **[EVIDENCE] the repoint is present on the V160 base, so V160 is NOT inert.**
✅ **[EVIDENCE] the gate is VALIDATED ON-CAR**: `gp-0x6806 != 0` agrees with `latActive` on
**99.90 % (route 29) / 99.94 % (route 28)**, does not drop out during steady engaged holding, and
toggles **three orders of magnitude below** the 21/45 Hz modes ⇒ it cannot parametrically pump.
⭐ **6553 IS CONFIRMED TWICE, INDEPENDENTLY**: it is the int16 overflow bound I derived from
`(5120 x g) >> 10 <= 32767`, **and** it is the ceiling the golden model already recorded for this
cell class (*"1 reader / 0 writers, no float mirror, same CRC block #48 as 0xC6446, ceiling <= 6553"*).

## ⛔⛔ **RETRACTION — "`0xCC214`/`0xCC914` ARE DEAD TABLES" IS WRONG**
`0xCC214` is **LIVE**: it is the **fourth pointer array of gain_B (r24)**, the 100 km/h speed-blend
record set, reached as **`tp+0xD214`** and hard-coded in the instruction stream — which is exactly why
it carries no `mov imm32` literal. My null scanned only `mov imm32` literals and 16-bit
`movhi`+`movea` pairs and **was blind to the long tp-relative form**, the encoding `CLAUDE.md` warns
about. ⚠ **`0xCC914` is therefore UNRESOLVED, not dead** — the question is OPEN again.
⭐ **A NULL IS ONLY AS GOOD AS ITS SCAN'S ENCODING COVERAGE.** Two encoding traps bit in one session:
the `hw2 = (disp | 1)` form (a scan for `hw2 == disp` returns **zero** readers for a cell that has
one), and `disp > 0x7FFF` cannot be a disp16 at all. **Validate any scanner against a cell whose
answer is already known BEFORE trusting its null** — doing so is what caught both.

## ✅✅ **THE `(0, N)` KNOT-COUNT HEADER — AND THE LANES B/C ANOMALY IS CLOSED**

### ⭐ EVERY CAL LERP IS ANCHORED BY A 2-HALFWORD `(0, N)` HEADER, N = THE KNOT COUNT
```
   layout:   [0][N]  X[0]..X[N-1]   Y[0]..Y[N-1]        (inline tp-relative cals)
             [N]     X[0]..X[N-1]   Y[0]..Y[N-1]        (pointer-table records, hdr at +0)
   validated 0xC6000-0xC7000: 54 WELL-FORMED (header + N strictly ascending X) vs 8 false positives
```
✅ **[EVIDENCE] this is the general layout, not a pattern-match on one table.** It gives a
**self-validating anchor**: a correct read must have `hdr == len(X)` with **X strictly ascending**.
⭐ **PUT THIS CHECK IN EVERY BUILD SCRIPT.** It catches a wrong address, a wrong knot count and a wrong
stride *in one assertion* — all three of the failure modes that cost this session builds.

### ✅ THE "LANES B/C NON-ASCENDING X" ANOMALY IS RESOLVED — IT WAS AN OFF-BY-2-HALFWORD READ
Anchored on the header, all three PID lanes are **well-formed**:
```
   lane A  0xC6B1E   X=[  0, 300, 2000, 4000]   Y=[ 256,  256,  225,  153]
   lane B  0xC6B0A   X=[  0, 400, 1500, 3000]   Y=[  98,   98,   98,   98]     FLAT
   lane C  0xC6ADE   X=[ 50, 400, 1500, 3000]   Y=[2048, 2048, 2048, 2048]     FLAT
```
(V159 reported `[256,256,0,8]` and `[717,0,0,5]` — those are a Y-tail plus the next `(0,N)` header.)

### ⛔ V159's MECHANISM DOES NOT EXIST — THE THREAD IS CLOSED ON EVIDENCE, NOT JUST ON ITS ADDRESS BUG
V159 was built on *"an 18.2 % parametric modulation of K_p at 2f, at the symptom's own operating point"*,
from a claimed `X=[96,104,608,704] Y=[704,832,832,832]`. **That table is not lane A.** Lane A's real
schedule is `X=[0,300,2000,4000] Y=[256,256,225,153]`, and the measured operating point
**`gp-0x6ac0` = 99 [94,113] lies in segment 0, where Y is FLAT at 256.**
=> **there is NO gain swing at the operating point**, at 2f or any other frequency. Lanes B and C are
flat constants across their whole axes.
✅ **THE LANE-GAIN PARAMETRIC-PUMP HYPOTHESIS IS NOW CLOSED BY DIRECT BYTE EVIDENCE**, not merely
"flat at the operating point" — a second, independent derivation agreeing with how V158's shared-axis
GATE 2 was closed.
⊕ What V159 would actually have done: `0xC6728` is `Y[3]` of an **unrelated 8-knot** table at `0xC6712`
(`X=[64,65,67,73,80,88,96,104]`, `Y=[608,704,704,832,832,832,832,832]`) — it would have set that Y[3]
832 -> 704. **The supersede was correct**, and the blast radius is now known rather than guessed.

## ✅✅ **V158 VERIFIED FROM THE SHIPPED BYTES — AND THE POINTER-TABLE FAMILY IS CLOSED**

### ✅ THE DAMPER FUNCTION IS `FUN_00034350`, AND IT CARRIES **FIVE** TABLES, NOT FOUR
Decompiled 2026-08-28. The cascade the golden model describes is confirmed instruction-by-instruction,
and the **fifth table is the OUTPUT CEILING** — previously known only from the model's prose.
```
   L1 torque  0xC9CCC  4-knot   X[0]@+2  Y[0]@+0xA     axis |torque|      flat unity 1024
   L2 speed   0xC9E9C  4-knot   X[0]@+2  Y[0]@+0xA     axis gp-0x6a5e     Y[0]=0  <- creep dead zone
   L3 angle   0xC9DB4  5-knot   X[0]@+2  Y[0]@+0xC     axis gp-0x6a10     flat unity 1024
   L4 rate    0xC9F84  4-knot   X[0]@+2  Y[0]@+0xA     axis gp-0x6ac0     Y[0]=0  <- rate dead zone
   ceiling    0xC77A0  2-knot   X[0]@+2  Y[0]@+6       axis gp-0x6ac2     X=[300,800] Y=[512,1024]
```
⭐ **THE RECORD'S FIRST HALFWORD IS THE KNOT COUNT** (hdr=2 on the ceiling, 4 on L1/L2/L4, 5 on L3).
That is a **self-validating invariant** — any correct record read must have `hdr == len(X)` and X strictly
ascending. **It would have caught V159's off-by-0x400 instantly**, and it belongs in every build script.
✅ The ceiling's 512 floor is now **read from the image**, not taken from prose: `gp-0x6ac2` is a
sign-gated kickback detector (0 in same-sign driving) => the LERP clamps flat to Y[0] = **512**, and the
`>= 0x32c9` bypass lands on `0xC6158` = **512** too. Both paths agree.

### ✅ V158 RE-VERIFIED BY EXACT INTEGER ARITHMETIC ON ITS OWN SHIPPED IMAGE
```
   5 km/h, rate  60 ct : FactorC=429 FactorE= 66 -> dose  27      (stock 0)
   5 km/h, rate  99 ct : FactorC=429 FactorE=120 -> dose  50      (stock 0)   <- the operating point
   5 km/h, rate 200 ct : FactorC=429 FactorE=261 -> dose 109      (stock 0)
   build-time rule (FactorC x FactorE[3])>>10 <= 512 :  m26 388 PASS   m27 385 PASS
```
✅ **[EVIDENCE] dose 50 at the measured operating point** — the model's design target, and the exact
value V74 flew with **67.4 % engaged-creep liveness and 0 frames reaching the ceiling**.
✅ **[EVIDENCE] GENUINELY RATE-PROPORTIONAL, NOT A RELAY**: 27 -> 50 -> 109 across 60/99/200 counts.
That is the substantive GATE 2 test and V158 passes it.

### ⚠ CORRECTION TO THIS SESSION'S OWN RECORD — V158's FactorC ARM IS **NOT** MONOTONE
V158 leaves FactorC `Y = [429, 234, 429, 908]` (m26) / `[426, 233, 426, 875]` (m27): it **dips** between
35 and 60 km/h. I earlier certified V158 as "MONOTONE"; **that wording was wrong.**
✅ **The build is still correct.** The model prescribes `FactorC Y[0] := Y[2]` **explicitly**, knowing it
exceeds the monotone limit (it also records that `Y[0] := Y[1]` is *"the largest monotone lift of Y[0]
alone"*). The shape law exists to stop **FactorE** being flattened across the **rate** axis into a
bang-bang relay — a limit-cycle generator at a lightly-damped resonance. FactorC is **speed**-indexed and
*"costs NO rate-proportionality"*; vehicle speed varies over seconds and cannot pump a 7.8 Hz ratchet.
=> **the gate that matters is on FactorE, and V158's FactorE is monotone and rate-proportional.**
⭐ Lesson: **name the AXIS when applying a shape law.** "Monotone" is load-bearing on a fast axis and
merely cosmetic on a slow one; asserting it unqualified nearly cost the lead build.

### ✅ THE 37 POINTER TABLES ARE CLOSED — AND TWO ARE DEAD
35 of 37 are loaded by **exactly one `mov imm32` literal** in code, each now located. **`0xCC214` and
`0xCC914` have NO reference anywhere in the image** — no literal, no `movhi`+`movea` pair.
⛔ **`0xCC914` IS A DEAD TABLE.** Its double dead zone (`Y=[0,0,512,2560]`, zero below ~40 km/h) looked
like a creep lever and **is not one — nothing reads it.**
⚠ **The "single reference `movea 0xC914` at `0x3938E`" was a FALSE POSITIVE**: the instruction is
`movea 0xC914, r4, r30` with **r1 = r4 = gp**, i.e. `gp - 0x36EC` (a RAM cell that appears throughout
`FUN_000389ec`), not a table base. A raw byte scan for an immediate cannot tell a **base register** from
a **`movhi` partner**; the decompile settled it in one call. **Decompile first — again.**

## ✅✅ **V158 ADDRESS-VERIFIED INDEPENDENTLY — AND WHY IT WAS IMMUNE TO V159's ERROR**
After the off-by-0x400 that killed V159, the lead build's addresses were re-derived **independently
and explicitly**, walking the pointer tables rather than trusting the builder.
```
   FactorC (L2 speed), pointer table 0xC9E9C -> records 0xD77BC / 0xD77D0 / 0xD77E4   (m25/26/27)
       m26 base 0xD77D0  X[0]@0xD77D2  Y[0]@0xD77DA  Y[1]@0xD77DC
       m27 base 0xD77E4  X[0]@0xD77E6  Y[0]@0xD77EE  Y[1]@0xD77F0
   FactorE (L4 rate),  pointer table 0xC9F84 -> records 0xD77F8 / 0xD780C / 0xD7820
       m26 base 0xD780C  X[0]@0xD780E  Y[0]@0xD7816  Y[1]@0xD7818
       m27 base 0xD7820  X[0]@0xD7822  Y[0]@0xD782A  Y[1]@0xD782C

   V158's six edits, each against its RE-DERIVED role:
       0xD77DA  FactorC m26 Y[0]    0 -> 429      0xD780E  FactorE m26 X[0]   60 -> 12
       0xD77EE  FactorC m27 Y[0]    0 -> 426      0xD7822  FactorE m27 X[0]   60 -> 12
                                                  0xD7818  FactorE m26 Y[1]  140 -> 539
                                                  0xD782C  FactorE m27 Y[1]  140 -> 539
   image diff V122 -> V158: 14 bytes = 10 payload + 4 CRC (0xD7FFC..0xD7FFF).  ZERO unattributed.
```
✅ **[EVIDENCE] all six cells match their independently re-derived roles exactly.**

### ⭐ THE STRUCTURAL REASON V158 COULD NOT SUFFER V159's BUG
```
   V159's addresses   computed as  tp + offset      -> one wrong digit = a wrong cell, silently
   V158's addresses   READ as ABSOLUTE POINTERS out of the image, then walked by a known layout
```
=> **no offset was ever added for V158**, so the **off-by-0x400 / off-by-0x1000 class cannot occur**
there. The pointer table *is* the ground truth, and a wrong pointer would land outside the image and
be caught by the `0x10000 < p < 0x100000` filter.
⭐ **RULE, generalised: PREFER POINTER-DERIVED ADDRESSES OVER OFFSET-DERIVED ONES.** When a table is
reachable through an in-image pointer array, walk the array — it is self-validating. Reserve
`tp + offset` arithmetic for scalars that have no pointer, and when you must use it, **add the offset
to `tp` explicitly and print BOTH** (the check that finally caught V159).
⊕ This also explains, retrospectively, why the **damper** work survived the audit while the
**lane-gain** work did not: the damper's records are pointer-reachable; the PID's lane gains are not.

### ✅ V158's STANDING
```
   addresses      VERIFIED independently, zero unattributed bytes
   dose           50 at the model's MEASURED operating point, inside its own [30,60] requirement
   shape          MONOTONE; dead zone opened by the AXIS, not by flattening Y[0]
   ceiling        9.8 % of the 512 creep ceiling -- a 10.2x margin to V80's bang-bang
   RULE 7         engaged modes 26/27, read from V106B, not assumed
   shared-axis    the PID schedule is FLAT at the operating point => the coupling does not bite
```
=> **every gate the golden model raised for this lever is now addressed.** V158 is the recommended
build.

## 🛑🛑🛑 **V159 SUPERSEDED — AN OFF-BY-0x400 ADDRESS ERROR, AND THE LANE GAINS ARE FLAT**
**V159 edits an unrelated cal on a false premise. It is superseded and must never be flown.**
```
   tp = 0xBF000
   tp + 0x7B1E  =  0xC6B1E     <- the REAL K_p X table
   V159 edited     0xC6728  =  tp + 0x7728   <- AN UNRELATED CAL
```
🛑 **I confused `0x7B1E` with `0x771E`** — an **off-by-0x400** address error, the same family as
the off-by-0x1000 trap `CLAUDE.md` records **six** times.

### 🛑 THE REAL TABLES KILL THE FINDING OUTRIGHT
```
   K_p  tp+0x7b1e = 0xC6B1E   X=[  0, 300, 2000, 4000]   Y=[ 256,  256,  225,  153]
   K_i  tp+0x7b0a = 0xC6B0A   X=[  0, 400, 1500, 3000]   Y=[  98,   98,   98,   98]
   K_d  tp+0x7ade = 0xC6ADE   X=[ 50, 400, 1500, 3000]   Y=[2048, 2048, 2048, 2048]
```
⇒ the operating point **`gp-0x6ac0` = 99 [94, 113]** lies in **segment 0 of every one of them**:
K_p is **256 -> 256 (FLAT)** from 0 to 300; **K_i and K_d are FLAT at every knot.**
⇒ **[EVIDENCE] ALL THREE PID LANE GAINS ARE FLAT AT THE OPERATING POINT. There is NO parametric
gain modulation there — not 18 %, not any.**
⇒ **the whole "parametric pump at lane gain A" line is VOID**, and so is V159.
✅ **The hypothesis is now CLOSED properly**, on the correct tables: the lane gains cannot be the
source of a 2f parametric pump, because they do not vary at the rate the symptom lives at.

### 🛑🛑 THE PROCESS FAILURE IS WORSE THAN THE ARITHMETIC
```
   1. computed tp+0x7b1e wrong (0xC671E)                  -- a digit error
   2. the garbage there happened to LOOK like a 4-knot table for lane A
   3. lanes B/C read NON-ASCENDING X                      -- the CORRECT symptom of a wrong base
   4. I RETRACTED -- right instinct, WRONG reason (blamed the LAYOUT, not the ADDRESS)
   5. I "verified" against the decompile -- and RE-DERIVED THE SAME WRONG ADDRESS
   6. UN-retracted, and built V159 on an unrelated cell
```
🛑 **The non-ascending X was the signal, and I read it twice and misdiagnosed it twice.**
⭐ **RULE: when a neighbouring record of the same family decodes as nonsense, suspect the BASE
ADDRESS before the LAYOUT.** A wrong base makes *every* record in the family garbage; a wrong layout
usually breaks them all *the same way*. **Lane A "working" while B and C were garbage was itself the
tell** — a correct base makes all three work.
⭐ **RULE: re-deriving an address the same way is not verification.** Step 5 felt like a check and
was not one. **Verify a tp offset by ADDING IT TO tp EXPLICITLY and printing both**, which is what
finally caught this.

### ✅ WHAT THIS COSTS AND WHAT IT LEAVES
⊕ **Nothing reached the car.** V159 was built and pushed but never flown.
⊕ **The lane-gain hypothesis is now closed on correct data** — a real result, not just a retraction.
🛑 **V158's shared-axis GATE 2 is now CLOSER to closable**: the model demanded FactorE edits be
sized against the PID's schedule on the same axis, and **that schedule is FLAT at the operating
point**, so **the coupling the model worried about does not bite at 99 counts.** That is the sizing
it asked for — done, on the right tables.
⇒ **V158 becomes the lead build again**, with its shared-axis gate substantially addressed.

