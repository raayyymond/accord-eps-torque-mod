import sys, time, io
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
import zstandard as zstd
from rlog_parse import log_capnp
from pathlib import Path
R='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs/'
def head_events(p, nbytes=6_000_000):
    raw=Path(p).read_bytes()
    data=zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read(nbytes)
    out=[]
    try:
        for e in log_capnp.Event.read_multiple_bytes(data):
            out.append(e)
            if len(out)>3000: break
    except Exception as ex:
        pass
    return out
t0=time.time()
ev=head_events(R+'75604b0a432fdc89_0000006c--68c6e94b17--0--rlog.zst')
print(len(ev), time.time()-t0)
for e in ev:
    try: w=e.which()
    except Exception: continue
    if w=='initData':
        d=e.initData; print('commit',d.gitCommit)
        for en in d.params.entries:
            k=en.key; v=bytes(en.value)
            print(k, len(v), v[:80])
        break
