exec(open('t1.py').read().split('print("consts")')[0])
d=D['A340']
for r in range(18,26):
    a=0xCD012+r*0x24; print(r,hex(a),list(d[a:a+9]))
sel=set()
for r in range(0,18):
    a=0xCD012+r*0x24; sel|={d[a],d[a+1],d[a+2],d[a+3]}
print('A340 selectable idx cols e012-e015 rows0-17',sorted(sel))
d=D['A160'];sel=set()
for r in range(0,16):
    a=0xCD012+r*0x24; sel|={d[a],d[a+1],d[a+2],d[a+3]}
print('A160',sorted(sel))
for r in range(16):
    a=0xCD012+r*0x24; 
    if {26,27}&{d[a],d[a+1],d[a+2],d[a+3]}: print('A160 row',r,list(d[a:a+4]))
