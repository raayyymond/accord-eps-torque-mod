import os,glob,numpy as np
from scipy import stats
FR=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord'
IMG={'V90':'_v90_*','V91':'_v91_*','V92':'_v92_*','V96':'_v96_*','V100':'_v100_*','V101':'_v101_*',
     'V102':'_v102_*','V103':'_v103_*','V104':'_v104_*','V105':'_v105_*','V106':'_v106_*',
     'V107':'_v107_*','V111':'_v111_*','V112':'_v112_*'}
# route -> (build, small-angle p90, LARGE-angle p90)   [within-drive, from matched test]
RT={'77':('V90',1.703,7.353),'78':('V91',1.067,3.719),'79':('V92',1.116,4.044),
    '7e':('V96',1.383,4.827),'7f':('V96',1.163,4.527),'85':('V100',2.277,6.510),
    '95':('V101',9.388,11.568),'96':('V102',4.554,8.868),'97':('STOCK',1.064,1.551),
    '9e':('V103',5.485,10.293),'a4':('V104',6.533,4.284),'a5':('V105',4.087,7.288),
    'a6':('V106',1.155,6.227),'1e':('V107',7.576,9.017),'21':('V111',1.007,3.137),
    '22':('V112',1.240,2.909),'23':('V112',1.060,8.320)}
CAL={'knee_C40BC':(0xC40BC,2),'K1_C40D2':(0xC40D2,2),'a2_C40DC':(0xC40DC,2),
     'clamp_C407E':(0xC407E,2),'gain_C6CD0':(0xC6CD0,2),'biq_C649B':(0xC649B,1),
     'kd_C6AE6':(0xC6AE6,2)}
def img(b):
    if b=='STOCK':
        for c in ('stock_fw_dump/code.bin','stock_fw_dump/code.bin'):
            p=os.path.join(FR,c)
            if os.path.exists(p): return open(p,'rb').read()
        g=glob.glob(FR+'/**/code.bin',recursive=True)
        return open(g[0],'rb').read() if g else None
    g=[x for x in glob.glob(os.path.join(FR,IMG[b]+'plain_image.bin')) if 'SUPERSEDED' not in x]
    return open(g[0],'rb').read() if g else None
blds={}
for b in ['STOCK']+list(IMG):
    d=img(b)
    if d is None: print('  MISSING image for',b); continue
    v={}
    for n,(a,w) in CAL.items():
        if a+w<=len(d): v[n]=int.from_bytes(d[a:a+w],'little')
    blds[b]=v
print("CAL VALUES PER BUILD (little-endian, image offset == address)\n")
hdr='  %-6s'%'build'+''.join('%12s'%n.split('_')[0] for n in CAL)
print(hdr); print('  '+'-'*(len(hdr)-2))
for b,v in blds.items():
    print('  %-6s'%b+''.join('%12s'%v.get(n,'?') for n in CAL))
rows=[]
for r,(b,lo,hi) in RT.items():
    if b in blds: rows.append((r,b,lo,hi,blds[b]))
print("\n\nNATURAL EXPERIMENT: %d routes across %d builds."%(len(rows),len(set(x[1] for x in rows))))
print("Outcome = log(LARGE-angle 6-9 Hz p90), controlling for log(small-angle p90).\n")
y=np.log([x[3] for x in rows]); x0=np.log([x[2] for x in rows])
b1,b0=np.polyfit(x0,y,1); resid=y-(b0+b1*x0)
print("  control fit: log(hi) = %.3f + %.3f*log(lo)   r = %.3f"%(b0,b1,np.corrcoef(x0,y)[0,1]))
print("  \u21d2 residual = angle-gated excess NOT explained by the drive's baseline level\n")
print("   predictor        n_levels   Spearman rho    p       direction")
for n in CAL:
    vals=np.array([float(x[4].get(n,np.nan)) for x in rows])
    if np.isnan(vals).any(): continue
    k=len(set(vals))
    if k<2: print("   %-16s %5d       --  (constant across all flown builds)"%(n,k)); continue
    rho,p=stats.spearmanr(vals,resid)
    print("   %-16s %5d      %+7.3f   %6.3f    %s"%(n,k,rho,p,'higher cal -> MORE excess' if rho>0 else 'higher cal -> LESS excess'))
g=np.array([x[4]['K1_C40D2']/1024.0*12.0/max(x[4]['knee_C40BC'],1) for x in rows])
rho,p=stats.spearmanr(g,resid)
print("\n   %-16s %5d      %+7.3f   %6.3f    <-- friction small-signal gain (K1/1024)(12/knee)"
      %('fric_gain',len(set(g)),rho,p))
print("\n  per-route residual (positive = worse than its baseline predicts):")
for (r,b,lo,hi,v),e in sorted(zip(rows,resid),key=lambda t:-t[1]):
    print("    r%-4s %-6s  resid %+6.3f   K1=%-5s knee=%-5s a2=%-4s fric_gain=%.5f"
          %(r,b,e,v.get('K1_C40D2'),v.get('knee_C40BC'),v.get('a2_C40DC'),
            v['K1_C40D2']/1024.0*12.0/max(v['knee_C40BC'],1)))
