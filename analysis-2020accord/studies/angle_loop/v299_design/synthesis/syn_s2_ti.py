# -*- coding: utf-8 -*-
r"""syn_s2_ti.py -- the composite's RATE CAP decided on the common S2 TI manoeuvre (D1c firmware + G4 O1 gate, lead 0,
takeover 0.4 s, clip x1.6): caps 200 / 250 / 300 deg/s, per seed and per member, 3 and 8 m/s.  ANALYSIS ONLY.
usage: python syn_s2_ti.py  (TI group only; ~10 s)"""
import importlib.util, json, os, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; V299 = HERE.parent; KIT = V299.parents[3]
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
_s = importlib.util.spec_from_file_location("s2_time_syn2", V299 / "scores" / "S2-time-nonlinear" / "s2_time.py")
S2 = importlib.util.module_from_spec(_s); sys.modules["s2_time_syn2"] = S2; _s.loader.exec_module(S2)
G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4); CLIP16 = (27.2, 24.8, 31.2, 27.2, 8.5, 4.5)
S2.CANDS = {k: S2.CANDS[k] for k in ("V298", "D1c")}
for cap in (2.0, 2.2, 2.5, 3.0):
    S2.FK[f"C{cap}"] = dict(cap_v=(cap, cap), clip=CLIP16, **G4)
    S2.CANDS[f"SYN-{int(cap*100)}"] = ("D1c", f"C{cap}", "composite cap sweep")
S2.FK["C2.5L6"] = dict(cap_v=(2.5, 2.5), clip=CLIP16, inst=1200.0, d600=8, o1lead=0.06, take=0.4)   # lead kept
S2.CANDS["SYN-250-lead06"] = ("D1c", "C2.5L6", "composite cap 250 with V298's O1 lead")
S2.CIDS = tuple(S2.CANDS)
if __name__ == "__main__":
    T0 = time.perf_counter(); rows = [S2._clean(r) for r in S2.grp_TI()]
    OUT = KIT / "_scratch" / "v299_SYN"; (OUT / "syn_s2_ti.json").write_text(json.dumps(rows), encoding="utf-8")
    L = ["| cand | v | member | t90 s per seed 0/1/2/3 | O1 eps per seed | hand-lost per seed | word p99 per seed | w pk | tap % | ovs | r48 | r1.6-3 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in S2.CIDS:
        for v in (3.0, 8.0):
            for m in ("r79F", "b_lo*J_hi"):
                rr = sorted([r for r in rows if r["cid"] == c and r["v"] == v and r["member"] == m], key=lambda r: r["s"])
                f = lambda k, fmt: "/".join(fmt % (r[k] if r[k] is not None else float("nan")) for r in rr)  # noqa: E731
                med = lambda k: float(np.median([r[k] for r in rr if r["s"] > 0 and r[k] is not None]))  # noqa: E731
                L.append(f"| {c} | {v:.0f} | {m} | {f('t90','%.2f')} | {f('o1_eps','%d')} | {f('hand_lost','%.2f')} | {f('w_p99','%.0f')} | "
                         f"{med('wpk'):.0f} | {100*med('tap_pk'):.0f} | {med('ovs'):.1f} | {med('r48'):.1f} | {med('r163'):.1f} |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s"); txt = "\n".join(L); print(txt); (OUT / "syn_s2_ti.md").write_text(txt, encoding="utf-8")
