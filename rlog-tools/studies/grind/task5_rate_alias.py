# -*- coding: utf-8 -*-
"""studies/grind/task5_rate_alias.py -- IS THE 0x18F WHEEL-RATE CHANNEL BAND-LIMITED, OR AN ALIASING
SAMPLE-AND-HOLD OF A FASTER PROCESS?

Subagent task5rate, 2026-09-04.  Companion: TASK5-RATE-AND-ALIAS-2026-09-04.md.

The question that decides V286: if `gp-0x6a56` (CAN 0x18F bytes[2:3], ~100 Hz) is a zero-order sample of
a ~1 kHz process with NO anti-alias filter, then real content at 68-73 Hz FOLDS onto 27-32 Hz and a
"clean" reading of that band is a FALSE ALL-CLEAR.

Sections (all read the existing v280 caches; NO new rlog read, NO CAN sent)
  0  ARRIVAL STRUCTURE      frame cadence, drops, and the nominal frame index we index on
  1  STALENESS / REPEATS    P(repeat) conditioned on LOCAL SLOPE -- the quantisation-immune form
                            + a null control (band-limited surrogate re-quantised to the same LSB)
                            + an explicit S&H surrogate at 50 Hz as the positive control
  2  HIGH-FREQUENCY SHAPE   PSD of the raw rate on the frame index, out to Nyquist, by regime
  3  CROSS-FRAME            0x18F rate vs d/dt(0x14A angle) -- coherence and gain to Nyquist
                            0x1AB 50 Hz tap -- what its own Nyquist can and cannot bound

Run: python rlog-tools/studies/grind/task5_rate_alias.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0            # nominal 0x18F cadence
CPD = 8.0             # raw counts per deg/s on the 0x18F rate wire  (1 LSB = 0.125 deg/s)
TAGS = ("r34", "r35", "r36", "r37", "r38")
BUILD = {"r34": "V280 rev 2", "r35": "V281 rev 3", "r36": "V283", "r37": "V283", "r38": "V283"}

LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    for k in ("t18", "t14", "t1ab", "te4", "tcs"):
        D[k] = D[k] - t0
    return D


# ==========================================================================================
# SECTION 0 -- arrival structure
# ==========================================================================================
def sec0(D, tag):
    t = D["t18"]
    dt = np.diff(t)
    n = len(t)
    dur = t[-1] - t[0]
    # a "drop" = an inter-arrival long enough that at least one nominal frame is missing.
    # arrival times are batch-jittered up to 10 ms, so only gaps >= 1.5 frames are counted.
    drops = int(np.sum(np.round(dt / 0.01) - 1 > 0.5))
    missing = float(np.sum(np.maximum(np.round(dt / 0.01) - 1, 0)))
    pr("  %s  0x18F  n=%6d  dur=%7.1f s  mean rate=%6.2f Hz  dt med=%.4f p01=%.4f p99=%.4f"
       % (tag, n, dur, (n - 1) / dur, np.median(dt), np.percentile(dt, 1), np.percentile(dt, 99)))
    pr("        gaps >=1.5 frames: %d  (implied missing frames %.0f = %.3f%% of the stream)"
       % (drops, missing, 100.0 * missing / n))
    for nm, tk in (("0x14A", "t14"), ("0x1AB", "t1ab"), ("0x0E4", "te4")):
        tt = D[tk]
        pr("        %s  n=%6d  mean rate=%6.2f Hz" % (nm, len(tt), (len(tt) - 1) / (tt[-1] - tt[0])))
    return drops, missing


# ==========================================================================================
# SECTION 1 -- staleness conditioned on local slope
# ==========================================================================================
def repeat_by_slope(x, edges):
    """P(x[n] == x[n-1]) binned by the LOCAL SLOPE magnitude, in LSB/sample.

    The slope is estimated by a least-squares line over a +-4 sample window CENTRED on n, which is
    insensitive to the one-sample repeat being scored (it uses 9 points, and the fit is dominated by
    the far ones).  This is the quantisation-immune form of the staleness test:
      * a genuinely fresh, quantised signal  -> P(repeat) collapses to ~0 once |slope| >> 1 LSB/sample
      * a sample-and-hold of a faster process -> P(repeat) stays at the hold ratio at EVERY slope
    """
    x = np.asarray(x, float)
    w = 4
    k = np.arange(-w, w + 1, dtype=float)
    ker = k / np.sum(k * k)                      # LS slope kernel
    sl = np.convolve(x, ker[::-1], mode="same")  # slope in units/sample
    rep = np.zeros(len(x), bool)
    rep[1:] = x[1:] == x[:-1]
    a = np.abs(sl)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (a >= lo) & (a < hi)
        m[:w] = False
        m[-w:] = False
        out.append((lo, hi, int(m.sum()), float(rep[m].mean()) if m.sum() else np.nan))
    return out, rep, a


def surrogate_bandlimited(x, fc=25.0, fs=FS):
    """NULL CONTROL: a genuinely band-limited signal with the SAME LSB and roughly the same spectrum
    below fc.  Low-pass the observed sequence, then re-quantise to integers."""
    b, a = signal.butter(4, fc / (fs / 2.0), "low")
    y = signal.filtfilt(b, a, x)
    return np.round(y)


def surrogate_sah(x, hold=2):
    """POSITIVE CONTROL: the same sequence held for `hold` samples -- what a S&H of a stream running
    at fs/hold looks like on this channel."""
    y = x.copy()
    for i in range(1, len(y)):
        if i % hold:
            y[i] = y[i - 1]
    return y


def sec1(D, tag, mask=None, label=""):
    x = np.asarray(D["rate"], float)
    if mask is not None:
        # score only inside CONTIGUOUS runs of the mask so that neighbouring samples are real neighbours
        pass
    edges = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 1e9]
    rows, rep, sl = repeat_by_slope(x, edges)
    pr("  %s %s  overall P(repeat) = %.4f   |slope| med = %.2f LSB/sample" % (tag, label, rep[1:].mean(), np.median(sl)))
    pr("        %-16s %8s %10s   %10s %10s" % ("|slope| LSB/samp", "n", "P(rep)", "null b/l", "S&H x2"))
    xn = surrogate_bandlimited(x)
    xs = surrogate_sah(x, 2)
    rn, _, _ = repeat_by_slope(xn, edges)
    rs, _, _ = repeat_by_slope(xs, edges)
    for (lo, hi, n, p), (_, _, _, pn), (_, _, _, ps) in zip(rows, rn, rs):
        pr("        [%5.2f,%5.2f) %10d %10.4f   %10.4f %10.4f"
           % (lo, min(hi, 99.99), n, p, pn, ps))
    # run-length distribution of held values, restricted to moving frames
    d = np.diff(x)
    runs = []
    c = 1
    for v in (d == 0):
        if v:
            c += 1
        else:
            runs.append(c)
            c = 1
    runs.append(c)
    runs = np.array(runs)
    pr("        constant-value run lengths: n=%d  mean=%.3f  p50=%.0f p90=%.0f p99=%.0f max=%d"
       % (len(runs), runs.mean(), np.percentile(runs, 50), np.percentile(runs, 90),
          np.percentile(runs, 99), runs.max()))
    return rows


# ==========================================================================================
# SECTION 2 -- high-frequency spectral shape
# ==========================================================================================
def psd_index(x, nper=1024):
    """Welch PSD on the FRAME INDEX (not arrival time): CAN receive times are batch-jittered up to
    10 ms, which is 1 whole frame, so timestamps must not define the grid."""
    x = np.asarray(x, float)
    x = x - x.mean()
    f, P = signal.welch(x, fs=FS, nperseg=min(nper, len(x)), noverlap=min(nper, len(x)) // 2,
                        detrend="constant", window="hann")
    return f, P


def band(f, P, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.mean(P[m]))


def sec2(D, tag):
    x = np.asarray(D["rate"], float)
    t = D["t18"]
    sca = np.asarray(D["sca"], float)
    # engagement: 0x18F SCA bit AND 0xE4 STEER_REQUEST, on the 0x18F frame index
    req = np.interp(t, D["te4"], D["req"].astype(float)) > 0.5
    v = np.interp(t, D["tcs"], D["vego"])
    eng = (sca > 0.5) & req
    regimes = [("ALL", np.ones(len(x), bool)),
               ("engaged", eng),
               ("manual", ~eng),
               ("eng creep <8 m/s", eng & (v < 8)),
               ("eng road >=15 m/s", eng & (v >= 15))]
    pr("  %s  band-mean PSD (counts^2/Hz), and the ratio to the 10-15 Hz reference" % tag)
    pr("        %-18s %8s %10s %10s %10s %10s %10s" %
       ("regime", "n", "10-15Hz", "20-24Hz", "27-32Hz", "38-44Hz", "45-49.5Hz"))
    out = {}
    for nm, m in regimes:
        seg = longest_runs(m, 2048)
        if not seg:
            pr("        %-18s   (no run >= 2048 frames)" % nm)
            continue
        Ps = []
        ntot = 0
        for a, b in seg:
            f, P = psd_index(x[a:b])
            Ps.append(P * (b - a))
            ntot += b - a
        P = np.sum(Ps, 0) / ntot
        bands = [band(f, P, 10, 15), band(f, P, 20, 24), band(f, P, 27, 32),
                 band(f, P, 38, 44), band(f, P, 45, 49.5)]
        pr("        %-18s %8d %10.4f %10.4f %10.4f %10.4f %10.4f" % ((nm, ntot) + tuple(bands)))
        pr("        %-18s %8s %10.3f %10.3f %10.3f %10.3f %10.3f"
           % ("  ratio to 10-15", "", 1.0, bands[1] / bands[0], bands[2] / bands[0],
              bands[3] / bands[0], bands[4] / bands[0]))
        out[nm] = (f, P)
    return out


def longest_runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


# ==========================================================================================
# SECTION 3 -- cross-frame
# ==========================================================================================
def sec3(D, tag):
    """0x18F rate (100 Hz) vs the first difference of the 0x14A angle (100 Hz, 0.1 deg LSB).

    Both frames arrive on the SAME cadence, so this cannot separate alias from real by rate contrast.
    What it CAN do: the angle channel comes from the steering-angle sensor, a physically different
    transducer with its own sampling path.  If both carry the SAME high-frequency content coherently,
    the content is a property of the shaft, not of one channel's sampler.  If the rate carries HF that
    the angle does not, the rate's HF is either folded or is genuinely motor-side."""
    n = min(len(D["rate"]), len(D["ang"]))
    r = np.asarray(D["rate"], float)[:n] / CPD          # deg/s
    a = np.asarray(D["ang"], float)[:n]                 # deg, 0.1 LSB
    da = np.diff(a, prepend=a[0]) * FS                  # deg/s, LSB 10 deg/s
    t = D["t18"][:n]
    req = np.interp(t, D["te4"], D["req"].astype(float)) > 0.5
    eng = (np.asarray(D["sca"], float)[:n] > 0.5) & req
    seg = longest_runs(eng, 4096)
    if not seg:
        pr("  %s  no engaged run >= 4096 frames" % tag)
        return
    Cxy = []
    ntot = 0
    for s, e in seg:
        f, C = signal.coherence(r[s:e], da[s:e], fs=FS, nperseg=1024, noverlap=512)
        Cxy.append(C * (e - s))
        ntot += e - s
    C = np.sum(Cxy, 0) / ntot
    pr("  %s  coherence(0x18F rate, d/dt 0x14A angle), engaged, n=%d frames" % (tag, ntot))
    pr("        %-12s %8s" % ("band", "coh"))
    for lo, hi in [(2, 5), (5, 10), (10, 15), (15, 20), (20, 24), (24, 27), (27, 32), (32, 38),
                   (38, 44), (44, 49.5)]:
        m = (f >= lo) & (f < hi)
        pr("        %5.1f-%4.1f Hz %8.3f" % (lo, hi, float(np.mean(C[m]))))


# ==========================================================================================
def main():
    for tag in TAGS:
        pr()
        pr("=" * 100)
        pr("ROUTE %s  (%s)" % (tag, BUILD[tag]))
        pr("=" * 100)
        D = load(tag)
        pr("-- SECTION 0  arrival structure")
        sec0(D, tag)
        pr("-- SECTION 1  staleness / repeats, conditioned on local slope")
        sec1(D, tag)
        pr("-- SECTION 2  high-frequency spectral shape")
        sec2(D, tag)
        pr("-- SECTION 3  cross-frame coherence")
        sec3(D, tag)
    out = os.path.join(HERE, "_scratch", "task5_rate_alias.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("\nwrote %s" % out)


if __name__ == "__main__":
    main()
