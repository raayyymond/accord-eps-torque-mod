# -*- coding: utf-8 -*-
r"""s1_report.py -- tables from s1_freq.py's cached rows (_scratch/v299_S1/s1_rows.npz, s1_paths.json).  Analysis only.
Writes out/s1_tables.md and out/s1_summary.json.  usage: python s1_report.py   (wall printed; ~2 s)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402

Z = np.load(S.SCR / "s1_rows.npz")
R, FR, CO = Z["R"], Z["FR"], Z["CO"]
PATHS = json.load(open(S.SCR / "s1_paths.json"))
C = {k: i for i, k in enumerate(S.COLS)}
FC_ = {k: i for i, k in enumerate(S.FCOLS)}
LN = [l.name for l in S.LOOPS]
out = []


def P(s=""):
    out.append(s)


def col(A, name):
    return A[:, C[name]]


def fcol(A, name):
    return A[:, FC_[name]]


def describe(row):
    return "%s @%.2f %s e%d %s a%.1f %s" % (
        S.MEMBERS[int(row[C["mem"]])], S.SPEEDS[int(row[C["v"]])], S.FRAMES[int(row[C["fr"]])][0], int(row[C["e"]]),
        "PD" if row[C["noI"]] else "PID", S.A_OP[int(row[C["aop"]])], S.FRIC[int(row[C["fric"]])][0])


def sel(li, block, fade1=True, gate_frames=False, noI=None):
    _, ia, ifc, frs, es = [b for b in S.BLOCKS if b[0] == block][0]
    m = (col(R, "loop") == li) & (col(R, "aop") == ia) & (col(R, "fric") == ifc)
    m &= np.isin(col(R, "fr"), S.GATE_FR if gate_frames else frs) & np.isin(col(R, "e"), es)
    m &= (col(R, "fade") == 1.0) if fade1 else (col(R, "fade") != 1.0)
    if noI is not None:
        m &= col(R, "noI") == int(noI)
    return m


def stats(m):
    A = R[m]
    pm, gm, tc, bar = col(A, "PM"), col(A, "GMu"), col(A, "Tc530"), col(A, "bar")
    fail = (pm < bar) | (gm < 6.0) | (tc > 3.0)
    k = int(np.argmin(pm - bar))
    kk = int(np.argmin(pm))
    return dict(n=int(len(A)), fails=int(fail.sum()), worst_margin=float((pm - bar)[k]), worst_at=describe(A[k]),
                minPM=float(pm[kk]), minPM_at=describe(A[kk]), lt30=int((pm < 30).sum()), minGM=float(gm.min()),
                maxMs=float(col(A, "Ms").max()), maxTc=float(tc.max()), r530=float(col(A, "r530").max()),
                r530_at=describe(A[int(np.argmax(col(A, "r530")))]),
                l1517_v295=float((col(A, "L1517") / col(A, "V295_1517")).max()),
                l1822_v295=float((col(A, "L1822") / col(A, "V295_1822")).max()),
                l1517=float(col(A, "L1517").max()), l1822=float(col(A, "L1822").max()))


SUMM = {"wall": json.load(open(S.SCR / "s1_wall.json"))}

# ---------------------------------------------------------------------------------------------------------------------
P("## A. Inner loop GATE 2 per unique linear loop and block (PID + PD, fade 1)")
P("")
P("Blocks: core = theta_op 0, no friction, frames nom/FA.83/FA1.155/FB.83/FB1.155/R79.55/R79.88, e -1/0/10; "
  "op1.5 / op2.5 = curve-hold operating point a_lat 1.5 / 2.5 m/s^2 (5 gate frames, e 0/10); fricA5 / fricA1 = Coulomb "
  "describing function at A = 5 / 1 deg (frames nom, FB.83, R79.55, R79.88; e 0/10).  Bars: singles 45 (e<=0) / 30, "
  "combined 30, GM_up 6 dB, |T_c| 5-30 Hz +3 dB.  r530 = max over 5-30 Hz of |L|/|L_V298| at the same point.  "
  "L/V295 = band peak |L| over V295's band peak on the same member/frame/e.")
P("")
P("| loop | block | n | fails | worst PM-bar (at) | min PM | #PM<30 | min GM dB | max Ms | max Tc dB | r530 vs V298 | 13-17 /V295 | 18-22 /V295 |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for li, ln in enumerate(LN):
    for b in S.BLOCKS:
        st = stats(sel(li, b[0]))
        SUMM.setdefault(ln, {})[b[0]] = st
        P("| %s | %s | %d | %d | %+.1f (%s) | %.1f | %d | %.1f | %.2f | %+.1f | %.3f | %.3f | %.3f |" % (
            ln, b[0], st["n"], st["fails"], st["worst_margin"], st["worst_at"], st["minPM"], st["lt30"], st["minGM"],
            st["maxMs"], st["maxTc"], st["r530"], st["l1517_v295"], st["l1822_v295"]))
P("")

# core split: gate frames only vs the route-79 frames; PID vs PD
P("### A2. Core block split: the panel's gate frames vs the route-79 measured D/P fractions; PID vs PD")
P("")
P("| loop | frames | loop state | n | fails | worst PM-bar (at) | min PM |")
P("|---|---|---|---|---|---|---|")
for li, ln in enumerate(LN):
    for fset, fname in ((S.GATE_FR, "gate box"), ((5, 6), "R79.55 / R79.88")):
        for noI in (False, True):
            m = (col(R, "loop") == li) & (col(R, "aop") == 0) & (col(R, "fric") == 0) & (col(R, "fade") == 1.0)
            m &= np.isin(col(R, "fr"), fset) & (col(R, "noI") == int(noI))
            st = stats(m)
            SUMM[ln]["core|%s|%s" % (fname, "PD" if noI else "PID")] = st
            P("| %s | %s | %s | %d | %d | %+.1f (%s) | %.1f |" % (ln, fname, "PD" if noI else "PID", st["n"], st["fails"],
                                                               st["worst_margin"], st["worst_at"], st["minPM"]))
P("")

# per-speed worst PM (PID, core gate frames) for each loop: where a table edit moves the margin
P("### A3. Worst PM over members/frames/e per speed (PID; core block, gate frames) -- where a G-table edit acts")
P("")
P("| v m/s | " + " | ".join(LN) + " |")
P("|---|" + "---|" * len(LN))
for iv, v in enumerate(S.SPEEDS):
    cells = []
    for li in range(len(LN)):
        m = sel(li, "core", gate_frames=True, noI=False) & (col(R, "v") == iv)
        A = R[m]
        cells.append("%.1f" % col(A, "PM").min())
    P("| %.2f | %s |" % (v, " | ".join(cells)))
P("")
P("### A4. Worst PM per speed at the curve-hold op-point a 2.5 m/s^2 (PID) and in the A = 1 deg friction state (PID)")
P("")
P("| v m/s | " + " | ".join("%s op2.5" % n for n in LN[:4]) + " | " + " | ".join("%s A1" % n for n in LN) + " |")
P("|---|" + "---|" * (4 + len(LN)))
for iv, v in enumerate(S.SPEEDS):
    c1 = ["%.1f" % col(R[sel(li, "op2.5", noI=False) & (col(R, "v") == iv)], "PM").min() for li in range(4)]
    c2 = ["%.1f" % col(R[sel(li, "fricA1", noI=False) & (col(R, "v") == iv)], "PM").min() for li in range(len(LN))]
    P("| %.2f | %s | %s |" % (v, " | ".join(c1), " | ".join(c2)))
P("")

# hands-on fade floor
P("### A5. Hands-on fade floor x0.30 (PD; nom frame, e 0, core): min PM / min GM")
P("")
for li, ln in enumerate(LN):
    m = (col(R, "loop") == li) & (col(R, "fade") != 1.0)
    A = R[m]
    P("- %s: n %d, min PM %.1f, min GM %.1f dB, fails(bar) %d" % (ln, len(A), col(A, "PM").min(), col(A, "GMu").min(),
                                                                int(((col(A, "PM") < col(A, "bar")) | (col(A, "GMu") < 6)).sum())))
P("")

# ---------------------------------------------------------------------------------------------------------------------
P("## B. Route-79 consistency of the plant family (V298 PID, theta_op 0, e 0): closed-loop T_ref = theta/theta_sp")
P("")
P("Measured on route 79: bandwidth 0.4-0.6 Hz at 8-25 m/s (1.1 Hz > 25), |H| <= 0.96, 0.1 Hz lag for < 5 deg corrections 1188 ms.")
P("")
P("| v | frame | friction | nominal bw Hz | nominal |T|pk | nominal lag@0.1 ms | members with bw in 0.3-0.8 Hz | median bw over members |")
P("|---|---|---|---|---|---|---|---|")
ci = {k: i for i, k in enumerate(("im", "iv", "ifr", "ifc", "bw", "Tpk", "lag01"))}
cons_tab = []
for iv, v in enumerate(S.SPEEDS):
    if v < 8 or v > 27:
        continue
    for ifr in (0, 5):
        for ifc in range(3):
            m = (CO[:, ci["iv"]] == iv) & (CO[:, ci["ifr"]] == ifr) & (CO[:, ci["ifc"]] == ifc)
            A = CO[m]
            nom = A[A[:, ci["im"]] == 0][0]
            inb = int(((A[:, ci["bw"]] >= 0.3) & (A[:, ci["bw"]] <= 0.8)).sum())
            P("| %.2f | %s | %s | %.2f | %.2f | %.0f | %d / %d | %.2f |" % (
                v, S.FRAMES[ifr][0], S.FRIC[ifc][0], nom[ci["bw"]], nom[ci["Tpk"]], nom[ci["lag01"]], inb, len(A),
                float(np.nanmedian(A[:, ci["bw"]]))))
            cons_tab.append(dict(v=v, frame=S.FRAMES[ifr][0], fric=S.FRIC[ifc][0], bw_nom=float(nom[ci["bw"]]),
                                 Tpk_nom=float(nom[ci["Tpk"]]), lag01=float(nom[ci["lag01"]]), in_band=inb, n=len(A)))
SUMM["consistency"] = cons_tab
P("")

# ---------------------------------------------------------------------------------------------------------------------
P("## C. Fork-coupled loops (theta_op 0, no friction; frames nom / FA.83 / FB1.155; e 0/10; Trt 30/60/90 ms)")
P("")
P("O1 loop: setpoint = theta(t - Trt) + tau_O1 * rate.  clip loop: setpoint = theta(t - Trt) +- c (+ D3's post-clip lead).")
P("")
P("| kind | loop | fade | state | n | min PM (at) | min GM dB | max Ms | #PM<30 |")
P("|---|---|---|---|---|---|---|---|---|")
fork_s = {}
for ki, kind in enumerate(S.KINDS):
    for li, ln in enumerate(LN):
        for fd in (1.0, S.FADE_HON):
            for noI in (False, True):
                m = (fcol(FR, "kind") == ki) & (fcol(FR, "loop") == li) & (np.isclose(fcol(FR, "fade"), fd)) & \
                    (fcol(FR, "noI") == int(noI))
                A = FR[m]
                if not len(A):
                    continue
                pm = fcol(A, "PM")
                k = int(np.argmin(pm))
                at = "%s @%.2f %s e%d Trt %.0f ms" % (S.MEMBERS[int(A[k, FC_["mem"]])], S.SPEEDS[int(A[k, FC_["v"]])],
                                                       S.FRAMES[int(A[k, FC_["fr"]])][0], int(A[k, FC_["e"]]),
                                                       A[k, FC_["trt"]] * 1000)
                st = dict(n=len(A), minPM=float(pm.min()), at=at, minGM=float(fcol(A, "GMu").min()),
                          maxMs=float(fcol(A, "Ms").max()), lt30=int((pm < 30).sum()))
                fork_s["%s|%s|%.3f|%s" % (kind, ln, fd, "PD" if noI else "PID")] = st
                P("| %s | %s | %.2f | %s | %d | %.1f (%s) | %.1f | %.2f | %d |" % (
                    kind, ln, fd, "PD" if noI else "PID", st["n"], st["minPM"], at, st["minGM"], st["maxMs"], st["lt30"]))
SUMM["fork"] = fork_s
P("")
# per-Trt split for the O1 loops (V298 inner loop): what the lead change buys
P("### C2. O1 loop on V298's inner loop, worst over members/frames/e, per round-trip delay (fade 1, PD | PID)")
P("")
P("| tau_O1 | Trt ms | PD min PM | PD min GM | PID min PM | PID min GM |")
P("|---|---|---|---|---|---|")
for kind in ("O1.06", "O1.00"):
    for trt in S.TRT:
        cells = []
        for noI in (True, False):
            m = (fcol(FR, "kind") == S.KINDS.index(kind)) & (fcol(FR, "loop") == 0) & (fcol(FR, "fade") == 1.0) & \
                (fcol(FR, "noI") == int(noI)) & np.isclose(fcol(FR, "trt"), trt)
            A = FR[m]
            cells += ["%.1f" % fcol(A, "PM").min(), "%.1f" % fcol(A, "GMu").min()]
        P("| %s | %.0f | %s |" % (kind[2:], trt * 1000, " | ".join(cells)))
P("")
# clip loop: D3 lead per speed
P("### C3. Clip-bound loop, worst PM per speed (PID, fade 1, worst Trt): plain vs D3's post-clip K3 lead")
P("")
P("| v | V298 clip | D3a-tab clip | V298 + K3 lead | D3a-tab + K3 lead |")
P("|---|---|---|---|---|")
for iv, v in enumerate(S.SPEEDS):
    cells = []
    for kind, li in (("clip", 0), ("clip", 2), ("clipD3lead", 0), ("clipD3lead", 2)):
        m = (fcol(FR, "kind") == S.KINDS.index(kind)) & (fcol(FR, "loop") == li) & (fcol(FR, "noI") == 0) & \
            (fcol(FR, "v") == iv)
        A = FR[m]
        cells.append("%.1f / %.1f dB" % (fcol(A, "PM").min(), fcol(A, "GMu").min()))
    P("| %.2f | %s |" % (v, " | ".join(cells)))
P("")

# ---------------------------------------------------------------------------------------------------------------------
P("## D. Reference path and the fork's path loop (nominal member, nom frame, e 0, PID; report only)")
P("")
P("| loop + reference lead | v | |T|pk 0.05-3 Hz | bw Hz | lag@0.2 ms | lag@0.5 ms | |T| 13-17 | |T| 18-22 | |T|@20 | path PMo | path GMo |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
for k, rows in PATHS.items():
    for r in rows:
        P("| %s | %.2f | %.3f | %.2f | %.0f | %.0f | %.4f | %.4f | %.4f | %.1f | %.1f |" % (
            k, r["v"], r["Tpk"], r["bw"], r["lag02"], r["lag05"], r["T1517"], r["T1822"], r["T20"], r["PMo"], r["GMo"]))
P("")

# ---------------------------------------------------------------------------------------------------------------------
# per-candidate summary
REFL = {"none": "V298|none", "D3K3": "D3a-tab|D3K3", "D5lead": "V298|D5lead", "D2aSD": "V298|D2aSD",
        "D2bPlan": "V298|D2bPlan"}
CAND_ROWS = []
P("## E. One row per candidate")
P("")
P("| candidate | inner loop | core fails | core worst PM-bar | op-pt min PM (2.5) | fricA1 min PM (V298) | min PM any | PM<30 | r530 vs V298 | 13-17/V295 | 18-22/V295 | O1 min PM (applic.) | clip min PM | path PMo min | |T_ref|@20 max |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
v298fA1 = SUMM["V298"]["fricA1"]["minPM"]
for cid, des, ln, o1, o1state, clipk, lead, note in S.CANDS:
    s = SUMM[ln]
    core = s["core"]
    allmin = min(s[b[0]]["minPM"] for b in S.BLOCKS)
    lt30 = sum(s[b[0]]["lt30"] for b in S.BLOCKS)
    r530 = max(s[b[0]]["r530"] for b in S.BLOCKS)
    states = ("PID", "PD") if o1state == "PID+PD" else ("PD",)
    o1pm = min(fork_s["%s|%s|%.3f|%s" % (o1 if not (o1 == "O1.00" and ln != "V298") else "O1.06", ln, fd, stt)]["minPM"]
               for fd in (1.0, S.FADE_HON) for stt in states)
    o1gm = min(fork_s["%s|%s|%.3f|%s" % (o1, ln, fd, stt)]["minGM"] for fd in (1.0, S.FADE_HON) for stt in states)
    clp = min(fork_s["%s|%s|%.3f|%s" % (clipk, ln, 1.0, stt)]["minPM"] for stt in ("PID", "PD"))
    pk = PATHS[REFL[lead]] if lead != "none" else PATHS["%s|none" % (ln if ln != "D3a-tab" else "V298")]
    pmo = min(r["PMo"] for r in pk)
    t20 = max(r["T20"] for r in pk)
    flags = []
    if allmin < 30:
        flags.append("PM<30")
    if r530 > 1.0005:
        flags.append("5-30 Hz |L| > V298 (x%.3f)" % r530)
    if core["fails"]:
        flags.append("core gate fails %d" % core["fails"])
    if s["fricA1"]["minPM"] < v298fA1 - 0.05:
        flags.append("friction PM below V298 by %.1f" % (v298fA1 - s["fricA1"]["minPM"]))
    if o1pm < 30:
        flags.append("O1 loop PM<30")
    if clp < 30:
        flags.append("clip loop PM<30")
    row = dict(cid=cid, designer=des, loop=ln, note=note, core_fails=core["fails"], core_worst=core["worst_margin"],
               core_worst_at=core["worst_at"], op25=s["op2.5"]["minPM"], fricA1=s["fricA1"]["minPM"],
               fricA5=s["fricA5"]["minPM"], allmin=allmin, lt30=lt30, r530=r530, l1517=core["l1517_v295"],
               l1822=core["l1822_v295"], o1pm=o1pm, o1gm=o1gm, o1state=o1state, o1kind=o1, clip=clp, clipkind=clipk,
               pmo=pmo, t20=t20, lead=lead, flags=flags)
    CAND_ROWS.append(row)
    P("| %s | %s | %d | %+.1f | %.1f | %.1f | %.1f | %d | %.3f | %.3f | %.3f | %.1f (%s %s) | %.1f (%s) | %.1f | %.4f |" % (
        cid, ln, core["fails"], core["worst_margin"], s["op2.5"]["minPM"], s["fricA1"]["minPM"], allmin, lt30, r530,
        core["l1517_v295"], core["l1822_v295"], o1pm, o1, o1state, clp, clipk, pmo, t20))
P("")
for r in CAND_ROWS:
    P("- **%s**: %s" % (r["cid"], "; ".join(r["flags"]) if r["flags"] else "no flag"))
SUMM["candidates"] = CAND_ROWS
P("")
P("report wall %.1f s" % (time.time() - T0))
(HERE / "out" / "s1_tables.md").write_text("\n".join(out) + "\n", encoding="utf-8")
json.dump(SUMM, open(HERE / "out" / "s1_summary.json", "w"), indent=1, default=float)
print("\n".join(out[-25:]))
print("tables -> out/s1_tables.md ; wall %.1f s" % (time.time() - T0))
