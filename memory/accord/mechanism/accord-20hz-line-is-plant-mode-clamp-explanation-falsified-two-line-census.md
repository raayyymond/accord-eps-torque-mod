---
name: accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census
description: MODE-NATURE-RECENSUS 2026-09-09 (using V289's r62/r63) reconfirms the 2026-09-08 "20 Hz line is a lightly-damped PLANT MODE the LKAS rate loop de-damps, f pinned across Kp" verdict and STRENGTHENS it -- the clamp explanation for the Kp-pinning is directly falsified by measurement, and the 12-26 Hz census band is shown to hold TWO separable lines that must be split by LKAS DEMAND INDEX, not speed. V289's notch removed the 20 Hz line entirely (0/1414 present windows) rather than shifting it; a DIFFERENT pre-existing 15-17 Hz pole took its place.
metadata:
  type: reference
---

# The 20 Hz line is a plant mode (clamp explanation falsified); the census band holds two lines, split by demand — 2026-09-09

**Context.** After V289 (a phase-only edit: notch on the rate-loop's clamped output + fb lag pole
16.5→25 Hz, Kp/Kd/clamps/gain/map unchanged) flew and the grinding line moved 20.0 Hz → 15–17 Hz, an
interim reading argued the 20 Hz line must have been the loop's own CROSSOVER (since a phase-only edit
moved it), which would falsify the 2026-09-08 "pinned plant mode" verdict. `MODE-NATURE-V289-RECENSUS-
2026-09-09.md` (agent `modenat2`, 11 routes / 14,678 windows) resolved this. **Verdict: the crossover
inference was wrong; the plant-mode classification survives and is now better supported.**

## The census band contains two lines — gate on LKAS DEMAND, not speed

**EVIDENCE.** `idx` = the live assist-map demand index (0 = openpilot asking for ~nothing; ≥20 = the rate
loop working). Cross-tabbing f0 by `idx × speed`:
- **Low-demand line** (`idx < 5`): 12.4–13.8 Hz, falls with speed, ~4 raw of command amplitude, **same
  frequency on V282/V288/V289 and every Kp-LERP build** — a road/plant line indifferent to what the loop
  is doing.
- **High-demand line** (`idx ≥ 20`): 20.0 Hz on V278r3/V280r2/V281r3/V282/V288, **16.2–16.7 Hz on V289**,
  at every speed bin 0–20 m/s, carrying 15–40 raw of command amplitude — this is the grinding mode.

Pooling both without a demand gate drags every median to a spurious ~14.8 Hz — **the 2026-09-08 band
(15–26 Hz) avoided this by accident; a widened 12–26 Hz band does not, and must gate on demand.**
Independent confirmation with no census gate at all (pooled wheel-rate auto-spectrum, engaged/v<8m/s/
|bar|<400): V282 19.92 Hz (×3.4 over median), V288 19.92 Hz (×3.7), V289 16.80 Hz (×10.3).

## V289's notch removed the line; a different, pre-existing pole took its place

Demand-gated (`idx ≥ 20`) f0 histogram (1 Hz bins, present windows): V282 has 17/222/279/12/4 counts at
18/19/20/21/22 Hz; **V289 has 1/0/0/0/2** — **the 18–22 Hz band is EMPTY on V289: 0 of 1414 present
windows** (only 1 count at 18 Hz). ζ is unchanged: V282 0.029 median (CI 0.018–0.044), V289 0.029 median
(CI 0.019–0.040) — **the frequency moved, the damping did not.** The 15–17 Hz pole V289 now shows is
one V282 already carried at |L| 1.13 with ~30° of phase margin, which the notch's own skirt (−41.6° at
that frequency) plus the new fb pole (+11.5°) spent.

## The clamp explanation for the Kp-pinning is FALSIFIED

Matched-demand contrast (same load, same plant, flat-Kp vs Kp-LERP builds inside the same idx stratum):
Δf0 = **0.00 ± 0.15 Hz across Kp 248 → 696 (×2.81)**, while ζ **does** respond: 0.033 (Kp 240–320) → 0.030
(320–450) → 0.018 (450–700). Pushed through the byte-exact PID chain at each stratum's own measured ring
amplitude: **clamp binding is 0.0 % on D / sum / out clamps in every one of six strata**, including the
loudest. At 20 Hz the D clamp (`0xC61B6`=10240) needs a **32.4 deg/s** ring, the sum clamp needs 42.8
deg/s, the output clamp needs 218 deg/s — **measured rings are 3–8 deg/s at p50, 7–14 deg/s at p90.**
The clamps are nowhere near the line; a rising Kp reading as "pinned" because of clamp-limited effective
gain is dead. (A ×2.81 nominal Kp is only a ×1.52 loop-gain lever at 20 Hz once the D-term-dominated PID's
own phase lead is counted — it costs 26° of lead, from 61.4° at Kp 248 to 35.2° at Kp 696.)

**f pinned + ζ falling with gain is the root-locus signature of a loop closing on a lightly damped PLANT
MODE** (the locus departs the plant pole nearly horizontally) — not a crossover, which a −26°/×1.52 gain
change would necessarily drag downward (every plant family refit to V289 alone predicts exactly that
downward drag, and none of the four families' V282 fit puts |L(20 Hz)| ≥ 1 — all sit at 0.43–0.61, "not a
crossover"). No single LTI plant fits both the V289 move and the Kp-pinning jointly (best joint χ² 25.8;
the fits that honour the pinning get ζ wrong by 2–14×) — **the one-plant-one-pole model is what broke,
not the plant-mode classification.**

Sources: `rlog-tools/studies/grind/MODE-NATURE-V289-RECENSUS-2026-09-09.md` (§0, §1, §5b–5e),
`rlog-tools/studies/grind/GRIND1-CENSUS-V289-R62-R63-2026-09-09.md`.

**How to apply:** any future 12–26 Hz census on this loop must gate on LKAS demand index (`idx ≥ 20` for
the grinding mode; `idx < 5` for the road line), not speed or amplitude, or its pooled median will be
spurious (~14.8 Hz). Do not re-open the clamp explanation for Kp-pinning without new ring-amplitude
evidence — it is falsified at every tested stratum. See [[accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature]]
(supersedes that memory's "under adjudication" framing — the plant-mode picture is no longer in doubt) and
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]] (its "crosses unity 17–21
Hz" framing is not supported by this joint refit — every family's V282 fit sits at |L(20)| 0.43–0.61).
