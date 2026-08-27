"""Sub-band phase progression (Nyquist), and the ENGAGEMENT TRANSIENT from the frozen state."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS); HO=L.honda_exact(); a=0.098
K=np.load('_scratch/data/_g2b_kappa.npz'); c=complex(K['c']); P0=complex(K['P4'])

def sp(tag,ykey):
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    return (L.episode_specs(d['tq'].astype(float),d[ykey].astype(float),eps,NPER),
            L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER))
G4s,Z4s=sp('r85','x6b94'); G8s,Z8s=sp('r95','x6b94')

print("### NYQUIST: sub-band phase progression of P = c*G  (does the locus cross the -1 axis above |P|=1?)")
Df=[L.f32(v) for v in L.design_boost(8.05,0.980,300.0)]
print(f"{'band':10}{'|rho-1|':>9}{'|c|':>8}{'arg c':>8}{'|P|':>7}{'arg P':>8}{'|1+P|':>8}  ->BOOSTED:{'|P_n|':>8}{'argP_n':>9}{'|1+P_n|':>9}")
for lo,hi in [(5.5,6.5),(6.0,7.0),(6.5,7.5),(7.0,8.0),(7.5,8.5),(8.0,9.0),(8.5,9.5),(6.0,9.0)]:
    G4=L.band_H(G4s,f,lo,hi)[0]; Z4=L.band_H(Z4s,f,lo,hi)[0]
    G8=L.band_H(G8s,f,lo,hi)[0]; Z8=L.band_H(Z8s,f,lo,hi)[0]
    rho=Z4/Z8; cc=(rho-1)/(G8-rho*G4); P=cc*G4
    fc=0.5*(lo+hi); dG=-a*(L.H_biquad(*Df,fc)-L.H_biquad(*HO,fc)); Pn=P+cc*dG
    print(f"{lo:4.1f}-{hi:4.1f}{abs(rho-1):9.3f}{abs(cc):8.2f}{np.angle(cc,deg=True):+8.1f}{abs(P):7.3f}"
          f"{np.angle(P,deg=True)%360:+8.1f}{abs(1+P):8.3f}          {abs(Pn):8.3f}{np.angle(Pn,deg=True)%360:+9.1f}{abs(1+Pn):9.3f}")

print("\n### ENGAGEMENT TRANSIENT from the FROZEN state (arm-gated filter, states freeze while disarmed)")
def free_resp(a1,a2,b1,w1,w2,n=600):
    """zero-input response of  w[n] = -a1 w[n-1] - a2 w[n-2],  y[n] = w[n] + b1 w[n-1] + w[n-2]"""
    W=[w2,w1]; Y=[]
    for k in range(n):
        wn=-a1*W[-1]-a2*W[-2]
        Y.append(wn+b1*W[-1]+W[-2]); W.append(wn)
    return np.array(Y)

for name,(a1,a2,b1,g),wmaxfac in [('HONDA (shipped)',HO,8.97),('BOOST r=0.980',tuple(Df),0.544),
                                  ('BOOST r=0.990',tuple(L.f32(v) for v in L.design_boost(8.05,0.990,300.0)),0.994)]:
    xp99=1244.0; wmax=wmaxfac*xp99
    best=0; bestph=0
    for ph in np.linspace(0,2*np.pi,721):
        y=free_resp(a1,a2,b1,wmax*np.cos(ph),wmax*np.cos(ph-2*np.pi*8.05/1000))
        if np.abs(y).max()>best: best=np.abs(y).max(); bestph=ph
    y=free_resp(a1,a2,b1,wmax*np.cos(bestph),wmax*np.cos(bestph-2*np.pi*8.05/1000))
    tau=-1.0/np.log(np.sqrt(a2))       # ticks
    n5=int(np.ceil(3*tau))
    env=np.abs(y); k95=np.argmax(np.cumsum(env)>0.95*env.sum())
    print(f"  {name:16} state ceiling |w|<= {wmax:8.0f} ct  |  worst free-response peak |y| = {best:8.0f} ct"
          f"  |  tau = {tau:6.1f} ms  |  3tau = {3*tau:6.1f} ms  |  95% of |y| energy by {k95:4d} ms"
          f"  |  cycles of ring at 8 Hz = {3*tau*8.05/1000:.2f}")
print("  (transient <= 2x this if the stale state and the correct state are anti-phase)")
print(f"  aggregator sum clamp = +-10240 ct ; gp-0x6b86 lane clamp = +-12288 ct")

print("\n### FILTER POLE Q (is +3.23 dB 'another resonance'?)")
for name,(a1,a2,b1,g) in [('HONDA',HO),('BOOST r=0.980',tuple(Df)),('BOOST r=0.990',tuple(L.f32(v) for v in L.design_boost(8.05,0.990,300.0)))]:
    p=np.roots([1,a1,a2]); r=abs(p[0]); th=abs(np.angle(p[0]))
    s=complex(np.log(r),th); zeta=-s.real/abs(s); Q=1/(2*zeta)
    print(f"  {name:14} |pole|={r:.6f} @ {th/(2*np.pi)*1000:7.3f} Hz   zeta={zeta:.4f}   Q={Q:.3f}")
print("  measured MECHANICAL mode (record): Q = 10.21 (zeta = 0.049) at ~8.1 Hz")
