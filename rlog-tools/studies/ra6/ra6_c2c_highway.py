r"""NEW-Q2 -- `|gp-0x6c2c|` AT ROAD SPEED, AND THE RESHAPE CLAMP DUTIES.  THE BUILD-BLOCKING NUMBER.

=================================================================================================
🛑 WHERE THE SIGNAL ACTUALLY LIVES
=================================================================================================
**`gp-0x6c2c` has NEVER been on the wire, and `gp-0x6b26` is NOT on the wire on route a6.**
V104/V105/V106 all point the 427 tap at `gp-0x6b86`.  `|gp-0x6b26|` was on the wire on:
    r77  V90  x1.00 stock   packer |b26|*5>>3  => counts = wire * 8/5
    r78  V91  x1.50         same packer
    r7d  V94  x0.25         |b26|*5>>1;  EXCLUDED -- 10.7 s, parked, wire censors at 409 < the rail
Neither r77 nor r78 ever clamps (`duty >= 511` = 0.00000 measured), so on those routes the wire
value is the UNCLAMPED lane and the inversion below is exact up to wire quantisation.

=================================================================================================
THE ARITHMETIC, AND ITS PROVENANCE
=================================================================================================
    |gp-0x6b26| = ( |Y_eff(v)| * 0x111 * |gp-0x6c2c| ) >> 24
    => |gp-0x6c2c| = |gp-0x6b26| * 2^24 / (273 * |Y_eff(v)|) = |gp-0x6b26| * 61455 / |Y_eff(v)|
    => the clamp knee (|b26| = 511) sits at |gp-0x6c2c| = 31,403,505 / |Y_eff(v)|

⚠ PROVENANCE, STATED SO IT IS NOT MISTAKEN FOR A BINARY READ.  The `>>24` and the `0x111` are
  INHERITED from agent `mechanism`, not confirmed here from `FUN_00036c12`.  What IS confirmed
  here, independently:
    * the product `|Y| x knee` is invariant at 3.1403e7 across two of its own rows
      (5898 x 5324 and 29490 x 1065), which pins the constant to 511 * 2^24 / 273 = 31,403,505;
    * the LERP: X = (0, 1280, 5760) counts read byte-exact from the image, at **64 counts per
      km/h** -- itself cross-confirmed by an unrelated kit fact, `0xC62EA` = 320 counts ~ 5 km/h
      (`accord-low-speed-lockout-window-c62ea`);
    * LERPing Honda's stock Y at 8.05 km/h (= 5 mph) and multiplying by 3 gives **-24,546**,
      reproducing `mechanism`'s figure exactly.
  ⇒ Good cross-checks, but still circular against its derivation.  **SECTION 3 IS CONSTANT-FREE
    AND DOES NOT DEPEND ON ANY OF IT.**  Stake the build on section 3.

=================================================================================================
⭐ SECTION 3 IS THE ANSWER -- AND IT USES ONLY MEASURED WIRE VALUES
=================================================================================================
Whatever the scale constant is, `|gp-0x6b26| = C * |Y_eff(v)| * |gp-0x6c2c|`.  So under a reshape
that changes the schedule to `Y_X(v)`, the SAME driving produces
        |b26|_X (v)  =  |b26|_measured (v)  *  Y_X(v) / Y_route(v)
and the clamp duty is just the fraction of that above 511.  **No constant, no reconstruction, no
transfer function -- only r77's measured wire and a ratio of two flash tables.**
⚠ It is an UPPER BOUND: r77 ran x1.00 with no added damping, so its `|gp-0x6c2c|` is larger than
  what a damped V106/V107 will meet.  For a safety gate that is the right direction.

Usage:  python studies/ra6/ra6_c2c_highway.py
"""
import os
import sys
import json
import struct

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
CLAMP = 511.0
CNT_PER_KPH = 64.0
C2C_PER_B26 = 2 ** 24 / 273.0                       # 61455.0
KNEE_NUM = CLAMP * C2C_PER_B26                      # 31,403,505
Y_STOCK = np.array([-9830.0, -5734.0, -1966.0])
X_CNT = np.array([0.0, 1280.0, 5760.0])
DOSE = {'r77': 1.0, 'r78': 1.5}
WIRE = {'r77': 8.0 / 5.0, 'r78': 8.0 / 5.0}
VE = [0, 16, 40, 70, 90, 1e9]
VL = ['<16', '16-40', '40-70', '70-90', '>=90']
RE = [0, 5, 15, 40, 100, 1e9]
RL = ['0-5', '5-15', '15-40', '40-100', '100+']
OUT = {}

RESHAPE = {
    'V106 today': (-29490.0, -17202.0, -5898.0),
    'RESHAPE A': (-29490.0, -29490.0, -29490.0),
    'RESHAPE B': (-29490.0, -24000.0, -16000.0),
    'RESHAPE C': (-29490.0, -29490.0, -20000.0),
}


def yeff(v_kph, Y):
    """Piecewise-linear |Y| over the record's own X breakpoints, in km/h."""
    return np.abs(np.interp(np.asarray(v_kph, float) * CNT_PER_KPH, X_CNT, np.asarray(Y, float)))


# ---- self-check of the LERP against mechanism's published figure
_chk = yeff(8.0467, Y_STOCK * 3.0)
assert abs(_chk - 24546) < 3, "LERP self-check failed: got %.1f, expected 24546" % _chk
print("LERP self-check: V106 |Y_eff| at 5 mph (8.047 km/h) = %.0f   (mechanism: 24,546)  OK"
      % _chk)
print("Knee |gp-0x6c2c| = %.0f / |Y_eff|.  V106 @>=90 km/h: |Y|=5898 -> knee %.0f   "
      "RESHAPE A: |Y|=29490 -> knee %.0f" % (KNEE_NUM, KNEE_NUM / 5898, KNEE_NUM / 29490))


def route(tag):
    d = L.load(tag)
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    b26 = mt[j] * WIRE[tag]
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d.files
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    rc = np.abs(np.asarray(d['rate_c'], float))
    Ye = yeff(v, Y_STOCK * DOSE[tag])
    c2c = b26 * C2C_PER_B26 / np.maximum(Ye, 1.0)
    return b26, c2c, e, v, rc, Ye


R = {t: route(t) for t in ('r77', 'r78')}

# ================================================================== 1. THE NUMBER
print()
print("=" * 124)
print("1.  ⭐⭐ `|gp-0x6c2c|` BY SPEED BAND -- **MEASURED**, engaged, from the r77/r78 wire.")
print("    This is the number that picks the reshape variant.  ⚠ r77 ran x1.00 with NO added")
print("    damping, so this is the UNDAMPED distribution and an UPPER BOUND for V107.")
print("=" * 124)
print("%6s %8s %9s %8s %10s %10s %10s %10s %12s"
      % ('route', 'speed', 'n frames', 'sec', 'p50', 'p90', 'p99', 'max', '|Y_eff| med'))
for tag in ('r77', 'r78'):
    b26, c2c, e, v, rc, Ye = R[tag]
    for i, s in enumerate(VL):
        m = e & (v >= VE[i]) & (v < VE[i + 1])
        if m.sum() < 60:
            print("%6s %8s %9d   -- too few engaged frames --" % (tag, s, m.sum()))
            continue
        x = c2c[m]
        print("%6s %8s %9d %8.1f %10.0f %10.0f %10.0f %10.0f %12.0f"
              % (tag, s, int(m.sum()), m.sum() / FS,
                 *[np.percentile(x, p) for p in (50, 90, 99)], x.max(), np.median(Ye[m])))
        OUT.setdefault('c2c_measured', {}).setdefault(tag, {})[s] = dict(
            n=int(m.sum()), sec=float(m.sum() / FS), mx=float(x.max()),
            yeff_med=float(np.median(Ye[m])),
            **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

print()
print("  SAME, BY |rate_c| BIN, at >= 40 km/h only (the road-speed arm):")
print("%6s %10s %9s %10s %10s %10s %10s" % ('route', '|rate| bin', 'n', 'p50', 'p90', 'p99', 'max'))
for tag in ('r77', 'r78'):
    b26, c2c, e, v, rc, Ye = R[tag]
    for i, s in enumerate(RL):
        m = e & (v >= 40) & (rc >= RE[i]) & (rc < RE[i + 1])
        if m.sum() < 40:
            continue
        x = c2c[m]
        print("%6s %10s %9d %10.0f %10.0f %10.0f %10.0f"
              % (tag, s, int(m.sum()), *[np.percentile(x, p) for p in (50, 90, 99)], x.max()))
        OUT.setdefault('c2c_by_rate_ge40', {}).setdefault(tag, {})[s] = dict(
            n=int(m.sum()), mx=float(x.max()),
            **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

print()
print("  🛑 QUANTISATION FLOOR, so the percentiles are not over-read: one wire LSB = %.1f counts"
      % WIRE['r77'] + " of |b26|, which at a given |Y_eff| is")
for tag in ('r77',):
    b26, c2c, e, v, rc, Ye = R[tag]
    for i, s in enumerate(VL):
        m = e & (v >= VE[i]) & (v < VE[i + 1])
        if m.sum() < 60:
            continue
        step = WIRE[tag] * C2C_PER_B26 / np.median(Ye[m])
        print("     %-6s |gp-0x6c2c| step = %8.1f counts   (%.1f %% of frames read wire 0)"
              % (s, step, 100 * np.mean(b26[m] == 0)))
        OUT.setdefault('quantisation', {})[s] = dict(step=float(step),
                                                     frac_wire_zero=float(np.mean(b26[m] == 0)))

# ================================================================== 2. the a6 reconstruction
print()
print("=" * 124)
print("2.  THE SAME QUANTITY RECONSTRUCTED ON ROUTE a6 ITSELF -- the ALREADY-DAMPED distribution,")
print("    which is the operative one for sizing V107.  🛑 RECONSTRUCTION (r77 alpha->b26 law,")
print("    residuals resampled from r77's own), +-20 %% on the tail.  Not a measurement.")
print("=" * 124)
d6 = L.load('ra6')
e6 = np.asarray(d6['cc_lat'], float) > 0.5
v6 = np.asarray(d6['v_rear'], float) * KPH
rc6 = np.abs(np.asarray(d6['rate_c'], float))
rf6 = np.asarray(d6['rate_f'], float)
a6 = np.abs(np.gradient(rf6) * FS)
kk = int(round(0.05 * FS)) | 1
a6 = np.convolve(a6, np.ones(kk) / kk, mode='same')
b77, c77, e77, v77, rc77, Ye77 = R['r77']
rf7 = np.asarray(L.load('r77')['rate_f'], float)
a77 = np.convolve(np.abs(np.gradient(rf7) * FS), np.ones(kk) / kk, mode='same')
m = e77 & (b77 > 0) & (a77 > 0)
sl, ic = np.polyfit(np.log(a77[m]), np.log(b77[m]), 1)
res = np.log(b77[m]) - (sl * np.log(a77[m]) + ic)
rg = np.random.default_rng(9)
NS = 12
# predict |b26| at r77's OWN dose, then convert to |c2c| via r77's Y schedule -> dose-free
pred_b26_stockdose = np.exp(sl * np.log(np.clip(a6, 1e-6, None))[None, :] + ic
                            + rg.choice(res, (NS, len(a6))))
Ye6_stock = yeff(v6, Y_STOCK)
c2c6 = pred_b26_stockdose * C2C_PER_B26 / np.maximum(Ye6_stock, 1.0)[None, :]
print("%8s %9s %8s %10s %10s %10s %10s" % ('speed', 'n frames', 'sec', 'p50', 'p90', 'p99', 'max'))
for i, s in enumerate(VL):
    mm = e6 & (v6 >= VE[i]) & (v6 < VE[i + 1])
    if mm.sum() < 60:
        continue
    x = c2c6[:, mm]
    print("%8s %9d %8.1f %10.0f %10.0f %10.0f %10.0f"
          % (s, int(mm.sum()), mm.sum() / FS,
             *[np.percentile(x, p) for p in (50, 90, 99)], x.max()))
    OUT.setdefault('c2c_a6_reconstructed', {})[s] = dict(
        n=int(mm.sum()), sec=float(mm.sum() / FS), mx=float(x.max()),
        **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

# ================================================================== 3. CONSTANT-FREE
print()
print("=" * 124)
print("3.  ⭐⭐⭐ **THE CONSTANT-FREE ANSWER -- STAKE THE BUILD ON THIS TABLE.**")
print("    |b26|_X(v) = |b26|_MEASURED(v) * Y_X(v) / Y_route(v).  Only r77/r78's measured wire and")
print("    a ratio of two flash tables.  No scale constant, no >>24, no reconstruction.")
print("    ⚠ UPPER BOUND: r77 is undamped, so a damped V107 meets LESS than this.")
print("=" * 124)
for tag in ('r77', 'r78'):
    b26, c2c, e, v, rc, Ye = R[tag]
    Yr = yeff(v, Y_STOCK * DOSE[tag])
    print("\n  from %s (measured, dose x%.2f stock, %.0f s engaged)"
          % (tag, DOSE[tag], e.sum() / FS))
    print("%14s %8s %9s" % ('variant', 'speed', 'n') + "".join(
        "%13s" % c for c in ('p50 |b26|', 'p99 |b26|', 'duty>=511', 'duty>=256')))
    for nm, Y in RESHAPE.items():
        for i, s in enumerate(VL):
            mm = e & (v >= VE[i]) & (v < VE[i + 1])
            if mm.sum() < 60:
                continue
            scaled = b26[mm] * yeff(v[mm], Y) / np.maximum(Yr[mm], 1.0)
            print("%14s %8s %9d %13.1f %13.1f %13.5f %13.5f"
                  % (nm, s, int(mm.sum()), np.percentile(scaled, 50),
                     np.percentile(scaled, 99), np.mean(scaled >= CLAMP),
                     np.mean(scaled >= 256)))
            OUT.setdefault('reshape_duty', {}).setdefault(tag, {}).setdefault(nm, {})[s] = dict(
                n=int(mm.sum()), p50=float(np.percentile(scaled, 50)),
                p99=float(np.percentile(scaled, 99)),
                duty511=float(np.mean(scaled >= CLAMP)),
                duty256=float(np.mean(scaled >= 256)))

# ================================================================== 4. NEW-Q3
print()
print("=" * 124)
print("4.  NEW-Q3 -- THE **MEASURED** V106 CLAMP DUTY AT <16 km/h, against the predicted 9.98 %.")
print("    V106 is exactly x3.0 of stock at EVERY knot, so scaling r77's measured wire by 3.0")
print("    (and r78's by 2.0) reproduces V106's lane exactly -- again with no model.")
print("=" * 124)
print("%6s %10s %8s %9s %10s %10s %10s %12s %12s"
      % ('route', 'stratum', 'k used', 'n', 'p50', 'p90', 'p99', 'duty>=511', 'duty>=256'))
for tag in ('r77', 'r78'):
    b26, c2c, e, v, rc, Ye = R[tag]
    k = 3.0 / DOSE[tag]
    tq = np.abs(np.asarray(L.load(tag)['tq'], float))
    for lbl, mm in (('engaged', e), ('<8 km/h', e & (v < 8)), ('<16 km/h', e & (v < 16)),
                    ('S1-like', e & (v < 10) & (rc >= 5) & (rc < 40)),
                    ('S2c hard', e & (v < 20) & (tq >= 500) & (rc >= 15) & (rc < 40)),
                    ('40-95', e & (v >= 40) & (v < 95)), ('>=70', e & (v >= 70))):
        if mm.sum() < 60:
            continue
        x = b26[mm] * k
        print("%6s %10s %8.2f %9d %10.1f %10.1f %10.1f %12.5f %12.5f"
              % (tag, lbl, k, int(mm.sum()), *[np.percentile(x, p) for p in (50, 90, 99)],
                 np.mean(x >= CLAMP), np.mean(x >= 256)))
        OUT.setdefault('newq3_measured_v106_duty', {}).setdefault(tag, {})[lbl] = dict(
            k=float(k), n=int(mm.sum()), duty511=float(np.mean(x >= CLAMP)),
            duty256=float(np.mean(x >= 256)),
            **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})
print("  🛑 These rows are UPPER BOUNDS on V106's real duty: r77/r78 carry the UNDAMPED (or")
print("     half-damped) |gp-0x6c2c|, and V106's whole purpose is to shrink it.")

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_c2c_highway.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_c2c_highway.json")
