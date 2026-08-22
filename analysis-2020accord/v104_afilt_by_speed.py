"""MEASURE `a_filt` SEPARATELY IN A LOW-SPEED AND A HIGH-SPEED ARM -- no ROM, no map model.

THE POINT
---------
v104_dose_vs_speed.py gets its speed shape s(v) from the ROM assist map.  That is a MODEL.
The V102->V103 natural experiment can be split by speed directly, which tests the same
question with the car's own data and no map at all:

    a_filt(band) = -A_dis . (1/rho(band) - 1) / (c . (H - 1)),   rho = Z_V103 / Z_V102

If a_filt is materially smaller in the high-speed arm, the ROM speed schedule is corroborated
and k = 1.85 is under-dosed on the highway.  If the two arms agree, the ROM shape is refuted
for this purpose and k = 1.85 stands.

🛑 THE CONTROL COMES FIRST.  Before quoting any band contrast this file runs:
   (a) a SPLIT-HALF null inside each speed arm (episodes interleaved) -- the contrast must be
       larger than the split-half spread or it is exposure, not speed;
   (b) a PLACEBO band (21-22.5 Hz) where `c4`'s own model says |A| ~ 1.0 and the lever is inert;
   (c) the exposure census for each arm, because an unmatched |rate| mix manufactures a contrast.

🛑 TRAPS: x6b94 read only on r85/r95.  Episode bootstrap.  Speed from `v_rear` (m/s).
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402
import check_427_alias as CA                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
KPH = 3.6
c1, c2, c3, c4 = L.honda_exact()
for t in ('r85', 'r95'):
    CA.assert_is_sum(t)


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


def win_specs_masked(x, y, keep, runmask, nper=NPER):
    """Per-run summed spectra; only windows entirely inside `keep` are used."""
    idx = np.flatnonzero(np.diff(runmask.astype(np.int8)) != 0) + 1
    bnds = np.concatenate(([0], idx, [len(runmask)]))
    step = nper // 2
    w = np.hanning(nper + 1)[:nper]
    U = (w ** 2).sum()
    tt = np.arange(nper)
    A = np.vstack([tt, np.ones(nper)]).T
    out = []
    for i in range(len(bnds) - 1):
        a0, b0 = bnds[i], bnds[i + 1]
        if not runmask[a0] or (b0 - a0) < nper:
            continue
        XS = YS = XY = None
        nw = 0
        for s in range(a0, b0 - nper + 1, step):
            if not keep[s:s + nper].all():
                continue
            xs, ys = x[s:s + nper], y[s:s + nper]
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


R = {}
for t in ('r96', 'r9e'):
    d = L.load(t)
    R[t] = dict(d=d, eng=d['cc_lat'] > 0.5,
                v=d['v_rear'].astype(float) * KPH,
                ra=np.abs(d['rate_f'].astype(float)),
                w=d['rate_f'].astype(float) * L.DEG2RAD,
                tq=d['tq'].astype(float))


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float),
                            eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def solve_cA(lo, hi, i4, i8):
    G4 = L.band_H([G4s[j] for j in i4], f, lo, hi)[0]
    Z4 = L.band_H([Z4s[j] for j in i4], f, lo, hi)[0]
    G8 = L.band_H([G8s[j] for j in i8], f, lo, hi)[0]
    Z8 = L.band_H([Z8s[j] for j in i8], f, lo, hi)[0]
    r = Z4 / Z8
    return (r - 1) / (G8 - r * G4), None


ARMS = [('LOW    18-60 km/h', 18.0, 60.0),
        ('HIGH   60-110 km/h', 60.0, 110.0),
        ('ALL    18-90 km/h (as shipped)', 18.0, 90.0)]
RHI = 60.0

print("=" * 112)
print("0. EXPOSURE CENSUS of each arm -- the contrast is meaningless if these are unmatched")
print("=" * 112)
print("%34s %7s %9s %9s %9s %9s %9s %9s" %
      ('arm', 'route', 'runs', 'windows', 'sec', 'v p50', '|rate| p50', '|tq| p50'))
SPEC = {}
for nm, vlo, vhi in ARMS:
    for t in ('r96', 'r9e'):
        r = R[t]
        keep = (r['v'] >= vlo) & (r['v'] <= vhi) & (r['ra'] <= RHI)
        sp = win_specs_masked(r['w'], r['tq'], keep, r['eng'])
        SPEC[(nm, t)] = sp
        m = keep & r['eng']
        nw = sum(s[3] for s in sp)
        print("%34s %7s %9d %9d %9.1f %9.1f %9.2f %9.0f"
              % (nm, t, len(sp), nw, nw * NPER / 2 / L.FS, np.median(r['v'][m]),
                 np.median(r['ra'][m]), np.median(np.abs(r['tq'])[m])))

BANDS = [(6, 9), (21, 22.5)]
NB = 3000
print()
print("=" * 112)
print("1. `a_filt` PER SPEED ARM -- 6-9 Hz is the load-bearing band, 21-22.5 Hz is the PLACEBO")
print("=" * 112)
print("%34s %7s %11s %11s %22s %9s %9s" %
      ('arm', 'band', '|rho|', 'a_filt', '95 % CI', 'P(a>0)', 'Im/Re'))
OUT = {}
for nm, vlo, vhi in ARMS:
    for lo, hi in BANDS:
        s96, s9e = SPEC[(nm, 'r96')], SPEC[(nm, 'r9e')]
        if len(s96) < 2 or len(s9e) < 2:
            print("%34s %7s   (too few runs: %d / %d)" % (nm, "%.0f-%.1f" % (lo, hi),
                                                          len(s96), len(s9e)))
            continue
        dH = Hh(0.5 * (lo + hi)) - 1
        c_pt, _ = solve_cA(lo, hi, range(len(G4s)), range(len(G8s)))
        A_pt = 1 + c_pt * L.band_H(G4s, f, lo, hi)[0]
        Z2 = L.band_H(s96, f, lo, hi)[0]
        Z3 = L.band_H(s9e, f, lo, hi)[0]
        a_pt = -A_pt * (1 / (Z3 / Z2) - 1) / (c_pt * dH)
        rng = np.random.default_rng(17)
        n2, n3, n4, n8 = len(s96), len(s9e), len(G4s), len(G8s)
        draws = np.empty(NB, complex)
        for i in range(NB):
            cb, _ = solve_cA(lo, hi, rng.integers(0, n4, n4), rng.integers(0, n8, n8))
            Ab = 1 + cb * L.band_H([G4s[j] for j in rng.integers(0, n4, n4)], f, lo, hi)[0]
            z2 = L.band_H([s96[j] for j in rng.integers(0, n2, n2)], f, lo, hi)[0]
            z3 = L.band_H([s9e[j] for j in rng.integers(0, n3, n3)], f, lo, hi)[0]
            draws[i] = -Ab * (1 / (z3 / z2) - 1) / (cb * dH)
        ci = np.percentile(draws.real, [2.5, 97.5])
        OUT[(nm, (lo, hi))] = (a_pt, ci, draws)
        print("%34s %7s %11.3f %11.4f  [%8.4f,%8.4f] %9.3f %9.2f"
              % (nm, "%.0f-%.1f" % (lo, hi), abs(Z3 / Z2), a_pt.real, ci[0], ci[1],
                 (draws.real > 0).mean(), a_pt.imag / (abs(a_pt.real) + 1e-12)))

print()
print("[1.1] THE CONTRAST -- HIGH / LOW at 6-9 Hz, with the placebo band beside it")
for lo, hi in BANDS:
    kl = ('LOW    18-60 km/h', (lo, hi))
    kh = ('HIGH   60-110 km/h', (lo, hi))
    if kl not in OUT or kh not in OUT:
        continue
    dl, dh = OUT[kl][2].real, OUT[kh][2].real
    ratio = dh / dl
    ratio = ratio[np.isfinite(ratio)]
    print("  %5.1f-%-5.1f Hz:  a_LOW %.4f   a_HIGH %.4f   ratio (point) %.3f   "
          "ratio 95 %% CI [%.2f, %.2f]   P(a_HIGH < a_LOW) = %.3f"
          % (lo, hi, OUT[kl][0].real, OUT[kh][0].real,
             OUT[kh][0].real / OUT[kl][0].real,
             np.percentile(ratio, 2.5), np.percentile(ratio, 97.5),
             (dh < dl).mean()))

print()
print("[1.2] SPLIT-HALF NULL inside each arm at 6-9 Hz -- interleaved episodes.")
print("      The speed contrast must exceed this spread to be a speed effect at all.")
for nm, vlo, vhi in ARMS:
    s96, s9e = SPEC[(nm, 'r96')], SPEC[(nm, 'r9e')]
    if len(s96) < 4 or len(s9e) < 4:
        print("  %34s  (too few runs for a split-half: %d / %d)" % (nm, len(s96), len(s9e)))
        continue
    dH = Hh(7.5) - 1
    c_pt, _ = solve_cA(6, 9, range(len(G4s)), range(len(G8s)))
    A_pt = 1 + c_pt * L.band_H(G4s, f, 6, 9)[0]
    vals = []
    for sl in (slice(0, None, 2), slice(1, None, 2)):
        Z2 = L.band_H(s96[sl], f, 6, 9)[0]
        Z3 = L.band_H(s9e[sl], f, 6, 9)[0]
        vals.append((-A_pt * (1 / (Z3 / Z2) - 1) / (c_pt * dH)).real)
    print("  %34s  half A %+9.4f   half B %+9.4f   ratio %7.2f"
          % (nm, vals[0], vals[1], vals[0] / vals[1] if vals[1] else np.nan))

print()
print("=" * 112)
print("2. A SECOND, MODEL-FREE READ: |rho| = |Z_V103 / Z_V102| per speed arm")
print("=" * 112)
print("  `a_filt` inherits (c, A0).  |rho| does not -- it is the raw thing the car measured.")
print("  Arming the filter should MOVE |Z| more where `a` is larger.")
print("%34s %11s %11s %22s" % ('arm', '|rho| 6-9', '|rho| 21-22.5', '|rho| 6-9 95 % CI'))
for nm, vlo, vhi in ARMS:
    s96, s9e = SPEC[(nm, 'r96')], SPEC[(nm, 'r9e')]
    if len(s96) < 2 or len(s9e) < 2:
        continue
    rng = np.random.default_rng(29)
    n2, n3 = len(s96), len(s9e)
    b = np.array([abs(L.band_H([s9e[j] for j in rng.integers(0, n3, n3)], f, 6, 9)[0]
                      / L.band_H([s96[j] for j in rng.integers(0, n2, n2)], f, 6, 9)[0])
                  for _ in range(2000)])
    r69 = abs(L.band_H(s9e, f, 6, 9)[0] / L.band_H(s96, f, 6, 9)[0])
    r21 = abs(L.band_H(s9e, f, 21, 22.5)[0] / L.band_H(s96, f, 21, 22.5)[0])
    print("%34s %11.4f %11.4f      [%7.3f, %7.3f]"
          % (nm, r69, r21, np.percentile(b, 2.5), np.percentile(b, 97.5)))
