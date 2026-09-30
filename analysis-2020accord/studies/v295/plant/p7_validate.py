# -*- coding: utf-8 -*-
"""p7_validate.py -- TASK 4: validate the delivered plant FAMILY by replaying the route's own 0xE4 command through the
byte-exact V294 lane + each family member on HELD-OUT data (never used by any fit), scoring simulated vs measured.
python p7_validate.py -> p7_validate_out.txt, _scratch/p7.json

Two replay forms, both CLOSED on the inner loop (command -> Lane294 (== golden model) -> plant -> x -> lane):
  (1) 1 s windows (the multiple-shooting form): start = the measured th, om and the march's exact lane state; one
      nuisance per window (c0 = the model's mean equation residual over the window +-0.5 s).  Scores: om R2 / fit%, the
      om 'skill' over holding om at its start value, dth R2 (angle change from the start), tap R2.  Windows banded by
      their OWN speed, held-out = windows of the held-out 20 s parents.
  (2) 20 s free-run segments (oe_lib.Batch): start from the measured state, lane fb state at the fixed point of x0, output
      lag at the march's T; one nuisance per segment (c0); th scored segment-demeaned.  This is the demanding form:
      stick-slip timing and slow road drift accumulate.
F4 (pre-registered): for a band with >= 60 s of held-out data, the NOMINAL's (1) angle R2 < 0.5 or rate R2 < 0.3 = the
plant is NOT READY for that band.  F5: any member diverging under the SHIPPED cells (|om| > 1500 deg/s, non-finite, or
|T| at the 3072 clamp on > 1 % of ticks) in either form.
Also: the linear wheel mode (f, zeta), open and with the V294 lane (exact 1 kHz poles, friction off), per member.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oe_lib as O  # noqa: E402
import plib as P  # noqa: E402
import v294_plant as VP  # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def divergence(out):
    om_max = float(np.nanmax(np.abs(out["om"])))
    clamp = float(np.mean(np.abs(out["T"]) >= 3072))
    return (not np.all(np.isfinite(out["om"]))) or om_max > 1500 or clamp > 0.01, om_max, clamp


def main():
    d = P.load()
    c = VP.v294_cells()
    cl = dict(c)
    cl["kp_Y"] = [float(c["kp_Y"][0])]
    fam = VP.family()
    fam["nominal+mode13"] = fam["nominal"].with_mode20(f2=13.0, zeta2=0.10, r2=0.2)
    fam["nominal+mode20"] = fam["nominal"].with_mode20(f2=20.0, zeta2=0.05, r2=0.2)
    segs = O.segments(d)
    wins = O.windows(segs, d=d)
    res = {"win": {}, "seg": {}}
    f5 = []
    pr("(1) HELD-OUT 1 s WINDOWS: route command -> byte-exact V294 lane -> speed-scheduled plant (1 kHz)")
    pr("  %-15s %-6s %4s | %7s %6s %6s | %7s | %7s | %s" % ("member", "band", "win", "om R2", "fit%", "skill", "dth R2",
                                                         "tap R2", "F5"))
    for nm, mem in fam.items():
        res["win"][nm] = {}
        for bi, (bn, lo, hi) in enumerate(P.BANDS):
            wh = [w for w in wins if w["band"] == bi and w["role"] == "held"]
            if not wh:
                continue
            W = O.WindowBatch(d, wh, c)
            out, _ = W.replay(mem)
            sc = W.scores(out)
            dv, om_max, clamp = divergence(out)
            if dv:
                f5.append((nm, bn, "win"))
            sc.update(n=len(wh), seconds=len(wh) * 1.0, om_max=om_max, clamp=clamp, diverged=bool(dv))
            res["win"][nm][bn] = sc
            pr("  %-15s %-6s %4d | %+7.3f %6.1f %+6.2f | %+7.3f | %+7.4f | %s" % (
                nm, bn, len(wh), sc["om_R2"], sc["om_fit"], sc["om_skill_vs_hold"], sc["dth_R2"], sc["T_R2"],
                "DIVERGED" if dv else "ok"))
    pr("")
    pr("(2) HELD-OUT 20 s FREE-RUN SEGMENTS (th segment-demeaned)")
    pr("  %-15s %-6s %4s | %7s %6s | %7s %6s | %7s | %s" % ("member", "band", "s", "th R2", "fit%", "om R2", "fit%", "tap R2", "F5"))
    for nm, mem in fam.items():
        res["seg"][nm] = {}
        for bi, (bn, lo, hi) in enumerate(P.BANDS):
            hs = [s for s in segs if s["band"] == bi and s["role"] == "held"]
            if not hs:
                continue
            Bh = O.Batch(d, hs, c)
            out, _ = Bh.replay(mem)
            sc = Bh.scores(out)
            dv, om_max, clamp = divergence(out)
            if dv:
                f5.append((nm, bn, "seg"))
            sc.update(seconds=float(Bh.mask.sum() / 100.0), om_max=om_max, clamp=clamp, diverged=bool(dv))
            res["seg"][nm][bn] = sc
            pr("  %-15s %-6s %4.0f | %+7.3f %6.1f | %+7.3f %6.1f | %+7.4f | %s" % (
                nm, bn, sc["seconds"], sc["th_R2"], sc["th_fit"], sc["om_R2"], sc["om_fit"], sc["T_R2"],
                "DIVERGED" if dv else "ok (max |om| %.0f)" % om_max))
    pr("")
    for bn, sc in res["win"]["nominal"].items():
        f4 = sc["seconds"] >= 60 and (sc["dth_R2"] < 0.5 or sc["om_R2"] < 0.3)
        pr("  F4 band %-6s (%3.0f s held-out windows): nominal angle R2 %.3f, rate R2 %.3f (skill over hold %.2f) -> %s" % (
            bn, sc["seconds"], sc["dth_R2"], sc["om_R2"], sc["om_skill_vs_hold"],
            "FIRES -- NOT READY for this band" if f4 else ("does not fire" if sc["seconds"] >= 60 else
                                                          "n/a (< 60 s held-out; reported, not gated)")))
    pr("  F5: %s" % ("FIRES for %s" % f5 if f5 else "does not fire -- no member diverged under the shipped V294 cells"))
    pr("")
    pr("LINEAR WHEEL MODE (exact 1 kHz poles, friction off, sp = 0): f Hz / zeta, open plant -> with the V294 lane")
    modes = {}
    for nm, mem in fam.items():
        row = []
        modes[nm] = []
        for v in VP.V_CENTRES:
            p = mem.at(v)
            fo, zo = VP.wheel_mode(p, cl, lane_on=False)
            fc_, zc_ = VP.wheel_mode(p, cl)
            modes[nm].append(dict(v=float(v), f_open=fo, z_open=zo, f_lane=fc_, z_lane=zc_))
            row.append("%4.2f/%4.2f->%4.2f/%4.2f" % (fo, zo, fc_, zc_))
        pr("  %-15s %s" % (nm, "  ".join(row)))
    pr("  (columns: v = %s m/s; 'nan' = no oscillatory pair below 8 Hz, i.e. overdamped)" % list(VP.V_CENTRES))
    json.dump(dict(scores=res, modes=modes, f5=f5), open(os.path.join(HERE, "_scratch", "p7.json"), "w"), indent=1)
    open(os.path.join(HERE, "p7_validate_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
