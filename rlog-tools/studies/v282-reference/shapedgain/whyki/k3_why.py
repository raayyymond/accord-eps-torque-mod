# -*- coding: utf-8 -*-
"""K3 -- WHY the integrator is weak: it is not the size of |L| it adds, it is the PHASE it adds.

1  arg(L) per band, measured.  |S| = 1/|1+L|, so what helps is Re(L), not |L|.  An integral term
   adds its gain at -90 deg relative to the P term; if arg(L) is ALREADY well below 0, the added
   vector points into the third quadrant and Re(1+L) FALLS even as |L| rises.

2  THE GOAL METRIC, implemented here from its own definition, per route: total (X-Y) error power
   over 0.15-2.4 Hz / total demand (X) power over the same band, >=15 m/s, laterally engaged,
   hands-off runs >= 30 s.  X = model desired lateral accel, Y = livePose yaw rate * v.
   Positive control: rev 6.4 must land near the study's 1.350 and V282 near 0.442.

3  The dose on that metric, by the exact identity  X - Y = A + V*D  (A the setpoint chain, V the
   measured wheel->yaw leg, D = Z - M the loop's own error), with D multiplied per bin by the
   measured complex sensitivity ratio S_new/S_old from K2.  A is held fixed -- that is the stated
   assumption, not a result.

out: K3-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402
from k1_iterm import CFG, ki_of, lsf_of, DT, FS  # noqa: E402

BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (1.80, 3.50)]
TORQ64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
LADDER = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8", "00000075--6c8687d5bd"]
ALL = TORQ64 + LADDER + V282
KI_BP = [8.0, 18.0]
NPS = 2048
MBAND = (0.15, 2.40)


def windows(S, min_s=30.0, nps=NPS, hop=None):
    hop = hop or nps // 2
    out = []
    for a, b in V.runs(V.usable(S, 15.0), S["t"], min_s=min_s):
        for s in range(a, b - nps + 1, hop):
            out.append((s, s + nps))
    return out


def route_pack(rk):
    S = V.load(rk)
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    e_log = np.interp(S["t"], D["t_cs"], D["cs_err"])
    X = np.nan_to_num(S["model"])
    Yp = np.nan_to_num(S["la_pose"])
    M = np.nan_to_num(S["la_act"])
    # sign of the livePose leg, from its own correlation with the controller's measurement
    u = V.usable(S)
    sgn = np.sign(np.corrcoef(Yp[u], M[u])[0, 1])
    Y = Yp * sgn
    Z = np.nan_to_num(S["setpoint"])
    p, i_, ff, out = (np.nan_to_num(S[k]) for k in ("p", "i", "f", "out"))
    with np.errstate(divide="ignore", invalid="ignore"):
        laf = float(np.nanmedian(np.where(np.abs(out) > 5e-3, -(p + i_ + ff) / out, np.nan)[u]))
    wins = windows(S)
    pack = dict(rk=rk, c=CFG[rk], sgn=float(sgn), laf=laf, wins=wins,
                X=X, Y=Y, Z=Z, M=M, p=p, i=i_, ffwd=ff, e=e_log, v=S["v"], t=S["t"])
    del S, D
    return pack


def spectra(P):
    """Windowed FFTs of X, Y, Z, M, p, i, ff on every window, plus per-window median speed."""
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, DT)
    keys = ["X", "Y", "Z", "M", "p", "i", "ffwd"]
    F = {k: np.empty((len(P["wins"]), len(f)), complex) for k in keys}
    vm = np.empty(len(P["wins"]))
    for j, (a, b) in enumerate(P["wins"]):
        for k in keys:
            F[k][j] = np.fft.rfft(signal.detrend(P[k][a:b]) * w)
        vm[j] = float(np.median(P["v"][a:b]))
    return f, F, vm


def main():
    print("=" * 128)
    print("K3  WHY Ki IS WEAK, AND WHAT IT IS WORTH ON THE GOAL METRIC")
    print("=" * 128)

    PK = {rk: None for rk in ALL}
    SP = {}
    for rk in ALL:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        P = route_pack(rk)
        if not P["wins"]:
            continue
        f, F, vm = spectra(P)
        SP[rk] = dict(f=f, F=F, vm=vm, c=P["c"], laf=P["laf"], sgn=P["sgn"],
                      nwin=len(P["wins"]), sec=len(P["wins"]) * NPS / 2 / FS,
                      segs=P["wins"], e=P["e"], p=P["p"], i=P["i"], ffwd=P["ffwd"], v=P["v"])
        del P

    # ---------------- 1. the phase of L ----------------
    print("\n1  arg(L) and Re(L), MEASURED.  L = (C_P + C_I)*G with C_P = S_Ep/S_EE, C_I = S_Ei/S_EE,")
    print("   G = S_fy/S_fu (feedforward instrument).  Power-weighted per bin, E as the weight.")
    print(f"   {'route':10s} {'grp':5s} " + " ".join(f"{('%.2f-%.2f' % bd):>22s}" for bd in BANDS[:4]))
    print(f"   {'':10s} {'':5s} " + " ".join(f"{'|L|  argL  ReL   |S|':>22s}" for _ in BANDS[:4]))
    LL = {}
    for rk in ALL:
        if rk not in SP:
            continue
        d = SP[rk]; F = d["F"]; f = d["f"]
        E = F["Z"] - F["M"]
        xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
        See = xs(E, E).real
        CP = xs(E, F["p"]) / np.maximum(See, 1e-300)
        CI = xs(E, F["i"]) / np.maximum(See, 1e-300)
        U = F["p"] + F["i"] + F["ffwd"]
        G = xs(F["ffwd"], F["Y"] * 0 + F["M"]) / xs(F["ffwd"], U)
        L = (CP + CI) * G
        LL[rk] = dict(f=f, CP=CP, CI=CI, G=G, L=L, W=See)
        line = f"   {rk[:8]:10s} {d['c']['g']:5s} "
        for (a_, b_) in BANDS[:4]:
            s = (f >= a_) & (f < b_); w = np.maximum(See[s], 1e-300)
            line += (f"{np.average(np.abs(L[s]), weights=w):5.2f}"
                     f"{np.average(np.degrees(np.angle(L[s])), weights=w):6.0f}"
                     f"{np.average(L[s].real, weights=w):6.2f}"
                     f"{np.average(np.abs(1/(1+L[s])), weights=w):6.2f} ")
        print(line)

    print("\n   READ: |S| improves only through Re(L).  The I term enters L at -90 deg relative to the P")
    print("   term, so it adds  |dL| * sin(argL)  to Re(L): NEGATIVE wherever argL < 0.")

    # ---------------- 2. the goal metric ----------------
    print("\n2  THE GOAL METRIC as defined: sum|X-Y|^2 over 0.15-2.4 Hz / sum|X|^2 over the same band,")
    print("   >=15 m/s, laterally engaged, hands off, runs >= 30 s (20.48 s Hann windows, 50 % overlap).")
    print(f"   {'route':10s} {'grp':5s} {'ki_eff':>7s} {'kp/LAF':>7s} {'win':>4s} {'sec':>6s} "
          f"{'sgn':>4s} {'METRIC':>8s}")
    MET = {}
    for rk in ALL:
        if rk not in SP:
            continue
        d = SP[rk]; f = d["f"]; F = d["F"]; c = d["c"]
        s = (f >= MBAND[0]) & (f < MBAND[1])
        err = np.sum(np.abs(F["X"][:, s] - F["Y"][:, s]) ** 2)
        dem = np.sum(np.abs(F["X"][:, s]) ** 2)
        kie = float(np.median(np.interp(d["vm"], KI_BP, [c["ki"], c["kih"]]) if c["kih"] > 0
                              else np.full(len(d["vm"]), c["ki"])))
        MET[rk] = float(err / dem)
        print(f"   {rk[:8]:10s} {c['g']:5s} {kie:7.3f} {c['kp']/c['laf']:7.4f} {d['nwin']:4d} "
              f"{d['sec']:6.0f} {d['sgn']:4.0f} {err/dem:8.3f}")
    for g, rs in (("rev 6.4 (T64/T64B/T5)", TORQ64), ("V282 reference", V282)):
        vals = [MET[r] for r in rs if r in MET]
        if vals:
            print(f"   {g:34s} route median {np.median(vals):.3f}   pooled mean {np.mean(vals):.3f}")

    # ---------------- 3. the dose on the metric ----------------
    print("\n3  DOSE ON THE METRIC via the exact identity  X - Y = A + V*D.")
    print("   V = S_MY/S_MM measured per route (the wheel->yaw leg, OUTSIDE the loop).  A is then defined")
    print("   EXACTLY as (X-Y) - V*D per window, so the identity holds bit for bit and A carries whatever")
    print("   the V regression does not.  A dose multiplies D by the complex ratio S_new/S_old, per bin.")
    print("   ASSUMPTION, stated: the exogenous drivers of D and the whole A leg are unchanged.")
    doses = [("as flown", None, 1.0), ("KiHigh 1.0", 1.0, 1.0), ("KiHigh 2.5", 2.5, 1.0),
             ("KiHigh 4.0", 4.0, 1.0), ("KiHigh 6.0", 6.0, 1.0),
             ("SteerKP 2.0", None, 2.0), ("SteerKP 3.0", None, 3.0),
             ("KiHigh 2.5 + KP 2.0", 2.5, 2.0), ("KiHigh 6.0 + KP 3.0", 6.0, 3.0)]
    base = np.median([MET[r] for r in TORQ64 if r in MET])
    ref = np.median([MET[r] for r in V282 if r in MET])
    print(f"\n   baseline (rev 6.4 median) {base:.3f}   V282 reference {ref:.3f}   gap {base-ref:.3f}")
    print(f"   {'lever':22s} " + " ".join(f"{r[:8]:>10s}" for r in TORQ64) + f" {'median':>9s} {'gap closed':>11s}")
    for name, kih, kpm in doses:
        cells = []
        for rk in TORQ64:
            if rk not in SP or rk not in LL:
                continue
            d = SP[rk]; F = d["F"]; f = d["f"]; c = d["c"]
            xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
            Vleg = xs(F["M"], F["Y"]) / np.maximum(xs(F["M"], F["M"]).real, 1e-300)
            Dw = F["Z"] - F["M"]
            Aw = (F["X"] - F["Y"]) - Vleg * Dw
            L0 = LL[rk]["L"]; CP = LL[rk]["CP"]; CI = LL[rk]["CI"]; G = LL[rk]["G"]
            v = float(np.median(d["vm"])); lsf = float(lsf_of(v)); kp0 = c["kp"]
            ki0 = c["ki"] if c["kih"] <= 0 else float(np.interp(v, KI_BP, [c["ki"], c["kih"]]))
            ki1 = ki0 if kih is None else float(np.interp(v, KI_BP, [c["ki"], kih]))
            kp1 = kp0 * kpm
            sP = (kp1 + lsf) / (kp0 + lsf)
            sI = (ki1 / ki0) * (1 + lsf / kp1) / (1 + lsf / kp0)
            L1 = (CP * sP + CI * sI) * G
            r = (1 + L0) / (1 + L1)
            s = (f >= MBAND[0]) & (f < MBAND[1])
            new = np.sum(np.abs(Aw[:, s] + Vleg[s] * Dw[:, s] * r[s]) ** 2)
            dem = np.sum(np.abs(F["X"][:, s]) ** 2)
            cells.append(float(new / dem))
        m = float(np.median(cells))
        print(f"   {name:22s} " + " ".join(f"{x:10.3f}" for x in cells) +
              f" {m:9.3f} {100*(base-m)/max(base-ref,1e-9):10.1f} %")

    # ---------------- 4. what shape WOULD work ----------------
    print("\n4  IF THE PROBLEM IS PHASE, WHAT SHAPE WOULD WORK?  The same |dL| added to L at a chosen")
    print("   phase, on the rev-6.4 routes, 0.15-0.30 Hz -- to show the integrator's -90 deg is the")
    print("   WORST available direction, not merely a weak one.  (Diagnostic; no such toggle exists.)")
    print(f"   {'added phase':>14s} {'|L| after':>10s} {'|S| after':>10s} {'errx':>8s}")
    rk = TORQ64[0]
    d = SP[rk]; f = d["f"]; L0 = LL[rk]["L"]; W = LL[rk]["W"]
    s = (f >= 0.15) & (f < 0.30); w = np.maximum(W[s], 1e-300)
    s0 = float(np.average(np.abs(1 / (1 + L0[s])), weights=w))
    dmag = float(np.average(np.abs(L0[s]), weights=w)) * 0.9      # the size KiHigh 2.5 adds
    for ph in (0, -30, -45, -60, -90, -120, +45, +90):
        L1 = L0 + dmag * np.exp(1j * np.radians(ph)) * np.exp(1j * np.angle(L0))
        s1 = float(np.average(np.abs(1 / (1 + L1[s])), weights=w))
        print(f"   {ph:>13d}d {float(np.average(np.abs(L1[s]), weights=w)):10.2f} {s1:10.3f} {s1/s0:8.3f}")


if __name__ == "__main__":
    main()
