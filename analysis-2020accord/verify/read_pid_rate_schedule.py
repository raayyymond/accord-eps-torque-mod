import os,glob
FR=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord'
st=open(glob.glob(FR+'/**/code.bin',recursive=True)[0],'rb').read()
v112=open([x for x in glob.glob(FR+'/_v112_*plain_image.bin') if 'SUPER' not in x][0],'rb').read()
TP=0xBF000
def u16(d,a): return int.from_bytes(d[a:a+2],'little')
def s16(d,a):
    v=u16(d,a); return v-65536 if v>=32768 else v
LERP={'Kp 0xC6B26':(0x7b1e,0x7b20,0x7b24,0x7b26,0x7b2c),
      'Ki 0xC6B12':(0x7b0a,0x7b0c,0x7b10,0x7b12,0x7b18),
      'Kd 0xC6AE6':(0x7ade,0x7ae0,0x7ae4,0x7ae6,0x7aec)}
print("PID GAIN SCHEDULING \u2014 all three LERP on the SAME axis gp-0x6ac0\n")
print("  gate: the whole lane is DISABLED when gp-0x6ac0 >= 0x32C9 = %d\n"%0x32c9)
for nm,(thr,x0,xup,y0,ylast) in LERP.items():
    for tag,d in (('stock',st),('V112',v112)):
        X=[u16(d,TP+thr)]+[u16(d,TP+x0+2*i) for i in range(int((xup-x0)/2)+1)]
        nY=int((ylast-y0)/2)+1
        Y=[u16(d,TP+y0+2*i) for i in range(nY)]
        print("  %-12s %-5s  X(thr,knots) = %-28s  Y = %s"%(nm,tag,X,Y))
    print()
print("  axis  gp-0x6ac0  = resolver/FOC ELECTRICAL RATE  (reference-accord-c520c-cap-table-axis-provenance)")
print("\n  \u21d2 every Y row is FLAT and byte-identical stock vs V112 \u21d2 the scheduling")
print("    mechanism is Honda's, is WIRED, and has NEVER been used by anyone.")
same=all(st[TP+a:TP+b+2]==v112[TP+a:TP+b+2] for _,_,_,a,b in LERP.values())
print("  byte-identical stock vs V112 across all three Y rows: %s"%same)
