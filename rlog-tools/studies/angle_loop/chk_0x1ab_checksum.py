# -*- coding: utf-8 -*-
r"""chk_0x1ab_checksum.py -- TWO WIRE IDENTITIES THE V299 READ RESTS ON, recomputed on a route's raw frames.

    python rlog-tools/studies/angle_loop/chk_0x1ab_checksum.py [<dongle_counter--hash prefix>]   (default route 79; ~3 s)

ANALYSIS ONLY.  Reads rlogs and the kit's wire cache; writes nothing; sends nothing.

(1) THE 0x1AB CHECKSUM.  Every raw 0x1AB frame (all buses) is decoded from the route's rlogs (the kit's cereal; one
    process per segment) and checked against opendbc's OWN honda_checksum, compiled VERBATIM by ast from the V299 fork
    commit's opendbc_repo/opendbc/car/honda/hondacan.py (`git show c6452361e:...`; its source sha16 is printed; the
    only free name, HONDA_CANFD_MVL_CHECKSUM_IDS, matters for extended ids only and is bound to an empty set).  The
    fork's parser (carstate.py accord_eps_torque_s10) rejects a frame unless len == 3 and honda_checksum(0x1AB, None,
    dat) == dat[2] & 0xF -- this script counts exactly that.  Also printed: the 2-bit counter (byte 2 bits 4-5) steps.
(2) THE 0x18F SIGN.  On the latest 0x18F frame at or before each carState row (the frame carState was parsed from),
    the 0x18F torque word vs carState.steeringTorque: slope, correlation and the exact-equality share.  The reader's
    bar = word x 1.024, so bar = -1.024 x steeringTorque when the word == -steeringTorque.

RESULT ON ROUTE 79 (2026-10-02, EVIDENCE): 61 113 / 61 113 three-byte 0x1AB frames (src 1, the only source) pass the
checksum (100.0000 %), counter steps mod 4 == 1 on 99.99 %; the 0x18F word == -carState.steeringTorque EXACTLY on
100.00 % of 121 383 rows (slope -1.0000 on the word, -1.0240 on bar; corr -0.99999): the 0x18F word is + = RIGHT.
"""
import ast
import glob
import hashlib
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FORK = "C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
FORK_COMMIT = "c6452361e"            # the V299 fork commit (Accord V299: no fork override, EPS torque bar from 0x1AB)
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
R79 = "75604b0a432fdc89_00000079--a1f5d2a272"


def work(p):
    sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
    import zstandard
    from cereal import log as clog
    with open(p, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    out = []
    for evt in clog.Event.read_multiple_bytes(data):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        tm = evt.logMonoTime
        for m in evt.can:
            if m.address == 0x1AB:
                d = bytes(m.dat)
                out.append((tm, m.src, len(d)) + tuple(d[:3]) + (0,) * (3 - min(len(d), 3)))
    return out


def honda_checksum_verbatim():
    src = subprocess.run(["git", "-C", FORK, "show", FORK_COMMIT + ":opendbc_repo/opendbc/car/honda/hondacan.py"],
                         capture_output=True, text=True).stdout
    fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "honda_checksum"][0]
    ns = dict(HONDA_CANFD_MVL_CHECKSUM_IDS=set())
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "hondacan.py", "exec"), ns)
    return ns["honda_checksum"], hashlib.sha256(ast.get_source_segment(src, fn).encode()).hexdigest()[:16]


def main():
    t0 = time.time()
    prefix = sys.argv[1] if len(sys.argv) > 1 else R79
    segs = sorted(glob.glob(os.path.join(RLOGS, prefix + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        raise SystemExit("no segments for " + prefix)
    with Pool(min(16, len(segs))) as pool:
        res = pool.map(work, sorted(segs, key=lambda p: -os.path.getsize(p)), chunksize=1)
    F = np.array(sorted(r for rr in res for r in rr), dtype=np.int64).reshape(-1, 6)
    print("%s: %d segments, %d 0x1AB frames (decode %.1f s)" % (prefix, len(segs), len(F), time.time() - t0))
    hc, sha = honda_checksum_verbatim()
    print("(1) honda_checksum compiled verbatim from fork %s hondacan.py (source sha16 %s)" % (FORK_COMMIT, sha))
    for src in np.unique(F[:, 1]):
        G = F[F[:, 1] == src]
        lens = np.unique(G[:, 2], return_counts=True)
        ok = np.array([hc(0x1AB, None, bytearray([int(a), int(b), int(c)])) == (int(c) & 0xF) for a, b, c in G[:, 3:6]])
        ok &= G[:, 2] == 3
        ctr = (G[:, 5] >> 4) & 3
        print("    src %d: %d frames, lengths %s; the fork parser's test (len 3 and checksum) passes %d / %d (%.4f %%); "
              "counter steps mod 4 == 1 on %.4f %%" % (src, len(G), dict(zip(lens[0].tolist(), lens[1].tolist())),
                                                       int(ok.sum()), len(G), 100.0 * ok.mean(),
                                                       100 * np.mean(((ctr[1:] - ctr[:-1]) % 4) == 1)))
    tag = "r%s_%s_al" % (prefix.split("_")[1].split("--")[0].lstrip("0") or "0", prefix.split("--")[1][:6])
    p = os.path.join(CACHE, tag + ".npz")
    if os.path.exists(p):
        Z = np.load(p)
        j = np.searchsorted(Z["t18"], Z["tcs"], side="right") - 1
        m = j >= 0
        x, w = Z["cs_tq"][m], Z["tq"][j[m]]
        print("(2) 0x18F word vs carState.steeringTorque on the frame each row was parsed from (%d rows): slope %.4f "
              "(bar = word x 1.024: %.4f), corr %.5f, word == -steeringTorque exactly on %.2f %%" % (
                  int(m.sum()), np.dot(x, w) / np.dot(x, x), 1.024 * np.dot(x, w) / np.dot(x, x),
                  np.corrcoef(x, w)[0, 1], 100 * np.mean(np.abs(w + x) < 0.5)))
    else:
        print("(2) no wire cache %s: run the drive read once first" % p)
    print("wall %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
