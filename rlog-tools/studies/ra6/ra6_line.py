r"""ROUTE `a6` == V106 -- Q4 (THE ~8 Hz LINE vs THE FLOOR) AND Q-RATCHET (LINE vs LKAS DEMAND).

=================================================================================================
THE PRE-REGISTERED DECOMPOSITION, TAKEN VERBATIM FROM `accord-ratchet-is-a-gain-driven-line`
=================================================================================================
    LINE  = 7.4-8.6 Hz, MINUS a local background
    FLOOR = that local background x 31 bins
    512-sample windows (0.198 Hz bins at fs = 101.148)
**Pooling them dilutes a real effect by 2-3x, which is what every 6-9 Hz number in this kit's
history did.**  Local background = the median PSD over the two shoulders 5.5-7.0 and 9.0-10.5 Hz.

=================================================================================================
Q-RATCHET -- "RATCHETING IS STILL PRESENT DURING HIGH LKAS DEMAND"
=================================================================================================
This is a **WITHIN-DRIVE** question and is therefore the well-powered one: does LINE power track
instantaneous |e4tq| INSIDE route a6?  Two forms, because they fail differently:
  (a) LINE by demand DECILE, engaged, with an episode bootstrap;
  (b) the same with |motor rate| PARTIALLED OUT -- the record says the ratchet line is RATE-GATED
      (`LINE = 0 at 0-5 deg/s even on a 6x build`), and rate and demand are correlated, so a raw
      demand association could be a rate association wearing a demand label.  That confusion has
      already cost this kit one retracted claim ("band power tracks driver effort" -> it tracked
      motor rate; partial rho of effort given rate was NEGATIVE).

🛑 CONTROLS: a 32-38 Hz PLACEBO band gets the identical treatment, and every ratio is printed
   beside route a6's own split-half-by-episode null.

Usage:  python studies/ra6/ra6_line.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NPER = 512
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
LINE = (7.4, 8.6)
SH1, SH2 = (5.5, 7.0), (9.0, 10.5)
PLAC = (32.0, 38.0)
CARR = (21.0, 28.0)
TAGS = ('r97', 'ra4', 'ra5', 'ra6')
NAMES = {'r97': 'STOCK 1x', 'ra4': 'V104 6x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
OUT = {}


def load(tag):
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d.files
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    return (d, e, v, np.asarray(d['rate_f'], float),
            np.abs(np.asarray(d['rate_c'], float)), np.abs(np.asarray(d['e4tq'], float)))


def windows(x, e, v, rc, dem, vlo=0.0, vhi=1e9, min_s=2.5):
    """Per-WINDOW spectra plus the per-window covariates.  Windows are tagged with their EPISODE
    index so every bootstrap below can resample EPISODES, never windows."""
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    P, DE, RC, EP = [], [], [], []
    ei = 0
    for a, c in zip(b[:-1], b[1:]):
        if not (m[a] and (c - a) >= int(min_s * FS)):
            continue
        seg = x[a:c]
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            P.append((X.conj() * X).real / (FS * UU))
            DE.append(float(np.mean(dem[a + s:a + s + NPER])))
            RC.append(float(np.mean(rc[a + s:a + s + NPER])))
            EP.append(ei)
        ei += 1
    if not P:
        return None
    return np.array(P), np.array(DE), np.array(RC), np.array(EP)


def split(S):
    """LINE (background-subtracted), FLOOR (background x 31 bins), CARRIER and PLACEBO powers.
    S may be one spectrum or a stack; operates on the last axis."""
    kl = (FB >= LINE[0]) & (FB <= LINE[1])
    ks = ((FB >= SH1[0]) & (FB <= SH1[1])) | ((FB >= SH2[0]) & (FB <= SH2[1]))
    kc = (FB >= CARR[0]) & (FB <= CARR[1])
    kp = (FB >= PLAC[0]) & (FB <= PLAC[1])
    bg = np.median(S[..., ks], axis=-1)
    line = np.clip(S[..., kl].sum(-1) - bg * kl.sum(), 0, None) * DF
    floor = bg * 31 * DF
    return line, floor, S[..., kc].sum(-1) * DF, S[..., kp].sum(-1) * DF


# ================================================================== 1. the ladder
print("=" * 124)
print("1.  Q4 -- THE LINE (7.4-8.6 Hz, BACKGROUND-SUBTRACTED) AND THE FLOOR, SCORED SEPARATELY.")
print("    Pre-registered decomposition; 512-sample windows; engaged only.")
print("=" * 124)
W = {}
for lbl, vlo, vhi in (('engaged <16 km/h', 0, 16), ('engaged 40-95 km/h', 40, 95)):
    print("\n  %s" % lbl)
    print("%14s %6s %8s %12s %22s %12s %12s %12s"
          % ('build', 'eps', 'nwin', 'LINE', 'LINE 95 % CI', 'FLOOR', 'CARRIER', 'PLACEBO'))
    for t in TAGS:
        d, e, v, rf, rc, dem = load(t)
        w = windows(rf, e, v, rc, dem, vlo, vhi)
        if w is None or len(np.unique(w[3])) < 3:
            print("%14s   -- too few episodes --" % NAMES[t])
            continue
        P, DE, RC, EP = w
        W[(lbl, t)] = w
        ue = np.unique(EP)
        ln, fl, ca, pl = split(P.mean(0))
        rg = np.random.default_rng(313)
        bs = []
        for _ in range(2000):
            pick = rg.choice(ue, len(ue))
            sel = np.concatenate([np.flatnonzero(EP == j) for j in pick])
            bs.append(split(P[sel].mean(0))[0])
        q = np.percentile(bs, [2.5, 97.5])
        print("%14s %6d %8d %12.4f %22s %12.4f %12.4f %12.4f"
              % (NAMES[t], len(ue), len(P), ln, "[%.4f, %.4f]" % (q[0], q[1]), fl, ca, pl))
        OUT.setdefault('ladder', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            eps=int(len(ue)), nwin=int(len(P)), line=float(ln),
            line_ci=[float(q[0]), float(q[1])], floor=float(fl),
            carrier=float(ca), placebo=float(pl))

print()
print("  a6 vs a5 and a6 vs a4, each quantity, WITH route a6's own split-half-by-episode null:")
print("%20s %10s %22s %22s %10s"
      % ('regime', 'quantity', 'a6/a5 [95 % CI]', 'a6 split-half null', 'clears?'))
for lbl in ('engaged <16 km/h', 'engaged 40-95 km/h'):
    for qi, qn in enumerate(('LINE', 'FLOOR', 'CARRIER', 'PLACEBO')):
        if (lbl, 'ra6') not in W:
            continue
        P6, _, _, E6 = W[(lbl, 'ra6')]
        u6 = np.unique(E6)
        rg = np.random.default_rng(404)
        nl = []
        for _ in range(1500):
            pm = rg.permutation(u6)
            h = len(u6) // 2
            A = P6[np.isin(E6, pm[:h])].mean(0)
            B = P6[np.isin(E6, pm[h:])].mean(0)
            a_, b_ = split(A)[qi], split(B)[qi]
            nl.append(a_ / b_ if b_ > 0 else np.nan)
        nq = np.nanpercentile(nl, [2.5, 97.5])
        for other in ('ra5', 'ra4'):
            if (lbl, other) not in W:
                continue
            PO, _, _, EO = W[(lbl, other)]
            uo = np.unique(EO)
            vals = []
            for _ in range(2000):
                p6 = rg.choice(u6, len(u6))
                po = rg.choice(uo, len(uo))
                a_ = split(P6[np.concatenate([np.flatnonzero(E6 == j) for j in p6])].mean(0))[qi]
                b_ = split(PO[np.concatenate([np.flatnonzero(EO == j) for j in po])].mean(0))[qi]
                vals.append(a_ / b_ if b_ > 0 else np.nan)
            vq = np.nanpercentile(vals, [2.5, 97.5])
            med = float(np.nanmedian(vals))
            clears = not (nq[0] <= med <= nq[1])
            if other == 'ra5':
                print("%20s %10s %22s %22s %10s"
                      % (lbl, qn, "%.3f [%.3f, %.3f]" % (med, vq[0], vq[1]),
                         "[%.3f, %.3f]" % (nq[0], nq[1]), "YES" if clears else "no"))
            OUT.setdefault('ratios', {}).setdefault(lbl, {}).setdefault(qn, {})[
                'a6/%s' % other] = dict(point=med, ci=[float(vq[0]), float(vq[1])],
                                        null=[float(nq[0]), float(nq[1])], clears=bool(clears))

# ================================================================== 2. Q-RATCHET
print()
print("=" * 124)
print("2.  ⭐ Q-RATCHET -- IS THE ~8 Hz LINE DRIVEN BY LKAS DEMAND?  **WITHIN ROUTE a6 ONLY.**")
print("    (a) LINE by |e4tq| tertile;  (b) the same INSIDE motor-rate strata, because the line")
print("    is known to be RATE-GATED and rate correlates with demand.")
print("=" * 124)
d6, e6, v6, rf6, rc6, dem6 = load('ra6')
w = windows(rf6, e6, v6, rc6, dem6, 0, 1e9)
P, DE, RC, EP = w
ue = np.unique(EP)
print("  route a6: %d episodes, %d windows, %.1f s engaged" % (len(ue), len(P), e6.sum() / FS))
qd = np.percentile(DE, [33.3, 66.7])
print("\n  (a) BY LKAS DEMAND TERTILE (cuts at |e4tq| = %.0f, %.0f):" % (qd[0], qd[1]))
print("%16s %9s %12s %22s %12s %12s %12s"
      % ('demand tertile', 'nwin', 'LINE', 'LINE 95 % CI', 'FLOOR', 'CARRIER', 'PLACEBO'))
TER = {}
for i, nm in enumerate(('low', 'mid', 'HIGH')):
    m = (DE < qd[0]) if i == 0 else ((DE >= qd[1]) if i == 2 else ((DE >= qd[0]) & (DE < qd[1])))
    ln, fl, ca, pl = split(P[m].mean(0))
    rg = np.random.default_rng(515 + i)
    bs = []
    for _ in range(2000):
        pick = rg.choice(ue, len(ue))
        sel = np.concatenate([np.flatnonzero((EP == j) & m) for j in pick])
        bs.append(split(P[sel].mean(0))[0] if len(sel) > 5 else np.nan)
    q = np.nanpercentile(bs, [2.5, 97.5])
    TER[nm] = (ln, fl, ca, pl)
    print("%16s %9d %12.4f %22s %12.4f %12.4f %12.4f"
          % (nm, int(m.sum()), ln, "[%.4f, %.4f]" % (q[0], q[1]), fl, ca, pl))
    OUT.setdefault('ratchet_by_demand', {})[nm] = dict(
        nwin=int(m.sum()), line=float(ln), line_ci=[float(q[0]), float(q[1])],
        floor=float(fl), carrier=float(ca), placebo=float(pl))
print("  HIGH/low ratio:  LINE %.3f   FLOOR %.3f   CARRIER %.3f   PLACEBO %.3f"
      % tuple(TER['HIGH'][i] / TER['low'][i] if TER['low'][i] > 0 else np.nan for i in range(4)))
print("  🛑 The PLACEBO column is what says whether a LINE ratio is band-specific or a broadband")
print("     lift.  A LINE ratio that matches the PLACEBO ratio is NOT a ratchet result.")

print("\n  (b) INSIDE MOTOR-RATE STRATA -- the confound control.")
print("%14s %16s %9s %12s %12s %12s"
      % ('rate stratum', 'demand tertile', 'nwin', 'LINE', 'CARRIER', 'PLACEBO'))
RE = [0, 5, 15, 40, 1e9]
RL = ['0-5', '5-15', '15-40', '40+']
for i, rl in enumerate(RL):
    mr = (RC >= RE[i]) & (RC < RE[i + 1])
    if mr.sum() < 60:
        continue
    qq = np.percentile(DE[mr], [33.3, 66.7])
    for j, nm in enumerate(('low', 'HIGH')):
        m = mr & ((DE < qq[0]) if j == 0 else (DE >= qq[1]))
        if m.sum() < 25:
            continue
        ln, fl, ca, pl = split(P[m].mean(0))
        print("%14s %16s %9d %12.4f %12.4f %12.4f" % (rl, nm, int(m.sum()), ln, ca, pl))
        OUT.setdefault('ratchet_partialled', {}).setdefault(rl, {})[nm] = dict(
            nwin=int(m.sum()), line=float(ln), carrier=float(ca), placebo=float(pl))
print("  ⇒ if LINE(HIGH) > LINE(low) INSIDE every rate stratum, the demand association survives")
print("     the rate confound.  If it survives in none, the association was the rate all along.")

# ================================================================== 3. corr
print()
print("=" * 124)
print("3.  THE SAME QUESTION AS A PARTIAL CORRELATION, over WINDOWS but with an EPISODE bootstrap.")
print("=" * 124)
ln, fl, ca, pl = split(P)
lg = np.log(np.clip(ln, 1e-9, None))
ld = np.log(np.clip(DE, 1.0, None))
lr = np.log(np.clip(RC, 0.5, None))


def pcorr(a, b, c):
    ra = a - np.polyval(np.polyfit(c, a, 1), c)
    rb = b - np.polyval(np.polyfit(c, b, 1), c)
    return float(np.corrcoef(ra, rb)[0, 1])


rg = np.random.default_rng(909)
bs_raw, bs_par = [], []
for _ in range(2000):
    pick = rg.choice(ue, len(ue))
    sel = np.concatenate([np.flatnonzero(EP == j) for j in pick])
    bs_raw.append(np.corrcoef(lg[sel], ld[sel])[0, 1])
    bs_par.append(pcorr(lg[sel], ld[sel], lr[sel]))
print("  corr(log LINE, log |e4tq|)                 = %+.4f  [%+.4f, %+.4f]"
      % (np.corrcoef(lg, ld)[0, 1], *np.percentile(bs_raw, [2.5, 97.5])))
print("  PARTIAL, given log |motor rate|            = %+.4f  [%+.4f, %+.4f]"
      % (pcorr(lg, ld, lr), *np.percentile(bs_par, [2.5, 97.5])))
print("  corr(log LINE, log |motor rate|)           = %+.4f" % np.corrcoef(lg, lr)[0, 1])
print("  PLACEBO control: corr(log PLACEBO, log |e4tq|) partial given rate = %+.4f"
      % pcorr(np.log(np.clip(pl, 1e-9, None)), ld, lr))
OUT['ratchet_corr'] = dict(
    raw=float(np.corrcoef(lg, ld)[0, 1]),
    raw_ci=[float(x) for x in np.percentile(bs_raw, [2.5, 97.5])],
    partial=float(pcorr(lg, ld, lr)),
    partial_ci=[float(x) for x in np.percentile(bs_par, [2.5, 97.5])],
    line_vs_rate=float(np.corrcoef(lg, lr)[0, 1]),
    placebo_partial=float(pcorr(np.log(np.clip(pl, 1e-9, None)), ld, lr)))

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_line.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_line.json")
