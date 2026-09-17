"""Per-route, per-segment toggle census from initData params (head of each rlog only) + carParams steerActuatorDelay."""
import sys, io, glob, os, json
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
import zstandard as zstd
from rlog_parse import log_capnp
from pathlib import Path
R='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs/'
ROUTES=["00000064--ce6b0b0ebb","00000065--b9f78988bd","0000006c--2bc842dbac","00000039--f56039af87","0000003a--283a39a1d6",
        "0000003c--927965c2b4","0000006c--68c6e94b17","0000006d--05e83bb04f","0000006e--6ca3e014fd","00000076--d0b7ea7e4d","00000075--6c8687d5bd"]
def head(p, nbytes=8_000_000):
    raw=Path(p).read_bytes()
    data=zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read(nbytes)
    out={}
    try:
        for e in log_capnp.Event.read_multiple_bytes(data):
            try: w=e.which()
            except Exception: continue
            if w=='initData' and 'init' not in out:
                d=e.initData
                out['commit']=str(d.gitCommit)[:10]
                P={}
                for en in d.params.entries:
                    v=bytes(en.value)
                    if en.key in ('LiveDelay','LiveTorqueParameters','CarParams','CarParamsCache','CarParamsPersistent','CarParamsPrevRoute') : continue
                    if len(v)<200:
                        P[en.key]=v.decode('utf8','replace')
                out['params']=P; out['init']=1
            elif w=='carParams' and 'cp' not in out:
                c=e.carParams
                out['cp']=dict(steerActuatorDelay=c.steerActuatorDelay, lateralSmoothSeconds=getattr(c,'lateralSmoothSeconds',None) if hasattr(c,'lateralSmoothSeconds') else None,
                               fingerprint=str(c.carFingerprint))
            if 'init' in out and 'cp' in out: break
    except Exception as ex:
        out['err']=str(ex)[:80]
    return out
res={}
for r in ROUTES:
    segs=sorted(glob.glob(R+f'75604b0a432fdc89_{r}--*--rlog.zst'), key=lambda p:int(os.path.basename(p).split('--')[2]))
    per=[]
    for p in segs:
        h=head(p); h['seg']=int(os.path.basename(p).split('--')[2]); per.append(h)
    res[r]=per
    print(r, len(segs), per[0].get('commit'), per[0].get('cp'), flush=True)
json.dump(res, open('census_params_raw.json','w'), indent=0)
