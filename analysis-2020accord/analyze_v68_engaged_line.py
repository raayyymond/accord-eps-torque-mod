#!/usr/bin/env python3
"""The engagement-conditional 18-28 Hz amplification on V68, and the ~27.6 Hz line behind it.

WHAT THE FIRST TWO PASSES ESTABLISHED
-------------------------------------
Maneuver-vs-control, computed INSIDE each arm against its own split-half null (so route, day,
tyre and road all cancel):

    band      ON (4e, engaged)          OFF (4c, manual)
    18-22     3.129 [2.408, 5.298]      1.780 [1.444, 1.927]
    24-28     5.098 [2.798, 6.160]      2.056 [1.470, 2.812]
    30-40     2.072 [1.550, 2.292]      2.081 [1.667, 2.711]
    40-49     2.516 [1.561, 3.701]      2.558 [1.469, 3.747]

⇒ 40-49 Hz (grind #2's band) rises by the SAME factor in both arms -- engagement does nothing to
  it. 18-28 Hz rises ~2.5x MORE when engaged. THAT is the engagement-conditional part, and it is
  NOT in grind #2's band.

WHAT THIS SCRIPT TESTS -- and the trap it is built to fail
-----------------------------------------------------------
The order veto turned up a peak near 27.6 Hz on the engaged route that does NOT track speed
(Theil-Sen -0.0665 Hz per m/s against order 2's +0.9616), with prominence up to 91. A fixed line
is a MODE. But this kit WITHDREW a "fixed 42 Hz mode" that had dBIC 249-460 and four independent
axes, because a band-limited argmax lands at BAND CENTRE when no line is present -- and 27.6 sits
uncomfortably close to the centre of the 24-30 search band (27.0).

So the band-centre artefact is attacked directly:
  1. WIDEN the search band (20-35, 18-40, 15-45 Hz). A real line stays put; an artefact MOVES with
     band centre. This is the single cheapest discriminator and it is decisive.
  2. Require prominence > 4 on the AVERAGED periodogram (average first, then peak-find).
  3. Check it is not wheel order 2 (which route 4c's manual arm shows cleanly at order 1.97-1.99).
  4. COHERENCE with the LKAS command. Grind #1 read 0.917 command<->bar; the highway 40-49 Hz
     population read 0.169 vs 0.166 background. A closed-loop LKAS mode must show coherence.
  5. ABSOLUTE level against grind #1 at creep, so "significant" is not confused with "felt".
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import periodogram, runs_of  # noqa: E402
from analyze_v68_highway_arms import (HWY, NFFT, HOP, mean_fs, segs_of,  # noqa: E402
                                      wrecs_v68)


def avg_spec(route, eng, vlo=HWY, vhi=99.0, sel=None, chan="tq"):
    """Averaged periodogram over qualifying windows. `sel(record-ish dict)` filters."""
    acc, n, fref = None, 0, None
    for s, d in segs_of(route):
        fs = mean_fs(d["t"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        le = d["cc_lat"] > 0.5
        for a, b in runs_of(le if eng else ~le, d["t"], NFFT):
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(a + i, a + i + NFFT)
                v = float(np.mean(d["cs_v"][sl]))
                if not (vlo <= v < vhi):
                    continue
                if sel is not None and not sel(d, sl):
                    continue
                P = periodogram(d[chan][a + i:a + i + NFFT], fs, NFFT, True)
                if P is None:
                    continue
                if acc is None:
                    acc, fref = np.zeros_like(P), f
                if len(P) == len(acc):
                    acc += P; n += 1
    return (fref, acc / n, n) if n else (None, None, 0)


def coherence(route, eng, f_lo, f_hi, a_chan="e4req", b_chan="tq", vlo=HWY, sel=None):
    """Magnitude-squared coherence between the LKAS command and the torsion bar, band-averaged.

    🛑 `e4req` is 0xE4 src 129 -- openpilot's OUTGOING command, i.e. sendcan. It is the right
    channel for "did the controller drive this", and the kit records it as living in src1, NOT
    can src0 (accord-lateral-engagement-signals).
    """
    Sxx = Syy = Sxy = None
    n = 0
    for s, d in segs_of(route):
        fs = mean_fs(d["t"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        le = d["cc_lat"] > 0.5
        for a, b in runs_of(le if eng else ~le, d["t"], NFFT):
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(a + i, a + i + NFFT)
                if float(np.mean(d["cs_v"][sl])) < vlo:
                    continue
                if sel is not None and not sel(d, sl):
                    continue
                x = np.asarray(d[a_chan][sl], float)
                y = np.asarray(d[b_chan][sl], float)
                if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                    continue
                w = np.hanning(NFFT)
                X = np.fft.rfft((x - x.mean()) * w)
                Y = np.fft.rfft((y - y.mean()) * w)
                if Sxx is None:
                    Sxx = np.zeros(len(X)); Syy = np.zeros(len(X)); Sxy = np.zeros(len(X), complex)
                Sxx += np.abs(X) ** 2; Syy += np.abs(Y) ** 2; Sxy += X * np.conj(Y)
                n += 1
    if not n:
        return np.nan, 0
    C = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    m = (f >= f_lo) & (f <= f_hi)
    return float(np.mean(C[m])), n


def main():
    res = {}
    W = {r: wrecs_v68(r) for r in ("4c", "4e")}
    OFF = [w for w in W["4c"] if not w["eng"] and w["v"] >= HWY]
    ON = [w for w in W["4e"] if w["eng"] and w["v"] >= HWY]
    allpk = np.concatenate([G.col(ON, "ratepk"), G.col(OFF, "ratepk")])
    HI = float(np.percentile(allpk, 90))

    G.hdr("1. THE BAND-CENTRE ARTEFACT TEST -- widen the search band and watch the peak")
    print("  A real line does not move when the search band moves. The withdrawn '42 Hz mode'")
    print("  tracked band centre exactly. Prominence criterion for a real line: > 4.\n")
    res["bandwidth"] = {}
    for route, eng, lbl in (("4e", True, "ENGAGED"), ("4c", False, "MANUAL ")):
        f, P, n = avg_spec(route, eng)
        if P is None:
            continue
        R = G.prom_spectrum(f, P)
        print(f"  route {route} ({lbl}, all highway windows, n={n}):")
        for lo, hi in ((24, 30), (20, 35), (18, 40), (15, 45), (23, 33)):
            f0, pr = G.locate(f, P, lo, hi, R=R)
            ctr = 0.5 * (lo + hi)
            res["bandwidth"][f"{route}_{lo}-{hi}"] = dict(f0=f0, prom=pr, centre=ctr)
            flag = "  *** LINE" if pr > 4 else ""
            print(f"    search {lo:2d}-{hi:2d} Hz (centre {ctr:4.1f}): peak {f0:6.2f} Hz  "
                  f"prom {pr:6.2f}   offset from centre {f0 - ctr:+6.2f}{flag}")
        print()

    G.hdr("2. THE SAME, RESTRICTED TO MANEUVER WINDOWS -- where the operator feels it")
    print(f"  maneuver = |rate|pk >= {HI:.1f} deg/s inside the window.\n")
    res["maneuver_spec"] = {}
    for route, eng, lbl in (("4e", True, "ENGAGED"), ("4c", False, "MANUAL ")):
        def sel(d, sl, _fs=None):
            return float(np.max(np.abs(d["rate_c"][sl]))) >= HI
        f, P, n = avg_spec(route, eng, sel=sel)
        if P is None or n < 6:
            print(f"  route {route} ({lbl}): n={n} -- too few maneuver windows")
            continue
        R = G.prom_spectrum(f, P)
        print(f"  route {route} ({lbl}, {n} maneuver windows):")
        for lo, hi in ((18, 40), (15, 45), (30, 49.5)):
            f0, pr = G.locate(f, P, lo, hi, R=R)
            res["maneuver_spec"][f"{route}_{lo}-{hi}"] = dict(f0=f0, prom=pr, n=n)
            print(f"    search {lo:4.1f}-{hi:4.1f} Hz: peak {f0:6.2f} Hz  prom {pr:6.2f}"
                  f"{'  *** LINE' if pr > 4 else ''}")
        print()

    G.hdr("3. COHERENCE -- is the LKAS command driving the bar in this band?")
    print("  benchmarks already on record: grind #1 command<->bar 0.917 at 21.09 Hz;")
    print("  the highway 40-49 Hz population 0.169 in events vs 0.166 background.\n")
    res["coh"] = {}
    for lo, hi, nm in ((1.0, 4.0, "1-4 (driver/controller band)"), (10.0, 16.0, "10-16"),
                       (18.0, 22.0, "18-22"), (24.0, 28.0, "24-28"), (30.0, 40.0, "30-40"),
                       (40.0, 49.0, "40-49")):
        c_on, n_on = coherence("4e", True, lo, hi)
        c_off, n_off = coherence("4c", False, lo, hi)
        res["coh"][nm] = dict(on=c_on, off=c_off, n_on=n_on, n_off=n_off)
        print(f"  {nm:30} ENGAGED {c_on:.3f} (n={n_on})   MANUAL {c_off:.3f} (n={n_off})")
    print("\n  ⚠ On the MANUAL route the 0xE4 command is openpilot's request while lateral")
    print("    control is off, so the manual column is a NEGATIVE CONTROL by construction.")

    G.hdr("4. ABSOLUTE LEVELS -- 'significant' is not 'felt'")
    print("  p99 band envelope, counts on the torsion bar. Grind #1 at creep ran 860-1290 and")
    print("  the creep grind #2 bursts ran 2000-4000; the operator felt BOTH of those.\n")
    print(f"  {'band':8} {'ON med':>8} {'ON p90':>8} {'ON max':>8} | "
          f"{'OFF med':>8} {'OFF p90':>8} {'OFF max':>8}")
    res["levels"] = {}
    for band in ("1-4", "10-16", "18-22", "24-28", "30-40", "40-49"):
        k = "e_" + band
        a, b = G.col(ON, k), G.col(OFF, k)
        res["levels"][band] = dict(on=[float(np.median(a)), float(np.percentile(a, 90)),
                                       float(a.max())],
                                   off=[float(np.median(b)), float(np.percentile(b, 90)),
                                        float(b.max())])
        print(f"  {band:8} {np.median(a):8.1f} {np.percentile(a, 90):8.1f} {a.max():8.1f} | "
              f"{np.median(b):8.1f} {np.percentile(b, 90):8.1f} {b.max():8.1f}")

    G.hdr("5. FLIGHT HEALTH -- two independent methods, per the standing convention")
    res["health"] = {}
    ev_all = {}
    for route in ("4c", "4e"):
        st4 = st3 = nraw4 = nraw3 = nfr = 0
        for s, d in segs_of(route):
            st4 += int((d["sstat"] == 4).sum()); st3 += int((d["sstat"] == 3).sum())
            r = d["raw18_st"]
            nraw4 += int((r == 4).sum()); nraw3 += int((r == 3).sum())
            nfr += len(d["t"])
            ep = HERE.parent / "_cache_v68" / f"{route}s{s}_events.json"
            if ep.exists():
                for e in json.loads(ep.read_text()):
                    ev_all.setdefault(route, {}).setdefault(e["name"], 0)
                    ev_all[route][e["name"]] += 1
        res["health"][route] = dict(st4=st4, st3=st3, raw_st4=nraw4, raw_st3=nraw3, frames=nfr)
        print(f"  {route}: gridded ST==4 {st4}  ST==3 {st3}  |  raw un-gridded 0x18F "
              f"ST==4 {nraw4}  ST==3 {nraw3}   ({nfr} frames)")
    print()
    WATCH = ("steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
             "immediateDisable", "steerSaturated", "canBusMissing", "canErrorPersistent")
    for route in ("4c", "4e"):
        hits = {k: v for k, v in ev_all.get(route, {}).items() if k in WATCH}
        top = sorted(ev_all.get(route, {}).items(), key=lambda x: -x[1])[:6]
        print(f"  {route}: watchlist {hits or 'CLEAN'}")
        print(f"      most frequent onroadEvents: {top}")
    res["events"] = ev_all

    Path(HERE / "_v68_engaged_line.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {HERE / '_v68_engaged_line.json'}")


if __name__ == "__main__":
    main()
