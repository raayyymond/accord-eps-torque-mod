# -*- coding: utf-8 -*-
r"""V285 -- V282 + **Kp = 0** on the LKAS rate PID.  ONE RECORD, SLOT 7.  CAL-ONLY.  NO CAVE CHANGE.

    0xE5378   X  (0, 68, 112, 136, 208)          UNTOUCHED
              Y  (248, 248, 248, 248, 248)  ->  (0, 0, 0, 0, 0)

Ten payload bytes written at 0xE5384..0xE538D (of which FIVE actually change value -- the Y high bytes
are already 0x00), plus one 4-byte page CRC at 0xE5FFC.  No code byte, no cave byte, no other cal, no
other slot, no X knot.

=== CLASS OF BUILD -- and it is not a gain re-shape ==============================================
**V285 is the first build in the whole post-V38 arc to run the LKAS rate PID with only ONE LIVE TERM.**
It is a STRUCTURAL REDUCTION OF THE CONTROLLER, not a re-tune of it.  Under this image the PID sum has
three addends of which two are identically zero:

    sum = (I >> 7) + P + D      with  Ki = 0  (0xC63E6, carried from V282)  and now  Kp = 0
        =    0     + 0  + D

The arc, for context:  V38-V52 authority / filters / poles / caves - V53-V61 telemetry probes and lane
mutes - V62-V73 the rate lane (r24/r26) - V74-V83a the base-assist damper - V84 damper reverted -
V280 rev 2 the assist map LINEARISED - V281 rev 3 Kp FLATTENED to 248 - V282 the r24 comparator tap
(telemetry only) - V283 the INTEGRAL TERM added, Ki 50 -- FLOWN and REJECTED - V284 a SHAPED Kp table --
BUILT, four-way attacked, SHELVED DO-NOT-FLASH.
Every one of those moved a LEVEL, a SHAPE, a TERM's value or an INSTRUMENT.  **V285 deletes a term.**

Operator, 2026-09-04, verbatim:
    "I don't like the direction this firmware has gone.  We should keep Kp fixed, if not 0.  I'm thinking
     about doing a Ziegler-Nichols tuned PID loop for angular acceleration.  This means we need to set
     Kp=0, then increase Kd to get Ku."
    "Frontier firmware: V282."  -  "Let's do Kp=0 (angular rate) and best, most valuable telemetry on V285."

=== BASE IS V282 -- NOT V283, NOT V284 =========================================================
V285 descends from `_v282_..._plain_image.bin` (sha256 0ea98d06...), so `0xC63E6` **Ki = 0** and the Kp
record is V281 rev 3's flat 248.  Asserted on the base AND on the built image AND on the decoded .rwd.
  - **V283 (Ki 50) FLEW and was REJECTED.**  Its own prereg PASSED (stalls 7 -> 1, (b) 87 %, (c) 0.048)
    but the operator rejects the integrator on principle: in the acceleration frame openpilot commands,
    our P is already the integral, so our I is a DOUBLE integral.  A measured residual seals it -- the
    EPS integrator does not clear at disengage (139-383 counts still delivered 0.5-1.0 s after
    STEER_REQUEST drops; both Ki-0 builds are at zero within 0.5 s).
  - **V284 (shaped Kp) is SHELVED, DO-NOT-FLASH.**  All four adversaries returned FLASH-with-caveats and
    the build was sound -- the LEVER was not.  Measured ring loop gain at flat Kp 248 is
    **0.976 [0.944-0.990]** (per-episode complex-ACF fit), so headroom is 1.0-5.6 % and V284 spent
    2.1-5.4 % of it.  **GAIN IS SPENT AS A LEVER ON THIS LOOP.**  V285 moves the other way.

=== PURPOSE -- the Ziegler-Nichols P-only condition, in the ACCELERATION frame ===================
Frame mapping, established in `docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md`
(`studies/pidframe/pid_frame_sizing.py`, image-read):  relative to ANGLE, our I -> proportional,
our **P -> derivative**, our **D -> 2nd derivative**.  So in the ACCELERATION frame that openpilot
actually commands (its output is modelled as a torque, i.e. proportional to angular acceleration):

    accel-frame PROPORTIONAL gain  =  our **D**   (Kd = 128 at 0xE511C, i.e. 0.016 s)
    accel-frame INTEGRAL     gain  =  our **P**   (Kp = 248, i.e. 0.969)
    accel-frame DERIVATIVE         =  HAS NO HOME IN THIS FIRMWARE -- the sum has exactly three addends
                                      and none of them is a second difference of E.

**Kp = 0 therefore removes accel-frame INTEGRAL action and leaves a pure accel-frame P controller.**
That is exactly the Ziegler-Nichols Ku-hunt configuration.  The NEXT build raises Kd toward Ku
-- 🛑 **but read the Ku block immediately below BEFORE planning it: Ku is reachable with NO clamp
backstop, and the mode that sets it is above the 427 tap's Nyquist, i.e. unobservable on today's wire.**

**WHERE Ku ACTUALLY IS -- and there is NO CLAMP BACKSTOP ON A Kd SWEEP.**
  - **`Ku` (as an `0xE511C` Kd cell value) ~ 227, [217 - 270].  `Tu` ~ 36 ms.**  The binding instability
    is a classic **Nyquist -180 deg crossing at 27-32 Hz** -- **NEITHER symptom band** (not the 7.3 Hz
    ring, not the 20 Hz creep grind).
  - **The anchor is a MEASURED gain margin**, `CREEP-20HZ-LOOP-ID-2026-09-03.md`, the estimator table's
    **bar-IV** rows: `1.75x @ 23.4 Hz` (Kp 295) and `1.32x @ 22.4 Hz` (Kp 470).  `Ku = Kd x GM`
    = 128 x 1.75 = **224**, against `zn285`'s independent **217**.  Two routes, ~3 % apart.
    ⚠ **CAVEAT TO CARRY: only the bar-IV estimator family finds a crossing at all** -- every other row
    in that table reads "none".  The number rests on one family.

  🛑 **THE ORDERING, AND IT IS THE UNCOMFORTABLE ONE:**

        Ku (Nyquist, 27-32 Hz) = 227   <   D clamp bites 845-1489   <   ring-magnitude root 859

    ⇒ **THE +-10240 D CLAMP DOES *NOT* BITE FIRST.  Ku IS PHYSICALLY REACHABLE AT Kd ~ 227, WITH NO
    SATURATION BACKSTOP.**  An earlier draft of this docstring said the opposite -- that a Kd sweep
    would be protected by the clamp and would only find a clamp-limited limit cycle.  **That was wrong,
    and it was wrong in the REASSURING direction, which is the worst kind of error to leave in a
    build's own docstring.**  A Kd sweep past ~227 goes genuinely unstable.
  - **What `Ku = 859` actually was:** the Kd at which the **7.3 Hz ring's MAGNITUDE** reaches unity.
    That is a real quantity and it is not retracted as a measurement -- it is simply **not Ku**, because
    a different instability (the 27-32 Hz Nyquist crossing) arrives at 227, long before it.
    🛑 Also **RETRACTED as a Ku estimate: `Ku ~ 143-151 / Tu ~ 49 ms`** (the orchestrator's first
    extrapolation).  Do not cite either number as Ku.
  - 🛑 **AND THE 27-32 Hz MODE IS INVISIBLE ON THE WIRE TODAY.**  The 427 delivered-torque tap runs at
    50 Hz, so its **Nyquist is 25 Hz** -- the binding instability sits **ABOVE** it.  Nothing currently
    flying can observe the mode that sets Ku; it would alias.  **A Kd sweep therefore cannot be scored
    on the instrument that would have to catch it going unstable.**  Treat that as a hard gate on any
    future Kd build, not a footnote.
  - **`Kd` is bracketed from BOTH sides: `Kd` in `[118, 227]` at Kp 248.**  The **7.3 Hz ring gets
    BETTER with more Kd** (lower root 118 -- a Kd CUT re-arms the cycle); the **27-32 Hz mode gets
    WORSE**.  **Today's Kd = 128 sits near the FLOOR** -- 1.08x above the root, 1.77x below Ku.
    At **Kp = 0 the lower root falls to ~65**, so **V285's Kd 128 is ~2x clear of it.**
    🛑 A Kd CUT remains DO-NOT-FLASH.
  - 🛑 **`zn285`'s pass-1 ZN constants are RETRACTED AS UNSTABLE, not merely stale:**
    **ZN-PI (Kp 108 / Kd 387) has GM 0.69x** and **ZN-PID (Kp 241 / Kd 515) has GM 0.51x** -- both
    **below 1.0, i.e. already unstable.**  Neither is a candidate.  **The understeer point SURVIVES and
    still matters:** ZN is a stability recipe, the operator's live complaint is understeer, and the two
    pull opposite ways -- any ZN form trades delivered rate for margin.
  - ⭐ **THE STRONGEST RESULT OF THE SESSION, and it is a convergence:** the **revised ZN-PID gives
    `Kd = 162`**, which is the loop-shape study's independent candidate **F (`Kd = 160`) to within 1 %.**
    Two methods with no shared derivation landing on the same cell value.  [Report, not this build --
    V285 leaves Kd at 128.]

=== PREDICTED EFFECT -- recomputed in [4] from IMAGE-READ Kp/Kd, not quoted ======================
The output lag, the taper, the 5346 forward gain, the feedback EMA and the PLANT are all common to P
and D and cancel exactly in the ratio |C(Kp=0)| / |C(Kp=248)|, so this IS the delivered-surface ratio at
every point downstream.  Tick rate T = 1.000 ms [EVIDENCE: `FUN_00028ea6` has one caller `FUN_0002214a`
at 0x22522, which is the 1 kHz control task -- OSTM0CMP 79999 / 80 MHz PCLK, corroborated by the
`0xC64DF = 100` dwell measured at 100.00 ms on the bus; no divider between task entry and the call].

    f (Hz)   |C| Kp248    |C| Kp0    ratio     loss      d(phase)
      1       0.9743      0.1005     0.103    -89.7 %    +83.9 deg
      7.3     1.2286      0.7338     0.597    -40.3 %    +52.0 deg
      9.638   1.3905      0.9686     0.697    -30.3 %    +44.1 deg
     13.5     1.7002      1.3568     0.798    -20.2 %    +34.7 deg
     20       2.2848      2.0093     0.879    -12.1 %    +25.0 deg

[4] recomputes every row of that table from the Kp/Kd READ OUT OF THE BUILT IMAGE with an implementation
written here from the disassembly, and asserts it against `zn285`'s independently-computed values.

**THE PHASE COLUMN IS A CORRECTION, and it points the safe way.**  The orchestrator's first note said
removing P "removes ~90 deg of lag."  **That is backwards.**  In the rate frame **P is phase-FLAT (0 deg)**
and **D leads by 86-90 deg**, so removing the flat component rotates the controller TOWARD +90 -- it
**ADDS lead**.  Consequences, all from `zn285` on measured arm splits:

    metric                              V282 as built      V285 (Kp 0)
    ring return ratio                   ~0.98              **0.861**
    GAIN MARGIN                         1.77x              **2.11x**
    Re @ 20 Hz (aggregator damping)     +2.06              +2.59
    loop phase change @ 13.5 Hz         0 deg              +34.7 deg  (margin RETURNED)
    damping -> pumping crossover        61 Hz              82 Hz

=> **V285 should be QUIETER than V282, and self-sustained oscillation is NOT expected.**  Every stability
gate we have improves.  [BELIEF on the absolute level, which rests on a plant-free arm model; EVIDENCE on
the arm splits, the phases and the ratio table.]  ⚠ The ring and GM figures come from the corrected
gain-margin anchor and supersede `zn285`'s 0.843; the ORDERING (V285 quieter, with more margin) is
unaffected by the revision and is what is robust.

=== 🛑 THE COST -- AND THE ORCHESTRATOR'S RECOMMENDATION IS **DO NOT FLY THIS** ==================
**V285 IS A BENCH / SYSTEM-IDENTIFICATION CONFIG, NOT A DRIVE CANDIDATE.**
**IT DELIVERS ZERO STEADY-STATE LANE KEEPING.  Not "weak", not "reduced" -- ZERO.**

The chain is exact, not modelled: at steady state `dE = 0`, so `D = 0`; with `Kp = 0` and `Ki = 0` the
other two addends are identically 0; so `S = 0`.  `L(0) = 0` EXACTLY, at every plant gain.  Verified
three independent ways -- the orchestrator's integer mirror (0.000 deg/s at every plant gain), `zn285`'s
mirror (0.0 % of a 25 deg/s request at 4 s, vs V282's 53.5 %), and [4] of this script.

`zn285` settled the plant's type FROM THE WIRE rather than by argument.  The r34/r35 stalled-push strata
show a STEADY tap |T| of 657-828 counts held for 1-3 s against a STEADY, BOUNDED, NON-ZERO wheel rate of
5.8-34.1 deg/s.  That excludes an integrator in rate (which would ramp) and excludes a differentiator in
rate (which would give zero rate).  **The plant from PID output to measured rate is TYPE 0**, DC gain
g = 0.007-0.052 deg/s per T count.  With `C(s) = Kd_r*s` and a TYPE-0 plant, **`L(0) = 0` EXACTLY** and
the steady-state rate error is **100 %**.  The integer mirror, 25 deg/s request, mid-load plant:

    build / tune                              rate at 4 s   % of request   |T|
    V282 as built (Kp 248, Kd 128, Ki 0)      13.38 deg/s      53.5 %      446
    V283          (Ki 50)                     24.16 deg/s      96.6 %      806
    ** V285       (Kp 0,  Kd 128, Ki 0)        0.00 deg/s       0.0 %        0 **

**The only thing that reaches the motor on this image is `d(32*sp)/dt` -- a kick on command CHANGE and
nothing held.**  Lane keeping will not work.  The operator would be steering the car.  Do not read "the
car wandered" as a defect: it is the design.

🛑 **THE ORCHESTRATOR'S RECOMMENDATION IS NOT TO FLY V285.**  It is built, hash-verified and safe to
hold on the shelf; the case for driving it has to be made separately, and it would have to be on a road
where the car not steering itself is acceptable.

**AND THE HONEST OTHER HALF, because it is WHY this config exists:** every stability metric improves.
    ring return ratio      0.861   (vs today's ~0.98)
    gain margin            2.11x   (vs today's 1.77x)
    controller lead        +52 deg at 7.3 Hz, +25 deg at 20 Hz
The direction of the cost is also the SAFE one -- it under-delivers and cannot over-assist, and it is
not a brick in any sense.  V285 buys MARGIN and identification value; it spends ALL of the DC authority
to do it.

=== THE NULL-LICENSING SENTENCE, AND THE DRIVE SPEC IT FORCES ====================================
Because the loop goes inert below ~1 Hz, **the ring will appear as a DAMPED TRANSIENT AFTER A
DISTURBANCE, NOT AS A STANDING HUM.**  There is no longer a low-frequency term to keep re-exciting it.

=> **THE DRIVE MUST SEEK BUMPS, QUICK CORRECTIONS AND STALL RELEASES WHILE LATERALLY ENGAGED.**
    Smooth cruising on this build returns an UNINTERPRETABLE NULL -- the mode is simply never excited.
    ("Engaged" means LATERALLY engaged: 0xE4 STEER_REQUEST and 0x18F SCA.  Longitudinal-only is a confound.)

**Written before the drive:**
    "If V285's engaged frames show no 17-21 Hz energy AND no 7 Hz energy, that licenses NOTHING about
     either mode -- it is fully explained by the loop having gone inert below ~1 Hz and the mode never
     being excited.  The interpretable readout is the DECAY of a burst after a disturbance, on
     `gp-0x6a56` (0x18F bytes[2:3], 100 Hz), scored as ring-down Q, together with the 427 tap |T| showing
     the kick-on-change-only signature (|T| non-zero only while the demand index is MOVING, and
     returning to ~0 within a few ticks of it settling).  If |T| is instead sustained during a HELD
     demand, then Kp = 0 did not reach the live lookup -- the selector is not 7 -- and no further Kp or
     Kd cell edit is licensed until the selector is tapped."

**DO NOT CLAIM V285 FIXES GRINDING.**  A quiet 20 Hz line on this build is CONFOUNDED with the loop
simply going weak.  The predicted 20 Hz authority loss is only -12.1 %, so a large observed drop in the
20 Hz line would be evidence of the excitation vanishing, not of the mode being damped.  The grind lever
(`0xC6446` = 5244) is BYTE-UNTOUCHED here and is asserted so in [3].

**AND THE P-ONLY DEADBAND IS EXPECTED TO RETURN, PROBABLY WORSE.**  V281 rev 3 (flat Kp 248, Ki 0)
created it -- SEVEN stalled runs at idx 54-79, 14.8 s, tap 778-868 counts.  **Ki 50 was what cured it**
(7 -> 1 stalls), and **Ki is 0 here.**  Removing Kp as well removes the term that was breaking those
stalls at all.  The operator lists *"stuttering when the wheel is turning"* as an open symptom; this
build is expected to make it WORSE, not better.  Nothing in this image addresses it.

=== TELEMETRY -- NOTHING IS ADDED, AND THAT IS A DELIBERATE, JUSTIFIED DECISION ==================
**THE BUILD IS NOT UNOBSERVABLE.  IT CARRIES NO *NEW* INSTRUMENT BECAUSE THE INSTRUMENTS ALREADY
EXIST AND ALREADY FLY, BYTE-IDENTICAL, ON THIS EXACT IMAGE.**  Subagent `telem285`
(`docs/specs/design/V285-TELEMETRY-2026-09-04.md`) evaluated four candidates and returned BUILD NOTHING:
three are redundant with channels already on the wire, and the fourth is structurally vacuous.

The channels this build is read by, all asserted byte-identical to V282 in [3]:
  1. **`gp-0x6a56` on CAN 0x18F bytes[2:3], 100 Hz** -- the physical MOTION, 10x finer LSB than the
     0x14A copy, and the literal upstream input to this loop's own feedback EMA.  The operator's standing
     rule is to score the motion, not the lever's output.  **This is the primary instrument.**
  2. **`T` (`gp-0x6b38`) on CAN 0x1AB / 427, 50 Hz** -- the delivered lane torque, packer window
     0x55DF0-0x55E11, field `(sign(T) << 9) | (|T| >> 3)`, saturation flag `|field| >= 309`.
     Cross-check and rail exclusion.
  3. **0x14A byte 4 bits 6 / 5 / 4** -- V282's r24 comparator tap (`|r24| >= |T|`, `|r24| >= |agg|`,
     `sign(r24)`), cave 0xC4B34, hook 0x55C0E.  Unaffected by this edit; it is how the r24 arm's share
     is resolved per episode, which is what `zn285` needs to pin Ku with no sweep.

**AND WHY THE OBVIOUS FOURTH INSTRUMENT IS *STRUCTURALLY VACUOUS ON THIS BUILD*, verified here:**
a `|D| >= |P|` comparator rung pins to 1 BY CONSTRUCTION.  Under Kp = 0 AND Ki = 0 the controller has
exactly ONE live term, so there is no ratio to compare -- `P == 0` identically, and `sum == D` identically.
Asserted numerically in [4] over the built image, not taken on trust.

**FOR THE NEXT BUILD, NOT THIS ONE -- four free tap sites, found in the decompile this session.**
`FUN_00028ea6` already PUBLISHES all four PID quantities to gp RAM every tick, at the function tail:
    `gp-0x6b32` = P (clamped)   `gp-0x6b36` = D (clamped)   `gp-0x6b34` = the PID sum   `gp-0x6b2e` = output
On V285, `gp-0x6b32` is identically 0 and `gp-0x6b34 == gp-0x6b36` identically.  A future cave could read
D's MAGNITUDE directly from `gp-0x6b36` with no recomputation.  **Recorded as a finding; NOT built here.**

=== THE LERP, AND WHY Kp = 0 IS SAFE ARITHMETIC -- re-derived from the V282 IMAGE this session ====
GhidraMCP `decompile_function` on the V282 program (decompile-first, per the standing instruction), then
the byte reads.  The Kp lookup is `FUN_00028ea6` 0x29DC6-0x29E36:

    0x29DC6  mov   0xcb994, r10          r10 = the Kp POINTER TABLE base
    0x29DD0  sld.w 0x0, ep, ep           ep  = *(0xCB994 + slot*4)  = THE RECORD BASE  <- WALK THE POINTER
    0x29DDA  st.h  r7, -0x697a, gp       (the demand index is published to RAM here -- a future tap site)
    0x29DDE  sld.hu 0x2, ep, r9          r9  = X[0]   <- rec+0x02 IS X[0], explicit; no implicit X0
    0x29DE2  add   0xc, r10              r10 = &Y[0]  <- rec+0x0C
    0x29DEA  cmp r9,r7 ; bh              if NOT (idx > X[0])  -> r9 = Y[0]; return          [LOW CLAMP]
    0x29DF6  cmp r6,r7 ; bnc             if idx >= X[4]       -> r9 = Y[4]; return          [HIGH CLAMP]
    0x29E20  sub r13,r9                  r9 = Y[i] - Y[i-1]
    0x29E26  mul r7,r9,r0                r9 = (idx - X[i-1]) * (Y[i] - Y[i-1])
    0x29E2C  divq r6,r9,r0               / (X[i] - X[i-1])    <- THE DIVISOR IS AN **X** SEGMENT WIDTH
    0x29E30  add r13,r9                  + Y[i-1]
    0x29E36  mul r9,r8,r0                ... and straight into the P term

**THE ONE SAFETY QUESTION A Kp = 0 BUILD RAISES IS DIVISION BY ZERO, AND IT IS ANSWERED NO.**
I extracted every division in the whole decompiled `FUN_00028ea6` (17 sites) and every single one has the
divisor `(*puVar42 - puVar42[-1])` -- an **X-axis segment width**.  **No Y value is ever a divisor
anywhere in the function.**  Writing Y = 0 cannot produce a divide-by-zero, and **X is not touched at all
by this build**, so every `divq` divisor is bit-identical to V282's.  [EVIDENCE -- decompiled and
enumerated this session against the V282 image itself.]

**And Y all-zero is degenerate in the SAFE direction on every path through the LERP:** low clamp returns
Y[0] = 0; high clamp returns Y[4] = 0; the interpolated leg returns `Y[i-1] + ((idx-X[i-1])*(Y[i]-Y[i-1]))
/ width` = `0 + (k*0)/width` = 0.  **Kp = 0 at all 256 demand indices, by three independent branches.**
[4] asserts exactly that over the built image, index by index.

**The P term then vanishes cleanly, not by saturation:** `P = (E * Kp) >> 8` = 0 for every E, and the
symmetric clamp against `0xC61BC` = 15360 passes 0 through unchanged.  No sign, no overflow, no
sign-extension edge: 0 is a fixed point of every downstream operation in the chain
(`sum = 0 + 0 + D`; `out = clamp(((taper >> 8) * sum) >> 8, +-0xC61BE)`).

=== SLOT 7 ONLY -- and the fallback fails toward MORE assist, which is the safe direction =========
V281 rev 3 blanket-wrote all 28 records.  This build does NOT -- it follows V284's precedent, which the
four-way adversarial pass approved.
1. **The selector census** (`gp-0x674e`: ONE writer at 0x4272A, the UDS coding path; all reads inside the
   live PID load the same byte into the same register; `iVar23 = gp-0x674e << 2` indexes `0xCB994`
   directly -- re-confirmed by me in the decompile this session).  **The live selector is 7 -- MEASURED
   on the wire, not assumed** (a V38-era "slot 1 / TVAA1" assumption was falsified twice).
2. **The page CRCs.**  The 28 records span FIVE separately-CRC'd 4 KB pages (0xE4000 slots 0-5 - 0xE5000
   slots 6-11 - 0xE6000 12-17 - 0xE7000 18-23 - 0xE8000 24-27).  Slot-7-only touches ONE page CRC;
   a blanket write touches FIVE.  On a build class whose only bricking mode is a bad write, a 5x smaller
   CRC surface is the argument that should lead.  [1c]/[5] assert the other four trailers bit-unchanged.
3. **THE FALLBACK IS SAFE, AND IT IS SAFE IN THE *OPPOSITE* SENSE TO V284'S.**  Y by slot on the base
   image is 205 (0,2,4,5) - 266 (1,6) - 248 (3,7,8,9) - 307 (10-27, dead -- the selector maxes at 9).
   If the coding ever moved off slot 7, the car falls back to a FLAT Kp of 205-307 -- i.e. **to a NORMAL,
   PREVIOUSLY-FLOWN gain, not to zero.**  A mis-selected slot on THIS build fails toward MORE assist,
   never less, and 307 is well under any Kp_crit.

**THE Kd RECORD IS ON THE SAME PAGE AND HAS A DIFFERENT SHAPE.  IT IS NOT TOUCHED.**
`0xE511C` (Kd slot 7, pointer table `KD_PTR = 0xCB7D4`) is a **20-byte, n=4** record -- X = (0, 11, 22, 32),
Y = (128, 128, 128, 128) at 0xE5126/28/2A/2C -- versus the Kp record's 24-byte, n=5 shape.  Both live on
page 0xE5000 and share its CRC.  Kd stays 128: **it is the NEXT build's variable** (the Ku hunt), and
[3]/[8] assert all 28 Kd records byte-identical.

=== LINEAGE: what has been done to the Kp bank, and what Y = 0 has and has not been ==============
  - V280 rev 2 and earlier -- stock LERP on slot 7: X (0,68,112,136,208), Y (248,512,645,696,696).  FLOWN
    (r32/r33/r34).  Ring PRESENT (F7 4.3-8.1 per 100 s); zero stalls.
  - V281 rev 2 -- X (0,24,68,136,208), Y (248,341,341,341,341), all records.  BUILT, SUPERSEDED, NEVER FLOWN.
  - V281 rev 3 -- Y flattened to Y[0] (= 248) on all 28 records, X stock.  FLOWN (r35).  Ring GONE
    (F7 0.0/100 s); SEVEN stalled runs at idx 54-79, 14.8 s, tap 778-868 counts.
  - V282 -- Kp bank UNTOUCHED (cave repoint only).  V283 -- Kp bank UNTOUCHED (Ki 50 only).  FLOWN r36-r38.
  - V284 -- X (0,32,36,44,88), Y (248,248,512,512,248), slot 7 only.  BUILT, SHELVED, DO-NOT-FLASH.
**Kp = 0 HAS NEVER BEEN FLOWN, and no shipped record has ever carried a zero Y.**  Nothing between flat
248 and the stock 512-696 has flown either.  V285 goes the other way off 248, to the floor.
Related but NOT the same lever: **V279 / V279 rev 1 set Kd (`0xE511C`) to 0** -- a different cell, a
different term, confounded with four other edits, and never flown.  `0xE511C` is not virgin; `0xE5378`
at zero is new.

=== ASSERTION CENSUS -- what this script CAN and CANNOT catch ====================================
Printed at the end, per category.  Stated plainly, because V274 passed 720/720 of its own checks while
its central claim was false and ~451 of those assertions were entailed by the base hash:
  **CAN catch:** a wrong record address or a stale pointer walk; a stray byte anywhere in
  [0x13000,0x100000); a wrong or missing page CRC (all 50 blocks are recomputed and compared, not just
  the edited one); a corrupted Kd/taper/map/other-slot record; a cave, hook or 427-tap byte moving; an
  encode/decode round-trip defect; a Y that does not read back as 0 through the pointer at every one of
  the 256 demand indices; an X knot that moved (which would change a `divq` divisor).
  **CANNOT catch:** that the LIVE SELECTOR IS ACTUALLY 7 (that is a wire measurement, not a byte fact --
  and it is the single premise on which this whole edit rests); that the plant is TYPE 0 (measured, from
  four stalled-push strata, not asserted here); that Kd 128 is the right companion; that the operator
  will find the car acceptable to drive.  **A build's own assertions cannot falsify it.**

Cal-only: one 24-byte record, ten written bytes of which five change, one page CRC.
"""
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V285_WRITE", "").strip().lower()

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
             "_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
GRANDPARENT_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GRANDPARENT_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
SIBLING_V283 = ("_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
                "_plain_image.bin")
SIBLING_V284 = ("_v284_V284-V282BASE-KI0-KP.M8.SLOT7.512.IDX32.88-CAVE.R24CMP-MAP.LINEAR.TO6X."
                "FEEDBACK46080.TORQUE.TAP_plain_image.bin")
TAG = "V285-V282BASE-KP.ZERO-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"

# ---- [A] the Kp bank ------------------------------------------------------------------------------------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
BASE_KP_X, BASE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5   # V281 rev 3's flat 248, carried through V282
NEW_KP_X, NEW_KP_Y = BASE_KP_X, (0,) * 5                    # X UNTOUCHED; Y to the floor
STOCK_KP_Y = (248, 512, 645, 696, 696)                      # V280 rev 2 / Honda, read from the grandparent
LIVE_KD_REC, LIVE_KD_N, LIVE_KD_X, LIVE_KD_Y = 0xE511C, 4, (0, 11, 22, 32), (128,) * 4
KP_PAGES = (0xE4000, 0xE5000, 0xE6000, 0xE7000, 0xE8000)
EDIT_PAGE = 0xE5000
EDIT_LO, EDIT_HI = 0xE5384, 0xE538E      # the ten Y bytes, [lo, hi)

# ---- [B] the V282 cave / tap -- this build touches NONE of it -------------------------------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
HOOK = 0x55C0E
HOOK_STOCK4 = bytes.fromhex("86ff26ef")
V282_EDIT_SITES = (0xC4B36, 0xC4B42, 0xC4B64, 0xC4B70)
PACK_LO, PACK_HI = 0x55DF0, 0x55E12
MAP_PTR, MAP_N = 0xC9A88, 10
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

# ---- [C] cells that MUST NOT move -----------------------------------------------------------------------
KI_CELL = 0xC63E6           # the integral gain -- MUST STAY 0; the operator rejects the integrator
P_CLAMP, D_CLAMP, OUT_CLAMP, AW_CLAMP = 0xC61BC, 0xC61B6, 0xC61BE, 0xC61BA
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,
    0xC61B6: 10240,  0xC61BA: 10240,
    0xC61BC: 15360,  0xC61BE: 15360,
    0xC63E6: 0,                             # Ki -- ZERO.  V285 is NOT V283.
    0xC63E8: 923,    0xC63EA: 1560,         # feedback EMA (corner 15.7 Hz, DC 30.891)
    0xC63EC: 992,    0xC63EE: 507,          # output lag (corner 5.05 Hz, DC 0.9902)
    0xC62E4: 4,
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
    0xC6446: 5244,                          # the r24 gain arm -- the 20 Hz creep lever, NOT this build's
    0xC62E6: 46080,                         # the feedback clamp (V280 rev 2's edit)
}

# `zn285`'s independently-computed |C(Kp=0)|/|C(Kp=248)| table (ZN-ACCEL-FRAME-V285-2026-09-04.md sec.2),
# recomputed here from IMAGE-read Kp/Kd by an implementation written from the disassembly.
# f Hz -> (|C| Kp248, |C| Kp0, ratio, dphase deg)
PREREG_RATIO = {
    1.0:    (0.9743, 0.1005, 0.103, 83.9),
    7.3:    (1.2286, 0.7338, 0.597, 52.0),
    9.638:  (1.3905, 0.9686, 0.697, 44.1),
    13.5:   (1.7002, 1.3568, 0.798, 34.7),
    20.0:   (2.2848, 2.0093, 0.879, 25.0),
}
TICK_S = 0.001                              # 1 kHz control task -- see the docstring

OK, BAD = "[PASS]", "[FAIL]"
# ASSERTION CENSUS -- the V274 lesson: 720/720 passing assertions coexisted with a false central claim.
#   S = SUBSTANTIVE   -- can fail on a real defect and is entailed by nothing already asserted.
#   V = VACUOUS       -- a read of the BASE image against a constant; entailed by BASE_SHA.
#   T = TAUTOLOGICAL  -- reads back, at the same address, the value this script just wrote.
#   R = REDUNDANT     -- true by construction given an assertion that already passed earlier in this run
#                        (chiefly: everything asserted on `dec` after `dec == code` has been proved).
_census = {"S": 0, "V": 0, "T": 0, "R": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def kp_lerp(X, Y, idx):
    """The Kp lookup, mirroring FUN_00028ea6 0x29DE8-0x29E32 instruction for instruction.
    X/Y are the five u16 words as read from the image (ld.hu -> zero-extended).
    """
    idx &= 0xFFFF                                    # 0x29DE8  zxh r7
    if not (idx > X[0]):                             # 0x29DEA  cmp r9,r7 ; bh   (unsigned)
        return Y[0]                                  # 0x29DEE  ld.hu 0x0,r10,r9      [LOW CLAMP]
    if idx >= X[4]:                                  # 0x29DF6  cmp r6,r7 ; bnc  (unsigned)
        return Y[4]                                  # 0x29E04  ld.hu 0x8,r10,r9      [HIGH CLAMP]
    i = 1                                            # 0x29DFA/0x29E0A  walk while idx >= X[i]
    while idx >= X[i]:
        i += 1
    num = (idx - X[i - 1]) * (Y[i] - Y[i - 1])       # 0x29E24 sub ; 0x29E20 sub ; 0x29E26 mul
    den = X[i] - X[i - 1]                            # 0x29E2A sub        <- THE divq DIVISOR (an X width)
    q = -((-num) // den) if num < 0 else num // den  # 0x29E2C divq -- SIGNED, TRUNCATES TOWARD ZERO
    return (Y[i - 1] + q) & 0xFFFF                   # 0x29E30 add ; 0x29E32 zxh


def curve(X, Y, n=256):
    return [kp_lerp(X, Y, i) for i in range(n)]


def clamp_sym(v, lim):
    """The symmetric clamp the function applies to P (0xC61BC), D (0xC61B6) and the output (0xC61BE)."""
    return lim if v > lim else (-lim if v < -lim else v)


def pid_terms(E, dE, Kp, Kd, pl, dl):
    """P = (E*Kp) >> 8 clamped;  D = (dE*Kd) >> 3 clamped.  Integer >> throughout (V850 sar)."""
    return clamp_sym((E * Kp) >> 8, pl), clamp_sym((dE * Kd) >> 3, dl)


def controller_response(Kp, Kd, f, T=TICK_S):
    """C(f) of the DISCRETE controller: P is phase-flat Kp/256; D is (Kd/8)*(1 - exp(-j*2*pi*f*T)).
    |1-e^-jth| = 2 sin(th/2), angle = 90deg - th/2.  Returns (|C|, angle_deg).
    """
    th = 2.0 * math.pi * f * T
    dre = (Kd / 8.0) * (1.0 - math.cos(th))
    dim = (Kd / 8.0) * math.sin(th)
    re, im = Kp / 256.0 + dre, dim
    return math.hypot(re, im), math.degrees(math.atan2(im, re))


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: walk the pointer, zero the
    five Y halfwords straight in, then re-CRC every block touched via FF.crc_block_map."""
    img = bytearray(base)
    p = u32(img, KP_PTR + 4 * LIVE_SLOT)
    n = u16(img, p)
    assert n == 5
    touched = set()
    for i in range(n):
        off = 2 + 2 * n + 2 * i
        struct.pack_into("<H", img, p + off, 0)
        touched |= {p + off, p + off + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 112)
    print("  V285 -- V282 + Kp = 0 on the live LKAS rate PID record 0xE5378.  SLOT 7 ONLY.  CAL-ONLY.")
    print("=" * 112)

    # =========================================================================================
    print("\n  [1] BASE = V282  (NOT V283, NOT V284 -- Ki must be 0 and the Kp record must be flat 248)")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches", "S")
    check(len(base) == 0x100000, "base is 1,048,576 bytes", "V")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in sorted(FROZEN.items()):
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    check(u16(base, KI_CELL) == 0,
          "base Ki (0xC63E6) == 0 -- the base is V282; the operator REJECTED the integrator on V283", "V")

    print("\n  [1b] THE LIVE RECORD, REACHED BY WALKING THE POINTER TABLE (never by a contiguous stride)")
    p7 = u32(base, KP_PTR + 4 * LIVE_SLOT)
    check(p7 == LIVE_KP_REC, f"u32(0x{KP_PTR:05X} + 4*{LIVE_SLOT}) == 0x{p7:05X} "
                             f"(expected 0x{LIVE_KP_REC:05X})", "V")
    n7, X7, Y7 = rec(base, p7)
    check(n7 == 5 and tuple(X7) == BASE_KP_X and tuple(Y7) == BASE_KP_Y,
          f"base live record: n={n7} X={tuple(X7)} Y={tuple(Y7)} (V281 rev 3's flat 248)", "V")
    check(u16(base, p7 + 0x16) == 0, "base record pad at rec+0x16 == 0", "V")
    ptrs = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    check(len(set(ptrs)) == N_SLOTS,
          f"all {N_SLOTS} Kp record pointers are DISTINCT (no aliasing onto slot 7)", "S")
    check(sorted(ptrs) != [ptrs[0] + 0x18 * i for i in range(N_SLOTS)],
          "the records are NOT contiguous at stride 0x18 -- a contiguous model would be wrong "
          f"(pointers span 0x{min(ptrs):05X}-0x{max(ptrs):05X})", "S")
    pages = sorted({q & ~0xFFF for q in ptrs})
    check(tuple(pages) == KP_PAGES, f"the 28 records live on exactly {len(pages)} pages: "
          f"{', '.join(f'0x{q:05X}' for q in pages)}", "S")
    check(all(not (p7 <= q < p7 + 0x18) for q in ptrs if q != p7),
          "no other record overlaps slot 7's 24 bytes", "S")
    ylo = p7 + 2 + 2 * n7
    check((ylo, ylo + 2 * n7) == (EDIT_LO, EDIT_HI),
          f"the Y array computed from the record layout is [0x{ylo:05X},0x{ylo + 2 * n7:05X}) "
          f"== the declared edit extent [0x{EDIT_LO:05X},0x{EDIT_HI:05X})", "S")

    print("\n  [1b1] THE 84-RECORD CROSS-FAMILY CENSUS -- THREE FAMILIES INTERLEAVE IN THIS ADDRESS RANGE")
    # `delta282` established that the ASSIST MAP is a 28-record family behind 0xC9A88 (stride 0x2C) living
    # at 0xE4000-0xE80B0 -- i.e. INSIDE the same pages as the Kp and Kd records.  A page does NOT hold one
    # family, and the records are NOT contiguous.  An earlier agent's contiguous-record assumption in this
    # exact range produced a false "21 distinct X axes" alarm.  So: walk all three pointer tables, build
    # every record's true extent, and prove (a) no two of the 84 overlap and (b) the ten bytes this build
    # writes fall inside EXACTLY ONE record, and that record is Kp slot 7.
    fam = []
    for s in range(N_SLOTS):
        q = u32(base, MAP_PTR + 4 * s)
        fam.append(("MAP", s, q, q + 0x2C))                      # 0x2C stride (n=10 -> 42 B used, 44 B slot)
    for s in range(N_SLOTS):
        q = ptrs[s]
        fam.append(("KP ", s, q, q + 0x18))                      # n=5  -> 24 B
    for s in range(N_SLOTS):
        q = u32(base, KD_PTR + 4 * s)
        fam.append(("KD ", s, q, q + 0x14))                      # n=4  -> 20 B
    check(len(fam) == 84, f"census walked {len(fam)} records (28 MAP via 0x{MAP_PTR:05X} + 28 KP via "
                          f"0x{KP_PTR:05X} + 28 KD via 0x{KD_PTR:05X})", "S")
    ordered = sorted(fam, key=lambda r: r[2])
    laps = [(a, b) for a, b in zip(ordered, ordered[1:]) if a[3] > b[2]]
    check(not laps, f"ZERO overlaps among all 84 records across the three interleaved families "
                    f"({len(laps)} found); span 0x{ordered[0][2]:05X}-0x{ordered[-1][3]:05X}", "S")
    hits = [r for r in fam if r[2] < EDIT_HI and EDIT_LO < r[3]]
    check(len(hits) == 1 and hits[0][0] == "KP " and hits[0][1] == LIVE_SLOT,
          f"the ten bytes 0x{EDIT_LO:05X}-0x{EDIT_HI - 1:05X} fall inside EXACTLY ONE of the 84 records, "
          f"and it is {hits[0][0].strip()} slot {hits[0][1]} @0x{hits[0][2]:05X}-0x{hits[0][3] - 1:05X}", "S")
    print(f"      MAP family spans 0x{min(r[2] for r in fam if r[0] == 'MAP'):05X}-"
          f"0x{max(r[3] for r in fam if r[0] == 'MAP') - 1:05X}   "
          f"KP 0x{min(r[2] for r in fam if r[0] == 'KP '):05X}-"
          f"0x{max(r[3] for r in fam if r[0] == 'KP ') - 1:05X}   "
          f"KD 0x{min(r[2] for r in fam if r[0] == 'KD '):05X}-"
          f"0x{max(r[3] for r in fam if r[0] == 'KD ') - 1:05X}")
    print(f"      the edit lands in {hits[0][0].strip()} slot {hits[0][1]} only; "
          f"Kp slot 7 = 0x{LIVE_KP_REC:05X}-0x{LIVE_KP_REC + 0x18 - 1:05X}, "
          f"Kd slot 7 = 0x{LIVE_KD_REC:05X}-0x{LIVE_KD_REC + 0x14 - 1:05X}")

    print("\n  [1b2] THE FALLBACK IF THE SELECTOR IS EVER RE-CODED -- read from the base, not assumed")
    fb = {}
    for s in range(N_SLOTS):
        _, _, ys = rec(base, ptrs[s])
        fb.setdefault(tuple(ys), []).append(s)
    for ys, sl in sorted(fb.items(), key=lambda kv: kv[1][0]):
        print(f"      slots {str(sl):28s}  Y = {ys}")
    other_max = max(max(rec(base, ptrs[s])[2]) for s in range(N_SLOTS) if s != LIVE_SLOT)
    check(other_max <= 307,
          f"every OTHER slot's max Y is {other_max} (<= 307) -- a mis-selected slot on this build falls "
          f"back to a NORMAL, previously-flown flat Kp, i.e. it fails toward MORE assist, never less", "S")

    print("\n  [1c] ALL FIVE Kp PAGES' CRC TRAILERS -- recorded now, asserted UNCHANGED in [5] except one")
    crc_before = {q: u32(base, q + 0xFFC) for q in KP_PAGES}
    for q in KP_PAGES:
        print(f"      page 0x{q:05X}  trailer 0x{q + 0xFFC:05X} = 0x{crc_before[q]:08X}"
              f"{'   <- the ONLY page this build touches' if q == EDIT_PAGE else ''}")

    print("\n  [1d] THE Kd RECORD ON THE SAME PAGE -- a DIFFERENT SHAPE, and NOT this build's variable")
    kd7 = u32(base, KD_PTR + 4 * LIVE_SLOT)
    nk, Xk, Yk = rec(base, kd7)
    check(kd7 == LIVE_KD_REC and nk == LIVE_KD_N and tuple(Xk) == LIVE_KD_X and tuple(Yk) == LIVE_KD_Y,
          f"Kd slot 7 @0x{kd7:05X}: n={nk} X={tuple(Xk)} Y={tuple(Yk)} -- 20 bytes, n=4, NOT the Kp "
          f"record's 24-byte n=5 shape; same page 0x{EDIT_PAGE:05X}, same CRC", "V")
    check((kd7 & ~0xFFF) == EDIT_PAGE, "the Kd record shares the edited page -- know it is there", "V")
    check(not (LIVE_KP_REC <= kd7 < LIVE_KP_REC + 0x18)
          and not (kd7 <= LIVE_KP_REC < kd7 + 2 + 4 * nk),
          "the Kp and Kd records do NOT overlap -- zeroing Kp cannot corrupt Kd", "S")

    print("\n  [1e] LINEAGE -- the flown Kp shapes, read from the IMAGES")
    gp_img = Path(plain_image_path(GRANDPARENT_NAME)).read_bytes()
    check(hashlib.sha256(gp_img).hexdigest() == GRANDPARENT_SHA, "V280 rev 2 image sha256 matches", "S")
    _, Xg, Yg = rec(gp_img, u32(gp_img, KP_PTR + 4 * LIVE_SLOT))
    check(tuple(Yg) == STOCK_KP_Y and tuple(Xg) == BASE_KP_X,
          f"the stock/flown LERP on the V280 rev 2 IMAGE is X={tuple(Xg)} Y={tuple(Yg)} -- read, "
          f"not remembered", "S")
    check(min(Yg) > 0 and min(Y7) > 0,
          "NO shipped or flown record has ever carried a zero Y -- Kp = 0 has never flown", "S")

    # =========================================================================================
    print("\n  [2] THE EDIT -- slot 7's five Y halfwords to ZERO, and NOTHING else")
    check(NEW_KP_X == BASE_KP_X, f"constants gate: X {NEW_KP_X} is UNTOUCHED -- every divq divisor at "
                                 f"0x29E2C is bit-identical to V282's", "S")
    check(set(NEW_KP_Y) == {0}, f"constants gate: Y {NEW_KP_Y} is all-zero", "S")
    check(tuple(sorted(NEW_KP_X)) == NEW_KP_X and len(set(NEW_KP_X)) == 5,
          f"constants gate: X {NEW_KP_X} is STRICTLY INCREASING (non-zero divq divisor at every knot)", "S")

    code = bytearray(base)
    attributed = set()
    for i in range(n7):
        off = 2 + 2 * n7 + 2 * i
        struct.pack_into("<H", code, p7 + off, NEW_KP_Y[i])
        attributed |= {p7 + off, p7 + off + 1}
    check(sorted(attributed) == list(range(EDIT_LO, EDIT_HI)),
          f"exactly the ten bytes 0x{EDIT_LO:05X}-0x{EDIT_HI - 1:05X} were written "
          f"({len(attributed)} addresses)", "S")
    nb, Xb, Yb = rec(code, p7)
    check(nb == 5 and tuple(Xb) == NEW_KP_X and tuple(Yb) == NEW_KP_Y,
          f"record written: n={nb} X={tuple(Xb)} Y={tuple(Yb)}", "T")
    check(u16(code, p7) == u16(base, p7) == 5, "the COUNT word at rec+0x00 is UNTOUCHED (5)", "S")
    check(bytes(code[p7 + 2:p7 + 0x0C]) == bytes(base[p7 + 2:p7 + 0x0C]),
          "the whole X array rec+0x02..rec+0x0B is byte-untouched", "S")
    check(u16(code, p7 + 0x16) == u16(base, p7 + 0x16) == 0, "the PAD at rec+0x16 is UNTOUCHED (0)", "S")

    # =========================================================================================
    print("\n  [3] EVERYTHING ELSE BYTE-IDENTICAL TO V282, BEFORE THE CRC RECOMPUTE")
    outside = [a for a in range(START, END) if a not in attributed and code[a] != base[a]]
    check(outside == [], f"no byte outside slot 7's Y array changed ({len(outside)} stray diffs)", "S")
    for a, v in sorted(FROZEN.items()):
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}",
              "R")   # entailed by the base read in [1] + `outside == []` immediately above
    check(u16(code, KI_CELL) == 0,
          "Ki (0xC63E6) is STILL 0 on the built image -- V285 does NOT re-introduce V283's integrator", "S")
    check(u16(code, 0xC6446) == 5244,
          "the r24 gain arm 0xC6446 == 5244 -- the 20 Hz creep-grind lever is BYTE-UNTOUCHED, so a "
          "quiet 20 Hz line on this build is NOT a grind result", "S")
    base_cave = hashlib.sha256(bytes(base[CAVE_START:CAVE_END])).hexdigest()
    check(hashlib.sha256(bytes(code[CAVE_START:CAVE_END])).hexdigest() == base_cave,
          f"the V282 cave (0x{CAVE_START:05X}-0x{CAVE_END - 1:05X}, {CAVE_END - CAVE_START} B) is "
          f"byte-identical, sha256[:8] {base_cave[:8]} -- the r24 comparator bits survive", "S")
    for a in V282_EDIT_SITES:
        check(s16(code, a) == s16(base, a) and s16(code, a) in (-0x6ADA, -0x6B38, -0x6B94),
              f"cave site 0x{a:05X} still carries its V282 displacement ({s16(code, a)})", "S")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4,
          "hook 0x55C0E == jarl 0xc4b34,lp, byte-identical", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          f"427 delivered-torque tap window 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} byte-identical "
          f"-- instrument 2 is intact", "S")
    for q in sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)}):
        check(bytes(code[q:q + 2 + 4 * MAP_N]) == bytes(base[q:q + 2 + 4 * MAP_N]),
              f"assist map 0x{q:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        q = ptrs[s]
        if s == LIVE_SLOT:
            continue
        check(bytes(code[q:q + 0x18]) == bytes(base[q:q + 0x18]),
              f"Kp slot {s:2d} @0x{q:05X} byte-identical -- flat Y {rec(base, q)[2][0]} preserved", "S")
    for s in range(N_SLOTS):
        q = u32(base, KD_PTR + 4 * s)
        n = u16(base, q)
        check(bytes(code[q:q + 2 + 4 * n]) == bytes(base[q:q + 2 + 4 * n]),
              f"Kd slot {s} @0x{q:05X} byte-identical (Kd is the NEXT build's variable)", "S")
    tps = {u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)}
    for q in sorted(tps):
        n = s16(base, q)
        check(bytes(code[q:q + 2 + 4 * n]) == bytes(base[q:q + 2 + 4 * n]),
              f"taper 0x{q:05X} byte-identical", "S")

    # =========================================================================================
    print("\n  [4] THE DELIVERED SURFACE -- emulated from the DISASSEMBLY, over the BUILT IMAGE")
    _, Xr, Yr = rec(code, u32(code, KP_PTR + 4 * LIVE_SLOT))   # re-read through the pointer, not constants
    cb, cc = curve(BASE_KP_X, BASE_KP_Y), curve(Xr, Yr)
    check(all(v == 0 for v in cc),
          "Kp == 0 at ALL 256 demand indices, read back through the pointer -- low clamp (idx<=X[0]), "
          "high clamp (idx>=X[4]) and the interpolated legs all return 0", "S")
    check(all(cb[i] == 248 for i in range(256)), "V282's surface was flat 248 at all 256 indices", "V")
    check(all(cc[i] <= cb[i] for i in range(256)),
          "the gain never RISES at any index -- authority strictly falls, the SAFE direction", "S")
    print("        idx    V282 Kp   V285 Kp")
    for i in (0, 1, 32, 67, 68, 69, 111, 112, 135, 136, 207, 208, 209, 240, 255):
        print(f"        {i:3d}      {cb[i]:5d}     {cc[i]:5d}")
    check(all(Xr[i] < Xr[i + 1] for i in range(4)),
          f"IMAGE X {tuple(Xr)} strictly increasing -- divq at 0x29E2C has a non-zero divisor", "S")
    check(tuple(Xr) == tuple(X7), "IMAGE X is bit-equal to the BASE X -- no knot moved", "S")

    print("\n      [4b] THE P TERM IS IDENTICALLY ZERO, AND THE SUM IS IDENTICALLY D")
    pl, dl, ol = u16(code, P_CLAMP), u16(code, D_CLAMP), u16(code, OUT_CLAMP)
    check((pl, dl, ol) == (15360, 10240, 15360),
          f"clamps read from the built image: P +-{pl} (0x{P_CLAMP:05X}), D +-{dl} (0x{D_CLAMP:05X}), "
          f"output +-{ol} (0x{OUT_CLAMP:05X})", "R")
    kd = rec(code, u32(code, KD_PTR + 4 * LIVE_SLOT))[2][0]
    check(kd == 128, f"Kd read through its own pointer == {kd}", "R")
    worst, nsamp = 0, 0
    for E in range(-40000, 40001, 617):
        for dE in (-4000, -512, -17, 0, 17, 512, 4000):
            p_new, d_new = pid_terms(E, dE, cc[0], kd, pl, dl)
            p_old, d_old = pid_terms(E, dE, cb[0], kd, pl, dl)
            assert p_new == 0 and d_new == d_old
            worst = max(worst, abs(p_old))
            nsamp += 1
    check(worst > 0, f"over {nsamp} (E, dE) samples spanning +-40000 counts: P is 0 on V285 for EVERY "
                     f"sample (V282's |P| reached {worst}), and D is bit-identical to V282's", "S")
    check(all(pid_terms(E, dE, cc[0], kd, pl, dl)[0] == 0 for E in (-32767, -1, 0, 1, 32767)
              for dE in (-32767, 0, 32767)),
          "P == 0 at the sign and range extremes too -- no overflow or sign-extension edge", "S")
    print("        sum = (I>>7) + P + D  ->  0 + 0 + D.  The controller has ONE live term.")
    print(f"        |D| <= {dl}, so |sum| <= {dl} (V282: |P|+|D| <= {pl}+{dl} = {pl + dl}, "
          f"clipped by the output clamp {ol})")
    check(dl < ol, f"the D clamp {dl} is BELOW the output clamp {ol} -- on V285 the OUTPUT clamp can "
                   f"never bind, so the delivered surface is exactly the (tapered) D term", "S")
    print("      [4c] AND THEREFORE THE `|D| >= |P|` COMPARATOR IS STRUCTURALLY VACUOUS ON THIS BUILD")
    check(all(pid_terms(E, dE, cc[0], kd, pl, dl)[0] == 0
              for E in (-30000, -100, 0, 100, 30000) for dE in (-3000, 0, 3000)),
          "`|D| >= |P|` would pin to 1 by construction (P == 0 identically) -- it is a tautology here "
          "and correctly NOT built; telem285's verdict re-verified numerically over the built image", "S")

    print("\n      [4d] |C(Kp=0)| / |C(Kp=248)| -- recomputed from IMAGE-read Kp/Kd, T = 1.000 ms")
    print("        f (Hz)   |C| V282   |C| V285   ratio    loss       d(phase)")
    for f in sorted(PREREG_RATIO):
        m_old, a_old = controller_response(cb[0], kd, f)
        m_new, a_new = controller_response(cc[0], kd, f)
        r = m_new / m_old
        print(f"        {f:6.3f}   {m_old:8.4f}   {m_new:8.4f}   {r:5.3f}   {100 * (r - 1):+7.1f} %  "
              f"{a_new - a_old:+6.1f} deg")
        e_old, e_new, e_r, e_dp = PREREG_RATIO[f]
        check(abs(m_old - e_old) < 5e-4 and abs(m_new - e_new) < 5e-4 and abs(r - e_r) < 1e-3
              and abs((a_new - a_old) - e_dp) < 0.1,
              f"@{f} Hz reproduces zn285's INDEPENDENTLY-computed row "
              f"(|C| {e_old}/{e_new}, ratio {e_r}, dphase {e_dp:+.1f} deg) -- "
              f"ZN-ACCEL-FRAME-V285-2026-09-04.md sec.2", "S")
    _, a1 = controller_response(cb[0], kd, 20.0)
    _, a2 = controller_response(cc[0], kd, 20.0)
    check(a2 > a1, f"removing P ADDS lead at 20 Hz ({a1:+.1f} -> {a2:+.1f} deg): P is phase-flat and D "
                   f"leads, so the 'removing P removes 90 deg of lag' premise is BACKWARDS", "S")
    check(controller_response(cc[0], kd, 1e-6)[0] < 1e-6,
          "|C(Kp=0)| -> 0 as f -> 0: with a TYPE-0 plant (measured, g = 0.007-0.052 deg/s per T count) "
          "L(0) = 0 EXACTLY. ZERO steady-state authority. NOT A DRIVABLE LANE-KEEPING TUNE.", "S")

    # =========================================================================================
    print("\n  [5] CRC -- the edited block located GENERICALLY, then ALL 50 BLOCKS RECOMPUTED")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns the whole edit ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b0 == EDIT_PAGE and b1 == EDIT_PAGE + 0xFFC,
          f"block is [0x{b0:05X},0x{b1:05X}) -- the slot 6-11 page, ONE of the five record pages", "S")
    check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:05X}", "S")
    oldc = u32(code, b1)
    newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:05X},0x{b1:05X}) CRC actually moved", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      Kp page [0x{b0:05X},0x{b1:05X})  trailer 0x{b1:05X}  0x{oldc:08X} -> 0x{newc:08X}")
    for q in KP_PAGES:
        if q == EDIT_PAGE:
            continue
        check(u32(code, q + 0xFFC) == crc_before[q],
              f"page 0x{q:05X} CRC trailer UNCHANGED (0x{crc_before[q]:08X}) -- slot-7-only kept the CRC "
              f"surface to one page of five", "S")
    bmap = list(FF.crc_block_map(bytes(code)))
    bad = [(s_, e_) for s_, e_ in bmap
           if (zlib.crc32(bytes(code[s_:e_])) & 0xFFFFFFFF) != u32(code, e_)]
    check(len(bmap) == 50 and not bad,
          f"EVERY page CRC in the image recomputed and compared: {len(bmap)}/50 blocks correct, "
          f"{len(bad)} stale", "S")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50 (independent walker)", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # =========================================================================================
    print("\n  [6] FULL-FILE BYTE DIFF vs V282")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed,
          f"every one of the {len(diff)} differing bytes is a written Y byte or the page CRC trailer", "S")
    expect_payload = sum(1 for i in range(5)
                         for j in (0, 1)
                         if struct.pack("<H", BASE_KP_Y[i])[j] != struct.pack("<H", NEW_KP_Y[i])[j])
    check(expect_payload == 5,
          f"of the 10 written Y bytes, exactly {expect_payload} actually CHANGE value -- the five LOW "
          f"bytes (0xF8 -> 0x00); the five HIGH bytes were already 0x00 (248 = 0x00F8)", "S")
    check(len(diff) == expect_payload + 4,
          f"total diff vs V282 == {expect_payload} payload + 4 CRC = {expect_payload + 4}, "
          f"got {len(diff)}", "S")
    check(all(EDIT_LO <= a < EDIT_HI or b1 <= a < b1 + 4 for a in diff),
          f"every differing byte is inside the Y array [0x{EDIT_LO:05X},0x{EDIT_HI:05X}) or the one "
          f"4-byte trailer", "S")
    rr = runs(diff)
    for s, e in rr:
        kind = (f"page CRC trailer 0x{b1:05X}" if s == b1
                else f"0xE5378 rec +0x{s - LIVE_KP_REC:02X}  Y[{(s - EDIT_LO) // 2}] low byte")
        print(f"      0x{s:05X}-0x{e - 1:05X} ({e - s:2d} B)  {kind:44s}  "
              f"{bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    check(len(rr) == 6 and [e - s for s, e in rr] == [1, 1, 1, 1, 1, 4],
          f"exactly 6 runs: five single low bytes at stride 2, plus the 4-byte CRC ({rr})", "S")
    print(f"      runs: {len(rr)}   bytes: {len(diff)}   (payload {expect_payload} + CRC 4)")

    print("\n  [6b] CROSS-IMAGE -- V285 must be V282 + this edit, and must resemble NEITHER sibling")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    d_v282_par = {a for a in range(START, END) if base[a] != parent[a]}
    d_par_gp = {a for a in range(START, END) if parent[a] != gp_img[a]}
    d_v285_gp = {a for a in range(START, END) if code[a] != gp_img[a]}
    sites = d_v282_par | d_par_gp | set(diff)
    check(d_v285_gp <= sites,
          f"V285 vs V280 rev 2 ({len(d_v285_gp)} B) introduces NO byte outside the three known deltas: "
          f"V282's cave ({len(d_v282_par)} B) + V281 rev 3's Kp-Y ({len(d_par_gp)} B) + this build "
          f"({len(diff)} B), {len(sites)} distinct addresses", "S")
    for nm, fn, want in (("V283 (Ki 50, FLOWN and REJECTED)", SIBLING_V283, 50),
                         ("V284 (shaped Kp, SHELVED DO-NOT-FLASH)", SIBLING_V284, 0)):
        sp = Path(plain_image_path(fn))
        if not sp.exists():
            print(f"      ({nm} image not on disk at {sp} -- cross-check skipped)")
            continue
        sib = sp.read_bytes()
        check(u16(sib, KI_CELL) == want, f"the {nm} image on disk carries Ki = {want}", "S")
        _, Xs, Ys = rec(sib, u32(sib, KP_PTR + 4 * LIVE_SLOT))
        check(min(Ys) > 0,
              f"{nm} carries a NON-ZERO Kp record (X={tuple(Xs)} Y={tuple(Ys)}) -- V285 is a different "
              f"arm from both: it deletes the P term rather than re-valuing or re-shaping it", "S")
        d_s = {a for a in range(START, END) if code[a] != sib[a]}
        d_sb = {a for a in range(START, END) if sib[a] != base[a]}
        check(d_s <= set(diff) | d_sb,
              f"V285 vs {nm.split()[0]} ({len(d_s)} B) is contained in this build's {len(diff)} bytes "
              f"UNION that sibling's own {len(d_sb)}-byte delta from the shared V282 base", "S")
    check(u16(code, KI_CELL) == 0 and set(rec(code, p7)[2]) == {0},
          "V285 is the ONLY image in the family with BOTH Ki == 0 AND Kp == 0 -- one live term", "S")

    # =========================================================================================
    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V285 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN exists -- the non-circular cipher test is reachable", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    # =========================================================================================
    print("\n  [8] END STATE -- re-read from the FINAL image AND from the DECODED .rwd")
    # `dec` was already proved byte-identical to `code` in [7]; every check on it is therefore REDUNDANT.
    # It is kept because it is the only path that would survive a change to the encode/decode table.
    for nm, im in (("code", code), ("dec ", dec)):
        kind = "T" if nm == "code" else "R"
        pp = u32(im, KP_PTR + 4 * LIVE_SLOT)
        nn, XX, YY = rec(im, pp)
        check(pp == LIVE_KP_REC and nn == 5 and tuple(XX) == NEW_KP_X and tuple(YY) == NEW_KP_Y,
              f"{nm}: slot 7 @0x{pp:05X} n={nn} X={tuple(XX)} Y={tuple(YY)}", kind)
        check(all(XX[i] < XX[i + 1] for i in range(4)), f"{nm}: X strictly increasing (divq gate)",
              "S" if nm == "code" else "R")
        check(all(v == 0 for v in curve(XX, YY)), f"{nm}: Kp == 0 at all 256 demand indices", "R")
        check(u16(im, KI_CELL) == 0, f"{nm}: Ki (0xC63E6) == 0", "R")
        for a, v in sorted(FROZEN.items()):
            check(u16(im, a) == v, f"{nm}: 0x{a:05X} == {v}", "R")
        check(hashlib.sha256(bytes(im[CAVE_START:CAVE_END])).hexdigest() == base_cave,
              f"{nm}: V282 cave hash-identical ({base_cave[:8]})", "R")
        check(bytes(im[HOOK:HOOK + 4]) == HOOK_STOCK4, f"{nm}: hook untouched", "R")
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
              f"{nm}: 427 tap window untouched", "R")
        check(rec(im, u32(im, KD_PTR + 4 * LIVE_SLOT)) == (LIVE_KD_N, list(LIVE_KD_X), list(LIVE_KD_Y)),
              f"{nm}: Kd slot 7 still n=4 X={LIVE_KD_X} Y={LIVE_KD_Y}", "R")
        for s in range(N_SLOTS):
            if s == LIVE_SLOT:
                continue
            check(bytes(im[ptrs[s]:ptrs[s] + 0x18]) == bytes(base[ptrs[s]:ptrs[s] + 0x18]),
                  f"{nm}: Kp slot {s:2d} untouched", "R")
        for q in KP_PAGES:
            if q == EDIT_PAGE:
                continue
            check(u32(im, q + 0xFFC) == crc_before[q], f"{nm}: page 0x{q:05X} CRC unchanged", "R")

    # =========================================================================================
    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (direct pointer-walk + generic re-CRC, no shared state) == built image "
          "sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =========================================================================================
    _scr = os.environ.get("ACCORD_V285_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v285_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v285_{TAG}.rwd").write_bytes(rwd)
        print(f"\n      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v285_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha,
              f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha,
              f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V285*.rwd")
                  if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V285 rwd on disk (others: {others})", "S")
        disk = out_img.read_bytes()
        _, dX, dY = rec(disk, u32(disk, KP_PTR + 4 * LIVE_SLOT))
        check(all(v == 0 for v in curve(dX, dY)),
              "the ON-DISK image, re-read from the filesystem, delivers Kp == 0 at all 256 indices", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V285_WRITE=rwd to emit the files")

    print("\n" + "=" * 112)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- CENSUS: {_census['S']} SUBSTANTIVE  |  "
          f"{_census['V']} vacuous (entailed by the base sha256)  |  {_census['T']} tautological "
          f"(readback of a write)  |  {_census['R']} redundant (entailed by an assertion that already "
          f"passed above -- chiefly the `dec` arm, which `dec == code` in [7] already settles)")
    print("  ** V285 -- the live Kp record 0xE5378 Y (248,248,248,248,248) -> (0,0,0,0,0).  X UNTOUCHED. **")
    print("  ** SLOT 7 ONLY -- one page CRC of five.  Ki stays 0.  Kd stays 128.  Cave/tap byte-identical.**")
    print("  ** The LKAS rate PID now has ONE live term: sum = 0 + 0 + D.                                 **")
    print("  ** !! ZERO steady-state lane keeping -- L(0) = 0 EXACTLY. Not 'weak', not 'reduced': ZERO.  **")
    print("  ** !! BENCH / IDENTIFICATION CONFIG, NOT A DRIVE CANDIDATE.                                 **")
    print("  **    THE ORCHESTRATOR'S RECOMMENDATION IS **DO NOT FLY THIS**.                             **")
    print("  **    The honest other half: ring 0.861 (vs ~0.98), GM 2.11x (vs 1.77x), +52 deg lead @7.3Hz.**")
    print("  ** !! DRIVE SPEC: seek BUMPS, QUICK CORRECTIONS and STALL RELEASES while LATERALLY engaged.  **")
    print("  **    Smooth cruising returns an UNINTERPRETABLE NULL -- the mode is never excited.          **")
    print("  ** !! Do NOT read a quiet 20 Hz line as a grind fix (predicted loss there is only 12 %).     **")
    print("  ** !! The P-only deadband/stutter is expected to RETURN and worsen (Ki 50 was its cure).     **")
    print("  ** Instruments, all already flying, byte-identical: gp-0x6a56 on 0x18F[2:3] (motion, 100 Hz),**")
    print("  ** T = gp-0x6b38 on 427 (50 Hz), and V282's r24 comparator bits on 0x14A byte 4 bits 6/5/4.  **")
    print("=" * 112)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
