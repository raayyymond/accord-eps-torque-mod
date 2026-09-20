# -*- coding: utf-8 -*-
"""f5 -- THE JOINT MAP AND THE FRONTIER.

For every reachable combination of the loop parameters, compute on the MEASURED transfers:
  * the goal metric (and its band breakdown, ONE denominator),
  * the 1.8-3.5 Hz COMMAND shake ratio (exact re-synthesis from the logged p/i/f, closed-loop
    corrected by the same sensitivity ratio the metric uses),
  * shake-band |L| on the axis the FLOWN anchors sit on (r71 0.46 limit-cycled, r72 0.19 fine),
  * |S| per band, Ms, crossover and phase margin.

ALGEBRA (all of it exact given the measured objects; the ONE modelled step is named):
    L_old = P * C_old,  L_new = P * C_new           P measured (IV), C analytic from the fork source
    rho   = (1+L_old) / (1+L_new)                   the sensitivity ratio
    D_new = rho * D          <-- THE ONE MODELLED STEP: the loop error scales by rho because the
                                 exogenous drivers of D are assumed unchanged
    E_new = E + V * D * (rho - 1)                   from X - Y = A + V*D with A := E - V*D
    U_new = UFF + UFB * (C_new/C_old) * rho

EVIDENCE: E, D, X, UFF, UFB, V, P are all measured.  BELIEF: that the car and the exogenous
drivers are unchanged at the new gain, and that nothing nonlinear (friction, the Honda rate
limiter) responds to the rougher command.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
SHAKE_F = (1.95, 2.54, 3.03)      # the three report frequencies the flown anchors were read at
SHAKE_BAND = (1.8, 3.5)
TARGET = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]     # rev 6.4 as flown = T64
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, ki_hi=0.0, q=1.0)
V282_METRIC = 0.442               # the brief's reference value; my own re-derivation is 0.471


def load_target():
    Xs, Ys, Zs, Ms, UFB, UFF, U, SR, vm = [], [], [], [], [], [], [], [], []
    for r in TARGET:
        D = np.load(OUT / f"f1_{r}.npz")
        for a, k in ((Xs, "X"), (Ys, "Y"), (Zs, "Z"), (Ms, "M"), (UFB, "UFB"), (UFF, "UFF"), (U, "U"), (SR, "SR")):
            a.append(D[k])
        vm.append(D["vmed"])
        f = D["f"]
        laf = float(D["laf"])
    cat = lambda a: np.concatenate(a, axis=0)
    return dict(f=f, laf=laf, v=cat(vm), X=cat(Xs), Y=cat(Ys), Z=cat(Zs), M=cat(Ms),
                UFB=cat(UFB), UFF=cat(UFF), U=cat(U), SR=cat(SR))


def plant_per_window(f, v):
    """P(f) for each window, taken from its own speed bin's IV identification (f3)."""
    S = json.load(open(OUT / "f3_ident.json"))
    out = np.empty((len(v), len(f)), complex)
    Vleg = np.empty((len(v), len(f)), complex)
    for tag, lo, hi in (("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)):
        D = S[f"T64|{tag}"]
        P = np.array(D["P"][0]) + 1j * np.array(D["P"][1])
        Vh = np.array(D["V_h1"][0]) + 1j * np.array(D["V_h1"][1])
        sel = (v >= lo) & (v < hi)
        out[sel] = P
        Vleg[sel] = Vh
    return out, Vleg


def C_of(f, v, kp, laf, ki, ki_hi, q):
    """(nwin, nf) analytic feedback transfer, per window, with that window's lsf / ki(v) / notch centre."""
    lsf = LP.low_speed_factor(v)[:, None]
    kie = LP.ki_of(v, ki, ki_hi)[:, None]
    z = np.exp(-2j * np.pi * f[None, :] * LP.DT)
    pi = kp + kie * LP.DT / (1.0 - z)
    C = -pi * (1.0 + lsf / max(kp, 1e-3)) / laf
    if q is not None and q > 0:
        f0 = LP.mode_hz(v)
        k = np.tan(np.pi * np.minimum(f0, 0.45 / LP.DT) * LP.DT)[:, None]
        norm = 1.0 / (1.0 + k / q + k * k)
        b0 = (1.0 + k * k) * norm
        b1 = 2.0 * (k * k - 1.0) * norm
        a2 = (1.0 - k / q + k * k) * norm
        C = C * (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)
    return C


class Engine:
    def __init__(self):
        W = load_target()
        self.f = W["f"]
        self.v = W["v"]
        self.laf0 = W["laf"]
        self.X, self.Y, self.Z, self.M = W["X"], W["Y"], W["Z"], W["M"]
        self.UFB, self.UFF, self.U, self.SR = W["UFB"], W["UFF"], W["U"], W["SR"]
        self.E = self.X - self.Y
        self.D = self.Z - self.M
        self.P, self.V = plant_per_window(self.f, self.v)
        f = self.f
        self.b = (f >= BAND[0]) & (f <= BAND[1])
        self.sb = [(f >= a) & (f < c) for a, c in SUB]
        self.shk = (f >= SHAKE_BAND[0]) & (f <= SHAKE_BAND[1])
        self.shj = [int(np.argmin(np.abs(f - q))) for q in SHAKE_F]
        self.px = float(np.sum(np.abs(self.X[:, self.b]) ** 2))
        self.pu_shk = float(np.sum(np.abs(self.U[:, self.shk]) ** 2))
        self.C0 = C_of(f, self.v, FLOWN["kp"], self.laf0, FLOWN["ki"], FLOWN["ki_hi"], FLOWN["q"])
        self.L0 = self.P * self.C0

    def run(self, kp, laf, ki, ki_hi, q):
        C1 = C_of(self.f, self.v, kp, laf, ki, ki_hi, q)
        K = C1 / self.C0
        L1 = self.L0 * K
        rho = (1.0 + self.L0) / (1.0 + L1)
        E1 = self.E + self.V * self.D * (rho - 1.0)
        U1 = self.UFF + self.UFB * K * rho
        m = float(np.sum(np.abs(E1[:, self.b]) ** 2)) / self.px
        bands = [float(np.sum(np.abs(E1[:, s]) ** 2)) / self.px for s in self.sb]
        shake_cmd = float(np.sqrt(np.sum(np.abs(U1[:, self.shk]) ** 2) / self.pu_shk))
        shake_L = float(np.mean(np.abs(L1[:, self.shj])))
        S1 = np.abs(1.0 / (1.0 + L1))
        ms_sel = (self.f >= 0.10) & (self.f <= 2.5)
        Ms = float(np.max(np.mean(S1[:, ms_sel], axis=0)))
        Smean = [float(np.mean(S1[:, s])) for s in self.sb]
        # crossover and phase margin on the exposure-averaged loop
        Lm = np.mean(L1, axis=0)
        sel = (self.f >= 0.10) & (self.f <= 3.5)
        ff, LL = self.f[sel], Lm[sel]
        mag = np.abs(LL)
        wc = pm = np.nan
        x = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
        if len(x):
            k0 = x[0]
            w = np.log(mag[k0]) / (np.log(mag[k0]) - np.log(mag[k0 + 1]))
            wc = float(ff[k0] + w * (ff[k0 + 1] - ff[k0]))
            ph = np.unwrap(np.angle(LL))
            pm = float(180.0 + np.degrees(np.angle(np.exp(1j * np.interp(wc, ff, ph)))))
        return dict(kp=kp, laf=laf, ki=ki, ki_hi=ki_hi, q=q, metric=m, bands=bands,
                    shake_cmd=shake_cmd, shake_L=shake_L, Ms=Ms, Smean=Smean, wc=wc, pm=pm,
                    closure=(1.351 - m) / (1.351 - V282_METRIC))


if __name__ == "__main__":
    eng = Engine()
    base = eng.run(**FLOWN)
    print("AS FLOWN (positive control: metric must reproduce 1.351, shake_cmd 1.000, shake_L ~0.105)")
    print(f"  metric {base['metric']:.4f}  bands {['%.3f' % x for x in base['bands']]}  "
          f"shake_cmd {base['shake_cmd']:.3f}  shake_L {base['shake_L']:.3f}  Ms {base['Ms']:.3f}  wc {base['wc']}")
    print()
    KPS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]
    KIH = [0.0, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]
    QS = [0.0, 0.25, 0.35, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0]
    LAFS = [14.0]
    rows = []
    for kp, kih, q, laf in itertools.product(KPS, KIH, QS, LAFS):
        rows.append(eng.run(kp, laf, FLOWN["ki"], kih, q))
    json.dump(rows, open(OUT / "f5_grid.json", "w"))
    print(f"grid: {len(rows)} configs -> f5_grid.json")

    # the frontier: max closure at each shake_L ceiling
    print()
    print("FRONTIER on shake-band |L| (anchors: today 0.105, r72 0.19 flown clean, r71 0.46 limit-cycled)")
    print(f"{'|L| ceil':>9s} {'best metric':>11s} {'closure':>8s} {'shake_cmd':>10s} {'|L|':>6s} "
          f"{'Ms':>5s} {'wc Hz':>6s} {'PM':>5s}   config")
    for ceil in (0.11, 0.13, 0.15, 0.17, 0.19, 0.22, 0.25, 0.30, 0.35, 0.46):
        ok = [r for r in rows if r["shake_L"] <= ceil]
        if not ok:
            continue
        b = min(ok, key=lambda r: r["metric"])
        print(f"{ceil:9.2f} {b['metric']:11.4f} {b['closure']*100:7.1f}% {b['shake_cmd']:10.3f} "
              f"{b['shake_L']:6.3f} {b['Ms']:5.2f} {b['wc']:6.3f} {b['pm']:5.0f}   "
              f"KP {b['kp']:.2f} KiHigh {b['ki_hi']:.1f} Q {b['q']:.2f}")
    print()
    print("FRONTIER on the COMMAND shake ratio (the felt quantity; 1.00 = as flown)")
    print(f"{'shake x':>8s} {'best metric':>11s} {'closure':>8s} {'|L|':>6s} {'Ms':>5s} {'wc Hz':>6s} {'PM':>5s}   config")
    for ceil in (1.00, 1.02, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.40, 1.60):
        ok = [r for r in rows if r["shake_cmd"] <= ceil]
        if not ok:
            continue
        b = min(ok, key=lambda r: r["metric"])
        print(f"{ceil:8.2f} {b['metric']:11.4f} {b['closure']*100:7.1f}% {b['shake_L']:6.3f} {b['Ms']:5.2f} "
              f"{b['wc']:6.3f} {b['pm']:5.0f}   KP {b['kp']:.2f} KiHigh {b['ki_hi']:.1f} Q {b['q']:.2f}")
