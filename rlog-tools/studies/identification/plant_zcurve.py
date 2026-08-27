#!/usr/bin/env python3
r"""THE |Z| CURVE, BIN BY BIN -- the decisive shape test for a PASSIVE wheel resonance.

WHAT THE PRECEDING FILES ESTABLISHED (all reproduced by `studies/identification/plant_recon.py` / `studies/identification/plant_impedance.py`)
  * `ang` (0x14A, LSB 0.1 deg) is QUANTISATION-LIMITED in band: 6-9 Hz band-RMS 0.0155-0.032 deg
    against a 0.0071 deg quantiser floor.  Differentiating it amplifies that noise as w^2 --
    |rate_f / d(ang)/dt| falls to 0.15 by 20 Hz, i.e. the differentiated angle is then ~7x pure
    noise.  🛑 **`dang` is NOT an admissible denominator above ~6 Hz.**
  * `rate_c` == 1.25 x `rate_f` at EVERY frequency and at identical phase.  🛑 **They are ONE
    channel, not two.**  Any "agreement between rate_f and rate_c" is vacuous.
  * arg(rate_f / d(ang)/dt) is LINEAR in f at -4.51 deg/Hz  =>  **12.5 ms of relative delay**,
    which independently CONFIRMS and quantifies the kit's "0x18F payload is one frame stale" trap.
    ⭐ `tq` and `rate_f` ride the SAME frame, so Z = tq/rate_f carries NO relative delay.  That is
    why this file uses `rate_f` and nothing else.

THE TEST
    Hands off:   Z(jw) = T_bar/Omega_w = -(J_w s + b_w)   =>   |Z|^2 = J_w^2 w^2 + b_w^2
  A PASSIVE upper column cannot put a PEAK in |Z|.  If |Z| is straight in w^2 through 8 Hz, the
  8.16 Hz line in `T_s` is not a passive wheel-on-torsion-bar resonance.  If |Z| peaks at ~8 Hz,
  it is.  This file prints the curve so the shape can be read rather than fitted.

⚠ SCALE CAVEAT, carried on every number below: `rate_f` and `rate_c` differ by exactly 1.25x, so
  at least one decode carries a wrong deg/s scale.  J_w scales linearly with that choice and f_n as
  its square root (1.12x).  The SHAPE conclusion is scale-invariant; the absolute J_w is not.
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
NFFT = 1024                 # 0.098 Hz resolution -- enough to see a Q=10 mode at 8 Hz (FWHM 0.8 Hz)
F = np.fft.rfftfreq(NFFT, 1 / FS)
HOLD_OFF, HOLD_ON = 300.0, 1200.0
K_BAR = 2296.0
ROUTE_LABEL = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x",
               "95": "V101 8x"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 110); print(s); print("=" * 110, flush=True)


def episodes(rt):
    eps = []
    for blk in L.all_blocks(rt):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        d = dict(tq=np.asarray(blk["tq"], float), r=np.asarray(blk["rate_f"], float),
                 v=np.asarray(blk.get("v_rear", blk["cs_v"]), float))
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s >= NFFT:
                eps.append(dict(lat=bool(lat[s]), **{k: v[s:e] for k, v in d.items()}))
    return eps


def wins(ep, hold):
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(ep["tq"]) - NFFT, NFFT // 2):
        y = ep["tq"][i:i + NFFT]
        if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
            continue
        if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
            continue
        x = ep["r"][i:i + NFFT]
        X = np.fft.rfft((x - x.mean()) * w)
        Y = np.fft.rfft((y - y.mean()) * w)
        out.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
    return out


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def curve(rt, lat, hold):
    eps = [e for e in episodes(rt) if e["lat"] == lat]
    per = [w for w in (wins(e, hold) for e in eps) if len(w) >= 1]
    if len(per) < 2:
        return None
    allw = [w for p in per for w in p]
    Sxx, Sxy, Syy = pool(allw)
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    Z1 = np.abs(Sxy) / np.maximum(Sxx, 1e-30)                # biased LOW by rate noise
    Z2 = Syy / np.maximum(np.abs(Sxy), 1e-30)                # biased HIGH by torque noise
    ph = np.angle(Syy / np.maximum(np.conj(Sxy), 1e-30) * 0 + Sxy / np.maximum(Sxx, 1e-30),
                  deg=True)
    return dict(per=per, Z1=Z1, Z2=Z2, coh=ch, ph=ph, nep=len(per), nwin=len(allw))


def band(x, lo, hi, wt=None):
    m = (F >= lo) & (F < hi)
    return float(np.average(x[m], weights=None if wt is None else wt[m]))


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85") if reg(r)]

    hdr("1.  |Z| = |tq / rate_f|  AND  |Z|/w  -- if the column is a pure inertia+damper, "
        "|Z|/w -> J_w = const")
    print("    1 Hz bins.  Z2 (torque-numerator) estimator; coh in brackets.  ENGAGED, HANDS-OFF.")
    print("    A PASSIVE PEAK would show as a bump in |Z| AND a bump in |Z|/w.  A pure inertia")
    print("    shows |Z|/w FLAT.  A pure damper shows |Z| flat and |Z|/w falling as 1/w.")
    print("\n    %-11s %s" % ("route", "".join("%13s" % ("%g-%g Hz" % (f, f + 1))
                                               for f in (4, 5, 6, 7, 8, 9, 10, 12, 14, 16))))
    OUT = {}
    for rt in routes:
        c = curve(rt, True, "off")
        if not c:
            continue
        cells = []
        for f0 in (4, 5, 6, 7, 8, 9, 10, 12, 14, 16):
            m = (F >= f0) & (F < f0 + 1)
            z = float(np.average(c["Z2"][m], weights=c["coh"][m] + 1e-9))
            zw = z / (2 * np.pi * (f0 + 0.5))
            cells.append("%13s" % ("%.0f|%.2f(%.2f)" % (z, zw, np.median(c["coh"][m]))))
        print("    %-11s %s" % (ROUTE_LABEL.get(rt, rt), "".join(cells)))
        OUT[rt] = dict(nep=c["nep"], nwin=c["nwin"])
    print("\n    cells read:  |Z| counts/(deg/s)  |  |Z|/w = apparent J in counts.s^2/deg  (coh)")

    hdr("2.  THE SAME CURVE, MANUAL (LKAS OFF) -- the fully passive car, no loop at all")
    print("    %-11s %s" % ("route", "".join("%13s" % ("%g-%g Hz" % (f, f + 1))
                                             for f in (4, 5, 6, 7, 8, 9, 10, 12, 14, 16))))
    for rt in routes:
        for hold in ("off", "on"):
            c = curve(rt, False, hold)
            if not c:
                continue
            cells = []
            for f0 in (4, 5, 6, 7, 8, 9, 10, 12, 14, 16):
                m = (F >= f0) & (F < f0 + 1)
                z = float(np.average(c["Z2"][m], weights=c["coh"][m] + 1e-9))
                cells.append("%13s" % ("%.0f|%.2f(%.2f)" % (z, z / (2 * np.pi * (f0 + .5)),
                                                           np.median(c["coh"][m]))))
            print("    %-11s %-4s %s" % (ROUTE_LABEL.get(rt, rt), hold, "".join(cells)))

    hdr("3.  PEAK TEST -- is there a LOCAL MAXIMUM of |Z|/w anywhere in 5-14 Hz?")
    print("    A passive inertia+damper column gives |Z|/w MONOTONE NON-INCREASING (it falls from")
    print("    b_w/w at low f to J_w at high f).  🛑 ANY interior peak is inconsistent with it.")
    print("\n    %-11s %-9s %-5s %8s %10s %10s %10s %10s"
          % ("route", "arm", "hold", "nep", "argmax f", "|Z|/w peak", "|Z|/w @14", "peak ratio"))
    peaks = {}
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                c = curve(rt, lat, hold)
                if not c:
                    continue
                m = (F >= 4.0) & (F <= 16.0)
                zw = c["Z2"][m] / (2 * np.pi * F[m])
                ff = F[m]
                # smooth over ~1 Hz to suppress single-bin noise
                k = max(int(1.0 / (F[1] - F[0])), 3)
                sm = np.convolve(zw, np.ones(k) / k, mode="same")
                sub = (ff >= 5) & (ff <= 14)
                if sub.sum() < 5 or np.median(c["coh"][m][sub]) < 0.10:
                    continue
                i = int(np.argmax(sm[sub]))
                fpk = float(ff[sub][i])
                ref = float(np.median(sm[(ff >= 13.5) & (ff <= 16)]))
                print("    %-11s %-9s %-5s %8d %10.2f %10.3f %10.3f %10.2f"
                      % (ROUTE_LABEL.get(rt, rt), latl, hold, c["nep"], fpk,
                         float(sm[sub][i]), ref, float(sm[sub][i]) / max(ref, 1e-9)))
                peaks["%s|%s|%s" % (rt, latl, hold)] = dict(f=fpk, pk=float(sm[sub][i]),
                                                            ref=ref, nep=c["nep"])
    (HERE / "_scratch/out/_plant_zcurve.json").write_text(json.dumps(dict(peaks=peaks, meta=OUT), indent=1,
                                                        default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_plant_zcurve.json"))


if __name__ == "__main__":
    main()
