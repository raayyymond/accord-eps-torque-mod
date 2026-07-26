"""Inspect specific (bus,addr) fields' SHAPE vs coarse 0x2C8 lead range (bead eps-ejq).
For each requested frame, every u16 position: print binned (coarse-range decile -> field mean/std) so we
can see if it's a real monotonic/saturating sub-10m field or a small-sample artifact.
Usage: python _finerange_inspect.py <seg.zst>...   (targets hardcoded below)
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp
import numpy as np

CEREAL_DIR = Path(__file__).parent / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))
ALIGN_NS = 60_000_000
TARGETS = [(1, 0x324), (2, 0x240), (1, 0x158)]   # the R_close-notable fields

def load(p, cap=400000):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    out = []; n = 0
    for evt in log_capnp.Event.read_multiple_bytes(data):
        if evt.which() == "can":
            t = evt.logMonoTime
            for c in evt.can:
                out.append((t, int(c.src), int(c.address), bytes(c.dat)))
        n += 1
        if n >= cap: break
    return out

def main(paths):
    co_t, co_v, db = [], [], {k: ([], []) for k in TARGETS}
    for p in paths:
        for t, bus, addr, d in load(p):
            if bus == 2 and addr == 0x2C8 and len(d) >= 2 and d[0] != 0xFF:
                co_t.append(t); co_v.append((d[0] << 8) | d[1])
            if (bus, addr) in db and len(d) >= 2:
                db[(bus, addr)][0].append(t); db[(bus, addr)][1].append(d)
    ct = np.array(co_t); cv = np.array(co_v, float)
    o = np.argsort(ct); ct, cv = ct[o], cv[o]
    print(f"coarse lead samples={len(ct)} raw {int(cv.min())}..{int(cv.max())}\n")
    for (bus, addr), (ts, ds) in db.items():
        ts = np.array(ts)
        if len(ts) < 50:
            print(f"0x{addr:03X} bus{bus}: too few ({len(ts)})\n"); continue
        idx = np.clip(np.searchsorted(ct, ts), 1, len(ct)-1)
        pl = (ts - ct[idx-1]) <= (ct[idx]-ts); nidx = np.where(pl, idx-1, idx)
        ok = np.abs(ts - ct[nidx]) <= ALIGN_NS
        ca = cv[nidx][ok]; L = min(len(d) for d in ds)
        arr = np.array([[d[i] for i in range(L)] for d in ds], int)[ok]
        print(f"=== 0x{addr:03X} bus{bus}  DLC={L}  aligned n={int(ok.sum())} ===")
        edges = np.percentile(ca, np.linspace(0, 100, 7))
        for pos in range(L-1):
            for tag in ("BE", "LE"):
                fv = ((arr[:,pos]<<8)|arr[:,pos+1]) if tag=="BE" else ((arr[:,pos+1]<<8)|arr[:,pos])
                fv = fv.astype(float)
                if fv.std() < 1: continue
                r = np.corrcoef(fv, ca)[0,1]
                if abs(r) < 0.25: continue
                means = []
                for i in range(6):
                    m = (ca >= edges[i]) & (ca <= edges[i+1])
                    means.append(f"{fv[m].mean():6.0f}" if m.sum() else "    --")
                print(f"  B{pos}:B{pos+1} {tag} R={r:+.2f} [{int(fv.min())}..{int(fv.max())}]  by coarse-bin(near->far): {' '.join(means)}")
        print()

if __name__ == "__main__":
    main(sys.argv[1:])
