---
name: feedback-convert-the-symptom-into-the-levers-own-units-before-reading-a-null
description: "🛑⭐⭐⭐⭐⭐ PROCESS: four premises the kit reasoned from for days were FALSE, and every one was caught by an agent re-deriving a claim it had ALREADY REPORTED -- never by review. Before reading any null, convert the symptom into the lever's own units and check the lever was actually active there."
metadata:
  node_type: memory
  type: feedback
---

🛑 **The 2026-09-10 session overturned FOUR premises the kit had been reasoning from — and not one was a
measurement error. Every one was a PREMISE that was recorded confidently, inherited into later work, and
never checked against the thing it was supposed to do.**

| premise, as recorded | what it actually was |
|---|---|
| "V288's pre-filter cut 20 Hz by ×0.457, so the reference-side class is EXHAUSTED" | the cave is **non-LTI**; at the ring's amplitude it changed **neither amplitude (−1 % to +9 %) nor phase (0.0°)**. **Untested, not exhausted.** |
| "`clip_curvature` removes the raw staircase before the PID sees it" | **binding fraction 0.000** everywhere. 60–71 % of low-speed ticks carry the raw model output bit-for-bit. |
| "the command stream is 100 Hz" | the device's own tx counter fits **99.53–99.56 Hz** — anything on that axis was biased 0.45 %. |
| "kp = 0.600 on all routes; latAccelFactor = 1.68933" | live values are **kp 0.8/0.9** and **LAF 2.11/6.00** — one gain chain was wrong by **×3.6**. |

## ⭐ The rule that would have caught the biggest one

> **Before reading any null, convert the SYMPTOM into the LEVER'S OWN UNITS and check the lever was
> actually active there.**

V288's filter was gain-0.457 for *large* inputs and **1.000 for small ones**. The ring, converted into
the filter's own units, is **4.0–10.7 setpoint counts** (15–40 raw ÷ 16.125736 idx LSB × 4.30 sp/idx) —
where the gain is 0.95–1.01. A slew-capped frame is **32.8** counts, where the filter genuinely works.
So it attenuated what we were not asking about and was invisible to what we were.

**An experiment that did not move the independent variable cannot test the dependent one.** The caveat
was in the kit's own adversarial pass **three days before the build flew** — *"below ~8 counts the filter
is essentially transparent"* — and was simply not applied when the drive was read. **The adversarial pass
did its job; the reading of the result did not.**

⇒ Corollary, alongside *a null from the wrong image is not a null*: **a null from a lever that was
transparent at the amplitude of interest is not a null.** An integer IIR with a `>>k` floor is the
standard offender — to be non-transparent at small amplitudes it needs a **fractional accumulator /
error-feedback remainder word**.

## ⭐ How every one of them was actually caught

**By an agent re-deriving a claim it had ALREADY REPORTED, and reporting against its own headline.**
Never by review, never by an adversarial pass aimed at it afterwards. Five instances in one session:

- `fwpath` reported V288's filter as "uniform, |H| = 0.457 applies to ALL inputs", went back, found the
  anti-stick branch, and **withdrew its own Q4 headline** — which voided the kit's standing verdict.
- `slewburst` generated an onset-locked pre/post asymmetry that read as a clean echo result (p = 0.003 on
  4/5 routes) and **killed it as confounded by construction**, because an onset *is* an envelope rise.
- `modelrate`'s first phase-lock detector **failed its own positive control** — a signal generated on the
  model clock scored *below* its null — and it diagnosed why (a staircase's 20 Hz component flips sign
  with the plan's slope, so a circular mean cancels; the square law is the correct detector). Later it
  **retracted a V288 falsification I had already relayed**, on sample-size grounds it found itself.
- `combsize`'s detuned-clock control **failed** (null floor 84 % of signal at 3 s windows, |Δf|·T = 1.1),
  so it **quarantined its own "COMB net = 7.51"** and rebuilt the headline on a method immune to it.
- `echoloop` **rejected its own rescue** of a sister agent's result by measurement, and separately
  corrected its own sign convention (`pid_log.output` is negated ⇒ critical point L = **+1**, metric
  |1 − L|, critical phase ~0°) — under the old convention the *safest* route reads as the most dangerous.

**How to apply.** Brief every agent to **re-derive its own load-bearing claim before reporting it**, and
to say so when the re-derivation disagrees. Ask explicitly for the **positive control to pass before any
null is quoted** — `modelrate` and `cyclekind` both stated that without it a null would just be a bug.
And demand the **failed controls** in the report, not only the successful ones.

## Two statistical traps that each cost a retraction here

- 🛑 **A low coherence/lock statistic on a SHORT stratum is a NON-DETECTION, not a zero.** R2's floor
  scales as 1/√N_eff: a 98.9 s stratum has floor 0.455 where a 182 s one has 0.161. **Measure the floor,
  debias (`R2_deb = √(max(R2² − mean(R2²_detuned), 0))`), report raw and debiased side by side, and state
  N_eff per stratum.**
- 🛑 **A detuned-frequency null does not decorrelate unless |Δf|·T ≫ 1.** At 3 s windows and Δf 0.37 Hz
  that is 1.1 cycles of slip and the "null" sits at 84 % of signal. Use **12 s+ windows.**

## And one framing error of my own, for the record

I put *"a Q ≈ 17 resonance rings 12–32× larger than its impulse"* into a brief and in front of the
operator. **False.** Q is the gain on a **sustained sinusoid**, not on an impulse: a unit-area impulse
peaks at ωn, so a 10 ms kick of height h rings to ≈**1.26 h**. ζ = 0.029 buys the **5.5-cycle length**,
not amplitude. The phase-locked accumulation ceiling is **1/(1 − e^(−2πζ)) = 6.00**, degraded by |cos ψ|.

Related: [[accord-v288-null-is-void-filter-was-transparent-at-the-ring]] ·
[[accord-episodes-of-hardcodes-the-18-22hz-gate]] ·
[[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]] ·
[[feedback-a-check-that-condemns-the-flown-build-is-broken]] ·
[[feedback-attribute-the-build-from-the-tap-not-from-the-label]]
