# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298 -- F9: the sar-5 integrator rounding (e5 = Ep>>5, inc = (e5*Ki)>>3, both arithmetic floor).
Under ZERO-MEAN symmetric Ep dither, both floors bias toward -inf. Measure the open-loop drift rate and where the
A3 theta-bound + ICL clamp pin it.  (e5 = Ep>>5 is STOCK/V295 arithmetic; Ki 40 (was 0) makes it live.)"""
import struct, hashlib
from pathlib import Path
M32 = 0xFFFFFFFF
def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v
def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)
IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
KI = u16(0xC63E6); ICL = u16(0xC61BA); icl = ((ICL & 0xFFFF) << 10) >> 3

import numpy as np
rng = np.random.default_rng(1)
# open-loop: Ep is a symmetric zero-mean integer dither of amplitude A, theta=0 so A3 bound=1250 (low-speed cap->4096
# but at theta=0 the base 1250 dominates). Integrate with the image's e5/inc arithmetic + A3 freeze + ICL clamp.
for A in (8, 16, 32, 64, 128):
    I8 = 0
    for t in range(200000):
        Ep = int(rng.integers(-A, A + 1))
        e5 = s32(Ep) >> 5                              # 0x29D7C sar 0x5 (floor)
        exc = e5                                       # DB 0
        # A3 bound at theta=0, assume v>2880 (sh=6): bound = (0<<6)+1250 = 1250
        bound = 1250
        t_cmp = (I8 >> 10) if Ep >= 0 else -(I8 >> 10)  # cave 0xC4CAC..0xC4CB6
        frz = (t_cmp >= bound)
        if frz:
            e5 = 0; exc = 0
        inc = s32(s32(exc * KI) >> 3)                  # 0x29DA8 mul ; 0x29DB2 sar 0x3 (floor)
        I = clamp(s32((s32(I8) >> 3) + inc), -icl, icl)
        I8 = s32(I << 3)
    print(f"  Ep dither +-{A:3d}: settled I>>7 = {I8>>3>>7:+6d}  (bound caps I>>10 at 1250 -> I>>7 ~ {1250*1024>>7})"
          f"  ICL caps I>>7 at {icl>>7}")
print("\n  NOTE: e5 = Ep>>5 is the STOCK/V295 sar (inherited). Ki 40 (was 0) activates it. The drift is FLOORED (sign"
      "\n  toward -inf) but BOUNDED by the A3 theta-bound (1250 at center) and ICL; the common scorer uses the same"
      "\n  Ep>>5 floor, so its closed-loop tracking numbers already include it. Covered by R6 + the c0 instrument.")
