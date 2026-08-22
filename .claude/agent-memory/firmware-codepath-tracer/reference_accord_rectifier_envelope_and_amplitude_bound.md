---
name: reference_accord_rectifier_envelope_and_amplitude_bound
description: gp-0x6ac0's abs() (in FUN_00041464) runs AFTER a 54Hz-corner EMA, not before -- so it demodulates a still-oscillating 40-50Hz signal into a baseband envelope with nothing downstream to re-attenuate it. Only ~1.0 degree of column angular amplitude at 40-50Hz is needed to push the filtered/rectified gp-0x6ac0 past the cap table's first breakpoint (X=1050); ~3.7-4.3 degrees reaches the full Y=512 floor. The 4.7121 ct/(column-deg/s) scale is confirmed NOT a domain-confusion error (electrical vs mechanical) -- verified 3 independent ways.
metadata:
  type: reference
---

# The rectifier/envelope HF->LF coupling mechanism, and its amplitude bound (2026-08-22)

Companion to [[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]]. Raised by
team-lead against my own A4 finding: I reported `gp-0x6ac0`'s EMA corner (~54Hz, `FUN_00041464`,
`alpha=cal(0xC643C)/128=37/128`) as "too fast to be a 0.3-3Hz source" -- correct for a LINEAR resonator
hypothesis, but the real candidate mechanism is a DEMODULATOR, which the filter does not block.

## Why the order of operations matters
`FUN_00041464`'s body, in order: `target = raw<<10` -> **EMA filter** (`state_new = state_old +
((target-state_old)*alpha)>>7`) -> **`gp_6ac0 = abs(state_new)>>10`**. The `abs()` is APPLIED AFTER THE
FILTER, to the filter's OWN output, not to the raw input before filtering. A single-pole 54Hz-corner
low-pass only mildly attenuates a 40-50Hz signal (`|H(40Hz)|=0.807`, `|H(45Hz)|=0.773`,
`|H(50Hz)|=0.739` -- exact discrete EMA magnitude response, `H(f)=alpha/|1-(1-alpha)e^{-j2*pi*f/fs}|` at
fs=1000Hz), so the filtered state STILL OSCILLATES at 40-50Hz (at ~74-81% of its raw amplitude) going
into the `abs()`. The rectification then demodulates that still-oscillating signal into a baseband
envelope. **Nothing downstream re-attenuates that envelope**: `FUN_0007b022`'s own axis handling is a
bare instantaneous clamp (no temporal element, see companion memory), so a slow envelope component
(e.g. an amplitude-modulated grind bursting on/off over ~1s) passes through essentially unattenuated
into the cap-table lookup and hence into `gp-0x4f64`'s value.

## The domain check: 4.7121 ct/(column-deg/s) is NOT a units-confusion error
`gp-0x6ac0`'s NATIVE definition is `30 * f_electrical(Hz)` (from the confirmed 4kHz PWM/ADC chain,
[[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]]) -- genuinely electrical-domain at the
root. But the full gear-reduction P*G factor (pole-pairs x motor:column ratio, =56.5) is ALREADY folded
into the 4.7121 figure -- confirmed two independent firmware-derivation paths in
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp6abe_column_degps_scale_settled.md`:
(a) direct disassembly of the real CAN 0x14A/0x18F packers (`FUN_0003f776`, cal `0xC613A`=1159) tracing
to the externally-grounded STEER_ANGLE_RATE field, and (b) `30*f_elec` combined with `P*G=56.5`
reproduces 4.7121 to 4 sig figs. **Independent on-car cross-check**
(`memory/reference-accord-rate-scale-4p7121-stands.md`): a fitted scale against V74's flown probe peaks
at 5.80 [5.12, 8.27] -- same order of magnitude, not two orders off (which is what a real P*G-domain
confusion would look like -- the fit would land near 265 or near 0.08, not 5.8). **Verdict: 4.7121
stands, and reachability bounds computed with it are not a domain error.**

## The amplitude arithmetic
For a pure sinusoid at column-angle amplitude A (degrees) and frequency f (Hz), peak rate =
`2*pi*f*A` deg/s. Required RAW (pre-filter) amplitude to reach a cap-table breakpoint X, accounting for
the EMA's own attenuation `|H(f)|` at that frequency:
```python
alpha = 37/128; fs = 1000.0; SCALE = 4.7121   # ct per column deg/s
rate_postfilter_needed = X / SCALE            # deg/s, post-EMA
rate_prefilter_needed = rate_postfilter_needed / H_mag(f)
A_deg = rate_prefilter_needed / (2*math.pi*f)
```
| f | \|H(f)\| | A for X[0]=1050 (taper starts) | A for X[4]=4100 (Y=512 floor) |
|---|---|---|---|
| 40 Hz | 0.807 | 1.098 deg | 4.289 deg |
| 45 Hz | 0.773 | 1.020 deg | 3.984 deg |
| 50 Hz | 0.739 | 0.960 deg | 3.750 deg |

**~1 degree of column angular amplitude at 40-50Hz is enough to enter the taper; ~3.7-4.3 degrees
reaches the full collapse.** Cross-check against the kit's own measured ORDINARY steering operating
point: `gp-0x6ac0` in-burst p50 = 99 counts [94,113] (`analysis-2020accord/eps_chain_lanes.py`) -- under
10% of the way to X[0]. **Ordinary deliberate steering never gets close; the frequency-multiplication
effect (2*pi*f term) is what makes a small-amplitude high-frequency buzz reach what would otherwise
require ~230 deg/s of quasi-static wheel motion -- roughly 60-70x leverage vs quasi-static steering at
the same peak rate.**

## What remains open
Whether an actual "grind #3" event produces >=1 degree of column-angle amplitude at 40-50Hz is a
road/spectral question, NOT resolved this session (no rlog/spectral data pulled). The amplitude bar is
LOW ENOUGH that "implausible amplitude" is not a valid reason to kill the mechanism, but it is not
CONFIRMED live either -- this is the single number that would close it. Also open: `fVar48`'s actual
value in `FUN_0007b022`'s axis scale (BELIEF only that it's ~1 in steady state -- see companion memory),
and whether this is a genuinely nonlinear/nonresonant coupling means the kit's existing linear
loop-margin arguments (describing-function saturation reasoning, the V101 more-authority-is-worse
precedent) do NOT directly bear on it -- it needs its own falsifier.

## Related
[[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]] -- the full chain this mechanism
sits in, including the cap table and the state-gating that keeps it live during ordinary driving.
