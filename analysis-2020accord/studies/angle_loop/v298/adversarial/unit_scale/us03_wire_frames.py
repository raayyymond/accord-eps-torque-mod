"""us03 -- UNIT/SCALE adversary on V298: on-car frame checks from the wire (route 71, V294 flew; the angle/rate/torque
formers and packers are byte-identical in V298 -- us01 diff shows no byte changed at 0x3E6D8.., 0x40B04.., 0x55C50..,
0x7FE84.., 0x41EEC.., 0x522FE.., 0x534DA..).
Firmware facts used (Ghidra dry-run on the V298 copy, this session):
  0x55C50  0x18F bytes0-1 = -((gp-0x4f60*125)>>7)  ; 0x55C62  0x18F bytes2-3 = -gp-0x6a56 (held rate x)
  0x40B04  0x14A bytes0-1 = -gp-0x6a00 (theta)      (0x14A bytes2-3 = rate/8 per kit record, checked below by slope)
  cave     opposing freeze: |gp-0x4f68| > 300 raw (= 293 wire) ; hard freeze > 512 raw (= 500 wire)
Q1  sign(d theta/dt) vs sign(x): if +, theta and x share a frame (P on theta and the held/fresh rate are co-framed).
Q2  engaged |0x18F torque| distribution vs the 293 / 500 wire thresholds (is the opposing freeze above the floor?).
Q3  0x158 speed vs 0x1D0 wheel speeds (both 0.01 km/h per opendbc) -- consistency of the speed raw unit."""
import numpy as np
C = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz"
z = np.load(C)
def get(k):
    t = z[f"{k}_t"]; d = z[f"{k}_dat"].astype(np.int64); o = np.argsort(t); return t[o], d[o]
def s16(d, i): v = (d[:, i] << 8) | d[:, i + 1]; return np.where(v >= 32768, v - 65536, v)
t4, d4 = get("x14A_b1"); ang, r4 = s16(d4, 0), s16(d4, 2)
t8, d8 = get("x18F_b1"); tq, r8 = s16(d8, 0), s16(d8, 2)
te, de = get("x0E4_b128")
# Q1
K = 5
dt = t4[2*K:] - t4[:-2*K]; w = (ang[2*K:] - ang[:-2*K]) / dt          # field counts/s (field = -theta)
r = r4[K:-K].astype(float)
ok = (dt > 0.08) & (dt < 0.12) & (np.abs(w) > 50) & (np.abs(w) < 3000) & (np.abs(r) < 1500)
print(f"Q1 n={ok.sum()}  corr(d(0x14A angle)/dt, 0x14A rate) = {np.corrcoef(w[ok], r[ok])[0,1]:+.4f}  "
      f"sign-agree = {np.mean(np.sign(w[ok]) == np.sign(r[ok])):.4f}")
idx = np.clip(np.searchsorted(t4, t8), 1, len(t4) - 1)
m8 = np.abs(r4[idx]) < 1500
print(f"   0x18F rate vs 0x14A rate slope = {np.sum(r8[m8]*r4[idx][m8])/np.sum(r4[idx][m8]**2):+.3f} (kit: +8)")
s = np.sum(w[ok] * r[ok]) / np.sum(w[ok] ** 2)
print(f"   0x14A rate per (0.1-deg angle count/s) = {s:+.4f} -> x per deg/s of theta = {80*s:.2f} (all |angle|)")
# Q2
req = (de[:, 2] >> 7) & 1
j = np.clip(np.searchsorted(te, t8) - 1, 0, len(te) - 1)
eng = (np.abs(te[j] - t8) < 0.05) & (req[j] == 1)
a = np.abs(tq[eng])
print(f"Q2 engaged 0x18F frames n={eng.sum()}  |tq| wire pct 50/90/99/99.9 = "
      f"{np.percentile(a,50):.0f}/{np.percentile(a,90):.0f}/{np.percentile(a,99):.0f}/{np.percentile(a,99.9):.0f}")
for thr in (293, 500, 1200):
    print(f"   fraction engaged |tq| > {thr} wire: {np.mean(a > thr):.4f}")
# Q3
t1, d1 = get("x158_b1"); vs = ((d1[:, 0] << 8) | d1[:, 1]) * 0.01               # XMISSION_SPEED kph (opendbc)
tw, dw = get("x1D0_b1")
fl = ((dw[:, 0] << 7) | (dw[:, 1] >> 1)) * 0.01                                  # WHEEL_SPEED_FL 7|15@0+ kph (opendbc)
jj = np.clip(np.searchsorted(t1, tw), 0, len(t1) - 1)
mm = vs[jj] > 10
print(f"Q3 0x158 speed vs 0x1D0 FL wheel (both 0.01 kph): median ratio = {np.median(fl[mm]/vs[jj][mm]):.4f}, "
      f"max speed seen {vs.max():.1f} km/h")
