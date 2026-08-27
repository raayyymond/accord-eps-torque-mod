#!/usr/bin/env python3
"""TRANSMISSIBILITY bar -> chassis, and whether it can be measured AT ALL.

🛑 THE POSITIVE CONTROL COMES FIRST.  `studies/estimator-qc/imu_ceiling.py` found bar->IMU coherence at the chance
floor at every frequency.  A null coherence is worthless without proof the estimator can see a
coupling that MUST be there -- otherwise "no transmission" and "broken pipeline" look identical.
So P0 runs the identical estimator on pairs whose coupling is not in doubt:
    tq <-> rate_c   (bar torque and column angle rate -- same mechanical node)
    tq <-> sc_tq    (bar torque against the SAME quantity from a different CAN message)
Only if those come back high is a null on the IMU informative.

Power is maximised: every engaged sample from every available route, nperseg 256 with 75%
overlap, so the 95% chance floor drops to ~0.01 instead of the 0.07-0.21 of the first pass.
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
from scipy.signal import coherence, csd, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
O = {}
ROUTES = ("V86/r6f", "V85/r6e", "V86B/r70", "V84/r6d", "V81/r67")
NPS, NOV = 256, 192


def runs(nm, engaged=True, minlen=NPS * 2, speed=True):
    cache, pfx, segs = V.ROUTES[nm]
    for s in segs:
        p = ROOT / cache / ("%s%d.npz" % (pfx, s))
        if not p.exists():
            continue
        d = C31.load(s, ROOT / cache, pfx)
        t = np.asarray(d["t"], float)
        fs = C31.fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.asarray(d["cs_v"], float)
        m = lat if engaged else ~lat
        if speed:
            m = m & (v >= V.VLO) & (v < V.VHI)
        for a, b in C31.runs_of(m, t, minlen):
            yield d, a, b, fs


def pooled_coherence(nm_list, xk, yk, engaged=True, speed=True):
    """Welch coherence pooled over every qualifying run in every route named."""
    Sxy = Sxx = Syy = None
    n = 0
    fout = None
    for nm in nm_list:
        for d, a, b, fs in runs(nm, engaged, speed=speed):
            x = np.asarray(d.get(xk, np.full(len(d["t"]), np.nan)), float)[a:b]
            y = np.asarray(d.get(yk, np.full(len(d["t"]), np.nan)), float)[a:b]
            if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                continue
            x, y = x - x.mean(), y - y.mean()
            if x.std() == 0 or y.std() == 0:
                continue
            f, pxy = csd(x, y, fs=fs, nperseg=NPS, noverlap=NOV)
            _, pxx = welch(x, fs=fs, nperseg=NPS, noverlap=NOV)
            _, pyy = welch(y, fs=fs, nperseg=NPS, noverlap=NOV)
            k = (len(x) - NOV) // (NPS - NOV)
            Sxy = pxy * k if Sxy is None else Sxy + pxy * k
            Sxx = pxx * k if Sxx is None else Sxx + pxx * k
            Syy = pyy * k if Syy is None else Syy + pyy * k
            n += k
            fout = f
    if Sxy is None or n < 4:
        return None, None, None, 0
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    gain = np.abs(Sxy) / Sxx                       # H1 estimator |Y/X|
    return fout, coh, gain, n


def band(f, y, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.mean(y[m])) if m.any() else np.nan


BANDS = [(5, 8), (8, 11), (11, 14), (14, 17), (17, 20), (20, 23), (23, 26),
         (26, 29), (29, 33), (33, 38), (38, 45)]


def main():
    ALL = list(ROUTES)
    NEW = ["V86/r6f", "V85/r6e", "V86B/r70"]

    V.hdr("P0  🛑 POSITIVE CONTROL FIRST.  Identical estimator, pairs whose coupling is NOT in\n"
          "    doubt.  If these do not come back high, a null on the IMU means nothing.")
    O["p0"] = {}
    print("    %-26s %6s %7s | %s" % ("pair", "n seg", "floor", "  ".join(
        "%d-%d" % b for b in BANDS)))
    for xk, yk, lab in (("tq", "rate_c", "bar torque <-> column angle rate"),
                        ("tq", "sc_tq", "bar torque <-> same via other msg"),
                        ("tq", "tq", "bar torque <-> ITSELF (=1.0)")):
        f, coh, gain, n = pooled_coherence(ALL, xk, yk)
        if f is None:
            print("    %-26s -- unavailable --" % lab)
            continue
        floor = 1.0 - 0.05 ** (1.0 / max(n - 1, 1))
        print("    %-26s %6d %7.4f | %s" % (lab, n, floor,
              "  ".join("%.3f" % band(f, coh, lo, hi) for lo, hi in BANDS)))
        O["p0"][lab] = dict(n=n, floor=float(floor),
                            coh=[float(band(f, coh, lo, hi)) for lo, hi in BANDS])

    V.hdr("P1  THE TEST -- bar torque -> every chassis-side channel available.\n"
          "    Engaged, speed-matched, pooled over all routes.  Coherence first: the\n"
          "    transmissibility GAIN is only meaningful where coherence clears the floor.")
    O["p1"] = {}
    print("    %-26s %6s %7s | %s" % ("pair", "n seg", "floor", "  ".join(
        "%d-%d" % b for b in BANDS)))
    for yk, lab in (("imu_vert", "bar -> IMU vertical"), ("imu_lat", "bar -> IMU lateral"),
                    ("cs_yaw", "bar -> yaw rate"), ("ws_fl", "bar -> wheel speed FL")):
        f, coh, gain, n = pooled_coherence(ALL, "tq", yk)
        if f is None:
            print("    %-26s -- unavailable --" % lab)
            continue
        floor = 1.0 - 0.05 ** (1.0 / max(n - 1, 1))
        cb = [band(f, coh, lo, hi) for lo, hi in BANDS]
        print("    %-26s %6d %7.4f | %s" % (lab, n, floor,
              "  ".join(("%.3f" % c) + ("*" if c > floor else " ") for c in cb)))
        O["p1"][lab] = dict(n=n, floor=float(floor), coh=[float(c) for c in cb],
                            gain=[float(band(f, gain, lo, hi)) for lo, hi in BANDS],
                            f=[float(x) for x in f], coh_full=[float(x) for x in coh],
                            gain_full=[float(x) for x in gain])
    print("\n    (* = clears the 95%% chance floor.)")

    V.hdr("P2  IS THE COUPLING THERE AT ALL, ANYWHERE?  Best-case reading: the single largest\n"
          "    coherence over 5-45 Hz for each chassis channel, and how it compares to floor.")
    O["p2"] = {}
    for lab, rec in O["p1"].items():
        f = np.array(rec["f"]); c = np.array(rec["coh_full"])
        m = (f >= 5) & (f <= 45)
        j = int(np.argmax(np.where(m, c, -np.inf)))
        print("    %-26s peak coherence %.4f at %6.2f Hz   floor %.4f   ratio %.2f"
              % (lab, c[j], f[j], rec["floor"], c[j] / rec["floor"]))
        O["p2"][lab] = dict(peak=float(c[j]), at=float(f[j]), floor=rec["floor"])

    V.hdr("P3  THE BAR-SIDE SPECTRUM 15-45 Hz -- the LANDING-ZONE map.  This does NOT need the\n"
          "    IMU: `tq` is on the 101 Hz CAN grid, so it is honest to ~45 Hz.  Speed-matched\n"
          "    engaged mean prominence, the three new routes.")
    E = {}
    for nm in NEW:
        c, p, s = V.ROUTES[nm]
        E[nm] = V.in_speed(V.spectra(V.windows(nm, c, p, s, engaged=True)))
    VB = V.VBINS
    cA = np.array([sum(1 for r in E["V86/r6f"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    cB = np.array([sum(1 for r in E["V85/r6e"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    c70 = np.array([sum(1 for r in E["V86B/r70"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    w = np.minimum(cA, cB)
    f, S6f = V.matched_mean_spectrum(E["V86/r6f"], w, "R")
    _, S6e = V.matched_mean_spectrum(E["V85/r6e"], w, "R")
    _, S70 = V.matched_mean_spectrum(E["V86B/r70"], np.minimum(cA, c70), "R")
    print("    %6s %9s %9s %9s   %s" % ("Hz", "V86/6f", "V85/6e", "V86B/70", "note"))
    rows = []
    for j in np.flatnonzero((f >= 15.0) & (f <= 45.0)):
        if j % 3:
            continue
        mx = max(S6f[j], S6e[j], S70[j])
        note = "<-- LINE" if mx > 4 else ("quiet" if mx < 1.6 else "")
        print("    %6.2f %9.2f %9.2f %9.2f   %s" % (f[j], S6f[j], S6e[j], S70[j], note))
        rows.append([float(f[j]), float(S6f[j]), float(S6e[j]), float(S70[j])])
    O["p3"] = dict(cols=["hz", "V86", "V85", "V86B"], rows=rows)
    print("\n    QUIETEST 2 Hz WINDOW in 24-45 Hz, by the worst of the three routes:")
    best = None
    for lo in np.arange(24.0, 43.1, 0.5):
        m = (f >= lo) & (f < lo + 2)
        if not m.any():
            continue
        worst = max(np.nanmean(S6f[m]), np.nanmean(S6e[m]), np.nanmean(S70[m]))
        if best is None or worst < best[1]:
            best = (lo, worst)
        print("      %5.1f-%5.1f Hz  worst-route mean prominence %6.2f" % (lo, lo + 2, worst))
    print("    => quietest landing window: %.1f-%.1f Hz (worst-route prominence %.2f)"
          % (best[0], best[0] + 2, best[1]))
    O["p3_landing"] = dict(lo=float(best[0]), hi=float(best[0] + 2), prom=float(best[1]))

    (ROOT / "_scratch/cache/r6f" / "transmissibility.json").write_text(
        json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "transmissibility.json"))


if __name__ == "__main__":
    main()
