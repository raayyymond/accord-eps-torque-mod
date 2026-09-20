# -*- coding: utf-8 -*-
"""d8 -- IS THE REFERENCE LEVER REAL, OR IS IT THE 102 ms?

THE TRAP.  Y is logged 102 ms late (d6, two estimators, 11 routes, control passed).  The optimal
setpoint prefilter will therefore want to ADVANCE the reference by ~102 ms, because that makes the
LOGGED error smaller while making the CAR 102 ms early.  Any reference-class number that survives
only at tau_i = 0 is an artefact.

SO EVERY NUMBER HERE IS COMPUTED TWICE:
   raw      : against E = X - Y                (the metric exactly as defined)
   corrected: against Ec = X - Y e^{+j w tau_i} (the metric with the instrument lag taken out)
A lever is real only if it survives the corrected column.

THE LADDER.  The free per-bin optimum is an upper bound on a class the fork cannot fully build.
Four nested sub-classes, each one fork-implementable:
   G1  one real gain on the setpoint                      (1 number)
   G2  gain + pure lead/lag                               (2 numbers; the fork already has a plan
                                                           buffer, so a LEAD is realizable)
   G3  gain + lead + one first-order lag                  (3 numbers)
   G4  the free per-bin optimum                           (upper bound, possibly non-causal)

SHAKE COST of each, measured: the command's 1.8-3.5 Hz RMS ratio, through the measured Z -> U path.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import optimize

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
SHAKE = (1.8, 3.5)
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
TAU_I = 0.102
JREF, JFLOWN = 0.442, 1.3512


def gather(routes):
    cols = {k: [] for k in ("X", "Y", "Z", "M", "U")}
    f = None
    for r in routes:
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        for k in cols:
            cols[k].append(D[k])
        del D
    return dict(f=f, **{k: np.concatenate(v) for k, v in cols.items()})


def screened_V(fgrid):
    D = np.load(OUT / "d3_broadV.npz")
    f, H1 = D["f"], D["H1"]
    return np.interp(fgrid, f, np.abs(H1)) * np.exp(1j * np.interp(fgrid, f, np.unwrap(np.angle(H1))))


class Ref:
    def __init__(self, routes, corrected):
        W = gather(routes)
        self.f = f = W["f"]
        self.sel = (f >= BAND[0]) & (f <= BAND[1])
        self.shk = (f >= SHAKE[0]) & (f <= SHAKE[1])
        ph = np.exp(2j * np.pi * f * TAU_I)[None, :]
        Vf = screened_V(f)
        self.V = Vf[None, :] * (ph if not corrected else 1.0)
        self.X, self.Z, self.M, self.U = W["X"], W["Z"], W["M"], W["U"]
        self.Y = W["Y"] * (ph if corrected else 1.0)
        self.E = self.X - self.Y
        self.px = float(np.sum(np.abs(self.X[:, self.sel]) ** 2))
        self.Hzm = (np.sum(np.conj(self.Z) * self.M, 0) /
                    np.sum(np.abs(self.Z) ** 2, 0))[None, :]
        self.Hzu = (np.sum(np.conj(self.Z) * self.U, 0) /
                    np.sum(np.abs(self.Z) ** 2, 0))[None, :]
        self.G = self.V * self.Hzm * self.Z
        self.pu = float(np.sum(np.abs(self.U[:, self.shk]) ** 2))
        self.J0 = float(np.sum(np.abs(self.E[:, self.sel]) ** 2)) / self.px

    def apply(self, Wf):
        """Wf is (nf,) -- the prefilter.  Returns J and the shake-band command ratio."""
        d = (Wf - 1.0)[None, :]
        E1 = self.E - d * self.G
        U1 = self.U + d * self.Hzu * self.Z
        return (float(np.sum(np.abs(E1[:, self.sel]) ** 2)) / self.px,
                float(np.sqrt(np.sum(np.abs(U1[:, self.shk]) ** 2) / self.pu)))

    def free_optimum(self):
        k = np.sum(np.conj(self.G) * self.E, 0) / np.maximum(np.sum(np.abs(self.G) ** 2, 0), 1e-300)
        return 1.0 + k

    def fit(self, form, x0, bounds):
        def cost(p):
            return self.apply(form(self.f, p))[0]
        r = optimize.minimize(cost, x0, method="Nelder-Mead",
                              options=dict(maxiter=4000, xatol=1e-5, fatol=1e-9))
        return r.x, form(self.f, r.x)


def F1(f, p):
    return np.full(len(f), float(p[0]))


def F2(f, p):
    return p[0] * np.exp(2j * np.pi * f * p[1])


def F3(f, p):
    return p[0] * np.exp(2j * np.pi * f * p[1]) / (1.0 + 2j * np.pi * f * max(p[2], 0.0))


def report(lab, corrected):
    R = Ref(T64 if lab == "T64" else V282R, corrected)
    tag = "instrument-CORRECTED" if corrected else "raw (metric as defined)"
    print(f"\n  {lab}, {tag}:  J as flown {R.J0:.4f}")
    rows = []
    for nm, form, x0, bd in (("G1 gain only            ", F1, [1.0], None),
                             ("G2 gain + lead          ", F2, [1.0, 0.1], None),
                             ("G3 gain + lead + lag    ", F3, [1.0, 0.1, 0.05], None)):
        p, Wf = R.fit(form, x0, bd)
        J, sh = R.apply(Wf)
        rows.append((nm, J, sh, p))
    Wf = R.free_optimum()
    J, sh = R.apply(Wf)
    rows.append(("G4 free per-bin optimum ", J, sh, None))
    print(f"    {'class':26s} {'J':>7s} {'closure':>8s} {'cmd shake x':>12s}  params")
    for nm, J, sh, p in rows:
        ps = "" if p is None else ("gain %.3f" % p[0]) + ("" if len(p) < 2 else "  lead %+.0f ms" % (p[1] * 1000)) \
            + ("" if len(p) < 3 else "  lag %.0f ms" % (max(p[2], 0) * 1000))
        print(f"    {nm:26s} {J:7.4f} {(JFLOWN-J)/(JFLOWN-JREF)*100:7.1f}% {sh:12.3f}  {ps}")
    # the free optimum's shape
    j = [int(np.argmin(np.abs(R.f - q))) for q in (0.20, 0.29, 0.39, 0.59, 0.98, 1.46, 1.95)]
    print(f"    free optimum |W|  " + " ".join(f"{R.f[i]:.2f}:{abs(Wf[i]):5.2f}" for i in j))
    print(f"    free optimum argW " + " ".join(f"{R.f[i]:.2f}:{np.degrees(np.angle(Wf[i])):+5.0f}" for i in j))
    gd = np.degrees(np.angle(Wf)) / (-360.0 * np.maximum(R.f, 1e-6)) * 1000
    s = (R.f >= 0.15) & (R.f <= 0.6)
    w = np.sum(np.abs(R.Z[:, s]) ** 2, 0)
    print(f"    equivalent LEAD of the free optimum over 0.15-0.60 Hz: "
          f"{-float(np.average(gd[s], weights=w)):.0f} ms")
    return rows, Wf


if __name__ == "__main__":
    print("=" * 108)
    print("THE REFERENCE-CLASS LADDER, raw and instrument-corrected")
    out = {}
    for corrected in (False, True):
        for lab in ("T64", "V282"):
            rows, Wf = report(lab, corrected)
            out[f"{lab}|{'corr' if corrected else 'raw'}"] = [
                dict(cls=nm.strip(), J=J, shake=sh, p=(None if p is None else list(map(float, p))))
                for nm, J, sh, p in rows]
    print("\n" + "=" * 108)
    print("READ THIS BEFORE BELIEVING THE REFERENCE LEVER:")
    a = out["T64|raw"][-1]["J"]
    b = out["T64|corr"][-1]["J"]
    print(f"   free optimum, raw {a:.4f}  vs instrument-corrected {b:.4f}")
    print("   If the two are close, the lever is about the SHAPE of the setpoint chain and survives.")
    print("   If the corrected one collapses toward J_inf, the lever was buying back the 102 ms.")
    json.dump(out, open(OUT / "d8.json", "w"), indent=1, default=float)
    print("\nwrote out/d8.json")
