#!/usr/bin/env python3
r"""studies/v103-r9e/v103_r9e_symptom2.py -- FIXES TWO DEFECTS in `studies/v103-r9e/v103_r9e_symptom.py`, and adds the speed-matched
V102/V103 contrast.  Run BOTH; this one supersedes parts A(rate), D(rate bins), D2 and C.

DEFECT 1 -- RATE-BINNED REGIMES RETURNED ZERO WINDOWS.  Masking on `rate in [lo,hi)` and then
   demanding a 2.56 s CONTIGUOUS run is impossible: wheel rate crosses every bin many times a
   second.  FIX: window over the ENGAGEMENT run, then CLASSIFY each window by its own median rate.

DEFECT 2 -- THE "PHASE-SHUFFLED" LINE CONTROL WAS A NO-OP.  It randomised the phase of `X` and then
   took `|X e^{iφ}|² = |X|²` -- bit-identical to the real spectrum (it returned 4.42 vs 4.42).
   FIX: a proper surrogate.  Take the pooled average PSD, MEDIAN-SMOOTH it to remove any line, then
   draw n_win independent chi²₂ realisations of that smooth PSD and measure the max prominence of
   their average.  That is the finite-averaging null a peak must beat.  A SPLIT-HALF frequency
   stability test is carried alongside -- a real line lands in the same bin in both halves.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402
import decode_v90_probe as P      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(4103)
NW, HOP = 256, 128
BANDS = [("2.5-4.5", 2.5, 4.5), ("6-9", 6.0, 9.0), ("10-15", 10.0, 15.0),
         ("15-22", 15.0, 22.0), ("20-28", 20.0, 28.0), ("21.5-25.5", 21.5, 25.5),
         ("22-26", 22.0, 26.0), ("31-35", 31.0, 35.0)]
CH = [("tq", "driver torque"), ("rate_c", "steer rate 14A"), ("cs_ang", "steer angle"),
      ("e4tq", "LKAS cmd 0E4"), ("x6b4c", "EPS 427 lane"), ("imu_lat", "IMU lat")]
OUT = {}
DT = 0.01


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def brms_all(x, fs):
    w = np.hanning(len(x))
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X = np.fft.rfft((x - x.mean()) * w)
    psd = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    psd[1:-1] *= 2.0
    df = f[1] - f[0]
    return {nm: float(np.sqrt(np.sum(psd[(f >= lo) & (f <= hi)]) * df)) for nm, lo, hi in BANDS}


def win_over(mask, t):
    out = []
    for a, b in V.episodes(mask, t, NW):
        for i in range(0, (b - a) - NW + 1, HOP):
            out.append(slice(a + i, a + i + NW))
    return out


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    seg = np.asarray(z["seg"], int)
    fs = 1.0 / float(np.median(np.diff(t)))
    eng, press = M["eng"], M["press"]
    v, rate = M["v"], M["rate"]
    chan = {k: np.asarray(z[k], float) for k, _ in CH}
    print("  fs %.2f Hz  window %d = %.2f s  hop %.2f s" % (fs, NW, NW / fs, HOP / fs))

    # ================================================================ A2  RATE REGIMES, FIXED
    hdr("A2 -- BAND-RMS BY WHEEL-RATE REGIME (DEFECT 1 FIXED: window over the ENGAGEMENT run,\n"
        "      then classify each window by its OWN median |wheel rate|).")
    RB = [(0.0, 1.0, "still  <1"), (1.0, 6.0, "micro-lo 1-6"), (6.0, 13.0, "micro-hi 6-13"),
          (13.0, 25.0, "ratchet 13-25"), (25.0, 50.0, "ratchet-hi 25-50"), (50.0, 1e9, "macro >50")]
    for armnm, am in (("ENGAGED", eng & (v > 0.5)), ("MANUAL", (~eng) & (v > 0.5))):
        W = win_over(am, t)
        med = np.array([np.median(rate[w]) for w in W])
        vs = np.array([np.median(v[w]) * 3.6 for w in W])
        print("\n  --- %s: %d windows total ---" % (armnm, len(W)))
        print("      %-17s %5s %7s %8s " % ("rate bin deg/s", "n", "v p50", "hands") +
              " ".join("%9s" % b[0] for b in BANDS))
        for lo, hi, nm in RB:
            sel = [w for w, m_ in zip(W, med) if lo <= m_ < hi]
            if len(sel) < 4:
                continue
            hh = float(np.mean([press[w].mean() for w in sel]))
            vv = float(np.median([np.median(v[w]) * 3.6 for w in sel]))
            b = {nm2: float(np.median([brms_all(chan["tq"][w], fs)[nm2] for w in sel]))
                 for nm2, _, _ in BANDS}
            print("      %-17s %5d %7.0f %8.2f " % (nm, len(sel), vv, hh) +
                  " ".join("%9.1f" % b[x[0]] for x in BANDS))
            OUT.setdefault("A2", {}).setdefault(armnm, {})[nm] = dict(
                n=len(sel), v_p50=vv, hands=hh, tq=b)
        _ = vs

    # ================================================================ D2  ENG vs MAN, MATCHED
    hdr("D2 -- ENGAGED vs MANUAL, MATCHED on speed AND wheel rate (DEFECT 1 FIXED).\n"
        "      Ratios are ENG/MAN of the median 2.56 s band-RMS.  >1 = engagement AMPLIFIES.")
    We = win_over(eng & (v > 0.5), t)
    Wm = win_over((~eng) & (v > 0.5), t)
    ce = [(w, float(np.median(v[w]) * 3.6), float(np.median(rate[w]))) for w in We]
    cm = [(w, float(np.median(v[w]) * 3.6), float(np.median(rate[w]))) for w in Wm]
    cells = []
    for vlo, vhi in ((0, 30), (30, 60), (60, 95)):
        for rlo, rhi, rn in ((1, 6, "1-6"), (6, 13, "6-13"), (13, 50, "13-50"), (50, 1e9, ">50")):
            se = [w for w, vv, rr in ce if vlo <= vv < vhi and rlo <= rr < rhi]
            sm = [w for w, vv, rr in cm if vlo <= vv < vhi and rlo <= rr < rhi]
            if len(se) < 4 or len(sm) < 4:
                continue
            row = dict(v="%d-%d" % (vlo, vhi), r=rn, ne=len(se), nm=len(sm))
            for k, _l in CH:
                if k == "e4tq":
                    continue
                a = np.median([brms_all(chan[k][w], fs)["6-9"] for w in se])
                b = np.median([brms_all(chan[k][w], fs)["6-9"] for w in sm])
                row[k] = float(a / max(b, 1e-9))
                row[k + "_eng"] = float(a)
                row[k + "_man"] = float(b)
            # bootstrap the tq ratio over windows within the cell
            bs = []
            for _ in range(400):
                ia = RNG.integers(0, len(se), len(se))
                ib = RNG.integers(0, len(sm), len(sm))
                a = np.median([brms_all(chan["tq"][se[i]], fs)["6-9"] for i in ia])
                b = np.median([brms_all(chan["tq"][sm[i]], fs)["6-9"] for i in ib])
                bs.append(a / max(b, 1e-9))
            row["tq_lo"], row["tq_hi"] = V.ci(bs)
            cells.append(row)
    print("      %-8s %-7s %5s %5s %22s %10s %10s %10s"
          % ("v km/h", "rate", "n_E", "n_M", "tq 6-9 E/M [95% CI]", "rate_c", "angle", "IMU lat"))
    for r in cells:
        print("      %-8s %-7s %5d %5d %8.2f [%5.2f,%6.2f] %10.2f %10.2f %10.2f"
              % (r["v"], r["r"], r["ne"], r["nm"], r["tq"], r["tq_lo"], r["tq_hi"],
                 r["rate_c"], r["cs_ang"], r["imu_lat"]))
    OUT["eng_vs_man_matched"] = cells

    # ================================================================ C2  THE LINE, PROPER NULL
    hdr("C2 -- IS THERE A ~23 Hz LINE?  (DEFECT 2 FIXED.)  Null = chi²₂ realisations of the\n"
        "      MEDIAN-SMOOTHED pooled PSD, averaged over the same n windows.  Split-half\n"
        "      frequency stability carried alongside: a real line lands in the same bin twice.")
    for nm, m in (("ENG hands-off 29-86 km/h", eng & (~press) & (v >= 8.0) & (v < 24.0)),
                  ("ENG hands-off 60-85 km/h", eng & (~press) & (v >= 16.67) & (v < 23.6)),
                  ("ENG hands-off 29-50 km/h", eng & (~press) & (v >= 8.0) & (v < 14.0)),
                  ("ENG low speed  <30 km/h", eng & (v > 0.5) & (v < 8.33)),
                  ("MANUAL moving 29-86 km/h", (~eng) & (v >= 8.0) & (v < 24.0))):
        W = win_over(m, t)
        if len(W) < 8:
            print("\n  %-26s only %d windows -- skipped" % (nm, len(W)))
            continue
        wn = np.hanning(NW)
        f = np.fft.rfftfreq(NW, 1.0 / fs)
        S = np.array([np.abs(np.fft.rfft((chan["tq"][w] - chan["tq"][w].mean()) * wn)) ** 2
                      for w in W])
        acc = S.mean(axis=0)
        sel = (f >= 15.0) & (f <= 32.0)
        fs_ = f[sel]
        a_ = acc[sel]
        sm = median_filter(a_, size=9, mode="nearest")
        prom = float((a_ / sm).max())
        fpk = float(fs_[int(np.argmax(a_ / sm))])
        # NULL: chi2_2 draws of the smoothed PSD, averaged over len(W) windows
        nulls = []
        for _ in range(300):
            d = sm[None, :] * RNG.chisquare(2, size=(len(W), len(sm))) / 2.0
            am = d.mean(axis=0)
            nulls.append(float((am / median_filter(am, size=9, mode="nearest")).max()))
        p95 = float(np.percentile(nulls, 95))
        # split-half frequency stability
        idx = RNG.permutation(len(W))
        h1 = S[idx[: len(W) // 2]].mean(axis=0)[sel]
        h2 = S[idx[len(W) // 2:]].mean(axis=0)[sel]
        f1 = float(fs_[int(np.argmax(h1 / median_filter(h1, size=9, mode="nearest")))])
        f2 = float(fs_[int(np.argmax(h2 / median_filter(h2, size=9, mode="nearest")))])
        vs = np.array([np.median(v[w]) * 3.6 for w in W])
        print("\n  %-26s n=%3d win   speed p10/p50/p90 %.0f/%.0f/%.0f km/h"
              % (nm, len(W), np.percentile(vs, 10), np.percentile(vs, 50), np.percentile(vs, 90)))
        print("      peak %.2f Hz  prominence %.2f x local median   NULL p95 %.2f   => %s"
              % (fpk, prom, p95, "LINE PRESENT" if prom > p95 else "no line above noise"))
        print("      split-half peaks: %.2f Hz / %.2f Hz  (%s)"
              % (f1, f2, "STABLE" if abs(f1 - f2) <= 1.0 else "UNSTABLE -- not a line"))
        loc = [(fs_[i], (a_ / sm)[i]) for i in range(1, len(a_) - 1)
               if a_[i] > a_[i - 1] and a_[i] > a_[i + 1]]
        loc.sort(key=lambda x: -x[1])
        print("      top local maxima: " + "  ".join("%.2f Hz (x%.2f)" % x for x in loc[:5]))
        OUT.setdefault("line", {})[nm] = dict(n_win=len(W), f_peak=fpk, prominence=prom,
                                              null_p95=p95, split_half=[f1, f2],
                                              v_p50=float(np.median(vs)),
                                              top=[[float(a2), float(b2)] for a2, b2 in loc[:5]])

    # ================================================================ E  SPEED-MATCHED V102/V103
    hdr("E -- V102 vs V103, SPEED-MATCHED.  V103's f0 windows sat at v p50 16.6 m/s against\n"
        "     V102's 15.5, and f0 moves +0.157 Hz/(m/s).  Match the two before comparing.")
    arms = {}
    for rt, lab in (("96", "V102"), ("9e", "V103"), ("97", "STOCK")):
        zz = V.load(rt)
        MM = V.masks(zz)
        tt = np.asarray(zz["t"], float)
        fss = 1.0 / float(np.median(np.diff(tt)))
        mm = MM["eng"] & (~MM["press"]) & MM["moving"]
        G = V.wins_by_episode(zz, mm, (np.asarray(zz["rate_f"], float) * V.DEG2RAD,
                                       np.asarray(zz["tq"], float), MM["v"],
                                       np.abs(np.asarray(zz["e4tq"], float))))
        arms[rt] = (G, fss, lab)
    for vlo, vhi in ((8.0, 24.0), (8.0, 14.0), (14.0, 19.0), (16.67, 23.6)):
        print("\n  --- speed window %.0f-%.0f km/h ---" % (vlo * 3.6, vhi * 3.6))
        print("      %-7s %5s %5s %8s %9s %22s" % ("build", "n_w", "n_ep", "v p50", "med|0E4|",
                                                   "f0 [95% CI episode]"))
        for rt in ("97", "96", "9e"):
            G, fss, lab = arms[rt]
            Gs = [[w for w in ep if vlo <= float(np.median(w[2])) < vhi] for ep in G]
            Gs = [ep for ep in Gs if ep]
            W = [w for ep in Gs for w in ep]
            if len(W) < 8:
                print("      %-7s %5d  -- too few" % (lab, len(W)))
                continue
            pr = [(w[0], w[1]) for w in W]
            pt = V.f0_of(pr, fss)
            b = V.boot_episode([[(w[0], w[1]) for w in ep] for ep in Gs], fss, V.f0_of,
                               nboot=300, rng=np.random.default_rng(77))
            lo_, hi_ = V.ci(b)
            print("      %-7s %5d %5d %8.2f %9.0f   %.2f [%.2f, %.2f]"
                  % (lab, len(W), len(Gs), np.median([np.median(w[2]) for w in W]),
                     np.median([np.median(w[3]) for w in W]), pt, lo_, hi_))
            OUT.setdefault("speed_matched", {}).setdefault(
                "%.0f-%.0f" % (vlo * 3.6, vhi * 3.6), {})[lab] = dict(
                n_win=len(W), n_ep=len(Gs), f0=float(pt), lo=float(lo_), hi=float(hi_),
                v_p50=float(np.median([np.median(w[2]) for w in W])),
                cmd=float(np.median([np.median(w[3]) for w in W])))

    Path(HERE / "_scratch/out/_v103_r9e_symptom2.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_symptom2.json")


if __name__ == "__main__":
    main()
