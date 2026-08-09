---
name: reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table
description: Full phase/magnitude table for every EMA pole in the plant-model/residual chain (FUN_0003b8f6 + FUN_00038148) at 7.79Hz/20Hz/21.09Hz — FUN_00038148's own outer EMA (0xC63AC=102) lands at the SAME alpha (~0.0996) as V86's 0xC40D4 target, a second never-touched phase-lag lever one stage downstream
metadata:
  type: reference
---

Computed 2026-08-09 (`fw-lever-census` task) by mirroring the decompiled integer/float arithmetic in Python: discrete first-order EMA `H(z)=α/(1-(1-α)z⁻¹)`, cascaded per the confirmed pole count (some cals apply the same alpha twice = a 2-pole cascade, confirmed by decompile not assumption), evaluated at fs=1000Hz (1kHz confirmed for FUN_0003b8f6; FUN_00038148/bc20/37fe6 = BELIEF-1kHz, inherited from the chain diagram, not independently re-verified).

| Element | α cal | value | poles | 7.79Hz mag/phase | 20Hz mag/phase | 21.09Hz mag/phase |
|---|---|---|---|---|---|---|
| Command-branch EMA | 0xC40D4 | 573 (stock) | 2 | -0.87dB/-33.25° | -4.57dB/-72.63° | -4.96dB/-75.25° |
| — | 0xC40D4 | 286 (V86 candidate) | 2 | -3.27dB/-65.36° | -12.06dB/-113.00° | -12.76dB/-115.21° |
| Sensor-branch EMA | 0xC40D8 | 3686 | 2 | -0.003dB/-0.62° | -0.017dB/-1.60° | -0.019dB/-1.68° |
| FRICTION's EMA | 0xC40D0 | 408 | 1 | -0.85dB/-23.63° | -3.86dB/-46.60° | -4.14dB/-47.90° |
| INERTIA's derivative EMA | 0xC40D6 | 246 | 2 | -4.21dB/-73.86° | -14.17dB/-120.40° | -14.92dB/-122.38° |
| **FUN_00038148's outer EMA** | **0xC63AC** | **102 (α=102/1024=0.0996, note: /1024 not /4096)** | 1 | **-0.85dB/-23.63°** | **-3.86dB/-46.60°** | **-4.14dB/-47.90°** |

★★★★★ **0xC63AC lands at essentially the SAME alpha (0.0996) as V86's `0xC40D4` stock corner (α=0.1399, close-ish) and its phase table is numerically IDENTICAL to 0xC40D0's** (coincidence of the two ratios 408/4096 and 102/1024 both reducing to ≈0.0996). 0xC63AC gates the WHOLE `SUM_6ch → EMA*16 → residual-compare` stage inside `FUN_00038148` (see [[reference_accord_fun38148_fun37fe6_channel_census_and_dead_lanes]]), i.e. it is a phase-lag pole ONE STAGE DOWNSTREAM of the estimator itself, not inside it. **Never touched by any build script (grep-confirmed).** If V86's `0xC40D4` move alone doesn't fully clear the 7.79Hz ratchet ([[accord-v85-flew-linear-loop-oscillation]] class hypothesis), 0xC63AC is a structurally distinct second EMA-pole lever of comparable size — genuinely novel relative to every prior build class (V38-52 authority/filters/caves, V53-61 telemetry, V62-73 rate lane, V74-83a damper). First time it has been named as a candidate.

**Cross-check / reconciliation note**: an existing (pre-this-session) figure for 0xC40D4 already on record — "7.79Hz: -0.87dB,-36.06deg | 21.09Hz: -4.96dB,-82.84deg (incl. 1-tick transport)" — reconciles EXACTLY with the bare-cascade number above plus one straight 1kHz-sample delay (`-360°×f/1000`): 33.25+2.80=36.05≈36.06; 75.25+7.59=82.84 exact. So that existing figure already bakes in one extra tick of pipeline handoff beyond the filter itself. **The table above is the bare filter only** — add ≈2.8°@7.79Hz / ≈7.6°@21Hz per extra 1kHz tick of cross-stage transport when chaining (e.g. FUN_0003b8f6 this tick → FUN_00038148 reading it next tick).

100Hz zero-order hold downstream (existing record): -37.6°/-75.2° at 21Hz (two accounting conventions on record, not re-derived here).
