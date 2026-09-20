"""Independent re-derivation of the demand-matched wheel-mode-band RMS table directly from RUNS
(bypassing BLK / d_extract.py's block reduction and d_matched.py's pipeline entirely)."""
import sys, numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS=100.0
def bp(x, f1, f2, order=4):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)
def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)
def deriv(x):
    return np.gradient(x) * FS

BLOCK = 128  # 1.28s blocks, matching d_extract.py's block cadence

def cells_for_route(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS=D['RUNS']; RUNLEN=D['RUNLEN']; o=0
    out=[]  # list of (v, abs_des, abs_rate_des, sr1835_block_rms)
    for n in RUNLEN:
        r = RUNS[:, o:o+n]; o+=n
        if n<300: continue
        v=r[0]; sad=r[1]; sr=r[4]
        rate_des = deriv(lp(sad, 2.0, 2))
        sr18 = bp(sr, 1.8, 3.5)
        for k0 in range(50, n-50-BLOCK+1, BLOCK):
            s = slice(k0, k0+BLOCK)
            out.append((float(np.median(v[s])), float(np.mean(np.abs(sad[s]))), float(np.mean(np.abs(rate_des[s]))),
                        float(np.sqrt(np.mean(sr18[s]**2)))))
    return out

RB = [(0,5),(5,15),(15,35)]
groups = {}
for rk, meta in V.ROUTES.items():
    groups.setdefault(meta['group'], []).extend(cells_for_route(rk))

print("Independent recompute: sr_18_35 RMS, 2.5-8 m/s, |des|<45, by demand-rate bin")
for g in ['V282','V282old','T64','T64B','T5','T4']:
    if g not in groups: continue
    rows = np.array(groups[g])
    v,ad,ard,sr18 = rows[:,0], rows[:,1], rows[:,2], rows[:,3]
    m8 = (v>=2.5)&(v<8.0)&(ad<45)
    line=[]
    for lo,hi in RB:
        mm = m8 & (ard>=lo)&(ard<hi)
        if mm.sum()<5:
            line.append(f"{lo}-{hi}:n{mm.sum()}"); continue
        line.append(f"{lo}-{hi}: n={mm.sum():4d} rms={np.sqrt(np.mean(sr18[mm]**2)):.3f}")
    print(f"{g:8s}  " + "   ".join(line))
