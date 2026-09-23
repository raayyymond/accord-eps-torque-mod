# Independent gp/tp/abs census scanner for V294 redo (Ghidra-free second method).
import struct, sys
ROOT='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
IM={'stock':ROOT+'stock_fw_dump/code.bin',
    'v293':ROOT+'_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin',
    'v294':ROOT+'_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin'}
def s16(v): return v-0x10000 if v&0x8000 else v
def scan(b, lo=0x13000, hi=0xC0000):
    """yield (addr, len, kind, base_reg, reg2, disp) for every byte offset (even) in code region"""
    out=[]
    for a in range(lo, hi-6, 2):
        h0=b[a]|b[a+1]<<8; h1=b[a+2]|b[a+3]<<8
        reg1=h0&31; op=(h0>>5)&0x3F; reg2=h0>>11
        # 4-byte Format VII loads/stores
        if op in (0x38,0x3A):
            out.append((a,4,'ld.b' if op==0x38 else 'st.b',reg1,reg2,s16(h1)))
        elif op in (0x39,0x3B):
            w=h1&1; k=('ld.' if op==0x39 else 'st.')+('w' if w else 'h')
            out.append((a,4,k,reg1,reg2,s16(h1&0xFFFE)))
        elif op in (0x3C,0x3D) and (h1&1)==1:
            out.append((a,4,'ld.bu',reg1,reg2,s16((h1&0xFFFE)|(op&1))))
        elif op in (0x3E,0x3F) and (h1&1)==1 and reg2!=0:
            out.append((a,4,'ld.hu(op%x)'%op,reg1,reg2,s16(h1&0xFFFE)))
        # 6-byte extended form (Format XIV)
        if (h0&0xFFE0) in (0x0780,0x07A0):
            h2=b[a+4]|b[a+5]<<8
            disp=(s16(h2)<<7)|((h1>>4)&0x7F)
            out.append((a,6,'x6(%04x,%x)'%(h0&0xFFE0,h1&0xF),h0&31,(h1>>11)&31,disp))
    return out
def abs_hits(b,val,lo=0,hi=0x100000):
    pat=struct.pack('<I',val); r=[];i=b.find(pat,lo)
    while i!=-1 and i<hi: r.append(i); i=b.find(pat,i+1)
    return r
def movhi_pairs(b,addr,lo=0x13000,hi=0xC0000):
    hi16=((addr+0x8000)>>16)&0xFFFF; lo16=addr&0xFFFF; r=[]
    for a in range(lo,hi-4,2):
        h0=b[a]|b[a+1]<<8; h1=b[a+2]|b[a+3]<<8
        if ((h0>>5)&0x3F)==0x32 and h1==hi16:  # movhi
            r.append(a)
    return r,hi16,lo16
if __name__=='__main__':
    pass
def branches(b, lo=0x13000, hi=0xC6000):
    """Format V jr/jarl (disp22) and 6-byte jr/jarl disp32; returns (addr, target, kind)"""
    out=[]
    for a in range(lo, hi-6, 2):
        h0=b[a]|b[a+1]<<8; h1=b[a+2]|b[a+3]<<8
        if ((h0>>6)&0x1F)==0x1E and (h1&1)==0:
            d=((h0&0x3F)<<16)|h1
            if d&0x200000: d-=0x400000
            out.append((a,a+d,'jarl' if (h0>>11) else 'jr'))
        if (h0&0xFFE0)==0x02E0:
            d=struct.unpack_from('<i',b,a+2)[0]
            if d%2==0: out.append((a,a+d,'jr32/jarl32 r%d'%(h0&31)))
    return out
