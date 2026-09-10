# V290 row S — THE PARAMETRIC-MODULATION HAZARD, resolved

**Agent** `paramod` (SUBAGENT; orchestrator `main`). **Analysis only — nothing was built, flashed or sent.**
Date 2026-09-09.

**Scripts (everything below reproduces from these two, and only these two)**
- `rlog-tools/studies/grind/paramod_v290_modulation.py` — items 1 and 3. Measures the modulation from the wire
  and scores the mitigation variants. → `_scratch/paramod_v290_modulation.txt` (+ `.json`).
- `rlog-tools/studies/grind/paramod_v290_floquet.py [verify|sweep|deep|trace|nl|nlsweep|all]` — item 2. The
  Floquet / Lyapunov analysis and the clamped integer mirror. → `_scratch/paramod_v290_floquet.txt` (+ `.json`).

**Inputs read, not re-derived**: `reqaxis`'s byte-exact `demand()` mirror in `kpkd_axis_r62_r63.py` (which
agrees **1.0000 frame-for-frame** with the kit's independent `GI.demand_live` on all three routes);
`design290b_candidates.py`'s `Elec`/`Controller`/`mkplant`; `_scratch/design290b_family.json` (304 fits, 121
linear-stable on V289, **87 also burst-consistent** — the SUB family); the census episode cache
`_scratch/grind1_census_v289_r62_r63_cache.pkl`; route caches `r62_v289`, `r63_v289`, `r5e_v288`, `r39`.

---

## 0. VERDICT (item 4)

> ## ✅ **ROW S IS SAFE TO BUILD. No mitigation is required.**
>
> The parametric hazard is **real**, the loop **is** susceptible to it, and the clamped loop is susceptible
> **far more than a linear reading shows**. Row S cannot reach it: the modulation it produces on the measured
> wire is **15–50× too slow** and **50–500× too shallow**, on two independent axes at once, and the **actual
> measured `Kd(t)` trace run through the byte-exact clamped mirror never pumped — decay ≥ V282's in 9 of 9 cases.**

**This is not "we could not tell from the wire."** Both axes of the hazard are measurable from data already
in hand, and both were measured.

**What a FAIL would have looked like, written before the runs were made:** a Floquet spectral radius > 1 at
any depth row S can deliver; or a measured-trace Lyapunov exponent above **both** frozen-Kd references; or a
clamped-mirror ring decay under the measured `Kd(t)` below V282's. **None occurred.** One intermediate result
*did* come back FAIL-shaped (§4.3) and is reported as such rather than smoothed away.

### 🛑 A correction to the brief's premise, which changes the shape of the hazard

Under row S, `Y[0] = Y[1] = Y[2] = 96`, so **knot 11 is a NO-OP** and **there is no step at knot 32.** The
delivered surface is

```
Kd(idx) = 96                              idx <= 22      flat   <- knot 11 does nothing under row S
        = 96 + 32*(idx-22)/(32-22)        22 < idx < 32  RAMP   <- dKd/didx = +3.2 per idx count
        = 128                             idx >= 32      flat   <- byte-identical to V282
```

The LERP is **piecewise linear and continuous in `idx`**; nothing switches discontinuously anywhere. The
hazard is therefore a *continuous* parametric modulation whose depth is set by how much of a 10-count-wide
ramp the demand traverses — not the two-state switch the brief (reasonably) assumed. The square waves used
in §4 are a **construction, to bound the hazard**, not something the firmware does.

**Physical scale of the slope**: 3.2 Kd per idx count = **0.1984 Kd per wire count of 0xE4**
(1 idx LSB = 16.1257 wire counts, `reqaxis`).

---

## 1. ITEM 1 — THE MODULATION, MEASURED FROM THE WIRE [EVIDENCE]

Method: `AX.demand()` (the byte-exact `0x29032 → 0x29CFA` integer mirror) on the four route caches, then the
row-S LERP applied to the resulting `idx` trace. All statistics engaged-only.

### 1.1 Time inside the only band where row S's Kd varies (22 < idx < 32)

| route | ENG | GRIND (census episodes) | TURN7 (2–5 m/s, \|ang\| 70–140°) | CRUISE (≥22 m/s, \|ang\|<5°) |
|---|---|---|---|---|
| r62_v289 | 3.9 % | 3.0 % | 3.5 % | 0.11 % |
| r63_v289 | 4.2 % | 8.8 % | 6.0 % | 0.32 % |
| r5e_v288 | 4.2 % | 10.5 % | 3.8 % | 0.00 % |
| r39 (V282) | 7.2 % | 12.2 % | 4.9 % | 1.38 % |

**Kd is pinned at exactly one value 88–96 % of the time.** The `Kd(idx)` map is a *saturating* nonlinearity,
and that is the structural reason the ring's own echo in the command cannot modulate Kd for most of an
episode.

### 1.2 Knot-crossing rate — the modulation FREQUENCY

Crossings per second of the named regime, at the two knots row S actually uses:

| route | knot 22, ENG / GRIND / TURN7 | knot 32, ENG / GRIND / TURN7 |
|---|---|---|
| r62_v289 | 0.83 / 1.36 / 2.06 | 0.73 / 1.20 / 1.82 |
| r63_v289 | 1.05 / 2.77 / 4.93 | 0.93 / 3.54 / 4.62 |
| r5e_v288 | 1.17 / 3.43 / 2.11 | 0.80 / 2.81 / 1.76 |
| r39 (V282) | 1.59 / 2.78 / 1.78 | 0.93 / 2.59 / 2.91 |

⇒ **1.2–3.5 crossings/s inside grinding episodes.** The ring is at 16–20 Hz. **The demand crosses these knots
at the rate the driver changes lane demand, one to two orders of magnitude below the ring, and well below 7 Hz.**
(Knot 11, a no-op under row S, is crossed 1.8–4.1/s — reported for completeness only.)

### 1.3 Spectrum of the delivered Kd(t) — where the modulation energy actually is

Share of the AC variance of `Kd(t)`, whole-route engaged, contiguous runs ≥ 2 s (DC bin excluded; each
periodogram normalised so Σ P = var(x)):

| route | 0–2 Hz | 2–5 | 5–9 | 9–13 | 13–18 | 18–23 | 23–30 | 30–36 | 36–44 | 44–50 |
|---|---|---|---|---|---|---|---|---|---|---|
| r62_v289 | **0.955** | .027 | .007 | .003 | .002 | .004 | .001 | .000 | .001 | .000 |
| r63_v289 | **0.935** | .032 | .013 | .006 | .003 | .006 | .002 | .001 | .001 | .001 |
| r5e_v288 | **0.945** | .032 | .011 | .003 | .002 | .004 | .001 | .001 | .001 | .000 |
| r39 | **0.944** | .030 | .010 | .004 | .003 | .003 | .003 | .001 | .001 | .001 |

**94–96 % of the modulation energy is below 2 Hz.** The wire is 100 Hz, so the 2f bands (31–40 Hz) sit well
below Nyquist and are real, not aliases.

### 1.4 The drive DEPTH, in V59's own statistic

`eps_kf` = (rms of the `Kd` component within ±2 Hz of *k·f₀*) ÷ (mean Kd over the episode), computed **per
episode** (never on a concatenation of disjoint windows) and pooled by duration, then ×√2 so it matches V59's
half-swing convention:

| route | n episodes | mean Kd | f₀ | **eps_2f** (principal tongue) | eps_1f (subharmonic) | worst single episode, 2f |
|---|---|---|---|---|---|---|
| r62_v289 | 12 | 106.5 | 16.8 | **0.0021** | 0.0045 | 0.0048 |
| r63_v289 | 15 | 118.9 | 17.0 | **0.0048** | 0.0095 | 0.0233 |
| r5e_v288 | 46 | 115.5 | 19.7 | **0.0071** | 0.0181 | 0.0266 |
| r39 (V282) | 79 | 114.4 | 20.0 | **0.0052** | 0.0126 | 0.0214 |

> **V59's MEASURED pump, for scale: eps 0.333 at 42.19 Hz = 2 × a 21.09 Hz mode, prominence 11.10×**
> (`accord-parametric-pump-intervention-never-run`). Row S's drive is **47×–160× weaker at the mean** and
> **~12× weaker than V59 even on the single worst episode in the whole corpus.**

---

## 2. ITEM 2 — THE METHOD, AND WHY THE OBVIOUS ONE IS WRONG

A loop whose gain varies periodically is a **linear time-periodic (LTP)** system. Its stability is *not* given
by the eigenvalues of the frozen-Kd loop at any single Kd: a system stable at *every* frozen Kd can still be
unstable when the parameter alternates. That is the whole content of the hazard.

**The state basis is the crux, and it is easy to get wrong.** I built the closed loop as a discrete
state-space at 1 kHz in a **physical basis** — one state per physical storage element (the feedback filter,
the D term's `E_prev`, the output lag, the explicit `z^-1` in `R()`, and the plant's own states plus its
transport-delay ticks). Kd enters **only the static output row** of the PID block:

```
u = (Kp/256 + Kd/8) * E  -  (Kd/8) * E_prev          <- the ONLY Kd-dependent row
```

so `A_cl(Kd)` is **affine in Kd and every Kd shares the same state basis**. That is what makes switching Kd a
well-posed product of matrices.

> 🛑 **A companion realisation built from the characteristic polynomial would NOT be valid here**, even though
> it reproduces the right poles at each frozen Kd: its similarity transform depends on Kd, so a product of
> such matrices models a *different physical system* at every switch. This is the single trap in the method
> and it is invisible in the frozen-Kd checks.

**VERIFICATION [EVIDENCE].** Eigenvalues of `A_cl(Kd)` against `design290b.poles_of(ElecP(cellsfb(c282, None,
None, kd)), plant)` — its own machinery, not mine — over 6 fits × Kd ∈ {128, 112, 96}, matching every
reference pole to its nearest eigenvalue: **worst |dz| = 2.028 × 10⁻¹¹.** State dimension 8–15.

Base electronics: **V282** (`fb_a/fb_b` 923/1560 = 16.53 Hz, no notch, lag 992/507, gain 5346, Kp 248) —
confirmed against `reconcile_v290.build_rows`, where row S's siblings are built as
`ElecP(cellsfb(c282, None, None, kd))`.

---

## 3. ITEM 2 RESULTS — THE LINEAR (FLOQUET) READING

### 3.1 The tongue is real and sits exactly where theory puts it

Sweeping a square-wave Kd 96↔128 over every modulation frequency the 100 Hz wire can carry (1–50 Hz) × duty
0.1–0.9, on all 87 SUB fits, and comparing **per fit** against that same fit's worst frozen-Kd spectral radius:

- the maximum excess is at **f_mod 39.25–40 Hz = 2 × the 20.0 Hz V282 ring** — the **principal tongue**;
- a second, weaker peak sits at **20.0 Hz** — the **subharmonic tongue**;
- everywhere else the excess is *negative* (the modulated loop is better damped than the worse frozen Kd).

**The method is demonstrably not blind to the phenomenon it was built to find.**

### 3.2 …and linearly it is negligible

| quantity | value |
|---|---|
| constant Kd 128 (V282), ρ max over 87 fits | 0.998378 (0 unstable) |
| constant Kd 96, ρ max | 0.996352 (0 unstable) |
| **worst modulated ρ, full swing, worst f/duty/fit** | **0.998423** |
| worst per-fit excess | **+3.76 × 10⁻⁴ / tick** |
| in continuous terms | decay 4.573 → 4.196 1/s, a **8.3 % loss** |
| margin to instability (ρ = 1) | 0.00158 |

### 3.3 The tongue DOES open — but only at a near-total gain modulation

Depth sweep with **f_mod and duty re-optimised at every depth** (a fixed-frequency sweep has a hole: raising
the swing lowers the mean Kd, which moves the mode, which moves the tongue):

| swing | Kd range | eps | f_mod | duty | max ρ | max excess | unstable fits |
|---|---|---|---|---|---|---|---|
| 4 | 124–128 | 0.016 | 39.25 | 0.30 | 0.998371 | +3.4e-05 | 0 |
| 16 | 112–128 | 0.069 | 39.25 | 0.30 | 0.998407 | +2.4e-04 | 0 |
| **32** | **96–128** | **0.129** | 39.25 | 0.25 | 0.998423 | +3.8e-04 | **0** ← **the MOST row S can ever deliver** |
| 64 | 64–128 | 0.343 | 37.75 | 0.30 | 0.998437 | +8.1e-04 | 0 |
| 96 | 32–128 | 0.727 | 37.75 | 0.40 | 0.998757 | +1.6e-03 | 0 |
| 112 | 16–128 | 0.942 | 37.75 | 0.40 | 0.999746 | +2.2e-03 | 0 |
| **118** | **10–128** | **1.035** | 37.75 | 0.40 | **1.001075** | +2.3e-03 | **7 of 87** ← threshold |
| 126 | 2–128 | 1.174 | 37.75 | 0.40 | 1.002654 | +2.5e-03 | 15 of 87 |

> **Row S's absolute maximum is eps 0.129 — a factor 8.1 below the instability threshold — and that is the
> FULL 96↔128 square wave. The eps actually MEASURED at 2f on the wire is 0.002–0.007 (0.027 worst single
> episode): a factor 38×–490× below threshold.**

### 3.4 The measured trace, linear Lyapunov

Top Lyapunov exponent (QR on the product of `A_cl` over the real per-tick `Kd(t)`, the 100 Hz `idx` held for
10 loop ticks), on the three least-damped SUB fits, over every census grinding episode of each route:

**Excess over the worse frozen-Kd reference is NEGATIVE on all 12 route × fit combinations**, ranging
−4.7 × 10⁻⁴ to −3.7 × 10⁻³. The measured modulated loop is *better* damped than the worst constant Kd,
always.

---

## 4. ITEM 2 RESULTS — THE CLAMPED INTEGER MIRROR, and the one FAIL-shaped result

### 4.1 Why this check exists

Everything in §3 is **linear**. The kit's own reading of the V289 ring is a **clamp/friction-limited cycle**,
and a limit cycle is a nonlinear object a Floquet analysis of the unclamped loop *structurally cannot see*.
So: `design290b.Controller` byte-for-byte (P clamp 15360, D clamp 10240, sum clamp 15360, output clamp 3072
all live; the feedback quantised to 1/8 deg/s exactly as the firmware does), **Kd written per tick**, setpoint
held at 0, and a single torque impulse injected **at the plant input**.

> ⚠ **A method note that cost a wrong answer on the first pass.** Exciting the ring through the *setpoint*
> saturates the D clamp at any useful kick — `E = 32·sp`, so `sp ≥ 256` rails `D` — which makes kicks of 300,
> 900 and 2400 produce **identical** traces, and at those amplitudes the ring sits on the 1/8 deg/s feedback
> quantiser and becomes a quantisation limit cycle rather than a decaying mode. The first run of this section
> reported decay rates 10× inconsistent with the linear analysis for exactly that reason. Injecting at the
> plant fixes both: decay at constant Kd 128 is then 1.15–2.47 1/s against the linear prediction of 1.62 1/s,
> and at Kd 96 is 5.5–10.4 against 5.78.

### 4.2 The measured Kd(t) never pumps — 9 of 9

Three least-damped SUB fits × ring peaks 1 / 4 / 12 deg/s. "MEASURED" is the real `Kd(t)` from the
**most-modulated census grinding episode in the entire corpus** (r39, sd(Kd) 15.8, 1010 loop ticks), at three
phase offsets, worst taken:

| fit | ring pk | Kd128 | Kd96 | **MEASURED** | verdict |
|---|---|---|---|---|---|
| fp21.2 zp0.09 k0.15 τ2 f1 11 g0 .098 | 1.00 | 1.152 | 5.523 | **1.234** | ≥ V282 |
| " | 3.92 | 2.256 | 9.624 | **2.256** | ≥ V282 |
| " | 12.11 | 2.474 | 9.105 | **2.474** | ≥ V282 |
| fp22.0 zp0.12 k0.30 τ6 f1 30 g0 .049 | 0.98 | 1.075 | 7.522 | **1.220** | ≥ V282 |
| " | 4.08 | 2.048 | 10.154 | **2.048** | ≥ V282 |
| " | 11.87 | 2.074 | 10.379 | **2.074** | ≥ V282 |
| fp23.4 zp0.31 τ1 f1 30 g0 .048 | 1.02 | 1.091 | 6.463 | **1.696** | ≥ V282 |
| " | 3.99 | 1.688 | 7.584 | **2.035** | ≥ V282 |
| " | 12.17 | 1.661 | 7.422 | **2.010** | ≥ V282 |

Decay rates in 1/s of the |rate| peak envelope; **higher = faster = better**.

### 4.3 🛑 THE FAIL-SHAPED RESULT: the clamped loop is MUCH more susceptible than the linear one

A **synthetic** full-swing square wave (a construction, not the wire) at the tongue peak cuts the ring decay
**below both** constant-Kd references — at the 1 deg/s ring, to **0.482 1/s against V282's 1.152, i.e. 0.42×.**
The linear Floquet excess for the same modulation was **+3.8e-4/tick ≈ 2 %.**

> **The linear analysis alone would have understated this hazard by more than an order of magnitude, and I
> would have reported a false all-clear on it.** This is recorded because it is a standing methodological
> finding for the kit, not just a row-S result: *for this loop, a Floquet analysis of the unclamped
> electronics is NOT a sufficient parametric-safety argument.*

### 4.4 So where IS the clamped loop susceptible? The danger band, measured

Full-swing square wave, worst phase and duty, ring peak 1 deg/s (the most susceptible amplitude), least-damped
SUB fit. References: constant Kd 128 → 1.152 1/s, constant Kd 96 → 5.523 1/s.

| f_mod (Hz) | 2 | 4 | 6 | 7.3 | 10 | 13 | 16 | 18 | **20** | 22 | 25 | 28 | 31 | 34 | 37 | **39.25** | 42 | 45 | 50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| decay vs V282 | .76 | .83 | .82 | .77 | .76 | .80 | .81 | .68 | **.37** | .85 | .87 | .78 | .74 | .69 | .78 | **.42** | .82 | .82 | .81 |

Two sharp dips — **20.0 Hz (1f, subharmonic) and 39.25 Hz (2f, principal)** — on a broadband ~20 % floor that
is a *switching-transient* effect (a step in Kd steps the D term even at constant `dE`), not a resonance.
**Danger band (>20 % decay cost at full swing): 2.0–39.2 Hz.**

**And that is precisely the band the measured modulation does not occupy**: measured crossing rate inside
grinding episodes is **1.2–3.5 /s**, an order of magnitude below the bottom of the band, before its depth is
counted at all. Note also that row S's ramp is continuous, so it cannot produce the *step* that drives the
broadband floor either — the largest single-frame Kd change row S can make is bounded in §6.

---

## 5. ITEM 3 — THE MITIGATIONS, SIZED

Every variant below keeps `Y[3] = 128` and is therefore **byte-identical to V282 above idx 32**, where the
lookup takes its high-clamp branch (`0x29EA0 sld.hu 0x6,ep,r10` = X[3]; `0x29EB0 ld.hu 0x6,r8,r7` = Y[3]).
⇒ **the 7 Hz strong-turn gate and the capped-step authority are ×1.000 BY CONSTRUCTION on all of them**, not
by estimate.

> 🛑 **The gate on any X edit**: the LERP divides by `X[i] − X[i−1]` (`divq`), so **X must stay strictly
> increasing** — `X = [0, 11, 11, 32]` divides by zero. X bytes are also a **different, riskier byte class**
> than Y bytes: they move the axis that every consumer of this record shares.

| variant | bytes | class | ramp (idx) | dKd/didx | note |
|---|---|---|---|---|---|
| V282 (no edit) | 0 | — | none | 0.00 | the revert |
| **S — Y=[96,96,96,128]** | **6** | Y only | 22–32 | **3.20** | **the candidate** |
| S′ — Y=[112,112,112,128] | 6 | Y only | 22–32 | 1.60 | shallower cut |
| **M1 — Y=[96,96,112,128]** | **6** | Y only | 11–32 | **1.60** | ramp widened, **SAME byte cost** |
| M2 — Y=[96,104,116,128] | 6 | Y only | 0–32 | 1.20 | ramp widened further, same cost |
| M3 — X=[0,8,11,32] Y=[96,96,96,128] | 10 | **X + Y** | 11–32 | 1.52 | same as M1 but via the risky class |

Against the measured wire — `Kd_eff` over all engaged time (**lower = more of the damping benefit kept**);
`sd` and `eps2f` over census grinding episodes:

| variant | r62 Kd_eff / sd / eps2f | r63 | r5e | r39 |
|---|---|---|---|---|
| V282 | 128.0 / 0.00 / 0.0000 | 128.0 / 0.00 / 0.0000 | 128.0 / 0.00 / 0.0000 | 128.0 / 0.00 / 0.0000 |
| **S** | **101.4 / 4.96 / 0.0021** | **102.0 / 6.97 / 0.0048** | **102.7 / 11.02 / 0.0071** | **103.2 / 11.27 / 0.0052** |
| S′ | 114.7 / 2.48 / 0.0009 | 115.0 / 3.48 / 0.0023 | 115.3 / 5.51 / 0.0033 | 115.6 / 5.64 / 0.0024 |
| **M1** | 102.4 / 5.13 / 0.0017 | 103.0 / 5.09 / 0.0028 | 103.9 / 9.81 / 0.0047 | 105.5 / 10.25 / 0.0040 |
| M2 | 105.2 / 5.36 / 0.0018 | 105.7 / 4.26 / 0.0021 | 106.7 / 8.20 / 0.0040 | 109.0 / 8.71 / 0.0033 |
| M3 | 102.5 / 5.15 / 0.0017 | 103.1 / 5.02 / 0.0027 | 103.9 / 9.78 / 0.0047 | 105.6 / 10.23 / 0.0039 |

**Reading.** M1 is the best mitigation available and it is **free** — same 6 payload bytes, same Y byte class,
authority protection untouched. It halves `dKd/didx` (3.20 → 1.60) and cuts `eps2f` by 25–35 %, at the cost of
`Kd_eff` rising 102.7 → 103.9 (r5e): it gives the 11–22 band (11.7 % of engaged time) 96→112 instead of a flat
96, so a small part of the damping benefit is traded away. **M3 buys the same factor through the riskier X
class and 4 more bytes — not worth it.**

**But against a hazard already 38×–490× below its threshold, a further factor of 1.3 is not worth any loss of
the damping benefit that is the whole point of row S. ⇒ recommend row S AS SPECIFIED; hold M1 in reserve.**

### Mitigation (a) from the brief — "move the cut wholly below the band the index visits during rings" — **CANNOT BE BUILT AS STATED**

The grinding episodes' `idx` p50 is **8 (r62) / 46 (r63) / 37 (r5e) / 20 (r39)**, with **24–66 % of their time
at idx ≥ 32**. The rings live on **both** sides of the ramp. There is no placement simultaneously below the
ring band and above nothing. ⚠ r62's episodes skew much lower than r63's (p50 8 vs 46) and with only 12 and 15
episodes that split is unresolved — `reqaxis` flagged this too, and **no design should lean on either number
alone.**

---

## 6. THE ONE RESIDUAL PATH, stated so it is not hidden

**[arithmetic EVIDENCE; the conclusion that it does not happen is EVIDENCE from §1.2; that it *cannot* happen
is BELIEF]**

openpilot's slew cap is 123 wire counts/frame = **7.63 idx per 100 Hz frame**, and row S's ramp is only **10
idx wide**. So a command slewing at the cap crosses the *whole* ramp in **1.31 frames**, and a sustained
capped up-down oscillation would be a full-swing triangle at **~38 Hz — inside the danger band of §4.4 and
right on the 2f tongue.**

**It has never been observed.** Such an oscillation would read as **~76 knot-crossings/s**; the measurement in
§1.2 says **1.2–3.5**. It is a path that exists in the arithmetic and that nothing on the wire suggests the
car takes. It is also the exact thing the instrument in §7 is specified to catch.

Under **M1** the ramp is 21 idx wide, a full traverse takes 2.75 frames, and the fastest achievable full-swing
triangle drops to ~18 Hz — still inside the band, which is why M1 is a factor, not a fix, and why it is not
recommended on this ground.

---

## 7. ITEM 5 — THE INSTRUMENT (for `instr290` and `main`)

### 7.1 The surprise: this hazard needs ZERO cave bits

`reconcile` suggested a comparator bit on which Kd cell was selected, noting the demand index is already on
the wire. **It is more than already on the wire — it is fully sufficient.**

- `idx` is **reconstructable byte-exactly from the 0xE4 command at 100 Hz** (`AX.demand()`, which agrees
  **1.0000** with `GI.demand_live`). Item 1 is that reader.
- **`idx` is frame-locked**: the firmware LERPs at 1 kHz, but `idx` only updates when a new 0xE4 arrives. So
  **100 Hz is the complete story for `idx`** — a 1 kHz probe would add literally nothing.
- Both halves of the hazard are therefore already observable with no new bits: its **cause** (crossing rate,
  ramp duty, spectrum) from the 0xE4 wire, and its **effect** (ring decay) from the existing grind census.

⇒ **Do not spend cave budget on the parametric hazard.** Spend it on V290's actual edit. What this hazard
needs instead is **pre-registration**, below.

### 7.2 PRE-REGISTERED READINGS — what the wire must show if the hazard is ABSENT

Computed on the V290 drive with `paramod_v290_modulation.py` (add the new route tag to `ROUTES`). **All
engaged-only; grinding windows from the same census detector used for V282/V288/V289.**

| statistic | engaged | inside grinding episodes | **HAZARD PRESENT if** |
|---|---|---|---|
| knot-22 crossings / s | 0.8 – 1.6 | 1.4 – 3.5 | **≥ 15 /s** |
| knot-32 crossings / s | 0.7 – 1.0 | 1.2 – 3.6 | **≥ 15 /s** |
| duty inside the ramp 22<idx<32 | 3.9 – 7.2 % | 3.0 – 12.2 % | **≥ 30 %** |
| eps_2f of Kd(t) | — | 0.002 – 0.007 (worst episode ≤ 0.03) | **≥ 0.10** |
| share of Kd AC variance below 2 Hz | 0.94 – 0.96 | — | **≤ 0.60** |
| share of Kd AC variance in 18–42 Hz | 0.006 – 0.011 | — | **≥ 0.10** |

The thresholds are set an order of magnitude above the measured spread and an order of magnitude below the
§4.4 danger band, so the test is decisive in both directions.

### 7.3 The ONE bit worth having — and it is not about the hazard

If `instr290` has a spare rung, the highest-value single bit here is a **comparator that confirms the axis
model itself on-car**, which is a premise **nobody has ever verified directly for the Kd record**, and on
which the entire row-S design rests:

> **`b = (Kd_selected > Y_floor)`** — set inside the cave immediately after the Kd LERP returns
> (`0x29E92`…`0x29EDE`), 1 when the looked-up Kd exceeds the table's floor value, 0 otherwise. Comparator:
> **no scale assumption, no LSB, no ceiling — its DUTY is the answer.**

**Pre-registered duty if the model is correct** (= the measured `idx > 22` duty, from §1.1):

| route regime | r62 | r63 | r5e | r39 |
|---|---|---|---|---|
| engaged | 18.9 % | 20.9 % | 23.1 % | 26.5 % |
| grinding episodes | 34.4 % | 75.5 % | 66.2 % | 63.7 % |
| strong turns (TURN7) | 91.7 % | 82.4 % | 90.3 % | 89.2 % |
| cruise | 0.1 % | 0.4 % | 0.0 % | 2.4 % |

**The sentence a null licenses**: if the bit reads within those bands, the demand-axis model behind row S is
confirmed on-car and the hazard's absence follows directly from §1. **If it reads materially otherwise, the
row-S premise is wrong** — which is a far larger finding than the hazard, and one no other planned instrument
would catch.

> 🛑 **A related point `instr290` and `main` must weigh, which is outside my brief but follows from it:**
> row S as specified is **cal-only, and therefore carries NO instrument for its own edit.** The standing rule
> is that every build carries the instrument for its own edit and that a cal-only edit still needs telemetry.
> §7.2 discharges that for the *hazard*, from the free wire. Whether the *lever* — the Kd cut's effect on the
> ring — is observable from one short drive without a cave is `instr290`'s call, not mine.

---

## 8. EVIDENCE / BELIEF LEDGER

| claim | status | method |
|---|---|---|
| Knot 11 is a no-op under row S; the surface is a continuous 22→32 ramp | **EVIDENCE** | LERP semantics read from `0x29DDE/0x29DE2/0x29DF4` + `0x29EA0/0x29EB0` (`reqaxis`), applied to the row-S Y vector |
| Crossing rates, ramp duty, Kd spectrum, eps_1f/eps_2f | **EVIDENCE** | byte-exact `demand()` on 4 route caches; per-episode spectra, DC-excluded, variance-normalised |
| The state-space is a faithful physical realisation | **EVIDENCE** | eigenvalues vs `design290b.poles_of`, worst \|dz\| 2.03e-11, 18 cases |
| The 2f tongue exists at 39.25–40 Hz, subharmonic at 20 Hz | **EVIDENCE** | Floquet monodromy sweep, 87 fits, per-fit excess |
| Linear instability threshold is eps ≈ 1.035 | **EVIDENCE** | depth sweep with f_mod and duty re-optimised at each depth |
| The measured trace does not pump (linear and clamped) | **EVIDENCE** | Lyapunov on 12 route×fit combos; clamped mirror 9/9 |
| The clamped loop is far more susceptible than the linear one | **EVIDENCE** | clamped integer mirror, 0.42× vs a linear +2 % |
| Danger band 2.0–39.2 Hz | **EVIDENCE** for the numbers; **BELIEF** that it transfers to the real plant | one least-damped fit, one ring amplitude |
| Row S is safe to build | **EVIDENCE**-backed conclusion | two independent margins (rate 15–50×, depth 38–490×) plus the direct measured-trace test |
| The capped-slew 38 Hz path cannot happen | **BELIEF** | the arithmetic that it *could* is EVIDENCE; that it does not is EVIDENCE from §1.2; that it never will is not established |

---

## 9. WHAT WOULD CHANGE THIS VERDICT

1. **A drive on which the pre-registered §7.2 readings move.** Chiefly a knot-crossing rate above ~15/s or a
   ramp duty above 30 % — either would mean the demand has started oscillating in a way no route in the corpus
   shows, and the §6 path would be live.
2. **A change to openpilot's command shaping** that raises the slew cap or removes the 1.2 Hz jerk LPF. The
   whole rate margin rests on how fast the *command* moves, which is a property of the fork, not the ECU.
3. **A V290 that also narrows the ramp** (moving X[3] down toward X[2]) — that would raise `dKd/didx` and is
   the one edit direction that makes this hazard worse. Nothing currently proposed does so.

---

*Agent `paramod`, 2026-09-09. Reports to orchestrator `main`. Built nothing, flashed nothing, sent nothing.*
