# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V168 SUPERSEDES V158 AS FLY-FIRST.** V168 *is* V158 plus one byte, so it carries both levers, and the two symptoms score from the SAME 15 s episode in different bands (grind 15-25 Hz, ratchet 5-12 Hz, both in `cs_tq`) — **separated by the INSTRUMENT, not by the build**. Fly V158 alone only to isolate the grind lever on FEEL. Card: `docs/scoring/DRIVE-CARD-V168.md`.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-assist-map-session.md` carries every finding, every retraction and the open-items list with what would close each.
## ⭐⭐ **THE NOTCH DELIVERS MOST EXACTLY WHERE THE GRIND IS WORST — and this supersedes the 7.7×**
Last section's "honest 7.7×" was computed on the **POOLED** spectrum. Per route, the engaged/manual
grind ratio varies enormously, so pooling was misleading **in both directions**:
```
   engaged/manual GRIND power ratio, 15-25 Hz on cs_rate, per route (30 routes)
     p10   2.3x     p25  7.7x     p50  24.6x     p75  57.9x     p90 102.9x     max 397.1x  (r9e)
```
✅ **That reconciles the discrepancy.** The recorded *"9,200× less power with LKAS off"* and my
pooled *11.3×* are not in conflict — they are different points on a very wide distribution. **Neither
is "the" number.**

✅ **AND THE NOTCH'S BENEFIT TRACKS SEVERITY**, because loop gain is highest where the grind is worst:
```
   worst quartile (eng/man >= 57.9x)   median ratio 87.8x  ->  notch gives 51.9x
   best  quartile (eng/man <=  7.7x)   median ratio  2.7x  ->  notch gives  2.4x

   worst individual routes:  r9e 397.1x -> 224.3x  ·  r96 168.4x -> 102.4x  ·  r95 157.9x -> 89.5x
```
⇒ **THE OPERATOR-FACING STATEMENT: on the drives where grinding is worst, expect roughly 50× less
grind power; on drives where it is already mild, roughly 2×.** That is the right shape for a fix — it
does the most when it is needed most — and it is far more useful than any single averaged figure.

🛑 **THE NUMBER HAS NOW BEEN CORRECTED TWICE. The progression is the point:**
```
   21.5x   open-loop score            -- valid only for RANKING designs; attenuates the
                                         disturbance floor, which a notch cannot remove
    7.7x   closed-loop, POOLED        -- right method, wrong aggregation: pooling a median
                                         spectrum underweights the bad routes
   2.4x .. 51.9x   closed-loop, PER ROUTE   <- the honest answer, and it is a RANGE
```
**A single number was the wrong output all along.** Record the range, not a point estimate.

## 🛑⭐ **THE CLOSED-LOOP PREDICTION IS *WEAKER* THAN THE OPEN-LOOP ONE — MY NOTCH FIGURES WERE OVERSTATED**
Every notch estimate so far multiplied the measured spectrum by `|H|²`. That treats the filter as a
feedforward attenuator. The grind is a **closed-loop** effect, so the measured engaged/manual ratio
identifies the loop gain directly: `R = 1/|1−L|²`.
```
   cs_rate, 15-25 Hz, pooled creep windows
     engaged (measured)      3.2
     manual  (measured)      0.3      <- the floor a broken loop returns to
     OPEN-loop prediction    0.2      x16.9 reduction   <- what I have been quoting
     CLOSED-loop prediction  0.4      x 7.7 reduction   <- the honest number
     engaged/manual ratio   11.3x     <- the CEILING on any assist-path fix in this band
```
🛑 **The open-loop estimate attenuates the DISTURBANCE FLOOR as well** — but that floor is set by
road and plant, and **the notch sits in the ASSIST path, so it cannot remove it.** The loop can only
give back what it added.
⇒ **CORRECTION: the "21.5× / 15.0× / 14.3×" figures quoted for V188/V195/V196 are OPEN-LOOP and
OVERSTATE the achievable reduction.** The honest band-integrated prediction is **~7.7×, with 11.3× as
the hard ceiling.** The *ranking* of the designs is unaffected — they were all scored the same way —
so V195's re-fit is still better than V188's, but the absolute promise was too large.

⊕ **The notch DOES fully break the loop at its centre**: `g = 0.0025` at 19.73 Hz drives `R` from
27.8 to **1.00** — exactly the manual level. It is away from the centre that the ceiling bites
(`g` 0.26–0.60 at 22–25 Hz ⇒ `R` only 1.5–2.4).

⚠ **A DISCREPANCY TO FLAG, NOT RECONCILE:** this gives loop gain **L ≈ 0.78–0.81** at the peak — an
amplified resonance, **not** the near-unity instability implied by the recorded *"9,200× less power
with LKAS off"*. Different channel, band and conditions; **do not treat 9,200× and 11.3× as the same
measurement.** Which is right matters for how much the notch can deliver, and **only a drive settles
it.**

⊕ Simplification stated in the tool: `L` is taken real and positive near the resonance (worst case).
A power ratio does not identify phase, so this is the right order of magnitude, not an exact figure.
⊕ Tool: `rlog-tools/score/closed_loop_notch_prediction.py`.

## 🛑⭐ **THE 8× LKAS GAIN HAS BEEN TRIED AND ABANDONED THREE TIMES, NOT ONCE**
Backfilling the lineage from the images (V122–V196, 57 builds) immediately turned up history the
record does not carry:
```
   0xC6CD0   the LKAS gain      stock 0xFFFF (inert)
     V101   3564 -> 7128   4x -> 8x    ** and the grind came back **
     V102   7128 -> 5346   8x -> 6x
     V124   5346 -> 7128   6x -> 8x    <-- undocumented
     V137   7128 -> 5346   back to 6x  <-- undocumented
     V142   5346 -> 7128   6x -> 8x    <-- undocumented
     V147   7128 -> 5346   back to 6x  <-- undocumented
```
🛑 **8× was reached and backed away from THREE separate times.** My authority recommendation
(*"confirm the grind fix, then 6× → 8×"*) therefore enters **territory that has already failed
three times**, not unexplored ground. It is still the right *sequence* — the notch is what breaks
the gain/grind coupling, and that is genuinely new — but **the prior on 8× is much worse than the
V101 story alone suggests, and the operator should be told that before it is proposed again.**
⊕ Also surfaced: **`0xC40BC`** (the Coulomb ramp knee) was raised **3000 → 3600 at V151 and reverted
at V152** — another undocumented try-and-back-off.

## ✅ **THE LINEAGE GAP IS PARTIALLY CLOSED — `grep <address>` WORKS AGAIN FOR V122–V196**
`docs/BUILD-LINEAGE.md` carried a banner: *"THIS LINEAGE STOPS AT V121. V122–V178 HAVE NO ROWS —
INCLUDING THE FLYING BUILD."* That file is a **mandatory pre-read before proposing any calibration
edit**, and the standing rule *"grep the lineage before naming any address"* **silently passed** for
every cell those builds moved. That is how the 10× K1 dose and the 72 dead bytes stayed invisible.
✅ **`docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md`** — **generated, not narrated**: every row is
a byte diff between two images on disk. **43 cells across 57 builds, 7.4 KB.**
⚠ **Honest limits, stated in the file itself:** it carries **no reasoning**; **not every build
number has an image** (gaps 122→124, 125→127, 127→129, 129→131, 131→137, 142→147, 161→164,
165→167, 177→179, 181→183), so a change across a gap reads as *"at or before this build"*; and
anything load-bearing should still be diffed **against the stock image**, not against the file.

## ✅ **THE THIRD SYMPTOM RESOLVED: "PEAK COMMAND OSCILLATION" NEEDS NO SEPARATE LEVER**
🛑 **A lead/lag test is NOT usable here, and that was established BEFORE running it:** at 20 Hz one
period is 50 ms = **5 samples** at 100 Hz, so lag resolves only modulo half a period, while
openpilot's latency is 1–3 periods. Coherence is usable; lag is not.
```
   sc_tq x cs_rate       @ 1 Hz    @ 8 Hz    @ 20 Hz
   pooled                 0.115     0.119      0.180
   hands OFF (31 win)     0.338        -       0.181
   SHUFFLED floor         0.049     0.050      0.048
```
✅ **The low pooled 1 Hz figure was a MIXED-EXPOSURE ARTEFACT.** Hands-off it rises to **0.338, ~7×
the floor** — the command *does* move the wheel at 1 Hz. **This was flagged as a question, not
reported as an authority finding, and the stratification is why.**
✅ **20 Hz coupling is weak but real (0.181, 3.8× floor) and UNCHANGED by hands** ⇒ not driver-related.
➕ **The decisive fact is a prior, not this test: the LKAS lane is a ~1–5 Hz low-pass, so openpilot
CANNOT COMMAND a 20 Hz oscillation.** Whatever the 3.3× excess in `sc_tq` is, it is not commanded.
⇒ **the command's 20 Hz content is the command REACTING to the grind (or an artefact), not driving
it ⇒ no separate firmware lever is indicated for the third symptom, and the notch in V195/V196 is
already the intervention that addresses it.**
⚠ Only **31 hands-off and 1 hands-on** 20.5 s episodes exist in the whole corpus — consistent with
the earlier finding of zero continuous 15 s hands-on engaged-creep windows. **Hands-on remains the
corpus's blind spot.**
⊕ Tool: `rlog-tools/score/command_coupling_at_grind.py`.

### ⇒ ALL THREE STATED SYMPTOMS NOW HAVE AN ANSWER
```
   GRINDING            a real MOTION oscillation, strongest in cs_rate  -> the notch (V195: 21.5x)
   RATCHETING          torque-dominant, omega^2 lane                    -> inertia half-dose (V196)
                                                                           + the K1 revert
   COMMAND OSCILLATION cannot be commanded (1-5 Hz low-pass); it tracks -> fixed BY fixing the grind
                       the grind                                           no separate lever
   LKAS AUTHORITY      the knob is 0xC6CD0 and it is the grind's carrier -> sequenced: confirm the
                                                                           grind fix, THEN 6x -> 8x
```

## ✅ **V196 — THE ONE FREQUENCY-SELECTIVE RATCHET LEVER LEFT, AND IT COSTS NOTHING AT DC**
The biquad is spent on the grind. The only other **frequency-selective** lever aimed at the ratchet
is `gp-0x6b26`: built from the acceleration EMA, so its loop contribution scales as **ω²** —
**67× stronger at 8.2 Hz than at 1 Hz.**
```
   gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )
   L = LERP(0xCBE74[mode], gp-0x6a5e)

   FLYING V122   engaged Y = (-29490, -17202, -16000)   ~3x Honda   ** and it ratchets **
   V189..V195    engaged Y = ( -9830,  -5734,  -1966)   = Honda
   V196          engaged Y = ( -4915,  -2867,   -983)   = HALF Honda
```
✅ **ENGAGED ONLY.** m24 (manual) and m26 (engaged) are **distinct records** (`0xD6A64` vs
`0xD7A54`), so only `0xD7A5C..0xD7A61` moves and **manual driving stays byte-identical** — the V74
pattern the TVCA4 memory endorses.
⚠ **This deliberately RE-CREATES an engaged/manual asymmetry** that earlier work removed. The
difference is **direction**: the ones removed made engaged **worse** (more anti-damping when
engaged); this makes engaged **better**. Recorded explicitly so a later reader does not "fix" it.
✅ **THE TRADE, PLAINLY:** negative apparent inertia makes the wheel feel lighter to fast inputs, so
halving it means the wheel feels closer to its true inertia at high frequency — very fast steering
inputs get marginally less help. **But ZERO at DC** (acceleration is zero in steady state), so **no
LKAS authority is lost and no steady steering weight is added.** A half-dose rather than zero
precisely because the trade is real.
✅ **V196 = V195 + three int16.** `f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e`
⚠ Sign basis: the ★★★★★ anti-damping reading plus the dose ladder. **If inverted, the term was
damping and the ratchet gets worse — revert to V195, three int16.**

⇒ **THE SHELF NOW SEPARATES CLEANLY BY SYMPTOM:**
```
   V195   the GRIND lever, re-fitted on the channel the grind lives in.  No sign bets.
   V196   V195 + the RATCHET lever, omega^2-selective, engaged-only, free at DC.  One sign bet.
   V194   V193 + the gp-0x6c2c probe, if the detector question is worth a drive.
```

## ✅ **V195's LOW SHOULDER IS CLEAR — AND THE WIDER NOTCH IS GENTLER THAN V189's**
A notch adds lag below itself, so a wider pole (0.9000 vs V188/V189's 0.9300) needed its own check;
the V188 result does not transfer. Measured on **`cs_rate`**, pooled engaged-creep windows:
```
   f (Hz)   excess   V189 |H|  V189 lag   V195 |H|  V195 lag
   15.04     1.66      0.486    -29.9      0.449    -27.7
   16.21     2.35      0.372    -34.0      0.349    -30.5
   16.99     2.95      0.288    -36.9      0.278    -32.4
   17.97     3.80      0.176    -40.5      0.184    -34.8
   18.95     7.90      0.057    -44.3      0.085    -37.1
```
✅ **Frequencies with excess>2 AND |H|>0.5 AND lag<−30°: ZERO.** The danger pattern needs all three
at once, and for a notch lag and attenuation grow together — the worst three points (16.2–17.6 Hz)
have |H| already cut to 0.22–0.35 exactly where the lag peaks.
➕ **AND V195's LAG IS SMALLER THAN V189's AT EVERY SHOULDER FREQUENCY** (−37.1° vs −44.3° at
18.95 Hz). The lower-Q notch has a gentler phase transition. ⇒ **V195 dominates V189 on BOTH axes:
1.43× more grind power removed AND less shoulder lag.** That is unusual and worth stating — the
re-fit was not a trade.
⊕ Tool kept: `rlog-tools/score/notch_shoulder_check.py`.

## ✅✅ **V195 — THE NOTCH RE-FITTED ON THE CHANNEL WHERE THE GRIND ACTUALLY LIVES**
V188 centred the notch at 19.40 Hz by minimax over **`cs_tq`, the driver torque sensor**. The
cross-channel work then showed the grind is a **motion** oscillation, strongest in **`cs_rate`**
(excess 7.3× vs 5.1× in torque). **The fit had been done on the weaker instrument.** Re-fitting on
`cs_rate`, same minimax criterion, same GATE 2 constraints, 67 routes:
```
   per-route GRIND peak 15-25 Hz    cs_rate  p10 16.33  med 20.12  p90 22.15 Hz
                                    cs_tq    p10 15.74  med 19.92  p90 21.68 Hz

   design                       median remaining   p90 remaining   phase @3 Hz
   V188/V189  19.40 Hz r 0.9300   0.0666  15.0x    0.0962  10.4x     -3.8 deg
   V195       19.75 Hz r 0.9000   0.0466  21.5x    0.0698  14.3x     -4.6 deg
```
✅ **1.43× more grind power removed at the median, 1.38× at p90, for 0.8° more phase.**
⊕ The substantive change is **the pole radius, not the centre**: 0.9300 → 0.9000 makes the notch
**wider**, because the rate-channel peak distribution is wider than the torque-channel one. The
0.35 Hz centre shift is minor by comparison.
✅ **V195 = V189 + four float32 cells. 11 payload bytes, 30/30 assertions.**
`a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b`
```
   DC gain 1.000003   max|H| 1.7177   added lag vs V189: -0.27 deg @1 Hz, -0.77 deg @3 Hz
   notch at 19.76 Hz  |H| 0.00094     15 Hz 0.42 - 21 Hz 0.12 - 22.2 Hz 0.23 - 25 Hz 0.48
```
⊕ Still engagement-gated, so manual driving stays bit-for-bit stock — **including Honda's 55.226 Hz
null, which is given up only while LKAS is engaged.**

⇒ **V195 REPLACES V189 as the recommendation.** Same lever set, same risk profile, a better-aimed
notch — and the improvement came from measuring the symptom in the right channel rather than from any
new firmware insight.

## 🛑 **THREE CLAIMS TESTED, TWO DIED TO THEIR OWN CONTROLS — and one of them was mine from last tick**

### ❌ 1. THE COULOMB SIGN-FLIP HYPOTHESIS IS REFUTED
Coulomb friction opposes motion, so it must flip sign at rate zero-crossings. Testing that with a
**matched** control (samples DWELLING at similarly low |rate| without changing sign):
```
   RATCHET  5-12 Hz   cross/dwell  3.73  [2.97, 4.35]
   GRIND   15-25 Hz   cross/dwell  4.96  [3.84, 5.92]   <- the CONTROL is HIGHER
```
⇒ crossings excite **everything** broadly; there is no Coulomb-specific preference.
**The friction explanation for the ratchet is NOT supported.** (The K1 revert is still defensible —
it returns a 10× dose to Honda — but not on this rationale.)

### ❌ 2. AND THE RATE-SCALING TEST WAS CONFOUNDED
The ratchet/control ratio rises 63.7 → 211 peaking at 20–40 °/s — **but the GRIND control does the
same** (9.6 → 24.9), and the ratchet/grind ratio stays flat at 6.2–8.5 throughout. The common
rise-and-fall is the **normalisation**, not a rate signature. Inconclusive, not supportive.

### 🛑 3. **I OVER-CLAIMED LAST TICK: "THE RATCHET IS NOT IN THE MOTION" IS TOO STRONG**
The first coherence attempt returned **1.000 for everything including the shuffled surrogate** —
degenerate, because one sub-window per segment makes coherence trivially 1. **The shuffled floor
caught it.** Redone with 2048-sample episodes and 256-sample sub-windows:
```
   coherence cs_tq x cs_rate    @ 8 Hz  0.888      @ 20 Hz  0.842
   SHUFFLED floor                       0.049               0.053
```
⇒ **torque and motion are STRONGLY COUPLED at 8 Hz.** The ratchet's motion is **small, not absent** —
the rack is stiff at 8 Hz, so a large torque ripple produces little movement. That is consistent with
the recorded *"lightly-damped resonance, Q 14–29, motor/rack-side"*, and it is **not** a
torque-sensor-only artifact.
⇒ **CONSEQUENCE: `gp-0x6c2c` DOES contain 8 Hz, so the detector's amplitude gate is NOT provably
uncrossable.** V193's premise is **not** dead, and **V194's probe is still the honest decider**, not a
formality. The "peaks below 12800" branch is a real possibility again, not the expected outcome.
⊕ What survives from last tick unchanged: **the GRIND is a genuine motion oscillation, strongest in
RATE (7.3×)** — so the notch remains well aimed.
⊕ An independent rate (`d(cs_ang)/dt` computed here) gives ratchet 1.5× / grind 2.6× — it corroborates
the small ratchet but **degrades the grind too**, because differentiating a quantised angle amplifies
HF noise. `cs_rate` is the better motion instrument.

➕ **THE PROCESS POINT: three claims, and the CONTROL killed or corrected two of them before any of it
reached a build.** A refuted hypothesis with a control that fired is worth more than a confirmed one
without. 🛑 *Run the control BEFORE the measurement* — the shuffled floor at 1.000 is exactly what a
broken estimator looks like when nobody checks.

### ✅ WHERE THIS LEAVES THE RECOMMENDATION
**V189 still stands** — the notch is aimed at a confirmed motion oscillation, and the reverts return
10× and 3× doses to Honda on their own merits. But **the detector route (V191–V194) is back to
UNDECIDED rather than ruled out**, and V194 is the build that settles it.

## 🛑🛑⭐ **THE RATCHET IS NOT IN THE MOTION — IT IS A TORQUE-PATH EFFECT, AND THAT RE-AIMS EVERYTHING**
Every prediction this session rested on **`cs_tq`, the driver torque sensor**. Running the same
slope-corrected excess across **all** channels, 1080 pooled engaged-creep windows, null ~3.9×:
```
   channel                       RATCHET 5-12          GRIND 15-25
   cs_tq   driver torque         13.5x @  8.01 Hz       5.1x @ 20.12 Hz
   cs_rate steering RATE          1.7x @  8.01 Hz  ***  7.3x @ 20.31 Hz
   sc_tq   LKAS command           1.2x                  3.3x
   probe   cave channel           2.2x                  1.9x
   cs_press hands-on              1.2x                  1.8x
```
✅ **THE GRIND IS A GENUINE MOTION OSCILLATION** — **strongest in RATE (7.3×)**, present in torque and
command. That confirms the closed-loop model and means **the notch is well aimed.**
🛑 **THE RATCHET IS NOT IN THE MOTION AT ALL** — 13.5× in torque, **1.7× in rate, BELOW the null.**
The wheel is not oscillating at 8 Hz; the **torque** is. That is a **friction / stiction** signature,
and it matches the operator's word for it: he feels it, he does not see the wheel move.

### 🛑 CONSEQUENCE 1 — THE DETECTOR ROUTE CANNOT REACH THE RATCHET, FOR A SECOND REASON
`FUN_000428d4` watches **`gp-0x6c2c`, an ACCELERATION EMA**. No 8 Hz in the rate ⇒ none in its
derivative ⇒ **the amplitude gate `|gp-0x6c2c| > 12800` will not be crossed either.** So V191, V192
**and V193** are inert for the ratchet on **both** counts — frequency (established last tick) **and now
amplitude.** V194's probe will confirm it; the pre-registered "peaks below 12800" branch is now the
*expected* outcome, not merely a possibility.

### ✅ CONSEQUENCE 2 — THE RATCHET'S PRIME SUSPECT IS THE FLYING BUILD'S 10× COULOMB FRICTION
```
   friction = clamp(motor_rate * 12 / cal[0xC40BC], +-1) * (|model| * K1/1024 + K0/1024)

   cal        STOCK  V88  V89  V108  V122(FLYING)  V177..V194
   0xC40D2 K1   102  102  204   204     ** 1020 **     102      <- TEN TIMES Honda
   0xC40BC knee 600  600  600   600        3000        3000
```
⇒ **the car is running 10× Honda's modelled Coulomb friction**, and Coulomb friction is exactly what
makes torque ripple without motion. **V177's K1 revert — already carried on V189 through V194 — is
aimed straight at the lane the measurement points to.**
⚠ The ramp knee is **3000 vs Honda's 600** and has never been reverted (it was 600 as late as V108).
A 5× knee makes the ramp shallower, i.e. *less* friction below saturation — aligned with the
operator's "low apparent friction" requirement, so it is left alone, **but it is non-stock and
unattributed to any stated intent.**

### ⭐ **THIS RE-ORDERS THE RECOMMENDATION — V189 IS NOW THE BEST BUILD**
```
   V189   the grind NOTCH (aimed at a confirmed MOTION oscillation)
          + the inertia revert and the K1 revert (aimed at the TORQUE path, where the ratchet is)
          no sign bets - nothing that can change normal driving - both symptoms addressed
   V190   adds a sign-bet lever on the MOTION path, where the ratchet is NOT
   V191-3 add detector levers now shown unreachable on BOTH frequency and amplitude,
          and V193 can change normal driving for no expected benefit
   V194   = V193 + the probe that confirms the above
```
⇒ **RECOMMEND V189.** Everything after it is aimed at the motion path; the measurement says the
ratchet is not there. **V194 remains worth flying only if the operator wants the `gp-0x6c2c`
measurement itself** — which is now a confirmation, not a fork.

## ✅✅ **THE V194 DELTA IS NOW 100 % ATTRIBUTED — and V57 turns out to be the authority build**
Every payload byte of V194 vs stock is explained. The two stragglers were the **part-number marker**
(`39990-TVA-A160` → `39990-TVA,A160`, two copies) — a UDS-visible flag that the ECU is modified.

**What was NOT in the record: V57 is a large LKAS-AUTHORITY build.** Beyond the `0xC646C`
decoupling it is credited with, it also carries:
```
   0xC62EA          320 -> 0        ** the LOW-SPEED STEER LOCKOUT, DISABLED **
   0xC659A..0xC65CE float32 +-1.0 -> +-5.0   a family of saturation limits raised FIVE-FOLD
   0xC674E..0xC676C int     +-1024 -> +-5120  the same family, integer form
   0xC61C0/C2/C4    1600 / 896 / 1280 -> -1   saturated, i.e. removed as constraints
   0xC64B4/B6/B8    24688 / 16438 / 112 -> -1 / 255   saturated
```
⇒ **substantial authority work is ALREADY ON THE CAR and has been since V57**, and the lineage
describes that build only as *"the `0xC646C` decoupling"*. Worth knowing before adding more.

### ✅ THE HEADLINE FOR THE OPERATOR
```
   V122 (what he drives) vs stock   310 payload bytes
   V194                  vs stock   319 payload bytes
   ** V194 changes NINE cells relative to the car as it is today **
     4  the grind notch          0xC60A8 / AC / B0 / B4        V188
     3  detector-conditional     0xC64AE - 0xC691A - 0xC64DD   V190/V192/V193
     2  pure instrument          0x55DF2 - 0x55E10             V194
```
Everything else on V194 is already flying. **The proposal is nine bytes of change, of which two are
telemetry and three do nothing unless Honda's own oscillation detector fires.**
✅ Tool: `analysis-2020accord/verify/cumulative_delta_vs_stock.py` — now attributes 100 % and still
refuses to stay silent about anything new.

## 🛑✅ **THE CUMULATIVE DELTA — AND IT FOUND 72 DEAD BYTES ON THE BUILD HE IS DRIVING**
The close-out contract requires enumerating **every** cell that differs from stock, read from the
**built image**. Doing it for V194 turned up a block nothing in the record explains:
```
   0xE4194..0xE41A4 - 0xE41BC..0xE41CC - 0xE420C..0xE421C - 0xE4234..0xE4244
   0xE5194..0xE51A4 - 0xE51BC..0xE51CC - 0xE51E4..0xE51F4 - 0xE520C..0xE521C
   8 runs x 9 entries = 72 halfwords, EVERY ONE 15360 -> 16384  (+6.67 %)
   context:  X = [3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320]   Y = [15360 x8] -> [16384 x8]
   present on V108, V122, V158, V189, V194  => introduced at V108
```
🛑 **AND THEY ARE DEAD.** `0xC61BE` — the clamp on that path — is **byte-stock at 15360 on V194**,
so every raised entry is cut straight back. The lineage records why: V108 built the
`0xC61BE` → 16384 raise **and then PULLED it** on a pre-registered null.
⇒ **V108 raised the TABLES and pulled the CLAMP. 72 bytes of half-applied edit have been carried on
every build since — including the one on the car right now — doing nothing.**
⊕ That is exactly the category the contract calls *"carried by accident"*, and it had never been
found because nobody had run a full cumulative diff against stock.

### ✅ THE 9 CELLS V194 CHANGES RELATIVE TO WHAT HE DRIVES TODAY
```
   0xC60A8/AC/B0/B4   the GRIND NOTCH, 55.226 Hz -> 19.40 Hz              V188
   0xC64AE            2nd omega^2 accel term disabled                      V190
   0xC691A            oscillating slew curve tightened by Honda's 0.60     V192
   0xC64DD            detector dwell 50 -> 100 (the ratchet becomes visible) V193
   0x55DF2 / 0x55E10  the 427 probe -> gp-0x6c2c at sar 6                 V194
```
Everything else on V194 is already on the flying build. **V122 vs stock = 310 payload bytes;
V194 vs stock = 319.** So the whole proposal is **9 bytes of change from what he drives**, of which
**4 are the notch, 3 are detector-conditional, and 2 are pure instrument.**

✅ Tool kept: **`analysis-2020accord/verify/cumulative_delta_vs_stock.py`** — prints the full
attributed delta and **refuses to stay silent about anything it cannot attribute**, which is how the
72 bytes surfaced.

## ✅ **V190's XREF CHAIN BYTE-CONFIRMS — the BELIEF caveat is LIFTED**
Last section flagged that V190's xref counts came from `search_instructions` and were not
byte-confirmed. Re-derived from raw bytes, both gp-relative encodings, whole image:
```
   cell                          ghidra   raw-real   verdict
   gp-0x6bc2   V190 chain           2         2      COMPLETE
   gp-0x6ad6   V190 chain           3         3      COMPLETE  (2 raw hits adjudicated away)
   gp-0x6c2e   the 2nd accel EMA    5         5      COMPLETE
   gp-0x6b26   CONTROL              5         5      the scanner is CALIBRATED
   gp-0x6b2e   the caught case      2         3      ghidra undercounted by 1 (0x2A896)
```
⇒ **V190's completeness moves from BELIEF to EVIDENCE.** Only `gp-0x6b2e` was genuinely
undercounted, and that one is already recorded.

### 🛑 **MY OWN SCANNER OVER-REPORTS — THE MIRROR IMAGE OF GHIDRA'S UNDERCOUNT**
The two extra `gp-0x6ad6` hits were **false positives I manufactured**:
```
   0xBCC52  disassembles as  `st.b r7, -0x6ad5, gp`     <- -0x6ad5, NOT -0x6ad6
```
My scan accepted **both** `(hw2 & 0xFFFE)` and `(hw2 & 0xFFFE) | 1` for every opcode, so it matched
the NEIGHBOURING cell. And the surrounding stream is six consecutive `st.b r7` to scattered
unrelated displacements (`0x446c`, `0x6cdb`, `-0x42a4`, `-0x1a90`, `0xd65`) — **that is DATA being
force-disassembled, not code.**
➕ **THE RULE, and it cuts both ways:** *Ghidra UNDERCOUNTS (it only sees analysed code and still
reports `truncated:false`); a naive byte scan OVERCOUNTS (it cannot tell code from data, and a
loose displacement rule matches neighbours).* **Neither is authoritative alone. Adjudicate every
disagreement by disassembling the disputed address and checking it sits in a sensible instruction
stream** — which is exactly how `0x2A896` was confirmed real and `0xBCC52` was rejected.
✅ **Scanner refinement owed:** derive the odd/even displacement bit from the OPCODE FIELD
(`0x3D` ⇒ odd, `0x3C` ⇒ even, as established for `ld.bu`) instead of accepting both. Accepting
both is what produced the neighbour match.

⊕ **Ghidra reports `analyzed: true` with 2086 functions, yet `0x2A896` has no function.**
"Analysed" does not mean complete coverage on this image — so the `CLAUDE.md` instruction to analyse
the whole `.bin` first is **already satisfied as far as the tool is concerned**, and the residual
gaps are not fixable by re-running analysis. **The byte scan plus adjudication is the only complete
method.**

## 🛑 **LKAS AUTHORITY: `0xC61BE` IS MISLABELLED, AND THE REAL KNOB IS COUPLED TO THE GRIND**
`0xC61BE` is described in the lineage as *"the LKAS request clip"*. **It is not.** Decompiled:
```c
   FUN_0002a93a  (driver torque gp-0x682f -> a pointer-table assist map)
       uVar11 = clamp(uVar11, +-cal(0xC61BE));      // 15360
       gp-0x6b2e = uVar11;                          // the BASE-ASSIST output
   ... consumed at 0x2A896:  r9 = (gp-0x6b2e * cal(0xC63EE)) >> 10
```
⇒ **it clamps the BASE-ASSIST path (driver torque → assist), not the LKAS request.** Raising it adds
**manual** assist, not LKAS authority. **The label is wrong and the lever is aimed at the wrong lane.**

### 🛑🛑 **AND I NEARLY RECORDED A FALSE NULL — THE TWO-METHOD RULE CAUGHT IT**
`search_instructions` returned **2 hits for `gp-0x6b2e`, both stores**, which reads as *"a dead cell,
so `0xC61BE` is provably inert"*. That is a clean, quotable, **wrong** conclusion. The raw byte scan
found a **third** site:
```
   0x2A896   hw1 = 0x4F24  ->  opcode bits5-10 = 0x39 = ld.h, reg r9
             = `ld.h -0x6b2e, gp, r9`   ** A READER **
```
It sits in a region Ghidra has **not analysed**, which is exactly the recorded failure mode:
*"`search_instructions` silently undercounts — it scans only already-analysed instructions and still
reports `truncated:false`."*
⚠ **CONSEQUENCE FOR THIS SESSION'S OTHER SEARCHES.** The xref counts behind **V190** — `gp-0x6bc2`
(1 writer / 1 reader) and `gp-0x6ad6` (1 writer / 2 readers) — came from the same tool and were
**not** byte-confirmed. They may undercount. The chains I built on them are still the best available
reading, but **their completeness is BELIEF, not EVIDENCE.** (By contrast `gp-0x671a`, the setf
family and the dormant-cal sweep were all byte-scanned and stand.)
➕ **`CLAUDE.md` already says to analyse the whole image in Ghidra first. The image is NOT fully
analysed, and that is a live hazard for every operand search in this session.**

### ✅ **THE HONEST ANSWER ON AUTHORITY — IT IS SEQUENCED, NOT BLOCKED**
```
   the real LKAS authority knob is 0xC6CD0, the LKAS gain:  reach = (clip * cal(0xC6CD0)) >> 15
     V57..V88   3564  = 4x     <- the value at which grinding was CONFIRMED FIXED on-car (V88)
     V101       7128  = 8x     <- and the grind came back
     V102..now  5346  = 6x     <- where it sits today
   the SAME cell is what the de-confounded 2x2 named as the CARRIER of the ~23 Hz vibration
   (effect 2.7-3.9x).  Authority and grind are the SAME LEVER pushed in opposite directions.
```
⇒ **that coupling is exactly what the notch breaks.** V188's notch removes the gain's 19.4 Hz
consequence **without touching the gain**, so:
```
   step 1  fly the notch, confirm the grind is gone            <- V194 does this
   step 2  THEN 0xC6CD0 6x -> 8x becomes available, restoring the authority V102 gave up,
           with the notch now suppressing the vibration that made 8x untenable
```
🛑 **Do NOT raise the gain before the grind result is in** — that is the V101 mistake, and it is
the one build in the arc that demonstrably brought the grind back.

## ✅ **V194 — MEASURE THE ONE NUMBER THAT DECIDES WHETHER V191/V192/V193 CAN WORK AT ALL**
V193 opened the detector's **frequency** window. There is a **second** gate, and it has never been
measured: the counter increments only when **`|gp-0x6c2c|` exceeds T = `cal(0xC620A)` = 12800.**
⇒ if the ratchet's acceleration never reaches T, then **V191, V192 AND V193 are all inert** and the
next lever is **T**, for an amplitude reason rather than the frequency one. That fork is worth one
CAN channel.
✅ **V194 repoints the 427 probe from `gp-0x6ac0` (V183) onto `gp-0x6c2c`, the detector's own input.**
```
   0x55DF2  hw2 of `ld.h disp, gp, r6`   0x9540 (-0x6AC0)  ->  0x93D4 (-0x6C2C)
   0x55E10  the pack shift               sar 4 (0xA4)      ->  sar 6 (0xA6)
```
🛑 **THE SHIFT IS NOT COSMETIC — `gp-0x6ac0` WAS UNSIGNED, `gp-0x6c2c` IS SIGNED.** The packer does
`andi 0xffff` (zero-extend) then `sar N` then masks to 10 bits, so for a signed source the shift must
be chosen to make the field carry the sign:
```
   sar 6:   positive x -> raw    0 .. 511        negative x -> raw 512 .. 1023
   decode:  x = (raw < 512 ? raw : raw - 1024) * 64
   resolution 64 counts   range +-32704   ** T = 12800 lands at raw 200 **
```
A smaller shift wraps negatives into the positive range and makes the channel unreadable. **That is
the trap this build exists to avoid, and it is why the shift moves WITH the source.** Verified by a
round-trip assertion over ±1000 / ±12800 / ±32704 in the builder.
✅ **40/40 assertions.** `2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10`
⊕ Decoder shipped: **`rlog-tools/probe/decode_v194_detector_input.py <route-tag>`**, which prints the
percentiles and the verdict directly.
⊕ Every V193 lever is carried — **this build adds an instrument, it does not remove a fix.**

### ⇒ WHAT ONE SHORT DRIVE NOW SETTLES
```
   |x| peaks well past 12800   => amplitude is fine; the detector route is LIVE and V193's window
                                  fix is the operative change
   peaks below 12800           => T IS THE BLOCKER. V191/V192/V193 are ALL inert, and the next
                                  build lowers T (0xC620A) instead
   peaks near 12800            => marginal; T needs a modest reduction
```
➕ This is the design law working as intended: **the probe was sized against its OWN lane's
reachable output** (±32704 at 64-count resolution, threshold mid-scale at raw 200), not against a
downstream clamp — and it pairs a magnitude channel with a sign, which is the pattern every probe
that ever DECIDED something has used.

## 🛑🛑⭐ **HONDA'S OSCILLATION DETECTOR HAS A FREQUENCY WINDOW, AND THE RATCHET FALLS OUTSIDE IT**
`FUN_000428d4` is a reversal counter on **`gp-0x6c2c` (the acceleration EMA)**:
```c
   T    = cal(0xC620A) = 12800        amplitude threshold
   HYST = cal(0xC64DD) = 50           DWELL LIMIT, in task ticks
   state +latched:  if (dwell >= HYST) -> neutral          // TIMES OUT
                    else if (x < -T)   -> -latched, count++
                    else dwell++
```
A reversal only COUNTS if the opposite peak arrives **within HYST ticks**. `FUN_000428d4`,
`FUN_00041464` and `FUN_000352b4` **all share the single caller `FUN_0002214a`** ⇒ same task, the
**1 kHz** control task (corroborated: the biquad response was verified at fs = 1000 Hz against three
stock points). So HYST = 50 ticks = **50 ms**:
```
   countable  <=>  half-period < 50 ms  <=>  f > 10.0 Hz
     ratchet  7.34 - 8.59 Hz    half-period 58 - 68 ms   ** OUTSIDE the window **
     grind   15   - 25   Hz     half-period 20 - 33 ms      inside
```
🛑 **THE DETECTOR CANNOT COUNT AN 8 Hz OSCILLATION.** The dwell expires before the opposite peak
arrives, so `gp-0x671a` never leaves 0 for the ratchet ⇒ **V191 and V192, which both act only on the
counter≥5 branch, are INERT FOR THE RATCHET.** They may still act on the **grind**, which is inside
the window, if its amplitude reaches T. **This is the "nothing changes" outcome, now predictable
BEFORE the drive rather than after it.**

➕ **AND IT CORRECTS A RECORDED ASSUMPTION.** The lineage treats **T** as the detector knob
(*"lowering T changes five things at once"*). **T is the WRONG knob for the ratchet: no amount of
lowering an AMPLITUDE threshold makes an 8 Hz oscillation countable when the DWELL is what expires.**
**HYST is the binding constraint**, and it has never been touched.

### ✅ **V193 — OPEN THE WINDOW SO THE RATCHET IS VISIBLE**
```
   0xC64DD  50 -> 100      dwell 50 ms -> 100 ms
     HYST  50  =>  f > 10.0 Hz    ratchet EXCLUDED
     HYST 100  =>  f >  5.0 Hz    the whole 5-12 Hz band INSIDE, with margin
```
With the ratchet finally visible to the detector, **V191's and V192's damping responses — which are
gated on exactly that counter — can act on it.** One byte, 31/31 assertions.
`0f1a7bb6849f17824cbc9fa7e8a6aeeb40e8fe4bb548fc7310fa4e17052b7992`

⚠ **THE RISK IS DIFFERENT IN KIND FROM V191/V192 — SAY IT PLAINLY.** V191 and V192 are conditional
on a state that never occurs during the ratchet, so they **cannot** affect normal driving. **V193
makes that state REACHABLE**, so for the first time in this chain the detector-conditional damping
can engage while driving. A spurious detection tightens the slew limit for a hold period and could
read as brief heaviness. The counter still needs **|gp-0x6c2c| > 12800 on BOTH sides** — a large
acceleration excursion — so it is bounded, not free-running. But it is a real change to normal
driving, unlike everything else in the V189–V192 chain.

⇒ **TWO OPTIONS, and the choice is the operator's:**
```
   V192  the conservative build: five levers, ALL provably inert in normal driving.
         But per the finding above, its detector-gated pair cannot reach the ratchet.
   V193  V192 + one byte that makes the detector see the ratchet, unlocking that pair.
         The only build in the chain that can change how the car feels when nothing is wrong.
```

## ✅✅✅ **V192 — HONDA'S OSCILLATION RESPONSE DOES NOTHING AT LOW INDEX. V192 CLOSES THAT GAP.**
`FUN_00035b20` switches the slew limit `gp-0x69a0` between two curves on the reversal counter:
```
   NORMAL      (counter < 5)   X = [ 320, 1600, 3200,  4480]   Y = [358, 358, 461, 512]
   OSCILLATING (counter >= 5)  X = [ 640, 3200, 6400, 12800]   Y = [358, 307, 307, 307]
                                                                    ^^^ IDENTICAL
```
🛑 **At the LOW index the two curves are the SAME (358)** — so Honda's oscillation response gives
**no tightening at all** there — and the oscillating breakpoints are **stretched 2×**, pushing what
tightening exists even further out.
✅ **V192 applies Honda's OWN ratio once more.** Honda chose `512 → 307` = **0.600** as its response
to detected oscillation; V192 scales the whole oscillating curve by that same 0.600:
```
   Y = [358, 307, 307, 307]  ->  [215, 184, 184, 184]
```
so the limit is tightened across the entire index range, **including the low end where the detector
currently does nothing.**

### ⭐ **WHY THIS IS THE SAFEST LEVER IN THE SESSION**
```
   PROVABLY INERT IN NORMAL DRIVING   the curve is read ONLY on the counter>=5 branch; below
                                      saturation the NORMAL curve is used and is byte-untouched.
   THE DIRECTION IS HONDA'S, NOT MINE Honda tightens the slew limit on detection; V192 tightens it
                                      MORE.  ** This is not a polarity gamble like V190/V191 -- the
                                      sign is established by Honda's own two curves. **
   MECHANISM IS EXPLICIT              gp-0x69a0 rate-limits the boost-table walk in FUN_000352b4
                                      (delta = ((step * limit * 4) >> 12)), so lowering it slows how
                                      fast the assist may change DURING an oscillation.  That is
                                      what damping an oscillation means.
```
✅ **V192 = V191 + four halfwords at `0xC691A`.** 32/32 assertions.
`c36b6ca12e27633f6a52a9a0d8c32feab71e08606fb253d4ef96cf3a17d5cdc1`
⚠ **Watch for:** a slew limit too tight during an event could read as a brief **HESITATION** rather
than a ratchet. That is a *different* symptom, not a worse one, and it is pre-registered.

## 🛑 **CORRECTION TO V191's RATIONALE — THE "4.2× BOOST" DOES NOT HOLD AT CREEP**
I justified V191 by saying the oscillation fallback `0xC640A` = −8192 is **4.2× stronger** than the
LERP it replaces. **That compares against the LERP's HIGH-INDEX end, which is not the creep operating
point.**
```
   inertia LERP (mode 26)   X = [0, 1280, 5760]   Y = [-9830, -5734, -1966]   index gp-0x6a5e
   fallback when oscillating                        -8192
     index 0      LERP -9830  ->  fallback is 17% WEAKER
     index 1280   LERP -5734  ->  fallback is 43% stronger
     index 5760+  LERP -1966  ->  fallback is 4.2x stronger   <- the figure I quoted
```
✅ **But `gp-0x6a5e` is the SAME index FactorC uses, and the recorded evidence is that it sits below
FactorC's first breakpoint 2240 across 100% of the micro regime.** ⇒ **at creep the LERP returns its
STRONG end and −8192 sits INSIDE the range — it is not reliably a boost at all.**
⇒ **V191 is still a valid lever, but its honest description is *"when the detector saturates, remove
the anti-damping term"*, NOT *"undo a 4.2× boost."*** The builder assertion and the card now say so.

## ✅ **THE DETECTOR MAP IS COMPLETE — AND HONDA USES IT TO DAMP**
All three `gp-0x671a` consumers are now read:
```
   FUN_00036c12   counter >= 5  ->  L = cal(0xC640A) = -8192 instead of the LERP
                  the ONE place the assist gain itself changes.  V191 zeroes it.
   FUN_0003a382   two counter-indexed LERPs, X = [5,10,15] and [5,8,10], Y FLAT at 1024 / 5120.
                  ** The counter is CLAMPED AT 5 and the first breakpoint IS 5, so `5 < counter`
                  is never true => both return Y[0] permanently. INERT over the reachable range. **
                  (the recorded worry that T is "a shape parameter on a load-bearing lane" is only
                  true if T or CEIL are moved -- at stock CEIL=5 these tables are constants)
   FUN_00035b20   SWITCHES CURVES on the counter, for the slew limit gp-0x69a0:
                     normal  X = [320, 1600, 3200, 4480]   Y = [358, 358, 461, 512]
                     osc     X = [640, 3200, 6400, 12800]  Y = [358, 307, 307, 307]
                  ** the oscillating curve is SMALLER (307 vs up to 512) with breakpoints stretched
                  2x => Honda TIGHTENS the slew limit when it detects oscillation. It DAMPS. **
```
➕ **So Honda's detector is a damping mechanism**, and V191 is *consistent with that design intent*
rather than opposed to it — it takes the same "when oscillating, back off" idea further.

### ⭐ **THE NEXT LEVER, AND IT HAS V191's IDEAL SHAPE**
`0xC691A..0xC6920` is the **oscillating** slew curve, `Y = [358, 307, 307, 307]`. Lowering it tightens
the slew limit **further** during a detected oscillation — **and it is read ONLY on the counter≥5
branch, so it is provably inert in normal driving**, exactly like V191. It also pushes in the
direction Honda already chose, which makes it far safer than a sign bet.

## ✅✅✅ **V191 — THE FIRMWARE BOOSTS ITS ANTI-DAMPING *AFTER* ITS OWN DETECTOR SEES OSCILLATION**
`gp-0x671a` is Honda's **HARD-REVERSAL COUNTER** — a built-in oscillation detector, clamped at
CEIL = 5 (`0xC64FA`). `FUN_00036c12` branches on it:
```c
   if (gp-0x671a < 0xFF && gp-0x67f4 == 1) {
       if (gp-0x671a < cal(0xC64FD)=5)   L = LERP(0xCBE74[mode], gp-0x6a5e);   // normal
       else                              L = cal(0xC640A) = -8192;             // OSCILLATING
   } else                                L = cal(0xC640C) = -3277;
   gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )
```
```
   LERP Y (Honda, mode 26) = [-9830, -5734, -1966]     on X = [0, 1280, 5760]
   fallback when OSCILLATING = -8192   ** 4.2x STRONGER than the LERP's weak end **
```
⇒ **once sustained oscillation is DETECTED, the anti-damping acceleration gain can jump 4.2×
STRONGER.** That is positive feedback on the thing the detector just found, and it is a plausible
reason the ratchet **sustains instead of decaying** — which is exactly the character the ring-down
work established (ζ 0.017–0.036, Q 14–29).

### ✅ WHY THIS LEVER IS BETTER-SHAPED THAN ANYTHING ELSE IN THE ARC
```
   PROVABLY INERT OUTSIDE THE SYMPTOM   0xC640A is read ONLY on the counter>=5 branch, so below
                                        saturation the cell is never loaded.  No steering-feel and
                                        no LKAS-authority change on a calm road -- BY CONSTRUCTION,
                                        not by measurement.
   ACTS EXACTLY DURING THE SYMPTOM      the one moment we want the term gone.
   ONE HALFWORD, cal-only, no cave.     never touched in the whole post-V38 arc.
```
✅ **V191 = V190 + `0xC640A` −8192 → 0.** 30/30 assertions.
`82ce1db4e73099377c61a78c1b5033b5ca3ba3368062761e8836c709b0c29f4b`
⊕ It also **does not depend on `gp-0x6a5e`'s value during the ratchet** — zeroing removes the term
outright, so the edit is unambiguous whether or not −8192 was a "boost" at the live operating point.

### ✅ AND IT SETTLED A REAL WORRY ABOUT V189
The same branch decides whether the **inertia LERP is used at all.** Had `gp-0x671a` normally sat at
or above 5, the LERP would be bypassed and **V184/V189's inertia revert would have been INERT** — the
same failure class as mode 27. ✅ **It is not: the counter is a reversal count clamped at 5, so
normal driving sits BELOW the threshold and the LERP path IS live.** The revert is real.

⚠ **Sign basis is shared with V190** — `gp-0x6b26` anti-damping per the ★★★★★ result plus the
3×-dose / 3.58×-ratchet observation. **If inverted, this term was DAMPING and zeroing it during an
oscillation makes the ratchet worse.** Same pre-registered revert.

## ✅ **V190 UN-RETRACTED — THE DECIDING TEST IS THE SIGN *RELATIVE TO* `gp-0x6b26`, AND IT MATCHES**
The retraction one section below was **wrong, and here is the specific error**: I judged
`gp-0x6bc2` in isolation, asking *"does opposing acceleration mean damping?"* — a question that
rests on the aggregator→plant sign, **which is exactly the link I had already flagged as unproven.**
The answerable question is the **RELATIVE** one.
```
   the gp-0x6bc2 path, both inversions now PROVEN:
     d(gp-0x6ad4)/d(gp-0x6ad6) = (-K) * (-1) = +K      the two inversions CANCEL
     gp-0x6ad6 ~ -a                              =>    gp-0x6ad4 ~ -a
   the inertia term, added DIRECTLY with no inversions:
     gp-0x6b26 = -K*alpha                        =>    gp-0x6b26 ~ -a
```
⇒ **BOTH terms enter the aggregator with the SAME SIGN, so they are the same class.** Whatever
`gp-0x6b26` is, `gp-0x6bc2` is.
✅ The kit's ★★★★★ finding [[accord-gp6b26-is-inertia-not-damping]] says `gp-0x6b26` is an
**inertia term giving NEGATIVE apparent inertia — anti-damping**. **Empirical support:** the flying
build carries **3×** Honda's dose of it (`m26 Y = −29490/−17202/−16000` vs `−9830/−5734/−1966`) **and
ratchets 3.58× more when engaged.** If these terms were damping, tripling one should have *reduced*
the ratchet.
⇒ **`gp-0x6bc2` is anti-damping too, and disabling it (V190) is directionally correct.**

🛑 **What was actually learned, and it is not nothing:** `FUN_0003a382` was decompiled and
**`error = measured − reference` is now PROVEN**, as is `gp-0x6ad4 = −K·error`. Those two links were
BELIEF before this tick. The mistake was framing an absolute question the data cannot answer
(*"is this damping?"*) instead of the relative one it can (*"is this the same sign as the term we
already characterised?"*).
➕ **GENERAL RULE: when an absolute sign depends on an unproven link, do not guess it — ask whether
the new term matches a term already characterised through the SAME unproven link. The unknown link
cancels.**

✅ **V190 restored as the recommendation.** Its sign now rests on **consistency with the ★★★★★
`gp-0x6b26` result plus the 3×-dose/3.58×-ratchet observation**, not on an independent proof — so
the pre-registered "ratchet gets worse ⇒ revert to V189" outcome **stays on the card.**

## 🛑❌ **V190 IS RETRACTED AS A RECOMMENDATION — I VERIFIED THE SIGN AND IT WENT THE OTHER WAY**
V190 disabled the `gp-0x6bc2` acceleration term on the BELIEF that it was destabilising. I said the
sign rested on a five-link chain and pre-registered the failure mode. **Decompiling the consumer
settled it, and the belief was wrong.**

**`FUN_0003a382`, the only reader of `gp-0x6ad6`:**
```c
   uVar24 = clamp(gp-0x6ad6, +-cal(0xC6200))
   iVar30 = gp-0x4f60 - uVar24              // error = MEASURED - REFERENCE   <- record CONFIRMED
   ... PID(error) ...
   iVar30 = (PID * gain >> 10) * gp-0x6752  // gp-0x6752 = -1
   gp-0x6ad4 = clamp(iVar30, ...)           // => gp-0x6ad4 is proportional to -error
```
and `gp-0x6ad4` is an additive term in the `FUN_0003aa2c` aggregator (already decompiled).

**The chain, now with five links PROVEN instead of assumed:**
```
   gp-0x6bc2  ~ -a                (gp-0x6752 = -1)                          PROVEN
   gp-0x6ad6 += gp-0x6bc2  ~ -a                                             PROVEN
   error = measured - gp-0x6ad6   ~ +k*a                                    PROVEN
   gp-0x6ad4 = -K*error           ~ -k*a                                    PROVEN
   aggregator += gp-0x6ad4        => the sum OPPOSES acceleration           PROVEN
   (unproven: whether a more-negative gp-0x6b94 is less assist in the driver's direction)
```
⇒ **opposing acceleration is POSITIVE damping — stabilising.** So disabling the term would most
likely make the ratchet **WORSE**, which is exactly the inverted-sign outcome the card pre-registered.
⊕ **Independent support:** Honda ships this flag **enabled**. A manufacturer adds acceleration
feedback for damping; it would not enable a destabilising one. The decompile and the shipped
configuration agree.

✅ **ACTION: V189 is restored as the recommendation. `docs/scoring/DRIVE-CARD-V190.md` is marked
NOT RECOMMENDED** (the artifact is kept — it stays a legitimate probe if V189 leaves ratchet behind
and we want to test this term deliberately, knowing it may worsen it).

🛑 **THE PROCESS POINT, worth more than the build:** the lever was built, recorded, and its sign
labelled **BELIEF** with the failure mode pre-registered — and then the verification killed it
**before it cost a drive.** *"I'm not sure, here's what I'd need to verify"* is the preferred output;
this is what it looks like when the check comes back negative. **Do not ship a lever whose sign
rests on an unverified chain when the chain is decompilable in one tick.**

## ✅✅✅ **V190 — A WHOLE FEEDBACK PATH THE ARC HAS NEVER TOUCHED, AND IT PEAKS AT CREEP**
Tracing the second acceleration EMA found a complete path nobody here has ever looked at:
```
   FUN_00041464   gp-0x6c2e = EMA(rate derivative) >> 9        the 2nd accel channel (cal 0xC40DA)
   FUN_00036f30   L = LERP(0xC68EA/0xC68F2, speed)
                  gp-0x6bc2 = clamp(((L*a)>>6) * sign(gp-0x6752) * gp-0x69be >> 6, +-gp-0x6bc0)
   FUN_00037fe6   gp-0x6ad6 = clamp((SUM + gp-0x6bc2*cal(0xC64AE) + ...) * LERP >> 10, +-25600)
                              ^ gp-0x6ad6 is the TORQUE-TRACKING REFERENCE
```
🛑 **AND THE RECORD'S DESCRIPTION OF THIS SUM WAS WRONG.** It says *"the six-term Path-2 sum in
`FUN_00038148`, weights `0xC63A0..0xC63AA`, only w[3] is frequency-selective."* Actually:
**`FUN_00037fe6` · SEVEN terms · flags at `0xC64AD..0xC64B3`** — and they are **ENABLE FLAGS (0/1),
not gains**, all reading 1 in stock/V122/V189. (Their siblings `0xC64AB`/`0xC64AC` ship at **0**,
which is what proves 0 is a supported state.) ⇒ **there are TWO ω²-scaled terms, not one.**

### ✅ WHY THIS IS THE RIGHT SHAPE FOR THE RATCHET
```
   omega^2 scaling      acceleration-derived => 66x stronger at 8.2 Hz than at 1 Hz
   speed weighting      X = [0, 4, 32, 96] km/h   Y = [64, 64, 32, 32]
                          1 km/h -> 64      24 km/h -> 41      40+ km/h -> 32
                        ** 2x STRONGER AT CREEP **, and the ratchet is a creep symptom
   DC contribution      ZERO -- acceleration is 0 in steady state
```
✅ **So it costs NO LKAS authority and NO added steering weight** — which is exactly the operator's
standing constraint: *do not buy the ratchet fix with apparent mass or friction.*
✅ **V190 = V189 + `0xC64AE` 1→0.** One byte, cal-only, 41/41 assertions.
`ab75a383fad5c65ad03645daffa8d3a93d15916040b438d3a01275e82196744f`

⚠ **THE SIGN IS BELIEF, NOT EVIDENCE — and this is the honest limit.** `gp-0x6752` is −1 (verified
3 ways) so `gp-0x6bc2 ≈ −k·a`; following the recorded polarity chain (`gp-0x6ad6` ↓ ⇒ error ↑ ⇒
**more** assist), positive acceleration → more assist → **positive acceleration feedback = negative
apparent inertia = destabilising**, so removing it should damp the ratchet. **That chain has five
links.** EVIDENCE: the term exists, is acceleration-derived, is 2× weighted at creep, flag reads 1.
BELIEF: the sign. 🛑 **If the sign is inverted the term was providing DAMPING and the ratchet gets
WORSE** — a one-byte revert to V189 undoes it. That failure mode is pre-registered on the card.

## ❌ **NEGATIVE RESULT, RECORDED SO IT IS NEVER REPEATED: THERE IS NO SECOND DORMANT FILTER**
Hunted every dormant Honda feature with the gate signature the biquad uses — a **tp-relative CAL BYTE
that reads 0 in stock** and is compared against a constant. **48 such cals exist.** Every one that
touches the steering path was resolved by decompile:
```
   0xC649B                the BIQUAD ARM        -- already used (V103)
   0xC64AB / 0xC64AC      MUTE switches (cal==0 ENABLES the term) in the gp-0x67ac==1 aggregator
                          branch, gating the RETURN-CENTRE/DETENT term -- which the record already
                          measured DEAD ENGAGED (0.0000 over 75,227 frames).  Useless to us.
   0xC40EB..0xC40EE       DIAGNOSTIC SENSOR OVERRIDES, one per channel:
                            if (magic == 0x49d6b173 && cal == 0xE9)
                                gp-0x6abc = base + value*cal(0xC6134)/1000;   // synthetic
                            else gp-0x6abc = real sensor;
                          Honda's factory injection path for gp-0x6abc/6abe/6ac0/6ac2.
                          NOT a filter, and not something to arm on a moving car.
```
⇒ **ONE biquad, ONE notch. The V188/V189 allocation decision is FINAL, not provisional.**

✅ **BONUS — the delivery path is now decompile-confirmed end to end:**
`FUN_00041464` (sensors, and `gp-0x6c2c = EMA(accel) >> 9` with the EMA coefficient at **`tp+0x50DC`
= `0xC40DC`, exactly the cell V179 moved**) → `FUN_000352b4` (boost + the biquad) → **`gp-0x6b86`**
→ `FUN_0003aa2c` aggregator sum (clamped ±12288) → `gp-0x6b94` → governor → motor.
⊕ **So the notch's output really does reach the motor** — V188/V189's premise is verified, not assumed.
⊕ A **second, parallel EMA** on the same acceleration input exists: `>>7` with coefficient
`tp+0x50DA` = **`0xC40DA`** → `gp-0x6c2e`. Unexplored.

🛑 **METHOD TRAP HIT AND FIXED IN THE SAME TICK — the recorded V850 odd/even displacement bug.**
`ld.bu disp16[tp]` has **two** opcode fields: bits5-10 == **0x3D ⇒ displacement ODD**
(`disp = (hw2 & 0xFFFE) | 1`), **0x3C ⇒ EVEN** (`disp = hw2 & 0xFFFE`). My first scan filtered on
0x3D alone and then computed the displacement as even, so it **caught only the odd half AND reported
every address one too low** — inventing a phantom cal `0xC649A` next to the real arm `0xC649B`.
✅ Caught by cross-checking one address against Ghidra's own decode. **Validate any cal scan by
requiring a KNOWN cell to appear** — here, the arm `0xC649B` at `0x359FE`.

## ✅ **THE BIQUAD GATE, VERIFIED END-TO-END — IT *IS* ENGAGEMENT-GATED, AND V103's PATCH HAS THREE SITES, NOT TWO**
Decompiled stock, then disassembled it, then confirmed the encoding empirically. **Stock:**
```
   35A02  ld.bu   0x74fa, tp, r12     ; cal 0xC64FA = 5
   35A06  ld.bu   -0x671a, gp, r9     ; a runtime byte, NOT engagement
   35A0C  cmp     0x1, r14            ; the arm cal 0xC649B
   35A0E  setfe   r8
   35A12  cmp     r12, r9
   35A18  setfnc  r6                  ; r6 = (r9 >= r12) unsigned
   35A22  be 0x35A86                  ; skip the biquad if r8 == 0
   35A26  be 0x35A86                  ; skip the biquad if r6 == 0
```
**Ours (V122 onward) changes THREE sites — `docs/BUILD-LINEAGE.md` names only the first two:**
```
   0x35A08  ld.bu displacement  -0x671a -> -0x6806   (disp = sext16(hw2 & 0xFFFE))  the LKAS flag
   0x35A12  ec 49 cmp r12,r9    ->  e0 49 cmp r0,r9
   0x35A18  e9 37 setfnc r6     ->  ea 37 setfne r6     <== THE SITE THE LINEAGE OMITS
```
⇒ the live gate is **`cal(0xC649B)==1 AND gp-0x6806 != 0`** — **genuinely engagement-gated.**

⚠ **I asserted mid-session that this gate was BROKEN and the biquad always-on.** That was wrong: I
compared only the two sites the lineage names, and `setfnc` after `cmp r0,r9` *would* be always-true.
The third site is what makes it correct. 🛑 **The encoding was confirmed EMPIRICALLY, not by hand:**
scanning the setf family (`hw1 bits4-10 == 1111110`, `hw2 == 0`) found 10 condition nibbles in use,
and Ghidra decodes nibble **`0xA` at 0x16034 (`ea 57 00 00`) as `setfne`** — the same nibble our build
carries. **Do not hand-decode a condition nibble; find a real instance and let Ghidra name it.**

### ✅ WHAT THIS BUYS V188/V189 — THE 55 Hz RISK IS HALVED
Because the section only runs engaged, **Honda's 55.226 Hz null is given up ONLY WHILE LKAS IS
ENGAGED. Manual driving is bit-for-bit stock**, notch and all. So the one unquantifiable risk on the
notch builds is confined to engaged driving, where the operator is already attentive and where he
stops instantly.
⊕ It also confirms the earlier closure: with every mode-indexed table now equal 24-vs-26, the two
things that remain engaged-only are **the LKAS command** and **this biquad** — which on V189 is the
grind notch.

## ✅✅ **THE ENGAGED/MANUAL ASYMMETRY SPACE IS NOW EXHAUSTED — and that pins what each symptom rests on**
🛑 **CORRECTION to the previous section: MODE 27 IS UNREACHABLE, so V189's relay revert is INERT.**
V73's probe settled this over **104,061 frames**: the car is row 11 `TVCA4`, using **e012 = 24
disengaged** and **e014 = 26 engaged**. Mode 27 would read as **11** in the probe's 4-bit field and
**only 8 and 10 were ever observed.** The V189 edit is still correct — strictly toward stock — but it
is a **cleanup, not a fix**, and the previous section left that ambiguous.

**The sweep that matters instead — EVERY mode-indexed table, m24 vs m26:**
```
   strict scan (>=3 breakpoints, STRICTLY increasing X, real span): 7 tables
     0xC7B40  DIFFERS on V189 -- but DIFFERS ON STOCK TOO (4181 vs 4114)  => HONDA'S OWN
     all other 6                                                          => == m24
   plus the six damper tables asserted in the V189 builder                 => all == m24
```
✅ **NO mode-indexed table on V189 differs 24-vs-26 that is not also different on stock.**
⚠ A looser first pass reported six "asymmetries"; five were **junk from my own heuristic** — records
like `X=(3,3,3)` and `X=(5,5,5,5,5)` passed because it only required NON-decreasing X. **A monotonic-X
test without strict increase and a span floor manufactures tables out of arbitrary data.**

### ⇒ WHAT REMAINS ENGAGED-ONLY ON V189 IS EXACTLY TWO THINGS
1. **The LKAS command itself** (the excitation), and
2. **the biquad ARM** (`0xC649B`=1, ours since V103) — which on V189 **is the grind notch.**

⇒ **so each symptom now rests on one identified mechanism, and both are levered:**
```
   GRIND    a CLOSED-LOOP INSTABILITY (9,200x less power LKAS-off, 2x2 attribution to 0xC6CD0)
            -> the notch at 19.40 Hz breaks the loop AT the unstable frequency.  14.3x.
   RATCHET  engaged-amplified 3.58x.  The flying build's ONLY engaged-only dose was the inertia
            table (m26 Y = -29490/-17202/-16000 vs Honda's -9830/-5734/-1966, ~3x).
            V184+ reverts it, so with every other asymmetry now equal, that revert is the
            candidate mechanism -- and its predicted endpoint is the manual floor.
```
✅ **This makes the earlier pre-registration the live prediction for V189**: engaged ratchet excess
**26.7× → toward the manual 2.8×**, and the null is ~3.9× — i.e. **crossing below the null is
"gone by the instrument", and manual proves that state is reachable.**
🛑 If the ratchet survives V189, the engaged-only cause is **not in the calibration at all** — it
is in the command, which is openpilot's loop (the operator's third symptom, *peak command
oscillation*), and no firmware cal lever addresses it.

## 🛑✅ **V189 — WE HAD CREATED AN ENGAGED-ONLY DAMPER RELAY BY ACCIDENT. TWO BYTES REMOVE IT.**
Auditing **every** FactorC mode record against stock, **exactly one deviates**:
```
   record 0xD77E4, reached by mode 27
     stock  Y = (  0, 233, 426, 875)     monotonic -- Honda's viscous surface
     V188   Y = (426, 233, 426, 875)     steps UP at zero, then DROPS
                 ^^^ Y[0]=426 at 0xD77EE
```
🛑 **THE FLYING BUILD V122 MATCHES STOCK.** So this is a regression introduced in the V177–V183
chain and inherited by V185/V186/V187/V188 — **every build recommended this session.**
**V184's "engaged == manual in every data table" fixed m26 and MISSED m27.**
➕ **WHY IT MATTERS:** FactorC is a factor of the base-assist damper, `ch0 = (FactorC × FactorE) >> 10`.
The recorded fact is **`FactorC Y[0] == 0` in ALL 13 stock records** — the damper is dead at low index
*by design*, which is what makes Honda's surface **viscous rather than switched**. A non-zero `Y[0]`
gives it a floor that engages abruptly at the first breakpoint — **a RELAY** — and a relay in exactly
this component is what V80 shipped, producing **the worst grinding in the whole arc**.
⚠ Here it is worse than a plain relay: **`Y[0]=426 > Y[1]=233`**, so the curve steps up then falls.
**That is not a calibration anyone chose; it is a defect.**
✅ **V189 = V188 + `0xD77EE` 426 → 0**, Honda's value copied from the stock image. **One int16,
2 payload bytes, 38/38 assertions.** All six damper tables now read `m26 == m24` and
`m27 == m24 or IS STOCK`. `71a7032a485ec8253cd46c2532adcf0331382b5b8c374fb204b9fc9d07e9240b`
⊕ **REACHABILITY, STATED HONESTLY:** the record is ambiguous on whether the car runs mode 27 (one
memory says TVCA4 uses **24/26**, another describes **26/27** as engaged). **If m27 is reachable this
removes a live engaged-only relay in the damper — a prime suspect for ratcheting/stuttering. If not,
it is INERT.** The edit is strictly toward stock, so **there is no configuration in which it is
worse.** EVIDENCE: the byte deviation and that V122 matches stock. BELIEF: m27 reachability.

## ✅ **V188'S NOTCH DOES NOT THREATEN ITS OWN LOW SHOULDER — and the reason is structural**
A notch inside a loop adds lag *below* itself, so it could in principle grow a new mode there. On the
pooled 67-route engaged spectrum:
```
   f (Hz)   excess   V188 |H|   added lag
    9.2      8.71      0.852      -14.0     highest excess, SMALLEST lag
   12.0      2.81      0.709      -21.0
   15.0      2.26      0.486      -29.9
   16.2      2.97      0.372      -34.0     largest lag, gain already down 63 %
```
✅ **No frequency has high excess, high retained gain AND large lag at once.** For a notch, **added
lag and attenuation grow together**, so loop gain is cut in proportion to the phase spent — which is
precisely why a notch is the standard tool for this job. Still checkable on the drive: a **new** peak
at 13–16 Hz would falsify it.

## ✅✅ **V188 — THE NOTCH ON THE GRIND. ONE BIQUAD, AND THE MECHANISM DECIDES WHERE IT GOES**
There is **exactly one biquad** (re-checked with a DC-gain-plus-structure criterion; the 60-odd other
"hits" are mode-table data at regular strides, several reporting pole radius > 1). So one notch, and
the middle ground is **DOMINATED**:
```
   design                  ratchet 5-12   grind 15-25   phase @3 Hz
   V187  notch  8.80 Hz        6.0x          0.9x         -10.0 deg
   V188  notch 19.40 Hz        1.3x         14.3x          -3.8 deg   <== RECOMMENDED
   middle notch 14.10 Hz       2.2x          2.3x          -8.2 deg   (worse than BOTH)
```
➕ **THE MECHANISM DECIDES IT — and the kit already established both:**
- **THE GRIND IS A CLOSED-LOOP INSTABILITY.** 21.09 Hz, **9,200× less power with LKAS off**,
  de-confounded 2×2 attribution to the LKAS gain `0xC6CD0` (effect 2.7–3.9×). **A notch inside the
  loop AT the unstable frequency BREAKS THE LOOP — a cure, not a mitigation.**
- **THE RATCHET IS A PLANT RESONANCE.** Ring-down ζ 0.017–0.036, Q 14–29, motor/rack-side, limit
  cycle EXCLUDED. A command notch only reduces its **excitation**; road input still rings the mode.
  And the ratchet **already has an independent lever on this build** — the engaged inertia revert.
- The biquad is **ENGAGED-GATED** (`0xC649B`=1, arm = the LKAS engagement flag) and the grind is
  **ENGAGED-ONLY on 7/7 routes**. An engaged-only filter against an engaged-only instability.
✅ It also costs **a THIRD of the phase**, because 19 Hz is far from openpilot's band — which is
exactly why the notch can be made **WIDE** (r 0.9300 vs 0.9795) and still pass. Per-route grind peaks
run p10 15.74 / median 19.92 / p90 21.68 Hz, so **width is what matters here**, not depth.
✅ **GATES, the best of any filter build in the arc: DC 1.000002 · max|H| 1.3533 · added lag
−1.25° @1 Hz, −3.84° @3 Hz · cal-only, no cave. 30/30.**
`81c0845fdf22c3af8a164c56240acfd3be2467705997f2f299b29fe560be3279`
```
   8.8 Hz -1.2 dB (helps the ratchet too)   15 Hz -6.2   18 Hz -15.3   19.4 null
   21 Hz -13.7   23 Hz -6.7   25 Hz -3.0
```

## ✅ **THE TWO MEASURED GRIND FIXES ARE STILL ON THE CAR — checked, not assumed**
This kit lost V42's ratchet fix to a rebase once (byte-stock V53–V70), so the same check was run:
```
   0xC6446  Lever B, the LKAS-gated r24 arm (V88, grinding FIXED on-car)   5244  CARRIED
   0x3AA96  the V88 sign fix                                               251  CARRIED
   0x454FE  V42 ratchet fix                                                181  CARRIED
```
⚠ **But `0xC6CD0` — the gain the 2×2 identified as the CARRIER of the ~23 Hz vibration — was
3564 (4×) when V88's grind fix was CONFIRMED on-car, and is 5346 (6×) now** (V101 raised it to 8×,
V102 stepped it down to 6×). 🛑 **Lowering it back is NOT recommended: LKAS reach is
`(clip × cal(0xC6CD0)) >> 15`, so 6×→4× cuts authority by a third — the opposite of the operator's
stated goal.** That tension is exactly why the answer is a **notch**: keep the gain, remove its 23 Hz
consequence. ⊕ Supersedes the stale *"the 4× LKAS gain is frozen on every build"* memory, which
predates V101.

## 🛑🛑 **EVERY ENDPOINT IN THIS KIT IS RELATIVE — AND ONE OF THEM INVERTS V184'S VERDICT**
Two endpoint families cover essentially every verdict in the arc, and **both divide by something
that a broadband filter also attenuates**:
```
   A) slope-corrected excess (score_band_excess)   band / power law fitted OUTSIDE the band
   B) control-band ratio     (~every other scorer) band / 30-40 Hz
```
Applying V184's real `|H|²` to the real flying spectrum (route `r24`, V122):
```
   band            ABSOLUTE          ctrl-band ratio      slope excess
   GRIND 15-25     x0.025  -15.9 dB      x3.05  UP          x1.02
   RATCHET 5-12    x0.131   -8.8 dB      x15.6  UP          x1.12
   the 30-40 Hz CONTROL BAND itself falls -20.8 dB -- that is the whole mechanism
```
🛑 **V184 cuts absolute grind 40x, and the kit's standard endpoint would have reported it as a
3-15x REGRESSION.** I would have told him a large fix was a large regression.
✅ **FIXED: absolute band power is restored to `score_band_excess.py`**, with the worked example in
the output so it cannot be re-withdrawn by accident. It was withdrawn once for spectral tilt — the
right handling of tilt is to **report the slope** (which the scorer already does), not to delete the
level. **Compare ABSOLUTE across builds; the ratio is valid only WITHIN a build, where the divisor
is common.**

## ✅ **V187 BUILT — A NEW LEVER CLASS: THE NOTCH, MOVED ONTO THE RATCHET**
Every filter build in the arc (V43, V173/V174/V184) moved the **denominator** — the poles — which
makes a low-pass. **V187 moves the NUMERATOR, which has never been done.**
```
   H(z) = B4*(z^2 + B0*z + 1) / (z^2 + A8*z + AC)
   the numerator's roots have product 1 => they are ALWAYS on the unit circle
   => the numerator is a PERFECT NOTCH and B0 alone sets its frequency
   Honda placed it at 55.226 Hz.  V187 moves it to 8.80 Hz, onto the ratchet.
```
➕ **WHY A NOTCH AND NOT ANOTHER LOW-PASS — and it is a FORCED tradeoff, not a search failure:**
```
   lever                            ratchet atten   phase @3 Hz   dB per degree
   V184 (poles 0.980, low-pass)         -8.8 dB       -40.5 deg       0.22
   best low-pass at a <=10 deg budget   -0.8 dB       -10.0 deg       0.08
   V187 (notch)                         -7.8 dB        -9.95 deg      0.78   <- 3.5x better
```
Unity DC gain pins `B4 = (1+A8+AC)/(2+B0)`; with the notch near 8 Hz that **forces the poles within
~0.05 of the unit circle**, so REAL poles (a low-pass) land their corner at 8 Hz too — reproducing
V184's phase problem exactly. **One biquad cannot serve LKAS phase, ratchet attenuation and 55 Hz
protection at once.** A notch escapes because its phase returns to ~0 away from itself.
✅ **FITTED MINIMAX OVER 67 ROUTES, not the pooled average** — per-route peaks run p10 7.34 / median
7.81 / p90 8.59 Hz, so tuning to the mean leaves a shoulder (V186 did: on r24 its residual peak
moved to 9.96 Hz). Minimax wins on **both** criteria, so it is not an artifact of the robust one:
```
   design                     p90 remaining     median remaining
   V186  8.30 Hz / r 0.9885   0.3983 -4.0 dB    0.2515  4.0x
   V187  8.80 Hz / r 0.9795   0.2584 -5.9 dB    0.1661  6.0x   <- BETTER ON BOTH
```
✅ **GATES: DC gain 0.999972 · max|H| 1.1403 · added lag −2.97° @1 Hz, −9.95° @3 Hz · cal-only,
no cave. 30/30 assertions.** `105238993346f0e7e792e418c808d6ddf3f42504fb8bf2705c1eb7e0cad045ab`
⚠ **THE COST — Honda's 55.226 Hz null is given up** (|H| 0.000016 → 1.136). Our logging is 100 Hz
so 55 Hz is invisible — tested by **ALIASING** (55.226 folds to 44.774 Hz): across **295 routes**
median ratio 0.99, max 2.69, **zero above 3**, while control frequencies reach 3.6–6.5. Evidence
against a road-excited plant mode. 🛑 **HONEST LIMIT: the notch is active in every drive we have,
so this cannot exclude a COMMAND-excited loop mode it is currently suppressing.** BELIEF, not
EVIDENCE. Mitigation: cal-only ⇒ reflash V185 recovers.

## ✅ **THE PRE-REGISTRATION IS COMPLETE — ONE BINARY THRESHOLD, AND MANUAL PROVES IT IS REACHABLE**
Measured on `r24` (the FLYING build) with the scorer's own estimator:
```
   band              ENGAGED    MANUAL    null
   GRIND  15-25 Hz     11.1x     2.3x     ~3.9      manual is BELOW the null
   RATCHET 5-12 Hz     26.7x     2.8x     ~3.9      manual is BELOW the null
   (9 engaged / 26 manual creep windows on this route)
```
✅ **Both manual arms sit below the null**, so "excess below 3.9" is a **demonstrated, reachable
state**, not an aspiration — the car already reaches it whenever LKAS is off.
⊕ This also gives a **single-route answer to the question my hands-on test was too underpowered to
settle**: on `r24` the RATCHET is engaged-only too (manual 2.8 < null 3.9, 26 windows). Not
hands-matched, so it does not replace Stage 1b, but it is real evidence in the same direction as the
7/7 grind result.
⇒ **the drive reduces to ONE binary question: does the engaged excess fall below ~3.9x?**
```
   below ~3.9      -> the symptom is GONE by the instrument; engaged now looks like manual
   falls, above    -> the inertia lane contributes but is not the whole story
   unchanged       -> the inertia-dose account FAILS
```
⊕ And the poles are tested separately by the **spectral slope** (2.671 → 4.531 for V184, outside the
entire 0.80–2.37 history), because they cannot move the excess numbers at all.

## 🛑🛑 **THE SCORER'S EXCESS ENDPOINT CANNOT SEE THE POLES AT ALL — MY CARD DISCRIMINATOR WAS BACKWARDS**
Applying each build's `|H|²` to the REAL flying spectrum (route `r24`, V122) and re-running the
scorer's own estimator:
```
   build                    GRIND 15-25 Hz     RATCHET 5-12 Hz
   FLYING (V122)                11.1x              26.7x
   V185 (poles at Honda)        11.1x              26.7x
   V184 (poles 0.980)           11.3x              30.0x      <- -16 dB of attenuation, and the
                                                                 endpoint does not move
```
🛑 **V184's −16 dB grind attenuation is INVISIBLE to the endpoint the card scores.** The reason
is structural, not a bug: the **slope-corrected excess** divides band power by a power law fitted
**outside** the band (3–6 and 12–40 Hz). A low-pass attenuates the fit region too and **steepens the
fit**, so the RATIO barely moves.
➕ **THE GENERAL FACT, worth more than this build: the scorer measures PEAKINESS, not LEVEL.** A
smooth broadband filter changes level without changing peakiness and is therefore invisible to it.
A **damping** change alters peakiness and IS visible.
❌ So the card's rule *"grind moved ⇒ the poles did it"* is **WRONG and withdrawn.** The poles will
not move that number.

### ✅ THE ENDPOINT THAT DOES SEE THEM — AND THE SCORER ALREADY PRINTS IT
```
   spectral slope over 3-40 Hz
     FLYING (V122)        1/f^2.671
     V185 (poles Honda)   1/f^2.671    delta +0.000
     V184 (poles 0.980)   1/f^4.531    delta +1.860
```
✅ **1/f^4.53 is far outside the entire historical range (0.80–2.37)** — no route has ever produced
anything like it, so a single pass is unmistakable. **This is a binary, pre-registered check.**

### ✅ THE CORRECTED DISCRIMINATOR
```
   spectral slope jumps to ~4.5   => the POLES are live => you flew V184, and they work
   slope unchanged (~2.7)         => you flew V185, or the poles are not reaching the signal
   GRIND / RATCHET excess falls   => the INERTIA DOSE REVERT did it (both builds carry it;
                                     the poles cannot move these numbers)
   nothing moves anywhere         => both accounts fail together
```
⊕ **And note what this means for the fork**: since the excess endpoints respond only to the inertia
revert, **V184 and V185 are indistinguishable on the ratchet/grind excess.** The ONLY thing V184 buys
that V185 does not is the slope change — bought with **+16.4° of engaged-only phase lag**. Stated that
way, **V185 is the better first drive**: same measurable ratchet effect, none of the phase risk.
⚠ The inertia revert's effect is NOT in these numbers (it acts in a different lane), so the excess
columns above are a **lower bound** on what both builds do to the ratchet.

## ✅ **THE GRIND IS ENGAGED-ONLY — 7 ROUTES OUT OF 7, INCLUDING THE FLYING BUILD**
Dry-running the second scorer answered, for the GRIND, the question my underpowered hands-on test
could not answer for the ratchet. Per-route slope-matched nulls, adequate exposure:
```
   route  build   engaged exc / null    manual exc / null    manual real?
   r78    V91       6.1 / 3.5             2.3 / 3.8            no
   r7e    V96      28.9 / 3.2             2.2 / 4.8            no
   r7f    V96      14.3 / 3.5             2.2 / 3.9            no
   r96    V102    248.2 / 4.0             1.5 / 4.9            no
   ra6    V106     25.3 / 4.0             3.0 / 3.9            no
   r1e    V107     27.7 / 2.7             1.6 / 4.5            no
   r24    V122     14.0 / 3.9             1.9 / 4.1            no   <- the FLYING build
```
✅ **The manual arm falls BELOW its own null on every route.** The grind does not exist without
engagement — replicated 7/7 across six different builds, and true on what the operator drives today.
⇒ **an ENGAGED-ONLY lever CAN eliminate the grind**, which is exactly the family on the shelf, and
V184's poles are engaged-gated so they are correctly targeted at it.
⚠ **This is the GRIND, not the ratchet.** The same question for the ratchet remains unanswered —
that test needs hands-on exposure the corpus does not have (21/11 windows), which is why Stage 1b
exists.

## ✅ **BOTH SCORERS DRY-RUN CLEAN — AND ONE CARRIED STALE ATTRIBUTION**
`score_band_excess.py` and `grind_engaged_vs_manual.py` both run end to end on r77/r24.
🛑 But the first told the operator to attribute a result between **V172, V173 and V158** — none of
which are on the shelf. **Had he driven V185 and run it, the guidance would have misled him.** Updated
to the actual fork:
```
   GRIND moved at all       => the POLES did it => you flew V184 and they work
   GRIND essentially flat   => expected on V185; read the RATCHET row instead
   RATCHET down, grind flat => the INERTIA dose revert (both builds carry it)
   neither moved            => both accounts fail together
   427 now carries gp-0x6ac0 >> 4 (V183+), NOT motor torque; gate at field 812
```
⊕ **Testing the instrument before the drive is worth as much as another lever** — a scorer that
runs but says the wrong thing wastes the drive just as completely as one that crashes.

## 🛑 **I BROKE THE DRIVE CARD LAST ROUND, AND THIS CAUGHT IT: THERE ARE ZERO HANDS-ON 15 s WINDOWS**
Last round I changed the card to demand HANDS ON, on the strength of the hands-off confound. **That
was half-right and it broke the other half.**
```
   continuous 15 s ENGAGED CREEP windows in the corpus
     ALL (what the card's thresholds were computed on)   27
     HANDS-ON (what the card then started demanding)      0     <- ZERO
```
⇒ **two problems, both mine:**
1. **The card's promises do not transfer.** Grind "ANSWERABLE, margin 2.89x", ratchet "needs 2
   passes", LKAS "not measurable" — all computed on **hands-OFF** windows. Nothing supports them
   for a hands-on pass, and there is **no data to recompute them from.**
2. **It broke comparability with the entire corpus.** The 27-window historical baseline is
   hands-off. A hands-on-only drive could not be compared to ANY of it.

### ✅ THE FIX — ASK FOR BOTH, 30 SECONDS TOTAL
```
   1a  15 s engaged creep, driven HOW HE NORMALLY DOES   -> SCOREABLE today, thresholds apply,
                                                            comparable to the 27-window baseline
   1b  15 s engaged creep, HANDS ON                      -> answers the cs_tq confound and builds
                                                            the first hands-on baseline;
                                                            ** thresholds UNKNOWN, stated as such **
```
✅ 1a keeps every promise the card already makes. 1b buys the thing the corpus provably cannot
supply. Neither is asked to do the other's job, and **1b is explicitly labelled a baseline-building
pass, not a scored one** — so it cannot produce a result I would then over-read.
⊕ **THE GENERAL LESSON**: changing what a drive asks for **silently invalidates every power figure
computed on the old exposure.** Re-run the power check against the NEW exposure, or the card is
promising a result the drive will not deliver.

## 🛑 **THE CORPUS CANNOT ANSWER HANDS-MATCHED QUESTIONS — ONLY 21 ENGAGED HANDS-ON CREEP WINDOWS EXIST**
Three tests in a row have now failed their controls, and the cause is one structural fact.

**The question**: every lever on the shelf is engaged-only, so *does the ratchet exist in MANUAL?*
If it does, an engaged-only lever can at best remove the ~3.6x engaged excess and leaves the rest.
```
   HANDS-ON windows in the WHOLE corpus:   engaged 21   manual 11
   slope-corrected excess at a FIXED 8.40 Hz, power law fitted on 3-6 and 12-40 Hz:
       ENGAGED   0.71x   CI [0.43, 1.31]   no significant peak
       MANUAL    1.45x   CI [0.80, 2.72]   no significant peak
```
🛑 **THE ENGAGED ARM IS THE POSITIVE CONTROL, AND IT FAILS** — the ratchet is known to be there
and the test cannot see it. So the manual null means nothing, and the script's auto-verdict ("no
ratchet in manual ⇒ the engaged levers are the right family") is **unsupported and withdrawn.**

➕ **A REAL METHOD FIX CAME OUT OF IT.** The first version scored the band with `argmax`, and the
point estimate landed **outside its own bootstrap CI** (engaged 1.47x vs CI [1.48, 3.71]). A
max-over-band statistic is **upward-biased under resampling**; the estimator now reads a **FIXED**
frequency. With that fix the ordering also stopped being backwards (it had manual > engaged, which
contradicts everything established).
🛑 **RULE: never bootstrap a max-over-band statistic. If the point estimate falls outside its own
CI, the statistic is biased, not the data interesting.**

### ✅ THE ACTIONABLE CONSEQUENCE — THE DRIVE MUST BE HANDS-ON, AND THE CARD NOW SAYS SO
The corpus is overwhelmingly hands-OFF while engaged (1606 hands-off vs 21 hands-on creep windows),
because that is how the car is normally driven. **Every hands-matched question is therefore
unanswerable from existing data**, including:
- does the ratchet exist in manual at all?
- is the ~3.6x engaged excess the whole effect, or only the part hands-on exposure can see?
⇒ **the Stage 1 pass must be driven with HANDS ON THE WHEEL**, which also matches how the operator
actually experiences the symptom. That is a one-line change to the card and it makes the drive
answer questions the corpus cannot.

## 🛑 **RECALIBRATION: ENGAGEMENT AMPLIFIES 8.4 Hz BY ~3.6x, NOT 15-33x. I QUOTED THE CONFOUNDED FIGURE ALL SESSION.**
`cs_tq` is the DRIVER TORQUE SENSOR, and when engaged the driver largely is not steering. So an
engaged-vs-manual torque comparison conflates **engagement** with **hands-off**. Stratifying on
`cs_press` (steeringPressed) separates them:
```
   subset        n_eng  n_man   ratio @ 8.40 Hz    95 % CI (bootstrap over WINDOWS)
   ALL            2255    339        20.94         [16.29, 41.43]
   ** hands-ON      68     77         3.58         [ 1.36, 14.92]  <- the FAIR comparison **
   hands-OFF      1606     56        18.34         [ 5.44, 68.85]
```
✅ **The amplification is REAL** — the hands-on CI excludes 1. 🛑 **But it is ~3.6x, not the
15-33x I have been repeating.** The large numbers are engagement *plus* hands-off, not engagement.
⊕ **THE KIT'S OWN RECORD HAD IT RIGHT**: [[accord-engagement-amplifies-6-9hz]] gives a band contrast
of **2.8x**, which sits inside [1.36, 14.92]. **My session figures drifted upward; the record did
not.** Every earlier statement in this session of the form "engaged-amplified ~15x" should be read
as **~3.6x [1.36, 14.92]**.
⚠ The hands-on cell is small (68/77 windows), which is why the CI is wide. A tighter number needs
matched hands-on exposure, which is a drive request, not an analysis.

### ❌ AND THE 4.7 Hz "CROSSOVER" IS DEAD — IT WAS THE SAME CONFOUND
I measured engagement SUPPRESSING below ~4.7 Hz and AMPLIFYING above, and started reasoning about
which firmware element has its phase crossover there (none does: the nearest corners are 16.7, 21.3
and 36.2 Hz). **The hands-on control kills it:**
```
   hands-ON    crossover NOT FOUND in 2-20 Hz    CI [5.83, 18.97] Hz  -- spans the band
   hands-OFF   crossover 5.38 Hz                 CI [4.59,  6.12] Hz
```
⇒ with hands on there is **no detectable crossover**. The suppression below 4.7 Hz was **the driver
not steering**, not loop dynamics. **The line of reasoning is withdrawn before anything was built on
it.**

### ➕ WHAT THIS CHANGES FOR THE BUILDS
Nothing about which cells are right — but it **resizes the target**. The effect to eliminate is
**~3.6x at 8.4 Hz**, not 15-33x, so:
- a lever that removes a 3.0x engaged-only dose (the inertia revert, V185) is **the right order of
  magnitude** to account for it, which strengthens rather than weakens that build;
- and the drive's detection threshold matters more than I implied: the earlier power check found one
  15 s pass resolves a **presence/absence** change, and a ~3.6x band move is comfortably inside the
  **grind** endpoint's power but near the ratchet endpoint's, which needs 2 passes.

## ❌ **THE FREQUENCY SIGNATURE DOES NOT SETTLE THE V184/V185 FORK — BUT IT SHARPENED THE MEASUREMENT**
The fork is whether the ratchet is driven by the **inertia lane** (`gp-0x6b26 = K·α`, loop
contribution ∝ ω²) or by **assist-section loop gain** (a mild broadband filter on the car). Both are
engaged-only, so the engaged/manual *contrast* cannot separate them — but their **frequency
signatures** differ, so the engaged/manual ratio vs frequency should.
✅ **Speed-matched** (300 engaged / 300 manual windows, mean 15.2 vs 14.6 km/h) with a **permutation
null on the labels**:
```
   engaged / manual PSD ratio        3.91 Hz   0.79      <- engagement SUPPRESSES 4 Hz
                                     8.20 Hz  30.56
                                     8.40 Hz  33.06      <- the peak
                                    15.04 Hz   8.72
                                    25.00 Hz   5.48
   log-log slope over 3-30 Hz  b = +0.461   permutation null [-0.119, +0.113]
```
🛑 **MY FIRST VERDICT WAS WRONG.** The script concluded "slope exceeds its null ⇒ inertia
fingerprint ⇒ V185 favoured". **It tested the wrong thing.** An ω² force term needs **b ≈ +4 in
PSD**; observed is **+0.461**. And the shape test settles it:
```
   peak 33.06x at 8.40 Hz    band-edge mean 1.48x    peak / edges = 22.3x
```
⇒ **the ratio is a narrow PEAK, not a power law.** Fitting a line to a peaked function produces a
spurious positive slope, and its significance against the null says nothing about ω². The verdict
logic now tests SHAPE first and reports no discrimination.
⇒ **THE FORK STAYS OPEN. Only the car can settle it.**

### ✅ WHAT THE MEASUREMENT DID BUY — A MUCH SHARPER ENGAGEMENT NUMBER
The record carried engagement amplifying the ratchet band **~15x** (and 2.8x on a band contrast).
**Speed-matched, the peak is 33.1x at 8.40 Hz**, and the excess is **narrow**: 22.3x above the
band edges, with the ratio **BELOW 1 (0.79) at 3.9 Hz**.
⇒ **engagement does not raise torque activity broadly — it SUPPRESSES ~4 Hz and excites a specific
mode at ~8.4 Hz.** That is a resonance being driven, not a gain change, and it is the cleanest
statement of the engagement effect the kit has.
⊕ It also re-confirms the mode centre independently: **8.40 Hz**, inside the ±0.71 Hz wander band
established earlier, and consistent with 8.17–8.20 Hz from the other estimators.

## ✅ **GATE 2 PHASE, ENGAGED-ONLY — V184 PASSES AT THE RATCHET, AND THE COST IS NOW QUANTIFIED**
The biquad being engaged-gated forced the phase check V184 had never had. **It passes, and cleanly.**
```
   at 8.17 Hz the multiplicative change in the loop path is r = H_V184 / H_flying
       |r| = 0.3642        arg(r) = -61.51 deg
       Re(r) = +0.1737     Im(r) = -0.3201
   the destabilising direction is L -> +1 (real, positive)
   => |r| < 1 AND Re(r) < 1: the rotation moves L AWAY from +1 on BOTH axes.
      ** The phase lag does NOT give back the 64 % gain reduction. **
   max |H_V184 / H_flying| over 0.1-499 Hz = 0.9995  -> it never amplifies at ANY frequency.
```
✅ So the pole retune is stabilising at the ratchet in magnitude *and* in phase, which is the check
[[feedback-run-the-control-before-the-measurement]] would demand and which the earlier
magnitude-only GATE 2 did not cover.

### ⚠ THE COST, STATED AS A NUMBER FOR THE FIRST TIME
```
   engaged-vs-manual phase (manual is a BYPASS, H = 1)
        1.00 Hz   flying  -1.35 deg  ->  V184  -17.78 deg     (+16.43 deg)
        8.17 Hz   flying -11.13 deg  ->  V184  -72.65 deg     (+61.51 deg)
       21.00 Hz   flying -30.01 deg  ->  V184  -91.82 deg     (+61.81 deg)
```
⚠ **+16.4 deg of engaged-only lag at 1 Hz is a real phase-margin cost**, and it bears on the
operator's THIRD goal: added lag inside a loop is exactly what worsens command oscillation.
🛑 **BUT WHETHER IT REACHES OPENPILOT'S LOOP IS NOT ESTABLISHED.** The biquad sits on the
**torque-fed** assist path (`gp-0x6b86`); openpilot's command travels a different lane. The coupling
is **unestablished, not absent** — [BELIEF] that it is small, and it is pre-registered here as a risk
the drive can contradict: **if peak command oscillation gets WORSE while the grind improves, this is
the mechanism to suspect first.**
⊕ Note the lag is nearly flat above ~8 Hz (+61.5 deg at 8.17, +61.8 at 21) — the pole is well below
the band, so the ratchet and grind see essentially the same rotation.

## 🛑 **CORRECTION: THE BIQUAD IS ENGAGED-GATED, SO V184 IS A TWO-VARIABLE TEST, NOT ONE**
I wrote in V184's docstring that the assist-section poles *"act in both modes, so they do not confound
the engaged/manual contrast."* **That is WRONG.** Read from the images:
```
   build         0x35A06 arm src   0x35A12   0x35A18   0xC649B   arm
   stock         gp-0x671a         0xEC      0xE9      0         Honda's gate, DISABLED
   V103          gp-0x6806         0xE0      0xEA      1         ENGAGED-ONLY (LKAS flag)
   V122 FLYING   gp-0x6806         0xE0      0xEA      1         ENGAGED-ONLY
   V184          gp-0x6806         0xE0      0xEA      1         ENGAGED-ONLY
```
⇒ **the biquad runs only while LKAS is engaged**, so **every pole edit (V173/V174/V176/V180 and
therefore V184) is an ENGAGED-ONLY change.**
➕ It is also a **SECOND kit-created engaged/manual asymmetry on the car** — one my mode-record
enumeration could not have found, because it is a **code path**, not a data table. The enumeration was
sound for what it covered and I overstated its scope.

### 🛑 WHAT THIS COSTS, AND WHAT REPLACES IT
❌ **The engaged-vs-manual ratio NO LONGER isolates the inertia dose.** V184 carries two engaged-only
changes — the inertia revert and the pole retune — so a ratio move cannot attribute between them.
✅ **But a BAND discriminator still separates them cleanly, because their frequency signatures differ:**
```
   lever                  grind 15-25 Hz     ratchet 6.5-11 Hz
   assist-section poles      -16.0 dB            -8.8 dB      (hits the GRIND hardest)
   inertia dose revert       ~none               engaged-only (hits the RATCHET only)
```
⇒ **grind falls hard AND ratchet falls modestly → the poles.**
⇒ **ratchet falls with the grind roughly unchanged → the inertia dose.**
⇒ **both fall in proportion to the table above → both are contributing.**
That is a usable, pre-registered discriminator and it does not need the manual pass at all.

### ➕ IS THE ENGAGED-ONLY BIQUAD ITSELF THE ~15x AMPLIFIER?
**Probably not, and the reason is worth recording.** Unarmed the section is a BYPASS (`H ≡ 1`); armed
with Honda's coefficients `|H| <= 1` everywhere, so arming it can only REMOVE gain. Engaged therefore
sees **less** high-frequency gain than manual, which would make engaged **less** ratchet-prone, not
more. ⚠ The one channel by which it could still matter is **PHASE**: an engaged-only phase lag can
cost stability margin even when the magnitude only falls. With Honda's coefficients at 8 Hz that lag is
small (a few degrees) — but **V184's retuned poles make it large**, which is a real and previously
unstated engaged-only cost of the pole lever. [BELIEF, structural — not measured.]

## ✅ **INTEGRITY CHECK AFTER TWO RETRACTIONS — THE SHELF IS CLEAN**
After retracting V178 and V182 I re-ran **every surviving builder** and re-checked what each one
actually touches. **All eight reproduce bit-for-bit with every assertion passing, every artifact on
disk matches its recorded hash, and each has exactly ONE flashable `.rwd`.**
```
   V173 25/25   V174 27/27   V175 26/26   V176 28/28
   V177 21/21   V179 19/19   V180 30/30   V181 27/27
```
✅ **No surviving build touches a retracted cell relative to its own base.** V181 is byte-identical to
its ancestor V158 at `0xD77DA`, `0xD77EE`, `0xC6598` and `0xC65C4`. Both retracted images are renamed
`SUPERSEDED-DO-NOT-FLASH-*` and their builders raise on entry.
⚠ **My first pass of this check FLAGGED ALL EIGHT** — because it compared against the FLYING build
instead of each build's own base, so it caught **V158-era inheritance** and called it a defect. The
check was wrong, not the builds. **A comparison is only as good as its reference.**

### 🛑 AND IT SURFACED SOMETHING THE OPERATOR SHOULD KNOW
```
   cell       stock   V122 (FLYING)   V158 (my base)   all my builds
   0xD77DA      0           0              429              429
   0xD77EE      0           0              426              426
```
**V158 changed FactorC's below-range fallback from 0 to 429/426, and the car does not have that
change.** So **every build I have made already carries a V158-era damper edit relative to what is on
the car** — inherited, not something I added, and present in V173 through V181 alike.
⊕ That also partly rehabilitates the damper direction: **V158 already moved this fallback the way
V182 tried to move it further.** But the axis is still `gp-0x6a5e`, not speed, so *when* it applies
remains unestablished — V182 stays retracted.

## 🛑🛑 **V182 RETRACTED — FactorC's AXIS IS `gp-0x6a5e`, NOT VEHICLE SPEED. AND THE DAMPER IS A FIVE-FACTOR PRODUCT.**
`FUN_00034350` decompiled. **`gp-0x6bd0` is not `FactorC x FactorE`. It is a FIVE-factor product:**
```
   uVar7 = ((( clamp(gp-0x698a, 0x400) * L1 >> 10) * FactorC >> 10) * L3 >> 10) * FactorE >> 10
   if (gp-0x6abe > 0)  uVar7 = -uVar7
   gp-0x6bd0 = clamp(uVar7, +- L5)

   L1      = LERP(0xC9CCC[mode], index = |gp-0x6bcc| )
   FactorC = LERP(0xC9E9C[mode], index = gp-0x6a5e )     <-- ** NOT vehicle speed **
   L3      = LERP(0xC9DB4[mode], index = gp-0x6a10 )      (absolute steering angle)
   FactorE = LERP(0xC9F84[mode], index = gp-0x6ac0 )      (resolver / FOC ELECTRICAL RATE)
   L5      = LERP(PTR_000C77A0[mode], index = gp-0x6ac2 ) (the symmetric output clamp)

   GATES:  FactorC needs gp-0x67f4 == 1 AND gp-0x6a5e <= 0x7d00, else it is ** 1024 (UNITY, not 0) **
           FactorE needs gp-0x6ac0 < 0x32c9 AND |gp-0x6abe| <= 0x6590, else ** the WHOLE PRODUCT = 0 **
```
🛑 **V182 raised FactorC's below-range fallback believing X[0] = 2240 = 35.0 km/h. That was
NUMEROLOGY** — 2240/64 happens to equal 35 and I built on the coincidence. **The index is
`gp-0x6a5e`.** Whether that signal is ever below X[0] during creep ratcheting was never established.
⇒ artifacts renamed **`SUPERSEDED-DO-NOT-FLASH-WRONGAXIS-*`**, builder raises on entry.
❌ **The 272-crossing knot-step null is also void for this purpose** — it tested SPEED crossings
against a knot that is not on speed. It remains valid only as a statement about speed knots generally.

### 🛑 THE PATTERN, STATED PLAINLY — THIS IS THE FOURTH TIME TODAY
V178 (authority ladder), the damper-memory flip-flop, the FS=100 errors, and now V182: **every one
was asserting what a table's AXIS or a cell's ROLE is from something plausible — a round unit
conversion, a nearby array, an adjacent build number — instead of from the code.**
➕ **STANDING RULE, and it supersedes the softer versions I wrote earlier today:
BEFORE ANY EDIT TO A LERP, QUOTE THE INDEX EXPRESSION FROM THE DECOMPILE.** Not the X values, not
the unit conversion, not the neighbouring table — **the index expression.** If it cannot be quoted,
the axis is unknown and the edit is a bet.

### ✅ WHAT THIS TRACE DID ESTABLISH, CORRECTLY
- **`w[0]` (`0xC63A0`) IS a genuine second multiplier** on this whole product, confirming the
  lineage's description. It is at 1024 and V72/V77 moved it 2x on-car fault-free.
- **The damper has a hard OFF switch**: `gp-0x6ac0 >= 0x32c9` or `|gp-0x6abe| > 0x6590` zeroes the
  entire product. Any damper lever is inert whenever either holds.
- **FactorC's gate FAILS OPEN to 1024 (unity), not to 0** — so a "dead zone" reading of FactorC is
  wrong in the other direction too.
- The five indices are now named, which is the map any future damper work needs.
🛑 **No damper build should be attempted until `gp-0x6a5e` and `gp-0x6ac0` are characterised on
the corpus** — their distributions during engaged creep ratcheting decide whether any of these knots
is even reachable.

## ✅🛑 **MODE-PROOFED AND FINAL: THE DAMPER IS LIVE AT CREEP WHEN ENGAGED, DEAD IN MANUAL**
**This point flipped three times. It is now pinned by disassembly and by the pointer table, and this
section supersedes every earlier statement about it.**

### THE INDEX, PINNED BY DISASSEMBLY
```
   0x34502  ld.bu  0x63fd, gp, r13     ; the MODE INDEX byte, at gp+0x63FD
   0x34506  mov    0xc9e9c, r16        ; FactorC pointer table
   0x3450c  shl    0x2, r13            ; index * 4
   0x3450e  add    r16, r13
   0x34510  ld.w   0x0, r13, ep        ; -> the per-mode record
```
`gp+0x63FD` is **the same byte `FUN_00036c12` uses for the `0xCBE74` dereference**, and this car runs
**mode 24 = MANUAL, modes 26/27 = ENGAGED** ([[accord-car-is-tvca4-mode-24-26]]).

### THE RECORDS AT THE RIGHT INDICES (V181 vs stock)
```
   FactorC 0xC9E9C[m]        X                          Y
     m24 -> 0xD67E4   [2240,3840,5120,8960]   [  0,234,429,908]   STOCK-IDENTICAL
     m26 -> 0xD77D0   [2240,3840,5120,8960]   [429,234,429,908]   Y[0] 0 -> 429
     m27 -> 0xD77E4   [2240,3840,5120,8960]   [426,233,426,875]   Y[0] 0 -> 426
   FactorE 0xC9F84[m]
     m24 -> 0xD6820   [  60,400,2500,4000]    [  0,140,539,927]   STOCK-IDENTICAL
     m26 -> 0xD780C   [  12,400,2500,4000]    [  0,539,539,927]   X[0] 60->12, Y[1] 140->539
     m27 -> 0xD7820   [  12,400,2500,4000]    [  0,539,539,927]   same
```
🛑 **X[0] = 2240 = 35.0 km/h and Y[0] is the BELOW-RANGE FALLBACK** ⇒ below 35 km/h:
**manual returns 0 (dead), engaged returns 429.** During an 8 Hz ratchet the oscillation itself makes
~50 deg/s, which clears FactorE's knee, so
**ch0 = (429 x ~310) >> 10 = ~129 — the damper IS working at creep WHEN ENGAGED.**

### 🛑 THE THREE FLIPS, RECORDED SO THIS STOPS
1. I read `0xD77DA`/`0xD77EE` directly and said the damper is live — **that was RIGHT.**
2. I resolved the pointer table at **indices 0..3**, found stock values, and retracted — **that
   retraction was WRONG.** Indices 0..3 are some other mode set entirely.
3. Resolving at the **actual mode indices 24/26/27** returns exactly the `0xD77xx` records from (1).
⊕ **THE LESSON IS NOT "resolve the pointer table" — I did that and still got it wrong. It is:
RESOLVE IT AT THE MODE INDEX THE CAR ACTUALLY RUNS.** A pointer table read at index 0 is as wrong as
no pointer table at all. [[accord-car-is-tvca4-mode-24-26]] RULE 7 exists for exactly this.

### ✅ WHAT IS STILL AVAILABLE, NOW MODE-PROOFED
FactorC m26/m27 `Y[0]` is **429/426 against an in-range maximum of 908**, so creep damping can be
raised ~2x by moving the fallback. ✅ The knot-step worry is **measured away**: 272 crossings of
35 km/h vs 1069 controls give a median activity ratio **1.030** against a permutation null of
**[0.863, 1.190]** — the knot sits exactly on the smooth speed trend, so knot discontinuities in this
family are not detectable on-car.
⊕ **Manual (m24) is stock and stays stock** — so this lever is **ENGAGED-ONLY**, which also makes it
separable on a drive by the same engaged-vs-manual contrast the card already uses.

## ✅✅ **EVERY BYTE OF THE NON-STOCK DELTA IS NOW ACCOUNTED FOR — THE AUDIT IS COMPLETE**
Not "I could not find more" — **enumerated, classified, and each class resolved.**
```
   PART                       METHOD                          RESULT
   cal cells (u16/byte)       value across 139 images,        every SINGLE JUMP resolved;
                              in build order                  LADDERs identified as deliberate
   0xE4195..0xE5FFF           same                            80 bytes; the dominant run is
                              (9 x u16)                       15360 -> 16384 at V38 = an
                                                              AUTHORITY raise. DO NOT revert.
   float block 0xC6598..CC    same                            V31/V38 AUTHORITY LADDER. V178
                                                              tried to revert it and is RETRACTED.
   cave 0xC4B34 (164 B)       disassembled every gp/tp        7 READS of control cells; all 5
                              access inside the extent        WRITES go to gp-0x1511/13/14, the
                                                              CAN scratch it owns. TELEMETRY-ONLY,
                                                              no control cell written. CLEAN.
   code bytes                 lineage + churn history         0x35A08/12/18 V103 arm - 0x3AA96 +
                                                              0xC6446 Lever B - 0x454FE V42 fix -
                                                              0x2A1F0, 0x55C0E/DF2/E10 telemetry
```
🛑 **THE FIRMWARE SEARCH IS COMPLETE, AND THIS TIME IT IS VERIFIED COMPLETE RATHER THAN
DECLARED.** Twice today I said the search was finished and was wrong; both times the gap was found by
reading BYTES rather than the record. The delta has now been read byte by byte.

### ✅ WHAT THE WHOLE SESSION PRODUCED — SIX BUILDS, TWO LEVER FAMILIES, THREE HONDA REVERTS
```
   V173  assist-section poles 0.970           grind -12.6 dB, ratchet -5.9 dB, +29 ms lag
   V174  assist-section poles 0.980           grind -16.0 dB, ratchet -8.8 dB, +43 ms lag
   V175  V173 + engaged inertia Y -> Honda    removes a 3.0x/8.1x engaged-only dose
   V176  V175 + pole 0.980                    the strongest attenuation inside the lag guardrail
   V177  V175 + K1 -> Honda (ONE cell)        removes a 10x-oversized velocity-dependent term
   V179  V177 + accel alpha -> Honda (1 byte) completes Honda's inertia lane (gain + filter)
   V178  RETRACTED and quarantined            would have cut LKAS authority ~5x
```
✅ **FLY V177 FIRST.** One cell, fully attributable, quantitative case, and it contains V175/V173.
➕ Then **V179** (completes the lane) or **V176** (more attenuation, more lag), per the card.
🛑 **Nothing further can be settled without the car.** Every remaining question — which lever the
ratchet responds to, whether the lag is acceptable, whether `0xC63A6` is needed — is a drive question,
and the drive card is staged so Stage 1 is a single 15 s pass.

## ✅ **THE NON-STOCK DELTA IS NOW FULLY AUDITED — 139 IMAGES, EVERY CELL CLASSIFIED**
Applying the rule the V178 error earned: print every non-stock cal across **all 139 images in build
order**, then classify. **LADDER** (3+ changes / monotone) = a deliberate tuning axis, do not revert.
**CHURN** = already explored. **SINGLE JUMP** (changed once, never revisited) = the candidate class,
and the shape of both real findings today.
```
   SINGLE JUMP           resolution
   0x14120, 0xC64DE      V2, ancient, 1-count            -- noise
   0x35A08/12/18         V103 biquad arm                 -- documented, deliberate
   0xC61C0, 0xC64B4      V36/V37 -- read together at the SAME four sites; memory records these
                         as the gentle-EME debounce disable that FIXED the problem on-car.
                         ** Reverting them would bring the gentle EME back. **
   0xC40DC               V122, 22 -> 8   ** THE ONLY ONE UNEXPLAINED **
```
=> **the delta is fully accounted for.** No further unexplored cells exist.

## ✅ **V179 BUILT — HONDA'S ACCELERATION FILTER, THE LAST UNEXPLORED CELL**
`FUN_00041464`: `gp-0x6c2c = EMA(accel, alpha = cal[0xC40DC] >> 6) >> 9`, the input to the
apparent-inertia term.
```
   build            cal    a        fc        phase lag at 8.17 Hz
   Honda / V108      22   0.3438   67.0 Hz        6.95 deg
   V122+ (flying)     8   0.1250   21.3 Hz       21.03 deg
```
=> **V122 slowed the acceleration filter 67 -> 21 Hz and added 14.1 deg of phase lag at the ratchet.**
Extra lag rotates a positive-acceleration-feedback term toward a velocity term, changing its
character in the loop.
⚠ **HONEST LIMIT: the magnitude is exact; the SIGN of its effect on damping is NOT established.**
So V179 is justified exactly as V175 and V177 are — **a revert to Honda's own value that makes the
inertia lane self-consistent** (V175 gave it Honda's GAIN; this gives it Honda's FILTER, removing a
hybrid nobody designed) — and **NOT as an understood lever.**
✅ **ONE byte · 19/19 assertions · CRC 50/50 · readback byte-identical.** image
`c1e07f2d6e86bc31…` · rwd `c19f3b36bcdf8daf…`. ➕ The builder **asserts the V31/V38 authority
ladder is INTACT at 5.0**, so V178's error cannot recur silently.
🛑 **V177 STAYS FLY-FIRST.** V177's case is quantitative (a term 10x oversized); V179's rests on
design coherence with an unestablished sign. **V179 is the follow-up if V177 helps but does not cure.**

## 🛑🛑 **V178 IS RETRACTED AND QUARANTINED — THOSE CELLS ARE THE AUTHORITY LADDER, NOT V122'S DOING**
**I built a firmware image on a wrong premise and nearly handed it over as flashable. Caught by the
audit I had scheduled, one turn later.**
❌ **The claim**: V122 flattened three LERPs to ±5.0 and deleted a deadband, so V178 reverts them.
✅ **The full V108-vs-V122 diff is TWELVE BYTES in five payload runs, and that block is NOT among
them:**
```
   0x55DF2  37844 -> 38212   CAN 427 telemetry source
   0x55E10  12965 -> 12963   427 packer sar
   0xC40BC    600 -> 3000    Coulomb ramp width      <- V177 keeps this (protective)
   0xC40D2    204 -> 1020    K1 Coulomb              <- V177 REVERTS this; still valid
   0xC40DC     22 -> 8       accel EMA alpha         <- still OPEN
```
🛑 **The real history of `0xC6598`/`AC`/`C4`/`C8`/`CC`, read across EVERY image in the repo:**
```
   stock  1.0  -1.0   0.0  1.5  2.0
   V29    2.0  -2.0   (stock ramp)
   V30    4.0  -4.0   (stock ramp)
   V31    4.0  -4.0   4.0  4.0  4.0
   V38    5.0  -5.0   5.0  5.0  5.0     <- and unchanged on EVERY build since
```
⇒ **that is a deliberate GAIN / AUTHORITY LADDER, raised at V31/V38** — almost certainly how this
kit obtains its LKAS authority at all. **Reverting it to Honda's 1.0 would cut authority ~5x, the
exact opposite of the operator's second stated goal.** V178's artifacts are renamed
**`SUPERSEDED-DO-NOT-FLASH-AUTHORITY-*`** and `build_v178_tva.py` now raises on entry.

### 🛑 THE METHOD ERROR, WHICH IS THE REAL LESSON
**I asked "did V122 change this cell?" when the question that mattered was "WHEN did this cell
change?"** Having just found the lineage gap at V122, I attributed everything unfamiliar to V122
without checking. **One `for build in images: print(value)` loop — four lines — settled it and would
have prevented the build entirely.**
➕ **STANDING RULE, earned:** before reverting ANY cell, print its value across **every image in the
repo, in build order**. A cell that steps through a **ladder** (1 → 2 → 4 → 5) is a **deliberate
tuning axis**, not an accident, and reverting it undoes deliberate work. A cell that jumps **once** is
the candidate.

### ✅ WHAT SURVIVES, UNCHANGED
- **V177 stands.** `0xC40D2` 204 → 1020 **is** genuinely V122's, confirmed by this very diff. Its
  rationale, its single-cell attribution and its fly-first status are unaffected.
- **The lineage gap stands** — `grep V122` still returns zero rows — but its consequence is smaller
  than I said: V122's cal delta is **three** cells, not four, plus two telemetry cells.
- **`0xC40DC` (22 → 8) remains genuinely V122's and genuinely OPEN.**
❌ **Retracted with V178**: the "V122 deleted a deadband / flattened a ramp" story, and the V80-relay
framing attached to it.

## 🛑🛑 **THE BUILD LINEAGE STOPS AT V121 — AND V122, THE FLYING BUILD, MADE FOUR UNDOCUMENTED CHANGES**
**`docs/BUILD-LINEAGE*.md` contains ZERO occurrences of "V122".** The highest documented build is
**V121**. Nothing from V122 to V178 has a lineage row. 🛑 **Every lever proposed this session was
checked against a lineage that does not cover what is on the car** — which is exactly why V122's
changes only surfaced when I finally read the raw byte delta rather than the record.
```
   V122's undocumented delta, read from the images:
     0xC40D2  K1 Coulomb        204  -> 1020    (5x; 10x Honda)   -> reverted by V177
     0xC40BC  ramp width        600  -> 3000    (5x)              -> KEEP, it is protective
     0xC40DC  accel EMA alpha    22  -> 8                          -> OPEN, a phase change
     0xC6598/9C/AC/B0/C4/C8/CC  three LERPs flattened to +-5.0     -> reverted by V178
```
⚠ **This is the failure the lineage rule exists to prevent**, and it defeated the rule's own
enforcement: *"grep `build_v*_tva.py` and `BUILD-LINEAGE.md` before naming any address"* returns
nothing for a cell V122 moved, so the check silently passes.

## ✅ **V122 FLATTENED A GRADUATED RAMP TO A CONSTANT, AND DELETED A DEADBAND — V178 RESTORES IT**
Pinned by disassembly at `0x44374..0x443EE` inside `FUN_00043e44`:
```
   0x44374  ld.w   0x75b8, tp, r11    ; X[0] = 700.0
   0x44378  cmpf.s le, r9, r11        ; input < X[0] ?
   0x4438e  ld.w   0x75c4, tp, r13    ; -> Y[0]   ** the BELOW-RANGE FALLBACK **

   addr      stock   V122+     the LERP: X = [700, 800, 1100]
   0xC65C4     0.0     5.0     Y[0] -- below 700, stock gives ZERO, the car gives MAXIMUM
   0xC65C8     1.5     5.0
   0xC65CC     2.0     5.0
   0xC6598     1.0     5.0     (a second LERP, same treatment)
   0xC659C     1.0     5.0
   0xC65AC    -1.0    -5.0     (its mirror)
   0xC65B0    -1.0    -5.0
```
⇒ **stock rises 0.0 → 1.5 → 2.0 with input; the flying build is a FLAT 5.0 everywhere**, and the
deadband below 700 is **gone**. That is the shape change
[[accord-v80-damper-relay-and-grind1-inert]] was written about — *"the damper became a RELAY …
**restore the RAMP**, don't merely lower k"* — and it is live on the car.
🛑 **HONEST LIMIT: the SHAPE change is pinned; the QUANTITY is NOT.** The input arrives in `r9`
and the only nearby RAM cell (`gp-0x6d94`) has **one writer, zero readers** ⇒ a diagnostic mirror,
not the source. **V178 is justified as a REVERT TO HONDA'S OWN VALUES — the safest class — and NOT
as an understood lever. Do not describe it as one.**

### ✅ V178 BUILT — 7 float32 cells, 28 bytes, base V177
**23/23 assertions · CRC 50/50 · readback byte-identical · all seven cells byte-identical to stock ·
`0xC407E` 511, `0xC40BC` 3000, `0xC40D2` 102, `0xC63A6` 1024 all asserted FROZEN.**
image `2a78d9241b9db4bc…` · rwd `b75d7e5438585a1d…`.
🛑 **NOT fly-first.** V177 is ONE cell and fully attributable; V178 adds seven whose semantics
are unestablished. **Fly V177 first.** V178 is for undoing the whole undocumented V122 delta in one
go, accepting that its result could not be attributed to a single cell.
❌ **`0xC40BC` is deliberately NOT reverted** — 600 would make the Coulomb zero-crossing **5x
sharper**, undoing the one V122 change that helps.

## 🛑 **RETRACTION: THE COULOMB TERM IS NOT A RELAY. V122 WIDENED THE RAMP BY THE SAME 5x.**
I claimed `0xC40D2` at 10x Honda makes a **relay** injecting a **1.99x|model| STEP** at every velocity
reversal, ~16 times a second. **Decompiling `FUN_0003b8f6` shows that is WRONG.** The term is a
**SATURATED RAMP**, not a sign function:
```
   iVar20   = frame_conv * motor_rate * 12
   fVar13   = clamp( iVar20 / cal[0xC40BC], +-1 )         <- a RAMP, saturating at cal/12 counts
   friction = fVar13 * ( |model|*K1/1024 + K0/1024 )       K1 = 0xC40D2, K0 = 0xC4080
```
**And V122 raised the ramp width by exactly the same factor it raised K1:**
```
   config            K1     ramp width      saturated amp        SLOPE through zero
   Honda            102    +-50 counts    0.0996 x |model|        0.00199 / count
   FLYING (V122)   1020   +-250 counts    0.996  x |model|        0.00398 / count
   V177 (built)     102   +-250 counts    0.0996 x |model|        0.000398 / count
```
⇒ **there is no step** — the transition spans ±250 rate counts. ⊕ And **`K0` = 0 (VIRGIN)**, so
friction → 0 as |model| → 0, which removes the small-signal step entirely. **My "V80 relay in another
lane" framing was overstated and is withdrawn.**

### ✅ WHAT SURVIVES — AND V177 IS STILL THE RIGHT BUILD, FOR A DIFFERENT REASON
- the **saturated amplitude is genuinely 10x Honda's**, and
- the **slope through zero is 2x Honda's**
⇒ a real, oversized, velocity-dependent term sitting in the assist path, never tested above 204.
✅ **V177 as built is the GENTLEST of the three configurations**: Honda's amplitude at **one fifth of
Honda's slope**, because it reverts K1 while leaving V122's wider ramp in place. For a symptom driven
by rapid assist changes near velocity reversals, gentler is the right direction — so the build stands
and stays fly-first; only my stated mechanism was wrong.
🛑 **DO NOT also revert `0xC40BC` to 600.** That would make the zero crossing **5x sharper** and
undo the one mitigation V122 got right. It is asserted untouched in V177.
➕ **STILL OPEN: `0xC40DC` (accel EMA alpha), which V122 moved 22 → 8** — a slower filter on the
acceleration feeding `gp-0x6b26`. That is a **PHASE** change on the inertia term; direction not
established. Deliberately excluded from V177 to keep it single-cell.
⊕ **METHOD NOTE, worth keeping**: I found the oversized cell by re-reading the kit's own non-stock
delta, then **immediately overstated its mechanism from the cell value alone**. The decompile settled
it in one call. **Read the code before naming the mechanism** — the value tells you a cell moved, not
what moving it does.

## 🛑🛑 **WE HAVE BEEN DRIVING A RELAY AT 10x HONDA: `0xC40D2` K1 — V177 REVERTS IT, AND IS THE NEW FLY-FIRST**
**Found by re-reading the kit's own non-stock delta, not by new tracing.** `0xC40D2` is K1, the gain on
the modelled Coulomb friction in the plant model (`FUN_0003b8f6`):
```
   friction = |model| * sign(polarity * gp-0x6abc) * K1 / 1024        gp-0x6abc = MOTOR RATE
   => it is a SIGN FUNCTION of velocity, so every reversal steps it by  2*|model|*K1/1024

     Honda   K1 =  102  ->  step = 0.199 x |model|
     V89     K1 =  204  ->  step = 0.398 x |model|     (flew; measured "delivered, but small")
     V122+   K1 = 1020  ->  step = 1.992 x |model|     <== ON EVERY BUILD SINCE V122

   read from the images:  stock/V81/V87/V88 = 102 | V89..V108 = 204 | V122..V176 = 1020
```
🛑 **V89 raised it to 204 and its own docstring PRE-REGISTERED the risk**, which the polarity memory
records verbatim: *"Coulomb friction flips sign at every reversal, so larger K1 = a larger **STEP at
each reversal** — **notchiness on turn-in**, not steady drag. Transient, **unmeasured**."*
**V122 then took it to 1020 — 5x the value that warning was written about — and it has still never
been tested.** At an 8 Hz oscillation the motor rate reverses **~16 times a second**, so a step of
**~2x|model|** is injected 16 times a second, **synchronised to the mode**.
⊕ **This is V80's failure mode in a different lane.** V80 turned the base-assist damper into a relay
and produced *"the worst grinding ever"*. A relay's describing function **does not shrink with
amplitude**, which is exactly how it sustains a mode that linear analysis says should be damped — and
why none of my linear transfer-function work would ever have found it.

### ✅ V177 BUILT — ONE CELL, 2 BYTES, AND IT IS THE MOST ATTRIBUTABLE BUILD OF THE SESSION
Base **V175**. `0xC40D2` **1020 -> 102**, Honda's own value **read from the stock image, not typed**.
**21/21 assertions · 2 payload bytes · CRC 50/50 · readback byte-identical · hard-fault interlock
`0xC407E` frozen at 511 · `0xC63A6` frozen · both prior reverts and all four section coefficients
asserted CARRIED.** image `fc93255645014a0f…` · rwd `86cd9394c0f426fe…` · builder
`analysis-2020accord/builds/v108_plus/build_v177_tva.py`.

### ✅ IT MAKES THE DRIVE **MORE** INTERPRETABLE, NOT LESS — TWO INDEPENDENT SIGNATURES
`0xC40D2` is a **bare `tp` scalar** ⇒ by RULE 7 it is **live in MANUAL and ENGAGED alike**. The
inertia revert is mode-26/27 only. So one drive separates them:
```
   ratchet falls in BOTH engaged and manual, ratio ~unchanged  -> K1's RELAY was carrying it   (V177)
   ratchet falls in ENGAGED only, ratio falls                  -> the inertia dose             (V175)
   ratchet falls, ratio unchanged, manual unchanged            -> the assist-section poles     (V173)
   nothing moves                                               -> all three accounts fail together
```
⚠ **THE FEEL COST, stated plainly: steady effort gets slightly HEAVIER.** The verified chain is
*more modelled friction -> more assist -> lighter*, so undoing 10x removes some of the lightness V89
was chasing. **That is the trade: a little steady weight, against removing a 1.99x|model| step that
fires at every velocity reversal.** The operator has named eliminating the ratcheting/stuttering as
the priority five times, so that is the right side to err on — but he should be told before driving.
🛑 **FLIGHT ORDER: V177 supersedes V175 as fly-first.** It *contains* V175 and adds a one-cell
revert to a Honda value with the strongest mechanism-to-symptom match in the session.
➕ **OPEN, deliberately not folded in**: `0xC40DC` (the acceleration EMA alpha) which V122 also moved
**22 -> 8**. That changes the inertia term's **phase** rather than its size, its direction is not
established, and including it would have cost V177's single-cell attribution.

## ❌ **THE FOC IS CLOSED TOO — THE WHOLE CHAIN IS NOW ENUMERATED END TO END**
The last untouched territory was the FOC / current loop. **It cannot hold an 8 Hz damping lever**, and
the kit's own golden model already says so in its **[VERIFIED]** notes
(`analysis-2020accord/model/eps_chain_delivery.py`, SECTION 9):
- *"the FOC/PWM ISRs (EIIC 0x600 / 0x970) run asynchronously and **far faster** than this
  steering-task tick"*
- *"q-current reference **tracks** the merged command (torque ~ Iq), gated by FOC enable/fault"* — a
  **PI current regulator + SVPWM**, not a shaper.
⇒ the FOC **delivers** whatever `gp-0x6b98` asks for; it contains **no torque-command shaping**, and
its bandwidth is orders of magnitude above the ~8 Hz mechanical mode. **A resonance at 8 Hz is damped
by the torque COMMAND, not by the current controller.** ✅ Physics argument and the model's own
verified description agree ⇒ **closed, and NOT worth the motor-stability risk of editing.**

### 🛑 THE COMPLETE MAP — EVERY STAGE, CAN INTAKE TO MOTOR PWM
```
   stage                                    status
   CAN intake / torque voter                prior sessions
   base assist, boost index                 prior sessions
   rate lanes r24 / r26                     FALSIFIED (V62-V73 arc)
   engage SM / arbitration                  prior sessions
   assist section biquad 0xC60A8..B4        *** THE LEVER *** -> V173 / V174 / V176
   six-term Path-2 sum (w[0]..w[5])         CLOSED -- only w[3] is omega-weighted; w[3] HELD
   gp-0x6b26 inertia lane, 0xCBE74 Y rows   *** THE LEVER *** -> V175 / V176 (revert to Honda)
   residual LERP + its scales + its floors  CLOSED (not a cal / unity / inert+unreachable)
   Honda's 55.23 Hz notch (C_B0)            CLOSED -- spent at V105, refused at 6-9 Hz on phase
   governor -> comp-add -> gp-0x6acc        prior sessions
   shaper gp-0x6acc -> gp-0x6b08            CLOSED -- mode 0, a PURE PASS-THROUGH
   integrator gp-0x6b08 -> gp-0x6b98        CLOSED -- hardcoded shifts; limit only; V41 falsified
   FOC current loop / SVPWM / motor PWM     CLOSED -- tracks the command, far faster than 8 Hz
```
⇒ **The firmware search is COMPLETE.** Two lever families were found, and **both are already built**:
the **assist-section poles** and the **engaged apparent-inertia revert**. Everything else in the chain
is enumerated and closed. **The only unspent cell is `0xC63A6` (w[3]), deliberately held as the fine
adjustment after a drive result.**
🛑 **What remains is not analysis. It is one 15-second engaged creep pass.**

## ✅ **V176 BUILT — BOTH LEVERS AT THE STRONGER DOSE. THE FOUR-BUILD CHOICE IS NOW COMPLETE.**
The operator has stated the priority four times: **eliminate the grinding and the ratcheting.** V176 is
simply **V175 with V174's pole** — the inertia revert *and* the stronger pole in one image, the
maximum-attenuation build still inside the kit's own lag guardrail.
```
   build   poles          engaged inertia   ratchet@8.64   grind@21   lag@1Hz    note
   flying  0.7966 pair    3.0x Honda           0.9789        0.8659    +2.1 ms
   V173    0.970/0.475    3.0x Honda           0.4761        0.1894   +29.1 ms
   V175    0.970/0.475    HONDA'S OWN          0.4761        0.1894   +29.1 ms   <- FLY FIRST
   V174    0.980/0.475    3.0x Honda           0.3393        0.1275   +42.8 ms
   V176    0.980/0.475    HONDA'S OWN          0.3393        0.1275   +42.8 ms   <- strongest
```
➕ **V176's section response is IDENTICAL to V174's** — the inertia revert is a different mechanism in
a different lane and does not touch the biquad. What V176 adds over V174 is removal of the 3.0x engaged
apparent-inertia dose; what it adds over V175 is the stronger pole.
✅ **28/28 assertions · 12 payload bytes · CRC 50/50 · readback byte-identical · base V175 ·
`C_B0` untouched · GATE 2 max |H| = 0.9880.** image `bba4cd5a92c5186f…` · rwd `7beac7510411c7ec…` ·
builder `analysis-2020accord/builds/v108_plus/build_v176_tva.py`.
⚠ **THE HONEST TRADE: +42.8 ms of group delay at 1 Hz vs V175's +29.1.** The operator feels that as
**steering weight**, and he has said explicitly that apparent mass and friction must **not** be the
price of fixing the ratcheting. ⇒ **V175 stays fly-first; V176 is his choice if he wants the
strongest attack and will judge the lag on the same drive.** The card's staging and endpoint power
analysis apply unchanged to both, because the ENGAGED-vs-MANUAL discriminator belongs to the inertia
revert, which both carry.
🛑 **What V176 deliberately does NOT spend, asserted frozen in the builder:** `0xC63A6` (w[3])
stays 1024 — it multiplies the same quantity the revert already cut, so stacking it would push the
product **below Honda's own value** on a nine-link sign chain with no new information; it is the fine
adjustment **after** a drive, not a stacking opportunity. `p_slow` stops at 0.980, the last point
below the **do-not-pass-0.985-without-a-lag-verdict** guardrail. And nothing in the FOC.

## ❌ **THE DELIVERY PATH HAS NO DAMPING LEVER EITHER — THE SHAPER IS A PURE PASS-THROUGH**
Followed the mapped bridge to the motor side, where the record says the resonance actually lives
([[accord-ratchet-is-a-lightly-damped-resonance]]). **Both stages are closed.**

### ❌ THE "SHAPER" (`gp-0x6acc` → `gp-0x6b08`) IS INERT — `FUN_00042af8` @0x43206, ONE writer
```
   gate  = (|gp-0x6acc| <= 8192)          HARDCODED store-zero, not a cal
   mode  = cal[0xC64C8]
     mode 1 -> gp-0x6b08 = cal[0xC61D4]                      (a constant)
     mode 2 -> gp-0x6b08 = clamp(cal[0xC61D4] + gated, +-12288)
     else   -> gp-0x6b08 = gated                             (pass-through)

   0xC64C8 mode    = 0     VIRGIN on stock/V122/V158/V173/V175
   0xC61D4 offset  = 0     VIRGIN
```
⇒ **LIVE MODE IS 0 with a zero offset ⇒ the stage is a PURE PASS-THROUGH. There is nothing to
tune.** Its only structure is a hardcoded ±8192 store-zero gate.

### ❌ THE INTEGRATOR (`gp-0x6b08` → `gp-0x6b98`) HAS NO TUNABLE GAIN
Accumulator at `gp-0x3570`, saturated against `cal[0xC61DC] << 15` and shifted `>>15` on output.
**Every gain in the stage is a hardcoded shift** — the only cals are an **anti-windup LIMIT**
(`0xC61DC`) and a post gain feeding a monitor cell (`0xC61DA` = 1092).
⇒ an integrator limit governs **large-signal windup, not small-signal damping** ⇒ lowering it clips
authority without touching the resonance. **Not a damping lever.**
⊕ And this is the region whose **motor-rate cap V41 already FALSIFIED** (V40 bricked, V41 booted
clean and killed the hypothesis) — so it is also not new ground.

### 🛑 WHAT THIS MEANS FOR THE SEARCH
Both sides of the chain are now enumerated and closed:
```
   ASSIST / OBSERVER side   six-term sum (only w[3] selective, HELD) - notch - residual LERP   ALL CLOSED
   DELIVERY / MOTOR side    shaper (pass-through) - integrator (no gain, limit only)           ALL CLOSED
```
⇒ **the only untouched territory left is the FOC / current loop itself.** That is genuinely
different ground, but it is also the one place where a mistake is a **motor stability** problem rather
than a feel problem, and the kit has never edited there. **I will not cut anything in the FOC without
saying first exactly what it could break.**

## ❌❌ **THE ENTIRE AMPLITUDE-SELECTIVITY LEAD IS CLOSED — ALL THREE BRANCHES, DOUBLY**
The last surviving branch was the small-signal Y floors. **They are dead twice over**, read from the
image with the tp off-by-0x1000 guarded (tp = 0xBF000 ⇒ tp+0x713e is **0xC613E**, not 0xC713E):
```
   addr      what                            stock/V122/V158/V173/V175
   0xC613E   X threshold A (arms floor A)    15000  (VIRGIN)
   0xC6140   X threshold B (arms floor B)    15000  (VIRGIN)
   0xC617A   Y FLOOR A                           0  (VIRGIN)
   0xC617C   Y FLOOR B                           0  (VIRGIN)
   0xC62D8   arm gate on gp-0x6a64            3840  (VIRGIN)
   0xC6178   per-knot output clamp            5274  (VIRGIN)
```
1. **Both floors are ZERO** ⇒ max(Y, 0) is a **no-op** for non-negative Y.
2. **Both thresholds are 15000 = 183 % of the ±8192 residual clamp** (0xC6200) ⇒ the residual is
   **hard-clamped below them and X can NEVER reach them** ⇒ the floors **cannot arm**.
**FULL CLOSURE of the lead, for the record so nobody re-opens it:**
   branch                what killed it
   the 9-knot table      NOT a calibration -- FUN_000389ec rebuilds it every cycle
   the scale factors     zero gp-relative writers -> unity; or, if coded, a BROADBAND rescale
   the Y floors          value 0 AND thresholds unreachable behind the +-8192 clamp
⇒ **there is no amplitude-selective lever in the assist-residual path.**

### ➕ WHERE THIS POINTS INSTEAD — THE DELIVERY PATH, WHICH I HAVE NOT TOUCHED
🛑 The record says the ratchet is a lightly-damped resonance that is **MOTOR/RACK-SIDE**
([[accord-ratchet-is-a-lightly-damped-resonance]]), yet this entire session has worked in the
**assist/observer** path. The bridge is already mapped
([[accord-aggregator-reaches-motor-via-gp6acc-bridge]]):
   gp-0x6b94 -> governor -> gp-0x6ace -> comp-add -> gp-0x6acc -> SHAPER -> gp-0x6b08
             -> INTEGRATOR -> gp-0x6b98 -> FOC
**The SHAPER and the INTEGRATOR sit between the aggregator and the motor, downstream of everything
examined so far, and on the side the resonance actually lives.** That is the next territory.
⚠ It is also nearer the current loop, so GATE 2 there is a **stability** question, not a feel one.

## ✅ **GATE 1 RE-VERIFIED AFTER FINDING TWO HOLES IN MY OWN SCANNER — AND THE SCALE BRANCH IS CLOSED**
🛑 **MY gp-RELATIVE SCANNER HAD TWO HOLES, AND THE KIT'S OWN MEMORY WARNED ABOUT ONE OF THEM.**
Chasing `gp-0x6982`/`gp-0x6984` — which `FUN_000389ec` demonstrably reads — my scan returned **zero
sites in BOTH encodings**. Ghidra settled it:
```
   00038bc6  ld.hu  -0x6984, gp, r7    bytes e4 3f 7d 96   -> hw2 = 0x967D, not 0x967C
   00038bec  ld.hu  -0x6982, gp, r16   bytes e4 87 7f 96   -> hw2 = 0x967F, not 0x967E
```
1. **`hw2 = (disp | 1)`** for these load forms — exactly the recorded trap in
   [[accord-v850-scan-traps-formatv-and-storezero]]. I scanned for the even value and found nothing.
2. **My opcode whitelist omitted `ld.hu` (0x3F)** entirely.
⚠ **Either hole alone manufactures a FALSE NULL**, and a false null is how this kit gets wrong
answers. **Re-scanned with NO opcode whitelist and hw2 ∈ {D, D|1}.**

### ✅ THE LOAD-BEARING RESULT SURVIVES
```
   gp-0x6b26  (INERTIA -- GATE 1 for V175 rests on it)   1 WRITER  0x36CF0 st.h   4 readers
   gp-0x6bd0 w[0] 3 writers   gp-0x6bbe w[1] 3   gp-0x6b46 w[2] 1   gp-0x6b4e w[4] 1   gp-0x6b4c w[5] 3
```
⇒ **identical to the earlier counts** ⇒ **V175's mechanism claim and the six-lane classification both
stand under the stricter method.** ⚠ Still blind to **register-indirect** stores by construction —
that limitation is unchanged and is stated, not solved.

### ❌ THE SCALE-FACTOR BRANCH OF THE LERP LEAD IS CLOSED
`gp-0x6982`/`gp-0x6984` have **ZERO gp-relative writers** and exactly two readers each, both inside
the LERP builder. And `FUN_0003897a` — which I had called an *adaptation* — is nothing of the kind:
```
   FUN_0003897a(target, state, lo, hi, step_fast, step_slow)
     state inside [lo,hi] -> state = clamp(target, lo, hi)          (direct snap)
     state <  target      -> state += step   (step_slow if state >= hi)
     state >  target      -> state -= step   (step_slow if state <= lo)
```
🛑 **RETRACTION: I warned this was "a lever inside an adaptation loop" that could "wind up or
chatter". IT IS A RANGE-CHECK + CLAMP + TWO-RATE SLEW LIMITER** — deterministic, single state, bounded
by construction, no integrator and no convergence question. **That warning was overcautious and is
withdrawn.**
⇒ **But the branch is dead anyway, both ways**: if nothing writes those cells they are **constant**,
the validity test `(x − 0xcc) < 0x735` fails and both scales default to **0x400 = unity** ⇒ the
bounding cals (`0xC6390`/`92`/`9A`/`9C`, `0xC6394`/`96`/`98`/`9E`) are **INERT**. If instead a
register-indirect coding write does move them, then editing their bounds **rescales the whole LERP
globally** — a **broadband** gain change, the same class as V173's poles and strictly worse than it.
**Neither case is amplitude-selective.**
➕ **What survives of the lead**: only the small-signal **floors** `0xC617A`/`0xC617C` and their
thresholds `0xC613E`/`0xC6140`. That is now the sole amplitude-selective candidate in the kit, and it
still needs its knot-index gating traced before it is a lever rather than a guess.

## ❌ **COVARIATE ADJUSTMENT DOES NOT RESCUE THE ONE-PASS RATCHET ENDPOINT — THE 2-PASS ASK STANDS**
I tried to buy statistical power **for free** rather than ask for more driving, since the record says
the ratchet’s axis is WHEEL RATE (1.16x at 2 °/s → 3.94x at 100 °/s) so much of the window-to-window
spread should be operating point, not noise. **It does not work.**
```
   adjustment (LEAVE-ONE-OUT residual, not in-sample)   log10 sd   detect@1 pass
   none                                                  0.3317        4.47x
   log|wheel rate|                                       0.3106        4.06x   <- controlled
   log|command|                                          0.2990        3.85x   <- NOT controlled
   log|wheel rate| + log speed + log|command|            0.3324        4.48x   <- WORSE
```
🛑 **V175 predicts a 3.85x cut — so even the best adjustment puts the effect EXACTLY ON the
detection threshold (~50 % power). Not good enough. Keep the 2-pass ask.**
✅ **Permutation control passes for wheel rate** (real 0.3106 vs shuffled p5 0.3320) ⇒ the gain is
real, just small. ⚠ **The `log|command|` figure is UNCONTROLLED** — its permutation null was not run,
so it is not usable and the honest best is the wheel-rate number, 4.06x.
⊕ **Adding all three covariates made it WORSE** (0.3324 vs 0.3317 raw) — overfitting at n=27, caught
by leave-one-out. **In-sample R² would have flattered this badly**; do not use it here.
⇒ **The instrument is near its limit and more covariates will not help.** Buying power on this
endpoint means EXPOSURE, not cleverness — which is exactly why the card stages it behind a win.

## ✅ **EVERY DRIVE-CARD ENDPOINT IS NOW POWER-CHECKED — AND THE LKAS CLAIM WAS UNSUPPORTABLE**
Against 27 real 15 s engaged creep windows, comparing ONE new window to the historical distribution:
```
   endpoint                 log10 sd   detect@1 pass   V175 predicts    margin   verdict
   GRIND 15-25 Hz             0.396        5.96x         0.058x          2.91x   ANSWERABLE
   lane-change 26-31 Hz       0.158        2.04x         0.029x         16.97x   ANSWERABLE
   RATCHET 6.5-11 Hz          0.332        4.47x         0.260x          0.86x   needs 2 passes
   LKAS band 0.5-3 Hz         0.654       19.16x         0.846x          0.06x   needs 54 passes
```
🛑 **RETRACTION on the card: I claimed the drive would show LKAS authority unchanged. IT CANNOT.**
One pass bounds an LKAS-band change only to **19.2x**, so a measured null there is worthless and must
never be reported as evidence of no change. **That authority is intact is an ANALYTIC claim** from the
section transfer function (−0.05 to −1.42 dB over 0.5–3 Hz); **the operator's own impression is the
better instrument** and is now what the card asks for.
✅ **The good news is structural**: the build's LARGEST predicted effect (grind, a 17x cut) is also
the **best-powered endpoint on the card**, margin 2.9x. ⇒ **if the grinding does not measurably fall
on one pass, the pole-retune account is in trouble** — a real, pre-registered failure mode.
⚠ The ratchet's *amplitude-change* endpoint needs **2** passes (margin 0.86x). The ratchet's
**presence/absence** endpoint does not — it is an ~8x move and one window resolves it. **Keep those
two questions separate**: "is it gone" is answerable now; "by how much did the band fall" is not.

## ⚠ **POWER CHECK BEFORE THE DRIVE: THE V175 CARD WAS UNDERPOWERED FOR ATTRIBUTION — NOW STAGED**
**Caught before the drive rather than after, which is the whole point of the design law.** The card
asked for one 15 s engaged pass and one 15 s LKAS-off pass and attributed the result via the
engaged/manual ratio. Resampling real 15 s creep windows out of the corpus and scoring them exactly as
the card says:
```
   engaged 15 s window   n=27   p50 214.3   log10 sd 0.332
   manual  15 s window   n=22   p50  17.2   log10 sd 0.270
   single-pair RATIO            p50  10.5   95 % band [1.33, 56.49]   log10 sd 0.418
   => ONE pair resolves only a change LARGER THAN 6.6x
      2 pairs 3.80x  ·  3 pairs 2.97x  ·  4 pairs 2.57x  ·  6 pairs 2.16x
```
🛑 **V175's predicted ratio move is well under 6.6x** (a 3.0x dose on one of six terms in the
sum) ⇒ **a single pair could not have attributed the result.**
✅ **The PRIMARY question is unaffected and stays a single pass**: the ratchet endpoint is
**presence/absence**, an ~8x move, and one 15 s engaged window resolves it 11/11 on the corpus.
✅ **The card is now STAGED**: Stage 1 is one engaged pass and stop — which is exactly the operator's
own rule (*"if I observe micro-ratcheting or grinding, I am generally going to stop instantly"*).
**Stage 2 (three alternating engaged / LKAS-off passes, ~90 s total) is driven ONLY if Stage 1 shows a
win**, because attribution only matters when there is something to attribute.
⊕ **Generalises**: any endpoint that is a RATIO of two separately-driven conditions costs roughly
**4x the exposure** of a presence/absence endpoint. Stage ratio endpoints behind the presence check.

## ❌ **THE AMPLITUDE-SELECTIVITY LEAD IS CLOSED IN ITS ORIGINAL FORM — THE RESIDUAL LERP IS NOT A CALIBRATION**
🛑 **I proposed reshaping the residual LERP's 9 knots as a static cal edit. THAT TABLE DOES NOT
EXIST IN FLASH.** `FUN_000389ec` **rebuilds it every cycle** into a scratch buffer and publishes it:
```
   scratch:  X at gp-0x373c ... , Y at gp-0x3714 ...
   X[i] = ((int)raw << 10) / iVar32        iVar32 = FUN_0003897a(gp-0x6982, clamped by cals)
   Y[i] = (raw * iVar33) >> 10             iVar33 = FUN_0003897a(gp-0x6984, clamped by cals)
   then published:  gp-0x64b8.. <- gp-0x373c..     gp-0x641c.. <- gp-0x3714..
```
=> the knots are **computed from two RUNTIME ADAPTATION STATES** (`gp-0x6982`, `gp-0x6984`) every
cycle. **There is no static table to edit**, and my earlier flash search was hunting something that
does not exist. ➕ It also explains the measured **`f'` compression** (p50 2.174 hands-off vs 0.346
hands-ON) — that is not a fixed curve being traversed at different points, it is **the curve itself
being rescaled** by the adaptation.

### ⚠ THE SALVAGEABLE SUB-LEAD, AND WHY I AM NOT SPENDING IT NOW
The **scale factors are bounded by static cals**, and those are editable:
```
   tp+0x7390 / 0x7392  = 0xC6390 / 0xC6392   upper clamps on the two adaptation inputs
   tp+0x739a / 0x739c  = 0xC639A / 0xC639C   lower clamps
   tp+0x717a / 0x717c  = 0xC617A / 0xC617C   small-signal FLOORS applied to Y per knot
   tp+0x713e / 0x7140  = 0xC613E / 0xC6140   the thresholds those floors are gated on
   tp+0x7178           = 0xC6178             per-knot output clamp
```
Since `f' ∝ iVar33 · iVar32 / 1024²`, bounding the adaptation **does** move small-signal gain, and
`0xC617A`/`0xC617C` look like a direct small-signal floor — the amplitude-selective handle in cal form.
🛑 **But this is a lever INSIDE AN ADAPTATION LOOP, which is a new and materially riskier class
than anything the kit has flown.** Before any dose it needs: the exact knot-index gating of the floors
traced (the logic is threshold-and-index dependent, not a simple clamp); `FUN_0003897a` decompiled to
learn what the adaptation actually converges to; **GATE 1** on `gp-0x6982`/`gp-0x6984`; and **GATE 2 in
magnitude AND phase against an ADAPTIVE plant**, which the kit has never had to do. ⚠ **A wrongly
bounded adaptation can wind up or chatter** — the failure mode would look like new ratcheting.
=> **That is a full session's work and it must NOT be started before V175 flies**, because if V175's
result falsifies the polarity chain, this entire path is falsified with it.

## ✅ **THE SIX-TERM SUM IS NOW FULLY CLASSIFIED — `gp-0x6b26` IS ITS ONLY FREQUENCY-SELECTIVE LANE**
**A CLOSING result, both positive and negative.** Every lane of `FUN_00038148`'s Path-2 sum has been
traced to its writer and classified by differentiation order. **No second ω-weighted lever exists in
this structure** — so the search over it is closed and no future session need re-open it.
```
   w    cell      signal      writer            what it is                      order
   w[0] 0xC63A0   gp-0x6bd0   0x34730 (3 st)    base-assist damper (FactorC x FactorE)   ~w^1 BUT
                                                zero on 95.91% engaged / 100% of micro
   w[1] 0xC63A2   gp-0x6bbe   0x3508C (3 st)    viscous + DC PEDESTAL (~90 ct/(rad/s))   w^1 + DC
   w[2] 0xC63A4   gp-0x6b46   0x3681A (1 st)    EMA'd, deadbanded torque-ERROR tracker   LAG (w^-1)
   w[3] 0xC63A6   gp-0x6b26   0x36CF0 (1 st)    ** K * ACCELERATION **                   ** w^2 **
   w[4] 0xC63A8   gp-0x6b4e   0x27466 (1 st)    sum over the 11 aggregator slots         w^0
   w[5] 0xC63AA   gp-0x6b4c   0x276F0 (3 st)    11-slot sum + frame-converted term       w^0
```
✅ **`gp-0x6b46` is NOT a derivative** — `FUN_00036682` forms
`err = (gp-0x6b48 + conv*(gp-0x4f60*cal>>15)) − gp-0x6b46`, passes it through an **adaptive hysteresis
band** and a down-counter (`gp-0x6a80`), clamps to ±512 and **EMA-filters** it. It is
**self-referential ⇒ a first-order LAG**, and the inventory census already measures its contribution
at **0.0032** — negligible twice over.
✅ **`gp-0x6b4e` and `gp-0x6b4c` are both written by `FUN_00026c80`**, the **11-slot aggregator**
(`while (i < 0xb)`), as **sums over the slots** ⇒ ω⁰, no frequency shaping.
⇒ **`gp-0x6b26` (w[3]) is the UNIQUE ω-weighted lane**, which is what makes it the only handle here
that can attack 8 Hz without touching 1 Hz.

### ❌ AND THE ONE OTHER CANDIDATE IS RULED OUT BY THE OPERATOR'S OWN CONSTRAINT
`gp-0x6bbe` (w[1]) is genuinely **viscous** — raising w[1] would add damping ∝ ω, 8x stronger at 8 Hz
than at 1 Hz. **But it carries a DC PEDESTAL** ([[accord-gp6bbe-is-viscous-plus-dc-pedestal]]: p50
**73.6 ct flat across 0–6 °/s**), so raising it **amplifies static friction at EVERY frequency,
including zero.** That is exactly the trade the operator ruled out — *"low apparent steering mass and
friction to LKAS AND no ratcheting"*. 🛑 **Do not propose raising `0xC63A2` as a damping lever.**

➕ **`0xC63AC`** (the EMA alpha on the whole sum, = 102 ⇒ corner ≈ 16.9 Hz at 1 kHz) is a **shared
low-pass on all six lanes**. Lowering it would attenuate 8 Hz content in every term — but it is a
**broadband** lever with the same lag cost as V173's poles, so it is **strictly worse than V173** and
is **not** a new direction. Recorded so it is not re-proposed as one.

🛑 **CONSEQUENCE FOR THE FLIGHT ORDER: nothing changes.** `0xC63A6` stays **held** as the
pre-registered fine adjustment *after* V175's drive — spending it now would confound the one
measurement that can attribute the effect.

## 🛑🛑 **THE ENGAGED RATCHET MAY BE OURS: WE AMPLIFY A DESTABILISING INERTIA TERM 3-8x, ENGAGED-ONLY — V175 REVERTS IT**
**A new mechanism, traced end to end this session, decompile-first.** It is the first account that
explains **why the ratchet is ENGAGED-amplified ~15x** in terms of a cell we ourselves moved.

### ✅ THE TRACE [EVIDENCE — both ends confirmed in Ghidra + a raw LE byte scan]
`FUN_00036c12` is the **sole writer** of `gp-0x6b26` (one `st.h -0x6b26[gp]` at `0x36CF0`; the other
five disp16 sites decode as `ld.h`, opcode 0x39 vs 0x3B):
```
   gp-0x6b26 = clamp( ((gp-0x6c2c * validgate) * LERP_0xCBE74[mode](gp-0x6a5e) >> 6) * 0x111 >> 0x12,
                      +- cal[0xC407E] )
```
- `gp-0x6c2c` is the **ACCELERATION** — `FUN_00041464` @`0x41602` `sub r7,r9` is a FIRST DIFFERENCE of
  the EMA-filtered resolver rate, then ×32, clamped, EMA'd, `>>9`.
- **the acceleration enters LINEARLY**; the LERP is indexed by `gp-0x6a5e`, a **scheduling** variable,
  not by α ⇒ `gp-0x6b26 = K(mode, sched) · α`, a pure apparent-inertia term.
- ⇒ **its loop contribution scales as ω²: 66.7x more at 8.17 Hz than at 1 Hz.**
  🛑 **This is the frequency selectivity the kit concluded it did not have** — and it is
  **STRUCTURAL, from differentiation order, not from a filter.** It costs NO phase lag anywhere.
  (It does not contradict [[accord-factord-is-the-angle-error-lever]], which refuted a *filter*-based
  1/ω selectivity. This is a different thing.)

### ✅ THE GATE CANNOT CLOSE
`FUN_00038148` admits it into the six-term Path-2 sum with `w[3]` = `tp+0x73a6` = **`0xC63A6`**, gated
on `(gp-0x6b26 + 0x400) < 0x801` i.e. `|x| <= 1024` (a **store-zero**, not a clamp). But the writer
clamps to **±`0xC407E` = 511** on stock, V173 and V174 alike ⇒ **511 < 1024, the gate is open EVERY
frame** and `w[3]` is an unconditional multiplier. [EVIDENCE, read from all three images.]

### 🛑 THE SIGN — IT IS POSITIVE ACCELERATION FEEDBACK, I.E. **NEGATIVE APPARENT INERTIA**
The Y rows are NEGATIVE, so `gp-0x6b26 = −|K|·α`. Through the verified polarity chain
([[accord-friction-polarity-more-friction-is-more-assist]], whose step 4 gives `f' >= 0` EVERYWHERE):
```
   alpha UP -> MODEL DOWN -> res UP -> gp-0x6b70 UP (f'>=0) -> target effort DOWN -> MORE ASSIST
```
⇒ **assist RISES with acceleration** ⇒ lowers effective mass **and lowers the damping ratio of the
resonance**. Amplifying it is the wrong direction — exactly what
[[accord-gp6b26-is-inertia-not-damping]] already said: *"the whole V74/V75/V91/V92 dose direction was
aimed at the wrong physics."*

### 🛑🛑 AND THE FLIGHT BUILD AMPLIFIES IT 3.0x / 3.0x / **8.14x**, ON THE ENGAGED MODES ONLY
```
   0xD7A5C m26 ENGAGED   Honda (-9830,-5734,-1966)  ->  FLOWN (-29490,-17202,-16000)
   0xD7A6C m27 ENGAGED   Honda (-9830,-5734,-1966)  ->  FLOWN (-29490,-17202,-16000)
   0xD6A6C m24 MANUAL    Honda (-9830,-5734,-1966)  ->  UNCHANGED
```
⊕ **The one destabilising ω²-weighted term is amplified 3-8x on exactly the modes where the ratchet
is amplified ~15x, and left alone in manual, where it barely appears.** [BELIEF — a structural match,
not yet a measured cause.]

### 🛑 **RETRACTION — I OVERSTATED THE RELAY HAZARD. IT IS MEASURED AT 0.49 % DUTY.**
I wrote that saturating the ±511 clamp makes this lane V80's relay and that the hazard was
"unexcluded". **Now measured, and that framing was wrong.** Route `77` (`probe_build` = **V90**) carries
`gp-0x6b26` itself on CAN 427 at **Honda's K**, 52,926 engaged frames. `gp-0x6b26` is hard-clamped to
±511, which pins the packer shift to s ∈ {0,1} (s ≥ 3 would imply a max of 1592 — impossible).
At the **tightest** admissible s = 1:
```
   K              saturation duty      p99      (clamp 511)
   Honda 1.0x         0.0000 %         136
   V91   1.5x         0.0094 %         204
   FLOWN 3.0x         0.4875 %         408      <== the current build
```
⇒ **0.49 % is rare tail clipping, NOT a relay.** V80's relay ran at near-unity duty. **The relay
argument is withdrawn and is NOT part of the case for V175.**
⚠ Two further caveats on this measurement: **r78/r79 are NOT comparable to r77** — the 427 packer
scaling changed across V91/V92, so those columns are **not** a dose-response and must not be read as
one. And the extrapolation is a **model**, exact only because `gp-0x6b26 = K·α` is linear *before* the
clamp.

### ✅ WHAT SURVIVES — AND IT IS STILL THE CASE FOR V175
The **linear** amplification is untouched and is the real argument: at the flown dose the term runs
**p99 = 408 against a 511 clamp**, a genuine **3x amplification of a DESTABILISING ω²-weighted term,
engaged-only**. ⊕ And it is **highly intermittent** — p50 ≈ 18 counts, p99 = 408 — i.e. negligible in
steady driving and large **exactly during the fast transients where the ratchet lives**. That is the
signature an acceleration term should have, and it is why the lane is worth reverting even though it
almost never clips.

### ✅ `0xC63A6` IS **UN-STRUCK** — ITS BLOCKING GATE IS CLEARED
It was struck 2026-08-11/12 because Path 2's sign depended on an **unknown LERP slope**, with the
release condition *"re-derive the slope from V96/V97's own instruments."* **That slope is now known:
`f' >= 0` everywhere (structural) and measured p50 2.174 hands-off / 0.346 hands-on**, with the
cross-check `d(gp-0x6b94)/d(gp-0x6b70)` = +0.2529/+0.2565/+0.2617 and a passing positive control.
⇒ **the cell is available.** V175 deliberately does **not** spend it (asserted FROZEN at 1024): a
revert to Honda's own numbers is a lower risk class and carries an on-car saturation measurement.

### ✅ V175 BUILT — 12 BYTES, SUBTRACTIVE, ENGAGED-ONLY
Base **V173**. `0xD7A5C`/`0xD7A6C` → Honda's row, **read from the stock image, never typed**.
**26/26 assertions · 12 payload bytes in 3 runs · CRC 50/50 · readback byte-identical · mode 24
untouched · `0xC407E` and `0xC63A6` asserted frozen · V173's four section coefficients asserted
carried.** image `a4e0dc4254ad8559…` · rwd `5bf63d0ea539fd18…` · builder
`analysis-2020accord/builds/v108_plus/build_v175_tva.py`.
✅ **THE DISCRIMINATOR vs V173's poles is ENGAGED vs MANUAL.** They stack and both attenuate the
ratchet, so amplitude alone cannot attribute — but V173's poles act in **both** modes and this revert
**cannot act in manual**. Ratchet falls *and* the engaged/manual ratio falls ⇒ the inertia dose was
carrying it. Ratio unchanged ⇒ V173's poles did it. Neither moves ⇒ both accounts fail together.
Score with `rlog-tools/score/grind_engaged_vs_manual.py` beside `score_band_excess.py`.
⚠ **It removes drag — creep effort will be lighter than the operator is used to.** Intended, and he
should be told.

## ✅ **V174 BUILT — THE PRE-REGISTERED SECOND POINT ON THE FRONTIER. V173 STILL FLIES FIRST.**
Cut so that the verdict *"better, but the ratcheting is still there"* costs **no build delay**.
🛑 **V174 IS NOT AN ALTERNATIVE TO V173 AND MUST NOT BE FLOWN FIRST.** It is the *expensive* point
on the same curve; flying it first throws away the ability to tell which point the car needed.
```
   ONE knob:  slow pole 0.970 -> 0.980   (C_B0 byte-identical, Honda's 55.23 Hz notch KEPT)
     0xC60A8  C_A8  -1.53719997 -> -1.45500004    raw BFBA3D71
     0xC60AC  C_AC  +0.63462001 -> +0.46549999    raw 3EEE5604
     0xC60B4  C_B4  +0.81730998 -> +0.08808687    raw 3DB466E4   (solved for unity DC)

                 flying    V174    ratio        V173 for comparison
     3.00 Hz     0.9975   0.7288   0.731x        0.8476
     8.64 Hz     0.9789   0.3393   0.347x        0.4761   RATCHET  (2.9x vs V173's 2.1x)
    21.00 Hz     0.8659   0.1275   0.147x        0.1894   GRIND    (6.8x vs V173's 4.6x)
    55.23 Hz     0.000128 0.000009               0.000013 Honda's notch, KEPT and deeper
```
✅ **27/27 assertions · 12 payload bytes · CRC chain 50/50 · readback byte-identical ·
`[0xC5000,0xC5FFC)` untouched.** Base **V158** (`42078806f5582903…`), so it carries V158's damper.
image `c3d6776cc72d4657…` · rwd `5e4ba53db14442cb…` · builder
`analysis-2020accord/builds/v108_plus/build_v174_tva.py`.
✅ **GATE 2 magnitude PASS: max |H| = 0.9880 to Nyquist** ⇒ can only REMOVE loop gain.
✅ **GATE 1 as V173**: `gp-0x6b86` has exactly one consumer outside its producer, no monitor.
⚠ **THE HONEST COST: +42.8 ms of group delay at 1 Hz** (V173 spends +29.1). The operator feels that
as **steering weight**, which is the thing he has explicitly said must not be the price of the fix —
so this build is **his call on a lag verdict**, not a default.
🛑 **DO NOT CUT PAST `p_slow` = 0.985 WITHOUT AN OPERATOR LAG VERDICT IN HAND.** Beyond there the
added lag exceeds anything this kit has ever shipped.
⚠ **The coefficients are RE-DERIVED FROM THE FORMULA inside the builder and asserted against the
pinned raw words** — a 6-dp decimal does not round-trip a float32; see [[feedback-float-spec-must-be-the-formula]].

