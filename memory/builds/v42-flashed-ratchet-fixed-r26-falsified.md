---
name: v42-flashed-ratchet-fixed-r26-falsified
description: "V42 flashed 2026-07-20 — Change 1 (state-4 governor substitution, one byte at 0x454FE) FIXED the hard-turn ratchet on-car; Change 2 (zeroing r26) did nothing, so r26 is falsified and with r24 the whole Sensor-B rate family is out."
metadata: 
  node_type: memory
  type: project
  originSessionId: 1b5347d0-4bca-4b24-acf8-731450f48b64
  modified: 2026-07-20T06:30:09.611Z
---

**V42 was flashed 2026-07-20. The result is split and both halves are load-bearing.**

**Change 1 — `0x454FE` `bne`→`br`, disabling the state-4 governor magnitude-suppression substitution —
FIXED THE HARD-TURN RATCHET.** It is now a **CONFIRMED root cause**, not a hypothesis: the first symptom
in this lineage traced to a specific branch and closed by a single-byte edit, and the kit's first code
edit that is not a cave/trampoline. **Carry it into every subsequent build unchanged.**

**Change 2 — zeroing the `r26` adaptive torque-rate gain surface — did nothing. `r26` is FALSIFIED.**
Together with V39's `r24` null this eliminates the entire *identified* Sensor-B torque-rate derivative
family — a family-level negative neither build could deliver alone.

⚠ **But that family elimination was incomplete, and believing it was complete cost builds.** A THIRD
route carrying the same physical signal existed and had never been tested:
[[reference-accord-fun3a382-unfiltered-residual-lane]]. Falsifying two of three routes is not falsifying
the family.

**The operator's post-V42 datum is the most discriminating one this project has had:** the vibration is
present in *all* wheel movement driven purely by LKAS, and **vanishes when the driver adds hand torque**;
speed-independent, audible as grinding only near 5 mph (road-noise masking elsewhere).

**A correction of record it forced.** `gain_rescaling_invariance_analysis()` had the vibration filed as
"small command dithering around zero", which pushed every search *upstream* of the gain. Wrong: LKAS
turning the wheel alone against tyre/rack load is a **large** command, and driver assist *reduces* it. The
vibration lives in the same ">417-count, never-existed-before" downstream regime as the ratchet.

**Also downgraded:** the recorded elimination "motor torque ripple is RULED OUT". Its comparison case —
hand steering delivers comparable torque and is smooth — is *always* measured with hands on the wheel,
which is precisely the damping condition under test. The right conclusion was never "the motor is clean"
but "the motor's ripple has an unfiltered path back into the torque command".

Successor: [[v43-dirty-derivative-pole-built]].
