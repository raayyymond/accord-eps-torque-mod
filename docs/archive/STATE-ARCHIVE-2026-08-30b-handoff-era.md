# STATE ARCHIVE — blocks moved out of `docs/STATE.md` on 2026-08-30

These are a RECORD of what was believed when written, not an instruction. They were moved to keep
`STATE.md` under its working target; nothing here was retracted by the move. 18 blocks, 30.2 KB.

---

> 🛑🛑⭐⭐ **SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED TO UNRESOLVED. The
separation-based conclusions are UNAFFECTED.** I published *"r24 DAMPS at 6–9 Hz"* as EVIDENCE earlier
this session. The first external check of that **absolute** label fails. The instrument makes a
retrodiction that can be tested against V88, which raised r24 and measured three bands on-car:

| band | φ(T,rate) | r24 phase | work factor | **V88 on-car** |
|---|---|---|---|---|
| ratchet 6–9 | −120.7° | +143.9° | **−0.808** | 0.859× |
| mid 9–12 | −150.8° | +111.6° | **−0.368** | 0.604× |
| grind 15–22 | **+119.8°** | +16.5° | **+0.959** | **0.549×** |

**V88 helped MOST at 15–22 Hz — exactly where the instrument says r24 pumps hardest.**
`corr(work, V88 ratio) = −0.803`; the prediction required **positive**. ➕ **Flipping the sign gives
+0.803 and retrodicts V88 across all three bands**, which is what a globally inverted frame looks like.
🛑 **My controls pinned the PIPELINE, not the PHYSICS.** A constructed +90° lead reading +90°, and a
viscous torque landing in quadrature, establish internal consistency — they say nothing about whether
r24’s output reaches the motor with the same sign as `cs_rate`. That frame question was flagged OPEN
from the start, and this is the first evidence bearing on it. ⚠ The evidence is **weak**: n = 3 bands,
not independent, and **V88 changed 5 bytes, not only Lever B**. It is not proof of an inversion — it is
enough to withdraw the absolute claim.
✅ **WHAT IS UNAFFECTED, BY DESIGN.** Every actionable conclusion was deliberately re-anchored on the
**separation between lanes plus V88’s on-car result**, with no absolute label in the chain: r24 and
`gp-0x6ad4` are **76° apart on opposite sides**, V88 fixes r24’s side as beneficial, the PID lane is
**0.25× r24**, **V227’s ceiling does not bind**, the **span cal is a redundant gain knob**, the phase is
**structurally capped**, and **delivery lag is bounded at 3.25 ms**. **None of those use the sign.**
⇒ **V222 remains the flight candidate and the guidance is unchanged**, because it rests on V88’s direct
measurement. ⇒ **What IS withdrawn**: any statement that r24 damps or pumps *in absolute terms*, and
with it the claim that the record’s *"net PID DAMPS"* is a convention flip — **it may be the record that
is right and me that is inverted.**
Study: `analysis-2020accord/studies/mixer/r24_retrodiction_test_fails.py`.

> ⭐⭐⭐ **THE ANTI-DAMPING IS BROADBAND AND ITS PEAK IS AT 9–10 Hz — BETWEEN the two bands the kit
treats as its symptoms.** `Re(Z) = Re(S_TR/S_RR)` measured over 6 routes engaged, magnitude-weighted
rather than phase-only:

| band | mean Re(Z) | mean cos | coherence | |
|---|---|---|---|---|
| ratchet 6–9 | −23.5 | −0.401 | 0.532 | |
| **mid 9–12** | **−67.9** | −0.784 | **0.618** | ← **strongest, and best-measured** |
| the gap 12–15 | −51.3 | **−0.986** | 0.511 | near-perfect antiphase, less magnitude |
| grind 15–22 | −14.2 | −0.591 | 0.631 | |

🛑 **`Re(Z)` is negative across the ENTIRE 4–24 Hz range** — this is **broadband** anti-damping, not a
narrow mode. Its magnitude peaks at **10 Hz (−71.5)** and the anti-damping **power** peaks at **9 Hz**.
⇒ the dominant energy exchange is **~3× the ratchet band and ~5× the grind band**, and it sits in
**9–12 Hz** — a band the kit **scores but has never treated as a target**, since its named symptoms map
to 6–9 (ratchet) and 15–22 (grinding).
➕ **A phase-only read would have put the peak at 13 Hz** (cos −0.998, essentially 179° opposed) — that
is the *phase* extremum, but torque amplitude is lower there, so the *impedance* extremum is at 9–10.
**Magnitude-weighting moved the answer; phase alone would have mis-aimed a lever by 3 Hz.**
✅ Unlike the command–rate coherence null (0.14–0.23), **torque–rate coherence is 0.44–0.76 across
7–23 Hz**, so this is a real measurement over its whole range.
⚠ The **absolute sign** of `Re(Z)` still depends on the unresolved frame; what is frame-free — and what
this block asserts — is the **SHAPE**: the extremum is at 9–10 Hz and the band ordering is
**mid > gap > ratchet > grind**.
⇒ **Consequence for lever design: size and aim at 9–12 Hz, not only at 6–9.**

> ✅ **AND V222’S AIM WAS CHECKED AGAINST THAT — the gap is real but MITIGATED, and the fix is
DEFERRED, not taken.** Computed from the image floats (`0xC60A8/AC/B0/B4`, direct-form II, 1 kHz):
the car is `f0 = 55.23 Hz, r = 0.7966`; V222 is `f0 = 20.50 Hz, r = 0.9575`. V222/car by band:
**6–9 0.998 · 9–12 0.955 · 12–15 0.805 · 15–22 0.281 · 22–30 0.402** ➕ 🛑 **CORRECTED 2026-08-30 — the figures first published here (0.970 / 0.924 / 0.366 / 0.821) came from a PARAMETRIC RECONSTRUCTION, not the image floats, and were WRONG in the pessimistic direction.** V222’s biquad is **NOT symmetric**: its zeros sit at 20.50 Hz but its **poles at 15.50 Hz** (Honda’s own are 12.88 Hz apart, so the shape is structural). A `coef(f0, r)` reconstruction places poles AT the zeros and does not reproduce the build.. ⇒ **the notch cuts the band with
the LEAST anti-damping 2.7× and the band with the MOST by 8 %.** ✅ **But V222 is not blind to the
peak**: Lever B’s transfer is a 4 ms difference, which **RISES** with frequency — `|H|` **0.1955 at
7.79 Hz → 0.2630 at 10.5 Hz = 1.35× stronger at the Re(Z) peak than at the ratchet.** The broadband
lever is best-aimed exactly where the narrowband one is weakest.
🛑 **RE-CENTRING to 13 Hz is REJECTED**: 9–12 would improve to 0.460, but 15–22 degrades **0.366 →
0.807** (surrendering a measured grinding win) and 22–30 goes to **1.402 — a BOOST**, in the region that
folds into the scored 30–49 Hz band.
⏸ **WIDENING is DEFERRED, not rejected.** Lowering the pole radius improves **both** target bands at
once (r = 0.92: 9–12 **0.813**, 15–22 **0.254**), with DC held at exactly **1.000000** by
`c4 = (1+a1+a2)/(2+b1)`. 🛑 **But the skirt extends DOWNWARD into 6–9 Hz — precisely the band where
V214–V217 found the shelf had been cutting a REAL damper 7.15× below the car, a defect found only
through an ABORTED DRIVE.** At r = 0.92 the trade is **8.7 % of the 6–9 damper for a 14.1 % deeper 9–12 cut and only 2.7 % on 15–22** — i.e. it buys almost all of its value in the peak band, which is the right place, but pays for it in the wrong one.
That is far smaller than the 7.15× that caused the abort — **but it is the same DIRECTION, on the one
band four builds were just spent repairing, and it buys 14 % on a notch already delivering 2.7×.**
⇒ **Fly V222 as built.** If its drive shows residual 9–12 Hz content, **r = 0.92 is the pre-computed
follow-up rung** (`a1 −1.82475755, a2 +0.84640000, b1 −1.983432120, c4 +1.30628962`).
Study: `analysis-2020accord/studies/mixer/notch_aim_vs_where_the_energy_is.py`.

> ✅⭐⭐ **AND THE NOTCH IS NOW CLOSED, NOT DEFERRED: V222 IS THE CONSTRAINED OPTIMUM OF ITS OWN
FAMILY.** Searched **109,446** configs (zeros 12–30 Hz × poles 5–30 Hz × r 0.70–0.985). The constraint
set had to be built in **three passes, because the optimiser exploited every omission**:
> ① **band-mean constraints** → an apparent **+360 %**, but the 6–9 *mean* of 1.019 concealed a
**1.265× POINTWISE peak at 6.0 Hz** and a **Q≈33 pole at 7.0 Hz sitting on the ratchet.** Rejected on
**GATE 2** — a lightly-damped pole inside an already anti-damped loop.
> ② **pointwise CEILING only** → an apparent **+394 %**, achieved by **cutting 6–9 Hz to 0.528** — a
1.9× cut of the damper, the V214–V217 defect’s own direction. I had added a ceiling and removed the
floor.
> ③ **pointwise ceiling AND floor, no global lift, no worsening of 52–71 Hz** → best feasible scores
**12.65 against V222’s 23.30, i.e. −45.7 %.**
> ⇒ **nothing in the biquad family beats V222.** Every “improvement” along the way was a missing
constraint. **The notch lever is CLOSED.**

> 🛑🛑⭐⭐ **AND A SCORING TRAP THE SEARCH SURFACED: DO NOT SCORE 30–49 Hz ACROSS THE V222/V122
BOUNDARY.** V222 **removes Honda’s 55 Hz notch** in order to place one at 20.50 Hz. Every cache runs at
**fs ≈ 101 Hz ⇒ Nyquist 50.5**, and the record establishes that **52–71 Hz folds into the scored
30–49 Hz band** from **above Nyquist**, where it can be neither seen nor filtered.
**mean |H| over 52–71 Hz: car 0.1700 vs V222 0.6392 ⇒ V222 passes 3.76× more.**
⚠ A **911×** ratio appears at 55.2 Hz but is an **ARTEFACT** of dividing by the car’s notch null
(|H| = 0.0007) — **the honest figure is the band mean, 3.76×.**
⇒ **any 30–49 Hz difference between V222 and the car is CONFOUNDED** by genuine 52–71 Hz content the
build no longer notches, folded down by the sample rate. **It cannot be separated post hoc.** This
applies to **every notch build**, not just V222.
Study: `analysis-2020accord/studies/mixer/notch_is_the_constrained_optimum_and_the_alias_cost.py`.

> 🛑⭐ **AND THE ALIAS COST CANNOT BE ENGINEERED AWAY — THERE IS EXACTLY ONE BIQUAD.** The obvious fix
for the 30–49 Hz confound is to keep Honda’s 55 Hz notch **and** add the 20.50 Hz one, which needs a
second second-order section. **There is not one.** Scanned the entire cal region **`0xC4000`–`0xD8000`**
at 4-byte stride for float quads with biquad structure (stability triangle `|a1| < 1+a2`, `0 < a2 < 1`,
`|b1| ≤ 2`, non-trivial `c4`), rejecting constant blocks and monotone runs (lookup tables) and
requiring the notch to fall in a plausible 1–200 Hz control band:

```
     addr           a1         a2         b1         c4   zero Hz  pole Hz     DC
   0xC60A8    -1.53720    0.63462   -1.88080    0.81731     55.23    42.35   1.0000   <- the only one
   biquad-shaped quads in the ENTIRE cal region: 1
```

⇒ **one section places ONE notch pair, so the 55 Hz vs 20.50 Hz choice is STRUCTURAL.** The alias cost
can be **ACCEPTED or REVERTED — it cannot be removed**, and reverting would surrender the 3.6× grind cut
that is the build’s main grinding lever. ⇒ **accept it, and score around it** (drive card already says
so).
⚠ **Scope, stated precisely**: this establishes there is exactly one **float32 biquad coefficient block
in the cal region**. A second-order filter implemented in a different numeric format (int16 Q-format)
or with a non-contiguous coefficient layout would not be caught by this scan — the claim is about the
float32 layout, not about every conceivable filter. The record independently calls `FUN_0003b8f6`
*"the dormant biquad"*, singular, which agrees.
➕ Related: Honda shipped this section **DISARMED** (`0xC649B` = 0); the kit armed it at V103.

> ✅⭐⭐ **THE LAST UNCHARACTERISED REGION IS CLOSED: THE FOC CURRENT LOOP IS TRANSPARENT AT THE
RATCHET.** `gp-0x6b98` is *"the final merged command and the only path to FOC"*, and everything below it
was the one stage the golden model only **abstracts** (`motor_pwm_output` is a placeholder
`duty = q_current_ref / 51200`, with *"[OPEN] the PWM carrier Hz"*). It is also where the record says
the ratchet physically lives — *"motor/rack-side, which no channel on this bus observes."* So it looked
like the obvious remaining place to search. **It is not, and the bound is not close.**
The model verifies the structure even where the carrier Hz is open: the FOC/PWM ISRs
(**EIIC 0x600** = ADC-complete inner loop, **0x970**) run **asynchronously and FAR FASTER** than the
1 kHz task, on a **~4–8 kHz** carrier. A current loop is tuned to 1/10–1/20 of switching ⇒ **200–800 Hz**
bandwidth. As a first-order loop at 7.79 Hz:

```
    BW (Hz)   |H| @7.79    phase        verdict
        800     0.99995    -0.56 deg    transparent   <- plausible for an 8 kHz carrier
        200     0.99924    -2.23 deg    transparent   <- plausible for a 4 kHz carrier
         50     0.98808    -8.86 deg    mild
         25     0.95472   -17.31 deg    mild
```

⇒ **even at an implausible 25 Hz bandwidth the loop contributes −17.3° and 0.955 gain.** For it to
matter at the ratchet (≈45°) the current loop would need **BW = 7.8 Hz — slower than the 1 kHz task
that feeds it**, contradicting the verified ISR structure.
⇒ **[EVIDENCE] the FOC gains cannot be a ratchet lever at any plausible tuning.** And *"motor/rack-side"*
points at the **PLANT** — mechanical, which **no firmware calibration can change** — not at this loop.
⚠ It is also the **worst edit class available**: motor control, **no instrument on it**, and code caves
in exactly this kind of region are this kit’s **only bricking class** (V24, V27, V48B).

> 🛑⭐⭐ **WITH THAT, THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION FROM THE AGGREGATOR.**
Upstream: the **aggregator lane census** is closed at 7.79 Hz and only r24 has ever been shown to help.
Downstream: the **governor** is retired by the task rate, and the **FOC loop** is transparent. Sideways:
the **notch** is the constrained optimum of its only second-order section, the **span cal** is a
redundant gain knob next to a double kill-switch, **creep damping** is exhausted, **authority** caps at
11×, **Lever B** is linear across its whole uint16 range, and **delivery lag** is bounded at 3.25 ms
against a 77 ms inversion threshold. ⇒ **The binding constraint is now a DRIVE, not analysis.** V222 is
built, verified and audited against all three asks; **nothing further can be learned about it from data
already on disk.**

> ✅⭐ **NEW GATE: NO ORPHAN BYTES. Every non-stock byte on the whole ladder has a written home.**
An **orphan** is a byte that differs from stock and that **no document in the kit mentions**. Orphans
are how this kit loses things: **V42’s ratchet fix sat silently REVERTED across eighteen builds
(V53–V70)** because nothing checked that the bytes on the candidate still matched the bytes the record
described. A byte nobody can explain is the same failure pointed the other way — and the operator is
entitled to know what every non-stock byte in his ECU does.

```
  build   payload bytes   runs   cited     record: 4998 distinct 0x addresses across 789 files
  V217         320         115   100.0 %
  V221         320         115   100.0 %
  V222         323         116   100.0 %   <- the flight candidate
  V223-V226    323         116   100.0 %
  V227         324         117   100.0 %
```

⇒ **ZERO orphan runs anywhere on the shelf.** ➕ Two cells that looked unannotated when I first grepped
are in fact fully documented — my search was too narrow, not the record: **`0x2A1F0` is V57’s decouple
displacement** (`746C`→`7CD0`, which is *why* the stock dump reads `0xFFFF` at `0xC6CD0`), and
**`0xC61C0`/`C2`/`C4` are the angle-rate tiers of the `STEER_STATUS` debounce SM** raised to unsigned
max at V36, with `0xC64B4`/`B6`/`B8` the matching V37 gentle-EME defeat.
⚠ **Scope:** this proves each byte has a written **home**, **not** that the annotation is correct,
current, or that the byte does what it claims — those need the lineage and a drive.
➕ Correcting a figure I gave the operator: the cumulative delta is **323** payload bytes, not 331; the
first count failed to exclude the `0xE4FFC`/`0xE5FFC` CRC trailers.
Gate: `analysis-2020accord/verify/no_orphan_bytes.py` (takes a build tag, defaults to v222).

> 🛑🛑⭐⭐⭐ **THE RATCHET BAND CANNOT BE SCORED BY BAND POWER — IT NEEDS ~7 HOURS PER ARM. This may
be why "nothing has moved micro-ratcheting in sixty builds."** The kit’s design law says every build
must be interpretable from ONE short symptomatic drive, and *"UNINTERPRETABLE is a DESIGN FAILURE on
our side."* That was never checked quantitatively. Measured, from real cached data — the
episode-to-episode spread of the band/control ratio, which **is** the noise floor for a single-episode
drive:

```
  band         sd(log10)   MDE, 1 episode/arm   MDE, 2 each   V88 measured on-car
  ratchet 6-9     0.587          42-45x            14.2x           0.859x
  mid 9-12        0.392          11-13x             5.9x           0.604x
  grind 15-22     0.426          13-15x             6.5x           0.549x
```

⇒ **one episode cannot resolve ANY of them**: the floor is 12–45× and the effects are 1.2–1.8×. V88 got
its 0.549× from a **full route**, not one episode. Exposure needed per arm at 80 % power:

```
  band          n episodes   minutes/arm      if V222 DOUBLES V88's effect
  grind 15-22        42          14.0          11 episodes,   3.7 min   achievable
  mid 9-12           51          17.0          13 episodes,   4.3 min   achievable
  ratchet 6-9      1241         413.7         311 episodes, 103.7 min   NOT achievable
```

🛑 **The ratchet band is 30× more expensive than the other two**, because its episode-to-episode
spread is a factor of **3.9** — the ratchet is INTERMITTENT, so 20 s windows vary enormously while the
effect is small. ⇒ **band power could never have detected a V88-sized ratchet improvement at any
exposure this operator has ever given.** ⚠ **That does NOT mean improvements happened** — it means the
instrument cannot answer the question, so sixty builds of "no ratchet change" is **weaker evidence than
it reads as.**
✅ **This is exactly why the standing instruction is "SCORE BANDS; LET THE OPERATOR SCORE SYMPTOMS"** —
now quantified. The operator’s verdict needs **one** episode; the band readout needs **minutes**. They
are different instruments and a 20 s band ratio must not be reported as evidence either way.
➕ **The known alternative for the ratchet is RING-DOWN** — the record calls ζ = 0.017–0.036 *"the only
estimator that passes its control"*, and it is a per-burst measurement rather than a band average, so
its variance structure is different. **Its power has NOT been computed; that is the open question.**

> ⭐ **RING-DOWN COMPUTED: it is the better ratchet instrument, but only for LARGE effects — and a
quality filter BIASES AGAINST the mode of interest.** 304 ring-down events extracted over **75.1
engaged minutes** across 6 routes (**4.05 events/min**), from command drops ≥35 % within 100 ms.

```
  min R2   kept  ev/min  p50 zeta  sd(log10)  min/arm to see a 2x change
     0.0    304    4.05    0.0400     0.474            9.6
     0.3    171    2.28    0.0709     0.294            6.6   <- best exposure
     0.8     52    0.69    0.1384     0.272           18.8
     0.9     29    0.39    0.1427     0.209           20.7
```

✅ **For a 2× change in ζ, ring-down needs ~7–10 engaged min/arm against band power’s ~104.** That is a
**10–15×** improvement and makes a large ratchet effect **measurable on a drive somebody would
actually do.**
🛑 **But it does NOT rescue a V88-sized effect**: 1.16× still needs **209–404 min/arm**. ⇒ **neither
instrument can resolve a small ratchet change at any realistic exposure** — and that conclusion is
robust across every filter setting, so it does not depend on implementation details.
🛑🛑 **THE TRAP, and it is the interesting part: filtering on fit quality selects AGAINST the
ratchet.** As R² rises the median ζ climbs **0.040 → 0.143** — but the record’s ratchet is
**ζ = 0.017–0.036 (Q 14–29)**, and ζ = 0.14 is **Q ≈ 3.6**, heavily damped. A **lightly** damped mode
barely decays across a 0.5 s window, so its fit is POOR by construction; a clean exponential over that
span is something **faster-decaying and probably not the ratchet at all.** ⇒ **do not filter ring-downs
on R²** without checking what it selects.
⚠ **Scope:** this is a quick re-implementation, not the kit’s validated scorer, and it does **not**
reproduce the record’s ζ (0.040 unfiltered vs 0.017–0.036). The **exposure ratios** are indicative; the
absolute ζ values are **not** trustworthy here. ⇒ **OPEN: re-run this variance estimate through
`rlog-tools/score/ratchet_ringdown.py` with its own controls** (time-reversal, random-frame) before any
build is sized against it.

> 🛑⭐⭐ **AND THE RATCHET ARM OF V222/V224 IS UNPRICED AGAINST THAT FLOOR — its lane’s SHARE and its
SIGN have both never been measured.** `0xC63AE` is **1024 in stock and on the car**, **512 on
V217–V223**, **256 on V224**. The record annotates it only as a *"Stage-2 input"* scale on the second
aggregator chain. A weight cut moves ζ only as much as that lane weighs in the net:

```
  D_net(w) = D_other + w*D_lane ;  f = |D_lane| / D_car
     lane ANTI-damps:  zeta_new/zeta_old = 1 + f*(1-k)      cutting it HELPS
     lane      damps:  zeta_new/zeta_old = 1 - f*(1-k)      cutting it HURTS

     lane f    V222 k=.5 anti   V224 k=.25 anti   V222 damp   V224 damp
       0.20         1.100            1.150          0.900       0.850
       0.50         1.250            1.375          0.750       0.625
       1.00         1.500            1.750          0.500       0.250
       2.00         2.000            2.500          0.000       0.000
```

⇒ to clear the **2.00×** ring-down floor, **V222 needs f = 2.00** and **V224 needs f = 1.33** — i.e. this
ONE Stage-2 input would have to supply anti-damping worth **1.3–2× the entire net damping.** (f *can*
exceed 1, since `D_other > D_car` when the lane is anti-damping, but that is a lane dominating the whole
balance.) **⇒ if the lane is anything less than dominant, the ratchet arm is BELOW the measurement
floor — unmeasurable by design, which is the kit’s own definition of a build failure rather than a lever
failure.**
🛑 **And the SIGN is the load-bearing unknown.** If the lane **damps**, cutting it makes ζ **worse**:
at a modest f = 0.5, **V224 would cut ζ to 0.62× the car.** Nobody has measured which way it goes.
✅ **Scope — this does NOT argue against flying V222.** `0xC63AE` = 512 is the V217 baseline, not a new
V222 edit, and the build’s audited levers are Lever B and the notch. What it says is narrower and
worth saying before the drive rather than after a null: **the ratchet arm specifically is unpriced, so
a ratchet null on this drive licenses NOTHING about `0xC63AE`.** The grinding and authority arms are
priced and audited; this one is not.
➕ Corrected mid-derivation: my first pass had a sign error that made a **bigger** cut need a **larger**
lane share, which is backwards. The table above is the corrected algebra and passes that sanity check.

> 🛑 **AND THE SIGN CANNOT BE RECOVERED FROM CACHE — every 427-derived channel is RECTIFIED, verified.**
The obvious move was the r24 method: reconstruct the lane and measure its phase against rate. It does
not work here, and the reason is worth recording. Checked across **r7e / r80 / r81 / r82** (V96–V99, the
builds that put `gp-0x6b70` on CAN 427 at `sar 6`):

```
  ab_mt              0..251, 250 distinct, ZERO negatives   <- the 427 torque byte, RECTIFIED
  probe / field / raw14_b4   only 4-8 distinct values       <- cave threshold rungs, not waveforms
  slow3 / g6ac2      constant                               <- carry nothing on these routes
```

⇒ **rectification destroys the sign by construction**, and the cave channels are **comparator duties**,
not sampled waveforms — neither can yield a phase. The record’s *"CAN 427 is RECTIFIED"* is confirmed
empirically here rather than quoted.
➕ **Why r24 worked and this does not:** r24’s **input** (column torque) is on the wire **unrectified**,
so its lane could be reconstructed from a known transfer applied to a known signal. `gp-0x6b70` has no
equivalent unrectified input available — the chain `FUN_00038148 → gp-0x6b70` sums several weighted
lanes, and reconstructing it would require every one of them.
⇒ **The sign needs ONE CAVE SIGN BIT.** ✅ That is a **proven, low-risk pattern in this kit**, not a new
cave class: **V70 flew a 4-bit sign probe** and **V88’s `b7` carried a sign at 100 Hz**. It is the
cheapest instrument that would settle whether cutting `0xC63AE` helps or hurts.
⚠ But it is still a **cave**, and caves are this kit’s **only bricking class** (V24, V27, V48B) — so it
is a proposal for after V222 flies, not a reason to delay the drive.

> ✅⭐ **AUTHORITY AUDIT: V222’S 8× STEP SCALES ITS CLAMP EXACTLY — margin identical to the car to four
digits.** A gain raise whose forward clamp does not follow silently turns the authority lever into a
**clipper**, so this was checked from the images rather than assumed. `lane_max = (0xC61BE × gain) >> 15`
must stay under the clamp `0xC61B2/B4`, which must stay under the EME wall `0xC674E`:

| build | gain | lane max | clamp | EME wall | margin |
|---|---|---|---|---|---|
| **V122 (the car)** | 6.0× | 2505 | 3072 | 5120 | **1.2263×** |
| **V217 / V221 / V222 / V223** | 8.0× | 3341 | 4096 | 5120 | **1.2260×** |
| V225 (the 10× rung) | 10.0× | 4176 | 4608 | 5120 | 1.1034× |

⇒ **V222 preserves the car’s clamp margin exactly** — the 8× step is proportional, not a bare gain
raise. ➕ **And V225’s smaller margin is NOT an oversight**: proportional scaling to 10× would need clamp
byte **20 = 5120, which is EXACTLY the EME wall**, and the ordering constraint requires strict
inequality. **18 is forced by the wall, not chosen carelessly.** ⚠ Byte **19** (margin 1.165×) was
available and would give **5.6 % more headroom** while still clearing — free if V225 is ever re-cut.
🛑 **STRUCTURAL CEILING ON THIS PATH — and it is CLOSE.** `lane_max` reaches the EME wall at 12.26×, but the practical limit is tighter because the clamp is a BYTE << 8 and must sit strictly between them:
```
    6x  lane 2505  clamp bytes 10..19  best margin 1.942x
    8x  lane 3341  clamp bytes 14..19  best margin 1.456x   <- V222
   10x  lane 4176  clamp bytes 17..19  best margin 1.165x   <- V225 (built with 18 = 1.103x)
   11x  lane 4594  clamp bytes 18..19  best margin 1.059x   <- the LAST workable step
   12x  lane 5011  NO VALID CLAMP EXISTS -- the path is exhausted
```
⇒ **the forward-gain authority lever has ONE ~10 % step left beyond V225, not an open runway.** Past 11× the clamp cannot be placed at all, and a gain raise there would clip by construction.

> ✅⭐ **THIRD ASK CLOSED — LEVER B CAN NEVER CLIP THE MICRO REGIME, AT ANY VALUE IN ITS RANGE.** The
record’s standing instruction on peak command oscillation is *"roughness is a SMALL-COMMAND phenomenon
… size levers for the micro regime"*, so the question is whether V222/V223 stay **linear where the
roughness actually lives**, not at the peaks. Measured `|dT|` over the span-4 ms window, pooled across
6 routes engaged, **n = 455,183**: **p50 16.5 · p90 104.1 · p99 298.9 · max 977.4** counts.
Lever B saturates when `|dT| × cal/1024 ≥ 8192`:

```
        cal   x car  |dT|_sat  sat duty  micro gain  delivered
       5244    1.0x    1599.7    0.000%       84.5     100.0%   <- the car
      13107    2.5x     640.0    0.014%      211.1     100.0%   <- V222
      26214    5.0x     320.0    0.740%      422.2      98.6%   <- V223
      39321    7.5x     213.3    3.093%      633.2      94.0%
      52428   10.0x     160.0    5.674%      844.3      88.1%
      65535   12.5x     128.0    7.859%     1055.4      82.6%   <- cal MAX (uint16)
```

⇒ **V222 delivers 100.0 % of its dose and V223 delivers 98.6 %** — both fully linear in the micro
regime, with micro gain scaling **exactly proportionally** (84.5 → 211 → 422). ➕ **And the whole ladder
is usable**: even at the cal maximum, saturation onset (128 ct) sits **7.8× above the p50 of 16.5 ct**,
so **no uint16 value can clip the regime the symptom lives in**; delivery degrades only gracefully, to
**82.6 %** at the extreme. ⚠ What DOES clip is the top of the distribution — 7.9 % of frames at cal max
— i.e. large excursions, not roughness. ⇒ **the dose reaches the symptom, and the ladder has room
beyond V223 if the drive asks for it.**
➕ Correcting my own working line: an intermediate print called the high end *"mostly clipped"*. It is
not — **82.6 % still arrives at the maximum.**

> ✅ **PRE-FLIGHT AUDIT OF ALL THREE ASKS IS NOW COMPLETE.** ① **Grinding** — the notch cuts 15–22 Hz
2.7×; it reaches the 9–12 Hz `Re(Z)` peak by only 8 %, but Lever B covers that band **1.35× more
strongly than the ratchet**, and both re-centring and widening are priced and deferred. ② **LKAS
authority** — the 8× step scales its clamp **exactly**, preserving the car’s margin to four digits;
the path’s structural ceiling is **11×**. ③ **Peak command oscillation** — the dose is **fully linear in
the micro regime** and cannot be clipped there at any cal. **Nothing in the audit argues against flying
V222 as built.**

> 🛑 **AND THE FRAME TEST IS INCONCLUSIVE — reported as such, not dressed up.** The plan was to
calibrate the pipeline against the operator-confirmed *"+ LKAS demands negative steering angle"*.
Measured: median `corr(sc_tq, cs_ang)` = **−0.166**, which matches the convention — **but 2 of 6 routes
come out POSITIVE** and the magnitudes are **0.015–0.413**, i.e. noise-level. The 0.1–0.5 Hz phase reads
**−89.3°**, dominated by plant dynamics rather than a clean 0/180 readout. ⇒ **the frame is NOT
resolvable from bus data**; it needs a probe putting the delivered assist on the wire with a known
sign, which is a cave build. **It blocks nothing** — every actionable conclusion is anchored on V88.

> 🛑 **RECORD DEFECT FIXED — `r95` is V101, not V102, and the correction had been made in only HALF
the files.** `r95` flew **V101 = 8× (`0xC6CD0` 7128) with Lever B REMOVED** (`GAIN8X.C6CD0.7128-NOLEVERB`);
`r95_v102_prereg.py` is the pre-registration **FOR** V102 **MEASURED ON** r95=V101, and its own docstring
says so — the filename was read as an attribution. `cal_association_scan.py` and `cal_scan_stability.py`
had already been corrected; **`dissociation_full_corpus.py` and `knee_headroom.py` had not**, and the
latter is a **cal-association scan**, so it was attaching **gain 5346 to a 7128 route — a 1.33× error on
the single most important cal.** All four now agree, with a guard that scans every live script.
➕ **Two image-reading traps recorded**, both of which returned plausible-looking wrong data rather than
an error: **(1)** in a `*_plain_image.bin` the **file offset IS the address** — rebasing by `0x13000`
yields `0xFFFF` for every cal and an arm byte of `0x63`; **(2)** a bare `*v104*` glob matches
`SUPERSEDED-DO-NOT-FLASH-…` **before** the live image, because `S` sorts before `_`.


## 📁 **EARLIER BLOCKS (20) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

