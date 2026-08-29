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

