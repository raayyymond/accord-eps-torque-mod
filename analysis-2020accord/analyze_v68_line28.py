#!/usr/bin/env python3
"""Is the 28.13 Hz engaged-highway line NEW to these routes, or has it always been there?

STATE OF THE QUESTION
---------------------
On V68 route `4e` (engaged highway) the averaged periodogram carries a line at **28.13 Hz** with
prominence **18.81** over all highway windows and **32.65** restricted to maneuver windows. It
SURVIVES the band-centre artefact test that killed the withdrawn "42 Hz mode": the peak does not
move as the search band sweeps 24-30 / 20-35 / 18-40 / 15-45 / 23-33 Hz. It does not track speed
(Theil-Sen -0.0665 Hz per m/s against wheel order 2's +0.9616). On the manual route `4c` the same
band peaks at 26.59 Hz with prominence 3.33 -- below the kit's >4 criterion, i.e. no line.

🛑 BUT `4c` AND `4e` ARE DIFFERENT ROADS, 14 HOURS APART. "Engaged-only" and "route-only" are not
separated by that pair. The decisive test is whether prior ENGAGED-HIGHWAY routes on OTHER builds
carry the same line:

    r47  V67  engaged highway, 850 s      -- the same conditional Kd arm as V68
    r2b  V58  engaged highway, 227 s      -- stock Kd = 1.00 lane
    r37  V62  engaged highway             -- flat Kd = 2.00
    r3b  V65  highway                     -- flat Kd = 2.00

If 28 Hz is there on r47/r2b too, it is an ordinary feature of engaged highway driving on this car
and NOT something V68 or the lane-change symptom introduced. If it is absent, it is new and the
next question is what changed.

ALSO FIXED HERE
---------------
🛑 The previous pass computed command<->bar coherence against `e4req`, which is the ENGAGEMENT BIT
`(d[2] >> 7) & 1`, not the command. The command is `e4tq` = `i16be(d, 0)` of 0xE4. That is why
every coherence read exactly 0.000. Redone against `e4tq`.

★ And route `4e` carries 45 `laneChange` onroadEvents -- openpilot's own lane-change state
machine. That anchors the operator's trigger far better than the blinker duty cycle.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import load, periodogram, runs_of  # noqa: E402
from analyze_v68_highway_arms import (HWY, NFFT, HOP, boot_ratio, mean_fs,  # noqa: E402
                                      segs_of, split_null, wrecs_v68)

# prior routes with real engaged highway exposure. cache / prefix / segments / build label
PRIOR = {
    "r47/V67": (ROOT / "_cache_r47", "r47s", list(range(0, 26))),
    "r2b/V58": (ROOT / "_cache_r2b", "r2bs", list(range(0, 14))),
    "r37/V62": (ROOT / "_cache_r37", "r37s", list(range(0, 15))),
    "r3b/V65": (ROOT / "_cache_r3b", "r3bs", list(range(0, 14))),
}


def avg_spec_generic(segiter, eng, vlo=HWY, chan="tq", sel=None):
    """Averaged periodogram. `segiter` yields (label, cache-dict). Average FIRST, peak-find after."""
    acc, n, fref = None, 0, None
    for _s, d in segiter:
        if chan not in d or "cc_lat" not in d:
            continue
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
                P = periodogram(d[chan][a + i:a + i + NFFT], fs, NFFT, True)
                if P is None:
                    continue
                if acc is None:
                    acc, fref = np.zeros_like(P), f
                if len(P) == len(acc):
                    acc += P; n += 1
    return (fref, acc / n, n) if n else (None, None, 0)


def prior_segs(key):
    cache, pfx, segs = PRIOR[key]
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if p.exists():
            yield s, {k: v for k, v in np.load(p).items()}


def coh(segiter, eng, f_lo, f_hi, vlo=HWY, sel=None, a_chan="e4tq", b_chan="tq"):
    Sxx = Syy = Sxy = None
    n = 0
    for _s, d in segiter:
        if a_chan not in d:
            continue
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
                x = np.asarray(d[a_chan][sl], float); y = np.asarray(d[b_chan][sl], float)
                if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                    continue
                if x.std() < 1e-9 or y.std() < 1e-9:
                    continue
                w = np.hanning(NFFT)
                X = np.fft.rfft((x - x.mean()) * w); Y = np.fft.rfft((y - y.mean()) * w)
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
    rng = np.random.default_rng(20260803)
    G.EPKEY = "blk"
    res = {}

    G.hdr("1. IS 28 Hz NEW? -- prior ENGAGED-HIGHWAY routes, same estimator")
    print("  averaged periodogram over v >= 20 m/s engaged windows, peak-find in 18-40 Hz.")
    print("  criterion: prominence > 4 is a line.\n")
    res["prior"] = {}
    rows = [("4e/V68", lambda: segs_of("4e"), True)]
    rows += [(k, (lambda kk=k: prior_segs(kk)), True) for k in PRIOR]
    rows += [("4c/V68 MANUAL", lambda: segs_of("4c"), False)]
    for lbl, it, eng in rows:
        f, P, n = avg_spec_generic(it(), eng)
        if P is None or n < 10:
            print(f"  {lbl:16} n={n} -- insufficient engaged highway exposure")
            continue
        R = G.prom_spectrum(f, P)
        f0, pr = G.locate(f, P, 18.0, 40.0, R=R)
        # explicit read AT 28.13 Hz regardless of where the argmax landed
        j = int(np.argmin(np.abs(f - 28.13)))
        pr28 = float(R[j]) if np.isfinite(R[j]) else np.nan
        f1, pr1 = G.locate(f, P, 30.0, 49.5, R=R)
        res["prior"][lbl] = dict(n=n, f0=f0, prom=pr, prom_at_2813=pr28, f_hi=f1, prom_hi=pr1)
        print(f"  {lbl:16} n={n:4d}  18-40 peak {f0:6.2f} prom {pr:6.2f}"
              f"{' *** LINE' if pr > 4 else '         '}   "
              f"prominence AT 28.13 Hz = {pr28:6.2f}   |   "
              f"30-49.5 peak {f1:5.2f} prom {pr1:5.2f}")

    G.hdr("2. COHERENCE, REDONE AGAINST THE ACTUAL COMMAND (0xE4 e4tq)")
    print("  benchmarks: grind #1 command<->bar 0.917 at 21.09 Hz; the highway 40-49 Hz")
    print("  population 0.169 in events vs 0.166 background.\n")
    res["coh"] = {}
    bands = ((1.0, 4.0, "1-4"), (10.0, 16.0, "10-16"), (18.0, 22.0, "18-22"),
             (24.0, 28.0, "24-28"), (26.5, 29.5, "26.5-29.5 (the line)"),
             (30.0, 40.0, "30-40"), (40.0, 49.0, "40-49"))
    print(f"  {'band':22} {'4e ENGAGED':>12} {'r47 ENGAGED':>13} {'4c MANUAL':>12}")
    for lo, hi, nm in bands:
        c1, n1 = coh(segs_of("4e"), True, lo, hi)
        c2, n2 = coh(prior_segs("r47/V67"), True, lo, hi)
        c3, n3 = coh(segs_of("4c"), False, lo, hi)
        res["coh"][nm] = dict(v68_on=c1, r47_on=c2, v68_off=c3, n=[n1, n2, n3])
        print(f"  {nm:22} {c1:12.3f} {c2:13.3f} {c3:12.3f}")
    print(f"\n  (window counts: 4e {n1}, r47 {n2}, 4c {n3})")
    print("  ⚠ the 4c column is a NEGATIVE CONTROL: lateral control is off, so openpilot's")
    print("    request is not being applied to the rack at all.")

    G.hdr("3. LANE CHANGES ANCHORED ON openpilot's OWN laneChange EVENT (route 4e)")
    ev = []
    for s in [31, 32, 33, 34]:
        p = ROOT / "_cache_v68" / f"4es{s}_events.json"
        if p.exists():
            for e in json.loads(p.read_text()):
                if e["name"] == "laneChange":
                    ev.append((s, e["t"]))
    print(f"  {len(ev)} laneChange events across segments "
          f"{sorted(set(s for s, _ in ev))}")
    W4e = wrecs_v68("4e")
    ON = [w for w in W4e if w["eng"] and w["v"] >= HWY]
    evbyseg = {}
    for s, t in ev:
        evbyseg.setdefault(s, []).append(t)
    WIN = NFFT / 100.0

    def near_lc(w, pad=1.5):
        ts = evbyseg.get(w["seg"], [])
        return any(w["t0"] - pad <= t <= w["t0"] + WIN + pad for t in ts)

    lc = [w for w in ON if near_lc(w)]
    bg = [w for w in ON if not near_lc(w, pad=4.0)]
    print(f"  {len(lc)} windows overlapping a laneChange (+-1.5 s), "
          f"{len(bg)} background windows (>4 s clear)")
    res["lanechange"] = dict(n_events=len(ev), n_lc=len(lc), n_bg=len(bg))
    if len(lc) >= 6 and len(bg) >= 10:
        print(f"\n  {'band':10} {'ratio [95% CI]':>26} {'null':>16}")
        for band in ("1-4", "10-16", "18-22", "24-28", "30-40", "40-49"):
            k = "e_" + band
            pt, ci = boot_ratio(lc, bg, k, rng)
            nl = split_null(bg, k, rng)
            sig = ("  *** outside the null" if np.isfinite(ci[0]) and np.isfinite(nl[1])
                   and ci[0] > nl[1] else "")
            res["lanechange"][band] = dict(ratio=pt, ci=ci, null=nl)
            print(f"  {band:10} {pt:9.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}] "
                  f"[{nl[0]:5.2f}, {nl[1]:5.2f}]{sig}")

        # The averaged spectrum of the lane-change windows themselves -- does the 28 Hz line
        # concentrate there? Built per segment so the event times stay attached to their own log.
        acc, nn, fref = None, 0, None
        for s, d in segs_of("4e"):
            ts = evbyseg.get(s, [])
            if not ts:
                continue
            fs = mean_fs(d["t"])
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            for a, b in runs_of(d["cc_lat"] > 0.5, d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    if float(np.mean(d["cs_v"][sl])) < HWY:
                        continue
                    t0 = float(d["t"][a + i])
                    if not any(t0 - 1.5 <= t <= t0 + WIN + 1.5 for t in ts):
                        continue
                    P = periodogram(d["tq"][a + i:a + i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    if acc is None:
                        acc, fref = np.zeros_like(P), f
                    if len(P) == len(acc):
                        acc += P; nn += 1
        if nn >= 6:
            Pm = acc / nn
            R = G.prom_spectrum(fref, Pm)
            f0, pr = G.locate(fref, Pm, 18.0, 40.0, R=R)
            fh, prh = G.locate(fref, Pm, 30.0, 49.5, R=R)
            j = int(np.argmin(np.abs(fref - 28.13)))
            res["lanechange"]["spec"] = dict(n=nn, f0=f0, prom=pr, prom_at_2813=float(R[j]),
                                             f_hi=fh, prom_hi=prh)
            print(f"\n  averaged spectrum of the {nn} lane-change windows:")
            print(f"    18-40 Hz peak {f0:6.2f} Hz prom {pr:6.2f}"
                  f"{'  *** LINE' if pr > 4 else ''}   "
                  f"prominence AT 28.13 Hz = {float(R[j]):6.2f}")
            print(f"    30-49.5 Hz peak {fh:6.2f} Hz prom {prh:6.2f}"
                  f"{'  *** LINE' if prh > 4 else '   (grind #2 band: no line)'}")

    Path(HERE / "_v68_line28.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {HERE / '_v68_line28.json'}")


if __name__ == "__main__":
    main()
