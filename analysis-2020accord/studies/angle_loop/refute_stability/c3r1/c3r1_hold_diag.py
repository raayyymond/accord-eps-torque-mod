# -*- coding: utf-8 -*-
"""c3r1_hold_diag.py -- one curve-hold case on the integer lane, 30 s: per-second theta min/max, I (S), freeze duty,
T range; plus the LINEAR PM / exact pole at the operating point.  python c3r1_hold_diag.py dn mem v a fr [fric]"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_intlane as IL  # noqa: E402
import c3r1_kop as K  # noqa: E402
import c3r1_hold_td as H  # noqa: E402

dn, mem, v, a, fr = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
fric = int(sys.argv[6]) if len(sys.argv) > 6 else 0
pulse = float(sys.argv[7]) if len(sys.argv) > 7 else 120.0
D = M.designs()
kap, jb = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FB.83": (0.83, 1 / 1.155)}[fr]
pl = M.member(mem, v)
th_op = K.theta_op(v, a)
sat = K.sat(v)
s2 = 1 - math.tanh(th_op / sat) ** 2
pk = M.member(mem, v)
pk.k *= s2
L, Sx, Tr, _ = M.loop(D[dn], pk, v, e=0, kappa=kap, jb=jb)
pm, fc, gm = M.pm_gm(L)
rho, f, z, _ = M.Periodic(D[dn], pk, v, e=0, kappa=kap, jb=jb).rho_ring()
print(f"{dn} {mem}@{v} a{a} {fr}: theta_op {th_op:.1f} sat {sat:.1f} k {pl.k:.1f} -> k_eff {pk.k:.2f}; J {pl.J:.2f} b {pl.b:.2f};"
      f" LINEAR PM {pm:.1f} fc {fc:.2f} GM {gm:.1f}; exact rho {rho:.4f} pole {f:.2f} Hz zeta {z:.3f}")
fc_, rs = H.fric_of(mem, v) if fric else (0.0, 1.25)
n = 30000
r = IL.simulate(D[dn], pl, v, n, lambda k: np.full(1, th_op * min(max((k - 200) / 1500.0, 0.0), 1.0)), kappa=kap, jb=jb,
                sat=sat, fric=fc_ * fric, Fs_ratio=rs, d_ext=lambda k: (pulse if 7000 <= k < 7060 else 0.0),
                record=("th", "T", "I", "frozen", "P", "D"))
th, T, I, fz = r["th"][0], r["T"][0], r["I"][0], r["frozen"][0]
for s in list(range(1, 8)) + list(range(8, 30, 2)):
    a_, b_ = s * 1000, (s + 1) * 1000
    print(f"  t {s:2d}-{s + 1:2d}s: theta {th[a_:b_].min():7.2f}..{th[a_:b_].max():7.2f}  I(S) {I[a_:b_].min():6.0f}..{I[a_:b_].max():6.0f}"
          f"  T {T[a_:b_].min():6.0f}..{T[a_:b_].max():6.0f}  frozen {fz[a_:b_].mean():.2f}")
