# -*- coding: utf-8 -*-
"""ds_explore.py -- round 1: every STRUCTURE x a few parameter values, scored the same way BEFORE any table is fitted:
the gated envelope (max G passing PM/GM bars on every gated member of the brief's credible set) at 14 speeds, expressed
as the angle stiffness it buys (T counts per degree at DC = 0.1002 Kp_eff), and what that envelope costs at 20 Hz
(M20, Re(T/w)20 at hold age 0 and 10, vs V295 under the SAME rate model) and in LF tracking (|T_ref| and phase at
0.2 / 0.5 Hz, nominal plant).  ANALYSIS ONLY.  usage: python ds_explore.py  (writes ds_explore_out.txt)"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as M  # noqa: E402
import ds_gate2 as G2  # noqa: E402

SPEEDS = [1.0, 3.0, 5.0, 8.0, 10.0, 11.5, 12.5, 13.0, 15.0, 17.0, 19.0, 22.0, 27.0, 30.0]
KD_PER_FRESH = -M.ABE_PER / 8.0          # fresh D: S per deg/s per Kd count = 0.589
KD_PER_FINE = -M.D_PER / 8000.0          # fine D (dop_k 1): S per deg/s per (Kd*dop_k) = 0.0348


def candidates():
    c = []
    A = c.append
    A(M.Des("B0 C1r2 (held D Kd20)"))
    A(M.Des("P+I only (no D)", dsrc="none"))
    for kde in (48, 96, 160, 256):
        A(M.Des(f"D1a D-on-E Kd{kde}", dsrc="E", kd=kde))
    for kD in (10, 20, 30):
        A(M.Des(f"D1b fine K_D{kD}", dsrc="op", dop="fine", kd=round(kD / KD_PER_FINE / 8), dop_k=8))
    for beta, kD in ((1 / 8, 20), (1 / 16, 20)):
        A(M.Des(f"D1c heldLP b1/{round(1 / beta)} K_D{kD}", dsrc="op", dop="held_lp", lp_beta=beta, kd=kD * 100 // 8,
                dop_k=8))
    for kD in (10, 20, 30, 40):
        A(M.Des(f"D2a fresh K_D{kD}", dsrc="op", dop="fresh_rate", kd=round(kD / KD_PER_FRESH)))
    for (b, kh) in ((1 / 16, 1.0), (3 / 32, 2.0)):
        A(M.Des(f"D2b fwd lead b{b:.4f} kh{kh:g} +heldD20", lead="fwd", lead_beta=b, lead_kh=kh))
        A(M.Des(f"D2c fb lead b{b:.4f} kh{kh:g} +heldD20", lead="fb", lead_beta=b, lead_kh=kh))
        A(M.Des(f"D2b fwd lead b{b:.4f} kh{kh:g} +freshD20", lead="fwd", lead_beta=b, lead_kh=kh, dsrc="op",
                dop="fresh_rate", kd=34))
    for kpi, kir in ((24, 0.5), (40, 0.5), (46, 0.5), (40, 0.25)):
        A(M.Des(f"D3a cascade held Kp{kpi} Ki{kpi * kir:g}", kind="cascade", kp=kpi, ki=kpi * kir, ka=4.0,
                dsrc="none"))
        A(M.Des(f"D3b cascade fresh Kp{kpi} Ki{kpi * kir:g}", kind="cascade", kp=kpi, ki=kpi * kir, ka=4.0,
                dsrc="none", cop="fresh"))
    return c


def p_per_deg(des, G):
    """angle P, S counts per degree of error at DC (P path only)."""
    g = G / 256.0
    if des.kind == "cascade":
        return des.kp / 256.0 * 4 * g * des.ka * 40
    return des.kp / 256.0 * g * 160


def score(des, env):
    out = {}
    fr = np.array([20.0])
    re0, re10, m20 = [], [], []
    for v in SPEEDS:
        G = env[v]
        re0.append(M.re_tw(replace(des, G=G), fr)[0])
        re10.append(M.re_tw(replace(des, G=G, extra_age=10), fr)[0])
        m20.append(M.m20(replace(des, G=G)))
    v295 = (M.re_tw(M.V295, fr)[0], M.re_tw(replace(M.V295, extra_age=10), fr)[0], M.m20(M.V295))
    out.update(re0=min(re0), re10=min(re10), m20=max(m20), v295=v295)
    trk = {}
    for v in (8.0, 15.0, 22.0):
        G = 0.96 * env[v]
        pl, d, ea, _ = M.member("nominal", v)
        r = M.loop_frf(replace(des, G=G, d=d), pl, np.array([0.2, 0.5, 2.0]))
        trk[v] = [(abs(x), np.degrees(np.angle(x))) for x in r["Tr"]]
    out["trk"] = trk
    return out


if __name__ == "__main__":
    lines = []
    P = lambda s="": (print(s, flush=True), lines.append(s))  # noqa: E731
    res = {}
    t0 = time.time()
    for des in candidates():
        e = G2.envelope(des, members=G2.GATED, grid=SPEEDS)
        sc = score(des, e["env"])
        res[des.name] = dict(env=e["env"], bind=e["bind"], score=sc)
        P(f"{des.name:42s} T/deg at env: " + " ".join(f"{0.1602 * p_per_deg(des, e['env'][v]):5.0f}" for v in SPEEDS)
          + f" | M20 {sc['m20']:5.2f} (V295 {sc['v295'][2]:.2f}) Re20 a0 {sc['re0']:+.2f} ({sc['v295'][0]:+.2f}) "
            f"a10 {sc['re10']:+.2f} ({sc['v295'][1]:+.2f}) | Tr 15 m/s 0.2/0.5/2 Hz "
          + " ".join(f"{m:.2f}<{p:+.0f}" for m, p in sc["trk"][15.0]) + f"  [{time.time() - t0:.0f}s]")
        P("   bind: " + " ".join(f"{v:g}:{e['bind'][v]}" for v in SPEEDS))
    P("speeds: " + " ".join(f"{v:g}" for v in SPEEDS))
    (HERE / "ds_explore_out.txt").write_text("\n".join(lines), encoding="utf-8")
    (G2.OUT / "explore.json").write_text(json.dumps(res, default=lambda o: str(o)))
