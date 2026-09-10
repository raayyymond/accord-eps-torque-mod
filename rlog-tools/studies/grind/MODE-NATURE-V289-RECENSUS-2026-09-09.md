# MODE-NATURE RE-CENSUS WITH THE V289 ROUTES — 2026-09-09

Subagent `modenat2` (resuming `modenat`, killed mid-run by the machine restart). **Analysis only: builds nothing,
flashes nothing, sends nothing on the wire.**

**Question put to this agent:** the 2026-09-08 study concluded *"the 20 Hz line is a PLANT MODE the loop de-damps,
f pinned 20.03–20.08 Hz across Kp 248–696"*. V289 rev 1 — a **phase-only** edit (notch on the clamped rate-loop
output S, 20.04 Hz Q 3.0; feedback lag pole 16.5 → 25 Hz; Kp / Kd / clamps / gain / map all unchanged) — flew on
r62/r63 and the grinding line **moved to 15–17 Hz**. A pinned plant mode does not move 3.3 Hz on a phase-only change.
Re-census, refit, back out the plant, and return a verdict.

**Scripts (all in `rlog-tools/studies/grind/`, raw output in its `_scratch/`):**

| script | output | what it does |
|---|---|---|
| `mode_nature_v289_recensus.py` | `_scratch/mode_nature_v289_recensus.txt` | the census, free-decay fits, closed-loop transfers, the 427 plant tap, exact closed-loop poles per plant family, the joint refit, and the plant back-out |
| `mode_nature_v289_addenda.py` | `_scratch/mode_nature_v289_addenda.txt` | the post-lag-term sign check, the ζ′ = ζ/√(1+k) "spring" test, and each family's Δχ² ≤ 4 width |
| `mode_nature_v289_kp_pinning.py` | `_scratch/mode_nature_v289_kp_pinning.txt` | tests the clamp explanation for the Kp-pinning against the measured ring amplitudes |
| `mode_nature_v289_reconcile.py` | `_scratch/mode_nature_v289_reconcile.txt` | refits all four families to V289's move **and** the Kp-pinning together, with four pre-registered falsifiable questions |

11 routes, 14 678 windows (2 s, 0.5 s step, engaged lateral), builds V278r3 / V280r2 / V281r3 / V282 / V288 / V289.
Every cell (Kp knots, Kd, lag, fb, gain, clamps) is read from that build's own plain image, and asserted before use.

---

## 0. THE VERDICT IN FIVE LINES

1. 🛑 **The widened 12–26 Hz band contains TWO different lines.** Separating them needs an LKAS **demand** gate, not a
   speed or amplitude gate. Every pooled median in my predecessor's numbers — and in the first version of this
   run — mixed them and landed at a spurious ~14.8 Hz.
2. **The 20 Hz line is still a plant mode the loop de-damps.** The 2026-09-08 classification **SURVIVES**, and is now
   stronger: the Kp-pinning is confirmed *model-free at matched load*, and the clamp explanation for it is falsified.
3. **V289's notch did exactly what it was designed to do.** It did not shift the 20 Hz mode — it removed the loop gain
   feeding it (|N| = 0.011, −39.3 dB), and the 18–22 Hz band is now **EMPTY**: 0 of 1414 present V289 windows.
4. **The 16.6 Hz line is a DIFFERENT pole** — a crossing V282 already carried with |L| 1.13 and 30° of phase margin,
   which the notch skirt (−41.6°) and the new fb pole (+11.5°) spent. That one *is* the loop's own crossover.
5. **No single LTI plant carries both facts** (best joint χ² 25.8, ζ wrong by 2–14×). The one-plant-one-pole model is
   the thing that broke, not the plant-mode classification.

---

## 1. 🛑 THE WIDENED BAND CONTAINS TWO LINES — READ THIS BEFORE ANY NUMBER BELOW

**EVIDENCE.** Method: f0 median cross-tabbed by LKAS demand index × speed over all present windows
(`mode_nature_v289_recensus.py`, section 1e). `idx` is the live assist-map demand index: `idx < 5` means openpilot is
asking for essentially nothing; `idx ≥ 20` means the rate loop is working.

**V282 + V288** — f0 median / n:

| idx \ v | 0–6 m/s | 6–12 | 12–20 | 20–40 |
|---|---|---|---|---|
| 0–5 | n=3 | 12.95 / 54 | 13.26 / 229 | 13.72 / 603 |
| 5–20 | 19.90 / 77 | 14.66 / 247 | 13.79 / 296 | 13.10 / 396 |
| **20–60** | **20.01 / 136** | **20.02 / 170** | **19.62 / 56** | n=11 |
| **60–300** | **20.03 / 130** | **20.01 / 122** | **19.11 / 30** | n=0 |

**V289** — the same table:

| idx \ v | 0–6 m/s | 6–12 | 12–20 | 20–40 |
|---|---|---|---|---|
| 0–5 | n=1 | 13.48 / 26 | 13.78 / 189 | 12.40 / 401 |
| 5–20 | 16.20 / 45 | 15.05 / 81 | 13.84 / 170 | 12.38 / 169 |
| **20–60** | **16.74 / 95** | **16.38 / 48** | **16.54 / 43** | n=3 |
| **60–300** | **16.30 / 101** | **16.17 / 36** | n=6 | n=0 |

- The **low-demand line** (idx < 5) sits at 12.4–13.8 Hz, **falls with speed**, carries ~4 raw of command amplitude at
  its own frequency, and is at the **same frequency on V282, V288, V289 and the Kp-LERP builds**. It does not care what
  the loop is doing. It is a road/plant line, not the grinding mode.
- The **high-demand line** (idx ≥ 20) sits at **20.0 Hz** on V278r3 / V280r2 / V281r3 / V282 / V288 and at
  **16.2–16.7 Hz** on V289, at **every** speed bin 0–20 m/s, and carries 15–40 raw of command amplitude.

The 2026-09-08 band (15–26 Hz) excluded most of the low-demand line **by accident**. Widening to 12–26 Hz without a
demand gate mixes the two and drags every pooled median to ~14–15 Hz. **Everything below uses the demand-gated
population (`idx ≥ 20`).**

**Independent confirmation that uses no census gate at all** — the pooled wheel-rate auto-spectrum peak in 12–26 Hz
(section 3; the pooling condition is engaged / v < 8 m/s / |bar| < 400, with no prominence or amplitude gate and no
per-window line-finding): V282 **19.92 Hz** (×3.4 the band median), V288 **19.92 Hz** (×3.7), V289 **16.80 Hz** (×10.3).

### 1a. The demand-gated census

| build | f0 demand-gated (Hz) | n | f0 low-demand (idx<5) |
|---|---|---|---|
| V278r3 | 20.07 [19.45–21.13] | 285 | 13.03 [12.46–13.79] |
| V280r2 | 20.03 [19.24–21.07] | 704 | 13.02 [12.21–14.03] |
| V281r3 | 20.01 [19.86–20.13] | 227 | 13.17 [12.71–13.70] |
| V282 | 19.98 [19.57–20.20] | 490 | 13.57 [12.65–14.37] |
| V288 | 20.03 [19.72–20.25] | 165 | 13.62 [12.34–14.84] |
| **V289** | **16.47 [15.81–16.91]** | 332 | 12.76 [12.05–13.29] |

**f0 histogram of present windows, 1 Hz bins** — the V289 row is the headline:

| build | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V282 | 418 | 352 | 322 | 106 | 24 | 23 | 17 | 222 | 279 | 12 | 4 | 2 | 3 | 6 |
| V288 | 110 | 84 | 152 | 47 | 14 | 8 | 10 | 51 | 112 | 7 | 0 | 1 | 0 | 2 |
| **V289** | 414 | 206 | 112 | **172** | **235** | **63** | **1** | **0** | **0** | **0** | 2 | 2 | 1 | 7 |

🛑 **The 18–22 Hz band is EMPTY on V289** — 1 count in 18 Hz and zero in 19/20/21, out of 1414 present windows.
The notch did not move the 20 Hz line. It **removed** it.

### 1b. Free-decay fits — the measured targets

Demand-gated, ≥ 0.5 s present runs, ζ = −g_d/2πf₀ from the bar envelope at f₀ ± 2 Hz. 498 episodes, 473 with a
measurable decay.

| build | n | ζ p10/p50/p90 | ζ median CI95 | f₀ p50 | f₀ median CI95 |
|---|---|---|---|---|---|
| V278r3 | 53 | 0.002 / **0.018** / 0.080 | 0.012–0.036 | **20.13** | 20.01–20.47 |
| V280r2 | 152 | 0.006 / **0.024** / 0.086 | 0.021–0.031 | **20.06** | 19.84–20.22 |
| V281r3 | 42 | 0.004 / **0.023** / 0.069 | 0.013–0.036 | **19.99** | 19.92–20.06 |
| V282 | 114 | 0.003 / **0.029** / 0.094 | 0.018–0.044 | **19.96** | 19.84–20.07 |
| V288 | 39 | 0.003 / **0.020** / 0.078 | 0.011–0.033 | **20.15** | 19.96–20.20 |
| **V289** | 73 | 0.004 / **0.029** / 0.092 | 0.019–0.040 | **16.63** | 16.51–16.82 |

(The low-demand control population, run through the same pipeline for the record, gives 12.7–13.9 Hz on every build.)

### 1c. A method note that matters for anyone re-running this

`GI.line_of` uses `nfft = 4096` on 200-sample windows, and `G2.prom_spectrum` then allocates a 2049×2049 float array
(32 MiB) **per call** — the first census run died with `_ArrayMemoryError` and would have taken ~100 minutes had it not.
I replaced it with a banded prominence floor that computes the same median over the same fixed offset annulus, only for
the rows in [lo, hi]. **Verified identical:** 264 windows, 0 disagreements with `GI.line_of` on both signals
(`verify_line_of()`, cached in `_scratch/mode_nature_v289_lineof_check.txt`). The census is also cached per route, so a
killed run resumes.

---

## 2. THE JOINT REFIT OF ALL FOUR PLANT FAMILIES

Exact closed-loop poles from the roots of 1 + L(z) = 0 — **not** the |S|-peak proxy the 2026-09-08 study used. Plant
ZOH-discretised at 1 kHz with an integer-tick delay; electronics byte-exact from each image, including the ZOH half-tick.

**The four 2026-09-08 fits as they stand**, under V282's, V288's (= V282's loop; the V288 pre-filter is outside it) and
V289's electronics:

| plant | V282 f / ζ | V288 f / ζ | V289 f / ζ | χ² | rel. L |
|---|---|---|---|---|---|
| smooth | 19.87 / +0.033 | 19.87 / +0.033 | 16.32 / −0.016 **UNS** | 48.2 | 1.000 |
| resonant | 20.26 / −0.012 **UNS** | 20.26 / −0.012 **UNS** | 21.09 / −0.003 **UNS** | 290.4 | 0.000 |
| smooth+mode | 21.63 / +0.022 | 21.63 / +0.022 | 22.67 / +0.016 | 340.0 | 0.000 |
| weak-mode | 21.58 / +0.016 | 21.58 / +0.016 | 22.42 / +0.018 | 314.1 | 0.000 |
| **measured** | **19.96 / 0.029** | **20.15 / 0.020** | **16.63 / 0.029** | | |

Only `smooth` survives the *ranking*, and even it is rejected in absolute terms (χ² 48.2, and it predicts V289
**unstable** at 16.32 Hz against a measured 16.63 / +0.029). **All four 2026-09-08 fits are rejected on the two-build
data.** My predecessor's reproduction of the 2026-09-08 solver is confirmed: it returns 19.87 Hz ζ +0.033 for `smooth`
on V282, matching the earlier study's 19.87/0.033.

**Joint refit** to the V282 pole + the V289 pole + the off-line 427 tap |G| and ∠ at 10 and 15 Hz (weight 0.3), grid
search, τ in whole ms:

| best joint fit | V282 f / ζ | V289 f / ζ | χ²(poles) | total | rel. L |
|---|---|---|---|---|---|
| **smooth+mode** g0 0.0469, τ 2 ms, f1 20 Hz, fp 24.5 Hz, ζp 0.25 | 19.43 / 0.033 | 16.24 / 0.035 | **3.7** | 3.9 | **0.804** |
| smooth g0 0.0693, τ 9 ms, f1 30 Hz | 19.98 / 0.094 | 16.27 / 0.021 | 7.0 | 7.8 | 0.150 |
| weak-mode g0 0.0431, τ 4 ms, f1 30, fp 21.0, ζp 0.10, κ 0.3 | 19.89 / 0.009 | 17.16 / 0.052 | 9.4 | 9.7 | 0.046 |
| resonant g0 0.0176, τ 1 ms, f1 12, fp 19.0, ζp 0.080 | 17.87 / 0.025 | 16.83 / 0.081 | 40.2 | 41.9 | 0.000 |

⇒ **conditional on one pole explaining both builds**, the surviving plant is smooth, or smooth plus a *heavily damped*
(ζp 0.25) mode at 24.5 Hz — barely a mode. A lightly damped plant resonance in 16–21 Hz is excluded (rel. L 0.000).
🛑 **Section 5 shows that premise is wrong**, so read this table as "the best fit *if* one pole explains both builds".

### 2a. Family width — the phase/|G| band 8–30 Hz

Every grid plant within Δχ² ≤ 4 of its family's best joint fit (`mode_nature_v289_addenda.py` section B). Phase in deg,
|G| in e-3 deg/s per T count:

| f (Hz) | 10 | 12.5 | 15 | 16.5 | 18 | 20 | 22 | 25 |
|---|---|---|---|---|---|---|---|---|
| smooth ∠ | −51 | −63 | −75 | −82 | −89 | −98 | −108 | −121 |
| smooth \|G\| | 66–70 | 64–67 | 62–63 | 60.6–60.7 | 58–59 | 55–58 | 53–56 | 49–53 |
| smooth+mode ∠ | −48 | −60 | −74 | −83 | −94 | −110 | −130 | −164 |
| smooth+mode \|G\| | 49 | 51 | 54–55 | 56–58 | 59–61 | 63–64 | 65 | 56–57 |
| weak-mode ∠ | −35 | −45 | −56 | −64 | −76 | −106 | −151 | −139 |
| weak-mode \|G\| | 35–59 | 36–56 | 40–55 | 44–56 | 49–59 | 46–66 | 19–57 | 8–16 |
| **POOLED ∠ (min…max)** | −56…−35 | −68…−45 | −79…−56 | −87…−64 | −96…−76 | −128…−95 | −174…−103 | −184…−114 |
| **POOLED \|G\|** | 35–70 | 36–67 | 40–63 | 44–61 | 49–61 | 46–66 | 19–65 | 8–57 |

The kept sets are narrow: smooth keeps τ ∈ {7, 9} ms and f1 ∈ {20, 30}; smooth+mode keeps τ = 2 ms, f1 = 20,
fp ∈ {24.0, 24.5}, ζp = 0.25.

---

## 3. THE PLANT, BACKED OUT FROM THE TWO MEASURED LINE FREQUENCIES

### The condition, and why this one

**The −180° crossing, with an error bar derived from the measured ζ.** At a lightly damped closed-loop pole that is the
**loop's own** (its residue in the sensitivity is order 1), L(jω₀) sits within |1+L| ≈ 2ζ of −1, so

> ∠L(ω₀) = −180° ± 2ζ rad   and   |L(ω₀)| = 1 ± 2ζ.

This is the peak-of-|S| condition made quantitative; I state it as the −180° crossing because the error bar then follows
directly from the measured ζ rather than from an arbitrary window around a spectral peak. It does **not** hold for a
weakly coupled plant mode the loop merely de-damps (small residue in S). The electronics side includes the ZOH
half-tick, so the plant point is *"motor-current command at the hold → wheel rate on the 0x18F wire"*.

### The two points

| | V282 | V289 |
|---|---|---|
| line f₀ | 19.96 Hz [IQR 17.90–20.28] | 16.63 Hz [IQR 16.30–17.08] |
| measured ζ | 0.029 [IQR 0.009–0.075] | 0.029 [IQR 0.011–0.070] |
| electronics \|Re\| (×CPD 8) | 14.095 T counts per deg/s | 14.131 |
| electronics ∠ | −75.7° (slope −1.7 °/Hz) | −99.7° (slope −11.2 °/Hz) |
| of which the notch | — | ×0.748 / **−41.6°** |
| of which the fb pole | — | ×1.180 / **+11.5°** |
| **⇒ PLANT ∠** | **−104.3° ± 8.8** (condition ±8.6, f-spread ±2.0) | **−80.3° ± 9.1** (condition ±8.0, f-spread ±4.3) |
| **⇒ PLANT \|G\|** | **70.9 e-3** deg/s per T count [61.7–83.4] | **70.8 e-3** [62.1–82.2] |

- **Two-point slope** −7.2 ± 3.8 deg/Hz = **20.0 ± 10.5 ms** of equivalent pure delay if it were all delay.
- **|G| ratio 20 / 16.6 = 1.00** — the plant magnitude is **flat** across the band. No resonance bump between the two.

**Cross-check against the 427 tap** (offset-corrected, engaged, v < 8, hands-off):

| pool | at 16.4 Hz | at 20.3 Hz |
|---|---|---|
| V282 (r39+r3a+r3c) | \|G\| 48.9 e-3, ∠ −87°, coh 0.43 | \|G\| 47.6 e-3, ∠ −100°, coh 0.52 |
| V288 (r5e) | 44.0, −92°, 0.46 | 45.3, −95°, 0.55 |
| V289 (r62+r63) | 57.9, −88°, **0.72** | 47.2, +75°, coh 0.27 (the notch killed the drive here) |
| V280r2+V278r3 | 41.6, −73°, 0.40 | 52.5, −88°, 0.66 |

Phase agrees with the back-out to **4–8°**, inside the error bar, on both points. Magnitude is ~1.45× lower on the tap —
expected, since an H1 estimator at coherence 0.43–0.52 is biased low (attenuation bias); its **ratio** 0.97 matches the
backed-out 1.00. Treat the backed-out magnitude as the better one and the tap as the phase corroborator.

### 🛑 Status of the two points after section 5

- **16.63 Hz: EVIDENCE.** That pole *is* the loop's own crossover (section 5), so the condition holds, and the tap
  corroborates the phase independently.
- **19.96 Hz: CONDITIONAL, not evidence.** Its derivation assumes the 20 Hz line is the loop's own crossing, which the
  Kp data denies. It happens to agree with the tap phase and with a smooth extrapolation from 16.63 Hz, so it is
  probably about right as a number — but do not size a build on it.

### What it says about V282 and V289

With the backed-out plant, **V282's loop at 16.63 Hz had |L| 1.13 at ∠ −150° — 30° of phase margin**. V289's notch
skirt (−41.6°) and fb pole (+11.5°) net −28.9°, and spent essentially all of it. At 20 Hz V289's loop is |L| 0.013 —
the notch took it out completely. **The relocation was fully predictable from the notch skirt before the drive.**

---

## 4. IS PROPORTIONAL RATE FEEDBACK A SPRING OR A DAMPER THROUGH THIS PLANT?

**Neither — it is worse than a spring.** Sweeping a scalar loop-gain multiplier k over the whole V289 loop
(`mode_nature_v289_addenda.py`), on **8 of 8** fits ζ falls monotonically and goes negative:

| fit | ζ at k=0 | k=0.25 spring / actual | k=0.5 spring / actual | k=1.0 spring / actual |
|---|---|---|---|---|
| joint-refit smooth | 0.0208 | 0.0186 / **−0.0154** | 0.0170 / **−0.0394** | 0.0147 / **−0.0696** |
| joint-refit smooth+mode | 0.0351 | 0.0314 / **−0.0048** | 0.0287 / **−0.0349** | 0.0248 / **−0.0745** |
| joint-refit weak-mode | 0.0520 | 0.0465 / 0.0224 | 0.0425 / **−0.0003** | 0.0368 / **−0.0308** |
| joint-refit resonant | 0.0813 | 0.0727 / 0.0604 | 0.0664 / 0.0382 | 0.0575 / **−0.0058** |

("spring" = ζ′ = ζ/√(1+k).) The frequency prediction fails too: a spring would give f × √(1+k), i.e. 16.27 →
18.19 / 19.93 / 23.01 on the smooth refit; the actual poles are 16.64 / 17.02, and at k = 1.0 the least-damped pole
jumps to a *different* one at 27.53 Hz. So the mechanism is not stiffening — it is a **phase-lag-driven de-damper**:
the extra gain pushes the crossing outward into more plant lag and the root locus goes RIGHT, not up.

⇒ **Any V290 candidate that adds proportional rate feedback is adding anti-damping at this crossing.**

**Re-confirmed, the added post-lag term class is closed either sign.** S′ = y_post ∓ (S − y)>>3 replaces N·H_lag by
N·H_lag ∓ (1/8)(1 − N) in the forward path. |R| at 20 Hz goes **0.023 → 1.137 (minus) / 1.091 (plus)**: (1−N)/8
bypasses the 5 Hz output lag and re-injects exactly the 20 Hz content the notch removed. Minus drives the 16.4 Hz pole
to ζ −0.041…−0.082; plus removes it but the crossover reappears at 26.9–27.0 Hz with ζ +0.006…+0.024. On the three
mode-carrying 2026-09-08 fits the signs reverse — but those fits are rejected (section 2), so the claim
*"minus lowers, plus raises on 8/8 fits"* is **not supported**: it holds on 4 of 8, and specifically on the fits that
survive.

---

## 5. THE VERDICT ON THE Kp-PINNING — AND WHY IT REVERSES THE POST-V289 READING

### 5a. The pinning is real, and it is model-free

**EVIDENCE** (`mode_nature_v289_kp_pinning.py` section 0). The Kp-LERP builds index Kp off the demand index, so a raw
"f0 by Kp bin" table is confounded with load.
Matching **flat-Kp (Kp 248 fixed) against the Kp-LERP builds inside the same demand stratum** — same demand, same hands
load, same plant — isolates the Kp lever:

| idx stratum | n flat | f0 at Kp 248 | n LERP | f0 at LERP Kp | LERP Kp | **Δf0** |
|---|---|---|---|---|---|---|
| 20–30 | 218 | 19.91 [17.42–20.10] | 193 | 20.03 [19.76–20.25] | 337 | **+0.12** |
| 30–45 | 183 | 20.02 [19.83–20.18] | 168 | 20.03 [19.82–20.32] | 388 | **+0.01** |
| 45–70 | 174 | 20.03 [19.84–20.20] | 158 | 20.08 [19.80–20.89] | 458 | **+0.05** |
| 70–110 | 182 | 20.01 [19.76–20.20] | 139 | 20.15 [18.73–22.18] | 582 | **+0.15** |
| 110–200 | 107 | 20.03 [19.67–20.24] | 166 | 19.88 [16.02–22.40] | 696 | **−0.15** |

**Δf0 = 0.00 ± 0.15 Hz across a ×2.81 Kp.** Meanwhile ζ **does** respond: 0.033 (Kp 240–320) → 0.030 (320–450) →
0.018 (450–700). The cells are acting; they just do not move the frequency.

### 5b. The clamp explanation is FALSIFIED

**EVIDENCE** (`mode_nature_v289_kp_pinning.py`). Each demand-gated window's measured ring amplitude at its own f₀
(`bamp` = √2·std = the sinusoid's peak, deg/s) pushed through the byte-exact chain, then compared to the real clamps
read from the image (D clamp 0xC61B6 = 10240, sum clamp 0xC61BE = 15360, out clamp 0xC61B4 = 3072):

| stratum | n | rate p50 | E p50 | D p50 | P+D p50 | S p50 | clamp binding (D / sum / out) |
|---|---|---|---|---|---|---|---|
| flat-Kp Kp=248 | 882 | 3.25 deg/s | 515 | 1022 | 1163 | 46 | **0.0 % / 0.0 % / 0.0 %** |
| V289 Kp=248 | 332 | 2.94 | 520 | 837 | 1000 | 48 | **0.0 % / 0.0 % / 0.0 %** |
| Kp-LERP 300–400 | 319 | 4.57 | 720 | 1457 | 1824 | 72 | **0.0 % / 0.0 % / 0.0 %** |
| Kp-LERP 400–500 | 174 | 6.81 | 1067 | 2148 | 2926 | 114 | **0.0 % / 0.0 % / 0.0 %** |
| Kp-LERP 500–600 | 117 | 7.99 | 1227 | 2528 | 3723 | 140 | **0.0 % / 0.0 % / 0.0 %** |
| Kp-LERP 600–700 | 379 | 7.89 | 1202 | 2516 | 4170 | 162 | **0.0 % / 0.0 % / 0.0 %** |

At 20 Hz, E = 157.2 × rate(deg/s), D = 2.009 E, P+D = 2.285 E, S = 0.03921 (P+D). So:

- the **D clamp** needs a **32.4 deg/s** ring;
- the **sum clamp** needs **42.8 deg/s**;
- the **output clamp** needs **218 deg/s**.

The measured ring is **3–8 deg/s at p50 and 7–14 deg/s at p90**, in every bin. Describing-function effective gain
equals nominal gain to three decimals in all six strata, including the top-quartile-loud subsets. **The clamps are
nowhere near the line. The hypothesis is dead.**

**Useful by-product:** C(z) = Kp/256 + (Kd/8)(1 − z⁻¹), and at 20 Hz the D term is **2.010** against a P term of 0.969
at Kp 248. So the D term carries **88 %** of |C|:

| Kp | P term | D term | \|C\| at 20 Hz (× Kp 248) | ∠C at 20 Hz |
|---|---|---|---|---|
| 248 | 0.969 | 2.009 | 2.285 (×1.000) | **+61.4°** |
| 350 | 1.367 | 2.009 | 2.500 (×1.094) | +53.3° |
| 470 | 1.836 | 2.009 | 2.806 (×1.228) | +45.6° |
| 560 | 2.188 | 2.009 | 3.062 (×1.340) | +40.9° |
| 696 | 2.719 | 2.009 | 3.481 (×1.523) | **+35.2°** |

A ×2.81 nominal Kp is only a **×1.52** loop-gain lever at 20 Hz — and it **costs 26° of the PID's phase lead**.

### 5c. What that costs the crossover reading

A loop whose **crossover** sets the frequency cannot pin it: −26° of lead and ×1.52 of gain must drag a crossover down,
and every family refitted to V289 alone predicts exactly that (`smooth` 19.98 → 18.58 **UNS**; `smooth+mode`
19.43 → 17.25 **UNS**; open-loop −180° crossings 20.9 → 16.7 Hz). The measurement says 0.00 ± 0.15 Hz and *never
unstable*.

Conversely, **f pinned + ζ falling with gain is precisely the root-locus signature of a loop closing on a lightly
damped PLANT MODE**: the locus departs the plant pole nearly horizontally.

### 5d. No single LTI plant carries both facts

I refitted all four families against V289's move **and** the Kp-pinning together, with four falsifiable questions
written down before the run (`mode_nature_v289_reconcile.py`; four grids, ~106 000 plants; targets V282 19.96/0.029,
V289 16.63/0.029, Δf(Kp 696−248) = +0.04 ± 0.30 Hz, ζ ratio 0.55, plus the tap at 10/15 Hz):

| family | best joint fit | V282 f / ζ | V289 f / ζ | χ² |
|---|---|---|---|---|
| smooth (no mode) | g0 0.0561, τ 3 ms, f1 20 | 20.30 / +0.405 | 17.11 / +0.099 | 40.8 |
| light mode (resonant) | g0 0.0124, τ 1 ms, f1 20, fp 19.25, ζp 0.090 | 18.43 / +0.031 | 17.29 / +0.081 | 48.0 |
| smooth+mode | g0 0.0136, τ 2 ms, f1 20, fp 19.00, ζp 0.100 | 17.95 / +0.036 | 16.81 / +0.080 | 65.6 |
| weak-mode (κ) | g0 0.0290, τ 2 ms, f1 30, fp 20.00, ζp 0.100, κ 0.2 | 19.62 / +0.059 | 17.68 / +0.096 | **25.8** |
| **measured** | | **19.96 / 0.029** | **16.63 / 0.029** | |

**None passes.** Best χ² 25.8 over 4 pole constraints + 4 tap constraints; the fits that honour the pinning get ζ wrong
by 2–14× (0.059–0.405 against a measured 0.029) and miss V289's frequency by 0.5–1.1 Hz.

The pre-registered questions, per best fit:

| | Q1 Kp pinning | Q2 18–22 Hz pole re-damped on V289 | Q3 V289 pole in 16.2–17.1 | Q4 \|L(20)\| on V282 |
|---|---|---|---|---|
| smooth | PASS (Δf −0.37) | PASS (none) | **FAIL** (17.11) | **0.559** — not a crossover |
| light mode | **FAIL** (Δf −1.24) | PASS (20.79 / +0.087) | **FAIL** (17.29) | **0.605** — not a crossover |
| smooth+mode | **FAIL** (Δf −1.48) | **FAIL** | PASS (16.81) | **0.573** — not a crossover |
| weak-mode | PASS (Δf −0.75) | PASS (20.73 / +0.100) | **FAIL** (17.68) | **0.435** — not a crossover |

🛑 **In all four, |L(20 Hz)| under V282 is 0.43–0.61 — well below 1.** Once the Kp evidence is admitted, no family puts
a gain crossover at 20 Hz.

### 5e. The verdict

**The 2026-09-08 "plant mode, f pinned across Kp 248–696" classification is NOT falsified. It survives, and is now
better supported than it was**: the pinning is confirmed model-free at matched load, and the one alternative
explanation on the table (clamp-limited effective Kp) is falsified by direct measurement.

**What IS falsified is the inference drawn after V289 flew** — that the 20 Hz line must have been the loop's own
crossover because a phase-only edit moved it. It did not move it. The reading that survives all the evidence is that
**there are two objects, and V289 traded one for the other:**

1. **20 Hz = a lightly damped plant mode the loop de-damps.** f pinned against Kp, ζ falling with Kp, |L| ≈ 0.4–0.6
   there. V289's notch removed the loop gain feeding it (|N| = 0.011, −39.3 dB), so the loop stopped de-damping it and
   it fell back to its own plant damping. **Measured: the 18–22 Hz band is EMPTY on V289.** The notch achieved its
   design goal completely.
2. **16.6 Hz = the loop's own crossover**, which V282 already carried at |L| 1.13 with 30° of margin, and which the
   notch skirt (−41.6°) plus the fb pole (+11.5°) pushed to marginal. This is a genuinely different pole, and it is why
   V289 is a *mixed* result rather than a cure.

**The single-LTI-plant model is what broke, not the classification.** Any future fit must carry both a lightly damped
mode near 20 Hz *and* a crossover near 16–17 Hz; none of the four families as parameterised can do that, which is
itself a finding about the model, not about the car.

---

## 6. WHAT THIS IMPLIES FOR V290 — BELIEF, NOT EVIDENCE

I did not size any candidate; that is `design290d`'s job. Stated so the design can use or discard it:

- **The target has changed.** "Damp the 20 Hz mode" is done — V289 did it, completely, and the band is empty. The
  remaining symptom lives at the **16–17 Hz crossing**, and the quantity to buy is **phase margin there**.
- **Size against the 16.63 Hz plant point** (∠ −80.3° ± 9.1, |G| 70.8 e-3 deg/s per T count [62.1–82.2]), which is
  EVIDENCE. Do not size against the 19.96 Hz point, which is conditional (§3).
- **Do not add proportional rate feedback** in any form: §4 shows it is a de-damper at this crossing on 8/8 fits, and
  the added post-lag term is closed either sign because (1−N)/8 re-injects what the notch removed.
- **Kd is the bigger gain lever and probably the cheaper one.** The D term carries 88 % of |C| at 20 Hz but only
  Kd/8·|1−z⁻¹| ∝ f at low frequency, so trimming Kd cuts loop gain at the crossing far harder than it cuts
  steady-state or low-frequency authority. Kp is the opposite trade. Neither is sized here.
- ⚠️ **Anything that lifts the loop gain back up at 20 Hz un-does V289's one clear success.** The notch is currently
  holding a plant mode out of the loop; a lead network aimed at 12–22 Hz must be checked at 20 Hz against |N| before
  it is flown.
- ⚠️ **A caution on the whole exercise**: §5d says no LTI plant in the tested families reproduces both measured facts.
  Every pole prediction in this report — including the ones I would use to size V290 — inherits that. The two-point
  plant back-out (§3) and the demand-gated census (§1) are the parts that do not depend on a fit, and they should carry
  more weight in the design than any family's numbers.

---

## 7. EVIDENCE / BELIEF LEDGER

**EVIDENCE** (method stated, re-derivable from the scripts):
- The widened band holds two lines, separable on demand, not speed (§1) — cross-tab over 14 678 windows, plus the
  gate-free pooled-PSD confirmation 19.92 / 19.92 / 16.80 Hz.
- The demand-gated line frequencies and free-decay ζ per build (§1a, §1b).
- The 18–22 Hz band is empty on V289 (§1a histogram).
- The banded prominence floor is bit-identical to `GI.line_of` (§1c), 264 windows, 0 disagreements.
- The Kp-pinning at matched load, Δf0 = 0.00 ± 0.15 Hz over a ×2.81 Kp (§5a).
- No clamp binds at the line in any stratum; the amplitudes each clamp would need (§5b).
- The plant point at 16.63 Hz (§3), and the tap phase agreement at 4–8°.
- The closed-loop pole predictions of every named fit under byte-exact electronics (§2, §4, §5d) — these are exact
  computations *given the fit*; the fits themselves are inferences.

**BELIEF** (inference, could be wrong):
- The two-object reading of §5e. It is the only reading I found that survives all the evidence, but no fitted plant
  reproduces both facts, so it is not yet a model.
- The plant point at 19.96 Hz (§3), whose derivation assumes what §5 denies.
- Everything in §6.

**RETRACTED from my own earlier message to the orchestrator this session:** the claim that the 2026-09-08 plant-mode
classification was falsified and that only the smooth/crossover fit explains V289. Sections 5a–5e supersede it.

---

*Verified before writing: every table above is copied from a run that completed to exit 0 on this machine on
2026-09-09, with the raw text preserved beside the scripts in `rlog-tools/studies/grind/_scratch/`.*
