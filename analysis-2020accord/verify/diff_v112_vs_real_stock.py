import struct, glob, os
FR=r'C:\Users\dudei\Desktop\Projects\accord-firmwares'
stock=os.path.join(FR,'analysis-2020accord','stock_fw_dump','code.bin')
v112=[x for x in glob.glob(os.path.join(FR,'analysis-2020accord','*plain_image.bin')) if 'v112' in os.path.basename(x).lower()][0]
a=open(stock,'rb').read(); b=open(v112,'rb').read()
print("STOCK: %s  (%d bytes)"%(stock,len(a)))
print("V112 : %s  (%d bytes)\n"%(os.path.basename(v112),len(b)))
s16=lambda buf,x: struct.unpack_from('<h',buf,x)[0]
u32=lambda buf,x: struct.unpack_from('<I',buf,x)[0]
# resolve the LIVE records through the factor pointer arrays for this car (TVCA4 -> idx 24/26/27)
ARR={'FactorB':0xC9CCC,'FactorC':0xC9E9C,'FactorD':0xC9DB4,'FactorE':0xC9F84}
print("LIVE FACTOR RECORDS for indices 24 / 26 / 27  (X and Y knots, STOCK -> V112)")
for nm,arr in ARR.items():
    for idx in (24,26,27):
        pa=u32(a,arr+4*idx); pb=u32(b,arr+4*idx)
        if pa!=pb: print("  %s[%d] POINTER MOVED 0x%05X -> 0x%05X"%(nm,idx,pa,pb)); continue
        if not (0xC0000<=pa<0x100000): continue
        X=[(s16(a,pa+2+2*k),s16(b,pa+2+2*k)) for k in range(4)]
        Y=[(s16(a,pa+10+2*k),s16(b,pa+10+2*k)) for k in range(4)]
        ch = any(x!=y for x,y in X+Y)
        if not ch: continue
        print("  %s[%2d] @0x%05X"%(nm,idx,pa))
        print("      X stock %s" % [x[0] for x in X], " -> V112", [x[1] for x in X])
        print("      Y stock %s" % [y[0] for y in Y], " -> V112", [y[1] for y in Y])
print("\nFULL DIFF vs REAL STOCK, main cal block only (0xC4000-0xC8000):")
diff=[i for i in range(0xC4000,0xC8000) if a[i]!=b[i]]
runs=[]
for i in diff:
    if runs and i==runs[-1][1]: runs[-1][1]=i+1
    else: runs.append([i,i+1])
for lo,hi in runs:
    if hi-lo==2:
        print("   0x%05X  u16 %6d -> %6d"%(lo,struct.unpack_from('<H',a,lo)[0],struct.unpack_from('<H',b,lo)[0]))
    else:
        print("   0x%05X  %3d B  %s -> %s"%(lo,hi-lo,bytes(a[lo:hi]).hex()[:28],bytes(b[lo:hi]).hex()[:28]))
print("   (%d runs in the main cal block)"%len(runs))
