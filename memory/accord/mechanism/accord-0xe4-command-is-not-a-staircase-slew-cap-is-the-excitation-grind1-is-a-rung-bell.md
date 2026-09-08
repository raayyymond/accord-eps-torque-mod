---
name: accord-0xe4-command-is-not-a-staircase-slew-cap-is-the-excitation-grind1-is-a-rung-bell
description: MEASURED on V282 (r39/r3a/r3c): the 0xE4 command changes on 92 % of 100 Hz frames (no 20 Hz staircase, no 4-frame hold); it is slew-capped at 123 raw/frame by openpilot's own limit (0.03×4096) and the census's "top-1 % step" WAS that cap; ~54 % of D-clamp binds land on capped frames; the command's 20 Hz line is an ECHO (9 % share, open-loop mirror); grind #1 is a RUNG BELL (97.6 % of episodes decay, ζ≈0.026), so cutting excitation shrinks it.
metadata:
  type: project
  modified: 2026-09-08T05:30:52.032Z
---

# The 0xE4 command is not a staircase; the slew cap is the excitation; grind #1 is a rung bell (2026-09-07)

- **Cadence** [EVIDENCE, rlog-tools/studies/grind/wire_0xe4_20hz.py]: value changes on 92.2 % of engaged frames; 94.5 % of gaps are 1 frame. The
  "20 Hz stairstep held 4 frames" premise is falsified.
- **Slew cap** [EVIDENCE, fork opendbc honda carcontroller.py + wire_0xe4_slewcap.py]: |Δcmd| never exceeds 123; `rate_limit(…, 3·DT_CTRL)`
  × STEER_MAX 4096 = 122.88. Capped frames are 7–60× enriched inside grind episodes and 3.9–11.5× in the 0.5 s BEFORE onset;
  same-sign runs up to 854 ms; 54 % of D-clamp binding ticks are capped frames (base 12 %).
- **Echo** [EVIDENCE]: a sharp 20.03 Hz line in the command, on the car's frequency, swelling 2.7–5.5× when it grinds:
  openpilot's unfiltered 100 Hz angle measurement re-transmits the wheel's ring. Open-loop share of T's 20 Hz: 9 %
  (feedback path 63 %). The kit's 1 kHz mirror (GI.simulate) is OPEN-LOOP (logged rate as feedback): shares, not closed-loop bounds.
- **Rung bell** [EVIDENCE, wire_0xe4_burst_damping.py]: 127/130 episodes: decay after peak 97.6 %; τ_up 259–347 ms,
  τ_down 166–227 ms for bursts; both faster than phase-randomised surrogates (p<1e-4 on r39); nothing rails. ζ_eff ≈ 0.026.
  ⇒ positive damping ⇒ reducing the per-tick excitation reduces the ring; the 8–13 % direct share is a FLOOR of the benefit.

**How to apply:** treat any "smooth the command" lever as an excitation lever and score it against D-bind duty and the
18–22 Hz envelope; do not expect it to move feedback-dominated strata. See [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]].
