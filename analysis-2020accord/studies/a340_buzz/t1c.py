exec(open('t1.py').read().split('print("consts")')[0])
def rec(d,a): return [s(d,a+2*i) for i in range(0,8)]
for k,base in (('A340',0xCBE40),('A160',0xCBE74),('A340R3',0xCBE40),('A160V300',0xCBE74)):
    d=D[k]
    print(k)
    ps=[w(d,base+4*i) for i in range(0,34)]
    print(' ptrs',[hex(p) for p in ps])
    if k in('A340','A160'): 
      for i,p in enumerate(ps):
        if 0xC0000<p<0x100000: print(' ',i,hex(p),rec(d,p))
