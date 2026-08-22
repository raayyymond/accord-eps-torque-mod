r"""GRIND #1 -- FIXING TWO CONTROLS THAT FAILED, AND BOUNDING THE LINE WIDTH HONESTLY.

`ra5_grind1_line.py` produced the centre estimates but TWO of its controls did not do their job.
Both failures are in the CONTROL's design, not the estimator, and both are fixed here.

🛑 FAILURE 1 -- "STOCK's CI should be wider than the builds'" -- IT WASN'T (0.25 vs 0.50/1.75 Hz).
   Reason: STOCK has no interior peak, so its argmax PINS TO THE BAND EDGE (17.98 / 18.23 Hz) and
   an edge-pinned argmax is trivially reproducible.  A tight CI on stock means "no line", not
   "confident line".  ⇒ replaced by TWO diagnostics that cannot be fooled that way:
     P1 PROMINENCE   peak PSD / local shoulder baseline -- how far above its own floor the line is
     P2 EDGE-PINNED  is the argmax at the first or last bin of the search band?

🛑 FAILURE 2 -- THE Q NUMBERS ARE VOID.  The white-noise control returned **BW 0.749 Hz, Q 36.2**,
   and every measured Q (19.1-33.5) is BELOW that.  ⇒ the -3 dB width estimator carries NO
   information at 4 s / ~6 episodes.  [same family as `q_of` returning 79 on white noise,
   `feedback-run-the-control-before-the-measurement`]
   ⇒ replaced by a WINDOW-LENGTH LADDER, which is the right experiment:
     measure BW at 4 s / 8 s / 16 s windows, with a MATCHED white-noise control at EACH length.
     **If BW tracks the window's ENBW down, the line is UNRESOLVED and only an upper bound
     exists.  If BW plateaus, that plateau is the line's true width.**

🛑 FAILURE 3 (found here, not there) -- E3's band-centre bias.  On STOCK, E3 returned 19.84
   (band 18-22, centre 20.0) and 20.45 (band 17.5-24, centre 20.75) -- i.e. E3 returns the BAND
   CENTRE when there is no line.  `a5`'s line at ~20.5 Hz sits almost exactly at those centres,
   so E3 CANNOT independently confirm it.  ⇒ re-run E3 on a DELIBERATELY ASYMMETRIC band whose
   centre is far from the line; if the estimate stays with the line, E3 is tracking the line.
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
TAGS = ('r97', 'r96', 'r9e', 'ra4', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x',
         'ra5': 'V105 6x+NOTCH'}
WIDE = (17.5, 24.0)
OUT = {}


def run_slices(tag, vlo, vhi, minlen_s):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if m[a] and (c - a) >= ml]


def welch(tag, vlo, vhi, win_s, chan='rate_f'):
    nper = int(round(win_s * FS))
    fb = np.fft.rfftfreq(nper, 1 / FS)
    w = np.hanning(nper + 1)[:nper]
    uu = (w ** 2).sum()
    d, rs = run_slices(tag, vlo, vhi, win_s + 0.2)
    x = d[chan].astype(float)
    per = []
    for a, b in rs:
        seg = x[a:b]
        acc, nw = None, 0
        for s in range(0, len(seg) - nper + 1, nper // 2):
            xs = seg[s:s + nper] - seg[s:s + nper].mean()
            X = np.fft.rfft(xs * w)
            p = (X.conj() * X).real / (FS * uu)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
    S = None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)
    return fb, S, per, [len(x[a:b]) for a, b in rs]


def noise_welch(lens, win_s, seed=7):
    nper = int(round(win_s * FS))
    fb = np.fft.rfftfreq(nper, 1 / FS)
    w = np.hanning(nper + 1)[:nper]
    uu = (w ** 2).sum()
    rg = np.random.default_rng(seed)
    per = []
    for n in lens:
        seg = rg.normal(size=n)
        acc, nw = None, 0
        for s in range(0, n - nper + 1, nper // 2):
            xs = seg[s:s + nper] - seg[s:s + nper].mean()
            X = np.fft.rfft(xs * w)
            p = (X.conj() * X).real / (FS * uu)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
    return fb, (None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)), per


def peak_stats(fb, S, lo, hi):
    """argmax, prominence over shoulder baseline, edge-pinned flag, -3 dB BW."""
    k = np.flatnonzero((fb >= lo) & (fb <= hi))
    j = k[int(np.argmax(S[k]))]
    sh = ((fb >= lo - 2.0) & (fb < lo)) | ((fb > hi) & (fb <= hi + 2.0))
    base = float(np.median(S[sh])) if sh.any() else float(np.median(S[k]))
    prom = float(S[j] / base) if base > 0 else np.inf
    edge = bool(j == k[0] or j == k[-1])
    y = S - base
    half = y[j] / 2.0
    i = j
    while i > 0 and y[i] > half:
        i -= 1
    f_lo = fb[i]
    i = j
    while i < len(y) - 1 and y[i] > half:
        i += 1
    f_hi = fb[i]
    return float(fb[j]), prom, edge, float(f_hi - f_lo), float(S[j]), base


# ================================================================= P1/P2
print("=" * 120)
print("P1/P2.  THE REPLACEMENT FOR THE FAILED 'STOCK CI' CONTROL:")
print("        PROMINENCE over the line's own shoulders, and EDGE-PINNING.")
print("        Engaged < 16 km/h, search band %.1f-%.1f Hz, 4 s Hann." % WIDE)
print("=" * 120)
print("%14s %5s %10s %12s %12s %12s %12s"
      % ('build', 'eps', 'peak Hz', 'peak PSD', 'baseline', 'PROMINENCE', 'edge-pinned?'))
for t in TAGS:
    fb, S, per, lens = welch(t, 0.0, 16.0, 4.0)
    if S is None or len(per) < 3:
        continue
    f, prom, edge, bw, pk, base = peak_stats(fb, S, *WIDE)
    print("%14s %5d %10.3f %12.4f %12.4f %12.1f %12s"
          % (NAMES[t], len(per), f, pk, base, prom, "🛑 YES" if edge else "no"))
    OUT.setdefault('prominence', {})[NAMES[t]] = dict(peak=f, psd=pk, base=base,
                                                      prom=prom, edge=edge, eps=len(per))
fbn, Sn, pern = noise_welch([int(20.6 * FS)] * 6, 4.0)
f, prom, edge, bw, pk, base = peak_stats(fbn, Sn, *WIDE)
print("%14s %5d %10.3f %12.4f %12.4f %12.1f %12s"
      % ('WHITE NOISE', len(pern), f, pk, base, prom, "YES" if edge else "no"))
OUT.setdefault('prominence', {})['WHITE NOISE'] = dict(peak=f, prom=prom, edge=edge)
print("  🛑 STOCK's argmax is EDGE-PINNED -- it has no interior line, which is why its CI was")
print("     trivially tight.  Prominence is the diagnostic that separates a line from a slope.")

# ================================================================= the width ladder
print()
print("=" * 120)
print("W.  🛑 THE WINDOW-LENGTH LADDER -- the honest way to bound the line's width.")
print("    Each row: measured -3 dB BW at that window length, against a MATCHED white-noise")
print("    control at the SAME length.  ENBW = 1.5 / T.")
print("=" * 120)
print("%8s %8s %8s | %s"
      % ('win s', 'ENBW', 'arm', '  '.join("%16s" % NAMES[t] for t in ('ra4', 'ra5'))
         + "%16s" % 'WHITE NOISE'))
LAD = {}
for win_s in (4.0, 6.0, 8.0, 12.0, 16.0):
    enbw = 1.5 / win_s
    row_bw, row_f, row_n = [], [], []
    for t in ('ra4', 'ra5'):
        fb, S, per, lens = welch(t, 0.0, 16.0, win_s)
        if S is None:
            row_bw.append(np.nan)
            row_f.append(np.nan)
            row_n.append(0)
            continue
        f, prom, edge, bw, pk, base = peak_stats(fb, S, *WIDE)
        row_bw.append(bw)
        row_f.append(f)
        row_n.append(sum(p[1] for p in per))
    _, _, lens5 = welch('ra5', 0.0, 16.0, 4.0)[2:] + (None,) if False else (None, None, None)
    d5, rs5 = run_slices('ra5', 0.0, 16.0, win_s + 0.2)
    lens5 = [c - a for a, c in rs5]
    if lens5:
        fbn, Sn, pern = noise_welch(lens5, win_s)
        _, _, _, bwn, _, _ = peak_stats(fbn, Sn, *WIDE)
    else:
        bwn = np.nan
    LAD[win_s] = dict(enbw=enbw, bw_v104=row_bw[0], bw_v105=row_bw[1], bw_noise=bwn,
                      f_v104=row_f[0], f_v105=row_f[1],
                      win_v104=row_n[0], win_v105=row_n[1], eps_v105=len(lens5))
    print("%8.1f %8.3f %8s | %16s %16s %16s"
          % (win_s, enbw, 'BW Hz',
             "%.3f (%dw)" % (row_bw[0], row_n[0]) if np.isfinite(row_bw[0]) else '-',
             "%.3f (%dw)" % (row_bw[1], row_n[1]) if np.isfinite(row_bw[1]) else '-',
             "%.3f" % bwn if np.isfinite(bwn) else '-'))
    print("%8s %8s %8s | %16s %16s %16s"
          % ('', '', 'peak Hz',
             "%.3f" % row_f[0] if np.isfinite(row_f[0]) else '-',
             "%.3f" % row_f[1] if np.isfinite(row_f[1]) else '-', ''))
OUT['ladder'] = LAD
print()
print("  READ IT LIKE THIS:  BW tracking ENBW down  => the line is NARROWER than we can see,")
print("  and every Q here is a LOWER bound.  BW plateauing => that plateau IS the line's width.")

# ================================================================= E3 asymmetric-band control
print()
print("=" * 120)
print("E3-C.  THE BAND-CENTRE BIAS CONTROL.  E3 returns the BAND CENTRE on stock, and `a5`'s")
print("       line sits almost exactly at the centre of both bands used -- so E3 could not")
print("       confirm it.  Re-run on DELIBERATELY ASYMMETRIC bands.")
print("=" * 120)


def e3(tag, lo, hi, vlo=0.0, vhi=16.0):
    d, rs = run_slices(tag, vlo, vhi, 4.2)
    x = d['rate_f'].astype(float)
    num = den = 0.0
    for a, b in rs:
        seg = x[a:b]
        n = len(seg)
        X = np.fft.rfft(seg - seg.mean())
        fr = np.fft.rfftfreq(n, 1 / FS)
        Y = np.zeros_like(X)
        keep = (fr >= lo) & (fr < hi)
        Y[keep] = X[keep]
        Z = np.zeros(n, complex)
        Z[:len(Y)] = 2.0 * Y
        Z[0] /= 2
        z = np.fft.ifft(Z)
        env = np.abs(z)
        ph = np.unwrap(np.angle(z))
        f = np.diff(ph) / (2 * np.pi) * FS
        w = env[1:] ** 2
        g = (env[1:] > np.median(env)) & (f > lo) & (f < hi)
        if g.sum() < 10:
            continue
        num += float((f[g] * w[g]).sum())
        den += float(w[g].sum())
    return num / den if den > 0 else np.nan


BANDS = [(17.5, 24.0), (18.0, 22.0), (18.0, 30.0), (14.0, 24.0), (16.0, 21.0), (19.5, 32.0)]
print("%14s" % 'build' + "".join("%14s" % ("%g-%g" % b) for b in BANDS))
print("%14s" % 'band centre' + "".join("%14.2f" % (0.5 * (b[0] + b[1])) for b in BANDS))
for t in TAGS:
    print("%14s" % NAMES[t] + "".join("%14.3f" % e3(t, *b) for b in BANDS))
    OUT.setdefault('e3_bands', {})[NAMES[t]] = {("%g-%g" % b): float(e3(t, *b)) for b in BANDS}
print("  🛑 STOCK's row should TRACK THE BAND CENTRE row (it has no line).  A build's row that")
print("     stays PUT while the band centre swings 17.75 -> 25.75 Hz is tracking a real line.")

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '_ra5_grind1_resolve.json'), 'w'), indent=1, default=float)
print("\nwrote _ra5_grind1_resolve.json")
