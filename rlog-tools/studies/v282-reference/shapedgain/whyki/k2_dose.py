# -*- coding: utf-8 -*-
"""K2 -- WHAT RAISING Ki BUYS, AND WHAT IT COSTS, on measured transfers only.

LOOP ALGEBRA (the same one adv6_dose.py used for the SteerKP dose, so the two are comparable):
    y = G*(u_fb + f),   u_fb = C_fb*E,   E = Z - y      =>   L = C_fb * G,  S = 1/(1+L)
    C_fb = C_P + C_I  measured separately from the SEPARATELY LOGGED p and i (H1 on the raw error E)
    G                 measured by INSTRUMENTAL VARIABLE with the feedforward f as the instrument:
                      G = S_fy / S_fu with u = p + i + f.  f is a function of the setpoint, speed and
                      the measured rate/observer -- it is the same instrument adv6 used.
A Ki change scales C_I ONLY, by ki_new_eff/ki_old_eff, and leaves C_P untouched (source: p = kp*e,
i += ki*dt*e, both on the SAME notched, lsf-inflated error).  That is measurement + algebra.

SHAKE COST is NOT taken from the loop: it is the EXACT re-synthesis of the logged command at the new
gain (re-integrate the logged pid error with the fork's recursion), band-filtered 1.8-3.5 Hz.  The
SteerKP x2 column is a POSITIVE CONTROL: the study's published figure is x1.16-1.38.

out: K2-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402
from k1_iterm import CFG, ORDER, ki_of, lsf_of, bandavg, DT, FS, NPS  # noqa: E402

BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (1.80, 3.50)]
TORQ64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
LADDER = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000075--6c8687d5bd"]
KI_BP = [8.0, 18.0]


def gather(rk):
    """Pooled cross-spectra over that route's >=15 m/s hands-off engaged runs >= 30 s."""
    c = CFG[rk]
    S = V.load(rk)
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    e_log = np.interp(S["t"], D["t_cs"], D["cs_err"])
    Z = np.nan_to_num(S["setpoint"]); Y = np.nan_to_num(S["la_act"])
    p, i_, ff, out = (np.nan_to_num(S[k]) for k in ("p", "i", "f", "out"))
    E = Z - Y
    U = p + i_ + ff
    with np.errstate(divide="ignore", invalid="ignore"):
        laf = float(np.nanmedian(np.where(np.abs(out) > 5e-3, -U / out, np.nan)[V.usable(S)]))
    segs = V.runs(V.usable(S, 15.0), S["t"], min_s=30.0)
    acc, vs = {}, []
    fr = None
    for a, b in segs:
        w = b - a
        pairs = dict(EE=(E[a:b], E[a:b]), Ep=(E[a:b], p[a:b]), Ei=(E[a:b], i_[a:b]),
                     fy=(ff[a:b], Y[a:b]), fu=(ff[a:b], U[a:b]), ff=(ff[a:b], ff[a:b]),
                     yy=(Y[a:b], Y[a:b]), uu=(U[a:b], U[a:b]), ZZ=(Z[a:b], Z[a:b]))
        for k, (x, y) in pairs.items():
            xs_, ys_ = x - x.mean(), y - y.mean()
            _, pxy = signal.csd(xs_, ys_, FS, nperseg=NPS, noverlap=NPS // 2)
            fr, _ = signal.welch(xs_, FS, nperseg=NPS, noverlap=NPS // 2)
            acc[k] = pxy * w if k not in acc else acc[k] + pxy * w
        vs.append(float(np.median(S["v"][a:b])))
    out_d = dict(laf=laf, v=float(np.median(vs)), c=c,
                 kie=float(np.median([np.median(ki_of(S["v"][a:b], c)) for a, b in segs])),
                 lsf=float(np.median([np.median(lsf_of(S["v"][a:b])) for a, b in segs])),
                 segs=[(a, b) for a, b in segs],
                 e_log=e_log, p=p, i=i_, ffwd=ff, v_arr=S["v"], t=S["t"])
    out_d.update({k: v for k, v in acc.items()})
    out_d["f"] = fr
    del S, D
    return out_d


def band_S(f, L, W, a, b):
    """|S| averaged per BIN over the band, power-weighted (magnitudes per bin, never a phasor mean)."""
    s = (f >= a) & (f < b)
    return float(np.average(np.abs(1.0 / (1.0 + L[s])), weights=np.maximum(W[s], 1e-300)))


def main():
    print("=" * 130)
    print("K2  THE Ki DOSE: loop gain bought, per band, from MEASURED C_P, C_I and G.")
    print("=" * 130)
    R = {}
    for rk in ORDER:
        if (V.CACHE / f"{rk}.npz").exists():
            R[rk] = gather(rk)

    # -------- 0. instrument quality --------
    print("\n0  INSTRUMENT: coherence of the feedforward instrument with u and with y, per band.")
    print(f"   {'route':10s} {'grp':5s} " + " ".join(f"{('%.2f-%.2f' % bd):>15s}" for bd in BANDS))
    print(f"   {'':10s} {'':5s} " + " ".join(f"{'coh_fu coh_fy':>15s}" for _ in BANDS))
    for rk in ORDER:
        if rk not in R:
            continue
        d = R[rk]; f = d["f"]
        cfu = np.abs(d["fu"]) ** 2 / np.maximum(d["ff"].real * d["uu"].real, 1e-300)
        cfy = np.abs(d["fy"]) ** 2 / np.maximum(d["ff"].real * d["yy"].real, 1e-300)
        line = f"   {rk[:8]:10s} {CFG[rk]['g']:5s} "
        for (a_, b_) in BANDS:
            line += f"{bandavg(f, cfu, d['ff'].real, a_, b_):7.2f}{bandavg(f, cfy, d['ff'].real, a_, b_):8.2f} "
        print(line)

    # -------- 1. the flown Ki ladder: |L| actually delivered --------
    print("\n1  THE FLOWN Ki LADDER (r71 ki 0.30 / r72 ki 0.60 / r75 ki 0.60->2.50 schedule; all kp 0.85, LAF 14).")
    print("   |L| = |(C_P + C_I) * G| power-weighted per bin.  This is NOT a prediction: these three flew.")
    print(f"   {'route':10s} {'ki_eff':>7s} " + " ".join(f"{('|L| %.2f-%.2f' % bd):>16s}" for bd in BANDS))
    for rk in LADDER + TORQ64[:1] + V282[:1]:
        if rk not in R:
            continue
        d = R[rk]; f = d["f"]
        CP = d["Ep"] / np.maximum(d["EE"].real, 1e-30)
        CI = d["Ei"] / np.maximum(d["EE"].real, 1e-30)
        G = d["fy"] / d["fu"]
        L = (CP + CI) * G
        line = f"   {rk[:8]:10s} {d['kie']:7.3f} "
        for (a_, b_) in BANDS:
            s = (f >= a_) & (f < b_)
            line += f"{float(np.average(np.abs(L[s]), weights=np.maximum(d['EE'].real[s],1e-300))):16.3f} "
        print(line + f"  ({CFG[rk]['g']})")

    # -------- 2. the dose curve on rev 6.4 --------
    print("\n2  DOSE CURVE on the rev-6.4 routes (T64/T64B/T5, ki 0.30 flat as flown).  AccordTorqueKiHigh")
    print("   acts from 18 m/s (AccordTorqueKi below 8, linear between), so the effective ki is evaluated at")
    print("   each run's own median speed.  'errx' = |S_new|/|S_old| per bin, power-weighted = the factor the")
    print("   COHERENT tracking error in that band is multiplied by.  Measurement + algebra, not a feel claim.")
    print(f"   {'lever':22s} " + " ".join(f"{('%.2f-%.2f' % bd):>13s}" for bd in BANDS))
    print(f"   {'':22s} " + " ".join(f"{'|L|   errx':>13s}" for _ in BANDS))
    doses = ([("as flown", None, 1.0)] +
             [(f"KiHigh {k:g}", k, 1.0) for k in (1.0, 2.5, 4.0, 6.0)] +
             [("SteerKP 2.0", None, 2.0), ("SteerKP 3.0", None, 3.0),
              ("KiHigh 2.5 + KP 2.0", 2.5, 2.0)])
    ROWS = {}
    for name, kih, kpm in doses:
        Lb, ex = {b: [] for b in BANDS}, {b: [] for b in BANDS}
        for rk in TORQ64:
            if rk not in R:
                continue
            d = R[rk]; f = d["f"]; c = d["c"]
            CP = d["Ep"] / np.maximum(d["EE"].real, 1e-30)
            CI = d["Ei"] / np.maximum(d["EE"].real, 1e-30)
            G = d["fy"] / d["fu"]
            kp0, lsf, v = c["kp"], d["lsf"], d["v"]
            ki0 = d["kie"]
            ki1 = ki0 if kih is None else float(np.interp(v, KI_BP, [c["ki"], kih]))
            kp1 = kp0 * kpm
            sP = (kp1 + lsf) / (kp0 + lsf)
            # a SteerKP change also scales I, through error_with_lsf = e*(1+lsf/kp)
            sI = (ki1 / ki0) * (1 + lsf / kp1) / (1 + lsf / kp0)
            L0 = (CP + CI) * G
            L1 = (CP * sP + CI * sI) * G
            for bd in BANDS:
                s = (f >= bd[0]) & (f < bd[1])
                w = np.maximum(d["EE"].real[s], 1e-300)
                Lb[bd].append(float(np.average(np.abs(L1[s]), weights=w)))
                ex[bd].append(band_S(f, L1, d["EE"].real, *bd) / band_S(f, L0, d["EE"].real, *bd))
        line = f"   {name:22s} "
        for bd in BANDS:
            line += f"{np.median(Lb[bd]):6.2f}{np.median(ex[bd]):7.3f} "
        ROWS[name] = {bd: (float(np.median(Lb[bd])), float(np.median(ex[bd]))) for bd in BANDS}
        print(line)

    # -------- 3. shake cost by exact command re-synthesis --------
    print("\n3  SHAKE COST -- EXACT command re-synthesis from the logged pid error, band RMS ratio.")
    print("   u_new = (kp_mult-scaled p + re-integrated i + f)/LAF.  The SteerKP 2.0 row is a POSITIVE")
    print("   CONTROL against the study's published x1.16-1.38 for that same dose.")
    sos = signal.butter(4, [1.8, 3.5], btype="band", fs=FS, output="sos")
    sos2 = signal.butter(4, [1.2, 2.4], btype="band", fs=FS, output="sos")
    print(f"   {'lever':22s} " + " ".join(f"{r[:8]:>12s}" for r in TORQ64) + f" {'median':>9s} {'(1.2-2.4)':>10s}")
    for name, kih, kpm in doses:
        cells, cells2 = [], []
        for rk in TORQ64:
            if rk not in R:
                continue
            d = R[rk]; c = d["c"]
            kp0, lsf = c["kp"], d["lsf"]
            num = num2 = den = den2 = 0.0
            for a, b in d["segs"]:
                e = d["e_log"][a:b]
                vv = d["v_arr"][a:b]
                ki0v = ki_of(vv, c)
                ki1v = ki0v if kih is None else np.interp(vv, KI_BP, [c["ki"], kih])
                kp1 = kp0 * kpm
                # error_with_lsf scales by (1+lsf/kp1)/(1+lsf/kp0) when SteerKP moves
                se = (1 + lsf / kp1) / (1 + lsf / kp0)
                p0, i0, f0 = d["p"][a:b], d["i"][a:b], d["ffwd"][a:b]
                p1 = p0 * kpm * se
                i1 = i0[0] + np.cumsum(ki1v * DT * e * se)
                i1 = i1 - (i1[0] - i0[0])
                u0 = (p0 + i0 + f0) / d["laf"]
                u1 = (p1 + i1 + f0) / d["laf"]
                for s_, acc_n, acc_d in ((sos, "a", "a"), (sos2, "b", "b")):
                    x0 = signal.sosfiltfilt(s_, u0); x1 = signal.sosfiltfilt(s_, u1)
                    if acc_n == "a":
                        num += float(np.sum(x1 ** 2)); den += float(np.sum(x0 ** 2))
                    else:
                        num2 += float(np.sum(x1 ** 2)); den2 += float(np.sum(x0 ** 2))
            cells.append(np.sqrt(num / max(den, 1e-30)))
            cells2.append(np.sqrt(num2 / max(den2, 1e-30)))
        print(f"   {name:22s} " + " ".join(f"{x:12.3f}" for x in cells) +
              f" {np.median(cells):9.3f} {np.median(cells2):10.3f}")

    print("\n4  WHERE THE TWO LEVERS PUT THEIR GAIN -- the shape argument, in one table.")
    print(f"   {'lever':22s} {'gain at 0.15-0.30':>18s} {'gain at 1.2-2.4':>17s} {'gain at 1.8-3.5':>17s} "
          f"{'shape ratio':>12s}")
    base = ROWS["as flown"]
    for name in ROWS:
        if name == "as flown":
            continue
        g1 = ROWS[name][(0.15, 0.30)][0] / base[(0.15, 0.30)][0]
        g2 = ROWS[name][(1.20, 2.40)][0] / base[(1.20, 2.40)][0]
        g3 = ROWS[name][(1.80, 3.50)][0] / base[(1.80, 3.50)][0]
        print(f"   {name:22s} {g1:18.2f} {g2:17.2f} {g3:17.2f} {g1/max(g2,1e-9):12.2f}")


if __name__ == "__main__":
    main()
