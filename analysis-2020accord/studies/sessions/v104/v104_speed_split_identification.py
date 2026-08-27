"""IS THE LOOP IDENTIFICATION ITSELF SPEED-DEPENDENT?  And what does V103's HIGHWAY arm measure?

Three questions, in order of how much they can change the V104 verdict:

  Q1  Can (c, A0, |kG|) be identified at HIGHWAY speed at all?
      They come from the 4x/8x step between r85 (V100) and r95 (V101).  If either arm has no
      highway exposure the answer is NO and the speed dependence of the LOOP is unclosable.

  Q2  Is G = tq -> aggregator SUM speed-dependent on the one route that has both (r85)?

  Q3  What does V103 -- THE CAR TODAY -- actually measure for Re(Z) at 6-9 Hz per speed band?
      This needs no model at all.  It is the operator's question stated as a measurement.

🛑 TRAPS: x6b94 read only on r85/r95.  Episode bootstrap, never window.  `rate_f` scale cancels
in Re Z RATIOS but NOT in absolute counts -- absolute counts here are 1.2506x high and are
compared only against other rate_f numbers.
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
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402
import check_427_alias as CA                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
KPH = 3.6
for t in ('r85', 'r95'):
    CA.assert_is_sum(t)


def masked_episode_specs(x, y, mask, nper=NPER):
    """Per-run summed spectra over contiguous runs of `mask` (>= one window)."""
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not mask[a0] or (b0 - a0) < nper:
            continue
        r = L._win_spec(x[a0:b0], y[a0:b0], nper, L.FS)
        if r is None:
            continue
        XS, YS, XY = r
        out.append((XS.sum(0), YS.sum(0), XY.sum(0), len(XS)))
    return out


def boot(specs, lo, hi, nboot=3000, seed=7):
    rng = np.random.default_rng(seed)
    n = len(specs)
    return np.array([L.band_H([specs[j] for j in rng.integers(0, n, n)], f, lo, hi)[0]
                     for _ in range(nboot)])


VB = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 130)]

print("=" * 110)
print("Q1 -- CAN THE LOOP BE IDENTIFIED AT HIGHWAY SPEED?  engaged seconds per arm per band")
print("=" * 110)
print("%22s" % 'arm' + "".join("%12s" % ("%d-%d" % b) for b in VB))
for tag, nm in (('r85', 'V100 4x  (arm 1)'), ('r95', 'V101 8x  (arm 2)')):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    print("%22s" % nm + "".join("%12.1f" % ((eng & (v >= a) & (v < b)).sum() / L.FS)
                                for a, b in VB))
print()
print("  🛑 THE 8x ARM HAS ZERO ENGAGED SECONDS ABOVE 80 km/h.  The 4x/8x step -- the ONLY")
print("     source of `c`, `A0` and |kG| in this kit -- CANNOT be evaluated at highway speed.")
print("     Any speed dependence of the LOOP is therefore UNMEASURED, not measured-and-small.")

print()
print("=" * 110)
print("Q2 -- IS G = tq -> aggregator SUM SPEED-DEPENDENT?  (route r85, the only one with both)")
print("=" * 110)
d = L.load('r85')
eng = d['cc_lat'] > 0.5
v = d['v_rear'].astype(float) * KPH
tq = d['tq'].astype(float)
u = d['x6b94'].astype(float)
print("%14s %8s %10s %10s %10s %22s" % ('speed band', 'sec', '|G|', 'arg G', 'coh2', '|G| 95 % CI'))
for lo, hi in VB:
    m = eng & (v >= lo) & (v < hi)
    sp = masked_episode_specs(tq, u, m)
    if len(sp) < 2:
        print("%9d-%-4d %8.1f %10s (%d runs -- too few for a bootstrap)"
              % (lo, hi, m.sum() / L.FS, '-', len(sp)))
        continue
    H, coh = L.band_H(sp, f, 6, 9)
    bb = np.abs(boot(sp, 6, 9))
    print("%9d-%-4d %8.1f %10.4f %+10.1f %10.3f      [%7.4f, %7.4f]"
          % (lo, hi, m.sum() / L.FS, abs(H), np.angle(H, deg=True), coh,
             np.percentile(bb, 2.5), np.percentile(bb, 97.5)))
print("  ⚠ |G| here is the SUM's transfer.  A speed trend in |G| does NOT separate `a` (the")
print("    filtered lane) from the other 10 slots -- it is the NET, after the near-cancellation.")

print()
print("=" * 110)
print("Q3 -- V103 (THE CAR TODAY, route 0x9e): Re(Z) at 6-9 Hz PER SPEED BAND, model-free")
print("=" * 110)
d9 = L.load('r9e')
e9 = d9['cc_lat'] > 0.5
v9 = d9['v_rear'].astype(float) * KPH
w9 = d9['rate_f'].astype(float) * L.DEG2RAD
t9 = d9['tq'].astype(float)
print("%14s %8s %7s %11s %11s %22s %9s" %
      ('speed band', 'sec', 'runs', 'Re Z', 'Im Z', 'Re Z 95 % CI', 'coh2'))
for lo, hi in VB:
    m = e9 & (v9 >= lo) & (v9 < hi)
    sp = masked_episode_specs(w9, t9, m)
    if len(sp) < 2:
        print("%9d-%-4d %8.1f %7d   (too few runs)" % (lo, hi, m.sum() / L.FS, len(sp)))
        continue
    H, coh = L.band_H(sp, f, 6, 9)
    bb = boot(sp, 6, 9)
    print("%9d-%-4d %8.1f %7d %+11.0f %+11.0f  [%+9.0f, %+9.0f] %9.3f"
          % (lo, hi, m.sum() / L.FS, len(sp), H.real, H.imag,
             np.percentile(bb.real, 2.5), np.percentile(bb.real, 97.5), coh))

print()
print("  SPLIT-HALF NULL CONTROL -- the SAME statistic on two halves of the SAME speed band,")
print("  which must agree if the band contrast is real and not window-manufactured:")
for lo, hi in VB:
    m = e9 & (v9 >= lo) & (v9 < hi)
    sp = masked_episode_specs(w9, t9, m)
    if len(sp) < 4:
        continue
    h1 = L.band_H(sp[0::2], f, 6, 9)[0].real
    h2 = L.band_H(sp[1::2], f, 6, 9)[0].real
    print("    %3d-%-4d km/h: half A %+8.0f   half B %+8.0f   ratio %6.2f"
          % (lo, hi, h1, h2, h1 / h2 if h2 else np.nan))

print()
print("  AND THE SAME FOR THE 6-9 Hz RATCHET AMPLITUDE (band RMS of rate_f, deg/s):")
print("%14s %8s %12s %12s" % ('speed band', 'sec', 'engaged RMS', 'manual RMS'))
for lo, hi in VB:
    row = []
    for m in (e9 & (v9 >= lo) & (v9 < hi), (~e9) & (v9 >= lo) & (v9 < hi)):
        sp = masked_episode_specs(d9['rate_f'].astype(float), d9['rate_f'].astype(float), m)
        if not sp:
            row.append(np.nan)
            continue
        sel = (f >= 6) & (f < 9)
        Sxx = sum(s[0] for s in sp)
        nw = sum(s[3] for s in sp)
        row.append(float(np.sqrt(Sxx[sel].sum() / nw * (f[1] - f[0]))))
    m0 = e9 & (v9 >= lo) & (v9 < hi)
    print("%9d-%-4d %8.1f %12.4f %12.4f" % (lo, hi, m0.sum() / L.FS, row[0], row[1]))
