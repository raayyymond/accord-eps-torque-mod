# -*- coding: utf-8 -*-
r"""s4b_slew_attrib.py -- D5-architect.  Which V299-(b) element makes the 3-8 m/s hands-off slew overshoot, and what
dose of the lead to fly?  Closed loop on s4_closed_loop's engine (panel2 CandLane + fork model), slew + drift only,
3 / 5 / 8 m/s, members nominal and r79F.  Variants change ONE element of V299b at a time.  Wall printed (< 30 s).
"""
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_closed_loop as S  # noqa: E402

VAR = {
    "V298": ("V298", dict(S.FORK["V298"])),
    "b:final(lead.5,nokick)": ("V299b", dict(S.FORK["V299b"])),
    "b:lead0": ("V299b", dict(S.FORK["V299b"], lead=0.0)),
    "b:lead.7": ("V299b", dict(S.FORK["V299b"], lead=0.7 / 0.5)),
    "b:+kick (rejected)": ("V299b", dict(S.FORK["V299b"], kick=1.0)),
    "b:A3cap removed": ("V299bnoA3", dict(S.FORK["V299b"])),
    "b:clipV298": ("V299b", dict(S.FORK["V299b"], clip=S.EV298)),
    "b:fw only (V298 fork)": ("V299b", dict(S.FORK["V298"])),
    "b:fork only (V298 fw)": ("V298", dict(S.FORK["V299b"])),
}
S.FW["V299bnoA3"] = S.ST.Cand("V299bnoA3", "D5", S.GBP, "fresh", 48, ki=40, icl=8192, thr=1229, sgn_thr=0,
                              arb=(6, 4, 2880, 1250, 0, 4096), ramp_in=328, ramp_out=66)


def install():
    for k, (fw, fk) in VAR.items():
        S.FW[k] = S.FW[fw].__class__(**{**S.FW[fw].__dict__, "id": k})
        S.FORK[k] = fk
    S.CANDS = tuple(VAR)
    S.MEMBERS = ("nominal", "r79F")


def job(name):
    install()
    t0 = time.time()
    if name == "slew":
        S.SLEW_A = {3.0: 90.0, 5.0: 90.0, 8.0: 45.0}
        S.SPEEDS = tuple(S.SLEW_A)
        nm, out = S.sc_slew()
    else:
        nm, out = S.sc_drift()
    return nm, out, time.time() - t0


if __name__ == "__main__":
    T0 = time.time()
    with Pool(2) as P:
        res = P.map(job, ["slew", "drift"])
    for nm, out, w in res:
        print("== %s (%.1f s)" % (nm, w))
        for r in out:
            if nm == "slew":
                print("  %-22s %-8s v %4.1f t90 %.3f over %+.3f cover %.2f Tpk %5.0f wpk %4.0f g20 %.3f" % (
                    r["cand"], r["member"], r["v"], r["t90"], r["over"], r["cover"], r["T_peak"], r["w_peak"], r["g20_rms"]))
            elif r["v"] in (3.0, 8.0, 12.0, 20.0):
                print("  %-22s %-8s v %4.1f stuck %.3f brk %.2f lagerr %.3f" % (r["cand"], r["member"], r["v"],
                                                                               r["stuck_frac"], r["brk_err_p50"],
                                                                               r["lag_err_p50"]))
    print("wall %.1f s" % (time.time() - T0))
