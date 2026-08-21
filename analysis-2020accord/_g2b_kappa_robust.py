"""Robustness of the Mobius identification: conditioning, speed-matching, leave-one-episode-out."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)

def win_specs(tag,ykey,vlo=None,vhi=None):
    """per-EPISODE spec sums, optionally restricted to windows whose median speed is in [vlo,vhi)."""
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    tq=d['tq'].astype(float); y=d[ykey].astype(float); w=d['rate_f'].astype(float)*L.DEG2RAD
    v=d['v_rear'].astype(float)
    outG=[];outZ=[];nw=[]
    step=NPER//2; hann=np.hanning(NPER+1)[:NPER]; U=(hann**2).sum()
    tt=np.arange(NPER); A=np.vstack([tt,np.ones(NPER)]).T; pinv=np.linalg.pinv(A)
    for a,b in eps:
        Gxx=Gxy=Gyy=0; Zxx=Zxy=Zyy=0; k=0
        for s in range(a,b-NPER+1,step):
            if vlo is not None:
                mv=np.median(v[s:s+NPER])
                if not (vlo<=mv<vhi): continue
            def dt(z):
                z=z[s:s+NPER]; return z-A@(pinv@z)
            T=np.fft.rfft(dt(tq)*hann); Y=np.fft.rfft(dt(y)*hann); W=np.fft.rfft(dt(w)*hann)
            Gxx=Gxx+(T.conj()*T).real; Gxy=Gxy+T.conj()*Y; Gyy=Gyy+(Y.conj()*Y).real
            Zxx=Zxx+(W.conj()*W).real; Zxy=Zxy+W.conj()*T; Zyy=Zyy+(T.conj()*T).real
            k+=1
        if k>0:
            outG.append((Gxx,Gyy,Gxy,k)); outZ.append((Zxx,Zyy,Zxy,k)); nw.append(k)
    return outG,outZ,nw

def solve_from(G4s,Z4s,G8s,Z8s,lo,hi):
    G4=L.band_H(G4s,f,lo,hi)[0]; Z4=L.band_H(Z4s,f,lo,hi)[0]
    G8=L.band_H(G8s,f,lo,hi)[0]; Z8=L.band_H(Z8s,f,lo,hi)[0]
    rho=Z4/Z8; c=(rho-1)/(G8-rho*G4)
    return c, c*G4, rho, G4, G8, Z4, Z8

print("### CONDITIONING: |rho-1| per band (the solve is ill-posed when rho ~ 1)")
G4s,Z4s,_=win_specs('r85','x6b94'); G8s,Z8s,_=win_specs('r95','x6b94')
print(f"{'band':11}{'|rho-1|':>9}{'|P4|':>8}{'arg c':>9}   note")
for lo,hi in [(2,4),(4,6),(6,9),(9,13),(13,15),(15,22),(21,22.5),(22,26),(26,31)]:
    c,P4,rho,*_=solve_from(G4s,Z4s,G8s,Z8s,lo,hi)
    note = "WELL-POSED" if abs(rho-1)>0.15 else ("marginal" if abs(rho-1)>0.08 else "ILL-POSED (rho~1)")
    print(f"{lo:4.1f}-{hi:4.1f} {abs(rho-1):9.3f}{abs(P4):8.3f}{np.angle(c,deg=True):+9.1f}   {note}")

print("\n### SPEED-MATCHED (windows with median v_rear in the common band only)")
for vlo,vhi in [(0,5),(5,12),(12,20),(0,20),(3,17)]:
    try:
        g4,z4,n4=win_specs('r85','x6b94',vlo,vhi); g8,z8,n8=win_specs('r95','x6b94',vlo,vhi)
        if not g4 or not g8: print(f"  v {vlo}-{vhi} m/s : no windows"); continue
        c,P4,rho,G4,G8,Z4,Z8=solve_from(g4,z4,g8,z8,6.0,9.0)
        print(f"  v {vlo:2d}-{vhi:2d} m/s : wins r85={sum(n4):3d} r95={sum(n8):3d} | G4={abs(G4):.4f}@{np.angle(G4,deg=True):+6.1f} "
              f"G8={abs(G8):.4f}@{np.angle(G8,deg=True):+6.1f} | |rho-1|={abs(rho-1):.3f} | "
              f"|P4|={abs(P4):.3f}@{np.angle(P4,deg=True):+6.1f} |A|={abs(1+P4):.3f} 1/|A|={1/abs(1+P4):.2f} argc={np.angle(c,deg=True):+6.1f}")
    except Exception as e: print(f"  v {vlo}-{vhi}: {e}")

print("\n### LEAVE-ONE-EPISODE-OUT (6-9 Hz)")
for drop4 in range(len(G4s)+1):
    for drop8 in range(len(G8s)+1):
        g4=[x for i,x in enumerate(G4s) if i!=drop4-1]; z4=[x for i,x in enumerate(Z4s) if i!=drop4-1]
        g8=[x for i,x in enumerate(G8s) if i!=drop8-1]; z8=[x for i,x in enumerate(Z8s) if i!=drop8-1]
        if not g4 or not g8: continue
        c,P4,rho,*_=solve_from(g4,z4,g8,z8,6.0,9.0)
        lbl=f"drop r85 ep{drop4-1 if drop4 else '-'}, r95 ep{drop8-1 if drop8 else '-'}"
        print(f"  {lbl:34} |P4|={abs(P4):6.3f} argP={np.angle(P4,deg=True):+7.1f} |A|={abs(1+P4):6.3f} argc={np.angle(c,deg=True):+7.1f}")

print("\n### Z0 (the identified PASSIVE plant) at 6-9 Hz -- the model's free consistency check")
c,P4,rho,G4,G8,Z4,Z8=solve_from(G4s,Z4s,G8s,Z8s,6.0,9.0)
Z0=Z4*(1+P4)
print(f"  Z0 = {abs(Z0):.0f} at {np.angle(Z0,deg=True):+.2f} deg  ->  Re={Z0.real:+.0f}  Im={Z0.imag:+.0f}")
print(f"  Re(Z0)/|Z0| = {Z0.real/abs(Z0):+.4f}   (0 = LOSSLESS SPRING; the solve was free to return anything)")
print(f"  implied stiffness K = |Z0|*w  at 7.5 Hz = {abs(Z0)*2*np.pi*7.5:.0f} counts/rad = {abs(Z0)*2*np.pi*7.5*np.pi/180:.0f} counts/deg")
print(f"  measured Z (closed loop) = {abs(Z4):.0f} at {np.angle(Z4,deg=True):+.1f}  ->  ALL of Re(Z)={Z4.real:.0f} is LOOP-GENERATED")
