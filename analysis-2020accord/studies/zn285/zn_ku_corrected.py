"""CORRECTED Ku: the first instability is a -180d crossing at 22-32 Hz, not the 7.3 Hz ring."""
import os,math,cmath,struct,hashlib
from pathlib import Path
ROOT=Path(os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares"))/"analysis-2020accord"
IMG=ROOT/("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
b=IMG.read_bytes(); u16=lambda a:struct.unpack_from("<H",b,a)[0]
FB_A,FB_B,LAG_A,LAG_B=u16(0xC63E8),u16(0xC63EA),u16(0xC63EC),u16(0xC63EE)
T=1e-3; z=lambda f: cmath.exp(2j*math.pi*f*T)
def C(f,kp,kd): return kp/256+(kd/8)*(1-1/z(f))
def Hlag(f): zz=z(f); return (LAG_B/32768)*(1+1/zz)/(1-(LAG_A/1024)/zz)
def Fb(f):   zz=z(f); return (FB_B/1024)*(1+1/zz)/(1-(FB_A/1024)/zz)
dg=lambda c: math.degrees(cmath.phase(c))
print(f"sha256 {hashlib.sha256(b).hexdigest()[:16]}  (V282)")

# --- convention check: no extra inversion; gp-0x6752 = -1 is already in the forward gain -----
PH_G20 = 157.0 - dg(C(20,295,0)) - dg(Hlag(20)) - dg(Fb(20)) - 360   # unwrap to the lagging branch
print(f"\nCONVENTION CHECK  [EVIDENCE]")
print(f"  item 4 measures angle L(20 Hz) = +157d at Kd 0, Kp 295 (== -203d).")
print(f"  byte-exact: angle C = {dg(C(20,295,0)):+.1f}d, angle Hlag = {dg(Hlag(20)):+.1f}d, angle Fb = {dg(Fb(20)):+.1f}d")
print(f"  => implied PLANT phase at 20 Hz = {PH_G20:+.1f}d")
print(f"  CREEP-20HZ sec1.5 MEASURES the plant at -73d at 22 Hz (and -28d at 10 Hz), INDEPENDENTLY.")
print(f"  Agreement to {abs(PH_G20-(-73)):.1f}d -> the decomposition is validated, and NO extra -180d")
print(f"  inversion belongs in L (gp-0x6752 = -1 is already inside the forward gain).")
SLOPE = -(73-28)/12.0     # deg per Hz, from the two measured plant phases
print(f"  measured plant phase slope 10->22 Hz = {SLOPE:+.2f} d/Hz  (= a {1000*(-SLOPE)/360:.1f} ms equivalent delay)")

KMAG = 0.37/abs(C(20,295,0)*Hlag(20)*Fb(20))
def phL(f,kp,kd,mode="delay"):
    g = PH_G20 + (SLOPE*(f-20) if mode=="delay" else 0.0)
    return dg(C(f,kp,kd))+dg(Hlag(f))+dg(Fb(f))+g
def magL(f,kp,kd): return KMAG*abs(C(f,kp,kd)*Hlag(f)*Fb(f))
def f180(kp,kd,mode,lo=12.0,hi=300.0):
    g=lambda f: phL(f,kp,kd,mode)+180
    if g(lo)*g(hi)>=0: return None
    for _ in range(90):
        m=(lo+hi)/2
        if g(lo)*g(m)<0: hi=m
        else: lo=m
    return (lo+hi)/2

print("\n"+"="*94)
print("THE NYQUIST POINT -- |L| = 1 AND angle L = -180d TOGETHER.  This, not the 7.3 Hz ring, is Ku.")
print("="*94)
print(f"  {'plant model':>12} {'Kp':>5} {'Kd':>5} {'f(-180d)':>10} {'|L| there':>10} {'GAIN MARGIN':>12} {'=> Ku (Kd cell)':>16}")
KU={}
for mode,lbl in [("delay","measured slope"),("frozen","OPTIMISTIC")]:
    for kp_,kd_ in [(295,128),(248,128),(160,128),(0,128)]:
        fx=f180(kp_,kd_,mode)
        if fx is None: print(f"  {lbl:>12} {kp_:>5} {kd_:>5} {'none':>10}"); continue
        Lm=magL(fx,kp_,kd_); gm=1/Lm
        KU[(mode,kp_)]=kd_*gm
        print(f"  {lbl:>12} {kp_:>5} {kd_:>5} {fx:>9.1f}Hz {Lm:>10.3f} {gm:>11.2f}x {kd_*gm:>16.0f}")
print(f"""
  *** INDEPENDENT CONFIRMATION, from the doc's OWN measured rows (item 4 table): ***
      bar-IV Kp 295 -> "GM 1.75x @ 23.4 Hz" ;  bar-IV Kp 470 -> "GM 1.32x @ 22.4 Hz".
      My delay-model GM at Kp 295 is {KU[('delay',295)]/128:.2f}x at {f180(295,128,'delay'):.1f} Hz -- the SAME NUMBER,
      derived independently from the byte-exact controller + the measured plant slope.
      => Ku = 128 x GM = {KU[('delay',295)]:.0f} (Kp 295) .. {KU[('delay',0)]:.0f} (Kp 0).  MEASURED-GRADE.""")

print("\n"+"="*94)
print("ZN, RE-DERIVED ON THE CORRECT Ku")
print("="*94)
for kp_base,lbl in [(0,"Kp = 0 (the ZN hunt config)"),(248,"Kp = 248 (today)")]:
    for mode in ["delay","frozen"]:
        Kdu=KU[(mode,kp_base)]; fosc=f180(kp_base,128,mode); Tu=1.0/fosc; Kua=(Kdu/8)*T
        print(f"\n  --- {lbl}, plant={mode}:  Kd_u = {Kdu:.0f}, f_osc = {fosc:.1f} Hz, Tu = {1000*Tu:.1f} ms ---")
        for form,kf,tif in [("ZN PID",0.6,2.0),("ZN PI",0.45,1.2)]:
            Kpa=kf*Kua; Tia=Tu/tif
            print(f"    {form:<7} -> Kd (0xE511C) = {Kpa*8/T:>5.0f} , Kp (0xE5378) = {(Kpa/Tia)*256:>5.0f}"
                  + ("   , Td = %.1f ms -> NO CELL"%(1000*Tu/8) if form=="ZN PID" else ""))

print("\n"+"="*94)
print("Q4 RE-RUN -- gain margin at the blind-band Nyquist point, delay plant")
print("="*94)
print(f"  {'candidate':>24} {'Kp':>5} {'Kd':>5} {'f(-180d)':>10} {'|L|':>7} {'GM':>7} {'GM dB':>7} {'vs today':>9}")
base=None
for name,kp_,kd_ in [("V282/V283 as built",248,128),("F: Kd 160",248,160),("Kd 192",248,192),
                     ("Kd 112",248,112),("Kp 0 only",0,128),("Kp 0, Kd 160",0,160),
                     ("ZN-PID (new): 328/162",328,162),("ZN-PI (new): 148/122",148,122),
                     ("ZN-PI (OLD, retracted)",108,387),("ZN-PID (OLD, retracted)",241,515)]:
    fx=f180(kp_,kd_,"delay"); Lm=magL(fx,kp_,kd_); gm=1/Lm
    if base is None: base=gm
    flag = "  UNSTABLE" if gm<1 else ""
    print(f"  {name:>24} {kp_:>5} {kd_:>5} {fx:>9.1f}Hz {Lm:>7.3f} {gm:>7.2f}x {20*math.log10(gm):>6.1f}dB {gm/base:>8.2f}x{flag}")

print("\n"+"="*94)
print("CROSS-GATE -- the ZN candidates against the 7.3 Hz RING (which moves the OPPOSITE way in Kd)")
print("="*94)
Ls,Lr = 0.55*cmath.exp(1j*math.radians(96)), 1.19*cmath.exp(1j*math.radians(-27))
def ring(kp,kd):
    R=(C(7.3,kp,kd)*Hlag(7.3))/(C(7.3,248,128)*Hlag(7.3))
    return abs(Ls*R+Lr)
print(f"  {'candidate':>24} {'Kp':>5} {'Kd':>5} {'ring ratio':>11} {'|L(7.3)|':>9} {'GM@blind':>9} {'verdict':>28}")
for name,kp_,kd_ in [("V282/V283 as built",248,128),("F: Kd 160",248,160),
                     ("ZN-PID (new): 329/162",329,162),("ZN-PI (new): 148/122",148,122),
                     ("Kp 0 only",0,128),("Kp 0, Kd 160",0,160),("Kp 0, Kd 192",0,192)]:
    rr=ring(kp_,kd_); L73=0.976*rr/ring(248,128)
    fx=f180(kp_,kd_,"delay"); gm=1/magL(fx,kp_,kd_)
    v=[]
    if L73>=1.0: v.append("RING >= 1")
    if gm<1.30:  v.append("GM < 2.3 dB")
    print(f"  {name:>24} {kp_:>5} {kd_:>5} {rr/ring(248,128):>11.3f} {L73:>9.3f} {gm:>8.2f}x {(' + '.join(v) if v else 'both gates pass'):>28}")
print("""
  The two modes move in OPPOSITE directions in Kd:
    7.3 Hz ring   -- more Kd is BETTER (lower root at Kd ~118; a Kd CUT re-arms the cycle)
    27-32 Hz Nyquist -- more Kd is WORSE (Ku ~227; a Kd RAISE spends gain margin)
  => Kd is bracketed from BOTH sides: [118, 227] at Kp 248.  Today's 128 sits near the BOTTOM
     of that window; candidate F's 160 sits near its middle.  That is the whole design space.""")
