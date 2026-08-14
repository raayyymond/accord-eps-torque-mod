#!/usr/bin/env python3
r"""⭐ SETTLING THE dCMD/dt QUESTION WITHOUT A CONTROL BAND, AND THE HANDS-ON STRATIFICATION.

WHY THIS FILE EXISTS.  `dcmd_dt_hypothesis.py` returned an answer that DEPENDS ON THE CONTROL BAND:

    control band 20-24 Hz : pooled partial rho -0.0176   0 of 8 routes support the hypothesis
    control band 32-38 Hz : partial rho +0.035..+0.112,  POSITIVE on 5 of 6 well-powered routes,
                            3 of 6 clearing every control (r77 +0.112 [+0.041,+0.174],
                            r78 +0.093 [+0.011,+0.192], r79 +0.105 [+0.015,+0.190])

🛑 THAT DISAGREEMENT IS ITSELF A FINDING AND IT MUST NOT BE RESOLVED BY PICKING THE BAND I LIKE.
   Two facts decide which control is contaminated:
   1. **20-24 Hz sits INSIDE the kit's own engaged-conditional band.**  V68 measured the
      engaged-conditional part of the lane-change vibration at **18-28 Hz**; the recorded grind
      bands are 18-22 and 26-31.  A "control" band that itself responds to engagement
      OVER-SUBTRACTS and biases the contrast toward zero.
   2. **32-38 Hz is a REAL band on this channel, not an alias.**  CAN 0x18F is measured at
      **100.8 Hz** on every route (r85 100.80, r77 100.86, r78 100.83, r79 100.85, r7e 100.83,
      r7f 100.82), so Nyquist is ~50 Hz.  The kit's "35-45 Hz IS VOID AS A CONTROL BAND" memory
      is about the **50 Hz CAN-427 lane**, where 35-45 Hz IS an alias.  It does not transfer to
      0x18F.
   Direct evidence of the contamination: rho(R, 20-24 Hz) = +0.23..+0.49 versus
   rho(R, 32-38 Hz) = +0.09..+0.35.  The nearer band responds substantially more.

⇒ THE FIX IS TO STOP CHOOSING.  Compute rho(R, log RMS(f)) in NARROW BANDS ACROSS THE WHOLE
  SPECTRUM.  If the 6-9 Hz region carries a PEAK above a smooth background, the command's
  derivative selectively drives it.  If the curve is flat or monotone, it is broadband excitation.
  **No control band is chosen, so none can be chosen wrongly.**

PART 2 -- THE HANDS-ON DEFECT, which I had not applied.  Reported this session and measured twice:
  the relevant lane is ~16.9x quieter in-band HANDS-ON, engaged frames are largely hands-off, and a
  whole-episode statistic scored a real 3.188x effect as 1.017.  My windows are 1.28 s so I am not
  computing whole-episode statistics, but I had NOT stratified by grip, and this kit has separately
  measured that DRIVER GRIP DAMPS the 6-9 Hz mode (-0.720 [-0.918,-0.500] vs control -0.266).
  Grip is therefore a live confound on every number above.  Stratified here.

Usage:  python dcmd_dt_spectrum.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

import dcmd_dt_hypothesis as H          # noqa: E402  the SAME regressor, episodes and conditioning
from v97_r80_vs_v96 import band_rms     # noqa: E402

OUT = AN / "_v100"
BIG = ["r85", "r77", "r78", "r79", "r7e", "r7f"]
# narrow bands, 3 Hz wide, 1.5 Hz hop, from 2 Hz to the top of the usable range
EDGES = [(f, f + 3.0) for f in np.arange(2.0, 42.1, 1.5)]


def spectrum():
    """rho(R, log RMS(band)) and the PARTIAL, across the whole spectrum.  No control band."""
    print("=" * 100)
    print("  PART 1 -- rho(|dCMD/dt|, log RMS(f)) ACROSS THE SPECTRUM.  NO CONTROL BAND CHOSEN.")
    print("=" * 100)
    res = {"bands": [f"{a:.1f}-{b:.1f}" for a, b in EDGES], "routes": {}}
    curves, pcurves = {}, {}
    for stem in BIG:
        d = H.load(stem)
        rows, eps = H.windows_for(d)
        R, ep, _yr, _yc, _y, lr, lv = H.arrays(rows, "20-24")
        sig = d["tq"]
        M = np.zeros((len(R), len(EDGES)))
        k = 0
        for a_, b_ in eps:
            for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
                sl = slice(a_ + s, a_ + s + H.NPERSEG)
                for j, (lo, hi) in enumerate(EDGES):
                    M[k, j] = band_rms(sig[sl], H.FS, lo, hi, H.NPERSEG)
                k += 1
        raw = np.array([float(stats.spearmanr(R, np.log(M[:, j] + 1e-12)).statistic)
                        for j in range(len(EDGES))])
        par = np.array([H.partial_spearman(np.log(M[:, j] + 1e-12), R, [lr, lv])
                        for j in range(len(EDGES))])
        curves[stem], pcurves[stem] = raw, par
        res["routes"][stem] = dict(raw=raw.tolist(), partial=par.tolist(), n=len(R))
        print(f"  {stem} done ({len(R):,} windows)")

    Craw = np.vstack([curves[s] for s in BIG])
    Cpar = np.vstack([pcurves[s] for s in BIG])
    mraw, mpar = Craw.mean(0), Cpar.mean(0)
    se = Cpar.std(0, ddof=1) / np.sqrt(len(BIG))
    res["pooled_raw"] = mraw.tolist()
    res["pooled_partial"] = mpar.tolist()
    res["pooled_partial_se"] = se.tolist()

    print(f"\n  {'band Hz':>11s} {'RAW rho (mean)':>15s} {'PARTIAL rho (mean)':>19s} "
          f"{'+-1.96 se':>11s} {'routes >0':>10s}")
    for j, (lo, hi) in enumerate(EDGES):
        star = ""
        if 6.0 <= lo <= 6.0 or (lo <= 7.5 <= hi):
            star = "  <-- 6-9 Hz, the symptom band"
        npos = int((Cpar[:, j] > 0).sum())
        print(f"  {f'{lo:.1f}-{hi:.1f}':>11s} {mraw[j]:+15.4f} {mpar[j]:+19.4f} "
              f"{1.96*se[j]:11.4f} {npos:6d}/6   {star}")

    # where is the partial maximised, and is 6-9 special?
    jstar = int(np.argmax(mpar))
    lo_s, hi_s = EDGES[jstar]
    in69 = [j for j, (a, b) in enumerate(EDGES) if a >= 5.5 and b <= 9.5]
    print(f"\n  ⭐ PARTIAL rho PEAKS at {lo_s:.1f}-{hi_s:.1f} Hz (mean {mpar[jstar]:+.4f})")
    if in69:
        print(f"     mean partial rho inside 6-9 Hz  = {mpar[in69].mean():+.4f}")
    print(f"     mean partial rho over 25-42 Hz    = "
          f"{mpar[[j for j,(a,b) in enumerate(EDGES) if a>=25]].mean():+.4f}")
    print(f"     mean partial rho over 15-25 Hz    = "
          f"{mpar[[j for j,(a,b) in enumerate(EDGES) if 15<=a<25]].mean():+.4f}")
    res["peak_band"] = f"{lo_s:.1f}-{hi_s:.1f}"
    res["peak_value"] = float(mpar[jstar])
    return res


def hands_on():
    """PART 2 -- the grip stratification I had not applied."""
    print("\n" + "=" * 100)
    print("  PART 2 -- HANDS-ON / HANDS-OFF STRATIFICATION.  Grip DAMPS the 6-9 Hz mode")
    print("  (-0.720 [-0.918,-0.500] vs control -0.266, on this kit's own record), so it is a")
    print("  live confound on every number in the primary analysis.")
    print("=" * 100)
    res = {}
    print(f"  {'route':6s} {'press duty':>11s} {'HANDS-OFF partial':>32s} "
          f"{'HANDS-ON partial':>32s}")
    for stem in BIG:
        d = H.load(stem)
        z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
        press = np.asarray(z["cs_press"], float) > 0.5
        rows, eps = H.windows_for(d)
        R, ep, _yr, _yc, y, lr, lv = H.arrays(rows, "32-38")   # the CLEAN control band
        pw = []
        for a_, b_ in eps:
            for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
                pw.append(float(press[a_ + s:a_ + s + H.NPERSEG].mean()))
        pw = np.array(pw)
        duty = float(press[d["eng"]].mean())
        row = {"press_duty_engaged": duty}
        line = f"  {stem:6s} {duty:11.4f} "
        for tag, m in (("off", pw <= 0.05), ("on", pw >= 0.95)):
            if m.sum() < 60:
                line += f"{'n<60':>32s} "
                row[tag] = None
                continue
            p = H.partial_spearman(y[m], R[m], [lr[m], lv[m]])
            lo_, hi_, ne = H.boot_episodes(
                lambda i: H.partial_spearman(y[m][i], R[m][i], [lr[m][i], lv[m][i]]),
                ep[m], n=1500)
            row[tag] = dict(n=int(m.sum()), partial=p, ci=[lo_, hi_], n_eps=ne)
            line += f"{f'{p:+.3f} [{lo_:+.3f},{hi_:+.3f}] n={int(m.sum())}':>32s} "
        res[stem] = row
        print(line)
    print("\n  🛑 The primary analysis pooled both grip states.  If the two columns disagree, the")
    print("     pooled number is a mixture and must be read as one.")
    return res


def main():
    res = {"why": "the primary answer depended on the control band; this removes the choice",
           "spectrum": spectrum(), "hands_on": hands_on()}
    (OUT / "dcmd_dt_spectrum.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'dcmd_dt_spectrum.json'}")
    return res


if __name__ == "__main__":
    main()
