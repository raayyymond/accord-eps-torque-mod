# -*- coding: utf-8 -*-
"""studies/grind/task5_imu_extract.py -- pull the DEVICE IMU (accelerometer + gyroscope, with their
HARDWARE timestamps) alongside the 0x18F rate, for the alias adjudication.

WHY THE IMU IS THE INSTRUMENT: it samples at ~92-104 Hz, a rate that is NOT commensurate with the EPS
frame's 100 Hz.  A component truly at 68-73 Hz folds to 27-32 Hz on a 100 Hz sampler but to a DIFFERENT
band on a ~104 Hz one; a component truly at 27-32 Hz appears at 27-32 Hz on BOTH (it is below both
Nyquists).  So a 27-32 Hz line that is present on 0x18F and coincident on the IMU is REAL; one that is
present on 0x18F and absent on the IMU is either folded or below the IMU's sensitivity -- which is why
this script also carries the 20.3 Hz grind line as the POSITIVE CONTROL for IMU sensitivity.

Cache: rlog-tools/studies/grind/_scratch/imu_<tag>.npz
Run:   python rlog-tools/studies/grind/task5_imu_extract.py r35 r36 r37 r38
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))

PREFIX = {"r34": "75604b0a432fdc89_00000034--a1a7e1b8a2",
          "r35": "75604b0a432fdc89_00000035--580292087d",
          "r36": "75604b0a432fdc89_00000036--f4be1a18e9",
          "r37": "75604b0a432fdc89_00000037--4a79da5d18",
          "r38": "75604b0a432fdc89_00000038--f77bddf4bd"}


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def read(tag):
    import zstandard
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, PREFIX[tag] + "--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    at, ahw, av = [], [], []
    gt, ghw, gv = [], [], []
    t18, rate, tq, sca = [], [], [], []
    te4, req = [], []
    for p in segs:
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                print("  truncated: %s" % str(e)[:50]); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "accelerometer":
                try:
                    m = evt.accelerometer
                    at.append(tm); ahw.append(int(m.timestamp) * 1e-9); av.append(list(m.acceleration.v))
                except Exception:
                    pass
            elif w == "gyroscope":
                try:
                    m = evt.gyroscope
                    gt.append(tm); ghw.append(int(m.timestamp) * 1e-9); gv.append(list(m.gyroUncalibrated.v))
                except Exception:
                    try:
                        gt.append(tm); ghw.append(int(evt.gyroscope.timestamp) * 1e-9)
                        gv.append(list(evt.gyroscope.gyro.v))
                    except Exception:
                        gt.pop(); ghw.pop()
            elif w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    if m.src == 1 and m.address == 0x18F and len(d) >= 5:
                        t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2))
                        sca.append((d[4] >> 3) & 1)
                    elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); req.append((d[2] >> 7) & 1)
        print("  %s done" % os.path.basename(p), flush=True)
    A = lambda x, dt=float: np.asarray(x, dt)                    # noqa: E731
    D = dict(at=A(at), ahw=A(ahw), av=A(av), gt=A(gt), ghw=A(ghw), gv=A(gv),
             t18=A(t18), rate=A(rate), tq=A(tq), sca=A(sca, int), te4=A(te4), req=A(req, int))
    os.makedirs(OUT, exist_ok=True)
    np.savez(os.path.join(OUT, "imu_%s.npz" % tag), **D)
    print("%s: accel %d  gyro %d  0x18F %d" % (tag, len(at), len(gt), len(t18)))


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["r36"]):
        f = os.path.join(OUT, "imu_%s.npz" % t)
        if os.path.exists(f):
            print("%s cached" % t); continue
        print("=== %s" % t, flush=True)
        read(t)
