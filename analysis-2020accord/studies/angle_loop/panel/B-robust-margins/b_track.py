# -*- coding: utf-8 -*-
"""b_track.py -- the GOAL'S OWN tracking metric (c1r2_trackmetric: OLS slope of actual on desired lat accel, 0.5 Hz
filtfilt, weighted by r71b's measured desired-lat-accel spectrum per band) applied to each panel-B implementation's
INNER-LOOP reference transfer T_ref(f) = K*(G/256)*PI*160*Pt/(1+L).  Reports slope_inner per band >= 8 m/s on the key
members, plus the 0.2/0.5 Hz in-phase proxies and group delay.  ANALYSIS ONLY."""
import sys, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parents[1]/'refute_stability', HERE.parents[1]/'c1', HERE.parents[2]/'v295'/'plant'):
    sys.path.insert(0, str(_p))
import b_lib as B
import stab_lin as S
import c1_lib as C
import c1r2_members as M
import c1r2_trackmetric as TM

IMPL = {
 "B1": dict(dmode="held", kd=20, ki=56, ema=None,
            knots=[(3.1,952),(8.0,1321),(10.0,855),(11.9,699),(15.5,1044),(26.9,2041)]),
 "B2": dict(dmode="fresh_ema", kd=24, ki=56, ema=40.0,
            knots=[(3.1,1106),(8.0,1475),(10.0,989),(11.9,826),(15.5,1213),(26.9,2241)]),
 "B3": dict(dmode="held", kd=20, ki=0, ema=None,
            knots=[(3.1,1690),(8.0,1805),(10.0,1357),(11.9,1162),(15.5,1366),(26.9,2765)]),
 "rev2": dict(dmode="held", kd=20, ki=56, ema=None, knots=C.VARIANTS["r2"]["knots"]),
}

def tref_fn(impl, name, v):
    cfg = IMPL[impl]; tbl = C.make_table(cfg["knots"])
    J,b,k,tau,ea = M.params(name, v); pl = S.rigid(J,b,k)
    c = B.ctl_at(v, tbl, 112, cfg["ki"], cfg["kd"], d=tau, extra_age=ea, G=C.G_at(v,tbl))
    def T(f):
        L, KCth, KCw, Pt, Pw = B.frf(c, pl, f, dmode=cfg["dmode"], ema_hz=cfg["ema"])
        z = np.exp(1j*2*np.pi*f*S.TS); zi=1/z
        Hout=(S.OB/1024)*(1+zi)/(32*(1-(S.OA/1024)*zi))
        K=c.fade*S.FWD*Hout*zi**c.d
        PI=c.kp/256+(c.ki/32768)/(1-zi)
        return K*(c.G/256)*PI*160*Pt/(1+L)
    return T

def proxies(impl, name, v):
    T = tref_fn(impl, name, v)
    f02, f05 = np.array([0.2]), np.array([0.5])
    t02 = T(f02)[0]; t05 = T(f05)[0]
    # group delay at 0.2 Hz
    df=1e-3; ph=lambda f: np.angle(T(np.array([f]))[0])
    gd02 = -(ph(0.2+df)-ph(0.2-df))/(2*df)/(2*np.pi)
    return t02.real, t05.real, abs(t02), gd02*1000.0

def main():
    print("# inner-loop tracking factor = the goal metric's slope with the fork/vehicle factor perfect (c1r2_trackmetric)")
    members = ("nominal","b_lo","J_hi","J1.0","b_q","b_q*J_hi","b_q*J1.0","b_lo*J_hi")
    for impl in ("B1","B2","B3","rev2"):
        print(f"\n== {impl} ==  band tracking slope_inner (>=8 m/s) on key members | nominal 0.2/0.5Hz inphase, |T(0.2)|, gd(0.2)ms")
        print(f"  {'v':>5s} | " + " ".join(f"{m[:9]:>9s}" for m in members) + " | prox tg02/tg05 |T02| gd02ms")
        for v in (8,11.9,12.5,15,17,19,22,26,30):
            cells=[]
            for m in members:
                try: cells.append(f"{TM.slope(tref_fn(impl,m,v), v):9.3f}")
                except Exception: cells.append(f"{'--':>9s}")
            t02r,t05r,at02,gd=proxies(impl,"nominal",v)
            print(f"  {v:5.1f} | " + " ".join(cells) + f" | {t02r:5.2f}/{t05r:5.2f} {at02:5.2f} {gd:5.0f}")

if __name__=="__main__":
    main()
