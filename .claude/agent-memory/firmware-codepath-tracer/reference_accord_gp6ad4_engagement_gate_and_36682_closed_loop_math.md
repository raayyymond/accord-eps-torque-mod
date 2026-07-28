---
name: reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math
description: gp-0x6ad4 (FUN_0003a382) is gated to zero only when the EPS's OWN FOC/assist substate gp-0x67fe==0 (motor drive down) -- NOT an openpilot-engagement gate, corrected 2026-07-28 by team-lead with V31P telemetry (TRUMP=(gp-0x67fe==2) reads 1 in 100% of frames incl. disengaged stretches). Also NOT among the six 0xC646C gain readers (0 hits, function-scoped search). FUN_00036682's actual transfer function is a closed loop (y[n-1] subtracted twice), giving DC gain K/2 not K, and ~0.005-0.011 counts/count at 21Hz vs a measured 0.22 target -- decisively ruled out as the 21Hz carrier regardless of the tp+0x73d2=6-vs-14 discrepancy.
metadata:
  type: reference
---

# gp-0x6b98 21Hz-carrier attribution — traced 2026-07-28, same session as the aggregator lane inventory

On-car H1 measurement (team-lead, V55, engaged+hands-off creep): sensor(`gp-0x4f60`)→command(`gp-0x6b98`)
transfer is **flat ~0.19-0.22 counts/count from DC to 21Hz**, phase rotates only ~28° across that whole
band (~4ms lag — NOT a filter's phase response), coherence 0.687 at 21.09Hz. Needs engaged+hands-off.
This entry pins down which lane can match that number. Builds on
[[reference_accord_gp6b98_aggregator_full_lane_inventory]].

## `gp-0x6ad4` (`FUN_0003a382`) is NOT among the six `0xC646C` (4x gain) readers — CONFIRMED

`search_instructions(function="FUN_0003a382", operand_pattern="746c")` → **0 matches, 468 instructions
scanned, function-scoped.** Its gain instead comes from 4 separate Q10 LERP tables (see below). This means
the previously-scoped fix ([[reference_accord_c646c_gain_feedback_vs_forward_classification]]'s "retarget
only `0x2a1ee`") does **not** touch `gp-0x6ad4` at all — if this lane is the 21Hz carrier, that fix is a
no-op against it.

## `gp-0x6ad4` IS gated to zero via `gp-0x67fe` — but this is NOT an openpilot-engagement gate ⚠ CORRECTED 2026-07-28

The lane's final output is `min_magnitude_select(gain_chain_value, limit)`. `limit` comes from a branch on
`gp-0x67fe`:
- `gp-0x67fe==0`: `limit = tp+0x71fc` = **0xC61FC = 0** (fresh read) → min-select against 0
  **zeroes the whole lane unconditionally.**
- `gp-0x67fe∈{1,2}`: `limit` = a live nonzero LERP-derived signal (`sVar15` or `uVar17`).

**I originally mis-called this an "engagement gate." Team-lead corrected this same-day, and I'm accepting
the correction — it's better evidenced than my structural read.** Per
[[eps-gp67fe-trump-engaged-holding-substate]] (Ghidra-verified 2026-07-13, cross-checked on-car), `gp-0x67fe`
is the EPS's own FOC/assist substate, written by `FUN_0003bd7c` from `gp-0x6772`: `gp-0x6772==5 -> 2`,
`==4 -> 1`, else `0`. Decisive empirical evidence: V31P's `TRUMP=(gp-0x67fe==2)` telemetry bit read **1 in
100% of frames across whole rlogs (routes 77/79), including disengaged stretches** — because
`gp-0x6772==5` means the motor drive is running, i.e. power steering is on, true for the whole ignition
cycle regardless of openpilot engagement. **`gp-0x6ad4` is therefore live during ordinary manual driving
too; this gate closes only when EPS assist itself is down, not when openpilot disengages.** It does not
explain the on-car engagement-dependence of the 21Hz oscillation — that has to come from the operating
point (hands-off + motor actively loading the column) instead.

**Build-safety consequence (more important than the gate mislabel):** muting `gp-0x6ad4` via `0xC6AF0`
would change **manual steering feel**, not just LKAS behavior, since the lane is live whenever assist is
up. V52C is the standing precedent (null for the vibration, changed manual feel) — factor into GATE 2.

## `gp-0x6ad4`'s input stage: gain exactly 1.0, no feedback subtraction

`iVar31 = clamp(gp-0x4f60 - bias, ±0x2800)` where `bias` = a slowly hysteresis-switched `±tp+0x7200` value
(shifts DC operating point, does NOT attenuate AC content). Unlike `FUN_00036682` (below), there is **no
`y[n-1]` subtracted anywhere in this input path** — a real structural difference.

Downstream: 3 parallel branches process `iVar31`.
- **Stage A** (cal `0xC6450`=1024/1024) and **Stage C** (cal `0xC644A`=1024/1024): both **exact algebraic
  identities** (zero lag, reconfirmed fresh this session, matches
  [[reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole]]).
- **A 3rd branch is a clamped/anti-windup ACCUMULATOR, not a peak-hold**: `iVar18 += (base_input*uVar16)>>10`
  every cycle with no decay term, clamped back into range by headroom vars each cycle. A literal unclamped
  integrator would show ~90° phase lag at 21Hz; the measured ~28° total rotation is inconsistent with this
  branch dominating, and consistent with Stage A/C (both zero-lag) dominating instead — circumstantial but
  real supporting evidence for this lane as the carrier.
- 4 LERP table endpoint reads (fresh, `code.bin`): Stage-A gain (idx=`gp-0x6ac0` motor rate) Y∈[153,256]/1024
  =[0.15,0.25]; the accumulator-branch gain (idx=`gp-0x6ac0` too) constant at 98/1024=0.096 across every
  knot read; a vehicle-speed(`gp-0x6a5e`)-indexed gain Y∈[0,1024]/1024=[0,1.0], ~0.19-0.4 at 5.4-9km/h
  creep (ASSUMES `gp-0x6a5e` uses the same km/h×64 scale as `gp-0x6a46` — not independently confirmed for
  this variable); a 4th LERP (idx=`gp-0x671a`) constant at 1024/1024=1.0 — a no-op.

**NOT CERTIFIED: the exact combine arithmetic across the 3 branches** (`(stageC+accumBranch+stageA)>>5`
then `*uVar27>>10`) — Stage A/C carry an internal ×32 normalization the accumulator branch does not
obviously share; reconciling this needs either careful cycle-accurate numeric simulation or an empirical
cross-check, not attempted this session. Do not treat "~0.22 achievable" as more than an order-of-magnitude
plausibility argument until that's done.

## `FUN_00036682` (the `0xC646C` readers #5/#6): closed-loop math, decisively ruled out

Previously modeled (in [[reference_accord_c646c_gain_feedback_vs_forward_classification]]'s "Round 3") as
a simple EMA with DC gain = α. **Correction: it's a closed loop.** `y[n-1]` (=`gp-0x6b46`) is subtracted
once to form the error `e[n] = K*gp-0x4f60[n] - y[n-1]` (K=GAIN/32768), then subtracted AGAIN inside the
EMA's own update (`y[n]=y[n-1]+α(e[n]-y[n-1])`), giving:
```
y[n] = y[n-1]*(1-2α) + α*K*x[n]
```
DC gain = **K/2** (not K). At 21.09Hz (fs=1000Hz): gain formula `α*K / sqrt(1-2a·cos(w)+a²)`, a=1-2α.
- Using `tp+0x73d2`=6 (this session's fresh 3x-corroborated read): gain@21Hz ≈ **0.0048**.
- Using the previously-recorded 14 (unresolved discrepancy, see
  [[reference_accord_c646c_gain_feedback_vs_forward_classification]]'s addendum): gain@21Hz ≈ **0.0111**
  (matches the team-lead's own independent estimate almost exactly — cross-validates this closed-loop
  model as structurally correct regardless of which α is right).
Either way, **20-45x smaller than the measured ~0.22** — decisively rules out `FUN_00036682`/readers #5-#6
as the 21Hz carrier, independent of resolving the 6-vs-14 discrepancy.

## Numeric simulation (2026-07-28, same session) — gain ≈0.25-0.27 @21Hz, flat IFF the untraced ceiling term is small

Hand-symbolic tracing of the 3-branch combine hit a real limit (see above), so ran a cycle-by-cycle Python
simulation instead: translated Stage A / Stage C / the accumulator-headroom branch to plain clamp/min/max
arithmetic from the decompile, drove it with a synthetic sinusoid at 21.09Hz and 0.98Hz, measured
steady-state gain/phase by projection (sanity-checked against an identity system first: 1.0/0.0°, correct).
Used the fresh LERP endpoints already on record (Stage A gain 153-256/1024, accumulator gain 98/1024,
final multiplier 1024=no-op). The one un-derived input, `C_limit` (stands in for `iVar10`, the ceiling
chain rooted in `gp-0x6bda` + a hardware-status nibble — NOT `gp-0x4f60`-dependent, not traced this
session), was **swept** rather than guessed.

**Result: 21Hz gain is stable at 0.25-0.27 across the whole `C_limit` sweep (0 to 20000), phase stays
small (+3.6° to +7.8°)** — matches the measured 0.19-0.22 / ~28°-total-rotation reasonably well (same
order, ~15-25% high on magnitude, plausibly within the error of the LERP-endpoint estimate and the
untraced bias term).

**Important caveat found: LOW-frequency (0.98Hz) behavior is NOT flat unless `C_limit` is small.** As
`C_limit` grows past ~1000, gain@0.98Hz rises to 0.55 and phase swings to -62° — a real break from
flatness. **Isolating Stage A+Stage C alone (accumulator gain forced to 0) gives a clean flat, near-zero-
phase response at both test frequencies (0.2556@21Hz/+8.7° vs 0.2500@0.98Hz/+0.4°)** — the accumulator
branch is specifically what would break flatness, and only when its own ceiling is large. This makes a
falsifiable prediction: if the real `iVar10` is small at hands-off/creep (physically plausible — low
commanded assist), this lane's own transfer function should closely match the measured shape; if `iVar10`
is large there, this lane alone would show a low-frequency-heavy, non-flat response inconsistent with the
measurement, meaning either another mechanism dominates or something downstream flattens it back out.
Amplitude-swept 500-10000 counts at `C_limit`=2000: gain@21Hz stable ~0.255 throughout (no clamp
saturation in the tested range).

**Confidence: hand-translated pseudocode simulation, not byte-exact instruction replication.** The
Stage-A/C-only control case matching theoretical prediction exactly is reassuring for that part; the
accumulator branch's clamp/min-select logic was NOT independently verified against real instructions.
`C_limit` itself needs `gp-0x6bda`'s own LERP tables (`tp+0x77a2` region, not yet read) plus the hardware-
status-nibble source to resolve from a swept parameter to a real number.

## ★★★★★ DECISIVE: the `0xC6AF0` LERP unconditionally gates gp-0x6ad4's FINAL output (2026-07-28)

Team-lead's actual build-decisive question, answered by register-level disassembly trace (not decompile
guessing) on `FUN_0003a382` in `code.bin` — verified two independent ways (decompile algebra + raw
instruction trace), no ambiguity:

```
0x3a632  ld.hu -0x6966[gp],r11     authority index (gp-0x6966)
0x3a636  movea 0x7af0,tp,r15       LERP base = tp+0x7af0 = 0xC6AF0
0x3a63a  addi 0xc,r15,r13          r13 = tp+0x7afc = 0xC6AFC (Y[0])
0x3a69c  andi 0xffff,r6,r21        r21 = LERP result
0x3a794  cmovnh r21,r15,r15        r15 = saturate(r21, 0x8000)
0x3a79e  mul r15,r10,r0            product
0x3a7aa  sar 0xf,r10               r10 = ceiling ("iVar10"), >>15
```
**`r10` is never overwritten anywhere in `0x3a7ac`-`0x3a88c`** (scanned every instruction in that span for
`r10` as a destination — none; r11/r13/r16 get reused for unrelated purposes in that window, r10 doesn't).
Final block:
```
0x3a88c  cmp r10,r14        ceiling vs combine result (Stage A+B+C's output)
0x3a88e  bgt 0x3a8a0         if ceiling>combine: store ceiling as-is
0x3a890  subr r0,r10         else: negate ceiling
0x3a892  cmp r14,r10
0x3a894  cmovle r14,r10,r10  min-select
0x3a8a0  st.h r10,-0x6ad4[gp]
```
With `r10`(ceiling)=0 (forced by muting `0xC6AFC`/`0xC6AFE` to 0, given `gp-0x6966` sits at 0 inside the
muted low-index table region): **both paths through this block store exactly 0, regardless of `r14`
(the combine result).** Hand-verified both branches of the compare algebraically.

**Conclusion: the `0xC6AF0` mute is a complete, branch-agnostic kill of `gp-0x6ad4`'s output — it is NOT a
partial edit hitting only one of the three parallel branches (Stage A / Stage C / accumulator).** This is
the answer that mattered for the build decision; the earlier gain-attribution work (which branch produces
what magnitude) does NOT gate this decision since the ceiling forces 0 regardless of the combine result.

## Verdict for whoever picks up the build decision
`gp-0x6ad4`/`FUN_0003a382` is the structurally-consistent candidate: unfiltered input (gain=1.0, no
feedback subtraction), two exact-zero-lag stages, untouched by the existing `0xC646C` fix plan, and a
phase signature consistent with zero-lag-stage dominance. `FUN_00036682` is ruled out. **The gate on this
lane is an EPS-assist-down gate, not an openpilot-engagement gate** (corrected above) — the measured
engagement-dependence must come from elsewhere, and any mute-fix here touches manual steering feel, not
just LKAS. The exact 0.22 magnitude for `gp-0x6ad4` is NOT yet certified — next step is a concrete numeric
walk-through of the 3-branch combine, or an empirical isolation of this lane if a telemetry channel exists.

## Related
[[reference_accord_gp6b98_aggregator_full_lane_inventory]] — the full 9-lane structural inventory this
entry's carrier attribution builds on.
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — source of the #5/#6 chain and the
6-vs-14 `tp+0x73d2` discrepancy this entry resolves the *consequence* of (doesn't matter which is right).
[[eps-gp67fe-trump-engaged-holding-substate]] — the `gp-0x67fe` variable this entry newly ties to a hard
zero-output gate on `gp-0x6ad4`; that memory only had it as an "ENGAGED/HOLDING substate" with "no event
info" — this session gives it a concrete downstream consequence.
