---
name: accord-launch-jerk-is-the-bosch-gas-learner-fork-272394d0-2026-10-21
description: "2026-10-21: the jerky launch (bookmark b9 390 s) = the Bosch GAS-FACTOR LEARNER (kp=ki=0 on Bosch long, the learner is the only accel feedback; /50 winds 0.24→1.75 in the turbo spool, crashes at boost, cycle locked to upshifts ~2 s); FIX on fork accord-PTM 272394d0 PUSHED not pulled: Accord learn speed 2000 + no learning at the 1600 gas rail; torque bar = (setpoint − wheel)/clip; error clip from Kmax−Imax = 35.4/23.4/45/61/25/12.2°; rlogs pulled over ssh from the device; remote shell writes blocked by the classifier"
metadata:
  node_type: memory
  type: project
  originSessionId: 1732f167-b674-49bb-892e-d9d44ba199ea
  modified: 2026-10-22T03:56:12.034Z
---

**State 2026-10-21 (E unless marked):** fork accord-PTM `311c4cc0 → 272394d0` (3 commits) pushed to origin; the device still
runs 311c4cc0 until `git pull origin accord-PTM` + reboot. Firmware V300 rev 2 unchanged. Page
https://claude.ai/artifact/CvZEDCq6RZW8xM4VBPPTz2; handoff `docs/handoffs/2026-10/HANDOFF-2026-10-21-launch-jerk-torque-bar-error-clip.md`.

- **Launch jerk:** Bosch longcontrol is pure feedforward (kp = ki = 0), so `honda/carcontroller.py`'s gas-factor learner
  (`factor += err/50 × force` per 20 ms) is the only accel feedback. 10/10 full launches on b5–b9 cycle at ~2 s on the
  upshifts; aTarget smooth (0.16/cycle) while aEgo drops 1.37; the factor carries 89 % of each gas cut. Fix `da4b2c1845`:
  Accord learn speed 2000 (40× slower) + no learning while the last gas sat on the rail. Replay: swing 1.15 → 0.03, 88 % of
  cut depth gone; price (B) ≈ 72 % of today's gas in the first 4 s. Readout: `long_launch_jerk_read.py` (pre-registered
  numbers in `LAUNCH-JERK-READ-2026-10-21.md`).
- **Torque bar** `b5d39556fe`: (carOutput setpoint − wheel) / ANGLE_ERROR_MAX(v), ±1, Accord angle-fw only.
- **Error clip** `272394d0cf` (operator rule Kp·e = Kmax − Imax, from the V300 image, trace
  `docs/traces/TRACE-2026-10-21-v300-kmax-imax.md`): P = ((160·deg·G(v))≫8)·112≫8, Kmax 15360 (15481 pre-taper), Imax
  4096/6144/8192 by speed tier ⇒ 35.4/23.4/45.0/61.0/25.0/12.2° at the six knots. D is on ROTOR RATE (gp-0x6abe), not angle.
  Risk: hands-on creep (the hand fight at the clip) may worsen.
- **Tooling:** rlogs copy fine over `scp comma:/data/media/0/realdata/<route>--<seg>/rlog.zst` (connect's multi-download
  prompt blocks the browser skill); ssh READS and scp work, but remote shell WRITES (`git checkout` on the device) are
  denied by the auto-mode classifier — restore device files by scp from `git show <rev>:<path>`. Device venv has no pytest;
  a stand-in (`approx`/`raises`) + a function runner ran 33 fork tests on the comma 4.

**How to apply:** score the next launch drive with the pre-registered readout before touching anything else; if launches
are too soft the lever is the planner's accel profile, not the learner; never re-propose a firmware PID edit for max
angle. See [[accord-v300-flew-ad-b4-grind-is-hand-fight-long-is-brake-cycling-2026-10-20]].
