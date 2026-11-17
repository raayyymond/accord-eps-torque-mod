exec(open('t1c.py').read().split("for k,base")[0])
for k,base in (('A340R3',0xCBE40),('A160V300',0xCBE74)):
    d=D[k]; ps=[w(d,base+4*i) for i in range(34)]
    print(k,[(i,rec(d,p)[4:7]) for i,p in enumerate(ps) if rec(d,p)[4:7]!=[-9830,-5734,-1966]])
# are the 34 ptrs in table beyond 34? read 40
for k,base in (('A340',0xCBE40),('A160',0xCBE74)):
    print(k,[hex(w(D[k],base+4*i)) for i in range(34,40)])
# who else uses these records: 0xD7A5C
for k in D:
    d=D[k]; b=struct.pack('<h',-29490)
    print(k,'rows -29490 at',[hex(i) for i in range(0xC0000,0x100000-1) if d[i:i+2]==b][:6])
