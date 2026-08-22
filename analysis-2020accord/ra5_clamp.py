r"""THE `gp-0x6b26` CLAMP TABLES -- LOAD-BEARING FOR V106, SO THEY ARE A SCRIPT, NOT A LOG.

Both tables here were first produced by inline commands whose output survived only as printed text
in `rlog-tools/_ra5_clampdose.log` and `_ra5_clamprate.log`.  `.gitignore:44` eats `*.log`, and a
log is not a reproducer.  **These two tables licensed V106's dose and refuted the orchestrator's
saturation model, so they are committed as code.**

=================================================================================================
WHY THIS IS MEASURED AND NOT RECONSTRUCTED
=================================================================================================
`gp-0x6b26` is an ACCELERATION term (`accord-gp6b26-is-inertia-not-damping`: `gp-0x6c2c` is a first
difference of the filtered EPS-motor rate, and `gp-0x6b26 = -K*alpha`).  Its lane clamps at +-511
(`0xC407E`).  V106 raises its Y tables to x3.0 stock-relative, so the question is whether the raise
ARRIVES or is eaten by the clamp.

**No cascade `H(f)` is fabricated here.**  `gp-0x6b26` was ITSELF ON THE 427 WIRE on:
    r77 / r78   V90 / V91   packer `|b26|*5>>3`   =>  counts = wire * 8/5
    r7d         V94         packer `|b26|*5>>1`   =>  counts = wire * 2/5
so the distribution and the clamp duty are DIRECTLY MEASURABLE.

DOSE MAP (read from the images by the orchestrator, 2026-08-22 -- the input this file needs):
    build      mode24 0xD6A6C       mode26 0xD7A5C        mode27 0xD7A6C        mode26 vs stock
    V89/V90    (-9830,-5734,-1966)  (-9830,-5734,-1966)   (-9830,-5734,-1966)   x1.00   <- r77
    V91        (-9830,-5734,-1966)  (-14745,-8601,-2949)  (-14745,-8601,-2949)  x1.50   <- r78
    V93/V94    (-4915,-2867,-983)   (-2458,-1434,-492)    (-2458,-1434,-492)    x0.25   <- r7d
⇒ **r77 ran x1.00 stock, so V106's x3.0-stock is EXACTLY k = 3 on the r77 arm of TABLE 1.**

=================================================================================================
🛑 CAVEATS THAT TRAVEL WITH THESE NUMBERS
=================================================================================================
* The wire carries the POST-clamp lane value, so a rail shows as a PILE-UP at 511.  There is none:
  r77's highest distinct values are 274/275/293/296/302/318, TWO FRAMES EACH -- a smooth tail.
* **r7d is excluded from TABLE 2**: 10.7 s of engaged exposure, median speed 0.00 km/h (a parking
  sample), and its 10-bit wire saturates at |b26| = 409.2 -- BELOW the 511 rail -- so its tail is
  censored.  r77/r78 map the rail to wire 319 and cannot saturate.
* r77/r78 are V90/V91.  Intervening builds changed the lane's inputs, so the SHAPE transfers and
  the absolute counts transfer only through the dose map above.

=================================================================================================
WHAT TABLE 2 REFUTED
=================================================================================================
Orchestrator's model: *"at 200-400 deg/s the pre-clamp value is ~543 ct at x1.5 and ~1085 at x3.0,
both already past 511 => the term is already saturated there today."*
**Measured MAX at 200-400 deg/s on r77 is 104.0 counts** -- 5.2x under the model, 4.9x under the
rail, `duty >= 511` exactly 0.  And the SHAPE is inverted: `|gp-0x6b26|` PEAKS at 40-100 deg/s and
COLLAPSES above 100.  That is a WITHIN-ROUTE comparison across rate bins and is therefore
**DOSE-INDEPENDENT** -- it holds whatever dose r77 carried.
⭐ Mechanism: a smooth fast driver turn is high RATE but low motor ACCELERATION.  The acceleration
comes from the oscillation itself, which is why the term peaks in the mode's own 15-100 deg/s band.

Usage:  python ra5_clamp.py            # both tables
        python ra5_clamp.py dose       # TABLE 1 only
        python ra5_clamp.py rate       # TABLE 2 only
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
CLAMP = 511.0
SCALE = {'r77': 8.0 / 5.0, 'r78': 8.0 / 5.0, 'r7d': 2.0 / 5.0}
DOSE_VS_STOCK = {'r77': 1.00, 'r78': 1.50, 'r7d': 0.25}
K_COLS = (1, 1.5, 2, 3, 4, 6, 8, 12)
RATE_EDGES = [0, 5, 15, 40, 100, 200, 400, 1e9]
RATE_LBL = ['0-5', '5-15', '15-40', '40-100', '100-200', '200-400', '400+']
OUT = {'clamp': CLAMP, 'scale': SCALE, 'dose_vs_stock': DOSE_VS_STOCK}


def load_b26(tag):
    """|gp-0x6b26| in COUNTS on the row grid, plus the masks everything is stratified by."""
    d = L.load(tag)
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    b26 = mt[j] * SCALE[tag]
    e = np.asarray(d['cc_lat'], float) > 0.5
    if 'v_rear' in d.files:                       # older caches predate `v_rear`
        v = np.asarray(d['v_rear'], float) * KPH
    else:
        v = 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float)) * KPH
    rc = np.abs(np.asarray(d['rate_c'], float))   # TRUE deg/s
    tq = np.abs(np.asarray(d['tq'], float))
    acc = np.abs(np.gradient(np.asarray(d['rate_c'], float)) * FS)     # deg/s^2 proxy
    masks = [('engaged', e),
             ('S1-like', e & (v < 10) & (rc >= 5) & (rc < 40)),
             ('S2a-like', e & (v < 20) & (tq >= 1000) & (rc >= 40)),
             ('S2c-like', e & (v < 20) & (tq >= 500) & (rc >= 15) & (rc < 40)),
             ('S3-like', e & (v >= 60))]
    return b26, masks, e, rc, acc


def table1():
    print("=" * 122)
    print("TABLE 1.  CLAMP-CROSSING DUTY vs DOSE MULTIPLE k, relative to the dose THAT ROUTE ran.")
    print("          duty_k = fraction of frames with |gp-0x6b26| >= %.0f/k" % CLAMP)
    print("                 = the fraction the +-%.0f rail would clip at k x that route's dose."
          % CLAMP)
    print("          ⭐ r77 ran x1.00 stock  =>  V106's x3.0-stock is EXACTLY k = 3 on the r77 rows.")
    print("=" * 122)
    print("%8s %11s %8s" % ('route', 'mask', 'sec')
          + "".join("%11s" % ("k=%g" % k) for k in K_COLS))
    for tag in ('r77', 'r78', 'r7d'):
        b26, masks, _, _, _ = load_b26(tag)
        for lbl, m in masks:
            if m.sum() < 50:
                continue
            x = b26[m]
            row = [float(np.mean(x >= CLAMP / k)) for k in K_COLS]
            print("%8s %11s %8.1f" % (tag, lbl, m.sum() / FS)
                  + "".join("%11.5f" % r for r in row))
            OUT.setdefault('table1', {}).setdefault(tag, {})[lbl] = dict(
                sec=float(m.sum() / FS), n=int(m.sum()),
                duty={("k=%g" % k): r for k, r in zip(K_COLS, row)})
    print("  🛑 r7d rows are shown for completeness ONLY -- 10.7 s engaged, parking sample, and")
    print("     its wire censors at |b26| = 409.2, below the rail.  Do not read a k off r7d.")


def table2():
    print()
    print("=" * 122)
    print("TABLE 2.  |gp-0x6b26| ON THE WIRE, BINNED BY |rate_c| (TRUE deg/s), ENGAGED.")
    print("          This is the table that refuted the rate-monotone saturation model.")
    print("          🛑 The SHAPE across bins is a WITHIN-ROUTE comparison => DOSE-INDEPENDENT.")
    print("=" * 122)
    for tag in ('r77', 'r78'):
        b26, _, e, rc, acc = load_b26(tag)
        print("\n  === %s  (engaged %.0f s, dose x%.2f stock) ==="
              % (tag, e.sum() / FS, DOSE_VS_STOCK[tag]))
        print("%10s %9s %8s %8s %8s %8s %10s %10s %10s"
              % ('|rate| bin', 'n', 'p50', 'p90', 'p99', 'MAX',
                 'duty>=511', 'duty>=256', 'duty>=170'))
        for i, lbl in enumerate(RATE_LBL):
            m = e & (rc >= RATE_EDGES[i]) & (rc < RATE_EDGES[i + 1])
            if m.sum() < 30:
                print("%10s %9d   -- too few frames --" % (lbl, m.sum()))
                continue
            x = b26[m]
            print("%10s %9d %8.1f %8.1f %8.1f %8.1f %10.6f %10.6f %10.6f"
                  % (lbl, m.sum(), np.percentile(x, 50), np.percentile(x, 90),
                     np.percentile(x, 99), x.max(),
                     np.mean(x >= 511), np.mean(x >= 256), np.mean(x >= 170)))
            OUT.setdefault('table2', {}).setdefault(tag, {})[lbl] = dict(
                n=int(m.sum()), p50=float(np.percentile(x, 50)),
                p90=float(np.percentile(x, 90)), p99=float(np.percentile(x, 99)),
                mx=float(x.max()), duty511=float(np.mean(x >= 511)),
                duty256=float(np.mean(x >= 256)), duty170=float(np.mean(x >= 170)))
        # what drives it: rate, or acceleration?
        m = e & (b26 > 0)
        lr = np.log(np.clip(b26[m], 1, None))
        c_rate = float(np.corrcoef(lr, np.log(np.clip(rc[m], 0.5, None)))[0, 1])
        c_acc = float(np.corrcoef(lr, np.log(np.clip(acc[m], 0.5, None)))[0, 1])
        print("  corr(log|b26|, log|rate_c|)     = %+.4f" % c_rate)
        print("  corr(log|b26|, log|d(rate)/dt|) = %+.4f" % c_acc)
        # a rail would show as a PILE-UP; show the top of the histogram instead of asserting
        u, c = np.unique(b26[e], return_counts=True)
        top = np.argsort(u)[-6:]
        print("  highest distinct values (value:count): "
              + "  ".join("%.0f:%d" % (u[k], c[k]) for k in top)
              + "   <- a rail would be a PILE-UP at %.0f" % CLAMP)
        OUT.setdefault('drivers', {})[tag] = dict(corr_rate=c_rate, corr_acc=c_acc)


def assert_reported():
    """🛑 The numbers below were REPORTED to the orchestrator from the inline runs and are now
    FROZEN.  This asserts the committed script reproduces them, so the fold-in cannot silently
    change a load-bearing figure.  [`firmware-iteration`: anything reported is re-verified from
    disk at close-out.]"""
    b26, masks, e, rc, _ = load_b26('r77')
    m = e & (rc >= 200) & (rc < 400)
    assert abs(float(b26[m].max()) - 104.0) < 1e-6, "r77 200-400 MAX changed"
    assert float(np.mean(b26[m] >= CLAMP)) == 0.0, "r77 200-400 duty>=511 changed"
    m2 = e & (rc >= 40) & (rc < 100)
    assert abs(float(np.percentile(b26[m2], 99)) - 181.6) < 0.05, "r77 40-100 p99 changed"
    assert abs(float(np.mean(b26[m2] >= 170)) - 0.013209) < 1e-5, "r77 40-100 duty>=170 changed"
    d = dict(masks)
    assert abs(float(np.mean(b26[d['S1-like']] >= CLAMP / 3)) - 0.00996) < 1e-4, "S1 k=3 changed"
    assert abs(float(np.mean(b26[d['S2a-like']] >= CLAMP / 3)) - 0.00063) < 1e-4, "S2a k=3 changed"
    assert float(np.mean(b26[e] >= CLAMP)) == 0.0, "r77 engaged duty>=511 changed"
    print("\n✅ ASSERTIONS PASS -- the committed script reproduces every reported figure.")


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'dose':
        table1()
    if not a or a[0] == 'rate':
        table2()
    if not a:
        assert_reported()
        json.dump(OUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         '_ra5_clamp.json'), 'w'), indent=1, default=float)
        print("wrote _ra5_clamp.json")
