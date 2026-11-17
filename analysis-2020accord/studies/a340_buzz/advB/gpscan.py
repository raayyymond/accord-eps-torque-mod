import struct,sys
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
def load(n): return open(R+n,'rb').read()
def gpscan(img,off,lo=0x13000,hi=0xC5000):
    """gp-relative accesses with displacement 'off' (negative int). returns (addr,form,hw1,hw2,hw3)"""
    d16=off&0xFFFF; d23=off&0x7FFFFF
    out=[]
    for a in range(lo,hi-4,2):
        h1,h2=struct.unpack_from('<HH',img,a)
        if h1&0x1F!=4: continue
        op=(h1>>5)&0x3F
        if op<0x38: continue
        if (h2&0xFFFE)==(d16&0xFFFE):
            # 4 byte form (disp16 signed) ; 6-byte form has hw3 = high bits
            h3=struct.unpack_from('<H',img,a+4)[0]
            out.append((a,'4B?' ,hex(h1),hex(h2),hex(h3), 'ldst='+hex(op)))
        # 6-byte: hw2 holds disp[15:1]|type? check hw3 
    return out
if __name__=='__main__':
    nm,off=sys.argv[1],int(sys.argv[2],0)
    img=load(nm)
    for r in gpscan(img,off): print(*r)
