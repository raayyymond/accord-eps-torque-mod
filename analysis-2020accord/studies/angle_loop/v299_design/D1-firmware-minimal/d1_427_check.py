# -*- coding: utf-8 -*-
"""d1_427_check.py -- is the V298 0x1AB (427 STEER_MOTOR_TORQUE) frame a VALID Honda frame on route 79?
Decodes every r79 segment once (one process per segment), keeps 0x1AB on bus 1 (EPS side) and bus 0 (car side),
and checks the Honda nibble checksum (opendbc honda_checksum form) and the 2-bit COUNTER sequence in byte 2.
This decides whether the fork can add STEER_MOTOR_TORQUE to its CANParser without risking canValid.
ANALYSIS ONLY (reads rlogs).  Wall time printed."""
import glob, os, sys, time, contextlib, io
from multiprocessing import Pool
from pathlib import Path
import numpy as np
t0 = time.time()
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "studies" / "grind"))
PREFIX = "75604b0a432fdc89_00000079--a1f5d2a272"


def honda_checksum(address, d):
    s, a = 0, address
    while a > 0:
        s += a & 0xF
        a >>= 4
    for i, x in enumerate(d):
        if i == len(d) - 1:
            x >>= 4
        s += (x & 0xF) + (x >> 4)
    return (8 - s) & 0xF


def seg(p):
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_flight_read as FR
    FR.g = {}
    clog, _ = FR.fork_log_schema()
    import zstandard
    with open(p, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    out = []
    it = clog.Event.read_multiple_bytes(data)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            break
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        for m in evt.can:
            if m.address == 0x1AB and m.src in (0, 1, 2):
                d = bytes(m.dat)
                out.append((tm, m.src, len(d)) + tuple(d[:3]) + ((0,) * (3 - min(3, len(d)))))
    return out


if __name__ == "__main__":
    segs = sorted(glob.glob(str(KIT / "analysis-2020accord" / "rlogs" / f"{PREFIX}--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    with Pool(16) as pool:
        R = [r for rr in pool.map(seg, segs) for r in rr]
    A = np.array(R, float)
    print(f"segments {len(segs)}; 0x1AB frames {len(A)}")
    for src in (0, 1, 2):
        X = A[A[:, 1] == src]
        if not len(X):
            print(f"  src {src}: none")
            continue
        L = X[:, 2].astype(int)
        b = X[:, 3:6].astype(int)
        ok = np.array([honda_checksum(0x1AB, bytes([int(q) for q in r])) == (int(r[2]) & 0xF) for r in b])
        cnt = (b[:, 2] >> 4) & 3
        dc = np.diff(cnt) % 4
        print(f"  src {src}: n {len(X)}  len {sorted(set(L))}  checksum valid {ok.mean()*100:.3f} %  "
              f"counter step==1 {np.mean(dc == 1)*100:.3f} %  rate {len(X)/(X[-1,0]-X[0,0]):.1f} Hz")
        bad = np.flatnonzero(~ok)[:5]
        for i in bad:
            print(f"     bad t {X[i,0]:.3f} bytes {bytes([int(q) for q in b[i]]).hex(' ')}")
        tq = ((b[:, 0] & 0x3) << 8) | b[:, 1]                 # MOTOR_TORQUE 1|10@0+ (Motorola): byte0 bits1..0, byte1
        print(f"     MOTOR_TORQUE field: min {tq.min()} max {tq.max()}; sign bit 9 set {np.mean(tq >> 9)*100:.1f} %;"
              f" CONFIG_VALID (byte0 bit7) {np.mean(b[:,0] >> 7)*100:.1f} %; OUTPUT_DISABLED (byte2 bit6) {np.mean((b[:,2]>>6)&1)*100:.1f} %")
    print(f"wall {time.time()-t0:.1f} s")
