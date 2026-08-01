#!/usr/bin/env python3
"""Extract the comma device IMU for the CONTROL routes 2c / 31 / 35 and for V62's route 37.

Why this exists: the IMU is physically independent of the EPS -- different sensor, different bus,
different ECU -- so an IMU dose-response over Kd = 0 / 1x / 2x shares no signal path with the thing
being changed. It was previously extracted for the V65 routes only, which made it a confirmation
that the burst is real but useless as a cross-build control. The rlogs for 2c / 31 / 35 are on disk;
nobody had extracted them.

🛑 TIME BASE. The CAN caches for 2c / 31 / 35 do not store `t0_mono` (r2c/r31 have a `mono` key but
it is all 1.0 -- not a timestamp). t0 is therefore RE-DERIVED here with the extractors' own rule:
`t0 = logMonoTime of the first 0x14A src1 frame that follows a 0x18F src1 frame`. That is exactly
`t0 = d["t"][0]` in extract_r35_cache.py. Verified against route 37, whose cache does store
`t0_mono`, so the rule is checked rather than assumed.

🛑 NATIVE GRID. The IMU keeps its own hardware `timestamp`, never resampled to 100 Hz -- the point
is that it samples at a different rate from the CAN grid.

Usage:  python extract_imu_controls.py            # everything
        python extract_imu_controls.py r2c r31
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {
    "r2c": ("75604b0a432fdc89_0000002c--eb219f392c", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    "r31": ("75604b0a432fdc89_00000031--0441e00d2b", [0, 1, 2, 3]),
    "r35": ("75604b0a432fdc89_00000035--77808fe7ce", [0, 1, 2]),
    "r37": ("75604b0a432fdc89_00000037--6231e33f3d", list(range(15))),
}


def extract(tag, s):
    route, _ = ROUTES[tag]
    path = RLOGDIR / f"{route}--{s}--rlog.zst"
    out = ROOT / f"_cache_{tag}"
    if not path.exists():
        print(f"{tag}s{s}: rlog missing")
        return None

    t0 = None
    seen18 = False
    a_hw, a_mono, a_v, a_st = [], [], [], []
    g_hw, g_mono, g_v, g_st = [], [], [], []
    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "can" and t0 is None:
            for m in evt.can:
                if int(m.src) != 1:
                    continue
                a = int(m.address)
                if a == 0x18F:
                    seen18 = True
                elif a == 0x14A and seen18 and len(bytes(m.dat)) >= 7:
                    t0 = evt.logMonoTime * 1e-9
                    break
        elif w == "accelerometer":
            m = evt.accelerometer
            a_hw.append(int(m.timestamp) * 1e-9)
            a_mono.append(evt.logMonoTime * 1e-9)
            a_v.append(list(m.acceleration.v))
            a_st.append(int(m.acceleration.status))
        elif w == "gyroscope":
            m = evt.gyroscope
            g_hw.append(int(m.timestamp) * 1e-9)
            g_mono.append(evt.logMonoTime * 1e-9)
            try:
                v, st = list(m.gyroUncalibrated.v), int(m.gyroUncalibrated.status)
            except Exception:
                v, st = list(m.gyro.v), int(m.gyro.status)
            g_v.append(v)
            g_st.append(st)

    if t0 is None or not len(a_hw):
        print(f"{tag}s{s}: t0={t0} accel={len(a_hw)} -- SKIPPED")
        return None

    # cross-check the re-derived t0 where the CAN cache stores its own
    ref = out / f"{tag}s{s}.npz"
    chk = ""
    if ref.exists():
        z = np.load(ref)
        if "t0_mono" in z:
            chk = f"  [t0 check vs cache: {t0 - float(z['t0_mono'][0]):+.6f} s]"

    a_hw, g_hw = np.array(a_hw), np.array(g_hw)
    a_mono, g_mono = np.array(a_mono), np.array(g_mono)
    A, G = np.array(a_v, float), np.array(g_v, float)
    off_a = float(np.median(a_mono - a_hw))
    off_g = float(np.median(g_mono - g_hw)) if len(g_hw) else np.nan
    d = dict(
        at=a_hw + off_a - t0, at_mono=a_mono - t0, ax=A[:, 0], ay=A[:, 1], az=A[:, 2],
        a_status=np.array(a_st, float),
        gt=(g_hw + off_g - t0) if len(g_hw) else np.array([]), gt_mono=g_mono - t0,
        gx=G[:, 0] if len(G) else np.array([]), gy=G[:, 1] if len(G) else np.array([]),
        gz=G[:, 2] if len(G) else np.array([]), g_status=np.array(g_st, float),
        a_hw_off=np.array([off_a]), g_hw_off=np.array([off_g]),
        a_off_sd=np.array([float(np.std(a_mono - a_hw))]),
        g_off_sd=np.array([float(np.std(g_mono - g_hw))]),
        t0_mono=np.array([t0]))
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"{tag}s{s}_imu.npz", **d)
    da = np.diff(a_hw)
    print(f"{tag}s{s}: accel {len(a_hw):5d} gyro {len(g_hw):5d}  "
          f"{1 / da.mean():8.4f} Hz (median dt {1e3 * np.median(da):.4f} ms, "
          f"sd {1e3 * da.std():.4f} ms){chk}")
    return 1 / da.mean()


if __name__ == "__main__":
    tags = sys.argv[1:] or list(ROUTES)
    for tag in tags:
        rates = []
        for s in ROUTES[tag][1]:
            r = extract(tag, s)
            if r:
                rates.append(r)
        if rates:
            print(f"  {tag}: accel rate {min(rates):.4f}-{max(rates):.4f} Hz "
                  f"over {len(rates)} segments\n")
