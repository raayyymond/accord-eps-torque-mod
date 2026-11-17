R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
s=open(R+'other bins/39990-TVA-A340.bin','rb').read()
r4=open(R+'_v300_a340_REV4_plain_image.bin','rb').read()
print('d7a5c',s[0xd7a5c:0xd7a62].hex(),r4[0xd7a5c:0xd7a62].hex(),'c40d4',s[0xc40d4],r4[0xc40d4])
print('F181',s[0x13100:0x13110],r4[0x13100:0x13110], s[0x14110:0x14120])
print('0x13109',s[0x13109:0x1310a],r4[0x13109:0x1310a])
# DampAxis ptr table 0xCBE40
import struct
for i in range(0,48):
    p=struct.unpack_from('<I',s,0xCBE40+4*i)[0]; print(i,hex(p),end='; ')
print()
# all diffs list within [0xC0000,0xE4000)
import itertools
d=[i for i in range(0xC0000,0x100000) if s[i]!=r4[i]]
print(len(d))
