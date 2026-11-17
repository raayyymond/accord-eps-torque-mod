import struct, json, numpy as np, glob, os
from scipy import signal
FW='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
st=open(FW+'other bins/39990-TVA-A340.bin','rb').read()
r3=open(FW+'_v300_a340_REV3_plain_image.bin','rb').read()
r4=open(FW+'_v300_a340_REV4_plain_image.bin','rb').read()
u16=lambda b,a: struct.unpack_from('<H',b,a)[0]; s16=lambda b,a: struct.unpack_from('<h',b,a)[0]; u32=lambda b,a: struct.unpack_from('<I',b,a)[0]
def rec(b,p):
    n=u16(b,p); return [s16(b,p+2+2*i) for i in range(n)],[s16(b,p+2+2*n+2*i) for i in range(n)]
out={}
out['damp']={k:rec(img,u32(img,0xCBE40+4*26)) for k,img in (('stock',st),('rev3',r3),('rev4',r4))}
out['alpha2']={k:img[0xC40D4] for k,img in (('stock',st),('rev3',r3),('rev4',r4))}
for nm,t in (('Kp',0xC77E4),('Kd',0xC7784),('Ki',0xC77B4)):
    out[nm]={k:rec(img,u32(img,t)) for k,img in (('stock',st),('rev4',r4))}
tbl=[];t=0xC4C00+0xDA
while True:
    X,G,S=struct.unpack_from('<HHh',r4,t); tbl.append((X,G,S)); t+=6
    if X==0xFFFF: break
out['cave_tbl']=tbl
out['cells']={hex(a):(u16(st,a),u16(r3,a),u16(r4,a)) for a in (0xC61C0,0xC61C2,0xC61C8,0xC61CC,0xC61CE,0xC63F8,0xC63FA,0xC63FC,0xC63FE,0xC6E88,0xC648A,0xC679E,0xC67AA,0xC67B8)}
out['f181']={k:img[0x13100:0x1310E].decode() for k,img in (('stock',st),('rev3',r3),('rev4',r4))}
d=[i for i in range(0x13000,0x100000) if r4[i]!=st[i]]; d3=[i for i in range(0x13000,0x100000) if r4[i]!=r3[i]]
out['diff']={'vs_stock':len(d),'vs_rev3':len(d3),'vs_rev3_addrs':[hex(i) for i in d3]}
def lane(f,a2,Y):
    z=np.exp(1j*2*np.pi*f/1000)
    a1=37/128; e1=a1/(1-(1-a1)/z)*1024
    diff=(1-1/z)*32
    b=a2/64; e2=b/(1-(1-b)/z)
    return e1*diff*e2/512*Y/64*0x111/(1<<18)
f=np.logspace(0,np.log10(480),120)
out['freq']=f.round(2).tolist()
for k,a2,Y in (('stock_lo',22,-9830),('rev3_lo',14,-29490),('stock_hi',22,-1966),('rev3_hi',14,-16000)):
    H=lane(f,a2,Y)
    out['H_'+k]={'mag':np.abs(H).round(4).tolist(),'ph':np.degrees(np.unwrap(np.angle(-H))).round(1).tolist()}
def s16a(dd,i): return ((dd[:,i].astype(np.int32)<<8)|dd[:,i+1]).astype(np.int16).astype(float)
def tr(cache,seg,t0,t1):
    z=np.load('rlog-tools/_scratch/cache/%s/seg%02d.npz'%(cache,seg)); t=z['t_14a']-z['t_14a'][0]
    m=(t>=t0)&(t<t1); ang=-0.1*s16a(z['d_14a'],0)[m]; rate=-s16a(z['d_14a'],2)[m]
    req=np.interp(z['t_14a'][m],z['t_e4'],(z['d_e4'][:,2]>>7)&1)
    return {'t':(t[m]-t0).round(3).tolist(),'ang':ang.round(1).tolist(),'rate':rate.tolist(),'req':float(req.mean()),'seg':int(seg),'t0':float(t0)}
out['tr_rev3_manual']=tr('a340_user55',22,19.0,23.0)
out['tr_rev3_eng']=tr('a340_user55',7,23.5,27.5)
b,a=signal.butter(2,3/50,'low')
best=None
for p in sorted(glob.glob('rlog-tools/_scratch/cache/a340_user5d/seg*.npz')):
    z=np.load(p); t=z['t_14a']-z['t_14a'][0]; ang=-0.1*s16a(z['d_14a'],0); rate=signal.filtfilt(b,a,-s16a(z['d_14a'],2))
    n=min(len(t),len(ang)); req=np.interp(z['t_14a'],z['t_e4'],(z['d_e4'][:,2]>>7)&1); v=np.interp(z['t_14a'],z['cs'][:,0],z['cs'][:,1])
    for i in range(0,len(t)-500,50):
        s=slice(i,i+500)
        if req[s].max()>0 or v[s].min()<8: continue
        toC=int(((np.sign(ang[s])*np.sign(rate[s])<0)&(abs(rate[s])>5)&(abs(ang[s])<30)).sum())
        if best is None or toC>best[0]: best=(toC,int(os.path.basename(p)[3:5]),float(t[i]))
out['tr_stock_manual']=tr('a340_user5d',best[1],best[2],best[2]+4)
json.dump(out,open('analysis-2020accord/_scratch/out/a340_buzz/page/data.json','w'))
for k in ('damp','alpha2','Kp','Kd','Ki','cave_tbl','cells','f181'): print(k,out[k])
print(out['diff']['vs_stock'],out['diff']['vs_rev3'],out['diff']['vs_rev3_addrs'])
for k in ('tr_rev3_manual','tr_rev3_eng','tr_stock_manual'): print(k,out[k]['seg'],out[k]['t0'],out[k]['req'],len(out[k]['t']),np.ptp(out[k]['rate']), np.round(np.mean(out[k]['ang']),1), np.round(np.ptp(out[k]['ang']),1))
for fq in (10,20,100):
    i=int(np.argmin(abs(f-fq))); print(fq,'Hz rev3/stock lo', round(out['H_rev3_lo']['mag'][i]/out['H_stock_lo']['mag'][i],2), 'hi', round(out['H_rev3_hi']['mag'][i]/out['H_stock_hi']['mag'][i],2), 'phase stock/rev3', out['H_stock_lo']['ph'][i], out['H_rev3_lo']['ph'][i])
