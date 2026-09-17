"""ATTRIBUTION, the clean way: what ACTUALLY differed on the car between the rev 5 route (76)
and the rev 6.4 routes (6c, 6d)? Not what the commits say -- what the device was running.
Every difference is a candidate cause of the measured 27-33% over-delivery.
"""
import sys, glob
sys.path.insert(0,'/home/user/accord-eps-torque-mod/rlog-tools/lib')
from rlog_parse import read_messages

def params(route_glob):
    p=sorted(glob.glob(route_glob))[0]
    out={}
    n=0
    for evt in read_messages(p):
        try: w=evt.which()
        except Exception: continue
        n+=1
        if w=='initData':
            d=evt.initData
            out['__gitCommit']=str(d.gitCommit)
            try:
                for e in d.params.entries:
                    k=e.key if isinstance(e.key,str) else e.key.decode('utf8','ignore')
                    v=e.value
                    v=v.decode('utf8','ignore') if isinstance(v,(bytes,bytearray)) else str(v)
                    if len(v)<60: out[k]=v
            except Exception as ex: print('param err',ex)
            break
        if n>5000: break
    return out

R='/home/user/accord-eps-torque-mod/analysis-2020accord/rlogs/'
P76=params(R+'75604b0a432fdc89_00000076--*--0--rlog.zst')
P6C=params(R+'75604b0a432fdc89_0000006c--*--0--rlog.zst')
P6D=params(R+'75604b0a432fdc89_0000006d--*--0--rlog.zst')
print(f"route 76 commit {P76.get('__gitCommit','?')[:12]}  ({len(P76)} params)")
print(f"route 6c commit {P6C.get('__gitCommit','?')[:12]}  ({len(P6C)} params)")
print(f"route 6d commit {P6D.get('__gitCommit','?')[:12]}  ({len(P6D)} params)")

keys=sorted(set(P76)|set(P6C)|set(P6D))
print()
print("="*100)
print("EVERY DIFFERENCE BETWEEN THE REV 5 FLIGHT AND THE REV 6.4 FLIGHTS")
print("="*100)
print(f"  {'param':42s} {'route76 (rev5)':>18} {'6c (rev6.4)':>16} {'6d (rev6.4)':>16}")
ndiff=0
for k in keys:
    if k.startswith('__'): continue
    a,b,c=P76.get(k,'<absent>'),P6C.get(k,'<absent>'),P6D.get(k,'<absent>')
    if a==b==c: continue
    ndiff+=1
    star=' *' if ('ccord' in k or 'Lane' in k or 'Steer' in k or 'Torque' in k) else ''
    print(f"  {k[:42]:42s} {a[:18]:>18} {b[:16]:>16} {c[:16]:>16}{star}")
print(f"\n  {ndiff} parameters differ.  (* = lateral-control relevant)")

print()
print("="*100)
print("DID 6c AND 6d DIFFER FROM EACH OTHER? (if not, they are a clean pooled sample)")
print("="*100)
d2=[k for k in keys if not k.startswith('__') and P6C.get(k,'<absent>')!=P6D.get(k,'<absent>')]
if d2:
    for k in d2: print(f"  {k[:42]:42s} 6c={P6C.get(k,'<absent>')[:20]:>20}  6d={P6D.get(k,'<absent>')[:20]:>20}")
else:
    print("  identical -- 6c and 6d are the same configuration, so pooling them is sound.")
