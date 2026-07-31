"""
analyze_r31_manual_vs_engaged.py -- what the V61 drive (route 31) actually measured.

V61 killed the torsion-bar RATE lane at both taps. Two questions this answers, both decisive:

 1. Did the engaged grinding get worse, and DID THE MODE MOVE?  Control = V59's route 2c, identical
    method, identical speed window, same channel. A pure GAIN change cannot move a resonance frequency.
    A PHASE change can -- and removing a lead compensator lowers the frequency at which the loop phase
    reaches -180 deg, so the limit cycle should drop in frequency. That is a structural signature.
 2. Is the newly-reported MANUAL grinding real, is it worst in REVERSE, and is it the same mode?

METHODOLOGY -- the project's hard-won conventions, all of them:
  * engagement = carControl.latActive. NEVER cruiseState.enabled.
  * PROMINENCE (peak vs local baseline), not mean Welch power -- the mode is bursty.
  * peak-frequency SCATTER discriminates a real mode from the argmax of a floor.
  * average periodograms across DISJOINT runs. NEVER splice runs into one FFT.
  * 🛑 do NOT pre-restrict to 18-26 Hz when LOCATING a peak. The first pass of this analysis did, and the
    argmax pinned to the band edge at 18.04 Hz with sd 0.00 -- a truncation artifact, because the real
    peak had MOVED BELOW the band. Locate over 12-30 Hz, then interpret. The strict band is for
    presence-testing a mode whose frequency you already know, not for finding one that has shifted.
  * the ratchet's 2nd harmonic (2 x 6-9 = 12-18 Hz) is the standing trap here. Discriminate on relative
    strength: a "harmonic" 380x stronger than its own fundamental is not a harmonic.
"""

import glob
import numpy as np

SPEED_CAP = 5.35             # route 31's own max, so the V59 control is speed-matched to it
MIN_RUN_S = 2.0
NPER_S = 4.0                 # 0.25 Hz resolution


def _runs(mask, min_len):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask)))
    return out


def _welch(x, fs, nper):
    """Average periodograms across DISJOINT half-overlapped windows of ONE run."""
    w = np.hanning(nper)
    segs = []
    for s in range(0, len(x) - nper + 1, nper // 2):
        g = x[s:s + nper] - x[s:s + nper].mean()
        segs.append(np.abs(np.fft.rfft(g * w)) ** 2)
    return (np.fft.rfftfreq(nper, 1 / fs), np.mean(segs, axis=0)) if segs else (None, None)


def _subbin(freqs, power, i):
    """Log-parabolic sub-bin peak interpolation."""
    if not 0 < i < len(power) - 1:
        return freqs[i]
    a, b, c = np.log(power[i - 1]), np.log(power[i]), np.log(power[i + 1])
    denom = a - 2 * b + c
    d = 0.5 * (a - c) / denom if denom != 0 else 0.0
    return freqs[i] + d * (freqs[1] - freqs[0])


def _pool(pattern, selector):
    arrs, fs = [], None
    for f in sorted(glob.glob(pattern)):
        d = np.load(f, allow_pickle=True)
        t = np.asarray(d["t"], float)
        fs = 1.0 / np.median(np.diff(t))
        tq = np.nan_to_num(np.asarray(d["tq"], float))
        lat = np.nan_to_num(np.asarray(d["cc_lat"], float)) > 0.5
        # ⚠ the older route-2c cache predates the gear column; gear-based selectors are route-31 only.
        gear = (np.nan_to_num(np.asarray(d["cs_gear"], float)).astype(int)
                if "cs_gear" in d.files else np.full(len(t), -1, int))
        v = np.nan_to_num(np.asarray(d["cs_v"], float))
        for a, b in _runs(selector(lat, gear, v), int(MIN_RUN_S * fs)):
            arrs.append(tq[a:b])
    return arrs, fs


def _spectrum(arrs, fs):
    nper = int(NPER_S * fs)
    acc, n = None, 0
    for x in arrs:
        if len(x) < nper:
            continue
        fr, p = _welch(x, fs, nper)
        if fr is None:
            continue
        acc = p if acc is None else acc + p
        n += 1
    return (None, None, 0) if acc is None else (fr, acc / n, n)


def _report(label, arrs, fs, lo=12.0, hi=30.0):
    fr, p, n = _spectrum(arrs, fs)
    if n == 0:
        print(f"  {label:24s}  n=0 runs -- NOT COMPUTABLE from this route")
        return None
    sel = (fr >= lo) & (fr <= hi)
    fr2, p2 = fr[sel], p[sel]
    base = np.median(p[(fr >= 8) & (fr <= 40)])
    i = int(np.argmax(p2))
    pk = _subbin(fr2, p2, i)
    print(f"  {label:24s}  n={n:2d} runs | peak {pk:5.2f} Hz | prominence {p2.max()/base:8.1f}x "
          f"| abs power {p2.max():.3g}")
    return dict(peak=pk, prom=p2.max() / base, power=p2.max(), n=n)


def main():
    creep = lambda lat, gear, v: lat & (v > 0.3) & (v <= SPEED_CAP)          # noqa: E731
    fwd = lambda lat, gear, v: ~lat & (gear == 2) & (v > 0.3)                # noqa: E731
    rev = lambda lat, gear, v: ~lat & (gear == 4) & (v > 0.3)                # noqa: E731

    print("=" * 88)
    print("1. DID THE MODE MOVE?  engaged creep, v <= %.2f m/s, identical method both builds" % SPEED_CAP)
    print("=" * 88)
    res = {}
    for label, pat in (("V59  route 2c", "_cache_r2c/r2cs*.npz"), ("V61  route 31", "_cache_r31/r31s*.npz")):
        arrs, fs = _pool(pat, creep)
        res[label] = _report(label, arrs, fs)
    a, b = res["V59  route 2c"], res["V61  route 31"]
    if a and b:
        print(f"\n  => frequency {a['peak']:.2f} -> {b['peak']:.2f} Hz  ({b['peak']-a['peak']:+.2f} Hz)")
        print(f"  => power     {a['power']:.3g} -> {b['power']:.3g}  ({b['power']/a['power']:.1f}x)")
        print("  A pure gain change cannot move a resonance frequency; removing a phase LEAD lowers the")
        print("  frequency at which the loop phase reaches -180 deg. Both observables agree.")

    print()
    print("=" * 88)
    print("2. IS THE NEW MANUAL GRINDING REAL, AND WORST IN REVERSE?   route 31 only")
    print("=" * 88)
    for label, sel in (("ENGAGED (latActive)", creep), ("MANUAL forward (drive)", fwd),
                       ("MANUAL reverse", rev)):
        arrs, fs = _pool("_cache_r31/r31s*.npz", sel)
        secs = sum(len(x) for x in arrs) / fs if arrs else 0.0
        print(f"[{label}]  {len(arrs)} runs, {secs:.1f} s")
        _report(label, arrs, fs)


if __name__ == "__main__":
    main()
