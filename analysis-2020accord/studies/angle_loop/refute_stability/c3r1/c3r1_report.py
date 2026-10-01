# -*- coding: utf-8 -*-
"""c3r1_report.py -- tables from sweep_<tag>.npz, and the exact periodic rho / ring at every binding point.
python c3r1_report.py [tag]  -> _scratch/.../report_<tag>.txt"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402

tag = sys.argv[1] if len(sys.argv) > 1 else "base"
Z = np.load(M.OUT / f"sweep_{tag}.npz")
A = Z["arr"]                      # members, grid, des, loops, es, frames, met
MEM, GRID, DES, LOOPS, ES, FR = [list(Z[k]) for k in ("members", "grid", "des", "loops", "es", "frames")]
GRID = [float(g) for g in GRID]
ES = [int(e) for e in ES]
iPM, iFC, iGM, iPK, iL20 = range(5)
D = M.designs()
FRAMES = {f[0]: f for f in S.FRAMES}
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))  # noqa: E731
GF = [FR.index(f) for f in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
PHYS = [FR.index(f) for f in ("FAc", "FBc", "FAo", "FBo")]


def tiers(mem, e, strict=False):
    if mem in S.SINGLE:
        if e <= 0:
            return 45.0
        return 45.0 if strict else 30.0
    if mem in S.COMBINED:
        return 30.0
    return None


def binding(di, li, mems, es, frames, metric=iPM, sel=None):
    best = (math.inf, None)
    for mi, m in enumerate(MEM):
        if m not in mems:
            continue
        for ei, e in enumerate(ES):
            if e not in es:
                continue
            for fi in frames:
                col = A[mi, :, di, li, ei, fi, metric]
                j = int(np.nanargmin(col))
                if col[j] < best[0]:
                    best = (float(col[j]), (m, GRID[j], e, FR[fi], float(A[mi, j, di, li, ei, fi, iFC])))
    return best


def exact_at(dn, pt, noI=False, fade=1.0, kds=1.0):
    m, v, e, fr, _ = pt
    _, kap, jb = FRAMES[fr]
    pl = M.light_b(v) if m == "light_b" else M.member(m, v)
    rho, f, z, _ = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb, noI=noI, fade=fade, kd_scale=kds).rho_ring()
    return f"rho {rho:.4f}, least-damped pole {f:.2f} Hz zeta {z:.3f}"


for di, dn in enumerate(DES):
    P("=" * 110)
    P(dn)
    li = LOOPS.index("PID")
    # gate counts
    nfail = {"A": 0, "B": 0, "A_strict": 0, "GM": 0, "PK": 0, "L20": 0}
    fails = {}
    for mi, m in enumerate(MEM):
        for ei, e in enumerate(ES):
            bar = tiers(m, e)
            bar_s = tiers(m, e, strict=True)
            if bar is None:
                continue
            for fi in GF:
                pm = A[mi, :, di, li, ei, fi, iPM]
                gm = A[mi, :, di, li, ei, fi, iGM]
                pk = A[mi, :, di, li, ei, fi, iPK]
                l20 = A[mi, :, di, li, ei, fi, iL20]
                nb = int(np.sum(pm < bar))
                key = "A" if bar == 45 else "B"
                nfail[key] += nb
                nfail["A_strict"] += int(np.sum(pm < bar_s)) if bar_s == 45 and m in S.SINGLE else 0
                nfail["GM"] += int(np.sum(gm < 6))
                nfail["PK"] += int(np.sum(pk > 3))
                nfail["L20"] += int(np.sum(l20 > 1.0))
                if nb:
                    fails.setdefault((m, e), []).append((FR[fi], nb, float(np.nanmin(pm))))
    P(f"  GATED fails (PID; credible set; e -1..10; gated frames): tier A (45) {nfail['A']}, tier B (30) {nfail['B']},"
      f" strict aged singles (45) {nfail['A_strict']}, GM<6 {nfail['GM']}, peak>+3dB {nfail['PK']}, L20>V295 {nfail['L20']}")
    for (m, e), v in sorted(fails.items()):
        P(f"     FAIL {m} e{e}: " + "; ".join(f"{fr} {n} pts min {pm:.1f}" for fr, n, pm in v))
    # minima by category and hold offset
    for lab, mems, es, bar in (("tier A singles, ages 1-10 (e0)", S.SINGLE, [0], 45),
                               ("tier A singles, ages 0-9 (e-1)", S.SINGLE, [-1], 45),
                               ("aged singles e1..e10 (strict 45 / R2 30)", S.SINGLE, list(range(1, 11)), 30),
                               ("combined, e -1..10", S.COMBINED, ES, 30),
                               ("combined excl. ms_free x, e -1..10", tuple(c for c in S.COMBINED if "ms_free" not in c), ES, 30),
                               ("ms_free x {b_lo, b_q}, e -1..10", ("b_lo*ms_free", "b_q*ms_free"), ES, 30)):
        pm, pt = binding(di, li, mems, es, GF)
        P(f"  min PM {lab:42s}: {pm:5.1f}  at {pt[0]}@{pt[1]} e{pt[2]} {pt[3]} fc {pt[4]:.2f}  [{exact_at(dn, pt)}]")
    P("  min PM per hold offset e (gated set, gated frames):")
    for e in ES:
        pa, pta = binding(di, li, S.SINGLE, [e], GF)
        pb, ptb = binding(di, li, S.COMBINED, [e], GF)
        P(f"     e{e:<3d} (ages {e + 1}-{e + 10}): singles {pa:5.1f} ({pta[0]}@{pta[1]} {pta[3]}) | combined {pb:5.1f} "
          f"({ptb[0]}@{ptb[1]} {ptb[3]})")
    pm, pt = binding(di, li, S.SINGLE + S.COMBINED, ES, PHYS)
    P(f"  min PM at the PHYSICAL frame points (FAc/FBc/FAo/FBo), credible set, all e: {pm:.1f} at {pt}")
    gm, ptg = binding(di, li, S.SINGLE + S.COMBINED, ES, GF, metric=iGM)
    P(f"  min GM up (PID, gated): {gm:.1f} dB at {ptg}")
    pkmax = np.nanmax(A[[MEM.index(m) for m in S.SINGLE + S.COMBINED]][:, :, di, li][:, :, :, GF, iPK])
    P(f"  max 5-30 Hz closed-loop peak (|Tc|,|Tref|), gated: {pkmax:+.2f} dB")
    l20max = np.nanmax(A[[MEM.index(m) for m in S.SINGLE + S.COMBINED]][:, :, di, li][:, :, :, GF, iL20])
    P(f"  max |L(20 Hz)| / V295's (same member, speed, frame, e): {l20max:.3f}")
    P("  REPORT members (min PM over all e, gated frames):")
    for m in S.REPORT:
        pm, pt = binding(di, li, (m,), ES, GF)
        pm0, pt0 = binding(di, li, (m,), [0], [0])
        P(f"     {m:20s} {pm:6.1f} at {pt[1]} e{pt[2]} {pt[3]} fc {pt[4]:.2f} | nominal frame e0: {pm0:6.1f} at {pt0[1]}")
    # other loop states
    for ln, noI, fade, kds in S.LOOPS[1:]:
        lj = LOOPS.index(ln)
        pm, pt = binding(di, lj, S.SINGLE + S.COMBINED, ES, GF)
        gm, ptg = binding(di, lj, S.SINGLE + S.COMBINED, ES, GF, metric=iGM)
        P(f"  loop {ln:7s}: min PM {pm:6.1f} at {pt[0]}@{pt[1]} e{pt[2]} {pt[3]} fc {pt[4]:.2f} [{exact_at(dn, pt, noI, fade, kds)}];"
          f" min GM {gm:.1f} dB at {ptg[0]}@{ptg[1]} e{ptg[2]} {ptg[3]}")
        # count < bars
        n = 0
        for mi, m in enumerate(MEM):
            for ei, e in enumerate(ES):
                bar = tiers(m, e)
                if bar is None:
                    continue
                n += int(np.sum(A[mi, :, di, lj, ei][:, GF, iPM] < bar))
        P(f"           points below the tier bars: {n}")
(Path(M.OUT) / f"report_{tag}.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
