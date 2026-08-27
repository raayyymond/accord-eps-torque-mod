#!/usr/bin/env python3
"""D6 -- EVENT-LEVEL forensics on the 7.8 Hz train.  Is it impulsive, and what triggers it?

D5 concluded [BELIEF]: "a ~7.8 Hz impulsive event train that RINGS the ~21 Hz resonance", from
MSC(bandpass(tq,5-12), envelope(tq,12-28)) peaking at exactly 7.81 Hz, +0.225 [+0.139,+0.351] over a
circular-shift null, carrier-specific. That is coupling; it is not a mechanism. This file tries to
break it.

🛑 THE RESOLUTION CONSTRAINT, STATED UP FRONT. A 12-28 Hz band has an envelope time resolution of
~1/16 Hz = 62 ms. The inter-event interval under the hypothesis is 128 ms. So there are ~2 envelope
resolution cells per event and a decay constant can be measured only COARSELY. Worse: the kit's own
Q ~ 13.6 at 21 Hz implies tau = 2Q/omega = 206 ms, i.e. LONGER than the interval -- a lightly-damped
mode re-excited every 128 ms never decays between events, so "ring-down" and "sustained" converge in
the envelope. Every Q1 statement below is therefore made on ASYMMETRY and HIGHER MOMENTS against a
phase-randomised surrogate, not on a decay fit alone.

  Q1  impulsive or sustained -- event-triggered envelope, rise/decay asymmetry, kurtosis, and the
      HARMONIC CONTENT of the 6-9 Hz line (a stick-slip sawtooth has 2f/3f; a resonance does not).
  Q2  trigger alignment -- lowpass-rate zero crossings, command rail, a fixed magnitude, or none.
      🛑 raw `rate_c` zero crossings are CIRCULAR (the 7.8 Hz oscillation is IN rate_c and crosses
      zero twice per cycle by construction). Only the 3 Hz-lowpassed manoeuvre rate is admissible.
  Q3  event RATE dependencies -- a stick-slip rate scales with drive velocity; a resonance does not.
  Q4  V73 (route 5a) vs V72 (route 59): event RATE vs event AMPLITUDE vs RING amplitude.
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402

OUT = ROOT / "_scratch/out/_d6_events.json"
RNG = np.random.default_rng(20260806)

CARRIER = (12.0, 28.0)
RATCHET = (5.0, 12.0)
MINSEP = 0.055           # s -- allows event rates up to 18 Hz, so 7.8 Hz is MEASURED not imposed
MINRUN = 512             # 5.12 s of contiguous engagement
PARKED = {"V73/r5a": [17], "V72/r59": [12, 13, 14]}
LADDER = ["V59/r2c", "V64/r35", "V58/r2b", "V62/r37", "V65/r3a", "V65/r3b", "V67/r47",
          "V69/r4f", "V70/r50", "V71B/r54", "V71C/r58", "V72/r59", "V73/r5a"]


# ------------------------------------------------------------------ primitives -------------------
def bp(x, fs, lo, hi):
    x = np.asarray(x, float)
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    y = x - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = X[m]
    return np.fft.irfft(H, n=len(y))


def analytic(xr):
    n = len(xr)
    X = np.fft.fft(xr)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[0] = 1
        h[1:(n + 1) // 2] = 2
    return np.fft.ifft(X * h)


def phase_surrogate(x, fs, lo, hi, rng):
    """Randomise phases inside [lo,hi]; magnitudes untouched. Same power spectrum, no event structure."""
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, np.asarray(x, float), 1)
    y = np.asarray(x, float) - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    m = (f >= lo) & (f <= hi)
    H = np.zeros(len(f), complex)
    H[m] = np.abs(X[m]) * np.exp(1j * rng.uniform(0, 2 * np.pi, int(m.sum())))
    return np.fft.irfft(H, n=len(y))


def find_events(env, fs, minsep=MINSEP, k_med=1.6, k_trough=1.25, amin=0.0):
    """Local maxima of the envelope that stand above BOTH neighbouring troughs and the run median.

    Returns list of dict(i, A, i_lo, i_hi, rise_s, decay_s, tau_s) -- `i_lo`/`i_hi` are the
    bracketing troughs, so rise and decay are measured on the event's OWN excursion.
    """
    n = len(env)
    med = float(np.median(env))
    if med <= 0:
        return []
    d = np.diff(env)
    pk = np.flatnonzero((d[:-1] > 0) & (d[1:] <= 0)) + 1
    tr = np.flatnonzero((d[:-1] < 0) & (d[1:] >= 0)) + 1
    if len(pk) < 2 or len(tr) < 2:
        return []
    out, last = [], -1e9
    for p in pk:
        A = env[p]
        if A < k_med * med or A < amin:
            continue
        jl = tr[tr < p]
        jh = tr[tr > p]
        if not len(jl) or not len(jh):
            continue
        a, b = int(jl[-1]), int(jh[0])
        if A < k_trough * max(env[a], env[b]):
            continue
        if (p - last) / fs < minsep:
            if out and A > out[-1]["A"]:
                out.pop()
            else:
                continue
        seg = env[p:b + 1]
        tau = np.nan
        if len(seg) >= 3 and seg[-1] > 0 and A > 0:
            tt = np.arange(len(seg)) / fs
            with np.errstate(all="ignore"):
                sl = np.polyfit(tt, np.log(np.maximum(seg, 1e-9)), 1)[0]
            tau = float(-1.0 / sl) if sl < 0 else np.nan
        out.append(dict(i=int(p), A=float(A), i_lo=a, i_hi=b, rise_s=(p - a) / fs,
                        decay_s=(b - p) / fs, tau_s=tau))
        last = p
    return out


def runs(build, vlo=0.0, vhi=4.0, engaged=True, minrun=MINRUN):
    """Yield (build, seg, i0, i1, d, fs) for contiguous engagement runs inside the speed window."""
    B = G.BUILDS[build]
    for s in B["segs"]:
        if s in PARKED.get(build, []):
            continue
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        m = (np.asarray(d["cc_lat"], float) > 0.5) if engaged else \
            (np.asarray(d["cc_lat"], float) <= 0.5)
        v = np.abs(np.asarray(d["cs_v"], float))
        for a, b in C.runs_of(m, d["t"], minrun):
            if not (vlo <= float(np.mean(v[a:b])) < vhi):
                continue
            if not np.all(np.isfinite(d["tq"][a:b])):
                continue
            yield build, int(s), int(a), int(b), d, fs


def collect(builds, vlo=0.0, vhi=4.0, engaged=True, nsur=1):
    """All events in all qualifying runs, plus per-run surrogate events for the null."""
    ev, sur, meta = [], [], []
    for build in builds:
        for _, s, a, b, d, fs in runs(build, vlo, vhi, engaged):
            x = np.asarray(d["tq"][a:b], float)
            car = bp(x, fs, *CARRIER)
            env = np.abs(analytic(car))
            amin = 1.5 * float(np.median(env))
            es = find_events(env, fs, amin=0.0)
            rlp = C.sustained(np.asarray(d["rate_c"][a:b], float), fs, 3.0)
            rsg = bp(np.asarray(d["rate_c"][a:b], float), fs, 0.0, 3.0)
            tlp = C.sustained(x, fs, 3.0)
            e4 = np.abs(np.asarray(d["e4tq"][a:b], float))
            vv = np.abs(np.asarray(d["cs_v"][a:b], float))
            rat = np.abs(analytic(bp(x, fs, *RATCHET)))
            run = (build, s, a)
            for e in es:
                i = e["i"]
                e.update(build=build, seg=s, run=run, fs=fs, t=float(d["t"][a + i]),
                         v=float(vv[i]), rate_lp=float(rlp[i]), rate_sg=float(rsg[i]),
                         eff=float(tlp[i]), e4=float(e4[i]), rat=float(rat[i]),
                         amin=amin, nrun=b - a)
                ev.append(e)
            meta.append(dict(run=run, n=b - a, fs=fs, sec=(b - a) / fs, env_med=float(np.median(env)),
                             v=float(np.mean(vv)), nev=len(es),
                             rsg=rsg, rlp=rlp, e4=e4, t0=float(d["t"][a]), env=env, car=car,
                             x=x, rat_sig=bp(x, fs, *RATCHET)))
            for _ in range(nsur):
                ys = phase_surrogate(x, fs, *CARRIER, rng=RNG)
                en2 = np.abs(analytic(ys))
                for e in find_events(en2, fs, amin=0.0):
                    e.update(run=run, fs=fs)
                    sur.append(e)
    return ev, sur, meta


def med_ci(v, n=3000):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 3:
        return np.nan, np.nan, np.nan
    dr = np.array([np.median(v[RNG.integers(0, len(v), len(v))]) for _ in range(n)])
    return float(np.median(v)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def ep_med_ci(items, key, n=3000):
    """Median of `key`, resampling RUNS (episodes), not events."""
    by = {}
    for e in items:
        by.setdefault(e["run"], []).append(e.get(key, np.nan))
    ks = list(by)
    if len(ks) < 3:
        return np.nan, np.nan, np.nan, 0, len(ks)
    allv = np.concatenate([np.array(by[k], float) for k in ks])
    allv = allv[np.isfinite(allv)]
    dr = np.full(n, np.nan)
    for j in range(n):
        ii = RNG.integers(0, len(ks), len(ks))
        v = np.concatenate([np.array(by[ks[i]], float) for i in ii])
        v = v[np.isfinite(v)]
        if len(v):
            dr[j] = np.median(v)
    return (float(np.median(allv)), float(np.nanpercentile(dr, 2.5)),
            float(np.nanpercentile(dr, 97.5)), len(allv), len(ks))


def main():
    L.install_fs()
    res = {}
    L.hdr("D6 ss0  CORPUS -- engaged runs >= 5.12 s below 4 m/s, all builds with creep exposure")
    ev, sur, meta = collect(LADDER)
    print(f"  runs={len(meta)}   seconds={sum(m['sec'] for m in meta):.0f}   "
          f"events={len(ev)}   surrogate events={len(sur)}")
    for b in LADDER:
        mm = [m for m in meta if m["run"][0] == b]
        if mm:
            print(f"    {b:<10} runs {len(mm):>3d}  sec {sum(m['sec'] for m in mm):>7.1f}  "
                  f"events {sum(1 for e in ev if e['build'] == b):>5d}")
    res["census"] = {b: dict(runs=len([m for m in meta if m["run"][0] == b]),
                             sec=sum(m["sec"] for m in meta if m["run"][0] == b),
                             nev=sum(1 for e in ev if e["build"] == b)) for b in LADDER}

    # ------------------------------------------------------------- Q1 --------------------------
    L.hdr("Q1  IMPULSIVE OR SUSTAINED?")
    iei = []
    by = {}
    for e in ev:
        by.setdefault(e["run"], []).append(e)
    for r, es in by.items():
        es.sort(key=lambda z: z["i"])
        for p, q in zip(es[:-1], es[1:]):
            iei.append(dict(run=r, dt=(q["i"] - p["i"]) / p["fs"], v=p["v"],
                            rate_lp=abs(p["rate_lp"]), eff=abs(p["eff"]), e4=p["e4"], A=p["A"],
                            build=p["build"]))
    m, lo, hi, n, ne = ep_med_ci(iei, "dt")
    print(f"  inter-event interval: median {1000*m:.1f} ms [{1000*lo:.1f}, {1000*hi:.1f}]  "
          f"=> event rate {1/m:.2f} Hz   (n={n} intervals, {ne} runs)")
    q = np.percentile([z["dt"] for z in iei], [10, 25, 50, 75, 90])
    print(f"  IEI deciles (ms): " + "  ".join(f"{100*p:.0f}%:{1000*x:.0f}" for p, x in
                                              zip([0.1, 0.25, 0.5, 0.75, 0.9], q)))
    res["iei"] = dict(med=m, lo=lo, hi=hi, n=n, nruns=ne, rate=1 / m,
                      dec=[float(z) for z in q])

    for lab, key in (("rise (trough->peak)", "rise_s"), ("decay (peak->trough)", "decay_s")):
        o = ep_med_ci(ev, key)
        s_ = med_ci([e[key] for e in sur])
        print(f"  {lab:<22} OBS {1000*o[0]:>6.1f} ms [{1000*o[1]:.1f},{1000*o[2]:.1f}]   "
              f"phase-randomised SURROGATE {1000*s_[0]:>6.1f} ms")
        res.setdefault("shape", {})[key] = dict(obs=o[:3], sur=s_)
    asym = [e["decay_s"] / e["rise_s"] for e in ev if e["rise_s"] > 0]
    asym_s = [e["decay_s"] / e["rise_s"] for e in sur if e["rise_s"] > 0]
    ao = med_ci(asym)
    as_ = med_ci(asym_s)
    print(f"  decay/rise ASYMMETRY  OBS {ao[0]:.3f} [{ao[1]:.3f},{ao[2]:.3f}]   "
          f"SURROGATE {as_[0]:.3f} [{as_[1]:.3f},{as_[2]:.3f}]")
    print("    (a ring-down is fast-rise/slow-decay => ratio > 1; a symmetric beat => ratio ~ 1)")
    res["asym"] = dict(obs=ao, sur=as_)

    tau = ep_med_ci(ev, "tau_s")
    f0 = 21.0
    print(f"  decay time constant tau = {1000*tau[0]:.0f} ms [{1000*tau[1]:.0f},{1000*tau[2]:.0f}]"
          f"  => implied Q = pi*f0*tau = {np.pi*f0*tau[0]:.1f} at f0 = {f0:.0f} Hz")
    print("    🛑 tau is bounded ABOVE by the inter-event interval by construction -- an event ends")
    print("       at the next trough. Read it as a LOWER bound on damping, not as a free Q estimate.")
    res["tau"] = dict(med=tau[0], lo=tau[1], hi=tau[2], Q=float(np.pi * f0 * tau[0]))

    ko, ks = [], []
    for m_ in meta:
        c = m_["car"]
        ko.append(float(np.mean((c - c.mean()) ** 4) / (np.var(c) ** 2 + 1e-30)))
        y = phase_surrogate(m_["x"], m_["fs"], *CARRIER, rng=RNG)
        ks.append(float(np.mean((y - y.mean()) ** 4) / (np.var(y) ** 2 + 1e-30)))
    ko, ks = np.array(ko), np.array(ks)
    dd = ko - ks
    dr = np.array([np.median(dd[RNG.integers(0, len(dd), len(dd))]) for _ in range(3000)])
    print(f"  KURTOSIS of the 12-28 Hz carrier  OBS {np.median(ko):.3f}   "
          f"SURROGATE {np.median(ks):.3f}   paired diff {np.median(dd):+.3f} "
          f"[{np.percentile(dr,2.5):+.3f}, {np.percentile(dr,97.5):+.3f}]")
    print("    (a Gaussian band-limited process is 3.0; impulsive excitation raises it)")
    res["kurtosis"] = dict(obs=float(np.median(ko)), sur=float(np.median(ks)),
                           diff=float(np.median(dd)), lo=float(np.percentile(dr, 2.5)),
                           hi=float(np.percentile(dr, 97.5)))

    # harmonic content of the 6-9 Hz line -- a stick-slip sawtooth has 2f/3f, a resonance does not
    L.hdr("Q1b  HARMONIC CONTENT of the ratchet line -- sawtooth (stick-slip) vs sinusoid (mode)")
    acc, K, fr = None, 0, None
    for m_ in meta:
        P = C.periodogram(m_["x"][:1024], m_["fs"], 1024, True) if m_["n"] >= 1024 else None
        if P is None:
            continue
        fr = np.fft.rfftfreq(1024, 1 / m_["fs"]) if fr is None else fr
        acc = P.copy() if acc is None else acc + P
        K += 1
    if K:
        P = acc / K
        R = G.prom_spectrum(fr, P)
        f1, p1 = G.locate(fr, P, 6, 9, R=R)
        print(f"  fundamental {f1:.3f} Hz prominence {p1:.2f}   (K={K} runs)")
        for h in (2, 3, 4):
            j = int(np.argmin(np.abs(fr - h * f1)))
            w = slice(max(0, j - 3), j + 4)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            print(f"    {h}x = {h*f1:>6.2f} Hz  ->  local max {fr[k]:>6.2f} Hz prominence "
                  f"{R[k]:>6.2f}")
            res.setdefault("harmonics", {})[f"{h}x"] = dict(pred=float(h * f1),
                                                            f=float(fr[k]), prom=float(R[k]))
        res["harmonics"]["f0"] = dict(f=f1, prom=p1, K=K)

    # ------------------------------------------------------------- Q2 --------------------------
    L.hdr("Q2  WHAT TRIGGERS AN EVENT?  alignment against a matched random-time null")
    print("  null = the same number of times drawn uniformly inside the SAME runs (same exposure).\n")

    # 2.1 lowpass-rate zero crossings (NON-circular: raw rate_c contains the 7.8 Hz oscillation)
    hits_o, hits_n, tot_o = [], [], 0
    lag_o = []
    for m_ in meta:
        r = m_["rsg"]
        zc = np.flatnonzero(np.sign(r[:-1]) != np.sign(r[1:]))
        es = [e["i"] for e in by.get(m_["run"], [])]
        if not len(zc) or not es:
            continue
        for i in es:
            lag_o.append(float((i - zc[np.argmin(np.abs(zc - i))]) / m_["fs"]))
        d_o = np.array([np.min(np.abs(zc - i)) / m_["fs"] for i in es])
        rnd = RNG.integers(0, m_["n"], len(es))
        d_n = np.array([np.min(np.abs(zc - i)) / m_["fs"] for i in rnd])
        hits_o.append(float(np.mean(d_o <= 0.05)))
        hits_n.append(float(np.mean(d_n <= 0.05)))
        tot_o += len(es)
    ho, hn = np.array(hits_o), np.array(hits_n)
    dd = ho - hn
    dr = np.array([np.median(dd[RNG.integers(0, len(dd), len(dd))]) for _ in range(3000)])
    print(f"  1. LOWPASS-RATE ZERO CROSSINGS (3 Hz manoeuvre rate)  n={tot_o} events, "
          f"{len(ho)} runs")
    print(f"     fraction within +-50 ms   OBS {np.median(ho):.3f}   NULL {np.median(hn):.3f}   "
          f"diff {np.median(dd):+.3f} [{np.percentile(dr,2.5):+.3f}, {np.percentile(dr,97.5):+.3f}]")
    res.setdefault("trigger", {})["rate_zc"] = dict(obs=float(np.median(ho)),
                                                    null=float(np.median(hn)),
                                                    diff=float(np.median(dd)),
                                                    lo=float(np.percentile(dr, 2.5)),
                                                    hi=float(np.percentile(dr, 97.5)), n=tot_o)

    # 2.2 command rail
    ho, hn, nsat = [], [], 0
    for m_ in meta:
        e4 = m_["e4"]
        sat = e4 >= 4090
        edges = np.flatnonzero(sat[:-1] != sat[1:])
        es = [e["i"] for e in by.get(m_["run"], [])]
        if not len(edges) or not es:
            continue
        nsat += int(sat.sum())
        d_o = np.array([np.min(np.abs(edges - i)) / m_["fs"] for i in es])
        rnd = RNG.integers(0, m_["n"], len(es))
        d_n = np.array([np.min(np.abs(edges - i)) / m_["fs"] for i in rnd])
        ho.append(float(np.mean(d_o <= 0.10)))
        hn.append(float(np.mean(d_n <= 0.10)))
    if len(ho) >= 3:
        ho, hn = np.array(ho), np.array(hn)
        dd = ho - hn
        dr = np.array([np.median(dd[RNG.integers(0, len(dd), len(dd))]) for _ in range(3000)])
        print(f"\n  2. COMMAND RAIL (|e4tq| >= 4090) entry/exit edges  {len(ho)} runs carry any rail")
        print(f"     fraction within +-100 ms  OBS {np.median(ho):.3f}   NULL {np.median(hn):.3f}   "
              f"diff {np.median(dd):+.3f} "
              f"[{np.percentile(dr,2.5):+.3f}, {np.percentile(dr,97.5):+.3f}]")
        res["trigger"]["rail"] = dict(obs=float(np.median(ho)), null=float(np.median(hn)),
                                      diff=float(np.median(dd)),
                                      lo=float(np.percentile(dr, 2.5)),
                                      hi=float(np.percentile(dr, 97.5)), nruns=len(ho))
    else:
        print("\n  2. COMMAND RAIL -- fewer than 3 runs carry any rail edge; UNPOWERED here.")
        res["trigger"]["rail"] = dict(nruns=len(ho))

    # 2.3 a repeatable magnitude at onset
    print("\n  3. A FIXED MAGNITUDE at onset?  spread of the covariate AT the event vs at random "
          "times")
    for key, lab in (("eff", "|lowpass(tq,3Hz)| counts"), ("rate_lp", "|lowpass(rate,3Hz)| deg/s"),
                     ("v", "speed m/s")):
        vo = np.array([abs(e[key]) for e in ev], float)
        vn = []
        for m_ in meta:
            k = len(by.get(m_["run"], []))
            if not k:
                continue
            arr = {"eff": np.abs(C.sustained(m_["x"], m_["fs"], 3.0)),
                   "rate_lp": np.abs(m_["rlp"]), "v": None}[key]
            if arr is None:
                continue
            vn += list(arr[RNG.integers(0, len(arr), k)])
        if not len(vn):
            continue
        vn = np.array(vn, float)
        cv_o = float(np.std(vo) / (np.mean(vo) + 1e-9))
        cv_n = float(np.std(vn) / (np.mean(vn) + 1e-9))
        print(f"     {lab:<28} median at event {np.median(vo):>8.1f}  at random "
              f"{np.median(vn):>8.1f}   CV {cv_o:.3f} vs {cv_n:.3f}")
        res["trigger"][f"mag_{key}"] = dict(ev=float(np.median(vo)), rnd=float(np.median(vn)),
                                            cv_ev=cv_o, cv_rnd=cv_n)

    # ------------------------------------------------------------- Q3 --------------------------
    L.hdr("Q3  DOES THE EVENT RATE DEPEND ON ANYTHING?  median IEI by covariate bin")
    for key, bins, lab in (("v", [(0, 0.5), (0.5, 1.5), (1.5, 3.0), (3.0, 4.0)], "speed m/s"),
                           ("rate_lp", [(0, 5), (5, 15), (15, 40), (40, 1e9)], "|rate_lp| deg/s"),
                           ("eff", [(0, 200), (200, 800), (800, 2000), (2000, 1e9)],
                            "driver effort counts"),
                           ("e4", [(0, 500), (500, 2000), (2000, 4090), (4090, 1e9)],
                            "|e4tq| command")):
        print(f"\n  by {lab}")
        for lo_, hi_ in bins:
            sub = [z for z in iei if lo_ <= abs(z[key]) < hi_]
            if len(sub) < 30:
                print(f"    {lo_:>6.0f}-{hi_ if hi_ < 1e8 else 9999:<6.0f} n={len(sub):<5d} "
                      f"-- underpowered")
                continue
            mm, l_, h_, n_, ne_ = ep_med_ci(sub, "dt")
            print(f"    {lo_:>6.0f}-{hi_ if hi_ < 1e8 else 9999:<6.0f} n={len(sub):<5d} "
                  f"runs={ne_:<3d} IEI {1000*mm:>6.1f} ms [{1000*l_:>5.1f},{1000*h_:>5.1f}]  "
                  f"=> {1/mm:>5.2f} Hz")
            res.setdefault("q3", {})[f"{key}|{lo_}-{hi_}"] = dict(n=len(sub), nruns=ne_,
                                                                  iei=mm, lo=l_, hi=h_)

    # hands-on vs hands-off, and the MANUAL arm
    print("\n  hands-off (effort < 200) vs hands-on, and the DISENGAGED arm")
    for lab, sub in (("hands-off  eff<200", [z for z in iei if abs(z["eff"]) < 200]),
                     ("hands-on   eff>=200", [z for z in iei if abs(z["eff"]) >= 200])):
        if len(sub) < 30:
            print(f"    {lab:<22} n={len(sub)} -- underpowered")
            continue
        mm, l_, h_, n_, ne_ = ep_med_ci(sub, "dt")
        print(f"    {lab:<22} n={len(sub):<5d} runs={ne_:<3d} IEI {1000*mm:>6.1f} ms "
              f"[{1000*l_:>5.1f},{1000*h_:>5.1f}]  => {1/mm:>5.2f} Hz")
    evm, _, metam = collect(LADDER, engaged=False)
    bym = {}
    for e in evm:
        bym.setdefault(e["run"], []).append(e)
    ieim = []
    for r, es in bym.items():
        es.sort(key=lambda z: z["i"])
        for p_, q_ in zip(es[:-1], es[1:]):
            ieim.append(dict(run=r, dt=(q_["i"] - p_["i"]) / p_["fs"]))
    if len(ieim) >= 30:
        mm, l_, h_, n_, ne_ = ep_med_ci(ieim, "dt")
        print(f"    {'MANUAL (disengaged)':<22} n={len(ieim):<5d} runs={ne_:<3d} IEI "
              f"{1000*mm:>6.1f} ms [{1000*l_:>5.1f},{1000*h_:>5.1f}]  => {1/mm:>5.2f} Hz")
        res["q3_manual"] = dict(iei=mm, lo=l_, hi=h_, n=len(ieim), nruns=ne_)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
