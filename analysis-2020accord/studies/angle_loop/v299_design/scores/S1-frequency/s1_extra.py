# -*- coding: utf-8 -*-
r"""s1_extra.py -- S1-frequency follow-ups on the SAME engine and grid as s1_freq.py (imported).  Analysis only.

(1) EXACT PERIODIC rho (c3r1_model.Periodic, q = 4 sub-steps, the 10-tick monodromy) at every loop's worst points with
    PM < 32 deg in the core and operating-point blocks (the LTI PM formula 180 - |wrap(phase)| cannot tell a crossing at
    -170 from one at -190; rho can).  R79 frames are mapped exactly: P/I x p, D x kappa  ==  gain p, kappa/p on D.
(2) DELAY MARGIN of the fork-coupled loops: the round-trip Trt (20-200 ms) at which the loop loses its phase margin
    (first Trt with PM < 1 deg or max|S| > 50), per loop x fork kind, worst over members/frames/e/speed.
(3) FRICTION AMPLITUDE SCAN (describing function): PM vs the sliding amplitude A (0.05-5 deg) -> the largest A at which
    PM < 1 deg (a predicted stick-slip / hunting limit cycle) and the A at which PM falls below 30 deg.
usage: python s1_extra.py   (wall printed; target < 30 s)
"""
from __future__ import annotations

import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402

M = S.M
F, W = S.F, S.W
C = {k: i for i, k in enumerate(S.COLS)}


# ---------------------------------------------------------------------------------------------------------------------
def rho_job(a):
    li, im, iv, ifr, e, noI, ia = a
    mem, v = S.MEMBERS[im], S.SPEEDS[iv]
    fn, kap, jb, ps = S.FRAMES[ifr]
    pl = M.member(mem, v)
    th = S.theta_op(v, S.A_OP[ia])
    if th:
        pl.k *= 1.0 - math.tanh(th / S.sat(v)) ** 2
    if S.LOOPS[li].wash:
        return a + (float("nan"), float("nan"), float("nan"))      # the washout state is not in Periodic (LTI only)
    P = M.Periodic(S.DES[li], pl, v, e=e, kappa=kap / ps, jb=jb, noI=bool(noI), gain=ps)
    rho, fz, zeta, _ = P.rho_ring()
    return a + (rho, fz, zeta)


def rho_jobs():
    Z = np.load(S.SCR / "s1_rows.npz")
    R = Z["R"]
    jobs = []
    for li in range(len(S.LOOPS)):
        for ia in range(3):
            m = (R[:, C["loop"]] == li) & (R[:, C["aop"]] == ia) & (R[:, C["fric"]] == 0) & (R[:, C["fade"]] == 1.0) & \
                (R[:, C["PM"]] < 32)
            A = R[m]
            A = A[np.argsort(A[:, C["PM"]])]
            seen = set()
            for r in A:
                key = (int(r[C["mem"]]), int(r[C["v"]]))
                if key in seen:
                    continue
                seen.add(key)
                jobs.append((li, int(r[C["mem"]]), int(r[C["v"]]), int(r[C["fr"]]), int(r[C["e"]]), int(r[C["noI"]]), ia))
                if len(seen) >= 4:
                    break
    return jobs


# ---------------------------------------------------------------------------------------------------------------------
TRTS = np.round(np.arange(0.02, 0.2001, 0.01), 3)
TR_MEM = ("nominal", "b_lo", "J_hi", "b_lo*tau6", "ms_free", "b_lo*J_hi", "tau6")
TR_V = (2.0, 3.1, 5.0, 8.0, 11.75, 17.5, 26.9)
TR_COMBOS = (("V298", "O1.06"), ("V298", "O1.00"), ("V298", "clip"), ("V298", "clipD3lead"),
             ("G0-1400", "O1.06"), ("D3a-tab", "O1.06"), ("D3a-tab", "clipD3lead"), ("D3a-tab", "clip"),
             ("GB-S13", "O1.06"), ("D5a-small", "O1.06"), ("D5a-small", "clip"))


def trt_job(a):
    im, iv = a
    mem, v = TR_MEM[im], TR_V[iv]
    pl = M.member(mem, v)
    out = []
    K1 = M.Kout(F, 1.0)
    for ifr in (0, 4):
        fn, kap, jb, ps = S.FRAMES[ifr]
        Pt, Pw = M.plant_channels(pl, F, jb)
        for e in (0, 10):
            for noI in (False, True):
                Ls, meta = [], []
                for ln, kind in TR_COMBOS:
                    li = S.LIDX[ln]
                    Cth, Cw, Cref = S.ctl_pieces(S.DES[li], S.LOOPS[li], v, e, noI)
                    for trt in TRTS:
                        dl = np.exp(-1j * W * trt)
                        if kind == "O1.06":
                            Wf = dl * (1 + 0.06 * 1j * W)
                        elif kind in ("O1.00", "clip"):
                            Wf = dl
                        else:
                            Wf = dl * (1 + 0.5 * S.tauD_D3(v) * 1j * W * S.LP30)
                        Ls.append(-K1 * (Cth * Pt + kap * Cw * Pw + Cref * Wf * Pt))
                        meta.append((ln, kind, trt))
                L = np.array(Ls)
                PM, FC, GM = S.pm_gm_rows(L)
                Ms = np.abs(1 / (1 + L)).max(axis=1)
                for k, mt in enumerate(meta):
                    out.append(mt + (mem, v, fn, e, int(noI), float(PM[k]), float(FC[k]), float(GM[k]), float(Ms[k])))
    return out


# ---------------------------------------------------------------------------------------------------------------------
AMPS = np.array([5.0, 3.0, 2.0, 1.5, 1.0, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12, 0.08, 0.05])
FA_MEM = ("nominal", "b_lo", "J_hi", "b_hi", "b_lo*J_hi", "ms_free")
FA_V = (2.0, 3.1, 5.0, 8.0, 10.0, 11.75, 13.0, 15.0, 17.5, 20.0, 26.9)
FA_LOOPS = ("V298", "G0-1400", "D3a-tab", "GB-S13", "D5a-small", "D5a-sat")


def fa_job(a):
    im, iv = a
    mem, v = FA_MEM[im], FA_V[iv]
    pl = M.member(mem, v)
    K1 = M.Kout(F, 1.0)
    out = []
    for ifr in (0, 5):
        fn, kap, jb, ps = S.FRAMES[ifr]
        Pt0, Pw0 = M.plant_channels(pl, F, jb)
        for noI in (False, True):
            Ls, meta = [], []
            for ln in FA_LOOPS:
                li = S.LIDX[ln]
                Cth, Cw, Cref = S.ctl_pieces(S.DES[li], S.LOOPS[li], v, 0, noI)
                for A in AMPS:
                    Pt, Pw = S._fric(Pt0, Pw0, v, A)
                    Ls.append(-K1 * (ps * Cth * Pt + kap * Cw * Pw))
                    meta.append((ln, float(A)))
            L = np.array(Ls)
            PM, FC, GM = S.pm_gm_rows(L)
            for k, mt in enumerate(meta):
                out.append(mt + (mem, v, fn, int(noI), float(PM[k]), float(FC[k])))
    return out


def main():
    rj = rho_jobs()
    tj = [(im, iv) for im in range(len(TR_MEM)) for iv in range(len(TR_V))]
    fj = [(im, iv) for im in range(len(FA_MEM)) for iv in range(len(FA_V))]
    with Pool(16) as P:
        r1 = P.map_async(rho_job, rj)
        r2 = P.map_async(trt_job, tj)
        r3 = P.map_async(fa_job, fj)
        RHO, TR, FA = r1.get(), [x for y in r2.get() for x in y], [x for y in r3.get() for x in y]
    out = []
    pr = out.append
    pr("## F. Exact periodic rho at each loop's worst LTI points (PM < 32 deg; up to 4 member/speed pairs per block)")
    pr("")
    pr("| loop | block | member @ v | frame | e | state | rho | ring Hz | zeta |")
    pr("|---|---|---|---|---|---|---|---|---|")
    for r in RHO:
        li, im, iv, ifr, e, noI, ia, rho, fz, z = r
        pr("| %s | %s | %s @%.2f | %s | %d | %s | %.4f | %.2f | %.3f |" % (
            S.LOOPS[li].name, ("core", "op1.5", "op2.5")[ia], S.MEMBERS[im], S.SPEEDS[iv], S.FRAMES[ifr][0], e,
            "PD" if noI else "PID", rho, fz, z))
    pr("")
    # delay margin
    pr("## G. Fork-coupled loops: round-trip delay margin (first Trt with PM < 1 deg or max|S| > 50), worst case")
    pr("")
    pr("| loop | kind | state | min Trt_crit ms (at) | min PM at Trt 60 ms (at) | min GM dB at Trt 60 | min PM at Trt 90 | crossing Hz at the 90-ms worst |")
    pr("|---|---|---|---|---|---|---|---|")
    TRS = {}
    for ln, kind in TR_COMBOS:
        for noI in (0, 1):
            rows = [t for t in TR if t[0] == ln and t[1] == kind and t[7] == noI]
            crit = []
            groups = {}
            for t in rows:
                groups.setdefault((t[3], t[4], t[5], t[6]), []).append(t)
            for g, ts in groups.items():
                ts = sorted(ts, key=lambda x: x[2])
                c = next((x[2] for x in ts if x[8] < 1.0 or x[11] > 50), float("inf"))
                crit.append((c, g))
            cmin = min(crit, key=lambda x: x[0])
            r60 = [t for t in rows if abs(t[2] - 0.06) < 1e-9]
            r90 = [t for t in rows if abs(t[2] - 0.09) < 1e-9]
            w60 = min(r60, key=lambda x: x[8])
            g60 = min(x[10] for x in r60)
            w90 = min(r90, key=lambda x: x[8])
            TRS["%s|%s|%s" % (ln, kind, "PD" if noI else "PID")] = dict(trt_crit=cmin[0], at=cmin[1], pm60=w60[8],
                                                                        gm60=g60, pm90=w90[8], fc90=w90[9])
            pr("| %s | %s | %s | %s (%s @%.2f %s e%d) | %.1f (%s @%.2f) | %.1f | %.1f | %.2f |" % (
                ln, kind, "PD" if noI else "PID", ("%.0f" % (cmin[0] * 1000)) if math.isfinite(cmin[0]) else "> 200",
                cmin[1][0], cmin[1][1], cmin[1][2], cmin[1][3], w60[8], w60[3], w60[4], g60, w90[8], w90[9]))
    pr("")
    # friction amplitude
    pr("## H. Friction amplitude scan (describing function, Fc(v) = 156 -> 85 T): limit-cycle amplitude A_lc (PM < 1 deg) "
       "and A30 (PM < 30 deg), worst over members (nominal, b_lo, J_hi, b_hi, b_lo*J_hi, ms_free) and frames nom / R79.55; e 0")
    pr("")
    pr("| v | " + " | ".join("%s A_lc / A30 (PID)" % ln for ln in FA_LOOPS) + " | V298 A_lc / A30 (PD) |")
    pr("|---|" + "---|" * (len(FA_LOOPS) + 1))
    FAS = {}
    for v in FA_V:
        cells = []
        for ln, noI in [(x, 0) for x in FA_LOOPS] + [("V298", 1)]:
            alc, a30 = 0.0, 0.0
            for mem in FA_MEM:
                for fn in ("nom", "R79.55"):
                    ts = sorted([t for t in FA if t[0] == ln and t[2] == mem and t[3] == v and t[4] == fn and t[5] == noI],
                                key=lambda x: -x[1])
                    a1 = next((x[1] for x in ts if x[6] < 1.0), 0.0)
                    b1 = next((x[1] for x in ts if x[6] < 30.0), 0.0)
                    alc, a30 = max(alc, a1), max(a30, b1)
            FAS["%s|%s|%.2f" % (ln, "PD" if noI else "PID", v)] = (alc, a30)
            cells.append("%s / %s" % (("%.2f" % alc) if alc else "-", ("%.2f" % a30) if a30 else "-"))
        pr("| %.2f | %s |" % (v, " | ".join(cells)))
    pr("")
    pr("extra wall %.1f s (rho %d points, Trt rows %d, friction rows %d)" % (time.time() - T0, len(RHO), len(TR), len(FA)))
    (HERE / "out" / "s1_extra.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(rho=[list(map(float, r)) for r in RHO], trt=TRS, fric={k: list(v) for k, v in FAS.items()},
                   wall=time.time() - T0), open(HERE / "out" / "s1_extra.json", "w"), indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
