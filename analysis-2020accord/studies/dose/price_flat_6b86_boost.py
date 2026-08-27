"""PRICE THE **FLAT** gp-0x6b86 BOOST -- scale the biquad's overall gain c4 (0xC60B4) by k.

WHY FLAT IS DIFFERENT FROM THE (DEAD) RESONANT BOOST
----------------------------------------------------
    H(z) = c4 * (1 + c3 z^-1 + z^-2) / (1 + c1 z^-1 + c2 z^-2)          [GATE2 sec 1.2]
c4 multiplies the WHOLE transfer.  c4 -> k*c4 gives H -> k*H at EVERY frequency: a real,
frequency-independent factor, ZERO phase rotation, poles UNMOVED (tau_ring stays Honda's
4.40 ms, so the engaged-only stale-state transient stays negligible).  One 4-byte cal edit
at 0xC60B4.  c1/c2/c3 untouched.

MODEL (all decision-bearing inputs cited; EVIDENCE unless marked)
----------------------------------------------------------------
  G(f)  = u/T_s          aggregator SUM gp-0x6b94 per count of driver torque   [measured]
  L(f)  = -a * H_honda(f)   the gp-0x6b86 lane's contribution to G             [a solved, GATE2 2.2]
  G(k)  = G(1) + (k-1)*L                                                       [c4 is a pure gain]
  P     = c*G,  A = 1+P,   c = lambda*kappa identified from the 4x/8x gain step (studies/grind2/_g2b_kappa.py)
  Z(k)  = Z(1) * A(1)/A(k)          EXACT Mobius form -- NOT the first-order Re(dG.Z) proxy,
                                    because the dose is ~90 % of |G| and first order is invalid.
  criterion 1 ("magnitude"):  |G(k)|/|G(1)|          -- GATE2 sec 5's optimiser
  criterion 2 ("damping"):    sign/size of Re(Z(k))  -- first-order proxy Re(dG.Z) reproduced
                                                        for continuity with GATE2 sec 3.2
Uncertainty: the JOINT episode bootstrap of (G4,G8,Z4,Z8) -> (c, A, G) from studies/grind2/_g2b_kappa.py,
crossed with a in [0.07, 0.15].  Worst case is reported over that joint space, not the point.
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

try:                                    # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
np.set_printoptions(suppress=True)
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180

# ---------------------------------------------------------------- measured constants
A_POOL = 0.098                                 # gp-0x6b86 lane gain, 4-build pool  GATE2 2.2
A_R9E = 0.117                                  # same, route 0x9e alone             GATE2 2.2
A_GRID = np.round(np.arange(0.07, 0.1501, 0.005), 3)
G0_POOL = 0.0528 * np.exp(1j * 15.1 * DEG)     # pooled aggregator-sum transfer     GATE2 2.2
BANDS = [(2, 4), (4, 6), (6, 9), (9, 13), (15, 22), (22, 26)]
Z_G2 = {(2, 4): 1405 * np.exp(1j * -23.9 * DEG),      # Z on route 0x9e (V103)      GATE2 3.2
        (4, 6): 2413 * np.exp(1j * -68.1 * DEG),
        (6, 9): 6873 * np.exp(1j * -123.2 * DEG),
        (9, 13): 4931 * np.exp(1j * -172.2 * DEG),
        (15, 22): 1379 * np.exp(1j * 108.6 * DEG),
        (22, 26): 1168 * np.exp(1j * 96.8 * DEG)}
ARGZ69_CI = (-126.3, -117.6)                   # deg, episode bootstrap             GATE2 3.2
KS = np.round(np.arange(1.00, 3.001, 0.05), 2)

c1, c2, c3, c4 = L.honda_exact()
print("# stock biquad  c1=%.6f c2=%.6f c3=%.6f c4=%.6f  (0xC60A8..B4, LE float32)"
      % (c1, c2, c3, c4))
print("# c4 LE bytes stock = %s   DC gain = %.6f"
      % (L.le_bytes(c4), abs(L.H_biquad(c1, c2, c3, c4, 0.0))))


def Hh(fc):
    """Honda's stock biquad evaluated at fc Hz (fs = 1000)."""
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


# ================================================================ SECTION B: identification
def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    spG = L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER)
    spZ = L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float), eps, NPER)
    return spG, spZ


G4s, Z4s = load_sp('r85', 'x6b94')    # V100 4x, 427 = SUM
G8s, Z8s = load_sp('r95', 'x6b94')    # V101 8x, 427 = SUM


def ident(lo, hi, nboot=4000, seed=41):
    """Point + episode-bootstrap draws of (c, G4, A4, Z4). Mobius solve, as studies/grind2/_g2b_kappa.py."""
    def one(g4, z4, g8, z8):
        G4 = L.band_H(g4, f, lo, hi)[0]
        Z4 = L.band_H(z4, f, lo, hi)[0]
        G8 = L.band_H(g8, f, lo, hi)[0]
        Z8 = L.band_H(z8, f, lo, hi)[0]
        rho = Z4 / Z8
        c = (rho - 1) / (G8 - rho * G4)
        return c, G4, 1 + c * G4, Z4
    pt = one(G4s, Z4s, G8s, Z8s)
    rng = np.random.default_rng(seed)
    n4, n8 = len(G4s), len(G8s)
    bs = []
    for _ in range(nboot):
        i4 = rng.integers(0, n4, n4)
        i8 = rng.integers(0, n8, n8)
        bs.append(one([G4s[j] for j in i4], [Z4s[j] for j in i4],
                      [G8s[j] for j in i8], [Z8s[j] for j in i8]))
    return pt, np.array(bs)           # columns c, G4, A4, Z4


IDENT = {b: ident(*b) for b in BANDS}

print("\n" + "=" * 104)
print("SECTION B -- band-wise loop identification (routes 0x85 4x / 0x95 8x, aggregator SUM on 427)")
print("=" * 104)
print("%9s %8s %7s %7s %7s %7s %7s %16s %7s %7s %7s"
      % ('band', '|G4|', 'argG4', '|c|', 'arg c', '|kG|', '|A|', '|A| CI', '1/|A|', '|Z4|', 'argZ4'))
for b in BANDS:
    (c, G4, A4, Z4), bs = IDENT[b]
    aci = L.ci(np.abs(bs[:, 2]))
    print("%4.0f-%-4.0f %8.4f %+7.1f %7.2f %+7.1f %7.3f %7.3f [%6.3f,%6.3f] %7.2f %7.0f %+7.1f"
          % (b[0], b[1], abs(G4), np.angle(G4, deg=True), abs(c), np.angle(c, deg=True),
             abs(c * G4), abs(A4), aci[0], aci[1], 1 / abs(A4), abs(Z4), np.angle(Z4, deg=True)))

# ================================================================ PART 1
print("\n" + "=" * 104)
print("PART 1 -- DOSE RESPONSE of the FLAT boost  k = c4_new/c4_stock,  a = %.3f (4-build pool)"
      % A_POOL)
print("=" * 104)


def sweep(a, G0map, cmap, Zmap, ks=KS):
    """band -> rows (k, |G|/|G0|, Re(dG.Z), |A|, 1/|A|, ampratio, Re Z(k), Im Z(k))."""
    out = {}
    for b in BANDS:
        fc = 0.5 * (b[0] + b[1])
        Lb = -a * Hh(fc)
        G0 = G0map[b]
        c = cmap[b]
        Z1 = Zmap[b]
        A1 = 1 + c * G0
        rows = []
        for k in ks:
            dG = (k - 1) * Lb
            Gk = G0 + dG
            Ak = 1 + c * Gk
            Zk = Z1 * A1 / Ak
            rows.append((k, abs(Gk) / abs(G0), (dG * Z1).real, abs(Ak), 1 / abs(Ak),
                         abs(A1) / abs(Ak), Zk.real, Zk.imag))
        out[b] = np.array(rows)
    return out


# primary map: G0 = pooled sum at 6-9 (GATE2 2.2), route-85 G4 elsewhere; c, Z from identification
G0map = {b: (G0_POOL if b == (6, 9) else IDENT[b][0][1]) for b in BANDS}
cmap = {b: IDENT[b][0][0] for b in BANDS}
Zmap = dict(Z_G2)
S = sweep(A_POOL, G0map, cmap, Zmap)

hdr = "%5s " % 'k' + " ".join("%13s" % ("%d-%d" % b) for b in BANDS)
SHOW = [1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.75, 2.00, 2.25, 2.50, 3.00]
IDX = [int(np.argmin(np.abs(KS - s))) for s in SHOW]

print("\n[1.1] |G(k)| / |G(1)|   (criterion 1: aggregator-sum magnitude; <1 = smaller loop gain)")
print(hdr)
for i in IDX:
    print("%5.2f " % KS[i] + " ".join("%13.3f" % S[b][i, 1] for b in BANDS))

print("\n[1.2] Re(dG . Z)  (GATE2 3.2 first-order damping proxy; >0 = LESS anti-damping = BETTER)")
print(hdr)
for i in IDX:
    print("%5.2f " % KS[i] + " ".join("%+13.1f" % S[b][i, 2] for b in BANDS))

print("\n[1.3] |A(k)| = |1 + c.G(k)|  EXACT.  >1 = closed loop ATTENUATES.")
print("      [6-9 Hz is the only band where A has a usable CI; other bands are BELIEF-grade]")
print(hdr)
for i in IDX:
    print("%5.2f " % KS[i] + " ".join("%13.3f" % S[b][i, 3] for b in BANDS))

print("\n[1.4] amplification ratio |A(1)|/|A(k)|  (<1 = less closed-loop amplification = BETTER)")
print(hdr)
for i in IDX:
    print("%5.2f " % KS[i] + " ".join("%13.3f" % S[b][i, 5] for b in BANDS))

print("\n[1.5] Re(Z(k))  EXACT Mobius Z(k)=Z(1).A(1)/A(k)  (negative = anti-damped = the ratchet)")
print(hdr)
for i in IDX:
    print("%5.2f " % KS[i] + " ".join("%+13.0f" % S[b][i, 6] for b in BANDS))

print("\n[1.6] 6-9 Hz HEADLINE  (a = %.3f pooled)" % A_POOL)
r = S[(6, 9)]
print("%5s %9s %9s %10s %7s %7s %10s %9s %9s"
      % ('k', 'c4', '|G|/|G0|', 'Re(dG.Z)', '|A|', '1/|A|', 'amp ratio', 'Re Z(k)', 'ReZ/ReZ0'))
for i, k in enumerate(KS):
    print("%5.2f %9.5f %9.3f %+10.1f %7.3f %7.2f %10.3f %+9.0f %9.3f"
          % (k, k * c4, r[i, 1], r[i, 2], r[i, 3], r[i, 4], r[i, 5], r[i, 6], r[i, 6] / r[0, 6]))


def knife(arr_k, arr_v, target):
    """First k where v crosses target (linear interpolation)."""
    for i in range(1, len(arr_k)):
        if (arr_v[i - 1] - target) * (arr_v[i] - target) <= 0 and arr_v[i - 1] != arr_v[i]:
            t = (target - arr_v[i - 1]) / (arr_v[i] - arr_v[i - 1])
            return arr_k[i - 1] + t * (arr_k[i] - arr_k[i - 1])
    return None


print("\n[1.7] KNIFE EDGES at 6-9 Hz (where each criterion's benefit reverses)")
kk = np.arange(1.0, 6.001, 0.002)
Sf = sweep(A_POOL, G0map, cmap, Zmap, ks=kk)[(6, 9)]
print("  |G| minimum                      k = %.3f   (|G|/|G0| = %.3f)"
      % (kk[np.argmin(Sf[:, 1])], Sf[:, 1].min()))
print("  |G| back to baseline (ratio=1)   k = %s" % knife(kk, Sf[:, 1], 1.0))
print("  |A| = 1 (loop neutral)           k = %.3f" % kk[np.argmin(np.abs(Sf[:, 3] - 1.0))])
print("  amp ratio back to 1              k = %s" % knife(kk, Sf[:, 5], 1.0))
kz = knife(kk, Sf[:, 6], 0.0)
print("  Re Z(k) crosses 0 at 6-9 Hz      k = %s" % (("%.3f" % kz) if kz else "never for k<=6"))
print("  Re(dG.Z) sign: positive for every k>1 (it is linear in (k-1) with a positive coefficient)")


# ================================================================ PART 1.8 -- UNCERTAINTY
print("\n" + "=" * 104)
print("PART 1.8 -- WORST CASE over the JOINT uncertainty space")
print("  axes: (i) episode bootstrap of (G4,G8,Z4,Z8) -> joint (c, G0, A0, Z);  4000 draws")
print("        (ii) a in [0.07, 0.15] (17 values);  (iii) arg Z over its CI [-126.3, -117.6] deg")
print("  4000 x 17 x 3 = 204,000 corners.  'WORSE' = amp ratio > 1  OR  Re Z(k) < Re Z(1).")
print("=" * 104)

(c69, G69, A69, Z69), BS69 = IDENT[(6, 9)]
bc, bG, bA, bZ = BS69[:, 0], BS69[:, 1], BS69[:, 2], BS69[:, 3]
H75 = Hh(7.5)


def worst(ks=np.round(np.arange(1.0, 2.51, 0.05), 2)):
    rows = []
    for k in ks:
        amps, rez, rez0, wors = [], [], [], []
        for a in A_GRID:
            dG = (k - 1) * (-a * H75)
            Ak = bA + bc * dG                       # A(k) = 1 + c(G0+dG) = A0 + c.dG
            ampr = np.abs(bA) / np.abs(Ak)
            amps.append(ampr)
            for argz in (ARGZ69_CI[0], -123.2, ARGZ69_CI[1]):
                Z1 = np.abs(bZ) * np.exp(1j * argz * DEG)   # magnitude from the draw, phase swept
                Zk = Z1 * bA / Ak
                rez.append(Zk.real)
                rez0.append(Z1.real)
                wors.append((ampr > 1.0) | (Zk.real < Z1.real))
        amps = np.concatenate(amps)
        rez = np.concatenate(rez)
        rez0 = np.concatenate(rez0)
        wors = np.concatenate(wors)
        rows.append((k, np.median(amps), np.percentile(amps, 95), amps.max(),
                     np.median(rez - rez0), np.percentile(rez - rez0, 5), (rez < rez0).mean(),
                     wors.mean()))
    return np.array(rows)


W = worst()
print("%5s %10s %10s %10s %12s %12s %10s %10s"
      % ('k', 'amp p50', 'amp p95', 'amp MAX', 'dReZ p50', 'dReZ p5', 'P(ReZ wo)', 'P(WORSE)'))
for row in W:
    print("%5.2f %10.3f %10.3f %10.3f %+12.0f %+12.0f %10.4f %10.4f"
          % tuple(row))

print("\n[1.9] LEAVE-ONE-OUT / self-consistency variants at 6-9 Hz, k = 1.25 / 1.35 / 1.50")
variants = [
    ("primary: G0 pooled 0.0528<15.1, c from ident, Z route9e", G0_POOL, c69, Z_G2[(6, 9)], A_POOL),
    ("self-consistent: G0 = G4 route85, c, Z4 route85", G69, c69, Z69, A_POOL),
    ("a = 0.117 (route 9e alone)", G0_POOL, c69, Z_G2[(6, 9)], A_R9E),
    ("a = 0.070 (low end)", G0_POOL, c69, Z_G2[(6, 9)], 0.070),
    ("a = 0.150 (high end)", G0_POOL, c69, Z_G2[(6, 9)], 0.150),
    ("|A0| forced to 0.183 (LOO low)", G0_POOL, c69 * (abs(1 + c69 * G0_POOL) and 1), Z_G2[(6, 9)], A_POOL),
]
print("%58s %8s %8s %8s %8s %8s %8s" % ('variant', 'amp1.25', 'ReZ1.25', 'amp1.35', 'ReZ1.35',
                                        'amp1.50', 'ReZ1.50'))
for name, G0v, cv, Zv, av in variants[:5]:
    A1 = 1 + cv * G0v
    out = []
    for k in (1.25, 1.35, 1.50):
        dG = (k - 1) * (-av * H75)
        Ak = A1 + cv * dG
        out += [abs(A1) / abs(Ak), (Zv * A1 / Ak).real]
    print("%58s %8.3f %+8.0f %8.3f %+8.0f %8.3f %+8.0f" % (name, *out))

# explicit leave-one-out: drop one episode from each route (2 x 3 = 6 combinations)
print("\n[1.10] EXPLICIT LEAVE-ONE-OUT (drop 1 episode from r85 and/or r95), 6-9 Hz")
print("%14s %8s %8s %8s %9s %9s %9s" % ('dropped', '|kG|', '|A0|', 'ReZ(1)', 'amp@1.25', 'amp@1.35', 'amp@1.50'))


def solve_from(g4, z4, g8, z8):
    G4 = L.band_H(g4, f, 6, 9)[0]
    Z4 = L.band_H(z4, f, 6, 9)[0]
    G8 = L.band_H(g8, f, 6, 9)[0]
    Z8 = L.band_H(z8, f, 6, 9)[0]
    rho = Z4 / Z8
    c = (rho - 1) / (G8 - rho * G4)
    return c, G4, 1 + c * G4, Z4


combos = [("none", list(range(len(G4s))), list(range(len(G8s))))]
for i in range(len(G4s)):
    combos.append(("r85 ep%d" % i, [j for j in range(len(G4s)) if j != i], list(range(len(G8s)))))
for i in range(len(G8s)):
    combos.append(("r95 ep%d" % i, list(range(len(G4s))), [j for j in range(len(G8s)) if j != i]))
for name, i4, i8 in combos:
    c, G0v, A1, Zv = solve_from([G4s[j] for j in i4], [Z4s[j] for j in i4],
                                [G8s[j] for j in i8], [Z8s[j] for j in i8])
    out = []
    for k in (1.25, 1.35, 1.50):
        dG = (k - 1) * (-A_POOL * H75)
        Ak = A1 + c * dG
        out.append(abs(A1) / abs(Ak))
    print("%14s %8.3f %8.3f %+8.0f %9.3f %9.3f %9.3f"
          % (name, abs(c * G0v), abs(A1), Zv.real, *out))


# ================================================================ PART 2
print("\n" + "=" * 104)
print("PART 2 -- THE COST AT 15-26 Hz (grind #1 = 21.0-22.5 Hz; the 6x carrier = 22-26 Hz)")
print("=" * 104)
print("Honda's biquad is NOT transparent up there -- this is the crux GATE2 4.2.1 missed:")
for fc in (7.5, 18.5, 21.73, 24.0):
    H = Hh(fc)
    print("   H_Honda(%6.2f Hz) = %.4f (%+.3f dB) at %+.2f deg" %
          (fc, abs(H), 20 * np.log10(abs(H)), np.angle(H, deg=True)))
print("=> the boost vector dG = (k-1)(-a H) sits at 180+argH, i.e. +169.8 deg at 7.5 Hz but")
print("   +148.8 deg at 21.73 Hz.  A 21-deg rotation, and it FLIPS Re(dG.Z) at 15-26 Hz.")

HI_BANDS = [(15, 22), (18, 22), (21, 22.5), (20, 28), (22, 26), (26, 31)]
IDH = {b: ident(*b) for b in HI_BANDS}
print("\n[2.1] identification in the HIGH bands")
print("%10s %8s %7s %7s %7s %7s %7s %16s" %
      ('band', '|G4|', 'argG4', '|c|', 'arg c', '|kG|', '|A|', '|A| CI'))
for b in HI_BANDS:
    (c, G4, A4, Z4), bs = IDH[b]
    aci = L.ci(np.abs(bs[:, 2]))
    print("%5.1f-%-4.1f %8.4f %+7.1f %7.2f %+7.1f %7.3f %7.3f [%6.3f,%6.3f]" %
          (b[0], b[1], abs(G4), np.angle(G4, deg=True), abs(c), np.angle(c, deg=True),
           abs(c * G4), abs(A4), aci[0], aci[1]))

# Z per 1-Hz bin, route 0x9e (V103) -- the instrument f0 is DEFINED on
SIGNMAP = [(16, -2462.6), (17, -1654.3), (18, -1163.9), (19, -745.0), (20, -607.1), (21, -487.8),
           (22, -236.8), (23, -102.7), (24, -7.9), (25, 117.1), (26, 203.1), (27, 357.5),
           (28, 532.5), (29, 624.8), (30, 851.0), (31, 917.5), (32, 787.2), (33, 852.8)]
print("\n[2.2] both criteria in the high bands, k = 1.25 / 1.35 / 1.50   (a = %.3f)" % A_POOL)
print("%10s %8s %8s %8s | %9s %9s %9s | %9s %9s %9s" %
      ('band', 'G1.25', 'G1.35', 'G1.50', 'ReGZ1.25', 'ReGZ1.35', 'ReGZ1.50',
       'ReZ 1.00', 'ReZ 1.35', 'ReZ 1.50'))
for b in HI_BANDS:
    fc = 0.5 * (b[0] + b[1])
    (c, G0v, A1, Z4v) = IDH[b][0]
    Zb = Z4v          # route-85 Z in this band (route 0x9e sign map used separately for f0)
    Lb = -A_POOL * Hh(fc)
    g, rgz, rz = [], [], [Zb.real]
    for k in (1.25, 1.35, 1.50):
        dG = (k - 1) * Lb
        Ak = A1 + c * dG
        g.append(abs(G0v + dG) / abs(G0v))
        rgz.append((dG * Zb).real)
        rz.append((Zb * A1 / Ak).real)
    print("%5.1f-%-4.1f %8.3f %8.3f %8.3f | %+9.1f %+9.1f %+9.1f | %+9.0f %+9.0f %+9.0f" %
          (b[0], b[1], *g, *rgz, rz[0], rz[2], rz[3]))

# ---------------------------------------------------------------- f0 prediction
print("\n[2.3] f0 PREDICTION -- Re(Z) sign crossover, route 0x9e instrument (1 Hz bins)")
print("      model: ReZ_new(f) = Re( Z_9e(f) * A(f)/A_k(f) ),  A(f) from the 4x/8x solve on")
print("      1 Hz-centred 2 Hz bands.  [BELIEF: A identified at 4x is transported to V103's 6x.]")


def A_at(fc, halfwidth=1.0):
    (c, G0v, A1, Z4v), bs = ident(fc - halfwidth, fc + halfwidth, nboot=800, seed=7)
    return c, G0v, A1, bs


def f0_of(pairs):
    """Linear interpolation of the first negative->positive zero crossing above 18 Hz."""
    for i in range(1, len(pairs)):
        f0_, v0 = pairs[i - 1]
        f1_, v1 = pairs[i]
        if f0_ >= 18 and v0 < 0 <= v1:
            return f0_ + (f1_ - f0_) * (-v0) / (v1 - v0)
    return None


ACACHE = {fc: A_at(fc) for fc, _ in SIGNMAP if 18 <= fc <= 30}
print("\n%6s %10s %8s %8s %10s %10s %10s %10s" %
      ('f Hz', 'ReZ V103', '|A|', 'arg A', 'ReZ@1.25', 'ReZ@1.35', 'ReZ@1.50', 'ReZ@1.70'))
KS_F0 = (1.25, 1.35, 1.50, 1.70)
pred = {k: [] for k in KS_F0}
base = []
for fc, rez in SIGNMAP:
    if not (18 <= fc <= 30):
        continue
    c, G0v, A1, bs = ACACHE[fc]
    Lb = -A_POOL * Hh(fc)
    row = []
    for k in KS_F0:
        Ak = A1 + c * (k - 1) * Lb
        # rotate/scale the MEASURED route-9e Re(Z) by the modelled A ratio; keep its own |Z| and arg
        # arg is not available per bin, so apply the ratio to the complex Z built from the
        # identified route-85 arg and the route-9e Re (conservative: ratio applied to Re only if
        # the rotation is small).  We use the full complex form from the route-85 Z4 phase.
        Z4v = ident(fc - 1, fc + 1, nboot=1, seed=1)[0][3]
        Zb = abs(Z4v) * np.exp(1j * np.angle(Z4v))
        scale = rez / Zb.real if Zb.real != 0 else 1.0
        Zk = (Zb * scale) * A1 / Ak
        row.append(Zk.real)
        pred[k].append((fc, Zk.real))
    base.append((fc, rez))
    print("%6.0f %10.0f %8.3f %+8.1f %10.0f %10.0f %10.0f %10.0f" %
          (fc, rez, abs(A1), np.angle(A1, deg=True), *row))

f0_base = f0_of(base)
print("\n  f0 baseline from this instrument  = %.2f Hz   (recorded V103 route 0x9e f0 = 25.23 Hz)" % f0_base)
for k in KS_F0:
    v = f0_of(pred[k])
    if v is None:
        print("  f0 at k = %.2f : NO CROSSING in 18-30 Hz (Re Z positive throughout => f0 < 18 Hz)" % k)
    else:
        print("  f0 at k = %.2f : %.2f Hz   (shift %+.2f Hz vs the %s1.05 Hz split-half floor)"
              % (k, v, v - f0_base, chr(177)))


# ---------------------------------------------------------------- 2.4 criterion adjudication
print("\n[2.4] WHY THE TWO CRITERIA DISAGREE -- the proxy drops a rotation that is NOT small")
print("  exact:  dZ = -(c/A) . Z . dG      =>   favourable cone is arg(dG)+arg(Z)+arg(-c/A) in +-90")
print("  GATE2 3.2 proxy assumes arg(-c/A) = 0 (i.e. c real-negative AND A = 1).  Measured:")
for b in [(6, 9), (15, 22), (21, 22.5), (22, 26)]:
    src = IDENT if b in IDENT else IDH
    (c, G0v, A1, Z4v) = src[b][0]
    rot = np.angle(-c / A1, deg=True)
    lo = -90 - np.angle(Z4v, deg=True) - rot
    hi = 90 - np.angle(Z4v, deg=True) - rot
    fc = 0.5 * (b[0] + b[1])
    argdG = np.angle(-Hh(fc), deg=True)
    inside = ((argdG - lo) % 360) < ((hi - lo) % 360)
    print("   %5.1f-%-4.1f  arg(-c/A) = %+7.1f deg  =>  favourable arg(dG) in (%+7.1f, %+7.1f);"
          "  boost sits at %+7.1f  => %s"
          % (b[0], b[1], rot, lo, hi, argdG, "INSIDE" if inside else "OUTSIDE"))
print("  GATE2 3.2 quoted the 6-9 Hz cone as (+33, +213) deg by setting that rotation to zero.")

print("\n[2.5] RETRODICTION -- score both criteria against the ONE on-car dose-direction the kit has")
print("  Record: ARMING the r24 rate lane moved grind #1 on the road.  V67/V68 (Lever B, LKAS-gated")
print("  r24 arm) is the best grind-#1 build in the kit; V71c beat stock (P=0.0006) but lost to V67")
print("  (P=0.0215); V88 restored Lever B and the operator reported grinding FIXED, 15-22 Hz command")
print("  ratio 0.549 [0.407,0.844].  [BUILD-LINEAGE.md:646; accord-v88-flew-grinding-fixed-command-intact]")
print("  Perturbation: dG_rate = +eps * (rate lane), structural phase pol*jw = angle -90 deg.")
print("%12s %10s %12s %12s %12s" % ('band', '|G| ratio', 'Re(dG.Z)', 'exact ReZ', 'ROAD'))
for b in [(6, 9), (15, 22), (18, 22), (21, 22.5), (22, 26)]:
    src = IDENT if b in IDENT else IDH
    (c, G0v, A1, Z4v) = src[b][0]
    fc = 0.5 * (b[0] + b[1])
    dG = 0.25 * abs(G0v) * np.exp(-1j * np.pi / 2)         # +25 % of |G| of pure rate lane
    Ak = A1 + c * dG
    road = {(6, 9): "n/a", (15, 22): "BETTER", (18, 22): "BETTER",
            (21, 22.5): "BETTER", (22, 26): "n/a"}[b]
    print("%5.1f-%-4.1f  %10.3f %+12.1f %+12.0f %12s"
          % (b[0], b[1], abs(G0v + dG) / abs(G0v), (dG * Z4v).real,
             (Z4v * A1 / Ak).real - Z4v.real, road))
print("  ('exact ReZ' column is the CHANGE in Re Z; positive = less anti-damped = better.)")

# ================================================================ PART 3
print("\n" + "=" * 104)
print("PART 3 -- IS THERE A BETTER CAL-ONLY LEVER? -- the frontier")
print("=" * 104)
HIGH_CONSTRAINT = [(15, 22), (18, 22), (21, 22.5), (22, 26)]


def score(dG_of_f, ks=(1.0,)):
    """Return (worstcase amp ratio at 6-9, p50 amp ratio, max high-band ReZ degradation ratio)."""
    fc69 = 7.5
    dG69 = dG_of_f(fc69)
    Ak = bA + bc * dG69
    ampr = np.abs(bA) / np.abs(Ak)
    worst_hi = 1.0
    for b in HIGH_CONSTRAINT:
        (c, G0v, A1, Z4v) = IDH[b][0]
        fc = 0.5 * (b[0] + b[1])
        Akh = A1 + c * dG_of_f(fc)
        rz1 = Z4v.real
        rzk = (Z4v * A1 / Akh).real
        if rz1 < 0:
            worst_hi = max(worst_hi, rzk / rz1)      # >1 = more negative = worse
        elif rzk < rz1:
            worst_hi = max(worst_hi, 1 + (rz1 - rzk) / abs(rz1))
    return np.median(ampr), np.percentile(ampr, 95), ampr.max(), worst_hi


print("\n[3.1] FRONTIER -- flat c4 boost, k swept.  constraint: no high band worse by >20 %")
print("%6s %10s %10s %10s %12s %8s" %
      ('k', 'amp p50', 'amp p95', 'amp MAX', 'hi worst', 'feasible'))
best = None
for k in np.round(np.arange(1.00, 2.301, 0.05), 2):
    p50, p95, mx, hi = score(lambda fc, k=k: (k - 1) * (-A_POOL * Hh(fc)))
    ok = hi <= 1.20
    if ok and k > 1.0 and (best is None or p95 < best[2]):
        best = (k, p50, p95, mx, hi)
    print("%6.2f %10.3f %10.3f %10.3f %12.3f %8s" % (k, p50, p95, mx, hi, "yes" if ok else "NO"))
print("  FRONTIER POINT (max guaranteed benefit = min amp p95, s.t. hi<=1.20):")
print("    k = %.2f   amp p50 %.3f   amp p95 %.3f   amp MAX %.3f   hi %.3f"
      % (best[0], best[1], best[2], best[3], best[4]))

print("\n[3.2] r24/r26 RATE-LANE scaling m (V88 = 1.0 by construction; GATE2 5 gives eps* = -0.116)")
print("%6s %10s %10s %10s %12s" % ('m', 'amp p50', 'amp p95', 'amp MAX', 'hi worst'))
RATE69 = 0.1173 * np.exp(-1j * 89.9 * DEG)     # measured, GATE2 2.2, referenced to T_s


def rate_dG(fc, m):
    """Rate lane scales with frequency (pol*jw); magnitude anchored at 7.5 Hz."""
    return (m - 1) * abs(RATE69) * (fc / 7.5) * np.exp(-1j * np.pi / 2)


for m in (0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0):
    p50, p95, mx, hi = score(lambda fc, m=m: rate_dG(fc, m))
    print("%6.2f %10.3f %10.3f %10.3f %12.3f" % (m, p50, p95, mx, hi))

print("\n[3.3] 2-POLE LOW-PASS realisation:  c3 = +2.0 (double zero at Nyquist), poles at fp/zeta,")
print("      c4 solved for DC gain.  H_lp replaces H_Honda entirely => dG = -a (H_lp - H_Honda).")
print("%6s %6s %5s %9s %9s %9s %9s %9s %9s %9s %9s" %
      ('fp', 'zeta', 'DC', '|H|@7.5', 'arg@7.5', '|H|@21.7', '|H|@24', 'argdG7.5',
       'amp p50', 'amp MAX', 'hi worst'))
LP = []
for fp in (10, 12, 15, 20, 25):
    for zeta in (0.5, 0.7071, 1.0):
        for dc in (1.0, 1.35, 1.5):
            r = np.exp(-2 * np.pi * zeta * fp / 1000.0)
            wd = 2 * np.pi * fp * np.sqrt(max(1e-9, 1 - zeta ** 2)) / 1000.0
            d1 = -2 * r * np.cos(wd)
            d2 = r * r
            d3 = 2.0
            d4 = dc * (1 + d1 + d2) / 4.0

            def Hlp(fc, d1=d1, d2=d2, d3=d3, d4=d4):
                return complex(L.H_biquad(d1, d2, d3, d4, np.array([fc]))[0])

            def dG(fc, Hlp=Hlp):
                return -A_POOL * (Hlp(fc) - Hh(fc))

            p50, p95, mx, hi = score(dG)
            H75, H217, H24 = Hlp(7.5), Hlp(21.73), Hlp(24.0)
            LP.append((fp, zeta, dc, abs(H75), np.angle(H75, deg=True), abs(H217), abs(H24),
                       np.angle(dG(7.5), deg=True), p50, mx, hi, (d1, d2, d3, d4)))
LP.sort(key=lambda t: (t[10] > 1.20, t[9]))
for t in LP[:16]:
    print("%6.0f %6.3f %5.2f %9.3f %+9.1f %9.3f %9.3f %+9.1f %9.3f %9.3f %9.3f"
          % t[:11])
print("  (sorted: feasible first, then by worst-case amp ratio.  'hi worst' <=1.20 required.)")
best_lp = LP[0]
feas = [t for t in LP if t[10] <= 1.20]
if not feas:
    print("  *** NOT ONE of the %d low-pass designs is feasible: the BEST makes a high band"
          " %.2fx worse" % (len(LP), best_lp[10]))
    print("     (best on 6-9 Hz alone: fp=%.0f zeta=%.4f DC=%.2f, amp p50 %.3f, but hi %.3f)"
          % (best_lp[0], best_lp[1], best_lp[2], best_lp[8], best_lp[10]))
    print("     Reason: a low-pass CUTS the gp-0x6b86 lane at 15-26 Hz (|H| 0.15-0.44 vs Honda's")
    print("     0.82-0.90).  On the damping criterion that REMOVES damping there -- the brief's")
    print("     premise that attenuating 21.7/23 Hz is a co-benefit is inverted by the same")
    print("     criterion that adjudicates the rate lane in [2.5].")
else:
    t = feas[0]
    print("  BEST FEASIBLE LOW-PASS: fp=%.0f zeta=%.4f DC=%.2f -> c1=%.6f c2=%.6f c3=%.6f c4=%.6f"
          % (t[0], t[1], t[2], *t[11]))
    print("     bytes: %s %s %s %s" % tuple(L.le_bytes(v) for v in t[11]))


print("\n[3.4] FRONTIER re-cut on the SYMPTOM-BEARING high bands only")
print("  Grind #1 is the 21.0-22.5 Hz slice (STATE.md: 77.3 % of 15-22 power at <10 km/h sits")
print("  there); 22-26 Hz is the 6x carrier.  16-19 Hz carries NO recorded symptom.")
SYMPT = [(21, 22.5), (22, 26)]


def score2(dG_of_f, bands):
    dG69 = dG_of_f(7.5)
    Ak = bA + bc * dG69
    ampr = np.abs(bA) / np.abs(Ak)
    worst = 1.0
    for b in bands:
        (c, G0v, A1, Z4v) = IDH[b][0]
        Akh = A1 + c * dG_of_f(0.5 * (b[0] + b[1]))
        rz1, rzk = Z4v.real, (Z4v * A1 / Akh).real
        worst = max(worst, rzk / rz1 if rz1 < 0 else 1 + max(0, rz1 - rzk) / abs(rz1))
    return np.median(ampr), np.percentile(ampr, 95), ampr.max(), worst


print("%6s %10s %10s %10s %12s %12s" %
      ('k', 'amp p50', 'amp p95', 'amp MAX', 'symptom hi', '15-26 hi'))
for k in np.round(np.arange(1.00, 2.001, 0.1), 2):
    a1 = score2(lambda fc, k=k: (k - 1) * (-A_POOL * Hh(fc)), SYMPT)
    a2 = score2(lambda fc, k=k: (k - 1) * (-A_POOL * Hh(fc)), HIGH_CONSTRAINT)
    print("%6.2f %10.3f %10.3f %10.3f %12.3f %12.3f" % (k, a1[0], a1[1], a1[2], a1[3], a2[3]))
print("  => on the SYMPTOM bands the flat boost has NO cost at any k. The 15-26 cost is entirely")
print("     16-19 Hz, where no symptom has ever been recorded.")

print("\n[3.5] fine-grained Re(Z) cost/benefit per 1 Hz bin, k = 1.35 (route 0x9e instrument)")
print("%6s %10s %10s %9s" % ('f Hz', 'ReZ base', 'ReZ@1.35', 'ratio'))
for fc, rez in SIGNMAP:
    if not (16 <= fc <= 27):
        continue
    if fc in ACACHE:
        c, G0v, A1, bs = ACACHE[fc]
    else:
        c, G0v, A1, bs = A_at(fc)
    Ak = A1 + c * 0.35 * (-A_POOL * Hh(fc))
    Z4v = ident(fc - 1, fc + 1, nboot=1, seed=1)[0][3]
    Zk = Z4v * (rez / Z4v.real) * A1 / Ak
    print("%6.0f %10.0f %10.0f %9.3f" % (fc, rez, Zk.real, Zk.real / rez))

# ================================================================ PART 4
print("\n" + "=" * 104)
print("PART 4 -- THE FALSIFIER, pre-registered")
print("=" * 104)

print("\n[4.1] P(Re Z > 0) at 6-9 Hz engaged, over the 204,000-corner joint uncertainty space")
print("%6s %14s %14s %14s %12s" % ('k', 'P(ReZ>0)', 'P(ReZ>-1000)', 'P(ReZ<-2000)', 'ReZ p5'))
for k in np.round(np.arange(1.00, 2.001, 0.05), 2):
    vals = []
    for a in A_GRID:
        dG = (k - 1) * (-a * H75)
        Ak = bA + bc * dG
        for argz in (ARGZ69_CI[0], -123.2, ARGZ69_CI[1]):
            Z1 = np.abs(bZ) * np.exp(1j * argz * DEG)
            vals.append((Z1 * bA / Ak).real)
    v = np.concatenate(vals)
    print("%6.2f %14.4f %14.4f %14.4f %12.0f"
          % (k, (v > 0).mean(), (v > -1000).mean(), (v < -2000).mean(), np.percentile(v, 5)))

print("\n[4.2] EXPOSURE CONTROL -- can ONE 15-30 s engaged episode read Re(Z) at 6-9 Hz?")
print("  Method: cut route 0x9e's engaged frames into contiguous blocks of T seconds, compute the")
print("  frozen Re(Z) estimator on each block independently, report the distribution.  This is the")
print("  CONTROL, run BEFORE the measurement.")
d9 = None
try:
    d9 = L.load('r9e')
except Exception as exc:                      # pragma: no cover - cache naming fallback
    print("  (route 0x9e cache not loadable as 'r9e': %s)" % exc)

if d9 is not None:
    eng = d9['cc_lat'] > 0.5
    w = d9['rate_f'].astype(float) * L.DEG2RAD
    tq = d9['tq'].astype(float)
    eps9 = L.episodes(eng)
    print("  route 0x9e: %d episodes >=2.5 s, %.1f s engaged" %
          (len(eps9), sum(b - a for a, b in eps9) / L.FS))
    print("%8s %7s %10s %10s %10s %10s %10s" %
          ('block s', 'n', 'ReZ p5', 'ReZ p25', 'ReZ p50', 'ReZ p95', 'P(ReZ>0)'))
    for T in (15, 20, 30, 45, 60):
        n = int(T * L.FS)
        vals = []
        for a0, b0 in eps9:
            for s in range(a0, b0 - n + 1, n):
                sp = L.episode_specs(w, tq, [(s, s + n)], NPER)
                if not sp:
                    continue
                H, _ = L.band_H(sp, f, 6, 9)
                vals.append(H.real)
        vals = np.array(vals)
        if len(vals) == 0:
            print("%8d %7d   (no blocks)" % (T, 0))
            continue
        print("%8d %7d %10.0f %10.0f %10.0f %10.0f %10.4f"
              % (T, len(vals), np.percentile(vals, 5), np.percentile(vals, 25),
                 np.median(vals), np.percentile(vals, 95), (vals > 0).mean()))
    # manual control on the same drive
    man = ~eng
    epsm = L.episodes(man)
    if epsm:
        spm = L.episode_specs(w, tq, epsm, NPER)
        Hm, cm = L.band_H(spm, f, 6, 9)
        print("  MANUAL frames, same drive, 6-9 Hz: Re(Z) = %+.0f  (coh2 %.3f, %d runs >=2.5 s, %.1f s)"
              % (Hm.real, cm, len(epsm), sum(b - a for a, b in epsm) / L.FS))


print()
print("[4.3] IN-FORCE WITNESS -- the V104 spec's b6 rung already does this job, free")
print("  Rung: b6 = (|gp-0x6b86| >= |gp-0x6b82|).  gp-0x6b86 = clamp(H.gp-0x6b82 + gp-0x6b7e).")
print("  |H_Honda| by band:")
for fc in (0.5, 2, 5, 7.5, 12, 21.73):
    print("     %6.2f Hz  stock |H| = %.4f   at k=1.25 %.4f   k=1.35 %.4f   k=1.50 %.4f"
          % (fc, abs(Hh(fc)), 1.25 * abs(Hh(fc)), 1.35 * abs(Hh(fc)), 1.50 * abs(Hh(fc))))
print("  => stock: |H| <= 1.000034, so b6 is decided by the sign of the gp-0x6b7e pedestal")
print("     (duty ~0.5, and V103 measured nothing here).  At k >= 1.25 the FILTERED term alone")
print("     exceeds the input at every frequency below ~40 Hz, so b6 duty -> ~1.0 ENGAGED while")
print("     MANUAL frames (bypass, filter disarmed) keep the stock duty.  A single-frame,")
print("     zero-exposure, within-drive witness that (a) the arm gate is closed and (b) the c4")
print("     edit is in force -- which is exactly the V64 failure mode (the null was ON THE GATE).")

print()
print("[4.4] PRE-REGISTERED FALSIFIER")
print("""
  PRIMARY ENDPOINT       Re(Z) at 6-9 Hz, ENGAGED frames only.
  STATISTIC              Z = sum_band S_wT / sum_band S_ww ; w = rate_f (rad/s), T = tq (counts);
                         4 s Hann windows, 50 % overlap, linear detrend, Welch-summed inside the
                         engaged run.  Frozen method, GATE2 sec 2 / _gate2_boost_lib.band_H.
  EXPOSURE               ONE contiguous engaged block of >= 15 s.  No matched episodes, no
                         cross-build contrast, no minutes of exposure.
  BASE RATE (measured)   V103 route 0x9e, 23 independent 15 s engaged blocks: Re(Z) < 0 in 23/23,
                         p95 = -1489, median -3784.  Across every drive ever scored: 6/6 negative
                         (stock manual -3375/-3176/-3073; engaged -3639/-3762/-3761).
  PASS (lever worked)    Re(Z) > 0 in the block.   Model P(pass | k=1.35) = 0.996 over the
                         204,000-corner joint uncertainty; 5th percentile of the predicted value
                         is +506.
  FAIL (lever did not)   Re(Z) <= -1489 (V103's own worst 15 s block).
  AMBIGUOUS              -1489 < Re(Z) <= 0 : report as partial, do not call it either way.
  IN-FORCE WITNESS       b6 duty (see 4.3) engaged >> manual.  If b6 duty does NOT rise, the
                         endpoint is VOID -- the gate, not the hypothesis, and no physics may be
                         read from the drive.

  *** THE SENTENCE A NULL LICENSES, written before the cut:
    "The flat c4 boost injected dG = 0.034 at 7.5 Hz -- 65 % of the whole measured aggregator sum
     (0.0528) and 93 % of it at k = 1.5.  The identified loop says a perturbation that size MUST
     move Re(Z) at 6-9 Hz from -3763 to +547, with P = 0.996 over the full joint uncertainty.
     If b6 confirms the filter was in force and Re(Z) is still <= -1489, then the |kG| = 0.630 /
     A = 0.440 identification from the 4x/8x pair is FALSIFIED -- not merely imprecise -- and every
     lever priced against it since 2026-08-20, including the three GATE2 refusals, must be re-opened."

  ⚠ The manual arm is NOT a usable Re(Z) control on this route: route 0x9e's manual frames give
    Re(Z) = -273 at coh2 = 0.016 -- indistinguishable from noise.  Use b6 duty as the witness,
    not the manual Re(Z).
""")


print()
print("=" * 104)
print("SECTION C -- POSITIVE CONTROLS, and the DIRECTION COMPASS at 6-9 Hz")
print("=" * 104)
print("[C.1] reproduce GATE2 sec 3.2's published BOOST x1.44 row from this script's own model:")
dG144 = 0.44 * (-A_POOL * Hh(7.5))
print("      dG = %.4f at %+.1f deg  (GATE2: 0.042 at +169 deg)" % (abs(dG144), np.angle(dG144, deg=True)))
print("      Re(dG.Z) = %+.0f            (GATE2: +203)" % (dG144 * Z_G2[(6, 9)]).real)
dG150 = 0.50 * (-A_POOL * Hh(7.5))
print("      k=1.50: Re(dG.Z) = %+.0f     (GATE2: +230)" % (dG150 * Z_G2[(6, 9)]).real)
print("[C.2] reproduce studies/grind2/_g2b_kappa.py's 6-9 Hz solve: |kG| %.3f (rec 0.630), |A| %.3f (rec 0.440),"
      % (abs(c69 * G69), abs(A69)))
print("      |c| %.2f (rec 13.087), arg c %+.1f (rec +145.3)" % (abs(c69), np.angle(c69, deg=True)))

print()
print("[C.3] DIRECTION COMPASS -- which realisations of a gp-0x6b86 change are FAVOURABLE?")
rot69 = np.angle(-c69 / (1 + c69 * G0_POOL), deg=True)
lo69 = -90 - np.angle(Z_G2[(6, 9)], deg=True) - rot69
hi69 = 90 - np.angle(Z_G2[(6, 9)], deg=True) - rot69
print("      corrected favourable cone for arg(dG) at 6-9 Hz: (%+.1f, %+.1f) deg" % (lo69, hi69))
print("      [GATE2 3.2 published (+33, +213) by setting arg(-c/A) = 0; the measured value is"
      " %+.1f deg]" % rot69)
H75c = Hh(7.5)
cands = [("FLAT GAIN BOOST  k>1 (c4 up)", -A_POOL * H75c),
         ("flat gain CUT    k<1 (c4 down)", +A_POOL * H75c),
         ("full NULL of the lane", +A_POOL * H75c),
         ("pure LAG  30 deg at 7.5 Hz", -A_POOL * H75c * (np.exp(-1j * 30 * DEG) - 1)),
         ("pure LAG  60 deg", -A_POOL * H75c * (np.exp(-1j * 60 * DEG) - 1)),
         ("pure LAG  90 deg", -A_POOL * H75c * (np.exp(-1j * 90 * DEG) - 1)),
         ("pure LEAD 60 deg", -A_POOL * H75c * (np.exp(+1j * 60 * DEG) - 1)),
         ("gain x1.35 WITH 60 deg lag", -A_POOL * H75c * (1.35 * np.exp(-1j * 60 * DEG) - 1))]
print("      %34s %10s %10s %10s" % ("realisation", "arg(dG)", "inside?", "margin"))
for name, dg in cands:
    ang = np.angle(dg, deg=True)
    rel = (ang - lo69) % 360
    inside = rel < ((hi69 - lo69) % 360)
    margin = min(rel, ((hi69 - lo69) % 360) - rel) if inside else -min(rel % 360, (360 - rel) % 360)
    print("      %34s %+10.1f %10s %+9.1f deg" % (name, ang, "YES" if inside else "no", margin))
print("      => the ONLY favourable direction is a pure FLAT GAIN INCREASE. Every phase-based")
print("         realisation (lead OR lag) leaves the cone. GATE2 sec 5 item 5's 'a lag would be")
print("         favourable' is REVERSED by the arg(-c/A) correction.")


print()
print("=" * 104)
print("SECTION D -- CROSS-BUILD LEDGER, read from the plain images (not from build scripts)")
print("=" * 104)
import os
_ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                       'C:/Users/dudei/Desktop/Projects/accord-firmwares') + '/analysis-2020accord'
_IMGS = [
    ("V100", "_v100_V99BASE-CAVE.SAT.6AD6.C6200.4F60-SIGN.6B94-ID.B3CONST1-427.6B94_plain_image.bin"),
    ("V101", "_v101_V99BASE-GAIN8X.C6CD0.7128-NOLEVERB-CAVE.LKASSAT.SIGNS-427.6B94_plain_image.bin"),
    ("V102", "_v102_V101BASE-GAIN6X.C6CD0.5346-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6_plain_image.bin"),
    ("V103", "_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA-"
             "ID.B3VARIES_plain_image.bin"),
]


def _u16(b, a):
    return b[a] | (b[a + 1] << 8)


print("%6s %9s %9s %9s %9s %9s %9s %9s" %
      ("build", "0x3AA96", "0xC6446", "0x3AB76", "0x3AC20", "0xC6CD0", "0xC649B", "0xC60B4"))
print("%6s %9s %9s %9s %9s %9s %9s %9s" %
      ("STOCK", "c5", "512", "aa", "aa", "-", "00", "3a3b513f"))
for nm, fn in _IMGS:
    fp = os.path.join(_ROOT, fn)
    if not os.path.exists(fp):
        print("%6s   (image not found)" % nm)
        continue
    b = open(fp, 'rb').read()
    print("%6s %9s %9d %9s %9s %9d %9s %9s" %
          (nm, "%02x" % b[0x3AA96], _u16(b, 0xC6446), "%02x" % b[0x3AB76], "%02x" % b[0x3AC20],
           _u16(b, 0xC6CD0), "%02x" % b[0xC649B], b[0xC60B4:0xC60B8].hex()))
print("  Lever B = (0x3AA96 fb, 0xC6446 5244) = r24 x2.000 while LKAS applies -- grind-#1 effect")
print("           0.40 [0.27,0.58] on-car; Lever A = (0x3AB76/0x3AC20 non-aa) = V62's r24 half.")
print("  *** V101, V102 and V103 -- THREE CONSECUTIVE FLOWN BUILDS -- carry NEITHER grind-#1 fix.")
print("  *** The A0 = 0.440 baseline came from V100, which DID carry Lever B. The car today does")
print("      not.  Every Part-1 number is anchored to V100's operating point, not V103's.")
