---
name: openpilot-steer-delta-not-rescaled-for-gain
description: "⚠ DOWNGRADED 2026-07-20 - cannot explain a FAST vibration (the LKAS lane low-passes it away); survives only as a several-Hz explanation. Rescaling openpilot's PID for a firmware gain raise restores loop GAIN but not command SLEW RATE - STEER_DELTA is applied in normalized units upstream of STEER_MAX and the gain, so a 4x gain silently loosens the rate limit 4x."
metadata:
  node_type: memory
  type: reference
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T02:42:16.821Z
---

**A hole in the "just rescale the PID" compensation that is easy to miss and is not a firmware defect.**

`opendbc/car/honda/carcontroller.py:126` rate-limits steering **in normalized units, before** the CAN scaling:

```python
limited_torque = rate_limit(actuators.torque, self.last_torque,
                            -STEER_DELTA_DOWN * DT_CTRL, STEER_DELTA_UP * DT_CTRL)
...
apply_torque = int(np.interp(-limited_torque * STEER_MAX, STEER_LOOKUP_BP, STEER_LOOKUP_V))
```

`STEER_DELTA_UP = STEER_DELTA_DOWN = 3`, `DT_CTRL = 0.01` ⇒ ±0.03 per 10 ms tick, full scale in 0.33 s. `STEER_MAX = torqueBP[-1] = 4096` for the Accord, and `torqueBP == torqueV == [0,4096]` makes `STEER_LOOKUP` an **identity**.

Because the limit is applied to the PID's *normalized* output, it sits **upstream of both `STEER_MAX` and the firmware gain** — so quartering kp/ki does nothing to it. The slew ceiling in firmware lane counts is `(0.03 × STEER_MAX × 4 × gain) >> 15`, which scales with the **firmware gain**:

| build | lane counts per 10 ms tick | time to reach stock full scale (417 counts) |
|---|---|---|
| V9 stock (gain 891) | 13.4 | **312 ms** |
| V31 (gain 1782, 2×) | 26.7 | **156 ms** |
| V38 (gain 3564, 4×) | 53.5 | **78 ms** |

`interface.py` sets `steerActuatorDelay = 0.1` s. **At stock and at 2× the rate limiter was SLOWER than the actuator delay and dominated the loop, damping it. At 4× the rise time falls inside the delay and that damping is gone.** The crossover lands between 2× and 4× — and the vibration is first reported at V38, not V31. That is a retrodiction the model was not fitted to.

⚠ **DOWNGRADED 2026-07-20 — this was the session's leading vibration candidate and is no longer.** The arbitration IIR makes the whole LKAS command lane a **~1–5 Hz low-pass** ([[reference-accord-lkas-lane-is-a-lowpass]]), and this rate limiter sits **upstream** of it. So openpilot's command dynamics — however fast or slow the slew — cannot deliver a tens-of-Hz component to the motor at all. This survives only as an explanation for a **several-Hz** symptom, not a buzz. The arithmetic below is still correct and the `1/N` rule still generalises; only its claim on the fast symptom is retracted. **Test it as a SEPARATE trial** if the vibration survives V42 — never concurrently with a firmware change targeting the same symptom.

**Why:** stock's slow slew was load-bearing damping nobody knew they were relying on. It suppressed an oscillatory tendency the low-speed lateral loop always had; a 4× gain raise silently removed 4× of it.

**How to apply:** whenever a firmware torque gain is raised by N, scale `STEER_DELTA_UP`/`STEER_DELTA_DOWN` by **1/N** as well as the PID — for V38 that is `3 → 0.75`, which restores exactly stock's 13.4 counts/tick and 312 ms. ⚠ Sequencing, revised by the downgrade above: this is **no longer** the thing to test before building firmware. Run it as a **separate later trial** if a symptom survives V42 — never concurrently with a firmware change aimed at the same symptom, or the two interventions become unattributable. It remains a one-line comma-side change, reversible in seconds, no flash and no brick risk. Trade-off to state to the operator: openpilot becomes correspondingly slower to build torque on sharp corrections — that *is* stock behaviour, but it will be felt. Modelled as `openpilot_command_slew_invariance()` in `analysis-2020accord/model/eps_lkas_chain_model.py`. Related: [[reference-accord-gain-rescaling-invariance-partition]], [[reference-accord-pregain-deadband-c61b8]].
