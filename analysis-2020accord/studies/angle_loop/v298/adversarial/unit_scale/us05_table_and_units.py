# us05 -- G table + per-band effective gains, all read from the V298 image bytes; design-page cross-check.
import hashlib, struct, os
from pathlib import Path
FW = Path(os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares"))
IMG = FW/"analysis-2020accord"/("_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
b = IMG.read_bytes()
assert hashlib.sha256(b).hexdigest()=="177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
TP=0xBF000
u16=lambda a: struct.unpack_from("<H",b,a)[0]; i16=lambda a: struct.unpack_from("<h",b,a)[0]
# GB-P table at cave+0xDA (mov imm32 r9 points here); rows (X u16, G u16, S s16), 6 bytes
tbl=0xC4CDA; rows=[]
t=tbl
while True:
    X,G,S=struct.unpack_from("<HHh",b,t); rows.append((X,G,S)); t+=6
    if X==0xFFFF: break
print("GB-P rows (X km/h*64, G, S):")
for X,G,S in rows: print(f"   X={X:5d} ({X/64:6.2f} km/h = {X/64/3.6:5.2f} m/s)  G={G:5d}  S={S:6d}")
def walkG(vc):
    vc&=0xFFFF
    if vc<=rows[0][0]: return rows[0][1]
    i=0
    while i+1<len(rows) and vc>rows[i+1][0]: i+=1
    X,G,S=rows[i]
    if rows[i+1][0]==0xFFFF: return G
    # firmware walk: G + ((vc-X)*S >> 12)   (shl 2 on index? no: it is G + ((vc-X)*S)>>12 per build [8] walk)
    return G + (((vc-X)*S)>>12)
Kp=u16(0xE5384); Ki=u16(0xC63E6); Kd=u16(0xE5126)
print(f"\nKp={Kp} Ki={Ki} Kd={Kd}  (Q: E'=(E*G)>>8, P=(E'*Kp)>>8, I: exc*Ki>>3 then I>>7, D=(Kd*op)>>3)")
print("per-band: v, G, Kp_eff=Kp*G/256/256 (torque-count per E-count), E->theta: E=16*(theta_sp-theta) 0.1deg")
print("          so Kp per deg error = Kp_eff*16*10 ; rail angle err = SCL*256/(Kp*G)/16/10 deg")
SCL=u16(0xC61BE); PCL=u16(0xC61BC)
for v in (3.1,6.0,8.0,10.0,11.75,12.5,15.0,17.5,22.0,26.9):
    vc=int(round(v*3.6*64)); G=walkG(vc)
    kpe=Kp*G/256/256                 # P torque-count per E-count
    kp_deg=kpe*160                   # per deg of angle error (E=160 per deg)
    p_rail_deg=PCL/kpe/160 if kpe else 0
    print(f"   v={v:5.1f} m/s vc={vc:5d} G={G:5d}  Kp_eff={kpe:7.4f}/E  ={kp_deg:7.2f} Tcnt/deg  P-rail@{p_rail_deg:6.2f} deg err")
# A3 bound units
print(f"\nA3 bound: low shl {4} (= *16 Tcnt/0.1deg = 160/deg) if v<=2880(=12.5m/s*... check) else shl {6} (*64=640/deg); +1250; cap 4096 if v<=1382")
print(f"  knee vc 2880 = {2880/64:.2f} km/h = {2880/64/3.6:.2f} m/s ; cap vc 1382 = {1382/64:.2f} km/h = {1382/64/3.6:.2f} m/s")
print(f"  ICL={u16(0xC61BA)} -> I>>7 max = ICL*1024/8>>7... I clamp (ICL<<10)>>3 = {((u16(0xC61BA)&0xFFFF)<<10)>>3}, contributes I>>7 = {(((u16(0xC61BA)&0xFFFF)<<10)>>3)>>7} Tcnt")
print(f"  DCL={u16(0xC61B6)}  lane OCL={u16(0xC61B4)}  fwd gain 5346 at 0xC6CD0={u16(0xC6CD0)}  (T = (yr*pol*5346)>>15, clamp OCL)")
# rail 2461: OCL 3072 * 5346/32768?  check the output scaling endpoint
print(f"  stock rail check: OCL {u16(0xC61B4)} is the pre-fwd clamp; after *5346>>15 = {u16(0xC61B4)*5346>>15}; (kit 'rail 2461')")
