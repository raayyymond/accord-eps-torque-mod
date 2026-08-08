#!/usr/bin/env python3
"""T2 -- SATURATION AND WINDUP SIGNATURE for the V81 outer-loop test.

H1 requires openpilot's outer loop to be WOUND UP: the command pinned at STEER_MAX against a plant
that will not deliver, so the error keeps integrating.  That is a directly measurable claim.

  T2a  rail duty at STEER_MAX = 4096 and at the 123 ct/frame slew cap, by speed regime and
       specifically inside the instability event.
  T2b  waveform character during the event: crest factor and rail duty -- bang-bang or sinusoid?
  T2c  windup: phase between commanded torque and the angle error openpilot is acting on.
  T2d  DEMANDED vs ACHIEVED angle rate -- the operator's own claim.

🛑 The rate columns: `rate_c` (0x14A, x-1.0) is quantised to 1 deg/s.  `rate_f` (0x18F, x-0.1 as
   stored) is the 8.000x-finer copy but the stored scale is WRONG BY 0.8 -- measured on five
   segments below 2 Hz, rate_f/rate_c = 0.7954 +- 0.006, i.e. the true factor is -0.125 and
   `rate_fine_degs = rate_f * 1.25`.  Everything here uses that.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v81loop_lib import CACHE, band_env, fs_run, load_seg  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEGS = list(range(14))
STEER_MAX = 4096.0
SLEW = 123.0            # openpilot's per-frame command slew cap, counts/frame
RATE_FIX = 1.25         # rate_f as stored -> true deg/s
EVENT = (8, 38.0, 52.0)
STEER_RATIO = 16.0      # 2020 Accord; used only for the demanded-rate conversion, stated as such
WHEELBASE = 2.83


def allsegs():
    for s in SEGS:
        try:
            yield s, load_seg(s)
        except Exception:
            continue


def main():
    print("=" * 104)
    print("T2a  RAIL AND SLEW-CAP DUTY, by speed regime.  engaged = cc_lat.  command = sendcan 0x0E4")
    print("=" * 104)
    bins = [("creep <4 m/s", 0, 4), ("4-11", 4, 11), ("11-20", 11, 20),
            ("20-24", 20, 24), (">24 (highway)", 24, 99)]
    acc = {b[0]: dict(n=0, rail=0, near=0, slew=0, amax=0.0, asum=0.0) for b in bins}
    for s, d in allsegs():
        eng = d["cc_lat"] > 0.5
        c = np.asarray(d["sc_tq"], float)
        dc = np.abs(np.diff(c, prepend=c[0]))
        for nm, lo, hi in bins:
            m = eng & (d["cs_v"] >= lo) & (d["cs_v"] < hi)
            if not m.any():
                continue
            a = acc[nm]
            a["n"] += int(m.sum())
            a["rail"] += int((np.abs(c[m]) >= 0.995 * STEER_MAX).sum())
            a["near"] += int((np.abs(c[m]) >= 0.90 * STEER_MAX).sum())
            a["slew"] += int((dc[m] >= 0.98 * SLEW).sum())
            a["amax"] = max(a["amax"], float(np.abs(c[m]).max()))
            a["asum"] += float(np.abs(c[m]).sum())
    print(f"  {'regime':>16} {'sec':>7} {'|cmd| mean':>11} {'|cmd| max':>10} "
          f"{'% at rail':>10} {'% >=90%':>9} {'% at slew':>10}")
    for nm, _, _ in bins:
        a = acc[nm]
        if not a["n"]:
            continue
        print(f"  {nm:>16} {a['n'] / 100:>7.1f} {a['asum'] / a['n']:>11.1f} {a['amax']:>10.0f} "
              f"{100 * a['rail'] / a['n']:>10.3f} {100 * a['near'] / a['n']:>9.3f} "
              f"{100 * a['slew'] / a['n']:>10.3f}")

    s, t0, t1 = EVENT
    d = load_seg(s)
    t = d["t"]
    fs = fs_run(t)
    ev = (t >= t0) & (t <= t1)
    print()
    print("=" * 104)
    print(f"T2b  INSIDE THE EVENT  (seg {s}, {t0}-{t1} s, v = "
          f"{d['cs_v'][ev].min():.1f}-{d['cs_v'][ev].max():.1f} m/s, {ev.sum() / fs:.1f} s)")
    print("=" * 104)
    c = np.asarray(d["sc_tq"], float)[ev]
    dc = np.abs(np.diff(c))
    print(f"  command   mean {c.mean():+8.1f}   |mean| {np.abs(c).mean():7.1f}   "
          f"max |c| {np.abs(c).max():7.0f}  = {100 * np.abs(c).max() / STEER_MAX:.1f}% of STEER_MAX")
    print(f"  RAIL DUTY at 4096:          {100 * np.mean(np.abs(c) >= 0.995 * STEER_MAX):.4f} %")
    print(f"  duty >= 90% of STEER_MAX:   {100 * np.mean(np.abs(c) >= 0.90 * STEER_MAX):.4f} %")
    print(f"  duty >= 50% of STEER_MAX:   {100 * np.mean(np.abs(c) >= 0.50 * STEER_MAX):.4f} %")
    print(f"  SLEW-CAP DUTY at {SLEW:.0f} ct/frame: {100 * np.mean(dc >= 0.98 * SLEW):.4f} %"
          f"   (max step {dc.max():.0f} ct/frame)")
    ac = c - c.mean()
    print(f"  crest factor |c|max/rms about the mean = {np.abs(ac).max() / np.sqrt(np.mean(ac ** 2)):.2f}"
          f"   [pure sinusoid 1.41, bang-bang 1.00, impulsive >3]")
    print(f"  sign reversals of the command: {int((np.diff(np.sign(c)) != 0).sum())} in "
          f"{ev.sum() / fs:.1f} s")

    print()
    print("=" * 104)
    print("T2c  BAND-BY-BAND: is the command's oscillation IN THE SAME BAND as the bar's?")
    print("=" * 104)
    chans = dict(bar_tq=d["tq"], angle=d["ang"], rate_fine=d["rate_f"] * RATE_FIX,
                 cmd_sendcan=d["sc_tq"], cmd_echo=d["e4tq"], op_torque_req=d["cc_req"],
                 desired_curv=d["ct_dcurv"], meas_curv=d["ct_curv"], imu_lat=d["imu_lat"])
    bands = [("1-4", 1, 4), ("6-10", 6, 10), ("18-24", 18, 24), ("24-32", 24, 32),
             ("32-45", 32, 45)]
    print(f"  {'channel':>14} " + " ".join(f"{b[0]:>10}" for b in bands) + "   [p99 band envelope]")
    for nm, x in chans.items():
        xv = np.asarray(x, float)[ev]
        if not np.isfinite(xv).all():
            xv = np.nan_to_num(xv)
        row = [band_env(xv, fs, lo, hi) for _, lo, hi in bands]
        sc = 1e6 if "curv" in nm else 1.0
        print(f"  {nm:>14} " + " ".join(f"{v * sc:>10.3f}" for v in row)
              + ("   [x1e6 1/m]" if "curv" in nm else ""))
    print("  -- ratio of each channel's 24-32 Hz envelope to its own 1-4 Hz envelope --")
    for nm, x in chans.items():
        xv = np.nan_to_num(np.asarray(x, float)[ev])
        lo4 = band_env(xv, fs, 1, 4)
        hi = band_env(xv, fs, 24, 32)
        print(f"  {nm:>14}  24-32 / 1-4 = {hi / lo4 if lo4 > 0 else np.nan:8.4f}")

    print()
    print("=" * 104)
    print("T2d  DEMANDED vs ACHIEVED ANGLE RATE  (operator: 'openpilot demands more rate than it gets')")
    print("=" * 104)
    print("  demanded column rate = d/dt[ desiredCurvature ] * v * steerRatio * wheelbase, deg/s")
    print(f"  [steerRatio {STEER_RATIO}, wheelbase {WHEELBASE} m -- nominal, so read the RATIO not the absolute]")
    print(f"  {'regime':>16} {'sec':>7} {'p50 dem':>9} {'p95 dem':>9} {'p50 ach':>9} "
          f"{'p95 ach':>9} {'p95 ach/dem':>12}")
    rows = {}
    for nm, lo, hi in bins + [("EVENT", -1, -1)]:
        dem, ach = [], []
        src = [(s, d)] if nm == "EVENT" else allsegs()
        for ss, dd in src:
            tt = dd["t"]
            ffs = fs_run(tt)
            m = (dd["cc_lat"] > 0.5)
            if nm == "EVENT":
                m = m & (tt >= t0) & (tt <= t1)
            else:
                m = m & (dd["cs_v"] >= lo) & (dd["cs_v"] < hi)
            if m.sum() < 50:
                continue
            dcv = np.nan_to_num(np.asarray(dd["ct_dcurv"], float))
            # low-pass at 3 Hz before differentiating: a raw derivative of a 20 Hz-noisy curvature
            # is dominated by that noise and would inflate the DEMAND by an order of magnitude
            X = np.fft.rfft(dcv - dcv.mean())
            fq = np.fft.rfftfreq(len(dcv), 1 / ffs)
            X[fq > 3.0] = 0
            dcs = np.fft.irfft(X, n=len(dcv)) + dcv.mean()
            ddem = np.gradient(dcs, tt) * dd["cs_v"] * STEER_RATIO * WHEELBASE * 180 / np.pi
            dem.append(np.abs(ddem[m]))
            ach.append(np.abs(np.asarray(dd["rate_f"], float)[m] * RATE_FIX))
        if not dem:
            continue
        D, A = np.concatenate(dem), np.concatenate(ach)
        rows[nm] = (len(D), np.percentile(D, 50), np.percentile(D, 95),
                    np.percentile(A, 50), np.percentile(A, 95))
        print(f"  {nm:>16} {len(D) / 100:>7.1f} {rows[nm][1]:>9.2f} {rows[nm][2]:>9.2f} "
              f"{rows[nm][3]:>9.2f} {rows[nm][4]:>9.2f} {rows[nm][4] / max(rows[nm][2], 1e-9):>12.2f}")
    print("  ach/dem >> 1 means the column moves FASTER than the plan asks -- the opposite of a")
    print("  rate-starved outer loop. ach/dem < 1 would support the operator's reading.")

    (CACHE / "v81loop_t2.json").write_text(json.dumps(
        dict(regime={k: v for k, v in acc.items()},
             event=dict(rail_duty=float(np.mean(np.abs(c) >= 0.995 * STEER_MAX)),
                        maxcmd=float(np.abs(c).max()),
                        slew_duty=float(np.mean(dc >= 0.98 * SLEW))),
             rate=rows), indent=0, default=float))


if __name__ == "__main__":
    main()
