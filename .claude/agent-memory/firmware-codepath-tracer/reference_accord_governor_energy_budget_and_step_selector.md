---
name: reference-accord-governor-energy-budget-and-step-selector
description: Governor's energy/thermal-budget accumulator is structurally unreachable at any calibrated command magnitude (ceiling cal=0); governor's slew-STEP selector IS driver-torque-dependent via gp-0x6a5e/gp-0x6a62's producer FUN_00041eec. gp-0x6ba4 identity resolved as |delivered torque|.
metadata:
  type: reference
---

# Governor non-cap terms — energy budget + STEP selector — Accord TVA-A160

Traced 2026-07-19 in response to a team-lead request investigating the governor's non-cap terms as a
possible tens-of-Hz vibration modulator (V38 4x-gain hard-turn/vibration investigation). Two functions:
`FUN_0007b022` (producer of the governor cap `gp-0x4f64`, decompiled in full — 1263 decompile lines) and
`FUN_0004503c` (`m_motor_torque_governor`, the consumer that turns the cap into the per-cycle slewed
output `gp-0x6ace`). Ghidra decompile + byte-level cal reads against `code.bin` (stock structure) and
`_v38_plain_image.bin`/`_v42_plain_image.bin` (cal values — all three IDENTICAL on every cal below,
none touched by any build in the V9-V42 lineage).

## 1. gp-0x6ba4 identity RESOLVED: |delivered torque command|

**[VERIFIED]** `gp-0x6ba4` is written at `0x43c0c` inside the shaper `FUN_00042af8`, immediately after
its FINAL ±0x2000 hard clamp (`r21`, the same value written to `gp-0x6b98`/delivered torque at
`0x43b52`):
```
00043bf4: cmp r0,r21
00043bf6: mov r21,r12
00043bfc: bge 0x00043c00
00043bfe: subr r0,r12          ; r12 = |r21|
00043c00: ld.hu -0x6ba4[gp],r15  ; lockstep prior-value read
00043c04: ld.hu -0x4ce6[gp],r6
00043c08: cmp r6,r15
00043c0a: bne 0x00043c16         ; mismatch -> FUN_0006b9fa fault
00043c0c: st.h r12,-0x6ba4[gp]   ; gp-0x6ba4 = |delivered torque|
00043c10: st.h r12,-0x4ce6[gp]   ; lockstep mirror
```
This resolves a previously-unidentified variable used elsewhere: the engage-SM decider's `dec_gate7`
(cal `0xC61CC`=3584, "verdict 7") in `FUN_00040d58` and the angle-deadband trampoline `FUN_0003c3c6`
both gate on **the magnitude of the currently-delivered torque command**, not a separate sensor.

## 2. Energy/thermal-budget accumulator — structurally UNREACHABLE at any calibrated magnitude

`FUN_0007b022` computes `gp+0x128` (one of 3 MIN operands forming the governor cap `gp-0x4f64` in
branch-1/steady-state-LKAS mode — see [[reference-accord-governor-gp0x184-chain]]) via a genuine
hysteretic accumulator:

- **Charge trigger**: `fVar53 = gp-0x6ba4 / 1024` (delivered-torque magnitude, from §1) compared against
  **threshold `fVar64 = cal 0xC509E / 1024`**. `0xC509E = 5325` (stock/V38/V42 identical) → threshold =
  **5325 raw counts**.
- **Charge/discharge**: `fVar43 = (fVar53-fVar64)^2` (squared error). If `fVar53 > fVar64`: accumulator
  `fStack_48 += cal(0xC5128)/16 * fVar43` (charge gain = 1024/16 = **64.0**). If `fVar53 <= fVar64`:
  `fStack_48 -= fVar43` (unity-rate discharge).
- **Hysteresis latch `gp-0x285f`**: rising edge when `fStack_48 >= cal(0xC5164)` (the "ceiling"), falling
  edge (reset to 0, clear latch) when `fStack_48 < 1`.
- **⚠ Ceiling cal `0xC5164 = 0`** (stock/V38/V42 identical). This COLLAPSES the intended hysteresis band:
  the rising edge fires the instant the accumulator would go non-negative (i.e. on the very first
  charging cycle, since it's clamped back to exactly 0 = the ceiling every time it fires), and the
  falling edge fires the instant it would go negative. **There is effectively no real multi-cycle
  wind-up — this reduces to a same-cycle/one-cycle-lag comparator on `fVar53 > fVar64`, not a slow
  accumulator**, regardless of the 64x charge gain.
- **Structural unreachability**: `gp-0x6ba4` (§1) is the shaper's POST-governor-clamp delivered torque
  (governor clamp #6 is applied BEFORE the final ±0x2000 hard clamp #7 in `FUN_00042af8` — see
  [[reference-accord-shaper-fun42af8]]), so `gp-0x6ba4 ≤ gp-0x4f64 ≤` governor nominal ceiling
  **cal 0xC6202 = 4762** (see [[reference-accord-governor-gp0x184-chain]]) in ALL steady-state
  operation. **4762 < 5325** — the charge threshold is unreachable by construction, independent of LKAS
  gain. V38's ~4342-count sustained command and stock's ~417-count command are BOTH far below it.
- **VERDICT: this mechanism CANNOT be the tens-of-Hz vibration source under the current calibration** —
  disconfirmed, not just untriggered-in-practice. The only lever that could ever activate it is raising
  `0xC6202` toward/above 5325, which is independently rejected per CLAUDE.md's governor-raise audit.

## 3. Second energy term (gp+0x13c / fVar54) — a low-pass, not an oscillator

A SEPARATE current-based term (`fVar47²+fVar52²` and `fVar34²+fVar46²`, likely FOC Id/Iq-style vector
magnitudes from `gp-0x6c1a/6c1c/4f0a` and `gp-0x4f6a/6c/6e/70` — sources NOT individually identified)
feeds a **32-sample ROLLING MEAN** (two parallel ring buffers, cross-validated via a float "almost-equal"
lockstep compare), multiplied by `cal 0xC5638 = 30544` (≈0.4661 in the /65536 domain). This becomes
`gp+0x13c`, the third MIN operand for the governor's branch-1 cap (`gp+0x1a4 = MIN(gp+0x130, gp+0x128,
fVar54)`). **No SET/CLEAR latch structure — this is a plain moving-average low-pass**, consistent with
the already-documented `gp-0x3d3c` arbitration IIR
([[reference-accord-lkas-lane-is-a-lowpass]]): a 32-sample MA at either contested loop rate (100 Hz or
1 kHz — task rate is UNRESOLVED per `eps_lkas_chain_model.py`) is a low-pass, not a source of tens-of-Hz
content. Not a relaxation-oscillator candidate.

## 4. Governor slew-STEP selector `gp-0x67f5` IS driver-torque-dependent — [VERIFIED]

**[VERIFIED]** In `m_motor_torque_governor` (`FUN_0004503c`, `0x45402-0x45416`):
```c
if (*(char *)(unaff_gp + -0x67f5) == '\0') {
    uVar9 = *(ushort *)(unaff_tp + 0x7206);   // STEP = cal 0xC6206 = 512  (FAST)
} else {
    uVar9 = *(ushort *)(unaff_tp + 0x7208);   // STEP = cal 0xC6208 = 205  (~2.5x SLOWER)
}
```
`gp-0x67f5` has **zero direct reads inside FUN_0004503c or FUN_0007b022 of any of {gp-0x6a5e, gp-0x6a62,
gp-0x682f, gp-0x4f60, gp-0x6bf0}** (confirmed by exhaustive `search_instructions` scoped to both
functions — 0 matches each), so the governor functions themselves don't read driver torque directly.
**But `gp-0x67f5`'s SOLE writer is `FUN_00041eec`**, which is a 5-channel voting/slew/debounce pipeline
that ALSO produces `gp-0x6a62` and `gp-0x6a5e` — two of the operator-question's named driver-torque
candidates, and `gp-0x6a62` is CLAUDE.md's documented "Sensor-A column-torque voter" (used elsewhere as
the V33 gentle-EME gate `gp-0x6a62 >= cal 0xC6312`).

Mechanism inside `FUN_00041eec` (`0x42260-0x42296`):
- `puVar29` = a rate-limited/voted version of `uVar4 = gp-0x6a5e` (5-channel min/max/average voting over
  `gp-0x6a44/6a40/6a3c/6a38/6a46`, then its OWN slew limiter using LERP-table step sizes `uVar20`/`uVar17`).
- Debounced threshold compare: **`puVar29` vs `cal 0xC531E = 1062`**, hold count **`cal 0xC64E7 = 10`
  cycles** (same hold count both directions):
  - `puVar29 >= 1062` sustained 10 cycles → `gp-0x67f5 = 1` (governor STEP → 205, SLOWER)
  - `puVar29 < 1062` sustained 10 cycles → `gp-0x67f5 = 0` (governor STEP → 512, FASTER)
  - Reset state `gp-0x67f5 = 0xFF` also routes to the slow (205) branch (only literal `== 0` selects fast).

**Physical reading: when the driver-torque-voted signal is LOW (hands-off-ish) sustained, the governor
slews its output FASTER (STEP 512); when driver torque is HIGH (hands-on) sustained, the governor slews
SLOWER (STEP 205, ~2.5x more damped).** This is a genuine driver-torque-dependent term inside the
governor's own rate-limiting behavior, and it points the RIGHT direction for the operator's report
("vibration vanishes when driver adds hand torque") — hands-off gives less filtering (faster tracking of
whatever target the redundant-channel voting/clamp bounds produce), hands-on gives more.

**[INFERRED, not confirmed]**: this alone does not prove causation. A faster slew only removes damping —
it doesn't itself inject tens-of-Hz content unless the upstream TARGET (the Q15-bounded voting/clamp
output inside `FUN_0004503c`, channels unidentified — see open item below) fluctuates at that rate. No
evidence of such fluctuation was found this session (the voting loop is MIN/clamp-only, not toggling; the
STEP-selector debounce itself is slow, 10 cycles). The asymmetric slew (§5) is the more promising
rectification mechanism IF a fluctuating target is later found.

## 4b. V43 safety review addendum (2026-07-19) — cal 0xC6206 512→205, [VERIFIED] via full branch decode

Re-derived `0x4543a-0x45458` branch-by-branch from raw disassembly (V850 `cmp A,B` = flags on `B-A`,
per established convention) instead of trusting Ghidra's overflow-flag decompile. Full instruction dump
`0x45380-0x4546f`.

**Sign-crossing reset is TWO-PHASE, not instantaneous jump-to-new-sign** (refines the existing
"toward-zero snaps instantly" note — that's only true WITHIN one sign): at `0x45420-0x45436`, HELD
(`gp-0x138a`) is force-reset to exactly 0 whenever TARGET and HELD have (or would have, at the
TARGET==0 boundary) opposite non-zero signs. The MAIN slew logic (`0x4543a+`) then only ever runs with
TARGET and HELD sharing a sign (or one at 0) — a full sign reversal is: snap-to-0 this cycle, then ramp
from 0 toward the new-sign TARGET at rate STEP_scaled starting next cycle. Not a threat to the
invariant, just a correction to "instant" framing for this specific case.

**Invariant `|OUTPUT|<=|TARGET|` (same sign) is enforced by explicit MIN-style snap-on-overshoot
comparisons in ALL FOUR ramp sub-branches** (`0x45448 ble`, `0x45456 blt`, plus the two `bge`/`ble`
zero-boundary snaps at `0x45440`/`0x4544e`) — each is a `cmp candidate,TARGET` immediately followed by
`mov TARGET,r8` on the branch that would overshoot. **This logic is STEP-magnitude-agnostic: a SMALLER
STEP only makes the "haven't reached yet, use partial step" path active for MORE cycles (slower
convergence) — it does not change which branch fires or weaken any snap comparison. No counterexample
found. Tried: monotonic-target stress case (target rising faster than STEP, forever `HELD<TARGET`,
never trips), and STEP→0 degenerate limit (freezes ramp branches but the toward-zero snap paths, which
don't depend on STEP at all, still work) — invariant holds in both.** [VERIFIED]

**Monitor `FUN_0004595a`** (only place besides `FUN_0004503c` itself that directly compares
`gp-0x6ace`(OUTPUT) against `gp-0x6b94`(TARGET)) computes `sVar4 = |TARGET|-|OUTPUT|` (raw counts) and
faults (`FUN_000462e6(0x3f8e,...)`) only if `sVar4 < -10.24` (i.e. `|OUTPUT|` exceeds `|TARGET|` by
>~10 counts) OR `OUTPUT*TARGET` is strongly negative (opposite sign, magnitude >~0.01 in the /1024²
domain). **Verified numerically** (bit-pattern threshold `0xbc23d70b` = exactly `-0.01`): `sVar4=+100`
(output far BELOW target) passes; `sVar4=-100` (output exceeds target) fails. **This monitor explicitly
TOLERATES output lagging target — the exact direction a smaller STEP produces. A slower governor makes
this monitor's margin LARGER, not smaller.** [VERIFIED]

**Exhaustive image-wide search for OTHER readers of `gp-0x6ace`/`gp-0x6b94`** (all substring matches
checked individually — most were false positives from unrelated absolute-address bit ops or branch
targets containing the same 4 hex digits): the complete real consumer list is `FUN_0004503c` (self),
`FUN_000456a4` (post-governor comp-add — reads `gp-0x6ace` to compute `gp-0x6acc = gp-0x6ace +
comp_add_term`, where `comp_add_term` is a LERP on `gp-0x6a10`/`gp-0x6ac0`, UNRELATED to slew rate),
`FUN_0004595a` (above), `FUN_00036bec` (unrelated IIR low-pass of `gp-0x6b94` into a different output
`gp-0x6b48`), `FUN_0007ff08` (unrelated diagnostic dispatcher, checks `gp-0x6b94==0` as one state-entry
condition, not a divergence/timeout check), `FUN_0003aa2c` (the aggregator, writer of `gp-0x6b94`).
**No timeout, no "command not reached" check, no divergence check with a time bound exists anywhere in
the image for this pair.** [VERIFIED]

**Lockstep partner `gp-0x4cca`**: outside a CRC-gated diagnostic branch (`*(uint*)(*(int*)(gp-0x3490)+4)
== 0x49d6b173 && tp+0x74b9==0xE9` — reachability in normal drive UNCONFIRMED, reads like a factory/
service-mode override, same pattern noted in the original trace), `gp-0x4cca` is written IDENTICALLY to
`gp-0x6ace` every cycle (standard same-cycle read-verify-write RAM-corruption-detection shadow used
throughout this firmware, not an independently-slewing partner). **Under normal operation this is not a
second clock/rate to diverge from.** [VERIFIED]

**Item: `0xC6206`/`0xC6208` re-confirmed genuinely separate, single-reader cells** — corrected an
initial substring-search error (searched literal `"6206"`/`"6208"` and got false positives from branch
targets; the real operand text is `"0x7206, tp"`/`"0x7208, tp"`). Re-run on `"7206"`/`"7208"`: exactly
ONE genuine cal read each, both inside `FUN_0004503c` (`0x45410` for `0xC6206`, `0x45416` for
`0xC6208`), 2 bytes apart (non-overlapping cells), selected by the same branch but never both read on
the same path. [VERIFIED]

**r23 (the STEP's Q15 scale factor, `mul r23,r16,r0 ; sar 0xf,r16` @ `0x4541a`) origin traced**: fed by
the SAME literal-`0x8000`-seeded MIN-chain already described in [[reference-accord-gp4f64-three-consumers]]
(confirmed same instruction `0x45380: ori 0x8000,r0,r6`), specifically the voting loop's later stage
(channels around `gp-0x6942`/`gp-0x6956` and a second pair near `gp-0x68e6`, distinct from but structurally
identical to the earlier 6-element loop — exact channel identities still UNRESOLVED). **The chain proves
an UPPER bound (r23<=32768) but NO lower bound** — the per-channel clamp helper `FUN_00049a90(x,0,y)`
explicitly allows 0 as a floor, so r23 CAN be far below 32768 at runtime. **Consequence for the V43
edit: because `STEP_scaled=(STEP*r23)>>15` is LINEAR in STEP for any fixed r23, the RATIO between
STEP=512 and STEP=205 stays ~2.44-2.5x regardless of r23's actual value — the "2.5x slower" framing
survives in RELATIVE terms even though the ABSOLUTE step size (and therefore absolute drivability) is
data-dependent and unresolved.** Whether r23 fluctuates cycle-to-cycle fast enough to itself be a ripple
source is UNRESOLVED — no new evidence either way; a redundant-sensor-voting/clamping scheme is more
typically a noise-REJECTION mechanism by design, but this is [INFERRED], not proven. [VERIFIED: bound
facts and linearity] / [UNRESOLVED: exact channel identity and runtime fluctuation].

**Convergence cycle count (STEP=205 vs 512, to reach a 1782-count LKAS lane from 0, at r23=32768
best-case/fastest, computed exactly from the branch logic — NOT ms-converted, task rate contested)**:
STEP=512 -> 4 cycles; STEP=205 -> 9 cycles. At smaller r23 both slow down proportionally (e.g.
r23=8192 -> 14 cycles @512, 35 cycles @205) but the ~2.2-2.5x ratio between the two STEP values is
preserved at every r23 tested.

## 5. Asymmetric slew — confirmed structure, no evidence of self-sustained oscillation

Re-confirms [[reference-accord-v40-governor-slew-step-65535-no-overflow]] by direct decompile this
session (not just disasm): the slew branch at `0x4543a-0x45458` is asymmetric — motion AWAY from zero is
capped to `HELD ± STEP_scaled` per cycle; motion TOWARD zero (crossing the target) SNAPS instantly to
TARGET, no partial step. A separate SIGN-CROSSING RESET zeroes `HELD` (`gp-0x138a`) outright when its
sign relationship to the new TARGET satisfies specific overflow-flag conditions (decompiled explicitly
this session, matches the prior branch-graph-only finding).

**Rectification analysis**: this asymmetry can turn a fluctuating TARGET into an asymmetric ripple
("slow charge, fast discharge" or vice versa) on `gp-0x6ace`, but **on a CONSTANT target it produces no
oscillation by itself** — it only changes convergence shape. No tens-of-Hz-rate target fluctuation was
found feeding this slew this session (see §4's caveat). Not ruled out — the 6-element voting-loop
channel identities (gp-0x6544/652c/6514/64fc/6538/6520/6508/64f0 and siblings) remain UNRESOLVED and are
the next place to check for oscillatory content if this thread is picked back up.

## Calibration lever summary (all read from stock/_v38_plain_image.bin/_v42_plain_image.bin — byte-identical across all three, none touched by any build)

| Cal addr | tp offset | Value | Role |
|---|---|---|---|
| 0xC6202 | tp+0x7202 | 4762 | governor nominal ceiling |
| 0xC509E | tp+0x609e | 5325 | energy-budget charge threshold (UNREACHABLE, > governor ceiling) |
| 0xC5164 | tp+0x6164 | 0 | energy-budget ceiling (collapses hysteresis band to ~0) |
| 0xC5128 | tp+0x6128 | 1024 (→64.0 charge gain) | energy-budget charge-rate gain |
| 0xC5638 | tp+0x6638 | 30544 (→0.4661) | current-based rolling-avg (gp+0x13c) multiplier |
| 0xC6206 | tp+0x7206 | 512 | governor slew STEP, FAST (gp-0x67f5==0) |
| 0xC6208 | tp+0x7208 | 205 | governor slew STEP, SLOW (gp-0x67f5!=0) |
| 0xC531E | tp+0x731e | 1062 | STEP-selector threshold on driver-torque-voted signal |
| 0xC64E7 | tp+0x74e7 | 10 (cycles) | STEP-selector debounce hold count, both directions |

## 6. Slew-limiter engagement amplitude vs STEP — [VERIFIED math, CONDITIONAL verdict on r23]

Traced 2026-07-20 for team-lead's whole-system 21Hz feedback audit (asked to determine whether the
FAST/SLOW STEP switch could plausibly explain the hands-off/hands-on 21Hz asymmetry given measured
~139-count raw sensor amplitude at 21.4Hz, 1000Hz task tick — see [[control-task-tick-confirmed-1khz]]).

`STEP_scaled = (STEP × r23) >> 15`. Max per-cycle increment for a sinusoid of amplitude A at 21.4Hz/
1000Hz ≈ `0.134×A` counts/cycle. Limiter engages once `0.134×A > STEP_scaled`, i.e. at
`A_thresh = STEP_scaled / 0.134`:

| r23 | STEP_scaled(FAST=512) | A_thresh FAST | STEP_scaled(SLOW=205) | A_thresh SLOW |
|---|---|---|---|---|
| 32768 (ceiling, §4's proven upper bound) | 512 | ~3820 | 205 | ~1530 |
| 8192 (this file's own §4 illustrative value) | 128 | ~955 | 51 | ~381 |
| 2048 (1/16 ceiling) | 32 | ~240 | 13 | ~96 |

**At r23 near its proven ceiling, BOTH thresholds sit far above the measured ~139-count amplitude —
the limiter is transparent at either STEP and switching 512↔205 would do nothing measurable to 21Hz
transmission at that amplitude, even allowing generous 2-5x amplification through unfiltered upstream
lanes** (see [[reference-accord-fun352b4-untested-carrier-and-dead-biquad]]). **Only if r23 drops to
roughly ≤3000 in real operation does the crossover land near the measured amplitude** — which would
produce exactly the reported asymmetry. **r23's runtime magnitude remains unresolved** (§4's own
"no lower bound" caveat is the crux of this open item) — this is the single fact that would convert
this lever from "plausible" to "confirmed or dead." [VERIFIED: the arithmetic and thresholds]
[UNRESOLVED: which regime is real]

**Safety re-confirmed fresh this session** (independent of §4b's prior derivation): `search_instructions`
on `"7206"`/`"7208"` re-run — `0xC6206` still exactly 1 real hit (`0x45410`), `0xC6208` still exactly 1
real hit after excluding 7 substring false-positives (2× unrelated absolute address `0xB7208`, 5×
branch-target hex collisions). `FUN_0004595a` re-decompiled fresh: confirms it tolerates OUTPUT lagging
TARGET and only faults on OUTPUT *exceeding* TARGET or opposite-sign — lowering `0xC6206` (more lag,
never overshoot) cannot trip it. This is the OPPOSITE direction from V40's `0xFFFF` fault (which
removed the limiter's "haven't reached target" branch entirely via an astronomically large STEP).

## Related
[[reference-accord-governor-gp0x184-chain]] — the gp+0x128/0x130/0x184/gp+0x1a4 producer chain this extends.
[[reference-accord-gp4f64-three-consumers]] — the 3 consumers of the governor cap value.
[[reference-accord-shaper-fun42af8]] — clamp order in FUN_00042af8 (governor clamp #6 before final #7), the structural bound behind §2's disconfirmation.
[[reference-accord-lkas-lane-is-a-lowpass]] — the existing low-pass finding §3's rolling-average is consistent with.
[[reference-accord-v40-governor-slew-step-65535-no-overflow]] — prior asymmetric-slew finding, now confirmed by full decompile.
[[reference-accord-fun352b4-untested-carrier-and-dead-biquad]] — §6's candidate amplitude source; also documents the full aggregator per-lane gate-width map.
