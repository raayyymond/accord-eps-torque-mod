#!/usr/bin/env python3
"""PART 3 -- the DEFINITIVE power test, the lever-in-force test, and the figure.

P1  FREQUENCY-SHIFT SURROGATE.  The injection test in part 2 notches 6f's line out and adds a
    synthetic sine; a 2nd-order notch leaves energy behind and a jittered sine is less coherent
    than the real line, so that test is PESSIMISTIC.  The faithful surrogate takes 6f's OWN
    measured line, removes it, and re-adds it FREQUENCY-SHIFTED by exactly the pre-registered
    ratio -- preserving amplitude, coherence, modulation and duty exactly.  If the pipeline
    cannot recover THAT, the test was underpowered and the verdict is AMBIGUOUS.

P2  LEVER IN FORCE, from the firmware's own probe.  🛑 V86 and V86B SWAP the b5/b6 weights
    (STATE.md: "same cave, b5/b6 weight-swapped for identity"), so the duties are NOT
    comparable bit-for-bit -- they must be re-mapped by MEANING first.
      V86  : b6 = (gp-0x6b70 != 0)   b5 = (|gp-0x6b70| >= 512)
      V86B : b5 = (gp-0x6b70 != 0)   b6 = (|gp-0x6b70| >= 512)
      both : b7 = (gp-0x6b70 < 0)    b4 = (gp-0x67ab < 2), the aggregator gate
    b7's SIGN-TOGGLE RATE is a direct 100 Hz observable of the residual's own bandwidth, and
    routes 6f and 70 are both parking-lot -- so it is the cleanest available alpha contrast.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_7792)
O3 = {}


def shift_line(r, f0, f_target, half=1.2):
    """Take r['x'], move the f0 line to f_target, keep everything else bit-identical.

    x = x_rest + Re{ analytic(x_line) * exp(-j 2 pi (f0-f_target) t) }
    The line's envelope, coherence, duty and amplitude are preserved EXACTLY."""
    x = np.asarray(r["x"], float)
    fs = r["fs"]
    b = butter(4, [max(f0 - half, 0.4), f0 + half], btype="band", fs=fs)
    x_line = filtfilt(*b, x)
    x_rest = x - x_line
    tt = np.arange(len(x)) / fs
    a = hilbert(x_line)
    shifted = np.real(a * np.exp(-2j * np.pi * (f0 - f_target) * tt))
    return x_rest + shifted


def main():
    E = {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True)))

    f_6f = 7.999
    f_V85 = 8.006

    V.hdr("P1  FREQUENCY-SHIFT SURROGATE -- the definitive power test.  6f's OWN line, moved by\n"
          "    the pre-registered ratio, everything else untouched.  If the pipeline recovers it,\n"
          "    the falsifier COULD have fired and the verdict stands.")
    print("    window-to-window spread of the measured line on 6f: f_free std = %.3f Hz "
          "(n=%d)" % (np.nanstd([r["f_free"] for r in E["V86/r6f"]]), len(E["V86/r6f"])))
    O3["p1"] = {}
    print("\n    %-30s %24s %28s %9s" % ("surrogate", "f_c (Hz), block CI",
                                         "ratio vs REAL 6e", "excl 1.00"))
    for tag, ratio in (("UNSHIFTED (identity control)", 1.000),
                       ("x0.875 (pre-reg WEAKEST)", 0.875),
                       ("x0.843 (pre-reg MEDIAN)", 0.843),
                       ("x0.797 (pre-reg STRONGEST)", 0.797),
                       ("x0.95 (half the weakest)", 0.950),
                       ("x0.97 (a third of weakest)", 0.970)):
        q = []
        for r in E["V86/r6f"]:
            y = shift_line(r, f_6f, f_6f * ratio) if ratio != 1.0 else r["x"]
            d = dict(x=y, fs=r["fs"], v=r["v"], blk=r["blk"], ep=r["ep"], t0=r["t0"])
            V.spectra([d])
            q.append(d)
        fc = V.block_boot([r["f_free"] for r in q], [r["blk"] for r in q])
        rr = V.strat_block_boot_ratio(q, E["V85/r6e"], key="f_free")
        ex = "YES" if (rr["hi"] < 1.0 or rr["lo"] > 1.0) else "no"
        print("    %-30s %7.3f [%6.3f,%6.3f] %9.3f [%6.3f,%6.3f] %9s"
              % (tag, fc[0], fc[1], fc[2], rr["ratio"], rr["lo"], rr["hi"], ex))
        O3["p1"][tag] = dict(shift=ratio, f_c=list(fc), ratio=rr, excludes_1=(ex == "YES"))

    print("\n    SMALLEST DETECTABLE SHIFT -- sweep the shift until the CI stops excluding 1.00:")
    mdd = None
    for ratio in (0.99, 0.98, 0.96, 0.94, 0.92, 0.90):
        q = []
        for r in E["V86/r6f"]:
            d = dict(x=shift_line(r, f_6f, f_6f * ratio), fs=r["fs"], v=r["v"],
                     blk=r["blk"], ep=r["ep"], t0=r["t0"])
            V.spectra([d])
            q.append(d)
        rr = V.strat_block_boot_ratio(q, E["V85/r6e"], key="f_free")
        ex = rr["hi"] < 1.0 or rr["lo"] > 1.0
        print("      shift x%.3f (%+.2f Hz)  ratio %.3f [%.3f,%.3f]  excl 1.00: %s"
              % (ratio, f_6f * (ratio - 1), rr["ratio"], rr["lo"], rr["hi"],
                 "YES" if ex else "no"))
        O3.setdefault("mdd", []).append([ratio, rr["ratio"], rr["lo"], rr["hi"], bool(ex)])
        if ex and mdd is None:
            mdd = ratio
    print("    -> smallest shift this instrument resolves on 6f: about x%.2f "
          "(%.2f Hz).  The pre-registration asked for x0.843 (-1.26 Hz)."
          % (mdd or 0.90, abs(f_6f * ((mdd or 0.90) - 1))))
    O3["mdd_ratio"] = mdd

    # =========================================================================================
    V.hdr("P2  WAS THE LEVER IN FORCE?  The firmware's own probe, RE-MAPPED BY MEANING.\n"
          "    🛑 V86 and V86B swap b5/b6, so raw duties are not comparable.  b7 (sign) and\n"
          "    b4 (aggregator gate) have the same weight on both.")
    O3["probe"] = {}
    for nm, swap in (("V86/r6f", False), ("V86B/r70", True)):
        cache, pfx, segs = V.ROUTES[nm]
        n = 0; nz = 0.0; big = 0.0; neg = 0.0; gate = 0.0; tog = 0.0; secs = 0.0
        toggles_per_s = []
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            v = np.asarray(d["cs_v"], float)
            t = np.asarray(d["t"], float)
            k = lat & (v >= V.VLO) & (v < V.VHI)
            if k.sum() < 200:
                continue
            q = np.asarray(d["probe"], float).astype(int)
            b7 = (q & 0x80) != 0
            b6 = (q & 0x40) != 0
            b5 = (q & 0x20) != 0
            b4 = (q & 0x10) != 0
            NZ, BIG = (b5, b6) if swap else (b6, b5)
            n += int(k.sum())
            nz += float(NZ[k].sum()); big += float(BIG[k].sum())
            neg += float(b7[k].sum()); gate += float(b4[k].sum())
            # sign toggles per second, over contiguous runs only
            for a, b in C31.runs_of(k, t, 200):
                sg = b7[a:b].astype(int)
                dur = t[b - 1] - t[a]
                if dur > 1.0:
                    toggles_per_s.append(np.sum(np.abs(np.diff(sg))) / dur)
                    secs += dur
        tps = float(np.mean(toggles_per_s)) if toggles_per_s else np.nan
        print("    %-10s n=%6d fr  |  resid != 0 : %.4f   |resid| >= 512 : %.4f   "
              "resid < 0 : %.4f   GATE OPEN : %.4f" % (nm, n, nz / n, big / n, neg / n, gate / n))
        print("    %-10s     sign toggles/s = %6.2f   over %.1f s in %d runs"
              % ("", tps, secs, len(toggles_per_s)))
        O3["probe"][nm] = dict(n=n, nonzero=nz / n, ge512=big / n, negative=neg / n,
                               gate=gate / n, toggles_per_s=tps, secs=secs,
                               n_runs=len(toggles_per_s))
    a = O3["probe"]["V86/r6f"]; b = O3["probe"]["V86B/r70"]
    print("\n    alpha CONTRAST (V86 alpha=286 vs V86B alpha=573, both parking-lot, speed-matched):")
    print("      sign-toggle rate   %.2f /s  vs  %.2f /s   ratio %.3f" %
          (a["toggles_per_s"], b["toggles_per_s"], a["toggles_per_s"] / b["toggles_per_s"]))
    print("      |resid| >= 512     %.4f     vs  %.4f      ratio %.3f" %
          (a["ge512"], b["ge512"], a["ge512"] / b["ge512"]))
    print("      resid != 0         %.4f     vs  %.4f" % (a["nonzero"], b["nonzero"]))
    O3["alpha_contrast"] = dict(toggle_ratio=a["toggles_per_s"] / b["toggles_per_s"],
                                ge512_ratio=a["ge512"] / b["ge512"])

    # =========================================================================================
    V.hdr("P3  FIGURE")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    VB = V.VBINS
    cA = np.array([sum(1 for r in E["V86/r6f"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    cB = np.array([sum(1 for r in E["V85/r6e"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    c70 = np.array([sum(1 for r in E["V86B/r70"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    w = np.minimum(cA, cB)
    f, S6f = V.matched_mean_spectrum(E["V86/r6f"], w, "R")
    _, S6e = V.matched_mean_spectrum(E["V85/r6e"], w, "R")
    _, S70 = V.matched_mean_spectrum(E["V86B/r70"], np.minimum(cA, c70), "R")
    q = []
    for r in E["V86/r6f"]:
        d = dict(x=shift_line(r, f_6f, f_6f * 0.843), fs=r["fs"], v=r["v"], blk=r["blk"],
                 ep=r["ep"], t0=r["t0"])
        V.spectra([d])
        q.append(d)
    _, Ssur = V.matched_mean_spectrum(q, w, "R")

    fig, ax = plt.subplots(figsize=(11, 6))
    m = (f >= 4.0) & (f <= 12.0)
    ax.axvspan(6.2, 6.9, color="tab:orange", alpha=0.15, zorder=0)
    ax.plot(f[m], S6e[m], lw=2.0, color="tab:blue", label="V85 / route 6e  (alpha=573)")
    ax.plot(f[m], S6f[m], lw=2.4, color="tab:red", label="V86 / route 6f  (alpha=286)")
    ax.plot(f[m], S70[m], lw=1.4, color="tab:green", ls="--",
            label="V86B / route 70 (alpha=573, FactorC lever)")
    ax.plot(f[m], Ssur[m], lw=1.6, color="0.4", ls=":",
            label="V86 surrogate, line moved x0.843 (what CONFIRMED looks like)")
    ax.set_xlabel("Hz"); ax.set_ylabel("prominence over local floor")
    ax.set_title("V86 pre-registered frequency test: speed-matched engaged mean spectrum\n"
                 "shaded = pre-registered CONFIRMED window [6.2, 6.9] Hz")
    ax.legend(fontsize=8.5); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = ROOT / "_scratch/cache/r6f" / "v86_freq_test.png"
    fig.savefig(out, dpi=140)
    print("    wrote %s" % out)

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part3.json").write_text(
        json.dumps(O3, indent=1, default=float))
    print("    wrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part3.json"))


if __name__ == "__main__":
    main()
