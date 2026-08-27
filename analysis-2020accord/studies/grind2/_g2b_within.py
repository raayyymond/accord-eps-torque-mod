"""Can the loop be identified WITHIN one drive, from the |T| operating-point ladder?
   (decides whether repointing 427->gp-0x6b94 on V104 alone would bound |kG|)"""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)

def strat(tag,ykey,edges):
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    tq=d['tq'].astype(float); y=d[ykey].astype(float); w=d['rate_f'].astype(float)*L.DEG2RAD
    hann=np.hanning(NPER+1)[:NPER]; step=NPER//2
    tt=np.arange(NPER); A=np.vstack([tt,np.ones(NPER)]).T; pv=np.linalg.pinv(A)
    out={i:{'G':[],'Z':[],'n':0} for i in range(len(edges)-1)}
    for a,b in eps:
        for s in range(a,b-NPER+1,step):
            m=np.percentile(np.abs(tq[s:s+NPER]),75)
            k=np.searchsorted(edges,m)-1
            if k<0 or k>=len(edges)-1: continue
            def dt(z): z=z[s:s+NPER]; return z-A@(pv@z)
            T=np.fft.rfft(dt(tq)*hann); Y=np.fft.rfft(dt(y)*hann); W=np.fft.rfft(dt(w)*hann)
            out[k]['G'].append(((T.conj()*T).real,(Y.conj()*Y).real,T.conj()*Y,1))
            out[k]['Z'].append(((W.conj()*W).real,(T.conj()*T).real,W.conj()*T,1))
            out[k]['n']+=1
    return out

EDG=[0,300,700,1200,2000,20000]
print("### WITHIN-DRIVE |T| ladder (window p75 of |tq|), 6-9 Hz, sum-packing routes")
for tag in ['r85','r95']:
    st=strat(tag,'x6b94',EDG)
    print(f"  --- {tag}")
    res=[]
    for k in sorted(st):
        if st[k]['n']<4: print(f"     bin {EDG[k]:5.0f}-{EDG[k+1]:5.0f}: n={st[k]['n']:3d}  (too few)"); continue
        G=L.band_H(st[k]['G'],f,6,9)[0]; Z=L.band_H(st[k]['Z'],f,6,9)[0]
        print(f"     bin {EDG[k]:5.0f}-{EDG[k+1]:5.0f}: n={st[k]['n']:3d}  G={abs(G):.4f}@{np.angle(G,deg=True):+6.1f}   Z={abs(Z):5.0f}@{np.angle(Z,deg=True):+6.1f}")
        res.append((G,Z))
    for i in range(len(res)):
        for j in range(i+1,len(res)):
            Gi,Zi=res[i]; Gj,Zj=res[j]; rho=Zi/Zj
            if abs(rho-1)<0.05: note=" ILL-POSED"; 
            else: note=""
            c=(rho-1)/(Gj-rho*Gi); P=c*Gi
            print(f"       pair {i}x{j}: |rho-1|={abs(rho-1):.3f}  c={abs(c):6.2f}@{np.angle(c,deg=True):+7.1f}  "
                  f"|P|={abs(P):.3f}@{np.angle(P,deg=True)%360:+7.1f}  |1+P|={abs(1+P):.3f}{note}")

print("\n### CROSS-BUILD reference for comparison: |c|=13.09@+145.3, |P|=0.630, |1+P|=0.440")
print("\n### EPISODE-COUNT REQUIREMENT: how the CI on |A| narrows with episodes (resample r85's 2 + r95's 3)")
def sp(tag,ykey):
    d=L.load(tag); eps=L.episodes(d['cc_lat']>0.5)
    return (L.episode_specs(d['tq'].astype(float),d[ykey].astype(float),eps,NPER),
            L.episode_specs(d['rate_f'].astype(float)*L.DEG2RAD,d['tq'].astype(float),eps,NPER),eps)
G4s,Z4s,e4=sp('r85','x6b94'); G8s,Z8s,e8=sp('r95','x6b94')
print(f"  r85 episode lengths (s): {[round((b-a)/L.FS,1) for a,b in e4]}")
print(f"  r95 episode lengths (s): {[round((b-a)/L.FS,1) for a,b in e8]}")
print(f"  current |A| CI half-width / point = {(0.662-0.106)/2/0.440:.2f}  (i.e. +-63% of the estimate)")
for n in [2,4,6,8,12]:
    print(f"  n_ep={n:2d}: CI half-width scales ~1/sqrt(n) => ~{(0.662-0.106)/2/0.440*np.sqrt(2/n)*100:.0f}% of the estimate")
