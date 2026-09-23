"""
REDO-PHYSICS claim 3 (high-frequency part): the 15-17 Hz pole, the 20 Hz plant line, 26-31 Hz; the -180 deg crossing
of the trim's added torque; a scale-free comparison with V282's flown P+D rate loop at the SAME sensor/actuator points;
and a collocated two-mass plant family.

Controllers, from the integer arithmetic, both x -> T counts, linear regime:
  V294: T = -3.75 * g(1-z^-1)/(1-p z^-1) * taper * Hout * FWD * x            (a 1011, b 567)
  V282: T = -[248/256 + (128/8)(1-z^-1)] * g'(1+z^-1)/(1-p' z^-1) * taper * Hout * FWD * x   (a 923, b 1560)
Rate-referenced controller Cr = -T/rate (T counts per deg/s, x = 8 rate): Re Cr > 0 = damping, < 0 = anti-damping
(for a collocated mode). Extra transport delay Td (sensor + compute + actuator) swept.
"""
import math
import numpy as np
from scipy import signal
from rp3_wheel_mode import T_PER_U, J0, k_of, pmul, closed_poles, s_of, plant_tf, sensor_tf

TS = 1e-3
XS = 8.0
TAPER, FWD = 254 / 256, 5346 / 32768


def z1(f):
    return np.exp(-2j * np.pi * f * TS)


def Hout(f):
    return (507 / 1024) * (1 + z1(f)) / (1 - (992 / 1024) * z1(f)) / 32


def Cr294(f, Td=0.0):
    x = (567 / 1024) * (1 - z1(f)) / (1 - (1011 / 1024) * z1(f))
    return 3.75 * x * TAPER * Hout(f) * FWD * XS * np.exp(-2j * np.pi * f * Td)


def Cr282(f, Td=0.0):
    fb = (1560 / 1024) * (1 + z1(f)) / (1 - (923 / 1024) * z1(f))
    pd = 248 / 256 + 16 * (1 - z1(f))
    return pd * fb * TAPER * Hout(f) * FWD * XS * np.exp(-2j * np.pi * f * Td)


print("=== P-counts per x-count at 20 Hz (before taper/output lag): V294 vs V282 ===")
p294 = abs(3.75 * (567 / 1024) * (1 - z1(20)) / (1 - (1011 / 1024) * z1(20)))
p282 = abs((248 / 256 + 16 * (1 - z1(20))) * (1560 / 1024) * (1 + z1(20)) / (1 - (923 / 1024) * z1(20)))
print(f"V294 {p294:.3f}  V282 {p282:.2f}  ratio {p294/p282:.4f} = {20*math.log10(p294/p282):.2f} dB")

print("\n=== |Cr| ratio V294/V282 across frequency (scale-free: same sensor, same actuator, same Td cancels in the ratio) ===")
for f in (1, 2, 3, 5, 7, 10, 13, 16, 18, 20, 22, 26, 30, 35, 40, 60):
    r = abs(Cr294(f)) / abs(Cr282(f))
    print(f"  {f:5.1f} Hz: |Cr294| {abs(Cr294(f)):7.3f}  |Cr282| {abs(Cr282(f)):8.3f} T/(deg/s)   ratio {r:.4f} ({20*math.log10(r):6.1f} dB)"
          f"   phase294 {np.degrees(np.angle(Cr294(f))):7.1f}  phase282 {np.degrees(np.angle(Cr282(f))):7.1f}")

print("\n=== where the V294 added torque crosses 180 deg of total lag re acceleration (Re Cr294 = 0 crossing; damping below) ===")
f = np.linspace(0.5, 200, 400000)
for Td_ms in (0, 1, 2, 3, 4, 5, 6, 8, 10):
    c = Cr294(f, Td_ms * 1e-3)
    idx = np.where(np.diff(np.sign(c.real)) != 0)[0]
    first = f[idx[0]] if len(idx) else float('nan')
    # the anti-damping band's worst Re Cr and its size relative to the trim's own low-frequency damping (at 2.4 Hz)
    band = (f > first) if len(idx) else np.zeros_like(f, bool)
    worst = c.real[band].min() if band.any() else 0.0
    wf = f[band][np.argmin(c.real[band])] if band.any() else float('nan')
    print(f"  Td {Td_ms:4.1f} ms: damping -> anti-damping at {first:6.2f} Hz; worst anti-damping Re Cr {worst:+.4f} T/(deg/s) at {wf:.1f} Hz "
          f"(= {abs(worst)/Cr294(2.4).real*100:.1f} % of the trim's 2.4 Hz damping {Cr294(2.4).real:.3f})")

print("\n=== V282's anti-damping for comparison (the loop that ground at 17-21 Hz) ===")
for Td_ms in (0, 1, 2, 3, 5):
    c = Cr282(f, Td_ms * 1e-3)
    idx = np.where(np.diff(np.sign(c.real)) != 0)[0]
    first = f[idx[0]] if len(idx) else float('nan')
    print(f"  Td {Td_ms} ms: V282 Re Cr282 changes sign at {first:6.2f} Hz; Re Cr at 20 Hz {Cr282(20, Td_ms*1e-3).real:+.3f}, at 26 Hz {Cr282(26, Td_ms*1e-3).real:+.3f}; "
          f"V294 Re Cr at 20 Hz {Cr294(20, Td_ms*1e-3).real:+.4f}, 26 Hz {Cr294(26, Td_ms*1e-3).real:+.4f}")

# ---- rigid-body loop gain of V282 in the fork plant: does it cross over near the recorded 17-21 Hz? --------------
print("\n=== consistency check: V282's rate loop crossover in this plant (J_T = J * T_per_u), rigid body ===")
JT = J0 * T_PER_U
for Td_ms in (0, 2, 4):
    ff = np.logspace(0, 2.5, 20000)
    L = Cr282(ff, Td_ms * 1e-3) / (1j * 2 * np.pi * ff * JT)
    i = np.where(np.diff(np.sign(abs(L) - 1)))[0]
    fc = ff[i[-1]]
    print(f"  Td {Td_ms} ms: V282 |L| = 1 at {fc:.1f} Hz, phase {np.degrees(np.angle(L[i[-1]])):.0f} deg (PM {180+np.degrees(np.angle(L[i[-1]])):.0f})"
          f"; V294 |L| there {abs(Cr294(fc, Td_ms*1e-3)/(1j*2*np.pi*fc*JT)):.4f}")

# ---- a collocated two-mass family: motor/rack side J_m (sensor + actuator), wheel side J_w on a torsion spring ---------
print("\n=== collocated two-mass family: flexible-mode zeta, open / with V294 trim / with V282 loop (d = 2 ticks, m = 3) ===")


def two_mass_tf(Jm, Jw, kt, ct, b, k):
    # states: th_m, th_m', th_w, th_w' ; input T (u units) on the motor side ; output th_m
    A = np.array([[0, 1, 0, 0],
                  [-(k + kt) / Jm, -(b + ct) / Jm, kt / Jm, ct / Jm],
                  [0, 0, 0, 1],
                  [kt / Jw, ct / Jw, -kt / Jw, -ct / Jw]])
    B = np.array([[0], [1 / Jm], [0], [0]]); C = np.array([[1, 0, 0, 0]]); D = np.array([[0]])
    Ad, Bd, Cd, Dd, _ = signal.cont2discrete((A, B, C, D), TS, method="zoh")
    num, den = signal.ss2tf(Ad, Bd, Cd, Dd)
    return np.squeeze(num), den


def ctrl_tf(which):
    p2, g2 = 992 / 1024, 507 / 1024
    out_n, out_d = g2 / 32 * np.array([1, 1]), np.array([1, -p2])
    if which == "v294":
        n = -3.75 * (567 / 1024) * np.array([1, -1]); d = np.array([1, -1011 / 1024])
    else:
        fb_n, fb_d = (1560 / 1024) * np.array([1, 1]), np.array([1, -923 / 1024])
        pd = np.array([248 / 256 + 16, -16])
        n = -pmul(pd, fb_n); d = fb_d
    k = TAPER * FWD / T_PER_U
    return k * pmul(n, out_n), pmul(d, out_d)


def cl_modes(gn, gd, which, d=2, m=3):
    sn, sd = sensor_tf(m)
    if which is None:
        return closed_poles(np.zeros(1), gd)
    cn, cd = ctrl_tf(which)
    dn = np.zeros(d + 1); dn[d] = 1
    Ln = -pmul(pmul(pmul(gn, sn), cn), dn); Ld = pmul(pmul(gd, sd), cd)
    return closed_poles(Ln, Ld)


def flex_mode(P, flo, fhi):
    best = None
    for z in P:
        if z.imag <= 1e-9: continue
        s = s_of(np.array([z]))[0]; fn = abs(s) / 2 / math.pi
        if flo <= fn <= fhi:
            zt = -s.real / abs(s)
            if best is None or zt < best[0]: best = (zt, fn)
    return best, max(abs(P))


v = 19.0; k = k_of(v); b = 6e-4
rows = []
for fmode in (12, 16, 20, 26, 31, 40):
    for rw in (0.2, 0.5, 0.8):
        for zeta_m in (0.02, 0.05):
            Jw = rw * J0; Jm = J0 - Jw
            kt = (2 * math.pi * fmode) ** 2 * Jm * Jw / (Jm + Jw)
            ct = 2 * zeta_m * math.sqrt(kt * Jm * Jw / (Jm + Jw))
            gn, gd = two_mass_tf(Jm, Jw, kt, ct, b, k)
            o, _ = flex_mode(cl_modes(gn, gd, None), 0.6 * fmode, 1.6 * fmode)
            w4, r4 = flex_mode(cl_modes(gn, gd, "v294"), 0.5 * fmode, 1.8 * fmode)
            w2, r2 = flex_mode(cl_modes(gn, gd, "v282"), 0.3 * fmode, 2.5 * fmode)
            rows.append((fmode, rw, zeta_m, o, w4, r4, w2, r2))
            print(f"  mode {fmode:3d} Hz, J_w/J {rw:.1f}, zeta_open {zeta_m:.2f}: open {o[0]:.4f}@{o[1]:.1f} | V294 "
                  f"{(w4[0] if w4 else float('nan')):.4f}@{(w4[1] if w4 else float('nan')):.1f} (max|z| {r4:.4f}) | V282 "
                  f"{(w2[0] if w2 else float('nan')):.4f}@{(w2[1] if w2 else float('nan')):.1f} (max|z| {r2:.4f})")
worst = min(((r[4][0] - r[3][0]) / r[3][0], r) for r in rows if r[4])
print(f"\n  worst relative zeta change of the flexible mode under V294: {worst[0]*100:+.1f} % at mode {worst[1][0]} Hz, J_w/J {worst[1][1]}, zeta {worst[1][2]}")
print(f"  V294 unstable in any case: {any(r[5] >= 1 for r in rows)};  V282 unstable in any case: {any(r[7] >= 1 for r in rows)}")
for d in (0, 1, 3, 5, 8):
    ws = []
    for fmode in (12, 16, 20, 26, 31, 40):
        for rw in (0.2, 0.5, 0.8):
            Jw = rw * J0; Jm = J0 - Jw
            kt = (2 * math.pi * fmode) ** 2 * Jm * Jw / (Jm + Jw)
            ct = 2 * 0.05 * math.sqrt(kt * Jm * Jw / (Jm + Jw))
            gn, gd = two_mass_tf(Jm, Jw, kt, ct, b, k)
            o, _ = flex_mode(cl_modes(gn, gd, None), 0.6 * fmode, 1.6 * fmode)
            w4, r4 = flex_mode(cl_modes(gn, gd, "v294", d=d), 0.5 * fmode, 1.8 * fmode)
            ws.append(((w4[0] - o[0]) / o[0] if w4 else 0.0, fmode, rw, r4))
    wmin = min(ws)
    print(f"  d {d} ticks: worst flexible-mode zeta change under V294 {wmin[0]*100:+.1f} % (mode {wmin[1]} Hz, J_w/J {wmin[2]}); any unstable {any(x[3] >= 1 for x in ws)}")
