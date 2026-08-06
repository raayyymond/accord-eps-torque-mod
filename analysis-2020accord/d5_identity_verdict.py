#!/usr/bin/env python3
"""D5 ss10-12 -- the three checks the verdict actually rests on.

  ss10  MSC PROFILE + CONTROL CARRIER. ss8 found the 6-9 Hz signal coherent with the 12-28 Hz
        envelope. Two things could produce that: (i) the 7.8 Hz event train RINGS the ~21 Hz mode,
        or (ii) everything bursts together and any band's envelope would do. Discriminate by
        running the identical test against a CONTROL carrier (30-46 Hz) and by printing WHERE in
        2-15 Hz the coherence peaks.
  ss11  ANGLE, RATE-MATCHED. ss2 found e_18-22 at creep peaks at 3-10 deg, not 0-3 deg -- but
        `rate_lp` rises 5.6 -> 10.0 -> 24.2 deg/s across those bins, so the angle axis is confounded
        with steering activity. Re-run inside one rate_lp band.
  ss12  AUDIBILITY ARITHMETIC. If ONE mode is heard at creep and merely felt elsewhere, the 18-22
        amplitude ratio between those conditions has to be large. Quote it, against the split-half
        null, and beside the 6-9 ratio over the same cells.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r31_common as C  # noqa: E402
import _r59_lib as L  # noqa: E402
from d5_identity_coupling import bandpass, hilbert, msc, segs_of  # noqa: E402

OUT = ROOT / "_d5_verdict.json"
RNG = np.random.default_rng(742026)
BUILDS = N.LADDER


def main():
    L.install_fs()
    res = {}

    # ---------------------------------------------------------------- ss10 -----------------------
    L.hdr("ss10  MSC of bandpass(tq,5-12) against the ENVELOPE of two carriers -- 12-28 vs 30-46")
    print("  A carrier-SPECIFIC excess says the 7.8 Hz events ring the ~21 Hz mode.")
    print("  An equal excess in both says everything simply bursts together.\n")
    NSEG, NRUN = 256, 2048
    prof = {}
    for label, (vlo, vhi) in (("creep 0-4", (0.0, 4.0)), ("mid 4-15", (4.0, 15.0)),
                              ("fast 15+", (15.0, 1e9))):
        rows = {"12-28": [[], []], "30-46": [[], []]}
        curves, fc = [], None
        for b in BUILDS:
            for s, d in segs_of(b):
                fs = G.fs_of(d)
                x = np.asarray(d["tq"], float)
                v = np.abs(np.asarray(d["cs_v"], float))
                m = np.asarray(d["cc_lat"], float) > 0.5
                for a, e in C.runs_of(m, d["t"], NRUN):
                    xw = x[a:e]
                    if not np.all(np.isfinite(xw)) or not (vlo <= float(np.mean(v[a:e])) < vhi):
                        continue
                    lo = bandpass(xw, fs, 5.0, 12.0)
                    lag = int(RNG.integers(int(5 * fs), len(xw) - int(5 * fs)))
                    for cb in ("12-28", "30-46"):
                        cl, ch = (12.0, 28.0) if cb == "12-28" else (30.0, 46.0)
                        env = np.abs(hilbert(bandpass(xw, fs, cl, ch)))
                        env = env - env.mean()
                        cc, f = msc(lo, env, fs, NSEG)
                        if cc is None:
                            continue
                        band = (f >= 6) & (f <= 9)
                        c2 = msc(lo, np.roll(env, lag), fs, NSEG)[0]
                        rows[cb][0].append(float(np.max(cc[band])))
                        rows[cb][1].append(float(np.max(c2[band])))
                        if cb == "12-28":
                            curves.append(cc)
                            fc = f
        out = {}
        for cb, (o, n) in rows.items():
            if len(o) < 5:
                print(f"  {label:<11} {cb:<7} -- underpowered ({len(o)})")
                continue
            o, n = np.array(o), np.array(n)
            dd = o - n
            dr = np.array([np.median(dd[RNG.integers(0, len(dd), len(dd))]) for _ in range(3000)])
            l_, h_ = np.percentile(dr, [2.5, 97.5])
            out[cb] = dict(n=len(o), obs=float(np.median(o)), null=float(np.median(n)),
                           diff=float(np.median(dd)), lo=float(l_), hi=float(h_))
            print(f"  {label:<11} carrier {cb:<7} runs={len(o):<4d}  OBS {np.median(o):.3f}  "
                  f"SHIFTED {np.median(n):.3f}   diff {np.median(dd):+.3f} [{l_:+.3f}, {h_:+.3f}]")
        if curves and fc is not None:
            M = np.median(np.array(curves), axis=0)
            sel = (fc >= 2) & (fc <= 15)
            j = int(np.argmax(np.where(sel, M, -np.inf)))
            print(f"  {label:<11} median MSC(12-28 env) peaks at {fc[j]:.2f} Hz, MSC = {M[j]:.3f}"
                  f"   |  profile " +
                  " ".join(f"{fc[k]:.1f}Hz:{M[k]:.2f}"
                           for k in np.flatnonzero(sel)[::2][:8]))
            out["peak_hz"] = float(fc[j])
        res.setdefault("msc", {})[label] = out

    # ---------------------------------------------------------------- ss11 -----------------------
    store = N.records()
    zeros = {b: N.route_zero(b, store)[0] for b in BUILDS}
    creep = []
    for b in BUILDS:
        for r in store.get(b, []):
            if r["eng"] != 1 or not (1.5 <= r["v"] < 3.0):
                continue
            if not np.isfinite(r.get("a_mean", np.nan)):
                continue
            q = dict(r)
            q["adev"] = abs(r["a_mean"] - zeros[b])
            creep.append(q)
    L.hdr("ss11  ANGLE at creep, RATE-MATCHED -- inside one rate_lp band, does zero angle win?")
    AB = [(0.0, 3.0), (3.0, 10.0), (10.0, 25.0), (25.0, 1e9)]
    AN = ["0-3", "3-10", "10-25", "25+"]
    for rlo, rhi in ((0.0, 8.0), (8.0, 20.0), (20.0, 1e9)):
        sub0 = [r for r in creep if rlo <= r["rate_lp"] < rhi]
        print(f"\n  rate_lp {rlo:.0f}-{rhi if rhi < 1e8 else float('inf'):.0f} deg/s  "
              f"(n={len(sub0)})")
        for i, nm in enumerate(AN):
            lo_, hi_ = AB[i]
            sub = [r for r in sub0 if lo_ <= r["adev"] < hi_]
            if len(sub) < 6:
                print(f"    |ang| {nm:<7} n={len(sub):<4d}  -- underpowered")
                continue
            e18 = float(np.median([r["e_18-22"] for r in sub]))
            e69 = float(np.median([r["e_6-9"] for r in sub]))
            e24 = float(np.median([r["e_24-28"] for r in sub]))
            print(f"    |ang| {nm:<7} n={len(sub):<4d} ep={len({r[G.EPKEY] for r in sub}):<3d} "
                  f" e_18-22 {e18:>8.0f}   e_6-9 {e69:>8.0f}   e_24-28 {e24:>7.0f}"
                  f"   18-22/24-28 {e18/e24:>6.2f}")
            res.setdefault("angle_rate_matched", {})[f"{rlo:.0f}-{rhi:.0f}|{nm}"] = dict(
                n=len(sub), e18=e18, e69=e69, e24=e24)

    # ---------------------------------------------------------------- ss12 -----------------------
    L.hdr("ss12  AUDIBILITY ARITHMETIC -- creep vs elsewhere, both bands, against the null")
    eng = [r for b in BUILDS for r in store.get(b, []) if r["eng"] == 1]
    cells = {"creep 1.5-3 m/s": [r for r in eng if 1.5 <= r["v"] < 3.0],
             "4-8 m/s": [r for r in eng if 4.0 <= r["v"] < 8.0],
             "8-15 m/s": [r for r in eng if 8.0 <= r["v"] < 15.0],
             "15-25 m/s": [r for r in eng if 15.0 <= r["v"] < 25.0],
             "25+ m/s": [r for r in eng if r["v"] >= 25.0]}
    ref = cells["15-25 m/s"]
    print(f"  {'cell':<18}{'n':>6}   " + "".join(f"{k:>28}" for k in ("e_18-22 vs 15-25 m/s",
                                                                     "e_6-9 vs 15-25 m/s")))
    for nm, rs in cells.items():
        if len(rs) < 20:
            continue
        s = f"  {nm:<18}{len(rs):>6}   "
        for k in ("e_18-22", "e_6-9"):
            r_, l_, h_ = G.boot_cellwise(rs, ref, k, RNG, nboot=800, min_ep=2, min_win=4)[:3]
            s += f"{r_:>12.2f}x [{l_:>5.2f},{h_:>5.2f}]"
            res.setdefault("audibility", {})[f"{nm}|{k}"] = dict(r=r_, lo=l_, hi=h_, n=len(rs))
        print(s)
    n18 = G.split_half_null(eng, "e_18-22", RNG, nrep=150, min_ep=2, min_win=4)
    n69 = G.split_half_null(eng, "e_6-9", RNG, nrep=150, min_ep=2, min_win=4)
    print(f"\n  split-half null (same estimator): e_18-22 {n18[0]:.2f} [{n18[1]:.2f},{n18[2]:.2f}]"
          f"   e_6-9 {n69[0]:.2f} [{n69[1]:.2f},{n69[2]:.2f}]")
    res["null"] = dict(e18=n18, e69=n69)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
