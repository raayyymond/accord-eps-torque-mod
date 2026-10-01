# -*- coding: utf-8 -*-
r"""g_gate.py -- GATE 2 for designer G's implementations on the EXTENDED credible set, every grid speed (1-35 m/s at
0.25 incl. the plant knots), with the common scorer's extractor (score_freq.metrics_from via g_ext.metrics_ext) and
pm_fixed, plus the EXACT periodic rho / least-damped pole (g_exact, == ds_model.Lifted to 1.7e-14) on every point and the
exact gain margin on each member's binding point.  ANALYSIS ONLY.

Bars (written before the run): tier A PM >= 45, GM >= 6 dB, max(|Tc|, |Tref|) 5-30 Hz <= +3 dB, M20 <= V295's, L20 <=
V295's on the same member; tier B PM >= 30, GM >= 6 dB; every point exact rho < 1.  Two tierings are reported:
  'strict'  : the brief's tier A + the aged single corners (+h10) at 45 deg; the refuters' ms_free x {b_lo, b_q}
              products and b_lo*J_hi*tau6 at tier B
  'brief'   : the brief's literal set (aged single corners at 30 deg; the new products report-only)
Frames: every gated member at kappa 1 / 0.83 / 1.155 and under the motor-frame plant reading (|fb) for rate-operand D;
box10 at kappa 1 and |fb (frame-exact).
usage: python g_gate.py <impl id> [<impl id> ...]   -> _scratch/angle_loop/G-dop/gate_<id>.json, g_gate_<id>.txt"""
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
import g_ext as X  # noqa: E402
import g_exact as GE  # noqa: E402

GRID = X.G2.GRID
REPORT = tuple(m for m in X.G2.REPORT) + ("light_b",)
_IMPLS = {}


def impls():
    if not _IMPLS:
        for k, v in json.loads((X.OUT / "g_impls.json").read_text()).items():
            _IMPLS[k] = dict(v, rows=[tuple(r) for r in v["rows"]])
    return _IMPLS


def cand_of(iid):
    im = impls()[iid]
    return X.cand(iid, im["dkind"], im["rows"], im["kd"], ki=im.get("ki", 56), dop_k=2.0 ** im.get("sh", 6))


def point(args):
    iid, name, v = args
    im = impls()[iid]
    c = cand_of(iid)
    try:
        r = X.metrics_ext(c, name, v)
    except KeyError:
        return None
    pl, d, ea, jbk, kappa = X.plant_ext(name, v)
    G = r["G"]
    ex = GE.Exact(im["dkind"], pl, d, ea, G, 112, im.get("ki", 56), im["kd"], kappa=kappa, dop_k=2.0 ** im.get("sh", 6))
    rho, pf, pz = ex.rho_pole()
    l20ref = X.ref_L20("V295", name, v)
    out = dict(member=name, v=v, G=G, pm=r["pm"], pm_raw=r["pm_raw"], fc=r["fc"], gm=r["gm"], nc=r["ncross"],
               Tc530=r["Tc530"], Tr530=r.get("Tr530", -99.0), M20=r["M20"], L20=r["L20"], L20ref=l20ref, rho=rho,
               pole_f=pf, pole_z=pz, hold=r.get("hold", float("nan")), Tr163=r.get("Tr163", float("nan")))
    return out


def m20_ref_for(name, dkind):
    """V295's M20 in the member's PHYSICAL frame.  A rate-operand D reads the SAME lin-frame motor rate V295 reads, so the
    member's kappa scales both (the ratio is frame-robust); the angle-own D is frame-exact, so it is held against V295
    at the stricter of kappa 1 and 1/1.155 (V295's lin-frame operand under-reads gp-0x6a00's rate near centre)."""
    base, ea, kappa, jb = X._split(name)
    if dkind == "box10":
        return min(X.ref_m20("V295", kappa=1.0), X.ref_m20("V295", kappa=1.0 / X.S_C))
    return X.ref_m20("V295", kappa=kappa)


def fails_of(rows, strict=True, dkind="fresh"):
    m20c = {}
    out = []
    for r in rows:
        t = X.tier_of(r["member"], strict)
        bad = []
        if r["rho"] >= 1:
            bad.append("UNSTABLE")
        if t == "A":
            if r["member"] not in m20c:
                m20c[r["member"]] = m20_ref_for(r["member"], dkind)
            l20ref = r["L20ref"] / (X.S_C if dkind == "box10" else 1.0)
            if not (r["pm"] >= 45):
                bad.append("PM45")
            if not (r["gm"] >= 6):
                bad.append("GM6")
            if max(r["Tc530"], r["Tr530"]) > 3.0:
                bad.append("T530")
            if r["M20"] > m20c[r["member"]] * (1 + 1e-9):
                bad.append("M20")
            if r["L20"] > l20ref * (1 + 1e-9):
                bad.append("L20")
        elif t == "B":
            if not (r["pm"] >= 30):
                bad.append("PM30")
            if not (r["gm"] >= 6):
                bad.append("GM6")
        if bad:
            out.append((r["member"], r["v"], bad, round(r["pm"], 1)))
    return out


def run(iid, procs=6):
    t0 = time.time()
    im = impls()[iid]
    mems = X.gated_members(im["dkind"], strict=True, new=True)
    frames_rep = ("", "|k0.83") if im["dkind"] != "box10" else ("",)
    rep = [m + fr for m in REPORT for fr in frames_rep] + \
          [m + "|fb" for m in ("J1.3", "b_lo*J1.3", "b_q*J1.3", "light_b")] + \
          [m + "+h20" for m in ("nominal", "J_hi", "ms_free", "b_lo*J_hi", "b_q*J1.0")]
    jobs = [(iid, m, v) for m in mems + rep for v in GRID]
    with Pool(procs) as pool:
        res = [r for r in pool.map(point, jobs, chunksize=16) if r is not None]
    (X.OUT / f"gate_{iid}.json").write_text(json.dumps(res, default=float))
    report(iid, res, time.time() - t0)
    return res


def report(iid, res, sec=0.0):
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)
    im = impls()[iid]
    P(f"GATE 2 -- {iid}: {im['note']}  ({len(res)} points, {sec:.0f} s)")
    P(f"  table rows {im['rows']}  Kd {im['kd']}")
    nraw = sum(1 for r in res if abs(r["pm"] - r["pm_raw"]) > 1e-6)
    P(f"  points where pm_fixed != the shared formula: {nraw}  (min pm_raw there "
      f"{min((r['pm_raw'] for r in res if abs(r['pm'] - r['pm_raw']) > 1e-6), default=float('nan')):.1f}; "
      f"max rho there {max((r['rho'] for r in res if abs(r['pm'] - r['pm_raw']) > 1e-6), default=float('nan')):.4f})")
    P(f"  max exact rho over ALL points (gated + report): {max(r['rho'] for r in res):.5f}  "
      f"unstable points: {sum(1 for r in res if r['rho'] >= 1)}")
    for strict in (True, False):
        f = fails_of(res, strict, im['dkind'])
        P(f"  GATE-2 fails ({'strict' if strict else 'brief literal'} tiering): {len(f)}")
        byname = {}
        for m, v, bad, pm in f:
            byname.setdefault(m, []).append((v, bad, pm))
        for m, L in sorted(byname.items(), key=lambda kv: min(x[2] for x in kv[1])):
            vs = [x[0] for x in L]
            P(f"      {m:34s} v {min(vs):5.2f}-{max(vs):5.2f} ({len(L)} pts) worst PM {min(x[2] for x in L):5.1f}  "
              f"{sorted(set(b for x in L for b in x[1]))}")
    # per base member (over frames): min PM / speed / ring
    P("  per member (min over speed; the frame variant that binds):")
    P("    member                            tier  min PM (v, frame)                 min GM   max T530   least-damped "
      "pole (v)        max L20/V295")
    bases = {}
    for r in res:
        b = r["member"].split("|")[0]
        bases.setdefault(b, []).append(r)
    for b in sorted(bases, key=lambda k: ({"A": 0, "B": 1, "report": 2}[X.tier_of(k)], k)):
        rr = bases[b]
        w = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        lp = min(rr, key=lambda r: r["pole_z"] if np.isfinite(r["pole_z"]) else 9)
        fr = "|" + "|".join(w["member"].split("|")[1:]) if "|" in w["member"] else "nominal frame"
        P(f"    {b:34s} {X.tier_of(b):6s}{w['pm']:6.1f} ({w['v']:5.2f}, {fr:14s}) fc {w['fc']:4.2f}  "
          f"{min(r['gm'] for r in rr):6.1f}  {max(max(r['Tc530'], r['Tr530']) for r in rr):+6.1f}   "
          f"{lp['pole_f']:5.2f} Hz z {lp['pole_z']:.3f} ({lp['v']:5.2f})   "
          f"{max(r['L20'] / r['L20ref'] for r in rr if r['L20ref'] > 0):6.3f}")
    worst = max(res, key=lambda r: r["M20"] / m20_ref_for(r["member"], im["dkind"]))
    P(f"  M20 / V295's M20 in the same frame: max {worst['M20'] / m20_ref_for(worst['member'], im['dkind']):.3f}x "
      f"({worst['member']} @ {worst['v']}); at kappa 1: max {max(r['M20'] for r in res if '|k' not in r['member']) / X.ref_m20('V295'):.3f}x")
    (HERE / f"g_gate_{iid}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for iid in sys.argv[1:]:
        if iid.startswith("report:"):
            k = iid.split(":", 1)[1]
            report(k, json.loads((X.OUT / f"gate_{k}.json").read_text()))
        else:
            run(iid)
