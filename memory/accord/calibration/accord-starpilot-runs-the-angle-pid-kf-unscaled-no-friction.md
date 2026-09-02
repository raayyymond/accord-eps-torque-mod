---
name: accord-starpilot-runs-the-angle-pid-kf-unscaled-no-friction
description: StarPilot (the operator's fork, openpilots/raayyymond-StarPilot) runs LatControlPID (the ANGLE PID) for the Accord, not the torque controller. The "," in the EPS part number sets EPS_MODIFIED and halves kpV/kiV (0.6->0.3, 0.18->0.09); the user multipliers HondaLateralPidKpScale/KiScale scale kpV/kiV ONLY. kf = 0.00006 is NEVER scaled by either. There is NO friction term in this controller -- any "openpilot friction relay" attribution is wrong. Effective today at 0.33: kp 0.099 (405 CAN counts/deg), ki 0.0297. For V279: Kp 0.33 = 16.7 dB gain margin at the 3.9 Hz phase crossover measured on the V276 log; Ki 0.33 (0.5 ok); never above Kp 1.0 (7 dB).
metadata:
  type: reference
---

# StarPilot runs the ANGLE PID; kf is unscaled; there is no friction term -- 2026-09-02 [EVIDENCE]

Source: `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot` @ e631b24.
- `opendbc/car/honda/interface.py:85` kf = 0.00006; `:98-104` `b"," in fw.fwVersion` -> EPS_MODIFIED;
  `:139-142` Accord kpV/kiV [[0.3],[0.09]] if modified else [[0.6],[0.18]].
- `selfdrive/controls/controlsd.py:102-103` picks `LatControlPID` when `lateralTuning.which() == 'pid'`.
- `starpilot/common/starpilot_variables.py:690-691` HondaLateralPidKpScale/KiScale (0.1-4.0), PID path only;
  `latcontrol_pid.py:116-117` scales kpV/kiV only; `:142` ff = kf * angle_des * v^2, UNSCALED.
- `common/pid.py`: P + I + F with anti-windup. **No friction term** (that belongs to LatControlTorque, unused).

**The V279 derivation (from the operator's V276 log r2e, 3-5 Hz band, coh 0.97):** |G(3.9 Hz)| = angle/torque =
0.00056 deg per torque count at -104 deg (hands-ON windows -- conservative); openpilot's flown cmd/angle 332-354
counts/deg (predicts 0.33 from 0.6*0.5*0.33*4096 = 406); cmd-vs-angle phase -79 deg -> ~56 ms openpilot delay.
=> plant -104 + delay -79 = **-183 deg at 3.9 Hz: the phase crossover.** |L| = 1229*mult * 0.645 * 0.00056 =
**0.444 x mult**. Kp 0.33 -> 0.147 (16.7 dB); 0.5 -> 13.1 dB; 1.0 -> 7.0 dB; 2.25 -> 0 dB.
BELIEF: the low-frequency side (column stiffness k ~ 85-170 torque counts/deg, not identifiable from 31 s of a
railed limit cycle). Watch for a NEW 1-2.5 Hz wallow -> Kp 0.2.

**How to apply:** the multipliers are a loop-SHAPE decision, not a torque ratio. Re-derive from the cmd->angle
response whenever the EPS plant changes class. See [[accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440]].
