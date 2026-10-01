# -*- coding: utf-8 -*-
"""c1_gate2.py -- GATE 2 for C1: magnitude AND phase in every loop the signal is in, on a 0.25 m/s grid that includes the
plant knots, every member by tier (c1_members), the hold aged to 20 ticks, two independent linear methods.

What a FAIL is (written before the run; the C1 design page's H2):
  tier A (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6):  PM < 45 deg | exact GM < 6 dB | unstable | a 5-50 Hz closed-loop
      pole with zeta < 0.2 | M20 > 3.58 | L20 > V295's L20 on the same member | max(|T_c|, |T_ref|) > +3 dB in 5-30 Hz
  tier B (b_lo*J_hi, b_lo*J_hi*tau6, b_lo*tau6, J_hi*tau6, b/1.9*J_hi, b_lo*J0.3, J_hi2, J1.0, nominal/b_lo/J_hi+h10, b_q):
      PM < 30 deg | unstable | exact GM < 6 dB
  method disagreement: |PM(stab_lin) - PM(harness_freq)| > 1 deg on any non-h10 point (two methods must agree)
Sections:
  A  the fine grid (stab_lin LTI PM, exact periodic rho / least-damped pole / exact GM; harness_freq PM, M20, L20 vs V295,
     |T| / |T_ref| 5-30 Hz, |T_ref| 1.6-3 Hz)
  B  Re(T/omega) 5-25 Hz vs V294 / V295 / V282 (the stability refuter's stab_hf.torque_per_rate)
  C  two-mass stress rows, hands-off (240) and hands-on (288), C1 vs V294/V295 (stab_hf's exact_any), plus the same rows
     with the motor-side b at the b_q floor (the 3-5 Hz damping the identification did not see)
  D  the 20 Hz stress rows (rec_mode20's plant set) on harness_freq's exact lifted loop, C1 vs V295 vs V282
  E  the fork outer-loop stand-in L_o = T_ref e^{-0.06 s}/(tau_o s), tau_o 0.3/0.5/1.0
usage: python c1_gate2.py [A|B|C|D|E|all]"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_members as M  # noqa: E402
import stab_lin as S  # noqa: E402

TBL = C.c1_table()
KD = C.KD
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
OUTP = []


def P(s=""):
    OUTP.append(s)
    print(s, flush=True)


# ------------------------------------------------------------------------------------------------------------------ A
def point(args):
    import harness_freq as HF
    name, v = args
    pl, tau, ea, (J, b, k) = M.member(name, v)
    c = C.stab_ctl(v, TBL, d=tau, extra_age=ea, kd=KD)
    mg = S.margins(c, pl, npts=4000)
    rho, poles = S.exact(c, pl)
    hfp = [q for q in poles if 5.0 <= q[0] <= 50.0]
    lowp = [q for q in poles if 0.3 <= q[0] < 5.0]
    gm = S.exact_gm(c, pl) if rho < 1 else float("-inf")
    r = dict(member=name, v=v, G=c.G, kp_eff=C.KP_BASE * c.G / 256, pm=mg["pm"], fc=mg["fc"], rho=rho, gm=gm,
             hf=hfp[0] if hfp else (float("nan"), float("nan")), low=lowp[0] if lowp else (float("nan"), float("nan")))
    if ea == 0:
        hp = HF.Plant(J=J, b=b, k=k, tau=tau)
        hc = C.hf_ctl(v, TBL, kd=KD)
        h = HF.metrics(hc, hp, exact=False)
        h295 = HF.metrics(HF.V295, hp, exact=False)
        r.update(pm_hf=h["pm"], M20=h["M20"], L20=h["L20"], L20_v295=h295["L20"], Tc530=h["Tc530_db"],
                 Tr530=h.get("Tr530_db", -99), Tr163=h.get("Tr163", float("nan")), S530=h["S530_db"],
                 trk02=None)
    return r


def secA():
    P("=" * 110)
    P(f"A. FINE GRID: {len(GRID)} speeds x members; C1 table {TBL} ; Kp_base {C.KP_BASE} Ki_base {C.KI_BASE} Kd {KD}")
    P("=" * 110)
    names = M.TIER_A + M.TIER_B + M.REPORT
    jobs = [(n, v) for n in names for v in GRID]
    t0 = time.time()
    with Pool(14) as pool:
        res = pool.map(point, jobs, chunksize=8)
    (C.OUT / "gate2_A.json").write_text(json.dumps(res, default=float))
    P(f"[{time.time() - t0:.0f} s, {len(res)} points]")
    by = {}
    for r in res:
        by.setdefault(r["member"], []).append(r)
    fails = []
    P("member            tier  min PM (v)        PM<thr pts  min exact GM (v)   max rho  least-damped 5-50 Hz pole   "
      "max M20  max L20/V295  max T 5-30 dB  max Tr1.6-3  |PMlin-PMhf| max")
    for n in names:
        rr = by[n]
        tier = "A" if n in M.TIER_A else ("B" if n in M.TIER_B else "rep")
        thr = M.TIER_PM.get(n, 30.0)
        pmr = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        nbad = sum(1 for r in rr if not (r["pm"] >= thr))
        gmr = min(rr, key=lambda r: r["gm"])
        mrho = max(r["rho"] for r in rr)
        hfr = min(rr, key=lambda r: r["hf"][1] if np.isfinite(r["hf"][1]) else 9)
        m20 = max((r.get("M20", 0) for r in rr), default=0)
        l20 = max((r["L20"] / r["L20_v295"] for r in rr if "L20" in r), default=float("nan"))
        t530 = max((max(r["Tc530"], r["Tr530"]) for r in rr if "Tc530" in r), default=float("nan"))
        tr163 = max((r["Tr163"] for r in rr if "Tr163" in r), default=float("nan"))
        dpm = max((abs(r["pm"] - r["pm_hf"]) for r in rr if "pm_hf" in r and np.isfinite(r["pm_hf"])), default=0.0)
        P(f"{n:17s} {tier:4s} {pmr['pm']:6.1f} ({pmr['v']:5.2f})   {nbad:4d}       {gmr['gm']:6.1f} ({gmr['v']:5.2f})"
          f"    {mrho:.4f}   {hfr['hf'][0]:5.1f} Hz z {hfr['hf'][1]:.3f} ({hfr['v']:5.2f})   {m20:5.2f}   {l20:6.3f}"
          f"      {t530:+5.1f}      {tr163:5.2f}      {dpm:5.2f}")
        if tier == "A":
            for r in rr:
                bad = []
                if not (r["pm"] >= 45): bad.append("PM45")
                if not (r["gm"] >= 6): bad.append("GM6")
                if r["rho"] >= 1: bad.append("UNSTABLE")
                if r["hf"][1] < 0.2: bad.append("pole<0.2")
                if r.get("M20", 0) > 3.58: bad.append("M20")
                if "L20" in r and r["L20"] > r["L20_v295"] * (1 + 1e-9): bad.append("L20")
                if "Tc530" in r and max(r["Tc530"], r["Tr530"]) > 3.0: bad.append("T530")
                if "pm_hf" in r and abs(r["pm"] - r["pm_hf"]) > 1.0: bad.append("method")
                if bad: fails.append((n, r["v"], bad))
        elif tier == "B":
            for r in rr:
                bad = []
                if not (r["pm"] >= 30): bad.append("PM30")
                if r["rho"] >= 1: bad.append("UNSTABLE")
                if not (r["gm"] >= 6): bad.append("GM6")
                if "pm_hf" in r and abs(r["pm"] - r["pm_hf"]) > 1.0: bad.append("method")
                if bad: fails.append((n, r["v"], bad))
    P(f"\nGATE 2 (A) FAILS: {len(fails)}")
    for f in fails[:60]:
        P(f"   {f}")
    # the knot / design-speed table for the page
    P("\nper-speed table at the design speeds (PM / exact GM / fc / wheel pole):")
    for v in (3.0, 3.1, 5.0, 8.0, 10.0, 10.5, 11.0, 11.5, 11.9, 12.0, 12.5, 13.0, 15.0, 17.0, 19.0, 22.0, 26.0, 26.9, 30.0):
        rr = {r["member"]: r for r in res if abs(r["v"] - v) < 1e-9}
        if not rr:
            continue
        P(f"  v {v:5.2f} G {rr['nominal']['G']:5d} Kp_eff {rr['nominal']['kp_eff']:6.0f} | " + " ".join(
            f"{n}:{rr[n]['pm']:.1f}" for n in ("nominal", "J_hi", "b_lo", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "J_hi2",
                                                "b_q", "nominal+h10", "b_lo+h10", "J1.3", "ms_free", "light_b")))
    return res


# ------------------------------------------------------------------------------------------------------------------ B
def secB():
    import stab_hf as H
    P("=" * 110)
    P("B. Re(T/omega), T counts per deg/s, hold included, d = 2: >0 damps, <0 anti-damps (stab_hf.torque_per_rate)")
    P("=" * 110)
    fr = (5, 7, 10, 13, 15, 17, 20, 25)
    P("ctl              " + "".join(f"{f:>9d}Hz" for f in fr))
    rows = {}
    for c, nm in ((H.V294, "V294"), (H.V295, "V295"), (H.V282, "V282")):
        vals = [H.torque_per_rate(c, f).real for f in fr]
        rows[nm] = vals
        P(f"{nm:16s} " + "".join(f"{x:+11.2f}" for x in vals))
    c0 = {}
    for v in (3, 8, 12.5, 19, 26, 30):
        c = S.Ctl(v, d=2)                                   # the refuter's own C0 operating point
        c0[v] = [H.torque_per_rate(c, f).real for f in fr]
        P(f"C0@{v:<13g} " + "".join(f"{x:+11.2f}" for x in c0[v]))
    c1 = {}
    for v in (3, 5, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 26, 30):
        c = C.stab_ctl(v, TBL, d=2, kd=KD)
        c1[v] = [H.torque_per_rate(c, f).real for f in fr]
        P(f"C1@{v:<5g}Kp{C.KP_BASE * c.G / 256:5.0f} " + "".join(f"{x:+11.2f}" for x in c1[v]))
    worst = {f: min(c1[v][i] for v in c1) for i, f in enumerate(fr)}
    P("C1 worst over speed " + "".join(f"{worst[f]:+11.2f}" for f in fr))
    P("C1 worst / V295     " + "".join(f"{worst[f] / rows['V295'][i]:11.1f}" if rows['V295'][i] < 0 else f"{'(V295>0)':>11s}"
                                      for i, f in enumerate(fr)))
    P("C1 worst / C0 worst " + "".join(f"{worst[f] / min(c0[v][i] for v in c0):11.2f}" for i, f in enumerate(fr)))
    return dict(fr=fr, ref=rows, c0=c0, c1={str(k): v for k, v in c1.items()})


# ------------------------------------------------------------------------------------------------------------------ C
def _tm_row(args):
    import stab_hf as H
    kind, v, J, b, k, r2, fz, zw, alpha, za = args
    if kind == "off":
        pl = S.two_mass(J, b, k, r2, fz, zw)
    else:
        pl = S.two_mass(J, b, k, r2, fz, zw, J_arm_ratio=alpha, zeta_arm=za)
    out = {}
    for c, nm in ((C.stab_ctl(v, TBL, d=2, kd=KD), "C1"), (S.Ctl(v, d=2), "C0"), (H.V294, "V294"), (H.V295, "V295")):
        rho, hf = H.exact_any(c, pl)
        out[nm] = (rho, hf[0] if hf else (float("nan"), float("nan")))
    return dict(kind=kind, v=v, b=b, r2=r2, fz=fz, zw=zw, alpha=alpha, za=za, res=out)


def secC():
    import v294_plant as VP
    fam = VP.family()
    P("=" * 110)
    P("C. TWO-MASS STRESS (collocated motor-side sensor): hands-off 240 rows, hands-on 288 rows (the stability refuter's "
      "sets), and the hands-off set again with the motor-side b at the b_q value (0.25 b, floored) at >= 12.5 m/s")
    P("=" * 110)
    jobs = []
    for v in (3, 8, 12.5, 19, 26):
        p = fam["nominal"].at(v)
        for fz in (10.0, 13.0, 16.0, 20.0):
            for r2 in (0.1, 0.2, 0.3, 0.5):
                for zw in (0.01, 0.02, 0.05):
                    jobs.append(("off", v, p.J, p.b, p.k, r2, fz, zw, 0, 0))
                    if v >= 12.5:
                        bq = max(0.25 * p.b, M.B_FLOOR)
                        jobs.append(("off_bq", v, p.J, bq, p.k, r2, fz, zw, 0, 0))
    for v in (3, 8, 12.5, 19, 26, 30):
        p = fam["nominal"].at(v)
        for r2 in (0.1, 0.2, 0.3):
            for alpha in (1.0, 2.0, 3.0, 5.0):
                for za in (0.02, 0.05, 0.1, 0.2):
                    jobs.append(("on", v, p.J, p.b, p.k, r2, 13.0, 0.02, alpha, za))
    with Pool(14) as pool:
        res = pool.map(_tm_row, jobs, chunksize=4)
    for kind in ("off", "off_bq", "on"):
        rr = [r for r in res if r["kind"] == kind]
        if not rr:
            continue
        un = {nm: sum(1 for r in rr if r["res"][nm][0] >= 1) for nm in ("C1", "C0", "V294", "V295")}
        ratio = [r["res"]["C1"][1][1] / r["res"]["V295"][1][1] for r in rr if r["res"]["V295"][1][1] > 0]
        dz = [r["res"]["C1"][1][1] - r["res"]["V295"][1][1] for r in rr]
        worse = sum(1 for d in dz if d < -1e-4)
        P(f"  {kind:7s}: rows {len(rr)}; unstable C1 {un['C1']} C0 {un['C0']} V294 {un['V294']} V295 {un['V295']} | "
          f"C1 least-damped zeta < V295's on {worse}/{len(rr)} rows; zeta(C1)/zeta(V295) min {min(ratio):.3f} "
          f"median {np.median(ratio):.3f}; zeta(C1) - zeta(V295) min {min(dz):+.4f}")
        rr.sort(key=lambda r: r["res"]["C1"][1][1])
        for r in rr[:6]:
            P(f"      v {r['v']:4g} b {r['b']:5.2f} fz {r['fz']:4g} r2 {r['r2']:.1f} zw {r['zw']:.2f} a {r['alpha']:g} za {r['za']:.2f}:"
              f" C1 {r['res']['C1'][1][0]:5.1f} Hz z{r['res']['C1'][1][1]:+.4f} rho {r['res']['C1'][0]:.4f} | C0 z"
              f"{r['res']['C0'][1][1]:+.4f} | V294 z{r['res']['V294'][1][1]:+.4f} | V295 z{r['res']['V295'][1][1]:+.4f}")
    (C.OUT / "gate2_C.json").write_text(json.dumps(res, default=float))
    return res


# ------------------------------------------------------------------------------------------------------------------ D
def _m20row(args):
    import harness_freq as HF
    v, f2, r2, z2 = args
    base = HF.plant_at("nominal", v)
    p = replace(base, f2=f2, r2=r2, zeta2=z2)
    out = {}
    for nm, cc in (("C1", C.hf_ctl(v, TBL, kd=KD)), ("V295", HF.V295), ("V282", HF.V282)):
        r = HF.metrics(cc, p, exact=True)
        out[nm] = (bool(r["stable"]), r["hfmode"])
    A, B, Cc, D = p.ss()
    ev = np.linalg.eigvals(A)
    fl = [(abs(e) / (2 * np.pi), -e.real / abs(e)) for e in ev if abs(e) / (2 * np.pi) > 5]
    zo = min(fl, key=lambda t: t[1]) if fl else (float("nan"), float("nan"))
    return dict(v=v, f2=f2, r2=r2, z2=z2, open=zo, res=out)


def secD():
    P("=" * 110)
    P("D. 20 Hz STRESS ROWS (rec_mode20's set: f2 13/16/20/24 Hz, r2 0.2/0.5, zeta2 0.02/0.05, v 3/8/12.5/19/26), "
      "harness_freq exact lifted loop")
    P("=" * 110)
    jobs = [(v, f2, r2, z2) for v in (3.0, 8.0, 12.5, 19.0, 26.0) for f2 in (13.0, 16.0, 20.0, 24.0) for r2 in (0.2, 0.5)
            for z2 in (0.02, 0.05)]
    with Pool(14) as pool:
        res = pool.map(_m20row, jobs)
    un = {nm: sum(1 for r in res if not r["res"][nm][0]) for nm in ("C1", "V295", "V282")}
    dz = [r["res"]["C1"][1][1] - r["open"][1] for r in res if r["res"]["C1"][0]]
    P(f"  rows {len(res)}; unstable: C1 {un['C1']} V295 {un['V295']} V282 {un['V282']} (positive control); "
      f"C1 HF zeta shift vs the open plant: min {min(dz):+.3f} max {max(dz):+.3f}")
    return res


# ------------------------------------------------------------------------------------------------------------------ E
def secE():
    P("=" * 110)
    P("E. FORK OUTER-LOOP STAND-IN  L_o = T_ref e^{-0.06 s}/(tau_o s): PM / GM by tau_o (stab_more section 2's method)")
    P("=" * 110)
    f = np.logspace(-2, 1.7, 4000)

    def tref(c, pl):
        L, KCth, KCw, Pt, Pw = S.frf(c, pl, f)
        z = np.exp(1j * 2 * np.pi * f * S.TS); zi = 1 / z
        Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
        K = c.fade * S.FWD * Hout * zi ** c.d
        PI = c.kp / 256 + (c.ki / 32768) / (1 - zi)
        return K * (c.G / 256) * PI * 160 * Pt / (1 + L)
    out = {}
    for nm in ("nominal", "b_lo", "J_hi", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0"):
        for v in (3, 8, 11.9, 12.5, 19, 26):
            pl, tau, ea, _ = M.member(nm, v)
            c = C.stab_ctl(v, TBL, d=tau, kd=KD)
            Tr = tref(c, pl)
            cells = [f"{nm:15s} v {v:4g}: |Tref| peak {np.max(np.abs(Tr)):.2f} at {f[np.argmax(np.abs(Tr))]:.2f} Hz"]
            for tau_o in (0.3, 0.5, 1.0):
                Lo = Tr * np.exp(-1j * 2 * np.pi * f * 0.06) / (tau_o * 1j * 2 * np.pi * f)
                mag = np.abs(Lo); ph = np.unwrap(np.angle(Lo)) * 180 / np.pi
                i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
                pm = (ph[i[0]] + 180) if len(i) else float("nan")
                j = np.where((ph[:-1] > -180) & (ph[1:] <= -180))[0]
                gm = min([-20 * math.log10(mag[q]) for q in j], default=float("inf"))
                cells.append(f"tau_o {tau_o}: PM {pm:5.1f} GM {gm:5.1f} dB")
                out[f"{nm}|{v}|{tau_o}"] = (pm, gm)
            P("  " + " | ".join(cells))
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {}
    for s, fn in (("A", secA), ("B", secB), ("C", secC), ("D", secD), ("E", secE)):
        if which in (s, "all"):
            res[s] = fn()
    tag = which
    (HERE / f"gate2_{tag}_Kd{KD}.txt").write_text("\n".join(OUTP), encoding="utf-8")
