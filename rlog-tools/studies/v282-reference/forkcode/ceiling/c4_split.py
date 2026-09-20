# -*- coding: utf-8 -*-
"""c4 -- THE CONFOUND IN THE TARGET, AND WHETHER THE RANKING SURVIVES IT.

hsurface/surface/params_all.json, read from each route's OWN initData:
    0000006c--68c6e94b17   SteerFriction 0.0
    0000006d--05e83bb04f   SteerFriction 0.2120497077703476     <-- the stock back-fill bug
Both are pooled as "rev 6.4 as flown".  get_friction (opendbc/car/lateral.py:190) is a saturating
ramp on error_with_lsf, added to ff:
    d(output_torque)/d(error) = friction * latAccelFactor / friction_threshold / latAccelFactor
                              = friction / friction_threshold
against the P path's kp / latAccelFactor.  At friction 0.212, threshold ~0.3, LAF 14 that is an
extra feedback gain of ~0.71 torque per unit error versus P's 1.0/14 = 0.071 -- TEN TIMES Kp, and
it lands in `f`, i.e. in what the engine calls UFF and treats as EXOGENOUS.

So this script (a) MEASURES the extra path per route, (b) re-runs the SteerKP sweep on each route
alone, and (c) says whether the answer to "how far past 33 %" depends on the confound.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                    # noqa: E402
from f5_frontier import Engine, FLOWN                  # noqa: E402
from c3_ceiling import Ceiling, C_gen, fmt, HDR        # noqa: E402

np.seterr(divide="ignore", invalid="ignore")
OUT = FRONT / "out"
R = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
FRIC = {R[0]: 0.0, R[1]: 0.2120497077703476}


def iv_paths(route):
    """IV estimates, instrument Z: raw error -> UFB (the PID path) and raw error -> UFF."""
    D = np.load(OUT / f"f1_{route}.npz")
    f, Z, M, UFB, UFF = D["f"], D["Z"], D["M"], D["UFB"], D["UFF"]
    E = Z - M
    xs = lambda A, B: np.mean(np.conj(A) * B, axis=0)
    Cfb = xs(Z, UFB) / xs(Z, E)
    Cff = xs(Z, UFF) / xs(Z, E)
    v = float(np.median(D["vmed"]))
    lsf = float(LP.low_speed_factor(v))
    Cana = LP.c_fb_analytic(f, 1.0, 0.3, float(D["laf"]), lsf, float(LP.mode_hz(v)), 1.0)
    del D
    return f, Cfb, Cff, Cana, v


class Sub(Ceiling):
    """The same engine restricted to ONE route's windows."""

    def __init__(self, keep):
        super().__init__()
        n0 = np.load(OUT / f"f1_{R[0]}.npz")["vmed"].shape[0]
        sel = np.zeros(len(self.v), bool)
        sel[:n0] = (keep == 0)
        sel[n0:] = (keep == 1)
        for a in ("v", "X", "Y", "Z", "M", "UFB", "UFF", "U", "SR", "E", "D", "P", "V", "C0", "L0"):
            setattr(self, a, getattr(self, a)[sel])
        self.px = float(np.sum(np.abs(self.X[:, self.b]) ** 2))
        self.pu_shk = float(np.sum(np.abs(self.U[:, self.shk]) ** 2))
        self.Eflown = float(np.sum(np.abs(self.E[:, self.b]) ** 2)) / self.px


if __name__ == "__main__":
    print("=" * 130)
    print("(a) MEASURED: the error -> UFF path per route.  UFF is 'feedforward' only if this is ~0.")
    print(f"{'route':24s} {'SteerFriction':>14s} " + " ".join(f"{q:>8.2f}Hz" for q in (0.20, 0.29, 0.39, 0.59, 0.98)))
    for r in R:
        f, Cfb, Cff, Cana, v = iv_paths(r)
        j = [int(np.argmin(np.abs(f - q))) for q in (0.20, 0.29, 0.39, 0.59, 0.98)]
        print(f"{r:24s} {FRIC[r]:14.4f} " + " ".join(f"|Cff| {abs(Cff[i]):.4f}" for i in j))
        print(f"{'  ratio |Cff|/|Cfb|':24s} {'':14s} " + " ".join(f"{abs(Cff[i])/abs(Cfb[i]):10.2f}" for i in j))
        print(f"{'  |Cfb| vs analytic':24s} {'':14s} " + " ".join(f"{abs(Cfb[i])/abs(Cana[i]):10.2f}" for i in j))
    print()
    print("  EXPECTED small-signal relay gain, torque per unit lat-accel error:")
    for r in R:
        print(f"    {r}: friction {FRIC[r]:.4f} -> {FRIC[r]/0.3:.3f}   (P path at SteerKP 1.0 / LAF 14 = {1/14:.3f})")

    print()
    print("=" * 130)
    print("(b) THE SteerKP SWEEP, EACH ROUTE ALONE.  If the ranking is a relay artefact it dies here.")
    KPS = [1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0]
    QS = [0.0, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 4.0]
    store = {}
    for keep, lbl in ((0, "6c  SteerFriction 0.0  (CLEAN)"), (1, "6d  SteerFriction 0.212 (RELAY)")):
        S = Sub(keep)
        # the sub-engine's own closure scale: its own as-flown J against the same V282 reference
        base = S.score(kp=1.0, laf=14.0, q=1.0)
        J0 = base["metric"]
        print(f"\n   --- {lbl}   windows {len(S.v)}   as-flown J {J0:.4f}   "
              f"(pooled J is 1.3512; V282 reference 0.442)")
        print("   " + HDR + "   Q")
        rows = []
        for kp in KPS:
            cand = [(q, S.score(kp=kp, laf=14.0, q=q)) for q in QS]
            rows.append((kp, cand))
            ok = [(q, r) for q, r in cand if r["shake_cmd"] <= 1.0]
            bq, br = (min(ok, key=lambda t: t[1]["metric"]) if ok
                      else min(cand, key=lambda t: t[1]["metric"]))
            br = dict(br)
            br["closure"] = (J0 - br["metric"]) / (J0 - 0.442)
            tag = f"Q {bq:.2f}" + ("" if ok else "  (no Q holds shake<=1)")
            print("   " + fmt(f"KP {kp:5.1f} shake<=1.00", br, tag))
        store[lbl] = J0
    print()
    print("=" * 130)
    print("(c) THE INHERITED |L|shake AXIS vs THE COMMAND-SHAKE AXIS, on the flown anchors (c2).")
    print("    |L|shake   r72 FLEW CLEAN 1.343 (IV) / 0.882 (blended)   >   r71 LIMIT-CYCLED 0.519 / 0.485")
    print("    command shake, common units:  r72 4.6   <   rev 6.4 32.4   <<   r71 951 (power) = 176 (rms, the brief)")
    print("    => the |L|shake ceiling the frontier was priced on does NOT order the two flown anchors.")
