# REFUTE (stability lens), round 1: DESIGN C1, the angle loop, 2026-09-30

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent; the fork was not touched. Ghidra was not needed
(all numbers are the documented C1 lane arithmetic plus the r71b plant family). Python = the `bin_decompile` env.

**Author:** a refuter subagent (Opus), for the orchestrator `main`. **Brief:** make the REVISED design **C1**
(`docs/specs/design/DESIGN-ANGLE-LOOP-C1-2026-09-30.md`) FAIL on **loop stability and phase** — re-derive the
margins independently, sweep a ≤ 0.25 m/s grid incl. the plant knots, attack every single / combined / aged /
stress member, report Re(T/ω) 5–25 Hz vs V294/V295, and find any operating point with **PM < 30° on a credible
member** or **< 45° nominal**, any 5–30 Hz closed-loop peak, or any damping regression the design did not declare.

**How to read this.** Every claim is **EVIDENCE** (with method) or **BELIEF**. Cited by grep string. My scripts:
`analysis-2020accord/studies/angle_loop/refute_stability/refute_c1_ind.py` (independent model),
`refute_c1_run.py` (sweep), `refute_c1_stage2.py` (characterisation); originals/outputs in
`_scratch/angle_loop/refute-c1-stability/`.

---

## 0. Verdict: FAIL. Do not flash C1 as designed.

**The design's verified core is sound.** My independent model reproduces every published anchor to **±0.1°**
(§1), so I corroborate, not dispute: tier A ≥ 45° everywhere (nominal min **62.3°**), the design-gated tier B
≥ 30° (b_lo×J_hi 35.2, ×tau6 32.7, J1.0 32.0, b_q 32.8 — all reproduced exactly), and the headline
**Re(T/ω)₂₀ = 0.997× V295** (my −0.6307 vs V295 −0.633). The 13 Hz 6.8× anti-damping is **declared** (§2.4). None
of those is a refutation.

**But C1 fails its own gate bar on a credible member it never ran.** The design gates the damping axis at its
own extreme (**b_q** = b × 0.25 at speed) — but only at **nominal inertia**. It gates the inertia axis (J_hi, J1.0)
only at **nominal damping**. It never combines them. Combining the two — each a member the design itself deemed
credible and gated — gives (EVIDENCE, two independent methods, §2):

| credible member | 15 m/s | 17 m/s | 19 m/s | nature |
|---|---|---|---|---|
| **b_q × J_hi** (J 0.5, direct p5c refit; b at the design's own 0.25× highway bound) | PM **4.9°**, Ms 12.7 | PM **3.3°**, GM 1.1 dB, Ms **19.3** | PM **5.5°**, Ms 11.9 | near-unstable 2.8–3.1 Hz ring |
| **b_q × J1.0** (J 1.0 interp refit, BELIEF; same 0.25× damping) | **UNSTABLE** ρ 1.0044 | **UNSTABLE** ρ 1.0071, PM −8.8° | **UNSTABLE** ρ 1.0049 | divergent 2.0–2.3 Hz mode |

- PM < 30° holds across the **entire v ≥ 12.5 m/s range** for b_q × J_hi (80/80 grid points), not one speed.
- **The design's own tool agrees.** `stab_lin.margins` + the exact 10-tick monodromy (ρ) give the same numbers
  (§2.3): b_q×J1.0 ρ > 1 at 15/17/19 m/s; b_q×J_hi PM 3.3° / Ms 19.3 at 17.
- **It is undeclared.** `grep b_q` over the design finds b_q only as the nominal-J member (§2.2 member table,
  §3.1 GATE row "b_q 32.8", §3.3, §6.3 discriminator). Nothing in GATE 2, §5 hazards, §8 misses or the §6.2
  reverts combines low damping with non-nominal inertia at highway.
- **It is unmitigated.** The ring is at **1.6–3.3 Hz**; the only highway stop, **R3**, is pitched at
  **3.5–5.5 Hz** (§6.2, §6.3), so R3 is blind to it; the §6.3 discriminator treats 1.4–2.8 Hz rings as "keep".
  Only R6 (|θ−θ_sp| > 10°) or R9 (operator feel) would fire, and only after the oscillation is already large.

This is exactly the failure class the design was revised to close (the refuter F4 "highway damping" + F2 "inertia
not excluded at speed"). C1 closed each **separately** and left the **product** — the worse case — ungated.

---

## 1. Method and validation (EVIDENCE)

`refute_c1_ind.py` is an independent linear model of the C1 edited lane. It does **not** import `stab_lin`,
`harness_freq` or `c1_gate2`; it takes only PLANT DATA from `v294_plant.family()` and the C1 TABLE/immediates
(G walk, KP_BASE 225, KI_BASE 100, KD 16) from `c1_lib`. The plant θ/u and ω/u are ZOH-discretised with my own
`expm`; the digital loop (100 Hz hold `(1/10)Σz⁻ᵃ`, output lag 992/507, forward 5346/32768, fade 254/256,
transport z⁻ᵈ, the fb path `80·θ·(1+z⁻¹)` held, PI `kp/256 + (ki/32768)/(1−z⁻¹)`, D `−kd·held-rate`) is assembled
by hand and L(e^{jωT}) swept; **my own** crossover finder gives PM/GM. Re(T/ω) is the controller output impedance
(member-independent), formed independently and aged.

**Validation — I reproduce the design and the C0 refuter to ±0.1°** (`refute_c1_run.py` "VALIDATION"):

| anchor | published | mine |
|---|---|---|
| C0 J_hi @ 11.9 (refuter FAIL) | 40.7° | **40.8°** |
| C1 nominal @1.0 / J_hi / b_lo / tau6 | 62.3 / 46.5 / 53.5 / 60.2 | 62.3 / 46.5 / 53.5 / 60.2 |
| C1 b_lo×J_hi@10 / ×tau6@10 / J1.0@11.9 / b_q@27 | 35.2 / 32.7 / 32.0 / 32.8 | 35.2 / 32.7 / 32.0 / 32.8 |
| C1 J_hi2@11.9 / J1.3@11.9 / ms_free@11.9 | 39.8 / 22.7 / 7.6 | 39.8 / 22.7 / 7.6 |

The model is correct; the disagreement below is about **which members were run**, not about the arithmetic.

---

## 2. Findings

### F1 — HIGH, CONFIRMED: a credible member is near-unstable / unstable at highway, undeclared and outside R3's band

**EVIDENCE (`refute_c1_stage2.py` §2A; my model and the design's `stab_lin`, §2.3):**

| member | v | J | b | k | Kp_eff | PM | exact GM | \|T_ref\| peak | ring Hz | ρ (monodromy) |
|---|---|---|---|---|---|---|---|---|---|---|
| b_q (gated, nominal J) | 17 | 0.20 | 5.16 | 79.7 | 1692 | 34.0 | 7.8 dB | 1.93 | **4.43** (in R3) | 0.974 |
| **b_q × J_hi** | 15 | 0.50 | 3.49 | 56.0 | 1243 | **4.9** | 2.1 dB | 12.4 | 2.77 | 0.995 |
| **b_q × J_hi** | 17 | 0.50 | 4.53 | 77.1 | 1692 | **3.3** | 1.1 dB | **18.9** | 3.14 | 0.997 |
| **b_q × J_hi** | 19 | 0.50 | 5.01 | 73.2 | 1748 | **5.5** | 1.8 dB | 11.4 | 3.12 | 0.994 |
| **b_q × J1.0** | 15–19 | 1.0 | 3.5–5.0 | 58–78 | 1243–1748 | **−6 … −8.8** | <0 | 6.6–10.3 | 2.0–2.3 | **1.004–1.007 UNSTABLE** |

**Why the components are credible (the design's own standards):**
- **b_q (b × 0.25 at ≥ 12.5 m/s)** is the design's *chosen* highway damping bound — "G(v) sized for PM ≥ 30° at
  b = 0.25× (floored)" (§2.2, §5 F4 row). At 17 m/s, 0.25 × (J_hi refit b 18.1) = 4.53, **above** the 3.46 floor,
  so the floor's own "intrinsic steering damping" argument does not rescue it.
- **J_hi (0.5)** at 17 m/s is a **direct p5c refit**, not an interpolation. refuter F2: "nothing up to J = 1.3 is
  excluded at 10–15 m/s"; the J profile is flat at 15–22 m/s (+4.5 % at J 1.3). So J 0.5 at highway is squarely
  credible; J 1.0 is credible on the design's own BELIEF interpolation.
- The design already gates **three-way** stacks (b_lo×J_hi×tau6) at PM ≥ 30°, so multi-axis stacking is inside its
  declared credible set. b_q×J_hi is a **two-way** stack of the same damping axis (at its own 0.25× bound) and the
  inertia axis. There is no stated reason the highway combined member should pin inertia to nominal (0.2) when the
  identification leaves it free to ≥ 1.0 there.
- **Not obvious double-counting (BELIEF):** inertia magnitude and the frequency-dependence of damping are separate
  unknowns; both are unconstrained at 15–19 m/s (rate R² 0.01–0.10 on 1 s windows; F4 fires). Combining them is not
  clearly re-using the same unmodelled effect twice. This is the one place I mark BELIEF; the arithmetic is EVIDENCE.

**Why it is a FAIL, not a declared miss:**
- **Undeclared:** `grep b_q` over the design (§0) finds b_q only at nominal J. No GATE-2 member, §5 hazard, §8
  miss (M1–M10) or §6.2 revert names low-damping × high-inertia at highway. §8 M9 covers J 1.3 / ms_free at *mid*
  speed with *nominal* b, a different corner.
- **Unmitigated:** the unstable/near-unstable ring is **1.6–3.3 Hz**. R3, the one pre-registered highway **stop**,
  is **3.5–5.5 Hz** (§6.2 R3, §6.3). The §6.3 discriminator lists 1.4–2.8 Hz rings as "keep". So neither the stop
  nor the discriminator catches this; only R6/R9 fire, after the fact.

### F2 — MEDIUM, CONFIRMED: the combined-member hold-age gate is incomplete (ungated combos + 10-tick age < 30°)

The design added F7's hold aging to the credible set, but only as `nominal+h10 / b_lo+h10 / J_hi+h10` (§2.2, §3.1)
— **single members only**. Combined members with a 10-tick-late slot 4 are ungated (EVIDENCE `refute_c1_run.py`
ATTACK 3, `refute_c1_stage2.py`):

| member (ungated) | min PM | at v | ring Hz | R3? |
|---|---|---|---|---|
| b_lo×J_hi×tau6 + h10 | **26.5°** | 10.0 | 1.8 | below R3 (and < 12.5 m/s) |
| b_lo×J_hi + h10 | **29.0°** | 10.0 | ~1.8 | — |
| J1.0 + h10 | **27.6°** | 11.9 | ~1.2 | — |
| b_q + h10 | **19.5°** | 27.0 | 4.0 | **in R3** (this one R3 catches) |
| b_q×J_hi + h10 | **UNSTABLE** (−5 … −7.9°) | 15–17 | 2.7–3.0 | below R3 |

These stack hold-aging onto already-aggressive combos (deeper tail than F1), so I rate them MEDIUM — but they show
the +h10 gate was applied to the wrong (single-member) subset. b_q×J_hi+h10 going unstable reinforces F1.

### F3 — LOW/observation: R3's band and the discriminator do not cover the credible 1–3 Hz ring frequency

Independently of F1/F2, the design's J-class rings live at **1–3.3 Hz** (my §2A and the design's own §3.3:
b_lo×J_hi 1.96–2.79 Hz, J1.0 0.95–1.81 Hz, b_q×J_hi 2.2–3.1 Hz). R3 (3.5–5.5 Hz) is tuned to the **b_q
(nominal-J)** ring (~4 Hz, EVIDENCE §2A). So the single pre-registered highway stop covers the damping-axis mode
but **not** the inertia-axis or combined mode. Recommend widening R3 to **~1.5–5.5 Hz at ≥ 12.5 m/s** regardless
of F1's disposition.

### F4 — observation (not a refutation): Re(T/ω) aging worsens 5–7 Hz, but 20 Hz holds

The design's `torque_per_rate` reports **age 0** only (§2.4). With a 10-tick-late hold, C1's Re(T/ω) at **5 Hz goes
−4.02** (age 0: −3.12) and **7 Hz −2.76** (−2.14) — ~30 % worse where V294/V295 *damp* (EVIDENCE §2B). This is
within the declared "5–17 Hz anti-damping, bounded not designed out" (§2.4), so **not** a refutation, but the aged
numbers belong on the page. **At 20 Hz aging does NOT hurt** (age-10 ratio 0.793× V295), so the headline
Re(T/ω)₂₀ ≤ V295 claim survives aging — I confirm it.

### 2.3 Cross-check against the design's own tool (EVIDENCE)

`stab_lin.margins` + exact 10-tick monodromy ρ, at the F1 operating points:

```
b_q        @15/17/19  PM 34.0/34.0/34.0  Ms 2.4/2.5/2.5  rho 0.9735/0.9740/0.9732   (stable, gated)
b_q*J_hi   @15/17/19  PM  4.9/ 3.3/ 5.5  Ms 12.7/19.3/11.9 rho 0.9952/0.9965/0.9941  (near-unstable)
b_q*J1.0   @15/17/19  PM -6.0/-8.8/-5.9  Ms  9.6/ 6.6/10.0 rho 1.0044/1.0071/1.0049  UNSTABLE
```

My independent model and the design's own tool agree → **CONFIRMED**, not merely plausible. The design simply never
ran this combination.

---

## 3. What survived the attack (the design is right about these)

- **Tier A, 0.25 m/s grid + plant knots:** nominal min PM **62.3°**; every single corner (J_lo/J_hi/b_lo/b_hi/
  tau0/tau6/F_hi/F_lo) ≥ 45°. No nominal point < 45°, no single-corner point < 45°. (EVIDENCE ATTACK 1.)
- **The design-gated tier B** (b_lo×J_hi, ×tau6, b_lo×tau6, J_hi×tau6, b/1.9×J_hi, b_lo×J0.3, J_hi2, J1.0, b_q,
  nominal/b_lo/J_hi +h10): all ≥ 30°, reproduced to ±0.1°. (EVIDENCE ATTACK 2.)
- **Re(T/ω)₂₀ ≤ V295 at every speed** (worst −0.6307 at 27 m/s vs V295 −0.633 = 0.997×), and aging does not break
  it. The 13 Hz 6.8× anti-damping is correctly declared. (EVIDENCE §2B, §2.4 of the design.)
- **Fork outer loop** at τ_o = 1 s: GM ≥ 11.7 dB on b_q×J_hi, ≥ 15 dB on b_lo×J_hi×tau6, ≥ 4.2 dB even on the
  (inner-unstable) b_q×J1.0 — the outer rule is sound; the failure in F1 is an **inner-loop** failure, not the
  outer loop. (EVIDENCE §2C.)
- The re-base (G ×2, Kp_base 225, Ki_base 100) and the five-knot table reproduce the claimed Kp_eff schedule.

---

## 4. What I could not check / limits

- Everything above ~8 Hz is model, not measured plant (the design says so). My F1 ring is at 2–3 Hz, inside the
  identified band, which strengthens it.
- The J 1.0 refit is the design's BELIEF interpolation; **b_q × J_hi (J 0.5, direct refit) alone already gives
  PM 3.3°**, so F1 does not depend on the interpolation.
- I did not re-score friction/stick-slip (friction refuter's lens).
- The credibility of simultaneously worst-casing damping-frequency AND inertia is a BELIEF (§F1); I argue it is
  inside the design's own declared credible set (it gates three-way stacks), but the operator may rule it a tail.

---

## 5. What would turn this FAIL into a PASS (for the designer; not run here)

1. **Gate b_q × {J_hi, J1.0} (and × tau6) at ≥ 12.5 m/s.** Either cap the highway Kp_eff so PM ≥ 30° holds on
   b_q × J_hi (my §2A suggests a large cut at 15–19 m/s — the current 1243–1748 is far too high for that member),
   **or** measure a 1–5 Hz plant FRF above 10 m/s before flight and show J and the 3–5 Hz damping are not both at
   their credible extremes. The design already says (§10.1) not to relax tier B without that FRF; the same FRF is
   the prerequisite to *keep* the current highway gain against this member.
2. **Widen R3 to ~1.5–5.5 Hz at ≥ 12.5 m/s**, so the pre-registered highway stop covers the inertia-axis / combined
   ring (1–3 Hz), not only the damping-axis ring (~4 Hz). Make it a STOP from the first highway minute.
3. **Extend the +h10 hold-age gate to the combined members**, or state why single-member aging bounds the combos.
4. Put the aged Re(T/ω) 5–7 Hz numbers on the page (EVIDENCE already bounded/declared, but age-0 only is shown).
