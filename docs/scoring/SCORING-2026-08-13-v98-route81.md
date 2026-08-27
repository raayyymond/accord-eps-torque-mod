# SCORING — V98, route `0x81`, 2026-08-13

**The first COMPARATOR probe in the kit. It answered.**

Artifacts: cache `analysis-2020accord/_scratch/cache/r81/` · extractor `rlog-tools/decode/extract_r81.py` ·
scorer `rlog-tools/score/v98_r81_score.py` · outputs `analysis-2020accord/sessions/v99/v98_r81_score.{json,log}`.
Rlogs: `75604b0a432fdc89_00000081--c7103d2cb4--{0,1,2}--rlog.zst`.

**Operator's own description of the drive, verbatim:**
> *"Mostly parking-lot speed creep with the demonstration of LKAS-engaged grinding and stuttering.
> At the end, I demonstrate how smooth LKAS engagement really should be (with LKAS disengaged)."*

---

## HEADLINE — five findings, in the order they should change the next build

1. ⭐ **THE COMPARATOR ANSWERED, AND THE ANSWER IS `(b6,b5) → REQUEST IS THE SMALLEST ARM;
   MODEL AND ACTUAL ARE COMPARABLE.`** Engaged joint duty `(0,0) 0.5765 · (1,0) 0.4235 ·
   (0,1) 0.0000 · (1,1) 0.0000`. **`b5` = 0.0000 on all 6,591 engaged frames.** ⇒ the LKAS
   REQUEST arm `gp-0x6bfa` is minor; `b6` at 0.4235 is the pre-registered **CANCELLATION regime**.
2. 🛑 **THIS REFUTES THE STANDING "THE ARMS MAY BE WILDLY UNEQUAL" BELIEF.** Both V89's K1
   (`0xC40D2`, MODEL) and V97's pole (`0xC63AC`, ACTUAL) sit on **live, comparable** arms.
   **Neither null is a REACH failure.** The one-mechanism explanation of both nulls is dead.
3. ⭐ **THE SYMPTOM IS INSTRUMENTED, IN THE OPERATOR'S OWN REGIME, WITH HIS OWN CONTROL.**
   6–9 Hz column torque, engaged / manual, standardised on speed × |wheel rate|:
   **7.12× [3.27, 16.09]**, against a 0.5–3 Hz null of 0.89 and a 35–45 Hz negative control of 1.43.
   Present in the **steering ANGLE** too (2.66× [1.69, 4.33]) and **absent from openpilot's command**.
4. ⭐ **WITHIN THE SYMPTOM, `b6` FALLS.** Partial Spearman(log 6–9 Hz, b6 duty | speed, |rate|,
   press) = **−0.321, block-permutation p = 0.0050**, null 95 % |r| ≤ 0.221. `b4` and `b7` are
   null on the identical test. ⇒ **when the grinding is loudest, the ACTUAL arm is swelling
   relative to the MODEL arm.**
5. ✅ **`b3` CLOSED A MULTI-SESSION BLOCKER: `gp-0x6752 < 0`, constant, 0 transitions in 17,982
   frames.** ⇒ `b4 == 1` ⇔ the six-lane sum is **POSITIVE**.

---

## D0 — HEALTH AND IDENTITY

### Identity: **V98 IS ON THE CAR** [EVIDENCE]

`0x14A` byte7[7:6] histogram is a **single code**: `{2: 17,983}`. Duty **1.000000**.

| build | byte7[7:6] | mechanism |
|---|---|---|
| ≤ V91 | 0 | never writes byte 7 — structural |
| V96 / V97 | 1 (and 3) | `mov 0x1,r7` — structural |
| **V98** | **2** | `mov 0x2,r7` @ cave +0x82 |

POS-1 passes at 100.0000 %. This is the first **single-frame** build identity since V96, and it
closes the "V96-or-V97" ambiguity class that cost a session.
⚠ Residual, as the build itself stated: **V92 can also emit 2.** V92 is a shelf artefact, not a
flash candidate, and its cave writes a different byte-4 map — but no structural separation from
V92 is claimed here.

**Method:** `raw14_b7` from the 0x14A byte-7 pass-through tap, asserted **elementwise identical**
in its byte-4 column to the extractor's own `raw14_b4` (the assertion kills the run rather than
mispairing), then indexed through `row2raw14` (lead = 1, `constant_lead_holds = True`).

### Health: **FAULT-FREE** [EVIDENCE]

| check | value | verdict |
|---|---|---|
| `0x7FFF` sentinels on `0x14A` | **0** | ✅ |
| `0x7FFF` sentinels on `0x18F` | **0** | ✅ |
| `CONFIG_VALID` duty | **1.00000** | ✅ |
| `OUTPUT_DISABLED` duty | **0.00178** | ✅ (route 80: 0.0009) |
| DTC bit 2 duty | **0.00000**, 0 transitions | ✅ |
| `STEER_STATUS` | `{0: 17,981, 3: 2}` | ✅ two frames of the low-speed code |
| onroadEvents | 1,086, all normal (pedalPressed 448, steerOverride 329, wrongGear 84…) | ✅ **zero immediateDisable** |
| `0x1AB` COUNTER +1 | 99.97 % | ✅ |
| `0x1AB` CHECKSUM distinct | 16/16 | ✅ |

**POS-2 — 427 non-degenerate:** **251 distinct codes**, nonzero 98.60 %, max 251,
p50/p95/p99 = 98/216/238, **0.000 % saturation**. Pre-registration was ≥20 codes and p99 ≥ 8. PASS.

🛑 **THE PRE-REGISTERED CONVENTION BREAK HELD.** `byte4 field = (byte4>>3)&0x1F` is **EVEN on
100 % of frames** — alphabet `{2, 8, 10, 12, 16, 24, 26, 28}`. That is `b3 == 0` on every frame,
which is **the finding, not a fault**. Liveness lives on byte 7 and byte 7 read clean.
*Without the pre-registration a scorer pulls a working build here.*

### Exposure and the matched pair

181.5 s · 3 segments · 17,982 rows at 99.06 Hz. **Engaged 65.9 s (36.65 %) in 3 episodes.**

```
seg0   t   0.00 ..  61.52 s   33.6 % engaged   v p50 4.14 km/h
seg1   t  61.53 .. 121.59 s   76.3 % engaged   v p50 6.46 km/h   <- the symptomatic creep
seg2   t 121.60 .. 181.52 s    0.0 % engaged   v p50 6.93 km/h   <- the LKAS-OFF DEMONSTRATION
```

| episode | window (s) | dur | v p50 | \|rate\| p50 | press |
|---|---|---|---|---|---|
| ENG ep0 | 25.20 – 44.73 | 19.5 s | 4.94 km/h | 22.1 °/s | 23.8 % |
| ENG ep1 | 60.97 – 90.73 | **29.8 s** | 5.57 | 24.4 | 35.9 % |
| ENG ep2 | 93.98 – 110.56 | 16.6 s | 9.17 | 30.2 | 40.0 % |
| **MAN demo** | **110.57 – 181.52** | **70.9 s** | 7.66 | 60.7 | 65.9 % |

⭐ **THE MATCHED PAIR IS BACK-TO-BACK.** The last engaged episode ends at t = 110.56 s and the
LKAS-off demonstration begins at t = 110.57 s — **the same lot, the same tyres, the same tyre
pressures, seconds apart, not minutes.** This is the within-route positive control the kit has
never had. Engaged ≥ 20 km/h: **0.0 s** — this is a pure creep route, as designed.

---

## D1 — THE COMPARATOR

### The pre-registered `0x7FFF` latch exclusion: **ZERO FRAMES EXCLUDED** [EVIDENCE]

`427 == 1023` on **0 of 8,991** `0x1AB` frames (max code observed = **251**). ZOH-mapped onto the
`0x14A` grid: **0 of 17,982 rows excluded.** The observer plausibility latch has now **never fired
in 96,414 frames** across routes 7e / 7f / 80 / 81 — a fourth independent replication.
**Every b6 duty below is therefore the raw duty, uncontaminated.**

### The joint table [EVIDENCE]

```
ENGAGED, n = 6,591 frames (65.9 s)

  (b6=0, b5=0)  0.5765     |MODEL| <  |ACTUAL|  and  |REQUEST| < |ACTUAL|
  (b6=1, b5=0)  0.4235     |MODEL| >= |ACTUAL| > |REQUEST|
  (b6=0, b5=1)  0.0000
  (b6=1, b5=1)  0.0000
```

**Reading it against the build's OWN pre-registration, word for word:**

- **`b5` duty 0.0000 engaged** ⇒ *"the REQUEST arm is the small one."* The 11-slot LKAS request
  aggregator `gp-0x6bfa` **never exceeds** the six-lane ACTUAL arm on any engaged frame.
  It is not structurally railed: it fires 38 times in manual/hands-off (duty 0.0077) and always
  jointly with `b6 = 1`, i.e. only when `|ACTUAL| ≈ 0`. **All four codes are reachable; three of
  them just have essentially zero duty here.**
- **`b6` duty 0.4235 engaged** ⇒ the pre-registered *"`b6 ~ 0.5` — the arms are comparable ⇒ both
  live, and the residual is a genuine difference of two similar numbers: the CANCELLATION regime."*
  0.4235 with SE 0.031 sits squarely there. It is **not** → 1 and **not** → 0.

### The pre-registered SE, computed from the bits' OWN measured correlation time [EVIDENCE]

| bit | τ (ACF integral to first zero) | T engaged | n_eff | p | SE | 95 % CI |
|---|---|---|---|---|---|---|
| **b6** | 0.254 s | 65.9 s | 259 | 0.4235 | 0.0307 | **[0.363, 0.484]** |
| b4 | 0.375 s | 65.9 s | 176 | 0.4465 | 0.0375 | [0.373, 0.520] |
| b7 | 0.379 s | 65.9 s | 174 | 0.5239 | 0.0379 | [0.450, 0.598] |

The build pre-registered τ ∈ [0.125, 1.0] s; **the measured τ is 0.25–0.38 s, inside that range**,
and the achieved exposure (65.9 s, 3.8× the 17.2 s the build budgeted for) makes the ordering
decisive with room to spare.

### Stratification [EVIDENCE]

```
stratum                          n      b6      b5      b7      b4      b3
ALL                          17982  0.6646  0.0022  0.6010  0.4048  0.0000
ENGAGED                       6591  0.4235  0.0000  0.5239  0.4465  0.0000
  + override (hands-on)       2198  0.4727  0.0000  0.4686  0.5255  0.0000
  + hands-off                 4393  0.3988  0.0000  0.5516  0.4070  0.0000
MANUAL                       11391  0.8041  0.0034  0.6456  0.3807  0.0000
  + hands-on                  6479  0.9756  0.0003  0.6240  0.3851  0.0000
  + hands-off                 4912  0.5778  0.0075  0.6741  0.3748  0.0000
seg1 ENGAGED                  4581  0.4410  0.0000  0.5080  0.4235  0.0000
seg2 MANUAL (LKAS-off demo)   5992  0.8126  0.0002  0.7123  0.4217  0.0000
ENG  v 5-10 km/h              4491  0.4246  0.0000  0.4785  0.4631  0.0000
MAN  v 5-10 km/h              3894  0.7273  0.0003  0.6287  0.4471  0.0000
ENG |rate|  0-5  deg/s         894  0.4911  ...
ENG |rate|  5-25               2469  0.3556  ...
ENG |rate| 25-60               1781  0.3268  ...
ENG |rate| 60+                 1447  0.6164  ...
```

🛑 **CORRECTED 2026-08-13 (later), from `scorer-v99`'s completed flight score — this line used to
read only "It survives speed matching... so it is not a speed artefact" and stop there. That
robustness check was insufficient: the confound is on WHEEL RATE, not speed, and speed-matching alone
does not catch it.** **`b6` has a large ENGAGEMENT CONTRAST: raw 0.4235 engaged vs 0.8041 manual —
but this OVERSTATES the true effect by ~22%.** Manual exposure on this route is **1.84× more
60+ °/s weighted than engaged** (b6 is itself strongly rate-dependent — 0.49→0.36→0.33→0.62 across
the four rate bins below), which biases the raw contrast in exactly the direction that manufactures
it. Matched on a 4|rate|×6 speed grid (`score/v99_r82_matched.py` §C, 5.12 s block bootstrap, 15 cells,
96.0% engaged / 83.4% manual exposure surviving): **matched contrast engaged 0.4543 vs manual
0.7493, diff −0.2950 [−0.4099, −0.1727].** **Quote the matched figures, not 0.4235-vs-0.8041.**
🛑 **This is a correction to the MAGNITUDE, not the finding — the CI still excludes zero by a wide
margin, so the conclusion below stands, just smaller than stated.**
The sharpest cell is **MANUAL + hands-on: b6 = 0.9756** — with LKAS off and the driver pushing,
the MODEL arm dominates almost totally — against **ENGAGED + hands-on 0.4727**. (This specific cell
pair is not itself rate-matched; read it as illustrative, not as the headline number.)
⇒ **Engaging LKAS makes the ACTUAL (Path-2 / six-lane) arm relatively LARGER.** [EVIDENCE, magnitude
corrected — see `docs/traces/TRACE-2026-08-13-v99-flight-score.md` §7b for the full derivation]

`b6` is also **non-monotonic in wheel rate**: 0.49 → 0.36 → 0.33 → 0.62 across the four rate bins.
The ACTUAL arm is largest relative to MODEL in the **5–60 °/s** band — which is where the operator's
engaged exposure sits (micro 11.5 s, 13–50 °/s 34.3 s).

### The freeze detector (pre-registered in `builds/v80_v107/build_v98_tva.py` §VAL) [EVIDENCE, and it is WEAK]

Duty of `(b4 constant ≥ 20 consecutive frames) AND (427 code changing over that span)`:
**0.7628 over all frames, 0.4934 engaged.**

🛑 **This detector, as specified, does not discriminate** — `b4` is a slow sign bit whose measured
correlation time is 0.375 s = **37 frames**, so a ≥20-frame hold is its *normal* behaviour, not a
freeze signature. The build flagged that its freeze detector was *"WEAKER than V96's, and that is
a real regression I am not hiding."* **It is weaker than that: it is uninformative as written.**
The liveness question it was meant to answer is answered instead, and better, by the direct
evidence that `b4` toggles: **duty 0.4048 with 6–9 Hz coherence 0.52 against wheel rate (D2)** —
a frozen bit cannot produce that. **Recommendation for V99: replace the run-length freeze rule
with a `d(b4)/dt` crossing-rate against the bit's own measured τ.**

---

## D2 — THE CONVERSE POSITIVE CONTROL (`b4` / `b7` phase)

Sign convention, self-checked before any number was produced:
`angle(scipy.signal.csd(x, y)) = arg(Y) − arg(X)`; positive ⇒ y **leads** x. Self-check delays a
signal 5 samples at 100 Hz and recovers **−140.22° measured vs −140.22° expected** at 7.79 Hz.

**Method A** = Welch over the whole engaged set, nperseg 1024 (V96's stated method).
**Method B** = 5.12 s windows, nperseg 128 (8 Welch segments ⇒ a *real* coherence), circular mean,
block-bootstrapped.

| route | build | `arg(B′) − arg(rate)` A | (coh) | Method B | `arg(V) − arg(rate)` A | `arg(V) − arg(B′)` A |
|---|---|---|---|---|---|---|
| **81** | **V98** | **−78.08°** | **0.516** | −84.96 [−88.9, −81.4] | **+101.17°** | **+179.76°** |
| 80 | V97 | −93.20° | 0.781 | −91.23 [−94.7, −88.3] | +82.23° | +170.64° |
| 7e | V96 | −95.94° | 0.257 | −108.27 [−114.5, −102.4] | +87.54° | −179.54° |
| 7f | V96 | −95.39° | 0.188 | −101.65 [−107.4, −95.6] | +82.89° | +179.03° |

### Verdict: **THE CONTROL REPRODUCES.** [EVIDENCE]

- ✅ **`arg(V) − arg(B′) = ±180° on ALL FOUR routes** (+179.76 on route 81; the record's value for
  7e/7f is −178.1). This quantity is **convention-free** — it is a difference of two phases
  measured the same way — and it reproduces to within 1°. A broken bit map, a wrong byte offset
  or a dead lane cannot produce a 180° anti-phase between two independent rungs.
- ✅ **`|arg(B′) − arg(rate)| = 78.1°** on route 81 (Method A) against the record's **78.6° / 78.0°**
  for 7e/7f. The magnitude reproduces to 0.5°.
- ✅ **Coherence on route 81 is 0.516**, against 0.257 / 0.188 on 7e / 7f. The mechanism is
  *more* clearly present on this route than on the routes the control was established on.

### 🛑 ONE FLAGGED DISCREPANCY, AND IT IS A SCRIPT DIFFERENCE, NOT A BUILD DIFFERENCE

Under the self-checked convention used here, every route including **V96's own 7e/7f** returns
`arg(B′) − arg(rate)` **NEGATIVE** and `arg(V) − arg(rate)` **POSITIVE** — the exact negatives of
the recorded `+78.6 / +78.0` and `−97.3 / −101.8`.

**Because the flip appears identically on the routes the record's own numbers came from, it is a
difference between the two SCRIPTS, not between builds.** Ruled out as the cause: the rate signal
(`cs_rate` and `rate_c` correlate at +0.9995/+0.9998 on both 7e and 81 — same sign), and the bit
polarity (`b4`/`b6` are the same predicate, `value < 0`, on both builds). The producing script for
the recorded numbers was not located this session; it is either a `csd(y,x)` ordering or a sign on
the bit series.

🛑 **This does NOT overturn V97's direction decision, and must not be reported as if it did.**
V97's direction rested on instrument (1) — `|Q| = 1.233 > 1`, an **amplitude** criterion under
which *"inversion is arithmetically excluded at any phase"* — not on the sign of these phases.
**But it is a live discrepancy in a kit that has already had one `csd` sign inversion caught, and
it should be resolved before any phase-signed lever is cut.** [The self-check on this session's
code is EVIDENCE; the cause of the record's opposite sign is UNRESOLVED.]

---

## D3 — `b3` = `gp-0x6752 ≥ 0`: **THE BLOCKER IS CLOSED**

**Duty 0.000000 over 17,982 frames. Zero transitions.** [EVIDENCE]

⇒ **`gp-0x6752` is CONSTANT and NEGATIVE.** POS-3 (b3 constant) passes, and the value is now known.

Consequence, which is why the build called this a **dependency and not a rider**:

```
0x381EE / 0x381F6:   target = ((sum6 * gp-0x6752 * 2639) >> 10) << 4
                     sign(gp-0x374c>>4) = sign(gp-0x6752) * sign(sum6)
with sign(gp-0x6752) = -1:
                     🛑  b4 == 1  (ACTUAL < 0)   <=>   the SIX-LANE SUM is POSITIVE
```

Every prior `b4`/`b6`-class sign reading whose physical meaning was ambiguous by this global flip
can now be resolved. ⚠ `|gp-0x6752| == 1` remains **BELIEF** — the build said so, and this probe
measured the sign only, not the magnitude.

---

## D4 — THE SYMPTOM, IN THE OPERATOR'S OWN REGIME

**Signal:** `tq` = `0x18F` `STEER_TORQUE_SENSOR`, **natively 100 Hz** on this route (median Δt
9.91 ms, 764 distinct values, only 12.8 % repeated samples — this is real data, not a ZOH
staircase, and 6–9 Hz and 35–45 Hz are both well inside Nyquist).

**Windows: 1.28 s (128 samples), 50 % overlap, condition required on EVERY frame.** The 5.12 s
estimator is not used, per `memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime`
(override runs have median 0.02 s corpus-wide).

### 🛑 CONTROLS FIRST

**(a) The episode bootstrap the kit mandates is IMPOSSIBLE on this route** — 3 engaged episodes,
and the LKAS-off demonstration is **one** 59.9 s run. The resampling unit is therefore a
contiguous **5.12 s BLOCK**. That is **weaker than an episode bootstrap** and is labelled as such
everywhere below. The split-half null uses the **same** unit, so floor and contrast are like-for-like.

**(b) Split-half-by-block noise floor (fold-width) — judge every ratio against THIS, not 1.0:**

| arm | blocks | 6–9 Hz floor p50 / p95 | 0.5–3 Hz | 35–45 Hz |
|---|---|---|---|---|
| ENG_all | 13 | **1.66× / 3.07×** | 1.96 / 4.45 | 1.05 / 1.12 |
| MAN_all | 23 | 1.12× / 1.44× | 1.43 / 2.16 | 1.25 / 1.62 |
| seg1_ENG | 9 | **2.04× / 6.01×** | 2.53 / 5.75 | 1.04 / 1.13 |
| seg2_MAN | 12 | 1.13× / 1.55× | 1.34 / 2.07 | 1.21 / 1.74 |

**(c) 🛑 THE MASK DIAGNOSTIC — the kit's own memory, reproduced within this route.**
A **pure** hands-on / hands-off split keeps only **8 + 8 of 98** engaged windows and discards
**83.7 %** of them: the windows where `|cs_tq|` crosses 1200 *inside* the window. Those discarded
windows are **exactly where the 6–9 Hz oscillation lives** — because the oscillation itself is what
drives `|cs_tq|` across the threshold at 6–9 Hz. ⇒ **The unmasked arm is the one to read**, and
the hands-on/hands-off sub-arms below are reported only to show they are underpowered, not as
results.

### The contrast [EVIDENCE]

Geometric mean of per-(speed × |wheel rate|) cell ratios; cells without ≥3 windows in **both**
arms are dropped, so no ratio is carried by a regime only one arm visited. Block bootstrap, 2,000
resamples.

**Arm A / Arm B = ENGAGED / MANUAL, whole route (13 / 23 blocks):**

| band | ratio | block-boot CI | vs ENG split-half floor p95 | reading |
|---|---|---|---|---|
| 0.5–3 Hz | 0.892 | [0.46, 2.11] | 4.45× | **NULL** |
| **6–9 Hz** | **7.119** | **[3.27, 16.09]** | 3.07× | ⭐ **CLEARS ITS FLOOR** |
| 15–22 Hz | 4.780 | [2.40, 9.19] | — | elevated |
| 26–31 Hz | 1.845 | [1.32, 2.48] | — | mildly elevated |
| 35–45 Hz | 1.425 | [1.12, 1.76] | 1.12× | **negative control — small but not 1** |

**Arm A / Arm B = seg1 ENGAGED / seg2 MANUAL — the operator's own back-to-back pair (9 / 12 blocks):**

| band | ratio | block-boot CI | vs seg1 floor p95 | reading |
|---|---|---|---|---|
| 0.5–3 Hz | 1.042 | [0.24, 3.63] | 5.75× | **NULL** |
| **6–9 Hz** | **4.106** | **[1.66, 11.54]** | **6.01×** | 🛑 **DOES NOT CLEAR ITS OWN FLOOR** |
| 15–22 Hz | 3.137 | [1.30, 6.21] | — | elevated |
| 35–45 Hz | 1.161 | [0.84, 1.42] | 1.13× | ✅ **negative control passes cleanly** |

🛑 **STATED PLAINLY: the back-to-back matched pair on its own is UNDERPOWERED.** 9 blocks in the
engaged arm give a 6–9 Hz split-half fold-width of 6.01× at p95, and the observed 4.11× sits inside
it. **The pair is beautiful exposure design and it does not, by itself, license the claim.**
The whole-route contrast (7.12× against a 3.07× floor) does. Both are reported; the weaker one is
not hidden behind the stronger one.

Underpowered sub-arms, reported for completeness only: ENG_handson / MAN_handson 6–9 Hz **1.248
[0.44, 4.09]** on **3 blocks**; ENG_handsoff / MAN_handsoff is **UNDEFINED** (no speed × rate cell
has ≥3 windows in both arms). Neither supports or refutes anything.

### D4b — CROSS-SIGNAL CONTROL: it is in the ANGLE, and it is NOT COMMANDED [EVIDENCE]

Engaged-vs-manual ratios of the same standardised statistic on four different signals:

| signal | 0.5–3 Hz | **6–9 Hz** | 15–22 Hz | 35–45 Hz (control) |
|---|---|---|---|---|
| `0x18F` column torque | 0.89 [0.45, 2.13] | **7.12 [3.23, 16.46]** | 4.78 [2.43, 9.21] | 1.43 [1.12, 1.77] |
| steering **ANGLE** | 1.19 [0.86, 1.62] | **2.66 [1.72, 4.20]** | 1.86 [1.27, 3.44] | **0.99 [0.62, 1.98]** |
| 427 = `gp-0x6b70` | 1.11 [0.51, 2.72] | 3.84 [1.77, 7.04] | **6.90 [2.79, 13.79]** | **4.14 [1.84, 9.10]** |
| openpilot command | — | — | — | — (manual arm has no command) |

- ⭐ **The 6–9 Hz excess is in the STEERING ANGLE as well as the torque, with a clean 0.99 negative
  control at 35–45 Hz and a clean 1.19 null at 0.5–3 Hz.** The wheel is physically moving at 6–9 Hz
  when engaged and not when manual. This is not a torque-sensor artefact.
- 🛑 **The 427 lane (`gp-0x6b70`) is elevated in EVERY band, including the 35–45 Hz negative
  control (4.14×).** It is **broadband**, so it supports **no band-specific claim** — the same
  conclusion V87 reached for `gp-0x6b98`. Reported so it is not misread as corroboration.
- **openpilot's command does not contain the band.** Within engaged frames the command's band RMS
  is 0.005 at 6–9 Hz against 0.107 at 0.5–3 Hz (ratio **0.047**), while the column torque's is
  335.7 against 166.4 (ratio **2.02**) — **the column is 43× more 6–9-Hz-rich than the command
  that drives it.** A cross-arm ratio is not computable because the manual arm has no command;
  the within-arm ratio is the statement. This reproduces
  `memory/accord-ratchet-characterised-on-route-4f` within a single route.

### D4c — ⭐ WITHIN-EPISODE DECOMPOSITION: THE COMPARATOR MOVES WITH THE SYMPTOM [EVIDENCE]

98 engaged windows in 13 blocks, split into terciles of their own 6–9 Hz band RMS:

| tercile | n | 6–9 Hz RMS | **b6** | b4 | b7 | v | \|rate\| | press |
|---|---|---|---|---|---|---|---|---|
| LOW | 33 | 45.8 | **0.5085** | 0.5078 | 0.4759 | 7.92 | 61.8 | 0.569 |
| MID | 32 | 335.7 | **0.4409** | 0.3906 | 0.4976 | 6.71 | 23.2 | 0.211 |
| HIGH | 33 | 682.8 | **0.3205** | 0.4337 | 0.5616 | 5.56 | 24.5 | 0.205 |

Partial Spearman of `log(6–9 Hz band RMS)` against each bit's window duty, **controlling for speed,
|wheel rate| and press**, with a **block-permutation null** (5.12 s blocks permuted whole, so
within-episode correlation cannot manufacture the result), 5,000 permutations:

| bit | partial r | block-perm p | null 95 % \|r\| | verdict |
|---|---|---|---|---|
| **b6** | **−0.321** | **0.0050** | 0.221 | ⭐ **SURVIVES** |
| b4 | +0.087 | 0.4948 | 0.239 | NULL |
| b7 | +0.037 | 0.7690 | 0.246 | NULL |

**`b4` and `b7` are the controls, and they are null on the identical test.** So this is not "any
bit correlates with anything during the symptom" — it is specific to the comparator.

⇒ **WHEN THE GRINDING IS LOUDEST, `|MODEL| ≥ |ACTUAL|` becomes LESS likely.** The ACTUAL
(Path-2 / six-lane, `gp-0x374c`) arm **swells relative to the MODEL arm during the symptom itself.**
This is exactly the within-frame, within-episode decomposition CLAUDE.md asks every build to
deliver, and it is the first time the kit has read one out **during** the symptom rather than
scoring a lever across drives.

---

## D5 — WHAT A NULL WOULD HAVE LICENSED, PRE-REGISTERED PER STATISTIC

Declared before each statistic was computed. Every one of these was a *live* possibility.

| statistic | what a NULL would have licensed | what happened |
|---|---|---|
| byte7[7:6] == 2 duty | *"The cave did not run or the offset is wrong — NOTHING may be reported."* | 1.000000 — reported |
| 427 == 1023 count | *"The latch fired; b6 is poisoned on N frames and those N are excluded."* | 0 frames — no exclusion needed |
| `b5` duty | *"REQUEST is comparable to ACTUAL"* if ~0.5; *"REQUEST dominates"* if →1 | 0.0000 ⇒ REQUEST is minor |
| `b6` duty →1 | *"the ACTUAL arm is minor; `0xC63AC` and the six lane weights move a small term; move to `FUN_0003b8f6`."* | 0.4235 — not this |
| `b6` duty →0 | *"Path-2 IS the residual; V97's null is dose/direction."* | 0.4235 — not this either |
| `b6` duty ~0.5 | *"the arms are comparable — the cancellation regime; BOTH are live levers."* | **THIS ONE** |
| `b3` varies | *"the bit offset is wrong — the map is indicted."* | constant, 0 transitions ⇒ map vindicated |
| `arg(V) − arg(B′)` ≠ 180° | *"the bit map or a lane is broken; the comparator result does not travel."* | +179.76° ⇒ **it travels** |
| 6–9 Hz ENG/MAN inside its floor | *"we cannot tell whether engagement amplifies the band on this route; report the floor and stop."* | 7.12× vs 3.07× floor ⇒ clears |
| 6–9 Hz on the **matched pair** | *"the pair is too short; the whole-route contrast carries it and the pair does not corroborate."* | **4.11× vs a 6.01× floor — THIS IS WHAT HAPPENED, and it is reported as such** |
| 35–45 Hz control ≠ 1 | *"the contrast is a broadband route/gain offset, not a band-specific effect."* | 1.43 [1.12, 1.77] on torque, **0.99 on angle** ⇒ band-specific on the angle, mildly offset on torque |
| D4c partial r inside the block-perm null | *"the comparator carries no within-symptom information; it is a static ordering only."* | −0.321, p = 0.0050 ⇒ it carries information |

🛑 **Where the honest answer is "we cannot tell", it is said and no number is offered:**
the hands-on / hands-off **sub**-contrasts (3 and 4 blocks), the freeze detector as specified,
and `|gp-0x6752|`'s magnitude.

---

## WHAT THIS LICENSES FOR V99

1. **The search does NOT move to `FUN_0003b8f6` on a "the MODEL arm dominates" argument** — that
   reading was pre-registered as `b6 → 1` and it is **not** what the car returned.
2. **`gp-0x6bfa` (the LKAS REQUEST arm) should not be levered.** `b5 = 0.0000` on every engaged
   frame. Its `±20000` gate was already known dead; now its *magnitude* is known minor.
3. **Both `0xC40D2` (V89, MODEL) and `0xC63AC` (V97, ACTUAL) sit on live comparable arms**, so
   their nulls are **dose or direction**, not reach. Re-dosing either is now a defensible class —
   but only with a **pre-registered observable that a DC-gain-1.000 pole can move**, which is the
   exact gap that made V97 uninterpretable.
4. ⭐ **The strongest new pointer is D4c: the ACTUAL arm swells during the symptom.** The six lane
   weights `0xC63A2`–`0xC63AA` are **virgin across every image in the kit** and `0xC63A0` has been
   at 1024 since V83a. That is the arm the symptom lives on, and it has never been touched.
5. **A V99 instrument should spend its rungs on the ACTUAL arm's composition**, not on another
   comparator against it — `b5` proved the comparator class works and also proved one of its two
   rungs was spent on an already-small term.
6. **Resolve the D2 sign discrepancy** before cutting anything whose direction depends on a
   measured phase.
