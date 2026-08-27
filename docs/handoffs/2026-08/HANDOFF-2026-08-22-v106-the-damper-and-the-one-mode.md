# HANDOFF 2026-08-22 — V105 FLEW AND RELOCATED THE MODE · THE THREE GRINDS ARE ONE FREQUENCY · V106 IS A DAMPER

**ON THE CAR: V105** (route `a5`, verified from the wire, three independent legs).
**V106 BUILT, VERIFIED, UNFLASHED.** Nothing flashed. No CAN. No UDS. No openpilot file modified.

```
V106 image  78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a
V106 .rwd   e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc
builder     analysis-2020accord/builds/v80_v107/build_v106_tva.py   50/50 assertions
```

---

## 0. THE ONE-PARAGRAPH VERSION

V105's 25.5 Hz notch flew. It did not fix grinding or ratcheting, and measurement showed why: **the notch
was aimed at spectrum that is not there.** On V104 only **1.2 %** of the engaged low-speed 18–30 Hz power
sat inside its stopband. Worse, the mode **RELOCATED** rather than damping — peak 22.73 → 20.48 Hz at low
speed, **UP** at highway, with total 18–30 Hz power **conserved**. Meanwhile the operator corrected the
kit's taxonomy twice, and both corrections held up under measurement: **his three "grinds" are ONE
frequency (21–27 Hz) under three CONDITIONS**, and the ratchet is a **separate gain-driven ~8 Hz line
that does not exist on stock**. So V106 abandons filtering entirely and raises `gp-0x6b26`, the
acceleration-damping term — the only lever in the kit with a signed on-car precedent pointing this way,
the only one that reaches both bands, and the only one that provably cannot rate-limit the driver.

---

## 1. WHAT FLEW, AND WHAT IT MEASURED

### 1.1 Route `a5` IS V105 — settled from the wire, not from a doc
`STATE.md` said "V105 BUILT, VERIFIED, UNFLASHED". It flew. Three independent legs:
1. **427 wire ceiling** — 25 of 32,980 frames carry a code > 800, **max 946**; V103's packer has a
   structural ceiling of **800**. Arithmetically impossible on anything before V104.
2. **The cave alphabet** — `b6` duty **0.0000** on `a5` vs **0.9918** on `a4`. V104's `b6` is
   `|gp-0x6ada| ≥ |gp-0x6adc|`; V105's is the repointed `|gp-0x6b94| ≥ |gp-0x4f64|`. Excludes V104.
3. ⭐ **The filter's own transfer function, read off its own output.** CAN 427 carries `|gp-0x6b86|`
   with the same packer on both routes. Normalised (21–24)/(3–8) Hz lane ratio **0.4337 [0.3107, 0.6426]**
   against **0.3864** predicted from the two images' float bytes. **The coefficients are in force.**

⇒ **Verify the flown build from the wire, never from a doc.** Second occurrence in two sessions.

### 1.2 🛑 THE NOTCH WAS AIMED AT EMPTY SPECTRUM
Share of engaged <16 km/h 18–30 Hz **power** inside V105's own −20 dB region (24.5–26.5 Hz):

| | <16 km/h | 40–95 km/h | 55–70 km/h |
|---|---|---|---|
| STOCK 1× | 0.1075 | 0.1669 | 0.1426 |
| V103 6× | 0.0052 | 0.3762 | 0.3806 |
| **V104 6×** | **0.0123** | 0.4199 | 0.7082 |
| V105 NOTCH | 0.0282 | 0.1092 | 0.2478 |

**On V104 only 1.2 % of the low-speed band power was inside the stopband.** A *perfect* 25.5 Hz notch
could have removed at most ~1.2 % of the power in the operator's own grinding window. At highway it was
42–71 %, which is why the notch's shape IS stamped there (local minimum at 24.97 Hz) and absent at low
speed. **The two estimates that named 25.5 Hz are both discredited:** `a4`'s per-window peak regression
had **R² = 0.039** (its own handoff says so), and `f0` = 24.90 Hz is a `Re(Z)` zero-crossing, which was
never the spectral peak.

### 1.3 ⭐⭐ THE MODE RELOCATES — the result that killed the whole filter approach
Engaged, absolute spectra, `rate_f`, episode-bootstrapped argmax:
```
                 peak Hz    95% CI            peak PSD    |H_V105| at its OWN peak
<16 km/h  V104    22.73   [22.48, 22.98]        51.36            0.3039
          V105    20.48   [20.23, 21.98]        17.48            0.5442      <- 1.79x
55-70 km/h V104   25.97   [24.97, 26.97]         7.74            0.0467
          V105    27.47   [26.97, 27.72]        11.42            0.1795      <- 3.84x
```
**Peak shift −2.25 Hz [−2.50, −0.50] at low speed, +1.50 Hz [+0.50, +2.50] speed-matched highway — both
CIs exclude 0 — while total 18–30 Hz band power is CONSERVED (0.769 [0.548, 1.135], spans 1).**

⭐ **The discriminator:** `|H_V105|` evaluated **at each build's own peak** rose 0.304 → 0.544 (low speed)
and 0.047 → 0.180 (highway). **The mode moved to where the notch costs it less.** A stationary mode being
attenuated cannot produce that; a describing-function intersection sliding along the loop does exactly it.
⊕ Corroborated from an independent channel and analyst: `tq`-based peaks agree to **≤0.4 Hz at highway and
≤0.5 Hz at low speed**, same signed shift in both directions.

### 1.4 🛑 ROUTE `a5` CANNOT RESOLVE V105 FROM V104 ON ANY BAND
Two pipelines independently reported narrow-band "cuts". **Both were band-placement artefacts, and both
authors withdrew them.** All from the same drive, V105/V104, engaged <16 km/h:
```
band          ratio                  within-drive split-half NULL   verdict
18-22 Hz      1.414 [0.792, 2.723]   [0.311, 3.023]                 INSIDE
20.5-23.0     0.349 [0.159, 0.637]   [0.262, 3.758]                 INSIDE
21-28         0.236 [0.127, 0.432]   [0.344, 2.894]                 INSIDE
18-30 (THE    0.410 [0.240, 0.688]   [0.402, 2.479]                 INSIDE
 ENDPOINT)
32-45 placebo 1.115 [0.749, 1.845]   [0.492, 2.155]                 INSIDE
```
**The null spans 0.26–3.8. A single drive at this exposure cannot detect a 2.5× change in either
direction, on any band.** 18–22 goes UP 30 % while 20.5–23 goes DOWN 65 % — a window centred high sees a
cut, one centred low sees a rise, and the widest window sees nothing.
⇒ **THE STANDING LIMIT: no V105-vs-V104 band-power ratio is resolved.** What survives is everything that
is **not** a cross-drive ratio of band powers: the peak location and shift, `|H|`-at-own-peak, the
427-lane shape (normalised within-drive), the grind-#1 centre, the stopband power fraction, and the cave
duties.
⭐ **The transferable lesson: on this corpus, design the statistic to live INSIDE a drive.**

---

## 2. 🛑 THE OPERATOR CORRECTED THE KIT TWICE, AND BOTH CORRECTIONS HELD

### 2.1 "All 3 grinds are the same frequencies" — CONFIRMED
His words: *"I actually think all 3 grinds are the same frequencies. They just happen under different
scenarios. Grind #1 low speed like 5 mph (LKAS engaged), grind #2 low speed but hard manual turns during
LKAS engagement, grind #3 highway speeds (LKAS engaged)."*

The kit had them as **three different frequencies** — #1 18–22 Hz, #2 **44.9 Hz Q≈37 "NOT a harmonic of
#1"**, #3 **~46 Hz**. Measured, peak-searched **15–48 Hz**, stratified by HIS scenario definitions:
```
                  S1 (<10 km/h)    S2 (hard manual)   S3 (highway)
STOCK 1x            17.02 (no line)  17.02 (no line)   15.02 (no line)
V100 4x             20.03                -             26.04
V102 6x             22.03            22.03             25.04
V103 6x             21.03            21.03             24.04
V104 6x             23.03            23.03             27.04
V101 8x             23.03            23.03             25.04
V105 NOTCH          22.03            21.03             27.04
```
**38–48 Hz prominence: 0.3–4.9, median ~1.0 — indistinguishable from the local baseline in every one of
21 build×scenario cells.** RMS 18–26 vs 38–48 runs **5–15×** in every scenario. A per-window burst
detector (because the record describes grind #2 as a rare event a pooled spectrum would wash out)
**never puts a 38–48 Hz window above an 18–26 Hz one** — range 0.09–0.91.
**Harmonic PLV test: NULL** where runnable. 🛑 **And NOT RUNNABLE at highway** — 2 × 25–27 Hz = 50–54 Hz,
at or above `0x18F`'s **50.57 Hz Nyquist**. The only scenario where a 44–46 Hz label was plausible is the
one where this channel is structurally blind to the harmonic.
⇒ **He is right within 5–48 Hz. Restate the taxonomy as three CONDITIONS of one 21–27 Hz mode.**
⚠ **Ceiling: nothing above ~50 Hz is observable in the CAN corpus at all.** The only wide-band instrument
is `rawAudioData` (Nyquist 8 kHz), already measured NULL from 100 Hz to 8 kHz across six builds.

### 2.2 ⭐ "Applying torque kills the buzz" is really "applying RATE kills the buzz"
The pre-registered S2 mask (`|tq| ≥ 1000` **AND** `|rate| ≥ 40 °/s`) returned nothing. Four definitions:
```
S2a  |tq|>=1000 AND |rate|>=40   V103 PSD   0.193   prom  1.7    <- the rate floor KILLS it
S2b  |tq|>=1000, any rate                  51.689        33.5
S2c  |tq|>=500 AND 15<=|rate|<40           97.676        58.7    <- maximal
S2d  |ang|>=300 counts                      3.828        19.0
```
**At high torque with no rate condition the mode is fully present; adding `rate ≥ 40 °/s` extinguishes
it.** The corpus claim (16.12× [5.29, 41.29]) attributed the suppression to the wrong variable.
[EVIDENCE — same drive, same channel, same window, only the mask differs.]

### 2.3 "Why don't we put telemetry on the mode?" — the hole he found
**The mode record has NEVER been directly telemetered.** What the record actually had: a byte census
showing Honda ships 24 ≡ 26 identical (says nothing about which is which), plus the re-selector firing on
engagement transitions. **V93 was built specifically as a mode discriminator — via dose-RATIO inference,
not telemetry — and never flew.** `accord-cbe74-dose-measured-inert-wrong-mode-record` names the engaged
mode record as **the suspect** for V91/V92's nulls. **RULE 7 ("mode-proof or it is a bet") has been open
since.** V106 closes it — see §4.3.

---

## 3. THE RATCHET IS A SEPARATE, GAIN-DRIVEN LINE THAT DOES NOT EXIST ON STOCK

### 3.1 TWO MECHANISMS, sharing one driver [EVIDENCE — five independent lines]
1. **AM depth bounded at m < 0.05** on every 6× arm, by a **calibrated injection ladder** (not by a null).
2. Measured 6–12 Hz RMS is a **median 2.39×** the carrier across 78 matched cells — **~75× the entire
   demodulation budget** at m < 0.05, and linear AM puts **zero** energy at `f_m`.
3. The ~8 Hz line is **sharper and more prominent than the carrier** on several arms. A by-product is not
   sharper than its source.
4. **Beating excluded** — every candidate partner peak has prominence ≤ 2.2 against a 3–24 dominant line;
   8 of 24 cells have no candidate at all.
5. ⭐ **`E_line` is centred ABOVE 1 — a by-product cannot outgrow its source.**

### 3.2 ⭐ THE 6–12 Hz BAND SPLITS INTO A LINE AND A FLOOR, AND THEY BEHAVE DIFFERENTLY
Pre-registered decomposition (LINE 7.4–8.6 Hz, fixed; FLOOR = background × 31 bins):
```
                              median E (6x vs stock)   4-dose ladder beta (1x/4x/6x/8x)
LINE   7.4-8.6 Hz                  +1.559                    +1.525  => E_line  +1.136
FLOOR  broadband residue           +0.256                    +0.693  => E_floor +0.300
CARRIER 21-28 Hz                      -                      +1.390
CTRL   32-38 Hz (placebo)             -                      +0.395
```
- 🛑 **On STOCK the line power is EXACTLY ZERO in 3 of 4 highway cells.** The ~8 Hz line is **ours**.
- **The line is rate-gated exactly like the carrier** — LINE = 0 at 0–5 °/s even on a 6× build.
- ⇒ **`E = 0.406` "partial coupling" was a MIXING ARTEFACT** — one part gain-driven line, two parts
  gain-blind floor. 🛑 **Every 6–9 Hz band-RMS number in this kit's history dilutes the real effect by
  ~2–3× by pooling them.**

### 3.3 H3 (rate-scheduled governor-ceiling dropout) — RETIRED, by two independent channels
- `v105_b6` = **0.000000 across all 65,959 frames** of `a5`. The governor never clips.
- Independently: the reconstructed peak-follower never reaches the 223 °/s knee on any highway or mid arm
  of five routes (`frac ≥ knee` = 0.00000), and demand never co-occurs with a lowered ceiling.
**They fail in different directions and agree.** An intermittent ceiling dropout is not the source of
*"vibration comes in and out."*

---

## 4. V106 — BUILT, VERIFIED, UNFLASHED

### 4.1 THE EDIT — 12 bytes, pure cal, one CRC trailer
```
0xD7A5C  mode 26 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)
0xD7A6C  mode 27 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)
```
= **×3.0 of Honda's stock `(-9830,-5734,-1966)`**, computed from it by an integer multiple, never typed
as hex. **16 bytes differ from V105 total (12 payload + 4 CRC). ZERO unattributed bytes vs stock.**

### 4.2 WHY THIS LEVER
- 🛑 **The only signed on-car precedent in the kit points this way.** V93/V94 LOWERED it and the operator
  aborted: *"made the stuttering and grinding worse, by a lot… I decided it was not safe to drive."*
  The RAISE direction was never tested at 18–28 Hz — the "closed both directions" verdict rested on a
  **dose-verification** check at 6–9 Hz. **FALSIFIED ≠ INERT ≠ UNTESTED.**
- **Damping removes a describing-function intersection; a notch relocates it** (§1.3, measured).
- **It reaches BOTH bands** — cascade gain **1.478 @ 7.79 Hz** (the ratchet line) and **3.706 @ 21.73 Hz**.
- 🛑 **`H(f=0) = 0` EXACTLY.** The differencer `32·(1−z⁻¹)` is identically zero at DC for any `a1/a2/K`,
  so **a held 6× command sees nothing from this term at any multiplier.** That is a proof, not a
  measurement, and it satisfies the operator's *"don't rate-limit me"* constraint by construction.

### 4.3 ⭐ THE BUILD PROVES ITS OWN PREMISE — RULE 7 closed at zero cost
The carried cave rung **`b5` = ( |gp-0x6ae2| ≥ |gp-0x6b26| )** = FRICTION vs INERTIA. Operand B at
`0xC4B70` = `da94` = disp `-0x6b26` — **the exact cell this build doubles** (asserted in the builder).
```
b5 engaged duty COLLAPSES  => the car IS reading modes 26/27 engaged. Dose arrived.
b5 engaged duty UNCHANGED  => it is NOT. The V91/V92 mode-record suspicion CONFIRMED,
                              and the whole dose family is invalidated.
```
Baseline on `a5`: **0.2533 pooled, 0.4019 engaged <16 km/h.** **MANUAL is the built-in control** — the
engaged arm must move, the manual arm must not.

### 4.4 WHY 26/27 ONLY — the family has FOUR members
Read from the pointer table, each record base occurring **exactly once** as an LE32 literal image-wide:
```
slot0 0xCBED4 -> 0xD6A64  Y@0xD6A6C  mode 24  MANUAL   stock, NEVER DOSED
slot1 0xCBED8 -> 0xD7A44  Y@0xD7A4C  mode 25  ROLE UNCONFIRMED, stock, NEVER DOSED
slot2 0xCBEDC -> 0xD7A54  Y@0xD7A5C  mode 26  ENGAGED  x1.5 since V96  <- DOSED
slot3 0xCBEE0 -> 0xD7A64  Y@0xD7A6C  mode 27  ENGAGED  x1.5 since V96  <- DOSED
```
🛑 **`builds/v80_v107/build_v100_tva.py`'s `DOSE_FAMILY_Y` lists THREE.** (`builds/v80_v107/build_v105_tva.py` already had four — the
stale map is the V100 one, inherited by several builds.) **Mode 24 is MANUAL**: dosing it would be inert
for an engagement-conditional symptom and would change manual/LKAS-off feel instead. **Mode 25's role is
unconfirmed** (shares 24's primary selector `gp-0x67f6 = 0`, differs only in `gp-0x67e2`, untraced) —
dosing it is the V69/V70 trap. Both left alone, and **both dosed arms move by the same factor.**

### 4.5 SAFETY
🛑 **`0xC407E` NOT TOUCHED, still 511.** `FUN_00036c12` clamps `gp-0x6b26` to ±511 **before** the RULE-11
monitor `FUN_00036d74` compares it (trips above 512). **511 < 512 by one count ⇒ structurally untrippable
at ANY multiplier** as long as that cal stays put. V73 raised a *different* cell's clamp past its own trip
and **V74 and V75 both hard-faulted with a mid-drive total loss of assist.** Intact **by construction, not
by care.**
**Int32 overflow** in the `mid × 0x111` product: threshold on `|gp-0x6c2c|` = `503342400/29490` = **17,068**
against a corpus max of **5,320** — 3.2× margin, zero frames near it.

---

## 5. 🛑 THE DRIVE CARD — THE OPEN QUESTIONS THIS BUILD'S LOGS MUST ANSWER

**Score in this order. Q1 is the build's own premise and outranks the symptom score.**

### Q1 — 🛑 DID THE DOSE ARRIVE, AND IS THE MODE RECORD RIGHT? (the mode proof)
**Read `b5` duty, engaged and manual, stratified <16 km/h.**
- **PASS:** engaged duty falls sharply from **0.4019**; manual arm ~unchanged.
  ⇒ the car reads modes 26/27 engaged, the dose is in force, **RULE 7 closed**, and every earlier
  `0xCBE74`-family result becomes interpretable.
- **FAIL (duty unchanged engaged):** the car is **not** reading 26/27 engaged. ⇒ **V91/V92's nulls are
  explained**, this build is inert, and **V107 doses mode 24 instead.** That is a full-credit outcome.
- ⚠ `b5` is a comparator whose *other* operand (`gp-0x6ae2`, friction) is unchanged, so a duty shift is
  attributable to the dose. **This is within-drive and needs no cross-build contrast.**

### Q2 — DOES THE DAMPER CLIP, AND WHERE?
**Reconstruct `|gp-0x6b26|` clamp duty by rate bin.** Pre-registered from r77 at k=3:
```
engaged overall  ~0.0015      S1-like (his grind #1)  ~0.0100      S2a-like (hard turns)  ~0.0006
```
🛑 **If clipping appears it should appear in SCENARIO 1, ~26× more than in scenario 2** — the mirror of
the worry this build started with. **A clamp duty far above ~1 % in S1 means the dose is too large and
V107 should be ×2.0, not ×3.0.**

### Q3 — DID THE 21–27 Hz MODE MOVE, AND DID IT MOVE *DOWN IN AMPLITUDE* RATHER THAN *SIDEWAYS*?
🛑 **Score the PEAK LOCATION and the WIDEST band (18–30 Hz), not a narrow window.** Every narrow-band
claim this session was a placement artefact.
- **Damping predicts: peak frequency roughly UNCHANGED, peak PSD DOWN.**
- **If the peak MOVES again, damping is not what this term does** — and that would be a genuinely new
  result, because a notch moved it and a damper should not.
⚠ **A cross-build band-power ratio is NOT-CURRENTLY-DECIDABLE** against the 0.26–3.8 null unless the
effect is large enough to clear it on its own. **Say so rather than reporting a number.**

### Q4 — DID THE ~8 Hz RATCHET **LINE** MOVE? (not the band)
🛑 **Score the LINE (7.4–8.6 Hz, minus local background) separately from the FLOOR.** Pooling them
dilutes a real effect by 2–3× — which is what every previous 6–9 Hz number in this kit did.
The term's gain at 7.79 Hz is **1.478** at this dose, so a real effect is expected if the line is
loop-borne. **A null on the LINE with a confirmed dose (Q1 PASS) would be a strong negative** and would
push the ratchet out of this lever's reach entirely.

### Q5 — THE OPERATOR'S OWN REPORT — **THE PRIMARY READOUT, NOT A FALLBACK**
Specifically, in his own words, for **each of his three scenarios separately**, now that they are known to
be one mode: 5 mph engaged · hard manual turns under LKAS · highway. **And explicitly: does the wheel feel
heavier or slower in fast turns?**

### Q6 — DID IT COST HIM ANYTHING IN FAST STEERING?
🛑 **My earlier claim that the high-rate cost is zero is RETRACTED.** Measured on the wire, `|gp-0x6b26|`
**peaks at 40–100 °/s and COLLAPSES above 100** — it does **not** grow with rate:
```
|rate| deg/s     0-5    5-15   15-40   40-100   100-200   200-400
p99             62.4   113.6   147.2    181.6      72.7      92.1
MAX            292.8   302.4   302.4    318.4     190.4     104.0
duty >= 511    0.000   0.000   0.000    0.000     0.000     0.000
```
At 200–400 °/s the MAX is **104 counts**, not the 543 my model predicted (5.2× over-predicted), and the
rail is never touched. ⇒ **The raise ARRIVES in full at high rate — it is a real added opposition,
NOT free.** Scale at k=3: 104 → 312, still under the rail. **Score whether he reports the wheel feeling
heavier in fast turns, and cross it against the reconstructed high-rate `|gp-0x6b26|`.**

### Q7 — ⭐ WAS THE ×1.5 EVER IN FORCE? (a free check, and it may resize everything)
r78 (V91, ×1.5) vs r77 (V90, ×1.0) is an unread dose-response on this exact cell:
```
|rate| bin     r77 p99   r78 p99   ratio      (expected 1.50 if the x1.5 were live)
   0-5           62.4      32.0     0.51
   5-15         113.6      83.2     0.73
  15-40         147.2     162.6     1.10
  40-100        181.6     133.4     0.73
 100-200         72.7      79.6     1.09
                                 median 0.73
```
**Observed ~0.7–1.1 against an expected 1.5.** [BELIEF — cross-drive, and every cross-drive ratio in this
corpus fails its own split-half null.] **If V91's engaged ×1.5 was inert, V106 is not a ×2 step from
today — it is the FIRST REAL DOSE this cell has ever received engaged, and the operator should expect a
LARGER change than "double the damping" implies.** **Q1 settles this directly.**

### Q8 — HOUSEKEEPING READOUTS
- **`b6` should still read ~0.000000** (the governor comparator, unchanged). A non-zero reading would mean
  something else moved.
- **`b7`/`b4`/`b3` should be flat** to a few points vs `a5` (0.384 / 0.434 / 0.487).
- ⚠ **`b5` moved 0.2918 → 0.4019 engaged between `a4` and `a5` and nobody explained it.** If it moves
  again in the *wrong* direction, that confounds Q1 — check it before concluding.
- **Fault census:** 0 sentinels, DTC bit2 duty 0.0, `STEER_STATUS` constant, CONFIG_VALID 1.0.

### Q9 — EXPOSURE THE DRIVE MUST SUPPLY
`a5` gave **87.0 s engaged <16 km/h in 20 runs, only 6 episodes ≥ 4.2 s and 2 ≥ 8.2 s**, and **2 episodes**
at highway with `|rate| ≥ 15`. **That is the root cause of the 0.26–3.8 null.**
🛑 **The cheapest fix needs no build: an ALTERNATING drive — ~30 s engaged / 30 s manual at 5–15 km/h,
same road, same session.** It removes the between-drive variance that defeats every cross-build ratio,
and it removes the one-stock-route confound the whole corpus rests on. **This has been open item #12
since the V105 handoff and is still not done.**

---

## 6. WHAT WAS KILLED THIS SESSION, AND WHY (so none is re-proposed)

| lever | verdict |
|---|---|
| **Biquad re-centre to 21.7 Hz** | The mode RELOCATES; a point-null slides it. And `b1` alone makes pole and zero nearly coincident — a four-float redesign, not one float |
| **Biquad as a LEAD compensator** | 🛑 **STRUCTURALLY IMPOSSIBLE.** The numerator `c4(1+b1z⁻¹+z⁻²)` is palindromic ⇒ the product of its roots is exactly 1 ⇒ any complex zero pair is **on the unit circle**. Exhaustive grid (zero 5–25 Hz × pole to 35.5 Hz × r 0.10–0.98): **zero configurations** deliver in-band lead while staying ≤ 0 dB above 28 Hz |
| **Wide-stopband notch (candidates A/B)** | **DESIGNED, BANKED, NOT SHIPPED.** Candidate B (pole 14 Hz, r 0.90, zero 22.0) gives −12 to −28 dB across 18–24 Hz and halves the ring to 43.7 ms — genuinely better than V105. **Rejected on relocation risk into 28–35 Hz, a band never characterised on this car** |
| 🛑 **"Lower the pole radius to widen the stopband"** | **WITHDRAWN BY ITS OWN AUTHOR.** At fixed DC unity, lowering `r` creates a resonant peak: `max|H|` 1.000 → 1.124 → 1.956 → **3.217** at r = 0.80, landing gain on grind #1's lower shoulder. **A future session re-deriving this would build an amplifier.** Widen by moving the POLE DOWN at r ≈ 0.95 |
| **`0xC61F6` rate-lane deadband raise** | **TESTED AND REJECTED** (not never-tried). D = 3 is 210–1400× below the lane's own excursion. And it is **SUBTRACTIVE** — a fixed tax of D counts at every amplitude above the knee, i.e. **literally Coulomb friction**, which is disqualified by the operator's own constraint. ⊕ Also: r24's `Re(Z)` is **DAMP at 12–31 Hz**, so raising D would remove a damper |
| **`gp-0x6b26` REDUCE** | Already flown as V93/V94; operator aborted as unsafe |
| **`0xC40BC` Coulomb knee** | Falsified both directions on-car (6000 on V85/86/86b; 300 on V99), and **saturated at the mode's own rate amplitude** (B/δ ≈ 2.8–7.5) |
| **PID `Kd`** | Virgin, but **even the SIGN of the needed change is not derivable from firmware**, and three drives disagree at this crossover. The `we-would-not-be-able-to-tell` case |
| **Relocating the 6× outside the loop** | 🛑 **It is already outside.** Mason's gain formula: `gp-0x6b4c` is a pure source node, so it never enters `Δ(z) = 1 − ΣL(z)` regardless of injection count. Confirmed by a fresh 0/1874 `gp-0x6b98`-read null on its home function. **There is no relocation to perform** |
| **Widening Lever B's gate** | The gate is **LIVE at creep** — `gp-0x6807`'s lower speed bound is `0xC62EA` = **0** on V104/V105 (V53 removed it), so no vehicle speed can fail it |
| **More r24/r26 dose** | The lane is at its **historical ceiling** — V67/V68's combination, exactly what V104/V105 carry, already produced the **best recorded grind-#1 median in the kit (109 vs stock's 879)** |
| **Self-interference cancellation** | Three independent lines agree it is a NO-GO: the byte scan (2026-08-06), the partial-coherence refutation (2026-08-22), and the architectural argument that a torsion bar measures differential twist |

---

## 7. THE ARCHITECTURAL RESULT — and why the operator's own framing is reachable

His mandate: *"sharp openpilot-controlled steering angle without all the noise and vibration due to the
feedback from the EPS motor driven by LKAS into the steering wheel… If we need to completely rewrite this
firmware, we will get there."*

### 7.1 A self-torque estimate ALREADY EXISTS, and it is on the wrong side
`FUN_0003a382` forms **`iVar30 = gp-0x4f60 − clamp(gp-0x6ad6)`** — **raw torsion bar minus reference.**
MODEL (`gp-0x6bfc`, built from `gp-0x6b98`, the delivered motor command) reaches the loop **only** through
`iVar6` → `gp-0x6b70` → `FUN_00037fe6` → `gp-0x6ad6`. ⇒ **it shapes what the PID is told to TRACK, never
what it is told it is tracking FROM.** *"Already doing this, and doing it badly"* is the correct answer.

### 7.2 ⭐ AND IT SELF-CANCELS AT DC, BY CONSTRUCTION
Two matched pathways from `gp-0x6b4c` into `iVar6`:
```
(a) Stage-1 -> gp-0x374c -> iVar6                    d(iVar6)/d(gp-0x6b4c) = +2.578
(b) aggregator -> gp-0x6b98 -> MODEL -> iVar6                              = -2.578
    REQUEST (the third term) is a HARD-CODED LITERAL ZERO for the LKAS slot
```
**Identical `polarity(gp-0x6752)` and identical `0xC6468`/1024 in both, with Stage-1's ×16 then >>4 a
designed no-op on that factor.** ⇒ **`d(iVar6)/d(gp-0x6b4c) ≈ 0` to first order — a DESIGNED cancellation,
not a coincidence.** 🛑 **This closes the DC/mean-shift mechanism at NULL. It does not close the
AC/describing-function question at 18–28 Hz, which remains genuinely open.**

### 7.3 THE STAGED PATH — and the step that must come first
1. **STAGE 1 (telemetry only, GATE 1 trivial, GATE 2 vacuous):** put **`gp-0x6bfc`** (MODEL) on the wire
   and compare `gp-0x6b98 → tq` (the real plant) against `gp-0x6b98 → MODEL` (the estimate) across
   18–30 Hz. 🛑 **MODEL's command branch is already at −5.2 to −8.2 dB and lagging 77°–92° in-band before
   any sampling.** Whether that matches the real mechanical plant is the whole question.
2. **STAGE 2 (cal):** rebalance `0xC63AA` to un-cancel the command-specific part. GATE 2 **not** vacuous.
3. **STAGE 3 — STOP CONDITION.** If Stage 1 is unfavourable, **do not proceed.** A correction built on a
   wrong model injects a wrong-shaped signal.
4. **STAGE 4 (cave, highest risk):** subtract a rescaled MODEL from `gp-0x4f60` before the error line.
   🛑 **This is the exact topological class that bricked V48B** (a notch on `gp-0x4f60`/error-term, ahead
   of fan-out, in the always-on base-assist loop — it bricked **on startup, parked, no LKAS command, full
   authority oscillation**). GATE 2 here is the thing that failed, not a formality.

### 7.4 🛑 THE CAVE RISK MODEL WAS WRONG AND IS NOW CORRECTED
The claim *"every flown cave is a read-only tap at ONE site; a 1 kHz cave has zero precedent"* is
**RETRACTED by its own author.** A kit-wide scan found **two** hook addresses, not one:
**`0x3AC78` is a task-1, 1 kHz trampoline hook INSIDE `FUN_0003aa2c` (the aggregator itself) and it FLEW
CLEAN on V39.** And **V48B's own postmortem explicitly exonerates the clock rate** (*"the biquad is
correctly clocked at fs=1000 — this was a worry and it is clean"*); it died of a **RAM collision** plus an
**open-loop magnitude check against the wrong crossover**.
⇒ **Corrected: a task-1 trampoline is PROVEN. What has never flown is a STATEFUL filter allocating NEW
persistent RAM into a live signal path.** Materially smaller risk surface than reported.

### 7.5 CAVE GROUNDWORK COMPLETED (reusable regardless of what the next cave computes)
- **Hook `0x36cca`** cleared by a real **pcode liveness sweep**: live-out = `{gp, tp, r6, r16}`; r7–r15,
  ep, lp all free scratch. ⊕ Hook `0x346a4` (Honda's own damper) swept too: **9+ free scratch, only r8
  live-in**.
- **RAM census on 8 cells, 3 methods** (disp16 with the `st.w`/`ld.w` LSB-discriminator trap, the 6-byte
  extended form, and `movhi`+register-indirect), every extra raw hit adjudicated to a false positive.
  Five donor cells (`gp-0x6d08/6d04/6d00/6de8/6de4`) confirmed 1-writer/0-reader.
- **Tick ordering confirmed** — `FUN_0003b66a` runs before `FUN_00036c12` in the same tick, so a cave can
  reuse those cells with **no neutralisation edit**.
- 🛑 **Static clearance is still NOT sufficient.** `gp-0x1500` passed both static methods and bricked via
  a runtime-computed index into an I/O mailbox — a pattern no byte scan can enumerate. **A live probe is
  the final gate.**

### 7.6 THE TELEMETRY CEILING, NOW FULLY MAPPED
**Only three IDs cross the gateway. `0x14A` = 0 free bits · `0x18F` = 10 · `0x1AB` = 5. Fifteen bits
total, permanently.** (The `0x1AB` five are new — found by decompiling `FUN_00021864` rather than
inheriting "already spoken for".) A **byte-exact spec** exists for a full-precision `|gp-0x6b26|`+sign
channel on `0x18F` at hook `0x55D50` (byte-stock on every build ever; 1048 free cave bytes verified at
`0xC4BD8`): `|gp-0x6b26| ∈ [0,511]` is **exactly 9 bits + sign = exactly 10** — a perfect fit with **zero
quantiser**. **Not shipped on V106** because the stub is an instruction-level spec, not assembled bytes.
⊕ Sampling checked by simulation: 100 Hz / 21.73 Hz = **4.60 samples/cycle**, a non-integer ratio, so the
sampling phase rotates and **duty bias is indistinguishable from zero even at 20 samples** — but variance
on a 4-cycle fragment is −40 %/+15 %. **Pool bursts; never score one fragment.**

---

## 8. RETRACTIONS — every one, with reasoning attached

| # | retraction |
|---|---|
| R1 | 🛑 **"Lower the pole radius to widen the stopband"** — creates a resonant peak, `max|H|` up to **3.22** at r = 0.80. Withdrawn by its author (§6) |
| R2 | 🛑 **All Q/linewidth numbers VOID.** The −3 dB estimator returns **BW 0.749 Hz / Q 36.2 on WHITE NOISE** at 4 s — above every measured value (19.1–33.5). Same family as `q_of` returning 79.00 on noise. **Second recorded instance; treat as a standing property of narrowband Q on short episodes** |
| R3 | **"V105 worked — a 3× cut"** — the bootstrap resampled 75 %-overlapped spectrogram frames. Redone on contiguous blocks with a within-drive null: **inside the null on every band** |
| R4 | **"The biquad lane is a parallel disturbance, not loop gain"** — rested on the same window; the agreement was between a prediction and a number drawn from a 0.26–3.8 distribution. Withdrawn |
| R5 | 🛑 **The surrogate nulls ABSORB the signal.** Phase-randomising a carrier band leaves carrier and sidebands still spaced `f_m` apart. Measured: a known **100 %** modulation scores 16.84 against its own null's p95 of **22.18** = "miss". **Voids every `hf_lf_04`/`hf_lf_06` p-value on T1/T2** |
| R6 | **`hf_lf_04`'s envelope test was BANDWIDTH-BLIND** — a 4 Hz band cannot show an envelope line above ~4 Hz, so its universal 3.12 Hz bottom-bin peak was a blind instrument, not a null |
| R7 | **The entire T3/partial-regression family is NON-DIAGNOSTIC** — calibrated against synthetics, and then **STOCK matched the ONE-mechanism synthetic too**, with a `b_car` as large as every 6× build's. That is the statistic's null level |
| R8 | **The stock bicoherence cell (b² = 0.2820, "ratio 33×")** — fails family-wise correction on all 13 arms; it sits at the **92.5th percentile of its own map** |
| R9 | 🛑 **My "the 6× is inside the loop, relocate it" hypothesis** — refuted by Mason's gain formula (§6) |
| R10 | 🛑 **My "grind #1 ↔ 21–28 Hz is inherited, not established"** — the operator corrected it and the ladder confirms him: four operator-scored rungs, monotone, with his unprompted *"between 4× and 8×"* reproduced by the instrument at 63 % on a log scale |
| R11 | 🛑 **My "V105 delivered −24.1 dB and he felt nothing"** — that was `|H|` at 24.9 Hz where almost nothing lives. At the actual mode `|H(21.73)| = 0.4150 = −7.6 dB`. **The honest statement is "we attenuated it ~8 dB and he felt nothing", which does not rule out a real attenuation being felt** |
| R12 | 🛑 **My "the high-rate cost is zero because both K saturate"** — refuted on the wire (§5 Q6). The term **peaks at 40–100 °/s and collapses above 100**; MAX at 200–400 °/s is **104 counts**, not 543 |
| R13 | 🛑 **My "dose all three modes symmetrically to restore Honda's 24 ≡ 26 identity"** — mode 24 is **MANUAL**; dosing it is inert for an engaged symptom and changes manual feel instead |
| R14 | **"The 4× rung has an operator report"** — it does not. `docs/archive/arc-maps/_v101_arc_map.md`: *"Whatever the operator felt on route `0x85`…"* |
| R15 | **A2's clamp-crossing estimate 11.62/17.40/27.52 %** → **0.088/1.563/9.969 %** (self-corrected; the single-frequency proxy over-weighted low-frequency content the cascade passes at 1.2 rather than 8.8) |
| R16 | **"`0x1AB` is already spoken for"** — self-corrected; 5 genuinely free bits |
| R17 | **"Zero 1 kHz cave precedent"** — self-corrected (§7.4) |
| R18 | **The "sign points the wrong way" claim** on `gp-0x6b4c` → `iVar6` — withdrawn when the second of two matched ±2.578 pathways was decompiled. **The corrected result (≈null at DC, by construction) is STRONGER than the original claim and must not be re-read as "unresolved"** |
| R19 | **`32–45 Hz is NOT a valid placebo for V105`** — the lane's own V105/V104 response there runs 0.27 → 0.955. Every placebo-corrected number is an over-correction; raw and corrected bracket the truth |
| R20 | **V104's biquad is not "×1.85 flat"** — `a1 = −1.53719997, a2 = 0.634620011, b1 = −1.88080001, c4 = 1.51202345` ⇒ pole 42.345 Hz r = 0.7966, zero 55.225 Hz, H(0) = 1.850063, drooping to 0.712 at 42.3 Hz |
| R21 | **"42 Hz gets 1.75× worse"** was **vs STOCK, not vs V104** — V105/V104 at 42.3 Hz is **0.955, essentially unchanged** |

---

## 9. OPEN ITEMS — each with what closes it

| # | item | what closes it |
|---|---|---|
| 1 | 🛑 **RULE 7 / the mode record** — never directly telemetered; the suspect for V91/V92's nulls | **V106's `b5` readout (Q1).** Or the full-precision `gp-0x6b26` channel |
| 2 | 🛑 **Exposure** — `a5` gave 87 s engaged <16 km/h, 2 highway episodes; the 0.26–3.8 null follows | **The alternating drive** (~30 s on / 30 s off at 5–15 km/h, same road, same session). Open since the V105 handoff |
| 3 | **V105's own peak is NOT localised** — 20.48 vs 22.13 from two pipelines; the residual looks bimodal | A spectrogram-**ridge track** inside each engaged episode — **runnable on existing data, never done.** If the peak HOPS between ~20.5 and ~22.1 Hz it is two states, not one broad line |
| 4 | **Linewidth UNRESOLVED** — BW tracks ENBW down at every window length and never plateaus; only `≲1.0 Hz, Q ≳ 21` survives as a LOWER bound | One engaged low-speed episode ≥ 30 s at steady 15–40 °/s. ⊕ Or a **ring-down** estimator on burst terminations — the only width estimator that ever passed its control |
| 5 | **Mode 25's role** — shares 24's primary selector, differs only in `gp-0x67e2` (untraced) | Decompile `gp-0x67e2`'s producer. Gates any future 24/25 dose |
| 6 | **Was V91's engaged ×1.5 ever in force?** r78/r77 ratio ~0.73 against an expected 1.50 | **Q1.** Or the same rate-binned read on another dose-differing pair |
| 7 | **The AC/describing-function question at 18–28 Hz** — the DC version is closed at null (§7.2) | Stage-1 MODEL telemetry, or a first-principles DF using the Stage-2 LERP's real flash knots |
| 8 | **`FUN_00055c42`'s indirect-dispatch timing** — zero literal callers; dispatched via the pointer table at `0xB72D0`. **Inherited from a 2026-07-07 memory** | Walk `FUN_0001d68e`'s three callers (`0x1d904`/`0x1db32`/`0x1dc8e`) to their roots. **Matters only for phase/coherence, not dose or duty** |
| 9 | **`cal(0xC6382)` / `gp-0x381c`** — *"the one unsized damping candidate"*; its LERP at `tp+0x78fc..0x790c` was never decoded | A trace. **It is not a lever until then** |
| 10 | **DITHER — named as the highest-value experiment in the V84 handoff, NEVER BUILT** | A design pass. It is the classical fix for a nonlinearity-sustained limit cycle |
| 11 | **`0xC61DA` blend-fraction residual** — an anti-windup ramp fraction, state-dependent, not a flat scalar | Trace `iVar27`/`iVar38` and the `0xC6A0C–0xC6A14` LERP |
| 12 | **The `r12`/`0x36c84` pcode anomaly** — zero DEF where the disassembly reads `ld.h 0x4[r14],r12`; four real CFG edges fixed and it persisted | Re-walk that loop's branch edges **against the raw pcode block list**, not hand-transcription |
| 13 | 🛑 **Static GATE-1 cannot rule out a computed pointer** on an unrecognised base — the `gp-0x1500` class | **A live on-car probe.** Not more static scanning |
| 14 | **The nonlinear-demodulator escape route** — dry friction at the rack could in principle convert 5 % AM into a line 2.4× its carrier | **Needs a MECHANISM, not a statistic.** A statistical re-run will not close it and should not be commissioned |
| 15 | **`b5` moved 0.2918 → 0.4019 engaged between `a4` and `a5`, unexplained** | Trace whether `gp-0x6ae2`/`gp-0x6b26` sit downstream of `gp-0x6b86`. **Confounds Q1 if it recurs** |
| 16 | **427 field headroom ~8 %** — `a5` max 946 of 1023 | Move `0x55E10` (`sar 4` → `sar 5`) on any build that raises that lane |
| 17 | **`studies/ledger/ledger_v38_to_v100_bytes.py` was edited IN PLACE** against its own "kept, not overwritten" convention, and covers only to V103 | Rename it and extend to V104/V105/V106 |
| 18 | **`BUILD-LINEAGE-CATCHUP-V76-V100.md` still says V100 is "BUILT AND NOT FLASHED"** — it flew as route `0x85` | A close-out edit |
| 19 | **`.gitignore` eats every `.log` and `_r??_*.json`** | 26 artefacts force-added this session. **Any future analysis must `git add -f` or its tables exist only on one machine** |
| 20 | **Nothing above ~50 Hz is observable in the CAN corpus** | Only `rawAudioData` (Nyquist 8 kHz), already NULL 100 Hz–8 kHz across six builds |

---

## 10. PROCESS NOTES — what actually worked

1. ⭐ **Nine agents, and the best results were self-corrections.** The `gp-0x6b26` raise exists because an
   agent overturned its own kill; the clamp veto lifted because another refuted the orchestrator's
   arithmetic on the wire; mode 25 surfaced because an agent scanned the ROM row table instead of trusting
   an inherited map. **Every one of R1–R21 that matters came from someone checking their own output.**
2. 🛑 **Run the control before the measurement.** Five claims died to controls this session — including
   two of the orchestrator's. `q_of` returns 79 on white noise; the −3 dB estimator returns Q 36 on white
   noise; the surrogate null absorbs the signal it is meant to destroy.
3. 🛑 **A control that can PASS for the wrong reason is as dangerous as no control.** The "stock's CI must
   be wider" control passed by pinning to a band edge.
4. ⭐ **Design the statistic to live INSIDE a drive.** Every cross-drive number died to its own null; every
   survivor — peak shift, `|H|`-at-own-peak, the 427-lane shape, the rate-bin ordering — is within-route.
5. **The operator corrected the kit twice and was right twice.** His lived experience outranks analyst
   reconstruction, and it is written into the doctrine for a reason.
6. **A virgin cell is not automatically an opportunity.** `0xC63AE` and `0xC6200` are virgin *because* two
   independent tracers already flagged them as flatten-into-relay traps. **Check why before treating
   virginity as a green light.**
