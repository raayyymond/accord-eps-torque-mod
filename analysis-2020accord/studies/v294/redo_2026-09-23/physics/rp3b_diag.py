"""Diagnostics for the zeta ratio: exact discrete poles vs a continuous 4th-order model vs the perturbation
formula zeta_eff = b_eff / (2 sqrt(k J_eff)) evaluated at a frequency. Light-b world, shipped 1011/567."""
import math
import numpy as np
from rp3_wheel_mode import *

K_alpha_u = 0.20974 / T_PER_U       # u per deg/s^2 below the pole
wp = -math.log(1011 / 1024) / TS
wo = -math.log(992 / 1024) / TS
print(f"K_alpha_u = {K_alpha_u:.4e}; wp = {wp:.3f} rad/s ({wp/2/math.pi:.3f} Hz); wo = {wo:.3f} rad/s ({wo/2/math.pi:.3f} Hz)")


def H(w, d_s=0.0):  # normalised alpha->T lag: two first-order lags (DC 1) and a delay
    s = 1j * w
    return 1 / (1 + s / wp) / (1 + s / wo) * np.exp(-s * d_s)


print("\n v    open: zeta f_n | exact-discrete: all complex pairs < 10 Hz (zeta, f_n) | continuous 4th-order roots | perturbation @f_open, @f_closed")
for v in SPEEDS:
    k = k_of(v); b = 6e-4; J = J0
    z0, fd0, fn0 = open_mode(J, b, k)
    Ln, Ld = loop(J, b, k)
    P = closed_poles(Ln, Ld)
    S = s_of(P)
    pairs = sorted([(-s.real / abs(s), abs(s) / 2 / math.pi, s.imag / 2 / math.pi) for s in S if s.imag > 1e-6 and abs(s) / 2 / math.pi < 10])
    reals = sorted([s.real / 2 / math.pi for s in S if abs(s.imag) <= 1e-6 and abs(s) / 2 / math.pi < 10])
    # continuous: (J s^2 + b s + k)(1 + s/wp)(1 + s/wo) + K s^2 = 0  (no delay)
    c = np.polymul(np.polymul([J, b, k], [1 / wp, 1]), [1 / wo, 1]) + np.array([0, 0, K_alpha_u, 0, 0])
    rc = np.roots(c)
    cp = sorted([(-r.real / abs(r), abs(r) / 2 / math.pi) for r in rc if r.imag > 1e-9])
    crl = sorted([r.real / 2 / math.pi for r in rc if abs(r.imag) <= 1e-9])
    # perturbation formula
    def pert(w):
        h = H(w)
        Je = J + K_alpha_u * h.real
        be = b - K_alpha_u * w * h.imag
        return be / (2 * math.sqrt(k * Je)), Je / J, be / b
    pa = pert(2 * math.pi * fn0)
    pb = pert(2 * math.pi * (pairs[0][1] if pairs else fn0))
    print(f"{v:5.1f}  {z0:.3f} {fn0:.2f} | {[(round(a,3), round(bb_,2)) for a, bb_, _ in pairs]} reals(Hz) {[round(r,2) for r in reals]}"
          f" | cont {[(round(a,3), round(bb_,2)) for a, bb_ in cp]} reals {[round(r,2) for r in crl]}"
          f" | pert@open zeta {pa[0]:.3f} (x{pa[0]/z0:.2f}; Je/J {pa[1]:.2f}, be/b {pa[2]:.2f})  pert@closed x{pb[0]/z0:.2f}")
