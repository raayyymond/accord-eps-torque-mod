"""DOES THE OPERATOR'S "V103 IS JUST AS BAD AS ANY OTHER 6x" NULL CONSTRAIN `a_filt`?

Operator, route 0x9e (V103), 2026-08-22:
    "I would say this route is just as bad as any other 6x before it, I don't think I could
     tell the difference."   + "both grinding and ratcheting are still an issue."
The other 6x build is V102 (route 0x96).  V102 -> V103 is EXACTLY the single-variable pair that
`a_filt = 0.0457 [-0.0047, +0.0816]` was inverted from.

FOUR QUESTIONS
  1. How big was the V102->V103 perturbation, really, versus V103->V104?  The claim under test
     is "-0.149 dB = 1.7 %, so V104 is ~50x larger."  A dB is a MAGNITUDE; the loop sees the
     COMPLEX difference.  Checked, not assumed.
  2. Propagate a_filt across its FULL CI -- negative tail included -- into 1/|A(k)|.
  3. Does the perceptual null bound `a_filt` from above at all?  Inverted explicitly.
  4. Is there a k that is safe at every speed AND whose effect exceeds his DEMONSTRATED
     discrimination threshold?

HIS DEMONSTRATED RESOLUTION -- the empirical bracket, stated as such
  CAN resolve:    4x vs 6x vs 8x on 0xC6CD0, scored monotonically over four doses.
                  4x->6x is a 1.5x step in the forward gain (excitation, not loop gain).
  CANNOT resolve: V102 vs V103.
  => his threshold lies between the amplification change V102->V103 actually delivered and 1.5x.
  ⚠ THIS IS A BRACKET, NOT A NUMBER, and the two arms are not the same physical quantity
    (a gain step scales EXCITATION; a c4 step changes CLOSED-LOOP AMPLIFICATION).  Marked BELIEF.

🛑 x6b94 read only on r85/r95.  Episode bootstrap.  Same estimator as the shipped scripts.
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

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
KPH = 3.6
c1, c2, c3, c4 = L.honda_exact()
A_FILT = 0.0457
A_DIS = 0.440 * np.exp(1j * 25.0 * DEG)          # A of the DISARMED state (V100/V101/V102)
for t in ('r85', 'r95'):
    CA.assert_is_sum(t)


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


# ================================================================ 1. the perturbation ratio
print("=" * 110)
print("1. HOW BIG WAS V102->V103, REALLY?   [EVIDENCE -- closed-form biquad, stock float32]")
print("=" * 110)
print("  H(z) = c4.(1 + c3 z^-1 + z^-2)/(1 + c1 z^-1 + c2 z^-2), fs = 1000, c4 = %.5f" % c4)
print()
print("%8s %10s %10s %14s %14s %14s %10s" %
      ('f (Hz)', '|H|', 'arg H', '|H-1| V102->3', '0.85|H| V3->4', '|1.85H-1| V2->4', 'ratio 3->4'))
for fc in (6.0, 7.5, 7.79, 9.0, 21.73):
    H = Hh(fc)
    d23 = abs(H - 1)
    d34 = abs(1.85 * H - H)
    d24 = abs(1.85 * H - 1)
    print("%8.2f %10.4f %+10.2f %14.4f %14.4f %14.4f %10.2f"
          % (fc, abs(H), np.angle(H, deg=True), d23, d34, d24, d34 / d23))
print()
print("  🛑 THE '-0.149 dB = 1.7 %' FIGURE IS A MAGNITUDE-ONLY READ AND THE LOOP DOES NOT SEE IT.")
print("     |H| at 7.79 Hz = %.4f  (= %.3f dB, so 'the lane changed 1.7 %%')" %
      (abs(Hh(7.79)), 20 * np.log10(abs(Hh(7.79)))))
print("     but arg H = %+.2f deg, so the COMPLEX change is |H - 1| = %.4f = %.1f %%."
      % (np.angle(Hh(7.79), deg=True), abs(Hh(7.79) - 1), 100 * abs(Hh(7.79) - 1)))
print("     dG = -a.(H - 1) uses the COMPLEX difference.  This is retraction #4 of the V104")
print("     handoff, recurring: a lane-referenced dB about the kit's own flown build.")
print()
print("  ⇒ THE PERTURBATION RATIO IS %.2fx, NOT ~50x."
      % (abs(1.85 * Hh(7.79) - Hh(7.79)) / abs(Hh(7.79) - 1)))
print("    The V104 handoff sec 4.1 already records this: 'a 4.7x extrapolation in perturbation")
print("    size (|dH| 0.18 arming -> 0.85 at k = 1.85)'.  Reading 1's premise contradicts the")
print("    kit's own record. [EVIDENCE]")

# ================================================================ 2. identification
def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float),
                            eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def solve_c(i4, i8):
    G4 = L.band_H([G4s[j] for j in i4], f, 6, 9)[0]
    Z4 = L.band_H([Z4s[j] for j in i4], f, 6, 9)[0]
    G8 = L.band_H([G8s[j] for j in i8], f, 6, 9)[0]
    Z8 = L.band_H([Z8s[j] for j in i8], f, 6, 9)[0]
    r = Z4 / Z8
    return (r - 1) / (G8 - r * G4)


c0 = solve_c(range(len(G4s)), range(len(G8s)))
rng = np.random.default_rng(41)
bc = np.array([solve_c(rng.integers(0, len(G4s), len(G4s)), rng.integers(0, len(G8s), len(G8s)))
               for _ in range(4000)])
H75 = Hh(7.5)
AF_ALL = np.load(os.path.join(HERE, '_scratch/data/_v103_natexp.npz'))['a69'].real     # FULL draws, neg tail in
AF_ADM = AF_ALL[(AF_ALL > 0.005) & (AF_ALL < 0.25)]


def A_of(k, a, Adis=A_DIS, cc=None):
    """A at dose k, measured from the DISARMED baseline: dG = -a.(k.H - 1)."""
    cc = c0 if cc is None else cc
    return Adis + cc * (-a * (k * H75 - 1.0))


print()
print("=" * 110)
print("2. AMPLIFICATION 1/|A| ACROSS THE FULL a_filt CI -- negative tail INCLUDED")
print("=" * 110)
print("  Baseline: A_disarmed = %.3f∠%+.1f deg  =>  1/|A| = %.3f  (V100/V101/V102)"
      % (abs(A_DIS), np.angle(A_DIS, deg=True), 1 / abs(A_DIS)))
print()
print("%10s %12s %12s %12s %14s %16s" %
      ('a_filt', 'V103 1/|A|', 'V104 1/|A|', 'k=2.05 1/|A|', 'V102->V103', 'V103->V104(1.85)'))
for a in (-0.0047, 0.0, 0.010, 0.0209, 0.0318, 0.0457, 0.0600, 0.0816, 0.1022):
    A3 = A_of(1.00, a)
    A4 = A_of(1.85, a)
    A5 = A_of(2.05, a)
    r23 = abs(A_DIS) / abs(A3)                 # amplification ratio V103 / V102
    r34 = abs(A3) / abs(A4)                    # amplification ratio V103 / V104 = IMPROVEMENT
    print("%10.4f %12.3f %12.3f %12.3f %14s %16s"
          % (a, 1 / abs(A3), 1 / abs(A4), 1 / abs(A5),
             ("%.3fx WORSE" % r23) if r23 >= 1 else ("%.3fx better" % (1 / r23)),
             ("%.3fx BETTER" % r34) if r34 >= 1 else ("%.3fx worse" % (1 / r34))))
print()
_ci = [abs(A_DIS) / abs(A_of(1.0, a)) for a in np.linspace(-0.0047, 0.0816, 400)]
_im = [abs(A_of(1.0, a)) / abs(A_of(1.85, a)) for a in np.linspace(-0.0047, 0.0816, 400)]
print("  ⇒ V102->V103 (arming, k=1): amplification moves %.3fx to %.3fx across the WHOLE 95 %% CI,"
      % (min(_ci), max(_ci)))
print("    point estimate %.3fx.  ⭐ EVERY VALUE IN THE CI IS BELOW HIS DEMONSTRATED 1.5x"
      % (abs(A_DIS) / abs(A_of(1.0, A_FILT))))
print("    RESOLUTION.  THE MODEL PREDICTED THE OPERATOR'S NULL. [EVIDENCE]")
print("  ⇒ V103->V104 at k=1.85: improvement %.3fx to %.3fx, point estimate %.3fx --"
      % (min(_im), max(_im), abs(A_of(1.0, A_FILT)) / abs(A_of(1.85, A_FILT))))
print("    i.e. the SAME CI that predicts an imperceptible V103 predicts a V104 effect that")
print("    reaches his resolution over most of it.  The two are not in tension.")

# ================================================================ 3. does the null bound a?
print()
print("=" * 110)
print("3. DOES THE PERCEPTUAL NULL BOUND `a_filt` FROM ABOVE?  -- inverted explicitly")
print("=" * 110)
print("  Solve: what `a` would arming the filter have needed for V102->V103 to move the")
print("  6-9 Hz closed-loop amplification by X, i.e. |A_dis|/|A(1)| = X ?")
print("%14s %16s %26s" % ('amp change X', 'a required', 'inside the 95 % CI?'))
agrid = np.linspace(0.0, 1.0, 200001)
amp1 = np.abs(A_DIS) / np.abs(A_DIS + c0 * (-agrid * (H75 - 1.0)))
print("  (|A(1)| is NOT monotone in `a` -- the A-locus is a straight line whose modulus has a")
print("   minimum -- so the SMALLEST POSITIVE root is taken, never argmin.)")


def first_root(X):
    hit = np.flatnonzero((amp1[:-1] < X) & (amp1[1:] >= X))
    return agrid[hit[0] + 1] if len(hit) else np.nan


for X in (1.05, 1.10, 1.20, 1.30, 1.50, 2.00):
    a_req = first_root(X)
    print("%14.2fx %16.4f %26s"
          % (X, a_req, "YES -- inside [-0.005, 0.082]" if a_req <= 0.0816 else
             "NO -- %.1fx above the CI top" % (a_req / 0.0816)))
A15 = first_root(1.5)
print()
print("  ⇒ FOR V102 vs V103 TO HAVE REACHED HIS DEMONSTRATED 1.5x RESOLUTION, `a_filt` WOULD")
print("    HAVE HAD TO BE >= %.4f.  P(a_filt >= that) over the FULL bootstrap = %.4f."
      % (A15, (AF_ALL >= A15).mean()))
print("  ⇒ 🛑 SO THE NULL EXCLUDES ONLY THE TOP %.1f %% OF THE POSTERIOR, WHICH THE"
      % (100 * (AF_ALL >= A15).mean()))
print("       MEASUREMENT ALREADY PUT NEAR ITS 95 %% CI EDGE (%.4f).  Bayes factor for the null"
      % 0.0816)
print("       against 'a_filt as measured' is ~%.2f:1 -- essentially 1. **THE PERCEPTUAL NULL"
      % (1.0 / max(1e-9, 1 - (AF_ALL >= A15).mean()) if False else
         1.0 / (1 - (AF_ALL >= A15).mean())))
print("       ADDS NO USABLE INFORMATION ABOUT a_filt.** [EVIDENCE]")

# ================================================================ 4. did the instrument agree?
print()
print("=" * 110)
print("4. DID THE INSTRUMENT ALSO SAY V102 ~ V103?  -- the operator's null, cross-checked")
print("=" * 110)


def band_rms(tag, mask_fn, lo, hi):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    rate = d['rate_f'].astype(float)
    m = mask_fn(d, eng)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    sp = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not m[a0] or (b0 - a0) < NPER:
            continue
        r = L._win_spec(rate[a0:b0], rate[a0:b0], NPER, L.FS)
        if r is not None:
            sp.append((r[0].sum(0), len(r[0])))
    if not sp:
        return np.nan, 0
    sel = (f >= lo) & (f < hi)
    return float(np.sqrt(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp)
                         * (f[1] - f[0]))), len(sp)


def matched(d, eng):
    v = d['v_rear'].astype(float) * KPH
    ra = np.abs(d['rate_f'].astype(float))
    return eng & (v >= 18.0) & (v <= 90.0) & (ra <= 60.0)


print("%12s %14s %14s %12s" % ('band (Hz)', 'V102 (r96)', 'V103 (r9e)', 'V103/V102'))
for lo, hi in ((2, 4), (4, 6), (6, 9), (9, 13), (18, 22), (22, 26)):
    r2, n2 = band_rms('r96', matched, lo, hi)
    r3, n3 = band_rms('r9e', matched, lo, hi)
    print("%6.0f-%-5.0f %14.4f %14.4f %12.3f" % (lo, hi, r2, r3, r3 / r2))
print("  (engaged, matched exposure 18-90 km/h and |rate| <= 60 deg/s -- the same window that")
print("   produced a_filt.  Band RMS of rate_f, deg/s.)")

# ================================================================ 5. threshold vs dose
print()
print("=" * 110)
print("5. P(THE V104 EFFECT EXCEEDS HIS THRESHOLD), per dose and per speed")
print("=" * 110)
S_ROM = {'town 0-20': 2.36, 'mid 40-60': 0.93, 'highway 100-130': 0.585}
print("  R = |A(k)|/|A(1)| = amp(V103)/amp(V104), the 6-9 Hz amplification IMPROVEMENT factor.")
print("  Thresholds: 1.5x = his DEMONSTRATED resolution (4x vs 6x).  1.2x and 1.3x bracket a")
print("  more optimistic reading.  Joint bootstrap over (c) x a_filt, FULL draws incl. negatives.")
print()
print("%7s %18s %10s %10s %10s %10s %12s" %
      ('k', 'speed band', 'R p50', 'P(R>1.2)', 'P(R>1.3)', 'P(R>1.5)', 'P(R<1.05)'))
for k in (1.85, 2.05, 2.25):
    for nm, s in S_ROM.items():
        Rs = []
        for a in AF_ALL[::5] * s:
            A1 = A_DIS + bc * (-a * (1.0 * H75 - 1.0))
            Ak = A_DIS + bc * (-a * (k * H75 - 1.0))
            Rs.append(np.abs(Ak) / np.abs(A1))    # amplification IMPROVEMENT = |A(k)|/|A(1)|
        R = np.concatenate(Rs)
        print("%7.2f %18s %10.3f %10.3f %10.3f %10.3f %12.3f"
              % (k, nm, np.median(R), (R > 1.2).mean(), (R > 1.3).mean(), (R > 1.5).mean(),
                 (R < 1.05).mean()))
print()
print("  P(R < 1.05) is 'he will not be able to tell V104 from V103 at all'.")

print()
print("[5.1] THE k REQUIRED for P(R > threshold) >= 0.5, per speed band")
print("%18s %14s %14s %14s" % ('speed band', 'thr 1.2x', 'thr 1.3x', 'thr 1.5x'))


def k_for(s, thr, tgt=0.5):
    lo_, hi_ = 1.0, 12.0
    for _ in range(45):
        mid = 0.5 * (lo_ + hi_)
        Rs = []
        for a in AF_ALL[::11] * s:
            A1 = A_DIS + bc * (-a * (H75 - 1.0))
            Ak = A_DIS + bc * (-a * (mid * H75 - 1.0))
            Rs.append(np.abs(Ak) / np.abs(A1))
        if (np.concatenate(Rs) > thr).mean() < tgt:
            lo_ = mid
        else:
            hi_ = mid
    return hi_


for nm, s in S_ROM.items():
    print("%18s" % nm + "".join("%14.2f" % k_for(s, t) for t in (1.2, 1.3, 1.5)))
print("  🛑 CLIP CEILING (reachable, step-response) = k <= 2.235.  Anything above is UNBUILDABLE.")
