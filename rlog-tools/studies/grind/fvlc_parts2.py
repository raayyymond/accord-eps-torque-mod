# -*- coding: utf-8 -*-
"""fvlc_parts2.py -- PARTS 5 and 7 of the FORCED vs LIMIT-CYCLE vs RESONANCE study, plus the driver.
Subagent cyclekind, 2026-09-10.  ANALYSIS ONLY.
"""
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F            # noqa: E402
import fvlc_analysis as A       # noqa: E402
import creep20_loop_id as C20   # noqa: E402
from scipy import signal as _sig  # noqa: E402

FS = A.FS
pr = A.pr
fmt = A.fmt
ci = A.ci
ORDER = A.ORDER


def _blockboot_slope(X, Y, blk, n=1200, seed=5):
    """OLS slope of Y on X with a block bootstrap over episode ids."""
    b = np.unique(blk)
    rng = np.random.default_rng(seed)
    sl = []
    for _ in range(n):
        pick = rng.choice(b, len(b), replace=True)
        m = np.concatenate([np.flatnonzero(blk == p) for p in pick])
        if len(m) < 10:
            continue
        sl.append(stats.linregress(X[m], Y[m]).slope)
    s0 = stats.linregress(X, Y).slope
    return s0, float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))


def part5(tags):
    pr("")
    pr("=" * 118)
    pr("PART 5 -- AMPLITUDE vs EXCITATION, INSIDE episodes")
    pr("=" * 118)
    pr("Regression of log(ring envelope) on log(excitation proxy), 0.25 s samples inside detected episodes, block-")
    pr("bootstrapped over episodes.  (A)/(C): amplitude tracks excitation, slope -> 1.  (B): amplitude is set by the")
    pr("nonlinearity, slope -> 0.")
    pr("THE CONTROL THAT MAKES A NULL READABLE: the identical regression with a SHAM band (%.1f +- %.1f Hz) as the"
       % (A.SHAM_C, A.HALFBW))
    pr("response, in the SAME windows.  A proxy that is merely noisy attenuates BOTH slopes; a ring with a preferred")
    pr("amplitude flattens ONLY the mode row.  Read the CONTRAST, never the mode slope alone.")
    pr("proxies: neigh = %.1f Hz band envelope (broadband excitation just above the mode) | lf = 2-6 Hz bar envelope"
       % A.NEIGH_C)
    pr("         slew = rms |d cmd| over 0.5 s | rate = |steer rate| | idx = LKAS demand index")
    pr("")
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        f0 = A._F0[b]["f0"]
        cols, blk, eid = {}, [], 0
        for t in ts:
            d = A.bands(t, f0)
            dv = A._drive_vars(t, f0)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                sl = np.arange(a, bb, 25)
                if len(sl) < 3:
                    continue
                cols.setdefault("mode", []).append(d["mode"][sl])
                cols.setdefault("sham", []).append(d["sham"][sl])
                cols.setdefault("neigh", []).append(d["neigh"][sl])
                cols.setdefault("lf", []).append(d["lf"][sl])
                cols.setdefault("slew", []).append(np.maximum(dv["slew"][sl], 1e-3))
                cols.setdefault("rate", []).append(np.maximum(dv["rate"][sl], 1e-3))
                cols.setdefault("idx", []).append(np.maximum(dv["idx"][sl], 1e-3))
                blk.append(np.full(len(sl), eid))
                eid += 1
        if eid < 5:
            pr("  %s: too few episodes" % b)
            continue
        C = {k: np.log(np.maximum(np.concatenate(v), 1e-9)) for k, v in cols.items()}
        blk = np.concatenate(blk)
        pr("  %s  (f0 %.2f Hz, %d episodes, %d samples)" % (b, f0, eid, len(blk)))
        pr("    %-8s | %-26s %-26s %10s" % ("proxy", "slope: MODE band", "slope: SHAM band (control)", "mode-sham"))
        for px in ("neigh", "lf", "slew", "rate", "idx"):
            a1 = _blockboot_slope(C[px], C["mode"], blk)
            a2 = _blockboot_slope(C[px], C["sham"], blk)
            pr("    %-8s | %-26s %-26s %10.3f" % (px, fmt(a1), fmt(a2), a1[0] - a2[0]))
        pr("")


def part7(tags):
    pr("")
    pr("=" * 118)
    pr("PART 7 -- WHAT V288's NULL ACTUALLY LICENSES")
    pr("=" * 118)
    v282 = [t for t in tags if F.BUILD.get(t) == "V282"]
    v288 = [t for t in tags if F.BUILD.get(t) == "V288"]
    r0 = rlo = rhi = np.nan
    f0 = A._F0["V282"]["f0"] if "V282" in A._F0 else 20.03
    if v282 and v288:
        pr("MEASURED FIRST: the V282 -> V288 ring amplitude ratio at %.2f Hz, matched on demand index and speed." % f0)
        pr("Windows: 0.5 s, inside detected episodes; strata = idx quartile x speed quartile, edges from the POOLED")
        pr("data so both builds see the same bins; ratio = min(n)-weighted ratio of per-stratum medians.")
        A_, B_ = [], []
        for t in v282:
            g = A.R(t)
            d = A.bands(t, f0)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                for s in range(a, bb - 49, 50):
                    A_.append((np.sqrt(np.mean(d["mode"][s:s + 50] ** 2)),
                               np.mean(g["idx"][s:s + 50]), np.mean(g["vego"][s:s + 50])))
        for t in v288:
            g = A.R(t)
            d = A.bands(t, f0)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                for s in range(a, bb - 49, 50):
                    B_.append((np.sqrt(np.mean(d["mode"][s:s + 50] ** 2)),
                               np.mean(g["idx"][s:s + 50]), np.mean(g["vego"][s:s + 50])))
        Aa, Bb = np.array(A_), np.array(B_)
        allv = np.vstack([Aa, Bb])
        qi = np.percentile(allv[:, 1], [25, 50, 75])
        qv = np.percentile(allv[:, 2], [25, 50, 75])
        sa = np.digitize(Aa[:, 1], qi) * 4 + np.digitize(Aa[:, 2], qv)
        sb = np.digitize(Bb[:, 1], qi) * 4 + np.digitize(Bb[:, 2], qv)
        rng = np.random.default_rng(11)

        def wratio(ia, ib):
            num = den = w = 0.0
            for s in range(16):
                ma = ia[sa[ia] == s]
                mb = ib[sb[ib] == s]
                if len(ma) < 5 or len(mb) < 5:
                    continue
                ww = min(len(ma), len(mb))
                num += ww * np.median(Bb[mb, 0])
                den += ww * np.median(Aa[ma, 0])
                w += ww
            return num / den if den > 0 else np.nan

        r0 = wratio(np.arange(len(Aa)), np.arange(len(Bb)))
        bs = np.array([wratio(rng.integers(0, len(Aa), len(Aa)), rng.integers(0, len(Bb), len(Bb)))
                       for _ in range(1500)])
        bs = bs[np.isfinite(bs)]
        rlo, rhi = np.percentile(bs, [2.5, 97.5])
        pr("  V282 nwin %d (%s), V288 nwin %d (%s)" % (len(Aa), ",".join(v282), len(Bb), ",".join(v288)))
        pr("  RING AMPLITUDE RATIO V288/V282 at %.2f Hz = %.3f  [%.3f - %.3f]   (95%% bootstrap)"
           % (f0, r0, rlo, rhi))
    pr("")
    K = 0.457
    pr("V288's edit: a 10.3 Hz one-pole PRE-FILTER on the SETPOINT -- on the REFERENCE, BEFORE the error former.")
    pr("|F(j2pi*20)| = %.3f.  It is OUTSIDE the loop: the return ratio L(s) is byte-identical to V282's." % K)
    pr("")
    pr("     y = [ L/(1+L) ] * F * r     +     [ G/(1+L) ] * d     +     [ 1/(1+L) ] * n")
    pr("                          ^ V288 changes ONLY this factor.  L, G, d, n are all untouched.")
    pr("")
    pr("  (A)  FORCED THROUGH THE REFERENCE   y20 = |T| |F| |r20|          predicted ratio = %.3f   (-6.8 dB, -54.3%%)" % K)
    pr("  (A') FORCED BY A DISTURBANCE (road / cogging / rack / sensor), F absent   predicted ratio = 1.000")
    pr("  (C)  EXCITED RESONANCE  y20 = |G/(1+L)| |d20|, F absent                   predicted ratio = 1.000")
    pr("  (B)  LIMIT CYCLE.  The describing-function balance is  1 + N(A) L(jw) = 0.  F DOES NOT APPEAR IN IT,")
    pr("       so A* and w* are EXACTLY unchanged.                                  predicted ratio = 1.000")
    pr("")
    pr("  ==> (B) and (C) make the SAME prediction for a REFERENCE-path filter.  V288 CANNOT SEPARATE THEM.")
    pr("      The reason is TOPOLOGICAL (the filter is not in the characteristic equation), not a property of N(A):")
    pr("      the (B) prediction is not 'nearly unchanged', it is 'exactly unchanged'.")
    pr("")
    pr("  FOR COMPLETENESS -- what a x%.3f cut IN THE LOOP would have predicted under (B):" % K)
    pr("      balance:  N(A*) kappa |L| = 1  =>  N(A*_new) = N(A*_old)/kappa,  kappa = %.3f, 1/kappa = %.3f" % (K, 1 / K))
    dA = np.linspace(1e-5, 1.0 - 1e-9, 400000)
    Nsat = (2 / np.pi) * (np.arcsin(dA) + dA * np.sqrt(1 - dA ** 2))
    for A0 in (1.5, 2.0, 3.0, 5.0, 10.0):
        N0 = float(np.interp(1.0 / A0, dA, Nsat))
        Nn = N0 / K
        if Nn >= 1.0:
            pr("      saturation, A/delta = %5.1f : N = %.4f -> N_new = %.4f > 1 IMPOSSIBLE: the cycle is EXTINGUISHED"
               % (A0, N0, Nn))
        else:
            x = float(np.interp(Nn, Nsat, dA))
            pr("      saturation, A/delta = %5.1f : N = %.4f -> A_new/A_old = %.3f" % (A0, N0, (1.0 / x) / A0))
    pr("      ideal relay / Coulomb friction, N = 4M/(pi A) exactly 1/A : A_new/A_old = kappa = %.3f" % K)
    pr("      rate limiter, |N| ~ 1/A with an A-DEPENDENT PHASE lag     : A ~ kappa  AND  w* SHIFTS")
    pr("      deadband / backlash, N <= 1 and RISING in A               : N_new > 1 impossible -> EXTINGUISHED")
    pr("      stick-slip (not a memoryless DF; A set by breakaway-minus-Coulomb and the local stiffness): ratio ~ 1")
    pr("  So had the same x0.457 been IN the loop, every classical memoryless nonlinearity would have shown either")
    pr("  ~x0.46 or outright extinction.  It was not in the loop, so none of that was ever on offer.")
    pr("")
    if np.isfinite(r0):
        pr("BOUNDS THE MEASURED NULL DOES PUT ON THINGS -- from ratio = %.3f [%.3f - %.3f]:" % (r0, rlo, rhi))
        # A reference-path contribution would push the ratio BELOW 1, so the most permissive case for it
        # is the LOWER end of the CI, not the upper one.
        for lab, rr in (("point estimate", r0), ("most permissive end of the CI", min(rlo, rhi))):
            phi_c = max((1.0 - rr) / (1.0 - K), 0.0)
            q = max((1.0 - rr ** 2) / (1.0 - K ** 2), 0.0)
            ell = max((1.0 - rr) / (1.0 - K * rr), 0.0)
            pr("  [%s: ratio %.3f]%s" % (lab, rr, "   (>= 1: the data give NO room at all for a reference"
                                            " contribution)" if rr >= 1.0 else ""))
            pr("      reference-path share of the ring AMPLITUDE, if phase-COHERENT with it : <= %.1f %%" % (100 * phi_c))
            pr("      reference-path share of the ring AMPLITUDE, if INCOHERENT             : <= %.1f %%"
               % (100 * np.sqrt(q)))
            pr("      openpilot OUTER-loop return ratio l at %.1f Hz (it passes through the setpoint, hence through F):"
               % f0)
            pr("         ratio = (1-l)/(1-%.3f l)   =>   l <= %.3f" % (K, ell))
        pr("")
        pr("  READ: V288 falsifies '(A) driven through the LKAS reference path' and bounds the openpilot outer loop's")
        pr("  contribution to the ring's regeneration.  It says NOTHING about (A') disturbance forcing, and it cannot")
        pr("  distinguish (B) from (C) even in principle.")
    pr("")



# ======================================================================================================
# PART 2b -- the Rice/Rayleigh test done on POOLED, PER-EPISODE-NORMALISED envelopes.
# Why not per-window: a +-1.5 Hz band gives B*T = 1.5 independent envelope samples in a 0.5 s window, so
# K-hat there is pure noise (the simulated Rayleigh null itself reads median 4.2 with a [0, 39] spread).
# Pooling every episode sample, each episode divided by its OWN mean first, keeps the marginal shape,
# removes the across-episode amplitude spread, and gives B*T_total ~ 10^3 independent samples.  The
# within-episode rise/decay that survives normalisation INFLATES the spread, i.e. biases K DOWN --
# conservative against a limit cycle / coherent tone.  The sham and neighbour bands get the identical
# treatment in the identical windows, and the null is simulated with the same episode-length mixture.
# ======================================================================================================
def _pool_norm(arrs):
    out = []
    for e in arrs:
        m = np.mean(e)
        if m > 0 and len(e) >= 10:
            out.append(e / m)
    return np.concatenate(out) if out else np.array([])


def _shape(x):
    """(K-hat, CV).  Rayleigh: K = 0, CV = 0.5227.  Pure tone: K -> inf, CV -> 0."""
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30:
        return np.nan, np.nan
    return A.rice_K(x), float(np.std(x) / np.mean(x))


def _null_shape(lens, halfbw, nrep=200, seed=7):
    rng = np.random.default_rng(seed)
    Ks, Cs = [], []
    for _ in range(nrep):
        segs = []
        for L in lens:
            x = rng.standard_normal(int(L) + 800)
            y = np.abs(_sig.hilbert(C20.bandpass(x, 20.0 - halfbw, 20.0 + halfbw, FS)))
            segs.append(y[400:400 + int(L)])
        k, c = _shape(_pool_norm(segs))
        Ks.append(k); Cs.append(c)
    return np.array(Ks, float), np.array(Cs, float)


def part2b(tags):
    pr("")
    pr("=" * 118)
    pr("PART 2b -- COHERENT TONE or NARROWBAND NOISE?  (Rice K and envelope CV on pooled, per-episode-normalised")
    pr("           envelopes; the 0.5 s-window version in PART 2 is uninformative and is reported only as a control)")
    pr("=" * 118)
    pr("A narrowband-filtered stationary GAUSSIAN process has a RAYLEIGH envelope: K = 0, CV = 0.5227.")
    pr("A deterministic oscillation in noise has a RICIAN envelope: K = coherent/random power, CV -> 0.")
    pr("   (C) noise-rung resonance -> K ~ 0        (A) coherent forcing -> K >> 0        (B) limit cycle -> K >> 0")
    pr("So this is a {A,B}-vs-(C) test, NOT an A-vs-B test.  Bands all +-%.1f Hz wide; SHAM %.1f Hz and NEIGH %.1f Hz"
       % (A.HALFBW, A.SHAM_C, A.NEIGH_C))
    pr("are measured in the SAME episode windows, so any artefact of windowing/normalisation hits all three equally.")
    pr("")
    pr("%-8s %6s %8s | %-22s %-22s | %-22s %-22s | %-22s" %
       ("build", "nep", "nsamp", "MODE K", "MODE CV", "SHAM K", "SHAM CV", "NEIGH K"))
    lens_all = []
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        f0 = A._F0[b]["f0"]
        seg = {"mode": [], "sham": [], "neigh": []}
        for t in ts:
            d = A.bands(t, f0)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                if bb - a < 30:
                    continue
                lens_all.append(bb - a)
                for nm in seg:
                    seg[nm].append(d[nm][a:bb])
        if len(seg["mode"]) < 5:
            pr("%-8s (too few episodes)" % b)
            continue
        P = {nm: _pool_norm(seg[nm]) for nm in seg}
        rng = np.random.default_rng(21)
        def bs(nm, which):
            out = []
            n = len(seg[nm])
            for _ in range(400):
                pick = rng.integers(0, n, n)
                v = _shape(_pool_norm([seg[nm][i] for i in pick]))
                out.append(v[0] if which == 0 else v[1])
            return np.percentile([x for x in out if np.isfinite(x)], [2.5, 97.5])
        row = []
        for nm in ("mode", "sham", "neigh"):
            k, c = _shape(P[nm])
            kl, kh = bs(nm, 0)
            cl, ch = bs(nm, 1)
            row.append(("%.2f [%.2f-%.2f]" % (k, kl, kh), "%.3f [%.3f-%.3f]" % (c, cl, ch)))
        pr("%-8s %6d %8d | %-22s %-22s | %-22s %-22s | %-22s" %
           (b, len(seg["mode"]), len(P["mode"]), row[0][0], row[0][1], row[1][0], row[1][1], row[2][0]))
    if lens_all:
        lens = np.array(lens_all)
        sel = lens[np.random.default_rng(2).integers(0, len(lens), min(len(lens), 60))]
        nk, nc = _null_shape(sel, A.HALFBW, nrep=60)
        pr("")
        pr("  SIMULATED RAYLEIGH NULL, same episode-length mixture, same +-%.1f Hz band, same normalisation:" % A.HALFBW)
        pr("     K-hat  %.3f [%.3f - %.3f]        CV  %.3f [%.3f - %.3f]     (theory: K = 0, CV = 0.5227)"
           % (np.median(nk), np.percentile(nk, 2.5), np.percentile(nk, 97.5),
              np.median(nc), np.percentile(nc, 2.5), np.percentile(nc, 97.5)))
    pr("")



# ======================================================================================================
# PART 6b -- the burst-shape statistics WITH THEIR SELECTION CONTROL.
# "decay rate after the episode's own peak" is peak-SELECTED: regression to the mean makes it positive
# even for pure noise.  "plateau fraction" likewise depends on the envelope's marginal shape.  So every
# statistic is recomputed on the SHAM band (25.5 +- 1.5 Hz) IN THE SAME EPISODE WINDOWS -- the sham band
# is selected by the mode band's detector, not by its own, so it carries the artefact and nothing else.
# The contrast mode-minus-sham is the only readable quantity here.
# ======================================================================================================
def part6b(tags):
    pr("")
    pr("=" * 118)
    pr("PART 6b -- BURST SHAPE with the peak-selection control (sham band, same windows)")
    pr("=" * 118)
    pr("Read the CONTRAST.  A self-sustained limit cycle: plateau fraction HIGH and decay ~ 0 -> mode-minus-sham")
    pr("strongly negative on decay, strongly positive on plateau.  A rung, decaying resonance: a REAL positive decay")
    pr("well above the sham artefact.  A preferred amplitude: CVlog(mode peak) well BELOW CVlog(sham peak).")
    pr("")
    pr("%-8s %5s | %-21s %-21s | %-21s %-21s | %8s %8s" %
       ("build", "nep", "decay 1/s MODE", "decay 1/s SHAM", "plateau MODE", "plateau SHAM", "CVlg md", "CVlg shm"))
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        f0 = A._F0[b]["f0"]
        D = {"mode": [], "sham": []}
        PF = {"mode": [], "sham": []}
        PK = {"mode": [], "sham": []}
        for t in ts:
            d = A.bands(t, f0)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                if bb - a < 40:
                    continue
                for nm in ("mode", "sham"):
                    e = d[nm][a:bb]
                    PK[nm].append(e.max())
                    med = np.median(e)
                    PF[nm].append(np.mean(np.abs(20 * np.log10(np.maximum(e, 1e-9) / med)) <= 2.0))
                    k = int(np.argmax(e))
                    tail = e[k:]
                    if len(tail) >= 15:
                        sl = stats.linregress(np.arange(len(tail)) / FS,
                                              np.log(np.maximum(tail, 1e-9))).slope
                        D[nm].append(-sl)
                    else:
                        D[nm].append(np.nan)
        if len(PK["mode"]) < 5:
            continue
        cm = float(np.std(np.log(np.maximum(PK["mode"], 1e-9))))
        cs = float(np.std(np.log(np.maximum(PK["sham"], 1e-9))))
        pr("%-8s %5d | %-21s %-21s | %-21s %-21s | %8.3f %8.3f" %
           (b, len(PK["mode"]), fmt(ci(D["mode"])), fmt(ci(D["sham"])),
            fmt(ci(PF["mode"])), fmt(ci(PF["sham"])), cm, cs))
    pr("")
    pr("  (decay is measured from each episode's OWN peak to its end; the sham column is the pure selection")
    pr("   artefact, since the sham band never chose those windows.)")
    pr("")



# ======================================================================================================
# PART 1b -- the frequency test done PER EPISODE, against the Kp the loop was ACTUALLY running.
# Kp is scheduled on the LKAS demand index (record 0xE5378, X = 0/68/112/136/208 counts, 16.125736 wire
# counts per LSB), so the acting Kp varies WITHIN the LERP builds as well as between builds.  That makes
# a within-corpus regression of f0 on Kp possible instead of a two-point build contrast.
#   (A) forced        : f0 pinned at the drive's frequency, moves with NEITHER gain nor loop phase
#   (B) limit cycle   : f0 = where loop phase hits -180 deg -> INDEPENDENT of a pure gain change (a real
#                       describing function N is real), MOVES when the loop phase is reshaped
#   (C) de-damped     : f0 = the plant pole -> also nearly independent of gain (a lightly damped pole's
#       plant mode      damped frequency moves as sqrt(1-zeta^2)), and a notch at the mode REMOVES the
#                       loop gain feeding it rather than moving it
# So the gain row ALONE cannot separate (B) from (C); it only kills any model in which f0 tracks gain.
# ======================================================================================================
def part1b(tags):
    pr("")
    pr("=" * 118)
    pr("PART 1b -- PER-EPISODE f0 vs the ACTING Kp, and vs the loop-PHASE change (V289's notch)")
    pr("=" * 118)
    pr("Kp record 0xE5378: X = [0, 68, 112, 136, 208] demand counts.  V278r3/V280r2 carry Y = [248, 512, 645,")
    pr("696, 696]; V281r3/V282/V288/V289 carry Y = 248 flat.  The acting Kp is read per episode from its own")
    pr("median demand index, so the LERP builds supply within-build Kp variation.")
    pr("")
    pr("%-8s %5s | %-24s %-24s %-24s" % ("build", "nep", "episode f0 (Hz)", "acting Kp", "median demand idx"))
    allf, allk, allb, allr, allv = [], [], [], [], []
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        c = F.cells(b)
        f0s, kps, idxs, rts, vgs = [], [], [], [], []
        for t in ts:
            g = A.R(t)
            eps, _ = A.EPS(t)
            for a, bb, fe in eps:
                if bb - a < 40:
                    continue
                im = float(np.median(g["idx"][a:bb]))
                f0s.append(fe); idxs.append(im)
                rts.append(float(np.median(np.abs(g["wire"][a:bb]))))
                vgs.append(float(np.median(g["vego"][a:bb])))
                kps.append(float(np.interp(im, c["kp_X"], c["kp_Y"])))
        if len(f0s) < 5:
            continue
        allf += f0s; allk += kps; allb += [b] * len(f0s); allr += rts; allv += vgs
        pr("%-8s %5d | %-24s %-24s %-24s" % (b, len(f0s), fmt(ci(f0s)), fmt(ci(kps)), fmt(ci(idxs))))
    allf, allk = np.array(allf), np.array(allk)
    allb = np.array(allb)
    pre = np.isin(allb, ["V278r3", "V280r2", "V281r3", "V282", "V288"])   # every build BEFORE the notch
    pr("")
    pr("  GAIN ROW -- regression of episode f0 on acting Kp, restricted to the FIVE pre-notch builds")
    pr("  (V278r3, V280r2, V281r3, V282, V288: identical loop PHASE, Kp is the only thing that differs):")
    if pre.sum() > 20:
        rng = np.random.default_rng(9)
        sl = stats.linregress(allk[pre], allf[pre])
        bs = []
        ii = np.flatnonzero(pre)
        for _ in range(3000):
            m = rng.choice(ii, len(ii), replace=True)
            bs.append(stats.linregress(allk[m], allf[m]).slope)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        pr("     d f0 / d Kp = %+.5f Hz per Kp count  [%+.5f - %+.5f]   (n = %d episodes, r = %+.3f, p = %.3g)"
           % (sl.slope, lo, hi, int(pre.sum()), sl.rvalue, sl.pvalue))
        pr("     over the measured Kp span %.0f -> %.0f that is %+.2f Hz [%+.2f - %+.2f]"
           % (allk[pre].min(), allk[pre].max(),
              sl.slope * (allk[pre].max() - allk[pre].min()),
              lo * (allk[pre].max() - allk[pre].min()), hi * (allk[pre].max() - allk[pre].min())))
    pr("")
    pr("  IS THE LINE TIED TO A ROTATING / RATE-DEPENDENT SOURCE?  A forced drive from motor cogging, gear mesh or")
    pr("  a tooth-pass scales with SHAFT SPEED.  Per-episode f0 regressed on the episode's own median |steer rate|")
    pr("  and vehicle speed, within the pre-notch builds:")
    if pre.sum() > 20:
        rng2 = np.random.default_rng(13)
        ii = np.flatnonzero(pre)
        for nm, arr in (("|steer rate| (raw counts)", np.array(allr)), ("vEgo (m/s)", np.array(allv))):
            sl = stats.linregress(arr[pre], allf[pre])
            bs = [stats.linregress(arr[m], allf[m]).slope
                  for m in (rng2.choice(ii, len(ii), replace=True) for _ in range(2000))]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            span = np.percentile(arr[pre], 90) - np.percentile(arr[pre], 10)
            pr("     d f0 / d %-26s = %+.5f [%+.5f - %+.5f]  -> %+.2f Hz over the p10-p90 span (%.1f)"
               % (nm, sl.slope, lo, hi, sl.slope * span, span))
    pr("")
    pr("  PHASE ROW -- V289 put a 20.04 Hz Q3 notch on the loop output and raised the feedback pole 16.5 -> 25 Hz.")
    pr("  Kp, Kd, the clamps, the gain LERPs and the map are BYTE-IDENTICAL to V282.  Pure phase, zero gain change")
    pr("  at the loop's low-frequency operating point.")
    m282 = allb == "V282"
    m289 = allb == "V289"
    if m282.sum() > 5 and m289.sum() > 5:
        a1 = ci(allf[m282]); a2 = ci(allf[m289])
        pr("     V282 episode f0 %s Hz   ->   V289 episode f0 %s Hz   :  %+.2f Hz"
           % (fmt(a1), fmt(a2), a2[0] - a1[0]))
    pr("")



# ======================================================================================================
# PART 2c -- THE DECISIVE {A,B} vs (C) TEST: how long does the line stay PHASE-COHERENT?
#
# Demodulate the band at its own f0 and measure |<z(t) z*(t+tau)>| / <|z|^2>, the complex-envelope
# autocorrelation, pooled over episodes.  Physics:
#   (C) a lightly damped pole rung by broadband noise      -> |rho(tau)| = exp(-zeta w0 tau) EXACTLY,
#       i.e. the coherence time IS the ring-down time, tau_c = 1/(zeta w0).  At zeta = 0.029, f0 = 20 Hz
#       that is 0.27 s, about 5.5 cycles.
#   (A) a coherent external drive, or (B) a self-sustained limit cycle -> phase persists for as long as
#       the source does: tau_c >> 1/(zeta w0), limited only by episode length and frequency wander.
# The +-HB Hz bandpass imposes its OWN coherence floor of about 1/(pi * 2HB); HB is set WIDE here (3 Hz,
# floor ~0.053 s) so the floor sits far below both predictions.  The SHAM band, demodulated at its own
# peak in the same windows, measures that floor empirically.
# ======================================================================================================
def part2c(tags, HB=3.0, TAUMAX=1.0):
    pr("")
    pr("=" * 118)
    pr("PART 2c -- PHASE COHERENCE TIME of the line  (the decisive {A,B}-vs-(C) discriminator)")
    pr("=" * 118)
    pr("|rho(tau)| = |<z z*>|/<|z|^2> of the demodulated analytic signal, pooled over episodes, fitted over")
    pr("tau in [0.02, %.2f] s.  (C) predicts tau_c = 1/(zeta w0) -- the ring-down time itself.  (A)/(B) predict" % TAUMAX)
    pr("tau_c far longer.  Bands +-%.1f Hz (filter coherence floor ~%.3f s); SHAM measures that floor." % (HB, 1 / (np.pi * 2 * HB)))
    pr("")
    pr("%-8s %5s | %-13s %-13s %-9s | %-13s %-9s | %s" %
       ("build", "nep", "tau_c MODE s", "cycles", "zeta_eq", "tau_c SHAM s", "sham cyc", "ratio mode/sham"))
    lags = np.arange(2, int(TAUMAX * FS) + 1)
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        f0 = A._F0[b]["f0"]
        acc = {"mode": [np.zeros(len(lags)), np.zeros(len(lags)), 0.0],
               "sham": [np.zeros(len(lags)), np.zeros(len(lags)), 0.0]}
        nep = 0
        for t in ts:
            g = A.R(t)
            eps, _ = A.EPS(t)
            x = g["bar"]
            for nm, c in (("mode", f0), ("sham", A.SHAM_C)):
                z = _sig.hilbert(C20.bandpass(x, c - HB, c + HB, FS))
                tt = np.arange(len(z)) / FS
                zd = z * np.exp(-2j * np.pi * c * tt)
                g["_z_" + nm] = zd
            for a, bb, fe in eps:
                if bb - a < int(TAUMAX * FS) + 40:
                    continue
                nep += 1
                for nm in ("mode", "sham"):
                    zd = g["_z_" + nm][a:bb]
                    p0 = float(np.mean(np.abs(zd) ** 2))
                    for i, L in enumerate(lags):
                        acc[nm][0][i] += np.real(np.vdot(zd[:-L], zd[L:]))
                        acc[nm][1][i] += np.imag(np.vdot(zd[:-L], zd[L:]))
                    acc[nm][2] += p0 * (len(zd) - 1)
            for nm in ("mode", "sham"):
                g.pop("_z_" + nm, None)
        if nep < 5:
            pr("%-8s %5d | (too few long episodes)" % (b, nep))
            continue
        out = {}
        for nm in ("mode", "sham"):
            rho = np.hypot(acc[nm][0], acc[nm][1]) / max(acc[nm][2], 1e-9)
            rho = np.clip(rho / max(rho[0], 1e-9), 1e-6, 1.0)
            sl = stats.linregress(lags / FS, np.log(rho))
            out[nm] = -1.0 / sl.slope if sl.slope < 0 else np.inf
        w0 = 2 * np.pi * f0
        pr("%-8s %5d | %-13.3f %-13.1f %-9.4f | %-13.3f %-9.1f | %.2f" %
           (b, nep, out["mode"], out["mode"] * f0, 1.0 / (out["mode"] * w0),
            out["sham"], out["sham"] * A.SHAM_C, out["mode"] / max(out["sham"], 1e-9)))
    pr("")
    pr("  READ: tau_c a few tenths of a second, i.e. a handful of cycles, and an equivalent zeta in the same")
    pr("  ballpark as the free-decay zeta, means the line is a DAMPED MODE BEING RUNG -- there is no persistent")
    pr("  phase, so there is no persistent source.  tau_c of seconds would mean a coherent drive or a cycle.")
    pr("")



# ======================================================================================================
# PART 4b -- the harmonic test as a POWER RATIO with an explicit DETECTION BOUND.
# "the prominence did not move" is not a measurement.  This reports P(k f0)/P(f0) in dB against the local
# floor, and -- the part that makes a null readable -- the SAME ratio at two sham multiples, which is the
# level at which this instrument can no longer tell a harmonic from the floor.
# ⚠ WEAKNESS, stated: these are PHYSICAL channels downstream of the rack, so a 40 or 60 Hz harmonic is
# attenuated by the plant before it is measured.  A null here bounds the harmonic AT THE SENSOR, not the
# harmonic content of an internal nonlinearity.
# ======================================================================================================
def part4b(tags):
    pr("")
    pr("=" * 118)
    pr("PART 4b -- harmonic POWER RATIOS P(k f0)/P(f0), in dB, with the sham-multiple detection bound")
    pr("=" * 118)
    pr("Pooled 2 s periodograms inside episodes.  Each entry is 10 log10 [ P(k f0) / P(f0) ] with the local")
    pr("median floor SUBTRACTED from both, so a band at the floor reads -inf and is printed as '< floor'.")
    pr("REFERENCE: an ideal relay limit cycle puts 3f0 at -9.5 dB of f0 and 5f0 at -14 dB; a saturation or")
    pr("rate-limit cycle less.  A linear response, forced or resonant, puts NOTHING there.")
    pr("")
    for chan in ("bar", "wire", "ang"):
        pr("  channel %s" % chan)
        pr("    %-8s %6s | %8s %8s %8s | %8s %8s" % ("build", "nwin", "f0 (abs)", "2f0 dB", "3f0 dB", "1.4f0 dB", "2.4f0 dB"))
        for b in ORDER:
            ts = [t for t in tags if F.BUILD.get(t) == b]
            if not ts:
                continue
            f0 = A._F0[b]["f0"]
            Ps, n, fgrid = 0.0, 0, None
            for t in ts:
                g = A.R(t)
                eps, _ = A.EPS(t)
                st = []
                for a, bb, fe in eps:
                    if bb - a >= 200:
                        st += list(range(a, bb - 199, 100))
                if not st:
                    continue
                st = np.array(st, int)
                for c0 in range(0, len(st), 256):
                    fq, P = A.win_spec(g[chan], st[c0:c0 + 256], 200)
                    fgrid = fq
                    Ps = Ps + P.sum(axis=0)
                n += len(st)
            if fgrid is None or n < 5:
                continue
            P = Ps / n
            rows, Rr = A._prom_band(fgrid, P, 5.0, 49.4)
            fr = fgrid[rows]
            Pr = P[rows]
            fl = Pr / np.maximum(Rr, 1e-12)                 # the local median floor, recovered
            exc = np.maximum(Pr - fl, 0.0)                  # excess power above the floor
            def pk(ff):
                ff = ff if ff <= 50.0 else 100.0 - ff
                m = (fr > ff - 0.6) & (fr < ff + 0.6)
                return float(np.max(exc[m])) if m.any() else np.nan
            p0 = pk(f0)
            def db(ff):
                v = pk(ff)
                if not np.isfinite(v) or v <= 0 or p0 <= 0:
                    return None
                return 10 * np.log10(v / p0)
            def fm(ff):
                d = db(ff)
                return "< floor" if d is None else "%8.1f" % d
            pr("    %-8s %6d | %8.3g %8s %8s | %8s %8s" %
               (b, n, p0, fm(2 * f0), fm(3 * f0), fm(1.4 * f0), fm(2.4 * f0)))
        pr("")


def main():
    tags = [t for t in F.ROUTES if os.path.exists(os.path.join(F.SCR, "fvlc_%s.pkl" % t))]
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    parts = argv or ["0", "1", "2", "3", "4", "5", "6", "7"]
    pr("FORCED (A) vs LIMIT CYCLE (B) vs EXCITED RESONANCE (C) -- 2026-09-10, subagent cyclekind")
    pr("routes with caches: %s" % ", ".join("%s/%s" % (t, F.BUILD[t]) for t in tags))
    pr("EPISODE DEMAND GATE: median LKAS demand index >= %g  (0 = no gate)" % A.EP_MINIDX)
    pr("")
    A.part0_1(tags)
    part1b(tags)
    if "2" in parts:
        A.part2(tags)
    if "2" in parts or "2b" in parts:
        part2b(tags)
    if "2" in parts or "2c" in parts:
        part2c(tags)
    if "6" in parts:
        A.part6(tags)
        part6b(tags)
    if "3" in parts:
        A.part3(tags)
    if "4" in parts:
        A.part4(tags)
        part4b(tags)
    if "5" in parts:
        part5(tags)
    if "7" in parts:
        part7(tags)
    A.dump()
    print("\nwrote %s" % os.path.join(F.SCR, "fvlc_analysis.txt"))


if __name__ == "__main__":
    main()
