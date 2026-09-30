"""census one rlog segment: service counts, CAN (bus, address) counts, decode time.  ANALYSIS ONLY."""
import sys, os, time, collections
import zstandard, capnp

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
capnp.remove_import_hook()
log = capnp.load(os.path.join(KIT, "_scratch", "cereal_fork_native", "log.capnp"))
RL = os.path.join(KIT, "analysis-2020accord", "rlogs")
route = "75604b0a432fdc89_00000071--a7b8ba5d9d"
seg = int(sys.argv[1]) if len(sys.argv) > 1 else 0
t0 = time.time()
data = zstandard.ZstdDecompressor().stream_reader(open(os.path.join(RL, f"{route}--{seg}--rlog.zst"), "rb")).read()
svc = collections.Counter(); can = collections.Counter(); lens = {}
first = {}
for evt in log.Event.read_multiple_bytes(data):
    w = evt.which()
    svc[w] += 1
    if w not in first:
        first[w] = evt.logMonoTime
    if w == "can":
        for m in evt.can:
            can[(m.src, m.address)] += 1
            lens[(m.src, m.address)] = len(m.dat)
print("decode s", round(time.time() - t0, 1), "bytes", len(data))
for k, v in sorted(svc.items(), key=lambda kv: -kv[1]):
    print(f"  {k:32s} {v}")
print("CAN:")
for (b, a), v in sorted(can.items()):
    if a in (0xE4, 0x18F, 0x14A, 0x1AB, 0x158, 0x1D0, 0x309, 0x156, 0x33D, 0x39F, 0x1A6, 0x326, 0x17C, 0x1FA, 0x255) or v > 5000:
        print(f"  bus {b:3d} 0x{a:03X} ({a}) n={v} len={lens[(b, a)]}")
print("n distinct (bus,addr):", len(can))
