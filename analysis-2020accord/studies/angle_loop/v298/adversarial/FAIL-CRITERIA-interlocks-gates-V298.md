# V298 adversary INTERLOCKS-GATES — FAIL criteria, written BEFORE any analysis

Written 2026-10-01 17:25 PDT, before reading the build script, the image, or the design page in detail.
This file is not edited after analysis starts; the report (ADV-interlocks-gates-V298.md) scores against it.

## DO_NOT_FLASH if ANY of these is shown on the BUILT image (sha 177abf04...)

F1  A new branch / jr / jarl / table pointer resolves to an address the design does not name
    (relink defect class): G-table ptr != the table's actual start, FRZ/CAM return != a valid
    instruction boundary in FUN_00028ea6's epilogue path, op-skip jr != the Honda skip epilogue.
F2  Register liveness: the cave clobbers a register that is live at the hook return (other than the
    ones the stock code at the hook also overwrites), or reads r25 / r14 / any input that is NOT what
    the design says at the hook (r25 != camera-field compare result, r14 != ramp).
F3  GATE 1: the cave or an in-place edit WRITES a RAM word that has another writer, or that is read
    by another task with a different meaning, without that being designed; or reads a word whose
    owner/writer is not established (including register-indirect writers).
F4  A torque path exists that produces non-zero motor demand from the new lane when the setpoint is
    NOT valid/current: 0xE4 timeout, checksum/counter fault, STEER_REQUEST=0, field != 2
    (camera / wrong payload), gp-0x67fe != 2, mode == 3 — i.e. any of these leaves the integral,
    P or D term driving torque without decaying to zero.
F5  Integer overflow / sign-extension / truncation reachable in the cave on reachable inputs that
    flips sign or saturates to a large wrong torque (int16 store of an int32, sar/shl wraps).
F6  A changed cell (cal or record) has a consumer outside the angle lane (EME, governor, lockstep
    monitor, DTC plausibility) whose behaviour changes in an unsafe direction (monitor disabled,
    threshold widened past a safety margin, a check now trivially satisfied), undesigned.
F7  The A2/B2/op-skip guard semantics on the real control flow differ from the design such that the
    PID runs when it should not (ramp==0, request!=1) or the integral is written on the skip path.
F8  GATE 2 on the image's actual read-back cals/table: closed-loop unstable (any pole in RHP / |z|>1)
    or phase margin below the design's own stated floor at any speed knot, or gain margin < design
    floor, in the angle loop or the inner loops the signal is in.
F9  The flight bytes differ from what H1 validated (the shipped cave is not the cave that was
    scored), or the .rwd payload does not decode to the plain image.
F10 The camera interlock is inverted (camera frames run the lane, fork frames are inert) or the
    CAM handler leaves a non-decaying torque term.

## PASS_WITH_DEFECTS if
  None of F1-F10, but: a decision-bearing premise is BELIEF only (e.g. camera field value), a census
  is incomplete with a stated gap, a verification claim in the builder's report is wrong in a way that
  does not change the safety verdict, or a non-safety correctness defect exists.

## PASS if
  None of the above, every census positively controlled, every crux verified from bytes by me.
