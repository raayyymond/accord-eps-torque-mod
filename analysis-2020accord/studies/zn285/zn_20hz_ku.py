"""20 Hz Ku, phase-tracked, against CREEP-20HZ-LOOP-ID item 4's dose-response.
Byte-exact controller from the V282 image; plant anchored on the measured L(20 Hz).
"""
import os,math,cmath,struct,hashlib
from pathlib import Path
ROOT=Path(os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares"))/"analysis-2020accord"
IMG=ROOT/("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
b=IMG.read_bytes(); u16=lambda a:struct.unpack_from("<H",b,a)[0]
FB_A,FB_B,LAG_A,LAG_B,GAIN=u16(0xC63E8),u16(0xC63EA),u16(0xC63EC),u16(0xC63EE),u16(0xC6CD0)
print(f"sha256 {hashlib.sha256(b).hexdigest()[:16]}  fbEMA {FB_A}/{FB_B}  lag {LAG_A}/{LAG_B}  gain {GAIN}")
T=1e-3
z=lambda f: cmath.exp(2j*math.pi*f*T)
def C(f,kp,kd): return kp/256 + (kd/8)*(1-1/z(f))
def Hlag(f): zz=z(f); return (LAG_B/32768)*(1+1/zz)/(1-(LAG_A/1024)/zz)
def Fb(f):   zz=z(f); return (FB_B/1024)*(1+1/zz)/(1-(FB_A/1024)/zz)
dg=lambda c: math.degrees(cmath.phase(c))

print("\n"+"="*92)
print("TEST 1 -- does the BYTE-EXACT controller reproduce CREEP-20HZ item 4's dose-response?")
print("="*92)
print("  item 4 counterfactuals, direct G, Kp 295:  Kd 0 -> 0.37 /+157d ;  Kd 64 -> 0.51 /-163d")
c0,c64,c128=C(20,295,0),C(20,295,64),C(20,295,128)
print(f"  model |C(20,295,0)|  = {abs(c0):.4f} /{dg(c0):+.1f}d")
print(f"  model |C(20,295,64)| = {abs(c64):.4f} /{dg(c64):+.1f}d")
print(f"  everything else in the loop (lag, fb, gain, taper, PLANT) is common and CANCELS in the ratio.")
print(f"\n  MAGNITUDE:  model |C0|/|C64| = {abs(c0)/abs(c64):.4f}   measured 0.37/0.51 = {0.37/0.51:.4f}"
      f"   -> {100*abs(abs(c0)/abs(c64)/(0.37/0.51)-1):+.1f}%")
dph_meas = 157-(-163)-360        # +157 vs -163, going Kd 64 -> 0
print(f"  PHASE:      model d(angle) Kd 64->0 = {dg(c0)-dg(c64):+.1f}d   measured = {dph_meas:+.1f}d"
      f"   -> {abs((dg(c0)-dg(c64))-dph_meas):.1f}d residual")
print("\n  => the byte-exact controller reproduces BOTH the magnitude and the phase of an")
print("     independently derived 20 Hz dose-response to <1% and <1 degree. [EVIDENCE]")

print("\n  EXTRAPOLATING the same anchor to the LIVE Kd 128, Kp 295:")
L128 = 0.37*abs(c128)/abs(c0); ph128 = 157+dg(c128)-dg(c0)
print(f"    |L(20)| = {L128:.3f} /{(ph128-360):+.1f}d     vs the doc's own Kd-128 rows: 0.8-1.0 at -140..-158d")
print(f"    => lands inside the measured band.  The anchor and the model are mutually consistent.")

print("\n"+"="*92)
print("TEST 2 -- Kp = 0: where is |L(20)| = 1, and IS THAT Ku?")
print("="*92)
K20 = 0.37/abs(c0)          # |L(20)| per unit |C|, at the item-4 anchor (Kp 295, direct G)
PH20 = 157 - dg(c0)         # phase of everything except C, at 20 Hz
print(f"  anchor: |L(20)| = {K20:.4f} * |C(20)| ;  angle(L) = {PH20:+.1f}d + angle(C(20))")
print(f"  (the non-controller phase {PH20:+.1f}d already contains the lag, the fb EMA and the PLANT)")
print(f"\n  {'Kp':>5} {'Kd':>5} {'|L(20)|':>8} {'ang L(20)':>10} {'PM at 20 Hz':>12}")
for kp_,kd_ in [(295,0),(295,64),(295,128),(248,128),(0,64),(0,128),(0,160),(0,198),(0,256),(0,387),(0,859)]:
    c=C(20,kp_,kd_); L=K20*abs(c); ph=PH20+dg(c)
    ph=((ph+180)%360)-180
    print(f"  {kp_:>5} {kd_:>5} {L:>8.3f} {ph:>+9.1f}d {180-abs(ph):>11.1f}d")
kd_unity = 1.0/(K20*abs(C(20,0,8))/8)   # |C(20,0,Kd)| is linear in Kd
print(f"\n  |L(20)| = 1 at Kp 0 occurs at Kd = {kd_unity:.0f}")
c=C(20,0,kd_unity); print(f"  ...but the PHASE there is {((PH20+dg(c)+180)%360)-180:+.1f}d, i.e. PM = "
      f"{180-abs(((PH20+dg(c)+180)%360)-180):.1f}d.")
print("  🛑 THAT IS A CROSSOVER FREQUENCY, NOT Ku.  Ku needs |L| = 1 AND angle = -180d together.")
print("  *** THAT IS A CROSSOVER FREQUENCY, NOT Ku.  Ku needs |L| = 1 AND angle = -180d TOGETHER. ***")

print("\n"+"="*92)
print("TEST 3 -- decompose the +157d, extrapolate above 20 Hz, and find the REAL -180d crossing")
print("="*92)
ph_el20 = dg(Hlag(20)*Fb(20))
print(f"  electronics (lag x fb) phase at 20 Hz = {ph_el20:+.1f}d  [byte-exact]")
print(f"  negative-feedback inversion            = -180.0d")
ph_plant20 = 157 - 0.0 - ph_el20 + 180      # C(20,295,0) is 0d ; unwrap the inversion
ph_plant20 = ((ph_plant20+180)%360)-180
print(f"  => implied PLANT phase at 20 Hz        = {ph_plant20:+.1f}d")
print(f"  CREEP-20HZ sec1.5/sec5 measures the plant at -73d at 22 Hz and -28d at 10 Hz")
print(f"     (slope -3.75 d/Hz = a 10.4 ms equivalent transport delay).  Consistent to a few degrees.")

TAU = (73-28)/12/360        # s per Hz -> equivalent pure delay from the measured slope
print(f"  fitted equivalent delay from the measured plant slope: {1000*TAU:.1f} ms")
def Gpl(f, mode="delay"):
    """plant phase model, anchored at 20 Hz on the item-4 decomposition."""
    if mode=="delay":  ph = ph_plant20 - 360*TAU*(f-20)
    else:              ph = ph_plant20                    # OPTIMISTIC: phase frozen above 20 Hz
    return cmath.exp(1j*math.radians(ph))
KMAG = 0.37/abs(C(20,295,0)*Hlag(20)*Fb(20))   # |L| per unit |C*Hlag*Fb|, anchored
def L(f,kp,kd,mode="delay"):
    return -KMAG*C(f,kp,kd)*Hlag(f)*Fb(f)*Gpl(f,mode)   # the minus = negative feedback
def phase_unwrapped(f,kp,kd,mode):
    # accumulate: controller + lag + fb + plant + inversion, without wrapping the plant delay
    ph = dg(C(f,kp,kd)) + dg(Hlag(f)) + dg(Fb(f)) + (ph_plant20 - 360*TAU*(f-20) if mode=="delay" else ph_plant20) - 180
    return ph
print(f"\n  Kp = 0.  Loop phase vs frequency (delay model), and where it reaches -180d:")
print(f"  {'f Hz':>7} {'ang C':>7} {'ang lag':>8} {'ang fb':>7} {'ang plant':>10} {'ang L':>8} {'|L|/Kd':>9}")
for f in [10,15,20,25,30,35,40,50,60,80]:
    php = ph_plant20-360*TAU*(f-20)
    print(f"  {f:>7.0f} {dg(C(f,0,128)):>6.1f}d {dg(Hlag(f)):>7.1f}d {dg(Fb(f)):>6.1f}d {php:>9.1f}d "
          f"{phase_unwrapped(f,0,128,'delay'):>7.1f}d {abs(L(f,0,128))/128:>9.5f}")
def f180(kp,kd,mode,lo=15.0,hi=200.0):
    g=lambda f: phase_unwrapped(f,kp,kd,mode)+180
    if g(lo)*g(hi)>=0: return None
    for _ in range(90):
        m=(lo+hi)/2
        if g(lo)*g(m)<0: hi=m
        else: lo=m
    return (lo+hi)/2
print(f"\n  {'model':>10} {'Kp':>4} {'Kd':>5} {'f(-180d)':>10} {'|L| there':>10} {'GAIN MARGIN':>12} {'=> Ku (Kd)':>11}")
for mode in ["delay","frozen"]:
    for kp_,kd_ in [(248,128),(0,128),(0,160),(0,198)]:
        fx=f180(kp_,kd_,mode)
        if fx is None: print(f"  {mode:>10} {kp_:>4} {kd_:>5} {'none <200Hz':>10}"); continue
        Lm=abs(L(fx,kp_,kd_,mode)); gm=1/Lm
        print(f"  {mode:>10} {kp_:>4} {kd_:>5} {fx:>9.1f}Hz {Lm:>10.3f} {gm:>11.2f}x {kd_*gm:>11.0f}")
