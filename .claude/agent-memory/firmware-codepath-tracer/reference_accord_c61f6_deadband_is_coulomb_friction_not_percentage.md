---
name: reference_accord_c61f6_deadband_is_coulomb_friction_not_percentage
description: 0xC61F6 (r24-only rate-lane deadband, stock=3) is confirmed a SUBTRACTIVE soft-threshold (shaped=scaled-D for scaled>D), which asymptotes to "unity gain minus a constant" -- a Coulomb-friction tax on r24's contribution, not a percentage cut, at any amplitude above D. Any dose large enough to plausibly reach the ~21.73Hz mode (D~100-1000+) is disqualified by the operator's explicit "don't add friction that rate-limits hard/fast steering" constraint, independent of whether it would even work.
metadata:
  type: reference
---

# 0xC61F6 rate-lane deadband -- full structural verdict (2026-08-22, `deadband` session, team-lead's evaluate-the-candidate brief)

## What it is, confirmed first-hand [EVIDENCE, fresh `decompile_function(0x3aa2c)` this session on `code.bin` stock,
cross-checked against 3 independent prior sessions in this memory dir + the golden model
`model/eps_chain_lanes.py:_inline_torque_rate_b`, all agreeing byte-for-byte]

`read_memory(0xC61F6)` = `03 00` LE = **3**. Reader: exactly ONE site, inside `FUN_0003aa2c` (the
aggregator), **on r24 only** -- r26 has NO deadband (confirmed: zero occurrence of `0x71f6` anywhere in
r26's block in the same fresh decompile).

```python
dtorque = clamp(gp_0x4f62, -5120, 5120)      # N=4 backward diff of RAW TORQUE SENSOR gp-0x4f60, shared with r26
scaled  = (dtorque * gain_q10) >> 10          # Q10; gain_q10 = 5244 when LKAS-engaged (0xC6446/Lever B,
                                               # confirmed carried unchanged into V104 AND V105's build scripts)
D = 3                                          # cal 0xC61F6, VIRGIN -- written by 0 of 65+ images (BUILD-LINEAGE Rule 4)
if   scaled >  D: shaped = scaled - D
elif scaled < -D: shaped = scaled + D
else:             shaped = 0
r24 = clamp(shaped * polarity(gp_0x6752), -8192, 8192)   # -> gp-0x6ada, post-clamp mirror
```

Form: **SUBTRACTIVE / soft-threshold** (`y = sign(x)*max(|x|-D,0)`), equivalently `y = x - sat_D(x)`.
Continuous everywhere (Lipschitz-1, no jump at |x|=D) -- structurally cannot inject new relay/switching
harmonics the way a hard dead-zone or relay could.

`gp-0x6ada` confirmed **zero readers, two independent methods** this session: the decompile shows exactly
one store and no loads in the whole function; `search_instructions(operand_pattern="6ada")` across all
183,570 analyzed instructions returns exactly one real data hit (that same store; 5 other hits are
coincidental branch-target substrings in an unrelated function, `FUN_0006ac1a`). `get_xrefs_to` on the
resolved address (`0xFEDF1526`) returns 0 -- the known gp-relative blind spot; corroborated here, not
contradicted, by the instruction-text scan. **Genuinely free, zero-GATE-1-risk telemetry**, unused by
every build to date.

## 🛑🛑 THE DECISIVE FINDING -- this is a Coulomb-friction tax, not a percentage cut

`shaped = scaled - D` for ANY `scaled > D`, no matter how large `scaled` gets. As `scaled -> infinity`,
`shaped/scaled -> 1` -- the asymptotic behavior is literally **"unity gain minus a constant"**, the exact
mathematical definition of Coulomb friction (constant opposing term, independent of magnitude) versus
viscous friction (proportional). This is NOT a percentage-cut nonlinearity, and describing-function
framing (percentage passed vs amplitude, which DOES shrink toward 0% as amplitude grows) understates the
real cost: **the ABSOLUTE tax stays fixed at exactly D counts every 1kHz cycle that `|scaled|>D`, for as
long as the maneuver continues** -- it never asymptotes to zero the way a proportional (gain) reduction
would.

Sized against reference scales, at doses large enough to plausibly matter for a 21.73Hz mode (see below):
```
D      % of r24's own clamp (8192)   % of aggregator clamp (10240, gp-0x6b94, confirmed this session)
100          1.22%                              0.98%
300          3.66%                              2.93%
1000        12.20%                              9.77%
```
This is a standing, always-on tax whenever the driver/LKAS produces ANY meaningful torque-rate -- not
targeted to the oscillation.

**This independently disqualifies the candidate against the operator's explicit constraint** (his words,
2026-08-22): *"Damping is fine. I just don't want this to become so much friction that even a 6x DC
torque signal gets steer angle rate limited... the point of the torque mod is to be able to turn the
steering wheel harder AND faster."* Not literally a `dOutput/dt` rate limiter (structurally it's an
additive-lane offset, not a clamp on a derivative) -- but the LKAS command r24 feeds through
governor->comp-add->shaper is itself capped downstream (±0x2000/0x3000 per `FUN_000074c4[tp+4]`, see
`[[reference-accord-integrator-update-form]]`); if that cap is approached during hard/fast 6x maneuvers
(plausible -- 6x exists specifically to maximize authority), a persistent D-count tax on one contributing
lane could produce an effective rate ceiling well before the firmware's own explicit limiters would.
**[BELIEF for this specific mechanism -- no headroom-margin measurement during hard 6x maneuvers exists to
confirm how close to the cap the system runs.]** The structural fact (constant tax, not a percentage) is
EVIDENCE regardless of whether this exact downstream-cap mechanism is what the operator is feeling.

## Is the mode even inside the deadband at D=3 (stock)? [BELIEF, no direct on-car measurement exists]

No build has ever tapped `gp-0x6ada` -- there is no direct measurement of `x` (=`scaled`, what the
deadband gates). From the analytic chain: only on-record pre-gain input measurement is V65's
`|dtorque| in [123,839]` over 120,049 frames (general driving, different build/route, not burst-specific,
see `studies/models/orch_c6446_clamp_headroom.py`). At the CURRENT gain (5244), `x` ranges **629-4296** even during
ordinary (non-oscillating) driving -- **D=3 is 0.07%-0.48% of that**, i.e. structurally invisible by
2-3+ orders of magnitude. (Corrects this dir's own `[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]]`,
which computed "D is 0.4-2.4% of typical excursion" against the PRE-gain `dtorque` directly rather than
against `x`, the actual post-gain quantity D is compared to -- with the current 5.12x-effective gain the
correct fraction is ~5x smaller than that file states. Not yet corrected in that file pending team-lead's
call, per the ask-before-updating-stale-memory rule.)

N=4 differencer's own gain, exact, at the OPERATOR-CONFIRMED line (2026-08-22 correction: the symptom
band is ~21Hz / 18-22Hz "grind #1", measured 21.73Hz on route `0x9e` -- NOT the previously-used pooled
21-28Hz figures):
```
|H(f)| = sin(2*pi*f*N/(2*fs)), fs=1000Hz, N=4
 1.00 Hz  |H|=0.01257
 1.50 Hz  |H|=0.01885
21.73 Hz  |H|=0.26969   <- 21.5x the 1Hz gain, 14.3x the 1.5Hz gain, for the SAME underlying torque amplitude
```
A 21.73Hz oscillation, if it has any real torque-sensor signature (physically plausible -- the sensor
sits on the same shaft), gets pushed toward or past the top of the 629-4296 ordinary-driving range by the
differencer's own frequency response, not the bottom.

## V80/RULE 14 check, done directly against this decompile

r24/r26 do **NOT** carry the "zero-reject if out of range" cliff pattern (`x * (x+K<2K+1)`) that
`gp-0x6ad4`/`gp-0x6b26`/`gp-0x6bbe`/`gp-0x6bd0`/`gp-0x6b86` all carry when re-summed into the aggregator --
confirmed directly in the fresh decompile: `iVar21`/`iVar16` (r24/r26) are added into the sum with no such
gate (they're fresh locals computed in the same function, not values crossing a function boundary via
RAM). **Raising D also can't newly trigger this cliff** -- it only ever shrinks magnitudes, moving away
from any zero-reject threshold, never toward one. The specific V80 "one count past the cliff -> full
dropout" mechanism does not recur here. [EVIDENCE]
But there IS a related degradation: as D grows toward r24's own 8192 clamp, it compresses the lane's
live/nonzero input range toward that same clamp -- at D=1000+, r24 does effectively nothing until
`dtorque*gain` is already large, then engages over a narrow remaining window. Not a relay (still
continuous, no jump), but the same family of shape-degradation as V80: a graded lane turning into a
late-onset, steep one.

## Sign context -- why raising D may be removing a damper, not a pump [BELIEF, extrapolated]

Per `[[reference_accord_r24r26_driver_torque_lane_reZ_estimate]]` (same dir, corrected same-day for the
now-CONFIRMED `gp-0x6752=-1`): the cross-spectral Re(Z) estimate for r24/r26 (same sign, same input) is
**PUMP at 6-9/9-12Hz but DAMP at 12-31Hz** -- which contains the 21.73Hz line. If that sign holds, r24 is
currently part of what's fighting the resonance, not sustaining it, so raising D doesn't remove a pump,
it partially removes a (weak, unmeasured-magnitude) damper -- the opposite mechanism from the one
motivating this candidate.

## Verdict
**Dead as specified.** D=3 is structurally invisible to the mode (2-3+ orders of magnitude too small);
any dose large enough to plausibly matter is a standing Coulomb-friction tax disqualified by the
operator's explicit "don't add friction that costs rate authority" constraint, independent of whether it
would even suppress the mode. GATE 1 vacuous (pure existing-cal edit, no new RAM). Highest-value next
step if this lane stays interesting: add `gp-0x6ada`/`gp-0x6adc` to telemetry (free, zero new GATE-1 risk,
confirmed zero readers) before ever proposing a dose here again.

## Related
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]] -- original disassembly this session's
decompile reconfirms byte-for-byte; contains the now-corrected pre-gain-vs-post-gain fraction error.
[[reference_accord_lever_a_gate_structure_and_cal_double_equivalence]] -- the gate/gain-selector structure
this file's `gain_q10=5244` reuses.
[[reference_accord_r24r26_driver_torque_lane_reZ_estimate]] -- the sign estimate this file's "damper not
pump at 21-31Hz" conclusion is built on; BELIEF-tier, not measured.
[[reference-accord-integrator-update-form]] -- the downstream `FUN_000074c4[tp+4]` command cap this file's
rate-limiting mechanism argument depends on.
[[reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor]] -- confirms r24 is upstream of the
SM3 integrator by several stages (aggregator -> governor -> comp-add -> shaper -> integrator), so the
classic deadband-inside-integrator hunting/windup hazard does not apply in the firmware-loop sense (r24
isn't part of the integrator's own error/envelope definition) -- the physical mechanical-loop concern and
the Coulomb-friction feel cost above are the operative hazards instead.
