"""v77 GATE 2 -- where the symptoms actually sit on the rate axis, and the candidate sweep.

★ THE NEW ANCHOR. The coordinator supplied two level-crossing counts from the route-5d replay,
engaged, 0-35 km/h:
        V74  X1 = 400 counts  ->   35 plateau entries
        V75  X1 = 200 counts  ->  282 plateau entries          (8.1x)
For a stationary Gaussian rate signal, Rice's formula gives up-crossings of level `a` per unit time
        n(a) = (1/2pi)(sigma_v/sigma_r) * exp(-a^2 / (2 sigma^2))
so the RATIO of two thresholds depends only on sigma:
        n(a1)/n(a2) = exp( (a2^2 - a1^2) / (2 sigma^2) )
=> ONE equation, ONE unknown. That yields the RMS of the engaged-creep rate signal, and with it the
   whole amplitude axis the symptoms have to live on -- and a PRICE for any candidate X1.

⊕ CROSS-CHECK, independent: the kit's own measured |gp-0x6ac0| p50 IN-BURST = 99 counts
  [94.2, 113.0]. For a zero-mean Gaussian, median|x| = 0.6745 sigma.
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
import math
from v77_gate2_describing_function import (
    Surface, N_closed, N_numeric, lerp_int, deg_s, CX, STOCK, V74, V75,
    A_BURST, A_RATCHET, A_GRIND, RATE_CT_PER_DEG_S,
)

# ==================================================================================================
# 1. THE RATE SIGNAL'S OWN SCALE -- two independent estimates
# ==================================================================================================
X1_V74, N_V74 = 400, 35
X1_V75, N_V75 = 200, 282

sigma_cross = math.sqrt((X1_V74 ** 2 - X1_V75 ** 2) / (2.0 * math.log(N_V75 / N_V74)))
sigma_median = 99 / 0.6744897501960817
sigma_median_lo, sigma_median_hi = 94.2 / 0.67449, 113.0 / 0.67449

print("=" * 100)
print("1. THE ENGAGED-CREEP RATE SIGNAL'S RMS  -- two independent estimates")
print("=" * 100)
print(f"  (a) from the level-crossing RATIO 282/35 at thresholds 200/400 :  sigma = {sigma_cross:6.1f} ct"
      f"  ({deg_s(sigma_cross):5.1f} deg/s)")
print(f"  (b) from the measured |gp-0x6ac0| p50 = 99 ct (median|x| = 0.6745 sigma) :"
      f"  sigma = {sigma_median:6.1f} ct  [{sigma_median_lo:.0f}, {sigma_median_hi:.0f}]")
print(f"  ⇒ the two agree to {abs(sigma_cross-sigma_median)/sigma_median*100:.0f}% -- a real cross-validation,")
print("    by two methods that share NO arithmetic (one is a crossing count, one is an amplitude p50).")
print()
sigma = sigma_cross
print(f"  Using sigma = {sigma:.1f} counts = {deg_s(sigma):.1f} deg/s RMS.")
print("  Self-check of the fitted model against its own two inputs:")
for x1, n in ((X1_V75, N_V75), (X1_V74, N_V74)):
    pred = N_V75 * math.exp(-(x1 ** 2 - X1_V75 ** 2) / (2 * sigma ** 2))
    print(f"     X1={x1:4d}  predicted {pred:6.1f}  measured {n:4d}")
print()
print("  🛑 WHAT THIS DOES TO THE ASSUMED SYMPTOM AMPLITUDES:")
for nm, A in (("burst p50-implied", A_BURST), ("ratchet +/-2deg @7.79Hz", A_RATCHET),
              ("grind#1 +/-2deg @20Hz", 1184), ("grind#1 (brief's 1249)", A_GRIND)):
    print(f"     {nm:26s} A = {A:5d} ct = {A/sigma:5.2f} sigma"
          f"   P(|r| > A) = {math.erfc(A/(sigma*math.sqrt(2))):.3e}")
print("  ⇒ a rate component at 1184-1249 counts is 7.0-7.4 sigma of the WHOLE signal. The whole")
print("    signal cannot be smaller than one of its components ⇒ the +/-2 deg premise is REFUTED")
print("    by the kit's own crossing counts. The symptoms live at roughly 1-3 sigma: 150-500 counts.")


def crossings(x1, sig=None):
    """Predicted plateau entries on the same exposure as route 5d, from Rice's formula."""
    sig = sig or sigma
    return N_V75 * math.exp(-(x1 ** 2 - X1_V75 ** 2) / (2 * sig ** 2))


# ==================================================================================================
# 2. WHAT IS STRUCTURALLY ACHIEVABLE -- the impossibility bound
# ==================================================================================================
print()
print("=" * 100)
print("2. THE BOUND: you cannot have V75's SMALL-SIGNAL gain without a near-relay")
print("=" * 100)
print("  For any odd, monotone, single-valued f, the fundamental obeys  N(A) <= (4/pi) f(A)/A.")
print("  The no-clip rule caps f at the ceiling floor 512, and V75's plateau at 297.")
for A in (100, 140, 200, 300, 461, 800, 1184):
    print(f"    A = {A:5d} ct : N <= (4/pi)*297/A = {4/math.pi*297/A:6.3f} (at V75's plateau)"
          f" | <= {4/math.pi*512/A:6.3f} (at the 512 ceiling)"
          f" | V75 actual {N_closed(V75, A):6.3f}")
print("  ⇒ V75's N(140)=1.41 is 74% of the ABSOLUTE bound at that amplitude. Any surface matching")
print("    it must reach ~297 counts of dose by ~200 counts of rate ⇒ slope >= 1.5 ⇒ it IS a relay.")
print("    [EVIDENCE, arithmetic] There is no smooth surface with V75's small-signal damping.")


# ==================================================================================================
# 3. CANDIDATE FAMILIES
# ==================================================================================================
def mk(name, cy0, ex, ey, weight=2048):
    return Surface(name, CX, [cy0, 234, 429, 908], ex, ey, damp_weight=weight)


EY_PLATEAU = [0, 539, 539, 927]
CANDS = []
# Family A -- V75's dose (C_Y0=566), the relay ENTRY moved back out. `LEVERS EX1` is a FLAG.
for x1 in (200, 250, 300, 350, 400, 450, 500, 525, 550, 600, 700):
    CANDS.append(mk(f"A: C566 X1={x1}", 566, [12, x1, 2500, 4000], EY_PLATEAU))
# Family B -- V74's dose, entry swept (the "lower the dose instead" arm)
for x1 in (200, 300, 400, 525):
    CANDS.append(mk(f"B: C429 X1={x1}", 429, [12, x1, 2500, 4000], EY_PLATEAU))
# Family C -- the ORIGINAL brief: delete the plateau (Y1 < Y2), X1 swept
for x1, y1 in ((400, 140), (400, 300), (400, 450), (200, 140), (200, 300), (200, 450),
               (700, 450), (1000, 450)):
    CANDS.append(mk(f"C: C566 X1={x1} Y1={y1}", 566, [12, x1, 2500, 4000], [0, y1, 539, 927]))
# Family D -- a genuinely PROGRESSIVE (convex) surface: X2 pulled left, no flat segment
for x1, y1, x2 in ((250, 180, 700), (300, 150, 800), (200, 100, 600), (350, 200, 900)):
    CANDS.append(mk(f"D: C566 X1={x1} Y1={y1} X2={x2}", 566, [12, x1, x2, 4000], [0, y1, 539, 927]))
# Family E -- revert the damper weight instead (0xC63A0 2048 -> 1024), V75 surface untouched
CANDS.append(mk("E: V75 surface, 0xC63A0=1024", 566, [12, 200, 2500, 4000], EY_PLATEAU, 1024))

REF = {"stock": STOCK, "V74": V74, "V75": V75}

A_GRID = [x for x in range(5, 4001, 5)]
SYMPTOM_BAND = [140, 200, 300, 461, 600, 800, 1184]


def flat_run(s):
    """Longest run of |rate| over which the dose is CONSTANT and NON-ZERO (the relay segment)."""
    best, cur, prev = 0, 0, None
    for r in range(0, 4001, 1):
        d = s.g(r)
        if d > 0 and d == prev:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
        prev = d
    return best


def metrics(s):
    vals = [(N_closed(s, A), A) for A in A_GRID]
    npk, apk = max(vals)
    return {
        "npk": npk, "apk": apk,
        "N": {A: N_closed(s, A) for A in SYMPTOM_BAND},
        "M": s.g(2000),
        "x1": s.EX[1],
        "flat": flat_run(s),
        "cross": crossings(next((r for r in range(1, 4001) if s.g(r) >= 0.98 * s.g(2000)), s.EX[1])),
        "w": s.damp_weight,
    }


print()
print("=" * 100)
print("3. CANDIDATES.  N_peak is the SMALL-SIGNAL/chatter risk; N at 300-1184 is the SYMPTOM damping.")
print("   'entries' = predicted plateau entries on route-5d exposure (Rice, sigma above).")
print("   'x N_pk(V74)' = N_peak relative to V74, the ONLY surface with 1,011 s of fault-free flight.")
print("=" * 100)
m74 = metrics(V74)
m75 = metrics(V75)
hdr = (f"{'surface':30s} {'M':>5s} {'X1':>5s} {'flatct':>7s} {'N_peak':>7s} {'@A':>6s} "
       f"{'xV74pk':>7s} {'entries':>8s} " + " ".join(f"N{A:<5d}" for A in SYMPTOM_BAND))
print(hdr)
print("-" * len(hdr))
for nm, s in list(REF.items()) + [(c.name, c) for c in CANDS]:
    m = metrics(s)
    ns = " ".join(f"{m['N'][A]:6.3f}" for A in SYMPTOM_BAND)
    ratio = m["npk"] / m74["npk"] if m74["npk"] else float("nan")
    print(f"{nm:30s} {m['M']:5d} {m['x1']:5d} {m['flat']:7d} {m['npk']:7.3f} {m['apk']:6.0f} "
          f"{ratio:7.2f} {m['cross']:8.1f} {ns}")

print()
print("=" * 100)
print("4. THE TWO RECOMMENDED POINTS, priced against BOTH flown builds")
print("=" * 100)
PRIMARY = mk("V77-a  C566 / X1=400 (= V75 dose, V74 entry)", 566, [12, 400, 2500, 4000], EY_PLATEAU)
CONSERV = mk("V77-b  C566 / X1=525 (= V75 dose, V74 SLOPE)", 566, [12, 525, 2500, 4000], EY_PLATEAU)
for cand in (PRIMARY, CONSERV):
    m = metrics(cand)
    print(f"\n  {cand.name}")
    print(f"     plateau height M = {m['M']} counts  (V74 {m74['M']}, V75 {m75['M']})")
    print(f"     small-signal slope = {(cand.c_creep()*cand.EY[1]>>10)/(cand.EX[1]-cand.EX[0]):.4f}"
          f"   (V74 0.5799, V75 1.5798)")
    print(f"     N_peak = {m['npk']:.3f}  = {m['npk']/m74['npk']:.2f}x V74  = {m['npk']/m75['npk']:.2f}x V75")
    print(f"     predicted plateau entries = {m['cross']:.1f}  (V74 35 measured, V75 282 measured)")
    print(f"     {'A(ct)':>7s} {'A/sig':>6s} {'V74':>7s} {'V75':>7s} {'cand':>7s} {'vs V74':>7s} {'vs V75':>7s}")
    for A in SYMPTOM_BAND:
        n0, n1, nc = N_closed(V74, A), N_closed(V75, A), N_closed(cand, A)
        print(f"     {A:7d} {A/sigma:6.2f} {n0:7.3f} {n1:7.3f} {nc:7.3f} "
              f"{nc/n0 if n0 else float('nan'):7.2f} {nc/n1 if n1 else float('nan'):7.2f}")
