import sys, os, struct, re
os.environ["ACCORD_FIRMWARE_ROOT"]="C:/Users/dudei/Desktop/Projects/accord-firmwares"
SRC="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/builds/v108_plus/build_v300_tva.py"
src=open(SRC,encoding="utf-8").read()
# hook: mutate right after APPLY (before CRC recompute, so CRC cannot catch it)
hook='    code[0x1310D:0x1310E] = RELEASE_LETTER\n'
assert src.count(hook)==1
src=src.replace(hook,hook+'    MUT(code, kp_y, kd_y, v299, KP, KD)\n')
src=src.replace('if __name__ == "__main__":\n    main()','')
src=src.replace('__file__','SRC_FILE')
g={"__name__":"v300mut","SRC_FILE":SRC,"MUT":None}
exec(compile(src,SRC,"exec"),g)
def u16(b,a): return struct.unpack_from("<H",b,a)[0]
def flip(a): 
    def f(c,kp,kd,v9,KP,KD): c[a]^=1
    return f
def setb(a,v):
    def f(c,kp,kd,v9,KP,KD): c[a]=v
    return f
MUTS={
 "m01 cave byte 0xC4C50^1":flip(0xC4C50),
 "m02 Kp rec12 Y[2]+1":lambda c,kp,kd,v9,KP,KD: struct.pack_into("<H",c,kp[12][0]+4,113),
 "m03 Kd rec20 Y[0]=0 (V299 leftover)":lambda c,kp,kd,v9,KP,KD: struct.pack_into("<H",c,kd[20][0],0),
 "m04 stray byte 0x20000^1":flip(0x20000),
 "m05 Kp rec5 padding after Y span ^1":lambda c,kp,kd,v9,KP,KD: c.__setitem__(KP[5]+22,c[KP[5]+22]^1),
 "m06 A7 EME int 0xC674E^1":flip(0xC674E),
 "m07 restore telemetry hook 0x55C0E from V299":lambda c,kp,kd,v9,KP,KD: c.__setitem__(slice(0x55C0E,0x55C12),v9[0x55C0E:0x55C12]),
 "m08 Ki 0xC63E6=41":lambda c,kp,kd,v9,KP,KD: c.__setitem__(0xC63E6,41),
 "m09 base-assist page byte 0xCE100^1":flip(0xCE100),
 "m10 Kp rec12 X knot[1]+1":lambda c,kp,kd,v9,KP,KD: c.__setitem__(KP[12]+4,c[KP[12]+4]+1),
 "m11 F181 first byte 0x13100^1":flip(0x13100),
 "m12 Kp rec9 all Y=960 (V299 leftover)":lambda c,kp,kd,v9,KP,KD: [struct.pack_into("<H",c,kp[9][0]+2*i,960) for i in range(kp[9][1])],
 "m13 hand-freeze imm 0xC4C64 = 1230":lambda c,kp,kd,v9,KP,KD: struct.pack_into("<H",c,0xC4C64,1230),
 "m14 D6 DTC gate 0xC64B8=0xFE":setb(0xC64B8,0xFE),
 "m15 Kp rec0 Y -> 112 but Kp rec1 Y[4]=111":lambda c,kp,kd,v9,KP,KD: struct.pack_into("<H",c,kp[1][0]+8,111),
 "m16 Kd rec27 N header 4->5 (layout corruption)":lambda c,kp,kd,v9,KP,KD: struct.pack_into("<H",c,KD[27],5),
 "m17 flip kept DampAxis byte 0xD7A5C^1":flip(0xD7A5C),
 "m18 flip kept DampAxis byte 0xD7A71^1":flip(0xD7A71),
 "m19 flip kept 0xC40DC (14->15)":flip(0xC40DC),
 "m20 swap the two Y rows D7A5C<->D7A6C":lambda c,kp,kd,v9,KP,KD: (lambda a,b:(c.__setitem__(slice(0xD7A5C,0xD7A62),b),c.__setitem__(slice(0xD7A6C,0xD7A72),a)))(bytes(c[0xD7A5C:0xD7A62]),bytes(c[0xD7A6C:0xD7A72])),
 "m21 swap words within row D7A5C (ce8c<->cebc)":lambda c,kp,kd,v9,KP,KD: c.__setitem__(slice(0xD7A5C,0xD7A62),bytes(c[0xD7A60:0xD7A62])+bytes(c[0xD7A5E:0xD7A60])+bytes(c[0xD7A5C:0xD7A5E])),
 "m22 revert row 0xD7A6C to stock (rev-1 state)":lambda c,kp,kd,v9,KP,KD: c.__setitem__(slice(0xD7A6C,0xD7A72),bytes.fromhex("9ad99ae952f8")),
 "m23 flip other page-0xD7 byte 0xD7A80^1":flip(0xD7A80),
}
sel=sys.argv[1:]
for name,f in MUTS.items():
    if sel and name[:3] not in sel: continue
    g["MUT"]=f
    R=g["Run"](quiet=True,collect=True)
    try:
        g["build"](quiet=True,do_rwd=False,run=R)
        res="SILENT PASS" if not R.failures else f"CAUGHT by {len(R.failures)}: "+"; ".join(m[:70] for k,m in R.failures[:2])
    except SystemExit as e: res="CAUGHT(exit) "+str(e)[:90]
    except Exception as e: res="CAUGHT(exception) "+repr(e)[:100]
    print(f"{name:52s} -> {res}",flush=True)
