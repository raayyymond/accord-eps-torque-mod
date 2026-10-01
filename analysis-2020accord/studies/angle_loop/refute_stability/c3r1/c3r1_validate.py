# -*- coding: utf-8 -*-
"""c3r1_validate.py -- positive controls for my independent model against PUBLISHED anchors (not their code).
python c3r1_validate.py  -> _scratch/angle_loop/refute-c3r1-stability/validate_out.txt"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402

D = M.designs()
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))  # noqa: E731

for nm in ("C3-P", "C3-F"):
    dc = M.decode_cave(M.C3D / f"c3_cave_{nm}.hex")
    P(nm, "cave", dc["n"], "B sha", dc["sha"], "table @", hex(dc["tbl"]), "rows", dc["rows"])
    P("   movea imms", dc["movea"], " addi imms", dc["addi"], " shl", dc["shl"], " sar", dc["sar"])
    P("   G at 3.1/8/10/11.75/12.5/15/17.5/26.9:", [D[nm].G(v) for v in (3.1, 8.0, 10.0, 11.75, 12.5, 15.0, 17.5, 26.9)])

FQ = [5, 7, 10, 13, 16, 20, 25]
pub = {("V295", 0): [2.46, 1.24, 0.09, -0.47, -0.73, -0.82, -0.76], ("V294", 0): [1.33, 0.67, 0.05, -0.25, -0.39, -0.44, -0.41],
       ("V295", 10): [1.69, 0.08, -1.17, -1.50, -1.36, -0.89, -0.25],
       ("C3-P", 0): [-0.05, -0.16, -0.30, -0.37, -0.41, -0.43, -0.42], ("C3-F", 0): [-0.53, -0.70, -0.86, -0.91, -0.89, -0.80, -0.65],
       ("C3-P", 10): [-0.23, -0.14, -0.13, -0.15, -0.18, -0.29, -0.35], ("C3-F", 10): [-1.49, -1.65, -1.64, -1.40, -1.06, -0.63, -0.13]}
SP = np.arange(1.0, 35.01, 0.25)
P("\nRe(T/w) worst over 1-35 m/s, kappa 1, 2 ms (mine vs published)")
mx = 0
for (nm, e), ref in pub.items():
    vals = np.min([M.retw(D[nm], v, FQ, e=e) for v in SP], axis=0)
    mx = max(mx, float(np.max(np.abs(vals - np.array(ref)))))
    P(f"  {nm:5s} e{e:<3d}", " ".join(f"{x:+.2f}" for x in vals), " | pub", " ".join(f"{x:+.2f}" for x in ref))
P(f"  max |diff| = {mx:.3f}")

S_C = 1.155
cases = [("C3-P", "nominal", None, 0, 1.0, 1.0, "nominal min over speed", 69.2),
         ("C3-P", "J_hi", 1.00, 0, 0.83, 1.0, "J_hi@1 FA.83", 51.7),
         ("C3-P", "J_hi", 1.00, 10, 0.83, 1.0, "J_hi+h10@1 FA.83", 47.1),
         ("C3-P", "b_q*J1.0", 26.9, 10, 0.83, 1 / S_C, "b_q*J1.0+h10@26.9 FB.83", 34.2),
         ("C3-P", "b_lo*ms_free", 9.0, 10, 0.83, 1.0, "b_lo*ms_free+h10@9 FA.83", 35.4),
         ("C3-P", "b_q*ms_free", 15.75, 10, 0.83, 1.0, "b_q*ms_free+h10@15.75 FA.83", 36.6),
         ("C3-F", "nominal", None, 0, 1.0, 1.0, "nominal min over speed", 68.6),
         ("C3-F", "J_hi", 1.00, 0, 0.83, 1.0, "J_hi@1 FA.83", 50.7),
         ("C3-F", "b_q*J1.0", 27.0, 10, 0.83, 1 / S_C, "b_q*J1.0+h10@27 FB.83", 34.8),
         ("C3-F", "b_lo*ms_free", 8.75, 10, 0.83, 1 / S_C, "b_lo*ms_free+h10@8.75 FB.83", 35.8),
         ("C3-F", "b_q*ms_free", 15.75, 10, 0.83, 1 / S_C, "b_q*ms_free+h10@15.75 FB.83", 36.9)]
P("\nPM anchors (LTI averaged hold; exact periodic rho/ring/GM/DM at the same point)")
for nm, mem, v, e, kap, jb, lab, ref in cases:
    if v is None:
        pms = [(M.metrics(D[nm], M.member(mem, vv), vv, e=e, kappa=kap, jb=jb)["PM"], vv) for vv in SP]
        pm, v = min(pms)
        P(f"  {nm} {lab:32s} mine {pm:5.1f} @{v} | pub {ref}")
        continue
    m = M.metrics(D[nm], M.member(mem, v), v, e=e, kappa=kap, jb=jb)
    pl = M.member(mem, v)
    per = M.Periodic(D[nm], pl, v, e=e, kappa=kap, jb=jb)
    rho, fr, zr, _ = per.rho_ring()
    dm = M.exact_dm(D[nm], pl, v, e=e, kappa=kap, jb=jb)
    pm_dm = dm * 1e-3 * m["fc"] * 360
    P(f"  {nm} {lab:32s} mine PM {m['PM']:5.1f} fc {m['fc']:.2f} GM {m['GMu']:.1f} | exact rho {rho:.4f} ring {fr:.2f} Hz "
      f"z {zr:.3f} DM {dm:.2f} ms (= {pm_dm:.1f} deg at fc) | pub {ref}")

(Path(M.OUT) / "validate_out.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
