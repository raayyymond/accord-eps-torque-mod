# REFUTER: what G (Kp_eff) the flagged points would tolerate; b thresholds at a lower highway gain.
import sys, math
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import v294_plant as VP
fam = VP.family()
def pm(v, pl, G, kd=16):
    return S.margins(S.Ctl(v, d=2, G=G, kd=kd), pl, npts=3000)['pm']
print("max G (Kp_eff) keeping PM >= 45 on J_hi, and PM >= 30 / 45 on J_hi*b/1.8, at the trough speeds")
for v in (10.5, 11.0, 11.5, 11.9, 12.5):
    p = fam["J_hi"].at(v)
    pj = S.rigid(p.J, p.b, p.k); pjb = S.rigid(p.J, p.b/1.8, p.k)
    out = [f"v {v:5.1f} C0 G {S.G_of_v(v)} (Kp_eff {450*S.G_of_v(v)/256:.0f})"]
    for lab, pl, tg in (("J_hi PM45", pj, 45), ("J_hi*b/1.8 PM30", pjb, 30), ("J_hi*b/1.8 PM45", pjb, 45)):
        best = None
        for G in range(120, 1200, 4):
            if pm(v, pl, G) >= tg: best = G
            else: break
        out.append(f"{lab}: G<={best} (Kp_eff {450*best/256 if best else float('nan'):.0f})")
    print("  " + " | ".join(out))
print("\nhighway: b-scale threshold for PM 0/30/45 at reduced highway gains (J 0.2, nominal k)")
for v in (26.0,):
    p = fam["nominal"].at(v)
    for Kpe in (3000, 2500, 2000, 1500):
        G = Kpe*256/450
        row = [f"v {v} Kp_eff {Kpe}"]
        for tg in (0, 30, 45):
            lo, hi = 0.02, 1.0
            def ok(x):
                pl = S.rigid(p.J, p.b*x, p.k); c = S.Ctl(v, d=2, G=G)
                if tg == 0:
                    return S.exact(c, pl)[0] < 1
                return S.margins(c, pl, npts=3000)['pm'] >= tg
            if not ok(hi): row.append(f"PM{tg}: >1"); continue
            for _ in range(25):
                m = 0.5*(lo+hi)
                if ok(m): hi = m
                else: lo = m
            row.append(f"PM{tg}: b>={p.b*hi:.2f} ({hi:.2f}x)")
        print("  " + " | ".join(row))
