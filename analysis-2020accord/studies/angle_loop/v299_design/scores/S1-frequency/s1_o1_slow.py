# -*- coding: utf-8 -*-
"""s1_o1_slow.py -- the O1 loop with the integrator RUNNING (a hand of 600-1229 words under a 1229 freeze) vs frozen:
peak |S_tot| and its frequency per loop / O1 lead / Trt, worst over all 19 members x 7 speeds x frames nom/FA.83/FB1.155
x e 0/10.  Analysis only.  Pool(16), ~4 s (the first version looped serially and took 62 s -- replaced)."""
import sys
import time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402
M, W = S.M, S.W
LNS = ("V298", "G0-1400", "D3a-tab", "GB-S13")
VS = (2.0, 3.1, 5.0, 8.0, 11.75, 17.5, 26.9)


def job(a):
    mem, v = a
    pl = M.member(mem, v)
    res = []
    K = M.Kout(S.F)
    for ifr in (0, 1, 4):
        fn, kap, jb, ps = S.FRAMES[ifr]
        Pt, Pw = M.plant_channels(pl, S.F, jb)
        for e in (0, 10):
            for ln in LNS:
                li = S.LIDX[ln]
                for noI in (False, True):
                    Cth, Cw, Cref = S.ctl_pieces(S.DES[li], S.LOOPS[li], v, e, noI)
                    for tau in (0.06, 0.0):
                        for trt in S.TRT:
                            Wf = np.exp(-1j * W * trt) * (1 + tau * 1j * W)
                            s = np.abs(1 / (1 + -K * (Cth * Pt + kap * Cw * Pw + Cref * Wf * Pt)))
                            k = int(np.argmax(s))
                            res.append((ln, tau, trt, noI, s[k], S.F[k], "%s @%.1f" % (mem, v)))
    return res


if __name__ == "__main__":
    t0 = time.time()
    with Pool(16) as P:
        R = [x for y in P.map(job, [(m, v) for m in S.MEMBERS for v in VS]) for x in y]
    out = ["| loop | O1 lead s | Trt ms | PID: max |S_tot| (f Hz, member @v) | PD: max |S_tot| (f Hz, member @v) |",
           "|---|---|---|---|---|"]
    for ln in LNS:
        for tau in (0.06, 0.0):
            for trt in S.TRT:
                c = []
                for noI in (False, True):
                    b = max((r for r in R if r[0] == ln and r[1] == tau and r[2] == trt and r[3] == noI), key=lambda r: r[4])
                    c.append("%.2f (%.2f Hz, %s)" % (b[4], b[5], b[6]))
                out.append("| %s | %.2f | %.0f | %s | %s |" % (ln, tau, trt * 1000, c[0], c[1]))
    out.append("")
    out.append("wall %.1f s" % (time.time() - t0))
    (HERE / "out" / "s1_o1_slow.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
