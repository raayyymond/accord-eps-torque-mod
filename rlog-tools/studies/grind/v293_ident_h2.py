# -*- coding: utf-8 -*-
"""v293_ident_h2.py -- THE RATCHET, part 2: a SCALE-FREE measure of "snaps between angles rather than
smoothly moving", and an ACTIVITY-MATCHED comparison.  Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

WHY THIS SCRIPT EXISTS.  v293_ident_h.py established that route 70 spends far more time with the wheel
still AND has a higher rms wheel rate than the V282 references -- i.e. the motion is concentrated into
fewer, faster bursts.  But two of its statistics are confounded and must not be quoted alone:
  * P(rate == 0) rises on V293, but the SPIKE RATIO P(0)/P(0,0.25] is 0.56-0.64 on EVERY route and
    band.  So there is NO excess spike at exactly zero relative to its own neighbourhood: the
    classic stiction "delta at zero" is NOT present.  What changed is the whole low-rate mass.
  * route 70's rms wheel rate is 2-3x the references' in the same speed band, because the drive
    contains more steering activity (roundabouts).  A raw comparison is therefore not like-for-like.

THE MEASURE USED HERE IS SCALE-FREE: of all the steering travel in a window, what fraction is
delivered in the fastest 10 % of its frames?  A wheel that moves smoothly spreads its travel evenly
(10 % of frames carry ~25-30 % of the travel for a smooth band-limited signal); a wheel that snaps
delivers most of its travel in a few frames.  It does not care how fast the wheel moves overall, and
it is dimensionless, so the roundabout confound cancels.

Windows are then MATCHED ON ACTIVITY (binned by their own rms |rate|) so the V293-vs-V282 contrast is
between windows doing the same amount of steering.
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
ROUTES = [("r70_v293", "V293"), ("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3")]
BANDS = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
BNAME = ["0-5", "5-10", "10-20", ">20"]
NPER, STEP = 400, 100          # 4 s windows, 1 s hop


def load(tag):
    d = dict(np.load(os.path.join(V280, tag + ".npz")))
    t0 = d["t18"][0]
    t1 = min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1])
    ta = np.arange(0.0, t1 - t0, DT) + t0
    g = {}
    g["rate"] = L.zoh(ta, d["t18"], d["rate"]) / CPD
    g["ang"] = L.zoh(ta, d["t14"], d["ang"])
    g["cmd"] = L.zoh(ta, d["te4"], d["cmd"])
    g["v"] = L.zoh(ta, d["tcs"], d["vego"])
    g["eng"] = (L.zoh(ta, d["te4"], d["req"]) > 0.5) & (L.zoh(ta, d["t18"], d["sca"]) > 0.5)
    g["press"] = L.zoh(ta, d["tcs"], d["cs_press"]) if "cs_press" in d else None
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


def conc_mag(a, frac=0.10):
    """fraction of the total of |a| carried by the largest `frac` of frames.  Use this on the RATE
    itself: it is the same quantity concentration(angle) tries to measure, but it is read from the
    0.125 deg/s rate field instead of the 0.1 deg angle field, so it is NOT quantiser-limited."""
    a = np.abs(np.asarray(a, float))
    tot = a.sum()
    if tot <= 0 or len(a) < 20:
        return np.nan
    k = max(1, int(round(frac * len(a))))
    return float(np.sort(a)[-k:].sum() / tot)


def concentration(x, frac=0.10):
    """fraction of the total |increment| delivered by the largest `frac` of frames."""
    a = np.abs(np.diff(x))
    tot = a.sum()
    if tot <= 0 or len(a) < 20:
        return np.nan
    k = max(1, int(round(frac * len(a))))
    return float(np.sort(a)[-k:].sum() / tot)


pr("=" * 108)
pr("V293 -- THE RATCHET, part 2: a scale-free 'snappiness' measure, activity-matched")
pr("=" * 108)
pr("\n    SMOOTHNESS BASELINES, computed on synthetic signals of the same length and sample rate,")
pr("    so the numbers below have a scale [EVIDENCE -- construction]:")
rng = np.random.default_rng(7)
for nm, sig in (("band-limited noise 0-2 Hz", None), ("pure 1 Hz sine", None),
                ("a perfect staircase (10 equal steps)", None)):
    pass
t = np.arange(NPER) * DT
sine = np.sin(2 * np.pi * 1.0 * t)
w = rng.standard_normal(NPER)
from scipy import signal as _sg  # noqa: E402
bl = _sg.sosfiltfilt(_sg.butter(4, 2.0, "lowpass", fs=FS, output="sos"), w)
stair = np.repeat(np.arange(10, dtype=float), NPER // 10)[:NPER]
for nm, x in (("pure 1 Hz sine", sine), ("band-limited noise, 0-2 Hz", bl),
              ("a 10-step staircase", stair)):
    pr("      %-34s conc of |d/dt| (top 10%% of frames) = %.3f   conc of the signal itself = %.3f"
       % (nm, concentration(x), conc_mag(np.diff(x))))

pr("\n" + "=" * 108)
pr("H8. SNAPPINESS of the steering ANGLE, per route and speed band, on laterally engaged frames")
pr("    (4 s windows, 1 s hop, each window wholly inside one engaged in-band run)")
pr("=" * 108)
G = {}
WIN = {}
for tag, build in ROUTES:
    try:
        G[tag] = load(tag)
    except Exception as ex:
        pr("    %s: %s" % (tag, str(ex)[:70])); continue
    g = G[tag]
    WIN[tag] = []
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        m = g["eng"] & (g["v"] >= lo) & (g["v"] < hi)
        for (a, b) in runs_of(m, NPER):
            for s0 in range(a, b - NPER + 1, STEP):
                sl = slice(s0, s0 + NPER)
                WIN[tag].append(dict(k=k, s0=s0,
                                     conc_ang=concentration(g["ang"][sl]),
                                     conc_cmd=concentration(g["cmd"][sl]),
                                     conc_rate=conc_mag(g["rate"][sl]),
                                     conc_cmdm=conc_mag(np.diff(g["cmd"][sl])),
                                     rms=float(np.sqrt(np.mean(g["rate"][sl] ** 2))),
                                     act=float(np.abs(np.diff(g["ang"][sl])).sum())))

pr("\n    %-10s %-8s %-8s %7s %14s %14s %14s %12s"
   % ("route", "build", "band", "n win", "ANGLE conc", "cmd conc", "RATE-MAG conc", "rms rate"))
for tag, build in ROUTES:
    if tag not in WIN:
        continue
    for k in range(len(BANDS)):
        W = [w for w in WIN[tag] if w["k"] == k and np.isfinite(w["conc_ang"])]
        if len(W) < 8:
            continue
        pr("    %-10s %-8s %-8s %7d %14.3f %14.3f %14.3f %12.2f"
           % (tag, build, BNAME[k], len(W),
              float(np.median([w["conc_ang"] for w in W])),
              float(np.median([w["conc_cmd"] for w in W])),
              float(np.median([w["conc_rate"] for w in W])),
              float(np.median([w["rms"] for w in W]))))
        RES.setdefault("conc", {}).setdefault(tag, {})[BNAME[k]] = dict(
            n=len(W), ang=float(np.median([w["conc_ang"] for w in W])),
            cmd=float(np.median([w["conc_cmd"] for w in W])),
            rate=float(np.median([w["conc_rate"] for w in W])),
            rms=float(np.median([w["rms"] for w in W])))

pr("\n" + "=" * 108)
pr("H9. ACTIVITY-MATCHED -- the same measure, with windows binned by their OWN rms wheel rate, so")
pr("    the comparison is between windows doing the same amount of steering.  This removes the")
pr("    roundabout confound (route 70's rms rate is 2-3x the references' in the same speed band).")
pr("=" * 108)
allrms = np.concatenate([[w["rms"] for w in WIN[t2]] for t2, _ in ROUTES if t2 in WIN])
EDG = [0] + [float(np.percentile(allrms, q)) for q in (25, 50, 75, 90)] + [1e9]
LAB = ["q0-25", "q25-50", "q50-75", "q75-90", "q90+"]
pr("\n    rms-rate bins (deg/s): " + " ".join("%s<%.2f" % (LAB[i], EDG[i + 1]) for i in range(4)))
pr("\n    🛑 THE ANGLE metric is QUANTISER-LIMITED below ~10 deg/s: the 0x14A LSB is 0.1 deg, so at")
pr("    1 deg/s the angle ticks only every 10th frame and reads 1.000 whatever the plant does.  The")
pr("    quantiser-safe version is the concentration of the RATE MAGNITUDE (0x18F, 0.125 deg/s LSB),")
pr("    which measures exactly the same quantity.  READ THE RATE TABLE; the angle table follows for")
pr("    completeness only.")
pr("\n    RATE-MAGNITUDE concentration -- the fraction of ALL wheel travel delivered in the fastest")
pr("    10 % of frames.  Baselines: a pure sine 0.157, band-limited noise 0.278, a staircase 1.000.")
pr("    %-10s %-8s" % ("route", "build") + "".join("%12s" % x for x in LAB) + "%10s" % "n total")
for tag, build in ROUTES:
    if tag not in WIN:
        continue
    row, ns = [], 0
    for i in range(5):
        W = [w for w in WIN[tag] if EDG[i] <= w["rms"] < EDG[i + 1] and np.isfinite(w["conc_rate"])]
        ns += len(W)
        row.append(float(np.median([w["conc_rate"] for w in W])) if len(W) >= 8 else np.nan)
    pr("    %-10s %-8s" % (tag, build) + "".join("%12.3f" % x for x in row) + "%10d" % ns)
    RES.setdefault("matched_rate", {})[tag] = row

pr("\n    ANGLE concentration (quantiser-limited; for completeness only):")
pr("    %-10s %-8s" % ("route", "build") + "".join("%12s" % x for x in LAB) + "%10s" % "n total")
for tag, build in ROUTES:
    if tag not in WIN:
        continue
    row, ns = [], 0
    for i in range(5):
        W = [w for w in WIN[tag] if EDG[i] <= w["rms"] < EDG[i + 1] and np.isfinite(w["conc_ang"])]
        ns += len(W)
        row.append(float(np.median([w["conc_ang"] for w in W])) if len(W) >= 8 else np.nan)
    pr("    %-10s %-8s" % (tag, build) + "".join("%12.3f" % x for x in row) + "%10d" % ns)
    RES.setdefault("matched", {})[tag] = row

pr("\n    the same for the 0xE4 COMMAND -- the control that says whether the snappiness is inherited")
pr("    from openpilot's command or generated by the car:")
pr("    %-10s %-8s" % ("route", "build") + "".join("%12s" % x for x in LAB))
for tag, build in ROUTES:
    if tag not in WIN:
        continue
    row = []
    for i in range(5):
        W = [w for w in WIN[tag] if EDG[i] <= w["rms"] < EDG[i + 1] and np.isfinite(w["conc_cmd"])]
        row.append(float(np.median([w["conc_cmd"] for w in W])) if len(W) >= 8 else np.nan)
    pr("    %-10s %-8s" % (tag, build) + "".join("%12.3f" % x for x in row))
    RES.setdefault("matched_cmd", {})[tag] = row

pr("\n    and the ANGLE-minus-COMMAND difference, per cell -- how much snappiness the CAR ADDS:")
pr("    %-10s %-8s" % ("route", "build") + "".join("%12s" % x for x in LAB))
for tag, build in ROUTES:
    if tag not in RES.get("matched", {}):
        continue
    a = np.array(RES["matched"][tag], float); b = np.array(RES["matched_cmd"][tag], float)
    pr("    %-10s %-8s" % (tag, build) + "".join("%12.3f" % x for x in (a - b)))

pr("\n" + "=" * 108)
pr("H10. DOES A HAND ON THE WHEEL SUPPRESS IT?  (r70 only -- steeringPressed exists there)")
pr("=" * 108)
g = G["r70_v293"]
pr("\n    %-16s %8s %14s %14s %12s" % ("stratum", "n win", "RATE-MAG conc", "cmd conc", "rms rate"))
NP2 = 200      # 2 s, so the hands-ON stratum (51.6 s in 175 short episodes) is populated at all
for nm, extra in (("hands-off", g["press"] < 0.5), ("hands-ON", g["press"] > 0.5)):
    rows = []
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        m = g["eng"] & extra & (g["v"] >= lo) & (g["v"] < hi)
        for (a, b) in runs_of(m, NP2):
            for s0 in range(a, b - NP2 + 1, NP2 // 2):
                sl = slice(s0, s0 + NP2)
                c = conc_mag(g["rate"][sl])
                if np.isfinite(c):
                    rows.append((c, concentration(g["cmd"][sl]),
                                 float(np.sqrt(np.mean(g["rate"][sl] ** 2)))))
    if len(rows) < 6:
        pr("    %-16s %8d  (too few windows)" % (nm, len(rows))); continue
    A = np.array(rows)
    pr("    %-16s %8d %14.3f %14.3f %12.2f"
       % (nm, len(A), np.median(A[:, 0]), np.nanmedian(A[:, 1]), np.median(A[:, 2])))

with open(os.path.join(L.SCRATCH, "v293_ident_h2.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_h2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_h2.txt / .json")
