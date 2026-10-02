"""ADV UNIT-SCALE V297 -- is gp-0x4f60 (signed hand torque, read by the opposing-hand freeze) in the THETA frame?
Firmware (Ghidra dry-run, V294 program = V295 code):
  0x55C50..0x55C5C  0x18F torque field = -(gp-0x4f60*125 >> 7)
  0x55C62..0x55C66  0x18F next field   = -gp-0x6a56            (x, the held rate, 8 counts per deg/s)
  0x40B04..0x40B18  0x14A angle field  = -gp-0x6a00            (theta, 0.1 deg)
So on 0x18F torque and rate carry the SAME negation. If gp-0x4f60 is in the theta/x frame, a driver steering by hand
(no LKAS request) gives corr(torque_field, rate_field) > 0 and corr(torque_field, angle_field) > 0 (holding a turn).
Byte layout BE s16: 0x18F torque = bytes 0-1, rate = bytes 2-3 (opendbc STEER_STATUS; checked below against 0x14A)."""
import numpy as np
z = np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz")
def s16(d, i): v = (d[:, i].astype(np.int64) << 8) | d[:, i + 1]; return np.where(v >= 32768, v - 65536, v)
t8 = z["x18F_b1_t"]; d8 = z["x18F_b1_dat"]; o = np.argsort(t8); t8, d8 = t8[o], d8[o]
tq, rt8 = s16(d8, 0), s16(d8, 2)
t4 = z["x14A_b1_t"]; d4 = z["x14A_b1_dat"]; o = np.argsort(t4); t4, d4 = t4[o], d4[o]
ang, rt4 = s16(d4, 0), s16(d4, 2)
# align 0x14A to 0x18F by nearest time
idx = np.clip(np.searchsorted(t4, t8), 1, len(t4) - 1); idx -= (t8 - t4[idx - 1]) < (t4[idx] - t8)
a_al, r4_al = ang[idx], rt4[idx]
m = np.abs(r4_al) < 1500
print("CHECK byte layout: corr(0x18F rate field, 0x14A rate field) =", np.corrcoef(rt8[m], r4_al[m])[0, 1].round(4),
      " slope =", (np.sum(rt8[m] * r4_al[m]) / np.sum(r4_al[m] ** 2)).round(3), "(expect +8: -x vs -x/8)")
# LKAS request from openpilot's own 0xE4 (TX echo bus 128): STEER_TORQUE_REQUEST = byte 2 bit 7 (opendbc; BELIEF)
te = z["x0E4_b128_t"]; de = z["x0E4_b128_dat"]; o = np.argsort(te); te, de = te[o], de[o]
req = (de[:, 2] >> 7) & 1
j = np.clip(np.searchsorted(te, t8) - 1, 0, len(te) - 1)
req_al = np.where(np.abs(te[j] - t8) < 0.05, req[j], 0)
print("request=1 fraction of 0x18F frames:", req_al.mean().round(3))
for lab, sel in [("NO request (manual)", req_al == 0), ("request=1 (engaged)", req_al == 1)]:
    for thr in (300, 600, 1200):
        mm = sel & (np.abs(tq) > thr) & (np.abs(rt8) < 12000)
        if mm.sum() < 100: print(f"{lab:22s} |tq|>{thr}: n={mm.sum()} too few"); continue
        c_rate = np.corrcoef(tq[mm], rt8[mm])[0, 1]; c_ang = np.corrcoef(tq[mm], a_al[mm])[0, 1]
        agree_ang = np.mean(np.sign(tq[mm]) == np.sign(a_al[mm]))
        print(f"{lab:22s} |tq|>{thr:4d}: n={mm.sum():6d} corr(tq,rate)={c_rate:+.3f} corr(tq,angle)={c_ang:+.3f} sign(tq)==sign(angle) {agree_ang:.3f}")
