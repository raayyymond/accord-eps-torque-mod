exec(open('t1.py').read().split('print("consts")')[0])
for k in ('A340','A160'):
    d=D[k]; print(k)
    for r in range(18):
        a=0xCD012-0x12+ 0xE000 - 0xE000 + r*0x24  # base such that tp+0xE012 = 0xCD012 + r*0x24
        a=0xCD012+r*0x24
        print(r,hex(a),'e012..e01a:',list(d[a:a+9]))
