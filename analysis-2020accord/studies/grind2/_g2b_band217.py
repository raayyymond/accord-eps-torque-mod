"""THE 21.7 Hz SIGN QUESTION: full band table, all four routes, 6-9 vs 21.0-22.5 Hz."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS))
ROUTES=[('r85','V100 4x','x6b94','SUM'),('r95','V101 8x','x6b94','SUM'),
        ('r96','V102 6x','x6b4c','LANE'),('r9e','V103 6x','x6b4c','LANE')]
BANDS=[('6.0-9.0',6.0,9.0),('15-22',15.,22.),('21.0-22.5',21.0,22.5),('22-26',22.,26.)]

print("=== 427 transfer  (y/T) per route, per band ===")
print(f"{'route':6}{'kind':6}{'band':11}{'|H|':>8}{'phase':>8}{'coh2':>7}{'eps':>4}   {'|H| CI':>20}{'phase CI':>18}")
TR={}
for tag,bld,key,kind in ROUTES:
    d=L.load(tag); f=np.fft.rfftfreq(NPER,1/L.FS); eps=L.episodes(d['cc_lat']>0.5)
    sp=L.episode_specs(d['tq'].astype(float),d[key].astype(float),eps,NPER)
    for nm,lo,hi in BANDS:
        H,coh,arr=L.boot_H(sp,f,lo,hi,nboot=4000,seed=21)
        mci=L.ci(np.abs(arr)); pci=L.phase_ci(arr,np.angle(H,deg=True))
        TR[(tag,nm)]=(H,coh,arr)
        print(f"{tag:6}{kind:6}{nm:11}{abs(H):8.4f}{np.angle(H,deg=True):+8.1f}{coh:7.3f}{len(sp):4d}   [{mci[0]:.4f},{mci[1]:.4f}]  [{pci[0]:+6.1f},{pci[1]:+6.1f}]")
    print()

print("=== Z = S_wT/S_ww per route (plant-side impedance, engaged) ===")
print(f"{'route':6}{'band':11}{'Re(Z)':>9}{'ReCI':>20}{'Im(Z)':>9}{'|Z|':>8}{'arg':>8}{'coh2':>7}")
ZZ={}
for tag,bld,key,kind in ROUTES:
    d=L.load(tag); f=np.fft.rfftfreq(NPER,1/L.FS); eps=L.episodes(d['cc_lat']>0.5)
    spz=L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER)
    for nm,lo,hi in BANDS:
        Z,coh,arr=L.boot_H(spz,f,lo,hi,nboot=4000,seed=23)
        rc=L.ci(arr.real); ZZ[(tag,nm)]=(Z,coh,arr)
        print(f"{tag:6}{nm:11}{Z.real:9.0f} [{rc[0]:8.0f},{rc[1]:8.0f}]{Z.imag:9.0f}{abs(Z):8.0f}{np.angle(Z,deg=True):+8.1f}{coh:7.3f}")
    print()
np.savez('_scratch/data/_g2b_band217.npz',
   **{f'TR|{k[0]}|{k[1]}':v[2] for k,v in TR.items()},
   **{f'ZZ|{k[0]}|{k[1]}':v[2] for k,v in ZZ.items()},
   **{f'TRp|{k[0]}|{k[1]}':np.array([v[0],v[1]]) for k,v in TR.items()},
   **{f'ZZp|{k[0]}|{k[1]}':np.array([v[0],v[1]]) for k,v in ZZ.items()})
