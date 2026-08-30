# -*- coding: utf-8 -*-
"""NET DAMPING, THE RIGHT FIGURE OF MERIT -- |H| * cos(phase), per band, per build.

A lane's damping contribution is not its magnitude and not its phase: it is |H|*cos(phi). Every notch
comparison in this kit has been made on |H| alone. This computes the product.

The lane phase was MEASURED on ra4/ra5/ra6, which carry Honda's biquad, so the measured phi already
includes Honda's contribution. To predict another geometry, apply the DIFFERENCE:

    net_ratio(build) = (|H_build| / |H_honda|) * cos(phi_meas + dphi) / cos(phi_meas)

phi_meas from the flown measurement: 6-9 cos -0.918, 9-12 cos -0.989, 12-15 cos -0.629,
22-30 cos +0.936, 30-40 cos +0.821. Positive net = damping, negative = pumping.
"""
import cmath, glob, math, os, struct, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS=1000.0; R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
A8,AC,B0,B4=0xC60A8,0xC60AC,0xC60B0,0xC60B4
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def img(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
def C(b): return tuple(f32(b,o) for o in (A8,AC,B0,B4))
def H(c,f):
    a8,ac,b0,b4=c; z=cmath.exp(2j*math.pi*f/FS)
    return b4*(z*z+b0*z+1.0)/(z*z+a8*z+ac)
HON=C(img('_v122_'))
BUILDS=[('car / V231',HON),('V228',C(img('_v228_'))),('V232',C(img('_v232_')))]
# measured lane cos per band, and the implied phase
BANDS=[('6-9',6,9,-0.918),('9-12',9,12,-0.989),('12-15',12,15,-0.629),
       ('22-30',22,30,+0.936),('30-40',30,40,+0.821)]
print('='*98)
print('  NET DAMPING  |H|*cos(phase)  -- ratio to the car, per band.  >1 = MORE damping')
print('='*98)
print()
print('  %-12s %s' % ('build',' '.join('%12s'%b[0] for b in BANDS)))
for lbl,c in BUILDS:
    cells=[]
    for nm,lo,hi,cm in BANDS:
        phm=math.degrees(math.acos(cm))          # measured lane phase magnitude
        rs=[]
        for f in np.linspace(lo,hi,40):
            dm=abs(H(c,f))/abs(H(HON,f))
            dp=math.degrees(cmath.phase(H(c,f)))-math.degrees(cmath.phase(H(HON,f)))
            rs.append(dm*math.cos(math.radians(phm+dp))/cm)
        cells.append(np.mean(rs))
    print('  %-12s %s' % (lbl,' '.join('%11.3fx'%v for v in cells)))
print()
print('  reading: in the DAMPING bands (6-15 Hz) >1 means MORE damping = better.')
print('           in the PUMPING bands (22-40 Hz) >1 means MORE pumping = WORSE.')
print()
for lbl,c in BUILDS:
    d=[]; p=[]
    for nm,lo,hi,cm in BANDS:
        phm=math.degrees(math.acos(cm))
        v=np.mean([abs(H(c,f))/abs(H(HON,f))*math.cos(math.radians(phm+(math.degrees(cmath.phase(H(c,f)))-math.degrees(cmath.phase(H(HON,f))))))/cm
                   for f in np.linspace(lo,hi,40)])
        (d if cm<0 else p).append(v)
    print('  %-12s damping bands mean %6.3fx   pumping bands mean %6.3fx   %s'
          % (lbl,np.mean(d),np.mean(p),
             'keeps damping, cuts pumping' if np.mean(d)>0.95 and np.mean(p)<0.95
             else ('LOSES DAMPING' if np.mean(d)<0.95 else 'leaves pumping')))
