#!/usr/bin/env python3
r"""score_v102_full.py -- V102 (route 96, 6x) scored against V101 (r95, 8x), V100 (r85, 4x) and,
for the first time in this kit, **HONDA STOCK (r97, 1x)**.

WHY THIS EXISTS ALONGSIDE `score_v102.py`
    `score_v102.py` runs the PRE-REGISTERED cross-route matched-cell estimator with a 15 s block
    bootstrap.  Its cells came out THIN (5-6 cells, n as low as 5) because V101's route 95 tops out
    at 68 km/h while V102's route 96 reaches 110 km/h, and `VB` caps at 65 km/h -- so 344 s of
    V102's 576 s engaged exposure is discarded.  This file adds:

      1. the LITERAL primary endpoint of `STATE.md` -- the WITHIN-ROUTE shape statistic, the same
         estimator that produced the record's 5.07 / 0.62 (`r95_v102_prereg.py`), so no cross-route
         matching is needed at all;
      2. a SPLIT-HALF NULL, run BEFORE any ratio is quoted, per the standing instruction;
      3. EPISODE-level bootstrap alongside the 15 s block bootstrap, so the two can be compared;
      4. route 97 = STOCK as a 1x rung -- the record says "no 1x or 2x route survives with usable
         channels."  One does now.
      5. a matched-speed peak-frequency estimate with a per-window speed census.

TRAPS HONOURED
  * `t` is EVENT-DRIVEN.  The within-route statistic (1) reproduces `r95_v102_prereg.py` EXACTLY,
    including its treatment of the native grid, so its numbers are comparable to 5.07 / 0.62.
    Everything SPECTRAL (peak frequency) goes through `v102_xb_lib`'s uniform 100 Hz resampler.
  * `v_rear` is METRES PER SECOND.  `cs_v` is m/s too.
  * raw14 off-by-one: this file never pairs `t` with `raw14_b4`.  It uses `probe` only.
  * No `band_envelope` anywhere -- the `_r2b_common` rectification defect cannot touch these.

Usage:  python score_v102_full.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- register the two new routes on the uniform-grid loader
for _r, _lab, _g in (("96", "V102", 5346), ("97", "V9b-STOCK", 891)):
    L.ROUTES[_r] = L._mk(_r, _lab, gain=_g, clamp=3072 if _r == "96" else 512,
                         leverB=False, idcode=3 if _r == "96" else 0, bits="v102")

ARMS = [("97", "V9b STOCK", "1x", 891),
        ("85", "V100", "4x", 3564),
        ("96", "V102", "6x", 5346),
        ("95", "V101", "8x", 7128)]
NPZ = {"97": "_cache_r97/r97.npz", "85": "_cache_r85/r85.npz",
       "96": "_cache_r96/r96.npz", "95": "_cache_r95/r95.npz"}

BANDS = {"B23": (21.5, 25.5),    # the PRIMARY target band
         "B8": (7.3, 9.3),       # the micro-ratchet band
         "CTRL": (2.5, 4.5),     # the PRIMARY control band (the LKAS command passband)
         "HI": (32.0, 38.0)}     # the pre-declared NEGATIVE-CONTROL band
CHANS = ("tq", "rate_f", "cs_ang")
LIGHT = 400.0                    # |driver torque| below this = hands-light
out = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


# =====================================================================================================
# 1.  THE WITHIN-ROUTE SHAPE STATISTIC -- estimator VERBATIM from `r95_v102_prereg.py`
# =====================================================================================================
def runs_break(mask, t, min_n):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


def bp(x, a, b, FS, lo, hi):
    seg = np.nan_to_num(np.asarray(x[a:b], float) - np.nanmean(x[a:b]))
    X = np.fft.rfft(seg)
    f = np.fft.rfftfreq(len(seg), 1 / FS)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(seg))


def build_table(route):
    """One row per engaged 1 s window, tagged with its EPISODE id, speed and driver torque."""
    z = dict(np.load(ROOT / "analysis-2020accord" / NPZ[route], allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    dtq = np.abs(np.asarray(z["cs_tq"], float))
    WL = int(round(1.0 * FS))
    rows = []
    for ep, (a, b) in enumerate(runs_break(lat, t, WL)):
        B = {(c, bn): bp(np.asarray(z[c], float), a, b, FS, *br)
             for c in CHANS for bn, br in BANDS.items()}
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            rec = {"epi": float(ep), "v": float(np.median(vk[a:b][sl])),
                   "dtq": float(np.median(dtq[a:b][sl])),
                   "t0": float(t[a:b][sl][0])}
            for c in CHANS:
                for bn in BANDS:
                    rec["%s_%s" % (c, bn)] = float(np.sqrt(np.mean(B[(c, bn)][sl] ** 2)))
            rows.append(rec)
    T = {k: np.array([r[k] for r in rows], float) for k in rows[0]}
    T["_FS"] = FS
    T["_nepi"] = len(set(T["epi"].tolist()))
    return T


def shape(T, c, tgt, ctl, m=None):
    a = T["%s_%s" % (c, tgt)]
    b = T["%s_%s" % (c, ctl)]
    if m is not None:
        a, b = a[m], b[m]
    return a / b


def boot_median(vals, groups, nboot=4000, seed=3):
    """Median of `vals`, bootstrapped by RESAMPLING WHOLE GROUPS (episodes or 15 s blocks)."""
    rng = np.random.default_rng(seed)
    g = np.asarray(groups)
    keys = np.unique(g)
    idx = {k: np.nonzero(g == k)[0] for k in keys}
    pt = float(np.median(vals))
    bs = []
    for _ in range(nboot):
        pick = rng.integers(0, len(keys), len(keys))
        sel = np.concatenate([idx[keys[j]] for j in pick])
        bs.append(float(np.median(vals[sel])))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return pt, float(lo), float(hi), len(keys)


def ratio_boot(vA, gA, vB, gB, nboot=4000, seed=5):
    """median(B)/median(A) with BOTH arms group-resampled independently."""
    rng = np.random.default_rng(seed)
    def prep(v, g):
        g = np.asarray(g)
        k = np.unique(g)
        return v, k, {kk: np.nonzero(g == kk)[0] for kk in k}
    vA, kA, iA = prep(vA, gA)
    vB, kB, iB = prep(vB, gB)
    pt = float(np.median(vB) / np.median(vA))
    bs = []
    for _ in range(nboot):
        sa = np.concatenate([iA[kA[j]] for j in rng.integers(0, len(kA), len(kA))])
        sb = np.concatenate([iB[kB[j]] for j in rng.integers(0, len(kB), len(kB))])
        bs.append(float(np.median(vB[sb]) / np.median(vA[sa])))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), nA=len(kA), nB=len(kB))


# =====================================================================================================
if __name__ == "__main__":
    TAB = {}
    hdr("0 -- EXPOSURE, EPISODES, SPEED CENSUS, HANDS-ON/OFF.  Read this before any ratio.")
    print("    %-6s %-11s %-4s %7s %7s %6s   %s" % ("route", "build", "gain", "eng win",
                                                    "eng s", "episo", "engaged speed km/h "
                                                    "p10/p50/p90/max   hands-light frac"))
    for r, lab, gl, _g in ARMS:
        T = build_table(r)
        TAB[r] = T
        v = T["v"]
        hl = float(np.mean(T["dtq"] < LIGHT))
        print("    %-6s %-11s %-4s %7d %7.1f %6d   %5.1f /%5.1f /%5.1f /%5.1f      %.3f"
              % ("r" + r, lab, gl, len(v), len(v) * 1.0, T["_nepi"],
                 *np.percentile(v, [10, 50, 90, 100]), hl))
        out.setdefault("exposure", {})[r] = dict(
            build=lab, gain=gl, n_windows=int(len(v)), engaged_s=float(len(v)),
            episodes=int(T["_nepi"]), v_p10=float(np.percentile(v, 10)),
            v_p50=float(np.percentile(v, 50)), v_p90=float(np.percentile(v, 90)),
            v_max=float(v.max()), hands_light_frac=hl, FS=float(T["_FS"]))
    print("\n    per-window SPEED CENSUS (fraction of engaged 1 s windows in each bin):")
    EDGES = [0, 5, 20, 35, 50, 65, 80, 200]
    print("    %-6s " % "route" + "".join("%10s" % ("%d-%d" % (EDGES[i], EDGES[i + 1]))
                                          for i in range(len(EDGES) - 1)))
    for r, lab, gl, _g in ARMS:
        v = TAB[r]["v"]
        print("    %-6s " % ("r" + r) + "".join(
            "%10.3f" % np.mean((v >= EDGES[i]) & (v < EDGES[i + 1]))
            for i in range(len(EDGES) - 1)))

    # ------------------------------------------------------------------ SPLIT-HALF NULL FIRST
    hdr("1 -- 🛑 THE SPLIT-HALF NULL, RUN BEFORE ANY RATIO IS QUOTED.\n"
        "     Randomly split ONE route's episodes into two halves and run the SAME estimator.\n"
        "     A calibrated bootstrap unit gives ~1.00 with the quoted CI covering it ~95 % of the\n"
        "     time.  If this is wide, the cross-build CI below cannot be narrower.")
    rng = np.random.default_rng(17)
    for unit in ("episode", "block15s"):
        print("\n    bootstrap unit = %s" % unit)
        for r, lab, gl, _g in ARMS:
            T = TAB[r]
            s = shape(T, "tq", "B23", "CTRL")
            g = T["epi"] if unit == "episode" else T["epi"] * 1e6 + np.floor(T["t0"] / 15.0)
            keys = np.unique(g)
            if len(keys) < 4:
                print("      r%-4s %-11s only %d groups -- SPLIT-HALF NOT RUN" % (r, lab, len(keys)))
                continue
            rr = []
            for _ in range(600):
                perm = rng.permutation(keys)
                h1, h2 = perm[:len(perm) // 2], perm[len(perm) // 2:]
                m1 = np.isin(g, h1)
                m2 = np.isin(g, h2)
                if m1.sum() < 10 or m2.sum() < 10:
                    continue
                rr.append(np.median(s[m2]) / np.median(s[m1]))
            rr = np.array(rr)
            lo, hi = np.percentile(rr, [2.5, 97.5])
            print("      r%-4s %-11s %4d groups   split-half ratio  p50 %.3f   95%% spread "
                  "[%.2f, %.2f]  (width %.2fx)"
                  % (r, lab, len(keys), np.median(rr), lo, hi, hi / lo))
            out.setdefault("splithalf_" + unit, {})[r] = dict(
                groups=int(len(keys)), p50=float(np.median(rr)), lo=float(lo), hi=float(hi))

    print("\n    ⊕ EXTERNAL null -- the V89 PLACEBO PAIR r75 vs r76 (byte-identical firmware),")
    print("      same within-route statistic, so it prices DRIVE-TO-DRIVE variation, not split noise.")
    try:
        for a, b in (("75", "76"),):
            Ta, Tb = build_table(a) if a in NPZ else None, None
    except Exception:
        pass
    print("      (r75/r76 lack a whole-route npz in this schema; the uniform-grid placebo floor")
    print("       measured by score_v102.py on the SAME convention is 1.68x -- USE THAT.)")

    # ------------------------------------------------------------------ THE PRIMARY
    hdr("2 -- 🛑 THE PRIMARY ENDPOINT, literally as STATE.md defines it:\n"
        "     within-route  tq band-RMS(21.5-25.5) / band-RMS(2.5-4.5),  median over 1 s engaged\n"
        "     windows.  Record values: V101 = 5.07x V100 ; V100 absolute = 0.62.")
    for c in ("tq", "rate_f", "cs_ang"):
        for tgt, ctl in (("B23", "CTRL"), ("B23", "HI"), ("B8", "CTRL")):
            print("\n    ### %s   shape = %s / %s" % (c, tgt, ctl))
            print("        %-6s %-11s %-4s %8s   %-26s %-26s" %
                  ("route", "build", "gain", "n", "EPISODE boot [95% CI]",
                   "15 s BLOCK boot [95% CI]"))
            for r, lab, gl, _g in ARMS:
                T = TAB[r]
                s = shape(T, c, tgt, ctl)
                pe, le, he, ne = boot_median(s, T["epi"])
                gb = T["epi"] * 1e6 + np.floor(T["t0"] / 15.0)
                pb, lb, hb, nb = boot_median(s, gb)
                print("        %-6s %-11s %-4s %8d   %6.2f [%5.2f,%6.2f] n=%-3d "
                      "%6.2f [%5.2f,%6.2f] n=%d"
                      % ("r" + r, lab, gl, len(s), pe, le, he, ne, pb, lb, hb, nb))
                out.setdefault("within_%s_%s_%s" % (c, tgt, ctl), {})[r] = dict(
                    build=lab, gain=gl, n=int(len(s)), point=float(pe),
                    epi_lo=float(le), epi_hi=float(he), n_epi=int(ne),
                    blk_lo=float(lb), blk_hi=float(hb), n_blk=int(nb))

    hdr("3 -- 🛑 THE DECISION: V102 / V101 on the PRIMARY, with an EPISODE bootstrap.\n"
        "     Pre-registered rule:  <=0.70 dose-response HOLDS · >0.85 THE GAIN IS NOT THE CARRIER\n"
        "                           inside the 1.68x placebo floor => NOT A RESULT.")
    for c in ("tq", "rate_f", "cs_ang"):
        for tgt, ctl in (("B23", "CTRL"), ("B23", "HI")):
            print("\n    %s  %s/%s" % (c, tgt, ctl))
            base = shape(TAB["95"], c, tgt, ctl)
            gbase = TAB["95"]["epi"]
            for r, lab, gl, _g in ARMS:
                if r == "95":
                    continue
                s = shape(TAB[r], c, tgt, ctl)
                d = ratio_boot(base, gbase, s, TAB[r]["epi"])
                dblk = ratio_boot(base, TAB["95"]["epi"] * 1e6 + np.floor(TAB["95"]["t0"] / 15.0),
                                  s, TAB[r]["epi"] * 1e6 + np.floor(TAB[r]["t0"] / 15.0))
                print("        %-11s %-4s / V101 8x  = %6.3f  EPISODE [%5.3f, %6.3f] "
                      "(nA=%d nB=%d)   BLOCK [%5.3f, %6.3f]"
                      % (lab, gl, d["r"], d["lo"], d["hi"], d["nA"], d["nB"],
                         dblk["lo"], dblk["hi"]))
                out.setdefault("vs_v101_%s_%s_%s" % (c, tgt, ctl), {})[r] = dict(
                    build=lab, gain=gl, ratio=d["r"], epi_lo=d["lo"], epi_hi=d["hi"],
                    blk_lo=dblk["lo"], blk_hi=dblk["hi"])

    # ------------------------------------------------------------------ SPEED-STRATIFIED
    hdr("4 -- SPEED-STRATIFIED within-route primary (tq B23/CTRL).  A moving wheel order would\n"
        "     show up as a speed-dependent shape; wheel order 1 is 0.489*v Hz => 21.5-25.5 Hz\n"
        "     needs 44-52 m/s = 158-188 km/h, unreachable.  Higher orders are the real risk.")
    BINS = [(0, 20), (20, 40), (40, 70), (70, 95), (95, 200)]
    print("    %-6s %-11s " % ("route", "build") +
          "".join("%18s" % ("%d-%d km/h" % b) for b in BINS))
    for r, lab, gl, _g in ARMS:
        T = TAB[r]
        s = shape(T, "tq", "B23", "CTRL")
        line = "    %-6s %-11s " % ("r" + r, lab)
        for lo, hi in BINS:
            m = (T["v"] >= lo) & (T["v"] < hi)
            if m.sum() < 8:
                line += "%18s" % ("n=%d --" % m.sum())
            else:
                line += "%18s" % ("%.2f (n=%d)" % (np.median(s[m]), m.sum()))
        print(line)

    # ------------------------------------------------------------------ HANDS
    hdr("5 -- HANDS-ON / HANDS-OFF split on the primary (the operator: the buzz dies when he pushes)")
    print("    %-6s %-11s %18s %18s %10s" % ("route", "build", "hands-LIGHT (<400)",
                                             "hands-ON (>=400)", "ratio on/light"))
    for r, lab, gl, _g in ARMS:
        T = TAB[r]
        s = shape(T, "tq", "B23", "CTRL")
        ml, mo = T["dtq"] < LIGHT, T["dtq"] >= LIGHT
        if ml.sum() < 8 or mo.sum() < 8:
            print("    %-6s %-11s  too thin (%d / %d)" % ("r" + r, lab, ml.sum(), mo.sum()))
            continue
        a, b = np.median(s[ml]), np.median(s[mo])
        print("    %-6s %-11s %18s %18s %10.2f"
              % ("r" + r, lab, "%.2f (n=%d)" % (a, ml.sum()), "%.2f (n=%d)" % (b, mo.sum()), b / a))

    # ------------------------------------------------------------------ PEAK FREQUENCY
    hdr("6 -- 🛑 PEAK FREQUENCY, uniform 100 Hz grid, nfft=1024 (df = 0.0977 Hz).\n"
        "     MATCHED SPEED: every arm restricted to the SAME band, with a per-window census.")
    NF = 1024
    win = np.hanning(NF)
    f = L.psd(np.zeros(NF), L.FS, win)[0]
    for vlo, vhi in ((5, 65), (20, 50), (50, 110), (65, 115)):
        print("\n    speed window %d-%d km/h" % (vlo, vhi))
        for r, lab, gl, _g in ARMS:
            P, vs = [], []
            for b in L.all_blocks(r):
                m = (b["cc_lat"] > 0.5) & (b["v_rear"] * 3.6 >= vlo) & (b["v_rear"] * 3.6 < vhi)
                i = 0
                while i + NF <= len(m):
                    if m[i:i + NF].mean() >= 0.98:
                        P.append(L.psd(b["tq"][i:i + NF], L.FS, win)[1])
                        vs.append(float(np.median(b["v_rear"][i:i + NF] * 3.6)))
                    i += NF // 2
            if len(P) < 3:
                print("      %-6s %-11s %-4s  only %d windows -- NOT QUOTED" % ("r" + r, lab, gl,
                                                                                len(P)))
                continue
            P = np.asarray(P)
            pm = np.median(P, axis=0)
            bnd = (f >= 19) & (f <= 27)
            k = int(np.argmax(pm[bnd]))
            base = np.median(pm[(f >= 15) & (f <= 32)])
            # episode-free CI: bootstrap over WINDOWS is not allowed to carry the conclusion, so
            # resample WINDOWS only to show estimator jitter, and report the census beside it.
            rngp = np.random.default_rng(29)
            pk = []
            for _ in range(1500):
                sel = rngp.integers(0, len(P), len(P))
                q = np.median(P[sel], axis=0)
                pk.append(f[bnd][int(np.argmax(q[bnd]))])
            lo, hi = np.percentile(pk, [2.5, 97.5])
            print("      %-6s %-11s %-4s  %3d win  v p50 %5.1f km/h   f0 = %5.2f Hz "
                  "[%5.2f, %5.2f]   prominence %5.2f"
                  % ("r" + r, lab, gl, len(P), np.median(vs), f[bnd][k], lo, hi, pm[bnd][k] / base))
            out.setdefault("peak_%d_%d" % (vlo, vhi), {})[r] = dict(
                build=lab, gain=gl, n_win=int(len(P)), v_p50=float(np.median(vs)),
                f0=float(f[bnd][k]), lo=float(lo), hi=float(hi),
                prominence=float(pm[bnd][k] / base))

    (ROOT / "analysis-2020accord" / "_cache_r96" / "score_v102_full.json").write_text(
        json.dumps(out, indent=1, default=float))
    print("\nwrote analysis-2020accord/_cache_r96/score_v102_full.json")
