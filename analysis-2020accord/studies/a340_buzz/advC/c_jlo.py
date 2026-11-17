import math,numpy as np
from c_pert import G,HF,F_da,FH,HTBH,AUTH,ROWS_S
ROWS3=[-29490,-17202,-16000]
def jl(v,rows,scale): return abs(float(np.interp(v*3.6*64.0,G.DA_X,rows)))*G.DA_SCALE*64.0*G.KAPPA_M*1e-3*scale
F=G.F
HTB=G.htb_model(F,G.fit_two_mass(*G.measure_htb()[:3]))
for sc in (0.25,0.5,0.7,1.0,2.0):
    v=3.0; p=HF.plant_at('J_lo',v); 
    Jmech=p.J-jl(v,ROWS3,sc)
    c=G.ctl_v299(v); Fr=G.F_r24(F,v,G.r24_gain_stock(v)-2.0,-1.0,HTB)
    P=p.frf(F); F3=F_da(F,v,ROWS3,14,0,sc)
    Pc=P/(1-P*(F_da(F,v,ROWS_S,22,0,sc)-F3+Fr))
    r=G.loop_metrics(c,Pc*AUTH,F)
    print(f'lane scale x{sc}: J_lo total {p.J:.3f}, x3-lane inertia {jl(v,ROWS3,sc):.4f} => mech J {Jmech:+.4f} ({"ADMISSIBLE" if Jmech>0 else "negative"}) ; REV4 doc-form J_lo 3 m/s: GM {r["gm_db"]:.1f} dB T {r["T530_db"]:+.1f} dB PM {r["pm"]:.0f}')
