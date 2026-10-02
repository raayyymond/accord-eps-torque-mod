# -*- coding: utf-8 -*-
r"""s5_gate2.py -- D5-architect.  GATE 2 (magnitude AND phase) for V299 (a) and (b) on the panel-2 COMMON frequency
scorer's own pipeline (panel2/score_freq.py: ctl_split, member_plant, K_out, pm_gm, the frame box, the member set),
imported unchanged; a reduced speed grid so it runs in seconds.
  CONTROL  V298 (= C3B-P: GB-P table, Kp 112, Ki 40, fresh D Kd 48) must reproduce SCORE-FREQ's C3B-P row
           (PM nom 79.9, GM nom 23.0, B box min PM 38.5 at b_lo*ms_free+h10 @ 11.9).
  (b)      the firmware's LINEAR loop is byte-identical to V298 (only the freeze thresholds move) -> L(b) == L(V298);
           the fork LEAD multiplies the REFERENCE path only: Cref' = Cref (1 + tau_L(v) Bx(f) LP(f)), Bx = the 5-frame
           boxcar slope, LP = 30 ms pole.  Reported: |T_ref| peak 0.05-3 Hz, -3 dB bandwidth, lag at 0.2 / 0.5 Hz, the
           20 Hz reference gain (staircase leakage), and the fork outer loop (tau_o 1 s, 60 ms) margins.
  (a)      washout D: D_w x HPF, HPF = 1 - a / (1 - (1 - a) z^-1), a = 2^-9; friction comp = extra P (Kf 112) at small
           signal -> loop at kp 224 (small-signal, |E' Kf >> 8| < Lf) AND at kp 112 (saturated).  Full gate box.
Gate (panel-2 R2 box): PM >= 45 (tier A) / 30 (tier B), GM up >= 6 dB, max(|T|) 5-30 Hz <= +3 dB.  Wall printed.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
for _q in (AL / "c3" / "rev2B", AL / "panel2"):
    sys.path.insert(0, str(_q))
_sp = importlib.util.spec_from_file_location("p2_sf_d5", AL / "panel2" / "score_freq.py")
SF = importlib.util.module_from_spec(_sp)
sys.modules["p2_sf_d5"] = SF
_sp.loader.exec_module(SF)
import rb_table as RT  # noqa: E402

OUT = KIT / "_scratch" / "out" / "v299_D5"
F = SF.F
z = SF._z(F)
SPD = [3.1, 5.0, 8.0, 9.0, 10.0, 11.0, 11.9, 13.0, 15.75, 17.0, 20.0, 26.9]
GBP = [list(r) for r in RT.GB_P]
V298 = SF.Spec("V298", "D5", GBP, 48, ki=40.0, dkind="fresh")
A_L = SF.Spec("V299a-sat", "D5", GBP, 48, kp=112.0, ki=40.0, dkind="fresh")
alpha = 2.0 ** -9
HPF = 1.0 - alpha / (1.0 - (1.0 - alpha) * z)
EBP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
GKN = np.array([1178.0, 1465.0, 760.0, 560.0, 1068.0, 2188.0])
TAU_L = 0.5 * 89.5 / GKN
zf = np.exp(-2j * np.pi * F * 0.01)
BX = (1 - zf ** 5) / 0.05                                       # 5-frame boxcar slope (per s)
aL = math.exp(-0.01 / 0.03)
LP = (1 - aL) / (1 - aL * zf)
B530, I20 = SF.B530, SF.I20


def loop(sp, member, v, vi, wash=False):
    nm, kap, jb = SF.VARIANTS[vi]
    pl, d, ea, jbk = SF.member_plant(member, v, jb)
    Pt, Pw = SF.DM.plant_frf(pl, F)
    G = float(SF.C.cave_G(SF.C.spd_counts(v), sp.rows))
    cs = SF.ctl_split(F, sp, G, ea)
    (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
    if wash:
        mw = mw * HPF                                              # the D part lives in the motor frame (fresh abe)
    K = SF.K_out(F, d)
    Cth, Cw, Cref = tth + kap * mth, tw + kap * mw, tref + kap * mref
    L = -K * (Cth * Pt + Cw * Pw)
    return L, K * Cref * Pt, Pt


def gate(sp, wash=False, members=SF.MEMBERS, vis=SF.GATE_FULL):
    fails, worst, gmin, t530max, rows = 0, (999, None), 999, -99, []
    for m in members:
        tierA = SF.tier_of(m, "R2")
        if tierA is None:
            continue
        bar = SF.BAR[tierA]
        for v in SPD:
            for vi in vis:
                L, _, _ = loop(sp, m, v, vi, wash)
                PM, FC, PMR, gmu, gmd = SF.pm_gm(L)
                S = 1 / (1 + L)
                t530 = 20 * math.log10(max(np.abs(L[B530] * S[B530]).max(), 1e-12))
                bad = (PM < bar) or (gmu < 6.0) or (t530 > 3.0)
                fails += bad
                if PM - bar < worst[0]:
                    worst = (PM - bar, "%s@%.2f %s PM %.1f (bar %d) fc %.2f" % (m, v, SF.VARIANTS[vi][0], PM, bar, FC))
                gmin = min(gmin, gmu)
                t530max = max(t530max, t530)
    return dict(fails=fails, worst_margin_over_bar=worst[0], worst=worst[1], gm_min=gmin, t530_max=t530max)


def nominal_table(sp, wash=False, lead=False):
    rows = []
    for v in SPD:
        L, Tn, Pt = loop(sp, "nominal", v, 0, wash)
        PM, FC, PMR, gmu, gmd = SF.pm_gm(L)
        S = 1 / (1 + L)
        Ms = float(np.abs(S).max())
        Cl = 1.0
        if lead:
            Cl = 1 + float(np.interp(v, EBP, TAU_L)) * BX * LP
        Tr = Tn * S * Cl
        band = (F >= 0.05) & (F <= 3.0)
        pk = float(np.abs(Tr[band]).max())
        bw = float(F[np.argmax(np.abs(Tr) < 1 / math.sqrt(2))]) if (np.abs(Tr) < 1 / math.sqrt(2)).any() else float("nan")

        def lag(f0):
            i = int(np.argmin(abs(F - f0)))
            return float(-np.angle(Tr[i]) / (2 * np.pi * F[i]) * 1000)
        i20 = int(np.argmin(abs(F - 20.0)))
        # the fork's outer path-level loop (score_freq.outer_margin's model): integral tau_o 1 s, 60 ms, around T_ref
        Lo = (0.01 / 1.0) / (1 - zf) * np.exp(-2j * np.pi * F * 0.06) * Tr
        PMo, FCo, _, GMo, _ = SF.pm_gm(Lo)
        rows.append(dict(v=v, PM=PM, fc=FC, GM=gmu, Ms=Ms, Tpk=pk, bw=bw, lag02=lag(0.2), lag05=lag(0.5),
                         T20=float(abs(Tr[i20])), PMo=PMo, GMo=GMo))
    return rows


R = {}
lines = []


def pr(s=""):
    print(s)
    lines.append(s)


def main(kf=None):
    kf = KF_A if kf is None else kf
    A_S = SF.Spec("V299a-small", "D5", GBP, 48, kp=112.0 + kf, ki=40.0, dkind="fresh")
    pr("s5 -- GATE 2 on the panel-2 common frequency scorer (reduced speed grid %s); (a) Kf = %d" % (SPD, kf))
    for nm, sp, wash in (("V298 (control) == V299b feedback", V298, False),
                         ("V299a small-signal (kp 112+Kf + washout)", A_S, True),
                         ("V299a saturated friction (kp 112 + washout)", A_L, True)):
        g = gate(sp, wash)
        R[nm] = g
        pr("  %-46s R2-box fails %d | worst PM-bar %+.1f (%s) | min GM up %.1f dB | max T 5-30 Hz %+.1f dB" % (
            nm, g["fails"], g["worst_margin_over_bar"], g["worst"], g["gm_min"], g["t530_max"]))
    pr("\n  nominal member, kappa 1 (PID loop; T_ref = reference -> wheel; outer = fork tau_o 1 s / 60 ms around T_ref):")
    pr("  %-9s %5s %6s %5s %5s %5s | %6s %6s %7s %7s %7s %6s %6s" % ("cand", "v", "PM", "fc", "GM", "Ms", "|T|pk",
                                                                   "bw Hz", "lag.2", "lag.5", "T@20Hz", "PMo", "GMo"))
    for nm, sp, wash, lead in (("V298", V298, False, False), ("V299b", V298, False, True), ("V299a", A_S, True, False)):
        rows = nominal_table(sp, wash, lead)
        R[nm + "_nominal"] = rows
        for r in rows:
            pr("  %-9s %5.2f %6.1f %5.2f %5.1f %5.2f | %6.3f %6.2f %7.0f %7.0f %7.4f %6.1f %6.1f" % (
                nm, r["v"], r["PM"], r["fc"], r["GM"], r["Ms"], r["Tpk"], r["bw"], r["lag02"], r["lag05"], r["T20"],
                r["PMo"], r["GMo"]))
    R["wall_s"] = time.time() - T0
    pr("\nwall %.1f s" % R["wall_s"])
    (OUT / "s5_gate2.json").write_text(json.dumps(R, indent=1, default=float), encoding="utf-8")
    (OUT / "s5_gate2.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


KF_A = 28           # (a)'s friction-comp small-signal gain, sized by s5b_kf_sweep.py (the largest Kf with 0 R2-box fails)

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
