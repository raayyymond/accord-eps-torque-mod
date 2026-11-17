import struct,sys
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
OPN={0x38:'ld.b',0x39:'ld.h/w',0x3a:'st.b',0x3b:'st.h/w',0x3c:'ld.bu(e)',0x3d:'ld.bu(o)',0x3e:'ld.hu',0x3f:'ld.hu/mul'}
def scan(img,base,reg,lo=0x13000,hi=0xC5000,imgname=''):
    d=(base)&0xFFFF
    out=[]
    for a in range(lo,hi-4,2):
        h1,h2=struct.unpack_from('<HH',img,a)
        if h1&0x1F!=reg: continue
        op=(h1>>5)&0x3F
        if op<0x38: continue
        if (op in (0x3a,0x38) and h2==d) or (op in (0x3c,) and h2==d) or (op==0x3d and h2==(d|0)) or (op in (0x39,0x3b,0x3e,0x3f) and (h2&0xFFFE)==d and True):
            out.append((hex(a),OPN[op],hex(h1),hex(h2)))
        elif op==0x3d and (h2&0xFFFE)==(d&0xFFFE): out.append((hex(a),OPN[op]+'?',hex(h1),hex(h2)))
    return out
