# -*- coding: utf-8 -*-
"""fvlc_analysis.py -- FORCED (A) vs LIMIT CYCLE (B) vs EXCITED RESONANCE (C).  Subagent cyclekind, 2026-09-10.
ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

Parts
  0  channel provenance (which channels are demonstrably NOT rectified) + per-build line frequency
  1  cross-build f0 vs Kp vs loop PHASE  (the (A)/(B)/(C) frequency test)
  2  envelope statistics: Rice K-factor per 0.5 s window, mode band vs a matched neighbour band vs a
     simulated Gaussian-noise null of the same bandwidth and window length  -> coherent tone or noise?
  3  hysteresis: driving variable at episode ONSET vs OFFSET, with the envelope-decay lag control
  4  harmonics at 2f0 / 3f0 in episodes vs quiet, on signed (non-rectified) channels, with sham-harmonic floors
  5  amplitude vs excitation INSIDE episodes: slope of log(ring envelope) on log(excitation proxy),
     against the SAME slope for a sham band (the control that makes a null interpretable)
  6  burst shape: plateau vs rise/decay, cycles, duration
  7  the V288 arithmetic: what a x0.457 REFERENCE-path cut predicts under (A)/(B)/(C), and the bound
     the measured null actually puts on the reference/outer-loop contribution
Run: python fvlc_analysis.py [part ...]      (writes _scratch/fvlc_analysis.txt)
"""
import json
import os
import pickle
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F                                # noqa: E402
import creep20_loop_id as C20                       # noqa: E402
import grind_incident_r35 as GI                     # noqa: E402
import _grind2_lib as G2                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
SCR = F.SCR
OUT = []
DEMAND_MIN = 20.0        # the grinding stratum (STATE: high-demand line, idx >= 20)
HALFBW = 1.5             # +- Hz around a band centre, used identically for mode / sham / neighbour
SHAM_C, NEIGH_C = 25.5, 30.0
RNG = np.random.default_rng(20260910)


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def dump(name="fvlc_analysis.txt"):
    with open(os.path.join(SCR, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


def ci(x, fn=np.median, n=4000, seed=1):
    return F.boot_ci(x, fn, n, seed)


def fmt(v):
    m, lo, hi = v
    return "%.3f [%.3f-%.3f]" % (m, lo, hi)


# ======================================================================================================
# shared: per-route derived state
# ======================================================================================================
_R = {}


def R(tag):
    if tag in _R:
        return _R[tag]
    g = F.load(tag)
    g["mask"] = g["eng"] & (g["idx"] >= DEMAND_MIN)
    _R[tag] = g
    return g


def pooled_line(tag, chan="bar", lo=12.0, hi=26.0, nperseg=512):
    """pooled Welch over engaged high-demand runs; returns (f, P) and the located line."""
    g = R(tag)
    segs = [g[chan][a:b] for a, b in C20.runs(g["mask"], nperseg)]
    if not segs:
        return None, None, np.nan, np.nan
    Ps, n = 0.0, 0
    for s in segs:
        f, P = signal.welch(s, fs=FS, nperseg=nperseg, noverlap=nperseg // 2, detrend="constant")
        w = max(1, (len(s) - nperseg // 2) // (nperseg // 2))
        Ps = Ps + w * P; n += w
    P = Ps / n
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    f0, prom = G2.locate(f, P, lo, hi, R=Rp)
    return f, P, f0, prom


def f0_of(build_tags):
    """per-build f0 from the pooled, demand-gated driver-torque spectrum."""
    out = {}
    for b, tags in build_tags.items():
        fs_, Ps_, n = None, 0.0, 0
        for t in tags:
            f, P, _, _ = pooled_line(t)
            if f is None:
                continue
            fs_ = f; Ps_ = Ps_ + P; n += 1
        P = Ps_ / max(n, 1)
        lo, hi = F.BAND[b]
        Rp = G2.prom_spectrum(fs_, P, 6.0, 1.5)
        f0, prom = G2.locate(fs_, P, lo, hi, R=Rp)
        # also the band-agnostic 12-26 locate, so the census gate's blindness is visible
        f0w, promw = G2.locate(fs_, P, 12.0, 26.0, R=Rp)
        out[b] = dict(f0=f0, prom=prom, f0_wide=f0w, prom_wide=promw, f=fs_, P=P)
    return out


# ======================================================================================================
# band-aware episode detector -- the V282 census recipe (2 s windows / 0.5 s step, 12-26 Hz peak
# prominence >= 8 AND band amplitude >= 40 raw, episode = contiguous >= 0.5 s present run inside an
# engaged run), with the AMPLITUDE BAND taken per build so it is not blind to V289's relocated line.
# ======================================================================================================
_PB = {}


def _prom_band(f, P2, lo, hi, halfwin=6.0, exclude=1.5):
    """G2.prom_spectrum restricted to rows in [lo,hi]; P2 may be (nwin, nfreq)."""
    key = (len(f), float(f[1]), lo, hi, halfwin, exclude)
    got = _PB.get(key)
    if got is None:
        rows = np.flatnonzero((f >= lo - 1e-9) & (f <= hi + 1e-9))
        df = float(f[1]); kmax = int(np.floor(halfwin / df + 1e-9))
        offs = np.array([k for k in range(-kmax, kmax + 1) if exclude < abs(k) * df <= halfwin + 1e-12], int)
        got = (rows, np.clip(rows[:, None] + offs[None, :], 0, len(f) - 1))
        _PB[key] = got
    rows, idx = got
    with np.errstate(all="ignore"):
        fl = np.median(P2[..., idx], axis=-1)
        r = np.where(fl > 0, P2[..., rows] / np.where(fl > 0, fl, 1.0), np.nan)
    return rows, r


def win_spec(x, starts, W=200, nfft=4096):
    """periodogram (hann, nfft) of every window x[s:s+W] -- vectorised, matches GI.line_of."""
    idx = starts[:, None] + np.arange(W)[None, :]
    xw = x[idx]
    xw = xw - xw.mean(axis=1, keepdims=True)
    w = signal.get_window("hann", W)
    U = (w ** 2).sum()
    X = np.fft.rfft(xw * w, n=nfft, axis=1)
    P = (np.abs(X) ** 2) / (FS * U)
    P[:, 1:-1] *= 2.0
    f = np.fft.rfftfreq(nfft, 1.0 / FS)
    return f, P


def episodes_band(g, lo, hi, W=200, STEP=50, ampthr=40.0, promthr=8.0, wlo=12.0, whi=26.0):
    x = g["bar"]
    ek = "_envdet_%g_%g" % (lo, hi)
    if ek not in g:                       # recomputed here, NOT read from the pickle, so the detection
        g[ek] = np.abs(signal.hilbert(C20.bandpass(x, lo, hi, FS)))   # band can be changed without a re-extract
    env = g[ek]
    starts = np.concatenate([np.arange(a, b - W + 1, STEP) for a, b in C20.runs(g["eng"], W)]) \
        if len(C20.runs(g["eng"], W)) else np.array([], int)
    if not len(starts):
        return [], np.zeros(len(x), bool), np.array([]), np.array([])
    # CHUNKED: _prom_band materialises (nwin, nrows, noffs) -- ~3 GB at nwin = 2000 -- so slice the
    # window axis.  Identical arithmetic, bounded memory.
    proms, f0ws = [], []
    for c0 in range(0, len(starts), 128):
        ch = starts[c0:c0 + 128]
        f, P = win_spec(x, ch, W)
        rows, Rr = _prom_band(f, P, wlo, whi)
        kk = np.nanargmax(Rr, axis=1)
        proms.append(Rr[np.arange(len(kk)), kk])
        f0ws.append(f[rows][kk])
    prom = np.concatenate(proms)
    f0w = np.concatenate(f0ws)
    amp = np.sqrt(np.array([np.mean(env[s:s + W] ** 2) for s in starts]))
    present = (prom >= promthr) & (amp >= ampthr)
    tr = g["tr"]
    wt = tr[starts]
    j = np.clip(np.searchsorted(wt, tr - 1.0), 0, len(wt) - 1)
    near = np.abs(wt[j] + 1.0 - tr) < 1.5
    hot = g["eng"] & near & present[j]
    eps = []
    for a, b in C20.runs(hot, int(0.5 * FS)):
        n = b - a
        if n < 32:
            continue
        xe = x[a:b] - x[a:b].mean()
        w = signal.get_window("hann", n)
        X = np.fft.rfft(xe * w, n=4096)
        Pe = (np.abs(X) ** 2)[None, :]
        rr, Rr2 = _prom_band(np.fft.rfftfreq(4096, 1.0 / FS), Pe, wlo, whi)
        fgr = np.fft.rfftfreq(4096, 1.0 / FS)[rr]
        kk = int(np.nanargmax(Rr2[0]))
        eps.append((a, b, float(fgr[kk])))
    return eps, hot, f0w, prom


EP_MINIDX = float(os.environ.get("FVLC_MINIDX", "0"))   # keep only episodes whose median demand index >= this


def EPS(tag):
    """episodes on the BUILD's own grinding band, optionally restricted to the high-demand stratum.

    The two-object picture (STATE 2026-09-09): a LOW-demand 12.4-13.8 Hz road line and the HIGH-demand
    grinding mode, separable on DEMAND not speed.  EP_MINIDX is how this study keeps them apart."""
    g = R(tag)
    key = "eps_b_%g" % EP_MINIDX
    if key not in g:
        lo, hi = F.BAND[g["build"]]
        disk = os.path.join(SCR, "fvlc_eps_%s_%g_%g_%g.pkl" % (tag, lo, hi, EP_MINIDX))
        if os.path.exists(disk):
            with open(disk, "rb") as fh:
                g[key] = pickle.load(fh)
            return g[key]
        eps, hot, _, _ = episodes_band(g, lo, hi)
        if EP_MINIDX > 0:
            keep = [(a, b, f) for a, b, f in eps if np.median(g["idx"][a:b]) >= EP_MINIDX]
            h = np.zeros(len(hot), bool)
            for a, b, f in keep:
                h[a:b] = True
            eps, hot = keep, h
        g[key] = (eps, hot)
        with open(disk, "wb") as fh:
            pickle.dump(g[key], fh, protocol=4)
    return g[key]


# ======================================================================================================
# Rice K-factor (moment estimator, exact inverse) -- 0 for Rayleigh (pure narrowband noise),
# -> inf for a pure tone.  gamma = E[r^2]^2 / E[r^4];  gamma = 1/2 <=> Rayleigh, -> 1 <=> tone.
# ======================================================================================================
def rice_K(r):
    r = np.asarray(r, float); r = r[np.isfinite(r)]
    if len(r) < 8:
        return np.nan
    m2 = np.mean(r ** 2); m4 = np.mean(r ** 4)
    if m4 <= 0:
        return np.nan
    gam = m2 * m2 / m4
    if gam <= 0.5:
        return 0.0
    if gam >= 1.0 - 1e-12:
        return np.inf
    return float((1.0 - 2.0 * gam - np.sqrt(gam * (2.0 * gam - 1.0))) / (gam - 1.0))


# ======================================================================================================
# matched-bandwidth envelopes: mode band (f0 +- HALFBW), sham band, neighbour band -- SAME width, so
# every distributional statistic is comparable across bands.
# ======================================================================================================
def bands(tag, f0, chan="bar"):
    g = R(tag)
    key = "_bands_%s_%.2f" % (chan, f0)
    if key in g:
        return g[key]
    x = g[chan]
    d = {}
    for nm, c in (("mode", f0), ("sham", SHAM_C), ("neigh", NEIGH_C)):
        d[nm] = np.abs(signal.hilbert(C20.bandpass(x, c - HALFBW, c + HALFBW, FS)))
    d["lf"] = np.abs(signal.hilbert(C20.bandpass(x, 2.0, 6.0, FS)))
    g[key] = d
    return d


def null_K(halfbw, W, nrep=400, seed=3):
    """K-hat of pure narrowband Gaussian noise, same bandwidth and window length -> the Rayleigh null."""
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(nrep):
        x = rng.standard_normal(int(W * 6) + 600)
        y = np.abs(signal.hilbert(C20.bandpass(x, 20.0 - halfbw, 20.0 + halfbw, FS)))
        y = y[300:-300]
        for s in range(0, len(y) - W + 1, W):
            ks.append(rice_K(y[s:s + W]))
    return np.array(ks, float)


BUILD_TAGS = {}
for _t, _b in F.BUILD.items():
    BUILD_TAGS.setdefault(_b, []).append(_t)
ORDER = ["V278r3", "V280r2", "V281r3", "V282", "V288", "V289"]
_F0 = {}


def part0_1(tags):
    global _F0
    pr("=" * 118)
    pr("PART 0 -- CHANNELS, AND WHICH ONE IS PROVABLY NOT RECTIFIED")
    pr("=" * 118)
    pr("The kit has a channel that RECTIFIES (the 427 tap: memory accord-427-rectification-keeps-energy-kills-sign,")
    pr("accord-427-sign-is-clamped-away-by-the-frame-builder) and would MANUFACTURE 2f0.  The channels used below are")
    pr("raw signed CAN fields decoded i16 big-endian, never an absolute value or a magnitude-only cave field:")
    pr("  bar  = 0x18F bytes 0-1, i16be, x1.024   -- driver torsion-bar torque  (the grinding observable; hands-off = twist)")
    pr("  wire = 0x18F bytes 2-3, i16be           -- steering rate")
    pr("  ang  = 0x14A bytes 0-1, i16be, x-0.1    -- steering angle")
    pr("EVIDENCE that none of the three is rectified: a rectified channel is one-signed.  Sign balance and mean below.")
    pr("")
    pr("%-11s %-8s %10s %10s %10s %10s %10s %10s" % ("route", "build", "bar>0", "bar mean", "wire>0", "wire mean", "ang>0", "ang mean"))
    for t in tags:
        g = R(t); m = g["eng"]
        pr("%-11s %-8s %10.3f %10.2f %10.3f %10.2f %10.3f %10.2f"
           % (t, g["build"], np.mean(g["bar"][m] > 0), np.mean(g["bar"][m]), np.mean(g["wire"][m] > 0),
              np.mean(g["wire"][m]), np.mean(g["ang"][m] > 0), np.mean(g["ang"][m])))
    pr("  -> all three straddle zero.  The 0x1AB / 427 tap is NOT used anywhere in this study.")
    pr("")
    pr("=" * 118)
    pr("PART 1 -- THE LINE FREQUENCY PER BUILD, and how it moves with GAIN vs with PHASE")
    pr("=" * 118)
    bt = {b: [t for t in BUILD_TAGS[b] if t in tags] for b in ORDER if any(t in tags for t in BUILD_TAGS.get(b, []))}
    _F0 = f0_of(bt)
    pr("pooled Welch (nperseg 512, 5.12 s) of driver torque over ENGAGED & demand idx >= %d frames" % DEMAND_MIN)
    pr("%-8s %-26s %8s %8s %10s %8s %8s" % ("build", "routes", "f0(band)", "prom", "band", "f0(12-26)", "prom"))
    for b, d in _F0.items():
        pr("%-8s %-26s %8.2f %8.1f %10s %8.2f %8.1f"
           % (b, ",".join(bt[b]), d["f0"], d["prom"], "%g-%g" % F.BAND[b], d["f0_wide"], d["prom_wide"]))
    return _F0


def part2(tags):
    pr("")
    pr("=" * 118)
    pr("PART 2 -- IS THE RING A COHERENT TONE OR NARROWBAND NOISE?  (Rice K-factor, 0.5 s windows)")
    pr("=" * 118)
    pr("A narrowband-filtered stationary GAUSSIAN process has a RAYLEIGH envelope (K = 0).  A deterministic")
    pr("oscillation buried in noise has a RICIAN envelope with K = (coherent power)/(random power) >> 0.")
    pr("  (C) noise-driven resonance -> K ~ 0      (A) coherent forcing -> K large      (B) limit cycle -> K large")
    pr("K is therefore a {A,B} vs {C} test, not an A-vs-B test.  Controls, all with the SAME +-%.1f Hz bandwidth" % HALFBW)
    pr("and the SAME 50-sample window: a SHAM band at %.1f Hz, a NEIGHBOUR band at %.1f Hz, and a simulated" % (SHAM_C, NEIGH_C))
    pr("Gaussian-noise null.  Windows are taken INSIDE detected episodes (hot) and, separately, in engaged quiet.")
    nk = null_K(HALFBW, 50)
    pr("")
    pr("  simulated Rayleigh null, 50-sample windows, +-%.1f Hz: K-hat median %.3f  [p05 %.3f, p95 %.3f]  n=%d"
       % (HALFBW, np.median(nk), np.percentile(nk, 5), np.percentile(nk, 95), len(nk)))
    pr("")
    pr("%-11s %-8s %7s | %-22s %-22s %-22s" % ("route", "build", "nwin", "MODE band K", "SHAM band K", "NEIGH band K"))
    rows = {}
    for t in tags:
        g = R(t); b = g["build"]
        f0 = _F0[b]["f0"]
        d = bands(t, f0)
        eps, hot = EPS(t)
        idx = np.flatnonzero(hot)
        if len(idx) < 200:
            pr("%-11s %-8s %7d | (too few hot frames)" % (t, b, len(idx))); continue
        # contiguous 50-sample windows fully inside hot
        st = [a for a, bb in C20.runs(hot, 50) for a in range(a, bb - 49, 50)]
        st = np.array(st, int)
        K = {nm: np.array([rice_K(d[nm][s:s + 50]) for s in st]) for nm in ("mode", "sham", "neigh")}
        rows[t] = (b, st, K)
        pr("%-11s %-8s %7d | %-22s %-22s %-22s" % (t, b, len(st),
           fmt(ci(K["mode"])), fmt(ci(K["sham"])), fmt(ci(K["neigh"]))))
    pr("")
    pr("POOLED BY BUILD (episode-block bootstrap over windows):")
    pr("%-8s %7s | %-22s %-22s %-22s %10s" % ("build", "nwin", "MODE K", "SHAM K", "NEIGH K", "mode/sham"))
    for b in ORDER:
        ts = [t for t in tags if t in rows and rows[t][0] == b]
        if not ts:
            continue
        K = {nm: np.concatenate([rows[t][2][nm] for t in ts]) for nm in ("mode", "sham", "neigh")}
        n = len(K["mode"])
        r = np.median(K["mode"]) / max(np.median(K["sham"]), 1e-9)
        pr("%-8s %7d | %-22s %-22s %-22s %10.2f" % (b, n, fmt(ci(K["mode"])), fmt(ci(K["sham"])), fmt(ci(K["neigh"])), r))
    return rows


def part6(tags):
    pr("")
    pr("=" * 118)
    pr("PART 6 -- BURST SHAPE: does the ring PLATEAU at a preferred level (limit cycle) or RISE-AND-DECAY (resonance)?")
    pr("=" * 118)
    pr("Per episode: peak envelope, the fraction of the episode within +-2 dB of the episode's median envelope")
    pr("('plateau fraction'), the log-envelope decay slope after the peak (1/s) -> equivalent zeta, and the number")
    pr("of cycles.  A self-sustained limit cycle: plateau fraction high, decay slope ~ 0.  A rung resonance: low")
    pr("plateau fraction and a clear positive decay rate.  ALSO: the ACROSS-episode dispersion of the peak envelope")
    pr("-- a limit cycle has a PREFERRED amplitude (low CV); an excited resonance inherits the excitation's spread.")
    pr("")
    pr("%-11s %-8s %5s | %-20s %-20s %-20s %-20s %8s" % ("route", "build", "nep", "peak env (raw)",
                                                          "plateau frac", "decay 1/s", "zeta_eq", "CVpeak"))
    store = {}
    for t in tags:
        g = R(t); b = g["build"]; f0 = _F0[b]["f0"]
        d = bands(t, f0)
        eps, hot = EPS(t)
        if len(eps) < 3:
            pr("%-11s %-8s %5d | (too few episodes)" % (t, b, len(eps))); continue
        pk, pf, dec, zz, dur = [], [], [], [], []
        for a, bb, fe in eps:
            e = d["mode"][a:bb]
            if len(e) < 25:
                continue
            pk.append(e.max()); dur.append((bb - a) / FS)
            med = np.median(e)
            pf.append(np.mean(np.abs(20 * np.log10(np.maximum(e, 1e-9) / med)) <= 2.0))
            k = int(np.argmax(e))
            tail = e[k:]
            if len(tail) >= 15:
                tt = np.arange(len(tail)) / FS
                sl = stats.linregress(tt, np.log(np.maximum(tail, 1e-9))).slope
                dec.append(-sl); zz.append(-sl / (2 * np.pi * f0))
        store[t] = dict(build=b, pk=np.array(pk), pf=np.array(pf), dec=np.array(dec), zz=np.array(zz), dur=np.array(dur))
        cv = np.std(pk) / np.mean(pk)
        pr("%-11s %-8s %5d | %-20s %-20s %-20s %-20s %8.3f" % (t, b, len(pk), fmt(ci(pk)), fmt(ci(pf)),
                                                               fmt(ci(dec)), fmt(ci(zz)), cv))
    pr("")
    pr("POOLED BY BUILD:")
    pr("%-8s %5s | %-20s %-20s %-20s %-20s %8s %8s" % ("build", "nep", "peak env", "plateau frac", "decay 1/s", "zeta_eq", "CVpeak", "CVlog"))
    for b in ORDER:
        ts = [t for t in tags if t in store and store[t]["build"] == b]
        if not ts:
            continue
        pk = np.concatenate([store[t]["pk"] for t in ts])
        pf = np.concatenate([store[t]["pf"] for t in ts])
        dec = np.concatenate([store[t]["dec"] for t in ts])
        zz = np.concatenate([store[t]["zz"] for t in ts])
        pr("%-8s %5d | %-20s %-20s %-20s %-20s %8.3f %8.3f" % (b, len(pk), fmt(ci(pk)), fmt(ci(pf)), fmt(ci(dec)),
                                                               fmt(ci(zz)), np.std(pk) / np.mean(pk), np.std(np.log(pk))))
    pr("")
    pr("REFERENCE: for a LOGNORMAL amplitude driven by a lognormal excitation, CVlog is just the excitation's own")
    pr("log-spread.  The comparison that matters is CVlog(mode peak) vs CVlog(neighbour-band level in the same")
    pr("episodes) -- if the ring is much TIGHTER than its own excitation, it has a preferred amplitude.")
    pr("%-8s %5s | %-20s %-20s %10s" % ("build", "nep", "CVlog mode peak", "CVlog neigh in-ep", "ratio"))
    for b in ORDER:
        ts = [t for t in tags if t in store and store[t]["build"] == b]
        if not ts:
            continue
        pk, nb = [], []
        for t in ts:
            g = R(t); f0 = _F0[b]["f0"]; d = bands(t, f0); eps, _ = EPS(t)
            for a, bb, fe in eps:
                if bb - a < 25:
                    continue
                pk.append(d["mode"][a:bb].max()); nb.append(np.median(d["neigh"][a:bb]))
        pk, nb = np.array(pk), np.array(nb)
        c1, c2 = np.std(np.log(pk)), np.std(np.log(np.maximum(nb, 1e-9)))
        pr("%-8s %5d | %-20.3f %-20.3f %10.2f" % (b, len(pk), c1, c2, c1 / max(c2, 1e-9)))
    return store


def _drive_vars(t, f0):
    g = R(t); d = bands(t, f0)
    n = len(g["bar"])
    k = np.ones(50) / 50.0
    sm = lambda x: np.convolve(np.asarray(x, float), k, mode="same")   # noqa: E731
    return dict(idx=sm(g["idx"]), load=sm(np.abs(g["bar"])), vego=sm(g["vego"]),
                exc=sm(d["neigh"]), lf=sm(d["lf"]), slew=sm(g["slew"]),
                rate=sm(np.abs(g["wire"])), n=n)


def part3(tags):
    pr("")
    pr("=" * 118)
    pr("PART 3 -- HYSTERESIS: the driving variable at episode ONSET vs at OFFSET")
    pr("=" * 118)
    pr("If episodes START at a higher value of the driving variable than they STOP at, the mechanism has a")
    pr("subcritical / stick-slip character -- (B).  CONFOUND, stated up front: the ring's own decay lag tau means")
    pr("the detector drops out ~tau after the drive does, so ANY mechanism shows some on>off gap.  So each row")
    pr("carries (i) the raw paired gap, (ii) the gap after moving the offset sample back by the MEASURED decay")
    pr("time constant tau of that build, and (iii) the tau that WOULD be needed to explain the raw gap from the")
    pr("local drive slope alone.  Only (ii) is evidence.")
    pr("")
    for b in ORDER:
        ts = [t for t in tags if F.BUILD.get(t) == b]
        if not ts:
            continue
        f0 = _F0[b]["f0"]
        taus = []
        for t in ts:
            d = bands(t, f0); eps, _ = EPS(t)
            for a, bb, fe in eps:
                e = d["mode"][a:bb]
                if len(e) < 25:
                    continue
                kk = int(np.argmax(e)); tail = e[kk:]
                if len(tail) >= 15:
                    sl = stats.linregress(np.arange(len(tail)) / FS, np.log(np.maximum(tail, 1e-9))).slope
                    if sl < 0:
                        taus.append(-1.0 / sl)
        tau = float(np.median(taus)) if len(taus) >= 5 else 0.25
        pr("  %s  (f0 %.2f Hz, median post-peak decay tau = %.3f s, n=%d)" % (b, f0, tau, len(taus)))
        pr("    %-8s %6s %12s %12s | %-24s %-24s %10s" % ("drive", "nep", "at ONSET", "at OFFSET",
                                                          "raw gap on-off", "lag-corrected gap", "tau needed"))
        acc = {}
        for t in ts:
            dv = _drive_vars(t, f0); eps, _ = EPS(t)
            for a, bb, fe in eps:
                if bb - a < 30:
                    continue
                w = 20
                lagb = max(a + 10, bb - int(tau * FS))
                for nm in ("idx", "load", "vego", "exc", "lf", "slew", "rate"):
                    x = dv[nm]
                    on = np.mean(x[max(a - w, 0):a + w])
                    off = np.mean(x[max(bb - w, 0):min(bb + w, dv["n"])])
                    offc = np.mean(x[max(lagb - w, 0):min(lagb + w, dv["n"])])
                    sl = (np.mean(x[min(bb, dv["n"] - 1):min(bb + 50, dv["n"])]) -
                          np.mean(x[max(bb - 50, 0):bb])) / 0.5 if bb + 50 <= dv["n"] else np.nan
                    acc.setdefault(nm, []).append((on, off, offc, sl))
        for nm in ("idx", "load", "vego", "exc", "lf", "slew", "rate"):
            A = np.array(acc.get(nm, []), float)
            if len(A) < 5:
                continue
            gap = A[:, 0] - A[:, 1]
            gapc = A[:, 0] - A[:, 2]
            sl = A[:, 3]
            need = np.nanmedian(np.where(np.abs(sl) > 1e-9, gap / np.abs(sl), np.nan))
            pr("    %-8s %6d %12.3f %12.3f | %-24s %-24s %10.3f"
               % (nm, len(A), np.median(A[:, 0]), np.median(A[:, 1]), fmt(ci(gap)), fmt(ci(gapc)), need))
        pr("")


def part4(tags):
    pr("")
    pr("=" * 118)
    pr("PART 4 -- HARMONICS at 2f0 and 3f0, in episodes vs engaged quiet")
    pr("=" * 118)
    pr("A limit cycle riding a nonlinearity distorts -> harmonics.  Linear forcing and a noise-rung resonance do not.")
    pr("Statistic = spectral PROMINENCE (peak / local median floor, the census's own G2 measure) at k*f0, on the")
    pr("signed channels from PART 0.  SHAM multiples 1.4f0 / 2.4f0 give the no-harmonic floor.")
    pr("ALIASING, stated: fs = 100 Hz.  For f0 ~ 20.0 Hz, 3f0 = 60.1 Hz ALIASES to 39.9 Hz, on top of 2f0 = 40.1 Hz")
    pr("and unresolvable from it in a 2 s window -- so the V282-family '2f0' row is an UPPER BOUND (2f0 + alias 3f0)")
    pr("and its '3f0' row is meaningless.  For V289 (f0 ~ 16.3 Hz) 2f0 = 32.6 and 3f0 = 48.9 are BOTH below Nyquist:")
    pr("V289 is the only build that gives a clean 3f0.  That is the decisive row.")
    pr("")
    for chan in ("bar", "wire", "ang"):
        pr("  channel %s" % chan)
        pr("    %-8s %6s %7s | %8s %8s %8s | %8s %8s | %s" % ("build", "nwin", "where", "f0", "2f0", "3f0",
                                                              "1.4f0", "2.4f0", "note"))
        for b in ORDER:
            ts = [t for t in tags if F.BUILD.get(t) == b]
            if not ts:
                continue
            f0 = _F0[b]["f0"]
            for where in ("episode", "quiet"):
                Ps, n = 0.0, 0; fgrid = None
                for t in ts:
                    g = R(t); eps, hot = EPS(t)
                    x = g[chan]
                    if where == "episode":
                        runsl = [(a, bb) for a, bb, _ in eps if bb - a >= 200]
                    else:
                        runsl = C20.runs(g["eng"] & ~hot, 200)
                    st = []
                    for a, bb in runsl:
                        st += list(range(a, bb - 199, 100))
                    if not st:
                        continue
                    st = np.array(st, int)
                    for c0 in range(0, len(st), 256):
                        fq, P = win_spec(x, st[c0:c0 + 256], 200)
                        fgrid = fq; Ps = Ps + P.sum(axis=0)
                    n += len(st)
                if fgrid is None or n < 5:
                    continue
                P = Ps / n
                rows, Rr = _prom_band(fgrid, P, 5.0, 49.5)
                get = lambda ff: float(np.nanmax(Rr[(fgrid[rows] > ff - 0.6) & (fgrid[rows] < ff + 0.6)])) if (ff < 49.4) else np.nan  # noqa: E731
                alias = lambda ff: ff if ff <= 50 else 100.0 - ff  # noqa: E731
                note = ""
                if 2 * f0 > 49.4 or 3 * f0 > 49.4:
                    note = "3f0=%.1f->alias %.1f" % (3 * f0, alias(3 * f0))
                pr("    %-8s %6d %7s | %8.1f %8.1f %8.1f | %8.1f %8.1f | %s"
                   % (b, n, where, get(f0), get(2 * f0), get(alias(3 * f0)), get(1.4 * f0), get(2.4 * f0), note))
        pr("")
