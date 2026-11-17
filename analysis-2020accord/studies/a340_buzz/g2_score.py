# -*- coding: utf-8 -*-
"""g2_score.py -- GATE 2 (PM, GM, closed-loop peak 5-30 Hz, Ms) for the V300-A340 angle loop under four DampAxis
configurations, on (A) the A160 identified family box, (B) the family box scaled to the A340 low-frequency estimate,
(C) an EXPLICIT mechanical plant + explicit lane (with its own delay) -- the only form that can show the lane's LOCAL loop.
Everything reuses the release re-score script's functions (imported, not edited).  ANALYSIS ONLY.  Seconds."""
import json
import math
import os
import struct
import sys
import time
import numpy as np

t00 = time.time()
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
OUT = os.path.join(KIT, "analysis-2020accord", "_scratch", "out", "a340_buzz")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "release"))
import gate2_rescore_stock_terms as G   # noqa: E402
HF = G.HF
F = G.F
FH = np.unique(np.concatenate([np.logspace(-1, math.log10(480.0), 1100), [5.0, 30.0, 200.0]]))

# ---- built-image reads (EVIDENCE): A340 REV 3 lane cells + authority
FWR = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
A340 = open(FWR + "_v300_a340_REV3_plain_image.bin", "rb").read()
h = lambda a: struct.unpack_from("<h", A340, a)[0]   # noqa: E731
Hh = lambda a: struct.unpack_from("<H", A340, a)[0]  # noqa: E731
ROWS_X3 = [h(0xD7A5C + 2 * i) for i in range(3)]
assert ROWS_X3 == [h(0xD7A6C + 2 * i) for i in range(3)] == [-29490, -17202, -16000]
assert A340[0xC40D4] == 14 and A340[0xC645A] == 37 and h(0xC407E) == 511 and Hh(0xC6E88) == 5328
assert [Hh(0xC4C00 + 218 + 6 * i + 2) for i in range(6)] == [589, 733, 380, 280, 534, 1094]       # G' = G/2 (round half up)
ROWS_S = list(G.DA_Y_S)
AUTH = 5328.0 / 5346.0                     # A340 private gain vs the A160 V300 cell
CFG = {
    "REV3 x3/a14": (ROWS_X3, 14),
    "REV4 stock/a22": (ROWS_S, 22),
    "MID stock/a14": (ROWS_S, 14),
    "x1.5/a22": ([1.5 * y for y in ROWS_S], 22),
    "x2/a22": ([2.0 * y for y in ROWS_S], 22),
    "x2/a14": ([2.0 * y for y in ROWS_S], 14),
}
SIG_R, SIG_D = -1.0, +1.0                  # the release doc's anchors (BELIEF-anchored; tracer: lane opposes acceleration)


def F_da(f, v, rows, K2, dl=0):
    """DampAxis lane, T counts per deg of theta (torque added in u's sense); dl = extra ticks of lane delay."""
    Y = float(np.interp(v * 3.6 * 64.0, G.DA_X, rows))
    chain = 1024.0 * G.ema(f, 37 / 128.0) * (1 - G.zi(f)) * 32.0 * G.ema(f, K2 / 64.0) / 512.0
    return SIG_D * Y * G.DA_SCALE * chain * G.KAPPA_M * (2j * np.pi * np.asarray(f, float)) * G.zi(f) ** dl


assert np.allclose(F_da(F, 3.0, ROWS_X3, 14), G.F_dampaxis(F, 3.0, "v299", SIG_D))
assert np.allclose(F_da(F, 12.5, ROWS_S, 22), G.F_dampaxis(F, 12.5, "stock", SIG_D))


def J_lane(v, rows):
    """low-frequency inertia equivalent of the lane, T per deg/s^2 (EMA DC gains = 1)."""
    return abs(float(np.interp(v * 3.6 * 64.0, G.DA_X, rows))) * G.DA_SCALE * 64.0 * G.KAPPA_M * 1e-3


def metrics(c, P, f):
    """release-script loop_metrics + T peak 30-200 Hz when the grid reaches it."""
    r = G.loop_metrics(c, P * AUTH, f)
    if f[-1] > 100:
        L = G.C_fb_v299(f, c) * P * AUTH
        T = L / (1 + L)
        b = (f >= 30) & (f <= 200)
        r["T30200_db"] = 20 * math.log10(float(np.abs(T[b]).max()))
    return r


def gate(r):
    return ("" if r["pm"] >= 45 else "PM<45 ") + ("" if r["gm_db"] >= 6 else "GM<6 ") + ("" if r["T530_db"] <= 3 else "T>+3 ")


fm, Hm, cohm, _, _ = G.measure_htb()
HTBFIT = G.fit_two_mass(fm, Hm, cohm)
HTB = G.htb_model(F, HTBFIT)
HTBH = G.htb_model(FH, HTBFIT)
MEMB = ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "ms_free")
res = {}

# =============================================================== (A) the A160 family box
print("(A) A160 FAMILY BOX -- angle loop, r24 stock, lane per config.  cells: PM deg / GM dB / T5-30 dB / Ms   [gate flags]")
rowsA = []
for v in HF.SPEEDS:
    c = G.ctl_v299(v)
    Fr = G.F_r24(F, v, G.r24_gain_stock(v) - 2.0, SIG_R, HTB)
    F3 = F_da(F, v, ROWS_X3, 14)
    for m in MEMB:
        P = HF.plant_at(m, v).frf(F)
        d = dict(v=v, member=m)
        for name, (rows, K2) in CFG.items():
            Pc = P / (1 - P * (F_da(F, v, rows, K2) - F3 + Fr))
            r = metrics(c, Pc, F)
            d[name] = dict(pm=r["pm"], gm=r["gm_db"], T=r["T530_db"], fT=r["fTpk"], Ms=r["Ms"], L20=r["L20"], enc=r["encircle"], flag=gate(r))
        rowsA.append(d)
res["A"] = rowsA


def table(rows, keyf, names, only=None):
    print("| v | member | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for d in rows:
        if only and not only(d):
            continue
        print("| %g | %s | " % (d["v"], keyf(d)) + " | ".join("%.0f / %.1f / %+.1f / %.2f %s" % (d[n]["pm"], d[n]["gm"], d[n]["T"], d[n]["Ms"],
                                                                                                ("**" + d[n]["flag"].strip() + "**") if d[n]["flag"] else "") for n in names) + " |")


NAMES = list(CFG)
table(rowsA, lambda d: d["member"], NAMES[:3], only=lambda d: d["member"] in ("nominal", "J_lo", "b_lo", "J_hi", "ms_free"))
print("\nfail census, family box (7 members x 7 speeds = 49 points):")
for n in NAMES:
    fl = [d for d in rowsA if d[n]["flag"]]
    print("  %-16s fails %2d : %s | min PM %.1f, min GM %.1f dB, max T5-30 %+.1f dB, max Ms %.2f" % (
        n, len(fl), ", ".join("%s@%g(%s)" % (d["member"], d["v"], d[n]["flag"].strip()) for d in fl) or "-",
        min(d[n]["pm"] for d in rowsA), min(d[n]["gm"] for d in rowsA), max(d[n]["T"] for d in rowsA), max(d[n]["Ms"] for d in rowsA)))

# =============================================================== (B) family box scaled to the A340 low-frequency estimate
KK = (1.0, 1.3, 2.4)      # k multipliers (A340/A160 tracking ratio 1.1-2.4, g2_ident)
KB = (0.7, 1.0, 1.6, 3.0)  # b multipliers (loss ratio 1.3-8 at <1 Hz incl. friction/hands; 0.7 = the estimator-bias side)
print("\n(B) A340 BOX = family member with k x kk, b x kb.  Worst point per config over kk in %s, kb in %s" % (KK, KB))
rowsB = []
for v in HF.SPEEDS:
    c = G.ctl_v299(v)
    Fr = G.F_r24(F, v, G.r24_gain_stock(v) - 2.0, SIG_R, HTB)
    F3 = F_da(F, v, ROWS_X3, 14)
    for m in ("nominal", "J_lo", "J_hi", "ms_free"):
        p0 = HF.plant_at(m, v)
        for kk in KK:
            for kb in KB:
                P = HF.Plant(J=p0.J, b=p0.b * kb, k=p0.k * kk).frf(F)
                d = dict(v=v, member=m, kk=kk, kb=kb)
                for name, (rows, K2) in CFG.items():
                    r = metrics(c, P / (1 - P * (F_da(F, v, rows, K2) - F3 + Fr)), F)
                    d[name] = dict(pm=r["pm"], gm=r["gm_db"], T=r["T530_db"], fT=r["fTpk"], Ms=r["Ms"], flag=gate(r))
                rowsB.append(d)
res["B"] = rowsB
for n in NAMES:
    fl = [d for d in rowsB if d[n]["flag"]]
    print("  %-16s fails %3d of %d | min PM %.1f, min GM %.1f dB, max T5-30 %+.1f dB, max Ms %.2f" % (
        n, len(fl), len(rowsB), min(d[n]["pm"] for d in rowsB), min(d[n]["gm"] for d in rowsB), max(d[n]["T"] for d in rowsB), max(d[n]["Ms"] for d in rowsB)))
    for d in sorted(fl, key=lambda d: -d[n]["T"])[:8]:
        print("       %s@%g kk %.1f kb %.1f: PM %.0f GM %.1f T %+.1f dB @%.1f Hz Ms %.2f  [%s]" % (
            d["member"], d["v"], d["kk"], d["kb"], d[n]["pm"], d[n]["gm"], d[n]["T"], d[n]["fT"], d[n]["Ms"], d[n]["flag"].strip()))
print("  central A340 estimate (nominal, kk 1.3, kb 1.6):")
table([d for d in rowsB if d["member"] == "nominal" and d["kk"] == 1.3 and d["kb"] == 1.6], lambda d: "nom k1.3 b1.6", NAMES[:3])
print("  J_lo at the A340 central k/b (kk 1.3, kb 1.6) and at kb 1.0:")
table([d for d in rowsB if d["member"] == "J_lo" and d["kk"] == 1.3 and d["kb"] in (1.0, 1.6) and d["v"] <= 8], lambda d: "J_lo k%.1f b%.1f" % (d["kk"], d["kb"]), NAMES[:3])


# =============================================================== (C) explicit mechanical plant + explicit lane: the LOCAL loop
def local_gm(Lloc, f):
    """Lloc = -P_mech * F_lane (the lane's own loop, 1 + Lloc = 0 unstable).  Margin at the worst negative-real crossing."""
    im, re = Lloc.imag, Lloc.real
    jx = np.where((np.sign(im[:-1]) != np.sign(im[1:])) & (re[:-1] < 0) & (f[:-1] > 20))[0]
    if not len(jx):
        return float("inf"), float("nan")
    j = max(jx, key=lambda i: abs(Lloc[i]))
    return -20 * math.log10(abs(Lloc[j])), float(f[j])


print("\n(C1) LOCAL LOOP of the lane on a rigid motor-side inertia J_m (b, k from nominal; irrelevant at these frequencies).")
print("     g_crit = J_lane(LF)/J_m at which 1 + Lloc = 0, and the frequency (alias at 100 Hz):")
gc = {}
for K2 in (22, 14):
    for dl in (1, 2, 3, 4, 5):
        Pm = HF.Plant(J=1.0, b=0.0, k=0.0).frf(FH)                  # unit inertia: Lloc scales as 1/J_m
        Fl = F_da(FH, 0.0, [-1.0, -1.0, -1.0], K2, dl) / J_lane(0.0, [-1.0, -1.0, -1.0])   # lane normalised to J_lane = 1
        gm, fx = local_gm(-Pm * Fl, FH)
        gc[(K2, dl)] = (10 ** (gm / 20.0), fx)
        print("       alpha2 %d  lane+transport delay %d ms: g_crit %.2f at %.0f Hz (alias %.1f Hz)" % (K2, dl, gc[(K2, dl)][0], fx, abs(((fx + 50) % 100) - 50)))
res["gcrit"] = {"%d_%d" % k: v for k, v in gc.items()}
print("     lane LF inertia J_lane (T per deg/s^2) by speed:  v      stock    x3(REV3)  ratio")
for v in (0.0, 3.0, 5.56, 8.0, 12.5, 16.0, 19.0, 25.0, 30.0):
    print("        %25s %5.1f   %.4f   %.4f   x%.2f" % ("", v, J_lane(v, ROWS_S), J_lane(v, ROWS_X3), J_lane(v, ROWS_X3) / J_lane(v, ROWS_S)))
print("     J_m window in which REV 3 is locally UNSTABLE at 16 m/s (buzz 100 %) AND stock is locally STABLE at every speed >= 2 m/s:")
win = {}
for dl in (2, 3, 4, 5):
    jmax = J_lane(16.0, ROWS_X3) / gc[(14, dl)][0]
    jmin = max(J_lane(v, ROWS_S) for v in np.linspace(2.0, 30.0, 57)) / gc[(22, dl)][0]
    win[dl] = (jmin, jmax)
    m_lo = [20 * math.log10(gc[(22, dl)][0] * jmax / J_lane(v, ROWS_S)) for v in (3.0, 5.56, 16.0, 25.0)]
    print("        delay %d ms: J_m in (%.4f, %.4f]  => stock local margin at 3/5.6/16/25 m/s is at most %s dB (and > 0)" % (
        dl, jmin, jmax, " / ".join("%.1f" % x for x in m_lo)))
    print("                     intermediate doses at 5.6 m/s, margin relative to the stock margin m: " + ", ".join(
        "%s: m %+.1f dB" % (n, 20 * math.log10(gc[(K2, dl)][0] / gc[(22, dl)][0] / (rows[1] / ROWS_S[1]))) for n, (rows, K2) in CFG.items()))
res["win"] = {str(k): v for k, v in win.items()}

print("\n(C2) ANGLE LOOP on the explicit plant: J_mech split motor/rim (two-mass, rim on the torsion bar f2 16.5 Hz) or rigid; lane explicit")
print("     with 2 ms delay; b,k = nominal x (1.6, 1.3) [A340 central] and x (1.0, 1.0).  cells: local GM dB | PM / GM / T5-30 / T30-200 / Ms")
rowsC = []
for v in (3.0, 5.0, 8.0, 12.5, 19.0, 26.0):
    c = G.ctl_v299(v)
    Fr = G.F_r24(FH, v, G.r24_gain_stock(v) - 2.0, SIG_R, HTBH)
    pn = HF.plant_at("nominal", v)
    for kb, kk in ((1.6, 1.3), (1.0, 1.0)):
        for Jm in (0.012, 0.02, 0.035, 0.07, 0.15):
            for r2 in (0.0, 0.5):
                if r2:
                    Pm = HF.Plant(J=Jm / (1 - r2), b=pn.b * kb, k=pn.k * kk, f2=16.5, zeta2=0.2, r2=r2).frf(FH)
                else:
                    Pm = HF.Plant(J=Jm, b=pn.b * kb, k=pn.k * kk).frf(FH)
                d = dict(v=v, Jm=Jm, r2=r2, kb=kb, kk=kk)
                for name in NAMES[:3]:
                    rows, K2 = CFG[name]
                    Fl = F_da(FH, v, rows, K2, 2)
                    lg, lf = local_gm(-Pm * Fl, FH)
                    r = metrics(c, Pm / (1 - Pm * (Fl + Fr)), FH)
                    d[name] = dict(lgm=lg, lf=lf, pm=r["pm"], gm=r["gm_db"], T=r["T530_db"], fT=r["fTpk"], T2=r["T30200_db"], Ms=r["Ms"], flag=gate(r))
                rowsC.append(d)
res["C"] = rowsC
print("| v | b,k x | J_m (motor side) | rim share | " + " | ".join(NAMES[:3]) + " |")
print("|---|---|---|---|---|---|---|")
for d in rowsC:
    if d["v"] not in (3.0, 8.0, 19.0):
        continue
    print("| %g | %.1f,%.1f | %.3f | %.1f | " % (d["v"], d["kb"], d["kk"], d["Jm"], d["r2"]) + " | ".join(
        ("LOCAL UNSTABLE %.1f dB @%.0f Hz" % (d[n]["lgm"], d[n]["lf"])) if d[n]["lgm"] <= 0 else
        "%.1f | %.0f / %.1f / %+.1f / %+.1f / %.2f %s" % (d[n]["lgm"], d[n]["pm"], d[n]["gm"], d[n]["T"], d[n]["T2"], d[n]["Ms"],
                                                         ("**" + d[n]["flag"].strip() + "**") if d[n]["flag"] else "") for n in NAMES[:3]) + " |")
json.dump(res, open(os.path.join(OUT, "g2_score.json"), "w"), indent=1, default=float)
print("\nwall %.1f s" % (time.time() - t00))
