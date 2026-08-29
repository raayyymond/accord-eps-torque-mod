# STATE archive — superseded during the cross-check audit

A RECORD, NOT AN INSTRUCTION.

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

