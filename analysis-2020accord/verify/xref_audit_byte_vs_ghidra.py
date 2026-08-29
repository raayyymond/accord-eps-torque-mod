# -*- coding: utf-8 -*-
"""Byte-confirm every xref count this session leaned on.

Ghidra reports analyzed:true / 2086 functions, but 0x2A896 has NO function and its `ld.h` was
invisible to search_instructions.  So "analyzed" does not mean complete coverage, and every operand
search in this session may undercount.  Re-derive the counts from raw bytes, both gp-relative
encodings, whole image, and diff against what Ghidra reported.
"""
import io,struct,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
b=io.open('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin','rb').read()
# opcode field (hw1 bits 5-10) -> mnemonic, for base-reg-relative 4-byte forms
OPC={0x38:'ld.b',0x39:'ld.h',0x3A:'ld.w',0x3B:'st.b',0x3C:'ld.bu/st.h',0x3D:'ld.hu/st.h',
     0x3E:'st.w',0x3F:'ld.hu'}
def scan(disp_want, base_reg=4):
    hits=[]
    for o in range(0x13000,0x100000,2):
        hw1=struct.unpack_from('<H',b,o)[0]
        if (hw1&0x1F)!=base_reg: continue
        opc=(hw1>>5)&0x3F
        if opc not in OPC: continue
        if o+4>len(b): break
        hw2=struct.unpack_from('<H',b,o+2)[0]
        for d in ((hw2&0xFFFE),(hw2&0xFFFE)|1):
            dd=d-0x10000 if d>=0x8000 else d
            if dd==disp_want:
                hits.append((o,OPC[opc],(hw1>>11)&0x1F)); break
    for o in range(0x13000,0x100000,2):
        if o+6>len(b): break
        hw1=struct.unpack_from('<H',b,o)[0]
        hw2=struct.unpack_from('<H',b,o+2)[0]
        d=((hw2-0x10000 if hw2>=0x8000 else hw2)<<7)|((hw1>>4)&0x7F)
        if d==disp_want: hits.append((o,'6B-form',(hw1>>11)&0x1F))
    return sorted(set(hits))
CASES=[('gp-0x6bc2  V190 chain', -0x6bc2, {0x36FEA,0x38096}),
       ('gp-0x6ad6  V190 chain', -0x6ad6, {0x38142,0x3A6BA,0x3A798}),
       ('gp-0x6c2e  the 2nd accel EMA', -0x6c2e, {0x343B4,0x34AFE,0x36F3A,0x4185A,0x41AC6}),
       ('gp-0x6b2e  the caught case', -0x6b2e, {0x2A17C,0x2B064}),
       ('gp-0x6b26  CONTROL (inertia)', -0x6b26, {0x36CE4,0x36CF0,0x36D78,0x3815C,0x3AC98})]
print('%-30s %6s %6s  %s'%('cell','ghidra','raw','sites raw found that ghidra MISSED'))
print('-'*96)
bad=[]
for nm,d,gh in CASES:
    h=scan(d)
    raw={o for o,_,_ in h}
    miss=sorted(raw-gh)
    flag=''
    if miss:
        flag=' '.join('0x%05X(%s)'%(o,k) for o,k,_ in h if o in miss)
        bad.append(nm)
    print('%-30s %6d %6d  %s'%(nm,len(gh),len(raw),flag if miss else '-- none --'))
print('')
if bad:
    print('=> %d of %d cells were UNDERCOUNTED by search_instructions:'%(len(bad),len(CASES)))
    for x in bad: print('     '+x)
else:
    print('=> every count byte-confirms.  The V190 chain is COMPLETE as reported.')
