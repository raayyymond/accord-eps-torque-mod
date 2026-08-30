import sys, os, struct, cmath
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import clip_duty_and_v238_dose as C
import numpy as np

FS=1000.0
def resp(a1,a2,b1,c4,f):
    z=cmath.exp(-2j*cmath.pi*f/FS)
    return c4*(1+b1*z+z*z)/(1+a1*z+a2*z*z)
def geom(a1,a2,b1,c4):
    # zeros on the unit circle: angle = acos(-b1/2)
    zc = np.arccos(np.clip(-b1/2,-1,1))*FS/(2*np.pi)
    r  = np.sqrt(abs(a2)); pc = np.arccos(np.clip(-a1/(2*r),-1,1))*FS/(2*np.pi)
    return zc, pc, r

FW=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
def coeffs(path):
    b=open(path,'rb').read()
    return struct.unpack_from('<ffff', b, 0xC60A8)
import glob
print('BIQUAD GEOMETRY -- zero freq / pole freq / pole radius, and gain at the ratchet\n')
print('  %-42s %8s %8s %7s %9s %9s' % ('image','zero Hz','pole Hz','r','|H|@7.79','max|H|'))
print('  '+'-'*90)
fs_grid=np.linspace(0.5,50,400)
for tag,pat in (('STOCK/car','stock_fw_dump/code.bin'),
                ('V235','_v235_*plain_image.bin'),('V238','_v238_*plain_image.bin'),
                ('V240','_v240_*plain_image.bin')):
    g=glob.glob(FW+pat)
    if not g: 
        g=glob.glob(os.environ['ACCORD_FIRMWARE_ROOT']+'/'+pat)
    if not g: print('  %-42s (not found)'%tag); continue
    a1,a2,b1,c4=coeffs(g[0])
    zc,pc,r=geom(a1,a2,b1,c4)
    h=abs(resp(a1,a2,b1,c4,7.79)); mx=max(abs(resp(a1,a2,b1,c4,f)) for f in fs_grid)
    print('  %-42s %8.2f %8.2f %7.4f %9.4f %9.4f' % (tag,zc,pc,r,h,mx))

print('\nWHAT A NOTCH AIMED AT THE RATCHET WOULD GIVE (zeros on the unit circle at 7.79 Hz):')
print('  %8s %9s %9s %9s %9s %9s' % ('pole Hz','r','|H|@7.79','|H|@6','|H|@9','max|H|'))
print('  '+'-'*60)
wz=2*np.pi*7.79/FS; b1n=-2*np.cos(wz)
for pf,r in ((7.79,0.90),(7.79,0.95),(7.79,0.98),(7.79,0.99),(7.79,0.995)):
    wp=2*np.pi*pf/FS
    a1n=-2*r*np.cos(wp); a2n=r*r
    # normalise so DC gain is 1
    c4n=abs((1+a1n+a2n)/(1+b1n+1))
    hs=[abs(resp(a1n,a2n,b1n,c4n,f)) for f in fs_grid]
    print('  %8.2f %9.3f %9.5f %9.4f %9.4f %9.4f'
          % (pf,r,abs(resp(a1n,a2n,b1n,c4n,7.79)),abs(resp(a1n,a2n,b1n,c4n,6.0)),
             abs(resp(a1n,a2n,b1n,c4n,9.0)),max(hs)))
