import io
from pathlib import Path
import zstandard as zstd, capnp
CER = Path(__file__).parent / "cereal"
capnp.remove_import_hook(); L = capnp.load(str(CER / "log.capnp"))

def ev(p):
    d = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    it = L.Event.read_multiple_bytes(d)
    while True:
        try: yield next(it)
        except StopIteration: return
        except capnp.KjException: return

for segn in [3, 2, 4]:
    p = f"D:/drivedata/00000002--a6fcb0a223--{segn}/rlog.zst"
    rows=[]; vEgo=aEgo=cmd=0.0; en=lo=brake=gas=ss=False; t0=None
    for e in ev(p):
        w=e.which(); t=e.logMonoTime
        if t0 is None: t0=t
        ts=(t-t0)/1e9
        if w=="carState":
            cs=e.carState; vEgo=cs.vEgo; aEgo=cs.aEgo; brake=cs.brakePressed; gas=cs.gasPressed
        elif w=="carControl":
            cc=e.carControl; en=cc.enabled; lo=cc.longActive; cmd=cc.actuators.accel
        elif w=="drivingModelData":
            try: ss=e.drivingModelData.action.shouldStop
            except: pass
        if w=="carState":
            rows.append((ts,vEgo,aEgo,cmd,en,lo,ss,brake,gas))
    if not rows:
        print(f"seg {segn}: (empty)"); continue
    # find min aEgo (the hardest brake)
    mi=min(range(len(rows)), key=lambda k: rows[k][2])
    mt=rows[mi][0]
    print(f"=== seg {segn}: min aEgo={rows[mi][2]:.2f} at t_in_seg={mt:.1f}s — window: ===")
    last=-1
    for x in rows:
        if mt-7 <= x[0] <= mt+5 and int(x[0]*2)!=last:
            last=int(x[0]*2)
            print(f"  t={x[0]:5.1f} vEgo={x[1]*2.237:4.0f}mph aEgo={x[2]:+5.2f} cmd={x[3]:+5.2f} OP={x[4]!s:5} long={x[5]!s:5} stop={x[6]!s:5} brk={x[7]!s:5} gas={x[8]!s:5}")
