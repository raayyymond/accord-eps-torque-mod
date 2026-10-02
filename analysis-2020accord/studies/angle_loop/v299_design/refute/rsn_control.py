# -*- coding: utf-8 -*-
"""rsn_control.py -- control: MY lane (rsn_engine.Lane) vs S2's S2Lane (V298 and D1c columns) bit for bit on random
input sequences; my G walk vs score_time.glut on 0..12000.  ANALYSIS ONLY."""
import importlib.util, sys, time
from pathlib import Path
import numpy as np
T0 = time.perf_counter()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
_s = importlib.util.spec_from_file_location("s2_time_rsn", HERE.parent / "scores" / "S2-time-nonlinear" / "s2_time.py")
S2 = importlib.util.module_from_spec(_s); sys.modules["s2_time_rsn"] = S2; _s.loader.exec_module(S2)
g1 = E.G_walk(np.arange(12001)); g2 = S2.ST.glut(S2.GBP)
print("G walk mismatches", int(np.count_nonzero(g1 != g2)))
rng = np.random.default_rng(3)
speeds = [3.0, 5.0, 6.0, 8.0, 11.0, 13.0, 20.0, 27.0]
cids = ["V298", "D1c"]
cols = [(c, v) for c in cids for v in speeds for _ in range(8)]
B = len(cols)
vw = np.round(np.array([v for _, v in cols]) * 230.4).astype(np.int64)
mine = E.Lane(["V298" if c == "V298" else "V299" for c, _ in cols], vw)
ref = S2.S2Lane([S2.mk_cand(c) for c, _ in cols], vw)
th = rng.normal(0, 300, B).astype(np.int64); mism = 0; nfrz = np.zeros(2); N = 6000
for n in range(N):
    th = np.clip(th + rng.integers(-6, 7, B), -5000, 5000)
    held = th if n % 10 == 4 or n == 0 else held
    sp = np.clip(held + rng.integers(-300, 300, B), -4000, 4000) * 4
    abe = rng.integers(-3000, 3000, B)
    w = (rng.normal(0, 700, B)).astype(np.int64)
    ramp = 0x8000 if (n // 700) % 5 else rng.integers(0, 0x8000)
    a = mine.tick(held, abe, sp, w, ramp)
    b = ref.tick(held, held, held, abe, sp, w, ramp, 1, 1)
    mism += int(np.count_nonzero(a != b)) + int(np.count_nonzero(mine.log["I"] != ref.log["I"]))
    nfrz += [mine.log["frz"].mean(), mine.log["a3"].mean()]
print(f"ticks {N} x cols {B}: T/I mismatches {mism}; my freeze duty {nfrz[0]/N:.3f}, a3 duty {nfrz[1]/N:.3f}")
# the check can fail: V299 rule on my lane vs S2's V298 column
bad = E.Lane(["V299"] * B, vw); ref2 = S2.S2Lane([S2.mk_cand("V298") for _ in cols], vw); mm = 0
rng = np.random.default_rng(3); th = rng.normal(0, 300, B).astype(np.int64)
for n in range(1500):
    th = np.clip(th + rng.integers(-6, 7, B), -5000, 5000); held = th
    sp = np.clip(held + rng.integers(-300, 300, B), -4000, 4000) * 4; abe = rng.integers(-3000, 3000, B)
    w = (rng.normal(0, 700, B)).astype(np.int64)
    mm += int(np.count_nonzero(bad.tick(held, abe, sp, w, 0x8000) != ref2.tick(held, held, held, abe, sp, w, 0x8000, 1, 1)))
print("negative control (V299 mine vs V298 ref) mismatches:", mm)
print(f"wall {time.perf_counter()-T0:.1f} s")
