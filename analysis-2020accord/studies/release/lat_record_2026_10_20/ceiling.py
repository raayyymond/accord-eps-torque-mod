# Steady-state, hands-off lane-torque ceiling of the V300 angle loop vs the plant hold load, integer mirror of the cave
# (FIRMWARE-CODEPATH 2.2/2.3).  Every constant is read LE from the V300 image.  D = 0 in a static hold.
import glob, struct, math, numpy as np, sys
R="C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
img=open(glob.glob(R+"_v300_*plain_image.bin")[0],'rb').read()
u16=lambda a: struct.unpack_from("<H",img,a)[0]; s16=lambda a: struct.unpack_from("<h",img,a)[0]
KI=u16(0xC63E6); ICL=u16(0xC61BA); PCL=u16(0xC61BC); SCL=u16(0xC61BE); GAIN=u16(0xC6CD0); RAIL=u16(0xC61B4)
FRZ=u16(0xC4C64); VNOCAP=u16(0xC4C80); VCAP=u16(0xC4C8E); CAPLO=u16(0xC4C96); CAPHI=u16(0xC4C9C); BLO=u16(0xC4C8A); BHI=u16(0xC4CAA)
KP=[u16(0xE5384+2*i) for i in range(5)]
TAB=[(u16(0xC4CDA+6*i),u16(0xC4CDA+6*i+2),s16(0xC4CDA+6*i+4)) for i in range(7)]
print("image consts: Ki",KI,"ICL",ICL,"PCL",PCL,"SCL",SCL,"gain",GAIN,"rail clamp",RAIL,"freeze",FRZ,
      "v-gates",VCAP,VNOCAP,"caps",CAPLO,CAPHI,"B",BLO,BHI,"Kp",KP); print("G table",TAB)
VW=1382/6.0   # v-word per m/s (cave comment: 1382 = 6.0 m/s, 714 = 3.1, 2880 = 12.5)
def G(vw, tab=TAB):
    if vw<=tab[0][0]: return tab[0][1]
    k=0
    while vw>tab[k+1][0]: k+=1
    x,y,s=tab[k]; return ((vw-x)*s>>12)+y
def lane_T(err_deg, th_deg, v, kp=KP[0], caplo=CAPLO, caphi=CAPHI, icl=ICL, gscale=1.0):
    vw=int(round(v*VW)); g=int(G(vw)*gscale)
    E=16*int(round(err_deg*10))                       # E = 4sp - 16theta, 160 per degree
    Ep=(E*g)>>8
    P=max(-PCL,min(PCL,(Ep*kp)>>8))
    r9=int(round(abs(th_deg)*10))                     # outward error (same sign as theta): bound uses |theta|
    if vw>VNOCAP: b=(r9<<6)+BHI
    else: b=min((r9<<4)+BLO, caplo if vw<=VCAP else caphi)
    I=min(b, icl)                                     # I>>7 <= ICL (S units)
    S=I+P; S=(S*254)>>8; S=max(-SCL,min(SCL,S))       # hands-off fade 254
    y=S*0.990                                         # output lag DC (2*507/1024 * 1024/1024..), ramp full
    return min(RAIL,(GAIN*y)/32768), I, P
CLIP_BP=[3.1,8.0,10.0,11.75,17.5,26.9]; CLIP_V=[17.0,15.5,19.5,17.0,8.5,4.5]
clip=lambda v: float(np.interp(v,CLIP_BP,CLIP_V))
rail=(GAIN*((15360*254>>8)*0.990))/32768
print(f"rail at S=15360: {rail:.0f} T")
# Plant hold load (BELIEF on shape): V293 hold-map shape k(v)*sat*tanh(th/sat), LEVEL scaled so that
# L(135 deg, 4.5 m/s) = 1144 T = the measured p50 on r9c/r9d/r79 quasi-static holds at 3-6 m/s, 90-180 deg (EVIDENCE).
KB=[2.0,4.0,6.0,8.0,10.0,12.5]; KV=[0.0021,0.0028,0.0044,0.0052,0.0074,0.0092]
def shape(th,v):
    k=np.interp(v,KB,KV); sat=19.3+546*math.exp(-v/3.01); return k*sat*math.tanh(abs(th)/sat)
SC=1144/shape(135,4.5)
L=lambda th,v: SC*shape(th,v)
# VM lateral-accel angle limit (fork limiter): kinematic, SR 16.84, L 2.83 m, no understeer term (BELIEF +0-20 %)
vm=lambda v: math.degrees(math.atan(3.589/max(v,1)**2*2.83))*16.84
print("\n v m/s | G | clip deg | P@clip S | I cap S | T_max @clip (T, %rail) | VM limit deg | load L(180/270/360/430) T | theta_max deg")
for v in [3,4,5,6,7,8,10,12]:
    g=G(int(round(v*VW))); c=clip(v)
    Tm,I,P=lane_T(c,360,v)
    ths=[th for th in range(10,440,2) if lane_T(c,th,v)[0]>=L(th,v)]
    thmax=max(ths) if ths else 0
    print(f" {v:>4} | {g:4d} | {c:5.1f} | {P:6d} | {I:5d} | {Tm:6.0f} {Tm/rail*100:5.1f}% | {min(vm(v),400):5.0f} | "
          + " / ".join(f"{L(t,v):4.0f}" for t in (180,270,360,430)) + f" | {thmax if thmax<438 else '>=lock'}")
def thmax(v, **kw):
    c=clip(v)*kw.pop('clipx',1.0)
    ths=[th for th in range(10,440,2) if lane_T(c,th,v,**kw)[0]>=L(th,v)]
    return (max(ths) if ths else 0), lane_T(c,360,v,**kw)[0]
print("\nLEVERS: theta_max (deg, 438 = lock) / T_max at 360 deg (T) by speed")
levers=[("V300 as built",{}),("ICL 8192->10240",dict(icl=10240)),("Ki (any)",{}),("cap lo 4096->5120",dict(caplo=5120)),
        ("cap lo 4096->6144",dict(caplo=6144)),("cap hi 6144->7168",dict(caphi=7168)),("Kp 112->140 (x1.25, all 28)",dict(kp=140)),
        ("G(v) x1.25",dict(gscale=1.25)),("fork clip x1.3",dict(clipx=1.3)),("fork clip x1.15",dict(clipx=1.15))]
print(" lever".ljust(32)+"".join(f"{v:>5} m/s   " for v in [3,4,5,6,8,10,12]))
for nm,kw in levers:
    row=[thmax(v,**dict(kw)) for v in [3,4,5,6,8,10,12]]
    print(" "+nm.ljust(31)+"".join(f"{a:>4}/{b:5.0f}  " for a,b in row))
# sanity: reproduce the measured hold at 135 deg 4.5 m/s from the measured standing error 8.7 deg (r9d p50)
print("\ncheck: lane_T(err 8.7, th 135, 4.5 m/s) =", round(lane_T(8.7,135,4.5)[0]), "T vs measured p50 1144 (r9d 3-6 m/s 90-180 deg)")
print("check: lane_T(err 6.6, th 135, 4.5) =", round(lane_T(6.6,135,4.5)[0]), "vs r9c p50 976")
print("\nWITH COULOMB FRICTION (outward motion; Fc 156 T at 0-5 m/s, 85 T above -- r79 measured 156 / 73-94):")
Fc=lambda v: 156 if v<=5 else 85
def thmax_f(v, **kw):
    c=clip(v)*kw.pop('clipx',1.0)
    ths=[th for th in range(10,440,2) if lane_T(c,th,v,**kw)[0]>=L(th,v)+Fc(v)]
    return max(ths) if ths else 0
print(" lever".ljust(32)+"".join(f"{v:>6} m/s" for v in [3,4,5,6,8,10,12]))
for nm,kw in levers:
    print(" "+nm.ljust(31)+"".join(f"{thmax_f(v,**dict(kw)):>10}" for v in [3,4,5,6,8,10,12]))
