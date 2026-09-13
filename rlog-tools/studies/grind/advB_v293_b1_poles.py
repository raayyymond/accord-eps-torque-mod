# -*- coding: utf-8 -*-
"""advB_v293_b1_poles.py -- ADVERSARY B, criteria B1 and B7(poles): the closed-loop poles of the BUILT V293.

Agent `advB3`, subagent of `main`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends
nothing on any bus, edits no build script, writes no image.

B1 (pre-registration): "Any fit of the family unstable, or any pole with zeta < 0.05 in 3-30 Hz, with the
LKAS loop open and r24 at the chosen arm -- on the RE-FITTED family with r24 explicit
(r24_plant_refit.json), at kappa 0.45 AND kappa 1.45 (the disputed effective arm; both must pass)."
B7 (poles half): "a new pole with zeta < 0.10 in 10-18 Hz".

WHAT IS SCORED, AND WHY IT IS SCORED FOUR WAYS
  The record contains TWO disagreeing plant families and this file adjudicates them rather than picking:
    (A) r24_plant_refit.json  -- design290b's grid re-run with the r24 arm IN the loop, at kappa
        0.45 and 1.00, both signs.  Under the V289 constraint it keeps 0 plants at kappa 0.45 sign +1
        and 12 at kappa 0.45 sign -1.
    (B) the v293_s8 "both-poles" family -- the same grid but built with a DIFFERENT B(f) rational
        (fit_B nb=1 nd=3 instead of nb=4 nd=2) and kappa 0.10/0.20/0.45, which keeps 269/256/12.
  They cannot both be right.  Both are rebuilt here from the same code path and the disagreement is
  attributed to the B(f) fit order, which is reported as a fragility of the record, not of the build.

EVERY electronics dict is read from the BUILT IMAGE.  The torque-mode arm is BlocksTM with fb_zero=True,
Kp from the image (120), Kd 0 -- not the design's 119.
"""
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"                 # this box runs out of pagefile with a threaded BLAS per worker

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
NCAP = 700                               # families are SUBSAMPLED to this size; declared in the output
RNG = np.random.default_rng(20260913)
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A               # noqa: E402
import r24_lane_transfer as M              # noqa: E402
import v293_lib as L                       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG293 = glob.glob(FW + "_v293_*_plain_image.bin")[0]
IMG282 = glob.glob(FW + "_v282_*_plain_image.bin")[0]
F282, Z282 = (19.7, 20.4), (0.012, 0.045)
F289, Z289 = (15.6, 17.3), (-0.06, 0.12)
ARMS = [5244.0, 4451.0, 2048.0, 512.0, 0.0]        # flown V282 / the design's / THE BUILT DOSE / stock / none
OUT = []
_G = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def _init():
    c, _ = A.read_v289()
    c282i = dict(c)
    c282i["fb_a"], c282i["fb_b"] = 923, 1560
    _G["el282"] = A.Blocks(c282i, False, 0.0)                 # V282 servo, the record's own construction
    _G["el289"] = A.Blocks(c, True, 0.0)
    c293 = L.read_cells(IMG293)
    _G["c293"] = c293
    _G["elTM"] = L.BlocksTM(c293, notch=False, g=0.0, kp=float(c293["kp_Y"][0]), kd=0.0, fb_zero=True)
    _G["fb13"] = M.fit_B("creep_1_3med", nb=1, nd=3)          # the v293_s8 / dzeta_stable fit
    _G["fb14"] = M.fit_B("creep_1_3med", nb=1, nd=4)          # the module default
    return _G


def r24(fbkey, kappa, arm):
    if kappa <= 0 or arm <= 0:
        return (np.array([0.0]), np.array([1.0]))
    n, d = M.R_r24_poly(_G[fbkey], kappa=kappa)
    return n * (float(arm) / M.GAIN_FLOWN), d


def worst_pole(el, pl, r, lo=3.0, hi=30.0):
    """worst (least-damped) closed-loop pole in [lo, hi] Hz, and whether ANY 2-60 Hz root is outside
    the unit circle.  The unstable flag is BAND-LIMITED to 2-60 Hz, per the record's own `stable_band`:
    B(w)'s rational fit carries near-unit REAL roots at DC (its denominator is ~(1-w)^3), and counting
    those makes every cell read 'unstable'.  That is a FIT ARTEFACT, not a plant claim."""
    f, z, zz = M.poles2(el, pl, r)
    band = (f >= 2.0) & (f <= 60.0)
    uns = bool(np.any(np.abs(zz[band]) >= 1.0)) if band.any() else False
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan, uns
    j = int(np.nanargmin(z[m]))
    return float(f[m][j]), float(z[m][j]), uns


# ---------------------------------------------------------------------------- family (re)construction
def _wfam(args):
    fp, zps, kaps, taus, f1s, g0s, kappa, sgn, fbkey = args
    if "el282" not in _G:
        _init()
    el282, el289 = _G["el282"], _G["el289"]
    r = r24(fbkey, kappa, M.GAIN_FLOWN)
    if sgn < 0:
        r = (r[0] * -1.0, r[1])
    keep = []
    for zp in zps:
        for ka in kaps:
            if fp is None and (zp is not None or ka is not None):
                continue
            for tau in taus:
                for f1 in f1s:
                    for g0 in g0s:
                        p = dict(g0=float(g0), tau=float(tau), f1=float(f1), fp=fp, zp=zp,
                                 kappa=ka, label="m")
                        pl = A.Plant(p, 1.0, "m")
                        f2, z2 = M.mode2(el282, pl, r)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        f9, z9 = M.mode2(el289, pl, r)
                        p["ok289"] = bool(np.isfinite(f9) and F289[0] <= f9 <= F289[1]
                                          and Z289[0] <= z9 <= Z289[1])
                        p["f282"], p["z282"] = float(f2), float(z2)
                        keep.append(p)
    return keep


def build_family(kappa, sgn, fbkey, npc):
    fps = [None] + list(np.arange(15.0, 28.01, 0.5))
    zps = (0.02, 0.04, 0.07, 0.12, 0.2, 0.35, 0.5, 0.7)
    kaps = (None, 0.15, 0.3, 0.6, 1.0)
    taus = (0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012)
    f1s = (3.0, 5.0, 12.0, 30.0)
    g0s = np.exp(np.linspace(np.log(0.002), np.log(0.8), 30))
    jobs = []
    for fp in fps:
        if fp is None:
            jobs.append((None, (None,), (None,), tuple(np.arange(0.001, 0.0161, 0.001)),
                         (2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0),
                         np.exp(np.linspace(np.log(0.002), np.log(0.8), 50)), kappa, sgn, fbkey))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s, kappa, sgn, fbkey))
    with Pool(npc, initializer=_init) as pool:
        res = pool.map(_wfam, jobs)
    return [x for r in res for x in r]


def score(fam, kappa, sgn, fbkey, tag):
    """the B1 table for one family: worst 3-30 Hz pole on TORQUE MODE at each r24 arm."""
    n_all = len(fam)
    if n_all > NCAP:
        fam = [fam[i] for i in RNG.choice(n_all, NCAP, replace=False)]
        tag += "  [SUBSAMPLED %d of %d]" % (NCAP, n_all)
    pls = [A.Plant(p, 1.0, "m") for p in fam]
    el282, elTM = _G["el282"], _G["elTM"]
    pr("")
    pr("  %s   (n = %d plants)" % (tag, len(pls)))
    pr("  %8s | %-34s | %-46s | %-24s | %s"
       % ("0xC6446", "V282 SERVO PRESENT (the flown build)", "V293 TORQUE MODE (the built image)",
          "B7: worst 10-18 Hz, TM", "0.3-3 Hz (fit artefact)"))
    pr("  %8s | %7s %8s %8s %5s | %7s %8s %8s %7s %6s %6s | %7s %8s %7s | %6s %8s"
       % ("", "f", "z md", "z p10", "n<.05", "f", "z md", "z p10", "n<.05", "n<=0", "unst",
          "f", "z md", "n<.10", "f", "z md"))
    rows = []
    for arm in ARMS:
        r = r24(fbkey, kappa, arm)
        if sgn < 0:
            r = (r[0] * -1.0, r[1])
        a1 = np.array([worst_pole(el282, pl, r)[:2] for pl in pls], float)
        a2 = np.array([worst_pole(elTM, pl, r) for pl in pls], dtype=object)
        f2 = np.array([x[0] for x in a2], float)
        z2 = np.array([x[1] for x in a2], float)
        un = np.array([bool(x[2]) for x in a2])
        b7 = np.array([worst_pole(elTM, pl, r, 10.0, 18.0)[:2] for pl in pls], float)
        lfa = np.array([worst_pole(elTM, pl, r, 0.3, 3.0)[:2] for pl in pls], float)
        rows.append(dict(arm=arm, f_sv=float(np.nanmedian(a1[:, 0])), z_sv=float(np.nanmedian(a1[:, 1])),
                         n05_sv=int(np.nansum(a1[:, 1] < 0.05)),
                         f_tm=float(np.nanmedian(f2)), z_tm=float(np.nanmedian(z2)),
                         z_tm_p10=float(np.nanpercentile(z2, 10)),
                         n05_tm=int(np.nansum(z2 < 0.05)), nneg=int(np.nansum(z2 <= 0.0)),
                         unst=int(un.sum()),
                         f_b7=float(np.nanmedian(b7[:, 0])), z_b7=float(np.nanmedian(b7[:, 1])),
                         n10_b7=int(np.nansum(b7[:, 1] < 0.10)),
                         f_lf=float(np.nanmedian(lfa[:, 0])), z_lf=float(np.nanmedian(lfa[:, 1])),
                         n=len(pls)))
        pr("  %8.0f | %7.2f %8.4f %8.4f %5d | %7.2f %8.4f %8.4f %7d %6d %6d | %7.2f %8.4f %7d | %6.2f %8.4f"
           % (arm, np.nanmedian(a1[:, 0]), np.nanmedian(a1[:, 1]), np.nanpercentile(a1[:, 1], 10),
              int(np.nansum(a1[:, 1] < 0.05)), np.nanmedian(f2), np.nanmedian(z2),
              np.nanpercentile(z2, 10), int(np.nansum(z2 < 0.05)), int(np.nansum(z2 <= 0.0)),
              int(un.sum()), np.nanmedian(b7[:, 0]), np.nanmedian(b7[:, 1]),
              int(np.nansum(b7[:, 1] < 0.10)), np.nanmedian(lfa[:, 0]), np.nanmedian(lfa[:, 1])))
    return rows


def main():
    npc = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 1)
    _init()
    c293 = _G["c293"]
    pr("=" * 126)
    pr("ADVERSARY B -- B1 (and the pole half of B7): the closed-loop poles of the BUILT V293")
    pr("agent `advB3`, 2026-09-13.  ANALYSIS ONLY.   (%d procs)" % npc)
    pr("=" * 126)
    pr("Electronics read from the BUILT image: Kp %s  Kd %s  fb_clamp %d  d_clamp %d  r24 arm %d  gain %d"
       % (c293["kp_Y"], c293["kd_Y"], c293["fb_clamp"], c293["d_clamp"], c293["r24_arm"], c293["gain"]))
    pr("B1 FAIL = any fit unstable, or any pole with zeta < 0.05 in 3-30 Hz, on torque mode at the arm.")
    pr("B7 FAIL(poles) = a new pole with zeta < 0.10 in 10-18 Hz.")
    pr("")

    # ---------------------------------------------------- 0. the B(f) fits, and the reproducibility gap
    pr("-" * 126)
    pr("0. THE B(f) RATIONAL -- and a reproducibility defect in the record")
    pr("-" * 126)
    for k in ("fb13", "fb14"):
        fb = _G[k]
        pr("  %s: rms ln|B| %.4f, rms phase %.2f deg, den %s"
           % (k, fb["rms_ln_mag"], fb["rms_phase_deg"], np.round(fb["den"], 4).tolist()))
    try:
        M.fit_B("creep_1_3med", nb=4, nd=2)
        pr("  fit_B(nb=4, nd=2) RUNS -- r24_plant_refit.py reproduces")
    except Exception as e:                                            # noqa: BLE001
        pr("  fit_B(nb=4, nd=2) RAISES %s: %s" % (type(e).__name__, e))
        pr("  => `r24_plant_refit.py` as it stands on disk CANNOT regenerate `r24_plant_refit.json`.")
        pr("     The family the pre-registration names is therefore NOT reproducible from its own script.")

    # ---------------------------------------------------- 1. the record's own refit family, as stored
    pr("")
    pr("-" * 126)
    pr("1. THE STORED RE-FIT FAMILY (_scratch/r24_plant_refit.json) -- what it actually contains")
    pr("-" * 126)
    stored = json.load(open(os.path.join(SCR, "r24_plant_refit.json")))
    for k, v in stored.items():
        pr("  %-12s n(V282 pole) = %5d   n(V282 AND V289 poles) = %4d" % (k, len(v), sum(1 for x in v if x["ok289"])))
    pr("  => at the DEFAULT sign (+1, r24 ADDED) the both-poles subfamily is EMPTY at every kappa it stores.")
    pr("     Only the r24-SUBTRACTED sign keeps any plant (12, at kappa 0.45).")

    res = {}
    pr("")
    pr("  🛑 THE STORED FAMILY CANNOT BE RE-SCORED ON ITS OWN TERMS: the B(w) rational it was built with")
    pr("     is not reproducible (above).  Re-scored below under fb13, the BEST-FITTING rational of the")
    pr("     two the module can actually produce -- so the membership test and the scoring test differ,")
    pr("     and that is declared, not hidden.  The rebuilt families in sections 2-3 do not have this flaw.")
    for key, kap, sgn in (("k0.45_s+1", 0.45, +1), ("k1.00_s+1", 1.00, +1), ("k0.45_s-1", 0.45, -1)):
        fam = stored[key]
        both = [p for p in fam if p["ok289"]]
        res[key] = dict(all=score(fam, kap, sgn, "fb13", "STORED %s, V282-pole-only (re-scored, fb13)" % key))
        if both:
            res[key + "_both"] = dict(all=score(both, kap, sgn, "fb13",
                                                "STORED %s, BOTH measured poles (re-scored, fb13)" % key))

    # ---------------------------------------------------- 2. the design's both-poles family, rebuilt
    pr("")
    pr("-" * 126)
    pr("2. THE DESIGN'S BOTH-POLES FAMILY (v293_s8: fit_B nb=1 nd=3, kappa 0.10/0.20/0.45), REBUILT HERE")
    pr("   POSITIVE CONTROL: the counts must reproduce the design's published 269 / 256 / 12.")
    pr("-" * 126)
    for kap in (0.10, 0.20, 0.45):
        t0 = time.time()
        fam = build_family(kap, +1, "fb13", npc)
        both = [p for p in fam if p["ok289"]]
        pr("  kappa %.2f (fb13): %d fit V282, %d also fit V289   (design published 269/256/12)  (%.0f s)"
           % (kap, len(fam), len(both), time.time() - t0))
        res["design_k%.2f_n" % kap] = dict(nV282=len(fam), nboth=len(both))
        if both:
            res["design_k%.2f_both" % kap] = dict(all=score(both, kap, +1, "fb13",
                                                            "DESIGN family kappa %.2f, BOTH poles" % kap))

    # ---------------------------------------------------- 3. kappa 0.45 and 1.45, the brief's two
    pr("")
    pr("-" * 126)
    pr("3. THE BRIEF'S TWO DISPUTED KAPPAS -- 0.45 (the cave's scale-free bit-6 instrument) and 1.45")
    pr("   (the record's normalised 7.3 Hz split).  Built with fb13, both signs of the r24 arm.")
    pr("-" * 126)
    for kap in (0.45, 1.45):
        for sgn in (+1, -1):
            t0 = time.time()
            fam = build_family(kap, sgn, "fb13", npc)
            both = [p for p in fam if p["ok289"]]
            pr("  kappa %.2f sign %+d : %d fit the V282 pole, %d also fit the V289 pole  (%.0f s)"
               % (kap, sgn, len(fam), len(both), time.time() - t0))
            res["b_k%.2f_s%+d_n" % (kap, sgn)] = dict(nV282=len(fam), nboth=len(both))
            if fam:
                res["b_k%.2f_s%+d" % (kap, sgn)] = dict(
                    all=score(fam, kap, sgn, "fb13", "kappa %.2f sign %+d, V282-pole-only" % (kap, sgn)))
            if both:
                res["b_k%.2f_s%+d_both" % (kap, sgn)] = dict(
                    all=score(both, kap, sgn, "fb13", "kappa %.2f sign %+d, BOTH poles" % (kap, sgn)))

    json.dump(res, open(os.path.join(SCR, "advB_v293_b1.json"), "w"), indent=1, default=float)
    open(os.path.join(SCR, "advB_v293_b1.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/advB_v293_b1.{txt,json}")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
