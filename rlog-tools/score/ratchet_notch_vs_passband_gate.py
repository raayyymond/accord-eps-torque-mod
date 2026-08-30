import sys, os
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np, notch_vs_imu_profile as N
import torque_vs_imu_band_agreement as T
wf=np.arange(3.0,45.0,0.25)
tq=[np.interp(wf,f,c) for f,c in T.torque_curves()]
W=np.clip(np.median(np.vstack(tq),axis=0)-1.0,0,None)
G=np.arange(0.25,50.01,0.25); pb=(G>=0.0)&(G<=5.0)
print('CAN A RATCHET NOTCH PASS THE REAL PASSBAND GATE?\n')
print('  the kit gate: min|H| over 0-5 Hz >= 0.99  (below that, the build is turning base assist down)')
print('  V244 as built: 0.9179  -- FAILS\n')
best=[]
for zf in np.arange(6.0,12.01,0.25):
    for pf in np.arange(5.5,13.01,0.25):
        for r in (0.990,0.993,0.995,0.997,0.998,0.999):
            H=N.resp(zf,pf,r,G)
            if H.max()>1.0+1e-9: continue
            if H[pb].min()<0.99: continue
            Hb=N.resp(zf,pf,r,wf)
            c=float((W*Hb**2).sum()/W.sum())
            best.append((c,zf,pf,r,H.max(),H[pb].min()))
best.sort()
if not best:
    print('  *** NO GEOMETRY PASSES ***')
else:
    print('  %9s %9s %8s %9s %10s %10s' % ('zero Hz','pole Hz','r','max|H|','pb min','removed'))
    print('  '+'-'*62)
    for c,zf,pf,r,mx,lo in best[:8]:
        print('  %9.2f %9.2f %8.3f %9.4f %10.4f %8.1f %%' % (zf,pf,r,mx,lo,100*(1-c)))
    print('  '+'-'*62)
    print('  BEST that passes the passband gate removes %.1f %% of the torque excess.' % (100*(1-best[0][0])))
print('  (V241, aimed at 22-30 Hz, removes 21.8 %% and passes the gate.)')
