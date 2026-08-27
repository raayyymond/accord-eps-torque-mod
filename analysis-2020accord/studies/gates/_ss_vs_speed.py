"""Correlate raw CAN 399 STEER_STATUS against vEgo.
If STEER_STATUS==3 is a LOW-SPEED state, the FUN_00028ea6 deadband gate (live only while
gp-0x6806==0, which the ramp SM forces whenever STEER_STATUS visits {3,4,7}) is LIVE at
exactly the ~5 mph regime where the operator reports vibration."""
import io, collections
from pathlib import Path
import zstandard as zstd, capnp

KIT = Path(__file__).resolve().parents[2].parent
capnp.remove_import_hook()
log_capnp = capnp.load(str(KIT/"rlog-tools"/"cereal"/"log.capnp"))
MPH = 2.23694

def be_bits(data, start, length):
    val=0; bit=start
    for _ in range(length):
        byte,b_in = bit//8, bit%8
        val=(val<<1)|((data[byte]>>b_in)&1); bit = bit+15 if b_in==0 else bit-1
    return val

def which_of(evt):
    w = evt.which; return w() if callable(w) else w

def events(path):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(path).read_bytes())).read()
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try: yield next(it)
        except (StopIteration, capnp.KjException): break

# speed bucket -> Counter(status)
buckets = collections.defaultdict(collections.Counter)
EDGES = [0,1,2,3,4,5,6,8,10,15,20,30,45,100]
def bucket(mph):
    for i in range(len(EDGES)-1):
        if EDGES[i] <= mph < EDGES[i+1]: return f"{EDGES[i]}-{EDGES[i+1]}"
    return "100+"

for p in sorted((KIT/"analysis-2020accord"/"rlogs").glob("*.zst")):
    veg=None
    for evt in events(p):
        try:
            w=which_of(evt)
            if w=="carState": veg=evt.carState.vEgo*MPH
            elif w=="can" and veg is not None:
                for c in evt.can:
                    if c.address==399 and c.src==1 and len(c.dat)>=7:
                        buckets[bucket(veg)][be_bits(bytes(c.dat),39,4)] += 1
        except Exception: continue

print(f"{'speed (mph)':>12} {'n':>7}   {'ST=0':>7} {'ST=3':>7} {'ST=4':>7}")
print("-"*50)
order = [f"{EDGES[i]}-{EDGES[i+1]}" for i in range(len(EDGES)-1)]
for b in order:
    c = buckets.get(b)
    if not c: continue
    tot=sum(c.values())
    print(f"{b:>12} {tot:>7}   {100*c[0]/tot:6.1f}% {100*c[3]/tot:6.1f}% {100*c[4]/tot:6.1f}%")
