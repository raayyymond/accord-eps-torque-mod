import sys, os
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import v294_plant as VP
rows = VP._profile_rows(os.path.join(os.path.dirname(VP.__file__), "_scratch", "p5c.json"))
for Jr in (0.5, 0.8, 1.3):
    b0, k0, F0, Fs0 = rows[Jr]
    mem = VP.PlantFamilyMember(f"J{Jr}", J=np.full(5, Jr), b=b0, k=k0, Fc=F0, Fs=Fs0, tau_ms=2)
    out = []
    for v in (8, 10, 11, 11.9, 12.5, 14, 16, 19, 22, 26):
        p = mem.at(v); pl = S.rigid(p.J, p.b, p.k); c = S.Ctl(v, d=2)
        mg = S.margins(c, pl, npts=3000); rho, poles = S.exact(c, pl)
        lz = [q for q in poles if 0.5 <= q[0] <= 50]
        out.append(f"{v:g}:{mg['pm']:.1f}({lz[0][0]:.1f}Hz z{lz[0][1]:.2f})" if lz else f"{v:g}:{mg['pm']:.1f}")
    print(f"J-profile refit J {Jr}: b {np.round(b0,2)} k {np.round(k0,1)} | PM by v: " + "  ".join(out))
fam = VP.family()
for v in (11.5, 12.0):
    p = fam["J_hi"].at(v); pl = S.rigid(p.J, p.b/1.8, p.k); c = S.Ctl(v, d=2)
    print(f"b_lo*J_hi v {v}: exact GM {S.exact_gm(c, pl):.1f} dB, rho {S.exact(c, pl)[0]:.4f}")
p = fam["J_hi"].at(11.9); c = S.Ctl(11.9, d=2); pl = S.rigid(p.J, p.b, p.k)
print(f"J_hi v 11.9: own model PM {S.margins(c, pl)['pm']:.1f} exact GM {S.exact_gm(c, pl):.1f} least-damped {S.exact(c, pl)[1][:1]}")
