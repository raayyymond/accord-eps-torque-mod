"""Transfer function from the MODEL's desired lateral accel to the ACHIEVED lateral accel,
by frequency band, on CONTIGUOUS engaged runs only.

No differentiation (my last attempt died on differentiation noise). No concatenation across
gaps (a prior session's bug -- every join is a broadband step). Delay handled by reading the
PHASE of the cross-spectrum rather than regressing in the time domain.

The existing suite stops at 0.60 Hz (FINE band). The operator's notes 4 and 5 are about
TRANSIENTS, which live above that. This extends the same convention upward.
"""
import numpy as np
from scipy import signal

D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t = D['t_cs']; act = D['cs_active'].astype(bool)
la_des, la_act = D['cs_la_des'], D['cs_la_act']
v = np.interp(t, D['t_cst'], D['vego'])
sa = np.interp(t, D['t_cst'], D['sa_deg'])
FS = 1.0/float(np.median(np.diff(t)))

BANDS = [('MID   0.08-0.25', 0.08, 0.25), ('FINE  0.25-0.60', 0.25, 0.60),
         ('TRANS 0.60-1.20', 0.60, 1.20), ('FAST  1.20-3.00', 1.20, 3.00)]

def contiguous_runs(mask, t, min_s):
    """Index slices of contiguous True with no time gap > 3 frames."""
    out, n = [], len(mask)
    i = 0
    while i < n:
        if not mask[i]: i += 1; continue
        j = i
        while j+1 < n and mask[j+1] and (t[j+1]-t[j]) < 4.0/FS:
            j += 1
        if (t[j]-t[i]) >= min_s: out.append((i, j+1))
        i = j+1
    return out

def band_tf(runs, x, y, f1, f2, nps):
    """Welch cross-spectrum pooled over runs -> |H| and phase in [f1,f2]."""
    Pxx = Pxy = None; freqs = None; nseg = 0
    for a, b in runs:
        xs, ys = x[a:b], y[a:b]
        if len(xs) < nps: continue
        xs = xs - xs.mean(); ys = ys - ys.mean()
        f, pxx = signal.welch(xs, FS, nperseg=nps, noverlap=nps//2)
        _, pxy = signal.csd(xs, ys, FS, nperseg=nps, noverlap=nps//2)
        w = len(xs)
        Pxx = pxx*w if Pxx is None else Pxx + pxx*w
        Pxy = pxy*w if Pxy is None else Pxy + pxy*w
        freqs = f; nseg += 1
    if Pxx is None: return None
    sel = (freqs >= f1) & (freqs < f2)
    if sel.sum() < 2: return None
    H = Pxy[sel].sum()/Pxx[sel].sum()
    # coherence-weighted quality
    return abs(H), np.degrees(np.angle(H)), sel.sum(), nseg

print(f"FS = {FS:.2f} Hz")
print("="*96)
print("BAND TRANSFER FUNCTION  desired lateral accel -> achieved lateral accel")
print("  |H| = 1.000 is a perfect match.  phase is negative = the car LAGS the model.")
print("="*96)
for vlo, vhi, label in [(12.0, 18.0, '12-18 m/s'), (18.0, 24.0, '18-24 m/s'), (24.0, 32.0, '24-32 m/s')]:
    m = act & (v >= vlo) & (v < vhi)
    runs = contiguous_runs(m, t, 40.0)
    tot = sum(b-a for a, b in runs)
    print(f"\n{label}:  {len(runs)} contiguous engaged runs >= 40 s, {tot/FS:.0f} s total")
    if not runs: continue
    print(f"  {'band':>16} {'|H|':>8} {'phase deg':>10} {'bins':>6} {'runs':>5}   interpretation")
    for name, f1, f2 in BANDS:
        nps = int(min(2**np.floor(np.log2(FS*40)), 2**np.floor(np.log2(min(b-a for a,b in runs)))))
        r = band_tf(runs, la_des, la_act, f1, f2, nps)
        if r is None: print(f"  {name:>16}   (insufficient resolution)"); continue
        mag, ph, nb, ns = r
        interp = ('matches' if 0.9 <= mag <= 1.1 else
                  'UNDER-delivers' if mag < 0.9 else 'OVER-delivers')
        print(f"  {name:>16} {mag:8.3f} {ph:10.1f} {nb:6d} {ns:5d}   {interp}")

print()
print("="*96)
print("POSITIVE CONTROL: the same transfer function, desired -> desired (must be 1.000, 0 deg)")
print("="*96)
m = act & (v >= 18.0) & (v < 24.0)
runs = contiguous_runs(m, t, 40.0)
if runs:
    nps = int(min(2**np.floor(np.log2(FS*40)), 2**np.floor(np.log2(min(b-a for a,b in runs)))))
    for name, f1, f2 in BANDS:
        r = band_tf(runs, la_des, la_des, f1, f2, nps)
        if r: print(f"  {name:>16} |H|={r[0]:.4f}  phase={r[1]:+.2f} deg")
    print()
    print("NEGATIVE CONTROL: desired -> desired delayed by 0.29 s (the measured liveDelay)")
    lag = int(round(0.29*FS))
    delayed = np.concatenate([np.full(lag, la_des[0]), la_des[:-lag]])
    for name, f1, f2 in BANDS:
        r = band_tf(runs, la_des, delayed, f1, f2, nps)
        if r:
            fc = 0.5*(f1+f2)
            print(f"  {name:>16} |H|={r[0]:.4f}  phase={r[1]:+.1f} deg   (expected {-360*fc*0.29:+.1f} deg)")
