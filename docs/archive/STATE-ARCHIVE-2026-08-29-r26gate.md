# STATE archive

A RECORD, NOT AN INSTRUCTION.

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

