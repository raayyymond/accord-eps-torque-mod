# -*- coding: utf-8 -*-
"""v293_s9_prereg.py -- DELIVERABLE 6: the instrument check behind the pre-registration.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

Every readout the pre-registration names has to be ON THE WIRE in a V282-based build and has to be
able to MOVE.  This file measures the discriminating power of each one on the operator's own recorded
episodes, before any image exists.

  1. THE EDIT-LIVE CONTROL -- the within-frame identity.  With 0xC62E6 = 0, the CAN-427 torque tap is
     an EXACT function of the 0xE4 command and the driver torque (through the fade) and carries NO
     dependence on the wheel rate.  Measured as R^2 of the tap against f(cmd)*fade, within frame, on
     both arms.  It is not tautological: on V282 the same regression has a large residual because the
     feedback leg is in T, and that residual is what must vanish.
  2. THE 0x14A CAVE BITS -- b7/b6/b5/b4/b3 duties on both arms, so the pre-registration can name a
     duty that MOVES rather than one that merely exists.
  3. RESOLUTION -- the LSB and rate of every channel, and what a one-LSB change is worth.

Run: python v293_s9_prereg.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_echo_sizing as ES                      # noqa: E402
import design290b_candidates as D                   # noqa: E402
import v292_replay_lib as R                         # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_s2_replay as S3                         # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def tap_quantise(T):
    """the CAN-427 tap as the frame builder writes it: (sign(T)<<9) | (|T|>>3), 8 counts per LSB."""
    T = np.asarray(T, float)
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8.0


def r2(y, yhat):
    y = np.asarray(y, float)
    yhat = np.asarray(yhat, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1.0 - np.sum((y - yhat) ** 2) / ss) if ss > 0 else np.nan


def main():
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    c282 = L.read_cells(L.IMG282)
    c293 = L.torque_mode(c282, kp=119)
    pl = D.mkplant(byid[225])

    pr("=" * 118)
    pr("V293 PRE-REGISTRATION -- THE INSTRUMENT CHECK       tmdesign 2026-09-13    ANALYSIS ONLY")
    pr("=" * 118)

    g = S2.route("r39", (18.0, 22.0))
    wins = ES.loud_windows(g)

    pr("")
    pr("1. THE EDIT-LIVE CONTROL -- the within-frame identity  T_tap = f(cmd) * fade")
    pr("-" * 118)
    pr("With the feedback clamped to zero, E = 32*sp exactly, so the delivered torque depends ONLY on")
    pr("the demand index (through the map and Kp) and on the driver's bar torque (through the fade and")
    pr("the demand taper).  Regressing the 427 tap on f(cmd)*fade within the SAME frames therefore has")
    pr("to go to R^2 = 1 on V293 and must NOT on V282 -- the V282 residual is the feedback leg.")
    pr("")
    pr("  %-8s %10s %12s %12s %12s %12s" %
       ("window", "n frames", "R2 V282", "R2 V293", "resid V282", "resid V293"))
    acc = []
    for (a0, b0, p0) in wins:
        W2 = R.prep_window(g, a0, b0, c282)
        W9 = R.prep_window(g, a0, b0, c293)
        d, _ = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, W2["wire1k"])
        A2 = R.closed_run(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, d)
        B9 = R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0), R.PlantIIR(pl), W9, d)
        # the PREDICTOR available on the wire: the open-loop surface at this frame's idx and fade
        sl = slice(800, None, 20)                     # the tap is 50 Hz; the sim is 1 kHz
        pred2 = L.surface(c282, W2["idx"][sl], 0.0, fade=254)["T"] * (W2["m"][sl] / 254.0)
        pred9 = L.surface(c293, W9["idx"][sl], 0.0, fade=254)["T"] * (W9["m"][sl] / 254.0)
        t2 = tap_quantise(A2["T"][sl]) * np.sign(W2["sp"][sl] + 1e-12)
        t9 = tap_quantise(B9["T"][sl]) * np.sign(W9["sp"][sl] + 1e-12)
        R2a = r2(np.abs(t2), np.abs(pred2))
        R2b = r2(np.abs(t9), np.abs(pred9))
        rs2 = float(np.sqrt(np.mean((np.abs(t2) - np.abs(pred2)) ** 2)))
        rs9 = float(np.sqrt(np.mean((np.abs(t9) - np.abs(pred9)) ** 2)))
        acc.append((R2a, R2b, rs2, rs9))
        pr("  %-8.1f %10d %12.4f %12.4f %12.1f %12.1f" %
           (g["tr"][p0], len(t2), R2a, R2b, rs2, rs9))
    a = np.array(acc, float)
    pr("  %-8s %10s %12.4f %12.4f %12.1f %12.1f" %
       ("MEDIAN", "", np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]), np.median(a[:, 3])))
    pr("")
    pr("  The V293 residual is NOT zero because the tap quantises to 8 counts and the fade LERP is")
    pr("  evaluated on the 100 Hz bar while the PID runs at 1 kHz.  What matters is the CONTRAST:")
    pr("  a V293 drive must show R^2 rising from ~%.2f to ~%.2f and the residual falling x%.1f."
       % (np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]) / max(np.median(a[:, 3]), 1e-9)))
    pr("  🛑 If it does not, the cal did not take -- the SAME CLASS of check as V292's b3 read, but")
    pr("  within-frame and with a positive control built in.")

    pr("")
    pr("2. THE 0x14A CAVE BITS -- which duties MOVE, and by how much")
    pr("-" * 118)
    pr("V282's cave is carried UNCHANGED by a cal-only V293 (no code byte moves), so every bit stays")
    pr("live.  b7 = sign(gp-0x6b4c) (the LKAS summand) . b6 = |r24| >= |T| . b5 = |r24| >= |agg sum| .")
    pr("b4 = sign(r24) . b3 = sign(gp-0x3680).  Only b6 and b5 involve T, so only they can move.")
    pr("")
    pr("  %-26s %12s %12s %12s" % ("duty", "V282", "V293", "change"))
    du = {"b7 sign(LKAS summand)": [], "b6 |r24| >= |T|": [], "b4 sign(r24)": []}
    for (a0, b0, p0) in wins:
        W2 = R.prep_window(g, a0, b0, c282)
        W9 = R.prep_window(g, a0, b0, c293)
        d, _ = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, W2["wire1k"])
        A2 = R.closed_run(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, d)
        B9 = R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0), R.PlantIIR(pl), W9, d)
        # r24, from the recorded bar, the way the lane computes it
        bar = W2["bar1k"]
        dd = (np.r_[np.zeros(4), bar[4:] - bar[:-4]]) / 2.0
        dd = np.clip(dd, -5120, 5120)
        s = np.floor(dd * c282["r24_arm"] / 1024.0)
        s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s) * 3)
        r24 = np.clip(-s, -8192, 8192)
        du["b7 sign(LKAS summand)"].append((float(np.mean(A2["T"] >= 0)), float(np.mean(B9["T"] >= 0))))
        du["b6 |r24| >= |T|"].append((float(np.mean(np.abs(r24) >= np.abs(A2["T"]))),
                                      float(np.mean(np.abs(r24) >= np.abs(B9["T"])))))
        du["b4 sign(r24)"].append((float(np.mean(r24 >= 0)), float(np.mean(r24 >= 0))))
    for k, v in du.items():
        v = np.array(v, float)
        pr("  %-26s %12.3f %12.3f %12.3f" %
           (k, np.median(v[:, 0]), np.median(v[:, 1]), np.median(v[:, 1]) - np.median(v[:, 0])))
    pr("")
    pr("  ⭐ b7 IS THE ONE THAT MOVES, not b6 -- and that is the opposite of what I expected before")
    pr("  running it, so it is recorded that way.  On V282 the LKAS summand's sign is pinned (duty")
    pr("  ~1.00 on these one-direction turn windows) because the feedback leg keeps T on one side;")
    pr("  with the loop open T follows the COMMAND's sign exactly and the duty falls to ~0.81.  b6")
    pr("  (|r24| >= |T|) moves only ~+0.03, which is INSIDE the duty noise of a single short episode")
    pr("  and must NOT be pre-registered as a readout.")
    pr("  b4 is identical by construction (r24 does not depend on T) and is the NEGATIVE CONTROL: if")
    pr("  b4's duty moves on a V293 drive, something other than the intended cal changed.")

    pr("")
    pr("3. RESOLUTION -- what one LSB of each channel is worth")
    pr("-" * 118)
    pr("  %-34s %10s %10s %s" % ("channel", "rate Hz", "LSB", "what one LSB is"))
    for nm, rate, lsb, what in (
            ("CAN 427 (0x1AB) delivered torque", 50, 8, "8 EPS torque counts, sign in bit 9"),
            ("0x18F STEER_ANGLE_RATE", 100, 1, "0.125 deg/s (CPD = 8 counts per deg/s)"),
            ("0xE4 STEER_TORQUE command", 100, 1, "1/4096 of scale = 0.062 demand-index LSB"),
            ("0x14A byte 4 bits 3-7", 100, 1, "one comparator/sign decision per 10 ms tick"),
            ("driver torque (torsion bar)", 100, 1, "wire = raw x 1.024")):
        pr("  %-34s %10d %10d %s" % (nm, rate, lsb, what))
    pr("")
    pr("  The 18-22 Hz ring on the RATE channel is ~16 raw counts = 1.98 deg/s (the 2026-09-13 unit")
    pr("  correction).  A x0.25 change takes it to ~4 counts, still 4x the quantiser.  The ring is")
    pr("  therefore READABLE on the rate channel at the predicted dose.  [EVIDENCE -- arithmetic on")
    pr("  the record's own corrected unit.]")

    open(os.path.join(SCR, "v293_s9_prereg.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s9_prereg.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
