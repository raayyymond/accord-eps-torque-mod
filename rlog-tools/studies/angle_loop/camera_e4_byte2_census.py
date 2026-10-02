# -*- coding: utf-8 -*-
r"""camera_e4_byte2_census.py -- census of 0xE4 (STEERING_CONTROL) byte 2 over EVERY cached rlog segment.

    python rlog-tools/studies/angle_loop/camera_e4_byte2_census.py [--rlogs DIR] [--jobs N] [--json PATH]

ANALYSIS ONLY.  Reads rlog.zst files; writes one JSON under _scratch/out/.  Sends nothing, flashes nothing.

WHY.  V298 gates the EPS LKAS lane on gp-0x6803 == 2, where gp-0x6803 = 0xE4 byte 2 bits 3:2 (FUN_00052676 handler:
`shl 0x1c` @0x526E6, `shr 0x1e` @0x526F6 -- LOGICAL shift, so the stored value is the unsigned 2-bit field 0..3).
The interlock is fail-safe against the stock camera only if the camera NEVER emits bits 3:2 == 2.  This script
counts that field per route and pooled, split strictly BY BUS (CanData.src), never by content.

BUS MAP on this car (Honda Bosch with radar, openpilot longitudinal; fork opendbc/car/honda/hondacan.py CanBus):
    src 0   = ACC-CAN, radar side            src 1   = F-CAN B, powertrain (the EPS is here)
    src 2   = ACC-CAN, CAMERA side  <- TARGET  src 128/129/130 = panda TX echo of bus 0/1/2
    sendcan bus 1 = openpilot's OWN 0xE4 (CAN.lkas = CAN.pt = 1 when openpilotLongitudinalControl)
openpilot's frames are excluded from the camera census by bus: they are never on src 2.

DBC (fork _steering_control_d_ext.dbc, imported by honda_accord_2017_can_ext; = _steering_control_a.dbc):
    STEER_TORQUE 7|16@0-  -> bytes 0-1 big-endian signed
    STEER_TORQUE_REQUEST 23|1@0+ -> byte 2 bit 7
    SET_ME_X00 22|7@0+  -> byte 2 bits 6:0   (bits 3:2 = the gp-0x6803 field)
  _bosch_2018.dbc names DRIVER_OVERRIDE 17|1 (byte 2 bit 1) and CONTROL_STATE 26|3 (byte 3 bits 2:0) -- both
  also tallied, for reference only.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# ---- PATH BOOTSTRAP: walk up to the kit root (.pkgroot) and import rlog-tools/lib ----
_here = Path(__file__).resolve()
_root = next(p for p in _here.parents if (p / ".pkgroot").exists())  # rlog-tools
sys.path.insert(0, str(_root / "lib"))
REPO = _root.parent
DEFAULT_RLOGS = REPO / "analysis-2020accord" / "rlogs"
DEFAULT_JSON = REPO / "_scratch" / "out" / "camera_e4_byte2_census.json"


def _new_bucket():
    return {"n": 0, "f32": [0, 0, 0, 0], "req": [0, 0], "b2lo7": {}, "max_abs_tq": 0, "max_abs_tq_req": 0,
            "req_and_tq": 0, "tq_no_req": 0, "ovr_bit1": [0, 0], "b3_ctl": {}, "dlc": {},
            "f32_eq2_first_t": None, "req_by_f32": {}}


def _add(b, d, t):
    b["n"] += 1
    b["dlc"][len(d)] = b["dlc"].get(len(d), 0) + 1
    if len(d) < 3:
        return
    tq = int.from_bytes(d[0:2], "big", signed=True)          # STEER_TORQUE 7|16@0-
    req = (d[2] >> 7) & 1                                     # STEER_TORQUE_REQUEST 23|1
    f32 = (d[2] >> 2) & 3                                     # gp-0x6803 = (b2 << 28) >>> 30
    b["f32"][f32] += 1
    b["req"][req] += 1
    k = d[2] & 0x7F
    b["b2lo7"][k] = b["b2lo7"].get(k, 0) + 1
    rk = f"{req}/{f32}"
    b["req_by_f32"][rk] = b["req_by_f32"].get(rk, 0) + 1
    b["ovr_bit1"][(d[2] >> 1) & 1] += 1
    if len(d) >= 4:
        c = d[3] & 7
        b["b3_ctl"][c] = b["b3_ctl"].get(c, 0) + 1
    b["max_abs_tq"] = max(b["max_abs_tq"], abs(tq))
    if req:
        b["max_abs_tq_req"] = max(b["max_abs_tq_req"], abs(tq))
        if tq != 0:
            b["req_and_tq"] += 1
    elif tq != 0:
        b["tq_no_req"] += 1
    if f32 == 2 and b["f32_eq2_first_t"] is None:
        b["f32_eq2_first_t"] = t


def scan_segment(path):
    from rlog_parse import read_messages
    out = {"path": os.path.basename(path), "events": 0, "can_events": 0, "error": None, "buckets": {}}
    B = out["buckets"]
    try:
        for e in read_messages(path):
            out["events"] += 1
            try:
                w = e.which()
            except Exception:
                continue                                      # union member unknown to the kit cereal (slot 137 etc.)
            if w == "can":
                out["can_events"] += 1
                t = e.logMonoTime
                for m in e.can:
                    if m.address == 0xE4:
                        key = f"can_src{m.src}"
                        if key not in B:
                            B[key] = _new_bucket()
                        _add(B[key], bytes(m.dat), t)
            elif w == "sendcan":
                t = e.logMonoTime
                for m in e.sendcan:
                    if m.address == 0xE4:
                        key = f"sendcan_bus{m.src}"
                        if key not in B:
                            B[key] = _new_bucket()
                        _add(B[key], bytes(m.dat), t)
    except Exception as ex:                                   # truncated / corrupt file: keep the partial counts
        out["error"] = f"{type(ex).__name__}: {ex}"[:300]
    return out


def _merge(dst, src):
    dst["n"] += src["n"]
    for i in range(4):
        dst["f32"][i] += src["f32"][i]
    for i in range(2):
        dst["req"][i] += src["req"][i]
        dst["ovr_bit1"][i] += src["ovr_bit1"][i]
    for fld in ("b2lo7", "b3_ctl", "dlc", "req_by_f32"):
        for k, v in src[fld].items():
            dst[fld][k] = dst[fld].get(k, 0) + v
    dst["max_abs_tq"] = max(dst["max_abs_tq"], src["max_abs_tq"])
    dst["max_abs_tq_req"] = max(dst["max_abs_tq_req"], src["max_abs_tq_req"])
    dst["req_and_tq"] += src["req_and_tq"]
    dst["tq_no_req"] += src["tq_no_req"]
    if src["f32_eq2_first_t"] is not None and dst["f32_eq2_first_t"] is None:
        dst["f32_eq2_first_t"] = src["f32_eq2_first_t"]


def route_of(fname):
    return "--".join(fname.split("--")[:2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rlogs", default=str(DEFAULT_RLOGS))
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.rlogs, "*--rlog.zst")))
    print(f"segments found: {len(files)} under {a.rlogs}", flush=True)
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        segs = list(ex.map(scan_segment, files, chunksize=4))

    routes = collections.OrderedDict()
    pooled = {}
    for s in segs:
        r = routes.setdefault(route_of(s["path"]), {"segments": 0, "errors": [], "no_can": [], "buckets": {}})
        r["segments"] += 1
        if s["error"]:
            r["errors"].append([s["path"], s["error"], s["events"]])
        if s["can_events"] == 0:
            r["no_can"].append(s["path"])
        for k, b in s["buckets"].items():
            _merge(r["buckets"].setdefault(k, _new_bucket()), b)
            _merge(pooled.setdefault(k, _new_bucket()), b)

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    with open(a.json, "w") as f:
        json.dump({"rlogs": a.rlogs, "segments": len(files), "routes": routes, "pooled": pooled}, f, indent=1,
                  default=str)

    # ---- report ----
    def row(name, b):
        f = b["f32"]
        return (f"{name:<40} n={b['n']:>9}  bits3:2 0/1/2/3 = {f[0]}/{f[1]}/{f[2]}/{f[3]}  req0/1 = "
                f"{b['req'][0]}/{b['req'][1]}  max|tq| {b['max_abs_tq']} (req: {b['max_abs_tq_req']})  "
                f"req&tq!=0 {b['req_and_tq']}  tq!=0&!req {b['tq_no_req']}")
    print("\n=== POOLED ===")
    for k in sorted(pooled):
        print(row(k, pooled[k]))
        print(f"{'':<40} byte2&0x7F: {dict(sorted(pooled[k]['b2lo7'].items()))}  req/f32: "
              f"{dict(sorted(pooled[k]['req_by_f32'].items()))}  byte3&7: {dict(sorted(pooled[k]['b3_ctl'].items()))}"
              f"  dlc: {pooled[k]['dlc']}")
    print("\n=== PER ROUTE (camera = can_src2; openpilot = sendcan_bus1) ===")
    for rn, r in routes.items():
        cam = r["buckets"].get("can_src2", _new_bucket())
        op = r["buckets"].get("sendcan_bus1", _new_bucket())
        f, g = cam["f32"], op["f32"]
        print(f"{rn:<42} seg {r['segments']:>3}  CAM n={cam['n']:>8} f32={f[0]}/{f[1]}/{f[2]}/{f[3]} "
              f"req1={cam['req'][1]} max|tq|={cam['max_abs_tq']}  |  OP n={op['n']:>7} f32={g[0]}/{g[1]}/{g[2]}/{g[3]} "
              f"b2lo7={sorted(op['b2lo7'])}  err={len(r['errors'])} nocan={len(r['no_can'])}")
    cam2 = pooled.get("can_src2", _new_bucket())
    print(f"\nCAMERA bits3:2 == 2 frames, pooled: {cam2['f32'][2]}  (== 3: {cam2['f32'][3]})")
    print(f"routes: {len(routes)}  segments: {len(files)}  segments with errors: "
          f"{sum(len(r['errors']) for r in routes.values())}  JSON: {a.json}")

    # ---- markdown per-route table (pasted into docs/traces/TRACE-2026-10-01-camera-0xE4-byte2-census.md) ----
    print("\n| route | seg | cam frames | cam bits3:2 0/1/2/3 | cam req=1 | cam max\\|tq\\| | cam byte2&0x7F | "
          "OP frames (sendcan b1) | OP bits3:2 0/1/2/3 | OP byte2&0x7F | pre-OP bus-1 frames (field) | errs |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for rn, r in routes.items():
        cam = r["buckets"].get("can_src2", _new_bucket())
        op = r["buckets"].get("sendcan_bus1", _new_bucket())
        b1 = r["buckets"].get("can_src1", _new_bucket())
        f, g = cam["f32"], op["f32"]
        print(f"| `{rn.split('_')[1]}` | {r['segments']} | {cam['n']} | {f[0]}/{f[1]}/**{f[2]}**/{f[3]} | "
              f"{cam['req'][1]} | {cam['max_abs_tq']} | {sorted(int(k) for k in cam['b2lo7'])} | {op['n']} | "
              f"{g[0]}/{g[1]}/{g[2]}/{g[3]} | {sorted(int(k) for k in op['b2lo7'])} | "
              f"{b1['n']} ({'/'.join(map(str, b1['f32']))}) | {len(r['errors'])} |")


if __name__ == "__main__":
    main()
