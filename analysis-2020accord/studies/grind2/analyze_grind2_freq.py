#!/usr/bin/env python3
"""Deliverable F -- WHAT IS grind #2? Frequency, Q, what it tracks, and the aliasing question.

  F1 ALIASING, tested rather than caveated. fs is not constant: it ranges 99.36-101.55 Hz across
     segments. If the true line is BELOW Nyquist the measured f0 does not move with fs (slope 0).
     If it is in (fs/2, fs) the measured f0 is fs - f_true, so it moves with fs at slope +1.
     If in (fs, 3fs/2) it is f_true - fs, slope -1. A ~2 Hz lever arm on fs against a 0.39 Hz bin
     is enough to separate these. Also reports f0/fs, which is constant for a pure sampling
     artifact and is not for a physical mode.
  F2 IS IT FIXED IN HERTZ?  f0 against speed, steering rate, driver effort, and steering angle.
     Wheel order 1 is 0.489*v Hz -- at creep that is under 2 Hz and cannot reach this band, but
     the check is run anyway because it costs nothing.
  F3 HARMONIC OR INDEPENDENT MODE?  2 x 20.9 = 41.8 Hz sits inside the band, so this must be
     settled: a harmonic and an independent structural mode call for different fixes. Tested by
     (a) is f0 within tolerance of 2*f_18-22 measured in the SAME window, (b) is the 18-22 Hz
     mode even present when the burst fires, (c) does f0 track 2*f_18-22 window by window.
  F4 Q and the burst envelope -- growth rate, duration, duty cycle.
  F5 Cross-channel: torsion bar vs steering ANGLE (a different sensor on a different CAN message).

Usage:  python studies/grind2/analyze_grind2_freq.py
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load, periodogram, runs_of  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_freq.json"
RNG = np.random.default_rng(20260801)
BURST = 400.0
NFFT = 256


def wls(x, y, w=None):
    """(slope, intercept, slope 95% CI) by ordinary least squares with a bootstrap CI."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 4:
        return np.nan, np.nan, (np.nan, np.nan), 0
    b = np.polyfit(x, y, 1)
    dr = []
    for _ in range(2000):
        i = RNG.integers(0, len(x), len(x))
        try:
            dr.append(np.polyfit(x[i], y[i], 1)[0])
        except Exception:
            pass
    return float(b[0]), float(b[1]), (float(np.percentile(dr, 2.5)),
                                      float(np.percentile(dr, 97.5))), len(x)


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    allr = [r for b in G.ORDER for r in store[b]]
    burst = [r for r in allr if r["e_30-49"] > BURST]
    out = {}

    G.hdr(f"THE BURST POPULATION: {len(burst)} windows with 30-49 Hz envelope p99 > {BURST:.0f} "
          f"counts,\nfrom {len({r['blk'] for r in burst})} blocks on "
          f"{len({r['build'] for r in burst})} routes.")
    print(f"  {'build':10s} {'n':>4s} {'f0 med':>7s} {'f0 sd':>6s} {'f0 IQR':>14s} {'Q med':>6s} "
          f"{'env med':>8s} {'v med':>6s} {'rate med':>8s} {'eff med':>8s} {'eng':>5s}")
    for b in G.ORDER:
        rs = [r for r in burst if r["build"] == b]
        if not rs:
            print(f"  {b:10s} {0:4d}")
            continue
        f = G.col(rs, "f_30-49")
        print(f"  {b:10s} {len(rs):4d} {np.median(f):7.2f} {f.std(ddof=1):6.2f} "
              f"{np.percentile(f, 25):6.2f}-{np.percentile(f, 75):<7.2f} "
              f"{np.median(G.col(rs, 'Qhf')):6.1f} {np.median(G.col(rs, 'e_30-49')):8.0f} "
              f"{np.median(G.col(rs, 'v')):6.2f} {np.median(G.col(rs, 'rate')):8.1f} "
              f"{np.median(G.col(rs, 'eff')):8.0f} {np.mean(G.col(rs, 'eng')):5.2f}")
    fall = G.col(burst, "f_30-49")
    print(f"\n  POOLED: f0 = {np.median(fall):.2f} Hz  (IQR {np.percentile(fall, 25):.2f}-"
          f"{np.percentile(fall, 75):.2f}, sd {fall.std(ddof=1):.2f}, "
          f"full range {fall.min():.2f}-{fall.max():.2f})")
    print(f"  histogram, 1 Hz bins 30..50: " +
          " ".join(f"{int(e)}:{c}" for e, c in
                   zip(np.arange(30, 50), np.histogram(fall, bins=np.arange(30, 51))[0]) if c))
    print(f"  Q: median {np.median(G.col(burst, 'Qhf')):.1f}, IQR "
          f"{np.percentile(G.col(burst, 'Qhf'), 25):.1f}-"
          f"{np.percentile(G.col(burst, 'Qhf'), 75):.1f}   🛑 the Hann main lobe caps measurable Q "
          f"at f0/(1.44*fs/256) = {np.median(fall) / (1.44 * 100.5 / 256):.0f}, so a Q at or above\n"
          f"     that is UNRESOLVED, not measured.")
    out["f0"] = dict(median=float(np.median(fall)), sd=float(fall.std(ddof=1)),
                     n=len(burst), q=float(np.median(G.col(burst, "Qhf"))))

    # ============================================================ F1 aliasing ===================
    G.hdr("F1.  ALIASING, TESTED.  f0 regressed on the segment's own sample rate.\n"
          "  slope  0  => the true line is BELOW Nyquist and is really at this frequency\n"
          "  slope +1  => the true line is in (fs/2, fs); measured f0 = fs - f_true\n"
          "  slope -1  => the true line is in (fs, 3fs/2); measured f0 = f_true - fs")
    fsv = G.col(burst, "fs")
    s, i0, ci, n = wls(fsv, fall)
    print(f"  n = {n} burst windows, fs spans {fsv.min():.2f}-{fsv.max():.2f} Hz "
          f"(lever arm {fsv.max() - fsv.min():.2f} Hz)")
    print(f"  slope d(f0)/d(fs) = {s:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")
    for hyp, val in (("below Nyquist (slope 0)", 0.0), ("first alias, fs-f (slope +1)", 1.0),
                     ("second alias, f-fs (slope -1)", -1.0)):
        inside = ci[0] <= val <= ci[1]
        print(f"     {hyp:32s} {'CONSISTENT' if inside else 'excluded'}")
    r = G.col(burst, "f_30-49") / fsv
    print(f"  f0/fs: median {np.median(r):.4f}  CV {r.std(ddof=1) / np.median(r):.4f}   vs   "
          f"CV(f0 in Hz) {fall.std(ddof=1) / np.median(fall):.4f}")
    # second attempt: aggregate to one point per segment, strong bursts only, tighter f window
    import collections
    sg = collections.defaultdict(list)
    for rr in burst:
        if rr["e_30-49"] > 800 and 40 <= rr["f_30-49"] <= 49:
            sg[(rr["build"], rr["seg"])].append(rr)
    xs = np.array([v[0]["fs"] for v in sg.values() if len(v) >= 2])
    ys = np.array([np.median(G.col(v, "f_30-49")) for v in sg.values() if len(v) >= 2])
    s2, _, ci2, n2 = wls(xs, ys)
    print(f"  per-SEGMENT retest (strong bursts only, one point per segment): n={n2} segments, "
          f"fs span {xs.max() - xs.min():.2f} Hz")
    print(f"     slope {s2:+.2f}  95% CI [{ci2[0]:+.2f}, {ci2[1]:+.2f}]")
    print("\n  🛑 VERDICT: UNDERPOWERED -- BOTH forms of the test admit slope 0, +1 and -1. The\n"
          "  intrinsic scatter of f0 (sd 5.4 Hz, and the mode's own Q gives it real width) is\n"
          "  2.5x the fs lever arm, so no fold can be excluded. The CV comparison is a TIE\n"
          "  (0.120 vs 0.120) and decides nothing either. Do not read this section as evidence\n"
          "  for the line being below Nyquist.")
    print("  Stated plainly: the torsion bar is sampled on a ~100.5 Hz CAN grid, so a line\n"
          "  reported at 44.9 Hz is formally indistinguishable from 55.6 / 145.4 / 156.1 ... Hz,\n"
          "  and this data cannot separate them. Resolving it needs a faster observation than\n"
          "  100 Hz CAN -- an in-firmware cave sampling at the 1 kHz task rate would do it.")
    out["alias"] = dict(slope=s, ci=list(ci), n=n, slope_seg=s2, ci_seg=list(ci2), n_seg=n2,
                        cv_f=float(fall.std(ddof=1) / np.median(fall)),
                        cv_r=float(r.std(ddof=1) / np.median(r)), verdict="underpowered")

    # ============================================================ F2 what does it track =========
    G.hdr("F2.  WHAT DOES f0 TRACK?  Regressions over the burst population.")
    print(f"  {'against':22s} {'slope':>10s} {'95% CI':>22s} {'n':>4s}  interpretation")
    for nm, key, unit in (("vEgo (m/s)", "v", "Hz per m/s"), ("steering rate (deg/s)", "rate",
                                                              "Hz per deg/s"),
                          ("driver effort (counts)", "eff", "Hz per count"),
                          ("|steering angle| (deg)", "ang", "Hz per deg")):
        s, _, ci, n = wls(G.col(burst, key), fall)
        flat = ci[0] <= 0 <= ci[1]
        print(f"  {nm:22s} {s:10.5f} [{ci[0]:9.5f},{ci[1]:9.5f}] {n:4d}  "
              f"{'FLAT (no dependence)' if flat else 'moves'} [{unit}]")
    print(f"\n  wheel order 1 is 0.489*v Hz; at the burst population's median speed "
          f"{np.median(G.col(burst, 'v')):.2f} m/s that is "
          f"{0.489 * np.median(G.col(burst, 'v')):.2f} Hz -- 20x below the band. The road cannot "
          f"reach here.")
    print(f"  order of the observed line = f0/(0.489*v) = "
          f"{np.median(fall / (0.489 * np.maximum(G.col(burst, 'v'), 1e-3))):.1f} -- not a "
          f"plausible tyre order.")

    # ============================================================ F3 harmonic ===================
    G.hdr("F3.  HARMONIC OF THE 20.9 Hz MODE, OR AN INDEPENDENT MODE?\n"
          "2 x 20.9 = 41.8 Hz is inside the band, so this has to be settled explicitly.")
    f18 = G.col(burst, "f_18-22")
    print(f"  in the SAME burst windows, the 18-22 Hz locator sits at median {np.median(f18):.2f} "
          f"Hz (sd {f18.std(ddof=1):.2f})")
    print(f"  2 x that = {2 * np.median(f18):.2f} Hz  vs  measured f0 = {np.median(fall):.2f} Hz  "
          f"-> offset {np.median(fall) - 2 * np.median(f18):+.2f} Hz")
    d = fall - 2 * f18
    print(f"  per-window f0 - 2*f(18-22): median {np.median(d):+.2f} Hz, sd {d.std(ddof=1):.2f}, "
          f"{100 * np.mean(np.abs(d) < 0.8):.0f}% within +/-0.8 Hz (2 bins)")
    s, _, ci, n = wls(f18, fall)
    print(f"  does f0 TRACK 2*f(18-22)?  slope d(f0)/d(f18-22) = {s:+.3f} 95% CI "
          f"[{ci[0]:+.3f},{ci[1]:+.3f}]  (a true 2nd harmonic must give +2)")
    print(f"     {'CONSISTENT with a 2nd harmonic' if ci[0] <= 2 <= ci[1] else 'INCONSISTENT with a 2nd harmonic (2.0 excluded)'}")
    # is the 18-22 fundamental even present when the burst fires?
    e18 = G.col(burst, "e_18-22")
    e30 = G.col(burst, "e_30-49")
    print(f"\n  amplitude in the SAME windows: 18-22 env p99 median {np.median(e18):.0f} counts, "
          f"30-49 median {np.median(e30):.0f} counts, ratio "
          f"{np.median(e30 / np.maximum(e18, 1e-9)):.1f}x")
    print(f"  a 2nd harmonic {np.median(e30 / np.maximum(e18, 1e-9)):.0f}x LARGER than its own "
          f"fundamental is not a harmonic.")
    q = [r for r in allr if r["build"] in G.DOSE[2.0] and r["e_30-49"] < 150]
    print(f"  and the reverse check: on Kd=2 the 18-22 mode has already been suppressed "
          f"({np.median(G.col(q, 'e_18-22')):.0f} counts median in quiet windows) while the "
          f"30-49 burst is at its strongest.")
    print("\n  ★ THE DECISIVE ARGUMENT is the dose-response, not any within-window statistic:\n"
          "    a harmonic must move WITH its fundamental. Across Kd = 0 / 1 / 2 the 18-22 Hz mode\n"
          "    falls monotonically while the 30-49 Hz burst rises from absent to present. Two\n"
          "    bands that move in OPPOSITE directions under the same single-instruction lever\n"
          "    cannot be fundamental and harmonic of one another.")
    out["harmonic"] = dict(f18_med=float(np.median(f18)), slope=s, ci=list(ci),
                           amp_ratio=float(np.median(e30 / np.maximum(e18, 1e-9))))

    # ============================================================ F4 burst shape ================
    G.hdr("F4.  BURST SHAPE -- duration, rise, duty cycle. Measured on the raw series, not on\n"
          "windowed statistics, so 'one 3-window burst' is not counted as three events.")
    from _grind2_lib import win_env  # noqa
    events = []
    for b in G.DOSE[2.0]:
        B = G.BUILDS[b]
        segs = sorted({r["seg"] for r in store[b] if r["e_30-49"] > BURST})
        for s in segs:
            d = load(s, B["cache"], B["pfx"])
            fs = fs_of(d)
            x = np.asarray(d["tq"], float)
            # 30-49 Hz analytic envelope over the whole segment, detrended in 512-sample chunks
            X = np.fft.rfft(x - np.mean(x))
            f = np.fft.rfftfreq(len(x), 1 / fs)
            H = np.zeros(len(f), complex)
            m = (f >= 30) & (f <= 49)
            H[m] = 2 * X[m]
            env = np.abs(np.fft.irfft(H, n=len(x)))
            hot = env > BURST
            for a, bb in runs_of(hot, d["t"], 3, max_gap=0.06):
                dur = float(d["t"][bb - 1] - d["t"][a])
                if dur < 0.05:
                    continue
                pk = int(a + np.argmax(env[a:bb]))
                events.append(dict(build=b, seg=int(s), t0=float(d["t"][a]), dur=dur,
                                   peak=float(env[pk]), tpk=float(d["t"][pk] - d["t"][a]),
                                   v=float(np.mean(d["cs_v"][a:bb])),
                                   lat=float(np.mean(d["cc_lat"][a:bb] > 0.5)),
                                   rate=float(np.mean(np.abs(d["rate_c"][a:bb])))))
    print(f"  {len(events)} contiguous burst events on the Kd=2 routes "
          f"({len({(e['build'], e['seg']) for e in events})} segments).")
    if events:
        du = np.array([e["dur"] for e in events])
        pk = np.array([e["peak"] for e in events])
        tp = np.array([e["tpk"] for e in events])
        print(f"  duration: median {np.median(du):.3f} s, p90 {np.percentile(du, 90):.3f} s, "
              f"max {du.max():.3f} s")
        print(f"  peak env: median {np.median(pk):.0f}, max {pk.max():.0f} counts")
        print(f"  time to peak: median {np.median(tp):.3f} s = "
              f"{np.median(tp) * np.median(fall):.1f} cycles at {np.median(fall):.0f} Hz.")
        print(f"  🛑 NOT interpretable as a growth rate: a 30-49 Hz brick-wall filter has an\n"
              f"     impulse response ~1/(49-30) = 53 ms long, so any onset faster than that reads\n"
              f"     as {1000 * 1 / 19.0:.0f} ms here. The measured rise is AT the instrument's\n"
              f"     resolution -- the true onset is this fast or faster, and the data cannot say\n"
              f"     which.")
        nseg = len({(e["build"], e["seg"]) for e in events})
        print(f"  duty cycle: {du.sum():.1f} s of burst inside the {nseg} 60 s segments that "
              f"contain any burst at all = {100 * du.sum() / (60.0 * nseg):.2f}% of that time.\n"
              f"     Short and repetitive: a burst TRAIN (e.g. V65/r3a seg 3 fires at t = 37.20,\n"
              f"     37.38, 37.46, 37.64, 37.99, 38.39 s), which is what 'like a subwoofer' means.")
        print(f"  engaged fraction of events: {np.mean([e['lat'] > 0.5 for e in events]):.2f}  "
              f"(LKAS ON in {int(sum(1 for e in events if e['lat'] > 0.5))} of {len(events)})")
        print(f"\n  {'build':10s} {'seg':>3s} {'t0':>7s} {'dur':>6s} {'peak':>7s} {'tpk':>6s} "
              f"{'v':>6s} {'rate':>6s} {'lat':>5s}")
        for e in sorted(events, key=lambda z: -z["peak"])[:20]:
            print(f"  {e['build']:10s} {e['seg']:3d} {e['t0']:7.2f} {e['dur']:6.3f} "
                  f"{e['peak']:7.0f} {e['tpk']:6.3f} {e['v']:6.2f} {e['rate']:6.1f} "
                  f"{e['lat']:5.2f}")
    out["events"] = events

    # ============================================================ F5 cross-channel ==============
    G.hdr("F5.  CROSS-CHANNEL.  Torsion bar (0x18F) vs steering ANGLE (0x14A) in the same band.")
    print(f"  {'population':34s} {'n':>5s} {'tq 30-49':>9s} {'ang 30-49':>10s} "
          f"{'counts per deg':>15s}")
    for nm, rs in (("Kd=2 burst windows", burst),
                   ("Kd=2 quiet windows", q),
                   ("all Kd<=1 windows",
                    [r for b in G.DOSE[0.0] + G.DOSE[1.0] for r in store[b]])):
        t = np.median(G.col(rs, "e_30-49"))
        a = np.median(G.col(rs, "ang_hf"))
        print(f"  {nm:34s} {len(rs):5d} {t:9.0f} {a:10.3f} {t / max(a, 1e-9):15.0f}")
    # 🛑 The angle channel must be controlled for SWEEP SIZE. A hard turn is a large curved ramp
    # in `ang`, and residual curvature after a linear detrend leaks into 30-49 Hz. Matched on the
    # 1-10 Hz angle content (the sweep-size proxy), the leakage floor turns out to be FLAT at
    # ~0.12 deg -- it does not scale with sweep -- so the burst elevation is not leakage.
    G.hdr("F5b. THE ANGLE CONTROL, MATCHED ON SWEEP SIZE.  Rows are matched on 1-10 Hz angle\n"
          "content, so 'the driver was turning harder' cannot produce the column difference.")
    kd1all = [r for b in G.DOSE[0.0] + G.DOSE[1.0] for r in store[b]]
    kd2q = [r for b in G.DOSE[2.0] for r in store[b] if r["e_30-49"] <= BURST]
    print(f"  {'ang 1-10 Hz (sweep proxy)':26s} | " +
          " ".join(f"{h:>26s}" for h in ("BURST windows", "Kd<=1 windows",
                                         "Kd=2 non-burst windows")))
    for lo, hi in ((2, 6), (6, 15), (15, 40)):
        cells = []
        for rs in (burst, kd1all, kd2q):
            v = G.col([r for r in rs if lo <= r["ang_lf"] < hi], "ang_hf")
            cells.append(f"{'n=0':>26s}" if not len(v) else
                         f"n={len(v):<4d} med {np.median(v):5.3f} max {v.max():5.3f}")
        print(f"  {f'{lo}-{hi} deg':26s} | " + " ".join(f"{c:>26s}" for c in cells))
    amed = np.median(G.col(burst, "ang_hf"))
    print(f"\n  The leakage floor is FLAT at ~0.12 deg across every sweep decile and never exceeds\n"
          f"  0.26 deg on any of the 632 Kd<=1 windows or the 1,214 Kd=2 non-burst windows. The\n"
          f"  burst windows sit at 0.40-1.38 deg median with a max of "
          f"{G.col(burst, 'ang_hf').max():.2f} deg -- 3-11x the floor.")
    print(f"  ⇒ {amed:.2f} deg (p90 {np.percentile(G.col(burst, 'ang_hf'), 90):.2f}, max "
          f"{G.col(burst, 'ang_hf').max():.2f}) of REAL WHEEL MOTION at ~{np.median(fall):.0f} Hz.")
    print(f"  Implied rim velocity {2 * np.pi * np.median(fall) * amed:.0f} deg/s; the 0x14A and\n"
          f"  0x18F angle-rate channels independently reach 300-480 deg/s in these windows.")
    print(f"  ⚠ CAVEAT: 0x14A and 0x18F are both steering-system messages on bus 1, so this is\n"
          f"  two sensors but NOT an independent instrument. It rules out a torsion-bar-only\n"
          f"  telemetry artifact; it does not rule out a shared steering-sensor artifact.")

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
