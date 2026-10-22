---
name: accord-cruise-pingpong-is-the-bosch-brake-floor-fork-038103ddd4-2026-10-21
description: "2026-10-21 evening: the no-lead SET-SPEED PING-PONG (route bb, to set, 2-3 mph under, back; ~18 s) = Bosch BRAKE MODE armed on -0.05..-0.13 requests and delivering -0.3..-0.4 (floor) with a -0.7 bite; the car never coasted (gas 0 at force -0.2, brake at -0.12). FIX fork accord-PTM 038103ddd4 PUSHED not pulled: Accord brake arms at force -0.45, releases at -0.20 (bosch_brake_force_thresholds); torque bar sign flipped 5a00f1f68a; rlogs decoded ON the device when the link is kB/s"
metadata:
  type: project
---

**State 2026-10-21 evening (E unless marked):** fork accord-PTM `272394d0 → 038103ddd4` pushed; device runs 272394d0 until pulled. Firmware V300 rev 2 unchanged.
Page https://claude.ai/artifact/KycTb96kJAGEpmnqSsrEYJ; handoff `docs/handoffs/2026-10/HANDOFF-2026-10-21b-cruise-pingpong-brake-floor.md`.

- **Mechanism:** route bb, 5.2 min no-lead cruise: brake mode armed 4.2/min on requests of −0.05…−0.13 m/s²; delivered p50 −0.31 for [−0.1, 0), −0.28 for [−0.2, −0.1), tracking only below ≈ −0.4; entry bite to −0.7…−0.9; sag p50 4.9 mph; gas mode over-delivers +0.13 (−0.7° pitch; standstill −0.8°, B mounting offset). 0 s of coast on the route. The planner is not the oscillator (|cmd − aTarget| ≤ 0.17).
- **Fix:** `bosch_brake_force_thresholds(HONDA_ACCORD) = (−0.45, −0.20)`; others keep (−0.12, −0.02). Replay: cruise entries 21 → 6–7, duty 47 → 13 %. Checked on the comma by loading the edited module from /tmp (no tree change). Readout `long_cruise_pingpong_read.py <route>` (READOUT line): entries < 1/min, coast duty > 20 %, sag < 2 mph. Risk (B): the coast frame (GAS −30000, BRAKE 0, active) is new on this car; expected: 1–2 mph creep over set on downhills.
- **Tooling:** when scp runs at kB/s, decode on the device (`device_extract.py` piped to `/usr/local/venv/bin/python -` with PYTHONPATH=/data/openpilot) and pull the npz; the reader falls back to `_scratch/cache/<route>/cruise_seg*.npz`. carState.cruiseState.speed is 0 under op long; use carState.vCruise (km/h).

**How to apply:** score the next drive with the READOUT line before touching anything; if the car does anything but coast in the new band, revert the two numbers; never re-propose the −0.12 arm point or a planner-side fix for this symptom. See [[accord-launch-jerk-is-the-bosch-gas-learner-fork-272394d0-2026-10-21]].
