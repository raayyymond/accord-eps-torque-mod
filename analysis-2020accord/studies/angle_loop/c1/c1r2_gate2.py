# -*- coding: utf-8 -*-
"""c1r2_gate2.py -- GATE 2 for C1 rev 2 (2026-10-01): magnitude AND phase in every loop the signal is in, on a 0.25 m/s
grid that includes the plant knots, EVERY member of c1r2_members by tier (the round-2 refuter's combined members and
the hold aged to 20 ticks on EVERY tier-B member), two independent linear methods.  ANALYSIS ONLY.

Re-uses c1_gate2's point() / secC / secD / secE unchanged, with its member module swapped for c1r2_members at IMPORT
time (so the spawned Pool workers, which re-import this file as __mp_main__, run the rev-2 members too).

What a FAIL is (written before the run; the rev-2 page's H2):
  tier A (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6):  PM < 45 | exact GM < 6 dB | unstable | a 5-50 Hz closed-loop
      pole zeta < 0.2 | M20 > 3.58 | L20 > V295's on the same member | max(|T_c|, |T_ref|) > +3 dB in 5-30 Hz
  tier B (33 members: every combined member incl. b_q*J_hi, b_q*J_hi2, b_q*J1.0, b_q*J_hi*tau6, b_q*tau6, J1.0*tau6,
      and every tier-B member again with slot 4 late by 10 ticks):  PM < 30 | unstable | exact GM < 6 dB
  method disagreement > 1 deg on any non-aged point
  Re(T/omega) at 20 Hz above V295's at ANY speed, at hold age 0 OR 10 (B2)
usage: python c1r2_gate2.py [A|B|C|D|E|all]"""
from __future__ import annotations

import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_members as M  # noqa: E402
import c1_gate2 as G2  # noqa: E402
import stab_lin as S  # noqa: E402

G2.M = M                                   # <- the swap (top level: the workers get it too)
TBL = G2.TBL
KD = G2.KD
assert TBL == C.c1_table() and KD == C.KD
GRID = G2.GRID
OUTP = G2.OUTP
P = G2.P


_FHF = np.logspace(-2.3, 2.0, 24000)


def point(args):
    """c1_gate2.point + harness_freq's PM taken as the MINIMUM over every |L| = 1 crossing (the gate's own PM definition;
    HF.metrics reports the FIRST crossing only, which differs from stab_lin's minimum wherever |L| crosses 1 more than
    once -- rev 2's lightly damped b_q members do, at 0.5-0.6 Hz and again at 1.5-2 Hz).  Both are kept in the record."""
    import harness_freq as HF
    r = G2.point(args)
    name, v = args
    pl, tau, ea, (J, b, k) = M.member(name, v)
    if ea == 0:
        hp = HF.Plant(J=J, b=b, k=k, tau=tau)
        from dataclasses import replace as _rep
        hc = _rep(C.hf_ctl(v, TBL, kd=KD), d=tau)        # HF.metrics(use_plant_tau=True) does the same
        L = HF.C_fb(_FHF, hc) * hp.frf(_FHF)
        mag = np.abs(L)
        ph = np.unwrap(np.angle(L)) * 180 / np.pi
        pms = []
        for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]:
            if mag[i] == mag[i + 1]:
                continue
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            pms.append(((ph[i] + t * (ph[i + 1] - ph[i]) + 180) + 180) % 360 - 180)
        r["pm_hf_first"] = r["pm_hf"]
        r["pm_hf"] = min(pms) if pms else float("nan")
        r["n_cross"] = len(pms)
    return r


def secA():
    P("=" * 110)
    P(f"A. FINE GRID (rev 2): {len(GRID)} speeds x {len(M.TIER_A + M.TIER_B + M.REPORT)} members; table {TBL}; "
      f"Kp_base {C.KP_BASE} Ki_base {C.KI_BASE} Kd {KD}")
    P("=" * 110)
    names = M.TIER_A + M.TIER_B + M.REPORT
    jobs = [(n, v) for n in names for v in GRID]
    t0 = time.time()
    with Pool(14) as pool:
        res = pool.map(point, jobs, chunksize=8)
    (C.OUT / "gate2_r2_A.json").write_text(json.dumps(res, default=float))
    P(f"[{time.time() - t0:.0f} s, {len(res)} points]")
    by = {}
    for r in res:
        by.setdefault(r["member"], []).append(r)
    fails = []
    P("member                  tier  min PM (v)       PM<thr  min exact GM (v)   max rho   least-damped 5-50 Hz pole    "
      "max M20 max L20/V295 max T5-30dB  |PMlin-PMhf|")
    for n in names:
        rr = by[n]
        tier = M.tier(n)
        thr = M.TIER_PM.get(n, 30.0)
        pmr = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        nbad = sum(1 for r in rr if not (r["pm"] >= thr))
        gmr = min(rr, key=lambda r: r["gm"])
        mrho = max(r["rho"] for r in rr)
        hfr = min(rr, key=lambda r: r["hf"][1] if np.isfinite(r["hf"][1]) else 9)
        m20 = max((r.get("M20", 0) for r in rr), default=0)
        l20 = max((r["L20"] / r["L20_v295"] for r in rr if "L20" in r), default=float("nan"))
        t530 = max((max(r["Tc530"], r["Tr530"]) for r in rr if "Tc530" in r), default=float("nan"))
        dpm = max((abs(r["pm"] - r["pm_hf"]) for r in rr if "pm_hf" in r and np.isfinite(r["pm_hf"])), default=0.0)
        P(f"{n:23s} {tier:6s} {pmr['pm']:6.1f} ({pmr['v']:5.2f})  {nbad:4d}   {gmr['gm']:6.1f} ({gmr['v']:5.2f})"
          f"   {mrho:.4f}   {hfr['hf'][0]:5.1f} Hz z {hfr['hf'][1]:.3f} ({hfr['v']:5.2f})   {m20:5.2f}  {l20:6.3f}"
          f"     {t530:+5.1f}      {dpm:5.2f}")
        for r in rr:
            bad = []
            if tier == "A":
                if not (r["pm"] >= 45): bad.append("PM45")
                if not (r["gm"] >= 6): bad.append("GM6")
                if r["rho"] >= 1: bad.append("UNSTABLE")
                if r["hf"][1] < 0.2: bad.append("pole<0.2")
                if r.get("M20", 0) > 3.58: bad.append("M20")
                if "L20" in r and r["L20"] > r["L20_v295"] * (1 + 1e-9): bad.append("L20")
                if "Tc530" in r and max(r["Tc530"], r["Tr530"]) > 3.0: bad.append("T530")
            elif tier == "B":
                if not (r["pm"] >= 30): bad.append("PM30")
                if r["rho"] >= 1: bad.append("UNSTABLE")
                if not (r["gm"] >= 6): bad.append("GM6")
            if tier in ("A", "B") and "pm_hf" in r and abs(r["pm"] - r["pm_hf"]) > 1.0:
                bad.append("method")
            if bad:
                fails.append((n, r["v"], bad))
    gated = [r for r in res if M.tier(r["member"]) in ("A", "B")]
    multi = [r for r in gated if r.get("n_cross", 1) > 1]
    P(f"\nmethod check: harness_freq's PM is taken as the MIN over every |L| = 1 crossing (HF.metrics' first-crossing PM "
      f"is kept as pm_hf_first); gated points with > 1 crossing: {len(multi)}")
    for lim in (40, 50, 60, 999):
        sub = [abs(r["pm"] - r["pm_hf"]) for r in gated if "pm_hf" in r and np.isfinite(r["pm_hf"])
               and min(r["pm"], r["pm_hf"]) < lim]
        P(f"   max |PM(stab_lin) - PM(harness_freq)| where either PM < {lim:3d} deg: {max(sub):.2f} over {len(sub)} points")
    meth = [f for f in fails if f[2] == ["method"]]
    stab = [f for f in fails if f[2] != ["method"]]
    lowest = min((min(r["pm"], r["pm_hf"]) for r in gated if "pm_hf" in r and np.isfinite(r["pm_hf"])
                  and abs(r["pm"] - r["pm_hf"]) > 1.0), default=float("nan"))
    P(f"\nGATE 2 (A): {len(gated)} gated points; STABILITY / MARGIN FAILS (PM, GM, rho, pole, M20, L20, T): {len(stab)}; "
      f"METHOD flags (> 1 deg) as pre-registered: {len(meth)}, every one at PM >= {lowest:.1f} deg on both methods")
    for f in stab[:80]:
        P(f"   {f}")
    for f in meth[:12]:
        P(f"   method: {f}")
    P("\nper-speed PM at the design speeds (deg):")
    cols = ("nominal", "J_hi", "b_lo", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J_hi*tau6",
            "b_q*J1.0", "b_q*J1.0+h10", "b_lo*J_hi*tau6+h10", "J1.0*tau6+h10", "J1.3", "b_q*J1.3", "ms_free", "light_b")
    P("    v      G Kp_eff | " + " ".join(f"{c[:12]:>12s}" for c in cols))
    for v in (1.0, 3.0, 3.1, 5.0, 8.0, 10.0, 11.0, 11.9, 12.25, 12.5, 13.0, 15.0, 15.25, 17.0, 19.0, 19.25, 22.0, 26.0,
              26.9, 30.0):
        rr = {r["member"]: r for r in res if abs(r["v"] - v) < 1e-9}
        if not rr:
            continue
        P(f"  {v:5.2f} {rr['nominal']['G']:5d} {rr['nominal']['kp_eff']:6.0f} | " +
          " ".join(f"{rr[c]['pm']:12.1f}" for c in cols))
    P("\nleast-damped closed-loop pole 0.3-8 Hz (exact periodic), per member, at >= 10 m/s (the drive's discriminator):")
    for v in (10.0, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
        rr = {r["member"]: r for r in res if abs(r["v"] - v) < 1e-9}
        P(f"  v {v:4.1f}: " + " | ".join(
            f"{c}: {rr[c]['low'][0]:.2f} Hz z {rr[c]['low'][1]:.2f}"
            for c in ("nominal", "b_lo", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "light_b")))
    return res


def secB():
    """Re(T/omega) 5-25 Hz vs V294 / V295 / V282, at hold age 0 AND age 10 (the round-2 refuter's F4), worst over
    every speed 1-35 m/s at 0.25 m/s (the table's integer G)."""
    import stab_hf as H
    sys.path.insert(0, str(C.AL / "refute_stability"))
    import refute_c1_ind as R
    P("=" * 110)
    P("B. Re(T/omega), T counts per deg/s, hold included, d = 2: > 0 damps, < 0 anti-damps.  Two independent forms: "
      "stab_hf.torque_per_rate (age 0) and refute_c1_ind.torque_per_rate_C1 / _rate (age 0 and 10).")
    P("=" * 110)
    fr = (5, 7, 10, 13, 15, 17, 20, 25)
    P("ctl                     " + "".join(f"{f:>9d}Hz" for f in fr))
    ref = {}
    for nm, (a, b, op, kp, kd) in (("V294", (1011, 567, "diff", 960, 0)), ("V295", (1011, 1050, "diff", 960, 0))):
        for age in (0, 10):
            ref[(nm, age)] = [R.torque_per_rate_rate(a, b, op, kp, kd, f, d=2, age=age).real for f in fr]
            P(f"{nm} age {age:<2d}            " + "".join(f"{x:+11.3f}" for x in ref[(nm, age)]))
    v282 = [H.torque_per_rate(H.V282, f).real for f in fr]
    P("V282 age 0 (stab_hf)    " + "".join(f"{x:+11.2f}" for x in v282))
    vs = [round(x, 2) for x in np.arange(1.0, 35.01, 0.25)]
    worst = {}
    for age in (0, 10):
        w = []
        for f in fr:
            vals = [(R.torque_per_rate_C1(C.G_at(v, TBL), C.KP_BASE, C.KI_BASE, KD, f, d=2, age=age).real, v) for v in vs]
            w.append(min(vals))
        worst[age] = w
        P(f"C1r2 worst age {age:<2d}      " + "".join(f"{x[0]:+11.3f}" for x in w))
        P(f"   at v (m/s)           " + "".join(f"{x[1]:11.2f}" for x in w))
        P(f"   / V295 same age      " + "".join(
            (f"{x[0] / ref[('V295', age)][i]:11.2f}" if ref[("V295", age)][i] < 0 else f"{'(V295>0)':>11s}")
            for i, x in enumerate(w)))
    # cross-check with stab_hf at age 0
    c_hf = [min(H.torque_per_rate(C.stab_ctl(v, TBL, d=2, kd=KD), f).real for v in vs[::4]) for f in fr]
    P("C1r2 worst age 0 (stab_hf, 1 m/s grid)" + "".join(f"{x:+9.3f}" for x in c_hf))
    i20 = fr.index(20)
    ok = all(worst[a][i20][0] >= ref[("V295", a)][i20] for a in (0, 10))
    P(f"\nRULE Re(T/w)20 <= V295's at every speed, at age 0 and 10: {'PASS' if ok else 'FAIL'} "
      f"(age 0: {worst[0][i20][0]:+.3f} vs {ref[('V295', 0)][i20]:+.3f}; age 10: {worst[10][i20][0]:+.3f} vs "
      f"{ref[('V295', 10)][i20]:+.3f})")
    # rev 1 and rev 2 side by side over 5-25 Hz (rev 1 = the kd16 table at Kd 16 / Ki 100)
    t1 = C.make_table(C.VARIANTS["kd16"]["knots"])
    for age in (0, 10):
        w1 = [min(R.torque_per_rate_C1(C.G_at(v, t1), 225, 100, 16, f, d=2, age=age).real for v in vs) for f in fr]
        P(f"C1 rev1 worst age {age:<2d}   " + "".join(f"{x:+11.3f}" for x in w1) + "   (rev 2 / rev 1: " +
          " ".join(f"{worst[age][i][0] / w1[i]:.2f}" if w1[i] < 0 else "-" for i in range(len(fr))) + ")")
    return dict(fr=fr, worst={str(k): v for k, v in worst.items()})


def secE():
    """the fork outer-loop stand-in, now including the round-2 combined members."""
    P("=" * 110)
    P("E. FORK OUTER-LOOP STAND-IN  L_o = T_ref e^{-0.06 s}/(tau_o s): PM / GM by tau_o, incl. the rev-2 combined members")
    P("=" * 110)
    f = np.logspace(-2, 1.7, 4000)

    def tref(c, pl):
        L, KCth, KCw, Pt, Pw = S.frf(c, pl, f)
        z = np.exp(1j * 2 * np.pi * f * S.TS); zi = 1 / z
        Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
        K = c.fade * S.FWD * Hout * zi ** c.d
        PI = c.kp / 256 + (c.ki / 32768) / (1 - zi)
        return K * (c.G / 256) * PI * 160 * Pt / (1 + L)
    worst = {}
    for nm in ("nominal", "b_lo", "J_hi", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0",
               "b_q*J1.0+h10"):
        for v in (3, 8, 11.9, 12.5, 15, 17, 19, 26):
            pl, tau, ea, _ = M.member(nm, v)
            c = C.stab_ctl(v, TBL, d=tau, extra_age=ea, kd=KD)
            Tr = tref(c, pl)
            cells = [f"{nm:14s} v {v:4g}: |Tref| pk {np.max(np.abs(Tr)):.2f} @ {f[np.argmax(np.abs(Tr))]:.2f} Hz"]
            for tau_o in (0.3, 0.5, 1.0):
                Lo = Tr * np.exp(-1j * 2 * np.pi * f * 0.06) / (tau_o * 1j * 2 * np.pi * f)
                mag = np.abs(Lo); ph = np.unwrap(np.angle(Lo)) * 180 / np.pi
                i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
                pm = (ph[i[0]] + 180) if len(i) else float("nan")
                j = np.where((ph[:-1] > -180) & (ph[1:] <= -180))[0]
                gm = min([-20 * math.log10(mag[q]) for q in j], default=float("inf"))
                cells.append(f"tau_o {tau_o}: PM {pm:5.1f} GM {gm:5.1f}")
                worst[tau_o] = min(worst.get(tau_o, 99), gm)
            P("  " + " | ".join(cells))
    P("  worst outer GM by tau_o: " + ", ".join(f"{k}: {v:.1f} dB" for k, v in sorted(worst.items())))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for s, fn in (("A", secA), ("B", secB), ("C", G2.secC), ("D", G2.secD), ("E", secE)):
        if which in (s, "all"):
            fn()
    (HERE / f"gate2_r2_{which}.txt").write_text("\n".join(OUTP), encoding="utf-8")
