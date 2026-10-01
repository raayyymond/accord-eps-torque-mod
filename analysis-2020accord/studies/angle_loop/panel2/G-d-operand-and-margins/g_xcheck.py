# -*- coding: utf-8 -*-
r"""g_xcheck.py -- the crux numbers of designer G's page re-derived on an INDEPENDENT engine: the round-2 stability
refuter's c2r2_model (imports none of ds_model / score_freq / g_ext's loop code; its own image read, sensor chain, plant
members incl. ms_free products, exact periodic model, exact delay margin).  ANALYSIS ONLY.
  X1  the PM-formula finding: rev2-A's rejected Kd 41 / 48 envelope points, on c2r2_model's own L: every crossing,
      the shared formula vs 180 - |phase|, the exact rho and the EXACT DELAY MARGIN (the physical meaning of a margin)
  X2  every implementation's binding points (from g_gate) on c2r2_model: LTI PM (fixed) and exact rho, both frames
      (FA: kd x kappa; FB: G x 1.155, k x 1.155 -- the refuter's own two readings) -- agreement with g_gate
  X3  the round-2 refuter's F1 / F4 / F6 table rows, re-run on every implementation (P2 / F2 published values reproduced
      first as the positive control)
usage: python g_xcheck.py    -> g_xcheck_out.txt"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
sys.path.insert(0, str(X.AL / "refute_stability" / "c2r2"))
import c2r2_model as RM  # noqa: E402

LINES = []


def P(s=""):
    print(s, flush=True)
    LINES.append(s)


def design(iid, im):
    return RM.Design(iid, None, "fresh" if im["dkind"] == "fresh" else "held", kd=float(im["kd"]),
                     ki=float(im.get("ki", 56)), rows=[tuple(r) for r in im["rows"]])


def pm_fixed_of(des, pl, v, kd_scale=1.0, gs=1.0):
    d2 = replace(des)
    G0 = des.G(v)
    d2.G = (lambda vv, G0=G0: G0 * gs)
    r, (L, Tr, S) = RM.lti_metrics(d2, pl, v, kd_scale=kd_scale)
    pmf, fc, pmraw = X.pm_fixed(RM.FG, L)
    return pmf, pmraw, fc, d2


def x1():
    P("X1  rev2-A's REJECTED structures (fresh-rate Kd 41 / 48) at the low-G rows where its envelope 'collapsed', on the "
      "refuter's own engine (c2r2_model): ")
    for kd, m, v, G in ((41, "b_q*J1.0", 14.0, 40.0), (41, "b_q*J_hi", 13.0, 40.0), (48, "b_q*J_hi", 13.0, 40.0),
                        (48, "b_lo", 5.0, 40.0), (48, "b_q*J1.0", 15.0, 60.0)):
        des = RM.Design("x", None, "fresh", kd=float(kd))
        des.G = (lambda vv, G=G: G)
        pl = RM.member(m, v)
        r, (L, Tr, S) = RM.lti_metrics(des, pl, v)
        cr = X.crossings(RM.FG, L)
        rho = RM.Periodic(des, pl, v).rho_poles()[0]
        dm = RM.exact_delay_margin(des, pl, v, hi=400.0)
        P(f"    Kd {kd} {m:9s}@{v:4.1f} G {G:4.0f}: shared-formula PM {r['pm']:7.1f} | crossings "
          + "; ".join(f"{fc:.2f} Hz ph {ph:+6.1f} -> {pf:5.1f}" for fc, ph, pf, _ in cr)
          + f" | exact rho {rho:.4f} | exact delay margin {dm:.1f} ms")


def x2(impls):
    P("X2  binding points of each implementation (g_gate), re-derived on c2r2_model (independent engine):")
    for iid, im in impls.items():
        if im["dkind"] == "box10":
            P(f"    {iid}: box10 is not expressible in c2r2_model (no angle-own D) -- cross-checked by g_exact vs the LTI "
              f"fundamental instead (g_gate rho on every point)")
            continue
        try:
            g = json.loads((X.OUT / f"gate_{iid}.json").read_text())
        except FileNotFoundError:
            P(f"    {iid}: no gate cache")
            continue
        des = design(iid, im)
        by = {}
        for r in g:
            b = r["member"]
            if X.tier_of(b) == "report":
                continue
            if b not in by or r["pm"] < by[b]["pm"]:
                by[b] = r
        worst = sorted(by.values(), key=lambda r: r["pm"] - X.bar_of(r["member"]))[:8]
        for r in worst:
            base, ea, kappa, jb = X._split(r["member"])
            name = base + ("+h10" if ea == 10 else "")
            try:
                pl = RM.member(name, r["v"])
            except KeyError:
                P(f"    {iid} {r['member']}: not expressible in c2r2_model")
                continue
            if jb != 1.0:                    # motor-frame plant reading: J, b / 1.155 (g_ext) <-> the refuter's FB
                pl = replace(pl, J=pl.J * jb, b=pl.b * jb)
            pmf, pmraw, fc, d2 = pm_fixed_of(des, pl, r["v"], kd_scale=kappa)
            rho = RM.Periodic(d2, pl, r["v"], kd_scale=kappa).rho_poles()
            P(f"    {iid} {r['member']:30s}@{r['v']:5.2f}: g_gate PM {r['pm']:5.1f} rho {r['rho']:.4f} | c2r2_model PM "
              f"{pmf:5.1f} rho {rho[0]:.4f} (pole {rho[2]:.2f} Hz z {rho[1]:.3f})")


def x3(impls):
    P("X3  the round-2 stability refuter's F1 (frame), F4 (ms_free products) and F6 (aged single corners) rows, on its own "
      "engine, worst over its grid (1-35 m/s at 0.25 + knots), every implementation (P2 / F2 = its published values):")
    grid = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
    rows = [("J_hi", "FA", 45), ("ms_free", "FA", 45), ("b_lo*J_hi+h10", "FA", 30), ("b_q*J1.0+h10", "FB", 30),
            ("b_lo*J_hi*tau6+h10", "FB", 30), ("b_q*ms_free+h10", "nom", 30), ("b_q*ms_free", "nom", 30),
            ("b_lo*ms_free", "nom", 30), ("J_hi+h10", "nom", 45), ("ms_free+h10", "nom", 45)]
    allim = dict(P2=dict(dkind="fresh", kd=34, rows=X.P2_ROWS), F2=dict(dkind="held", kd=20, rows=X.F2_ROWS))
    allim.update({k: v for k, v in impls.items() if v["dkind"] != "box10"})
    P("    member                  frame  bar | " + " | ".join(f"{k:>14s}" for k in allim))
    for m, fr, bar in rows:
        cells = []
        for iid, im in allim.items():
            des = design(iid, im)
            worst = (999.0, None)
            for v in grid:
                pl = RM.member(m, v)
                if fr == "FA":
                    pmf, _, _, _ = pm_fixed_of(des, pl, v, kd_scale=1 / 1.155)
                elif fr == "FB":
                    pl = replace(pl, k=pl.k * 1.155)
                    pmf, _, _, _ = pm_fixed_of(des, pl, v, gs=1.155)
                else:
                    pmf, _, _, _ = pm_fixed_of(des, pl, v)
                if pmf < worst[0]:
                    worst = (pmf, v)
            cells.append(f"{worst[0]:5.1f} @{worst[1]:5.2f}{'*' if worst[0] < bar else ' '}")
        P(f"    {m:24s} {fr:4s} {bar:4d} | " + " | ".join(f"{c:>14s}" for c in cells))
    P("    (* = below the bar; FA = D operand x 1/1.155, FB = G and k x 1.155: the refuter's own two readings)")


if __name__ == "__main__":
    impls = json.loads((X.OUT / "g_impls.json").read_text())
    which = sys.argv[1:] or ["1", "2", "3"]
    if "1" in which:
        x1()
    if "2" in which:
        x2(impls)
    if "3" in which:
        x3(impls)
    (HERE / ("g_xcheck_out.txt" if len(which) == 3 else f"g_xcheck_{'_'.join(which)}.txt")).write_text(
        "\n".join(LINES) + "\n", encoding="utf-8")
