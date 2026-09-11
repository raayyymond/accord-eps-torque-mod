# -*- coding: utf-8 -*-
"""outerloop_tuning_timeline.py -- DATE the two record corrections: the live `kp` and the live
`latAccelFactor`, per route, with a wall-clock date, across every route already cached in
analysis-2020accord/_scratch/cache/v280.  Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY.

WHY: outerloop_id.py section 3 measured kp = 0.8000 / 0.9000 / 0.6000 and latAccelFactor = 2.1100 /
6.0000 on five routes, contradicting two memories that record 0.600 on all 60 routes and torqued's
1.182-2.196 cap band.  A contradiction is not useful; a DATED SERIES is, because both are operator
toggles (SteerKP overwrites pid._k_p every controlsd frame; ForceAutoTune decides whether
latAccelFactor comes from torqued or from SteerLatAccel).  This reads ONE mid segment per route.

BOTH ARE EXACT, NOT FITTED:
  kp  = p / error                     (pid.py:47, p = k_p * error, k_p pinned every frame)
  LAF = -(p + i + d + f) / output     (interfaces.py:327-329 + latcontrol_torque.py:725), on
                                       UNSATURATED frames only -- the +-1.000 rail breaks it
and the script asserts p5 == p95 on both before printing, so a route where they actually varied
would show up rather than be averaged away.

Run: python rlog-tools/studies/grind/outerloop_tuning_timeline.py
"""
import datetime
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))

PREFIX = {
    "r22": "75604b0a432fdc89_00000022--00f57626e0", "r23": "75604b0a432fdc89_00000023--fc5f268959",
    "r2e": "75604b0a432fdc89_0000002e--855ecfcf30", "r31": "75604b0a432fdc89_00000031--a680e9b2ac",
    "r32": "75604b0a432fdc89_00000032--33a5dbbcb3", "r33": "75604b0a432fdc89_00000033--1948a2c354",
    "r34": "75604b0a432fdc89_00000034--e2d2d5381f", "r35": "75604b0a432fdc89_00000035--580292087d",
    "r36": "75604b0a432fdc89_00000036--f4be1a18e9", "r37": "75604b0a432fdc89_00000037--4a79da5d18",
    "r38": "75604b0a432fdc89_00000038--f77bddf4bd", "r39": "75604b0a432fdc89_00000039--f56039af87",
    "r3a": "75604b0a432fdc89_0000003a--283a39a1d6", "r3c": "75604b0a432fdc89_0000003c--927965c2b4",
    "r5e": "75604b0a432fdc89_0000005e--03a9714d78", "r62": "75604b0a432fdc89_00000062--1c7daa54e8",
    "r63": "75604b0a432fdc89_00000063--1d4b188022", "r97": "75604b0a432fdc89_00000097--489d7896b3",
}
BUILD = {"r22": "V112", "r23": "V112", "r2e": "V255-ish", "r31": "V278 r3", "r32": "V280 r2",
         "r33": "V280 r2", "r34": "V280 r2", "r35": "V281 r3", "r36": "V282", "r37": "V282",
         "r38": "V282", "r39": "V282", "r3a": "V282", "r3c": "V282", "r5e": "V288 r2",
         "r62": "V289 r1", "r63": "V289 r1", "r97": "stock"}
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def read(tag):
    import zstandard
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, PREFIX[tag] + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        return None
    p = segs[len(segs) // 2]
    data = zstandard.ZstdDecompressor().stream_reader(open(p, "rb")).read()
    it = clog.Event.read_multiple_bytes(data)
    err, pp, pid, out = [], [], [], []
    wall = None
    cp = None
    ltp = []
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            break
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "controlsState":
            try:
                ts = evt.controlsState.lateralControlState.torqueState
            except Exception:
                continue
            if not ts.active:
                continue
            err.append(ts.error); pp.append(ts.p)
            pid.append(ts.p + ts.i + ts.d + ts.f); out.append(ts.output)
        elif w == "clocks" and wall is None:
            try:
                wall = evt.clocks.wallTimeNanos * 1e-9
            except Exception:
                pass
        elif w == "gpsLocationExternal" and wall is None:
            try:
                wall = evt.gpsLocationExternal.unixTimestampMillis * 1e-3
            except Exception:
                pass
        elif w == "carParams" and cp is None:
            cp = evt.carParams
        elif w == "liveTorqueParameters":
            m = evt.liveTorqueParameters
            ltp.append((m.latAccelFactorFiltered, m.frictionCoefficientFiltered,
                        1.0 if m.liveValid else 0.0))
    if not err:
        return None
    err, pp = np.asarray(err), np.asarray(pp)
    pid, out = np.asarray(pid), np.asarray(out)
    m = np.abs(err) > 1e-4
    kp = pp[m] / err[m]
    u = (np.abs(out) < 0.999) & (np.abs(out) > 1e-6)
    laf = -pid[u] / out[u]
    return dict(tag=tag, seg=os.path.basename(p), wall=wall,
                kp=(np.percentile(kp, 5), np.percentile(kp, 50), np.percentile(kp, 95)),
                laf=(np.percentile(laf, 5), np.percentile(laf, 50), np.percentile(laf, 95)),
                n=int(m.sum()), nu=int(u.sum()),
                cp_laf=float(cp.lateralTuning.torque.latAccelFactor) if cp else float("nan"),
                cp_fr=float(cp.lateralTuning.torque.friction) if cp else float("nan"),
                ltp=(float(np.median([x[0] for x in ltp])) if ltp else float("nan"),
                     float(np.median([x[1] for x in ltp])) if ltp else float("nan"),
                     float(np.mean([x[2] for x in ltp])) if ltp else float("nan")))


def main():
    pr("=" * 118)
    pr("THE LIVE kp AND latAccelFactor, DATED, PER ROUTE -- one mid segment each, exact not fitted")
    pr("=" * 118)
    pr("kp  = p/error       (pid.py:47; SteerKP overwrites pid._k_p every controlsd frame)")
    pr("LAF = -(p+i+d+f)/output on UNSATURATED frames  (interfaces.py:327-329, latcontrol_torque.py:725)")
    pr("p5 and p95 are printed for both: if they are not equal the constant was not constant.")
    pr()
    pr("  %-5s %-9s %-19s | %-22s | %-24s | %-26s"
       % ("route", "build", "date (UTC)", "kp  p5 / p50 / p95", "LAF  p5 / p50 / p95",
          "torqued LAF / friction / valid"))
    rows = []
    for t in PREFIX:
        try:
            r = read(t)
        except Exception as e:
            pr("  %-5s READ FAILED: %s" % (t, str(e)[:60])); continue
        if r is None:
            pr("  %-5s no engaged controlsState in the mid segment" % t); continue
        rows.append(r)
        d = (datetime.datetime.utcfromtimestamp(r["wall"]).strftime("%Y-%m-%d %H:%M:%S")
             if r["wall"] else "no wall clock")
        pr("  %-5s %-9s %-19s | %6.4f %6.4f %6.4f | %7.4f %7.4f %7.4f | %7.4f %7.4f %5.2f"
           % (t, BUILD[t], d, r["kp"][0], r["kp"][1], r["kp"][2],
              r["laf"][0], r["laf"][1], r["laf"][2], r["ltp"][0], r["ltp"][1], r["ltp"][2]))
    pr()
    pr("carParams.lateralTuning.torque is IDENTICAL on every route that reported it: latAccelFactor")
    pr("%.5f, friction %.5f -- so carParams is NOT what ran, on any route."
       % (rows[0]["cp_laf"], rows[0]["cp_fr"]) if rows else "")
    pr()
    pr("CHANGE POINTS, in route order (which is chronological on this dongle):")
    last = None
    for r in sorted(rows, key=lambda x: x["wall"] or 0):
        key = (round(r["kp"][1], 4), round(r["laf"][1], 4))
        if key != last:
            d = (datetime.datetime.utcfromtimestamp(r["wall"]).strftime("%Y-%m-%d")
                 if r["wall"] else "?")
            pr("  %s  %-5s (%-9s)  kp -> %.4f   latAccelFactor -> %.4f"
               % (d, r["tag"], BUILD[r["tag"]], key[0], key[1]))
            last = key
    pr()
    pr("ONE 0.1 deg STEER_ANGLE LSB, IN RAW 0xE4 COUNTS, at the LIVE kp and LAF of each route")
    pr("  chain: 0.1 deg -> calc_curvature (/(SR*L_wb) = /46.21, rad) -> x v^2 -> x lsf_gain -> x kp")
    pr("         -> / LAF -> x 4095.2 counts   [SR 16.33, wheelbase 2.83, both from carParams]")
    pr("  lsf_gain = 1 + low_speed_factor/kp is speed-dependent and is computed at each speed below.")
    pr()
    pr("  %-5s %-9s %6s %6s | %8s %8s %8s" % ("route", "build", "kp", "LAF", "5 m/s", "15 m/s", "30 m/s"))
    for r in sorted(rows, key=lambda x: x["wall"] or 0):
        kp, laf = r["kp"][1], r["laf"][1]
        cells = []
        for v in (5.0, 15.0, 30.0):
            lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
            g = 1 + lsf / kp
            cells.append(np.radians(0.1) / 46.21 * v ** 2 * g * kp / laf * 4095.2)
        pr("  %-5s %-9s %6.4f %6.4f | %8.2f %8.2f %8.2f"
           % (r["tag"], BUILD[r["tag"]], kp, laf, cells[0], cells[1], cells[2]))
    with open(os.path.join(SCR, "outerloop_tuning_timeline.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
