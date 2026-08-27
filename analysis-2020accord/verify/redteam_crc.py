import struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
code=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
END=0x100000; START=0x13000
start_page,num_pages=struct.unpack_from("<HH",code,END-8)
bs,bl=start_page<<12,(num_pages<<12)-4
blocks=[]; seen=set()
while True:
    assert bs not in seen; seen.add(bs)
    blocks.append((bs,bs+bl))
    if bs==START: break
    np_,nn=struct.unpack_from("<HH",code,bs-8); bs,bl=np_<<12,(nn<<12)-4
blocks.sort()
print(f"CRC chain: {len(blocks)} blocks")
TARGETS={"0xD6004 clampBound m24":0xD6004,"0xD6010 K1 m24":0xD6010,"0xD60F0 finalBound m24":0xD60F0,
         "0xD6158 assist map m24":0xD6158,"0xD7002 clampBound m26":0xD7002,"0xD700E K1 m26":0xD700E,
         "0xD70D8 finalBound m26":0xD70D8,"0xD7130 assist map m26":0xD7130,
         "0xC60B4 c4":0xC60B4,"0xC615A finalBound fallback":0xC615A,"0xC520C bank A":0xC520C}
for nm,a in TARGETS.items():
    hit=[(s,e) for s,e in blocks if s<=a<e]
    print(f"  {nm:32s} 0x{a:X}  -> " + (f"block [0x{hit[0][0]:X},0x{hit[0][1]:X}) trailer 0x{hit[0][1]:X}"
          if hit else "🛑 NOT IN ANY CRC BLOCK"))
gaps=[]
for i in range(len(blocks)-1):
    if blocks[i][1]+4 != blocks[i+1][0]: gaps.append((blocks[i][1]+4, blocks[i+1][0]))
print("\nGaps in the chain (bootloader-skipped):", [f"[0x{a:X},0x{b:X})" for a,b in gaps])
