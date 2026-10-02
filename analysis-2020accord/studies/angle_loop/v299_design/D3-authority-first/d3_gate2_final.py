# -*- coding: utf-8 -*-
r"""d3_gate2_final.py -- GATE 2 on D3a's EXACT table (G x1.2 below 8 m/s, V298 knots >= 10 m/s byte-identical), against
V298 on the same model and grid.  ANALYSIS ONLY.

MODEL: refute_stability/c3r1/c3r1_model.py UNCHANGED (the model rb_gate2.py cleared V298 on), as in d3_gate2.py.
D3a's table differs from V298's only below X = 2304 (10.0 m/s), so the grid is every 0.25 m/s from 1.0 to 10.5 plus
0.05 steps over 7.0-10.5 (the descent where the table changes slope).  Gated set: SINGLE + COMBINED (incl. the ms_free
products) x frames {nom, FA.83, FA1.155, FB.83, FB1.155} x hold offsets e {-1, 0, 10} x {PID, PD (I frozen)}.
Bars: PM 45 (tier-A singles, e <= 0) / 30 else; GM_up >= 6 dB; 5-30 Hz peak <= +3 dB.  Reported: |L(20 Hz)| / V295.
PART 2 = the OPERATING-POINT GATE 2 (refuter F1: k -> k sech^2(theta_op / sat(v)), a_lat 1.0-2.5 m/s^2) at 3.1-10.0 m/s
(rb_gate2 ran it at >= 8 only; D3 extends it down to where the table moves); PM / GM only (min PM printed).
TABLES: V298; D3a-flat = G x1.2 at both low knots (3.1 and 8.0 m/s) -- REJECTED by the op-point gate at 8 m/s;
D3a = G x1.2 at 3.1 m/s tapering to x1.0 at the 8.0 m/s knot (the D3 (a) table).
usage: python d3_gate2_final.py  -> _scratch/angle_loop/v299-D3/gate2_final.{txt,json}
"""
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "refute_stability" / "c3r1"))
import c3r1_model as M  # noqa: E402
import d3_common as D  # noqa: E402

SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6", "b_lo*ms_free", "b_q*ms_free")
GATED = SINGLE + COMBINED
S_C = 1.155
FRAMES = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / S_C),
          ("FB1.155", 1.155, 1 / S_C))
ES = (-1, 0, 10)
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 10.51, 0.25)] + [3.1, 8.0]
                  + [round(x, 2) for x in np.arange(7.0, 10.51, 0.05)]))
F = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 900), [5, 7, 10, 13, 15, 16, 17, 20, 25, 30]]))
I20 = int(np.argmin(abs(F - 20.0)))
B530 = (F >= 5) & (F <= 30)
TABLES = {"V298": D.GB_P, "D3a-flat": D.scaled_rows(1.2), "D3a": D.scaled_rows(1.2, mult_8=1.0)}


@dataclass
class Des(M.Design):
    tab: tuple = ()

    def G(self, v):
        return M.walk_G(self.tab, M.spd(v))


DES_OP = {k: Des(k, "fresh", kp=112.0, ki=40.0, kd=48.0, rows=t, tab=t) for k, t in TABLES.items()}
DES = {k: d for k, d in DES_OP.items() if k != "D3a-flat"}     # theta = 0 part: D3a-flat was run first (+2.8 deg, 0 fails)


def bar(mem, e):
    return 45.0 if (mem in SINGLE and e <= 0) else 30.0


def work(args):
    mem, v = args
    pl = M.member(mem, v)
    chans = {jb: M.plant_channels(pl, F, jb) for jb in (1.0, 1 / S_C)}
    V295 = M.designs()["V295"]
    out = []
    for dn, des in DES.items():
        worst, gmin, pkmax, l20 = (1e9, ""), 1e9, -1e9, 0.0
        for e in ES:
            CthV, CwV, _ = M.controller(V295, v, F, e, 1.0)
            for noI in (False, True):
                for fn, kap, jb in FRAMES:
                    Pt, Pw = chans[jb]
                    Cth, Cw, Cref = M.controller(des, v, F, e, kap, noI=noI)
                    K = M.Kout(F)
                    L = -K * (Cth * Pt + Cw * Pw)
                    PM, FC, GMu = M.pm_gm(L, F)
                    Sx = 1 / (1 + L)
                    pk = 20 * math.log10(max(np.abs(L * Sx)[B530].max(), np.abs(K * Cref * Pt * Sx)[B530].max()))
                    mg = PM - bar(mem, e)
                    if mg < worst[0]:
                        worst = (mg, f"{fn} e{e} {'PD' if noI else 'PID'} PM {PM:.1f} @{FC:.2f} Hz")
                    gmin, pkmax = min(gmin, GMu), max(pkmax, pk)
                    if not noI:
                        l20 = max(l20, abs(L[I20]) / abs((-M.Kout(F) * kap * CwV * Pw)[I20]))
        out.append(dict(d=dn, mem=mem, v=v, margin=worst[0], where=worst[1], gm=gmin, pk=pkmax, l20=l20))
    return out


def theta_op(v, a):
    return 16.0 * 2.83 * a / (v * v) * 180 / math.pi


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


def work_op(args):
    mem, v = args
    out = []
    for a in (1.0, 1.5, 2.0, 2.5):
        pl = M.member(mem, v)
        pl.k *= 1 - math.tanh(theta_op(v, a) / sat(v)) ** 2
        ch = {jb: M.plant_channels(pl, F, jb) for jb in (1.0, 1 / S_C)}
        for fn, kap, jb in FRAMES:
            Pt, Pw = ch[jb]
            for dn, des in DES_OP.items():
                for e in (-1, 0, 10):
                    Cth, Cw, _ = M.controller(des, v, F, e, kap)
                    L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                    PM, FC, GM = M.pm_gm(L, F)
                    out.append(dict(d=dn, mem=mem, v=v, a=a, fn=fn, e=e, PM=PM, GM=GM, bar=bar(mem, e)))
    return out


def main():
    t0 = time.time()
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, [(m, v) for m in GATED for v in GRID], chunksize=4) for r in rr]
        SP = (3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0)
        RO = [r for rr in pool.imap_unordered(work_op, [(m, v) for m in GATED for v in SP], chunksize=2) for r in rr]
    L = [f"D3 GATE 2 on the EXACT D3a table vs V298, c3r1_model unchanged; grid {GRID[0]}..{GRID[-1]} m/s "
         f"({len(GRID)} speeds), {len(GATED)} members x 5 frames x e {ES} x (PID, PD)",
         f"D3a rows: {TABLES['D3a']}"]
    J = {}
    for dn in DES:
        X = [r for r in R if r["d"] == dn]
        fails = [r for r in X if r["margin"] < 0 or r["gm"] < 6 or r["pk"] > 3]
        w = min(X, key=lambda r: r["margin"])
        gm = min(X, key=lambda r: r["gm"])
        pk = max(X, key=lambda r: r["pk"])
        l20 = max(r["l20"] for r in X)
        L.append(f"\n{dn}: GATE-2 fails {len(fails)} / {len(X)} (member x speed points)")
        L.append(f"   worst PM margin {w['margin']:+.1f} deg at {w['mem']} @{w['v']} m/s {w['where']}")
        L.append(f"   min GM_up {gm['gm']:.1f} dB at {gm['mem']} @{gm['v']};  max 5-30 Hz peak {pk['pk']:+.1f} dB at "
                 f"{pk['mem']} @{pk['v']};  max |L20|/V295 {l20:.3f}")
        J[dn] = dict(fails=len(fails), worst=w, gm=gm["gm"], pk=pk["pk"], l20=l20)
        # per-speed worst margin (compact)
        row = []
        for v in (1.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5):
            Y = [r for r in X if abs(r["v"] - v) < 1e-6]
            if Y:
                y = min(Y, key=lambda r: r["margin"])
                row.append(f"{v}:{y['margin']:+.1f}")
        L.append("   worst margin by speed: " + " ".join(row))
    L.append("\n== operating-point GATE 2 (k sech^2(theta_op/sat), a 1.0-2.5 m/s^2), 3.1-10.0 m/s ==")
    for dn, lo, hi in [(d, lo, hi) for d in DES_OP for lo, hi in ((3.0, 7.9), (7.9, 10.1))]:
        X = [r for r in RO if r["d"] == dn and lo <= r["v"] < hi]
        nf = [r for r in X if r["PM"] < r["bar"]]
        nf_msf = [r for r in nf if "ms_free" in r["mem"]]
        w = min(X, key=lambda r: r["PM"] - r["bar"])
        wn = min([r for r in X if "ms_free" not in r["mem"]], key=lambda r: r["PM"] - r["bar"])
        L.append(f"  {dn} [{lo:.0f}-{hi:.0f} m/s]: PM<bar {len(nf)} of {len(X)} ({len(nf_msf)} in the ms_free family); worst {w['PM']:.1f} "
                 f"(bar {w['bar']:.0f}) {w['mem']}@{w['v']} a{w['a']} {w['fn']} e{w['e']}; worst non-ms_free "
                 f"{wn['PM']:.1f} (bar {wn['bar']:.0f}) {wn['mem']}@{wn['v']} a{wn['a']}; min PM overall "
                 f"{min(r['PM'] for r in X):.1f}")
        J[f"{dn}_op_{lo:.0f}"] = dict(n_fail=len(nf), n_fail_msf=len(nf_msf), worst=w, worst_non_msf=wn)
    L.append(f"\nwall time {time.time() - t0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (D.OUT / "gate2_final.txt").write_text(txt, encoding="utf-8")
    (D.OUT / "gate2_final.json").write_text(json.dumps(J, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
