---
name: accord-v293-rev2-flew-route71-2hz-limit-cycle-hold-map-wrong-twice
description: "V293 + fork REV 2 FLEW 2026-09-13 evening (route 75604b0a432fdc89_00000071--f2c9d073a3, 18 segs, fork 66cf4454a, rev-2 config attributed: Kp 0.8500 / LAF 14.0000 at 100 Hz). Operator: 'does not feel like StarPilot has accurately modeled my EPS + car dynamics', loose on straights/slight bends, jerks to correct on hard low-speed curves, worse with oscillation/resonance on hard high-speed curves. WIRE: a 2.34 Hz +-6 deg LIMIT CYCLE on every sustained curve above 20 m/s (rate +22.5 dB, cmd +-300 counts, the SteerFriction relay flipping every half cycle) -- the lightly damped STEERING MODE (J ~8e-5 torque/(deg/s^2), zeta 0.2-0.35, f_n = sqrt(k(v)/J)/2pi = 1.0 Hz at 4.5 m/s to 2.1 Hz above 20) pumped by the ~60 ms-delayed P + the relay (linear PM -5..-28 deg at 19-28 m/s with the relay); 20 rate bursts/min of 84-442 deg/s in low-speed hard curves (stiction -> command ramp -> snap, honda limiter capped 6 % of frames at 0-5 m/s); tracking gain 0.83/0.93/0.99/1.12; scorer ratchet REVERT trigger fired (dwells 9.1 vs r70 4.6 /min at 10-20). The HOLD TORQUE is a SATURATING spring 0.020 + k(v)*sat(v)*tanh(th/sat), sat = 19.3 + 546 exp(-v/3.01) deg: the rev-2 linear tables are x3-5 too SMALL below 10 m/s at 5-35 deg (-> loose on slight bends, under-turning) and x0.6-0.7 too LARGE above 17-25 m/s. Vehicle model NOT a cause (gyro check 0.99-1.01)."
metadata:
  type: project
---

# Rev 2 flew on route 71 (2026-09-13 evening): the relay limit-cycles the 2 Hz steering mode; the hold map is wrong twice [EVIDENCE — `rlog-tools/studies/grind/_scratch/v293r2_read_r71_v293r2.txt`, `v293_flight_read_r71_v293r2.txt`, `r70r71_hold_joint_fit.txt`]

**The three symptoms on the wire.** (1) *Loose on straights/slight bends* = the feedforward supplying 20–35 % of
the measured hold at 5–35° below 10 m/s (linear tables ×0.2–0.35 of the need), the integrator (Ki 0.3/14, ~3 s)
doing the rest late; loop P-stiffness on straights was HIGHER than route 70 (0.011/0.0164 torque/deg), so it is
not stiffness. (2) *Jerks on low-speed hard curves* = stiction: the wheel sits still while the lsf-inflated P
(Kp_eff 5.4 at 5 m/s) ramps the command 1082 → 2748 counts in 0.4 s, breakaway at 315 deg/s, 80° overshoot,
reversal; the relay is bang-bang there (linear zone 0.044 m/s²). (3) *Oscillation on high-speed hard curves* =
the 2.34 Hz limit cycle (t = 630–638 s at 21.8 m/s: angle 16↔29°, cmd −600↔−1200, error −0.5↔+1.3 m/s²).

**The plant, second pass.** Band-passed fit u − relay = aθ + bθ' + Jθ'' (0.1–5 Hz): J 7.2e-5…9.1e-5 in every
band, ζ 0.18–0.38, ω_n 1.17/1.76/2.01 Hz at 8–15/15–22/>22; the limit-cycle point (angle/command 68–104
deg/torque at −150…−165°, coh 0.75–0.85) gives the same plant. Loop delay from timestamps: 0x14A→carState 3 ms,
controlsState→0xE4 13 ms, 0xE4→delivered torque 30–45 ms. The low-frequency joint fit (0.5 Hz LPF) still reads
a 0.0022/0.0050/0.0120 at 6/11/18 m/s and b 0.0015–0.0037 — a different, slower quantity than the mode's damping.

**Why:** the fork's rev-2 model (linear spring tables + an error-keyed friction relay) put loop gain exactly at
the frequency where the plant's phase + the loop delay reach −180°, and under-held everywhere the driver feels
"loose". **How to apply:** never key friction compensation on the error on this plant; keep the P/I loop gain
away from √(k(v)/J)/2π; use the measured hold map for the feedforward; see
[[accord-fork-rev3-hold-map-hysteresis-rate-loop-notch-shipped]] for what shipped and
[[accord-steering-mode-2hz-inertia-and-loop-delay-budget]] for the numbers a design needs. Related:
[[accord-v293-flew-route70-plant-is-a-spring-ratchet-measured]].
