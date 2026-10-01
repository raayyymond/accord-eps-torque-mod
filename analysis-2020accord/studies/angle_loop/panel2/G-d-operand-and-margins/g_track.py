# -*- coding: utf-8 -*-
r"""g_track.py -- the TRACKING PRICE of each implementation's table, LINEAR (the goal's own metric as a frequency weighting,
c1r2_trackmetric.slope, as rev2-A's r2a_freq section D used it), turn-hold |T_ref(0.02 Hz)| and the hard-turn band
|T_ref| 1.6-3 Hz, per member (incl. frame variants) and speed >= 8 m/s, and the Kp_eff / T-per-degree the table gives.
The linear metric cannot see the integrator clamp (round-2 nonlinear finding F1); g_nl.py runs the refuter's nonlinear
r71b-path metric for the clamp.  ANALYSIS ONLY.   usage: python g_track.py <impl id> ...  -> g_track_out.txt"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_gate as GG  # noqa: E402
import c1r2_trackmetric as TM  # noqa: E402

SF = X.SF
MEMS = ("nominal", "b_lo", "b_hi", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "ms_free",
        "nominal+h10", "b_q*J1.0+h10", "nominal|fb", "J_hi|fb", "nominal|k0.83", "b_q*J1.0|k0.83", "b_q*ms_free",
        "b_lo*ms_free")
VS = (8.0, 9.0, 10.0, 11.0, 11.9, 12.5, 13.5, 15.0, 17.0, 19.0, 22.0, 26.0, 26.9, 30.0)


def Tr_fn(c, name, v):
    def Tf(f):
        f = np.asarray(f, float)
        Pt, Pw = X.DM.plant_frf(X.plant_ext(name, v)[0], f)
        pl, d, ea, jbk, kappa = X.plant_ext(name, v)
        pr = c.cont(v)
        Cth0, Cref0, CthD, CwD = X.ctl_parts(c, pr, ea, f)
        kd = pr["kd"]
        Cth = Cth0 + kd * kappa * CthD
        Cw = kd * kappa * CwD
        K = SF.K_out(f, d)
        L = -K * (Cth * Pt + Cw * Pw)
        return K * Cref0 * Pt / (1 + L)
    return Tf


def run(iids):
    lines = []

    def P(t=""):
        print(t, flush=True)
        lines.append(t)
    summ = {}
    for iid in iids:
        c = GG.cand_of(iid)
        im = GG.impls()[iid]
        P(f"--- {iid}: {im['note']}")
        wmin, wmax, hmin, t163 = 9.0, 0.0, 9.0, 0.0
        per_v = {}
        for v in VS:
            vals, holds, trs = [], [], []
            for m in MEMS:
                Tf = Tr_fn(c, m, v)
                vals.append(TM.slope(Tf, v))
                fr = np.array([0.02])
                holds.append(float(abs(Tf(fr)[0])))
                f16 = np.linspace(1.6, 3.0, 29)
                trs.append(float(np.max(np.abs(Tf(f16)))))
            G = X.G_of(im["rows"], v)
            per_v[v] = dict(G=G, mmin=min(vals), mmax=max(vals), nominal=vals[0], hold=min(holds), t163=max(trs))
            wmin, wmax = min(wmin, min(vals)), max(wmax, max(vals))
            hmin, t163 = min(hmin, min(holds)), max(t163, max(trs))
            P(f"  v {v:5.1f} G {G:5.0f} (T/deg {0.1002 * 112 * G / 256:5.1f}): metric nominal {vals[0]:.3f} min "
              f"{min(vals):.3f} ({MEMS[int(np.argmin(vals))]}) max {max(vals):.3f} | hold min {min(holds):.3f} | "
              f"Tr1.6-3 max {max(trs):.2f} ({MEMS[int(np.argmax(trs))]}) nominal {trs[0]:.2f}")
        P(f"  => {iid}: linear goal metric >= 8 m/s {wmin:.3f} .. {wmax:.3f} "
          f"({'PASS' if 0.95 <= wmin and wmax <= 1.05 else 'FAIL'} 0.95-1.05); turn-hold min {hmin:.3f}; "
          f"|T_ref| 1.6-3 Hz max {t163:.2f}")
        summ[iid] = dict(metric_min=wmin, metric_max=wmax, hold_min=hmin, t163=t163, per_v=per_v)
    return lines, summ


if __name__ == "__main__":
    iids = sys.argv[1:]
    lines, summ = run(iids)
    tag = "_".join(iids)
    (HERE / f"g_track_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (X.OUT / f"track_{tag}.json").write_text(json.dumps(summ, default=float))
