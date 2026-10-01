"""EXP C: LIGHT-HAND OVERRIDE -- the regime the harness never ran.  The harness's ov_fade scripts the driver-torque word
at 2400 (fade at its 77/256 floor AND the cave's bleed on).  Here the driver holds the wheel delta deg off a constant
setpoint (straight road, theta_sp = 0, no fork O1 -- steeringPressed is not raised by a light hand) for H s with the
torque word |tq| at 0 / 700 / 1000 (bleed OFF: <= 1024; fade 1.00 / 0.98 / 0.90) or 1100 / 2400 (bleed ON; fade 0.88 /
0.30), then releases (30 ms).  Hand = the harness's stiff position source (2000 T/deg, 30 T/(deg/s)).
Reports: the lane torque the hand is fighting at the end of the hold (and the I's share), and after release the peak
|T|, the overshoot beyond the setpoint (deg, the lurch) and the time to return within 0.2 deg."""
import sys, json, time
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
SPEEDS = [float(s) for s in sys.argv[1].split(",")] if len(sys.argv) > 1 else [5.0, 8.0, 12.5, 19.0, 26.0]
DELTAS = (0.5, 1.0, 2.0)
TQS = (0, 700, 1000, 1100, 2400)
H = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
TG, TRAMP = 1.0, 0.3
TREL = TG + TRAMP + H
DUR = TREL + 4.0
def hand(delta):
    def h(t):
        if TG <= t < TREL:
            frac = min(1.0, (t - TG) / TRAMP)
            return (2000.0, 30.0, -frac * delta)
        return None
    return h
def tqf(a):
    return lambda t: (a * min(1.0, (t - TG) / TRAMP) if TG <= t < TREL else (a * (1 - (t - TREL) / 0.03) if TREL <= t < TREL + 0.03 else 0.0))
cols = []
for v in SPEEDS:
    for dl in DELTAS:
        for a in TQS:
            cols.append(dict(member="nominal", v=v, delta=dl, tqa=a, ref=lambda t: 0.0, hand=hand(dl), tq=tqf(a)))
t0 = time.time()
rec = F.run(cols, DUR, rec_I=True)
tt = np.arange(rec["th"].shape[0]) * 1e-3
i_end = int(TREL * 1000) - 5
w = tt >= TREL
res = []
print("[%.0f s] hold %.1f s" % (time.time() - t0, H))
print("  v   delta  |tq|  fade | T fought  I-share(T) | peak|T| after  overshoot deg  return-to-0.2deg s")
for j, c in enumerate(cols):
    T = rec["T"][:, j].astype(float); th = rec["th"][:, j].astype(float)
    I = rec["I"][:, j].astype(float); f = rec["f"][:, j]
    Ishare = I[i_end] * f[i_end] / 256.0 * 5346 / 32768.0      # I>>7 in S units -> T (approx, after fade, DC of lag)
    pk = np.abs(T[w]).max()
    ovs = th[w].max()                                         # beyond theta_sp = 0 on the far side (hand held at -delta)
    back = np.where(np.abs(th[w]) <= 0.2)[0]
    # time after the overshoot peak to settle within 0.2 deg for good
    bad = np.abs(th[w]) > 0.2
    last = (len(bad) - 1 - np.argmax(bad[::-1])) if bad.any() else 0
    res.append(dict(v=c["v"], delta=c["delta"], tq=c["tqa"], T_fought=float(T[i_end]), I_T=float(Ishare), peakT=float(pk), overshoot=float(ovs), settle=last * 1e-3, fade=int(f[i_end])))
    print("%5.1f %5.1f %5d  %4d | %7.0f  %7.0f   | %6.0f   %6.2f   %5.2f" % (c["v"], c["delta"], c["tqa"], f[i_end], T[i_end], Ishare, pk, ovs, last * 1e-3))
(OUT / ("expC_H%.1f.json" % H)).write_text(json.dumps(res))
