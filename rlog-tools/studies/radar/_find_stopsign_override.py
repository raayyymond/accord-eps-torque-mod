import glob, io
from pathlib import Path
import zstandard as zstd, capnp
CER = Path(__file__).parents[2] / "cereal"
capnp.remove_import_hook(); L = capnp.load(str(CER / "log.capnp"))

def ev(p):
    d = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    it = L.Event.read_multiple_bytes(d)
    while True:
        try: yield next(it)
        except StopIteration: return
        except capnp.KjException: return

# Build a merged per-time sample of the signals we need, then find stop episodes.
routes = {"00000000": "74efcd1ee3", "00000001": "638fd75d31", "00000002": "a6fcb0a223"}
for r, sfx in routes.items():
    segs = sorted(glob.glob(f"D:/drivedata/{r}--{sfx}--*/rlog.zst"),
                  key=lambda p: int(Path(p).parent.name.split("--")[-1]))
    rows = []  # (ts, seg, vEgo, aEgo, enabled, brake, cmdacc, longact)
    vEgo=99.0; aEgo=0.0; enabled=False; brake=False; cmdacc=0.0; longact=False; t0=None
    for s in segs:
        seg = int(Path(s).parent.name.split("--")[-1])
        for e in ev(s):
            w=e.which(); t=e.logMonoTime
            if t0 is None: t0=t
            ts=(t-t0)/1e9
            if w=="carState":
                cs=e.carState; vEgo=cs.vEgo; aEgo=cs.aEgo; brake=cs.brakePressed
            elif w=="carControl":
                cc=e.carControl; enabled=cc.enabled; longact=cc.longActive; cmdacc=cc.actuators.accel
                rows.append((ts, seg, vEgo, aEgo, enabled, brake, cmdacc, longact))
    # find stop episodes: vEgo dips < 0.5 then rises > 3
    eps=[]; i=0; n=len(rows)
    while i<n:
        if rows[i][2]<0.5:
            j=i
            while j<n and rows[j][2]<3.0: j+=1   # until moving again
            win=rows[i:min(j+40,n)]               # stop + launch window
            if win:
                launch=rows[max(i-1,0):min(j+40,n)]
                op_en = any(x[4] for x in launch)
                peak_cmd = max((x[6] for x in launch), default=0)
                peak_a = max((x[3] for x in launch), default=0)
                min_a = min((x[3] for x in launch), default=0)
                br = any(x[5] for x in launch)
                # disengage during launch: enabled True then False
                diseng = any(launch[k][4] and not launch[k+1][4] for k in range(len(launch)-1))
                ts0=rows[i][0]; seg=rows[i][2] and rows[i][1]
                eps.append((round(ts0,0), rows[i][1], round(ts0-rows[i][1]*60,1), op_en, round(peak_cmd,2), round(peak_a,2), round(min_a,2), br, diseng))
            i=j+1
        else: i+=1
    print(f"=== route {r}: {len(eps)} stop episodes (showing last 8) ===")
    print("   route_t seg t_in_seg OPen peakCmd peakA minA brake diseng")
    for x in eps[-8:]:
        print(f"   {x[0]:>6.0f}s s{x[1]} t={x[2]:>5}  OP={x[3]!s:>5} cmd={x[4]:>5} aMax={x[5]:>5} aMin={x[6]:>6} brk={x[7]!s:>5} dis={x[8]!s:>5}")
