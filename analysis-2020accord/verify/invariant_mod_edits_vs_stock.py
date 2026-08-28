import os,glob
FR=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord'
FLOWN=['_v90_','_v91_','_v92_','_v96_','_v100_','_v101_','_v102_','_v103_',
       '_v104_','_v105_','_v106_','_v107_','_v111_','_v112_']
stock=open(glob.glob(FR+'/**/code.bin',recursive=True)[0],'rb').read()
imgs={}
for t in FLOWN:
    f=[x for x in glob.glob(os.path.join(FR,t+'*plain_image.bin')) if 'SUPERSEDED' not in x]
    if f: imgs[t.strip('_').upper()]=open(f[0],'rb').read()
one=next(iter(imgs.values()))
print("agreement with stock per 64 KB block (V90 image, %d B):"%len(one))
BS=0x10000; valid=[]
for b in range(0,min(len(one),len(stock)),BS):
    a=one[b:b+BS]; s=stock[b:b+BS]
    ff=sum(1 for x in a if x==0xFF)/len(a)
    ag=sum(1 for x,y in zip(a,s) if x==y)/len(a)
    tag=''
    if ag>0.9: valid.append(b); tag='  <-- VALID'
    elif ff>0.9: tag='  (blank 0xFF - not in dump extent)'
    print("   0x%06X  agree %.3f   0xFF %.3f%s"%(b,ag,ff,tag))
print("\nvalid blocks: %s"%[hex(v) for v in valid])
lo,hi=min(valid),max(valid)+BS
diff=[]
for i in range(lo,hi):
    s=stock[i]
    if all(v[i]!=s for v in imgs.values()) and len(set(v[i] for v in imgs.values()))==1:
        diff.append((i,s,one[i]))
runs=[]
for a,s,m in diff:
    if runs and a==runs[-1][-1][0]+1: runs[-1].append((a,s,m))
    else: runs.append([(a,s,m)])
print("\n\U0001f6d1 INVARIANT MOD EDITS \u2014 differ from stock, IDENTICAL across all %d flown builds"%len(imgs))
print("   (perfectly confounded with 'is it a mod' \u21d2 the only remaining candidates for a")
print("    cause common to every mod and absent from stock)\n")
print("   %d bytes in %d runs, valid region 0x%05X-0x%05X\n"%(len(diff),len(runs),lo,hi))
for r in runs:
    a0=r[0][0]; sb=''.join('%02x'%x[1] for x in r); mb=''.join('%02x'%x[2] for x in r)
    reg='CAL' if 0xC0000<=a0<0xC8000 else 'CODE'
    ex=''
    if len(r)==2: ex='  stock=%-6d mod=%-6d'%(int.from_bytes(bytes(x[1] for x in r),'little'),
                                              int.from_bytes(bytes(x[2] for x in r),'little'))
    print("   0x%05X  %-4s %2dB  %-16s -> %-16s%s"%(a0,reg,len(r),sb,mb,ex))
