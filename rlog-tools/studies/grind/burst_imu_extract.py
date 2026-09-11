# -*- coding: utf-8 -*-
"""studies/grind/burst_imu_extract.py -- extend task5_imu_extract.py's IMU pull to the four routes the
BURST-ONSET-TRIGGERS study needs (r39 V282, r5e_v288, r62/r63 V289 rev 1).  Same npz field names as
task5_imu_extract.py so the crosscheck code loads either cache unchanged; ADDS the Honda WHEEL_SPEEDS
frame (0x1D0, four 15-bit wheels at 0.01 kph/LSB) as an independent road-roughness channel.

Cache: rlog-tools/studies/grind/_scratch/imu_<tag>.npz
Run:   python rlog-tools/studies/grind/burst_imu_extract.py r39 r5e_v288 r62_v289 r63_v289
ANALYSIS ONLY: reads rlogs, writes one npz.  Builds nothing, sends nothing.
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

PREFIX = {"r39": "75604b0a432fdc89_00000039--f56039af87",
          "r5e_v288": "75604b0a432fdc89_0000005e--03a9714d78",
          "r62_v289": "75604b0a432fdc89_00000062--1c7daa54e8",
          "r63_v289": "75604b0a432fdc89_00000063--1d4b188022",
          "r35": "75604b0a432fdc89_00000035--580292087d"}


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
    tws, ws = [], []
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
                    elif m.src == 0 and m.address == 0x1D0 and len(d) >= 8:
                        # Honda bosch WHEEL_SPEEDS: 4 x 15-bit big-endian bitfields starting bit 0
                        v = int.from_bytes(d[:8], "big")
                        tws.append(tm)
                        ws.append([(v >> 49) & 0x7FFF, (v >> 34) & 0x7FFF,
                                   (v >> 19) & 0x7FFF, (v >> 4) & 0x7FFF])
        print("  %s done" % os.path.basename(p), flush=True)
    A = lambda x, dt=float: np.asarray(x, dt)                    # noqa: E731
    D = dict(at=A(at), ahw=A(ahw), av=A(av), gt=A(gt), ghw=A(ghw), gv=A(gv),
             t18=A(t18), rate=A(rate), tq=A(tq), sca=A(sca, int), te4=A(te4), req=A(req, int),
             tws=A(tws), ws=A(ws))
    os.makedirs(OUT, exist_ok=True)
    np.savez(os.path.join(OUT, "imu_%s.npz" % tag), **D)
    print("%s: accel %d  gyro %d  0x18F %d  0x1D0 %d" % (tag, len(at), len(gt), len(t18), len(tws)))


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["r39"]):
        f = os.path.join(OUT, "imu_%s.npz" % t)
        if os.path.exists(f):
            print("%s cached" % t); continue
        print("=== %s" % t, flush=True)
        read(t)
