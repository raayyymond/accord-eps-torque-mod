import sys, os, glob, struct
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import notch_vs_imu_profile as N
import torque_vs_imu_band_agreement as T
wf=np.arange(3.0,45.0,0.25)
tq=[np.interp(wf,f,c) for f,c in T.torque_curves()]
W=np.clip(np.median(np.vstack(tq),axis=0)-1.0,0,None)
G=N.GRID; gout=(G<5.5)|(G>10.5)
print('HOW MUCH COLLATERAL DOES A 6-10 Hz NOTCH REQUIRE?\n')
print('  a single 2nd-order section at 1 kHz has ~0.05 rad/sample at 8 Hz -- the skirt is wide')
print('  in absolute Hz. Sweeping the "leave the rest alone" floor to find where it becomes feasible:\n')
print('  %10s %10s %9s %9s %7s %10s' % ('out floor','feasible','zero Hz','pole Hz','r','removed'))
print('  '+'-'*60)
for floor in (0.90,0.80,0.70,0.60,0.50,0.40,0.30,0.20):
    best=None
    for zf in np.arange(6.0,11.01,0.25):
        for pf in np.arange(4.0,14.01,0.25):
            for r in (0.94,0.96,0.97,0.98,0.985,0.99,0.995):
                H=N.resp(zf,pf,r,G)
                if H.max()>1.0+1e-9: continue
                if H[gout].min()<floor: continue
                Hb=N.resp(zf,pf,r,wf)
                c=float((W*Hb**2).sum()/W.sum())
                if best is None or c<best[0]: best=(c,zf,pf,r)
    if best is None:
        print('  %10.2f %10s' % (floor,'NONE'))
    else:
        c,zf,pf,r=best
        print('  %10.2f %10s %9.2f %9.2f %7.3f %9.1f %%' % (floor,'yes',zf,pf,r,100*(1-c)))
print('  '+'-'*60)
FW=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
p=[x for x in glob.glob(FW+'*plain_image.bin') if '_v241_' in x][0]
a1,a2,b1,c4=struct.unpack_from('<ffff',open(p,'rb').read(),0xC60A8)
z=np.exp(-2j*np.pi*wf/1000.0); Hv=np.abs(c4*(1+b1*z+z*z)/(1+a1*z+a2*z*z))
Gz=np.exp(-2j*np.pi*G/1000.0); Hg=np.abs(c4*(1+b1*Gz+Gz*Gz)/(1+a1*Gz+a2*Gz*Gz))
print('  V241 for comparison: removes %.1f %% of the torque excess, and its own')
print('  minimum outside 5.5-10.5 Hz is %.4f (it is a 22-30 Hz notch, so that is its trough).'
      % Hg[gout].min())
