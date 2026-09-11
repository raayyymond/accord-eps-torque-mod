---
name: accord-episodes-of-hardcodes-the-18-22hz-gate
description: "🛑⭐⭐⭐⭐ TOOL BUG: wire_0xe4_20hz.episodes_of hard-codes an 18-22 Hz amplitude gate, so it finds 12 and 15 episodes on the V289 routes where a band-aware detector finds 57 and 83 (or 225 corpus-wide). Every V289 rate comparison in the record is affected. Also: the live openpilot kp and latAccelFactor are NOT the config defaults."
metadata:
  node_type: memory
  type: reference
---

Three instrument defects found 2026-09-10 that will silently corrupt a future session's numbers.

## 1. 🛑 `episodes_of` hard-codes the 18–22 Hz gate

`rlog-tools/studies/grind/wire_0xe4_20hz.py`'s `episodes_of` uses `present = 15–26 Hz prominence ≥ 8 AND
bar 18–22 ≥ 40 raw`. **The 18–22 Hz amplitude term is hard-coded**, so the detector is **blind to any
relocated line** — exactly what V289 produced.

| detector | r62 | r63 | corpus |
|---|---|---|---|
| `episodes_of` (18–22 gate) | **12** | **15** | — |
| band-aware, same recipe otherwise (`fvlc_lib.py`) | **57** | **83** | **225 on V289** |

⇒ **Every V289 episode-rate number in the record computed with `episodes_of` is wrong**, and
`STATE.md`'s "V289 presence 2.1–2.2 %" is a **gate miss, not an improvement** (already flagged there).
**Use the band-aware detector** in `rlog-tools/studies/grind/fvlc_lib.py`, or pass the band explicitly.

**Band per build:** 18–22 Hz pre-V289 · **V289 is 15–18.5 Hz, and that is the cleanest of the three
candidates tested.** 13–18 catches the low-demand road line (median episode demand index 7.0 vs 13.2 at
15–18.5, f0 16.16 Hz); 14–18 is intermediate (10.0). Every conclusion is band-invariant across the three
(τ_c 0.345/0.385/0.410 s), but the **demand** column is not — so the band choice decides *which object*
you are scoring.

## 2. 🛑 The live openpilot gains are NOT the config defaults

Measured exactly from the rlogs, not fitted — `−(p+i+d+f)/output` is a hard constant (p5 == p95):

| route | build | kp | latAccelFactor |
|---|---|---|---|
| r35 | V281r3 | 0.6000 | **2.1100** |
| r39 | V282 | **0.8000** | **2.1100** |
| r5e / r62 / r63 | V288 / V289 | **0.9000** | **6.0000** |

- ⇒ **`memory/accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes.md` no longer holds for
  the recent routes.** `SteerKP` overwrites the PID's Kp every frame (`controlsd.py:449-450`), so this is
  a toggle the operator changed; 0.600 was presumably right when measured.
- ⇒ **carParams' `latAccelFactor` 1.68933 is NOT live**, and neither is torqued's filtered 2.46–2.50.
  🛑 **Any gain chain through `torque_from_lateral_accel` computed with 1.6893 is too large by ×3.6 on
  the recent routes.** This corrupted one agent's "one 0.1° angle LSB = 13.2 / 20.6 / 52.8 raw 0xE4
  counts" figures; corrected they are **3.92 / 7.58 / 21.97** at 5/15/30 m/s (net ×0.30–0.42:
  the kp rise 0.6→0.9 partly offsets the ×3.55 LAF rise).
  ⚠ The live 6.00 is outside torqued's cap band, so **ForceAutoTune is no longer driving it** — it looks
  as though [[accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps]]
  was acted on. BELIEF; the rlogs cannot show toggle state.

## 3. Two more premises that were recorded confidently and are false

- **`clip_curvature` never binds — 0.000 everywhere.** `STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`
  §2.1's "removes the raw staircase discontinuity before the PID ever sees it" is false in practice.
- **`jerk_filter` is transparent at 20 Hz** (|setpoint/F| = 1.000; 0.878 at 12 Hz, 0.943 at 26 Hz). The
  same §2 lists it as one of three command-smoothing stages. It should not be counted as one.
- **`pid_log.output` is the NEGATED torque** (`latcontrol_torque.py:725`) ⇒ the characteristic equation
  is `1 − P·K = 0`: **critical point L = +1, metric |1 − L|, critical phase ~0°, not ±180°.** The
  opposite convention makes the *safest* route look like the most dangerous one.
- **A second feedback path hides in the feedforward**: `latcontrol_torque.py:547`, `get_friction`'s
  argument contains the measurement, so the FF carries a parallel feedback branch worth **×1.04–3.35 on
  K**. Any outer-loop gain computed without it is low.
- **The naive `S(m,u)/S(u,u)` return-ratio estimator is biased toward −1/K in closed loop and
  MANUFACTURES |L| ≈ 1** — 0.265 vs an instrumented 0.017 on r35, 16× inflated, at a plausible-looking
  phase. Use a setpoint-instrumented (IV) estimator.

Related: [[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]] ·
[[accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it]] ·
[[accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes]] ·
[[feedback-a-check-that-condemns-the-flown-build-is-broken]]
