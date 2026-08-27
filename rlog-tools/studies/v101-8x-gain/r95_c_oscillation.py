#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- **C. THE OSCILLATION**.

Locates the dominant engaged oscillation per channel and per SPEED BIN, and runs the kit's
recorded WHEEL-ORDER TRAP explicitly: a line at 0.489*v Hz (v in m/s) is tyre order 1, not
firmware.  Order k sits at k*v/(2*pi*r) with the measured circumference 2.073-2.080 m
=> order-1 slope 0.4808..0.4824 Hz per m/s; the kit's recorded constant is 0.489.
"""
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

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
t = L.col("t")
lat = L.engaged()
vk = np.abs(L.col("cs_v")) * 3.6           # km/h  (cs_v is m/s)
vms = np.abs(L.col("cs_v"))                # m/s
CIRC = 2.0765                              # m, measured on this car (V57)
ORDER1 = 1.0 / CIRC                        # Hz per m/s = 0.4816

CH = {
    "tq": ("driver torsion bar (0x18F b0:2)", L.col("tq")),
    "rate_f": ("fine angle rate deg/s (0x18F b2:4)", L.col("rate_f")),
    "ang": ("steering angle deg (0x14A b0:2)", L.col("ang")),
    "x6b94": ("AGGREGATOR OUTPUT counts (CAN 427)", L.col("x6b94")),
    "sc_tq": ("openpilot LKAS command (sendcan 0xE4)", L.col("sc_tq")),
}

SPEED_BINS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70)]
NFFT = 1024                                 # 0.0970 Hz resolution at 99.32 Hz


def peaks(f, P, lo, hi, k=5):
    b = (f >= lo) & (f <= hi)
    fb, Pb = f[b], P[b]
    out = [(Pb[i], fb[i]) for i in range(1, len(fb) - 1)
           if Pb[i] > Pb[i - 1] and Pb[i] > Pb[i + 1]]
    out.sort(reverse=True)
    return out[:k], float(np.median(Pb))


def refine(f, P, f0, halfwidth=1.5):
    """Power-weighted centroid and -3 dB width around the local max nearest f0."""
    b = (f >= f0 - halfwidth) & (f <= f0 + halfwidth)
    fb, Pb = f[b], P[b]
    if len(fb) < 3:
        return f0, float("nan"), float("nan")
    i = int(np.argmax(Pb))
    pk = Pb[i]
    cen = float(np.sum(fb * Pb) / np.sum(Pb))
    half = pk / 2.0
    lo = fb[0]
    for j in range(i, -1, -1):
        if Pb[j] < half:
            lo = fb[j]
            break
    hi = fb[-1]
    for j in range(i, len(fb)):
        if Pb[j] < half:
            hi = fb[j]
            break
    return float(fb[i]), cen, float(hi - lo)


out = {"fs": FS, "circumference_m": CIRC, "order1_hz_per_ms": ORDER1, "channels": {}}

print("=" * 104)
print("C. THE OSCILLATION -- route 95 / V101.  Welch nfft=1024 (df=%.4f Hz), 50%% overlap, "
      "contiguous engaged runs only" % (FS / NFFT))
print("=" * 104)

for key, (desc, x) in CH.items():
    f, P, K = L.welch(x, lat, FS, nfft=NFFT)
    pk, med = peaks(f, P, 2.0, 45.0, 6)
    print(f"\n### {key:6s} {desc}   K={K} windows, all engaged")
    for p, ff in pk:
        fpk, cen, w3 = refine(f, P, ff)
        print(f"     {ff:6.2f} Hz   PSD {p:11.4g}  = {p/med:6.1f}x band median   "
              f"-3dB width {w3:4.2f} Hz   centroid {cen:6.2f} Hz")
    out["channels"][key] = {"desc": desc, "K": K,
                            "peaks": [{"f": float(ff), "psd": float(p), "x_median": float(p / med)}
                                      for p, ff in pk]}

# =====================================================================================
#  SPEED-RESOLVED -- THE WHEEL-ORDER TRAP
# =====================================================================================
print("\n" + "=" * 104)
print("SPEED-RESOLVED PEAK TRACKING -- 🛑 THE WHEEL-ORDER TRAP")
print("  order-1 tyre line = v_ms / 2.0765 m  (0.4816 Hz per m/s).  If the peak tracks that")
print("  line it is a TYRE, not the firmware.  A speed-INVARIANT peak is a fixed resonance.")
print("=" * 104)

track = {}
for key in ("tq", "rate_f", "x6b94"):
    desc, x = CH[key]
    print(f"\n### {key}  -- {desc}")
    print(f"    {'speed km/h':>12s} {'sec':>7s} {'K':>4s}  {'v_ms':>6s} {'order1':>7s}  "
          f"| {'PEAK 5-12Hz':>12s} {'x med':>7s} | {'PEAK 15-32Hz':>13s} {'x med':>7s}")
    rows = []
    for lo, hi in SPEED_BINS:
        m = lat & (vk >= lo) & (vk < hi)
        if m.sum() < NFFT:
            continue
        f, P, K = L.welch(x, m, FS, nfft=NFFT)
        if K == 0:
            continue
        vmed = float(np.median(vms[m]))
        pl, medl = peaks(f, P, 5.0, 12.0, 1)
        ph, medh = peaks(f, P, 15.0, 32.0, 1)
        fl = pl[0][1] if pl else float("nan")
        rl = pl[0][0] / medl if pl else float("nan")
        fh = ph[0][1] if ph else float("nan")
        rh = ph[0][0] / medh if ph else float("nan")
        print(f"    {lo:5d}-{hi:<6d} {m.sum()/FS:7.1f} {K:4d}  {vmed:6.2f} {vmed*ORDER1:7.2f}  "
              f"| {fl:12.2f} {rl:7.1f} | {fh:13.2f} {rh:7.1f}")
        rows.append(dict(lo=lo, hi=hi, sec=float(m.sum() / FS), K=K, v_ms=vmed,
                         order1_hz=float(vmed * ORDER1), f_lo=float(fl), r_lo=float(rl),
                         f_hi=float(fh), r_hi=float(rh)))
    track[key] = rows

out["speed_tracking"] = track

# ---- formal wheel-order regression on the strongest low-band channel
print("\n" + "-" * 104)
print("WHEEL-ORDER REGRESSION -- peak frequency vs v_ms, per band, weighted by exposure")
print("-" * 104)
for key in ("tq", "rate_f", "x6b94"):
    for band, fk in (("5-12 Hz", "f_lo"), ("15-32 Hz", "f_hi")):
        rows = [r for r in track[key] if np.isfinite(r[fk])]
        if len(rows) < 3:
            continue
        v = np.array([r["v_ms"] for r in rows])
        fp = np.array([r[fk] for r in rows])
        w = np.array([r["sec"] for r in rows])
        A = np.vstack([v, np.ones_like(v)]).T
        W = np.diag(w)
        beta = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ fp, rcond=None)[0]
        pred = A @ beta
        ss = float(np.sum(w * (fp - pred) ** 2) / np.sum(w * (fp - np.average(fp, weights=w)) ** 2))
        print(f"  {key:6s} {band:9s}  slope {beta[0]:+7.4f} Hz/(m/s)  intercept {beta[1]:7.3f} Hz  "
              f"1-R2 {ss:5.3f}   [tyre order 1 slope = {ORDER1:+.4f}, intercept 0]")
        out.setdefault("regressions", []).append(
            dict(channel=key, band=band, slope=float(beta[0]), intercept=float(beta[1]),
                 resid_frac=ss, tyre_slope=ORDER1))

# =====================================================================================
#  AMPLITUDE vs SPEED -- the operator's "at ALL speeds now" claim
# =====================================================================================
print("\n" + "=" * 104)
print("AMPLITUDE vs SPEED -- band-RMS of the analytic envelope, engaged, per speed bin")
print("  (p50 and p90 of the per-sample band envelope; the mode is BURSTY so p90 matters)")
print("=" * 104)
BANDS = {"6-10 Hz": (6.0, 10.0), "20-27 Hz": (20.0, 27.0), "2-5 Hz (control)": (2.0, 5.0)}
amp = {}
for key in ("tq", "rate_f", "x6b94"):
    desc, x = CH[key]
    print(f"\n### {key}  ({desc})")
    hdr = f"    {'speed km/h':>12s} {'sec':>7s}"
    for bn in BANDS:
        hdr += f" | {bn+' p50':>16s} {'p90':>8s}"
    print(hdr)
    for lo, hi in SPEED_BINS:
        m = lat & (vk >= lo) & (vk < hi)
        if m.sum() < 200:
            continue
        line = f"    {lo:5d}-{hi:<6d} {m.sum()/FS:7.1f}"
        for bn, (bl, bh) in BANDS.items():
            env = L.band_envelope(x, FS, bl, bh, mask=lat)
            e = env[m]
            e = e[np.isfinite(e)]
            line += f" | {np.percentile(e,50):16.3f} {np.percentile(e,90):8.3f}"
            amp.setdefault(key, {}).setdefault(bn, []).append(
                dict(lo=lo, hi=hi, sec=float(m.sum() / FS), p50=float(np.percentile(e, 50)),
                     p90=float(np.percentile(e, 90))))
        print(line)
out["amplitude_vs_speed"] = amp

(L.CACHE / "r95_C_oscillation.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_C_oscillation.json'}")
