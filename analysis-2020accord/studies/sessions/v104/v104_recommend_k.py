"""THE RECOMMENDATION: what k should 0xC60B4 carry, given the speed schedule?

Inputs, all reproduced upstream in this session:
  K = a.(k_cross-1) = 0.02507   [studies/sessions/v104/v104_dose_vs_speed.py sec 1; verified constant to 4 s.f.]
  a_filt = 0.0457 [-0.0047, 0.0816]   [studies/sessions/v104/v103_filter_natural_experiment.py, REPRODUCED bit-exact]
  s(v) from the ROM assist map + the measured (v, |tq|) joint duty   [studies/sessions/v104/v104_dose_vs_speed.py sec 2]
  the direct a_filt speed split                                       [studies/sessions/v104/v104_afilt_by_speed.py]

Three explicit hypotheses, priced side by side.  No single number is presented as THE answer.
  H0  NO speed dependence          a(v) = 0.0457 everywhere
  H1  ROM SHAPE                    a(v) = 0.0457 . s(v)          s(hwy) = 0.60
  H2  DIRECT SPLIT (underpowered)  a(hwy) = 0.0173               ratio 0.39
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

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
c1, c2, c3, c4 = L.honda_exact()
H75 = complex(L.H_biquad(c1, c2, c3, c4, np.array([7.5]))[0])
Z69 = 6873 * np.exp(1j * -123.2 * DEG)
G0 = 0.0528 * np.exp(1j * 15.1 * DEG)
A_FILT = 0.0457

# --- identification (identical to the shipped scripts) ---------------------------------
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


c0 = one(range(len(G4s)), range(len(G8s)))
A0 = 1 + c0 * G0
rng = np.random.default_rng(41)
bc = np.array([one(rng.integers(0, len(G4s), len(G4s)), rng.integers(0, len(G8s), len(G8s)))
               for _ in range(4000)])
bA = 1 + bc * G0
AF = np.load('_scratch/data/_v103_natexp.npz')['a69'].real
AF = AF[(AF > 0.005) & (AF < 0.25)]

# exposure shares and ROM shape, from studies/sessions/v104/v104_dose_vs_speed.py sec 2/3.3
BANDS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 130)]
S_ROM = {(0, 20): 2.330, (20, 40): 1.527, (40, 60): 0.925,
         (60, 80): 0.647, (80, 100): 0.612, (100, 130): 0.599}
EXPO = {(0, 20): 0.170, (20, 40): 0.191, (40, 60): 0.206,
        (60, 80): 0.171, (80, 100): 0.135, (100, 130): 0.127}


def metrics(k, s, thin=7):
    """Joint (c,A0) x a_filt bootstrap at dose k and speed-shape s."""
    amps, rzs = [], []
    for a in AF[::thin] * s:
        Ak = bA + bc * (-a * H75 * (k - 1.0))
        amps.append(np.abs(bA) / np.abs(Ak))
        rzs.append((Z69 * bA / Ak).real)
    amps, rzs = np.concatenate(amps), np.concatenate(rzs)
    return dict(amp50=np.median(amps), amp95=np.percentile(amps, 95), ampmax=amps.max(),
                pworse=(amps > 1).mean(), ppos=(rzs > 0).mean(), rz50=np.median(rzs))


print("=" * 112)
print("1. THE THREE HYPOTHESES, AT THE HIGHWAY (80-130 km/h)")
print("=" * 112)
K = 0.02507
HYP = [('H0  no speed dependence', 1.000, A_FILT),
       ('H1  ROM shape (s = 0.60)', 0.605, A_FILT * 0.605),
       ('H2  direct split (0.39x)', 0.394, A_FILT * 0.394)]
print("%28s %10s %10s %12s %14s" % ('hypothesis', 's(hwy)', 'a(hwy)', 'k_cross', 'k=1.85 verdict'))
for nm, s, a in HYP:
    kc = 1 + K / a
    print("%28s %10.3f %10.4f %12.3f %14s"
          % (nm, s, a, kc, "CLEARS" if 1.85 >= kc else "SHORT by %.3f" % (kc - 1.85)))

print()
print("=" * 112)
print("2. DOSE SWEEP -- worst speed band and exposure-weighted, under H1 (the ROM shape)")
print("=" * 112)
KS = [1.50, 1.70, 1.85, 1.95, 2.05, 2.15, 2.25, 2.33, 2.50]
print("%7s %10s %10s %10s %10s %11s %11s %11s" %
      ('k', 'hwy amp50', 'hwy P(>0)', 'hwy ReZ', 'hwy Pworse', 'town amp50', 'town ReZ',
       'exp-w amp50'))
for k in KS:
    hw = metrics(k, S_ROM[(100, 130)])
    tw = metrics(k, S_ROM[(0, 20)])
    ew = sum(EXPO[b] * metrics(k, S_ROM[b])['amp50'] for b in BANDS)
    print("%7.2f %10.3f %10.3f %+10.0f %10.4f %11.3f %+11.0f %11.3f"
          % (k, hw['amp50'], hw['ppos'], hw['rz50'], hw['pworse'], tw['amp50'], tw['rz50'], ew))

print()
print("[2.1] SAME SWEEP under H0 (no speed dependence) -- the case k = 1.85 was sized for")
print("%7s %10s %10s %10s %10s" % ('k', 'amp50', 'P(ReZ>0)', 'ReZ p50', 'P(worse)'))
for k in KS:
    m = metrics(k, 1.0)
    print("%7.2f %10.3f %10.3f %+10.0f %10.4f" % (k, m['amp50'], m['ppos'], m['rz50'],
                                                  m['pworse']))

print()
print("[2.2] WORST SPEED BAND at each k, under H1 -- 'worst' = highest P(worse)")
print("%7s %14s %12s %12s %12s" % ('k', 'worst band', 'P(worse)', 'amp p95', 'amp MAX'))
for k in KS:
    rows = [(metrics(k, S_ROM[b])['pworse'], b, metrics(k, S_ROM[b])) for b in BANDS]
    pw, b, m = max(rows, key=lambda r: r[0])
    print("%7.2f %9d-%-4d %12.4f %12.3f %12.3f" % (k, b[0], b[1], pw, m['amp95'], m['ampmax']))

# ------------------------------------------------------------------ 3. the hard clip bound
print()
print("=" * 112)
print("3. THE RIGOROUS CLIP BOUND -- ROM-reachable |gp-0x6b82| x the biquad's TRUE peak gain")
print("=" * 112)
nimp = 4000
imp = np.zeros(nimp)
imp[0] = 1.0
b = np.array([c4, c4 * c3, c4])
aa = np.array([1.0, c1, c2])
h = np.zeros(nimp)
y1 = y2 = x1 = x2 = 0.0
for n in range(nimp):
    x0 = imp[n]
    y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - aa[1] * y1 - aa[2] * y2
    h[n] = y0
    x2, x1 = x1, x0
    y2, y1 = y1, y0
l1 = np.abs(h).sum()
print("  biquad impulse response: l1 norm (Sum |h[n]|) = %.4f    <- the EXACT worst-case peak" % l1)
print("     gain for any bounded input; |H(e^jw)| <= 1.000031 is only the sinusoidal bound.")
print("  peak of the step response = %.4f" % np.abs(np.cumsum(h)).max())
CEIL_6B82 = 5274.0        # cal 0xC6178 -- the ROM-reachable ceiling on |gp-0x6b82| (sec 5 upstream)
CLAMP = 12288.0
print("  ROM-reachable max |gp-0x6b82| = %.0f  (cal 0xC6178, integer-exact over 0-200 km/h)"
      % CEIL_6B82)
print("  ⇒ RIGOROUS clip-free bound:  k <= %.4f / %.4f = %.3f   (worst case, l1)"
      % (CLAMP / CEIL_6B82, l1, CLAMP / (CEIL_6B82 * l1)))
print("  ⇒ sinusoidal-only bound:     k <= %.3f" % (CLAMP / (CEIL_6B82 * 1.000031)))
print("  (The record's 'clean to k <= 3.40' and 'first clip at k = 10.76' are OBSERVED-frame")
print("   bounds, not reachability bounds.  The reachability bound is TIGHTER and is the one")
print("   that survives an unseen driving regime.)")

# ------------------------------------------------------------------ 4. bytes
print()
print("=" * 112)
print("4. 0xC60B4 LITTLE-ENDIAN FLOAT32 BYTES for candidate doses")
print("=" * 112)
stock = float(np.frombuffer(bytes.fromhex('3a3b513f'), '<f4')[0])
print("%8s %14s %14s %10s" % ('k', 'c4 value', 'LE bytes', 'exact k'))
for k in (1.00, 1.85, 1.95, 2.00, 2.05, 2.10, 2.15, 2.20, 2.25, 2.30, 2.33):
    v = np.float32(np.float32(stock) * np.float32(k))
    print("%8.2f %14.6f %14s %10.7f" % (k, float(v), v.tobytes().hex(), float(v) / stock))
print()
print("  (stock 0xC60B4 = 3a3b513f = %.6f;  V104 as built = fc89c13f = %.6f, ratio %.7f)"
      % (stock, float(np.frombuffer(bytes.fromhex('fc89c13f'), '<f4')[0]),
         float(np.frombuffer(bytes.fromhex('fc89c13f'), '<f4')[0]) / stock))

# ------------------------------------------------------------------ 5. what k costs elsewhere
print()
print("=" * 112)
print("5. WHAT RAISING k COSTS IN THE OTHER BANDS  (point estimate, a = a_filt, no speed shape)")
print("=" * 112)
BB = [(2, 4), (4, 6), (6, 9), (9, 13), (15, 22), (21, 22.5), (22, 26), (26, 31)]


def ident_band(lo, hi):
    G4 = L.band_H(G4s, f, lo, hi)[0]
    Z4 = L.band_H(Z4s, f, lo, hi)[0]
    G8 = L.band_H(G8s, f, lo, hi)[0]
    Z8 = L.band_H(Z8s, f, lo, hi)[0]
    r = Z4 / Z8
    c = (r - 1) / (G8 - r * G4)
    return c, G4, 1 + c * G4


print("%10s" % 'band' + "".join("%12s" % ("k=%.2f" % k) for k in (1.00, 1.85, 2.05, 2.25)))
for lo, hi in BB:
    cb_, Gb_, Ab_ = ident_band(lo, hi)
    Hb = complex(L.H_biquad(c1, c2, c3, c4, np.array([0.5 * (lo + hi)]))[0])
    row = []
    for k in (1.00, 1.85, 2.05, 2.25):
        Ak = Ab_ + cb_ * (-A_FILT * Hb * (k - 1.0))
        row.append(abs(Ab_) / abs(Ak))
    print("%5.1f-%-4.1f" % (lo, hi) + "".join("%12.3f" % r for r in row))
print("  values are AMPLIFICATION RATIO vs today (<1 better, >1 worse).")
print("  🛑 the 15-26 Hz rows sit above the ~13 Hz |Z| roll-off open item -- treat as INDICATIVE.")
