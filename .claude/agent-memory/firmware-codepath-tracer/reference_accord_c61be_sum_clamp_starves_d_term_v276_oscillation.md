---
name: reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation
description: In FUN_00028ea6's LKAS rate PID, the post-gain sum clamp 0xC61BE (15360) is the REAL bottleneck on D-term authority, not D's own clamp 0xC61B6 -- P alone already fills 0xC61BE at low driver-override index, so D is discarded whenever it matters. Explains a reported 2-4Hz self-exciting LKAS oscillation on V276 (which raised the reference 6x without touching this clamp) ð CORRECTED BY ORCHESTRATOR 2026-09-01: raising 0xC61BE is NOT a zero-cost fix and MUST NOT be flown while an oscillation is active -- it RAISES delivered LKAS torque ~22.6% (2505 -> the 3072 cap) INTO an active limit cycle. It also does NOT restore linearity, because P's OWN clamp 0xC61BC is ALSO 15360, so P stays railed and you get saturated-P + saturated-D = a larger relay. And D cannot use the headroom: by this file's own arithmetic D saturates at |dErr|>20/tick (~2.9% of the error range at 3 Hz), so it is railed during an oscillation too. TREAT AS A SECOND-STAGE LEVER, for after the loop is stable, when the 2505->3072 headroom is real free authority. The PRIMARY lever is reducing the reference scale K, which is the only change that lets the error CHANGE SIGN again. Also documents 0xC61BE's sign-extension defect on its POSITIVE saturation branch specifically (0x2a146), and that 0xC61BE -- not 0xC61B4 -- is secretly the binding constraint on peak torque today (2505 actual vs 3072 nominal).
metadata:
  type: reference
---

# `0xC61BE` starves the D term; it is also the REAL peak-torque bottleneck (not `0xC61B4`)

Traced 2026-09-01 (GhidraMCP `disassemble_function` on `code.bin` @0x29d9c, register-level, plus a
fresh raw byte read of the V276 image). Function/region: `FUN_00028ea6`, the confirmed 1kHz LKAS
steering-RATE PID (see [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]]). This region is
byte-identical stock -> V268 -> V276.

## The chain, register-traced through `0x29d9c-0x2a174`

`sum = I>>7 + P + D` (r2 accumulates I>>7 @0x29f18, +P(r9) @0x29f1e, +D(r8) @0x29f24 -- traced by hand
because Ghidra's decompile reuses `r9`/`r27` across the P/D blocks and misreads easily).

- **P** = `clamp(32*err * Kp[variant](|req|) >> 8, +-0xC61BC=15360)`. Kp read fresh from V276, reachable
  slots 0-9 (per [[accord-variant-selector-max-is-nine]]): range 205-717, X breakpoints 0-208.
- **D** = `clamp((32*err_now - 32*err_prev) * Kd[variant](|req|) >> 3, +-0xC61B6=10240)`. Kd read fresh
  from V276 slots 0-9: **128 for slots 0,1,3,4,6,7,8,9; 64 for slots 2,5** -- NOT uniformly 128 (an
  earlier session's note that said "Kd=128 either way" only checked 2 of the 10 reachable slots).
- Then: `clamp(sum * LERP1(gp-0x6830) * LERP2(gp-0x682f) >> 16, +-0xC61BE=15360)` -> feeds the 5Hz-ish
  output LPF / hysteresis / engagement ramp / final clamp.

**LERP1/LERP2 read fresh from the V276 image (`0xCBB54/C34`, `0xCBAE4/BC4`, 28-slot pointer banks):
both are near-unity (Y=255/256) at LOW index** -- LERP1 (grab-rate) at index <=10, LERP2 (driver-torque
override) at index <=24-45. Gain only drops (LERP2 -> 51/256 =~ 0.2) once the driver-torque index rises
to ~96-112, i.e. once the driver grips firmly. This is an address-level match for "the oscillation stops
when I hold the wheel firmly."

## The bottleneck (EVIDENCE)

At near-unity combined gain, **P alone (max 15360) already equals `0xC61BE`'s clamp (15360)**. V276's
own build docstring independently confirms this was ALREADY nearly true pre-V276 ("P reaches 15360 in
all 28 slots where V268 stopped at 97.4%"). **Once P saturates, D's entire clamped range (+-10240) is
discarded by `0xC61BE` regardless of D's own headroom** -- raising `0xC61B6` (D's clamp) alone does
nothing. V276's x6 reference scaling didn't change this clamp topology at all, it just made the loop
spend far more of its operating range in the region where P alone already saturates `0xC61BE` -- turning
a chunk of the PID's operating range into a relay/bang-bang controller (P saturated + D discarded), a
textbook route to a self-sustaining limit cycle. This is offered as the mechanism behind an operator-
reported 2-4Hz self-exciting LKAS oscillation on V276 ("excites itself... even on straight roads...
only way to stop it is to hold the wheel very firmly") -- BELIEF for the causal link to the symptom,
EVIDENCE for every step of the clamp-topology chain itself.

**D saturation amplitude, quantified**: D_raw = 512*dErr per 1ms tick (Kd=128 slots), clamp +-10240 ->
saturates at `|dErr| > 20` raw-err-units/tick. For a sinusoid at freq f, `A_sat ~= 3183/f` raw-err-units.
At f=3Hz, A_sat~=1061 -- **only ~2.9% of V276's own error dynamic range** (+-36096 at max setpoint). D
saturates on almost any perceptible 2-4Hz error component; it is not providing continuous phase-lead
once an oscillation is underway.

## The sign-extension defect on `0xC61BE`'s POSITIVE branch specifically (EVIDENCE)

4 reader instructions of `0xC61BE` in this stretch: 3x `ld.hu` (zero-extend, safe to 65535) + **1x
`ld.h` at `0x2a146`** (sign-extend). Disassembly of `0x2a13e-0x2a174`:
```
0002a13e: ld.hu 0x71be[tp],r9      ; r9 = threshold (zero-ext, safe)
0002a142: cmp   r9,r12
0002a144: ble   0x0002a14c         ; if raw_sum <= threshold, skip positive saturation
0002a146: ld.h  0x71be[tp],r12     ; <-- POSITIVE saturation value, SIGN-EXTENDED
0002a14a: br    0x0002a174
0002a14c: ld.hu 0x71be[tp],r6      ; negative-branch threshold (zero-ext, safe)
...
```
The sign-extended read fires exactly on the **positive** overflow path -- the case that matters for
max positive torque demand. **`0xC61BE` must stay strictly < 32768**, or "positive saturation" becomes
a large NEGATIVE clamped value -- a sign-flip discontinuity at peak demand. This is the same defect
CLASS already documented for `0xC61B4`/`0xC61BE` in V276's own build script (which avoided touching
`0xC61BE` for exactly this reason), but here the SPECIFIC branch and instruction are pinned.

## `0xC61BE` is secretly the binding constraint on peak torque TODAY, not `0xC61B4`

Downstream chain (from [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]]): sum-clamp output ->
5Hz-ish LPF (`0xC63EC`/`EE`=992/507) -> hysteresis gate -> x engagement ramp -> final
`clamp((other_lane + gp-0x6b30) * gp-0x6752 * 0xC6CD0(5346) >> 15, +-0xC61B4=3072)`.
**At `0xC61BE`=15360, theoretical max reaching the final stage is `15360*5346>>15 = 2505`** -- 18%
below the operator's own frozen nominal cap of 3072. `0xC61BE`, not `0xC61B4`, is the real ceiling on
delivered torque right now.

## The fix this implies (proposed for V278, NOT built by this agent)

**Raise `0xC61BE` from 15360 to ~28000-30000** (covers full P(<=15360)+D(<=10240) sum without
re-saturating; stays safely under the 32768 sign-cap). This simultaneously (a) restores D's damping
headroom in the regime that matters and (b) closes the 18% authority shortfall above, WITHOUT touching
`0xC61B4`(3072)/`0xC6CD0`(5346)/the assist map -- i.e. without giving back any of the operator's kept
x6 authority (peak output stays clamped by the frozen `0xC61B4` either way, `30000*5346>>15 =~ 4894 >
3072`). Optionally also raise `0xC61B6` (D's own clamp, `ld.hu`-safe to 65535, no sign-cap issue) if D
should retain full authority even when P alone is near 15360.

**Do NOT partially back off `0xC62E6`** (the feedback clamp) as an alternative fix -- it clamps the
MEASURED rate, not the PID's internal saturation; backing it off makes the loop blind to fast wheel
motion exactly where damping is needed, the opposite of the goal, and breaks the Honda setpoint:feedback
ratio (1.395) V276 deliberately preserved.

## Also closed this session (V276 image, re-verified fresh)
- `0xC693E`(=358)/`0xC6384`(=2048): **do NOT touch the LKAS path** -- confirmed via
  `accord-assist-map-slope-cap-is-the-ratchet-lever`, a different lane (`clamp(gp-0x4f60)+gp-0x6b4a`,
  `0xC616C`=0 forces `gp-0x6b4a=0`). The orchestrator's brief had these as LKAS candidates; they are not.
- `0xC6974` (grab-rate taper): re-confirmed 4-knot flat `255,255,255,255`, INERT.
- `0xC63E8`/`EA` feedback lag pole (923/1560): fc ~= 16.5 Hz @ 1kHz loop -- too high a corner to matter
  at 2-4Hz.
- `0xC63EC`/`EE` output LPF (992/507): fc ~= 4.97 Hz, sits INSIDE this PID's own output path (between
  the `0xC61BE` clamp and the engagement ramp) -- a real secondary candidate for added 2-4Hz phase lag,
  separate from the `0xC61BE` fix above. Not GATE-2'd this session.

## Related
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] -- the base PID decode this extends.
[[accord-variant-selector-max-is-nine]] -- why only slots 0-9 matter for Kp/Kd/LERP1/LERP2.
[[reference-accord-v850-load-opcode-map-ldhu-0x3e]] -- ld.hu vs ld.h opcode identification used here.
