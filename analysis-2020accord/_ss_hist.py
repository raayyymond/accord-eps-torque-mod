"""Histogram raw CAN 399 STEER_STATUS across every rlog on disk.
Answers: does STEER_STATUS ever visit 3 (or 2) during real driving?
That decides whether the FUN_00028ea6 deadband gate (gated by gp-0x6806, which the
ramp SM drops to 0 whenever STEER_STATUS visits {3,4,7}) is ever live mid-drive."""
import io, collections
from pathlib import Path
import zstandard as zstd, capnp

KIT = Path(__file__).resolve().parent.parent
capnp.remove_import_hook()
log_capnp = capnp.load(str(KIT/"rlog-tools"/"cereal"/"log.capnp"))

def be_bits(data, start, length):
    val=0; bit=start
    for _ in range(length):
        byte,b_in = bit//8, bit%8
        val=(val<<1)|((data[byte]>>b_in)&1)
        bit = bit+15 if b_in==0 else bit-1
    return val

def which_of(evt):
    w = evt.which
    return w() if callable(w) else w

def events(path):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(path).read_bytes())).read()
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try: yield next(it)
        except (StopIteration, capnp.KjException): break

grand=collections.Counter(); trans=collections.Counter(); srcs=collections.Counter()
for p in sorted((KIT/"analysis-2020accord"/"rlogs").glob("*.zst")):
    hist=collections.Counter(); prev=None
    for evt in events(p):
        try:
            if which_of(evt)!="can": continue
            for c in evt.can:
                if c.address==399 and len(c.dat)>=7:
                    srcs[c.src]+=1
                    if c.src!=1: continue          # EPS frames ride bus 1
                    s=be_bits(bytes(c.dat),39,4); hist[s]+=1
                    if prev is not None and s!=prev: trans[(prev,s)]+=1
                    prev=s
        except Exception: continue
    if hist:
        tot=sum(hist.values())
        print(f"{p.name[:44]:<44} n={tot:>6}  " + " ".join(f"{k}:{100*v/tot:5.1f}%" for k,v in sorted(hist.items())))
    grand.update(hist)

tot=sum(grand.values()) or 1
print("\n"+"="*84)
print(f"src distribution for addr 399: {dict(srcs)}")
print(f"GRAND TOTAL n={sum(grand.values())}")
for k,v in sorted(grand.items()):
    print(f"  STEER_STATUS={k:<2} {v:>8} frames  {100*v/tot:6.3f}%")
print("\ntransitions:")
for (a,b),n in trans.most_common(20):
    print(f"  {a} -> {b}: {n}")
