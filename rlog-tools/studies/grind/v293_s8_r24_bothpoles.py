# -*- coding: utf-8 -*-
"""v293_s8_r24_bothpoles.py -- ADDENDUM to v293_s3_gate7: the r24 sweep on the BOTH-POLES family,
with the record's own dzeta_stable rows reproduced first as a POSITIVE CONTROL.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

WHY.  `v293_s3_gate7` scored the family "fits the measured V282 pole AND is closed-loop stable 2-60 Hz"
and found that with the SERVO PRESENT, cutting 0xC6446 RAISES zeta at 20 Hz.  The record
(`TRACE-2026-09-13-r24-lane-transfer` section 6.1, `_scratch/dzeta_stable.py`) found the OPPOSITE on
the subfamily that ALSO reproduces the measured V289 pole.  The two differ only in that extra
constraint, and the disagreement is material -- it decides whether cutting r24 is free or expensive.

So: reproduce the record's published rows exactly, then read the servo-gone columns off the SAME
subfamily.  If the control does not reproduce, nothing below it is reportable.

Also corrects one column of `v293_s3_gate7`: its 'unst' counted roots outside the unit circle over ALL
frequencies, and B(w)'s rational fit carries a near-unit-circle REAL root at DC (its denominator is
[1, -2.9915, 2.9861, -0.9947], which is ~(1-w)^3).  That DC artifact is why every cell read 250/250.
The record's own `stable_band` band-limits to 2-60 Hz for exactly this reason; so does this file.

Run: python v293_s8_r24_bothpoles.py [nproc]
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
import adv_v290_physics as A                 # noqa: E402
import r24_lane_transfer as M                # noqa: E402
import v293_lib as L                         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
F282, Z282 = (19.7, 20.4), (0.012, 0.045)
F289, Z289 = (15.6, 17.3), (-0.06, 0.12)
ZMIN = -0.005
KS = [1.00, 0.9010, 0.8488, 0.75, 0.5858, 0.50, 0.39, 0.33, 0.10, 0.00]
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
    fp, zps, kaps, taus, f1s, g0s, kap = args
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
                        p = dict(g0=float(g0), tau=float(tau), f1=float(f1), fp=fp, zp=zp, kappa=ka, label="m")
                        pl = A.Plant(p, 1.0, "m")
                        f2, z2 = M.mode2(el282, pl, r24)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        if not stable_band(el282, pl, r24):
                            continue
                        f9, z9 = M.mode2(el289, pl, r24)
                        if np.isfinite(f9) and F289[0] <= f9 <= F289[1] and Z289[0] <= z9 <= Z289[1]:
                            keep.append(p)
    return keep


def grid(kap, npc):
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
                         np.exp(np.linspace(np.log(0.002), np.log(0.8), 50)), kap))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s, kap))
    with Pool(npc, initializer=_init) as pool:
        res = pool.map(_w, jobs)
    return [x for r in res for x in r]


def main():
    npc = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 1)
    _init()
    c282 = L.read_cells(L.IMG282)
    elTM = L.BlocksTM(L.torque_mode(c282, kp=119), notch=False, g=0.0, kp=119, kd=0.0, fb_zero=True)
    el282, fb = _G["el282"], _G["fb"]

    pr("=" * 118)
    pr("r24 ON THE BOTH-POLES FAMILY -- the record's own subfamily, and what torque mode does to it")
    pr("agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 118)
    pr("Family: reproduces the MEASURED V282 pole (19.7-20.4 Hz, zeta 0.012-0.045) AND the MEASURED V289")
    pr("pole (15.6-17.3 Hz, zeta -0.06..0.12), and is closed-loop stable 2-60 Hz with BOTH arms.")
    pr("Published control (TRACE-2026-09-13-r24-lane-transfer section 6.1 / _scratch/dzeta_stable.json):")
    pub = {}
    try:
        pub = json.load(open(os.path.join(SCR, "dzeta_stable.json")))
    except Exception:                                            # noqa: BLE001
        pr("   (dzeta_stable.json not readable -- the control cannot be run)")
    for kk in ("0.10", "0.20", "0.45"):
        if kk in pub and "rows" in pub[kk]:
            pr("   kappa %s: n=%d, rows (0xC6446, f, zeta) = %s" %
               (kk, pub[kk]["n289"], ", ".join("%.0f/%.2f/%+.4f" % (r[0] * 5244, r[1], r[2])
                                               for r in pub[kk]["rows"][:4])))
    res = {}
    for kap in (0.10, 0.20, 0.45):
        t0 = time.time()
        fam = grid(kap, npc)
        pr("")
        pr("kappa %.2f : %d plants fit BOTH measured poles and are stable 2-60 Hz  (%.0f s)"
           % (kap, len(fam), time.time() - t0))
        if kk in pub and "n289" in pub.get("%.2f" % kap, {}):
            pr("   published count at this kappa: %d   %s" %
               (pub["%.2f" % kap]["n289"],
                "MATCH" if abs(len(fam) - pub["%.2f" % kap]["n289"]) <= 2 else
                "DIFFERS -- the control does not reproduce; read nothing below this line"))
        if not fam:
            res["%.2f" % kap] = dict(n=0)
            continue
        pls = [A.Plant(p, 1.0, "m") for p in fam]
        pr("  %8s %7s | %-24s | %-24s | %-18s" %
           ("0xC6446", "k", "SERVO PRESENT (control)", "SERVO GONE (V293)", "worst pole 3-30, TM"))
        pr("  %8s %7s | %7s %8s %8s | %7s %8s %8s | %7s %8s %5s" %
           ("", "", "f Hz", "zeta md", "z p10", "f Hz", "zeta md", "z p10", "f Hz", "zeta", "unst"))
        rows = []
        for k in KS:
            r = M.R_r24_poly(fb, kappa=kap * k) if k > 0 else (np.array([0.0]), np.array([1.0]))
            a1 = np.array([M.mode2(el282, pl, r) for pl in pls], float)
            a2 = np.array([M.mode2(elTM, pl, r) for pl in pls], float)
            worst, unst = [], 0
            for pl in pls:
                f, z, zz = M.poles2(elTM, pl, r)
                m = (f >= 3.0) & (f <= 30.0)
                if m.any():
                    j = int(np.nanargmin(z[m]))
                    worst.append((f[m][j], z[m][j]))
                    if z[m][j] < ZMIN:
                        unst += 1                         # BAND-LIMITED, per the record's stable_band
            worst = np.array(worst, float) if worst else np.zeros((1, 2))
            jw = int(np.nanargmin(worst[:, 1]))
            rows.append(dict(arm=k * 5244, k=k, f_sv=float(np.nanmedian(a1[:, 0])),
                             z_sv=float(np.nanmedian(a1[:, 1])), f_tm=float(np.nanmedian(a2[:, 0])),
                             z_tm=float(np.nanmedian(a2[:, 1])), wf=float(worst[jw, 0]),
                             wz=float(worst[jw, 1]), unst=unst, n=len(pls)))
            pr("  %8.0f %7.4f | %7.2f %8.4f %8.4f | %7.2f %8.4f %8.4f | %7.2f %8.4f %5d" %
               (k * 5244, k, np.nanmedian(a1[:, 0]), np.nanmedian(a1[:, 1]),
                np.nanpercentile(a1[:, 1], 10), np.nanmedian(a2[:, 0]), np.nanmedian(a2[:, 1]),
                np.nanpercentile(a2[:, 1], 10), worst[jw, 0], worst[jw, 1], unst))
        r1 = M.R_r24_poly(fb, kappa=kap)
        r0 = (np.array([0.0]), np.array([1.0]))
        dsv = np.array([M.mode2(el282, pl, r0)[1] - M.mode2(el282, pl, r1)[1] for pl in pls])
        dtm = np.array([M.mode2(elTM, pl, r0)[1] - M.mode2(elTM, pl, r1)[1] for pl in pls])
        pr("  PAIRED dzeta from REMOVING r24:  servo present p10/p50/p90 %+.4f %+.4f %+.4f (frac>0 %.2f)"
           % (*np.nanpercentile(dsv, [10, 50, 90]), float(np.mean(dsv > 0))))
        pr("                                   servo GONE     p10/p50/p90 %+.4f %+.4f %+.4f (frac>0 %.2f)"
           % (*np.nanpercentile(dtm, [10, 50, 90]), float(np.mean(dtm > 0))))
        pr("  (a POSITIVE paired dzeta means removing r24 RAISES zeta, i.e. r24 was DE-damping.)")
        res["%.2f" % kap] = dict(n=len(pls), rows=rows,
                                 paired_servo=list(np.nanpercentile(dsv, [10, 50, 90])),
                                 paired_tm=list(np.nanpercentile(dtm, [10, 50, 90])))
    json.dump(res, open(os.path.join(SCR, "v293_s8_r24_bothpoles.json"), "w"), indent=1)
    open(os.path.join(SCR, "v293_s8_r24_bothpoles.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s8_r24_bothpoles.{txt,json}")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
