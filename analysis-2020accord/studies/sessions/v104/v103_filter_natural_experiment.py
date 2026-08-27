"""THE V102 -> V103 NATURAL EXPERIMENT: Honda's biquad, armed engaged-only, ALREADY FLOWN.

WHY THIS EXISTS
---------------
V103 = V102 + `0xC649B` 00->01 + the arm-source repoint (`gp-0x671a` -> `gp-0x6806`, latActive)
+ cave bits.  Byte-read from the images: 0xC6CD0 = 5346 on BOTH (6x), Lever A and Lever B stock on
BOTH.  The ONLY control-path difference is that V103 runs `gp-0x6b86 = H_stock(z).gp-0x6b82 + ped`
on ENGAGED frames and the literal bypass (`mov r10,r6`, H = 1) on MANUAL frames, while V102 runs
the bypass ALWAYS.

=> [X_engaged - X_manual]_V103 - [X_engaged - X_manual]_V102  isolates the filter's effect,
   controlling for everything engagement itself does.  A difference-in-differences on flown data.

This is a FREE, ALREADY-COLLECTED, on-car dose-response on the exact cell block a c4 boost moves.
The predicted perturbation is computed FIRST, then measured.  [Run the control before the
measurement -- feedback-run-the-control-before-the-measurement.]

THE PREDICTION THE RECORD GOT WRONG
-----------------------------------
HANDOFF-2026-08-21 sec 2.1 records V103's filter as "-0.149 dB at 7.79 Hz, inert where the ratchet
lives".  -0.149 dB is small ON THE LANE.  But the kit's own LAW (STATE.md, 3.1) says the 6-9 Hz
aggregator is a 4:1 near-cancellation, so a lane-referenced dB is the wrong unit:
    dG_arm = -a * (H_stock - 1)
and |H_stock - 1| = 0.184 at 7.79 Hz, so |dG_arm| = 0.018 against a SUM of 0.048-0.053
=> 34-37 % of the whole loop gain.  NOT inert.
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
A_POOL = 0.098

BANDS = [(2, 4), (4, 6), (6, 9), (9, 13), (15, 22), (18, 22), (21, 22.5), (22, 26), (26, 31)]


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


# ------------------------------------------------------------------ 1. THE PREDICTION
print("=" * 100)
print("1. PREDICTION -- what arming Honda's own filter injects, BEFORE looking at the data")
print("=" * 100)
print("%10s %9s %9s %10s %10s %10s" %
      ('band', '|H|', 'arg H', '|H-1|', '|dG_arm|', 'arg dG_arm'))
for b in BANDS:
    fc = 0.5 * (b[0] + b[1])
    H = Hh(fc)
    dH = H - 1
    dG = -A_POOL * dH
    print("%5.1f-%-4.1f %9.4f %+9.2f %10.4f %10.4f %+10.1f" %
          (b[0], b[1], abs(H), np.angle(H, deg=True), abs(dH), abs(dG), np.angle(dG, deg=True)))
print()
print("  *** |H-1| at 7.5 Hz = %.4f -- the lane changes by only -0.14 dB, but dG = %.4f is"
      % (abs(Hh(7.5) - 1), A_POOL * abs(Hh(7.5) - 1)))
print("      %.0f %% of the whole 6-9 Hz aggregator sum (0.0528).  The record's 'inert' is wrong."
      % (100 * A_POOL * abs(Hh(7.5) - 1) / 0.0528))
print("  *** at 21.73 Hz |H-1| = %.4f => dG = %.4f, %.0f %% of the 21-22.5 Hz sum (0.2703)."
      % (abs(Hh(21.73) - 1), A_POOL * abs(Hh(21.73) - 1),
         100 * A_POOL * abs(Hh(21.73) - 1) / 0.2703))


# ------------------------------------------------------------------ 2. THE MEASUREMENT
def specs(d, mask, x, y):
    eps = L.episodes(mask)
    return L.episode_specs(x, y, eps, NPER), eps


def load(tag):
    d = L.load(tag)
    return dict(d=d, eng=d['cc_lat'] > 0.5,
                w=d['rate_f'].astype(float) * L.DEG2RAD, tq=d['tq'].astype(float))


R = {t: load(t) for t in ('r96', 'r9e')}
print()
print("=" * 100)
print("2. MEASUREMENT -- Re(Z) and band power, engaged vs manual, V102 (r96) vs V103 (r9e)")
print("=" * 100)
for t, nm in (('r96', 'V102 disarmed'), ('r9e', 'V103 armed-engaged')):
    r = R[t]
    for lbl, m in (('engaged', r['eng']), ('manual', ~r['eng'])):
        eps = L.episodes(m)
        print("  %-4s %-20s %-8s : %2d runs >=2.5 s, %6.1f s"
              % (t, nm, lbl, len(eps), sum(b - a for a, b in eps) / L.FS))


def boot_stat(fn, specs_list, nboot=4000, seed=3):
    rng = np.random.default_rng(seed)
    n = len(specs_list)
    out = np.empty(nboot)
    for i in range(nboot):
        pick = rng.integers(0, n, n)
        out[i] = fn([specs_list[j] for j in pick])
    return out


print()
print("[2.1] Re(Z) = Re(sum S_wT / sum S_ww), w = rate_f (rad/s), T = tq")
print("%10s %26s %26s %14s" % ('band', 'V102 (r96) eng / man', 'V103 (r9e) eng / man', 'DiD'))
ZSTORE = {}
for b in BANDS:
    row = []
    for t in ('r96', 'r9e'):
        r = R[t]
        for m in (r['eng'], ~r['eng']):
            sp, _ = specs(r['d'], m, r['w'], r['tq'])
            H, coh = L.band_H(sp, f, b[0], b[1])
            row.append((H.real, coh, sp))
    did = (row[2][0] - row[3][0]) - (row[0][0] - row[1][0])
    ZSTORE[b] = row
    print("%5.1f-%-4.1f  %+9.0f (%.2f) /%+8.0f  %+9.0f (%.2f) /%+8.0f %+14.0f" %
          (b[0], b[1], row[0][0], row[0][1], row[1][0],
           row[2][0], row[2][1], row[3][0], did))

print()
print("[2.2] band RMS of rate_f (deg/s), engaged and manual -- the ratchet's own amplitude")
print("%10s %12s %12s %12s %12s %12s" %
      ('band', 'V102 eng', 'V102 man', 'V103 eng', 'V103 man', 'DiD ratio'))


def band_rms(d, mask, sig, lo, hi):
    eps = L.episodes(mask)
    sp = L.episode_specs(sig, sig, eps, NPER)
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    Sxx = sum(s[0] for s in sp)
    nw = sum(s[3] for s in sp)
    return float(np.sqrt(Sxx[sel].sum() / nw * (f[1] - f[0])))


for b in BANDS:
    vals = []
    for t in ('r96', 'r9e'):
        r = R[t]
        rate = r['d']['rate_f'].astype(float)
        vals.append(band_rms(r['d'], r['eng'], rate, b[0], b[1]))
        vals.append(band_rms(r['d'], ~r['eng'], rate, b[0], b[1]))
    did = (vals[2] / vals[3]) / (vals[0] / vals[1])
    print("%5.1f-%-4.1f %12.4f %12.4f %12.4f %12.4f %12.3f" % (b[0], b[1], *vals, did))

print()
print("[2.3] speed / rate census -- the DiD's biggest threat is an unmatched exposure mix")
print("%6s %9s %10s %10s %10s %10s" %
      ('route', 'arm', 'v p50 eng', 'v p50 man', '|rate| p50 e', '|rate| p50 m'))
for t, nm in (('r96', 'disarmed'), ('r9e', 'engaged-only')):
    r = R[t]
    v = r['d']['v_rear'].astype(float)
    rate = np.abs(r['d']['rate_f'].astype(float))
    print("%6s %9s %10.2f %10.2f %10.2f %10.2f" %
          (t, nm, np.median(v[r['eng']]), np.median(v[~r['eng']]),
           np.median(rate[r['eng']]), np.median(rate[~r['eng']])))


# ==================================================================================================
# 3. THE INVERSION -- solve for `a` from the flown V102->V103 pair.  Open item #1 closed, or not.
# ==================================================================================================
# The pair is SINGLE-VARIABLE on the control path (0xC6CD0 identical 5346; Lever A/B identical
# stock; only 0xC649B + the arm-source repoint differ).  So:
#     rho = Z_V103 / Z_V102 = A_disarmed / A_armed,      A_armed = A_dis + c * dG(a)
#     =>  dG = A_dis * (1/rho - 1) / c ,   a = -dG / (H_stock - 1)
# `a` is a MEMORYLESS map slope, so the SAME `a` must come back from EVERY band.  That is a real
# over-determination test the solve is free to fail.
print()
print("=" * 100)
print("3. INVERSION -- measuring `a` from the flown pair (over-determined across bands)")
print("=" * 100)

C69 = 13.087 * np.exp(1j * 145.3 * DEG)          # studies/grind2/_g2b_kappa.py, 6-9 Hz
A_DIS = 0.440 * np.exp(1j * 25.0 * DEG)          # A of the DISARMED state (V100/V101 both 0xC649B=00)


def win_specs_masked(x, y, keep, mask, nper=NPER):
    """Per-window spectra over runs of `mask`, keeping only windows whose `keep` is all-True."""
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    bnds = np.concatenate(([0], idx, [len(mask)]))
    step = nper // 2
    w = np.hanning(nper + 1)[:nper]
    U = (w ** 2).sum()
    tt = np.arange(nper)
    A = np.vstack([tt, np.ones(nper)]).T
    out = []
    for i in range(len(bnds) - 1):
        a0, b0 = bnds[i], bnds[i + 1]
        if not mask[a0] or (b0 - a0) < nper:
            continue
        XS = YS = XY = None
        nw = 0
        for s in range(a0, b0 - nper + 1, step):
            if not keep[s:s + nper].all():
                continue
            xs = x[s:s + nper]
            ys = y[s:s + nper]
            if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
                continue
            xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
            ys = ys - A @ np.linalg.lstsq(A, ys, rcond=None)[0]
            X = np.fft.rfft(xs * w)
            Y = np.fft.rfft(ys * w)
            sxx = (X.conj() * X).real / (L.FS * U)
            syy = (Y.conj() * Y).real / (L.FS * U)
            sxy = (X.conj() * Y) / (L.FS * U)
            XS = sxx if XS is None else XS + sxx
            YS = syy if YS is None else YS + syy
            XY = sxy if XY is None else XY + sxy
            nw += 1
        if nw:
            out.append((XS, YS, XY, nw))
    return out


# matched exposure window: the overlap of the two engaged distributions
VLO, VHI = 5.0, 25.0            # m/s
RHI = 60.0                      # deg/s, drop the extremes
MSPECS = {}
for t in ('r96', 'r9e'):
    r = R[t]
    v = r['d']['v_rear'].astype(float)
    ra = np.abs(r['d']['rate_f'].astype(float))
    keep = (v >= VLO) & (v <= VHI) & (ra <= RHI)
    MSPECS[t] = win_specs_masked(r['w'], r['tq'], keep, r['eng'])
    nw = sum(s[3] for s in MSPECS[t])
    print("  %s: %d episodes with matched windows, %d windows (%.1f s equivalent), "
          "median v %.2f m/s" % (t, len(MSPECS[t]), nw, nw * NPER / 2 / L.FS,
                                 np.median(v[r['eng'] & keep])))

print()
print("%10s %11s %11s %11s %11s %11s %13s %11s" %
      ('band', '|Z| V102', 'arg V102', '|Z| V103', 'arg V103', '|rho|', 'a solved', 'Im/Re resid'))
ASOLVED = {}
for b in BANDS:
    Z2, coh2_ = L.band_H(MSPECS['r96'], f, b[0], b[1])
    Z3, coh3_ = L.band_H(MSPECS['r9e'], f, b[0], b[1])
    fc = 0.5 * (b[0] + b[1])
    dH = Hh(fc) - 1
    rho = Z3 / Z2
    dG = A_DIS * (1 / rho - 1) / C69
    a = -dG / dH
    ASOLVED[b] = (a, rho, Z2, Z3)
    print("%5.1f-%-4.1f %11.0f %+11.1f %11.0f %+11.1f %11.3f %13.3f %11.2f" %
          (b[0], b[1], abs(Z2), np.angle(Z2, deg=True), abs(Z3), np.angle(Z3, deg=True),
           abs(rho), a.real, a.imag / (abs(a.real) + 1e-12)))
print("  (`a` must be REAL and POSITIVE and the SAME in every band.  A large Im/Re residual, a")
print("   negative value, or band-to-band scatter falsifies either the single-variable claim, the")
print("   value of c, or the linear-perturbation model.)")

# --------------------------------------------------------------- forward check at a = 0.098
print()
print("[3.1] FORWARD CHECK -- what the model with a = 0.098 PREDICTED for this flown pair")
print("%10s %14s %14s %14s %14s" %
      ('band', 'pred |A| ratio', 'pred ReZ V103', 'MEASURED', 'pred/meas'))
for b in BANDS:
    a_, rho, Z2, Z3 = ASOLVED[b]
    fc = 0.5 * (b[0] + b[1])
    dG = -A_POOL * (Hh(fc) - 1)
    A_arm = A_DIS + C69 * dG
    pred = Z2 * A_DIS / A_arm
    print("%5.1f-%-4.1f %14.3f %+14.0f %+14.0f %14.2f" %
          (b[0], b[1], abs(A_DIS) / abs(A_arm), pred.real, Z3.real,
           pred.real / Z3.real if Z3.real else np.nan))
print("  NOTE: `c` was identified at 6-9 Hz only; using it at other bands is BELIEF.  The 6-9 Hz")
print("  row is the load-bearing one.")


# ==================================================================================================
# 4. THE INVERSION WITH BAND-SPECIFIC c/A AND A FULL EPISODE BOOTSTRAP
# ==================================================================================================
# a = -A_dis (1/rho - 1) / (c (H-1)).  `a` depends on c and A_dis only through the RATIO A_dis/c,
# which is exactly the sensitivity the 4x/8x solve constrains best.  Bootstrap:
#   - episodes of r96 and r9e independently (they set rho),
#   - AND the r85/r95 episodes jointly (they set A_dis/c),
# all in the same draw.
print()
print("=" * 100)
print("4. `a_filt` MEASURED -- band-specific c, full episode bootstrap")
print("=" * 100)
print("SINGLE-VARIABLE CLAIM VERIFIED BY BYTE DIFF (this session): V102 vs V103 = 55 bytes in 13")
print("runs -- 0x35A08/12/18 + 0xC649B (the lever), the telemetry cave 0xC4B5A/0xC4BA8-0xC4BD7,")
print("and the two CRC trailers.  0xC60A8..B7 (the biquad coefficients) are IDENTICAL. [EVIDENCE]")

G4s, Z4s = None, None


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    spG = L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER)
    spZ = L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float), eps, NPER)
    return spG, spZ


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def solve_cA(lo, hi, i4, i8):
    G4 = L.band_H([G4s[j] for j in i4], f, lo, hi)[0]
    Z4 = L.band_H([Z4s[j] for j in i4], f, lo, hi)[0]
    G8 = L.band_H([G8s[j] for j in i8], f, lo, hi)[0]
    Z8 = L.band_H([Z8s[j] for j in i8], f, lo, hi)[0]
    r = Z4 / Z8
    c = (r - 1) / (G8 - r * G4)
    return c, 1 + c * G4


rng = np.random.default_rng(17)
NB = 3000
print()
print("%10s %11s %11s %20s %9s %9s" %
      ('band', 'a point', 'Im/Re', 'a 95 % CI', 'P(a>0)', 'coh2 min'))
AFILT = {}
for b in BANDS:
    lo, hi = b
    fc = 0.5 * (lo + hi)
    dH = Hh(fc) - 1
    c_pt, A_pt = solve_cA(lo, hi, range(len(G4s)), range(len(G8s)))
    Z2 = L.band_H(MSPECS['r96'], f, lo, hi)[0]
    Z3 = L.band_H(MSPECS['r9e'], f, lo, hi)[0]
    coh_min = min(L.band_H(MSPECS['r96'], f, lo, hi)[1], L.band_H(MSPECS['r9e'], f, lo, hi)[1])
    a_pt = -A_pt * (1 / (Z3 / Z2) - 1) / (c_pt * dH)
    draws = np.empty(NB, complex)
    n2, n3 = len(MSPECS['r96']), len(MSPECS['r9e'])
    n4, n8 = len(G4s), len(G8s)
    for i in range(NB):
        c_b, A_b = solve_cA(lo, hi, rng.integers(0, n4, n4), rng.integers(0, n8, n8))
        z2 = L.band_H([MSPECS['r96'][j] for j in rng.integers(0, n2, n2)], f, lo, hi)[0]
        z3 = L.band_H([MSPECS['r9e'][j] for j in rng.integers(0, n3, n3)], f, lo, hi)[0]
        draws[i] = -A_b * (1 / (z3 / z2) - 1) / (c_b * dH)
    ci = np.percentile(draws.real, [2.5, 97.5])
    AFILT[b] = (a_pt, ci, draws)
    print("%5.1f-%-4.1f %11.4f %11.2f  [%8.4f,%8.4f] %9.3f %9.3f" %
          (lo, hi, a_pt.real, a_pt.imag / (abs(a_pt.real) + 1e-12), ci[0], ci[1],
           (draws.real > 0).mean(), coh_min))

a69 = AFILT[(6, 9)]
print()
print("  *** 6-9 Hz: a_filt = %.4f  [%.4f, %.4f], P(a>0) = %.3f, Im/Re residual %.1f %%"
      % (a69[0].real, a69[1][0], a69[1][1], (a69[2].real > 0).mean(),
         100 * a69[0].imag / abs(a69[0].real)))
print("  *** the budget-closure value (GATE2 2.2) is a = 0.098.  Ratio measured/closure = %.2f"
      % (a69[0].real / 0.098))
print("  *** f_filt = a_filt / a_closure = %.2f" % (a69[0].real / 0.098))
np.savez('_scratch/data/_v103_natexp.npz', a69=a69[2], bands=[str(b) for b in BANDS])
