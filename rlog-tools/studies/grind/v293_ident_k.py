# -*- coding: utf-8 -*-
"""v293_ident_k.py -- THE SNAP STATISTICS, in the form the orchestrator asked for.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

(a) |rate| histogram per band, and the fraction of frames with |rate| < 1 deg/s WHILE THE COMMAND IS
    CHANGING -- the conditioning matters: a still wheel under a still command is not a snap.
(b) dwell run-lengths, and the ANGLE JUMP at the end of every dwell >= 0.2 s (the snap amplitude in
    degrees), p50/p90 and events per minute.
(c) the same on the V282 reference r6c, like-for-like.
(d) does the command cross the Coulomb band during the dwell?  |d cmd| from dwell start to slip
    onset against 2F, with F the measured Coulomb friction (0.011 of full scale = 45 counts of 0xE4,
    so 2F = 90 counts).  That is the stick-slip test the orchestrator specified.
(e) is the COMMAND smooth across the snap?  -- rules out a stepping command.

🛑 MASKING.  r70 carries carState.steeringPressed, so its hands-off stratum is exact (pressed False
with a +-0.5 s buffer).  r6c does NOT carry it, and the 0x18F driver-torque bar cannot substitute:
measured on r70, |bar| < 800 catches 98.2 % of hands-off frames and 0.1 % of hands-on ones, i.e. it
is just "almost everything" (v293_ident_h.py H0).  So EVERY CROSS-ROUTE ROW IS ALL-ENGAGED on both
routes, and r70's hands-off stratum is reported beside it as its own row.

🛑 INSTRUMENT.  The 0x14A angle quantises at 0.1 deg, so d(angle)/dt cannot resolve a still wheel.
All rate statistics use the 0x18F rate field (0.125 deg/s LSB), which is an independent measurement.
The angle is used only for the SNAP AMPLITUDE, where 0.1 deg is fine.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V280 = os.path.join(L.KIT, "analysis-2020accord", "_scratch", "cache", "v280")
OUT = []
pr = L.pr_factory(OUT)
FS, DT, CPD = 100.0, 0.01, 8.0
RES = {}
BANDS = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
BNAME = ["0-5", "5-10", "10-20", ">20"]
F_TORQUE = 0.011                 # measured Coulomb friction, fraction of full-scale torque
F_CNT = F_TORQUE * 4096.0        # in 0xE4 counts
DWELL_TH = 0.5                   # deg/s
DWELL_MIN = int(0.20 * FS)


def load(tag):
    d = dict(np.load(os.path.join(V280, tag + ".npz")))
    t0 = d["t18"][0]
    t1 = min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1])
    ta = np.arange(0.0, t1 - t0, DT) + t0
    g = dict(rate=L.zoh(ta, d["t18"], d["rate"]) / CPD, ang=L.zoh(ta, d["t14"], d["ang"]),
             cmd=L.zoh(ta, d["te4"], d["cmd"]), v=L.zoh(ta, d["tcs"], d["vego"]),
             eng=(L.zoh(ta, d["te4"], d["req"]) > 0.5) & (L.zoh(ta, d["t18"], d["sca"]) > 0.5))
    if "cs_press" in d:
        p = L.zoh(ta, d["tcs"], d["cs_press"]) > 0.5
        w = int(0.5 * FS)
        pad = np.convolve(p.astype(float), np.ones(2 * w + 1), "same") > 0
        g["ho"] = g["eng"] & ~pad
    else:
        g["ho"] = None
    return g


def runs_of(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


G = {t: load(t) for t in ("r70_v293", "r6c")}
STRATA = [("r70 hands-off", "V293", "r70_v293", "ho"),
          ("r70 all-engaged", "V293", "r70_v293", "eng"),
          ("r6c all-engaged", "V282", "r6c", "eng")]

pr("=" * 110)
pr("V293 -- THE SNAP STATISTICS  (the operator's primary symptom, in the requested form)")
pr("=" * 110)
pr("\n    r70 hands-off exposure: %.0f s of %.0f s engaged (steeringPressed False, +-0.5 s buffer)."
   % (G["r70_v293"]["ho"].sum() * DT, G["r70_v293"]["eng"].sum() * DT))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 110)
pr("K1(a). |WHEEL RATE| DISTRIBUTION -- bimodal or continuous?  bins in deg/s.")
pr("=" * 110)
EDG = np.array([0, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 1e9])
pr("\n    %-17s %-7s %7s" % ("stratum", "band", "sec") +
   "".join("%8s" % ("<%g" % x) for x in EDG[1:8]) + "%11s %11s" % ("P(rate=0)", "P(<1 dps)"))
for lab, build, tag, mk in STRATA:
    g = G[tag]
    m0 = g[mk]
    if m0 is None:
        continue
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m0 & (g["v"] >= lo) & (g["v"] < hi)
        if s.sum() < 500:
            continue
        r = np.abs(g["rate"][s])
        h, _ = np.histogram(r, bins=EDG)
        h = h / h.sum()
        pr("    %-17s %-7s %7.0f" % (lab, BNAME[k], s.sum() * DT)
           + "".join("%8.3f" % x for x in h[:7])
           + "%11.3f %11.3f" % (float(np.mean(r < 1e-9)), float(np.mean(r < 1.0))))
pr("\n    The distribution is CONTINUOUS on every route: there is no separated slip lobe.  The")
pr("    difference between builds is the WEIGHT of the low-rate mass, not its shape (v293_ident_h.py")
pr("    measured P(rate=0)/P(0,0.25] = 0.556-0.641 on EVERY route and band).")

pr("\n    (a2) 🛑 THE CONDITIONED VERSION -- the fraction of frames with |rate| < 1 deg/s WHILE THE")
pr("    COMMAND IS CHANGING (|d cmd| over the previous 0.2 s > 20 counts, i.e. the loop is asking")
pr("    for motion).  A wheel that is still because nothing is pushing it is not a snap; this is.")
pr("    %-17s %-7s %9s %14s %16s" % ("stratum", "band", "sec", "P(<1 dps)", "P(<1 dps | cmd moving)"))
W2 = 20
for lab, build, tag, mk in STRATA:
    g = G[tag]
    m0 = g[mk]
    if m0 is None:
        continue
    dc = np.zeros(len(g["cmd"]))
    dc[W2:] = np.abs(g["cmd"][W2:] - g["cmd"][:-W2])
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m0 & (g["v"] >= lo) & (g["v"] < hi)
        if s.sum() < 500:
            continue
        q = s & (dc > 20)
        if q.sum() < 200:
            continue
        pr("    %-17s %-7s %9.0f %14.3f %16.3f"
           % (lab, BNAME[k], s.sum() * DT, float(np.mean(np.abs(g["rate"][s]) < 1.0)),
              float(np.mean(np.abs(g["rate"][q]) < 1.0))))
        RES.setdefault("cond", {}).setdefault(lab, {})[BNAME[k]] = dict(
            all=float(np.mean(np.abs(g["rate"][s]) < 1.0)),
            cmdmoving=float(np.mean(np.abs(g["rate"][q]) < 1.0)), sec=s.sum() * DT)

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 110)
pr("K1(b,c). DWELLS >= 0.20 s AND THE SNAP THAT ENDS THEM, like-for-like against V282")
pr("    dwell = |rate| < %.2f deg/s for >= 0.20 s; snap = the ANGLE CHANGE from the end of one" % DWELL_TH)
pr("    dwell to the start of the next.  Events per minute of the stratum's own time.")
pr("    🛑 The dwell test is run on a 0.10 s MOVING MEAN of |rate|, not the raw field.  A hard")
pr("    threshold on the raw 100 Hz rate is crossed by noise every few frames and finds almost")
pr("    nothing (13 dwells on r70 and ZERO on r6c -- an artefact of the detector, not a result).")
pr("    The smoothed version is what 'the wheel is not moving' means physically, and it is applied")
pr("    identically to both routes.  A threshold sweep follows, so the answer is not one choice.")
pr("=" * 110)
pr("\n    %-17s %-7s %8s %8s %10s %10s %10s %10s %10s"
   % ("stratum", "band", "sec", "dwells", "per min", "dwell p50", "dwell p90", "snap p50", "snap p90"))
EV = {}
for lab, build, tag, mk in STRATA:
    g = G[tag]
    m0 = g[mk]
    if m0 is None:
        continue
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m0 & (g["v"] >= lo) & (g["v"] < hi)
        segs = runs_of(s, int(2 * FS))
        if not segs:
            continue
        dl, sn, tot, ev = [], [], 0, []
        for (a, b) in segs:
            r = g["rate"][a:b]; an = g["ang"][a:b]; cm = g["cmd"][a:b]
            rs = np.convolve(np.abs(r), np.ones(10) / 10.0, "same")
            dws = runs_of(rs < DWELL_TH, DWELL_MIN)
            tot += (b - a)
            for q in range(len(dws)):
                i0, j0 = dws[q]
                dl.append((j0 - i0) * DT)
                if q + 1 < len(dws):
                    i1 = dws[q + 1][0]
                    if i1 > j0:
                        snap = abs(an[i1] - an[j0 - 1])
                        sn.append(snap)
                        ev.append(dict(seg=(a, b), i0=i0, j0=j0, i1=i1, snap=snap,
                                       dcmd_dwell=abs(cm[j0 - 1] - cm[i0]),
                                       dcmd_slip=abs(cm[min(i1, len(cm) - 1)] - cm[j0 - 1]),
                                       cmd=cm[max(0, j0 - 20):min(len(cm), i1 + 20)],
                                       ang=an[max(0, j0 - 20):min(len(an), i1 + 20)]))
        if tot < 500 or len(dl) < 5:
            continue
        pr("    %-17s %-7s %8.0f %8d %10.2f %10.3f %10.3f %10.3f %10.3f"
           % (lab, BNAME[k], tot * DT, len(dl), 60.0 * len(dl) / (tot * DT),
              np.percentile(dl, 50), np.percentile(dl, 90),
              np.percentile(sn, 50) if sn else np.nan,
              np.percentile(sn, 90) if sn else np.nan))
        EV.setdefault(lab, {})[BNAME[k]] = ev
        RES.setdefault("dwell", {}).setdefault(lab, {})[BNAME[k]] = dict(
            sec=tot * DT, n=len(dl), per_min=60.0 * len(dl) / (tot * DT),
            dwell_p50=float(np.percentile(dl, 50)), dwell_p90=float(np.percentile(dl, 90)),
            snap_p50=float(np.percentile(sn, 50)) if sn else None,
            snap_p90=float(np.percentile(sn, 90)) if sn else None)

pr("\n    THRESHOLD SWEEP -- dwells per minute, so the contrast does not rest on one threshold:")
pr("    %-17s %-7s" % ("stratum", "band")
   + "".join("%12s" % ("th %.2f" % t) for t in (0.25, 0.5, 1.0, 2.0)))
for lab, build, tag, mk in STRATA:
    g = G[tag]
    m0 = g[mk]
    if m0 is None:
        continue
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m0 & (g["v"] >= lo) & (g["v"] < hi)
        segs = runs_of(s, int(2 * FS))
        if not segs:
            continue
        row, tot = [], sum(b - a for a, b in segs)
        for th in (0.25, 0.5, 1.0, 2.0):
            n = 0
            for (a, b) in segs:
                rs = np.convolve(np.abs(g["rate"][a:b]), np.ones(10) / 10.0, "same")
                n += len(runs_of(rs < th, DWELL_MIN))
            row.append(60.0 * n / (tot * DT))
        pr("    %-17s %-7s" % (lab, BNAME[k]) + "".join("%12.2f" % x for x in row))
        RES.setdefault("sweep", {}).setdefault(lab, {})[BNAME[k]] = row

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 110)
pr("K1(d). 🛑 IS IT STICK-SLIP DRIVEN THROUGH THE COULOMB BAND?")
pr("    The test the orchestrator specified: does the 0xE4 command move by more than 2F across the")
pr("    dwell, where F = %.3f of full scale = %.0f counts, so 2F = %.0f counts?"
   % (F_TORQUE, F_CNT, 2 * F_CNT))
pr("    If the loop were winding through the friction band, |d cmd| across the dwell would be")
pr("    COMPARABLE TO OR LARGER THAN 2F, and it would be larger than on the reference build.")
pr("=" * 110)
pr("\n    %-17s %-7s %7s %14s %14s %14s %16s"
   % ("stratum", "band", "n", "|dcmd| dwell", "as frac of 2F", "P(> 2F)", "|dcmd| in slip"))
for lab in EV:
    for bn in EV[lab]:
        ev = EV[lab][bn]
        if len(ev) < 5:
            continue
        dd = np.array([e["dcmd_dwell"] for e in ev])
        ds = np.array([e["dcmd_slip"] for e in ev])
        pr("    %-17s %-7s %7d %14.1f %14.3f %14.3f %16.1f"
           % (lab, bn, len(ev), np.median(dd), np.median(dd) / (2 * F_CNT),
              float(np.mean(dd > 2 * F_CNT)), np.median(ds)))
        RES.setdefault("band_cross", {}).setdefault(lab, {})[bn] = dict(
            n=len(ev), dcmd_dwell=float(np.median(dd)), frac2F=float(np.median(dd) / (2 * F_CNT)),
            p_gt=float(np.mean(dd > 2 * F_CNT)), dcmd_slip=float(np.median(ds)))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 110)
pr("K1(e). IS THE COMMAND SMOOTH ACROSS THE SNAP?  -- rules out a stepping 0xE4")
pr("    For each snap, over a window from 0.2 s before the slip to 0.2 s after it: the largest")
pr("    single-frame command step, and the ratio of that to the window's rms step.  A stepping")
pr("    command would show a crest ratio far above the reference's; a smooth one would not.")
pr("=" * 110)
pr("\n    %-17s %-7s %7s %14s %14s %16s"
   % ("stratum", "band", "n", "max |dcmd|/fr", "rms |dcmd|/fr", "crest max/rms"))
for lab in EV:
    for bn in EV[lab]:
        ev = EV[lab][bn]
        if len(ev) < 5:
            continue
        mx, rm, cr = [], [], []
        for e in ev:
            d = np.abs(np.diff(e["cmd"]))
            if len(d) < 5:
                continue
            mx.append(d.max()); rm.append(np.sqrt(np.mean(d ** 2)))
            cr.append(d.max() / max(np.sqrt(np.mean(d ** 2)), 1e-9))
        if len(cr) < 5:
            continue
        pr("    %-17s %-7s %7d %14.1f %14.1f %16.2f"
           % (lab, bn, len(cr), np.median(mx), np.median(rm), np.median(cr)))
        RES.setdefault("crest", {}).setdefault(lab, {})[bn] = dict(
            n=len(cr), maxd=float(np.median(mx)), rmsd=float(np.median(rm)),
            crest=float(np.median(cr)))

with open(os.path.join(L.SCRATCH, "v293_ident_k.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_k.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_k.txt / .json")
