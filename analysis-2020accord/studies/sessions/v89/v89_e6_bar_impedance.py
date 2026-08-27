#!/usr/bin/env python3
r"""T3, REDONE ON A CLEAN CHANNEL -- what IMPEDANCE does the column torque present, hands-off?

🛑 WHY `v89_e4`'s T3 NEEDED REDOING, and both reasons are instrument defects, not results:
  1. It differentiated `ang` (0x14A, **0.1 deg/LSB**) TWICE.  The 6-9 Hz angle rms is 0.015-0.025
     deg against a 0.0071 deg quantisation floor -- only 2-3.5x -- so every row above ~6 Hz was
     quantisation-limited, and quantisation noise in the DENOMINATOR biases |T/alpha| DOWN, which is
     exactly the falling trend that file reported.
  2. `ang` and `tq` come from DIFFERENT CAN messages (0x14A and 0x18F), so their relative phase
     carries a ZOH skew of up to one 100 Hz period = 28 deg at 7.8 Hz.

  ⇒ This file uses **`rate_f` = STEER_ANGLE_RATE from 0x18F**, which is 0.1 deg/s per LSB and
  arrives in **the same CAN frame as the torque**, so there is no cross-message skew at all, and
  alpha needs only ONE differentiation (done spectrally, as j*omega).

THE THREE CANONICAL IMPEDANCES and what each predicts for phase(T_bar, omega):
       INERTIA   T = J*alpha       -> +90 deg   |T/omega| RISES linearly with f
       DAMPER    T = C*omega       ->   0 deg   |T/omega| FLAT
       SPRING    T = K*theta       -> -90 deg   |T/omega| FALLS as 1/f
       NEGATIVE DAMPING T = -C*omega -> 180 deg (this is what a self-exciting loop looks like)

HANDS-OFF ONLY (`cs_press` == 0) is the decisive arm: with the driver's arms off the rim, the
torsion bar can only be carrying the upper column's own inertia, friction and whatever the assist
loop is feeding back into it.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))

import _r31_common as C31        # noqa: E402
import _r4f_lib as R4F           # noqa: E402
from v89_e4_inertia import ARMS, NFFT, HOP, fs_of, CT_PER_NM  # noqa: E402

R4F.install_fs()
RNG = np.random.default_rng(89_6666)
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e6_bar_impedance.json"
FB = [(2, 4), (4, 6), (6, 9), (9, 12), (12, 16), (16, 22), (26, 31), (32, 38)]
Q_LSB = 0.1          # deg/s per LSB on 0x18F STEER_ANGLE_RATE
OUT = {}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116, flush=True)


def run(name, handsoff=True):
    cache, pfx, segs = ARMS[name]
    acc = {f"{lo}-{hi}": [] for lo, hi in FB}
    phs = {f"{lo}-{hi}": [] for lo, hi in FB}
    wrm = {f"{lo}-{hi}": [] for lo, hi in FB}
    coh = {f"{lo}-{hi}": [] for lo, hi in FB}
    for s in segs:
        if not (cache / f"{pfx}{s}.npz").exists():
            continue
        d = C31.load(s, cache, pfx)
        fs = fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        pr = np.asarray(d.get("cs_press", np.zeros_like(lat, float)), float)
        w = np.radians(np.asarray(d["rate_f"], float))      # rad/s, 0x18F, same frame as tq
        tq = np.asarray(d["tq"], float)                     # counts, 0x18F
        for a, b in C31.runs_of(lat, d["t"], NFFT):
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(a + i, a + i + NFFT)
                if handsoff and np.mean(pr[sl] > 0.5) > 0.02:
                    continue
                if not handsoff and np.mean(pr[sl] > 0.5) < 0.5:
                    continue
                han = np.hanning(NFFT)
                W = np.fft.rfft((w[sl] - w[sl].mean()) * han)
                TQ = np.fft.rfft((tq[sl] - tq[sl].mean()) * han)
                f = np.fft.rfftfreq(NFFT, 1 / fs)
                for lo, hi in FB:
                    m = (f >= lo) & (f <= hi)
                    pw = np.sum(np.abs(W[m]) ** 2)
                    pt = np.sum(np.abs(TQ[m]) ** 2)
                    if pw <= 0 or pt <= 0:
                        continue
                    k = f"{lo}-{hi}"
                    S = np.sum(TQ[m] * np.conj(W[m]))
                    acc[k].append(np.sqrt(pt / pw))
                    phs[k].append(np.angle(S))
                    coh[k].append(np.abs(S) ** 2 / (pw * pt))
                    wrm[k].append(np.degrees(np.sqrt(pw)) / (NFFT / 2))
    return acc, phs, coh, wrm


def report(name, acc, phs, coh, wrm, tag):
    print(f"\n    {name}  [{tag}]")
    print(f"    {'band Hz':>8s} {'|T/omega| ct.s/rad':>19s} {'N.m.s/rad*':>11s} "
          f"{'phase(T,omega)':>15s} {'|coh|^2':>8s} {'rate rms deg/s':>15s} {'x floor':>8s} "
          f"{'n':>6s}")
    row = {}
    for lo, hi in FB:
        k = f"{lo}-{hi}"
        if len(acc[k]) < 20:
            continue
        Z = float(np.median(acc[k]))
        ph = float(np.degrees(np.angle(np.mean(np.exp(1j * np.array(phs[k]))))))
        cq = float(np.median(coh[k]))
        wr = float(np.median(wrm[k]))
        floor = Q_LSB / np.sqrt(12) * np.sqrt((hi - lo) / 50.0)
        print(f"    {k:>8s} {Z:19.1f} {Z/CT_PER_NM:11.4f} {ph:14.1f}° {cq:8.3f} "
              f"{wr:15.4f} {wr/floor:8.1f} {len(acc[k]):6d}")
        row[k] = dict(Z_ct_s_per_rad=Z, Z_Nms_per_rad=Z / CT_PER_NM, phase_deg=ph, coh2=cq,
                      rate_rms_dps=wr, x_floor=wr / floor, n=len(acc[k]))
    return row


def polarity_anchor():
    """🛑 THE 180-DEGREE CONVENTION, SETTLED BEFORE ANY PHASE IS READ.

    Every impedance verdict here turns on whether positive `tq` means "torque driving the wheel in
    the +angle direction" or its reaction.  A 180 deg error turns an inertia into a spring.
    THE ANCHOR: in the MANUAL arm with the driver working the wheel, the driver is doing POSITIVE
    WORK on the column, so phase(T_bar, omega) MUST be ~0 deg at low frequency.  ~180 deg would
    mean the whole table is flipped.
    ⊕ Second, independent check: corr(d(ang)/dt, rate_f) must be POSITIVE, i.e. the 0x14A angle and
    the 0x18F rate share a polarity, so the rate channel can stand in for the angle channel.
    """
    hdr("POLARITY ANCHOR -- settle the 180 deg convention BEFORE reading any phase")
    FBP = [(0.3, 1.0), (1.0, 2.0), (2.0, 4.0), (6.0, 9.0)]
    OUT["polarity"] = {}
    for name in ARMS:
        cache, pfx, segs = ARMS[name]
        res = {f"{lo}-{hi}": [[], []] for lo, hi in FBP}
        cc = []
        nw = ntot = 0
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            d = C31.load(s, cache, pfx)
            fs = fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            w = np.radians(np.asarray(d["rate_f"], float))
            tq = np.asarray(d["tq"], float)
            da = np.gradient(np.asarray(d["ang"], float)) * fs
            m0 = np.isfinite(da) & np.isfinite(d["rate_f"])
            cc.append(float(np.corrcoef(da[m0], np.asarray(d["rate_f"], float)[m0])[0, 1]))
            for a, b in C31.runs_of(~lat, d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP // 2):
                    sl = slice(a + i, a + i + NFFT)
                    ntot += 1
                    if np.median(np.abs(tq[sl])) < 1200 or np.std(np.degrees(w[sl])) < 2.0:
                        continue
                    nw += 1
                    han = np.hanning(NFFT)
                    f = np.fft.rfftfreq(NFFT, 1 / fs)
                    W = np.fft.rfft((w[sl] - w[sl].mean()) * han)
                    TQ = np.fft.rfft((tq[sl] - tq[sl].mean()) * han)
                    for lo, hi in FBP:
                        m = (f >= lo) & (f <= hi)
                        pw, pt = np.sum(np.abs(W[m]) ** 2), np.sum(np.abs(TQ[m]) ** 2)
                        if pw <= 0 or pt <= 0:
                            continue
                        S = np.sum(TQ[m] * np.conj(W[m]))
                        res[f"{lo}-{hi}"][0].append(np.angle(S))
                        res[f"{lo}-{hi}"][1].append(np.abs(S) ** 2 / (pw * pt))
        print(f"\n    {name}: corr(d(ang)/dt, rate_f) = {np.mean(cc):+.4f}   "
              f"{nw}/{ntot} manual windows with |tq|>1200 ct and >2 deg/s rms")
        for lo, hi in FBP:
            k = f"{lo}-{hi}"
            ph, co = res[k]
            if len(ph) < 15:
                print(f"      {k:>9s}  n={len(ph)} -- too few")
                continue
            p = float(np.degrees(np.angle(np.mean(np.exp(1j * np.array(ph))))))
            print(f"      {k:>9s}  phase(T,omega) {p:+8.1f}°   coh2 {np.median(co):.3f}   "
                  f"n={len(ph)}")
            OUT["polarity"][f"{name}/{k}"] = dict(phase=p, coh2=float(np.median(co)), n=len(ph))
        OUT["polarity"][f"{name}/corr_dang_ratef"] = float(np.mean(cc))


def manual_control():
    """🛑 THE CONTROL THAT DOES NOT EXIST ON THESE ROUTES, recorded as a null of EXPOSURE.

    The impedance above is measured ENGAGED.  Its control is the same measurement MANUAL and
    hands-off while moving -- and nobody drives that way: 0-6 qualifying windows per route.
    ⇒ these logs CANNOT separate "the EPS loop is anti-damped" from "the column is anti-damped".
    """
    hdr("CONTROL -- the SAME impedance MANUAL + hands-off + moving.  Exposure check.")
    for name in ARMS:
        cache, pfx, segs = ARMS[name]
        n = 0
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            d = C31.load(s, cache, pfx)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            pr = np.asarray(d.get("cs_press", np.zeros_like(lat, float)), float)
            v = np.abs(np.asarray(d["cs_v"], float))
            for a, b in C31.runs_of(~lat, d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    if np.mean(pr[sl] > 0.5) <= 0.02 and np.mean(v[sl]) >= 0.5:
                        n += 1
        print(f"    {name}: {n} manual hands-off moving windows "
              f"{'-- UNINTERPRETABLE, no control exists' if n < 20 else ''}")
        OUT.setdefault("manual_control_exposure", {})[name] = n


if __name__ == "__main__":
    polarity_anchor()
    manual_control()
    hdr("THE COLUMN'S APPARENT IMPEDANCE, T_bar / omega_wheel, ENGAGED, HANDS-OFF\n"
        "    INERTIA +90 deg (|Z| rises with f) · DAMPER 0 deg (flat) · SPRING -90 deg (falls)\n"
        "    NEGATIVE DAMPING 180 deg -- the signature of a self-exciting loop\n"
        "    * N.m.s/rad uses the 1200 ct/N.m anchor: BELIEF, +-3x.")
    for name in ARMS:
        for tag, ho in (("HANDS-OFF", True), ("hands-on", False)):
            OUT[f"{name}/{tag}"] = report(name, *run(name, ho), tag)
    print("\n    🛑 `rate_f` is 0.1 deg/s per LSB; the 'x floor' column is the measured band rms")
    print("       divided by the white-quantisation floor for that band.  Rows under ~3x are NOISE.")
    print("    🛑 The INERTIA prediction is unambiguous and scale-free: |T/omega| must RISE")
    print("       LINEARLY with frequency and the phase must sit at +90 deg.")
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
