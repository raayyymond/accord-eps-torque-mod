"""REFUTE-V299 bytes/failsafe: re-read every spec'd byte from the V298 image (Python LE). Wall < 2 s."""
import hashlib, zlib, glob, time, os
t0=time.time()
P=glob.glob('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin')[0]
b=open(P,'rb').read(); print('len',hex(len(b)),'sha',hashlib.sha256(b).hexdigest()[:16])
def h(a,n): return b[a:a+n].hex(' ')
for a,n in [(0xC4C5E,0x20),(0xC4C60,8),(0xC4C6A,0x14),(0xC4C7E,4),(0x1310D,1),(0x13100,0x20),(0xC4FFC,4)]:
    print(hex(a),h(a,n))
print('cave',h(0xC4C00,0x104))
print('cave sha',hashlib.sha256(b[0xC4C00:0xC4D04]).hexdigest())
print('crc main', hex(zlib.crc32(b[0x13000:0xC4FFC])), 'trailer LE', hex(int.from_bytes(b[0xC4FFC:0xC5000],'little')),'BE',hex(int.from_bytes(b[0xC4FFC:0xC5000],'big')))
# occurrences of the patched patterns
for pat in [bytes.fromhex('206e0002'),bytes.fromhex('206e2c01'),bytes.fromhex('244fa0b0'),bytes.fromhex('244f0096')]:
    i=-1; hits=[]
    while True:
        i=b.find(pat,i+1)
        if i<0: break
        hits.append(hex(i))
    print(pat.hex(),hits[:20])
# F181 strings
i=b.find(b'A16A'); print('A16A at',[hex(m) for m in range(len(b)) if b[m:m+4]==b'A16A'][:10])
print('wall %.2f s'%(time.time()-t0))
