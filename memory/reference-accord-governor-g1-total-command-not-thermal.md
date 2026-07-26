---
name: reference-accord-governor-g1-total-command-not-thermal
description: Governor G1 (FUN_0004503c) clamps the TOTAL aggregated command gp-0x6b94 (LKAS + all base-assist lanes), verified at instruction level -- not LKAS-only. Its "energy budget" is NOT a thermal integrator (structurally unreachable). Relabel it a motor-rate-adaptive total-command ceiling.
metadata:
  type: reference
---

# Governor G1 scope + "thermal" correction (Governor trace, 2026-07-21)

The operator's falsification test — "if G1 only limits LKAS it can't be thermal, since the driver
commands more torque than LKAS" — forced this. Result: the SCOPE half was right, the THERMAL half wrong.

- **G1 (`FUN_0004503c`, `m_motor_torque_governor`) clamps the TOTAL command.** Instruction-level:
  `0x453e0 ld.h -0x6b94[gp]` → clamped against `±(gp-0x4f64 × Q15) >> 15`. `gp-0x6b94` is the
  aggregator's FULL sum (boost + friction + damping + return-centre + LKAS + carriers). Every
  base-assist lane funnels through it; exhaustively bypass-checked (all non-aggregator readers are
  report-only DTC monitors, not motor paths). So driver-sourced assist IS governed — capped at the same
  ~4762 ceiling as LKAS at the motor (the driver's *hand* torque can exceed it; the *motor assist* can't).
- **The "energy budget" is NOT a genuine I²t/thermal integrator.** Producer `FUN_0007b022`: charge
  threshold cal `0xC509E`=5325 EXCEEDS the ceiling `0xC6202`=4762 that G1 already caps the watched
  quantity (`gp-0x6ba4`) below → the charge condition can never fire; and `0xC5164`=0 collapses the
  hysteresis to a same-cycle comparator. Structurally unreachable regardless. **Do not call G1 thermal
  protection — it is a motor-rate-adaptive TOTAL-COMMAND ceiling.**
- The motor-rate cap is a MIN-style **ceiling** (binds only when `|gp-0x6b94|` exceeds it), and it does
  **not bind at the ~139-count resonance amplitude** (9-34× above it). So G1 is **neither the vibration
  cause nor a useful lever.** Do NOT edit it: V40 proved slew edits there are hard-fault-coupled
  (recoverable, not thermal damage), and it is the operative protective ceiling.

Clean stage names between aggregator and motor: A=aggregator ceiling (`FUN_0003aa2c`, ±10240),
**B=G1 governor** (`FUN_0004503c`, ±≤4762 + slew + state-4 ratchet), C=post-gov comp-add
(`FUN_000456a4`), **D=shaper** (`FUN_00042af8`, final ±8192 `gp-0x6b98`), E=FOC/mixer, F=hard-shutdown
monitors (M1 `gp-0x3564` / M2 `gp-0x3550`).
