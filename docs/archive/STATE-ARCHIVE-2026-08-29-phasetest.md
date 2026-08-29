# STATE archive — sections superseded during the phase-test iteration

A RECORD, NOT AN INSTRUCTION.

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

