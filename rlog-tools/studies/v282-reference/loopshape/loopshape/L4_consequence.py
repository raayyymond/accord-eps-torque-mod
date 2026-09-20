# -*- coding: utf-8 -*-
"""L4 -- what the measured loop shape implies, by ALGEBRA on measured transfers only.

1. LAG DECOMPOSITION.  The closed loop from the shaped setpoint to the wheel angle is exactly
       T_ry = (P * C_total) * S ,     S = 1/(1+L),
   so its phase splits EXACTLY into a feedforward-and-plant part and a sensitivity part.  Both
   sides are measured (T_ry by IV, S from the identified L).  This says how much of the L34
   timing gap the loop gain is responsible for, and how much is the feedforward and the plant.
   This is a DECOMPOSITION OF A MEASUREMENT, not a prediction of a new configuration.

2. DOSE ALGEBRA.  A change to SteerKP/SteerLatAccel scales C_fb, hence L, by a constant k.
   From the measured L(jw): the new crossover, the new phase margin, the new Ms, and the gain
   margin ceiling.  Marked BELIEF where it extrapolates beyond the measured band.

3. SHAKE ACCOUNTING.  What share of the command's 1.8-3.5 Hz content is carried by the feedback
   term (p+i) versus the feedforward (f), per build -- measured, so a gain dose can be sized
   against the shake it moves as well as the tracking it buys.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
FAMS = ["V282", "T64", "T64B", "T5", "T4", "RF00T", "T2", "T3"]


def lag_decomp(bin_tag="15-22", nps=1024):
    D = json.load(open(OUT / "L3_pool.json"))
    print("=" * 112)
    print(f"1. LAG DECOMPOSITION of the measured closed loop  Z (shaped setpoint) -> M (wheel angle)")
    print(f"   T_ry = (P*C_total) * S.   lag = -arg/(2 pi f) in ms.   bin {bin_tag}, nperseg {nps}")
    print("=" * 112)
    print(f"{'family':8s} {'f Hz':>5s} {'coh':>5s} {'|Try|':>6s} {'lag_total':>10s} {'lag_S':>8s} "
          f"{'lag_ffplant':>12s} {'|S|':>5s} {'|L|':>6s}")
    rows = {}
    for fam in FAMS:
        k = f"{fam}|{bin_tag}|{nps}"
        if k not in D:
            continue
        b = D[k]
        f = np.array(b["f"])
        Try = np.array(b["Try_re"]) + 1j * np.array(b["Try_im"])
        L = np.array(b["L_re"]) + 1j * np.array(b["L_im"])
        coh = np.array(b["coh"])
        S = 1.0 / (1.0 + L)
        for fq in (0.20, 0.29, 0.39, 0.59, 0.78, 0.98, 1.17):
            j = int(np.argmin(np.abs(f - fq)))
            lt = -np.degrees(np.angle(Try[j])) / 360.0 / f[j] * 1000
            ls = -np.degrees(np.angle(S[j])) / 360.0 / f[j] * 1000
            fl = " " if coh[j] >= LP.COH_GATE else ("~" if coh[j] >= LP.COH_SOFT else "?")
            print(f"{fam:8s} {f[j]:5.2f}{fl}{coh[j]:5.2f} {abs(Try[j]):6.3f} {lt:10.0f} {ls:8.0f} "
                  f"{lt-ls:12.0f} {abs(S[j]):5.2f} {abs(L[j]):6.3f}")
            rows.setdefault(fam, {})[round(f[j], 2)] = (lt, ls, lt - ls, abs(S[j]), abs(L[j]))
        print()
    # the V282-vs-torque difference, leg by leg
    print(f"   GAP vs V282 (ms; + = torque mode is later).  'S part' is what the LOOP GAIN owns.")
    print(f"{'family':8s} " + " ".join(f"{q:>21s}" for q in ("0.20 Hz", "0.29 Hz", "0.39 Hz", "0.59 Hz", "0.98 Hz")))
    print(f"{'':8s} " + " ".join(f"{'total  S  ff+plant':>21s}" for _ in range(5)))
    ref = rows.get("V282", {})
    for fam in FAMS:
        if fam == "V282" or fam not in rows:
            continue
        cells = []
        for fq in (0.20, 0.29, 0.39, 0.59, 0.98):
            key = min(ref, key=lambda x: abs(x - fq))
            a, b2 = rows[fam].get(key), ref.get(key)
            cells.append(f"{a[0]-b2[0]:7.0f}{a[1]-b2[1]:7.0f}{a[2]-b2[2]:7.0f}" if a and b2 else " " * 21)
        print(f"{fam:8s} " + " ".join(cells))
    print()
    return D


def dose(D, bin_tag="15-22", nps=1024):
    print("=" * 112)
    print("2. DOSE ALGEBRA -- scale C_fb (i.e. SteerKP/SteerLatAccel) by k, recompute FROM THE")
    print("   MEASURED L.  EVIDENCE for the numbers; BELIEF for what the car would feel.")
    print("=" * 112)
    print(f"{'family':8s} {'kp/LAF':>7s} {'k':>5s} {'wc Hz':>7s} {'PM deg':>7s} {'Ms':>6s} {'f_Ms':>5s} "
          f"{'|S|0.2':>7s} {'|S|0.3':>7s} {'|S|0.6':>7s} {'|S|1.0':>7s} {'GM':>6s}")
    for fam in FAMS:
        k = f"{fam}|{bin_tag}|{nps}"
        if k not in D:
            continue
        b = D[k]
        f = np.array(b["f"])
        L0 = np.array(b["L_re"]) + 1j * np.array(b["L_im"])
        coh = np.array(b["coh"])
        band = (f >= 0.10) & (f <= 2.0) & (coh >= LP.COH_SOFT)
        for kk in (1.0, 1.5, 2.0, 2.5, 3.0):
            L = L0 * kk
            ff, LL = f[band], L[band]
            mag = np.abs(LL)
            xs = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
            if len(xs):
                j = xs[0]
                w = np.log(mag[j]) / (np.log(mag[j]) - np.log(mag[j + 1]))
                fc = ff[j] + w * (ff[j + 1] - ff[j])
                ph = np.unwrap(np.angle(LL))
                pm = 180 + np.degrees(np.angle(np.exp(1j * np.interp(fc, ff, ph))))
            else:
                fc, pm = np.nan, np.nan
            Sm = np.abs(1.0 / (1.0 + LL))
            jm = int(np.argmax(Sm))
            Sat = [abs(1.0 / (1.0 + L[int(np.argmin(np.abs(f - q)))])) for q in (0.2, 0.3, 0.6, 1.0)]
            gm = b["m"].get("gm")
            print(f"{fam:8s} {b['kp_laf']:7.4f} {kk:5.1f} {fc:7.3f} {pm:7.0f} {Sm[jm]:6.2f} {ff[jm]:5.2f} "
                  + " ".join(f"{x:7.2f}" for x in Sat)
                  + (f" {gm/kk:6.2f}" if gm else "    n/a"))
        print()


def shake_accounting(vlo=15.0, vhi=22.0, f1=1.8, f2=3.5):
    print("=" * 112)
    print(f"3. SHAKE-BAND COMMAND ACCOUNTING  ({f1}-{f2} Hz, {vlo}-{vhi} m/s, laterally engaged, hands off)")
    print("   rms of the command and of its parts, in output-torque units; share = var(part)/var(total).")
    print("   u = out ;  u_fb = -(p+i)/LAF  (the term a kp/LAF dose scales) ;  u_ff = -f/LAF")
    print("=" * 112)
    print(f"{'route':6s} {'fam':7s} {'rms u':>8s} {'rms ufb':>8s} {'rms uff':>8s} {'fb share':>9s} "
          f"{'rms srate':>10s} {'d/s per u':>10s}")
    sos = signal.butter(4, [f1, f2], btype="band", fs=LP.FS, output="sos")
    out = {}
    for route, fam in LP.GROUPS.items():
        if not (LP.V.CACHE / f"{route}.npz").exists():
            continue
        L = LP.load_loop(route)
        m = LP.runs_mask(L) & (L["v"] >= vlo) & (L["v"] < vhi)
        segs = LP.V.runs(m, L["t"], min_s=4.0)
        if not segs:
            del L
            continue
        laf = L["laf"]
        acc = {k: [] for k in ("u", "ufb", "uff", "sr")}
        for a, b in segs:
            acc["u"].append(signal.sosfiltfilt(sos, np.nan_to_num(L["out"][a:b])))
            acc["ufb"].append(signal.sosfiltfilt(sos, -(np.nan_to_num(L["p"][a:b]) + np.nan_to_num(L["i"][a:b])) / laf))
            acc["uff"].append(signal.sosfiltfilt(sos, -np.nan_to_num(L["f"][a:b]) / laf))
            acc["sr"].append(signal.sosfiltfilt(sos, np.nan_to_num(L["sr"][a:b])))
        r = {k: float(np.sqrt(np.mean(np.concatenate(v) ** 2))) for k, v in acc.items()}
        share = r["ufb"] ** 2 / max(r["u"] ** 2, 1e-30)
        print(f"{route[6:8]:6s} {fam:7s} {r['u']:8.5f} {r['ufb']:8.5f} {r['uff']:8.5f} {share:9.3f} "
              f"{r['sr']:10.4f} {r['sr']/max(r['u'],1e-9):10.1f}")
        out[route] = dict(fam=fam, **r, fb_share=share)
        del L
    json.dump(out, open(OUT / "L4_shake.json", "w"), indent=1)
    print()


if __name__ == "__main__":
    D = lag_decomp("15-22", 1024)
    dose(D, "15-22", 1024)
    shake_accounting()
