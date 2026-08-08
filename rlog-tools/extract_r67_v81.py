#!/usr/bin/env python3
"""Extract route 67 (V81) into `_cache_r67x/` with the SCHEMA the grind harness already reads.

Route 67 = V81 = the flown V75 image with exactly two cal reverts (`0xC407E` 850->511, friction
back to stock at 14 sites).  🛑 **The cave/probe is byte-identical to V75's**, so the probe byte
(CAN 0x14A byte4, bits 7:3) is V75's magnitude thermometer on `gp-0x6bd0` plus the `gp-0x6ac2`
back-drive bit -- `decode_v75_probe.py` is the authority for the layout and this file mirrors it.

Field names 0..`imu_vert` are `compare_v75_v76_v80_grind.extract66`'s VERBATIM, so the per-segment
files drop straight into `_grind2_lib.wrecs` / `_r31_common.load` and every cross-build ratio is
computed by the identical code path.  This file only ADDS columns:

    cs_rate    carState.steeringRateDeg      -- the ACHIEVED column rate, openpilot's own view
    cs_brake   carState.brakePressed         -- T5(a): "turning AND braking"
    cs_brakev  carState.brake                -- the analogue pedal
    cs_yaw     carState.yawRate
    cc_curv    carControl.actuators.curvature      -- the DEMAND, in curvature
    cc_ccurv   carControl.currentCurvature
    ct_dcurv   controlsState.desiredCurvature      -- the demand upstream of the actuator
    ct_curv    controlsState.curvature
    damp_nz/thermo_128/thermo_288/thermo_448/thermo/g6ac2   the V75 probe, decoded
    illegal    1.0 where bits 7:3 are OUTSIDE the 10-value thermometer alphabet
    imu_lat    the horizontal IMU axis with the smaller gravity projection

Usage:  python extract_r67_v81.py [seg ...]      (default: all 14)
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

from compare_v75_v76_v80_grind import (GEAR, KMH, _grid, held_last,  # noqa: E402
                                       i16be, wheel_speeds_kph)
from decode_v75_probe import (BIT_BACKDRIVE, BIT_DAMP_NZ, BIT_MAG128,  # noqa: E402
                              BIT_MAG288, BIT_MAG448, LEGAL_PAYLOADS, PROBE_MASK)

ROUTE = "75604b0a432fdc89_00000067--9b3ebbe218"
SEGS = list(range(14))
RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
CACHE = ROOT / "_cache_r67x"
PFX = "r67xs"
LABEL = "V81"
SENTINEL = 0x7FFF


def extract(paths):
    from rlog_parse import read_messages

    rows, seg_of_row = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    sent14 = sent18 = 0
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": [], "rate": [], "brake": [], "brakev": [], "yaw": []}
    cc = {"t": [], "lat": [], "en": [], "req": [], "curv": [], "ccurv": []}
    ct = {"t": [], "dcurv": [], "curv": []}
    co = {"t": [], "req": [], "can": []}
    a_hw, a_mono, a_v, a_st = [], [], [], []
    events = []

    for si, p in enumerate(paths):
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_t.append(tm)
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        raw18_b4.append(d[4])
                        sent18 += ((d[0] << 8) | d[1]) == SENTINEL
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 1 and addr == 0x1AB and len(d) >= 1:
                        raw1ab_t.append(tm)
                        raw1ab_b0.append(d[0])
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                    elif src == 1 and addr == 0x1D0 and len(d) >= 8:
                        ws_t.append(tm)
                        ws_v.append(wheel_speeds_kph(d))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_t.append(tm)
                        raw14_b4.append(d[4])
                        sent14 += ((d[0] << 8) | d[1]) == SENTINEL
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
                        seg_of_row.append(si)
            elif w == "sendcan":
                for m in evt.sendcan:
                    if int(m.src) == 1 and int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            sc_t.append(tm)
                            sc_tq.append(float(i16be(d, 0)))
                            sc_rq.append(float((d[2] >> 7) & 1))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                cs["rate"].append(float(c.steeringRateDeg))
                cs["brakev"].append(float(c.brake))
                cs["yaw"].append(float(c.yawRate))
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker"),
                                ("brake", "brakePressed")):
                    try:
                        cs[k].append(float(bool(getattr(c, attr))))
                    except Exception:
                        cs[k].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                for k, get in (("req", lambda e: e.carControl.actuators.torque),
                               ("curv", lambda e: e.carControl.actuators.curvature),
                               ("ccurv", lambda e: e.carControl.currentCurvature)):
                    try:
                        cc[k].append(float(get(evt)))
                    except Exception:
                        cc[k].append(np.nan)
            elif w == "controlsState":
                ct["t"].append(tm)
                for k, attr in (("dcurv", "desiredCurvature"), ("curv", "curvature")):
                    try:
                        ct[k].append(float(getattr(evt.controlsState, attr)))
                    except Exception:
                        ct[k].append(np.nan)
            elif w == "carOutput":
                try:
                    a = evt.carOutput.actuatorsOutput
                    co["t"].append(tm); co["req"].append(float(a.torque))
                    try:
                        co["can"].append(float(a.torqueOutputCan))
                    except Exception:
                        co["can"].append(np.nan)
                except Exception:
                    pass
            elif w == "accelerometer":
                try:
                    m = evt.accelerometer
                    a_hw.append(int(m.timestamp) * 1e-9); a_mono.append(tm)
                    a_v.append(list(m.acceleration.v)); a_st.append(int(m.acceleration.status))
                except Exception:
                    pass
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        events.append((tm, str(e.name), bool(getattr(e, "enable", False)),
                                       bool(getattr(e, "softDisable", False)),
                                       bool(getattr(e, "immediateDisable", False)),
                                       bool(getattr(e, "noEntry", False))))
                    except Exception:
                        continue
        print(f"  seg {si} done, rows so far {len(rows)}", flush=True)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    d["seg"] = np.array(seg_of_row, float)

    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press", "rate", "brakev", "yaw"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink", "brake"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req", "curv", "ccurv"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))
    ctt = np.array(ct["t"], float) - t0
    for k in ("dcurv", "curv"):
        d["ct_" + k] = _grid(d["t"], ctt, ct[k])
    cot = np.array(co["t"], float) - t0
    d["co_req"] = _grid(d["t"], cot, co["req"])
    d["co_tqcan"] = _grid(d["t"], cot, co["can"])
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)

    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = (_grid(d["t"], wst, wsv[:, i] * KMH) if len(wst)
                        else np.full(len(d["t"]), np.nan))

    # ---- the probe.  🛑 V75's cave, byte-identical on V81 -- see decode_v75_probe.py -------------
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["status"] = (p & 0x07).astype(float)
    d["damp_nz"] = ((p & BIT_DAMP_NZ) != 0).astype(float)
    d["thermo_128"] = ((p & BIT_MAG128) != 0).astype(float)
    d["thermo_288"] = ((p & BIT_MAG288) != 0).astype(float)
    d["thermo_448"] = ((p & BIT_MAG448) != 0).astype(float)
    d["thermo"] = (d["damp_nz"] + d["thermo_128"] + d["thermo_288"] + d["thermo_448"])
    d["g6ac2"] = ((p & BIT_BACKDRIVE) != 0).astype(float)
    d["illegal"] = np.array([0.0 if int(x) in LEGAL_PAYLOADS else 1.0 for x in d["field"]])

    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = (held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan)
                       if len(r1ab_t) else np.full(len(d["t"]), np.nan))

    A = np.array(a_v, float).reshape(-1, 3) if len(a_v) else np.zeros((0, 3))
    if len(A):
        off_a = float(np.median(np.array(a_mono, float) - np.array(a_hw, float)))
        at = np.array(a_hw, float) + off_a - t0
        means = np.array([A[:, i].mean() for i in range(3)])
        vi = int(np.argmin(np.abs(np.abs(means) - 9.807)))
        li = int(np.argmax([abs(means[i]) if i != vi else -1 for i in range(3)]))
        li = [i for i in range(3) if i != vi][0] if li == vi else li
        d["imu_vert"] = _grid(d["t"], at, A[:, vi])
        d["imu_lat"] = _grid(d["t"], at, A[:, li])
        print(f"  IMU gravity means {means} -> vertical = {'xyz'[vi]}, lateral = {'xyz'[li]}")
    else:
        d["imu_vert"] = np.full(len(d["t"]), np.nan)
        d["imu_lat"] = np.full(len(d["t"]), np.nan)

    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE / "r67.npz", **d,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv, sc_t=sct, sc_tq_raw=np.array(sc_tq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        sentinels=np.array([sent14, sent18]),
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([LABEL]))
    (CACHE / "r67_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    print(f"\nroute 67: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print(f"  0x7FFF sentinels: 0x14A {sent14}  0x18F {sent18}")
    print(f"  sstat values: "
          f"{dict(zip(*[x.tolist() for x in np.unique(d['sstat'], return_counts=True)]))}")
    print(f"  latActive {100 * np.mean(d['cc_lat'] > 0.5):.1f}% of {d['t'][-1]:.0f} s")
    print(f"  dtc_active max {np.nanmax(d['dtc_active']) if len(r1ab_t) else float('nan')}")
    return d


PASS_1D = ["t", "ang", "rate_c", "wang", "tq", "rate_f", "sca", "sstat", "slow3", "e4tq", "e4req",
           "cs_v", "cs_eng", "cs_ang", "cs_tq", "cs_press", "cs_gear", "cs_std", "cs_lblink",
           "cs_rblink", "cs_lchg", "cs_rate", "cs_brake", "cs_brakev", "cs_yaw",
           "cc_lat", "cc_en", "cc_req", "cc_curv", "cc_ccurv", "ct_dcurv", "ct_curv",
           "co_req", "co_tqcan", "sc_tq", "sc_req", "ws_fl", "ws_fr", "ws_rl", "ws_rr",
           "dtc_active", "imu_vert", "imu_lat", "probe", "field", "status",
           "damp_nz", "thermo_128", "thermo_288", "thermo_448", "thermo", "g6ac2", "illegal"]


def split():
    """Per-segment files with `t` RESET to 0 -- the schema every `_r*_lib.py` assumes."""
    d = np.load(CACHE / "r67.npz")
    seg = d["seg"]
    census = {}
    for s in np.unique(seg.astype(int)):
        m = seg == s
        if m.sum() < 256:
            print(f"  seg{s}: {int(m.sum())} frames -- SKIPPED")
            continue
        out = {k: d[k][m] for k in PASS_1D if k in d.files}
        out["t"] = out["t"] - out["t"][0]
        out["probe_build"] = np.array([LABEL])
        np.savez_compressed(CACHE / f"{PFX}{s}.npz", **out)
        tt, vv, ll = out["t"], np.abs(out["cs_v"]), out["cc_lat"] > 0.5
        census[int(s)] = dict(n=int(m.sum()), sec=float(tt[-1] - tt[0]),
                              v_mean=float(vv.mean()), v_max=float(vv.max()),
                              lat_frac=float(ll.mean()), eng_sec=float(ll.sum() * 0.01))
        print(f"  seg{s}: n={int(m.sum()):6d} {tt[-1] - tt[0]:6.1f}s  v_mean {vv.mean():5.2f} "
              f"(max {vv.max():5.2f})  engaged {ll.mean() * 100:5.1f}% ({ll.sum() * .01:5.1f}s)")
    (CACHE / "r67_census_seg.json").write_text(json.dumps(census, indent=1))


if __name__ == "__main__":
    argv = [int(x) for x in sys.argv[1:] if x.isdigit()]
    extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in (argv or SEGS)])
    split()
