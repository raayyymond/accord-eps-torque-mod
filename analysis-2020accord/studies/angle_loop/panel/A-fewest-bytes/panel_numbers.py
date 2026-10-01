# -*- coding: utf-8 -*-
"""panel_numbers.py -- tracking (where A1's flat Ki shows its miss vs A2), Re(T/w) 5-25 Hz, M20/L20 vs V295, and
per-tier max |S| 5-30, for Designer A's A1 and A2.  ANALYSIS ONLY.  Uses harness_freq (validated) + panel_fast.
"""
from __future__ import annotations
import json, sys
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
import stab_lin as S           # noqa
import harness_freq as HF      # noqa
import c1r2_members as M       # noqa

OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "panel" / "A-fewest-bytes"
SPEEDS = (3, 5, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 26, 30)


def tracking(impl):
    print(f"\n--- {impl}: tracking (nominal plant), |T_ref| at 0.2/0.5 Hz (in-phase, DC-normalised), turn-hold |T|@0.05Hz, "
          f"group delay @0.2Hz, M20, L20/V295 ---")
    print(f"{'v':>5} {'hold':>6} {'tg0.2':>6} {'tg0.5':>6} {'gd0.2ms':>8} {'M20':>5} {'L20':>6} {'L20/V295':>9} {'fc':>5} {'PM':>6}")
    rows = {}
    for v in SPEEDS:
        p = M.FAM["nominal"].at(v)
        hp = HF.Plant(J=p.J, b=p.b, k=p.k, tau=p.tau_ms)
        c = PS.hf_ctl(v, impl)
        m = HF.metrics(c, hp, exact=False)
        m295 = HF.metrics(HF.V295, hp, exact=False)
        print(f"{v:5.1f} {m['hold']:6.3f} {m['trkn_min']:6.3f} {m['trkn_max']:6.3f} "
              f"{m.get('taug02', float('nan')) if False else 0:8} {m['M20']:5.2f} {m['L20']:6.3f} "
              f"{m['L20']/m295['L20']:9.3f} {m['fc']:5.2f} {m['pm']:6.1f}")
        rows[v] = dict(hold=m["hold"], tg02=m["trkn_min"], tg05=m["trkn_max"], M20=m["M20"],
                       L20=m["L20"], L20_v295=m295["L20"], fc=m["fc"], pm=m["pm"], stiff=m.get("stiff_dc"))
    return rows


def retable(impl):
    print(f"\n--- {impl}: Re(T/w) T counts per deg/s (controller-only; Re<0 anti-damps a collocated mode at f) ---")
    fs = (5, 8, 10, 13, 15, 17, 20, 25)
    hdr = "  speed  " + "".join(f"{f:>7}Hz" for f in fs)
    print(hdr)
    for v in (3, 8, 12.5, 19, 26):
        p = M.FAM["nominal"].at(v)
        c = S.Ctl(v, kp=PS.kp_of(v, impl), ki=PS.ki_of(v, impl), kd=PS.kd_of(v), d=p.tau_ms, G=256)
        print(f"  {v:5.1f}  " + "".join(f"{F.re_tpr(c, f).real:+9.3f}" for f in fs))
    import stab_hf as HFR
    for nm, ctl in (("V295", HFR.V295), ("V294", HFR.V294)):
        print(f"  {nm:5s}  " + "".join(f"{HFR.torque_per_rate(ctl, f).real:+9.3f}" for f in fs))


def per_tier_S(impl):
    rows = json.loads((OUT / f"gate2_{impl}.json").read_text())
    for tier in ("A", "B"):
        rr = [r for r in rows if r["tier"] == tier]
        sm = max(rr, key=lambda r: r["S530"])
        tm = max(rr, key=lambda r: r["Tc530"])
        print(f"  {impl} tier {tier}: max |S| 5-30 {sm['S530']:+.1f} dB ({sm['member']}@{sm['v']}a{sm['age']}); "
              f"max |Tc| 5-30 {tm['Tc530']:+.1f} dB ({tm['member']}@{tm['v']}a{tm['age']})")


if __name__ == "__main__":
    for impl in ("A1", "A2"):
        tracking(impl)
    for impl in ("A1", "A2"):
        retable(impl)
    print("\n--- per-tier closed-loop |S|/|Tc| 5-30 Hz (tier-A bar: max > +3 dB = FAIL) ---")
    for impl in ("A1", "A2"):
        per_tier_S(impl)
