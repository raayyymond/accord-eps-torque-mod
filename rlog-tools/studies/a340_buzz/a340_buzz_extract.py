"""Cache steering CAN + carState for the A340 user route (27da1a2b0cde4a09|00000055--a39019e01a)."""
import sys, os, glob
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from rlog_parse import read_messages

D = sys.argv[1]
OUT = sys.argv[2]
BUS = int(sys.argv[3]) if len(sys.argv) > 3 else 1
import re
SEG = lambda s: int(re.search(r"(\d+)--rlog", os.path.basename(s)).group(1))
IDS = (0xE4, 0x14A, 0x18F, 0x1AB, 0x156)
for p in sorted(glob.glob(os.path.join(D, "*--rlog.zst")), key=SEG):
    seg = SEG(p)
    can = {i: [] for i in IDS}
    cs, cc = [], []
    fw = None
    t0 = None
    for e in read_messages(p):
        try:
            w = e.which()
        except Exception:
            continue
        t = e.logMonoTime * 1e-9
        if t0 is None:
            t0 = t
        if w == "can":
            for m in e.can:
                if m.src == BUS and m.address in can:
                    can[m.address].append((t, bytes(m.dat).ljust(8, b"\0")[:8]))
        elif w == "carState":
            c = e.carState
            cs.append((t, c.vEgo, c.steeringAngleDeg, c.steeringRateDeg, c.steeringTorque, c.steeringTorqueEps,
                       float(c.steeringPressed), float(c.cruiseState.enabled)))
        elif w == "carControl":
            c = e.carControl
            cc.append((t, float(c.latActive), c.actuators.torque, c.actuators.steeringAngleDeg))
        elif w == "carParams" and fw is None:
            fw = [(f.ecu.raw, hex(f.address), bytes(f.fwVersion)) for f in e.carParams.carFw]
    sv = {"t0": t0, "cs": np.array(cs), "cc": np.array(cc)}
    for i in IDS:
        sv["t_%x" % i] = np.array([x[0] for x in can[i]])
        sv["d_%x" % i] = np.frombuffer(b"".join(x[1] for x in can[i]), dtype=np.uint8).reshape(-1, 8)
    np.savez(os.path.join(OUT, "seg%02d.npz" % seg), **sv)
    print(seg, {hex(i): len(can[i]) for i in IDS}, len(cs), len(cc))
    if fw:
        for f in fw:
            if b"39990" in f[2] or f[0] in (0, 1):
                print("   FW", f)
