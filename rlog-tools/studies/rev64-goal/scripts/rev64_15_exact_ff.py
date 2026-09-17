"""Close the feedforward decomposition using the EXACT angle_des the controller computes.

Previous attempt used a pooled empirical deg-per-curvature (2412) where the VehicleModel gives
2961-3901 depending on speed -- that was the dominant error, not roll. Redo with:
    curv_des  = (setpoint - latAccelOffset*fade) / max(v^2, 1)
    angle_des = degrees(VM.get_steer_from_curvature(-curv_des, v, roll*fade))
using per-frame roll/steerRatio/stiffness from liveParameters and the real VehicleModel.
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
LAF=14.0; FLOWN=dict(rate_gain=0.5,hyst=0.015,rateloop=0.001,dob_hz=0.6)
cp=CarInterface.get_non_essential_params(CAR.HONDA_ACCORD.value); VM=VehicleModel(cp)

CA='analysis-2020accord/_scratch/cache/tau/'
def load(tag):
    D=np.load(CA+f'r{tag}_rev64_ident.npz',allow_pickle=True); L=np.load(CA+f'r{tag}_rev64_live.npz')
    t=D['t_cs']; v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
        pr=np.interp(t,D['t_cst'],D['spress'])>0.5,sa=np.interp(t,D['t_cst'],D['sa_deg']),
        sr=np.interp(t,D['t_cst'],D['sr_deg']),out=D['cs_out'],f=D['cs_f'],sat=D['cs_sat'],
        lad=D['cs_la_des'],laa=D['cs_la_act'],dcurv=D['cs_des_curv'],
        roll=np.interp(t,L['t_lp'],L['roll']),sR=np.interp(t,L['t_lp'],L['sR']),
        stiff=np.interp(t,L['t_lp'],L['stiff']),aoff=np.interp(t,L['t_lp'],L['aoff']),
        lao=np.interp(t,L['t_lt'],L['lao_f']))
R={'6c':load('6c'),'6d':load('6d')}
FS=R['6c']['FS']; DT=1.0/FS

def build(S, use_offset):
    n=len(S['t']); ad=np.empty(n)
    sRl=np.median(S['sR']); VM.update_params(float(np.median(S['stiff'])), float(sRl))
    for j in range(n):
        v=max(float(S['v'][j]),0.1)
        off = float(S['lao'][j]) if use_offset else 0.0
        curv=(float(S['lad'][j])-off)/max(v*v,1.0)
        ad[j]=math.degrees(VM.get_steer_from_curvature(-curv, v, float(S['roll'][j])))
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
        lim=T.get_honda_accord_ff_move_torque_limit(v)
        move[j]=float(np.clip(FLOWN['rate_gain']*adr[j]/G,-lim,lim))
        zz=T.honda_accord_friction_hysteresis(zz,float(ad[j]-(ad[j-1] if j else ad[0])),FLOWN['hyst'],
                                              T.get_honda_accord_friction_hyst_band(v,True))
        z[j]=zz; rl[j]=T.get_honda_accord_rate_loop_gain(v,FLOWN['rateloop'])*(adr[j]-rm[j])
    dob=T.HondaAccordDisturbanceObserver(DT); dob.reset(float(S['sr'][0])); dl=np.zeros(n); prev=0.0
    for j in range(n):
        if not S['act'][j]:
            dob.reset(float(S['sr'][j])); prev=0.0; dl[j]=0.0; continue
        dl[j]=prev
        prev=dob.update(float(S['sa'][j]-S['aoff'][j]),float(S['sr'][j]),float(S['v'][j]),
                        float(-S['out'][j]),FLOWN['dob_hz'],T.get_honda_accord_hold_torque,
                        hold_map=True,gain_scale=1.0,spring_scale=1.0,
                        freeze=bool(S['pr'][j] or S['sat'][j]>0.5))
    model=-(hold+move+z+rl+dl)
    return dict(ad=ad,hold=hold,move=move,z=z,rl=rl,dob=dl,model=model,ff=S['f']/LAF)

print("="*100); print("VALIDATION: reconstructed ff_torque vs the LOGGED ff_torque (cs_f / 14)"); print("="*100)
best={}
for tag,S in R.items():
    for use_off in (False,True):
        c=build(S,use_off); m=S['act']&~S['pr']&(S['v']>=15)
        r=float(np.corrcoef(c['model'][m],c['ff'][m])[0,1]); sl=float(np.dot(c['model'][m],c['ff'][m])/np.dot(c['model'][m],c['model'][m]))
        res=np.std(c['ff'][m]-c['model'][m])/np.std(c['ff'][m])
        print(f"   {tag} latAccelOffset={'ON ':3s} corr={r:+.4f} slope={sl:.3f} resid/sig={res:.3f}" if use_off
              else f"   {tag} latAccelOffset=OFF corr={r:+.4f} slope={sl:.3f} resid/sig={res:.3f}")
        if tag not in best or r>best[tag][0]: best[tag]=(r,use_off,c)
for tag,(r,uo,_) in best.items():
    print(f"   -> {tag}: best is latAccelOffset {'ON' if uo else 'OFF'} (corr {r:+.4f})")

if min(b[0] for b in best.values())<0.90:
    print("\n   RECONSTRUCTION STILL BELOW 0.90 -- not reporting a dose off it."); raise SystemExit

def runs(S,vlo,ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo); out=[];n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((i,j+1))
        i=j+1
    return out
print()
print("="*100); print("CLOSED DECOMPOSITION OF THE BAND-LIMITED FEEDFORWARD"); print("="*100)
for name,f1,f2,meas in [('0.15-0.30 Hz',0.15,0.30,1.275),('0.30-0.60 Hz',0.30,0.60,1.333)]:
    sos=signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
    acc={k:0.0 for k in ('hold','move','z','rl','dob','model','den')}
    for tag,S in R.items():
        c=best[tag][2]
        for a,b in runs(S,15.0,30.0):
            e=int(3.0*FS); tot=signal.sosfiltfilt(sos,c['ff'][a:b])[e:-e]
            if len(tot)<50: continue
            for key,sig in (('hold',-c['hold'][a:b]),('move',-c['move'][a:b]),('z',-c['z'][a:b]),
                            ('rl',-c['rl'][a:b]),('dob',-c['dob'][a:b]),('model',c['model'][a:b])):
                acc[key]+=float(np.dot(signal.sosfiltfilt(sos,sig)[e:-e],tot))
            acc['den']+=float(np.dot(tot,tot))
    print(f"\n  {name}   over-delivery {meas:.3f}; command must fall {(1-1/meas)*100:.1f}%")
    for key,lbl in (('hold','hold'),('move','move'),('z','friction hysteresis'),
                    ('rl','rate loop'),('dob','observer')):
        print(f"     {lbl:22s} {acc[key]/acc['den']:+.3f}")
    print(f"     {'-- modelled total':22s} {acc['model']/acc['den']:+.3f}   unexplained {1-acc['model']/acc['den']:+.3f}")
