"""Parallel cache build: same fields as a340_buzz_extract.py, one process per segment; skips segments already cached.
usage: a340_buzz_extract_par.py <rlog dir or glob prefix> <cache dir> [bus=1]
Files matched: <dir>/*rlog.zst ; segment number = the integer just before 'rlog' ('--7--rlog.zst' or '7--rlog.zst')."""
import sys, os, glob, re
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

IDS = (0xE4, 0x14A, 0x18F, 0x1AB, 0x156)
SEG = lambda s: int(re.search(r"(\d+)--rlog", os.path.basename(s)).group(1))


def work(args):
    p, out, bus = args
    from rlog_parse import read_messages
    seg = SEG(p)
    fn = os.path.join(out, "seg%02d.npz" % seg)
    if os.path.exists(fn):
        return seg, "cached"
    can = {i: [] for i in IDS}
    cs, cc = [], []
    t0 = None
    fw = None
    try:
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
                    if m.src == bus and m.address in can:
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
    except Exception as ex:
        return seg, "ERR %r" % ex
    sv = {"t0": t0, "cs": np.array(cs), "cc": np.array(cc)}
    for i in IDS:
        sv["t_%x" % i] = np.array([x[0] for x in can[i]])
        sv["d_%x" % i] = np.frombuffer(b"".join(x[1] for x in can[i]), dtype=np.uint8).reshape(-1, 8)
    np.savez(fn, **sv)
    eps = [f for f in (fw or []) if b"39990" in f[2]]
    return seg, "%s %s" % ({hex(i): len(can[i]) for i in IDS}, eps)


if __name__ == "__main__":
    D, OUT = sys.argv[1], sys.argv[2]
    BUS = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(D + "*rlog.zst") if not os.path.isdir(D) else glob.glob(os.path.join(D, "*rlog.zst")), key=SEG)
    with Pool(min(8, os.cpu_count() or 4)) as pool:
        for seg, msg in pool.imap_unordered(work, [(p, OUT, BUS) for p in files]):
            print(seg, msg, flush=True)
