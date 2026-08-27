# ★★ V55 FLASHED — the ~21 Hz IS in the motor command, and the loop is INSIDE the EPS

**Route `1c`, 2026-07-28** (two segments, 113 s on a uniform 100 Hz grid, parking-lot creep, max
1.98 m/s / 4.4 mph, 20.9% engaged, openpilot railed 33.7% of engaged time). Probe live: 10 distinct
field values, 100% interior, no rails.

## 1. The vibration is unambiguous, on two independent channels

| channel | engaged / disengaged, 15-26 Hz | peak |
|---|---|---|
| CAN 399 torsion-bar torque | **877×** | 20.90 Hz |
| CAN 399 `STEER_ANGLE_RATE` | **996×** | 20.90 Hz |

Angle rate is a *different physical quantity in the same message*, so this is not a torque-sensor
artifact. Fits the speed trend: 20.12 Hz @1.0 m/s (`1b`) → **20.90 @1.6** (`1c`) → 21.68 @4.0 (`1a`).
It is a **hands-OFF** phenomenon — on `1b`, engaged+hands-off carries **26×** the power of
engaged+hands-on. Hands damp it.

## 2. V55's partition answered: the mode IS commanded

`gp-0x6b98` peaks in the **same 0.195 Hz bin** as the sensor, coherence **0.93** at the peak bin.
**Route `1b` is a clean null control** — V54's constant field yields *exactly zero* command power, so
the pipeline cannot manufacture the peak.

Also `bit7 = 1` in 11,128/11,128 ⇒ damper variant INDEX ≥ 10 ⇒ **V44/V47 hit the LIVE tables; the
missing-damping hypothesis is genuinely falsified.** That thread is closed.

## 3. ★★ openpilot is NOT the source — the rail is the natural experiment

```python
# LKAS lane budget: openpilot counts -> gp-0x6b98 counts
DC   = 4.0 * 3564 / 32768          # setpoint x(-4), then Q15 gain 0xC646C  = 0.4351
IIR  = 1/sqrt(1 + (21/4.97)**2)    # gp-0x3d3c pole 0.96875 @1kHz -> fc 4.97 Hz = 0.2314
# openpilot's own 21 Hz amplitude = 31.7 counts
31.7 * DC * IIR   ==  3.2 counts        # what the LKAS lane can deliver
# MEASURED in gp-0x6b98:            120.5 counts   -> 38x over budget
31.7 * DC         == 13.8 counts        # even with the low-pass DELETED -> still 8.7x short
```

**And while openpilot is RAILED its 21 Hz content is exactly 0.0, yet the command still carries
105.8 counts at 21 Hz** (coherence 0.66). ⇒ the oscillation is generated **inside the EPS**,
downstream of the LKAS lane's low-pass.

## 4. ★ The carrier's fingerprint: FLAT, unfiltered, ~0.2

H1 estimator `P_tc / P_tt`, engaged runs, 9 **independent** segments (coherence significance 0.312):

| f | H1 (counts of `gp-0x6b98` per count of CAN-399 torque) | coherence |
|---|---|---|
| 0.98 Hz | **0.192** | 0.672 |
| 1.95 Hz | 0.148 | 0.370 |
| **21.09 Hz** | **0.216** | **0.687** |

phase(sensor→command) +171° @1 Hz → −161° @21 Hz — only ~28° of rotation across the whole band.
⇒ **a near-proportional, inverted, ~4 ms-lagged feedback with NO low-pass.**

**A lane behind a pole cannot produce a flat transfer to 21 Hz.** That is what rules out the whole
`0xC646C` reader set — see [[reference-accord-c646c-shared-gain-not-lkas-only]].

## How to apply
- The vibration is a **closed-loop instability internal to the EPS**, not an openpilot artifact and not
  a command arriving from outside. Do not propose openpilot-side work ([[feedback-no-openpilot-side-modifications]]).
- Any candidate lane must be **unfiltered at 21 Hz** and able to produce ~0.2 counts/count.
- **Direction is still not proven.** H1 in closed loop with no external excitation cannot separate plant
  from controller — the damping sign remains open. See [[reference-accord-gp6ad4-lane-and-c6af0-output-gate]].
- Analysis scripts: `rlog-tools/probe/decode_v55_motorcmd.py`; the session's Welch/H1/rail scripts are described
  in `docs/handoffs/2026-07/HANDOFF-2026-07-28-v55-drive-oscillation-is-internal-and-v56-mute.md`.
