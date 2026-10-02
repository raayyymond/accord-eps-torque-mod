# -*- coding: utf-8 -*-
"""extract_r79_1ab.py -- route 79: every 0x1AB (427 STEER_MOTOR_TORQUE) frame on bus 1 (the Accord pt bus the fork's
CANParser reads, hondacan.CanBus: Bosch non-radarless pt = offset + 1), full 3 bytes, plus segment 0's bus-1 event times
(the parser clock).  One process per segment.  Output: _scratch/v299_fork/r79_1ab.npz.  Read-only on the rlogs.
Schema: the fork's cereal at 2712e1336 as the r79 extractor materialised it.  Wall printed."""
import glob, os, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
T0 = time.time()
KIT = Path(__file__).resolve().parents[5]
PREFIX = "75604b0a432fdc89_00000079--a1f5d2a272"
SCHEMA = KIT / "_scratch" / "cereal_fork_dom_2712e1336"
OUT = KIT / "analysis-2020accord" / "_scratch" / "v299_fork"


def seg(p):
    import capnp, zstandard
    capnp.remove_import_hook()
    log = capnp.load(str(SCHEMA / "log.capnp"), imports=[str(SCHEMA), str(SCHEMA / "include")])
    with open(p, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    f1ab, tev = [], []
    for evt in log.Event.read_multiple_bytes(data):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        t = evt.logMonoTime
        bus1 = False
        for m in evt.can:
            if m.src != 1:
                continue
            bus1 = True
            if m.address == 0x1AB:
                d = bytes(m.dat)
                f1ab.append((t, len(d)) + tuple(d[:3]) + (0,) * (3 - min(3, len(d))))
        if bus1:
            tev.append(t)
    return int(os.path.basename(p).split("--")[2]), f1ab, tev


if __name__ == "__main__":
    segs = sorted(glob.glob(str(KIT / "analysis-2020accord" / "rlogs" / f"{PREFIX}--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    with Pool(min(16, len(segs))) as pool:
        R = sorted(pool.map(seg, segs))
    A = np.array([r for _, f, _ in R for r in f], dtype=np.int64)
    tev0 = np.array(R[0][2], dtype=np.int64)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "r79_1ab.npz", t_ns=A[:, 0], length=A[:, 1].astype(np.uint8), b=A[:, 2:5].astype(np.uint8),
                        seg0_bus1_event_ns=tev0, segments=np.array([s for s, _, _ in R]))
    print(f"segments {len(segs)}; 0x1AB bus-1 frames {len(A)}; lengths {sorted(set(A[:,1].tolist()))}; seg0 bus-1 events {len(tev0)}")
    print(f"wall {time.time() - T0:.1f} s")
