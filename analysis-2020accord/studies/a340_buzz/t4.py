exec(open('t1.py').read().split('print("consts")')[0])
a=D['A340'];b=D['A340R3']
diffs=[i for i in range(0x13000,0x100000) if a[i]!=b[i]]
print(len(diffs))
groups=[];cur=[diffs[0]]
for i in diffs[1:]:
    if i-cur[-1]<=8: cur.append(i)
    else: groups.append(cur);cur=[i]
groups.append(cur)
print(len(groups))
for g in groups:
    s0,e0=g[0],g[-1]
    print(hex(s0),hex(e0),len(g),'stock',a[s0:e0+1].hex()[:48],'->',b[s0:e0+1].hex()[:48])
