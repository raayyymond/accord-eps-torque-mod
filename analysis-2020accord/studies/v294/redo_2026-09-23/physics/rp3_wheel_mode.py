"""
REDO-PHYSICS claim 3: the trim's closed-loop effect on the wheel mode, EXACT DISCRETE-TIME closed loop at 1 kHz.

Plant (fork units, BELIEF): J th'' + b th' + k(v) th = u,  J = 8e-5 u/(deg/s^2), k(v) = HONDA_ACCORD_HOLD_K_V,
  b light 6e-4 (free fit 5e-4..9e-4 below 15 m/s) or identified 1/G(v).  u -> ZOH at 1 kHz.
Sensor: x[n] = 8 (th[n] - th[n-m]) / (m Ts)   (rate former = a position difference; m = 3 -> 3 ms window, BELIEF)
Trim (EVIDENCE, integer-derived): r26 = g(1-z^-1)/(1-p z^-1) x ; P = -3.75 r26 ; S = 254/256 P ;
  y = g2 (1+z^-1)/(32 (1-p2 z^-1)) S ; T = 5346/32768 y ; u_trim = T / 2625.4 (T counts per fork unit, from the map)
Extra transport delay d ticks (compute + actuator, BELIEF, swept 0..8).
Characteristic: 1 + L(z) = 0, L = -G_th(z) S(z) C(z) z^-d.
"""
import math
import numpy as np
from scipy import signal

TS = 1e-3
T_PER_U = 2625.4
J0 = 8e-5
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]
SPEEDS = [5, 8, 12.5, 19, 26]


def k_of(v):
    return float(np.interp(v, HOLD_V_BP, HOLD_K_V))


def b_ident(v):
    return 1.0 / float(np.interp(v, G_BP, G_V))


def pmul(a, b):
    return np.convolve(a, b)


def trim_tf(a=1011, bb=567, gain=1.0, kp=3.75):
    """controller from x to u_trim, as (num, den) in z^-1 (includes the NEGATIVE sign)."""
    p, g = a / 1024, bb / 1024
    p2, g2 = 992 / 1024, 507 / 1024
    kc = -kp * (254 / 256) * (5346 / 32768) / T_PER_U * gain
    num = kc * g * g2 / 32 * pmul([1, -1], [1, 1])
    den = pmul([1, -p], [1, -p2])
    return num, den


def plant_tf(J, b, k):
    nd, dd, _ = signal.cont2discrete(([1.0], [J, b, k]), TS, method="zoh")
    nd = np.atleast_1d(np.squeeze(nd))
    return nd / dd[0], dd / dd[0]


def sensor_tf(m=3):
    num = np.zeros(m + 1); num[0] = 1; num[m] = -1
    return 8.0 / (m * TS) * num, np.array([1.0])


def loop(J, b, k, d=1, m=3, a=1011, bb=567, gain=1.0, kp=3.75):
    gn, gd = plant_tf(J, b, k)
    sn, sd = sensor_tf(m)
    cn, cd = trim_tf(a, bb, gain, kp)
    dn = np.zeros(d + 1); dn[d] = 1.0
    Ln = -pmul(pmul(pmul(gn, sn), cn), dn)
    Ld = pmul(pmul(gd, sd), cd)
    return Ln, Ld


def closed_poles(Ln, Ld):
    n = max(len(Ln), len(Ld))
    A = np.zeros(n); A[:len(Ld)] += Ld; A[:len(Ln)] += Ln
    return np.roots(A)


def s_of(z):
    s = np.log(z.astype(complex)) / TS
    return s


def mode(poles, fmin=0.2, fmax=6.0):
    """the complex pair in [fmin, fmax] Hz with the lowest damping ratio"""
    best = None
    for z in poles:
        if z.imag <= 1e-9:
            continue
        s = s_of(np.array([z]))[0]
        wn = abs(s); f = wn / (2 * math.pi)
        if fmin <= f <= fmax:
            zeta = -s.real / wn
            if best is None or zeta < best[0]:
                best = (zeta, f, s.imag / (2 * math.pi), -s.real)
    return best


def open_mode(J, b, k):
    wn = math.sqrt(k / J); z = b / (2 * math.sqrt(k * J))
    return z, wn * math.sqrt(max(1 - z * z, 0)) / (2 * math.pi), wn / (2 * math.pi)


def freq(Ln, Ld, f):
    z1 = np.exp(-2j * np.pi * f * TS)
    return np.polyval(Ln[::-1], z1) / np.polyval(Ld[::-1], z1)


def crossings(Ln, Ld, fmin=0.02, fmax=450, n=200000):
    f = np.logspace(math.log10(fmin), math.log10(fmax), n)
    L = freq(Ln, Ld, f)
    ph = np.unwrap(np.angle(L))
    out = []
    # phase crossings of odd multiples of pi (the negative real axis)
    k = np.floor((ph - np.pi) / (2 * np.pi))
    for i in np.where(np.diff(k) != 0)[0]:
        out.append((f[i], abs(L[i]), np.degrees(ph[i])))
    return f, L, out


def nyquist_encircle(Ln, Ld):
    f = np.linspace(1e-4, 499.999, 400000)
    L = freq(Ln, Ld, f)
    w = np.unwrap(np.angle(1 + L))
    return (w[-1] - w[0]) / (2 * np.pi)


if __name__ == "__main__":
    print("=== open-loop wheel mode (fork plant, BELIEF) ===")
    for v in SPEEDS:
        k = k_of(v)
        for bn, b in (("light 6e-4", 6e-4), (f"ident {b_ident(v):.1e}", b_ident(v))):
            z, fd, fn = open_mode(J0, b, k)
            print(f"  v {v:5.1f}  k {k:.5f}  b {bn:14s}: f_n {fn:.2f} Hz, zeta {z:.3f}")

    for world in ("light", "ident"):
        print(f"\n=== zeta ratio (with trim / without) by pole, {world}-b world, d = 1 tick, m = 3; the worst-damped pair in 0.2-6 Hz ===")
        print(" pole     a/b          " + "  ".join(f"{v:>6} m/s" for v in SPEEDS))
        ladder = [("16.5 Hz", 923, None), ("8 Hz", 973, None), ("2.0 Hz", 1011, 567), ("1.4 Hz", 1015, None)]
        for name, a, bb in ladder:
            # hold K_alpha/J = 1 at the BELIEF plant: K_alpha = 3.75*..*(b/1024)*Ts/(1-a/1024)*8 -> choose b
            if bb is None:
                bb = 567 * (1 - a / 1024) / (1 - 1011 / 1024)
            row = []
            for v in SPEEDS:
                k = k_of(v); b = 6e-4 if world == "light" else b_ident(v)
                z0 = open_mode(J0, b, k)[0]
                # the open loop, computed on the same discrete machinery with gain 0, for a like-for-like ratio
                Ln0, Ld0 = loop(J0, b, k, gain=0.0)
                m0 = mode(closed_poles(Ln0, Ld0))
                Ln, Ld = loop(J0, b, k, a=a, bb=bb)
                P = closed_poles(Ln, Ld)
                m1 = mode(P)
                if m0 is None or m1 is None:
                    row.append(("overdamped" if m0 is None else f"z0 {m0[0]:.2f}") + "->" + ("ovd" if m1 is None else f"{m1[0]:.2f}@{m1[1]:.2f}") + ("!" if max(abs(P)) >= 1 else ""))
                else:
                    row.append(f"{m1[0]/m0[0]:6.2f}x@{m1[1]:.2f}Hz" + ("!" if max(abs(P)) >= 1 else ""))
            print(f" {name:7s}  {a}/{bb:7.1f}  " + "  ".join(row))

    print("\n=== shipped (1011/567): absolute zeta, frequency, loop gain, -180 crossings, encirclements; light world ===")
    for world in ("light", "ident"):
        for v in SPEEDS:
            k = k_of(v); b = 6e-4 if world == "light" else b_ident(v)
            Ln0, Ld0 = loop(J0, b, k, gain=0.0); m0 = mode(closed_poles(Ln0, Ld0))
            Ln, Ld = loop(J0, b, k)
            P = closed_poles(Ln, Ld); m1 = mode(P)
            if m0 is None: m0 = (float('nan'),)*4
            if m1 is None: m1 = (float('nan'),)*4
            f, L, cr = crossings(Ln, Ld)
            i24 = np.argmin(abs(f - 2.4)); imax = np.argmax(abs(L))
            enc = nyquist_encircle(Ln, Ld)
            crs = "; ".join(f"{c[0]:.2f} Hz |L| {c[1]:.3f}" for c in cr[:6])
            print(f" {world:5s} v {v:5.1f}: zeta {m0[0]:.3f}@{m0[1]:.2f} -> {m1[0]:.3f}@{m1[1]:.2f} Hz (x{m1[0]/m0[0]:.2f}); max|pole| {max(abs(P)):.5f}; "
                  f"|L|(2.4) {abs(L[i24]):.2f}, max |L| {abs(L[imax]):.2f} @ {f[imax]:.2f} Hz ph {np.degrees(np.angle(L[imax])):.0f}; "
                  f"min Re L {L.real.min():+.3f}; enc(1+L) {enc:+.3f}\n        -180 crossings: {crs}")

    print("\n=== sensitivity: transport delay d (ticks) and rate-former window m; worst zeta ratio over 2..35 m/s, both worlds, K/J 0.5/1/2 ===")
    vs = np.arange(2.0, 35.01, 1.0)
    for d in (0, 1, 2, 3, 5, 8):
        for m in (1, 3):
            worst = (9, None)
            unstable = 0
            for gain in (0.5, 1.0, 2.0):
                for world in ("light", "ident", "vlight2e-4", "heavy6e-3"):
                    for kmul in (0.5, 1.0, 1.45, 2.0):
                        for v in vs:
                            k = k_of(v) * kmul
                            b = {"light": 6e-4, "ident": b_ident(v), "vlight2e-4": 2e-4, "heavy6e-3": 6e-3}[world]
                            Ln0, Ld0 = loop(J0, b, k, d=d, m=m, gain=0.0); m0 = mode(closed_poles(Ln0, Ld0), 0.1, 8)
                            Ln, Ld = loop(J0, b, k, d=d, m=m, gain=gain); P = closed_poles(Ln, Ld)
                            if max(abs(P)) >= 1: unstable += 1
                            m1 = mode(P, 0.1, 8)
                            if m0 is None or m1 is None:
                                continue
                            r = m1[0] / m0[0]
                            if r < worst[0]:
                                worst = (r, (gain, world, kmul, v, m0[0], m1[0], m1[1]))
            print(f"  d {d} m {m}: worst zeta ratio {worst[0]:.3f} at gain/world/kmul/v/z0/z1/f {worst[1]}; unstable closed loops {unstable}")
