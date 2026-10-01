# -*- coding: utf-8 -*-
r"""g_stress.py -- two-mass stress beyond the gate (rev2-A r2a_freq section F and the stability refuter's E3, extended to
the D-operand frame): a collocated two-mass mode at 13 / 15 / 16.5 / 17 / 20 Hz, zeta2 0.02 / 0.05, wheel share r2 0.2 /
0.4 (ds_gate2.two_mass_mu: the free-free resonance at f2), on nominal, b_lo, b_q, nominal+h10 and -- for the rate-operand
D -- nominal at kappa 1.155 (the strongest D the frame allows) aged and not, at every 1 m/s 1-35.  Per point: the EXACT
rho (g_exact), the least-damped 5-50 Hz closed-loop pole (frequency, zeta) and the 5-30 Hz closed-loop peak
max(|Tc|, |Tref|) (LTI, score_freq's extractor).  The question: does the D re-sizing create or de-damp a 13-20 Hz line?
ANALYSIS ONLY.   usage: python g_stress.py <impl> ...   -> g_stress_out.txt (appends) + _scratch json"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_exact as GE  # noqa: E402
import g_gate as GG  # noqa: E402

SF, DM, G2 = X.SF, X.DM, X.G2
MODES = [(f2, z2, r2) for f2 in (13.0, 15.0, 16.5, 17.0, 20.0) for z2 in (0.02, 0.05) for r2 in (0.2, 0.4)]
VS = [float(v) for v in range(1, 36)]


def point(args):
    iid, base, f2, z2, r2, v = args
    im = GG.impls()[iid]
    b, ea, kappa, jb = X._split(base)
    J, bb, k, d, ea0 = X.params_ext(b, v)
    pl = G2.two_mass_mu(J * jb, bb * jb, k, f2, z2, r2)
    ea = ea0 + ea
    G = X.G_of(im["rows"], v)
    ex = GE.Exact(im["dkind"], pl, d, ea, G, 112, im.get("ki", 56), im["kd"], kappa=kappa,
                  dop_k=2.0 ** im.get("sh", 6))
    lam = np.linalg.eigvals(ex.monodromy())
    rho = float(np.max(np.abs(lam)))
    hf = (float("nan"), 9.0)
    for l in lam:
        if abs(l) < 1e-9:
            continue
        s = np.log(complex(l)) / 0.01
        f = abs(s.imag) / (2 * np.pi)
        z = -s.real / abs(s)
        if 5.0 <= f <= 49.9 and z < hf[1]:
            hf = (f, z)
    c = GG.cand_of(iid)
    pr = dict(c.cont(v), G=G)
    Cth0, Cref0, CthD, CwD = X.ctl_parts(c, pr, ea)
    kd = im["kd"]
    Cth = Cth0 + kd * kappa * CthD
    Cw = kd * kappa * CwD
    K = SF.K_out(X.F, d)
    Pt, Pw = DM.plant_frf(pl, X.F)
    m = SF.metrics_from(Cth, Cw, Cref0, K, Pt, Pw)
    return dict(iid=iid, base=base, f2=f2, z2=z2, r2=r2, v=v, rho=rho, hf_f=hf[0], hf_z=hf[1],
                peak=max(m["Tc530"], m.get("Tr530", -99.0)))


def run(iids, procs=6):
    lines = []

    def P(t=""):
        print(t, flush=True)
        lines.append(t)
    for iid in iids:
        im = GG.impls()[iid]
        bases = ["nominal", "b_lo", "b_q", "nominal+h10"]
        if im["dkind"] != "box10":
            bases += ["nominal|k1.155", "nominal+h10|k1.155"]
        jobs = [(iid, b, f2, z2, r2, v) for b in bases for (f2, z2, r2) in MODES for v in VS]
        t0 = time.time()
        with Pool(procs) as pool:
            res = pool.map(point, jobs, chunksize=8)
        (X.OUT / f"stress_{iid}.json").write_text(json.dumps(res))
        uns = [r for r in res if r["rho"] >= 1]
        w = min(res, key=lambda r: r["hf_z"])
        pk = max(res, key=lambda r: r["peak"])
        P(f"{iid}: {len(res)} points ({time.time() - t0:.0f} s): unstable {len(uns)}; least-damped 5-50 Hz pole "
          f"{w['hf_f']:.2f} Hz zeta {w['hf_z']:.3f} ({w['base']}, mode {w['f2']} Hz z2 {w['z2']} r2 {w['r2']}, {w['v']} m/s); "
          f"max 5-30 Hz closed-loop peak {pk['peak']:+.1f} dB ({pk['base']}, mode {pk['f2']} Hz z2 {pk['z2']}, {pk['v']} m/s)")
        for f2 in (13.0, 15.0, 16.5, 17.0, 20.0):
            rr = [r for r in res if r["f2"] == f2 and r["z2"] == 0.02]
            wz = min(rr, key=lambda r: r["hf_z"])
            P(f"    mode {f2:4.1f} Hz (open zeta 0.02): closed-loop least zeta {wz['hf_z']:.3f} at {wz['hf_f']:.2f} Hz "
              f"({wz['base']}, {wz['v']} m/s); max peak {max(r['peak'] for r in rr):+.1f} dB")
    with open(HERE / "g_stress_out.txt", "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    run(sys.argv[1:])
