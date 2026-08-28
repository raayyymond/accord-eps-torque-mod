# STATE — living current state of the kit

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

## 🛑🛑 **RETRACTION: THE "8× vs GRINDING" TRADE IS NOT SUPPORTED — I OVERSTATED IT**
Last section I told the operator his two standing instructions *"cannot both be satisfied"*, on
the strength of `grind ~ command magnitude` (within-drive) plus the standing `m^1.74`. **I then
tested the gain effect directly and it does not hold up.**

### THE DIRECT TEST — a clean natural experiment in the cache, and it is NULL
The cache contains **12 routes at two gains with α2 HELD at 22**, which de-confounds gain from α2:
`4× = r77 r78 r79 r85 r96 r97` · `6× = r1e ra4 ra5 ra6`.
```
   6x / 4x, engaged, 25-64 km/h, bootstrapped over ROUTES
      21-26 Hz GRIND    1.252 [0.297, 2.304]   NULL
      30-40 Hz CONTROL  0.874 [0.320, 1.545]   NULL
      m^1.74 predicts 2.02x -- ALSO inside the CI
```
🛑 **Per-route 21–26 Hz share spans 0.047–0.389 WITHIN the same gain group — an 8× spread.**
Route variance swamps the comparison; the test can neither confirm nor refute `m^1.74`, and its
**point estimate 1.252 sits well below it.**

### ✅ AND THE MECHANISM I MISSED: OPENPILOT IS A CLOSED LOOP
Within a drive, more command ⇒ more grind **at fixed gain**. That does **not** transfer to
"more gain ⇒ more grind" **because openpilot compensates** — with more EPS gain it needs **less
command** for the same steering:
```
   6x / 4x, over routes
      |e4tq| p50  (command)    0.733 [0.320, 1.210]   NULL   <- full compensation predicts 0.667
      |e4tq| p90  (command)    0.903 [0.334, 2.763]   NULL
      |rate| p50  (achieved)   1.867 [0.711, 5.111]   NULL
```
**Point estimates are directionally consistent with compensation** (command falls 0.733× against a
predicted 0.667× while achieved rate rises) — **but every CI spans 1.** Underpowered, again.

### 🛑 WHAT I GOT WRONG, PRECISELY
✘ *"6× → 8× = 1.65× more grinding"* — **NOT MEASURED.** It was `m^1.74` applied to a gain ratio;
the only direct test of that exponent is **null with a CI from 0.30 to 2.30.**
✘ *"His two instructions cannot both hold"* — **RETRACTED.** There is **no measured evidence that
8× increases grinding.**
✔ What survives: **within a drive, at fixed gain, grind tracks command magnitude** (3/3 drives,
band-specific, controls flat or opposite). That is a statement about *when* grind appears, not
about *what a gain change does.*
⇒ **→ NO 6× VARIANT IS WARRANTED. 8× STANDS**, as the operator instructed, and the authority work
in V124–V133 carries no demonstrated grinding cost.

### ⭐ THE DEEPER LESSON, WHICH IS THE SESSION'S MOST REUSABLE ONE
**A within-unit association does not license a between-unit causal claim** — especially across a
**feedback loop**, where the controller absorbs the very change being tested. I made exactly that
leap, and the loop was openpilot. ⊕ It is also why **every** between-build ratio in this kit needs
its route-variance null first: **8× within-group spread** makes n≈4 routes powerless to see a 2×
effect.

## 🛑🛑🛑 **GRIND TRACKS COMMAND *MAGNITUDE*, NOT ITS RATE — SO THERE IS NO NON-CONFLICTING LEVER**
Excitation-driven splits into two very different prescriptions:
- if grind tracks the command's **MAGNITUDE** ⇒ only cutting **GAIN** helps — **conflicts with
  authority**;
- if it tracks the command's **RATE or HF content** ⇒ **smoothing** helps — **does not conflict**.
Tested on three drives, 25–64 km/h engaged, each with its 30–40 Hz control:
```
   drive        command MAGNITUDE      30-40 Hz control      reading
   r24 (V122)   1.630 [1.356,2.040]   0.817 [0.580,0.949]   signal UP, control DOWN
   r1e (V107)   1.738 [1.311,2.201]   1.155 [0.969,1.372]   signal UP, control flat
   r22 (V112)   1.434 [1.071,2.080]   0.525 [0.345,0.648]   signal UP, control DOWN
```
✅ **Command MAGNITUDE predicts grind on ALL THREE drives** (1.63 / 1.74 / 1.43), with the control
flat or moving the **opposite** way. **Command RATE is inconsistent** (up on r24/r22, **down** on
r1e, 0.543), and **HF fraction is inverse** — which is just magnitude seen through a normalisation
(high HF fraction ⇔ low DC).
⇒ **[EVIDENCE] grind #1 scales with the DELIVERED COMMAND MAGNITUDE.**
⇒ **Smoothing the command would NOT help.** The only lever that reduces grind is the one that
reduces delivered magnitude: **the forward gain.**

### 🛑 A CORRECTION TO MY OWN VERDICT LOGIC, MADE HERE RATHER THAN LEFT STANDING
The first pass marked a cell *"confounded"* whenever the control's CI merely excluded 1 — including
cases where the control moved **opposite** to the signal. That is backwards: **a control moving the
other way is STRONGER band-specificity, not a confound.** Under the corrected reading, magnitude is
band-specific on **3 of 3** drives rather than 1 of 3. ⊕ The rule that still holds is the one that
killed the relay story: **a confound is when signal and control move the SAME way** (the relay's
control was 1.260 against a 1.205 signal — same direction, larger).

### 🛑 THE TRADE IS NOW FULLY SPECIFIED, AND IT IS THE OPERATOR'S TO MAKE
```
   grind ~ (delivered command magnitude)             measured, 3/3 drives, band-specific
   vibration ~ m^1.74                                 standing record
   =>  6x -> 8x  =  1.65x MORE grinding
   =>  8x -> 6x  =  0.61x grinding, at 0.75x command authority at the rail
```
⚠ His two standing instructions — *"just go to 8× IF you decide to increase LKAS gain"* and
*"If you're going to increase gain make sure we don't get even more oscillation and grinding"* —
**cannot both be satisfied by a gain change.** That is not a failure to find a lever; it is the
lever's measured cost. **V124–V133 all carry 8× by his instruction.**
✅ **A 6× variant is a TWO-CELL edit** (`0xC6CD0` 7128→5346 + clamps `0xC61B2/B4` 4096→3072, ratio
held at exactly 1.000) and can be cut in minutes **if he chooses grinding over authority.**

### ✅ WHAT STILL REDUCES GRIND WITHOUT TOUCHING THE COMMAND
**Only V62's Lever A** — the rate-lane `sar`, restored in V133, the one grind lever in this kit's
record with band-specific evidence that **passed its own control** (18–22 Hz 0.124 [0.036, 0.387];
30–40 Hz control ~1.0). ⇒ **that is why V133's Lever A restore, not its ceiling raise, is the
build's real content** — and it is the only thing on the table that improves grinding at **zero
authority cost.**

## ✅✅✅ **GRIND #1 IS EXCITATION-DRIVEN — THE COMMAND PREDICTS IT, BAND-SPECIFICALLY, ON TWO DRIVES**
With the relay hypothesis dead, I screened **every channel in the cache** against 21–26 Hz power —
engaged, restricted to **25–64 km/h (the operator's own grinding band)**, high-30 % vs low-30 % of
each predictor, **with the 30–40 Hz negative control beside every single one.**
```
   drive        predictor        21-26 Hz hi/lo         30-40 Hz CONTROL       verdict
   r1e (V107)   e4 torque cmd   1.346 [1.027,2.047]   1.008 [0.694,1.387]   BAND-SPECIFIC
   r24 (V122)   e4 torque cmd   1.469 [1.132,1.905]   0.895 [0.556,1.161]   BAND-SPECIFIC
   r22 (V112)   e4 torque cmd   1.153 [0.863,1.815]   0.757 [0.583,0.958]   control moves -> uninformative
   r1e (V107)   driver torque   0.628 [0.422,0.742]   0.870 [0.644,1.306]   BAND-SPECIFIC (INVERSE)
```
✅ **The LKAS torque command predicts grind-band power on 2 of 3 drives, and the third is
uninformative rather than contradictory** (its control moved, so nothing can be read from it).
⊕ **Driver torque runs the other way** — more driver torque, **less** grind — matching
[[accord-fprime-compression-explains-v89-and-v97]] and the recorded grip-damping result. Two
independent, oppositely-signed, band-specific effects is a much stronger pattern than one.

### ⭐ THIS EXPLAINS WHY TWELVE BUILDS OF DAMPING WORK DID NOT CLOSE IT
- the **damping lanes are structurally capped** (`gp-0x6b26` at its ±1024 gate bound; `gp-0x6bd0`
  already saturating on stock);
- the **relay story fails its own negative control** (previous section);
- and the thing that **actually predicts the symptom is the COMMAND.**
⇒ **grind #1 is EXCITATION-limited, not damping-limited.** This is exactly V87's flight
conclusion (*"a lightly-damped mode driven by broadband command content"*) and
[[accord-the-8x-gain-is-the-carrier]] — **now reproduced independently, band-specifically, on two
further drives.**

### 🛑 AND IT PUTS THE THREE COMPLAINTS IN A MEASURED CONFLICT
The **8× forward gain** that V124+ carries **for LKAS authority** is the same knob that scales
grind excitation. The record puts the vibration at **`m^1.74`**, so **6× → 8× ≈ 1.65× more
grinding**. ⇒ **the authority fix and the grinding fix pull in opposite directions, and that is
now measured rather than argued.**
⚠ The operator's standing instructions are explicit — *"just go to 8× IF you decide to increase
LKAS gain"* and *"If you're going to increase gain make sure we don't get even more oscillation and
grinding."* **Those two cannot both be fully satisfied by a gain change**; the honest framing is a
trade, and the trade is his to make.
⊕ **What does NOT conflict**: V62's Lever A (restored in V133) reduces grind **without touching
the command**, which is precisely why it is the most defensible content of the build.

### 🛑 WHAT REMAINS, GIVEN THE MECHANISM
Reducing **delivered HF excitation without cutting DC authority** is the only non-conflicting
lever class — and this session already established **no calibration implements it** (no notch, no
biquad, and the shaper/integrator region reads no filter cal). The two HF-reduction cals that DO
exist are **already used**: α2 `0xC40DC` at 5 and the trim IIR `0xC63D2` at 3.
⇒ **There is no further calibration lever for grinding that does not cost authority.**

## 🛑🛑🛑 **THE RELAY HYPOTHESIS FAILS ITS OWN NEGATIVE CONTROL — THE BIGGEST NEGATIVE OF THIS SESSION**
`r1e` carries **both** `gp-0x6c2c` (so per-window b26 rail duty computes exactly) **and** `cs_rate`
(so 21–26 Hz power measures directly). That is a **within-drive test of the whole relay story**,
and it had never been run.
```
   stratum      band               ratio [95 % CI]        verdict
   0-25 km/h    21-26 Hz GRIND     1.283 [0.868, 2.680]   NULL
                30-40 Hz control   1.361 [1.051, 2.063]   DIFFERENT   <- CONTROL MOVED MORE
                6-9 Hz ratchet     1.839 [0.712, 4.164]   NULL

   25-64 km/h   21-26 Hz GRIND     1.205 [1.003, 1.650]   DIFFERENT
                30-40 Hz control   1.260 [0.976, 1.512]   NULL        <- LARGER POINT ESTIMATE
                6-9 Hz ratchet     1.080 [0.821, 1.258]   NULL
```
🛑 **In BOTH strata the control band moves as much as or MORE than the grind band.** The 1.205
at 25–64 km/h reads as significant in isolation — until you see the control's point estimate is
**1.260**, larger. ⇒ **railed windows are BROADBAND rougher, not grind-band specific.**
⊕ The pooled comparison was worse still: railed windows median **25 km/h** vs non-railed **68**,
and the pooled control ran **0.610 [0.495, 0.735]** — a huge speed confound.

### ⚠ WHAT THIS COSTS — stated against my own work
⇒ **[EVIDENCE] `gp-0x6b26` railing does NOT specifically explain grind #1.** That premise drove
**V126, V127, V129, V130, V132 and V133's ceiling raise.** The builds are not *wrong* — they are
bounded, verified, and harmless — but **the reason I gave for them is not supported.**
⊕ This is the kit's own rule firing on me: [[feedback-run-the-control-before-the-measurement]]
— *"four claims died to controls in one session."* **Five, now.** And note the direction: every
single-band number I quoted this session about railing (32.32 %, the 9.31 %, the 1.205×) looked
compelling until a control ran beside it.

### ✅ WHAT SURVIVES — and it is the thing V133 actually restores
**V62's Lever A is the ONLY grind lever in this kit's record with band-specific evidence that
passed its control**: 18–22 Hz **0.124 [0.036, 0.387]** (8×) and **0.024 [0.016, 0.234]** at
|rate| 16–32 °/s (42×), **with a 30–40 Hz negative control at ~1.0** — i.e. the effect was
demonstrably confined to the band, which is exactly what the relay hypothesis just failed to do.
⇒ **V133's most defensible content is not the ceiling raise — it is the restored Lever A**, which
had been off the car since ~V80 behind a guard that asserted its own absence.

### 🛑 WHERE GRINDING'S MECHANISM NOW STANDS
- **b26 relay** — ❌ **fails its negative control** (this section)
- **damping headroom** — ❌ exhausted; both lanes capped, `gp-0x6bd0` already saturating on stock
- **HF filtering of the command** — ❌ no calibration implements it
- **rate lane (Lever A)** — ✅ **the one mechanism with a passing control; restored in V133**
- **excitation (the 8× gain)** — ⚠ known carrier, fixed by operator instruction
⇒ **The honest position: grinding's mechanism is not established, one lever has real band-specific
evidence, and V133 carries it.** Further calibration search is not the bottleneck — a drive that
scores V133 against V122 with a negative control is.

## ✅✅✅ **THE FORK IS SETTLED — FROM CACHED DATA, WITHOUT A DRIVE. V130 IS REFUTED AND DELETED.**
`r1e` (V107) carries **`gp-0x6c2c` measured on the wire**, and `b26 = clamp((c2c·Y>>6)·273>>18,
±511)` is exact arithmetic. So the rail duty of **any `Y` record** can be computed on **real
measured input** — not extrapolated. **V106 and V107 share α2 = 22 AND the 6× gain**, so the V106
row is near-exact, and V106 is the build that **EXTINGUISHED the mode**.
```
   build                     0-10    10-25    25-40    40-64
   STOCK   (V90 era)        0.00%    0.00%    0.00%    0.00%
   V106    EXTINGUISHED     6.52%    0.97%    0.00%    0.00%
   V107    WORST build      7.27%    9.31%    7.72%    1.90%
   V133    on the car       6.52%    0.97%    0.00%    0.00%   <- ALREADY V106's profile
   V129    Y[2] -> -5898    6.52%    0.97%    0.00%    0.00%   <- IDENTICAL in this range
   V130    Y[1]/Y[2] x1.856 8.37%   14.87%   13.51%    7.76%   <- WORSE THAN V107
```

### ✅ RAIL DUTY *DOES* DISCRIMINATE — and it points the opposite way to the pre-registered rule
**V107 rails ~10× V106 across 10–40 km/h**, exactly the operator's grinding band (15–40 mph =
24–64 km/h). **V107 was the worst build in the modern lineage; V106 extinguished the mode.**
⇒ **more railing = worse**, and since railing rises with `Y`, **more `Y` = worse.**
🛑 **V130 would rail 14.87 % / 13.51 % — worse than V107.** The pre-registered rule said
*"≤ 2 % ⇒ the term is LINEAR ⇒ the deficit is DAMPING ⇒ fly V130 (`Y` up)"*. That rule rested on a
**structural** argument; the **measured ladder refutes it.** ✅ **V130's artifacts are DELETED.**
⊕ **Better evidence beats a pre-registration.** The pre-registration was right to fix the endpoint
in advance; it was wrong about which direction a low duty implies, and the ladder settles it.

### ✅ AND V133 IS **ALREADY AT THE MEASURED-GOOD CONFIGURATION**
`V112/V133`'s `Y` = `[-29490, -17202, -16000]` differs from V106's only at **`Y[2]`, the 90 km/h
knot** ⇒ **through the entire grinding band the two are IDENTICAL**, and the computed duties agree
to the digit. ⇒ **V129 buys nothing measurable**: its only change is above ~64 km/h.
⚠ **The 64–200 km/h column is UNINFORMATIVE for both** — at `Y[2]` = 16000 the rail threshold is
**1963**, and at 5898 it is **5325**, both **above the wire's 1637 clip** ⇒ the 0.00 % there is a
**measurement limit, not a result.** V129 remains a *reasonable* high-speed hypothesis; it is
simply **not supported or refuted by this data.**

### ⭐ WHAT THIS CHANGES
- **V130: REFUTED and deleted.** It would have been flown on a rule that better data overturns.
- **V129: demoted to a high-speed-only hypothesis**, unmeasurable from the current cache.
- **V133: confirmed to sit at V106's rail profile through the whole symptom band** — i.e. at the
  only configuration this kit has ever measured extinguishing the mode.
- 🛑 **The fork no longer needs a drive to choose a branch.** What a V133 drive is still for:
  **the operator's symptom report**, and confirming the duty under V133's own α2 = 5 (all rows
  above use V107's α2 = 22 `c2c`, which is the one thing that does not transfer).

## 🛑🛑 **THE OSCILLATION DETECTOR'S THRESHOLD IS ~11× THE OBSERVED p90 — `0xC640A` MAY BE INERT**
Applying the r77 lesson — *check what the kit already flew* — to the rest of the 427 tap history:
```
   v100/101  0x946C = gp-0x6B94 (aggregator out)   v102/103  0x94B4 = gp-0x6B4C
   v104-106  0x947A = gp-0x6B86 (biquad lane)      v107-110  0x93D4 = gp-0x6C2C
   v118/119  0x9806 = gp-0x67FA (state gate)
```
**V107–V110 put `gp-0x6c2c` on the wire** — the damper's input **and the oscillation detector's
input** — and **`r1e` is V107**. That directly tests whether V127/V133's `0xC640A` edit can fire.

### 🛑 THE MEASUREMENT, AND ITS HONEST LIMIT
```
   route 1e = V107, 427 <- gp-0x6c2c, sar 3 (LSB 1.6), 48,047 engaged frames
   |gp-0x6c2c| ENGAGED   p50 125   p90 1170   >= 1637 (the WIRE rail) in 3.15 % of frames
   the DETECTOR arms at cal(0xC620A) = 12800  --  7.8x ABOVE what the wire can represent
       0-10 km/h 2.52 %   10-25 4.06 %   25-40 4.34 %   40-64 1.47 %   64-200 3.67 %
```
🛑 **The arming threshold sits ~11× above p90.** Because 3.15 % of frames **clip at 1637**, I
cannot see how far those go ⇒ **P(arming) is NOT measurable from r1e; it is BOUNDED at ≤ 3.15 %**,
and the steep unclipped distribution (p50 125 → p90 1170) makes 12800 look unlikely — **but that
is an inference, not a measurement.**

### ⚠ THE CONSEQUENCE, AGAINST MY OWN BUILDS AGAIN
⇒ **The `0xC640A` oscillation branch may be taken almost never**, which would make **V126/V127's
central premise — and that part of V133 — close to INERT.** ⊕ This is exactly what
`SCORING-V131-preregistered.md` already warned about in its confounds section (*"if the drive
contains no oscillation episode the counter never saturates and `0xC640A` is inert by
construction"*) — **but I had treated that as a drive-planning caveat, not as the likely
steady state.** It is now the likely steady state.
⚠ V107 ran a **6×** forward gain; V133 runs **8×**, so its `|c2c|` is larger — by how much is the
same closed-loop question the record forbids extrapolating.

### ✅ WHAT WOULD SETTLE IT — and it is cheap
A `gp-0x6c2c` probe at **sar 6** instead of sar 3: `wire = (|c2c|·5)>>6` puts **12800 → wire 1000**
of 1023, so the arming threshold becomes **directly visible** instead of 7.8× off-scale. That is a
**one-byte** change to the packer (`0x55E10`) plus the tap displacement — the same 2-byte edit
class as V127's probe, no cave, no new instructions.
🛑 **But it costs the `gp-0x6b26` rail measurement**, which decides the V129/V130 fork. One wire,
one signal. ⇒ **Not built: the fork is the higher-value question**, and r77 already showed the b26
term linear at 0.0000 % under a different configuration.

⊕ **Running score of the "check the cache first" lesson: two sessions-worth of open questions
answered from data already on disk** — the b26 rail duty (r77) and now the detector-threshold
bound (r1e). **Neither needed a new drive.**

## 🛑🛑🛑 **THE DAMPER NEVER RAILED — A DIRECT MEASUREMENT THAT WAS SITTING IN THE CACHE**
Route **77 = V90**, which put **`gp-0x6b26` on 427 at sar 3** — the same tap V133 carries. The data
has been on disk the whole time. **52,258 engaged frames, wire unclipped** (it saturates at 1637,
the clamp is 511):
```
   ENGAGED   p50 5   p90 35   p99 109   max 296        RAIL DUTY 0.0000 %
    0- 10 km/h  p99 147  max 275  0.0000 %      25- 40 km/h  p99  80  max 296  0.0000 %
   10- 25 km/h  p99  95  max 293  0.0000 %      40- 64 km/h  p99  76  max 250  0.0000 %
   64-200 km/h  p99  59  max 146  0.0000 %
```
🛑 **The term NEVER reached its clamp — not one frame, in any speed bin.** p99 is **21 %** of it.

### 🛑 AND IT CONTRADICTS THE 32.32 % THAT MOTIVATED THE WHOLE RELAY STORY
V107's *"32.32 % rail duty at 10–25 km/h"* — cited repeatedly this session, including by me — was
**RECONSTRUCTED**, not measured (`accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it`:
*"Reconstructed `P(|gp-0x6b26| = 511)`"*). **The direct wire reads 0.0000 % in that exact bin.**
⇒ **[EVIDENCE] the kit's first DIRECT measurement of this term's rail duty is ZERO.**

### ⚠ TWO CONSEQUENCES I HAVE TO STATE AGAINST MY OWN BUILDS
1. **The "railed → Coulomb relay → grinding" premise for `gp-0x6b26` is WEAKENED**, and with it part
   of the reasoning behind V126–V133.
2. **V133's headline edit — the 511→1023 ceiling raise — may be INERT.** If the term never
   approaches 511, doubling the clamp changes nothing. ⊕ It is still **harmless** (strictly more
   headroom, monitor twin matched, admission gate cleared), but it may buy nothing.

🛑 **WHAT THIS DOES *NOT* ESTABLISH.** V90 ran **stock `Y`** (pre-V106 ×3) and **α2 = 22**;
V133 runs **×3 `Y`** and **α2 = 5**. Scaling V90's distribution to V133 is **exactly the open-loop
move the record forbids** — V107 predicted ≤1.05 % and measured 33.49 %, a **32× miss**, doing
precisely that. ⇒ **this SHIFTS THE PRIOR, it does not settle it.**

### ⭐ IT DOES, HOWEVER, POINT THE FORK
The pre-registered rule reads: **rails ≤ 2 % ⇒ the term is LINEAR ⇒ the deficit is DAMPING ⇒ fly
V130 (`Y` up)**. The only direct evidence now available reads **0.0000 %**. ⇒ **V130 becomes the
favoured branch**, and `0xC63A6` — the weight that adds authority past the ceiling — becomes the
*likely* next lever rather than the unlikely one. **Both remain gated on V133's own probe**, which
measures the term under V133's actual `Y` and α2.
⊕ And a method lesson: **the answer to the session's central question was already in the cache.**
Before designing a probe, check whether a past build already flew the signal — `r77` carried it
with the identical tap and scale.

## 🛑🛑 **THE BASE-ASSIST DAMPER IS *ALREADY* A RELAY — THE LANE CLOSES, AND V80 IS EXPLAINED**
I promised to read `FUN_00034350`'s ceiling before choosing any FactorC dose. **Read — and it
blocks the dose.**
```c
   uVar7  = ((((FactorB clamped to 1024) * FactorC >>10) * FactorD >>10) * FactorE >>10) * FactorF >>10;
   uVar10 = LERP(gp-0x6ac2)[mode]   or   cal(tp+0x7158) = 45496       // <- THE CEILING
   gp-0x6bd0 = clamp(uVar7, +- uVar10)                                // saturate -> CONSTANT magnitude
```
```
   ceiling LERP (&PTR_DAT_000c77a0)[mode]:  modes 24/25/26/27 ALL  X=[300,800]  Y=[512,1024]
   stock product at FactorC's top knot:      ~2216   =>  over 2x the ceiling
```
🛑 **The damper output is clamped to 512–1024, and the product already exceeds it** ⇒ **the
base-assist damper is ALREADY SATURATING at high speed ON STOCK** — already a relay there.
⇒ **raising FactorC does not add damping; it WIDENS THE RELAY REGION.**

⭐ **THIS IS THE MECHANISM BEHIND V80's RESULT.** V80 flattened FactorC to a constant 566, pushed
the product further past this ceiling, and measured **the worst grinding in the kit's record**
([[accord-v80-damper-relay-and-grind1-inert]]). Its own note — *"the no-clip gate is blind to
`= ceiling − 17`"* — is exactly this clamp. **The lane behaves identically to `gp-0x6b26`: the
term's authority is capped, and pushing past the cap converts damping into ratcheting.**
⚠ **HONESTY**: my FactorE read came back `X=[140,539,927,0]`, and the trailing `0` says the field
offsets are off by one ⇒ **2216 is APPROXIMATE**. The ordering conclusion is robust anyway: the
ceiling is **512–1024** while single factors alone reach **908–2500**.

### ✅ SO THE LANE CLOSES — unless the CEILING is raised, which is a separate build
To make this a *linear* damper at 21–26 Hz the **ceiling** must rise, not FactorC — the same move
as the `gp-0x6b26` clamp, and it needs its own admission/monitor analysis (`gp-0x6bd0` has an
int shadow `gp-0x4cf2` and a ±2048 admission gate in `FUN_00038148`). **Not attempted here.**
⊕ What the task-5 result still buys: **the rate objection is dead** (≥ 250 Hz, Nyquist ≥ 125 Hz),
so if that ceiling is ever raised, the damper **can** act in the grind band. **The blocker moved
from "wrong physics" to "capped authority" — a better-understood problem.**

### 🛑 EVERY DAMPING LANE IN THIS FIRMWARE IS NOW CAPPED THE SAME WAY
| term | cap | state |
|---|---|---|
| `gp-0x6b26` | clamp `0xC407E` + ±1024 admission gate | **at max** (V133: 1023/1.0) |
| `gp-0x6bd0` (base assist) | per-mode LERP ceiling **512–1024** | **already saturating on stock** |
⇒ **Honda caps both damping terms, and both are at or past their caps.** That is the structural
reason grinding has resisted twelve builds: **the firmware has no headroom left to damp with**,
and every attempt to force more converts a damper into a relay — measured three times now
(V74/V75, V80, V107).

## 🛑🛑🛑 **TASK 5 IS ≥ 250 Hz — THE BASE-ASSIST DAMPER *CAN* ACT AT 21–26 Hz. THE LANE RE-OPENS.**
The one avenue recorded as *neither closed nor sized*. **Now bounded, from flown data.**

### ✅ THE STRUCTURE — the TCB table, both entries located
`FUN_00034350` (the base-assist damper) has exactly one caller, `FUN_00022ca0`, which itself has
**no callers** ⇒ it is a **task entry**, dispatched from a table. Both it and the **confirmed
1 kHz** task appear in one TCB array, stride **0x60**:
```
   task 1 (CONFIRMED 1 kHz)          task 5 (rate was OPEN)
   0xBB924  0x00010607               0xBB9E4  0x00050207     id | a | b
   0xBB928  0x0002214A  entry        0xBB9E8  0x00022CA0  entry
   0xBB934  0x00000000               0xBB9F4  0x00000004    <- differs
```
🛑 **That is STRUCTURE, NOT A RATE.** Inferring a period from field positions is *exactly* the
error the 2026-08-12 retraction documents (the RTOS handler was identified on an **address
coincidence**). **I did not do it.**

### ✅ THE RATE, BOUNDED EMPIRICALLY — TWO STATISTICS, BOTH FROM FLOWN DATA
`gp-0x6bbe`'s outer EMA has a **known** coefficient, α = 205/1024, and route 79 (V92, 220 windows /
19 episodes) measured its transfer at **≈ −1.2 dB** across 6–9 Hz with a step τ in **[0, 20] ms**:
```
   task rate    6 Hz   7.79 Hz    9 Hz    vs -1.2 dB              tau      vs <= 20 ms
    100 Hz     -5.80    -7.55    -8.58    EXCLUDED, off 6.1 dB   50.0 ms   EXCLUDED
    200 Hz     -2.32    -3.40    -4.12    EXCLUDED, off 2.1 dB   25.0 ms   EXCLUDED
    250 Hz     -1.62    -2.46    -3.05    close                  20.0 ms   OK
    500 Hz     -0.47    -0.76    -0.99    CONSISTENT             10.0 ms   OK
   1000 Hz     -0.12    -0.20    -0.27    close                   5.0 ms   OK
```
⇒ **TASK 5 ≥ 250 Hz, best fit 500 Hz** ⇒ **Nyquist ≥ 125 Hz** ⇒ **the base-assist damper CAN act
at 21–26 Hz.** The *"structurally cannot damp the 20.9 Hz mode"* claim is no longer merely
retracted — it is **empirically EXCLUDED**, by a frequency-domain and a time-domain statistic.
⚠ **Load-bearing assumption**: that `gp-0x6bbe`'s outer EMA lives in task 5. That link was made by
the prior session's retraction, not re-derived here. The two statistics share one route, so they
are **different estimators on common data**, not independent samples.

### ✅ AND THE DAMPER IS AT HONDA'S STOCK CALIBRATION, WITH A DEAD ZONE OVER HALF THE SYMPTOM BAND
```
   FactorC m26   X = [2240, 3840, 5120, 8960] counts = [35.0, 60.0, 80.0, 140.0] km/h
                 Y = [   0,  234,   429,  908]
   V80 modified it (Y flat 566); V84 REVERTED to Honda's; stock ever since, V133 included.
```
🛑 **Below 35 km/h FactorC = 0 ⇒ the damper is DEAD across 24–35 km/h**, the lower half of the
operator's 15–40 mph grinding band, and merely ramping up through the rest.

### ⭐ THE CANDIDATE — and the gate it must pass first
**Raise `FactorC` `Y[1..3]` while KEEPING `Y[0] = 0` and the monotone ramp.**
🛑 **V80 already proved the wrong version of this**: it flattened `FactorC` to a constant **566**
— a **PLATEAU, i.e. a RELAY** — and produced **the worst grinding in the kit's record**
([[accord-v80-damper-relay-and-grind1-inert]]). Its own prescription is the design rule:
***"Restore the RAMP, don't merely lower k."*** Likewise V74/V75 made `FactorE` a relay via
`Y[1] := Y[2]`. ⇒ **any edit here must preserve strict monotonicity and create no plateau.**
🛑 **THE GATE, NOT YET RUN**: `FUN_00034350` carries a **ceiling clamp**
([[accord-damper-evaluator-fun34350-ceiling-clamp]]). Raising `Y` without checking that the
product `ch0 = (FactorC × FactorE) >> 10` stays **below** it would recreate a relay by saturation
— **the identical failure mode as `gp-0x6b26`, on a different term.** ⇒ **the ceiling must be read
and the product bounded BEFORE any dose is chosen.** Not done here; named as the next step.

## 🛑🛑 **THE CALIBRATION SEARCH FOR GRINDING IS NOW BOUNDED — AND V133 IS ITS ENDPOINT**
V87's flight fixed the lever class: *"a lightly-damped mode driven by **broadband command
content**, not a commanded tone ⇒ the lever class is **less broadband HF in the delivered
command**, NOT a notch."* Enumerating the delivered path with the now-reliable census closes it.

### ✅ THE DELIVERED SHAPER/INTEGRATOR PATH HAS **NO FILTER CAL AT ALL**
Every genuine tp-relative cal read in `[0x43100, 0x43280)` — the region carrying
`gp-0x6acc → shaper → gp-0x6b08 → integrator → gp-0x6b98`:
```
   0xC41E0  257      0xC47F0  0       0xC61DC  30720   SM3 arm threshold -- known, DO NOT TOUCH
   0xC64C8  0        the MODE SWITCH: mode 1 DISCARDS the aggregator for a static cal -> WORSE
   0xC61D4  0        adjacent to 0xC61D6, the slew cell V16 was REJECTED for: 0 -> nonzero
                     ACTIVATES AN UNCALIBRATED MAP  [[reference-accord-eme-lever-semantics]]
```
⇒ **not one of them is a filter.** This agrees with two independent standing results —
*"no notch filter exists anywhere"* (V44) and *"no biquad"* (the resonance memory).
⇒ **The lever class V87 identified has NO CALIBRATION IMPLEMENTING IT.**

### 🛑 THE COMPLETE, BOUNDED PICTURE FOR GRINDING
| avenue | status | why |
|---|---|---|
| **b26 damper lane** | ❌ **EXHAUSTED, provably** | ceiling at the ±1024 gate bound; **no weight cell in Path 1** (bare `add`); α2 is a trade |
| **rate lane (Lever A/B)** | ✅ **at V62's measured-good config** | V133 reproduces V62's six cells byte-for-byte |
| **HF filtering of the command** | ❌ **no cal exists** | this section |
| **`0xC642A/C`** | ❌ **closed** | base-assist input EMAs; changes MANUAL feel |
| **`0xC63A6`** | ⚠ **blocked on GATE 2** | loop gain past a 16.70 Hz corner; needs measured phase |
| **the `Y` fork** | ⏳ **needs one number** | V129 (down) vs V130 (up) — the probe decides |
| **base-assist damper** | ⚠ **neither closed nor sized** | task-5 rate is OPEN (the 100 Hz claim was retracted) |

⇒ **Every calibration avenue is either exhausted, closed, or gated on a measurement.** That is
not the same as "out of ideas" — it is a search space with its boundary drawn, and **V133 sits at
the best point reachable inside it with current knowledge.**

### ⭐ WHAT WOULD ACTUALLY CLOSE THE THREE COMPLAINTS
**One drive on V133**, containing creep (2–10 mph with real steering), 15–40 mph, and at least one
slow hard hands-off turn. It yields:
- the **operator's report** on all three symptoms — the primary endpoint, and the only one that has
  ever tracked what he actually hears;
- `score_v131_grind.py` band ratios vs V122, with a 30–40 Hz negative control and a validated null;
- `score_v127_rail.py` (`ACCORD_RAIL_V133=1`) **rail duty**, which selects V129 vs V130 **and**
  decides whether `0xC63A6` is even the right question.

🛑 **No further build should be cut before that drive.** Three of this session's builds were
superseded pre-flight for defects found by re-deriving them (V126 mis-sized, V128 contradicted a
measured result, V132 broke its own probe). **The next defect of that class will not be found by
more analysis — it will be found by the car.**

## ✅✅ **THE DISPLACEMENT SCAN IS FIXED — AND IT CLOSES THE LAST GRIND CANDIDATE**
Turning to the **excitation** side (V87 established the lever class: *"a lightly-damped mode driven
by **broadband command content**, not a commanded tone ⇒ the lever class is **less broadband HF in
the delivered command**, NOT a notch"*, with engagement adding **3.37× at 15–22 Hz**), the standing
candidate was `0xC642A/C` — virgin, 194, a plausible IIR. Censusing it exposed a much bigger
problem first.

### 🛑 THE KIT'S STANDARD CENSUS METHOD IS 98 % NOISE AT ITS WORST
```
   cell        raw hits   real   the worst false positive
   0xC407E         4        3    0x07028 = `dispose 0x0, {r25,r27,r29,lp}, lp`
   0xC4004         7        3    0x0B8DE = `mov 0xfedf5004, r8`  -- a RAM ADDRESS
   0xC642A        52        1    0x3A118 = `cmpf.s le, r28, r15, 0x5`  -- an FP compare
   0xC642C        43        1
```
The displacement bytes occur inside **other instructions' encodings** — FP opcodes, `dispose`,
32-bit immediates. **A census decides blast radius before an edit**, so this is not a cosmetic
problem: I have hit it **three times this session** and nearly abandoned a good lever on it once.

### ✅ THE FIX — a STRUCTURAL filter, validated against every hand-verified census
V850 Format-VII loads encode the **base register in the low 5 bits of the first halfword**:
```
   ld.h  0x740a, tp, r12  ->  25 67 0a 74   hw1 = 0x6725,  & 0x1F = 5 = tp
   ld.hu 0x7936, tp, r14  ->  e5 77 37 79   hw1 = 0x7725,  & 0x1F = 5
   ld.w  0x5004, tp, r14  ->  25 77 05 50   hw1 = 0x7725,  & 0x1F = 5
```
⇒ require **`(hw1 & 0x1F) == 5`**. It reproduces **every** hand-verified census exactly
(`0xC407E` 3, `0xC4004` 3, `0xC640A` 1, `0xC63A6` 1) while cutting `0xC642A` from **52 to 1**.
Shipped as `analysis-2020accord/verify/tp_cal_readers.py`.
⚠ **It is a FILTER, not a proof** — it cannot catch the 6-byte gp/tp form, nor an access through a
register loaded with the absolute address (**exactly what `0x0B8DE` was**). **Still confirm the
survivors in Ghidra.**

### 🛑 AND `0xC642A/C` IS **NOT** A GRIND LEVER — the candidate is CLOSED
With the noise gone, each has **exactly one reader**, both inside `FUN_0002b62c` — the **BASE
ASSIST** function — and both are **EMA alphas on its INPUTS**:
```
   0xC642C @0x2B73C   state += ((gp-0x6a52 << 9)/25 - state) * alpha >> 10
   0xC642A @0x2B76E   state += (gp-0x4f60 * 32     - state) * alpha >> 10   <- DRIVER COLUMN TORQUE
```
⇒ they smooth **base-assist inputs**, not the LKAS delivered path. Cutting them changes **manual
feel** — the opposite of the operator's standing instruction to keep manual light — and does
**nothing** to broadband HF in the delivered command.
✅ **This also retires V125's original probe question.** V125 was built to measure *"reader #3's
delivered sign"* to decide `0xC642A/C`; reader #3 is `FUN_0002b62c`, so **the question was about a
base-assist cell all along.** Replacing that probe with the rail-duty probe (V127 onward) was the
right call for a reason better than the one I had at the time.

⇒ **The last standing grind candidate outside the b26 lane is closed.** What remains is exactly
what the previous section named: **the fork (one number from one drive)** and **`0xC63A6` (blocked
on phase)**.

## ✅✅ **THE `gp-0x6b26` DAMPER IS STRUCTURALLY EXHAUSTED — A DEFINITIVE CLOSE, NOT A PARTIAL ONE**
The record says *"Path 1 = `FUN_0003aa2c`, the aggregator, **unity weight, zero phase** — this is
what delivers the damping."* Path 2 fails GATE 2 on phase, so a **zero-phase** weight in Path 1
would have been the ideal lever. **It does not exist.** Disassembling the aggregator's own use:
```
   0x3acb0  addi   0x400, r11, r14      <- gp-0x6b26 + 1024
   0x3acb4  addi  -0x801, r14, r0       <- the SAME +-1024 ADMISSION GATE
   0x3acb8  cmovc  0x0, r11, r15        <- gated
   0x3acc8..0x3acda   add r24,r6 / add r6,r8 / add r8,r12 / add r12,r10 / add r10,r15
                      / add r15,r16 / add r16,r13 / add r13,r7 / add r7,r28
```
⇒ **a chain of BARE `add` instructions — there is NO weight cell on `gp-0x6b26` in Path 1.**
Two consequences, both load-bearing:
1. **No zero-phase weight lever exists.** Path 1 is literally unity, so there is nothing to raise.
   The **only** weight on this term is `0xC63A6`, in Path 2 — the closed firmware loop whose
   16.70 Hz corner puts grind #1's 21–26 Hz **past the corner**, where added gain destabilises.
2. 🛑 **The ±1024 admission gate binds in BOTH consumers**, `0x3ACB0` (aggregator) and `0x3815C`
   (`FUN_00038148`) — **not just the one found last section.** The hard ceiling is doubly binding,
   and V133's 1023 keeps the term ADMITTED in both. **This also makes 1024 unambiguously final.**

### 🛑 THE COMPLETE BOUND ON THIS LANE — every knob, and where it now sits
| knob | cell | state on V133 | headroom left |
|---|---|---|---|
| shape | α2 `0xC40DC` | 5 (of 22 stock) | trades in-band damping for broadband rail-drive |
| gain | `Y` `0xD7A5C/5E/60` | ×3 stock | **the fork** — V129 down / V130 up, probe decides |
| **ceiling** | `0xC407E` + float twin `0xC4004` | **1023 / 1.0** | ❌ **NONE — 1024 is the gate bound** |
| Path 1 weight | — | **does not exist** | ❌ **NONE — bare `add`** |
| Path 2 weight | `0xC63A6` | 1024 virgin | ⚠ exists, **fails GATE 2 on phase** |
| oscillation branch | `0xC640A` | −1966, linear at arm | ❌ none — sized to the threshold |

⇒ **THE DAMPER IS FULLY EXPLOITED.** No further damping is available from `gp-0x6b26` by any
calibration, at any dose, in either path — **except** the fork (a measurement, not a choice) and
`0xC63A6` (blocked on phase). **A future session should not re-open this lane looking for more.**

### ⭐ WHAT THIS MEANS FOR THE THREE COMPLAINTS
It is a **real result, not a dead end**: it converts *"keep trying damper doses"* into a bounded
question. **If V133 still grinds and its probe shows the term LINEAR, the deficit is authority and
the answer is `0xC63A6` with the phase measured** — the single named next step, with a stated
gate. **If the probe shows it RAILING, the answer is V129 rebuilt on V133.** Either way the next
build is determined by one number from one drive, and both branches are already specified.

## ⭐ **A NEW LEVER OUTSIDE THE EXHAUSTED LANE — `0xC63A6`, AND WHY IT IS *NOT* BUILT**
`FUN_00038148`'s six-term sum applies a **per-term CAL WEIGHT** to each summand, **after** the
clamp and after the admission gate:
```
   0xC63A0  gp-0x6bd0 weight     0xC63A2  gp-0x6bbe weight     0xC63A4  gp-0x6b46 weight
   0xC63A6  gp-0x6b26 weight  <- THE DAMPER
   0xC63A8  gp-0x6b4e weight     0xC63AA  gp-0x6b4c weight
   all 1024 (unity) on STOCK and on EVERY build; only 0xC63A0 was ever moved (V72 2048, V77 back)
```
⇒ **`0xC63A6` is a virgin unity weight that multiplies the damper PAST both ceilings** — the 1023
clamp and the ±1024 admission gate both bind *upstream* of it. On paper it is the escape from the
lane bound established one section above.

### 🛑 IT FAILS **GATE 2**, AND THE ONE ON-CAR DATUM IS CONFOUNDED — SO IT IS NOT BUILT
1. **These weights are LOOP GAIN, not a feed-forward scale.**
   [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]]: the sum → `gp-0x6b70` →
   `FUN_00037fe6` → `gp-0x6ad6` → the PID `FUN_0003a382` → aggregator → `gp-0x6b98`, **which
   re-enters via `FUN_0003b8f6` one sample later** ⇒ **a closed feedback loop inside the firmware.**
2. **The loop's own IIR corner is 16.70 Hz** (`0xC63AC` = 102) ⇒ grind #1's **21–26 Hz is PAST the
   corner**, where the added phase lag is exactly what turns extra gain into instability.
3. **The one on-car datum points the other way but does not attribute.** V83a **lowered** the
   sibling `0xC63A0` 2048→1024 and flew **the worst build in the modern lineage for both scored
   symptoms** — grind #1 **2.674× V81 [1.956, 3.885]**, null [0.63, 1.55], **10/10 cells > 1**;
   micro-ratchet 1.526× [1.174, 2.019]. ⚠ **But V83a moved THREE things** (FactorE m26 → Honda's
   ramp, `gain_A` rec0/rec1 → stock, **and** the weight) ⇒ **the 2.674× is not attributable to the
   weight**, and the kit's own note adds that V83a *"left mode 27 carrying V81's whole damper."*

⇒ **[EVIDENCE] the weight exists, is virgin, is unity, and sits downstream of both ceilings.
[BELIEF] that raising it damps rather than destabilises** — and the kit's standing law is
**magnitude AND phase, in every loop the signal is in.** Building it now would repeat exactly the
mistake this session caught three times: acting on a structural argument without the measurement.

### ✅ WHAT WOULD OPEN IT
The V133 probe already carries `|gp-0x6b26|`. If its rail duty comes back **low** (the term is
linear) **and** grinding persists, then the damper is **under-delivering rather than relay-ing**,
and `0xC63A6` is the only remaining way to give it more authority — at which point the phase
question must be answered on **`FUN_00038148`'s measured transfer**, not on its structure.
⊕ A ×2 step is **+6.02 dB** by the kit's own figure for the sibling cell, with **zero cost to
Path 1** (the aggregator's unity-weight, zero-phase route, which is what actually delivers damping).

## 🛑🛑 **1024 IS A HARD CEILING ON `0xC407E` — V133's 1023 IS THE MAXIMUM, BY ONE COUNT**
Applying V133's own rule (*"when a build changes a RANGE, re-derive everything that consumes it"*)
to `gp-0x6b26` itself. **6 read sites**; `0x36CE4`/`0x36CF0` are the writer, `0x36D78` the monitor
(handled by the float twin), `0x614A2` is a **`jarl` false positive**. Two real consumers:
`0x3AC98` (the aggregator, governed at 4762 ⇒ 1023 is fine) and **`0x3815C`, in `FUN_00038148`**:
```c
   (int)(gp-0x6b26) * (uint)((int)(gp-0x6b26) + 0x400U < 0x801) * cal(tp+0x73a6) >> 10
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                             (x + 1024) < 2049   <=>   -1024 <= x <= +1024
                             OUTSIDE it the multiplier is literally 0
```
🛑 **This is an ADMISSION GATE, not a clamp: outside ±1024 the damper does not saturate — it
VANISHES from the `gp-0x6b70` sum entirely**, while the aggregator path at `0x3AC98` still sees
it. A partial, asymmetric failure that would be extremely hard to diagnose from a drive.
```
   |x| = 511    ADMITTED        |x| = 1024   ADMITTED
   |x| = 1023   ADMITTED        |x| = 1025   ZEROED -- the damper VANISHES
```
✅ **V133 sits at 1023 — inside by ONE COUNT, and it is the maximum available.** ⊕ The other
summands' windows, for contrast: `gp-0x6b4e`/`gp-0x6b4c` **±10240**, `gp-0x6bd0`/`gp-0x6bbe`
**±2048**, `gp-0x6b26`/`gp-0x6b46` **±1024** — the tightest in the sum.
⭐ **This is almost certainly why Honda ships 511**: comfortably inside a ±1024 gate, with the
monitor twin at 512 just above it. The design is coherent once both are seen together.
🛑 **A future build trying 2047 “ because 1023 helped ” would silently zero the damper.** The
builder now asserts BOTH directions: that 1023 is admitted, and that **1025 would be zeroed**,
with the message *"NEVER raise 0xC407E above 1024."* **77/77**, image SHA unchanged.

⇒ **The gp-0x6b26 lane is now fully bounded and fully exploited**: α2 sets the shape, `Y` sets the
gain, the **ceiling is at its structural maximum**, and the oscillation branch is sized linear at
its arming threshold. **There is no remaining headroom in this lane** — anything further must come
from the fork (which the probe decides) or from outside the lane.

## 🛑🛑 **V132 WOULD HAVE BROKEN ITS OWN MEASUREMENT — CAUGHT PRE-FLIGHT. V133 IS THE BUILD.**
V132 raised the `gp-0x6b26` clamp **511 → 1023** but left the 427 packer at **sar 2**, which had
been sized for the 511 clamp:
```
   wire = min((|gp-0x6b26| * 5) >> sar, 0x3FF)

   sar   wire @511   wire @1023   wire saturates at |x|
    2         638         1023                     819   <- V132: CLIPS BELOW ITS OWN CLAMP
    3         319          639                    1637   <- V133
    4         159          319                    3274
```
🛑 **At sar 2 the WIRE saturates at |x| = 819, BELOW the new 1023 clamp.** The rail-duty scorer
would have counted `wire == 1023` as *"railed"* while the term was only at **819**, and could never
have observed the term between 819 and 1023 at all. ⇒ **V132 would have destroyed the one number
the entire V129-vs-V130 fork depends on** — while *looking* like it worked. **Artifacts DELETED.**

⭐ **The general lesson, and it is not the same as V126's.** V126 was mis-*sized* against a
threshold. **V132 was internally inconsistent: the EDIT and the INSTRUMENT were sized against
different assumptions.** Raising a clamp silently changes what the probe watching that clamp can
see. ⇒ **RULE: when a build changes a quantity's RANGE, re-derive every probe that measures it in
the same build.** The builder now enforces it — `THE PROBE GATE` asserts the clamp maps below
1023, and a second assertion records that **sar 2 would clip at 819**, so the mistake cannot recur.

### ✅ V133 BUILT — 3 payload bytes on a V131 base
```
   0xC407F   01 -> 03     int clamp   511 -> 1023
   0xC4006   00 -> 80     float twin  0.5 -> 1.0     (float*1024 == int+1, HARD GATE)
   0x55E10   a2 -> a3     packer sar  2 -> 3         (1023 -> wire 639 of 1023, LSB 1.6)
```
image `f26ddb4364198293f5fd91c99cccd103ebc951b4f1bb9cc56d40b67a7388822b` ·
rwd `4647801d492c75c5a90e60e9f7505dd8ee663b87a60de562bf1c533066973e01` · **75/75, CRC 50/50.**
✅ `verify_int_float_twins.py` PASSES it. ✅ `score_v127_rail.py` now takes
**`ACCORD_RAIL_V133=1`** to switch to clamp 1023 / sar 3 (rail wire **639**); its wrong-build guard
still correctly REFUSES an r24 cache in both modes.

## ✅✅ **A TWIN VERIFIER THAT REDISCOVERS BOTH HISTORICAL FAULT CLASSES FROM SCRATCH**
`analysis-2020accord/verify/verify_int_float_twins.py` — checks Honda's own invariant
**`float × 1024 == int`** across every documented mirror family on any built image.
```
   FAIL  _v73, _v74 (x3), _v75 (x2), _v76, _v77, _v77b   int 850 / float 512  MISMATCHED
   FAIL  _v25, _v26, _v27, _v28                          (the DTC 0xF00049 era)
   PASS  V124 V125 V127 V129 V130 V131 V132              all 8 twin pairs matched
   PASS  stock code.bin
```
⭐ **EVERY image it flags is one that ACTUALLY HARD-FAULTED ON THE CAR** — V74/V75 through the b26
twin, V25–V28 through the corridor/envelope twin. **It was not tuned to find them; it derives them
from the invariant alone.** That is the positive control this class of check has never had.
⇒ **Run it on every built image before flashing.** A desync does not fail at build time and does
not fail on the bench — **it faults on the road.**

### ✅ AND IT CONFIRMS V132 IS CLEAN
All three documented families are matched on V132 — the b26 ceiling **511/0.5 → 1023/1.0**, the
direction corridor (int 5120 ↔ float 5.0) and the boost floor (int 5120 ↔ float 5.0). The corridor
and boost pairs were **already** moved in lockstep by earlier builds; **only the b26 ceiling had
never been lifted**, and V132 lifts it correctly. ⇒ **V73's failure mode exists nowhere else on
the current build.**

### 🛑 A NOTE ON THE FIRST ATTEMPT, BECAUSE THE METHOD MATTERS
My first audit paired ints to floats **by value** (`|int| ≈ float×1024`) across the whole cal
region. It returned **353 KB of output** dominated by nonsense — cave bytes reading `0xFF` = −1
"pairing" with an unrelated `0.0011`. ⇒ **a value-similarity heuristic is not a structural claim.**
The families in the verifier are the ones the kit has **traced to a monitor that actually compares
them**; that is what makes a pair real.

## 🛑🛑🛑 **THE 511 CEILING IS NOT A HARD LIMIT — IT HAS A FLOAT TWIN. V132 LIFTS BOTH.**
`gp-0x6b26 = clamp(…, ±cal(0xC407E) = 511)`, and because **damping and railing are one knob**, that
clamp was the **hard ceiling on how much damping this lane can ever deliver.** Every other move is
a trade: **V129 (Y↓) de-rails but LOSES damping; V130 (Y↑) adds damping but RAILS EARLIER.**
✅ **Raising the ceiling is the only move that is not a trade** — linear damping `|H|×Y` is
**unchanged**, and only the point at which the term becomes a bang-bang relay moves out:
```
   speed knot     rails @511   rails @1023   change          (detector arms at 12800)
    0 km/h            1065         2132      2.00x later
   20 km/h            1826         3655      2.00x later
   90 km/h            1963         3930      2.00x later
```

### 🛑 AND IT EXPLAINS THE V74/V75 HARD FAULTS EXACTLY
`FUN_00036d74` is a **range monitor with a FLOAT twin**:
```c
   fVar3 = gp-0x6b26 * 0.0009765625;          // /1024
   lim   = *(float*)(tp + 0x5004);            // = cal 0xC4004
   if (fVar3 > lim || fVar3 < -lim) FUN_000462e6(0x39bc, ...);   // the FAULT report
```
Honda ships them **matched**: int **511**, float **0.5** ⇒ `0.5×1024 = 512 = 511+1`.
```
   build         0xC407E   0xC4004   float x1024   matched?
   STOCK             511   0.500000       512.0    YES
   V73/V74/V75       850   0.500000       512.0    NO -- MISMATCHED
   V131              511   0.500000       512.0    YES
```
⇒ **V73 raised the INT clamp to 850 and left the FLOAT monitor at 512.** Every time `|gp-0x6b26|`
passed 512 the monitor fired → hard fault. **That is the whole story of V74/V75**, and it is the
**same int-vs-float desync that produced DTC `0xF00049` in the V21–V24 era**, repeated on a new
pair. ⇒ the standing *"`0xC407E` is the fault interlock, never raise it"* is **HALF RIGHT: never
raise it ALONE.** [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]] needs this qualifier.

### ✅ V132 BUILT — 2 payload bytes on a V131 base
```
   0xC407F   01 -> 03     int clamp   511 -> 1023   (ff01 -> ff03)
   0xC4006   00 -> 80     float twin  0.5 -> 1.0    (…003F -> …803F)
```
image `b47f231cfd3ae3a62605da3fd8230d69e2e03dcd00d7389397aa084b33351c80` ·
rwd `439bf613c47675e56991b1d2a48ef19ce7208ee3806eef525fda3e09c1d22cd3` · **73/73, CRC 50/50.**
✅ **The invariant `float×1024 == int+1` is asserted as a HARD GATE** — the exact check that would
have stopped V73. ✅ The float is asserted **against its ENCODING** (`0x3F800000`), not a decimal
([[feedback-float-spec-must-be-the-formula]]). ✅ **The monitor is NOT disabled** — it still trips
on anything beyond the new limit, just at 2× the threshold; the safety property is preserved.

### ✅ BLAST RADIUS — BOTH CELLS PRIVATE, and 5 of 11 raw scan hits were FALSE POSITIVES
```
   0xC407E   3 readers: 0x36C34, 0x36CD0, 0x36CDC   -- ALL inside FUN_00036c12
   0xC4004   3 readers: 0x36D80, 0x36D8C, 0x36DBC   -- ALL inside FUN_00036d74
```
🛑 The raw byte scan also reported `0x07028` and `0x09288`/`0x0B8DE`/`0x0B914`/`0x0B928`.
**All five are FALSE POSITIVES at the instruction boundary**: `0x07028` is
`dispose 0x0, {r25,r27,r29,lp}, lp`, and `0x0B8DE` is `mov 0xfedf5004, r8` — a **32-bit RAM
address** whose low half is `0x5004`, not a tp-relative displacement. ⇒
[[accord-v850-scan-traps-formatv-and-storezero]]'s *"validate every byte-scan hit on an instruction
boundary"* fired on **5 of 11** hits here. **I nearly abandoned this lever on the false positives.**
⊕ Downstream headroom: the aggregator is governed at **4762** and clamped **±8192**, so 1023 is far
inside both.

⚠ [BELIEF] that a 2× ceiling improves the symptom. It **strictly** reduces relay behaviour and
**strictly** preserves linear damping, so it cannot make the term more of a relay — but whether the
residual grinding is dominated by this term is what **V131's probe measures**. **V132 is the right
move if the probe shows railing, and inert if the term is already linear.**

## ✅ **THE BUILD SET, STATED EXACTLY — AND TWO THINGS THE NEXT SESSION MUST NOT GET WRONG**
```
   build   gain  α2   0xC640A   Y[1]/Y[2]        LeverA sar   427 tap   rwd
   V124    7128   5     -8192   -17202/-16000      aa/aa        6ABC      yes
   V127    7128   5     -1966   -17202/-16000      aa/aa        6B26      yes
   V129    7128   5     -1966   -17202/ -5898      aa/aa        6B26      yes
   V130    7128   5     -1966   -31923/-29692      aa/aa        6B26      yes
   V131    7128   5     -1966   -17202/-16000      a9/a9        6B26      yes   <- THE FLIGHT
```

### 🛑 GAP 1 — **V129 AND V130 DO NOT CARRY LEVER A.** They are built on **V127**, before
V131 restored `0x3AB76`/`0x3AC20`. ⇒ **after V131 flies, the winning fork branch must be REBUILT
ON V131**, not flown as-is. Flying V129 or V130 as they stand would silently drop V62's 8–42× fix
again — **the exact failure this session just spent a build undoing.**

### 🛑 GAP 2 — THE BASE-ASSIST DAMPER IS **NEITHER CLOSED NOR USABLE**, and I nearly got this wrong
Looking for a damping path that is **not** capped by `gp-0x6b26`'s 511 clamp, the obvious candidate
is the base-assist damper `ch0 = (FactorC(speed) × FactorE(rate)) >> 10` in `FUN_00034350`. The
record appears to close it: *"task 5 is 100 Hz ⇒ the damper structurally cannot damp the 20.9 Hz
mode."*
🛑 **That claim was RETRACTED on 2026-08-12 and the file says so in its own header.** The
`syscall8`/TCB derivation rested on an **address coincidence** (`tp-0x3814` pointing at TCB[0]),
and `FUN_00083854`/`FUN_00083918` are **not task-wake primitives at all**. Flown telemetry
contradicts it directly: `gp-0x6bbe`'s outer EMA (α = 205/1024) predicts **−6.6/−8.4/−9.5 dB** at
6/7.79/9 Hz **if the lane ran at 100 Hz**, versus **−0.2/−0.3/−0.3 dB at 1 kHz** — **measured
≈ −1.2 dB**, about **7 dB** from the 100 Hz prediction.
⇒ **Task 5's true rate is OPEN.** The damper is **not** ruled out on rate grounds — but it is also
**not sized**, so no build may rest on it until the rate is closed. ✅ **What survives untouched:**
**task 1 = 1 kHz** (two independent methods), so `FUN_0003aa2c` and `FUN_0003a382` — the aggregator
and the PID, which V131's Lever A edits — **are confirmed 1 kHz.**
⊕ **I was one step from dismissing a live lever on a retracted claim.** Recorded so the next
session does neither: **do not close it, and do not build on the 100 Hz figure.**

### ⭐ WHERE THE THREE COMPLAINTS ACTUALLY STAND
- **grinding** — every measured anti-grind edit is on **V131** for the first time. 🛑 The one
  structural fact that bounds it: **`gp-0x6b26`'s damping is capped at 511 counts by `0xC407E`,
  which CANNOT be raised** (Honda ships it one count under its own 512 monitor trip; V73 raised it
  and V74/V75 hard-faulted). **Damping and railing are one knob**, so within this lane there is a
  hard ceiling on how much damping is available — and at 8× excitation the build sits at **0.54×**
  of V106's measured-good in-band product, with `Y[0]` unable to reach 1.00× because **int16
  forbids it**. ⇒ **if V131 does not eliminate grinding, the remaining moves are the fork (V129/
  V130 rebuilt on V131), α2, or a damping path outside this lane** — and the only known candidate
  outside it is the base-assist damper above, whose task rate is OPEN.
- **LKAS authority** — 8× with matched 4096 clamps; chain verified unclipped end to end
  (3341 < 4096 clamp < 4762 governor, 1.43× headroom, room to ~11.4×). ✅ Nothing further is
  available without exceeding the operator's own 8× instruction.
- **peak-turn oscillation** — `0xC640A` −8192 → −1966, sized to stay **LINEAR at the detector's own
  arming threshold** (409 of 511). This is the first build ever to touch that branch.

🛑 **The analysis is now bounded by measurement, not by ideas.** Every remaining lever's
direction depends on a number only a drive produces — the rail duty — and the record is explicit
that it **cannot be predicted open-loop** (V107: predicted ≤1.05 %, measured 33.49 %, a **32×**
miss, because the lane is a closed loop).

## ✅ **V131's FLIGHT CARD IS WRITTEN — AND THE DRIVE MUST CONTAIN CREEP, OR THE TEST CANNOT WORK**
`docs/scoring/SCORING-V131-preregistered.md`, committed before any V131 flight exists.

### 🛑 THE FINDING THAT CHANGES WHAT THE DRIVE HAS TO BE
V62's headline result — **42× at 18–22 Hz** — was measured at **engaged creep**, in the
`|rate| 16–32 °/s` cell. Scoring **r22 vs r23 (both V112)** shows that cell is **EMPTY on highway
routes: n = 2 and n = 0**, because they speed-match at **36–69 km/h**.
⇒ **a highway-only drive CANNOT reproduce V62's endpoint**, and V131's whole grind case rests on
V62's lane. The card therefore requires: **(1) engaged creep 2–10 mph with real steering**,
(2) engaged 15–40 mph, **(3) at least one slow hard turn hands-off engaged**, (4) some highway.
⊕ Without (3) the counter never saturates ⇒ **`0xC640A` is inert BY CONSTRUCTION** and the rail
bins read near zero **for the wrong reason**.

### ✅ THE NULL CONTROL PASSES — the estimator does not manufacture significance
`score_v131_grind.py --null` scores **r22 vs r23, the SAME firmware**; every band must span 1.0:
```
   18-22 Hz  0.860 [0.592, 1.344]        21-26 Hz  0.957 [0.802, 1.203]
   6-9 Hz    1.162 [0.535, 1.852]        30-40 Hz  1.189 [0.822, 1.538]
```
✅ All four span 1. ⊕ Episode-clustered, speed-matched, with a **30–40 Hz negative control** — a
ratio that moves in the signal band **and** the control band is a **global** change, not a grind
result.

### 🛑 THE DETECTION FLOOR, QUANTIFIED AND STATED IN ADVANCE
Those same-firmware CIs **are** the resolution limit: **±20 % at 21–26 Hz, ±40 % at 18–22 Hz.**
⇒ **do not read a ratio of 0.9 as an improvement.** This is the route-variance floor
([[accord-averaged-spectrum-needs-matched-speed-distributions]]) made numeric, and it means a
small effect simply cannot be resolved on one drive — the operator's own report stays PRIMARY.

### ⚠ A CONFOUND STATED BEFORE THE DRIVE, NOT AFTER
**V131 changes the rate lane AND, versus V122, the forward gain (6×→8×).** They are not separable
on one drive: the rate-lane restore should REDUCE grinding, while
[[accord-the-8x-gain-is-the-carrier]] says the gain INCREASES the ~23 Hz excitation.
⇒ **if grinding comes back unchanged, cancellation is a live explanation and NOT a null.**

## ✅✅ **LEVER A × LEVER B: A RISK RAISED, CHECKED, AND RESOLVED IN V131's FAVOUR**
I flagged that V131 might stack two levers that had never flown together. **It does stack them —
they multiply — but V62 ITSELF already flew the stacked configuration.** Both halves recorded.

### ✅ THEY DO MULTIPLY — same expression, 24 bytes apart
```
   0x3ac08  ld.hu 0x7446, tp, r10     <- 0xC6446 = Lever B arm (5244; stock 512)
   0x3ac18  mul   r10, r8, r0         <- r8 = r1 * arm          <- Lever B multiplies HERE
   0x3ac20  sar   0xa, r8             <- >> 10                  <- Lever A shifts HERE
```
`out = (r1 × arm) >> sar` ⇒ **arm and sar compound directly.** ⊕ And **r26 has its OWN arm**,
`0xC643E` @`0x3AB68`, a **different cell** from Lever B's `0xC6446` ⇒ the r26 `sar` edit is clean
and cannot compound with Lever B at all.
```
   r26 lane:  out = ((r1*r6)>>10 * arm 0xC643E) >> sar 0x3AB76
   r24 lane:  out = (r1 * arm 0xC6446|0xC6440) >> sar 0x3AC20
```

### 🛑 MY CONCERN WAS WRONG — AND THE CORRECTION IS THE INTERESTING PART
I asserted V62 flew at `0xC6446` = **512** (stock) and therefore that V131's 5244 + sar 9 =
**20.48×** was unflown and 10× past V62's *"2× ≈ OPTIMUM"*. **Reading the V62 image instead of the
narrative: `0xC6446` was ALREADY 5244 on V62.**
```
   THE WHOLE r24/r26 RATE LANE, V62 (measured 8-42x) vs V131
     r26 arm 0xC643E    1536  ==  1536
     r24 arm A 0xC6440  2048  ==  2048
     r24 arm B 0xC6446  5244  ==  5244
     r26 sar 0x3AB70    0xaa  ==  0xaa
     r26 sar 0x3AB76    0xa9  ==  0xa9
     r24 sar 0x3AC20    0xa9  ==  0xa9
   => V131 reproduces V62's rate lane EXACTLY
```
⇒ **the 20.48× r24 total IS the configuration that measured 8–42× better, fault-free** (`ST==4`
on 0 of 86,278 frames). **V131 is not a new dose; it is V62's lane, byte-for-byte.**
⊕ The *"2× ≈ optimum"* note refers to **the `sar` step alone**, not to the lane total — conflating
them is what produced the false alarm. ⊕ `0xC6446`'s history is **non-monotone**: 5244 at V62,
**512 at V87**, 5244 again from V88 — consistent with its own frozen note, *"Reverted 3× at
rebases."*

### ⭐ THE METHOD LESSON, WHICH IS THE REAL TAKEAWAY
**The narrative said 512; the image said 5244.** Two sessions of build notes attributed Lever B to
V67/V68, so I reasoned from that attribution instead of reading V62's bytes — and nearly revised a
correct build on the strength of it. ⇒ **when a risk depends on what a PRIOR BUILD contained, read
that build's IMAGE, not the record of it.** The images are the ground truth and they are all in
`accord-firmwares`.
⊕ This is the third time this session that going to the bytes overturned a narrative claim
(the `ld.bu` disp¦1 scan, V106's extinction result, and now this) — **twice the bytes corrected me
toward MORE caution, once toward LESS.**

⇒ **V131 stands unchanged, now with its riskiest interaction explicitly checked.**

## ✅✅ **EVERY MEASURED-GOOD EDIT IS NOW ON THE BUILD — THE LOST-FIX AUDIT CLOSES CLEAN**
Prompted by V131: if V62's fix could sit lost for ~50 builds behind a guard that *asserted* the
loss, **what else is missing?** Two audits.

### ✅ AUDIT 1 — every edit with a MEASURED on-car result, checked byte-by-byte against V131
```
   fix                          addr       stock   wanted    V131   status
   V42  governor state-4        0x454FE      186      181     181   OK
   V62  Lever A r26 sar         0x3AB76      170      169     169   OK   <- restored by V131
   V62  Lever A r24 sar         0x3AC20      170      169     169   OK   <- restored by V131
   V88  sign fix                0x3AA96      197      251     251   OK
   V67/V68/V88 Lever B arm      0xC6446      512     5244    5244   OK
   V106 engaged Y[0] x3         0xD7A5C    -9830   -29490  -29490   OK
   V106 engaged Y[1] x3         0xD7A5E    -5734   -17202  -17202   OK
   V112 relay knee              0xC40BC      600     3000    3000   OK
   V112 relay K1                0xC40D2      102     1020    1020   OK
   V14  forward clamp A/B       0xC61B2/B4   512     4096    4096   OK
```
⇒ **11 of 11 present. Nothing else is lost.**
🛑 **One FALSE POSITIVE, corrected here rather than left standing.** My list also carried
**V33's `0xC6312` 320→65535** as a measured fix. **It is not one — V33 was never flashed**
(`project_accord_torque_mod_v0`: *"49/49 CRC, 0 code edits, UNFLASHED"*), and the gentle-EME was
resolved on-car by **V37 via the debounce SM**, a different mechanism entirely. ⇒ `0xC6312` at
**stock 320 is CORRECT**, and raising it would be an untested change, not a restoration.

### ✅ AUDIT 2 — every builder's frozen/tracked table, read for descriptions that record a LOSS
74 distinct cells across all builders; **6 descriptions record a loss or a null rather than a
decision**:
```
   0x454FE  0xB5    "V42 byte -- MEASURED INERT. Carried because free"
   0xC6446  5244    "Lever B ARM -- the ONLY measured fix on the car. Reverted 3x at rebases"
   0xC40D2  204     "V89's K1 -- CARRIED"                     (superseded: the car runs 1020)
   0xC40D8  3686    "gp-0x4f60 EMA -- a NO-OP. Kill any proposal to move it"
   0x55DF2  0x7A    "CAN 427 SOURCE (V104) -- CARRIED"        (V127 deliberately repoints it)
   0x55E10  0xA4    "CAN 427 SCALER (V104) -- sar 0x4. CARRIED"
```
⭐ **`0xC6446`'s own note says it was REVERTED THREE TIMES at rebases** — the same failure that
took V62's Lever A. **It is present at 5244 on V131**, but that entry is the kit telling itself,
in writing, that this class of loss is recurrent. ⇒ **the V131 rule generalises: a frozen entry
must state WHY, and "carried"/"absent" is not a why.**
⚠ `0x454FE` is described as **"MEASURED INERT"** while [[accord-v42-flashed-ratchet-fixed-r26-falsified]]
calls it *"the confirmed root cause"* of the state-4 ratchet. **The builder comment and the memory
disagree.** The byte is present either way, so nothing is at risk today — recorded as an open
discrepancy, not resolved here.

### ✅ WHERE THIS LEAVES THE THREE COMPLAINTS
- **grinding** — V131 restores the kit's strongest measured fix (8–42×) **and** carries V106's
  ×3 Y row, V88's Lever B, V112's relay ladder. **All measured anti-grind work is now on one image
  for the first time.**
- **LKAS authority** — 8× forward gain + matched 4096 clamps, chain verified unclipped end to end
  (3341 < 4096 clamp < 4762 governor, 1.43× headroom).
- **peak-turn oscillation** — `0xC640A` −8192→−1966, sized to be LINEAR at the detector's own
  arming threshold.
⇒ **V131 is the flight.** One drive scores the grind symptom, the authority, the oscillation,
**and** the rail-duty probe that decides V129-vs-V130.

## 🛑🛑🛑 **V62's GRIND FIX HAS BEEN OFF THE CAR SINCE ~V80 — AND A GUARD KEPT IT OFF. V131 RESTORES IT.**
```
   build         0x3AB76 (r26 sar)   0x3AC20 (r24 sar)
   STOCK              0xaa                0xaa
   V62                0xa9                0xa9      <- THE FIX (sar 0xa -> 0x9)
   V80 .. V130        0xaa                0xaa      <- STOCK.  IT IS GONE.
```
🛑 **V62 is the kit's FIRST AND BEST-MEASURED grind fix** ([[accord-v62-fixed-the-grinding]]),
route 37, 86,278 frames, operator: *"Original grinding at 2–5 mph is gone!"* — engaged creep,
speed-standardised, **episode-clustered** bootstrap:
```
   18-22 Hz  V62/V59 = 0.124 [0.036, 0.387]                   =  8x better
   at |rate| 16-32 deg/s = 0.024 [0.016, 0.234]               = 42x better
   30-40 Hz NEGATIVE CONTROL ~ 1.0                            => band-specific, not global
   FLIGHT-CLEAN: ST==4 on 0 of 86,278 frames
```
**Lowest p90/p99/>1000-count transient rate of any build in the kit.** ⇒ the strongest measured
anti-grind result this project has, and **it has not been on the car for ~50 builds.**

### 🛑🛑 A GUARD ENSHRINED THE REGRESSION — THIS IS THE REAL LESSON
`V106B.FROZEN` records both cells as **"Lever A r24/r26 sar — V62's edit is ABSENT (stock).
Carried"**, and every later builder asserts the frozen set is unchanged. ⇒ **the LOSS was written
down as an INVARIANT**, so ~50 builds actively verified that the fix stayed OFF. The guard did
exactly what it was told; what it was told was wrong.
⇒ **Same failure family as [[accord-v42-ratchet-fix-lost-since-v53]]** (V42's ratchet fix
byte-stock V53–V70) — but worse, because here a check was *asserting* the regression every build.
⭐ **RULE: a FROZEN entry must record WHY a cell is at its value. "Absent (stock). Carried" is a
description of a loss, not a decision** — and it read as a decision for fifty builds.

### ✅ WHY THE REASON IT WAS DROPPED DOES NOT HOLD
The record carries *"Lever A = V62's sar ×2 (r24 half CAUSED grind #2)"*. **V62's own memory says
that regression is NOT ESTABLISHED**: the 43 excursions >2000 are **ONE 0.92 s burst ⇒ n = 1**;
burst rate **V62 0.00142 [0.00004, 0.00793] vs V59 0 [0, 0.00986] — V62's CI is INSIDE V59's**;
**V61 is 72× V62**; exposure-matched, **p = 0.51**; and *"instant #1 is a 38–46 Hz singleton at
5.4 mph, not the reported 10–20."*
⇒ **an n = 1, p = 0.51 observation was allowed to retire an 8–42× measured fix that passed its own
negative control.** That is the wrong trade, and it is why V131 exists.

### ✅ V131 BUILT — 2 payload bytes on a V127 base
```
   0x3AB76   0xaa -> 0xa9    sar 0xa -> sar 0x9   (r26 arm, FUN_0003aa2c)
   0x3AC20   0xaa -> 0xa9    sar 0xa -> sar 0x9   (r24 arm, FUN_0003aa2c)
```
image `4bb43e7f15c3df61fa44cfdfda75f25b2cadf6a34ae28d4f4d535f3038315e28` ·
rwd `77444293082ddfdd3fc5cee40f80ba15a32d41378eb0a48533e1c23c6c76d450` · **68/68, CRC 50/50.**
✅ **Instruction-verified**: `0x3AC20` disassembles as `sar 0xa, r8`, bytes **`aa42`** — V850 is LE
so the immediate is the **FIRST** byte; the builder asserts the register byte is **untouched**,
because this kit has slipped on exactly that before. In-place immediate edit, **same class as V62
itself, which flew fault-free** — **not** a cave edit, so no V24/V27/V48B bricking risk.
✅ **INDEPENDENT OF THE gp-0x6b26 FORK.** Lever A is the **rate lane** (`FUN_0003aa2c`); V129/V130
move the **acceleration lane**'s `Y` (`FUN_00036c12`). V131 touches neither `Y` nor `0xC640A`, so
it **composes with whichever branch the probe selects.**
⚠ [BELIEF] that V62's fix reproduces on the current build: V62 flew at **4×** gain, α2 = 22 and a
**stock** `Y` row; the car now runs **8×**, α2 = 5 and a **×3** row. Same lane, different excitation
and different parallel damping. **This restores a measured-good edit; it does not re-measure it.**

### ⭐ THE FLIGHT ORDER IS NOW CLEAR
**V131** is the strongest single grind candidate available and is **fork-independent** — it is the
build to fly if the goal is grinding. It carries everything V127 does (8× + clamps, α2 5, trim 3,
`0xC640A` −1966, the rail-duty probe) **plus** the restored Lever A, so **one drive scores both**
the grind symptom **and** the probe that decides V129-vs-V130.

## ✅ **BOTH BRANCHES OF THE FORK ARE NOW BUILT — V129 (Y down) AND V130 (Y up). NEITHER FLIES YET.**
`gp-0x6b26`'s damping and its railing are **the same knob** — both scale as `|H_lane(α2)| × Y × raw`
⇒ **the 511 clamp is a HARD CEILING on the damping this term can ever deliver.** What α2 changes
is the **SHAPE**:
```
   α2   |H|@21.7   broadband RMS   18-30 Hz fraction   RMS per unit in-band
   22     7.72         7.32              3.06 %              0.948
   14     7.10         4.92              5.51 %              0.693
    8     5.68         2.97              9.05 %              0.524
    5     4.16         1.92             11.15 %              0.463
```
α2 22→5 costs **0.538×** in-band but cuts broadband RMS to **0.263×** ⇒ **2.05× more in-band
damping per unit of rail-driving content.** ⊕ So at α2 = 5, restoring V106's in-band damping
**costs LESS rail duty than V106 itself paid** — an argument for raising `Y`, the OPPOSITE of V129.
🛑 **But V107 raised `Y` and its own rail-duty map matched the symptom map** — at α2 = 22, where
broadband was **3.8×** higher. **The two arguments genuinely conflict and only the probe separates
them.** Rail duty is closed-loop; V107's open-loop prediction missed by **32×**.

### ✅ V130 BUILT — the "≤ 2 % rails" branch
```
   0xD7A5E / 0xD7A6E   Y[1] modes 26/27  -17202 -> -31923    x1.856 = |H|(22)/|H|(5)
   0xD7A60 / 0xD7A70   Y[2] modes 26/27  -16000 -> -29692
```
Base V127, 8 payload bytes. image `de64f6079d45b4c7af9c7def77622479edc621ab7a96961739b9b182239c349b`
· rwd `b71a4862bb412438e533b44699427a8822ca1d505f61edd93fb4b81597ad78e6` · **83/83, CRC 50/50.**
`Y[0]` is **held** — int16 blocks it (29490×1.856 = 54727 > 32767) and **there is no low-speed
symptom**. `Y[1]` (20 km/h) and `Y[2]` (90 km/h) bracket the whole 24–64 km/h symptom band, and
both are restored to V106's **1.00×**. ⊕ The builder **asserts the scale equals `|H|(22)/|H|(5)`**
and **states plainly that the build rails EARLIER by design** (`Y[2]` threshold 1963 → 1058) —
because damping and railing are one knob. ⚠ It flattens Honda's speed taper, the largest single
`Y` departure this kit has made, which is why it is **gated, not recommended**.

### 🛑 THE FORK, PRE-REGISTERED — ONE DRIVE ON **V127** DECIDES
| `score_v127_rail.py` worst engaged bin | fly | why |
|---|---|---|
| **> 10 % rails** | **V129** (`Y[2]` ↓ to −5898) | the term is a relay; de-rail it |
| **≤ 2 % rails** | **V130** (`Y[1]/Y[2]` ×1.856) | the term is LINEAR ⇒ the deficit is DAMPING |
| **2–10 %** | neither as built | size `Y` to the measured duty |
⇒ **V127 is the flight.** It touches **no `Y` knot**, changes only the oscillation branch, and
carries the probe. **V129 and V130 embody OPPOSITE beliefs and exactly one is right** — flying
either blind is a guess, and this kit has paid for that guess before.

### ✅ A BUILDER DEFECT FOUND AND FIXED IN 11 BUILDERS
The byte-diff classifier asked whether a run **CONTAINS** a CRC trailer's start address; it must
ask whether the run **OVERLAPS** the 4-byte trailer `[t, t+4)`. It only bites when **fewer than
all four trailer bytes change** — V130 changed 3 of 4, so `0xD7FFF` was reported as **payload**
and the payload-count assertion failed on a correct build. Fixed in `build_v120..v130`. ✅ **The
already-emitted artifacts are unaffected** — V124/V127/V129 re-run to their recorded SHAs exactly.

## 🛑🛑🛑 **α2 AND Y MULTIPLY — THE α2 LADDER SILENTLY HALVED THE DAMPER. V129 HELD; V127 FLIES.**
`gp-0x6b26`'s effective damping is `|H_lane(α2)| × |Y|`. **Both levers have been moved, in opposite
directions, and NO build has ever held the product constant.** At the grind band (21.73 Hz):
```
   build     α2   |H|@21.7   Y = [lo, mid, hi]           product vs V106 (lo / mid / HI)
   STOCK     22     7.72     [ -9830, -5734,  -1966]      0.33x / 0.33x / 0.33x
   V106      22     7.72     [-29490,-17202,  -5898]      1.00x / 1.00x / 1.00x   <- MEASURED: NO LINE
   V107      22     7.72     [-29490,-24000, -16000]      1.00x / 1.40x / 2.71x
   V112      14     7.10     [-29490,-17202, -16000]      0.92x / 0.92x / 2.50x
   V122       8     5.68     [-29490,-17202, -16000]      0.74x / 0.74x / 1.99x
   V124/127   5     4.16     [-29490,-17202, -16000]      0.54x / 0.54x / 1.46x   <- ON THE CAR
   V129       5     4.16     [-29490,-17202,  -5898]      0.54x / 0.54x / 0.54x
```

### 🛑 TWO CONSEQUENCES, BOTH CORRECTIONS TO WHAT THIS SESSION ASSUMED
1. **The α2 ladder is NOT only a de-rail — it is also a DAMPING CUT.** I read 22→14→8→5 purely as
   shrinking the term's input to stop it railing. It does that, **and** it cuts the damper to
   **0.54×** of the configuration that measured the mode extinguished. Both effects are real and
   they oppose each other. **No prior session separated them, because the product was never held.**
2. **V129 is the WRONG DIRECTION and is NOT recommended.** It takes high-speed damping
   **1.46× → 0.54×**, while the build already sits at 0.54× low/mid **and carries more excitation
   than V104** (8× vs 6×) — and **V104 is the build that showed a pinned line at prominence 6.89.**
   More excitation with less damping is the one combination the record says produces a line.

### 🛑 AND THE PRODUCT CANNOT BE RESTORED AT α2 = 5 — int16 FORBIDS IT
To reach V106's 1.00× at α2 = 5, `Y` must scale by `7.72/4.16` = **1.856×**:
`Y[0]` = 29490 × 1.856 = **54,733 — past the int16 range (32767)**, giving at most 1.11× ⇒ 0.60×.
⇒ **only α2 can recover the low-speed damping.** The two levers are not interchangeable.

### ✅ THEREFORE: FLY **V127**, NOT V129 — THE DIRECTION IS A MEASUREMENT, NOT A GUESS
Whether `Y` should go **up** (restore damping) or **down** (de-rail) depends entirely on **whether
the term is actually railing on the current build**, and the record is explicit that
**rail duty cannot be predicted open-loop** — V107 predicted ≤1.05 % and measured 33.49 %, a
**32× miss**, because the lane is a closed loop. ⇒ **shipping a Y change blind is guessing.**
- **V127** changes only the **oscillation branch** (`0xC640A`, well-founded and sized against the
  detector's own arming threshold) and **carries the rail-duty probe**. It changes NO `Y` knot.
- **V129 is HELD, not deleted** — unlike V126/V128 it is not wrong-by-construction, it is
  *unsized*. It becomes the right build **iff** the probe shows the term railing at high speed.

**Decision rule, pre-registered:** run `score_v127_rail.py`; if the worst engaged bin
- **rails > 10 %** → fly **V129** (`Y[2]` down de-rails where it matters);
- **rails ≤ 2 %** → the term is LINEAR and the deficit is DAMPING → raise `Y[2]` toward
  **−32767** (1.11×, the int16 ceiling) and/or step α2 back up 5 → 8;
- **2–10 %** → mixed; size `Y[2]` to the measured duty rather than to either endpoint.

## 🛑🛑🛑 **V128 RETRACTED — IT WOULD HAVE UNDONE THE KIT'S BEST MEASURED FIX. V129 IS THE BUILD.**
V128 restored the whole engaged-mode `Y` row to stock, arguing our ×3 raise railed the term into a
Coulomb relay. **The rail arithmetic was right; the CONCLUSION was wrong.**

🛑 [[accord-v106-extinguished-the-mode-at-low-speed]] — **V106's ×3 raise is the kit's STRONGEST
measured anti-grind result**, and the **only band-power result ever to clear its own within-drive
split-half null** (18–30 `a6/V105` = **0.347** vs null **[0.482, 1.982]**; positive control
`a6/STOCK` = **5.735**, so the instrument was alive):
```
             peak Hz  PROMINENCE  18-30 RMS   argmax vs search-band edge
   STOCK 1x   18.23      1.46       0.3121    follows the edge   <- no line
   V104 6x    22.23      6.89       7.6624    pinned             <- a real line
   V106       18.23      1.51       3.7255    follows the edge   <- NO LINE
```
⊕ **A Coulomb relay is a STRONG nonlinear damper**, so *"railed"* and *"extinguished the mode"*
are **both true** — bang-bang kills a resonant line while adding broadband roughness. ⇒ my
inference *"railed ⇒ must restore to stock"* skipped the measurement. **V128's artifacts DELETED.**

### ✅ WHAT IS ACTUALLY WRONG WITH THE BUILD ON THE CAR — V107's HIGH-SPEED ESCALATION
```
   build          mode-26 Y                   rails from |c2c| (0/20/90 km/h)
   V106          [-29490, -17202,  -5898]      1065 / 1826 /  5325   <- MEASURED GOOD
   V107          [-29490, -24000, -16000]      1065 / 1309 /  1963
   V112 .. V127  [-29490, -17202, -16000]      1065 / 1826 /  1963   <- ON THE CAR
```
🛑 **V112 kept V106's `Y[1]` but inherited V107's `Y[2]` = −16000 — 2.7× V106's −5898.** So the
car has **never actually run the configuration that measured the extinction**: it carries V107's
high-speed escalation, and **V107 is precisely the build whose own session matched its rail-duty
map to the symptom map.** ⊕ V106's residual was explicitly a **HIGH-SPEED** phenomenon (hwy 40–95
prominence 6.5 vs stock 1.3, carried by the >70 km/h portion); V107 answered it by raising `Y[2]`
2.7×. **That is the single change V129 undoes.**

### ✅ V129 BUILT — 4 payload bytes, a return to a MEASURED-GOOD state
```
   0xD7A60  Y[2] mode 26  -16000 -> -5898     (Y[0], Y[1] HELD)
   0xD7A70  Y[2] mode 27  -16000 -> -5898
```
Base **V127**. image `dd643b6e7df85f7b598956d708f1ad1aa55da19dd4b2cb8512930c7a11d3c3dd` ·
rwd `e1c339f7ae0f9ecc12267d0f1820f08f00bcc3ec5c91b646ec22c7b3d05db8e6` · **75/75, CRC 50/50.**
- rail threshold at 90 km/h **1963 → 5325**, a **2.7× de-rail exactly where V106's residual lived**;
- `Y[0]`/`Y[1]` **asserted UNTOUCHED** ⇒ the low/mid-speed behaviour that measured the extinction
  is bit-identical to the current build;
- manual modes 24/25 asserted **byte-stock**;
- **no confound with V127**: `0xC640A` fires only when the counter is SATURATED, this record only
  when it is NOT — mutually exclusive by construction.

### 🛑 THE LESSON, RECORDED
**"The arithmetic says a term is railed" does NOT license "restore it".** A relay is a strong
damper; whether that is good or bad is an EMPIRICAL question, and this kit had already answered it
on-car. ⇒ **before acting on a structural argument, search the flight record for a build that
already tested it** — which is exactly what
[[feedback-search-the-kit-before-naming-a-cause]] says, and I did it one build late.
⚠ [BELIEF] that −5898 beats −16000 **on the current build**: V106 flew at α2 = 22 and 6×, the car
now runs α2 = 5 and 8×, so `|gp-0x6c2c|` and the command both differ. V129 returns the one cell
that was escalated past the measured configuration; it does **not** re-verify V106's whole result.

## ✅ THE FULL V128-vs-STOCK AUDIT — ONE NEW RISK FOUND, AND ONE FRAMING CORRECTED
Motivated by the V128 finding: **a raise on a term that CLAMPS is not a dose, it is a relay
conversion.** So every cell our builds have moved was re-read against stock. **302 payload bytes
in 112 runs.** ✅ The mode-26 record is **correctly ABSENT** — V128 restored it, so it is now
byte-identical to stock.

### 🛑 NEW: THE LKAS SETPOINT CLAMP NOW SITS **EXACTLY** ON THE SM2 ARMING THRESHOLD
```
   build   arb_setpoint_limit 0xE4194   SM2 arm 0xC6422   margin
   STOCK              15360                  16384        +1024  (6.2 %)
   V31                15360                  16384        +1024  (6.2 %)
   V42 .. V128        16384                  16384           +0  (0.0 %)   <- since V38
```
**Honda ships the setpoint clamp one step under its own SM2 trip**, exactly as it ships the
`gp-0x6b26` clamp at 511 one count under the 512 monitor trip
([[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]). **The same design idiom, and we
removed the margin in one of the two places.** SM2 arms on `demand > 16384`, so a clamp *at*
16384 does not by itself cross it — but there is **zero headroom** for anything that adds to
`demand` (`blend × min >> 15`), and the record already says **V19's raised SM2 still saw the
soft EME trigger**, so the SM does arm in practice on 2× builds.
⚠ **NOT BUILT, deliberately.** Restoring 15360 costs **6.7 % of top-end setpoint at every tier**,
which is directly against the operator's standing priority, and **no EME is currently being
reported** (V122 was fault-free). ⇒ recorded as a **known, quantified risk with zero current
symptom**, not a pending fix. **The test that would settle it**: log raw CAN 399 `STEER_STATUS`
for an SM cut during a hard engaged turn; if cuts appear, restore 15360 before anything else.

### 🛑 CORRECTION — the 15360→16384 block is NOT an unexamined change
I first read it as an unexamined block the audit had turned up. **The kit documents it well**: it
is **`arb_setpoint_limit`, the ± clamp on the LKAS setpoint `gp-0x69ae`, raised +6.7 % at V38**,
described in `docs/archive/arc-maps/` and `LEDGER-V38-TO-V84.md` G6 as *"the kit's oldest still-
active lever family"* — **8 of 12 records raised; `0xE41D0`, `0xE4248`, `0xE5220`, `0xE5248` were
left stock and still are.** ⇒ the lever is known; **only the SM2-margin observation above is new.**

### ✅ WHAT ELSE THE AUDIT CONFIRMED, ALL DELIBERATE AND ALREADY ON THE RECORD
- `0xC40BC` 600→3000 (×5) and `0xC40D2` 102→1020 (×10) — the Coulomb ladder, **exhausted rung**.
- `0xC6CD0` **stock 65535** → 7128 — stock leaves the forward-gain cell unprogrammed and binds on
  the 512 clamp instead; V57 onward drives it. Consistent with the earlier chain audit.
- `0xC62EA` 320→0 — the low-speed steer lockout window **eliminated**
  ([[accord-low-speed-lockout-window-c62ea]]).
- `0xC6446` 512→5244, `0x3AA96` c5→fb — V88's Lever B + sign fix.
- `0x454FE` ba→b5 — V42's state-4 governor fix, **restored and still present**.
- `0xC4B34` 164 B — the cave. `0x55C0E`/`0x55DF2`/`0x55E10` — the 427 packer and V127's probe.

⇒ **No second instance of the V128 pathology was found.** The engaged-mode `Y` record was the
only raise that pushed a term past a clamp into relay behaviour.

## 🛑🛑🛑 **THE GRINDING IS OURS — WE TRIPLED THE ENGAGED-MODE DAMPER AT V96/V106. V128 RESTORES IT.**
`gp-0x6b26`'s speed schedule `Y` is a **per-mode** LERP reached through the pointer array at
`0xCBE74`. **`MANUAL_MODES = (24,25)`, `ENGAGED_MODES = (26,27)`.** Read straight out of the images:
```
   mode-26 record (0xD7A54, Y@0xD7A5C)     Y[0]     Y[1]     Y[2]    rails from |c2c| (0/20/90 km/h)
   STOCK  (byte-identical to mode 24)     -9830    -5734    -1966     3195 / 5477 / 15974
   V106 onward, carried to V127          -29490   -17202   -16000     1065 / 1826 /  1963
```
🛑 **The rail threshold fell 3.0× / 3.0× / 8.1×.** The detector arms at `cal(0xC620A)` = 12800,
so **on STOCK the term was still LINEAR at the arming threshold at 90 km/h** (15974 > 12800);
**on our builds it rails from 1963 — essentially always.** A railed acceleration term is
`sign(α)·511`: a **bang-bang Coulomb relay**. A relay ratchets; it does not damp.

### ✅ IT UNIFIES THE WHOLE RECORD — FOUR THINGS AT ONCE
1. **The symptom is ENGAGED-ONLY and so is the dose.** Modes 26/27 only; **manual modes 24/25 are
   byte-stock on every build**. [[accord-stock-mode24-equals-mode26-damper-is-ours]] already said
   *"the engaged-only damper is OURS"* — **this is the cell.**
2. **α2 WORKS BY DE-RAILING.** The lane is
   `gp-0x4f50 → EMA1(α0=0xC643C) → (1−z⁻¹) → EMA2(α2=0xC40DC) → gp-0x6c2c`, so lowering α2
   shrinks the term's **INPUT** ⇒ that is why 22→14→8 tracked his reports monotonically: each
   step cut rail duty. **Not a mysterious "selectivity" — a de-rail.**
3. 🛑 **V91/V92's ×1.5 dose on `0xCBE74` measured INERT (ratio 0.99) because the term was
   ALREADY RAILED** — a raise is absorbed by the clamp. **This SUPERSEDES the "saturated counter
   bypasses the record" explanation I gave earlier this session**: that one needs an oscillation
   episode, whereas clamp absorption explains a whole-drive null directly. ✅ Correction recorded.
4. **V107 measured 32.32 % rail duty at 10–25 km/h** and noted *"the symptom map and the rail-duty
   map are the same map"*. **This is the cell that set that map.**

### ✅ V128 BUILT — A RESTORATION, NOT AN EXPERIMENT
```
   0xD7A5C  Y mode 26  [-29490,-17202,-16000] -> [-9830,-5734,-1966]   STOCK
   0xD7A6C  Y mode 27  [-29490,-17202,-16000] -> [-9830,-5734,-1966]   STOCK
```
Base **V127**. 12 payload bytes. image
`2e42e916a118e42a5adabe3156a6b6c33992d8ce90760d3eb144331f271474a7` · rwd
`6d5fa1377bff005f32d2d42b9c531bea303558c7939d7187b056022eeaf36828` · **71/71, CRC 50/50.**
⊕ These are **Honda's own shipped values, byte-identical to the manual-mode records this firmware
already runs** ⇒ calibrated-safe by construction. Largest available de-rail.
✅ **IT DOES NOT CONFOUND V127's EDIT.** `0xC640A` applies **only when the reversal counter is
SATURATED**; the mode record applies **only when it is NOT**. The branches are **mutually exclusive
by construction**, so V128 stays single-variable *per state* and one drive interprets both. The
427 probe measures `|gp-0x6b26|` duty in **both** states.
✅ The builder asserts **manual modes 24/25 byte-identical** (manual feel untouched) and **engaged
modes 26/27 now byte-identical to STOCK**.

### 🛑 RESIDUAL RISK, STATED PLAINLY
[EVIDENCE] the values, the rail arithmetic, the mode assignment, the stock comparison.
[BELIEF] that restoring improves the symptom. **Below the old rail point this removes 3–8× of
acceleration feedback, which is real damping in the LINEAR regime.** Stock shipped exactly these
values so the risk is bounded to *"the car behaves as Honda calibrated it"* — but V96/V106 raised
them for a reason and **that reason is not re-tested here**. ⇒ **if grinding WORSENS, the next
step is a PARTIAL restore sized to the measured duty, NOT a return to −29490.**

## 🛑🛑 **V126 WAS SIZED WRONG — CAUGHT BEFORE FLIGHT. V127 IS THE BUILD.**
**The detector's input is `gp-0x6c2c`, the MOTOR-RATE DERIVATIVE — not driver torque.**
`ld.h -0x6c2c,gp,r10` @`0x428FA`, compared against `cal(0xC620A)=12800` loaded @`0x42910`.
⇒ **the branch fires HANDS-OFF**, on exactly the signal grinding and oscillation excite — and it
is the **same signal `FUN_00036c12` multiplies by `Y`**, so the detector's input and the term's
input are one signal. That is the positive feedback, stated exactly.

### 🛑 AND IT LETS THE VALUE BE SIZED — WHICH V126 WAS NOT
The branch is only ever taken **once the detector has armed**, so `Y` must be sized against the
**arming threshold**, not against "what Honda ships somewhere". Mirroring the decompiled integer
arithmetic exactly (`iVar4 = ((c2c*Y)>>6)*0x111` · `iVar5 = iVar4>>0x12` · clamp ±511):
```
   Y                       b26 at arm    rails from    state when the detector arms
   -8192  stock fallback        1706          3834     RAILED (3.34x over the clamp)
   -3277  V126 as built          682          9584     RAILED (1.33x over the clamp)
   -2453  exact break-even       510         12803     LINEAR (100 % of clamp)
   -1966  Honda Y[2], 90 km/h    409         15974     LINEAR (80 % of clamp)
```
🛑 **−3277 STILL RAILS the instant the detector arms** ⇒ **V126 would have left the term a
bang-bang Coulomb relay in exactly the state it was built to fix.** I chose −3277 for being
Honda-shipped without checking it against the detector's own threshold. ✅ **−1966 is the LARGEST
Honda-shipped value in this family that stays LINEAR at the arming threshold**, still a **strong**
term at **80 % of clamp**, with headroom to `|c2c| = 15974`. It is Honda's own **Y[2]** — the
90 km/h end of the very mode record this branch replaces.

### ✅ V127 BUILT — identical to V126 but for the one halfword
```
   0xC640A   -8192 -> -1966    the oscillation-branch Y   (V126 had -3277)
   0x55DF2    9544 -> 94DA     427 probe source, gp-0x6ABC -> gp-0x6B26
   0x55E10      a3 -> a2       packer sar 3 -> 2, sized to the +-511 clamp
```
image `706363366c017817e34f6f66ece5ea192ca98787f45e45a21e9c33d9b927ed62` ·
rwd `38181d0991ab0d5267dbc67488c5bf27cd6406b0e5eb4a86f33d0da33d2e503c` · **60/60, CRC 50/50.**
⊕ The fallback now **NEVER exceeds** the speed schedule at any speed: creep 0.22×, 24 km/h 0.36×,
44 km/h 0.44×, 64 km/h 0.58×, 90 km/h 1.00×.
✅ **THE SIZING GATE IS NOW A HARD ASSERTION** in the builder — it computes `b26` at the arming
threshold and fails the build if the value is not linear there. **It fails −3277 explicitly.**
A rule someone had to remember is now a check that cannot be forgotten.
🛑 **V126's artifacts are DELETED, not superseded** — it never flew and it does not achieve its
own stated goal, so leaving it flashable is a hazard. Same policy as V123.

### ⭐ A LARGER FINDING THAT THIS BUILD DELIBERATELY DOES **NOT** ACT ON
**The NORMAL speed LERP also rails at mid speeds**: `Y = -4442` at 44 km/h rails from
`|c2c| = 7070`; `Y = -5519` at 24 km/h rails from `5691` — **both far below the 12800 arming
threshold.** ⇒ **the term rails in ORDINARY driving at 15–40 mph, not only in the oscillation
branch**, which is precisely the speed band where the operator reports grinding. Honda's schedule
is only linear at its high-speed end (90 km/h → −1966, rails from 15974).
⇒ **the mode record `0xCBE74` is the bigger lever**, and V91/V92's INERT dose there is now
explained (a saturated counter bypasses the record). **Not taken in V127**: it would confound the
`0xC640A` change on one drive, and V127's probe measures the duty that would size it.

## ✅✅ THE FULL OSCILLATION-RESPONSE CENSUS — `0xC640A` IS THE ONLY MAGNITUDE, AND TWO CORRECTIONS
The saturated reversal counter `gp-0x671a` has **8 instruction sites, 5 consumers + the writer**
— enumerated correctly this time (see the trap below). What each does when the counter saturates:

| site | function | what saturation does |
|---|---|---|
| `0x36C1E` | `FUN_00036c12` | **`Y` = fixed −8192 instead of the speed LERP — the ONLY MAGNITUDE change, and it RAISES the term 1.21–4.17× above 15 km/h** ← **V126's target** |
| `0x3AA70` | `FUN_0003aa2c` | enable flag `0xC6138`=**1** → `0xC6136`=**0** ⇒ **DISABLES** a lane |
| `0x3A4A6` | `FUN_0003a382` | LERP `0xC67B0`: X=[5,10,15] **Y=[1024,1024,1024] — FLAT UNITY** |
| `0x35A06` | `FUN_000352b4` | boolean gate (`setfnc`) on a 2nd-order IIR update |
| `0x35BEA` | `FUN_00035b20` | boolean selector (`setfnc`) between two LERP curves at `0xC7934` |

✅ **`0xC640A` IS THE ONLY CELL IN THE WHOLE OSCILLATION RESPONSE THAT CHANGES A FEEDBACK
MAGNITUDE.** Everything else is a boolean gate or inert ⇒ **V126 targets the right cell, and there
is no second hidden gain jump to chase.**

### 🛑 CORRECTION 1 — `FUN_0003a382`'s use is INERT, not *"the worrying one"*
[[accord-gp671a-blast-radius-not-a-free-lever]] calls the PID's use *"the worrying one — it makes
`T` a shape parameter on a lane already known to be load-bearing."* **The table is FLAT UNITY at
all three points, and its first breakpoint X[0]=5 is at the counter's own CEIL**, so the LERP can
only ever return `Y[0]` = 1024. **Doubly inert.** ⇒ lowering `T` does **not** reshape the PID.
That memory's "five things at once" count should read **two live + three inert/boolean**.

### 🛑 CORRECTION 2 — HONDA'S OSCILLATION RESPONSE IS COHERENT; OUR GAIN IS WHAT BREAKS IT
My first V126 write-up framed the −8192 branch as simply *"the firmware raises a gain"*. The
census shows the design is **deliberate and sensible**: on detecting an oscillation it **disables
a destabilising lane** (`0x3AA70`) **and applies a strong FIXED acceleration feedback**
(`0xC640A`). **That would work — if the fixed term stayed LINEAR.** It does not, because
`|gp-0x6b26|` clamps at 511 and our elevated forward gain makes `|gp-0x6c2c|` far larger than
stock. ⇒ **the defect is the RAIL, not Honda's intent**, and V126's job is to keep the term
inside its linear range rather than to remove Honda's response. ⊕ This also means **−1966 is the
floor, not a target**: cutting further eventually removes the anti-oscillation response itself.

### 🛑🛑 THE SCAN TRAP THAT BIT ME — `ld.bu` ENCODES disp16 AS `(disp & 0xFFFE) | 1`
A whole-image scan for `gp-0x671a` at displacement **`0x98E6` returned ONE hit** — the `st.b`
writer — and I nearly concluded the record's *"8 hits, 6 reader functions"* was stale. **Every
reader is `ld.bu`, which stores the displacement as `0x98E7`.** Scanning both forms returns
**exactly 8**, matching the record. ⇒ [[accord-v850-scan-traps-formatv-and-storezero]]'s
`hw2 = (disp|1)` trap applies to **`ld.bu`/`ld.hu` reads, not just the forms already listed** —
and a *low* count is as much a symptom of it as a wrong one. **Always scan `disp` AND `disp|1`.**
⊕ Ghidra could not help here: `get_xrefs_to 0xFEDF18E6` returns **"No references found"**,
because gp-relative accesses are never resolved to absolute RAM addresses in this program.

## 🛑🛑🛑 **THE OSCILLATION BRANCH — THE FIRMWARE RAISES Y WHEN IT DETECTS AN OSCILLATION. V126 BUILT.**
**A NEW LEVER, and the best-targeted one in the kit's record.** `FUN_00036c12` picks the
`gp-0x6b26` acceleration-feedback scale `Y` three ways — decompiled AND disassembled this session:
```
   if (gp-0x671a < 0xff) and (gp-0x67f4 == 1):
       if gp-0x671a < cal(0xC64FD)=5:  Y = LERP(mode record, index = VOTED VEHICLE SPEED)
       else:                           Y = cal(0xC640A) = -8192   <- ld.h 0x740a,tp,r12 @0x36CB4
   else:                               Y = cal(0xC640C) = -3277   <- ld.h 0x740c,tp,r12 @0x36CBA
   gp-0x6b26 = clamp(((c2c_gated * Y) >> 6) * 273 >> 18, +-cal(0xC407E)=511)
```
🛑 **`gp-0x671a` is the hard-reversal counter and it is CLAMPED to CEIL = 5**
(`min(revcount, CEIL)` @`0x42A12`, the only `st.b` writer image-wide) ⇒ **`>= 5` is reachable ONLY
when the counter has SATURATED** = 5+ hard reversals, held 5.0 s. **The fallback IS the oscillation
branch.** And Honda's schedule tapers `Y` with speed while the fallback is a **flat −8192**:
```
   speed     LERP Y    fallback/LERP          speed     LERP Y    fallback/LERP
    5 km/h    -8806        0.93x              44 km/h    -4442        1.84x  <- HIS EVENT
   15 km/h    -6758        1.21x              64 km/h    -3366        2.43x
   24 km/h    -5519        1.48x              90 km/h    -1966        4.17x
```
⇒ **on detecting an oscillation the firmware MULTIPLIES the term by up to 4×, at exactly the
speeds where the symptoms live**, driving `|gp-0x6b26|` into its 511 rail — where it is
`sign(α)·511`, a **bang-bang Coulomb relay**, V80's measured mechanism. **A relay ratchets; it does
not damp.** A positive-feedback trap: oscillate → detector arms → bigger Y → rail → relay.

### ✅ IT EXPLAINS THREE THINGS AT ONCE, INCLUDING A NULL THE KIT COULD NOT EXPLAIN
1. the **peak-turn oscillation at 44 km/h**, hands-off, engaged — a **1.84×** jump;
2. **grinding at 15–40 mph and NEVER below 5–6 mph** — the ratio is 0.93× at creep and rises
   monotonically with speed. V107 noted *"the symptom map and the rail-duty map are the same
   map"*; **this supplies the mechanism**;
3. ⭐ **why the `0xCBE74` ×1.5 dose MEASURED INERT** — if the counter saturates during the
   manoeuvre the **mode record is BYPASSED entirely**, so no dose on it can act.
   ⇒ [[accord-cbe74-dose-measured-inert-wrong-mode-record]] is **RESOLVED**.

### ✅ V126 BUILT — 5 payload bytes on a V124 base, cal-only, no code or cave edit
```
   0xC640A   -8192 -> -3277    THE EDIT -- the oscillation-branch Y
   0x55DF2    9544 -> 94DA     427 probe source, gp-0x6ABC -> gp-0x6B26
   0x55E10      a3 -> a2       packer sar 3 -> 2, sized to the +-511 clamp
```
image `d6aacb4d563cc7726db8bcf94b659b30341a510dab64a086c93b23c0402707d0` ·
rwd `190231aa4021fe663a7490c1a966a6ef4777241044c3af2bf54caa7306d30d83` · **56/56, CRC 50/50.**
⊕ **−3277 is not invented** — it is Honda's own value at `0xC640C` for **this same variable in
this same function**, so it is inside the calibrated range by construction. New ratios: creep
0.37×, 24 km/h 0.59×, **44 km/h 0.74×**, 64 km/h 0.97×, 90 km/h 1.67× ⇒ at his event, detecting
an oscillation now **REDUCES** Y instead of raising it, a **2.5×** change in the term.
✅ **BLAST RADIUS IS THE SMALLEST IN RECENT MEMORY**: `0xC640A` has **1 reader, 0 writers**
(whole-image byte scan for the tp-displacement **and** instruction-boundary disassembly — the
scan hit `0x36CB6`, the SECOND halfword of a 4-byte `ld.h` starting at `0x36CB4`), and the branch
fires **only while the reversal counter is saturated** ⇒ **every other moment of driving is
behaviourally identical to V124.**

### ✅ THE PROBE MEASURES THE ONE QUANTITY THE KIT HAS GOT WRONG
`wire = min((|gp-0x6b26|·5) >> 2, 0x3FF)` ⇒ the 511 rail maps to **638 of 1023: no clipping**,
LSB 0.8 counts, **rail duty directly countable**. ⚠ 427 is 49.9 Hz and the lane's −3 dB band
(25–153 Hz) is above Nyquist, so this wire **cannot** measure the lane's SPECTRUM — that blindness
is exactly what voided V107's safety case. **Rail duty is a LEVEL statistic**, and undersampling
an ergodic signal leaves it unbiased. This probe measures duty, and nothing else.
🛑 [BELIEF] that lowering `0xC640A` de-rails the term on-car. **Duty CANNOT be predicted
open-loop here** — V107 predicted ≤1.05 % and measured 33.49 %, a **32× miss**, because
`gp-0x6b26 → aggregator → motor → motor rate → gp-0x6c2c` is a **CLOSED LOOP**. Hence the probe
rather than an asserted number. ⊕ Next rung if V126 under-delivers: **−1966**, which never exceeds
the schedule at any speed.

## 🛑🛑 **THE KNEE/K1 LADDER IS EXHAUSTED — V122/V124 IS ITS LAST RUNG**
Every build since V111 has raised the Coulomb knee with K1 scaled to hold the small-signal gain
**exactly**: `(K1/1024)·(12/knee) = 0.0039844`. That invariant has a hard end, because **K1 ≥ 1024
inverts the residual's sign** — friction would exceed `|model|`.
```
   knee    K1 required   possible?      relay saturates at   viscous slope /(deg/s)
    600        204       yes             10.6 deg/s            0.094242   <- STOCK
   1800        612       yes             31.8 deg/s            0.031414   <- V112
   2400        816       yes             42.4 deg/s            0.023561   <- V116
   3000       1020       yes             53.1 deg/s            0.018848   <- V122/V124  LAST RUNG
   3300       1122       NO -- >1023     58.4 deg/s            0.017135
   3600       1224       NO -- >1023     63.7 deg/s            0.015707
```
🛑 **`MEASURED_DUTY` still lists a 3600 rung — it is UNREACHABLE.** Do not propose knee 3300+ as a
gain-holding step; it cannot be built. **The friction axis is closed at V124.** Further grind-#1
work must come from a different lever, which is exactly why `0xC642A/C` (pending V125's probe)
matters.

### 🛑🛑 AND THE RELAY IS **SATURATED THROUGH THE OSCILLATION** — STRUCTURALLY, NOT BY CHOICE
A 2°-peak 7.8 Hz oscillation has peak rate **98 deg/s**. V124's relay saturates at **53.1 deg/s**.
⇒ through the operator's peak-turn oscillation the friction term is **past its knee**, i.e. a
**constant-magnitude force opposing motion — textbook Coulomb friction, the classic stick-slip and
limit-cycle driver.** Making it viscous across that range would need knee **5542 / K1 1884** —
**impossible** by the ceiling above.

⊕ **THE TRADE IS PICK-TWO, and it is the operator's own tension made precise.** With
`plateau = K1/1024`, `sat_rate = knee/56.545`, `slope = plateau/sat_rate`, you may choose any two:
- **grind #1** wants a **large low-rate slope**;
- **the peak-turn oscillation** wants a **small plateau** (weak Coulomb) **and a high sat rate**;
- his standing instruction wants **low apparent friction** overall.
One relay cannot serve all three. ⇒ **a genuinely new lever is required for the oscillation**, not
another rung. ⚠ The one same-axis option left is **knee 3000→4200 with K1 HELD at 1020**: low-rate
friction −29 %, saturation 53→74 deg/s, plateau unchanged — **characterised, NOT recommended**,
because it trades measured grind performance for an unmeasured oscillation benefit and would
confound V124's three existing edits.

## 🛑🛑 **V122 COULD NOT HAVE IMPROVED AUTHORITY — IT CARRIES V112'S GAIN, UNCHANGED**
The operator flew V122 and reported *"on the improved LKAS authority, it does not feel like it has
improved at all."* **That is the correct result for that build.** Byte-verified from the images:
```
   build   gain 0xC6CD0   full-command forward   clamp 0xC61B2      governor 0xC6202
   STOCK      65535             30719            512  CLIPS 98.3%     4762  9.30x free
   V112        5346              2505           3072  (82 % used)     4762  1.90x free
   V122        5346              2505           3072  (82 % used)     4762  1.90x free   <- SAME AS V112
   V124        7128              3341           4096  (82 % used)     4762  1.43x free
```
🛑 **V112 and V122 have the IDENTICAL forward gain.** V122's edits were knee 1800→3000, K1 612→1020
and α2 14→8 — **all three are friction/shape, none is authority.** ⇒ his null is **expected, not
disappointing**, and **V124 is the first build since V112 to raise authority at all** (×1.333).

### ✅ THE 8× FORWARD CHAIN IS CLEAN END TO END — NOTHING DOWNSTREAM CLIPS IT
At full LKAS command the forward value is **3341**, which sits **under the 4096 clamp (82 % used)**
and **under the 4762 governor with 1.43× headroom**. ⇒ **the whole ×1.333 reaches the motor.**
⊕ **The V123 clamp defect is now quantified, not merely asserted**: 8× against the old 3072 clamp
gives 3341 > 3072 ⇒ **8.1 % clipped**, an effective 7.34×. Raising the clamps with the gain was
necessary; the builder's `clamp/gain == 1.000` assertion is the right invariant.
⊕ **Headroom to the governor allows ~11.4× before `0xC6202` binds** — so 8× is nowhere near it, and
**`0xC6202` must NOT be raised** (it is lockstep-shadowed → fault `0x17`).
⚠ [BELIEF] the "full command = 15360 internal units" figure is from the standing record, not
re-measured here. The clamp/governor comparison is in those same units, so the ORDERING is robust
even if the scale is off; an absolute claim about clip margin is not.

### ✅ AND THE "OUR GAIN NEVER REACHES LKAS" SCARE IS REFUTED
`0xC646C` = 891 = stock on every build, and reader #3 (`FUN_0002b62c`) multiplies by it — but a
fresh decompile shows that function is the **BASE-ASSIST** path: two LERP lanes × a ramped enable,
`× polarity × 0xC646C >> 15`, clamped by a per-mode table at `0xC7090`, written to **`gp-0x6AF0`**.
It is **not** the delivered-LKAS formula. The LKAS forward reader is the one V57 moved onto
`0xC6CD0`, which every build since has scaled. ⇒ **the gain edits do reach LKAS.**

## ✅✅ THE 427 PROBE INSTRUMENT IS NOW VALIDATED — and it was BROKEN in three ways first
**Run the control before the measurement, again.** `score_v125_probe.py` was written, then run
against r24 as a dry-run *before* any V125 flight. It reported a clean-looking answer — phase
+73.9°, coherence 1.000 — that was **entirely artefact**. Three defects, each found by a control:

| # | defect | symptom | fix |
|---|---|---|---|
| 1 | `nperseg == NW` ⇒ Welch has ONE segment | coherence identically **1.000**, so the shuffled control could never fail | `NP = NW//4`, then `NW = 512` |
| 2 | **427 is a 50 Hz channel; `cs_rate` is 100 Hz** — truncated to a common INDEX, not TIME | 2× misalignment; coherence **0.512 → 0.049** | regrid both on the 427 frames' own timestamps |
| 3 | coherence **bias ≈ 1/n_segments** | at NW=128 the shuffled null read **0.347** vs a real 0.510 — almost all "coherence" was bias | permutation null (20 shuffles), bar is the **EXCESS** |

✅ **THE POSITIVE CONTROL NOW PASSES DECISIVELY.** r24 (V122) taps `gp-0x6ABC` = wheel rate
× 4.7121, so the wire *is* a scaled |rate| and the answer is known in advance:
```
   corr(|rate|, wire)                  +0.9832
   corr(packer model, wire)            +0.9832    (p50 2 vs 3, p99 319 vs 321 -- BYTE-ACCURATE)
   coherence 6-9 Hz  0.335  vs  permutation null 0.069 +- 0.004
   EXCESS 0.266   z = +60.7            => INSTRUMENT OK
```
⊕ The packer model `min((|rate|·4.7121·5)>>3, 0x3FF)` reproduces the real wire byte-accurately
⇒ **the cave, the tap and the decode are all confirmed on-car.**

### 🛑 TWO FACTS THIS TURNED UP THAT CHANGE HOW CACHES MUST BE READ
1. **`raw14_b4` / `probe` IS NOT CAVE TELEMETRY ON POST-V106 ROUTES.** It is CAN **0x14A byte 4**,
   the *legacy* 5-bit field (bits 7:3) that the V70–V88 caves wrote. V106+ caves write **427
   (0x1AB)** instead. On r24 its low 3 bits are **constant** and its 5-bit field does not track
   anything of ours (corr with |rate| **+0.06**) — yet the extractor still calls it `probe`.
   ⇒ **Any post-V106 analysis that read `probe` as cave output was reading Honda's bits.**
   The real wire is `((b0 & 3) << 8) | b1` on 0x1AB, and it is `ab_mt` in the caches.
2. **🛑 THE 427 WIRE CANNOT MEASURE GRIND #1.** It arrives at **49.9 Hz ⇒ Nyquist 24.95 Hz**,
   and grind #1's band is **21–26 Hz**, which straddles it. Cave telemetry is a **6–9 Hz
   instrument only**. (The 21–26 Hz endpoint itself is safe — it comes from `cs_rate` at 99.8 Hz.)

✅ `--control r24` is now a permanent self-test: change the scorer, re-run it, and if the EXCESS
moves the script broke rather than the car.

## 🛑 A BROAD VIRGINITY SWEEP IS THE WRONG TOOL — and V125's scorer is pre-written
**The sweep, and why it failed.** I scanned `[0xC6000, 0xC7000)` for cells that are virgin across all
117 builds and hold a plausible IIR-alpha value (1-512), then kept those whose implied corner lands
in 1-40 Hz. **It returned 266 "candidates" — which is noise.** The filter cannot tell an alpha from a
LERP table entry, a threshold or a deadband: `0xC61B8` = 102 is in the list, and the kit already knows
it is the **pre-gain deadband**, not a filter coefficient
([[reference-accord-pregain-deadband-c61b8]]).
⇒ **The targeted method works, the shotgun does not.** Every lever found this session — the forward
clamps `0xC61B2/B4`, the trim IIR `0xC63D2`, the candidate `0xC642A/C` — came from **enumerating the
readers of a specific cell and tracing what each one does**, not from scanning for value patterns.
✅ **Recorded so the next session does not repeat the sweep.** A cell is only a lever once its
CONSUMER is traced; virginity and a plausible value are necessary, nowhere near sufficient.

### ✅ `rlog-tools/score/score_v125_probe.py` — written BEFORE the drive
V125 puts `gp-0x6AF0` (reader #3's output) on CAN 427 at sar 4. The scorer asks **one** question:
```
   delivered phase of |gp-0x6af0| vs |wheel rate| at 6-9 Hz, coherence-weighted,
   with a MANDATORY shuffled control

     near +90 deg  -> reader #3 DAMPS      -> cutting 0xC642A/C is the V94 direction, lever CLOSED
     near -90 deg  -> reader #3 ANTI-DAMPS -> cutting it HELPS, build 194 -> ~29
     low coherence -> NOT RESOLVED, build neither way
```
⊕ Same method that settled `gp-0x6b26` after V94 (+137/+139° ⇒ a real damper). ⚠ The wire carries a
**magnitude**, so the sign is lost and only the ENVELOPE phase is recoverable — the scorer says so and
refuses to interpret a phase whose coherence does not clear the shuffled control.
⇒ **One drive on V125 now decides the best-shaped remaining lever**, instead of leaving it an
unbounded guess.

## 🛑 "SAFE BY CONSTRUCTION" WAS AN OVER-CLAIM — and a better-shaped lever that I am NOT proposing
### The over-claim, corrected
For V124's trim edit (`0xC63D2` 6→3) I argued *"reducing the magnitude of a feedback term cannot
destabilise a stable loop, whatever its phase."* 🛑 **That is only true for DESTABILISING feedback.
If the term is dissipative, cutting it is the V94 direction** — and V94 is exactly the case where a
term that looked structurally like **inertia** measured as a **damper** (+137° delivered vs wheel
rate), and removing it made the operator abort. **Structure ≠ delivered sign**, and I do not have the
delivered phase for these feedback paths.
✅ **But the RISK IS BOUNDED, and V124 stands:**
```
   reader #5 is clamped to +-512 = 5.00 % of the aggregator's +-10240
   7.8 Hz transmission:  cal 6 -> 0.1191   cal 3 -> 0.0598
   => the edit moves at most 0.0593 x 5.00 % = 0.297 % of aggregator authority
   V94 removed up to 5.00 % and the drive was aborted  =>  V124's edit is 17x smaller
```
⇒ **[LOW RISK, bounded at 0.297 % of aggregator authority] — not [SAFE BY CONSTRUCTION].** The build
is unchanged; the claim is downgraded.

### A better-shaped candidate, deliberately NOT proposed
```
   0xC642A / 0xC642C = 194   fc 30.15 Hz   |H(7.8 Hz)| 0.9739   VIRGIN on all 117 builds
```
These are reader #3's two input IIRs, and at **fc 30 Hz they pass 97 % of the 7.8 Hz content** — the
path is nearly unfiltered at the oscillation. Lowering 194 → ~29 (fc 4.5 Hz) would **halve** its
7.8 Hz contribution while leaving ≤2 Hz essentially untouched (|H(1 Hz)| 1.000 → 0.976) —
**better selectivity than `alpha2` achieves.**
🛑 **NOT PROPOSED.** Reader #3's output authority is **not bounded** the way reader #5's ±512 clamp
bounds it, so **the downside cannot be capped without knowing its delivered sign.** Proposing it would
repeat exactly the reasoning that this section just retracted.
✅ **What would unlock it:** the delivered phase of reader #3's output (`gp-0x6af0`) against wheel
rate at 6-9 Hz — the same measurement that settled `gp-0x6b26` after V94. **That needs the cell on the
wire, i.e. a 427 repoint** (a 2-byte displacement edit, the proven class — NOT a cave).

## 🛑 CORRECTION: THE "LKAS GAIN" HAS **NEVER** TOUCHED THE FEEDBACK PATHS
```
   build     0xC646C (readers #3/#5/#6)   0xC6CD0 (forward reader #1)
   STOCK          891                        65535
   V90            891                         3564   (4x)
   V101           891                         7128   (8x)
   V112/V122      891                         5346   (6x)
   V124           891                         7128   (8x)
```
✅ **`0xC646C` is 891 = STOCK on EVERY build ever made.** V57 decoupled only the **forward** reader
(#1, `0x2a1ee`) onto `0xC6CD0`; readers **#3 (`0x2b656`), #5 (`0x36686`), #6 (`0x3684a`)** still
multiply by `0xC646C`. Confirmed from the `FUN_0002b62c` decompile: its gain operand is
`tp+0x746c` = **`0xC646C`**, not `0xC6CD0`.
🛑 **⇒ MY V124 RATIONALE WAS WRONG ON ONE LEG.** I claimed the 8× rise multiplies the
positive-feedback trim path by 1.333× and that `0xC63D2` 6→3 pays for it. **The gain rise does not
reach that path at all.**
✅ **TWO CONSEQUENCES, BOTH GOOD:**
1. **The 8× rise is SAFER than I stated.** It touches only the forward path; **the feedback loops
   stay at stock gain**, so it cannot destabilise them. The `m^1.74` vibration law was measured with
   the feedback paths already at stock, so it still applies as measured.
2. **The `0xC63D2` trim lever still stands on its own merits** — it halves a positive-feedback
   contribution at 7.8 Hz (0.1191 → 0.0598) and lowering a feedback magnitude is safe by
   construction. **What is withdrawn is the "it pays for the gain" framing, not the lever.**
⊕ It also re-frames [[reference-accord-c646c-shared-gain-not-lkas-only]]'s warning: that note said
raising `0xC646C` for "4x authority" silently raised two raw-sensor feedback paths. **V57's decoupling
already fixed that, permanently — and no build since has re-coupled them.**
✅ The V124 builder's comments are corrected in place; the image is unchanged (the error was in the
rationale, not the bytes).

## ✅ DELIVERY IS **NOT** SATURATED — V123's gain rise should bite, but with diminishing returns
Before trusting V123's 8× I checked whether the car is already delivering its maximum at the rail.
**It is not.**
```
   30-60 deg (where the rail lives):
     cmd    0-2000   |rate| p50 18.9   p90  66.7    rate per 1000 cmd 18.93
     cmd 2000-3500              24.0        77.6                       8.72
     cmd 3500-4095              19.3        34.9                       5.09
     cmd      4096              26.5       112.1                       6.47
   manual overall:  p50 51.4   p90 123.3   p99 174.5
```
✅ **Rate still RISES with command** (p50 18.9 → 26.5, p90 66.7 → 112.1) ⇒ **nothing hard-clips the
delivery**; the efficiency fall is a **load** effect, not a rail. **This supports V123's gain rise.**
🛑 **But efficiency falls 2.9× from low command to the rail (18.93 → 6.47 per 1000 cmd)** ⇒ **8× will
NOT buy 1.33× more rate. Expect roughly 1.1-1.2×.** Do not promise the clamp ratio.
⭐ **THE AUTHORITY GAP, QUANTIFIED FOR THE FIRST TIME:** at **maximum** command in a 30-60° turn the
car manages **p50 26.5 deg/s**, against **51.4 deg/s** the driver achieves manually. ⇒ **LKAS at full
command delivers about HALF the driver's ordinary steering rate.** That is the operator's complaint,
in one number, and it is why the command winds up to the rail.
⊕ Combined with the windup finding (tracking error **101×** larger at the rail) the picture is
coherent: **the car under-delivers, openpilot winds up, the loop rings at 7.81 Hz, and the command
carries that same 7.81 Hz peak.**


---

## 📚 OLDER SECTIONS ARE IN THE ARCHIVE
Retired 2026-08-28 to keep this file under the 256 KB `Read` cap:
**`docs/archive/STATE-ARCHIVE-2026-08-28b.md`** (this split) and
**`docs/archive/STATE-ARCHIVE-2026-08-28.md`** (the first). Records, not instructions;
where they disagree with this file, **this file wins**.
