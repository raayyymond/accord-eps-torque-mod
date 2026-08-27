#!/usr/bin/env python3
"""Follow-ups to `studies/misc/retrodiction_bias_r6e.py`.

  S1  RESCUE R2.  The within-route engaged/manual test is the confound-free one, and it returned
      NaN on V84 and V85 -- the two builds that carry the zero-bias condition -- because their
      engaged and manual arms share no speed bin below 35 km/h at the original bin width.  Retry
      with COARSER bins and a lower per-bin minimum, and report the per-bin occupancy so the
      failure (if it persists) is visible rather than hidden behind a NaN.

  S2  SECOND METHOD for R1.  R1 used band-pass + Hilbert p99.  Redo it with FFT BAND POWER over the
      same 7.2-8.4 Hz -- a different estimator on the same windows.  A dose-response that survives
      both is not an estimator artefact.

  S3  THE ~20 Hz FEATURE.  R4's coarse spectrum showed V85 at **+1.2 dB at 20 Hz** where V84 read
      -8.8 and V81 -10.3, i.e. a LOCAL PEAK on V85 that the other two do not have, sitting inside
      the 18-22 Hz grinding band.  Resolve 14-26 Hz finely and check whether it is a line, and
      whether it is engagement-conditional.
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
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import retrodiction_bias_r6e as RB  # noqa: E402  -- windowing, dose ledger, bootstrap
import score_v85_r6e_bands as SB  # noqa: E402
import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402

ORDER, V_CREEP = RB.ORDER, RB.V_CREEP
RNG = np.random.default_rng(85_6340)
OUT = {}

COARSE = [(0.0, 2.0), (2.0, 5.0), (5.0, 9.72)]


def s1(W, dose):
    RB.hdr("S1  RESCUE THE WITHIN-ROUTE TEST -- coarser speed bins (0-2, 2-5, 5-9.72 m/s),\n"
           "    min 3 windows per bin per arm, and the OCCUPANCY printed so a failure is visible.")
    print(f"    {'build':10s} {'bias':>12s} | " + " ".join(f"{f'{lo:g}-{hi:g}':>12s}"
                                                           for lo, hi in COARSE)
          + f" | {'eng/man LINE':>22s} {'bins':>4s} | {'eng/man NEG':>20s}")
    OUT["s1"] = {}
    for b in ORDER:
        e = [r for r in W[b] if r["arm"] == "engaged" and r["v"] < V_CREEP]
        m = [r for r in W[b] if r["arm"] == "manual" and r["v"] < V_CREEP]
        occ = []
        for lo, hi in COARSE:
            ne = sum(1 for r in e if lo <= r["v"] < hi)
            nm = sum(1 for r in m if lo <= r["v"] < hi)
            occ.append(f"{ne:5d}/{nm:<6d}")
        r1 = RB.binned_ratio(e, m, "a779", vb=COARSE, min_n=3)
        r2 = RB.binned_ratio(e, m, "aneg", vb=COARSE, min_n=3)
        print(f"    {b:10s} {dose[b]['bias']:12,d} | " + " ".join(occ)
              + f" | {r1[0]:7.3f} [{r1[1]:6.3f},{r1[2]:6.3f}] {r1[3]:4d} | "
                f"{r2[0]:6.3f} [{r2[1]:5.3f},{r2[2]:5.3f}]")
        OUT["s1"][b] = dict(bias=dose[b]["bias"], occupancy=occ, line=list(r1), neg=list(r2))
    print("\n    occupancy is  engaged/manual  windows per bin.  A bin needs >= 3 on BOTH arms.")


def s2(W, dose):
    RB.hdr("S2  SECOND METHOD for R1 -- FFT BAND POWER over 7.2-8.4 Hz instead of Hilbert p99.\n"
           "    Same windows, different estimator.  Reference V85 = 1.000.")
    from _r31_common import periodogram
    for b in ORDER:
        for r in W[b]:
            r["pw"] = np.nan
    # recompute from the raw caches, since `windows` kept only the envelope statistics
    for b in ORDER:
        B = G.BUILDS[b]
        idx = {}
        for r in W[b]:
            idx.setdefault((r["seg"], r["arm"]), []).append(r)
        for s in B["segs"]:
            if s in SB.S.PARKED.get(b, []):
                continue
            p = B["cache"] / f"{B['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = C31.load(s, B["cache"], B["pfx"])
            t = np.asarray(d["t"], float); tq = np.asarray(d["tq"], float)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            fs = C31.fs_of(d)
            f = np.fft.rfftfreq(RB.NW, 1.0 / fs)
            ml = (f >= 7.2) & (f <= 8.4)
            mn = (f >= 32.0) & (f <= 38.0)
            for arm, mask in (("engaged", lat), ("manual", ~lat)):
                rs = idx.get((s, arm), [])
                k = 0
                for a, bb in C31.runs_of(mask, t, RB.NW):
                    for j in range(0, (bb - a) - RB.NW + 1, RB.HOPW):
                        if not np.all(np.isfinite(tq[a:bb][j:j + RB.NW])):
                            continue
                        P = periodogram(tq[a:bb][j:j + RB.NW], fs, nfft=RB.NW, detrend=True)
                        if P is not None and k < len(rs):
                            rs[k]["pw"] = float(np.mean(P[ml]))
                            rs[k]["pwn"] = float(np.mean(P[mn]))
                        k += 1
    ref = [r for r in W["V85/r6e"] if r["arm"] == "engaged" and r["v"] < V_CREEP]
    print(f"    {'build':10s} {'bias':>12s} | {'FFT band power vs V85':>24s} {'bins':>4s} | "
          f"{'sqrt(power) ratio':>18s} | {'R1 Hilbert':>10s}")
    OUT["s2"] = {}
    for b in ORDER:
        e = [r for r in W[b] if r["arm"] == "engaged" and r["v"] < V_CREEP]
        if len(e) < 8:
            continue
        rr = RB.binned_ratio(e, ref, "pw")
        amp = np.sqrt(rr[0]) if np.isfinite(rr[0]) else np.nan
        h = RB.OUT["r1"].get(b, {}).get("line", [np.nan])[0]
        print(f"    {b:10s} {dose[b]['bias']:12,d} | {rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}]"
              f" {rr[3]:4d} | {amp:18.3f} | {h:10.3f}")
        OUT["s2"][b] = dict(power=list(rr), amp=float(amp), hilbert=float(h))
    rows = [(b, dose[b]["bias"], OUT["s2"][b]["amp"]) for b in OUT["s2"]]
    if len(rows) >= 4:
        from scipy.stats import spearmanr
        d_ = np.array([r[1] for r in rows], float); a_ = np.array([r[2] for r in rows], float)
        sr = spearmanr(d_, a_)
        print(f"\n    Spearman(bias, sqrt-power amplitude ratio) rho = {sr.statistic:+.3f}  "
              f"p = {sr.pvalue:.3f}   (R1's Hilbert version: rho = "
              f"{RB.OUT['r3']['rho_line']:+.3f})")
        z = [r[2] for r in rows if r[1] == 0]; nz = [r[2] for r in rows if r[1] > 0]
        print(f"    zero-bias median {np.median(z):.3f}   bias median {np.median(nz):.3f}   "
              f"separation {np.median(z)/np.median(nz):.2f}x")
        OUT["s2"]["_rho"] = float(sr.statistic)
        OUT["s2"]["_sep"] = float(np.median(z) / np.median(nz))


def s3():
    RB.hdr("S3  THE ~20 Hz FEATURE.  R4's coarse grid put V85 at +1.2 dB at 20 Hz where V84 read\n"
           "    -8.8 and V81 -10.3.  Resolve 14-26 Hz finely, engaged AND manual, to see whether\n"
           "    it is a real line and whether it is engagement-conditional.")
    from _r31_common import periodogram
    NF = 1024
    OUT["s3"] = {}
    for b in ("V85/r6e", "V84/r6d", "V81/r67"):
        B = G.BUILDS[b]
        for arm_name, want in (("engaged", True), ("manual", False)):
            acc, f = [], None
            for s in B["segs"]:
                if s in SB.S.PARKED.get(b, []):
                    continue
                p = B["cache"] / f"{B['pfx']}{s}.npz"
                if not p.exists():
                    continue
                d = C31.load(s, B["cache"], B["pfx"])
                t = np.asarray(d["t"], float); tq = np.asarray(d["tq"], float)
                lat = np.asarray(d["cc_lat"], float) > 0.5
                v = np.asarray(d["cs_v"], float)
                fs = C31.fs_of(d)
                mask = (lat if want else ~lat) & (np.abs(v) < V_CREEP)
                for a, bb in C31.runs_of(mask, t, NF):
                    for j in range(0, (bb - a) - NF + 1, NF // 2):
                        P = periodogram(tq[a:bb][j:j + NF], fs, nfft=NF, detrend=True)
                        if P is not None:
                            acc.append(P); f = np.fft.rfftfreq(NF, 1.0 / fs)
            if len(acc) < 5:
                print(f"    {b:10s} {arm_name:8s} n={len(acc)}  -- too few --")
                continue
            M = np.median(np.array(acc), axis=0)
            i12 = int(np.argmin(np.abs(f - 12.0)))
            M = M / M[i12]
            band = (f >= 14.0) & (f <= 26.0)
            db = 10 * np.log10(M[band])
            fb = f[band]
            pk = int(np.argmax(db))
            # local prominence of that peak against a +-2 Hz median floor
            fl = np.median(M[(np.abs(f - fb[pk]) <= 2.5) & (np.abs(f - fb[pk]) > 0.8)])
            print(f"    {b:10s} {arm_name:8s} n={len(acc):4d}  peak in 14-26 Hz at "
                  f"{fb[pk]:5.2f} Hz  {db[pk]:+6.1f} dB re 12 Hz   prominence over its own "
                  f"floor {M[band][pk]/fl:5.2f}x")
            OUT["s3"][f"{b}|{arm_name}"] = dict(n=len(acc), f_peak=float(fb[pk]),
                                                db=float(db[pk]),
                                                prom=float(M[band][pk] / fl),
                                                curve=[[float(x), float(y)]
                                                       for x, y in zip(fb[::2], db[::2])])
    print("\n    prominence ~1 means the 'peak' is just the top of a smooth roll-off, not a line.")
    for k, v in OUT["s3"].items():
        print(f"      {k:22s} f {v['f_peak']:5.2f} Hz  prominence {v['prom']:.2f}x  "
              f"{'A LINE' if v['prom'] > 1.6 else 'not a line'}")


def main():
    dose = RB.r0()
    SB.register()
    W = {b: RB.windows(b) for b in ORDER}
    # R1 must exist for S2's comparison column
    ref = [r for r in W["V85/r6e"] if r["arm"] == "engaged" and r["v"] < V_CREEP]
    RB.OUT["r1"] = {}
    for b in ORDER:
        e = [r for r in W[b] if r["arm"] == "engaged" and r["v"] < V_CREEP]
        if len(e) >= 8:
            RB.OUT["r1"][b] = dict(line=list(RB.binned_ratio(e, ref, "a779")))
    rows = [(b, dose[b]["bias"], RB.OUT["r1"][b]["line"][0]) for b in RB.OUT["r1"]]
    from scipy.stats import spearmanr
    RB.OUT["r3"] = dict(rho_line=float(spearmanr([r[1] for r in rows],
                                                 [r[2] for r in rows]).statistic))
    s1(W, dose)
    s2(W, dose)
    s3()
    (ROOT / "_scratch/cache/r6e" / "retrodiction_bias_b.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {ROOT / '_scratch/cache/r6e' / 'retrodiction_bias_b.json'}")


if __name__ == "__main__":
    main()
