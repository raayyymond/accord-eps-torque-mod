---
name: accord-clamped-loop-parametric-modulation-hazard-v290-kd-schedule-safe
description: The CLAMPED, quantised LKAS rate-loop integer mirror is far more susceptible to a Kd parametric pump than a linear Floquet/Lyapunov analysis of the same loop predicts (nonlinear worst-case decay cut to 0.37-0.42x at a full-swing synthetic square wave, vs a linear worst-case excess of only +3.8e-4/tick, ~2%) -- so a linear-only parametric analysis would give a false all-clear. The specific V290 Kd-schedule candidate (row S, 96<->128 ramped over demand idx 22-32) is measured safe on BOTH axes: its crossing rate (1.2-3.5/s) sits an order of magnitude below the measured nonlinear danger band (2.0-39.2 Hz) and its depth (duration-weighted eps 0.002-0.007, worst single episode 0.027) sits 8-500x below the instability threshold (eps~1.035 linear / eps 0.1286 = row S's own maximum, 8.1x below that threshold). 2026-09-09.
metadata:
  type: reference
---

# A clamped loop is far more susceptible to parametric modulation than its linear reading — V290's Kd candidate is safe on both axes — 2026-09-09

**The general hazard (EVIDENCE, from agent `paramod`'s finished write-up
`docs/review/V290-PARAMETRIC-HAZARD-2026-09-09.md`, verified line-by-line against the on-disk script
outputs it cites — see Sources below).**

The LKAS rate loop's Kd term is scheduled by a demand-indexed LERP (`0xE511C`, see
[[accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb]]); any edit to that schedule makes Kd a
function of time as the driving demand crosses its knots — a textbook parametric-modulation setup. A
**linear** Floquet/Lyapunov analysis of the loop (87 burst-consistent plant fits, square-wave Kd 96↔128,
every modulation frequency the 100 Hz wire can carry) finds the hazard small: worst per-fit excess over
the frozen-Kd LTI reading is **+3.759e-4/tick at 39.25 Hz duty 0.25** (a 2f tongue at 2× V282's 20 Hz
ring, exactly where parametric theory puts it), highest ρ anywhere in the sweep 0.998423 (margin to
instability 0.0016) — genuine but far too weak to matter at any modulation the schedule can produce.

**But the CLAMPED, quantised integer mirror (the check a linear analysis structurally cannot make) is
MORE susceptible**: the same full-swing 96↔128 square wave at its own worst frequency/duty cuts the
ring's decay rate to **0.37–0.42× the constant-Kd-128 reference** (worst at 20.0 Hz duty 0.15: decay
0.430 vs reference 1.152; also at 39.25 Hz duty 0.25: 0.482) — a factor the linear analysis's +3.8e-4/tick
excess (~2% decay loss) badly understates. ⇒ **a linear-only parametric analysis of this loop would give
a false all-clear; the nonlinear clamp/quantisation check is required.**

**The measured (not synthetic) danger band, from the clamped mirror:** any modulation frequency costing
>20% of ring decay at FULL 96↔128 swing spans **2.0–39.2 Hz** (worst points at 20.0 and 39.25 Hz).

**The instability threshold, from the re-optimized linear depth sweep (frequency AND duty re-searched at
each depth):** the 2f tongue only opens (any of 87 fits unstable) at swing 118 (Kd 10↔128), **eps ≈
1.035** — a near-total gain modulation, far beyond anything a Kd LERP row can deliver (Kd's own floor is
Y≥0; a real schedule cannot go below its programmed low knot).

**The specific V290 candidate (row S, `Kd Y=[96,96,96,128]` ramped over demand idx 22–32) is measured
safe on both the frequency and the depth axis:**
- **Crossing rate.** Measured knot-crossing rate on the wire, inside census grinding episodes: **1.2–3.5
  crossings/s** — an order of magnitude below the 2.0 Hz lower edge of the measured nonlinear danger band.
- **Depth.** Row S's absolute maximum possible modulation depth (full 96↔128 swing, more than the LERP
  ramp actually produces) is **eps = 0.1286 — a factor 8.1 below the eps≈1.035 instability threshold.**
  The depth actually measured on the wire at 2f, duration-weighted over census grinding episodes, is far
  smaller still: **eps 0.0021–0.0071 per route** (r62/r63/r5e/r39: 0.0021/0.0048/0.0071/0.0052), **worst
  single episode 0.0266** (r5e) — **a factor 38×–490× below threshold** (report's own rounding of
  eps≈1.035 ÷ these figures).

Row S also keeps `Y[3]=128`, so it is byte-identical to V282 above idx 32 (where the lookup takes its
high-clamp branch) — the 7 Hz strong-turn gate and capped-step authority are ×1.000 by construction.

**Clarification kept from an earlier reconciliation pass, and still correct:** **eps ≈ 0.1286 is what row
S's own maximum 96↔128 swing DELIVERS, not the instability threshold** — the threshold is **eps ≈ 1.035**
(swing 118, Kd 10↔128), a near-total gain modulation no real Kd schedule can reach. Do not conflate the
two eps figures.

Sources: `docs/review/V290-PARAMETRIC-HAZARD-2026-09-09.md` (agent `paramod`'s finished write-up, written
2026-09-09 21:25:41) is the source of record for every number above. Its own cited scripts —
`rlog-tools/studies/grind/paramod_v290_floquet.py` → `_scratch/paramod_v290_floquet.txt`/`.json`
(written 21:25:19, 22 s before the report) and `paramod_v290_modulation.py` →
`_scratch/paramod_v290_modulation.txt`/`.json` (written 21:17:42) — reproduce the report's tables to full
precision on direct inspection of the JSON (threshold row swing=118/eps=1.0354/7-of-87-unstable, row-S row
swing=32/eps=0.1286/excess=3.759e-4, `nlsweep` ratios 0.3737 at 20 Hz and 0.4187 at 39.25 Hz — all match
the report to 3+ significant figures). The script is deterministic (no randomness in the Floquet/Lyapunov
math), so these numbers hold regardless of which agent's invocation last wrote the `_scratch` files.

**How to apply:** for any future scheduled-gain (Kp/Kd/other LERP) edit on an in-loop cell, run BOTH the
linear Floquet/Lyapunov check AND the clamped/quantised integer-mirror nonlinear check — the linear check
alone is not conservative here. Compare the measured wire crossing-rate and eps-depth against the
nonlinear danger band and threshold before flying, not the linear ones. See
[[accord-parametric-pump-intervention-never-run]] (the kit's one MEASURED parametric pump, V59's boost-index
2f pump into the 21 Hz mode, a different mechanism — amplitude-index rectification, not a scheduled-gain
LERP — but the same "parametric coupling into a lightly-damped mode" hazard class) and
[[accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census]] (the mode this hazard would
couple into).
