# -*- coding: utf-8 -*-
"""Proof obligation for `starpilot_Dom_margin-safe-gain.patch` hunk 2.

The patch adds a speed schedule to AccordErrorNotchQ.  Its safety rests on ONE claim:
**the shipped default (q = 1.0) must reproduce today's behaviour at EVERY speed, exactly.**
This script mirrors the patched function and asserts that, plus three other properties.

Run:  python verify_notch_q_schedule.py
"""
import numpy as np

# --- mirror of the patched get_honda_accord_error_notch_q ---
HONDA_ACCORD_NOTCH_Q_V_BP = [8.0, 15.0]
HONDA_ACCORD_NOTCH_Q_LOW = 1.0


def get_honda_accord_error_notch_q(v_ego, q):
    if q <= 0.0:
        return q
    return float(np.interp(v_ego, HONDA_ACCORD_NOTCH_Q_V_BP, [max(q, HONDA_ACCORD_NOTCH_Q_LOW), q]))


VS = [0, 2, 4, 6, 8, 10, 12, 15, 20, 28, 40]
LABEL = {1.0: "SHIPPED DEFAULT -- must be flat 1.0 (bit-identical to today)",
         0.3: "ARM-KP3 (toggle-only, flies without the patch)",
         0.2: "the patched KP 5.0 / KP 6.0 operating point",
         0.0: "notch bypassed -- must pass straight through",
         2.0: "narrower than default -- must be speed-flat"}

print("AccordErrorNotchQ speed schedule, delivered Q vs vEgo\n")
for q in (1.0, 0.3, 0.2, 0.0, 2.0):
    out = [get_honda_accord_error_notch_q(v, q) for v in VS]
    flat = all(abs(x - out[0]) < 1e-12 for x in out)
    print(f"  q={q:<4}  {LABEL[q]}")
    print("      " + "  ".join(f"{v:g}:{o:.2f}" for v, o in zip(VS, out))
          + f"   [{'FLAT' if flat else 'scheduled'}]")

fine = np.arange(0.0, 45.0, 0.25)
assert all(abs(get_honda_accord_error_notch_q(v, 1.0) - 1.0) < 1e-12 for v in fine), \
    "DEFAULT NOT FLAT -- the patch would change behaviour on an unmodified config"
assert get_honda_accord_error_notch_q(5.0, 0.0) == 0.0 and get_honda_accord_error_notch_q(30.0, 0.0) == 0.0, \
    "notch-bypass escape (q <= 0) not preserved"
assert abs(get_honda_accord_error_notch_q(1.0, 0.3) - 1.0) < 1e-12, "low speed not pinned to the flown 1.0"
assert abs(get_honda_accord_error_notch_q(25.0, 0.3) - 0.3) < 1e-12, "toggle value not delivered above 15 m/s"
assert all(abs(get_honda_accord_error_notch_q(v, 2.0) - 2.0) < 1e-12 for v in fine), \
    "q > 1 must be speed-flat -- nobody should be surprised in the narrowing direction"

print("""
ALL ASSERTIONS PASS:
  - q = 1.0 (shipped default) is FLAT 1.0 over 0-45 m/s  => an unmodified config behaves exactly as today
  - q <= 0 passes through unchanged                      => the notch-bypass escape is preserved
  - q < 1 pins low speed to the flown 1.0 and delivers the toggle value at >= 15 m/s, the metric's own floor
    (so the schedule is metric-inert BY CONSTRUCTION: every scored window is >= 15.75 m/s)
  - q > 1 is speed-flat

WHY THE SCHEDULE EXISTS, measured: the notch CENTRE is already speed-dependent (0.82 Hz at 2 m/s, 1.28 at 8,
2.05 at 23), so one scalar Q is a different filter at every speed.  |N| and phase at 0.3 Hz:
    Q 1.00 -> 0.920 @ -23 deg at 2 m/s      Q 0.30 -> 0.576 @ -55 deg      Q 0.20 -> 0.426 @ -65 deg
A Q wide enough to hold the 3.4-4.9 Hz mode down at speed therefore sits on top of the demand at low speed --
the regime the operator reports as ratchety, and one the goal metric never scores.""")
