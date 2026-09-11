# Is the grinding FORCED (A), a LIMIT CYCLE (B), or an EXCITED RESONANCE (C)?

**Subagent `cyclekind`, 2026-09-10. ANALYSIS ONLY — nothing was built, flashed, or sent on any bus.**

Scripts (all in `rlog-tools/studies/grind/`): `fvlc_lib.py`, `fvlc_analysis.py`, `fvlc_parts2.py`,
`fvlc_f0_controls.py`, `fvlc_v288_gain_check.py`, `fvlc_camera_lock.py`,
`fvlc_v289_band_robustness.py`, `fvlc_build_cache.py`.
Raw output: `_scratch/fvlc_analysis.txt`, `_scratch/fvlc_f0_controls.txt`,
`_scratch/fvlc_camera_lock.txt`, `_scratch/fvlc_v289_band_robustness.txt`.
Per-route caches: `_scratch/fvlc_<route>.pkl`; episode caches `_scratch/fvlc_eps_*.pkl`.

**11 routes, 6 builds:** r31 (V278r3) · r32/r33/r34 (V280r2) · r35 (V281r3) · r39/r3a/r3c (V282) ·
r5e_v288 (V288) · r62_v289/r63_v289 (V289). 715 detected episodes.

---

## VERDICT

**(C) EXCITED RESONANCE — a lightly damped mode that a feedback loop de-damps, rung by ordinary driving
excitation — with a REAL BUT MINORITY (A) ADMIXTURE. Not (B), on five independent signatures.**

⭐ **The number that settles it: 3.5–14.5 % of the grinding band's EXCESS energy is phase-locked to the
camera clock; 85.5–96.5 % is free.** modeld's 20 Hz comb is real, it is strongly locked on the command
(R2 − floor +0.19 to +0.33 on all 11 routes), and the ring does **not** follow it. ⭐ **Consequence, and it
is the actionable one: perfectly removing the camera comb from the command would reduce the grinding
amplitude by √(1−lock) — about 3 % at the median route and at most 8 %.** The kit's standing conclusion survives; what does *not* survive is the inference that led the
brief to doubt it.

🛑 **EVIDENCE / BELIEF split, precisely.** What this study measures is that the line is a
**lightly damped mode being rung by incoherent excitation** — that part is EVIDENCE, from the five tests
below. That **the rate loop is what makes it lightly damped** (the "de-damps" half of the standing
phrase) is *not* measured here; it is BELIEF carried from the record — V289's notch removing the 20 Hz
object entirely, and the reported fall of ζ 0.036 → 0.019 with loop gain. My contribution to that half is
negative only: nothing I measured contradicts it, and the alternatives to it are now closed.

| | verdict |
|---|---|
| **(A) forced through the LKAS reference path — specifically by modeld's 20 Hz comb** | **MINORITY CONTRIBUTOR, NOT THE MECHANISM.** Tested directly and independently: the ring is only **3.5–14.5 %** camera-locked in energy while the command is 19–33 %. (V288 tested nothing here — see the RETRACTION — so this is the first actual measurement of that path.) |
| **(A′) forced by a coherent narrowband disturbance** (cogging, gear mesh, tooth-pass) | **FALSIFIED** — the phase survives only 6.5–17.4 cycles, the envelope carries **no** coherent component (Rice K = 0.00 on every build), f₀ does not scale with shaft speed, and V289's notch *removed* the line rather than making it louder |
| **(B) limit cycle** | **FALSIFIED on five independent signatures** — coherence time = ring-down time, no preferred amplitude, no plateau, no hysteresis, no harmonics. None of the five uses V288 or the comb as an input. |
| **(C) excited resonance** | **SUPPORTED** — coherence time = ring-down time, Rayleigh envelope, amplitude tracks excitation, f₀ only weakly affected by gain and moved 3.8 Hz by phase, no plateau |

---

## THE MEASUREMENTS THAT CARRY IT

### 1. ⭐ The line's PHASE COHERENCE TIME equals its RING-DOWN TIME
This is the decisive one. Demodulate the band at its own f₀ and measure |⟨z(t)z*(t+τ)⟩|/⟨|z|²⟩, the
complex-envelope autocorrelation, pooled over episodes.

- **(C)** a lightly damped pole rung by broadband noise → |ρ(τ)| = exp(−ζω₀τ) *exactly*: the coherence
  time **is** the ring-down time, τ_c = 1/(ζω₀) ≈ 0.27 s ≈ 5.5 cycles at ζ = 0.029, f₀ = 20 Hz.
- **(A)** a coherent external drive or **(B)** a self-sustained cycle → the phase persists as long as the
  source does: τ_c of *seconds*, tens to hundreds of cycles.

| build | n ep | τ_c MODE (s) | cycles | equivalent ζ | τ_c SHAM (s) | ratio |
|---|---|---|---|---|---|---|
| V278r3 | 55 | 0.411 | 9.0 | 0.0177 | 0.375 | 1.10 |
| V280r2 | 137 | 0.354 | 7.1 | 0.0224 | 0.181 | 1.96 |
| V281r3 | 37 | 0.870 | 17.4 | 0.0091 | 0.282 | 3.09 |
| V282 | 89 | 0.519 | 10.4 | 0.0153 | 0.270 | 1.92 |
| V288 | 34 | 0.555 | 11.1 | 0.0143 | 0.328 | 1.69 |
| V289 | 87 | 0.383 | 6.5 | 0.0246 | 0.243 | 1.58 |

Bands ±3.0 Hz so the filter's own coherence floor (~0.053 s) sits far below both predictions; the SHAM
band, demodulated at its own peak in the same windows, measures that floor empirically (0.18–0.38 s).

**The line stays phase-coherent for 6.5 to 17.4 cycles and no longer, and the ζ implied by that decay
(0.009–0.025) lands on top of the independently measured free-decay ζ (0.011–0.018 here, 0.029 in the
record).** A damped mode being rung does exactly this. A drive or a cycle cannot: there is no persistent
phase, therefore there is no persistent source. [EVIDENCE]

### 2. ⭐ THE RING IS NOT LOCKED TO THE CAMERA CLOCK — but the command is
`modelrate` found a sustained 20 Hz comb in the command's second difference, phase-locked to the camera
crystal at **19.99974 Hz ± 0.0006**, 5–10× stronger in grinding windows, on every build including the
stock-map era — and `clip_curvature` never binds, so the vision model's staircase reaches the PID raw.
That is a concrete (A) candidate, and it has to be tested **on the ring channel**, which is mine.

I re-derived it independently (`fvlc_camera_lock.py`) rather than relay it: the square-law locked
fraction **R2 = |Σ z² e^(−2i·2πft)| / Σ|z|²**, which is *exactly* the fraction of in-band energy lying on
one phase axis relative to that clock. |R2| is invariant to the clock's phase intercept, so only the
**rate** is needed — no modelV2 in my cache. Evaluated in 20 s windows of route time (bounding any
drift between my CAN time axis and the camera crystal), floor measured with 28 clocks detuned
0.10–0.80 Hz, 11 routes, both strata.

**Positive control first, because a null on the torque channel would otherwise be my bug:**

| channel | stratum | R2 − floor, median over 11 routes | min | max |
|---|---|---|---|---|
| 0xE4 command, 2nd difference | quiet | **+0.2869** | +0.2163 | +0.3361 |
| 0xE4 command, 2nd difference | grinding | **+0.2078** | +0.1788 | +0.2872 |
| 0xE4 command | quiet | **+0.2772** | +0.2060 | +0.3273 |
| 0xE4 command | grinding | **+0.2121** | +0.1850 | +0.2955 |
| **bar driver torque** | quiet | **+0.0209** | −0.0443 | +0.1196 |
| **bar driver torque** | grinding | **+0.0427** | −0.0651 | +0.1409 |
| **wheel rate 0x18F** | grinding | **+0.0382** | −0.0684 | +0.0993 |

The control passes decisively — my implementation sees the comb at 19–33 % of the command's in-band
energy on every route. **The ring sees it at 2–4 %.**

**And the decomposition that actually answers the question** — of the grinding *excess* energy over
quiet, how much is locked? (V289 excluded: its ring sits at 16.2 Hz, outside this band.)

| route | build | ΔE total | ΔE_lock | ΔE_free | **lock fraction** |
|---|---|---|---|---|---|
| r31 | V278r3 | 2.16e4 | 792 | 2.08e4 | **0.037** |
| r32 | V280r2 | 8 927 | 310 | 8 617 | **0.035** |
| r33 | V280r2 | 1.56e4 | 615 | 1.49e4 | **0.040** |
| r34 | V280r2 | 1.92e4 | 1 699 | 1.75e4 | **0.088** |
| r35 | V281r3 | 1.16e4 | 1 686 | 9 942 | **0.145** |
| r39 | V282 | 5 755 | 753 | 5 001 | **0.131** |
| r3a | V282 | 1.01e4 | 652 | 9 424 | **0.065** |
| r3c | V282 | 6 965 | 318 | 6 647 | **0.046** |
| r5e_v288 | V288 | 8 340 | 1 036 | 7 304 | **0.124** |

**Median 0.065, range 0.035–0.145. The grinding is 86–96 % free energy.** [EVIDENCE]

⭐ **What that buys, in the only unit that matters.** Locked and free energies are orthogonal by
construction, so deleting the comb entirely changes the ring's amplitude by √(1 − lock):
**×0.967 at the median route, ×0.925 at the worst.** A perfect fork-side comb filter is worth
**3–8 % of grinding amplitude.** That is the honest price of the fork-side lever.

⚠ **This inference depends on the mode sitting close enough to the comb rate that a forced response
would stay locked** — it does: f₀ is 19.95–20.02 Hz against a 19.99974 Hz clock, so over the measured
0.5 s ring-down the phase slips ≤ 0.025 cycles. A comb-driven ring *would* have read locked. It does not.

⚠ **I do not fully reproduce `modelrate`'s decomposition and the difference should be on the record.**
Theirs clamps to 0.000 on 6 of 7 rows (0.357 on r39); mine reads a consistent small non-zero 0.035–0.145.
The cause is methodological — they evaluate whole strata against a max-over-detunings floor, which clamps;
I evaluate in 20 s windows. **Both agree the forced component is a minority**; mine puts a number on it
and is the more conservative of the two for the fork-side lever, since it credits the comb with *more*.

### 3. There is NO preferred amplitude — the ring is *broader* than its own excitation
A limit cycle's defining property is that a nonlinearity sets its amplitude. Then the ring should be
**tighter** than whatever is driving it. It is the opposite, on every build:

| build | n ep | CVlog(mode peak) | CVlog(neighbour band, same episodes) | ratio |
|---|---|---|---|---|
| V278r3 | 81 | 0.800 | 0.560 | **1.43** |
| V280r2 | 240 | 0.843 | 0.583 | **1.45** |
| V281r3 | 62 | 0.776 | 0.539 | **1.44** |
| V282 | 145 | 0.639 | 0.509 | **1.26** |
| V288 | 47 | 0.682 | 0.662 | 1.03 |
| V289 | 140 | 0.689 | 0.572 | **1.20** |

And there is no plateau. With the peak-selection artefact controlled by the sham band (25.5 ± 1.5 Hz,
scored in the **same** episode windows, selected by the mode band and not by itself):

| build | plateau frac MODE | plateau frac SHAM | decay 1/s MODE | decay 1/s SHAM |
|---|---|---|---|---|
| V278r3 | 0.275 [0.220–0.323] | 0.308 [0.274–0.358] | 1.592 [1.317–2.220] | 0.663 [0.352–1.093] |
| V280r2 | 0.260 [0.243–0.282] | 0.314 [0.291–0.333] | 1.747 [1.454–2.159] | 0.952 [0.684–1.356] |
| V281r3 | 0.313 [0.278–0.347] | 0.296 [0.257–0.362] | 1.946 [1.081–2.560] | 0.993 [0.518–1.992] |
| V282 | 0.313 [0.290–0.356] | 0.330 [0.302–0.373] | 1.397 [1.021–1.862] | 0.991 [0.528–1.444] |
| V288 | 0.343 [0.288–0.462] | 0.328 [0.286–0.377] | 1.495 [0.645–2.295] | 1.028 [0.602–1.699] |
| V289 | 0.279 [0.257–0.314] | 0.312 [0.281–0.340] | 1.940 [1.254–2.204] | 1.424 [1.006–1.965] |

The ring spends **~30 %** of an episode within ±2 dB of its own median — *no more than pure band-limited
noise does* — and it **decays**, at 1.4–1.9 /s (equivalent ζ 0.011–0.018 at 20 Hz). A self-sustained
oscillation does neither. [EVIDENCE]

🛑 **Honest limit:** the decay figure is only ~1.5–2× the sham selection artefact and the CIs overlap,
so *"it decays at exactly this rate"* is NOT established — what is established is *"it does not
plateau"*, where the sham control sits right on top of the mode.

### 4. The envelope is RAYLEIGH — there is no deterministic component at all
A narrowband-filtered *Gaussian* process has a Rayleigh envelope (Rice K = 0, CV = 0.5227). A
deterministic oscillation buried in noise — whether an external drive (A) or a limit cycle (B) — has a
**Rician** envelope with K ≫ 0. Pooled over every episode sample, each episode normalised by its own
mean (which removes across-episode amplitude spread and leaves the marginal shape):

| build | n samples | MODE K | MODE CV | SHAM K | SHAM CV |
|---|---|---|---|---|---|
| V278r3 | 22 555 | **0.00 [0.00–0.00]** | 0.770 | 0.00 | 0.689 |
| V280r2 | 55 136 | **0.00 [0.00–0.00]** | 0.792 | 0.00 | 0.691 |
| V281r3 | 15 856 | **0.00 [0.00–0.00]** | 0.674 | 0.00 | 0.679 |
| V282 | 32 196 | **0.00 [0.00–0.00]** | 0.633 | 0.00 | 0.652 |
| V288 | 10 593 | **0.00 [0.00–0.00]** | 0.717 | 0.00 | 0.597 |
| V289 | 30 157 | **0.00 [0.00–0.00]** | 0.702 | 0.00 | 0.617 |

Simulated Rayleigh null with the same episode-length mixture, band and normalisation: K 0.550
[0.047–0.908], CV 0.493 [0.469–0.515].

Every build reads K = 0 and a CV **above** Rayleigh, i.e. over-dispersed — the signature of an
amplitude-modulated noise process, not of a tone. [EVIDENCE]

⚠ **What this test does and does not do.** K separates {A, B} from (C). It does **not** separate A from
B. And the within-episode amplitude modulation that survives normalisation pushes K *down*, so the test
is conservative only in the direction of (C) — it cannot manufacture a K = 0. But a genuine tone at
−10 dB SNR inside a ±1.5 Hz band would still have lifted K above the sham column, and it did not.

### 5. Amplitude TRACKS excitation, and there is no hysteresis
Inside episodes, log(ring envelope) regressed on log(excitation proxy), block-bootstrapped over
episodes, with the identical regression on the sham band as the control that makes a null readable
(a merely noisy proxy attenuates **both** slopes; a preferred amplitude flattens only the mode row):

| build | proxy | slope MODE | slope SHAM | contrast |
|---|---|---|---|---|
| V281r3 | command slew | **0.916 [0.741–1.133]** | 0.332 [0.162–0.494] | **+0.584** |
| V281r3 | steer rate | 0.567 [0.474–0.661] | 0.138 [0.052–0.219] | **+0.429** |
| V281r3 | demand idx | 0.528 [0.392–0.689] | 0.150 [0.036–0.254] | **+0.379** |
| V282 | command slew | 0.287 [0.171–0.588] | 0.067 [0.005–0.167] | +0.220 |
| V282 | steer rate | 0.343 [0.271–0.416] | 0.088 [0.037–0.139] | +0.255 |
| V282 | demand idx | 0.370 [0.297–0.441] | 0.101 [0.040–0.166] | +0.268 |
| V288 | steer rate | 0.243 [0.131–0.348] | 0.013 [−0.083–0.120] | +0.229 |
| V289 | command slew | 0.220 [0.150–0.292] | −0.107 [−0.192–−0.031] | **+0.328** |
| V289 | demand idx | 0.176 [0.121–0.230] | −0.054 [−0.113–−0.004] | +0.231 |

The ring's amplitude rises with the drive on every build, significantly more than the sham band does.
Under (B) this contrast should be **zero**. [EVIDENCE]

And the hysteresis test — the one the brief called close to a smoking gun for (B) — is **null**. For
every build and all seven driving variables (demand index, load, speed, band excitation, 2–6 Hz content,
command slew, steer rate), the onset-minus-offset gap corrected for the ring's own decay lag has a 95 %
CI that straddles zero. The largest single row is V289 load, raw +14.99 [4.03–26.88] → lag-corrected
**+6.74 [−3.09, +17.47]**. [EVIDENCE]

### 6. No harmonics — including on the one build where 2f₀ is clean
Spectral prominence at k·f₀ in episodes vs engaged quiet, with 1.4f₀ and 2.4f₀ as the no-harmonic floor.
The V282 family is *aliased*: at f₀ ≈ 20.0 Hz, 3f₀ = 60.1 Hz folds to 39.9 Hz, on top of 2f₀ = 40.1 Hz
and unresolvable from it in a 2 s window. **V289 (f₀ 16.89) is the only build with a clean 2f₀ = 33.8 Hz**,
and it reads 1.0 (bar) / 1.3 (wire) / 1.2 (ang) in episodes against 1.0 / 0.9 / 0.9 in quiet — at the
floor — while f₀ itself reads 4.8 / 21.3 / 4.1 against 0.8 / 2.1 / 1.2. No build shows a 2f₀ excess
above its own sham multiples. [EVIDENCE]

As a **power ratio with an explicit detection bound** — 10 log₁₀[P(kf₀)/P(f₀)] with the local median
floor subtracted from both, against the same statistic at the sham multiples 1.4f₀ and 2.4f₀, which is
the level below which this instrument cannot tell a harmonic from the floor:

| channel | build | 2f₀ dB | 3f₀ dB | sham 1.4f₀ | sham 2.4f₀ |
|---|---|---|---|---|---|
| bar | V282 | −31.0 | −31.0 (aliased) | < floor | −25.1 |
| bar | **V289** (clean) | **−43.2** | −20.9 | −26.5 | −34.5 |
| wire | V282 | −19.6 | −19.6 (aliased) | −31.9 | −23.8 |
| wire | **V289** (clean) | **−22.6** | −20.6 | < floor | −23.2 |
| ang | V282 | −10.5 | −10.6 (aliased) | −14.8 | −17.4 |
| ang | **V289** (clean) | **−17.3** | −16.8 | −12.1 | −20.6 |

**REFERENCE: an ideal relay limit cycle puts 3f₀ at −9.5 dB of f₀; saturation and rate limiting put less.**
On `bar` the sham floor is −25 to −34 dB, so a relay-grade harmonic is excluded by **15–25 dB**. On `wire`
the floor is −23 to −24 dB, excluding it by ~13 dB. On `ang` the floor is only −12 to −17 dB, so that
channel excludes a relay but not a mild saturation. **No channel on any build shows a 2f₀ above its own
sham multiples.** [EVIDENCE]

⚠ These are *physical* channels downstream of the rack, so a 40 or 60 Hz harmonic is attenuated by the
plant before it is measured. The null bounds the harmonic **at the sensor**, not the harmonic content of
an internal nonlinearity. This is the weakest of the (B) tests and is reported last for that reason.

**Channels used, and why they cannot manufacture a 2f₀:** `bar` = 0x18F bytes 0–1 i16be ×1.024 (driver
torsion-bar torque), `wire` = 0x18F bytes 2–3 i16be (steer rate), `ang` = 0x14A bytes 0–1 i16be ×−0.1
(steering angle). All three are signed and straddle zero on every route (sign-positive fraction 0.40–0.68,
means of both signs). **The 0x1AB / 427 tap — the kit's rectifying channel — is used nowhere in this
study.** [EVIDENCE]

---

## THE FREQUENCY TEST, DONE PROPERLY — and a correction to how it is usually quoted

Per-episode f₀, on each build's own grinding band (18–22 Hz; **15–18.5 Hz for V289**, because the
18–22 gate is blind to its relocated line and 13–18 would have straddled the low-demand 12.4–13.8 Hz
road line):

| build | n ep | episode f₀ (Hz) | acting Kp | median demand idx |
|---|---|---|---|---|
| V278r3 | 81 | 20.020 [19.873–20.264] | 333 | 22 |
| V280r2 | 240 | 19.971 [19.897–20.081] | 330 | 21 |
| V281r3 | 62 | 19.971 [19.836–20.044] | 248 | 22.5 |
| V282 | 145 | 19.946 [19.824–20.044] | 248 | 27 |
| V288 | 47 | 19.995 [19.897–20.117] | 248 | 32 |
| **V289** | 140 | **16.162 [15.649–16.431]** | 248 | 13.25 |

🛑 **A naive pooled regression of f₀ on acting Kp gives +0.00406 Hz/count [+0.00199, +0.00612],
p = 6 × 10⁻⁵ — i.e. +1.82 Hz over Kp 248 → 696. That number is an ARTEFACT and must not be quoted.**
Acting Kp is a *deterministic function of the demand index* within a build, so the regression is
perfectly confounded with any dependence of f₀ on demand. **The confound is real and measurable:** on
the FLAT-Kp builds, where Kp is 248 at every index and therefore has zero variation,
**d f₀/d idx = +0.0138 [+0.0047, +0.0249] Hz/count, p = 0.004 → +1.19 Hz over the demand span.**
f₀ rises with demand with no gain change behind it at all.

🛑 **And the honest identified contrast is NOT the ±0.07 Hz the build medians suggest.** Comparing the
Kp-LERP arm against the flat-Kp arm inside matched cells (5 demand quintiles × 3 speed terciles, n = 231
matched weight, ΔKp = +158.8 counts):

> **Δf₀ = +0.638 Hz [−0.008, +1.580]  ⇒  d f₀/d Kp = +0.0040 [−0.0000, +0.0099] Hz/count
> ⇒ +1.80 Hz [−0.02, +4.46] over Kp 248 → 696.**

That is **consistent with zero and also consistent with ~+1.6 Hz.** The correct statement is not *"f₀ is
pinned"* but ***"any gain effect on f₀ is small and poorly determined; the phase effect is large and
unambiguous."*** The build medians (20.02 / 19.97 at Kp ≈ 330 versus 19.97 / 19.95 / 20.00 at Kp = 248)
look tighter than the data warrant because the builds differ in demand and speed composition.
🛑 **The record's "+0.4 Hz across Kp 248 → 696" should be re-stated with a CI before it is leaned on
again.** [EVIDENCE, `_scratch/fvlc_f0_controls.txt`]

**What the pattern fits, plainly.** f₀ pinned under a gain change and moved 3.8 Hz by a pure
phase change fits **(B) and (C) equally well and rules out (A)**:
- under **(B)** the cycle sits where the loop phase reaches −180°, and a *real* describing function
  makes that point independent of a pure gain change — so f₀ pinned under Kp is exactly what (B)
  predicts too;
- under **(C)** f₀ is the plant pole, which a light change in closed-loop damping barely moves
  (ω_d = ω_n√(1−ζ²), and ζ ≈ 0.03 ⇒ a 0.05 % shift);
- under **(A)** f₀ sits at the drive and should move with *neither* — **but V289's notch moved it by
  3.78 Hz, which kills (A)** unless the drive itself changed, which nothing in V289 could do.

🛑 **And V289 did not "move the line".** The 20 Hz object was *removed* (0 of 1414 present windows in
18–22 Hz, STATE §1) and a **different, pre-existing 15–17 Hz pole took over**. Reading the 3.78 Hz as
"one mode moved" is what makes the one-plant-one-pole fit fail (joint χ² 25.8,
`MODE-NATURE-V289-RECENSUS-2026-09-09.md`). **The failure of that fit is a failure of a ONE-POLE model,
not evidence of nonlinearity.** V282's own return ratio already carried the 15–17 Hz pole at |L| 1.13
with 30° of margin; a two-pole plant needs no nonlinear mechanism at all.

**Not a rotating source.** Per-episode f₀ against the episode's own median |steer rate|:
+0.00196 Hz/count [+0.00035, +0.00410] → **+0.66 Hz over the p10–p90 span** — essentially flat, where a
cogging / gear-mesh / tooth-pass drive would scale with shaft speed. And against vehicle speed the slope
is **negative and significant in both demand strata on the flat-Kp builds** — −0.112 [−0.187, −0.034]
Hz per m/s at low demand and −0.206 [−0.322, −0.074] at high demand, ≈ −2 Hz over the speed span. A
rotational source's frequency rises with speed; a plant mode's falls as the tyres and rack load up.
**This is a plant-stiffness signature.**
⚠ Read the speed slope as a lower bound on magnitude: the 18–22 Hz detection band censors real
excursions past its edges. [EVIDENCE]

---

## 🛑 WHAT V288's NULL ACTUALLY LICENSES — the crux, with the arithmetic

**Measured first, on my own stratified estimate** (0.5 s windows inside episodes, 16 strata =
demand-index quartile × speed quartile with edges from the pooled data so both builds see the same bins):

> **ring amplitude ratio V288 / V282 at 19.98 Hz = 1.080 [0.926 – 1.243]** (95 % bootstrap,
> V282 n = 618 windows over r39/r3a/r3c, V288 n = 200 over r5e_v288)

i.e. the ring is, if anything, marginally **louder** on V288.

**What V288 physically was**, re-derived from the images by me, not taken from the build script:
V288 differs from V282 in **91 bytes / 6 runs** — one 4-byte hook at `0x29D72`, the cave
`0xC4BD6–0xC4C2F`, and the CRC at `0xC4FFC`. **Zero calibration cells changed**: no Kp, Kd, clamp, pole,
gain-LERP or map byte moves. The cave (build script `filter_cave()`) filters **r16 = sp**, the raw map
output, and leaves **r26 (the rate feedback) untouched** — the error is formed *after* the hook from the
filtered setpoint. So V288 **is** a reference pre-filter and the loop's return ratio L(s) **is**
byte-identical to V282's. [EVIDENCE — image diff + cave source]

## 🛑🛑 RETRACTION, 2026-09-10 — THE FILTER WAS TRANSPARENT AT THE RING

**An earlier draft of this section used |F(j2π·20)| = 0.457, the LTI pole. That is the WRONG number and
every conclusion drawn from it is withdrawn.** The `fwpath` subagent raised this while this study was
running; I re-derived it from the cave's integer arithmetic rather than relay it, and it is correct.

**The cave is not LTI.** Its body carries an anti-stick branch:

```python
d    = sp - y                 # 32-bit signed
step = d >> 4                 # V850 `sar`: ARITHMETIC, floors toward -inf
if step == 0 and d != 0:      # reached ONLY for 0 < d < 16, since sar never rounds a NEGATIVE d to 0
    step = 1                  #   <-- THIS is what breaks linearity
y    = y + step
```

For |d| < 16 the filter moves **1 count per tick** in the direction of the setpoint, i.e. it becomes a
slew-limited *follower* with a rail of 1 count/tick = 1000 sp counts/s at the 1 kHz control rate. A
20.3 Hz sinusoid of amplitude A has peak slope A·2π·20.3/1000 counts/tick, so **the rail stops binding
below A ≈ 8 counts and the filter passes the signal at unity.**

My own byte-exact integer mirror (`fvlc_v288_gain_check.py`), fundamental gain at 20.3 Hz:

| setpoint ripple A (sp counts) | 2 | 4 | 6 | 8 | 12 | 16 | 24 | 40 | ≥ 80 |
|---|---|---|---|---|---|---|---|---|---|
| **cave \|H\|** | **1.000** | **1.000** | **1.000** | **1.000** | 0.822 | 0.622 | 0.472 | 0.438 | 0.451 |
| LTI \|H\| (what was assumed) | 0.451 | 0.451 | 0.451 | 0.451 | 0.451 | 0.451 | 0.451 | 0.451 | 0.451 |

And with a large low-frequency steering command carrying the ripple — the realistic case, where the LF
slew ought to hold the `>>K` path open — the ring still sees 1.00 at A_lf ≤ 60 and only 0.61–0.83 at
A_lf = 200–600, because the 0.7 Hz carrier's own slope reaches 1 count/tick only at A_lf ≈ 227.

**The ring, in the filter's own units:** the measured 20 Hz command line is 15–40 raw 0xE4 counts
(STATE, demand-gated census) ÷ 16.1257 raw per index × 4.30 sp per index (the 6× map slope) =
**4.0–10.7 sp counts** — squarely inside the transparent regime. **V288 attenuated the grinding band
by 0–5 %, not 54 %.** [EVIDENCE, re-derived; agrees with `ADV-V288-A-ARITHMETIC-2026-09-07.md`, whose
caveat was written three days before V288 flew and was not applied when the drive was read]

**What this does to the predictions.** With κ = |F| ≈ 1.00 at the ring, **every** hypothesis predicts
ratio ≈ 1.000, including (A). The measured 1.080 [0.926–1.243] is therefore consistent with all four and
discriminates none of them. ⚠ **The bounds in the next paragraphs — "reference share ≤ 13.6 %",
"outer-loop return ratio ≤ 0.128" — are VOID; they were computed from κ = 0.457. At κ ≈ 1 the same
algebra yields no bound at all.** They are left below only so the arithmetic is auditable.

⚠ **This does NOT rescue (B).** The five (B) tests — coherence time, amplitude dispersion, plateau,
hysteresis, harmonics — use no V288 input whatsoever. And it does not rescue an *external* fixed-frequency
drive either: V289's notch moved f₀ by 3.78 Hz at unchanged gain, which no external source can do. What it
**does** reopen is the **openpilot echo loop** — ring → openpilot's unfiltered 100 Hz angle → 0xE4 → setpoint
→ ring. That is not "(A) forced"; it is a second *feedback* path that could be supplying part of the
de-damping, and V288 was supposed to have tested it and did not.
(`docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`, STATE ✨NEXT item 3.)

```
   y  =  [ L/(1+L) ] · F · r     +     [ G/(1+L) ] · d     +     [ 1/(1+L) ] · n
                          ^ V288 changes ONLY this factor.  L, G, d and n are all untouched.
```

**The table below is what the predictions WOULD have been at the designed κ = 0.457.** It is kept
because its middle rows are what actually matter — (B) and (C) coincide there for a topological reason
that survives the retraction. 🛑 **At the REALISED κ ≈ 1.00 the (A) row collapses to 1.000 as well and
the table discriminates nothing.**

| hypothesis | predicted ratio at the DESIGNED κ = 0.457 | at the REALISED κ ≈ 1.00 | why |
|---|---|---|---|
| **(A)** forced through the reference | **0.457** (−6.8 dB, −54.3 %) | **1.000** | y₂₀ = \|T\|·\|F\|·\|r₂₀\| |
| **(A′)** forced by a disturbance (road, cogging, rack, sensor) | **1.000** | 1.000 | F does not appear |
| **(C)** excited resonance | **1.000** | 1.000 | y₂₀ = \|G/(1+L)\|·\|d₂₀\|; F does not appear |
| **(B)** limit cycle | **1.000, exactly** | 1.000, exactly | the describing-function balance is `1 + N(A)L(jω) = 0`; **F is not in it** |

🛑 **(B) and (C) make the SAME prediction for a reference-path filter, so V288's null cannot separate
them — not weakly, not at all.** The brief's framing ("a partial gain cut can leave a limit cycle nearly
unchanged, so the null is weak evidence") reaches the right conclusion by the wrong route: V288 **was
not a loop-gain cut**. The reason (B) predicts no change is **topological** — the filter is not in the
characteristic equation — not a property of the shape of N(A). Under (B) the prediction is not "nearly
unchanged", it is *exactly* unchanged, in amplitude and in frequency.

**The 1/A describing-function arithmetic the brief asked for — it applies to an IN-loop cut, which this
was not.** For a loop gain scaled by κ = 0.457, the balance N(A\*)·κ·|L| = 1 forces N(A\*) up by 1/κ = 2.188:

| nonlinearity | describing function | amplitude after a ×0.457 **in-loop** cut |
|---|---|---|
| ideal relay / Coulomb friction | N = 4M/(πA), exactly ∝ 1/A | **×0.457** exactly |
| saturation, A/δ = 10 | N = 0.1271 | ×0.454 |
| saturation, A/δ = 5 | N = 0.2529 | ×0.444 |
| saturation, A/δ = 3 | N = 0.4164 | ×0.406 |
| saturation, A/δ ≤ 2 | N = 0.609 → N_new = 1.333 > 1 | **cycle EXTINGUISHED** |
| rate limiter | \|N\| ∝ 1/A with an A-dependent phase lag | ≈ ×0.457 **and ω\* shifts** |
| deadband / backlash | N ≤ 1 and *rising* in A → N_new > 1 impossible | **cycle EXTINGUISHED** |
| stick-slip | not a memoryless DF; A set by breakaway−Coulomb and local stiffness | ≈ ×1 |

So an in-loop ×0.457 would have produced either ≈×0.46 or outright extinction for every classical
memoryless nonlinearity. **It was never on offer, because the filter was outside the loop.**

**🛑 THE FOLLOWING BOUNDS ARE VOID — they assume κ = 0.457 and the realised κ was ≈ 1.00. They are
left in only so the algebra is auditable; do not quote them.** Taking the most permissive end of the CI
(ratio 0.926 — lower, because a reference contribution pushes the ratio *below* 1):

- reference-path share of the ring **amplitude**, if phase-coherent with it: **≤ 13.6 %**
  — from (1−0.926)/(1−0.457).
- if incoherent (the usual case for an autonomous ring): **≤ 42.5 % of amplitude, ≤ 18 % of power**
  — from √[(1−0.926²)/(1−0.457²)]. *This is a weak bound and should be quoted as such.*
- the **openpilot outer loop's return ratio ℓ at 20 Hz** — it passes through the setpoint, hence through
  F — solving (1−ℓ)/(1−0.457ℓ) = 0.926: **ℓ ≤ 0.128**. The outer loop contributes at most ~13 % of the
  ring's regeneration. ⚠ magnitude-only: V288 also added ~15 ms of group delay to the outer loop, so
  treat this as an order-of-magnitude bound.
- At the **point estimate** (1.080 ≥ 1) the data leave **no room at all** for a reference contribution.

**In one sentence: V288 licenses NOTHING.** Its filter was transparent at the ring's amplitude, so the
null is silent rather than negative — *a null from a filter that was not active at the amplitude of
interest is not a null*, exactly as *a null from the wrong image is not a null*. The record's reading
— *"the reference-side class is exhausted"* — **does not hold**, and the plant-mode conclusion must rest
entirely on the five measurements above, which it does.

⭐ **And the topological point survives the retraction and is worth keeping**, because it governs the
*next* experiment on this path: **a filter on the REFERENCE cannot change a limit cycle's amplitude or
frequency at all**, since it does not appear in `1 + N(A)L(jω) = 0`. So even a *correctly sized*
reference filter would have been unable to separate (B) from (C). If the command path is to be tested,
the experiment has to be sized against the ring's own amplitude **and** read for what it can actually
decide — which is whether the command path supplies excitation or regeneration, not which of (A)/(B)/(C)
the mechanism is.

### V289's detection band — verified, not asserted
Three bands are in circulation for V289's relocated line (13–18 in STATE, 14–18 from the orchestrator's
correction, 15–18.5 used here). Re-running the verdict-carrying statistics on r62+r63 under each
(`fvlc_v289_band_robustness.py`):

| band | n ep | median f₀ | median demand idx | τ_c mode | τ_c sham | ratio | plateau | CVlg peak | CVlg neigh |
|---|---|---|---|---|---|---|---|---|---|
| 13–18 | 225 | 15.063 | **7.0** | 0.345 | 0.260 | 1.33 | 0.295 | 0.687 | 0.544 |
| 14–18 | 194 | 15.552 | **10.0** | 0.385 | 0.231 | 1.66 | 0.309 | 0.682 | 0.558 |
| **15–18.5 (used)** | 140 | **16.162** | **13.2** | 0.410 | 0.242 | 1.70 | 0.289 | 0.671 | 0.572 |

**Every conclusion is band-invariant** — τ_c stays at a few tenths of a second, plateau at ~0.29–0.31,
and CVlog(peak) stays above CVlog(neighbour) under all three. The orchestrator's point about 13–18 is
confirmed and is visible in the *demand* column: at 13–18 the median episode sits at demand index 7.0,
i.e. the detector is catching the low-demand road line; 15–18.5 puts it at 13.2 and f₀ at 16.16 Hz,
which is the relocated grinding mode. **15–18.5 is the cleanest of the three**, and 14–18 is intermediate.

---

## CONSISTENCY WITH THE EXISTING RECORD

Every number below was re-derived here independently of the study that first reported it.

| claim in the record | this study | agrees? |
|---|---|---|
| f₀ 20.03–20.08 Hz on every pre-notch build | 19.95–20.02 Hz, per-episode medians, 6 builds | ✅ |
| V289 relocated the line to 15–17 Hz (demand-gated median 16.47 [15.81–16.91]) | 16.162 [15.649–16.431] | ✅ |
| ζ ≈ 0.029 of the mode | free-decay ζ_eq 0.011–0.018 (peak-selected, biased low); coherence-time ζ_eq 0.009–0.025 | ✅ same order, two independent estimators |
| V288's grinding "did not move" (envelope p50 126 vs 127) | stratified ring ratio **1.080 [0.926–1.243]** | ✅ on the measurement — but ⭐ the *reading* of it is wrong: the filter was transparent at the ring (my own integer mirror: gain **1.000** at A ≤ 8 sp counts), so the null is SILENT, not negative |
| "+0.4 Hz across Kp 248 → 696" | identified contrast **+1.80 Hz [−0.02, +4.46]** | ⚠ **the record's figure is tighter than the data support** |
| "no single LTI plant fits both V289's move and the Kp-pinning" | reproduced in spirit — and explained: it is a ONE-POLE model failing, not linearity failing | ✅ with a correction |
| the 18–22 Hz census gate is blind to V289 | 12 + 15 episodes with the fixed gate vs **57 + 83** with the band-aware one | ✅ |
| `modelrate`: a camera-locked 20 Hz comb on the command, 19.99974 Hz | reproduced independently — R2 − floor +0.19 to +0.33 on all 11 routes, both strata | ✅ |
| `modelrate`: the grinding excess in `bar` is FREE, lock frac 0.000 on 6 of 7 rows | lock frac **0.035–0.145**, median 0.065 — same verdict, but a consistent small NON-zero (method difference: whole-stratum clamping vs 20 s windows) | ✅ with a numeric correction |
| `slewburst`: a seconds-scale dose–response with no per-event trigger (≤ 13 %) | matches my §5 — amplitude tracks excitation with slope 0.18–0.92, and my bursts are ringdowns, not triggered events | ✅ |
| `slewburst`: the phase-locked ceiling is 1/(1−e^(−2πζ)) = 6.0, not 17× | confirmed arithmetically; I never used the 17× figure. It matters here: a locked comb *could* have built to 6× a single kick — and did not, because the ring is not locked | ✅ |

---

## WHAT EACH VERDICT WOULD HAVE IMPLIED — and what mine implies

| if the answer were | do this | this is ruled out |
|---|---|---|
| **(A)** forced | find and remove the drive; a loop fix is beside the point | damping levers, nonlinearity hunts |
| **(A″)** modeld's camera comb forces the ring | **measured: it supplies 3.5–14.5 % of the grinding energy.** Deleting it buys 3–8 % of amplitude — real, cheap, not a cure | it being *the* mechanism |
| **(A‴)** the openpilot echo loop *regenerates* the ring — **still open** | measure the outer loop's return ratio at 20 Hz; the command's 20 Hz energy is 70–81 % FREE, i.e. echo | nothing yet — V288 was meant to test this and was transparent |
| **(B)** limit cycle | remove the nonlinearity (D clamp `0xC61B6`, sum clamp `0xC61BE`, the 123/frame slew cap, rack stiction) or the phase lag; reducing excitation barely helps; a ×2 loop-gain cut would halve or kill it | adding damping as the primary fix |
| **(C)** excited resonance ✅ | raise damping *at the mode*, or reduce the **sensitivity peak** \|1/(1+L)\| across the whole band the modes live in; reducing excitation helps in proportion | drive-hunting and nonlinearity-hunting |

**Under (C), what follows for this kit — and it is not comfortable:**

1. **The lever is the sensitivity peak across 12–26 Hz, not a notch at one frequency.** V289 proves the
   mechanism works and proves the trap in one drive: it drove |L| at 20.04 Hz to 0.011 (−39.3 dB), the
   20 Hz object vanished completely — and the ±41.6° of notch skirt spent the 30° of margin the
   *already-present* 15–17 Hz pole had, so that one took over at the same measured ζ. **A build that
   lowers Ms at one frequency while raising it at another is a lateral move, and that is what the
   operator felt.** Design against **max Ms over 12–26 Hz**, and pre-register the *whole* band.
2. ⭐ **Amplitude tracks excitation with a slope well below 1 (0.18–0.92 across builds and proxies).**
   That is the signature of a *resonant transfer from a broadband drive*, and it means shaving excitation
   buys only ×0.5^β for a halved drive — real, but sublinear.
   🛑 **I withdraw the claim that the excitation-side class is closed.** It rested on V288, and V288 was
   transparent at the ring. **The command path is untested at the ring's amplitude and is the cheapest
   open lever in this report**, because it can be tested on the FORK, with no ECU flash at all.
3. **The firmware-side options remain (i) broadband roll-off inside the rate loop above ~10 Hz, which is
   exactly what costs transient authority and is what put option C at pkR 0.928 against the operator's
   0.95 floor; or (ii) lowering the loop's crossover so that neither pole is inside it.** Both are the
   same trade the operator already declined once.
   🛑 **On the fork-side lever, I now have a price and it is small.** Filtering the camera comb out of
   the command is worth **×0.967 of grinding amplitude at the median route, ×0.925 at the worst** — 3–8 %.
   That is measured, not modelled: the comb accounts for 3.5–14.5 % of the grinding band's excess energy
   and locked/free energies are orthogonal. **It is cheap (no flash, no drive risk, no EPS authority cost)
   but it is not a cure, and a drive spent scoring 3–8 % would not be readable** — by the kit's own
   readability arithmetic, the within-drive stratified contrast could not resolve a ×1.22 effect, let
   alone ×1.03. If it is done, do it as a *free rider* on a drive that is being spent on something else,
   and do not pre-register it as the thing being tested.
   ⭐ **The broader fork-side question is different and still open**: the comb is only one component of
   the command's in-band content. The rest of the command's 20 Hz energy is FREE — i.e. it is the echo of
   the ring — and an echo that returns with the wrong phase is regeneration. **Measuring the openpilot
   outer loop's return ratio at 20 Hz is still worth doing, and V288 did not do it.**
4. **Any next build in this class must carry a probe on the loop's OWN sensitivity, not on one line.**
   The instrument that would have predicted V289's outcome before the drive is a measurement of |1+L|
   across 12–26 Hz, not the 18–22 Hz census gate. The gate was blind to exactly the thing that went
   wrong.

---

## WHAT I COULD NOT DETERMINE

1. **The decay rate itself.** The mode's post-peak decay (1.4–1.9 /s) is only ~1.5–2× its own
   peak-selection artefact and the CIs overlap the sham column. The *absence of a plateau* is solid; the
   numerical ζ is not. A clean free-decay ζ needs the episode-terminated fits the record already has
   (ζ ≈ 0.029), not this estimator.
2. **Whether the excitation is road, rack, or motor.** Every proxy available is a CAN channel inside the
   steering system, so "excitation" here is measured through the very plant whose response I am
   scoring. **An IMU / accelerometer channel, which the kit has for r5e only, is the instrument that
   would separate road input from rack-generated input** — it is off the EPS entirely. That is the single
   highest-value missing measurement in this study.
3. **Whether the 15–17 Hz and 20 Hz objects are two plant poles or one pole plus one loop crossover.**
   My data says they are two distinct objects with the *same* measured damping and different
   frequencies, and that a one-pole model cannot hold both. Deciding between "two plant poles" and "one
   plant pole plus the loop's own crossover" needs a swept or shaker-style excitation the car cannot give
   from a symptomatic drive.
4. **V289's demand exposure is not matched to V282's** (median episode demand index 13.25 vs 27), so the
   V282→V289 *amplitude* contrast in this report is confounded and is deliberately not quoted. Only the
   V282→V288 contrast is stratified, and only that one is used.
5. **The openpilot outer loop's return ratio at 20 Hz.** I bounded the *comb* (a drive) but not the
   *echo* (a feedback). 70–81 % of the command's own in-band energy is free, i.e. ring-locked rather than
   camera-locked, and whether that returns as regeneration or as damping is unmeasured. My V288-based
   bound on it is void. This is the cheapest remaining open question in the study.
6. **Stick-slip specifically.** Classical (B) is excluded, but stick-slip is not a memoryless describing
   function and its clearest signature is hysteresis, which I tested and found null. If the operator
   wants that closed harder, the test is a slow, deliberate steer-torque ramp up and down at constant
   speed — a *designed* manoeuvre, not a symptomatic drive.

---

## METHOD NOTES THAT MATTER

- **Episode detection is the V282 census recipe in substance** (2 s windows / 0.5 s step, 12–26 Hz peak
  prominence ≥ 8 **and** band amplitude ≥ 40 raw, episode = contiguous ≥ 0.5 s present run inside an
  engaged run) with one change: **the amplitude band is the build's own.** `wire_0xe4_20hz.episodes_of`
  hard-codes 18–22 Hz, which finds **12 and 15** episodes on r62/r63; the band-aware detector finds
  **140** on the same two routes. Any cross-build episode count taken from the 18–22 gate on a V289 route
  is a gate miss.
- **Every distributional statistic has a matched control in the same windows** — a SHAM band at
  25.5 ± 1.5 Hz and a NEIGHBOUR band at 30.0 ± 1.5 Hz, the same width as the mode band, selected by the
  mode band's detector and not by their own. Read the contrast, never the mode column alone.
- `_prom_band` is `G2.prom_spectrum` restricted to the rows in the band, chunked over the window axis —
  bit-identical inside the band, bounded memory (the unrestricted form materialises ~3 GB at 2 000
  windows).
- Python is the `bin_decompile` conda env; `ACCORD_FIRMWARE_ROOT` points at `../accord-firmwares`.
  No disassembler was needed: the only firmware work here is a raw byte diff of three images.
