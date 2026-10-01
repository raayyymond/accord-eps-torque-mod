---
name: accord-lkas-feedback-is-a-100hz-hold-and-the-zero-cave-angle-loop-edit-set
description: "TRACED 2026-09-30 (three tracers, crux re-verified by the orchestrator from the TCB table at 0xBB910 and Ghidra callers): the LKAS lane FUN_00028ea6 runs in RTOS task 0 (every 1 ms tick) but BOTH its feedback operand gp-0x6a56 (rate) and the EPS angle gp-0x6a00 are produced in task 4 (every 10th tick) — every rate-loop build V282..V295 closed on a 100 Hz sample-and-hold (1–10 ms stale, mean 5.5 ms; TRACE-2026-09-10's 'no staleness' is wrong). gp-0x6a00 = signed halfword, 0.1 deg/count, = +10 x openpilot steeringAngleDeg, no clamp, forced 0 unless gp-0x67fe in {1,2} (2 throughout driving), wraps to ~+32700 on the -0x8000 baseline sentinel (mode gp-0x679c != 3). ZERO-CAVE ANGLE P LOOP, bytes verified in V295: 0x28F4E aa95->0096 (x := gp-0x6a00), 0x28FA4 89d1->c9d1 (subr->add), cals a=0 b=8192 C=65535 (r26 = 16*theta, 2-tap FIR), 0x29D6A 0880ed80->24875296 (sp := gp-0x69ae = clamp(-4*raw, +-16384), bypassing the 8-bit demand index whose 1.61 deg steps make the map path unusable) => E = 16*(theta_sp - theta) exactly, theta_sp = -raw (0.1 deg per 0xE4 count, +-409.6 deg). Optional: 0x29EDE/0x29EE0 rate damping D = (-Kd*x)>>3 (negation required: sign(dtheta/dt) = sign(x)); 0x29A5A ba05->b005 = I reset whenever ramp == 0 (closes the override-latch wind-up: I is otherwise NEVER reset in that case). Kp schedule X axis is now |theta_sp| in 1.61 deg steps (cal-only angle-magnitude schedule); a SPEED schedule or a driver-torque I bleed needs a cave (no LERP helper exists; speed gp-0x6a5e 64 counts/km/h at 100 Hz; |driver torque| gp-0x4f68). SAFETY ON THE CAR NOW (V293–V295): an 0xE4 RX fault writes the setpoint sentinel 0x7FFF and the PID keeps running through the 2.048 s ramp-down => P rails in a fixed direction (2245/1860/1259 T at 0.1/0.5/1 s if the lane was already pushing that way); stock commanded max RATE there, not max torque; cal 0xC63F6 16->328 shortens it to 0.1 s; downstream gating untraced (in progress). Free RAM gp-0x6c44/-0x6c40/-0x6c3c (V289) and gp-0x6d74 (V292) flight-proven; free code 0xC4BD8–0xC4FEF (1048 B, dirties only CRC trailer 0xC4FFC)."
metadata:
  type: reference
---

Traces: `docs/traces/TRACE-2026-09-30-angle-signal-gp6a00.md`, `TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md`,
`TRACE-2026-09-30-speed-driver-torque-lerp-and-ram-homes.md`. Mirrors (byte-exact, edits as switches, golden model agrees
tick-for-tick on V295): `analysis-2020accord/studies/angle_loop/lane_mirror_v295.py`, `angle_signal_mirror.py`.

**Why it matters:** the whole rate-loop record assumed 1 kHz feedback; a 10-tick hold is ~36 deg of phase at 20 Hz on top
of the 2–3 ms delay the record modelled. For the ANGLE loop (2–4 Hz crossover) the hold costs ~4 deg at 2 Hz — small —
and the cheapest loop needs NO cave: 8 code bytes + 3 cals. The fork must send raw = −10·steeringAngleDeg whenever it is
not steering (0 = "steer to centre" through the 2 s ramp-down).

**Stale memories flagged by the tracers (not edited):** the dispatcher memory's state byte is gp-0x679c, not gp-0x67DC;
gp-0x67fe has 5 writers, not 4; register_map_and_taper §3 (fade B's axis is gp-0x682f = driver torque, not speed);
op_0e4_full_path (normal gp-0x69ae store is 0x526F2; sentinels at 0x5268C/0x52726/0x527C6).

Related: [[project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent]], [[feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify]].
