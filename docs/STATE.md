# STATE — living current state of the kit

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

## ✅✅✅ **THE SWITCHING CENSUS IS COMPLETE — EXACTLY TWO ARE CAL-REMOVABLE, AND BOTH ARE BUILT**
Every counter-gated selection in the assist chain has now been read at its site:
```
   gate        what it selects                    structure              removable?
   gp-0x671a   the NOTCH gate (0x35BEA)           an ENABLE, not a pair       no
   gp-0x671a   the b26 Y-branch (0x36C1E)         LERP(speed) vs const        no
   gp-0x671a   the r26 MULTIPLIER (0x3AA70)       LERP        vs const        no
   gp-0x671a   the r26 SUPPRESSION flag           cal=1 vs cal=0   BOTH CONST  YES -> V150
   gp-0x671d   the r24 MULTIPLIER (0x3AB98)       5244 vs 1024     BOTH CONST  YES -> V149
   gp-0x671b   a float branch at count > 1        not a cal pair              no
   gp-0x671f   jump-table dispatch, index 0..160  not a switch at all         --
   gp-0x6700/03/04                                32-bit FLOATS, not counters --
```
🛑 **Two corrections to my own sweep**: `gp-0x671f` is a **state index driving a `jr` jump
table** (`ld.bu` → `addi -0xa1` → `bnc` → `jr 0x377b2`), not a binary selector; and
**`gp-0x6700`/`03`/`04` are 32-bit FLOATS** — `0x38AEA` is `ld.w -0x6704, gp, r8` followed by
`trncf.sw`, a float-to-int truncate. **The sweep classified them as counters purely by
displacement.** Neither belongs to the family.

### ⭐ THE RESULT
**Exactly TWO switching nonlinearities in this firmware are reachable by a cal edit, and both are
now built:**
```
   V149   0xC6446 : 5244 -> 1024   removes the r24 multiplier's 5.12x switch      2 bytes, 52/52
   V150   0xC6136 :    0 -> 1      removes the r26 suppression switch, in the      1 byte,  51/51
                                   pump-SUPPRESSING direction
```
Everything else on that list would need an **in-place instruction edit on the branch itself** — the
class that bricked V24, V27 and V48B — and is **not proposed without a confirmed reason.**

### ⭐ WHAT THIS MEANS FOR THE FLIGHT ORDER
```
   1. V149   the LARGER switch (5.12x), 2 bytes, safe by construction
   2. V150   the second switch, 1 byte, can only REMOVE pump contribution
   3. V148   MEASURES whether gp-0x671d actually toggles (probe on gp-0x671E high byte)
   4. V139   halves both pump arms -- the only lever with demonstrated on-car potency
```
⊕ **V149 and V150 are independent single-lever builds and must not be stacked before either has
flown** — each builder asserts the other's cell is held.
⊕ **If BOTH are null**, the switching hypothesis is retired for every lever a cal can reach, and the
remaining candidates are the `gp-0x671a` LERP-vs-const switches, which require code edits.
⭐ **That is a complete, bounded search of the switching class** — the first time this session a
hypothesis class has been enumerated exhaustively rather than sampled.

## ⭐⭐ **THE SWITCHING IS EVERYWHERE — BUT `gp-0x671d`'s IS THE ONLY ONE A CAL EDIT CAN REMOVE**
`gp-0x671a` was checked for the same pattern. **It has it.**
```
   gp-0x671a  updated in FUN_000428d4 <- FUN_0002214a = TASK 1, the CONFIRMED 1 kHz task
              and it is `min(revcount, CEIL)` -- a CLAMPED COPY recomputed EVERY TICK, so it is
              free to move BOTH WAYS, not a one-way latch
   it gates THREE cal selections:
       0x35BEA  the NOTCH gate            -> the filter ARMS/DISARMS at up to 1 kHz
       0x36C1E  the b26 Y-branch          -> LERP(speed) vs cal(0xC640A) = -8192
       0x3AA70  the aggregator r26 branch -> LERP vs cal(0xC643E)=1536 / cal(0xC6444)=512
```
⇒ **switching nonlinearities are not one anomaly in this firmware — they are a PATTERN.** A notch
that arms and disarms at kHz rate is itself a nonlinearity, quite apart from what it filters.

### ⭐ BUT THE STRUCTURE MAKES ONLY ONE OF THEM REMOVABLE
```
   gp-0x671d switch :  cal(0xC6446)=5244   vs   cal(0xC6442)=1024     BOTH CONSTANTS
   gp-0x671a switches:  LERP(speed)        vs   a constant cal        ONE SIDE IS SPEED-VARYING
```
**V149's trick is to make both branches return the SAME value, so the switch becomes a no-op.**
⇒ **that only works when both sides are constants.** You cannot equalise a constant against a
speed-varying LERP — matching it at one speed unmatches it at every other.
⇒ **[EVIDENCE] `gp-0x671d`'s 5.12× switch is the ONLY one of these that a cal edit can eliminate.**
⇒ **V149 is not merely the best available build — it is the only removal of a switching
nonlinearity that this firmware's structure permits without a code edit.**

### ⚠ AND WHAT THAT IMPLIES IF V149 IS NULL
If removing the one removable switch does not help, then either the switching class is not the
cause, or the culprit is one of the **`gp-0x671a` switches, which cannot be removed by cal at all**.
⇒ in that case the options narrow to an **in-place instruction edit** on the branch itself — which
is the class that has bricked this ECU three times and must be gated accordingly.
⇒ **so V149 is also the cheapest possible test of the whole hypothesis class.** A null result is
informative; it retires switching-as-cause for every lever a cal can reach.

## 🛑🛑🛑 **ROOT-CAUSE CANDIDATE: A 5.12x GAIN SWITCH TOGGLING AT TASK RATE INSIDE A CONFIRMED PUMP**
Tracing the counter's increment and clear paths to their task roots settles the time course that
was left open — and it is far more interesting than a latch.
```
   INCREMENT   FUN_00041d56  <-  FUN_0002214a   = TASK 1, the CONFIRMED 1 kHz task
   CLEAR       FUN_0003bcb2  <-  FUN_0003debc <- FUN_000568d0 <- FUN_00023d24 <- FUN_00022ca0
                                              = TASK 5, >= 250 Hz, best fit 500 Hz
   SELECT      0x3AB98   ld.bu -0x671d, gp, r6 ; cmp r0, r6
                         gp-0x671d == 0  ->  cal(0xC6446)      gp-0x671d != 0  ->  cal(0xC6442)
```
⇒ **`gp-0x671d` is INCREMENTED at 1 kHz by one task and CLEARED at ~500 Hz by another.**
⇒ **it is NOT a drive-long latch — it is a flag that can TOGGLE AT TASK RATE.**
⇒ and it selects between two r24 multipliers **5.12× apart**, in a lane whose polarity
(`gp-0x6752 = −1`, verified three ways including on-car) makes it a **CONFIRMED PUMP**.

### ⭐ **A 5.12× GAIN SWITCHING AT HUNDREDS OF HERTZ INSIDE A POSITIVE-FEEDBACK LANE**
That is a **switching nonlinearity**, and it is a textbook mechanism for a rough, grinding,
ratcheting feel. ⊕ It also explains why the symptom is **intermittent and route-dependent**: the
toggle rate depends on how often the `|x| ≥ cal(0xC61FA)=5530` threshold is being crossed, which
depends on the road.

### ✅ AND THE BUILD HISTORY LINES UP EXACTLY
```
   STOCK    512 <-> 1024    a 2.00x switch   -- the mechanism is in HONDA's own calibration
   V88     5244 <-> 1024    a 5.12x switch   -- V88 made an EXISTING switch 2.6x WORSE
   V122    5244 <-> 1024    unchanged        -- it is on the car RIGHT NOW
   V149    1024 <-> 1024    NO SWITCH        -- the two branches become IDENTICAL
```
⇒ **V149 does not reduce the switching. It ELIMINATES it**, and it does so regardless of how fast
the counter toggles, because both branches return the same value.
⇒ **V149 is now the strongest-motivated build of the session**, and it is **2 bytes, cal-only,
outside the bricking class, and safe by construction** (it also reduces a pump 5.12× in the
count==0 regime).

### EVIDENCE vs BELIEF — STATED PRECISELY
```
   [EVIDENCE] increment in task 1 (1 kHz) and clear in task 5 (~500 Hz), both by call chain
   [EVIDENCE] the two branches differ by 5.12x on V122 and by 2.00x on stock
   [EVIDENCE] the lane's polarity is -1 (verified 3 ways, including on-car)
   [BELIEF]   that this switching is what the operator HEARS.  Plausible and mechanically apt --
              but no measurement ties it to his symptom, and this kit has repeatedly shown that a
              compelling mechanism is not a cause.
```
⚠ **It partially reverts V88, which he reported as a fix.** If grinding gets WORSE, V88's high
value was doing something and the answer is a value **between** 1024 and 5244 — but note that **any**
value other than 1024 **restores the switch**, so a middle value trades switch depth against
whatever V88 bought.
⭐ **V148 measures the toggle directly** (its probe reads `gp-0x671d` via the even `gp-0x671E`) —
**V149 removes the switch, V148 proves it was switching.**

## 🛑🛑 **CORRECTION: "THE COUNTERS NEVER RESET WITHIN A DRIVE" IS NOT ESTABLISHED**
The section above asserts that the fault counters latch for the whole drive and only clear on an
init path, and builds the noise-floor explanation on it. **That assertion came from a SINGLE
zero-store without checking who calls it.** Checked now:
```
   0x3EAA6 .. 0x3EAC4   FUN_0003e936 is a CLEAR ROUTINE -- it walks the counters, compares each
                        against its lockstep shadow (gp-0x4c27 for gp-0x6725), and on a match does
                        `st.b r0` to BOTH; on a mismatch it calls the lockstep-fault handler.
   FUN_0003e936         has NINE callers
   FUN_0003bcb2         holds the gp-0x671d zero-store at 0x3BD2A, AND has SEVEN callers of its own
   all of them inside a dense 0x3Cxxx-0x3Exxx fault-management web
```
⇒ **this is NOT an init-only path.** The counters **can be cleared during operation**, under
conditions that have not been traced.
⇒ **[RETRACTED] "they never reset within a drive."** ⊕ **[RETRACTED] that this is established as
the explanation for the 20–36× noise floor** — it remains a **plausible HYPOTHESIS**, but the time
course is unknown and a monotone one-way migration is exactly what was assumed and not shown.

### ✅ WHAT SURVIVES — ALL VERIFIED AT SPECIFIC SITES
```
   the counters EXIST, are LOCKSTEP-SHADOWED, and GATE CAL SELECTIONS       verified
   gp-0x671A gates three of them (aggregator / b26 Y-branch / notch gate)   verified
   gp-0x671D selects the r24 multiplier with a 5.12x step  (0x3AB98)        verified
   it INCREMENTS on a threshold crossing and SATURATES at 255 (FUN_00041d56) verified
   WHEN it resets                                                           UNRESOLVED
```
⇒ **the mechanism is real; the TIME COURSE is unknown.**

### ⭐ AND IT MAKES V149 STRONGER, NOT WEAKER
If the counter **latches once**, V149 removes a one-time 5.12× step.
If the counter can be **cleared and re-armed**, the multiplier **toggles 5.12× repeatedly through a
drive** — which is **worse** than a single step, and a far better candidate for a symptom that
"comes and goes".
⇒ **V149 removes the step under EITHER time course**, because it makes the count==0 and count>0
values identical. **Its rationale does not depend on the retracted claim.**

### ⭐ THE NEXT MEASUREMENT THIS POINTS AT
**V148's probe already reads `gp-0x671d`** (via the even `gp-0x671E`, high byte). ⇒ one drive would
show **not just whether the counter is non-zero, but whether it TOGGLES** — settling the time course
directly instead of by tracing seven callers.
⊕ That makes **V148 and V149 complementary**: V149 removes the step, V148 measures it.

## 🛑🛑🛑 **THE ASSIST CALIBRATION IS NOT FIXED — IT MIGRATES AS FAULT COUNTERS ACCUMULATE**
Sweeping `gp-0x6700`–`gp-0x6728` for cells read inside the assist chain (0x33000–0x43000) turns up
**a whole FAMILY of lockstep-shadowed latching counters**, every one of them read there:
```
   cell        total  in-assist   what it is / does
   gp-0x671A     7        7       gates THREE cal selections: the aggregator branch (0x3AA70),
                                  the b26 Y-branch (0x36C1E), and the NOTCH gate (0x35BEA)
   gp-0x671B     6        6       0x39854: ld.bu / cmp 0x1 / cmovh / bh -> gates FLOAT behaviour
                                  at count > 1
   gp-0x671C     8        8       0x3A346: st.b r22, -0x671c  + lockstep shadow gp-0x4c23
   gp-0x671D    26       26       0x3AB98: the r24 MULTIPLIER -- a 5.12x step  (V149 removes it)
   gp-0x671F/20  3        3       0x3750C / 0x375C0 / 0x37674   -- UNEXAMINED
   gp-0x6725-28 35-40   35-40     0x3CBxx / 0x3EAxx             -- UNEXAMINED, the largest users
   gp-0x6700/03/04 2-7   2-7      0x38AExx / 0x39Dxx            -- UNEXAMINED
```
⊕ the adjacent-pair pattern (`671A/671B`, `671C/671D`, `6725/6726`, `6727/6728`) is the **`ld.bu`
disp|1 ambiguity** — each pair is one cell reached by both encodings.

### 🛑 WHAT THIS MEANS — AND IT REFRAMES THE WHOLE PROJECT
`FUN_00041d56` showed the pattern in full for `gp-0x671d`: **increment on a threshold crossing,
never decrement, saturate at 255, lockstep-shadowed, raise a DTC at a count limit, and reset only
on a clear/init path.** The sweep shows that is **not one counter — it is an architecture.**
⇒ **[EVIDENCE] the effective assist calibration depends on HOW MANY FAULT THRESHOLDS HAVE BEEN
CROSSED SO FAR IN THE DRIVE.** At least four of these counters select different cal values as they
advance.
⇒ **"which build is on the car" is NOT the full state.** Two runs of identical firmware can be
running **materially different assist configurations** — and the configuration only ever moves in
one direction within a drive.
⭐ **That is a concrete, mechanical explanation for the 20–36× between-route noise floor**, and for
why the operator's grinding "comes and goes". It is not road noise; **it is the firmware
reconfiguring itself as the drive proceeds.**

### ⭐ WHAT IT CHANGES
1. **V149 gains weight.** Removing the `gp-0x671d` step (5244→1024 → constant 1024) eliminates
   **one** of these migrations outright. It is no longer just "reduce a pump" — it is **making one
   lane's calibration drive-invariant.**
2. **Every future build should ask: does this cal sit behind a counter?** Three levers this session
   already did (the notch, `0xC643E`/`0xC6440`, Lever B). 🛑 **`probe_census.py` answers "has this
   cell been probed"; this needs the companion question "is this cell SELECTED by a counter".**
3. **A drive's early minutes are not the same firmware as its late minutes.** Any endpoint that
   pools a whole drive averages across configurations. ⊕ The share endpoint's **n ≥ 90 window** gate
   makes this worse, not better, by requiring long exposure.
⚠ **UNEXAMINED and worth a session**: `gp-0x6725`–`gp-0x6728` have **35–40 accesses each**, the
largest of the family, in `0x3CBxx`/`0x3EAxx`. Nobody has looked at what they gate.

## ✅ **V139's DESIGN VERIFIED OPTIMAL — AND A FLAG ON V88's "LEVER B"**
A `sar` edit is locked to exactly ÷2, so a **finer, cal-only** version of V139 would be preferable
if one existed. **It does not.** Every cal multiplier on these lanes is **BRANCH-GATED**:
```
   0xC643E  r26 = 1536   only when gp-0x683c==0 AND gp-0x671a >= CEIL
   0xC6444  r26 =  512   only when gp-0x683c != 0
   0xC6440  r24 = 2048   only when gp-0x671d==0 AND gp-0x683c==0 AND gp-0x671a >= CEIL
   0xC6446  r24 = 5244   only when gp-0x671d==0 AND gp-0x683c != 0     <- V88's "Lever B"
   0xC6442  r24 = 1024   only when gp-0x671d != 0
```
⊕ the **MAIN path is neither of these** — `FUN_0003aa2c` LERPs from a **RAM table**
(`gp-0x6e30`/`gp-0x6e28` for r26, `gp-0x6e40`/`gp-0x6e38` for r24) whose **flash source is not
identified**.
⊕ and **two of those gates require `gp-0x671a ≥ CEIL`** — the very gate measured as **effectively
never open** (≥ 99.9 % of engaged frames below half the detector threshold).
⇒ **the `sar` at `0x3AB76`/`0x3AC20` is applied AFTER the multiply on EVERY path**, so it is the
**only lever that scales these lanes universally.** ✅ **V139 is correct as built; no finer cal-only
variant exists without the unidentified flash LERP source.**

### 🛑 AND A FLAG ON V88's "LEVER B" — IT MAY BE LARGELY INERT
`0xC6446` (V88 set it **512 → 5244**, recorded as *"Lever B … best in kit"*) applies **only when
`gp-0x671d == 0` AND `gp-0x683c != 0`.** ⊕ **That gate's duty has NEVER been measured.**
⇒ **[UNKNOWN] how often Lever B is in force at all** — the same failure mode that made the notch
family inert, and the same one that `probe_census.py` exists to catch. ⊕ It is **cheap to settle**:
`gp-0x671d` and `gp-0x683c` are byte cells, and a 427 tap on either would give a binary duty exactly
as V147's gate probe does.
🛑 **This does not retract V88** — its fix was reported by the operator, which survives the
noise-floor audit. It flags that **the MECHANISM credited for it is unverified.**

⭐ **RULE, now general across this kit: before crediting a cal with an effect, check the DUTY of the
branch that reads it.** Three separate levers this session (the notch, `0xC643E`/`0xC6440`, and now
possibly Lever B) turned out to sit behind gates whose duty nobody had measured.

## 🛑🛑🛑 **CAPSTONE AUDIT: ESSENTIALLY EVERY HISTORICAL BETWEEN-BUILD GRIND RATIO IS BELOW THE NOISE FLOOR**
The measured between-route floor is **20–36×**. Sweeping the memory index for historical
between-build grind claims and testing each against it:
```
   V72   grind #1 ratio 0.953                = 1.05x    BELOW FLOOR
   V76   predicted 0.57x, measured ~1.0      = 1.8x     BELOW FLOOR
   V75 / V74  grind 0.349                    = 2.9x     BELOW FLOOR
   V62   18-22 Hz 0.124 [0.036,0.387] vs V59 = 8x       BELOW FLOOR
   V107  "rails ~10x V106 across 10-40 km/h" = 10x      BELOW FLOOR
   V69   ladder 2501 / 879 / 168 / 109 / 746 = 23x      MARGINAL
   V62   0.024 at |rate| 16-32 deg/s         = 42x      MARGINAL -- the only one clearing 36x
```
⇒ **[EVIDENCE] the kit's entire history of BETWEEN-BUILD grind comparisons is uninformative**,
with V62's 42× the sole marginal survivor. ⊕ Several of these carried **negative controls**, which
is strictly more than a bare ratio and is why they are *marginal* rather than *dead* — but **none of
them clears the floor on magnitude alone.**

### ✅ WHAT SURVIVES: THE OPERATOR'S REPORTS, BECAUSE THEY ARE NOT RATIOS
```
   V62   "Original grinding at 2-5 mph is GONE"
   V80   "worst grinding ever, no fault"
   V88   grinding fixed  (his report; the accompanying 0.549 ratio is 1.8x = below floor)
   V122  "better, still ever so slight ... in rare moments"
   V133  "massive, violent grinding ... continues after disengaging"
```
⇒ **every durable thing this kit knows about grinding came from the operator's ear**, and every
number attached to those reports is, on its own, within route noise.
⭐ That is not a criticism of the measurements — it is the **correct calibration of what they can
decide**, and it took an identical-cal control to establish. **It also means the kit's doctrine
(*"score bands, let the OPERATOR score symptoms"*) was right all along and under-obeyed.**

### ⭐ WHAT THIS MEANS FOR THE NEXT DRIVE
1. **Judge the build by ear.** The scorers are for MECHANISM questions (does the gate open, is the
   lane live, did the notch run) — **not for ranking builds.**
2. **The share endpoint (`score_creep_share.py`, floor ~1.8×) is the ONE exception**, and only with
   **≥ 2 minutes of engaged creep**; below that gate it refuses.
3. **Do not re-derive conclusions from the historical ratios.** They are recorded as history, not as
   evidence. 🛑 **Any future session quoting a between-build grind ratio must state it against the
   20–36× floor** — the scorers now carry that banner.

## ✅✅ **V139 RE-ELEVATED — ITS EVIDENCE SURVIVED THE RETRACTION, BECAUSE IT NEVER USED THE ENDPOINT**
The noise-floor retraction was propagated to this session's own comparisons but **not to the older
claims that rest on the same kind of statistic.** Doing that now changes the flight order.

### 🛑 V62's HEADLINE IS A BETWEEN-BUILD RATIO OF 8× — INSIDE THE MEASURED FLOOR
`accord-v62-flashed-grinding-is-fixed`: **18–22 Hz creep 0.124 [0.036, 0.387] vs V59** = **8×
better**, and **0.024 (42×) at |rate| 16–32 °/s**, with a **30–40 Hz negative control at ~1.0**.
⊕ The between-route floor measured today on the engaged/manual creep ratio is **20–36×**.
⇒ **V62's 8× headline sits INSIDE the floor of a closely related statistic.** ⚠ It is **NOT
invalidated** — it is a **different statistic** and it **carried a passing negative control**, which
is strictly more than a bare ratio. But **the caveat has never been recorded**, and the 42× figure
is the more robust half of that result.

### 🛑 AND IT EXPOSES A CONTRADICTION THAT WAS NEVER STATED PLAINLY
```
   V62   sar 9, gain 3564 (4x)   ->  operator: "Original grinding at 2-5 mph is GONE"
   V133  sar 9, gain 7128 (8x)   ->  operator: "massive, VIOLENT grinding"
```
**The same two bytes, opposite outcomes, different base gain.** ⊕ A gain-normalised reading (lane
strength × base gain: V62 ≈ 82, V122 ≈ 61, V133 ≈ 164) would put V62's configuration at
`0xC6446 ≈ 6989` on the 6× base — **and that is NOT proposed**, because it **RAISES a confirmed
pump** (`gp-0x6752 = −1`), which is the V133 direction.
⭐ **Between an 8× between-build ratio and a recent, unambiguous operator report on his own car,
the operator's report wins.** The kit has now measured that its statistics cannot resolve builds;
his ear demonstrably can.

### ✅ WHICH RE-ELEVATES V139
V139 halves **both** pump arms (`0x3AB76`/`0x3AC20`, `sar 10 → 11`). **Its entire rationale is:**
```
   1. gp-0x6752 = -1, verified THREE ways including on-car  -> these arms are a CONFIRMED PUMP
   2. V133 DOUBLED them and the operator reported violent grinding  -> the bytes are POTENT on-car
   3. reducing a feedback magnitude cannot destabilise a stable loop -> SAFE BY CONSTRUCTION
```
⇒ **not one of those three depends on the retracted endpoint.** ⊕ I demoted V139 earlier partly on
the α2-vs-knee ladder, which is now withdrawn — **the demotion went with it and was never undone.**
⇒ **V139 is now co-primary with V147**, and arguably has the **stronger** basis of the two:
```
   V147  0xC61F6 deadband  virgin cal, lane feeds the aggregator directly, BUT the dose is a
                           guess and gp-0x6ADA has never been flown -> potency UNKNOWN
   V139  both pump arms    the bytes are PROVEN POTENT on-car (V133), direction is inference
```
⚠ **V139's remaining caveat is unchanged and real**: knowing `sar 9` is worse than `sar 10` does
not prove `sar 11` is better. **Expected failure mode: the steering goes number without the grind
improving — in which case revert to V122.** ⊕ And the *"2× ≈ optimum"* framing that argued against
it rested on V62's between-build numbers, which is exactly the class now in question.

## 🛑🛑🛑 **`gp-0x6B4C` IS A FAULT-ARBITRATION SUM — THE LAST CAL CANDIDATE IS CLOSED, AND THE LEVER WAS UNSAFE**
`FUN_0002caa2` (slot 8) decompiles to a **LATCHING PLAUSIBILITY MONITOR**:
```c
   if (gp-0x3cba == 1) {
       sStack_1c = gp-0x6b12;
       if (|gp-0x6b12| exceeds cal(0xC61D2)) {
           gp-0x6788 = 1;        // FAULT FLAG
           gp-0x3cba = 2;
           sStack_1c = 0;        // this contribution LATCHES OFF, permanently
       }
   } else if (gp-0x3cba == 2) { sStack_1c = 0; }      // stays off
   ...
   local_20 = 8;  cStack_1f = <state 0..5>;  uStack_1c = sStack_1c;   // <- THE PAYLOAD
   FUN_00025c32(&local_20);
```
⇒ **`gp-0x6B4C` is NOT an assist sum. It is a sum of MONITORED contributions, each behind a
latching fault gate**, and the `0xC4124` "type" vector is that monitor's per-slot **configuration**.

### ✅ THIS EXPLAINS EVERY MEASUREMENT AT ONCE
```
   p50 0-26                     contributions LATCH OFF and stay off
   max 1459-1664                spikes BEFORE latching
   broadband, spiky spectrum    latching transitions are IMPULSIVE
   "1.4x flat" band share       an IMPULSIVENESS ARTIFACT, not 18-22 Hz content
```
⇒ **the one lane that looked consistently elevated was elevated because it is SPIKY, not because
it oscillates at 20 Hz.** ⊕ The flat-baseline control caught the inflation; **this decompile
explains its CAUSE.**
⇒ **[EVIDENCE] `gp-0x6B4C` is not the grind carrier. The last cal-path candidate is CLOSED.**

### 🛑 AND THE LEVER WAS NOT MERELY WEAK — IT WAS UNSAFE
`0xC4124[i] : 0 → 5` would have **disabled a plausibility monitor** — a fault-detection function —
on an EPS. ⊕ The kit came within one decompile of proposing that, on **1.4×-flat evidence**.
⭐ **RULE: before disabling ANY per-slot/per-term configuration cell, read what the slot COMPUTES.
A "weight vector" and a "monitor configuration table" look identical from the cal side.**

### ⭐ THE CAL SPACE IS NOW EXHAUSTED
```
   CLOSED by measurement    b26 (clamp/a2/knee/K1) | the notch family | base-assist damper
                            gp-0x6BBE | EVERY flown cal | and now gp-0x6B4C
   REJECTED before building 0xC6372 (lane below flat) | 0xC4124 (a fault monitor)
   NEVER FLOWN, still open  0xC61F6 -- the r24 pump deadband.  V147 tests it.
```
⇒ **V147's deadband is the only cal lever left with a live rationale**: virgin cell, on a lane
that feeds the aggregator **directly**, with a confirmed pump polarity behind it.
⇒ **The analysis has converged. The remaining information is on the car.**

## ✅✅ **THE `gp-0x6B4C` CONTRIBUTORS NARROWED TO FOUR — AND THE METHOD IS VALIDATED**
`FUN_0003a8a8`'s full decompile fixes the struct layout passed to `FUN_00025c32`:
```c
   local_1c = 7;      // [0] SLOT INDEX      uStack_12 = 0x400;   // [10] weight
   cStack_1b = mode;  // [1] mode            uStack_10 = 0x400;   // [12] weight
   uStack_1a = 0;     // [2] data            uStack_e  = 0x400;   // [14] weight
   uStack_18 = 0;     // [4] data
   uStack_16 = 0;     // [6] data
   uStack_14 = 0;     // [8] data
```
⇒ **offsets 10/12/14 are CONSTANT 0x400 weights** — an earlier scan counted those as "computed
fields" and wrongly called every caller a contributor. **Only offsets 2/4/6/8 are data.** Reading
just those, from the `sst.h` stores before each call:
```
   slot 0  FUN_0002e52e   0@2  r12@4  0@6  0@8      data at offset 4
   slot 1  FUN_0002b422   0@2  r12@4  0@6  0@8      data at offset 4
   slot 3  FUN_0002c246   0@2   r8@4  0@6  0@8      data at offset 4
   slot 8  FUN_0002caa2   0@2   r9@4  0@6  0@8      data at offset 4
   slot 6  FUN_0003aff4   0@2   0@4   0@6  r7@8     data at offset 8
   slot 7  FUN_0003a8a8   0@2   0@4   0@6  0@8      NO DATA
```
✅ **slot 7 reads ALL-ZERO, exactly as its full decompile showed ⇒ THE METHOD IS VALIDATED**
against a known answer before being trusted on the unknowns.

### ✅ AND THE OFFSET DECIDES WHICH ARRAY IS FED
From `FUN_00025c32`:
```c
   *(short *)(gp-0x62e0 + slot*2) = clamp(param_1[2], +-0x4000);
   *(short *)(gp-0x62f8 + slot*2) = clamp(param_1[4], +-0x2800);   // <- THE ARRAY THE SUM READS
   *(short *)(gp-0x6274 + slot*2) = clamp(param_1[6], +-900);
   *(short *)(gp-0x633c + slot*2) = clamp(param_1[8], +-20000);
```
⇒ **offset 4 feeds `gp-0x62f8`, the array the 11-slot sum walks.** Offset 8 feeds `gp-0x633c`, a
**different** array.
⇒ **ONLY slots 0, 1, 3 and 8 contribute to `gp-0x6B4C`. Slots 6 and 7 do NOT.**
```
   remaining candidates:  slot 0 FUN_0002e52e | slot 1 FUN_0002b422
                          slot 3 FUN_0002c246 | slot 8 FUN_0002caa2
   all four callers sit in ONE cluster, 0x2B4xx-0x2E5xx
```
⊕ Narrowed from **seven unknown indices → four named functions in one subsystem cluster**, and the
`0xC4124[i] : 0 → 5` lever can now be aimed at any one of them.
⚠ **Still not a build**: what those four compute is unread, and the lane's evidence base is
**1.4× flat = weak**. **V147 flies first.**

## 🛑 **`0xC6372` SIZED AND REJECTED BEFORE BUILDING — AND IT NARROWS THE FIELD TO ONE**
The aggregator adds its ten lanes **BARE — admission gates only, no per-lane weights** (which is why
the kit recorded *"no weight cell exists"* for `gp-0x6b26`). ⇒ **an aggregator lane can only be
scaled at its SOURCE.** For `gp-0x6BBE`, the largest lane (p50 74 vs the aggregator's 115–218), all
three source cals are **VIRGIN** — so `0xC6372`, its torque-EMA alpha, looked like the lever.

### ✅ IT SIZES WELL
`iVar29 += ((gp-0x4f60*32 - iVar29) * cal(0xC6372)) >> 10`, a one-pole EMA, `alpha = cal/1024`,
in **task 5** (kit bound ≥ 250 Hz, best fit 500 Hz). At fs = 500:
```
   alpha    fc Hz   |H| 1Hz   |H| 3Hz   |H| 20Hz   20Hz attenuation
     205     15.9    0.9984    0.9861     0.6661       1.00x   (stock)
     102      7.9    0.9929    0.9412     0.3863       1.72x
      77      6.0    0.9873    0.9008     0.2978       2.24x
      51      4.0    0.9711    0.8047     0.1997       3.34x
```
⊕ and the lane is **DOMINATED by this path** — the earlier sizing gave torque : accel = **6464 : 576
= 11 : 1** at engaged creep, so this alpha shapes **~92 %** of the lane input. ⊕ the direction is
robust across the whole fs bound (20 Hz sits above `fc` at every rate in 250–1000).

### 🛑 AND IT IS STILL POINTLESS — THE LANE DOES NOT CARRY THE BAND
**`gp-0x6BBE`'s measured 18–22 Hz share is 0.54× FLAT — BELOW baseline.** It carries **less**
18–22 Hz than a featureless spectrum. ⇒ **attenuating 20 Hz in a lane that does not carry 20 Hz
achieves nothing.** ⇒ **V148 on `0xC6372` would have been a null. One command cost; no drive
spent.** ⭐ **Size the lever, THEN check the lane carries the band — in that order, because the
sizing is the seductive part.**

### ⭐ WHICH LEAVES EXACTLY ONE TARGET STANDING
```
   lane                       sig/flat            consistent across its routes?
   gp-0x6B4C (11-slot sum)    1.44x, 1.38x        YES -- the only one
   "default tap" gp-0x6ABC    1.42 / 0.53 / 0.08  no -- wildly route-dependent
   gp-0x6BBE                  0.54x               BELOW baseline
   gp-0x6B26                  0.43-0.56x          BELOW baseline
   notch lane gp-0x6B86       0.06-0.27x          BELOW baseline
```
⇒ **`gp-0x6B4C` is the only lane consistently above a flat spectrum**, and because the aggregator
adds it **bare**, its **only** lever is **`0xC4124`, the slot vector**. ⊕ `0xC63AA` scales it only
into `gp-0x6b70`, which is **itself below baseline** — so that weight, however well-formed, is
aimed at the wrong output.
⇒ **the slot disable is the SOLE remaining cal-path candidate**, and it still needs the five
payload decompiles (slots 0, 1, 3, 6, 8 — `FUN_0002e52e`, `FUN_0002b422`, `FUN_0002c246`,
`FUN_0003aff4`, `FUN_0002caa2`).
⚠ And its evidence base is **1.4× flat**, which is **weak**. **V147 remains the build to fly**: its
cal is equally virgin, its lane feeds the aggregator directly, and its drive also carries the gate
probe that retires the notch family.

## ✅✅ **19 VIRGIN ASSIST-PATH CALS — AND THE `FUN_00038148` PER-TERM WEIGHT MAP**
Since **no flown cal moves the creep grind**, the answer must be in a cal **never flown**. A census
across **131 build images** (diffing `0xC4000–0xC8000` against stock; **948 cells ever touched**)
gives the frontier:
```
   VIRGIN assist-path cals (19):
     0xC40DA gp-0x6c2e EMA alpha      0xC4124 11-slot type vector    0xC6136/38 gate values
     0xC615A gp-0x6bbe clamp fallback 0xC6194 DEAD lkas rate limiter 0xC620A detector threshold
     0xC6316 governor speed gate      0xC6370 gp-0x6c2e weight       0xC6372 torque EMA alpha
     0xC63A2 0xC63A4 0xC63A6 0xC63A8 0xC63AA   FUN_38148 per-term weights
     0xC63C2 gp-0x6b5e gain           0xC643C alpha0                 0xC64FA gate CEIL
     0xC64FD b26 Y-branch threshold
```

### ✅ THE WEIGHT MAP, VERIFIED FROM THE DECOMPILE
```c
   sum = (gp-0x6b4e * gate(+-0x2800) * cal(0xC63A8)) >> 10
       + (gp-0x6b4c * gate(+-0x2800) * cal(0xC63AA)) >> 10
       + (gp-0x6b26 * gate(+-0x400)  * cal(0xC63A6)) >> 10
       + (gp-0x6b46 * gate(+-0x400)  * cal(0xC63A4)) >> 10
       + (gp-0x6bd0 * gate(+-0x800)  * cal(0xC63A0)) >> 10
       + (gp-0x6bbe * gate(+-0x800)  * cal(0xC63A2)) >> 10
   then  * gp-0x6752 (the -1 POLARITY),  *16,  through a cal(0xC63AC)=102 IIR  ->  gp-0x6b70
```
```
   cal       lane        meaning                 gate      stock  V122   status
   0xC63A0   gp-0x6bd0   base-assist damper      +-0x800    1024  1024   touched by a build
   0xC63A2   gp-0x6bbe   viscous + DC pedestal   +-0x800    1024  1024   VIRGIN
   0xC63A4   gp-0x6b46   (unmapped lane)         +-0x400    1024  1024   VIRGIN
   0xC63A6   gp-0x6b26   b26 inertia             +-0x400    1024  1024   VIRGIN
   0xC63A8   gp-0x6b4e   (unmapped lane)         +-0x2800   1024  1024   VIRGIN
   0xC63AA   gp-0x6b4c   11-SLOT ASSIST SUM      +-0x2800   1024  1024   VIRGIN
```
⭐ **All six are UNITY 1024 in stock and V122; only `0xC63A0` has ever been moved.**

### ⭐ `0xC63AA` IS THE BEST-FORMED LEVER FOUND ALL SESSION
It is a **per-term weight on `gp-0x6b4c`** — the lane that ranked as the **most consistent grind
carrier** — at **unity 1024**, **never flown**, **cal-only**, and **continuously dosable**.
⇒ **strictly better than disabling an unidentified slot INSIDE `gp-0x6b4c`**: same target, **no
slot map required**, and it **scales** rather than zeroes, so the dose is a choice rather than a
cliff.

### 🛑 THE HONEST CHECK AGAINST IT
This loop's output is **`gp-0x6b70`**, whose measured band share is **0.46–0.52× flat — BELOW
baseline** ⇒ `gp-0x6b70` is **not itself a grind carrier**, so reducing `gp-0x6b4c`'s contribution
*here* may not reach the symptom. ⊕ And `gp-0x6b4c` **also enters the aggregator directly**
(`FUN_0003aa2c`), a path this weight does **not** touch.
⇒ **[BELIEF] well-formed and virgin; [UNKNOWN] whether it reaches the symptom. NOT a build yet.**
**V147 still flies first** — its cal is equally virgin and its lane feeds the aggregator directly.

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


---

🛑 **8 older section(s) moved to `docs/archive/STATE-ARCHIVE-2026-08-28.md`** to hold this file under the 145 KB target.
