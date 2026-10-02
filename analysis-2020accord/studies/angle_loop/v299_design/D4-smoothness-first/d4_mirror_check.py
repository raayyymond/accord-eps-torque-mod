# -*- coding: utf-8 -*-
"""d4_mirror_check.py -- CONTROL: the simulated lane (d4_sim.D4Lane, config 'b8:lp5H512') takes the SAME freeze decision
and writes the SAME state word as the integer mirror d4_cave.d4b_ref (which the D4b cave bytes reproduce, H1 0/20000),
on random states and inputs (valid rate only: the sim does not model the op-skip).  < 15 s."""
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4_cave as DC  # noqa: E402
import d4_sim as DS  # noqa: E402

rng = np.random.default_rng(23)
B = 4000
cand = DS.ST.CBYID["b8:lp5H512"]
vw = rng.choice([0, 714, 1382, 1383, 2880, 2881, 4032, 6198, 9000], B)
lane = DS.D4Lane([cand] * B, vw)
a6 = rng.integers(-4000, 4000, B)
sp = rng.integers(-16384, 16385, B)
abe = np.where(rng.random(B) < 0.3, rng.integers(-15, 16, B), rng.integers(-12000, 12000, B))
tq = rng.choice(np.r_[[0, 300, 301, -300, -301, 512, 513, -513], rng.integers(-3000, 3000, 50)], B)
h0 = rng.choice(np.r_[[0, 300, -300, 512, -513], rng.integers(-3000, 3000, 50)], B)
first = rng.random(B) < 0.2
I8 = (rng.integers(-(8192 << 10), 8192 << 10, B) // 8) * 8
ramp = rng.choice([0x8000, 0x7FFF], B)
lane.lane_ok[:] = 0
lane.h[:] = h0
lane.Eprev[:] = np.where(first, DS.SENT32, 5)
lane.I8[:] = I8
lane.tick(a6, a6, 0, abe, sp, tq, ramp, 1, 1)
frz_sim, h_sim = lane.log["frz"], lane.h
bad_f = bad_h = 0
for j in range(B):
    c = {"6a5e": int(vw[j]), "4f60": int(tq[j]), "6abe": int(abe[j]), "6a00": int(a6[j]), "6dd0": int(I8[j]),
         "6a32": int(h0[j]), "6cf8": 0x7FFFFFFF if first[j] else 5}
    ex, r16, r6, r26, h = DC.d4b_ref(int(sp[j]), int(8 * a6[j]), c, int(ramp[j]), 1)
    bad_f += (ex == DC.FRZ_RET) != bool(frz_sim[j])
    bad_h += h != int(h_sim[j])
print("mirror vs simulated lane (b8): freeze decision mismatches %d / %d ; state word mismatches %d / %d ; wall %.1f s"
      % (bad_f, B, bad_h, B, time.time() - T0))
