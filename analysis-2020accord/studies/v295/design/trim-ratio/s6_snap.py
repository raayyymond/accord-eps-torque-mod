# -*- coding: utf-8 -*-
"""s6_snap.py -- trim-ratio lens: SNAP SOFTENING.  Open loop (no fork), zero sensor noise, a slow command ramp against
the Karnopp friction of each member: count the stick-slip jumps and measure each jump's peak wheel rate, peak wheel
acceleration and angle step, for V293 (trim off), V294 and the candidates.  Relative to V294 only (BELIEF for the car:
the stick-slip here is the fit's Fs/Fc, which the plant study flags as biased at speed; the harness says simulated
dwell COUNTS are noise-model dominated -- only per-jump shape is read here, at zero noise).
Writes s6_snap_out.txt.  Analysis only."""
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


def run(member, v, secs=24.0, top=700.0):
    NF = int(secs * 100)
    k = np.arange(NF)
    wire = top * np.sin(np.pi * k / NF) ** 2 * np.sign(np.sin(2 * np.pi * k / NF))   # slow out-and-back, both signs
    B = len(CELLS)
    lane = H.Lane(CELLS)
    plant = H.PlantBatch([member] * B, np.zeros(B), np.zeros(B), x_noise=0.0)
    plant.set_speed(np.full(B, v))
    om = np.zeros((B, NF * 10))
    for n in range(NF * 10):
        if n % 10 == 0:
            idx, sp, m = lane.demand(np.full(B, wire[n // 10]))
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, m)
        plant.step(T.astype(float))
        om[:, n] = plant.om
    out = []
    for j in range(B):
        w = om[j]
        moving = w != 0.0
        dd = np.diff(np.r_[0, moving.astype(int), 0])
        ev = [(a, b) for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)) if b - a >= 3]
        al = np.gradient(w) * 1000.0
        pk_w = [np.max(np.abs(w[a:b])) for a, b in ev]
        pk_a = [np.max(np.abs(al[a:b])) for a, b in ev]
        step = [abs(np.sum(w[a:b]) * 1e-3) for a, b in ev]
        dur = [(b - a) for a, b in ev]
        out.append(dict(n=len(ev), w=np.median(pk_w) if ev else np.nan, a=np.median(pk_a) if ev else np.nan,
                        step=np.median(step) if ev else np.nan, dur=np.median(dur) if ev else np.nan,
                        w90=np.percentile(pk_w, 90) if ev else np.nan))
    return out


def main():
    fam = H.family()
    print("per-jump medians (open loop, zero noise, slow +-700-count ramp): n jumps | peak rate deg/s | peak accel deg/s^2 |"
          " angle step deg | slip duration ms ; ratios vs V294")
    for nm in ("nominal", "F_hi", "light_b", "J_hi"):
        for v in (5.0, 8.0, 12.0, 17.0):
            r = run(fam[nm], v)
            b = r[1]
            print("  %-8s v %4.1f  V294: n %3d rate %6.2f accel %7.1f step %.3f dur %4.0f" % (
                nm, v, b["n"], b["w"], b["a"], b["step"], b["dur"]))
            for c, x in zip(CELLS, r):
                if c.name == "V294":
                    continue
                print("            %-8s n %3d  rate x%.2f  accel x%.2f  step x%.2f  dur x%.2f" % (
                    c.name, x["n"], x["w"] / b["w"], x["a"] / b["a"], x["step"] / b["step"], x["dur"] / b["dur"]))


if __name__ == "__main__":
    main()
