# -*- coding: utf-8 -*-
"""REFUTER scans on the independent model stab_lin.py.  Prints tables to stdout."""
import sys, math, copy
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import v294_plant as VP

fam = VP.family()
SPEEDS_FINE = [round(x, 2) for x in np.arange(1.0, 35.01, 0.5)]
CRED = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")


def pm_exact(v, pl, tau, **kw):
    c = S.Ctl(v, d=tau, **kw)
    mg = S.margins(c, pl)
    rho, poles = S.exact(c, pl)
    lowz = [p for p in poles if 0.5 <= p[0] <= 50]
    return mg, rho, (lowz[0] if lowz else (float('nan'), float('nan')))


def section(t):
    print("\n" + "=" * 110 + "\n" + t + "\n" + "=" * 110)


# ---------------------------------------------------------------- 1. fine speed grid, credible family
section("1. FINE SPEED GRID (0.5 m/s), credible members: min PM per member, and where")
worst = {}
for nm in CRED + ("J_hi2", "ms_free", "light_b"):
    rows = []
    for v in SPEEDS_FINE:
        p, pl, tau = S.member_at(fam, nm, v)
        mg, rho, lz = pm_exact(v, pl, tau)
        rows.append((mg['pm'], v, mg['fc'], rho, lz))
    rows.sort()
    pmmin, vmin, fc, rho, lz = rows[0]
    unst = [r[1] for r in rows if r[3] >= 1]
    sub30 = sorted(set(r[1] for r in rows if r[0] < 30))
    sub45 = sorted(set(r[1] for r in rows if r[0] < 45))
    print(f"{nm:8s} min PM {pmmin:6.1f} at {vmin:5.1f} m/s (fc {fc:.2f} Hz) | PM<45 at {sub45[:3]}..{sub45[-3:] if sub45 else ''} "
          f"({len(sub45)} pts) | PM<30 at {sub30[:4]}..{sub30[-2:] if sub30 else ''} ({len(sub30)}) | unstable {unst[:3]}..({len(unst)})")

# ---------------------------------------------------------------- 2. combined corners
section("2. COMBINED CORNERS (each factor is a stated uncertainty of the identification); min PM over 1..35 m/s")
def combo(name, v):
    # returns (p, plant, tau)
    if name == "b_lo*J_hi":
        p = fam["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b_lo*J_hi*tau6":
        p = fam["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 6
    if name == "b_lo*tau6":
        p = fam["b_lo"].at(v); return p, S.rigid(p.J, p.b, p.k), 6
    if name == "J_hi*tau6":
        p = fam["J_hi"].at(v); return p, S.rigid(p.J, p.b, p.k), 6
    if name == "b/1.9 (G3a top)":
        p = fam["nominal"].at(v); bs = 1 / 1.9 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b/1.9*J_hi":
        p = fam["J_hi"].at(v); bs = 1 / 1.9 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b_lo*J0.3":           # J 0.3 is inside the 0-5 m/s CI and inside the 10-15 preference
        p = fam["nominal"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(0.3, p.b * bs, p.k), 2
    if name == "tau10":                # the 0 ms tap offset reading of the ident gives 8.4 ms equivalent delay
        p = fam["nominal"].at(v); return p, S.rigid(p.J, p.b, p.k), 10
    if name == "b_lo*tau10":
        p = fam["b_lo"].at(v); return p, S.rigid(p.J, p.b, p.k), 10
    raise KeyError(name)

COMBOS = ("b_lo*J_hi", "b_lo*J_hi*tau6", "b_lo*tau6", "J_hi*tau6", "b/1.9 (G3a top)", "b/1.9*J_hi", "b_lo*J0.3",
          "tau10", "b_lo*tau10")
for nm in COMBOS:
    rows = []
    for v in SPEEDS_FINE:
        p, pl, tau = combo(nm, v)
        mg, rho, lz = pm_exact(v, pl, tau)
        rows.append((mg['pm'], v, mg['fc'], rho, lz, mg['gm']))
    rows.sort()
    pmmin, vmin, fc, rho, lz, gm = rows[0]
    sub30 = sorted(set(r[1] for r in rows if r[0] < 30))
    sub45 = sorted(set(r[1] for r in rows if r[0] < 45))
    unst = [r[1] for r in rows if r[3] >= 1]
    print(f"{nm:18s} min PM {pmmin:6.1f} at {vmin:5.1f} m/s fc {fc:.2f} least-damped {lz[0]:.2f} Hz z {lz[1]:.2f} | "
          f"PM<45 {len(sub45)} pts [{sub45[0] if sub45 else '-'}..{sub45[-1] if sub45 else '-'}] | "
          f"PM<30 {len(sub30)} pts [{sub30[0] if sub30 else '-'}..{sub30[-1] if sub30 else '-'}] | unstable {len(unst)}")

# ---------------------------------------------------------------- 3. thresholds in b and J by speed
section("3. THRESHOLDS: the b-scale (J nominal 0.2) and the J (b nominal) at which PM = 45 / 30 / 0 (instability), by speed")
def thresh(v, kind, target):
    # bisection on the parameter; returns the parameter where PM crosses target (or None)
    p = fam["nominal"].at(v)
    def pmf(x):
        if kind == "b":
            pl = S.rigid(p.J, p.b * x, p.k)
        else:
            pl = S.rigid(x, p.b, p.k)
        c = S.Ctl(v, d=2)
        if target == 0:
            rho, _ = S.exact(c, pl)
            return 1 - rho      # >0 stable
        return S.margins(c, pl, npts=3000)['pm'] - target
    if kind == "b":
        lo, hi = 0.02, 1.0     # pm(hi) > target presumably, find largest x where pm < target
        if pmf(hi) < 0:
            return ">1"
        if pmf(lo) > 0:
            return "<0.02"
        for _ in range(30):
            m = 0.5 * (lo + hi)
            if pmf(m) < 0: lo = m
            else: hi = m
        return f"{hi:.3f} (b={p.b*hi:.2f})"
    else:
        lo, hi = 0.2, 20.0
        if pmf(lo) < 0:
            return "<0.2"
        if pmf(hi) > 0:
            return ">20"
        for _ in range(30):
            m = math.sqrt(lo * hi)
            if pmf(m) > 0: lo = m
            else: hi = m
        return f"{lo:.2f}"

for v in (3, 5, 8, 10, 12.5, 15, 17, 19, 22, 26, 30):
    p = fam["nominal"].at(v)
    out = [f"v {v:5.1f} (b {p.b:5.2f} k {p.k:5.1f} G {S.G_of_v(v)})"]
    for tg in (45, 30, 0):
        out.append(f"b-scale@PM{tg}: {thresh(v, 'b', tg)}")
    for tg in (45, 30, 0):
        out.append(f"J@PM{tg}: {thresh(v, 'J', tg)}")
    print(" | ".join(out))

# ---------------------------------------------------------------- 4. delay
section("4. DELAY: exact delay margin (extra whole ticks of transport before instability) and PM vs extra hold age")
for nm in ("nominal", "b_lo", "J_hi"):
    for v in (3, 8, 12.5, 19, 26, 30):
        p, pl, tau = S.member_at(fam, nm, v)
        c = S.Ctl(v, d=tau)
        dm = S.delay_margin_ticks(c, pl)
        pms = []
        for ea in (0, 2, 5, 10):
            c2 = S.Ctl(v, d=tau, extra_age=ea)
            pms.append(S.margins(c2, pl, npts=3000)['pm'])
        print(f"{nm:8s} v {v:5.1f}: delay margin {dm} ticks (ms) | PM with slot-4 late by 0/2/5/10 ticks: "
              + " / ".join(f"{x:.1f}" for x in pms))

# ---------------------------------------------------------------- 5. exact GM on the credible family at knot midpoints
section("5. EXACT GM (monodromy bisection) at knots and knot midpoints, nominal / b_lo / J_hi")
for nm in ("nominal", "b_lo", "J_hi", "tau6"):
    out = []
    for v in (4.0, 6.5, 10.25, 12.5, 15.75, 19.0, 22.5, 26.0, 30.0):
        p, pl, tau = S.member_at(fam, nm, v)
        c = S.Ctl(v, d=tau)
        out.append(f"{v:g}:{S.exact_gm(c, pl):.1f}")
    print(f"{nm:8s} GM dB  " + "  ".join(out))
