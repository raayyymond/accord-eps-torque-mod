# -*- coding: utf-8 -*-
"""nl_turnhold.py -- TURN-HOLD at realistic curve sizes (nonlinear lens, C2 rev 2).  The harness's A_TURN (5 deg at
19 m/s, 3 deg at 26 m/s) never loads the integrator past its clamp ICL 4096 S (~657 T after the output stage), so the
designers' turn-hold numbers never test the clamp.  Here the hold angle is set by lateral acceleration:
th_sw = a_lat * L * SR / v^2 (deg), L 2.83 m, SR 16 (BELIEF: no understeer, the fork map's centre ratio), a_lat in
{0.5, 1.0, 1.5, 2.0} m/s^2; ramp 1.5 s, hold 8 s; hold ratio = mean(th)/th_sp over the last 2 s; also the spring
load k sat tanh(th/sat) against the I's ceiling.  Members nominal / bc / F_hi / b_lo*J_hi, ages native and +h10.
ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_sim as S  # noqa
import nl_lens as L  # noqa
SPEEDS = (8.0, 10.0, 11.9, 13.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 24.0, 26.9, 30.0)
ALAT = (0.5, 1.0, 1.5, 2.0)
IM = ("P2", "F2", "D2a", "B0r")
MEM = ("nominal", "bc", "F_hi", "b_lo*J_hi", "nominal_nf")
lines = ["# turn-hold vs lateral acceleration (hold ratio over the last 2 s of an 8 s hold); load = spring torque at the "
         "target (T counts); I ceiling ~657 T"]
for mem in MEM:
    cols = [dict(impl=i, member=mem, v=v, age=a, alat=al) for a in (0, 10) for v in SPEEDS for al in ALAT for i in IM]
    tgt = np.array([c["alat"] * 2.83 * 16.0 / c["v"] ** 2 * 180 / np.pi for c in cols])
    scn = S.Scn(dur=11.0, ref=lambda t: tgt * np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1]))
    r = S.run(cols, scn)
    th = r["th"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    w = (tt >= 9.0) & (tt < 11.0)
    ratio = th[w].mean(0) / tgt
    Isat = (np.abs(r["I"][w]) >= 4096).mean(0)
    for a in (0, 10):
        for al in ALAT:
            for im in IM:
                idx = [j for j, c in enumerate(cols) if c["age"] == a and c["alat"] == al and c["impl"] == im]
                cells = []
                for j in idx:
                    J, b, k, sat, Fc, Fs, tau = S.params(mem, cols[j]["v"])
                    load = k * sat * np.tanh(tgt[j] / sat)
                    cells.append(f"{cols[j]['v']:g}:{ratio[j]:.2f}{'*' if Isat[j] > 0.5 else ''}({tgt[j]:.0f}d,{load:.0f}T)")
                lines.append(f"{mem:11s} {'+h10' if a else 'age1-10':7s} a {al:.1f} {im:3s} " + " ".join(cells))
    print("\n".join(lines[-16:]), flush=True)
(L.OUT / "turnhold.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
