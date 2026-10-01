# -*- coding: utf-8 -*-
"""ds_explore2.py -- round 2: the envelope now includes the brief's 20 Hz rules (M20 <= V295, Re(T/w)20 >= V295 at hold
age 0 and 10, L20 <= V295 per tier-A member).  Refines the lead placement/strength with the fresh D, the D-on-E gain,
and the cascade gains.  ANALYSIS ONLY.  usage: python ds_explore2.py  (writes ds_explore2_out.txt)"""
import sys, time, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as M, ds_gate2 as G2
import ds_explore as X

def cands():
    c = []; A = c.append
    A(M.Des("B0 C1r2 structure (held D Kd20)"))
    for kD in (16, 20, 24):
        A(M.Des(f"D2a fresh K_D{kD}", dsrc="op", dop="fresh_rate", kd=round(kD / X.KD_PER_FRESH)))
    A(M.Des("D1b fine K_D20", dsrc="op", dop="fine", kd=72, dop_k=8))
    for m, kh in ((4, 1), (4, 2), (3, 3), (3, 2), (5, 1)):
        for pl in ("fwd", "fb"):
            A(M.Des(f"D2{'b' if pl == 'fwd' else 'c'} {pl} lead m{m} kh{kh} +fresh20", lead=pl, lead_beta=2.0 ** -m,
                    lead_kh=kh, dsrc="op", dop="fresh_rate", kd=34))
    for kde in (200, 256, 320):
        A(M.Des(f"D1a D-on-E Kd{kde}", dsrc="E", kd=kde))
    for kp, ki in ((40, 10), (40, 20), (32, 16), (46, 12), (40, 5)):
        A(M.Des(f"D3b cascade fresh Kp{kp} Ki{ki}", kind="cascade", kp=kp, ki=ki, ka=4.0, dsrc="none", cop="fresh"))
    for kp, ki in ((24, 12), (16, 8), (24, 6)):
        A(M.Des(f"D3a cascade held Kp{kp} Ki{ki}", kind="cascade", kp=kp, ki=ki, ka=4.0, dsrc="none"))
    return c

if __name__ == "__main__":
    lines = []
    P = lambda s="": (print(s, flush=True), lines.append(s))
    t0 = time.time()
    res = {}
    for des in cands():
        e = G2.envelope(des, members=G2.GATED, grid=X.SPEEDS)
        sc = X.score(des, e["env"])
        res[des.name] = dict(env=e["env"], bind=e["bind"])
        P(f"{des.name:36s} T/deg: " + " ".join(f"{0.1602 * X.p_per_deg(des, e['env'][v]):4.0f}" for v in X.SPEEDS)
          + f" | M20 {sc['m20']:4.2f} Re20 a0 {sc['re0']:+.2f} a10 {sc['re10']:+.2f} | Tr15 "
          + " ".join(f"{m:.2f}<{p:+.0f}" for m, p in sc["trk"][15.0]) + " | Tr22 "
          + " ".join(f"{m:.2f}<{p:+.0f}" for m, p in sc["trk"][22.0]) + f" [{time.time() - t0:.0f}s]")
        P("   bind: " + " ".join(f"{v:g}:{e['bind'][v]}" for v in X.SPEEDS))
    P("speeds: " + " ".join(f"{v:g}" for v in X.SPEEDS) + "   (V295 under ema: M20 3.38, Re20 a0 -0.82 a10 -0.89)")
    (HERE / "ds_explore2_out.txt").write_text("\n".join(lines), encoding="utf-8")
    (G2.OUT / "explore2.json").write_text(json.dumps(res))
