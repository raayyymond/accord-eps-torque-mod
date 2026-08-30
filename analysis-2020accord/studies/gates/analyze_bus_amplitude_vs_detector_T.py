#!/usr/bin/env python3
"""How big does the bus-visible torsion-bar signal actually get, against the detector threshold?

🛑🛑 THE SIZING SECTIONS OF THIS SCRIPT ARE SUPERSEDED AND MUST NOT BE REUSED. Read this first.
-------------------------------------------------------------------------------------------------
This file was written to size cal 0xC620A (T) by bounding the detector's input from the bus. That
whole framing rested on ONE unverified assumption -- that `gp-0x6c2c` is derived from the 0x18F
torsion-bar TORQUE channel at the bus LSB. **It is not.** Traced 2026-07-31 in `FUN_00041464`
@0x4184E: `gp-0x6c2c` is a MOTOR-RATE DERIVATIVE off `gp-0x4f50` (the resolver/motor electrical
rate), differenced, gained x32, twice low-passed:

    K1 = 37 (cal 0xC643C, >>7)      K2 = 22 (cal 0xC40DC, >>6)
    if abs(x) > 13000: gp_0x6c2c = 0x7fff; return     # validity ceiling -> fault sentinel
    target = x * 1024                                 # x = s16(gp-0x4f50)
    step   = ((target - old) * K1) >> 7 ; old += step  # EMA #1 increment -- THE DIFFERENCE
    acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)   # x32, clamp +-16,384,000
    state += ((acc - state) * K2) >> 6                 # EMA #2
    gp_0x6c2c = state >> 9                             # range +-32,000; T = 12800 = 40.0% of clamp

WITHDRAWN (do not carry these forward -- sections 4 / 4b / 4c below):
  * the "T ~= 2048-2560" sizing band          -- assumed the bus torque LSB
  * the "LSB at most 3.29x finer" bound        -- same assumption
  * the "per-tick rate => effectively dead" row -- priced the chain at unity gain; the x1024 and
    x32 pre-scales are invisible from the bus.

REPLACED BY: driving the integer chain above with a 21.3 Hz sinusoid, tripping T needs
|gp-0x4f50| ~= 1683 counts @1 kHz / 1821 @100 Hz -- inside that signal's own +-13000 validity
ceiling. Independently reproduced in the frequency domain (|1-H1| differencing magnitude x |H2|)
as U = 1685: agreement to 4 significant figures by a different method. The `acc` clamp bites at
U ~= 4017, so T is reached at ~42% of saturation and the response is linear there.
=> the mode was only ~1.7-2x short of arming the detector, NOT 5x and not 30x.

⚠ AND SIZING IS NOT THE BINDING ARGUMENT ANYWAY. `gp-0x671a` has four EXTERNAL consumers besides
the r24/r26 rate lanes -- `FUN_0003a382` (a CONTINUOUS LERP index into the live P/I/D lane
gp-0x6ad4), `FUN_00036c12` (friction-comp, sums into the same aggregator), `FUN_000352b4`,
`FUN_00035b20`. Lowering T changes five things at once, one of them a shape parameter on a lane
already known to be load-bearing. That is why V62 was recommended over a T edit.

WHAT STILL STANDS in this file, and is worth reusing: the 0x18F amplitude and first-difference
distributions (raw counts, native grid, all three routes), the 12-30 Hz pk-pk excursion figures,
the 8.000x rate-copy result (corr 1.0000, 16/16 segments), the no-railing check, and the "zero
samples over 12,800 on any bus channel in 88,009 frames" null -- that last one is still true, it
just no longer bears on the detector.
-------------------------------------------------------------------------------------------------

ORIGINAL PREMISE, kept for provenance (SUPERSEDED -- see above). V64's oscillation detector never
armed: bit4 of the probe (`gp-0x67df != 0`, i.e. the FSM left NEUTRAL) stayed clear for all 14,979
frames of route 35, so |gp-0x6c2c| never crossed T = cal 0xC620A = 12800. The candidate lever is to
lower T. This script bounds the input from the bus so T is not picked by guessing.

🛑 RAW COUNTS ONLY. Every number below is the signed 16-bit big-endian field as it appears on the
wire, BEFORE any DBC scale factor. That matters more than it looks:

    channel                       cache column   DBC factor   raw = ?
    0x18F[0:2] STEER_TORQUE_SENSOR   tq            x -1.0     |raw| == |tq|
    0x18F[2:4] STEER_ANGLE_RATE(F)   rate_f        x -0.1     |raw| == |rate_f| * 10
    0x14A[2:4] STEER_ANGLE_RATE(C)   rate_c        x -1.0     |raw| == |rate_c|
    0x14A[0:2] STEER_ANGLE           ang           x -0.1     |raw| == |ang| * 10

The known caveat is that the two STEER_ANGLE_RATE copies disagree: 0x18F[2:4]x-0.1 reads
0.799-0.800 of 0x14A[2:4]x-1.0 in SCALED units. In RAW COUNTS that same relation is a factor of
EIGHT (0.8 / 0.1), not 1.25 -- so "which copy" changes a raw-count headroom figure by 8x, not 25%.
Both copies are reported, raw, and the ratio is re-measured here rather than assumed.

NATIVE GRID: the .npz caches sample 0x18F held-last onto the 0x14A arrival grid. That is a
resample. This script re-reads the rlogs and takes each address at ITS OWN arrival timestamps, so
the amplitude and first-difference statistics are on the wire grid. Selection context (latActive,
vEgo, effort) is mapped from the cache by nearest-sample lookup, which is a context label, not a
resample of the measured channel.

Usage:  python studies/gates/analyze_bus_amplitude_vs_detector_T.py [--quick]
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _r31_common import band_envelope, runs_of, sustained  # noqa: E402
from rlog_parse import read_messages  # noqa: E402

T_DETECTOR = 12800          # cal 0xC620A, byte-verified by the orchestrator
RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"

ROUTES = {
    "V59 route 2c": ("75604b0a432fdc89_0000002c--eb219f392c", [0, 1, 3, 4, 8, 9, 10, 11, 12],
                     ROOT / "_scratch/cache/r2c", "r2cs"),
    "V61 route 31": ("75604b0a432fdc89_00000031--0441e00d2b", [0, 1, 2, 3],
                     ROOT / "_scratch/cache/r31", "r31s"),
    "V64 route 35": ("75604b0a432fdc89_00000035--77808fe7ce", [0, 1, 2],
                     ROOT / "_scratch/cache/r35", "r35s"),
}

# raw signed-16 fields to pull, at their own arrival timestamps
FIELDS = [("tq_raw", 0x18F, 0), ("rateF_raw", 0x18F, 2), ("ang_raw", 0x14A, 0),
          ("rateC_raw", 0x14A, 2), ("wang_raw", 0x14A, 5)]
NPZ = ROOT / "_scratch/cache/native"


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def native(route, seg):
    """Raw i16 fields at their OWN arrival times, plus t0 matching the .npz cache convention."""
    out = {n: ([], []) for n, _, _ in FIELDS}
    t0, seen18 = None, False
    for evt in read_messages(RLOGDIR / f"{route}--{seg}--rlog.zst"):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        for m in evt.can:
            if int(m.src) != 1:
                continue
            addr, d = int(m.address), bytes(m.dat)
            if addr == 0x18F and len(d) >= 5:
                seen18 = True
            if addr == 0x14A and len(d) >= 7 and seen18 and t0 is None:
                t0 = tm                      # same rule the extractors use for t=0
            for nm, a, off in FIELDS:
                if addr == a and len(d) >= off + 2:
                    out[nm][0].append(tm)
                    out[nm][1].append(i16be(d, off))
    return {nm: (np.array(t, float) - (t0 or 0.0), np.array(v, float)) for nm, (t, v) in out.items()}


def cache_ctx(cachedir, pfx, seg):
    d = {k: v for k, v in np.load(cachedir / f"{pfx}{seg}.npz").items()}
    fs = 1.0 / np.median(np.diff(d["t"]))
    return dict(t=d["t"], lat=d["cc_lat"] > 0.5, v=d["cs_v"],
                eff=np.abs(sustained(d["tq"], fs)), ang=np.abs(d["ang"]),
                gear=(d["cs_gear"] if "cs_gear" in d else np.full(len(d["t"]), -1.0)))


def label_at(ctx, t):
    """Nearest-cache-sample context for each native timestamp. A LABEL, not a resample."""
    j = np.clip(np.searchsorted(ctx["t"], t), 0, len(ctx["t"]) - 1)
    return {k: ctx[k][j] for k in ("lat", "v", "eff", "ang", "gear")}


def pct(x, name, extra=""):
    x = np.abs(np.asarray(x, float))
    if not len(x):
        return f"  {name:26s} n=0"
    return (f"  {name:26s} n={len(x):6d}  p50={np.percentile(x,50):8.1f}  "
            f"p90={np.percentile(x,90):8.1f}  p99={np.percentile(x,99):8.1f}  "
            f"max={x.max():9.1f}{extra}")


def build():
    NPZ.mkdir(exist_ok=True)
    store = {}
    for label, (route, segs, cachedir, pfx) in ROUTES.items():
        cache = NPZ / f"{pfx}native.npz"
        if cache.exists():
            store[label] = dict(np.load(cache, allow_pickle=True))
            continue
        acc = {}
        for seg in segs:
            nat = native(route, seg)
            ctx = cache_ctx(cachedir, pfx, seg)
            for nm, (t, v) in nat.items():
                lab = label_at(ctx, t)
                acc.setdefault(nm, []).append(np.column_stack(
                    [t, v, lab["lat"], lab["v"], lab["eff"], lab["ang"], lab["gear"],
                     np.full(len(t), seg, float)]))
            print(f"  {label} seg {seg}: " + "  ".join(
                f"{nm} n={len(v)}" for nm, (t, v) in nat.items()))
        store[label] = {nm: np.vstack(v) for nm, v in acc.items()}
        np.savez_compressed(cache, **store[label])
    return store


COLS = dict(t=0, v=1, lat=2, veh=3, eff=4, ang=5, gear=6, seg=7)


def sel(a, engaged=None, vlo=None, vhi=None):
    m = np.ones(len(a), bool)
    if engaged is not None:
        m &= (a[:, COLS["lat"]] > 0.5) if engaged else (a[:, COLS["lat"]] <= 0.5)
    if vlo is not None:
        m &= a[:, COLS["veh"]] > vlo
    if vhi is not None:
        m &= a[:, COLS["veh"]] <= vhi
    return m


def diffs(a):
    """(|dx| per sample, dt) over a SELECTED subset, per segment, dropping selection-gap joins."""
    dxs, dts = [], []
    for s in by_seg(a):
        dx, dt = np.diff(s[:, 1]), np.diff(s[:, 0])
        keep = (dt > 0) & (dt < 0.05)
        dxs.append(np.abs(dx[keep])); dts.append(dt[keep])
    return np.concatenate(dxs), np.concatenate(dts)


def by_seg(a):
    """🛑 The store is segment-CONCATENATED and each segment restarts t at 0, so the time column
    is NOT monotonic across a boundary. np.diff, np.searchsorted and any FFT over the whole array
    would silently splice across that discontinuity (a -60 s "gap" is not caught by a
    `gap > max_gap` test, and searchsorted on non-monotonic input returns nonsense). Everything
    time-aware must iterate segments. Amplitude percentiles are order-free and unaffected."""
    for s in np.unique(a[:, COLS["seg"]]):
        yield a[a[:, COLS["seg"]] == s]


def main():
    print("Building native-grid stores (cached in _scratch/cache/native/)...")
    store = build()

    print()
    print("=" * 108)
    print("A.  THE TWO STEER_ANGLE_RATE COPIES, IN RAW COUNTS -- re-measured, not assumed")
    print("=" * 108)
    print("  In SCALED units 0x18F[2:4]x-0.1 is ~0.80 of 0x14A[2:4]x-1.0. In RAW COUNTS the same")
    print("  relation is 0.80/0.1 = 8.0x. Measured PER SEGMENT on a common 100 Hz grid -- the two")
    print("  messages interleave, so a nearest-sample pairing of a fast channel destroys the fit.")
    for label in ROUTES:
        sl, co = [], []
        for Fs, Cs in zip(by_seg(store[label]["rateF_raw"]), by_seg(store[label]["rateC_raw"])):
            t0, t1 = max(Fs[0, 0], Cs[0, 0]), min(Fs[-1, 0], Cs[-1, 0])
            if t1 - t0 < 5:
                continue
            g = np.arange(t0, t1, 0.01)
            f = np.interp(g, Fs[:, 0], Fs[:, 1])
            c = np.interp(g, Cs[:, 0], Cs[:, 1])
            if np.sum(c * c) == 0:
                continue
            sl.append(np.sum(f * c) / np.sum(c * c))
            co.append(np.corrcoef(f, c)[0, 1])
        if not sl:
            print(f"  {label:14s} no usable segment")
            continue
        print(f"  {label:14s} {len(sl)} segments | LS slope through origin: "
              f"med={np.median(sl):6.3f} min={min(sl):6.3f} max={max(sl):6.3f} | "
              f"corr med={np.median(co):+.4f}   => scaled-unit {np.median(sl)*0.1:.3f}")

    print()
    print("=" * 108)
    print("1 & 2.  AMPLITUDE AND FIRST DIFFERENCE, RAW COUNTS, NATIVE GRID, ENGAGED CREEP (v<=5.35)")
    print("=" * 108)
    for label in ROUTES:
        print(f"\n[{label}]  engaged creep, 0.3 < v <= 5.35 m/s")
        for nm in ("tq_raw", "rateF_raw", "rateC_raw", "ang_raw"):
            a = store[label][nm]
            m = sel(a, engaged=True, vlo=0.3, vhi=5.35)
            x = a[m, 1]
            if len(x) < 10:
                print(pct([], nm))
                continue
            print(pct(x, nm + " |x|"))
            dx, dt = diffs(a[m])
            print(pct(dx, nm + " |dx| /sample"))
            print(pct(dx / dt, nm + " |dx| counts/s",
                      f"   (median dt {np.median(dt)*1e3:.2f} ms)"))

    print()
    print("=" * 108)
    print("3.  THE OSCILLATION'S OWN EXCURSION -- 12-30 Hz band, engaged creep, peak-to-peak counts")
    print("=" * 108)
    print("  band_envelope returns the AMPLITUDE A of the band-limited component; pk-pk = 2A.")
    for label in ROUTES:
        a = store[label]["tq_raw"]
        pk = []
        for seg in by_seg(a):                      # never band-limit across a segment boundary
            sm = sel(seg, engaged=True, vlo=0.3, vhi=5.35)
            t, x = seg[sm, 0], seg[sm, 1]
            if len(t) < 256:
                continue
            fs = 1.0 / np.median(np.diff(t))
            for s, e in runs_of(np.ones(len(t), bool), t, 256):
                if e - s >= 256:
                    pk.append(2 * band_envelope(x[s:e], fs, 12.0, 30.0))
        if not pk:
            print(f"  {label:14s} n=0")
            continue
        pk = np.concatenate(pk)
        print(f"  {label:14s} pk-pk n={len(pk):6d}  p50={np.percentile(pk,50):7.1f}  "
              f"p90={np.percentile(pk,90):7.1f}  p99={np.percentile(pk,99):7.1f}  "
              f"max={pk.max():7.1f} counts")

    print()
    print("=" * 108)
    print(f"4.  HEADROOM TO T = {T_DETECTOR} (cal 0xC620A)")
    print("=" * 108)
    print(f"  {'route':14s} {'channel':12s} {'max|x|':>9s} {'T/max|x|':>9s} "
          f"{'max|dx|/samp':>13s} {'T/that':>9s} {'max|dx| /s':>12s}")
    for label in ROUTES:
        for nm in ("tq_raw", "rateF_raw", "rateC_raw"):
            a = store[label][nm]
            m = sel(a, engaged=True, vlo=0.3, vhi=5.35)
            if m.sum() < 10:
                continue
            x = a[m, 1]
            dx, dt = diffs(a[m])
            print(f"  {label:14s} {nm:12s} {np.abs(x).max():9.0f} "
                  f"{T_DETECTOR/np.abs(x).max():9.1f} {dx.max():13.0f} "
                  f"{T_DETECTOR/dx.max():9.1f} {(dx/dt).max():12.0f}")

    print()
    print("=" * 108)
    print("4b.  SIZING SWEEP -- what would T have to be, and what duty cycle does it buy?")
    print("=" * 108)
    print("  duty = % of engaged-creep samples with |tq_raw| > T. LEVEL hypothesis, bus LSB.")
    print("  " + f"{'T':>7s}" + "".join(f"{lab.split()[0]:>12s}" for lab in ROUTES)
          + "   note")
    notes = {12800: "stock -- never fires", 3200: "arms on the very largest transients only",
             2560: "arms during strong bursts", 2048: "arms during ordinary grinding",
             1280: "arms most of the time"}
    for Tc in (12800, 6400, 4000, 3200, 2560, 2048, 1600, 1280, 1024):
        row = f"  {Tc:7d}"
        for label in ROUTES:
            a = store[label]["tq_raw"]
            x = np.abs(a[sel(a, engaged=True, vlo=0.3, vhi=5.35), 1])
            row += f"{100*(x>Tc).mean():11.2f}%"
        print(row + "   " + notes.get(Tc, ""))

    print()
    print("=" * 108)
    print("4c.  THE RATE HYPOTHESIS AT THE EPS TICK RATE (control task = 1 kHz, confirmed)")
    print("=" * 108)
    print("  Our bus grid is 100 Hz. If gp-0x6c2c is a per-TICK difference at 1 kHz, the internal")
    print("  delta is ~1/10 of our per-sample delta at the same slew rate:")
    print("      d_1kHz ~= (counts/s) / 1000")
    for label in ROUTES:
        a = store[label]["tq_raw"]
        dx, dt = diffs(a[sel(a, engaged=True, vlo=0.3, vhi=5.35)])
        r = dx / dt
        print(f"  {label:14s} max {r.max():9.0f} counts/s  =>  per-tick@1kHz max "
              f"{r.max()/1000:7.1f}  p99 {np.percentile(r,99)/1000:6.1f}  "
              f"T/max = {T_DETECTOR/(r.max()/1000):7.1f}x")

    print()
    print("=" * 108)
    print(f"5.  DOES ANY SAMPLE ANYWHERE EXCEED {T_DETECTOR} RAW COUNTS?  (all frames, all routes,")
    print("     engaged AND disengaged, no speed gate)")
    print("=" * 108)
    for label in ROUTES:
        for nm in ("tq_raw", "rateF_raw", "rateC_raw", "ang_raw", "wang_raw"):
            a = store[label][nm]
            x = np.abs(a[:, 1])
            over = x > T_DETECTOR
            hdr = f"  {label:14s} {nm:11s} n={len(x):7d} max={x.max():8.0f}"
            if not over.any():
                print(f"{hdr}   over-T: 0")
                continue
            idx = np.flatnonzero(over)
            print(f"{hdr}   *** over-T: {over.sum()} samples ***")
            # report contiguous excursions with context
            brk = np.flatnonzero(np.diff(idx) > 1)
            groups = np.split(idx, brk + 1)
            for g in groups[:8]:
                r = a[g]
                print(f"      seg{int(r[0,COLS['seg']])} t={r[0,0]:7.2f}-{r[-1,0]:7.2f}s "
                      f"({len(g)} samp)  peak={np.abs(r[:,1]).max():8.0f}  "
                      f"v={r[:,COLS['veh']].mean():5.2f} m/s  |ang|={r[:,COLS['ang']].mean():6.1f} "
                      f"eff={r[:,COLS['eff']].mean():6.0f}  "
                      f"{'ENGAGED' if r[:,COLS['lat']].mean()>0.5 else 'manual'}")
            if len(groups) > 8:
                print(f"      ... {len(groups)-8} more excursions")

    print()
    print("=" * 108)
    print("6.  IS THE TORQUE CHANNEL RAILING?  (a saturated sensor cannot bound an internal signal)")
    print("=" * 108)
    for label in ROUTES:
        x = store[label]["tq_raw"][:, 1]
        top = np.sort(np.unique(np.abs(x)))[-6:]
        n_at = (np.abs(x) >= top[-1] - 1).sum()
        print(f"  {label:14s} highest distinct |raw| values {top.astype(int).tolist()}   "
              f"samples within 1 count of max: {n_at}  ({100*n_at/len(x):.4f}%)")
    print("\n  A hard rail shows up as many samples piled on one exact value. A ragged top with")
    print("  single-sample occupancy means the channel is NOT clipping and the max is a real peak.")


if __name__ == "__main__":
    main()
