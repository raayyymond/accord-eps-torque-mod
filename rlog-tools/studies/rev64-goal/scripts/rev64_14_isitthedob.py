"""The residual carries 59-62% of the band-limited feedforward. I called it "the observer" -- but a
residual is everything I did not model, so that is an attribution I have not earned.

EARN IT: run the fork's ACTUAL HondaAccordDisturbanceObserver class on the logged signals and
compare its output to my residual. If they match, the attribution is exact, not inferred.
"""
import math, sys, importlib.util
import numpy as np
from scipy import signal
sys.path.insert(0,"/home/user/starpilot")
spec=importlib.util.spec_from_file_location("tunes","/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T=importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
LAF=14.0
CA='analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']; v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
        pr=np.interp(t,D['t_cst'],D['spress'])>0.5,sa=np.interp(t,D['t_cst'],D['sa_deg']),
        sr=np.interp(t,D['t_cst'],D['sr_deg']),off=np.interp(t,D['t_cst'],D['sa_off']),
        curv=D['cs_curv'],dcurv=D['cs_des_curv'],out=D['cs_out'],f=D['cs_f'],sat=D['cs_sat'])
R={'6c':load('r6c_rev64_ident.npz'),'6d':load('r6d_rev64_ident.npz')}
FS=R['6c']['FS']; DT=1.0/FS
FLOWN=dict(rate_gain=0.5,hyst=0.015,rateloop=0.001,dob_hz=0.6)

def run_real_dob(S):
    """Drive the fork's own observer class with the logged signals, exactly as update() does."""
    dob=T.HondaAccordDisturbanceObserver(DT)
    dob.reset(float(S['sr'][0]))
    n=len(S['t']); out=np.zeros(n)
    hold_fn=T.get_honda_accord_hold_torque
    prev=0.0
    for j in range(n):
        if not S['act'][j]:
            dob.reset(float(S['sr'][j])); prev=0.0; out[j]=0.0; continue
        out[j]=prev
        # latcontrol_torque.py: dob.update(CS.steeringAngleDeg - angleOffsetDeg, CS.steeringRateDeg,
        #                                  v, output_torque, dob_hz, hold_fn, hold_map, ..., freeze)
        prev=dob.update(float(S['sa'][j]-S['off'][j]), float(S['sr'][j]), float(S['v'][j]),
                        float(-S['out'][j]), FLOWN['dob_hz'], hold_fn, hold_map=True,
                        gain_scale=1.0, spring_scale=1.0,
                        freeze=bool(S['pr'][j] or S['sat'][j]>0.5))
    return out

def my_residual(S):
    m=S['act']&~S['pr']&(np.abs(S['curv'])>1e-5)
    k=float(np.dot(S['curv'][m],S['sa'][m])/np.dot(S['curv'][m],S['curv'][m]))
    ad=S['dcurv']*k; n=len(ad)
    raw=np.concatenate([[0.0],np.diff(ad)])/DT
    a1=DT/(T.HONDA_ACCORD_FF_RATE_RC+DT); adr=np.zeros(n)
    for j in range(1,n): adr[j]=adr[j-1]+a1*(raw[j]-adr[j-1])
    a2=DT/(T.HONDA_ACCORD_RATE_LOOP_RC+DT); rm=np.zeros(n); rm[0]=S['sr'][0]
    for j in range(1,n): rm[j]=rm[j-1]+a2*(S['sr'][j]-rm[j-1])
    hold=np.empty(n);move=np.empty(n);z=np.zeros(n);rl=np.empty(n);zz=0.0
    for j in range(n):
        v=float(S['v'][j])
        hold[j]=T.get_honda_accord_hold_torque(float(ad[j]),v,level=True)
        G=float(np.interp(v,T.HONDA_ACCORD_EPS_G_BP,T.HONDA_ACCORD_EPS_G_V))
        move[j]=float(np.clip(FLOWN['rate_gain']*adr[j]/G,-T.get_honda_accord_ff_move_torque_limit(v),
                              T.get_honda_accord_ff_move_torque_limit(v)))
        zz=T.honda_accord_friction_hysteresis(zz,float(ad[j]-(ad[j-1] if j else ad[0])),FLOWN['hyst'],
                                              T.get_honda_accord_friction_hyst_band(v,True))
        z[j]=zz
        rl[j]=T.get_honda_accord_rate_loop_gain(v,FLOWN['rateloop'])*(adr[j]-rm[j])
    return -(S['f']/LAF + hold + move + z + rl)

print("="*100)
print("IS THE RESIDUAL THE OBSERVER?  fork's own HondaAccordDisturbanceObserver vs my residual")
print("="*100)
for tag,S in R.items():
    real=run_real_dob(S); res=my_residual(S)
    m=S['act']&~S['pr']&(S['v']>=15)
    r=float(np.corrcoef(real[m],res[m])[0,1])
    sl=float(np.dot(real[m],res[m])/max(np.dot(real[m],real[m]),1e-12))
    print(f"   {tag}: corr = {r:+.4f}   slope(residual/dob) = {sl:.3f}   "
          f"rms dob {np.std(real[m]):.4f}  rms residual {np.std(res[m]):.4f}")
    print(f"        -> {'ATTRIBUTION CONFIRMED: the residual IS the observer' if r>0.8 else ('partial -- the observer explains some of it' if r>0.5 else 'NOT the observer -- residual is something else')}")

print()
print("="*100)
print("THE OBSERVER'S OWN IN-PHASE SHARE OF THE BAND-LIMITED FEEDFORWARD (computed, not residual)")
print("="*100)
def runs(S,vlo,ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo); out=[];n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((i,j+1))
        i=j+1
    return out
DOB={tag:run_real_dob(S) for tag,S in R.items()}
for name,f1,f2,meas in [('0.15-0.30 Hz',0.15,0.30,1.275),('0.30-0.60 Hz',0.30,0.60,1.333)]:
    sos=signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
    num=den=0.0
    for tag,S in R.items():
        for a,b in runs(S,15.0,30.0):
            e=int(3.0*FS)
            tot=signal.sosfiltfilt(sos,S['f'][a:b]/LAF)[e:-e]
            if len(tot)<50: continue
            num+=float(np.dot(signal.sosfiltfilt(sos,-DOB[tag][a:b])[e:-e],tot))
            den+=float(np.dot(tot,tot))
    s=num/den; need=(1-1/meas)/s*100
    print(f"  {name}: observer in-phase share {s:+.3f}   would need a {need:.1f}% cut to reach 1.000")
print()
print("  For reference, the rev 6 rationale in latcontrol_vehicle_tunes.py said a low hold map")
print("  'makes the observer carry 45-64% of the feedforward'. Rev 6.4 raised the level to collapse")
print("  that loop. Measured on rev 6.4's own flight data, the observer still carries the share above.")
