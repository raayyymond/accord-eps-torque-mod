# -*- coding: utf-8 -*-
"""c1_design_G.py -- size the C1 speed gain G(v) on a 0.25 m/s grid (plus the plant knots 3.1/8.0/11.9/17.0/26.9 and
the 10.5..12.0 m/s trough the stability refuter found), against every member of c1_members by tier.

Method (EVIDENCE when run): the loop is LINEAR in g = G/256 --
    L(f; g) = g * A(f) + B(f),   A = K*PI*80*(1+z^-1)*hold*Pt ,  B = K*Kd*hold*Pw
(the stability refuter's stab_lin.frf, factored; K = fade*FWD*Hout*z^-d, PI = Kp_base/256 + Ki_base/32768/(1-z^-1)).
For each (member, v) A and B are computed once; PM(g) is then scanned on a G grid (step 8) and the largest G whose PM
meets the member's tier (A 45 deg, B 30 deg) -- scanning UP from G = 128, stopping at the first failure -- is G_max.
The envelope G_env(v) = min over the gating members.  Report-only members are tabulated, not gated.
Output: _scratch/angle_loop/c1/design_G.json and design_G.txt (copied next to this script)."""
from __future__ import annotations

import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_members as M  # noqa: E402
import stab_lin as S  # noqa: E402

F = np.logspace(math.log10(0.05), math.log10(120.0), 2500)
GGRID = np.arange(128, 6001, 8)
SPEEDS = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))


def AB(name, v, kp=C.KP_BASE, ki=C.KI_BASE, kd=C.KD):
    pl, tau, ea, _ = M.member(name, v)
    A_, B_, Ct, Cw = pl
    Ad, Bd = S.c2d(A_, B_)
    z = np.exp(1j * 2 * np.pi * F * S.TS)
    zi = 1 / z
    # 2x2 resolvent (zI - Ad)^-1 Bd, vectorised
    a, b, c, d = Ad[0, 0], Ad[0, 1], Ad[1, 0], Ad[1, 1]
    det = (z - a) * (z - d) - b * c
    x0 = ((z - d) * Bd[0, 0] + b * Bd[1, 0]) / det
    x1 = (c * Bd[0, 0] + (z - a) * Bd[1, 0]) / det
    Pt, Pw = x0, x1                                     # Ct = [1,0], Cw = [0,1]
    hold = sum(zi ** (q + ea) for q in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** tau
    PI = kp / 256 + (ki / 32768) / (1 - zi)
    A = K * PI * 80 * (1 + zi) * hold * Pt
    B = K * kd * hold * Pw
    return A, B


def pm_of(L):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    s = np.sign(mag - 1)
    idx = np.where(s[:-1] * s[1:] <= 0)[0]
    if len(idx) == 0:
        return float("nan"), float("nan")
    pms, fcs = [], []
    for i in idx:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        pms.append(((p + 180) + 180) % 360 - 180)
        fcs.append(F[i] + t * (F[i + 1] - F[i]))
    j = int(np.argmin(pms))
    return pms[j], fcs[j]


def gmax_for(name, v, thr):
    A, B = AB(name, v)
    best = None
    pm_lo = None
    for G in GGRID:
        pm, fc = pm_of((G / 256) * A + B)
        if pm_lo is None:
            pm_lo = pm
        if not (pm >= thr):
            break
        best = int(G)
    return best, pm_lo


def job(v):
    out = {}
    for name in M.TIER_A + M.TIER_B + M.REPORT:
        thr = M.TIER_PM.get(name, 30.0)
        g, pm_lo = gmax_for(name, v, thr)
        out[name] = dict(G=g, pm_at_G128=pm_lo, thr=thr)
    return v, out


def main():
    t0 = time.time()
    with Pool(12) as pool:
        res = dict(pool.map(job, SPEEDS))
    js = {str(v): r for v, r in res.items()}
    (C.OUT / "design_G.json").write_text(json.dumps(js))
    lines = ["# c1_design_G.py: G_max(v) per member (G in the C1 base: Kp_eff = 225*G/256); None = fails at G = 128",
             "# tier A gate PM >= 45 deg; tier B gate PM >= 30 deg; report-only members at 30 deg, not gated",
             "  v     envA  (binding)       envB  (binding)       env   Kp_eff | " + " ".join(f"{m[:9]:>9s}" for m in M.REPORT)]
    for v in SPEEDS:
        r = res[v]
        def env(names):
            vals = [(r[n]["G"] if r[n]["G"] is not None else 0, n) for n in names]
            return min(vals)
        ea, na = env(M.TIER_A)
        eb, nb = env(M.TIER_B)
        e = min(ea, eb)
        rep = " ".join(f"{(r[n]['G'] if r[n]['G'] is not None else 0):9d}" for n in M.REPORT)
        lines.append(f"{v:6.2f}  {ea:5d} ({na:>12s})  {eb:5d} ({nb:>14s})  {e:5d}  {225*e/256:6.0f} | {rep}")
    txt = "\n".join(lines)
    (C.OUT / "design_G.txt").write_text(txt)
    (HERE / "design_G.txt").write_text(txt)
    print(txt)
    print("[%.0f s]" % (time.time() - t0))


if __name__ == "__main__":
    main()
