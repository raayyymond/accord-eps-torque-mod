# -*- coding: utf-8 -*-
r"""r2a_freq.py -- GATE 2 for every C2 rev 2 (reviser A) implementation, on the COMMON frequency scorer and the exact
periodic model, plus everything the C2 stability refuter listed as unrun.  ANALYSIS ONLY.

  A  the COMMON SCORER (panel/score_freq.py: its validate(), its controller FRF, its metrics extractor, its member set and
     0.25 m/s grid incl. the plant knots, hold ages 1-10 AND 11-20 on every member) on P1 P2 P5 F1 F2, the brief's GATED
     set, fails counted with score_freq.summarize's own rules; then the same extractor on the REPORT members (the rest of
     the factorial incl. b_lo*J_hi*tau6(+h10), J1.3, light_b) -- tabulated.
  B  the EXACT periodic model (ds_gate2.full_gate: lifted 10-tick monodromy rho, least-damped poles, exact GM by bisection)
     on every member of ds_gate2.ALL (gated + report) at every grid speed, for every implementation.
  C  Re(T/w) 5-25 Hz, worst over 1-35 m/s, hold ages 0 and 10, against V294 / V295 / V282 (same rate model).
  D  the goal's OWN tracking metric (c1r2_trackmetric.slope, the kit scorer's slope through r71b's weighted spectrum) per
     member and speed >= 8 m/s; turn-hold |T_ref(0.02 Hz)|; the hard-turn |T_ref| peak in 1.6-3 Hz.
  E  the fork outer-loop stand-in L_o = T_ref e^(-0.06 s) / (tau_o s), tau_o 0.3 / 0.5 / 1.0 s (PM, GM).
  F  stress plants beyond the gate: collocated two-mass modes at 13 / 15 / 16.5 / 17 / 20 Hz, zeta 0.02 / 0.05, wheel
     share r2 0.2 / 0.4, on nominal and b_lo at every 1 m/s: stability (rho) and the closed-loop |T| peak 5-30 Hz.
usage:  python r2a_freq.py [A B C D E F]      outputs r2a_freq_<sec>.txt (+ _scratch caches)"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

import r2a_common as R

import score_freq as SF  # noqa: E402
import ds_gate2 as G2  # noqa: E402
import ds_model as DM  # noqa: E402

IMPL_ORDER = ("P1", "P2", "P5", "F1", "F2")


def _P(lines):
    def P(s=""):
        print(s, flush=True)
        lines.append(s)
    return P


def _cands():
    tabs = R.tables()
    return {k: (R.cand_freq(k, tabs[k]), tabs[k]) for k in IMPL_ORDER}


# ------------------------------------------------------------------------------------------------------------- A
def _score_job(args):
    cid, mem, v = args
    cand, _ = _cands()[cid]
    r = SF.score(cand, mem, v)
    return cid, mem, v, r


def secA():
    lines = []
    P = _P(lines)
    ok = SF.validate()
    P(f"score_freq.validate(): {'PASS' if ok else 'FAIL'}")
    members = list(SF.GATED)
    report = [m for m in G2.REPORT]
    speeds = SF.GRID
    v295M20 = SF.score_ref("V295", "nominal", 12.5)["M20"]
    v294M20 = SF.score_ref("V294", "nominal", 12.5)["M20"]
    refRe = {nm: {ff: SF.score_ref(nm, "nominal", 12.5)[f"ReTw{ff}"] for ff in (7, 10, 13, 16, 20)}
             for nm in ("V294", "V295", "V282")}
    v295Re20 = {0: 1e9, 10: 1e9}
    for v in speeds:
        for ea, nm in ((0, "nominal"), (10, "nominal+h10")):
            Pt, Pw, d, ea2, _ = SF.plant_frf(nm, v)
            Cth, Cw, Cref, K = SF.ref_ctl_frf("V295", SF.FGRID, d, ea2)
            iff = int(np.argmin(abs(SF.FGRID - 20.0)))
            wf = 2 * np.pi * 20.0
            v295Re20[ea] = min(v295Re20[ea], float((-K[iff] * (Cth[iff] + 1j * wf * Cw[iff]) / (1j * wf)).real))
    v295L20 = {(m, v): SF.score_ref("V295", m, v)["L20"] for m in members for v in speeds}
    jobs = [(c, m, v) for c in IMPL_ORDER for m in members + report for v in speeds]
    t0 = time.time()
    with Pool(15) as pool:
        res = pool.map(_score_job, jobs, chunksize=20)
    rows = {c: {} for c in IMPL_ORDER}
    for c, m, v, r in res:
        rows[c][(m, v)] = r
    summ = {}
    for c in IMPL_ORDER:
        cand, _ = _cands()[c]
        s = SF.summarize(cand, {k: x for k, x in rows[c].items() if k[0] in members}, members, speeds, v295M20,
                         v294M20, v295L20, v295Re20, refRe)
        summ[c] = s
    P(f"[{time.time() - t0:.0f} s]  COMMON SCORER (score_freq) on the brief's GATED set ({len(members)} members x "
      f"{len(speeds)} speeds), V295 M20 {v295M20:.3f}")
    P("| impl | minPM nom | minPM single (tier A) | minPM comb (tier B) | binding | M20 (xV295) | L20x | ReTw13 | ReTw16 | "
      "ReTw20 | Re20 age10 | Tr1.6-3 nom | turn-hold >=8 | trk 0.1-1 | dPM(age) | GATE2 fails |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c, s in summ.items():
        rw = s["Re20_worst"]
        P(f"| {c} | {s['minPM_nom']:.1f} | {s['minPM_single']:.1f} | {s['minPM_comb']:.1f} | {s['bind']} | "
          f"{s['M20']:.2f} ({s['M20_ratio']:.2f}) | {s['L20_ratio']:.2f} | {s['Re'][13]:+.2f} | {s['Re'][16]:+.2f} | "
          f"{s['Re'][20]:+.2f} | {rw[10]:+.2f} ({rw[10] / v295Re20[10]:.2f}) | {s['Tr163']:.2f} | {s['turnhold']:.3f} | "
          f"{s['trk_range'][0]:.2f}-{s['trk_range'][1]:.2f} | {s['holdage_dPM']:.1f} | {s['n_fail']} |")
        for f_ in s["fails"][:12]:
            P(f"     FAIL {f_}")
    P("")
    P("REPORT members (not gated by the brief; the same extractor), min PM (speed) and min LTI GM per member:")
    P("| member | " + " | ".join(IMPL_ORDER) + " |")
    P("|---|" + "---|" * len(IMPL_ORDER))
    for m in report:
        cells = []
        for c in IMPL_ORDER:
            rr = [(v, rows[c][(m, v)]) for v in speeds]
            pv = min(rr, key=lambda t: t[1]["pm"] if np.isfinite(t[1]["pm"]) else 999)
            gv = min(t[1]["gm"] for t in rr)
            cells.append(f"{pv[1]['pm']:.1f} ({pv[0]:g}) GM {gv:.1f}")
        P(f"| {m} | " + " | ".join(cells) + " |")
    (R.OUT / "freqA.json").write_text(json.dumps({c: {f"{m}|{v}": r for (m, v), r in rows[c].items()}
                                                  for c in IMPL_ORDER}, default=float))
    (R.OUT / "freqA_summary.json").write_text(json.dumps(summ, default=float))
    (R.HERE / "r2a_freq_A.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- B
def secB(only=None):
    lines = []
    P = _P(lines)
    tabs = R.tables()
    allf = {}
    for c in IMPL_ORDER:
        if only and c not in only:
            continue
        des = R.des_of(c)
        res, sec = G2.full_gate(des, tabs[c], members=G2.ALL, grid=G2.GRID, tag=f"r2a_{c}")
        fl = G2.fails(res)
        allf[c] = fl
        P("=" * 150)
        P(f"{c}: {R.IMPLS[c]['note']}   [{sec:.0f} s, {len(res)} points]  GATED FAILS (exact periodic): {len(fl)}")
        for f_ in fl[:30]:
            P(f"   FAIL {f_}")
        G2.summarize(res, P)
        unst = [(r["member"], r["v"], round(r["rho"], 4)) for r in res if r["rho"] >= 1]
        P(f"   UNSTABLE points on ANY member (gated or report): {len(unst)} {unst[:10]}")
        (R.OUT / f"freqB_{c}.json").write_text(json.dumps(res, default=float))
    tag = "_".join(only) if only else "all"
    (R.HERE / f"r2a_freq_B_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- C
def secC():
    lines = []
    P = _P(lines)
    tabs = R.tables()
    fr = (5, 7, 10, 13, 15, 17, 20, 25)
    out = {}
    for c in IMPL_ORDER:
        r = G2.re_tw_table(R.des_of(c), tabs[c], freqs=fr)
        out[c] = r
        for ea in (0, 10):
            if c == IMPL_ORDER[0]:
                for nm in ("V294", "V295", "V282"):
                    P(f"{nm:5s} age {ea:2d}         " + "".join(f"{x:+8.2f}" for x in r[ea][nm]))
            P(f"{c:5s} age {ea:2d} worst   " + "".join(f"{x:+8.2f}" for x in r[ea]["worst"]) + "   at v " +
              " ".join(f"{x:g}" for x in r[ea]["at_v"]))
            ratio = [w / v if v < 0 else float("nan") for w, v in zip(r[ea]["worst"], r[ea]["V295"])]
            P(f"{'':5s}        x V295 " + "".join(f"{x:8.2f}" for x in ratio))
    P("Hz:                 " + "".join(f"{f:8d}" for f in fr))
    P("Re(T/w) in T counts per deg/s, controller-only, > 0 damps a collocated mode, < 0 removes damping; 'x V295' = the "
      "worst over speed divided by V295's (V295 is speed-independent), > 1 = more anti-damping than the flown V295")
    (R.OUT / "freqC.json").write_text(json.dumps(out))
    (R.HERE / "r2a_freq_C.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- D
def secD():
    import c1r2_trackmetric as TM
    lines = []
    P = _P(lines)
    tabs = R.tables()
    mems = ("nominal", "b_lo", "b_hi", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "ms_free",
            "nominal+h10", "b_q*J1.0+h10")
    vs = (8.0, 9.0, 10.0, 11.0, 11.9, 12.5, 13.5, 15.0, 17.0, 19.0, 22.0, 26.0, 26.9, 30.0)
    P("GOAL TRACKING METRIC (c1r2_trackmetric.slope: the kit scorer's slope through r71b's weighted desired-lateral-accel "
      "spectrum; bar 0.95-1.05) | turn-hold |T_ref(0.02 Hz)| (bar >= 0.90) | hard-turn |T_ref| peak 1.6-3 Hz")
    worst = {}
    for c in IMPL_ORDER:
        des = R.des_of(c)
        P(f"--- {c}: {R.IMPLS[c]['note']}")
        wmin, wmax, hmin, t163 = 9.0, 0.0, 9.0, 0.0
        for v in vs:
            G = float(R.G_at(v, tabs[c]))
            vals, holds, trs = [], [], []
            for m in mems:
                pl, d, ea, _ = G2.member(m, v)
                dd = replace(des, G=G, d=d, extra_age=ea)

                def Tf(f, dd=dd, pl=pl):
                    return DM.loop_frf(dd, pl, np.asarray(f, float))["Tr"]
                vals.append(TM.slope(Tf, v))
                mt = DM.metrics(dd, pl)
                holds.append(mt["hold"])
                trs.append(mt["Tr163"])
            wmin, wmax = min(wmin, min(vals)), max(wmax, max(vals))
            hmin, t163 = min(hmin, min(holds)), max(t163, max(trs))
            P(f"  v {v:5.1f} G {int(G):5d}: metric min {min(vals):.3f} ({mems[int(np.argmin(vals))]}) max {max(vals):.3f}"
              f" | hold min {min(holds):.3f} | Tr1.6-3 max {max(trs):.2f} ({mems[int(np.argmax(trs))]}) nominal "
              f"{trs[0]:.2f}")
        worst[c] = dict(metric_min=wmin, metric_max=wmax, hold_min=hmin, tr163_max=t163)
        P(f"  => {c}: goal metric over every member and speed >= 8: {wmin:.3f} .. {wmax:.3f} "
          f"({'PASS' if 0.95 <= wmin and wmax <= 1.05 else 'FAIL'} 0.95-1.05); turn-hold min {hmin:.3f} "
          f"({'PASS' if hmin >= 0.90 else 'FAIL'}); |T_ref| 1.6-3 Hz max {t163:.2f}")
    (R.OUT / "freqD.json").write_text(json.dumps(worst))
    (R.HERE / "r2a_freq_D.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- E
def secE():
    lines = []
    P = _P(lines)
    tabs = R.tables()
    f = DM.FGRID
    mems = ("nominal", "b_lo", "J_hi", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "b_q", "b_q*J1.0", "ms_free",
            "nominal+h10", "b_lo*J_hi+h10", "J1.0+h10", "b_q*J1.0+h10")
    vs = (3.1, 5.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0)
    P("E. FORK OUTER-LOOP STAND-IN  L_o = T_ref e^{-0.06 s}/(tau_o s): worst PM / GM over the members, per speed")
    out = {}
    for c in IMPL_ORDER:
        des = R.des_of(c)
        worst = {0.3: [99, 99], 0.5: [99, 99], 1.0: [99, 99]}
        P(f"--- {c}")
        for v in vs:
            G = float(R.G_at(v, tabs[c]))
            cells = {0.3: [99, 99, ""], 0.5: [99, 99, ""], 1.0: [99, 99, ""]}
            for m in mems:
                pl, d, ea, _ = G2.member(m, v)
                Tr = DM.loop_frf(replace(des, G=G, d=d, extra_age=ea), pl, f)["Tr"]
                for tau in (0.3, 0.5, 1.0):
                    Lo = Tr * np.exp(-1j * 2 * np.pi * f * 0.06) / (tau * 1j * 2 * np.pi * f)
                    pms, _ = DM.pm_all(f, Lo)
                    pm = min(pms) if pms else 99.0
                    gm = DM.gm_lti(f, Lo)
                    if pm < cells[tau][0]:
                        cells[tau][0], cells[tau][2] = pm, m
                    cells[tau][1] = min(cells[tau][1], gm)
            for tau in cells:
                worst[tau][0] = min(worst[tau][0], cells[tau][0])
                worst[tau][1] = min(worst[tau][1], cells[tau][1])
            P(f"  v {v:5.1f}: " + " | ".join(f"tau_o {t}: PM {cells[t][0]:5.1f} ({cells[t][2]}) GM {cells[t][1]:5.1f}"
                                           for t in (0.3, 0.5, 1.0)))
        P(f"  => {c} worst: " + ", ".join(f"tau_o {t}: PM {worst[t][0]:.1f} GM {worst[t][1]:.1f} dB" for t in worst))
        out[c] = {str(t): worst[t] for t in worst}
    (R.OUT / "freqE.json").write_text(json.dumps(out))
    (R.HERE / "r2a_freq_E.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- F
def _stress_job(args):
    c, base, f2, z2, r2, v = args
    tabs = R.tables()
    des = R.des_of(c)
    J, b, k, d, ea = G2.M2.params(base, v)
    pl = G2.two_mass_mu(J, b, k, f2, z2, r2)
    dd = replace(des, G=float(R.G_at(v, tabs[c])), d=int(d), extra_age=int(ea))
    rho, poles = DM.Lifted(dd, pl).exact()
    m = DM.metrics(dd, pl)
    hf = sorted([q for q in poles if 5.0 <= q[0] <= 50.0], key=lambda t: t[1])
    return dict(c=c, base=base, f2=f2, z2=z2, r2=r2, v=v, rho=rho, pm=m["pm"], Tc530=m["Tc530"],
                Tr530=m.get("Tr530", -99), hf=hf[0] if hf else (float("nan"), float("nan")))


def secF():
    lines = []
    P = _P(lines)
    jobs = [(c, base, f2, z2, r2, float(v)) for c in IMPL_ORDER for base in ("nominal", "b_lo", "nominal+h10")
            for f2 in (13.0, 15.0, 16.5, 17.0, 20.0) for z2 in (0.02, 0.05) for r2 in (0.2, 0.4)
            for v in range(1, 36, 1)]
    t0 = time.time()
    with Pool(15) as pool:
        res = pool.map(_stress_job, jobs, chunksize=8)
    P(f"F. TWO-MASS STRESS ({len(jobs)} points, {time.time() - t0:.0f} s): collocated wheel-side mode f2 at zeta2, share r2,"
      f" on nominal / b_lo / nominal+h10, every 1 m/s 1-35")
    P("| impl | unstable points | min PM | max |T_c|,|T_ref| 5-30 Hz dB | least-damped 5-50 Hz pole (f, zeta) and where |")
    P("|---|---|---|---|---|")
    out = {}
    for c in IMPL_ORDER:
        rr = [r for r in res if r["c"] == c]
        uns = [r for r in rr if r["rho"] >= 1]
        pmr = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        pk = max(max(r["Tc530"], r["Tr530"]) for r in rr)
        hf = min(rr, key=lambda r: r["hf"][1] if np.isfinite(r["hf"][1]) else 9)
        P(f"| {c} | {len(uns)} | {pmr['pm']:.1f} ({pmr['base']} {pmr['f2']:g} Hz z{pmr['z2']} r{pmr['r2']} @{pmr['v']:g}) | "
          f"{pk:+.1f} | {hf['hf'][0]:.2f} Hz z {hf['hf'][1]:.4f} ({hf['base']} {hf['f2']:g} Hz z{hf['z2']} r{hf['r2']} "
          f"@{hf['v']:g}) |")
        out[c] = dict(unstable=len(uns), minpm=pmr["pm"], peak=pk, hf=hf["hf"])
    (R.OUT / "freqF.json").write_text(json.dumps(out, default=float))
    (R.HERE / "r2a_freq_F.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    which = sys.argv[1:] or ["A", "C", "D", "E", "F", "B"]
    for w in which:
        t0 = time.time()
        {"A": secA, "B": secB, "C": secC, "D": secD, "E": secE, "F": secF}[w]()
        print(f"[{w}: {time.time() - t0:.0f} s]", flush=True)
