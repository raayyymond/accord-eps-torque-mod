# -*- coding: utf-8 -*-
r"""s1_crosscheck.py -- second-method checks of S1's decision-bearing findings.  Analysis only.  ~5 s.
(a) GB-S13's R2-box failure on the panel-2 COMMON engine (panel2/score_freq.py: ctl_split, member_plant, K_out, pm_gm,
    imported unchanged) -- an independent pipeline from c3r1_model -- at the binding points, V298 alongside.
(b) the fork O1 loop: my combined-loop form 1 + L_tot equals (1 + L)(1 - T_in W) (D2's outer positive-feedback form)
    to machine precision, and D2's own metric (peak |T_in W| over f >= 0.05 Hz) at the binding point."""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402

AL = S.AL
sys.path.insert(0, str(AL / "c3" / "rev2B"))
_sp = importlib.util.spec_from_file_location("p2_sf_s1", AL / "panel2" / "score_freq.py")
SF = importlib.util.module_from_spec(_sp)
sys.modules["p2_sf_s1"] = SF
_sp.loader.exec_module(SF)
F = SF.F
out = []
pr = out.append
pr("(a) panel-2 engine, PID, PM (deg): V298 vs GB-S13 at the c3r1 binding points")
for mem, v, vname in (("b_lo*ms_free+h10", 11.0, "FA.83"), ("b_lo*ms_free+h10", 11.75, "FA.83"),
                      ("b_q*ms_free+h10", 15.0, "FB.83"), ("b_lo*ms_free+h10", 10.0, "FA.83"), ("b_lo*J_hi+h10", 11.0, "FA.83"),
                      ("nominal", 11.0, "nom")):
    vi = SF.VNAMES.index(vname)
    nm, kap, jb = SF.VARIANTS[vi]
    res = []
    for rows in (S.GBP, S.T_GBS13):
        sp = SF.Spec("x", "S1", [list(r) for r in rows], 48, ki=40.0, dkind="fresh")
        pl, d, ea, _ = SF.member_plant(mem, v, jb)
        Pt, Pw = SF.DM.plant_frf(pl, F)
        G = float(SF.C.cave_G(SF.C.spd_counts(v), sp.rows))
        cs = SF.ctl_split(F, sp, G, ea)
        (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
        K = SF.K_out(F, d)
        L = -K * ((tth + kap * mth) * Pt + (tw + kap * mw) * Pw)
        PM, FC, PMR, gmu, gmd = SF.pm_gm(L)
        res.append("PM %.1f fc %.2f GMup %.1f" % (PM, FC, gmu))
    pr("  %-18s @%5.2f %-6s V298: %s | GB-S13: %s" % (mem, v, vname, res[0], res[1]))
# (b)
M = S.M
W = S.W
pl = M.member("b_lo*tau6", 8.0)
fn, kap, jb, ps = S.FRAMES[4]
Pt, Pw = M.plant_channels(pl, S.F, jb)
pr("")
pr("(b) O1 loop at b_lo*tau6 @8 m/s FB1.155 e0 (V298 inner loop):")
for noI in (True, False):
    Cth, Cw, Cref = S.ctl_pieces(S.DES[0], S.LOOPS[0], 8.0, 0, noI)
    K = M.Kout(S.F)
    L = -K * (Cth * Pt + kap * Cw * Pw)
    Tin = K * Cref * Pt / (1 + L)
    for tau in (0.06, 0.0):
        for trt in (0.06, 0.09):
            Wf = np.exp(-1j * W * trt) * (1 + tau * 1j * W)
            Lt = -K * (Cth * Pt + kap * Cw * Pw + Cref * Wf * Pt)
            err = np.max(np.abs((1 + Lt) - (1 + L) * (1 - Tin * Wf)) / np.abs(1 + Lt))
            lo = Tin * Wf
            b = S.F >= 0.05
            pk = np.abs(lo[b]).max()
            fpk = S.F[b][np.argmax(np.abs(lo[b]))]
            PM, FC, GM = S.pm_gm_rows(Lt[None, :])
            pr("  %s tau_O1 %.2f Trt %.0f ms: |1+Lt - (1+L)(1-Tin W)|/|1+Lt| max %.1e ; D2 metric peak |Tin W| %.3f @ %.2f Hz ;"
               " S1 PM %.1f GM %.1f dB fc %.2f Hz ; min|1 - Tin W| %.3f" % (
                   "PD " if noI else "PID", tau, trt * 1000, err, pk, fpk, PM[0], GM[0], FC[0],
                   np.abs(1 - lo[b]).min()))
pr("")
pr("crosscheck wall %.1f s" % (time.time() - T0))
(HERE / "out" / "s1_crosscheck.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
