# -*- coding: utf-8 -*-
"""x1ab_extract.py -- D2 (fork-first) V299 design: is the V298 cave's 0x1AB frame a VALID Honda frame (COUNTER + CHECKSUM)?

C12 of DRIVE-READ-V298-r79: the cache stores 0x1AB bytes 0-1 only, so whether byte 2 (COUNTER bits 5:4, CHECKSUM bits
3:0, OUTPUT_DISABLED bit 6 per opendbc _honda_common.dbc BO_ 427) is consistent with the tapped bytes 0-1 is UNKNOWN.
The fork's bar fix (D2 implementation b) parses 0x1AB with opendbc's CANParser; a frame with a bad checksum/counter
never updates (parser.MessageState.parse returns False), so the answer decides whether the parse can keep the checks on.

ANALYSIS ONLY: reads route-79 rlogs, writes _scratch/v299_D2/x1ab_r79.npz + .txt.  One decode pass per segment,
16 processes.  Checksum = opendbc honda/hondacan.py honda_checksum (re-implemented verbatim below).
"""
import glob
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
KIT_A = os.path.join(KIT, "analysis-2020accord")
RLOGS = os.path.join(KIT_A, "rlogs")
PREFIX = "75604b0a432fdc89_00000079--a1f5d2a272"
SCHEMA_DIR = os.path.join(KIT, "_scratch", "cereal_fork_dom_2712e1336")
OUT = os.path.join(KIT, "_scratch", "v299_D2")
_LOG = None


def load_log():
    global _LOG
    if _LOG is None:
        import capnp
        capnp.remove_import_hook()
        _LOG = capnp.load(os.path.join(SCHEMA_DIR, "log.capnp"))
    return _LOG


def honda_checksum(address, d):
    """opendbc/car/honda/hondacan.py honda_checksum, 11-bit ids (verbatim arithmetic)."""
    s = 0
    addr = address
    while addr:
        s += addr & 0xF
        addr >>= 4
    for i in range(len(d)):
        x = d[i]
        if i == len(d) - 1:
            x >>= 4
        s += (x & 0xF) + (x >> 4)
    return (8 - s) & 0xF


def work(path):
    import zstandard
    log = load_log()
    data = zstandard.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    T, S, B = [], [], []
    for ev in log.Event.read_multiple_bytes(data):
        try:
            if ev.which() != "can":
                continue
        except Exception:
            continue
        t = ev.logMonoTime * 1e-9
        for m in ev.can:
            if m.address == 0x1AB:
                d = bytes(m.dat)
                if len(d) >= 3:
                    T.append(t); S.append(m.src); B.append(d[:3])
    return path, np.array(T), np.array(S, np.int64), np.frombuffer(b"".join(B), np.uint8).reshape(-1, 3)


def main():
    t0 = time.perf_counter()
    segs = sorted(glob.glob(os.path.join(RLOGS, PREFIX + "--*--rlog.zst")))
    with Pool(min(16, len(segs))) as p:
        res = p.map(work, sorted(segs, key=lambda q: -os.path.getsize(q)))
    T = np.concatenate([r[1] for r in res]); S = np.concatenate([r[2] for r in res])
    Bt = np.concatenate([r[3] for r in res])
    o = np.argsort(T, kind="stable"); T, S, Bt = T[o], S[o], Bt[o]
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, "x1ab_r79.npz"), t=T, src=S, b=Bt)
    L = [f"segments {len(segs)}  frames {len(T)}  decode {time.perf_counter()-t0:.1f} s"]
    for src in np.unique(S):
        m = S == src
        b = Bt[m].astype(np.int64)
        ck = np.array([honda_checksum(0x1AB, bytes(r)) for r in Bt[m]])
        rx = b[:, 2] & 0xF
        cnt = (b[:, 2] >> 4) & 0x3
        od = (b[:, 2] >> 6) & 1
        dc = (cnt[1:] - cnt[:-1]) & 3
        raw10 = ((b[:, 0] & 3) << 8) | b[:, 1]
        mag = raw10 & 0x1FF
        L.append(f"src {src}: n {m.sum()}  checksum OK {np.mean(ck == rx)*100:.3f} %  (bad {np.sum(ck != rx)})  "
                 f"counter step==1 {np.mean(dc == 1)*100:.3f} % (bad {np.sum(dc != 1)})  OUTPUT_DISABLED=1 {np.mean(od)*100:.2f} %  "
                 f"CONFIG_VALID(b0.7)=1 {np.mean((b[:,0]>>7)&1)*100:.2f} %  |tap|>0 {np.mean(mag>0)*100:.1f} %  "
                 f"b0 bits 6:2 nonzero {np.mean((b[:,0]>>2)&0x1F != 0)*100:.2f} %")
        bad = np.where(ck != rx)[0][:5]
        for i in bad:
            L.append(f"   bad example t {T[m][i]:.3f} bytes {Bt[m][i].tobytes().hex()} calc {ck[i]:x}")
    L.append(f"wall {time.perf_counter()-t0:.1f} s")
    txt = "\n".join(L)
    open(os.path.join(OUT, "x1ab_r79.txt"), "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
