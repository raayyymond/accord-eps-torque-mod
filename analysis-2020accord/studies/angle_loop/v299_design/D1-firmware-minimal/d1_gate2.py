# -*- coding: utf-8 -*-
r"""d1_gate2.py -- GATE 2 (magnitude AND phase) for D1's stiffness levers, on the C3-r1 STABILITY refuter's independent
model (refute_stability/c3r1/c3r1_model.py, unchanged; it reproduces every published GATE-2 anchor -- rb_gate2.py).

Parts (each one batch on a Pool; total wall time printed; < 30 s):
  A  CONTROL: V298 itself (GB-P, Kp 112, Ki 40, Kd 48 fresh) at theta = 0, every gated member x frame x hold offset e,
     speeds 1..35 (coarse) -> must give 0 fails (it did for C3B-P on the full grid).
  B  LOW-SPEED BIG-ANGLE Kp (the Kp(idx) schedule, idx = 0.6177 |theta_sp deg|): Kp 112 / 168 / 224 at the operating
     points theta_op in {110, 180, 270, 360} deg (k -> k sech^2(theta/sat(v)), the refuter's F1 form) at 2..10 m/s,
     PID and I-frozen PD, every gated member x frame x e in {-1, 0, 5, 10}.
  C  LOW-SPEED ROW-0 G: GB-P with knot-0 G 1178 -> 1400 / 1600 (theta = 0 and the op-points), 2..9 m/s.
  D  HIGHWAY G x1.25 (knots >= 4032) at theta = 0 and the curve-hold op-points a 1.0..2.5 m/s^2, 15..30 m/s.
Bars (rb_gate2): tier-A singles PM >= 45 (e <= 0) / 30 (aged e > 0); tier-B combined 30; GM_up >= 6 dB; 5-30 Hz |T| peak
<= +3 dB.  The exact periodic rho is computed wherever PM < 32 deg.
"""
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "refute_stability" / "c3r1"))
sys.path.insert(0, str(AL / "c3" / "rev2B"))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402
import rb_table as T  # noqa: E402

F = S.F
SCR = HERE.parents[4] / "_scratch" / "v299_D1"   # the big row arrays live in the gitignored scratch
SCR.mkdir(parents=True, exist_ok=True)
B530 = (F >= 5) & (F <= 30)
GBP = [tuple(r) for r in T.GB_P]
GF = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
GATED = S.SINGLE + S.COMBINED
SR, LWB = 16.0, 2.83


def rows_g0(g0):
    r = [list(x) for x in GBP]
    X0, X1, G1 = r[0][0], r[1][0], r[1][1]
    r[0][1] = g0
    r[0][2] = int(round((G1 - g0) * 4096 / (X1 - X0)))
    return [tuple(x) for x in r]


def rows_hi(scale):
    r = [list(x) for x in GBP]
    for i in range(len(r)):
        if r[i][0] >= 4032:
            r[i][1] = int(round(r[i][1] * scale))
    for i in range(len(r) - 1):                                  # re-slope every segment to stay linear between knots
        if r[i + 1][0] != 0xFFFF:
            r[i][2] = int(round((r[i + 1][1] - r[i][1]) * 4096 / (r[i + 1][0] - r[i][0])))
        else:
            r[i][2] = 0
    return [tuple(x) for x in r]


DES = {
    "V298": M.Design("V298", "fresh", kp=112, ki=40, kd=48, rows=tuple(GBP)),
    "Kp168": M.Design("Kp168", "fresh", kp=168, ki=40, kd=48, rows=tuple(GBP)),
    "Kp224": M.Design("Kp224", "fresh", kp=224, ki=40, kd=48, rows=tuple(GBP)),
    "G0-1400": M.Design("G0-1400", "fresh", kp=112, ki=40, kd=48, rows=tuple(rows_g0(1400))),
    "G0-1600": M.Design("G0-1600", "fresh", kp=112, ki=40, kd=48, rows=tuple(rows_g0(1600))),
    "Ghi1.25": M.Design("Ghi1.25", "fresh", kp=112, ki=40, kd=48, rows=tuple(rows_hi(1.25))),
    "Kd36": M.Design("Kd36", "fresh", kp=112, ki=40, kd=36, rows=tuple(GBP)),
    "Kd24": M.Design("Kd24", "fresh", kp=112, ki=40, kd=24, rows=tuple(GBP)),
}


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


def bar(mem, e):
    return (45.0 if e <= 0 else 30.0) if mem in S.SINGLE else 30.0


def evalpt(des, pl, v, chans, e, kap, jb, noI):
    Pt, Pw = chans[jb]
    Cth, Cw, Cref = M.controller(des, v, F, e, kap, noI=noI)
    L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
    PM, FC, GMu = M.pm_gm(L, F)
    Sx = 1 / (1 + L)
    pk = 20 * math.log10(max(np.abs(L * Sx)[B530].max(), np.abs(M.Kout(F) * Cref * Pt * Sx)[B530].max(), 1e-9))
    return PM, FC, GMu, pk


def work(args):
    part, mem, v, thetas, dnames, es = args
    res = []
    for th in thetas:
        pl = M.member(mem, v)
        if th:
            pl.k *= 1 - math.tanh(th / sat(v)) ** 2
        chans = {jb: M.plant_channels(pl, F, jb, 0.0) for jb in (1.0, 1 / 1.155)}
        for dn in dnames:
            for noI in (False, True):
                for e in es:
                    for fn, kap, jb in GF:
                        PM, FC, GMu, pk = evalpt(DES[dn], pl, v, chans, e, kap, jb, noI)
                        rho = 0.0
                        if PM < 32.0:
                            rho = M.Periodic(DES[dn], pl, v, e=e, kappa=kap, jb=jb, noI=noI).rho_ring()[0]
                        res.append((part, dn, mem, v, th, noI, e, fn, PM, FC, GMu, pk, rho, bar(mem, e)))
    return res


def theta_of_a(v, a):
    return SR * LWB * a / (v * v) * 180 / math.pi


def jobs():
    J = []
    if len(sys.argv) > 1 and sys.argv[1] == "kd":
        # part E: the Kd(idx) schedule -- Kd lowered only where |theta_sp| >= 36 deg (idx 22); op-points 36..360 deg
        for m in GATED:
            for v in (2.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0):
                J.append(("E", m, v, (36.0, 60.0, 110.0, 180.0, 270.0), ("V298", "Kd36", "Kd24"), (-1, 0, 10)))
        return J
    for m in GATED:
        for v in (1.0, 2.0, 3.1, 5.0, 8.0, 10.0, 11.75, 14.0, 17.5, 22.0, 26.9, 30.0, 35.0):
            J.append(("A", m, v, (0.0,), ("V298",), (-1, 0, 5, 10)))
        for v in (2.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0):
            J.append(("B", m, v, (110.0, 180.0, 270.0, 360.0), ("V298", "Kp168", "Kp224"), (-1, 0, 10)))
            J.append(("C", m, v, (0.0, 110.0, 270.0), ("G0-1400", "G0-1600"), (-1, 0, 10)))
        for v in (15.0, 17.5, 20.0, 22.5, 26.9, 30.0):
            ths = (0.0,) + tuple(theta_of_a(v, a) for a in (1.0, 1.5, 2.0, 2.5))
            J.append(("D", m, v, ths, ("V298", "Ghi1.25"), (-1, 0, 10)))
    return J


def summarize(R):
    out = []
    keyf = lambda r: (r[0], r[1], r[5])  # noqa: E731
    groups = {}
    for r in R:
        groups.setdefault(keyf(r), []).append(r)
    out.append("part design loop | n  PM<bar  GM<6  pk>3  rho>=1 | worst PM-bar (PM/bar @ member v theta e frame) | min GM")
    for k in sorted(groups):
        X = groups[k]
        pmf = [r for r in X if r[8] < r[13]]
        gmf = [r for r in X if r[10] < 6.0]
        pkf = [r for r in X if r[11] > 3.0]
        un = [r for r in X if r[12] >= 1.0]
        w = min(X, key=lambda r: r[8] - r[13])
        g = min(X, key=lambda r: r[10])
        out.append(f"{k[0]} {k[1]:8s} {'PD ' if k[2] else 'PID'} | {len(X):5d} {len(pmf):5d} {len(gmf):5d} {len(pkf):5d} "
                   f"{len(un):5d} | {w[8]-w[13]:+6.1f} ({w[8]:.1f}/{w[13]:.0f} @ {w[2]} {w[3]} th{w[4]:.0f} e{w[6]} {w[7]}) "
                   f"| {g[10]:.1f} dB @ {g[2]} {g[3]} th{g[4]:.0f}")
    # per-speed worst PM for part B (designs x theta), PID only, tier A singles e<=0
    out.append("")
    out.append("B detail: worst PM over gated members/frames/e (PID | PD) by speed and theta_op, per design")
    for dn in ("V298", "Kp168", "Kp224"):
        for th in (110.0, 180.0, 270.0, 360.0):
            row = []
            for v in (2.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0):
                X = [r for r in R if r[0] == "B" and r[1] == dn and r[4] == th and r[3] == v]
                a = min(r[8] - r[13] for r in X if not r[5])
                b = min(r[8] - r[13] for r in X if r[5])
                row.append(f"{a:+5.0f}|{b:+4.0f}")
            out.append(f"  {dn:6s} th{th:4.0f}: " + " ".join(row))
    out.append("  (columns v = 2 3.1 4 5 6 7 8 9 10 m/s; entries = worst PM minus its bar, PID|PD)")
    return out


if __name__ == "__main__":
    t0 = time.time()
    J = jobs()
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, J, chunksize=2) for r in rr]
    if len(sys.argv) > 1 and sys.argv[1] == "kd":
        o = HERE / "out"
        np.save(SCR / "d1_gate2_kd_rows.npy", np.array([tuple(map(str, r)) for r in R]))
        print(f"part E rows saved ({len(R)}), wall {time.time() - t0:.1f} s")
        sys.exit(0)
    out = [f"d1_gate2: {len(J)} jobs, {len(R)} loop evaluations"] + summarize(R)
    out.append(f"wall {time.time() - t0:.1f} s")
    o = HERE / "out"
    o.mkdir(exist_ok=True)
    (o / "d1_gate2.txt").write_text("\n".join(out), encoding="utf-8")
    np.save(SCR / "d1_gate2_rows.npy", np.array([tuple(map(str, r)) for r in R]))
    print("\n".join(out))
