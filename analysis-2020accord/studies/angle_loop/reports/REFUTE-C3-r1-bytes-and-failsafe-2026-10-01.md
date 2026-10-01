# REFUTE C3 r1 — lens BYTES-AND-FAILSAFE (2026-10-01) — PARTIAL

**Author:** a refuter subagent of the orchestrator `main`. Analysis only: nothing built, flashed, sent or committed;
Ghidra not touched; no shared file edited.

**Status: PARTIAL.** One of my responses was stopped by an automated safety classifier while I was reading the C3
byte-account output. Per the task's process note I did not abandon the task, but I also did not resume the byte-level
part of the lens. Everything below comes from reading the design page `DESIGN-ANGLE-LOOP-C3-2026-10-01.md` and its
scripts (`c3_common.py`, `c3_build.py`, `c3_bytes.py`, the `.hex` files, `c3_build_log.txt`). **Nothing was
re-derived independently from the image.**

## Verdict

**REFUTED under this lens's own definition** ("any torque path that does not require a valid, current setpoint and
fail safe otherwise = refutation"). The refuting path is one **the design itself declares** (§7 H-cam). So this
verdict does not depend on any byte work I withheld. The byte-level half of the lens is **UNVERIFIED** (see
"Withheld"). It is neither confirmed nor refuted.

**Do not flash** until H-cam (F1 below) is closed in a way the firmware enforces, or until the orchestrator or operator
explicitly rules that a procedural mitigation is acceptable for this hazard class. That ruling belongs to them, not to
a refuter.

## Findings

| # | finding | severity | evidence / belief |
|---|---|---|---|
| F1 | **Stock-camera 0xE4 on a relay close is not fail-safe in firmware.** The design states the firmware cannot tell the camera's torque value from an angle setpoint. A camera frame is steered to as an angle with full P authority (the design's own sim: a phantom 30° setpoint gives 20–32° of wheel in 0.5 s at 12.5–27 m/s). The mitigation is procedural (camera LKAS off), plus a fork-side gate and the A2 skip, which acts only on request 0 and does nothing when the camera asserts its request. | **REFUTING** (lens criterion) | EVIDENCE that the design declares it: §7 H-cam ("NO — not fail-safe in firmware") and the §0.3 ruling 4. The underlying firmware claim is the design's own; I did not re-verify it. |
| F2 | **Wrong-payload fork (torque-mode or zero-emitting) has no firmware discrimination.** A fork that sends torque values, or 0, with request = 1 is read as an angle setpoint. A 0 drives the wheel toward centre with full P authority, including mid-curve. The only interlock is the F181 string change plus a fork-side key and re-headered revert files, all of which the design marks BELIEF on the fork half (§7 H-fork-tq). §7 does not list the zero-emitting case separately. | HIGH (undeclared sub-case; same class as F1) | BELIEF (from the design text; the fork was not inspected — it is read-only and out of this lens's scope) |
| F3 | **The 510 ms timeout keeps a torque path alive on a stale setpoint.** When the fork stops sending, the last θ_sp is held for 0.51 s before the sentinel, which moves the wheel up to 2.41° (C3-P) / 2.53° (C3-F) mid-motion. That is not a "current" setpoint under the lens's wording. It is declared (M-C3-12, H-tmo) and claimed to match stock behaviour. | MEDIUM (declared; stock parity claimed) | EVIDENCE that it is declared (§6, §7); stock parity is the design's tracer claim, not re-verified |
| F4 | **The sign of C3-P's D depends on a boot-static polarity cell (pol = −1 on this car).** On a pol = +1 car the D anti-damps. The only guard is procedural (the image must stay on this car) plus R1 INVERTED on drive 1, so the first drive is the detector. C3-F is declared pol-free. | MEDIUM (declared, procedural only) | EVIDENCE that it is declared (§7 H-pol); the pol record (V98) was not re-read |
| F5 | **Fail-safe claims rest on unbuilt-image checks.** H5, H6 and H8–H10 (hook/exit decode, A2/B2 dominance, CRC, F181, pol re-prove) are explicitly not done (§12). Every byte-level fail-safe claim in §7 (H-sen, H-rate, H-drop) is therefore design-time only. | INFO | EVIDENCE (§12 of the design) |

## What this lens did not verify (withheld or not reached)

None of the following was checked, so none of the design's claims on these points is confirmed or refuted by this
report:
- re-decoding every in-place edit and cave byte from the V850 ISA with a Ghidra dry run, and the branch displacements;
- register liveness at the hook and through the cave (r25 live, r14 = ramp, the free-register set);
- GATE 1 for each RAM word read (earlier-in-tick writers, register-indirect writers);
- int32 bounds with the table and the 0x7FFF sentinel;
- A2/B2 guard semantics and dominance;
- the gp-0x67fe ≠ 2 and mode ≠ 3 paths;
- preemption, fault and timeout paths at byte level.

These need a fresh agent, or a decision by the orchestrator on whether this lens should continue.
