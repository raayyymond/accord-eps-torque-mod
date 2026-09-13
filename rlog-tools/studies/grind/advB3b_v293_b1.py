# -*- coding: utf-8 -*-
"""advB3b_v293_b1.py -- ADVERSARY B, criterion B1 (and the pole half of B7) on the BUILT V293.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY -- reads images, writes one text file.  Never flashes.

ATTACK, not review.  Three things the design's own scripts do NOT do:
  1. it models Kp = 119; the BUILT IMAGE carries Kp = 120 on all 28 records (adversary A).  Re-score
     at the byte value and show the difference.
  2. `v293_s3_gate7`'s 'unst' column is broken (250/250 everywhere -- a DC artefact of B(w)'s
     rational fit).  Band-limit it to 2-60 Hz, as s8 does, and recount.
  3. apply the BROKEN-CHECK test to B1's own wording: score V282 (the FLOWN build) and arm 0
     against the same clause.  If they fail it too, the clause cannot decide anything.

Families:
  BOTH-POLES  -- reproduces the measured V282 pole AND the measured V289 pole (s8's constraint)
  V282-ONLY   -- reproduces the measured V282 pole only (s3's broader constraint)
both rebuilt here, at kappa 0.45 AND kappa 1.45, with the positive control that the kappa-0.45
both-poles count must reproduce the design's published 12.

Run: python advB3b_v293_b1.py [nproc]
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\advB3b"
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                 # noqa: E402
import r24_lane_transfer as M                # noqa: E402
import v293_lib as L                         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
F282, Z282 = (19.7, 20.4), (0.012, 0.045)
F289, Z289 = (15.6, 17.3), (-0.06, 0.12)
ZMIN = -0.005
ARMS = [5244, 4725, 4451, 3072, 2048, 1024, 512, 0]
NSUB = 250
_G = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def _init():
    c, _ = A.read_v289()
    c282 = dict(c)
    c282["fb_a"], c282["fb_b"] = 923, 1560
    _G["el282"] = A.Blocks(c282, False, 0.0)
    _G["el289"] = A.Blocks(c, True, 0.0)
    _G["fb"] = M.fit_B("creep_1_3med", nb=1, nd=3)


def stable_band(el, pl, r24, lo=2.0, hi=60.0):
    f, z, _ = M.poles2(el, pl, r24)
    m = (f >= lo) & (f <= hi)
    return (not m.any()) or bool(np.nanmin(z[m]) >= ZMIN)


def _w(args):
    fp, zps, kaps, taus, f1s, g0s, kap, need289 = args
    if "el282" not in _G:
        _init()
    el282, el289 = _G["el282"], _G["el289"]
    r24 = M.R_r24_poly(_G["fb"], kappa=kap) if kap > 0 else (np.array([0.0]), np.array([1.0]))
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
                        f2, z2 = M.mode2(el282, pl, r24)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        if not stable_band(el282, pl, r24):
                            continue
                        if need289:
                            f9, z9 = M.mode2(el289, pl, r24)
                            if not (np.isfinite(f9) and F289[0] <= f9 <= F289[1] and Z289[0] <= z9 <= Z289[1]):
                                continue
                        keep.append(p)
    return keep


def grid(kap, npc, need289):
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
                         np.exp(np.linspace(np.log(0.002), np.log(0.8), 50)), kap, need289))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s, kap, need289))
    with Pool(npc, initializer=_init) as pool:
        res = pool.map(_w, jobs)
    return [x for r in res for x in r]


# ---------------------------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------------------------
def _score_one(args):
    plist, kap, arm, kp = args
    if "el282" not in _G:
        _init()
    el282 = _G["el282"]
    c282 = L.read_cells(L.IMG282)
    elTM = L.BlocksTM(L.torque_mode(c282, kp=kp), notch=False, g=0.0, kp=kp, kd=0.0, fb_zero=True)
    r24 = L.R_r24_poly(_G["fb"], arm=float(arm), kappa=kap) if kap > 0 else (np.array([0.0]), np.array([1.0]))
    rows = []
    for p in plist:
        pl = A.Plant(p, 1.0, "m")
        out = {}
        for tag, el in (("v282", el282), ("tm", elTM)):
            f, z, zz = L.poles_two_arm(el, pl, r24, 2.0, 60.0)
            m3 = (f >= 3.0) & (f <= 30.0)
            f3, z3 = f[m3], z[m3]
            if len(z3):
                k = int(np.argmin(z3))
                out[tag + "_wf"], out[tag + "_wz"] = float(f3[k]), float(z3[k])
                out[tag + "_n05"] = int(np.sum(z3 < 0.05))
                out[tag + "_n10_1018"] = int(np.sum((f3 >= 10.0) & (f3 <= 18.0) & (z3 < 0.10)))
            else:
                out[tag + "_wf"], out[tag + "_wz"] = np.nan, np.nan
                out[tag + "_n05"] = 0
                out[tag + "_n10_1018"] = 0
            # the 20 Hz mode itself (least damped in 12-32)
            m2 = (f >= 12.0) & (f <= 32.0)
            if m2.any():
                k2 = int(np.argmin(z[m2]))
                out[tag + "_mf"], out[tag + "_mz"] = float(f[m2][k2]), float(z[m2][k2])
            else:
                out[tag + "_mf"], out[tag + "_mz"] = np.nan, np.nan
            # BAND-LIMITED instability: any root in 2-60 Hz outside the unit circle
            out[tag + "_unst"] = bool(np.any(np.abs(zz) >= 1.0)) if len(zz) else False
        rows.append(out)
    return rows


def score(fam, kap, kp, npc, label):
    rng = np.random.default_rng(20260913)
    if len(fam) > NSUB:
        sel = rng.choice(len(fam), NSUB, replace=False)
        sub = [fam[i] for i in sel]
        note = "   (seeded subsample %d of %d)" % (NSUB, len(fam))
    else:
        sub = fam
        note = "   (all %d plants)" % len(fam)
    pr("%s   kappa %.2f   Kp %d%s" % (label, kap, kp, note))
    pr("   0xC6446 |  V282 SERVO PRESENT (flown)      |  V293 TORQUE MODE (built image)   | B7 10-18Hz")
    pr("           |  20Hz f/z md   worst3-30 z  n<.05 |  20Hz f/z md   worst3-30 z  n<.05 unst | n(z<.10)")
    tab = {}
    for arm in ARMS:
        chunks = [sub[i::npc] for i in range(npc)]
        with Pool(npc, initializer=_init) as pool:
            res = pool.map(_score_one, [(ch, kap, arm, kp) for ch in chunks])
        rows = [r for rr in res for r in rr]
        g = lambda k: np.array([r[k] for r in rows], float)  # noqa: E731
        rec = dict(
            arm=arm,
            v282_mf=float(np.nanmedian(g("v282_mf"))), v282_mz=float(np.nanmedian(g("v282_mz"))),
            v282_wz=float(np.nanmin(g("v282_wz"))), v282_n05=int(np.sum(g("v282_n05") > 0)),
            tm_mf=float(np.nanmedian(g("tm_mf"))), tm_mz=float(np.nanmedian(g("tm_mz"))),
            tm_wz=float(np.nanmin(g("tm_wz"))), tm_n05=int(np.sum(g("tm_n05") > 0)),
            tm_unst=int(np.sum([r["tm_unst"] for r in rows])),
            v282_unst=int(np.sum([r["v282_unst"] for r in rows])),
            tm_b7=int(np.sum(g("tm_n10_1018") > 0)), v282_b7=int(np.sum(g("v282_n10_1018") > 0)),
            n=len(rows))
        tab[arm] = rec
        pr("      %5d | %6.2f %7.4f  %8.4f  %4d | %6.2f %7.4f  %8.4f  %4d %4d | %4d (V282 %d)" % (
            arm, rec["v282_mf"], rec["v282_mz"], rec["v282_wz"], rec["v282_n05"],
            rec["tm_mf"], rec["tm_mz"], rec["tm_wz"], rec["tm_n05"], rec["tm_unst"],
            rec["tm_b7"], rec["v282_b7"]))
    pr()
    return tab


def main():
    npc = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    _init()
    c282 = L.read_cells(L.IMG282)
    c293 = L.read_cells(L.IMG293) if hasattr(L, "IMG293") else None
    pr("=" * 126)
    pr("ADVERSARY B -- B1 / B7(poles) on the BUILT V293 image.   agent advB3b, 2026-09-13.  ANALYSIS ONLY")
    pr("=" * 126)
    pr("B1 FAIL (as written): any fit unstable, or ANY pole with zeta < 0.05 in 3-30 Hz, loop open, at")
    pr("the chosen arm, on BOTH families, at kappa 0.45 AND 1.45.")
    pr("B7 FAIL (pole half):  a NEW pole with zeta < 0.10 in 10-18 Hz.")
    pr("Columns: '20Hz f/z md' = median over the family of the least-damped pole in 12-32 Hz;")
    pr("         'worst3-30 z' = the MINIMUM over the family of the least-damped 3-30 Hz pole (extreme value);")
    pr("         'n<.05' = how many PLANTS carry any 3-30 Hz pole below zeta 0.05 (the literal clause);")
    pr("         'unst' = plants with a root outside the unit circle IN 2-60 Hz (band-limited -- s3's")
    pr("                  unbanded column read 250/250 everywhere on a DC artefact of B(w)'s fit).")
    pr()

    tot = time.time()
    out = {}
    for need289, label in ((True, "BOTH-POLES family (V282 pole AND V289 pole)"),
                           (False, "V282-POLE-ONLY family (the broader one)")):
        for kap in (0.45, 1.45):
            t0 = time.time()
            fam = grid(kap, npc, need289)
            pr("-" * 126)
            pr("%s | kappa %.2f | n = %d plants  (%.0f s)" % (label, kap, len(fam), time.time() - t0))
            if need289 and abs(kap - 0.45) < 1e-9:
                pr("   POSITIVE CONTROL: the design's published both-poles count at kappa 0.45 is 12 -> %s"
                   % ("MATCH" if len(fam) == 12 else "MISMATCH (got %d)" % len(fam)))
            pr("-" * 126)
            if not fam:
                pr("   EMPTY FAMILY -- nothing to score at this kappa.")
                pr()
                continue
            for kp in (120, 119):
                tab = score(fam, kap, kp, npc, "  Kp from the BUILT IMAGE" if kp == 120 else "  Kp as the DESIGN modelled it")
                out["%s|k%.2f|kp%d" % ("both" if need289 else "v282only", kap, kp)] = tab
    pr("=" * 126)
    pr("total %.0f s" % (time.time() - tot))
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b1_poles.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(out, open(os.path.join(OUTDIR, "b1_poles.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
