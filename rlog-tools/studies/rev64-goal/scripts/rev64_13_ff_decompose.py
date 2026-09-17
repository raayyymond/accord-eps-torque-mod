"""The over-delivery is 91-99% feedforward. WHICH PART OF THE FEEDFORWARD?

From latcontrol_torque.py the Accord path is exactly:
    plant_ff_torque = -(hold + move)
    inner_torque    = -(friction_z + rate_loop) - dob
    ff_torque       = plant_ff_torque + inner_torque      (friction_torque == 0 since hyst > 0)
    cs_f            = ff_torque * LAF                     (LAF = 14, confirmed: out = -(p+i+f)/14)

hold, move, friction_z and rate_loop are ALL computable from logged signals using the fork's own
functions. The observer is then recoverable as the RESIDUAL, and validated against its own clip
(HONDA_ACCORD_DOB_MAX_TORQUE = 0.3).
"""
import math, sys, importlib.util
import numpy as np
from scipy import signal
sys.path.insert(0, "/home/user/starpilot")
spec = importlib.util.spec_from_file_location(
    "tunes", "/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
LAF = 14.0
FLOWN = dict(rate_gain=0.5, hyst=0.015, rateloop=0.001, ref=0.06)

CA='analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']; v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
                pr=np.interp(t,D['t_cst'],D['spress'])>0.5,sa=np.interp(t,D['t_cst'],D['sa_deg']),
                sr=np.interp(t,D['t_cst'],D['sr_deg']),curv=D['cs_curv'],dcurv=D['cs_des_curv'],
                out=D['cs_out'],p=D['cs_p'],i=D['cs_i'],f=D['cs_f'])
R={'6c':load('r6c_rev64_ident.npz'),'6d':load('r6d_rev64_ident.npz')}
FS=R['6c']['FS']; DT=1.0/FS

def components(S):
    m=S['act']&~S['pr']&(np.abs(S['curv'])>1e-5)
    k=float(np.dot(S['curv'][m],S['sa'][m])/np.dot(S['curv'][m],S['curv'][m]))
    ad=S['dcurv']*k
    n=len(ad)
    # angle_des_rate through the fork's FirstOrderFilter(FF_RATE_RC)
    raw=np.concatenate([[0.0],np.diff(ad)])/DT
    a1=DT/(T.HONDA_ACCORD_FF_RATE_RC+DT); adr=np.zeros(n)
    for j in range(1,n): adr[j]=adr[j-1]+a1*(raw[j]-adr[j-1])
    # measured rate through FirstOrderFilter(RATE_LOOP_RC)
    a2=DT/(T.HONDA_ACCORD_RATE_LOOP_RC+DT); rm=np.zeros(n); rm[0]=S['sr'][0]
    for j in range(1,n): rm[j]=rm[j-1]+a2*(S['sr'][j]-rm[j-1])
    hold=np.empty(n); move=np.empty(n); z=np.zeros(n); rl=np.empty(n)
    zz=0.0
    for j in range(n):
        v=float(S['v'][j])
        hold[j]=T.get_honda_accord_hold_torque(float(ad[j]),v,level=True)
        G=float(np.interp(v,T.HONDA_ACCORD_EPS_G_BP,T.HONDA_ACCORD_EPS_G_V))
        lim=T.get_honda_accord_ff_move_torque_limit(v)
        move[j]=float(np.clip(FLOWN['rate_gain']*adr[j]/G,-lim,lim))
        band=T.get_honda_accord_friction_hyst_band(v,True)
        zz=T.honda_accord_friction_hysteresis(zz,float(ad[j]-(ad[j-1] if j else ad[0])),FLOWN['hyst'],band)
        z[j]=zz
        rl[j]=T.get_honda_accord_rate_loop_gain(v,FLOWN['rateloop'])*(adr[j]-rm[j])
    ff_torque=S['f']/LAF
    dob = -(ff_torque + hold + move + z + rl)      # residual
    return dict(ad=ad,hold=hold,move=move,z=z,rl=rl,dob=dob,ff=ff_torque)

print("="*100)
print("VALIDATION: is the residual (attributed to the observer) inside its own clip of 0.3?")
print("="*100)
C={}
for tag,S in R.items():
    c=components(S); C[tag]=c
    m=S['act']&~S['pr']&(S['v']>=15)
    d=c['dob'][m]
    print(f"   {tag}: |residual| p50={np.percentile(np.abs(d),50):.4f} p99={np.percentile(np.abs(d),99):.4f} "
          f"max={np.abs(d).max():.4f}   frames over the 0.3 clip: {(np.abs(d)>0.3).mean()*100:.2f}%"
          f"   {'PLAUSIBLE' if np.percentile(np.abs(d),99)<0.35 else 'IMPLAUSIBLE -- decomposition suspect'}")

def runs(S,vlo,ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo); out=[]; n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((i,j+1))
        i=j+1
    return out

print()
print("="*100)
print("IN-PHASE SHARE OF THE BAND-LIMITED FEEDFORWARD, BY TERM  (shares of ff_torque, sum to 1.000)")
print("="*100)
for name,f1,f2,meas in [('0.15-0.30 Hz',0.15,0.30,1.275),('0.30-0.60 Hz',0.30,0.60,1.333)]:
    sos=signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
    acc={k:0.0 for k in ('hold','move','z','rl','dob','den')}; secs=0.0
    for tag,S in R.items():
        c=C[tag]
        for a,b in runs(S,15.0,30.0):
            e=int(3.0*FS)
            tot=signal.sosfiltfilt(sos,c['ff'][a:b])[e:-e]
            if len(tot)<50: continue
            for key,sig in (('hold',-c['hold'][a:b]),('move',-c['move'][a:b]),
                            ('z',-c['z'][a:b]),('rl',-c['rl'][a:b]),('dob',-c['dob'][a:b])):
                acc[key]+=float(np.dot(signal.sosfiltfilt(sos,sig)[e:-e],tot))
            acc['den']+=float(np.dot(tot,tot)); secs+=len(tot)/FS
    print(f"\n  {name}  ({secs:.0f} s)   measured over-delivery {meas:.3f}; command must fall {(1-1/meas)*100:.1f}%")
    tot_share=0.0
    for key,lbl,knob in (('hold','hold term','AccordHoldLevel scales it x1.45'),
                         ('move','move term','AccordFFRateGain 0.5'),
                         ('z','friction hysteresis','AccordFrictionHyst 0.015'),
                         ('rl','100 Hz rate loop','AccordRateLoopGain 0.001'),
                         ('dob','observer (residual)','AccordDobHz 0.6')):
        s=acc[key]/acc['den']; tot_share+=s
        need=(1-1/meas)/s*100 if s>0.02 else float('inf')
        flag='' if need<=100 else '  (too small to fix alone)'
        print(f"     {lbl:22s} {s:+.3f}   needs {need:7.1f}% cut{flag}    [{knob}]")
    print(f"     {'-- sum (must be 1.000)':22s} {tot_share:+.3f}")
