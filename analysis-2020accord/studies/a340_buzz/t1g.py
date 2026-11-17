exec(open('t1.py').read().split('print("consts")')[0])
for k in ('A340','A160'):
    d=D[k];print(k)
    for r in range(29):
        b=0xCD000+r*0x24
        print(r,'key',d[b:b+5].hex(),'sel',list(d[b+0x12:b+0x16]))
