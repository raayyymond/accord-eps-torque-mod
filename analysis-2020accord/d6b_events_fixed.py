#!/usr/bin/env python3
"""D6b -- Q1-Q4 redone after `d6_events.py` exposed an artefact in its own detector.

🛑 WHAT WAS WRONG IN D6. Events were defined as maxima of the 12-28 Hz envelope. A 16 Hz-wide band's
envelope fluctuates at roughly BW/2 whatever the physics, and the PHASE-RANDOMISED SURROGATE produced
rise/decay of 80 ms against the observed 60 ms -- i.e. the same order. So d6's "event rate 6.67 Hz"
is set by the filter bandwidth, not by the car, and its Q3 table inherits a detection-threshold
confound (low amplitude => fewer envelope maxima clear the threshold => longer apparent interval).
The two d6 results that DO survive are the ones taken against the surrogate or in the spectrum:
kurtosis +2.271 [+1.629, +3.186], and the harmonic structure.

WHAT REPLACES IT
  Q1  the ratchet's own WAVEFORM: harmonic content (odd/even), and burstiness measured at two time
      scales -- kurtosis of the raw band, and kurtosis after dividing out a 0.5 s envelope. If the
      excess kurtosis survives slow-envelope normalisation the burstiness is FAST (impulsive);
      if it disappears the signal is a near-sinusoid whose amplitude wanders on a ~second scale.
  Q2  BURST ONSET triggers. If the oscillation is sustained rather than impulsive, "what triggers an
      event" becomes "what precedes a burst". Compare each covariate in the 0.5 s BEFORE onset
      against the run's own background, run-paired.
  Q3  the LINE FREQUENCY per episode vs covariates -- the non-circular way to ask whether the rate
      scales with anything. A stick-slip rate scales with drive velocity; a resonance does not.
  Q4  V73 (route 5a) vs V72 (route 59): burst RATE vs burst AMPLITUDE vs RING amplitude.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from d6_events import LADDER, analytic, bp, collect, ep_med_ci, med_ci, phase_surrogate, runs

OUT = ROOT / "_d6b_events.json"
RNG = np.random.default_rng(6062026)
CARRIER, RATCHET = (12.0, 28.0), (5.0, 12.0)


def bursts(env, fs, k=1.8, minlen=0.30):
    """Contiguous stretches where the ratchet envelope exceeds k x its run median. Returns
    [(i0, i1, peak)] -- the ON periods of the oscillation, the unit a limit cycle actually has."""
    thr = k * float(np.median(env))
    m = env > thr
    out = []
    i = 0
    n = len(m)
    while i < n:
        if not m[i]:
            i += 1
            continue
        j = i
        while j < n and m[j]:
            j += 1
        if (j - i) / fs >= minlen:
            out.append((i, j, float(np.max(env[i:j]))))
        i = j
    return out


def main():
    L.install_fs()
    res = {}
    ev, sur, meta = collect(LADDER)
    L.hdr("D6b Q1  IS THE 7.8 Hz THING IMPULSIVE, OR A NEAR-SINUSOID THAT COMES AND GOES?")

    # --- harmonic content, on the RATCHET band's own fundamental ------------------------------
    acc, K, fr = None, 0, None
    for m_ in meta:
        if m_["n"] < 2048:
            continue
        P = C.periodogram(m_["x"][:2048], m_["fs"], 2048, True)
        if P is None:
            continue
        fr = np.fft.rfftfreq(2048, 1 / m_["fs"]) if fr is None else fr
        acc = P.copy() if acc is None else acc + P
        K += 1
    P = acc / K
    R = G.prom_spectrum(fr, P)
    f0, p0 = G.locate(fr, P, 6, 9, R=R)
    print(f"  fundamental {f0:.3f} Hz prominence {p0:.2f}  (NFFT 2048 = 20.5 s, "
          f"{100/2048:.3f} Hz bins, K={K} runs)")
    print("  a stick-slip / impulse train has a FULL harmonic series (2f, 3f, 4f ~ 1/n);")
    print("  a near-sinusoid has none; a symmetric relay (Coulomb) has ODD harmonics only.")
    harm = {}
    for h in range(2, 7):
        j = int(np.argmin(np.abs(fr - h * f0)))
        w = slice(max(0, j - 4), j + 5)
        k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
        harm[f"{h}x"] = dict(pred=float(h * f0), f=float(fr[k]), prom=float(R[k]))
        print(f"    {h}x = {h*f0:>6.2f} Hz -> local max {fr[k]:>6.2f} Hz prominence {R[k]:>6.2f}"
              + ("   <- this is the INDEPENDENT ~21 Hz mode, not a harmonic (D5: no tracking)"
                 if h == 3 else ""))
    res["harmonics"] = dict(f0=f0, prom=p0, K=K, **harm)

    # --- burstiness at two time scales ---------------------------------------------------------
    print("\n  BURSTINESS AT TWO TIME SCALES -- kurtosis of the band, raw and slow-envelope-normalised")
    rows = {}
    for lab, band in (("ratchet 5-12", RATCHET), ("carrier 12-28", CARRIER)):
        ko, kn, ks = [], [], []
        for m_ in meta:
            fs = m_["fs"]
            y = bp(m_["x"], fs, *band)
            e = np.abs(analytic(y))
            slow = np.abs(analytic(bp(e - e.mean(), fs, 0.0, 2.0))) + e.mean()
            yn = y / np.maximum(slow, 1e-6)
            kur = lambda z: float(np.mean((z - z.mean()) ** 4) / (np.var(z) ** 2 + 1e-30))  # noqa
            ko.append(kur(y))
            kn.append(kur(yn))
            ks.append(kur(phase_surrogate(m_["x"], fs, *band, rng=RNG)))
        ko, kn, ks = np.array(ko), np.array(kn), np.array(ks)
        d1, d2 = ko - ks, kn - ks
        b = lambda z: np.percentile(  # noqa
            [np.median(z[RNG.integers(0, len(z), len(z))]) for _ in range(3000)], [2.5, 97.5])
        c1, c2 = b(d1), b(d2)
        print(f"    {lab:<14} raw {np.median(ko):.2f}  slow-normalised {np.median(kn):.2f}  "
              f"surrogate {np.median(ks):.2f}")
        print(f"    {'':<14} excess raw {np.median(d1):+.2f} [{c1[0]:+.2f},{c1[1]:+.2f}]   "
              f"excess AFTER removing the slow envelope {np.median(d2):+.2f} "
              f"[{c2[0]:+.2f},{c2[1]:+.2f}]")
        rows[lab] = dict(raw=float(np.median(ko)), norm=float(np.median(kn)),
                         sur=float(np.median(ks)), d_raw=float(np.median(d1)),
                         d_raw_ci=[float(c1[0]), float(c1[1])], d_norm=float(np.median(d2)),
                         d_norm_ci=[float(c2[0]), float(c2[1])])
    res["kurtosis"] = rows

    # --- burst inventory ----------------------------------------------------------------------
    L.hdr("D6b Q1b  BURST INVENTORY -- how long is the oscillation ON, and how often does it start?")
    binfo, allb = [], []
    for m_ in meta:
        fs = m_["fs"]
        e = np.abs(analytic(bp(m_["x"], fs, *RATCHET)))
        bs = bursts(e, fs)
        binfo.append(dict(run=m_["run"], sec=m_["sec"], nb=len(bs),
                          duty=float(sum(j - i for i, j, _ in bs) / max(len(e), 1))))
        for i, j, pk in bs:
            allb.append(dict(run=m_["run"], build=m_["run"][0], i0=i, i1=j, fs=fs,
                             dur=(j - i) / fs, peak=pk, meta=m_))
    d_, l_, h_, n_, ne_ = ep_med_ci([dict(run=z["run"], dur=z["dur"]) for z in allb], "dur")
    print(f"  bursts={len(allb)}   median duration {1000*d_:.0f} ms [{1000*l_:.0f},{1000*h_:.0f}]"
          f"   = {d_*f0:.1f} cycles of the {f0:.2f} Hz line")
    duty = med_ci([z["duty"] for z in binfo])
    rate = med_ci([z["nb"] / z["sec"] for z in binfo])
    print(f"  duty cycle {duty[0]:.3f} [{duty[1]:.3f},{duty[2]:.3f}]   "
          f"burst onsets {rate[0]:.3f}/s [{rate[1]:.3f},{rate[2]:.3f}]")
    res["bursts"] = dict(n=len(allb), dur=d_, dur_lo=l_, dur_hi=h_, cycles=float(d_ * f0),
                         duty=duty, rate=rate)

    # ------------------------------------------------------------- Q2 --------------------------
    L.hdr("D6b Q2  WHAT PRECEDES A BURST?  covariate in the 0.5 s BEFORE onset vs the run background")
    print("  run-paired log ratio, bootstrapped over RUNS. >0 means the covariate is elevated "
          "before onset.\n")
    chans = {"|rate_lp| deg/s": lambda m: np.abs(m["rlp"]),
             "|lowpass(tq)| effort": lambda m: np.abs(C.sustained(m["x"], m["fs"], 3.0)),
             "|e4tq| command": lambda m: m["e4"],
             "rail duty |e4|>=4090": lambda m: (m["e4"] >= 4090).astype(float),
             "|d/dt rate_lp| deg/s2": lambda m: np.abs(np.gradient(m["rlp"], 1 / m["fs"])),
             "speed m/s": lambda m: np.full(len(m["x"]), m["v"])}
    for lab, fn in chans.items():
        per = {}
        for z in allb:
            m_ = z["meta"]
            arr = fn(m_)
            a = max(0, z["i0"] - int(0.5 * z["fs"]))
            pre = float(np.mean(arr[a:z["i0"]])) if z["i0"] > a else np.nan
            bg = float(np.mean(arr))
            if np.isfinite(pre) and bg > 1e-9:
                per.setdefault(z["run"], []).append(np.log((pre + 1e-9) / (bg + 1e-9)))
        ks = [k for k, v in per.items() if v]
        if len(ks) < 5:
            print(f"  {lab:<24} -- underpowered")
            continue
        pm = np.array([np.median(per[k]) for k in ks])
        dr = np.array([np.median(pm[RNG.integers(0, len(pm), len(pm))]) for _ in range(3000)])
        lo, hi = np.percentile(dr, [2.5, 97.5])
        star = "  <== ELEVATED" if lo > 0 else ("  <== SUPPRESSED" if hi < 0 else "")
        print(f"  {lab:<24} log-ratio {np.median(pm):+.3f} [{lo:+.3f}, {hi:+.3f}]  "
              f"(x{np.exp(np.median(pm)):.2f}){star}")
        res.setdefault("onset", {})[lab] = dict(lr=float(np.median(pm)), lo=float(lo),
                                                hi=float(hi), nruns=len(ks))

    # ------------------------------------------------------------- Q3 --------------------------
    L.hdr("D6b Q3  DOES THE LINE FREQUENCY MOVE?  per-window f0 in the free 5-12 Hz band")
    print("  🛑 measured in the SPECTRUM, so it carries no detection-threshold confound. Windows")
    print("     below 12.5 m/s only, so tyre order 1 (v/2.080) stays under 6 Hz.\n")
    pw = []
    for build in LADDER:
        for _, s, a, b, d, fs in runs(build, 0.0, 12.5, True, 512):
            x = np.asarray(d["tq"][a:b], float)
            rlp = np.abs(C.sustained(np.asarray(d["rate_c"][a:b], float), fs, 3.0))
            eff = np.abs(C.sustained(x, fs, 3.0))
            e4 = np.abs(np.asarray(d["e4tq"][a:b], float))
            vv = np.abs(np.asarray(d["cs_v"][a:b], float))
            f = np.fft.rfftfreq(512, 1 / fs)
            for i in range(0, len(x) - 512 + 1, 256):
                P = C.periodogram(x[i:i + 512], fs, 512, True)
                if P is None:
                    continue
                R = G.prom_spectrum(f, P)
                ff, pp = G.locate(f, P, 5, 12, R=R)
                if not np.isfinite(ff) or pp < 3.0:
                    continue
                pw.append(dict(run=(build, s, a), build=build, f0=ff, prom=pp,
                               v=float(np.mean(vv[i:i + 512])),
                               rate=float(np.mean(rlp[i:i + 512])),
                               eff=float(np.mean(eff[i:i + 512])),
                               e4=float(np.mean(e4[i:i + 512]))))
    m0, l0, h0, n0, ne0 = ep_med_ci(pw, "f0")
    print(f"  overall f0 = {m0:.3f} Hz [{l0:.3f}, {h0:.3f}]   n={n0} windows, {ne0} runs")
    for key, bins, lab in (("v", [(0, 1), (1, 3), (3, 6), (6, 12.5)], "speed m/s"),
                           ("rate", [(0, 5), (5, 15), (15, 40), (40, 1e9)], "|rate_lp| deg/s"),
                           ("eff", [(0, 200), (200, 800), (800, 2000), (2000, 1e9)], "effort"),
                           ("e4", [(0, 500), (500, 2000), (2000, 4089), (4089, 1e9)], "|e4tq|")):
        print(f"\n  by {lab}")
        for lo_, hi_ in bins:
            sub = [z for z in pw if lo_ <= z[key] < hi_]
            if len(sub) < 25:
                print(f"    {lo_:>6.0f}-{hi_ if hi_ < 1e8 else 9999:<6.0f} n={len(sub):<4d} "
                      f"-- underpowered")
                continue
            mm, l_, h_, n_, ne_ = ep_med_ci(sub, "f0")
            print(f"    {lo_:>6.0f}-{hi_ if hi_ < 1e8 else 9999:<6.0f} n={len(sub):<4d} "
                  f"runs={ne_:<3d}  f0 = {mm:>6.3f} Hz [{l_:>6.3f}, {h_:>6.3f}]")
            res.setdefault("q3", {})[f"{key}|{lo_}"] = dict(n=len(sub), f0=mm, lo=l_, hi=h_)
    res["f0_overall"] = dict(f0=m0, lo=l0, hi=h0, n=n0, nruns=ne0)

    # ------------------------------------------------------------- Q4 --------------------------
    L.hdr("D6b Q4  V73 (route 5a) vs V72 (route 59) -- burst RATE vs AMPLITUDE vs RING amplitude")
    print("  V73's live levers: friction lane x1.5 (0xD2A44) and clamp 0xC407E 511->850.")
    print("  🛑 engaged, < 4 m/s, runs >= 5.12 s. Speed census printed -- the arms must match.\n")
    arms = {}
    for build in ("V72/r59", "V73/r5a"):
        bb = [z for z in allb if z["build"] == build]
        mm = [m for m in meta if m["run"][0] == build]
        if not mm:
            continue
        ring, rat = [], []
        for m_ in mm:
            fs = m_["fs"]
            ring.append(float(np.percentile(np.abs(analytic(bp(m_["x"], fs, *CARRIER))), 99)))
            rat.append(float(np.percentile(np.abs(analytic(bp(m_["x"], fs, *RATCHET))), 99)))
        arms[build] = dict(
            nrun=len(mm), sec=sum(m["sec"] for m in mm),
            vmed=float(np.median([m["v"] for m in mm])),
            burst_rate=[z["nb"] / z["sec"] for z in binfo if z["run"][0] == build],
            burst_dur=[z["dur"] for z in bb], burst_peak=[z["peak"] for z in bb],
            ring=ring, rat=rat)
    for b_, a_ in arms.items():
        print(f"  {b_:<10} runs={a_['nrun']}  sec={a_['sec']:.1f}  v_med={a_['vmed']:.2f} m/s  "
              f"bursts={len(a_['burst_dur'])}")
    if len(arms) == 2:
        A, B = arms["V73/r5a"], arms["V72/r59"]
        print(f"\n  {'quantity':<28}{'V73/r5a':>14}{'V72/r59':>14}{'ratio V73/V72':>28}")
        for lab, ka in (("burst onsets per second", "burst_rate"), ("burst duration s", "burst_dur"),
                        ("burst PEAK envelope", "burst_peak"),
                        ("RING p99 env 12-28 (counts)", "ring"),
                        ("RATCHET p99 env 5-12 (counts)", "rat")):
            a, b = np.array(A[ka], float), np.array(B[ka], float)
            if len(a) < 3 or len(b) < 3:
                print(f"  {lab:<28}{'--':>14}{'--':>14}{'underpowered':>28}")
                continue
            dr = np.array([np.median(a[RNG.integers(0, len(a), len(a))]) /
                           max(np.median(b[RNG.integers(0, len(b), len(b))]), 1e-9)
                           for _ in range(4000)])
            lo, hi = np.percentile(dr, [2.5, 97.5])
            print(f"  {lab:<28}{np.median(a):>14.3f}{np.median(b):>14.3f}"
                  f"{np.median(a)/max(np.median(b),1e-9):>16.3f}x [{lo:.2f},{hi:.2f}]")
            res.setdefault("q4", {})[lab] = dict(v73=float(np.median(a)), v72=float(np.median(b)),
                                                 ratio=float(np.median(a) / max(np.median(b), 1e-9)),
                                                 lo=float(lo), hi=float(hi))
        print("\n  🛑 n = 2 runs per arm. These CIs resample bursts/runs inside two drives; they are")
        print("     NOT a build contrast with the corpus's usual episode count. Treat as indicative.")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
