# -*- coding: utf-8 -*-
"""s1_plane.py -- trim-ratio lens: map the (loop gain, pole) plane LINEARLY on the whole plant family.

Axes
  a      fb-lag pole cell 0xC63E8 (pole = -ln(a/1024)/(2 pi 1 ms))
  G      the trim's HIGH-FREQUENCY gain relative to V294 = (Kp * b) / (960 * 567).  Above the pole the trim is a damper
         B_inf = G * 2.66 T per deg/s (census); below it an inertia K_alpha = G * 0.210 * 13 / (1024 - a) T per deg/s^2.
         The static FF is held byte-identical by Kp * 2^shift = 3840 (shift 2 -> Kp 960, shift 1 -> Kp 1920, shift 0 -> Kp 3840).
  realisation: the LEAST code change that keeps every int32 margin >= 2 (b <= b_max / 2): shift 2 if possible, else 1, else 0.
  C = 983040 / Kp (the trim cap held at V294's 616 delivered T counts).

Per point (all LINEAR, exact 1 kHz z-domain; harness functions):
  K_alpha, T/omega at 1 / 2 / 2.5 / 3 Hz (damping = Re, inertia = Im/omega), |T/x| 10-25 Hz vs V294,
  inner M_LOOP on the family (Ms, GM, |L| 1-3 Hz, the least-damped closed-loop wheel mode 0.3-8 Hz),
  stress-member flexible-mode zeta (mode13 / mode20 / mode20_lo at 5 / 12 / 25 m/s) vs V294 and open,
  OUTER loop (fork r1 linearised, relay on and off) GM / Ms on nominal, b_lo, J_hi, light_b at 5 / 8 / 12 / 17 / 26.9 m/s,
  closed-form |alpha/cmd| at 0.3-5 Hz (flatness = max/min over 0.5-3 Hz).
Writes s1_plane.json and prints a table.  Analysis only.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
FAM = H.family()


def pole_hz(a):
    return -math.log(a / 1024.0) / (2 * math.pi * 1e-3)


def realise(a, G, cap_T_equiv=True, margin=2.0):
    """cells for (a, G) with the static FF byte-identical: returns Cells or None if no shift fits."""
    for sh in (2, 1, 0):
        kp = 3840 >> sh
        b = int(round(G * 567 * 960 / kp))
        bmax = (2 ** 31) * (1024 - a) / (12000.0 * a)
        if b <= bmax / margin and b <= 65535:
            C = int(round(983040 / kp)) if cap_T_equiv else 1024
            return BASE.replace(name="a%d_G%.2f" % (a, G), fb_a=a, fb_b=b, e_shift=sh, kp_y=(kp,) * 5, fb_clamp=C)
    return None


def trim_stats(c):
    f = np.array([0.5, 1.0, 2.0, 2.5, 3.0])
    Tw = H.trim_T_per_omega(c, f)
    w = 2 * np.pi * f
    out = {}
    for fi, t, wi in zip(f, Tw, w):
        out["damp_%.1f" % fi] = float(t.real)               # T per deg/s in phase with rate (opposing)
        out["iner_%.1f" % fi] = float(t.imag / wi)          # T per deg/s^2
    # K_alpha from the closed form at 0.05 Hz
    t0 = H.trim_T_per_omega(c, np.array([0.05]))[0]
    out["K_alpha"] = float(t0.imag / (2 * np.pi * 0.05))
    fh = np.array([10.0, 13.0, 17.0, 20.0, 25.0])
    r = np.abs(H.lane_ctf(c, fh)) / np.abs(H.lane_ctf(BASE, fh))
    out["HF_x_V294"] = r.tolist()
    out["HF_max_x"] = float(r.max())
    out["P_per_x_20"] = float(abs(H.lane_ctf(c, np.array([20.0]), kind="P")[0]))
    return out


def inner(c, members=("nominal", "b_lo", "J_lo", "J_hi", "J_hi2", "light_b", "tau6", "tau9"),
          speeds=(3.1, 8.0, 12.0, 17.0, 26.9)):
    fg = np.logspace(-1, np.log10(45.0), 900)
    worst = dict(Ms=0.0, GM=1e9, Ms15=0.0, rho=0.0, zmin=1.0, L13max=0.0)
    per = {}
    for nm in members:
        for v in speeds:
            p = FAM[nm].at(v)
            L = H.loop_frf(c, p, fg)
            mg = H.margins(fg, L)
            L15 = H.loop_frf(c, H.replace(p, tau_ms=int(round(max(p.tau_ms, 2) * 1.5))), fg)
            mg15 = H.margins(fg, L15)
            md, rho = H.closed_loop_modes(p, c)
            osc = [(f, z) for f, z in md if 0.3 < f < 8.0]
            zmin = min([z for _, z in osc], default=1.0)
            L13 = float(np.mean(np.abs(L[(fg > 1) & (fg < 3)])))
            per["%s@%.1f" % (nm, v)] = dict(Ms=mg["Ms"], GM=mg["GM_min"], Ms15=mg15["Ms"], rho=rho, zmin=zmin,
                                           modes=[(round(f, 2), round(z, 3)) for f, z in osc], L13=L13)
            worst["Ms"] = max(worst["Ms"], mg["Ms"])
            worst["GM"] = min(worst["GM"], mg["GM_min"])
            worst["Ms15"] = max(worst["Ms15"], mg15["Ms"])
            worst["rho"] = max(worst["rho"], rho)
            worst["zmin"] = min(worst["zmin"], zmin)
            worst["L13max"] = max(worst["L13max"], L13)
    return worst, per


def stress(c):
    out = {}
    worst = 1e9
    for nm, band in (("mode13", (8, 20)), ("mode20", (14, 30)), ("mode20_lo", (14, 30))):
        for v in (5.0, 12.0, 25.0):
            p = FAM[nm].at(v)
            (fc, zc), rc = H.stress_damping(c, p, band)
            (fb_, zb), _ = H.stress_damping(BASE, p, band)
            (fo, zo), _ = H.stress_damping(c.replace(fb_clamp=0), p, band)
            out["%s@%.0f" % (nm, v)] = dict(f=fc, zeta=zc, zeta_V294=zb, zeta_open=zo, rho=rc)
            worst = min(worst, zc - min(zb, zo))
    return worst, out


def outer(c, members=("nominal", "b_lo", "J_hi", "light_b"), speeds=(5.0, 8.0, 12.0, 17.0, 26.9)):
    ff = np.logspace(-2, np.log10(20.0), 700)
    out = {}
    for nm in members:
        for v in speeds:
            p = FAM[nm].at(v)
            for relay in (True, False):
                Lo = H.outer_frf(c, p, v, ff, relay=relay)
                mg = H.margins(ff, Lo)
                out["%s@%.1f@%s" % (nm, v, "R" if relay else "n")] = dict(GM=mg["GM_min"], Ms=mg["Ms"], PM=mg["PM_min"],
                                                                         xover=mg["crossovers_hz"][:2])
    return out


def track(c, members=("nominal", "light_b", "b_lo", "J_hi"), speeds=(8.0, 12.0, 17.0, 26.9)):
    f = np.array([0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0])
    out = {}
    for nm in members:
        for v in speeds:
            A = H.alpha_per_cmd(c, FAM[nm].at(v), f)
            g = np.abs(A)
            m = (f >= 0.5) & (f <= 3.0)
            out["%s@%.1f" % (nm, v)] = dict(G=g.tolist(), ph=np.degrees(np.angle(A)).tolist(),
                                          flat=float(g[m].max() / g[m].min()),
                                          phspan=float(np.ptp(np.unwrap(np.angle(A[m])) * 180 / np.pi)))
    return out


def evaluate(c):
    r = dict(name=c.name, a=c.fb_a, pole_hz=pole_hz(c.fb_a), b=c.fb_b, shift=c.e_shift, kp=c.kp_y[0], C=c.fb_clamp,
             G=c.kp_y[0] * c.fb_b / (960.0 * 567.0), b_over_bmax=c.fb_b / c.b_max, problems=c.problems())
    r.update(trim_stats(c))
    r["inner_worst"], r["inner"] = inner(c)
    r["stress_worst"], r["stress"] = stress(c)
    r["outer"] = outer(c)
    r["track"] = track(c)
    return r


def main():
    t0 = time.time()
    res = [evaluate(BASE.replace(name="V294"))]
    base_outer = res[0]["outer"]
    for a in (993, 1000, 1005, 1008, 1011, 1014, 1016, 1017, 1018, 1019, 1020):
        for G in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
            c = realise(a, G)
            if c is None:
                continue
            if a == 1011 and G == 1.0:
                continue
            res.append(evaluate(c))
            print("   %.0f s  %s" % (time.time() - t0, c.name), flush=True)
    json.dump(H.to_jsonable(res), open(os.path.join(HERE, "s1_plane.json"), "w"), indent=0)
    print("\n%-14s %5s %5s %2s %5s %5s | %6s %6s %6s %6s | %5s %5s | %5s %5s %5s %6s | %6s | %6s %6s %6s %6s | %5s %5s" % (
        "cand", "pole", "b", "sh", "Kp", "C", "Ka", "d2.0", "d2.5", "i2.5", "HFx", "P/x20", "Msin", "GMin", "zmin",
        "L13mx", "stress", "oGMlb17", "oGMlb27", "oMsNom", "oGMnom", "flatN12", "flatLb12"))
    for r in res:
        o = r["outer"]
        gm_lb17 = min(o["light_b@17.0@R"]["GM"], o["light_b@17.0@n"]["GM"])
        gm_lb27 = min(o["light_b@26.9@R"]["GM"], o["light_b@26.9@n"]["GM"])
        ms_nom = max(v["Ms"] for k, v in o.items() if not k.startswith("light_b"))
        gm_nom = min(v["GM"] for k, v in o.items() if not k.startswith("light_b"))
        print("%-14s %5.2f %5d %2d %5d %5d | %6.3f %6.2f %6.2f %6.3f | %5.2f %5.2f | %5.2f %5.1f %5.2f %6.2f | %+6.3f | %6.2f %6.2f %6.2f %6.1f | %5.2f %5.2f" % (
            r["name"], r["pole_hz"], r["b"], r["shift"], r["kp"], r["C"], r["K_alpha"], r["damp_2.0"], r["damp_2.5"],
            r["iner_2.5"], r["HF_max_x"], r["P_per_x_20"], r["inner_worst"]["Ms15"], r["inner_worst"]["GM"],
            r["inner_worst"]["zmin"], r["inner_worst"]["L13max"], r["stress_worst"], gm_lb17, gm_lb27, ms_nom, gm_nom,
            r["track"]["nominal@12.0"]["flat"], r["track"]["light_b@12.0"]["flat"]))
    print("total %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
