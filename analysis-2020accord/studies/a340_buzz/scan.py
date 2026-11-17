import struct
F="C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
def load(k):
    return open({'A340':F+"other bins/39990-TVA-A340.bin",'A160':F+"stock_fw_dump/code.bin"}.get(k,k),'rb').read()
TP=0xBF000; GP=0xFEDF8000
OPN={0x38:'ld.b',0x39:'ld.h/w',0x3A:'st.b',0x3B:'st.h/w',0x3C:'ld.bu(6)/st.b(6)/jr',0x3D:'..',0x3E:'ld.hu',0x3F:'ld.hu/mul'}
def scan(d,addr,base_reg=5,base=TP,rng=(0x0,0xC0000)):
    disp=addr-base
    hits=[]
    for i in range(rng[0],rng[1]-6,2):
        h1=struct.unpack_from('<H',d,i)[0]
        if (h1&0x1F)!=base_reg: continue
        op=(h1>>5)&0x3F
        if op<0x38: continue
        h2=struct.unpack_from('<H',d,i+2)[0]
        # 4-byte: disp16 = h2 & ~1 (for ld.h/w, st.h/w, ld.hu) ; byte forms disp16 full h2 (bit0 odd/even via h1 bit5 in ld.bu)
        sd=disp&0xFFFF
        if op in (0x39,0x3B,0x3E,0x3F):
            if (h2&0xFFFE)==(sd&0xFFFE): hits.append((i,hex(h1),hex(h2),'4B',op))
        elif op in (0x38,0x3A):
            if h2==sd: hits.append((i,hex(h1),hex(h2),'4B',op))
        if op in (0x3C,0x3D) and (h2&1)==1 and (h2&0xFFFE)==(sd&0xFFFE) and (op&1)==(sd&1): hits.append((i,hex(h1),hex(h2),'4B ld.bu',op))
        # 6-byte
        if op in (0x3C,0x3D,0x3E,0x3F):
            h3=struct.unpack_from('<H',d,i+4)[0]
            if (h2&0xFFFE)==(sd&0xFFFE) and h3==(disp>>16) and op in (0x3C,0x3D): hits.append((i,hex(h1),hex(h2),hex(h3),'6B',op))
    return hits
if __name__=='__main__':
    import sys
    for k,addrs in (('A340',[0xC40D4,0xC40D2,0xC645A]),('A160',[0xC40DC,0xC40DA,0xC643C])):
        d=load(k)
        for a in addrs:
            print(k,hex(a),scan(d,a))
