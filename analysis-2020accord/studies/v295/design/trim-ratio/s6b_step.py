# -*- coding: utf-8 -*-
"""s6b_step.py -- trim-ratio lens: the BREAKAWAY STEP.  (s6_snap.py's slow ramp produced continuous slides, not
stick-slip -- it is NOT informative and is not cited.)  Here: wheel at rest and stuck, command stepped (through the real
lane: map, FF, output lag) to a level just past breakaway (FF = Fs + ~1 idx) and to a medium level (FF ~ 150 T);
open loop (no fork), zero sensor noise.  Per cell set: peak wheel rate, peak wheel acceleration, angle overshoot past
the settled angle, and the settled angle (must be equal: the trim has no DC).  Relative to V294 only; BELIEF for the car
(the plant is the identified family + the light_b prior; nothing above ~8 Hz is identified).
Writes s6b_step_out.txt.  Analysis only."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
CELLS = [BASE.replace(fb_clamp=0, name="V293"), BASE.replace(name="V294"), BASE.replace(name="b1134", fb_b=1134),
         BASE.replace(name="g3sh1", fb_b=850, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512),
         BASE.replace(name="a1017g2", fb_a=1017, fb_b=567, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512)]
FF_PER_WIRE = 0.6409


def step(member, v, wire, secs=4.0):
    B = len(CELLS)
    lane = H.Lane(CELLS)
    plant = H.PlantBatch([member] * B, np.zeros(B), np.zeros(B), x_noise=0.0)
    plant.set_speed(np.full(B, v))
    N = int(secs * 1000)
    th = np.zeros((B, N))
    om = np.zeros((B, N))
    idx, sp, m = lane.demand(np.full(B, 0.0))
    for n in range(N):
        if n == 200:
            idx, sp, m = lane.demand(np.full(B, float(wire)))
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, m)
        plant.step(T.astype(float))
        th[:, n] = plant.th
        om[:, n] = plant.om
    out = []
    for j in range(B):
        al = np.gradient(om[j]) * 1000.0
        # 2 ms moving average on alpha (the Euler step makes single-tick spikes at stick transitions)
        al = np.convolve(al, np.ones(5) / 5, "same")
        thf = th[j, -1]
        ov = (np.max(np.abs(th[j])) - abs(thf)) / max(abs(thf), 1e-9)
        out.append(dict(w=np.max(np.abs(om[j])), a=np.max(np.abs(al[200:])), ov=ov, thf=thf))
    return out


def main():
    fam = H.family()
    print("BREAKAWAY STEP (open loop, zero noise): per cell set peak |rate| deg/s, peak |accel| deg/s^2 (2 ms smoothed),"
          " overshoot past the settled angle (fraction), settled angle deg")
    for nm in ("nominal", "F_hi", "b_lo", "J_hi", "light_b"):
        for v in (5.0, 8.0, 12.0, 17.0, 26.9):
            p = fam[nm].at(v)
            for label, W in (("just-past-Fs", (p.Fs + 6.0) / FF_PER_WIRE), ("medium 150T", 150.0 / FF_PER_WIRE)):
                r = step(fam[nm], v, W)
                b = r[1]
                s = "  %-8s v %4.1f %-13s W %4.0f  V294: rate %6.2f accel %7.1f ov %5.2f thf %6.2f |" % (
                    nm, v, label, W, b["w"], b["a"], b["ov"], b["thf"])
                for c, x in zip(CELLS, r):
                    if c.name == "V294":
                        continue
                    s += " %s rate x%.2f acc x%.2f ov %.2f thf %.2f |" % (c.name, x["w"] / max(b["w"], 1e-9),
                                                                       x["a"] / max(b["a"], 1e-9), x["ov"], x["thf"])
                print(s)


if __name__ == "__main__":
    main()
