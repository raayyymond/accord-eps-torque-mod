#!/usr/bin/env python3
"""extract_imu_cache.py -- pull the comma device's IMU onto its OWN native grid.

The comma's LSM6DS3TR-C is PHYSICALLY INDEPENDENT of the EPS. Everything this kit has measured so
far came off the EPS's own CAN channels, so an IMU confirmation cannot be an artefact of EPS signal
processing, a decode error, or the torsion-bar channel's scaling.

🛑 NATIVE GRID, NOT THE CAN GRID. The whole point is that the IMU samples at a DIFFERENT rate from
the 0x14A/0x18F CAN grid, so resampling onto 100 Hz would destroy exactly the property being tested.
The sample clock used here is the sensor's own hardware `timestamp` (ns, sensor boot clock), not
logMonoTime -- logMonoTime is the time the log DAEMON saw the packet and carries scheduler jitter.
Both are stored; the offset between them is reported so the two clocks can be checked against each
other rather than assumed equal.

⚠ accelerometer and gyroscope come out of ONE FIFO and share a timestamp, so they are one 6-axis
sample, not two independent streams.

Time base: `t` is seconds relative to the SAME t0 the CAN cache used (read from `t0_mono` in the
matching .npz), so IMU time and CAN time are directly comparable window-for-window.

Usage:  python extract_imu_cache.py r3a 0 1 2   |   python extract_imu_cache.py r3b
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {"r3a": "75604b0a432fdc89_0000003a--4e55c1e0f4",
          "r3b": "75604b0a432fdc89_0000003b--a4a7f4dbf1",
          "r47": "75604b0a432fdc89_00000047--3e0b6134c0",
          "r2b": "75604b0a432fdc89_0000002b--7926e8f7e5",
          "r2c": "75604b0a432fdc89_0000002c--eb219f392c",
          "r37": "75604b0a432fdc89_00000037--6231e33f3d"}
# r2c/r37 segment lists are SPARSE (some segments were never pulled), so NSEG is the highest index
# plus one and a missing rlog is skipped rather than fatal.
NSEG = {"r3a": 7, "r3b": 14, "r47": 26, "r2b": 14, "r2c": 13, "r37": 15}


def recover_t0(path):
    """t=0 for caches written before `t0_mono` was stored (route 2b).

    The old extractors set t=0 at the first src-1 0x14A arrival, so that is reproduced here by
    re-reading the rlog. ⚠ If a pre-0x18F frame was dropped by the newer convention this can be off
    by ONE frame (~10 ms) -- irrelevant for a band envelope over multi-second episodes, but the
    alignment is CHECKED in analyze_r47_imu.sec_align rather than assumed.
    """
    for evt in read_messages(path):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        for m in evt.can:
            if int(m.src) == 1 and int(m.address) == 0x14A:
                return evt.logMonoTime * 1e-9
    return None


def extract(tag, s):
    path = RLOGDIR / f"{ROUTES[tag]}--{s}--rlog.zst"
    out = ROOT / f"_cache_{tag}"
    z = np.load(out / f"{tag}s{s}.npz")
    if "t0_mono" in z.files:
        t0 = float(z["t0_mono"][0])                            # the CAN cache's t=0
    else:
        t0 = recover_t0(path)
        if t0 is None:
            print(f"{tag}s{s}: no 0x14A src1 frame -- SKIPPED")
            return None

    a_hw, a_mono, a_v, a_st = [], [], [], []
    g_hw, g_mono, g_v, g_st = [], [], [], []
    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "accelerometer":
            m = evt.accelerometer
            a_hw.append(int(m.timestamp) * 1e-9)
            a_mono.append(evt.logMonoTime * 1e-9)
            a_v.append(list(m.acceleration.v))
            a_st.append(int(m.acceleration.status))
        elif w == "gyroscope":
            m = evt.gyroscope
            g_hw.append(int(m.timestamp) * 1e-9)
            g_mono.append(evt.logMonoTime * 1e-9)
            # `gyroUncalibrated` is the populated field on this fork; `gyro` is empty.
            try:
                v = list(m.gyroUncalibrated.v)
                st = int(m.gyroUncalibrated.status)
            except Exception:
                v, st = list(m.gyro.v), int(m.gyro.status)
            g_v.append(v)
            g_st.append(st)

    a_hw, g_hw = np.array(a_hw), np.array(g_hw)
    a_mono, g_mono = np.array(a_mono), np.array(g_mono)
    A, G = np.array(a_v, float), np.array(g_v, float)

    # hardware clock -> the CAN time base, via the median offset against logMonoTime
    off_a = float(np.median(a_mono - a_hw)) if len(a_hw) else np.nan
    off_g = float(np.median(g_mono - g_hw)) if len(g_hw) else np.nan
    d = dict(
        at=a_hw + off_a - t0, at_mono=a_mono - t0, ax=A[:, 0], ay=A[:, 1], az=A[:, 2],
        a_status=np.array(a_st, float),
        gt=g_hw + off_g - t0, gt_mono=g_mono - t0, gx=G[:, 0], gy=G[:, 1], gz=G[:, 2],
        g_status=np.array(g_st, float),
        a_hw_off=np.array([off_a]), g_hw_off=np.array([off_g]),
        a_off_sd=np.array([float(np.std(a_mono - a_hw))]),
        g_off_sd=np.array([float(np.std(g_mono - g_hw))]),
        t0_mono=np.array([t0]))
    np.savez_compressed(out / f"{tag}s{s}_imu.npz", **d)

    da, dg = np.diff(a_hw), np.diff(g_hw)
    print(f"{tag}s{s}: accel {len(a_hw):5d}  gyro {len(g_hw):5d} | "
          f"accel dt mean {1e3 * da.mean():.4f} ms -> {1 / da.mean():8.4f} Hz  "
          f"sd {1e3 * da.std():.4f} ms  med {1e3 * np.median(da):.4f} ms | "
          f"gyro {1 / dg.mean():8.4f} Hz sd {1e3 * dg.std():.4f} ms")
    return 1 / da.mean(), 1 / dg.mean(), da, dg


if __name__ == "__main__":
    tag = sys.argv[1]
    segl = sys.argv[2:] or [str(i) for i in range(NSEG[tag])]
    fa, fg, DA, DG = [], [], [], []
    for s in segl:
        r = extract(tag, s)
        if r is None:
            continue
        a, g, da, dg = r
        fa.append(a); fg.append(g); DA.append(da); DG.append(dg)
    DA, DG = np.concatenate(DA), np.concatenate(DG)
    print(f"\n{tag.upper()} ROUTE-WIDE IMU SAMPLE RATE (hardware timestamps, {len(DA) + 1} samples)")
    print(f"   accel: mean {1 / DA.mean():.4f} Hz   from median dt {1 / np.median(DA):.4f} Hz")
    print(f"          dt mean {1e3 * DA.mean():.4f} ms  sd {1e3 * DA.std():.4f} ms  "
          f"p1 {1e3 * np.percentile(DA, 1):.4f}  p99 {1e3 * np.percentile(DA, 99):.4f}")
    print(f"          per-segment rates: {[round(x, 4) for x in fa]}")
    print(f"          spread across segments: {max(fa) - min(fa):.5f} Hz")
    print(f"   gyro : mean {1 / DG.mean():.4f} Hz   from median dt {1 / np.median(DG):.4f} Hz")
    print(f"          dt sd {1e3 * DG.std():.4f} ms  per-segment: {[round(x, 4) for x in fg]}")
    print(f"   dt histogram (accel, ms): "
          + "  ".join(f"{v:.3f}x{c}" for v, c in
                      sorted(zip(*np.unique(np.round(DA * 1e3, 3), return_counts=True)),
                             key=lambda q: -q[1])[:6]))
