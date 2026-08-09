#!/usr/bin/env python3
"""Follow-up to `relay_fingerprint_r6e.py`: the POSITIVE CONTROLS that make its nulls readable,
the absolute-amplitude check that makes its one POSITIVE result safe, and the micro/macro split.

🛑 WHY THIS FILE EXISTS.  `relay_fingerprint_r6e.py` returned two nulls (no odd-harmonic comb, no
3:1 phase locking) and one strong positive (a fixed ~8 Hz ridge, 3.2x more prominent on V85).
Neither is reportable as it stands:

  P1  A NULL WITHOUT A POSITIVE CONTROL IS UNINTERPRETABLE -- this kit's own recorded failure mode
      (`accord-v68-detector-still-zero-no-positive-control`).  The bar is measured THROUGH the
      column, whose wheel-on-torsion-bar mode sits at 12.8 Hz, so a 3rd harmonic at ~24 Hz is
      rolled off relative to its 8 Hz fundamental.  P1 INJECTS a synthetic relay comb of known
      size into the REAL windows and re-runs T1/T2 verbatim.  If the estimator recovers an injected
      comb at the amplitude a relay would actually produce at the bar, the null MEANS something.
      If it cannot, the null means only "not detectable here".

  P2  PROMINENCE IS A RATIO TO THE LOCAL FLOOR.  V85 drove slower on a smoother road (cell-matched
      IMU 0.958), so a lower broadband floor RAISES prominence with no change in the line itself.
      P2 measures the ABSOLUTE band amplitude at the fixed line, speed-matched.

  P3  T4's null was ONE random placement per window.  P3 uses 40 and bootstraps.

  P4  MICRO- vs MACRO-RATCHETING.  Tested, not assumed: is the ~8 Hz envelope ONE population or
      TWO?  If two, they should differ in f0, speed slope, engagement ratio or burst structure.

Usage:
    python relay_fingerprint_r6e_b.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import relay_fingerprint_r6e as RF  # noqa: E402  -- the windowing + estimators, reused verbatim
import _grind2_lib as G  # noqa: E402

NW, MACRO, CIRC = RF.NW, RF.MACRO, RF.CIRC
RNG = np.random.default_rng(85_7791)
OUT = {}


def _prom_at(f, R, ft, half=0.35):
    m = (np.abs(f - ft) <= half) & np.isfinite(R)
    return float(np.nanmax(R[m])) if m.any() else np.nan


def comb_stat(x, fs, f0):
    """T1's statistic, recomputed on an arbitrary waveform: (h2, h3, h4, h5, odd/even)."""
    from _r31_common import periodogram
    P = periodogram(x, fs, nfft=NW, detrend=True)
    if P is None:
        return None
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    R = G.prom_spectrum(f, P, halfwin=3.0, exclude=0.6)
    h = [_prom_at(f, R, k * f0) for k in (2, 3, 4, 5)]
    odd, even = np.nanmean([h[1], h[3]]), np.nanmean([h[0], h[2]])
    return h, (odd / even if (np.isfinite(odd) and np.isfinite(even) and even > 0) else np.nan)


def p1(recs):
    """POSITIVE CONTROL for T1/T2: inject a relay comb of known size into the REAL bar signal.

    A symmetric relay's Fourier series is  sin(w t) + sin(3 w t)/3 + sin(5 w t)/5 ...
    The column then filters it.  Modelled as a 2nd-order plant at f_r = 12.8 Hz, Q = 13.6 -- the
    kit's own measured wheel-on-torsion-bar mode -- so the 3rd and 5th harmonics arrive attenuated
    exactly as a real relay's would.  `amp` is the injected FUNDAMENTAL as a fraction of the
    window's own 6-9 Hz envelope, so 1.00 = "the entire observed 8 Hz line is relay-generated".
    """
    RF.hdr("P1  POSITIVE CONTROL for the comb -- inject a plant-filtered relay of known size into\n"
           "    the REAL windows and re-run T1's estimator.  🛑 If an injected comb at amp=1.00 is\n"
           "    not recovered, T1's null says NOTHING about whether a relay exists.")
    fr, Q = 12.8, 13.6

    def plant(fq):
        s = 1j * fq / fr
        return abs(1.0 / (1.0 - (fq / fr) ** 2 + s / Q))

    b_bp = butter(2, [6.0, 9.0], btype="band", fs=101.0)
    print(f"    plant |H| at  8.0 Hz {plant(8.0):.3f} · 24.0 Hz {plant(24.0):.3f} · "
          f"40.0 Hz {plant(40.0):.3f}")
    print(f"    ⇒ a relay's 3rd harmonic reaches the bar at "
          f"{(1/3)*plant(24.0)/plant(8.0):.4f} of its fundamental, 5th at "
          f"{(1/5)*plant(40.0)/plant(8.0):.4f}\n")
    print(f"    {'inject amp':>11s} {'odd/even med':>13s} {'95% CI':>20s} {'frac oe>1.3':>12s}")
    OUT["p1"] = {}
    base = []
    for r in recs:
        c = comb_stat(r["x"], r["fs"], r["f0"])
        if c:
            base.append(c[1])
    for amp in (0.0, 0.15, 0.30, 0.60, 1.00):
        vals, units = [], []
        for r in recs:
            f0 = r["f0"]
            if not np.isfinite(f0):
                continue
            env = float(np.percentile(np.abs(hilbert(filtfilt(*b_bp, r["x"]))), 99))
            n = np.arange(NW) / r["fs"]
            ph = RNG.uniform(0, 2 * np.pi)
            sig = np.zeros(NW)
            for k, w in ((1, 1.0), (3, 1 / 3), (5, 1 / 5)):
                fq = k * f0
                if fq < 0.47 * r["fs"]:
                    sig += w * plant(fq) / plant(f0) * np.sin(2 * np.pi * fq * n + k * ph)
            c = comb_stat(r["x"] + amp * env * sig, r["fs"], f0)
            if c:
                vals.append(c[1]); units.append(r["blk"])
        m = RF._boot_med(vals, units)
        fr13 = float(np.mean(np.array(vals) > 1.3))
        print(f"    {amp:11.2f} {m[0]:13.3f} [{m[1]:8.3f},{m[2]:8.3f}] {100*fr13:11.1f}%")
        OUT["p1"][f"{amp:.2f}"] = dict(oe=list(m), frac_gt_1p3=fr13)
    print("\n    🛑 amp=0.00 is the observed data.  If odd/even rises MONOTONICALLY with the\n"
          "       injected amplitude, the estimator works and the observed value bounds how much\n"
          "       of the 8 Hz line can be relay-generated.")


def p2(W):
    """ABSOLUTE amplitude at the fixed line, speed-matched -- prominence alone is a ratio."""
    RF.hdr("P2  ABSOLUTE AMPLITUDE at the fixed ~7.79 Hz line, SPEED-MATCHED.  🛑 T3's prominence\n"
           "    is a ratio to the local floor, and V85's floor is lower (smoother road, lower\n"
           "    speed).  This asks whether the LINE ITSELF is bigger, not just cleaner.")
    b = butter(2, [7.2, 8.4], btype="band", fs=101.0)
    per = {}
    for route, arm, recs in W:
        if arm != "engaged":
            continue
        for r in recs:
            r["a779"] = float(np.percentile(np.abs(hilbert(filtfilt(*b, r["x"]))), 99))
        per[route] = recs
    VB = ((0, 2), (2, 4), (4, 6), (6, 8), (8, 11), (11, 16), (16, 40))
    print(f"    {'v bin m/s':>10s} | " + " | ".join(f"{k.split('/')[0]:>22s}" for k in per))
    OUT["p2"] = {}
    for lo, hi in VB:
        row = f"    {f'{lo}-{hi}':>10s} | "
        cells = []
        for k, recs in per.items():
            m = [r for r in recs if lo <= r["v"] < hi]
            if len(m) < 4:
                cells.append(f"{'-- n=' + str(len(m)) + ' --':>22s}")
                continue
            s = RF._boot_med([r["a779"] for r in m], [r["blk"] for r in m])
            cells.append(f"{s[0]:8.1f} [{s[1]:5.0f},{s[2]:5.0f}] n={s[3]:<2d}")
            OUT["p2"].setdefault(k, {})[f"{lo}-{hi}"] = list(s)
        print(row + " | ".join(cells))
    print("\n    prominence at the same line, for comparison (from T3): "
          "V85 17.10 · V84 6.37 · V81 5.36")
    # matched-bin pooled ratio: only bins all three occupy
    print("\n    pooled over the v bins BOTH routes occupy (equal weight per bin):")
    for A, B in (("V85/r6e", "V84/r6d"), ("V85/r6e", "V81/r67")):
        lr = []
        for lo, hi in VB:
            a = [r["a779"] for r in per[A] if lo <= r["v"] < hi]
            bb = [r["a779"] for r in per[B] if lo <= r["v"] < hi]
            if len(a) >= 4 and len(bb) >= 4:
                lr.append(np.log(np.median(a) / np.median(bb)))
        print(f"      {A.split('/')[0]}/{B.split('/')[0]}  absolute-amplitude ratio "
              f"{np.exp(np.mean(lr)):.3f}  over {len(lr)} shared v bins")
        OUT["p2"][f"ratio|{A}|{B}"] = dict(ratio=float(np.exp(np.mean(lr))), bins=len(lr))


def p3(W):
    """T4 with a proper null: 40 random placements per window, bootstrapped over blocks."""
    RF.hdr("P3  SWITCHING-SURFACE TIMING, with a PROPER null (40 random placements per window,\n"
           "    episode-bootstrapped) -- T4 used a single draw and could not support a verdict.")
    LAGS = np.arange(-30, 31)
    print(f"    {'build':10s} {'n':>4s} | {'ETA peak/base':>24s} | {'NULL peak/base':>24s} | "
          f"{'excess':>7s}")
    OUT["p3"] = {}
    for route, arm, recs in W:
        if arm != "engaged":
            continue
        eta, nul, units = [], [], []
        for r in recs:
            e = r["env"] / (np.median(r["env"]) + 1e-9)
            z = r["x_lf"]
            cr = np.flatnonzero((z[:-1] < 0) & (z[1:] >= 0)) + 1
            cr = cr[(cr > 40) & (cr < NW - 40)]
            if len(cr) < 2:
                continue
            A = np.mean([e[c + LAGS] for c in cr], axis=0)
            eta.append(A.max() / np.mean(np.r_[A[:10], A[-10:]]))
            nn = []
            for _ in range(40):
                pc = RNG.integers(40, NW - 40, len(cr))
                N = np.mean([e[c + LAGS] for c in pc], axis=0)
                nn.append(N.max() / np.mean(np.r_[N[:10], N[-10:]]))
            nul.append(float(np.mean(nn)))
            units.append(r["blk"])
        if len(eta) < 5:
            continue
        a = RF._boot_med(eta, units)
        b = RF._boot_med(nul, units)
        exc = RF._boot_med(list(np.array(eta) - np.array(nul)), units)
        print(f"    {route:10s} {len(eta):4d} | {a[0]:8.4f} [{a[1]:7.4f},{a[2]:7.4f}] | "
              f"{b[0]:8.4f} [{b[1]:7.4f},{b[2]:7.4f}] | {exc[0]:+7.4f}")
        OUT["p3"][route] = dict(n=len(eta), eta=list(a), null=list(b), excess=list(exc))
    print("\n    🛑 The verdict is the EXCESS and whether its CI clears 0 -- printed below.")
    for k, v in OUT["p3"].items():
        e = v["excess"]
        print(f"      {k:10s} excess {e[0]:+.4f} [{e[1]:+.4f}, {e[2]:+.4f}]  "
              f"{'TIME-LOCKED' if e[1] > 0 else 'not distinguishable from chance'}")


def p4(W):
    """MICRO- vs MACRO-RATCHETING: is the ~8 Hz envelope one population or two?"""
    RF.hdr("P4  MICRO- vs MACRO-RATCHETING -- TESTED, NOT ASSUMED.  Split the engaged ~8 Hz\n"
           "    envelope at its own median and ask whether the two halves are different KINDS of\n"
           "    signal (f0, speed slope, burst structure) or just two amplitudes of one.")
    b = butter(2, [7.2, 8.4], btype="band", fs=101.0)
    OUT["p4"] = {}
    for route, arm, recs in W:
        if arm != "engaged" or len(recs) < 20:
            continue
        for r in recs:
            e = np.abs(hilbert(filtfilt(*b, r["x"])))
            r["a779"] = float(np.percentile(e, 99))
            m = np.median(e)
            r["burst_duty"] = float(np.mean(e > 2.0 * m))       # fraction of time above 2x median
            r["crest"] = float(np.max(e) / (m + 1e-9))
            # burst RATE: upward crossings of 2x median, per second
            up = np.flatnonzero((e[:-1] <= 2 * m) & (e[1:] > 2 * m))
            r["burst_rate"] = float(len(up) / (NW / r["fs"]))
        a = np.array([r["a779"] for r in recs])
        thr = float(np.median(a))
        lo_ = [r for r in recs if r["a779"] <= thr]
        hi_ = [r for r in recs if r["a779"] > thr]
        print(f"\n  {route}   n={len(recs)}   split at a779 = {thr:.0f} counts")
        print(f"    {'':22s} {'LOW half':>26s} {'HIGH half':>26s}")
        rows = {}
        for k, nm in (("a779", "amplitude (counts)"), ("f_free", "free argmax f0 (Hz)"),
                      ("v", "speed (m/s)"), ("burst_duty", "duty above 2x median"),
                      ("burst_rate", "burst rate (per s)"), ("crest", "crest (max/median)")):
            s1 = RF._boot_med([r[k] for r in lo_], [r["blk"] for r in lo_])
            s2 = RF._boot_med([r[k] for r in hi_], [r["blk"] for r in hi_])
            print(f"    {nm:22s} {s1[0]:9.2f} [{s1[1]:7.2f},{s1[2]:7.2f}] "
                  f"{s2[0]:9.2f} [{s2[1]:7.2f},{s2[2]:7.2f}]")
            rows[k] = dict(lo=list(s1), hi=list(s2))
        # speed slope within each half
        for nm, half in (("LOW", lo_), ("HIGH", hi_)):
            v = np.array([r["v"] for r in half]); f = np.array([r["f_free"] for r in half])
            A = np.vstack([v, np.ones_like(v)]).T
            sl = float(np.linalg.lstsq(A, f, rcond=None)[0][0])
            print(f"    {nm} half: f0 slope vs speed {sl:+.4f} Hz per m/s")
            rows[f"slope_{nm}"] = sl
        # bimodality: Hartigan-style dip is overkill; use the log-amplitude histogram's shape
        la = np.log(a[a > 0])
        sk = float(((la - la.mean()) ** 3).mean() / la.std() ** 3)
        ku = float(((la - la.mean()) ** 4).mean() / la.std() ** 4)
        print(f"    log-amplitude skew {sk:+.3f}  kurtosis {ku:.3f}   "
              f"(a single log-normal population gives skew ~0, kurtosis ~3; "
              f"{'BIMODAL-ish' if ku < 2.3 else 'consistent with ONE population'})")
        rows["log_skew"], rows["log_kurt"] = sk, ku
        OUT["p4"][route] = rows


def main():
    RF.SB.build_records()      # registers the routes
    W = []
    for route, cache, pfx, segs in RF.ROUTES:
        rs = RF.spectra(RF.windows(route, cache, pfx, segs, engaged=True))
        W.append((route, "engaged", rs))
        print(f"  {route}: {len(rs)} engaged windows", flush=True)
    v85 = [r for rt, _, rr in W if rt == "V85/r6e" for r in rr]
    p1(v85)
    p2(W)
    p3(W)
    p4(W)
    (ROOT / "_cache_r6e" / "relay_fingerprint_b.json").write_text(json.dumps(OUT, indent=1))
    print(f"\nwrote {ROOT / '_cache_r6e' / 'relay_fingerprint_b.json'}")


if __name__ == "__main__":
    main()
