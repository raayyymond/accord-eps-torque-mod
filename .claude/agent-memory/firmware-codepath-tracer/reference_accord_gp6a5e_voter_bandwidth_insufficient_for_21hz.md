---
name: reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz
description: FUN_00041eec's adaptive slew limiter on gp-0x6a5e (byte-verified LERP tables, step=16 up / 27 down near the 0xC9E9C damping gate's operating point) plus its phase-gated call rate (6 of 16 phases, i.e. 37.5% of the host task's ticks) together cap gp-0x6a5e's trackable 21Hz peak excursion at roughly 5-70 counts depending on the unresolved 100Hz-vs-1kHz task rate -- 30-400x too small to cross the 0xC9E9C damping gate's 2240 threshold. Decisive against the "damping engages during the vibration" hypothesis regardless of which task-rate candidate is correct.
metadata:
  type: reference
---

Traced 2026-07-21 for team-lead's hypothesis: does the `0xC9E9C` damping-table gate (see
[[reference-accord-damping-friction-returncentre-torque-gates]]) fail to engage DURING a 21Hz hands-off
vibration because `gp-0x6a5e`'s own voter can't track the oscillation fast enough, locking the damping
term at zero for exactly the signal it should suppress?

## 1. The slew limiter — byte-verified tables [VERIFIED]

`FUN_00041eec` (the voter) rate-limits its own output each call via two independent LERP tables, both
keyed on the CURRENT (pre-update) value of `gp-0x6a5e` itself:

**Downward step** (`uVar20`, applied when the new candidate is LOWER than the previous value) — tables at
`tp+0x7842`(X0 dup)/`tp+0x7844..784A`(X array, 4 pts)/`tp+0x784C..7852`(Y array)/`tp+0x7854`(Y-high dup),
byte-read at `0xC6842`:
```
X = (0[dup], 31808, 31872, 31936, 32000)
Y = (27, 27, 27, 27, 27)         -- FLAT. Downward step = 27 counts/call, unconditionally.
```

**Upward step** (`uVar17`, applied when the candidate is HIGHER) — tables at `tp+0x785A`(X0 dup)/
`tp+0x785C..7862`(X array)/`tp+0x7864..786A`(Y array)/`tp+0x786C`(Y-high, does NOT match Y[3] — see below),
same read, offset `0xC685A`:
```
X = (5504[dup], 6400, 8000, 11200, 17600)
Y = (16, 16, 14, 11, 8)   then a DISCONTINUOUS jump to 5 at/above X=17600 (Y-high=5 != Y[3]=8 -- a real
    3-count downward step right at the boundary, genuinely verified in the bytes, not a parsing artifact)
```
**Near zero and near the `2240` gate threshold — the region that matters — both tables are in their flat
low-end segment: UP = 16 counts/call, DOWN = 27 counts/call.** The falling/discontinuous part of the
upward table only engages above 6400, well past the gate's operating point.

Both steps apply to `gp-0x6a5e`'s own value directly: the persisted "previous" state (`gp-0x3584`) IS
`gp-0x6a5e`'s prior output, and the slew-limited result is what gets written back to `gp-0x6a5e`
(`0x42342`) at the end of the function. This is the ONLY dynamics-shaping stage in the whole
`gp-0x6a44..46` → `gp-0x6a5e` path — see §3.

## 2. Call rate — phase-gated, NOT every task tick [VERIFIED structure, rate itself unresolved]

`FUN_00041eec`'s sole caller is `FUN_00022ca0` (confirmed via `get_function_callers`), a large
phase-dispatched RTOS task body. The call is gated:
```
0x22cb2: r25 = 1 << (gp-0x67fa & 0xF)         ; one-hot phase bit, 16-phase cycle
0x22cdc: r22 = r25 & 0xD38                     ; r22 != 0 selects phases {3,4,5,8,10,11}
0x22daa: be [skip]                              ; skip the call if r22==0
0x22dae: jarl FUN_00041eec
```
`0xD38` = bits 3,4,5,8,10,11 set → **FUN_00041eec runs on exactly 6 of every 16 phases (37.5%), not
every host-task tick.** This is on top of, not a resolution of, this kit's existing open question of
whether the host task itself runs at ~100 Hz or ~1 kHz — I did not find new evidence to settle that here.

## 3. No additional filtering upstream of the voter [VERIFIED for FUN_000534da; FUN_00053216 not fully checked]

`gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38` are written by `FUN_000534da` — decompiled in full this session.
It's itself a `param_1`-dispatched (phase-selected) state machine: `param_1==0` calls `FUN_00053216`
(the raw ×41/64-scale function per [[reference-accord-dual-torque-sensor-architecture]]) once per
channel and stores the result DIRECTLY — no averaging, no EMA, no extra state. Other `param_1` values
either pin all channels to the invalid sentinel `0x7fff` or copy fixed/shadow values (not live sensor
data). **No additional smoothing exists between the raw hardware-scaled sample and the voter's own slew
limiter.** [OPEN, flagged not resolved]: `FUN_000534da` is NOT called from `FUN_00022ca0` (not present
in that function's call list) — it must be driven by a separate hardware-timer path (`FUN_000520d0`,
TAUA0-paced per the architecture memory), whose rate relative to `FUN_00041eec`'s is unknown. If that
acquisition is SLOWER than the voter's sampling, the voter would sometimes reuse a stale raw value
(effectively free zero-order-hold, not a new filter) — this can only worsen, not improve, the tracking
bandwidth conclusion below.

## 4. Tracking bandwidth for a 21 Hz sinusoid [VERIFIED arithmetic given §1-2; INFERRED task rate]

Standard rate-limiter bound: to track `A·sin(2πft)` without clipping, need `A·2πf ≤ step/T_sample`, i.e.
`A_max = step × f_call / (2πf)`. Using the binding UP step (16, smaller than DOWN's 27, since reaching
2240 requires an upward excursion) and `f = 21 Hz`:

| Host task rate (candidate) | `FUN_00041eec` effective rate (×0.375) | `A_max` (counts) | Calls per 21 Hz period |
|---|---|---|---|
| 100 Hz | 37.5 Hz | **≈ 4.6** | **≈ 1.8** — sub-Nyquist, cannot even represent 21 Hz without aliasing |
| 1000 Hz | 375 Hz | **≈ 45.5** | ≈ 17.9 — adequately sampled, but still slew-capped |

Cross-checked with a quarter-period-climb estimate (`A ≈ step × calls_per_period / 4`): 7.2 and 71.6
respectively — same order of magnitude, as expected from a cruder approximation.

**Either candidate rate gives an answer 30-400x smaller than the `2240` gate threshold.** At the lower
rate the voter cannot even resolve a 21 Hz component (aliasing); at the higher rate it resolves it but
clips its amplitude to roughly 45 counts. **`gp-0x6a5e` cannot represent a 21 Hz oscillation large enough
to cross `2240`, under either task-rate hypothesis this kit has on the table.** This is the decisive
result: it does not depend on resolving the 100 Hz vs 1 kHz question.

## 5. Outlier rejection under coherent 21 Hz swing [INFERRED, not separately instrumented]

If all 5 channels see the same physical oscillation in phase (a genuine shared mechanical resonance),
they stay within the voter's agreement threshold and the plain-average path is taken (not the "closest
channel to last cycle" outlier-rejection fallback) — so the analysis above applies without a qualitative
change. If the channels were somehow OUT of phase with each other, the outlier-rejection path (a
discrete nearest-match selection, not a smooth average) would engage instead and could behave
differently — not evidenced either way this session, flagged as unresolved rather than assumed.

**Side note, not requested but relevant**: because every channel is `abs()`'d before averaging
(see [[reference-accord-gp6a5e-sensorA-magnitude-no-can-bridge]]), a genuinely coherent zero-mean 21 Hz
input would appear to the voter as a full-wave-rectified, frequency-DOUBLED (~42 Hz) magnitude signal
even before the slew limiter acts on it — an additional reason the raw 21 Hz shape could not survive
intact even if the slew limiter were fast enough.

## 6. LERP below-range behaviour on the damping table itself — CLAMPS, does not extrapolate [VERIFIED]

Re-confirmed from the exact Ghidra-decompiled branch for `FUN_00034350`'s `0xC9E9C` lookup (captured this
session, not re-derived from raw asm): the `else` arm taken when the key is at or below `X[0]` (`2240`)
is `uVar13 = *puVar20;` where `puVar20` points directly at `Y[0]` (`= 0`) — a **flat clamp**, not a
computed extrapolation. No sign-inversion risk from this specific table for `gp-0x6a5e < 2240`.

## 7. Hysteresis on the damping gate — none found on the direct compare [VERIFIED for this specific gate]

The `0xC9E9C` gate itself (`gp-0x6a5e ≤ 32000 AND gp-0x67f4==1`, `0x344d8-0x344fa`) is a bare compare
chain — no loop, no counter, no dwell instruction anywhere in that span (re-confirmed from the raw
disassembly captured earlier this session). The voter's plausibility flag `gp-0x67f4` DOES have its own
transition debounce (`|new-old|<0x41` before flipping from invalid→valid, inside `FUN_00041eec`), but
that is a different mechanism (sensor plausibility, not torque-magnitude hysteresis) and does not
soften the `2240` threshold itself. **The slew limiter (§1) is the closest thing to "smoothing" in this
whole path — there is no separate hysteresis band on the gate's own comparison.**

## Related
[[reference-accord-damping-friction-returncentre-torque-gates]] — the `0xC9E9C` gate this bandwidth
  analysis was tasked to test
[[reference-accord-gp6a5e-sensorA-magnitude-no-can-bridge]] — the voter's structure and magnitude-not-
  signed finding this session builds directly on
[[reference-accord-dual-torque-sensor-architecture]] — Sensor A acquisition path, `FUN_00053216` scale
[[reference-accord-lkas-lane-is-a-lowpass]] — the sibling finding that the LKAS command path itself is
  also a low-pass (different mechanism, same qualitative shape: multiple independent band-limiting
  stages in this firmware, none of them a notch/biquad)
