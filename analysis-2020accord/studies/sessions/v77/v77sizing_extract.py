#!/usr/bin/env python3
"""studies/sessions/v77/v77sizing_extract.py -- extract route 65 (**V76**, driven, operator reports grind#1 + micro-
ratcheting still present at creep) to `_scratch/cache/r65/r65.npz`.

Route `75604b0a432fdc89_00000065--ae43aa0f27`, segments 0..10.

THE PROBE ON THIS BUILD (V76, COMBO B) -- CAN 0x14A byte4, bits 7,4,3 only (bits 6,5 STRUCTURALLY
CLEAR, per `builds/v50_v79/build_v76_v38base_tva.py`'s own exhaustive `_check_wire_model`):
    bit7 = |gp-0x6b26| > 448          THE FRICTION-LANE MARGIN (root-cause lane; the DTC-0x1d fix)
    bit4 = gp+0x63fd & 0x2            the mode index (1 of 5 bits only)
    bit3 = gp-0x67fa == 5             ★ THE POSITIVE CONTROL
    bits 6:5 = 0 always (unreachable by construction -- NOT a measurement if seen non-zero)
    bits 2:0 = live STEER_SENSOR_STATUS, preserved

🛑 The spec is RE-READ out of `builds/v50_v79/build_v76_v38base_tva.py` at import time -- see `_assert_probe_spec()`,
which execs the builder's OWN `wire_model()` and checks this file's decode inverts it exhaustively.
Mirrors the discipline `studies/sessions/v74_v75/v74fault_extract.py` and `studies/sessions/v74_v75/v75fault_extract.py` established; if the builder's
spec drifts, this extractor fails loudly rather than silently mis-decoding.

Route-GLOBAL time base: `t` is seconds from the first 0x14A frame of segment 0. `seg` carries the
segment index per sample. (`extract/v77sizing_cache.py` re-splits this into per-segment files with `t`
reset to 0 at each segment, which is the schema `_grind2_lib` / `_r31_common` expect.)

Usage: python studies/sessions/v77/v77sizing_extract.py            # all 11 segments -> _scratch/cache/r65/r65.npz
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[3]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000065--ae43aa0f27"
SEGS = list(range(11))
OUT = Path(os.environ.get("R65_CACHE", ROOT / "_scratch/cache/r65"))

BUILD = "V76"
RWD_NAME = ("39990-TVA,A160-V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd-"
            "0x13000-0x100000.rwd")

# ---- the probe spec, RE-READ from the builder ------------------------------------------------------
PAYLOAD_SHIFT = 3
STATE_EQ = 5
MODEIDX_MASK = 0x2
B26_THRESH = 448
B26_INCLUSIVE = False
W_STATE, W_MODE, W_FRICTION = 1, 2, 16
BIT_STATE5, BIT_MODEIDX, BIT_FRICTION = 3, 4, 7
PROBE_MASK = 0x98        # bits 7,4,3
ILLEGAL_MASK = 0x60      # bits 6,5 -- structurally unreachable
STATUS_MASK = 0x07       # PAYLOAD_KEEP_MASK, chains V76 -> V68 -> V54


def _assert_probe_spec():
    """Re-read the builder's own constants and its own wire model; refuse to run on a drift."""
    src = (HERE / "builds/v50_v79/build_v76_v38base_tva.py").read_text(encoding="utf-8")

    def hexnum(name):
        m = re.search(rf"^{name}\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
        assert m, f"{name} not found in builds/v50_v79/build_v76_v38base_tva.py"
        return int(m.group(1), 16)

    def decnum(name):
        m = re.search(rf"^{name}\s*=\s*([0-9]+)", src, re.M)
        assert m, f"{name} not found in builds/v50_v79/build_v76_v38base_tva.py"
        return int(m.group(1))

    assert decnum("BIT_STATE5") == BIT_STATE5, "BIT_STATE5 drifted"
    assert decnum("BIT_MODEIDX") == BIT_MODEIDX, "BIT_MODEIDX drifted"
    assert decnum("BIT_FRICTION") == BIT_FRICTION, "BIT_FRICTION drifted"
    assert decnum("STATE_EQ") == STATE_EQ, "STATE_EQ drifted"
    assert hexnum("MODEIDX_MASK") == MODEIDX_MASK, "MODEIDX_MASK drifted"
    assert decnum("B26_THRESH") == B26_THRESH, "B26_THRESH drifted"
    m = re.search(r"^B26_INCLUSIVE\s*=\s*(True|False)", src, re.M)
    assert m and (m.group(1) == "True") == B26_INCLUSIVE, "B26_INCLUSIVE drifted"
    m = re.search(r"^W_STATE, W_MODE, W_FRICTION\s*=\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)", src, re.M)
    assert m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (W_STATE, W_MODE, W_FRICTION), \
        "W_STATE/W_MODE/W_FRICTION drifted"
    assert hexnum("PROBE_MASK") == PROBE_MASK, "PROBE_MASK drifted"
    assert hexnum("ILLEGAL_MASK") == ILLEGAL_MASK, "ILLEGAL_MASK drifted"
    assert decnum("PAYLOAD_SHIFT") == PAYLOAD_SHIFT, "PAYLOAD_SHIFT drifted"
    # PAYLOAD_KEEP_MASK chains V76 -> V68 -> V54; resolve at its ROOT, do not trust the comment.
    assert re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*V68\.PAYLOAD_KEEP_MASK", src, re.M), \
        "V76 no longer inherits PAYLOAD_KEEP_MASK from V68"
    v68 = (HERE / "builds/v50_v79/build_v68_tva.py").read_text(encoding="utf-8")
    assert re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*V54\.PAYLOAD_KEEP_MASK", v68, re.M), \
        "V68 no longer inherits PAYLOAD_KEEP_MASK from V54"
    v54 = (HERE / "builds/v50_v79/build_v54_tva.py").read_text(encoding="utf-8")
    m = re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*0x([0-9A-Fa-f]+)", v54, re.M)
    assert m and int(m.group(1), 16) == STATUS_MASK, "PAYLOAD_KEEP_MASK drifted at its root (V54)"
    # ---- exec the builder's OWN wire_model() and check this file's decode inverts it exhaustively
    m = re.search(r"^def wire_model\(.*?(?=^def _check_wire_model)", src, re.M | re.S)
    assert m, "wire_model() not found in builds/v50_v79/build_v76_v38base_tva.py"
    ns = {"STATE_EQ": STATE_EQ, "MODEIDX_MASK": MODEIDX_MASK, "W_MODE": W_MODE,
          "B26_THRESH": B26_THRESH, "B26_INCLUSIVE": B26_INCLUSIVE, "W_FRICTION": W_FRICTION,
          "PAYLOAD_SHIFT": PAYLOAD_SHIFT, "PAYLOAD_KEEP_MASK": STATUS_MASK}
    exec(compile(m.group(0), "builds/v50_v79/build_v76_v38base_tva.py:wire_model", "exec"), ns)
    wire = ns["wire_model"]
    for st in (0, 1, 4, 5, 6, 255):
        for md in (0, 1, 2, 3, 255):
            for v in (0, 1, 447, 448, 449, 511, 0xFFFF, 0xFE01, 0x8000):
                for status in range(8):
                    b = wire(st, md, v, status)
                    assert b & ILLEGAL_MASK == 0, f"payload 0x{b:02X} sets bit6/bit5 -- impossible"
                    signed = v - 0x10000 if v & 0x8000 else v
                    hit = (abs(signed) >= B26_THRESH) if B26_INCLUSIVE else (abs(signed) > B26_THRESH)
                    assert (((b >> BIT_FRICTION) & 1) != 0) == hit, "our bit7 (friction) decode is wrong"
                    assert (((b >> BIT_MODEIDX) & 1) != 0) == bool(md & MODEIDX_MASK), \
                        "our bit4 (mode) decode is wrong"
                    assert (((b >> BIT_STATE5) & 1) != 0) == (st == STATE_EQ), \
                        "our bit3 (state==5) decode is wrong"
                    assert (b & STATUS_MASK) == (status & STATUS_MASK), "our status decode is wrong"
    return True


_assert_probe_spec()

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
KPH_TO_MS = 1.0 / 3.6
SENTINEL = 0x7FFF


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def u16be(d, i):
    return (d[i] << 8) | d[i + 1]


def wheel_speeds_kph(d):
    fl = (d[0] << 7) | (d[1] >> 1)
    fr = ((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)
    rl = ((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)
    rr = ((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)
    return fl * 0.01, fr * 0.01, rl * 0.01, rr * 0.01


def held_last(t_out, t_in, v_in, fill):
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    out = np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)])
    return out.astype(float)


def _grid(t_out, t_in, v_in):
    t_in = np.asarray(t_in, float)
    if not len(t_in):
        return np.full(len(t_out), np.nan)
    return np.interp(t_out, t_in, np.asarray(v_in, float))


def extract(paths):
    rows, events = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    co = {"t": [], "req": [], "can": []}
    a_hw, a_mono, a_v, a_st = [], [], [], []
    g_hw, g_mono, g_v, g_st = [], [], [], []
    census = {}
    seg_of_row = []
    t0 = None
    ud = []
    ps = {"t": [], "fault": [], "safety": [], "ign": []}

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
                    key = (src, addr)
                    c = census.get(key)
                    if c is None:
                        census[key] = [1, tm, tm]
                    else:
                        c[0] += 1
                        c[2] = tm
                    if 0x700 <= addr <= 0x7FF or 0x18DA0000 <= addr <= 0x18DAFFFF:
                        ud.append((tm, src, addr, d.hex()))
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_t.append(tm)
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        raw18_b4.append(d[4])
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
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1],
                                     u16be(d, 0), u16be(d, 2), u16be(d, 5)))
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
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker")):
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
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)
            elif w == "carOutput":
                try:
                    a = evt.carOutput.actuatorsOutput
                    co["t"].append(tm)
                    co["req"].append(float(a.torque))
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
            elif w == "gyroscope":
                try:
                    m = evt.gyroscope
                    try:
                        v, st = list(m.gyroUncalibrated.v), int(m.gyroUncalibrated.status)
                    except Exception:
                        v, st = list(m.gyro.v), int(m.gyro.status)
                    g_hw.append(int(m.timestamp) * 1e-9); g_mono.append(tm)
                    g_v.append(v); g_st.append(st)
                except Exception:
                    pass
            elif w == "pandaStates":
                try:
                    for st in evt.pandaStates:
                        ps["t"].append(tm)
                        ps["fault"].append(float(int(getattr(st, "faultStatus", 0))))
                        ps["safety"].append(float(int(getattr(st, "safetyModel", 0))))
                        ps["ign"].append(float(bool(getattr(st, "ignitionLine", False))))
                except Exception:
                    pass
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm,
                                   bool(getattr(e, "enable", False)),
                                   bool(getattr(e, "softDisable", False)),
                                   bool(getattr(e, "immediateDisable", False)),
                                   bool(getattr(e, "noEntry", False))))
        print(f"  seg {si} done, rows so far {len(rows)}", flush=True)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req", "ang_u16", "rate_u16", "wang_u16"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    d["seg"] = np.array(seg_of_row, float)

    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))
    cot = np.array(co["t"], float) - t0
    d["co_req"] = _grid(d["t"], cot, co["req"])
    d["co_tqcan"] = _grid(d["t"], cot, co["can"])
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)

    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = _grid(d["t"], wst, wsv[:, i] * KPH_TO_MS) if len(wst) else \
            np.full(len(d["t"]), np.nan)

    # ---- V76 COMBO B probe decode -------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["friction_hit"] = (((p >> BIT_FRICTION) & 1) != 0).astype(float)      # bit7
    d["mode_bit1"] = (((p >> BIT_MODEIDX) & 1) != 0).astype(float)         # bit4
    d["state_eq5"] = (((p >> BIT_STATE5) & 1) != 0).astype(float)          # bit3
    d["status"] = (p & STATUS_MASK).astype(float)
    d["bits65_viol"] = ((p & ILLEGAL_MASK) != 0).astype(float)             # MUST be all-zero
    # 0x1AB byte0 bit2 = the firmware's own DTC/fault-active flag, held onto the 0x14A grid.
    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan) \
        if len(r1ab_t) else np.full(len(d["t"]), np.nan)

    # ---- IMU ------------------------------------------------------------------------------------
    a_hw, g_hw = np.array(a_hw, float), np.array(g_hw, float)
    a_mono, g_mono = np.array(a_mono, float), np.array(g_mono, float)
    A = np.array(a_v, float).reshape(-1, 3) if len(a_v) else np.zeros((0, 3))
    G = np.array(g_v, float).reshape(-1, 3) if len(g_v) else np.zeros((0, 3))
    off_a = float(np.median(a_mono - a_hw)) if len(a_hw) else np.nan
    off_g = float(np.median(g_mono - g_hw)) if len(g_hw) else np.nan
    at = (a_hw + off_a - t0) if len(a_hw) else np.zeros(0)
    gt = (g_hw + off_g - t0) if len(g_hw) else np.zeros(0)
    imu = dict(at=at, at_mono=a_mono - t0, ax=A[:, 0], ay=A[:, 1], az=A[:, 2],
               a_status=np.array(a_st, float),
               gt=gt, gt_mono=g_mono - t0, gx=G[:, 0], gy=G[:, 1], gz=G[:, 2],
               g_status=np.array(g_st, float),
               a_hw_off=np.array([off_a]), g_hw_off=np.array([off_g]))
    if len(A):
        means = np.array([A[:, i].mean() for i in range(3)])
        vi = int(np.argmin(np.abs(np.abs(means) - 9.807)))
        vname = ("ax", "ay", "az")[vi]
        d["imu_vert"] = _grid(d["t"], at, A[:, vi])
        print(f"  IMU gravity means ax={means[0]:+.4f} ay={means[1]:+.4f} az={means[2]:+.4f} "
              f"m/s^2  -> VERTICAL = {vname}")
    else:
        d["imu_vert"] = np.full(len(d["t"]), np.nan)

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT / "r65.npz", **d, **imu,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv,
        sc_t=sct, sc_tq_raw=np.array(sc_tq, float), sc_rq_raw=np.array(sc_rq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        ps_t=np.array(ps["t"], float) - t0, ps_fault=np.array(ps["fault"], float),
        ps_safety=np.array(ps["safety"], float), ps_ign=np.array(ps["ign"], float),
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([BUILD]), probe_rwd=np.array([RWD_NAME]))
    (OUT / "r65_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))
    (OUT / "r65_census.json").write_text(json.dumps(
        {f"{s}:{a_:03X}": {"n": c[0], "t0": c[1] - t0, "t1": c[2] - t0}
         for (s, a_), c in sorted(census.items())}, indent=1))
    (OUT / "r65_uds.json").write_text(json.dumps(
        [{"t": tt - t0, "src": s, "addr": f"{a_:X}", "dat": h} for tt, s, a_, h in ud], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad65 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & ILLEGAL_MASK) != 0}
    print(f"\nroute 65: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print("  bits 6/5 (STRUCTURALLY unreachable) set in: " +
          (f"{bad65} -- ⚠⚠ THIS IMAGE IS NOT V76 / spec drifted" if bad65 else "0 frames (clean)"))
    print(f"  friction_hit duty {100 * d['friction_hit'].mean():7.3f}%   "
          f"state_eq5 duty {100 * d['state_eq5'].mean():7.3f}%   "
          f"mode_bit1 duty {100 * d['mode_bit1'].mean():7.3f}%")
    print(f"  events {len(events)}  UDS frames {len(ud)}  0x1AB frames {len(r1ab_t)}  "
          f"dtc_active max {np.nanmax(d['dtc_active']) if len(r1ab_t) else float('nan')}")
    return d


if __name__ == "__main__":
    argv = [int(x) for x in sys.argv[1:] if not x.startswith("--")]
    extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in (argv or SEGS)])
