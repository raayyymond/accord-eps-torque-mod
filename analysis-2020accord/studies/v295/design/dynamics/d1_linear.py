# -*- coding: utf-8 -*-
"""d1_linear.py -- lens "dynamics": the LINEAR phase/lag study of every knob in the lens (exact 1 kHz z-domain, the
shared harness's own transfer functions, so the lane arithmetic is the golden model's).

Candidate families (CRITERIA-dynamics.md):
  L  output lag 0xC63EC/0xC63EE: pole f_L, a = round(1024 exp(-2 pi f_L Ts)), b = floor(507/512 * 16 * (1024 - a)) so the
     DC gain b/(16(1024-a)) never exceeds V294's 507/512 (the rail must not rise).
  D  Kd flat on all 4 knots + D clamp 10240 + sum clamp 15240 (holds the rail at 2461 with D live).
  A  fb pole 0xC63E8: (i) b held 567, (ii) K_alpha held (b = 567 (1024-a)/13).
Measures (all against V294):
  M1 cmd -> T phase / equivalent delay (ff_tf x 100 Hz ZOH) at 0.5..8 Hz
  M4 trim opposing torque T/omega: magnitude, angle, damping component |.|cos at 2..5 Hz and 13..25 Hz
  M5 |T/x| 5-30 Hz vs V294 and V282; |P(+D)/x| at 20 Hz
  M2 closed-form alpha/cmd (inner trim loop closed) phase and |G| at 0.3..8 Hz, nominal / light_b / J_hi / b_lo
  M3 the fork outer loop (r1) margins, identified + light_b + stress members (stress: the fork sees the WHEEL side)
  M6 stress-mode damping (mode13, mode20, mode20_lo) at 5 / 12 / 25 m/s
  M8 rail / sub-rail slope / int32 / restart pulse (harness m_safe)
Output: d1_linear_out.txt, d1_linear.json
"""
import json
import math
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

TS = 1e-3


def lag_cells(base, fL):
    a = int(round(1024 * math.exp(-2 * math.pi * fL * TS)))
    b = int(math.floor(507.0 / 512.0 * 16 * (1024 - a)))
    return base.replace(lag_a=a, lag_b=b, name="L%.1f" % fL)


def candidates(base):
    C = [base]
    for fL in (6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0):
        C.append(lag_cells(base, fL))
    for kd in (128, 256, 512, 945):
        C.append(base.replace(kd_y=(kd,) * 4, d_clamp=10240, sum_clamp=15240, name="D%d" % kd))
    for a in (1005, 1014, 1017, 1020):
        C.append(base.replace(fb_a=a, name="A%d_bheld" % a))
    for a in (999, 1017):
        b = int(round(567 * (1024 - a) / 13.0))
        C.append(base.replace(fb_a=a, fb_b=b, name="A%d_Kaheld_b%d" % (a, b)))
    return C


def zoh100(f):
    return np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)


def wheel_side(p, f):
    """theta_wheel / theta_motor of the collocated two-mass stress member (1 for rigid)."""
    if p.f2 <= 0:
        return np.ones(len(f), complex)
    s = 2j * np.pi * np.asarray(f, float)
    Jw = p.J * p.r2
    Jm = p.J - Jw
    mu = Jm * Jw / p.J
    K = (2 * np.pi * p.f2) ** 2 * mu
    c = 2 * p.zeta2 * np.sqrt(K * mu)
    return (c * s + K) / (Jw * s * s + c * s + K)


def outer_wheel(c, p, v, f):
    """the harness outer_frf with the fork reading the WHEEL-side angle (stress members); identical for rigid members."""
    Lo = H.outer_frf(c, p, v, f, relay=True)
    return Lo * wheel_side(p, f)


def main():
    out_lines = []
    pr = lambda *a: (print(*a), out_lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base = H.Cells.v294()
    v282 = H.Cells.v282()
    fam = H.family()
    C = candidates(base)
    J = {}
    pr("d1_linear -- lens dynamics.  V294 image %s" % base.image_sha256[:16])
    pr("candidates:")
    for c in C:
        d = c.diff(base)
        pr("   %-18s %s  problems %s  class %s" % (c.name, d, c.problems(), c.edit_class(base)))

    # ---------------- M1 cmd -> T
    fM1 = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
    pr("\nM1  cmd -> T (tap sign), small-signal at idx 60, x 100 Hz ZOH.  |G| T/wire, phase deg, tau_eq ms = -phase/(2 pi f)")
    G0 = H.ff_tf(base, fM1) * zoh100(fM1)
    for c in C:
        G = H.ff_tf(c, fM1) * zoh100(fM1)
        ph = np.degrees(np.angle(G))
        tau = -np.angle(G) / (2 * np.pi * fM1) * 1e3
        pr("   %-18s |G| %s  ph %s  tau_eq %s  dphase vs V294 %s" % (
            c.name, np.round(np.abs(G), 4).tolist(), np.round(ph, 1).tolist(), np.round(tau, 1).tolist(),
            np.round(ph - np.degrees(np.angle(G0)), 1).tolist()))
        J.setdefault(c.name, {})["M1"] = dict(f=fM1.tolist(), G=np.abs(G).tolist(), ph=ph.tolist(), tau_ms=tau.tolist())

    # ---------------- M4 trim T/omega
    fM4 = np.array([1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 13.0, 17.0, 20.0, 25.0])
    pr("\nM4  trim opposing torque T/omega (T per deg/s): |.| @angle (0 = damping, +90 inertia) and damping component |.|cos")
    for c in C:
        To = H.trim_T_per_omega(c, fM4)
        damp = np.abs(To) * np.cos(np.angle(To))
        pr("   %-18s f %s" % (c.name, fM4.tolist()))
        pr("        |T/w|  %s" % np.round(np.abs(To), 3).tolist())
        pr("        angle  %s" % np.round(np.degrees(np.angle(To)), 1).tolist())
        pr("        damp   %s" % np.round(damp, 3).tolist())
        J[c.name]["M4"] = dict(f=fM4.tolist(), mag=np.abs(To).tolist(), ang=np.degrees(np.angle(To)).tolist(), damp=damp.tolist())

    # ---------------- M5 HF controller gain
    fM5 = np.array([5.0, 9.0, 13.0, 17.0, 20.0, 23.0, 25.0, 30.0])
    Tb = np.abs(H.lane_ctf(base, fM5))
    T2 = np.abs(H.lane_ctf(v282, fM5))
    pr("\nM5  |T/x| (T per x count) at %s Hz; ratio vs V294; |P+D/x| at 20 Hz (V294 2.079, V282 44.90)" % fM5.tolist())
    pr("   %-18s |T/x| %s" % ("V282", np.round(T2, 3).tolist()))
    for c in C:
        Tc = np.abs(H.lane_ctf(c, fM5))
        P20 = abs(H.lane_ctf(c, np.array([20.0]), kind="P")[0])
        pr("   %-18s |T/x| %s  xV294 %s  |P/x|20 %.3f  (x V294 %.2f, / V282 %.3f)" % (
            c.name, np.round(Tc, 3).tolist(), np.round(Tc / Tb, 2).tolist(), P20, P20 / 2.0794, P20 / 44.90))
        J[c.name]["M5"] = dict(f=fM5.tolist(), T_per_x=Tc.tolist(), ratio=(Tc / Tb).tolist(), P20=P20)

    # ---------------- M2 closed-form alpha/cmd
    fM2 = np.array([0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
    pr("\nM2  closed-form alpha/cmd (inner trim loop closed): |G| deg/s^2 per count and phase; candidate minus V294")
    for nm in ("nominal", "light_b", "J_hi", "b_lo"):
        for v in (8.0, 12.0, 17.0, 26.9):
            p = fam[nm].at(v)
            a0 = H.alpha_per_cmd(base, p, fM2)
            pr("   %-8s v %4.1f  V294 |G| %s ph %s" % (nm, v, np.round(np.abs(a0), 3).tolist(),
                                                     np.round(np.degrees(np.angle(a0)), 1).tolist()))
            for c in C[1:]:
                a1 = H.alpha_per_cmd(c, p, fM2)
                dph = np.degrees(np.angle(a1 / a0))
                pr("        %-18s ratio %s  dphase %s" % (c.name, np.round(np.abs(a1 / a0), 3).tolist(), np.round(dph, 1).tolist()))
                J[c.name].setdefault("M2", {})["%s|%.1f" % (nm, v)] = dict(ratio=np.abs(a1 / a0).tolist(), dph=dph.tolist())

    # ---------------- M3 outer loop
    ff = np.logspace(-2, np.log10(40.0), 1600)
    pr("\nM3  fork outer loop (r1, relay slope incl.): Ms / PM_min / GM_min per plant x speed (stress: wheel-side angle)")
    for nm in ("nominal", "light_b", "b_lo", "J_hi", "tau6", "mode13", "mode20", "mode20_lo"):
        for v in (5.0, 8.0, 12.0, 17.0, 26.9):
            p = fam[nm].at(v)
            row = []
            for c in C:
                Lo = outer_wheel(c, p, v, ff)
                mg = H.margins(ff, Lo)
                row.append((c.name, mg["Ms"], mg["PM_min"], mg["GM_min"], mg["f_Ms"]))
                J[c.name].setdefault("M3", {})["%s|%.1f" % (nm, v)] = dict(Ms=mg["Ms"], PM=mg["PM_min"], GM=mg["GM_min"],
                                                                          f_Ms=mg["f_Ms"], xover=mg["crossovers_hz"])
            b0 = row[0]
            pr("   %-9s v %4.1f  V294 Ms %.3f@%.2f PM %.1f GM %.2f | " % (nm, v, b0[1], b0[4], b0[2], b0[3]) +
               "  ".join("%s Ms%+.1f%% GM%+.1f%% PM%+.1f" % (r[0], 100 * (r[1] / b0[1] - 1), 100 * (r[3] / b0[3] - 1),
                                                             r[2] - b0[2]) for r in row[1:]))

    # ---------------- M6 stress-mode damping
    pr("\nM6  stress-mode damping (least-damped pair in band): zeta cand (V294, open)")
    for nm, band in (("mode13", (8, 20)), ("mode20", (14, 30)), ("mode20_lo", (14, 30))):
        for v in (5.0, 12.0, 25.0):
            p = fam[nm].at(v)
            (fb_, zb), _ = H.stress_damping(base, p, band)
            (fo, zo), _ = H.stress_damping(base.replace(fb_clamp=0), p, band)
            s = []
            for c in C[1:]:
                (fc, zc), rho = H.stress_damping(c, p, band)
                s.append("%s %.4f" % (c.name, zc))
                J[c.name].setdefault("M6", {})["%s|%.0f" % (nm, v)] = dict(f=fc, zeta=zc, zeta_V294=zb, zeta_open=zo, rho=rho)
            pr("   %-9s v %4.1f  V294 %.1f Hz zeta %.4f  open %.4f | %s" % (nm, v, fb_, zb, zo, "  ".join(s)))

    # ---------------- M8 safety + inner loop
    pr("\nM8  M_SAFE: rail +/-, sub-rail slope, trim cap, int32 min margin, restart peak @10/30/100/300 deg/s; inner M_LOOP worst")
    plants = ("nominal", "b_lo", "F_hi", "J_hi", "light_b", "tau6") + H.STRESS_PLANTS
    for c in C:
        s = H.m_safe(c)
        ml = H.m_loop(c, fam, plants)
        worst_gm = min(x["GM_min"] for x in ml.values())
        worst_ms = max(x["Ms"] for x in ml.values())
        unst = [k for k, x in ml.items() if x["stable"] is not True]
        i32 = min((x["margin"], k) for k, x in s["int32"].items())
        pr("   %-18s rail +%d/%d  subrail %.4f  cap %d  int32 %.2f (%s)  restart %s  | inner GMmin %.1f Msmax %.3f unstable %s" % (
            c.name, s["rail_pos"], s["rail_neg"], s["subrail_T_per_wire"], s["trim_cap_T"], i32[0], i32[1],
            [v["peak"] for v in s["restart"].values()], worst_gm, worst_ms, unst))
        J[c.name]["M8"] = dict(rail_pos=s["rail_pos"], rail_neg=s["rail_neg"], subrail=s["subrail_T_per_wire"], cap=s["trim_cap_T"],
                               int32=i32[0], restart=[v["peak"] for v in s["restart"].values()],
                               restart_ms50=[v["ms_above_50"] for v in s["restart"].values()],
                               inner_GM_min=worst_gm, inner_Ms_max=worst_ms, unstable=[str(u) for u in unst])
    json.dump(H.to_jsonable(J), open(os.path.join(HERE, "d1_linear.json"), "w"), indent=1)
    open(os.path.join(HERE, "d1_linear_out.txt"), "w").write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    main()
