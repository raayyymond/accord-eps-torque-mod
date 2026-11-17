import sys, os, zlib, hashlib, struct, glob
os.environ["ACCORD_FIRMWARE_ROOT"]="C:/Users/dudei/Desktop/Projects/accord-firmwares"
from pathlib import Path
_d=Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
for sub in ("./builds/telemetry","builds","lib","model","verify","extract","builds/a340"):
    sys.path.insert(0,str(_d/sub))
import build_vfourframe_tva as FF
from encode_eps import parse_x31, build_decode_table
FWR=Path("C:/Users/dudei/Desktop/Projects/accord-firmwares")
A=FWR/"analysis-2020accord"
st=(A/"other bins/39990-TVA-A340.bin").read_bytes()
r3=(A/"_v300_a340_REV3_plain_image.bin").read_bytes()
r4=(A/"_v300_a340_REV4_plain_image.bin").read_bytes()
def u16(b,o): return b[o]|b[o+1]<<8
def u32(b,o): return int.from_bytes(b[o:o+4],'little')
def blocks(img):  # own chain walk, no bridge: follow links from END trailer
    END=0x100000; bs=u16(img,END-8)<<12; bl=(u16(img,END-6)<<12)-4; out=[]
    while True:
        out.append((bs,bl))
        if bs==0x13000: break
        nbs=u16(img,bs-8)<<12; nbl=(u16(img,bs-6)<<12)-4
        if nbs==bs or len(out)>100: break
        bs,bl=nbs,nbl
    return out
def crcs(img,tag):
    bl=blocks(img); bad=[(hex(s),hex(l)) for s,l in bl if zlib.crc32(img[s:s+l])&0xffffffff!=u32(img,s+l)]
    print(tag,"blocks",len(bl),"bad",bad); return bl,bad
print("== 3 CRC")
bl4,_=crcs(r4,"REV4"); crcs(st,"STOCK(pos ctl)"); crcs(r3,"REV3")
neg=bytearray(r4); neg[0x50000]^=1; crcs(bytes(neg),"corrupt(neg ctl)")
sys.path.insert(0,str(_d/"lib"))
import verify_bootloader_crc as V
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()):
    w=V.walk(r4); wa=V.walk_all_blocks(r4)
print("kit walkers fails:",w,wa)
print("== 1 reconstruct")
def i16(v): return struct.pack('<h',v)
for o in (0xD7A5C,0xD7A6C): print(hex(o),"stock",struct.unpack('<3h',st[o:o+6]),"rev3",struct.unpack('<3h',r3[o:o+6]),"rev4",struct.unpack('<3h',r4[o:o+6]))
print("C40D4 stock/r3/r4",st[0xC40D4],r3[0xC40D4],r4[0xC40D4]); print("F181",r3[0x13100:0x1310E],r4[0x13100:0x1310E])
rec=bytearray(r3)
rec[0xD7A5C:0xD7A62]=st[0xD7A5C:0xD7A62]; rec[0xD7A6C:0xD7A72]=st[0xD7A6C:0xD7A72]; rec[0xC40D4]=st[0xC40D4]
assert rec[0x1310D]==ord('C'); rec[0x1310D]=ord('D')
for s,l in bl4:
    rec[s+l:s+l+4]=(zlib.crc32(bytes(rec[s:s+l]))&0xffffffff).to_bytes(4,'little')
print("reconstruction == REV4 on disk:",bytes(rec)==r4)
print("== 2 diffs")
print("[0,0x13000) REV4==stock:",r4[:0x13000]==st[:0x13000]," REV3==stock:",r3[:0x13000]==st[:0x13000])
def runs(a,b,lo=0x13000,hi=0x100000):
    out=[];i=lo
    while i<hi:
        if a[i]!=b[i]:
            j=i
            while j<hi and a[j]!=b[j]: j+=1
            out.append((i,j)); i=j
        else: i+=1
    return out
# coalesce gaps<=16 for readability
def coal(rs,g=16):
    o=[]
    for s,e in rs:
        if o and s-o[-1][1]<=g: o[-1]=(o[-1][0],e)
        else: o.append((s,e))
    return o
d43=runs(r4,r3); print("REV4 vs REV3 runs:",[(hex(s),e-s) for s,e in d43])
trail={s+l for s,l in bl4}
for s,e in d43:
    tag="crc-trailer" if any(t<=s<t+4 for t in trail) else ""
    print(hex(s),e-s,r3[s:e].hex(),"->",r4[s:e].hex(),tag)
d4s=runs(r4,st); print("REV4 vs stock: bytes",sum(e-s for s,e in d4s),"runs",len(d4s))
c=coal(d4s); print("coalesced(16)",len(c))
for s,e in c: print(hex(s),hex(e),e-s)
# DampAxis rows equal stock?
print("DampAxis in REV4 == stock:",r4[0xD7A5C:0xD7A62]==st[0xD7A5C:0xD7A62],r4[0xD7A6C:0xD7A72]==st[0xD7A6C:0xD7A72],r4[0xC40D4]==st[0xC40D4])
print("REV3 vs stock bytes",sum(e-s for s,e in runs(r3,st)))
print("== 4 rwd")
dec=build_decode_table(FF.V9B["keys"],FF.V9B["ops"])
src=Path(FF.V38_RWD).read_bytes(); v38=parse_x31(src)["encs"][0]
print("cipher noncircular: V38 rwd decode == V38 plain:",bytes(v38).translate(dec)==Path(FF.V38_PLAIN).read_bytes()[0x13000:0x100000])
for p in sorted(glob.glob(str(FWR/"flashing-2020accord/rwd/*A340*"))):
    d=Path(p).read_bytes(); pi=parse_x31(d)
    pay=bytes(pi["encs"][0]).translate(dec)
    hd={t.decode('latin1'):[v.decode('latin1') for v in vv] for t,vv in pi["headers"]}
    n=Path(p).name[:40]
    print(n,"hdr",hd,"blocks",[(hex(b['start']),hex(b['length'])) for b in pi["blocks"]])
    for nm,img in (("stock",st),("REV4",r4),("V37A4",(A/"_v37a_a340_REV4_plain_image.bin").read_bytes())):
        print("   payload==",nm,pay==img[0x13000:0x100000])
