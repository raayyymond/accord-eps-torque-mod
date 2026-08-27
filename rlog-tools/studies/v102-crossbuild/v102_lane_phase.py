#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_lane_phase.py -- cross-spectral phase arg(csd(lane, torque)) at 20-23 Hz, for `pole-hunt`.

WHAT WAS ASKED:  arg(csd(gp-0x6b26 or gp-0x6bbe, gp-0x4f60/STEER_TORQUE_SENSOR)) at 20-23 Hz.

WHAT ROUTE 96 CAN ACTUALLY GIVE -- stated before any number:
  * Neither `gp-0x6b26` nor `gp-0x6bbe` is on the wire on V102.  The ONLY firmware-internal
    magnitude channel on this build is CAN 427, and V102 repointed it to **`gp-0x6b4c`** (the
    11-slot assist sum) -- confirmed on-car, engaged-vs-manual non-zero contrast 262x.
  * `gp-0x6b26` IS on the wire on routes **7d (V84), 77 (V90), 78 (V91)**, and `gp-0x6bbe` on
    route **79** -- all 4x builds.  Those are scored here too, because they answer the actual
    question even though they are not the 6x build.

TWO INSTRUMENT HAZARDS AT 20-23 Hz, both large enough to dominate the answer:
  1. **427 SAMPLES AT 49.8 Hz => NYQUIST 24.9 Hz.**  20-23 Hz is 0.80-0.92 of Nyquist, ~2.2
     samples/cycle.  `v102_xb_lib.CH_NYQ` itself caps this lane at 20 Hz, and `builds/v80_v107/build_v102_tva.py`
     says outright "427 MUST NOT BE USED TO READ THE 23 Hz SPECTRUM."
  2. **DIFFERENTIAL ZOH PHASE.**  The lane is sample-and-held from 49.8 Hz and `tq` from
     100.74 Hz onto the same row grid, so the lane lags `tq` by (T_lane - T_tq)/2 =
     (1/49.8 - 1/100.74)/2 = 5.077 ms of PURE INSTRUMENT DELAY = **+39.3 deg at 21.5 Hz**,
     rising linearly with f.  It is corrected here explicitly; the correction is comparable in
     size to the effect being measured, so the corrected number carries real model risk.
  3. **ALIASING.**  V102's mode sits at 24.6 Hz at highway speed.  Content at 26.8-29.8 Hz folds
     straight into 20-23 Hz on a 49.8 Hz channel.  Highway frames are therefore EXCLUDED from the
     427 estimate here and the estimate is restricted to <= 65 km/h.

=> The 100.74 Hz BUS channels (`rate_f`, `cs_ang` vs `tq`) are given first and are CLEAN.  The
   record already establishes `gp-0x6b26` is an INERTIA term (a first difference of the filtered
   motor rate => acceleration) and `gp-0x6bbe` is VISCOUS + a DC pedestal (rate-derived), so the
   bus rate channel is the same physical quantity one and two differentiations away -- which is
   almost certainly a better path to L(f) than a 2.2-samples/cycle lane.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF = 256                       # 2.56 s -> df 0.391 Hz; 8 bins across 20-23 Hz
WIN = np.hanning(NF)
F = np.fft.rfftfreq(NF, 1.0 / L.FS)
BAND = (F >= 20.0) & (F <= 23.0)
T_LANE, T_TQ = 1.0 / 49.8, 1.0 / 100.74

for _r in ("96", "97", "7d", "77", "78", "79"):
    if _r not in L.ROUTES:
        L.ROUTES[_r] = L._mk(_r, _r, gain=0, clamp=0, leverB=False, idcode=0, bits="x")

LANE_ROUTES = {
    "96": ("V102 6x", "x6b94", "gp-0x6b4c (11-slot assist sum)"),
    "7d": ("V84  4x", "x6b94", "gp-0x6b26 (INERTIA lane, sar 1)"),
    "77": ("V90  4x", "x6b94", "gp-0x6b26 (INERTIA lane, sar 3)"),
    "78": ("V91  4x", "x6b94", "gp-0x6b26 (INERTIA lane, sar 3)"),
    "79": ("V91  4x", "x6b94", "gp-0x6bbe (BOOST/viscous lane, sar 4)"),
    "95": ("V101 8x", "x6b94", "gp-0x6b94 (aggregator output)"),
}


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def taper(x):
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    return (x - (c[0] * r + c[1])) * WIN


def phase_band(route, lane, ref="tq", vlo=5.0, vhi=65.0, hands=None):
    """Band-averaged arg(csd(lane, ref)) over 20-23 Hz, with a coherence gate and an episode
    bootstrap.  Cross-spectra are SUMMED (complex) across windows before the angle is taken --
    averaging angles directly is wrong when the phase wraps."""
    S, Pl, Pr, ep = [], [], [], []
    e = 0
    for b in L.all_blocks(route):
        if lane not in b or ref not in b:
            continue
        vv = b["v_rear"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= vlo) & (vv < vhi)
        if hands is not None and "cs_tq" in b:
            m = m & ((np.abs(b["cs_tq"]) >= 400) if hands else (np.abs(b["cs_tq"]) < 400))
        e += 1
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                A = np.fft.rfft(taper(b[lane][i:i + NF]))
                B = np.fft.rfft(taper(b[ref][i:i + NF]))
                S.append(A * np.conj(B))
                Pl.append(np.abs(A) ** 2)
                Pr.append(np.abs(B) ** 2)
                ep.append(e)
            i += NF // 2
    if len(S) < 6:
        return None
    S, Pl, Pr, ep = np.array(S), np.array(Pl), np.array(Pr), np.array(ep)

    def est(sel):
        s, pl, pr = S[sel].sum(0), Pl[sel].sum(0), Pr[sel].sum(0)
        coh = (np.abs(s) ** 2) / np.maximum(pl * pr, 1e-30)
        # magnitude-weighted band average of the complex cross-spectrum
        z = s[BAND].sum()
        return np.degrees(np.angle(z)), float(np.mean(coh[BAND]))
    ang, coh = est(np.arange(len(S)))
    rng = np.random.default_rng(7)
    keys = np.unique(ep)
    bs = []
    for _ in range(2000):
        pick = rng.integers(0, len(keys), len(keys))
        sel = np.concatenate([np.nonzero(ep == keys[j])[0] for j in pick])
        bs.append(est(sel)[0])
    bs = np.unwrap(np.radians(np.array(bs)))
    bs = np.degrees(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(ang=float(ang), lo=float(lo), hi=float(hi), coh=coh,
                nwin=len(S), nep=len(keys))


if __name__ == "__main__":
    hdr("1 -- CLEAN, 100.74 Hz BUS CHANNELS on route 96 (V102, 6x).  No Nyquist or ZOH problem.\n"
        "    arg(csd(X, tq)) band-averaged over 20-23 Hz, engaged, episode bootstrap.")
    for ref, nm in (("rate_f", "EPS fine angle-rate (0x18F b2:4)"),
                    ("rate_c", "carState wheel rate"),
                    ("cs_ang", "steering angle")):
        for hn, h in (("all", None), ("hands-light", False), ("hands-ON", True)):
            r = phase_band("96", ref, "tq", hands=h)
            if r is None:
                print("    %-8s %-12s too thin" % (ref, hn))
                continue
            print("    %-8s %-12s  arg = %+7.1f deg  [%+7.1f, %+7.1f]   coh2 %.3f   "
                  "%d win / %d epi   (%s)" % (ref, hn, r["ang"], r["lo"], r["hi"], r["coh"],
                                              r["nwin"], r["nep"], nm))

    hdr("2 -- THE FIRMWARE-INTERNAL LANES via CAN 427.  🛑 READ THE HAZARD BLOCK ABOVE FIRST.\n"
        "    Restricted to <= 65 km/h to keep V102's 24.6 Hz highway mode out of the alias band.\n"
        "    'corrected' adds the differential ZOH delay 5.077 ms = +39.3 deg at 21.5 Hz.")
    fc = float(np.mean(F[BAND]))
    corr = 360.0 * fc * ((T_LANE - T_TQ) / 2.0)
    print("    band centre %.2f Hz  =>  ZOH correction %+.1f deg\n" % (fc, corr))
    for rt, (lab, col, cell) in LANE_ROUTES.items():
        if rt not in L.ROUTES:
            continue
        try:
            r = phase_band(rt, col, "tq")
        except Exception as exc:
            print("    r%-3s %-9s  FAILED: %s" % (rt, lab, exc))
            continue
        if r is None:
            print("    r%-3s %-9s  too thin  (%s)" % (rt, lab, cell))
            continue
        print("    r%-3s %-9s  raw %+7.1f  CORRECTED %+7.1f deg  [%+7.1f, %+7.1f]  coh2 %.3f  "
              "%3d win / %d epi   %s"
              % (rt, lab, r["ang"], r["ang"] + corr, r["lo"] + corr, r["hi"] + corr,
                 r["coh"], r["nwin"], r["nep"], cell))
    print("\n    🛑 A coh2 near the 1/nwin noise floor means the angle is a random walk, not a")
    print("       measurement.  Compare each coh2 against 1/nwin before using any of these.")
