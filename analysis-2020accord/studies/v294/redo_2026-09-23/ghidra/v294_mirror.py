# Integer-exact mirror of the V294 LKAS rate-PID path, FUN_00028ea6, read from the V294 decompile + disassembly.
# Python >> on ints == V850 `sar` (floor toward -inf). Constants read LE from the V294 image, not from any script.
import struct
IMG = r'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin'
B = open(IMG, 'rb').read()
u16 = lambda a: struct.unpack_from('<H', B, a)[0]; s16 = lambda a: struct.unpack_from('<h', B, a)[0]
A    = s16(0xC63E8)   # tp+0x73E8  ld.h  @0x28F8A  -> 1011
Bb   = u16(0xC63EA)   # tp+0x73EA  ld.hu @0x28F86  -> 567
C    = u16(0xC62E6)   # tp+0x72E6  ld.hu @0x28F96/9C/B8 -> 1024
KP   = 960            # 0xCB994[sel] record Y[0..4], all 28 records flat 960 (LERP @0x29DC6..0x29E32)
PCL  = u16(0xC61BC)   # tp+0x71BC  P clamp 15360  @0x29E3A..0x29E5C
SCL  = u16(0xC61BE)   # tp+0x71BE  sum clamp 15360 @0x2A13E..0x2A160
A2   = s16(0xC63EC)   # tp+0x73EC  ld.h  @0x2A184 -> 992
B2   = u16(0xC63EE)   # tp+0x73EE  ld.hu @0x2A174 -> 507
G    = s16(0xC6CD0)   # tp+0x7CD0  ld.h  @0x2A1EE -> 5346
CAP  = u16(0xC61B4)   # tp+0x71B4  lane cap 3072 @0x2A1F8..0x2A220
def clamp(v, c): return c if v > c else (-c if v < -c else v)
def sxh(v): v &= 0xFFFF; return v - 0x10000 if v & 0x8000 else v
class St:  # persistent RAM
    def __init__(s): s.sent = 0; s.s = 0; s.y = 0          # gp-0x3d2c, gp-0x3d30, gp-0x3d3c  (.data boot = 0,0,0)
def tick(st, x, sp=0, g=254, ramp=32768, pol=1, engaged=True, bail=False, v293=False):
    # ---- filter, runs EVERY tick (0x28F4C..0x290D4) ----
    if bail:                                   # 0x28F3C/48/5A/62 -> 0x290B0: r26:=0, r25:=0, sentinel:=2
        st.sent = 2; r26 = 0; engaged = False  # r25=0 forces the 0x29A64 skip to 0x2A164
    else:
        s_old = st.s if st.sent == 1 else 0    # 0x28F72 cmp 1 / 0x28F7C ld.w r26 | 0x28F84 mov 0,r26
        a = 923 if v293 else A; b = 1560 if v293 else Bb; c = 0 if v293 else C
        s_new = ((a * s_old) >> 10) + ((x * b) >> 10)   # 0x28F8E/92 mul, 0x28F9A/A0 sar 0xa, 0x28FA2 add r7,r9
        r26 = (s_old + s_new) if v293 else (s_new - s_old)   # 0x28FA4: V293 add r9,r26 | V294 subr r9,r26 (r26 := r9 - r26)
        st.s = s_new                           # 0x28FA8 st.w r9,-0x3d30
        r26 = clamp(r26, c)                    # 0x28FA6..0x28FBC  (signed ble/bge)
        st.sent = 1                            # 0x28F74 mov 1,r1 -> 0x290D4 st.b r1,-0x3d2c
    pub6a34 = abs((r26 >> 5) << 5) >> 5        # 0x28FBE..0x28FC6, 0x290C6 shr 5, 0x290CA st.h -> gp-0x6a34
    # ---- PID (engaged path) or skip to 0x2A164 ----
    if engaged:
        E = (sp << (5 if v293 else 2)) - r26   # 0x29D76 shl 0x2,r16 (V293: 0x5) ; 0x29D78 sub r26,r16
        P = clamp((E * (120 if v293 else KP)) >> 8, PCL)   # 0x29E36 mul r9,r8 ; 0x29E3E sar 8 ; clamp 0xC61BC
        I = 0; D = 0                           # Ki [0xC63E6]=0, integrator gp-0x6dd0 boots/resets 0; Kd=0 & D clamp [0xC61B6]=0
        S = (I >> 7) + P + D                   # 0x29F18 sar 7 ; 0x29F1E add ; 0x29F24 add
        St_ = (g * S) >> 8                     # 0x2A0B4 mulu/andi 0xffff/sar 8 = g (0..255) ; 0x2A0BE mul ; 0x2A0C2 sar 8
        St_ = sxh(clamp(St_, SCL))             # 0x2A13E..0x2A160
    else:
        St_ = 0                                # 0x2A172 mov 0,r12
    # ---- output lag, runs on both paths (0x2A174..0x2A1B0) ----
    y_new = ((A2 * st.y) >> 10) + ((St_ * B2) >> 10)   # 0x2A180/94 mul ; 0x2A1A0/A6 sar 0xa ; 0x2A1A8 add
    o = (st.y + y_new) >> 5                            # 0x2A1AA add r7,r9 ; 0x2A1AC sar 5
    st.y = y_new                                       # 0x2A1B0 st.w -0x3d3c
    # engaged: gp-0x6806 == 1 so the 0x2A1B6 deadband branch is bypassed (tp+0x74A3 == 1 on V294)
    T1 = sxh((o * ramp) >> 15)                         # 0x2A1E6 mul r14,r9 ; 0x2A1EA sar 0xf ; 0x2A1EC sxh
    T = clamp(((0 + T1) * (pol * G)) >> 15, CAP)       # 0x2A1F6 mulh (pol*G) ; 0x2A1FC add (gp-0x6b2c addend == 0) ; 0x2A1FE mul ; 0x2A202 sar 0xf
    return dict(r26=r26, pub6a34=pub6a34, S=St_, o=o, T=T)   # T -> gp-0x6b38 @0x2A23C
