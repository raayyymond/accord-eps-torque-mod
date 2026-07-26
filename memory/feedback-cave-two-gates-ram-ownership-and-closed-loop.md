---
name: feedback-cave-two-gates-ram-ownership-and-closed-loop
description: HARD RULE (self-enforcing, apply without being asked) — before ANY code cave / filter / dynamics-adding firmware change is called flash-ready, it MUST pass two gates that byte/CRC/disassembly/open-loop-DSP verification do NOT cover: (1) RAM OWNERSHIP — every byte the cave reads/writes proven free incl. writers and register-indirect/6-byte-extended-disp accesses; (2) CLOSED-LOOP STABILITY of EVERY control loop the touched signal participates in, esp. the always-on base-assist loop, with full magnitude+phase (Nyquist/margin), not a single-frequency magnitude. V48B bricked because it skipped both.
metadata:
  type: feedback
---

# Two mandatory gates for any code cave / filter / added dynamics (apply proactively, every time)

Before a cave/filter/dynamics change may be called "flash-ready" or safety-signed, it MUST pass BOTH gates
below **in addition to** the usual byte-exact / CRC / RWD-round-trip / Ghidra-re-disassembly checks. Passing
those usual checks is necessary but **NOT sufficient** — V48B passed all of them and still bricked violently
(full-authority oscillation, parked, no LKAS). See [[reference-accord-v48b-flashed-catastrophic-ram-collision]].

## GATE 1 — RAM OWNERSHIP (every byte, both directions, all encodings)
For EVERY RAM cell the cave reads OR writes:
- Prove it free by locating **readers AND writers** — "no readers found in a byte scan" is the exact trap
  that bricked V48B (a live status-byte *writer* was invisible to literal-displacement scanning).
- Check the **FULL multi-byte footprint** of every cell. V48B's fault was a 16-bit state cell whose **high
  byte** aliased a packed monitor/DTC status flag; the low byte was clean. Partial-cell aliases are a trap.
- Account for the encodings a naive scan misses: **register-indirect** (`movhi 0xFEDF,r0,rX` + `ld/st`) and
  the **6-byte extended-displacement** V850E2 form. Use Ghidra's decoded operands, not just byte patterns.
- Treat the **sparse-flag region `gp-0x1401..gp-0x1502` as POISON** for cave state. Vetted-safe slot on
  record: `gp-0x14E0` / `0xFEDF6B20` (32-bit clean). `gp-0x1500` (y1) is clean; `gp-0x14FC/F8` clean;
  `gp-0x14FA` is NOT (that was the collision).

## GATE 2 — CLOSED-LOOP STABILITY (of every loop the signal is in, not just the target loop)
- Enumerate **every control loop the touched signal participates in.** A driver-torque / sensor signal like
  `gp-0x4f60` is the input to the **always-on base power-steering assist loop** — not only the loop you are
  targeting. Anything you do to that signal, base assist inherits, energized the instant the motor powers up
  (no LKAS, no motion, no speed needed).
- **Open-loop filter validation does not cover closed-loop stability.** Poles-inside-unit-circle, DC unity,
  no-overflow, and a clean frequency-response plot are all open-loop. A stable filter dropped into a
  high-gain feedback loop is not a stable system.
- A notch/biquad is a **lightly-damped resonator** (V48B: r=0.979, ζ≈0.16, Q≈3.2). Its numerator zeros hide
  the ring open-loop; loop gain pushes its poles toward |z|=1.
- Check **magnitude AND phase across frequency (Nyquist / gain+phase margin)** of the loop WITH the element
  inserted — never a single-frequency magnitude multiply, and never only at the target loop's crossover.
  V48B checked notch phase only at 1–5 Hz; the base-assist loop acts at 15–28 Hz where the notch swings ±25°.

**Why:** These are the two failure dimensions that byte/CRC/disassembly/open-loop-DSP verification is blind
to, and they are exactly the two that bricked V48B. Code caves are this kit's only bricking class (V24/V27/
V48B); every cal-only build since V29 has been safe. A cave that "looks perfect" can still slam the motor.

**How to apply:** When reviewing or building any cave/filter/dynamics change, explicitly produce a RAM
ownership table (cell → readers → writers → free? incl. full footprint) and a closed-loop stability
analysis (list every loop the signal is in; Nyquist/margin with the element in place). If either cannot be
completed, the change is NOT flash-ready — say so plainly. Do this without being asked; it is a standing
gate, not a per-task request. And remember: even after both gates pass, a cave's ultimate test is
first-minutes on-car observation — flash only on explicit operator instruction naming file + bus.
