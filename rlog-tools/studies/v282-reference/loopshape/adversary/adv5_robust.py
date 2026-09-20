"""ADVERSARY 5 -- robustness of the crossover claim, and whether a single LTI L exists at all.

(a) per-ROUTE crossover and phase margin, so the family numbers are not one road;
(b) AMPLITUDE stratification of |L| -- an LTI loop has one L; if |L| moves with the size of the demand
    there is no single L to shape, and 'crossover / phase margin' stop being well defined;
(c) the ceiling any LINEAR remedy can reach, from the published incoherent fractions.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

FS = 100.0
NPS = 2048
FAM = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
       "0000006c--68c6e94b17": "TORQ", "0000006d--05e83bb04f": "TORQ", "0000006e--6ca3e014fd": "TORQ",
       "00000075--6c8687d5bd": "TORQ", "00000076--d0b7ea7e4d": "TORQ"}


def win(rk):
    """Every usable >=15 m/s window of NPS samples, with its own spectra."""
    S = V.load(rk)
    m = V.usable(S, 15.0)
    W = []
    for a, b in V.runs(m, S["t"], min_s=NPS / FS):
        Z = np.nan_to_num(S["setpoint"][a:b]); Y = np.nan_to_num(S["la_act"][a:b])
        p = np.nan_to_num(S["p"][a:b]); i_ = np.nan_to_num(S["i"][a:b]); ff = np.nan_to_num(S["f"][a:b])
        U = p + i_ + ff; E = Z - Y; PI = p + i_
        n = len(Z) // NPS * NPS
        for j in range(0, n, NPS):
            sl = slice(j, j + NPS)
            d = {}
            for k, (x, y) in dict(EPI=(E[sl], PI[sl]), FY=(ff[sl], Y[sl]), FU=(ff[sl], U[sl]),
                                  ZZ=(Z[sl], Z[sl])).items():
                xs, ys = x - x.mean(), y - y.mean()
                f, pxx = signal.welch(xs, FS, nperseg=NPS // 2, noverlap=NPS // 4)
                _, pxy = signal.csd(xs, ys, FS, nperseg=NPS // 2, noverlap=NPS // 4)
                d[k] = (pxx, pxy); d["f"] = f
            d["amp"] = float(np.std(Z[sl])); d["v"] = float(np.median(S["v"][a:b][sl]))
            W.append(d)
    del S
    return W


def combine(ws):
    if not ws:
        return None, None, None
    f = ws[0]["f"]
    S = {k: [np.zeros_like(ws[0][k][0]), np.zeros_like(ws[0][k][1])] for k in ["EPI", "FY", "FU", "ZZ"]}
    for w in ws:
        for k in S:
            S[k][0] = S[k][0] + w[k][0]; S[k][1] = S[k][1] + w[k][1]
    Cfb = S["EPI"][1] / S["EPI"][0]
    G = S["FY"][1] / S["FU"][1]
    return f, Cfb * G, S["ZZ"][0]


def cross(f, L, lo=0.05, hi=4.0):
    s = (f >= lo) & (f <= hi); ff, LL = f[s], L[s]
    mag = np.abs(LL); ph = np.degrees(np.unwrap(np.angle(LL)))
    k = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if not len(k):
        return np.nan, np.nan, float(mag.max())
    i = k[0]
    fc = float(np.interp(0, [np.log(mag[i + 1]), np.log(mag[i])], [ff[i + 1], ff[i]]))
    return fc, float(180 + np.interp(fc, ff, ph)), float(mag.max())


if __name__ == "__main__":
    print("=" * 112)
    print("(a)  PER-ROUTE crossover / phase margin, >=15 m/s.  (nw = 20.5 s windows)")
    print("=" * 112)
    print(f"  {'route':24s} {'fam':8s} {'nw':>3s} {'medV':>5s} | {'fc Hz':>7s} {'PM deg':>7s} {'max|L|':>7s} | "
          f"{'|L| .15-.30':>11s} {'|L| .30-.60':>11s}")
    keep = {}
    for rk, fam in FAM.items():
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        W = win(rk)
        if len(W) < 2:
            print(f"  {rk:24s} {fam:8s} {len(W):3d}  -- too few windows"); continue
        keep[rk] = (fam, W)
        f, L, Pzz = combine(W)
        fc, pm, mx = cross(f, L)
        b1 = (f >= 0.15) & (f < 0.30); b2 = (f >= 0.30) & (f < 0.60)
        print(f"  {rk:24s} {fam:8s} {len(W):3d} {np.median([w['v'] for w in W]):5.1f} | "
              f"{fc:7.3f} {pm:7.1f} {mx:7.2f} | "
              f"{abs(np.average(L[b1], weights=Pzz[b1])):11.3f} {abs(np.average(L[b2], weights=Pzz[b2])):11.3f}")

    print("\n" + "=" * 112)
    print("(b)  AMPLITUDE STRATIFICATION.  Windows split at the family median demand RMS.  An LTI loop has")
    print("     ONE L; a gap here means 'crossover' and 'phase margin' are not single-valued.")
    print("=" * 112)
    print(f"  {'fam':8s} {'stratum':10s} {'nw':>3s} {'ampRMS':>7s} | {'|L| .15-.30':>11s} {'<L':>7s} | "
          f"{'|L| .30-.60':>11s} {'<L':>7s} | {'fc Hz':>7s}")
    for fam in ["V282", "V282old", "TORQ"]:
        WS = [w for rk, (f_, W) in keep.items() if f_ == fam for w in W]
        if len(WS) < 6:
            print(f"  {fam:8s} only {len(WS)} windows -- not stratified"); continue
        med = float(np.median([w["amp"] for w in WS]))
        for lab, sel in [("low  dmd", [w for w in WS if w["amp"] <= med]),
                         ("high dmd", [w for w in WS if w["amp"] > med])]:
            f, L, Pzz = combine(sel)
            b1 = (f >= 0.15) & (f < 0.30); b2 = (f >= 0.30) & (f < 0.60)
            L1 = np.average(L[b1], weights=Pzz[b1]); L2 = np.average(L[b2], weights=Pzz[b2])
            fc, pm, mx = cross(f, L)
            print(f"  {fam:8s} {lab:10s} {len(sel):3d} {np.median([w['amp'] for w in sel]):7.4f} | "
                  f"{abs(L1):11.3f} {np.degrees(np.angle(L1)):7.1f} | {abs(L2):11.3f} "
                  f"{np.degrees(np.angle(L2)):7.1f} | {fc:7.3f}")

    print("\n" + "=" * 112)
    print("(c)  CEILING ON ANY LINEAR REMEDY, from the study's own exposure-weighted d(NRMSE^2) and its")
    print("     incoherent fractions.  A linear controller reshapes only the part of the error that is")
    print("     LINEARLY RELATED to the demand; the incoherent part is not a transfer-function defect.")
    print("=" * 112)
    tab = [("0.15-0.30", 0.266, 0.12), ("0.30-0.60", 0.822, 0.30), ("0.60-1.20", 1.955, 0.76)]
    tot = sum(t[1] for t in tab)
    coh_part = sum(t[1] * (1 - t[2]) for t in tab)
    for b, d, inc in tab:
        print(f"    {b:10s} d(NRMSE^2) {d:6.3f}  incoherent {inc*100:4.0f} %  -> reachable by LTI shaping "
              f"{d*(1-inc):6.3f}")
    print(f"    TOTAL {tot:.3f};  reachable by a PERFECT linear compensator {coh_part:.3f} = "
          f"{100*coh_part/tot:.1f} %  of the measured gap.")
    print("    (upper bound: assumes the compensator makes every coherent transfer exactly ideal and adds")
    print("     no incoherent motion of its own -- raising loop gain does the opposite.)")
