#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §1 THE LINE INVENTORY, 2-60 Hz, engaged creep.

The operator reports a MICRO-RATCHET at creep on V72: felt in the column and wheel, NOT audible,
NOT mechanically heavy. He hypothesises it is a low-amplitude continuation of grind #1 (18-22 Hz).
🛑 This file does NOT assume that. It sweeps the whole 2-60 Hz range and inventories every line.

INSTRUMENT -- identical numerics to studies/sessions/r58/r58_ratchet.py / studies/sessions/r50/r50_ratchet.py:
  * DISJOINT NFFT=256 windows (2.56 s, 0.391 Hz bins). Window counts are sample counts.
  * fs from `_r4f_lib.fs_lattice`, NEVER 1/median(dt).
  * AVERAGE THE PERIODOGRAMS FIRST, peak-find after (a median-of-per-window-argmax manufactures a
    line at band centre; it beat the alternative at dBIC 249-460 once and was wrong).
  * Prominence = P / its own local median floor, per bin (`_r37_ratchet_lib.prom_spectrum`).
  * Physical amplitude beside every prominence: analytic band envelope p99, counts; p-p = 2x.
  * ENGAGEMENT is `cc_lat` (carControl.latActive). NEVER cruiseState.
  * HANDS-OFF is sustained |lowpass(tq,3Hz)| <= 300.

Writes `_scratch/out/_r59_inventory.json`.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r37_ratchet_lib as R37  # noqa: E402

NFFT = 256
CACHE = ROOT / "_scratch/cache/r59"
PFX = "r59s"
SEGS = list(range(12))          # 12-14 are PARK, v == 0, lat 0% -- excluded from all driving cells
PARKED = [12, 13, 14]
CREEP = 4.0                     # m/s, the ratchet's own creep cell
HANDS_OFF = 300.0
OUT = {}


def hdr(s):
    print("\n" + "=" * 118 + f"\n{s}\n" + "=" * 118)


def scan(segs, nfft=NFFT, cache=CACHE, pfx=PFX):
    """Disjoint-window records with the FULL periodogram retained, so any band can be re-priced."""
    recs = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, cache, pfx)
        fs = R4F.fs_lattice(d)
        t = np.asarray(d["t"], float)
        tq = np.asarray(d["tq"], float)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        csang = np.asarray(d["cs_ang"], float)
        rate = np.asarray(d["rate_c"], float)
        rpm = np.asarray(d["rpm"], float)
        for i in range(0, len(t) - nfft + 1, nfft):
            w = slice(i, i + nfft)
            P = periodogram(tq[w], fs, nfft)
            if P is None:
                continue
            recs.append(dict(seg=int(s), i0=i, t0=float(t[i]), fs=fs, P=P,
                             lat=float(lat[w].mean()), v=float(v[w].mean()),
                             vmin=float(v[w].min()), vmax=float(v[w].max()),
                             ang=float(np.median(ang[w])), absang=float(np.mean(np.abs(ang[w]))),
                             csang=float(np.median(csang[w])),
                             rate90=float(np.percentile(np.abs(rate[w]), 90)),
                             ratem=float(np.mean(np.abs(rate[w]))),
                             rpm=float(np.nanmean(rpm[w])),
                             eff=float(np.median(eff[w]))))
    return recs


ALL = scan(SEGS)
PARK = scan(PARKED)
FS = float(np.median([r["fs"] for r in ALL]))
F = np.fft.rfftfreq(NFFT, 1 / FS)
print(f"route 59: {len(ALL)} driving windows ({len(ALL) * NFFT / FS:.1f} s), "
      f"{len(PARK)} parked windows ({len(PARK) * NFFT / FS:.1f} s), fs = {FS:.4f} Hz, "
      f"bin = {F[1]:.4f} Hz")


# ---------------------------------------------------------------- cells --------------------------
def cell(rs, eng=None, vlo=0.0, vhi=1e9, hands=None):
    out = list(rs)
    if eng is True:
        out = [r for r in out if r["lat"] > 0.9]
    if eng is False:
        out = [r for r in out if r["lat"] < 0.1]
    out = [r for r in out if vlo <= r["v"] < vhi]
    if hands == "off":
        out = [r for r in out if r["eff"] <= HANDS_OFF]
    if hands == "on":
        out = [r for r in out if r["eff"] > HANDS_OFF]
    return out


def avgP(rs):
    return np.mean(np.array([r["P"] for r in rs]), axis=0) if rs else None


hdr("§0  EXPOSURE CENSUS -- every cell used below, with its window count and speed distribution")
print(f"   {'cell':38s} {'wins':>5s} {'secs':>7s} | {'v med':>6s} {'v p5':>6s} {'v p95':>6s} "
      f"{'eff med':>8s} {'|ang| med':>9s}")
CELLS = {
    "engaged  creep <4          all-hands": cell(ALL, True, 0, CREEP),
    "engaged  creep <4          hands-OFF": cell(ALL, True, 0, CREEP, "off"),
    "engaged  creep <4          hands-ON ": cell(ALL, True, 0, CREEP, "on"),
    "manual   creep <4          all-hands": cell(ALL, False, 0, CREEP),
    "manual   creep <4          hands-OFF": cell(ALL, False, 0, CREEP, "off"),
    "engaged  4-10 m/s          all-hands": cell(ALL, True, CREEP, 10),
    "engaged  10-20 m/s         all-hands": cell(ALL, True, 10, 20),
    "engaged  20+ m/s           all-hands": cell(ALL, True, 20, 1e9),
    "manual   4-10 m/s          all-hands": cell(ALL, False, CREEP, 10),
    "PARKED   v==0 (segs 12-14) manual   ": PARK,
}
cens = {}
for k, rs in CELLS.items():
    if not rs:
        print(f"   {k:38s} {0:>5d} {'--':>7s} |  EMPTY")
        cens[k] = dict(n=0)
        continue
    v = np.array([r["v"] for r in rs])
    e = np.array([r["eff"] for r in rs])
    a = np.array([r["absang"] for r in rs])
    cens[k] = dict(n=len(rs), secs=len(rs) * NFFT / FS, vmed=float(np.median(v)),
                   v5=float(np.percentile(v, 5)), v95=float(np.percentile(v, 95)),
                   eff=float(np.median(e)))
    print(f"   {k:38s} {len(rs):>5d} {len(rs) * NFFT / FS:>7.1f} | {np.median(v):>6.2f} "
          f"{np.percentile(v, 5):>6.2f} {np.percentile(v, 95):>6.2f} {np.median(e):>8.0f} "
          f"{np.median(a):>9.2f}")
OUT["census"] = cens

# ---------------------------------------------------------------- §1 the inventory ---------------
hdr("§1  ★★ THE LINE INVENTORY -- averaged prominence spectrum, ENGAGED CREEP (<4 m/s), 2-60 Hz")
print("   Every local maximum of the AVERAGED prominence spectrum with prominence >= 2.0 is listed.")
print("   `amp p-p` is 2x the p99 analytic envelope in a +/-0.8 Hz band around the line, in torque")
print("   counts, MEDIAN over the cell's windows -- a physical amplitude, not a ratio.\n")


def band_amp(rs, f0, half=0.8):
    """Median (and p90) of the per-window p99 analytic envelope in [f0-half, f0+half]. Counts (p-p)."""
    vals = []
    for r in rs:
        d = _seg(r["seg"])
        w = slice(r["i0"], r["i0"] + NFFT)
        env = _env(r["seg"], f0, half)
        vals.append(2 * float(np.percentile(env[w], 99)))
    return (float(np.median(vals)), float(np.percentile(vals, 90)), float(np.max(vals))) if vals \
        else (np.nan, np.nan, np.nan)


_SEGC, _ENVC = {}, {}


def _seg(s):
    if s not in _SEGC:
        _SEGC[s] = C.load(s, CACHE, PFX)
    return _SEGC[s]


def _env(s, f0, half):
    key = (s, round(f0, 3), half)
    if key not in _ENVC:
        d = _seg(s)
        _ENVC[key] = band_envelope(np.asarray(d["tq"], float), R4F.fs_lattice(d),
                                   max(f0 - half, 0.5), f0 + half)
    return _ENVC[key]


def inventory(rs, lo=2.0, hi=60.0, minprom=2.0, label=""):
    P = avgP(rs)
    if P is None:
        return []
    R = R37.prom_spectrum(F, P)
    rows = []
    for j in range(1, len(F) - 1):
        if not (lo <= F[j] <= hi) or not np.isfinite(R[j]):
            continue
        if R[j] < minprom or R[j] < R[j - 1] or R[j] < R[j + 1]:
            continue
        y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
        den = y0 - 2 * y1 + y2
        dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        f0 = float(F[j] + np.clip(dl, -0.5, 0.5) * (F[1] - F[0]))
        # -3 dB width of the averaged spectrum at this peak
        half = P[j] / 2
        a = j
        while a > 1 and P[a] > half:
            a -= 1
        b = j
        while b < len(P) - 2 and P[b] > half:
            b += 1
        bw = max(F[b] - F[a], F[1] - F[0])
        rows.append(dict(f0=f0, prom=float(R[j]), bw=float(bw), P=float(P[j])))
    rows.sort(key=lambda r: -r["prom"])
    return rows


ec = CELLS["engaged  creep <4          all-hands"]
rows = inventory(ec, label="engaged creep")
print(f"   {'f0 Hz':>7s} {'prom':>7s} {'-3dB BW':>8s} {'Q(app)':>7s} | {'amp p-p med':>12s} "
      f"{'p90':>8s} {'max':>8s} | note")
inv = []
for r in rows[:24]:
    med, p90, mx = band_amp(ec, r["f0"])
    r.update(amp_med=med, amp_p90=p90, amp_max=mx)
    inv.append(r)
    note = ""
    if 6.0 <= r["f0"] <= 9.0:
        note = "<-- THE RATCHET BAND"
    if 18.0 <= r["f0"] <= 22.0:
        note = "<-- GRIND #1 BAND"
    if 40.0 <= r["f0"] <= 49.0:
        note = "<-- GRIND #2 BAND"
    print(f"   {r['f0']:>7.3f} {r['prom']:>7.2f} {r['bw']:>8.3f} {r['f0'] / r['bw']:>7.1f} | "
          f"{med:>12.0f} {p90:>8.0f} {mx:>8.0f} | {note}")
OUT["inventory_engaged_creep"] = inv

hdr("§1b  THE SAME SWEEP IN EVERY OTHER CELL -- what is CONDITIONAL and what is not")
print(f"   {'cell':38s} | top lines 2-60 Hz (f0 : prominence), strongest first\n")
cellinv = {}
for k, rs in CELLS.items():
    if len(rs) < 4:
        print(f"   {k:38s} | n={len(rs)}  UNDERPOWERED")
        continue
    rr = inventory(rs)
    cellinv[k] = rr[:8]
    s = "  ".join(f"{r['f0']:.2f}:{r['prom']:.1f}" for r in rr[:8])
    print(f"   {k:38s} | n={len(rs):<4d} {s}")
OUT["inventory_by_cell"] = cellinv

json.dump(OUT, open(ROOT / "_scratch/out/_r59_inventory.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_scratch/out/_r59_inventory.json'}")
