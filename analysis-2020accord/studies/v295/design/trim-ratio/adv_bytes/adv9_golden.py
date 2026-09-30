# adv9_golden.py -- adversary mirror vs the GOLDEN MODEL (lkas_fb_lag + lkas_rate_pid_tick), b 964, 8000 random ticks
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness")); sys.path.insert(0, HERE)
import v295_harness as H
import adv_mirror as AM
import eps_lkas_chain_model as M
c = H.Cells.v294().replace(fb_b=964)
cal = H.golden_cal(c)
st = M.EpsState()
L = AM.Lane(dict(AM.load_cells(), b=964))
rng = random.Random(11); bad = 0; x = 0
for k in range(8000):
    if k % 10 == 0:
        idx = rng.randrange(0, 241); sp = rng.choice((-1, 1)) * L.map[idx]; F = rng.choice((254, 178, 76))
    x = max(-12000, min(12000, x + rng.randint(-600, 600)))
    fb = M.lkas_fb_lag(x, st, cal, lane_live=(k > 0))
    g = M.lkas_rate_pid_tick(sp, fb, idx, st, cal, pol=1, taper=F)
    t = L.tick(x, sp, idx, F)
    bad += (g["T"] != t)
print("golden model vs adversary mirror, b 964: 8000 ticks, %d mismatches (fb_lag_b in cal = %d)" % (bad, cal.fb_lag_b))
