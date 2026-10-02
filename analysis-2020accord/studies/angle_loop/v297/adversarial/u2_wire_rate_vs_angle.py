"""ADV UNIT-SCALE V297 -- on-car frame check from the wire (route 71b, V294 flew; the angle/rate formers are
byte-identical stock code). 0x14A bytes 0-1 = -gp-0x6a00 (0.1 deg, BE s16), bytes 2-3 = -gp-0x6a56/8 (BE s16).
Question 1 (LOOP SIGN, U4): does d(theta)/dt have the SAME sign as the held rate x? -> slope > 0.
Question 2 (FRAME, the 1.155): slope of rate_field vs d(angle_field/10)/dt by |angle| bin should be ~1/1.155 = 0.866
near centre and rise toward ~1.04 outward, if x is 8 counts per deg/s of the LINEAR (motor) angle.
Byte positions are the opendbc STEERING_SENSORS layout (BELIEF: DBC, not firmware)."""
import numpy as np
z = np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz")
t = z["x14A_b1_t"]; d = z["x14A_b1_dat"].astype(np.int64)
ang = ((d[:, 0] << 8) | d[:, 1]); ang = np.where(ang >= 32768, ang - 65536, ang)        # field, 0.1 deg
rat = ((d[:, 2] << 8) | d[:, 3]); rat = np.where(rat >= 32768, rat - 65536, rat)        # field
o = np.argsort(t); t, ang, rat = t[o], ang[o], rat[o]
K = 5                                                     # +-50 ms central difference
dt = t[2*K:] - t[:-2*K]; da = (ang[2*K:] - ang[:-2*K]) / 10.0      # deg
w = da / dt                                               # d(angle_field)/dt, deg/s, in field sign
r = rat[K:-K].astype(float); a = ang[K:-K] / 10.0
ok = (dt > 0.08) & (dt < 0.12) & (np.abs(w) > 5) & (np.abs(w) < 300) & (np.abs(r) < 1500)
print("frames", len(t), "usable", ok.sum())
c = np.corrcoef(w[ok], r[ok])[0, 1]
print(f"corr(d(angle_field)/dt, rate_field) = {c:+.4f}")
print("sign agreement fraction:", np.mean(np.sign(w[ok]) == np.sign(r[ok])).round(4))
for lo, hi in [(0, 10), (10, 30), (30, 60), (60, 120), (120, 250), (250, 500)]:
    m = ok & (np.abs(a) >= lo) & (np.abs(a) < hi)
    if m.sum() < 50: print(f"|angle| {lo:3d}-{hi:3d}: n={m.sum()} (too few)"); continue
    s = np.sum(w[m] * r[m]) / np.sum(w[m] ** 2)
    print(f"|angle| {lo:3d}-{hi:3d} deg: n={m.sum():6d}  slope rate/angle-rate = {s:+.3f}  (=> x per deg/s of theta = {8*s:.2f})")
print("max |angle field| deg:", np.abs(ang).max() / 10.0)
