#!/usr/bin/env python3
r"""V87 / route 71, part 3 -- the controls that qualify parts 1 and 2, and two RETRACTIONS.

🛑 RETRACTION 1 -- part 2 Stage 9's "differentiator" is an ARTEFACT.
    `|H| = |Sxy|/Sxx` was computed at coherence 0.035-0.077 against a zero-coherence null of
    1/n_avg = 0.042.  At zero coherence the estimator returns `sqrt(Pyy/Pxx)/sqrt(n_avg)`, and that
    formula reproduces the measured |H| in ALL SEVEN bands to two decimals (checked in Stage 12).
    ⇒ the rise of |H| with frequency is the rise of `sqrt(Pyy/Pxx)`, i.e. nothing but the two
    signals' own spectral shapes.  It carries NO transfer information.

🛑 RETRACTION 2 -- the phase-randomised surrogate used in parts 1 and 2 is a WEAK control for a
    single-window periodogram.  Phase randomisation PRESERVES |X(f)|, so it preserves the line's
    power; only the Hann window's spectral leakage makes the two differ at all.  "real ~= surrogate"
    is therefore close to tautological and must not be read as "no line".
    ⇒ the load-bearing control is the WHITE-NOISE FLOOR at the same `nw` and the PAIRED comparison
    against the column torque on the SAME windows.  Both survive; the surrogate is withdrawn.

WHAT THIS FILE ADDS
    Stage 11  the engaged-vs-manual band comparison, SPEED-MATCHED.  Part 1's version is
              contaminated exactly the way `STATE.md` instrument defect #4 warns: 59 % of the manual
              frames on this route are PARKED (v < 0.2 m/s, |cmd| p50 = 9.6 counts).
    Stage 12  the coherence null, computed not assumed, and the transfer functions re-estimated on
              transparent unclipped windows where the coherence is high enough to mean something.
    Stage 13  the resonance in the command -> column path, with its own null and a shuffled-pairs
              control (window i's command against window j's column).
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
from scipy.signal import butter, filtfilt, csd, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _r31_common as C31        # noqa: E402
from v87_probe_6b98 import CACHE, RATCHET, SAT_WIRE, grid, block_boot  # noqa: E402

RNG = np.random.default_rng(87_31337)
OUT = {}
BANDS = ((0.5, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0), (12.0, 15.0), (15.0, 22.0))


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def band_rms(x, fs, lo, hi):
    b = butter(2, [lo, hi], btype="band", fs=fs)
    return float(np.std(filtfilt(*b, x)))


# =================================================================================================
# STAGE 11 -- what does ENGAGEMENT add to the delivered command?  speed-matched.
# =================================================================================================
def stage11(g):
    hdr("STAGE 11 -- ENGAGED vs MANUAL in the delivered command, SPEED-MATCHED")
    fs, v, lat = g["fs"], np.abs(g["v"]), g["lat"]
    print(f"    manual frames parked (v<0.2): {np.sum(~lat & (v < 0.2)):,} of {np.sum(~lat):,} "
          f"({100*np.mean(v[~lat] < 0.2):.0f} %)  <- part 1's ratio was mostly moving-vs-parked")
    print(f"    engaged frames parked       : {np.sum(lat & (v < 0.2)):,} of {np.sum(lat):,} "
          f"({100*np.mean(v[lat] < 0.2):.0f} %)")

    # per-window band rms so the comparison has a resampling unit, then match on a speed bin
    nw, hop = 256, 128
    recs = []
    for engaged in (True, False):
        m = lat if engaged else ~lat
        for a, b in C31.runs_of(m, g["t"], nw, max_gap=0.10):
            for j0 in range(0, (b - a) - nw + 1, hop):
                sl = slice(a + j0, a + j0 + nw)
                if not np.all(np.isfinite(g["cts"][sl])):
                    continue
                if np.mean(g["wire"][sl] >= SAT_WIRE) > 0:
                    continue
                r = dict(engaged=engaged, blk=f"{int(engaged)}:{a}:{j0//nw}",
                         vmed=float(np.median(v[sl])))
                for lo, hi in BANDS:
                    r[f"b{lo}_{hi}"] = band_rms(g["cts"][sl], fs, lo, hi)
                recs.append(r)
    for lo, hi in ((0.5, 2.0), (2.0, 4.0)):
        E = [r for r in recs if r["engaged"] and lo <= r["vmed"] < hi]
        M = [r for r in recs if not r["engaged"] and lo <= r["vmed"] < hi]
        sub(f"speed bin {lo}-{hi} m/s : engaged n={len(E)}  manual n={len(M)}")
        if len(E) < 4 or len(M) < 4:
            print("      too few windows in one arm -- NOT SCORED (this is the honest answer, not 1.0)")
            continue
        for blo, bhi in BANDS:
            k = f"b{blo}_{bhi}"
            be = block_boot([r[k] for r in E], [r["blk"] for r in E], nboot=3000)
            bm = block_boot([r[k] for r in M], [r["blk"] for r in M], nboot=3000)
            ratio = be["v"] / bm["v"] if bm["v"] else np.nan
            print(f"      {blo:4.1f}-{bhi:4.1f} Hz  engaged {be['v']:7.2f} "
                  f"[{be['lo']:6.2f},{be['hi']:7.2f}]   manual {bm['v']:7.2f} "
                  f"[{bm['lo']:6.2f},{bm['hi']:6.2f}]   ratio {ratio:6.2f}x")
            OUT.setdefault("stage11", {})[f"{lo}-{hi}/{k}"] = dict(eng=be, man=bm, ratio=float(ratio))


# =================================================================================================
# STAGE 12 -- the coherence null, computed.  And Retraction 1, demonstrated.
# =================================================================================================
def stage12(g):
    hdr("STAGE 12 -- THE COHERENCE NULL, COMPUTED -- and part 2 Stage 9 shown to be that null")
    fs, lat = g["fs"], g["lat"]
    x = g["e4tq"][lat] - np.mean(g["e4tq"][lat])
    y = g["cts"][lat] - np.mean(g["cts"][lat])
    f, pxx = welch(x, fs, nperseg=512)
    _, pyy = welch(y, fs, nperseg=512)
    _, pxy = csd(x, y, fs, nperseg=512)
    H = np.abs(pxy) / pxx
    navg = max(1, 2 * len(x) // 512 - 1)
    print(f"    n_avg ~= {navg} Welch segments  =>  E[coh^2 | independent] ~= 1/n_avg = "
          f"{1.0/navg:.3f}")
    print(f"    and at zero coherence  E[|H|] ~= sqrt(Pyy/Pxx)/sqrt(n_avg)\n")
    print(f"    {'band':>9} {'|H| measured':>13} {'null prediction':>16} {'ratio':>7}")
    for lo, hi in ((1, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 20), (20, 24)):
        m = (f >= lo) & (f < hi)
        hm = float(np.nanmean(H[m]))
        hn = float(np.sqrt(np.trapezoid(pyy[m], f[m]) / np.trapezoid(pxx[m], f[m])) / np.sqrt(navg))
        print(f"    {lo:3d}-{hi:<5d} {hm:13.4f} {hn:16.4f} {hm/hn:7.2f}")
    print("\n    ⇒ 🛑 the null reproduces the measurement in every band. Part 2 Stage 9's rising")
    print("      `|H|` is the null's own shape.  THE DIFFERENTIATOR READING IS WITHDRAWN.")

    sub("the same transfer where it CAN mean something: transparent, unclipped, engaged windows")
    b_dc = butter(2, 3.0, btype="low", fs=fs)
    b_rp = butter(2, list(RATCHET), btype="band", fs=fs)
    dc, rp = filtfilt(*b_dc, g["cts"]), filtfilt(*b_rp, g["cts"])
    nw = 256
    sel = []
    for a, b in C31.runs_of(lat, g["t"], nw, max_gap=0.10):
        for j0 in range(0, (b - a) - nw + 1, nw // 2):
            sl = slice(a + j0, a + j0 + nw)
            if np.mean(g["wire"][sl] >= SAT_WIRE) > 0:
                continue
            if dc[sl].min() > 3.0 * np.std(rp[sl]) and np.std(rp[sl]) > 0:
                sel.append(sl)
    print(f"      {len(sel)} transparent unclipped engaged windows of {nw/fs:.2f} s")
    if len(sel) >= 6:
        for nm, (a_sig, b_sig) in (("op cmd -> delivered", ("e4tq", "cts")),
                                   ("delivered -> column", ("cts", "tq"))):
            Sxx = Syy = Sxy = None
            for sl in sel:
                u = g[a_sig][sl] - np.mean(g[a_sig][sl])
                w = g[b_sig][sl] - np.mean(g[b_sig][sl])
                ff, p1 = welch(u, fs, nperseg=nw, nfft=nw)
                _, p2 = welch(w, fs, nperseg=nw, nfft=nw)
                _, p12 = csd(u, w, fs, nperseg=nw, nfft=nw)
                Sxx = p1 if Sxx is None else Sxx + p1
                Syy = p2 if Syy is None else Syy + p2
                Sxy = p12 if Sxy is None else Sxy + p12
            coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
            trans = np.abs(Sxy) / Sxx
            null = 1.0 / len(sel)
            print(f"\n      {nm}   (coh^2 null = 1/{len(sel)} = {null:.3f})")
            print(f"        {'band':>8} {'coh^2':>8} {'coh/null':>9} {'|H|':>10}")
            for lo, hi in ((2, 4), (4, 6), (6, 7), (7, 8), (8, 9), (9, 12), (12, 16), (16, 22)):
                m = (ff >= lo) & (ff < hi)
                c = float(np.mean(coh[m]))
                print(f"        {lo:3d}-{hi:<4d} {c:8.3f} {c/null:9.2f} "
                      f"{float(np.mean(trans[m])):10.4f}")
            OUT.setdefault("stage12", {})[nm] = dict(
                n=len(sel), null=null, f=ff.tolist(), coh=coh.tolist(), H=trans.tolist())


# =================================================================================================
# STAGE 13 -- the command -> column resonance, with a shuffled-pairs control
# =================================================================================================
def stage13(g):
    hdr("STAGE 13 -- THE COMMAND -> COLUMN RESONANCE, against a SHUFFLED-PAIRS control")
    print("    The control pairs window i's delivered command with window j's column torque "
          "(i != j).")
    print("    Any peak that survives shuffling is a property of the two SPECTRA, not of the link.")
    fs, lat = g["fs"], g["lat"]
    nw = 512
    sel = []
    for a, b in C31.runs_of(lat, g["t"], nw, max_gap=0.10):
        for j0 in range(0, (b - a) - nw + 1, nw // 2):
            sl = slice(a + j0, a + j0 + nw)
            if np.mean(g["wire"][sl] >= SAT_WIRE) == 0:
                sel.append(sl)
    n = len(sel)
    print(f"    {n} unclipped engaged windows of {nw/fs:.2f} s  (coh^2 null = {1.0/n:.3f})")
    if n < 6:
        return

    def pooled(pairs):
        Sxx = Syy = Sxy = None
        for si, sj in pairs:
            u = g["cts"][si] - np.mean(g["cts"][si])
            w = g["tq"][sj] - np.mean(g["tq"][sj])
            ff, p1 = welch(u, fs, nperseg=nw, nfft=nw)
            _, p2 = welch(w, fs, nperseg=nw, nfft=nw)
            _, p12 = csd(u, w, fs, nperseg=nw, nfft=nw)
            Sxx = p1 if Sxx is None else Sxx + p1
            Syy = p2 if Syy is None else Syy + p2
            Sxy = p12 if Sxy is None else Sxy + p12
        return ff, np.abs(Sxy) ** 2 / (Sxx * Syy), np.abs(Sxy) / Sxx

    ff, coh, tr = pooled([(s, s) for s in sel])
    shuf_coh, shuf_tr = [], []
    for _ in range(60):
        p = RNG.permutation(n)
        p = np.array([(i + 1) % n if p[i] == i else p[i] for i in range(n)])
        _, c2, t2 = pooled([(sel[i], sel[p[i]]) for i in range(n)])
        shuf_coh.append(c2); shuf_tr.append(t2)
    shuf_coh = np.array(shuf_coh); shuf_tr = np.array(shuf_tr)
    print(f"\n    {'band':>8} {'coh^2':>8} {'shuf p95':>9} {'|tq/cmd|':>10} {'shuf p95':>10} "
          f"{'excess':>8}")
    for lo, hi in ((2, 4), (4, 6), (6, 7), (7, 8), (8, 9), (9, 11), (11, 15), (15, 20)):
        m = (ff >= lo) & (ff < hi)
        c = float(np.mean(coh[m]))
        cs = float(np.percentile(np.mean(shuf_coh[:, m], axis=1), 95))
        t = float(np.mean(tr[m]))
        ts = float(np.percentile(np.mean(shuf_tr[:, m], axis=1), 95))
        print(f"    {lo:3d}-{hi:<4d} {c:8.3f} {cs:9.3f} {t:10.4f} {ts:10.4f} {t/ts:8.2f}x")
    j = int(np.argmin(np.abs(ff - 7.79)))
    print(f"\n    at 7.79 Hz: coh^2 {coh[j]:.3f} vs shuffled p95 "
          f"{np.percentile(shuf_coh[:, j], 95):.3f}   |tq/cmd| {tr[j]:.3f} vs shuffled p95 "
          f"{np.percentile(shuf_tr[:, j], 95):.3f}")
    OUT["stage13"] = dict(n=n, f=ff.tolist(), coh=coh.tolist(), H=tr.tolist(),
                          shuf_coh_p95=np.percentile(shuf_coh, 95, axis=0).tolist(),
                          shuf_H_p95=np.percentile(shuf_tr, 95, axis=0).tolist())


if __name__ == "__main__":
    g = grid()
    only = sys.argv[1:] or None
    for nm, fn in (("11", stage11), ("12", stage12), ("13", stage13)):
        if not only or nm in only:
            fn(g)
    (CACHE / "v87_probe_ctrl.json").write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {CACHE / 'v87_probe_ctrl.json'}")
