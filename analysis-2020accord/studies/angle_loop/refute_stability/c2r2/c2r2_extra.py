# -*- coding: utf-8 -*-
"""c2r2_extra.py -- the rest of the stability lens on P2, F2, D2a, B0r:
  E1  Re(T/omega) 5-25 Hz, worst over 1..35 m/s, hold ages 1-10 / 11-20 / 0-9, transport 2 and 6 ms, vs V294/V295;
      sensitivities: rate-former delay +0.5 / +1 tick on the D operand, D gain x0.866 / x1.04 (the gp-0x6a00 frame
      correction slope 1.155 near centre .. 0.962 outward vs the linear-frame rate)
  E2  M20 and the 20 Hz loop gain vs V295
  E3  two-mass stress: f2 13/15/16.5/17/20/22 Hz, zeta2 0.02/0.05, r2 0.2/0.4, BOTH placement conventions
      ('mu' = free-free resonance at f2, the gate's; 'jw' = wheel-side anti-resonance at f2), on nominal / b_lo / b_q /
      J_hi, ages 1-10 and 11-20, every 1 m/s; EXACT rho + least-damped pole + LTI PM + |Tc| 5-30 Hz peak
  E4  the fork outer-loop stand-in L_o = Tref e^{-0.06 s} / (tau_o s), tau_o 0.3/0.5/1/2 s, on every gated member
  E5  light_b (prior, report only)
Writes _scratch/angle_loop/refute-c2r2-stability/extra_*.json and prints the tables.  ANALYSIS ONLY."""
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402
import c2r2_sweep as SW  # noqa: E402

OUT = SW.OUT
D = M.load_designs()
DES = ["P2", "F2", "D2a", "B0r"]
GRID = [round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]
F = np.array([5, 6, 7, 8, 10, 13, 15, 16, 17, 20, 25.0])


def E1():
    print("== E1 Re(T/omega) worst (min) over 1..35 m/s, T counts per deg/s (>0 damps); ratio = design / V295 where V295 < 0")
    rows = {}
    for d in (2, 6):
        for ea in (0, 10, -1):
            ref = {nm: M.re_t_over_w(r, 10.0, F, ea, d=d) for nm, r in (("V295", M.V295_REF), ("V294", M.V294_REF))}
            for nm in ("V294", "V295"):
                rows[(nm, d, ea, "base")] = ref[nm]
            for dn in DES:
                for var, kw in (("base", {}), ("rf+0.5", dict(ddelay=0.5)), ("rf+1", dict(ddelay=1.0)),
                                ("kd*0.866", dict(kd_scale=0.866)), ("kd*1.04", dict(kd_scale=1.04))):
                    w = np.full(len(F), 1e9)
                    arg = np.full(len(F), np.nan)
                    for v in GRID:
                        x = M.re_t_over_w(D[dn], v, F, ea, d=d, **kw)
                        upd = x < w
                        arg = np.where(upd, v, arg)
                        w = np.minimum(w, x)
                    rows[(dn, d, ea, var)] = w
                    rows[(dn, d, ea, var, "v")] = arg
    hdr = "        " + " ".join(f"{f:>6.0f}" for f in F)
    for d in (2, 6):
        for ea in (0, 10, -1):
            tag = {0: "ages 1-10", 10: "ages 11-20", -1: "ages 0-9"}[ea]
            print(f"-- transport {d} ms, {tag}\n{hdr}")
            v295 = rows[("V295", d, ea, "base")]
            for nm in ("V294", "V295"):
                print(f"  {nm:14s}" + " ".join(f"{x:+6.2f}" for x in rows[(nm, d, ea, 'base')]))
            for dn in DES:
                for var in ("base", "rf+0.5", "rf+1", "kd*0.866", "kd*1.04"):
                    w = rows[(dn, d, ea, var)]
                    rat = np.where(v295 < 0, w / v295, np.nan)
                    print(f"  {dn + ' ' + var:14s}" + " ".join(f"{x:+6.2f}" for x in w) + "   x V295: " +
                          " ".join("  --  " if not np.isfinite(r) else f"{r:6.2f}" for r in rat))
                print(f"  {'  @v (m/s)':14s}" + " ".join(f"{x:6.2f}" for x in rows[(dn, d, ea, 'base', 'v')]))
    json.dump({"|".join(map(str, k)): list(map(float, v)) for k, v in rows.items()}, open(OUT / "extra_E1.json", "w"))


def E2():
    print("\n== E2 M20 (lane S counts per x count at 20 Hz) and L20 vs V295 (nominal, worst over speed)")
    f = M.FG
    for dn in ["V295", "V294"] + DES:
        des = {"V295": M.V295_REF, "V294": M.V294_REF}.get(dn, D.get(dn))
        m20 = []
        for v in GRID:
            r, _ = M.lti_metrics(des, M.member("nominal", v), v)
            m20.append(r["M20"])
        print(f"  {dn:5s} M20 max {max(m20):.3f}  min {min(m20):.3f}")


def _stress(args):
    dn, base, conv, f2, z2, r2, ea, v = args
    pl = M.member(base, v)
    pl.f2, pl.z2, pl.r2, pl.conv, pl.ea = f2, z2, r2, conv, ea
    r, _ = M.lti_metrics(D[dn], pl, v)
    rho, z, fp, lam = M.Periodic(D[dn], pl, v).rho_poles()
    # least-damped pole in 5-50 Hz specifically
    lam_nz = lam[np.abs(lam) > 1e-9]
    s = np.log(lam_nz.astype(complex)) / 0.01
    ff = np.abs(s.imag) / (2 * np.pi)
    zz = -s.real / np.maximum(np.abs(s), 1e-12)
    sel = (ff > 5) & (ff < 49.9)
    j = int(np.argmin(np.where(sel, zz, 9))) if sel.any() else None
    return dict(d=dn, base=base, conv=conv, f2=f2, z2=z2, r2=r2, ea=ea, v=v, rho=rho, pm=r["pm"], Tc530=r["Tc530"],
                Tr530=r["Tr530"], z_hf=(float(zz[j]) if j is not None else None),
                f_hf=(float(ff[j]) if j is not None else None))


def E3():
    print("\n== E3 two-mass stress (EXACT rho; least-damped 5-50 Hz closed-loop pole)")
    jobs = []
    for dn in DES:
        for base in ("nominal", "b_lo", "b_q", "J_hi"):
            for conv in ("mu", "jw"):
                for f2 in (13.0, 15.0, 16.5, 17.0, 20.0, 22.0):
                    for z2 in (0.02, 0.05):
                        for r2 in (0.2, 0.4):
                            for ea in (0, 10):
                                for v in range(1, 36, 2):
                                    jobs.append((dn, base, conv, f2, z2, r2, ea, float(v)))
    t0 = time.time()
    with Pool(6) as p:
        res = p.map(_stress, jobs, chunksize=32)
    json.dump(res, open(OUT / "extra_E3.json", "w"))
    print(f"  {len(res)} points [{time.time() - t0:.0f}s]")
    for dn in DES:
        rr = [r for r in res if r["d"] == dn]
        unst = [r for r in rr if r["rho"] >= 1]
        zmin = min((r for r in rr if r["z_hf"] is not None), key=lambda r: r["z_hf"])
        pk = max(rr, key=lambda r: max(r["Tc530"], r["Tr530"]))
        pmmin = min((r for r in rr if np.isfinite(r["pm"])), key=lambda r: r["pm"])
        print(f"  {dn:4s} unstable {len(unst)}/{len(rr)}  min PM {pmmin['pm']:.1f} ({pmmin['base']} {pmmin['conv']} "
              f"f2 {pmmin['f2']} z {pmmin['z2']} r2 {pmmin['r2']} ea {pmmin['ea']} v {pmmin['v']})")
        print(f"       least-damped 5-50 Hz pole: {zmin['f_hf']:.2f} Hz zeta {zmin['z_hf']:.4f} ({zmin['base']} {zmin['conv']} "
              f"f2 {zmin['f2']} z2 {zmin['z2']} r2 {zmin['r2']} ea {zmin['ea']} v {zmin['v']})")
        print(f"       max |Tc|,|Tref| 5-30 Hz: {max(pk['Tc530'], pk['Tr530']):+.1f} dB ({pk['base']} {pk['conv']} f2 {pk['f2']} "
              f"z2 {pk['z2']} r2 {pk['r2']} ea {pk['ea']} v {pk['v']})")
        for conv in ("mu", "jw"):
            for z2 in (0.02, 0.05):
                sub = [r for r in rr if r["conv"] == conv and r["z2"] == z2 and r["z_hf"] is not None]
                w = min(sub, key=lambda r: r["z_hf"] / r["z2"] if r["z2"] else 9)
                print(f"       {conv} z2 {z2}: worst closed/open zeta ratio {w['z_hf'] / w['z2']:.2f} at f2 {w['f2']} "
                      f"(pole {w['f_hf']:.2f} Hz z {w['z_hf']:.4f}, {w['base']} r2 {w['r2']} ea {w['ea']} v {w['v']})")


def E4():
    print("\n== E4 fork outer-loop stand-in L_o = Tref e^-0.06s/(tau_o s): worst PM / GM over gated members and speeds")
    f = M.FG
    gated = SW.SINGLE + SW.COMBINED
    gated = gated + [m + "+h10" for m in gated]
    s = 2j * np.pi * f
    for dn in DES:
        for tau_o in (0.3, 0.5, 1.0, 2.0):
            worst_pm = (1e9, None)
            worst_gm = (1e9, None)
            for m in gated:
                for v in GRID[::2] + [3.1, 8.0, 11.9, 17.0, 26.9]:
                    pl = M.member(m, v)
                    r, (L, Tr, S) = M.lti_metrics(D[dn], pl, v)
                    Lo = Tr * np.exp(-0.06 * s) / (tau_o * s)
                    pms, fcs = M.pm_all(f, Lo)
                    gup, _ = M.gm_lti(f, Lo)
                    if pms and min(pms) < worst_pm[0]:
                        worst_pm = (min(pms), (m, v, fcs[int(np.argmin(pms))]))
                    if gup < worst_gm[0]:
                        worst_gm = (gup, (m, v))
            print(f"  {dn:4s} tau_o {tau_o:3.1f} s: worst PM {worst_pm[0]:6.1f} at {worst_pm[1]}   worst GM {worst_gm[0]:5.1f} dB at {worst_gm[1]}")


def E5():
    print("\n== E5 light_b (prior world, report only): worst PM, exact rho, least-damped pole")
    for dn in DES:
        worst = None
        for ea in (0, 10):
            for v in GRID:
                pl = M.light_b(v)
                pl.ea = ea
                r, _ = M.lti_metrics(D[dn], pl, v)
                rho, z, fp, _ = M.Periodic(D[dn], pl, v).rho_poles()
                if worst is None or r["pm"] < worst[0]:
                    worst = (r["pm"], v, ea, rho, z, fp, r["fc"])
        print(f"  {dn:4s} light_b min PM {worst[0]:.1f} @ v {worst[1]} age+{worst[2]}  rho {worst[3]:.4f} "
              f"pole {worst[5]:.2f} Hz zeta {worst[4]:.3f} fc {worst[6]:.2f}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["E1", "E2", "E3", "E4", "E5"]
    for w in which:
        globals()[w]()
