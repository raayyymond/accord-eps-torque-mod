# -*- coding: utf-8 -*-
r"""cgf_gate2.py -- GATE 2 (exact periodic poles + LTI PM/GM/margins) for the Designer-C candidates over the FULL
factorial member set (c1r2_members) with hold ages 1-20, at the design speeds.  ANALYSIS ONLY.

For every member at every design speed, with the SCHEDULED Kp_eff(v)/Ki_eff(v) and Kd_eff 28 fresh-D:
  PM (min over |L|=1 crossings), exact GM (dB), stable?, least-damped <8 Hz (wheel) and 5-50 Hz (hf) mode (f, zeta),
  M20, L20, ReCr20, |T_ref| peak 1.6-3 Hz.
Also Re(T/w) 5-25 Hz vs V294/V295 (age 0 and age 10), on the nominal plant across speeds.

Tiers (gates written here, before the run):
  A  (tier A members): PM >= 45, exact GM >= 6 dB, stable, no 5-50 Hz pole zeta < 0.2
  B  (tier B, EXCLUDING the J1.0 x reduced-damping concession): PM >= 30, exact GM >= 6 dB, stable
  concession (J1.0 x {b_lo,b/1.9,b_q,bq10}): REPORTED, caught on-car by R3 (1.0-5.5 Hz ring, zeta<0.10)
  report: the rev-2 report members (J1.3, ms_free, light_b, ...)
20 Hz budget (nominal): M20 <= V295's, ReCr20 >= V295's (less anti-damping), no 5-30 Hz |T|,|T_ref| > +3 dB.

usage: python cgf_gate2.py [speeds...]   (default the design speeds)
"""
from __future__ import annotations

import json
import math
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(HERE), str(AL), str(AL / "c1"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cgf_freq as G                           # noqa: E402
import cgf_design as D                         # noqa: E402
import c1r2_members as M2                      # noqa: E402
import harness_freq as HF                      # noqa: E402

SPEEDS = [3.1, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0]
OUT = Path(os.environ["ACCORD_FIRMWARE_ROOT"]).parent / "accord-eps-torque-mod" / "_scratch" / "angle_loop" / "C-goal-first"
# repo-root scratch:
OUT = AL.parents[2] / "_scratch" / "angle_loop" / "C-goal-first"
OUT.mkdir(parents=True, exist_ok=True)


def is_concession(n):
    return ('J1.0' in n) and (('b_lo' in n) or ('b/1.9' in n) or ('b_q' in n) or ('bq10' in n))


def tier_of(n):
    if n in M2.TIER_A:
        return 'A'
    if n in M2.TIER_B:
        return 'concession' if is_concession(n) else 'B'
    return 'report'


ALL_MEMBERS = M2.TIER_A + M2.TIER_B + M2.REPORT


def ctl_for(v, ff=False):
    kp = D.kp_eff(v)
    return G.CtlC(kp=kp, ki=D.KI_BASE / 256.0 * D.G_at(v), kd=D.KD_EFF, op_hold="hold", d_hold="fresh_abe",
                 ff_gain=(1.0 if ff else 0.0))


def _job(args):
    name, v, ff = args
    c = ctl_for(v, ff)
    try:
        r = G.metrics(c, name, v, exact=True)
        gm = G.exact_gm_db(c, name, v)
    except Exception as e:  # noqa: BLE001
        return (name, v, dict(err=str(e)))
    out = dict(name=name, v=v, tier=tier_of(name), kp_eff=c.kp, pm=r['pm'], gm=gm, stable=r['stable'],
               wheel=r['wheel'], hf=r['hfmode'], M20=r['M20'], L20=r['L20'], ReCr20=r['ReCr20'],
               Tr163=r['Tr163'], Tc530=r['Tc530_db'], Tr530=r['Tr530_db'], fc=r['fc'], hold=r['hold'],
               trk_min=r['trk_min'], trk_max=r['trk_max'])
    return (name, v, out)


def run(ff=False):
    jobs = [(n, v, ff) for n in ALL_MEMBERS for v in SPEEDS]
    res = {}
    with Pool(12) as p:
        for name, v, out in p.imap_unordered(_job, jobs):
            res[(name, v)] = out
    tag = "ff" if ff else "noff"
    (OUT / f"gate2_{tag}.json").write_text(json.dumps({f"{k[0]}@{k[1]}": v for k, v in res.items()}, default=str))
    report(res, tag)
    return res


def report(res, tag):
    lines = []
    def pr(s=""):
        print(s); lines.append(str(s))
    pr(f"=== CGF GATE 2 ({tag}) -- Kd_eff {D.KD_EFF} fresh-D, schedule Kp_eff {D.kp_eff(15):.0f}@15 .. {D.kp_eff(26.9):.0f}@27 ===")
    # per-tier worst
    for tiername, bar in (("A", 45.0), ("B", 30.0), ("concession", None), ("report", None)):
        rows = [r for r in res.values() if r.get('tier') == tiername and 'err' not in r]
        if not rows:
            continue
        worst_pm = min((r['pm'] for r in rows if np.isfinite(r['pm'])), default=float('nan'))
        worst_gm = min((r['gm'] for r in rows if np.isfinite(r['gm'])), default=float('nan'))
        nunstable = sum(1 for r in rows if not r['stable'])
        subbar = [r for r in rows if bar and np.isfinite(r['pm']) and r['pm'] < bar]
        pr(f"\nTIER {tiername}: {len(rows)} points, min PM {worst_pm:.1f}, min exact GM {worst_gm:.1f} dB, "
           f"{nunstable} unstable" + (f", {len(subbar)} below PM {bar:.0f}" if bar else ""))
        if bar and subbar:
            for r in sorted(subbar, key=lambda x: x['pm'])[:8]:
                pr(f"   SUBBAR {r['name']:22s} v{r['v']:5.1f} PM {r['pm']:6.1f} GM {r['gm']:5.1f} "
                   f"wheel {r['wheel']} hf {r['hf']}")
        if tiername == "concession":
            for r in sorted(rows, key=lambda x: (x['name'], x['v'])):
                if r['v'] in (12.5, 15.0, 17.0, 19.0, 26.9):
                    pr(f"   {r['name']:22s} v{r['v']:5.1f} PM {r['pm']:6.1f} GM {r['gm']:5.1f} stable {int(r['stable'])} "
                       f"wheel {r['wheel'][0]:.2f}Hz z{r['wheel'][1]:.2f} ring zeta {r['wheel'][1]:.2f}")
    # the 20 Hz budget on nominal
    pr("\n--- 20 Hz budget (nominal) vs V295 ---")
    for v in SPEEDS:
        r = res[("nominal", v)]
        rv = HF.full(HF.V295, HF.plant_at("nominal", v))
        ok = (r['M20'] <= rv['M20'] + 1e-9) and (r['ReCr20'] >= rv['ReCr20'] - 1e-9)
        pr(f"  v{v:5.1f} M20 {r['M20']:.2f}/{rv['M20']:.2f} L20 {r['L20']:.4f}/{rv['L20']:.4f} "
           f"ReCr20 {r['ReCr20']:+.2f}/{rv['ReCr20']:+.2f} {'OK' if ok else 'OVER'}")
    # PM-by-member at design speeds (the deliverable table)
    pr("\n--- PM by member at design speeds (deg) ---")
    cols = ["nominal", "J_hi", "b_lo", "b_lo*J_hi", "b_q", "b_q*J_hi", "b_q*J_hi+h10", "b_q*J1.0", "b_q*J1.0+h10",
            "J1.0", "b_lo*J_hi2+h10", "light_b"]
    pr("  v   Kpe | " + " ".join(f"{c[:9]:>9}" for c in cols))
    for v in SPEEDS:
        row = []
        for c in cols:
            r = res.get((c, v))
            row.append(f"{r['pm']:9.1f}" if r and np.isfinite(r['pm']) else f"{'n/s' if r and not r['stable'] else '--':>9}")
        pr(f"  {v:5.1f} {D.kp_eff(v):4.0f} | " + " ".join(row))
    (HERE / f"gate2_{tag}_report.txt").write_text("\n".join(lines), encoding="utf-8")


def re_tw_table():
    """Re(T/w) 5-25 Hz vs V294/V295, nominal, age 0 and age 10."""
    lines = ["=== Re(T/w) T counts per deg/s, nominal, worst over speeds (age 0 / age 10) ==="]
    freqs = (5, 7, 10, 13, 15, 17, 20, 25)
    def worst(ctlfun, age):
        w = {f: 0.0 for f in freqs}
        for v in SPEEDS:
            c = ctlfun(v)
            c = G.replace(c, extra_age=age)
            r = G.metrics(c, "nominal", v, exact=False)
            for f in freqs:
                val = r[f"ReTw{f}"]
                if val < w[f]:
                    w[f] = val
        return w
    import harness_freq as HF2
    def v295c(v):
        return None
    # V294/V295 via harness_freq (held rate, d_src none): use HF Re_Cr at each freq
    def hf_retw(ctl, age):
        w = {f: 0.0 for f in freqs}
        for v in SPEEDS:
            c = HF2.replace(ctl, d=HF2.plant_at("nominal", v).tau)
            # age handled via hold ages in HF: emulate by extra ages -> use c.hold with ages range shift not supported;
            # approximate age 0 only for V294/V295 (they are the record's own age-0 numbers)
            for f in freqs:
                val = (HF2.C_fb(np.array([float(f)]), c)[0] / (1j * 2 * math.pi * f)).real
                if val < w[f]:
                    w[f] = val
        return w
    cgf0 = worst(lambda v: ctl_for(v), 0)
    cgf10 = worst(lambda v: ctl_for(v), 10)
    v295 = hf_retw(HF2.V295, 0)
    v294 = hf_retw(HF2.V294, 0)
    hdr = "  " + " ".join(f"{f:>6}Hz" for f in freqs)
    lines.append(hdr)
    lines.append("CGF age0  " + " ".join(f"{cgf0[f]:+7.2f}" for f in freqs))
    lines.append("CGF age10 " + " ".join(f"{cgf10[f]:+7.2f}" for f in freqs))
    lines.append("V295 age0 " + " ".join(f"{v295[f]:+7.2f}" for f in freqs))
    lines.append("V294 age0 " + " ".join(f"{v294[f]:+7.2f}" for f in freqs))
    txt = "\n".join(lines)
    print(txt)
    (HERE / "re_tw_table.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    if "--retw" in sys.argv:
        re_tw_table()
    else:
        run(ff=("--ff" in sys.argv))
