---
name: accord-liveparameters-steerratio-is-published-upstream-of-the-accord-scale
description: 2026-09-04. "SteerRatio measured on the wire" is NOT sufficient - liveParameters.steerRatio is published UPSTREAM of StarPilot's Accord scale, so the ratio the loop ACTUALLY used can differ from the logged one. On r31/r32/r33 the param sat at the stock 16.33, which makes accord_ratio_is_explicit FALSE (controlsd.py:471 requires |param - CP.steerRatio| > 0.01 and CP.steerRatio IS 16.33), so HONDA_ACCORD_STEER_RATIO_SCALE = 14.0/16.33 = 0.857 was applied - while ForceAutoTuneOff was off, so paramsd was LEARNING and lpar_sr wandered to 16.38-16.51, a number that looks like truth and is not what the loop used. Effective ratio on those three routes was ~14.05, a 1.21x measurement inflation nobody knew about. THE TEST: reconstruct actualLateralAccel from the vehicle model twice, once at sR = lpar_sr and once at sR = 0.857*lpar_sr, and TLS each against the logged channel - slope 1.000 identifies the ratio the VM actually ran. r31/r32/r33 reproduce ONLY with the scale (0.996/1.006/1.003); r34/r35/r36/r38 reproduce ONLY without it (1.000/1.000/1.003/1.002). Anything computed on r31/r32/r33 from openpilot's own measurement/error/f-p-i decomposition is biased; torque-to-pose quantities are SR-free and survive.
metadata:
  type: reference
---

# `liveParameters.steerRatio` is published UPSTREAM of the Accord scale — the logged ratio is not always the ratio the loop used — 2026-09-04

## The trap

`controlsd.py` computes, in this order:
```python
sr = max(lp.steerRatio, 0.1)                          # <-- what gets LOGGED
accord_ratio_is_explicit = use_custom_steerRatio and abs(custom - CP.steerRatio) > 0.01
...
elif carFingerprint == HONDA_ACCORD and not accord_ratio_is_explicit:
    sr *= get_honda_accord_steer_ratio_scale(v_ego)   # = 14.0/16.33 = 0.857
self.VM.update_params(x, sr)                          # <-- what the LOOP uses
```
**`liveParameters.steerRatio` is the value BEFORE the scale.** So reading it off the wire tells you what `paramsd` produced, **not** what `VM.calc_curvature` ran with. The two differ by 0.857 whenever the Accord branch fires.

🛑 And the branch fires **exactly when the param is left at the platform default**, because the Accord's `CP.steerRatio` **is 16.33** (`opendbc/car/honda/values.py:188`) and the gate needs `|param − 16.33| > 0.01`. Setting the param to the "correct" 16.33 therefore *disables* the explicit flag and *applies* the 0.857 — see
[[reference-starpilot-fork-updater-has-no-allowlist-and-the-16-33-steerratio-trap]].

## It already happened, on three routes

| route | build | logged `lpar_sr` | recon @ `sr` | recon @ `0.857·sr` | **effective sR** |
|---|---|---|---|---|---|
| r31 | V278 r3 | 16.51 | 1.1835 | **0.9962** | **14.16** 🛑 |
| r32 | V280 r2 | 16.38 | 1.1556 | **1.0062** | **14.04** 🛑 |
| r33 | V280 r2 | 16.41 | 1.1691 | **1.0034** | **14.07** 🛑 |
| r34 | V280 r2 + new tune | 16.10 | **1.0003** | 0.8658 | 16.10 clean |
| r35 | V281 r3 | 12.50 | **1.0001** | 0.8657 | 12.50 clean |
| r36 / r37 / r38 | V283 | 12.50 | **1.0030 / 1.0006 / 1.0018** | ~0.862 | 12.50 clean |

The compounding detail: on r31/r32/r33 `ForceAutoTuneOff` was **off**, so `paramsd` was *learning* and `lpar_sr` drifted to 16.38–16.51 — **a plausible-looking number that was never used.**

## 🛑 THE TEST — use it before trusting any SR-derived quantity

Reconstruct `actualLateralAccel` from the vehicle model **twice** — once at `sR = lpar_sr`, once at `sR = 0.857 · lpar_sr` — and TLS each against the **logged** channel. **Slope 1.000 identifies the ratio the VM actually ran.** It is self-controlling in both directions: the clean routes reproduce *only* without the scale, the tainted ones *only* with it.

## What is tainted and what survives

- **TAINTED on r31/r32/r33:** anything derived from openpilot's own `measurement` / `error` / f-p-i decomposition — a **1.21× inflation** sits inside it. Check before re-using any `error`-based result from those routes.
- **SURVIVES:** torque↔pose quantities, which contain no steering ratio on either side — including the 2026-09-02 back-calc's `LAF_true` and its friction/deadband figures.

## The companion distinction — GEOMETRIC vs EFFECTIVE ratio

Two different quantities, both measured, and they are **not** interchangeable:
- **Geometric ≈ 16.0** near centre (the rack map: wheel-speed / differential / yaw, **no tyre model**).
- **Effective ≈ 16.7** (the ratio that makes `VM.calc_curvature` match the road; it **absorbs carParams tyre-stiffness error** through `curvature_factor`).

Gap **1.04**. **The loop closes on `calc_curvature`, so the EFFECTIVE ratio is what zeroes the bias** — deploying the geometric map leaves ~4 % residual under-delivery. Ship it anyway (4 % against 28 %), but ⚠ **do not scale the rack map by 1.04 to close it** — that launders a tyre-model error into a geometry table, and the gap is speed-dependent by construction so a scalar cannot remove it everywhere. The principled fix is tyre stiffness in `carParams`.

⭐ Worth noting for orientation: the rack's true ratio is **12.8 at 236°**, so **`SteerRatio 12.5` is roughly the rack near LOCK applied at every angle** — the same *shape* of error as StarPilot's own `14.0/16.33` constant, which is the rack at ~95°. Both are truthful somewhere the car is not being lane-kept.

Related: [[accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps]],
[[feedback-attribute-the-build-from-the-tap-not-from-the-label]] (same family of error: the label is not the measurement),
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]].
