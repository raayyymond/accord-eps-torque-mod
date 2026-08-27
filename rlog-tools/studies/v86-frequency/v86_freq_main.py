#!/usr/bin/env python3
"""Driver for the V86 pre-registered frequency test.  See `studies/v86-frequency/v86_freq_test.py` for the instrument."""
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
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V  # noqa: E402

ROOT = V.ROOT
np = np
OUT = V.OUT
RNG = V.RNG
VBINS, MACRO = V.VBINS, V.MACRO


# ---------------------------------------------------------------------------------------------
def inject_recover(rs, f_target, amp, frac=1.0, jitter=0.15, notch_at=None, rng=None):
    """Notch 6f's own line out, add a synthetic line at f_target, re-run the SAME instrument.

    The notch is NARROW (+-0.6 Hz) so the local FLOOR the prominence statistic divides by stays
    intact -- widening it would manufacture the recovery."""
    rng = rng or RNG
    hits, fs_out, proms = [], [], []
    for r in rs:
        x = np.asarray(r["x"], float)
        if notch_at is not None and np.isfinite(notch_at):
            bs = butter(2, [max(notch_at - 0.6, 0.4), notch_at + 0.6], btype="bandstop", fs=r["fs"])
            x = filtfilt(*bs, x)
        n = len(x)
        tt = np.arange(n) / r["fs"]
        f_i = f_target * (1.0 + jitter * (rng.random() - 0.5))
        if frac > 0:
            x = x + frac * amp * np.sin(2 * np.pi * f_i * tt + 2 * np.pi * rng.random())
        q = dict(x=x, fs=r["fs"], v=r["v"], blk=r["blk"], ep=r["ep"], t0=r["t0"])
        V.spectra([q])
        fs_out.append(q["f_free"])
        proms.append(q["p_free"])
        hits.append(abs(q["f_free"] - f_target) <= 0.4)
    return dict(hit=float(np.mean(hits)), f_med=float(np.nanmedian(fs_out)),
                f_lo=float(np.nanpercentile(fs_out, 10)), f_hi=float(np.nanpercentile(fs_out, 90)),
                prom=float(np.nanmedian(proms)), n=len(rs), f_target=float(f_target),
                amp=float(frac * amp))


def main():
    V.hdr("V86 PRE-REGISTERED FREQUENCY TEST -- route 6f (V86) vs route 6e (V85), SPEED-MATCHED\n"
          "    signal `tq` (torsion bar) . NW=%d @ ~101 Hz -> %.4f Hz bins . engaged (`cc_lat`) . "
          "v in [%.1f, %.1f) m/s\n"
          "    PRE-REG: ratio in [%.3f, %.3f] -> peak in [%.1f, %.1f] Hz;  FALSIFIED if it stays "
          "at %.2f Hz" % (V.NW, 101.04 / V.NW, V.VLO, V.VHI, V.RATIO_LO, V.RATIO_HI,
                          V.PREREG_LO, V.PREREG_HI, MACRO))

    W = {}
    for name, (c, p, s) in V.ROUTES.items():
        for arm, en in (("engaged", True), ("manual", False)):
            W[(name, arm)] = V.spectra(V.windows(name, c, p, s, engaged=en))
    E = {k[0]: V.in_speed(v) for k, v in W.items() if k[1] == "engaged"}
    M = {k[0]: V.in_speed(v) for k, v in W.items() if k[1] == "manual"}

    # ---- §0 block-bootstrap legitimacy ------------------------------------------------------
    V.hdr("S0  IS THE BLOCK BOOTSTRAP LEGITIMATE?  6f is ONE 141 s engaged episode -> an EPISODE\n"
          "    bootstrap has n=1 and cannot run.  Resampling unit = `blk`, a ~10.13 s CONTIGUOUS\n"
          "    block.  Windows overlap 50%, so lag-1 correlation is EXPECTED by construction;\n"
          "    lag-2 is the first NON-overlapping pair and is the number that licenses the block.")
    OUT["autocorr"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        OUT["autocorr"][nm] = dict(
            f_free=V.autocorr_check(E[nm], "f_free", nm + " f_free"),
            p_free=V.autocorr_check(E[nm], "p_free", nm + " p_free"))

    # ---- §1 THE VERDICT ---------------------------------------------------------------------
    V.hdr("S1  THE VERDICT -- free 5-12 Hz prominence argmax, speed-stratified, block CI")
    print("%-12s %4s %4s | %26s | %24s | %16s"
          % ("build/route", "n", "blk", "f_c (Hz) speed-matched", "centroid 5-11 Hz", "bin counts"))
    OUT["f_c"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70", "V81/r67", "V84/r6d"):
        rs = E[nm]
        if len(rs) < 4:
            print("%-12s %4d   -- too few speed-matched windows --" % (nm, len(rs)))
            continue
        fc = V.block_boot([r["f_free"] for r in rs], [r["blk"] for r in rs])
        ct = V.block_boot([r["cent"] for r in rs], [r["blk"] for r in rs])
        cnt = [sum(1 for r in rs if lo <= r["v"] < hi) for lo, hi in VBINS]
        print("%-12s %4d %4d | %8.3f [%7.3f,%7.3f] | %7.3f [%6.3f,%6.3f] | %16s"
              % (nm, fc[3], fc[4], fc[0], fc[1], fc[2], ct[0], ct[1], ct[2], str(cnt)))
        OUT["f_c"][nm] = dict(f_free=list(fc), centroid=list(ct), bins=cnt)

    print("\n  RATIO f(A)/f(B), speed-STRATIFIED, both arms block-bootstrapped independently:")
    OUT["ratio"] = {}
    for A, B in (("V86/r6f", "V85/r6e"), ("V86/r6f", "V86B/r70"), ("V86B/r70", "V85/r6e"),
                 ("V86/r6f", "V81/r67")):
        if len(E[A]) < 4 or len(E[B]) < 4:
            continue
        for key in ("f_free", "cent"):
            r = V.strat_block_boot_ratio(E[A], E[B], key=key)
            tag = "argmax" if key == "f_free" else "centroid"
            print("    %-5s/%-5s %-9s fA %6.3f  fB %6.3f  ratio %6.3f [%6.3f,%6.3f]   "
                  "nA %3d/%2dblk  nB %3d/%2dblk  w %s"
                  % (A.split("/")[0], B.split("/")[0], tag, r["fA"], r["fB"], r["ratio"],
                     r["lo"], r["hi"], r["nA"], r["blkA"], r["nB"], r["blkB"], r["weights"]))
            OUT["ratio"]["%s|%s|%s" % (A, B, key)] = r

    # ---- ORDER-CLEAN -------------------------------------------------------------------------
    print("\n  WHEEL-ORDER-CLEAN re-run (drop any window whose order 1-4 line lands in 5-12 Hz):")
    OUT["order_clean"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        rc = V.order_clean(E[nm])
        if len(rc) < 4:
            print("    %-12s n=%d  -- too few --" % (nm, len(rc)))
            continue
        fc = V.block_boot([r["f_free"] for r in rc], [r["blk"] for r in rc])
        print("    %-12s n=%3d/%2dblk  f_c %7.3f [%6.3f,%6.3f]   (raw n=%d)"
              % (nm, fc[3], fc[4], fc[0], fc[1], fc[2], len(E[nm])))
        OUT["order_clean"][nm] = dict(f_free=list(fc), n_raw=len(E[nm]))
    rA, rB = V.order_clean(E["V86/r6f"]), V.order_clean(E["V85/r6e"])
    if len(rA) >= 4 and len(rB) >= 4:
        r = V.strat_block_boot_ratio(rA, rB)
        print("    ORDER-CLEAN ratio V86/V85 = %.3f [%.3f,%.3f]   fA %.3f  fB %.3f"
              % (r["ratio"], r["lo"], r["hi"], r["fA"], r["fB"]))
        OUT["order_clean"]["ratio_V86_V85"] = r

    # ---- SPEED INVARIANCE --------------------------------------------------------------------
    print("\n  SPEED-INVARIANCE of the line (the whole cross-route comparison rests on it):")
    OUT["speed_slope"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        rs = E[nm]
        if len(rs) < 6:
            continue
        v = np.array([r["v"] for r in rs]); ff = np.array([r["f_free"] for r in rs])
        ok = np.isfinite(ff)
        sl = float(np.polyfit(v[ok], ff[ok], 1)[0])
        g = {}
        for r in rs:
            g.setdefault(r["blk"], []).append(r)
        ks = list(g); d = []
        for _ in range(2000):
            rr = [x for i in RNG.integers(0, len(ks), len(ks)) for x in g[ks[i]]]
            vv = np.array([x["v"] for x in rr]); f2 = np.array([x["f_free"] for x in rr])
            o = np.isfinite(f2)
            if len(set(np.round(vv[o], 3))) < 3:
                continue
            d.append(np.polyfit(vv[o], f2[o], 1)[0])
        lo, hi = (np.percentile(d, [2.5, 97.5]) if len(d) > 50 else (np.nan, np.nan))
        print("    %-12s d(f_c)/dv = %+7.4f [%+7.4f,%+7.4f] Hz per m/s   "
              "(order 2 predicts +0.961, a fixed line 0.000)" % (nm, sl, lo, hi))
        OUT["speed_slope"][nm] = [sl, float(lo), float(hi)]
        parts = []
        for lo2, hi2 in VBINS:
            m2 = [r["f_free"] for r in rs if lo2 <= r["v"] < hi2]
            if len(m2) >= 2:
                parts.append("%.2f-%.2f: n=%d f=%.2f" % (lo2, hi2, len(m2), np.median(m2)))
        print("                 per bin: " + "   ".join(parts))

    # ---- §2 SUPPORTING PICTURE ---------------------------------------------------------------
    V.hdr("S2  THE SUPPORTING PICTURE")
    cA = np.array([sum(1 for r in E["V86/r6f"] if lo <= r["v"] < hi) for lo, hi in VBINS], float)
    cB = np.array([sum(1 for r in E["V85/r6e"] if lo <= r["v"] < hi) for lo, hi in VBINS], float)
    c70 = np.array([sum(1 for r in E["V86B/r70"] if lo <= r["v"] < hi) for lo, hi in VBINS], float)
    w = np.minimum(cA, cB)
    f6f, S6f = V.matched_mean_spectrum(E["V86/r6f"], w, "R")
    _, S6e = V.matched_mean_spectrum(E["V85/r6e"], w, "R")
    _, P6f = V.matched_mean_spectrum(E["V86/r6f"], w, "P")
    _, P6e = V.matched_mean_spectrum(E["V85/r6e"], w, "P")
    _, S70 = V.matched_mean_spectrum(E["V86B/r70"], np.minimum(cA, c70), "R")
    m = (f6f >= 4.0) & (f6f <= 12.0)
    print("  Speed-matched ENGAGED mean PROMINENCE spectrum, 4-12 Hz (floor-normalised):")
    print("    %6s %9s %9s %9s | %11s %11s"
          % ("Hz", "V86/6f", "V85/6e", "V86B/70", "V86 power", "V85 power"))
    rows = []
    for j in np.flatnonzero(m):
        if j % 2:
            continue
        print("    %6.2f %9.3f %9.3f %9.3f | %11.3e %11.3e"
              % (f6f[j], S6f[j], S6e[j], S70[j], P6f[j], P6e[j]))
        rows.append([float(f6f[j]), float(S6f[j]), float(S6e[j]), float(S70[j]),
                     float(P6f[j]), float(P6e[j])])
    OUT["mean_spectrum"] = dict(cols=["hz", "V86_prom", "V85_prom", "V86B_prom",
                                      "V86_power", "V85_power"], rows=rows,
                                weights=[float(x) for x in w])
    OUT["mean_argmax"] = {}
    mm = (f6f >= 5.0) & (f6f <= 12.0)
    for nm, S, P in (("V86/r6f", S6f, P6f), ("V85/r6e", S6e, P6e), ("V86B/r70", S70, P6f * np.nan)):
        j = int(np.nanargmax(np.where(mm, S, -np.inf)))
        print("  mean-spectrum argmax %-10s %.3f Hz   prominence %.3f" % (nm, f6f[j], S[j]))
        OUT["mean_argmax"][nm] = [float(f6f[j]), float(S[j])]

    print("\n  AMPLITUDE vs FLOOR, separated (the 'V85 3.2x more prominent' floor-effect trap):")
    print("    %-12s %4s | %24s | %24s | %24s | %22s"
          % ("build", "n", "p99 env @ its OWN f_c", "p99 env @ 7.79 Hz", "local FLOOR power",
             "prominence"))
    OUT["amp_floor"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        rs = E[nm]
        if len(rs) < 4:
            continue
        fcm = OUT["f_c"][nm]["f_free"][0]
        for r in rs:
            r["a_own"] = V.band_amp(r, fcm, 1.0)
            r["a_779"] = V.band_amp(r, MACRO, 1.0)
        u = [r["blk"] for r in rs]
        ao = V.block_boot([r["a_own"] for r in rs], u)
        a7 = V.block_boot([r["a_779"] for r in rs], u)
        fl = V.block_boot([r["floor_at"] for r in rs], u)
        pr = V.block_boot([r["p_free"] for r in rs], u)
        print("    %-12s %4d | %8.1f [%6.1f,%6.1f] | %8.1f [%6.1f,%6.1f] | %9.3e [%8.2e,%8.2e] "
              "| %6.2f [%5.2f,%5.2f]"
              % (nm, len(rs), ao[0], ao[1], ao[2], a7[0], a7[1], a7[2],
                 fl[0], fl[1], fl[2], pr[0], pr[1], pr[2]))
        OUT["amp_floor"][nm] = dict(a_own=list(ao), a_779=list(a7), floor=list(fl),
                                    prom=list(pr), f_c=fcm)

    print("\n  WITHIN-ROUTE control on 6f alone -- ENGAGED vs MANUAL (no cross-route matching):")
    OUT["eng_man_6f"] = {}
    fc6f = OUT["f_c"]["V86/r6f"]["f_free"][0]
    for arm, rs in (("engaged", E["V86/r6f"]), ("manual", M["V86/r6f"])):
        if len(rs) < 4:
            print("    %-8s n=%d  -- too few --" % (arm, len(rs)))
            continue
        for r in rs:
            r["a_own"] = V.band_amp(r, fc6f, 1.0)
        u = [r["blk"] for r in rs]
        fc = V.block_boot([r["f_free"] for r in rs], u)
        ao = V.block_boot([r["a_own"] for r in rs], u)
        pr = V.block_boot([r["p_free"] for r in rs], u)
        print("    %-8s n=%3d/%2dblk  f_c %6.3f [%5.3f,%5.3f]  amp@%.2fHz %7.1f [%6.1f,%6.1f]  "
              "prom %5.2f [%4.2f,%4.2f]"
              % (arm, len(rs), fc[4], fc[0], fc[1], fc[2], fc6f, ao[0], ao[1], ao[2],
                 pr[0], pr[1], pr[2]))
        OUT["eng_man_6f"][arm] = dict(f_free=list(fc), amp=list(ao), prom=list(pr), n=len(rs))
    if "engaged" in OUT["eng_man_6f"] and "manual" in OUT["eng_man_6f"]:
        e, m2 = OUT["eng_man_6f"]["engaged"], OUT["eng_man_6f"]["manual"]
        print("    ENG/MAN amplitude ratio %.2f   (the ratchet is engaged-only on record: 44/46)"
              % (e["amp"][0] / m2["amp"][0]))
        OUT["eng_man_6f"]["ratio"] = e["amp"][0] / m2["amp"][0]

    # ---- §3 POWER ----------------------------------------------------------------------------
    V.hdr("S3  THE FALSIFIER'S OWN HEALTH CHECK -- COULD a 0.843x shift have FIRED on 6f?\n"
          "    Notch 6f's own line out (+-0.6 Hz, floor left INTACT), inject a synthetic line at\n"
          "    the PREDICTED frequency at a MEASURED amplitude, re-run the SAME instrument.")
    rs6f = E["V86/r6f"]
    amp_meas = OUT["amp_floor"]["V85/r6e"]["a_own"][0]
    amp_6f = OUT["amp_floor"]["V86/r6f"]["a_own"][0]
    f_meas_6f = OUT["f_c"]["V86/r6f"]["f_free"][0]
    f_V85 = OUT["f_c"]["V85/r6e"]["f_free"][0]
    f_pred = f_V85 * 0.843
    print("    measured line amplitude: V85 %.1f ct . V86 %.1f ct   predicted frequency %.3f Hz"
          " (= 0.843 x V85's speed-matched %.3f Hz)" % (amp_meas, amp_6f, f_pred, f_V85))
    OUT["power"] = dict(amp_V85=amp_meas, amp_V86=amp_6f, f_pred=f_pred,
                        f_meas_6f=f_meas_6f, f_V85=f_V85, runs=[])
    print("\n    %12s %8s %6s | %18s | %16s %16s | %6s"
          % ("inject @ Hz", "amp ct", "frac", "recovery hit rate", "recovered f_med", "p10-p90",
             "prom"))
    for tag, ftgt in (("PREDICTED 0.843x", f_pred), ("PRE-REG midpoint", 6.55),
                      ("V85 line (ctrl)", f_V85)):
        for frac in (1.0, 0.5, 0.25):
            rr = inject_recover(rs6f, ftgt, amp_meas, frac=frac, notch_at=f_meas_6f)
            print("    %12.3f %8.1f %6.2f | %17.1f%% | %16.3f %16s | %6.2f   <- %s"
                  % (ftgt, rr["amp"], frac, 100 * rr["hit"], rr["f_med"],
                     "%.2f-%.2f" % (rr["f_lo"], rr["f_hi"]), rr["prom"], tag))
            rr["tag"] = tag
            OUT["power"]["runs"].append(rr)
    rr0 = inject_recover(rs6f, f_pred, 0.0, frac=0.0, notch_at=f_meas_6f)
    print("    %12s %8.1f %6.2f | %17.1f%% | %16.3f %16s | %6.2f   <- NOTCHED, NO INJECTION (null)"
          % ("--", 0.0, 0.0, 100 * rr0["hit"], rr0["f_med"],
             "%.2f-%.2f" % (rr0["f_lo"], rr0["f_hi"]), rr0["prom"]))
    OUT["power"]["null"] = rr0

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test.json"))


if __name__ == "__main__":
    main()
