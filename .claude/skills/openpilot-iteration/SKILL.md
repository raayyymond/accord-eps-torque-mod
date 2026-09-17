---
name: openpilot-iteration
description: How to iterate on the StarPilot/openpilot lateral control fork for the 2020 Accord on V293 torque-mode EPS — the operator's standing preferences, how to measure a control change so the answer means something, the mechanisms this kit has already learned the hard way, and the fork/test mechanics that waste a session when you rediscover them. Load before proposing, simulating, or shipping any fork-side control change, before writing a metric to judge one, and before touching a toggle.
---

# Iterating on the openpilot fork

The EPS firmware is a **pure torque map** (V293). All control lives in the fork. `firmware-iteration`
covers the firmware side; this covers the fork. `CLAUDE.md` has the repo layout and the EVIDENCE/BELIEF
rule.

---

## The operator's standing preferences

- **Firmware changes are high-risk. Keep them minimal.** Torque map in the EPS, control in openpilot.
- **Do not put the 1 kHz inner loop back in the EPS.** If an inner loop is ever needed, close it on
  **angular velocity**, not acceleration.
- **Elegant and efficient, not just robust and accurate.** Terms that cost lag must earn it.
- 🛑 **Do not delete a feature to fix a symptom — gate it.** The lane-change jerk clamp held a corner
  back, so it was deleted; the operator overruled. The fault was that a blinker-started lane change
  applied the clamp to a *turn*. Gate, don't remove. Same for lane centering: it is a feature that
  works, it is toggleable, and it stays.
- **Score bands; let the operator score symptoms.** Report what moved, in his words.
- **Subagent models:** Sonnet for trivial, Opus for nuanced. **Never Fable.**
- **Branches:** StarPilot → `Dom`. Kit → `main`.

---

## Measure the goal, not a proxy for it

🛑 **A single-frequency describing function is not the goal.** `|H|` and THD at one amplitude and
0.2 Hz ranked four arms one way; band-passing into the frequency band where corrections actually live
ranked them differently and retracted the recommendation.

- **Band-pass the demand *and* the delivered accel, then regress one on the other.** Lane-centring
  corrections live in **0.25–0.60 Hz**; the ping-pong mode in **0.08–0.25 Hz**. Gain 1.00 = a match.
- **Drive a demand that looks like a road** — a slow sweeper, a wander, and the fine correction on top
  — and weight the metric toward the component you care about. A metric whose rms is dominated by
  large-amplitude content cannot see a small-signal change.
- ⭐ **An insensitive metric is a design failure on our side, not a verdict.** The first goal metric
  said all seven arms tie within 4 %. They did not; the metric could not see them.
- **Write the fail condition before the run.** Then honour it when it fires — five hypotheses died this
  way, including two that looked elegant. If a threshold has no physical floor, say so *before* the
  sweep, not after (a ring below the 0.10° angle quantiser is invisible on the wire).
- ⭐ **Verify an estimator on a known answer before believing it on a real one.** A delay-immune
  resonance fit passed its own speed-tracking validation and was still wrong by 7–14×; simulating a
  plant with a damping value chosen by hand is what caught it.
- **Identical results across a swept parameter mean the wrong mechanism**, not a weak effect. Three
  corner frequencies giving one answer is the tell.

---

## Mechanisms this kit has already learned

- ⭐ **A disturbance observer cannot tell commanded motion from disturbance.** Its filter passes
  everything below its corner, and the correction band sits below it. Whatever the feedforward
  under-supplies, the observer carries — and carrying it is what makes it cancel the commanded fine
  correction.
- ⭐ **Under-correcting a model does not buy margin. It relocates the error to a slower term.** Rev 6
  set the hold level short of the measurement so "the observer could absorb scatter". That is what the
  observer was eating. Rev 6.4 corrected it and delivery went 0.86 → 0.95 at 19 m/s.
- ⭐ **Move the feedforward and the observer's model TOGETHER.** Correcting only the observer rings the
  hold-and-kick test 0.33 → 3.89° at 8 m/s, because the feedforward's deficit then lands on P and I.
  `AccordHoldLevel` already scales both — that is why it works.
- **The plant is a spring plus Coulomb friction**, i.e. backlash of half-width F/k — 1.3° of play at
  19 m/s. Below that amplitude the rack emits *nothing*. That is the resolution floor, and loop gain
  does not reach it: the gain that breaks friction at 1 deg/s is 0.012, the margin ceiling through the
  60 ms round trip is 0.0016–0.0059.
- **Stiction biases every passive damping estimate low by 7–14×.** The rack is stuck most of the time,
  so the mode never rings. This forecloses offline identification of `b` from a normal drive, and
  explains two older failures (an estimate that was really `k·τ`, and a ring-down that returned null).
  An identification run must keep the rack **moving** — a bias plus the injected line.
- **A dither linearises without raising the small-signal slope**, so it fixes distortion, not delivery.
  It cannot break a stuck rack when its amplitude is under the Coulomb band.
- **100 Hz is enough sample rate, not enough loop bandwidth.** The binding constraint is the 60 ms
  round trip. Second floor: `carState.steeringRateDeg` is **1 deg/s per LSB** — a sub-LSB rate error is
  invisible, not under-gained.

---

## Fork mechanics that cost a session to rediscover

- **A new toggle touches five files:** `common/params_keys.h`,
  `starpilot/common/starpilot_variables.py`, `starpilot/common/safe_mode.py`,
  `starpilot/common/assets/device_settings_layout.json`, and the Galaxy layout test.
- 🛑 **`AdvancedLateralTune` gates the tune toggles.** Without it, `SteerDelay`, `SteerKP`,
  `SteerFriction` and `SteerLatAccel` silently do nothing.
- 🛑 **`get_honda_accord_mode_hz` reads the same stiffness table as the hold map.** Levelling the table
  in place moves the P/I error notch by √level. Apply a level *inside* the hold-torque function only.
- **An open-loop term goes at the return site** of `latcontrol_torque.update`, downstream of the PID,
  the hysteresis, the rate loop and the observer, so it cannot enter a feedback state.
- **`SteerLatAccel` is not a gain trim on this car.** The Accord feedforward is computed in torque
  through the hold map and never passes through it; 14 → 20 moves the delivered gain by 4 %.
- **Toggle configs**: `tools/make_galaxy_toggle_config.py` holds the codec (XOR `s8#pL3*Xj!aZ@dWq`,
  base64, `starpilot-toggle-backup` v1). Always run a **positive control** against the existing
  encoded/decoded pairs in `analysis-2020accord/reference/` before writing one.
- 🛑 **Configs can be byte-identical across revisions** when the change is a code constant. Then the
  **commit** is the attribution, not the config, and nothing on the wire will tell you which is running.
  Say so wherever the config is handed over.

## Running the tests here

```
cd /home/user/starpilot && .venv/bin/python -m pytest <file> -q --noconftest
```

`--noconftest` is required — the repo conftest imports the manager, which needs hardware modules. Two
native extensions ship as aarch64 and must be rebuilt for x86_64 before anything importing `controlsd`
will load (`visionipc_pyx.so`, `pandad_api_impl.so`; needs `opencl-headers` and `.venv/bin` on `PATH`
so scons finds `cythonize`). Hide them with `git update-index --skip-worktree`.
**Two failures are pre-existing: Bolt and Palisade.** Anything else is yours.

---

## Traps in your own analysis code

Each of these produced a confident wrong answer in one session:

- **Concatenating non-contiguous segments before a spectral estimate.** Every join is a step, and a step
  is broadband. Split into contiguous runs and average the PSDs.
- **Truncating a dict key to build a verdict table.** Three distinct arms collapsed onto one key and
  reported identical results.
- **Correcting a known error by an arbitrary factor.** The plant's spring was ×1.50; the test corrected
  ×1.15 and the small recovery read as proof the loss was structural. Use the plant's actual value.
- **Editing a document between two markers whose order has drifted.** A section-08-to-09 replacement
  deleted sections 10–14 because 09 had moved to the end. Render-check before publishing.
