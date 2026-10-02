"""ADV interlocks-gates V298 / F8: re-run the operating-point GATE 2 (the test that REFUTED C3) at the IMAGE's
Ki=40 + GB-P table, and partition the PM<bar failures by ms_free-involvement, for the PRIMARY C3B-P only.
Resolves whether the op-point failures are CONFINED to the declared report-only ms_free family (M-F1) or whether a
CREDIBLE non-ms_free member fails (= GATE 2 FAIL). Reuses rb_gate2's exact machinery + the independent refuter model."""
import math, sys
from multiprocessing import Pool
from pathlib import Path
AL = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/angle_loop")
sys.path.insert(0, str(AL / "refute_stability" / "c3r1"))
sys.path.insert(0, str(AL / "c3" / "rev2B"))
import numpy as np
import c3r1_model as M
import c3r1_sweep as S
import rb_table as T
F = S.F
KI = 40.0
DES = {"C3B-P": M.Design("C3B-P", "fresh", kd=48, ki=KI, rows=tuple(T.GB_P))}
SR, LWB = 16.0, 2.83
SINGLE, COMBINED = S.SINGLE, S.COMBINED
GF = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
MS = lambda m: "ms_free" in m
def theta_op(v, a): return SR * LWB * a / (v * v) * 180 / math.pi
def sat(v): return 19.3 + 546.0 * math.exp(-v / 3.01)
def bar(mem, e): return (45.0 if e <= 0 else 30.0) if mem in SINGLE else 30.0
def work(args):
    mem, v = args; res = []
    for a in (1.0, 1.5, 2.0, 2.5):
        s2 = 1 - math.tanh(theta_op(v, a) / sat(v)) ** 2
        pl = M.member(mem, v); pl.k *= s2
        for fn, kap, jb in GF:
            Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
            for e in (-1, 0, 10):
                Cth, Cw, _ = M.controller(DES["C3B-P"], v, F, e, kap)
                L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                PM, FC, GM = M.pm_gm(L, F)
                rho = M.Periodic(DES["C3B-P"], pl, v, e=e, kappa=kap, jb=jb).rho_ring()[0] if PM < 32 else 0.0
                res.append((mem, v, a, fn, e, PM, GM, rho, bar(mem, e)))
    return res
if __name__ == "__main__":
    SP = sorted(set([round(x, 2) for x in np.arange(8.0, 30.01, 0.5)] + [8.0, 11.9, 17.0, 26.9]))
    jobs = [(m, v) for m in SINGLE + COMBINED for v in SP]
    with Pool(12) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=2) for r in rr]
    for setname, test in (("NON-ms_free credible set", lambda m: not MS(m)),
                          ("ms_free family (declared M-F1)", MS)):
        X = [r for r in R if test(r[0])]
        fails = [r for r in X if r[5] < r[8]]
        unst = [r for r in X if r[7] >= 1.0]
        w = min(X, key=lambda r: r[5] - r[8])
        print(f"{setname}:")
        print(f"   points {len(X)}  PM<bar {len(fails)}  exact rho>=1 {len(unst)}")
        print(f"   worst PM {w[5]:.1f} (bar {w[8]:.0f}) at {w[0]}@{w[1]} a{w[2]} {w[3]} e{w[4]}  margin {w[5]-w[8]:+.1f}")
        if fails:
            mems = sorted(set(r[0] for r in fails))
            print(f"   FAILING MEMBERS: {mems}")
            for m in mems:
                fm = [r for r in fails if r[0] == m]
                ww = min(fm, key=lambda r: r[5] - r[8])
                print(f"      {m}: {len(fm)} fails, worst PM {ww[5]:.1f} bar {ww[8]:.0f} a{ww[2]} v{ww[1]} e{ww[4]}")
