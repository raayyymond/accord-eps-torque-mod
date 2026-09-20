# -*- coding: utf-8 -*-
"""L2 -- read the L1 spectra and print the loop-shaping tables.

Sections
  A  VALIDATION on real data: C_fb measured vs analytic; and K_y vs -C_fb on the V282 routes,
     where the PID is the ONLY feedback path, so the total-loop estimator must reproduce it.
  B  THE PLANT Pl (command -> measured wheel angle), per build and speed -- gain, phase, and the
     same thing in deg per unit torque.  Says what each build's Pl contains.
  C  THE OPEN LOOP: |L|, crossover, phase margin, gain margin, Ms, f(|S|>1), with bootstrap CIs.
  D  The two decisive comparisons.
"""
import json
import sys
from pathlib import Path

import numpy as np

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
ORDER = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
         "00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
         "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
         "00000076--d0b7ea7e4d", "00000075--6c8687d5bd",
         "00000070--717f5a7866", "00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8"]
SHORT = {r: r[6:8] for r in ORDER}


def load_all():
    D = {}
    for r in ORDER:
        p = OUT / f"L1_{r}.json"
        if p.exists():
            D[r] = json.load(open(p))
    return D


def cx(b, k):
    return np.array(b[f"{k}_re"]) + 1j * np.array(b[f"{k}_im"])


def at(f, arr, fq):
    return arr[int(np.argmin(np.abs(f - fq)))]


def sec_A(D):
    print("=" * 118)
    print("A. VALIDATION ON REAL DATA")
    print("   A1  C_fb measured (IV) vs C_fb analytic from the flown kp/ki/LAF + lsf + notch.")
    print("   A2  K_y (total feedback map) vs -C_fb.  On V282 the PID is the ONLY feedback path,")
    print("       so A2 must read ~0 there; on the torque builds the gap IS the inner loops.")
    print("=" * 118)
    print(f"{'route':6s} {'grp':7s} {'bin':6s} {'n':>4s} {'coh(y,u)':>8s} "
          f"{'|C|/|Can| .3':>12s} {'.6':>6s} {'.9':>6s} {'1.2':>6s} | {'|Ky|/|C| .3':>11s} {'.6':>6s} {'.9':>6s} {'1.2':>6s} {'1.8':>6s}")
    for r, d in D.items():
        for key, b in d["bins"].items():
            if b["nps"] != 1024 or b["tag"] not in ("15-22", "8-15"):
                continue
            f = np.array(b["f"])
            C, Can, Ky = cx(b, "C"), cx(b, "Can"), cx(b, "Ky")
            rat = [abs(at(f, C, q)) / abs(at(f, Can, q)) for q in (0.3, 0.6, 0.9, 1.2)]
            rky = [abs(at(f, Ky, q)) / abs(at(f, C, q)) for q in (0.3, 0.6, 0.9, 1.2, 1.8)]
            cy = np.median(np.array(b["coh_yu"])[(f >= 0.3) & (f <= 2.0)])
            print(f"{SHORT[r]:6s} {d['group']:7s} {b['tag']:6s} {b['n_win']:4d} {cy:8.3f} "
                  + " ".join(f"{x:6.3f}" for x in rat) + "   |  "
                  + " ".join(f"{x:6.2f}" for x in rky))
    print()


def sec_B(D):
    print("=" * 118)
    print("B. THE PLANT Pl SEEN BY THE FORK  (logged command -> torqueState.actualLateralAccel,")
    print("   which IS the measured steering angle through a static vehicle-model gain).")
    print("   V282's Pl CONTAINS the EPS's own 1 kHz rate servo.  V293's Pl is the open-loop torque map")
    print("   plus the rack -- NOT a like-for-like plant.  phase is printed as LAG = 180 - arg(P).")
    print("=" * 118)
    print(f"{'route':6s} {'grp':7s} {'bin':6s} {'kvm':>6s} | " +
          " ".join(f"{q:>13s}" for q in ("0.3 Hz", "0.6 Hz", "0.9 Hz", "1.2 Hz", "1.8 Hz", "2.4 Hz")))
    print(f"{'':6s} {'':7s} {'':6s} {'m/s2/d':>6s} | " + " ".join(f"{'|P| lag':>13s}" for _ in range(6)))
    for r, d in D.items():
        for key, b in d["bins"].items():
            if b["nps"] != 1024 or b["tag"] not in ("15-22", "8-15"):
                continue
            f = np.array(b["f"])
            P = cx(b, "P")
            coh = np.array(b["coh_ru"])
            cells = []
            for q in (0.3, 0.6, 0.9, 1.2, 1.8, 2.4):
                j = int(np.argmin(np.abs(f - q)))
                lag = 180.0 - np.degrees(np.angle(P[j]))
                lag = (lag + 180) % 360 - 180
                flag = " " if coh[j] >= LP.COH_GATE else ("~" if coh[j] >= LP.COH_SOFT else "?")
                cells.append(f"{abs(P[j]):6.2f}{flag}{lag:6.0f}")
            print(f"{SHORT[r]:6s} {d['group']:7s} {b['tag']:6s} {b['kvm']:6.4f} | " + " ".join(cells))
    print("   flags: blank = instrument coherence >= 0.5   ~ = 0.2-0.5   ? = < 0.2 (not identified)")
    print("   deg of wheel per unit torque = |P| / kvm")
    print()


def sec_C(D, which="tot"):
    nm = {"pid": "L_pid = P*C_fb  (the PID's loop only)", "tot": "L_tot = -P*K_y  (PID + inner rate loop + observer)"}
    print("=" * 118)
    print(f"C. OPEN-LOOP SHAPE -- {nm[which]}   [5,95] run-cluster bootstrap CIs")
    print("=" * 118)
    print(f"{'route':6s} {'grp':7s} {'bin':6s} {'nps':>5s} {'|L|0.3':>16s} {'|L|0.6':>16s} {'|L|0.9':>16s} "
          f"{'|L|1.2':>14s} {'wc Hz':>14s} {'PM deg':>14s} {'Ms':>14s} {'f_Ms':>6s} {'f|S|>1':>7s}")
    for r, d in D.items():
        for key, b in d["bins"].items():
            if b["nps"] != 1024 or b["tag"] not in ("15-22", "22+", "8-15"):
                continue
            m = b[f"m_{which}"]
            ci = b["ci"]

            def c(k, fmt="{:.2f}"):
                v = ci.get(f"{which}_{k}")
                return f"[{fmt.format(v[0])},{fmt.format(v[1])}]" if v else "[--]"
            wc = m["wc"]
            wcs = f"{wc:.3f}" if np.isfinite(wc) else "none"
            frac = ci.get(f"{which}_wc")
            wfr = f"({frac[2]*100:.0f}%)" if frac else ""
            print(f"{SHORT[r]:6s} {d['group']:7s} {b['tag']:6s} {b['nps']:5d} "
                  f"{m['magL_0.3']:6.3f}{c('magL_0.3','{:.2f}'):>10s} "
                  f"{m['magL_0.6']:6.3f}{c('magL_0.6','{:.2f}'):>10s} "
                  f"{m['magL_0.9']:6.3f}{c('magL_0.9','{:.2f}'):>10s} "
                  f"{m['magL_1.2']:5.3f}{c('magL_1.2','{:.2f}'):>9s} "
                  f"{wcs:>6s}{wfr:>8s} "
                  f"{m['pm'] if np.isfinite(m['pm']) else float('nan'):6.1f}{c('pm','{:.0f}'):>8s} "
                  f"{m['Ms']:5.3f}{c('Ms','{:.2f}'):>9s} {m['f_Ms']:6.2f} {m['f_S1']:7.2f}")
    print()


def sec_D(D):
    print("=" * 118)
    print("D. GROUP MEANS (routes are the unit; per-route values from the 15-22 m/s bin, nps 1024)")
    print("=" * 118)
    G = {}
    for r, d in D.items():
        for key, b in d["bins"].items():
            if b["nps"] != 1024 or b["tag"] != "15-22":
                continue
            G.setdefault(d["group"], []).append((r, b, d))
    rows = []
    for g, lst in G.items():
        def col(fn):
            a = np.array([fn(b, d) for _, b, d in lst], float)
            a = a[np.isfinite(a)]
            return (np.mean(a), np.min(a), np.max(a), len(a)) if len(a) else (np.nan,) * 3 + (0,)
        rows.append((g, len(lst),
                     col(lambda b, d: d["kp_over_laf"]),
                     col(lambda b, d: abs(at(np.array(b["f"]), cx(b, "P"), 0.6))),
                     col(lambda b, d: b["m_tot"]["magL_0.3"]),
                     col(lambda b, d: b["m_tot"]["magL_0.6"]),
                     col(lambda b, d: b["m_tot"]["magL_0.9"]),
                     col(lambda b, d: b["m_tot"]["Ms"]),
                     col(lambda b, d: b["m_tot"]["f_Ms"]),
                     col(lambda b, d: b["m_tot"]["f_S1"]),
                     col(lambda b, d: b["m_tot"]["magS_0.9"])))
    hdr = ["kp/LAF", "|P|0.6", "|L|0.3", "|L|0.6", "|L|0.9", "Ms", "f_Ms", "f|S|>1", "|S|0.9"]
    print(f"{'group':8s} {'n':>2s} " + " ".join(f"{h:>18s}" for h in hdr))
    for row in rows:
        g, n = row[0], row[1]
        cells = [f"{m:6.3f}[{lo:.2f},{hi:.2f}]" for (m, lo, hi, k) in row[2:]]
        print(f"{g:8s} {n:2d} " + " ".join(f"{c:>18s}" for c in cells))
    print()


if __name__ == "__main__":
    D = load_all()
    print(f"{len(D)} routes loaded\n")
    sec_A(D)
    sec_B(D)
    sec_C(D, "pid")
    sec_C(D, "tot")
    sec_D(D)
