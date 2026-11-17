exec(open('t1.py').read().split('print("consts")')[0])
for k in D:
    d=D[k]
    if k.startswith('A340'):
        print(k,'0xC6420',s(d,0xC6420),'0xC6422',s(d,0xC6422),'thr 0xC654D',d[0xC654D],'ptrtab 0xCBE40+26*4,27*4',hex(w(d,0xCBE40+26*4)),hex(w(d,0xCBE40+27*4)))
    else:
        print(k,'0xC640A',s(d,0xC640A),'0xC640C',s(d,0xC640C),'thr 0xC64FD',d[0xC64FD],'ptrtab 0xCBE74..',[hex(w(d,0xCBE74+4*i)) for i in (26,27)])
