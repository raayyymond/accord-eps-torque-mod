import struct, glob, os
FR=r'C:\Users\dudei\Desktop\Projects\accord-firmwares'
def get(pat):
    g=[p for p in glob.glob(os.path.join(FR,'analysis-2020accord','*plain_image.bin')) if pat in os.path.basename(p).lower()]
    return g[0] if g else None
stock=get('stock'); v112=get('v112')
print("stock:",os.path.basename(stock)); print("v112 :",os.path.basename(v112))
a=open(stock,'rb').read(); b=open(v112,'rb').read()
CRC_TRAILERS={0xC4FFC,0xC5FFC,0xC6FFC,0xC7FFC,0xCCFFC,0xCDFFC,0xCEFFC,0xCFFFC,
              0xD0FFC,0xD1FFC,0xD2FFC,0xD3FFC,0xD4FFC,0xD5FFC,0xD6FFC,0xD7FFC,
              0xD8FFC,0xD9FFC,0xDAFFC,0xDBFFC,0xDCFFC,0xDDFFC,0xDEFFC,0xDFFFC}
diff=[i for i in range(0x13000,0x100000) if a[i]!=b[i]]
runs=[]
for i in diff:
    if runs and i==runs[-1][1]: runs[-1][1]=i+1
    else: runs.append([i,i+1])
print("\n%d differing bytes in %d runs (V112 vs STOCK, whole flashable region)"%(len(diff),len(runs)))
print("\n  addr range          len  stock -> v112                       note")
CODE=lambda lo: lo<0xC0000
for lo,hi in runs:
    if any(lo<=t+3 and hi>t for t in CRC_TRAILERS): note="CRC trailer"
    elif CODE(lo): note="** CODE **"
    else: note=""
    sa=bytes(a[lo:hi]).hex(); sb=bytes(b[lo:hi]).hex()
    if hi-lo<=12:
        print("  0x%05X..0x%05X %4d  %-22s -> %-22s %s"%(lo,hi-1,hi-lo,sa,sb,note))
    else:
        print("  0x%05X..0x%05X %4d  %-22s -> %-22s %s"%(lo,hi-1,hi-lo,sa[:20]+"..",sb[:20]+"..",note))
print("\nNON-CRC, NON-CODE cal runs (the actual calibration edits):")
n=0
for lo,hi in runs:
    if any(lo<=t+3 and hi>t for t in CRC_TRAILERS) or CODE(lo): continue
    n+=1
    if hi-lo==2:
        print("   0x%05X  u16 %6d -> %6d   (x%.3f)"%(lo,struct.unpack_from('<H',a,lo)[0],
              struct.unpack_from('<H',b,lo)[0],
              struct.unpack_from('<H',b,lo)[0]/max(struct.unpack_from('<H',a,lo)[0],1e-9)))
    else:
        print("   0x%05X  %d bytes  %s -> %s"%(lo,hi-lo,bytes(a[lo:hi]).hex(),bytes(b[lo:hi]).hex()))
print("   => %d calibration runs"%n)
