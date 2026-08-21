"""THE 21.7 Hz VERDICT: phase margin on the sign, and the amplitude criterion, with episode CIs."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)
HO=L.honda_exact(); Df=tuple(L.f32(v) for v in L.design_boost(8.05,0.980,300.0))

def specs(tag,key,ycol=None):
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    return d,eps,L.episode_specs(d['tq'].astype(float),d[key].astype(float),eps,NPER)

print("### A.  arg(Z) at 21.0-22.5 Hz vs the SIGN-FLIP BOUNDARY")
print("    Re(dG.Z) > 0  iff  arg(dG)+arg(Z) in (-90,+90).  arg(dG) = -23.12 deg (design-fixed, a-invariant).")
print("    => FLIPS TO HARMFUL when arg(Z) > +113.12 deg.\n")
argdG=np.angle(-(L.H_biquad(*Df,21.73)-L.H_biquad(*HO,21.73)),deg=True)
print(f"    arg(dG) recomputed = {argdG:+.2f} deg ; flip boundary arg(Z) = {90-argdG:+.2f} deg")
print(f"{'route':7}{'arg(Z)':>9}{'95% CI':>20}{'margin to flip':>16}{'P(flip)':>9}{'coh2':>7}")
for tag in ['r85','r95','r96','r9e']:
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    spz=L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER)
    Z,coh,arr=L.boot_H(spz,f,21.0,22.5,nboot=6000,seed=31)
    az=np.angle(Z,deg=True); pc=L.phase_ci(arr,az)
    ph=az+(np.angle(arr,deg=True)-az+180)%360-180
    pf=(ph>90-argdG).mean()
    print(f"{tag:7}{az:+9.2f}  [{pc[0]:+7.2f},{pc[1]:+7.2f}]{90-argdG-az:+16.2f}{pf:9.3f}{coh:7.3f}")

print("\n### B.  Re(dG.Z) at 21.73 Hz vs at 8.0 Hz  (a = 0.098)")
for fc,zb,lab in [(8.0,(6.0,9.0),'8.00 Hz'),(21.73,(21.0,22.5),'21.73 Hz')]:
    dG=-0.098*(L.H_biquad(*Df,fc)-L.H_biquad(*HO,fc))
    row=[]
    for tag in ['r85','r95','r96','r9e']:
        d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
        spz=L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER)
        Z,coh,arr=L.boot_H(spz,f,*zb,nboot=6000,seed=33)
        v=(dG*Z).real; vci=L.ci((dG*arr).real)
        row.append(f"{tag}:{v:+8.1f} [{vci[0]:+.0f},{vci[1]:+.0f}]")
    print(f"  {lab}:  "+"   ".join(row))

print("\n### C.  AMPLITUDE criterion  |u_new|/|u_old| at 21.73 Hz  (sum routes only: r85 4x, r95 8x)")
print("    u_new/T = (u/T)_measured + dG.  dG scales with a.")
for tag in ['r85','r95']:
    d,eps,sp=specs(tag,'x6b94')
    U,coh,arr=L.boot_H(sp,f,21.0,22.5,nboot=6000,seed=35)
    print(f"  {tag}: u/T = {abs(U):.4f} at {np.angle(U,deg=True):+.1f} deg (coh2 {coh:.3f}, {len(sp)} eps)")
    for a in [0.05,0.098,0.117,0.2,0.3,0.644]:
        dG=-a*(L.H_biquad(*Df,21.73)-L.H_biquad(*HO,21.73))
        r=abs(U+dG)/abs(U); rb=abs(arr+dG)/np.abs(arr); rc=L.ci(rb)
        # full-removal reference
        rrem=abs(U + a*L.H_biquad(*HO,21.73))/abs(U)
        print(f"      a={a:5.3f}  |dG|={abs(dG):.4f}  ratio={r:6.3f}x  CI[{rc[0]:.3f},{rc[1]:.3f}]   (pure full-removal would be {rrem:.3f}x)")

print("\n### D.  CANCELLATION STRUCTURE: is 21.7 Hz also 4:1?")
pool={}
for nm,routes,key in [('SUM',['r85','r95'],'x6b94'),('LANE(6b4c)',['r96','r9e'],'x6b4c')]:
    vals=[]
    for tag in routes:
        d,eps,sp=specs(tag,key); H,_,_=L.boot_H(sp,f,21.0,22.5,nboot=200,seed=1); vals.append(H)
    pool[nm]=np.mean(vals)
for band,lo,hi in [('6-9',6.,9.),('21.0-22.5',21.,22.5)]:
    s=[];l=[]
    for tag in ['r85','r95']:
        d,eps,sp=specs(tag,'x6b94'); s.append(L.band_H(sp,f,lo,hi)[0])
    for tag in ['r96','r9e']:
        d,eps,sp=specs(tag,'x6b4c'); l.append(L.band_H(sp,f,lo,hi)[0])
    S=np.mean(s); La=np.mean(l); R=S-La
    print(f"  {band:11} sum={abs(S):.4f}@{np.angle(S,deg=True):+7.1f}  lane={abs(La):.4f}@{np.angle(La,deg=True):+7.1f}"
          f"  residual={abs(R):.4f}@{np.angle(R,deg=True):+7.1f}   |lane|/|sum|={abs(La)/abs(S):.2f}  "
          f"lane-vs-residual angle={abs(((np.angle(La)-np.angle(R))*180/np.pi+180)%360-180):.1f} deg")
