# HANDOFF 2026-10-21b — set-speed ping-pong = the Bosch brake floor; torque bar sign

Previous: `HANDOFF-2026-10-21-launch-jerk-torque-bar-error-clip.md`. **No firmware built or flashed.** Fork accord-PTM `272394d0` → `038103ddd4` (2 commits) PUSHED; the device runs 272394d0 (route bb flew on it) until `git pull origin accord-PTM` + reboot. Page: https://claude.ai/artifact/KycTb96kJAGEpmnqSsrEYJ.

## 0. Operator's feedback (2026-10-21 evening)
1. Torque bar reversed ("clearly steering wheel is pulling the opposite direction"). 2. On the latest route (bb, bookmark set) the long control ping-pongs with no lead: to the set speed, 2–3 mph under, back up, repeat. "Design and implement a robust, elegant, and minimal fix." Also: fetch the route over ssh; save tokens by waiting for all segments rather than analysing piecemeal.

## 1. Data path (the link to the car was kB/s)
`scp` of 17 × 13 MB rlogs stalled; each segment was decoded ON the comma (`/usr/local/venv/bin/python`, the fork's own cereal) by a script piped over ssh and only a ~200 KB compressed table came back (`_scratch/cache/000000bb--12b73fe35c/cruise_seg*.npz`, schema of `long_cruise_pingpong_read.py`). The reader falls back to that cache when no rlog is local. Raw rlogs for bb are NOT in `analysis-2020accord/rlogs/`.

## 2. Mechanism (E) — route bb, 5.2 min no-lead cruise, 32–65 mph
- Brake mode armed 22× (4.2/min), each on a request of −0.05…−0.13 m/s² (force ≈ −0.12 once the −0.1 hill term and the wind term ×1.1–1.8 are added).
- Delivered vs asked (50 Hz): brake mode at request [−0.1, 0) → aEgo p50 −0.31; [−0.2, −0.1) → −0.28; [−0.3, −0.2) → −0.42; it tracks only from [−0.5, −0.3) down (−0.43, −0.03 off). Entry bite min aEgo −0.6…−0.9. Gas mode over-delivers +0.12…+0.16 at every request (the −0.7° pitch's gravity term; standstill pitch −0.8°, BELIEF partly a mounting offset).
- The cycle: brake arms → sag p50 4.9 mph over 4–6 s → release at −0.02 when the planner is back positive → aT +0.3, gas 300, +0.5 m/s² → 0.3 mph over set → aT drifts to −0.05 → brake. Period ~18 s, band envelope 2.1 mph p50 / 4.8 p90.
- Coast never happened: 0 s of gas-0/no-brake (gas lookup hits zero at force −0.2, the fork armed the brake at −0.12; upstream arms at −0.2, so upstream never coasts either).
- The planner is NOT cycling on its own: max |cmd − aTarget| 0.17, aTarget p10/p90 −0.24/+0.29, speeds[0] − vEgo p50 +0.08 mph. carState.cruiseState.speed is 0 under op long; carState.vCruise (km/h) is the set speed.

## 3. Fix (`038103ddd4`) — `opendbc/car/honda/carcontroller.py`
`bosch_brake_force_thresholds(fingerprint)` → Accord (−0.45, −0.20), else the existing (−0.12, −0.02); `update_honda_bosch_braking` takes the pair. Brake arms only when the request is at the floor (cannot over-deliver), releases when the request is back at a coast; the band between is gas 0 / no brake. Test `test_accord_brake_mode_arms_at_its_floor_and_releases_to_a_coast` in `honda/tests/test_honda.py`. Verified: local AST-level logic check; on the comma the edited module (scp to /tmp, loaded under its real name) imports and passes 14 assertions, device tree untouched. Replay on the logged forces (wf 1.0/1.5/2.0): cruise entries 21 → 7/7/6, duty 47 % → 13 %; whole route 23 → 8.
Rejected: a planner-side change (the planner is fine); scaling the brake-mode ACCEL (a floor cannot be scaled); keeping −0.12 and fixing the pitch (pitch only moves the arm point by 0.13; the floor is the defect).

## 4. Torque bar (`5a00f1f68a`)
`accord_angle_error_fraction` returns −(setpoint − wheel)/clip: openpilot angles are left-positive, the bar draws +x to the right, the torque branch already negates.

## 5. NEXT
1. Operator: `ssh comma; cd /data/openpilot && git pull origin accord-PTM` (→ 038103ddd4), reboot, drive with no-lead cruise at 35–65 mph including a downhill.
2. Read: `python analysis-2020accord/studies/long_control/long_cruise_pingpong_read.py <route> --dump` — the READOUT line (entries/min, coast duty, sag, duty) against the pre-registered targets in STATE; and the launch readout (`long_launch_jerk_read.py`) since bb was the first drive on the 2000 learner.
3. If the car does anything but coast in the new band (B risk): revert the two numbers.
4. Open: the −0.8° standstill pitch (mounting offset?) — a separate read; the 10-20 jerk-cost toggle config is superseded.
