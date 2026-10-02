"""us06 -- (A) is the signed hand torque gp-0x4f60 in the theta frame? (the opposing-hand freeze tests
sign(gp-0x4f60) != sign(E'), E' ~ (theta_sp - theta)).  Firmware: 0x18F bytes0-1 = -((gp-0x4f60*125)>>7) (0x55C50),
0x18F bytes2-3 = -gp-0x6a56 (0x55C62), 0x14A bytes0-1 = -gp-0x6a00; same negation on all three, so wire-frame
correlations carry over.  Manual (no lateral request) driving: a hand turning the wheel leads its rate (corr > 0);
holding a turn, torque has the sign of the angle (corr > 0).
(B) Kp / Kd Y across every variant record the pointer tables reach (0xCB994 / 0xCB7D4, indices 0..9): what the
lane would run if the live selector gp-0x674e were not 7."""
import struct
import numpy as np
C = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz"
z = np.load(C)
def get(k):
    t = z[f"{k}_t"]; d = z[f"{k}_dat"].astype(np.int64); o = np.argsort(t); return t[o], d[o]
def s16(d, i): v = (d[:, i] << 8) | d[:, i + 1]; return np.where(v >= 32768, v - 65536, v)
t8, d8 = get("x18F_b1"); tq, rt = s16(d8, 0), s16(d8, 2)
t4, d4 = get("x14A_b1"); ang = s16(d4, 0)
te, de = get("x0E4_b128"); req = (de[:, 2] >> 7) & 1
j = np.clip(np.searchsorted(te, t8) - 1, 0, len(te) - 1)
manual = ~((np.abs(te[j] - t8) < 0.05) & (req[j] == 1))
idx = np.clip(np.searchsorted(t4, t8), 1, len(t4) - 1)
a_al = ang[idx]
print("(A) hand-torque frame, MANUAL frames (no request):")
for thr in (300, 600, 1200):
    m = manual & (np.abs(tq) > thr) & (np.abs(rt) < 12000)
    print(f"   |tq|>{thr:4d} wire: n={m.sum():6d}  corr(tq,rate)={np.corrcoef(tq[m], rt[m])[0,1]:+.3f}  "
          f"corr(tq,angle)={np.corrcoef(tq[m], a_al[m])[0,1]:+.3f}  sign(tq)==sign(angle) {np.mean(np.sign(tq[m])==np.sign(a_al[m])):.3f}")
img = open("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin", "rb").read()
u16 = lambda a: struct.unpack_from("<H", img, a)[0]; u32 = lambda a: struct.unpack_from("<I", img, a)[0]
print("(B) per-selector records in V298 (pointer table entry -> n, Y):")
for nm, tb, n, yoff in (("Kp", 0xCB994, 5, 12), ("Kd", 0xCB7D4, 4, 10)):
    for s in range(10):
        p = u32(tb + 4 * s)
        nn = u16(p)
        ys = [u16(p + yoff + 2 * i) for i in range(n)] if nn == n else f"(n={nn}, layout differs)"
        print(f"   {nm} sel {s}: rec 0x{p:05X} n={nn} Y={ys}")
