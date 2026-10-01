# REFUTER: disturbance-driven nonlinear runs (15-count white road torque noise, the ident's own G3a control level,
# plus a +-0.5 deg 0.2 Hz lane-keeping setpoint).  Band rms of T and of the wheel rate; pole-band ratio vs nominal.
import sys, math
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_nl as N
import v294_plant as VP
fam = VP.family()
rng = np.random.default_rng(3)
secs = 20.0
noise = rng.normal(0, 15.0, int(secs * 1000))
sp = lambda t: 0.5 * math.sin(2 * math.pi * 0.2 * t)
def go(lab, J, b, k, Fc, Fs, v, sat):
    TH, T, OM = N.run(J, b, k, Fc, Fs, v, sp, secs=secs, sat=sat, d_noise=noise)
    s = slice(4000, None)
    print(f"  {lab:28s} v {v:5.1f}: T rms 1.6-3 {N.band_rms(T[s],1.6,3):6.1f} | 3-6 {N.band_rms(T[s],3,6):6.1f} | 5-30 {N.band_rms(T[s],5,30):6.1f}"
          f" || rate rms 1.6-3 {N.band_rms(OM[s],1.6,3):6.2f} | 3-6 {N.band_rms(OM[s],3,6):6.2f} deg/s | track err rms {np.std(TH[s]-np.array([sp(i*1e-3) for i in range(4000,int(secs*1000))])):.3f} deg")
print("C. 12 m/s band (the J_hi trough)")
for v in (11.9,):
    p = fam["nominal"].at(v); go("nominal", p.J, p.b, p.k, p.Fc, p.Fs, v, p.sat)
    p = fam["J_hi"].at(v); go("J_hi", p.J, p.b, p.k, p.Fc, p.Fs, v, p.sat)
    go("J_hi*b/1.8", p.J, p.b/1.8, p.k, p.Fc, p.Fs, v, p.sat)
    p = fam["J_hi2"].at(v); go("J_hi2", p.J, p.b, p.k, p.Fc, p.Fs, v, p.sat)
    p = fam["ms_free"].at(v); go("ms_free (J 2.08)", p.J, p.b, p.k, p.Fc, p.Fs, v, p.sat)
print("D. highway, b at the crossover band reduced (J 0.2, nominal k, friction)")
for v in (26.0, 30.0):
    p = fam["nominal"].at(v)
    for b, lab in ((p.b, "nominal b"), (p.b/1.8, "b_lo"), (9.5, "b 9.5 (PM~30)"), (7.0, "b 7"), (5.0, "b 5 (mech)")):
        go(lab, p.J, b, p.k, p.Fc, p.Fs, v, p.sat)
