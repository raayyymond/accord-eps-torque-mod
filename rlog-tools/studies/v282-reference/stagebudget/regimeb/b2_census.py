# -*- coding: utf-8 -*-
"""REGIME B stage 2: is the 0.60-1.20 Hz large-demand gap an OPERATING-POINT artefact?

The surface stream's A3 stratum is OPEN-ENDED (p95 |model lateral accel| >= 1.0 m/s^2).  Its own printout
shows the two builds are NOT at the same operating point inside that stratum:
    8-15 m/s A3:  V282  sa95  23.2 deg, in-band demand RMS 0.0147   |H| 1.097
                  TORQ  sa95  78.2 deg, in-band demand RMS 0.0298   |H| 2.503
So before naming anything I have to know whether |H| 1.10 -> 2.50 survives a matched read.  This script
does no naming: it is a census and a matched re-read.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b2_census.py > B2-OUT.txt
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
SPDN = ["0-8", "8-15", "15-22", "22+"]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
BAND = (0.60, 1.20)
rng = np.random.default_rng(11)


def inband_rms(Cplx, f1=BAND[0], f2=BAND[1]):
    """Per-window band RMS.  Hann one-sided scale rms^2 = sum|C|^2 * 16/(3 N^2); verified in b1 self-test."""
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(Cplx[:, s]) ** 2).sum(1) * 16.0 / (3.0 * (W * 100.0) ** 2))


def cell(idx, a="X", b="Y", f1=BAND[0], f2=BAND[1]):
    s = (FR >= f1) & (FR < f2)
    A = D[a][idx][:, s]; B = D[b][idx][:, s]
    Paa = (np.abs(A) ** 2).sum(0); Pbb = (np.abs(B) ** 2).sum(0)
    Pab = (np.conj(A) * B).sum(0)
    w = Paa
    Hb = np.abs(Pab) / np.maximum(Paa, 1e-300)
    coh = np.clip(np.abs(Pab) ** 2 / np.maximum(Paa * Pbb, 1e-300), 1e-6, 1.0)
    H = float(np.average(Hb, weights=w))
    inc = float(np.average(np.maximum(Pbb - np.abs(Pab) ** 2 / np.maximum(Paa, 1e-300), 0) /
                           np.maximum(Paa, 1e-300), weights=w))
    fc = float(np.average(FR[s], weights=w))
    ph = float(np.angle((Pab * w).sum()))
    n_ind = max(2, int(np.ceil(len(idx) / 2)))
    nrm = 16.0 / (3.0 * (W * 100.0) ** 2 * len(idx))
    return dict(n=len(idx), H=H, coh=float(np.average(coh, weights=w)),
                coh_floor=1 - 0.05 ** (1 / max(n_ind - 1, 1)),
                Minc=float(np.sqrt(max(inc, 0))), lag_ms=-np.degrees(ph) / 360.0 / max(fc, 1e-9) * 1000,
                in_rms=float(np.sqrt(Paa.sum() * nrm)), out_rms=float(np.sqrt(Pbb.sum() * nrm)),
                coh_out=float(np.sqrt(max((np.abs(Pab) ** 2 / np.maximum(Paa, 1e-300)).sum() * nrm, 0))),
                inc_out=float(np.sqrt(max((Pbb - np.abs(Pab) ** 2 / np.maximum(Paa, 1e-300)).sum() * nrm, 0))))


def boot_H(idx, a="X", b="Y", nb=400):
    rts = sorted(set(D["route"][idx]))
    if len(rts) < 2:
        return float("nan"), float("nan")
    per = {r: idx[D["route"][idx] == r] for r in rts}
    v = []
    for _ in range(nb):
        kk = np.concatenate([per[r] for r in rng.choice(rts, len(rts))])
        v.append(cell(kk, a, b)["H"])
    return tuple(float(x) for x in np.percentile(v, [2.5, 97.5]))


def main():
    grp = D["group"]; cls = D["cls"]; sb = D["sbin"]; ap = D["am_p95"]; sap = D["sa_p95"]
    xr = inband_rms(D["X"])
    print("=" * 130)
    print("A. WHERE THE TWO BUILDS ACTUALLY SIT inside the open-ended A3 stratum (p95|model| >= 1.0), hands-off engaged")
    print("=" * 130)
    print(f"{'speed':7s} {'group':8s} {'n':>4s} {'p95|model| m/s2 (p25/50/75)':>30s} {'sa95 deg (p25/50/75)':>26s} "
          f"{'0.6-1.2Hz demand RMS (p25/50/75)':>34s}")
    for i in (1, 2):
        for g in ["V282", "V282old", "TORQ"]:
            mem = TORQ if g == "TORQ" else [g]
            k = np.flatnonzero((cls == "E") & (sb == i) & (ap >= 1.0) & np.isin(grp, mem))
            if len(k) == 0:
                continue
            q = lambda a: "/".join(f"{x:.3g}" for x in np.percentile(a[k], [25, 50, 75]))
            print(f"{SPDN[i]:7s} {g:8s} {len(k):4d} {q(ap):>30s} {q(sap):>26s} {q(xr):>34s}")
        print("")

    print("=" * 130)
    print("B. |H| in 0.60-1.20 Hz on MATCHED in-band demand RMS, common support only.")
    print("   Bands of in-band demand RMS chosen so both builds have >=6 windows; no extrapolation.")
    print("=" * 130)
    EDGES = [0.004, 0.008, 0.012, 0.018, 0.026, 0.040, 0.070, 0.150]
    for i in (1, 2, 3):
        print(f"\n  speed {SPDN[i]} m/s   (hands-off engaged, ALL amplitude strata; the stratum is replaced by this axis)")
        print(f"   {'demand RMS bin':>16s} {'group':8s} {'n':>4s} {'sa95':>6s} {'|H|X->Y':>8s} {'[95CI]':>13s} "
              f"{'coh':>5s} {'flr':>5s} {'Minc':>6s} {'lag ms':>7s} {'outRMS':>7s} {'cohOUT':>7s} {'incOUT':>7s}")
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            rows = []
            for g in ["V282", "TORQ"]:
                mem = TORQ if g == "TORQ" else [g]
                k = np.flatnonzero((cls == "E") & (sb == i) & (xr >= lo) & (xr < hi) & np.isin(grp, mem))
                rows.append((g, k))
            if min(len(k) for _, k in rows) < 6:
                continue
            for g, k in rows:
                c = cell(k)
                ci = boot_H(k)
                print(f"   {lo:.3f}-{hi:.3f}    {g:8s} {len(k):4d} {np.median(sap[k]):6.1f} {c['H']:8.3f} "
                      f"[{ci[0]:5.2f},{ci[1]:5.2f}] {c['coh']:5.2f} {c['coh_floor']:5.2f} {c['Minc']:6.3f} "
                      f"{c['lag_ms']:7.0f} {c['out_rms']:7.4f} {c['coh_out']:7.4f} {c['inc_out']:7.4f}")

    print("\n" + "=" * 130)
    print("C. SAME, matched on WHEEL ANGLE p95 instead (sa95) -- a second matching axis, different confound")
    print("=" * 130)
    AE = [0, 5, 12, 25, 50, 100, 400]
    for i in (1, 2):
        print(f"\n  speed {SPDN[i]} m/s")
        print(f"   {'sa95 deg bin':>16s} {'group':8s} {'n':>4s} {'dmdRMS':>7s} {'|H|X->Y':>8s} {'[95CI]':>13s} "
              f"{'coh':>5s} {'Minc':>6s} {'lag ms':>7s} {'outRMS':>7s} {'incOUT':>7s}")
        for lo, hi in zip(AE[:-1], AE[1:]):
            rows = []
            for g in ["V282", "TORQ"]:
                mem = TORQ if g == "TORQ" else [g]
                k = np.flatnonzero((cls == "E") & (sb == i) & (sap >= lo) & (sap < hi) & np.isin(grp, mem))
                rows.append((g, k))
            if min(len(k) for _, k in rows) < 6:
                continue
            for g, k in rows:
                c = cell(k); ci = boot_H(k)
                print(f"   {lo:3d}-{hi:3d} deg      {g:8s} {len(k):4d} {np.median(xr[k]):7.4f} {c['H']:8.3f} "
                      f"[{ci[0]:5.2f},{ci[1]:5.2f}] {c['coh']:5.2f} {c['Minc']:6.3f} {c['lag_ms']:7.0f} "
                      f"{c['out_rms']:7.4f} {c['inc_out']:7.4f}")

    print("\n" + "=" * 130)
    print("D. EXPOSURE of the matched cells: how much of the torque car's engaged time is in each demand-RMS bin")
    print("=" * 130)
    for i in (1, 2, 3):
        kt = np.flatnonzero((cls == "E") & (sb == i) & np.isin(grp, TORQ))
        tot = len(kt)
        if not tot:
            continue
        print(f"  speed {SPDN[i]:6s} n={tot:4d} windows: " + " ".join(
            f"{lo:.3f}-{hi:.3f}:{np.mean((xr[kt] >= lo) & (xr[kt] < hi))*100:4.1f}%"
            for lo, hi in zip(EDGES[:-1], EDGES[1:])))


if __name__ == "__main__":
    main()
