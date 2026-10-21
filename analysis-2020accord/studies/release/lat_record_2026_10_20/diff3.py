import glob,hashlib,struct
R="C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
f=lambda p: open(glob.glob(R+p)[0],'rb').read()
v298=f("_v298_*plain_image.bin");v299=f("_v299_*plain_image.bin");v300=f("_v300_*plain_image.bin")
import os
st=open(glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/**/*stock*plain*.bin",recursive=True)[0] if glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/**/*stock*plain*.bin",recursive=True) else R+"x",'rb').read() if glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/**/*stock*plain*.bin",recursive=True) else None
for n,b in [("v298",v298),("v299",v299),("v300",v300)]: print(n,hashlib.sha256(b).hexdigest()[:16],len(b))
def runs(a,b,lo=0x13000,hi=0x100000):
    d=[i for i in range(lo,min(hi,len(a))) if a[i]!=b[i]]
    out=[];s=None;p=None
    for i in d:
        if s is None: s=p=i
        elif i-p<=3: p=i
        else: out.append((s,p));s=p=i
    if s is not None: out.append((s,p))
    return d,out
def page(a): return a>>12
for nm,a,b in [("V298->V299",v298,v299),("V299->V300",v299,v300),("V298->V300",v298,v300)]:
    d,o=runs(a,b); print("\n==",nm,len(d),"bytes",len(o),"runs")
    # summarize by page
    from collections import Counter
    c=Counter(page(i) for i in d)
    print(" pages:",{hex(k<<12):v for k,v in sorted(c.items())})
    for s,e in o:
        if (s>>12) in (0xCE,0xCF,0xD0,0xD1,0xD2,0xD3,0xD4,0xD5,0xD6,0xD8,0xD9) : continue
        if e-s>40: print(f"  {s:#07x}-{e:#07x} ({e-s+1}B) [long]"); continue
        print(f"  {s:#07x}-{e:#07x} old={a[s:e+1].hex()} new={b[s:e+1].hex()}")
