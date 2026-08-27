---
name: reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved
description: FUN_00034a72's "baseline" (rate_error's other operand) fully traced at instruction level -- torque/motor-rate domain only (angle-rate washout hypothesis FALSIFIED), FSM zeroes it except one steady state. Corrects reference_accord_gp6bbe_rate_error_speed_scheduled_lane.md's "rate-keyed" label for 0xCA4F4/0xCA23C -- both are keyed by gp-0x6ba6 (torque+motor-rate composite from FUN_0003b66a), not gp-0x6a56. Also solves the LERP table struct layout (count-dependent Y-base) and dumps 2 new tables + K1-vs-ceiling instruction-level order.
metadata:
  type: reference
---

# `gp-0x6bbe` baseline/FSM fully solved + LERP struct format decoded (2026-07-30, team-lead request)

Answers team-lead's 4-part ask on the angle-rate tributary gap in `model/eps_lkas_chain_model.py`. Full
disasm of `FUN_00034a72` (`code.bin`, gp=0xFEDF8000, tp=0xBF000), byte-verified tables, mode=10 (A160).

## 1. Baseline (r28) — [MEASURED] torque/motor-rate ONLY, no angle content anywhere

`rate_error = baseline(r28) - angle_rate_raw(gp-0x6a56)` at `0x34e96`. Traced r28's producer at
`0x34c06-0x34cae`:
```
r28 = clamp(gp-0x6986, 0, 1024)                                          ; 0x34c06-14
r28 = (r28 * Y1) >> 14                                                   ; 0x34c1c,26  Y1=LERP(gp-0x6ba6)
r28 = r28 * mode_gain_byte(0xCA40C->0xCA434->0xD2012=128) >> 7           ; 0x34c2e,38  =1.0 exactly (128/128)
r28 = r28 * LERP2(gp-0x6a10, RAM table gp-0x6394-family)                 ; 0x34c8c
r28 = r28 * sign(gp-0x6a02)                                              ; 0x34c98
r28 = -r28 >> 10                                                        ; 0x34cac,ae
```
gp-0x6986 unresolved this session (flag). gp-0x6a10 sources from gp-0x6a02 (torque, `(gp-0x4f60*10)/
gp-0x4ebc`) when `FUN_0003fc16`'s dedicated path is gated dead (`tp+0x74cf=0`, confirmed stock — see
[[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]]). **Every term is torque/motor-rate
domain. The angle-rate-washout hypothesis (baseline = filtered copy of gp-0x6a56) is FALSIFIED** — no
instruction between function entry and `0x34e96` reads gp-0x6a56 except the two already-known sites
(`0x34ab8` validity check, `0x34e8e` the subtraction's other operand).

## 2. FSM (gp-0x682e) — [MEASURED] gates baseline to 0, does NOT hold/lag its value

Disasm `0x34d40-0x34e8a`, corrected from an earlier same-day memory's framing:
- **State 0**: unconditional → state 1 (boot only, `0x34d48→0x34e56`).
- **State 1**: if `bVar10`(engage+plausibility gate) FALSE → state 2, baseline forced 0 (`0x34d5c→
  0x34dac`). If TRUE → **jumps straight to `0x34e8a`, using r28 AS FRESHLY COMPUTED THIS TICK** — no
  state-holding lag, r28 is recomputed every call regardless of FSM state.
- **State 2**: if `!bVar10` stay, baseline=0 (`0x34e52`). If `bVar10` → state 3, baseline=0, dwell
  counters reset to 1.
- **State 3**: dwell counter `gp-0x68c8` vs `(tp+0x74d1)*10` (byte-read `0xC64D1`=25→threshold=250). While
  dwelling, baseline=0 regardless of `bVar10`. On dwell-complete, falls to the state-0 trampoline
  (state→1, baseline uses this tick's fresh r28, not zero).
**Net: baseline = fresh torque/motor-rate product whenever the engagement gate holds steady (state 1,
the common case in normal driving); baseline = exactly 0 during disengage/debounce.** No frozen/stale
"reference" value exists — this is an enable/disable gate on a live signal, not a slow tracking filter.

## 3. `gp-0x6ba6`/`gp-0x6b9a` — CORRECTS "rate-keyed" label; sole producer FUN_0003b66a [MEASURED]

`search_instructions` for "6ba6"/"6b9a": writers are exclusively `FUN_0003b66a`@`0x3b892`/`0x3b8b0` (this
matches [[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]]'s prior finding — reused,
not rediscovered). Decompiled `FUN_0003b66a` fresh this session: output = magnitude(gp-0x6ba6)/signed
(gp-0x6b9a) of a SUM of two branches:
- **Branch A (slow, multi-stage)**: `gp-0x6abc` (motor/resolver electrical rate — producer `FUN_00041464`
  EMAs raw `gp-0x4f50`, see [[reference_accord_fun41464_sign_filter_phase_response]]) → 2-pole biquad
  (coeffs at tp-relative `&PTR_FUN_5018/501c/5020` = abs `0xC4018/1c/20`, NOT dumped) → combined with a
  torque-ratio term (`gp-0x4f62/gp-0x4ebc`, gated `tp+0x74be`) → **slew-limited ±565/cycle** → 2 more
  cascaded single-pole EMAs (coeff `tp+0x73b4`, used twice) → clamped ±10.0.
- **Branch B (fast, lightly filtered)**: raw `gp-0x4f60` (torque) → 2 cascaded single-pole EMAs, BOTH
  alpha=512/1024=0.5 (`tp+0x73ba`=512, already byte-verified in the V48B memory) → combined corner ≈110Hz,
  **only -1dB/-21.6° at 21Hz** (from that memory's own math).
Sum scaled by `tp+0x73b6` (not dumped) → `gp-0x6b9a`(signed)/`gp-0x6ba6`(abs).
**CORRECTION to [[reference_accord_gp6bbe_rate_error_speed_scheduled_lane]]**: 0xCA4F4(LERP1)/0xCA23C
(LERP4) are indexed by THIS composite (`gp-0x6ba6`), not by steering angle rate — that memory's "rate-
keyed" label is wrong; no angle-rate content enters here either. But because Branch B is only lightly
filtered, **`gp-0x6ba6`/`gp-0x6b9a` do carry near-unattenuated 21Hz TORQUE content** if the physical torque
sensor genuinely oscillates during a resonance — this is the one place baseline is NOT simply "slow."

⚠ Also found: the OLD "combine" computation (`gp-0x6c2e`×`tp+0x7370`(=2560, new)/`iVar29`(torque EMA,
`tp+0x7372`=205, matches prior memory)/polarity, `0x34ac4-34b34`) is **computed but functionally DEAD** on
this car — `tp+0x7499` byte-read = **1** (`0xC6499`), which routes LERP1/LERP4's index to `gp-0x6ba6`
directly (`0x34b6e-b72`), bypassing the combine entirely. Corrects my own prior-session framing that
attributed LERP1/LERP4's indexing to this combine chain.

## 4. K1 vs the final ±512 ceiling — full instruction-level order [MEASURED]

```
0x34f20-32  term1 = (K1[0xD200C=43] * rate_error_clamped) >> 7                    Q7 gain
0x34f34     term1_raw = term1 * Y3(speedLERP, gp-0x6a5e, 0xD2834 -- unchanged from prior memory)
0x34f40     term2 = term1_raw >> 10
0x34f42-5c  term2_clamped = clamp(term2, +-666)   [0xC7A58->0xC7A80(mode10)->0xD2000=666, CONFIRMED
            a real 3-way clamp via disasm -- NOT a sign-only pick as an earlier decompile-only read
            suggested]
0x34f5e-fc4 Y4 = LERP(gp-0x6ba6, 0xCA23C->0xCA264->0xD2888, dumped below) blended into EMA state
            gp-0x69ba via coeff at (mode*4)+tp+0xb06c [NOT dumped]
0x34fea-ff6 gp0x6988norm = clamp(gp-0x6988,0,1024)
0x34ffa-08  term3 = (term2_clamped * ((Y4blended * gp0x6988norm)>>10)) >> 14
0x35010     term3 *= polarity(r20, established at top from gp-0x6752)             mulh
0x35012-78  FINAL CLAMP to +-Y5(speedLERP2, gp-0x6a62, 0xD20C0=flat 512, unchanged from prior memory)
0x3507c-c2  store gp-0x6bbe (+ lockstep shadow gp-0x4cf0)
```
**Raising K1 is NOT a guaranteed null.** Between the 666 mid-chain clamp and the final 512 ceiling sit
TWO more multiplicative fractional stages (Y4-blend/16384-ish, gp-0x6988/1024) that generally attenuate,
not merely pass through — so saturating the 666 clamp does not imply saturating the 512 ceiling. Whether
K1 is currently in the linear region or already clamp-bound in practice cannot be determined statically
(depends on live rate_error/Y3/Y4/gp-0x6988 magnitudes at the same instant) — flag as needing telemetry,
not assumed either way.

## 5. LERP struct format SOLVED (count-dependent Y-base) + 2 new tables dumped [MEASURED, byte-verified]

Layout, confirmed against the two ALREADY-KNOWN tables (0xD2834 count=6, 0xD20C0 count=5) and matching the
disasm's Y-base offsets exactly (`+0xe` for count=6, `+0xc` for count=5 — i.e. **Y-base = 2+2*count**,
compiled as a per-callsite immediate, not a runtime formula):
```
offset+0        u16  count N
offset+2 .. +2N u16  X[0..N-1]   (X[0] doubles as the low-extrapolation threshold)
offset+2N.. +4N u16  Y[0..N-1]   (Y[0] doubles as the low value, Y[N-1] as the high value)
```
**LERP1** (`0xCA4F4->0xCA51C(mode10)->0xD28DC`, Y1's raw pre-EMA-blend curve, index=`|gp-0x6ba6|`):
count=6, X=[0,512,1490,2529,3645,5120], Y=[16384,14657,11672,9365,8244,8187] — fades 2^14(unity Q14) to
≈0.5x as the torque/motor-rate composite grows.
**LERP4** (`0xCA23C->0xCA264(mode10)->0xD2888`, same index): count=6, X=[0,307,1024,1741,3072,6144],
Y=[16384,14392,10265,8997,8176,8176] — same fade-to-~0.5x shape, finer X resolution.
**Y1's EMA-blend coeff** (`0xCA06C->0xCA094(mode10)->0xD2006`) = **102** (/1024 ≈ alpha 0.0996) — matches
[[reference_accord_gp6bbe_angle_rate_path_traced_net_damping]]'s prior figure exactly, independently
reconfirmed. This is baseline's OWN slowest pole (single-pole, alpha≈0.0996) — at a 1kHz task this is
fc≈15.8Hz (moderate attenuation at 21Hz, ≈-4.4dB/-53°); at 100Hz task, fc≈1.6Hz (21Hz deep in stopband).

## 6. Task rate — [MEASURED partial] FUN_00034a72's sole caller is FUN_00022ca0 (unconditional); FUN_00022ca0 itself is TABLE-DISPATCHED, period field NOT decoded

`get_xrefs_to(0x34a72)` → one hit, `FUN_00022ca0`@`0x232c0`, `UNCONDITIONAL_CALL` (runs every tick of that
task, no phase gate at this call site). `get_xrefs_to`/`search_instructions` on `0x22ca0` found ZERO
instruction references (consistent with RTOS task-table dispatch elsewhere in this kit); a raw
little-endian byte-pattern scan (`search_byte_patterns("a02c0200")`) found it as **data** at `0xBB9E8`, a
32-byte-stride table starting `0xBB9B8` alongside entries for `FUN_00022b24` and `FUN_0002351e` (the
already-known engage-SM dispatcher). Each entry carries a function pointer, a per-task RAM context pointer
(24 bytes apart across entries — consistent with a per-task control block), and 2-3 words I could not
attribute to a period/phase field this session. **This remains the single most decisive open item** — it
governs whether Y1's alpha=0.0996 pole (§5) sits at fc≈15.8Hz (moderate, 1kHz) or fc≈1.6Hz (near-total
attenuation, 100Hz), and whether Branch B's -1dB@21Hz figure (already established at 1kHz per the V48B
memory) even applies to THIS caller. Next step: find the scheduler/dispatch loop that walks the
`0xBB9B8`-table and decode which field is the period (or byte-verify one of the two unattributed words
against a known task's already-established rate, e.g. FUN_0002351e's if that's independently pinned).

## Bottom line for the team-lead's build question

Hypothesis (b) (baseline = filtered copy of angle rate, washout/high-pass reframing) is **FALSIFIED** —
confirmed by full instruction trace, zero angle-rate reads in baseline's computation. Hypothesis (a) (slow
independent reference) is **PARTIALLY true**: baseline IS an independent torque/motor-rate signal, but
one of its two summed input branches (Branch B, raw torque via `gp-0x4f60`) is only lightly filtered
(-1dB@21Hz) — so baseline is not uniformly "slow," it can carry live 21Hz TORQUE content (not angle-rate
content) with unknown absolute magnitude relative to `angle_rate_raw` (depends on the RAM-resident LERP2
table's runtime contents — not statically dumpable — and the still-unresolved task rate). **Net damping
is the structurally-favored read (baseline has no rate-domain washout mechanism), but "guaranteed net
damping regardless of magnitude" is not provable from static analysis alone** — the torque-fast-path's
absolute contribution and the task rate are the two remaining gates on full certification.

## Related
[[reference_accord_gp6bbe_angle_rate_path_traced_net_damping]] — the session this extends; its "NET
DAMPING" framing is REINFORCED (angle-washout ruled out) but its dead-branch "combine" chain for LERP1/4's
index is corrected here.
[[reference_accord_gp6bbe_rate_error_speed_scheduled_lane]] — its "rate-keyed" label for 0xCA4F4/0xCA23C
is corrected (keyed by gp-0x6ba6, torque+motor-rate composite, not angle rate).
[[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]] — source of FUN_0003b66a's Branch B
alpha=0.5 figure and the gp-0x6a10/FUN_0003fc16 dormant-gate fact, both reused here.
[[reference_accord_fun41464_sign_filter_phase_response]] — source of gp-0x6abc's identity (motor/resolver
electrical rate) and the task-rate-ambiguity framing this file's §6 extends to a second function.
