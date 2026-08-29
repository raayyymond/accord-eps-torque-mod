# STATE — living current state of the kit

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

## ✅✅✅ **UN-RETRACTED AND BUILT — V159 REMOVES AN 18 % PARAMETRIC MODULATION OF K_p AT 2f**
🛑 **I over-corrected last turn.** The "parametric pump" finding was **retracted in error**;
decompiling `FUN_0003a382` proves the original layout reading was right.
```c
   X[0] = tp+0x7b1e   X[last] = tp+0x7b24    =>  X is 4 halfwords at 0xC671E
   Y[0] = tp+0x7b26   Y[last] = tp+0x7b2c    =>  Y is 4 halfwords at 0xC6726
   X = [96, 104, 608, 704]        Y = [704, 832, 832, 832]
```
⇒ exactly the "X at base, Y at base+8" layout I first assumed. **The retraction is withdrawn.**
⊕ **What went wrong**: lanes B/C read non-ascending X under the same layout, and I let that anomaly
override **direct instruction evidence** for lane A. **A neighbouring record being unreadable is not
evidence against a record whose layout the decompile confirms line by line.**

### ⭐ THE MECHANISM, CONFIRMED
`FUN_0003a382` is a three-term torque-tracking servo whose **K_p is a LERP on `gp-0x6ac0`, the
RECTIFIED motor rate.** The golden model's **measured** in-burst operating point is
**`gp-0x6ac0` = 99 [94, 113]**, which lies **inside the FIRST segment (X 96 -> 104)** where Y rises
**704 -> 832 = an 18.2 % swing across 8 counts.**
⇒ and a **rectified** index sweeps at **2f**, so during a 7.8 Hz ratchet it traverses that window at
**15.6 Hz**.
⇒ **[EVIDENCE] the PID's proportional gain is PARAMETRICALLY MODULATED ~18 % at 2f at the symptom's
own operating point — STRUCTURALLY, on STOCK.**
⊕ This is the qualitative prediction the golden model made and never located, and a **named
candidate source** for [[accord-v59-parametric-pump-marginal]] (*"the pump is real but MARGINAL"*).

### ✅ V159 — ONE HALFWORD
```
   0xC6728  K_p Y[1]  832 -> 704        Y = [704, 704, 832, 832]
   2 payload bytes, 54/54, CRC 50/50
   image 47ac7932a16334d1a7719e2d0efdd955eef3cc2ab841b7bbb7d6813872389916
   rwd   7c51b28bddba3acfa129cd7a4c0e19efaad8f52ce3928332a66c7b6ccd0f5080
```
✅ **segment 0 becomes FLAT** ⇒ the 2f sweep sees **no gain change**: swing **18.2 % -> 0.0 %**.
✅ **DOWNWARD**: it **lowers** K_p between 96 and 104, so no clamp becomes newly reachable.
✅ **MONOTONE preserved** — the ramp is not deleted, it **moves to X 104..608**, the same 704->832
rise over a **63x wider span**.
✅ **RULE 7 SATISFIED BY STRUCTURE**: the decompile reads this table with **bare `tp` displacements
and NO index register** ⇒ a **flat scalar table shared by all modes**. There is no mode to get wrong.
✅ **VIRGIN**: `0xC6728` = 832 on **all 158 build images**.

### ⚠ WHAT IS NOT ESTABLISHED
⚠ **[BELIEF]** that removing an 18 % parametric modulation is audible. **The mechanism and its
magnitude are EVIDENCE; its share of the symptom is not.**
⚠ **[OPEN]** lanes B (`tp+0x7b0a`) and C (`tp+0x7ade`) read **non-ascending X** under the confirmed
layout (`[256,256,0,8]`, `[717,0,0,5]`). Unexplained, and **left open** — it does not bear on lane A.
⚠ **V159 does NOT close V158's shared-axis GATE 2.** It addresses the **PID side** of that coupling,
not the FactorE side. **V158 and V159 are INDEPENDENT single-lever builds — do not stack them.**

### ✅ THE QUEUE
```
   V158   damper, the golden model's own prescription      shared-axis GATE 2 still OPEN
   V159   K_p 2f modulation removed                        RULE 7 satisfied, virgin, monotone, down
   V148 / V150 / V151                                      probe / grind-#2 / marginal
   V152 / V153                                             GATE-2-OPEN, demoted
   SUPERSEDED  V139 V149 V154 V155 V156 V157
```
⭐ **V159 is the first build of this session derived from a mechanism located in the firmware rather
than from a lever list**, and the only one whose RULE 7 is satisfied *by the instruction encoding*
rather than by a mode table.

## 🛑🛑 **RETRACTED — THE "PARAMETRIC PUMP AT LANE GAIN A" WAS A TABLE-LAYOUT ARTEFACT**
Last turn I reported that lane gain A's knee straddles the measured operating point, giving an 18 %
parametric gain modulation at 2f. **I flagged RULE 7 as unsatisfied and said “verify before
building.” Verified. The finding is WRONG and is retracted in full.**

### 🛑 WHAT THE RAW BYTES ACTUALLY SHOW
```
   halfwords around 0xC671E:
     ... 0, 8, | 64, 65, 67, 73, 80, 88, 96, 104 | 608, 704, 704, 832, 832, 832, 832, 832 | 0, 4 ...
                 \________ one ascending run of 8 ________/
```
⇒ **`0xC671E` = 96 sits in the MIDDLE of that ascending run, not at a record base.**
⇒ my 4-knot reading (`X=[96,104,608,704]`, `Y=[704,832,832,832]`) **straddled the X/Y boundary** —
it paired the tail of the X axis with the head of the Y array. **The whole “steep knee at 99” follows
from that mis-split and nothing else.**
⊕ **The tell was in my own output and I noted it without heeding it**: the same layout gave lanes B
and C the implausible axes `X=[256,256,0,8]` and `X=[717,0,0,5]`. **A layout that produces nonsense on
two of three records is not a layout.**

### ⚠ AND THE PLAUSIBLE READING REVERSES THE CONCLUSION
Read as **count = 8, then X[8] = [64,65,67,73,80,88,96,104], then Y[8] = [608,704,704,832,832,832,
832,832]**, the operating point `gp-0x6ac0` = 99 falls between **X[6]=96 and X[7]=104**, where
**Y[6] = Y[7] = 832 — FLAT.**
⇒ **the gain is FLAT at the operating point, the OPPOSITE of what I claimed**, so there is no 18 %
modulation there at all.
⚠ **This reading is ALSO unverified** — stated as the plausible alternative, not as a finding.

### 🛑 AND I CANNOT VERIFY IT BY SCANNING
The `reg1 == tp` scan returns **NO readers** for `0xC671E`, `0xC670A` or `0xC66DE`. They are reached
some other way — a pointer table, a different base register, or an index computed at runtime.
⇒ **[UNRESOLVED] the layout, the readers and the mode-indexing of all three lane-gain tables.**
⇒ **all three of last turn's lane-gain readings are VOID**, including *“lanes B and C are flat”*.

### ✅ WHAT SURVIVES, AND WHAT THIS COSTS
✅ **The golden model's warning stands**: *"ALL THREE LANE GAINS ARE LERPs INDEXED ON `gp-0x6ac0` …
they are NOT independent … [GATE 2 — size any FactorE edit against this, not just dose]"*. That is
the model's statement, not mine, and it is **unaffected by my error.**
🛑 **So V158's GATE 2 qualification STANDS**: the shared-axis sizing the model demands **has still
not been done**, because **I could not read the tables it refers to.** V158's dose is the model's own
priced figure; **its shared-axis gate remains OPEN.**
⭐ **What this cost: nothing on the car.** The verification step caught it **before** a build — which
is the whole point of having flagged RULE 7 rather than proceeding. **Contrast V156/V157/V149/V139,
where I built first and audited later.**

## ⭐⭐⭐ **THE PARAMETRIC PUMP IS LOCATED — LANE GAIN A's KNEE STRADDLES THE OPERATING POINT**
Mining the golden model for levers (the V158 lesson) surfaced a warning I had not acted on, and
acting on it located a mechanism the kit has hypothesised since V59.

### ⚠ FIRST, A CORRECTION: V158's GATE 2 IS NOT FULLY CLOSED
The model says, of any FactorE edit:
> 🛑🛑 *"**ALL THREE LANE GAINS ARE LERPs INDEXED ON `gp-0x6ac0`** (tp+0x7b1e / tp+0x7b0a /
> tp+0x7ade) — **the SAME rectified motor rate that indexes FactorE.** So a FactorE slope change and
> this PID's own gain schedule move on ONE axis; **they are NOT independent** … **[GATE 2 — size any
> FactorE edit against this, not just dose.]**"*

⇒ **V158 changes FactorE's slope and I priced it by DOSE ALONE.** I have been describing its gate as
*"closed by the model"* — **that was overstated.** The dose is the model's own priced figure; the
**shared-axis requirement was not met.** Meeting it now.

### ⭐ SIZING IT — AND THE RESULT IS A FINDING IN ITS OWN RIGHT
```
   lane gain A  tp+0x7b1e (0xC671E)  X=[96, 104, 608, 704]  Y=[704, 832, 832, 832]
      at gp-0x6ac0 = 94 / 99 / 113  ->  704 / 752 / 832     local slope 6.74 per count
   lane gain B  tp+0x7b0a (0xC670A)  FLAT at the operating point (slope 0.000)
   lane gain C  tp+0x7ade (0xC66DE)  FLAT at the operating point (slope 0.000)
```
🛑🛑 **Lane gain A's FIRST SEGMENT spans X 96 -> 104, and the model's MEASURED operating point is
`gp-0x6ac0` = 99 [94, 113] — DEAD CENTRE.** An **18 % gain swing across 8 counts.**
⇒ and `gp-0x6ac0` is a **RECTIFIED** rate, so during a 7.8 Hz oscillation it **sweeps at 2f =
15.6 Hz** back and forth across that exact window.
⇒ **[EVIDENCE] the PID's lane gain A is PARAMETRICALLY MODULATED at 2f, by ~18 %, at the symptom's
own operating point — and this is STRUCTURAL, present on STOCK.**
⊕ This is precisely what the model predicted qualitatively: *"a rate-scheduled gain on a RECTIFIED
index (which sweeps at 2f) interacts with the parametric pump"* — **now located and quantified.**
⊕ It is also a candidate mechanism for [[accord-v59-parametric-pump-marginal]] (*"the pump is real
but MARGINAL"*), which has never had a named source.

### ✅ THE LEVER THIS IMPLIES — FLATTEN THE KNEE, DOWNWARD
```
   stock   0xC671E  Y = [704, 832, 832, 832]  over X = [96, 104, 608, 704]
   lever            Y = [704, 704, 832, 832]  -- Y[1] := Y[0]
```
⇒ the 96–104 segment becomes **FLAT at 704**, so the 2f sweep sees **no gain change** ⇒ **the
parametric modulation at the operating point is REMOVED.**
⇒ **DOWNWARD is the safe direction**: it **lowers** PID gain between 96 and 104 rather than raising
it, and the ramp simply moves to 104–608, a **far gentler slope over a 6x wider span.**
⇒ **MONOTONE preserved** ([704, 704, 832, 832] is non-decreasing) — the shape rule that V157 broke.
⚠ **[BELIEF] that removing an 18 % parametric modulation is audible.** The mechanism is EVIDENCE;
the magnitude of its contribution is not measured.
⚠ **[UNVERIFIED] `0xC671E`'s reader count, mode-indexing and blast radius** — **RULE 7 is NOT yet
satisfied**, and the three tables' record layout was inferred from a 4-knot pattern that fits lane A
cleanly but produces implausible values for B and C (X=[256,256,0,8] and X=[717,0,0,5]), **so the
layout is probably NOT uniform across the three.** **Verify before building.**

⇒ **NEXT: verify `0xC671E`'s layout, readers and mode-indexing, then build it.** This is the first
new lever since V158 and the first with a named parametric mechanism behind it.

## ✅ **THE AUDIT IS COMPLETE — V150 IS INERT HANDS-OFF, AND THE QUEUE IS FINAL**
V150 was the last unaudited build. Its structure checks out against the golden model, **but its
effect lands outside the symptom's regime.**

### ✅ THE STRUCTURE IS RIGHT
The model confirms the gate exactly as V150's builder describes it:
> *"a hard zero-force gate (**`gp-0x6b5e != 0` AND `assist_state_671a < cal 0xC64FA`**) that r24
> lacks"* · *"**r26 == 0 IFF `gp-0x6b5e != 0`**"*

V150 sets `0xC6136` 0 -> 1, making the state term always true, so the gate reduces to
`gp-0x6b5e != 0`. **That part is correct.**

### 🛑 BUT THE MODEL ALSO SAYS THE GATE DOES NOT FIRE WHERE THE SYMPTOM IS
> *"LEG 1, the GATE — **REVERSED**. r26 == 0 iff gp-0x6b5e != 0, and gp-0x6b5e is a trapezoid LERP on
> gp-0x6bda, a **MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque**. **Hands-off the margin
> sits ~24x above the kill threshold => THE GATE LEAVES r26 LIVE in ordinary driving and most
> strongly live in hands-off creep — exactly where the grinds and the ratchet occur.**"*

⇒ **hands-off, `gp-0x6b5e == 0`**, so the reduced condition `gp-0x6b5e == 0` is **already
satisfied** — r26 is computed exactly as before.
⇒ **[EVIDENCE] V150 changes behaviour ONLY when the driver is applying torque.**
⇒ **V150 is INERT in hands-off creep — the regime of the ratchet and grind #1.** It could only touch
**grind #2** (measured at `tq_avg` 1600–2700, i.e. driver-torque-present).
⇒ **NOT superseded** — it is not harmful and it is a legitimate grind-#2 probe — **but it is
DEMOTED and must not be described as a ratchet lever.**

### ✅ THE FINAL QUEUE, AFTER AUDITING EVERY BUILD AGAINST THE GOLDEN MODEL
```
   FLY      V158   damper, the model's own measured prescription, GATE 2 closed by it
   probe    V148   deadband + gp-0x671E rung -- an INSTRUMENT, explicitly not a fix
   grind#2  V150   inert hands-off; only acts under driver torque
   marginal V151   knee 3000->3600; the relay is already ~99 % unsaturated
   demoted  V152 / V153   GATE-2-OPEN: 0xC40D0 is one of the eight uncertifiable Path-2 coefficients
   SUPERSEDED  V139 · V149 · V154 · V155 · V156 · V157
```

### 🛑 THE AUDIT'S VERDICT ON THIS SESSION'S BUILD WORK
```
   built this session   V139 V148 V149 V150 V151 V152 V153 V154 V155 V156 V157 V158   (12)
   superseded            6      -- two of which would have REMOVED measured fixes
   demoted / inert       4
   survives as a FIX     1      -- V158, the only one designed FROM the golden model
```
⊕ **V149 would have removed Lever B**, the change that flew with *"grinding FIXED"*.
⊕ **V139 was the direction memory records as CAUSING grind #2.**
🛑 **Every failure has one cause: designing from `BUILD-LINEAGE` and fresh decompiles instead of
the GOLDEN MODEL**, which `CLAUDE.md` names as required reading and which already held the
structure, the prescriptions, the strikes, the measured fixes and their gain-dependence.
⭐ **The audit was worth more than the builds it deleted.** **Read `eps_chain_*.py` FIRST.**

## 🛑🛑 **V139 SUPERSEDED — AND THE sar PAIR IS CLOSED AT 6x GAIN, BOTH DIRECTIONS**
The audit reaches V139 (both pump arms `sar 10 -> 11`). It is wrong, **and its own builder already
said so.**

### ✅ THE STATE ON THE CAR
```
   0x3AB76 (r26 arm)  stock imm5 = 10   V122 imm5 = 10    Lever A is NOT carried
   0x3AC20 (r24 arm)  stock imm5 = 10   V122 imm5 = 10
```
⇒ **V62's sar pair — which `eps_lkas_chain_model.py` calls "the kit's ONLY measured grind-#1 fix"
(18-22 Hz down 8-42x) — is ABSENT from the flying build.** The obvious move is to restore it.
**It is not the right move.**

### 🛑 BOTH DIRECTIONS ARE WRONG ON A 6x BASE
```
   sar 9   = DOUBLE the arm   V62's measured fix -- BUT MEASURED ON A 4x-GAIN BASE
                              V133 flew sar 9 on a 6x base => "massive, violent grinding"
   sar 10  = stock, on the car
   sar 11  = HALVE the arm    V139 -- and memory records "r24 HALF CAUSED grind #2"
```
⊕ **V139's own builder contains the decisive argument**, which I should have followed rather than
promoted the build:
> *"scaling V62's 4x optimum to V122's **6x base lands BETWEEN sar 9 and sar 10**, which argues
> Honda sar 10 is already about right for a 6x base and **sar 11 OVERSHOOTS**."*

⇒ **[EVIDENCE, on-car] sar 9 at 6x produced the worst grinding the operator has reported (V133).**
⇒ **[REASONED, in the builder itself] sar 11 overshoots the other way.**
⇒ **=> stock sar 10 is approximately optimal for the 6x base, and the sar pair is CLOSED as a lever
at the current gain.** **V139 SUPERSEDED; do not restore Lever A either.**

### ⭐ THE GENERAL LESSON — THE sar OPTIMUM IS COUPLED TO THE GAIN
V62's result was obtained at **4x LKAS gain**; the car now runs **6x**. **A measured optimum does not
transfer across a gain change**, because the arm's contribution scales with the command that feeds
it.
⇒ **this is why “restore the kit's only measured fix” is the wrong instinct here** — the fix was
measured in a configuration the car no longer has.
⇒ **[RULE] before restoring ANY historical fix, check the gain base it was measured on.** The same
caution applies to every pre-V101 result, since `0xC6CD0` moved 3564 -> 5346 at V101.

### ✅ THE QUEUE AFTER A COMPLETE AUDIT
```
   1. V158   damper, the golden model's own prescription, GATE 2 closed        <-- FLY THIS
   2. V150   r26 suppression switch      premise still unverified after V149's collapse
   3. V148   deadband + probe            an instrument, not a fix
   4. V151   knee 3000 -> 3600           marginal: the relay is ~99 % unsaturated
   -  V152 / V153                        GATE-2-OPEN on 0xC40D0, demoted
   X  V139 / V149 / V154 / V155 / V156 / V157                        SUPERSEDED
```
🛑 **SIX of the builds this session recommended are now superseded.** Every one traces to the same
cause: **designed from `BUILD-LINEAGE` and fresh decompiles instead of the GOLDEN MODEL**, which held
the structure, the prescriptions, the strikes, the measured fix and its gain-dependence all along.
**V158 is the one built from the model, and it is the one that survives.**

## 🛑🛑🛑 **V149 SUPERSEDED — IT REMOVES LEVER B, THE KIT'S ONLY MEASURED GRINDING FIX**
The queue audit against the golden model reaches V149, and this is the worst of the four errors.

### 🛑 MY PREMISE FOR V149 WAS WRONG
I built V149 to *"remove the 5.12x r24 switch"*, describing it as **a fault counter (`gp-0x671d`)
selecting between `cal(0xC6446)=5244` and `cal(0xC6442)=1024` at task rate** — a switching
nonlinearity inside a confirmed pump. **The selector is not a fault counter.**
```
   0x3AA96   stock c5 -> V122 fb     ld.bu -0x683c[gp]  ->  ld.bu -0x6806[gp]
                                     i.e. the flag is gp-0x6806 = LKAS CONTROL ACTIVE
   0xC6446   stock 512 -> V122 5244  the LKAS-gated arm's gain
```
⇒ **the gate is ENGAGEMENT, not a counter.** It toggles on engage/disengage, **not at 1 kHz**.
**There is no task-rate switching nonlinearity here, so V149 has nothing to remove.**

### 🛑🛑 WORSE: 5244 IS THE FIX, AND V149 DELETES IT
The golden model describes this exact pair as **the grind #1 fix**:
> *"**THE FIX: V67 = V66 + the grind #1 fix GATED ON LKAS.** Two edits, no cave: `0x3AA96 c5 -> fb`
> + `0xC6446 512 -> 5244` … its flag `lp` already selects cal `0xC6446` for r24 — **the firmware
> already HAS a conditional-gain arm and it is merely wired to a dead cell.** Repointing it makes the
> gain conditional **with no code cave, this kit's only bricking class.**
> gate FALSE (LKAS off) -> the LERP, unchanged => **byte-for-byte STOCK base steering**
> gate TRUE (LKAS on) -> flat 5244 = **2.00x the LERP at grind #1's operating point**"*

⊕ And the memory record: **V88 = “Lever B restored” is the build that FLEW with “grinding FIXED”**
([[accord-v88-flew-grinding-fixed-command-intact]]), and
[[accord-v81-carries-neither-grind1-fix]] calls Lever B **“best in kit”**.
⇒ **[EVIDENCE] Lever B is ACTIVE on the flying build (`0x3AA96` = `fb`, `0xC6446` = 5244), and
V149 sets 5244 -> 1024, collapsing the gated arm to the ungated value.**
⇒ **V149 REMOVES THE ONLY CHANGE THIS KIT HAS EVER MEASURED AS FIXING GRINDING.**
⇒ **SUPERSEDED. `.rwd` renamed. It must never be flown.**

### ⚠ AND V152/V153 CARRY THE SAME OPEN GATE 2 AS V154/V155
`tp+0x50d0` = **`0xC40D0`** is **one of the eight Path-2 loop-gain coefficients** the golden model
names as *"NEVER BYTE-READ"* and on which **GATE 2 cannot be certified**. **V152/V153 move it.**
⊕ **Their argument is better than V154/V155's**: a *pure added low-pass* lowers HF loop gain, which
is directionally stabilising, whereas a weight change had an **unresolved sign**.
⚠ **But it is still not a certification** — a low-pass also adds phase lag, and phase margin cannot
be checked without the loop gain, which needs the RAM LERP slope that `FUN_000389ec` has defeated
twice.
⇒ **V152/V153 are NOT superseded, but they are DEMOTED and flagged GATE-2-OPEN.** They must not be
flown ahead of V158, whose gate is closed by the model's own priced prescription.

### ✅ THE QUEUE AFTER THE AUDIT
```
   1. V158   damper, the golden model's own prescription      GATE 2 closed by the model     FLY THIS
   2. V139   both pump arms halved                            not yet audited
   3. V150   r26 suppression switch                           premise deserves re-checking after V149
   4. V148   deadband + probe                                 instrument, not a fix
   5. V151   knee 3000 -> 3600                                marginal, relay ~99 % unsaturated
   -  V152 / V153   observer poles                            GATE-2-OPEN, demoted
   X  V149 / V154 / V155 / V156 / V157                        SUPERSEDED
```
🛑 **FIVE of the builds I recommended this session are now superseded, all for the same root
cause: designed from `BUILD-LINEAGE` and my own decompiles instead of the GOLDEN MODEL**, which
`CLAUDE.md` names as required reading and which already contained the structure, the prescription,
the strikes and the fix.

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

