# -*- coding: utf-8 -*-
"""c2r2_frame_wire.py -- the gp-0x6a00 vs motor-linear frame ratio measured on the wire (r71b 0x14A) and recomputed from
the image's correction LERP knots (0xC6892 / 0xC68A2).  0x14A packer (record): angle field = -gp-0x6a00 (0.1 deg),
rate field = (gp-0x69ea) >> 3 with gp-0x69ea = -gp-0x6a56 -> theta_6a00 = -A/10 deg, x/8 = -R deg/s.  ANALYSIS ONLY."""
import struct
import numpy as np
KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2"
       "-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
img = open(IMG, "rb").read()
X = struct.unpack_from("<8H", img, 0xC6892); Y = struct.unpack_from("<8h", img, 0xC68A2)
k = (1 / 8) * 1159 / 256 * 900 / 16384           # lin 0.1 deg per motor count (FUN_0003bd7c scale)
cin = 45 / 512                                    # C(x) input per motor count (FUN_0003e600)
print("BYTES: correction knots X", X, "Y", Y)
for i in range(len(X) - 1):
    s = (Y[i + 1] - Y[i]) / (X[i + 1] - X[i]) * cin / k
    print(f"  lin {X[i] / cin * k / 10:6.1f}..{X[i + 1] / cin * k / 10:6.1f} deg: d(6a00)/d(lin) = {1 + s:.3f}")
c = np.load(KIT + "/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz")
t = c["x14A_b1_t"].astype(float); dat = c["x14A_b1_dat"]
A = np.array([int.from_bytes(bytes(r[0:2]), "big", signed=True) for r in dat])
R = np.array([int.from_bytes(bytes(r[2:4]), "big", signed=True) for r in dat])
th = -A / 10.0; om = -R * 1.0
t = t - t[0]
if t[-1] > 1e6:
    t = t / 1e9
kk = 5
dt = t[2 * kk:] - t[:-2 * kk]; dth = (th[2 * kk:] - th[:-2 * kk]) / dt
omw = np.convolve(om, np.ones(2 * kk + 1) / (2 * kk + 1), mode="valid"); thc = th[kk:-kk]
ok = (dt > 0.09) & (dt < 0.11) & (np.abs(omw) < 500)
print("WIRE r71b 0x14A: all-angle slope d(theta_6a00)/dt on x/8 =", round(np.polyfit(omw[ok], dth[ok], 1)[0], 4), "n", int(ok.sum()))
for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 30), (30, 60), (60, 90), (90, 200), (200, 600)):
    m = ok & (np.abs(thc) >= lo) & (np.abs(thc) < hi) & (np.abs(omw) > 3)
    if m.sum() > 100:
        s = np.polyfit(omw[m], dth[m], 1)[0]
        print(f"  |theta| {lo:3d}-{hi:3d} deg: n {int(m.sum()):6d} slope {s:.3f}  (x per deg/s of the 6a00 frame {8 / s:.2f})")
cc = np.corrcoef(omw[ok], dth[ok])[0, 1]
print("  sign: corr(x/8, d theta_6a00/dt) =", round(cc, 4))
