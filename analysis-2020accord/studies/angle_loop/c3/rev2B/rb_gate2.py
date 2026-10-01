# -*- coding: utf-8 -*-
r"""rb_gate2.py -- C3 rev2-B GATE 2, on the C3-r1 STABILITY refuter's INDEPENDENT model (c3r1_model), UNCHANGED except
for the design under test: the rev2-B tables (rb_table.GB_P / GB_F, G >= 512) and Ki 28 (F1), fresh D Kd 48 / held Kd 24.

Three readouts, all on c3r1_model (which reproduces every published GATE-2 anchor to |dPM| 0.1 and Re(T/w) 0.005):
  (1) theta = 0 GATE 2 over the R2 box (every gated member, the frame box, hold offsets e -1..10, the fine speed grid):
      the normal GATE-2 bars (tier A 45 native / 30 aged, tier B 30), GM >= 6 dB, no 5-30 Hz peak > +3 dB.
  (2) the OPERATING-POINT GATE 2 (refuter F1): k -> k * sech^2(theta_op / sat(v)) at a 1.0..2.5, v >= 8, every gated
      member, frame, e -- the margins the design scores its turn-hold on, and the EXACT periodic rho (instability).
  (3) the rate-invalid PI-only loop (refuter F3) at Ki 28: exact rho over the gated set.

usage: python rb_gate2.py [ki]   (default 28)
"""
import json
import math
import os
import sys
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
RS = HERE.parents[1] / "refute_stability" / "c3r1"
sys.path.insert(0, str(RS))
sys.path.insert(0, str(HERE))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402
import rb_table as T  # noqa: E402

KI = float(sys.argv[1]) if len(sys.argv) > 1 else 28.0
OUT = M.KIT / "_scratch" / "angle_loop" / "c3-rev2B"
OUT.mkdir(parents=True, exist_ok=True)
F = S.F

DES = {
    "C3B-P": M.Design("C3B-P", "fresh", kd=48, ki=KI, rows=tuple(T.GB_P)),
    "C3B-F": M.Design("C3B-F", "held", kd=24, ki=KI, rows=tuple(T.GB_F)),
    "V295": M.designs()["V295"],
}
SINGLE, COMBINED = S.SINGLE, S.COMBINED
MSF_PROD = ("b_lo*ms_free", "b_q*ms_free")
GATED = SINGLE + COMBINED                       # the brief's credible set (singles + combined), + ms_free products below
ES = tuple(range(-1, 11))
GF = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
B530 = (F >= 5) & (F <= 30)
GRID0 = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]
                   + [round(x, 2) for x in np.arange(7.0, 13.51, 0.05)]))
SR, LWB = 16.0, 2.83


def bar(mem, e):
    if mem in SINGLE:
        return 45.0 if e <= 0 else 30.0
    return 30.0


def theta_op(v, a):
    return SR * LWB * a / (v * v) * 180 / math.pi


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


# ---- (1) theta = 0 GATE 2 ----
def work0(args):
    mem, v = args
    pl = M.member(mem, v)
    chans = {jb: M.plant_channels(pl, F, jb, 0.0) for jb in (1.0, 1 / 1.155)}
    rows = []
    for dn in ("C3B-P", "C3B-F"):
        for e in ES:
            for fn, kap, jb in GF:
                Pt, Pw = chans[jb]
                Cth, Cw, Cref = M.controller(DES[dn], v, F, e, kap)
                L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                PM, FC, GMu = M.pm_gm(L, F)
                Sx = 1 / (1 + L)
                pk = 20 * math.log10(max(np.abs(L * Sx)[B530].max(), np.abs(M.Kout(F) * Cref * Pt * Sx)[B530].max(), 1e-9))
                rows.append((dn, mem, v, e, fn, PM, GMu, pk, bar(mem, e)))
    return rows


def gate0():
    jobs = [(m, v) for m in GATED + MSF_PROD for v in GRID0]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work0, jobs, chunksize=3) for r in rr]
    out = ["== (1) theta=0 GATE 2 (R2 box: singles+combined+ms_free products, frame box, e -1..10, fine grid) =="]
    for dn in ("C3B-P", "C3B-F"):
        for setname, mems in (("credible set (brief)", GATED), ("ms_free products", MSF_PROD)):
            X = [r for r in R if r[0] == dn and r[1] in mems]
            pmf = [r for r in X if r[5] < r[8]]
            gmf = [r for r in X if r[6] < 6.0]
            pkf = [r for r in X if r[7] > 3.0]
            w = min(X, key=lambda r: r[5] - r[8])
            out.append(f"{dn} {setname:22s}: PM-fails {len(pmf)}  GM<6dB {len(gmf)}  pk>+3dB {len(pkf)}  "
                       f"(worst PM {w[5]:.1f} vs bar {w[8]:.0f} at {w[1]}@{w[2]} e{w[3]} {w[4]})")
    return out


# ---- (2) operating-point GATE 2 (F1) ----
def work1(args):
    mem, v = args
    res = []
    for a in (1.0, 1.5, 2.0, 2.5):
        s2 = 1 - math.tanh(theta_op(v, a) / sat(v)) ** 2
        pl = M.member(mem, v)
        pl.k *= s2
        for fn, kap, jb in GF:
            Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
            for dn in ("C3B-P", "C3B-F"):
                for e in (-1, 0, 10):
                    Cth, Cw, _ = M.controller(DES[dn], v, F, e, kap)
                    L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                    PM, FC, GM = M.pm_gm(L, F)
                    rho = M.Periodic(DES[dn], pl, v, e=e, kappa=kap, jb=jb).rho_ring()[0] if PM < 32 else 0.0
                    res.append((dn, mem, v, a, fn, e, PM, GM, rho, bar(mem, e)))
    return res


def gate1():
    SP = sorted(set([round(x, 2) for x in np.arange(8.0, 30.01, 0.5)] + [8.0, 11.9, 17.0, 26.9]))
    jobs = [(m, v) for m in GATED + MSF_PROD for v in SP]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work1, jobs, chunksize=2) for r in rr]
    out = ["", "== (2) operating-point GATE 2 (F1: k*sech^2(theta_op/sat), a 1.0-2.5, v>=8) =="]
    for dn in ("C3B-P", "C3B-F"):
        X = [r for r in R if r[0] == dn]
        unst = [r for r in X if r[8] >= 1.0]
        out.append(f"{dn}: exact rho>=1 (UNSTABLE) at operating points: {len(unst)}"
                   + (f"  worst {max(unst, key=lambda r: r[8])[8]:.4f}" if unst else ""))
        for grp, mems in (("tier-A singles", SINGLE), ("tier-B non-ms_free", [m for m in COMBINED]),
                          ("ms_free products", list(MSF_PROD))):
            Y = [r for r in X if r[1] in mems]
            fails = [r for r in Y if r[6] < r[9]]
            vs = sorted(set(round(r[2], 1) for r in fails))
            aa = sorted(set(r[3] for r in fails))
            w = min(Y, key=lambda r: r[6] - r[9])
            out.append(f"   {grp:20s}: PM<bar {len(fails)}  worst PM {w[6]:.1f} (bar {w[9]:.0f}) at {w[1]}@{w[2]} a{w[3]} "
                       f"{w[4]} e{w[5]}" + (f"; fails at a{aa} v{vs[0]}..{vs[-1]}" if fails else ""))
    return out


# ---- (3) rate-invalid PI-only (F3) at this Ki ----
def work3(args):
    mem, v = args
    res = []
    for dn in ("C3B-P", "C3B-F"):
        for e in (0, 10):
            for jb in (1.0, 1 / 1.155):
                rho, f, z, _ = M.Periodic(DES[dn], pl_of(mem, v), v, e=e, jb=jb, kd_scale=0.0).rho_ring()
                res.append((dn, mem, float(v), e, jb, rho, f, z))
    return res


def pl_of(mem, v):
    return M.member(mem, v)


def doff():
    SP = sorted(set(list(np.arange(1.0, 35.01, 1.0)) + [3.1, 8.0, 11.9, 17.0, 26.9]))
    jobs = [(m, v) for m in GATED for v in SP]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work3, jobs, chunksize=3) for r in rr]
    out = ["", "== (3) rate-invalid PI-only loop (F3): exact rho, D=0 =="]
    for dn in ("C3B-P", "C3B-F"):
        X = [r for r in R if r[0] == dn]
        un = [r for r in X if r[5] >= 1.0]
        low = [r for r in X if r[7] < 0.10]
        out.append(f"{dn} D=0: {len(X)} pts; rho>=1 {len(un)}; zeta<0.10 {len(low)}"
                   + (f"; worst {max(un, key=lambda r: r[5])[5]:.5f} at {max(un, key=lambda r: r[5])[1]}" if un else ""))
        if un:
            out.append("   unstable members: " + str(sorted(set(r[1] for r in un))))
    return out


if __name__ == "__main__":
    out = [f"C3 rev2-B GATE 2 on the independent refuter model; Ki = {KI:.0f}; tables GB-P / GB-F (G >= 512)"]
    out += gate0()
    out += gate1()
    out += doff()
    (OUT / f"gate2_ki{int(KI)}.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
