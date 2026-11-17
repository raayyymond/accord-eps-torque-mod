import struct
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
s=open(R+'other bins/39990-TVA-A340.bin','rb').read()
r=open(R+'_v300_a340_REV4_plain_image.bin','rb').read()
u32=lambda b,a:struct.unpack_from('<I',b,a)[0]
def rec(b,p):
    n=struct.unpack_from('<H',b,p)[0]
    return n,struct.unpack_from('<%dh'%n,b,p+2),struct.unpack_from('<%dh'%n,b,p+2+2*n)
names={"Kp":(0xC77E4,0xC78D4,0xC79C4),"Kd":(0xC7784,0xC7874,0xC7964),"Ki":(0xC77B4,0xC78A4,0xC7994)}
for nm,tabs in names.items():
    print(nm)
    for t in tabs:
        # check stock & REV4 pointer arrays identical, show 16 entries (more than 12)
        pp=[u32(s,t+4*i) for i in range(16)]
        pr=[u32(r,t+4*i) for i in range(16)]
        print(hex(t),'ptrs same',pp==pr,[hex(x) for x in pp])
        for i in range(16):
            p=pp[i]
            if 0xC0000<=p<0x100000:
                print('  v',i,hex(p),'stock',rec(s,p)[2],'rev4',rec(r,p)[2],'X',rec(s,p)[1]==rec(r,p)[1])
