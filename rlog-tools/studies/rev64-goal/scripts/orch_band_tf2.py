"""Band transfer function, desired -> achieved lateral accel, on route 76's natural engaged runs.
Fix vs orch_band_tf.py: do not pre-filter by instantaneous speed (that fragments runs); use the
runs as they are and report each run's mean speed. Per-band minimum run length so a band is only
scored where the window can actually resolve it.
"""
import numpy as np
from scipy import signal

D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t = D['t_cs']; act = D['cs_active'].astype(bool)
la_des, la_act = D['cs_la_des'], D['cs_la_act']
v = np.interp(t, D['t_cst'], D['vego'])
FS = 1.0/float(np.median(np.diff(t)))

# band, f1, f2, min cycles needed in a window -> min run length
BANDS = [('MID   0.08-0.25', 0.08, 0.25, 60.0),
         ('FINE  0.25-0.60', 0.25, 0.60, 24.0),
         ('TRANS 0.60-1.20', 0.60, 1.20, 12.0),
         ('FAST  1.20-3.00', 1.20, 3.00,  8.0)]

def natural_runs(mask):
    out, n, i = [], len(mask), 0
    while i < n:
        if not mask[i]: i += 1; continue
        j = i
        while j+1 < n and mask[j+1] and (t[j+1]-t[j]) < 4.0/FS: j += 1
        out.append((i, j+1)); i = j+1
    return out

RUNS = natural_runs(act)
print(f"FS={FS:.2f} Hz   engaged runs: " + ", ".join(f"{(b-a)/FS:.0f}s@{v[a:b].mean():.0f}m/s" for a,b in RUNS))

def band_tf(runs, x, y, f1, f2, min_s):
    use = [(a,b) for a,b in runs if (b-a)/FS >= min_s]
    if not use: return None
    nps = int(2**np.floor(np.log2(min(b-a for a,b in use))))
    Pxx = Pxy = None; freqs = None; secs = 0.0
    for a,b in use:
        xs, ys = x[a:b]-x[a:b].mean(), y[a:b]-y[a:b].mean()
        f, pxx = signal.welch(xs, FS, nperseg=nps, noverlap=nps//2)
        _, pxy = signal.csd(xs, ys, FS, nperseg=nps, noverlap=nps//2)
        w = b-a
        Pxx = pxx*w if Pxx is None else Pxx+pxx*w
        Pxy = pxy*w if Pxy is None else Pxy+pxy*w
        freqs = f; secs += w/FS
    sel = (freqs>=f1)&(freqs<f2)
    if sel.sum() < 2: return None
    H = Pxy[sel].sum()/Pxx[sel].sum()
    return abs(H), np.degrees(np.angle(H)), sel.sum(), len(use), secs, freqs[1]-freqs[0]

print()
print("="*100)
print("CONTROLS FIRST -- if these fail, ignore everything below")
print("="*100)
lag = int(round(0.29*FS))
delayed = np.concatenate([np.full(lag, la_des[0]), la_des[:-lag]])
print(f"  {'band':>16} {'pos ctl |H|,ph':>20} {'neg ctl (0.29s delay) |H|, ph  [expected ph]':>46}")
for name,f1,f2,ms in BANDS:
    r0 = band_tf(RUNS, la_des, la_des, f1, f2, ms)
    r1 = band_tf(RUNS, la_des, delayed, f1, f2, ms)
    if not r0: print(f"  {name:>16}   (no run long enough)"); continue
    fc = 0.5*(f1+f2); exp = -360*fc*0.29
    print(f"  {name:>16}   {r0[0]:6.4f}, {r0[1]:+6.2f}      {r1[0]:6.4f}, {r1[1]:+8.1f}   [{exp:+8.1f}]")

print()
print("="*100)
print("ROUTE 76 (REV 5) BASELINE -- model's desired lateral accel -> achieved")
print("  |H|=1 perfect.  <1 under-delivers (loose / understeer).  >1 over-delivers (oversteer).")
print("="*100)
print(f"  {'band':>16} {'|H|':>8} {'phase':>9} {'bins':>5} {'runs':>5} {'sec':>7} {'df Hz':>7}   verdict")
for name,f1,f2,ms in BANDS:
    r = band_tf(RUNS, la_des, la_act, f1, f2, ms)
    if not r: print(f"  {name:>16}   (no engaged run >= {ms:.0f}s)"); continue
    mag,ph,nb,nr,secs,df = r
    verdict = 'MATCHES' if 0.9<=mag<=1.1 else ('UNDER-delivers' if mag<0.9 else 'OVER-delivers')
    print(f"  {name:>16} {mag:8.3f} {ph:+9.1f} {nb:5d} {nr:5d} {secs:7.0f} {df:7.4f}   {verdict}")

print()
print("  Split-half noise floor (odd vs even runs), same bands:")
odd = RUNS[0::2]; even = RUNS[1::2]
for name,f1,f2,ms in BANDS:
    ra = band_tf(odd, la_des, la_act, f1, f2, ms); rb = band_tf(even, la_des, la_act, f1, f2, ms)
    if ra and rb:
        print(f"    {name:>16}  halves: {ra[0]:.3f} / {rb[0]:.3f}   spread {abs(ra[0]-rb[0]):.3f}")
    else:
        print(f"    {name:>16}  (one half has no qualifying run -- cannot split)")
