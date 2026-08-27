#!/usr/bin/env python3
r"""RECONNAISSANCE for the passive-plant fit -- can the channels even support it?

Before fitting `T_bar/theta_w = -(J_w s^2 + b_w s)` on real logs, three things have to be checked,
because each of them can silently invalidate the fit:

  Q1 QUANTISATION.  `ang` is 0x14A STEER_ANGLE at LSB 0.1 deg.  The 2026-08-20 analysis measured the
     engaged 6-9 Hz band-RMS of `ang` at **0.089 deg -- BELOW ONE LSB**.  If the angle channel's
     in-band content is at the quantisation floor the fit is measuring the ADC, not the car.
  Q2 RELATIVE DELAY.  `0x18F` is one frame (10 ms) stale; 10 ms = 28.8 deg of phase at 8 Hz, which
     lands directly on the `b_w` (imaginary) part.  The delay must be MEASURED, not assumed.
  Q3 EXPOSURE.  How much genuinely hands-off data exists, in each of LKAS-on and LKAS-off?

Nothing here fits anything.  It prints the numbers that decide whether the fit is worth running.
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
ANG_LSB = 0.1          # deg, 0x14A STEER_ANGLE
TQ_LSB = 1.0           # count, 0x18F STEER_TORQUE_SENSOR
HOLD_OFF = 300.0       # `studies/ratchet/v97_return_to_centre.py`'s HANDS-OFF criterion: p90|tq| < 300
NFFT = 512

ROUTE_LABEL = {"97": "V9b STOCK", "9e": "V103 (on the car)", "96": "V102", "85": "V100 4x",
               "95": "V101 8x", "73": "V88", "71": "V87"}


def reg(route, label):
    if route not in L.ROUTES:
        L.ROUTES[route] = L._mk(route, label, gain=0, clamp=0, leverB=False, idcode=0, bits=label)
    return bool(L.ROUTES[route]["segs"])


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def bandrms(x, lo, hi, nfft=NFFT):
    w = np.hanning(len(x))
    return L.bandrms(x, FS, lo, hi, w)


def q1_quantisation(routes):
    hdr("Q1  QUANTISATION -- is the angle channel's in-band content above its own LSB floor?")
    print("    `ang` LSB = %.3f deg -> uniform-quantiser noise RMS = LSB/sqrt(12) = %.4f deg,"
          % (ANG_LSB, ANG_LSB / np.sqrt(12)))
    print("    spread white over 0-%.0f Hz.  In a band of width W the floor is that x sqrt(W/%.0f)."
          % (FS / 2, FS / 2))
    print("\n    %-22s %-10s %10s %10s %10s %10s %10s" %
          ("route", "arm", "|ang|6-9", "q-floor", "SNR_amp", "|tq|6-9", "n_win"))
    out = {}
    for rt in routes:
        for arm in ("engaged", "manual"):
            A, T, n = [], [], 0
            for blk in L.all_blocks(rt):
                lat = blk["cc_lat"] > 0.5
                a, tq = np.asarray(blk["ang"], float), np.asarray(blk["tq"], float)
                for i in range(0, len(a) - NFFT, NFFT // 2):
                    m = lat[i:i + NFFT]
                    if arm == "engaged" and m.mean() < 0.98:
                        continue
                    if arm == "manual" and m.mean() > 0.02:
                        continue
                    A.append(bandrms(a[i:i + NFFT], 6, 9))
                    T.append(bandrms(tq[i:i + NFFT], 6, 9))
                    n += 1
            if not n:
                continue
            qf = ANG_LSB / np.sqrt(12) * np.sqrt(3.0 / (FS / 2))
            print("    %-22s %-10s %10.4f %10.4f %10.2f %10.1f %10d"
                  % (ROUTE_LABEL.get(rt, rt), arm, np.median(A), qf, np.median(A) / qf,
                     np.median(T), n))
            out.setdefault(rt, {})[arm] = dict(ang=float(np.median(A)), qfloor=float(qf),
                                               snr=float(np.median(A) / qf),
                                               tq=float(np.median(T)), n=n)
    print("\n    ⚠ SNR_amp is an AMPLITUDE ratio.  Errors-in-variables bias on an H1 estimator goes")
    print("      like 1/(1+1/SNR^2); at SNR 10 that is a 1 % underestimate, at SNR 3 a 10 % one.")
    return out


def q2_delay(routes):
    hdr("Q2  RELATIVE DELAY between `tq` (0x18F) and `ang` (0x14A) -- MEASURED, not assumed")
    print("    Method: cross-spectrum phase of (ang -> tq) over 10-24 Hz, where the passive")
    print("    column should have arg(T/theta) -> 0 (a pure inertia).  Any residual slope is delay.")
    print("    A 10 ms stale frame = -3.6 deg/Hz.  Reported as the LS slope of unwrapped phase.")
    print("\n    %-22s %-10s %12s %12s %10s %8s" %
          ("route", "arm", "slope deg/Hz", "delay ms", "coh2 med", "n_win"))
    out = {}
    for rt in routes:
        for arm in ("engaged", "manual"):
            Sxy, Sxx, Syy, n = 0, 0, 0, 0
            for blk in L.all_blocks(rt):
                lat = blk["cc_lat"] > 0.5
                a, tq = np.asarray(blk["ang"], float), np.asarray(blk["tq"], float)
                w = np.hanning(NFFT)
                for i in range(0, len(a) - NFFT, NFFT // 2):
                    m = lat[i:i + NFFT]
                    if arm == "engaged" and m.mean() < 0.98:
                        continue
                    if arm == "manual" and m.mean() > 0.02:
                        continue
                    aa = a[i:i + NFFT]; tt = tq[i:i + NFFT]
                    aa = (aa - aa.mean()) * w; tt = (tt - tt.mean()) * w
                    A_, T_ = np.fft.rfft(aa), np.fft.rfft(tt)
                    Sxy = Sxy + np.conj(A_) * T_
                    Sxx = Sxx + np.abs(A_) ** 2
                    Syy = Syy + np.abs(T_) ** 2
                    n += 1
            if not n:
                continue
            f = np.fft.rfftfreq(NFFT, 1 / FS)
            coh = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
            m = (f >= 10) & (f <= 24) & (coh > 0.2)
            if m.sum() < 6:
                print("    %-22s %-10s %12s (coh too low, %d usable bins)"
                      % (ROUTE_LABEL.get(rt, rt), arm, "--", int(m.sum())))
                continue
            ph = np.unwrap(np.angle(Sxy[m])) * 180 / np.pi
            sl, _ = np.polyfit(f[m], ph, 1)
            print("    %-22s %-10s %12.2f %12.2f %10.3f %8d"
                  % (ROUTE_LABEL.get(rt, rt), arm, sl, -sl / 360.0 * 1000.0,
                     float(np.median(coh[m])), n))
            out.setdefault(rt, {})[arm] = dict(slope_deg_hz=float(sl),
                                               delay_ms=float(-sl / 360.0 * 1000.0),
                                               coh=float(np.median(coh[m])), n=n)
    return out


def q3_exposure(routes):
    hdr("Q3  EXPOSURE -- how much HANDS-OFF data exists, split by LKAS state?")
    print("    hands-off = window p90|tq| < %.0f counts (`studies/ratchet/v97_return_to_centre.py`'s HOLD_OFF)."
          % HOLD_OFF)
    print("    🛑 NOT `steeringPressed` -- that mask is band-correlated and excludes the symptom")
    print("       regime (`reference-accord-steeringpressed-mask-excludes-the-symptom-regime`).")
    print("\n    %-22s %12s %12s %12s %12s %10s" %
          ("route", "eng+off s", "eng+on s", "man+off s", "man+on s", "total s"))
    out = {}
    for rt in routes:
        cells = dict(eo=0, en=0, mo=0, mn=0)
        tot = 0.0
        for blk in L.all_blocks(rt):
            lat = blk["cc_lat"] > 0.5
            tq = np.abs(np.asarray(blk["tq"], float))
            tot += len(tq) / FS
            for i in range(0, len(tq) - NFFT, NFFT):
                m = lat[i:i + NFFT]
                off = np.percentile(tq[i:i + NFFT], 90) < HOLD_OFF
                if m.mean() >= 0.98:
                    cells["eo" if off else "en"] += NFFT / FS
                elif m.mean() <= 0.02:
                    cells["mo" if off else "mn"] += NFFT / FS
        print("    %-22s %12.1f %12.1f %12.1f %12.1f %10.1f"
              % (ROUTE_LABEL.get(rt, rt), cells["eo"], cells["en"], cells["mo"], cells["mn"], tot))
        out[rt] = cells
    return out


def q4_edges(routes):
    hdr("Q4  RING-DOWN EDGE CENSUS -- how many usable latActive falling edges, and lane changes?")
    print("    %-22s %10s %10s %10s %12s" %
          ("route", "lat-fall", "clean(3s)", "lchg", "blinker on"))
    out = {}
    for rt in routes:
        nf = nc = nl = nb = 0
        for blk in L.all_blocks(rt):
            lat = blk["cc_lat"] > 0.5
            g = int(3 * FS)
            idx = np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1
            nf += len(idx)
            for i in idx:
                if i - g >= 0 and i + g < len(lat) and lat[i - g:i].mean() > 0.95 \
                        and lat[i:i + g].mean() < 0.05:
                    nc += 1
            if "cs_lchg" in blk:
                lc = np.asarray(blk["cs_lchg"], float) > 0.5
                nl += int(np.count_nonzero(np.diff(lc.astype(int)) > 0))
            if "cs_lblink" in blk:
                bl = np.asarray(blk["cs_lblink"], float) > 0.5
                nb += int(np.count_nonzero(np.diff(bl.astype(int)) > 0))
        print("    %-22s %10d %10d %10d %12d" % (ROUTE_LABEL.get(rt, rt), nf, nc, nl, nb))
        out[rt] = dict(fall=nf, clean=nc, lchg=nl, blink=nb)
    return out


def main():
    routes = [r for r in ("97", "9e", "96", "85", "95", "73") if reg(r, ROUTE_LABEL.get(r, r))]
    print("routes available: " + ", ".join("0x%s=%s" % (r, ROUTE_LABEL.get(r, r)) for r in routes))
    o = dict(q1=q1_quantisation(routes), q2=q2_delay(routes),
             q3=q3_exposure(routes), q4=q4_edges(routes))
    p = HERE / "_scratch/out/_plant_recon.json"
    p.write_text(json.dumps(o, indent=1, default=float))
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
