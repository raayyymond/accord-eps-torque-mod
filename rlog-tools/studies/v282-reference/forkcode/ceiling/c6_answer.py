# -*- coding: utf-8 -*-
"""c6 -- THE ANSWER: the joint frontier over (SteerKP, notch Q, k_d), tiered by what the logs can see.

TIERS (inherited from f7/f8 and kept, because the measurement limit is real):
  Tier A  crossover <= 0.50 Hz -- coh(Z,U) 0.79-0.91 there, the 55-75 ms delay is <= 12 deg.
  Tier B  crossover <= 1.20 Hz -- coh(Z,e) 0.19-0.42, delay 22 deg at 0.95 Hz.  REPORTED, NOT DEFENDED.
  Tier C  beyond that -- not offered.

COST CEILINGS on the CALIBRATED axis (c2): command shake in the brief's common units.
  r72 flew clean 19.4  |  rev 6.4 as flown 32.4  |  r71 LIMIT-CYCLED at 2.34 Hz 176.0

ROBUSTNESS, run on every headline row:
  (i)   each target route alone (6c SteerFriction 0.0 / 6d 0.212 -- both had the relay OFF because
        AccordFrictionHyst 0.015 > 0 gates it, torque.py: friction_torque = 0.0 if friction_hyst > 0)
  (ii)  V forced to 1.0 above 1 Hz (the out-of-loop wheel->yaw leg, the weakest measured object)
  (iii) the loop base taken as L_tot (PID + rate loop + observer) instead of L_pid
  (iv)  the V282 reference taken as 0.471 (my own re-derivation) instead of the brief's 0.442
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                        # noqa: E402
from f5_frontier import FLOWN                              # noqa: E402
from c3_ceiling import Ceiling, C_gen, fmt, HDR            # noqa: E402
from c4_split import Sub                                   # noqa: E402

np.seterr(divide="ignore", invalid="ignore")
OUTD = HERE / "out"
KD_LP = 2.0
KPS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0]
QS = [0.0, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
KDS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8]


class Pert(Ceiling):
    """Ceiling with the two modelled objects perturbable."""

    def __init__(self):
        super().__init__()
        S = json.load(open(FRONT / "out" / "f3_ident.json"))
        self.Ltot = np.empty_like(self.L0)
        for tag, lo, hi in (("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)):
            D = S[f"T64|{tag}"]
            self.Ltot[(self.v >= lo) & (self.v < hi)] = np.array(D["L_tot"][0]) + 1j * np.array(D["L_tot"][1])

    def alt(self, kp, laf, q, kd=0.0, mode="base", ref=0.442):
        C1 = C_gen(self.f, self.v, kp, laf, FLOWN["ki"], FLOWN["ki_hi"], q, kd=kd, kd_lp_hz=KD_LP)
        K = C1 / self.C0
        L0 = self.Ltot if mode == "ltot" else self.L0
        L1 = L0 * K
        rho = (1.0 + L0) / (1.0 + L1)
        Vv = self.V.copy()
        if mode == "vunit":
            Vv[:, self.f > 1.0] = 1.0
        E1 = self.E + Vv * self.D * (rho - 1.0)
        m = float(np.sum(np.abs(E1[:, self.b]) ** 2)) / self.px
        return (1.3512 - m) / (1.3512 - ref) * 100.0


def tier_of(r):
    wc = r["wc"]
    if np.isnan(wc) or wc <= 0.50:
        return "A"
    return "B" if wc <= 1.20 else "C"


if __name__ == "__main__":
    E = Pert()
    rows = []
    for kp, q, kd in itertools.product(KPS, QS, KDS):
        r = E.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)
        r.update(kp=kp, q=q, kd=kd, tier=tier_of(r))
        rows.append(r)
    json.dump([{k: v for k, v in r.items() if k != "bands"} for r in rows], open(OUTD / "c6_grid.json", "w"))
    print(f"joint grid {len(rows)} configs (SteerKP x AccordErrorNotchQ x k_d), SteerLatAccel held at 14")
    print()

    def best(ceil, tiers, extra=lambda r: True):
        ok = [r for r in rows if r["shake_common"] <= ceil and r["tier"] in tiers and extra(r)]
        return min(ok, key=lambda r: r["metric"]) if ok else None

    def cfg(r):
        return f"SteerKP {r['kp']:.1f}  NotchQ {r['q']:.2f}  k_d {r['kd']:.2f}"

    for tiers, lbl in (("A", "TIER A -- crossover <= 0.50 Hz.  DEFENSIBLE from the logs."),
                       ("AB", "TIER B -- crossover <= 1.20 Hz.  REPORTED, NOT DEFENDED.")):
        print("=" * 138)
        print(lbl)
        print(HDR + "   config")
        for ceil in (30.0, 32.4, 35.0, 37.5, 40.0, 45.0, 50.0, 60.0, 80.0):
            b = best(ceil, tiers)
            if b:
                print(fmt(f"shake <= {ceil:5.1f} common", b, cfg(b)))
        print("   ... and with k_d held at 0 (no new term, the k_d slot untouched):")
        for ceil in (32.4, 37.5, 45.0, 60.0):
            b = best(ceil, tiers, lambda r: r["kd"] == 0.0)
            if b:
                print("   " + fmt(f"shake <= {ceil:5.1f} kd=0", b, cfg(b)))
        print("   ... and with SteerKP held at its 3.00 TOGGLE CEILING (no constant change):")
        for ceil in (32.4, 37.5, 45.0, 60.0):
            b = best(ceil, tiers, lambda r: r["kp"] <= 3.0)
            if b:
                print("   " + fmt(f"shake <= {ceil:5.1f} KP<=3", b, cfg(b)))
        print()

    print("=" * 138)
    print("ROBUSTNESS of the headline rows")
    HEAD = [("as flown", 1.0, 1.00, 0.0), ("ARM-KP2 (toggle ceiling)", 3.0, 0.60, 0.0),
            ("A1  KP 3.0 Q 0.60 kd 0.20", 3.0, 0.60, 0.20),
            ("A2  KP 3.0 Q 0.60 kd 0.40", 3.0, 0.60, 0.40),
            ("A3  KP 5.0 Q 0.35 kd 0.20", 5.0, 0.35, 0.20),
            ("B1  KP 8.0 Q 0.20 kd 0.00", 8.0, 0.20, 0.0),
            ("B2  KP 8.0 Q 0.15 kd 0.40", 8.0, 0.15, 0.40),
            ("B3  KP 12  Q 0.15 kd 0.00", 12.0, 0.15, 0.0)]
    S6c, S6d = Sub(0), Sub(1)
    J6c = S6c.score(kp=1.0, laf=14.0, q=1.0)["metric"]
    J6d = S6d.score(kp=1.0, laf=14.0, q=1.0)["metric"]
    print(f"   per-route as-flown J: 6c {J6c:.4f}  6d {J6d:.4f}  (pooled 1.3512)")
    print(f"{'config':28s} {'tier':>4s} {'clos% base':>10s} {'6c only':>8s} {'6d only':>8s} "
          f"{'V=1>1Hz':>8s} {'L_tot':>7s} {'ref .471':>9s} {'shake':>6s} {'/r71':>6s}")
    for lbl, kp, q, kd in HEAD:
        r = E.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)
        a = E.alt(kp, 14.0, q, kd)
        c6 = S6c.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)["metric"]
        d6 = S6d.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)["metric"]
        print(f"{lbl:28s} {tier_of(r):>4s} {a:10.1f} {(J6c-c6)/(J6c-0.442)*100:8.1f} "
              f"{(J6d-d6)/(J6d-0.442)*100:8.1f} {E.alt(kp,14.0,q,kd,mode='vunit'):8.1f} "
              f"{E.alt(kp,14.0,q,kd,mode='ltot'):7.1f} {E.alt(kp,14.0,q,kd,ref=0.471):9.1f} "
              f"{r['shake_common']:6.1f} {r['k234_vs_r71']:6.3f}")
    print()
    print("   BANDS of the headline rows (0.15-0.30 / 0.30-0.60 / 0.60-1.20 / 1.20-2.40 Hz)")
    for lbl, kp, q, kd in HEAD:
        r = E.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)
        print(f"   {lbl:28s} " + " ".join(f"{b:6.3f}" for b in r["bands"]) + f"   total {r['metric']:.3f}")
    print()
    print("   V282 reference bands, for what 'good' looks like per band:")
    D = np.load(FRONT / "out" / "f1_0000006c--2bc842dbac.npz")
    f, X, Y, v = D["f"], D["X"], D["Y"], D["vmed"]
    s = v >= 15.0
    Ev = (X - Y)[s]
    px = float(np.sum(np.abs(X[s][:, (f >= 0.15) & (f <= 2.4)]) ** 2))
    bands = [float(np.sum(np.abs(Ev[:, (f >= a) & (f < b)]) ** 2)) / px for a, b in
             ((0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40))]
    print("   " + f"{'V282 route 6c (349 win)':28s} " + " ".join(f"{b:6.3f}" for b in bands)
          + f"   total {sum(bands):.3f}")
