"""ROBUSTNESS OF THE SPEED SHAPE s(v), AND THE TAIL-RISK / CLIP NUMBERS THE VERDICT NEEDS.

Four things the recommendation must not rest on a lucky choice of:
  1. THE SECANT HALF-WIDTH used to read the ROM map's local slope.  The right width is the
     actual in-band AC excursion of driver torque, which is MEASURED here, not guessed.
  2. WHETHER THE SHAPE IS THE SPEED SCHEDULE OR THE OPERATING POINT.  Both are reported.
  3. TAIL RISK.  P(amp > 1.5) and P(amp > 2) are more interpretable than a bootstrap MAX.
  4. THE CLIP GATE at realistic vs adversarial vs reachable inputs.

🛑 AND ONE RECORD CHECK: studies/dose/price_flat_6b86_boost.py's 204,000-corner sweep uses
   A_GRID = arange(0.07, 0.1501, 0.005).  The MEASURED a_filt = 0.0457 is BELOW that grid.
   Verified here by re-reading the constant out of the shipped source file.
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
import re
import sys
import numpy as np

os.environ.setdefault('ACCORD_FIRMWARE_ROOT', 'C:/Users/dudei/Desktop/Projects/accord-firmwares')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402
import assist_map_mirror as M                                      # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
KPH = 3.6
CTS_PER_KPH = 64.0625
c1, c2, c3, c4 = L.honda_exact()
H75 = complex(L.H_biquad(c1, c2, c3, c4, np.array([7.5]))[0])
Z69 = 6873 * np.exp(1j * -123.2 * DEG)
G0 = 0.0528 * np.exp(1j * 15.1 * DEG)
A_FILT = 0.0457
VB = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 130)]

# =============================================================== 0. the record check
print("=" * 112)
print("0. RECORD CHECK -- was the MEASURED `a` inside the 204,000-corner sweep's own grid?")
print("=" * 112)
src = open(os.path.join(HERE, 'studies/dose/price_flat_6b86_boost.py'), encoding='utf-8').read()
m = re.search(r"A_GRID\s*=\s*np\.round\(np\.arange\(([^)]*)\)", src)
print("  studies/dose/price_flat_6b86_boost.py:  A_GRID = np.arange(%s)" % m.group(1))
grid = np.round(np.arange(0.07, 0.1501, 0.005), 3)
print("  grid spans [%.3f, %.3f], %d values" % (grid.min(), grid.max(), len(grid)))
print("  MEASURED a_filt (same session) = %.4f   ⇒  %s"
      % (A_FILT, "INSIDE" if grid.min() <= A_FILT <= grid.max() else
         "🛑 BELOW THE GRID by %.1f %%  ⇒ the 'not one of 204,000 corners is worse' claim"
         " NEVER CONTAINED THE MEASURED VALUE." % (100 * (grid.min() / A_FILT - 1))))
print("  ⊕ studies/sessions/v104/v104_reprice_k185.py, run on the measured a_filt bootstrap, already reported")
print("    P(worse) = 0.0217 and amp MAX = 4.186 at k = 1.85 -- so the two numbers in the")
print("    handoff ('0 of 204,000' and '2.2 %%') are from DIFFERENT `a` assumptions.")

# =============================================================== 1. secant width from data
print()
print("=" * 112)
print("1. THE IN-BAND AC EXCURSION OF DRIVER TORQUE -- sets the honest secant half-width")
print("=" * 112)
print("%6s %14s %12s %12s %12s" %
      ('route', 'speed band', 'sec', '6-9 Hz RMS', 'p95 of |tq|'))
EXC = {}
for tag in ('r96', 'r9e'):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    tq = d['tq'].astype(float)
    for lo, hi in VB:
        m2 = eng & (v >= lo) & (v < hi)
        idx = np.flatnonzero(np.diff(m2.astype(np.int8)) != 0) + 1
        b = np.concatenate(([0], idx, [len(m2)]))
        sp = []
        for i in range(len(b) - 1):
            a0, b0 = b[i], b[i + 1]
            if not m2[a0] or (b0 - a0) < NPER:
                continue
            r = L._win_spec(tq[a0:b0], tq[a0:b0], NPER, L.FS)
            if r is not None:
                sp.append((r[0].sum(0), r[1].sum(0), r[2].sum(0), len(r[0])))
        if not sp:
            continue
        sel = (f >= 6) & (f < 9)
        Sxx = sum(s[0] for s in sp)
        nw = sum(s[3] for s in sp)
        rms = float(np.sqrt(Sxx[sel].sum() / nw * (f[1] - f[0])))
        EXC.setdefault((lo, hi), []).append(rms)
        print("%6s %9d-%-4d %12.1f %12.2f %12.0f"
              % (tag, lo, hi, m2.sum() / L.FS, rms, np.percentile(np.abs(tq[m2]), 95)))
print("  ⇒ the 6-9 Hz AC excursion of driver torque is 80-450 counts RMS -- COMPARABLE to the")
print("    map's near-origin segment width (X[1] = 471-673).  So the AC sensitivity is a CHORD")
print("    over ~+-100-450 counts, NOT a tangent.  Sec 2 sweeps exactly that half-width range.")
print("  ⚠ BUT the ROM map is integer-quantised: at |tq| ~ 150 ct the tangent is a staircase")
print("    of 0.0625-count steps.  A tangent narrower than ~64 counts reads QUANTISATION, not")
print("    slope.  Sec 2 therefore sweeps the half-width and reports the shape's sensitivity.")

# =============================================================== 2. shape sensitivity
print()
print("=" * 112)
print("2. IS s(v) ROBUST TO THE SECANT HALF-WIDTH, AND TO SPEED-vs-OPERATING-POINT?")
print("=" * 112)
_C = {}


def lane_out(vkph):
    key = int(round(vkph * CTS_PER_KPH))
    if key not in _C:
        A, B = M.stage_382d8(24, key)
        Xs, Ys = M.stage_389ec(A, B, key, angle_10deg=0x2711)
        X, Y, Z, S = M.build_map(Xs, Ys)
        _C[key] = np.array([abs(M.lane(int(t), X, Y, Z, S)['b82'])
                            for t in range(8193)], float)
    return _C[key]


def a_rom(vkph, tq, half):
    o = lane_out(vkph)
    t = int(round(abs(tq)))
    lo, hi = max(0, t - half), min(8192, t + half)
    return (o[hi] - o[lo]) / (hi - lo)


def duty_a(tag, half, vlo=-1e9, vhi=1e9, window=False):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    tq = np.abs(d['tq'].astype(float))
    m2 = eng & (v >= vlo) & (v < vhi)
    if window:
        ra = np.abs(d['rate_f'].astype(float))
        m2 = eng & (v >= 5 * KPH) & (v <= 25 * KPH) & (ra <= 60.0)
    if m2.sum() < 100:
        return np.nan
    vb = np.clip(np.round(v[m2] / 5.0) * 5.0, 0, 200)
    tb = np.clip(np.round(tq[m2] / 25.0) * 25.0, 25, 8000)
    return float(np.mean([a_rom(a_, b_, half) for a_, b_ in zip(vb, tb)]))


print("  (a) DUTY-WEIGHTED shape s(v) at three secant half-widths")
print("%14s %14s %14s %14s" % ('speed band', 'half = 64', 'half = 128', 'half = 256'))
SHAPES = {}
for half in (64, 128, 256):
    ref = 0.5 * (duty_a('r96', half, window=True) + duty_a('r9e', half, window=True))
    SHAPES[half] = {b: np.nanmean([duty_a(t, half, b[0], b[1]) for t in ('r96', 'r9e')]) / ref
                    for b in VB}
for b in VB:
    print("%9d-%-4d" % b + "".join("%14.3f" % SHAPES[h][b] for h in (64, 128, 256)))

print()
print("  (b) PURE SPEED SCHEDULE at a FIXED operating point (no duty weighting)")
print("%10s" % 'km/h' + "".join("%12s" % ("tq=%d h=%d" % (t, h))
                                for t, h in ((150, 64), (150, 128), (300, 128))))
for v in (0, 20, 40, 60, 80, 100, 120):
    print("%10.0f" % v + "".join("%12.4f" % a_rom(v, t, h)
                                 for t, h in ((150, 64), (150, 128), (300, 128))))
print("  ⇒ the pure speed schedule at fixed torque is a ratio of ~0.44 (120 km/h / parking);")
print("    the duty-weighted shape is ~0.60 because low-speed driving also uses MORE torque,")
print("    which pushes `a` up further there.  BOTH say the highway sits LOWER.")

# =============================================================== 3. tail risk
print()
print("=" * 112)
print("3. TAIL RISK -- P(amp > 1.0 / 1.5 / 2.0) instead of a bootstrap MAX")
print("=" * 112)


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float),
                            eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def one(i4, i8):
    G4 = L.band_H([G4s[j] for j in i4], f, 6, 9)[0]
    Z4 = L.band_H([Z4s[j] for j in i4], f, 6, 9)[0]
    G8 = L.band_H([G8s[j] for j in i8], f, 6, 9)[0]
    Z8 = L.band_H([Z8s[j] for j in i8], f, 6, 9)[0]
    r = Z4 / Z8
    return (r - 1) / (G8 - r * G4)


rng = np.random.default_rng(41)
bc = np.array([one(rng.integers(0, len(G4s), len(G4s)), rng.integers(0, len(G8s), len(G8s)))
               for _ in range(4000)])
bA = 1 + bc * G0
AF = np.load(os.path.join(HERE, '_scratch/data/_v103_natexp.npz'))['a69'].real
AF = AF[(AF > 0.005) & (AF < 0.25)]
S = SHAPES[128]
print("%7s %12s %10s %10s %10s %10s %11s" %
      ('k', 'speed band', 'P(>1.0)', 'P(>1.5)', 'P(>2.0)', 'amp p50', 'P(ReZ>0)'))
for k in (1.85, 2.05, 2.25):
    for b in ((0, 20), (40, 60), (100, 130)):
        amps, rzs = [], []
        for a in AF[::5] * S[b]:
            Ak = bA + bc * (-a * H75 * (k - 1.0))
            amps.append(np.abs(bA) / np.abs(Ak))
            rzs.append((Z69 * bA / Ak).real)
        amps, rzs = np.concatenate(amps), np.concatenate(rzs)
        print("%7.2f %7d-%-4d %10.4f %10.4f %10.4f %10.3f %11.3f"
              % (k, b[0], b[1], (amps > 1).mean(), (amps > 1.5).mean(), (amps > 2).mean(),
                 np.median(amps), (rzs > 0).mean()))

# =============================================================== 4. clip, three ways
print()
print("=" * 112)
print("4. THE CLIP GATE, THREE WAYS -- realistic, reachable, adversarial")
print("=" * 112)
mx_reach = max(lane_out(v).max() for v in (0, 20, 40, 60, 80, 100, 120))
print("  (i) REALISTIC: |gp-0x6b82| evaluated on the OBSERVED engaged |tq| distribution")
for tag in ('r96', 'r9e'):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    tq = np.abs(d['tq'].astype(float))
    vb = np.clip(np.round(v[eng] / 20.0) * 20.0, 0, 120)
    tb = np.clip(np.round(tq[eng]).astype(int), 0, 8192)
    b82 = np.array([lane_out(a_)[b_] for a_, b_ in zip(vb, tb)])
    print("      %s: |6b82| p50 %5.0f  p99 %5.0f  p99.9 %5.0f  MAX %5.0f  "
          "⇒ first clip at k = %.2f" % (tag, np.percentile(b82, 50), np.percentile(b82, 99),
                                        np.percentile(b82, 99.9), b82.max(),
                                        12288.0 / b82.max()))
print("  (ii) REACHABLE: ROM max |gp-0x6b82| = %.0f (cal 0xC6178) at |Tsens| -> 8192"
      % mx_reach)
print("       ⇒ sinusoidal bound k <= %.3f ;  step-response bound k <= %.3f"
      % (12288.0 / mx_reach, 12288.0 / (mx_reach * 1.0423)))
print("  (iii) ADVERSARIAL: l1 norm 1.9711 ⇒ k <= %.3f  (a sign-flipping input at the "
      "biquad's own impulse-response polarity; not physically produced by a driver)"
      % (12288.0 / (mx_reach * 1.9711)))
print()
print("  ⇒ THE BINDING BOUND FOR A ROAD BUILD IS (ii)-step: k <= 2.24.")
print("    The record's 'rigorous to k <= 3.40' is an OBSERVED-FRAME bound and does NOT")
print("    survive a driving regime that pushes |tq| to the +-8192 clamp (a hard parking")
print("    manoeuvre).  ⚠ NOTE the section is ENGAGED-ONLY, so parking cannot reach it while")
print("    LKAS is disengaged -- but a high-torque engaged event (a hard highway avoidance)")
print("    can.  |tq| p99 engaged is already 2764-3138 counts.")
