# -*- coding: utf-8 -*-
"""d5_score.py -- lens "dynamics": the shared harness's full score() for the lens's two finalists (so the four designs
are comparable), plus the clamp/overflow checks of design rule 7 on the drive itself.

  finalists: A1017 (fb pole 0xC63E8 1011 -> 1017, b held 567)   and   L8 (output lag 0xC63EC/EE 992/507 -> 974/792)
  (1) H.score(cand) -- candidate + V294 in one batch, default plants + stress, modes A and B, dists full and lp
  (2) on r71b's own command and 1 kHz rate (open-loop replay, byte-exact lane): max |r26| and fb-clamp binds, P-clamp
      and sum-clamp binds, |y| max, the largest a*s and la*o products (int32 headroom on the real drive), |T| max,
      and the trim (T - T_null) distribution vs V294.
Output: d5_score_out.txt, d5_score_<name>.json, d5_replay_internals.json
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
from d1_linear import lag_cells  # noqa: E402

NL = chr(10)


def main():
    base = H.Cells.v294()
    A = base.replace(fb_a=1017, name="A1017")
    L8 = lag_cells(base, 8.0).replace(name="L8")
    out = open(os.path.join(HERE, "d5_score_out.txt"), "w")
    for c in (A, L8):
        t0 = time.time()
        r = H.score(c)
        H.print_score(r, file=out)
        out.write("score runtime %.0f s  hash %s" % (time.time() - t0, r["meta"]["hash"]) + NL + NL)
        out.flush()
        json.dump(H.to_jsonable(r), open(os.path.join(HERE, "d5_score_%s.json" % c.name), "w"))
        print("scored", c.name, time.time() - t0, flush=True)
    # ---- (2) the drive replay with internals
    d = H.route()
    cl = [base, A, L8, base.replace(fb_clamp=0, name="null")]
    L = H.Lane(cl)
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    sp = d["sgn"].astype(np.int64)[None, :] * L.map_tab[:, d["idx"]]
    n = len(x1k)
    eng1k = np.repeat(d["eng"], 10)[:n]
    fcl = np.array([c.fb_clamp for c in cl]); pcl = np.array([c.p_clamp for c in cl]); scl = np.array([c.sum_clamp for c in cl])
    fa = np.abs(np.array([c.fb_a for c in cl])); la = np.abs(np.array([c.lag_a for c in cl]))
    Z = lambda: np.zeros(L.B, np.int64)  # noqa: E731
    r26max, fbbind, Pbind, Sbind, ymax, Tmax, asmax, laomax = Z(), Z(), Z(), Z(), Z(), Z(), Z(), Z()
    Tk = np.zeros((L.B, n), np.int32)
    t0 = time.time()
    for i in range(n):
        k = i // 10
        T, r26 = L.tick(x1k[i] * np.ones(L.B, np.int64), sp[:, k], np.full(L.B, d["idx"][k]), np.full(L.B, d["m"][k]), keep=True)
        Tk[:, i] = T
        if eng1k[i]:
            lt = L.last
            a26 = np.abs(lt["r26"])
            r26max = np.maximum(r26max, a26)
            fbbind += (fcl > 0) & (a26 >= fcl)
            Pbind += np.abs(lt["P"]) >= pcl
            Sbind += np.abs(lt["S"]) >= scl
            ymax = np.maximum(ymax, np.abs(lt["y"]))
            Tmax = np.maximum(Tmax, np.abs(T))
            asmax = np.maximum(asmax, np.abs(L.s) * fa)
            laomax = np.maximum(laomax, np.abs(L.o) * la)
    out.write("(2) r71b open-loop replay with internals (%.0f s, %d ticks, engaged ticks %d)" % (time.time() - t0, n, int(eng1k.sum())) + NL)
    res2 = {}
    for j, c in enumerate(cl):
        out.write("   %-6s max|r26| %d (clamp %d, binds %d)  P binds %d  S binds %d  max|y| %d  max|T| %d  max a*s %.3g (margin %.1f)"
                  "  max la*o %.3g (margin %.1f)" % (c.name, r26max[j], c.fb_clamp, fbbind[j], Pbind[j], Sbind[j], ymax[j], Tmax[j],
                                                     asmax[j], 2 ** 31 / max(asmax[j], 1), laomax[j], 2 ** 31 / max(laomax[j], 1)) + NL)
        res2[c.name] = dict(r26max=int(r26max[j]), fbbind=int(fbbind[j]), Pbind=int(Pbind[j]), Sbind=int(Sbind[j]), ymax=int(ymax[j]),
                            Tmax=int(Tmax[j]), as_margin=float(2 ** 31 / max(asmax[j], 1)), lao_margin=float(2 ** 31 / max(laomax[j], 1)))
    null = Tk[3].astype(float)
    for j, c in enumerate(cl[:3]):
        tr = Tk[j].astype(float) - null
        out.write("   %-6s trim (T - T_null) on engaged ticks: rms %.2f  p99 %.1f  max %.0f" % (
            c.name, np.sqrt(np.mean(tr[eng1k] ** 2)), np.percentile(np.abs(tr[eng1k]), 99), np.abs(tr[eng1k]).max()) + NL)
        res2[c.name]["trim_rms"] = float(np.sqrt(np.mean(tr[eng1k] ** 2)))
    json.dump(res2, open(os.path.join(HERE, "d5_replay_internals.json"), "w"), indent=1)
    out.close()


if __name__ == "__main__":
    main()
