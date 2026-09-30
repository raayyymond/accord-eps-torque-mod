---
name: accord-lkas-pid-ki-integrates-the-command-and-taper-axis-is-driver-torque
description: CENSUS 2026-09-30 of every LKAS PID cal value on V294 — Ki on the difference operand integrates the COMMAND (sum r26 telescopes to the lag state) with NO leak, no anti-windup, reset only 0.1–2.05 s after a disengage (Ki 64 at idx 58 rails T in 6 s); D is a command-rate feedforward (one-tick-in-ten setpoint kick); the override taper's axis is DRIVER TORQUE (|bar>>5|, x0.30 from 64), not speed — reported, crux not yet re-read by the orchestrator; output lag 992/507 never changed on 272 images; only the shl immediate and add/subr are one-opcode knobs, everything else needs a cave
metadata:
  type: project
---

**Census, 2026-09-30 (`analysis-2020accord/studies/v295/census/V294-LKAS-PID-DESIGN-SPACE.md`, integer mirror = golden model on
80,000/80,000 ticks incl. Ki/Kd live; Ghidra = positive-controlled Python scan on every reader set):**
- **Cal-only knobs:** fb pole a `0xC63E8`, gain b `0xC63EA`, clamp C `0xC62E6`, the Kp / Kd / map banks (per-variant, selector 7,
  X = demand index), Ki + deadband 4 + I clamp 10240, P/D/sum/lane clamps, the output lag pair `0xC63EC/0xC63EE` (992/507 = 5.05 Hz,
  never changed on any of 272 images). **One-opcode knobs:** the shl immediate at `0x29D76` (FF multiplier, powers of two, independent of
  Kp·b) and add/subr at `0x28FA4` (operand type). **Everything else needs a cave:** any speed schedule, two operands at once, D on the
  measurement only, a conditional or leaky integrator, an instrument for I or D.
- 🛑 **Ki on V294's operand integrates the COMMAND:** Σ r26 telescopes to the lag state, so I = Ki·Σ(4·sp − r26) ramps on any held
  command — Ki 64 at idx 58 takes T from 598 to the clamp (2239) in 6.1 s; there is NO leak and NO freeze on saturation or driver
  override; it resets only at ramp end, 0.1–2.05 s after a disengage request (cells 0xC63F4/FA/F6). V294's shl 2 made the I input 8×
  coarser (deadband 4 on E>>5 = |sp| < 40). It is V283's rejected class; no instrument on the wire reads I or D (the tap reads gp-0x6b38).
- **D on V294 is a command-rate feedforward** (setpoint kick Kd·Δsp/2 on one tick in ten; +30 T mean during a slew-cap ramp at Kd 128);
  its jerk-feedback half is negligible (4.4e-5·Kd S per deg/s³). With I or D live the rail rises 2461 → 2481 (sum clamp binds).
- **The post-PID override taper (bank 0xCBBC4, arm B×D) is on DRIVER TORQUE:** axis C/D = gp-0x682f = min(|bar>>5|, 254|255), arm
  chosen by r25 = (gp-0x6803 == 2) at 0x29A82; ×0.30 from |bar>>5| ≥ 64 (listing 0x29A74–0x29A82, 0x29C56, 0x2A000, 0x2A062). This
  contradicts TRACE-2026-09-13-lkas-pid-tracked-quantity §2.4 (speed axis, km/h BELIEF) and resolves STATE's "taper axis OPEN" —
  **BELIEF until a second reader confirms it; the orchestrator has not re-read the crux.**
- Smaller: the demand path has a ±½-idx L/R asymmetry from the double floor on negative products (+1 wire → idx 1; −1..−16 → idx 0);
  demand scale 16.12573 wire counts per idx = 2^22/(4·65025); the dither addend gp-0x6b2c is identically 0 (LERP Y all 0, enable has 0
  writers); the golden model's `e5 = E>>5` comment cited 0x29D6C — the sar is at 0x29D7C (fixed 2026-09-30).

**How to apply:** never propose Ki on this operand without a leak (= a cave); do not spend a build on Kd for "tracking" — it is
command lead, not feedback; cite the taper as driver-torque-keyed with the BELIEF tag until verified.
Related: [[accord-lkas-path-pid-ki-is-zero]], [[accord-the-override-taper-arm-is-selected-by-a-0xe4-field-openpilot-sends-0-the-live-post-pid-fade-is-0xcbbc4]],
[[accord-v294-flew-r71b-v295-trim-gain-x1852-built]].
