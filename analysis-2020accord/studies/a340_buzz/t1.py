import struct,os
F="C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
import glob
P={'A340':F+"other bins/39990-TVA-A340.bin",
'A340R3':F+"_v300_a340_REV3_plain_image.bin",
'A160':F+"stock_fw_dump/code.bin"}
P['A160V300']=glob.glob(F+"_v300_V300-REV2-RELEASE*A16C_plain_image.bin")[0]
D={k:open(v,'rb').read() for k,v in P.items()}
for k,v in D.items(): print(k,len(v))
def h(d,a): return struct.unpack_from('<H',d,a)[0]
def s(d,a): return struct.unpack_from('<h',d,a)[0]
def w(d,a): return struct.unpack_from('<I',d,a)[0]
print("consts")
for k in D:
    d=D[k]
    if k.startswith('A340'):
        c={'alpha1 0xC645A':h(d,0xC645A),'0xC40D2':h(d,0xC40D2),'0xC40D4':h(d,0xC40D4),'clamp 0xC407E':s(d,0xC407E),'fallb 0xC7420':s(d,0xC7420),'fallb 0xC7422':s(d,0xC7422),'gate 0xC74FD?':d[0xC7548+5-0]  }
    else:
        c={'alpha1 0xC643C':h(d,0xC643C),'0xC40DA':h(d,0xC40DA),'0xC40DC':h(d,0xC40DC),'clamp 0xC407E':s(d,0xC407E),'fallb 0xC740A':s(d,0xC740A),'fallb 0xC740C':s(d,0xC740C)}
    print(k,c)
