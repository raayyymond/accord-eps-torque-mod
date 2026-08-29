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

