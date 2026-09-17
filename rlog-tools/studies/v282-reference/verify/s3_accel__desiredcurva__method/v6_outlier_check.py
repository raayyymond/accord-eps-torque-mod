"""Is the LINEAR-band (2.5-8 m/s) des-rate elevation in T4/T64B/T64 a few extreme spike samples, or genuine
broadband texture? Bandpass filter the desired angle-rate to 1-3 Hz within the usable(2.5,8) mask per run,
and report kurtosis + the fraction of total band energy contributed by the single largest 1% of |samples|,
plus min instantaneous v seen in each contributing run (to catch any residual near-stop leakage)."""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal, stats as spstats
import v282cmp as V

M = 3279*0.45359237+136.0; WB=2.83; AF=0.39*WB; AR=WB-AF; TSF=0.8467
_M0,_WB0=1326.+136.,2.70; _AF0=_WB0*0.4; _AR0=_WB0-_AF0
CF=192150*TSF*M/_M0*(AR/WB)/(_AR0/_WB0); CR=202500*TSF*M/_M0*(AF/WB)/(_AF0/_WB0)
SF=M*(CF*AF-CR*AR)/(WB**2*CF*CR); SR_FIX=16.33
def curv_to_angle(k,v): return -np.degrees(k*SR_FIX*WB*(1.0-SF*v**2))

SOS = signal.butter(4,[1.0,3.0],btype='band',fs=V.FS,output='sos')

for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    v = np.nan_to_num(S['v']); vv = np.maximum(v,0.5)
    k_m = np.nan_to_num(S['model'])/vv**2
    ad = curv_to_angle(k_m, v)
    adr = V.deriv(ad)
    u = V.usable(S, 2.5, 8.0)
    segs = V.runs(u, S['t'], min_s=5.12)
    allx=[]; vmins=[]
    for a,b in segs:
        x = adr[a:b]
        xb = signal.sosfiltfilt(SOS, x)
        allx.append(xb)
        vmins.append(v[a:b].min())
    if not allx:
        print(f"{rk:24s} {meta['group']:7s} no runs"); continue
    x = np.concatenate(allx)
    rms = np.sqrt(np.mean(x**2))
    kurt = spstats.kurtosis(x)
    ax = np.abs(x)
    n1 = max(1,int(0.01*len(ax)))
    top1pct_energy_frac = float(np.sum(np.sort(ax)[-n1:]**2) / np.sum(ax**2))
    p99 = np.percentile(ax,99); pmax = ax.max()
    print(f"{rk:24s} {meta['group']:7s} n={len(x):6d} rms={rms:6.2f} kurtosis={kurt:7.2f} "
          f"top1%energy_frac={top1pct_energy_frac:.3f} p99={p99:6.1f} max={pmax:7.1f} vmin_in_runs={min(vmins):.2f}")
    del S
