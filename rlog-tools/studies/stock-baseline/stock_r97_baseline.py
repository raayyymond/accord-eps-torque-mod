#!/usr/bin/env python3
r"""studies/stock-baseline/stock_r97_baseline.py -- THE STOCK FLOOR.  Route 97 == V9b STOCK, the kit's first modern
instrumented stock baseline.  Scored with the SAME frozen machinery as V100 (r85) and V101 (r95):
`v102_xb_lib` band-RMS, episode bootstrap, matched (speed x wheel-rate) cells.

    python studies/stock-baseline/stock_r97_baseline.py            # everything
    python studies/stock-baseline/stock_r97_baseline.py <part>     # census | null | endpoint | spectrum | bands | manual

OPERATOR'S REPORT ON THIS DRIVE (his words, outranks every band statistic):
    "No vibration or grinding.  Maybe ever so slightly, barely perceptible ratcheting."

NO ENVELOPE IS USED ANYWHERE IN THIS FILE.  Every statistic is a Parseval-normalised FFT band-RMS
over a Hann window, so the `_r2b_common.band_envelope` / `_r31_common.band_envelope` defect
(one-sided `H = 2X` then `irfft` => RECTIFIED, not analytic) cannot reach these numbers.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- register the stock route on the SAME loader every other arm uses -------------------
L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0,
                       bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")

ARMS = [("97", "V9b STOCK  1x"), ("85", "V100      4x"), ("95", "V101      8x")]
if L._segs("96"):
    ARMS.append(("96", "V102      6x"))

NFFT, HOP = 256, 128                  # 2.56 s Hann, 1.28 s hop -- score/score_v102.py's own constants
# THE PRE-REGISTERED ENDPOINT (STATE.md), plus the second convention score/score_v102.py also carries
CONV = {"A  21.5-25.5 / 2.5-4.5": ((21.5, 25.5), (2.5, 4.5)),
        "B  22-26 / 32-38": ((22.0, 26.0), (32.0, 38.0))}
SPEED_BINS = [(5, 20), (20, 35), (35, 50), (50, 65), (65, 85), (85, 115)]
RATE_BINS = [(0, 1), (1, 13), (13, 50), (50, 200)]     # static / MICRO / ratchet / macro
OUT = {}
_W = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def wins(route, engaged=True):
    k = (route, engaged)
    if k not in _W:
        r = L.windows(route, nfft=NFFT, hop=HOP, engaged=engaged, keep_raw=True)
        win = np.hanning(NFFT)
        for rec in r:
            blk, sl = rec["_blk"], rec["_sl"]
            for ch in ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert"):
                if ch not in blk:
                    continue
                x = blk[ch][sl]
                for nm, ((lo, hi), (clo, chi)) in CONV.items():
                    num = L.bandrms(x, L.FS, lo, hi, win)
                    den = L.bandrms(x, L.FS, clo, chi, win)
                    rec["num:%s|%s" % (ch, nm)] = num
                    rec["den:%s|%s" % (ch, nm)] = den
                    if den > 0:
                        rec["sh:%s|%s" % (ch, nm)] = num / den
            rec["e4rail"] = float(np.mean(np.abs(blk["e4tq"][sl]) >= 4095.0))
            rec["press"] = float(np.mean(blk["cs_press"][sl] > 0.5))
        _W[k] = r
    return _W[k]


def epi_boot(recs, key, nboot=4000, seed=7, stat=np.median):
    """Point estimate + 95 % CI, BLOCK-BOOTSTRAPPED OVER EPISODES (never windows)."""
    d = {}
    for r in recs:
        v = r.get(key, np.nan)
        if np.isfinite(v):
            d.setdefault((r["route"], r["seg"], r["epi"]), []).append(v)
    E = [np.asarray(v, float) for v in d.values()]
    if len(E) < 2:
        return dict(pt=np.nan, lo=np.nan, hi=np.nan, nepi=len(E), nwin=0)
    rng = np.random.default_rng(seed)
    pt = float(stat(np.concatenate(E)))
    out = np.array([stat(np.concatenate([E[j] for j in rng.integers(0, len(E), len(E))]))
                    for _ in range(nboot)], float)
    lo, hi = np.percentile(out[np.isfinite(out)], [2.5, 97.5])
    return dict(pt=pt, lo=float(lo), hi=float(hi), nepi=len(E),
                nwin=int(sum(len(x) for x in E)))


# =========================================================================================
def census():
    hdr("1 -- EXPOSURE AND SPEED CENSUS.  Every band number below is conditional on this.")
    OUT["census"] = {}
    print("  %-14s %8s %8s %8s %8s   %s" % ("route/build", "eng_s", "man_s", "n_epi", "n_win",
                                            "engaged speed km/h  p10/p50/p90/max"))
    for rt, lab in ARMS:
        try:
            we, wm = wins(rt, True), wins(rt, False)
        except Exception as exc:
            print("  %-14s  UNAVAILABLE: %s" % (lab, exc))
            continue
        blks = L.all_blocks(rt)
        eng_s = sum(float((b["cc_lat"] > 0.5).sum()) / L.FS for b in blks)
        man_s = sum(float((b["cc_lat"] <= 0.5).sum()) / L.FS for b in blks)
        v = np.array([r["v"] for r in we], float)
        q = np.percentile(v, [10, 50, 90]) if len(v) else [np.nan] * 3
        print("  %-14s %8.1f %8.1f %8d %8d   %5.1f /%5.1f /%5.1f /%5.1f"
              % (lab, eng_s, man_s, L.nepi(we), len(we), q[0], q[1], q[2],
                 v.max() if len(v) else np.nan))
        cen = {}
        for lo, hi in SPEED_BINS:
            cen["%d-%d" % (lo, hi)] = int(sum(1 for r in we if lo <= r["v"] < hi))
        rcen = {}
        for lo, hi in RATE_BINS:
            rcen["%d-%d" % (lo, hi)] = int(sum(1 for r in we if lo <= r["rate"] < hi))
        print("      engaged windows per speed bin (km/h): " +
              "  ".join("%s:%d" % (k, v_) for k, v_ in cen.items()))
        print("      engaged windows per |wheel rate| bin (deg/s): " +
              "  ".join("%s:%d" % (k, v_) for k, v_ in rcen.items()))
        rail = np.array([r["e4rail"] for r in we], float)
        prs = np.array([r["press"] for r in we], float)
        print("      openpilot 0x0E4 command AT ITS +-4096 RAIL: %.2f %% of engaged samples"
              "     hands-ON: %.2f %%" % (100 * rail.mean(), 100 * prs.mean()))
        OUT["census"][rt] = dict(build=lab, eng_s=eng_s, man_s=man_s, nepi=L.nepi(we),
                                 nwin=len(we), speed_bins=cen, rate_bins=rcen,
                                 e4_rail_frac=float(rail.mean()), press_frac=float(prs.mean()))


# =========================================================================================
def null():
    hdr("2 -- THE SPLIT-HALF NULL, RUN BEFORE ANY RATIO IS QUOTED.\n"
        "     Episodes of ONE route are split at random into two halves and the endpoint ratio\n"
        "     half/half is computed.  A well-behaved estimator returns 1.00 with a CI that\n"
        "     contains 1.  The WIDTH of this null is the FLOOR: no cross-route ratio inside it\n"
        "     is a result.")
    OUT["null"] = {}
    key = "sh:tq|A  21.5-25.5 / 2.5-4.5"
    for rt, lab in ARMS:
        we = wins(rt, True)
        d = {}
        for r in we:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                d.setdefault((r["seg"], r["epi"]), []).append(v)
        E = [np.asarray(v, float) for v in d.values()]
        if len(E) < 4:
            print("  %-14s  only %d episodes -- NOT SCOREABLE" % (lab, len(E)))
            continue
        rng = np.random.default_rng(11)
        rs = []
        for _ in range(4000):
            p = rng.permutation(len(E))
            a = np.concatenate([E[j] for j in p[:len(E) // 2]])
            b = np.concatenate([E[j] for j in p[len(E) // 2:]])
            rs.append(np.median(a) / np.median(b))
        rs = np.array(rs)
        lo, hi = np.percentile(rs, [2.5, 97.5])
        floor = float(max(hi, 1.0 / lo))
        print("  %-14s  %2d episodes   split-half ratio  median %.3f   95%% [%.3f, %.3f]"
              "   => FLOOR %.2fx" % (lab, len(E), np.median(rs), lo, hi, floor))
        OUT["null"][rt] = dict(build=lab, nepi=len(E), med=float(np.median(rs)),
                               lo=float(lo), hi=float(hi), floor=floor)
    fl = [v["floor"] for v in OUT["null"].values()]
    if fl:
        OUT["null"]["FLOOR"] = float(max(fl))
        print("\n  ==> THE SPLIT-HALF FLOOR USED BELOW = %.2fx (worst arm).  Any cross-route "
              "ratio inside\n      [1/%.2f, %.2f] is NOT A RESULT." % (max(fl), max(fl), max(fl)))


# =========================================================================================
def endpoint():
    hdr("3 -- THE PRE-REGISTERED ENDPOINT, ABSOLUTE, ON EVERY ARM.\n"
        "     within-route `tq` band-RMS(21.5-25.5 Hz) / band-RMS(2.5-4.5 Hz), engaged windows,\n"
        "     median over windows, 95 % CI block-bootstrapped OVER EPISODES.")
    OUT["endpoint"] = {}
    for cname in CONV:
        print("\n  --- convention %s ---" % cname)
        print("  %-14s %10s %20s %8s %8s %12s %12s"
              % ("route/build", "SHAPE", "95% CI (episodes)", "n_epi", "n_win",
                 "NUM abs", "DEN abs"))
        for rt, lab in ARMS:
            we = wins(rt, True)
            s = epi_boot(we, "sh:tq|" + cname)
            n = epi_boot(we, "num:tq|" + cname)
            d = epi_boot(we, "den:tq|" + cname)
            print("  %-14s %10.3f   [%8.3f, %8.3f] %8d %8d %12.1f %12.1f"
                  % (lab, s["pt"], s["lo"], s["hi"], s["nepi"], s["nwin"], n["pt"], d["pt"]))
            OUT["endpoint"].setdefault(cname, {})[rt] = dict(
                build=lab, shape=s, num=n, den=d)

    hdr("3b -- THE SAME ENDPOINT INSIDE MATCHED (speed x wheel-rate) CELLS.\n"
        "      Stock's engaged speed distribution is NOT the modded routes' -- an unmatched\n"
        "      ratio is a speed contrast wearing a band's clothes.")
    cname = "A  21.5-25.5 / 2.5-4.5"
    key = "sh:tq|" + cname
    ref = "97"
    for rt, lab in ARMS:
        if rt == ref:
            continue
        A, B = wins(ref, True), wins(rt, True)
        tot_n = tot_d = 0.0
        rows = []
        for vlo, vhi in SPEED_BINS:
            for rlo, rhi in RATE_BINS:
                a = L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                b = L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                va = [r[key] for r in a if np.isfinite(r.get(key, np.nan))]
                vb = [r[key] for r in b if np.isfinite(r.get(key, np.nan))]
                if len(va) < 5 or len(vb) < 5:
                    continue
                w = min(len(va), len(vb))
                rows.append((vlo, vhi, rlo, rhi, len(va), len(vb),
                             float(np.median(va)), float(np.median(vb))))
                tot_n += w * np.log(np.median(vb) / np.median(va))
                tot_d += w
        if not rows:
            print("\n  %s vs STOCK: NO matched cell has >=5 windows on both arms -- NOT "
                  "SCOREABLE." % lab)
            continue
        print("\n  %s vs STOCK, %d matched cells:" % (lab, len(rows)))
        print("      %-12s %-10s %7s %7s %10s %10s %8s"
              % ("v km/h", "rate d/s", "n_stock", "n_mod", "stock", lab.split()[0], "x"))
        for vlo, vhi, rlo, rhi, na, nb, ma, mb in rows:
            print("      %-12s %-10s %7d %7d %10.3f %10.3f %8.2f"
                  % ("%d-%d" % (vlo, vhi), "%d-%d" % (rlo, rhi), na, nb, ma, mb, mb / ma))
        print("      ==> min(n)-weighted geometric mean  %s / STOCK = %.2fx"
              % (lab.split()[0], np.exp(tot_n / tot_d)))
        OUT["endpoint"].setdefault("matched_vs_stock", {})[rt] = dict(
            build=lab, ratio=float(np.exp(tot_n / tot_d)), cells=len(rows))


# =========================================================================================
def bands():
    hdr("4 -- THE STOCK SPECTRUM BY BAND, ENGAGED, ABSOLUTE -- and every arm beside it.\n"
        "     `tq` = driver-side column torque (0x18F bytes 0-1, counts).\n"
        "     `rate_c` = steering angle rate (0x14A bytes 2-3, deg/s).")
    OUT["bands"] = {}
    for ch in ("tq", "rate_c"):
        print("\n  --- channel %s, engaged band-RMS (median over windows, episode CI) ---" % ch)
        print("  %-10s " % "band" + "".join("%26s" % lab for _, lab in ARMS))
        for bn in L.BANDS:
            row = "  %-10s " % bn
            for rt, _lab in ARMS:
                r = epi_boot(wins(rt, True), ch + "|" + bn)
                row += "%10.2f [%6.2f,%6.2f]" % (r["pt"], r["lo"], r["hi"])
                OUT["bands"].setdefault(ch, {}).setdefault(bn, {})[rt] = r
            print(row)

    hdr("4b -- STOCK vs EACH MODDED ARM, MATCHED CELLS, EVERY BAND.\n"
        "      ratio > 1 means the MODDED build has more content than STOCK in that band.")
    for ch in ("tq", "rate_c"):
        print("\n  --- channel %s ---" % ch)
        print("  %-10s " % "band" + "".join("%16s" % lab.split()[0] for rt, lab in ARMS
                                            if rt != "97"))
        for bn in L.BANDS:
            row = "  %-10s " % bn
            for rt, lab in ARMS:
                if rt == "97":
                    continue
                key = ch + "|" + bn
                A, B = wins("97", True), wins(rt, True)
                num = den = 0.0
                for vlo, vhi in SPEED_BINS:
                    for rlo, rhi in RATE_BINS:
                        a = [r[key] for r in L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                             if np.isfinite(r.get(key, np.nan)) and r.get(key, 0) > 0]
                        b = [r[key] for r in L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                             if np.isfinite(r.get(key, np.nan)) and r.get(key, 0) > 0]
                        if len(a) < 5 or len(b) < 5:
                            continue
                        w = min(len(a), len(b))
                        num += w * np.log(np.median(b) / np.median(a))
                        den += w
                v = np.exp(num / den) if den else np.nan
                row += "%16.2f" % v
                OUT["bands"].setdefault("matched_" + ch, {}).setdefault(bn, {})[rt] = float(v)
            print(row)


# =========================================================================================
def spectrum():
    hdr("5 -- THE FULL ENGAGED SPECTRUM 2-50 Hz, MATCHED SPEED.\n"
        "     🛑 wheel order 1 sits at 0.489*v Hz (v in m/s) -- an unmatched average manufactures\n"
        "     a line.  Every arm below is restricted to the SAME speed bin and the per-bin\n"
        "     window census is printed with it.")
    OUT["spectrum"] = {}
    win = np.hanning(1024)
    for vlo, vhi in SPEED_BINS:
        avail = []
        for rt, lab in ARMS:
            w = [r for r in wins(rt, True) if vlo <= r["v"] < vhi]
            if len(w) >= 8:
                avail.append((rt, lab, w))
        if not avail:
            continue
        print("\n  --- speed %d-%d km/h  (wheel order 1 = %.2f-%.2f Hz) ---"
              % (vlo, vhi, 0.489 * vlo / 3.6, 0.489 * vhi / 3.6))
        print("      " + "   ".join("%s n=%d" % (lab.split()[0], len(w)) for _, lab, w in avail))
        for rt, lab, w in avail:
            acc, f = None, None
            for r in w:
                blk, sl = r["_blk"], r["_sl"]
                x = blk["tq"][sl]
                f, p = L.psd(x, L.FS, np.hanning(NFFT))
                acc = p if acc is None else acc + p
            acc /= len(w)
            m = (f >= 2) & (f <= 50)
            fi, pi = f[m], acc[m]
            top = np.argsort(pi)[::-1][:5]
            peaks = "  ".join("%.1fHz" % fi[i] for i in sorted(top))
            print("      %-12s peak %.2f Hz   top-5 bins: %s" % (lab, fi[np.argmax(pi)], peaks))
            OUT["spectrum"].setdefault("%d-%d" % (vlo, vhi), {})[rt] = dict(
                build=lab, n=len(w), f=fi.tolist(), psd=pi.tolist())
    _ = win


# =========================================================================================
def manual():
    hdr("6 -- ENGAGED vs MANUAL ON STOCK.  The record's central claim is that ENGAGEMENT\n"
        "     AMPLIFIES 6-9 Hz 2.8x (band contrast +0.413 [+0.146,+0.667], 30 routes).\n"
        "     If it still amplifies on STOCK, the relay is HONDA'S.  If not, it is OURS.")
    OUT["manual"] = {}
    for rt, lab in ARMS:
        we, wm = wins(rt, True), wins(rt, False)
        if len(wm) < 20:
            print("\n  %-14s  only %d manual windows -- NOT SCOREABLE" % (lab, len(wm)))
            continue
        print("\n  --- %s ---   engaged %d win / %d epi    manual %d win / %d epi"
              % (lab, len(we), L.nepi(we), len(wm), L.nepi(wm)))
        print("      %-10s %26s %26s %10s   %s"
              % ("band", "ENGAGED", "MANUAL", "eng/man", "matched-cell eng/man"))
        for bn in ("3-5", "6-9", "10-15", "15-22", "18-22", "22-26", "26-31", "32-38", "40-49"):
            key = "tq|" + bn
            e = epi_boot(we, key)
            m = epi_boot(wm, key)
            num = den = 0.0
            for vlo, vhi in SPEED_BINS:
                for rlo, rhi in RATE_BINS:
                    a = [r[key] for r in L.sel(L.sel(wm, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                         if np.isfinite(r.get(key, np.nan)) and r.get(key, 0) > 0]
                    b = [r[key] for r in L.sel(L.sel(we, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
                         if np.isfinite(r.get(key, np.nan)) and r.get(key, 0) > 0]
                    if len(a) < 5 or len(b) < 5:
                        continue
                    w = min(len(a), len(b))
                    num += w * np.log(np.median(b) / np.median(a))
                    den += w
                    _ = w
            mc = np.exp(num / den) if den else np.nan
            print("      %-10s %10.2f [%6.2f,%6.2f] %10.2f [%6.2f,%6.2f] %10.2f   %10.2f"
                  % (bn, e["pt"], e["lo"], e["hi"], m["pt"], m["lo"], m["hi"],
                     e["pt"] / m["pt"] if m["pt"] else np.nan, mc))
            OUT["manual"].setdefault(rt, {})[bn] = dict(
                eng=e, man=m, raw_ratio=float(e["pt"] / m["pt"]) if m["pt"] else np.nan,
                matched_ratio=float(mc))


PARTS = dict(census=census, null=null, endpoint=endpoint, bands=bands,
             spectrum=spectrum, manual=manual)

if __name__ == "__main__":
    want = sys.argv[1:] or list(PARTS)
    for p in want:
        PARTS[p]()
    Path(__file__).with_name("_scratch/out/_stock_r97_baseline.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_stock_r97_baseline.json")
