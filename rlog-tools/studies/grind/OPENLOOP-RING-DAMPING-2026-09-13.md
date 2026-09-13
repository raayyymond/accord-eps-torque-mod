# The 18–22 Hz object's damping with the LKAS rate loop OPEN

Subagent `openloop`, 2026-09-13. **ANALYSIS ONLY — nothing was built, flashed, or sent on any bus.**
Scripts: `openloop_lib.py` · `openloop_census.py` · `openloop_zeta.py` · `openloop_zeta2.py` ·
`openloop_ring.py` · `openloop_bound.py` · `openloop_drive.py` · `openloop_fade.py`, all in
`rlog-tools/studies/grind/`. Logs in `rlog-tools/studies/grind/_scratch/openloop_*.txt`.

---

## THE ANSWER, IN ONE PARAGRAPH

**With the LKAS rate loop open there is no 18–22 Hz object to measure a ζ on.** Over 4,759 s of
lateral-disengaged time in segments ≥ 10.24 s across 35 cached routes — 3,696 s of it at 0–4 m/s in 119
segments — the pooled spectrum carries **no resonance at all** in 16–26 Hz: fitted peak-over-background
**1.56** on driver torque and **1.14** on wheel rate, model-free prominence **1.00 / 1.25**, both *below*
the 1.26–1.48 that a synthetic no-mode control returns. The same estimator on engaged time at the same
speeds finds the line immediately (bump 20.4 / 22.5, prominence 11.9 / 16.0, **ζ = 0.0356 [0.0233, 0.0573]**
at f0 21.48 Hz on torque, **0.0338 [0.0227, 0.0515]** at 21.69 Hz on rate; per build **V282 ζ = 0.0164
[0.0126, 0.0222]** at 20.01 Hz). Converting the null into a bound by replacing the measured open-loop
18–22 Hz energy with a synthetic mode of known ζ: a mode carrying that energy is **detected outright for
ζ ≤ 0.03** and becomes **invisible from ζ ≥ 0.05**, on both channels. So **ζ_open ≥ 0.05 — at least ×3 the
engaged ζ on V282 — or the open-loop content is not modal at all, which is what the structure statistics
actually say.** The disengaged 18–22 events are *not* the same object seen weakly: only 24 % of
disengaged windows at 0–4 m/s put their 12–26 Hz line inside 18–22 (engaged 59 %), the band-specific
level gate reads **0.0009 disengaged against 0.4247 engaged (×451)**, and the pooled disengaged spectrum
falls monotonically from 12 to 22 Hz with no peak — while the 12–14 Hz road line the record says persists
is, in a long pooled record, **not a resolvable resonance on either label** (a failed positive control,
§6). **Amplitude, load-matched: the 18–22 Hz band is 0.2145 [0.2036, 0.2267] of engaged on driver torque
and 0.2217 [0.2101, 0.2351] on wheel rate at 0–4 m/s** — a factor of 4.5, not the ×33–72 the record's
*presence rate* implies; against the 26–34 Hz neighbour-band control (0.686 / 0.559) the **mode-specific**
suppression is only **×2.5–3.2**. **The T ring's drive on V282/r39 is 88 % linear rate feedback, 20 %
setpoint command, and 0.35 % rate-quantiser toggles** — the quantiser term is dead, because the ring is
**~16 LSBs** on the channel the EPS feedback operand reads, not sub-LSB (§7 corrects the brief's premise).

**Read against the pre-registration:** this is neither F1 nor F2 nor the "cure" branch. It is closest to
the "cure" branch — ζ_open ≥ 0.05 with the object absent, amplitude ratio 0.21 rather than < 0.10 — but
the honest form is a **bound and an absence**, not a point estimate, and §5 says why the absence has two
readings.

---

## 1. What was measured, and against what

| | record, 2026-09-10 | here |
|---|---|---|
| routes | 17 (`cache/v280`) | **35** (`cache/<route>/<route>.npz`) |
| engaged windows | 20,761 | **37,621** |
| lateral-OFF windows | 5,905 | **12,639** |
| OFF time in ≥ 10.24 s segments | — | **4,759 s** (3,696 s at 0–4 m/s, 119 segments) |

"Lateral engaged" is the kit's definition throughout: `0x18F` STEER_CONTROL_ACTIVE **and** `0xE4`
STEER_REQUEST ([[feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference]]).

**Loader validated against the canonical one** (`creep20_loop_id.load`) on all 14 shared routes:
driver torque matches to rms 0 – 0.19 counts (`corr = +1.000000`), the engagement mask agrees on
**0.99991 – 1.000000** of samples, and 18–22 Hz band power agrees to **×1.004 – 1.023**. One trap found
and fixed: the larger cache family stores `tq` and `rate_c` **negated** relative to the v280 cache
(`corr = −1.00000000` before the flip), and its `raw18_t` runs 1–2 samples longer than the data arrays on
25 of 35 routes. [EVIDENCE, `openloop_lib.py` docstring + the validation run]

---

## 2. 🛑 THE FAILED CONTROLS — read these before any ζ below

A ζ is only as good as the estimator behind it, and **one of the record's two estimators has no
resolving power at all.** Controls: synthetic white-noise-driven 2nd-order modes at f0 = 20 Hz of KNOWN
ζ, 600 s in 20 s pieces, at two in-band SNRs, plus negative controls with no mode.

### 2a. `design290d_anchors.decay()` — the DESIGN-V290B §A.2 anchors — CANNOT RESOLVE ζ

Crux verified by importing and calling **the record's own function**, not a re-implementation.

| true ζ | `DA.decay` @ SNR 10 dB | @ SNR 0 dB |
|---|---|---|
| 0.005 | 0.0188 | 0.0363 |
| 0.010 | 0.0221 | 0.0364 |
| 0.020 | 0.0325 | 0.0382 |
| 0.030 | 0.0333 | 0.0403 |
| 0.050 | 0.0373 | 0.0388 |
| 0.100 | 0.0399 | 0.0396 |
| 0.200 | 0.0360 | 0.0377 |
| 0.300 | 0.0414 | 0.0400 |
| **band-limited noise, NO MODE** | **0.0361** | — |
| **white noise** | **0.0396** | — |

Its output is the ±3 Hz bandpass's own envelope decay over the 60–250 ms fit window. **DESIGN-V290B
§A.2's r39 = 0.0355 and r5e = 0.0377 sit at or below the no-mode floor**; r62/r63's 0.054–0.063 are above
everything the control produced, so V289's ring does decay faster than the filter floor, but the
estimator cannot map that to a ζ. The "22 % / 16 % growing bursts" figures also reproduce on pure noise
(30 % growing). **[EVIDENCE]**

### 2b. Coherence time (`fvlc_parts2.part2c`) is sound where the record used it, and saturates above

Unbiased ×1.0–1.2 for true ζ in 0.02–0.05; returns **0.047–0.070 for true ζ = 0.10 / 0.20 / 0.30** and
**0.0527 for NO MODE**. So the record's ζ = 0.0091–0.0224 is inside its usable range and stands — but it
**cannot distinguish ζ = 0.05 from ζ = 0.30 from "no mode"**, which is exactly the range this question
lives in.

### 2c. The estimator of record here, and the two degeneracies it took to get it right

**E3b** = Lorentzian resonance on a **pinned power-law background**, fitted to the pooled Welch PSD
(nperseg 1024 = 10.24 s), f0 confined to the window interior. Two earlier forms failed on real data and
both failures are recorded because they are easy to repeat:

1. a bare Lorentzian + constant **parks f0 on the window edge** and uses the Lorentzian tail as the 1/f
   skirt — three disengaged rows did exactly that (f0 15.83 / 16.08 / 16.37 against a 16.0 Hz edge) while
   scoring R² 0.83–0.88 and measuring nothing;
2. with the background free, **the background collapses** and a broad Lorentzian becomes the continuum —
   fitted peak/background ratios of **10⁹** on spectra whose real line is ~20 dB.

Final form, controls (`_scratch/openloop_zeta2_controls.txt`): bias **×0.87–1.16** for true ζ 0.005–0.05
at 0 dB in-band SNR, **×0.96–1.03** up to ζ = 0.20 at 10 dB, and it **under-reads above ζ ≈ 0.05**
(×0.75 at 0.10, ×0.47 at 0.20). Under-reading is conservative here: a high measured ζ means the truth is
higher. Falsifiers, both required: `bump` = fitted peak/background and the **model-free** `prom` =
max(P within ±1 Hz of f0) / median(P over the window). No-mode controls give **1.26–1.48** on both;
threshold **1.8**, plus f0 off the window edges.

### 2d. Inhomogeneous broadening — why every stratum below is ≤ 4 m/s wide

Pooling a PSD over segments whose f0 differs inflates ζ: ×1.05 at 0.25 Hz of f0 spread, ×1.20 at 0.5 Hz,
**×1.60 at 1.0 Hz**, ×2.74 at 2.0 Hz. The record measures df0/dv at 0.11–0.21 Hz per m/s, so a 4 m/s bin
carries ≤ 0.84 Hz and ≤ ~×1.5. **Inflation biases ζ UP, i.e. against "the loop open is still lightly
damped" — so a LOW ζ on a wide bin is conservative and a HIGH one is not.**

---

## 3. TASK 1 — ζ with the loop open

### 3a. There is no line to fit

Pooled Welch over every contiguous segment of the stratum, fit window 16–26 Hz.

| stratum | secs | nseg | f0 fit | E3b ζ [95 % CI] | bump | prom | verdict |
|---|---|---|---|---|---|---|---|
| **driver torque `bar`** | | | | | | | |
| ENGAGED 0–4 m/s | 938 | 51 | 21.477 | **0.0356 [0.0233, 0.0573]** | 20.44 | 11.87 | **LINE** |
| ENGAGED 4–8 m/s | 821 | 55 | 21.266 | 0.0545 [0.0178, 0.0638] | 7.08 | 1.85 | LINE |
| ENGAGED 8–12 m/s | 1497 | 75 | 21.163 | 0.0489 [0.0305, 0.0512] | 9.33 | 4.50 | LINE |
| **OFF 0–4 m/s — LOOP OPEN** | **3696** | **119** | 25.386 | 0.0921 [0.0035, 0.1482] | **1.56** | **1.00** | **NO LINE** |
| OFF 4–8 m/s — LOOP OPEN | 98 | 8 | 17.105 | 0.0191 [0.0052, 0.0715] | 3.95 | 3.78 | LINE ⚠ 98 s |
| OFF 8–26 m/s — LOOP OPEN | 431 | 16 | 16.522 | 0.0751 [0.0499, 0.0865] | 5.80 | 2.46 | NO LINE (f0 on edge) |
| OFF 0–26 m/s — LOOP OPEN | 4759 | 143 | 16.522 | 0.1027 [0.0675, 0.1085] | 3.12 | 2.08 | NO LINE (f0 on edge) |
| **wheel rate `0x18F`** | | | | | | | |
| ENGAGED 0–4 m/s | 938 | 51 | 21.685 | **0.0338 [0.0227, 0.0515]** | 22.53 | 16.00 | **LINE** |
| **OFF 0–4 m/s — LOOP OPEN** | **3696** | **119** | 20.242 | 0.0302 [0.0035, 0.0775] | **1.14** | **1.25** | **NO LINE** |
| OFF 8–26 m/s — LOOP OPEN | 431 | 16 | 16.522 | 0.0830 [0.0212, 0.1080] | 2.67 | 2.12 | NO LINE (f0 on edge) |

⚠ **The high-demand engaged stratum (idx >= 20) has NO contiguous run of 10.24 s in the whole corpus**,
so every engaged row above is all-demand engaged creep, not the demand-gated grinding stratum. That
stratum is where the ring is loudest, so the engaged ζ above is if anything measured on a *weaker* line
than the grinding one; it does not weaken the disengaged comparison, which has no demand at all.

The three OFF rows whose fitted f0 lands on 16.522 Hz — the window's lower edge — are the degenerate fit
of §2c-1 recurring, and they are flagged, not quoted. §4 measures 11–19 Hz properly.

### 3b. Per build — the same car, loop closed and loop open

| build | ENGAGED 0–8 m/s, f0 / ζ [CI] / bump | OFF 0–26 m/s, f0 / ζ / bump | verdict OFF |
|---|---|---|---|
| stock (r97) | *no engaged exposure ≥ 10.24 s* | 24.079 / 0.0035 / 2.96 | LINE ≤ resolution ⚠ |
| V112 | 20.067 / 0.0270 / 28.69 | 17.534 / 0.0035 / 2.99 | LINE ≤ resolution ⚠ |
| V278r3 | 19.489 / 0.0408 [0.0256, 0.0535] / 9.00 | *< 3 segments* | — |
| V280r2 | 20.252 / 0.0431 [0.0292, 0.0549] / 7.23 | 16.522 / 0.2062 / 1.90 | NO LINE |
| V281r3 | 20.059 / 0.0248 [0.0179, 0.0272] / 9.50 | 22.318 / 0.0040 / 2.28 | LINE ⚠ 149 s |
| **V282** | **20.011 / 0.0164 [0.0126, 0.0222] / 9.15** | 25.478 / 0.0591 / 1.80 | **NO LINE** |
| V288r2 | 19.950 / 0.0331 / 12.55 | 25.478 / 0.0196 / 1.63 | NO LINE |
| V289r1 | 16.085 / 0.0365 [0.0308, 0.0397] / 8.38 | 25.478 / 0.0985 / 2.37 | NO LINE |

V282's engaged **0.0164 [0.0126, 0.0222]** lands inside the record's coherence-time range 0.0091–0.0224 —
an independent estimator agreeing with the kit's own. The two "LINE ≤ resolution" OFF rows (stock, V112)
sit at the Welch resolution floor at 24.1 and 17.5 Hz on 392 s and 343 s; they are **not** at 20 Hz and
are not the object under study, but they are narrow lines worth someone's attention.

### 3c. What the null EXCLUDES — the replacement injection

`openloop_bound.py`. Take the real lateral-OFF segments at 0–4 m/s, remove exactly the 18–22 Hz bins with
an FFT mask, and put back a synthetic mode of **known ζ at the same measured band amplitude**, so the
surrogate carries exactly the energy the wire carries, arranged as a resonance instead of as broadband.
(An earlier Butterworth notch left transition skirts the fit could grip and a whole-window notch removed
the continuum entirely; both are recorded in the script.)

| true ζ | bar: ζ̂ / bump / prom → ? | rate: ζ̂ / bump / prom → ? |
|---|---|---|
| 0.010 | 0.0035 / 7.08 / 6.17 → **DETECTED** | 0.0035 / 8.50 / 5.74 → **DETECTED** |
| 0.020 | 0.0063 / 4.12 / 3.23 → **DETECTED** | 0.0069 / 4.59 / 2.97 → **DETECTED** |
| 0.030 | 0.0083 / 2.89 / 2.31 → **DETECTED** | 0.0092 / 3.15 / 2.16 → **DETECTED** |
| 0.050 | 0.0596 / 2.83 / 2.24 → invisible | 0.0096 / 1.77 / 1.48 → invisible |
| 0.100 | 0.0703 / 3.14 / 2.27 → invisible | 0.0628 / 2.25 / 1.68 → invisible |
| 0.200 | 0.0694 / 4.97 / 2.48 → invisible | 0.0653 / 3.75 / 1.79 → invisible |
| **REAL DATA** | **— / 1.56 / 1.00** | **— / 1.14 / 1.25** |

⇒ **ζ_open ≥ 0.05.** And note the real data's `prom` of **1.00 / 1.25** is *below every injected row* —
below even ζ = 0.5 carrying all the energy (2.34 / 1.78). The open-loop 18–22 Hz content has **less**
structure than any modal arrangement of the same energy: it is the broadband continuum.

The on-top version (`openloop_ring.py` C5, mode added without removing anything, so twice the energy)
detects to **ζ = 0.10 at ≥ 0.25× the engaged ring amplitude** and to ζ = 0.05 at ≥ 0.10×. The two
variants have opposite artefacts and bracket the bound at **ζ_open ∈ [0.03, 0.10] as a floor**; quote
**≥ 0.05**.

### 3d. Same object, or the road line?

Not the same object, and not a weak version of it.

| speed | ENGAGED: n / med f0 / frac in 18–22 / in 12–14.5 | OFF: n / med f0 / in 18–22 / in 12–14.5 |
|---|---|---|
| 0–4 | 2774 / 20.08 / **0.586** / 0.061 | 4420 / 23.87 / **0.242** / 0.053 |
| 4–8 | 3635 / 19.93 / 0.520 / 0.154 | 190 / 14.71 / 0.126 / 0.389 |
| 8–13 | 5030 / 16.36 / 0.334 / 0.314 | 120 / 14.00 / 0.025 / 0.575 |

Band-specific LEVEL gate (prominence ≥ 8 inside 17–23 Hz **and** ≥ 40 raw of 18–22 amplitude):
**0.4247 engaged vs 0.0009 disengaged at 0–4 m/s (×451)**, and **0.0000 disengaged on 27 of 35 routes**,
maximum 0.0097. Pooled amplitude density on the disengaged 0–8 m/s stratum falls monotonically —
bar 6.7 → 5.87 → 5.66 → 4.92 → 4.51 → 3.92 → 3.80 → 3.42 → 3.33 → 3.29 → 3.08 across 12 → 22 Hz, with no
peak anywhere; engaged over the same samples runs 40.5 / 54.8 / 46.8 / 46.9 / 44.4 / 34.9 / 31.6 / **43.5
/ 54.8 / 53.8 / 51.9**, the ring plainly visible.

---

## 4. ⭐ THE 11–19 Hz WINDOW — where V289 failed, with the loop open

Directly decision-bearing, because V289's revert signature was a 15–17 Hz pole taking the margin.

| stratum | channel | secs | nseg | f0 | ζ [95 % CI] | bump | prom | verdict |
|---|---|---|---|---|---|---|---|---|
| ENGAGED 4–8 m/s | bar | 821 | 55 | 14.070 | 0.0932 [0.0097, 0.1282] | 2.33 | 2.45 | LINE |
| ENGAGED 8–26 m/s | bar | 10837 | 275 | 11.989 | 0.0079 | 1.51 | 3.85 | NO LINE |
| OFF 0–4 m/s | bar | 3696 | 119 | 14.111 | 0.0068 | **1.29** | **1.53** | **NO LINE** |
| OFF 4–8 m/s | rate | 98 | 8 | 15.396 | 0.0049 | 2.96 | 2.75 | LINE ⚠ 98 s |
| OFF 8–26 m/s | bar | 431 | 16 | 14.234 | 0.0837 [0.0417, 0.1144] | 1.96 | 1.98 | LINE ⚠ 431 s |
| **V289 ENGAGED 0–8** | bar | 220 | 11 | **16.065** | **0.0403 [0.0326, 0.0442]** | **11.17** | 2.31 | **LINE** |
| **V289 OFF, all speeds** | bar | 467 | 10 | 18.483 | 0.0123 | **1.52** | **0.73** | **NO LINE** |

⭐ **V289's relocated 16 Hz ring is ALSO engagement-gated.** It is a clear line engaged (bump 11.2) and
absent with the loop open (bump 1.52, prom 0.73), on 467 s. The 15–17 Hz pole that took V289's margin is
therefore **not a plant mode that survives opening the loop** — it is another closed-loop object.
⚠ 467 s in 10 segments is thin; treat as a strong indication, not a settled fact.

A weak 14–15 Hz object **is** present with the loop open at 4–26 m/s (bump 1.96–2.96, ζ 0.005–0.087), on
98 s and 431 s. That is the road line, and it is the only 12–26 Hz thing that survives disengagement.

---

## 5. 🛑 THE LIMIT OF THIS EXPERIMENT — stated before anyone designs against it

`STEER_REQUEST = 0` opens the LKAS rate loop **and removes the LKAS excitation with it.** So the absence
of a line has two readings and this measurement cannot separate them by itself:

1. **ζ_open really is ≥ 0.05** — the loop is doing the de-damping, and opening it removes the object.
2. **The mode exists at low ζ but nothing disengaged excites it** — it couples only to LKAS-commanded
   motor torque, not to road or driver input.

What narrows it: the load-matched disengaged windows at 0–4 m/s carry **more** driver torque (445.7 vs
418.8 rms) and **more** wheel motion (237.8 vs 137.6 rms) than the engaged ones, so base assist is
active, the motor is driving, and the wheel is moving — and there is still 0.398 deg/s of broadband
18–22 Hz wheel rate on the wire for a mode to feed on. Reading 2 requires the mode to be deaf to all of
that while being rung by LKAS torque of the same order. **Possible, not refuted, and it is the one thing
a transient test would settle.** [BELIEF on the weighting; the numbers are EVIDENCE]

**Both readings point the same way for the build in front of you:** opening the loop above ~8 Hz removes
the 18–22 Hz object either because it damps it or because it removes what drives it.

### The second and third methods, one of which failed outright

- **M1, the post-PID fade as a loop-gain knob: FAILED, no leverage.** `m = ((255·B)&0xFFFF)>>8` is
  effectively **binary** on the wire — 254 or 76, with 63–95 % of engaged creep samples at 254 and
  almost nothing between. There is no continuum to regress ζ against. Abandoned, not reported as a number.
- **M2, the acting-Kp axis (248 → 696 on the Kp-LERP builds): FAILED for exposure.** No Kp tercile had a
  single segment ≥ 10.24 s after the hands-off gate; the per-build fit across 4 points returns an
  intercept of **−0.036**, which is not a damping ratio. Confounded with demand index in any case
  (STATE correction 6).
- **M3, V289's own notch as an in-situ loop-opening at 20 Hz: WORKED, and it agrees.** V289 cut the loop
  at 20.04 Hz on the car while plant, excitation, driver and speed stayed put. On the 18–23 Hz window
  V289 reads **bump 2.78, prom 1.61 → NO LINE**, against V282's **ζ = 0.0117 [0.0094, 0.0372], bump 6.56,
  prom 4.71 → LINE** on the same window. Cutting the loop at 20 Hz **removed the 20 Hz mode**; it did not
  leave a lightly damped ring behind. ⚠ Confounded: V289 also moved the feedback pole 16.5 → 25 Hz.

---

## 6. THE POSITIVE CONTROL THAT FAILED — the 12–14 Hz "road/plant line"

The intended real-data positive control was the record's 12–14 Hz line, which is said not to be
engagement-gated. **E3b does not find it as a resonance on either label**: fit window 10–16 Hz gives
bump 1.25–1.66 and prom 0.93–2.63 on engaged *and* disengaged, at every speed, on up to 16,562 s.

That is a finding, not just a failed control: **the 12–14 Hz "line" is a short-window prominence, not a
mode with a resolvable width in a long pooled record.** The record's shape-gate rate of 0.25–0.50
disengaged is computed from 2 s-window prominence, a different statistic. The "two-object picture" as a
pair of *resonances* is not confirmed by line-width fitting; what §4 does find with the loop open is a
marginal 14–15 Hz object on thin exposure.

**The null in §3 does not depend on this failure**, because the injection test of §3c is a positive
control that passes: a mode of ζ ≤ 0.03 carrying the measured energy **would** have been found in exactly
these segments, and was not.

---

## 7. TASK 2 — AMPLITUDE, not presence rate

Load-matched: disengaged windows restricted, inside each speed bin, to the engaged interquartile range of
**both** driver-torque rms and wheel-rate rms. Ratio CI = 4,000-sample bootstrap of the ratio of medians,
resampling both labels.

| speed | channel | n eng | A engaged | n OFF | A OFF | **ratio OFF/eng [95 % CI]** | 26–34 Hz neighbour ratio |
|---|---|---|---|---|---|---|---|
| 0–4 | bar | 4085 | 46.61 | 1125 | 9.995 | **0.2145 [0.2036, 0.2267]** | 0.686 |
| 4–8 | bar | 5692 | 43.33 | 198 | 11.58 | **0.2672 [0.2373, 0.2923]** | 0.869 |
| 8–13 | bar | 7898 | 27.51 | 61 | 12.31 | 0.4474 [0.3827, 0.5480] | 0.826 |
| 0–4 | rate (deg/s) | 4085 | 2.2096 | 1125 | 0.4898 | **0.2217 [0.2101, 0.2351]** | 0.559 |
| 4–8 | rate | 5692 | 2.1640 | 198 | 0.5224 | **0.2414 [0.2195, 0.2774]** | 0.529 |
| 8–13 | rate | 7898 | 1.2662 | 61 | 0.5502 | 0.4346 [0.3289, 0.4665] | 0.517 |
| 0–4 | angle (deg) | 4085 | 0.0259 | 1125 | 0.0144 | 0.5582 [0.5357, 0.5780] | 0.939 |

**Three things to take from this:**

1. **The record's ×33–72 is a PRESENCE RATE, and the amplitude ratio is only ×4.5.** The level gate sits
   at 40 raw, essentially at the engaged median (46.6); a ×4.5 shift of the median across a threshold
   placed there produces an enormous rate ratio. Both numbers are correct; they are not the same claim.
2. **The effect is mode-specific, but by ×2.5–3.2, not ×33.** Dividing out the neighbour-band control:
   bar 0.2145 / 0.686 = **0.313**, rate 0.2217 / 0.559 = **0.397** at 0–4 m/s.
2b. **Presence rate, load-matched, for completeness** (18–22 Hz gate): engaged 0.4247 vs disengaged
   **0.0000 on 1,125 matched windows** at 0–4 m/s (⇒ ≥ ×159), 0.3542 vs 0.0000 on 198 at 4–8 m/s
   (≥ ×23). Above 8 m/s the matched disengaged count collapses to 1–61 windows and the test has no power.
3. **Not a load or exposure artefact.** At 0–4 m/s the matched disengaged windows carry bar rms
   **445.7 vs 418.8** and rate rms **237.8 vs 137.6** — more driver torque and more wheel motion than
   engaged, and still less 18–22 Hz content. This reproduces the record's own finding on twice the data.
4. **Re-derived by a second estimator.** The table uses a route-wide 4th-order zero-phase Butterworth
   band-pass and the window's std. Recomputing every matched window's 18–22 Hz amplitude instead from a
   per-window Hann periodogram band integral gives **0.2211 [0.2033, 0.2408]** (bar) and **0.2318
   [0.2130, 0.2550]** (rate) at 0–4 m/s, **0.2890 / 0.2871** at 4–8, **0.4130 / 0.3839** at 8–13 —
   agreeing with the table within the CIs on five of six cells.
5. On long contiguous segments without load matching the ratio is **0.079 / 0.081** (bar / rate), because
   the long engaged segments are the loudest ones. The load-matched window figure is the answer to the
   question as asked.

---

## 8. TASK 3 — DRIVE DECOMPOSITION OF THE T RING ON V282 (r39)

`openloop_drive.py`, byte-exact 1 kHz mirror (`grind_incident_r35.simulate`), 10 loudest 3 s engaged
windows (`burst_echo_sizing.loud_windows`) — the same machinery and the same windows as
`comb_mirror_apportion.py`.

**Baseline reproduces the record exactly: T_total 57.21 counts, command leg 11.56 (0.202)** — the
numbers `COMB-VS-ECHO-SIZING` §A1 published. P-only 27.07, D-only 51.07, quad sum 57.80.

### 8a. 🛑 The brief's premise on the quantiser is wrong, and it matters

The brief reads STATE correction 8c as *"the wire ring is 0.17–0.28 LSB of 0.125 deg/s"*, i.e. the RATE
channel. The source says the opposite: `OPENPILOT-EXCITATION-SOURCES-2026-09-10.md` §A1 is headed
**"The ANGLE ring is 0.17–0.28 LSB"** and its point is that `0x18F` STEER_ANGLE_RATE *"resolves this band
~100× finer than the angle"*. Measured on r39, 18–22 Hz band amplitude:

```
0x18F rate    15.818 raw counts = 1.9773 deg/s =  15.82 RATE  LSBs (0.125 deg/s)
0x14A angle   0.02589 deg                      =   0.259 ANGLE LSBs (0.1 deg)
rate -> implied angle at f0 19.92 Hz: 0.01580 deg = 0.158 angle LSBs   [matches 0.17-0.28]
```

⇒ The ring is **~16 LSBs** on the channel the EPS feedback operand reads and **~0.26 LSB** on the channel
openpilot reads. A quantiser only generates toggles when the signal is *below* one step. **The
quantiser-toggle mechanism is available to openpilot's measurement path and NOT to the EPS feedback
path.** [EVIDENCE]

### 8b. The four terms

Each row is `dT = band amplitude( T(perturbed) − T(as measured) )` over 18–22 Hz, median of the 10
windows, bootstrap CI. TP / TD are the mirror's own P-only and D-only torques, so the P/D split is exact.

| ablation | dT counts | share | 95 % CI |
|---|---|---|---|
| **(a) FEEDBACK leg — 18–22 notched out of the 0x18F rate** | **50.27** | **0.879** of T_total | [27.27, 95.18] |
| (b1) one quantiser step of dither added to the rate | **0.20** | **0.003** | [0.18, 0.21] |
| (b2) rate re-quantised at 2 LSB | 0.46 | 0.008 | [0.42, 0.51] |
| (b3) at 4 LSB | 0.74 | 0.013 | [0.64, 0.83] |
| (b4) at 8 LSB | 1.39 | 0.024 | [1.32, 1.63] |
| (b5) at 16 LSB | 2.56 | 0.045 | [2.17, 2.70] |
| **(c+d) COMMAND leg — 18–22 notched out of 0xE4** | **11.56** | **0.202** of T_total | [7.58, 18.72] |
| (c) command leg on the D-only torque TD | 9.83 | 0.193 of D-only | [6.59, 16.35] |
| (d) command leg on the P-only torque TP | 5.62 | 0.208 of P-only | [3.56, 10.22] |
| (a1) feedback leg on TD | 44.29 | 0.867 of D-only | [23.95, 83.88] |
| (a2) feedback leg on TP | 22.05 | 0.814 of P-only | [11.58, 40.86] |
| CONTROL freeze the command entirely | 12.24 | 0.214 | [7.57, 22.20] |
| CONTROL freeze the WIRE entirely | 53.97 | 0.943 | [28.13, 99.72] |
| CONTROL sham band 26–30 out of the rate | 0.44 | 0.008 | [0.32, 0.65] |
| CONTROL sham band 26–30 out of the command | 1.35 | 0.024 | [1.06, 1.69] |

**Do the shares add?** feedback 50.27 ⊕ command 11.56 = **51.59 = 90.2 %** of T_total in quadrature
(linear sum 61.84 = 108 %). The two legs are near-orthogonal and together nearly complete.

**ANSWER: the feedback leg is LINEAR RATE FEEDBACK, not quantiser-toggle kicks.** Quantisation is
**0.35 %** of the delivered ring, and the LSB would have to be **16× coarser** before it reached 4.5 % —
which is what §8a predicts arithmetically from a 16-LSB ring.

### 8c. The per-LSB arithmetic, from V282's own cells

```
s_new = floor((fb_a*s + fb_b*x) / 1024) ;  r26 = s + s_new ;  |r26| <= 46080
fb_a = 923   fb_b = 1560   kd = 128
DC gain    = 2*fb_b/(1024-fb_a) = 2*1560/101 = 30.8911      [record: 30.89  ✓]
FIRST-TICK = fb_b/1024          = 1.5234
E = 32*sp - r26 ;  D = floor(dE * kd / 8) = dE * 16
  ONE rate LSB, first tick   : dE = -1.5234  ->  D  = -24.4 S counts
  ONE rate LSB, steady state : dE = -30.891  ->  P  = -29.9 S counts at Kp 248
```
⚠ The mirror upsamples the rate band-limited 10:1 (`C20.up1k` = `resample_poly`), so a 100 Hz step does
not arrive as a 1 kHz step and **−24.4 is an upper bound** on what the mirror delivers. The ablations
are what measures it, and they say **0.20 counts**.

---

## 9. WHAT THIS LICENSES, AND WHAT IT DOES NOT

**Licensed [EVIDENCE]:**
- Opening the LKAS rate loop above ~8 Hz removes the 18–22 Hz object. It is absent with the loop open
  on 3,696 s at creep, and V289 removed it on the car by cutting the loop at 20 Hz alone.
- ⭐ **It should also remove V289's 16 Hz relocation**, which is itself engagement-gated (§4). That is the
  material difference from V289: V289 opened the loop at *one* frequency and left it closed where the
  margin was thin; a wideband feedback low-pass opens it across the whole 12–26 Hz band the design law
  now demands.
- The drive is the feedback leg, and it is linear. There is no quantiser term to design against.

**NOT licensed [BELIEF / open]:**
- A point value for ζ_open. The honest statement is **≥ 0.05, and the open-loop content is not modal**.
- Any claim that the grinding will be *fixed*. Band behaviour is not the operator's symptom, and nothing
  here says what the car will feel like. **Score bands; let the operator score symptoms.**
- Separating "the loop damps it" from "LKAS torque is the only thing that excites it" (§5). Only a
  transient test does that, and the existing spec
  (`docs/specs/design/SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`) still stands as the instrument.
- Anything above 8 m/s with the loop open: total exposure is **431 s in 16 segments** and there is **zero**
  disengaged exposure above 26 m/s in the entire cache.

**Corrections this study puts on the record:**
1. `design290d_anchors.decay()`, and therefore DESIGN-V290B §A.2's per-build free-decay ζ, **has no
   resolving power** (§2a). r39's 0.0355 and r5e's 0.0377 are at the no-mode floor.
2. The coherence-time ζ of 0.0091–0.0224 **stands**, and an independent estimator puts V282 at
   **0.0164 [0.0126, 0.0222]**.
3. The 12–14 Hz "road/plant line" is **not a resolvable resonance** in a long pooled record on either
   label (§6).
4. The engagement gating's **×33–72 is a presence rate**; the amplitude ratio is **×4.5**, and the
   mode-specific part is **×2.5–3.2** (§7).
5. STATE correction 8c's **0.17–0.28 LSB is the ANGLE channel**, not the rate channel (§8a).
