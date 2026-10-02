# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298 -- F8: the delivered-surface ceiling. Sustained worst-case T; and the sum/output clamps
compared V298 vs V295 (read from both images)."""
import sys, struct, hashlib, os
from pathlib import Path
HERE = Path(__file__).resolve()
AL = HERE.parents[2]
for p in (AL, AL / "panel2", AL / "refute_c2r2_nonlinear"):
    sys.path.insert(0, str(p))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np
import score_time as ST

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/")
V298 = FW / "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin"
V295 = FW / "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
i8 = V298.read_bytes(); i5 = V295.read_bytes()
assert hashlib.sha256(i8).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda img, a: struct.unpack_from("<H", img, a)[0]
for name, a in [("SCL 0xC61BE", 0xC61BE), ("OCL 0xC61B4", 0xC61B4), ("PCL 0xC61BC", 0xC61BC),
                ("DCL 0xC61B6", 0xC61B6), ("ICL 0xC61BA", 0xC61BA), ("fwd tp+0x7CD0", 0xBF000 + 0x7CD0)]:
    print(f"  {name}: V295={u16(i5,a):6d}  V298={u16(i8,a):6d}  {'SAME' if u16(i5,a)==u16(i8,a) else 'CHANGED'}")

rows = tuple((u16(i8, 0xC4CDA + 6 * j), u16(i8, 0xC4CDA + 6 * j + 2),
              struct.unpack_from("<h", i8, 0xC4CDA + 6 * j + 4)[0]) for j in range(7))
cand = ST.Cand("V298", "E2", rows, dop="fresh", kd=48, kp=112, ki=40, icl=8192, thr=512,
               sgn_thr=300, arb=ST.ARB_A3, ramp_frz=True)
# sustained worst case: hold a huge constant error and max rate the same sign, let I wind to its clamp.
N = 1
lane = ST.CandLane([cand] * N, [8000])
peakT = 0; peakS = 0
for t in range(5000):
    # cmd (sp) at +max, angle (fb) at -max to maximise +E; rate op at +max; no hand torque (no freeze)
    T = lane.tick(np.array([-12000]), np.zeros(1), np.zeros(1), np.array([12000]),
                  np.array([16384]), np.zeros(1), np.array([0x8000]), 1, 1, pol=-1)
    peakT = max(peakT, abs(int(T[0])))
print(f"\n  sustained worst-case (E rail + I wound + D rail, no freeze): peak |T| = {peakT}  (OCL = {u16(i8,0xC61B4)})")
print(f"  theoretical S max = (I>>7)+P+D = {(((8192&0xFFFF)<<10>>3)>>7)}+{u16(i8,0xC61BC)}+{u16(i8,0xC61B6)}"
      f" = {(((8192&0xFFFF)<<10>>3)>>7)+u16(i8,0xC61BC)+u16(i8,0xC61B6)}, SCL caps at {u16(i8,0xC61BE)}")
