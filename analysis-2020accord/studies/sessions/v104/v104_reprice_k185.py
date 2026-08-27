"""RE-PRICE the flat c4 boost on the MEASURED a_filt, centred on the operator's k = 1.85,
   with the two-regime SATURATION MIXTURE.

WHAT CHANGED SINCE studies/dose/price_flat_6b86_boost.py
-------------------------------------------
1. `a` is no longer the budget-closure 0.098.  `studies/sessions/v104/v103_filter_natural_experiment.py` measures the
   FILTER-BORNE fraction directly off the flown V102->V103 single-variable pair:
       a_filt = 0.0457  [-0.0047, 0.0816],  P(a>0) = 0.957,  Im/Re residual -3.1 %
   That is the right number for a c4 edit: arming the filter and scaling c4 are the same KIND of
   perturbation, so the inversion measures exactly the quantity that responds.
2. The dose is k = 1.85 (operator ruling), not 1.35.
3. SATURATION IS MODELLED, not assumed away.  In a frame where gp-0x6b86 sits on its +-12288
   clamp the filtered path's INCREMENTAL gain is 0, so that frame runs the NULL -- the direction
   GATE2 refuted.  With clip duty d (and stock duty d0):
       dG(k, d) = -a_filt.H . [ (1-d).k - (1-d0) ]
   => break-even at d* = 1 - (1-d0)/k.  Above d*, dG flips into the refuted null direction.
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
import numpy as np
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
c1, c2, c3, c4 = L.honda_exact()
A_FILT = 0.0457                       # MEASURED, studies/sessions/v104/v103_filter_natural_experiment.py sec 4
A_FILT_CI = (-0.0047, 0.0816)
A_CLOSURE = 0.098                     # GATE2 2.2 budget closure, for comparison only
KS = np.round(np.arange(1.00, 2.501, 0.05), 2)
BANDS = [(2, 4), (4, 6), (6, 9), (9, 13), (15, 22), (18, 22), (21, 22.5), (22, 26), (26, 31)]


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float), eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def ident(lo, hi, nboot=3000, seed=41):
    def one(i4, i8):
        G4 = L.band_H([G4s[j] for j in i4], f, lo, hi)[0]
        Z4 = L.band_H([Z4s[j] for j in i4], f, lo, hi)[0]
        G8 = L.band_H([G8s[j] for j in i8], f, lo, hi)[0]
        Z8 = L.band_H([Z8s[j] for j in i8], f, lo, hi)[0]
        r = Z4 / Z8
        c = (r - 1) / (G8 - r * G4)
        return c, G4, 1 + c * G4, Z4
    pt = one(range(len(G4s)), range(len(G8s)))
    rng = np.random.default_rng(seed)
    n4, n8 = len(G4s), len(G8s)
    bs = np.array([one(rng.integers(0, n4, n4), rng.integers(0, n8, n8)) for _ in range(nboot)])
    return pt, bs


ID = {b: ident(*b) for b in BANDS}
Z9E = {(2, 4): 1405 * np.exp(1j * -23.9 * DEG), (4, 6): 2413 * np.exp(1j * -68.1 * DEG),
       (6, 9): 6873 * np.exp(1j * -123.2 * DEG), (9, 13): 4931 * np.exp(1j * -172.2 * DEG),
       (15, 22): 1379 * np.exp(1j * 108.6 * DEG), (22, 26): 1168 * np.exp(1j * 96.8 * DEG)}

print("=" * 104)
print("1. DOSE DELIVERED -- measured a_filt vs the budget-closure a, at 7.5 Hz")
print("=" * 104)
print("%8s %14s %14s %14s" % ('k', 'dG @ a=0.098', 'dG @ a_filt', 'ratio'))
for k in (1.25, 1.35, 1.50, 1.70, 1.85, 2.00):
    d1 = (k - 1) * A_CLOSURE * abs(Hh(7.5))
    d2 = (k - 1) * A_FILT * abs(Hh(7.5))
    print("%8.2f %14.4f %14.4f %14.2f" % (k, d1, d2, d2 / d1))
print("  => k = 1.85 at the MEASURED a_filt delivers dG = %.4f, vs %.4f for k = 1.35 at the"
      % (0.85 * A_FILT * abs(Hh(7.5)), 0.35 * A_CLOSURE * abs(Hh(7.5))))
print("     assumed a.  The operator's dose lands just PAST my earlier recommendation.")

# ---------------------------------------------------------------- 2. the k = 1.85 rows
print()
print("=" * 104)
print("2. THE k = 1.85 ROWS -- everything, on a_filt = %.4f" % A_FILT)
print("=" * 104)
print("%10s %10s %11s %9s %11s %12s %12s" %
      ('band', '|G|/|G0|', 'Re(dG.Z)', '|A(k)|', 'amp ratio', 'Re Z base', 'Re Z @1.85'))
for b in BANDS:
    fc = 0.5 * (b[0] + b[1])
    c, G0, A0, Z4 = ID[b][0]
    Z1 = Z9E.get(b, Z4)
    dG = 0.85 * (-A_FILT * Hh(fc))
    Ak = A0 + c * dG
    print("%5.1f-%-4.1f %10.3f %+11.1f %9.3f %11.3f %+12.0f %+12.0f" %
          (b[0], b[1], abs(G0 + dG) / abs(G0), (dG * Z1).real, abs(Ak), abs(A0) / abs(Ak),
           Z1.real, (Z1 * A0 / Ak).real))

print()
print("[2.1] 6-9 Hz dose curve on a_filt (compare: on a = 0.098 the ReZ zero crossing was k = 1.256)")
b = (6, 9)
c, G0, A0, Z4 = ID[b][0]
G0 = 0.0528 * np.exp(1j * 15.1 * DEG)
A0 = 1 + c * G0
Z1 = Z9E[b]
print("%6s %9s %10s %9s %9s %11s %11s" %
      ('k', 'c4', '|G|/|G0|', '|A|', '1/|A|', 'amp ratio', 'Re Z(k)'))
for k in KS:
    dG = (k - 1) * (-A_FILT * Hh(7.5))
    Ak = A0 + c * dG
    print("%6.2f %9.5f %10.3f %9.3f %9.2f %11.3f %+11.0f" %
          (k, k * c4, abs(G0 + dG) / abs(G0), abs(Ak), 1 / abs(Ak),
           abs(A0) / abs(Ak), (Z1 * A0 / Ak).real))

# ---------------------------------------------------------------- 3. saturation mixture
print()
print("=" * 104)
print("3. THE SATURATION MIXTURE -- expected |A| and worst corner as a function of (k, clip duty)")
print("=" * 104)
print("  In a clipped frame the filtered path's incremental gain is 0 => that frame runs the NULL.")
print("  dG(k,d) = -a_filt.H.[(1-d).k - (1-d0)] ;  break-even  d* = 1 - (1-d0)/k")
print()
print("  BREAK-EVEN CLIP DUTY d* (the number that is the build gate):")
print("%10s %12s %12s %12s" % ('k', 'd0 = 0.00', 'd0 = 0.05', 'd0 = 0.10'))
for k in (1.25, 1.35, 1.50, 1.70, 1.85, 2.00, 2.50):
    print("%10.2f %12.3f %12.3f %12.3f" % (k, 1 - 1 / k, 1 - 0.95 / k, 1 - 0.90 / k))

bs = ID[(6, 9)][1]
bc, bA = bs[:, 0], bs[:, 2]
try:
    AF = np.load('_scratch/data/_v103_natexp.npz')['a69'].real
    AF = AF[(AF > 0.005) & (AF < 0.25)]        # keep physically admissible draws
    print("\n  a_filt bootstrap draws kept: %d of 3000 (0.005 < a < 0.25), p50 %.4f, p5/p95 %.4f/%.4f"
          % (len(AF), np.median(AF), np.percentile(AF, 5), np.percentile(AF, 95)))
except Exception as exc:                       # pragma: no cover
    AF = np.array([A_FILT])
    print("  (a_filt draws unavailable: %s)" % exc)

H75 = Hh(7.5)
print()
print("[3.1] k = 1.85: amp ratio (<1 = better) vs clip duty.  Joint bootstrap over (c, A0, a_filt).")
print("%10s %11s %11s %11s %11s %12s" %
      ('clip duty', 'amp p50', 'amp p95', 'amp MAX', 'P(worse)', 'Re Z p50'))
for d in (0.00, 0.10, 0.20, 0.30, 0.40, 0.4595, 0.50, 0.60, 0.75, 1.00):
    vals, rez = [], []
    for a in AF[::7]:
        dG = -a * H75 * ((1 - d) * 1.85 - 1.0)
        Ak = bA + bc * dG
        vals.append(np.abs(bA) / np.abs(Ak))
        rez.append((Z1 * bA / Ak).real)
    v = np.concatenate(vals)
    r = np.concatenate(rez)
    print("%10.3f %11.3f %11.3f %11.3f %11.4f %+12.0f" %
          (d, np.median(v), np.percentile(v, 95), v.max(), (v > 1).mean(), np.median(r)))

print()
print("[3.2] the (k, clip duty) surface -- median amp ratio.  '>1' = the lever has INVERTED.")
DUTIES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75)
print("%8s" % 'k' + "".join("%9s" % ("d=%.2f" % d) for d in DUTIES))
for k in (1.25, 1.50, 1.85, 2.00, 2.50):
    row = []
    for d in DUTIES:
        vals = []
        for a in AF[::15]:
            dG = -a * H75 * ((1 - d) * k - 1.0)
            Ak = bA + bc * dG
            vals.append(np.abs(bA) / np.abs(Ak))
        row.append(np.median(np.concatenate(vals)))
    print("%8.2f" % k + "".join("%9.3f" % v for v in row))
print("  Read DOWN a column: larger k tolerates more clipping.  Read ACROSS a row: the lever")
print("  degrades to 1.000 at d* and INVERTS beyond it.")

# ---------------------------------------------------------------- 4. secondary hazards
print()
print("=" * 104)
print("4. SECONDARY HAZARDS -- does anything become binding between k = 1.7 and k = 1.85?")
print("=" * 104)
fgrid = np.linspace(0.1, 500, 100000)
Hfull = L.H_biquad(c1, c2, c3, c4, fgrid)
print("  peak |H| over 0.1-500 Hz = %.6f at %.2f Hz  =>  peak |H_k| = k EXACTLY, and it is at DC."
      % (np.abs(Hfull).max(), fgrid[np.argmax(np.abs(Hfull))]))
print("     no HF shelf, no resonance: nothing appears between k = 1.7 and 1.85. [EVIDENCE]")
den = 1 + c1 * np.exp(-2j * np.pi * fgrid / 1000) + c2 * np.exp(-4j * np.pi * fgrid / 1000)
po = np.abs(c4 / den)
print("  pole-only internal state peaks %.3fx (%+.2f dB) at %.3f Hz; at k=1.85 that is %.0f counts"
      % (po.max(), 20 * np.log10(po.max()), fgrid[np.argmax(po)], 1.85 * 110197))
print("     float32, never clamped => no overflow.  The numerator zero cancels it at the OUTPUT,")
print("     and c4 factors out of both => the cancellation is SCALE-INVARIANT in k. [EVIDENCE]")

d85 = L.load('r85')
eng85 = d85['cc_lat'] > 0.5
u = np.abs(d85['x6b94'].astype(float)[eng85])
print()
print("  AGGREGATOR SUM CLAMP +-0x2800 = 10240, from route 0x85's flown gp-0x6b94:")
print("     engaged |u| p50 %.0f  p95 %.0f  p99 %.0f  p99.9 %.0f  MAX %.0f  (duty at rail %.5f)"
      % (np.percentile(u, 50), np.percentile(u, 95), np.percentile(u, 99),
         np.percentile(u, 99.9), u.max(), (u >= 10240).mean()))
for k in (1.35, 1.70, 1.85, 2.00):
    growth = 1 + (k - 1) * A_FILT / 0.0528       # worst case: dG adds in phase with u
    print("     k=%.2f worst-case |u| scale %.3f => p99.9 -> %.0f, MAX -> %.0f  (%s)"
          % (k, growth, np.percentile(u, 99.9) * growth, u.max() * growth,
             "CLEAR" if u.max() * growth < 10240 else "*** REACHES THE RAIL"))
print("     (worst case: assumes dG adds fully in phase with u at every frequency, which it does")
print("      not -- at 6-9 Hz it subtracts.  This is an upper bound, not an estimate.)")


# ==================================================================================================
# 5. ENDPOINT POWER -- and the variance decomposition that says which measurement buys it
# ==================================================================================================
print()
print("=" * 104)
print("5. ENDPOINT POWER at k = 1.85, with a_filt's OWN uncertainty folded in")
print("=" * 104)
c0, _, A0pt, _ = ID[(6, 9)][0]
A0pt = 1 + c0 * (0.0528 * np.exp(1j * 15.1 * DEG))
Zref = Z9E[(6, 9)]


def pgt(k, a_draws, c_draws, A_draws, d=0.0):
    v = []
    for a in np.atleast_1d(a_draws):
        dG = -a * H75 * ((1 - d) * k - 1.0)
        Ad = np.atleast_1d(A_draws)
        Ak = Ad + np.atleast_1d(c_draws) * dG
        v.append((Zref * Ad / Ak).real)
    v = np.concatenate(v)
    return (v > 0).mean(), np.median(v), np.percentile(v, 5), (v > -1489).mean()


print("%44s %10s %10s %10s %12s" %
      ('uncertainty sources active', 'P(ReZ>0)', 'p50', 'p5', 'P(>-1489)'))
for lbl, a_, c_, A_ in (("both (as it stands)", AF[::7], bc, bA),
                        ("a_filt PINNED; (c,A) bootstrapped", A_FILT, bc, bA),
                        ("(c,A) pinned; a_filt bootstrapped", AF, c0, A0pt),
                        ("both pinned (point estimate)", A_FILT, c0, A0pt)):
    p, m, lo, p2 = pgt(1.85, a_, c_, A_)
    print("%44s %10.3f %+10.0f %+10.0f %12.3f" % (lbl, p, m, lo, p2))

print()
print("  k needed for P(Re Z > 0) >= target:")
print("%10s %14s %14s" % ('target', 'as it stands', 'a_filt pinned'))
for tgt in (0.60, 0.70, 0.80, 0.90):
    ks = []
    for a_ in (AF[::7], A_FILT):
        lo_, hi_ = 1.0, 8.0
        for _ in range(40):
            mid = (lo_ + hi_) / 2
            if pgt(mid, a_, bc, bA)[0] < tgt:
                lo_ = mid
            else:
                hi_ = mid
        ks.append(hi_)
    print("%10.2f %14.2f %14.2f" % (tgt, ks[0], ks[1]))
print("  => a_filt's uncertainty is the BINDING constraint, not (c, A).  Pinning a_filt takes")
print("     k = 1.85 from P = 0.556 to P = 0.847.  Pinning (c, A) does not.")

print()
print("[5.1] the READABLE-ENDPOINT clip-duty gate (much tighter than the break-even d* = 0.459)")
print("%12s %12s %12s %12s" % ('clip duty', 'Re Z p50', 'P(ReZ>0)', 'P(>-1489)'))
for d in (0.00, 0.04, 0.08, 0.12, 0.20, 0.30, 0.46):
    p, m, lo, p2 = pgt(1.85, AF[::7], bc, bA, d=d)
    print("%12.2f %+12.0f %12.4f %12.4f" % (d, m, p, p2))

print()
print("=" * 104)
print("6. THE ENGAGED-vs-MANUAL CONTRAST -- pricing it as an endpoint")
print("=" * 104)
d9 = L.load('r9e')
eng9 = d9['cc_lat'] > 0.5
w9 = d9['rate_f'].astype(float) * L.DEG2RAD
tq9 = d9['tq'].astype(float)
print("%10s %6s %5s %9s %9s %9s %8s %9s" %
      ('arm', 'block', 'n', 'ReZ p5', 'ReZ p50', 'ReZ p95', 'IQR', 'coh2 p50'))
for lbl, mask in (('ENGAGED', eng9), ('MANUAL', ~eng9)):
    for T in (15, 30):
        n = int(T * L.FS)
        vals = []
        for a0, b0 in L.episodes(mask):
            for s in range(a0, b0 - n + 1, n):
                sp = L.episode_specs(w9, tq9, [(s, s + n)], NPER)
                if sp:
                    H, co = L.band_H(sp, f, 6, 9)
                    vals.append((H.real, co))
        if not vals:
            continue
        r = np.array([v[0] for v in vals])
        co = np.array([v[1] for v in vals])
        print("%10s %6d %5d %+9.0f %+9.0f %+9.0f %8.0f %9.3f" %
              (lbl, T, len(r), np.percentile(r, 5), np.median(r), np.percentile(r, 95),
               np.percentile(r, 75) - np.percentile(r, 25), np.median(co)))
print("  => the MANUAL arm has coh2 = 0.15 and an IQR of 1324 counts around a near-ZERO mean.")
print("     Subtracting it from the engaged value ADDS ~1300 counts of noise and removes no bias,")
print("     because the ratchet does not EXIST in manual (engaged/manual 24.29x).  The proposed")
print("     within-drive contrast is STRICTLY WORSE than the engaged arm alone.")
