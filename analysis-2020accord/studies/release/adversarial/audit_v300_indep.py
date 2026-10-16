import struct, zlib, glob, hashlib, os
R="C:/Users/dudei/Desktop/Projects/accord-firmwares/"
A=R+"analysis-2020accord/"
st=open(A+"stock_fw_dump/code.bin","rb").read()
v9=open(glob.glob(A+"_v299_*A16B_plain_image.bin")[0],"rb").read()
v0=open(glob.glob(A+"_v300_*plain_image.bin")[0],"rb").read()
S,E=0x13000,0x100000
print(len(st),len(v9),len(v0))
for n,b in(("stock",st),("v299",v9),("v300",v0)): print(n,hashlib.sha256(b).hexdigest()[:16], "outside-window-equal-stock", b[:S]==st[:S] and b[E:]==st[E:])
def runs(a,b,gap=0):
    d=[i for i in range(S,E) if a[i]!=b[i]]; out=[]
    for i in d:
        if out and i-out[-1][1]<=gap: out[-1][1]=i+1
        else: out.append([i,i+1])
    return d,out
def u16(b,a): return struct.unpack_from("<H",b,a)[0]
def u32(b,a): return struct.unpack_from("<I",b,a)[0]
# chain walk
sp,np_=struct.unpack_from("<HH",v0,E-8); bs,bl=sp<<12,(np_<<12)-4; blocks=[]
while True:
    blocks.append((bs,bs+bl))
    if bs==S: break
    p,n=struct.unpack_from("<HH",v0,bs-8); bs,bl=p<<12,(n<<12)-4
blocks.sort(); print("blocks",len(blocks), "contig", all(blocks[i][1]+4==blocks[i+1][0] for i in range(len(blocks)-1)), hex(blocks[0][0]), hex(blocks[-1][1]+4))
bad=[(hex(s),hex(e)) for s,e in blocks if zlib.crc32(v0[s:e])&0xffffffff!=u32(v0,e)]
print("CRC bad blocks (v300):",bad)
print("stock bad:",[(hex(s)) for s,e in blocks if zlib.crc32(st[s:e])&0xffffffff!=u32(st,e)], "v299 bad:",[(hex(s)) for s,e in blocks if zlib.crc32(v9[s:e])&0xffffffff!=u32(v9,e)])
# per-4KB-page: which pages differ vs stock and is crc consistent
print("block sizes", sorted({e-s+4 for s,e in blocks}))
dS,rS=runs(v0,st,0); d9,r9=runs(v0,v9,0)
print("v300 vs stock bytes",len(dS),"runs(gap0)",len(rS)); 
tp=lambda a:(a&0xFFF)>=0xFFC
pages=sorted({a>>12 for a in dS}); print("touched pages vs stock",[hex(p) for p in pages])
rg=runs(v0,st,8)[1]
print("RUNS v300 vs stock (merged gap<=8): addr len")
for a,b in rg:
    print(f" 0x{a:05X} +{b-a:<4d} stock={st[a:min(b,a+8)].hex()} v299={v9[a:min(b,a+8)].hex()} v300={v0[a:min(b,a+8)].hex()}")
print("RUNS v300 vs v299 (merged gap<=8)")
rg9=runs(v0,v9,8)[1]
for a,b in rg9:
    print(f" 0x{a:05X} +{b-a:<4d} v299={v9[a:min(b,a+8)].hex()} v300={v0[a:min(b,a+8)].hex()} stock={st[a:min(b,a+8)].hex()}")
open("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/release/adversarial/_v300_runs.txt","w").write("\n".join(f"S {a:X} {b-a}" for a,b in rg)+"\n"+"\n".join(f"9 {a:X} {b-a}" for a,b in rg9))
# page identity
print("pages CE-D9 == stock:", v0[0xCE000:0xDA000]==st[0xCE000:0xDA000])
print("cave C4C00..C4D03 == v299:", v0[0xC4C00:0xC4D04]==v9[0xC4C00:0xC4D04])
print("cave sha",hashlib.sha256(v0[0xC4C00:0xC4D04]).hexdigest()[:16])
# Kp/Kd layout
for nm,tab in(("Kp",0xCB994),("Kd",0xCB7D4)):
    ptr=[u32(v0,tab+4*k) for k in range(28)]
    print(nm,"distinct ptrs",len(set(ptr)),[hex(p) for p in ptr[:3]])
    for k in (0,7):
        p=ptr[k]; n=u16(v0,p); X=[u16(v0,p+2+2*i) for i in range(n)]; Y=[u16(v0,p+2+2*n+2*i) for i in range(n)]
        print(f"  rec{k} @0x{p:X} N={n} X={X} Y={Y} | stock Y={[u16(st,p+2+2*n+2*i) for i in range(n)]} v299 Y={[u16(v9,p+2+2*n+2*i) for i in range(n)]}")
    for img,nmi in((v0,"v300"),(v9,"v299")):
        ys=[]
        for p in ptr:
            n=u16(img,p); ys.append(tuple(u16(img,p+2+2*n+2*i) for i in range(n)))
        print("  ",nmi,"records with all-equal Y:",{y[0] for y in ys if len(set(y))==1}, "count by Y:", {v:sum(1 for y in ys if set(y)=={v}) for v in {y[0] for y in ys if len(set(y))==1}}, "non-flat:",sum(1 for y in ys if len(set(y))>1))
    # X knots and N identical to stock
    print("  N/X same as stock all 28:", all(v0[p:p+2+2*u16(st,p)]==st[p:p+2+2*u16(st,p)] for p in ptr))
    # record byte extent: does anything else of the record differ?
# rwd
import sys
sys.path.insert(0,"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/flashing-2020accord")
import encode_eps as EE
rw=open(glob.glob(R+"flashing-2020accord/rwd/*V300*.rwd")[0],"rb").read()
print("rwd sha",hashlib.sha256(rw).hexdigest()[:16],len(rw))
info=EE.parse_x31(rw); print("headers",[(t,[v.decode('latin1') for v in vv]) for t,vv in info["headers"]]); print("nblocks",len(info["encs"]),[len(x) for x in info["encs"]],"blocks",info["blocks"])
