#!/usr/bin/env python3
r"""Extract the WHOLE rlog corpus into a lean 20 Hz kinematics cache for the STEERING-RATIO
measurement (`analysis-2020accord/_scratch/cache/ratio/`).

🛑 THIS IS NOT A PROBE CACHE.  It deliberately does NOT touch the 0x14A cave bytes, so the
`raw14` off-by-one trap cannot apply here: every field on the output grid is produced by
`np.interp` / hold-last from its OWN source timebase onto ONE uniform grid.  There is no
`(t, probe)` pairing to get wrong.

WHAT IT TAPS
    carState        (~100 Hz)  vEgo, steeringAngleDeg, steeringRateDeg, steeringPressed,
                               standstill, gearShifter, brakePressed, yawRate
                               🛑 carState.yawRate is IDENTICALLY ZERO on this car (Honda's
                               carState never fills it) -- kept only to prove that.
    carControl      (~100 Hz)  latActive          <- THE engagement key (NOT cruiseState)
    livePose        (20 Hz)    angularVelocityDevice.{x,y,z} + valid, velocityDevice.x
                               => METHOD A's yaw rate (calibrated device frame, rad/s)
    gyroscope       (~104 Hz)  raw 3-axis, device/sensor frame => independent IMU cross-check
    CAN 0x1D0 src1  (~50 Hz)   4 wheel speeds  => METHOD B's yaw rate
    liveParameters  (20 Hz)    angleOffsetDeg, angleOffsetAverageDeg, steerRatio, stiffness, roll
                               => openpilot's OWN learned angle offset / steer ratio, as a
                               comparison for our fitted centre offset.  NOT used in the estimate.

SIGN CONVENTION (operator-confirmed, 2026-08-13): negative steering angle = RIGHT turn.
Nothing here flips any sign; `ang` is carState.steeringAngleDeg verbatim, `avz` is livePose's
z verbatim.  The relative sign of the two is MEASURED downstream, not assumed.

Usage:
    python decode/extract_ratio_corpus.py              # all routes, 8 workers
    python decode/extract_ratio_corpus.py 73 80 82     # named routes only
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, str(HERE))

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
OUTDIR = ROOT / "analysis-2020accord" / "_scratch/cache/ratio"
DT = 0.05                      # 20 Hz analysis grid == livePose's own rate
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]


def wheel_speeds_kph(d):
    """0x1D0 WHEEL_SPEEDS -- verbatim from compare_v75_v76_v80_grind.wheel_speeds_kph."""
    fl = (d[0] << 7) | (d[1] >> 1)
    fr = ((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)
    rl = ((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)
    rr = ((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)
    return fl * 0.01, fr * 0.01, rl * 0.01, rr * 0.01


def _held(t_out, t_in, v_in, fill=0.0):
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in, float), t_out, side="right") - 1
    return np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)]).astype(float)


def _interp(t_out, t_in, v_in):
    if len(t_in) < 2:
        return np.full(len(t_out), np.nan)
    return np.interp(t_out, np.asarray(t_in, float), np.asarray(v_in, float))


def extract_segment(path):
    """Parse ONE rlog.zst -> dict of 20 Hz arrays on that segment's own monotonic clock."""
    import rlog_parse

    cs = {k: [] for k in ("t", "v", "ang", "rate", "press", "std", "gear", "brake", "yaw")}
    cc = {"t": [], "lat": [], "en": []}
    lp = {"t": [], "avx": [], "avy": [], "avz": [], "valid": [], "vx": [], "zstd": []}
    gy = {"t": [], "x": [], "y": [], "z": []}
    ws = {"t": [], "fl": [], "fr": [], "rl": [], "rr": []}
    par = {"t": [], "off": [], "offavg": [], "sr": [], "stiff": [], "roll": [], "valid": []}

    for evt in rlog_parse.read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        if w == "carState":
            c = evt.carState
            cs["t"].append(tm)
            cs["v"].append(float(c.vEgo))
            cs["ang"].append(float(c.steeringAngleDeg))
            cs["rate"].append(float(c.steeringRateDeg))
            cs["yaw"].append(float(c.yawRate))
            cs["press"].append(float(bool(c.steeringPressed)))
            cs["std"].append(float(bool(c.standstill)))
            cs["brake"].append(float(bool(c.brakePressed)))
            try:
                cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
            except Exception:
                cs["gear"].append(0.0)
        elif w == "carControl":
            cc["t"].append(tm)
            cc["lat"].append(float(bool(evt.carControl.latActive)))
            cc["en"].append(float(bool(evt.carControl.enabled)))
        elif w == "livePose":
            q = evt.livePose
            a, vd = q.angularVelocityDevice, q.velocityDevice
            lp["t"].append(tm)
            lp["avx"].append(float(a.x)); lp["avy"].append(float(a.y)); lp["avz"].append(float(a.z))
            lp["zstd"].append(float(a.zStd))
            lp["valid"].append(float(bool(a.valid) and bool(q.inputsOK) and bool(q.sensorsOK)))
            lp["vx"].append(float(vd.x))
        elif w == "gyroscope":
            try:
                v = list(evt.gyroscope.gyroUncalibrated.v)
            except Exception:
                try:
                    v = list(evt.gyroscope.gyro.v)
                except Exception:
                    continue
            if len(v) >= 3:
                gy["t"].append(tm); gy["x"].append(v[0]); gy["y"].append(v[1]); gy["z"].append(v[2])
        elif w == "liveParameters":
            q = evt.liveParameters
            par["t"].append(tm)
            par["off"].append(float(q.angleOffsetDeg))
            par["offavg"].append(float(q.angleOffsetAverageDeg))
            par["sr"].append(float(q.steerRatio))
            par["stiff"].append(float(q.stiffnessFactor))
            par["roll"].append(float(getattr(q, "roll", np.nan)))
            par["valid"].append(float(bool(q.valid)))
        elif w == "can":
            for m in evt.can:
                if int(m.address) == 0x1D0 and int(m.src) == 1:
                    d = bytes(m.dat)
                    if len(d) >= 8:
                        f, fr, rl, rr = wheel_speeds_kph(d)
                        ws["t"].append(tm)
                        ws["fl"].append(f); ws["fr"].append(fr)
                        ws["rl"].append(rl); ws["rr"].append(rr)

    if len(cs["t"]) < 20 or len(lp["t"]) < 20:
        return None

    t_lo = max(cs["t"][0], lp["t"][0])
    t_hi = min(cs["t"][-1], lp["t"][-1])
    if t_hi - t_lo < 5.0:
        return None
    grid = np.arange(t_lo, t_hi, DT)

    out = {"t_mono": grid.astype(np.float64)}
    for k in ("v", "ang", "rate", "yaw"):
        out[k] = _interp(grid, cs["t"], cs[k]).astype(np.float32)
    for k in ("press", "std", "brake", "gear"):
        out[k] = _held(grid, cs["t"], cs[k]).astype(np.float32)
    for k in ("lat", "en"):
        out[k] = _held(grid, cc["t"], cc[k]).astype(np.float32)
    for k in ("avx", "avy", "avz", "vx", "zstd"):
        out[k] = _interp(grid, lp["t"], lp[k]).astype(np.float32)
    out["lp_valid"] = _held(grid, lp["t"], lp["valid"]).astype(np.float32)
    for k in ("x", "y", "z"):
        out["gy_" + k] = _interp(grid, gy["t"], gy[k]).astype(np.float32)
    for k in ("fl", "fr", "rl", "rr"):
        # km/h on the wire -> m/s on the grid
        out["ws_" + k] = (_interp(grid, ws["t"], ws[k]) / 3.6).astype(np.float32)
    out["ws_n"] = np.float32(len(ws["t"]))
    for k in ("off", "offavg", "sr", "stiff", "roll", "valid"):
        out["par_" + k] = _interp(grid, par["t"], par[k]).astype(np.float32)
    return out


def _one(args):
    path, seg = args
    try:
        d = extract_segment(path)
    except Exception as e:  # a truncated tail segment must not kill the route
        return seg, None, f"{type(e).__name__}: {e}"
    return seg, d, None


def extract_route(route, workers=8):
    files = sorted(RLOGDIR.glob(f"*_{route}--*--rlog.zst"),
                   key=lambda p: int(p.name.split("--")[2]))
    if not files:
        return None
    jobs = [(str(p), int(p.name.split("--")[2])) for p in files]
    parts = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for seg, d, err in ex.map(_one, jobs):
            if err:
                print(f"    route {route} seg {seg}: {err}", flush=True)
            elif d is not None:
                d["seg"] = np.full(len(d["t_mono"]), seg, np.float32)
                parts.append((seg, d))
    if not parts:
        return None
    parts.sort(key=lambda x: x[0])
    keys = [k for k in parts[0][1] if k != "ws_n"]
    merged = {k: np.concatenate([p[1][k] for p in parts]) for k in keys}
    merged["t"] = (merged["t_mono"] - merged["t_mono"][0]).astype(np.float64)
    merged["ws_n"] = np.array([p[1]["ws_n"] for p in parts], np.float32)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUTDIR / f"{route}.npz", **merged)
    return merged


def all_routes():
    seen = []
    for p in sorted(RLOGDIR.glob("*--rlog.zst")):
        r = p.name.split("--")[0].split("_")[-1]
        if r not in seen:
            seen.append(r)
    return seen


if __name__ == "__main__":
    todo = sys.argv[1:] or all_routes()
    print(f"{len(todo)} routes: {' '.join(todo)}")
    for r in todo:
        f = OUTDIR / f"{r}.npz"
        if f.exists():
            print(f"  {r}: cached")
            continue
        t0 = time.time()
        m = extract_route(r)
        if m is None:
            print(f"  {r}: NO USABLE SEGMENTS", flush=True)
        else:
            n = len(m["t"])
            print(f"  {r}: {n:,} rows  {n * DT / 60:.1f} min  "
                  f"v<={np.nanmax(m['v']):.1f} m/s  |ang|<={np.nanmax(np.abs(m['ang'])):.0f} deg  "
                  f"lat {np.nanmean(m['lat']):.3f}  ({time.time() - t0:.0f} s)", flush=True)
