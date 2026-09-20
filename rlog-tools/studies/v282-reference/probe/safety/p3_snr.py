# -*- coding: utf-8 -*-
"""p3 -- the SMALLEST amplitude that IDENTIFIES, against the LARGEST that is quiet.

Both sides are computed at the same node and on the same window set, so they can be put
side by side, which is the question the brief asks.

IDENTIFY.  A probe injected at the error sum puts  |S|*A  into the error, |C/(1+L)|*A into the
command and |T|*A into the measurement.  The ordinary-coherence an estimator would then see at that
line is  g2 = Ppr / (Ppr + Pamb)  with Ppr the probe-driven power at that line and Pamb the power
already there.  Solve for A at a target g2:

        A(f) = sqrt( g2/(1-g2) * Pamb(f) * df_line ) / |H_inject->that signal|

  Pamb is the MEASURED one-sided PSD on the metric's own windows.  df_line is the resolution
  bandwidth of ONE probe line: a probe that puts all of its power at discrete frequencies is
  compared against the ambient power in one analysis bin, not against the whole band.

  The binding channel is whichever of (error, command, measurement) needs the biggest A.

QUIET.  From p2: the same A converted to wheel angle, steering rate, lateral accel, yaw rate,
compared against the ambient band-RMS of those same signals on V282 (the build that was NOT
called shaky) and on rev 6.4 (the build that WAS).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS = 100.0, 1024
BINS = [("15", 13.0, 18.0), ("22", 18.0, 25.0), ("28", 25.0, 99.0)]
BAND = (0.6, 2.0)
KFIT = (0.2, 1.0)
W = np.hanning(NPS + 1)[:NPS]
PSD_SCALE = 2.0 / (FS * np.sum(W ** 2))
BURST_S = 20.0                    # the brief's "15-30 s of usable data per episode"
DF_LINE = 1.0 / BURST_S           # resolution bandwidth of one probe line in one burst
G2 = 0.80                         # target ordinary coherence at a probe line
CONFIGS = [("rev6.4 as flown", 1.0, 14.0, 0.3, 0.0, 1.00),
           ("ARM-KP3", 3.0, 14.0, 0.6, 0.0, 0.30),
           ("TierB kp8  Q.20", 8.0, 14.0, 0.6, 0.0, 0.20)]


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def stack(routes, vlo, vhi):
    cols, vm = None, []
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= vlo) & (D["vmed"] < vhi)
        if sel.any():
            if cols is None:
                cols = {k: [] for k in ("Z", "M", "Y", "U", "SR")}
                f = D["f"]
            for k in cols:
                cols[k].append(D[k][sel])
            vm.append(D["vmed"][sel])
        D.close()
    if cols is None:
        return None
    return dict(f=f, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]

    res = {}
    for fam in ("ALL_T64", "V282"):
        for bn, lo, hi in BINS:
            Wd = stack(fams[fam], lo, hi)
            if Wd is None or len(Wd["vmed"]) < 4:
                continue
            f = Wd["f"]
            jw = 2j * np.pi * np.maximum(f, 1e-9)
            Z, M, Y, U, SR = Wd["Z"], Wd["M"], Wd["Y"], Wd["U"], Wd["SR"]
            E = Z - M
            SRi = SR / jw[None, :]
            fit = (f >= KFIT[0]) & (f <= KFIT[1])
            k_map = abs(np.sum(np.conj(SRi[:, fit]) * M[:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2))
            Suu = xs(U, U).real
            res[f"{fam}|{bn}"] = dict(
                f=f, n=len(Wd["vmed"]), v=float(np.median(Wd["vmed"])), k_map=k_map,
                P=xs(U, M) / np.maximum(Suu, 1e-300),
                V=xs(M, Y) / np.maximum(xs(M, M).real, 1e-300),
                pE=xs(E, E).real * PSD_SCALE, pU=Suu * PSD_SCALE, pM=xs(M, M).real * PSD_SCALE,
                pA=xs(SRi, SRi).real * PSD_SCALE, pSR=xs(SR, SR).real * PSD_SCALE,
                pY=xs(Y, Y).real * PSD_SCALE, pZ=xs(Z, Z).real * PSD_SCALE)

    f = res["ALL_T64|22"]["f"]
    band = (f >= BAND[0]) & (f < BAND[1])
    df = f[1] - f[0]
    kfac = np.sqrt(G2 / (1.0 - G2) * DF_LINE)

    print("=" * 120)
    print(f"REQUIRED PROBE AMPLITUDE per line for coherence {G2:.2f} in a {BURST_S:.0f} s burst "
          f"(line bandwidth {DF_LINE:.3f} Hz)")
    print("A_line is the RMS of ONE probe sinusoid, in m/s^2 at the error sum.")
    for label, kp, laf, ki, ki_hi, q in CONFIGS:
        for bn, _, _ in BINS:
            key = f"ALL_T64|{bn}"
            if key not in res:
                continue
            R = res[key]
            v = R["v"]
            lsf = float(LP.low_speed_factor(v))
            C = LP.c_fb_analytic(f, kp, float(LP.ki_of(v, ki, ki_hi)), laf, lsf,
                                 notch_f0=float(LP.mode_hz(v)), q=q)
            L = R["P"] * C
            S = 1.0 / (1.0 + L)
            T = L / (1.0 + L)
            HU = np.abs(C * S)
            HM = np.abs(T)
            HE = np.abs(S)
            print(f"\n  --- {label:16s} v={v:4.1f} m/s  n={R['n']} ---")
            print(f"  {'f':>5s} | {'A_err':>7s} {'A_cmd':>7s} {'A_meas':>7s} {'A_REQ':>7s} | "
                  f"{'dAng':>6s} {'dRate':>6s} {'dY':>6s} {'dYaw':>6s} | "
                  f"{'ambE':>7s} {'ambU':>7s} {'ambM':>7s}   binds")
            print(f"  {'Hz':>5s} | {'m/s2':>7s} {'m/s2':>7s} {'m/s2':>7s} {'m/s2':>7s} | "
                  f"{'deg':>6s} {'d/s':>6s} {'m/s2':>6s} {'d/s':>6s} | "
                  f"{'/rtHz':>7s} {'/rtHz':>7s} {'/rtHz':>7s}")
            rows = []
            for i in np.where(band)[0]:
                aE = kfac * np.sqrt(R["pE"][i]) / max(HE[i], 1e-9)
                aU = kfac * np.sqrt(R["pU"][i]) / max(HU[i], 1e-9)
                aM = kfac * np.sqrt(R["pM"][i]) / max(HM[i], 1e-9)
                A = max(aE, aU, aM)
                which = ["err", "cmd", "meas"][int(np.argmax([aE, aU, aM]))]
                dAng = A * HM[i] / R["k_map"]
                dRate = 2 * np.pi * f[i] * dAng
                dY = A * abs(R["V"][i]) * HM[i]
                print(f"  {f[i]:5.2f} | {aE:7.4f} {aU:7.4f} {aM:7.4f} {A:7.4f} | "
                      f"{dAng:6.3f} {dRate:6.3f} {dY:6.4f} {np.degrees(dY/v):6.3f} | "
                      f"{np.sqrt(R['pE'][i]):7.4f} {np.sqrt(R['pU'][i]):7.5f} "
                      f"{np.sqrt(R['pM'][i]):7.4f}   {which}")
                rows.append(dict(f=float(f[i]), A=float(A), which=which, dAng=float(dAng),
                                 dRate=float(dRate), dY=float(dY), dYaw=float(np.degrees(dY / v)),
                                 L=float(abs(L[i])), T=float(HM[i]), S=float(HE[i]),
                                 dU=float(A * HU[i])))
            res.setdefault("REQ", {})[f"{label}|{bn}"] = rows

    print()
    print("=" * 120)
    print("EFFICIENCY OF THE INJECTION POINT: error signal delivered per unit of MOTION caused = |S|/|T| = 1/|L|")
    for bn, _, _ in BINS:
        key = f"ALL_T64|{bn}"
        if key not in res:
            continue
        R = res[key]
        v = R["v"]
        C = LP.c_fb_analytic(f, 1.0, 0.3, 14.0, float(LP.low_speed_factor(v)),
                             notch_f0=float(LP.mode_hz(v)), q=1.0)
        L = np.abs(R["P"] * C)
        print(f"  v={v:4.1f}  1/|L| over {BAND[0]}-{BAND[1]} Hz: "
              f"median {np.median(1/L[band]):6.1f}  min {np.min(1/L[band]):5.1f}  max {np.max(1/L[band]):6.1f}")

    print()
    print("=" * 120)
    print("THE RULER: ambient band-RMS 0.6-2.0 Hz on the metric windows (what is already there)")
    print(f"{'set':14s} {'n':>4s} {'v':>5s} {'angle':>8s} {'rate':>8s} {'latacc':>8s} {'yaw d/s':>8s}"
          f" {'cmd':>8s} {'err':>8s}")
    for key in sorted(k for k in res if "|" in k):
        R = res[key]
        v = R["v"]
        g = lambda p: float(np.sqrt(np.sum(R[p][band]) * df))
        print(f"{key:14s} {R['n']:4d} {v:5.1f} {g('pA'):8.4f} {g('pSR'):8.4f} {g('pY'):8.4f}"
              f" {np.degrees(g('pY')/v):8.4f} {g('pU'):8.5f} {g('pE'):8.4f}")

    json.dump({k: v for k, v in res.items() if k == "REQ"}, open(HERE / "p3_out.json", "w"), indent=1)
    print("\nwrote p3_out.json")


if __name__ == "__main__":
    main()
