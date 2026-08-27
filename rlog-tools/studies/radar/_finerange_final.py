"""Final, exhaustive check for the FUN_B718C fine-range field (bead eps-ejq).
Scans EVERY u16 (BE+LE, every byte position) on EVERY non-echo bus (0,1,2) for a field that is BOUNDED
near [0,2000] (the firmware clamp) AND varies AND correlates with the coarse 0x2C8 lead range. If the
5mm/LSB sub-10m field is on the wire at all, it shows here. Also reports the single best [0,2000]-bounded
field with slope/offset/R^2.
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp
import numpy as np

CEREAL_DIR = Path(__file__).parents[2] / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))
ALIGN_NS = 60_000_000

def load(p, cap=400000):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    out = []; n = 0
    try:
        for evt in log_capnp.Event.read_multiple_bytes(data):
            if evt.which() == "can":
                t = evt.logMonoTime
                for c in evt.can:
                    out.append((t, int(c.src), int(c.address), bytes(c.dat)))
            n += 1
            if n >= cap: break
    except Exception as e:
        sys.stderr.write(f"  [parse-end {Path(p).name}: {e}]\n")
    return out

def main(paths):
    co_t, co_v, db = [], [], {}
    for p in paths:
        for t, bus, addr, d in load(p):
            if bus == 2 and addr == 0x2C8 and len(d) >= 2 and d[0] != 0xFF:
                co_t.append(t); co_v.append((d[0] << 8) | d[1])
            if bus in (0, 1, 2) and len(d) >= 2:
                db.setdefault((bus, addr), ([], []))
                db[(bus, addr)][0].append(t); db[(bus, addr)][1].append(d)
        print(f"  loaded {Path(p).parent.name}")
    ct = np.array(co_t); cv = np.array(co_v, float)
    o = np.argsort(ct); ct, cv = ct[o], cv[o]
    print(f"coarse lead samples={len(ct)} raw span {int(cv.min())}..{int(cv.max())}")
    lo_thr = np.percentile(cv, 33)

    bounded = []   # fields bounded near [0,2000]
    for (bus, addr), (ts, ds) in db.items():
        ts = np.array(ts)
        if len(ts) < 60: continue
        idx = np.clip(np.searchsorted(ct, ts), 1, len(ct) - 1)
        pl = (ts - ct[idx-1]) <= (ct[idx] - ts); nidx = np.where(pl, idx-1, idx)
        ok = np.abs(ts - ct[nidx]) <= ALIGN_NS
        if ok.sum() < 50: continue
        ca = cv[nidx][ok]; lo = ca <= lo_thr
        L = min(len(d) for d in ds); arr = np.array([[d[i] for i in range(L)] for d in ds], int)[ok]
        for pos in range(L-1):
            for tag in ("BE", "LE"):
                fv = ((arr[:,pos]<<8)|arr[:,pos+1]) if tag=="BE" else ((arr[:,pos+1]<<8)|arr[:,pos])
                fv = fv.astype(float)
                mx, mn = fv.max(), fv.min()
                if not (1200 <= mx <= 2200): continue           # plausible clamp ceiling 10m@5mm=2000
                if fv.std() < 5 or len(set(fv.tolist())) < 8: continue   # must vary
                r = np.corrcoef(fv, ca)[0,1] if fv.std()>1e-6 else 0
                r_lo = np.corrcoef(fv[lo], ca[lo])[0,1] if lo.sum()>20 and fv[lo].std()>1e-6 else float('nan')
                frac_top = (fv >= mx-2).mean()
                bounded.append((abs(r), r, r_lo, bus, addr, pos, tag, int(mn), int(mx), frac_top, int(ok.sum())))
    bounded.sort(reverse=True)
    print(f"\n=== u16 fields BOUNDED near [0,2000] (clamp candidates), ranked by |R| vs coarse range ===")
    if not bounded:
        print("  NONE. No u16 on any bus is bounded near a 2000 clamp and varies with the lead.")
        print("  -> the 5mm/LSB saturate-at-10m fine-range field is NOT detectably broadcast on CAN.")
        return
    print(f"{'|R|':>5}{'R':>6}{'R_close':>8}  bus id     bytes end   min   max  frac@max   n")
    for ar, r, rl, bus, addr, pos, tag, mn, mx, ft, n in bounded[:20]:
        print(f"{ar:5.2f}{r:6.2f}{rl:8.2f}  {bus} 0x{addr:03X} B{pos}:B{pos+1} {tag} {mn:5d} {mx:5d}  {ft*100:5.1f}%  {n:5d}")

if __name__ == "__main__":
    main(sys.argv[1:])
