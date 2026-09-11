# Sizing the COMB through the byte-exact mirror — and what it does to the ECHO

Subagent `combsize`, 2026-09-10. **ANALYSIS ONLY** — built nothing, flashed nothing, sent nothing on any bus.

🛑🛑 **RETRACTION, 2026-09-11 — READ BEFORE ANYTHING ELSE.** Two headline results in this report,
**§1e ("the comb does not grow when the car grinds")** and **§3a's angle-vs-bar asymmetry ("bar 34 %
locked, angle 2 %")**, were **artefacts of a biased lock-fraction estimator and are WITHDRAWN IN FULL.**
Debiased, the comb **grows ×0.94–1.81** while the ring grows ×1.62–2.68, and the angle is **~40 %**
camera-locked, not 2 %. **§12 carries the retraction, the ground-truth test that settled the estimator,
and what survives.** The mirror sizing (§1b/§1c), the r63 falsifier, §3b's coherence collapse and the
crux checks (§10) do **not** use that estimator and are unaffected.


Scripts, all under `rlog-tools/studies/grind/`:

| script | what it does | output |
|---|---|---|
| `comb_mirror_sizing.py` | comb amplitude in raw counts; locked/free ablation through the mirror | `_scratch/comb_mirror_sizing.txt` |
| `comb_mirror_controls.py` | the detuned-clock null that **failed**, band-width sweep, accumulation ceiling | `_scratch/comb_mirror_controls.txt` |
| `comb_mirror_apportion.py` | the method-independent three-leg apportionment; the long-window null that **passed** | `_scratch/comb_mirror_apportion.txt` |
| `comb_vs_echo_partition.py` | common-driver test on angle/bar; partial coherence; apportionment | `_scratch/comb_vs_echo_partition.txt` |
| `v288_describing_function.py` | V288's real pre-filter gain, re-derived from the cave arithmetic | `_scratch/v288_describing_function.txt` |

Everything reuses `slewburst`'s instrument verbatim — `burst_onset_triggers.load_route`, `burst_echo_sizing.band_amp`
and `loud_windows`, `grind_incident_r35.simulate` — so every number below sits on the same axis as its
4.4–6.8 capped-step row and its 8–31 echo row. **Re-derived `T_total` = 57.21 on r39 and 125.86 on r63,
matching its E1 table exactly.** The R2 statistic is **imported** from `modelrate`'s `modeld_phase_lock.py`,
not re-implemented, so the two agents' locked fractions are produced by the same code.

⚠ **CARRIED LIMITATION, restated from `slewburst` and binding on every mirror row below:** `GI.simulate` is
the V282-era chain. It reads each build's cal cells from that build's image but does **not** implement V288's
pre-filter cave or V289's notch cave. **Only the r39 (V282) mirror row is a clean mirror result.** The wire
measurements (P1, P2, C1) are unaffected.

---

## 0. VERDICT

🛑 **REVISED after the crux checks in §10. The earlier headline — "neither mechanism is sufficient" —
is WITHDRAWN for V282/V288/V281r3**, because it rested on ζ = 0.029 and the measured ζ is lower (§X3).
What replaces it is a stronger statement, and it does not depend on ζ at all:

> ⭐ **THE EXCITATION IS CONSTANT AND THE DAMPING IS THE VARIABLE. At ζ ≈ 0.01–0.03 with the loop
> de-damping, no identifiable excitation is NEEDED — the ever-present camera comb suffices, and removing
> it perfectly would buy ~3 % (at most 8 %) of grinding amplitude. "What excites it" is the wrong
> question. The lever is ζ_eff — loop damping — and that is EPS-side.** [§11c]

The measurements behind it, in the order they bind. **Only the first is a sizing; the rest are
falsifications, and the falsifications are what carry the verdict.**

1. **THE COMB AND THE ECHO ARE NOT ADDITIVE — they are competing partitions of one command-side budget.**
   Both live in the 0xE4 command and nowhere else. Notching the whole ring band out of the command bounds
   **both together** with no assumption about clocks, phase or locking: **11.56 counts against 57.21
   delivered on r39/V282 — 20.2 %**; 5.21 against 125.86 on r63/V289 — 4.1 %. The feedback leg is 88–100 %.
   ⚠ **Whether that budget is "sufficient" is ζ-dependent and is NOT settled** — see §X3.
2. 🛑 **THE LOUDEST RING IN THE CORPUS SITS ON THE SMALLEST COMMAND DRIVE.** r63's ring is **1.71×** r39's
   in matched speed × demand cells (2.2× raw — a quarter of it was regime, §X2) on **0.30–0.45×** the
   command drive. Bandwidth-normalised, so not a filter artefact (§X1). **r63 is the one route where the
   command side is excluded as sufficient at EVERY ζ in the measured range** (0.75 at the most favourable).
3. ⭐ **THE COMB DOES NOT GROW WHEN THE CAR GRINDS — the result that needs no model at all.**
   Speed-matched, the ring rises **×1.6–2.8** while the camera-locked comb amplitude is **×0.55–0.86**,
   significantly **below 1** on three of four routes. No chain model, no cal cells, no ceiling, no phase
   assumption. §1e.
4. ⭐ **THE ZERO-LAG PUZZLE IS SOLVED, AND IT SOLVES ITSELF OUT OF RELEVANCE.** The common-driver reading
   is **confirmed** — command↔angle coherence at f0 is carried entirely by the camera clock (0.388 raw →
   **0.022** with the clock projected out, against a matched control that goes **up** to 0.598). But the
   clock-locked component is only **~2 %** of the angle's in-band energy. **The comb correctly explains
   the cross-phase and is far too small to be the grinding.**
5. 🛑 **THE ECHO IS FALSIFIED AS A COHERENT LINK, not merely sized.** After the clock is removed there is
   **no residual command↔angle coupling at f0** (0.022 on r39, 0.078 on r5e). An openpilot P-path echo
   would put the angle's dominant *free* content into the command at ≥ 144° of lag and would show up
   here. It does not. **The physical reason: the driver-torque BAR is 34 % camera-locked and the steering
   ANGLE only 2 % — a 20 Hz torque comb barely moves the column's inertia, and openpilot measures the
   ANGLE, not the torque.**

**Results 2–5 are independent of each other and of ζ, and four of the five are independent of the mirror.
They agree.**

**And one correction that cuts the other way, against my own conclusion:** V288's null is void in *both*
directions. Its pre-filter attenuated the ring by **−1 % to +9 %** (§4), so it never tested the
reference-side class at all. **That class is UNTESTED, not exhausted** — `STATE.md` is wrong on this. It
does not rescue the comb or the echo; it removes a *false confirmation* of a right answer.

---

## 1. ITEM 1 — SIZING THE COMB THROUGH THE MIRROR

### 1a. Why ablation, not injection

The comb is **already in the measured command**. Injecting a synthesised staircase would size an assumed
waveform; ablating the measured one sizes the real thing. `slewburst`'s 13.17-count echo row was an injected
sinusoid at an *assumed* amplitude (A = 20.6, from `oplpf`'s predicted per-LSB gain — a figure `slewburst`'s
own A3 then found to be wrong by ×1.1–8.6 and scaling the wrong way with speed). The 11.56 below is the same
quantity **measured**.

So: notch the ring band out of the command, run the mirror, and take the difference in delivered in-band
torque. That bounds the comb and the echo **together** and cannot be gamed by the choice of decomposition.

### 1b. THE THREE LEGS [EVIDENCE]

Byte-exact 1 kHz mirror, 10 loudest 3 s engaged windows per route, median over windows,
`sqrt(2)·rms` of the band-passed `dT` in the route's own ring band, bootstrap CI over windows.

| route | build | `T_total` | **CMD leg** | share | 95 % CI | **FB leg** | share | √(C²+F²) |
|---|---|---|---|---|---|---|---|---|
| **r39** | **V282 (clean)** | **57.21** | **11.56** | **0.202** | [7.6, 19.6] | **50.27** | **0.879** | 51.59 |
| r5e_v288 ⚠ | V288 rev 2 | 52.61 | 6.98 | 0.133 | [5.2, 20.2] | 47.33 | 0.900 | 47.84 |
| r62_v289 ⚠ | V289 rev 1 | 66.00 | 6.03 | 0.091 | [4.5, 10.3] | 75.64 | 1.146 | 75.88 |
| r63_v289 ⚠ | V289 rev 1 | 125.86 | **5.21** | **0.041** | [4.2, 13.4] | 125.26 | 0.995 | 125.37 |
| r35 | V281 rev 3 | 21.50 | 5.83 | 0.271 | [5.1, 16.5] | 23.49 | 1.093 | 24.20 |

- **CMD leg** — the whole ring band notched out of the 0xE4 command. **An upper bound on the comb AND the
  echo together.**
- **FB leg** — the whole ring band notched out of the measured 0x18F wheel rate feeding the feedback path.
  The loop's own regeneration of the ring already present.
- **√(C²+F²)** lands at 90–113 % of `T_total` on every route: a consistency check on the decomposition,
  not an assumption inside it.

⚠ The FB-leg CIs are wide ([27, 95] on r39) and two routes return a share slightly above 1. That is the
bandstop's own transient plus the chain's nonlinearity, and it means the FB leg should be read as
*"accounts for essentially all of it"*, not as a number good to three digits.

### 1c. Is the comb sufficient on its own?

Quoted on **`slewburst`'s exact terms** — the analytic phase-locked accumulation ceiling
`1/(1−e^(−2πζ)) = 6.00` at ζ = 0.029, degraded by `|cos ψ|` against the ring velocity — so the comb and the
echo are judged by one rule.

| route | CMD leg | ×6.00 | **ratio** | CI on the ratio | verdict at ψ = 0 (best case) |
|---|---|---|---|---|---|
| **r39 (V282)** | 11.56 | 69.4 | **1.213** | [0.80, 2.06] | marginal — fails past **ψ ≈ 34°** |
| r5e_v288 | 6.98 | 41.9 | 0.797 | [0.59, 2.30] | SHORT ×1.3 |
| r62_v289 | 6.03 | 36.2 | 0.548 | [0.41, **0.94**] | SHORT ×1.8 — **excluded at the upper bound** |
| r63_v289 | 5.21 | 31.3 | **0.248** | [0.20, **0.64**] | SHORT ×4.0 — **excluded at the upper bound** |
| r35 | 5.83 | 35.0 | 1.628 | [1.42, 4.60] | sufficient at ψ = 0 |

🛑 **THIS WHOLE TABLE IS SUPERSEDED BY §X3 AND MUST NOT BE QUOTED ON ITS OWN.** Every row assumes
ζ = 0.029. `cyclekind` measures ζ = 0.0091–0.0224, which raises the ceiling and makes the command side
**more** capable: at the measured ζ, r39 reaches **1.54–3.64**, not 1.21, and V282/V288/V281r3 are **not
excluded at all**. **Only r63 stays below unity at every measured ζ.** The table is kept because it is
what `slewburst`'s terms produce and because the ζ-dependence is only visible against it — but the
sufficiency verdicts in the last column are withdrawn. See §X3 for the swept version.

The one durable reading here: **the comb lands in exactly the place the echo did** — 1.21 vs the echo's
1.38 at the same ζ. That is not a coincidence. **It is the same 11.6 counts, read two ways.**

### 1d. The comb on the wire, in raw counts (the numerator `modelrate` reported as a ratio)

In-band amplitude of the 0xE4 command in a ±1.5 Hz band on the camera clock, split by R2:

| route | stratum | A_inband | R2 | floor | R2−floor | **A_locked** | A_free |
|---|---|---|---|---|---|---|---|
| r39 | baseline | 28.53 | 0.661 | 0.172 | +0.490 | 19.96 | 20.38 |
| r39 | grinding | 29.18 | 0.649 | 0.261 | +0.388 | **18.17** | 22.83 |
| r5e_v288 | grinding | 38.32 | 0.638 | 0.363 | +0.274 | **20.07** | 32.65 |
| r62_v289 | grinding | 24.60 | 0.584 | 0.545 | +0.039 | 4.84 ⚠ | 24.12 |
| r63_v289 | grinding | 35.33 | 0.682 | 0.351 | +0.331 | **20.31** | 28.90 |

**The comb is present on every build, including V289** — 20.3 counts locked on r63. It is simply at 20 Hz,
where V289's ring no longer is. ⚠ r62's floor is nearly as high as its R2; that route's estimate is weak.

⚠ **These are NOT the same numbers as §3a**, and the difference is by construction, not a discrepancy:
§1d uses a ±1.5 Hz band **on the camera clock** and a peak±0.5 s grinding stratum; §3a uses the route's
**ring band** and `modelrate`'s census episodes. On r39 the two bands coincide but the strata do not
(106 s here, 182 s there). Quote each against its own section.

### 1e. ⭐ THE MIRROR-INDEPENDENT FALSIFIER — the comb does not grow when the car grinds

Noticed while reconciling §1d against §3a, then measured properly in `comb_does_not_grow.py`. **This test
needs no chain model, no calibration cells, no accumulation ceiling and no assumption about phase.** If the
camera-clock comb drives the grinding, the comb must be *larger* in grinding windows. It is not.

`comb` = amplitude of the camera-**locked** part of the 0xE4 command at the clock ±1.5 Hz;
`ring` = amplitude of the driver-torque bar in that route's ring band. Same strata for both.

| route | build | comb quiet→grind | **comb ratio** | ring quiet→grind | **ring ratio** | discrepancy |
|---|---|---|---|---|---|---|
| r39 | V282 | 17.67 → 18.17 | 1.03 | 61.1 → 103.5 | 1.69 | 1.6× |
| r5e_v288 | V288 r2 | 21.71 → 20.07 | 0.92 | 56.1 → 107.3 | 1.91 | 2.1× |
| r62_v289 | V289 r1 | 16.38 → 4.84 | 0.30 | 69.3 → 137.8 | 1.99 | 6.7× |
| r63_v289 | V289 r1 | 21.87 → 20.31 | 0.93 | 95.2 → 261.5 | 2.75 | 3.0× |

**Speed-matched** (2 m/s bins, ≥ 8 s in both strata, energy-weighted, bootstrap over bins) — because the
obvious confound is that the quiet stratum in the earlier tables was restricted to v < 12 m/s:

| route | bins | **comb ratio** | 95 % CI | **ring ratio** | 95 % CI | discrepancy |
|---|---|---|---|---|---|---|
| r39 | 6 | **0.66** | **[0.48, 0.80]** | 1.62 | [1.35, 1.83] | 2.5× |
| r5e_v288 | 6 | **0.57** | **[0.30, 0.80]** | 1.86 | [1.47, 2.55] | 3.3× |
| r62_v289 | 2 | **0.55** | **[0.00, 0.94]** | 2.20 | [1.58, 3.08] | 4.0× |
| r63_v289 | 3 | 0.86 | [0.00, 1.08] | 2.68 | [1.95, 3.56] | 3.1× |

Demand-matched (LKAS demand-index bins) gives the same answer: comb ratio 0.35–0.91, ring ratio 1.44–2.36.

⇒ **The ring rises 1.6–2.8× while the comb is flat or FALLS — significantly below 1 on three of four routes.
The putative driver does not move when the symptom does.** [EVIDENCE] The confound survives every
stratification I applied, and the speed-matched version is *more* adverse to the comb than the raw one.

⚠ **What this does NOT show, stated so it is not over-read.** It does not show the comb is absent — it is
plainly there (R2 − floor = +0.27 to +0.49 on the command). It shows the comb is not what **modulates** the
grinding. **A constant driver exciting a mode whose DAMPING varies would produce exactly this pattern**, and
that is the de-damping picture already in the record, in which the loop — not the drive — is the variable.
So §1e is consistent with the comb being a real, permanent, *small* excitation that the loop amplifies by a
varying amount. [BELIEF] That reading is the one §1b and §5 quantify: the loop is the variable, and it is
carrying 88–100 %.

---

## 2. 🛑 A CONTROL OF MINE THAT FAILED — reported against my own first number

My first pass split the command's in-band content into camera-locked and free (`modelrate`'s mod-π
projection) and reported a **"COMB net" of 7.51 counts** on r39.

**The detuned-clock null did not collapse.** Same ablation against reference clocks where no line exists:

| route | clock | detune | in-phase | quadrature | NET |
|---|---|---|---|---|---|
| r39 | f_model | +0.00 | 9.53 | 5.86 | **7.51** |
| r39 | detuned | −0.37 | 9.22 | 6.72 | **6.32** ← 84 % of the signal |

Cause is structural, not a bug: delivery was measured in **3 s** windows, and `|Δf|·T = 0.37 × 3 = 1.1`
cycles of phase slip is not decorrelation. **At 3 s windows that split cannot separate comb from echo, and
the 7.51 must not be quoted.**

Redone on **12 s** windows (`|Δf|·T = 4.4`), the null does collapse:

| route | f_model | null floor (max over 6 detunings) | separation |
|---|---|---|---|
| r39 | **10.40** | 2.82 | **3.7×** — clean |
| r63_v289 | 1.76 | 1.38 | 1.3× — **not separable** |

So the comb **is** real and camera-locked on r39 and **is** the dominant part of that route's command leg; on
r63 it is not separable, exactly as a 3.5 Hz offset predicts. **The whole-band CMD-leg number in §1b is
immune to this problem entirely, which is why it is the headline and the 7.51 is not.**

Band-width sensitivity is benign: net 7.95 / 7.51 / 7.12 at half-widths 1.0 / 1.5 / 2.5 Hz.

---

## 3. ITEMS 2 & 3 — THE COMMON-DRIVER TEST, AND THE PUZZLE IT RESOLVES

### 3a. Item 2 — is the ANGLE camera-locked? [EVIDENCE]

R2 on the **steering angle** and the **driver-torque bar** (`modelrate` owns the command side), grinding vs
baseline, against its measured detuned-clock floor. r39 is the only route with enough data in both strata for
the floor to be low enough to resolve anything — this is stated, not worked around.

**r39 / V282, grinding stratum, 18–22 Hz:**

| channel | R2 | floor | **R2 − floor** | reading |
|---|---|---|---|---|
| 0xE4 command | 0.676 | 0.184 | **+0.492** | strongly camera-locked |
| BAR driver torque | 0.506 | 0.161 | **+0.344** | substantially camera-locked |
| **ANGLE 0x14A** | 0.262 | 0.243 | **+0.019** | **at the floor — NOT locked** |

And the grinding **excess** decomposition (`modelrate`'s script runs this for `bar` only; run here for the
angle, which is the channel the echo hypothesis depends on):

| route | channel | ΔE | ΔE_lock | **lock fraction of the excess** |
|---|---|---|---|---|
| r39 | **ANGLE 0x14A** | 1.25e−3 | 2.9e−5 | **0.023** |
| r39 | BAR torque | 7661 | 2737 | 0.357 |
| r5e_v288 ⚠ | ANGLE / BAR | — | 0 | 0.000 / 0.000 (floor too high, 99 s) |
| r62/r63 ⚠ | ANGLE / BAR | — | 0 | 0.000 (**band effect, see below**) |

⭐ **THE ASYMMETRY IS THE RESULT: the driver-torque bar is 34 % camera-locked; the steering angle is 2 %.**
Physically this is what a 20 Hz torque comb must do — the column's inertia means a torque line at 20 Hz
produces very little angular motion. **And openpilot measures the ANGLE, not the torque**, so the echo path
sees almost none of the comb. [EVIDENCE for the numbers; BELIEF for the inertia reading.]

🛑 **DO NOT READ THE V289 ROWS AS "THE COMB VANISHED".** They are computed in that build's **ring** band
(14–18 Hz), where the comb has never been. §1d measures the same command at 20 ± 1.5 Hz on the same routes
and finds R2 − floor = +0.33 on r63. **The comb is present on V289; the ring has moved away from it.**

### 3b. Item 3 — partial coherence, with a matched control [EVIDENCE]

Command↔angle coherence at f0 inside the grinding stratum, three ways: raw; with the camera-clock in-phase
projection removed from **both** signals; and — the control — with the **quadrature** projection removed
instead (same in-band energy, orthogonal to the clock).

| route | build | f0 | coh raw | **−clock** | **−quad (control)** | raw phase | implied lag |
|---|---|---|---|---|---|---|---|
| **r39** | V282 | 19.92 | 0.388 | **0.022** | **0.598** | +10.0° | −1.4 ms |
| r5e_v288 | V288 r2 | 20.02 | 0.261 | **0.078** | 0.302 | +66.8° | −9.3 ms |
| r62_v289 | V289 r1 | 14.75 | 0.084 | 0.088 | 0.088 | −36.1° | +6.8 ms |
| r63_v289 | V289 r1 | 16.50 | 0.017 | 0.016 | 0.016 | −69.4° | +11.7 ms |

**Read `−clock` against `−quad`, never against `raw`.** On r39 removing the clock destroys the coherence
(0.388 → **0.022**) while removing an equal amount of clock-orthogonal energy **raises** it (→ 0.598). The
control rules out "you just removed energy". ⇒ **the camera clock is what links command and angle at f0.
The common-driver reading is CONFIRMED.** r5e points the same way, weaker. r62/r63 have no coherence to
partial out in the first place — consistent with the ring sitting 3.5 Hz off the comb.

### 3c. 🛑 Resolving the apparent contradiction between 3a and 3b

3a says the angle is **2 % locked**. 3b says the clock carries **all** of the command↔angle coherence.
These look opposed. They are not, and the resolution is the point:

> The angle contains a **small** camera-locked component (~2 % of its in-band energy) sitting on a **large**
> free oscillation (the ring). Coherence is normalised and responds to the *shared* part regardless of its
> size; the lock fraction is an energy measure dominated by the large free part. The command is 49 % locked,
> so its locked half and the angle's locked 2 % are the *same clock* and are perfectly coherent — while the
> angle's other 98 % has nothing matching it in the command at all.

⭐ **Consequences, and they cut against both hypotheses:**

- **The zero-lag observation is correctly explained by the comb** — a common external driver, no round trip,
  no ≥144° of openpilot latency needed. The orchestrator's reading was right.
- **But it is explained by a component that is ~2 % of the angle's in-band energy and ~4 % of its grinding
  excess.** The cross-phase anomaly was never a measurement of the grinding.
- 🛑 **The echo is falsified as a coherent link, not merely sized down.** If openpilot's P-path echo carried
  the ring, the angle's dominant *free* content would reappear in the command at ≥ 144° lag and would show as
  residual coherence after the clock is removed. **It is 0.022.** There is no angle-shaped coupling left for
  an echo to live in. [EVIDENCE for the number; BELIEF for the inference.]
- ⇒ **The free part of the command leg must NOT be labelled "the echo."** It is unlocked command content of
  some other origin (plan noise, quantisation). I had that label in a first draft and it was wrong.

---

## 4. ITEM 4 — V288 RE-RUN WITH THE CORRECTED GAINS

**The orchestrator's arithmetic is confirmed, and the correction is if anything slightly stronger.** I did
not interpolate its four points; I re-derived the describing function from the cave arithmetic
(`delta = sp − y_prev; step = delta>>4` — an **arithmetic** shift, flooring toward −∞; `if step==0 and
delta!=0: step = ±1`; `y += step`) at 20.3 Hz, 1 kHz, and it reproduces them:

| A (sp counts) | my gain | phase | orchestrator's figure | agreement |
|---|---|---|---|---|
| 4 | 1.014 | −0.0° | 0.99 | +0.02 |
| 8 | 1.005 | −0.1° | 0.95 | +0.06 |
| 16 | 0.624 | −38.1° | 0.61 | +0.01 |
| 40 | 0.439 | −58.9° | 0.45 | −0.01 |
| LTI `y += (x−y)/16` | **0.452** | — | (amplitude-blind) | what `slewburst` assumed |

**Where the ring actually sits** (15–40 raw ÷ 16.125736 idx LSB × 4.30 sp/idx = 4.0–10.7 sp counts):

| raw counts | sp counts | gain | attenuation |
|---|---|---|---|
| 15 | 4.00 | 1.014 | **−1.4 %** |
| 20 | 5.33 | 0.986 | +1.4 % |
| 30 | 8.00 | 1.005 | −0.5 % |
| 40 | 10.67 | 0.906 | **+9.4 %** |
| *a slew-capped frame* | *32.8* | *0.47* | *53 %* |

**⇒ V288's pre-filter attenuated the grinding band by −1 % to +9 %, not 54 %.** The anti-stick makes it
marginally *expansive* at the smallest amplitudes, and it adds **no phase lag** there either (−0.0°).
**The cave was working — it simply was not working on the ring.** A slew-capped frame *does* see the full
×2.1 cut, which is why the cave looked alive on the wire.

**What the hypothesis therefore predicted, on my measured command leg:**

| reading | gain | ceiling | prediction for V288 |
|---|---|---|---|
| V282 baseline | — | 1.213 | (the baseline) |
| `slewburst` A1b — LTI, amplitude-blind | 0.452 | **0.548** | ring collapses |
| corrected, ring at 15 raw | 1.014 | **1.229** | **no visible change** |
| corrected, ring at 40 raw | 0.906 | **1.098** | **no visible change** |

**The corrected prediction is "no visible change", and the car agreed** — every ring statistic unchanged on
r5e_v288 with the cave live on 99.5 % of engaged frames. Your ≈1.31 estimate and my 1.10–1.23 are the same
answer. [EVIDENCE]

🛑 **The consequence that matters more than the agreement.** Under the LTI reading V288 was a *decisive* test
of the reference/excitation-side class that returned a null — which is how `STATE.md` came to call that class
**EXHAUSTED**. Under the correct arithmetic V288 moved the ring's drive by a few percent. **An experiment
that did not move the independent variable cannot test the dependent one. V288's null is uninformative in
both directions.** The reference-side class is **UNTESTED, not exhausted**; `STATE.md` needs correcting.

⚠ **And what that does not rescue.** Re-opening the class does not make the comb or the echo sufficient —
§1 settles that separately and against them. It removes a *false confirmation* of a conclusion that the
sizing reaches on much stronger grounds.

---

## 5. ITEM 5 — APPORTIONMENT

**r39 / V282, the only clean mirror row:**

```
 delivered in-band torque                          counts    share
 T_total (every input as measured)                  57.21    1.000
 ├── COMMAND leg  (comb AND echo TOGETHER)          11.56    0.202   [CI 7.6-19.6]
 │     ├── camera-locked part  — THE COMB           10.40 *  0.182 * [12 s windows, null floor 2.82]
 │     └── free part — NOT the echo (§3c)            8.09 *  0.141 *
 └── FEEDBACK leg (the loop regenerating the
     ring already in the wheel rate)                50.27    0.879   [CI 27.3-95.2]
```

`* ` the comb/free split is only usable on 12 s windows (§2). The command-leg total is not.
The two parts add in quadrature to 13.18, consistent with 11.56 to within the window-length difference.

**Across builds the command leg falls from 20 % → 13 % → 9 % → 4 % (r39 → r5e → r62 → r63) while the ring
rises from 57 → 53 → 66 → 126 counts.** A mechanism whose drive moves inversely to its symptom across four
builds is not that symptom's sustaining cause. [EVIDENCE for the numbers; BELIEF for the reading.]

**What is carrying the ring, on this decomposition, is the FB leg — 88–100 % everywhere.** That is the EPS's
own D-term response to the ring already present in the measured wheel rate, i.e. the de-damping loop. I
report it as a **positive control rather than a new finding**: it independently reproduces the record's
existing verdict (*"the creep grind is the LKAS rate loop's crossover resonance, D-dominated"*) from a
different direction, which is what gives me confidence in the decomposition.

🛑 **ANTI-DOUBLE-COUNT RULE.** The ×6.00 ceiling is a *model* of the same regeneration the FB leg *measures*.
It belongs on the exogenous command leg **only**. Multiplying both counts the loop's gain twice.

### What would separate the two command-side legs further — and what would not

1. ⭐ **The discriminator is not available offline and is not in the EPS.** It needs the echo path opened
   **at openpilot**: low-pass or decimate the **angle measurement** feeding `latcontrol_torque`, leaving the
   EPS untouched. That cuts the echo without touching the comb, the plant, the loop gain, or the authority
   the operator is protecting. `oplpf`'s territory. **§3b has already largely pre-empted it** — the residual
   coherence is 0.022 — so this is now a confirmation, not a discovery.
2. **The mirror image**: change the camera cadence or its phase without touching the angle path. That cuts
   the comb without touching the echo. Whether modeld's publish rate is reachable as a fork-side setting
   **I have not checked** — flagged, not asserted.
3. 🛑 **What would NOT separate them: another EPS-side filter on the command or the setpoint.** Comb and echo
   arrive through the *same* 0xE4 command path, so any EPS-side filter attenuates both by the same factor and
   cannot tell them apart. **V288 was exactly that experiment**, and even setting §4 aside it could never have
   discriminated.

---

## 6. What I could NOT determine

1. **Whether the comb is separable from the free command content on r5e, r62 and r63.** Only r39 has a clean
   long-window detuned null (3.7×). r63's is 1.3×. The **command-leg total** is reported for all five routes
   and is method-independent; the comb/free **split** is reported for r39 only.
2. **Whether `r5e_v288`'s zero lock fractions in §3a are real or a power limit.** Its grinding stratum is
   99 s and its measured floor rises to 0.45. r39's is 182 s with a floor of 0.16. **I read r5e as
   underpowered, not as a null**, and did not use it either way.
3. **The V288 and V289 mirror rows remain contaminated** by the missing caves. For V289 the contamination
   runs in the *safe* direction for my conclusion (the un-modelled notch would cut the 20 Hz comb further, so
   5.21 over-states it), and I flag that rather than leaning on it.
4. **Why the free (non-clock-locked) part of the command exists at all.** §3b says it is not an angle echo.
   What it is — plan noise, the lateral planner's own dynamics, quantisation — I did not establish.
5. **r22 (V112, stock map)** is in `modelrate`'s route list but has no build image in
   `burst_onset_triggers.IMG`, so the demand-gated f0 could not be built and it is excluded from §3.
   **r35 has no modeld cadence cache at all** and is excluded from every camera-clock test.
6. **I did not take `modelrate`'s step/hold distribution.** I asked for it and did not block on it — the
   ablation method does not need a reconstructed waveform, and I measured the comb's raw-count amplitude
   myself (§1d). If `modelrate`'s numbers differ from mine, **its wire characterisation should win on the
   command side** and §1d should be reconciled against it.

---

## 7. What this means for the operator's question

🛑 **REVISED after §X3.** He asked whether the grinding excitation can be **prevented** rather than the
resonance removed, and ruled out an LPF on the command because it costs authority.

**The answer is NO — but NOT for the reason I first gave.** My first answer was *"there is no command-side
excitation large enough to be worth preventing."* §X3 shows that is not safe: at the **measured** ζ
(0.0091–0.0224, `cyclekind`) rather than the inherited 0.029, the command-side budget on V282 is
**arithmetically capable** of sustaining the ring (ratio 1.54–3.64). **The sizing argument does not close
this, and I withdraw the version of it I first wrote.**

**The reason the answer is still NO is better, and it is ζ-free:**

- ⭐ **The excitation is ALWAYS THERE AND DOES NOT VARY.** `modelrate` measures the forcing flat at
  0.267–0.376 across six builds while the response varies **×98**; my §1e measures the comb flat-or-falling
  (×0.55–0.86) inside a route while the ring rises ×1.6–2.8. **A constant driver cannot explain a varying
  symptom** — and it equally cannot be "prevented", because it is the camera clock itself.
- **Removing it perfectly buys ~3 %, at most 8 %, of grinding amplitude** (`cyclekind`'s √(1−lock); my
  §1e supports it). **That is not worth a change.**
- **There is no echo to open**: removing the camera clock leaves no coherent command↔angle link (0.022).
- **Any EPS-side filter attenuates comb and echo identically and cannot discriminate them** — and §4 shows
  what such a filter buys at the ring's own amplitude: **−1 % to +9 %**. V288 was that experiment.

⇒ **The lever is ζ_eff — the loop's damping of the mode — not de-excitation.** That is EPS-side, it is
where the record already had it before either hypothesis was raised, and it is consistent with
`slewburst`'s trigger null, H1's amplitude null and `cyclekind`'s excited-resonance verdict, all reached
independently.

⚠ **The honest counterweight, updated.** The claim that the command side is *insufficient* now rests on
**r63 alone** — the one route below unity at every measured ζ (0.75 at best) — plus the cross-build inverse
relation (§X1/X2) and the two ζ-free falsifications (§1e, §3b). **It does NOT rest on r39, where the
command side is capable at the measured ζ.** If someone wants to keep the comb alive as the originator,
**V282 at low ζ is where it is still standing**, and §11d names the transient experiment that would settle
it: interrupt or phase-step the comb and time the ring's decay.

---

## 8. Reconciliation with `cyclekind`, and one number where we DISAGREE

`cyclekind`'s `FORCED-VS-LIMIT-CYCLE-2026-09-10.md` reaches the same verdict from a different direction
(11 routes, 6 builds, 715 episodes): **(C) excited resonance with a real but minority forced admixture**,
and its actionable figure is that *"perfectly removing the camera comb from the command would reduce the
grinding amplitude by √(1−lock) — about 3 % at the median route and at most 8 %."*

**That agrees with my verdict and is arrived at independently.** Its coherence-time-equals-ring-down-time
result is a cleaner discriminator than anything I ran, and my §1e (the comb does not grow with the ring)
is the same fact seen in amplitude rather than in phase.

🛑 **But one number does not reconcile, and I am flagging it rather than smoothing it over.**

| quantity | `cyclekind` | me (§3a) |
|---|---|---|
| camera-locked fraction of the **command** in-band energy | 0.19–0.33 (11 routes) | **+0.49** (r39 grinding) |
| camera-locked fraction of the **ring's grinding EXCESS** | **0.035–0.145** (11 routes) | **0.357** (r39 bar) |

My r39 bar figure is **2.5× its stated maximum**. The arithmetic behind mine is explicit — E_base 699 at
R2−floor 0.200 → E_lock 140; E_grind 8360 at R2−floor 0.344 → E_lock 2877; ΔE_lock/ΔE = 2737/7661 = 0.357
— so the discrepancy is in the **stratum or band definition**, not in the statistic: we both import the
same `r2_full`. Candidate crux, in order of likelihood:

1. **Stratum.** Mine is *burst peak ± 0.5 s* from the demodulation onset detector; `cyclekind`'s is its own
   episode set. Mine deliberately selects the loudest moments; its is broader.
2. **Baseline.** Mine is `engaged & outside every burst & v < 12`; a different quiet definition moves
   E_base and therefore ΔE.
3. **Band.** Mine is the full 18–22 Hz ring band; a narrower band around f0 would change the mix.

**I have not resolved it and should not be the one to.** `cyclekind` has 11 routes and 715 episodes against
my 4 routes, and this is precisely the quantity its study is built around — **its estimate should be
preferred over mine for the ring's lock fraction**, and §3a's 0.357 should be treated as an
upper-biased, loud-window-selected figure until the two strata are reconciled.

⭐ **None of my load-bearing conclusions depends on it.** §1b/§1c (the mirror sizing and the ×6 verdicts),
§1e (the comb does not grow), §3b (the partial coherence collapse) and §4 (the V288 describing function)
are all independent of the bar's lock fraction. If anything, a *lower* ring lock fraction — `cyclekind`'s —
strengthens the verdict against the comb rather than weakening it.

---

## 9. Scope note — openpilot-side changes are now IN SCOPE, with a named constraint

`memory/feedback/builds/feedback-no-openpilot-side-modifications.md` was **amended by the operator on
2026-09-10**: the 2026-07-28 blanket ban is superseded **for the grinding workstream only**. Fork-side
changes are now allowed *as fixes*, provided they do not limit the model's connection or steering
authority. Explicitly allowed: **measurement-side filtering/notching**, *"costs no command authority at
all, since it is in the feedback path"*. Explicitly forbidden, by name: **a low-pass filter on the
command**, added command lag, clipped output slew.

This matters for §5's recommendations and changes their standing:

- **§5.1 — low-pass or decimate the ANGLE MEASUREMENT feeding `latcontrol_torque` — is IN SCOPE.** It is
  measurement-side, in the feedback path, and costs no command authority. ⚠ **But on my own §3b result it
  would be a confirmation, not a fix**: residual command↔angle coherence after removing the clock is
  **0.022**, so there is no echo there to cut. Worth doing as a *test*, not as a *remedy*, and it should be
  proposed that way or not at all.
- **§5.2 — changing the camera cadence or phase — is also measurement/plan-side**, but the honest sizing is
  `cyclekind`'s: removing the comb perfectly buys **~3 %, at most 8 %**, of grinding amplitude. **That is
  not worth a change on its own**, and I would not propose it as a fix.
- **Nothing here licenses a command-path LPF**, which is the class the operator rejected by name — and
  which §1c shows would cost authority to buy at most the 20 % command-side budget anyway.

⇒ **The amendment opens a door that my own measurements then find little behind.** The lever the whole
decomposition points at remains the **FB leg** — the loop's own regeneration, 88–100 % — and that is
EPS-side.

---

# 10. THE THREE CRUX CHECKS — one passes, one partly weakens the claim, one FORCES A REVISION

Script `comb_crux_checks.py`, output `_scratch/comb_crux_checks.txt`. Each was written to *break* a claim
of mine. **One of them did.**

## X1 — bandwidth normalisation: PASSES, and the falsifier gets slightly STRONGER [EVIDENCE]

The concern was real: r63 is scored in 14–18 Hz and r39 in 18–22 Hz. Both are 4.0 Hz wide, but their
*fractional* widths differ (0.25 vs 0.20) and a Butterworth's shape follows the fractional width.
Redone with **equal absolute bandwidth centred on each route's own f0**:

| equal bandwidth | r39 `T_total` | r63 `T_total` | **r63/r39 ring** | r63 CMD share | r39 CMD share |
|---|---|---|---|---|---|
| 2.0 Hz | 45.42 | 98.35 | **2.17** | 0.029 | 0.208 |
| 3.0 Hz | 53.49 | 115.12 | **2.15** | 0.031 | 0.203 |
| 4.0 Hz | 57.30 | 124.96 | **2.18** | 0.035 | 0.207 |
| *published, per-build bands* | 57.21 | 125.86 | *2.20* | *0.041* | *0.202* |

**The ×2.2 is not a filter artefact** — it is 2.15–2.18 at every equal bandwidth. And r63's command share
*falls* to 0.029–0.035 under normalisation, so the falsifier is marginally stronger, not weaker.

## X2 — strata matching: the contrast is PARTLY a regime effect, and I am reducing the claim [EVIDENCE]

The loud windows are **not** the same kind of driving. r63's sit at higher speed and much higher load:

| route | v p50 | idx p50 | **abs(bar) p50** |
|---|---|---|---|
| r39 | 8.9 | 49.8 | **243** |
| r63_v289 | 12.6 | 51.5 | **581** |

Demand is well matched (50 vs 52); **speed and load are not.** Recomputing the ring contrast inside
**matched speed × demand cells** (13 cells, ≥ 8 s in both routes, whole-route bar amplitude at each
route's own f0 ± 1.5 Hz):

**weighted mean matched r63/r39 ring ratio = 1.71**, against 2.20 raw. Per-cell range **1.13 – 2.49**,
**12 of 13 cells above 1**.

⇒ **About a quarter of the raw contrast was driving regime. The claim stands but the magnitude comes
down: r63's ring is ~1.7× r39's in matched driving, not 2.2×.** I am revising the headline accordingly.
The command-leg ratio (0.30–0.45×) is unaffected by this, so the *inverse* relation survives intact.

## X3 — 🛑 ζ SENSITIVITY: THIS ONE RUNS AGAINST ME, AND I AM REVISING THE VERDICT

Every "sufficient / short" verdict in §1c rests on the ceiling `1/(1−e^(−2πζ))` at **ζ = 0.029** — the
record's figure, inherited from `slewburst`. **`cyclekind` measures phase coherence times implying
ζ = 0.0091–0.0224 — LOWER, which RAISES the ceiling and makes the command side MORE capable.** A lower ζ
is adverse to my conclusion, so it must be swept, not assumed:

| route | CMD | T_total | ζ=0.0091 | ζ=0.0150 | ζ=0.0224 | **ζ=0.029 (mine)** | ζ=0.040 |
|---|---|---|---|---|---|---|---|
| r39 | 11.56 | 57.21 | **3.64** | **2.25** | **1.54** | *1.21* | 0.91 |
| r5e_v288 | 6.98 | 52.61 | **2.39** | **1.48** | **1.01** | *0.80* | 0.60 |
| r62_v289 | 6.03 | 66.00 | **1.64** | **1.02** | 0.70 | *0.55* | 0.41 |
| **r63_v289** | 5.21 | 125.86 | **0.75** | **0.46** | **0.32** | *0.25* | 0.19 |
| r35 | 5.83 | 21.50 | **4.88** | **3.02** | **2.07** | *1.63* | 1.22 |

ζ at which each route's command leg becomes sufficient at ψ = 0:

| route | crossing ζ | vs the measured corpus range 0.0091–0.029 |
|---|---|---|
| r39 | 0.0359 | **ABOVE** — sufficient across the *entire* measured range |
| r35 | 0.0503 | **ABOVE** — sufficient across the entire range |
| r5e_v288 | 0.0227 | INSIDE |
| r62_v289 | 0.0152 | INSIDE |
| **r63_v289** | **0.0067** | **BELOW — insufficient across the entire measured range** |

🛑 **THE REVISION I OWE.** At the measured ζ rather than my assumed 0.029, **the command side is NOT
excluded as sufficient on V282, V288 or V281r3** — on r39 it reaches 1.54–3.64, comfortably above unity
and tolerant of ψ up to 49–74°. **My §1c verdict of "marginal, fails past ψ ≈ 34°" was too harsh, and the
§0 claim that neither mechanism is sufficient is WITHDRAWN for those three builds.**

**What survives X3 untouched:**
- **r63 is insufficient at every ζ in the measured range** (0.75 at the most favourable). The strongest
  single exclusion stands, and it is the one the headline falsifier rests on.
- **Every ζ-free result is unaffected**: §1e (the comb does not grow), §3b (the coherence collapse),
  X1 and X2 (the cross-build inverse relation).

⇒ **The sufficiency argument is the weakest leg of this analysis and I am no longer resting weight on it.
The falsification arguments are what carry the verdict.**

## X4 — `modelrate`'s cross-check: PARTIAL agreement, and the disagreement is informative

It predicted the mirror should reproduce ~2.3 for V282 and ~0.3 for V289. ⚠ **Not the same quantity, and
I say so before quoting it**: its ratio is command → **bar** (through the physical column); the mirror is
command → **delivered motor torque** and stops at the plant. Only the *ordering* is comparable.

| | ordering |
|---|---|
| mirror (mine) | r39 0.682 > r35 0.648 > r62 0.570 > r63 0.384 > r5e 0.363 |
| `modelrate` | r35 2.91 > r39 2.27 > r5e 1.34 > r62 0.30 > r63 0.00 |

**Agreeing:** {r39, r35} are the top two in both; r63 is bottom-two in both. **Disagreeing:** r5e (last
for me, third for it). ⭐ **And `modelrate`'s r63 = 0.00 is itself informative**: its bar figure is scored
in 18–22 Hz, so "no comb response in the bar at 20 Hz on V289" is **exactly what V289's notch at
20.04 Hz should do** — and my mirror cannot see it, because it does not implement that notch. The one
place we diverge most is the one place the mirror is known blind. That is a coherent reconciliation, not
an excuse: it predicts that a mirror *with* the notch would move r63 down to match.

---

# 11. INITIATOR vs AMPLIFIER (crux 2), and WHAT SEEDS IT (crux 3)

## 11a. The objection, stated at full strength

**The FB leg is near-tautological about proximate delivery.** The ring is in the measured wheel rate, so
of course the loop's D term delivers torque at the ring frequency. An 88/12 split shows where the torque
*proximately* comes from, **not what originated it**. A comb that seeds a small ring which the loop then
amplifies ×6 would produce exactly my 12/88 split. **The objection is correct as stated.**

## 11b. What makes it a statement about origination — and how much weight that now bears

The thing that converts proximate delivery into origination is the **accumulation ceiling applied to the
CMD leg**: if the exogenous drive times the most the loop can multiply it still falls short of the
observed ring, the command cannot be the originator regardless of what the FB leg proximately delivers.

**X3 has just shown how much weight that argument can bear, and it is less than I claimed.** It excludes
the command as originator **only on r63 (and r62 above ζ ≈ 0.015)**. On V282/V288/V281r3 it does not
exclude it at all. **So my decomposition alone cannot settle initiator-vs-amplifier on V282.** [stated
plainly, against my own earlier message]

**What settles it there is ζ-free evidence, not the decomposition:**

1. **§1e — the comb does not grow when the car grinds** (speed-matched ring ×1.6–2.8, comb ×0.55–0.86,
   significantly below 1 on 3 of 4 routes). An initiator whose amplitude is flat-or-falling while the
   response rises is not what *modulates* the response.
2. **§3b — no residual command↔angle coherence** (0.022) once the clock is removed: the echo is not there
   at all, so the command-side budget is comb-only.
3. **X1/X2 — the cross-build inverse relation**: r63's ring is 1.7–2.2× r39's on 0.30–0.45× the command
   drive.
4. **`modelrate`'s independent measurement**: the forcing (|Δ²cmd| model-phase fold) is **0.267–0.376 on
   all six builds, flat**, while the bar's 18–22 Hz energy runs 4.49e4 → 1.43e4 → 8360 → 1.08e4 → 459 →
   515 — **a ×98 spread in response on a constant drive.**

## 11c. ⭐ CRUX 3 — YES, AND IN THOSE WORDS

**At ζ ≈ 0.01–0.03 with the loop de-damping, no identifiable excitation is NEEDED. The ever-present
camera comb — constant across six builds — suffices, and what varies is the DAMPING, not the drive.
"What excites it" is the wrong question. The lever is damping.** [EVIDENCE for each premise below;
BELIEF for the synthesis.]

The premises, each measured, and each from a different agent or method:

| premise | measurement | source |
|---|---|---|
| the drive is essentially CONSTANT across builds | forcing fold R 0.267–0.376 on all 6 builds, vs a detuned null of 0.004–0.043 | `modelrate` |
| the RESPONSE varies by ×98 on that constant drive | bar 18–22 Hz energy 4.49e4 → 515 across 6 builds | `modelrate` |
| the drive does not track the symptom *within* a route either | comb ×0.55–0.86 while ring ×1.6–2.8, speed-matched | §1e, mine |
| the ever-present drive is ENOUGH at the measured ζ | r39 ratio 1.54–3.64 at ζ = 0.0091–0.0224 | X3, mine |
| the ring is a rung mode, not a forced line or a limit cycle | coherence time = ring-down time; Rayleigh envelope; no plateau, no hysteresis, no harmonics | `cyclekind` |
| no discrete trigger and no road input | ≤ 13 % of onsets; cap binds RR 0.83 [0.69, 0.96]; 30 IMU tests null | `slewburst` |

**The five agents' results compose into one mechanism**: a permanent, small, camera-locked excitation
that is always present and does not vary much; a lightly damped plant mode; and a loop whose damping of
that mode is the variable. **The grinding is loud when ζ_eff is small, not when the drive is large.**

⇒ **The operator's question — "can we prevent the excitation instead of removing the resonance?" — has
the answer NO, and now for a stronger reason than "the excitation is too small": the excitation is always
there and cannot be removed, and removing it perfectly would buy ~3 % (at most 8 %) of amplitude**
(`cyclekind`'s figure, which my §1e supports). **The lever is ζ_eff — loop damping — and that is EPS-side.**

## 11d. What would separate initiator from amplifier definitively, since I could not

**The test is a TRANSIENT one, not a spectral one.** Everything above is steady-state. The clean
discriminator is to **perturb the drive and watch the ring's ENVELOPE, not its level**:

1. ⭐ **Momentarily interrupt or phase-step the comb and time the ring's decay.** If the ring is a rung
   mode, removing the drive makes it decay with the ring-down time (≈ 0.27–0.87 s, 5–17 cycles) and then
   *stay* down until re-excited. If it is regeneratively sustained, it decays on the much slower
   closed-loop envelope, or not at all. This is a **fork-side, authority-free** change (one dropped or
   phase-shifted model frame), it is **in scope under the 2026-09-10 amendment**, and it needs no flash.
   `modelrate`'s or `oplpf`'s call — it is the single most informative experiment available.
2. **Measure ζ_eff per build directly** rather than inheriting 0.029. `cyclekind`'s coherence-time method
   already does this and should be adopted as the source of record. 🛑 **X3 shows that every sufficiency
   verdict in this kit is hostage to that one number, and it has been carried as an assumption.**
3. **What would NOT separate them:** any further steady-state spectral decomposition, mine included.

---

# 12. 🛑🛑 RETRACTION — TWO OF MY OWN HEADLINE RESULTS WERE ESTIMATOR ARTEFACTS

Added 2026-09-11 while adjudicating the `cyclekind` / `modelrate` lock-fraction dispute. Scripts
`comb_lockfrac_adjudication.py`, `comb_lockfrac_estimator_test.py`, `comb_does_not_grow_debiased.py`.

## 12a. The estimator, settled against a known ground truth

Two estimators were in use across three agents:

| | formula | used by |
|---|---|---|
| `R2 − maxfloor` | `max(R2 − max(R2 over detuned clocks), 0)` | `cyclekind`, **and me** |
| `R2_deb` | `sqrt(max(R2² − mean(R2²_detuned), 0))` | `modelrate` |

I settled it by building a signal with a **known** locked energy fraction *p* and running both:

| true p | `R2 − maxfloor` (err) | `R2_deb` (err) |
|---|---|---|
| 0.00 | 0.008 (+0.01) | 0.045 (+0.05) |
| 0.20 | 0.092 (**−0.11**) | 0.197 (−0.00) |
| 0.35 | 0.230 (**−0.12**) | 0.330 (−0.02) |
| 0.50 | 0.366 (**−0.13**) | 0.458 (−0.04) |
| 0.90 | 0.786 (**−0.11**) | 0.883 (−0.02) |

⇒ **`R2 − maxfloor` is biased LOW by ~0.12 whole-stratum and ~0.22 in 20 s blocks. `R2_deb` recovers the
truth to ±0.04.** The reason is dimensional: noise adds in **power**, so subtracting a floor in
**amplitude** over-subtracts, and increasingly so as power falls. **`modelrate`'s estimator is correct;
`cyclekind`'s and mine are a conservative lower bound that degrades with power.**

**And the proximity confound is clean** — a *free* mode 0.08 Hz from the camera clock (where r39's ring
actually sits: f0 19.92 vs f_model 19.9997) reads `R2_deb` = **0.018** over a 182 s stratum. The measured
lock is real, not an artefact of the ring merely being *near* the clock.

## 12b. 🛑 §1e IS WITHDRAWN — the comb DOES grow when the car grinds

§1e used `sqrt(2 · max(R2 − floor, 0) · E)` as the locked amplitude. **The bias depends on sample size,
and my quiet strata are 5–7× longer than my grinding strata** — so the quiet stratum was penalised less
and looked larger. **That manufactured the result.** Re-run with `R2_deb`, speed-matched, 2 m/s bins:

| route | comb ratio **as published (biased)** | **comb ratio, debiased** | 95 % CI | ring ratio |
|---|---|---|---|---|
| r39 | 0.66 [0.48, 0.80] | **1.29** | **[1.08, 1.59]** | 1.62 |
| r5e_v288 | 0.57 [0.30, 0.80] | **1.28** | [0.86, 2.09] | 1.86 |
| r62_v289 | 0.55 [0.00, 0.94] | **0.94** | [0.71, 1.21] | 2.12 |
| r63_v289 | 0.86 [0.00, 1.08] | **1.81** | [0.92, 2.38] | 2.68 |

**r39's CI now excludes 1 in the OPPOSITE direction.** The claim *"the comb does not grow when the car
grinds — significantly below 1 on three of four routes"* is **FALSE and is withdrawn in full.**

**What is left of it**, stated at its true strength: the comb grows **×0.94–1.81** while the ring grows
**×1.62–2.68**, so the response still outpaces the drive, but by **×1.3–2.3, not ×2.5–4.0**. That is
consistent with partial amplification. It is **no longer** the "constant driver, varying damping"
signature I claimed, and it must not be cited as one.

## 12c. 🛑 §3a's ANGLE-vs-BAR ASYMMETRY IS WITHDRAWN

Same cause. Debiased, on one stratum, r39:

| channel | raw R2 | `R2 − maxfloor` (**as published**) | **`R2_deb`** |
|---|---|---|---|
| 0xE4 command | 0.634 | 0.388 | **0.624** |
| BAR driver torque | 0.555 | 0.210 | **0.534** |
| **ANGLE 0x14A** | 0.418 | **0.192** | **0.401** |

**The angle is ~40 % camera-locked, not 2 %.** The claim *"the bar is 34 % camera-locked and the angle
only 2 % — a 20 Hz torque comb barely moves the column's inertia, and openpilot measures the angle"* is
**withdrawn, and so is the column-inertia explanation built on it.** It was the cleanest mechanical
sentence in my report and it was an artefact.

## 12d. What SURVIVES, and why

**Nothing that does not use a lock-fraction estimator is affected.** Specifically:

- **§1b/§1c — the mirror sizing** (CMD leg 11.56 = 20.2 % on r39; 5.21 = 4.1 % on r63). Band-stop
  ablation through `GI.simulate`; no R2 anywhere. **Survives.**
- **The r63 falsifier** — loudest ring on the smallest command drive — and **X1/X2** (bandwidth
  normalisation, strata matching). **Survive**; already independently stress-tested.
- **X3 — the ζ sensitivity.** Unaffected, and still the reason the sufficiency argument is weak.
- ⭐ **§3b — the partial coherence collapse** (0.388 → **0.022** with the clock removed, matched
  quadrature control **0.598**). This uses the in-phase/quadrature **projection**, a waveform operation,
  not a biased fraction. **Survives — and the corrected numbers EXPLAIN it better**: with the command
  62 % locked and the angle 40 % locked, the clock is exactly what they share, so removing it should and
  does collapse their coherence. **The echo falsification stands**: after the clock is removed, the
  angle's dominant free content still does not reappear in the command at any lag.

## 12e. The number, and what it means for the decision

**The true camera-locked fraction of r39's bar 18–22 Hz grinding energy is ≈ 0.50.** All three agents'
figures reconcile once each estimator's measured bias is restored: `cyclekind` 0.131 + 0.22 ≈ 0.35 ·
mine 0.396 + 0.13 ≈ 0.53 · `modelrate` 0.495. **Nobody's data was wrong; two of us used a biased
estimator.**

**TOTAL vs EXCESS is not the explanation and I report that against the brief:** on r39 the two agree to
within 2–5 % in *both* windowings (total 0.378 vs excess 0.396 whole-stratum; 0.128 vs 0.131 in blocks),
because the quiet stratum holds only ~10 % of the grinding stratum's in-band energy and has a similar
locked fraction. The factor decomposition is **F2 estimator ×4.09 · F1 windowing ×3.02 · F3 quantity
×0.98.**

⇒ **At a lock fraction of 0.50, perfectly removing the comb would cut the ring's amplitude by
1 − √(1−0.50) = 29 % (≈3 dB in energy)** — inside `modelrate`'s 18–56 % band, **not** `cyclekind`'s
3–8 %. **The decision moves toward `modelrate`.**

⚠ **Two counterweights the operator needs with that number, and neither is small:**

1. 🛑 **V289 IS ALREADY THE FLOWN EXPERIMENT FOR "REMOVE THE 20 Hz FORCING FROM THE LOOP", AND IT DID
   NOT CURE THE SYMPTOM.** Its notch removed the 20 Hz object entirely (0/1414 windows) and the grinding
   **relocated to 15–17 Hz and got worse** — matched speed × demand, r63's ring is **1.71×** r39's on
   **0.30–0.45×** the command drive. A comb fix may relocate the symptom rather than remove it, and the
   29 % is an upper bound on a **band-limited metric**, not on what the operator feels.
2. **The 29 % assumes the locked energy vanishes with the comb.** If the mode is rung by whatever
   broadband excitation remains, the loop's gain is unchanged and the ring returns at a lower but
   non-zero level. Nothing here measures that, and §11d's **transient** test — interrupt or phase-step
   the comb for one model frame and time the envelope decay — is still the experiment that would.

**Reconciling 50 % locked output with a 20 % command-side drive share** (§1b), which looks contradictory
and is not: a **phase-locked** drive accumulates **coherently** (amplitudes add) while random-phase drive
accumulates **incoherently** (powers add). A 20 % energy share of the drive that is coherent therefore
becomes a disproportionately larger share of the output's coherent energy. The two measurements are
consistent, and together they say the comb is a **minority of the drive that is over-represented in the
response because it is the only coherent part of it.**
