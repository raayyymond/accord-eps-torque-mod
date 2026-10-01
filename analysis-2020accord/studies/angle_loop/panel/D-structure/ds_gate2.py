# -*- coding: utf-8 -*-
r"""ds_gate2.py -- GATE 2 machinery for every D-structure implementation: the speed-gain ENVELOPE over the full credible
set, the integer table fit, and the full-grid gate (analytic PM / LTI GM / |T| / M20 / L20 / Re(T/w) + exact periodic
rho, poles and exact GM).  ANALYSIS ONLY.

MEMBERS (c1r2_members -- the full factorial damping {nominal, b_lo, b/1.9, b_q} x inertia {J 0.2, J_hi 0.5, J_hi2 0.8,
J1.0} x delay {2, 6 ms} x hold age {1-10, 11-20}, + the refuter's b_lo*J0.3, + report members), PLUS the two single
corners the brief names that c1r2_members lacks as linear members: 'mode13' / 'mode20' = the nominal plant with a
collocated two-mass mode at 13 Hz (zeta 0.1) / 20 Hz (zeta 0.05), r2 0.2 (harness_time's 'nominal+mode13Hz' /
'nominal+mode20Hz', v294_plant.with_mode20), gated at the tier-A bars.  F_lo / F_hi / bc differ from nominal / b_lo only
in friction, which a linear model cannot see: they are scored in the time domain (ds_time.py).

BARS (written before any run; the C1 pages' H2 kept, plus the brief's):
  tier A (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6, mode13, mode20):  PM >= 45 deg, GM >= 6 dB (LTI in the envelope;
      EXACT on the final table), stable, max(|T_c|, |T_ref|) <= +3 dB in 5-30 Hz, M20 <= V295's, L20 <= V295's on the
      same member
  tier B (every other factorial cell, incl. b_q*J_hi, b_q*J1.0, b_q*tau6, every combined member aged +h10):  PM >= 30,
      GM >= 6 dB, stable
  report: J1.3 and its products, tau10, ms_free, light_b, b_q0, bq10*...  (tabulated, not gated)
  Re(T/w) at 20 Hz >= V295's (the same hold age, the same rate model) at every speed, ages 0 and 10.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace, asdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as M  # noqa: E402
import c1r2_members as M2  # noqa: E402
import c1_lib as C  # noqa: E402

OUT = M.AL.parents[2] / "_scratch" / "angle_loop" / "D-structure"
OUT.mkdir(parents=True, exist_ok=True)
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
MODES = ("mode13", "mode20")
# ---- THE BRIEF'S CREDIBLE SET (the gate).  Single corners at the tier-A bars; every combined member and EVERY member
# ---- aged to 11-20 ticks (+h10) at the tier-B bars.  'bc' is b_lo in the linear model (its friction is time-domain).
SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6")
TIER_A = SINGLE
TIER_B = COMBINED + tuple(m + "+h10" for m in SINGLE + COMBINED)
# ---- REPORT: every other cell of c1r2_members' full factorial (damping x inertia x delay x age) and its report members
REPORT = tuple(m for m in tuple(M2.TIER_B) + tuple(M2.REPORT) if m not in TIER_A + TIER_B)
GATED = TIER_A + TIER_B
ALL = GATED + REPORT
PMBAR = {**{m: 45.0 for m in TIER_A}, **{m: 30.0 for m in TIER_B}}


def two_mass_mu(J, b, k, f2, zeta2, r2):
    """v294_plant.with_mode20 / harness_time.PlantVec / harness_freq.Plant.ss two-mass convention."""
    Jw = J * r2
    Jm = J - Jw
    mu = Jm * Jw / J
    K = (2 * np.pi * f2) ** 2 * mu
    c = 2 * zeta2 * np.sqrt(K * mu)
    A = np.array([[0, 1, 0, 0],
                  [-(k + K) / Jm, -(b + c) / Jm, K / Jm, c / Jm],
                  [0, 0, 0, 1],
                  [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    return A, B, np.array([[1.0, 0, 0, 0]]), np.array([[0, 1.0, 0, 0]])


def member(name, v):
    """(plant, d, extra_age, (J, b, k))"""
    base = name[:-4] if name.endswith("+h10") else name
    if base in MODES:
        J, b, k, d, ea = M2.params("nominal", v)
        f2, z2 = (13.0, 0.1) if base == "mode13" else (20.0, 0.05)
        return two_mass_mu(J, b, k, f2, z2, 0.2), int(d), int(ea) + (10 if name.endswith("+h10") else 0), (J, b, k)
    return M.member(name, v)


def tier(name):
    return "A" if name in TIER_A else ("B" if name in TIER_B else "report")


# ----------------------------------------------------------------------------------------------------------- envelope
_F = M.FGRID


def _pm_gm_rows(L):
    """L: (nG, nF).  per row: min PM over every |L| = 1 crossing, LTI GM (dB) = min over -180 crossings with |L| < 1."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L), axis=1) * 180 / np.pi
    nG = L.shape[0]
    pm = np.full(nG, np.inf)
    gm = np.full(nG, np.inf)
    for i in range(nG):
        m, p = mag[i], ph[i]
        idx = np.where((m[:-1] - 1) * (m[1:] - 1) <= 0)[0]
        for j in idx:
            if m[j] == m[j + 1]:
                continue
            t = (1 - m[j]) / (m[j + 1] - m[j])
            q = p[j] + t * (p[j + 1] - p[j])
            pm[i] = min(pm[i], ((q + 180) + 180) % 360 - 180)
        w = np.floor((p + 180) / 360)
        jx = np.where(w[:-1] != w[1:])[0]
        for j in jx:
            if m[j] < 1:
                gm[i] = min(gm[i], -20 * math.log10(max(m[j], 1e-12)))
            else:
                gm[i] = min(gm[i], -20 * math.log10(m[j]))       # |L| >= 1 at -180: negative margin
    return pm, gm


def L_affine(des, name, v):
    """L(g) = L0 + g dL exactly (G enters every structure linearly); g = G / 256."""
    pl, d, ea, _ = member(name, v)
    d0 = replace(des, d=d, extra_age=ea, G=0.0)
    d1 = replace(des, d=d, extra_age=ea, G=256.0)
    L0 = M.loop_frf(d0, pl, _F)["L"]
    L1 = M.loop_frf(d1, pl, _F)["L"]
    return L0, L1 - L0


GSCAN = np.unique(np.round(np.geomspace(40, 12000, 220)))


def env_point(args):
    """largest G on GSCAN such that every G' <= G passes PM >= bar and LTI GM >= 6 dB (monotone search from below)."""
    des, name, v = args
    L0, dL = L_affine(des, name, v)
    g = GSCAN / 256.0
    pm, gm = _pm_gm_rows(L0[None, :] + g[:, None] * dL[None, :])
    bar = PMBAR.get(name, 30.0)
    ok = (pm >= bar) & (gm >= 6.0)
    if not ok[0]:
        return dict(member=name, v=v, Gmax=0.0, pm_at=float(pm[0]))
    k = np.argmin(ok) if not ok.all() else len(ok)
    return dict(member=name, v=v, Gmax=float(GSCAN[k - 1]), pm_at=float(pm[k - 1]), gm_at=float(gm[k - 1]))


def rule_point(args):
    """the controller-only 20 Hz rules at speed v (member-independent): the largest G on GSCAN with M20 <= V295's and
    Re(T/w)20 >= V295's at hold age 0 AND 10 (same rate model), every smaller G passing too."""
    des, v = args
    ok_all = []
    for G in GSCAN:
        ok = True
        for ea in (0, 10):
            d = replace(des, G=float(G), extra_age=ea)
            ref = replace(M.V295, extra_age=ea, rate_model=des.rate_model)
            if M.m20(d) > M.m20(ref) * (1 + 1e-9):
                ok = False
            if M.re_tw(d, 20.0)[0] < M.re_tw(ref, 20.0)[0] - 1e-12:
                ok = False
        ok_all.append(ok)
        if not ok:
            break
    ok_all = np.array(ok_all)
    if not ok_all[0]:
        return dict(v=v, Grule=0.0)
    k = np.argmin(ok_all) if not ok_all.all() else len(ok_all)
    return dict(v=v, Grule=float(GSCAN[k - 1]))


def l20_point(args):
    """tier-A members: the largest G with L20 <= V295's L20 on the same member."""
    des, name, v = args
    pl, d, ea, _ = member(name, v)
    ref = M.loop_frf(replace(M.V295, d=d, extra_age=ea, rate_model=des.rate_model), pl, np.array([20.0]))["L"][0]
    f = np.array([20.0])
    L0 = M.loop_frf(replace(des, d=d, extra_age=ea, G=0.0), pl, f)["L"][0]
    L1 = M.loop_frf(replace(des, d=d, extra_age=ea, G=256.0), pl, f)["L"][0]
    gs = GSCAN / 256.0
    ok = np.abs(L0 + gs * (L1 - L0)) <= abs(ref) * (1 + 1e-9)
    if not ok[0]:
        return dict(member=name, v=v, Gl20=0.0)
    k = np.argmin(ok) if not ok.all() else len(ok)
    return dict(member=name, v=v, Gl20=float(GSCAN[k - 1]))


def envelope(des, members=GATED, grid=GRID, procs=15, tag=None, rules=True):
    jobs = [(des, n, v) for n in members for v in grid]
    t0 = time.time()
    with Pool(procs) as pool:
        res = pool.map(env_point, jobs, chunksize=6)
        if rules:
            rr = pool.map(rule_point, [(des, v) for v in grid])
            ll = pool.map(l20_point, [(des, n, v) for n in TIER_A for v in grid], chunksize=6)
        else:
            rr, ll = [], []
    env = {}
    bind = {}
    for r in res:
        if r["v"] not in env or r["Gmax"] < env[r["v"]]:
            env[r["v"]] = r["Gmax"]
            bind[r["v"]] = r["member"]
    for r in rr:
        if r["Grule"] < env[r["v"]]:
            env[r["v"]] = r["Grule"]
            bind[r["v"]] = "RULE M20/Re20"
    for r in ll:
        if r["Gl20"] < env[r["v"]]:
            env[r["v"]] = r["Gl20"]
            bind[r["v"]] = "L20:" + r["member"]
    out = dict(env=env, bind=bind, res=res, rules=rr, l20=ll, sec=time.time() - t0)
    if tag:
        (OUT / f"env_{tag}.json").write_text(json.dumps(dict(env=env, bind=bind, res=res), default=float))
    return out


# ----------------------------------------------------------------------------------------------------------- the table
def fit_table(env, knots_v, margin=0.96, grid=GRID, gmin=64):
    """LP: knot values G_i at speeds knots_v maximising the area under the walk, with lerp <= margin * env at every grid
    speed (clamped flat below the first and above the last knot), then integer rows (X u16, G u16, S s16 Q12) whose
    EXACT integer walk (c1_lib.cave_G) is checked <= margin * env; G_i lowered by 1 until it holds."""
    from scipy.optimize import linprog
    vs = np.array(grid)
    e = np.array([env[v] for v in grid]) * margin
    X = [C.spd_counts(k) for k in knots_v]
    n = len(X)
    A, b = [], []
    for v, ev in zip(vs, e):
        vc = C.spd_counts(v)
        row = np.zeros(n)
        if vc <= X[0]:
            row[0] = 1
        elif vc >= X[-1]:
            row[-1] = 1
        else:
            i = max(j for j in range(n - 1) if X[j] <= vc)
            t = (vc - X[i]) / (X[i + 1] - X[i])
            row[i], row[i + 1] = 1 - t, t
        A.append(row)
        b.append(ev)
    A = np.array(A)
    c = -A.sum(0)
    r = linprog(c, A_ub=A, b_ub=np.array(b), bounds=[(gmin, 30000)] * n, method="highs")
    Gk = [int(math.floor(x)) for x in r.x]
    for _ in range(400):
        tbl = C.make_table(list(zip(X, Gk)))
        bad = []
        for v, ev in zip(vs, e):
            gv = C.cave_G(C.spd_counts(v), tbl)
            if gv > ev:
                bad.append(v)
        if not bad:
            return tbl, Gk
        for v in bad:
            vc = C.spd_counts(v)
            i = 0 if vc <= X[0] else (n - 1 if vc >= X[-1] else max(j for j in range(n - 1) if X[j] <= vc))
            Gk[i] = max(gmin, Gk[i] - 1)
            if 0 < vc - X[i] and i + 1 < n:
                Gk[i + 1] = max(gmin, Gk[i + 1] - 1)
    raise RuntimeError("table fit did not converge")


def G_at(v, tbl):
    return C.cave_G(C.spd_counts(v), tbl)


# ----------------------------------------------------------------------------------------------------------- full gate
_V295_L20: dict = {}


def gate_point(args):
    des, name, v, tbl, exact_gm = args
    pl, d, ea, jbk = member(name, v)
    G = G_at(v, tbl) if tbl is not None else des.G
    dd = replace(des, d=d, extra_age=ea, G=float(G))
    m = M.metrics(dd, pl)
    lp = M.Lifted(dd, pl)
    rho, poles = lp.exact()
    low = sorted([q for q in poles if 0.3 <= q[0] < 8.0], key=lambda t: t[1])
    hf = sorted([q for q in poles if 5.0 <= q[0] <= 50.0], key=lambda t: t[1])
    r = dict(member=name, v=v, G=G, rho=rho, low=low[0] if low else (float("nan"), float("nan")),
             hf=hf[0] if hf else (float("nan"), float("nan")), **{k: (x if not isinstance(x, complex) else [x.real, x.imag])
                                                                    for k, x in m.items()})
    if exact_gm and rho < 1:
        r["gm_exact"] = lp.exact_gm()
    elif rho >= 1:
        r["gm_exact"] = float("-inf")
    v295 = replace(M.V295, d=d, extra_age=ea, rate_model=des.rate_model)
    r["L20_v295"] = float(abs(M.loop_frf(v295, pl, np.array([20.0]))["L"][0]))
    r["M20_v295"] = M.m20(v295)
    return r


def full_gate(des, tbl, members=ALL, grid=GRID, exact_gm_for=("A", "B"), procs=15, tag=None):
    jobs = [(des, n, v, tbl, tier(n) in exact_gm_for) for n in members for v in grid]
    t0 = time.time()
    with Pool(procs) as pool:
        res = pool.map(gate_point, jobs, chunksize=4)
    if tag:
        (OUT / f"gate_{tag}.json").write_text(json.dumps(res, default=float))
    return res, time.time() - t0


def fails(res):
    out = []
    for r in res:
        t = tier(r["member"])
        bad = []
        if t == "A":
            if not (r["pm"] >= 45): bad.append("PM45")
            if not (r.get("gm_exact", r["gm_lti"]) >= 6): bad.append("GM6")
            if r["rho"] >= 1: bad.append("UNSTABLE")
            if max(r["Tc530"], r.get("Tr530", -99)) > 3.0: bad.append("T530")
            if r["M20"] > r["M20_v295"] * (1 + 1e-9): bad.append("M20")
            if r["L20"] > r["L20_v295"] * (1 + 1e-9): bad.append("L20")
        elif t == "B":
            if not (r["pm"] >= 30): bad.append("PM30")
            if not (r.get("gm_exact", r["gm_lti"]) >= 6): bad.append("GM6")
            if r["rho"] >= 1: bad.append("UNSTABLE")
        if bad:
            out.append((r["member"], r["v"], bad))
    return out


def summarize(res, P=print):
    by = {}
    for r in res:
        by.setdefault(r["member"], []).append(r)
    P("member                    tier  min PM (v)      #<bar  min GM_exact (v)    max rho  least-damped low pole (v)     "
      "max M20 (V295)  max L20/V295  max T530 dB  max Tr1.6-3")
    for n in ALL:
        if n not in by:
            continue
        rr = by[n]
        t = tier(n)
        bar = PMBAR.get(n, 30.0)
        pmr = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        nb = sum(1 for r in rr if not (r["pm"] >= bar))
        gmr = min(rr, key=lambda r: r.get("gm_exact", r["gm_lti"]))
        lowr = min(rr, key=lambda r: r["low"][1] if np.isfinite(r["low"][1]) else 9)
        P(f"{n:25s} {t:6s} {pmr['pm']:6.1f} ({pmr['v']:5.2f})  {nb:4d}   {gmr.get('gm_exact', gmr['gm_lti']):6.1f} "
          f"({gmr['v']:5.2f})    {max(r['rho'] for r in rr):.4f}   {lowr['low'][0]:5.2f} Hz z {lowr['low'][1]:.3f} "
          f"({lowr['v']:5.2f})   {max(r['M20'] for r in rr):5.2f} ({max(r['M20_v295'] for r in rr):4.2f})"
          f"   {max(r['L20'] / r['L20_v295'] for r in rr):6.3f}   {max(max(r['Tc530'], r.get('Tr530', -99)) for r in rr):+6.1f}"
          f"   {max(r.get('Tr163', 0) for r in rr):6.2f}")


def re_tw_table(des, tbl, freqs=(5, 7, 10, 13, 15, 17, 20, 25), ages=(0, 10), vs=None):
    """Re(T/w) worst (most negative) over every speed 1-35 m/s at 0.25, by hold age; V294 / V295 / V282 same model."""
    vs = vs or [round(x, 2) for x in np.arange(1.0, 35.01, 0.25)]
    fr = np.array(freqs, float)
    out = {}
    for ea in ages:
        rows = []
        for v in vs:
            G = G_at(v, tbl) if tbl is not None else des.G
            rows.append(M.re_tw(replace(des, G=float(G), extra_age=ea), fr))
        rows = np.array(rows)
        k = np.argmin(rows, axis=0)
        out[ea] = dict(worst=rows.min(0).tolist(), at_v=[vs[i] for i in k])
        for nm, ref in (("V294", M.V294), ("V295", M.V295), ("V282", M.V282)):
            out[ea][nm] = M.re_tw(replace(ref, extra_age=ea, rate_model=des.rate_model), fr).tolist()
    return out
