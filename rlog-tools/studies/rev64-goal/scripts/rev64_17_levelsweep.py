"""DOSE FINDING on a reconstruction that closes to 0.7%.

Rebuild the feedforward under candidate toggle settings and predict the band gain. Uses the exact
angle_des and the fork's own functions/observer, so the hysteresis operator's nonlinearity and the
observer's dynamics are simulated, not linearised.

Prediction: command = P + I + F. Changing F to F' moves the in-phase band content by
    gain' = gain * <P+I+F', u> / <P+I+F, u>          (u = the measured band-limited command)
OPEN LOOP: P and I would partially refill the gap. They carry only 2-9% in band, so the refill is
small, but it means the predictions below are an UPPER bound on the improvement.
"""
import math, sys, importlib.util
import numpy as np
from scipy import signal
sys.path.insert(0,"/home/user/starpilot")
from opendbc.car.vehicle_model import VehicleModel
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
spec=importlib.util.spec_from_file_location("tunes","/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T=importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
LAF=14.0
cp=CarInterface.get_non_essential_params(CAR.HONDA_ACCORD.value); VM=VehicleModel(cp)
CA='analysis-2020accord/_scratch/cache/tau/'
def load(tag):
    D=np.load(CA+f'r{tag}_rev64_ident.npz',allow_pickle=True); L=np.load(CA+f'r{tag}_rev64_live.npz')
    t=D['t_cs']; v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
        pr=np.interp(t,D['t_cst'],D['spress'])>0.5,sa=np.interp(t,D['t_cst'],D['sa_deg']),
        sr=np.interp(t,D['t_cst'],D['sr_deg']),out=D['cs_out'],f=D['cs_f'],sat=D['cs_sat'],
        p=D['cs_p'],i=D['cs_i'],lad=D['cs_la_des'],roll=np.interp(t,L['t_lp'],L['roll']),
        sR=np.interp(t,L['t_lp'],L['sR']),stiff=np.interp(t,L['t_lp'],L['stiff']),
        aoff=np.interp(t,L['t_lp'],L['aoff']))
R={'6c':load('6c'),'6d':load('6d')}; FS=R['6c']['FS']; DT=1.0/FS

def ff_under(S, hold_level, hyst, rate_gain=0.5, rateloop=0.001, spring_scale=1.0):
    n=len(S['t']); ad=np.empty(n)
    VM.update_params(float(np.median(S['stiff'])), float(np.median(S['sR'])))
    for j in range(n):
        v=max(float(S['v'][j]),0.1)
        ad[j]=math.degrees(VM.get_steer_from_curvature(-(float(S['lad'][j]))/max(v*v,1.0),v,float(S['roll'][j])))
    raw=np.concatenate([[0.0],np.diff(ad)])/DT
    a1=DT/(T.HONDA_ACCORD_FF_RATE_RC+DT); adr=np.zeros(n)
    for j in range(1,n): adr[j]=adr[j-1]+a1*(raw[j]-adr[j-1])
    a2=DT/(T.HONDA_ACCORD_RATE_LOOP_RC+DT); rm=np.zeros(n); rm[0]=S['sr'][0]
    for j in range(1,n): rm[j]=rm[j-1]+a2*(S['sr'][j]-rm[j-1])
    hold=np.empty(n);move=np.empty(n);z=np.zeros(n);rl=np.empty(n);zz=0.0
    hf=(lambda a_,v_: T.get_honda_accord_hold_torque(a_,v_,level=hold_level))
    for j in range(n):
        v=float(S['v'][j])
        hold[j]=hf(float(ad[j]),v)*spring_scale
        G=float(np.interp(v,T.HONDA_ACCORD_EPS_G_BP,T.HONDA_ACCORD_EPS_G_V))
        lim=T.get_honda_accord_ff_move_torque_limit(v)
        move[j]=float(np.clip(rate_gain*adr[j]/G,-lim,lim))
        zz=T.honda_accord_friction_hysteresis(zz,float(ad[j]-(ad[j-1] if j else ad[0])),hyst,
                                              T.get_honda_accord_friction_hyst_band(v,True))
        z[j]=zz; rl[j]=T.get_honda_accord_rate_loop_gain(v,rateloop)*(adr[j]-rm[j])
    dob=T.HondaAccordDisturbanceObserver(DT); dob.reset(float(S['sr'][0])); dl=np.zeros(n); prev=0.0
    for j in range(n):
        if not S['act'][j]:
            dob.reset(float(S['sr'][j])); prev=0.0; dl[j]=0.0; continue
        dl[j]=prev
        prev=dob.update(float(S['sa'][j]-S['aoff'][j]),float(S['sr'][j]),float(S['v'][j]),
                        float(-S['out'][j]),0.6,hf,hold_map=True,gain_scale=1.0,
                        spring_scale=spring_scale,freeze=bool(S['pr'][j] or S['sat'][j]>0.5))
    return -(hold+move+z+rl+dl)

def runs(S,vlo,ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo); out=[];n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((i,j+1))
        i=j+1
    return out

BASE={tag:ff_under(S,True,0.015) for tag,S in R.items()}
print("="*104)
print("SANITY: baseline reconstruction must reproduce the logged feedforward")
print("="*104)
for tag,S in R.items():
    m=S['act']&~S['pr']&(S['v']>=15)
    print(f"   {tag}: corr={np.corrcoef(BASE[tag][m],S['f'][m]/LAF)[0,1]:+.4f}")


def predict(NEW):
    out=[]
    for f1,f2,meas in [(0.15,0.30,1.275),(0.30,0.60,1.333)]:
        sos=signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
        num=den=0.0
        for tag,S in R.items():
            for a,b in runs(S,15.0,30.0):
                e=int(3.0*FS)
                u=signal.sosfiltfilt(sos,-(S['p'][a:b]+S['i'][a:b]+S['f'][a:b])/LAF)[e:-e]
                if len(u)<50: continue
                old=signal.sosfiltfilt(sos,-(S['p'][a:b]+S['i'][a:b])/LAF+BASE[tag][a:b])[e:-e]
                new=signal.sosfiltfilt(sos,-(S['p'][a:b]+S['i'][a:b])/LAF+NEW[tag][a:b])[e:-e]
                num+=float(np.dot(new,u)); den+=float(np.dot(old,u))
        out.append(meas*num/den)
    return out

ORIG=list(T.HONDA_ACCORD_HOLD_LEVEL_V)
print()
print("="*100)
print(f"SWEEP OF HONDA_ACCORD_HOLD_LEVEL_V (now {ORIG}) -- keeps the toggle AND keeps low speed")
print("  np.interp CLAMPS, so knot[0] governs <=12.5 m/s and knot[1] governs >=17.5 m/s.")
print("="*100)
print(f"  {'HOLD_LEVEL_V':>16} {'0.15-0.30':>11} {'0.30-0.60':>11} {'worst err':>10}   note")
best=None
for lv in [[1.15,1.45],[1.15,1.30],[1.15,1.25],[1.15,1.20],[1.15,1.15],[1.15,1.10],[1.00,1.15],[1.00,1.00]]:
    T.HONDA_ACCORD_HOLD_LEVEL_V[:]=lv
    row=predict({tag:ff_under(S,True,0.015) for tag,S in R.items()})
    worst=max(abs(row[0]-1.0),abs(row[1]-1.0))
    note=''
    if row[0]<0.97 or row[1]<0.97: note='under-delivers (loose)'
    if lv==ORIG: note='AS FLOWN'
    if best is None or worst<best[0]: best=(worst,lv[:],row[:])
    print(f"  {str(lv):>16} {row[0]:11.3f} {row[1]:11.3f} {worst:10.3f}   {note}")
T.HONDA_ACCORD_HOLD_LEVEL_V[:]=ORIG
print()
print(f"  BEST: HOLD_LEVEL_V = {best[1]}  ->  {best[2][0]:.3f} / {best[2][1]:.3f}  (worst error {best[0]:.3f})")
print()
print("  Both predictions are OPEN LOOP: P and I refill part of any cut. They carry only 2-9% in")
print("  band, so the real result lands slightly ABOVE these -- i.e. safer. Under-delivery is what")
print("  the operator calls 'loose', so landing just above 1.000 beats landing just below.")
