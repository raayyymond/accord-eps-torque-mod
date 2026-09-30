"""b2_wire_units.py -- ADV-B step 2: the x scale and the command scale ON THE WIRE of r71b (route
75604b0a432fdc89_00000071--a7b8ba5d9d, V294), independent of the build script.

(1) integer identity between the 0x14A rate field and the 0x18F rate field (the bytes say: 0x14A field = (gp-0x69ea)>>3
    with gp-0x69ea = -x [FUN_00040a50], and the 0x55C62/0x557D6 packers publish -x at full resolution);
(2) slopes: 0x18F raw vs carState.steeringRateDeg; 0x14A deg/s vs x/8;
(3) kappa: d(0x14A angle)/dt against x/8, by |angle| bin (0.5 s spans), and by the spectral gain 0.5-3 Hz;
(4) 0xE4 wire counts per openpilot torque unit (carOutput.actuatorsOutput.torque and carControl.actuators.torque).
Run: python b2_wire_units.py > b2_wire_units_out.txt
"""
import sys

import numpy as np

sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
import r71b_cache as R  # noqa: E402

D = R.load()
C = D["can_raw"]


def i16be(d, i):
    v = (d[:, i].astype(np.int32) << 8) | d[:, i + 1].astype(np.int32)
    return np.where(v >= 32768, v - 65536, v)


f14 = i16be(C["x14A_b1_dat"], 2)          # raw 0x14A rate field (signed, DBC factor -1 deg/s)
t14 = C["x14A_b1_t"]
f18 = i16be(C["x18F_b1_dat"], 2)          # raw 0x18F rate field
t18 = C["x18F_b1_t"]
print("frames: 0x14A %d, 0x18F %d" % (len(t14), len(t18)))

# (1) integer identity: pair each 0x14A frame with 0x18F frames near it in time
print("\n[1] integer identity f14 == f(f18) over pairings (0x14A frame vs the 0x18F frame at offset k in the sorted stream)")
j = np.searchsorted(t18, t14)
for k in (-2, -1, 0, 1):
    jj = np.clip(j + k, 0, len(t18) - 1)
    dt = (t18[jj] - t14) * 1000
    for nm, g in (("f18>>3", f18[jj] >> 3), ("(-f18)>>3", (-f18[jj]) >> 3), ("-(f18>>3)", -(f18[jj] >> 3)),
                  ("round(f18/8)", np.round(f18[jj] / 8.0).astype(int))):
        eq = np.mean(f14 == g)
        print("   k=%+d  median dt %+6.2f ms  %-13s identical on %.4f of frames" % (k, np.median(dt), nm, eq))

# which pairing is best, and on moving frames only
jj = np.clip(j - 1, 0, len(t18) - 1)
mv = np.abs(f18[jj]) > 80
for k in (-1, 0):
    jj = np.clip(j + k, 0, len(t18) - 1)
    print("   moving frames (|f18|>80, n=%d) k=%+d: f14 == f18>>3 on %.4f" % (mv.sum(), k, np.mean((f14 == (f18[jj] >> 3))[mv])))

# (2) slopes
print("\n[2] slopes")
cs_t, cs_rate = D["cs_t"], D["cs_rate"]
x_fw = -f18.astype(float)                 # the kit's x_fw; the bytes say 0x18F raw = -x
ri = np.interp(cs_t, t18, x_fw)
A = np.vstack([cs_rate, np.ones_like(cs_rate)]).T
k = np.linalg.lstsq(A, ri, rcond=None)[0]
print("   x_fw (= -0x18F raw) vs carState.steeringRateDeg: slope %.4f counts per deg/s (offset %.3f)" % tuple(k))
r14 = -f14.astype(float)                  # DBC: deg/s = -1 x field
ri2 = np.interp(t14, t18, x_fw) / 8.0
A = np.vstack([r14, np.ones_like(r14)]).T
k2 = np.linalg.lstsq(A, ri2, rcond=None)[0]
print("   (x_fw/8) vs 0x14A deg/s (DBC -1): slope %.5f (offset %.3f deg/s; floor bias expected +0.44)" % tuple(k2))
print("   DBC for the Accord (honda_civic_hatchback_ex_2017_can_generated): 0x14A STEER_ANGLE_RATE (-1) deg/s;"
      " 0x18F STEER_ANGLE_RATE (-0.1) deg/s.")
print("   => the 0x18F DBC factor would give x = %.2f counts per deg/s, the wire says %.3f: the 0x18F DBC factor is"
      " WRONG for this car by x%.3f" % (10.0, k[0], 10.0 / k[0]))

# (3) kappa from the angle
print("\n[3] kappa = d(0x14A angle)/dt vs x/8 (0.5 s spans, all frames with |x/8| span-mean > 5 deg/s, and engaged-only)")
ang = -0.1 * i16be(C["x14A_b1_dat"], 0).astype(float)
t = t18
xr = x_fw / 8.0
angi = np.interp(t, t14, ang)
G = R.grid100(D)
eng = np.asarray(G["eng"], bool)
n = len(t)
L = 50
res = []
for mask_nm, msk in (("all", np.ones(n, bool)), ("engaged", eng)):
    rows = []
    for a in range(0, n - L, L):
        if not msk[a:a + L].all():
            continue
        if np.any(np.diff(t[a:a + L + 1]) > 0.03):
            continue
        dA = angi[a + L] - angi[a]
        integ = np.sum(xr[a:a + L] * np.diff(t[a:a + L + 1]))
        if abs(integ) < 2.5:           # at least 2.5 deg of motion in 0.5 s
            continue
        rows.append((np.mean(np.abs(angi[a:a + L])), dA / integ, abs(integ)))
    rows = np.array(rows)
    print("   %s: %d spans" % (mask_nm, len(rows)))
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 160), (160, 999)):
        m = (rows[:, 0] >= lo) & (rows[:, 0] < hi)
        if m.sum() < 5:
            continue
        w = rows[m, 2]
        print("      |angle| %3d-%3d deg: n %4d  kappa median %.3f  weighted %.3f" % (lo, hi, m.sum(), np.median(rows[m, 1]),
                                                                          np.sum(rows[m, 1] * w) / np.sum(w)))
    res.append(rows)

# spectral method, 0.5-3 Hz, on-centre (|angle| < 20) engaged runs
from scipy import signal  # noqa: E402
fs = 100.0
th_rate = np.gradient(angi) * fs
b_, a_ = signal.butter(2, [0.5 / 50, 3.0 / 50], btype="band")
oc = eng & (np.abs(angi) < 20)
dd = np.diff(np.r_[0, oc.astype(int), 0])
runs = [(s, e) for s, e in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)) if e - s > 600]
num, den = 0.0, 0.0
for s, e in runs:
    u = signal.filtfilt(b_, a_, xr[s:e])[100:-100]
    y = signal.filtfilt(b_, a_, th_rate[s:e])[100:-100]
    num += np.sum(u * y); den += np.sum(u * u)
print("   spectral 0.5-3 Hz, engaged |angle|<20 deg runs (%d runs): kappa = %.3f" % (len(runs), num / den))

# (4) wire per openpilot torque unit
print("\n[4] 0xE4 wire counts per openpilot torque unit")
e4t, e4 = D["e4_t"], D["e4_cmd"]
for nm, tk, yk in (("carOutput.actuatorsOutput.torque", "co_t", "co_torque"), ("carControl.actuators.torque", "cc_t", "cc_torque")):
    yi = np.interp(e4t, D[tk], D[yk])
    m = np.abs(yi) > 0.02
    A = np.vstack([yi[m], np.ones(m.sum())]).T
    kk = np.linalg.lstsq(A, e4[m], rcond=None)[0]
    print("   e4 wire vs %s: slope %.1f counts per unit (offset %.2f), n %d" % (nm, kk[0], kk[1], m.sum()))
# exact integer relation?
yi = np.interp(e4t, D["co_t"], D["co_torque"])
m = np.abs(yi) > 0.02
for S in (4096.0, 4095.0, 4093.0, 4091.0, 4064.0, 3840.0):
    print("   frac(e4 == round(-%g*torque)) = %.4f ; frac(|e4 - -%g*torque| <= 1) = %.4f" % (
        S, np.mean(e4[m] == np.round(-S * yi[m])), S, np.mean(np.abs(e4[m] + S * yi[m]) <= 1.0)))
