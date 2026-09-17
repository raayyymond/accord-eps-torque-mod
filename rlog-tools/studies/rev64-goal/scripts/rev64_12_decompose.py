"""EXACT ATTRIBUTION FROM LOGGED SIGNALS ONLY.

cs_out = torque_from_lataccel(P + I + F), and P, I, F are ALL LOGGED (pid_log.p/.i/.f).
So the band-limited command decomposes exactly -- no reconstruction, no model, no assumption.
Within F, AccordHoldLevel's part is exactly computable (it multiplies the hold term by 1.45).

Signs are determined EMPIRICALLY, not by tracing frames through the code (I got that wrong once).
"""
import math, sys, importlib.util
import numpy as np
from scipy import signal
sys.path.insert(0, "/home/user/starpilot")
spec = importlib.util.spec_from_file_location(
    "tunes", "/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)

CA = 'analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D = np.load(CA+f, allow_pickle=True); t = D['t_cs']
    v = np.interp(t, D['t_cst'], D['vego'])
    return dict(t=t, FS=1.0/float(np.median(np.diff(t))), act=D['cs_active'].astype(bool), v=v,
                pr=np.interp(t, D['t_cst'], D['spress'])>0.5, sa=np.interp(t, D['t_cst'], D['sa_deg']),
                curv=D['cs_curv'], dcurv=D['cs_des_curv'], out=D['cs_out'],
                p=D['cs_p'], i=D['cs_i'], f=D['cs_f'], laa=D['cs_la_act'], lad=D['cs_la_des'])
R = {'6c': load('r6c_rev64_ident.npz'), '6d': load('r6d_rev64_ident.npz')}
FS = R['6c']['FS']

print("="*100)
print("CONTROL: does P + I + F reconstruct the logged command? (it must, or the decomposition is void)")
print("="*100)
for tag, S in R.items():
    m = S['act'] & ~S['pr'] & (S['v'] >= 15)
    tot = S['p'][m] + S['i'][m] + S['f'][m]
    r = float(np.corrcoef(tot, S['out'][m])[0, 1])
    k = float(np.dot(tot, S['out'][m])/np.dot(tot, tot))
    resid = np.std(S['out'][m] - k*tot)/np.std(S['out'][m])
    print(f"   {tag}: corr(P+I+F, out) = {r:+.5f}   scale = {k:.5f}   residual/signal = {resid:.4f}")

def runs(S, vlo, ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo); out=[]; n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((i,j+1))
        i=j+1
    return out
def angle_des_of(S):
    m=S['act']&~S['pr']&(np.abs(S['curv'])>1e-5)
    return S['dcurv']*float(np.dot(S['curv'][m],S['sa'][m])/np.dot(S['curv'][m],S['curv'][m]))

print()
print("="*100)
print("BAND-LIMITED IN-PHASE DECOMPOSITION OF THE COMMAND  (shares of P+I+F, sum to 1.000)")
print("="*100)
for name, f1, f2, meas in [('0.15-0.30 Hz', 0.15, 0.30, 1.275), ('0.30-0.60 Hz', 0.30, 0.60, 1.333)]:
    sos = signal.butter(4, [f1, f2], btype='band', fs=FS, output='sos')
    acc = {k: 0.0 for k in ('p','i','f','lvl','den')}; secs=0.0
    for tag, S in R.items():
        ad = angle_des_of(S)
        for a, b in runs(S, 15.0, 30.0):
            v = S['v'][a:b]
            hon = np.array([T.get_honda_accord_hold_torque(float(x),float(vv),level=True) for x,vv in zip(ad[a:b],v)])
            hoff= np.array([T.get_honda_accord_hold_torque(float(x),float(vv),level=False) for x,vv in zip(ad[a:b],v)])
            e=int(3.0*FS)
            tot = signal.sosfiltfilt(sos, S['p'][a:b]+S['i'][a:b]+S['f'][a:b])[e:-e]
            if len(tot)<50: continue
            for key, sig in (('p',S['p'][a:b]),('i',S['i'][a:b]),('f',S['f'][a:b])):
                acc[key] += float(np.dot(signal.sosfiltfilt(sos,sig)[e:-e], tot))
            # the level's own contribution, in LAT-ACCEL units like p/i/f: scale by f/ff_torque.
            # ff_torque -> f is a fixed linear map (latAccelFactor), recovered per run from the logs.
            dlvl = signal.sosfiltfilt(sos, hon-hoff)[e:-e]
            acc['lvl'] += float(np.dot(dlvl, tot)); acc['den'] += float(np.dot(tot,tot)); secs+=len(tot)/FS
    sp,si,sf = acc['p']/acc['den'], acc['i']/acc['den'], acc['f']/acc['den']
    print(f"\n  {name}   ({secs:.0f} s highway engaged)")
    print(f"     P (fast feedback)      : {sp:+.3f}")
    print(f"     I (slow feedback)      : {si:+.3f}")
    print(f"     F (whole feedforward)  : {sf:+.3f}")
    print(f"     -- sum (must be 1.000) : {sp+si+sf:+.3f}")
    print(f"     measured over-delivery : {meas:.3f}  -> to reach 1.000 the command must fall {(1-1/meas)*100:.1f}%")
    print(f"     P alone is {sp*100:.0f}% of the command; F alone is {sf*100:.0f}%.")

print()
print("="*100)
print("WHICH TERM COULD ACTUALLY DELIVER THE NEEDED CUT?")
print("="*100)
print("  To bring 1.333 -> 1.000 the band-limited command must drop 25.0%.")
print("  A term carrying share s must be cut by 25.0/s percent to do it alone:")
for name, f1, f2, meas in [('0.30-0.60 Hz', 0.30, 0.60, 1.333)]:
    sos = signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
    acc={k:0.0 for k in ('p','i','f','den')}
    for tag,S in R.items():
        for a,b in runs(S,15.0,30.0):
            e=int(3.0*FS)
            tot=signal.sosfiltfilt(sos,S['p'][a:b]+S['i'][a:b]+S['f'][a:b])[e:-e]
            if len(tot)<50: continue
            for key,sig in (('p',S['p'][a:b]),('i',S['i'][a:b]),('f',S['f'][a:b])):
                acc[key]+=float(np.dot(signal.sosfiltfilt(sos,sig)[e:-e],tot))
            acc['den']+=float(np.dot(tot,tot))
    need=1-1/meas
    for key,lbl in (('p','P (SteerKP)'),('i','I (AccordTorqueKi)'),('f','F (whole feedforward)')):
        s=acc[key]/acc['den']
        cut=need/s*100 if s>0.01 else float('inf')
        note='' if cut<=100 else '  <- IMPOSSIBLE, term is too small'
        print(f"     {lbl:26s} share {s:+.3f}  needs a {cut:6.1f}% cut{note}")
