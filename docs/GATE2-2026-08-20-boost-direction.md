# GATE 2 — the `gp-0x6b86` BOOST direction: 21.7 Hz sign, the knife edge, the added pole, and `|κG|`

**2026-08-20/21 · subagent · analysis only. Nothing built, flashed or sent on CAN.**
Extends `docs/GATE2-2026-08-20-notch-sign.md`, which killed the *notch*. This file examines the
opposite direction — the **boost** — and the co-benefit it was claimed to have at 21.7 Hz.

---

## 0. VERDICT, up front

| # | question | verdict | grade |
|---|---|---|---|
| 1 | Does the design's **−15 dB at 21.7 Hz** help grind #1? | 🛑 **NO. Neutral-to-harmful.** It raises the measured 21.0–22.5 Hz aggregator loop gain **+8 % to +20 %**, and its damping benefit is **30× smaller** than at 8 Hz with only **5.1–7.0°** of phase margin before the sign flips. | **EVIDENCE** |
| 2 | Is ×1.42 safely inside the knife edge? | The **idealised** boost has its optimum at ×1.49 and its knife edge at ×1.98 — ×1.42 would sit comfortably inside. **But the REALISABLE biquad is not an idealised boost**; see 3. | EVIDENCE |
| 3 | Is the added pole a new resonance? | 🛑 **WORSE THAN THAT. The realisable filter REVERSES the sign of the amplitude criterion.** `|u|` at 6–9 Hz goes to **3.34×**, not 0.44×, and the identified loop is driven **past the −1 point**. | **EVIDENCE** for the transfer arithmetic; **BELIEF** (well-supported) for the closed-loop consequence |
| 4 | Can `|κG|` be bounded from existing data? | ✅ **YES — and it is bounded, for the first time.** `|κG|` at 6–9 Hz = **0.63 [0.51, 1.00]**, `|A| = |1+κG|` = **0.44 [0.11, 0.66]** ⇒ the closed loop **amplifies** the driver-felt impedance **2.3× [1.5, 9×]**. Replicated **within-drive** on two independent routes. | **EVIDENCE** |
| 5 | Recommendation | 🛑 **DO NOT BUILD THE BOOST.** No `(f0, r, f_zero)` passes all four gates. | — |

🛑 **THE BOOST IS ALSO DEAD — but for a completely different reason from the notch.**
The notch died because its **sign** was backwards. The boost's sign is **right** — and it is still dead,
because **the filter structure cannot deliver the sign it needs.**

> **A 2-pole resonance has exactly −90° of phase at its own pole frequency** (`H(jw0) = 1/(2*zeta)` at
> `−90°`). To boost 8 Hz you must put poles at 8 Hz, and that necessarily rotates the lane by ~−70°.
> The favourable perturbation is a **pure magnitude** change with **zero phase rotation**. The biquad
> cannot produce one at its own centre frequency. **This is structural, not a tuning problem.**

---

## 1. Method and positive control

Frozen, identical to the notch analysis (`GATE2-…-notch-sign.md` §2): 4 s Hann windows
(`nperseg = 405` at `fs = 101.1479 Hz`), 50 % overlap, linear detrend, Welch-summed **inside engaged
episodes only** (`cc_lat`); band estimate `H = Sum_band S_xy / Sum_band S_xx`; **CI = bootstrap over
EPISODES**. `Z = S_wT/S_ww` with `w = rate_f × π/180` (rad/s) and `T = tq` (counts).

**POSITIVE CONTROL — independent re-implementation, run before any new measurement:**

| quantity | prior analysis | this analysis |
|---|---|---|
| r9e lane/T, 6–9 Hz | 0.2068 ∠ +39.5° | **0.2068 ∠ +39.5°** ✓ |
| r95 sum/T, 6–9 Hz | 0.0572 ∠ +13.6° | **0.0572 ∠ +13.7°** ✓ |
| r85 sum/T, 6–9 Hz | 0.0485 ∠ +17.0° | 0.0481 ∠ +17.5° ✓ |
| `Z` 6–9 Hz | −3762 − j5752, 6873 ∠ −123.2° | **−3761 − j5752, 6873 ∠ −123.2°** ✓ |
| `Z` 15–22 Hz | −440 + j1307 | **−440 + j1307** ✓ |
| `Z` 22–26 Hz | −138 + j1160 | **−138 + j1160** ✓ |
| Honda biquad @ 6/7.79/9 Hz | −0.088 / −0.149 / −0.201 dB | **identical** ✓ |
| design bytes `f0=8.05, r=0.980, zero@300` | `258ffabf c6dc753f 7a371e3f e184913a` | **identical** ✓ |

⚠ **7 (r9e) / 8 (r96) / 3 (r95) / 2 (r85) episodes is the hard limit on every CI in this document.**
r85's 2 episodes are 231.0 s and 15.4 s — badly unbalanced; it is the dominant source of uncertainty
in §3 and its leave-one-out swing is large.

Scripts: `analysis-2020accord/_gate2_boost_lib.py` (frozen method) plus `_g2b_pc.py` (positive
control), `_g2b_band217.py`, `_g2b_design.py`, `_g2b_verdict217.py`, `_g2b_kappa.py`,
`_g2b_kappa_robust.py`, `_g2b_boostcurve.py`, `_g2b_sweep2d.py`, `_g2b_final.py`, `_g2b_within.py`.

---

## 2. 🛑 THE 21.7 Hz SIGN VERDICT — the −15 dB does NOT help grind #1

### 2.1 `Z` at 21.0–22.5 Hz — replicated on all four builds

| route | build | `Re(Z)` [CI] | `Im(Z)` | `\|Z\|` | `arg(Z)` [CI] | coh² |
|---|---|---|---|---|---|---|
| r85 | V100 4× | −353 [−542, −343] | +1155 | 1208 | **+107.02** [+106.53, +114.84] | 0.766 |
| r95 | V101 8× | −407 [−441, −374] | +1251 | 1315 | **+108.04** [+106.64, +110.24] | 0.981 |
| r96 | V102 6× | −354 [−381, −325] | +1207 | 1258 | **+106.35** [+105.67, +107.32] | 0.976 |
| r9e | V103 6× | −349 [−383, −321] | +1211 | 1260 | **+106.10** [+104.44, +107.57] | 0.983 |

**`Re(Z) < 0` at 21–22.5 Hz on every build, CI excluding zero** — there *is* anti-damping there, but it
is **≈11× weaker** than the 6–9 Hz term (−349 vs −3761), and `Z` is **reactive-dominated** (`arg` ≈ +107°).

### 2.2 The perturbation, and why its sign is `a`-invariant

```
D(u/T)  =  dG(f)  =  (H_new(f) - H_honda(f)) * ( gp-0x6b82 / T )
                  =  (H_new(f) - H_honda(f)) * ( -a )        # a > 0, real (LERP slope)
```
`a` is a **positive real scalar**, so it **cannot change the sign** of `Re(dG·Z)` — only its size.
**The 21.7 Hz sign verdict is therefore immune to the unknown `a`.**

At 21.73 Hz: `H_honda = 0.85565 ∠ −31.17°`, `H_new = 0.17752 ∠ −160.64°` (−13.66 dB **relative to
Honda**, −15.02 dB relative to DC), `dH = 0.97813 ∠ +156.88°`, ⇒ **`arg(dG) = −23.12°`**.

### 2.3 Criterion A — damping. Favourable, but **negligible and 5–7° from flipping**

`Re(dG·Z) > 0` iff `arg(dG) + arg(Z)` lies in `(−90°, +90°)`. With `arg(dG) = −23.12°` the sign
**flips to harmful when `arg(Z) > +113.12°`.**

| route | `arg(Z)` | margin to flip | P(flip) over the episode bootstrap |
|---|---|---|---|
| r85 | +107.02° | **+6.10°** | **0.255** |
| r95 | +108.04° | +5.07° | 0.000 |
| r96 | +106.35° | +6.77° | 0.000 |
| r9e | +106.10° | +7.02° | 0.000 |

Magnitude, at `a = 0.098`:

| band | r85 | r95 | r96 | r9e |
|---|---|---|---|---|
| **8.00 Hz** | +477.6 [+439,+502] | +274.1 [+226,+297] | +304.3 [+203,+346] | +437.0 [+376,+485] |
| **21.73 Hz** | **+12.3 [−4,+13]** | +11.1 [+6,+14] | +14.2 [+12,+16] | +14.8 [+12,+19] |

🛑 **The 21.7 Hz damping benefit is ~30× smaller than the 8 Hz one, and on r85 the CI includes zero.**
It is not a co-benefit; it is noise on the ledger.

### 2.4 Criterion B — amplitude. **The attenuation makes 21.7 Hz WORSE**

`u/T` measured at 21.0–22.5 Hz: **r85 `0.2703 ∠ −109.8°`** (coh² 0.465), **r95 `0.2610 ∠ −89.3°`**
(coh² 0.648). `dG` sits at **−23.12°** — i.e. **67°–77° away from `u`, near quadrature. A
near-orthogonal perturbation can only INCREASE a magnitude.**

| `a` | r85 ratio [CI] | r95 ratio [CI] |
|---|---|---|
| 0.050 | 1.026 [1.022, 1.065] | 1.089 [1.078, 1.113] |
| **0.098** | **1.080 [1.073, 1.138]** | **1.196 [1.174, 1.242]** |
| 0.117 | 1.108 [1.100, 1.170] | 1.243 [1.216, 1.297] |
| 0.300 | 1.518 [1.509, 1.523] | 1.781 [1.718, 1.903] |
| 0.644 | 2.589 [2.314, 2.592] | 2.962 [2.844, 3.183] |

**Monotone increasing in `a`, CI excludes 1.0 at every `a` on both routes.** For the attenuation to
*reduce* `|u|` you would need `arg(dG) ≈ +80°`; the design gives −23°, a **103° miss**.

### 2.5 The cancellation IS band-specific — confirmed

| band | sum | lane `gp-0x6b4c` | residual | `\|lane\|/\|sum\|` | lane↔residual angle |
|---|---|---|---|---|---|
| 6–9 Hz | 0.0526 ∠ +15.4° | 0.1969 ∠ +41.8° | 0.1515 ∠ −129.4° | **3.74** | **171.1°** (near anti-phase) |
| **21.0–22.5 Hz** | 0.2614 ∠ −99.7° | 0.4398 ∠ −153.2° | 0.3533 ∠ −9.7° | **1.68** | **143.5°** |

⚠ The 6–9 Hz lane inventory **does not close at 21.7 Hz**: after removing the structural `gp-0x6b86`
and `r24+r26` terms (the latter scaled by the 4-tick difference operator, `0.2697 ∠ +74.3°` at
21.73 Hz vs `0.1004 ∠ +84.2°` at 8 Hz), a **0.54 ∠ +21.6°** term is left unexplained. `gp-0x6b26`
(an **inertia** term, ∝ ω², 7.4× stronger at 21.7 than at 8 Hz) is the obvious candidate but is
untraced. **No 21.7 Hz decomposition is claimed here** — none is needed: §2.3 and §2.4 use only the
measured `u/T`, the measured `Z`, and the structurally exact `dG`.

**⇒ VERDICT 1: the −15 dB at 21.73 Hz is a COST LINE, not a co-benefit. The boost must be justified by
its 8 Hz behaviour alone.**

---

## 3. `|κG|` — IDENTIFIED, from the gain steps themselves

### 3.1 The identification

Model (sign conventions from `notch-sign.md` §1.6, `κ < 0`):
```
T = Z0*w - lambda*kappa*u ,  u = G*T    =>    Z = T/w = Z0 / (1 + c*G) ,   c = lambda*kappa
```
Two builds, **same plant `Z0`**, different `G`. With `rho = Z4/Z8`:
```
rho*(1 + c*G4) = 1 + c*G8       =>      c = (rho - 1) / (G8 - rho*G4)
```
**One complex equation, one complex unknown — exactly determined.** Route `0x85` (V100, 4×) and
`0x95` (V101, 8×) both pack `gp-0x6b94` = **the SUM**, so `G` is directly measured on both.

### 3.2 Result at 6–9 Hz

```
G4 = 0.0481 at +17.5 deg     Z4 = 6352 at -117.4 deg
G8 = 0.0572 at +13.7 deg     Z8 = 6918 at -134.2 deg
rho = 0.9183 at +16.8 deg    |rho-1| = 0.291   (WELL-POSED)

c  = lambda*kappa = 13.09 at +145.3 deg   [|c| CI 10.9-19.0 ; arg CI +124..+161 deg]
P4 = c*G4 = 0.630 at +162.8 deg           =>  |kG| = 0.630   [CI 0.512 - 1.001]
A4 = 1+P4 = 0.440 at  +25.0 deg           =>  1/|A| = 2.28x  [CI 1.51 - 9.4x]
P8 = 0.749 at +159.0 deg  ,  A8 = 0.404
Z0 = Z4*A4 = 2792 at -92.45 deg
```

**Three independent consistency checks the solve was free to fail:**

1. **`arg(c) = +145.3°` against a firmware prediction of `+180°`** (κ < 0, from the decompiled sign
   chain). The 34.7° discrepancy is exactly **12.8 ms of actuation lag at 7.5 Hz** — the right size for
   the EME shaper + integrator + FOC current loop. The identification knew nothing about κ's sign.
2. **`Z0 = 2792 ∠ −92.45°` — `Re(Z0)/|Z0| = −0.043`.** The identified passive plant came back as an
   almost **perfectly lossless spring**, which is what a torsion bar below its resonance must be.
   Implied stiffness ≈ 2296 counts/deg. **⇒ ALL of the measured `Re(Z) = −3761` is LOOP-GENERATED.**
3. **`|rho−1|` conditioning**: the solve is only well-posed where the gain step actually moved `Z`.
   6–9 Hz gives `|rho−1| = 0.291`; 15–22 Hz gives 0.144 and 21–22.5 Hz gives 0.083 (**ill-posed — the
   21.7 Hz row of the identification is NOT used anywhere in this document**).

### 3.3 Robustness

**Speed-matched** (windows binned by median `v_rear`; r85 median 11.0 m/s vs r95 8.7 m/s):

| band | wins 4×/8× | `\|P\|` | `arg P` | `\|A\|` | `1/\|A\|` | `arg c` |
|---|---|---|---|---|---|---|
| 0–5 m/s | 15/22 | 0.435 | −172.2° | 0.572 | 1.75 | **+173.0°** |
| 5–12 m/s | 49/29 | 0.759 | +159.9° | 0.388 | 2.57 | +142.7° |
| 12–20 m/s | 32/32 | 0.754 | +149.5° | 0.519 | 1.93 | +128.2° |
| 3–17 m/s | 83/60 | 0.585 | +156.5° | 0.519 | 1.93 | +137.2° |

**Leave-one-episode-out**: `|P|` 0.52–0.96, `|A|` 0.14–0.64, `arg c` +127° … +161°.
**`|A| < 1` in 100 % of the bootstrap, in every speed bin, and in every leave-one-out.**

**WITHIN-DRIVE replication (no cross-build assumption at all).** `a` varies with operating point, so
`G` varies with `|T|` inside one drive. Stratifying r85's own windows by `p75(|tq|)` and solving from
the well-posed pairs only (`|rho−1| > 0.4`):

| pair (ct bins) | `\|rho−1\|` | `c` | `\|P\|` | `arg P` | `\|1+P\|` |
|---|---|---|---|---|---|
| 700–1200 × >2000 | 0.572 | **13.82 ∠ +141.3°** | **0.634** | +165.4° | **0.418** |
| 0–300 × >2000 | 0.440 | 9.07 ∠ +152.3° | 0.528 | +173.8° | 0.479 |
| 300–700 × >2000 | 0.632 | 20.02 ∠ +161.0° | 0.862 | +171.3° | 0.197 |
| 1200–2000 × >2000 | 0.404 | 10.53 ∠ −179.1° | 0.600 | +191.2° | 0.428 |
| **cross-build reference** | 0.291 | **13.09 ∠ +145.3°** | **0.630** | +162.8° | **0.440** |

r95's own within-drive pairs give `|P|` 1.21–1.80 at `arg` +183…+204°, `arg c` **+166° … −171°** — even
closer to the firmware's +180°. Ill-posed pairs (`|rho−1| < 0.05`) return garbage, as they must.

🛑 **`|κG| ≈ 0.6` at 6–9 Hz with `arg(P) ≈ +165°` means the Nyquist locus passes within `|1+P| = 0.44`
of the −1 point, i.e. the assist loop AMPLIFIES the driver-felt impedance 2.3× at exactly the ratchet
frequency, and the gain margin is of order 1.2–1.6 (1.5–4 dB).** The 8 Hz mode is **not** a passive
mechanical resonance being excited — it is **the assist loop's own near-instability**, exactly as the
`|Z|` peak suggested. The question the previous analysis flagged as "the single most valuable open
question in the kit" is now answered, and the answer is the bad one.

---

## 4. GATE 2 on the boost — and why the realisable filter reverses the sign

### 4.1 The IDEALISED boost (what the previous analysis priced) — favourable

`dG = (B−1)·(−a·H_honda)`, i.e. a pure magnitude scale of the lane, **no phase rotation**:

| B | `\|dG\|` | `arg dG` | `Re(dG·Z)` | `\|u_new\|/\|u\|` | `\|dP\|` | `\|P_new\|` | `arg P_new` | `\|A_new\|` | `Re(Z_new)` |
|---|---|---|---|---|---|---|---|---|---|
| 1.00 | 0 | — | 0 | 1.000 | 0 | 0.630 | +162.8° | 0.440 | −2928 |
| 1.20 | 0.019 | +169.1° | +92 | 0.691 | 0.25 | 0.425 | +179.2° | 0.575 | −256 |
| **1.49** | 0.047 | +169.1° | +225 | **0.443** | 0.62 | 0.306 | +236.4° | **0.869** | **+812** |
| 1.80 | 0.077 | +169.1° | +368 | 0.720 | 1.01 | 0.544 | +281.0° | 1.226 | +904 |
| **1.98** | 0.094 | +169.1° | +451 | **1.000** ← knife edge | 1.23 | 0.744 | +290.6° | 1.441 | +862 |
| 2.50 | 0.144 | +169.1° | +690 | 1.900 | 1.89 | 1.369 | +301.8° | 2.077 | +705 |
| 4.00 | 0.289 | +169.1° | +1380 | 4.614 | 3.78 | 3.239 | +309.1° | 3.946 | +427 |

- **optimum `B* = 1.490×`** (`|u|` → 0.443×, `|A|` 0.440 → 0.869, `1/|A|` 2.28 → 1.15, `Re(Z)` −3761 → +812)
- **knife edge `B = 1.980×`** (`|u|` back to baseline) — ⚠ **not ×3 as the brief carried forward**
- ⇒ ×1.42 would sit at **72 % of the way to the optimum and 43 % of the way to the edge**. Fine — *if it
  were realisable.*

### 4.2 The REALISABLE biquad — the sign REVERSES

Because a 2-pole section contributes ~−90° at its own centre, `arg(H_new)` at 8 Hz is **−77.8°**, not
Honda's **−10.9°**. The **vector** change is therefore `|dH| = 1.378` — **larger than `|H|` itself** —
and since the lane contributes `|a·H| = 0.096` to a **sum of only `|G| = 0.048`**, that is
`|dG| = 0.135` = **2.8× the entire loop gain.**

| r | B = `\|H(8)\|/\|H_h\|` | `arg H_new` | peak `\|H\|` | τ_ring | `arg dG` | `\|u_new\|/\|u\|` | `\|dP\|` | `\|P_new\|` | `arg P_new` | `\|A_new\|` | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| honda | 1.000 | −10.9° | +0.00 dB | 4.4 ms | — | 1.000 | 0 | 0.630 | +162.8° | 0.440 | baseline |
| 0.80 | 0.975 | −24.3° | −0.00 dB | 4.5 ms | +66.2° | **1.311** | 0.29 | 0.852 | +177.8° | **0.152** | worse |
| 0.90 | 0.905 | −43.6° | −0.00 dB | 9.5 ms | +53.0° | **1.889** | 0.69 | 1.253 | **+181.4°** | 0.254 | **encircles −1** |
| 0.96 | 0.968 | −67.5° | +0.20 dB | 24.5 ms | +49.0° | **2.601** | 1.18 | 1.744 | +183.5° | 0.749 | **encircles −1** |
| **0.98** | **1.453** | **−77.8°** | **+3.23 dB** | 49.5 ms | +61.3° | **3.342** | **1.77** | **2.265** | **+195.5°** | 1.328 | **encircles −1** |
| 0.99 | 2.655 | −82.5° | +8.35 dB | 99.5 ms | +75.4° | 5.193 | 3.18 | 3.555 | +212.1° | 2.760 | **encircles −1** |

🛑 **`|u_new|/|u|` at 6–9 Hz is 3.34×, not 0.44×. The amplitude criterion REVERSES between the
idealised parameterisation and the realisable filter.** And `arg(P)` crosses +180° with `|P| > 1` —
a Nyquist **encirclement of −1** ⇒ two RHP closed-loop poles.

Sub-band detail (each sub-band solved independently for its own `c`; noisy at 2/3 episodes, but the
**direction is unanimous**):

| sub-band | `\|rho−1\|` | `\|P\|` | `arg P` | `\|1+P\|` | boosted `\|P\|` | boosted `arg P` | boosted `\|1+P\|` |
|---|---|---|---|---|---|---|---|
| 6.5–7.5 | 0.186 | 0.367 | +130.1° | 0.813 | 1.021 | **+173.1°** | **0.124** |
| 7.0–8.0 | 0.167 | 0.271 | +150.1° | 0.777 | 0.928 | **+182.0°** | **0.079** |
| 7.5–8.5 | 0.238 | 0.565 | +158.6° | 0.517 | 2.048 | +188.4° | 1.069 |
| 8.0–9.0 | 0.374 | 1.127 | +155.6° | 0.466 | 4.202 | +186.5° | 3.210 |

**In every sub-band the boost pushes `arg(P)` past 180°, and in two of them `|1+P|` collapses to
0.08–0.12 — an 8–13× closed-loop amplification that does not exist today.**

### 4.3 Is there ANY `(f0, r, f_zero)` that passes? — NO

Sweep `f0` over {8.05 … 40 Hz} × `r` over {0.60 … 0.99}, requiring **all** of: `|u_new|/|u| < 1`,
`|A_new| > |A0|`, no encirclement, `|H(21.73)| ≤ |H_honda(21.73)|`. Three settings pass those four —
`(12, 0.99)`, `(14, 0.98)`, `(14, 0.99)` — **and every one of them has a peak `|H|` of +7.2 to
+12.9 dB, i.e. a large new resonance parked in 12–14 Hz, immediately adjacent to the 9–13 Hz band where
`Re(Z) = −4885` (the second most anti-damped band in the car).** Adding the gate **peak `|H| ≤ +3 dB`**
leaves **NOTHING**.

### 4.4 The added pole — the honest answer to "is it a new resonance?"

- **The Q argument is a red herring, in the boost's favour.** `r = 0.980` ⇒ `ζ = 0.371`, **Q = 1.35**
  (Honda's stock: `ζ = 0.650`, Q = 0.77; the *mechanical* mode: Q = 10.21, ζ = 0.049). +3.23 dB at
  Q 1.35 is a gentle shelf, not a resonance. `r = 0.990` ⇒ Q = 2.57.
- **The PHASE is the problem, and it is decisive.** −67° of extra lag at 8.05 Hz, −83° by 9 Hz,
  injected into a loop measured at `arg(P) = +163°` with `|P| = 0.63` — i.e. **17° from the −1 axis
  with 1.5–4 dB of gain margin.** §4.2 is what that does.
- **⇒ The +3.23 dB peak is not the danger. The danger is that the pole pair rotates a near-marginal loop
  past its phase crossover.** Constraint (ii) is violated, but by the closed loop, not by the filter.

### 4.5 The engagement transient (orchestrator's GATE-3 addendum)

The filter is arm-gated and its states **freeze** while disarmed, so every engagement resumes from a
stale state. Worst-case zero-input response, state ceiling `= (state/input ratio) × engaged p99
(1244 ct)`:

| design | state ceiling `\|w\|` | worst free-response peak `\|y\|` | τ | 3τ | cycles of ring at 8 Hz |
|---|---|---|---|---|---|
| **HONDA (shipped)** | 11,159 ct | **828 ct** | 4.4 ms | 13.2 ms | **0.11** |
| **BOOST r = 0.980** | 677 ct | **1,770 ct** | 49.5 ms | **148.5 ms** | **1.20** |
| BOOST r = 0.990 | 1,237 ct | 3,234 ct | 99.5 ms | 298.5 ms | 2.40 |

(≤2× these if the stale and correct states are anti-phase ⇒ up to ~3,500 ct = **35 % of the ±10240
aggregator clamp**.)

🛑 **The boost's engagement transient is 2.1× larger and 11× longer than Honda's, and it rings for
1.2 cycles at exactly the ratchet frequency.** Route `0x9e` had 7 engagements in 647.8 s. **The build
would manufacture a short 8 Hz burst at every engagement — the symptom it is meant to remove, on a
schedule.** This alone argues against `r ≥ 0.98`, independently of §4.2.

---

## 5. Ranking against active damping (`−K·φ′`), the V105 candidate

1. **Active damping `−K·φ′` — clearly first, and §3 strengthens the case.** It adds a term
   `dG_damp ∝ +jω` whose **phase is set by the differentiator, not by a resonant pole**, so it can be
   placed anywhere in the favourable window **without** the −90° penalty that kills the biquad. And it
   is what the identification asks for: `Z0` is a **lossless spring** and 100 % of `Re(Z) = −3761` is
   loop-generated, so the deficit is real damping, and adding real damping is the matched fix.
   🛑 **Sizing, now quantitative:** the effect scales as `dP = c·dG` with **`|c| = 13.09`**. A `dG` of
   just **0.047** (≈ **89 % of the entire sum `|G| = 0.053`**, and only **49 % of one lane**) already
   yields `|A|` 0.44 → 0.87. **A lane-sized dose would be ~4× over.** Size against the sum.
   ⚠ Its wrong-sign failure mode is now also priced: at `|c| = 13`, a sign error of the same size drives
   `|A|` from 0.44 to ~0.15 — a **6.7× closed-loop amplification.** Pre-register the sign readout.
2. **A PURE-MAGNITUDE boost of `gp-0x6b86` (no phase rotation) — theoretically the best single lever
   found, and NOT buildable via the biquad.** `dG_opt = 0.0472 ∠ +169.1°`, i.e. **scale the lane by
   1.49× with zero phase change**: `|u|` → 0.443×, `|A|` 0.440 → 0.869, `Re(Z)` −3761 → **+812**,
   and `P` moves **away** from −1. The only structure that could deliver it is the **LERP map itself**
   (`gp-0x37e8[]` Y-values ⇒ `a`), which is a **DC-inclusive** change to steering effort at all
   frequencies — a different animal, with its own gate. **Reported as an observation, not a
   recommendation.**
3. **The biquad boost as specified — DEAD.** §4.
4. **The biquad notch — DEAD.** `GATE2-…-notch-sign.md`.

---

## 6. What I could NOT compute

- **A frequency-resolved `c(f)`.** The sub-band solves (§4.2) swing `|c|` 5.8–24 and `arg c` +114…+187°
  at 2/3 episodes. The 6–9 Hz band solve is well-conditioned; the sub-bands are indicative only, so the
  **encirclement is a strongly-supported BELIEF, not proven**. The *direction* (`arg P` increases past
  180°, `|P|` rises above 1) is unanimous across all four sub-bands and both parameterisations.
- **`a` at 21.7 Hz, and the identity of the 0.54 ∠ +21.6° unexplained term there.** Neither is needed
  for §2 (the sign is `a`-invariant; the amplitude ratio is monotone in `a`).
- **Whether the friction-hold limiter between the LERP and the biquad tap has a frequency-dependent
  describing function.** If it does, `a` is not flat and the *magnitudes* in §2.4 and §4 move. The
  *signs* do not.
- **Any closed-loop conclusion at 21.7 Hz.** `|rho−1| = 0.083` there ⇒ the identification is ill-posed.
- **A real CI on the sum's phase.** 2 episodes (r85), 3 (r95) — unchanged from the prior analysis, and
  it remains the single largest weakness.
- **A rigorous Nyquist encirclement count.** That needs `c(f)` on a fine grid over 0–50 Hz, which needs
  §7's drive.

## 7. What would close the remaining gaps — and the V104 answer

🛑 **YES: repointing the 427 lane from `gp-0x6b4c` to `gp-0x6b94` (the SUM) on V104 is worth it, and
it pays off from a SINGLE drive.** §3.3 proves the identification runs **within one drive** off the
`|T|` operating-point ladder — no cross-build assumption, no matched-exposure requirement, no
gain step needed. Requirements, in order of importance:

1. **≥ 6 engaged episodes** (currently the binding constraint: r85 has **2**, one of them 15.4 s, and
   dropping it swings `|A|` from 0.44 to 0.18). 6 episodes ⇒ CI half-width ≈ ±36 % of the estimate
   instead of today's ±63 %; 8–10 ⇒ ≈ ±30 %.
2. **Each episode ≥ 10 s** (≥ 4 non-overlapping 4 s windows). Total ≥ 60–120 s engaged.
3. 🛑 **A well-populated HIGH-torque bin — ≥ 12 windows with `p75(|tq|) > 2000 ct`.** This is what makes
   `|rho−1|` large enough to condition the solve; on r85 the top bin had only 12 of 120 windows and
   **every well-posed pair involved it.** In practice: a few firm pushes against the assist while
   engaged (holding a curve, a deliberate lane change) — ordinary symptomatic driving, no special
   protocol.
4. It also converts the identification from **exactly determined** (cannot fail) to **over-determined**
   (4×/6×/8× all packing the sum ⇒ 2 surplus real equations ⇒ a residual test that can falsify the
   model). That is worth having on the record regardless of V104's fix.

**It does NOT require the 8× gain**, and it does not compete with the fix for drive budget.
