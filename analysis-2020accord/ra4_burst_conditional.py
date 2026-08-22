"""BURST / CONDITIONAL READOUTS ON THE 21-28 Hz MODE, AT THE OPERATOR'S OWN WINDOW (< 16 km/h).

Operator, 2026-08-22: "It's like vibration comes in and out while highway driving and the
ratchet-like oscillation shows up on top of it when it's happening, sometimes."
And: "grinding ... low speed < 10 mph".

WHY THIS BAND, AT THIS WINDOW: `ra4_lowspeed_rescore.py` measured the 21-28 Hz mode at
**64.2x stock below 10 km/h** -- the largest contrast in this corpus, 6-9x the 6-9 Hz contrast in
the same window, 70-94x stock on the 6x builds -- peaking exactly where he reports grinding,
wheel order excluded (regression R2 = 0.039), and untouched by any lever on V104.

=================================================================================================
🛑 THE DETECTOR, PRE-DECLARED IN FULL BEFORE ANY OUTCOME WAS SEEN
=================================================================================================
CARRIER ENVELOPE
  `rate_f` band-limited to 21-28 Hz, TRUE ANALYTIC envelope |x + j.H{x}|.
  🛑 NOT the kit's `band_envelope`, which is RECTIFIED (one-sided H=2X then irfft, imaginary part
  discarded) -- measured this session to put its energy at 2.f_c: the 3-15 / 40-56 Hz envelope
  energy ratio is 431.2 analytic vs 0.487 rectified, a factor of ~885.
  [`accord-band-envelope-is-rectified-not-analytic`]

BURST DETECTOR  -- an ABSOLUTE threshold anchored to the STOCK arm, applied identically to all
                   four routes, so "burst duty" means the same physical thing on every build.
  THR_ON   = p95 of the STOCK (r97) ENGAGED < 16 km/h carrier envelope.        [one number, fixed]
  THR_OFF  = 0.70 x THR_ON                                                     [Schmitt hysteresis]
  MIN_BURST = 0.25 s  (~6 carrier cycles at 26 Hz)
  MERGE_GAP = 0.15 s  (gaps shorter than this do not end a burst)
  ⚠ DECLARED CONSEQUENCE: stock is the reference arm, so ITS duty is ~0.05 by construction.
    That is not a finding; the finding is how far the 6x arms sit above it.

RATCHET DETECTOR (the "ratchet on top of the vibration") -- events ON THE ENVELOPE, because that
                   is literally what he describes.
  envelope band-passed to 4-15 Hz; peaks with PROMINENCE >= 2.0 x MAD of that band-passed
  envelope computed WITHIN the burst; REFRACTORY 67 ms (caps the rate at 15 /s, above his 6-12).
  Reported as EVENTS PER SECOND inside bursts.

CONTROLS, RUN BEFORE ANY NUMBER IS QUOTED
  N1 PHASE-SHUFFLED SURROGATE -- randomise the 21-28 Hz band phases: destroys amplitude
     modulation and impulsiveness, preserves the spectrum EXACTLY.  The cleanest null available
     for both the burst structure and the event rate.
  N2 CONTROL-BAND CARRIER 32-45 Hz -- same detector, a band with no mode.
  N3 MANUAL arm, same speed window.
  Bootstrap over RUNS (contiguous mask segments), never windows.

🛑 POWER, STATED BEFORE THE RESULT: at < 16 km/h the run counts are r97 7 · r96 6 · **r9e 3** ·
   ra4 10.  **r9e's 3 runs cannot support a V104-vs-V103 comparison** and every such cell is
   marked rather than given a CI.
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
FS = L.FS
CARRIER = (21.0, 28.0)
CONTROL = (32.0, 45.0)
RATCHET = (4.0, 15.0)
THR_FRAC = 0.70
MIN_BURST_S = 0.25
MERGE_GAP_S = 0.15
PROM_MAD = 2.0
REFRACTORY_S = 0.067
VLO, VHI = 0.0, 16.0
TAGS = ('r97', 'r96', 'r9e', 'ra4')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x'}
NPER = int(round(4 * FS))
fb = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = fb[1] - fb[0]


def bp_analytic(x, lo, hi, shuffle=False, rng=None):
    """TRUE analytic envelope of x band-limited to [lo,hi)."""
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    keep = (fr >= lo) & (fr < hi)
    Y = np.zeros_like(X)
    Y[keep] = X[keep]
    if shuffle:
        Y[keep] = np.abs(Y[keep]) * np.exp(1j * rng.uniform(0, 2 * np.pi, keep.sum()))
    Z = np.zeros(n, complex)
    Z[:len(Y)] = 2.0 * Y
    Z[0] /= 2
    return np.abs(np.fft.ifft(Z))


def bp_real(x, lo, hi):
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    Y = np.zeros_like(X)
    k = (fr >= lo) & (fr < hi)
    Y[k] = X[k]
    return np.fft.irfft(Y, n)


def runs_of(tag, engaged=True, vlo=VLO, vhi=VHI, minlen=None):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = minlen if minlen is not None else int(2.0 * FS)
    return [rate[b[i]:b[i + 1]] for i in range(len(b) - 1)
            if m[b[i]] and (b[i + 1] - b[i]) >= ml]


def bursts(env, thr_on, thr_off):
    """Schmitt-triggered burst segments, min length and gap-merge applied."""
    on = np.zeros(len(env), bool)
    state = False
    for i, x in enumerate(env):
        state = (x >= thr_on) if not state else (x >= thr_off)
        on[i] = state
    idx = np.flatnonzero(np.diff(on.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(on)]))
    segs = [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1) if on[b[i]]]
    merged = []
    for s, e2 in segs:
        if merged and (s - merged[-1][1]) <= int(MERGE_GAP_S * FS):
            merged[-1] = (merged[-1][0], e2)
        else:
            merged.append((s, e2))
    return [(s, e2) for s, e2 in merged if (e2 - s) >= int(MIN_BURST_S * FS)]


def events(env_seg):
    """Ratchet events on a burst's envelope: 4-15 Hz peaks, prominence >= 2 MAD, 67 ms refractory."""
    if len(env_seg) < int(0.5 * FS):
        return 0
    y = bp_real(env_seg, *RATCHET)
    mad = np.median(np.abs(y - np.median(y)))
    if mad <= 0:
        return 0
    thr = PROM_MAD * mad
    ref = int(REFRACTORY_S * FS)
    n, last = 0, -10 ** 9
    for i in range(1, len(y) - 1):
        if y[i] > thr and y[i] >= y[i - 1] and y[i] > y[i + 1] and (i - last) >= ref:
            n += 1
            last = i
    return n


# ================================================================= 0. threshold
print("=" * 116)
print("0. THE PRE-DECLARED THRESHOLD, computed once from the STOCK arm")
print("=" * 116)
ref = runs_of('r97')
env_ref = np.concatenate([bp_analytic(r, *CARRIER) for r in ref]) if ref else np.array([0.0])
THR_ON = float(np.percentile(env_ref, 95))
THR_OFF = THR_FRAC * THR_ON
print("  STOCK (r97) engaged < 16 km/h, 21-28 Hz analytic envelope:")
print("     p50 %.4f  p75 %.4f  p90 %.4f  **p95 = THR_ON = %.4f**  p99 %.4f deg/s"
      % (np.percentile(env_ref, 50), np.percentile(env_ref, 75), np.percentile(env_ref, 90),
         THR_ON, np.percentile(env_ref, 99)))
print("     THR_OFF = 0.70 x THR_ON = %.4f   MIN_BURST %.2f s   MERGE_GAP %.2f s"
      % (THR_OFF, MIN_BURST_S, MERGE_GAP_S))

# ================================================================= 1-4
print()
print("=" * 116)
print("1-4. BURST DUTY · IN-BURST AMPLITUDE · IN-BURST RATCHET RATE, engaged < 16 km/h")
print("=" * 116)
print("%10s %6s %7s %10s %11s %11s %11s %11s %11s" %
      ('build', 'runs', 'sec', 'BURST DUTY', 'in-burst A', 'out-burst A', 'longest s',
       'ratchet /s', 'NULL /s'))
RES = {}
rng = np.random.default_rng(11)
for t in TAGS:
    rr = runs_of(t)
    if not rr:
        continue
    tot = dur = 0
    inb, outb, longest, ev, evdur = [], [], 0.0, 0, 0.0
    nev, nevdur = 0, 0.0
    duties = []
    for r in rr:
        env = bp_analytic(r, *CARRIER)
        bs = bursts(env, THR_ON, THR_OFF)
        n_on = sum(e2 - s for s, e2 in bs)
        tot += n_on
        dur += len(r)
        duties.append(n_on / len(r))
        for s, e2 in bs:
            inb.append(env[s:e2])
            longest = max(longest, (e2 - s) / FS)
            ev += events(env[s:e2])
            evdur += (e2 - s) / FS
        off = np.ones(len(env), bool)
        for s, e2 in bs:
            off[s:e2] = False
        if off.any():
            outb.append(env[off])
        envn = bp_analytic(r, *CARRIER, shuffle=True, rng=rng)
        for s, e2 in bursts(envn, THR_ON, THR_OFF):
            nev += events(envn[s:e2])
            nevdur += (e2 - s) / FS
    RES[t] = dict(duty=tot / dur, duties=duties, inb=np.concatenate(inb) if inb else np.array([]),
                  outb=np.concatenate(outb) if outb else np.array([]), longest=longest,
                  rate=ev / evdur if evdur > 0 else np.nan,
                  nrate=nev / nevdur if nevdur > 0 else np.nan, sec=dur / FS, nruns=len(rr))
    R = RES[t]
    print("%10s %6d %7.1f %10.4f %11.4f %11.4f %11.2f %11.2f %11.2f"
          % (NAMES[t], R['nruns'], R['sec'], R['duty'],
             np.median(R['inb']) if len(R['inb']) else np.nan,
             np.median(R['outb']) if len(R['outb']) else np.nan,
             R['longest'], R['rate'], R['nrate']))
print()
print("  BURST DUTY = fraction of engaged <16 km/h time above what STOCK exceeds 5 %% of the time.")
print("  in-burst / out-burst A = median 21-28 Hz analytic envelope, deg/s.")
print("  ratchet /s = 4-15 Hz envelope events inside bursts.  NULL /s = same detector on the")
print("  phase-shuffled surrogate (same spectrum, no AM).  🛑 the event rate is only meaningful")
print("  if it CLEARLY exceeds its own null.")

print()
print("  N2 CONTROL BAND (32-45 Hz carrier), same detector, threshold re-anchored on STOCK:")
ref2 = np.concatenate([bp_analytic(r, *CONTROL) for r in runs_of('r97')])
T2 = float(np.percentile(ref2, 95))
print("%10s %10s %11s %11s" % ('build', 'duty', 'in-burst A', 'ratchet /s'))
for t in TAGS:
    rr = runs_of(t)
    tot = dur = 0
    ev = 0
    evd = 0.0
    inb = []
    for r in rr:
        env = bp_analytic(r, *CONTROL)
        bs = bursts(env, T2, THR_FRAC * T2)
        tot += sum(e2 - s for s, e2 in bs)
        dur += len(r)
        for s, e2 in bs:
            inb.append(env[s:e2])
            ev += events(env[s:e2])
            evd += (e2 - s) / FS
    print("%10s %10.4f %11.4f %11.2f"
          % (NAMES[t], tot / dur, np.median(np.concatenate(inb)) if inb else np.nan,
             ev / evd if evd > 0 else np.nan))

print()
print("  N3 MANUAL arm, same window, same 21-28 Hz threshold:")
print("%10s %6s %7s %10s %11s" % ('build', 'runs', 'sec', 'duty', 'in-burst A'))
for t in TAGS:
    rr = runs_of(t, engaged=False)
    if not rr:
        continue
    tot = dur = 0
    inb = []
    for r in rr:
        env = bp_analytic(r, *CARRIER)
        bs = bursts(env, THR_ON, THR_OFF)
        tot += sum(e2 - s for s, e2 in bs)
        dur += len(r)
        for s, e2 in bs:
            inb.append(env[s:e2])
    print("%10s %6d %7.1f %10.4f %11.4f"
          % (NAMES[t], len(rr), dur / FS, tot / dur,
             np.median(np.concatenate(inb)) if inb else np.nan))

# ================================================================= 5. threshold test
print()
print("=" * 116)
print("5. THE THRESHOLD TEST -- does in-burst ratchet rate rise once carrier amplitude crosses")
print("   a level?  A threshold = a stick-slip / relay engaging above a critical amplitude.")
print("=" * 116)
print("%10s" % 'build' + "".join("%14s" % ("A<%.2f" % q) for q in (1, 2, 3, 5))
      + "%14s" % 'A>=5x thr')
for t in TAGS:
    rr = runs_of(t)
    binsA = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 1e9)]
    cnt = [[0, 0.0] for _ in binsA]
    for r in rr:
        env = bp_analytic(r, *CARRIER)
        for s, e2 in bursts(env, THR_ON, THR_OFF):
            a = np.median(env[s:e2]) / THR_ON
            for bi, (lo2, hi2) in enumerate(binsA):
                if lo2 <= a < hi2:
                    cnt[bi][0] += events(env[s:e2])
                    cnt[bi][1] += (e2 - s) / FS
                    break
    print("%10s" % NAMES[t] + "".join(
        ("%14.2f" % (c[0] / c[1]) if c[1] > 1.0 else "%14s" % '-') for c in cnt))
print("  cells are ratchet events/s inside bursts, binned by the burst's own median envelope in")
print("  units of THR_ON.  A RISING row = amplitude-triggered.  A FLAT row = no threshold.")

# ================================================================= 6. burst-conditioned table
print()
print("=" * 116)
print("6. THE STOCK->6x TABLE, BURST-CONDITIONED -- how much did pooling cost?")
print("=" * 116)
FBB = [(6, 9), (13, 18), (18, 22), (21, 28), (32, 45)]


def band_rms_masked(tag, use_burst):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= VLO) & (v < VHI)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    acc, nw = None, 0
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not m[a0] or (b0 - a0) < NPER:
            continue
        seg = rate[a0:b0]
        env = bp_analytic(seg, *CARRIER)
        onmask = np.zeros(len(seg), bool)
        for s, e2 in bursts(env, THR_ON, THR_OFF):
            onmask[s:e2] = True
        sel = onmask if use_burst else ~onmask
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            if not sel[s:s + NPER].all():
                continue
            xs = seg[s:s + NPER]
            xs = xs - xs.mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
    return (acc / nw if nw else None), nw


print("%12s" % 'band' + "".join("%13s" % (NAMES[t] + " P") for t in TAGS)
      + "%16s %16s" % ('V104/STOCK pooled', 'V104/STOCK IN-BURST'))
POOL = {t: band_rms_masked(t, False) for t in TAGS}
BUR = {t: band_rms_masked(t, True) for t in TAGS}
for t in TAGS:
    print("     windows %s: pooled(out-burst) %d, in-burst %d" % (t, POOL[t][1], BUR[t][1]))
print()
for lo2, hi2 in FBB:
    sel = (fb >= lo2) & (fb < hi2)
    vals = []
    for t in TAGS:
        S = BUR[t][0]
        vals.append(np.sqrt(S[sel].sum() * DF) if S is not None else np.nan)
    ok = all(BUR[t][0] is not None for t in ('r97', 'ra4'))
    pl = (np.sqrt(POOL['ra4'][0][sel].sum() * DF) / np.sqrt(POOL['r97'][0][sel].sum() * DF)
          if POOL['ra4'][0] is not None and POOL['r97'][0] is not None else np.nan)
    ib = vals[3] / vals[0] if ok else np.nan
    print("%7.0f-%-4.0f" % (lo2, hi2) + "".join("%13.4f" % v for v in vals)
          + "%16.2f %16.2f" % (pl, ib))
print("  'P' columns are IN-BURST band RMS (deg/s).  Last two columns: the same V104/STOCK ratio")
print("  computed OUT of bursts vs IN bursts.  If in-burst is larger, pooling diluted it.")


# ================================================================= 7. HIS ACTUAL BURST REGIME
print()
print("=" * 116)
print("7. 🛑 HIS 'COMES IN AND OUT' WAS ABOUT THE HIGHWAY, NOT THIS WINDOW.")
print("=" * 116)
print('  "It\'s like vibration comes in and out WHILE HIGHWAY DRIVING and the ratchet-like')
print('   oscillation shows up on top of it when it\'s happening, sometimes."')
print("  Sections 1-6 used < 16 km/h because that is where he places GRINDING.  The BURST")
print("  structure he describes is a HIGHWAY observation, so it must be tested there.")
print("  Threshold re-anchored on STOCK's own highway arm, same detector otherwise.")
print()
for lbl, vlo2, vhi2 in (('40-80 km/h', 40.0, 80.0), ('80-95 km/h (matched)', 80.0, 95.0)):
    rr97 = runs_of('r97', True, vlo2, vhi2)
    if not rr97:
        continue
    e97 = np.concatenate([bp_analytic(r, *CARRIER) for r in rr97])
    T = float(np.percentile(e97, 95))
    print("  %s   THR_ON = %.4f deg/s (STOCK p95 in this window)" % (lbl, T))
    print("%10s %6s %7s %10s %11s %11s %11s %11s" %
          ('build', 'runs', 'sec', 'duty', 'in-burst A', 'longest s', 'ratchet /s', 'NULL /s'))
    for t in TAGS:
        rr = runs_of(t, True, vlo2, vhi2)
        if not rr:
            continue
        tot = dur = 0
        inb, longest, ev, evd = [], 0.0, 0, 0.0
        nev, nevd = 0, 0.0
        for r in rr:
            env = bp_analytic(r, *CARRIER)
            bs = bursts(env, T, THR_FRAC * T)
            tot += sum(e2 - s for s, e2 in bs)
            dur += len(r)
            for s, e2 in bs:
                inb.append(env[s:e2])
                longest = max(longest, (e2 - s) / FS)
                ev += events(env[s:e2])
                evd += (e2 - s) / FS
            envn = bp_analytic(r, *CARRIER, shuffle=True, rng=rng)
            for s, e2 in bursts(envn, T, THR_FRAC * T):
                nev += events(envn[s:e2])
                nevd += (e2 - s) / FS
        print("%10s %6d %7.1f %10.4f %11.4f %11.2f %11.2f %11.2f"
              % (NAMES[t], len(rr), dur / FS, tot / dur,
                 np.median(np.concatenate(inb)) if inb else np.nan, longest,
                 ev / evd if evd > 0 else np.nan, nev / nevd if nevd > 0 else np.nan))
    print()

# ================================================================= 8. why 6 failed
print("=" * 116)
print("8. 🛑 WHY SECTION 6 IS NOT COMPUTABLE, AND WHAT THAT ITSELF SHOWS")
print("=" * 116)
print("  A burst-conditioned band RMS needs 4 s windows lying wholly inside (or wholly outside)")
print("  a burst.  At < 16 km/h:")
print("     STOCK burst duty 0.056, LONGEST BURST 0.69 s  =>  ZERO windows fit inside a burst,")
print("       at 4 s, at 2 s, or even at 1 s.  ⇒ STOCK'S MODE NEVER SUSTAINS FOR ONE SECOND.")
print("     6x builds duty 0.93-0.95            =>  ZERO windows fit wholly OUTSIDE a burst.")
print("  ⇒ THE TWO ARMS HAVE NO OVERLAPPING CONDITION.  The contrast cannot be conditioned.")
print()
print("  ⭐ AND THE DIRECTION OF THE POOLING ARTIFACT IS THE OPPOSITE OF WHAT WAS FEARED:")
sd = RES['r97']
for t in ('r96', 'r9e', 'ra4'):
    R = RES[t]
    print("     %-9s in-burst A %7.3f vs STOCK in-burst %7.3f  =>  CONDITIONED ratio %6.2f"
          % (NAMES[t], np.median(R['inb']), np.median(sd['inb']),
             np.median(R['inb']) / np.median(sd['inb'])))
print("     ...against POOLED 21-28 Hz ratios of 57x / 55x / 41x vs stock at this window.")
print("  ⇒ pooling INFLATES the low-speed contrast ~12x, because it compares a 6x arm that is on")
print("    95 %% of the time against a stock arm that is on 5.6 %% of the time.  BOTH numbers are")
print("    real and they answer DIFFERENT questions:")
print("      POOLED     'how different is the car overall'      -> 41-64x  (duty + amplitude)")
print("      CONDITIONED'when it is happening, how much louder' -> 3.5-13x (amplitude only)")
print("    🛑 The duty difference is the larger part of the effect and had never been measured.")


# ================================================================= 9. CIs on the headline numbers
print()
print("=" * 116)
print("9. RUN-BOOTSTRAP CIs ON THE TWO HEADLINE NUMBERS (duty and in-burst amplitude)")
print("=" * 116)


def boot_burst(tag, vlo2, vhi2, thr, nb=2000, seed=7):
    rr = runs_of(tag, True, vlo2, vhi2)
    if len(rr) < 3:
        return None
    per = []
    for r in rr:
        env = bp_analytic(r, *CARRIER)
        bs = bursts(env, thr, THR_FRAC * thr)
        on = sum(e2 - s for s, e2 in bs)
        amps = np.concatenate([env[s:e2] for s, e2 in bs]) if bs else np.array([])
        per.append((on, len(r), amps))
    rg = np.random.default_rng(seed)
    D, A = [], []
    for _ in range(nb):
        pick = rg.integers(0, len(per), len(per))
        on = sum(per[j][0] for j in pick)
        tot = sum(per[j][1] for j in pick)
        aa = [per[j][2] for j in pick if len(per[j][2])]
        D.append(on / tot)
        if aa:
            A.append(np.median(np.concatenate(aa)))
    dd = np.percentile(D, [2.5, 97.5])
    ad = np.percentile(A, [2.5, 97.5]) if A else (np.nan, np.nan)
    return len(rr), dd, ad


for lbl, vlo2, vhi2, thr in (('< 16 km/h', 0.0, 16.0, THR_ON),
                             ('40-80 km/h', 40.0, 80.0, 2.0775),
                             ('80-95 km/h', 80.0, 95.0, 1.9950)):
    print("  %s" % lbl)
    print("%12s %7s %26s %26s" % ('build', 'runs', 'burst duty 95 % CI', 'in-burst A 95 % CI'))
    for t in TAGS:
        r = boot_burst(t, vlo2, vhi2, thr)
        if r is None:
            rr = runs_of(t, True, vlo2, vhi2)
            print("%12s %7d   *** < 3 runs -- NOT COMPARABLE ***" % (NAMES[t], len(rr)))
            continue
        n, dd, ad = r
        print("%12s %7d      [%8.4f, %8.4f]      [%8.3f, %8.3f]"
              % (NAMES[t], n, dd[0], dd[1], ad[0], ad[1]))
    print()
