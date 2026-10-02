# -*- coding: utf-8 -*-
r"""m3_integrator_freeze.py -- M3: the V298 integrator, its hand-torque freezes, and the driver-torque sensor hands-off,
on route 79 (75604b0a432fdc89_00000079--a1f5d2a272), from the CACHE only.

    python analysis-2020accord/studies/angle_loop/v298_flight/m3_integrator_freeze.py

ANALYSIS ONLY.  Reads analysis-2020accord/_scratch/cache/v280/{r79_a1f5d2_al.npz, r79_fork.npz}, the instrument's cached
C3B-P replay (for validation), and the V298 image's cells.  Writes _scratch/out/r79/m3/m3.json (+ the stdout tables).
No rlog read, no per-sample Python loop (m3_lane: vectorised lane + event-driven exact I recursion), target < 30 s.

Sections:  1 signs  2 (a) bar distribution hands-off  3 (b) freeze conditions  4 (c) I-state replay + R2 + shares
           5 (d) the fork's O1 override  6 (e) effective integral strength and the c_I/c_P = 1.24 dissection
Marked: EVIDENCE = measured on the wire / read from the image; BELIEF = modelled or inherited.
"""
from __future__ import annotations

import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T00 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m3_lane as M                                           # noqa: E402

KIT = M.KIT
OUT = KIT / "_scratch" / "out" / "r79" / "m3"
OUT.mkdir(parents=True, exist_ok=True)
RES = {}
TIM = {}
BANDS = (("<5", 0.0, 5.0), ("5-8", 5.0, 8.0), ("8-10", 8.0, 10.0), ("10-12.5", 10.0, 12.5), ("12.5-15", 12.5, 15.0),
         ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))
ABINS = ((0, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, 1e9))      # |alpha| deg/s^2
RBINS = ((0, 5), (5, 15), (15, 40), (40, 80), (80, 1e9))                         # |rate| deg/s


def pr(s=""):
    print(s, flush=True)


def tic(k, t0):
    TIM[k] = round(time.time() - t0, 3)


def runs(mask, minlen=1):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def pct(x, q):
    x = np.asarray(x, float)
    return [round(float(v), 1) for v in np.percentile(x, q)] if len(x) else [None] * len(q)


def r2(y, yh):
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else float("nan")


# =====================================================================================================================
# 0. LOAD
# =====================================================================================================================
t0 = time.time()
C = M.image_cells()
GL = M.glut(C["rows"])
W = M.load_wire()
th, cmd, tq, x, abe, vws = M.wire_inputs(W)
n = len(th)
FK = np.load(M.CACHE / "r79_fork.npz")
tic("load", t0)
t, v = W["t"], W["vego"]
eng = W["eng"]
settled = eng & (W["tse"] >= 1.2)
nopress = ~W["pressed"]
ho_bar = np.abs(W["bar"]) < 500.0                            # the instrument's regression hands-off
gp60 = -W["bar"]                                             # gp-0x4f60 (signed hand word, + = pushes left)
a60 = np.abs(gp60)                                           # gp-0x4f68
err = W["err"]                                               # theta_sp - theta, deg
pr("M3 -- route 79, V298 image %s (%s)" % (C["version"], Path(C["path"]).name[:40]))
pr("engaged %.1f s, settled %.1f s, settled & cs_press==0 %.1f s" % (eng.sum() / 100, settled.sum() / 100,
                                                                       (settled & nopress).sum() / 100))

# motion: alpha by two methods
b8, a8 = signal.butter(2, 8.0 / 50.0)
b5, a5 = signal.butter(2, 5.0 / 50.0)
w_lp = signal.filtfilt(b8, a8, W["w18"])
alpha1 = np.gradient(w_lp) * 100.0                           # method 1: 0x18F rate, 8 Hz, d/dt
ang_lp = signal.filtfilt(b5, a5, W["ang"])
alpha2 = np.gradient(np.gradient(ang_lp)) * 1e4              # method 2: 0x14A angle, 5 Hz, d2/dt2
dang = np.gradient(ang_lp) * 100.0
err_lp = signal.filtfilt(b5, a5, err)
derr_abs = np.gradient(np.abs(err_lp)) * 100.0               # d|e|/dt, deg/s

# =====================================================================================================================
# 1. SIGNS
# =====================================================================================================================
pr("\n1. SIGNS")
D0 = np.load(M.CACHE / "r79_a1f5d2_al.npz")
j = np.clip(np.searchsorted(D0["t18"], D0["tcs"]) - 1, 0, len(D0["t18"]) - 1)
eq_neg = float(np.mean(D0["tq"][j] == -D0["cs_tq"]))
mm = settled
c_w = float(np.corrcoef(W["w18"][mm], dang[mm])[0, 1])
c_al = float(np.corrcoef(alpha1[mm], alpha2[mm])[0, 1])
# hands-off reaction model: gp-0x4f60 = J alpha + b rate + Fc sgn(rate) + k theta + c0   (engaged, settled, no press)
mR = settled & nopress & np.isfinite(alpha1)
X = np.c_[alpha1[mR], w_lp[mR], np.tanh(w_lp[mR] / 2.0), W["ang"][mR], np.ones(mR.sum())]
bR, *_ = np.linalg.lstsq(X, gp60[mR], rcond=None)
R2R = r2(gp60[mR], X @ bR)
hard = mR & (np.abs(alpha1) > 200)
opp_al = float(np.mean(np.sign(gp60[hard]) == -np.sign(alpha1[hard])))
pr("  0x18F raw == -carState torque on %.1f %% of carState rows (1-frame lag)   => gp-0x4f60 = +cs_tq*1.024" % (100 * eq_neg))
pr("  corr(w18, d(0x14A)/dt) settled %.3f ; corr(alpha_rate, alpha_angle) %.3f" % (c_w, c_al))
pr("  hands-off reaction fit gp-0x4f60 = J a + b w + Fc sgn(w) + k th + c0 : J %.3f /(deg/s2)  b %.2f /(deg/s)  Fc %.0f"
   "  k %.1f /deg  c0 %.0f   R2 %.3f (n %d)" % (*bR, R2R, mR.sum()))
pr("  at |alpha| > 200 deg/s2 hands-off: sign(gp-0x4f60) = -sign(alpha) on %.1f %% (n %d)" % (100 * opp_al, hard.sum()))
RES["signs"] = dict(raw18_eq_neg_cs_tq=eq_neg, corr_w18_dang=c_w, corr_alpha_methods=c_al,
                    reaction=dict(J=bR[0], b=bR[1], Fc=bR[2], k=bR[3], c0=bR[4], r2=R2R, n=int(mR.sum())),
                    opp_alpha_frac_hard=opp_al, n_hard=int(hard.sum()))

# =====================================================================================================================
# 2. (a) THE BAR WORD HANDS-OFF -- per speed band and per |alpha| bin
# =====================================================================================================================
pr("\n2. (a) |gp-0x4f60| (= |0x18F raw| x 1.024) while engaged, settled, cs_press == 0   [EVIDENCE, wire]")
pr("  %-9s %6s  %5s %5s %5s %5s %5s  %6s %6s %6s %6s" % ("band", "s", "p50", "p90", "p95", "p99", "max", ">300", ">512",
                                                           ">614", ">1229"))
A = {}
base = settled & nopress


def dist_row(m):
    z = a60[m]
    return dict(s=m.sum() / 100.0, p=pct(z, [50, 90, 95, 99, 100]), f300=float(np.mean(z > 300)),
                f512=float(np.mean(z > 512)), f614=float(np.mean(z > 614.4)), f1229=float(np.mean(z > 1228.8)))


for nm, lo, hi in BANDS + (("all", 0, 99),):
    m = base & (v >= lo) & (v < hi)
    if m.sum() < 100:
        continue
    r = dist_row(m)
    A[nm] = r
    pr("  %-9s %6.1f  %5.0f %5.0f %5.0f %5.0f %5.0f  %5.1f%% %5.1f%% %5.1f%% %5.1f%%" % (
        nm, r["s"], *r["p"], 100 * r["f300"], 100 * r["f512"], 100 * r["f614"], 100 * r["f1229"]))
pr("  by |alpha| (method 1 = 0x18F rate; method 2 = 0x14A angle, p50 shown for the cross-check)")
pr("  %-10s %6s  %5s %5s %5s %5s  %6s %6s %6s   %s" % ("|a| deg/s2", "s", "p50", "p90", "p99", "max", ">300", ">512",
                                                       ">614", "m2: s p50 >512"))
AB = {}
for lo, hi in ABINS:
    m = base & (np.abs(alpha1) >= lo) & (np.abs(alpha1) < hi)
    m2 = base & (np.abs(alpha2) >= lo) & (np.abs(alpha2) < hi)
    if m.sum() < 20:
        continue
    r = dist_row(m)
    r2_ = dist_row(m2) if m2.sum() >= 20 else None
    AB["%g-%g" % (lo, hi)] = dict(m1=r, m2=r2_)
    pr("  %-10s %6.1f  %5.0f %5.0f %5.0f %5.0f  %5.1f%% %5.1f%% %5.1f%%   %s" % (
        "%g-%g" % (lo, hi if hi < 1e8 else 999), r["s"], r["p"][0], r["p"][1], r["p"][3], r["p"][4], 100 * r["f300"],
        100 * r["f512"], 100 * r["f614"],
        ("%.1f %4.0f %4.1f%%" % (r2_["s"], r2_["p"][0], 100 * r2_["f512"])) if r2_ else "-"))
RES["a"] = dict(by_band=A, by_alpha=AB)

# =====================================================================================================================
# THE LANE -- replays (V298 runs the direction-2 ramp: 0xC63FC 328 / 0xC63FA 66; the instrument replays 33 / 16)
# =====================================================================================================================
BANDS_R = BANDS[1:]
TT, Ttap = W["T_t"], W["T"]


def score(T100, extra=None):
    out = {}
    for L_ in range(-2, 9):
        jj = np.clip(np.searchsorted(t, TT - L_ * 0.01, side="right") - 1, 0, n - 1)
        mb = (eng & ho_bar & (W["tse"] >= 1.2))[jj] & np.isfinite(Ttap)
        if extra is not None:
            mb &= extra[jj]
        row = {}
        for nm, lo, hi in BANDS_R + (("pooled", 0, 99),):
            m = mb & (v[jj] >= lo) & (v[jj] < hi)
            if m.sum() < 100:
                continue
            y, yh = Ttap[m] / 8.0, T100[jj[m]] / 8.0
            row[nm] = dict(r2=r2(y, yh), gain=float(np.dot(yh, y) / max(np.dot(yh, yh), 1e-9)), n=int(m.sum()))
        out[L_] = row
    best = max(out, key=lambda k: out[k].get("pooled", {}).get("r2", -9))
    return best, out[best]


t0 = time.time()
r0_0, R_0 = M.ramp_ticks(eng, C["ramp_in0"], C["ramp_out0"])
r0_2, R_2 = M.ramp_ticks(eng, C["ramp_in2"], C["ramp_out2"])
L0 = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R_0, r0_0, GL)
L2 = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R_2, r0_2, GL)
L2f = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R_2, r0_2, GL, sgn_flip=True)
VAR = {}
VAR["dir0 design"] = (L0, L0["c1"] | L0["c2"] | L0["c4"], True)
VAR["V298 design"] = (L2, L2["c1"] | L2["c2"] | L2["c4"], True)
VAR["no opposing"] = (L2, L2["c1"] | L2["c4"], True)
VAR["no hand frz"] = (L2, L2["c4"], True)
VAR["no A3 bound"] = (L2, L2["c1"] | L2["c2"] | L2["c4"], False)
VAR["no freeze"] = (L2, L2["c4"], False)
VAR["opp flipped"] = (L2f, L2f["c1"] | L2f["c2"] | L2f["c4"], True)
REP = {}
for k, (L, fr, a3) in VAR.items():
    Ia, a3s, clp, nev = M.i_recursion(L, fr, a3=a3, icl_s=C["icl"])
    REP[k] = dict(L=L, fr=fr, Ia=Ia, a3s=a3s, clp=clp, nev=nev, T=M.output_T(C, L2 if L is L2f else L, Ia, n))
REP["I = 0"] = dict(L=L2, fr=None, Ia=np.zeros(L2["m"] * 10, np.int64), a3s=None, clp=None, nev=0,
                    T=M.output_T(C, L2, np.zeros(L2["m"] * 10, np.int64), n))
# torque-word TIMING scan: the same V298 replay with the 0x18F word shifted by s ticks (s > 0: the firmware's word
# LEADS the 0x18F sample).  The instrument's convention is s = 0.  Zero free parameters inside the lane; s is the one
# timing assumption, chosen by pooled R2 and reported with every neighbour.
SHIFT = {}
for sft in (-20, -10, -5, 5, 10, 15, 20):
    Ls = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R_2, r0_2, GL, q_shift=sft)
    Ias, a3x, clx, nvx = M.i_recursion(Ls, Ls["c1"] | Ls["c2"] | Ls["c4"], a3=True, icl_s=C["icl"])
    SHIFT[sft] = dict(L=Ls, Ia=Ias, a3s=a3x, clp=clx, nev=nvx, T=M.output_T(C, Ls, Ias, n))
SHIFT[0] = dict(L=L2, Ia=REP["V298 design"]["Ia"], a3s=REP["V298 design"]["a3s"], clp=REP["V298 design"]["clp"],
                nev=REP["V298 design"]["nev"], T=REP["V298 design"]["T"])
SCAN = {s_: score(SHIFT[s_]["T"])[1]["pooled"]["r2"] for s_ in sorted(SHIFT)}
QS = max(SCAN, key=SCAN.get)
pr("\nTORQUE-WORD TIMING scan (pooled R2 of the V298 replay vs the tap; ticks, + = the firmware word leads 0x18F): "
   + "  ".join("%+d: %.3f" % (k, v_) for k, v_ in SCAN.items()) + "   -> best %+d ticks" % QS)
RES["timing_scan"] = dict(r2=SCAN, best=QS)
# the PRIMARY replay = V298 design at the best timing; the hand-rule variants are re-run at that timing
LQ = SHIFT[QS]["L"]
LQf = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R_2, r0_2, GL, sgn_flip=True, q_shift=QS)
REP["V298 @best timing"] = dict(L=LQ, fr=LQ["c1"] | LQ["c2"] | LQ["c4"], Ia=SHIFT[QS]["Ia"], a3s=SHIFT[QS]["a3s"],
                                clp=SHIFT[QS]["clp"], nev=SHIFT[QS]["nev"], T=SHIFT[QS]["T"])
for k, (L, fr, a3) in {"@best no opposing": (LQ, LQ["c1"] | LQ["c4"], True),
                       "@best no hand frz": (LQ, LQ["c4"], True),
                       "@best no A3 bound": (LQ, LQ["c1"] | LQ["c2"] | LQ["c4"], False),
                       "@best opp flipped": (LQf, LQf["c1"] | LQf["c2"] | LQf["c4"], True)}.items():
    Ia, a3s, clp, nev = M.i_recursion(L, fr, a3=a3, icl_s=C["icl"])
    REP[k] = dict(L=L, fr=fr, Ia=Ia, a3s=a3s, clp=clp, nev=nev, T=M.output_T(C, LQ, Ia, n))
# from here on "V298 design" / L2 = the PRIMARY (V298 arithmetic, dir-2 ramp, best torque timing); the instrument-timing
# replay is kept as "V298 instr. timing"
L2_instr = L2
REP["V298 instr. timing"] = REP["V298 design"]
REP["V298 design"] = REP["V298 @best timing"]
L2, L2f = LQ, LQf
tic("replays", t0)
# validation against the instrument's cached exact replay (dir-0, C3B-P)
cand = glob.glob(str(KIT / "_scratch" / "angle_loop" / "drive-read" / "replay" / "*_cand_C3B-P.npz"))
Z = np.load(cand[0])
I4 = M.slot4(L0, np.where(L0["run"], REP["dir0 design"]["Ia"] >> 7, 0), n)
dI = int(np.sum(I4 != Z["I"]))
dT = REP["dir0 design"]["T"] - Z["T"]
pr("\nVALIDATION: dir-0 I at slot 4 vs the instrument's cached exact replay: %d differing words of %d nonzero; "
   "T (float lag) vs cached integer T on engaged frames: max |d| %.2f T, mean %.3f T; events %d"
   % (dI, int(np.sum(Z["I"] != 0)), np.max(np.abs(dT[eng])), dT[eng].mean(), REP["dir0 design"]["nev"]))
RES["validation"] = dict(I_diff_words=dI, I_nonzero=int(np.sum(Z["I"] != 0)), T_maxdiff=float(np.max(np.abs(dT[eng]))),
                         T_meandiff=float(dT[eng].mean()), cache=Path(cand[0]).name)

# =====================================================================================================================
# 3. (b) THE FREEZE CONDITIONS (V298 design replay, dir-2 ramp) -- per tick, reported per frame
# =====================================================================================================================
pr("\n3. (b) FREEZE (V298 cave: hard |gp-0x4f68| > 512 ; opposing |gp-0x4f60| > 300 & sign != sign(E') ; A3 bound ;"
   " ramp < 0x8000)  [rule = EVIDENCE (image/design); the torque word at 1 kHz is the 100 Hz wire held: BELIEF]")
Ld = REP["V298 design"]
fz = {}
for nm, msk in (("hard", L2["c1"]), ("opposing", L2["c2"]), ("ramp", L2["c4"]), ("A3 stop", Ld["a3s"]),
                ("ICL", Ld["clp"])):
    fz[nm] = M.per_frame_frac(L2, msk & L2["run"], n)
anyhand = M.per_frame_frac(L2, (L2["c1"] | L2["c2"]) & L2["run"], n)
nostep = M.per_frame_frac(L2, (L2["c1"] | L2["c2"] | L2["c4"] | Ld["a3s"]) & L2["run"] & (L2["inc"] != 0), n)
incnz = M.per_frame_frac(L2, L2["run"] & (L2["inc"] != 0), n)
pr("  %-9s %6s  %6s %6s %6s %6s %6s | %8s %8s  %s" % ("band", "s", "hard", "opp", "A3", "ICL", "ramp", "x300/min",
                                                      "x512/min", "frozen-ep: n/min p50 p90 max s"))
FB = {}
for nm, lo, hi in BANDS + (("all", 0, 99),):
    for hon, mbase in (("ho", settled & nopress), ("all", settled)):
        m = mbase & (v >= lo) & (v < hi)
        if m.sum() < 100:
            continue
        mins = m.sum() / 6000.0
        up300 = int(np.sum(m[1:] & m[:-1] & (a60[1:] > 300) & (a60[:-1] <= 300)))
        up512 = int(np.sum(m[1:] & m[:-1] & (a60[1:] > 512) & (a60[:-1] <= 512)))
        ep = [(b - a) / 100.0 for a, b in runs(m & (anyhand >= 0.5))]
        row = dict(s=m.sum() / 100.0, hard=float(fz["hard"][m].mean()), opp=float(fz["opposing"][m].mean()),
                   a3=float(fz["A3 stop"][m].mean()), icl=float(fz["ICL"][m].mean()), ramp=float(fz["ramp"][m].mean()),
                   x300=up300 / mins, x512=up512 / mins, ep_n_min=len(ep) / mins,
                   ep_p=pct(ep, [50, 90, 100]) if ep else [0, 0, 0],
                   step_lost=float(nostep[m].sum() / max(incnz[m].sum(), 1e-9)))
        FB["%s|%s" % (nm, hon)] = row
        if hon == "ho":
            pr("  %-9s %6.1f  %5.1f%% %5.1f%% %5.2f%% %5.2f%% %5.2f%% | %8.1f %8.1f  %5.1f %5.2f %5.2f %5.2f" % (
                nm, row["s"], 100 * row["hard"], 100 * row["opp"], 100 * row["a3"], 100 * row["icl"],
                100 * row["ramp"], row["x300"], row["x512"], row["ep_n_min"], *row["ep_p"]))
pr("  (ho = settled & cs_press == 0; 'x300/min' = upward crossings of |word| through 300 per engaged minute at 100 Hz,"
   " a LOWER bound on the 1 kHz count)")
r_all = FB["all|ho"]
r_alls = FB["all|all"]
pr("  share of TICKS with a non-zero increment that were frozen or stopped: hands-off %.1f %%, all settled %.1f %%"
   % (100 * r_all["step_lost"], 100 * r_alls["step_lost"]))
# coincidence with manoeuvres
pr("  frozen-by-hand fraction by |alpha| (m1) and |rate| bin (settled, cs_press == 0):")
CO = dict(alpha={}, rate={})
for lo, hi in ABINS:
    m = settled & nopress & (np.abs(alpha1) >= lo) & (np.abs(alpha1) < hi)
    if m.sum() >= 20:
        CO["alpha"]["%g-%g" % (lo, hi)] = dict(s=m.sum() / 100, hard=float(fz["hard"][m].mean()),
                                               opp=float(fz["opposing"][m].mean()))
for lo, hi in RBINS:
    m = settled & nopress & (np.abs(w_lp) >= lo) & (np.abs(w_lp) < hi)
    if m.sum() >= 20:
        CO["rate"]["%g-%g" % (lo, hi)] = dict(s=m.sum() / 100, hard=float(fz["hard"][m].mean()),
                                              opp=float(fz["opposing"][m].mean()))
pr("    |alpha| " + "  ".join("%s: %.0fs h%.1f%% o%.1f%%" % (k, r["s"], 100 * r["hard"], 100 * r["opp"])
                             for k, r in CO["alpha"].items()))
pr("    |rate|  " + "  ".join("%s: %.0fs h%.1f%% o%.1f%%" % (k, r["s"], 100 * r["hard"], 100 * r["opp"])
                             for k, r in CO["rate"].items()))
# the opposing freeze vs the motion: accelerating TOWARD the setpoint (sign(alpha) = sign(e)) vs braking
Ep4 = M.slot4(L2, L2["Ep"], n)
mo = settled & nopress & (fz["opposing"] > 0.5)
tow = float(np.mean(np.sign(alpha1[mo]) == np.sign(Ep4[mo]))) if mo.sum() else float("nan")
mov = float(np.mean(np.sign(w_lp[mo]) == np.sign(Ep4[mo]))) if mo.sum() else float("nan")
pr("  opposing-freeze frames (n %d): wheel ACCELERATING toward the setpoint on %.1f %%, MOVING toward it on %.1f %%"
   % (mo.sum(), 100 * tow, 100 * mov))
# growth of |e| while frozen
mf = settled & nopress & (anyhand > 0.5)
mn = settled & nopress & (anyhand == 0)
G_ = dict(frozen=dict(s=mf.sum() / 100, e_p50=pct(np.abs(err[mf]), [50, 90]), grow=float(np.mean(derr_abs[mf] > 0)),
                      derr=float(np.mean(derr_abs[mf])), rate_p50=pct(np.abs(w_lp[mf]), [50, 90]),
                      alpha_p50=pct(np.abs(alpha1[mf]), [50, 90])),
          free=dict(s=mn.sum() / 100, e_p50=pct(np.abs(err[mn]), [50, 90]), grow=float(np.mean(derr_abs[mn] > 0)),
                    derr=float(np.mean(derr_abs[mn])), rate_p50=pct(np.abs(w_lp[mn]), [50, 90]),
                    alpha_p50=pct(np.abs(alpha1[mn]), [50, 90])))
ep_grow = []
for a, b in runs(mf, 5):
    ep_grow.append(abs(err_lp[b - 1]) - abs(err_lp[a]))
ep_grow = np.array(ep_grow)
G_["episodes"] = dict(n=int(len(ep_grow)), grew_gt_0p5=int(np.sum(ep_grow > 0.5)), shrank_gt_0p5=int(np.sum(ep_grow < -0.5)),
                      median=float(np.median(ep_grow)) if len(ep_grow) else None)
pr("  frozen (>=5/10 ticks by a hand rule) vs free, settled & cs_press==0:  |e| p50/p90 %s vs %s deg ; d|e|/dt > 0 on "
   "%.0f %% vs %.0f %% ; mean d|e|/dt %.2f vs %.2f deg/s ; |rate| p50/p90 %s vs %s ; |alpha| p50/p90 %s vs %s"
   % (G_["frozen"]["e_p50"], G_["free"]["e_p50"], 100 * G_["frozen"]["grow"], 100 * G_["free"]["grow"],
      G_["frozen"]["derr"], G_["free"]["derr"], G_["frozen"]["rate_p50"], G_["free"]["rate_p50"],
      G_["frozen"]["alpha_p50"], G_["free"]["alpha_p50"]))
pr("  frozen episodes >= 50 ms: %d ; |e| grew > 0.5 deg across %d, shrank > 0.5 deg across %d (median %+.2f deg)"
   % (G_["episodes"]["n"], G_["episodes"]["grew_gt_0p5"], G_["episodes"]["shrank_gt_0p5"],
      G_["episodes"]["median"] or 0))
RES["b"] = dict(by_band=FB, coincidence=CO, opp_toward_accel=tow, opp_toward_move=mov, growth=G_)

# =====================================================================================================================
# 4. (c) THE I-STATE: R2 per band vs the tap, the variants, shares, bounds
# =====================================================================================================================
pr("\n4. (c) REPLAY vs the 0x1AB tap (R2, lag-searched -2..8 frames, mask = engaged & |bar| < 500 & settled -- the"
   " instrument's _score_replay mask)")
SC = {}
pr("  %-13s lag  %s" % ("replay", "  ".join("%9s" % b[0] for b in BANDS_R) + "    pooled  gain"))
for k in ("dir0 design", "V298 instr. timing", "no opposing", "no hand frz", "no A3 bound", "no freeze", "opp flipped",
          "I = 0", "cached(dir0)", "V298 @best timing", "@best no opposing", "@best no hand frz", "@best no A3 bound",
          "@best opp flipped"):
    T100 = Z["T"].astype(float) if k == "cached(dir0)" else REP[k]["T"]
    lg, row = score(T100)
    SC[k] = dict(lag=lg, rows=row)
    pr("  %-13s %3d  %s    %6.3f  %5.3f" % (k, lg, "  ".join("%9.3f" % row[b[0]]["r2"] if b[0] in row else "      -  "
                                                              for b in BANDS_R), row["pooled"]["r2"],
                                           row["pooled"]["gain"]))
RES["c_r2"] = SC
# components (V298 design) through the output path
Ld = REP["V298 design"]
T_I = M.output_T(C, L2, Ld["Ia"], n, comp="I")
T_P = M.output_T(C, L2, Ld["Ia"], n, comp="P")
T_D = M.output_T(C, L2, Ld["Ia"], n, comp="D")
I_s = M.slot4(L2, np.where(L2["run"], Ld["Ia"] >> 7, 0), n)            # I >> 7 (S units)
bnd4 = M.slot4(L2, L2["bound"], n)
sg4 = np.sign(Ep4)
# holds: settled, cs_press==0, |rate_lp| < 2 deg/s for >= 1 s, |theta| >= 2 deg ; manoeuvres: |rate| >= 20 or |a| >= 100
hold_m = np.zeros(n, bool)
for a, b in runs(settled & nopress & (np.abs(w_lp) < 2.0) & (np.abs(W["ang"]) >= 2.0), 100):
    hold_m[a:b] = True
man_m = settled & nopress & ((np.abs(w_lp) >= 20) | (np.abs(alpha1) >= 100))
SH = {}
for nm, m in (("hold", hold_m), ("manoeuvre", man_m), ("all ho", settled & nopress)):
    tot = np.abs(T_P[m]) + np.abs(T_I[m]) + np.abs(T_D[m])
    Ttot = REP["V298 design"]["T"][m]
    SH[nm] = dict(s=m.sum() / 100, I_share_abs=float(np.mean(np.abs(T_I[m])) / max(np.mean(tot), 1e-9)),
                  I_signed_share=float(np.sum(T_I[m] * np.sign(Ttot)) / max(np.sum(np.abs(Ttot)), 1e-9)),
                  P_signed_share=float(np.sum(T_P[m] * np.sign(Ttot)) / max(np.sum(np.abs(Ttot)), 1e-9)),
                  D_signed_share=float(np.sum(T_D[m] * np.sign(Ttot)) / max(np.sum(np.abs(Ttot)), 1e-9)),
                  I_abs_p50_p90=pct(np.abs(I_s[m]), [50, 90]),
                  e_p50_p90=pct(np.abs(err[m]), [50, 90]),
                  at_icl=float(np.mean(np.abs(I_s[m]) >= 8192 - 64)),
                  at_a3=float(np.mean((I_s[m] * sg4[m]) >= bnd4[m])),
                  tap_vs_model_gain=float(np.dot(REP["V298 design"]["T"][m], W["T"][np.clip(np.searchsorted(
                      TT, t[m]), 0, len(TT) - 1)]) / max(np.dot(Ttot, Ttot), 1e-9)))
    pr("  %-9s %6.1f s : I share |.| %.0f %% ; signed shares of |T|: P %+.2f I %+.2f D %+.2f ; |I>>7| p50/p90 %s ;"
       " at ICL %.2f %% ; at/over the A3 bound %.2f %% ; |e| p50/p90 %s deg" % (nm, SH[nm]["s"], 100 * SH[nm]["I_share_abs"],
                                                          SH[nm]["P_signed_share"], SH[nm]["I_signed_share"],
                                                          SH[nm]["D_signed_share"], SH[nm]["I_abs_p50_p90"],
                                                          100 * SH[nm]["at_icl"], 100 * SH[nm]["at_a3"], SH[nm]["e_p50_p90"]))
RES["c_shares"] = SH
RES["c_events"] = {k: REP[k]["nev"] for k in REP}
# the fork's error clip and the hold error the integrator carried
tcs = FK["t_cs"]
jcc = np.clip(np.searchsorted(FK["t_cc"], tcs, side="right") - 1, 0, len(FK["t_cc"]) - 1)
lat = FK["cc_latActive"][jcc].astype(bool)
cc_ang = FK["cc_ang"][jcc]
co_ang = FK["co_ang"]
cs_ang, cs_rate, cs_tq = FK["cs_ang"], FK["cs_rate"], FK["cs_tq"]
vr = FK["cs_vegoraw"]
emax = np.interp(vr, [3.1, 8.0, 10.0, 11.75, 17.5, 26.9], [17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
jw = np.clip(np.searchsorted(t, tcs) , 0, n - 1)                       # wire frame of each carState row
hold_cs = hold_m[jw] & lat
clip_on = lat & (np.abs(cc_ang - cs_ang) > emax + 0.05)
EC = dict(lat_s=float(lat.sum() / 100), clip_frac_lat=float(clip_on[lat].mean()),
          clip_frac_hold=float(clip_on[hold_cs].mean()) if hold_cs.sum() else None,
          beyond_hold_p50_p90=pct((np.abs(cc_ang - cs_ang) - emax)[hold_cs & clip_on], [50, 90]) if (hold_cs & clip_on).sum() else None)
by = {}
for nm, lo, hi in BANDS:
    m = lat & (vr >= lo) & (vr < hi)
    if m.sum() > 100:
        mh = m & hold_cs
        by[nm] = dict(s=m.sum() / 100, clip=float(clip_on[m].mean()),
                      clip_hold=float(clip_on[mh].mean()) if mh.sum() > 50 else None,
                      i_at_a3_when_clip=float(np.mean((I_s[jw][m & clip_on] * sg4[jw][m & clip_on]) >=
                                                      bnd4[jw][m & clip_on])) if (m & clip_on).sum() > 20 else None,
                      hand_frz_when_clip=float(np.mean(anyhand[jw][m & clip_on] > 0.5)) if (m & clip_on).sum() > 20 else None)
EC["by_band"] = by
pr("  fork error clip |cc_ang - theta| > errmax(v): %.1f %% of latActive frames, %s of hold frames; beyond-clip error in"
   " holds p50/p90 %s deg" % (100 * EC["clip_frac_lat"], ("%.1f %%" % (100 * EC["clip_frac_hold"])) if EC["clip_frac_hold"]
                              is not None else "-", EC["beyond_hold_p50_p90"]))
pr("    by band: " + "  ".join("%s clip %.1f%% (hold %s) I@A3 %s handfrz %s" % (
    k, 100 * r["clip"], ("%.1f%%" % (100 * r["clip_hold"])) if r["clip_hold"] is not None else "-",
    ("%.0f%%" % (100 * r["i_at_a3_when_clip"])) if r["i_at_a3_when_clip"] is not None else "-",
    ("%.0f%%" % (100 * r["hand_frz_when_clip"])) if r["hand_frz_when_clip"] is not None else "-") for k, r in by.items()))
RES["c_errclip"] = EC

# =====================================================================================================================
# 5. (d) THE FORK'S O1 OVERRIDE (|cs_tq| > 600 on, <= 500 off, while latActive) -- reconstructed + validated
# =====================================================================================================================
pr("\n5. (d) O1 (fork carcontroller._update_angle: override = |steeringTorque| > (500 if on else 600); setpoint = "
   "angle + rate x 0.06 s, then the error clip)")
atq = np.abs(cs_tq)
dec = np.where(lat & (atq > 600), 1, np.where(~lat | (atq <= 500), 0, -1))
idx = np.where(dec >= 0, np.arange(len(dec)), 0)
idx = np.maximum.accumulate(idx)
o1 = np.where(dec[idx] == 1, True, False) & lat
o1[(dec == -1) & (np.maximum.accumulate(np.where(dec >= 0, np.arange(len(dec)), -1)) < 0)] = False
pred = np.clip(np.clip(cs_ang + cs_rate * 0.06, cs_ang - emax, cs_ang + emax), -400, 400)
VAL = {}
for lagc in (-1, 0, 1):
    jc = np.clip(np.arange(len(tcs)) + lagc, 0, len(co_ang) - 1)
    VAL[lagc] = (float(np.mean(np.abs(co_ang[jc][o1] - pred[o1]) < 0.02)) if o1.sum() else float("nan"),
                 float(np.mean(np.abs(co_ang[jc][lat & ~o1] - pred[lat & ~o1]) < 0.02)))
lagc = max(VAL, key=lambda k: VAL[k][0])
pr("  validation: co_ang == clip(angle + 0.06 rate) within 0.02 deg on %.1f %% of reconstructed-O1 frames vs %.1f %% of"
   " latActive non-O1 frames (carOutput row offset %+d)" % (100 * VAL[lagc][0], 100 * VAL[lagc][1], lagc))
ep = runs(o1, 1)
EPI = []
alpha_cs = alpha1[jw]
wlp_cs = w_lp[jw]
pred_rx = (bR[0] * alpha1 + bR[1] * w_lp + bR[2] * np.tanh(w_lp / 2.0) + bR[3] * W["ang"] + bR[4])[jw]   # gp units
for a, b in ep:
    a0 = max(a - 3, 0)
    s = slice(a0, a + 3)
    k = a0 + int(np.argmax(np.abs(alpha_cs[s])))
    EPI.append(dict(t=float(tcs[a] - tcs[0]), dur=(b - a) / 100.0, maxtq=float(atq[a:b].max()),
                    pressed=bool(np.any(FK["cs_press"][a:b])), v=float(vr[a]),
                    alpha=float(alpha_cs[k]), rate=float(wlp_cs[a]), tq=float(cs_tq[a]),
                    pred=float(pred_rx[a] / 1.024),
                    react_sign=bool(np.sign(cs_tq[a]) == -np.sign(alpha_cs[k])),
                    with_rate=bool(np.sign(cs_tq[a]) == np.sign(wlp_cs[a]))))
EPI_np = {k: np.array([e[k] for e in EPI]) for k in (EPI[0] if EPI else {})}
if EPI:
    nop = ~EPI_np["pressed"]
    rx = nop & EPI_np["react_sign"] & (np.abs(EPI_np["alpha"]) >= 100)
    rxp = rx & (np.abs(EPI_np["pred"]) >= 0.6 * 600) & (np.sign(EPI_np["pred"]) == np.sign(EPI_np["tq"]))
    O1 = dict(n=len(EPI), total_s=float(EPI_np["dur"].sum()), lat_s=float(lat.sum() / 100),
              per_min=len(EPI) / (lat.sum() / 6000.0), dur_p=pct(EPI_np["dur"], [50, 90, 100]),
              n_not_pressed=int(nop.sum()), s_not_pressed=float(EPI_np["dur"][nop].sum()),
              n_react_sign_hard=int(rx.sum()), n_react_model_ge_360=int(rxp.sum()),
              n_with_rate=int(np.sum(nop & EPI_np["with_rate"])),
              alpha_onset_p=pct(np.abs(EPI_np["alpha"][nop]), [50, 90]),
              rate_onset_p=pct(np.abs(EPI_np["rate"][nop]), [50, 90]), val=VAL, lag=lagc)
    # what the firmware saw during O1: the error and the I
    jo = jw[o1]
    O1["err_during_p50_p90"] = pct(np.abs(err[jo]), [50, 90])
    O1["hand_frz_during"] = float(np.mean(anyhand[jo] > 0.5))
    pr("  O1 episodes %d (%.2f /latActive-min), %.1f s total of %.0f s latActive; duration p50/p90/max %s s" % (
        O1["n"], O1["per_min"], O1["total_s"], O1["lat_s"], O1["dur_p"]))
    pr("  with cs_press == 0 throughout (|tq| < 1200): %d episodes, %.1f s ; of these: tq sign = -sign(alpha) with "
       "|alpha| >= 100 at onset (reaction-shaped): %d ; and the hands-off reaction model alone predicts >= 360 raw "
       "of the same sign: %d ; tq sign = sign(rate) (driver-shaped): %d" % (
           O1["n_not_pressed"], O1["s_not_pressed"], O1["n_react_sign_hard"], O1["n_react_model_ge_360"],
           O1["n_with_rate"]))
    pr("  onset |alpha| p50/p90 %s deg/s2, |rate| p50/p90 %s deg/s (not-pressed episodes) ; during O1 the firmware's"
       " |sp - theta| p50/p90 %s deg and the I is hand-frozen on %.0f %% of frames" % (
           O1["alpha_onset_p"], O1["rate_onset_p"], O1["err_during_p50_p90"], 100 * O1["hand_frz_during"]))
    O1["episodes"] = sorted(EPI, key=lambda e: -abs(e["alpha"]))[:12]
    # consequence for the setpoint (loop over EPISODES, not samples): the fork's own error before onset, the deficit
    # cc_ang - co_ang while O1 holds and until the rate limiter brings co_ang back within 0.5 deg of cc_ang
    dev = np.abs(cc_ang - np.r_[co_ang[1:], co_ang[-1:]])          # carOutput row offset +1 (validated above)
    pre_e, deficit, rec, fw_pre, fw_dur = [], [], [], [], []
    for (a, b), e_ in zip(ep, EPI):
        if e_["pressed"]:
            continue
        pre_e.append(abs(cc_ang[max(a - 1, 0)] - cs_ang[max(a - 1, 0)]))
        fw_pre.append(float(np.max(np.abs(err[jw[max(a - 3, 0)]:jw[max(a - 1, 0)] + 1]))))
        fw_dur.append(float(np.median(np.abs(err[jw[a] + 2:jw[b - 1] + 3]))))
        k = np.flatnonzero(dev[b:b + 300] < 0.5)
        r_ = (k[0] if len(k) else 300)
        rec.append(r_ / 100.0)
        deficit.append(float(np.sum(dev[a:b + r_]) / 100.0))
    O1["np_pre_err_p50_p90"] = pct(pre_e, [50, 90])
    O1["np_recover_s_p50_p90"] = pct(rec, [50, 90])
    O1["np_deficit_degs_p50_p90"] = pct(deficit, [50, 90])
    O1["np_deficit_degs_total"] = float(np.sum(deficit))
    O1["np_fw_err_pre_p50_p90"] = pct(fw_pre, [50, 90])
    O1["np_fw_err_during_p50_p90"] = pct(fw_dur, [50, 90])
    pr("  not-pressed O1: the firmware's |sp - theta| (wire) in the 30 ms before onset p50/p90 %s deg -> during the "
       "episode (+20 ms for the round trip) p50/p90 %s deg" % (O1["np_fw_err_pre_p50_p90"], O1["np_fw_err_during_p50_p90"]))
    pr("  not-pressed O1: the fork's desired-vs-wheel error at onset p50/p90 %s deg ; after release co_ang is back"
       " within 0.5 deg of cc_ang in p50/p90 %s s ; setpoint deficit per episode p50/p90 %s deg.s (total %.1f deg.s)"
       % (O1["np_pre_err_p50_p90"], O1["np_recover_s_p50_p90"], O1["np_deficit_degs_p50_p90"],
          O1["np_deficit_degs_total"]))
else:
    O1 = dict(n=0, val=VAL)
    pr("  no O1 episodes reconstructed")
RES["d"] = O1

# =====================================================================================================================
# 6. (e) THE INTEGRAL'S EFFECTIVE STRENGTH, and the c_I/c_P = 1.24 dissection
# =====================================================================================================================
pr("\n6. (e) INTEGRAL STRENGTH")
cIcP_design = 1000.0 * C["ki"] / (8 * 32 * 128) / (C["kp"] / 256.0)
pr("  design: per tick inc = ((E' >> 5) * Ki) >> 3 ; I -> S = I >> 7 ; P = (E' * Kp) >> 8  => c_I/c_P = 1000 Ki/(8*32*128)"
   " / (Kp/256) = %.3f /s (PI zero %.3f Hz, T_i %.3f s)  [EVIDENCE, image cells]" % (cIcP_design,
                                                                                    cIcP_design / 2 / np.pi,
                                                                                    1 / cIcP_design))
run2, inc2, ie2 = L2["run"], L2["inc"], L2["inc_exact"]
stp = np.diff(np.r_[0, Ld["Ia"]])
stp = np.where(run2 & ~L2["rs"], stp, 0)
EF = {}
for nm, lo, hi in BANDS + (("all", 0, 99),):
    for hon, fm in (("ho", settled & nopress), ("all", settled)):
        mt = np.repeat(fm & (v >= lo) & (v < hi), 1)[L2["F"]]
        mt = np.repeat(mt, 10) & run2
        if mt.sum() < 1000:
            continue
        sabs = np.sum(np.abs(inc2[mt]))
        eff = float(np.sum(stp[mt] * np.sign(inc2[mt])) / max(sabs, 1))
        bias = float(np.sum(inc2[mt] - ie2[mt]) / mt.sum() * 1000.0 / 128.0)          # S units per second
        gmean = float(np.mean(L2["G"][mt]))
        per_deg = 160.0 * gmean / 256.0 * C["ki"] / 256.0 * 1000.0 / 128.0              # S/s per deg of error
        EF["%s|%s" % (nm, hon)] = dict(eff=eff, cIcP_eff=eff * cIcP_design, bias_S_per_s=bias,
                                       bias_deg=bias / per_deg, frac_e5_zero=float(np.mean((L2["Ep"][mt] >> 5) == 0)),
                                       frac_e5_m1=float(np.mean((L2["Ep"][mt] >> 5) == -1)))
pr("  replay (V298 design): integration delivered / integration commanded (|inc|-weighted), and the sar-5 floor bias:")
for k, r in EF.items():
    if k.endswith("|ho"):
        pr("    %-9s eff %.3f -> c_I/c_P %.2f /s ; floor bias %+.1f S/s = %+.4f deg of standing error ; e5==0 %.1f %%,"
           " e5==-1 %.1f %%" % (k[:-3], r["eff"], r["cIcP_eff"], r["bias_S_per_s"], r["bias_deg"],
                                100 * r["frac_e5_zero"], 100 * r["frac_e5_m1"]))
RES["e_eff"] = EF
RES["e_design"] = dict(cIcP=cIcP_design, pi_zero_hz=cIcP_design / 2 / np.pi, Ti=1 / cIcP_design)


# the instrument's structural regression, re-run on this file's components, then varied
def comps(L, Ia, R):
    z_raw = (4.0 * FL_s16(L["cm"]) * L["G"] / 256.0) * C["kp"] / 256.0
    z_meas = (-L["r26"] * L["G"] / 256.0) * C["kp"] / 256.0
    out = {}
    for k_, z in (("Praw", z_raw), ("Pmeas", z_meas)):
        out[k_] = M.output_T(C, dict(L, P=z, D=np.zeros_like(z), run=L["run"]), Ia, n, comp="P") / 8.0
    out["I"] = M.output_T(C, L, Ia, n, comp="I") / 8.0
    out["D"] = M.output_T(C, L, Ia, n, comp="D") / 8.0
    return out


def FL_s16(a):
    return M.FL.s16(a).astype(float)


SOS_BP = signal.butter(2, [0.1, 3.0], "bandpass", fs=50.0, output="sos")


def regress_struct(cp, keys=("Praw", "Pmeas", "I", "D"), extra=None, icpt="one", lags=range(-2, 7), min_run=100,
                   bp=False):
    """icpt: 'one' (the instrument's single c0) | 'episode' | 'win10' (one per engaged episode x 10 s window);
    bp: 0.1-3 Hz band-pass of y and every regressor inside each run (edges trimmed 0.5 s), no intercept."""
    best = None
    for L_ in lags:
        jj = np.clip(np.searchsorted(t, TT - L_ * 0.01, side="right") - 1, 0, n - 1)
        m50 = (eng & ho_bar & (W["tse"] >= 1.2))[jj] & np.isfinite(Ttap) & (np.abs(Ttap) < 0.95 * 2461)
        if extra is not None:
            m50 &= extra[jj]
        Xs, Ys, Es = [], [], []
        for nm, lo, hi in BANDS_R:
            mb = m50 & (v[jj] >= lo) & (v[jj] < hi)
            rr_ = runs(mb, max(min_run, 100) if bp else min_run)
            if not rr_ or sum(b - a for a, b in rr_) < 100:
                continue
            for a, b in rr_:
                idx_ = jj[a:b]
                Xr = np.c_[[cp[k_][idx_] for k_ in keys]].T
                Yr = Ttap[a:b] / 8.0
                if bp:
                    Xr = signal.sosfiltfilt(SOS_BP, Xr, axis=0)[25:-25]
                    Yr = signal.sosfiltfilt(SOS_BP, Yr)[25:-25]
                    idx_ = idx_[25:-25]
                Xs.append(Xr)
                Ys.append(Yr)
                Es.append(W["eid"][idx_] * 1000 + (t[idx_] // 10).astype(int) * (icpt == "win10"))
        if not Ys:
            return None
        X_ = np.vstack(Xs)
        Y_ = np.concatenate(Ys)
        E_ = np.concatenate(Es)
        if bp:
            Xi = X_
        elif icpt in ("episode", "win10"):
            U, inv = np.unique(E_, return_inverse=True)
            Xi = np.c_[X_, np.eye(len(U))[inv]] if len(U) < 400 else np.c_[X_, np.ones(len(Y_))]
            if len(U) >= 400:
                # demean within each group instead (identical OLS slopes, cheaper)
                Xi = X_ - np.array([np.bincount(inv, X_[:, c]) / np.bincount(inv) for c in range(X_.shape[1])]).T[inv]
                Y_ = Y_ - (np.bincount(inv, Y_) / np.bincount(inv))[inv]
        else:
            Xi = np.c_[X_, np.ones(len(Y_))]
        b_, *_ = np.linalg.lstsq(Xi, Y_, rcond=None)
        rr2 = r2(Y_, Xi @ b_)
        if best is None or rr2 > best[0]:
            best = (rr2, L_, b_[:len(keys)], len(Y_))
    rr2, L_, b_, nn = best
    d = dict(zip(keys, [float(z) for z in b_]))
    d.update(r2=rr2, lag=L_, n=nn)
    if "I" in d and "Praw" in d:
        d["cIcP"] = d["I"] / d["Praw"] * cIcP_design
    return d


t0 = time.time()
CP0 = comps(L0, REP["dir0 design"]["Ia"], R_0)
CP2 = comps(L2, REP["V298 design"]["Ia"], R_2)
CPi = comps(L2_instr, REP["V298 instr. timing"]["Ia"], R_2)
CPn = dict(CP2, I=M.output_T(C, L2, REP["no freeze"]["Ia"], n, comp="I") / 8.0)
CPh = dict(CP2, I=M.output_T(C, L2, REP["no hand frz"]["Ia"], n, comp="I") / 8.0)
CPf = dict(CP2, I=M.output_T(C, L2f, REP["opp flipped"]["Ia"], n, comp="I") / 8.0)
RG = {}
RG["instrument form, dir-0 I"] = regress_struct(CP0)
RG["dir-2 I (V298 ramp), instr. timing"] = regress_struct(CPi)
RG["dir-2 I, best torque timing (primary)"] = regress_struct(CP2)
RG["primary I, per-episode intercepts"] = regress_struct(CP2, icpt="episode")
RG["I never frozen"] = regress_struct(CPn)
RG["I no hand freeze (A3 kept)"] = regress_struct(CPh)
RG["I opposing sign flipped"] = regress_struct(CPf)
hold_or_slow = np.abs(w_lp) < 5.0
RG["primary I, per-episode x 10 s intercepts"] = regress_struct(CP2, icpt="win10")
RG["dir-2 instr.-timing I, per-episode x 10 s icpt"] = regress_struct(CPi, icpt="win10")
RG["dir-0 I, per-episode x 10 s intercepts"] = regress_struct(CP0, icpt="win10")
RG["primary I, 0.1-3 Hz band-pass"] = regress_struct(CP2, bp=True)
RG["dir-0 I, 0.1-3 Hz band-pass"] = regress_struct(CP0, bp=True)
RG["primary I, |rate| < 5 deg/s only"] = regress_struct(CP2, extra=hold_or_slow)
RG["primary I, |rate| >= 5 deg/s (runs >= 0.5 s)"] = regress_struct(CP2, extra=~hold_or_slow, min_run=25)
tic("regressions", t0)
pr("  the instrument's structural regression tap = a P_raw + b P_meas + c I + d D + c0 (hands-off |bar|<500, settled, "
   "runs >= 2 s, lag-scanned), re-run here; c_I/c_P = (c/a) x %.2f" % cIcP_design)
pr("  %-46s %6s %6s %6s %6s  %6s  %6s %4s" % ("I regressor / mask", "a", "b", "c", "d", "c_I/c_P", "R2", "lag"))
for k, d in list(RG.items()):
    if d is None:
        RG.pop(k)
        pr("  %-46s (no runs)" % k)
        continue
    pr("  %-46s %6.3f %6.3f %6.3f %6.3f  %6.2f  %6.3f %4d" % (k, d["Praw"], d["Pmeas"], d["I"], d["D"], d["cIcP"],
                                                             d["r2"], d["lag"]))
RES["e_regress"] = RG
# hold test: in holds the D is ~0; the tap minus the modelled P vs the modelled I, window means (no intercept)
hw = runs(hold_m & ho_bar, 100)
Hy, Hp, Hi = [], [], []
Tap100 = np.interp(t, TT, Ttap)
for a, b in hw:
    s = slice(a + 20, b)
    Hy.append(np.mean(Tap100[s]) / 8.0)
    Hp.append(np.mean(CP2["Praw"][s] + CP2["Pmeas"][s]))
    Hi.append(np.mean(CP2["I"][s]))
Hy, Hp, Hi = map(np.array, (Hy, Hp, Hi))
if len(Hy) >= 3:
    bh, *_ = np.linalg.lstsq(np.c_[Hp, Hi], Hy, rcond=None)
    bh1, *_ = np.linalg.lstsq(np.c_[Hp + Hi], Hy, rcond=None)
    HT = dict(n=int(len(Hy)), s=float(sum(b - a - 20 for a, b in hw) / 100), cP=float(bh[0]), cI=float(bh[1]),
              c_PI=float(bh1[0]), r2=r2(Hy, np.c_[Hp, Hi] @ bh),
              I_over_PI_med=float(np.median(np.abs(Hi) / np.maximum(np.abs(Hp) + np.abs(Hi), 1e-9))),
              tap_p50=pct(np.abs(Hy), [50, 90]), P_p50=pct(np.abs(Hp), [50, 90]), I_p50=pct(np.abs(Hi), [50, 90]))
    pr("  HOLD TEST (%d holds, %.0f s; window means, no intercept): tap = %.2f P + %.2f I (R2 %.3f) ; single gain on P+I"
       " %.2f ; I / (|P|+|I|) median %.2f ; |tap| p50/p90 %s LSB, |P| %s, |I| %s"
       % (HT["n"], HT["s"], HT["cP"], HT["cI"], HT["r2"], HT["c_PI"], HT["I_over_PI_med"], HT["tap_p50"],
          HT["P_p50"], HT["I_p50"]))
else:
    HT = dict(n=int(len(Hy)))
RES["e_hold"] = HT
# EVENT TEST (second method for 'did the car integrate what the replay integrated?'): across each hands-off manoeuvre,
# the change of the slow offset (tap - replay) between a quiet window before and a quiet window after, regressed on
#   taken = the integration the V298 replay TOOK during the event, lost = the integration its hand rules FROZE.
# Real freeze == modelled -> both coefficients ~0 ; car froze MORE -> coef(taken) < 0 ; car froze LESS -> coef(lost) > 0.
fA0 = 254.0 / 256.0
kS = fA0 * 0.990 * C["fwd"] / 32768.0 / 8.0                  # tap LSB per S unit (DC, at rest; image cells)
off_S = -(Tap100 - REP["V298 design"]["T"]) / 8.0          # S-sign offset, car - replay, tap LSB
stp_d = np.where(L2["run"] & ~L2["rs"], np.diff(np.r_[0, Ld["Ia"]]), 0)
lost_h = np.where(L2["run"] & (L2["c1"] | L2["c2"]), L2["inc"], 0)
cs_taken = np.r_[0, np.cumsum(stp_d)]
cs_lost = np.r_[0, np.cumsum(lost_h)]
tick_of = np.full(n, -1)
tick_of[L2["F"]] = np.arange(L2["m"]) * 10
quiet = settled & nopress & (np.abs(w_lp) < 8.0)
ev = []
man_ev = signal.filtfilt(np.ones(1), np.ones(1), man_m.astype(float)) > 0      # (identity; kept explicit)
for a, b in runs(man_ev, 10):
    pa, pb = a - 80, a - 10
    qa, qb = b + 30, b + 130
    if pa < 0 or qb >= n or W["eid"][pa] != W["eid"][qb] or W["eid"][pa] == 0:
        continue
    if quiet[pa:pb].mean() < 0.6 or quiet[qa:qb].mean() < 0.6 or tick_of[pb] < 0 or tick_of[qa] < 0:
        continue
    d_off = float(np.median(off_S[qa:qb]) - np.median(off_S[pa:pb]))
    taken = (cs_taken[tick_of[qa]] - cs_taken[tick_of[pb]]) / 128.0 * kS
    lost = (cs_lost[tick_of[qa]] - cs_lost[tick_of[pb]]) / 128.0 * kS
    ev.append((d_off, taken, lost, float(v[a])))
EVT = dict(n=len(ev))
if len(ev) >= 10:
    E_ = np.array(ev)
    be, *_ = np.linalg.lstsq(E_[:, 1:3], E_[:, 0], rcond=None)
    # bootstrap CI over events (vectorised: 2000 resamples of the 2x2 normal equations)
    rng = np.random.default_rng(79)
    ii = rng.integers(0, len(E_), (2000, len(E_)))
    Xb, yb = E_[ii][:, :, 1:3], E_[ii][:, :, 0]
    XtX = np.einsum("bij,bik->bjk", Xb, Xb)
    Xty = np.einsum("bij,bi->bj", Xb, yb)
    bb = np.linalg.solve(XtX, Xty[..., None])[..., 0]
    EVT.update(coef_taken=float(be[0]), coef_lost=float(be[1]), ci_taken=pct(bb[:, 0] * 100, [5, 95]),
               ci_lost=pct(bb[:, 1] * 100, [5, 95]), d_off_p=pct(np.abs(E_[:, 0]), [50, 90]),
               taken_p=pct(np.abs(E_[:, 1]), [50, 90]), lost_p=pct(np.abs(E_[:, 2]), [50, 90]),
               r2=r2(E_[:, 0], E_[:, 1:3] @ be), sum_lost_over_taken=float(np.sum(np.abs(E_[:, 2])) /
                                                                         max(np.sum(np.abs(E_[:, 1])), 1e-9)))
    pr("  EVENT TEST (%d hands-off manoeuvres with quiet windows either side): d(offset) = %.2f x taken + %.2f x lost"
       " (90%% CI x100: taken %s, lost %s ; R2 %.2f) ; |d offset| p50/p90 %s LSB ; |taken| %s ; |lost| %s ;"
       " sum|lost|/sum|taken| %.2f" % (EVT["n"], EVT["coef_taken"], EVT["coef_lost"], EVT["ci_taken"],
                                         EVT["ci_lost"], EVT["r2"], EVT["d_off_p"], EVT["taken_p"], EVT["lost_p"],
                                         EVT["sum_lost_over_taken"]))
else:
    pr("  EVENT TEST: only %d events with quiet windows either side -- not fitted" % len(ev))
RES["e_event"] = EVT
# >22 m/s: the slow offset between the tap and the V298 replay (the band whose replay R2 is negative)
mh = eng & (v > 22) & ho_bar & (W["tse"] >= 1.2)
RES["c_gt22"] = dict(s=float(mh.sum() / 100), tap_mean=float(np.mean(Tap100[mh]) / 8), rep_mean=float(
    np.mean(REP["V298 design"]["T"][mh]) / 8), corr=float(np.corrcoef(Tap100[mh], REP["V298 design"]["T"][mh])[0, 1]),
    off_p=pct(off_S[mh], [10, 50, 90]))
pr("  >22 m/s: tap mean %.1f vs replay mean %.1f LSB, corr %.3f ; offset (car - replay, S-sign) p10/p50/p90 %s LSB"
   % (RES["c_gt22"]["tap_mean"], RES["c_gt22"]["rep_mean"], RES["c_gt22"]["corr"], RES["c_gt22"]["off_p"]))
TIM["total"] = round(time.time() - T00, 2)
RES["timing_s"] = TIM
pr("\nwall time %s" % TIM)


def _js(o):
    if isinstance(o, dict):
        return {str(k): _js(v_) for k, v_ in o.items()}
    if isinstance(o, (list, tuple)):
        return [_js(v_) for v_ in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 5)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _js(o.tolist())
    return o


(OUT / "m3.json").write_text(json.dumps(_js(RES), indent=1))
pr("wrote %s" % (OUT / "m3.json"))
