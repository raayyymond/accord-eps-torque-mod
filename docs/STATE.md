# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V168 SUPERSEDES V158 AS FLY-FIRST.** V168 *is* V158 plus one byte, so it carries both levers, and the two symptoms score from the SAME 15 s episode in different bands (grind 15-25 Hz, ratchet 5-12 Hz, both in `cs_tq`) — **separated by the INSTRUMENT, not by the build**. Fly V158 alone only to isolate the grind lever on FEEL. Card: `docs/scoring/DRIVE-CARD-V168.md`.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-assist-map-session.md` carries every finding, every retraction and the open-items list with what would close each.
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

## ✅ **100/12 Hz EXCLUDED · THE MODE GENUINELY WANDERS ±0.71 Hz · AND TWO OF MY OWN CLAIMS RETRACTED**
🛑 **RETRACTION 1 — I ran the assist section at FS=100 Hz. IT RUNS AT 1 kHz.** Verified against the
lineage's own three stock response points (notch 55.23 Hz, −1.25 dB @21, −3.01 dB @30, −0.02 dB @3):
FS=1000 reproduces all four, FS=100 reproduces none. **Two claims I made this session die with it:**
- ❌ *"Honda's notch is at 5.53 Hz, a 10x error in the record"* — **WRONG, the record was right.**
  The notch is at **55.226 Hz**. The 10x error was mine.
- ❌ *"V173 cuts the LKAS band up to 6.5x and doubles group delay"* — **WRONG.** At the true rate
  **LKAS 0.5–3 Hz is −0.05 to −1.42 dB — essentially intact.**

### ✅ THE 100/12 = 8.3333 Hz FIRMWARE-CYCLE HYPOTHESIS IS DEAD
Killed by a **synthetic positive control**, not by argument. Inject a *truly fixed* 8.3333 Hz line into
1/f noise with matched segment counts and run the identical estimator:
```
   synthetic FIXED line, SNR 0.5 / 1.0 / 2.0 -> sd 0.0051 / 0.0026 / 0.0011 Hz
   observed, 15 routes                       -> sd 0.7904 Hz     (150x larger)
   within-route split-half sd 0.3535  =>  TRUE route-to-route sd 0.7069 Hz
```
=> the estimator reproduces a fixed frequency to **0.005 Hz**. The spread is **real**, not noise.
**A firmware divider cannot produce a frequency that moves +-9 % between drives.** ✅ Also checked the
image directly: `add 1,rX` paired with `cmp N,rX` gives N=12 only **4** sites vs 22 for N=8 and 13 for
N=10, and the N=12/13/14 hits sit at regular 0x3E strides — **unrolled loop trip counts, not dividers.**

### ⚠ THE WANDER IS ITSELF A DESIGN CONSTRAINT — IT KILLS EVERY NARROW LEVER
🛑 **RETRACTION 3 (same FS=100 root cause): I said a re-centred notch dies because it is too
NARROW for a wandering mode, −0.42 dB worst case. WRONG on both the number and the reason.**
At the true 1 kHz it is relatively far wider and DOES attenuate the wander core — −15.4 dB at −1 sd,
−14.6 dB at +1 sd. **It dies on GATE 2 MAGNITUDE instead, catastrophically.** `C_B4` is pinned by
`C_B4 = (1+C_A8+C_AC)/(2+C_B0)` and `2+C_B0 = 2−2cosθ → 0` as the notch moves toward DC:
```
   notch @ 8.17 Hz, stock poles -> C_B4 = 36.98  (stock 0.8173, x45)
   max |H| absolute = 46.91      GATE 2 needs <= ~1   -> FAILS BY 47x
   GRIND 21 Hz  +16.33 dB (6.5x AMPLIFIED)    Honda's 55 Hz null  +108 dB (10^5 x)
```
⇒ a re-centred notch **amplifies the grind it is meant to help** and destroys Honda's null. This is
exactly the reason V173's own docstring already gives (`C_B4 ~ 1/f²`), reached independently from the
image bytes. ⊕ It is a second, independent argument for what V88 concluded from the wire (*"no notch, no phase lever
exists at 7.79 Hz specifically"*), and it re-confirms the standing lineage rule
🛑 **"THE NOTCH LEVER IS SPENT — do not re-propose a re-centred `0xC60A8` biquad."** V105 flew a
25.5 Hz notch and failed; `docs/review/GATE2-2026-08-20-notch-sign.md` refused re-centring at 6–9 Hz.
=> **the ratchet lever MUST be broadband.** That is exactly what V173's pole move is.

### ✅ V173 RE-PRICED AT THE CORRECT RATE — AND GATE 2 PASSES
```
   band                 V173 / stock          what it means
   LKAS   0.5-3 Hz      -0.05 .. -1.42 dB     authority MAGNITUDE intact
   ratchet 6.5-11 Hz    -4.50 .. -7.97 dB     partial (1.7-2.5x) but robust across the whole wander
   GRIND  15-25 Hz     -10.39 .. -14.70 dB    the primary endpoint, well served
   lane-change 26-31   -15.03 .. -16.51 dB
   COST: group delay  +30.1 ms @0.5 Hz  +29.1 @1  +21.4 @3   (-5.5 deg / -10.8 / -29.2)
```
✅ **GATE 2 (magnitude): PASS, decisively.** `max |H_V173 / H_stock| = 0.999753` over 0.1–499 Hz and
`max |H_V173| = 0.9998` absolute => the section **can only REMOVE loop gain, never add it**, and no new
resonance exists. Same argument class V103 passed on.
⚠ **GATE 2 (phase): a real, bounded cost.** −10.8 deg at 1 Hz and −29.2 deg at 3 Hz is materially more
in-band phase than V103 spent. It is the **mechanism** by which the mode is damped, not a side effect —
but it is the honest price, and the operator feels it as lag, not as lost authority.

### ➕ THE FRONTIER — PRE-REGISTERED NEXT STEP IF V173 IMPROVES BUT DOES NOT CURE
The slow real pole couples attenuation to lag **inseparably** (one real pole, one time constant), at a
strikingly linear rate:
```
   p_slow   corner   ratchet@8.17   grind 15-25   lag@1Hz      ~4.8 ms of 1 Hz lag
   0.9700   4.85 Hz    -5.89 dB      -12.61 dB    +29.1 ms  <== V173
   0.9800   3.22 Hz    -8.77 dB      -16.03 dB    +42.8 ms     buys each extra dB
   0.9850   2.41 Hz   -11.03 dB      -18.49 dB    +54.1 ms     of ratchet attenuation
   0.9900   1.60 Hz   -14.38 dB      -22.00 dB    +69.2 ms
```
=> **If the drive says "better but still there", the next build is `p_slow` 0.970 -> 0.980** (`C_A8`,
`C_AC`, `C_B4` re-solved for unity DC): −2.9 dB more ratchet for +14 ms more lag. **Do not go past
0.985 without an operator lag verdict** — past there the lag is larger than anything the kit has shipped.

## ⚠ **HYPOTHESIS, UNPROVEN: IS THE RATCHET AT EXACTLY 100/12 Hz? — AND THE DRIVE CAN SETTLE IT**
🛑 **Every ratchet frequency I have quoted this session — 7.81, 8.01, 8.20, 8.40, 8.59, 8.79 — is an
exact FFT BIN CENTRE** at 0.1953 Hz spacing. I never resolved the frequency, only which bin it fell
in. That is worth knowing because **100/12 = 8.3333 Hz** sits inside the measured range, and an exact
submultiple of the 100 Hz frame rate would mean a **firmware cycle** rather than a mechanical mode — a
completely different lever.
```
   parabolic peak interpolation on pooled continuous-run PSDs
     nperseg=512   19 routes   mean 8.1682 Hz  sd 0.7027   range 6.78-10.19
     nperseg=1024  12 routes   mean 8.2958 Hz  sd 0.8009   range 7.35-10.42

     100/11 = 9.0909  excluded at 2 SE     100/13 = 7.6923  excluded at 2 SE
     100/12 = 8.3333  consistent -- 0.5 % from the mean at nperseg=1024
```
⚠ **[HYPOTHESIS, NOT EVIDENCE] and two reasons to distrust it:**
1. **I selected the candidate submultiples AFTER seeing the range.** Finding that a mean lands near
   one of three post-hoc candidates is weak, and I have no pre-registration for it.
2. **The per-route scatter (sd 0.80 Hz) is far larger than the interpolation error.** A fixed-frequency
   mode measured at df = 0.098 Hz should not scatter that much, which argues the frequency **genuinely
   varies** route to route — i.e. against an exact submultiple. The alternative reading is that the
   estimator hops between nearby peaks on a noisy median PSD, which would inflate the scatter without
   the frequency moving. **These are not distinguishable at this window length.**

### ✅ WHAT WOULD SETTLE IT — AND THE V173 DRIVE CAN SUPPLY IT FOR FREE
No route in the corpus has **20 s of unbroken engaged creep**, which is why the resolution ceiling is
0.098 Hz. **A single 20-second continuous pass gives df = 0.05 Hz and pins the frequency to ~0.5 %
on that one route** — enough to separate 8.3333 from a nearby mechanical value.
⊕ The drive card already asks for **15 s continuous**. **Stretching one pass to 20 s costs nothing and
adds this test**, which is why it is worth mentioning rather than leaving as a curiosity.
⊕ **If it IS exactly 100/12**: the mechanism is something running on a 12-frame cycle, the lever is
that structure, and V173 would be treating a symptom rather than a cause. **If it is not**: the
mechanical-resonance reading stands and V173's case is unchanged.
🛑 **This changes nothing about the build or the flight order.** V173 attenuates the response
whatever the mode's origin. It is recorded because **the test is nearly free and the answer would
matter a great deal.**

## ⚠ **PRECISION: “COMMAND-DRIVEN” DOES NOT MEAN THE COMMAND CARRIES 8.2 Hz — AND THE DIFFERENCE
MATTERS**
I wrote *“THE RATCHET IS DRIVEN BY THE COMMAND”*. Read carelessly that says the command **contains**
8.2 Hz energy and injects it, which would make *“filter the command at 8 Hz”* an obvious lever.
**It would do nothing, because the command has no 8.2 Hz content.**
```
   command channels in the RATCHET band, 19 routes, excess / own slope-matched null
     sc_tq 0.92 · co_tqcan 0.91 · cc_req 0.88      — all BELOW 1.0, i.e. no peak at all
   and the kit's own record: the LKAS lane is a ~1-5 Hz LOW-PASS, so the command CANNOT
   carry 8.2 Hz even in principle.
```
✅ **What the coupling result actually shows**: band-specific coherence between command and `cs_tq`
at 7–10.5 Hz, above a 30–40 Hz control band and above phase-shuffled surrogates (median **+0.115**,
CI **[+0.027, +0.168]**, n=17). **Coherence at a frequency does not require the input to have a peak
there** — broadband command activity moves the wheel, the motion excites a **plant resonance**, and the
response appears at the plant's frequency, not the command's.
⇒ **the correct statement is: the ratchet is a PLANT resonance EXCITED by command activity, and
amplified ~15× by the engaged loop.** “Command-driven” is shorthand for the excitation source, not a
claim about the command's spectrum.

### ✅ WHY THIS PREVENTS A WRONG LEVER
❌ **Do not propose filtering or notching the LKAS command near 8 Hz.** There is nothing there to
remove — all three command channels sit below their nulls in that band, and the LKAS lane already
low-passes at 1–5 Hz. Such a build would be **inert by construction**, and its null would be
uninterpretable rather than informative.
✅ **The lever remains where V173 puts it**: the **response** path, not the excitation. Reducing `|L|`
attenuates the resonance regardless of how broadband the excitation is — which is exactly why V173
works whether the mode is command-excited or self-excited.
⊕ It also explains the **monotone command scaling** (excess 14.0 → 47.8): more command activity means
more broadband excitation reaching a fixed-frequency mode, **not** more energy at 8.2 Hz specifically.

## 🛑🛑🛑 **RETRACTED: THE CAL ASSOCIATION SCAN IS INVALID AS I RAN IT**
I reported *“a blind cal scan finds the grind's lever”* as a headline. **It does not, and the method
itself is unsound.** Three findings, in the order they emerged:

### 1. It is unstable — a two-label change flipped BOTH verdicts
Correcting `r95` (V102→V101) and adding `r77` (V90) reversed everything: **ratchet 0→2 survivors,
grind 1→0**. `0xC40BC` fell from ρ −0.715 to −0.662, below its threshold.

### 2. Leave-one-out confirms the grind hit was noise
```
   RATCHET  0xC4B58  17/17 leave-one-out subsets   0xC4B5E 13/17   others 3,2,1 / 17
   GRIND    0xC40BC   1/17                          <- the "confirmation" was never stable
```

### 3. 🛑 AND THE STABLE RATCHET HITS ARE ARTEFACTS — THE REGION IS NOT u16 CALS
`0xC4B58` looked convincing at ρ +0.783 and 17/17. But its values across builds are **1443, 1542,
12803, 14022, 14212, 60140, 60141** — jumping with no ordering, which is the signature of a
**mantissa half, not a scalar.** Reading the region as float32 gives absurdities at every alignment
(**−1.43e+26**, denormals like **1.76e−38**), and the raw bytes are plainly packed/structured:
```
   0xC4B50 on V122:  00 3A C4 3A 84 37 ED EA C6 36 BF 00 07 31 44 37 EC EA 24 37 1E 95 60 32
```
⇒ **`0xC4B58` is not a calibration scalar, so correlating it against anything is meaningless.** The
“stable association” is an artefact of slicing packed bytes on a 2-byte grid.

### ✅ WHAT THE ROOT CAUSE WAS, AND WHAT SURVIVES
🛑 **The method assumed every 2-byte-aligned pair in the cal region is a u16 scalar. It is not.**
That region holds floats, packed structures and pointer tables, and the scan silently treated all of
them as numbers. **Every result it produced — for both bands — is withdrawn.**
✅ **What SURVIVES, on its own separate evidence**: `0xC40BC` as the grind's lever. That came from the
**knee sweep**, where the cell was read as the actual relay knee, its values are **sensible and ordered
(300 / 600 / 1800 / 3000)**, and its role is **in the decompiled relay arithmetic**. ρ = −0.69,
p 0.039. **The scan neither confirms nor denies it — it simply never had standing to.**
✅ **V173 is untouched.** Its case is structural throughout: the assist map is the largest torque-fed
term, its cap binds, its section was never retuned, and both gates pass.
⊕ **The fix, if this is ever re-run**: restrict candidates to cells **verified as u16 cals** — by the
knot-count header, by a decompiled read site, or by sensible ordered values — rather than every
aligned pair. `analysis-2020accord/verify/check_lever.py --record` already does that validation.

## 🛑🛑 **I OVER-CORRECTED. THE RATCHET TREND IS UNRESOLVED, NOT ESTABLISHED — AND TWO LABELS WERE WRONG**
Searching memory for **operator verdicts** turned up two hard route→build statements that contradict
labels I had *inferred from filenames*:
- 🛑 **`r95` = V101, NOT V102** — *“V101 flew it at 8× (7128) as route `0x95`, 2026-08-19”*. My
  inference came from `r95_v102_prereg.py`, which is a **pre-registration FOR V102 that used route 95
  as its reference** — not a statement that r95 IS V102.
- ✅ **`r77` = V90** — *“V90 flew as route 77”*. I had **excluded** r77 as unattributable, and it is the
  **richest route in the corpus at 97 windows**.

### 🛑 WITH ONLY HARD ATTRIBUTIONS, MY OWN CORRECTION DOES NOT HOLD
```
                             n    RATCHET post-V102      GRIND post-V102
   session start             5    rho -0.14  p 0.787     rho -0.94  p 0.005
   after enlarging (8 inferred) 11 rho -0.60  p 0.052     rho -0.84  p 0.001
   ALL HARD attributions     8    rho -0.40  p 0.320     rho -0.86  p 0.007
```
✅ **[EVIDENCE] the GRIND trend is ROBUST** — ρ −0.76 to −0.86 across every attribution set tried,
significant in all of them. **That claim stands unchanged.**
🛑 **[UNRESOLVED] the RATCHET trend is NOT robust** — ρ swings **−0.14 → −0.60 → −0.40** with the
label set and is **never significant**. ⇒ **I over-corrected.** *“The ratchet is trending down”* was
as over-stated as *“the ratchet has never moved”* was. **The honest statement is that the ratchet's
build trend is UNRESOLVED at every sample size tried**, while the grind's is settled.
⊕ **What does NOT depend on this**: the ratchet is in torque not wheel rate (19/19 routes),
engaged-only (15/15 vs 6/15 marginal), command-driven (CI excludes zero), and **no varied cal tracks
it** under family-wise control. **V173's case is untouched** — it never rested on the trend.
⚠ **The cal scan used these labels too.** Its ratchet result was a **null** (0 of 94 cells survive),
which two label changes cannot create a survivor from; its grind hit (`0xC40BC`) is worth re-checking
if that cell is ever acted on.

### ⭐ AND V101 PRICES THE 8× GAIN, WHICH IS WORTH HAVING
`r95` is the **8×-gain build** (`0xC6CD0` = 7128), and now correctly labelled it is measurable:
```
   V101 (8x gain)   ratchet 193.2   grind 38.7
   all other builds ratchet  34.5   grind 15.6     (medians)
   => 8x gain: ratchet 5.6x WORSE, grind 2.5x WORSE
```
✅ **This is the first MEASUREMENT behind the standing rule never to raise the LKAS gain**, and it
matches the operator's own report that 8× made grinding worse. **The rule was right and now it has a
number.**

## ⚠ **THE GRIND METRIC WANTS KNEE 1800; THE OPERATOR ALREADY CHOSE 3000. HIS CHOICE WINS.**
`0xC40BC` is the **only** cell surviving a family-wise-controlled scan of 94 varying cals against the
grind, and independently the cell structural reasoning named. So the obvious next question is whether
the flying value has headroom. Plotting the actual shape rather than the correlation:
```
   knee   n   GRIND median   RATCHET median   saturates at |gp-0x6abc|
    300   9      27.4            38.6            25 ct
    600   6       9.5            29.1            50 ct
   1800   2       5.1            12.5           150 ct     <- grind MINIMUM
   3000   1      15.5            38.3           250 ct     <- the FLYING build, worse
```
⚠ **[WEAK] the grind minimum looks like knee ≈ 1800, and 3000 appears to be PAST it.** V112 at 1800
gave the two lowest grind figures in the whole corpus (7.9 and 2.2).
🛑 **But the 3000 point is ONE route** — `r24`, which has **9 windows, the fewest in the corpus** and
therefore the noisiest estimate of any. On that evidence alone I would not move a cell.

### 🛑 AND THE DECISIVE POINT IS NOT STATISTICAL
The flying image is named **`_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST`**. **V122 IS V112's
base with the knee taken from 1800 to 3000, and it is labelled BEST.** The operator has therefore
already driven both values and **chose 3000 on feel.**
✅ **The standing instruction settles it**: *the operator's lived experience overrides analyst
recommendations.* **No build is proposed to revert the knee**, and none should be, on a metric that
disagrees with a decision he made from the driver's seat.
⊕ Worth stating plainly because the temptation is real: the scan makes `0xC40BC` look like the most
defensible lever in the kit, and it is — **for understanding the grind, not for overriding him.**
⊕ It also explains the shape: the knee trades **grind against feel**. Raising it widens the linear
(viscous) region and shrinks the Coulomb one, which is what makes the wheel feel less notchy even
where the 15–25 Hz metric is slightly worse.

## 🛑 **TWO COMMITS CARRY THE WRONG MESSAGE — STALE FILES IN THE JOB TMP DIRECTORY**
🛑 **`068aace3` is titled *“The 511 ceiling is not a hard limit … V132 lifts both”*. Its actual
content is the flash-readiness section of `DRIVE-CARD-V173.md` (30 insertions, one file).** An earlier
commit had the same defect and was caught before pushing.

**Cause, diagnosed:** this job's tmp directory still holds `m7x`/`m8x` message files from a **previous
session** (`m84`–`m89` all present). My pattern of *write a message file, then `git commit -F` it*
silently used **stale content** on any tick where I skipped the write step — `git commit -F m80.txt`
**succeeded** against a V132 message instead of failing as it would have on a missing file.

✅ **Fixed forward, not by force-push.** The bad message is already on `origin`, and its **tree is
byte-identical to what was intended** — verified by `git diff --stat HEAD origin/main` returning
empty. Rewriting pushed history to correct a cosmetic message is not worth the risk, so the record
lives here instead.
⊕ **Message files are now named distinctly** (`msg-<topic>.txt`) and written immediately before use.
⊕ **If you are reading `068aace3` in the log: ignore its title.** It adds the flash-readiness section
to the V173 drive card and nothing else. Nothing about V132 or the 511 ceiling changed in it.

## ✅✅ **BOTH DRIVE-CARD INSTRUCTIONS CONFIRM AT FULL n — AND THE RATCHET CENTRES AT 8.2 Hz, NOT 8.64**
The last two subset results are **operational instructions on the card**, so a wrong one mis-specifies
the drive. Re-tested on **544 windows across 19 routes** (was 244 across 9):
```
   |COMMAND| ct   n win   RATCHET exc   GRIND exc    n=9 was (rat / grd)
   100-250         38      14.0          4.6          17.0 / 5.1
   250-600        137      15.7          8.1          19.4 / 8.5
   600-1500        87      32.4         14.5          39.4 / 12.6   <- grind PEAKS
   1500+          282      47.8          7.0          58.1 / 6.0    <- grind DIES, ratchet grows
```
✅ **[EVIDENCE] the ratchet is MONOTONE in command** (14.0 → 47.8, **3.4×**) ⇒ *“include real
curvature”* stands. ✅ **[EVIDENCE] the grind PEAKS mid-command and DIES above 1500 ct** (4.6 → 14.5 →
7.0) ⇒ *“take the grind verdict from the mid-command windows”* stands.
✅ **And the worst rate band strengthens**: 12–25 deg/s gives ratchet excess **155.2** (was 143.1).

### ✅ THE FREQUENCY IS BETTER PINNED THAN BEFORE — AND SLIGHTLY LOWER
```
   ratchet peak CV:  3.5 % across speed  ·  4.9 % across rate  ·  8.1 % across command
                     (n=9 gave 5.5 % / 12.3 % / 7.0 %)
   peaks across all strata: 7.81 - 9.57 Hz, median ~8.2
   grind peak: 19.92 - 20.90 Hz, tighter still
```
⚠ **The centre is ~8.2 Hz, not the 8.64 Hz quoted throughout this session.** 8.64 came from the
9-route pooled estimate. ⊕ **No design impact**: V173 targets attenuation across **7–11 Hz**, which
brackets 8.2 comfortably (its response there is ≈0.50 against 0.476 at 8.64 — a 5 % difference), and
the notch placement question does not arise because Honda's notch was kept. **The build is unchanged
and the drive card's bands are unchanged.**
⊕ **All three operational results held.** The pattern continues: **effect sizes and shapes survive;
only categorical small-n phrasings have needed correcting.**

## ✅✅✅ **THE CHANNEL RESULT HOLDS — THE ONE THAT MATTERS MOST SURVIVED THE TEST THAT BROKE TWO OTHERS**
Two n≤9 claims had already fallen on the full corpus, so the **channel survey** — the result that set
the scorer's channel and underwrites *“every prior 6–9 Hz endpoint read the wrong channel”* — had to be
re-tested before being trusted further. It was built on **four** routes. On **nineteen**:
```
   channel    routes  mean margin  median   min     n=4 result
   tq         19      28.20        15.52    1.60    7.62
   cs_tq      19      25.80        14.87    1.64    7.42
   ws_fl      19       6.13         6.02    3.74    3.95
   ws_fr      19       5.15         4.91    2.90    4.41
   cs_rate    19       2.60         1.66    0.68    1.03
   ang/wang   19       1.86         1.09    0.39    0.83
   cs_ang     19       1.52         1.16    0.50    0.79
   sc_tq      19       0.92         0.94    0.47    0.56
   co_tqcan   19       0.91         0.85    0.48    0.59
   cc_req     19       0.88         0.82    0.52    0.67
```
✅ **[EVIDENCE] the ordering is unchanged and every margin GREW.** Torque leads the next-best channel
by **5×** (25.8 vs 6.1) and wheel rate by **10×**. ✅ **All three COMMAND channels sit below 1.0 on 19
routes** — the ratchet is not in the command, now on the full corpus rather than four routes.
⇒ **the scorer's channel is right, and the “wrong channel” claim stands.**

### ⚠ ONE PHRASING SOFTENS — the same n≤9 pattern, a third time
I wrote that `cs_rate` scores **“at CHANCE (1.03)”**. On 19 routes it is **2.60 mean / 1.66 median**,
i.e. **above** its null on most routes. **Wheel rate carries a real but ~10× weaker ratchet signal;
it is not at chance.** The operational conclusion is unaffected — scoring the ratchet in `cs_rate`
would still be measuring the weakest usable channel with a floor it barely clears — but the wording
was a small-n overstatement, exactly like the other two.
⊕ **Three for three**: every claim of mine that has needed correcting was a **categorical statement at
n≤9** (*“never moved”*, *“absent in manual”*, *“at chance”*). **Every effect SIZE has held or grown.**

## 🛑 **CORRECTION 2: “ENGAGEMENT *CREATES* THE RATCHET” IS TOO STRONG — IT AMPLIFIES IT ~15×**
The same corpus enlargement that corrected the build-trend claim also softens the engaged/manual one.
```
                          n=7 (earlier)          n=15 (full corpus)
   engaged clears null     7/7                    15/15
   manual  clears null     0/7                    6/15        <- NOT zero
   speed-matched ratio     19.9x [4.82, 35.64]    15.1x [6.0, 38.9]   (n=12 matched)
```
🛑 **[EVIDENCE] the manual arm clears its slope-matched null on 6 of 15 routes**, where the
9-route subset gave 0 of 7. ✅ **But it clears MARGINALLY in 5 of those 6** — 3.3 vs 2.8, 2.7 vs 2.5,
2.3 vs 2.2, 3.8 vs 2.7, 2.9 vs 2.4 — with only `r21` clearly above (8.2 vs 4.7). Meanwhile the
**engaged arm clears 15/15, usually by 10–100×** (up to 339.3 vs 2.7 on `r82`).
⇒ **the right statement is that engagement AMPLIFIES the ratchet by ~15×, not that it CREATES it.**
The mode is faintly present in manual driving and enormously larger when engaged.

### ✅ WHAT THIS CHANGES
⊕ **The ratio TIGHTENS**: 15.1× **[6.0, 38.9]** on 12 matched pairs, against 19.9× [4.82, 35.64] on 4.
Same magnitude, better bounded.
⊕ **The drive endpoint is unaffected.** Engaged sits at 12–339 against a null near 2–5, so the
presence/absence reading holds with an enormous margin; the manual arm was only ever a control.
🛑 **But the MECHANISTIC claim changes.** *“Firmware-created”* implied the mode does not exist without
the loop. It does — faintly. The loop **amplifies an existing mode**, which is exactly the `1−P·L`
picture and is if anything **more** consistent with the account than outright creation would be.
⊕ **No build changes.** V173 reduces `|L|`, which is the amplification.

### ⚠ THE PATTERN IN BOTH CORRECTIONS
Both claims that fell were **presence/absence statements made at n≤9, and both fell in the direction
of my own hypothesis** — *“never moved”* and *“absent in manual”* were the strong readings, and the
full corpus made each one weaker. **Small-n presence/absence claims are the failure mode to watch for
here**, not the effect sizes, which have held.

## ✅✅✅ **THE CORPUS WAS TWICE WHAT I WAS USING — AND IT CLOSES THE DRIVEN/SELF-EXCITED QUESTION**
🛑 **I had been scoring 9 routes. There are 19** whole-route caches carrying the core channels, and
several hold far more engaged-creep windows than anything I used — **`r77` has 97 against `r1e`'s
42.** (The `sNN` entries are per-segment sub-caches of the same drives, so they are not independent
and are excluded.) **Nothing was wrong with the analysis; I simply never enumerated the cache.**
```
   ratchet, all 19 routes, cs_tq, excess / slope-matched null
     r78 12.2/2.2   r7e 31.0/2.0   r7f 39.2/2.3   r96 38.6/2.7   ra4 23.3/1.9
     ra6 29.0/1.9   r1e 21.0/1.9   r22 20.6/2.5   r24 38.3/3.2
     r21 27.2/1.9   r77 20.2/1.6   r79 11.5/2.0   r81 243.7/2.4  r82 237.2/2.3
     r85 58.7/2.8   r95 193.2/2.5  r97  4.4/2.5   r9e 38.1/2.4   ra5 84.6/2.3
   => REAL on 19 of 19 routes.  Peak 7.42-10.16 Hz, consistent with the 8.64 Hz estimate.
```

### ✅ AND THE ONE OPEN QUESTION THAT NEEDED POWER IS NOW ANSWERED
At n = 7 the driven-vs-self-excited test was **inconclusive** — specific on 6/9 routes but the pooled
CI **[−0.021, +0.176] crossed zero**. Same statistic, more data:
```
   band-specific coupling = coherence(7-10.5 Hz) - coherence(30-40 Hz control),
   command -> cs_tq, vs phase-shuffled surrogates.   n = 17 routes

     median specificity  +0.1148
     95 % CI             [+0.0274, +0.1682]      <- EXCLUDES ZERO
     individually specific on 10 of 17
     specificity vs window count: rho +0.31 (p 0.226)
```
✅ **[EVIDENCE] THE RATCHET IS DRIVEN BY THE COMMAND, not self-excited.** The CI excludes zero, and
the positive window-count trend is exactly what an underpowered *real* effect predicts — which is what
`r1e` hinted at when it was the only well-powered route.
⚠ **Not universal**: three routes (`r85`, `r95`, `r97`) show *negative* specificity. The claim is
about the population, not every drive.

### ⭐ WHAT IT CHANGES, AND WHAT IT DOES NOT
⊕ **V173 works either way.** The assist map amplifies whatever reaches the bar, so attenuating it at
8.64 Hz reduces the ratchet whether the excitation is the command or the loop itself. **No build
changes.**
⊕ What it *does* change is **what a null on the drive would mean**: with the ratchet established as
command-driven, a null could no longer be explained by "the excitation was absent on that pass" — the
pass carries command by construction. **It sharpens the pre-registered outcomes rather than altering
them.**
⊕ And it retires an open item that was recorded as *“closes with more continuous windows”*. **It did.**

## ❌ **RING-DOWN DOES NOT TEST THE `P·L` ASSUMPTION EITHER — AND MY FIRST CONTROL WAS VACUOUS**
The last idea for testing `P·L` without driving: a **time-domain** ring-down, immune to the spectral
tilt that killed the other estimators, and the one measure the kit's record says *“passed its
control”*. Since `ζ_eff = ζ_passive · |1−P·L|`, a decay rate that differs across builds would test the
account from data already in hand. Trigger: an abrupt command collapse, then fit the 8.64 Hz envelope
over 0.5 s of free decay.

### 🛑 MY FIRST CONTROL COULD NOT HAVE WORKED
I controlled by fitting the **time-REVERSED** envelope, reasoning that a genuine one-sided decay would
fit worse backwards. It returned **0.64/0.64, 0.61/0.61, 0.80/0.80 … identical on every route** — the
tell. **Reversing a linear fit's x-ordering flips the slope but leaves the residuals unchanged, so r²
is invariant BY CONSTRUCTION.** The control could never discriminate anything. Replaced with the same
fit on engaged segments that have **no** command collapse.

### ❌ AND WITH A REAL CONTROL, THE MEASUREMENT IS TOO WEAK TO USE
```
   route build  alpha 1/s  zeta     Q      CONTROL  verdict
   r78   V91      2.65     0.0489   10.2    2.12    no better than control
   r7e   V96      3.14     0.0579    8.6    2.16    no better than control
   r7f   V96      4.92     0.0906    5.5    1.80    DECAY
   r96   V102     3.40     0.0626    8.0   -0.95    control NEGATIVE -- nonsense
   ra4   V104     4.13     0.0761    6.6    1.51    DECAY
   ra6   V106     3.96     0.0729    6.9    1.59    DECAY
   r1e   V107     1.17     0.0216   23.2    1.62    no better than control
   r22   V112     4.82     0.0888    5.6    1.95    DECAY
   r24   V122     4.49     0.0827    6.0    1.35    DECAY
```
❌ **It clears its control on only 6 of 9 routes, and by 1.5–3.3x** — the decay alphas (1.17–4.92)
**overlap the control alphas (1.35–2.16)** heavily. ❌ **One route's control is NEGATIVE (−0.95)**, i.e.
its no-collapse envelopes *grow* on average, which invalidates the control there outright.
❌ **ζ = 0.022–0.091 does not match the kit's recorded ring-down ζ = 0.017–0.036** except at the
extreme. ❌ **And there is no build ordering**: V91 2.65 · V96 3.14/4.92 · V102 3.40 · V104 4.13 ·
V106 3.96 · V107 1.17 · V112 4.82 · V122 4.49.
⇒ **the ring-down carries no usable damping information at engaged creep in this corpus.**

### ✅ WHAT THIS SETTLES
**Three independent estimator families have now been tried on the `P·L` question and all three fail**:
frequency-domain Q (tilt-confounded), the slope-corrected excess stratified by torque (confounded by
rate, structurally), and now time-domain ring-down (does not clear its own control). **The assumption
is testable only by intervention.** That is no longer a judgement — it is a result, and this closes
the line for good.

## ✅ **TOOL AUDIT: ONE MORE LIVE HAZARD FOUND AND CLOSED**
Having found the primary scorer reading the wrong channel, I audited **all 43 scoring tools** for the
same defect — a ratchet or grind endpoint computed on `cs_rate`, where the ratchet scores at chance.
✅ **No other tool has that defect.** Every remaining ratchet/grind endpoint either reads `cs_tq`,
sweeps channels deliberately, or is a probe-specific scorer with its own anchor.

🛑 **But the audit found a different live hazard**: `docs/scoring/DRIVE-CARD-V158.md` and
`SCORING-V158-preregistered.md` still pointed at **`score_v158_creep.py`**, the scorer this session
**superseded**. Had V158 been flown from its own card, the drive would have been scored with:
- **half-power Q of the 15–25 Hz peak** — withdrawn, NON-MONOTONE (its null sits *above* the data);
- **Q at 5–12 Hz** — withdrawn, a WINDOW artefact (white noise alone returns Q 21.7–29.1);
- **fixed-floor prominence** — withdrawn, large by construction on a red spectrum;
- **non-continuous windows**, where the validated estimator requires continuous runs;
- and **`cs_rate`**, before the channel finding.
✅ **Closed three ways**: the tool now carries a superseded banner **and raises on import** so it
cannot be used by accident; both documents are redirected to `score_band_excess.py`; and no document
outside STATE's own retraction text mentions it any more.

⊕ **The pattern worth keeping**: the defect was not in the analysis, it was in the *plumbing between
the analysis and the drive*. Both instances were found by **running the drive card's own command
verbatim** rather than by reading the code. That check is cheap and it belongs in every close-out.

## 🛑✅ **THE SCORER WAS READING THE WRONG CHANNEL — CAUGHT BY RUNNING THE DRIVE CARD'S OWN COMMAND**
With the design closed, I ran the pipeline end-to-end exactly as it would run on a fresh route. It
found a defect that would have produced a **wrong verdict on the drive**.
```
   score_band_excess.py  read  z['cs_rate']
   but cs_rate scores at CHANCE for the ratchet: margin 1.03 vs cs_tq's 7.42
```
🛑 **[EVIDENCE] the tool the drive card points at was measuring the ratchet in the one channel
where it is not present.** Fixed to `cs_tq`, and the numbers now match the analysis they came from:
```
   r24 / V122, cs_tq        BEFORE (cs_rate)      AFTER (cs_tq)
     ratchet 5-12 Hz          4.4x                 33.2x     split-half 1.21x
     grind  15-25 Hz         23.2x                 14.0x     split-half 3.29x
```
⊕ Note the split-halves **swap**: the ratchet is now the *tighter* endpoint (1.21x) and the grind the
looser (3.29x). That is the right way round — the ratchet is what the channel is good for.

### ✅ AND THE DRIVE CARD'S TWO DISCRIMINATORS ARE NOW IN THE TOOL
One command gives the whole verdict instead of three hand-run analyses:
- **grind sub-bands 15–20 vs 20–25 Hz** — V173's filter attenuates the top **2.2x** more (sloped),
  V158's damper is dose-set and flat ⇒ the SHAPE says which lever produced a reduction.
  Reference measured on the flying build: **15–20 = 5.8x, 20–25 = 14.0x, ratio 2.39.**
- **grind vs ratchet by COMMAND level** — the grind saturates above 1500 ct while the ratchet grows,
  so the two verdicts come from different strata.
⊕ **Both carry an 8-window guard.** On r24 the strata hold 0 and 4 windows and now print *“TOO FEW to
report”* rather than the 198x / 1270x the unguarded version emitted — those came from a background
fit on four windows and were **not credible**. Catching that in the tool is the point of running it
before the drive rather than after.

## ✅✅✅ **EVERY REMAINING LEVER IS BELOW THE MEASUREMENT FLOOR — V173 IS THE WHOLE AVAILABLE FIX**
Pricing what is left after V173, with the corrected `L_other` (r26 gated off ⇒ 0.31–0.55, not 0.825).
Anchor unchanged in kind: the measured `Q_eff/Q_passive = 14.3` fixes `P·L = 0.93`, so `P = 0.93/|L|`.

### ✅ FIRST, THE PREDICTION SURVIVES MY OWN CORRECTION
```
   L_other   P        stock Q   V173 Q   V173 gain
   0.825     0.3292   14.29     2.45     5.8x     <- census value, now known WRONG
   0.550     0.3647   14.29     2.25     6.4x
   0.430     0.3827   14.29     2.16     6.6x     <- corrected, mid
   0.310     0.4026   14.29     2.07     6.9x
```
✅ **[EVIDENCE] V173's predicted effect is INSENSITIVE to the r26 error**: 5.8x at the wrong value,
6.9x at the low end of the right one. **The correction moves the prediction the RIGHT way and by
less than its own uncertainty.** That is the robustness check the earlier numbers lacked.

### 🛑 AND EVERY REMAINING LEVER IS UNMEASURABLE
```
   marginal gain ON TOP of V173 (L_other = 0.43)     new |L|   Q ratio   vs V173
     nothing (V173 alone)                             1.403     2.16      1.00x
     kill the PID entirely                            1.146     1.78      1.21x
     kill r24 entirely                                1.232     1.89      1.14x
     kill PID AND r24 together                        0.975     1.60      1.35x
     add the slope cap 1536 (V168's lever)            1.159     1.80      1.20x
     add the slope cap 1024 (V171's dose)             0.916     1.54      1.40x
```
🛑 **[EVIDENCE] the single-episode split-half floor is 1.63x.** Every entry above is **at or below
it** — so none of these could be distinguished from noise on a drive **even if built and even if the
model is exactly right.**
⇒ **V173 captures essentially all the available loop-gain reduction.** The assist map is the loop, and
V173 is the assist map's lever.

### ✅ WHAT THIS CLOSES, AND WHY NO EIGHTH BUILD
**The analysis is complete.** Not “out of ideas” — *priced*, and every remaining idea is worth less
than the noise on the only measurement available. Building another would be adding a variable that
cannot be read.
⊕ The three named symptoms now stand as: **ratcheting** → V173 (6.6x predicted) · **grinding** →
V158's damper + V173's filter, on the same build · **command oscillation** → shares the grind's band
and lever · **LKAS authority** → measured, not limiting, no lever needed.
⊕ **The next information can only come from the car.** Seven builds, one decision table
(`docs/scoring/BUILD-INVENTORY.md`), one continuous 15-second engaged creep pass with real curvature.

## ❌ **r26 IS ALREADY GATED OFF ENGAGED — NO LEVER THERE, AND MY LOOP DECOMPOSITION OVERCOUNTED**
Looking outside the assist lane: after V173 the assist map is ~54 % of `|L|` and the
engagement-conditional terms ~46 %. The census lists **r26 at 0.098–1.17**, potentially the largest
of those, *“LIVE only while `gp-0x6b5e == 0`”* — a **GATE, not a gain**, and one never examined
(`0xC6444` is falsified on-car but that was a MAGNITUDE cut with the gate still open).
```
   FUN_000361c8, the sole producer (writers 0x36256 / 0x36264, both st.h):
     gp-0x6b5e = +/- POL * ( LERP(gp-0x6bda) * cal(0xC63C2) ) >> 10

   X knots 0xC66CE: [-384, -128, 128, 294, 384, 0]      scale 0xC63C2 = 1024 (unity)
   Y knots 0xC66D8: [   0, 4762, 4762, 717,   0, 0]

   engaged, gp-0x6bda == 0.0000 over 75,227 frames  =>  0 falls in segment [-128, 128]
   =>  LERP returns 4762  =>  gp-0x6b5e = +/-4762   NON-ZERO
```
❌ **[EVIDENCE] r26 is ALREADY gated OFF during engaged creep.** The gate this line was chasing is
**already closed by Honda**, so there is no lever here and `0xC66D8`/`0xC63C2` need not be touched
(both byte-identical across all 167 images).
🛑 **AND IT CORRECTS MY OWN NUMBERS**: I have been carrying the census's **`L_other` = 0.825**,
derived as `2.825 − 2.0`, with r26's 0.098–1.17 inside it. **If r26 is gated off engaged, that figure
overcounts the engaged loop** — the remaining terms are PID 0.2565 + r24 0.049–0.293 + `FUN_00036682`
0.0032 ≈ **0.31–0.55**, not 0.825.
⊕ **This does NOT change the lever choice**: every build's predicted effect was computed as a RATIO
against the same anchoring, and a smaller `L_other` makes the assist map an even LARGER share of the
loop — it strengthens the case for V173 rather than weakening it. But **the absolute Q-ratio figures
carry more uncertainty than their two decimal places suggest**, and that is now on the record.
⚠ **Blast radius, for the record**: `gp-0x6b5e` has **4 readers** — `0x36390`, `0x3AA8E` (the
aggregator), and **`0x4DA92` / `0x4DFAE` outside it**. Had the gate been open, closing it would NOT
have been the clean single-consumer edit `gp-0x6b86` was.

### 🛑 THE tp OFF-BY-0x1000 TRAP RECURRED — EIGHTH RECORDED TIME, CAUGHT BY THE SHAPE
My first read used **`0xC76CE`** instead of `tp+0x76ce` = **`0xC66CE`**, and returned
`X = [15, 4100, 15, 4102, 15, 4104]` / `Y = [4104, 15, 4106, 15, 8192, 15]`. **The interleaved 15s
were the tell** — a knot table is monotone, not alternating — exactly as *“the denormals were the
tell”* on the sixth recurrence. It produced the **opposite conclusion** (apparently “gated off”, by
luck, from entirely the wrong cells). **Anchor first, then read; and check the SHAPE of what comes
back.**

## ✅ **V173 IS ON THE EFFICIENT FRONTIER — THE DESIGN WORK IS COMPLETE**
With Honda's notch fixed and the structure known to separate, the design reduces to choosing **one
real pole pair**. Sweeping every pair that holds DC within 2 % of unity and never amplifies:
```
   added lag   8.64 Hz   3 Hz     poles        21 Hz
     30.1 ms    0.4761   0.8476   0.970/0.475  0.1894   <- V173 AS BUILT
     30.1 ms    0.4691   ~0.85    0.970/0.75   ~0.17    <- best possible at that lag
     46.6 ms    0.3383   0.7285   0.980/0.60   0.1253
     54.6 ms    0.2832   0.7507   0.975/0.95   0.0584
```
✅ **[EVIDENCE] V173 is at the frontier**: the best achievable at its own 30.1 ms lag is **0.4691**
against V173's **0.4761** — a **1.5 %** difference, far inside any measurement floor. Its pole pair was
*inherited* from V172 rather than chosen, and it happens to be essentially optimal. **No rebuild.**
⊕ **The trade is priced if more is wanted**: **0.338 at 46.6 ms** or **0.283 at 54.6 ms**, i.e. buying
another 1.4–1.7x of ratchet attenuation costs 16–25 ms of additional assist lag. That is a **feel**
decision, and it is the operator's — the builds are one coefficient triple away if he wants one.

### ✅ WHAT THIS CLOSES
Design work on the assist lane is **finished**. Both lever classes are cut and verified, both gates
are closed, every artifact re-hashes from disk, and the remaining assumption is testable only by
driving. **Seven builds, one decision table, one 15-second pass.**

## 🚩✅ **V173 BUILT AND SUPERSEDES V172 — THE SAME LEVER WITHOUT GIVING UP HONDA'S NOTCH**
```
   V173 = V158 + THREE float32 cells (C_A8, C_AC, C_B4).  C_B0 left BYTE-IDENTICAL to stock.
   image  a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7
   .rwd   5d213cf8604df90f2df2eaa2a8e40ccedde89f1d66055cb2a22c81edb7245396
   11 payload bytes + one CRC trailer - 25/25 assertions - chain 50/50 - readback identical
```

### ⭐ THE STRUCTURE, COLLAPSED — AND IT SEPARATES
```
   H(z) = C_B4 * ( z^2 + C_B0*z + 1 ) / ( z^2 + C_A8*z + C_AC )
```
✅ the numerator's roots have **product 1** ⇒ the zeros are **always exactly on the unit circle**, so
this is **always a true notch**, at `2 cosθ = −C_B0` ⇒ **`C_B0` ALONE sets the notch frequency.**
✅ the poles are set by `C_A8`/`C_AC` **alone** ⇒ **notch frequency and damping are INDEPENDENT.**
✅ `DC gain = C_B4 (2 + C_B0) / (1 + C_A8 + C_AC)`.

### 🛑 WHICH EXPOSED A DEFECT IN V172
Stock `C_B0` puts Honda's notch at **55.23 Hz, −43.9 dB**. **V172 moved it to 27.17 Hz** as a side
effect of letting an optimiser choose all four coefficients ⇒ **V172 gives up Honda's 55 Hz notch
entirely** (0.000128 → 0.251316 there). **We do not know what that notch is FOR**, and Honda placed a
deep null at a specific frequency in the dominant assist lane deliberately.
✅ **V173 keeps `C_B0` bit-for-bit and moves ONLY the poles:**
```
   freq        FLYING      V172        V173
   0.5 Hz      0.999965    1.006656    0.994633     DC preserved
   3   Hz      0.997530    0.850073    0.847560     driver band -- same as V172
   8.64 Hz     0.978950    0.444078    0.476076     THE RATCHET -- same as V172
   21  Hz      0.865930    0.090235    0.189446     grind 4.6x (V172 got 9.6x)
   40  Hz      0.452204    0.134765    0.054184     better than V172
   55.23 Hz    0.000128    0.251316    0.000013     ** HONDA'S NOTCH KEPT, and deeper **
   group delay added at 0.5 Hz: V172 +30.1 ms, V173 +30.1 ms -- IDENTICAL (same poles)
   loop effect: V173 5.8x vs V172 6.1x - max |H| to Nyquist 0.9946 => NEVER amplifies
```
⇒ **same lag, same ratchet effect, Honda's notch preserved, and THREE cells instead of four.**
The trade is **half the grind attenuation**, which is the right side to err on: the ratchet is the
**unsolved** symptom and both builds are equal there, while the grind **already has V158's damper on
this same base.**

### ❌ WHY THE NOTCH CANNOT BE PUT ON THE RATCHET — STRUCTURAL, NOT AN OPTIMISER FAILURE
`C_B4 = DC(1+C_A8+C_AC)/(2+C_B0)` and `2+C_B0 = 2−2cosθ → 0` as the notch approaches DC, so **`C_B4`
scales as ~1/f²**:
```
   notch  8.64 Hz => C_B4 13.576 => amplifies out-of-band 1503x
   notch 27    Hz => C_B4  1.393 => amplifies 120x
   notch 55.2  Hz => C_B4  0.336 => amplifies 1.0x   <- Honda's placement, the ONLY free one
```
⇒ **Honda put the notch at 55 Hz because that is where it costs nothing.** A notch at the ratchet
needs 13.6x input gain and amplifies everything else. **The POLES, not the notch, are the lever in
the ratchet band.**
🛑 **I withdraw my remark that the optimiser “was fighting a structure it did not understand”** — it
found the right shape for the right reason; the defect was only the notch it displaced.

### 🛑 AND A CORRECTION TO MY OWN NOVELTY CLAIM
I wrote that this session **“RETRACTS two recorded claims — ‘no frequency-selective lever’ and ‘no
notch filter exists’”**. **`MEMORY-PART5` already carries that retraction**, in detail, with the same
four coefficients, the ±19.88° zeros and the “transparent except at the notch” observation.
**The kit found this first; I re-derived it without checking.** That is exactly the failure the
`feedback-search-the-kit-before-naming-a-cause` memory exists to prevent.
⊕ What IS new here: the **collapsed transfer function** and its separability, the **1/f² bound on
notch placement**, the **task-rate resolution** below, and the **built lever**.

### ✅ AND IT UNBLOCKS WHAT THAT MEMORY WAS PARKED ON
`MEMORY-PART5` records this lever as **“BLOCKED ON THE TASK RATE — task 5 is bounded ≥250 Hz but
NEVER pinned”**, with the notch landing anywhere from 13.8 to 55.2 Hz depending on the rate.
✅ **[EVIDENCE] `get_function_callers(0x352b4)` returns exactly `FUN_0002214a`**, which the kit's own
record identifies as **TASK 1, the CONFIRMED 1 kHz task**. The rate uncertainty belongs to **task 5**
(`FUN_00022ca0`), a **different** task that drives the damper. ⇒ **the assist section runs at 1 kHz,
the notch is at 55.23 Hz, and the block is lifted.** Confirmed independently: a full-band scan finds
the flying section's null at **55.0 Hz, −43.9 dB**, matching the ±19.881° zeros exactly.

## ✅ **SAME CLASS, DIFFERENT DRIVE LAW — THE GRIND SATURATES WHERE THE RATCHET KEEPS GROWING**
Both symptoms are engaged-only and both sit in `cs_tq`, so the question was whether they are one
mechanism at two plant modes. **Mostly yes — with one clean difference that matters for scoring.**
```
   244 pooled windows, each assigned to a stratum by its OWN mean operating point

   |COMMAND| ct    n win  |  GRIND Hz  excess  |  RATCHET Hz  excess
   100-250          23    |   19.14     5.1    |    9.57       17.0
   250-600          75    |   19.73     8.5    |    8.59       19.4
   600-1500         46    |   20.12    12.6    |    8.01       39.4
   1500+           100    |   19.14     6.0    |    8.20       58.1

   FREQUENCY   grind CV 9.6 % (speed) - 11.0 % (rate) - 2.1 % (command)
               ratchet CV 5.5 %       -  12.3 %       - 7.0 %
```
✅ **[EVIDENCE] both are FIXED-FREQUENCY** — neither peak moves materially with operating point, so
both carry the `1−P·L` signature of a plant mode whose damping the loop is cancelling. The grind's
**2.1 % CV across command** is the tightest figure either symptom produces.
🛑 **[EVIDENCE] but their DRIVE LAWS differ**: the ratchet is **MONOTONE in command (3.4x)** while
the grind **peaks mid-command (12.6 at 600–1500) and FALLS at high command (6.0 at 1500+)**.
⊕ That non-monotonicity is **consistent with the kit's own recorded fact** that *“saturation
suppresses it 141x”* — at high command the loop rails and the resonance is suppressed. The grind sits
at a higher frequency, so the same command amplitude produces a larger rate and rails sooner.
⚠ **[BELIEF, not EVIDENCE]** the saturation explanation. The drop is 12.6 → 6.0 across strata of 46
and 100 windows; it is a real pattern but a single-drive artefact is not excluded.

### ⭐ THE SCORING CONSEQUENCE, FREE FROM THE SAME EPISODE
The two symptoms are **best read at DIFFERENT command levels**:
```
   RATCHET   strongest at HIGH command (1500+)      excess 58.1
   GRIND     strongest at MID command (600-1500)    excess 12.6, and DIES above it
```
⇒ a pass that spends all its time at high command will read the ratchet well and **under-read the
grind**. **A slow lap with varied curvature covers both**, which is what the drive card already asks
for — this says *why*, and it means the grind verdict should be taken from the mid-command windows
rather than pooled across the whole pass.
⊕ Added to the V172 drive card.

## ✅✅ **THE GRIND IS ENGAGED-ONLY TOO — AND A SUB-BAND SPLIT ATTRIBUTES IT**
Both levers on the fly-first build act at 15–25 Hz, so a grind change needs attributing. The obvious
discriminator — V158's damper is **engaged modes 26/27 only** while V172's filter is **always
active** — would work if the grind existed in manual. **It does not.**
```
   GRIND 15-25 Hz, engaged vs MANUAL creep, slope-matched nulls
     r78  V91    engaged   6.1 / 3.5    manual  2.3 / 3.8    no
     r7e  V96             28.9 / 3.2            2.2 / 4.8    no
     r7f  V96             14.3 / 3.5            2.2 / 3.9    no
     r96  V102           248.2 / 4.0            1.5 / 4.9    no
     ra6  V106            25.3 / 4.0            3.0 / 3.9    no
     r1e  V107            27.7 / 2.7            1.6 / 4.5    no
     r24  V122            14.0 / 3.9            1.9 / 4.1    no
   => the grind clears its null in MANUAL on 0 of 7 routes
```
✅ **[EVIDENCE] the GRIND is engaged-only, exactly like the ratchet** (also 0/7 in manual).
⇒ **both symptoms are FIRMWARE-CREATED BY ENGAGEMENT**, not mechanical modes being amplified. They
differ in frequency and in which levers move them, **not in class**. **This is new** — the ratchet was
established engaged-only earlier this session; the grind had never been tested the same way.
❌ And it kills the manual-arm discriminator: neither symptom exists there to compare.

### ✅ WHAT DOES DISCRIMINATE: THE SHAPE ACROSS THE BAND
V172's filter attenuation is **frequency-SLOPED**; V158's damper adds a rate-proportional term whose
effect is set by the dose, not the frequency, so it is roughly flat across 15–25 Hz.
```
   V172 attenuation:  15 Hz 0.2298 - 17 Hz 0.1828 - 19 Hz 0.1415
                      21 Hz 0.1042 - 23 Hz 0.0694 - 25 Hz 0.0359
   mean 15-20 Hz 0.1737   vs   mean 20-25 Hz 0.0784
   => V172 attenuates the TOP of the band 2.21x more than the bottom
```
⭐ **DISCRIMINATOR, free from the same episode**: score the grind excess in **15–20** and **20–25**
separately.
- **20–25 falls much more than 15–20** ⇒ **V172's filter did it.**
- **both fall about equally** ⇒ **V158's damper did it.**
⊕ Added to the V172 drive card.

## ✅ **GATE 1 PASSES FOR V172 — `gp-0x6b86` HAS EXACTLY ONE CONSUMER, AND IT IS NOT A MONITOR**
V172 low-passes the assist map's output hard (**21 Hz down 9.6x, 40 Hz down 3.3x**). The aggregator
consuming it is fine with that — it is a torque contribution. **The risk was a MONITOR**: a
stuck-signal, rate-of-change or plausibility check that expects the value to keep moving, since
heavily low-passing a watched signal can look like a frozen sensor. Raw LE byte scan across **both**
gp encodings (operand-text search undercounts and cannot see register-indirect access at all):
```
   gp-0x6b86  4 accesses, ALL accounted for
     0x35AB6  ld.h        }  inside FUN_000352b4 -- the producer's own lockstep compare
     0x35AC0  st.h        }  the write
     0x35ACE  st.h r0        the store-zero (the out-of-range branch)
     0x3AC7C  ld.h           FUN_0003aa2c, THE AGGREGATOR -- the only consumer outside the producer

   gp-0x4cde  3 accesses -- the lockstep SHADOW, all inside the producer, written in step
```
✅ **[EVIDENCE] exactly ONE consumer outside the producer, and it is the torque sum this build
intends to change.** No monitor, no plausibility checker, no rate-of-change watchdog reads it.
⇒ **GATE 1 (RAM ownership) PASSES**: heavily filtering this signal cannot trip a fault path,
because nothing is watching it for liveness.
⊕ The lockstep shadow is unaffected by a coefficient change — the value is still written to both
cells in the same instruction pair, so the pairing that trips `FUN_0006b9fa` is preserved.
⊕ The same clearance covers V168, which changes only how the value is COMPUTED, not who reads it.

## ⚠ **THE `P·L` ACCOUNT CANNOT BE TESTED FROM THE EXISTING DATA — THE DRIVE IS NECESSARY**
The account makes one prediction that looked free to check: the assist map's local slope **falls
steeply along its own curve** (6.16 → 0.86 → 0.01, capped at 2.000 below X≈100), so if that slope is
the dominant term in `L`, the ratchet should **weaken at higher driver torque**. No other account has
to predict that.
```
   raw stratification by |driver torque|
     |tq| 80-150    n= 49   map slope 1.807   excess  10.7   |cmd|  303   |rate|  2.4
     |tq| 150-300   n= 34   map slope 0.768   excess  22.9   |cmd|  393   |rate|  6.0
     |tq| 300+      n=161   map slope 0.140   excess  44.2   |cmd| 1946   |rate| 35.4
     excess vs map slope rho -1.00   -- the WRONG sign, but |cmd| and |rate| are rho +1.00
```
❌ **The confounds are perfectly aligned with the stratum**, so the raw test is uninformative.
Stratifying torque WITHIN narrow command bands splits 2-supporting / 1-contradicting — but that is
**also fully explained by the rate confound alone**: excess peaks at **12–25 deg/s and FALLS above
it**, and the two “supporting” rows have mean rates of **40.6 and 59.7** (past the peak) while the
“contradicting” row runs **2.4 → 7.0** (climbing toward it).
🛑 **[INCONCLUSIVE] — and structurally so.** Driver torque, command and wheel rate are all driven by
how hard the wheel is being worked, so **observational data cannot separate the map's slope from the
rate**. This is not a power problem that more windows would fix. **Recorded so it is not re-attempted.**
⇒ **the `P·L` real-positive assumption is testable only by intervention** — i.e. by flying V172 or
V168 and seeing whether the peak moves. That is exactly what the pre-registered outcomes cover, and it
is why no further static analysis is being done on this question.

## ✅ **DO NOT STACK THE TWO LEVERS — AND V172 ALREADY PASSES THE TARGET**
```
   build                        eff s   |L|     Q ratio   vs stock
   STOCK / flying               2.000   2.825   14.29     1.0x
   V169  cap 1792               1.750   2.575    6.57     2.2x
   V168  cap 1536               1.500   2.325    4.26     3.4x
   V170  cap 1280               1.250   2.075    3.16     4.5x
   V171  cap 1024               1.000   1.825    2.50     5.7x
   V172  filter retune          0.907   1.732    2.33     6.1x
   V172 + cap 1536 (stacked)    0.680   1.505    1.98     7.2x
   V172 + cap 1024 (stacked)    0.454   1.279    1.73     8.3x
```
❌ **[EVIDENCE] stacking is a bad trade**: the cap on top of V172 buys **1.17x** (1536) or **1.35x**
(1024) while adding the **FULL static weight cost**. ⊕ V172's build asserts the cap is stock, so the
two cannot be stacked by accident.
✅ **[EVIDENCE] V172 alone already passes the target**: a Q ratio of 3.0 needs `|L| ≤ 2.025`, and
V172 leaves **1.732**.

### ⭐ WHAT A THIRD LEVER WOULD HAVE TO BE
After V172 the loop splits **52 % assist map / 48 % everything else**, and "everything else" is the
census's **engagement-conditional** terms — PID 0.2565, r24 0.049–0.293, r26 0.098–1.17 (live only
while `gp-0x6b5e == 0`), `FUN_00036682` 0.0032.
⇒ **a third lever must come from those, not from the map.**
🛑 **But it is NOT worth starting before a drive result.** Two independent levers already exceed the
target on paper; **which of them the car actually responds to is the one thing no further analysis can
settle**, and both rest on the same `P·L` assumption that a single pass tests. Six builds are cut and
only one can fly at a time — **more builds now would be speculation, not progress.**
⊕ Consolidated into `docs/scoring/BUILD-INVENTORY.md`: the decision table, the hashes, and what each
outcome licenses.

## 🚩 **FLIGHT ORDER REVISED — V172 FIRST. MY “130 ms LAG” WAS THE WRONG METRIC.**
I recommended V168 first on the grounds that V172 added *“~130 ms”* of lag. **That figure was the
STEP SETTLING TIME, which is not what a driver feels** — settling is dominated by the slowest pole's
tail regardless of whether any signal energy is there. The right metric is **group delay in the band
the driver actually steers in**:
```
   freq       FLYING     V172       ADDED LAG
   0.5 Hz     3.8 ms     33.9 ms    +30.1 ms
   1   Hz     3.8 ms     32.9 ms    +29.1 ms
   3   Hz     3.8 ms     25.1 ms    +21.4 ms
   5   Hz     3.8 ms     17.3 ms    +13.5 ms
   8.64 Hz    3.9 ms      9.3 ms     +5.4 ms
```
✅ **[EVIDENCE] the real added lag is +30 ms, not +130 ms**, and it FALLS with frequency. 30 ms is at
the low end of what is usually reported as noticeable in steering feel.
⇒ **V172's risk is materially lower than I stated, and the recommendation changes.**

### ⭐ WHY V172 NOW GOES FIRST
```
             predicted ratchet   also grind?   what it costs
   V168      3.4x                no            heavier NEAR CENTRE, uniformly, always
   V172      6.2x                9.6x          +30 ms group delay; 3-5 Hz content down 15-32 %
```
✅ **The operator's standing constraint is explicitly about apparent MASS AND FRICTION** — *“low
apparent steering mass and friction to LKAS”*. **V168 raises exactly that, uniformly. V172 leaves it
untouched** (DC gain 1.0067). ✅ **And V172 is the only lever that also attacks the grind.**
⇒ on both the operator's own stated axis and on predicted effect, **V172 is the better first flight.**
⊕ **V168 and its ladder remain cut and ready** as the alternative if V172's lag is the problem.

### ❌ A PROTECTED VARIANT WAS TRIED AND IS DOMINATED
A real-pole design constrained to hold 3–5 Hz nearer unity gives `poles [0.95916, 0.63265]`, 3 Hz
gain **0.9322** (vs V172's 0.8501) and 8.64 Hz **0.5716** (vs 0.4441) ⇒ **5.0x damping instead of
6.2x**. It buys back only **4 ms** of group delay (+26.1 vs +30.1 ms at DC) for a **1.2x loss of
damping**. **Dominated — not built.**

