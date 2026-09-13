# -*- coding: utf-8 -*-
"""studies/grind/r24_plant_refit.py -- RE-FIT the plant family with the r24 arm IN THE LOOP.

WHY THIS EXISTS.  design290b_family.json was fitted with the SERVO ARM ALONE closing the loop
(adv_v290_physics.loop = R_servo * CPD * G).  The r24 base-assist rate lane is a SECOND arm of the same
loop -- a 4 ms backward difference of the torsion-bar torque, gain 0xC6446 = 5244, summed into the same
aggregator with a unit coefficient.  At 20.3 Hz its arm is |R| ~ 3.2 counts per raw rate count against the
servo's 1.74, i.e. the loop the existing family fitted is MISSING ~65 % OF ITS OWN RETURN RATIO.  Any
plant fitted without it has absorbed r24 into its own zp/g0, so adding r24 on top double-counts -- which
is exactly what happens: 0 of 304 plants still reproduce the measured V282 pole once r24 is included.

WHAT THIS DOES.  Re-runs design290b's own grid (same ranges, same targets) with
    L_tot = (R_servo + sgn * R_r24) * CPD * G
for BOTH signs, keeping every plant that reproduces the MEASURED V282 pole (19.7-20.4 Hz, zeta
0.012-0.045) and, as a second and independent constraint, the MEASURED V289 pole (15.6-17.3 Hz,
zeta -0.06..0.12) -- V289 changed only the SERVO arm (notch + fb pole), so r24 is identical there.
Whether either sign can satisfy both with one plant is an empirical discriminator on the sign.

Run:  python r24_plant_refit.py [nproc]     -> _scratch/r24_plant_refit.{txt,json}
Subagent r24lane, 2026-09-13.  ANALYSIS ONLY.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A          # noqa: E402
import r24_lane_transfer as M         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, CPD = A.TS, A.CPD
F282, Z282 = (19.7, 20.4), (0.012, 0.045)
F289, Z289 = (15.6, 17.3), (-0.06, 0.12)
G_282 = {10.2: (27.0, -79.0), 15.6: (40.8, -63.0), 18.0: (39.0, -73.0),
         20.3: (47.6, -72.0), 22.7: (44.6, -69.0), 24.2: (18.8, -41.0)}
TAU_STREAM = 0.0039
STRATUM = "creep_1_3med"
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


_G = {}


def _init():
    c, _ = A.read_v289()
    c282 = dict(c); c282["fb_a"], c282["fb_b"] = 923, 1560
    _G["el282"] = A.Blocks(c282, False, 0.0)
    _G["el289"] = A.Blocks(c, True, 0.0)
    _G["el696"] = A.Blocks(c282, False, 0.0, kp=696)
    fb = M.fit_B(STRATUM, nb=4, nd=2)
    _G["fb"] = fb
    for kappa in (1.00, 0.45):
        for sgn in (+1, -1):
            n, d = M.R_r24_poly(fb, kappa=kappa)
            _G[(kappa, sgn)] = (n * sgn, d)
    _G[(0.0, +1)] = (np.array([0.0]), np.array([1.0]))


def _worker(args):
    fp, zps, kaps, taus, f1s, g0s, kappa, sgn = args
    if "el282" not in _G:
        _init()
    el282, el289 = _G["el282"], _G["el289"]
    r24 = _G[(kappa, sgn)] if kappa > 0 else _G[(0.0, +1)]
    keep = []
    for zp in zps:
        for kap in kaps:
            if fp is None and (zp is not None or kap is not None):
                continue
            for tau in taus:
                for f1 in f1s:
                    for g0 in g0s:
                        p = dict(g0=float(g0), tau=float(tau), f1=float(f1), fp=fp, zp=zp, kappa=kap)
                        pl = A.Plant(dict(p, label="m"), 1.0, "m")
                        f2, z2 = M.mode2(el282, pl, r24)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        f9, z9 = M.mode2(el289, pl, r24)
                        ok289 = bool(np.isfinite(f9) and F289[0] <= f9 <= F289[1] and Z289[0] <= z9 <= Z289[1])
                        err = []
                        for f0, (mag, phr) in G_282.items():
                            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * TAU_STREAM
                            err.append((float(np.log(abs(g) / mag)),
                                        float((np.degrees(np.angle(g)) - phc + 180) % 360 - 180)))
                        p.update(f282=f2, z282=z2, f289=f9, z289=z9, ok289=ok289, goff=err,
                                 kappa_r24=kappa, sgn=sgn)
                        keep.append(p)
    return keep


def grid(kappa, sgn, nproc):
    fps = [None] + list(np.arange(15.0, 28.01, 0.5))
    zps = (0.02, 0.04, 0.07, 0.12, 0.2, 0.35, 0.5, 0.7); kaps = (None, 0.15, 0.3, 0.6, 1.0)
    taus = (0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012); f1s = (3.0, 5.0, 12.0, 30.0)
    g0s = np.exp(np.linspace(np.log(0.002), np.log(0.8), 30))
    jobs = []
    for fp in fps:
        if fp is None:
            jobs.append((None, (None,), (None,), tuple(np.arange(0.001, 0.0161, 0.001)),
                         (2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0),
                         np.exp(np.linspace(np.log(0.002), np.log(0.8), 50)), kappa, sgn))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s, kappa, sgn))
    with Pool(nproc, initializer=_init) as pool:
        res = pool.map(_worker, jobs)
    fam = [p for r in res for p in r]
    for i, p in enumerate(fam):
        p["id"] = i
        p["label"] = ("smooth" if p["fp"] is None else "fp%.1f zp%.2f k%s" %
                      (p["fp"], p["zp"], ("%.2f" % p["kappa"]) if p["kappa"] is not None else "None")) \
            + " tau%.0f f1%.0f g0%.3f" % (1e3 * p["tau"], p["f1"], p["g0"])
    return fam


def main():
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 1)
    _init()
    pr("=" * 112)
    pr("PLANT FAMILY RE-FITTED WITH THE r24 ARM IN THE LOOP     r24lane 2026-09-13   (%d procs)" % nproc)
    pr("=" * 112)
    fb = _G["fb"]
    pr("B(f) fit: stratum %s, rms ln|B| %.4f, rms phase %.2f deg" % (STRATUM, fb["rms_ln_mag"], fb["rms_phase_deg"]))
    pr("targets: V282 pole %.1f-%.1f Hz zeta %.3f-%.3f ; V289 pole %.1f-%.1f Hz zeta %.3f-%.3f (2nd constraint)"
       % (F282 + Z282 + F289 + Z289))
    pr("")
    fams = {}
    for kappa, sgn, tag in ((0.0, +1, "NO r24 (control -- must reproduce design290b)"),
                            (1.00, +1, "r24 ADDED, kappa 1.00 (closed form at 5244)"),
                            (1.00, -1, "r24 SUBTRACTED, kappa 1.00"),
                            (0.45, +1, "r24 ADDED, kappa 0.45 (wire bit-6 inversion)"),
                            (0.45, -1, "r24 SUBTRACTED, kappa 0.45")):
        t0 = time.time()
        fam = grid(kappa, sgn, nproc)
        n289 = sum(1 for p in fam if p["ok289"])
        fams["k%.2f_s%+d" % (kappa, sgn)] = fam
        pr("  %-46s : %5d plants fit V282, of which %5d ALSO fit V289   (%.0f s)"
           % (tag, len(fam), n289, time.time() - t0))
    pr("")
    json.dump({k: v for k, v in fams.items()}, open(os.path.join(SCR, "r24_plant_refit.json"), "w"), indent=0)
    open(os.path.join(SCR, "r24_plant_refit.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("wrote _scratch/r24_plant_refit.{txt,json}")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
