# Are grinding bursts TRIGGERED by discrete command events? — onset timing, five routes, four builds

Subagent `slewburst`, 2026-09-10. **ANALYSIS ONLY** — built nothing, flashed nothing, sent nothing on any bus.

Script `rlog-tools/studies/grind/burst_onset_triggers.py` (full output `_scratch/burst_onset_triggers.txt`, 1,036 lines;
onset times cached to `_scratch/burst_onsets.npz`). IMU/CAN extraction extension `rlog-tools/studies/grind/burst_imu_extract.py`
(caches `_scratch/imu_{r39,r62_v289,r63_v289}.npz`; `imu_r35.npz` was already on disk from task 5).

Routes, with the build each carries and the ring band used:

| tag | build | route id | engaged | ring band | measured f0 |
|---|---|---|---|---|---|
| `r39` | V282 | `…00000039--f56039af87` | 880 s | 18–22 Hz | 19.92 Hz |
| `r5e_v288` | V288 rev 2 | `…0000005e--03a9714d78` | 642 s | 18–22 Hz | 20.02 Hz |
| `r62_v289` | V289 rev 1 | `…00000062--1c7daa54e8` | 619 s | **14–18 Hz** | 14.75 Hz |
| `r63_v289` | V289 rev 1 | `…00000063--1d4b188022` | 588 s | **14–18 Hz** | 16.50 Hz |
| `r35` | V281 rev 3 | `…00000035--580292087d` | 920 s | 18–22 Hz | 19.34 Hz |

🛑 The V289 band is **14–18 Hz, not 13–18**: at 13–18 the demand-gated peak on r62 landed at **13.18 Hz**, which is the
low-demand 12.4–13.8 Hz road line, not the relocated grinding mode (STATE's two-object picture). Narrowing to 14–18 moved
it to 14.75 Hz. The r62 estimate is still the weakest of the five — flagged wherever it matters below.

---

## 0. VERDICT

**NO. There is no triggering event class. Not slew-cap binds, not index steps, not large single-frame
command steps, not slope discontinuities, not sign reversals — and not the road either.** [EVIDENCE]

The strongest candidate in the whole corpus, pooled over 514 onsets and 3,649 s of engaged time:

| candidate event class | pooled RR | 95 % CI | p (perm) | **attributable fraction of onsets** |
|---|---|---|---|---|
| **openpilot slew-cap bind** (\|Δcmd\| ≥ 122) | 1.22 | [1.01, 1.42] | 0.067 | **4.2 % [0.3 %, 8.2 %]** |
| \|Δcmd\| ≥ 80 | 1.20 | [1.04, 1.36] | 0.022 | 6.5 % [1.3 %, 11.6 %] |
| \|Δcmd\| ≥ 100 | 1.23 | [1.04, 1.42] | 0.025 | 5.5 % [0.9 %, 10.1 %] |
| demand-index jump ≥ 7 LSB in one frame | 1.18 | [1.00, 1.37] | 0.082 | 4.2 % [0 %, 8.6 %] |
| demand-index jump ≥ 4 LSB | 1.13 | [1.01, 1.25] | 0.092 | 6.8 % [0.5 %, 13.3 %] |
| **\|Δ²cmd\| ≥ 150** (slope discontinuity) | **0.93** | [0.69, 1.16] | 0.813 | **0 % [0 %, 2.0 %]** |
| command zero crossing | 1.19 | [0.98, 1.42] | 0.035 | 3.2 % [0 %, 7.1 %] |
| slew direction reversal | 1.01 | [0.95, 1.08] | 0.444 | 2.3 % [0 %, 13.0 %] |
| **loop-error zero crossing** | **0.76** | [0.65, 0.86] | 1.000 | 0 % (onsets *avoid* it) |

**The number that decides it is the last column.** Under the model *"a fraction f of onsets are triggered and so land in
the event window with probability 1; the rest fall at chance"*, `f = c(RR−1)/(1−c)` with `c` the window coverage. **No
command event class can account for more than ~13 % of burst onsets at the upper 95 % bound, and the operator's own
candidate — the slew-cap bind — is bounded at 8.2 %.** Removing every slew-cap bind from the drive would, at its most
generous, remove one grinding burst in twelve.

Three further results, each independently load-bearing:

1. **The command does not LEAD the ring at the fast scale.** After removing the seconds-scale co-modulation, the residual
   coupling between the ring envelope and \|Δcmd\| is **r = 0.016–0.051** (r² ≤ 0.0026 — a quarter of one percent of the
   envelope's fast variance), broad, and centred within ±50 ms of zero lag. §12.
2. **The road is not the trigger either, and the chassis never sees the mode.** IMU impulse classes give RR 0.0–2.5 with
   CIs through 1 (one marginal hit in 30 tests). And the in-band chassis elevation at onsets is **not band-specific**:
   ring-band/control-band ratio 0.74–1.24 on every channel and route. §6, §10.
3. 🛑 **The impulse framing does NOT rescue H1 — a Q ≈ 17 resonance buys DURATION, not AMPLITUDE.** This is the crux
   arithmetic the orchestrator asked for, and it comes out against the hypothesis. §7.

**What IS real:** a **seconds-scale** association. Windows with more command slew carry ~1.2–3× more onsets, after
stratifying on speed × demand index. That is a shared regime, not a trigger, and the two are cleanly separated by the
timing tests. §10.

---

## 1. The detector, and why it can be trusted

**Envelope.** Complex demodulation of the driver-torque bar at the route's own demand-gated ring `f0`, Gaussian-smoothed
with σ = 35 ms, zero phase. *Not* a bandpass: a 4 Hz-wide bandpass has a ~250 ms impulse response and would smear an
onset by up to half of that, which is fatal in a ±200 ms window. Demodulation smears symmetrically by ±35 ms and has no
group delay.

**Onset.** A peak above `max(50 raw, p90 of the engaged envelope)`, walked back to 0.30× of its own peak; that walk-back
point is the onset. Required: ≥150 ms below that level beforehand (so it is a burst *start*, not a re-peak inside one),
350 ms refractory, engaged throughout.

| route | N onsets | onsets/min | IOI p25/p50/p75 (s) |
|---|---|---|---|
| r39 | 110 | 7.50 | 2.27 / 4.19 / 10.33 |
| r5e_v288 | 108 | 10.10 | 1.52 / 3.29 / 6.54 |
| r62_v289 | 80 | 7.76 | 1.60 / 4.12 / 8.19 |
| r63_v289 | 82 | 8.36 | 1.28 / 3.04 / 10.07 |
| r35 | 134 | 8.74 | 1.79 / 3.57 / 9.06 |

The inter-onset interval distribution is **broad and heavy-tailed**, not periodic: 9–16 % of intervals sit in 0.35–1.0 s,
a mode around 2–5 s, and 17–29 % beyond 10 s. **The "re-fires every 1.5–2 s" morphology the operator reported on r63 is
present but is not the dominant spacing** — on r63, 1.0–2.0 s holds 20 of 79 intervals.

**VALIDATION A — the r35 incident [EVIDENCE].** The detector places exactly **one** onset in t 1010–1022 s, at
**t = 1016.78 s**, with its peak at **t = 1017.22 s, envelope 598 raw.** `GRIND-INCIDENT-r35-2026-09-03.md` independently
reports the envelope growing from 41 raw at ~1016.4 to a **500-raw peak at t 1017.2**, and the operator's own wall-clock
mark of 23:48:21 maps to route t 1016.7. The detector reproduces the record's anatomy to ~0.4 s on onset and 0.02 s on peak,
having been written without reference to it.

**VALIDATION B — the operator's in-drive bookmarks.** 3 of 6 land on an onset (r5e t 820.15 → nearest onset **+0.17 s**,
envelope 499; r62 t 917.78 → **−0.03 s**, envelope 335; r63 t 684.30 → −5.54 s, envelope 215). ⚠ **The two r39 bookmarks
produced no onset at all** (envelope p90 only 62 and 36 there, below that route's threshold of 95). Either those two marks
were a different symptom, or the detector's absolute floor is too high for quiet episodes. **Stated as a limitation, not
explained away.** It does not affect the hazard results, which are internally normalised.

**The machinery demonstrably CAN see real time structure.** `E_zerocross` — zero crossings of the loop error — comes back
at **RR 0.76 [0.65, 0.86], p = 1.000**: onsets systematically *avoid* the error's zero crossings, which is mechanically
what you expect (at a ring onset the error is large, not crossing). That is a positive control on the detector, the event
construction and the null all at once. A pipeline that finds a strong, correctly-signed negative is not a pipeline that is
blind to a positive.

---

## 2. The base rates — why this had to be tested carefully

Candidate events are **not rare**. Per engaged second, and as a fraction of engaged time covered by the (0, +120] ms window:

| class | events/s (r39 … r35) | window coverage |
|---|---|---|
| slew-cap bind | 2.9 – 7.8 | 0.11 – 0.21 |
| \|Δcmd\| ≥ 20 | 24.7 – 32.9 | **0.68 – 0.91** |
| demand-index step ≥ 1 LSB | 50.3 – 59.5 | **0.98 – 0.99** |
| index jump ≥ 7 LSB | 3.7 – 8.3 | 0.15 – 0.23 |
| \|Δ²cmd\| ≥ 150 | 1.5 – 2.9 | 0.09 – 0.14 |

🛑 **`idx_step` covers 98–99 % of engaged time.** A demand-index crossing happens on essentially every frame; it is
structurally incapable of showing a hazard ratio and its RR of 0.99–1.01 is an arithmetic identity, not a result. The same
caution applies to `dcmd>=20` (coverage 0.68–0.91), whose RR of 1.05–1.19 sits against a ceiling of `1/c` ≈ 1.1–1.5. **Any
reading of those two rows as evidence either way would be wrong**, and they are reported only so the ceiling is visible.

The classes that *can* carry information are the ones with coverage ≲ 0.25: cap binds, \|Δcmd\| ≥ 80/100, index jumps ≥ 7,
\|Δ²cmd\| ≥ 150, command zero crossings.

---

## 3. Hazard ratios per route — the null, route by route

Full table in §3 of the output. The pattern:

- **`cap_bind`**: RR 1.01, 1.26, 1.03, **1.61**, 1.19 (r39, r5e, r62, r63, r35). Only r63 is elevated, and **r63's own
  circular-shift null already sits at 1.12** — that route has structurally more coincidence than the others. p = 0.060.
- **`idx_jump>=7`**: 0.99, 1.35, 0.93, 1.58, 1.08. Same story, same single route.
- **`d2cmd>=150`** — the operator's "knotted ramp" candidate: 0.57, 1.00, 0.86, 1.59, 0.62. **Three of five routes are
  below 1**, and the two lowest (r39 0.57, r35 0.62) are the two longest routes.
- Tightening the window to [0, +50] ms does not sharpen anything; loosening to [−120, 0] (a control in which the onset
  would have to *precede* the event) gives the same values.

**Per-route power is the limiting factor and must be stated: with 80–134 onsets and coverage ~0.15, a single route's 95 %
CI is roughly ±0.45 on RR.** A single route can exclude RR > 2 for cap binds; it cannot exclude RR = 1.3. That is exactly
why §8 pools.

---

## 4. Lead/lag correlograms — the shape of the (non-)effect

±500 ms, 20 ms bins, same circular-shift null, z per bin. The signature to look for was a **sharp excess in the bins just
after 0**. What the data show instead, on every route and every class, is a **broad, flat elevation of z ≈ 1–2 spread over
the entire ±500 ms with no peak anywhere near zero**:

```
r5e_v288 / cap_bind, z per 20 ms bin
 lag ms  -490 -450 -410 -370 -330 -290 -250 -210 -170 -130  -90  -50  -10  +30  +70 +110 +150 +190 +230 +270 +310 +350 +390 +430 +470
 z        1.5  0.6  0.0  1.0  1.5  1.6  1.6  2.4 -0.0  2.3  1.7  2.0  1.8  1.1  1.5  1.1  1.2  1.4  0.9  1.2 -0.1  1.6  1.5  1.1  0.1
                                                          ^ no peak at 0; the whole curve is lifted
```

That is the signature of **two series that both cluster in the same busy seconds**, which is the seconds-scale association
of §10 — not of an impulse and its response.

The one exception worth naming honestly: **r63 / cap_bind shows z 3.0 / 3.3 / 2.6 at −10 / +10 / +30 ms** over a
background of ~1.5 — a genuine local bump at lag zero, on one route out of five. r62, the *same build on the same tune*,
shows a uniformly **negative** correlogram. **A feature that reverses sign between the two routes of one build is not a
mechanism.** [BELIEF on that reading; EVIDENCE for the numbers.]

---

## 5. Dose–response — the real, seconds-scale effect

5 s engaged windows, split at the median of each slew statistic **within** strata of speed {0–3, 3–8, 8–15, 15+ m/s} ×
demand index {0–5, 5–20, 20–60, 60+}, so neither the engaged/manual speed confound nor the low-demand road line can drive
it. Ratio = onset rate in high-slew windows ÷ low-slew windows, with a 2,000-draw bootstrap over windows:

| route | rms \|Δcmd\| | cap-bind duty | idx-crossing rate | rms \|Δ²cmd\| |
|---|---|---|---|---|
| r39 | 1.38 [0.95, 2.08] | 1.23 [0.81, 1.80] | 1.26 [0.87, 1.87] | **1.66 [1.15, 2.50]** |
| r5e_v288 | 1.41 [0.93, 2.30] | 1.35 [0.90, 2.15] | 1.00 [0.64, 1.59] | 1.13 [0.74, 1.82] |
| r62_v289 ⚠ | **3.06 [1.73, 6.59]** | **1.95 [1.15, 3.30]** | **2.71 [1.59, 5.42]** | **2.41 [1.40, 4.63]** |
| r63_v289 | 1.20 [0.65, 2.37] | 0.87 [0.41, 1.85] | **1.98 [1.08, 3.96]** | 1.69 [0.90, 3.21] |
| r35 | 1.44 [0.95, 2.19] | **1.56 [1.06, 2.25]** | **1.52 [1.02, 2.37]** | 1.39 [0.92, 2.14] |

**This IS real** — 18 of 20 point estimates are above 1, and five CIs exclude it — **and it is the kernel of truth in the
operator's intuition.** But it is an association at the **five-second** scale, and §4 and §12 show there is no
corresponding structure at the **frame** scale. Busier command ⇒ more grinding seconds; a given command step does not
start a given burst.

⚠ r62 is the outlier that drives the impression of a strong effect, and it is the route whose ring `f0` was hardest to pin
(14.75 Hz, closest to the road line). **Do not quote r62 alone.**

---

## 6. THE FALSIFIER — the road, tested explicitly, and returning a null as well

Device IMU (accelerometer + gyroscope, ~101 Hz hardware timestamps), impulse events = peaks of the 30 ms envelope of the
>5 Hz high-passed channel above that channel's own p99, 200 ms refractory. Same hazard machinery, same null, same window.

**30 route × channel tests. RR ranges 0.00 – 2.54. One is nominally significant — r62 gyro_x(roll), RR 2.54 [0.95, 4.45],
p = 0.027 — which at 30 uncorrected tests is what chance produces, and it is on the same weak route.** Every other cell
has a CI through 1. **The road is not the trigger.** [EVIDENCE]

And the deeper check, which also rules the road out as a *carrier*: the in-band chassis energy at onsets is elevated
1.2–1.8× over engaged baseline on every channel — **but so is a control band at 28–38 Hz.** Ring ÷ control:

| route | accel_y (lat) | accel_z (vert) | gyro_x (roll) |
|---|---|---|---|
| r39 | 0.88 | 1.24 | 0.91 |
| r5e_v288 | 0.74 | 1.14 | 0.90 |
| r62_v289 | 1.01 | 0.94 | 1.00 |
| r63_v289 | 0.99 | 0.97 | 1.09 |
| r35 | 0.81 | 1.01 | 0.89 |

**All ≈ 1. The chassis is simply broadband busier during a burst; it does not carry the mode.** That reproduces the r35
incident's finding ("gyro 18–22 Hz 0.0003–0.0005 rad/s, identical to the engaged minute before") across four more builds
and 3,649 s, and it is consistent with the 48-event record. **The grinding mode is torsional and stays inside the column.**

---

## 7. 🛑 SIZING — the impulse framing does NOT buy a factor of Q

This is the check that was supposed to reconcile the operator's intuition with H1's amplitude null. **It does not
reconcile it. It closes it.** [EVIDENCE — the arithmetic is below and is reproducible from the script.]

**The premise under test was that a Q ≈ 17 mode rings 12–32× larger than the impulse that started it.** That premise is
false. Q is the amplification of a **sustained sinusoid** at `f0`; it is not the amplification of an **impulse**.

For `H(s) = ωn²/(s² + 2ζωn s + ωn²)` with DC gain 1, the impulse response is
`h(t) = (ωn/√(1−ζ²))·e^(−ζωn t)·sin(ωd t)`, so a **unit-area** impulse peaks at `ωn/√(1−ζ²)`:

| route | f0 | ωn | closed form | numeric | ringdown 1/e |
|---|---|---|---|---|---|
| r39 | 19.92 Hz | 125.2 rad/s | 125.2 /s | 127.2 | 275 ms = **5.5 cycles** |
| r63_v289 | 16.50 Hz | 103.7 rad/s | 103.7 /s | 105.5 | 333 ms = **5.5 cycles** |

A **single-frame (10 ms) kick of height h** delivers area `h × 0.01` and therefore rings to a peak of

```
peak = h × 0.01 × 125.2 = 1.25 × h          (r39)
peak = h × 0.01 × 103.7 = 1.04 × h          (r63, V289)
```

**≈ 1× the kick.** ζ = 0.029 gives the ring its **length** — 5.5 cycles to 1/e, which is exactly the "decaying burst"
morphology the operator describes — and **nothing in amplitude.**

Repeated kicks accumulate, but bounded:

| driving | r39 peak ÷ one kick | r63 peak ÷ one kick |
|---|---|---|
| random-phase Poisson, 4/s | ×1.61 | ×2.12 |
| random-phase Poisson, 8/s | ×2.38 | ×2.49 |
| random-phase Poisson, at f0 | ×3.68 | ×3.20 |
| **phase-locked, once per ring cycle** | **×5.61** | **×6.02** |

with the analytic ceiling `1/(1−e^(−2πζ)) = 1/(1−0.833) = 6.00` — **not Q = 17.2.** ⭐ And *phase-locked kicking at f0 is,
by definition, the closed-loop de-damping picture already in the record*: a command whose in-band content is locked to the
ring is an **echo of it**, not an exogenous cause.

**Now the delivered dose, read through the byte-exact 1 kHz mirror** (`GI.simulate`, live arms, real measured wire rate
and bar; one frame of the command displaced by +122 counts and held, every other input untouched; the difference in T is
the kick the step actually lands on the plant):

| route | ΔT peak | **ΔT in the ring band** | measured in-band T during loud grinding | one kick ÷ ring |
|---|---|---|---|---|
| r39 (V282) | 171.5 | **4.65** | 57.2 | **0.081** |
| r5e_v288 | 172.0 | **4.42** | 73.2 | **0.060** |
| r63_v289 | 170.0 | **6.84** | 127.7 | **0.054** |

**A slew-capped command frame delivers 4.4–6.8 counts of ring-band torque. The ring carries 57–128.** Even granting the
most generous accumulation the physics allows — the ×6.0 phase-locked ceiling, which would make the command an echo — a
train of cap binds reaches 26–41 counts against 57–128 measured, still short by **2.2–3.1×**. At the realistic
random-phase accumulation for the measured 3–8 cap binds/s (×1.6–2.4), it is short by **5.4–7.6×**.

⇒ **H1's amplitude verdict survives the impulse reframing intact, and is strengthened by it.** H1 compared a steady-state
residual; this compares an impulse against a ringdown, exactly as asked, and the gap is the same order. The 12–32× factor
the reframing was supposed to supply does not exist.

---

## 8. Direction — and a confound I had to retract mid-analysis

🛑 **§11a of the output is CONFOUNDED and must not be read as an echo finding.** I generated it, then killed it. Recording
why, because the trap is easy to fall into: an onset is *defined* as a point where the envelope goes from low to high, and
\|Δcmd\| correlates with the envelope at r ≈ 0.21–0.35 at **zero** lag. So \|Δcmd\| is mechanically lower before an onset
and higher after it, **whatever the causal order**. The circular-shift null does not remove this — it destroys alignment
entirely, so its expected pre/post difference is 0, and *any* zero-lag correlation manufactures a "significant" post-minus-pre
excess. §11a measures *"does \|Δcmd\| track the envelope?"* (yes, strongly), not *"does it lag it?"*.

**The clean test (§12)**: high-pass both series above 1.0 Hz inside each engaged run — removing the seconds-scale
co-modulation that dominates the raw cross-correlation — then cross-correlate. `r(k) = ⟨env(t)·|Δcmd|(t+k)⟩`; k > 0 means
the command comes later (echo), k < 0 means it comes first (trigger).

| route | peak lag | 95 % CI on the lag (block bootstrap) | r at peak | **r²** |
|---|---|---|---|---|
| r39 | −20 ms | [−30, −10] ms | 0.0514 | 0.0026 |
| r5e_v288 | −20 ms | [−300, +260] ms | 0.0475 | 0.0023 |
| r62_v289 | −50 ms | [−280, +110] ms | 0.0353 | 0.0012 |
| r63_v289 | −10 ms | [−290, +250] ms | 0.0164 | 0.0003 |
| r35 | +40 ms | [−150, +50] ms | 0.0455 | 0.0021 |

**Four of five peak slightly negative (command leading by 10–50 ms); one peaks positive. Only r39's lag CI excludes zero,
and it puts the command ahead by 10–30 ms.** But the magnitude settles it: **r ≤ 0.051, i.e. the command's fast slew
explains at most 0.26 % of the ring envelope's fast variance.** Restricting to the loudest decile of engaged time (§12b)
changes nothing — peaks at −300 to −10 ms, r 0.028–0.054, two of them negative-signed.

⇒ **There is a whisper of the command leading, at the right sign for a weak trigger, and it is far too small to be the
symptom.** [EVIDENCE for the numbers; BELIEF that the negative-lag sign on 4/5 routes is a real weak trigger rather than
noise — the CIs do not support asserting it.]

---

## 9. What I could NOT determine

1. **Whether the two r39 bookmarks are a detector miss or a different symptom.** The envelope there (p90 62 and 36) is
   below r39's own threshold. If the operator's grinding percept extends to episodes at half the amplitude my detector
   requires, my onset set is biased toward loud bursts and the hazard tests inherit that bias. **A threshold sweep would
   settle it; I did not run one.**
2. **Whether a trigger exists below the corpus's resolution.** Pooled MDE is RR ≈ 1.19–1.34 depending on class. A true
   trigger accounting for ~3 % of onsets would be invisible here. The *bounds* in §0 are therefore the result, not the
   point estimates.
3. **r62's ring frequency.** 14.75 Hz, the closest of the five to the low-demand road line, and r62 is the single route
   driving the strongest dose–response and the only significant IMU cell. Its results should not be quoted alone.
4. **Whether onsets align with `modeld`'s 20 Hz cadence.** Out of scope by instruction — the sister agent `modelrate` has
   the spectral side. I did no spectral work on the command's own cadence and deliberately did not duplicate H1 or the
   wire study.
5. **Taper-arm changes** were not tested as an event class: the 0xE4 byte-2 arm field is not in the v280 route cache.
   Engagement transitions were used as the control instead (RR 0.00 everywhere — but that is a detector artefact, since the
   onset rule requires 150 ms of prior engaged quiet, so it carries no information).
6. **The seconds-scale association's mechanism.** More slew ⇒ more grinding seconds is solid; *why* is not established
   here. The natural reading is that both track loop gain / operating point, which is the existing plant-mode picture,
   but I did not test it.

---

## 10. What this means for the operator's question

He asked to **prevent the ring excitation instead of removing the ring resonance**, and explicitly ruled out an LPF on the
command because it costs authority.

**On this evidence there is no excitation event to prevent.** [EVIDENCE for the bound; BELIEF for the recommendation.]

- Removing 100 % of slew-cap binds bounds out at **≤ 8.2 %** of burst onsets, point estimate 4.2 %.
- Removing every large single-frame command step bounds out at **≤ 13.3 %**.
- Slope discontinuities — the knotted-ramp candidate — are at **0 % [0, 2.0 %]**, and onsets slightly *avoid* them.
- A capped command frame lands **4.4–6.8 counts** of ring-band torque where the ring carries **57–128**, and the high-Q
  ringdown supplies **no amplification** to close that gap.

This is consistent with — and independent of — what V288 rev 2 already demonstrated on the car: it made every setpoint
step ~11× finer and **the grinding did not move**. The reference/excitation-side class was called exhausted then; the
timing test now closes the last door that H1's amplitude argument had left open.

⚠ **The honest counterweight:** the seconds-scale dose–response is real and is what the operator is feeling when he says
"high slew → grinding". A lever that reduced command slew *sustainedly* — not one that removed individual steps — would
plausibly reduce grinding seconds by something like the §10 ratios suggest. But that lever is a filter on the command,
which is precisely what he has ruled out on authority grounds, and the §7 sizing says the mechanism would be gain, not
de-excitation.

---
---

# ADDENDUM — SIZING THE PHASE-LOCKED ECHO (2026-09-10, same day)

Follow-up requested by the orchestrator after the trigger null was accepted. Script
`rlog-tools/studies/grind/burst_echo_sizing.py`, output `_scratch/burst_echo_sizing.txt`.
**ANALYSIS ONLY.** The trigger question is not re-opened; this sizes the one regime the first report
left open — a **sustained, phase-locked** echo at `f0`, whose accumulation ceiling is
`1/(1−e^(−2πζ)) = 6.00` at ζ = 0.029.

`oplpf`'s candidate mechanism [its EVIDENCE]: openpilot's lateral measurement is the CAN `0x14A`
steering angle — 100 Hz, 0.1°/LSB, unfiltered — reaching the command through P only. One LSB → 13.2
raw `0xE4` counts at 5 m/s, 20.6 at 15, 52.8 at 30. The measured 20 Hz command line is 15–40 counts.
(The 0.1°/LSB is confirmed independently here from the route extractor: `ang = i16be(d,0) * -0.1`,
so the cached `ang` is in degrees.)

## A1. VERDICT ON THE ECHO — arithmetically capable, but **already falsified on the car**

**Item 1 asked for the ratio. Here it is, and it flips the sign of the first report's sizing result.**

Byte-exact 1 kHz mirror, command replaced by `cmd(t) + A·sin(2π f0 t)`, every other input exactly as
measured, 10 loudest 3 s engaged windows per route, median. `dT_band` is the steady-state in-band
amplitude — the **same measure** as the capped-step row (4.4–6.8) and `T_band` (57–128) in §7.

| route | A (raw) | dT_band | ratio to measured ring | **×6.0 ceiling** | verdict |
|---|---|---|---|---|---|
| **r39 (V282)** | 13.2 | 8.30 | 0.145 | 0.87 | short by ×1.1 |
| **r39 (V282)** | **20.6** | **13.17** | **0.230** | **1.38** | **SUFFICIENT** |
| **r39 (V282)** | 40.0 | 24.28 | 0.424 | 2.55 | SUFFICIENT |
| r5e_v288 ⚠ | 20.6 | 9.83 | 0.187 | 1.12 | SUFFICIENT |
| r63_v289 ⚠ | 20.6 | 11.91 | 0.095 | 0.57 | short by ×1.8 |
| r63_v289 ⚠ | 40.0 | 23.12 | 0.184 | 1.10 | SUFFICIENT |

**A sustained echo delivers 8–31 in-band counts — 2 to 7× what a slew-capped step delivers (4.4–6.8).**
On V282 at `oplpf`'s 15 m/s figure the ×6.0 ceiling reaches **1.38**, i.e. **the echo is arithmetically
capable of sustaining the whole measured ring.** [EVIDENCE for the delivery numbers; the ×6.0 is the
best case, see A2.]

Delivery is very nearly **linear** in A (A ×4.0 → dT_band ×3.69 on r39, ×3.66 on r63), so the quantiser
does not swallow a sub-LSB echo — it dithers across the index boundaries on top of the moving command.

⚠ **r5e_v288 and r63_v289 rows overstate delivery and must not be quoted alone.** `GI.simulate` is the
V282-era chain mirror: it reads each build's own calibration cells from that build's image, but it does
**not** implement V288's pre-filter cave or V289's notch cave. **Only the r39 (V282) row is a clean
mirror result** — V282's cave is read-only r24 comparator telemetry and adds no filter to the rate path.

### A1b. And then the on-car test that already exists — **V288 rev 2 flew this exact lever**

`docs/BUILD-LINEAGE.md:341-348`: V288 rev 2 is a **reference pre-filter**, *"the first build V38→V288 to
touch the reference the LKAS rate PID compares against"* — first-order, corner 10.3 Hz at 1 kHz, DC gain
exactly 1 (`y += (x−y)>>4`). **A command echo enters exactly there**: cmd → idx → map → setpoint, and the
pre-filter sits on that setpoint.

```
|H(20.0 Hz)| of y += (x-y)>>4 at 1 kHz = 0.4572   ->  the echo's drive cut x2.19  (-6.8 dB)
|H(16.5 Hz)|                           = 0.5287   ->                     x1.89  (-5.5 dB)
```

Re-running the r39 mirror at the attenuated amplitude (exact for this purpose — the perturbation is what
the pre-filter scales):

| route | A | A×\|H\| | dT_band | ratio | **×6.0 ceiling** | vs unfiltered |
|---|---|---|---|---|---|---|
| r39 | 20.6 | 9.4 | 5.94 | 0.104 | **0.62** | ×0.45 |
| r39 | 40.0 | 18.3 | 11.69 | 0.204 | **1.23** | ×0.48 |

**Under the echo hypothesis V288 should have taken the sustaining capacity from 1.38 to 0.62 — from
just-above-unity to unable — and the 20 Hz ring should have collapsed.**

**What V288 rev 2 actually did on the car** (r5e_v288, census reproduced exactly from the V282 pipeline,
`GRIND1-CENSUS-V288-R5E-2026-09-08.md`): same 20.0–20.4 Hz line at all three operator bookmarks, *mark 3
louder than any V282 episode*; **258 vs 239 episodes/h; envelope p50 126 vs 127; f 20.06 vs 20.03 Hz;
rung-bell ratio 2.41 vs 2.25; no new line above 22 Hz** — with the cave demonstrably running (b4.5 live
on 99.5 % of engaged frames) and the D-clamp bind duty at ×0.03.

⇒ **Every ring statistic unchanged. The echo cannot be the DOMINANT sustaining leg.** [EVIDENCE, on-car]

🛑 **This on-car null outranks my offline sizing, and I am reporting it against my own E1 result.** E1
says a sustained echo of the measured amplitude is *arithmetically capable*; A1b says that when the
capability was actually cut by 2.19× on the car, **nothing happened**. A *contributing* leg of a few tens
of percent is not excluded — V288 would then have predicted only a modest change, inside the noise of
that comparison — but **the dominant-cause reading is falsified by a flown build.**

## A2. Phase (item 2)

**A2a — delivered amplitude is phase-independent, as it should be.** Sweeping the injection phase over a
full cycle at A = 20.6 changes `dT_band` by **3.0 % (r39) and 6.8 % (r63)** of the mean. The setpoint path
is open loop in the mirror, and the quantiser/map knots add only that few percent. [EVIDENCE]

**A2b — what phase actually controls.** Not delivery: *sign of damping*. For a modal coordinate driven by
a feedback torque of return-ratio magnitude |L| at `f0` and phase ψ against the **ring velocity**,
`Δζ = −(|L|/2)·cos ψ` — ψ = 0 pure de-damping, ψ = 90° pure frequency shift, ψ = 180° pure damping. **The
6.00 ceiling in A1 assumes ψ = 0 exactly**; at ψ it is ≈ `6.00·|cos ψ|`:

| ψ | 0° | 30° | 45° | 60° | 90° |
|---|---|---|---|---|---|
| ceiling | 6.00 | 5.20 | 4.24 | 3.00 | 0.00 |

So **A1's "SUFFICIENT" verdicts are the most generous possible reading** — any real phase offset reduces
them, and beyond ψ ≈ 43° even the r39 / A = 20.6 row falls below unity.

**A2c — what the wire says, and it does not support the simple model.** Measured `0x14A` angle → `0xE4`
command cross-phase at `f0` in the loud windows:

| route | coherence | phase | implied lag |
|---|---|---|---|
| r39 | 0.535 | **+5.9°** | −0.8 ms |
| r35 | 0.558 | **−1.2°** | +0.2 ms |
| r63_v289 | 0.386 | −117.3° | 19.7 ms |
| r5e_v288 | 0.078 ⚠ | (97.5°) | — |
| r62_v289 | 0.043 ⚠ | (−29.6°) | — |

🛑 **On the two routes with usable coherence the command is essentially IN PHASE with the angle at ~0 ms
lag — which openpilot cannot physically produce.** A CAN-in → 10 ms control tick → CAN-out round trip is
≥ 20 ms, i.e. ≥ 144° at 20 Hz. **A measured ~0° is therefore evidence that this cross-phase is not
measuring openpilot's round trip at all.** [EVIDENCE for the numbers; BELIEF for that reading.]

## A3. Wire gain (item 3) — the measured ratio does **not** match the predicted P-path gain

Measured `|CMD(f0)| / |ANG(f0)|` in 2 s engaged windows, coherence-gated ≥ 0.3 at `f0` (median coherence
0.67–0.79, so these are real coherent lines), against `oplpf`'s prediction ×10 (counts per **degree**):

| route | 0–8 m/s | 8–22 m/s | 22+ m/s |
|---|---|---|---|
| predicted | 132 | 206 | 528 |
| r39 (V282) | 754 (**×5.7**) | 772 (**×3.8**) | 1079 (×2.0) |
| r35 (V281r3) | 698 (×5.3) | 737 (×3.6) | 1058 (×2.0) |
| r5e_v288 | 1132 (×8.6) | 702 (×3.4) | 713 (×1.4) |
| r62_v289 | 571 (×4.3) | 396 (×1.9) | 311 (**×0.59**) |
| r63_v289 | 431 (×3.3) | 219 (×1.1) | 216 (**×0.41**) |

**Three things say this ratio is not openpilot's P-path gain** [EVIDENCE]:

1. **It is 1.1–8.6× the prediction, not ≈ 1.**
2. **The speed scaling runs the WRONG WAY.** The prediction rises 4.0× from 5 to 30 m/s; the measurement
   is flat or *falls* (r63: 431 → 216). `meas/pred` therefore collapses from ×3.3–8.6 at low speed to
   ×0.4–2.0 at high speed.
3. 🛑 **It differs 3.4× BETWEEN BUILDS where openpilot was unchanged** (r39/r35 ≈ 750 c/deg at 8–22 m/s;
   r63 = 219). A quantity that is a property of openpilot alone cannot depend on which firmware is in the
   EPS. **It does, so it is not that quantity** — it is dominated by the shared ring appearing in both
   signals, which is direction-blind.

⇒ **A3 cannot confirm the echo mechanism, and it flags a defect in the predicted constants or in the
premise behind them.** Handing that back to `oplpf` rather than resolving it: the conversion from
openpilot's torque units to `0xE4` counts runs through the live torque-controller parameters (the record
has them running the defaults 1.689/0.212 on every modded route, `liveValid` 0), and the operator runs
**force_torque_controller**, so an assumed-parameter derivation of 13.2 / 20.6 / 52.8 should be
re-checked. [BELIEF — I did not verify `oplpf`'s derivation.]

## A4. Threshold sweep (item 4) — **the trigger null gets STRONGER, and the r39 bookmarks come in**

| hi_abs | hi_q | r39 thr | pooled N onsets | **cap-bind RR** | 95 % CI | **f_trig** |
|---|---|---|---|---|---|---|
| 50 | 0.90 | 95 | 514 | 1.22 | [1.00, 1.42] | 0.042 [0, 0.082] |
| 40 | 0.85 | 77 | 684 | 1.06 | [0.89, 1.23] | 0.011 [0, 0.044] |
| 30 | 0.80 | 64 | 790 | 0.98 | [0.82, 1.15] | 0.000 [0, 0.028] |
| 25 | 0.75 | 55 | 915 | 0.90 | [0.76, 1.05] | 0.000 [0, 0.009] |
| 20 | 0.70 | 48 | 992 | **0.83** | **[0.69, 0.96]** | 0.000 [0, 0.000] |

**The relative risk falls monotonically as the detector is opened up, and at the two lowest thresholds it
is significantly BELOW 1.** The 4.2 % attributable fraction in §0 was the *most generous* reading
available; a detector that also catches half-amplitude episodes puts it at **0 %**, with slew-cap binds
mildly **anti**-correlated with onsets.

**The two r39 bookmarks are captured from hi_abs = 40 down**: nearest onset **−0.24 s** for the first at
every threshold ≤ 40, and −4.9 → −3.6 s for the second. So the concern I flagged was real — the strict
detector was missing his quieter episodes — **and closing it strengthens the null rather than weakening
it.** That is the safe direction, and I checked it because it could have gone the other way.

Onset counts per route across the sweep (50 → 20): r39 110 → 247, r5e_v288 108 → 175, r62_v289 80 → 184,
r63_v289 82 → 121, r35 134 → 265.

## A5. Where this leaves the echo

- **Arithmetically capable** on V282 at the measured command amplitude and perfect phase lock (×6.0
  ceiling → 1.38), degrading below unity past ψ ≈ 43°, and ×2–7 stronger than any impulsive path. [A1, A2]
- **Falsified as the dominant sustaining leg by V288 rev 2 on the car** — the pre-filter cut its drive
  2.19× at 20 Hz and every ring statistic was unchanged. [A1b, EVIDENCE, on-car — this outranks A1]
- **Unconfirmed as a mechanism by the wire**: the angle→command gain does not match the predicted P-path
  gain in magnitude, scales the wrong way with speed, and varies 3.4× across builds where openpilot did
  not change; and the measured cross-phase implies a physically impossible ~0 ms round trip. [A2c, A3]
- **The trigger null from the main report is unaffected and now stronger.** [A4]

### What would actually settle it
The clean discriminator is **not** available offline: it needs the echo path opened or attenuated *at
openpilot*, not inside the EPS, so the two legs can be separated. A fork-side change that low-passes or
decimates the angle *measurement* feeding `latcontrol_torque` (leaving the EPS untouched) would cut the
echo without touching the plant, the loop gain, or the authority the operator is protecting — and unlike
V288 it would not also filter the genuine reference. That is `oplpf`'s territory, not mine, and it is the
one version of "prevent the excitation" that does not cost authority in the EPS.
