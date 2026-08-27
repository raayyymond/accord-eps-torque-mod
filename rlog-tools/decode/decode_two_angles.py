#!/usr/bin/env python3
"""decode/decode_two_angles.py -- the EPS transmits TWO independent steering angles. Use them.

GROUND TRUTH (opendbc honda_accord_2018_can_generated.dbc), both messages TX'd BY THE EPS:

    BO_ 330 (0x14A) STEERING_SENSORS
      STEER_ANGLE        7|16@0-  (-0.1)  deg      bytes 0-1 BE signed
      STEER_ANGLE_RATE  23|16@0-  (-1.0)  deg/s    bytes 2-3 BE signed
      STEER_WHEEL_ANGLE 47|16@0-  (-0.1)  deg      bytes 5-6 BE signed   <-- SECOND ANGLE
    BO_ 399 (0x18F) STEER_STATUS
      STEER_TORQUE_SENSOR    7|16@0- (-1.0)        bytes 0-1 BE signed
      STEER_ANGLE_RATE      23|16@0- (-0.1) deg/s  bytes 2-3 BE signed   (10x finer copy)
      STEER_CONTROL_ACTIVE  35|1@0+                byte4 bit3
      STEER_STATUS          39|4@0+                byte4 bits 7:4

WHY THIS MATTERS
----------------------------------------------------------------------------------------------------
On a column EPS these two angles sit on OPPOSITE SIDES OF THE TORSION BAR. Their difference is the
bar twist, which is what the torque sensor measures. That gives two things this kit has never had:

  1. A TOPOLOGY CHECK.  twist = WHEEL_ANGLE - ANGLE  should track STEER_TORQUE_SENSOR. If it does,
     the two-sensor-at-different-locations picture is CONFIRMED FROM DATA, not inferred.

  2. A LOCALIZER FOR THE 20-25 Hz MODE.  If the mode is present in one angle and not the other, it
     localizes the resonance to one side of the bar:
        in WHEEL_ANGLE only  -> wheel/column inertia oscillating against the bar (upstream)
        in ANGLE only        -> motor/pinion/rack side (downstream)
        in BOTH, in phase    -> whole assembly moving; the bar is not the spring
        in TWIST (differential) -> the torsion bar IS the spring of the resonance

Item 2 is the discriminator ~50 builds of command-path levers could never reach.

CAVEAT, stated up front: CAN is 100 Hz, so 20-25 Hz is at 0.4-0.5 of Nyquist. Real, but a 21 Hz line
is indistinguishable from 79 Hz aliased. That ambiguity is inherited from every prior analysis here.

Usage:  python decode/decode_two_angles.py RLOG [RLOG ...]
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

FS = 100.0


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def collect(paths):
    """Return dict of parallel arrays, sampled on 0x14A arrivals with 0x18F held."""
    ang, wang, arate, t14 = [], [], [], []
    tq, frate, act, stat, t18 = [], [], [], [], []
    vego, engaged, tvego = [], [], []

    last18 = None
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:      # rlogs carry events whose union member is null
                continue
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x18F and len(d) >= 5:
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F)
                    elif m.address == 0x14A and len(d) >= 7:
                        ang.append(i16be(d, 0) * -0.1)
                        arate.append(i16be(d, 2) * -1.0)
                        wang.append(i16be(d, 5) * -0.1)
                        if last18 is None:
                            tq.append(np.nan); frate.append(np.nan)
                            act.append(0); stat.append(-1)
                        else:
                            tq.append(last18[0]); frate.append(last18[1])
                            act.append(last18[2]); stat.append(last18[3])
                        t14.append(evt.logMonoTime * 1e-9)
            elif w == "carState":
                vego.append(evt.carState.vEgo)
                engaged.append(bool(evt.carState.cruiseState.enabled))
                tvego.append(evt.logMonoTime * 1e-9)

    d = dict(t=np.array(t14), ang=np.array(ang), wang=np.array(wang),
             arate=np.array(arate), tq=np.array(tq), frate=np.array(frate),
             act=np.array(act), stat=np.array(stat))
    if tvego:
        d["v"] = np.interp(d["t"], np.array(tvego), np.array(vego))
        d["eng"] = np.interp(d["t"], np.array(tvego),
                             np.array(engaged, dtype=float)) > 0.5
    else:
        d["v"] = np.full_like(d["t"], np.nan)
        d["eng"] = np.zeros_like(d["t"], dtype=bool)
    return d


def bandpower(x, lo, hi, nfft=256):
    """Mean power in [lo,hi] Hz over NON-overlapping Hann segments. Returns (power, K)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < nfft:
        return np.nan, 0
    f = np.fft.rfftfreq(nfft, 1 / FS)
    sel = (f >= lo) & (f <= hi)
    win = np.hanning(nfft)
    acc, k = 0.0, 0
    for i in range(0, len(x) - nfft + 1, nfft):          # hop = nfft => independent
        seg = x[i:i + nfft]
        seg = seg - seg.mean()
        P = np.abs(np.fft.rfft(seg * win)) ** 2
        acc += P[sel].mean()
        k += 1
    return (acc / k if k else np.nan), k


def prominence(x, lo, hi, nfft=256, floor=(6.0, 40.0)):
    """Peak frequency in [lo,hi] and its PROMINENCE over the local broadband floor.

    Prominence = P(peak bin) / median(P over `floor` band, excluding [lo,hi]).  Because it is a
    RATIO within the same spectrum, it is invariant to the overall activity level -- which is what
    makes it usable when the conditioning variable is the measured channel itself. A resonance shows
    a high prominence at a stable frequency; mere steering activity raises the floor and the band
    together, leaving prominence flat.
    """
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < nfft:
        return np.nan, np.nan, 0
    f = np.fft.rfftfreq(nfft, 1 / FS)
    win = np.hanning(nfft)
    acc, k = np.zeros(len(f)), 0
    for i in range(0, len(x) - nfft + 1, nfft):
        seg = x[i:i + nfft]
        seg = seg - seg.mean()
        acc += np.abs(np.fft.rfft(seg * win)) ** 2
        k += 1
    if not k:
        return np.nan, np.nan, 0
    P = acc / k
    band = (f >= lo) & (f <= hi)
    ref = (f >= floor[0]) & (f <= floor[1]) & ~band
    if not band.any() or not ref.any():
        return np.nan, np.nan, k
    j = np.argmax(np.where(band, P, -np.inf))
    return f[j], P[j] / np.median(P[ref]), k


def report(tag, d):
    fin = np.isfinite(d["tq"])
    print(f"\n{'='*88}\n{tag}   n={len(d['t'])} frames  {d['t'][-1]-d['t'][0]:.1f}s  "
          f"vEgo {np.nanmin(d['v']):.2f}-{np.nanmax(d['v']):.2f} m/s")

    twist = d["wang"] - d["ang"]
    print(f"\n-- ranges --")
    for nm in ("ang", "wang", "arate", "tq"):
        a = d[nm][np.isfinite(d[nm])]
        print(f"   {nm:6s} min {a.min():9.2f}  max {a.max():9.2f}  rms {a.std():8.3f}")
    tw = twist[np.isfinite(twist)]
    print(f"   twist  min {tw.min():9.2f}  max {tw.max():9.2f}  rms {tw.std():8.3f}   "
          f"(= WHEEL_ANGLE - ANGLE)")

    # ---- TOPOLOGY CHECK -------------------------------------------------------------
    m = fin & np.isfinite(twist)
    if m.sum() > 100:
        r_tw = np.corrcoef(twist[m], d["tq"][m])[0, 1]
        r_aa = np.corrcoef(d["ang"][m], d["wang"][m])[0, 1]
        print(f"\n-- TOPOLOGY --")
        print(f"   corr(ANGLE, WHEEL_ANGLE)        = {r_aa:+.6f}   "
              f"(1.000 => same shaft / one sensor duplicated)")
        print(f"   corr(twist, STEER_TORQUE_SENSOR)= {r_tw:+.4f}   "
              f"(high => bar twist IS the torque signal)")
        nz = np.abs(twist[m]) > 1e-9
        print(f"   twist nonzero in {100*nz.mean():.1f}% of frames")
        if nz.sum() > 100:
            sl = np.polyfit(twist[m][nz], d["tq"][m][nz], 1)
            print(f"   torque = {sl[0]:.1f} * twist + {sl[1]:.1f}   "
                  f"[counts per degree of twist]")

    # ---- WHERE DOES THE 20-25 Hz MODE LIVE? -----------------------------------------
    print(f"\n-- 15-27 Hz BAND POWER, by channel and condition --")
    hands = np.abs(d["tq"]) > 200          # 'significant driver torque', provisional
    conds = [
        ("engaged, |tq|<=200 (hands-off)", d["eng"] & (np.abs(d["tq"]) <= 200)),
        ("engaged, |tq|> 200 (driver on)", d["eng"] & hands),
        ("disengaged",                     ~d["eng"]),
    ]
    chans = [("ANGLE", d["ang"]), ("WHEEL_ANGLE", d["wang"]),
             ("TWIST", twist), ("TORQUE", d["tq"]), ("RATE_fine", d["frate"])]
    hdr = "   {:32s}".format("condition") + "".join(f"{c[0]:>13s}" for c in chans) + "     K"
    print(hdr)
    for nm, sel in conds:
        if sel.sum() < 256:
            print(f"   {nm:32s}  (n={sel.sum()}, too few)")
            continue
        row, kk = "", 0
        for _, x in chans:
            p, k = bandpower(x[sel], 15, 27)
            kk = max(kk, k)
            row += f"{p:13.4g}" if np.isfinite(p) else f"{'--':>13s}"
        print(f"   {nm:32s}" + row + f"  {kk:4d}")

    # ---- DRIVER TORQUE THRESHOLD SWEEP ----------------------------------------------
    # 🛑 RAW BAND POWER IS CONFOUNDED HERE. The conditioning variable IS the measured channel, and
    # large driver torque means active steering, which lifts BROADBAND power in every channel. A
    # resonance is a NARROW PEAK, so use PROMINENCE = peak / local floor, which is invariant to the
    # overall activity level. Report both so the confound stays visible.
    print(f"\n-- does the mode die with DRIVER TORQUE? (engaged only) --")
    print(f"   {'|torque| bin':>14s} {'n':>6s} {'K':>3s} | "
          f"{'TQ raw':>10s} {'TQ peak':>8s} {'TQ prom':>8s} | "
          f"{'ANG peak':>8s} {'ANG prom':>8s} | {'v m/s':>6s}")
    edges = [0, 100, 200, 400, 800, 1600, 100000]
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = d["eng"] & (np.abs(d["tq"]) >= lo) & (np.abs(d["tq"]) < hi)
        if sel.sum() < 256:
            print(f"   {f'{lo}-{hi}':>14s} {sel.sum():6d}   (too few)")
            continue
        raw, k = bandpower(d["tq"][sel], 15, 27)
        ft, pt, _ = prominence(d["tq"][sel], 15, 27)
        fa, pa, _ = prominence(d["ang"][sel], 15, 27)
        print(f"   {f'{lo}-{hi}':>14s} {sel.sum():6d} {k:3d} | "
              f"{raw:10.3g} {ft:8.2f} {pt:8.2f} | {fa:8.2f} {pa:8.2f} | "
              f"{np.nanmean(d['v'][sel]):6.1f}")

    # ---- SPEED-CONTROLLED sweeps ----------------------------------------------------
    # The mode is documented as SHARP AT CREEP (23.24 Hz, 61x floor on route 24). At road speed the
    # peak wanders and prominence is 2-5, i.e. no resonance to test against. So sweep driver torque
    # in BOTH windows and let the prominence column say which operating point actually has a mode.
    for lbl, vlo, vhi in (("CREEP 0.3-3.0 m/s", 0.3, 3.0),
                          ("ROAD 14-19 m/s", 14.0, 19.0)):
        print(f"\n-- driver-torque sweep, engaged, {lbl} --")
        print(f"   {'|torque| bin':>14s} {'n':>6s} {'K':>3s} | "
              f"{'TQ peak':>8s} {'TQ prom':>8s} | {'ANG peak':>8s} {'ANG prom':>8s}")
        spd = d["eng"] & (d["v"] >= vlo) & (d["v"] <= vhi)
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = spd & (np.abs(d["tq"]) >= lo) & (np.abs(d["tq"]) < hi)
            if sel.sum() < 256:
                print(f"   {f'{lo}-{hi}':>14s} {sel.sum():6d}   (too few)")
                continue
            ft, pt, k = prominence(d["tq"][sel], 15, 27)
            fa, pa, _ = prominence(d["ang"][sel], 15, 27)
            print(f"   {f'{lo}-{hi}':>14s} {sel.sum():6d} {k:3d} | "
                  f"{ft:8.2f} {pt:8.2f} | {fa:8.2f} {pa:8.2f}")


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
