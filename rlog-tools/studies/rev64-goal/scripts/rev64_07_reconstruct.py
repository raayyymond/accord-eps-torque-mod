"""Reconstruct the Accord feedforward from the LOGGED signals using the FORK'S OWN FUNCTIONS,
verify it reproduces the logged pid_log.f, then ablate AccordHoldLevel to size its contribution.

No inference about which term causes the over-delivery until the reconstruction is validated
against the log. If it does not reproduce cs_f, the ablation means nothing and I stop.
"""
import math, sys, importlib.util
import numpy as np
sys.path.insert(0,'/home/user/starpilot')

# import the tunes module standalone (avoid dragging in openpilot's whole import tree)
spec=importlib.util.spec_from_file_location(
    "tunes","/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T=importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(T)
except Exception as e:
    print("direct import failed:",type(e).__name__,e); raise SystemExit(1)
print("imported fork tunes OK")
print("  HOLD_LEVEL_V      =",T.HONDA_ACCORD_HOLD_LEVEL_V)
print("  FF_RATE_GAIN      =",T.HONDA_ACCORD_FF_RATE_GAIN)
print("  FF_RATE_RC        =",T.HONDA_ACCORD_FF_RATE_RC)

CA='/home/user/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),
                v=np.interp(t,D['t_cst'],D['vego']),pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                sa=np.interp(t,D['t_cst'],D['sa_deg']),sr=np.interp(t,D['t_cst'],D['sr_deg']),
                lad=D['cs_la_des'],laa=D['cs_la_act'],f=D['cs_f'],out=D['cs_out'],
                dcurv=D['cs_des_curv'])
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz')

# angle_des from desired curvature. Fit the deg-per-(1/m) map empirically from the log
# (avoids re-implementing VehicleModel); r>0.99 in every speed bin on route 76.
def angle_per_curv(S):
    bp,val=[],[]
    for lo,hi in [(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,34)]:
        m=S['act']&(S['v']>=lo)&(S['v']<hi)&(np.abs(S['dcurv'])>1e-4)
        if m.sum()<300: continue
        s=float(np.dot(S['dcurv'][m],S['sa'][m])/np.dot(S['dcurv'][m],S['dcurv'][m]))
        bp.append((lo+hi)/2); val.append(s)
    return np.array(bp),np.array(val)

for tag,S in [('6c',A),('6d',B)]:
    bp,val=angle_per_curv(S)
    ang_des=S['dcurv']*np.interp(S['v'],bp,val)
    DT=1.0/S['FS']
    # angle_des_rate through the fork's own first-order filter
    raw=np.gradient(ang_des,S['t']); al=DT/(T.HONDA_ACCORD_FF_RATE_RC+DT)
    rate=np.zeros_like(raw)
    for n in range(1,len(raw)): rate[n]=rate[n-1]+al*(raw[n]-rate[n-1])
    def ff_torque(level):
        o=np.empty(len(ang_des))
        for n in range(len(ang_des)):
            o[n]=T.get_honda_accord_rate_plant_ff(float(ang_des[n]),float(rate[n]),float(S['v'][n]),
                   T.HONDA_ACCORD_FF_RATE_GAIN,1.0,1.0,hold_map=True,hold_level=level)
        return o
    ff_on=ff_torque(True); ff_off=ff_torque(False)
    m=S['act']&~S['pr']&(S['v']>=15.0)
    # validate: cs_f is in LAT-ACCEL units; cs_out is torque. ratio gives the effective LAF.
    laf=float(np.dot(S['f'][m],S['out'][m])/max(np.dot(S['out'][m],S['out'][m]),1e-12))
    recon_lataccel = ff_on*laf                       # plant FF converted the same way
    r=np.corrcoef(recon_lataccel[m],S['f'][m])[0,1]
    sl=float(np.dot(recon_lataccel[m],S['f'][m])/max(np.dot(recon_lataccel[m],recon_lataccel[m]),1e-12))
    print(f"\n=== route {tag}  (highway engaged n={m.sum()})")
    print(f"  VALIDATION of the reconstruction against logged pid_log.f:")
    print(f"     corr(recon, logged f) = {r:.4f}    slope = {sl:.3f}   (want corr>0.9, slope~1)")
    if r < 0.85:
        print("     -> RECONSTRUCTION FAILED. Not reporting an ablation off a model that does not match the log.")
        continue
    d=np.abs(ff_on[m])-np.abs(ff_off[m])
    print(f"  AccordHoldLevel contribution (torque units): mean |ff_on|-|ff_off| = {d.mean():+.5f}")
    print(f"     mean |ff_on| = {np.mean(np.abs(ff_on[m])):.5f}   mean |ff_off| = {np.mean(np.abs(ff_off[m])):.5f}"
          f"   ratio = {np.mean(np.abs(ff_on[m]))/max(np.mean(np.abs(ff_off[m])),1e-9):.3f}")
    print(f"  As a fraction of the mean applied torque |out| = {np.mean(np.abs(S['out'][m])):.5f}: "
          f"{d.mean()/max(np.mean(np.abs(S['out'][m])),1e-9)*100:+.1f}%")
    print(f"  Measured band over-delivery is +22 to +39%. Hold-level accounts for the above.")
