import struct, glob
A="C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
st=open(A+"stock_fw_dump/code.bin","rb").read()
v9=open(glob.glob(A+"_v299_*A16B_plain_image.bin")[0],"rb").read()
v0=open(glob.glob(A+"_v300_*plain_image.bin")[0],"rb").read()
S,E=0x13000,0x100000
u32=lambda b,a:struct.unpack_from("<I",b,a)[0]; u16=lambda b,a:struct.unpack_from("<H",b,a)[0]
R=lambda a,n:set(range(a,a+n))
# my own spans, typed from the census prose (not from the script)
KEEP=R(0x13109,5)|R(0x28F4E,2)|R(0x29A50,4)|{0x29A56}|R(0x29D6A,4)|R(0x29D76,4)|R(0x29EE0,4)|R(0x2A1F0,2)|R(0xC4C00,260)\
 |R(0xC63E8,4)|R(0xC62E6,2)|R(0xC62E4,2)|R(0xE54FC,26)|R(0xC6CD0,2)|R(0xC61B2,4)|R(0xC674E,4)|R(0xC675A,4)|R(0xC6768,6)\
 |R(0xC6598,0x40)|R(0xC63E6,2)|R(0xC61BA,2)|R(0xC62EA,2)|R(0xC61C0,6)|R(0xC64B4,5)|R(0xD7A5C,6)|R(0xD7A6C,6)|{0xC40DC}
Kp=[u32(st,0xCB994+4*k) for k in range(28)]; Kd=[u32(st,0xCB7D4+4*k) for k in range(28)]
KPD=set()
for p in Kp+Kd:
    n=u16(st,p); KPD|=R(p+2+2*n,2*n)
TR={a for a in range(S,E) if (a&0xFFF)>=0xFFC}
dS={a for a in range(S,E) if v0[a]!=st[a]}
orph=sorted(dS-KEEP-KPD-TR)
print("V300 vs stock:",len(dS),"bytes; orphans outside my KEEP/KpKd/trailer spans:",[hex(a) for a in orph])
print(" of which in loose C6598 span only (EME float mirrors):",sorted(hex(a) for a in dS&R(0xC6598,0x40)))
# 'kept' bytes (A-rows) equal V299?
KA=KEEP-{0x1310D}-R(0xC63E6,2)-R(0xC61BA,2)
print("kept A/B1/B2 bytes differing from V299 (expect only 0x1310D):",sorted(hex(a) for a in KEEP if v0[a]!=v9[a]))
print("Kp/Kd Y bytes: V300 uniform 112/48; stock-equal count:",sum(1 for a in KPD if v0[a]==st[a]))
d9={a for a in range(S,E) if v0[a]!=v9[a]}
# removed families by my own list
REM=R(0x14120,1)|R(0x35A08,0x11)|{0xC649B}|{0x3AA96}|R(0xC6446,2)|R(0x454FE,1)|R(0x55C0E,4)|R(0x55DF2,32)|R(0xC40BC,2)|R(0xC40D2,11)|R(0xC4B34,164)|{0xC64DE}\
 |(R(0xCE000,0xDA000-0xCE000)-R(0xD7A5C,6)-R(0xD7A6C,6))|R(0xE4000,0x1000*5)|R(0xE5000,0x0)|TR
EXTRA=KPD|{0x1310D}
o=sorted(d9-REM-EXTRA)
print("V300 vs V299:",len(d9),"bytes; orphans outside my REMOVED/E4-E8/trailer/KpKd spans:",[hex(a) for a in o][:20])
# E4..E8 assist map/LIM diffs: restrict to D9/D10 definition — verify V300==stock there
D=[a for a in d9 if 0xE4000<=a<0xE9000 and a not in KPD and a not in TR]
print("E4-E8 non-KpKd diffs vs V299:",len(D),"; of these V300!=stock:",sum(1 for a in D if v0[a]!=st[a]))
# every non-KEEP non-KpKd non-trailer byte in whole window equals stock
other=[a for a in range(S,E) if a not in KEEP and a not in KPD and a not in TR and v0[a]!=st[a]]
print("non-keep non-KpKd non-trailer bytes != stock:",len(other))
# trailers: touched-page set & untouched pages' trailers == stock
print("trailers differing from stock:",sorted(hex(a&~0xFFF) for a in TR if v0[a]!=st[a] and a%4==0 or (a in TR and a%4==0 and v0[a]!=st[a])))
