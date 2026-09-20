"""ADVERSARY 6 -- what a SteerKP dose can and cannot reach, from the SEPARATELY LOGGED P and I terms.

The fork's feedback compensator is   C_fb(s) = N(s) * [ (kp + lsf) + (ki/s)(1 + lsf/kp) ]
   (error_with_lsf = E*(1+lsf/kp); the Accord error NOTCH N(s) is applied to it; p = kp*that, i = ki*int(that))
so a SteerKP change scales the P part and the I part by DIFFERENT factors, and both are measurable
separately from the logged torqueState.p and .i.  That makes the dose arithmetic exact instead of assumed:
    C_P_new = C_P * (kp1 + lsf)/(kp0 + lsf)
    C_I_new = C_I * (1 + lsf/kp1)/(1 + lsf/kp0)
No claim is made here about how the car will FEEL.  What is reported is the loop gain the dose puts into
each band -- measurement plus algebra -- and the band where the logs cannot check it.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

FS = 100.0; NPS = 2048
TORQ = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
        "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
LOW_SPEED_X = [0, 10, 20, 30]; LOW_SPEED_Y = [12, 10.5, 8, 5]; MIN_SPEED = 1.0
KP0 = {r: 1.0 for r in ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                        "00000076--d0b7ea7e4d"]}
KP0.update({"00000075--6c8687d5bd": 0.85})
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.00), (2.00, 3.00)]
# the study's own exposure-weighted d(NRMSE^2) and incoherent fraction
GAP = {(0.15, 0.30): (0.266, 0.12), (0.30, 0.60): (0.822, 0.30), (0.60, 1.20): (1.955, 0.76)}


def gather(routes):
    acc = {}
    lsfs = []
    for rk in routes:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        S = V.load(rk)
        m = V.usable(S, 15.0)
        for a, b in V.runs(m, S["t"], min_s=NPS / FS):
            Z = np.nan_to_num(S["setpoint"][a:b]); Y = np.nan_to_num(S["la_act"][a:b])
            p = np.nan_to_num(S["p"][a:b]); i_ = np.nan_to_num(S["i"][a:b]); ff = np.nan_to_num(S["f"][a:b])
            v = S["v"][a:b]
            U = p + i_ + ff; E = Z - Y
            lsfs.append(float(np.median((np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2)))
            n = len(Z) // NPS * NPS
            for j in range(0, n, NPS):
                sl = slice(j, j + NPS)
                for k, (x, y) in dict(EP=(E[sl], p[sl]), EI=(E[sl], i_[sl]), FY=(ff[sl], Y[sl]),
                                      FU=(ff[sl], U[sl]), ZZ=(Z[sl], Z[sl])).items():
                    xs, ys = x - x.mean(), y - y.mean()
                    f, pxx = signal.welch(xs, FS, nperseg=NPS // 2, noverlap=NPS // 4)
                    _, pxy = signal.csd(xs, ys, FS, nperseg=NPS // 2, noverlap=NPS // 4)
                    d = acc.setdefault(k, [np.zeros_like(pxx), np.zeros_like(pxy)])
                    d[0] += pxx; d[1] += pxy
                acc["f"] = f
        del S
    return acc, float(np.median(lsfs))


def bandavg(f, H, W, a, b):
    s = (f >= a) & (f < b)
    return np.average(H[s], weights=W[s])


if __name__ == "__main__":
    A, lsf = gather(TORQ)
    f = A["f"]
    C_P = A["EP"][1] / A["EP"][0]
    C_I = A["EI"][1] / A["EI"][0]
    G = A["FY"][1] / A["FU"][1]
    W = A["ZZ"][0]
    kp0 = 0.97                       # power-weighted mean of the flown SteerKP over these five routes
    print(f"  flown SteerKP (mean over the 5 torque routes) = {kp0:.2f};  median low_speed_factor at >=15 m/s "
          f"= {lsf:.3f}")
    L0 = (C_P + C_I) * G
    print("\n  SANITY: measured |C_P| at 0.60-1.20 Hz (kp-dominated, notch nearly out of band) = "
          f"{abs(bandavg(f, C_P, W, 0.6, 1.2)):.3f};  fork arithmetic kp+lsf = {kp0+lsf:.3f}")

    print("\n" + "=" * 116)
    print("A.  THE DOSE CURVE.  SteerKP from its flown value to the toggle ceiling (platform Kp 0.6 x 5.0 = 3.0).")
    print("    'gain into band' = |L_new|/|L_old|.  'coh err x' = |S_new|/|S_old| = the factor the COHERENT")
    print("    tracking error is multiplied by -- measurement + loop algebra, not a claim about feel.")
    print("=" * 116)
    hdr = f"  {'SteerKP':>8s} |"
    for (a, b) in BANDS:
        hdr += f" {('%.2f-%.2f' % (a, b)):>11s}"
    print(hdr + f" | {'pred. gap closed':>16s}")
    print(f"  {'':>8s} |" + "".join(f" {'|L|  errx':>11s}" for _ in BANDS) + f" | {'of the +3.04':>16s}")
    for kp1 in [0.97, 1.5, 2.0, 2.5, 3.0]:
        sP = (kp1 + lsf) / (kp0 + lsf)
        sI = (1 + lsf / kp1) / (1 + lsf / kp0)
        L1 = (C_P * sP + C_I * sI) * G
        line = f"  {kp1:8.2f} |"
        closed = 0.0
        for (a, b) in BANDS:
            l0 = bandavg(f, L0, W, a, b); l1 = bandavg(f, L1, W, a, b)
            s0 = abs(bandavg(f, 1 / (1 + L0), W, a, b)); s1 = abs(bandavg(f, 1 / (1 + L1), W, a, b))
            line += f" {abs(l1):5.2f}{s1/s0:6.2f}"
            if (a, b) in GAP:
                d, inc = GAP[(a, b)]
                closed += d * (1 - inc) * (1 - (s1 / s0) ** 2)
        print(line + f" | {closed:6.3f} = {100*closed/3.043:5.1f} %")

    print("\n" + "=" * 116)
    print("B.  WHERE THE DOSE LANDS vs WHERE THE METRIC IS.  The P term carries the dose; the I term does not.")
    print("=" * 116)
    print(f"  {'band':12s} {'|C_P|':>7s} {'|C_I|':>7s} {'P share of C_fb':>16s} {'-> |L| x at SteerKP 3.0':>24s}")
    sP = (3.0 + lsf) / (kp0 + lsf); sI = (1 + lsf / 3.0) / (1 + lsf / kp0)
    for (a, b) in BANDS:
        cp = abs(bandavg(f, C_P, W, a, b)); ci = abs(bandavg(f, C_I, W, a, b))
        l0 = abs(bandavg(f, L0, W, a, b)); l1 = abs(bandavg(f, (C_P * sP + C_I * sI) * G, W, a, b))
        print(f"  {('%.2f-%.2f' % (a, b)):12s} {cp:7.3f} {ci:7.3f} {cp/(cp+ci):16.2f} {l1/l0:24.2f}")
    print(f"  (scale factors at SteerKP 3.0:  P x {sP:.2f},  I x {sI:.2f})")

    print("\n" + "=" * 116)
    print("C.  CAN THE LOGS CHECK THE BAND THE DOSE LOADS MOST?  Exogenous reference power and the")
    print("    coherence of the plant estimate, per band.")
    print("=" * 116)
    tot = float(np.sum(W[(f >= 0.05) & (f <= 4.5)]))
    Pff, Pfy = A["FY"][0], A["FY"][1]
    for (a, b) in BANDS + [(3.0, 4.5)]:
        s = (f >= a) & (f < b)
        share = 100 * float(np.sum(W[s])) / tot
        print(f"  {('%.2f-%.2f' % (a, b)):12s} reference power {share:7.3f} %   "
              f"{'IDENTIFIABLE' if share > 0.5 else 'NOT IDENTIFIABLE (excitation floor)'}")
