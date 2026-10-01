# -*- coding: utf-8 -*-
"""REFUTER: high-frequency (5-30 Hz) damping and flexible / hands-on modes.  Independent of the design's harnesses.
Controllers:
  C0      angle loop as in stab_lin (E' = E*G>>8, P 450, Ki 199, D = -16*rate_held)
  V295    rate loop: x = 8*omega_held, s_new = (1011*s_old + 1050*x)/1024, r26 = s_new - s_old, P = -r26*960/256
  V294    same with b = 567
  V282    x as above, s_new = (923 s_old + 1560 x)/1024, r26 = s_new + s_old, E = -r26*?  (sum), P = E*248/256,
          D = 128/8*(E - E_prev)            (positive control: V282 GROUND at 17-21 Hz on the car)
All share: fade 254/256, output lag 992/507, forward 5346/32768, transport d ticks, 100 Hz hold (slot 4 on n%10==4).
"""
import sys, math
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import v294_plant as VP

TS = S.TS
fam = VP.family()


class Rate:
    def __init__(self, name, a, b, op, kp, kd=0, d=2):
        self.name, self.a, self.b, self.op, self.kp, self.kd, self.d = name, a, b, op, kp, kd, d


V295 = Rate("V295", 1011, 1050, "diff", 960)
V294 = Rate("V294", 1011, 567, "diff", 960)
V282 = Rate("V282", 923, 1560, "sum", 248, kd=128)


def torque_per_rate(ctl, f, rate_delay_ms=0.0):
    """T counts (u, + along error) per deg/s of wheel rate at f, LTI fundamental (hold included). Re > 0 = damping."""
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** a for a in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** ctl.d
    w = 2 * np.pi * f
    rd = np.exp(-1j * w * rate_delay_ms * 1e-3)
    if isinstance(ctl, S.Ctl):
        g = ctl.G / 256
        PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
        Cth = g * PI * 80 * (1 + zi) * hold          # per deg of theta
        Cw = ctl.kd * hold * rd                        # per deg/s
        return K * (Cth / (1j * w) + Cw)
    R = (ctl.b / 1024) * (1 + (zi if ctl.op == "sum" else -zi)) / (1 - (ctl.a / 1024) * zi)
    g = ctl.kp / 256 + (ctl.kd / 8) * (1 - zi)
    return K * g * R * 8 * hold * rd


def phase_mats_rate(ctl, plant, gain=1.0):
    """exact periodic state space for a RATE-operand lane (V294/V295/V282). state: xp, ubuf, o_prev, s, Eprev, w_h."""
    A, B, Ct, Cw = plant
    Ad, Bd = S.c2d(A, B)
    npl = Ad.shape[0]; d = ctl.d
    ip = 0; iu = npl; io = npl + d; isx = io + 1; iE = isx + 1; iw = iE + 1
    N = iw + 1
    mats = []
    for p in range(10):
        M = np.zeros((N, N))
        row = lambda: np.zeros(N)  # noqa: E731
        x = row(); x[iw] = 8.0
        s_old = row(); s_old[isx] = 1
        s_new = (ctl.a / 1024) * s_old + (ctl.b / 1024) * x
        r26 = s_new + s_old if ctl.op == "sum" else s_new - s_old
        E = -r26
        P = E * ctl.kp / 256
        Eprev = row(); Eprev[iE] = 1
        D = (ctl.kd / 8) * (E - Eprev)
        Sx = P + D
        Sf = S.FADE * Sx
        o_prev = row(); o_prev[io] = 1
        o_new = (S.OA / 1024) * o_prev + (S.OB / 1024) * Sf
        y = (o_prev + o_new) / 32
        ucmd = gain * S.FWD * y
        if d == 0:
            uin = ucmd
        else:
            uin = row(); uin[iu + d - 1] = 1
        M[ip:ip + npl, ip:ip + npl] = Ad
        M[ip:ip + npl, :] += np.outer(Bd[:, 0], uin)
        if d > 0:
            M[iu, :] = ucmd
            for i in range(1, d):
                M[iu + i, iu + i - 1] = 1
        M[io, :] = o_new
        M[isx, :] = s_new
        M[iE, :] = E
        w_now = np.zeros(N); w_now[ip:ip + npl] = Cw[0]
        if p == S.HOLD_PHASE:
            M[iw, :] = w_now
        else:
            M[iw, iw] = 1
        mats.append(M)
    return mats


def exact_any(ctl, plant):
    mats = phase_mats_rate(ctl, plant) if isinstance(ctl, Rate) else S.phase_mats(ctl, plant)
    Phi = np.eye(mats[0].shape[0])
    for M in mats:
        Phi = M @ Phi
    lam = np.linalg.eigvals(Phi)
    rho = float(np.max(np.abs(lam)))
    hf = []
    for l in lam:
        if abs(l) < 1e-12:
            continue
        s = np.log(l + 0j) / (10 * TS)
        fhz = abs(s.imag) / (2 * np.pi)
        if 4.0 <= fhz <= 50.0:
            hf.append((fhz, -s.real / abs(s)))
    hf.sort(key=lambda t: t[1])
    return rho, hf


def sec(t):
    print("\n" + "=" * 110 + "\n" + t + "\n" + "=" * 110)


if __name__ == "__main__":
    sec("A. TORQUE PER UNIT WHEEL RATE (T counts per deg/s), Re (>0 damps, <0 ANTI-damps) | magnitude; hold included, d=2")
    freqs = (5, 7, 10, 13, 15, 16, 17, 20, 24, 30)
    print("ctl            " + "".join(f"{f:>15d}" for f in freqs))
    ctls = [V294, V295, V282] + [S.Ctl(v, d=2) for v in (3, 8, 12.5, 19, 26, 30)]
    for c in ctls:
        nm = c.name if isinstance(c, Rate) else f"C0@{c.v:g}"
        vals = [torque_per_rate(c, f) for f in freqs]
        print(f"{nm:14s} " + "".join(f"{v.real:+7.2f}|{abs(v):6.2f} " for v in vals))
    print("\n  same, with an extra 1.5 ms on the rate former (the 3 ms difference's centre; BELIEF):")
    for c in [S.Ctl(v, d=2) for v in (3, 12.5, 26)]:
        vals = [torque_per_rate(c, f, 1.5) for f in freqs]
        print(f"C0@{c.v:<11g} " + "".join(f"{v.real:+7.2f}|{abs(v):6.2f} " for v in vals))

    sec("B. COLLOCATED TWO-MASS, HANDS OFF: wheel on the torsion bar at fz (motor-side sensor). Unstable count and least "
        "HF zeta, C0 per speed vs V294/V295/V282")
    out = {}
    rows = []
    for v in (3, 8, 12.5, 19, 26):
        p = fam["nominal"].at(v)
        for fz in (10.0, 13.0, 16.0, 20.0):
            for r2 in (0.1, 0.2, 0.3, 0.5):
                for zw in (0.01, 0.02, 0.05):
                    pl = S.two_mass(p.J, p.b, p.k, r2, fz, zw)
                    res = {}
                    for c in (S.Ctl(v, d=2), V294, V295, V282):
                        nm = c.name if isinstance(c, Rate) else "C0"
                        rho, hf = exact_any(c, pl)
                        res[nm] = (rho, hf[0] if hf else (float('nan'), float('nan')))
                        out.setdefault(nm, []).append(rho >= 1)
                    rows.append((v, fz, r2, zw, res))
    for nm, l in out.items():
        print(f"  {nm}: unstable {sum(l)}/{len(l)}")
    # worst C0 rows vs the references on the same plant
    rows.sort(key=lambda r: r[4]["C0"][1][1])
    print("  ten least-damped C0 rows (v, fz, r2, zeta_w): C0 (f, zeta) | V294 | V295 | V282")
    for v, fz, r2, zw, res in rows[:10]:
        print(f"   v {v:4g} fz {fz:4g} r2 {r2:.1f} zw {zw:.2f}: C0 {res['C0'][1][0]:5.1f}Hz z{res['C0'][1][1]:+.4f} rho {res['C0'][0]:.4f}"
              f" | V294 z{res['V294'][1][1]:+.4f} | V295 z{res['V295'][1][1]:+.4f} | V282 z{res['V282'][1][1]:+.4f} rho {res['V282'][0]:.4f}")
    # rows where C0 is less damped than V295 on the same plant
    worse = [r for r in rows if r[4]["C0"][1][1] < r[4]["V295"][1][1] - 1e-4]
    print(f"  rows where C0's least-damped HF pole is LESS damped than V295's on the same plant: {len(worse)}/{len(rows)}")
    worse94 = [r for r in rows if r[4]["C0"][1][1] < r[4]["V294"][1][1] - 1e-4]
    print(f"  ... than V294's: {len(worse94)}/{len(rows)}")

    sec("C. HANDS ON: arms add inertia J_arm = alpha*Jw and damping zeta_arm on the wheel side (fz 13 Hz hands-off). "
        "C0 vs V294/V295; exact")
    rows = []
    for v in (3, 8, 12.5, 19, 26, 30):
        p = fam["nominal"].at(v)
        for r2 in (0.1, 0.2, 0.3):
            for alpha in (1.0, 2.0, 3.0, 5.0):
                for za in (0.02, 0.05, 0.1, 0.2):
                    pl = S.two_mass(p.J, p.b, p.k, r2, 13.0, 0.02, J_arm_ratio=alpha, zeta_arm=za)
                    res = {}
                    for c in (S.Ctl(v, d=2), V294, V295):
                        nm = c.name if isinstance(c, Rate) else "C0"
                        rho, hf = exact_any(c, pl)
                        res[nm] = (rho, hf[0] if hf else (float('nan'), float('nan')))
                    fmode = 13.0 / math.sqrt(1 + alpha)
                    rows.append((v, r2, alpha, za, fmode, res))
    nun = sum(1 for r in rows if r[5]["C0"][0] >= 1)
    print(f"  C0 unstable {nun}/{len(rows)}; V294 {sum(1 for r in rows if r[5]['V294'][0] >= 1)}; "
          f"V295 {sum(1 for r in rows if r[5]['V295'][0] >= 1)}")
    rows.sort(key=lambda r: r[5]["C0"][1][1])
    for v, r2, alpha, za, fm, res in rows[:12]:
        print(f"   v {v:4g} r2 {r2:.1f} alpha {alpha:g} (mode ~{fm:.1f} Hz) zeta_arm {za:.2f}: C0 {res['C0'][1][0]:5.1f}Hz "
              f"z{res['C0'][1][1]:+.4f} rho {res['C0'][0]:.4f} | V294 z{res['V294'][1][1]:+.4f} | V295 z{res['V295'][1][1]:+.4f}")
