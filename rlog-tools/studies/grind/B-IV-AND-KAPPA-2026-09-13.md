# `B(f)`'s closed-loop bias, the 10–14 Hz gap, and which r24 arm is admissible

Subagent **`biv`**, 2026-09-13. Brief from the orchestrator: close the two questions the V291
DO-NOT-FLASH turns on (`ADV-V291-B-LOOP-2026-09-13.md` §4.2, §5.2, §10 — "what would flip this to PASS",
items 1 and 2).

**Analysis only** — nothing built, nothing flashed, nothing sent on any bus, no build script edited,
no commit.

Routes: **r39** and **r6c**, both V282, on the pre-existing `analysis-2020accord/_scratch/cache/v280/`
caches. Control pool **r31–r34** (V278r3/V280r2). Scripts, all in this folder:
`b_iv_kappa.py` (estimator + per-window pooling) · `_biv_part2.py` (Q1 tables, instrument diagnostics,
the deadband inversion) · `_biv_part3.py` (window/pool scan, the incremental arithmetic, the arm-selector
check) · `_biv_part4.py` (the long-window re-measurement) · `_biv_part5.py` (the second-method
re-derivation) · drivers `_biv_run{,2,3,4}.py` → `_scratch/b_iv_kappa{,_p3,_p4,_p5}.{txt,json}`.

---

## 0. The answer, in one paragraph

**Neither of advB's two options is right, and the band it says decides the verdict is identifiable after
all — but not with an instrument.** On Q2: the ±3 post-gain deadband does **not** explain the
2353-vs-5244 factor, and it is falsified three independent ways — bof's ladder **already contains the
deadband** at every rung (byte-identical replay, max diff 0.000e+00), the post-gain magnitude the
mechanism needs (`v ≈ 5.44` counts) is **5–25× smaller than the measured median** (26–138), and the
deadband threshold that *would* reproduce the measured duty at the flown arm is **43.5–135.4**, i.e.
15–45× the cal cell's value of 3. The two remaining escapes from the effective arm are also dead: the
427 tap's encoder and the cache's decoder are **exact inverses** (`(|T|>>3)` vs `(w & 0x1ff)<<3`), and the
5244 rung **is** selected (gate byte `0x3AA96` = `0xFB` on the V282 image). The residual behaves like a
**constant multiplicative scale applied before the deadband** — the most stratum-invariant of the four
parameterisations tested (×1.21 over 16 cells against a raw duty range of 7.3×, versus ×3.12 for the
deadband). ⇒ **the admissible incremental arm is EFFECTIVE, κ = 0.449, arm ≈ 2354**, and the deadband's
own incremental cost is only ×0.85–0.98, so the V291 cut delivers **k_eff = 0.895** against its nominal
0.901. On Q1: the **0xE4 command is not a usable instrument** — it clears the pre-registered coherence
gate in only **2 of the 34 pooled** (frequency × stratum) cells, because it has almost no power at
10–14 Hz (0.17–0.23× its own 18–22 Hz line). Where it *is* usable it says the direct estimate is **not**
biased at the frequency that matters: at 20.3 Hz `|B_iv|/|B_dir|` = **×1.01 (creep) and ×1.02 (loaded)**,
phases within 4°, and split by route **3 of the 4** cells at 20.3 Hz clear the gate with ratios
**0.993–1.045**. **10–14 Hz does not become identified by instrumenting — it becomes identified by
LENGTHENING THE WINDOW.** At `nperseg` 512 (5.12 s) every frequency in 9.94–14 Hz clears coherence 0.40 on
the pooled creep data, and `|B|` and `∠B` there **move by at most 8 % in magnitude and 18° in phase**
from bof's 1.28 s values — and by ≤ 2° over 11–14 Hz.
advB's unblocking measurement is therefore available, and it **does not change the arithmetic** — it only
converts those numbers from a fit into a measurement.

**The Q2 headline re-derived by a second method** (§7): moving the comparator off the 100 Hz frame axis
onto the 1 kHz rate the ECU actually runs it at changes κ from **0.4558 to 0.4539 — 0.4 %** — so the
factor is not a sampling artefact; and computing the deadband's effect analytically straight from the
measured amplitude distribution, with no ladder and no inversion at all, gives **0.72–0.93**, not 0.449.

**Written before running** (`what a FAIL would look like`): *"B is biased and the effective arm is an
artefact"* = IV and direct disagree outside their bootstrap CIs at 20.3 Hz in **both** strata on **both**
routes, with `|B_iv| < |B_dir|` by a factor near 0.45, with the instrument passing its own exogeneity
diagnostics. *"The effective arm is real"* = IV and direct agree within CI at 20.3 Hz, so `|B|` is not
inflated. **The data returned the second.** Full pre-registration in §1.

---

## 1. Pre-registration and controls

### 1.1 The pre-registration, written before any estimator was run

Structural model defining the bias: `rate = G0·u + Gd·w` (w = road/driver disturbance),
`bar = B·rate + v` (v = the bar's response **not** mediated by rate).
`H1 = S_rate,bar/S_rate,rate = B + S_rate,v/S_rate,rate` — biased iff v correlates with rate.
`H_iv = S_cmd,bar/S_cmd,rate = B + S_cmd,v/S_cmd,rate` — unbiased iff cmd ⊥ v.

| registered outcome | what it would look like |
|---|---|
| **B is biased, the effective arm is an artefact of B** | IV and direct disagree outside CI at 20.3 Hz in both strata on both routes, `\|B_iv\|/\|B_dir\| ≈ 0.45`, instrument passing its diagnostics |
| **The effective arm is real (not a B artefact)** | IV ≈ direct within CI at 20.3 and 7.3 Hz; or `\|B_iv\| > \|B_dir\|`, which widens the gap |
| **10–14 Hz becomes identified** | `min(coh(cmd,bar), coh(cmd,rate)) ≥ 0.40` at 10/12/13/14 Hz in ≥ 1 main stratum **and** a bootstrap 95 % phase CI narrower than ±25° |
| **The deadband explains the factor** | bof's ladder does NOT contain the deadband, **and** the solved threshold θ ≈ 3 (2–5) in every stratum, **and** θ is more stratum-invariant than the arm |
| **The deadband does not explain it** | the replay already carries it, and/or θ ≫ 3, and/or θ's dispersion ≫ the arm's |

**Registered decision rule for the admissible incremental arm:** deadband → **FLOWN** (a static offset is
not an incremental gain) · constant scale on `(gain/1024)·B` → **EFFECTIVE** (the loop only ever sees the
product) · scale in `\|T\|` only → **FLOWN**, and must be checked separately.

🛑 **An instrument-validity caveat was registered in advance**, because the record already says the 0xE4
command's 20.03 Hz line is an **echo** of the wheel ring (`accord-0xe4-command-is-not-a-staircase…`;
open-loop share of T's 20 Hz = 9 %, feedback path 63 %). **If cmd were a pure echo, `cmd = E·rate`, then
`S_cmd,bar/S_cmd,rate` degenerates ALGEBRAICALLY to the direct `H1` and agreement is uninformative.** So
every agreement below is reported next to an echo measurement. §3.

### 1.2 Controls

| control | result |
|---|---|
| **C0** — my per-window pooling vs bof's `scipy.csd` pooling (r31–r34 creep, 17 frequencies) | max relative `\|H1\|` difference **4.4e-16**, max angle difference **2.8e-14°**, max coherence difference **4.4e-16**, 25 windows vs 25 → **PASS, the estimator is bof's to machine precision** |
| **C1 direct** — the record's +114°, coh 0.94, `\|B\|` 2.81 at 19.92 Hz, r31–r34 creep, instantaneous gate, nearest bin | **+115°, coh 0.94, `\|B\|` 2.80**, 28.0 s / 25 windows → **PASS to 1°** |
| **C1 IV(cmd)** — same pool, same bin | **+111°, `\|B\|` 2.92**, coh(cmd,bar) 0.46 / coh(cmd,rate) 0.44 → **PASS** (the brief's gate: +114 ± 10°) |
| **C1 IV(T427)** — same | **+116°, `\|B\|` 2.86**, coh 0.88 / 0.89 → **PASS** |
| bootstrap 95 % CI at that bin (600 block resamples, block = 2 adjacent Welch windows) | direct `\|B\|` [2.49, 2.94] ∠[+106, +117]° · IV(cmd) [2.70, 3.29] ∠[+103, +117]° · IV(T427) [2.51, 3.06] ∠[+108, +118]° |

🛑 **A control I report as a deliberate NEGATIVE:** the **427 T tap is not a valid instrument**. `T` is the
servo output, a function of the rate, so it is correlated with the feedback by construction; it is also a
50 Hz stream and therefore unusable at or above 25 Hz. Its IV **must** reproduce the direct estimate
rather than correct it — and it does (§2.3). It is carried for that reason, not as evidence.

---

## 2. Q1 — `B(f)` direct vs instrumented

Estimator: bof's, verbatim — Hann, `nperseg` 128, 50 % overlap, `detrend="constant"`, `nfft` 512,
band-averaged over `f0 ± 0.40 Hz`. `Hv = H1/√coh`. **IV USABLE requires BOTH `coh(cmd,bar)` and
`coh(cmd,rate)` ≥ 0.40.** Bootstrap: 400 block resamples over Welch windows, block length 2.

⭐ **The IV ratio is immune to any LTI filtering of the instrument itself** — the instrument's transfer
appears conjugated in both numerator and denominator and cancels — so the 0xE4 → 0x18F-frame
interpolation cannot bias it. That is worth stating because it removes the obvious objection.

### 2.1 Creep engaged hands-off, 1 s median gate, r39 + r6c pooled — 187.8 s / 240 windows

| f (Hz) | `\|B\|`dir (Hv) | ∠dir | coh dir | `\|B\|`iv | ∠iv | coh(cmd,bar) | coh(cmd,rate) | IV 95 % CI (`\|B\|`; ∠) | iv/dir |
|---|---|---|---|---|---|---|---|---|---|
| 3.0 | 2.87 | n/a | 0.29 | 1.34 | n/a | 0.19 | 0.87 | [1.09, 1.58]; [−171, −137] | ×0.47, −23° |
| 3.9 | 2.94 | −123° | 0.42 | 1.65 | n/a | 0.28 | 0.88 | [1.43, 1.84]; [−156, −122] | ×0.56, −14° |
| 5.0 | 4.19 | −108° | 0.57 | 2.49 | n/a | 0.29 | 0.82 | [2.09, 2.83]; [−128, −108] | ×0.59, −8° |
| 6.0 | 7.80 | −100° | 0.69 | 4.30 | n/a | 0.16 | 0.54 | [3.52, 4.79]; [−131, −103] | ×0.55, −16° |
| **7.3** | **10.87** | **−94°** | **0.88** | 7.44 | n/a | 0.16 | 0.34 | [6.66, 8.25]; [−124, −101] | ×0.68, −15° |
| 8.0 | 11.95 | −95° | 0.84 | 7.04 | n/a | 0.06 | 0.17 | [4.56, 9.30]; [−160, −115] | ×0.59, −39° |
| 10.0 | 12.31 | (−141°) | 0.41 | 8.97 | n/a | 0.16 | 0.30 | [4.37, 16.47]; [+126, +159] | ×0.73, −83° |
| 11.0 | 11.53 | (−146°) | 0.40 | 8.07 | n/a | 0.10 | 0.20 | [3.89, 13.79]; [+57, +145] | ×0.70, −100° |
| 12.0 | 11.36 | (−171°) | 0.45 | 8.35 | n/a | 0.13 | 0.24 | [6.05, 13.67]; [+89, +141] | ×0.73, −67° |
| 13.0 | 9.02 | n/a | 0.35 | 4.73 | n/a | 0.08 | 0.28 | [3.29, 8.47]; [+69, +142] | ×0.52, −67° |
| 14.0 | 6.32 | +149° | 0.44 | 4.06 | n/a | 0.16 | 0.39 | [3.17, 5.09]; [+99, +119] | ×0.64, −41° |
| 16.0 | 4.12 | +131° | 0.67 | 3.17 | n/a | 0.24 | 0.40 | [2.87, 3.44]; [+97, +112] | ×0.77, −25° |
| 18.0 | 3.19 | +120° | 0.85 | 2.85 | n/a | 0.38 | 0.48 | [2.71, 3.00]; [+108, +116] | ×0.89, −8° |
| **20.3** | **2.83** | **+120°** | **0.93** | **2.86** | **+116°** | **0.55** | **0.54** | **[2.65, 3.01]; [+113, +119]** | **×1.01, −4°** |
| 22.0 | 2.37 | +116° | 0.82 | 2.33 | n/a | 0.35 | 0.36 | [2.14, 2.54]; [+103, +112] | ×0.98, −8° |
| 25.0 | 2.14 | +108° | 0.53 | 2.09 | n/a | 0.25 | 0.26 | [1.85, 2.44]; [+102, +118] | ×0.98, +2° |
| 30.0 | 2.24 | n/a | 0.24 | 1.57 | n/a | 0.06 | 0.12 | [1.19, 2.11]; [+75, +112] | ×0.70, +11° |

### 2.2 Loaded high-angle, 1 s median idx gate, r39 + r6c pooled — 77.5 s / 82 windows

| f (Hz) | `\|B\|`dir (Hv) | ∠dir | coh dir | `\|B\|`iv | ∠iv | coh(cmd,bar) | coh(cmd,rate) | IV 95 % CI (`\|B\|`; ∠) | iv/dir |
|---|---|---|---|---|---|---|---|---|---|
| 3.0 | 2.21 | n/a | 0.05 | 1.35 | n/a | 0.15 | 0.41 | [0.78, 1.98]; [−132, −58] | ×0.61, −30° |
| 3.9 | 2.74 | n/a | 0.35 | 2.05 | n/a | 0.35 | 0.62 | [1.65, 2.57]; [−121, −92] | ×0.75, −5° |
| **5.0** | **3.44** | **−92°** | **0.62** | **2.67** | **−91°** | **0.44** | **0.73** | **[2.37, 2.93]; [−99, −79]** | **×0.78, +1°** |
| 6.0 | 5.88 | −89° | 0.69 | 4.24 | n/a | 0.28 | 0.54 | [3.90, 4.78]; [−107, −75] | ×0.72, −4° |
| **7.3** | **9.49** | **−91°** | **0.91** | 7.73 | n/a | 0.20 | 0.29 | [6.94, 8.64]; [−103, −90] | ×0.81, −5° |
| 8.0 | 10.75 | −91° | 0.89 | 8.50 | n/a | 0.14 | 0.23 | [7.59, 9.58]; [−113, −95] | ×0.79, −10° |
| 10.0 | 11.57 | n/a | 0.28 | 16.08 | n/a | 0.29 | 0.15 | [11.59, 22.33]; [+113, +161] | ×1.39, −53° |
| 11.0 | 9.50 | +168° | 0.44 | 10.26 | n/a | 0.22 | 0.19 | [7.90, 14.32]; [+110, +152] | ×1.08, −35° |
| 12.0 | 8.08 | +168° | 0.50 | 8.19 | n/a | 0.08 | 0.07 | [3.48, 26.20]; [+61, +131] | ×1.01, −71° |
| 13.0 | 6.08 | +147° | 0.61 | 4.98 | n/a | 0.13 | 0.19 | [3.76, 6.07]; [+114, +145] | ×0.82, −18° |
| 14.0 | 5.04 | +133° | 0.68 | 4.77 | n/a | 0.19 | 0.21 | [3.82, 5.81]; [+111, +132] | ×0.95, −12° |
| 16.0 | 3.78 | +126° | 0.79 | 3.38 | n/a | 0.13 | 0.16 | [2.70, 4.27]; [+109, +132] | ×0.89, −5° |
| 18.0 | 2.97 | +121° | 0.94 | 2.72 | n/a | 0.05 | 0.06 | [2.30, 3.28]; [+100, +124] | ×0.92, −7° |
| **20.3** | **2.74** | **+118°** | **0.96** | **2.80** | +115° | 0.37 | 0.35 | **[2.68, 2.96]; [+115, +120]** | **×1.02, −1°** |
| 22.0 | 2.28 | +119° | 0.85 | 2.51 | n/a | 0.05 | 0.04 | [1.90, 3.58]; [+118, +166] | ×1.10, +15° |
| 25.0 | 1.92 | +112° | 0.55 | 1.96 | n/a | 0.07 | 0.07 | [1.33, 2.80]; [+99, +142] | ×1.02, +6° |
| 30.0 | 1.96 | n/a | 0.25 | 2.24 | n/a | 0.12 | 0.09 | [1.43, 4.36]; [+80, +149] | ×1.14, +22° |

### 2.3 Where the two agree, where they diverge — and what is admissible

🛑 **Only 2 of the 34 (frequency × stratum) cells pass the pre-registered IV gate**: creep 20.3 Hz
(0.55 / 0.54) and loaded 5.0 Hz (0.44 / 0.73). Everything else is `n/a` by my own rule, and I do not
report a phase for it. The two usable cells say:

| cell | direct | IV | ratio |
|---|---|---|---|
| **creep 20.3 Hz** | 2.83 ∠+120° | 2.86 ∠+116° | **×1.01, −4°** |
| **loaded 5.0 Hz** | 3.44 ∠−92° | 2.67 ∠−91° | **×0.78, +1°** |

- ⭐ **At the frequency that decides the 20 Hz mode and the r24 arm, there is no detectable closed-loop
  bias.** ×1.01 and ×1.02 with the direct value inside the IV's 95 % CI in both strata. This is the
  pre-registered "the effective arm is real" outcome.
- **At 5 Hz loaded the IV is 22 % lower with an identical phase** — the direction a bar-side disturbance
  would produce, and the only usable evidence of any bias. It is one cell, and 0.78 is nowhere near 0.45.
- Below 16 Hz the IV runs systematically low (×0.47–0.81 creep, ×0.61–0.95 loaded) with tight-looking
  bootstrap CIs, **but every one of those cells fails the relevance gate**, and a weak instrument with a
  small `S_cmd,v` contamination produces exactly that pattern. **Do not read them as a bias measurement.**
⭐ **Split by route, the 20.3 Hz result is stronger than the pooled table makes it look.** Pooling two
routes partially cancels their cross-spectra and *lowers* the IV coherence; per route, **3 of the 4
route × stratum cells at 20.3 Hz clear the gate, and all three agree with the direct estimate to ±4.5 %:**

| stratum | route | direct | IV | coh(cmd,bar) / coh(cmd,rate) | iv/dir |
|---|---|---|---|---|---|
| creep | r39 | 2.90 ∠+123° | 3.03 ∠+118° | 0.57 / 0.53 ✓ | ×1.045 |
| creep | r6c | 2.75 ∠+117° | 2.73 ∠+114° | 0.55 / 0.56 ✓ | ×0.993 |
| loaded | r39 | 2.86 ∠+117° | 2.87 ∠+114° | 0.46 / 0.45 ✓ | ×1.003 |
| loaded | r6c | 2.68 ∠+119° | 2.73 ∠+119° | 0.32 / 0.31 ✗ | ×1.019 |

The anchors replicate across two routes 1580 s apart; the 12 Hz cells do not (§4.3). At 7.3 Hz the direct
estimate replicates (r39 −90° / r6c −101° creep; −89° / −93° loaded) while the IV does not clear the gate
on either route.

### 2.4 The 427-tap negative control — it behaves exactly as a non-instrument should

| stratum | f | `\|B\|`dir | ∠dir | `\|B\|`ivT | ∠ivT | coh(T,bar) | coh(T,rate) |
|---|---|---|---|---|---|---|---|
| creep | 7.3 | 10.87 | −94° | 11.26 | −95° | 0.92 | 0.85 |
| creep | 10.0 | 12.31 | −141° | 17.37 | −148° | 0.67 | 0.33 |
| creep | 12.0 | 11.36 | −171° | 12.52 | −170° | 0.56 | 0.46 |
| creep | 14.0 | 6.32 | +149° | 6.39 | +145° | 0.49 | 0.48 |
| creep | 20.3 | 2.83 | +120° | 2.81 | +120° | 0.88 | 0.89 |
| loaded | 7.3 | 9.49 | −91° | 9.37 | −92° | 0.93 | 0.96 |
| loaded | 12.0 | 8.08 | +168° | 8.69 | +169° | 0.59 | 0.51 |
| loaded | 14.0 | 5.04 | +133° | 4.93 | +131° | 0.66 | 0.69 |

**It reproduces the direct estimate to ≤ 10 % and ≤ 7° at every identified point.** That is the expected
result for a signal that is largely a function of the rate — it re-weights the same data, it does not
correct it. It is *not* evidence that B is unbiased. What it does establish is that the **direct
estimate's 10–14 Hz numbers are not an artefact of one particular weighting**, which matters for §4.

---

## 3. Why the command cannot be the instrument — measured, not argued

### 3.1 The echo

`coh(rate, cmd)` **is** the echo share: 1.0 means cmd is a pure function of the rate and the IV
degenerates to the direct estimate algebraically.

| stratum | 5 Hz | 7.3 Hz | 10 Hz | 12 Hz | 14 Hz | 18 Hz | 20.3 Hz | 25 Hz |
|---|---|---|---|---|---|---|---|---|
| creep | 0.82 | 0.34 | 0.30 | 0.24 | 0.39 | 0.48 | **0.54** | 0.26 |
| loaded | 0.73 | 0.29 | 0.15 | 0.07 | 0.21 | 0.06 | **0.35** | 0.07 |

At 20.3 Hz the echo carries **54 % (creep) / 35 % (loaded)** of the command's power, so the IV there is
**partly degenerate** — its agreement with direct is weaker evidence than the coherence alone suggests,
and I say so. Below 8 Hz the echo is strong (0.73–0.87) and the IV is close to the direct estimator by
construction. In the middle band the echo is *small*, which would be good — except that the command has
no power there at all.

### 3.2 The command has no power at 10–14 Hz — this is the mechanism

Normalised PSD, each signal's own 3–30 Hz power = 1, so the shapes are comparable.

| stratum | f | cmd | bar | rate | T427 | cmd vs its own 18–22 Hz peak |
|---|---|---|---|---|---|---|
| creep | 3.9 | **0.0789** | 0.0069 | 0.0271 | 0.0269 | ×17.5 |
| creep | 7.3 | 0.0042 | 0.0499 | 0.0145 | 0.0279 | ×0.94 |
| creep | **12.0** | **0.0010** | 0.0065 | 0.0016 | 0.0026 | **×0.23** |
| creep | **13.0** | **0.0009** | 0.0030 | 0.0014 | 0.0014 | **×0.20** |
| creep | 20.3 | 0.0045 | 0.0054 | 0.0225 | 0.0106 | ×1.00 |
| loaded | 3.9 | **0.0676** | 0.0054 | 0.0270 | 0.0128 | ×10.8 |
| loaded | **12.0** | **0.0011** | 0.0020 | 0.0010 | 0.0013 | **×0.17** |
| loaded | 20.3 | 0.0056 | 0.0022 | 0.0112 | 0.0051 | ×0.89 |

🛑 **The 0xE4 command's power at 12–13 Hz is ~1/80 of its 3.9 Hz content and ~0.2× its own 18–22 Hz
line.** An instrument with no energy in a band cannot identify that band, no matter how exogenous it is.
Lengthening the window does not help the instrument either: `coh(cmd,rate)` at 12 Hz creep goes
**0.24 → 0.25 → 0.28** as `nperseg` goes 128 → 256 → 512.

⇒ **ANSWER TO THE SECOND HALF OF Q1: the instrument does NOT lift the 10–14 Hz coherence.** That is a
result, pre-registered as such.

---

## 4. But 10–14 Hz IS identifiable — by window length, not by instrument

### 4.1 The coherence scan

`coh(rate,bar)` / `coh(cmd,rate)`, pooled r39 + r6c:

| stratum | nperseg | secs | nwin | 7.3 | 10.0 | 12.0 | 13.0 | 14.0 | 16.0 | 20.3 |
|---|---|---|---|---|---|---|---|---|---|---|
| creep 1–3 med | 128/512 | 187.8 | 240 | 0.88/0.34 | 0.41/0.30 | 0.45/0.24 | 0.35/0.28 | 0.44/0.39 | 0.67/0.40 | 0.93/0.54 |
| creep 1–3 med | 256/1024 | 165.3 | 94 | 0.87/0.41 | 0.39/0.39 | 0.60/0.25 | 0.45/0.24 | 0.52/0.36 | 0.69/0.39 | 0.93/0.58 |
| **creep 1–3 med** | **512/2048** | 123.3 | 31 | 0.86/0.51 | **0.45**/0.46 | **0.66**/0.28 | **0.43**/0.15 | **0.40**/0.41 | 0.74/0.48 | 0.93/0.60 |
| creep 1–6 med | 128/512 | 421.2 | 564 | 0.89/0.38 | 0.42/0.25 | 0.49/0.24 | 0.45/0.29 | 0.46/0.36 | 0.58/0.30 | 0.90/0.50 |
| **creep 1–6 med** | **512/2048** | 306.3 | 90 | 0.88/0.43 | **0.43**/0.33 | **0.58**/0.18 | **0.47**/0.22 | **0.40**/0.40 | 0.62/0.46 | 0.89/0.58 |
| loaded any | 128/512 | 144.1 | 177 | 0.89/0.29 | 0.31/0.23 | 0.43/0.10 | 0.58/0.17 | 0.65/0.22 | 0.77/0.18 | 0.96/0.35 |
| **loaded any** | **512/2048** | 82.1 | 15 | 0.92/0.35 | 0.33/0.21 | 0.37/0.01 | **0.70**/0.29 | **0.74**/0.21 | 0.82/0.12 | 0.97/0.25 |
| all engaged | 128/512 | 4016.3 | 6244 | 0.85/0.27 | 0.58/0.17 | 0.53/0.14 | 0.52/0.17 | 0.50/0.18 | 0.35/0.17 | 0.79/0.51 |

**Two things this shows.** (1) A **bigger pool does not lift the coherence** — `all_eng` has 4016 s and
6244 windows and reads 0.50–0.58 across 10–14 Hz, no better than creep's 240 windows. Coherence is a
property of the signals, not of the sample size. (2) A **longer window does**, in creep: 12 Hz goes
0.45 → 0.60 → **0.66**. That is the signature of **frequency-resolution smearing across a fast-varying
transfer**, not of additive noise — which is exactly the band where `∠B` swings ~70° in 4 Hz.

### 4.2 `B(f)` re-measured at `nperseg` 512 — the values barely move

Creep 1–3 med, pooled, `|B|`Hv / ∠ / coh:

| f (Hz) | 128 (bof's) | 256 | **512** |
|---|---|---|---|
| 8.00 | 11.95 / −95° / 0.84 | 11.97 / −93° / 0.86 | 12.15 / −95° / 0.89 |
| **9.94** (C10's corner) | 12.40 / −138° / **0.44** | 11.76 / −144° / 0.43 | **11.95 / −156° / 0.48** |
| 10.00 | 12.31 / −141° / 0.41 | 11.55 / n/a / 0.39 | **11.70 / −158° / 0.45** |
| 11.00 | 11.53 / −146° / 0.40 | 11.07 / −146° / 0.41 | **11.63 / −145° / 0.50** |
| 12.00 | 11.36 / −171° / 0.45 | 11.56 / −173° / 0.60 | **12.24 / −173° / 0.66** |
| **12.85** (advB's peak) | 9.82 / n/a / 0.37 | 9.50 / −179° / 0.45 | **10.28 / −171° / 0.41** |
| 13.00 | 9.02 / n/a / 0.35 | 8.61 / +178° / 0.45 | **9.06 / −173° / 0.43** |
| **13.70** (singular-band edge) | 6.67 / +152° / 0.42 | 6.70 / +158° / 0.50 | **6.76 / +152° / 0.42** |
| 14.00 | 6.32 / +149° / 0.44 | 6.26 / +154° / 0.52 | **6.40 / +147° / 0.40** |
| 16.00 | 4.12 / +131° / 0.67 | 4.08 / +134° / 0.69 | 3.91 / +127° / 0.74 |
| 20.30 | 2.83 / +120° / 0.93 | 2.78 / +119° / 0.93 | 2.69 / +114° / 0.93 |

The loaded stratum reaches the gate at the top of the band even at bof's own window length:
`loaded_any` at 128 reads **coh 0.55 / 0.58 / 0.63 / 0.65** at 12.85 / 13.0 / 13.7 / 14.0 Hz, rising to
**0.65 / 0.70 / 0.74 / 0.74** at 512, with `|B|` moving only 7.02 → 6.59 and ∠ +151° → +152° at 12.85 Hz.

⭐ **The headline: at `nperseg` 512 every frequency in 9.94–14 Hz clears coherence 0.40 on the pooled
creep data, and `|B|` and `∠B` move by at most 8 % in magnitude and 18° in phase from the
1.28 s values — the 18° is confined to 9.94–10 Hz; over 11–14 Hz the phase moves by ≤ 2°.** So advB's
unblocking measurement is available — **and it does not change the numbers**. It converts them from a
fit into a measurement, which removes the *"scored on a fit, not a measurement"* objection but leaves the
de-embed arithmetic where it was.

🛑 **A specific correction:** `ADV-V291-B-LOOP` §4.2 states *"C10's own corner, 9.94 Hz, reads coherence
0.299 creep / 0.249 loaded — below bof's own COH_MIN of 0.40."* Measured directly at 9.94 Hz on the creep
pool, `coh(rate,bar)` = **0.44 (nperseg 128) / 0.43 (256) / 0.48 (512)** — above the gate at every window
length. For reference, `r24_lane.coherence(9.94)` (a linear interpolation of the table's coherence column)
returns **0.427 creep / 0.297 loaded**, so the loaded half of advB's claim is close to that interpolant and
the creep half is not. **The corner is identified in creep; it is not in loaded.** [EVIDENCE — direct
band-averaged coherence at 9.94 Hz, `_scratch/b_iv_kappa_p4.txt` §7.]

### 4.3 The honest caveat on 12 Hz — it is route-dependent

Per-route at `nperseg` 512 (`|B|`Hv @ ∠, coh):

| stratum | route | 10 Hz | 12 Hz | 13 Hz | 14 Hz | windows |
|---|---|---|---|---|---|---|
| creep 1–3 med | r39 | 11.30 @ −158°, 0.52 | **12.81 @ −172°, 0.80** | 8.67 @ −168°, 0.56 | 6.31 @ +164°, 0.63 | 7 |
| creep 1–3 med | r6c | 12.34 @ −157°, 0.36 | 9.63 @ −177°, **0.17** | 9.83 @ +174°, 0.26 | 6.53 @ +111°, 0.33 | 24 |
| creep 1–6 med | r39 | 12.00 @ −150°, 0.54 | 12.50 @ −168°, 0.75 | 9.06 @ −171°, 0.54 | 7.17 @ +161°, 0.52 | 17 |
| creep 1–6 med | r6c | 12.66 @ −139°, 0.34 | 11.04 @ −154°, **0.37** | 9.17 @ +175°, 0.42 | 7.05 @ +141°, 0.34 | 73 |

**The pooled 12 Hz identification is carried by r39.** r6c alone does not clear the gate there, though it
returns a consistent magnitude (11.04 vs 12.50) and a phase within 14°. ⚠ **Do not quote "12 Hz is
identified" without this line.** The 13–14 Hz identification in the loaded stratum is the more robust one.

---

## 5. Q2 — the ±3 deadband does not explain the 0.45 factor

### 5.1 The premise is factually wrong: the deadband is ALREADY in the replay

`ADV-V291-B-LOOP` §3.1: *"If that is the cause, `GAIN_EFFECTIVE` is an artifact of not modelling the
deadband."* It was modelled. bof's ladder is `R24 = {gn: r24_series(bar, gn)}`
(grep `R24 = {t: {gn: r24_series` in `bof_v282.py`), and `r24_series` in `v282_r24_tap_read.py` is

```python
s = np.trunc(d * gain / 1024.0)
s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s) * 3)     # <-- the deadband, at EVERY rung
```

I re-derived the lane with the threshold exposed and asserted the identity:
**`max|deadband_lane(db=3) − r24_series| = 0.000e+00` over 95,275 frames.** [EVIDENCE — source read plus
numerical identity.] **advB's mechanism double-counts a term that is on both sides of the comparison.**

**And the direction is backwards.** Modelling the deadband *raises* the implied arm — because the
deadband bites harder at the smaller candidate arms. Median implied arm over 16 cells: **2137 with no
deadband → 2399 with the deadband**. In log terms the deadband closes `ln(2399/2137) / ln(5244/2137)` =
**12.9 %** of the gap, leaving 87.1 % unexplained. Against the number bof actually reported (2353, which
already carried the deadband) it closes **0 %**.

### 5.2 The amplitude the mechanism needs is not there

advB needs post-gain `v ≈ 5.44` counts for `(v−3)/v = 0.449`. Measured `v = |d·5244/1024|` on the
100 Hz frame axis:

| route | stratum | secs | p50 \|v\| | p75 | p90 | mean | **P(\|v\| ≤ 3)** | median \|T\| |
|---|---|---|---|---|---|---|---|---|
| r39 | creep 1–3 med | 63.7 | **43** | 100 | 177 | 71.0 | 0.107 | 169 |
| r39 | loaded idx≥68 med | 46.0 | **122** | 257 | 414 | 175.5 | 0.024 | 707 |
| r39 | highway | 237.9 | 45 | 94 | 161 | 69.5 | 0.065 | 136 |
| r39 | all engaged | 879.8 | 43 | 98 | 184 | 76.0 | 0.074 | 144 |
| r6c | creep 1–3 med | 146.1 | **28** | 68 | 127 | 50.6 | 0.141 | 130 |
| r6c | loaded idx≥68 med | 54.3 | **138** | 283 | 442 | 192.7 | 0.016 | 782 |
| r6c | highway | 2057.5 | 49 | 92 | 145 | 66.5 | 0.050 | 56 |
| r6c | all engaged | 3136.4 | 42 | 88 | 148 | 65.3 | 0.070 | 73 |

**The median `v` is 26–138 counts, 5–25× the 5.44 the mechanism requires.** At those medians
`(v−3)/v` = **0.89–0.98**, so the deadband can account for **2–11 %** of the 0.449 factor, not 100 %.

### 5.3 Solve for the threshold that WOULD explain it

Four single-parameter explanations, each inverted onto the same measured bit-6 duty on the same frames
(the inversion method is bof's — replay the lane on each route's own bar data at each rung and interpolate
the measured duty onto the ladder):

| route | stratum | measured b6 | (a) arm, db 3 | (b) arm, db 0 | **(c) deadband θ, arm 5244** | (d) post-scale, arm 5244 | (e) \|T\| scale | pred @5244 |
|---|---|---|---|---|---|---|---|---|
| r39 | creep 1–3 | 0.0906 | 2347 | 2048 | **55.5** | 0.408 | 2.45 | 0.1957 |
| r39 | creep 1–3 med | 0.0937 | 2325 | 2044 | **58.6** | 0.407 | 2.46 | 0.2020 |
| r39 | creep 1–6 | 0.0879 | 2359 | 2109 | **60.2** | 0.418 | 2.39 | 0.1899 |
| r39 | loaded idx≥68 | 0.0703 | 2747 | 2652 | **112.9** | 0.516 | 1.94 | 0.1388 |
| r39 | loaded idx≥68 med | 0.0630 | 2735 | 2643 | **116.5** | 0.513 | 1.95 | 0.1251 |
| r39 | loaded any | 0.0503 | 2646 | 2538 | **124.2** | 0.493 | 2.03 | 0.1066 |
| r39 | highway | 0.1321 | 2451 | 2196 | **52.8** | 0.437 | 2.29 | 0.2471 |
| r39 | all engaged | 0.1141 | 2438 | 2164 | **52.5** | 0.431 | 2.32 | 0.2203 |
| r6c | creep 1–3 | 0.0762 | 2279 | 1912 | **44.1** | 0.389 | 2.57 | 0.1621 |
| r6c | creep 1–3 med | 0.0774 | 2290 | 1933 | **45.0** | 0.393 | 2.55 | 0.1650 |
| r6c | creep 1–6 | 0.0765 | 2326 | 1935 | **43.5** | 0.394 | 2.53 | 0.1625 |
| r6c | loaded idx≥68 | 0.0455 | 2692 | 2631 | **127.0** | 0.515 | 1.94 | 0.0965 |
| r6c | loaded idx≥68 med | 0.0414 | 2639 | 2582 | **135.4** | 0.507 | 1.97 | 0.0906 |
| r6c | loaded any | 0.0342 | 2727 | 2675 | **130.0** | 0.522 | 1.92 | 0.0773 |
| r6c | highway | 0.2494 | 2268 | 2002 | **44.5** | 0.398 | 2.51 | 0.4388 |
| r6c | all engaged | 0.1918 | 2284 | 2005 | **44.9** | 0.400 | 2.50 | 0.3463 |

🛑 **The deadband threshold that would reproduce the measured duty at the flown arm is 43.5–135.4 —
15 to 45× the cal cell `0xC61F6` = 3, read from the V282 image.** [EVIDENCE.]

### 5.4 The invariance test — the mechanism is a constant scale, not a deadband

A constant scale must be stratum-invariant; a deadband's effect depends on the lane amplitude, which
varies across strata by a factor of 5. **The raw duty moves 7.3× (0.0342 → 0.2494) across the 16 cells.**

| parameterisation | min | median | max | **max/min** | sd ln | compression of the 7.3× duty range |
|---|---|---|---|---|---|---|
| **(a) arm, deadband 3** | 2268 | 2399 | 2747 | **×1.21** | **0.073** | **×6.0** |
| (b) arm, deadband 0 | 1912 | 2137 | 2675 | ×1.40 | 0.128 | ×5.2 |
| **(c) deadband threshold** | 43.5 | 57.1 | 135.4 | **×3.12** | **0.454** | ×2.3 |
| (d) post-deadband scale | 0.389 | 0.424 | 0.522 | ×1.34 | 0.115 | ×5.4 |
| (e) \|T\| scale | 1.92 | 2.36 | 2.57 | ×1.34 | 0.114 | ×5.4 |

- **The deadband is 4–6× LESS invariant than every alternative** (sd ln 0.454 against 0.073–0.128),
  exactly as its amplitude dependence predicts. **Falsified by its own signature.**
- ⭐ **The single most invariant parameterisation is a scale applied BEFORE the deadband** — the arm
  itself (sd ln 0.073), ahead of a post-deadband output scale (0.115) and a `|T|` scale (0.114). That is
  a modest but real discrimination in favour of *"the lane's effective gain"* over *"the output is scaled"*
  or *"the reference is mis-scaled"*.
- ⭐ **An internal consistency check that came out right:** modelling the deadband **halves the residual
  stratum drift**, from ×1.40 (b, no deadband) to ×1.21 (a). So the deadband *is* in the lane and *is*
  correctly sized at 3 — it absorbs part of the creep-vs-loaded difference. What remains is not it.

### 5.5 The two remaining escapes from the effective arm, both closed

**(e) "the 427 tap under-reads `|T|` by ~2.36×."** The V278r3 build's own packer, carried unchanged into
V282, is

```
wire = (sign(T) << 9) | (|T| >> 3)          T = gp-0x6b38, the delivered lane torque
Decode T = (-1 if bit9 else 1) * ((w & 0x1ff) << 3)
```
and `creep20_loop_id.load` decodes `sign × (fld & 511) × 8`. **Encoder and decoder are exact inverses.**
The only error is the `>>3` truncation, worth ≈ 3 % at the measured median `|T|`, and it makes the
*predicted* duty **higher**, i.e. it widens the gap rather than explaining it. The comparator also reads
the **same cell** the tap logs (`bit6 = |gp-0x6ada| ≥ |gp-0x6b38|`, `PREREG-V282-READ.md`), so there is no
second scale between them. **[EVIDENCE — build script §[C] plus the cache decode.] Branch (e) is closed.**

**A hypothesis I raised and then falsified myself.** The implied arm 2268–2747 lands inside the lane's own
alternative rungs — Honda's fixed **2048** (`0xC6440`) and the mode-10 LERP surface
(`BUILD-LINEAGE-PART1`: *"5244 = 2.00 × 2622, the LERP at grind #1's point"*) — and the stratum ordering
matched the LERP's rectified-column-rate axis (lowest at creep 2279–2359, highest loaded 2639–2747). **If
the 5244 rung were not selected, V291's cut would be INERT, not merely small, and B2's pass — which advB
says is bought entirely by the r24 cut — would be void.** I read the selector gate from the V282 image:

```
0x3AA96 = 0xFB     -> repointed to STEER_CONTROL_ACTIVE since V104: the 5244 rung IS taken while
                      laterally engaged.   (0xC5 = Honda gateless, where gp-0x683c has zero writers
                      image-wide and the 5244 load never executes -- BUILD-LINEAGE-PART1, 0xC6444 cell)
0xC6440 = 2048     0xC6442 = 1024     0xC6446 = 5244     0xC61F6 = 3
```
Every stratum here is gated on `eng` (0x18F SCA ∧ 0xE4 STEER_REQUEST). **My hypothesis is FALSIFIED, and
I report it because the failed branch is part of the answer.** [EVIDENCE — byte read from
`_v282_…_plain_image.bin`.]

### 5.6 The directions that do not work, checked

Three modelling artefacts could in principle produce a duty mismatch. All three push the **wrong way**:

| artefact | effect on the predicted duty | direction needed |
|---|---|---|
| `T100` is a linear interpolation of a 50 Hz stream — interpolation cannot create extremes, so it removes `\|T\|`'s deep dips | **LOWER** predicted duty | predicted is already too HIGH |
| the mirror's `resample_poly` reconstructs the bar only to 50 Hz, while the real 1 kHz lane sees content above it, and `\|D4(f)\|` rises with f | **LOWER** predicted `\|r24\|` | needs LOWER measured, not lower predicted |
| the `sar` floor vs `np.trunc` (V850 floors; the mirror truncates toward zero) | ±1 count on `\|s\|` ~ 26–138 | negligible |

⇒ **the observed direction — predicted 0.196 against measured 0.091 on r39 creep — is not produced by
any of them.**

---

## 6. Q2 — the answer, with the number

**The post-gain deadband explains 12.9 % of the log-gap** (×1.12 of the needed ×2.19), and **0 %** of the
gap as bof actually reported it, because bof had already modelled it. **The residual is ×1.95, and it
behaves as a constant multiplicative scale applied before the deadband.**

**Is that residual incremental?** Yes. Only a static **offset** is non-incremental, and that is the
deadband — whose own incremental contribution I measured directly. For a small perturbation riding on a
large broadband signal, a symmetric deadband's incremental (dual-input describing-function) gain is
`P(|s| > 3)`, measured on the **1 kHz** lane state, not the 100 Hz decimation:

| route | stratum | **P(\|s\| > 3) @5244** | @4725 | sinusoidal N(A) at the 18–22 Hz ring | at A = p50\|s\| | d ln gain / d ln arm |
|---|---|---|---|---|---|---|
| r39 | creep 1–3 med | 0.8885 | 0.8814 | 0.9449 | 0.9170 | 1.082 |
| r39 | loaded idx≥68 med | 0.9776 | 0.9755 | 0.9709 | 0.9692 | 1.029 |
| r39 | highway | 0.9320 | 0.9256 | 0.8930 | 0.9170 | 1.066 |
| r39 | all engaged | 0.9220 | 0.9153 | 0.9376 | 0.9152 | 1.070 |
| r6c | creep 1–3 med | 0.8507 | 0.8413 | 0.9301 | 0.8770 | 1.110 |
| r6c | loaded idx≥68 med | 0.9814 | 0.9793 | 0.9756 | 0.9727 | 1.019 |
| r6c | highway | 0.9476 | 0.9422 | 0.8324 | 0.9221 | 1.051 |
| r6c | all engaged | 0.9255 | 0.9190 | 0.9100 | 0.9112 | 1.065 |

**The deadband costs the lane's incremental transfer only ×0.85–0.98.** ⚠ This corrects
`TRACE-2026-09-13-r24-lane-transfer.md` §8.5, which puts the describing function at **0.4–0.8×** on an
assumed ring amplitude of 10–30 counts; the measured post-gain amplitude is 26–138 and the measured
describing function is **0.83–0.98**.

### 6.1 The verdict

> **EFFECTIVE.** The admissible incremental arm for the de-embed is **κ = 0.449, arm ≈ 2354**, not FLOWN
> 5244 and not something in between. The deadband is not the mechanism, the tap scale is not the
> mechanism, and the rung is selected. Whatever the residual ×1.95 physically is, it multiplies the
> product `(gain/1024)·D4·B`, and **the loop only ever sees that product** — so it belongs in `Λ`.

**What this does to advB's B3**, restating advB's own numbers rather than re-deriving them: the EFFECTIVE
row is the one that reads **`Ms` 12–26 reduced ×4.42 (PASS)**; the FLOWN rows read ×1.44–1.82 (FAIL).
⚠ **This does NOT clear B3 on its own**, and I am explicit about that: advB also records that the
EFFECTIVE arm's de-embed is near-singular (`min|1+Gc·Λ|` = 0.0039) at 12.0–13.7 Hz on 106 of 121 fits.
§4 says the measured `B` in that band **barely moves** when it becomes identified, so identifying it does
not un-condition the de-embed. **Q2 selects the arm; it does not repair the conditioning.**

### 6.2 The V291 cut itself

```
k_nominal = 4725 / 5244                                 = 0.901030
k_eff     = k_nominal * P(|s4725|>3) / P(|s5244|>3)
P ratio over the 8 cells: 0.9889 .. 0.9979  (median 0.9930)
k_eff                   : 0.8910 .. 0.8991  (median 0.8948)
```
**The deadband makes the −9.90 % cut into a −10.52 % cut** (median). That is 0.6 percentage points
deeper than the build assumes — in the *safe* direction for the 7.3 Hz gate (`gate_k` passes at 4725 with
a margin of 1.4e-4 and fails at 4726), and against the build on B3, where a deeper r24 cut costs more
20 Hz damping. It does not move either verdict on its own.

---

## 7. The headline, re-derived by a second method

### 7.1 The comparator moved to 1 kHz — κ does not move

The ECU compares `|r24| ≥ |T|` at **1 kHz**. bof's inversion and my §5.3 both decimate `r24` to the
100 Hz frame axis and interpolate `|T|` from its 50 Hz stream. If the 0.45 factor were a sampling
artefact, the implied arm would move when the comparison is re-run at 1 kHz against the same measured
duty. Same lane arithmetic, same strata, same measured `bit6`:

| route | stratum | measured b6 | arm @100 Hz | **arm @1 kHz** | ratio | pred@5244 100 Hz | pred@5244 1 kHz |
|---|---|---|---|---|---|---|---|
| r39 | creep 1–3 med | 0.0937 | 2325 | **2312** | 0.994 | 0.2020 | 0.1989 |
| r39 | creep 1–6 med | 0.0885 | 2343 | **2326** | 0.993 | 0.1901 | 0.1884 |
| r39 | loaded idx≥68 med | 0.0630 | 2735 | **2695** | 0.985 | 0.1251 | 0.1261 |
| r39 | loaded any | 0.0503 | 2646 | **2617** | 0.989 | 0.1066 | 0.1068 |
| r39 | highway | 0.1321 | 2451 | **2453** | 1.001 | 0.2471 | 0.2483 |
| r39 | all engaged | 0.1141 | 2438 | **2434** | 0.998 | 0.2203 | 0.2205 |
| r6c | creep 1–3 med | 0.0774 | 2290 | **2274** | 0.993 | 0.1650 | 0.1653 |
| r6c | creep 1–6 med | 0.0777 | 2328 | **2320** | 0.996 | 0.1640 | 0.1642 |
| r6c | loaded idx≥68 med | 0.0414 | 2639 | **2605** | 0.987 | 0.0906 | 0.0925 |
| r6c | loaded any | 0.0342 | 2727 | **2673** | 0.980 | 0.0773 | 0.0787 |
| r6c | highway | 0.2494 | 2268 | **2288** | 1.009 | 0.4388 | 0.4357 |
| r6c | all engaged | 0.1918 | 2284 | **2300** | 1.007 | 0.3463 | 0.3442 |

```
100 Hz comparator : implied arm  2268 .. 2390 (med) .. 2735    max/min 1.21
1 kHz  comparator : implied arm  2274 .. 2380 (med) .. 2695    max/min 1.18
kappa @100 Hz = 0.4558      kappa @1 kHz = 0.4539      they differ by 0.4 %
```

⭐ **κ is 0.454–0.456 on both axes. The factor is not a sampling artefact.** [EVIDENCE.]

### 7.2 The deadband's contribution, re-derived analytically — no ladder, no inversion

Straight from the measured 1 kHz distribution of `v = |trunc(d·5244/1024)|`, the deadband's
multiplicative effect on the lane's delivered magnitude is `P(|v|>3) · E[(v−3)/v | v>3]`:

| route | stratum | P(\|v\|>3) | E[(v−3)/v \| v>3] | **product** | advB needs |
|---|---|---|---|---|---|
| r39 | creep 1–3 med | 0.8885 | 0.8785 | **0.7806** | 0.449 |
| r39 | loaded idx≥68 med | 0.9776 | 0.9416 | **0.9205** | 0.449 |
| r39 | all engaged | 0.9220 | 0.8809 | **0.8122** | 0.449 |
| r6c | creep 1–3 med | 0.8507 | 0.8501 | **0.7232** | 0.449 |
| r6c | loaded idx≥68 med | 0.9814 | 0.9470 | **0.9294** | 0.449 |
| r6c | all engaged | 0.9255 | 0.8792 | **0.8137** | 0.449 |

**The deadband's own multiplicative effect is 0.72–0.93. advB's mechanism needs the whole 0.449 from
this column.** This reaches the same verdict as §5 with no ladder, no inversion and no model of `|T|` —
it uses only the lane's own arithmetic and the measured bar. **Two methods, one answer.**

---

## 8. What I did NOT verify

1. **What the residual ×1.95 physically is.** I closed the deadband, the tap scale and the arm-selector
   branches and showed it behaves as a constant pre-deadband scale, but I have not identified the
   mechanism. ⭐ **The one measurement that would:** a *frequency-resolved* κ. If the residual were, say,
   sensor conditioning upstream of `gp-0x4f62` that the 0x18F wire torque does not show, κ would be
   frequency-dependent rather than constant. The strata available here cannot separate that — the bar's
   power peaks at 7.3 Hz in **both** creep (0.0499) and loaded (0.0806), so the two strata do not contrast
   the lane's input spectrum enough to have power against that hypothesis. A band-limited replay against a
   band-limited comparator rung would.
2. **The r6c → V282 attribution.** Taken from `ROUTE-6C-ATTRIBUTION-2026-09-13.md` as bof did; not
   re-derived. Every Q2 number is reported per route, so r39 alone carries the same conclusion.
3. **Instrument exogeneity in the strict sense.** I measured the echo share (`coh(rate,cmd)`) and the
   command's power, and those are enough to say the instrument is *weak*; I did not attempt to prove cmd
   is uncorrelated with the bar-side disturbance. At 20.3 Hz the echo carries 35–54 % of the command, so
   the IV there is partly degenerate and its agreement with the direct estimate is weaker evidence than
   the coherence alone implies.
4. **The cmd → rate / rate → cmd group delays** in `_scratch/b_iv_kappa.txt` §2 are printed as a
   causality hint and are **not load-bearing**: the two columns are algebraically ±the same number, so
   they cannot distinguish direction on their own. I did not build a proper lead/lag test and no
   conclusion here rests on them.
5. **The bootstrap CIs at `nperseg` 512.** The long-window re-measurement is reported per route (§4.3)
   rather than with a bootstrap; with 7–31 windows a block bootstrap would not have been informative.
6. **`0xC61F6`'s and `0xC6446`'s values were read from the V282 image, not from the built V291 image.**
   Every number here is a V282 measurement; I did not open the V291 build.
7. **advB's loop arithmetic.** I did not re-derive `Ms`, the de-embed, or any of the 121 fits. §6.1
   restates advB's own numbers for the two arms and says which arm the wire selects — the loop
   consequences are advB's and the orchestrator's to adjudicate.
8. **A failed control, reported:** my §3.4 attempt to check the tap scale by comparing the measured
   `|T|/|rate|` transfer against `r24_lane.servo(f)` **does not work and I discarded it.** It reads
   ×0.62–0.68 in magnitude and 35° off in phase — but `T/rate` measured in closed loop is *not* the servo
   arm, because `T` also carries the `cmd` feedforward, so the ratio is contaminated by exactly the
   closed-loop correlation Q1 is about. The table is left in the output marked as such. The tap scale is
   closed by the encoder/decoder identity in §5.5 instead, which needs no transfer estimate at all.
