"""Correlation-driven hunt for the sub-10m fine-range field (bead eps-ejq).
Definitive test: for EVERY u16 field (BE+LE, every byte position) on bus 0/1, time-align to the coarse
0x2C8 selected-lead range (bus 2) and compute Pearson R / slope / offset / n. A field that measures the
same physical lead range will rank at the top; we then check it for the 5mm/LSB + saturate-at-2000 (10m)
behavior. Reports slope/offset/R^2 the operator asked for.
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp
import numpy as np

CEREAL_DIR = Path(__file__).parent / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))

CAND_IDS = {0x1EF, 0x30C, 0x39F, 0x1FA, 0x1DB, 0x33D, 0xE4}
COARSE_ID = 0x2C8
ALIGN_NS = 60_000_000          # 60 ms alignment window

def load(p, cap=300000):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    out = []
    n = 0
    try:
        for evt in log_capnp.Event.read_multiple_bytes(data):
            if evt.which() == "can":
                t = evt.logMonoTime
                for c in evt.can:
                    out.append((t, int(c.src), int(c.address), bytes(c.dat)))
            n += 1
            if n >= cap:
                break
    except Exception as e:
        sys.stderr.write(f"  [parse-end {Path(p).name}: {e}]\n")
    return out

def main(paths):
    # gather coarse reference (bus 2, 0x2C8, B0:B1, valid when B0 != 0xFF), and bus0/1 frames per (bus,addr)
    coarse_t, coarse_v = [], []
    framedb = {}   # (bus,addr) -> [t...], [dat...]
    for p in paths:
        fr = load(p)
        print(f"  {Path(p).parent.name}: {len(fr)} can frames")
        for t, bus, addr, dat in fr:
            if bus == 2 and addr == COARSE_ID and len(dat) >= 2 and dat[0] != 0xFF:
                coarse_t.append(t); coarse_v.append((dat[0] << 8) | dat[1])
            if bus in (0, 1) and len(dat) >= 2:
                k = (bus, addr)
                if k not in framedb:
                    framedb[k] = ([], [])
                framedb[k][0].append(t); framedb[k][1].append(dat)

    if len(coarse_t) < 100:
        print("  not enough coarse 0x2C8 lead samples; abort"); return
    ct = np.array(coarse_t); cv = np.array(coarse_v, dtype=float)
    order = np.argsort(ct); ct = ct[order]; cv = cv[order]
    print(f"\n=== coarse 0x2C8 lead samples (B0!=0xFF): {len(ct)} ; raw range span {int(cv.min())}..{int(cv.max())} ===")

    results = []
    for (bus, addr), (ts, dats) in framedb.items():
        ts = np.array(ts)
        if len(ts) < 100:
            continue
        # align each frame time to nearest coarse sample within ALIGN_NS
        idx = np.searchsorted(ct, ts)
        idx = np.clip(idx, 1, len(ct) - 1)
        left = ct[idx - 1]; right = ct[idx]
        pick_left = (ts - left) <= (right - ts)
        nidx = np.where(pick_left, idx - 1, idx)
        dt = np.abs(ts - ct[nidx])
        ok = dt <= ALIGN_NS
        if ok.sum() < 80:
            continue
        coarse_aligned = cv[nidx][ok]
        L = min(len(d) for d in dats)
        arr = np.array([[d[i] for i in range(L)] for d in dats], dtype=int)[ok]   # (n, L) bytes
        for pos in range(0, L - 1):
            be = (arr[:, pos] << 8) | arr[:, pos + 1]
            le = (arr[:, pos + 1] << 8) | arr[:, pos]
            for tag, fv in (("BE", be.astype(float)), ("LE", le.astype(float))):
                if fv.std() < 1e-6 or coarse_aligned.std() < 1e-6:
                    continue
                r = np.corrcoef(fv, coarse_aligned)[0, 1]
                if not np.isfinite(r):
                    continue
                results.append((abs(r), r, bus, addr, pos, tag, fv.min(), fv.max(), len(fv)))

    results.sort(reverse=True)
    print(f"\n=== TOP u16 fields by |Pearson R| vs coarse 0x2C8 range ===")
    print(f"{'|R|':>5} {'R':>6}  bus id      bytes endian   min    max     n   cand")
    for ar, r, bus, addr, pos, tag, mn, mx, n in results[:30]:
        cand = "*" if addr in CAND_IDS else ""
        print(f"{ar:5.2f} {r:6.2f}  {bus}  0x{addr:03X}  B{pos}:B{pos+1} {tag}  {int(mn):5d}  {int(mx):5d} {n:5d}   {cand}")

    # for the single best correlated field, print slope/offset/R^2 (linear fit field = a*coarse + b)
    if results and results[0][0] > 0.3:
        ar, r, bus, addr, pos, tag, mn, mx, n = results[0]
        # recompute aligned arrays for this field
        ts = np.array(framedb[(bus, addr)][0]); dats = framedb[(bus, addr)][1]
        idx = np.clip(np.searchsorted(ct, ts), 1, len(ct) - 1)
        pick_left = (ts - ct[idx - 1]) <= (ct[idx] - ts)
        nidx = np.where(pick_left, idx - 1, idx); ok = np.abs(ts - ct[nidx]) <= ALIGN_NS
        L = min(len(d) for d in dats); arr = np.array([[d[i] for i in range(L)] for d in dats], dtype=int)[ok]
        ca = cv[nidx][ok]
        fv = ((arr[:, pos] << 8) | arr[:, pos + 1]) if tag == "BE" else ((arr[:, pos + 1] << 8) | arr[:, pos])
        fv = fv.astype(float)
        a, b = np.polyfit(ca, fv, 1)
        rr = np.corrcoef(fv, ca)[0, 1] ** 2
        print(f"\n=== BEST: bus{bus} 0x{addr:03X} B{pos}:B{pos+1} {tag} ===")
        print(f"  field = {a:.4f} * coarse_raw + {b:.2f}   R^2={rr:.3f}  n={int(ok.sum())}")
        print(f"  field range observed: {int(fv.min())}..{int(fv.max())}  (saturate-at-2000 check)")
        print(f"  coarse raw range:     {int(ca.min())}..{int(ca.max())}")
    else:
        print("\n  No field correlates strongly (|R|<=0.3) with coarse lead range on bus 0/1.")

if __name__ == "__main__":
    main(sys.argv[1:])
