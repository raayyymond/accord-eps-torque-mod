"""FOLLOW-UPS TO THE 2:1 HARMONIC TEST -- the three things the first pass leaves open.

D1  WHY IS b^2 = 0.19 ON *STOCK* WHILE IT IS 0.0003 ON THE 6x BUILDS?  b^2 is amplitude-weighted
    (|X(f)|^4 in the numerator), so ONE loud window can carry it.  Diagnosed by leave-one-out and
    by the effective number of windows.  If b^2 is one window, it is the `q_of = 79.00 on white
    noise` failure mode and only the unweighted R may be quoted.

D2  THE PHYSICALLY-MOTIVATED VERSION OF THE HYPOTHESIS: a nonlinearity that only engages at LARGE
    amplitude would produce phase locking ONLY in the loud windows.  So stratify by fundamental
    amplitude and recompute the UNWEIGHTED resultant per stratum, each against its own shuffle.

D3  ENVELOPE TRACKING (brief step 2) and DOSE SCALING (brief step 3), with controls.
    ⚠ envelope correlation between any two bands is positively biased by common amplitude
    modulation (the driver steers harder => everything gets louder).  The NON-HARMONIC control
    pair is the only thing that separates coupling from common AM.  Run first, quoted beside.

🛑 rate_f / rate_c only; 427 is blind above 24.9 Hz.  Episode bootstrap.  Fundamental capped at
   25 Hz so 2f stays under the measured 50.44 Hz Nyquist.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
F_LO, F_HI = 20.0, 25.0
SEL = np.flatnonzero((f >= F_LO) & (f < F_HI))
J2 = [int(np.argmin(np.abs(f - 2.0 * f[i]))) for i in SEL]
J165 = [int(np.argmin(np.abs(f - 1.65 * f[i]))) for i in SEL]


def windows(tag, sig, mask, nper=NPER):
    d = L.load(tag)
    x = d[sig].astype(float)
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    tt = np.arange(nper)
    A = np.vstack([tt, np.ones(nper)]).T
    eps, starts = [], []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not mask[a0] or (b0 - a0) < nper:
            continue
        Xs, ss = [], []
        for s in range(a0, b0 - nper + 1, nper // 2):
            xs = x[s:s + nper]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
            Xs.append(np.fft.rfft(xs * WIN))
            ss.append(s)
        if Xs:
            eps.append(np.array(Xs))
            starts.append(ss)
    return eps, starts


def b2_R(X, J):
    num = 0.0 + 0j
    d1 = d2 = 0.0
    phs = []
    for k, i in enumerate(SEL):
        j = J[k]
        tri = X[:, i] ** 2 * np.conj(X[:, j])
        num += tri.sum()
        d1 += (np.abs(X[:, i]) ** 4).sum()
        d2 += (np.abs(X[:, j]) ** 2).sum()
        phs.append(tri / (np.abs(tri) + 1e-30))
    return float(np.abs(num) ** 2 / (d1 * d2)), float(np.abs(np.concatenate(phs).mean()))


ARMS = [('STOCK 1x  ENG>=60', 'r97', lambda d, e, v: e & (v >= 60)),
        ('STOCK 1x  ENG', 'r97', lambda d, e, v: e),
        ('V102 6x   ENG', 'r96', lambda d, e, v: e),
        ('V103 6x   ENG', 'r9e', lambda d, e, v: e)]


def load_arm(tag, fn, sig='rate_f'):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    eps, _ = windows(tag, sig, fn(d, e, v))
    return np.concatenate(eps, axis=0) if eps else np.zeros((0, len(f)), complex), eps


print("=" * 116)
print("D1 -- IS b^2 CARRIED BY ONE WINDOW?  (b^2 weights by |X(f)|^4, so it can be)")
print("=" * 116)
print("%20s %6s %10s %12s %12s %12s %14s" %
      ('arm', 'nw', 'b2', 'b2 drop-1', 'top1 share', 'top5 share', 'N_eff'))
for lbl, tag, fn in ARMS:
    X, _ = load_arm(tag, fn)
    if X.shape[0] < 8:
        continue
    b2, R = b2_R(X, J2)
    w = (np.abs(X[:, SEL]) ** 4).sum(1)                 # each window's weight in the numerator
    order = np.argsort(w)[::-1]
    b2_d1 = b2_R(X[order[1:]], J2)[0]
    neff = (w.sum() ** 2) / (w ** 2).sum()              # participation ratio
    print("%20s %6d %10.4f %12.4f %12.3f %12.3f %14.1f"
          % (lbl, X.shape[0], b2, b2_d1, w[order[0]] / w.sum(), w[order[:5]].sum() / w.sum(),
             neff))
print("  N_eff = participation ratio of the |X(f)|^4 weights: the EFFECTIVE number of windows")
print("  b^2 actually averages over.  N_eff ~ 1-3 means b^2 is one or two windows and is NOT")
print("  quotable; the unweighted resultant R has N_eff = nw by construction.")

print()
print("=" * 116)
print("D2 -- AMPLITUDE-STRATIFIED PHASE LOCKING (the nonlinearity's own prediction)")
print("=" * 116)
print("  A nonlinearity that only bites at large amplitude locks phase ONLY in the loud windows.")
print("  Unweighted resultant R per amplitude quartile, each against its OWN 400-shuffle null.")
print()
print("%20s %10s %6s %10s %12s %10s" % ('arm', 'quartile', 'nw', 'R', 'null R p95', 'p'))
rng = np.random.default_rng(9)
for lbl, tag, fn in ARMS:
    X, _ = load_arm(tag, fn)
    if X.shape[0] < 16:
        continue
    amp = np.sqrt((np.abs(X[:, SEL]) ** 2).sum(1))
    q = np.quantile(amp, [0.25, 0.5, 0.75])
    strata = [('Q1 quietest', amp <= q[0]), ('Q2', (amp > q[0]) & (amp <= q[1])),
              ('Q3', (amp > q[1]) & (amp <= q[2])), ('Q4 loudest', amp > q[2])]
    for nm, m in strata:
        Xs = X[m]
        if Xs.shape[0] < 5:
            continue
        _, R = b2_R(Xs, J2)
        nulls = []
        for _ in range(400):
            Y = Xs.copy()
            perm = rng.permutation(Xs.shape[0])
            for k, i in enumerate(SEL):
                Y[:, J2[k]] = Xs[perm, J2[k]]
            nulls.append(b2_R(Y, J2)[1])
        nulls = np.array(nulls)
        print("%20s %10s %6d %10.4f %12.4f %10.4f"
              % (lbl, nm, Xs.shape[0], R, np.percentile(nulls, 95), (nulls >= R).mean()))
    print()

print("=" * 116)
print("D3a -- ENVELOPE TRACKING, with the non-harmonic control pair beside it")
print("=" * 116)


def env_corr(tag, mask, b1, b2b, nboot=2000, seed=3):
    """Spearman correlation of two bands' per-window energies, bootstrapped over EPISODES."""
    eps, _ = windows(tag, 'rate_f', mask)
    if len(eps) < 2:
        return None
    def rho(E):
        a = np.concatenate([e[0] for e in E])
        b = np.concatenate([e[1] for e in E])
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        ra -= ra.mean()
        rb -= rb.mean()
        return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    E = []
    for X in eps:
        s1 = (f >= b1[0]) & (f < b1[1])
        s2 = (f >= b2b[0]) & (f < b2b[1])
        E.append(((np.abs(X[:, s1]) ** 2).sum(1), (np.abs(X[:, s2]) ** 2).sum(1)))
    pt = rho(E)
    r = np.random.default_rng(seed)
    bb = np.array([rho([E[j] for j in r.integers(0, len(E), len(E))]) for _ in range(nboot)])
    return pt, np.percentile(bb, 2.5), np.percentile(bb, 97.5), sum(len(e[0]) for e in E)


print("%20s %26s %10s %22s %8s" % ('arm', 'band pair', 'rho', '95 % CI', 'nw'))
PAIRS = [('HARMONIC   20-25 x 40-50', (20, 25), (40, 50)),
         ('CONTROL    20-25 x 33-41', (20, 25), (33, 41)),
         ('CONTROL    20-25 x 12-17', (20, 25), (12, 17)),
         ('CONTROL     6-9  x 40-50', (6, 9), (40, 50))]
for lbl, tag, fn in ARMS[1:]:
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    for pn, b1, b2b in PAIRS:
        r = env_corr(tag, fn(d, e, v), b1, b2b)
        if r:
            print("%20s %26s %10.3f   [%8.3f, %8.3f] %8d" % (lbl, pn, r[0], r[1], r[2], r[3]))
    print()
print("  ⇒ if the HARMONIC pair's rho is not clearly above the CONTROL pairs', the correlation is")
print("    common amplitude modulation (driver effort), not quadratic coupling.")

print()
print("=" * 116)
print("D3b -- DOSE SCALING: does 40-50 Hz grow like a HARMONIC of 20-25 Hz across 0xC6CD0?")
print("=" * 116)
print("  A quadratic nonlinearity gives harmonic ~ fundamental^2; even a soft one gives")
print("  harmonic growing AT LEAST as fast as the fundamental.  Band RMS of rate_f, engaged.")
print()
print("%26s %8s %10s %10s %10s %12s %12s" %
      ('build / gain', 'nw', '20-25 Hz', '40-50 Hz', 'ratio H/F', 'F vs stock', 'H vs stock'))
BASE = {}
ROWS = [('r97  STOCK 1x', 'r97'), ('r96  V102 6x', 'r96'), ('r9e  V103 6x', 'r9e'),
        ('r95  V101 8x  (CONFOUNDED)', 'r95'), ('r85  V100 4x', 'r85')]
for nm, tag in ROWS:
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    X, _ = load_arm(tag, lambda d_, e_, v_: e_)
    if X.shape[0] < 4:
        print("%26s  (only %d windows)" % (nm, X.shape[0]))
        continue
    U = (WIN ** 2).sum()
    S = (np.abs(X) ** 2).mean(0) / (L.FS * U)
    df = f[1] - f[0]
    F = np.sqrt(S[(f >= 20) & (f < 25)].sum() * df)
    H = np.sqrt(S[(f >= 40) & (f < 50)].sum() * df)
    if tag == 'r97':
        BASE['F'], BASE['H'] = F, H
    print("%26s %8d %10.4f %10.4f %10.4f %12.2f %12.2f"
          % (nm, X.shape[0], F, H, H / F, F / BASE['F'], H / BASE['H']))
print()
print("  ⚠ r95 (V101 8x) has Lever B DISARMED and ZERO engaged seconds above 80 km/h -- it is")
print("    confounded on both counts and is shown for completeness only.")
print("  ⇒ THE TEST: if 40-50 Hz is the 2nd harmonic of 20-25 Hz, then when the fundamental grows")
print("    Nx the harmonic must grow AT LEAST Nx (and ~N^2 for a quadratic nonlinearity).")
