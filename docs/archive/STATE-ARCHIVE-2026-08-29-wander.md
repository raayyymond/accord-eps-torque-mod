# STATE archive

A RECORD, NOT AN INSTRUCTION.

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

## ✅✅✅ **V168 BUILT — THE BASE-ASSIST SLOPE CAP, A LEVER CLASS THE KIT HAS NEVER TRIED**
```
   V168 = V158 + 0xC6384  2048 -> 1536   (2.000x -> 1.500x)
   image  058dd64ac442ef43c790965c9a5fc011f147f7ff0a5e7cd0c0d1bb8889c7b0ff
   .rwd   0f0ace3b5bc0a8541227e06c831c555797566374b298ba606614f5a09a1356f1
   ONE payload byte (0xC6385: 08 -> 06) + one CRC trailer.  35/35 assertions.
   CRC chain 50/50 - readback byte-identical - all six curve records untouched.
```
✅ **`0xC6384` is byte-identical on ALL 161 IMAGES** — the first time this kit has moved it.
⚠ **The payload is ONE byte, not two**: `0x0800 -> 0x0600` differs in the high byte only. The build
asserts the **VALUE**, not a hardcoded byte count — the hardcoded-2 assertion has bitten this kit
before and it fired here too, on the first run.

### ⭐ HOW THIS BUILD'S CLASS DIFFERS FROM THE WHOLE ARC SINCE V38
```
   V38-V52    authority / filters / poles / caves
   V53-V61    telemetry probes and lane mutes
   V62-V73    the rate lane (r24 / r26)
   V74-V83a   the base-assist DAMPER          V84 damper reverted to Honda
   V85-V122   friction / knee / alpha2, the Coulomb relay
   V133-V167  the damper's SHAPE and the Path-2 weight
   ---------------------------------------------------------------------------------
   V168       the BASE-ASSIST MAP's own slope cap  <- the DOMINANT torque-fed loop term
```
Every earlier lever acts on a term that is **not** the dominant one. `gp-0x6b86` is **5.8–7.8x the
entire PID** and has the widest window of all eleven aggregator slots. **This is a new lever, not the
same lever pushed the other way.**

### ✅ WHY IT IS AIMED AT THE RATCHET SPECIFICALLY
The grind and the ratchet **dissociate**: post-V102 the grind falls ρ = −0.94 (p 0.005) in three
channels while the ratchet does not move (ρ = −0.14, p 0.787) against a floor that would have shown
1.9x. Every lever the kit has found is the grind's. V168 is the first aimed at the other one.
⊕ **V168 is built on V158**, so it carries the grind lever too and **both symptoms score from the
SAME single episode in different bands** — the two are separated by the **INSTRUMENT**, not the build.

### 🛑 THE NON-STOCK DELTA, READ FROM THE BUILT IMAGE
```
   V168 vs STOCK: 341 differing bytes, 321 payload + 5 CRC trailers, in 12 blocks
     0xC4000  169 B   friction / knee / alpha2 / clamp family (V85-V122)
     0xC6000   42 B   main cal -- incl. the 6x LKAS gain, Lever B, and THIS BUILD'S 1 byte
     0xE4000   36 B   } arbitration setpoint limits raised at V38 (0x3c -> 0x40 pattern)
     0xE5000   36 B   }
     0xD7000   22 B   the damper records (V158's FactorC/FactorE shape)
     0x55000    6 B   CAN tap
     0x35000    4 B   · 0x2A000 2 B · 0x13000/0x14000/0x3A000/0x45000 1 B each
```

### ✅ WHAT A NULL WILL LICENSE — WRITTEN BEFORE THE CUT
One continuous **15 s** engaged creep pass, scored by `rlog-tools/score/score_band_excess.py`:
- **ratchet 5–12 Hz excess falls BELOW its slope-matched null** ⇒ the ratchet is gone in that regime
  and the loop-gain account is confirmed;
- **excess unchanged** (V122 reference ≈33, null ≈4) ⇒ a predicted 3.4x damping increase produced
  nothing ⇒ **falsifies the real-positive `P·L` assumption**, so this loop does not produce the 14.3x
  cancellation and the assist map is exonerated the way the Coulomb relay now is;
- **excess RISES** ⇒ lowering `|L|` sharpened the mode, possible only if `P·L` is not real-positive
  ⇒ revert and re-derive the phase.
✅ A single 15 s episode detected the ratchet **11/11 at 5–65x margin**, so **all three outcomes are
readable from one pass. There is no uninterpretable branch.**

### 🛑 THE FEEL COST — THE OPERATOR'S CALL
Lowering the cap means **less assist per unit driver torque near centre ⇒ heavier steering there**,
against a standing constraint. Narrower than it sounds: the curve is **uncapped above X≈450 so peak
authority and max rates are untouched**, and the map is **driver-torque fed, not the LKAS lane**
(`0xC616C`=0 ⇒ `gp-0x6b4a`≡0, asserted in the build). 1536 is the **smallest** dose clearing the
one-episode margin; 1280 and 1024 remain if it reads clean but incomplete.

## ⭐ **PEAK COMMAND OSCILLATION IS IN THE GRIND'S BAND — IT SHARES THE GRIND'S LEVER**
The third symptom, measured for the first time with the validated estimator. Sweeping the whole
usable spectrum of all three COMMAND channels, excess over each channel's **own** fitted power law,
nulled at that channel's **own** measured slope:
```
   median excess / slope-matched null p95, 7 routes
                 0.5-3   3-5    5-12   12-15   15-25   25-35   35-49
   cc_req        0.68    0.85   0.54   0.64    1.97    0.48    1.06
   co_tqcan      0.93    0.84   0.48   0.50    1.65    0.39    0.82
   sc_tq         0.61    0.88   0.50   0.65    1.55    0.52    0.64
   cs_tq (car)   0.03    0.17   9.15   1.84    5.40    0.35    0.38
```
✅ **[EVIDENCE] the command clears its own null in EXACTLY ONE band — 15–25 Hz, the GRIND's band —
and is below its null everywhere else, including the ratchet's.**
⭐ **The decisive asymmetry**: at 5–12 Hz the car's peak is **LARGER** (9.15) than its 15–25 Hz peak
(5.40), yet the command is **below null** at 5–12 (0.48–0.50) and **above** it at 15–25. So the command
does **not** simply inherit whatever the car does ⇒ **"openpilot re-emits everything" is refuted**,
and the selectivity needs an explanation.
⊕ **It has one**: openpilot steers on **angle/curvature**, and the ratchet is a **TORQUE-only mode
with no angle signature** (angle channels 0.79–0.83, i.e. chance). **A torque-only mode is invisible
to openpilot; a mode that moves the wheel is not.** That predicts exactly the observed pattern.

### ⚠ WHAT IS *NOT* ESTABLISHED — AND MY OWN CONTROL FAILED
⚠ **The correlation is NOT significant**: command 15–25 vs car 15–25 gives ρ **+0.54 / +0.61**,
p **0.215 / 0.148** at n = 7. Positive and the right sign, but it does not stand on its own.
🛑 **My 5–12 Hz negative control DID NOT DISCRIMINATE** — it returned ρ **+0.54 / +0.68**, as high as
the band it was meant to contrast with. It was correlating sub-null noise against the car's peak, so
**it carries no information and the causal direction is NOT established by it.** Recorded rather than
quietly dropped.
⚠ The build trend agrees in direction but is weaker: post-V102 command ρ **−0.70 / −0.80**
(p 0.188 / 0.104) against the car's **−0.90 (p 0.037)**.

### ✅ THE ACTIONABLE CONCLUSION
**Peak command oscillation is not a separate mechanism needing its own lever.** It sits in the
grind's band, moves in the grind's direction across builds, and openpilot must not be modified
(standing instruction). ⇒ **damping the 15–25 Hz resonance is the only permitted route, and V158's
damper shape — already on the fly-first build — is that lever.** No new build is required for it.
⊕ **The V168 drive scores it for free**: the same episode already yields the 15–25 Hz band, so the
command peak can be read alongside the grind with no extra exposure.

## ✅ **THE SLOPE-CAP DOSE LADDER IS CUT — ALL FOUR DIRECTIONS READY, NO REBUILD NEEDED**
```
   build  cap    gain     Q ratio   vs stock   image SHA256 (first 16)
   V169   1792   1.750x    6.57     2.2x       ed9e5fec84378f20   <- SMALLER, if V168 is too heavy
   V168   1536   1.500x    4.26     3.4x       058dd64ac442ef43   <- FLY FIRST
   V170   1280   1.250x    3.16     4.5x       0c923c363a920459   <- next step up
   V171   1024   1.000x    2.50     5.7x       e3cbc92de7a07bf2   <- largest sane dose
```
✅ All four are **V158 + one cal cell**, built through **V168's own verified builder** (one builder,
four build numbers) so the assertions and the CRC/readback path cannot drift apart. **35/35 on each.**
⊕ The feel cost rises monotonically with the dose; **peak authority and max rates are untouched at
every dose** (the curve is uncapped above X≈450) and **no dose touches the LKAS lane**.
⇒ whichever way the V168 drive reads — clean but incomplete, or effective but too heavy — **the next
build already exists.**

## ✅ **LKAS AUTHORITY IS NOT THE BINDING CONSTRAINT — THE COMMAND IS DELIVERED AND RARELY RAILS**
The third of the operator's three named symptoms, measured directly for the first time.
```
   ENGAGED frames, |sc_tq| against its own observed ceiling of 4096 counts
   route build   n       rail duty   >=90 %   >=50 %   p50 |cmd|
   r78   V91     61,987   0.0258     0.0302   0.0523     230
   r7e   V96     61,506   0.0648     0.0739   0.1161     230
   r96   V102    57,629   0.0145     0.0170   0.0401     145
   ra6   V106   123,802   0.0302     0.0338   0.0545     133
   r1e   V107    99,910   0.0277     0.0334   0.0625     247
   r22   V112    48,957   0.0379     0.0428   0.0754     232
   r24   V122    58,652   0.0271     0.0303   0.0495     149
   pooled: rail 3.3 % - >=90 % 3.7 % - >=50 % 6.4 %
```
✅ **[EVIDENCE] the command sits at its ceiling only ~3 % of engaged frames**, and its median is
**133–247 counts, i.e. 3–6 % of the ceiling.** openpilot is overwhelmingly asking for very little.
⇒ **raising an authority ceiling cannot add what was never requested.**

### ✅ AND WHAT IS REQUESTED *IS* DELIVERED
```
   command -> steering RATE, engaged, best lag over 0-400 ms, vs phase-shuffled surrogates
   r78 230 ms r -0.167 (shuf p95 0.087)   ra6  70 ms -0.263 (0.054)   r22 390 ms -0.296 (0.100)
   r7e 150 ms r -0.349 (0.094)            r1e  20 ms -0.293 (0.056)   r24 180 ms -0.441 (0.102)
   r96  40 ms r -0.402 (0.059)                                        DELIVERED on 7/7 routes
```
✅ **[EVIDENCE] the correlation clears its shuffled control on every route**, and its **sign is
negative**, which is exactly the operator-confirmed convention (*+LKAS demands negative angle*). That
sign agreement is a free sanity check on the whole measurement, and it passes.
⇒ **the plant is not swallowing the command.** Authority is not a delivery failure either.

### 🛑 ONE MEASURE OF MINE THAT DOES NOT WORK — RECORDED, NOT DROPPED
I stratified `mean|rate| / mean|cmd|` by command magnitude to look for a friction/stiction signature
(less motion per count at small commands). It shows the **opposite** — the 0–200 stratum has the
**highest** ratio (13.7–57.0 vs 6.2–26.6 at 200–800). **That is an artefact, not a finding**: when the
command is small the wheel motion is dominated by the driver and the road, so the ratio is
small-denominator noise rather than a delivery gain. **The stratification carries no information and
no stiction conclusion may be drawn from it.**

### ✅ THE CONCLUSION, AND WHAT IT LEAVES
**“LKAS authority” is not a firmware authority-ceiling problem.** The ceiling binds 3 % of the time,
the command is delivered when issued, and the firmware already multiplies it **6x** (`0xC6CD0`=5346).
The remaining ways to ask for more are **openpilot-side, which the standing instruction forbids**, and
the one firmware ceiling that was tried is closed: **`0xC407E` is the hard-fault interlock — Honda
ships it at 511, one count under its own 512 trip, and V73 raised it ⇒ V74/V75 FAULTED.**
⇒ **No authority lever is proposed, because the measurement says none is needed.** If the operator's
lived experience of weak lane-keeping persists, the thing to capture is **which manoeuvre** it happens
in — the 3 % rail duty means there IS a small population of railed frames, and those are the only
frames where a ceiling could matter.

## ✅✅ **THE RATCHET IS A FIXED RESONANCE WITH COMMAND-PROPORTIONAL DRIVE — THE `1−P·L` SIGNATURE**
244 pooled engaged-creep windows, each assigned to a stratum by its **own** mean operating point (the
earlier attempt required contiguous runs *within* a stratum, which fragments the data and left six of
seven strata empty — that cut is superseded).
```
                  n win   peak Hz   excess          FREQUENCY SPREAD
   speed 1-6       17      8.59      18.7
   speed 6-10      57      7.81      15.1
   speed 10-14     84      8.40      27.4           7.81-8.98 Hz   sd 0.46   CV 5.5 %
   speed 14-18     58      7.81      40.0
   speed 18-24     28      8.98      35.5

   |rate| 0-3      42     10.16       9.7
   |rate| 3-6      27     10.74      12.5
   |rate| 6-12     43      8.40      21.7           8.01-10.74 Hz  sd 1.12   CV 12.3 %
   |rate| 12-25    45      8.01     143.1   <- worst rate band
   |rate| 25+      87      8.20      27.6

   |cmd| 100-250   23      9.57      17.0
   |cmd| 250-600   75      8.59      19.4           8.01-9.57 Hz   sd 0.60   CV 7.0 %
   |cmd| 600-1500  46      8.01      39.4
   |cmd| 1500+    100      8.20      58.1   <- MONOTONE, 3.4x across the command range
```
✅ **[EVIDENCE] the FREQUENCY is near-invariant** — CV **5.5 %** across speed, **7.0 %** across
command, **12.3 %** across rate, with only a modest downward drift as rate and command rise.
✅ **[EVIDENCE] the AMPLITUDE is MONOTONE in command magnitude, 17.0 → 58.1 (3.4x).**
⇒ **fixed resonance + command-proportional drive.** That is precisely the `Z = (Z0 + P·F)/(1−P·L)`
signature: the command is the **excitation `F`**, the plant sets the frequency, and the loop sets how
sharply it rings. **A moving loop pole would have shifted the frequency with operating point. It does
not.**

### ⭐ AND IT SHARPENS THE ENGAGED-ONLY EXPLANATION
My earlier account attributed engaged-only entirely to the engagement-conditional lanes joining `L`,
predicting a **4.88x** engaged/manual ratio against a measured **19.9x [4.82, 35.64]** — consistent
but at the very bottom of the CI. **The command-scaling result supplies the missing factor**: in
manual the command is **zero**, so the excitation `F` is absent as well as the extra loop gain.
⊕ The two together land much closer to the measurement than either alone. **⚠ Not a clean product** —
excitation and the engagement-conditional loop terms are both driven by engagement and are not
independent factors to multiply — **but the direction and rough size now agree, where the loop-gain
term alone did not.**

### ✅ WHAT THIS MEANS FOR V168
It **confirms the lever's logic**: `1−P·L` divides the *whole* response, including the
command-driven part, so reducing `|L|` attenuates the ratchet **at every command level** rather than
only at some operating point. It also predicts the **drive should show the effect most clearly at
HIGH command and in the 12–25 deg/s rate band**, where the excess is largest — useful for the pass.

### ⚠ THE LKAS GAIN COSTS RATCHET — STATED, NOT RECOMMENDED
```
   gain 3564 (4x): ratchet excess median 16.5  (n=3)
   gain 5346 (6x): ratchet excess median 34.5  (n=6)   ratio 2.09x
   Mann-Whitney p = 0.167  -- NOT significant, and CONFOUNDED (V96->V102 spans other builds)
```
⚠ **[BELIEF, weak]** raising the LKAS gain raises the ratchet, as **excitation** — consistent with
the command-scaling result above and with the operator's own 8x experience of more grinding.
🛑 **This is NOT a recommendation to lower the gain** — there is a standing instruction never to, and
the operator wants 8x if anything. **The constructive reading is the opposite: damping the resonance
is what BUYS the headroom for more gain.** If V168 works, 8x becomes affordable in a way it is not
today.

## ⭐⭐ **LEVER #2 EXISTS: THE ASSIST MAP'S OWN SECOND-ORDER SECTION IS A RETUNABLE NOTCH**
This kit's record says *“this firmware has NO frequency-selective lever”* (FactorD refuted) and
*“no notch filter exists anywhere”*. **Both are wrong.** `FUN_000352b4` carries a genuine biquad in
the **dominant torque-fed lane**, and it is **already enabled on the flying build**.
```
   s1 = gp-0x3814,  s2 = gp-0x3818   (read BEFORE update),  1 kHz
     w = -C_AC*s1 - C_A8*s2 + C_B4*x
     y = (1-C_AC)*s1 + (C_B0-C_A8)*s2 + C_B4*x        y clamped to +/-12.0
     s1 <- s2 ;  s2 <- w
   coefficients 0xC60A8 / 0xC60AC / 0xC60B0 / 0xC60B4 (float32)  ·  enable 0xC649B
```
Simulated directly from the decompiled operand order (a sign slip here inverts the answer, so it is
**simulated, not hand-derived**):
```
   freq       FLYING (stock coeffs)      V106/V107 coeffs
   8.64 Hz    0.9788  -11.8 deg          0.9823  -16.5 deg     <- the RATCHET, PASSED by both
   21   Hz    0.8659  -30.0 deg          0.4925  -72.3 deg     <- the grind
   25.5 Hz                               gain 0.000            <- V106 placed a PERFECT NULL
```
✅ **[EVIDENCE] the structure can place a deep notch — the kit has already done it once**, at
25.5 Hz, in the V105/V106 notch work. ✅ **[EVIDENCE] neither tuning touches the ratchet**: both pass
8.64 Hz at ≈0.98.
✅ **[EVIDENCE] the enable is ON for the flying build** (`0xC649B` = 1 from V104; stock ships **0**),
and the coefficient cells have been changed before **without faults**, so neither the enable path nor
the coefficient path is new risk.

### ⭐ WHY THIS IS A BETTER LEVER THAN THE SLOPE CAP ON THE FEEL AXIS
```
   slope cap 0xC6384   reduces the map's gain at EVERY frequency INCLUDING DC
                       => heavier steering near centre.  Real, monotone with dose.
   notch at 8.64 Hz    reduces the loop's contribution ONLY at the resonance
                       => DC gain 1.0000  =>  NO steady-state feel cost at all.
```
⊕ And it **does not rest on the real-positive `P·L` assumption** that V168's lever needs: a notch
removes gain at the resonant frequency **without adding gain anywhere**, which is the textbook fix
for a loop resonance whatever the loop's phase there.
⚠ **[BELIEF] the DC-cost argument.** It follows from the section's own DC gain, which is measured;
what is *not* measured is whether the operator's felt “weight” tracks DC gain rather than the
mid-band. A first-order claim, not a guarantee.

### 🛑 WHY A RAZOR NOTCH IS THE WRONG DESIGN, AND WHAT REPLACES IT
An optimiser hits **−96 dB at exactly 8.64 Hz with DC gain 1.0000** — but that notch is also that
NARROW, and **the ratchet's own frequency spans 7.81–10.74 Hz across operating-point strata**
(CV 5.5 % speed, 7.0 % command, 12.3 % rate). A razor notch simply misses the mode when it drifts.
⊕ It also **amplified 40 Hz by 1.36x**, which must not be traded away silently.
⇒ the design in progress targets **attenuation across 7–11 Hz** with a pole-radius margin, unity DC,
and **no gain increase anywhere** — GATE 2 on a notch has to cover phase and out-of-band gain, not
just depth, because a notch flips phase across itself and that can destabilise frequencies either
side even while the notch attenuates.

