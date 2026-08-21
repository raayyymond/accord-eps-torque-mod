"""ITEM 4: identify the loop from the GAIN STEPS.   Z = Z0/(1+P),  P = c*G,  c = lambda*kappa.
Two builds, same plant:  rho = Z_4/Z_8  =>  c = (rho-1)/(G_8 - rho*G_4).   ONE complex eq, ONE complex unknown."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)

def load_sp(tag,ykey):
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    spG=L.episode_specs(d['tq'].astype(float),d[ykey].astype(float),eps,NPER)
    spZ=L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER)
    return d,eps,spG,spZ

d4,e4,G4s,Z4s=load_sp('r85','x6b94')      # V100, 4x LKAS gain, 427 = SUM
d8,e8,G8s,Z8s=load_sp('r95','x6b94')      # V101, 8x LKAS gain, 427 = SUM
print(f"r85 (V100 4x): {len(e4)} episodes, {sum(b-a for a,b in e4)/L.FS:.1f} s engaged")
print(f"r95 (V101 8x): {len(e8)} episodes, {sum(b-a for a,b in e8)/L.FS:.1f} s engaged")
print("speed p10/p50/p90 (m/s) engaged: r85",
      np.percentile(d4['v_rear'][d4['cc_lat']>0.5],[10,50,90]).round(1),
      " r95", np.percentile(d8['v_rear'][d8['cc_lat']>0.5],[10,50,90]).round(1))

def solve(lo,hi,nboot=6000,seed=41):
    rng=np.random.default_rng(seed)
    def one(g4,z4,g8,z8):
        G4=L.band_H(g4,f,lo,hi)[0]; Z4=L.band_H(z4,f,lo,hi)[0]
        G8=L.band_H(g8,f,lo,hi)[0]; Z8=L.band_H(z8,f,lo,hi)[0]
        rho=Z4/Z8
        c=(rho-1)/(G8-rho*G4)
        return c, c*G4, c*G8, G4, G8, Z4, Z8
    pt=one(G4s,Z4s,G8s,Z8s)
    out=[]
    n4,n8=len(G4s),len(G8s)
    for _ in range(nboot):
        i4=rng.integers(0,n4,n4); i8=rng.integers(0,n8,n8)
        out.append(one([G4s[j] for j in i4],[Z4s[j] for j in i4],
                       [G8s[j] for j in i8],[Z8s[j] for j in i8]))
    return pt, out

print("\n### MOBIUS LOOP IDENTIFICATION  (c = lambda*kappa ; P = c*G ; A = 1+P)")
print(f"{'band':11}{'|P4|=|kG|':>11}{'|P4| CI':>20}{'arg P4':>9}{'|A4|':>8}{'|A4| CI':>18}{'1/|A4|':>8}{'arg c':>9}")
for lo,hi in [(4,6),(6,9),(6.5,8.5),(9,13),(15,22),(21,22.5),(22,26)]:
    pt,bs=solve(lo,hi)
    c,P4,P8,G4,G8,Z4,Z8=pt
    P4b=np.array([b[1] for b in bs]); A4b=1+P4b
    pci=L.ci(np.abs(P4b)); aci=L.ci(np.abs(A4b))
    print(f"{lo:4.1f}-{hi:4.1f} {abs(P4):11.3f}  [{pci[0]:7.3f},{pci[1]:7.3f}]{np.angle(P4,deg=True):+9.1f}"
          f"{abs(1+P4):8.3f}  [{aci[0]:6.3f},{aci[1]:6.3f}]{1/abs(1+P4):8.2f}{np.angle(c,deg=True):+9.1f}")

pt,bs=solve(6.0,9.0)
c,P4,P8,G4,G8,Z4,Z8=pt
print(f"\n--- 6-9 Hz detail")
print(f"  G4 (4x) = {abs(G4):.4f} at {np.angle(G4,deg=True):+.1f}    Z4 = {abs(Z4):.0f} at {np.angle(Z4,deg=True):+.1f}")
print(f"  G8 (8x) = {abs(G8):.4f} at {np.angle(G8,deg=True):+.1f}    Z8 = {abs(Z8):.0f} at {np.angle(Z8,deg=True):+.1f}")
print(f"  rho=Z4/Z8 = {abs(Z4/Z8):.4f} at {np.angle(Z4/Z8,deg=True):+.1f}")
print(f"  c = lambda*kappa = {abs(c):.3f} at {np.angle(c,deg=True):+.1f} deg")
print(f"     FIRMWARE EXPECTATION: arg(c) = 180 deg (kappa<0, sec 1.6).  Discrepancy = {180-np.angle(c,deg=True):+.1f} deg")
print(f"     ... that lag at 7.5 Hz = {(180-np.angle(c,deg=True))/360/7.5*1000:.1f} ms of actuation delay")
print(f"  P4 = c*G4 = {abs(P4):.3f} at {np.angle(P4,deg=True):+.1f}   A4 = 1+P4 = {abs(1+P4):.3f} at {np.angle(1+P4,deg=True):+.1f}")
print(f"  P8 = c*G8 = {abs(P8):.3f} at {np.angle(P8,deg=True):+.1f}   A8 = 1+P8 = {abs(1+P8):.3f} at {np.angle(1+P8,deg=True):+.1f}")
print(f"  Z0 = Z4*A4 = {abs(Z4*(1+P4)):.0f} at {np.angle(Z4*(1+P4),deg=True):+.1f}   (passive plant, should be same via r95: "
      f"{abs(Z8*(1+P8)):.0f} at {np.angle(Z8*(1+P8),deg=True):+.1f})")
bsA=np.array([1+b[1] for b in bs]); bsc=np.array([b[0] for b in bs])
print(f"  bootstrap: |A4| median {np.median(np.abs(bsA)):.3f}  CI {L.ci(np.abs(bsA)).round(3)}   "
      f"P(|A4|<1) = {(np.abs(bsA)<1).mean():.3f}   P(|P4|>1) = {(np.abs(np.array([b[1] for b in bs]))>1).mean():.3f}")
print(f"  bootstrap: |c| CI {L.ci(np.abs(bsc)).round(2)}  arg(c) CI {L.phase_ci(bsc,np.angle(c,deg=True)).round(1)}")
np.savez('_g2b_kappa.npz', c=c, P4=P4, A4=1+P4, G4=G4, G8=G8, Z4=Z4, Z8=Z8,
         bs_c=bsc, bs_A4=bsA, bs_P4=np.array([b[1] for b in bs]))
