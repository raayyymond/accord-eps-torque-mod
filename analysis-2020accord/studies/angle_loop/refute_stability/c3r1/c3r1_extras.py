# -*- coding: utf-8 -*-
"""c3r1_extras.py -- the three inline checks the report quotes, saved for reproduction:
 (X1) cross-code check of the operating-point margins on the round-2 refuter's c2r2_model (a different code base);
 (X2) the same operating points on every C3 variant (C3-Pd, C3-P44; C3-PA2 has C3-P's linear loop);
 (X3) the Ki feasibility probe (NOT a design).
python c3r1_extras.py -> _scratch/.../extras_out.txt"""
import dataclasses
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "c2r2"))
import c3r1_model as M  # noqa: E402
import c3r1_kop as K  # noqa: E402
import c2r2_model as R  # noqa: E402

D = M.designs()
out = []
P = lambda *a: (out.append(" ".join(str(x) for x in a)), print(out[-1], flush=True))  # noqa: E731


def s2(v, a):
    return 1 - math.tanh(K.theta_op(v, a) / K.sat(v)) ** 2 if a > 0 else 1.0


P("(X1) operating-point PM: mine vs the c2r2 code (C3 tables parsed by each code from the C3 hex)")
rows, _, _ = R.cave_table(M.C3D / "c3_cave_C3-P.hex")
rowsF, _, _ = R.cave_table(M.C3D / "c3_cave_C3-F.hex")
RD = {"C3-P": R.Design("C3-P", None, "fresh", kd=48, rows=rows), "C3-F": R.Design("C3-F", None, "held", kd=24, rows=rowsF)}
for dn in ("C3-P", "C3-F"):
    for mem, v, a, e, kap in (("ms_free", 12.0, 0.0, 0, 1.0), ("ms_free", 12.0, 1.5, 0, 1.0), ("ms_free", 12.0, 2.0, 0, 1.0),
                              ("ms_free", 12.0, 2.5, 0, 1.0), ("b_lo*ms_free", 12.0, 2.5, 0, 0.83), ("b_hi", 11.9, 2.5, 0, 1.0),
                              ("J1.0", 8.0, 2.0, 10, 0.83), ("b_q*J1.0", 12.5, 2.5, 10, 0.83), ("b_lo*J_hi", 8.0, 2.0, 10, 0.83)):
        pl = M.member(mem, v)
        pl.k *= s2(v, a)
        L = M.loop(D[dn], pl, v, e=e, kappa=kap)[0]
        pm = M.pm_gm(L)[0]
        rho = M.Periodic(D[dn], pl, v, e=e, kappa=kap).rho_ring()
        p = R.member(mem + ("+h10" if e == 10 else ""), v)
        p.k *= s2(v, a)
        m, _ = R.lti_metrics(RD[dn], p, v, kd_scale=kap)
        rr = R.Periodic(RD[dn], p, v, kd_scale=kap).rho_poles()
        P(f"  {dn} {mem}@{v} a{a} e{e} k{kap}: mine PM {pm:.1f} rho {rho[0]:.4f} ({rho[1]:.2f} Hz z {rho[2]:.3f}) |"
          f" c2r2 signed PM {m['pm']:.1f} rho {rr[0]:.4f}")

P("\n(X2) the variants at the same operating points (PM, exact rho)")
for nm, kd in (("C3-Pd", 48), ("C3-P44", 44)):
    dc = M.decode_cave(M.C3D / f"c3_cave_{nm}.hex")
    D[nm] = M.Design(nm, "fresh", kd=kd, rows=tuple(dc["rows"]))
for nm in ("C3-P", "C3-F", "C3-Pd", "C3-P44"):
    row = []
    for mem, v, a, kap in (("ms_free", 12.0, 1.5, 1.0), ("ms_free", 12.0, 2.0, 1.0), ("ms_free", 12.0, 2.5, 1.0),
                           ("b_lo*ms_free", 12.0, 2.5, 0.83), ("J1.0", 10.0, 2.5, 1.0)):
        pl = M.member(mem, v)
        pl.k *= s2(v, a)
        pm = M.pm_gm(M.loop(D[nm], pl, v, e=0, kappa=kap)[0])[0]
        rho = M.Periodic(D[nm], pl, v, e=0, kappa=kap).rho_ring()[0]
        row.append(f"{mem}@{v} a{a} k{kap}: {pm:.1f} ({rho:.4f})")
    P(f"  {nm}: " + "; ".join(row))

P("\n(X3) Ki feasibility probe on C3-P (NOT a design): PM at native ages")
for ki in (56, 40, 28, 20, 14, 8):
    d = dataclasses.replace(D["C3-P"], ki=ki)
    row = []
    for mem, v, a, kap in (("ms_free", 12.0, 2.0, 1.0), ("ms_free", 12.0, 2.5, 1.0), ("b_lo*ms_free", 12.0, 2.5, 0.83),
                           ("ms_free", 12.0, 0.0, 1.0), ("b_q*J1.0", 26.9, 0.0, 0.83)):
        pl = M.member(mem, v)
        pl.k *= s2(v, a)
        row.append(f"{mem}@{v} a{a} k{kap}: {M.pm_gm(M.loop(d, pl, v, e=0, kappa=kap)[0])[0]:.1f}")
    P(f"  Ki {ki}: " + " | ".join(row))
(Path(M.OUT) / "extras_out.txt").write_text("\n".join(out), encoding="utf-8")
