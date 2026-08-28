import numpy as np, struct, glob, os
FR=r'C:\Users\dudei\Desktop\Projects\accord-firmwares'
img=glob.glob(os.path.join(FR,'analysis-2020accord','*v112*plain_image.bin'))[0]
b=open(img,'rb').read()
s16=lambda a: struct.unpack_from('<h',b,a)[0]
u32=lambda a: struct.unpack_from('<I',b,a)[0]
print("V112's gp-0x6b26 Y ROWS (dereferenced from 0xCBE74 + mode*4):")
rows={}
for mode,addr in ((24,0xD6A6C),(26,0xD7A5C),(27,0xD7A6C)):
    y=[s16(addr+2*k) for k in range(3)]
    rows[mode]=y
    print("   mode %2d @0x%05X  Y = %s   |Y|max %d   int16 headroom x%.3f"
          %(mode,addr,y,max(abs(v) for v in y),32767/max(abs(v) for v in y)))
HEAD=32767/max(abs(v) for v in rows[26])
FS=1000.0
def parts(f,a2,a_lp=37):
    w=2*np.pi*f/FS; z=np.exp(1j*w); a=a_lp/128.0; bb=a2/64.0
    H=64*(a/(1-(1-a)/z))*(1-1/z)*(bb/(1-(1-bb)/z))
    hr=H/(1j*w); phi=-np.angle(hr); m=np.abs(hr)*w
    return m*np.sin(phi), m*np.cos(phi), abs(H)
def band(a2,lo,hi,i):
    fs=np.arange(lo,hi+.001,.5); return np.mean([parts(f,a2)[i] for f in fs])
ff=np.linspace(0.5,499,3000)
def peak(a2):
    w=2*np.pi*ff/FS; z=np.exp(1j*w); a=37/128.0; bb=a2/64.0
    return np.max(np.abs(64*(a/(1-(1-a)/z))*(1-1/z)*(bb/(1-(1-bb)/z))))

print("\nHOW MUCH DAMPING CAN THIS LANE STILL SUPPLY?  Y is capped by int16 at x%.3f"%HEAD)
print("  a2   Yx    | 6-16Hz damping   6-16Hz mass   peak |H|   <- all vs V112 (a2=14, Yx=1)")
best=None
for a2 in (14,10,8,7,6,5,4,3):
    for yx in (1.0,HEAD):
        d=yx*band(a2,6,16,0)/band(14,6,16,0)
        m=yx*band(a2,6,16,1)/band(14,6,16,1)
        p=yx*peak(a2)/peak(14)
        ok = (m<=1.0) and (p<=1.0)
        if ok and (best is None or d>best[0]): best=(d,a2,yx,m,p)
        print("  %2d  %.3f  |    %6.3f          %6.3f       %6.3f   %s"
              %(a2,yx,d,m,p,"OK" if ok else ""))
print("\n  BEST feasible (mass <= V112 and peak <= V112): damping x%.3f at a2=%d, Y x%.3f"
      %(best[0],best[1],best[2]))

print("\nIS THAT ENOUGH?  The Re(Z) deficit at 6-9 Hz, engaged, measured on 17 route-arms:")
print("   route 21 (V111) 6-9 Hz Re(Z) = -43 per deg/s = %.0f per rad/s"%(-43*57.2958))
print("   gp-0x6b26's own measured contribution (V94 flight) = +518 to +565 per rad/s")
for lab,d in (("V115  a2=8",1.252),("a2=6",1.318),("best feasible",best[0])):
    add=518*(d-1.0)
    print("   %-14s damping x%.3f  =>  +%4.0f counts of Re(Z)  =  %.1f%% of the -2464 deficit"
          %(lab,d,add,100*add/2464))
print("\n  => the gp-0x6b26 lane can supply AT MOST %.0f more counts against a 2464-count deficit."
      %(518*(best[0]-1.0)))
print("     To CLOSE the deficit this lane would need x%.1f, but int16 caps Y at x%.3f."
      %(1+2464/518,HEAD))
