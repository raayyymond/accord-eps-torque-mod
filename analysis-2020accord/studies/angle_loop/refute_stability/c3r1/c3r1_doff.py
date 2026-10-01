# -*- coding: utf-8 -*-
"""c3r1_doff.py -- the RATE-INVALID state (design section 7, H-rate, claimed 'fails safe'): Honda's validity form makes
op := 0 (C3-P, cave 0xC4C08..12) and FUN_0003f776 writes gp-0x6a56 := 0 (C3-F), so D = 0 while the angle P + I keep
running on gp-0x6a00 (a different path).  Exact periodic rho of that PI-only loop over the gated set, every speed
1..35 (1 m/s) + knots, e 0 / 10, the gated frames (kappa is moot with D = 0; jb matters).
python c3r1_doff.py -> _scratch/.../doff_out.txt"""
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402

D = M.designs()
SP = sorted(set(list(np.arange(1.0, 35.01, 1.0)) + [3.1, 8.0, 11.9, 17.0, 26.9]))
MEMS = S.SINGLE + S.COMBINED


def work(args):
    mem, v = args
    pl = M.member(mem, v)
    res = []
    for dn in ("C3-P", "C3-F"):
        for e in (0, 10):
            for jb in (1.0, 1 / 1.155):
                rho, f, z, _ = M.Periodic(D[dn], pl, v, e=e, jb=jb, kd_scale=0.0).rho_ring()
                res.append((dn, mem, float(v), e, jb, rho, f, z))
    return res


if __name__ == "__main__":
    with Pool(14) as pool:
        R = [r for rr in pool.imap_unordered(work, [(m, v) for m in MEMS for v in SP]) for r in rr]
    out = []
    for dn in ("C3-P", "C3-F"):
        X = [r for r in R if r[0] == dn]
        un = [r for r in X if r[5] >= 1.0]
        low = [r for r in X if r[7] < 0.10]
        out.append(f"{dn} D=0: {len(X)} points; rho >= 1: {len(un)}; least-damped zeta < 0.10: {len(low)}")
        for r in sorted(un, key=lambda r: -r[5])[:12]:
            out.append(f"   UNSTABLE {r[1]}@{r[2]} e{r[3]} jb{r[4]:.3f}: rho {r[5]:.5f} pole {r[6]:.2f} Hz zeta {r[7]:.4f}")
        mems = sorted(set(r[1] for r in un))
        out.append(f"   members with an unstable point: {mems}")
        for m in ("nominal", "J_hi", "b_lo", "ms_free", "b_lo*J_hi", "b_q*J1.0"):
            Y = [r for r in X if r[1] == m]
            w = max(Y, key=lambda r: r[5])
            out.append(f"   worst {m:10s}: rho {w[5]:.5f} at {w[2]} e{w[3]} jb{w[4]:.3f} ({w[6]:.2f} Hz zeta {w[7]:.3f})")
    (Path(M.OUT) / "doff_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
