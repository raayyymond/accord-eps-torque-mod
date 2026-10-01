# Cross-check ONLY (second method on the crux): the design's own harness_freq on the speeds my grid flagged.
import sys, os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
sys.path.insert(0, r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/angle_loop/refute-stability")
import harness_freq as HF
import stab_lin as S
from dataclasses import replace
for nm in ("J_hi", "nominal", "b_lo"):
    for v in (9.0, 10.0, 10.25, 10.5, 11.0, 11.5, 11.9, 12.0, 12.5, 13.0):
        G = S.G_of_v(v); kp = 450*G/256; ki = 199*G/256
        c = HF.Ctl(kp=kp, ki=ki, kd=16)
        r = HF.metrics(c, HF.plant_at(nm, v), exact=True)
        print(f"{nm:8s} v {v:6.2f} G {G} Kp_eff {kp:7.1f} | HF: fc {r['fc']:.2f} PM {r['pm']:5.1f} GMlti {r['gm_lti_db']:.1f} stable {r['stable']} wheel {r['wheel'][0]:.2f}Hz z{r['wheel'][1]:.2f}")
# combined corner, built as an HF Plant directly
import v294_plant as VP
fam = VP.family()
for v in (10.0, 11.0, 11.5, 12.0, 13.0, 15.0, 19.0, 22.0):
    p = fam["J_hi"].at(v); bs = 1/1.8 if v >= 10 else 0.7
    pl = HF.Plant(J=p.J, b=p.b*bs, k=p.k, tau=2, name="bloJhi")
    G = S.G_of_v(v); kp = 450*G/256; ki = 199*G/256
    r = HF.metrics(HF.Ctl(kp=kp, ki=ki, kd=16), pl, exact=True)
    print(f"b_lo*J_hi v {v:5.1f}: HF fc {r['fc']:.2f} PM {r['pm']:5.1f} stable {r['stable']} wheel {r['wheel'][0]:.2f}Hz z{r['wheel'][1]:.2f} Tr1.6-3 {r.get('Tr163',float('nan')):.2f}")
