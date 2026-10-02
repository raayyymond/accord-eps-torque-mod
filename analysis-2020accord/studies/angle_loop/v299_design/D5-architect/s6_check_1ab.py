# -*- coding: utf-8 -*-
r"""s6_check_1ab.py -- D5-architect, V299 design round.  Is V298's 0x1AB (STEER_MOTOR_TORQUE) frame a VALID Honda frame
(checksum nibble + 2-bit counter) on the wire, so that the fork's CANParser could read MOTOR_TORQUE for the torque bar?

ANALYSIS ONLY.  Reads ONE rlog segment of route 79 (V298 flight); sends nothing, flashes nothing, edits nothing.
Checksum = opendbc can/common.cc honda_checksum (nibble sum of the address and every data nibble except the checksum
nibble, s = 8 - s, & 0xF; standard 11-bit id).  Signals from opendbc dbc/generator/honda/_honda_common.dbc
BO_ 427 STEER_MOTOR_TORQUE: 3 EPS -- CONFIG_VALID 7|1, MOTOR_TORQUE 1|10 (Motorola), OUTPUT_DISABLED 22|1,
COUNTER 21|2, CHECKSUM 19|4.
usage: python s6_check_1ab.py [segment]    (wall time printed; ~5-8 s for one segment)
"""
import os
import sys
import time

import numpy as np

t0 = time.time()
REPO = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
SCHEMA_DIR = os.path.join(REPO, "_scratch", "cereal_fork_dom_2712e1336")
RLOGS = os.path.join(REPO, "analysis-2020accord", "rlogs")
SEG = int(sys.argv[1]) if len(sys.argv) > 1 else 6
PATH = os.path.join(RLOGS, "75604b0a432fdc89_00000079--a1f5d2a272--%d--rlog.zst" % SEG)


def honda_checksum(addr, d):
    s = 0
    a = addr
    while a:
        s += a & 0xF
        a >>= 4
    for i, x in enumerate(d):
        if i == len(d) - 1:
            x >>= 4
        s += (x & 0xF) + (x >> 4)
    return (8 - s) & 0xF


import capnp  # noqa: E402
import zstandard  # noqa: E402

capnp.remove_import_hook()
LOG = capnp.load(os.path.join(SCHEMA_DIR, "log.capnp"))
data = zstandard.ZstdDecompressor().stream_reader(open(PATH, "rb")).read()
rows = []          # (t, src, b0, b1, b2)
e4 = []            # (t, src, req)
for ev in LOG.Event.read_multiple_bytes(data):
    try:
        w = ev.which()
    except Exception:
        continue
    if w != "can":
        continue
    t = ev.logMonoTime * 1e-9
    for m in ev.can:
        if m.address == 0x1AB:
            d = bytes(m.dat)
            if len(d) >= 3:
                rows.append((t, m.src, d[0], d[1], d[2]))
        elif m.address == 0xE4 and m.src == 129:
            d = bytes(m.dat)
            e4.append((t, (d[2] >> 7) & 1))
R = np.array(rows, dtype=float)
print("segment %d: %d 0x1AB frames, src values %s" % (SEG, len(R), sorted(set(R[:, 1].astype(int).tolist()))))
for src in sorted(set(R[:, 1].astype(int).tolist())):
    Q = R[R[:, 1] == src]
    b = Q[:, 2:5].astype(int)
    ck = np.array([honda_checksum(0x1AB, bytes(r.tolist())) for r in b])
    ok = (ck == (b[:, 2] & 0xF))
    cnt = (b[:, 2] >> 4) & 3
    dc = (np.diff(cnt) % 4)
    tq10 = ((b[:, 0] & 3) << 8) | b[:, 1]
    sgn = np.where(tq10 & 0x200, -1, 1)
    mag = tq10 & 0x1FF
    # engaged split: nearest fork 0xE4 request bit
    E = np.array(e4)
    j = np.clip(np.searchsorted(E[:, 0], Q[:, 0]) - 1, 0, len(E) - 1)
    req = E[j, 1] > 0.5
    print("  src %d: n %d  checksum valid %.4f (engaged %.4f, n_eng %d)  counter step==1 %.4f  "
          "CONFIG_VALID=1 %.3f  OUTPUT_DISABLED=1 %.3f  |field| max %d (engaged p99 %.0f)"
          % (src, len(Q), ok.mean(), ok[req].mean() if req.any() else float("nan"), int(req.sum()),
             (dc == 1).mean(), ((b[:, 0] >> 7) & 1).mean(), ((b[:, 2] >> 6) & 1).mean(), mag.max(),
             np.percentile(mag[req], 99) if req.any() else -1))
    bad = np.flatnonzero(~ok)[:5]
    for k in bad:
        print("    bad frame t=%.3f bytes %02x %02x %02x  computed ck %x" % (Q[k, 0], *b[k], ck[k]))
print("wall %.1f s" % (time.time() - t0))
