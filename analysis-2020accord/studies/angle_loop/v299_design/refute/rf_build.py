"""Build the V299 patch from spec §1.1, verify predicted hashes/CRC. Wall < 2s."""
import hashlib, zlib, glob, time
t0=time.time()
P=glob.glob('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin')[0]
b=bytearray(open(P,'rb').read())
# record V298 originals at each spec'd address
orig={a:bytes(b[a:a+n]) for a,n in [(0xC4C64,2),(0xC4C6A,4),(0xC4C6E,2),(0xC4C70,2),(0xC4C72,2),(0xC4C74,2),(0xC4C76,8),(0x1310D,1)]}
# apply spec §1.1
patch={
 0xC4C64: bytes.fromhex('cd04'),
 0xC4C6A: bytes.fromhex('244f0096'),
 0xC4C6E: bytes.fromhex('0968'),
 0xC4C70: bytes.fromhex('3069'),
 0xC4C72: bytes.fromhex('ae05'),
 0xC4C74: bytes.fromhex('004a'),
 0xC4C76: bytes.fromhex('0000000000000000'),
 0x1310D: bytes.fromhex('42'),
}
diffcount=0
for a,v in patch.items():
    for i,byte in enumerate(v):
        if b[a+i]!=byte: diffcount+=1
    b[a:a+len(v)]=v
print('differing content bytes (excl CRC):',diffcount)
# recompute main block trailer
b0,b1=0x13000,0xC4FFC
newc=zlib.crc32(bytes(b[b0:b1]))&0xFFFFFFFF
old=int.from_bytes(bytes(b[b1:b1+4]),'little')
b[b1:b1+4]=newc.to_bytes(4,'little')
print('block[0x13000,0xC4FFC) trailer old 0x%08X -> new 0x%08X  LE bytes %s'%(old,newc,b[b1:b1+4].hex(' ')))
print('spec says trailer 2d ad cf 2e ->',bytes.fromhex('2dadcf2e')==bytes(b[b1:b1+4]))
print('cave sha',hashlib.sha256(bytes(b[0xC4C00:0xC4D04])).hexdigest())
print('  spec cave 0ea16bdede4e58a538e728685500b5efd43e0c592f7928fa860649e8a990c82b')
print('image sha',hashlib.sha256(bytes(b)).hexdigest())
print('  spec img ac15b53359de2cffd448ba109ec19ec46e5dbd05bf8cd7c62d43d0f8d43160ec')
print('total differing bytes vs V298:', sum(1 for i in range(len(b)) if b[i]!=open(P,'rb').read()[i]) if False else 'see below')
# count total diff
v298=open(P,'rb').read()
print('TOTAL diff bytes vs V298:', sum(1 for i in range(len(b)) if b[i]!=v298[i]))
print('wall %.2fs'%(time.time()-t0))
