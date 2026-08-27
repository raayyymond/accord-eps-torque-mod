---
name: reference_accord_driver_side_inertia_hypothesis_refuted_synthesis
description: Answers the operator's own hypothesis ("driver-side steering wheel inertia feedback drives the ratchet") directly -- REFUTED as actionable. Both inertia/acceleration-shaped terms in this firmware (gp-0x6b26 via 0xCBE74, and FUN_0003b8f6's 0xC646E) are structurally motor/resolver-rate-derived (not literal driver-torque-derived), both are measured/derived DISSIPATIVE-signed (not anti-damping), both are too small to source the measured -3073..-4890ct pump, and the one road-tested in both directions (gp-0x6b26) got measurably WORSE when reduced (V94, operator-aborted). Synthesizes gp6b26-is-inertia-not-damping + fun36c12-sign-settled-dissipative + gp6b26-closed-both-directions-v94-aborted + micro-regime-has-no-scheduled-dissipation + V102's independent 0xCBE74 "inert both bands" re-test into one answer, with a fresh independent closed-form phase re-derivation (matches prior work to 4 sig figs) and a fresh byte-read of the current V101/V102 on-car cal state.
metadata:
  type: reference
---

# The operator's "driver-side inertia feedback" hypothesis — REFUTED as actionable, 2026-08-20 (`ratchet-inertia` task)

Briefed by team-lead to trace `gp-0x6c2c → gp-0x6b26` (V102's ratchet half) and check its `Re(Z)` sign
against the measured 6-9Hz pump (-3375/-3176/-3073 ct, `[[accord-rez-antidamping-replicated-three-drives]]`).
**Answer: the hypothesis is structurally real (the mechanism exists) but REFUTED as the cause and REFUTED
as an actionable lever — closed in both directions with on-car evidence, before this session started.**

## What exists, confirmed fresh this session [EVIDENCE — decompile + byte read, not relayed]

`decompile_function(0x36c12)` and `decompile_function(0x41464)` on stock `code.bin` this session
reproduce the producer chain byte-for-byte against `[[reference_accord_gp6c2c_transfer_function_triple_verified]]`
and `[[reference_accord_fun36c12_sign_settled_dissipative]]`:
```
FUN_00041464 (1kHz):
  s1 += (rate<<10 - s1) * cal(0xC643C)=37 >> 7        # EMA1, alpha=37/128     [0x415d4-0x415e8]
  d  = s1[n] - s1[n-1]                                 # backward difference    [0x41602]
  d32 = clamp(d*32, +-0xfa0000)                         # [0x41612]
  gp-0x6c2c = (EMA2(d32, alpha=cal(0xC40DC)=22, >>6)) >> 9     # [0x41632-0x41644, final >>9 per prior trace]
FUN_00036c12 (1kHz):
  Y_speed = LERP(gp-0x6a5e /*voted VEHICLE SPEED*/; 0xCBE74[mode])   # always negative, byte-confirmed
  raw = ((gate(gp-0x6c2c) * Y_speed) >> 6) * 0x111                   # 0x111=273
  gp-0x6b26 = clamp(raw >> 18, +-cal(0xC407E))
```
`rate = gp-0x4f50` (resolver rate estimate). `gp-0x6c2c` is confirmed **angular ACCELERATION of the
MOTOR/resolver rate** — NOT the raw torque sensor, NOT literally "driver torque" differentiated.
**This firmware has no term anywhere found that differentiates the raw torque sensor (`gp-0x4f60`)
twice to build a literal driver-input inertia estimate — every "inertia-shaped" term found uses the
motor/resolver rate as its base signal.** Worth stating plainly if the operator's phrase is taken
literally.

**Current on-car cal state, fresh byte read this session** (`stock_fw_dump/code.bin` vs both
`_v101_..._plain_image.bin` and `_v102_..._plain_image.bin` in `ACCORD_FIRMWARE_ROOT/analysis-2020accord/`):
```
                 stock                    V101 = V102 (current base)
0xCBE74 m26 Y    (-9830,-5734,-1966)      (-14745,-8601,-2949)   = exactly x1.5, engaged only
0xC407E          511                       511                   unchanged
0xC643C / 0xC40DC (gp-0x6c2c poles)       37 / 22                 37 / 22   unchanged, VIRGIN
0xC646E (Path-2 INERTIA gain, FUN_0003b8f6)  1428                 1428      unchanged, VIRGIN
0xC40D6 (Path-2 INERTIA EMA alpha)        246                     246       unchanged, VIRGIN
```
Matches every claim in `docs/STATE.md`/`docs/BUILD-LINEAGE.md` exactly — no drift found.

## The sign check [EVIDENCE — closed-form re-derivation, independently reproduces prior work to 4 s.f.]

Fresh closed-form z-domain calc (fs=1000Hz, confirmed 1kHz task rate) of `gp-0x6c2c` vs raw rate:
7.79Hz gain=3.0804 phase=+76.43° — matches `[[reference_accord_gp6c2c_transfer_function_triple_verified]]`'s
"3.080x .../+76.4°" to 4 significant figures, independent re-derivation. Folding in `Y_speed`'s always-
negative sign (+180°) gives phase(`gp-0x6b26`/raw rate) = **256.4° ≡ -103.6° at 7.79Hz**, `cos = -0.235`
— i.e. **NEGATIVE real part vs rate, "dissipative" in this file's own sign convention** (matches
`[[reference_accord_fun36c12_sign_settled_dissipative]]`'s "Re<0 ⇒ dissipative" table exactly, same
number). Robust across the whole 6-9Hz band (cos -0.18 to -0.27) and **identical in sign whether Y_speed
is stock's -9830 or V101/V102's x1.5 -14745** — the dose never flips this sign, only its magnitude.

🛑 **Convention warning, stated explicitly because it is easy to get backwards**: this file's convention
(`Re<0 ⇒ dissipative`, phase measured vs the term's OWN driving signal, motor rate) is the OPPOSITE
polarity of `[[accord-rez-antidamping-replicated-three-drives]]`'s whole-car convention
(`Re<0 ⇒ anti-damped/pumping`, phase measured as driver-torque/wheel-rate cross-spectrum, confirmed this
session by reading `rlog-tools/_scratch/logs/v92_rez.log` directly: 6-9Hz row reads `phase -125.3° coh² 0.769 Re(Z)
-3375.2`, i.e. `Re(Z)=|Z|cos(phase)` with NEGATIVE meaning anti-damped). **Do not compare the two `Re<0`
labels directly without translating.** The two are NOT the same physical quantity (one is a small-signal
lane transfer function in isolation; the other is a closed-loop driver-torque/wheel-rate impedance) —
this is exactly the "isolated-stage phase analysis is not sufficient, phase accumulates around the loop"
trap `[[accord-gp6b26-closed-both-directions-v94-aborted]]` already names.

**The number that IS directly comparable, inherited not re-derived this session** (flagged BELIEF —
I could not locate the source script under `rlog-tools/` to re-run it myself; treated as a trusted
prior-session record per this kit's memory conventions, not independently re-verified byte-for-byte):
`[[accord-gp6b26-closed-both-directions-v94-aborted]]` reports V96's on-car comparator measured the
delivered `gp-0x6b26` lane at **+137°/+139° vs WHEEL rate, |cos|=0.73, +518/+565 ct of POSITIVE Re(Z)**
— in the SAME whole-car convention as the -3375ct pump figure (`Re>0 = damped` there). **This is the
opposite sign from the pump, and only ~15-18% of its magnitude.** ⇒ `gp-0x6b26` cannot be the pump; at
most it is a small brake partially opposing it.

## Liveness in the micro regime (1-13°/s) [EVIDENCE, cited from an existing full census]

`[[reference_accord_micro_regime_has_no_scheduled_dissipation]]`'s census of every centring/damping
candidate on the current build (byte-verified against the V96 image, unaffected by anything since):
**`gp-0x6b26`/`0xCBE74` is LIVE in the micro regime** — one of only three things still live there
(alongside the PID D-term and the r24/r26 torque-phase-advance lane), while **all three scheduled
viscous dampers (end-stop cushion, base-assist `ch0`, comp-add) are gated to exactly ZERO**. So the
mechanism is not inert-by-operating-point — it is genuinely active exactly where the operator's
micro-ratcheting complaint lives; it is just wrong-signed and too small to be the cause.

## Why this is CLOSED, not merely unpromising — on-car evidence in BOTH directions

| direction | build | result |
|---|---|---|
| RAISE x1.5 (engaged only) | V91/V92 | measured INERT, TWICE independently: route 78/79 stratified ratio 0.99 [0.91,1.26] (`[[accord-cbe74-dose-measured-inert-wrong-mode-record]]`); **and again this session's V102 predecessor** via a de-confounded shape-floor 2×2 (V90 r77 vs V91 r78), `k`=0.86-0.90 at BOTH 22-26Hz and 6-9Hz against a 1.45x floor (`docs/handoffs/2026-08/HANDOFF-2026-08-20-v102-the-gain-is-the-carrier.md` §3.2, `docs/BUILD-LINEAGE.md`'s nine-killed table) |
| LOWER to 0.167-0.75x | V93/V94 | flown (route `7d`), fault-free, **operator ABORTED the drive**, verbatim: *"made the stuttering and grinding worse, by a lot... vibrated the entire car... not safe to drive"* |

Two independent RAISE measurements agree (inert); one LOWER measurement exists and it is the single
worst subjective on-car outcome associated with this specific mechanism in the kit's whole record.
**Going further down (e.g. to zero) is not an open question — it extrapolates a monotonic trend that
is already known to be bad in that direction, from a real drive, not a simulation.**

## The second candidate, checked and also excluded [mostly relayed — not independently re-derived this session]

`FUN_0003b8f6`'s Path-2 "INERTIA" term (`0xC646E`=1428, gain on a THIRD independent backward-difference
of `gp-0x6abc`, itself resolver-rate-derived — NOT the FOC core's `gp-0x6c2c`, a separate filter chain
off the same physical sensor) is the only other differentiator-of-a-motor-side-signal found in this
firmware. Per `[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]]`'s existing
instruction-level trace: **also dissipative-signed** (real part vs rate positive/never inverts across
7.79-28.5Hz, same conclusion class as `gp-0x6b26`, different sign-convention statement of the same
physical fact), **VIRGIN** (confirmed this session — byte-identical to stock on V101/V102), and running
at only **1-6% of its own clamp** (real headroom, unlike `gp-0x6b26`). ⇒ Same problem as `gp-0x6b26`:
right sign to be a brake, wrong sign to be the pump, so it cannot explain the measured anti-damping
either — and **raising it is "add damping," which the operator's own V103 brief forbids regardless of
score.** Not re-derived from fresh disassembly this session (time budget); flagged as inherited, not
newly verified, unlike the `gp-0x6b26` chain above.

## Bottom line

**CONFIRMED**: a real, live, motor-rate-derived acceleration/inertia-shaped feedback mechanism exists
(`gp-0x6b26`), matching the operator's description structurally.
**REFUTED**: that this mechanism is the SOURCE of the 6-9Hz anti-damping, or that reducing/removing it
would fix the ratchet. Wrong sign (dissipative, not anti-damping, by both an independent closed-form
re-derivation and an inherited on-car measurement), too small in magnitude (~15-18% of the pump), and
on-car evidence in the "eliminate it" direction is the single worst subjective result in the kit's
record for this mechanism.
⇒ **No cal-only or cave lever on this specific hypothesis survives.** The 6-9Hz pump's actual source is
outside the inertia/differentiator family as literally construed — see
`[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]]` /
`[[reference_accord_kd_pid_dterm_priced_and_manual_gate]]` for the nearest surviving (but also NOT-READY,
per `docs/BUILD-LINEAGE.md`'s nine-killed table) relative in the differentiator family, and note it sits
in a DIFFERENT function (`FUN_0003a382`'s PID D-term on the tracking ERROR, not a motor/driver rate) —
out of this file's scope, flagged for whoever chases the pump next (structural/loop-delay explanations,
e.g. the V102 "a pole moved" finding, may be the more productive direction for the actual 6-9Hz source).

## Related
[[accord-gp6b26-is-inertia-not-damping]] — the original (superseded-in-part) "pure inertia, dissipates
nothing" framing that motivated V93/V94's cut; its own algebra is fine, but the closed-loop measurement
it predicted against is `[[reference_accord_fun36c12_sign_settled_dissipative]]`'s correction.
[[accord-gp6b26-closed-both-directions-v94-aborted]] — the consolidated lineage + V94 abort quote this
file leans on for the decisive behavioral evidence.
[[reference_accord_micro_regime_has_no_scheduled_dissipation]] — liveness census.
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] — the second candidate.
[[accord-rez-antidamping-replicated-three-drives]] — the pump measurement this file's sign check targets.
