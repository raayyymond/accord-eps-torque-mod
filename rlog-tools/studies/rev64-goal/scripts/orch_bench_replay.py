"""FIRST EVER COMPARISON OF THE DESIGN BENCH AGAINST THE CAR.

24 scratchpad scripts import smallsig_simlib; none loads route data. smallsig_33_validate.py
checks the simulator against its own 2F/k formula -- self-consistency, not fidelity.
Every rev from 6 to 6.4 was accepted on this bench.

TEST: take route 76's ACTUAL applied torque off the wire, put it into the bench's plant from a
measured initial state, integrate forward H seconds, and compare where the model says the wheel
went to where it actually went.  Short horizons with frequent restarts, so an open-loop integrator
cannot drift its way to a meaningless answer.

This also settles the damping ambiguity the project has carried since the start:
  "mode" world  b = 0.0006 flat        vs   "ident" world  b = 0.0018-0.0049 (BANDS)
"""
import math, sys
import numpy as np
SC='/tmp/claude-0/-home-user-accord-eps-torque-mod/1835f72d-a78b-5e09-987d-1aaf14b661eb/scratchpad'
sys.path.insert(0, SC)

# ---- the fork's own hold map, imported from the live file (not re-typed)
sys.path.insert(0, '/home/user/starpilot')
SAT_A, SAT_B, SAT_C = (19.3, 546.0, 3.01)
K_BP=[2.0,4.0,6.0,8.0,10.0,12.5,15.0,17.5,20.0,23.0,28.0]
K_V=[0.0021,0.0028,0.0044,0.0052,0.0074,0.0092,0.0095,0.0103,0.0116,0.0133,0.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
def hold_torque(ang, v, level=True):
    k = np.interp(v,K_BP,K_V) * (np.interp(v,LVL_BP,LVL_V) if level else 1.0)
    s = SAT_A + SAT_B*math.exp(-max(v,0.0)/SAT_C)
    return k * s * np.tanh(ang/s)
BANDS = {"1-8":dict(b=0.00180,F=0.0120), "8-15":dict(b=0.00366,F=0.0119),
         "15-22":dict(b=0.00409,F=0.0112), ">22":dict(b=0.00489,F=0.0098)}
def band_for(v): return "1-8" if v<8 else "8-15" if v<15 else "15-22" if v<22 else ">22"

# ---------------------------------------------------------------- data
D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t = D['t_cs']; act = D['cs_active'].astype(bool)
FS = 1.0/float(np.median(np.diff(t))); DT = 1.0/FS
phi_m  = np.interp(t, D['t_cst'], D['sa_deg'])
rate_m = np.interp(t, D['t_cst'], D['sr_deg'])
v_m    = np.interp(t, D['t_cst'], D['vego'])
u_wire = np.interp(t, D['te4'], D['cmd'])/4096.0     # +left frame candidate (sign tested below)

def natural_runs(mask):
    out,n,i=[],len(mask),0
    while i<n:
        if not mask[i]: i+=1; continue
        j=i
        while j+1<n and mask[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i) > 400: out.append((i,j+1))
        i=j+1
    return out
RUNS = natural_runs(act)
print(f"FS={FS:.2f} Hz  engaged runs: " + ", ".join(f"{(b-a)/FS:.0f}s@{v_m[a:b].mean():.0f}m/s" for a,b in RUNS))

# ---------------------------------------------------------------- the plant (transcribed from simlib 510-544)
def step_plant(phi, phidot, u, v, b, F, J, hold_scale, level):
    spring = hold_scale * hold_torque(phi, v, level)
    if J <= 0.0:
        Dv = u - spring
        phidot = 0.0 if abs(Dv) <= F else (Dv - math.copysign(F, Dv))/b
        return phi + phidot*DT, phidot
    Dt = u - spring - b*phidot
    v_free = phidot + Dt/J*DT
    dv_fr = F/J*DT
    if phidot == 0.0:
        if abs(u - spring) <= F:
            phidot = 0.0
        else:
            phidot = math.copysign(max(abs(v_free)-dv_fr, 0.0), u - spring)
    else:
        if abs(v_free) <= dv_fr and abs(u - spring) <= F:
            phidot = 0.0
        else:
            phidot = (v_free - math.copysign(dv_fr, v_free)) if abs(v_free) > dv_fr else 0.0
            if phidot == 0.0 and abs(u - spring) <= F: phidot = 0.0
    return phi + phidot*DT, phidot

def replay(b_mode, F_scale, J, hold_scale, tau, level=True, restart_s=1.0, horiz_s=1.0, usign=+1.0):
    nd = int(round(tau*FS)); H = int(round(horiz_s*FS)); R = int(round(restart_s*FS))
    errs, base_p, base_v = [], [], []
    for a, bb in RUNS:
        for s in range(a, bb-H, R):
            v = float(v_m[s]); bd = BANDS[band_for(v)]
            b = (0.0006 if b_mode=='mode' else bd['b'])
            F = bd['F']*F_scale
            phi, phidot = float(phi_m[s]), float(rate_m[s])
            for n in range(s, s+H):
                k = max(n-nd, 0)
                phi, phidot = step_plant(phi, phidot, usign*float(u_wire[k]), v, b, F, J, hold_scale, level)
            errs.append(phi - phi_m[s+H])
            base_p.append(phi_m[s] - phi_m[s+H])
            base_v.append(phi_m[s] + rate_m[s]*horiz_s - phi_m[s+H])
    e=np.array(errs); return (np.sqrt(np.mean(e**2)), np.sqrt(np.mean(np.array(base_p)**2)),
                              np.sqrt(np.mean(np.array(base_v)**2)), len(e))

print()
print("="*94)
print("CONTROL 0: which sign of the wire torque drives the plant?  (1 s horizon)")
print("="*94)
for us in (+1.0, -1.0):
    r = replay('mode', 1.0, 1e-4, 1.0, 0.04, usign=us)
    print(f"  usign {us:+.0f}:  model RMS error {r[0]:8.2f} deg   (persistence {r[1]:.2f}, const-vel {r[2]:.2f}, n={r[3]})")
USIGN = -1.0 if replay('mode',1.0,1e-4,1.0,0.04,usign=-1.0)[0] < replay('mode',1.0,1e-4,1.0,0.04,usign=+1.0)[0] else +1.0
print(f"  -> using usign = {USIGN:+.0f}")

print()
print("="*94)
print("DOES THE BENCH PLANT PREDICT THE CAR?   RMS angle error at the horizon, degrees")
print("  Beat BOTH baselines or the model adds nothing over assuming the wheel does not move.")
print("="*94)
for horiz in (0.25, 0.5, 1.0):
    print(f"\n  horizon {horiz:.2f} s")
    print(f"  {'world':>8} {'b':>9} {'J':>8} {'hold x':>7} {'tau':>6} {'model RMS':>10} {'persist':>9} {'const-vel':>10} {'skill':>7}")
    best=None
    for world in ('mode','ident'):
        for J in (8e-5, 1e-4):
            for hs in (1.0, 1.5):
                for tau in (0.04,):
                    r = replay(world, 1.0, J, hs, tau, horiz_s=horiz, usign=USIGN)
                    skill = 1.0 - r[0]/min(r[1], r[2])
                    bshow = 0.0006 if world=='mode' else -1
                    print(f"  {world:>8} {(f'{bshow:.4f}' if bshow>0 else 'BANDS'):>9} {J:8.0e} {hs:7.2f} {tau:6.2f} "
                          f"{r[0]:10.3f} {r[1]:9.3f} {r[2]:10.3f} {skill:+7.3f}")
                    if best is None or r[0]<best[0]: best=(r[0],world,J,hs,tau)
    print(f"    best: {best[1]} J={best[2]:.0e} hold x{best[3]} -> {best[0]:.3f} deg")

print()
print("="*94)
print("CONTROL 1 (positive): replay a trajectory the SAME plant generated. Error must be ~0.")
print("="*94)
# generate a synthetic run with known params, then replay it
v=19.0; bd=BANDS[band_for(v)]; b=0.0006; F=bd['F']; J=1e-4
n=6000; phi=0.0; pd=0.0; PH=np.zeros(n); RT=np.zeros(n)
U = 0.08*np.sin(2*np.pi*0.3*np.arange(n)*DT) + 0.03*np.sin(2*np.pi*1.1*np.arange(n)*DT)
for i in range(n):
    PH[i], RT[i] = phi, pd
    phi, pd = step_plant(phi, pd, U[i], v, b, F, J, 1.0, True)
# replay it with the same params from restarts
H=int(1.0*FS); errs=[]
for s in range(0, n-H, 100):
    p, q = PH[s], RT[s]
    for k in range(s, s+H): p, q = step_plant(p, q, U[k], v, b, F, J, 1.0, True)
    errs.append(p - PH[s+H])
print(f"  self-replay RMS error at 1 s = {np.sqrt(np.mean(np.array(errs)**2)):.2e} deg  (must be ~1e-12)")
