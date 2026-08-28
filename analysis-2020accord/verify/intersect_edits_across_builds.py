import glob, os, struct
FR=r'C:\Users\dudei\Desktop\Projects\accord-firmwares'
stock=open(os.path.join(FR,'analysis-2020accord','stock_fw_dump','code.bin'),'rb').read()
def img(tag):
    f=[x for x in glob.glob(os.path.join(FR,'analysis-2020accord','*plain_image.bin'))
       if ('_%s_'%tag) in os.path.basename(x).lower()]
    return (os.path.basename(f[0]),open(f[0],'rb').read()) if f else (None,None)
# builds whose routes ALL show the 7-9 Hz excess
TAGS=['v90','v91','v92','v96','v100','v102','v112']
CRC={0xC4FFC,0xC5FFC,0xC6FFC,0xC7FFC}|{0xC0000+0x1000*k+0xFFC for k in range(0,32)}
sets={}
for t in TAGS:
    nm,b=img(t)
    if b is None: print("  %-5s NOT FOUND"%t); continue
    d=set()
    for i in range(0x13000,0x100000):
        if stock[i]!=b[i]:
            if any(tr<=i<tr+4 for tr in CRC): continue
            d.add(i)
    sets[t]=d
    print("  %-5s %-58s %6d differing bytes (non-CRC)"%(t,nm[:58],len(d)))
common=None
for t,d in sets.items():
    common = d if common is None else (common & d)
print("\n  INTERSECTION -- bytes changed vs stock in EVERY one of these builds: %d"%len(common))
runs=[]
for i in sorted(common):
    if runs and i==runs[-1][1]: runs[-1][1]=i+1
    else: runs.append([i,i+1])
nm,v112=img('v112')
print("\n  addr range        len   stock -> V112            note")
for lo,hi in runs:
    note="** CODE **" if lo<0xC0000 else ""
    if hi-lo==2 and lo>=0xC0000:
        print("   0x%05X..0x%05X %3d   u16 %6d -> %6d   %s"%(lo,hi-1,hi-lo,
              struct.unpack_from('<H',stock,lo)[0],struct.unpack_from('<H',v112,lo)[0],note))
    else:
        print("   0x%05X..0x%05X %3d   %-22s -> %-22s %s"%(lo,hi-1,hi-lo,
              bytes(stock[lo:hi]).hex()[:22],bytes(v112[lo:hi]).hex()[:22],note))
print("\n  => %d runs are present in EVERY build that shows the 7-9 Hz excess."%len(runs))
