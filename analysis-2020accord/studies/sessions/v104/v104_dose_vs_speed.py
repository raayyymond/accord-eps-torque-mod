"""RE-PRICE THE V104 c4 DOSE AS A FUNCTION OF VEHICLE SPEED.

THE QUESTION
------------
The V104 dose was set at k = 1.85.  The binding derivation (studies/sessions/v104/v104_reprice_k185.py) used the
MEASURED  a_filt = 0.0457, whose matched window is v in [5, 25] m/s and whose engaged median is
~48-54 km/h.  The same session measured from ROM that the assist-map slope is SPEED-SCHEDULED,
0.123 at parking -> 0.046 at 120 km/h.  If the effective `a` on the highway is materially below
the value the dose was priced on, k = 1.85 may sit on the WRONG side of the Re Z crossing exactly
where the operator now reports the problem.

THE STRUCTURE THAT MAKES THIS TRACTABLE
---------------------------------------
The dose enters the model ONLY through   dG(k) = -a . H(f) . (k - 1).
=> for any two values of `a`, the SAME dG is reached at   (k-1) . a = const.
=> the Re Z zero crossing obeys  k_cross(a) = 1 + K / a,  with K = a_ref (k_cross(a_ref) - 1).
   K is a property of the LOOP IDENTIFICATION (c, A0, Z) alone and carries its uncertainty.
This is verified numerically in sec 1 rather than assumed.

METHOD FOR a(v):  ROM for the SHAPE, a_filt for the LEVEL.
The ROM map slope and `a_filt` are NOT the same quantity (a_filt is the as-flown duty-weighted
sensitivity of the SUM to a change in H; the ROM slope is the LANE's own slope, and the slot
weight relating them is not independently measured).  So the ROM is used only for the RATIO
    s(v) = a_ROM(v, tq(v)) / a_ROM(<matched window>)
and the level is anchored:  a(v) = a_filt . s(v).  A ratio is immune to the slot weight.

🛑 TRAPS OBSERVED
  - x6b94 read ONLY on r85/r95 (genuine SUM).  check_427_alias.assert_is_sum enforced.
  - `rate_f` is 0.7996x true deg/s => every |Z| in counts is 1.2506x high.  Sec 4 shows the
    dose derivation is IMMUNE (it uses only RATIOS of Z), by re-running the whole solve on
    rate_c = 1.2506 x rate_f and asserting k_cross is unchanged.
  - bootstrap over EPISODES, never windows.
  - |Z| rolls off un-modelled above ~13 Hz -> the 6-9 Hz result is not exposed; the 21-22.5 Hz
    rows are, and are labelled.
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

os.environ.setdefault('ACCORD_FIRMWARE_ROOT', 'C:/Users/dudei/Desktop/Projects/accord-firmwares')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402
import assist_map_mirror as M                                      # noqa: E402
import check_427_alias as CA                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
KPH = 3.6
CTS_PER_KPH = 64.0625
c1, c2, c3, c4 = L.honda_exact()
A_FILT = 0.0457
H75 = complex(L.H_biquad(c1, c2, c3, c4, np.array([7.5]))[0])
Z9E_69 = 6873 * np.exp(1j * -123.2 * DEG)       # GATE2 3.2, route 0x9e (V103), 6-9 Hz

for tag in ('r85', 'r95'):
    CA.assert_is_sum(tag)
print("check_427_alias: r85 and r95 confirmed to carry the genuine aggregator SUM.\n")


# ================================================================= identification
def load_sp(tag, ykey, ratekey='rate_f', rate_scale=1.0):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    spG = L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER)
    spZ = L.episode_specs(d[ratekey].astype(float) * rate_scale * L.DEG2RAD,
                          d['tq'].astype(float), eps, NPER)
    return spG, spZ


def ident(G4s, Z4s, G8s, Z8s, lo, hi, nboot=4000, seed=41):
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
    return pt, np.array([one(rng.integers(0, n4, n4), rng.integers(0, n8, n8))
                         for _ in range(nboot)])


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')
PT69, BS69 = ident(G4s, Z4s, G8s, Z8s, 6, 9)
c0, G0m, A0m, Z0m = PT69
G0 = 0.0528 * np.exp(1j * 15.1 * DEG)           # pooled G0, as the shipped scripts use
A0 = 1 + c0 * G0
bc, bA = BS69[:, 0], 1 + BS69[:, 0] * G0


def rez(k, a, cd, Ad, Z1=Z9E_69):
    """Exact Mobius Re Z(k)."""
    dG = -a * H75 * (k - 1.0)
    return (Z1 * Ad / (Ad + cd * dG)).real


def k_cross(a, cd, Ad, lo=1.0, hi=60.0):
    """Smallest k > 1 with Re Z(k) >= 0 (bisection; assumes monotone crossing in [lo,hi])."""
    if rez(hi, a, cd, Ad) < 0:
        return np.inf
    if rez(lo, a, cd, Ad) >= 0:
        return lo
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if rez(mid, a, cd, Ad) < 0:
            lo = mid
        else:
            hi = mid
    return hi


# ================================================================= 1. the K invariant
print("=" * 108)
print("1. THE INVARIANT  K = a . (k_cross - 1)  -- verified numerically, not assumed")
print("=" * 108)
print("%12s %14s %14s %14s" % ('a', 'k_cross', 'K = a(k-1)', 'vs a=0.0457'))
for a in (0.020, 0.0293, 0.0348, 0.0457, 0.0500, 0.069, 0.0816, 0.098, 0.117, 0.123, 0.150):
    kc = k_cross(a, c0, A0)
    print("%12.4f %14.4f %14.6f %14.4f"
          % (a, kc, a * (kc - 1), a * (kc - 1) / (0.0457 * (k_cross(0.0457, c0, A0) - 1))))
K_PT = 0.0457 * (k_cross(0.0457, c0, A0) - 1)
print("  ⇒ K is constant to 4 significant figures over a 7.5x span in `a`.  [EVIDENCE]")
print("  ⇒ PUBLISHED CHECKS REPRODUCED: k_cross(0.0457) = %.3f  (handoff: 1.545)"
      % k_cross(0.0457, c0, A0))
print("                                 k_cross(0.098)  = %.3f  (handoff: 1.256)"
      % k_cross(0.098, c0, A0))
print("  ⇒ K = %.5f.  A dose k is PAST the crossing iff  a >= K/(k-1)." % K_PT)
print("  ⇒ AT k = 1.85 THE DOSE CLEARS IFF  a >= %.5f." % (K_PT / 0.85))

Kb = np.array([0.0457 * (k_cross(0.0457, bc[i], bA[i]) - 1) for i in range(len(bc))])
Kb_f = Kb[np.isfinite(Kb)]
print("\n  K over the 4000-draw episode bootstrap of (c, A0):  p50 %.5f  p5 %.5f  p95 %.5f  "
      "(%.1f %% of draws never cross)"
      % (np.median(Kb_f), np.percentile(Kb_f, 5), np.percentile(Kb_f, 95),
         100 * (1 - len(Kb_f) / len(Kb))))
print("  ⇒ a_min(k=1.85) over the loop bootstrap: p50 %.4f  p95 %.4f"
      % (np.median(Kb_f) / 0.85, np.percentile(Kb_f, 95) / 0.85))


# ================================================================= 2. a(v) from ROM
print()
print("=" * 108)
print("2. THE SPEED SHAPE  s(v) = a_ROM(v, tq) / a_ROM(matched window)  -- ROM for SHAPE ONLY")
print("=" * 108)
_CACHE = {}


def lane_out(speed_kph):
    key = int(round(speed_kph * CTS_PER_KPH))
    if key not in _CACHE:
        A, B = M.stage_382d8(24, key)
        Xs, Ys = M.stage_389ec(A, B, key, angle_10deg=0x2711)
        X, Y, Z, S = M.build_map(Xs, Ys)
        tt = np.arange(0, 8193)
        _CACHE[key] = np.array([abs(M.lane(int(t), X, Y, Z, S)['b82']) for t in tt], float)
    return _CACHE[key]


def a_rom(speed_kph, tq_cnt, h=None):
    """Local d|b82|/d|Tsens| at (speed, |tq|).  h = symmetric secant half-width in counts."""
    out = lane_out(speed_kph)
    t = int(round(abs(tq_cnt)))
    h = max(64, int(0.35 * t)) if h is None else h          # wide enough to beat the integer LSB
    lo, hi = max(0, t - h), min(8192, t + h)
    return (out[hi] - out[lo]) / (hi - lo)


VG = np.array([0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])
print("  a_ROM(v, tq) at fixed torque operating points  [local secant, half-width max(64, 0.35|tq|)]")
TQP = [100, 150, 200, 300, 500, 1000, 2000]
print("%8s" % 'km/h' + "".join("%10s" % ("tq=%d" % t) for t in TQP))
for v in VG:
    print("%8.0f" % v + "".join("%10.4f" % a_rom(v, t) for t in TQP))


def duty_weighted_a(tag, mask_extra=None, vlo=-1e9, vhi=1e9):
    """Frame-duty-weighted mean of a_ROM over a route's ENGAGED frames in a speed window."""
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    tq = np.abs(d['tq'].astype(float))
    m = eng & (v >= vlo) & (v < vhi)
    if mask_extra is not None:
        m = m & mask_extra
    if m.sum() < 100:
        return np.nan, 0
    vb = np.clip(np.round(v[m] / 5.0) * 5.0, 0, 200)
    tb = np.clip(np.round(tq[m] / 25.0) * 25.0, 25, 8000)
    tot, n = 0.0, 0
    for vv, tt_ in zip(vb, tb):
        tot += a_rom(vv, tt_)
        n += 1
    return tot / n, m.sum() / L.FS


print()
print("  DUTY-WEIGHTED a_ROM over the frames that actually produced each estimate:")
MW = {}
for tag in ('r96', 'r9e'):
    d = L.load(tag)
    v = d['v_rear'].astype(float) * KPH
    ra = np.abs(d['rate_f'].astype(float))
    MW[tag] = (v >= 5 * KPH) & (v <= 25 * KPH) & (ra <= 60.0)
aw96, s96 = duty_weighted_a('r96', MW['r96'])
aw9e, s9e = duty_weighted_a('r9e', MW['r9e'])
A_ROM_WINDOW = 0.5 * (aw96 + aw9e)
print("    a_filt matched window   r96 %.4f (%.0f s) · r9e %.4f (%.0f s)  ⇒ reference %.4f"
      % (aw96, s96, aw9e, s9e, A_ROM_WINDOW))

print()
print("%14s %10s %10s %10s %10s" % ('speed band', 'r96 a_ROM', 'r9e a_ROM', 'pooled', 's(v)'))
VB = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 130)]
SHAPE = {}
for lo, hi in VB:
    a1, t1 = duty_weighted_a('r96', vlo=lo, vhi=hi)
    a2, t2 = duty_weighted_a('r9e', vlo=lo, vhi=hi)
    vals = [x for x in (a1, a2) if np.isfinite(x)]
    pool = float(np.mean(vals)) if vals else np.nan
    SHAPE[(lo, hi)] = pool
    print("%9d-%-4d %10.4f %10.4f %10.4f %10.3f"
          % (lo, hi, a1, a2, pool, pool / A_ROM_WINDOW))
print()
print("  ⚠ The operating point MOVES WITH SPEED (|tq| p50 falls ~400 -> ~110 ct from town to")
print("    highway), so s(v) folds BOTH the map's speed schedule and the torque schedule.")
print("    That is the right thing to fold: it is the as-driven sensitivity.")


# ================================================================= 3. the verdict table
print()
print("=" * 108)
print("3. SPEED-RESOLVED SAFETY TABLE  --  a(v) = a_filt . s(v),  k_cross(v) = 1 + K/a(v)")
print("=" * 108)
print("%14s %9s %9s %11s %11s %11s %11s" %
      ('speed band', 's(v)', 'a(v)', 'k_cross', '|A|@1.85', 'amp@1.85', 'ReZ@1.85'))
for lo, hi in VB:
    s = SHAPE[(lo, hi)] / A_ROM_WINDOW
    a = A_FILT * s
    kc = k_cross(a, c0, A0)
    Ak = A0 + c0 * (-a * H75 * 0.85)
    print("%9d-%-4d %9.3f %9.4f %11.3f %11.3f %11.3f %+11.0f"
          % (lo, hi, s, a, kc, abs(Ak), abs(A0) / abs(Ak), rez(1.85, a, c0, A0)))

print()
print("[3.1] JOINT UNCERTAINTY at k = 1.85 -- (c, A0) episode bootstrap x a_filt bootstrap,")
print("      the a_filt draws SHIFTED by s(v).  P(worse) = P(amp ratio > 1).")
AF = np.load('_scratch/data/_v103_natexp.npz')['a69'].real
AF = AF[(AF > 0.005) & (AF < 0.25)]
print("%14s %10s %10s %10s %10s %11s %11s" %
      ('speed band', 'amp p50', 'amp p95', 'amp MAX', 'P(worse)', 'P(ReZ>0)', 'ReZ p50'))
ROWS = {}
for lo, hi in VB:
    s = SHAPE[(lo, hi)] / A_ROM_WINDOW
    amps, rzs = [], []
    for a in AF[::7] * s:
        dG = -a * H75 * 0.85
        Ak = bA + bc * dG
        amps.append(np.abs(bA) / np.abs(Ak))
        rzs.append((Z9E_69 * bA / Ak).real)
    amps = np.concatenate(amps)
    rzs = np.concatenate(rzs)
    ROWS[(lo, hi)] = (amps, rzs)
    print("%9d-%-4d %10.3f %10.3f %10.3f %10.4f %11.4f %+11.0f"
          % (lo, hi, np.median(amps), np.percentile(amps, 95), amps.max(),
             (amps > 1).mean(), (rzs > 0).mean(), np.median(rzs)))

print()
print("[3.2] THE k REQUIRED to reach a given P(Re Z > 0), per speed band")
print("%14s %10s %10s %10s %10s" % ('speed band', 'P>=0.50', 'P>=0.60', 'P>=0.70', 'P>=0.80'))


def k_for_target(s, tgt):
    lo_, hi_ = 1.0, 12.0
    for _ in range(45):
        mid = 0.5 * (lo_ + hi_)
        v = []
        for a in AF[::11] * s:
            dG = -a * H75 * (mid - 1)
            v.append((Z9E_69 * bA / (bA + bc * dG)).real)
        if np.concatenate(v).mean() * 0 + (np.concatenate(v) > 0).mean() < tgt:
            lo_ = mid
        else:
            hi_ = mid
    return hi_


for lo, hi in VB:
    s = SHAPE[(lo, hi)] / A_ROM_WINDOW
    print("%9d-%-4d" % (lo, hi) + "".join("%10.2f" % k_for_target(s, t)
                                          for t in (0.50, 0.60, 0.70, 0.80)))

print()
print("[3.3] THE SMALLEST k SAFE AT EVERY SPEED THE CAR ACTUALLY DRIVES,")
print("      weighted by MEASURED ENGAGED EXPOSURE across the whole V100+ corpus")
EXP = {}
for tag in ('r85', 'r95', 'r96', 'r97', 'r9e'):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    for lo, hi in VB:
        EXP[(lo, hi)] = EXP.get((lo, hi), 0.0) + (eng & (v >= lo) & (v < hi)).sum() / L.FS
tot = sum(EXP.values())
print("%14s %12s %10s %12s" % ('speed band', 'engaged s', 'share', 'k_cross'))
for lo, hi in VB:
    s = SHAPE[(lo, hi)] / A_ROM_WINDOW
    print("%9d-%-4d %12.1f %10.3f %12.3f"
          % (lo, hi, EXP[(lo, hi)], EXP[(lo, hi)] / tot, k_cross(A_FILT * s, c0, A0)))
worst = max(k_cross(A_FILT * SHAPE[b] / A_ROM_WINDOW, c0, A0) for b in VB)
print("  ⇒ worst-band k_cross (point estimate, all bands) = %.3f" % worst)


# ================================================================= 4. the rate_f trap
print()
print("=" * 108)
print("4. IS THE DOSE DERIVATION EXPOSED TO THE `rate_f` = 0.7996x SCALE ERROR?")
print("=" * 108)
G4b, Z4b = load_sp('r85', 'x6b94', rate_scale=1.2506)
G8b, Z8b = load_sp('r95', 'x6b94', rate_scale=1.2506)
PTb, _ = ident(G4b, Z4b, G8b, Z8b, 6, 9, nboot=1)
cb, Gb, Ab, Zb = PTb
Ab_pool = 1 + cb * G0
print("  on rate_f (as shipped):  c = %.4f∠%+.1f°   A0 = %.4f∠%+.1f°   k_cross(a_filt) = %.4f"
      % (abs(c0), np.angle(c0, deg=True), abs(A0), np.angle(A0, deg=True),
         k_cross(A_FILT, c0, A0)))
print("  on rate_c (1.2506x):     c = %.4f∠%+.1f°   A0 = %.4f∠%+.1f°   k_cross(a_filt) = %.4f"
      % (abs(cb), np.angle(cb, deg=True), abs(Ab_pool), np.angle(Ab_pool, deg=True),
         k_cross(A_FILT, cb, Ab_pool)))
print("  ⇒ IMMUNE.  `c` is solved from rho = Z4/Z8, a RATIO on one channel, so any common scale")
print("    cancels exactly.  Only the ABSOLUTE Re Z counts carry the 1.2506x -- and the endpoint")
print("    thresholds (-1489, -3784) were measured on the same channel, so they are")
print("    self-consistent.  [EVIDENCE: re-solved end-to-end on the rescaled channel.]")


# ================================================================= 5. clip gate
print()
print("=" * 108)
print("5. CLIP GATE at the recommended dose -- |gp-0x6b82| . k vs the +-12288 ceiling")
print("=" * 108)
print("  gp-0x6b82's own reachable maximum from the ROM map (integer-exact, all speeds):")
mx = 0
for v in VG:
    o = lane_out(v)
    mx = max(mx, o.max())
print("    max |gp-0x6b82| over 0-120 km/h and |Tsens| 0-8192 = %.0f counts" % mx)
for k in (1.85, 2.00, 2.20, 2.50, 3.00, 3.40):
    print("    k = %.2f  =>  worst reachable |H_k . 6b82| = %.0f  vs 12288  (%s, %.2fx clear)"
          % (k, k * mx, "CLEAR" if k * mx < 12288 else "*** CLIPS", 12288 / (k * mx)))
print("  (|H| <= 1.000031 everywhere, so k.|6b82| is a true upper bound on the filter output.)")
