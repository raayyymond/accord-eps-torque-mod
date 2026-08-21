"""POSITIVE CONTROL: reproduce docs/GATE2-2026-08-20-notch-sign.md Table 2.1 and 3.2."""
import numpy as np, _gate2_boost_lib as L

NPER = int(round(4 * L.FS))            # 4 s Hann
ROUTES = [('r85','V100 4x','x6b94','SUM'),('r95','V101 8x','x6b94','SUM'),
          ('r96','V102 6x','x6b4c','LANE'),('r9e','V103 6x','x6b4c','LANE')]

print(f"nperseg = {NPER} samples = {NPER/L.FS:.3f} s ; fs = {L.FS:.4f} Hz")
print("\n=== POSITIVE CONTROL: 6-9 Hz  u/T (or lane/T) ===")
print(f"{'route':6} {'build':10} {'tgt':5} {'|H|':>8} {'phase':>8} {'coh2':>6} {'eps':>4}  {'|H| CI':>18} {'phase CI':>18}")
store={}
for tag,bld,key,kind in ROUTES:
    d=L.load(tag); f=np.fft.rfftfreq(NPER, 1/L.FS)
    eps=L.episodes(d['cc_lat']>0.5)
    x=d['tq'].astype(float); y=d[key].astype(float)
    sp=L.episode_specs(x,y,eps,NPER)
    H,coh,arr=L.boot_H(sp,f,6.0,9.0,nboot=4000,seed=11)
    mci=L.ci(np.abs(arr)); pci=L.phase_ci(arr,np.angle(H,deg=True))
    print(f"{tag:6} {bld:10} {kind:5} {abs(H):8.4f} {np.angle(H,deg=True):+8.1f} {coh:6.3f} {len(sp):4d}  [{mci[0]:.4f},{mci[1]:.4f}]  [{pci[0]:+.1f},{pci[1]:+.1f}]")
    store[tag]=(f,sp,eps,d)

print("\n=== POSITIVE CONTROL: Z = S_wT/S_ww on r9e (w=rate_f rad/s, T=tq counts) ===")
d=store['r9e'][3]; f=store['r9e'][0]; eps=store['r9e'][2]
w=d['rate_f'].astype(float)*L.DEG2RAD; T=d['tq'].astype(float)
spz=L.episode_specs(w,T,eps,NPER)
print(f"{'band':10} {'Re(Z)':>10} {'ReCI':>22} {'Im(Z)':>10} {'ImCI':>22} {'|Z|':>8} {'arg':>8} {'coh2':>6}")
for lo,hi in [(2,4),(4,6),(6,9),(9,13),(13,15),(15,22),(21.0,22.5),(22,26),(26,31)]:
    Z,coh,arr=L.boot_H(spz,f,lo,hi,nboot=4000,seed=13)
    rc=L.ci(arr.real); ic=L.ci(arr.imag)
    print(f"{lo:4.1f}-{hi:4.1f} {Z.real:10.0f} [{rc[0]:9.0f},{rc[1]:9.0f}] {Z.imag:10.0f} [{ic[0]:9.0f},{ic[1]:9.0f}] {abs(Z):8.0f} {np.angle(Z,deg=True):+8.1f} {coh:6.3f}")
np.save('_g2b_pc_marker.npy', np.array([1]))
