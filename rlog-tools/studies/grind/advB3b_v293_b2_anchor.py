# -*- coding: utf-8 -*-
"""advB3b_v293_b2_anchor.py -- ADVERSARY B, criterion B2: the 18-22 Hz ring, and the CALIBRATION.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY.

B2 (verbatim): "The 18-22 Hz ring on the replayed grinding windows (r39, r6c) not <= x0.50 of
V282's AFTER calibrating the predictor on V292 (replay predicted x0.55-0.63, the wire read x0.4-0.8
in the strong-turn stratum) -- state the calibration and apply it."

THREE THINGS THIS DOES THAT THE DESIGN'S s2/s7 DO NOT:
 1. re-derives the on-car anchor INDEPENDENTLY of v293_s7 (own band filter, own engaged mask, own
    run pooling), so the anchor is not one script's artefact;
 2. states the V292 calibration in BOTH forms the record supports and applies each one explicitly,
    instead of quoting the uncalibrated point prediction;
 3. adds the calibration that the OPEN-LOOP case itself supplies: V282's own engaged-vs-disengaged
    contrast IS a measurement of "this car with the LKAS loop open", so the sensitivity method can
    be scored against a measured open-loop answer instead of against a closed-loop one.

Run: python advB3b_v293_b2_anchor.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\advB3b"
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, CPD = 100.0, 8.0
BANDS = dict(b59=(5.0, 9.0), b913=(9.0, 13.0), b1317=(13.0, 17.0), b1822=(18.0, 22.0), b2230=(22.0, 30.0))
OUT = []
RES = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band_rms(x, lo, hi, fs=FS):
    """rms of x inside [lo, hi] by a zero-phase Butterworth, x sqrt(2) to an amplitude."""
    from scipy.signal import butter, filtfilt
    x = np.asarray(x, float)
    if len(x) < 40:
        return np.nan
    b, a = butter(3, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    y = filtfilt(b, a, x - x.mean())
    return float(np.sqrt(np.mean(y ** 2)) * np.sqrt(2.0))


def runs(mask, min_len):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            if (j - i + 1) >= min_len:
                out.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    return out


def pooled_band(x, mask, lo, hi, min_s=2.56):
    """length-weighted pooling of band amplitude over contiguous runs of `mask`."""
    segs = runs(mask, int(min_s * FS))
    num, den = 0.0, 0.0
    for (a, b) in segs:
        v = band_rms(x[a:b], lo, hi)
        if np.isfinite(v):
            w = b - a
            num += w * v * v
            den += w
    return (np.sqrt(num / den) if den > 0 else np.nan), den / FS, len(segs)


def main():
    pr("=" * 122)
    pr("ADVERSARY B -- B2: the 18-22 Hz ring, the ON-CAR ANCHOR re-derived, and THE CALIBRATION")
    pr("agent advB3b, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 122)
    pr("Channel: 0x18F wheel RATE, raw wire counts (CPD 8 counts per deg/s), 100 Hz.")
    pr("Engaged = the kit's own lateral-engaged mask (0xE4 STEER_REQUEST & 0x18F SCA).")
    pr("Band amplitude = zero-phase Butterworth band rms x sqrt(2), pooled length-weighted over")
    pr("contiguous runs of >= 2.56 s.  This is an INDEPENDENT implementation of v293_s7's measure.")
    pr()

    tab = {}
    for tag in ("r39", "r6c", "r35"):
        try:
            g = C20.load(tag)
        except Exception as e:                                     # noqa: BLE001
            pr("  !! %s unavailable: %s" % (tag, e))
            continue
        w = np.asarray(g["wire"], float)
        eng = np.asarray(g["eng"], bool)
        dis = ~eng
        v = np.asarray(g["v"], float) if "v" in g else np.full(len(w), np.nan)
        pr("-" * 122)
        pr("  %s : %.0f s total, engaged %.0f s, disengaged %.0f s ; engaged v p50 %.1f m/s, "
           "disengaged v p50 %.1f m/s"
           % (tag, len(w) / FS, eng.sum() / FS, dis.sum() / FS,
              np.nanmedian(v[eng]) if eng.any() else np.nan,
              np.nanmedian(v[dis]) if dis.any() else np.nan))
        pr("    %-10s %10s %10s %10s %12s" % ("band Hz", "engaged", "diseng", "eng/dis", "1/(eng/dis)"))
        row = {}
        for nm, (lo, hi) in BANDS.items():
            ae, te, ne = pooled_band(w, eng, lo, hi)
            ad, td, nd = pooled_band(w, dis, lo, hi)
            r = ae / ad if (np.isfinite(ae) and np.isfinite(ad) and ad > 0) else np.nan
            row[nm] = dict(eng=ae, dis=ad, ratio=r, inv=(1.0 / r if r and np.isfinite(r) else np.nan),
                           eng_s=te, dis_s=td, n_eng=ne, n_dis=nd)
            pr("    %-10s %10.2f %10.2f %10.3f %12.3f" % ("%g-%g" % (lo, hi), ae, ad, r, 1.0 / r if r else np.nan))
        # speed-matched control
        pr("    SPEED-MATCHED (disengaged reference is mostly at rest -- the flightread caveat)")
        pr("    %-10s %10s %10s %10s" % ("band Hz", "0-3 m/s", "3-8 m/s", "8-15 m/s"))
        for nm, (lo, hi) in BANDS.items():
            cells = []
            for (v0, v1) in ((0.0, 3.0), (3.0, 8.0), (8.0, 15.0)):
                me = eng & (v >= v0) & (v < v1)
                md_ = dis & (v >= v0) & (v < v1)
                ae, te, _ = pooled_band(w, me, lo, hi)
                ad, td, _ = pooled_band(w, md_, lo, hi)
                cells.append(ae / ad if (np.isfinite(ae) and np.isfinite(ad) and ad > 0 and te > 5 and td > 5)
                             else np.nan)
            row[nm]["speed"] = cells
            pr("    %-10s %10s %10s %10s" % ("%g-%g" % (lo, hi),
                                             *["%10.3f" % c if np.isfinite(c) else "         -" for c in cells]))
        tab[tag] = row
    RES["anchor"] = {k: {b: {kk: (None if (isinstance(vv, float) and not np.isfinite(vv)) else vv)
                             for kk, vv in d.items() if kk != "speed"} for b, d in r.items()}
                     for k, r in tab.items()}

    # --------------------------------------------------------------------------------------------
    pr()
    pr("=" * 122)
    pr("THE CALIBRATION -- stated, then applied.  Two are available and they DISAGREE by ~2x.")
    pr("=" * 122)
    pr("CALIBRATION 1 -- V292, the prereg's own instruction.  [EVIDENCE: V292-REPLAY-PREDICTION line")
    pr("  198/225 predicted wheel ring x0.55-0.63; V292-FLIGHT-READ section 4 measured the loop's own")
    pr("  contribution (engaged/disengaged, ratioed to r6c) at x1.20-2.00, speed-matched x1.18-2.21.]")
    lo1, hi1 = 1.20 / 0.63, 2.00 / 0.55
    pr("  => the predictor under-read V292 by a factor in [%.2f, %.2f]." % (lo1, hi1))
    pr()
    pr("CALIBRATION 2 -- the OPEN-LOOP case itself, which V292 is not.  V282's own engaged-vs-")
    pr("  disengaged contrast IS a measurement of this car with the LKAS loop open; the replay's own")
    pr("  second method (s2 TASK 2.0, 1/|S_V282(20.3 Hz)|) predicts the same quantity, so the two can")
    pr("  be divided.  Sensitivity median 0.16 [p10 0.12, p90 0.28].")
    sens = 0.16
    for tag in tab:
        inv = tab[tag]["b1822"]["inv"]
        if np.isfinite(inv):
            pr("    %-4s measured open-loop ring ratio %.3f  /  predicted %.2f  =>  under-read x%.2f"
               % (tag, inv, sens, inv / sens))
    pr()
    pr("APPLYING EACH, to the design's replayed 18-22 Hz WHEEL ratios (s2 POOLED: r39 x0.285 at every")
    pr("arm, r6c x0.403).  The prereg's gate is <= x0.50.")
    pr("  %-28s %10s %10s %10s" % ("calibration", "factor", "r39", "r6c"))
    pr("  %-28s %10s %10.3f %10.3f" % ("none (the point prediction)", "x1.00", 0.285, 0.403))
    for nm, (a, b) in (("1: V292, low end", (lo1, lo1)), ("1: V292, high end", (hi1, hi1))):
        pr("  %-28s %10.2f %10.3f %10.3f" % (nm, a, 0.285 * a, 0.403 * b))
    ol = [tab[t]["b1822"]["inv"] / sens for t in tab if np.isfinite(tab[t]["b1822"]["inv"])]
    if ol:
        pr("  %-28s %10.2f %10.3f %10.3f" % ("2: open-loop, mean", float(np.mean(ol)),
                                             0.285 * float(np.mean(ol)), 0.403 * float(np.mean(ol))))
    pr()
    pr("AND THE ANCHOR ITSELF, which needs no predictor at all: the measured 1/(eng/dis) at 18-22 Hz.")
    pr("  V293's engaged r24 arm (0xC6446 = 2048) EQUALS the disengaged arm (0xC6440 = 2048) on every")
    pr("  image, so the r24 lane is bit-identical between 'V293 engaged' and 'V282 disengaged'.")
    for t in tab:
        d = tab[t]["b1822"]
        pr("    %-4s  1/(eng/dis) = %.3f   (speed-matched cells %s)"
           % (t, d["inv"], ", ".join("%.2f" % c if np.isfinite(c) else "-" for c in d["speed"])))
    json.dump(RES, open(os.path.join(OUTDIR, "b2_anchor.json"), "w"), indent=1)
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b2_anchor.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
