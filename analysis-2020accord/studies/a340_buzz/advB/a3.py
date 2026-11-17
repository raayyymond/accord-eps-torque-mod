import struct
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
s=open(R+'other bins/39990-TVA-A340.bin','rb').read()
r=open(R+'_v300_a340_REV4_plain_image.bin','rb').read()
d=[i for i in range(0xC5000,0xE4000) if s[i]!=r[i]]
# group
g=[];
for i in d:
    if g and i-g[-1][1]<=1: g[-1][1]=i
    else: g.append([i,i])
for a,b in g:
    a0=a&~1; b0=b|1
    print(hex(a0),'stock',s[a0:b0+1].hex(),'rev4',r[a0:b0+1].hex())
# raw LE32 scan for records region and pointer refs
for a in range(0x13000,0xC0000,2):
    v=struct.unpack_from('<I',s,a)[0]
    if 0xE4600<=v<0xE5E00: print('LE32 ref',hex(a),hex(v))
