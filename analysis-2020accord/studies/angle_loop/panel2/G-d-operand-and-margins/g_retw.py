# -*- coding: utf-8 -*-
r"""g_retw.py -- Re(T/w) 5-25 Hz (the controller's output impedance, T counts per deg/s, > 0 damps), WORST over every
speed 1-35 m/s at 0.25, for designer G's implementations against V294 / V295 under the SAME condition, at:
  hold ages 0-9 ('h0', slot 4 before the lane), 1-10 (native), 11-20 (+h10), 21-30 (+h20)
  transport 2 ms and 6 ms
  rate-former lag 0 / 0.5 / 1 tick on every rate operand (the candidate's AND V295's: both read the gp-0x4f50 former)
  the D-operand frame: s = 1 (the common scorer's convention) and s = 1.155 (near centre: every lin-frame rate
  operand, the candidate's and V295's, x 1/1.155 per degree/s of gp-0x6a00; the angle-own D unscaled)
This is the stability refuter's E1 attack list (REFUTE-C2-r2-stability F2), extended by +h20 and the frame.
ANALYSIS ONLY.  usage: python g_retw.py <impl id> ...   -> g_retw_out.txt (appends per run) + _scratch json"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_gate as GG  # noqa: E402

SF, DM = X.SF, X.DM
FR = np.array([5.0, 7.0, 10.0, 13.0, 15.0, 17.0, 20.0, 25.0])
VS = [round(x, 2) for x in np.arange(1.0, 35.01, 0.25)]
AGES = (("0-9", -1), ("1-10", 0), ("11-20", 10), ("21-30", 20))


def rf(f, lag):
    q = SF._z(f)
    a = min(lag, 1.0)
    return (1 - a) + a * q


def cand_re(iid, v, ea, d, lag, s):
    im = GG.impls()[iid]
    c = GG.cand_of(iid)
    G = X.G_of(im["rows"], v)
    pr = dict(c.cont(v), G=G, kd=0.0)
    Cth0, _, CthD, CwD = X.ctl_parts(c, pr, ea, FR)
    kap = 1.0 if im["dkind"] == "box10" else 1.0 / s
    Cth = Cth0 + im["kd"] * CthD
    Cw = im["kd"] * kap * CwD * rf(FR, lag)
    if im["dkind"] == "held":
        pass                                                   # the held operand also carries the former (rf above)
    K = SF.K_out(FR, d)
    w = 2 * np.pi * FR
    return (-K * (Cth + 1j * w * Cw) / (1j * w)).real


def ref_re(nm, ea, d, lag, s):
    des = replace(SF.des_for_ref(nm), d=d, extra_age=ea)
    Cth, Cw, _ = DM.ctl_frf(FR, des)
    K = DM.K_out(FR, des)
    w = 2 * np.pi * FR
    return (-K * (Cth + 1j * w * (Cw / s) * rf(FR, lag)) / (1j * w)).real


def table(iids):
    lines = []

    def P(t=""):
        print(t, flush=True)
        lines.append(t)
    P("Re(T/w) worst over 1-35 m/s, T counts per deg/s (> 0 damps); ratio = candidate / V295 where V295 < 0 "
      "(>1 = more anti-damping than V295); '+' where V295 damps and the candidate does not")
    P("freqs Hz: " + " ".join(f"{f:6.0f}" for f in FR))
    out = {}
    for s in (1.0, X.S_C):
        for d in (2, 6):
            for lag in (0.0, 0.5, 1.0):
                for agl, ea in AGES:
                    cond = f"s={s:.3f} d={d}ms lag={lag} ages {agl}"
                    r295 = ref_re("V295", ea, d, lag, s)
                    r294 = ref_re("V294", ea, d, lag, s)
                    P(f"--- {cond}")
                    P(f"    V294          " + " ".join(f"{x:+6.2f}" for x in r294))
                    P(f"    V295          " + " ".join(f"{x:+6.2f}" for x in r295))
                    for iid in iids:
                        W = np.min([cand_re(iid, v, ea, d, lag, s) for v in VS], axis=0)
                        rat = [(w / r if r < 0 else (float("inf") if w < 0 else 0.0)) for w, r in zip(W, r295)]
                        P(f"    {iid:12s}  " + " ".join(f"{x:+6.2f}" for x in W) + "   x V295: " +
                          " ".join(("  +inf" if not np.isfinite(x) else f"{x:6.2f}") for x in rat))
                        out[(iid, cond)] = dict(W=W.tolist(), ratio=rat, v295=r295.tolist(), v294=r294.tolist())
    return lines, out


if __name__ == "__main__":
    iids = sys.argv[1:]
    lines, out = table(iids)
    tag = "_".join(iids)
    (HERE / f"g_retw_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (X.OUT / f"retw_{tag}.json").write_text(json.dumps({f"{k[0]}|{k[1]}": v for k, v in out.items()}, default=float))
