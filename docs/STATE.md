# STATE — living current state of the kit

## ✅ THE "r24 IS THE CORPUS MAXIMUM" ALARM IS AN **ARTEFACT OF THE RATIO** — withdrawn
I flagged V122's angle-gated 6-9 Hz ratio (**12.05**) as the corpus maximum. **The absolute levels
say otherwise:**
```
   a2   n     hi-ang p90    hi-ang p50    lo-ang p90     ratio
   22  13       6.510         2.221         ~1.7          2.86
   14   3       3.137         1.151          1.060        3.12     (r22 2.909, r23 8.320)
    8   1       9.871         2.991          0.819       12.05     (r24 = V122)
```
✅ **r24's high-angle p90 of 9.871 sits just above r23's 8.320 — INSIDE the same-firmware spread**
(the two V112 drives differ 2.909 vs 8.320, a factor of 2.9), not outside it.
✅ **The ratio blew up because the LOW-ANGLE DENOMINATOR fell to 0.819, the lowest in the corpus.**
⇒ **`alpha2 = 8` improved LOW-angle behaviour and left HIGH-angle roughly unchanged** — which is
exactly what the operator reported: *grinding better, oscillation still there.* **No evidence it hurt
anything; the implication that it did is withdrawn.**
🛑 **METHOD NOTE, worth keeping:** the angle-gated **ratio** was chosen because it cancels
route-level exposure, and that is still right for cross-build comparison — **but a ratio moves when
either end moves.** A build that improves the denominator looks worse on the ratio while being
better on the car. ✅ **Always report the absolute numerator and denominator beside the ratio.**
⊕ It also explains why the ratio-based alpha2 result earlier looked so strong: part of that signal
was the denominator, not the symptom.

## 🛑🛑 **V122 FLEW (route 24)** — grinding better, authority NOT, and the CAUSE OF THE AUTHORITY CEILING IS FOUND
Operator: *"Grinding: better, still ever so slight grinding in even more rare moments. On the improved
LKAS authority, it does not feel like it has improved at all. I can feel that the manual driving
authority has been loosened, less mass and friction. That is fine but it is only worth it if it means
LKAS authority is improved, which it has not."* Route 24: **832 s, 70.6 % engaged, 14 segments,
fault-free.**

### 🛑🛑 THE HEADLINE: **THE LKAS COMMAND RAILS IN HARD TURNS**
```
   |ang|  30- 60 deg   command RAILED at 99 % of max  51.2 % of the time,  MEDIAN = 1.000
   |ang|  60-120 deg   railed 42.7 %,  median 0.863
   |ang| 120-400 deg   railed 28.0 %,  median 0.737
   |ang|   0- 10 deg   railed  0.0 %,  median 0.032
```
⇒ **In hard turns openpilot is already commanding 100 % and cannot ask for more.** ✅ **This is the
answer to the operator's standing complaint** (*"max steering wheel acceleration and velocity still
seem low for what I would expect for 6×"*): **the ceiling is the COMMAND, not the firmware.**
⇒ **No firmware edit acting DOWNSTREAM of the command can add authority there** — which is exactly
why V122's friction change showed up in MANUAL (where the driver supplies the torque) and not in LKAS.

### ✅ THE DATA CONFIRMS HIS REPORT PRECISELY
```
                    ENGAGED p99 rate   MANUAL p99 rate   ENGAGED p99 accel
   V112 (r23)            60.5              82.2              1831
   V122 (r24)           106.9             174.5              1564
                        +76.6 %          +112.2 %           -14.6 %
   engaged/manual ratio  0.74  ->  0.61
```
✅ **Manual gained 112 % against engaged's 77 %, and engaged ACCELERATION fell 14.6 %.** He said manual
loosened and LKAS did not improve; **the measurement says exactly that.**

### 🛑 THE PRE-REGISTERED GRIND ENDPOINT SAYS "NOT RESOLVED" — AND THE OPERATOR SAYS "BETTER"
```
   21-26 Hz engaged share p90:   r22 V112 0.22264 | r23 V112 0.20845 | r24 V122 0.21898
   bands: <=0.180 CONFIRMED | 0.180-0.230 NOT RESOLVED | >0.230 refuted
```
🛑 **V122 lands at 0.21898, inside the V112 two-drive spread ⇒ NOT RESOLVED**, while the operator
reports a real improvement. ⇒ **the endpoint is not measuring what he hears**, confirming
[[accord-the-21to26hz-excess-is-not-the-audible-grind]]. **Trust the operator's report over this
instrument**, and stop treating 21-26 Hz as the grind-#1 endpoint.

### ✅ HIS OSCILLATION EVENT (seg 11) IS **NOT** A SATURATION ARTEFACT
Worst 6-9 Hz window in segment 11: **t = 673.4 s, rms 13.16 deg/s, peak 7.81 Hz, 44 km/h**, 99.6th
percentile route-wide. **Command during the event: p50 0.277, max 0.372 — nowhere near the rail.**
⇒ **the oscillation happens well BELOW saturation**, so it is a different problem from the authority
ceiling. ⊕ **7.81 Hz — identical to the V112 event.** The mode is unchanged.

### ⭐ A SURPRISE WORTH TESTING: the angle-gated oscillation may FALL with gain
```
   gain 3564 (4x)  n=6    median angle-gated 6-9 Hz ratio  3.56
   gain 5346 (6x)  n=10                                    2.15
   gain 7128 (8x)  n=1                                     1.23
```
⇒ **monotone DOWN with gain — opposite to the ~23 Hz vibration** (which rises as `m^1.74`).
🛑 **NOT established**: n = 1 at 8×, and the 6× group spans **0.66 to 12.05, a factor of 18**.
⚠ **And r24 (V122) itself is 12.05, the HIGHEST ratio in the corpus** — which cuts against the trend.
✅ But if it holds, **8× would improve BOTH complaints** (authority ×1.29 at the rail, oscillation
down) at the cost of ×1.65 on the 23 Hz vibration. **That is the trade to put to the operator.**

## 🛑 RETRACTED IMMEDIATELY: the "1.5 kHz signature" of the labelled event was MULTIPLE-COMPARISONS NOISE
The operator's labelled event (r23, t = 445.6-448.2) appeared to show a tone cluster at
**1457-1561 Hz, +11 to +14 dB over the p95 of 19 matched engaged controls**, and I called it *"the
signature to hunt"*. **The follow-up refutes it.**
```
   1539 engaged audio windows, r23
   Spearman(6-9 Hz steering share, 1.4-1.6 kHz audio share) = -0.167   p = 4.2e-11
   top-20 % oscillation vs bottom-40 %:            ratio 0.79x  CI [0.75, 0.85]
   SPEED-MATCHED 38-68 km/h (n = 184/166):         ratio 0.70x  CI [0.65, 0.77]
```
🛑 **High-oscillation windows carry LESS 1.4-1.6 kHz tone, not more** — the opposite sign, and
significant.
✅ **The error was structural and I should have caught it before claiming**: **one** labelled window
against **19** controls, scanned across **~4000 frequency bins**. The p95 of 19 samples is
essentially their maximum, so **a large number of bins clear it by chance**. A family-wise
correction was required and was not applied. ⇒ **any single-window acoustic "signature" found this
way is noise unless it replicates across windows.**
⚠ The negative correlation is probably **normalisation**, not physics: the tone share is divided by
300-3000 Hz power, and if the oscillation adds broadband energy there the share falls. **Do not read
it as "the oscillation suppresses a 1.5 kHz tone".**
⇒ **STATUS: the acoustic instrument has NOT been shown to see the peak-turn oscillation.** Combined
with the earlier engaged-only case-control finding nothing for the 21-26 Hz grind band, **no acoustic
result in this corpus is currently load-bearing.**
✅ **What would make it load-bearing:** the operator naming the **pitch** (high whine / mid buzz / low
growl), which converts an unbounded 4000-bin search into a **pre-registered band** where a null or a
hit both mean something.

## 🛑🛑 THE 21-26 Hz EXCESS AND THE **AUDIBLE** GRIND ARE NOT SHOWN TO BE THE SAME THING
Two acoustic contrasts on r22 (V112), 710 s of 16 kHz PCM:
```
   1) ENGAGED vs MANUAL  -- USELESS, hopelessly speed-confounded
      engaged median 52.8 km/h vs manual 11.5 km/h, and the excess is a UNIFORM
      +9.5 to +12.6 dB across EVERY band 20-2000 Hz = road/wind noise, not LKAS.
      The speed-matched control could not even run: the arms barely overlap in speed.

   2) ENGAGED-ONLY case-control, speed-matched 30-61 km/h, 224 high-grind vs 189 low-grind
      windows, split on the 21-26 Hz STEERING-RATE content:
        20-50 Hz  +0.78 | 50-60 -0.92 | 60-80 +0.21 | 80-120 +0.57 | 120-200 +0.50
        200-300 -0.03 | 300-800 -0.08 | 800-2000 -0.54 | 2000-5000 +0.03 dB
        strongest lines only +2-3 dB (45, 51, 86, 152, 176 Hz)
```
🛑 **Windows with high 21-26 Hz steering-rate content have NO distinct acoustic signature** —
everything within ±1 dB, with the speed confound properly controlled this time.
⇒ **THE KIT HAS BEEN CALLING TWO DIFFERENT THINGS "GRIND #1":** a **21-26 Hz steering-rate excess**
(measurable, knee- and `alpha2`-responsive) and an **audible grind** the operator actually hears.
**Nothing demonstrates they are the same phenomenon**, and this is the first test that could have.
⚠ **Do not over-read the null either.** The recording carries only **0.01 %** of its power above
2 kHz, so it is heavily band-limited by codec or cabin; a null above ~2 kHz is uninformative. And a
±1 dB resolution on 224 vs 189 windows is not sensitive to a small effect.
⇒ **CONSEQUENCE FOR V122:** its grind endpoint measures the **steering-rate** phenomenon. That is the
only measured axis available and the build stands — **but whether it moves what the operator HEARS is
now explicitly open.** ✅ **The operator's own report remains the primary evidence for the audible
grind**, which is exactly why the pitch question matters: **high whine / mid buzz / low growl** would
tell us in one sentence whether the audible grind is even inside the recording's usable band.
Tools: `rlog-tools/decode/extract_audio_v112.py`, `rlog-tools/decode/audio_engaged_vs_manual.py`.

## ✅ AUDIO IS EXTRACTABLE FOR THE CURRENT BUILD — the 50 Hz ceiling does NOT apply to it
The corpus's blindness above ~49 Hz is a property of the **CAN/IMU** channels (all 100 Hz). The rlogs
also carry **`rawAudioData`** PCM, and it is **not** subject to that limit. Extracted for **r22
(V112)**: **11,364,800 samples = 710.3 s at 16 kHz.**
`rlog-tools/decode/extract_audio_v112.py` (the pre-existing `extract_audio_grind.py` has a stale
`_cache_<tag>` path from the 2026-08-26 reorg and no longer runs).
```
   A) SPECTRUM, share of 50-7800 Hz        B) AM ENVELOPE peak modulation rate
      100- 300 Hz   34.50 %                   100-300 Hz    5.86 Hz    21-26 Hz share 11.6 %
      300- 800 Hz    3.17 %                   300-800 Hz    5.37 Hz                    3.9 %
      800-2000 Hz    5.88 %                   800-2000 Hz   5.86 Hz                    2.0 %
     2000-5000 Hz    0.01 %                   2000-5000 Hz  5.37 Hz                    5.7 %
     5000-7800 Hz    0.00 %                   5000-7800 Hz  5.86 Hz                    9.8 %
      strongest lines: 51, 52, 53, 54, 55, 56 Hz
```
⭐ **THE LEAD: the strongest audio lines are at 51-56 Hz — ABOVE the 50 Hz ceiling of every other
channel.** That is exactly the region where the operator's *"moved to a higher frequency"* would be
invisible to all previous analysis, and it is a candidate for the current grind #1.
🛑 **IT PROVES NOTHING YET.** This is the **whole drive**, not an engaged-vs-manual contrast, so
51-56 Hz could equally be engine or road. ⊕ And the AM peak is **5.4-5.9 Hz in EVERY carrier band**,
which looks like a **common source or an artifact**, not a steering signature — a real grind
modulation would not be identical across five decades of carrier.
⚠ Also note **0.01 % above 2 kHz**: the audio is heavily band-limited, by the codec or the cabin.
Any claim above ~2 kHz is unsupported by this recording.
✅ **NEXT STEP, and it needs no new drive:** align the PCM to the CAN timebase and split
**engaged vs manual**. That isolates the LKAS-specific acoustic component and would settle whether
51-56 Hz is the moved grind #1 or ordinary vehicle noise.

## 🛑 CAVEAT ON V122's ENDPOINT — GRIND #1 MAY BE **ABOVE THE CORPUS'S NYQUIST**
The operator reports grind #1 moved to a **higher** frequency. My within-corpus measures do **not**
reproduce an upward drift on recent builds:
```
   cs_rate engaged band shares (p90 of 1-49 Hz)     21-26   26-34   34-42   42-49   argmax
     V104                                           0.729   0.705   0.027   0.017   21-26
     V105                                           0.528   0.812   0.029   0.026   26-34
     V106                                           0.243   0.689   0.044   0.027   26-34
     V107                                           0.139   0.087   0.022   0.016   21-26   <- collapses
     V111                                           0.168   0.121   0.052   0.038   21-26
     V112                                           0.218   0.140   0.047   0.044   21-26
     V112                                           0.205   0.122   0.041   0.034   21-26
   imu_vert argmax is 42-49 Hz on nearly EVERY build INCLUDING stock (road/tyre background),
     but V111 0.157 and V112 0.134/0.110 sit above V102-V107 (0.073-0.106).
   Mode-frequency drift across builds: 7-9 Hz rho +0.391 p 0.134 | grind rho -0.327 p 0.216
     -- NEITHER resolved, and the grind trend points DOWN, not up.
```
🛑🛑 **BOTH CHANNELS SAMPLE AT 100 Hz ⇒ NYQUIST 50 Hz. Anything above ~49 Hz is INVISIBLE in
this entire corpus**, and the 42-49 Hz figures sit at the aliasing edge and cannot be trusted.
⇒ **The engaged-specific excess I CAN measure on current builds is at 21-23 Hz. Whether that is what
the operator now hears as grind #1 — or something above 50 Hz that no route can show — is
UNRESOLVED.** ⇒ **V122's 21-26 Hz primary endpoint may be aimed at a band the symptom has left**, the
same error class the operator already caught once.
✅ **CHEAPEST FIX, and it is not a drive:** a **phone voice memo during a grind event**, or simply the
**pitch** — high whine (>1 kHz) / mid buzz (200-800 Hz) / low growl (<100 Hz). **A hum or a recording
pins the frequency immediately** and would tell us whether the kit's instruments can see it at all.
⚠ **This does not change the decision to flash V122**: its grind lever is the only measured one, its
authority gain is independent of the band question, and it is bit-identical below 31.8 deg/s. **But
the endpoint may be unmeasurable, so the operator's own report will be the primary evidence.**

## 🛑🛑 THE PEAK-TURN OSCILLATION IS **PROBABLY MECHANICAL** — three independent lines converge
The last untested generator hypothesis was the **`|model|`-scaled signum**: `|model|` rises **7-9×**
with angle, so if it set the generator's amplitude the harmonics would be **angle-gated**. Tested:
```
   by |ANGLE|  0-5 1.102 | 5-10 1.168 | 10-20 1.058 | 20-40 1.377 | 40-400 1.107
               high/low = 1.004   CI [0.843, 1.586]        <- FLAT
   (by SPEED and by |RATE| were already flat)
```
✅ The harmonics are **REAL** (1.233× vs a non-oscillating control, CI [1.060, 1.503]) but track
**NOTHING** — not speed, not rate, not angle. ⇒ **the harmonic signature is INTRINSIC to the mode,
unmodulated by how the car is driven.** That is what a **mechanical** nonlinearity looks like.
**THREE CONVERGENT LINES:** `f0` invariant to a 2× gain change · harmonics track neither firmware
saturation axis · harmonics track no operating variable. ⊕ Plus the ring-down (ζ 0.017-0.036,
**Q 14-29**, motor/rack-side) and the 6-9 Hz anti-damping being **present in stock**.
⚠ **Firmware is not irrelevant** — the oscillation is **engagement-amplified 2.8×**, **angle-gated**,
and its energy is **manufactured downstream of the command** ⇒ **firmware supplies the EXCITATION,
the mechanics supply the MODE.** 🛑 But every firmware excitation path is now closed: move it
(refuted) · damp it (rail-closed) · relay knee (**saturating**) · model bandwidth (GATE 2) · FIR notch
(arithmetically impossible) · `0xC4080` (never-raise) · `alpha2` (**costs** the damper).
✅ **⇒ A MECHANICAL INSPECTION IS NOW WORTH MORE THAN ANOTHER CAL EDIT.** A lightly damped Q 14-29
mode at 7.8 Hz with an intrinsic nonlinearity, motor/rack-side, is the signature of **lash or a worn
compliant element** — intermediate-shaft U-joints, rack bushings, tie-rod ends, the EPS
motor-to-rack coupling. ⚠ **[BELIEF, three convergent measurements] — a direction to check, not a
diagnosis**; the kit has no mechanical instrumentation.
⊕ V122 is unaffected: its grind-#1 lever and authority gain stand either way.
memory: [[accord-the-oscillation-is-probably-mechanical-not-firmware]]

## ✅ V122 IS THE BUILD TO FLASH — and the dose check came back UNINFORMATIVE, which is itself useful
Before recommending the `alpha2 = 8` dose I checked empirically whether cutting the damper worsens
the oscillation, using V109's already-flown `alpha2` 22 → 14 step (a **−1.3 %** damper cut):
```
   large-angle 6-9 Hz p90 / small-angle p90, per route
   a2=22 (n=13) median 2.667      a2=14 (n=3) median 3.269
   a2=14 / a2=22 = 1.225   route-bootstrap CI [0.618, 5.048]
```
🛑 **NOT RESOLVED** — the CI spans a factor of **8**. ⊕ And the reason is stark: **r22 = 2.10 vs
r23 = 10.67 on the SAME FIRMWARE**, a 5× same-firmware spread that swamps any group difference.
⊕ A **1.3 %** damper cut producing a 22.5 % oscillation rise would need **17× amplification** —
implausible ⇒ **the 1.225 is route noise, not a damper penalty.**
⇒ **The empirical check cannot guide the dose in either direction.** The dose therefore rests on the
**arithmetic margin**: `alpha2 = 8` costs **4.3 %** of the damper, **1/20th** of the V94 cut that
caused an abort. **That is sound, and `alpha2 = 8` stands.**
⚠ **Recorded for reading the next drive: the r22/r23 pair spans 2.10-10.67 on identical firmware.**
Any single-drive oscillation comparison must clear that, and almost nothing will.

### ✅ V122 — THE BUILD TO FLASH
```
   39990-TVA,A160-V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST-0x13000-0x100000.rwd
   image  b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0
   .rwd   cf40e9a4af4172fe2a627517cf6657a11bf52ac50d59bb2ca01e2f8c55fcbc6b
   41/41 assertions · 50/50 CRC · 5 payload bytes · cal-only, NO CAVE · zero unattributed vs V112

              knee 0xC40BC   K1 0xC40D2   alpha2 0xC40DC
   V112 (car)     1800           612           14
   V122           3000          1020            8
```
✅ **grind #1 −21.7 %** (the only measured axis) · ✅ **more assist above 31.8 deg/s**, bit-identical
below · 🛑 **the peak-turn oscillation will probably NOT improve** — that mode is mechanical, cannot
be moved or damped further, and `alpha2` costs it 4.3 %.
⚠ Two variables move at once, at the operator's explicit request ⇒ a better or worse drive will not
say which half did it.

## 🛑 V121 WILL PROBABLY FIX **NEITHER** SYMPTOM — the knee axis is SATURATING
Operator asked directly whether V121 fixes both. **Measured answer: no.**
```
   knee   21-26 Hz share   step ratio   relay saturation duty   duty removed
    300      0.63080                        29.08 %
    600      0.24591        2.57x           19.17 %             -9.9 pp
   1800      0.21341        1.15x            6.75 %            -12.4 pp
   3000        --                            3.70 %             -3.1 pp   <- V121's step
```
🛑 **The 1800→3000 step removes only 0.25× as much relay saturation as 600→1800 did — and that
step bought only 1.15× on the band.** ⇒ **V121's expected grind-#1 gain is about 4 %.**
🛑 **On the oscillation its effect is UNKNOWN** — the mechanism failed two independent checks (the
closed-loop simulation, and the harmonics not tracking the relay's saturation axis).
```
                 grind #1                              oscillation
   V121    ~4 %, the axis is exhausted        UNKNOWN, mechanism twice unsupported
   V115    -21.7 % predicted, measured axis   -4.3 % on the damper (a COST, not a benefit)
```
⇒ **This DOWNGRADES V121 as a symptom fix**, and it is a self-correction: V121 was the standing
recommendation for many ticks, and **the corrected 21-26 Hz band is what changed it.**
✅ **V121's honest remaining value is AUTHORITY, not symptom relief**: 1.571× / 1.667× more friction
above 31.8 deg/s ⇒ by the verified polarity, **MORE ASSIST** exactly where the operator reports
acceleration feeling low — and **bit-identical below 31.8 deg/s**, so the risk is near zero.
⇒ **REVISED SEQUENCE: V115 first (grind #1, 5× the expected effect, 1 payload byte). V121 second, and
framed as an AUTHORITY build, not a fix.**

## ✅ V115 IS BYTE-VERIFIED AND **PRE-REGISTERED** — `docs/scoring/SCORING-V115-preregistered.md`
Full diff against V112: **1 payload byte + 1 CRC trailer.** The cleanest single-variable build in the
kit.
```
   0xC40DC   0e -> 08     alpha2 14 -> 8
   0xC4FFC   CRC trailer
   IDENTICAL: knee 1800 · K1 612 · K0 0 · pole 408 · clamp 511 · gain 5346 · Lever B FB / 5244
   sha256 5f804a8a2aee5e18da226cfebe4b2bec564713a4183613e3aed846460a191a97
```
**PRIMARY ENDPOINT: the 21-26 Hz engaged share**, p90, as a fraction of each window's own 1-45 Hz
power. **V112 baseline 0.21341**; lane arithmetic predicts **about 0.167**.
```
   <= 0.180        alpha2 CONFIRMED -- next step is a2 = 6 (-35.2 % grind, -8.7 % damper)
   0.180 - 0.230   NOT RESOLVED -- inside the V112 two-drive spread; call it neither way
   >  0.230        alpha2 REFUTED for grind #1 -- stop this axis, fly V121
```
🛑 **The band is 21-26 Hz, NOT 18-22** — the old bands straddle the real peak and both miss it,
which produced every grind-#1 null this session.
Secondary, reported but never overturning the primary: **peak frequency** (V112 21.09/21.29 Hz,
expect ≤ 21.1; a RISE contradicts the mechanism) · **the damper must survive** (6-9 Hz p90 at
|ang| ≥ 20°; a large rise is the **V94 signature ⇒ revert**) · **assist** (engaged p99 |rate| ≥ 77.1
deg/s) · **`STEER_STATUS == 4` must be 0**.
✅ **Honest split recorded in the card: the STRUCTURAL half is strong** (selectivity is arithmetic
from the traced lane; 20× safety margin vs V94), **the EMPIRICAL half is weak** (`alpha2 = 14` on only
3 routes ⇒ collinear with build era; arithmetic assumes the 1 kHz rate).

## ✅✅ `alpha2` **IS** THE FREQUENCY-SELECTIVE LEVER — V115 is the recommended flight for GRIND #1
`alpha2` = `cal(0xC40DC)` is the EMA-A coefficient in `FUN_00041464` (`state += (diff*alpha2)>>6`
⇒ alpha = alpha2/64), and its input is a **first difference**, so the lane is `|1-z^-1|*|H_ema|` —
**a differentiator whose response RISES with frequency.** ⇒ lowering `alpha2` cuts **high**
frequencies far more than low ones. **Selectivity by construction.**
```
   freq       a2=22      a2=14      a2=8      8/14     what lives there
    3.0 Hz   0.018831   0.018795   0.018665  0.993x   LKAS command band -- UNTOUCHED
    7.8 Hz   0.048680   0.048071   0.046008  0.957x   the oscillation / damper   -4.3 %
   23.4 Hz   0.138812   0.126319   0.098848  0.783x   GRIND #1 PEAK             -21.7 %
   50.0 Hz   0.251820   0.194102   0.122891  0.633x
```
✅ **5.07× more cut at grind #1 than at the damper; 0.993× at 3 Hz** ⇒ the band where **steering
velocity and acceleration live is untouched.** **It removes loop gain at 21-26 Hz without adding
mass, friction or inertia** — the operator's constraint, satisfied by construction.
✅ **SAFETY GATE PASSES against the kit's worst precedent:** this is the lane **V94 cut 6×**, after
which the operator **aborted** — and `alpha2` 14→8 costs only **4.3 %** of that damper, **1/20th** of
V94's change. ⊕ **The precedent is already flown**: V109's 22→14 was selective the same way
(damper −1.3 %, grind #1 −9.0 %, **7.19×**) and flew **fault-free on V111 and V112**, the operator's
best builds.
⇒ **V115 (V112 + `0xC40DC` 14→8) is BUILT AND UNFLOWN** — `5f804a8a…` / `f1a47bb7…`, **42/42**,
cal-only. Now backed by **four independent things**: measured amplitude (1.340 [1.12,2.29]), measured
frequency shift (1.113 [1.06,1.17], p 0.035), structural selectivity (5.07×), and a flown precedent.
🛑 Caveats: `alpha2=14` is only on V111/V112 (**3 routes**) ⇒ the empirical half is **collinear with
build era**; the arithmetic assumes the **1 kHz** rate; `alpha2` also cuts **35-50 Hz by 30-37 %**
(grind #2 territory — likely helpful, **unverified**).
⇒ **SEQUENCE: V115 first, then V121.** memory: [[accord-alpha2-is-the-frequency-selective-lever]]

## ✅ THE `alpha2` DOSE LADDER, AND ITS FLOOR — so the next step is chosen, not improvised
```
   a2   EMA corner   3 Hz cmd   7.8 Hz damper   23.4 Hz grind#1   selectivity   note
   14     34.8 Hz     1.000x       1.000x           1.000x           --        CURRENT (V111/V112, flown)
   12     29.8 Hz     0.999x       -0.8 %           -5.0 %          6.47x
   10     24.9 Hz     0.997x       -2.0 %          -12.0 %          5.87x
    8     19.9 Hz     0.993x       -4.3 %          -21.7 %          5.07x      <- V115, BUILT
    6     14.9 Hz     0.985x       -8.7 %          -35.2 %          4.04x      the practical knee
    5     12.4 Hz     0.977x      -12.7 %          -43.7 %          3.44x      caution
    4      9.9 Hz     0.963x      -18.8 %          -53.2 %          2.83x      caution
    3      7.5 Hz     0.934x      -28.7 %          -63.9 %          2.23x      toward the V94 direction
```
✅ **A PRINCIPLED FLOOR:** the EMA corner falls with `alpha2`, and **at `a2 = 4` it reaches 9.9 Hz —
BELOW the 23.4 Hz target and close to the 7.8 Hz mode.** Past that the filter **eats the damper faster
than it eats the grind**, which is why selectivity collapses from 5.07× to 2.83× and then 1.27×.
⇒ **`alpha2 >= 6` is the usable range; `alpha2 <= 4` is the V94 direction.**
⇒ **FLY V115 (`a2 = 8`) FIRST, NOT a bigger dose.** It is already built (42/42), it is the smaller
step from the flown 14, and the empirical half of the `alpha2` case rests on **3 routes**. **`a2 = 6`
is the identified next step** — it nearly doubles the grind cut (−35.2 % vs −21.7 %) for a damper cost
of **−8.7 %**, still ~10× smaller than V94's −83 % — **but only after V115 shows the axis works on the
road.** 🛑 **Do not build `a2 = 6` yet**: seven unflown artifacts already exist, and a bigger dose
flown first would confound a larger effect with a larger cost.

## 🛑🛑 GRIND #1 IS A **MOVABLE POLE** — and `alpha2` (`0xC40DC`) is its handle
Same test that classified the 7.8 Hz mode as **mechanical** (`f0` invariant to a 2× gain change),
applied to grind #1 on the **corrected 21-26 Hz band**, 13 Lever-B-ON routes:
```
   B) FREQUENCY   a2_C40DC (14 vs 22)  rho +0.587  p 0.035  hi/lo 1.113  CI [1.06, 1.17]  <== HIT
   A) AMPLITUDE   a2_C40DC             rho +0.537  p 0.059  hi/lo 1.340  CI [1.12, 2.29]  <== HIT
                  knee_C40BC           rho -0.406  p 0.168  0.622 [0.29, 1.52]
```
✅ **`alpha2 = 22` → ~23.5 Hz; `alpha2 = 14` → ~21.1 Hz**, both CIs excluding 1.0 ⇒ **grind #1 is a
CLOSED-LOOP POLE, relocatable in firmware, not merely dampable.** **A categorically better position
than the oscillation**, where *move it* is refuted, *damp it* is measured-closed, and only *excite it
less* remains.
✅ **`alpha2` moves BOTH endpoints the same way**, and **V109 already went 22 → 14** — correct on both,
which the kit could not have known while measuring the wrong band.
✅ **`V115` (`alpha2` 14 → 8 on a V112 base) IS ALREADY BUILT AND UNFLOWN** — `5f804a8a…` /
`f1a47bb7…`, 42/42. **The direct next step on this axis, no new build needed.**
🛑 **CONFOUND:** `alpha2 = 14` exists only on V111/V112 (3 routes) ⇒ **collinear with build era**.
⇒ **[EVIDENCE the frequency is firmware-movable; BELIEF that `alpha2` specifically moves it.]**
⚠ `K1` also hits both but is perfectly confounded with `knee`. ⚠ The friction-row `rho = +0.729,
p = 0.005` has arms of **5 vs 1** — **not a result.**
🛑 Before flying V115, check `alpha2`'s **other** role: it sets the `gp-0x6b26` bandpass upper corner,
and lowering it **rotates** that vector (damping up, mass down). **Not analysed here.**
memory: [[accord-grind1-is-a-movable-pole-and-alpha2-is-its-handle]]

## 🛑🛑 OPERATOR CORRECTION: **GRIND #1 MOVED UP** — the kit's bands miss it, and the KNEE **IS** its lever
> *"grind #1 has moved to a new, higher frequency since a few firmware versions ago."*

**Every grind-#1 measurement in this session used 18-22 Hz** — its band in the V62 era. **He is
right, and that invalidated all of them.**
```
   ENGAGED-minus-MANUAL excess, peak location (within-route, so road/exposure cancel):
     STOCK        15.0 Hz (+4.4 dB)
     V90..V96     28.1 / 20.3 / 32.8 / 28.3 / 20.5 Hz
     V100..V107   22.9 / 22.7 / 23.4 / 24.6 / 27.0 / 21.1 Hz
     V111, V112   20.9 / 23.2 / 23.4 Hz        <- recent builds cluster 21-23.4
```
🛑🛑 **Stock peaks at 15.0 Hz, every mod at 20.3-32.8 ⇒ the kit's TWO bands (18-22 and 26-31)
STRADDLE the real peak near 23 Hz and BOTH MISS IT.**

### ✅ RE-RUN ON 21-26 Hz — THE KNEE IS A MEASURED GRIND-#1 LEVER
```
   band                      knee300  knee600  knee1800   300/1800        300/600 (n=8 vs 7)
   18-22 Hz (what I used)    0.26082  0.23104   0.33799   0.772 [0.575,1.169]      --
   21-26 Hz (the real peak)  0.63080  0.24591   0.21341   2.956 [1.164,4.079] <==  2.565 [1.010,4.664] <==
   26-31 Hz (kit's other)    0.19954  0.17920   0.10255   1.946 [0.986,7.375]      --
```
✅ **Monotone across all three knee levels; BOTH contrasts exclude 1.0, including the well-powered
n=8-vs-7 arm.** Raising the knee cuts the band ~2.6-3×. On the old band the same data gives **0.772,
pointing the WRONG WAY** — exactly what I reported.
🛑 **`c91a1ba5` — "the knee has NO measured dose-response on grind #1" — is WITHDRAWN.** It was a
**band error, not a null.** ⊕ And the operator's own report — grind #1 going constant → *"rare… a few
moments"* exactly when the knee went 600 → 1800 — which I could not reproduce and treated as
unsupported, **was right; my instrument was mis-aimed.** ⊕ The earlier "four predictors at p<0.10 that
contradict the operator" result used the same wrong band.

### ✅ CONSEQUENCES
1. **V121 (knee 1800 → 3000) now has a MEASURED dose-response behind it on grind #1** — more than its
   oscillation rationale ever had.
2. **`docs/scoring/SCORING-V121-preregistered.md` is CORRECTED**: grind #1 is **no longer excluded as
   an endpoint**, and its band is **21-26 Hz**.
3. ⚠ `n = 2` at knee 1800, and knee is **perfectly confounded with K1** ⇒ what is established is
   *"the knee-or-K1 axis cuts grind #1"*, **not which cell.**
4. ⚠ **Re-examine every other grind-#1 null in this session on 21-26 Hz** before trusting it.
memory: [[accord-grind1-moved-up-and-the-knee-IS-its-lever]]

## 🛑 THE IMU LEVER HUNT RETURNS NOTHING — and it was PRE-REGISTERED as uninformative if so
Ran the natural-experiment design with the new IMU outcome on all Lever-B-ON routes:
```
   route IMU eng/man:  r77 0.795 · r22 0.801 · r7e 0.961 · r1e 1.015 · r7f 1.113
                       r78 1.138 · r21 1.176 · ra6 1.451 · ra4 2.550
   gain_C6CD0  1.134 [0.77, 2.46] not resolved      biq_C649B  1.134 [0.77, 2.46] not resolved
   knee / K1 / alpha2 / friction row : too few routes per arm (3/1, 8/1, 2/7, 4/1)
```
🛑 **Nothing resolves, and per the instrument's own pre-registration that means NOTHING.** The IMU
is **~10× diluted** ([[accord-the-imu-is-a-valid-but-weak-grind-instrument]]) and only **9 routes**
carry usable IMU with Lever B held constant, with arms of **1-4 routes**. **Only a positive IMU result
is informative; these nulls are not evidence of absence** and must not be cited as such.
⚠ One unexplained observation, recorded not acted on: **`ra4` (V104) sits at 2.550, 2.2× the next
highest.** No cal in the set explains it. It is a single route.

### ⇒ THE HONEST STATE OF THE SEARCH, AFTER CLOSING MOST OF IT
| avenue | status |
|---|---|
| move the 7.8 Hz mode | **REFUTED** — `f0` invariant to a 2× forward-gain change |
| damp it more | **MEASURED-CLOSED** — the ±511 rail; `0xC407E` faults if raised |
| excite it less — relay knee | **V121 built**, mechanism failed two independent checks |
| excite it less — model bandwidth `0xC50D8` | **GATE 2 BLOCKED** — +63.4° phase, sign undetermined |
| frequency-selective filters | **arithmetically closed** — 3-tap FIR cannot notch without killing DC |
| Coulomb floor `0xC4080` | **NEVER-RAISE**, corroborated by this session's own measurement |
| angle handle, table (b) | orthogonal, **untested**, modest (~17 %) |
| grind #1 | **unmeasurable** without creep exposure; the IMU is too diluted to substitute |
🛑 **The binding constraint on BOTH symptoms is DATA, not analysis.** Further analysis passes on this
corpus are producing underpowered results, and saying so is more useful than producing more of them.
✅ **The three asks in `docs/scoring/SCORING-V121-preregistered.md` remain the highest-value actions**,
and none needs a build or a flash.

## ✅⚠ THE IMU IS A **VALID BUT WEAK** GRIND-#1 INSTRUMENT — and it needs no creep exposure
Every grind-#1 measure so far uses **steering rate**, which needs creep exposure **no post-V107 route
has**. Grind #1 is **audible and felt** (*"it vibrated the entire car"*), so a chassis accelerometer
measures it directly. ✅ **`imu_vert`/`imu_lat` log at 100 Hz on all 17 routes** (ratio 1.00 vs
`cs_rate`, checked first) ⇒ **Nyquist 50 Hz, 18-22 Hz genuinely visible, not aliased.**
Validated on the Lever B natural experiment, engaged-vs-manual within each drive:
```
   OFF (2 routes) 1.2020    ON (9 routes) 1.0552    OFF/ON = 1.139   CI [1.005, 1.338]
```
✅ **It discriminates** — CI excludes 1.0. 🛑 **But only just** (lower bound 1.005), and it recovers
**1.139×** where the steering-rate instrument recovers **2.32×** for the same known effect ⇒
**dilution about 10×**; a true effect `X` shows as about `1 + (X-1)/10.8`, so **it needs a true effect
above ~3× to clear its own floor.**
⇒ **USE IT** as the only grind-#1 instrument that works on routes with **no creep exposure**.
🛑 **DO NOT use it to declare a null** — at 10× dilution *"the IMU shows nothing"* is consistent with a
real 2× change. **Only a POSITIVE IMU result is informative.** ⚠ Validated at 18-22 Hz only;
re-validate before using it at 6-9 Hz.
memory: [[accord-the-imu-is-a-valid-but-weak-grind-instrument]]

## ⭐ A NEW, VIRGIN CANDIDATE: the model's own bandwidth `0xC50D8` — blocked on GATE 2, not on hazard
**The mechanism, quantified for the first time.** `FUN_0003b8f6` is the **1 kHz** plant-model
observer; its input passes **two cascaded EMA stages** at `pole2 = 0xC50D8 = 122` (`alpha/4096`):
```
     1.0 Hz  two stages 0.9586      7.8 Hz  0.2758  <- THE MODE      20 Hz  0.0548
   => at the mode the MODEL sees only 27.6 % of the real content, so ~72 % of the 7.8 Hz motion is
      classified as DISTURBANCE and the friction signum CHASES it.  That IS stick-slip, quantified.
   to pass 50 %: pole2 = 196 (1.6x)    80 %: 382 (3.1x)    90 %: 560 (4.6x)
```
✅ **The hazard that would have blocked it is CLOSED.** `0xC50D8` sits in `[0xC5000, 0xC5FFC)`, and
[[reference-crc-chain-is-50-blocks-c5000-not-a-gap]] closed that block **on three independent
traces**: boot does a **blank/presence check only**, the app range contains **no CRC32 polynomial**,
and there are **zero xrefs to `0xC5FFC`** in the whole 1 MiB image ⇒ the stale CRC is a **RED HERRING
for V40's ignition fault**, which has its own explanation
([[accord-aggregator-reaches-motor-via-gp6acc-bridge]]). **It is an ordinary editable cal.**
✅ **VIRGIN on all 115 images** — `pole1 = 832`, `pole2 = 122` in stock and in every build ever cut.
✅ **Orthogonal to the K1/knee confound** — it is on neither axis.
🛑 **NOT A BUILD PROPOSAL. It is blocked on GATE 2, and squarely.** The model's input `gp-0x6b98` is
**BROADBAND** ([[accord-v87-flew-the-probe-fired-and-6b98-is-broadband]]) **and downstream of the
assist**, so feeding it into the model is a **feedback path** — widening its bandwidth widens that
feedback, in a loop containing a **lightly damped Q 14-29 mode at 7.8 Hz**. That is exactly the class
where **phase, not just magnitude, decides stability**.
⇒ **What it needs before any build: a GATE 2 magnitude-AND-phase analysis of the `gp-0x6b98` → model
→ residual → assist path at 6-9 Hz.** Until then it stays a candidate. ⊕ Both arguments are on the
record: *widening lets the model explain the oscillation so the signum stops chasing it* vs *widening
increases feedback bandwidth around a lightly damped mode*. **Neither is settled.**

## 🛑🛑 GATE 2 **FAILS IT** — the sign is undetermined, and determining it costs the bricking class
```
   pole2   |H(7.8Hz)|   phase        vs stock gain   phase ADVANCE
     122     0.2758    -113.86 deg      1.000x          +0.00 deg
     196     0.5004     -87.19 deg      1.814x         +26.67 deg
     382     0.7998     -50.42 deg      2.900x         +63.44 deg   <- the 80 %-pass dose
     560     0.9002     -34.13 deg      3.264x         +79.72 deg
```
🛑 **A 63° phase advance**, in a branch that is **added** to the model and then **subtracted**
downstream. With `|residual|² = |M|² + |A|² − 2|M||A|·cos(φ_M − φ_A)`, a 63° move swings the cosine
by up to **0.7** ⇒ **it can make the symptom better OR worse, and magnitude reasoning cannot pick
which.** ⇒ **the lever fails GATE 2 on the phase leg, which is precisely what GATE 2 exists to catch.**
⚠ (My printed rationale said *"~46 deg"* from a stale literal; the computed value is **+63.4°**.)

### 🛑 AND THE MEASUREMENT THAT WOULD SETTLE IT IS NOT CHEAPLY AVAILABLE
Needed: **`arg(ACTUAL) − arg(MODEL)` at 6-9 Hz** — the real torque-sensor response against the
model's reconstruction of it.
⊕ The kit's **+137°/+139°** result is **delivered assist vs WHEEL rate** — a *different pair* — so it
**does not transfer**, however tempting the number is.
🛑 **None of `gp-0x4f60`, the model output `gp-0x6bf6`, or the residual `gp-0x6bfc` has ever been on
the wire** ⇒ the phase cannot be obtained from existing telemetry, and obtaining it requires a
**CAVE PROBE — the only class that has ever bricked this ECU (V24, V27, V48B).**
⇒ **STATUS: BLOCKED, not deferred.** The candidate is real, virgin, hazard-free on CRC, and
orthogonal to the K1/knee confound — **and it still cannot be built**, because its sign is unknown and
the price of learning it is the one risk class this kit refuses on cal-only grounds.
✅ **Recorded so the next session does not re-derive the lever and skip the gate.** The magnitude
argument is seductive (3.6× attenuation at exactly the mode, on exactly the right sensor); **the phase
argument is what kills it.**

## 🛑 CORRECTION — WHICH POLE FILTERS WHICH BRANCH. It was backwards, and the fix STRENGTHENS it.
Re-read of `FUN_0003b8f6`, instruction by instruction:
```
   gp-0x6b98  (command / assist path)  -> TWO EMA stages at tp+0x50d4 = 0xC50D4 = pole1 = 832
   gp-0x4f60  (TORQUE SENSOR)          -> TWO EMA stages at tp+0x50d8 = 0xC50D8 = pole2 = 122
```
I recorded pole2 as filtering the model's input generally. **It filters the TORQUE-SENSOR branch
specifically**, and pole1 — much faster — filters the command branch. At 7.8 Hz, 1 kHz task:
```
   command branch   pole1 = 832  corner 36.3 Hz   two stages |H| = 0.956   <- passes fine
   torque branch    pole2 = 122  corner  4.81 Hz  two stages |H| = 0.276   <- attenuated 3.6x
```
✅ **This makes the mechanism STRONGER.** The torque sensor measures **across the torsion bar** —
**exactly the element whose resonance this is** — and it is the one branch the model attenuates
3.6×. ⇒ **the model systematically under-represents the resonance at the very sensor that sees it,
so `residual = model - actual` carries it, and the friction signum chases it.**
⊕ It also **weakens my own GATE 2 objection**: `gp-0x4f60` is a **measurement**, not a feedback of
our own assist, and the loop through it is Honda's ordinary assist loop, present in stock. The
objection is not void — assist still moves the bar which moves the sensor — but it is **a normal
sensing loop, not a novel feedback path we would be creating.**
🛑 **Still not a build.** GATE 2 needs the magnitude *and phase* of
`gp-0x4f60 → model → residual → assist` at 6-9 Hz, and raising `pole2` **advances phase** in a branch
that is subtracted — sign and phase both have to be worked through, not assumed.

## 🛑 THE MODEL PATH'S 3-TAP FIR **CANNOT** BE MADE A NOTCH — the last hidden-filter hope, closed
`FUN_0003b8f6` contains `y[n] = a·x[n] + b·x[n-1] + c·x[n-2]` with **float** coefficients at
`0xC5048/504C/5050`, feeding the same `|model|` that multiplies the Coulomb signum. Floats in the
CRC-skipped `0xC5000` block — it looked like the frequency-selective lever the kit says does not exist.
```
   a = 10.000000   b = 0.800000   c = 0.400000     sum = 11.2   IDENTICAL stock -> V121
   |H| at 7.8 Hz:  11.1974 @1 kHz (0.02 % below DC)   |   10.9515 @100 Hz (2.2 % below DC)
```
✅ **As shipped it is a near-flat GAIN of 11.2, not a filter** — `b` and `c` are tiny against `a`.
🛑 **And it cannot be retuned into one.** A 3-tap FIR notch at `f0` needs `b = -2cos(w0)`, giving DC
gain `a+b+c` ≈ **0.0024 at 1 kHz** and **0.2375 at 100 Hz** ⇒ **the notch swallows DC**, which is the
model's whole purpose. With only 3 taps the notch Q is ~1 and **7.8 Hz is far too close to DC at
either candidate task rate.** ⇒ **arithmetically closed, not merely risky.**
⊕ It also sits in the block the bootloader skips, `[0xC5000, 0xC5FFC)`
([[reference-crc-chain-is-50-blocks-c5000-not-a-gap]]) — moot now, but recorded.
✅ **What DOES shape this path: the two EMA poles** `0xC50D4` = **832** and `0xC50D8` = **122**
(`alpha/4096`), each applied **twice**. These are 16-bit cals and are genuine frequency handles —
**but they set the MODEL's own bandwidth**, and the chain is a disturbance observer
(`residual = MODEL - ACTUAL`), so detuning them **manufactures residual by mis-modelling** rather
than filtering the symptom. **Not proposed; recorded as the only remaining shaping cells here.**

## ⭐ TABLE (b) IS THE **ANGLE HANDLE INSIDE THE OBSERVER** — orthogonal to the K1/knee confound
Decompiled `FUN_0003b8f6`:
```
   uVar17 = gp-0x6a10                                 <- ABSOLUTE STEERING ANGLE
   if (uVar17 < 0x2711) { LERP tp+0x7b66 (X) / tp+0x7b80 (Y) }   = 0xC6B66 / 0xC6B80 = table (b)
   fVar18 = fVar13 * uVar17 * 0.0009765625 + fVar18;  <- scales a model component INTO the model
```
⇒ **table (b) is ANGLE-SCHEDULED and feeds `|model|` — the exact amplitude that multiplies the
Coulomb signum** (`friction_in = |model|*K1/1024*fVar13 + K0/1024*fVar13`). **It sets part of the
angle-dependence that makes the symptom angle-gated.**
```
   X (deg)  0.00 0.85 1.60 2.12 2.50 3.00 ... 11.94       Y  899 908 981 1060 1083 1084 (flat)
   rise 899 -> 1084 = 1.21x, saturating at 2.5 deg
```
⚠ `|model|` rises **7-9×** with angle and table (b) supplies only **1.21×** ⇒ **most of the rise is
the model itself, not this table.** Do not oversell it.
✅ **Why it still matters: it is ORTHOGONAL.** Every flown mod sits on `K1/knee = 0.34`
([[accord-k1-and-knee-are-perfectly-confounded]]); table (b) is on **neither** axis — it changes
neither the small-signal gain nor the relay shape ⇒ **an independent lever that adds no new point to
the confounded line**, and **angle-targeted by construction**: flattening `Y` to **899** cuts the
high-angle contribution ~**17 %** and **touches nothing below 2.5°**.
🛑 **Modest**, and [[accord-factord-is-the-angle-error-lever]] calls table (b) *"DEAD as a shaped
lever"* because **88.6 % of engaged driving is in its flat first segment** — true for broadband
driving, but the **angle-gated** symptom lives in the other 11.4 %. **A different question, not a
contradiction.** [BELIEF; NOT proposed as a build yet.]
✅ **CLOSED, so it is not re-asked:** the relay's `12` is a **hardcoded `0xc` immediate, not a cal**
⇒ **no third handle** exists to hold the gain while varying `K1` independently of `knee`. **The
confound is structural; separating them requires a gain change (V113).** ⊕ Instruction-level address
confirmations: `knee` `tp+0x50bc`=`0xC40BC` · `K1` `tp+0x50d2`=`0xC40D2` · `K0` `tp+0x5080`=`0xC4080`
· friction EMA pole `tp+0x50d0`=`0xC40D0` — all match the kit's documented addresses.

## 🛑🛑 `K1` AND `knee` ARE **PERFECTLY CONFOUNDED** — a design critique of V121
```
   K1=204 knee= 300 -> V100..V107        K1=204 knee= 600 -> V90,V91,V92,V96,V111
   K1=612 knee=1800 -> V112              STOCK K1=102 knee=600
   knee values flown with MORE THAN ONE K1:  NONE      (every mod holds K1/knee = 0.34)
```
⇒ **the kit has never learned which of the two cells matters** — every result attributed to "the
knee" is equally attributable to `K1`.
🛑 **V121 is `knee 3000 / K1 1020` — ratio 0.34, a FOURTH point on the same line** ⇒ **by
construction it cannot separate them.** *If it works we will not know why; if it fails we will not
know which half failed.*
✅ **Structural, not an oversight:** holding the small-signal gain constant **requires** `K1 ∝ knee`
⇒ **a gain-matched build is inherently confounded**, and separating them **requires a gain change**.
✅ **V113** (`knee 1800 / K1 204`) is the **only built artifact that breaks it** — same knee as V112,
same K1 as V90-V111 ⇒ two K1 levels at one knee, the first separation ever. ⚠ **Cost: gain 0.333×
V112's**, below stock, ⇒ **less assist** ([[accord-friction-polarity-more-assist]]). The mirror
(`knee 600 / K1 612`, 3× gain) is the riskier half.
⇒ **SEQUENCING, recorded so it is deliberate:** **V121 first** — the only candidate that cannot make
normal driving worse (bit-identical ≤ 31.8 deg/s) and it tests the pre-registered endpoint.
**V113 second, ONLY if V121 moves that endpoint** — it is the sole way to learn which cell did it.
**If V121 lands in the “not resolved” band, V113 is not worth its feel cost.**

## ✅ `0xC4080`'s NEVER-RAISE FLAG IS **INDEPENDENTLY CORROBORATED** — and a natural idea is killed
Reasoning that led there: if the generator is **physical** friction, the firmware's counter-lever is
its **friction compensator** — and ours has the **wrong shape**. Real Coulomb friction is
constant-magnitude; ours is `|model|`-proportional:
```
   friction = EMA( |model| * cal(0xC40D2)/1024 * fVar13  +  cal(0xC4080)/1024 * fVar13 )
                    \____ K1, |model|-proportional ____/     \__ K0 = 0, a PURE SIGNUM __/
```
⇒ *"raise `0xC4080` to add a proper constant Coulomb floor."*
🛑 **The kit already flags `0xC4080` NEVER RAISE** — one of three named *flatten-into-a-relay*
hazards ([[accord-plant-model-residual-aggregator-chain]]), and V89 explicitly left it untouched.
✅ **And this session's own discriminator says WHY, independently:** the K0 term has **no amplitude
dependence, so it does not vanish at zero command** ⇒ raising it installs a nonlinearity **active
uniformly across the whole operating range** — **exactly the profile
[[accord-the-harmonics-track-neither-firmware-saturation]] just measured as the generator.**
⇒ **The idea would ADD the thing it was meant to remove.** Correctly flagged; the flag now has a
measured rationale rather than only a structural one.
⚠ A compensator that is constant-magnitude **but gated to vanish near zero** would need a **code**
change ⇒ the cave class that bricked V24/V27/V48B. **Not available.**

## 🛑 THE HARMONICS TRACK **NEITHER** FIRMWARE SATURATION — V121's mechanism weakens again
Two hard nonlinearities sit in the loop and **saturate on different axes**, so they separate: the
**Coulomb relay** on |RATE| (≥ 31.8 deg/s on V112) and the **damper's ±511 clamp** on SPEED (rail duty
15.46 % at 10-25 km/h → 0.23 % above 65, `build_v108` E2).
```
   by SPEED  (16-17 routes, tight CIs)     10-25 1.110 | 25-40 1.159 | 40-65 1.162 | 65-200 1.117
   by |RATE| (7-11 routes, wide CIs)       0-15 1.133 | 15-32 1.096 | 32-60 1.317 | 120+ 1.283
```
✅ **CLAMP hypothesis REFUTED** — well powered, and the ratio is **flat at 1.11-1.16** while the
clamp's own duty falls **67×** across that range. 🛑 **RELAY hypothesis NOT SUPPORTED** — no rise past
31.8 deg/s — ⚠ but that arm is **underpowered**, so **not supported ≠ refuted**.
⊕ Harmonics are **real and pervasive**: every bin > 1.0, most CIs exclude it.
⇒ **A nonlinearity uniformly active across the whole range is not a saturation.** That fits an
always-on mechanism — **physical friction / stick-slip in the column and rack** — better than any
firmware clip, and coheres with the mode being **mechanical** and with the 6-9 Hz anti-damping being
**present in stock**.
🛑 This does **not** overturn [[accord-the-7to9hz-energy-is-manufactured-not-commanded]] — the energy
is still generated downstream of the command. **What changes is WHERE: possibly the PLANT, not the
firmware — in which case no cal edit reaches it.**
🛑🛑 **V121's mechanism has now failed TWO independent checks** (the closed-loop simulation, and
this). ⇒ **It is a build with good engineering properties and a weak mechanism case**: gain held
**exactly** at V112's, more assist above 31.8 deg/s, cal-only, 4 bytes, 40/40, and `knee`'s on-car
track record. **Effect UNKNOWN. Fly it as a TEST, not as a fix** — the pre-registered card's
**> 1.45 = refuted** band is exactly the outcome this makes more likely.

## ✅⭐ THE 7-9 Hz ENERGY IS **MANUFACTURED**, NOT COMMANDED — the hopeful result
16 routes, oscillating windows, band power relative to each signal's **own** 0.5-3 Hz power:
```
   median COMMAND  6-9 / 0.5-3 = 0.00528      median RESPONSE 6-9 / 0.5-3 = 0.13962
   => the response carries 26.5x more RELATIVE 6-9 Hz content than the command
   coherence(cmd, rate) @6-9 Hz = 0.488  vs shuffled 0.356   diff 0.132  CI [0.082, 0.250]
```
✅ **The energy at the resonance is GENERATED INSIDE THE LOOP, not delivered by openpilot** — the
first direct measurement of what [[reference-accord-lkas-lane-is-a-lowpass]] implied.
⭐ Coherence above chance but only 0.488 with 26.5× less relative content ⇒ the command **modulates**
the oscillation without **containing** it: **the signature of a NONLINEARITY** converting a
low-frequency drive into energy at the resonance — matching
[[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]] independently.
⭐⭐ **WHY IT MATTERS.** The mode is a **fixed mechanical resonance** that cannot be moved
([[accord-the-78hz-mode-does-not-move-with-firmware-gain]]) or damped further
([[accord-the-damping-route-is-closed-by-the-rail]]), leaving only *"excite it less"* — and the
obvious worry was that excitation is simply **proportional to 6× torque**, making the operator's two
goals irreconcilable. ✅ **It is not in the command, so it is NOT an inherent price of 6× torque.**
⇒ **the generator can be attacked without giving up torque — the first structural reason to think
both goals are compatible.**
⇒ **V121 status change:** its **PREMISE** (energy generated downstream, attackable without spending
torque) is now **[EVIDENCE]**. 🛑 **Still [BELIEF]: that the Coulomb relay SPECIFICALLY is the
generator** — no measurement isolates it from other nonlinearities. **Effect still UNKNOWN; the
pre-registered card stands as written.**
⚠ `ra4`/`r1e` show command ratios 200-400× the rest with the highest coherences — outliers of a
different kind; medians are used and are robust, but do not pool them naively.

## 🛑🛑 THE 7.8 Hz MODE **DOES NOT MOVE** WITH FIRMWARE GAIN — it is MECHANICAL
A closed-loop pole moves with loop gain; a mechanical resonance does not. The kit classified the
~23 Hz line exactly this way (it **moved 20.3 → 23.0 Hz**). Across 17 routes spanning forward gain
**3564 / 5346 / 7128** and knee **300 / 600 / 1800**:
```
   Spearman(gain 0xC6CD0, f0) = -0.015  p = 0.954     Spearman(knee, f0) = +0.332  p = 0.193
   f0 by gain: 3564 (n=6) 7.764 Hz | 5346 (n=9) 8.008 | 7128 (n=1) 7.617 | stock (n=1) 6.836
```
✅ **`f0` is invariant to a 2× forward-gain change and the group medians are non-monotone** ⇒ a
**FIXED MECHANICAL RESONANCE**, not a relocatable pole. ⊕ Consistent with the ring-down result
(ζ 0.017-0.036, Q 14-29, motor/rack-side).
⚠ **Self-correction:** my script's verdict line said *"f0 MOVES"* on a **max/min spread of 22.9 %** —
dominated by the **single stock route** (6.836 Hz, IQR [6.20, 7.86], overlapping the mods). Spread
across heterogeneous routes is not the test; **the correlation with gain is**, and it is flat.
🛑🛑 **⇒ THE THREE THINGS FIRMWARE COULD DO, AND TWO ARE NOW CLOSED:**
```
   MOVE IT         REFUTED here -- f0 invariant to 2x gain
   DAMP IT         measured-CLOSED by the +-511 rail (0xC407E cannot be raised: V73 -> V74/V75 faulted)
   EXCITE IT LESS  the ONLY route left  ==  V121
```
⇒ **The 7.8 Hz peak-turn oscillation may not be fully eliminable in firmware.** A fixed, lightly
damped mechanical mode that cannot be relocated or damped further can only be **driven less hard**.
✅ That is the correct target definition, not a counsel of despair — and it is exactly what V121 aims
at. 🛑 **Do not promise elimination of this oscillation by any firmware build**; the honest claim is
*reduce how hard it is driven*, which is what
`docs/scoring/SCORING-V121-preregistered.md` measures.

## ✅ **V121's SCORING IS PRE-REGISTERED** — `docs/scoring/SCORING-V121-preregistered.md`
Written **before** the drive so the result cannot be reinterpreted after it. **Primary endpoint: the
harmonic ratio**, one number, with the decision bands fixed now:
```
   < 1.05        relay CONFIRMED as the excitation path
   1.05 - 1.35   NOT RESOLVED -- inside V112's own two-drive spread (0.970-1.455)
   > 1.45        mechanism REFUTED; stop pursuing the relay for this symptom
```
🛑 **V112's own two drives span 0.970-1.455**, so a single V121 drive landing in that band means
**nothing** — recorded now so it is not read as a trend later.
Secondary, reported but never used to overturn the primary: 6-9 Hz p90 at |ang| ≥ 20° matched on
small-angle p90 · **assist check** (engaged p99 |rate| must be ≥ V112's **77.1 deg/s**; below ~70 ⇒
the knee cost authority and **V116 is the fallback**) · `STEER_STATUS == 4` must be **0**.
⚠ **Grind #1 is explicitly NOT an endpoint** — V121 does not target it and it is unmeasurable on
routes with no creep exposure.
✅ **Three operator asks are in the card**, each worth more than another analysis pass: creep
exposure · a mark when grind #1 happens · one stock-configuration drive (p 0.100 → 0.018).

## 🛑🛑 THE DAMPING ROUTE IS **CLOSED** — by the ±511 rail, not by int16
I was about to propose raising `Y[1]`/`Y[2]` of the engaged friction row: it is the one lever whose
direction is **measured on the road**, `Y[0]` has only 1.11× int16 headroom but `Y[1]` has **1.90×**,
and the oscillation's median speed (**35 km/h**) sits between the 20 and 90 km/h knots. `Y[1] =
-24000` is even **flight-proven** — V107 flew it.
🛑 **`build_v108_tva.py` E2 already measured it harmful** (route `1e`, episode-bootstrapped, 10 episodes):
```
   bin (km/h)    V107 rail duty (Y1=-24000)      V106/V108 (Y1=-17202)
    10-25        32.32 % [29.93, 35.68]           <= 15.46 %
    24-40        21.27 % [19.93, 22.51]           <= 10.45 %
      65+        <= 0.23 %                        <=  0.23 %
```
**A damper that hits its clamp 32 % of the time IS A RELAY** — the class that made V80 *"the worst
grinding ever recorded."* ⚠ And at **24-40 km/h, where the oscillation lives, V108 ALREADY rails
≤ 10.45 %** ⇒ **no safe headroom at the symptom's own speed.**
✅ **The binding constraint is `gp-0x6b26`'s ±511 clamp (`0xC407E`), not int16 — and it is
HARD-BLOCKED**: Honda ships 511, one count under its own 512 trip, and **V73 raised it ⇒ V74/V75
hard-faulted.** More damping needs more rail; more rail needs `0xC407E`; that faults the ECU.
⇒ **ONLY EXCITATION REDUCTION REMAINS**, which is exactly what **V121** does (knee 1800→3000,
softening the signum indicted as the excitation path). **V121's case is strengthened BY ELIMINATION**
— its mechanism is still [BELIEF] and its effect still UNKNOWN, but it is the only direction on this
symptom not measured-closed. ⊕ `Y[2]` alone has rail headroom (≥0.03 % duty at 90+) but moves the
35 km/h coefficient only **1.10×** — not worth a flight.

## 🛑 THE DECELERATION TRIGGER **DOES NOT SURVIVE STRATIFICATION** where the symptom lives
Unstratified, the threshold test looked decisive — case rate for `dv/dt` below T vs at/above T,
**all 17 routes**, paired within route:
```
   T = -1.0  8.33 % vs 4.86 %  = 1.72x  CI [1.26, 2.21]      T = -0.4  1.67x  CI [1.23, 2.21]
   T = -0.8  7.83 % vs 4.79 %  = 1.63x  CI [1.16, 2.20]      T = -0.2  1.73x  CI [1.29, 2.26]
   bins: < -1.0 -> 8.33 %   -0.2..+0.2 -> 4.85 %   > +0.2 -> 4.03 %
```
**Every CI excluded 1.0.** 🛑 **Then I stratified on speed × angle, and it largely dissolves:**
```
   stratum                        decel    accel    ratio    CI              routes
   0-25 km/h   ang > 10 deg      30.22 %  21.69 %   1.39x   [0.94, 2.33]      10
   25-50 km/h  ang > 10 deg      18.20 %  14.43 %   1.26x   [0.71, 1.92]      12
   50-80 km/h  ang < 10 deg       2.13 %   0.52 %   4.12x   [1.44, 19.00]     15   <-- only cell that resolves
   80-200 km/h ang < 10 deg       2.12 %   3.29 %   0.64x   [0.00, 12.27]      9   <-- reverses
```
🛑 **The only cell whose CI excludes 1.0 is LOW-ANGLE at 50-80 km/h — which is NOT the peak-turn
regime.** Both high-angle cells, where the operator's symptom lives, **span 1.0**.
⚠ And decelerating windows are **slower**, not faster (median 40.0 vs 48.3 km/h), so the
unstratified 1.7× was partly **composition**, not effect.
⇒ **DOWNGRADED before it was ever claimed: [BELIEF, direction consistent in 5 of 6 strata, NOT
established in the regime that matters].** ⊕ Not refuted either — the direction holds nearly
everywhere and the high-angle cells are simply underpowered (10-12 routes, wide CIs).
✅ **What would settle it: more high-angle exposure**, which is the same gap the drive card already
names. 🛑 **Do not build against this.** ⚠ Two cells report absurd upper CIs (36,631,016) — a
degenerate bootstrap where the denominator approaches zero; **read those cells as uninformative, not
as huge effects.**

## ⚠ A CANDIDATE TRIGGER — **DECELERATING INTO THE TURN.** Suggestive (12/17), NOT established
First use of the operator's **labelled** event as a CASE rather than a description. r23,
t = 445.6-448.2 (his *"exact instance"*), against controls from the **same drive** matched on speed
and |angle| ⇒ route variance cannot apply.
```
   in the 2 s BEFORE      event      control median (n=6)   percentile
   speed                  43.6 km/h        25.4               100th
   d(speed)/dt           -1.159 m/s^2     +0.619                0th
   18-22 Hz rms          14.162            9.739               83rd
   |driver torque| mean 645.1           1113.7                 33rd
```
⭐ Two channels at opposite extremes, and they are **one physical fact: BRAKING INTO A CORNER AT
SPEED** — which matches the operator's own words, *"a fixed oscillation during the peak of a hard
curve."* 🛑 At n=6 that is p ≈ 0.14 — a hypothesis, not a finding.
**Tested corpus-wide** (cases = top 5 % by 6-9 Hz per route, controls matched on speed and |angle|
**within the same route**, bootstrap unit = ROUTE):
```
   12 of 17 routes have cases decelerating MORE than their matched controls
   median difference -0.1720 m/s^2   route-bootstrap CI [-0.2486, +0.0354]
   Wilcoxon signed-rank p = 0.1889    (sign test alone: p ~ 0.07)
```
🛑 **NOT ESTABLISHED** — the CI spans 0. ⭐ **But the direction is consistent (12/17) and this is the
first candidate TRIGGER the kit has had**, as opposed to a gain or a lane.
⚠ **The operator's own event is 6.7× more extreme than the corpus effect** (-1.159 vs -0.172) ⇒
**either his labelled instance is atypical, or deceleration matters only past a threshold** — a
threshold model would not show up in a linear mean comparison. **That is the next test, and it needs
no new data.**
✅ If it holds, it is actionable in a way no previous finding has been: a trigger can be **avoided or
anticipated**, and it points at longitudinal load transfer rather than at a firmware gain.
Tools: `rlog-tools/studies/peakturn/labelled_event_case_control.py`,
`rlog-tools/studies/peakturn/deceleration_precursor_test.py`.

## ⚠ THE DAMPER'S COST IN ACCELERATION — measured, NOT resolved, but the SHAPE is informative
The engaged friction row went **×1.5 (V91..V104) → ×3.0 (V107..V121)**, a natural experiment on the
operator's own complaint. Outcome = **p99 |d(rate)/dt| engaged vs manual within the same drive**
(exposure cancels). Only 4 routes carry ≥3,000 frames in *both* arms:
```
   dose    n   median eng/man acc ratio   median engaged rate p99
   1.5x    2          3.051                     66.2 deg/s
   3.0x    2          1.689                     77.1 deg/s
   x3.0 / x1.5 = 0.554   route-bootstrap CI [0.350, 1.039]
```
🛑 **NOT RESOLVED** — CI spans 1.0 and **n = 2 per arm is below this kit's own stated minimum.**
⭐ **But the shape cuts against the simple story: engaged RATE p99 went UP (66.2 → 77.1 deg/s).**
⇒ if the damper costs anything it is **acceleration headroom, not top steering velocity.** The
operator reports both as low; **the velocity half is not visible in the data.**
⇒ **[BELIEF, ~0.55× point estimate, unresolved]** — do not quote as a measured cost. It resolves by
**instrumenting the next build**, not by re-flying a historical dose.

### ⇒ WHERE THE OSCILLATION WORK STANDS, CONSOLIDATED
| lever | status |
|---|---|
| **relay knee** (V121 `0xC40BC` 3000 / `0xC40D2` 1020) | **BUILT, 40/40.** Gain held exactly at V112's ⇒ bit-identical ≤31.8 deg/s, more assist above. Harmonic rationale **weakened**; effect **UNKNOWN**. **The recommended flight.** |
| **engaged friction row** (the 6-9 Hz damper) | **DO NOT CUT** — V94 cut it 6× and the drive was aborted; delivered +137° vs wheel rate ⇒ real damper. Only **1.11× headroom** at `Y[0]` before int16 overflow. |
| **Lever B** | **already on the car** (V104..V121) — best measured grind-#1 fix. |
| **Lever A** (V62 `sar`×2) | absent from all 25 builds, **correctly** — its r24 half caused grind #2. |
| rate-scheduled `Kd` · FactorD · table (b) · `0xC64DE` · arbitration restore · base-assist damper | **closed** — each on its own control or arithmetic. |
| **grind #1** | **unmeasurable on the current corpus** — no creep exposure since V107. |
🛑 **Two gating measurements, neither needing a build:** (1) **one stock-configuration drive** takes
the angle-gating result from p = 0.100 to p = 0.018; (2) **a creep-inclusive drive OR operator
timestamps** makes grind #1 measurable at all.

## 🛑🛑 THE ADDED LKAS "MASS" **IS** THE DAMPER THAT WORKS — a build proposal stopped one step short
I had assembled: the engaged friction row is the only engaged asymmetry · it scales `gp-0x6b26` ·
`gp-0x6c2c` is **acceleration**, pinned in assembly ⇒ `−K·α` is **apparent inertia** ⇒ *"we add 3×
engaged-only steering mass, exactly what the operator forbade, and it explains his low-acceleration
complaint."* **Every link individually correct.**
🛑 **V94 flew that argument verbatim** (*"it is apparent inertia, nothing is dissipated, lowering is
strictly safe"*), cut the cell **6×**, and on route `7d` **the operator ABORTED**:
> *"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car,
> and I decided it was not safe to drive."*
Measured after: motor acceleration **3-7× up above 9 Hz**; column-torque↔wheel-rate coherence at
18-31 Hz **the highest of any drive in the corpus**. Then, two drives, ω-partialled, shuffled control:
```
   delivered phase vs WHEEL rate, 6-9 Hz:  +137 deg / +139 deg   =>  +518 / +565 counts POSITIVE Re(Z)
   => a REAL 6-9 Hz DAMPER.  V94 removed 6/6ths of it.  First measured d(symptom)/dK: sign UP.
```
✅ **Reconciliation, both notes stand:** [[accord-gp6b26-is-inertia-not-damping]] is right
**structurally** (built from an acceleration), but **structure is not delivered effect in a loop with
filters** — delivered, it is +137° against wheel rate, i.e. dissipative.
🛑🛑 **⇒ THE OPERATOR'S TWO GOALS ARE IN MEASURED OPPOSITION ON THIS LEVER.** The apparent mass he
feels under LKAS **is** the damper holding the oscillation down; V107's 3.0× (**90 % of the int16
ceiling 3.3335**) is a large part of why V112 is his best build. **Cutting it to buy acceleration is
REFUTED ON THE ROAD**, and "more damper" has only **1.11× headroom at Y[0]** before overflow.
✅ **Any acceleration gain must come from a DIFFERENT lever.** ⊕ This is the value of the standing
rule *check the build lineage before proposing a cal lever* — it stopped a rebuild of the worst drive
in the record.

## ✅ THE FRICTION-ROW FLAG IS **RETRACTED** — no defect on the car; the kit had already shown why
I flagged that V107..V121's engaged friction row at **3.00×** sits past a stated *"int32 wraparound at
1.6005×"*. **Verified. Wrong on three counts:**
1. 🛑 **Wrong clamp cited.** `FUN_00034350` reads FactorB/C/D/E + ceiling and clamps *their*
   product to `|gp-0x6bd0| <= 1024`; **it never reads `0xCBE74`.** The friction row's consumer is
   **`FUN_00036c12`** → `gp-0x6b26`, clamped at ±`0xC407E` = **±511**.
2. 🛑 **I scaled a MAX, not a distribution** (319.1 × 3.0 = 957). `build_v107_tva.py` has a
   section **"THE TERM IS NOT SATURATING"** with reconstructed duty on r a6's engaged distribution,
   **held-out validated on r78**:
```
      engaged all   n=123802   p50 15.1   p99 268.5   duty>=511 = 0.00121
```
   ⇒ **p99 268.5 vs a 511 clamp, duty 0.12 % — NOT a relay.**
3. ✅ **The governing bound is the int16 floor**: `Y` is signed int16, `Y[0]` stock -9830 ⇒
   **k_max = 32768/9830 = 3.3335**, and 3.00× = **90.00 % of it, chosen deliberately** (×4/×5/×6 are
   overflow). The "90.0 %" column is **percent of the int16 floor**, not clamp duty.
⇒ The **1.6005×** figure in [[accord-six-levers-closed-on-arithmetic]] does **not** describe this
row's headroom; those two records need reconciling, but **V107..V121 are inside the real bound.**
✅ **The V107 step is deliberate design**: a reshape at constant `Y[0]` (so *"creep-speed clamp duty
and the relay index are UNCHANGED BY CONSTRUCTION"*), raising only high-speed knots because Honda's
taper made the dose **4.2× weaker at highway**; V108 then reverted `Y[1]` (`GP6B26.Y1REVERT`).
🛑 **My "the shape change was never analysed" claim is withdrawn too** — V107's builder analyses
exactly that, with a four-speed delivered-coefficient table and an int16-headroom column.
⇒ **NET: the only engaged-vs-manual asymmetry is still this row (that stands), but it is not
saturating, not wrapping, and not a hidden relay. No defect in the flight build.**

## ⭐⭐ THE **ONLY** ENGAGED ASYMMETRY LEFT IS THE FRICTION ROW — and 3.0× sits past a stated wrap point
Dereferenced all fourteen mode-indexed families at `arr + mode*4`. On V112 and V121 exactly **one**
differs between mode 24 (manual) and mode 26 (engaged): **`0xCBE74` friction**. FactorB/C/D/E,
ceiling, the four r24 `gain_B` arrays, boost curve/amp/ceiling — **all byte-stock and symmetric**.
✅ **The V74-V81 engaged-only FactorC/E damper is GONE** (V90+ byte-stock, `Y[0]=0`, Honda's ramp) ⇒
[[accord-v80-damper-relay-and-grind1-inert]]'s *"restore the RAMP"* **is already satisfied — no build
needed.**
```
   build         m24 (MANUAL)           m26 (ENGAGED)              ratio
   STOCK, V90    [-9830,-5734,-1966]    [-9830,-5734,-1966]         1.00
   V91..V104     same                   [-14745,-8601,-2949]        1.50  uniform
   V107..V121    same                   [-29490,-17202,-16000]      3.00  NOT uniform
                                         Y[0] 3.00x Y[1] 3.00x Y[2] 8.14x
```
🛑 Stock's |Y| **decays 5.0×** across the axis; ours decays only **1.84×** — we tripled it **and
flattened it**. **All prior analysis of this cell was of UNIFORM scaling**; a shape change alters the
slope d|f|/dx, a different quantity, and nothing in the record addresses it.
🛑 **FLAG ON THE BUILD ON THE CAR:** [[accord-six-levers-closed-on-arithmetic]] closed this lever
partly on **"int32 wraparound at 1.6005×"** — **V107..V121 carry 3.00×.** ⚠ I have **not verified**
that claim, and two things argue against catastrophe: -29490 fits `i16`, and the evaluator's output is
**hard-clamped** to `|gp-0x6bd0| <= 1024` ([[accord-damper-evaluator-fun34350-ceiling-clamp]]) so an
oversized input should **saturate, not wrap**; V107-V112 flew fault-free. 🛑 **"Should saturate" is a
belief, not a check.** ⇒ **OPEN, highest-value verification available: does the 3.0× row overflow
anywhere between the LERP and the clamp? Pure arithmetic on a decompile — no drive, no flash.**
⚠ **NOT a build proposal**: the ×1.5 dose **measured INERT** over two flights (a candidate **T10**,
not falsified — V94's 6× cut made the operator abort, so the cell reaches the car), and delivered
damping was judged **5-69× below the resolvability floor**.

## 🛑 V121's HARMONIC RATIONALE IS **WEAKENED** — the one quantitative check does not support it
I tried to make V121 prospective, as the saturation-duty model was for V112. The relay is memoryless,
so I fed the measured V112 rate through `clamp(rate·4.7121·12/knee, ±1)` at each knee:
```
   knee     600     1800     2400     3000     4000     8000
   ratio   0.951   1.365    1.248    1.493    1.832    1.278
   knee 3000 predicted factor 1.094x  CI [0.755, 1.335]   <- slightly WORSE, not better
```
🛑 Non-monotone, and it **contradicts the cross-build trend** the mechanism rests on (wire: 600 →
1.412, 1800 → 1.213; simulation puts 600 BELOW 1800).
⚠ **The simulation is INVALID as a prediction** — the measured rate **already contains the effect of
the relay that was running**, and **a memoryless nonlinearity in a CLOSED LOOP cannot be simulated by
post-processing the loop's own output.** ⇒ it cannot confirm the mechanism. 🛑 **But it cannot be
waved away**: reproducing the trend would have been weak support, and it **fails to**. Net,
**confidence in the harmonic mechanism goes DOWN.**
⇒ **V121 is NOT withdrawn, but its case now rests on grounds independent of harmonics:** gain held
EXACTLY at V112's (bit-identical ≤ 31.8 deg/s ⇒ near-zero regression risk); **more assist above
31.8 deg/s**, serving the operator's constraint directly; `knee` has the best on-car track record of
any lever here (600→1800 coincided with the best-ever build, though confounded); cal-only, 4 bytes,
40/40.
⚠ **V116 is the conservative version of the same move** (K1 0.797 of |model| vs V121's 0.996, just
under the sign-inversion ceiling). **If the weakened mechanism argues for a smaller step, fly V116.**
🛑 **Plainly: V121 is a well-constructed build whose effect on the oscillation is UNKNOWN.**

## 🛑🛑 GRIND #1 IS **UNMEASURABLE** ON THE RECENT ROUTES — there is no creep exposure
I validated a grind-#1 pipeline against a known effect — V101/V102/V103 accidentally dropped Lever B,
and the pipeline recovered it at **OFF/ON = 2.32× [1.62, 2.94]** against the on-car **0.40
[0.27,0.58]** (≈2.5×). **The control PASSED.** Then the hunt gave four predictors at p < 0.10 and an
ordering the operator flatly contradicts:
```
   r1e V107 2.92 (best on my stat) · r21 V111 5.10 · r22 V112 7.33 · r23 V112 7.93 (worst)
   operator: V112 is "the best firmware ever... Grind #1 is now rare."
```
✅ **Cause found.** Grind #1 was characterised at **creep** — operator on V62: *"Original grinding at
**2-5 mph** is gone!"* Engaged windows in that band:
```
   r77 (V90) 39 · r85 11 · r9e 11 · ra5 11 · r1e 11 ·  r21 (V111) 0 · r22 (V112) 0 · r23 (V112) 0
```
⇒ **the all-speed statistic measured road-speed 18-22 Hz on V111/V112, NOT creep grind #1.** The four
"hits" are one collinear old-vs-new contrast — **do not act on them.**
🛑 **This weakens [[accord-knee-has-no-measured-dose-response-on-grind1]]**: it pooled all speeds
too, so that null is about **road-speed 18-22 Hz, not creep grind #1**. Its conclusion (V121 does not
fix grind #1) stands, but because **grind #1 was never measured**, not because a dose-response failed.
✅ **WHAT UNBLOCKS IT — no firmware change:** (1) **a drive with real engaged 2-5 mph creep**, which no
post-V107 route has; or (2) **operator timestamps** — he said *"I no longer have an understanding of
the kinds of scenarios that elicit grind #1"*, so **a mark at the moment it happens** converts an
unmeasurable symptom into a locatable one, exactly as the route-23 timestamp did for the oscillation.
⇒ **SECOND GATING MEASUREMENT ITEM**, alongside `docs/scoring/DRIVE-CARD-manual-at-speed.md`.

## ✅ LEVER B **IS** ON THE CAR — an alarm of mine, corrected; grind #1 needs something NEW
Byte scan, 25 built images + stock:
```
   build           0x3AA96      0xC6446     LEVER B?  |  0x3AB76 0x3AC20  LEVER A?
   STOCK           C5 stock     512 stock     no      |    AA      AA       no
   V90..V100       FB LKAS gate 5244 ARMED    YES     |    AA      AA       no
   V101,V102,V103  C5 stock     512 stock     NO   <-- a real gap, closed at V104
   V104..V121      FB LKAS gate 5244 ARMED    YES     |    AA      AA       no
   LEVER B: 22 of 25        LEVER A: 0 of 25
```
✅ **V112 (ON THE CAR) and V121 both carry Lever B** — grind #1 **0.40 [0.27, 0.58]**, *best in the
kit*, **and** creep grind #2 → **0 bursts**, mode-proof.
🛑 I raised an alarm from [[accord-v81-carries-neither-grind1-fix]] that the fix had been silently
lost. **Wrong — that memory is specific to V81.** Lever B was restored at V88 and is continuous since.
✅ **Lever A is absent, and correctly so**: its r24 half raised 40-49 Hz **×11.7 and CAUSED grind #2**,
while Lever B is equal-or-better on grind #1 *and* fixes grind #2. **Do not restore Lever A whole.**
⚠ Its **r26 half alone** (`0x3AB76` `AA`→`A9`, ONE byte) has never flown in isolation and did not
cause grind #2 — but [[accord-r26-is-structurally-inert]] leans inert (leg 2 BELIEF) ⇒ **likely a
no-op; NOT proposed on this evidence.**
🛑 ⇒ **THE REMAINING GRIND #1 IS NOT A LOST FIX.** The best measured fix is deployed and the symptom
persists ⇒ **it needs a NEW lever.** ⊕ Not the relay knee
([[accord-knee-has-no-measured-dose-response-on-grind1]]), ⊕ not the base-assist damper
([[accord-v80-damper-relay-and-grind1-inert]], inert across k = 0.58 → 4.16).

## 🛑 THE KNEE HAS **NO MEASURED** DOSE-RESPONSE ON GRIND #1 — an upgrade withdrawn before it was made
I was about to strengthen V121's claim on grind #1 using the operator's own dose-response (constant
→ *"rare… a few moments"* exactly when knee went 600→1800). **Tested it first; it does not
reproduce.** 17 routes, band power as a SHARE of each window's own 1-40 Hz power:
```
   knee   n_routes   18-22 Hz    26-31 Hz    6-9 Hz
    300       8        0.0718      0.0658     0.0427
    600       7        0.0930      0.0616     0.0659
   1800       2        0.0924      0.0532     0.0663
     18-22  rho +0.356 p 0.161   |   26-31  rho -0.158 p 0.546
```
🛑 **18-22 Hz goes the WRONG WAY**; 26-31 Hz is flat. ⇒ **V121's claim on grind #1 stays as
written — it does NOT address it.**
⚠ Not a refutation of the operator's report, for two reasons: **n = 2 routes at knee 1800**; and
🛑 **band SHARE is not severity** — it is normalised by broadband power, so a change that lowers
broadband more than the band **raises the share while the absolute level falls**. The 6-9 Hz
reference row shows the hazard: it *rises* with knee on share (rho +0.477), opposite to the harmonic
and on-road results. **The right statistic is absolute band level with exposure controlled, and this
corpus cannot deliver it at n=2. OPEN.**
⇒ V121 stands on the **harmonic** result alone (itself BELIEF). The operator's grind-#1
dose-response is also **confounded** — V112 moved `knee` **and** `K1` together — but remains the best
on-car signal the kit has for grind #1.

## 🛑 A FABRICATED "MEASURED" VALUE IN V121'S PROVENANCE — caught, removed, asserted against
Deriving `build_v121_tva.py` I wrote `MEASURED_DUTY = {..., 2400: 0.0484, 3000: 0.0370, 3600: 0.0000}`.
**`0.0370` was invented** by eye from the neighbouring rungs, inside a dict printed as
*"MEASURED relay saturation duty"* and asserted against. **The payload never depended on it — the
image SHA `ce565da7…` is unchanged** — but the provenance is what a future session trusts.
🛑 **Recomputing the ladder properly ALSO failed.** On the published gate (route 21, 5-10 mph,
engaged, hands-off, `|cmd| >= 2048`) my reconstruction gave **n = 572 vs the published 289**, and the
duties missed badly (`cs_rate` 0.9178/0.4493/0.1171/0.0087 vs 0.7439/0.4810/0.2353/0.0484).
⇒ **The ladder's exact gate is NOT recoverable from the r21 cache alone. OPEN.** Anyone extending it
must first reproduce the five published rungs; if they cannot, they must not add a sixth.
✅ **Fixed structurally**, not by resolving to be careful — the builder now asserts
`KNEE_NEW not in MEASURED_DUTY` and `2400 < KNEE_NEW < 3600`, so it **fails** if anyone adds an
unmeasured rung, and states its position as **bracketed by 0.0484 and 0.0000** rather than claiming a
value. **40/40 assertions; image unchanged.**
⇒ [[feedback-never-extend-a-measured-ladder-by-eye]]

## ✅ **V121 BUILT — THE MAXIMAL GAIN-MATCHED KNEE.** `0xC40BC` 1800→3000, `0xC40D2` 612→1020
```
image  ce565da74ad93f77c81a3e2572758d5c2df505f6d32889b65c5536904ea7596c
.rwd   8c154edb69ae4649ba55ac4760ae55aec56bd5be2b336e0d8f1e4a46b33512c9
38/38 assertions · 50/50 CRC blocks · 4 payload bytes · cal-only, NO cave · alpha2 HELD at 14
```
**A HARD SAFETY CEILING SETS THE DOSE.** `friction = |model|·(K1/1024)·clamp(·1)`, so `K1/1024` is the
friction's maximum as a **fraction of |model|**; at `K1 >= 1024` friction can exceed `|model|` and the
**residual INVERTS SIGN**. No build in the kit's history has run `K1 >= 1024`.
```
   build   knee    K1    gain        saturates   K1/1024   frames saturated
   stock    600   204   0.0039844    10.6 deg/s   0.199        19.165 %
   V112     1800   612   0.0039844    31.8         0.598         6.748 %   <- ON THE CAR
   V116     2400   816   0.0039844    42.4         0.797         4.713 %   <- still clipped at 47.06
   V121     3000  1020   0.0039844    53.1         0.996         3.697 %   <- CLEARS it
   (knee 4000 needs K1 1360 = 1.328 of |model| ⇒ REFUSED, residual inverts)
```
🛑 **V116 is a HALF-STEP**: oscillating windows have median p95 |rate| = **47.06 deg/s**, so
V116's relay is **still a signum exactly where the symptom lives.** V121 is the first gain-matched
step that clears it while staying same-signed.
✅ **Feel: bit-identical to V112 at and below 31.8 deg/s** (ratio 1.000 at 10 and 30 deg/s), then
**1.571× the friction at 50 and 1.667× at 100+** — and **more modelled friction = MORE assist**
([[accord-friction-polarity-more-assist]]) ⇒ it adds **no** drag where the LKAS command lives and
**increases** authority at high steering rate. That is the operator's constraint moved the right way.
⊕ Second, independent rationale for the knee: the 7-9 Hz mode radiates **real harmonics**
([[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]]) ⇒ a hard nonlinearity in its
excitation path; **knee is the relay's SHAPE** and the harmonic ratio is monotone in it
([[accord-knee-is-the-relay-shape-variable-k1-is-only-gain]]). V116's header said the knee *"does
NOT fix the peak-turn oscillation"* — written before that result, and **now too strong.**
🛑 **The mechanism is BELIEF, not EVIDENCE** (ρ −0.291, p 0.257). V121 is the **best-motivated
flight, not a guaranteed fix.** ⚠ `FUN_0003b8f6` is not LKAS-gated ⇒ **manual feel changes above
31.8 deg/s**, the same trade V112 made. ⚠ It does **not** address grind #1 — a separate mechanism.
✅ **FALSIFIER:** V121 should push the harmonic ratio below V112's **1.213** and be no worse on
assist. If the ratio does not move, the relay is not the excitation path.
⇒ **RECOMMENDED FLIGHT ORDER: V121 → (V116 only if V121's dose proves too large).** V120 is
withdrawn — it cuts assist and, being pure gain, cannot touch the harmonics.
⚠ Builder bug caught and fixed: the image first emitted under a `_v116_` prefix. Corrected to
`_v121_`; V116's own image was never overwritten. Builder:
`analysis-2020accord/builds/v108_plus/build_v121_tva.py`.

## ⭐⭐ `KNEE` IS THE RELAY'S SHAPE, `K1` IS ONLY GAIN ⇒ **THE RECOMMENDATION CHANGES TO V116**
🛑 My first dose-response test was **mis-constructed**: it used `fric_gain = (K1/1024)(12/knee)`,
but `K1` multiplies **after** the relay (pure gain) while `knee` sets where the clamp bites (the
**shape**) — and **a signum's harmonic ratio is scale-invariant**, so `K1` cannot move it by
construction. Re-tested on `knee` alone:
```
   knee   n_routes   median harmonic ratio     relay character
    300       8           1.743                hardest signum
    600       7           1.412                stock
   1800       2           1.213                softest        <- V112, the best build on-road
   Spearman = -0.291  p = 0.257   knee300/knee1800 = 1.437 CI [0.925, 2.258]
```
✅ Monotone across all three levels, direction as predicted. 🛑 **NOT significant** — CIs include
1.0. **[BELIEF, suggestive; a monotone ordering of 3 groups is ~1/6 by chance.]**
```
              knee    K1     small-signal gain   saturates at   assist change
   V112 (car) 1800   612        0.0039844        knee/12 = 150       --
   V116       2400   816        0.0039844        knee/12 = 200      NONE
   V120       1800   306        0.0019922        knee/12 = 150      LESS
```
✅ **V116 raises `knee` and `K1` together by 1.333× ⇒ small-signal gain EXACTLY V112's, relay
saturates 1.333× later** = *make the relay more linear without changing the assist.*
🛑 **V120 does the opposite of the operator's ask**: halving `K1` halves modelled friction, and
[[accord-friction-polarity-more-assist]] gives **more friction = MORE assist** ⇒ V120 **reduces
assist**; and being pure gain it cannot touch the harmonics on this mechanism.
⇒ **V116 SUPERSEDES V120 as the recommended flight** — already built, 38/38, cal-only.
⊕ Clean falsifier: V116 should drop the harmonic ratio below V112's 1.213 **and** be no worse on
assist. memory: [[accord-knee-is-the-relay-shape-variable-k1-is-only-gain]]

## ⭐⭐ THE 7-9 Hz MODE IS NONLINEARLY EXCITED — and that RESOLVES BOTH open contradictions
17 routes, 3,986 windows, NW=512. Peak prominence at `2f0`/`3f0` vs off-multiple controls, then
against the control that matters — **non-oscillating windows**:
```
   OSCILLATING      1.308        NON-OSCILLATING  1.061
   OSC / NON-OSC =  1.233    ROUTE-level bootstrap 95 % CI [1.060, 1.503]
   f0 = 7.81 Hz  ->  2f0 = 15.62 Hz   3f0 = 23.44 Hz
```
✅ **Harmonics are REAL** — CI excludes 1.0 with the DRIVE as the unit ⇒ the excitation path
contains a hard nonlinearity.
✅ **CONTRADICTION 1 RESOLVED — the symptoms stay TWO.** 2f0 and 3f0 land at 15.62 / 23.44 Hz;
**neither is in 18-22 or 26-31.** The 0.2-pp rate co-location is **shared exposure, not shared
mechanism** ⇒ [[accord-two-symptoms-two-mechanisms-rez-spectrum]] **wins**.
🛑 **⇒ Fixing the 7-9 Hz oscillation will NOT fix grind #1. Budget for two fixes.**
✅ **CONTRADICTION 2 RESOLVED — resonance AND nonlinearity are both true.**
[[accord-ratchet-is-a-lightly-damped-resonance]] excluded a limit cycle on a ring-down; harmonics
normally imply one. No conflict: **a linear resonance driven THROUGH a nonlinear element** gives a
clean ring-down when the drive stops *and* harmonics while driven. Both records stand as written.
⭐ **Points at the Coulomb relay** — `fVar13 = clamp(POL·gp-0x6abc·12/knee, ±1)` is a **signum**, the
textbook harmonic generator, and [[accord-engagement-amplifies-6-9hz]] already measured engagement
multiplying this band **2.8×** through it.
✅ **⇒ V120 (`0xC40D2` 612→306) now has a measured mechanism, not just reasoning.**
🛑 [BELIEF, one converging line] — nothing shows the relay is *the* path rather than *a*
nonlinearity, and [[accord-cbe74-dose-measured-inert-wrong-mode-record]] warns a relay dose can
measure inert.

## ⭐⭐ THE 18-22 Hz GRIND IS RATE-COLOCATED WITH THE OSCILLATION — a constraint on the whole search
🛑 **Correction to my own framing first.** I reported *"rate AUC 0.630 ⇒ weak, parked."* The number
is right, the framing was incomplete: 0.630 was against **hard curves** (n=106). Against **ordinary
driving** (n=4,920) rate gives **AUC 0.978** (median 47.06 vs 4.33 deg/s, **10.86×**), beating angle's
0.713. ⇒ rate separates the oscillation from ordinary driving almost perfectly; what it cannot do is
separate it from a **hard curve** — and the operator's words are *"a fixed oscillation during the peak
of a hard curve."* **The symptom IS that regime**, so the tension is structural, not a measurement
failure.
**Band power above a rate knot T, 8,200 engaged windows / 17 routes:**
```
   band                     T=20     T=40     T=60    T=100    T=140
   6-9 Hz   (oscillation)   82.7 %   59.3 %   26.2 %   15.8 %   12.2 %
   18-22 Hz (grind)         94.1 %   59.5 %   23.9 %   14.6 %   11.0 %
   26-31 Hz (grind)         92.7 %   64.4 %    2.6 %    1.1 %    0.7 %
   selectivity vs 18-22:  1.10x @T=60      vs 26-31:  10.15x @T=60
```
Archive: **D PUMPS 2-12 Hz, DAMPS 16-35 Hz** ⇒ a flat `Kd` cut needs selectivity **>2.82×** (18-22)
and **>4.36×** (26-31) to beat its own trade.
✅ **26-31 Hz cost SOLVED by scheduling** (10-17× ≫ 4.36×). 🛑 **18-22 Hz cost NOT** (1.10× vs
2.82× needed) — it sits in the **same rate regime** as the oscillation, 59.5 % vs 59.3 %.
⇒ **`Kd` stays REFUSED**, now ~2.6× against instead of 3-4×. **Not a build.**
⇒ ⭐ **GENERAL CONSTRAINT: no rate-scheduled lever can touch the 7-9 Hz oscillation without equally
touching the 18-22 Hz grind** — helping one and hurting the other in the same windows.
⊕ Raises, but does **not** establish, that the two are one mechanism; co-location is necessary, not
sufficient, and [[accord-two-symptoms-two-mechanisms-rez-spectrum]] separates them on `Re(Z)`.
**Those two records are NOT yet reconciled.**

## 🛑 …AND ITS CRUX TEST FAILED — the rate axis does NOT separate the symptom
Pre-registered above: *if `gp-0x6ac0` during the 7-9 Hz event overlaps a normal hard curve, the lever
fails.* **It ran. They overlap.** Proxy `|cs_rate|` p95, 8,200 engaged windows, 17 routes:
```
   OSCILLATING (6-9 Hz top 5 %)     n = 410   median 47.06 deg/s
   NORMAL HARD CURVE (ang>=20)      n = 106   median 24.49 deg/s
   knot T:   20 -> 83.4 % osc / 61.3 % normal    40 -> 60.2 % / 36.8 %
             60 -> 22.4 % / 27.4 %  (INVERTS)   200 -> 5.6 % / 2.8 %
   AUC = 0.630  (0.5 = none)   p = 1.9e-05
```
🛑 Every useful threshold also catches **a third to a half of normal hard curves** ⇒ **a
rate-scheduled `Kd` knot cannot spare normal steering**, the exact cost the operator forbade.
⚠ **Weak, not zero**: a LERP is smooth, medians separate **1.9×** highly significantly ⇒ a gradual
rolloff gives ~1.9× more reduction during oscillation. Modest, not clean.
⚠ The proxy may **understate** separation — the real axis is the **motor** rate and the motor sees
the oscillation more strongly than the wheel. **Resolving that needs a cave probe = the only
bricking class**, so it is not cheap.
⇒ **PARKED, not struck.** The **structure** (Honda rate-schedules the PID; `Kd` flat and virgin,
byte-identical stock vs V112) **stands as EVIDENCE**; the **discriminability** claim does not.
**Do not build it on the structure alone.**

## ⭐⭐ A FREQUENCY-SELECTIVE LEVER **DOES** EXIST — Honda rate-schedules the PID, and `Kd` is FLAT
Decompiled `FUN_0003a382`, then byte-verified: all three PID gains are four-knot LERPs on the **same
axis**, `gp-0x6ac0` (resolver/FOC electrical rate [BELIEF, kit record]):
```
  Kp 0xC6B26  X = [0, 300, 2000, 4000]   Y = [256, 256, 225, 153]   <-- NOT FLAT: Honda rolls off 40 %
  Ki 0xC6B12  X = [0, 400, 1500, 3000]   Y = [ 98,  98,  98,  98]       flat
  Kd 0xC6AE6  X = [50, 400, 1500, 3000]  Y = [2048,2048,2048,2048]      flat
  lane gate: disabled when gp-0x6ac0 >= 0x32C9 = 13001
```
✅ All three Y rows **byte-identical stock vs V112** — virgin across the entire build history.
✅ **Honda's own Kp row proves the machinery is live, wired and calibrated** — nothing to arm.
🛑 ⇒ **[[accord-factord-is-the-angle-error-lever]]'s "this firmware has NO frequency-selective
lever" is TOO STRONG and should be read as scoped to FactorD.**
⊕ `STATE-ARCHIVE-2026-08-11`: **D PUMPS ONLY 2-12 Hz and DAMPS 16-35 Hz** ⇒ Kd is an anti-damping
contributor **at exactly the symptom band**. A **rate-scheduled** rolloff — Kd unchanged at low rate,
reduced at the top knots, shaped the way Honda shapes Kp — costs no steering velocity or acceleration
where the LKAS command lives. That is the operator's constraint, satisfied by construction.
🛑 **NOT YET A BUILD. The crux is knot placement**, and it is unmeasured: nothing shows what
`gp-0x6ac0` reads during the 7-9 Hz event vs during a normal hard curve. **If those overlap, the
lever cannot separate them and the idea fails.** ✅ Measurable from existing telemetry — do that next.
⚠ Also: it changes **manual** steering (`gp-0x67fa & 0xc30`, not an LKAS flag); GATE 2 applies; and
the kit's earlier **refusal** of Kp/Ki/Kd was about *flat* scaling, which does not transfer.
✅ Cal-only, one Y row, no cave ⇒ outside the only bricking class.
Tool: `analysis-2020accord/verify/read_pid_rate_schedule.py` ·
memory: [[accord-pid-gains-are-rate-scheduled-and-kd-is-flat]]

## ✅ THE DELETION-SET HYPOTHESIS IS NOW PROVEN — and `0xC64DE` is struck
**16-route natural experiment**, 15 builds, using the route-offset-immune within-drive statistic.
Outcome = log(large-angle 6-9 Hz p90) with log(small-angle p90) regressed out (r = 0.645).
```
   predictor      levels   rho      p        predictor      levels   rho      p
   knee 0xC40BC      3    -0.158  0.546      biq  0xC649B      2    -0.072  0.783
   K1   0xC40D2      3    +0.280  0.276      fric_gain        3    +0.297  0.247
   a2   0xC40DC      2    +0.094  0.718      clamp 0xC407E    1   CONSTANT - untestable
   gain 0xC6CD0      4    -0.206  0.429      kd    0xC6AE6    1   CONSTANT - untestable
```
🛑 **NOTHING that has ever varied explains the excess** (|rho| < 0.30, p > 0.24) across knee
300-1800, K1 102-612, gain 3564-65535, biquad off/on. ⇒ **the cause is the shared SET of deleted
Honda limiters**, exactly as [[accord-the-mod-works-by-deleting-hondas-limiters]] predicted — that
note's "a reframe, not a proof" is now **proven**.
✅ The invariant set is byte-exact: `0x454FE` (governor call deleted) · `0xC61C0` (1600/896/1280 →
65535×3) · `0xC64B4` · `0xC62EA` (320→0) · `0xC674F/51/5B/5D` + the `0xC659A` f32 table (corridor
×5) · `0xC64DE`. Tool: `analysis-2020accord/verify/invariant_mod_edits_vs_stock.py`.
🛑 **`0xC64DE` IS A DEAD LEVER — do not build it.** It looked like the one non-authority member of
the set, but it is a **square-wave injector half-period whose amplitude LERP `0xC6736` is (0,0,0,0)
in stock and in every build** ⇒ structurally inert.
⇒ Every remaining member is an **authority limit**, so restoring any of them spends exactly what the
operator forbade. **The next lever must be FREQUENCY-SELECTIVE.** The dormant biquad `0x35A28`-
`0x35A50` is the only real candidate (editable 2nd-order section, armed since V103) but is tuned to
**42.3 Hz** — hence its rho = -0.072 above. ⚠ All-pole, **DC gain 8.39** ⇒ as-is it AMPLIFIES; in a
loop ⇒ GATE 2 applies. **Open question, NOT a build proposal.**

## ✅ ANGLE GATING — CONFOUND REMOVED, **9 of 9**; and ONE stock route caps p at **0.100**
Within-drive design (each route its own control ⇒ immune to route offset). Raw ratio gave STOCK
**1.46x** vs 16 mods median **2.99x**, but 3 mods fell below stock — **because the ratio's denominator
varies 10x across builds** and those 3 all had small-angle p90 > 6.
**Matched on small-angle p90** (stock ranks 3rd of 10 ⇒ exposure matched):
```
   route build   small-ang p90   LARGE-ang p90   ratio
   r97   STOCK       1.064          1.551       1.46x   <-- BELOW ALL NINE
   r22   V112        1.240          2.909       2.35x
   r23   V112        1.060          8.320       7.85x     (same firmware as r22)
   ... 7 more, large-angle 3.137 - 7.353
```
✅ **Stock's large-angle p90 is below all 9 matched mods.** The same-firmware V112 pair both sit
above stock by ≥ **1.88x**, so drive-to-drive spread does not explain it.
🛑 **Exact one-sided permutation p = 1/10 = 0.100. With ONE stock route the FLOOR is
1/(n_mod+1) — it cannot reach 0.05. The limit is the DESIGN, not the analysis.**
✅ **TWO stock routes below all nine ⇒ p = 0.0182.**
⇒ **[EVIDENCE for direction and size; NOT significant at 0.05 and cannot be, on n=1 stock drive.]**
✅ **THE GATING ITEM IS `docs/scoring/DRIVE-CARD-manual-at-speed.md` — ONE more stock-configuration
drive takes the strongest surviving finding from p=0.100 to p=0.018. No build, no flash.**
Tool: `rlog-tools/studies/peakturn/matched_denominator_angle_test.py`

## 🛑🛑 ONE ROUTE PER BUILD CANNOT RESOLVE A BAND RATIO — the K1 refutation is WITHDRAWN
`r22` and `r23` are **both V112**: identical firmware, different drives.
```
   |ang|     SAME-FIRMWARE r23/r22    95% CI          cross-build V112/V111
    0-  5           1.07x           [0.81, 1.25]            1.27x
    5- 20           0.77x           [0.55, 0.97]            0.90x
   20- 60           2.74x           [0.79, 8.87]            0.75x
```
🛑 **At 20–60° the SAME firmware varies 2.74× between drives.** A predicted 2–3× effect is below
that floor, and every cross-build ratio sits inside the same-firmware spread. My CIs were
bootstrapped over **windows**, ignoring route-level variance.
⇒ **The K1 mechanism is UNTESTED, not refuted.** The "0–5° residue" is withdrawn too.
✅ **RULE**: resample **ROUTES**, or quote the same-firmware spread beside every cross-build ratio;
a cross-build band ratio needs **≥ 2 routes per arm**, and at large angle an effect **> ~2.7×**.
⚠ [[accord-the-oscillation-excess-is-ANGLE-GATED]] **survives** — its tail effects (4.4× overall,
7.9× at 20–60°) clear the floor and it is exposure-controlled — **but it rests on ONE stock route**,
and its smaller per-band ratios (1.06–1.74×) are **not** resolved.
⇒ **V120 remains the recommended flight on REASONING, not on demonstrated mechanism.**

## 🛑🛑 THE K1 MECHANISM IS **REFUTED** — V120/V113 ARE NOT MECHANISM-BACKED FIXES
Tested on data already in hand. **V111 and V112 share a small-signal gain**, so their friction term is
identical at low rate and V112's is **1.9× at 20 °/s, 3.0× above 31.8 °/s**. If that term drove the
anti-damping, V112 must be 2–3× worse at large angle. **It is not:**
```
   |ang|     n111  n112   p90 ratio V112/V111    95% CI        verdict
    0-  5     488   424        1.27x           [1.05, 1.49]   excludes 2x
    5- 20      82   167        0.90x           [0.73, 1.22]   excludes 2x
   20- 60      25    48        0.75x           [0.48, 1.64]   excludes 2x -- V112 BETTER
   60-400      38    19        1.53x           [0.96, 4.15]   underpowered
```
⊕ At **0–5° the term is IDENTICAL and V112 is still 1.27× worse [1.05, 1.49]** — the friction term
cannot explain that at all.
✅ **STILL SOLID**: the excess IS angle-gated vs stock (exposure-controlled, confound inverted);
`|model|` rises 7–9× with angle; K1 IS ×6 on stock; the term IS in phase with rate.
🛑 **REFUTED**: the causal link from that term to the oscillation.
⇒ **V120 and V113 remain valid builds but are NOT fixes with a known mechanism.** Every earlier claim
that V113/V120 is "the targeted fix" or "evidence-backed end to end" is **WITHDRAWN**.
⚠ **Open residue**: something other than the friction term differs between V111 and V112 and shows up
even at 0–5° where their friction is identical.

## ⭐⭐⭐ V120 BUILT — **K1 612 → 306. HONDA-EQUIVALENT FEEL, HALF THE ANTI-DAMPING.**
```
builder  analysis-2020accord/builds/v108_plus/build_v120_tva.py   40/40   BASE = V112
image    a588f936e4cdfe58ece41ff4943bff532444daabc4b99a53f00c1d718950a1bb
.rwd     9d6469277a6bba995cd9d2137332d791460cc2c15f845fe00c228f13c80a67e1
0xC40D2  612 -> 306   2 payload bytes.  knee 1800, alpha2 14, cave, biquad ALL HELD.
```
🛑 **DOSE CORRECTION.** V112 raised knee ×3 AND K1 ×3, so **V111 and V112 deliver the SAME low-rate
compensation** — one number for "what he is used to". **V113's K1 = 204 is 0.333× of it, i.e. BELOW
Honda's own 0.500×** ⇒ heavier than STOCK at low rate. Not intended, not computed at the time.
```
   build      knee    K1    comp @ 3 deg/s    vs V112
   stock       600   102       0.02816         0.500   <- Honda's level
   V112       1800   612       0.05632         1.000   <- on the car
   V120       1800   306       0.02816         0.500   <- == STOCK
   V113       1800   204       0.01877         0.333   <- below stock
```
⭐ **V120 buys**: anti-damping **0.500× at every frequency** (no added inertia, no added phase);
low-rate feel **exactly Honda's**; relay **corner untouched at 31.8 °/s** so V112's 1.37–1.62×
authority win is kept; and it **self-targets** — linear in `|model|`, which rises **7–9×** with angle.
⇒ **V120 is the recommended flight; V113 is the fallback second step if 0.500× is not enough.**

## 🛑🛑⭐ K1 IS THE ANGLE-GATED ANTI-DAMPING — **V113 IS THE FIX, AND IT IS ALREADY BUILT**
Every link measured, 2026-08-28:
1. **The excess is ANGLE-GATED** — |ang| < 20° we ARE stock (1.06–1.08×); 20–60° p90 **1.74×**, max
   **16.568 vs stock's 2.111**; 60–400° p90 **3.16×**. ✅ Exposure-controlled and the confound
   **inverts**: stock drove that regime MORE (13.2 % vs 4.9 %), at higher angle and command, calmly.
2. **`|model|` RISES 7–9× WITH ANGLE** — the cave's `0x14A` byte4 **b5** is the `gp-0x6AE2` rung:
   duty **0.118→0.837** (r22) and **0.104→0.934** (r23), **monotone over four bins, two routes.**
3. `friction = EMA(|model| · K1/1024 · sat(rate·12/knee))`, **in phase with rate** (EMA adds only
   −1.1°…−11.1°) and a *compensation* ⇒ **ANTI-DAMPING**.
4. **K1 `0xC40D2` = 102 → 612 = ×6 ON STOCK** — the largest single multiplication in the live diff.
⇒ **at large angle our anti-damping is 6× stock's coefficient times a 7–9× larger `|model|`.**

```
   build    knee   K1    small-signal gain   K1 vs stock
   v112     1800   612      0.0039844          6.0x     <- ON THE CAR
   v113     1800   204      0.0013281          2.0x     <- THE FIX (already built)
   V113 vs V112 = 6 bytes / 2 runs: 0xC40D2 612->204 + the CRC trailer.  Nothing else moves.
```
⭐ **V113 = V111's K1 with V112's knee** — V111 gave *"oscillations gone, ratcheting reduced"* (at the
cost of rate) and V112's knee restored the authority (tracking **1.37–1.62×** better).
**It is the combination of the two things that each worked**, and it cuts the anti-damping term to
**0.333×** exactly where `|model|` is largest.
🛑 **I deprioritised V113 and that was wrong** — V112's flight refuted the *magnitude* of the
anti-damping risk at V112's operating point, not the mechanism.
⚠ **Cost: heavier below ~30 °/s**, manual feel included (`FUN_0003b8f6` is not LKAS-gated).
⭐⭐ **V113 CUTS THE TERM 0.333× AT EVERY RATE** — linear region and saturated plateau alike ⇒ it hits
**the anti-damping (the oscillation) AND the relay kick magnitude (grind #1)** in one 2-byte change,
while the relay **corner stays at 31.8 °/s** so V112's authority win is kept. ⭐ **Self-targeting**: the
term is linear in `|model|`, which rises **7–9×** with angle, so the absolute cut is 7–9× larger exactly
where the symptom lives. 🛑 **V113 SUPERSEDES V119 as the recommended flight** — 2 bytes vs 8, one
dynamics lever vs two, and the only one with a closed evidence chain.
🛑 **Falsifier**: if V113 flies and the large-angle oscillation is unchanged, K1 is not the
mechanism and the angle gating is plant-side. A clean single-variable read.

## ⭐⭐⭐ V119 BUILT — **BOTH LEVERS + THE PROBE.** Grind #1 AND the oscillation, one flight.
```
builder  analysis-2020accord/builds/v108_plus/build_v119_tva.py   42/42   BASE = V112
image    a39801bc621de7d6c7dd5cbb207866e70e56b43027bde3851f65d5dd717328bc
.rwd     18e3216fb6f01809bc542b82f7ffc8ec9098ade5f9037a1d4ab0c9ec05feaeba
0xC40BC  1800 -> 2400   relay knee              -> GRIND #1
0xC40D2   612 ->  816   K1, cancels the gain change EXACTLY
0xC649B     1 ->    0   disarm the biquad       -> THE OSCILLATION
0x55DF2  gp-0x6ABC -> gp-0x67FA   the 427 tap   -> THE STATE-4 DIAGNOSTIC
0x55E10  sar 3 -> sar 0
8 payload bytes.  🛑 NO CAVE EDIT.  ZERO unattributed.
```
### ⭐ WHY TWO DYNAMICS LEVERS IS STILL INTERPRETABLE HERE
The single-variable rule exists so a symptom report can be attributed. These two levers target
**two symptoms whose separation is MEASURED, not assumed** — the fine `Re(Z)` spectrum
(coherence 0.5–0.85) puts the **peak-turn oscillation at 7.42 Hz on a −81 peak** (a linear loop
instability) and **grind #1 at 18–22 Hz where `Re(Z)` is −1…−10** (neutral ⇒ a nonlinearity).
⇒ **the knee cannot fix the oscillation and the biquad cannot fix grind #1**, so *"grinding better,
oscillation unchanged"* — or the reverse — **attributes itself.**

### LEVER 1 — the relay knee, on a model that has already predicted correctly
```
   knee  600 (V111)  predicted 0.7439 [0.669,0.815]   MEASURED 0.7336            route 21
   knee 1800 (V112)  predicted 0.2353                 MEASURED 0.3102 / 0.1071   r22 / r23
   knee 2400 (V119)  predicted 0.0484                 <- this build
```
`(816/1024)(12/2400) = (612/1024)(12/1800) = 0.0039844` **exactly** ⇒ **bit-identical below 31.8 °/s.**

### LEVER 2 — disarm the biquad
One byte, coefficients untouched, revert is the same byte. Corpus point estimate **1.47×**
(OFF −37.7 / ON −55.4) but **P = 0.722, not separable** — **this build is the test.**
⊕ ~32 % is the right SIZE: the oscillation is bounded, not divergent, and no damping lane can supply
more than ~10 % of the deficit anyway.

### 🛑 SCORING IS PRE-REGISTERED — `docs/scoring/SCORING-V118-preregistered.md` applies unchanged.
**Read the identity check FIRST**: the 427 wire must come back **DISCRETE {0,5,…75}** or V119 is not
on the car. `state = wire/5`; **STATE 4 = WIRE 20**; wire ≥1023 = contamination, discard.

⚠ **Honest expectation: a REDUCTION, not elimination.** The 7–9 Hz excess is plausibly the price of
deleting Honda's four limiters, not one tunable fault
([[accord-the-mod-works-by-deleting-hondas-limiters]]).

## ⭐⭐ V118 BUILT — **BIQUAD DISARM + THE STATE-4 PROBE. One flight, two answers.**
```
builder  analysis-2020accord/builds/v108_plus/build_v118_tva.py   43/43   BASE = V112
image    8a0f0080631208dfa524e5eae54a4bcc9a9fac26759bac777e29daa1c7f7c4ce
.rwd     92b798a14abed24286e9b53a0c03bb6c97b107b5c3c8c26b9701645ea8db99e8
0xC649B   1 -> 0                    disarm the biquad        (candidate FIX)
0x55DF2   gp-0x6ABC -> gp-0x67FA    the CAN 427 tap          (candidate DIAGNOSTIC)
0x55E10   sar 3 -> sar 0            probe scaling
4 payload bytes.  🛑 NO CAVE EDIT — the 164-byte cave is byte-identical.
```
The tap repoint is a pure **displacement edit**, the class that has never failed on this ECU.

### WHY BOTH IN ONE FLIGHT
The two surviving candidates for the 7–9 Hz excess are the **armed biquad** (testable by flying the
disarm) and **`0x454FE`'s deletion of Honda's state-4 governor call** (**not** safely testable by
reverting — V42's change is a validated fix for the V38 macro ratchet). What `0x454FE` needs first is
its **duty**, which is unmeasured: `gp-0x67fa` is not on the bus and no cached build telemeters it.
⇒ **fly the disarm and measure the state simultaneously.**

### THE PROBE
`wire = min(|gp-0x67fa as halfword| × 5, 0x3FF)` ⇒ **state 0–15 maps to wire 0,5,…75; STATE 4 = WIRE
20.** `gp-0x67fb` (the high byte) has 4 writers, every one `st.b r0` = **zero**. If it is ever
non-zero the wire becomes ≥ 1285 and **CLIPS at 1023** ⇒ contamination is **self-identifying** and
those samples are discarded, not misread — the guard against a hidden 6-byte-form writer.
⊕ **What is given up:** the tap's `|gp-0x6abc|` rate, which is also on CAN as `cs_rate` — the channel
every Re(Z) measurement here already uses. **No existing analysis depends on the tap.**

### READ THE DRIVE FOUR WAYS
*oscillation weaker* ⇒ the biquad contributes; reshape its coefficients next · *no change* ⇒ biquad
eliminated · *worse* ⇒ revert the one byte. **And independently:** *state-4 duty HIGH* ⇒ `0x454FE`
becomes the prime suspect, and the fix is to restore `FUN_00049A5A` **modified**, never a blind
revert · *duty ≈ ZERO* ⇒ `0x454FE` eliminated, leaving the V57 gain repoint, the ceiling raise and
~20 cal cells.

## ⭐ V117 BUILT — **DISARM THE BIQUAD.** One byte, fully reversible.
```
builder  analysis-2020accord/builds/v108_plus/build_v117_tva.py   41/41   BASE = V112
image    ea5ad8d319cf75eca90da21cc37c337192a1ebedf77a21749ceeb1e2b3d91131
.rwd     754f15a0125f58450a3af69f8b3d218009c6da782cbedba761212621098630b7
0xC649B   1 -> 0   the biquad ARM cal.  knee 1800, K1 612, alpha2 14 all HELD.
1 payload byte (01 -> 00) + 1 CRC trailer.  All three biquad COEFFICIENTS byte-identical.
```
**The filter, read from assembly @`0x35A28`–`0x35A50`:**
`y[n] = 0.81731·x + 1.53720·y[n−1] − 0.63462·y[n−2]` — all-pole, pole radius 0.79663, angle
0.26565 rad, **DC gain 8.39**. At 1 kHz its pole is 42.3 Hz (a **flat 8.4×** through 7–12 Hz); at
100 Hz it is 4.23 Hz (a **Q-2.46 resonator** on the problem band). The task rate could not be pinned
(`FUN_000352b4` is entered from an RTOS TCB at `0xBB928`), **but either way arming it puts a large
gain into the aggregator path, and stock leaves it OFF.**
🛑 Arming needs THREE edits: `0xC649B` 0→1, `0x35A08` `e798`→`fb97` (gate input `gp-0x671a` →
`gp-0x6806`), `0x35A12` `ec`→`e0` (`cmp r12,r9` → `cmp r0,r9`). **V117 clears only the CAL byte.**

### WHY THIS, AND WHY IT IS HONEST ABOUT ITS OWN EVIDENCE
Seven candidates for the 7–9 Hz excess are eliminated, each with its own control. The biquad's
natural experiment is the **strongest surviving signal**: OFF (9 routes) median **−37.7** vs ON
(8 routes) **−55.4**, a **1.47×** point estimate — far larger than V115's ~1.05×.
🛑 **But P(ON worse) = 0.722 against chance 0.5 is NOT separable at n = 9/8, and the excess is
already present at V90, which has no biquad. The biquad is NOT the origin** — at most an additive
contributor. **This build converts an unseparable observational comparison into a single-variable
on-car test.**

### READ THE DRIVE THREE WAYS
*oscillation weaker* ⇒ real contributor, next step is reshaping its coefficients · *no change* ⇒
eliminated too, move to the remaining common edits · *worse* ⇒ arming was doing useful work, revert
the byte. ⊕ **V88 — which the operator reported as "grinding FIXED" — ran with this filter OFF.**

## ⭐⭐ V115 BUILT — **V112 (FLOWN, BEST YET) + ONE BYTE**.  THE RECOMMENDED NEXT FLIGHT.
```
builder  analysis-2020accord/builds/v108_plus/build_v115_tva.py   42/42   BASE = V112
image    5f804a8a2aee5e18da226cfebe4b2bec564713a4183613e3aed846460a191a97
.rwd     f1a47bb7d6b3d53a2c5a919338bfc80bd8dd4c84042cd08a0bb03ac1a74ecd22
0xC40DC   14 -> 8   alpha2.  knee 1800 and K1 612 (V112's) both HELD.
1 payload byte (0e -> 08) + 1 CRC trailer.  NO CAVE EDIT.
```
🛑 **V112 IS ON THE CAR AND IS THE BEST BUILD YET** — and it is not only comfort: it improved
**command authority**, the operator's own standing ask.
```
   achieved / demanded steering rate, engaged, low-torque, moving
     demand band    5-15    15-30   30-60  deg/s
     r21  V111      0.487   0.475   0.367
     r22  V112      0.669   0.590   0.432
     r23  V112      0.791   0.544   0.390
```
⇒ **V112 tracks 1.37–1.62× better than V111 at 5–15 °/s and better in every band.**
🛑 **V114 IS SUPERSEDED** — it was built on a V111 base before this was known. Same edit, wrong base.
🛑 **V113 IS DEPRIORITISED** — it was built to be "strictly safer" than V112 on an anti-damping
argument the car has now refuted.

### WHAT V115 ADDS
`α2` **14→8** ⇒ **6–16 Hz DAMPING ×1.252 while 6–16 Hz apparent MASS ×0.796** (the lane is a
bandpass; α2 moves its corner, so it **rotates** the vector instead of scaling it). It targets the
located peak-turn oscillation at **7.42 Hz** — route 23 seg 7, t = 445.6–448.2 s, **6–9 Hz RATE
16.86 °/s against a corpus p99 of 3.98.** ✅ Every magnitude falls (peak ×0.669, broadband ×0.604,
100 Hz 7.13→4.05) ⇒ **cannot repeat V107**, and the 100 Hz drop may also help grind #1.
✅ GATE 1 the cleanest in the kit (ONE access image-wide, zero writers).

## ⭐⭐ V114 BUILT — **ONE BYTE THAT RAISES DAMPING AND LOWERS MASS AT THE SAME TIME**
```
builder  analysis-2020accord/builds/v108_plus/build_v114_tva.py   42/42   BASE = V111
image    8c4f53ccf8be61f8d3ceee5dcd4ca2c4ef46abe36af7e8e51b59ade104491820
.rwd     26d2a6c10e7f2816338a698440ea454dffd2d15aadd6c3e76b7ebb906ef0f5c1
0xC40DC   14 -> 8   alpha2, the gp-0x6c2c EMA pole
1 payload byte (0e -> 08) + 1 CRC trailer.  NO CAVE EDIT.  Knee and K1 both HELD.
```
⭐⭐ **THE FIRST LEVER TO SATISFY THE BOTH-AT-ONCE DIRECTIVE FROM A SINGLE CELL.** The lane is a
**bandpass** `64·H_lp·(1−z⁻¹)·H_ema`; **α2 sets its upper corner**, so lowering it walks the peak
DOWN toward the anti-damped band. Split against the **velocity** phasor
(`DAMPING ~ |H|·sin φ`, `MASS ~ |H|·cos φ`):
```
   α2   peak Hz   6-16Hz DAMPING   6-16Hz MASS   20-30Hz damping   broadband rms
   22     61.1        0.794            1.085          0.921            1.488   (V108)
   14     46.5        1.000            1.000          1.000            1.000   (V111)
    8     34.2        1.252            0.796          0.899            0.604   <- V114
    6     29.3        1.318            0.647          0.769            0.463
    4     23.7        1.274            0.422          0.564            0.316
```
🛑 **DAMPING UP, MASS DOWN.** Only possible because α2 **rotates** the vector — more of a *smaller*
term lands on the damping axis. Every scaling lever moved both together; that is why the directive
looked like a contradiction. **It is not.**

### WHY THE DOSE IS 8
6–16 Hz damping peaks near α2 = 5–6, but the 20–30 Hz give-back grows fast and **21–27 Hz is where
V106's win was measured.** α2 = 8 takes **+25 % in the deep band for −10 % at 20–30 Hz**, and it is the
same step SIZE the operator already read clearly (V111's 22→14 was ×1.27 damping ⇒ *"oscillations
gone, ratcheting reduced"*). **6 and 5 stay available on a monotone axis.**

### ✅ IT CANNOT REPEAT V107
V107 railed by multiplying the **Y row** (magnitude). α2 does the opposite: **peak |H| 9.20→6.15
(×0.669), broadband rms ×0.604, 100 Hz 7.13→4.05.** Every magnitude falls ⇒ rail duty must fall.
⊕ The 100 Hz drop attacks V107's own *"higher-pitched, several hundred Hz"* complaint directly.
✅ **GATE 1 is the cleanest in the kit**: exactly ONE access image-wide, `0x41626 ld.hu 0x50dc,tp,r11`,
zero writers. Both lineage conditions met — ships WITH the notch revert, taken UNCOMPENSATED.

### ⚠ RESIDUAL RISK
`gp-0x6c2c` has **three** consumers; only the damper is verified against a reshaped signal. The
detector (`FUN_000428d4` vs `cal(0xC620A)`) is the second and **fires LESS** as α2 falls (safe
direction); the third is unenumerated. ⊕ V109/V111 already flew this axis (22→14) fault-free.

### 🛑 TWO INDEPENDENT SINGLE-VARIABLE CANDIDATES NOW SIT ON THE SHELF
**V113** (relay knee 600→1800, K1 held) and **V114** (α2 14→8) are **orthogonal** — different lanes,
different mechanisms. Fly either alone; **do not stack them** or the next report is uninterpretable.

## 🛑🛑 THE ANTI-DAMPING IS CENTRED AT **9–12 Hz** — NOT AT 20–30 Hz WHERE THE POWER IS
2026-08-27. `Re(Z) = Re(H1[rate → column torque])`, 17 route-arms. **Estimator validated**: per-°/s
here vs per-rad/s in the record — −43 × 57.3 = −2464 against the published −3375/−3176/−3073.
```
   Hz band      2-4   4-6   6-9  9-12 12-16 16-20 20-24 24-28 28-34 34-42
   r21  ENG       1    -7   -43   -67   -47   -15    -4     3     8     4
   r21  MAN       3     6     7     7     7     8    11    13    15    14
   r78  ENG      -4    -1   -33   -48   -39   -12    -3     5     8     8
   ra4  MAN       8    11    13    14    16    18    17    17    18    18
```
🛑 **The MANUAL arm is DAMPED at EVERY band on EVERY route that has one (+3 to +19, no exceptions).
Engaging drives 6–16 Hz deeply negative.** The anti-damping is a consequence of engaging.

### 🛑 THIS CORRECTS THE PREVIOUS BLOCK
20–30 Hz carries **36 % of the rate power**, and I concluded the damping lever should target it.
**Wrong.** `Re(Z)` at 20–24 Hz is only **−3 to −5** and crosses positive at **f0 ≈ 23.3 Hz** (corpus
p50, n=17; range 22.4–24.9 excluding two low-n outliers). The minimum is **−67 at 9–12 Hz.**
⇒ **20–30 Hz is where a lightly-damped resonance RINGS; 6–16 Hz is where the energy is PUT IN.**
**Size any damping lever on 6–16 Hz.**

### ⭐⭐ AND THE LANE IS ALREADY IDENTIFIED
`gp-0x6b26` measures **+137°/+139° vs wheel rate at 6–9 Hz ⇒ +518/+565 counts of POSITIVE Re(Z)** —
**inside the deepest anti-damped band.** That one fact explains both ends of the record: **V94 removed
6/6ths of it** ⇒ *"vibrated the entire car… not safe to drive"*; **V106 tripled it** ⇒ extinguished the
21–27 Hz mode, the kit's only band-power result to clear its own split-half null.
⇒ **If the operator re-opens the damping class, this is the lane and 6–16 Hz is the target.**
⚠ The **uniform** axis was declared exhausted after V106 and V107's reshape railed — a new dose needs
a **shape** argument, not a bigger number.

⚠ Engaged Re(Z) is hands-off, so the ENG/MAN contrast is directional evidence about the loop, not a
matched experiment; and route 21's −67 is confounded by its own speed/excitation mix — **not a build
ranking.**

## 🛑🛑 THE OSCILLATION IS **NOT COMMAND-DRIVEN** — WHICH KILLS A WHOLE LEVER CLASS AND RE-OPENS ANOTHER
2026-08-27, 15 routes pooled, engaged & hands-off & moving, Welch 1024-pt @100 Hz.
```
  band          % cmd pwr   % rate pwr   coh2    coherent rate pwr (of ALL rate power)
   0.1- 1.0 Hz   58.0971      27.9021    0.649        18.4569 %
   2.0- 5.0 Hz    2.3508       3.2236    0.309         0.9923 %
   5.0- 8.0 Hz    0.5996       3.8160    0.237         0.8771 %
  12.0-20.0 Hz    0.3442       6.3918    0.078         0.4334 %
  20.0-30.0 Hz    0.1912      36.0137    0.100         5.0124 %   <- DOMINANT
```
🛑 **Rate power above 5 Hz = 50.95 % of the total; the COHERENT part is 6.90 %** ⇒ **~86 % of the
high-frequency motion is not linearly explained by the command.** Command energy above 5 Hz is only
**1.65 %** of the command's own total.

### 🛑 KILLED: THE ENTIRE COMMAND-SIDE FILTER CLASS
A command-side low-pass can remove **at most 6.9 %** of total rate power. This independently
reproduces the struck verdict on the arbitration IIR `0xC63EC`/`0xC63EE` from a different instrument.
⊕ `Kd` (`0xC6AE6`) separately closed — one knot of a **flat** 4-knot LERP ⇒ a one-knot edit creates a
nonlinearity where a constant stands: **worse than inert** (it killed V110).
🛑 **Do not propose lowering the arbitration corner. Do not propose Kd.**

### ⭐⭐ RE-OPENED: LOOP DAMPING — THE ONLY CLASS WITH A MEASURED SUCCESS
**20–30 Hz dominates the energy while being nearly uncorrelated with the forward input.** That is a
**self-sustained loop oscillation**, matching *"9,200× less power with LKAS off"*: engaging closes a
loop whose gain is too high, it does not inject the tone. ⇒ **raise loop damping / cut loop gain.**
⊕ **V106's ×3.0 `gp-0x6b26` dose extinguished the 21–27 Hz mode at low speed** — still the kit's only
band-power result to clear its own split-half null.

### 🛑🛑 AND THE DIRECTIVE'S PREMISE DOES NOT SURVIVE MEASUREMENT — PUT THIS TO THE OPERATOR
His no-mass-no-friction rule rests on *"it costs max steering angular velocity."* Measured:
1. the firmware **over-delivers** vs its command (`CMD→rate` **+1.2 dB**, coh 0.51);
2. the deficit is **upstream in openpilot** (`demandRate→CMD` **−16.0 dB**);
3. damping is **cheap**: `gp-0x6bbe` ≈ 90 ct/(rad/s) vs a 2505-ct full command ⇒ **doubling it costs
   0.63 % at 5 °/s, 1.38 % at his p90 demand of 11 °/s, 5.01 % at the p99 of 40 °/s.**
⇒ **The damping class should be back on the table.** 🛑 **Ask him — do not act on this unilaterally.**

⚠ NOT established: **which** loop. Coherence at 12–30 Hz is 0.078–0.100, so the incoherent
remainder's origin (plant, road, or a loop the command cannot see) is unresolved. An on-car
gain-step system ID at 18–31 Hz stays the open item.

## 🛑🛑 V113 BUILT — AND IT **WITHDRAWS V112**. Knee ×3 with K1 HELD.
```
builder  analysis-2020accord/builds/v108_plus/build_v113_tva.py   39/39   BASE = V111
image    d2e86f8272dff71d402680399649dc35b7e39f6e7b200ae9c5a7ee9812ba823b
.rwd     07d64f509e6d92a538a26b99778888568b2ac8fc88ca731556cfa025e4dc3e5a
0xC40BC   600 -> 1800   relay KNEE   |   0xC40D2  204 -> 204  K1 HELD, NOT WRITTEN
2 payload bytes + 1 CRC trailer.  NO CAVE EDIT.  ZERO unattributed.
```
🛑 **V112 IS WITHDRAWN.** It scaled knee AND K1 together to hold the small-signal gain — which
delivers **up to 2.93× MORE anti-damping above 10.6 °/s** (describing function of the odd
saturation; the EMA `0xC40D0`=408 adds only −1.1° at 2 Hz to −11.1° at 21 Hz, so the term is
**in phase with RATE**, and it is a friction COMPENSATION). **That is V94's failure mode** — the
drive the operator aborted as unsafe, whose lane measured **+518/+565 counts of POSITIVE Re(Z)**.
⊕ **Real Coulomb friction IS constant-magnitude** (`μN·sign(v)`) ⇒ **the saturation was the model,
not the bug.**

⭐ **V113 raises the knee and HOLDS K1**, so `sat()` can only shrink ⇒ the term is **≤ V111's at
every rate**, proved by exhaustive sweep (`worst excess +0.000000`), not by argument:
```
   rate      V111 term   V113 term   ratio          relay saturation duty (route 21, measured)
    3 d/s     0.05632     0.01877    0.333             knee  600 (V111)  0.7439 [0.669,0.815]
   10 d/s     0.18775     0.06258    0.333             knee 1800 (V113)  0.2353   <- a 3.2x cut
   30 d/s     0.19922     0.18775    0.942          small-signal slope x0.333
   60 d/s     0.19922     0.19922    1.000          (both railed -- equal, never greater)
```
⚠ **COST:** less friction compensation ⇒ the wheel feels **HEAVIER than V111 below ~30 °/s**, and
`FUN_0003b8f6` is not LKAS-gated so manual feel changes too. That is the price of not repeating V94.

### ✅ THREE-WAY DISCRIMINATOR ON THE NEXT DRIVE
*"heavier but smoother"* ⇒ right axis, walk the dose back toward 1200 · *"smoother and no heavier"*
⇒ V112's premise was wrong in the safe direction · *"no change"* ⇒ **the relay is not the ratchet
mechanism, abandon this axis.**
🛑 `0xC40DC` α2 stays at V111's 14 ⇒ still a single-variable read.

## 🛑🛑 THE RATE DEFICIT IS **UPSTREAM OF THE FIRMWARE** — AND THE SAME DATA LOCATES THE OSCILLATION
2026-08-27, 15 routes, Welch H1 1024-pt @100 Hz, engaged & hands-off & moving, normalised to each
path's own 0.1–0.3 Hz value. **This splits the standing goal in two and closes one half.**

```
  band        demandRate->CMD     demandRate->rate      CMD->rate        drvTorque->rate
  0.1-0.3 Hz   1.000 coh 0.317     1.000 coh 0.428    1.000 coh 0.704    1.000 coh 0.682
  1.0-2.0 Hz   0.158 (-16.0 dB)    0.248 (-12.1 dB)   1.152 (+1.2 dB)    0.765 (-2.3 dB)
  5.0-8.0 Hz   0.075 (-22.5 dB)    0.201 (-13.9 dB)   2.019 (+6.1 dB)    0.208 (-13.6 dB)
 12.0-20.0 Hz     --               0.478  (-6.4 dB)   2.376 (+7.5 dB)    0.302 (-10.4 dB)
```

### 🛑 HALF ONE — "HIGHER MAX ANGULAR VELOCITY" IS **NOT FIRMWARE-TRACTABLE**
**`demandRate->CMD` is attenuated MORE than `demandRate->rate`** (−16.0 vs −12.1 dB). Both share the
same input, so the ordering is robust to the low coherence. ⇒ **openpilot does not turn its own fast
rate demand into a fast command, and the firmware then delivers MORE motion than it is asked for.**
⊕ Demand excursions above 15 °/s last **p50 0.030 s** against the arbitration IIR tau **0.0315 s**
⇒ a 30 ms pulse reaches **61 %**, and the measured `ach/dem` at 15–30 °/s is **0.63**.
⊕ openpilot's slew limiter = `STEER_DELTA 3.0/s × 0.01 × 4096` = **122.88 ct/frame** (full scale in
0.33 s) ⇒ in a 30 ms episode the command can move **9.0 % of scale**. Duty ≥90 % of the limiter **5.0 %**.
🛑 `STEER_MAX`/`STEER_DELTA` are openpilot-side and off-limits ⇒ **no cal can recover motion that was
never commanded. Stop hunting for a rate lever.**

### ⭐⭐ HALF TWO — THE OSCILLATION **IS** OURS, AND IT IS THE TRACTABLE HALF
`CMD->rate` **RISES** (+1.2 / +6.1 / +7.5 dB) while the driver's path through the **same plant FALLS**
(−2.3 / −13.6 / −10.4 dB). **Same plant, two inputs, opposite slopes ⇒ the high-frequency emphasis
is in the LKAS path, not the mechanics** — consistent with the Q 14–29 resonance being *excited* by it.
⇒ **The next lever is HF de-emphasis in the LKAS path with no added impedance.**

| the operator asked for | verdict |
|---|---|
| eliminate grinding / oscillation / ratcheting | ✅ **firmware-tractable** — `CMD->rate` is +6 to +7.5 dB above 5 Hz, and that is ours |
| higher max steering angular velocity under 6× | 🛑 **NOT firmware-tractable** — the firmware already over-delivers vs the command |

⚠ [EVIDENCE] for `CMD->rate` (coh 0.70 / **0.51** / 0.28) and the driver contrast; [BELIEF, direction
only] for the `demandRate->CMD` absolute dB (coh 0.06–0.32, noise-biased down — the **ordering** carries it).

## 🛑🛑 THE STEERING-RATE DEFICIT IS **MEASURED, REAL AND UNIVERSAL** — AND V111 DID NOT CAUSE IT
2026-08-27. Answers the operator's standing question (*"it feels like the max angular velocity has not
scaled 6x"*). **He is right, and it is not a V111 regression.**

```
  CORPUS POOLED — 18 cached routes, engaged & hands-off (D3) & moving, weighted by n
  demanded deg/s      n        RAIL DUTY (|cmd| >= 4090)      achieved / demanded
      5 - 15       103158             5.9 %                        0.73
     15 - 30        36595            16.9 %                        0.63
     30 - 60        18137            32.0 %                        0.47
     60 +           13407            49.8 %                        0.30
```
🛑 **Rail duty rises monotonically with demand.** Above 60 °/s openpilot emits its absolute maximum
(`STEER_MAX = 4096`) **half the time** and still gets **30 %** of the motion. ⇒ **AUTHORITY-STARVED.**
⊕ **Not the plant** — the **driver reaches 335.2 °/s** at the same speeds; LKAS at a railed command
reaches **84.6**. ⊕ **Not a hard clip** — no pile-up at 84.6 (2 samples within 5 %, vs 13 for manual),
and the engaged max moves with speed. A **soft roll-off.**

### ⭐ NOT A V111 REGRESSION — THIS RETIRES THE α2 REVERT
`ach/dem` at 60+ °/s is **0.09–0.49 across all 18 routes, median ~0.26**; **route 21 (V111) = 0.24.**
The deficit predates V111 on every build. 🛑 **Reverting `0xC40DC` α2 14→22 will NOT restore the
rate**, and the "α2 rotates inertia into friction ⇒ that caps velocity" story cannot explain a deficit
that predates it. ⊕ `gp-0x6b26` is clamped by `cal(0xC407E) = 511` (**decompile-confirmed**, operand
`tp+0x507E`) ⇒ ≤ 2.6 % of the ±20 000 residual, and α2 moves only its friction component
(Δ ≈ 0.078 at 8 Hz) ⇒ **≤ ~40 counts = 0.2 % of range.** Far too small.

### 🛑 FOUR CLAMPS EXCLUDED BY ARITHMETIC — DO NOT RE-PROPOSE
| candidate | why dead |
|---|---|
| `0xC520C` cap table | already struck; measured dead on route `a6` |
| `0xC6202` governor 4762 | full-command LKAS = `15360*5346>>15` = **2506** < 4762; also lockstep-shadowed → fault 0x17 |
| `0xC61B2/B4` arb clamp 3072 | **2506 < 3072** ⇒ never bites at 6x (would at ≥7.35x) |
| a hard 84.6 °/s rate clip | no pile-up |
⊕ `0xC646C` is **891 on every build**; the 6x lives on `0xC6CD0` = **5346** (= **6.000x** exactly).

### ⭐ CONSEQUENCE — IT INDEPENDENTLY CONFIRMS V112
`STEER_MAX` is openpilot-side and off-limits, so the useful lever is **more wheel motion per unit of
command with no added impedance.** **V112's corner move 10.6 → 31.8 °/s covers exactly the band where
`ach/dem` falls 0.63 → 0.47**, and more friction compensation = more assist (verified polarity).
Arrived at from a completely different direction than the ratchet argument that motivated V112.

### 🛑 TWO RETRACTIONS FROM THIS SESSION — both caught by their own controls
1. ~~"rate compresses against command"~~ — matched on speed and angle but **not on demand**; a high
   command also means *holding* a turn. Conditioning on demand dissolves it.
2. ~~"the car delivers 89–107 % of demand"~~ — used **`ct_curv` = `controlsState.curvature` = CURRENT**,
   so it was **circular** (tell: `r = -0.9995` vs measured angle). 🛑 **In this cache
   `ct_curv`/`cc_ccurv` are CURRENT; `ct_dcurv`/`cc_curv` are DEMAND.**

### ⚠ NOT ESTABLISHED
**Where** the roll-off lives. Four clamps excluded; loop bandwidth, the LKAS lane low-pass and plant
load remain. ⚠ The 60+ band is partly **planner steps** — the **15–30 °/s band (0.63, rail 16.9 %)
carries the argument**, being ordinary and physically reachable.

## ⭐⭐ V112 BUILT — THE FIRST LEVER THAT SATISFIES THE BOTH-AT-ONCE DIRECTIVE
```
builder  analysis-2020accord/builds/v108_plus/build_v112_tva.py   37/37   BASE = V111
image    f032878c4e0b8e90d782ddac6ba2d644e09956cc1b267a60ef4fb1c44ee1f96f
.rwd     64f2ee9eb23442673edd43251e1b27db90ba596ebea93016875379fbe0495692
0xC40BC   600 -> 1800   the relay KNEE     (saturation 10.6 -> 31.8 deg/s)
0xC40D2   204 ->  612   K1                 (cancels the knee's gain change EXACTLY)
4 payload bytes + 1 CRC trailer.  ZERO unattributed.  NO CAVE EDIT.
```
⭐ **Scaling BOTH cells is the whole trick.** `gain = (K1/1024)(12/knee)`, `saturation = knee/12` —
the knee is in both, K1 in only one, so K1 cancels the gain change and leaves the saturation change
standing. `(204/1024)(12/600) = (612/1024)(12/1800) = 0.0039844` **exactly** ⇒ **below 10.6 °/s V112
is BIT-IDENTICAL to V111**; above it the term keeps climbing instead of clipping.
⇒ **It adds NO impedance** — it reshapes a feed-forward friction COMPENSATION, so it cannot cap max
angular velocity the way `gp-0x6b26`, the damper and α2 all do. **That is what makes it the first
lever compatible with the operator's directive.**

### ⭐⭐ ROUTE 21 IS THE V111 DRIVE — AND IT MEASURED THE RELAY
Identified by **physics, not assumption**: the 427 tap's quantiles numerically EQUAL the steering rate
from `ang` — p95 39.4 vs 40.4, p99 167.4 vs 171.8, **p99.9 313.4 vs 313.3 °/s**. Only true if the tap
is `gp-0x6abc` at sar 3. ⊕ **Independently confirms the 4.7121 ct/(°/s) scale.**
```
  RELAY SATURATION DUTY  --  5-10 mph, engaged, hands-off, |cmd|>=2048, n=289
     knee  600 (V111)  0.7439   95% CI [0.6691, 0.8146]   <- ON THE CAR
     knee 1200         0.4810
     knee 1800 (V112)  0.2353                             <- BUILT, a 3.2x cut
     knee 2400         0.0484
```
🛑 **THE RELAY IS IN HARD COULOMB MODE 74 % OF THE TIME IN EXACTLY THE REGIME HE NAMED.** First
direct measurement of the mechanism the kit has asserted since V80. ⊕ Unconditioned the same regime
is 18.5 % ⇒ **command drives saturation 4×**, matching the command gate from a different instrument.

### GATES
✅ **GATE 1** — one reader each, two methods agreeing: `0xC40BC` at `0x3BAB4`, `0xC40D2` at `0x3BAFE`.
✅ **GATE 2** — the knee is an **odd, memoryless saturation** ⇒ DF real ⇒ **ZERO phase added.** The
magnitude rises ≤2.97× **but can never exceed the small-signal gain, which is unchanged and already
exercised at low rate every drive.** No new gain regime.
✅ **THE CLAMP OBJECTION IS DEAD** — `cal(0xC7468)=41232` and the residual clamps at ±20000, so
`|model| ≤ 0.4851` and `friction_max = 0.290` against a ±10.0 clamp: **34× headroom** (103× at V111).
⚠ **THE COST, PLAINLY:** above 31.8 °/s the residual falls `0.80·|model|` → `0.40·|model|` — a 2×
reduction in the torque-tracking reference. More assist by the verified polarity, but not small.
And `FUN_0003b8f6` is **not LKAS-gated**, so manual feel changes above 10.6 °/s too.

### 🛑 α2 IS DELIBERATELY LEFT ALONE
`0xC40DC` stays at V111's 14. The α2 cut is the suspected source of the friction he objects to, but
that magnitude is **unverified**, and reverting it would give back three measured improvements for
one regression. **V112 changes the RELAY ONLY**, so his next report is a single-variable read on the
relay hypothesis.

## 🛑🛑 V111 FLEW — OPERATOR REPORT, 2026-08-27. **THREE SYMPTOMS BETTER, STEERING RATE WORSE.**
**AND A STANDING DIRECTIVE THAT RULES OUT A WHOLE CLASS OF LEVER.**

⭐ **V111 is the cleanest single-variable experiment this kit has ever run.** V111 − V108 = three
payload bytes, two of them telemetry; **the only dynamics change is `0xC40DC` α2 22→14.** Every other
cell — relay knee 600, gain 5346, the `gp-0x6b26` Y row, the biquad, the whole 164-byte cave — is
byte-identical. ⇒ **whatever he felt, α2 caused it.**

### HIS WORDS — the primary readout
> *"Regarding the grinding issue, **most of it has been resolved.** However, **grind number one still
> occurs at low speeds between 5 and 10 mph, particularly under strong openpilot commands.** The
> frequency is **higher-pitched than before**, but it is a **muted or attenuated version.**"*
>
> *"**I no longer observe general oscillations** when driving straight or during slight turns. **The
> ratcheting effect also seems reduced**, but this appears to have come at **the cost of maximum
> steering angular velocity and acceleration.**"*

### 🛑🛑 THE DIRECTIVE — binding on every future lever
> *"**Increasing mass and friction should not be our primary approach to resolving the ratcheting if
> it comes at the cost of max steering angular velocity and acceleration. We want both: low apparent
> steering mass and friction to LKAS AND no ratcheting (feedback from driver torque sensor).**"*

⇒ **This is well-posed, because the two requirements live on DIFFERENT PATHS.** MOTION-fed lanes
(`gp-0x6b26` inertia, `gp-0x6bbe` viscous, the base-assist damper) oppose **all** motion and therefore
**cap max angular velocity by construction** — the LKAS command has to push through them. TORQUE-fed
lanes (the PID in `FUN_0003a382` on `gp-0x4f60`, the observer/friction lane) close the loop he calls
*"feedback from driver torque sensor"* and **do not load the LKAS path.**
🛑 **⇒ THE RATCHET LEVER MUST BE TORQUE-PATH. A motion-fed lever cannot satisfy him.**
Full note: `memory/feedback/builds/feedback-do-not-buy-ratchet-with-mass-and-friction.md`.

### ⭐ THE MECHANISM — lowering α2 rotates INERTIA into FRICTION
`gp-0x6b26 = −K·gp-0x6c2c` and `gp-0x6c2c` is filtered **acceleration**, so the term is pure apparent
**mass while in phase**. EMA lag `φ` rotates it; the component in phase with **velocity** — friction —
scales as `sin φ`, and α₂ 22→14 roughly **doubles φ**:
```
    f Hz   FRICTION component 22 -> 14   ratio      MASS ratio
    1.00        0.0120 -> 0.0224         1.87x        1.000x
    5.00        0.0596 -> 0.1104         1.85x        0.990x
    8.00        0.0946 -> 0.1723         1.82x        0.976x
```
⇒ his *"increased mass and friction"* is, by this account, **almost entirely FRICTION**, and friction
acts against velocity — exactly what caps angular velocity. It also explains the ratchet reduction
(more damping at ~8 Hz) and the grinding reduction (−27–−40 % over 61–300 Hz) **from the same byte.**

### 🛑 THE HOLE, STATED RATHER THAN PAPERED OVER
**Magnitude NOT verified.** `gp-0x6b26` clamps at ±511 against a ±20,000 residual (≤ **2.6 %** of
range; engaged p50 recorded at **4.8 counts**) — **doubling 11 % of a 2.6 % term is small to explain a
felt loss of steering rate.** ⚠ **And the counter-argument:** lower α2 also shrinks `|gp-0x6c2c|`, so
`gp-0x6b26` should **rail LESS**, which points the other way. **[BELIEF: right sign, right band,
magnitude unverified.]**

### ✅ WHAT WOULD SETTLE IT — AND THE DATA MAY ALREADY BE ON DISK
**Route `21`: 18 segments, uncached, newer than `1e` (V107).** If it is the V111 drive it carries
**V111's own `gp-0x6abc` tap** ⇒ (1) the **relay input amplitude** V111 exists to measure (GATE 2 says
the knee only bites below ~200–400 counts), and (2) `gp-0x6b26`'s real magnitude and rail duty, which
closes the hole above. 🛑 **It must be registered in the `ROUTES` table that
`extract_r7d.extract_route()` reads. That is the single highest-value action available.**

### ⚠ THE UNCOMFORTABLE COROLLARY — a straight α2 revert is NOT an obvious win
It would recover the steering rate but give back **three measured improvements for one regression.**
One EMA pole **couples** the magnitude cut (helps) to the phase lag (hurts). **Do not propose the
revert as a free fix.** ⊕ The real target is a lever that **decouples** them: cut the torque-path
feedback at the ratchet frequency (candidate: **`Kd`, all four knots `0xC6AE6/E8/EA/EC`**, which
reduces a feedback GAIN and therefore **cannot add apparent mass**) while leaving α2 where it is.
⚠ Kd's priced cost is **2.9–4.4:1 against, paid in 18–31 Hz grinding damping** — computed when
grinding was the top complaint. **It no longer is. Re-weigh, do not re-quote.**

## 🛑🛑 V108 FLEW — OPERATOR REPORT, 2026-08-27. **HIGH SPEED FIXED; LOW SPEED UNCHANGED; AND THE PREDICTION LANDED.**

🛑 **ON THE CAR: V108.** No rlogs available for this flight — **the operator's own words are the entire
readout**, and by the standing rule they are the PRIMARY one. Verbatim, in his terms:

- **"High speed behavior is good overall. I don't experience any oscillations or... any oscillations
  even on hard turns at speed at this point. So that has been fixed."**
- **"Twenty miles an hour and above, generally, this is the best that it's ever been in that regime at
  six x."**
- **"Around sixty to sixty five miles an hour, I think sometimes I do hear a grinding, or it's like a
  whole vehicle vibration... I'm not really completely sure that this is our firmware's fault. It might
  have just been the road because it's not consistent."**
- **"Low speed below ten miles an hour, grinding is still there. The audible grinding is still there. It
  seems like it's made up of TWO MODES. One mode that is slightly higher pitch, maybe around a hundred
  hertz. And there's another mode which seems like it's around a hundred or two hundred hertz...
  significantly higher in pitch."**
- **"At low speed, the maximum steering angular velocity is still limited."**
- **"Around ten to fifteen miles an hour, maybe ten to twenty, there is oscillation and grinding."**

### ⭐⭐ THE PREDICTION LANDED — the symptom map and the rail-duty map agree ACROSS A BUILD CHANGE
```
  speed        V107 measured   V108 predicted            operator's report on V108
  <6 mph          1.68 %       1.47 %  (Y[0] BYTE-IDENTICAL -- nothing changed here BY DESIGN)
                                                          grinding still there, TWO modes
  6-15 mph       32.32 %       <=15.46 % (halved, still the worst bin)
                                                          oscillation AND grinding
  15-25 mph      21.27 %       <=10.45 % (halved)         --
  25-40 mph       4.27 %       <= 3.43 %                  "best it's ever been at 6x"
  40+ mph        <=0.23 %      <=0.23 %  (identical to V107)
                                                          "that has been fixed"
```
🛑 **Where the duty fell, he reports it fixed. Where it stayed highest, he still hears it. Where the
calibration was deliberately left byte-identical, nothing changed.** That is the first quantified
on-car prediction in this kit's history and it held. ⚠ **EVIDENCE for the duty numbers and for his
report; BELIEF that the mapping is causal** — one build, no rlogs, and no matched control.

### WHAT THIS SAYS ABOUT THE REMAINING SYMPTOMS
- **The residual grinding sits exactly where V108's rail duty is still highest** (the 10–25 km/h bin, up
  to 15.46 %). **It is the same defect, under-dosed, not a different one.**
- ⭐ **His "two modes, ~100 Hz and something significantly higher" is precisely what V109's α2 targets:**
  −34 % at 100 Hz, −39 % at 200 Hz, for 8 % at the 21 Hz mode and **0 % at manoeuvre frequencies.**
- **The low-speed steering-rate limit is the same railed-damper DC drag** (`sign(α)·511` = 10.7 % of the
  governor ceiling), and it is worst exactly where duty is highest. V109 attacks it without costing
  manoeuvre-band authority.
- ⚠ **The 60–65 mph vibration is probably NOT ours.** At 96–105 km/h the rail duty is **≤0.03 %**, and
  that regime is **byte-identical between V107 and V108** — so a firmware change cannot explain a change
  there. Inconsistent, whole-vehicle and speed-specific fits road surface or a wheel order. **His own
  instinct was right and is recorded as such.**

⇒ **V109 IS THE NEXT BUILD, and now for a measured reason rather than a structural one.**

### 🛑🛑 CORRECTED — **V109 AND V111 DRIVE IDENTICALLY.** THE CHOICE IS THE INSTRUMENT, NOT THE FIX.
⚠ **Earlier in this session I repeatedly recommended "V109 first, then V111". That framing was
WRONG** and is corrected here. They are not a sequence of fixes.
```
  V108 -> V109 :  0xC40DC  16 -> 0e                        1 payload byte  + CRC
  V109 -> V111 :  0x55DF2  d493 -> 4495 ; 0x55E10 a5 -> a3  3 payload bytes + CRC
  V108 -> V111 :  all three of the above                    3 payload bytes + CRC
```
**Every dynamics cell is byte-identical on V109 and V111** — verified from the images:
`0xC40DC` (α2) **14 on both**, `0xC40BC` knee 600, `0xC6CD0` gain 5346, `0xD7A5C` `gp-0x6b26` row,
`0xC60A8` biquad. **V111 IS V109 plus three telemetry bytes.**

⇒ **The decision is which MEASUREMENT the drive buys, not which fix is on the car:**

| build | 427 tap watches | what it answers |
|---|---|---|
| **V109** | `gp-0x6c2c`, sar 5 | sizes the `gp-0x6b26` Y row — open since V107 |
| **V111** | `gp-0x6abc`, sar 3 | **the relay's input amplitude** |

⭐⭐ **RECOMMEND V111 OVER V109 FOR A SINGLE DRIVE**, and GATE 2 is the reason: the knee lever only
bites **below ~200–400 counts** of `|gp-0x6abc|` (describing-function ratio **0.96–0.99** above ~400,
i.e. a knee raise does essentially nothing there). **That amplitude decides whether the ratchet lever
exists at all, and whether the ~1.28:1 trade is even on the table.** The Y-row question is worth less
than that now. ⊕ **Both builds deliver the identical α2 test** on the low-speed grinding, so nothing
about the fix is given up by choosing V111.
⚠ What IS given up: the `gp-0x6c2c` channel goes dark, so the Y-row solve waits for another drive.

### 🛑🛑 KNEE CORRECTION — **`0xC40BC` STOCK IS 600, NOT 300**
⚠ Stated wrong repeatedly this session. From the images: **STOCK 600** → V85 6000 → V87 600 →
**V99 300** → nine builds at 300 (V99–V107) → **V108 600**. ⇒ **V108’s edit was a REVERT to
Honda’s own value**, and for nine builds the relay saturated at **half** Honda’s threshold
(5.3 °/s instead of 10.6). ⭐ **That gives V108’s “best it’s ever been at ≥20 mph” a candidate
cause that is a revert, not an invention** — still unattributed (V108 moved four cells), but the
only one of the four that restores a Honda value the kit had overridden for nine builds.
🛑 **And it reframes the lever: raising above 600 EXCEEDS Honda’s setting.**

### ✅ V111 BUILT — THE RELAY PROBE.  3 PAYLOAD BYTES, NO CAVE EDIT, NO DOSE.
```
builder  analysis-2020accord/builds/v108_plus/build_v111_tva.py   36/36   BASE = V109
image    9c4865cffd337cfb5d27f66843edbff928a8ffbf6f365e4fdeb7e98f7ddfb546
.rwd     221d99c605d2d9d9f86b0788ba6f46621d9738b5b2f5d866ac2b31a81e63f42e
0x55DF2  d4 93 -> 44 95    CAN-427 tap source  gp-0x6c2c -> gp-0x6abc  (THE RELAY INPUT)
0x55E10  a5    -> a3       sar 5 -> sar 3
3 payload bytes + 1 CRC trailer.  ZERO unattributed vs V109.
```
🛑 **IT CHANGES NO DYNAMICS CELL.** The relay knee, K1, the relay offset, alpha2, the 6× gain, the
biquad and all four `gp-0x6b26` mode rows are asserted **byte-identical to V109**. The 164-byte cave
is asserted byte-identical too, so every carried rung still means what routes `a5`/`a6`/`1e` measured.
**No cave edit ⇒ outside this kit's only bricking class.**

**WHAT IT MEASURES.** The full distribution of `|gp-0x6abc|` — the Coulomb relay's input — on the wire
at 49.8 Hz, from which the relay's saturation duty at **any** candidate knee is computed post-hoc.
```
  (wire >= 31) AND NOT (wire >= 125)  ==  EXACTLY the population a knee 600 -> 2400 raise affects
```
Sizing at sar 3: peak 913/1023 (no ceiling), 1 count = 0.340 °/s, knee-600 lands at 31 counts and
knee-2400 at 125. sar 2 would saturate. **Sized against a measured distribution** (the sibling
`gp-0x6ac0` peaks at 1462 ct), not a guess.
⭐ **If that duty is near zero where the operator feels the symptom, the knee lever is dead and no
assist was ever spent.** The null is interpretable — which is why this is a probe and not a dose.

🛑 **FLIGHT ORDER: V109 FIRST, THEN V111.** V109's tap still watches `gp-0x6c2c`, which V108's E5
added specifically so the next drive could solve the `gp-0x6b26` Y row — open since V107.
**Re-pointing the tap costs that solve.** V111 is the build AFTER V109, not instead of it.
⊕ The tap re-point is a **proven** mechanism: V107 made exactly this edit at exactly these two
addresses and flew fault-free as routes `1b`/`1e`; V108 then moved only the shift. Third use.

⚠ **A guard caught a real defect during the build.** The inherited `V106B.assert_frozen` asserts
V106's expected values, and V107 (tap), V108 (knee, sar) and V109 (alpha2) have legitimately moved
four of them since — so it failed on correct edits. **Rebased to the V109-RELATIVE form**: every
kit-frozen cell must equal THE BASE, with only the two deliberately-edited addresses exempt. That is
both correct and stronger. 🛑 **Any future builder inheriting `V106B.FROZEN` has the same latent
bug** — the table is three builds stale.

### 🛑⭐ THE ACOUSTIC COST OF THE GAIN IS MEASURED — **+1.16 dB from 4× to 6×**
Full note: `memory/accord/mechanism/accord-the-acoustic-cost-of-the-gain-is-measured.md`.
Eleven-route audio spectrogram ladder built this session (`rlog-tools/decode/extract_route_audio.py`),
**with a STOCK arm**. Statistic = **MECH (60–400 Hz) − FAR (1200–2000 Hz)**, engaged-minus-manual,
matched speed <10 mph, hands-off, within drive.
```
  gain   n     MECH     FAR   MECH-FAR        6x - 4x = +1.158 dB
   1x    1    +0.01   +0.74     -0.73                   [+0.475, +1.817]
   4x    3    +0.36   +1.16     -0.80                   P(>0) = 1.000
   6x    6    +0.95   +0.58     +0.36         8 of 9 routes outside their own null
   8x    1    +2.01   +0.39     +1.62         n=1 for stock and 8x -- not tested levels
```
🛑 **FAR IS NOT OPTIONAL** — it rises too (+0.74 on stock, +1.16 at 4×), which proves the engaged
and manual segments differ in ways that lift the WHOLE spectrum. **Every single-band
engaged-minus-manual claim on this corpus is confounded by that**, and that is exactly how three
earlier framings died today.
⇒ **The 6× costs ~1.2 dB of steering-band cabin noise over 4×. Goals #1 and #4 are in tension
THROUGH THE GAIN ITSELF, and the tension is now numeric.** ⊕ Independently consistent with
`accord-the-8x-gain-is-the-carrier`, reached from the 20–26 Hz steering-rate band — two unrelated
instruments, same conclusion. 🛑 **It is a PRICE, not a prescription**: the operator wants 6×, and
`accord-4x-lkas-gain-is-the-frozen-variable` warns against recommending a gain cut.

❌ **THREE FRAMINGS DIED GETTING HERE, ALL THE SAME ERROR** — a narrow-band acoustic claim with no
adjacent-band control: *"the ≈100 Hz mode is ours"* (controls rise equally; residual ≤ 0 on 6 of 10),
*"an 83.5 Hz comb is the grinding"* (**stock fires too**; the comb estimator has a sub-harmonic
ambiguity), and *"PMSM 6th/12th torque ripple"* (decisively excluded — an order moves 40× across the
rate span, the centroid moves 1.04×).
⭐ **RULE, and the steering-rate work already followed it:** a narrow-band acoustic claim needs
**adjacent control bands**, and an *"it is ours"* claim needs the **STOCK arm BEFORE publishing.**

🛑 **V109's ENDPOINT, RESTATED:** score V109 against V108 on **MECH − FAR**, same road, same driver.
Not a comb, not a single band. ⚠ And V109's α2 cut is band-limited to 61–300 Hz while the excess is
broadband over 60–400 Hz — **it is NOT "aimed squarely" at this**, and the note claiming so was
corrected. **The V109 drive MUST capture audio** or the endpoint is unmeasurable.

### ⭐⭐ THE COMMAND GATE SURVIVED ITS 2-D CONTROL — AND THE RELAY IS NOW **LOCATED IN THE CODE**
**Control first** (the one that killed three other findings today): command and steering rate are
correlated engaged, and the ratchet's rate-dependence is already known, so the command gate had to be
separated from it. 2-D cells, <20 mph, engaged, hands-off, 1058 windows, 6-9/1-3 band shape:
```
                rms<8      8-20 deg/s    20-45
  cmd <1k     0.50(493)    0.93(302)   1.39(83)
  cmd 1-2k        -        1.13( 50)   3.87(32)
  cmd 2-3k        -        4.72( 23)   1.70(22)
  cmd 3k+         -       44.71( 36)   4.33(17)
```
⭐ **At MATCHED rate (8–20 °/s) command drives a 48× fold; at matched command, rate drives only 2.8×.**
⇒ **genuinely command-gated, NOT the known rate effect.** The `3k+ / 8–20 °/s` cell — maximum command,
wheel barely moving, 45× the 7.8 Hz content — is the ratcheting isolated.

**And the mechanism is now located**, `FUN_0003b8f6` @`0x3B8F6` (full arithmetic in
`memory/accord/mechanism/accord-the-coulomb-relay-is-located-c40bc-is-its-knee.md`):
```
fVar13   = clamp( POL * gp-0x6abc * 12 / cal(0xC40BC), -1.0, +1.0 )   <-- THE RELAY
friction = EMA( |model| * cal(0xC40D2)/1024 * fVar13 + cal(0xC4080)/1024 * fVar13 )
gp-0x6ae2 = friction * 1024 ;  iVar20 = (model - friction - inertia) * gain
```
⇒ **magnitude ← `|model|` (tracks COMMAND); shape ← rate against the KNEE.** The two factors of the
product map onto the two axes of the measurement. Saturates at `|gp-0x6abc| >= knee/12`:
300 → 25, 600 → 50. 🛑 **600 is STOCK** — V99 halved it to 300 and it stayed there for NINE
builds (V99–V107); **V108 RESTORED Honda's value.** The operator called
≥20 mph *"the best it's ever been"* — ⚠ unattributed (V108 moved four cells), but it is the only one
that touches the relay.

🛑 **THE COST, BEFORE ANY DOSE:** `clamp(x/knee, ±1)` is **monotonically decreasing in the knee**, and
`accord-friction-polarity-more-assist` is verified nine ways — **more modelled friction = MORE assist**
⇒ **raising the knee REDUCES ASSIST**, trading directly against the 6× goal, in the same direction that
made V93/V94 unsafe. **Do not propose a knee dose until the assist cost is priced in counts.**
🛑 **CRUX, NOT YET VERIFIED: the scale of `gp-0x6abc`.** If it shares the 4.7121 ct/(°/s) column-rate
scale, V108's knee saturates at **~10.6 °/s — inside the 8–20 °/s band where the ratchet was isolated.**
`gp-0x6abc` is a DIFFERENT cell from `gp-0x6ac0`; the scale must be measured, not assumed.
⊕ **An instrument already exists**: `gp-0x6ae2` is the friction output and V106's `b5` rung compares
`|gp-0x6ae2|` against `|gp-0x6b26|`. A knee dose would fly with telemetry on it from day one.

### 🛑🛑 RETRACTED — "THE GAIN STOPS DELIVERING AT LOW SPEED" DOES NOT SURVIVE SPEED-MATCHING
⚠ **I told the operator twice that the data backed his perception. Properly controlled it does not —
and it does not contradict him either.** With **2 mph speed cells** (not a wide `<15 mph` bin) ×
`|cmd| >= 3072`, hands-off, route bootstrap on both arms, ideal 1.500:
```
  <=15 mph   1.292  [0.925, 1.673]   P(<1.500)=0.860   <- 1.500 is INSIDE
  >=15 mph   1.858  [1.387, 2.485]
  CONTRAST   0.711  [0.451, 1.032]   P(<1)=0.963       <- CONTAINS 1
```
**Nothing survives at 95 %.** The earlier 1.030 came from a speed mismatch inside the bin — median
speed within `<15 mph` was **6.2 mph (4×) vs 8.3 mph (6×)**, and acceleration varies strongly across
that range. 🛑 **RULE: match speed in cells <= 2 mph for any cross-build contrast on this corpus;
a `<15 mph` bin is NOT a speed control.**
⇒ **UNDERPOWERED, NOT REFUTED** — the 6× arm carries only 5–15 s per cell and the interval is 1.8×
wide. Closing it needs deliberate matched hands-off low-speed segments at large command, on both a
4× and a 6× build, on the same road.
✅ **UNAFFECTED and still standing:** the ratchet/grind **command gate** (a within-window band contrast
with its own internal controls — two control bands FALL while 6–9 Hz rises 3–4.7×); the hands-off
lesson; the E3 reconciliation (rate is an integral, so a rate test is blind to a torque ceiling, and
pulling `0xC61BE` was correct); and the refutation of stick-slip.

#### ⚠ SUPERSEDED, kept for the audit trail — the original claim
He pushed back on the `STEER_MAX` answer: *"I'm looking for a more structural limitation… one that does
not scale with the 6x LKAS gain… it feels like the max angular velocity has not scaled 6x."* **Tested
and confirmed.** `rlog-tools/studies/authority/gain_delivery_and_command_gate.py`; notes
`accord-gain-stops-delivering-at-low-speed-high-command` + `accord-ratchet-and-grind-are-command-gated-saturation`.

**Instrument:** angular acceleration in the commanded direction ∝ NET TORQUE at the instant. Ladder read
from the images (`0xC6CD0` 891/3564/5346/7128 = 1×/4×/6×/8×), build per route from `probe_build`.
Route-level p90, route bootstrap. **Ideal = 1.500.**
```
  ALL speeds, cmd>=3000    1.429 [1.134, 1.737]   <- the gain DOES reach the motor
  <15 mph,    cmd>=2048    1.030 [0.694, 1.499]   <- it does NOT, here
  15-45 mph,  cmd>=2048    1.814 [1.276, 2.522]   <- full delivery
  RATIO-OF-RATIOS          0.557 [0.359, 0.909]   P(low<high) = 0.992
```
🛑 **AND A CORRECTION MADE MID-ANALYSIS:** the first pass omitted the hands-off mask and returned
*"the gain scales NOWHERE"* (0.948 [0.748,1.182], no knee in any command bin). **That was the DRIVER** —
at low speed his hands move the wheel and his torque swamps LKAS. D3 flipped the low-command bins to
~1.50. ⭐ **Any cross-build torque or rate comparison at low speed is meaningless without a hands-off mask.**

⭐⭐ **AND THE RATCHET RIDES THE SAME GATE — this is the ratcheting answer.** Band SHAPE (power
normalised by 1–3 Hz in the same window), <20 mph, engaged, hands-off:
```
  fold-rise vs <1k cmd    3-5 ctl   6-9 RATCHET   10-13 ctl   14-18 ctl   20-26 grind
  1k-2k                      0.7x         3.0x        0.7x        1.1x          4.0x
  2k-3k                      0.6x         4.7x        0.7x        1.1x          5.7x
  3k+                        1.9x        52.0x        3.3x       12.7x         11.8x
```
**Two control bands FALL while 6–9 Hz rises 3–4.7×.** A cornering confound lifts every band; this does
the opposite. ⇒ **the ratcheting is SWITCHED ON by command magnitude — not a passively-excited
resonance** — and the 20–26 Hz grind rides the same axis.
⇒ 🛑 **[BELIEF, strongly supported] ONE saturating nonlinearity produces both symptoms**, in the same
regime where extra gain stops buying torque. **Sixty builds hunted a LINEAR lever (a pole, a damper, a
gain) for a COMMAND-TRIGGERED nonlinearity. A linear lever cannot fix a relay.** The target is the
saturating element: raise its ceiling or soften its corner.

**EXCLUDED already:** `0xC520C` (rate-indexed, first knot 222.8 °/s, struck by its own author) and the
forward clamps `0xC61B2`/`B4` (**they scale exactly with the gain** — 512/2048/3072/4096 for 1×/4×/6×/8×,
byte-verified V96→V110). **Still open:** the governor's vehicle-speed read (`0xC6316` ≈10 km/h); a shared
base-assist+LKAS sum Honda's own curve already fills at low speed; or — not a lever — the **motor current
limit**, since tyre scrub is highest at low speed. ⇒ **The discriminator is a delivered-torque or
motor-current channel, which the corpus does not carry cleanly across the 4×/6× builds** (CAN 427 was
repointed for probe use from V88 on). **That is the next telemetry to buy.**

### 🛑🛑 GOAL #5 IS ANSWERED, AND THE ANSWER IS NOT IN THE FIRMWARE
**The low-speed steering-rate limit is COMMAND SATURATION at openpilot's `STEER_MAX` = 4096.**
Measured 2026-08-27 from caches already on disk; reproducible via
`rlog-tools/studies/authority/steer_max_saturation.py`. Full note:
`memory/accord/mechanism/accord-low-speed-rate-limit-is-openpilot-steer-max.md`.

**The clamp is real** — `|e4tq|` histogram approaching its edge on r77 engaged decays smoothly
`832 / 903 / 394 / 183 / 112 / 34 / 25 / 3` and then **spikes to 13,783 at exactly 4096**, with
**zero frames above 4096 in ~200 cache files across the whole corpus.**

**It binds exactly where he feels it** — duty of `|e4tq| ≥ 4096` while engaged:
```
  band     r77      ra6      r1e          <-- "below ten mph the max angular velocity
  <6 mph  0.4036   0.3099   0.0745            is still limited"  ... and ...
  6-10    0.3697   0.2100   0.0684        <-- "twenty and above is the best it has ever been"
  10-15   0.2146   0.0889   0.0615
  15-20   0.0965   0.1458   0.0521
  20-30   0.0323   0.0274   0.0503
  30-45   0.0028   0.0000   0.0087
  45+     0.0000   0.0000   0.0021
```

**And the car is NOT the limit.** Achieved rate in the commanded direction keeps **climbing** through
the rail (r77 p90 `66.8 → 78.9 → 93.9 → 143.6`), and the **driver slews the same rack 3–4× faster**
(p90 103–162, max 402–459 °/s). ⇒ **plant headroom exists; openpilot ran out of command.**

⇒ 🛑 **NO FIRMWARE CALIBRATION CAN RAISE IT.** The 6× gain multiplies what arrives; pinned at 4096,
the firmware is already delivering 6× of the most openpilot can ask. The only two routes to more
low-speed rate are **(1) raise `STEER_MAX` openpilot-side — the operator's call, and
`feedback-no-openpilot-side-modifications` says we do not touch it**, or **(2) push the firmware gain
above 6×, which is the measured carrier of the grinding.**
⇒ **Goal #5 and goals #1–3 are in DIRECT TENSION and the binding constraint sits OUTSIDE the
firmware.** This is why the symptom survived every build — **none of them could have moved it.**

✅ **Retired in the same pass:** the `gp-0x69b0` authority ramp. All five rate cals mapped
(`0xC63F4/F6/F8/FA/FC` = 328/16/33/66/328, two up + three down, all stock and virgin), and the
pre-registered test returned its null — **STEER_STATUS is identically 0 across 3,312 s engaged on four
routes, every speed band, zero transitions**, with the control passing (status 3 exists, only at
0.0 mph and only disengaged). The ramp reaches full scale ~1 s after engagement and holds.
🛑 **And a correction:** the record files `0xC63F8`=33 vs `0xC63FC`=328 as a *"10× LEFT/RIGHT
asymmetry"* and deprioritised it on a left/right null. **`gp-0x6803` is a MODE fork, not a direction
flag** — three values, two parallel SM chains (1→3→2 vs 1→6→7). Right answer, wrong reason; do not let
a future session revive the cals on "left/right was never the issue".

### 🛑 V110 IS DEAD — TWO INDEPENDENT KILLS, and the second one closes the whole Kd lever
`Re(Z)` **is** already measured to 35 Hz **with phase** on route 77 (`rlog-tools/studies/impedance/v92_rez_extend.py`,
89,471 frames / 884.5 s engaged hands-off, 221 windows, all ten bands passing a pre-declared
coh² ≥ 0.10 AND ≥ 5× shuffled gate). **There is no separate `G_bar(f)` unknown — the measured `arg Z(f)`
already contains the whole rotation, plant included.** The disputed memory's numbers reproduce from it
**to within 4 %** via `Re(Z)_branch = |Z|·|H|·cos(argZ + argH)`.
**And the sign reverses, convention-free:** `cos(argZ + argH_D)` = **−0.802 at 7.79 Hz** but **+0.894 at
20 Hz** ⇒ **D PUMPS at 7.8 Hz and DAMPS at 18–22 Hz.** Halving Kd would remove damping in **20–40 mph —
the exact regime the operator just called the best it has ever been.**
⭐ **And 18–22 Hz is the BEST-CONDITIONED band in the whole sweep** — episode-parity split-half agrees to
**2 % (r77), 1 % (r78), 15 % (r79)**. The conclusion rests on the most reliable band available.
⭐ **Now replicated on THREE drives** (628 windows / 74 episodes / 2145 s engaged hands-off): pooled
`d = −0.2303 [−0.2411, −0.2125]` at 18–22 Hz, **−0.236 / −0.208 / −0.224 per drive**, P(damping) = 1.000.
Halving Kd would remove **Δd = +0.1151**. At 26–31 Hz `d = −0.3049`, Δd = **+0.1525** — ⚠ heterogeneous
(r79 is neutral at −0.0072), so the honest claim there is *"never helps"*, not a magnitude.
⭐ **And it is robust in a way a single skew cannot defeat:** 18–22 Hz needs a channel skew ≥ **+8.6 ms**
to flip, 26–31 Hz needs ≤ **−5.9 ms** — **OPPOSITE DIRECTIONS.** No single skew, and no torque-channel
low-pass at any corner from 6 Hz to ∞, makes D pump in both grinding bands. The normalised `d` depends
**only on `arg Z(f)`**, so every magnitude error — plant, the `rate_f` 0.7996 scale — cancels exactly.
⚠ The one honest residual: pooled `arg Z` falls at **−7.80 deg/Hz** over 16–35 Hz, which *if it were all
instrument delay* would be 21.7 ms and would flip 18–22. It is probably not delay — the phase **rises**
+30° from 3 → 7.79 Hz first, and a delay can only make phase fall — but it cannot be decomposed from the
bus. Closing it needs an on-car gain-step system ID at 18–31 Hz.
⊕ Crossover, pooled: **24.97 Hz [24.48, 25.35]**; per drive 25.40 / 24.07 / 23.97 ⇒ quote the
between-drive spread **24.0–25.4 Hz**, since the per-drive bootstrap CIs do not overlap.

#### 🛑🛑 KILL 2 — V110 IS NOT "Kd 2048→1024". IT IS **ONE KNOT OF A FOUR-KNOT LERP.**
Independent of the sign, and **orchestrator-confirmed from the images and the decompile, not relayed.**
Byte diff V109→V110 is 5 bytes: `0xC6AE7 08→04` plus the CRC trailer. **`0xC6AE8`/`EA`/`EC` all remain
2048.** Decompile of `0x3A382`:
```
axis = gp-0x6ac0                                  # motor / resolver rate
X = (50, 400, 1500, 3000) @ 0xC6ADE/E0/E2/E4      # 0xC6ADE is X[0], NOT a separate gate cal
Y = (Y0, Y1,  Y2,   Y3 )  @ 0xC6AE6/E8/EA/EC
  axis <=   50 -> Y0 alone          <-- the ONLY place V110's edit acts alone
  50 ..   400  -> LERP(Y0, Y1)      <-- ramps out against a still-stock Y1 = 2048
  400 ..  1500 -> LERP(Y1, Y2)      <-- the edit is NEVER READ at or above axis 400
  1500 .. 3000 -> LERP(Y2, Y3);  axis >= 3000 -> Y3
enable: axis < 0x32C9 (12,993)     =>  the edit touches the bottom ~0.4 % of the axis
```
⭐ **AND THAT IS WORSE THAN INERT.** Stock Y is **flat 2048 at all four knots**, so the LERP is
currently a **constant**. A one-knot edit does not reduce a gain — it **converts a constant into a
rate-dependent function**, introducing a nonlinearity that does not currently exist, at 2× the
oscillation frequency, inside a loop already known to be marginally stable. Describing-function
territory, not a linear gain cut. ⇒ **On a flat table, a one-knot edit is never a gain change.**

⇒ **THE KD LEVER IS CLOSED, NOT JUST V110.** The correct four-knot form — which
`docs/review/GATE2-2026-08-11-cbe74-independent.md:150` already recommended — is precisely what makes
KILL 1's cost real. **Do not rebuild it properly.** V110's builder docstring has been corrected in
place and the artifact stays on disk, parked, as the audit trail.

#### 🛑 THE GATE-1 LESSON — add it to the gate
V110's census said *"one reader (`0x3A460`), zero writers"*. **That is TRUE OF THE BYTES and FALSE OF
THE LEVER**: Y0 is also reached through a **walked pointer** (`puVar11++`), the register-indirect form
that operand-text search structurally cannot see. ⇒ **A GATE-1 census that counts ACCESSES to a cal
cell cannot tell you whether the cell is a scalar or one knot of a table — that requires reading the
READER'S STRUCTURE.** This is the same blind spot as `accord-gp4f60-two-encodings-enumeration-trap`,
in a new costume.

⇒ **V110 stays parked permanently.** My rejection of the "no computation behind it" refutation was
correct, and it is now proven rather than merely plausible — but the build it was defending is dead
anyway, for a reason that had nothing to do with the sign.
⊕ **A method note worth keeping:** the 500-draw phase-randomised surrogate gives |z| ≈ 1 on `d`, and
that is **NOT a failed control** — a random-phase null is the *wrong null* for `d`, which is a bounded
arcsine quantity whose null is "phase is uniform". The correct uncertainty is the **episode bootstrap
on the phase: ±5–6° against a 62° flip threshold.** Do not later read that z≈1 row as a refutation.

#### THE FULL D-ROTATION COST LADDER, and where the argument is weakest
```
   band     d pooled   Δd on halving Kd   cost vs the +0.0389 ratchet benefit   flips at
   6-9      +0.0779      -0.0389 (help)          --                        tau -18.7 ms
   16-18    -0.1129      +0.0565                1.45x        ⚠ tau +5.2 ms, LP fc 27.3 Hz
   18-22    -0.2303      +0.1151                2.96x           tau +8.6 ms, LP fc 10.8 Hz
   22-26    -0.2898      +0.1449                3.72x           tau +9.3 ms, LP fc  4.1 Hz
   26-31    -0.3049      +0.1525                3.92x           tau -5.9 ms, NO LP possible
   31-35    -0.1124      +0.0562                1.44x           tau -1.3 ms
```
⚠ **16–18 Hz is the weakest link in the sweep** — it flips on only **+5.2 ms** of skew or a 27 Hz
low-pass. **If the channel-defect argument is ever reopened, that is the band it will be won in, not
18–22.** ⊕ **22–26 Hz is the most consistent band measured** (−0.2879 / −0.2993 / −0.2892 across three
drives) and is where the crossover sits. 31–35 Hz is heterogeneous — do not lean on it.

### 🛑 NAMING CORRECTION — the `Re(Z)` instrument is **bar torque ÷ MOTOR rate**
The kit calls it a *"driving-point impedance"* throughout. It is not one. `0x18F[2:4]` STEER_ANGLE_RATE
is **not independently sensed** — per `accord-gp6a56-is-motor-rate-not-an-angle-sensor` it is a fixed
Q15 scale of `gp-0x6abe`, the **motor resolver electrical rate**. So `Z = tq / rate_f` is
**torsion-bar torque ÷ motor rate.** ⚠ This is true of the **whole instrument — the 7.79 Hz anchor and
the `mean(T·ω)` sign anchor included** — not just the 16–35 Hz extension, so **it changes no comparison
and no verdict.** But the name is doing work it has not earned, and a future agent reading
"driving-point impedance" will assume a column-side measurement that was never made.

### 🛑 OPEN — one cave bit would settle "V110 inert" vs "V110 injects a nonlinearity"
`gp-0x6ac0`, the Kd/Ki/Kp LERP axis, is the resolver/FOC electrical rate. Its **duty below 50 and below
400** is exactly what separates the two readings, and **it is not on disk**: no cache carries
`gp-0x6ac0`, and the adjacent `g6ac2` field is a **single BACKDRIVE bit** (`extract_r67_v81.py:266`),
constant 1.0 on r77 and a **stale decode on V100+ routes**. The `rate_f → gp-0x6ac0` scale is also
unknown, so even the shape would not give an absolute.
⇒ **Two comparator rungs — `axis < 50` and `axis < 400` — give the duty directly.** Cheap, and it is
the difference between *"V110 does nothing"* and *"V110 modulates Kd at 2× the oscillation frequency"*.
⚠ **It does not reopen V110** — KILL 1 stands either way. Worth one bit the next time a cave is cut,
because the same axis gates Ki and Kp.

### ✅ THE THREE V36-BLANKED CELLS ARE CLOSED — benign, correctly in force, and NOT a lever
`0xC61C0` = **1600**, `0xC61C2` = **896**, `0xC61C4` = **1280** in stock; all three **`0xFFFF` since V36**
and byte-identical through V110. **12 reads, 0 writers**, exactly as flagged — four each in
`FUN_00028ea6` and `FUN_0002a30e`, all `ld.hu`, implementing one **4-tier OR-envelope**:
```
   torque > cal(0xC64B4)=112 (rise) / 0xC64B5=96 (hold)          [torque alone]
     OR  rate > cal(0xC61C0)=1600                                 [rate alone]
     OR (torque > 0xC64B7=64  AND rate > 0xC61C2=896)             [combined A]
     OR (torque > 0xC64B6=54  AND rate > 0xC61C4=1280)            [combined B]
   -> 5 consecutive qualifying cycles (cal(0xC64E2)=5) -> STEER_STATUS = 4
```
⇒ **`0xFFFF` disables the three RATE arms, leaving the torque-alone arm.** This is exactly the
gentle-EME fix the record describes, **validated on-car by V37 (2026-07-14) and correctly still in
force.** ⚠ **NOT a lever for anything currently being chased**: it is a level-threshold + 5-cycle
debounce, so **it cannot produce an in-band oscillation by construction**; it watches different signals
from the ratchet's `gp-0x6b26`/`gp-0x6c2c` path; and when it fires it writes **three status bytes and
nothing in the torque chain.** Max steering rate is `0xC61BE`, a different cell (byte-stock through
V110). **Do not touch these.**

⭐ **AND IT CLOSED A MUCH OLDER QUESTION.** The record's long-standing *"the actual assist-reduction
instruction during the felt cut is still unlocated"* (2026-07-14) is at least partly answered:
`STEER_STATUS` outside {0,1,2} **blocks an increment of `gp-0x69b0` and a state advance** — a real
gating effect, not a report:
```
   0x2a55a  ld.bu -0x6807,gp,r14        ; STEER_STATUS
   0x2a56a  jr 0x2a890                  ; 3,4,5,6,7 -> BAIL
   0x2a572  ld.hu 0x73f8,tp,r14         ; else cal(0xC63F8) = 33
   0x2a588  st.h  r11,-0x69b0,gp        ; gp-0x69b0 += 33
```
Since `gp-0x69b0` is the **Q15 multiplier gating the whole LKAS block** (established separately this
session, `0x2A1E6 mul r14,r9,r0`), **the felt cut is not a hard zero — it is a STALLED RAMP**, which
fits "gentle" far better than a hard cut and is consistent with V37 having fixed it on-car.
⚠ **BELIEF** — the `gp-0x69b0`→motor chain was not re-traced in that pass.

🛑 **AND THE UNDERCOUNTING TRAP REPRODUCED CONCRETELY, WITH A NEW CAUSE.** `FUN_0002a30e`'s Ghidra body
**stops at `0x2A507`** (a `dispose` epilogue on one exit path mis-detected as the function end), but the
code continues contiguously to at least **`0x2A8A6`**. `get_function_by_address` returns *"No function
found"* for that whole region ⇒ **`search_instructions` found 32 reads of `gp-0x6807` where a raw byte
scan found 40. Eight real reads were invisible.** ⭐ **Code that is disassemblable but NOT
function-bound is invisible to `search_instructions`** — that is the mechanism behind this trap, stated
concretely for the first time. ⊕ `get_bulk_xrefs` gave its false *"no references"* a **fifth** time.

### 🛑 A MEASUREMENT-DISCIPLINE FINDING ONE LEVEL UP FROM THE STANDING RULE
Crossover frequency (`Re(Z)` = 0), episode-bootstrapped per drive:
**r77 25.40 [24.93, 25.72] · r78 24.07 [23.67, 24.30] · r79 23.97 [23.81, 24.17].**
🛑 **The three per-drive CIs DO NOT OVERLAP**, and the between-drive spread is **~4× the within-drive
CI.** ⇒ **the episode bootstrap UNDERSTATES the real uncertainty.** Quote the between-drive spread
wherever it is larger. This is `feedback-episodes-not-windows` one level up: **episodes are not
independent across drives either.**
⊕ **And the manual hands-off arm still does not exist**: pooled over r77/r78/r79 it is **2 windows /
21.4 s**, unchanged since 2026-08-11 — r78's 27.6 s and r79's 13.3 s are too fragmented to yield a
single 5.12 s window. **The manual hands-off coast experiment is still owed.**

---

## ⚠ SUPERSEDED BLOCK, 2026-08-27 (build session) — **V107 FLEW AND THE DAMPER IS A COULOMB RELAY · V108 IS THE FIRST SUBTRACTIVE BUILD IN THIS ARC**

🛑 **ON THE CAR: V107** (routes `1b` 35.8 s and `1e` 988.6 s engaged, both fault-free).
**V108 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS, no SSH.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-27-v107-flew-the-damper-is-a-relay.md`** — 16 retractions,
14 open items with what closes each, the V108 drive card, and the V109 lever already priced and gated.
```
V108 image  7a9577dd181a235845e87e592fbd1a191957674aef7b0f17caac6907c114a9e4
V108 .rwd   4fbfda0d76af2f1b592bd9e510cd926dbfabb6a02b7a25730e7018f07cf4c4d1
builder     analysis-2020accord/builds/v108_plus/build_v108_tva.py   54/54 assertions   BASE = V107
E1  0xC60A8..B7  V105's 25.5 Hz notch -> HONDA'S OWN 16 BYTES (copied, never typed).  Arm KEPT.
E2  0xD7A5C/6C   Y (-29490,-24000,-16000) -> (-29490,-17202,-16000)   V106's Y0+Y1, V107's Y2
E4  0xC40BC      300 -> 600 (Honda)
E5  0x55E10      sar 3 -> sar 5    (the tap was sized against a 5x arithmetic error)
E3  0xC61BE      BUILT AT 16384, THEN **PULLED** ON ITS OWN PRE-REGISTERED NULL.  Byte-stock.
31 bytes vs V107 in 11 runs, ZERO unattributed.  CAL-ONLY.  THE CAVE IS BYTE-IDENTICAL TO V107.
```



### 🛑🛑 THE VISIBLE OSCILLATION IS **OPENPILOT'S WEAVE**, NOT THE EPS — AND IT IS A SEPARATE DEFECT
Route `1e`, 998.9 s engaged / 338.6 s manual, 10 episodes. Full note:
`memory/accord/mechanism/accord-visible-oscillation-is-openpilots-weave.md`.
**46 events covering 17.3 % of engaged time, up to 24.02° p2p = 77.6 mm at the rim, at 0.44–2.93 Hz.**
🛑 **His "under or around 10 Hz" is really 0.4–1.6 Hz — above 4 Hz the angle NEVER reaches a centimetre
on any engaged window (4–6.3 Hz max 4.3 mm; 6.3–10 Hz max 3.6 mm).** Every earlier search scanned
4–10 Hz and was structurally incapable of finding it.
```
  angle phase vs COMMAND   all 46: +46.8 deg [+29.4,+71.3] R=0.581, angle LAGS in 72 %
                     near-straight: +63.3 deg              R=0.740, angle LAGS in 85 %
                     1.0-1.6 Hz median lag +0.088 s  <- sits on steerActuatorDelay = 0.100 s
  angle phase vs DRIVER TORQUE   -63.2 deg [-88.1,-24.8]  => the HANDS REACT to the wheel
  car follows the wheel kinematically in EVERY event (yaw/prediction p50 1.17, range 0.73-1.61)
  engaged/manual angle PSD, speed-stratified, 0.4-3.5 Hz:  0.022-0.21  => engaged is 5-45x QUIETER
```
⇒ **[BELIEF, strongly supported] a limit cycle in openpilot's own lateral loop.** The EPS-originated
signature (angle leading command) is a **28 % minority** with the pooled CI excluding zero on the wrong
side, the car yaws with the wheel every time (excluding a column/rack torsional mode), and the driver's
hands lag. ⭐ **It explains why sixty firmware builds never moved it: there was never a firmware lever
on it.** 🛑 `feedback-no-openpilot-side-modifications` is standing — **the operator's call, not ours.**
🛑 **AND IT IS NOT THE GRINDING.** Inside events vs speed-matched engaged baseline: rail duty **1.01
[0.88, 1.22]**, audio 100 Hz–2 kHz **+0.50 dB [−1.18, +2.54]** against a control spread of [−6.2, +7.9].
**Two independent defects; V109 and any successor must target them separately.**
⚠ **The one thing that could change it:** manual exposure above 24 km/h on `1e` is **35.8 s total**, so
the >24 km/h rate ratios rest on 0–2 manual events and the stratified PSD only has cells at 6–36 km/h —
while **5 of the 13 near-straight events are at 39–76 km/h.** Closes with deliberate matched manual
segments at 50–80 km/h on the same road.
⭐ **METHOD LESSON:** a single wideband 0.4–3 Hz detector would have found **nothing** — at these
amplitudes a 0.45 Hz cornering input destroys the zero-crossings of a small 1.2 Hz limit cycle riding on
it. Five sub-bands found it. Controls passed first, including a **ringing control** (impulse/step/ramp
through every band filter, **zero spurious chains in 15 combinations**).

### ⭐⭐ V109 BUILT — `0xC40DC` (α2) 22 → 14. **GATE 1 AND GATE 2 BOTH CLOSED.**
```
V109 image  e9eb51fcad9ffc8768cd3e8eb601619d0f2acc0f702f01c4732243c70cc7f4d6
V109 .rwd   83047f0fd3b5b656720487d5f70755c3b2506c4293097b403abf003e972087c1
builder     analysis-2020accord/builds/v108_plus/build_v109_tva.py   30/30   BASE = V108
5 bytes vs V108 (1 payload + 4 CRC).  Cal-only.  Cave byte-identical.  UNCOMPENSATED.
```
**V109 = V108 + one cell.** α2 is the only axis of this lane nobody has ever touched — V106 changed its
MAGNITUDE, V107 its SPEED SCHEDULE, and both pay for any HF reduction **one-for-one at 21.7 Hz** because
Y is a flat multiplier. **Shape does not.** Uncompensated:
```
   f Hz     1      3    7.79  21.73    27     40    61.1   100    200    300
  ratio   1.000  0.998 0.988  0.920  0.888  0.816  0.732  0.657  0.607  0.596
```
⇒ **~0 % cost at manoeuvre frequencies, 1.2 % at the ratchet, 8.0 % at the mode (below the ~9 %
perceptual floor) — and 27–40 % cut across 61–300 Hz.** Phasor at 21.73 Hz = **222.77°**, safe sector.

**GATE 1 CLOSED — and the fan-out is FOUR consumers, not three.** Cell: one access image-wide, zero
writers (`disp|1`, 6-byte and register-indirect forms all checked). Signal: friction lane = the target ·
oscillation detector **SAFE and margin IMPROVES** (arms at 12800 vs a corpus max ~5,300; V64 flew 1,158
reversals with **zero arms**) · `FUN_00071272` writes a **36-byte-stride diagnostic log record** at
`gp-0x26e8`, not the torque path · `FUN_0007b022` has **four outputs with zero readers** and its fifth
(`gp-0x4f64`) is cleared by tracing **its own three producers**. `gp-0x6c2e`/`cal(0xC40DA)` = 3 are
**independent AT THE PRODUCER** — separate state, separate cal, separate shift — with disjoint reader
sets as a second reason.
🛑 **GATE 2's real cost: the 90–180° sector ENTRY slides DOWN 74.1 → 54.0 Hz.** That is why **V109 MUST
sit on a V108 base** — across 54–74.5 Hz V105's notch left the parallel lane a geometric-mean **5.15×
(+14.2 dB)** louder than Honda's, and V108 reverts it. **`build_v109_tva.py` ASSERTS the base.**
🛑 **Rail duty under this dose is NOT predictable** — the only method available was measured **32× wrong**
on this lane, the loop term is 14–16×, and α2 sits upstream of the distribution any solve would need.
**V109 is a deliberate single-variable experiment against V108**, and that two-point contrast is the only
thing that can size this cell. **Recommendation: fly V108 first**, so the contrast exists.

### ⭐⭐ THE HEADLINE — `gp-0x6b26` IS NOT A DAMPER ABOVE ~30 Hz, AND V107 MADE IT A RELAY
The lane is `64·H1·(1−z⁻¹)·H2` (EMAs α0 = 37/128 = `cal(0xC643C)`, α2 = 22/64 = `cal(0xC40DC)`) —
**a BANDPASS peaking at 61.1 Hz, −3 dB span 25.1→153.0 Hz, never below 4.49× to Nyquist.** At 100 Hz it
runs at **10.86×, 40 % MORE than at the 21.7 Hz mode it was meant to damp.** Two independent derivations.
V107's own re-aimed 427 tap then measured the consequence — `P(|gp-0x6b26| = 511)`, engaged, route `1e`,
episode-bootstrapped over 10 episodes:
```
   bin      V107 rail duty          V106 same samples      <10   1.68% vs 1.47% EXACT
   10-25   32.32% [29.93,35.68]     <= 15.46%            40-64   4.27% vs <= 3.43%
   24-40   21.27% [19.93,22.51]     <= 10.45%             >=65   <= 0.23% / <= 0.03% BOTH
```
**V107's own builder predicted ≤1.05 % everywhere and REJECTED its alternative at 6.2 % as "V80 relay
territory".** A railed acceleration term is `sign(α)·511` — a bang-bang Coulomb relay, V80's exact
mechanism. 🛑 **The safety case could not see it: CAN 427 arrives at 49.8 Hz (Nyquist 24.9), and the
lane's entire −3 dB band is above that.**
🛑 **REFINED 2026-08-27 — that framing is right about SPECTRA and WRONG about DUTY.** Rail duty is
`P(|c2c| ≥ thr(v))`, a functional of the **MARGINAL** distribution; the 427 tap samples instantaneous
values, so its marginal is **UNBIASED** and only its SPECTRUM is aliased. **The measured duties are
sound.** What the 49.8 Hz tap genuinely cannot do is see the **25–153 Hz band the lever ACTS ON** —
which is why an α2 dose cannot be sized from it, and why **V107's error was a MODELLING error (an
open-loop push-through applied to a closed loop), not an instrument error.**
The rail threshold shrank **1.42–2.71×** across 24–90 km/h
while **Y[0] stayed byte-identical below 20 km/h** — and the operator reports grinding at 15–40 mph and
none below 5–6 mph. **The symptom map and the rail-duty map are the same map.**

### ⭐ "IT PERSISTS AFTER DISENGAGE" — MEASURED AT ~2.05 s, AND IT IS OURS
Mode records 26/27 are held until `gp-0x69b0` ramps to exactly 0 (`FUN_00028ea6`, 1 kHz, five rates =
100/497/993/**2048** ms + a ~40 ms commit hold). Wire-saturation duty is **zero from +2.0 s onward**;
last railed sample 1.81 / 0.85 / 0.40 s. **Pre-registered: 0.10/0.50/0.99 EXCLUDED, 2.05 CONSISTENT.**
Both controls passed — two of three transitions SPEED UP and still go to zero, and at matched steering
rate post-disengage `|c2c|` p50 = 72 with **0.00 %** rail duty against engaged p50 = 1080 and **20.43 %**.

🛑 **CORRECTED 2026-08-27 — `gp-0x69b0` IS A Q15 MULTIPLIER, NOT A GATE, SO THE RELEASE IS A CROSSFADE.**
An earlier census over its 45 accesses found **zero `mul` instructions** and concluded "gate". That does
not follow: **the multiply's operand is a REGISTER loaded ~2,700 bytes earlier**, and an operand-text
search over accesses to a symbol finds loads and stores but cannot see what is done with the value —
the same blind spot `CLAUDE.md` already records for register-indirect writes.
**The multiply is `0x2A1E6  mul r14,r9,r0`, then `0x2A1EA sar 0xf,r9`, `0x2A1EC sxh r9`** ⇒
`LKAS_lane = sxh((lane × gp-0x69b0) >> 15)`. Register liveness proved mechanically: all 41 accesses to
`gp-0x69b0` sit in `0x2936A`–`0x2972A`, every read is `ld.hu …,r14`, and **`r14` is never written across
the 1015 instructions between the state machine's exit at `0x29734` and the multiply** (the only
instruction with `r14` last is `0x29A48 cmp r0,r14`, PSW-only), with **zero `jarl`/`callt`/`trap`** in
that span so no callee can clobber it.
⊕ **The sign objection dissolves too**: the cell is *stored* with `st.h` but *read exclusively* with
`ld.hu`, and the SM saturates it at `0x8000` (`0x29490 ori 0x8000,r0,r14`). 32768 does not fit a signed
int16, so it stores as −32768 and reads back as **+32768 unsigned** — "signed, resting at 0/−32768" is
exactly what an unsigned Q15 0…32768 looks like in a raw halfword dump. **Range 0.000–1.000.**
⇒ **During the ~2.05 s tail there IS a decaying LKAS command while the engaged-only damper is still in
force** — a crossfade, not a hold-then-snap. The measured 2.05 s release stands unchanged; what changes
is what the car is doing during it.

### ⭐ THE 2×2 — THE RELAY IS MOSTLY PLANT, AND A 32× MISS IS EXPLAINED
Holding Y fixed, **engaged `|c2c|` alone gives 27× the rail duty of manual `|c2c|` at 10–25 km/h.**
`gp-0x6b26` feeds aggregator → motor → motor rate → `gp-0x6c2c`: **it is a closed loop**, so V107's
open-loop push-through (which assumes the input distribution is invariant to K) was **32× wrong**.
Reached independently from the code and from the data. 🛑 **No open-loop duty prediction on this lane
can be trusted again.**

### ⭐⭐ THE CLOSED-LOOP TERM IS NOW MEASURED — 14-16x, AND IT IS THE SAME MAP AS THE SYMPTOM
Median `|gp-0x6c2c|` engaged vs manual, matched speed, within route `1e`:
```
   <10 km/h    62.4 vs 22.4  =  2.79x     (n = 6248 / 20044)
   10-25      974.4 vs 60.8  = 16.03x     (n = 14950 / 3921)
   24-40      860.8 vs 52.8  = 16.30x     (n = 15483 / 2679)
   40-64      560.0 vs 40.0  = 14.00x     (n = 30250 /  896)
```
⇒ **~94 % of the engaged acceleration signal is LOOP-GENERATED.** [EVIDENCE for the ratio; BELIEF that
it is all loop — engagement also adds LKAS excitation, so 14-16x bounds the loop term ABOVE.]
⭐ **2.79x below 10 km/h against 14-16x above it is the SAME MAP as the operator's "grinding at 15-40 mph,
none below 5-6 mph" and the SAME MAP as the rail duty.** Three independent quantities, one shape.

### ⭐ V108's OWN PREDICTION — the first quantified one this kit has made, and its method is held out
An exact-integer reimplementation of the cascade, run per-sample over route `1e`, **reproduces the
MEASURED rail duty on all five speed bins with nothing fitted**: 1.60 vs 1.68 · 33.52 vs 32.32 ·
21.15 vs 21.27 · 5.19 vs 4.27 · [0.00,0.16] vs <=0.23 %. **HELD OUT on route `1b` — a different drive,
same build — 33.76 % at 10-25 km/h against `1e`'s 33.52 %.**
⇒ **V108's Y-row change alone is predicted to take 10-25 km/h rail duty from V107's measured 33.52 % to
7.0-15.4 %** — roughly halving the relay duty. ⚠ Route `1b` also gives 31.88 % at 24-40 against `1e`'s
21.15 % and 21.72 % at 40-64 against 5.19 %: **duty is strongly driving-dependent above 25 km/h.**
🛑 **A CLOSED-LOOP SIMULATOR IS NOT AVAILABLE AND THE REASON IS STRUCTURAL.** The identified column model
(`J_w` = 1.248, `b_w` = 35.8, corner 4.57 Hz) has a **measured validity band of 5-13 Hz**, while the lane
peaks at 61.1 Hz with a -3 dB span of 25.1-153.0 Hz ⇒ **100 % of the lane's band, and its peak, lie above
the plant's ceiling**, and above 13 Hz `|Z|/w` collapses 1.33 -> 0.45 for reasons the record itself
records as unresolved (real plant, or an internal low-pass in the torque channel). `ClosedLoopSim` is
implemented in `analysis-2020accord/model/eps_closed_loop_sim.py` and **refuses to run without
`allow_extrapolation=True`; no number in this block came from it.**

### 🛑 THE GHIDRA EMULATOR CANNOT VALIDATE THIS ARITHMETIC — three doors, three distinct reasons
1. `emulate_function` is **hardcoded x86** — fails `"Undefined register: ESP"` on every V850 call
   regardless of arguments; `V850:LE:32:default` has no ESP and nothing aliased to it. Server-side fix:
   take the SP from `getDefaultCompilerSpec().getStackPointer()`. `emulate_hash_batch` shares the defect.
2. `run_script_inline` is gated behind **`GHIDRA_MCP_ALLOW_SCRIPTS=1`**. Ghidra's own `EmulatorHelper`
   IS language-agnostic and would work; that env var is the whole blocker.
3. 🛑 **NEW — `get_function_pcode` is structurally insufficient to emulate from, and would have produced
   a confident WRONG answer.** No block out-edges, and the decompiler's condition-normalisation flips
   conditions while swapping edges (at `0x36C38`/`0x36CCE`/`0x36CEE` the inverted sense is right, at
   `0x36C48` the non-inverted sense is right) ⇒ **polarity is unrecoverable**; and **SSA varnodes collapse
   onto one `(space,offset)` key** (`u30300` is reused by the loads at `0x36C94`/`98`/`9C`).
⇒ **The arithmetic is validated instead by THREE NON-EXECUTION METHODS THAT AGREE** — decompile,
assembly, and the p-code IR — and the kit's mirrors are CORRECT. Confirmed at IR level: `INT_SEXT`x2 ->
`INT_MULT` -> `INT_SRIGHT #6` (arithmetic) -> `INT_MULT #111` -> `INT_SRIGHT #12` (arithmetic).
⊕ **Exact rail thresholds are 1063 / 1306 / 1959 ct** at 0/20/90 km/h — `sar` FLOORS, so the clamp is
reached ~0.2 % earlier than the closed form's 1064.9/1308.5/1962.7.
⊕ **The LERP divide is `INT_SDIV` (truncates toward zero), not floor** — identical for today's monotone
Y rows, but **a non-monotone Y row would make a floor-division mirror off by one.**
⊕ 🛑 **An unpriced nonlinearity: the `d32` clamp (±0xFA0000) saturates the lane** above an input of
~10,320 ct @7.79 Hz, 3,944 @21.7, 1,961 @61.1, 1,668 @100. Above it the lane delivers 8-32 % of `|H|`.
**The kit's whole alpha2 sweep table is a linear-`|H|` calculation.** Safe for the railing question
(railing needs only ~88 ct of input at 61 Hz) but **NOT safe for broadband claims.**

### 🛑 E3 WAS BUILT AND PULLED — the pre-registration was honoured
`0xC61BE` = 15360 is UPSTREAM of the 6× gain, so the lane's reach is `(clip × gain) >> 15` and has been
**81.5 % of its own output clamp on EVERY build since V14** — which is also why `0xC61B2`/`0xC61B4`
measured "0 % of the effect": **they are inert BECAUSE this clip caps the lane 18.5 % below them.**
Anchored two ways (`(15360×891)>>15 = 417` = the recorded stock V9 maximum). But the knee test on route
`1e` (93,356 frames / 924 s, `|e4tq|` p99 = max = 4096) shows **achieved rate still rising 2.1–3.9× at
the top of the command range at all five speeds, every CI excluding 1.0** ⇒ **the clip is IDLE and the
raise buys zero. PULLED.** ⚠ Not proof it can never bind — the clipped quantity carries int32 recursive
state (`gp-0x6cf8`, `gp-0x6dd0`), so it is also **not reconstructible from logs.**
⭐ Zero-firmware confirmation exists if ever wanted: **stock UDS DID `0x48AC` bytes 7–8 = `gp-0x6b38`**
(RDBI entry `0xB7864`, no security access); a bound clip pins it at ~2481, and **anything above 2505
falsifies the model.** Blocker on record: EPS UDS is bus-1 + OBD-mux only. **Nothing was transmitted.**

### 🛑 V109's LEVER IS ALREADY PRICED AND GATED — `0xC40DC` (α2), VIRGIN ON ALL 102 IMAGES
At K2 = 14 the delivered response is **FLAT across 18–30 Hz (1.024→0.966) and cuts 20–35 % over
61–300 Hz** — it de-rails **without giving back one count of mode-band damping**, which lowering Y cannot
do (Y is a flat multiplier). GATE 1 on the cell is the cleanest possible (exactly ONE gp/tp access
image-wide, zero writers, `disp|1` trap handled); GATE 2 at the mode is clean to K2 = 3.
**HELD OUT of V108 for three reasons:** the sector entry moves **DOWN** (74.1 → 54.0 Hz), `gp-0x6c2c`
fans out to **three** consumers of which two are unverified against a *reshaped* signal, and the only
available duty-prediction method was just measured 32× wrong.
🛑🛑 **AND IT MUST SHIP WITH THE NOTCH REVERT OR NOT AT ALL**: across 54–74.5 Hz V105's coefficients
leave the base-assist lane a geometric-mean **5.15× (+14.2 dB)** louder than Honda's, 21.8× at the
sector's new entry point. V108 ships E1, so the prerequisite will be on the car.
⊕ Take it **uncompensated** — the int16 boundary is exact: `29490 × 1/0.90 = 32,767` against a floor of
32,768, so a **−10 % α2 cut is the LAST one Y[0] can compensate.**

### 🛑 THE INSTRUMENT LESSONS
**CAN 427 is 49.8 Hz, not 100** (Nyquist 24.9) — no spectral claim can come off it. **The between-drive
audio contrast is PERMANENTLY unavailable** — the parked, engine-on cabin differs **3–12×** between
drives and no openpilot-version finding touches that; route `1e` has 35.4 s of matched manual inside the
grinding window, so within-drive is available and strictly better. **The device was reflashed** — the
route counter reset (`a6` → `1b`/`1e`) and **`0000001b` exists TWICE on disk with different hashes**;
key every cache on `counter--hash`, and never assume low route number = old build.
✅ **The a6-vs-1e confound is CLOSED for the CAN channels** (one openpilot commit `7c6741a9`→`36d0c074`,
AGNOS unchanged at 19.6.2, every lateral CarParams field identical).
🛑 **The whole extractor family was DEAD** (`ModuleNotFoundError: _grind2_lib`) because the 2026-08-26
reorg moved a module into `lib/` while the `PATH BOOTSTRAP` block stops at the FIRST `.pkgroot`.
**FIXED in 729 files** — it now walks every `.pkgroot` root in the repo, nearest first.

### 🛑 SIXTEEN RETRACTIONS THIS SESSION — the four that change what anyone should do
1. **`0xC520C` STRUCK as a lever** (retracted by its own author). Peak `gp-0x6ac0` = 1462 ct against a
   first knot at 1050, reached **0.11 % of engaged time, never past the second**; `gp-0x4f64` sits at its
   max 4762 for **99.9 %+** of engaged time. Reconciles `b6` = 0.000000 and explains V41's null.
   **Stands as a documented mechanism, not a lever.**
2. **`0xC64DE` is NOT a "re-engage ramp"** — it is the **half-period of a sign-flipping square wave**;
   V18 moved it **29.41 → 18.52 Hz, into grind #1's band**; burst ~381 ms; **amplitude LERP is all zeros
   ⇒ structurally INERT.** ⚠ A latent 18.5 Hz injector into the 6× path, four halfwords from live.
3. **`accord-4x-lkas-gain-is-the-frozen-variable` is STALE** — 4× only through V100, **8× on V101, 6×
   since V102** (`0xC6CD0` = 5346 = exactly 6.000×; 891 = 1×).
4. **`gp-0x4f62` "peaks at 125 Hz" DOES NOT FOLLOW FROM THE CODE** — ring buffer + variable tick weights
   + a conditional call; the effective delay is unresolved. **Do not reuse 125 Hz.**
⊕ Also: the `0xE4`/`0xE5` "skip" is **the selector-reachability complement, not a bug** (our car is
TVCA4 → slot 11 → selector 7 → `0xE51A8`, **raised**; V74's slot naming is right and V38's is wrong);
*"`H(0)=0` ⇒ cannot rate-limit"* is **VOID once the term rails** (a railed term is 10.7 % of governor
authority as constant DC drag through the whole acceleration phase); *"gp-0x6b26 can never raise a
resonance"* was only ever checked **to 40 Hz** — above **74.5 Hz** the phasor sits in the
resonance-raising sector continuously to Nyquist; and the *"16384 makes the two ceilings agree"* framing
is **VOID** (the E4/E5 taper clamps `gp-0x69ae`, bounded at ±16384 by STEER_MAX = 4096 **by
construction**, so V38's edit was correct and complete and there was no miss).

### THE DRIVE CARD FOR V108 — in the handoff §3
**Primary: the operator's report per scenario.** Then rail duty by speed bin off the uncensored `sar 5`
tap · `|gp-0x6c2c|` at ≥70 km/h (V107's item #2, still unanswered) · 18–30 Hz prominence against a6 as
**E1's risk readout** (V105's flight run backwards predicts ×1.30 [0.88, 1.82], a CI spanning 1) · a
**within-drive** third-octave audio split at 45–130 Hz, which **falsifies E1's HF case if it comes back
flat and broadband above 200 Hz** · `b5` at matched α · fault-free confirmation.
🛑 **AND THE TOP NON-BUILD ITEM, now with a new requirement: the alternating drive PLUS deliberate
disengagements at CONSTANT speed, throttle held ~15 s.** The operator disengaged three times on `1e` and
changed speed every time (−13.6, −6.1, **+10.7** km/h) — natural driving, fatal to the measurement.

---

## ⚠ SUPERSEDED BLOCK, 2026-08-23 — **V106 FLEW AND EXTINGUISHED THE MODE AT LOW SPEED · RULE 7 CLOSED · THE UNIFORM DOSE AXIS IS EXHAUSTED · V107 RESHAPES THE SCHEDULE**

🛑 **ON THE CAR: V106** (route `a6`, 1,224.0 s engaged, fault-free).
**V107 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-23-v107-the-schedule-is-the-lever.md`** — drive card, 13 retractions,
6 record defects, 14 open items with what closes each.
```
V107 image  c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45
V107 .rwd   78eae7da20a87f1a95295eca11da0d08f4cf2b3b823785594cde4be93a7b24ff
builder     analysis-2020accord/builds/v80_v107/build_v107_tva.py   55/55 assertions   BASE = V106
E1  0xD7A5C / 0xD7A6C   (-29490,-17202,-5898) -> (-29490,-24000,-16000)   modes 26/27, X untouched
E2  0x55DF2  7a 94 -> d4 93   427 tap: gp-0x6b86 -> gp-0x6c2c
    0x55E10  a4 -> a3         sar 4 -> sar 3
```

### ⭐ THE HEADLINE — V106 EXTINGUISHED THE 21–27 Hz MODE AT LOW SPEED
Engaged, <16 km/h, max-demand arm: prominence **1.51 against STOCK's 1.46**, and V106's argmax
**follows the search-band edge exactly as stock's does** while V104's and V105's stay pinned. Two
independent within-spectrum signatures of no line present.
**`18-30 a6/V105 = 0.347` CLEARS route a6's own within-drive split-half null [0.482, 1.982] — the
FIRST band-power result in this kit's history to do so.** Positive control `a6/STOCK = 5.735`.
🛑 The confound was cut: a6's engaged command is ~4× SMALLER than a5's, so the result was re-run in
matched (speed × **absolute** demand) cells and survives.

**Operator's report:** grinding attenuated in all three scenarios; ratcheting still present at high
LKAS demand; max LKAS-driven steering rate limited; LKAS-off feel normal.

### ⭐ RULE 7 IS CLOSED — the car reads modes 26/27 engaged
`b5` at **matched α** (a pooled duty is the WRONG estimator — the K·α product is invariant to K):
a6/a5 ratio **8/8 bins below 1, sign p = 0.0039**; within-drive engaged 0.1907 vs MANUAL 0.4509.
The ×1.5 WAS in force: delivered multiplier **1.68× [1.16, 1.88]**, excluding both 1.00 and 3.00.

### 🛑 WHAT SURVIVES, AND WHY V107 IS A RESHAPE
Residual is a ~27 Hz line **above ~70 km/h** (55–70 is measured AT STOCK: 1.4 vs 1.6). That is exactly
where Honda's taper makes V106 **4.2× weaker** (−24,546 at creep vs −5,898 at ≥90 km/h).
**The uniform axis is int16-EXHAUSTED:** Y[0] stock −9830 ⇒ k_max **3.3335**, V106 at ×3.0 = **90 %**
of the floor. ×4/×5/×6 are OVERFLOW. **Y[2] has ×5.56 of room and that is where the line is.**
RESHAPE B holds Y[0] byte-identical ⇒ creep clamp duty and relay index unchanged BY CONSTRUCTION.
A flat schedule was REJECTED: **6.2 % clamp duty at 70–90 km/h = V80 relay territory**, against B's
≤1.05 %. And **route a6 spent 809 of its 1,224 engaged seconds above 70 km/h.**

### THE RATE COST IS AN ACCELERATION PENALTY, NOT A SLEW CEILING
No rail · steady state restored to V104's level (`H(0)=0` predicts it) · wheel acceleration down
2–4×. At matched ABSOLUTE max demand, achieved rate p90: V88 326 · V104 166 · V105 229 · **V106 157**
⇒ **~30 % of peak rate given up vs V105.**

### THE RATCHET IS LKAS-DEMAND-DRIVEN — the next target, and a NEW discriminator
The 7.4–8.6 Hz LINE is the **only** band with a positive residual demand association after
partialling out motor rate (+0.1139 [+0.0374,+0.2548]); carrier and placebo go negative. 2/2 rate
strata, both CIs excluding 1, placebo flat.

### ⭐ THE ARCHITECTURAL ANSWER — the feedforward lane EXISTS
`0xC4124[1]` 0→5 moves LKAS to Honda's own post-governor lane; four channels already use it. Both
cal tables **0 writers**; the ASIL monitor dispatches on the same byte ⇒ follows by construction; the
authority gate is UPSTREAM of the router. **Topology change, NOT authority — it does NOT buy back
steering rate** (the damper subtracts at the FINAL add, downstream of both lanes). **V108 candidate.**

### 🛑 RECORD DEFECTS FOUND — reported, deliberately NOT silently patched
1. **Golden model `assist_polarity = 1`** where `gp-0x6752` is **−1**; nothing overrides it, so every
   `_demo()`/`_self_check()` run uses the pre-retraction sign. **NOT fixed** — `_self_check()`'s
   expectations were computed at +1, and editing them to match the model's new output would make the
   test agree with the code by construction. Defect note in place; **contract re-verified intact
   (2,512 B, `740f4bcd…`)**.
2. **V100 FLEW as route `0x85`** (2026-08-13); `BUILD-LINEAGE-CATCHUP-V76-V100.md` still says "BUILT
   AND NOT FLASHED" — the eleventh stale flight-status row, by that row's own warning. ⭐ **And V100
   carried the `|gp-0x6ad6| ≥ 8192` rail comparator — 🛑 **and this file's claim that its duty was NEVER HARVESTED is FALSE. It was harvested 2026-08-14 and re-run 2026-08-27: d(b5) = 0.000000 over 24,925 engaged frames, gate proven live by `b4` on the same cell at duty 0.6057. The dose is MERELY SMALL, not structurally zero — K1 = 204 IS delivered.** — it decides
   whether `0xC40D2`'s dose is small or structurally ZERO.
3. `accord-gp6b4c-is-an-11-slot-assist-sum` — modes 5/7 **re-route**, they do not zero.
4. `accord-friction-polarity-*` — conclusion stands, sign chain **replaced** (frame crossings).
5. `MEMORY.md` pointed at a file renamed after the operator retracted its claim (**"v84 fixed the
   highway ring"** → `accord/builds/accord-v84-flew-and-fixed-nothing.md`). **Fixed.**

### 🛑 THE INSTRUMENT LESSON — a STATIONARY mode returns a FAKE frequency slope
Injected at an amplitude ladder through the same argmax pipeline, a mode that does **not** move
returns **−1.14 / −0.759 / +1.731 Hz per e-fold** when the amplitude axis is INDEPENDENT of the band
power, with the sign tracking (band centre − mode frequency). Against band RMS the floor is **zero**.
⇒ **`accord-f0-crossover-is-the-endpoint`'s −1.93 Hz/e-fold was measured against COMMAND amplitude and
sits inside that artefact's range.** NOT retracted (`f0` is a `Re(Z)` crossing, not an argmax) — but
**push a stationary synthetic through the actual `Re(Z)` code before it sizes anything.** OPEN.

### 🛑 THE TOP NON-BUILD ITEM — THE ALTERNATING DRIVE, open since the V105 handoff
~30 s engaged / 30 s manual at 5–15 km/h, same road, same session, command swept hard and soft. It
closes the ~8 Hz LINE null (a6 had only **7** engaged episodes, one of them 941.6 s), the <16 km/h
pitch-vs-amplitude cell (30 and 46 windows), and the engaged/manual contrast above 25 km/h (a6 has
**0.0 s** of manual driving in 25–60 km/h).

---

## ⚠ SUPERSEDED BLOCK, 2026-08-22 — V105 flew and relocated the mode · the three grinds are one frequency · V106 is a damper

🛑 **ON THE CAR: V105** (route `a5`, verified from the wire — three legs, strongest being the biquad's own
427 output matching the image floats). **V106 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-22-v106-the-damper-and-the-one-mode.md`** — the full drive card with
**nine numbered open questions**, 21 retractions, 20 open items with what closes each.
```
V106 image  78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a
V106 .rwd   e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc
builder     analysis-2020accord/builds/v80_v107/build_v106_tva.py   50/50 assertions
```

### 🛑 THE OPERATOR CORRECTED THE KIT TWICE AND WAS RIGHT TWICE
1. **"All 3 grinds are the same frequencies, under different scenarios."** CONFIRMED. Peak-searched
   **15–48 Hz**, stratified by HIS scenarios: S1 (<10 km/h) / S2 (hard manual turns under LKAS) / S3
   (highway) **all peak at 21–27 Hz**, and **38–48 Hz prominence is 0.3–4.9 (≈ baseline) in all 21
   build×scenario cells.** 🛑 **The kit's "grind #2 = 44.9 Hz Q≈37, NOT a harmonic" and "grind #3 ≈ 46 Hz"
   are NOT REPRODUCED.** Restate as three CONDITIONS of one mode. ⚠ Ceiling: `0x18F` Nyquist is 50.57 Hz,
   so nothing above ~50 Hz is observable at all; the harmonic test is **not runnable at highway**
   (2 × 25–27 = 50–54 Hz).
2. **"Why don't we put telemetry on the mode?"** — he found a four-build hole. **The mode record has NEVER
   been directly telemetered.** V93 was built as a discriminator (via dose-ratio inference) and never
   flew; `accord-cbe74-dose-measured-inert-wrong-mode-record` names it as the suspect for V91/V92.
   **V106 closes RULE 7 at zero cost — see below.**
⊕ **And a corpus claim is re-attributed: "applying torque kills the buzz" is really "applying RATE kills
the buzz."** At `|tq| ≥ 1000` with no rate condition the mode is fully present (PSD 51.7); adding
`rate ≥ 40 °/s` extinguishes it. Same drive, same channel, only the mask differs.

### ⭐⭐ V105 SCORED — THE NOTCH WAS AIMED AT EMPTY SPECTRUM, AND THE MODE RELOCATED
**On V104 only 1.2 % of the engaged <16 km/h 18–30 Hz POWER sat inside V105's own stopband.** A perfect
25.5 Hz notch could have removed at most that. **The mode is at 21.7–22.9 Hz**; the two estimates that
named 25.5 are discredited (`a4`'s peak regression had **R² = 0.039**; `f0` is a `Re(Z)` zero-crossing,
never the spectral peak).
```
                 peak Hz     shift            |H_V105| at its OWN peak    18-30 band power
<16 km/h  V104    22.73                              0.3039
          V105    20.48    -2.25 [-2.50,-0.50]       0.5442  <- 1.79x     0.769 [0.548,1.135]
55-70 km/h V104   25.97                              0.0467              (CI SPANS 1)
          V105    27.47    +1.50 [+0.50,+2.50]       0.1795  <- 3.84x
```
🛑 **The mode moved to where the notch costs it LESS, with band power CONSERVED.** That is a
describing-function intersection sliding, not attenuation. ⇒ **filtering is structurally the wrong tool.**

### 🛑🛑 ROUTE `a5` CANNOT RESOLVE V105 FROM V104 ON ANY BAND — the standing limit
Within-drive split-half null spans **0.26–3.8**. 18–30 Hz reads 0.410 [0.240, 0.688] — **inside it.**
Two pipelines independently reported narrow-band "cuts" (0.348 and 0.343) and **both authors withdrew
them** as band placement: 18–22 goes UP 30 % while 20.5–23 goes DOWN 65 %, because the mode moved.
⇒ **No V105-vs-V104 band-power ratio is resolved.** What survives is everything that is not a cross-drive
ratio: peak location and shift, `|H|`-at-own-peak, the 427-lane shape, the grind-#1 centre, cave duties.
⭐ **THE TRANSFERABLE LESSON: on this corpus, design the statistic to live INSIDE a drive.**

### ⭐ THE RATCHET IS A SEPARATE, GAIN-DRIVEN ~8 Hz LINE THAT DOES NOT EXIST ON STOCK
Pre-registered split of 6–12 Hz into a **LINE (7.4–8.6 Hz)** and a **FLOOR**, replicated on two statistics:
```
                      median E (6x vs stock)   4-dose ladder beta (1x/4x/6x/8x)
LINE                       +1.559                   +1.525  => E_line  +1.136
FLOOR                      +0.256                   +0.693  => E_floor +0.300
CARRIER 21-28                  -                    +1.390
CTRL 32-38 (placebo)           -                    +0.395
```
🛑 **On STOCK the line power is EXACTLY ZERO in 3 of 4 highway cells.** `E_line` centred **above 1** — a
by-product cannot outgrow its source ⇒ the line is a **SIBLING** of the carrier, not a demodulation
(AM bounded at **m < 0.05**; measured 6–12 Hz RMS is **~75×** the entire demodulation budget).
⇒ **`E = 0.406` "partial coupling" was a MIXING ARTEFACT, and every 6–9 Hz band-RMS number in this kit's
history dilutes the real effect by 2–3× by pooling line and floor.**
⊕ **H3 (governor-ceiling dropout) RETIRED** by two independent channels: `v105_b6` = **0.000000 across
65,959 frames**, and the reconstructed peak-follower never reaches the 223 °/s knee on five routes.

### V106 — 12 BYTES, PURE CAL, AND IT PROVES ITS OWN PREMISE
```
0xD7A5C  mode 26 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)
0xD7A6C  mode 27 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)   = x3.0 stock
```
`gp-0x6b26 = -K·angular_acceleration`. **The only lever with a signed on-car precedent pointing this way**
(V93/V94 lowered it and the operator aborted the drive as unsafe). **Damping removes a DF intersection;
a notch relocates it.** Reaches **both** bands — gain **1.478 @ 7.79 Hz**, **3.706 @ 21.73 Hz**.
🛑 **`H(f=0) = 0` EXACTLY** — the differencer `32·(1−z⁻¹)` is identically zero at DC for any `a1/a2/K`, so
**it cannot rate-limit a held 6× command at any multiplier.** A proof, not a measurement.
⭐ **MODE PROOF AT ZERO COST:** the carried cave rung **`b5` = ( |gp-0x6ae2| ≥ |gp-0x6b26| )** — operand B
at `0xC4B70` = `da94` = `-0x6b26`, **the exact cell dosed**. Engaged duty must collapse from its **0.4019**
baseline if the car reads 26/27 engaged; unchanged confirms the V91/V92 suspicion. **MANUAL is the
built-in control.** **RULE 7 closed either way.**
🛑 **26/27 ONLY.** The family has **FOUR** members (`builds/v80_v107/build_v100_tva.py`'s `DOSE_FAMILY_Y` lists three;
`builds/v80_v107/build_v105_tva.py` already had four): mode 24 = **MANUAL** (dosing it is inert for an engaged symptom and
changes manual feel), mode 25 = **role unconfirmed** (V69/V70 trap class). Both left at stock.
**`0xC407E` untouched at 511** — one count under its own 512 trip, so the RULE-11 interlock is intact **by
construction, not by care** (V73 raised a different clamp past its trip; V74/V75 both faulted mid-drive).

### 🛑 WHAT V106's LOGS MUST ANSWER — the drive card, in the handoff §5
**Q1 `b5` duty (the mode proof — outranks the symptom score) · Q2 clamp duty by rate bin (predicted ~1 %
in S1, ~0.06 % in S2 — clipping, if any, appears in grind #1's scenario, 26× more than in #2) · Q3 peak
LOCATION + the WIDEST band (damping predicts frequency unchanged, PSD down; if it MOVES again that is a
new result) · Q4 the ~8 Hz LINE scored separately from the FLOOR · Q5 the operator's report per scenario,
the PRIMARY readout · Q6 does the wheel feel heavier in fast turns · Q7 was the ×1.5 ever in force ·
Q8 housekeeping rungs · Q9 exposure.**

### ⚠ CORRECTIONS TO CARRY (the orchestrator's own, all four)
1. **"The high-rate cost is zero"** — RETRACTED. On the wire `|gp-0x6b26|` **peaks at 40–100 °/s and
   collapses above 100**; MAX at 200–400 °/s is **104 counts**, not the 543 predicted (5.2× over). ⇒ the
   raise **arrives in full at high rate — a real added opposition, not free** — but by the same token it
   **arrives in scenario 2 too**, so V106 can reach grind #2.
2. **"Dose all three modes symmetrically"** — WRONG; mode 24 is manual.
3. **"The 21–28 Hz ↔ grinding tie is inherited"** — the operator corrected it and the ladder confirms him.
4. **"V105 delivered −24.1 dB and he felt nothing"** — that was `|H|` at 24.9 Hz. At the mode it is
   **−7.6 dB**. The honest statement is *"~8 dB and he felt nothing."*

### ⭐ THE ARCHITECTURAL RESULT — the operator's own framing is reachable, and step 1 is telemetry
`FUN_0003a382` forms **`iVar30 = gp-0x4f60 − reference`** — raw torsion bar. **MODEL feeds the REFERENCE
side, never the MEASUREMENT side** ⇒ *"already doing this, and doing it badly"*. ⭐ **And it self-cancels
at DC by construction:** Stage-1 gives `d(iVar6)/d(gp-0x6b4c) = +2.578`, MODEL gives **−2.578** (identical
`polarity` and `0xC6468`, Stage-1's ×16/>>4 a designed no-op), and REQUEST is a **hard-coded zero**.
🛑 **The DC/mean-shift mechanism is CLOSED AT NULL; the AC/DF question at 18–28 Hz is OPEN.**
🛑 **`0xC6CD0` is EXOGENOUS by Mason's gain formula** — a source node never enters `Δ(z) = 1 − ΣL(z)`.
**There is no "move the gain outside the loop" to perform.**
🛑 **THE CAVE RISK MODEL WAS WRONG:** `0x3AC78` is a **task-1, 1 kHz trampoline inside the aggregator that
FLEW CLEAN on V39**, and V48B's own postmortem **exonerates the clock rate**. Corrected: *a task-1
trampoline is proven; a STATEFUL filter allocating NEW RAM into a live path is not.*
⊕ **Telemetry ceiling fully mapped: only 3 IDs cross the gateway — `0x14A` 0 free bits, `0x18F` 10,
`0x1AB` 5. Fifteen, permanently.** A byte-exact `|gp-0x6b26|`+sign spec exists for `0x18F` (hook `0x55D50`,
byte-stock on every build; 1048 free cave bytes at `0xC4BD8`) — `[0,511]` is **exactly 9 bits + sign**.
**Not shipped on V106**: the stub is an instruction-level spec, not assembled bytes.

---

## 🛑🛑 THE SESSION'S REAL RESULT — `f′` COMPRESSION. READ THIS BEFORE PROPOSING ANY OBSERVER LEVER.

**`f′`, the Stage-2 LERP's local slope, is a deterministic function of `|iVar6|`:**
```
|iVar6| ct : 0-178  178-356  356-719  719-1200  1200-1800  1800-3000  3000-5000
f'         : 2.539   2.174    1.496    0.948      0.488      0.346      0.248
```
| route 81, engaged | steeringPressed | D3 mask |
|---|---|---|
| `\|iVar6\|` p50 **hands-ON** | **2,829 ct** | **2,818 ct** |
| `\|iVar6\|` p50 hands-OFF | 188 ct | 337 ct |
| **f′ p50 hands-ON / hands-OFF** | **0.346 / 2.174** | **0.346 / 2.137** |

🛑 **THE FIRMWARE DESENSITISES THIS LANE 6.3× EXACTLY WHEN THE DRIVER PUSHES — and pushing is how the
operator provokes the symptom.** Two independent masks agree to 2 %. **Every perturbation of `iVar6`
reaches the car through `f′`, and V89 and V97 BOTH argued their direction on hands-off data (the steep
part) while the symptom lives on the flat part.** ⇒ **ONE mechanism for both nulls, consistent with
V98's comparable arms and the lively 427 lane, requiring nothing unmeasured.** [BELIEF, fits all data]

🛑 **CONDITIONED 2026-08-13 (later) — this line used to read "PATH 2 IS AUTHORITATIVE... no dilution
anywhere" unconditionally. `tracer-6ad6` found a hard clamp inside the same chain; team-lead verified
the crux in Ghidra directly (`read_memory(0xC6200)` = 8192, `disassemble_bytes` reproduces the
listing instruction-for-instruction).** `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` at 7.79 Hz, **valid ONLY
under the condition `|gp-0x6ad6| < 8192`** — the `0xC6200` clamp at `0x3a7b0-0x3a7c8` sits INSIDE
this very chain (`FUN_0003a382`, all three of P/I/D driven from the same clamped difference) and
**zeroes the derivative when it binds.** The clamp duty is UNMEASURED — V100's RUNG A measures it.
**Do not delete the number; it is still correct in the unsaturated regime.** Positive control still
reproduces the recorded PID lead to 3 s.f. (that check is unaffected — it ran unsaturated). Both
gates OPEN, incl. **`gp-0x67ab` ≡ 0 STRUCTURALLY** (closes `HANDOFF-2026-07-27:287`).

### ⭐ THE PERCEPTUAL BRACKET — and every candidate scored against it
**~0.55× (−45 %) IS felt (V88, V62). ~1.09× (+9 %) IS NOT (V85, V89).**
| lever | dose in his regime | verdict |
|---|---|---|
| `0xC63AC` 150→102 | 0.8–2.5 % of Path-2's 140.6 ct | **below floor ~20×** |
| **`0xC40BC` 600→300** | **0.5–1.2 %** | **below floor 8–18×** |
| `0xC63AE` 1024→**2048** | ≈ **+28 %** on the lane | ⭐ **the only one ABOVE** |

🛑 **`0xC40BC` is structurally dead in his regime: 93.1 % of hands-on engaged frames sit ABOVE the
10.61 °/s knee, where 300 and 600 are ARITHMETICALLY IDENTICAL** (orchestrator-verified; mean ramp
ratio **1.050**, a ×1.05 not a ×2). And `friction = |fVar18|·ramp·K1/1024` ⇒ **`0xC40BC` and `0xC40D2`
are two factors of the SAME PRODUCT — V99's perturbation is 0.096× V89's, which measured FLAT.**

### 🛑 FOUR RETRACTIONS FROM THIS SESSION — do not re-cite any of them
1. **"Stock encodes an exact pole match and V97 broke it"** — the cell identity is real and probably
   deliberate (`round(0.1·4096)=410`, Honda shipped **408 = 4×102**), **but it is a match between two
   STAGES, not the ARMS**, which do not share an input and are already **84° and 0.557-vs-0.906 apart
   at stock.** 🛑 **NEVER quote the 0.111/0.136/0.151 "phantom".** Survives: V97 moved the arms
   **further apart** (+7.82°, +5.4 %).
2. **"REQUEST is minor"** — `b5` tests REQUEST vs **ACTUAL**; the denominator is the **RESIDUAL**
   (`|iVar6|` p50 389 ct). The kit's own retracted "≤ 9 %" error, repeated. **REQUEST is now the most
   important unmeasured term in the chain.**
3. **427 "broadband ⇒ no band-specific claim"** — an **artefact**: 427 is transmitted at 49.835 Hz and
   a ZOH images 5–15 Hz onto 35–45 Hz. With a valid **20–24 Hz** control, 6–9 Hz excess is **2.30× on
   427 and 1.97× on column — they agree.**
4. **V86's `gp-0x67ab < 2` rung could NEVER have fired** (`< 2` is true of both states), yet
   `BUILD-LINEAGE.md` cites it as *"lever in force three ways."*
⚠ Also: `0xC63A0` weights **`gp-0x6bd0`**, not `gp-0x6b26` (that is `0xC63A6`).

🛑 **PRIOR OPERATOR REPORT, on V97 (route `0x80`), VERBATIM:** *"I did not feel any difference in
grinding or stuttering (micro-ratcheting) behavior at all on V97, so I stopped the drive."*
⊕ **"Stuttering" ≡ micro-ratcheting — his own parenthetical.** It is not a fourth symptom.

⚠ **IDENTITY IS V96-OR-V97, NOT SINGLE-FRAME V97.** `0x14A` byte7[7:6] ≠ 0 on **10,750/10,750** frames
⇒ **not V94, not V92, not anything ≤ V91** (all mask those bits off — structural). But **V96→V97 is
5 bytes (one cal + its CRC)**: cave, 427 repoint and every bit map are **identical**, so *no* frame can
separate them. We rely on the operator's statement that V97 was flashed.
⇒ 🛑 **STANDING REQUIREMENT: every build must carry a BUILD-IDENTITY FIELD that changes on every cut,
independent of the lever under test.** 2 bits (byte7[7:6]) gives only ONE clean generation and
V96/V97 already burn {1,3}; a durable field needs ≥3 bits and its own `0x18F` hook — **as its own
build**, never combined with a new measurement class (that is how V24/V27/V48B bricked ECUs).

🛑🛑 **THIS FILE SAID "ON THE CAR: V94 … it is still flashed" FOR A FULL SESSION AFTER V96 FLEW, AND
IT COST REAL WORK.** It sent the session's strongest analyst to close its verdict with *"fly V96, S2
answers it"* — V96 had already flown and its regressor was 34× over-range, so **S1 and S2 are BOTH
VOID**. Seventh instance of the kit's "row says UNFLASHED after it flew" defect.
⇒ **NEW CLOSE-OUT GATE, mechanical, run it every time:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`, reconciled
against the identity bit from the most recent route. The old rule ("write the flight result in the
same pass that scores the flight") only fires if someone remembers; this one fails loudly.

## ⭐ FLOWN 2026-08-12 AS ROUTE `0x81` — **V98**, the first COMPARATOR probe in the kit
🛑 **This heading read "BUILT AND UNFLASHED" for a full session after V98 flew — the EIGHTH instance
of the "row says UNFLASHED after it flew" defect. Corrected 2026-08-13.** See the flight result and
the comparator verdict at the head of this file.

```
39990-TVA,A160-V98-V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2-0x13000-0x100000.rwd
  image c9babfed6acf24c0c5877754149a60fd5866dae8407029d7a3a5d74870d151d9
  rwd   fcfa1baa82ea8fbca104eee5c8a398b7d5de8762629351128b05e0cb811e5e3c
  builder analysis-2020accord/builds/v80_v107/build_v98_tva.py   199/199   BASE = V97 (on the car)
```
🛑 **ZERO calibration bytes. ZERO 427 bytes. Cave only — AN INSTRUMENT, NOT A FIX.**
It answers the one question this session could not: **which arm of the observer residual dominates.**

| bit | signal | role |
|---|---|---|
| byte4 b7 | `gp-0x6b70 < 0` | V96's rung, byte-identical |
| **b6** | ⭐ `\|gp-0x6bfe\| ≥ \|gp-0x374c>>4\|` | **MODEL vs ACTUAL** |
| **b5** | ⭐ `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` | **REQUEST vs ACTUAL** — with b6, ranks all three arms per frame, **no scale assumption** |
| b4 | `(gp-0x374c>>4) < 0` | V96's rung — **the converse positive control** (measured `arg(B′)−arg(rate)` = +78.6°/+78.0°) |
| b3 | `gp-0x6752 ≥ 0` | closes a multi-session blocker; **a DEPENDENCY, not a rider** |
| byte7[7:6] | hard-wired **2** | identity + liveness |

**Orchestrator-verified from disk:** both hashes ✓ · V97→V98 diff **146 B**, all in `0xC4B34–0xC4BCD`
+ `0xC4FFC`, **zero unattributed** ✓ · **every cal cell identical to V97** ✓ · **GATE 2 re-derived
independently — exactly 3 stores across exactly 2 cells (`gp-0x1514`, `gp-0x1511`)** ✓.
**GATE 1 PASS** on all four cells; wider 32-bit span scan **67 accesses, ZERO span-only hits**.
**Hook proven from the image to be the 100 Hz `0x14A` builder, NOT the 1 kHz task** (`0x55C14 =
movea 0x14A,r0,r8`). Cave **112 → 154 B (+37.5 %)**, 12.7 % of the extent — stated, not claimed away.

🛑 **SCORER WARNING — the ~50-build "byte4[7:3] is always ODD" convention DOES NOT HOLD on V98.**
`b3` is a measurand, so **byte4 goes EVEN whenever `gp-0x6752 < 0` — that is the FINDING, not a fault.**
Liveness moved to **byte7**. Without this a scorer pulls a working build.
🛑 **`0x7FFF` sentinel pre-registered:** when the plausibility latch fires, `gp-0x6bfe` = `0x7FFF` and b6
reads TRUE for an unrelated reason. The latch rails `gp-0x6b70` ⇒ **427 pins at exactly 1023.
Score b6 only on frames with 427 ≠ 1023, and report the excluded count.**
⚠ **One open gap before any flash:** `mov`'s flag-transparency is **BELIEF** — SLEIGH + Honda's own
instruction scheduling, not a manual quotation.

**DRIVE PROTOCOL: ONE parking-lot creep, LKAS engaged, hands on — stop the moment the symptom is felt.**
~15–30 s of engaged frames. **No matched arms, no episode counts, no highway, no second drive.**
Optional and free: a few seconds of the same creep LKAS-off; and 60 s turning the wheel by hand with the
car OFF (a positive is strong, a negative is weak).

---

## 🛑 V97's VERDICT — UNINTERPRETABLE. Not falsified. **Do not re-dose `0xC63AC`.**

`0xC63AC` 102 → 150, the Path-2 IIR pole in `FUN_00038148`. **FLEW route `0x80`.**

✅ **THE LEVER IS LIVE — BOTH OF THE OPERATOR'S OWN HYPOTHESES ARE REFUTED.**
- *"A mistaken cal address"* — **excluded 3 ways.** `0x38202` bytes `e5 6f ad 73` = `ld.hu 0x73ac[tp]`;
  `tp+0x73AC = 0xC63AC` reads **102 / 102 / 150** (stock / V96 / V97); off-by-0x1000 excluded
  (`0xC53AC` = 683, identical in all three) and the six neighbour cals `0xC63A0..0xC63AE` all 1024
  unchanged. Census **1 reader / 0 writers**, five methods, Ghidra∖Python set-difference **EMPTY**.
- *"The logic we touched isn't used"* — **REFUTED statically AND dynamically.** `FUN_00038148`'s sole
  caller guards it with `andi 0x830,r25,r28` + `cmp r0,r28`/`be` @`0x22672`, **byte-identical to the
  guard on the assist-channel mixer** @`0x225EE` ⇒ **a shut gate would mean NO POWER ASSIST AT ALL.**
  And `sign(gp-0x374c)` **toggled 181× in 109 s** on this route. **No speed gate, no rate gate, no
  engagement gate anywhere on the path**, and the accumulator update precedes the only in-function gate.

🛑 **WHY IT COULD NOT BE SCORED — three independent reasons, none of them the lever:**
1. **NO INSTRUMENT.** V96's cave is carried unchanged; its regressor is **34× over-range** — `M ≡ 0` on
   **10,749/10,749** frames (third replication: 7e 99.90 %, 7f 99.97 %, r80 **100 %**), `Mlo` duty
   **0.0000**. S1/S2 **VOID** — conceded in `builds/v80_v107/build_v97_tva.py:99-100` **before the flash**.
2. **EXPOSURE.** **1** engaged hands-off episode ≥2 s and **1** decaying-angle return, against **24/27**
   and **14/11** on 7e/7f — and the `|Q| = 1.233` direction result rests on **25**.
3. **THE OBSERVABLE.** **DC gain is 1.000000 at any `A` — a POLE, not a GAIN** ⇒ **no amplitude
   statistic can see it, and none was pre-registered.** Measured anyway: phase contrast **+3.27°** in
   one cell, **−4.08°** in the other (**opposite signs**); 6–9 Hz cross-build ratio **5.92× is SMALLER
   than r7e's own split-half noise 6.98×**; the `sign(gp-0x374c)` crossing-rate test sits inside its own
   split-half noise with the control bit moving too. **Four channels, four closing mechanisms.**

⊕ **V97 NEVER CLAIMED a grinding or ratcheting fix.** Its header prices only a **21 Hz cost** and argues
direction from **hands-off returns**. *"No difference in grinding"* **is consistent with the build
working exactly as specified.**

⚠ Correction: the build docstring's per-`A` phase row is **mis-tabulated** (correct: −23.63° / −15.81°);
the **deltas the decision rested on are right**. Task rate is **1000 Hz, EVIDENCE** (`0xC64DF` = 100
measured on-car at 100.00 ms + the `0x830 ⊆ 0x930` lockstep) — 🛑 **NOT from OSTM0**, which is 500 Hz
because PCLK is 40 MHz; that inference is a recorded red herring an agent nearly shipped this session.

🛑 **The number V95 is BURNED — see §A5.** ⚠ The `rlog-tools/v95_*.py` files are **analysis**
scripts, not build scripts.

🛑🛑 **THIS FILE HAS A HARD SIZE CAP: 256 KB. Keep it under ~150 KB.** On 2026-08-09 it reached
**506 KB / 6,114 lines / 53 sections** — past the `Read` limit, so no agent could load it in one call
and **the tail was silently invisible**. 47 superseded sections were split out verbatim to
**`docs/archive/STATE-ARCHIVE-pre-V89.md`** (432 KB) by `analysis-2020accord/archive/shrink_state_md.py`; the
2026-08-11 V90-flight headline went to **`docs/archive/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`**
(30 KB) at the 2026-08-12 close-out; **the V96/V94/routes-78-79/V88 flight headlines went to
`docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`** (54 KB) by `analysis-2020accord/archive/shrink_state_md_2026_08_13.py`
at the 2026-08-13 (later still) close-out — **177 KB → 126 KB**, each archived section's durable
facts confirmed to survive in `memory/` or `docs/BUILD-LINEAGE.md` before it moved. Nothing was
deleted. **Update this file IN PLACE at every close-out. Never append a new dated block — supersede
the old one.** Per-build history belongs in `docs/BUILD-LINEAGE.md`, narrative in `docs/HANDOFF-*.md`,
durable facts in `memory/`.

**Reading order:** this file → `docs/BUILD-LINEAGE.md` (RULES 3/5/6/7 first) → the latest
`docs/HANDOFF-*.md` → `memory/MEMORY.md` + `memory/MEMORY-PART2.md` + `memory/MEMORY_CONSTELLATION.md`.
🛑 `memory/MEMORY.md` was split in two on 2026-08-12 — it had reached **287 KB against a 256 KB `Read`
cap**, so its tail was silently invisible. **Read BOTH parts.** The archives are records, **not**
instructions — do not reason from them.

---

## ★★★★★ THE STRUCTURE, ESTABLISHED 2026-08-12 — V89 AND V97 PUSHED ON OPPOSITE ARMS OF ONE OBSERVER RESIDUAL

`FUN_00038148` @`0x38236-0x3823A`, coefficients **exactly ±1**, verified from raw bytes
(`0x38238 subr r15,r6` = opcode `0x0C`; `0x3823A add r9,r6` = opcode `0x0E`):

```
FUN_0003b8f6  — the 1 kHz PLANT MODEL / disturbance observer
                K0 0xC4080=0 (NEVER RAISE) · K1 0xC40D2=204 (V89, ON THE CAR) · relay 0xC40BC=600
                EMAs 0xC40D4=573 · 0xC40D6=246 · 0xC40D0=408 · 0xC40D8=3686   (all four VIRGIN)
      │ gp-0x6bfc → FUN_0003bc20 (plausibility ±20000, else force 0x7FFF)
      │ gp-0x6bfe ────── MODEL   ────────┐  UNFILTERED   ◄── V89's K1 acts HERE
LKAS 11-slot aggregator FUN_00026c80     │
      │ gp-0x6bfa ────── REQUEST ────────┤  UNFILTERED   (its ±20000 gate is DEAD — writer pre-clamps)
six lanes → ×sign(gp-0x6752) → ×2639(0xC6468) → <<4
      │ IIR pole 0xC63AC 102→150 = ALL OF V97
      │ (gp-0x374c>>4) ─ ACTUAL  ────────┘  ◄── V97's pole acts HERE.  MEASURED < 2048, 100 % of r80
                              iVar6
          gp-0x6b70 = sign(iVar6) × LERP(|iVar6|), clamp ±8192 (0xC6200)  = the PID REFERENCE
```

🛑 **BOTH ARMS ARE ESTIMATES OF THE SAME QUANTITY, in the same units, scaled by the same `0xC6468`=2639,
entering a DIFFERENCE.** ⇒ **V89's K1 measured FLAT and V97's pole felt like nothing, and one unmeasured
quantity explains both: the arms may be wildly unequal, so whichever you move, the residual barely
notices.** [BELIEF — but it is the first account explaining two nulls with one mechanism.]

🛑🛑 **A "≤ 9 % share" bound was computed and is RETRACTED — DO NOT REUSE IT.** Bounding one arm against
the other's *admitted range* is invalid for a difference of correlated estimates; the denominator is the
**residual**, not the range. **Path-2's share is UNRESOLVED, not small.**

### The Stage-2 transfer is FULLY READABLE — and the rescale is the IDENTITY
🛑 **`STATE.md` §A6b's "the transfer cannot be read from the image" is FALSE**, and so is the standing
*"`f′` swings ≥10× and cannot be pinned statically"*: **the swing is 1.000×.** `gp-0x6982`/`gp-0x6984`
(the X-divisor and Y-multiplier) have **ZERO writers image-wide** — Ghidra + raw disp16 + raw disp23 +
an exhaustive 32-bit-literal search, **with a working positive control** (the neighbours `gp-0x6980/86/
88/8A` all DO have `st.h` writers and the scan found them) — and both boot to **1024** from `.data`
(flash `0x8672E`/`0x8672C`). The `[204,2048]` cal rails guard a value that never moves.

Knots (mode 26, creep; `0xC63AE`=1024 ⇒ the LERP index is `|iVar6|` **raw**):
```
0.0 km/h  X [0,200,400,800,1200,1800,3000,5000,12000,14490]  Y [0,471,880,1408,1689,1953,2376,2844,4114,8192]
6.6 km/h  X [0,178,356,719,1200,1800,3000,5000,10681,14490]  Y [0,452,839,1382,1838,2131,2546,3043,4245,8192]
```
**Route 80 inverted:** `|gp-0x6b70|` p50 320 → `|iVar6|` **126–136** · p90 2,534 → **2,965–3,675** ·
max 3,187 → **5,681–6,891**. ⇒ **`|iVar6|` ≤ ~6,900 at creep, ~130 half the time** — 2.9× tighter than
the ±20,000 clamp. ⊕ **`|iVar6| ≈ 130` median against a six-lane term admitted to 2048 hints at strong
CANCELLATION between the three terms** — exactly what an observer residual should do. [live hypothesis]
⚠ **These numbers DO NOT TRAVEL above 50 km/h** — `0xC669A`/`0xC66A8` truncate the LERP's X axis to
7,000 there. ⚠ **`mode 24 ≠ mode 26` in THIS family** (recs 0/3/4/5 differ) — the
"stock ships 24 ≡ 26" memory is scoped to the **damper** families and does not generalise here.
🛑 **CORRECTED 2026-08-13 (later) — the parenthetical used to also claim "breakpoints differ"; that
is WRONG.** `tracer-c63ae` (crux verified by the team lead): **the mode-24/26 breakpoints do NOT
differ** — both read `[0,960,2560,5120,7680,10240,12800]`. Only records 0/3/4/5 differ, not the
X-axis knots.

### Other results from route `0x80`
- **427 lane (`gp-0x6b70`) is a GOOD instrument**: nonzero **98.29 %**, 250 codes, **0.000 % saturation**,
  p99 3,059 of a ±8192 clamp. Not a V64/V68-class dead probe.
- **The observer's plausibility latch has NEVER fired**: `427 == 1023` duty **0 on 87,423 frames** across
  80/7e/7f — and `>640` (the true reachable ceiling through the clamp) is also **0**.
- **`b3` constant ⇒ `gp-0x674e < 28` settles RULE 7 for the authority curve** — the `Y[last]=0` records
  are live; modes 28–39 excluded. That rung is now **SPENT** and can be reallocated.
- ⚠ **`0xC62EA` = 0 on V97 (stock 320 ≈ 5 km/h)** — the low-speed lockout has been disabled since ~V35,
  so creep sits in a regime stock Honda would have locked out. Context for anything felt at 5 km/h.

## → ARCHIVED 2026-08-27 — the V103→V107 superseded blocks
The six dated blocks for the **V103–V107** sessions (2026-08-13 final, 08-20 late, 08-21 early,
08-21 late, 08-22 early, 08-22 late) now live in
**`docs/archive/STATE-ARCHIVE-2026-08-27-v103-to-v107.md`** — verbatim, nothing edited.
V107’s and V106’s blocks are KEPT inline below, as the two most recent predecessor states.
⚠ They are a record, not an instruction, and their “on the car” lines are stale.

## → ARCHIVED SECTIONS — moved out 2026-08-21
Everything from *"ARCHIVED 2026-08-13 — V96's flight headline"* onward now lives in
**`docs/archive/STATE-ARCHIVE-2026-08-21-pre-v104.md`** — verbatim, nothing edited. That file holds the
archived flight headlines, the **STANDING CORPUS RESULTS**, the **STANDING INSTRUMENT CORRECTIONS**,
the methodology + signal-identity corrections, the tyre line, and the superseded on-the-car block.
🛑 **The instrument corrections and corpus results are still LOAD-BEARING — read that file before
any analysis session.**
