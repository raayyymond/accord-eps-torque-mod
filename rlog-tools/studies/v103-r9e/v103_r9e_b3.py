#!/usr/bin/env python3
r"""studies/v103-r9e/v103_r9e_b3.py -- THE V103 DELIVERABLE: what `b3` (sign of D_state, gp-0x3680) shows.

`probe/v103_r9e_cave.py` found the headline: b3's sign spectrum peaks at **24.3 Hz when ENGAGED** and at
**5.5 Hz when MANUAL**, with 29 % of its sign power in 20-28 Hz engaged against 17 % manual.  This
file hardens that:

  1  hands-OFF only (the f0 conditioning), so "engaged" is not standing in for "the driver is
     shaking the wheel"
  2  a per-window SPEED CENSUS on every arm -- a moving wheel order manufactures an "only here" line
  3  a proper null: chi²₂ surrogates of the median-smoothed pooled spectrum
  4  SPLIT-HALF frequency stability
  5  the ALIASING caveat quantified: a median run of 2 frames at 100 Hz is at the Nyquist limit
  6  427 UNDER-RANGE audit vs V102's own route
  7  b7's sign-vs-command agreement, conditioned the way V98 conditioned it
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(3103)
NW = 512
OUT = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def spec(sig, mask, t, fs, nw=NW):
    W = []
    for a, b in V.episodes(mask, t, nw):
        for i in range(0, (b - a) - nw + 1, nw // 2):
            W.append(slice(a + i, a + i + nw))
    if len(W) < 6:
        return None, W
    wn = np.hanning(nw)
    S = np.array([np.abs(np.fft.rfft((sig[w] - sig[w].mean()) * wn)) ** 2 for w in W])
    return S, W


def line_test(S, f, lo, hi, label, extra=""):
    sel = (f >= lo) & (f <= hi)
    fs_, a_ = f[sel], S.mean(axis=0)[sel]
    sm = median_filter(a_, size=9, mode="nearest")
    r = a_ / sm
    j = int(np.argmax(r))
    nulls = []
    for _ in range(300):
        d = sm[None, :] * RNG.chisquare(2, size=(len(S), len(sm))) / 2.0
        am = d.mean(axis=0)
        nulls.append(float((am / median_filter(am, size=9, mode="nearest")).max()))
    p95 = float(np.percentile(nulls, 95))
    idx = RNG.permutation(len(S))
    h1 = S[idx[: len(S) // 2]].mean(axis=0)[sel]
    h2 = S[idx[len(S) // 2:]].mean(axis=0)[sel]
    f1 = float(fs_[int(np.argmax(h1 / median_filter(h1, size=9, mode="nearest")))])
    f2 = float(fs_[int(np.argmax(h2 / median_filter(h2, size=9, mode="nearest")))])
    print("      %-30s n=%3d  peak %6.2f Hz  prom %5.2f  null p95 %5.2f  %-18s  "
          "split-half %.2f/%.2f %s%s"
          % (label, len(S), fs_[j], r[j], p95,
             "LINE PRESENT" if r[j] > p95 else "no line above noise", f1, f2,
             "STABLE" if abs(f1 - f2) <= 1.0 else "UNSTABLE", extra))
    return dict(n=len(S), f_peak=float(fs_[j]), prom=float(r[j]), null_p95=p95,
                split_half=[f1, f2], line=bool(r[j] > p95))


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    eng, press = M["eng"], M["press"]
    v, rate = M["v"], M["rate"]
    b3 = np.asarray(z["v103_b3"], float) > 0.5
    s3 = np.where(b3, -1.0, 1.0)
    f = np.fft.rfftfreq(NW, 1.0 / fs)

    hdr("1 -- b3 SIGN SPECTRUM, CONDITIONED.  A per-window SPEED CENSUS is printed on every arm:\n"
        "     an unmatched average manufactures a line (`accord-averaged-spectrum-needs-matched...`).")
    ARMS = [
        ("ENG hands-OFF 29-86 km/h", eng & (~press) & (v >= 8.0) & (v < 24.0)),
        ("ENG hands-OFF 60-85 km/h", eng & (~press) & (v >= 16.67) & (v < 23.6)),
        ("ENG hands-OFF 29-50 km/h", eng & (~press) & (v >= 8.0) & (v < 14.0)),
        ("ENG hands-OFF <30 km/h", eng & (~press) & (v > 0.5) & (v < 8.33)),
        ("ENG hands-ON any speed", eng & press & (v > 0.5)),
        ("MANUAL moving 29-86 km/h", (~eng) & (v >= 8.0) & (v < 24.0)),
        ("MANUAL moving <30 km/h", (~eng) & (v > 0.5) & (v < 8.33)),
        ("STANDSTILL (v<0.5)", v <= 0.5),
    ]
    for nm, m in ARMS:
        S, W = spec(s3, m, t, fs)
        if S is None:
            print("      %-30s only %d windows -- skipped" % (nm, len(W)))
            continue
        vs = np.array([np.median(v[w]) * 3.6 for w in W])
        r = line_test(S, f, 1.0, 45.0, nm,
                      extra="   v p10/50/90 %.0f/%.0f/%.0f km/h"
                            % (np.percentile(vs, 10), np.percentile(vs, 50),
                               np.percentile(vs, 90)))
        sel = (f >= 1.0) & (f <= 45.0)
        acc = S.mean(axis=0)
        r["band_share"] = {k: float(acc[(f >= lo) & (f <= hi)].sum() / acc[sel].sum())
                           for k, lo, hi in (("1-5", 1.0, 5.0), ("6-9", 6.0, 9.0),
                                             ("10-15", 10.0, 15.0), ("15-22", 15.0, 22.0),
                                             ("20-28", 20.0, 28.0), ("28-35", 28.0, 35.0),
                                             ("35-45", 35.0, 45.0))}
        r["v_p50"] = float(np.median(vs))
        print("           band share: " + "  ".join("%s %.3f" % (k, vv)
                                                    for k, vv in r["band_share"].items()))
        OUT.setdefault("b3_spectrum", {})[nm] = r

    hdr("2 -- THE ALIASING CAVEAT, QUANTIFIED.  b3 is sampled at the 0x14A rate (~100 Hz).")
    ch = np.where(np.diff(b3.astype(int)) != 0)[0]
    rl = np.diff(np.concatenate(([0], ch + 1, [len(b3)])))
    print("  0x14A frame rate %.2f Hz => Nyquist %.2f Hz." % (fs, fs / 2))
    print("  b3 run-length histogram (frames): " +
          "  ".join("%d:%.3f" % (k, float(np.mean(rl == k))) for k in range(1, 9)))
    print("  p50 run 2 frames.  A 2-frame alternation IS the %.1f Hz Nyquist-adjacent bin." % (fs / 4))
    print("  🛑 [BELIEF, stated as a limit] the observed ~24-25 Hz peak is a LOWER BOUND on the\n"
          "     dither's true frequency.  Any true content above %.1f Hz folds back into this band\n"
          "     and is indistinguishable at this sample rate.  A faster tap (or a counter rung)\n"
          "     would be needed to exclude it." % (fs / 2))
    OUT["aliasing"] = dict(fs=float(fs), nyquist=float(fs / 2),
                           runlen_hist={int(k): float(np.mean(rl == k)) for k in range(1, 12)},
                           p50=float(np.median(rl)))

    hdr("3 -- DOES b3's PEAK MOVE WITH SPEED?  If it tracks +0.157 Hz/(m/s) like the mode, it is\n"
        "     the SAME resonance seen from inside the loop.  If it is fixed, it is a loop rate.")
    rows = []
    for lo, hi in ((5.0, 11.0), (11.0, 15.0), (15.0, 19.0), (19.0, 24.0), (24.0, 30.0)):
        m = eng & (~press) & (v >= lo) & (v < hi)
        S, W = spec(s3, m, t, fs)
        if S is None:
            continue
        sel = (f >= 15.0) & (f <= 35.0)
        a_ = S.mean(axis=0)[sel]
        sm = median_filter(a_, size=9, mode="nearest")
        j = int(np.argmax(a_ / sm))
        vv = float(np.median([np.median(v[w]) for w in W]))
        rows.append((vv, float(f[sel][j]), len(S)))
        print("      v %5.1f-%-5.1f m/s  n=%3d  v p50 %5.2f m/s   b3 peak in 15-35 Hz = %6.2f Hz"
              % (lo, hi, len(S), vv, f[sel][j]))
    if len(rows) >= 3:
        x = np.array([r[0] for r in rows])
        y = np.array([r[1] for r in rows])
        sl = np.polyfit(x, y, 1)[0]
        print("      ==> slope %+.3f Hz/(m/s)   [the MODE's own slope is +0.157; an ORDER-1 tyre\n"
              "          would be +0.489]" % sl)
        OUT["b3_speed_slope"] = dict(slope=float(sl),
                                     points=[[float(a), float(b), int(c)] for a, b, c in rows])

    hdr("4 -- 427 UNDER-RANGE AUDIT.  GATE 3: size a field against its OWN lane's reachable\n"
        "     output.  V102's packer is carried unchanged on V103.")
    for rt, lab in (("96", "V102"), ("9e", "V103")):
        p = V.L.ROUTES[rt]["cache"] / ("r" + rt + "_lane427.json")
        if p.exists():
            d = json.loads(p.read_text())
            print("      %-6s frames %6d  nonzero %5.2f %%  distinct %4d  p50 %4.0f  p90 %4.0f  "
                  "p99 %4.0f  max %4d  => field used %.1f %%"
                  % (lab, d["frames"], 100 * d["nonzero_frac"], d["distinct"], d["p50"],
                     d["p90"], d["p99"], d["max"], 100.0 * d["max"] / 1023))
            OUT.setdefault("lane427", {})[lab] = d
    print("      🛑 The channel is under-used by ~%.1fx.  A `sar 3` packer (V90/V91's) would have\n"
          "         filled it.  This is a GATE-3 sizing miss CARRIED FROM V102, not new to V103."
          % (1023.0 / max(OUT.get("lane427", {}).get("V103", {}).get("max", 1), 1)))

    hdr("5 -- b7's SIGN-vs-COMMAND AGREEMENT, conditioned as V98 conditioned it (engaged, moving,\n"
        "     and |command| ABOVE a floor -- near-zero commands make the sign meaningless).")
    e4 = np.asarray(z["e4tq"], float)
    x6 = np.asarray(z["x6b4c"], float)
    W2 = eng & (v > 0.5)
    print("      %-22s %8s %10s" % ("|0x0E4| floor", "n", "agreement"))
    for flo in (0, 50, 100, 200, 400, 800, 1600):
        m = W2 & (np.abs(e4) > flo) & (np.abs(x6) > 0)
        if m.sum() < 200:
            continue
        a = float(np.mean(np.sign(x6[m]) == np.sign(e4[m])))
        print("      %-22s %8d %10.4f" % (">%d" % flo, m.sum(), a))
        OUT.setdefault("b7_sign_agreement", {})[str(flo)] = dict(n=int(m.sum()), agree=a)
    print("      [record `accord-gp6b4c-is-an-11-slot-assist-sum`: V98 measured 52.80 %% == CHANCE.\n"
          "       A materially higher number here is a DISCREPANCY worth a dedicated check, and is\n"
          "       reported as such, NOT as a retraction.]")

    Path(HERE / "_scratch/out/_v103_r9e_b3.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_b3.json")


if __name__ == "__main__":
    main()
