"""Outer-loop sensitivity: PM change V293 -> V294 plant over tau, friction slope on/off, k level, J x0.5/1/2, b worlds, speeds.
Second method for stability: closed-loop poles of a rational model (Pade 10 on every delay)."""
import math, itertools
import numpy as np
from scipy import signal
from rp5_outer_loop import L_outer, margins, G_la, lsf, J0, K_ALPHA_U, WP, WO, HOLD_V_BP, HOLD_K_V, G_BP, G_V

LEVEL_BP, LEVEL_V = [12.5, 17.5], [1.15, 1.45]


def pm_first(v, trim, b, k, **kw):
    p, c, f, Lf = margins(v, trim, b, k, **kw)
    worst_pm = min(pm for _, pm in p) if p else 999
    worst_gm = max((g for fc, g in c if fc > 0.05), default=0.0)
    return (p[0] if p else (float('nan'), 999)), worst_pm, worst_gm


rows = []
for v in (3, 5, 8, 12.5, 19, 26, 32):
    for world in ("light", "vlight", "ident", "free0.0009"):
        for kl in ("map", "lev"):
            for jm in (0.5, 1.0, 2.0):
                for tau in (0.015, 0.025, 0.040):
                    for fric in (0.011, 0.0):
                        k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * (float(np.interp(v, LEVEL_BP, LEVEL_V)) if kl == "lev" and v >= 12.5 else 1)
                        b = {"light": 6e-4, "vlight": 3e-4, "ident": 1 / float(np.interp(v, G_BP, G_V)), "free0.0009": 9e-4}[world]
                        kw = dict(J=J0 * jm, tau=tau, fric=fric)
                        a3 = pm_first(v, False, b, k, **kw)
                        a4 = pm_first(v, True, b, k, **kw)
                        rows.append((v, world, kl, jm, tau, fric, a3, a4))

d = [(r[7][1] - r[6][1], r) for r in rows if r[6][1] < 900 and r[7][1] < 900]
d.sort(key=lambda x: x[0])
print("=== the 12 largest PM LOSSES (worst-crossover PM, V294 - V293) ===")
for x, r in d[:12]:
    print(f"  dPM {x:+6.1f} | v {r[0]} {r[1]} k:{r[2]} J x{r[3]} tau {r[4]*1e3:.0f} ms fric {r[5]} | V293 PM {r[6][1]:+.0f} (xover {r[6][0][0]:.2f} Hz) GMinv {r[6][2]:.2f} -> V294 PM {r[7][1]:+.0f} (xover {r[7][0][0]:.2f} Hz) GMinv {r[7][2]:.2f}")
print(f"\n  cases with PM loss > 10 deg: {sum(1 for x, r in d if x < -10)} of {len(d)}; > 5 deg: {sum(1 for x, r in d if x < -5)}")
st3 = sum(1 for r in rows if r[6][1] > 0 and r[6][2] < 1); st4 = sum(1 for r in rows if r[7][1] > 0 and r[7][2] < 1)
print(f"  stable by margins: V293 plant {st3}/{len(rows)}, V294 plant {st4}/{len(rows)}")
flip_bad = [r for r in rows if (r[6][1] > 0 and r[6][2] < 1) and not (r[7][1] > 0 and r[7][2] < 1)]
flip_good = [r for r in rows if not (r[6][1] > 0 and r[6][2] < 1) and (r[7][1] > 0 and r[7][2] < 1)]
print(f"  V293-stable -> V294-unstable: {len(flip_bad)};  V293-unstable -> V294-stable: {len(flip_good)}")
for r in flip_bad[:10]:
    print("    BAD FLIP:", r[:6], r[6], r[7])
print("\n=== median / range of dPM by world at the nominal (map k, J x1, tau 25, fric on) ===")
for world in ("light", "vlight", "free0.0009", "ident"):
    xs = [(r[0], r[7][1] - r[6][1], r[6][1], r[7][1]) for r in rows if r[1] == world and r[2] == "map" and r[3] == 1.0 and r[4] == 0.025 and r[5] == 0.011]
    print(f"  {world:10s}: " + "  ".join(f"{v}:{a:+.0f}({p3:+.0f}->{p4:+.0f})" for v, a, p3, p4 in xs))


# ---- second method: closed-loop poles with Pade delays (nominal cases) ----------------------------------------------
def tf_mul(*tfs):
    n, d = np.array([1.0]), np.array([1.0])
    for a, b in tfs:
        n, d = np.polymul(n, a), np.polymul(d, b)
    return n, d


def pade(t, N=10):
    from scipy.interpolate import pade as _p
    # e^{-st} Taylor in s: coefficients (-t)^k/k!
    c = [(-t) ** k / math.factorial(k) for k in range(2 * N + 1)]
    p, q = _p(c, N)
    return np.array(p.coeffs), np.array(q.coeffs)


def cl_poles(v, trim, b, k, kp=0.9, ki=0.3, laf=14.0, fric=0.011, thr=0.3, tau=0.025, Td=0.003, J=J0):
    ls = lsf(v)
    Kp_eff = (kp + ls) / laf + (fric / thr) * (1 + ls / kp)
    Ki_eff = ki * (1 + ls / kp) / laf
    C = (np.array([Kp_eff, Ki_eff]), np.array([1.0, 0.0]))
    Hout = (np.array([1.0]), np.array([1 / WO, 1.0]))
    Dl = pade(tau + 0.005 + 0.0005, 8)
    if trim:
        tr_n, tr_d = tf_mul((np.array([K_ALPHA_U, 0, 0]), np.array([1.0])), (np.array([1.0]), np.array([1 / WP, 1.0])),
                            (np.array([1.0]), np.array([1 / WO, 1.0])), pade(Td, 3))
        # plant den = (J s^2 + b s + k) * tr_d + tr_n
        pn = tr_d
        pd = np.polyadd(np.polymul([J, b, k], tr_d), tr_n)
    else:
        pn, pd = np.array([1.0]), np.array([J, b, k])
    Ln, Ld = tf_mul(C, (np.array([G_la(v)]), np.array([1.0])), Hout, Dl, (pn, pd))
    return np.roots(np.polyadd(Ld, Ln))


print("\n=== closed-loop poles (Pade): max real part and the worst-damped pair below 10 Hz ===")
for world in ("light", "ident"):
    for v in (3, 5, 8, 12.5, 19, 26):
        k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)); b = 6e-4 if world == "light" else 1 / float(np.interp(v, G_BP, G_V))
        out = []
        for trim in (False, True):
            P = cl_poles(v, trim, b, k)
            pr = [p for p in P if abs(p) < 2 * math.pi * 10 and p.imag > 1e-6]
            wz = min(((-p.real / abs(p), abs(p) / 2 / math.pi) for p in pr), default=(float('nan'), float('nan')))
            out.append((max(P.real), wz))
        print(f"  {world:5s} v {v:5.1f}: V293 max Re {out[0][0]:+8.3f}, worst pair zeta {out[0][1][0]:+.3f} @ {out[0][1][1]:.2f} Hz | "
              f"V294 max Re {out[1][0]:+8.3f}, worst pair zeta {out[1][1][0]:+.3f} @ {out[1][1][1]:.2f} Hz")
