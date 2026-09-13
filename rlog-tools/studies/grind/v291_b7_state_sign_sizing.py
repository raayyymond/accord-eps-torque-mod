# -*- coding: utf-8 -*-
"""v291_b7_state_sign_sizing.py -- SIZING for V291's telemetry rung.

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

THE QUESTION.  V291 moves the LKAS rate-PID feedback-lag pole DOWN (0xC63E8/0xC63EA, 923/1560 ->
950/1143 = C12 or 974/772 = C8).  The filter's state `s` lives at gp-0x3d30 and is invisible: a
two-encoding census finds exactly TWO accesses to it image-wide, both inside the filter.  V291
therefore repoints the 0x14A cave's b7 rung onto it (one displacement halfword at 0xC4B94,
ld.h -0x6b4c[gp],r6 -> ld.w -0x3d30[gp],r6), so the wire publishes sign(s) at 100 Hz.

WHAT THIS SCRIPT DECIDES, and it changed the design:
  1. ld.w (32-bit) vs ld.h of the low halfword.  |s| exceeds 32767 on 0.18-0.36 % of frames and peaks
     at 52,821, so a 16-bit low-halfword read would report the WRONG SIGN roughly 1 frame in 300, in
     exactly the high-rate frames.  ** USE ld.w. **  (`s` is NOT clamped -- the +-46080 clamp is
     applied to the OUTPUT at 0x28FA6..0x28FBC, AFTER `st.w r9,-0x3d30[gp]` at 0x28FA8.)
  2. WHICH STATISTIC to read off the bit.  The brief proposed the DUTY of sign(s) != sign(0x18F rate).
     Measured, that is only x1.05 (C12) / x1.10 (C8) -- NOT resolvable.  The TRANSITION RATE of the
     same bit is x0.84-0.88 (C12) / x0.76-0.81 (C10) / x0.67-0.71 (C8), reproducing to +-0.02
     across four routes and
     across two different 100 Hz -> 1 kHz reconstructions.  ** READ THE TRANSITION RATE. **
  3. Per-FRAME agreement is NOT a usable test: sign(s) differs between the V282 and C8 poles on only
     3.3-4.4 % of frames while the reconstruction ambiguity alone is 2.0-3.4 %.

METHOD.  Each route's own 0x18F STEER_ANGLE_RATE (uniform 100 Hz frame axis, raw counts: the 0.125
deg/s LSB is 1 raw count of `x` -- 8 counts per deg/s) is upsampled to the filter's 1 kHz tick and run
through a BYTE-EXACT mirror of 0x28F86..0x28FA8.  Both linear-interpolation and zero-order-hold
upsampling are run; the ratio columns are the ones that agree between them, which is the point.
⚠ The wire cannot show content above 50 Hz, so the ABSOLUTE rates are reconstruction-limited.  Only
the V282-vs-dose RATIO is quoted as a prediction, and only because it survives both reconstructions.

USAGE:  ACCORD_FIRMWARE_ROOT=... python v291_b7_state_sign_sizing.py [route ...]
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CPD = 8.0                 # raw counts of x per deg/s == 0x18F STEER_ANGLE_RATE LSB 0.125 deg/s
FS = 100.0                # the 0x14A / 0x18F frame rate
TICK_HZ = 1000.0          # the filter's tick
X_SAT = 12000             # producer saturation at 0x3F7B8 / 0x3F7D0 / 0x3F7E0

POLES = {"V282": (923, 1560), "C12": (950, 1143), "C10": (962, 958), "C8": (974, 772)}
ROUTES = ("r39", "r3a", "r3c", "r35")     # V282 / V282 / V282 / V281r3 -- all carry V282's fb pole


def fb_state(x, a, b):
    """byte-exact mirror of the state recurrence, 0x28F86..0x28FA8.  Returns the stored state s[n].
       s_new = ((b*x) >> 10) + ((a*s) >> 10)   -- TWO separate arithmetic floors
       out   = s + s_new                       -- the two-sample sum (r26), clamped AFTER the store
       s    := s_new                           -- 0x28FA8 st.w, 32-bit, NOT clamped
    """
    s = 0
    S = np.empty(len(x), dtype=np.int64)
    for i in range(len(x)):
        xi = int(x[i])
        if not (-X_SAT <= xi <= X_SAT):        # 0x28F58 bnc -> BAIL: sentinel := 2, s zeroed next tick
            s = 0
            S[i] = 0
            continue
        s = ((b * xi) >> 10) + ((a * s) >> 10)
        S[i] = s
    return S


def analytic_lag_deg(a, f):
    """arg of S(z)/X(z) = (b/1024)/(1 - (a/1024)z^-1): the lag of the STATE behind x at f."""
    return float(np.degrees(np.angle(1 - (a / 1024.0) * np.exp(-1j * 2 * np.pi * f / TICK_HZ))))


def upsample(x100, how):
    n = len(x100)
    tgt = np.arange(0, (n - 1) * 10 + 1) / TICK_HZ
    if how == "lin":
        return np.round(np.interp(tgt, np.arange(n) / FS, x100.astype(float))).astype(np.int64)
    return x100[np.minimum(np.arange(len(tgt)) // 10, n - 1)]


def load(tag):
    D = np.load(os.path.join(CACHE, tag, tag + ".npz"), allow_pickle=True)
    x100 = np.round(np.asarray(D["rate_c"], float) * CPD).astype(np.int64)
    eng = np.asarray(D["sca"], float).astype(bool) & np.asarray(D["e4req"], float).astype(bool)
    v = np.asarray(D["cs_v"], float)
    bar = np.abs(np.asarray(D["tq"], float)) * 1.024        # accord-wire-torque-is-raw-times-1024
    creep = eng & (v > 1.0) & (v < 3.0) & (bar < 400)       # hands-off creep, the grinding stratum
    b4 = np.asarray(D["raw14_b4"], float) if "raw14_b4" in D.files else None
    return x100, eng, creep, b4


def main(routes):
    print("=" * 108)
    print("  ANALYTIC -- lag of the STATE behind x, and the duty a PURE SINUSOID at f would produce")
    print("=" * 108)
    fs = (3, 5, 7, 10, 13, 16, 20, 25)
    print("  pole   " + "".join(f"{f:>9.0f}Hz" for f in fs))
    for nm, (a, _b) in POLES.items():
        lags = [analytic_lag_deg(a, f) for f in fs]
        print(f"  {nm:6s} " + "".join(f"{l:8.1f}d " for l in lags))
        print(f"  {'':6s} " + "".join(f"{l / 180:8.3f}  " for l in lags) + "  <- duty = lag/180")
    print("\n  🛑 The sinusoid duty is NOT what a real drive produces: real x is dominated by")
    print("     low-frequency content where the poles barely differ.  The measured tables follow.")

    print("\n" + "=" * 108)
    print("  MEASURED -- byte-exact mirror driven by each route's own 0x18F rate")
    print("=" * 108)
    agg = {k: [] for k in POLES}
    for tag in routes:
        if not os.path.exists(os.path.join(CACHE, tag, tag + ".npz")):
            print(f"  -- {tag}: not cached, skipped")
            continue
        x100, eng, creep, b4 = load(tag)
        n = len(x100)
        print(f"\n  === {tag}   engaged(lat) {eng.sum() / FS:6.0f} s   hands-off creep "
              f"{creep.sum() / FS:5.0f} s   |x| p50/p90/p99/max "
              f"{np.percentile(np.abs(x100), 50):.0f}/{np.percentile(np.abs(x100), 90):.0f}/"
              f"{np.percentile(np.abs(x100), 99):.0f}/{np.abs(x100).max():.0f} raw ===")
        print(f"      {'pole':5s} {'recon':5s} {'trans/s eng':>12s} {'ratio':>7s} "
              f"{'trans/s creep':>14s} {'ratio':>7s} {'duty eng':>9s} {'ratio':>7s} "
              f"{'|s|>=32768':>11s} {'max|s|':>8s}")
        base_tr = {}
        for how in ("lin", "zoh"):
            xx = upsample(x100, how)
            idx = np.arange(0, len(xx), 10)
            row = {}
            for nm, (a, b) in POLES.items():
                s100 = fb_state(xx, a, b)[idx][:n]
                sg = np.sign(s100)
                tr_e = float(np.mean((np.abs(np.diff(sg)) > 0)[eng[1:n]]) * FS)
                tr_c = float(np.mean((np.abs(np.diff(sg)) > 0)[creep[1:n]]) * FS) if creep.sum() > 1 \
                    else float("nan")
                du_e = float((sg != np.sign(x100))[eng].mean())
                row[nm] = (tr_e, tr_c, du_e, float(np.mean(np.abs(s100) >= 32768) * 100),
                           int(np.abs(s100).max()))
            if how == "lin":
                base_tr = row
                for nm in POLES:
                    agg[nm].append((row[nm][0] / row["V282"][0], row[nm][1] / row["V282"][1],
                                    row[nm][2] / row["V282"][2]))
            for nm in POLES:
                tr_e, tr_c, du_e, big, mx = row[nm]
                print(f"      {nm:5s} {how:5s} {tr_e:12.2f} {tr_e / row['V282'][0]:7.3f} "
                      f"{tr_c:14.2f} {tr_c / row['V282'][1]:7.3f} {du_e:9.4f} "
                      f"{du_e / row['V282'][2]:7.3f} {big:10.3f}% {mx:8d}")
        if b4 is not None:
            ok = np.isfinite(b4)
            if ok.sum():
                bit7 = (np.asarray(b4[ok], int) >> 7) & 1
                print(f"      b7 AS FLOWN TODAY (sign gp-0x6b4c): duty {bit7.mean():.4f}, "
                      f"{np.mean(np.abs(np.diff(bit7)) > 0) * FS:.1f} transitions/s over {ok.sum()} "
                      f"frames  <- the positive control for 'did the repoint take'")

    print("\n" + "=" * 108)
    print("  THE PREDICTION V291 SHOULD BE SCORED AGAINST  (mean +- range over the routes above)")
    print("=" * 108)
    for nm in POLES:
        if not agg[nm]:
            continue
        A = np.array(agg[nm], float)
        print(f"    {nm:5s}  b7 transitions/s, engaged : x{A[:, 0].mean():.3f}  "
              f"[{A[:, 0].min():.3f}, {A[:, 0].max():.3f}]        "
              f"creep : x{np.nanmean(A[:, 1]):.3f}  [{np.nanmin(A[:, 1]):.3f}, {np.nanmax(A[:, 1]):.3f}]"
              f"        duty : x{A[:, 2].mean():.3f}")
    print("""
  HOW TO SCORE IT ON THE DRIVE -- WITHIN-DRIVE, NEVER CROSS-BUILD.
    The V282 baseline transition rate ranges 5.2-7.6 /s across routes, so a cross-route contrast is
    confounded by traffic.  Replay the FLOWN drive's OWN 0x18F rate through the mirror above at BOTH
    the V282 pole and the flown pole, and ask which predicts the observed b7 transition rate.  The two
    predictions differ by ~18 % (C12), ~27 % (C10) or ~31 % (C8); reconstruction ambiguity ~2 %.
    That is a LIVENESS AND DOSE test, and it accrues on ordinary engaged driving -- it does not need
    the grinding to occur.
  FAIL MODES:  b7 stuck at 0 or 1 over >= 20 s engaged (the repoint did not take, or the cave stopped
    firing -- b5/b6 staying live separates those two);  or b7 reading duty ~0.40 with 3.6-4.4
    transitions/s, i.e. STILL sign(gp-0x6b4c), meaning the displacement did not land.
""")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ROUTES)
