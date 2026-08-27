r"""ARE ALL THREE GRINDS THE SAME FREQUENCY?  The operator's claim, tested.

Operator, 2026-08-22: *"I actually think all 3 grinds are the same frequencies. They just happen
under different scenarios. Grind #1 low speed like 5 mph (LKAS engaged), grind #2 low speed but
hard manual turns during LKAS engagement, grind #3 highway speeds (LKAS engaged)"*

The kit's own taxonomy says three DIFFERENT frequencies: #1 = 18-22 Hz · #2 ~ 44.9 Hz (measured
44.31 Hz on V71C, `BUILD-LINEAGE.md:629`) · #3 ~ 46 Hz.  He says ONE frequency, THREE conditions.
🛑 His lived experience overrides analyst reconstruction -- but this is a FREQUENCY claim, which an
instrument can settle.  So: stratify by HIS scenarios, search WIDE, and let the peak land.

=================================================================================================
🛑 THE INSTRUMENT'S CEILING, STATED BEFORE ANYTHING ELSE -- IT BOUNDS WHAT THIS CAN ANSWER
=================================================================================================
Measured native rates on `a5`:
    0x18F  (`tq`, `rate_f`, `rate_c`, the row grid)   101.11 Hz  =>  **NYQUIST 50.56 Hz**
    0x1AB  (the 427 cave lane)                         49.78 Hz  =>  Nyquist 24.89 Hz
    wheel speeds                                       49.76 Hz  =>  Nyquist 24.88 Hz
⇒ **NOTHING IN THE CAN CORPUS CAN SEE ABOVE ~50 Hz.**  The orchestrator asked for 5-60 Hz; 5-48 Hz
is the honest maximum, and **44.9 Hz sits at 89 % of Nyquist**, where any content originally above
50.6 Hz folds down on top of it.  A peak found at 44-46 Hz therefore CANNOT be distinguished from
aliased content at 56-58 Hz by this channel alone.  ⊕ The only wide-band instrument in the corpus
is `rawAudioData` (16 kHz, Nyquist 8000 Hz) and it was measured NULL from 100 Hz to 8 kHz across
six builds, with a stated physics reason for the sub-100 Hz null (a rack is a hopeless radiator at
a ~16 m wavelength).  **Both facts go in the report; neither is hidden.**
🛑 The 427 lane is USELESS above 24.9 Hz and is not used here.

=================================================================================================
HIS THREE SCENARIOS, PRE-REGISTERED AS MASKS BEFORE ANY SPECTRUM WAS COMPUTED
=================================================================================================
S1  "low speed like 5 mph (LKAS engaged)"
      engaged & v < 10 km/h & 5 <= |rate_c| < 40 deg/s          (moderate steering)
S2  "low speed but HARD MANUAL TURNS during LKAS engagement"     <- THE ARM THE KIT NEVER ISOLATED
      engaged & v < 20 km/h & |tq| >= 1000 counts & |rate_c| >= 40 deg/s
      (`tq` engaged p50 is ~166 counts and p99 ~3208, so 1000 is a genuine push, not a brush;
       the 40 deg/s floor is what makes it a TURN rather than a shove.)
S3  "highway speeds (LKAS engaged)"
      engaged & v >= 60 km/h

⚠ S2 is a CONJUNCTION of three conditions and will be the thin one.  Its episode count is reported
before its spectrum, and if it is too thin the answer is "underpowered", not a number.

=================================================================================================
THE THREE OUTCOMES, PRE-REGISTERED
=================================================================================================
(1) all three peaks at ~21-27 Hz            => he is right; the 44.9/46 Hz labels are wrong
(2) S2 and/or S3 genuinely peak at ~45 Hz   => the taxonomy is right on frequency; he is naming
                                               three conditions of one SENSATION
(3) mixed / underpowered                    => say so with the exposure numbers

=================================================================================================
THE HARMONIC TEST -- and the control that has already killed one of these
=================================================================================================
44.31 ~ 2 x 22.15 and 46 ~ 2 x 23.  If the 44-46 Hz feature is the SECOND HARMONIC of the 21-23 Hz
mode, the operator is right in the way that matters: one mechanism.
    PLV = | <exp(i(phi_2f - 2 phi_f))> |   over frames where BOTH envelopes exceed their medians.
CONTROLS, all three run:
  H1 NON-HARMONIC control at 1.65 x f0 -- the record's own control, which previously came back
     IDENTICAL to the harmonic value (retraction 11 of the V105 handoff).
  H2 PHASE-SHUFFLED surrogate -- destroys coupling, preserves both spectra.
  H3 🛑 DROP-ONE-EPISODE and N_eff.  A bicoherence detector in this kit once returned a 300x
     "detection" that was ONE WINDOW (N_eff = 1.0), collapsed 14x on drop-one, and was LARGEST ON
     STOCK.  Any PLV here is reported with N_eff and its drop-one range or it is not reported.

=================================================================================================
THE CLAMP CHECK -- which may VETO V106, and which is MEASURED, not reconstructed
=================================================================================================
V106 raises `gp-0x6b26`, an ACCELERATION term whose lane clamps at +-511 (`0xC407E`).  Hard manual
turns = large angular acceleration => it should clamp MORE in exactly S2, and a clamped damper
delivers no incremental damping.
🛑 I do NOT have the confirmed cascade H(f), so I do not fabricate one.  Instead this uses the
   routes where **`gp-0x6b26` WAS ITSELF ON THE 427 WIRE** -- r77 / r78 (V90/V91, `sar 3`) and
   r7d (V94, `sar 1`) -- and measures the clamp duty DIRECTLY under an S2-equivalent mask, then
   reports how much headroom a x2 dose would consume.  A measurement beats a reconstruction.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NYQ = FS / 2.0
LO, HI = 5.0, 48.0                       # 48 < 0.95 * Nyquist
WIN_S = float(os.environ.get('G3_WIN_S', '1.0'))
MERGE_S = float(os.environ.get('G3_MERGE_S', '0.25'))
NPER = int(round(WIN_S * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
ENBW = 1.5 / WIN_S
TAGS = ('r97', 'r85', 'r96', 'r9e', 'ra4', 'r95', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r85': 'V100 4x', 'r96': 'V102 6x', 'r9e': 'V103 6x',
         'ra4': 'V104 6x', 'r95': 'V101 8x', 'ra5': 'V105 NOTCH'}
OUT = {'nyquist_hz': NYQ, 'search_band': [LO, HI], 'win_s': WIN_S, 'bin_hz': float(DF),
       'enbw_hz': ENBW}


def scen_mask(d, which):
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = np.asarray(d['v_rear'], float) * KPH
    rc = np.abs(np.asarray(d['rate_c'], float))
    tq = np.abs(np.asarray(d['tq'], float))
    if which == 'S1':
        return e & (v < 10.0) & (rc >= 5.0) & (rc < 40.0)
    if which == 'S2':
        return e & (v < 20.0) & (tq >= 1000.0) & (rc >= 40.0)
    if which == 'S3':
        return e & (v >= 60.0)
    raise ValueError(which)


def close_gaps(mask, gap_s=None):
    """🛑 S1 and S2 FLICKER: at 2 s windows they yielded ZERO windows on EVERY build, because the
    conditions dip below threshold for a tenth of a second mid-turn.  A 0.1 s dip below 40 deg/s
    does not end 'a hard turn'.  So gaps shorter than `gap_s` are closed before runs are taken.
    Reported explicitly; the un-merged census is printed alongside so the cost is visible."""
    g = int(round((MERGE_S if gap_s is None else gap_s) * FS))
    if g <= 0:
        return mask
    m = mask.copy()
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    for a, c in zip(b[:-1], b[1:]):
        if (not m[a]) and a > 0 and c < len(m) and (c - a) <= g:
            m[a:c] = True
    return m


def runs(mask, minlen, merge=True):
    mm = close_gaps(mask) if merge else mask
    idx = np.flatnonzero(np.diff(mm.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mm)]))
    return [(int(a), int(c)) for a, c in zip(b[:-1], b[1:])
            if mm[a] and (c - a) >= minlen]


def per_ep(tag, which, chan='rate_f'):
    d = L.load(tag)
    m = scen_mask(d, which)
    x = np.asarray(d[chan], float)
    out = []
    for a, c in runs(m, NPER):
        seg = x[a:c]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            out.append((acc, nw))
    return out, m


def pool(per):
    return None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)


def peak_prom(S):
    k = np.flatnonzero((FB >= LO) & (FB <= HI))
    j = k[int(np.argmax(S[k]))]
    f0 = FB[j]
    sh = (((FB >= f0 - 5) & (FB <= f0 - 2)) | ((FB >= f0 + 2) & (FB <= f0 + 5))) \
        & (FB >= LO) & (FB <= HI)
    base = float(np.median(S[sh])) if sh.sum() > 3 else float(np.median(S[k]))
    return float(f0), float(S[j]), (float(S[j] / base) if base > 0 else np.inf), base


def boot_peak(per, nb=3000, seed=911):
    k = np.flatnonzero((FB >= LO) & (FB <= HI))
    rg = np.random.default_rng(seed)
    pk = []
    for _ in range(nb):
        pick = rg.integers(0, len(per), len(per))
        S = sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick)
        pk.append(FB[k][int(np.argmax(S[k]))])
    return [float(np.percentile(pk, 2.5)), float(np.percentile(pk, 97.5))]


# ============================================================ 0. CENSUS FIRST
print("=" * 124)
print("0.  EXPOSURE CENSUS PER SCENARIO -- run BEFORE any spectrum, because S2 is a conjunction")
print("    of three conditions and may simply not exist in this corpus.")
print("    resolution: %.1f s Hann, bin %.3f Hz, ENBW %.3f Hz.  Search band %.0f-%.0f Hz."
      % (WIN_S, DF, ENBW, LO, HI))
print("    🛑 NYQUIST %.2f Hz (0x18F @ %.2f Hz).  Nothing above ~50 Hz is observable at all."
      % (NYQ, FS))
print("=" * 124)
print("    gap-merge %.2f s (see `close_gaps`); the UNMERGED window count is shown in ( ) so the"
      % MERGE_S)
print("    cost of the merge is visible.  🛑 AT 2.0 s WINDOWS, S1 GAVE ZERO WINDOWS ON EVERY")
print("    BUILD -- his two low-speed scenarios do not hold still for two seconds.")
print("%12s | %s" % ('build', ' | '.join("%30s" % s for s in ('S1 low speed', 'S2 HARD MANUAL',
                                                              'S3 highway'))))
CEN = {}
for t in TAGS:
    row = []
    for w in ('S1', 'S2', 'S3'):
        d = L.load(t)
        m = scen_mask(d, w)
        rr = runs(m, NPER)
        nw = sum((c - a - NPER) // (NPER // 2) + 1 for a, c in rr)
        raw = runs(m, NPER, merge=False)
        nwr = sum((c - a - NPER) // (NPER // 2) + 1 for a, c in raw)
        CEN[(t, w)] = dict(sec=float(m.sum() / FS), eps=len(rr), win=int(nw),
                           eps_raw=len(raw), win_raw=int(nwr))
        row.append("%30s" % ("%.1fs %deps %dw (%dw raw)" % (m.sum() / FS, len(rr), nw, nwr)))
    print("%12s | %s" % (NAMES[t], ' | '.join(row)))
OUT['census'] = {NAMES[t] + '|' + w: CEN[(t, w)] for t in TAGS for w in ('S1', 'S2', 'S3')}
print("  eps = contiguous runs of the mask that hold at least one %.0f s window." % WIN_S)

# ============================================================ 1. THE PEAKS
print()
print("=" * 124)
print("1.  🛑 THE TEST.  Wide-band peak (%.0f-%.0f Hz) per scenario.  `rate_f` (0x18F wheel rate)."
      % (LO, HI))
print("=" * 124)
RES = {}
for w, lbl in (('S1', "S1  engaged, v<10 km/h, 5-40 deg/s   (his grind #1)"),
               ('S2', "S2  engaged, v<20 km/h, |tq|>=1000, |rate|>=40  (his grind #2)"),
               ('S3', "S3  engaged, v>=60 km/h              (his grind #3)")):
    print("\n  %s" % lbl)
    print("%12s %5s %6s %10s %22s %11s %11s %12s"
          % ('build', 'eps', 'win', 'PEAK Hz', '95 % CI (episode)', 'peak PSD', 'PROMINENCE',
             'band RMS'))
    for t in TAGS:
        per, m = per_ep(t, w)
        if not per:
            print("%12s %5d %6d   -- no windows --" % (NAMES[t], 0, 0))
            continue
        S = pool(per)
        f0, pv, prom, base = peak_prom(S)
        ci = boot_peak(per) if len(per) >= 3 else None
        k = (FB >= LO) & (FB <= HI)
        rms = float(np.sqrt(S[k].sum() * DF))
        RES[(t, w)] = dict(per=per, S=S, f0=f0, psd=pv, prom=prom, rms=rms,
                           ci=ci, eps=len(per), win=sum(p[1] for p in per))
        print("%12s %5d %6d %10.2f %22s %11.3f %11.1f %12.4f"
              % (NAMES[t], len(per), sum(p[1] for p in per), f0,
                 ("[%.2f, %.2f]" % tuple(ci)) if ci else '< 3 eps, no CI',
                 pv, prom, rms))
    OUT.setdefault('peaks', {})[w] = {
        NAMES[t]: {k2: v for k2, v in RES[(t, w)].items() if k2 not in ('per', 'S')}
        for t in TAGS if (t, w) in RES}

# ============================================================ 1b. EDGE-PINNING FIX
print()
print("=" * 124)
print("1b. 🛑 THE 5-48 Hz ARGMAX IS EDGE-PINNED IN S1/S2 -- it returns 5.01 Hz, the band's own")
print("    lower edge, because the DRIVER'S OWN STEERING INPUT dominates below ~10 Hz and that")
print("    is loudest in exactly the scenarios that involve turning.  It is the same failure as")
print("    STOCK's argmax pinning to 17.98 Hz in the grind-#1 work.  ⇒ re-run over 15-48 Hz,")
print("    which is above the driver's input band and still covers 21 AND 45.")
print("=" * 124)
for w, lbl in (('S1', 'S1 low speed'), ('S2', 'S2 HARD MANUAL'), ('S3', 'S3 highway')):
    print("\n  %s" % lbl)
    print("%12s %5s %6s %10s %22s %11s %11s"
          % ('build', 'eps', 'win', 'PEAK Hz', '95 % CI (episode)', 'peak PSD', 'PROMINENCE'))
    for t in TAGS:
        if (t, w) not in RES:
            continue
        per = RES[(t, w)]['per']
        S = RES[(t, w)]['S']
        kk = np.flatnonzero((FB >= 15.0) & (FB <= 48.0))
        j = kk[int(np.argmax(S[kk]))]
        f0 = float(FB[j])
        sh = (((FB >= f0 - 6) & (FB <= f0 - 2)) | ((FB >= f0 + 2) & (FB <= f0 + 6))) \
            & (FB >= 15.0) & (FB <= 48.0)
        base = float(np.median(S[sh])) if sh.sum() > 3 else float(np.median(S[kk]))
        ci = None
        if len(per) >= 3:
            rg = np.random.default_rng(1301)
            pk = []
            for _ in range(3000):
                pick = rg.integers(0, len(per), len(per))
                S2m = sum(per[q][0] for q in pick) / sum(per[q][1] for q in pick)
                pk.append(FB[kk][int(np.argmax(S2m[kk]))])
            ci = [float(np.percentile(pk, 2.5)), float(np.percentile(pk, 97.5))]
        print("%12s %5d %6d %10.2f %22s %11.3f %11.1f"
              % (NAMES[t], RES[(t, w)]['eps'], RES[(t, w)]['win'], f0,
                 ("[%.2f, %.2f]" % tuple(ci)) if ci else '< 3 eps, no CI',
                 float(S[j]), float(S[j] / base) if base > 0 else np.inf))
        OUT.setdefault('peaks_15_48', {}).setdefault(w, {})[NAMES[t]] = dict(
            f0=f0, psd=float(S[j]), prom=float(S[j] / base) if base > 0 else None, ci=ci)

# ============================================================ 2. IS THERE ANY 40-48 Hz FEATURE?
print()
print("=" * 124)
print("2.  DIRECT LOOK AT 40-48 Hz -- the band the kit's taxonomy puts grind #2 and #3 in.")
print("    A global argmax can be dominated by a loud low-frequency mode and MISS a real, smaller")
print("    high-frequency line.  So: search 38-48 Hz SEPARATELY, on its own.")
print("=" * 124)
for w in ('S1', 'S2', 'S3'):
    print("\n  %s" % w)
    print("%12s %10s %11s %11s %14s %14s"
          % ('build', 'pk 38-48', 'PSD', 'PROMINENCE', 'RMS 18-26', 'RMS 38-48'))
    for t in TAGS:
        if (t, w) not in RES:
            continue
        S = RES[(t, w)]['S']
        k = np.flatnonzero((FB >= 38.0) & (FB <= 48.0))
        j = k[int(np.argmax(S[k]))]
        sh = ((FB >= 30) & (FB <= 36)) | ((FB >= 48) & (FB <= 50))
        base = float(np.median(S[sh])) if sh.sum() > 3 else float(np.median(S[k]))
        k1 = (FB >= 18) & (FB < 26)
        k2 = (FB >= 38) & (FB < 48)
        print("%12s %10.2f %11.4f %11.1f %14.4f %14.4f"
              % (NAMES[t], FB[j], S[j], S[j] / base if base > 0 else np.inf,
                 np.sqrt(S[k1].sum() * DF), np.sqrt(S[k2].sum() * DF)))
        OUT.setdefault('hiband', {}).setdefault(w, {})[NAMES[t]] = dict(
            pk=float(FB[j]), psd=float(S[j]), prom=float(S[j] / base) if base > 0 else None,
            rms_18_26=float(np.sqrt(S[k1].sum() * DF)),
            rms_38_48=float(np.sqrt(S[k2].sum() * DF)))

# ============================================================ 2b. BURST DETECTOR
print()
print("=" * 124)
print("2b. 🛑 GRIND #2 IS RECORDED AS A RARE BURST EVENT, NOT A STATIONARY LINE.")
print("    `BUILD-LINEAGE.md:629`: V71C produced 44.31 Hz with p99 **1741.9** against a")
print("    same-segment NON-BURST floor of **25.5** -- 3 of the corpus's 13 merged events in")
print("    5.28 %% of the exposure.  **A POOLED SPECTRUM WOULD WASH THAT OUT ENTIRELY.**")
print("    ⇒ per-WINDOW band RMS, and the tail, not the mean.")
print("=" * 124)


def win_bands(tag, which):
    d = L.load(tag)
    m = scen_mask(d, which)
    x = np.asarray(d['rate_f'], float)
    lo1, hi1, lo2, hi2 = 18.0, 26.0, 38.0, 48.0
    k1 = (FB >= lo1) & (FB < hi1)
    k2 = (FB >= lo2) & (FB < hi2)
    b1, b2 = [], []
    for a, c in runs(m, NPER):
        seg = x[a:c]
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            b1.append(np.sqrt(p[k1].sum() * DF))
            b2.append(np.sqrt(p[k2].sum() * DF))
    return np.asarray(b1), np.asarray(b2)


for w, lbl in (('S1', 'S1 low speed'), ('S2', 'S2 HARD MANUAL'), ('S3', 'S3 highway')):
    print("\n  %s   per-window band RMS (deg/s), %d windows-per-build shown in n" % (lbl, 0))
    print("%12s %5s | %8s %8s %8s %8s | %8s %8s %8s %8s | %10s"
          % ('build', 'n', '18-26 p50', 'p90', 'p99', 'MAX',
             '38-48 p50', 'p90', 'p99', 'MAX', 'MAX ratio'))
    for t in TAGS:
        if (t, w) not in RES:
            continue
        b1, b2 = win_bands(t, w)
        if len(b1) < 2:
            continue
        q1 = [float(np.percentile(b1, q)) for q in (50, 90, 99)] + [float(b1.max())]
        q2 = [float(np.percentile(b2, q)) for q in (50, 90, 99)] + [float(b2.max())]
        print("%12s %5d | %8.3f %8.3f %8.3f %8.3f | %8.3f %8.3f %8.3f %8.3f | %10.3f"
              % (NAMES[t], len(b1), q1[0], q1[1], q1[2], q1[3],
                 q2[0], q2[1], q2[2], q2[3], q2[3] / q1[3] if q1[3] > 0 else np.nan))
        OUT.setdefault('burst', {}).setdefault(w, {})[NAMES[t]] = dict(
            n=len(b1), b18_26=q1, b38_48=q2)
print("  'MAX ratio' = the loudest 38-48 Hz window / the loudest 18-26 Hz window.  If grind #2")
print("  were a real 44 Hz burst phenomenon, S2's MAX ratio would exceed 1 somewhere.")

# ============================================================ 3. HARMONIC / PHASE LOCK
print()
print("=" * 124)
print("3.  IS THE 40-48 Hz FEATURE THE SECOND HARMONIC OF THE 21-23 Hz MODE?")
print("    PLV between phi(2f0) and 2*phi(f0), with THREE controls.")
print("=" * 124)


def bp(x, lo, hi):
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    Y = np.zeros_like(X)
    keep = (fr >= lo) & (fr < hi)
    Y[keep] = X[keep]
    Z = np.zeros(n, complex)
    Z[:len(Y)] = 2.0 * Y
    Z[0] /= 2
    return np.fft.ifft(Z)


def plv_ep(tag, which, f0, ratio, shuffle=False, seed=5):
    d = L.load(tag)
    m = scen_mask(d, which)
    x = np.asarray(d['rate_f'], float)
    rg = np.random.default_rng(seed)
    per = []
    for a, c in runs(m, int(1.0 * FS)):
        seg = x[a:c]
        z1 = bp(seg, f0 - 1.5, f0 + 1.5)
        z2 = bp(seg, ratio * f0 - 2.0, ratio * f0 + 2.0)
        if shuffle:
            z2 = z2 * np.exp(1j * rg.uniform(0, 2 * np.pi))
            z2 = np.roll(z2, rg.integers(1, max(2, len(z2))))
        g = (np.abs(z1) > np.median(np.abs(z1))) & (np.abs(z2) > np.median(np.abs(z2)))
        if g.sum() < 20:
            continue
        ph = np.angle(z2[g]) - ratio * np.angle(z1[g])
        per.append(np.exp(1j * ph))
    if not per:
        return None
    allv = np.concatenate(per)
    plv = float(np.abs(allv.mean()))
    n_eff = len(per)
    drop = []
    for i in range(n_eff):
        rest = np.concatenate([p for j, p in enumerate(per) if j != i])
        drop.append(float(np.abs(rest.mean())))
    return dict(plv=plv, n_ep=n_eff, n_samp=int(len(allv)),
                drop_min=float(min(drop)) if drop else np.nan,
                drop_max=float(max(drop)) if drop else np.nan)


print("%12s %5s %8s %10s %12s %12s %12s %22s"
      % ('build', 'scen', 'f0 Hz', 'PLV 2f0', 'H1 1.65f0', 'H2 shuffled', 'n episodes',
         'H3 drop-one range'))
for w in ('S1', 'S2', 'S3'):
    for t in ('r97', 'ra4', 'ra5'):
        if (t, w) not in RES:
            continue
        k = np.flatnonzero((FB >= 18.0) & (FB <= 26.0))
        f0 = float(FB[k][int(np.argmax(RES[(t, w)]['S'][k]))])
        if 2 * f0 + 2.0 > NYQ:
            print("%12s %5s %8.2f   -- 2f0 = %.1f Hz is ABOVE NYQUIST %.1f, not testable --"
                  % (NAMES[t], w, f0, 2 * f0, NYQ))
            continue
        A = plv_ep(t, w, f0, 2.0)
        B = plv_ep(t, w, f0, 1.65)
        C = plv_ep(t, w, f0, 2.0, shuffle=True)
        if A is None:
            print("%12s %5s %8.2f   -- too few episodes --" % (NAMES[t], w, f0))
            continue
        print("%12s %5s %8.2f %10.4f %12s %12s %12d %22s"
              % (NAMES[t], w, f0, A['plv'],
                 "%.4f" % B['plv'] if B else '-', "%.4f" % C['plv'] if C else '-',
                 A['n_ep'], "[%.4f, %.4f]" % (A['drop_min'], A['drop_max'])))
        OUT.setdefault('plv', {}).setdefault(w, {})[NAMES[t]] = dict(
            f0=f0, plv=A['plv'], nonharm=(B['plv'] if B else None),
            shuffled=(C['plv'] if C else None), n_ep=A['n_ep'],
            drop=[A['drop_min'], A['drop_max']])
print("  🛑 A PLV is only meaningful if it CLEARLY exceeds BOTH the 1.65f0 non-harmonic control")
print("     and the phase-shuffled control, AND survives drop-one.  The record already reports")
print("     this test as NULL for grind #3 (V105 handoff retraction 11, refuted 4 ways).")

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 '_scratch/out/_ra5_three_grinds.json'), 'w'), indent=1, default=float)
print("\nwrote _scratch/out/_ra5_three_grinds.json")
