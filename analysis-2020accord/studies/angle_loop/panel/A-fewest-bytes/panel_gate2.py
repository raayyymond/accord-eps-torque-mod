# -*- coding: utf-8 -*-
"""panel_gate2.py -- GATE 2 for Designer A, FINAL configs A1 (scale 1.0, flat Ki 80) and A2 (scale 0.72, Ki(v)=0.5 Kp),
on the FULL credible set (c1r2_members).  Two methods: panel_fast's vectorised LTI FRF (PM min-over-crossings, LTI GM,
Ms, |S|/|Tc| 5-30 Hz, Re(T/w) 13/20, M20) validated == stab_lin, and stab_lin.exact (periodic rho + poles) for
stability and the least-damped 5-50 Hz pole.  exact_gm is spot-checked on the worst points.  ANALYSIS ONLY.

FAIL (written before the run):
  tier A: PM < 45 | periodic rho >= 1 | LTI GM < 6 | 5-50 Hz pole zeta < 0.2 | M20 > 3.58 | |Tc|/|S| 5-30 Hz > +3 dB
  tier B: PM < 30 | periodic rho >= 1 | LTI GM < 6
  Re(T/w) 20 Hz above V295's at any speed/age
usage: python panel_gate2.py A1|A2
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[1] / "c1"),
           str(HERE.parents[1] / "refute_stability"), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import os
os.environ.setdefault("C1_VARIANT", "r2")
import panel_schedules as PS   # noqa
import panel_fast as F         # noqa
import c1r2_members as M       # noqa
import stab_lin as S           # noqa
import stab_hf as HFR          # noqa

OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "panel" / "A-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)
GRID = sorted(set([round(x, 2) for x in np.arange(1.5, 28.01, 1.0)] + [3.1, 8.0, 11.0, 11.9, 12.5, 17.0, 26.9]))
AGES = (0, 10)
V295_RE13 = float(HFR.torque_per_rate(HFR.V295, 13.0).real)
V295_RE20 = float(HFR.torque_per_rate(HFR.V295, 20.0).real)
V294_RE20 = float(HFR.torque_per_rate(HFR.V294, 20.0).real)


def run(impl):
    names = M.TIER_A + M.TIER_B
    rows = []
    t0 = time.time()
    for n in names:
        tier = "A" if n in M.TIER_A else "B"
        for v in GRID:
            pl, tau, base_ea, (J, b, k) = M.member(n, v)
            for ax in AGES:
                ea = base_ea + ax
                c = S.Ctl(v, kp=PS.kp_of(v, impl), ki=PS.ki_of(v, impl), kd=PS.kd_of(v), d=tau, extra_age=ea, G=256)
                mg = F.margins(c, pl)
                rho, poles = S.exact(c, pl)
                hfp = [q for q in poles if 5.0 <= q[0] <= 50.0]
                rows.append(dict(member=n, tier=tier, v=v, age=ax, pm=mg["pm"], gm=mg["gm_db"], Ms=mg["Ms"],
                                 Tc530=mg["Tc530_db"], S530=mg["S530_db"], rho=rho,
                                 hfz=(hfp[0][1] if hfp else float("nan")), hff=(hfp[0][0] if hfp else float("nan")),
                                 re13=F.re_tpr(c, 13.0).real, re20=F.re_tpr(c, 20.0).real, m20=F.m20(c)))
    (OUT / f"gate2_{impl}.json").write_text(json.dumps(rows, default=float))
    summarize(impl, rows)
    print(f"[{time.time()-t0:.0f} s]")


def summarize(impl, rows):
    print("\n" + "=" * 100)
    print(f"  {impl}  (Kp scale {PS.KP_SCALE[impl]}, Ki {'flat '+str(PS.A1_KI_FLAT) if impl=='A1' else 'Ki/Kp=0.5 sched'}, Kd 20)")
    print(f"  Kp record Y {PS.KP_Y if impl=='A1' else PS.KP_Y_A2}  (key X {PS.KP_X})")
    print("=" * 100)
    for tier, thr in (("A", 45.0), ("B", 30.0)):
        rr = [r for r in rows if r["tier"] == tier]
        wpm = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        wgm = min(rr, key=lambda r: r["gm"])
        nun = sum(1 for r in rr if r["rho"] >= 1.0)
        nfail = sum(1 for r in rr if r["rho"] >= 1.0 or (np.isfinite(r["pm"]) and r["pm"] < thr))
        wz = min((r for r in rr if np.isfinite(r["hfz"])), key=lambda r: r["hfz"], default=None)
        print(f"  tier {tier}: min PM {wpm['pm']:6.1f} ({wpm['member']}@{wpm['v']}a{wpm['age']}); "
              f"min LTI GM {wgm['gm']:5.1f} dB ({wgm['member']}@{wgm['v']}a{wgm['age']}); "
              f"unstable {nun}; PM<{thr:.0f}-or-unstable {nfail}"
              + (f"; min 5-50Hz pole z {wz['hfz']:.2f}@{wz['hff']:.1f}Hz" if wz else ""))
    m20 = max(r["m20"] for r in rows)
    re13 = min(r["re13"] for r in rows)
    re20 = min(r["re20"] for r in rows)
    s530 = max(r["S530"] for r in rows)
    tc530 = max(r["Tc530"] for r in rows)
    ms = max(r["Ms"] for r in rows)
    print(f"  max M20 {m20:.2f} (V295 3.58);  worst Re(T/w) 13Hz {re13:+.3f} (V295 {V295_RE13:+.3f}); "
          f"20Hz {re20:+.3f} (V295 {V295_RE20:+.3f}, V294 {V294_RE20:+.3f})")
    print(f"  max |S| 5-30 {s530:+.1f} dB; max |Tc| 5-30 {tc530:+.1f} dB; max Ms {ms:.2f}")
    nn = [r for r in rows if r["member"] == "nominal"]
    print(f"  nominal: min PM {min(r['pm'] for r in nn):.1f}, min LTI GM {min(r['gm'] for r in nn):.1f} dB, "
          f"max M20 {max(r['m20'] for r in nn):.2f}")
    # spot exact_gm on the 3 worst-PM points
    wr = sorted(rows, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)[:3]
    for r in wr:
        pl, tau, bea, _ = M.member(r["member"], r["v"])
        c = S.Ctl(r["v"], kp=PS.kp_of(r["v"], impl), ki=PS.ki_of(r["v"], impl), kd=20, d=tau, extra_age=bea + r["age"], G=256)
        egm = S.exact_gm(c, pl)
        print(f"    exact_gm @ {r['member']}@{r['v']}a{r['age']} (PM {r['pm']:.1f}): {egm:.1f} dB, rho {r['rho']:.4f}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "A1")
