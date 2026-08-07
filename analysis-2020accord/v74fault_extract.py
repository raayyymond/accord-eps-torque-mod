#!/usr/bin/env python3
"""v74fault_extract.py -- extract route 61 (the V74 drive that HARD-FAULTED) to `_cache_r61/`.

Route `75604b0a432fdc89_00000061--3b8f2f9278`, segments 0..12.

THE PROBE ON THIS BUILD (V74) -- CAN 0x14A byte4, bits 7:3, a DAMPER-NONZERO BIT + THE STATE:
    bit7     = (*(short *)(gp - 0x6bd0) != 0)   damper output non-zero, SIGNED `ld.h`, two-sided
    bits 6:3 = (*(byte  *)(gp - 0x67fa)) & 0xF  ★ THE ASSIST-CHAIN STATE, zero-extended `ld.bu`
    bits 2:0 = live STEER_SENSOR_STATUS, preserved.
All 32 payloads in 7:3 are *encodable* -- the builder's own `LEGAL_PAYLOADS` is the full cross
product `{(d<<7) | (s<<3)}` over d in (0,1), s in range(16) -- so `illegal` is vacuous BY
CONSTRUCTION on V74 and is kept only to mirror the V75 extractor's column set. The discriminating
column is `state_impossible`: `gp-0x67fa`'s measured literal value set is
    STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
and the builder asserts `0 not in STATE_VALUE_SET`, so **state == 0 means the cave never ran**, and
state in {2, 12, 13, 14, 15} means the wire model or the build identity is wrong.

★ BUILD-IDENTITY DISCRIMINATOR vs V75. V75's byte4 was a THERMOMETER on |gp-0x6bd0| whose only
reachable payloads are {0x00,0x08,0x80,0x88,0xC0,0xC8,0xE0,0xE8,0xF0,0xF8}; read through V74's
decode those map to states {0,1,8,9,12,13,14,15}. V74's state set contains 3,4,5,6,7,10,11 -- which
V75 CANNOT produce -- and excludes 0,12,14,15 -- which V75 produces constantly. The histogram of
raw 0x14A byte4 therefore identifies the build on its own.

🛑 The spec is RE-READ out of `build_v74_tva.py` at import time, not hand-copied -- see
`_assert_probe_spec()`, which also `exec`s the builder's OWN `wire_byte4()` and checks that this
file's decode inverts it exhaustively. If the builder's spec drifts, this extractor fails loudly.

Route-GLOBAL time base: `t` is seconds from the first 0x14A frame of segment 0, so the whole
13-segment drive is one continuous axis. `seg` carries the segment index per sample.

Usage: python v74fault_extract.py            # all 13 segments -> _cache_r61/r61.npz
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000061--3b8f2f9278"
SEGS = list(range(13))
OUT = Path(os.environ.get("R61_CACHE", ROOT / "_cache_r61"))

BUILD = "V74"
RWD_NAME = ("39990-TVA,A160-V74-V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-"
            "frictionx1p5-C407E850-probe-67fa-6bd0nz-0x13000-0x100000.rwd")

# ---- the probe spec, RE-READ from the builder -----------------------------------------------------
STATE_DISP, DAMP_DISP = 0x67FA, 0x6BD0
STATE_MASK = 0xF
W_DAMP_NZ = 0x10                                 # pre-shift weight of the damper-nonzero seed
PAYLOAD_SHIFT = 3
BIT_DAMP_NZ = W_DAMP_NZ << PAYLOAD_SHIFT         # 0x80
STATE_FIELD = STATE_MASK << PAYLOAD_SHIFT        # 0x78 -- bits 6:3
PROBE_MASK = BIT_DAMP_NZ | STATE_FIELD           # 0xF8
STATUS_MASK = 0x07                               # == PAYLOAD_KEEP_MASK, from V54 via V68
STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
LEGAL_PAYLOADS = sorted({(d << 7) | (s << PAYLOAD_SHIFT)
                         for d in (0, 1) for s in range(STATE_MASK + 1)})
# V75's thermometer alphabet -- the ONLY payloads a V75 log can carry in 7:3.
V75_ALPHABET = [0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8]


def _assert_probe_spec():
    """Re-read the builder's own constants and its own wire model; refuse to run on a drift."""
    src = (HERE / "build_v74_tva.py").read_text(encoding="utf-8")

    def hexnum(name):
        m = re.search(rf"^{name}\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
        assert m, f"{name} not found in build_v74_tva.py"
        return int(m.group(1), 16)

    def decnum(name):
        m = re.search(rf"^{name}\s*=\s*([0-9]+)", src, re.M)
        assert m, f"{name} not found in build_v74_tva.py"
        return int(m.group(1))

    assert hexnum("STATE_DISP") == STATE_DISP, "STATE_DISP drifted"
    assert hexnum("DAMP_DISP") == DAMP_DISP, "DAMP_DISP drifted"
    assert hexnum("STATE_MASK") == STATE_MASK, "STATE_MASK drifted"
    assert hexnum("W_DAMP_NZ") == W_DAMP_NZ, "W_DAMP_NZ drifted"
    assert decnum("PAYLOAD_SHIFT") == PAYLOAD_SHIFT, "PAYLOAD_SHIFT drifted"
    for name, expect in (("BIT_DAMP_NZ", "W_DAMP_NZ << PAYLOAD_SHIFT"),
                         ("STATE_FIELD", "STATE_MASK << PAYLOAD_SHIFT"),
                         ("PROBE_MASK", "BIT_DAMP_NZ | STATE_FIELD")):
        m = re.search(rf"^{name}\s*=\s*([^#\n]+)", src, re.M)
        assert m and m.group(1).strip() == expect, f"{name}'s definition drifted"
    # PAYLOAD_KEEP_MASK chains V74 -> V68 -> V54; resolve it at its ROOT, do not trust the comment.
    m = re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*V68\.PAYLOAD_KEEP_MASK", src, re.M)
    assert m, "V74 no longer inherits PAYLOAD_KEEP_MASK from V68"
    v68 = (HERE / "build_v68_tva.py").read_text(encoding="utf-8")
    assert re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*V54\.PAYLOAD_KEEP_MASK", v68, re.M), \
        "V68 no longer inherits PAYLOAD_KEEP_MASK from V54"
    v54 = (HERE / "build_v54_tva.py").read_text(encoding="utf-8")
    m = re.search(r"^PAYLOAD_KEEP_MASK\s*=\s*0x([0-9A-Fa-f]+)", v54, re.M)
    assert m and int(m.group(1), 16) == STATUS_MASK, "PAYLOAD_KEEP_MASK drifted at its root (V54)"
    # the state value set, and the two structural assertions the builder makes about it
    m = re.search(r"^STATE_VALUE_SET\s*=\s*\{([^}]*)\}", src, re.M)
    assert m, "STATE_VALUE_SET not found"
    vs = {int(x) for x in m.group(1).replace(" ", "").split(",") if x}
    assert vs == STATE_VALUE_SET, f"STATE_VALUE_SET drifted: {sorted(vs)}"
    assert 'assert 0 not in STATE_VALUE_SET' in src, "the 0-impossible assertion is gone"
    assert re.search(r"assert len\(LEGAL_PAYLOADS\) == 32", src), "the 32-payload assertion is gone"
    m = re.search(r"^LEGAL_PAYLOADS\s*=\s*\{([^\n]+)\}", src, re.M)
    assert m and m.group(1).strip() == \
        "(d << 7) | (s << PAYLOAD_SHIFT) for d in (0, 1) for s in range(STATE_MASK + 1)", \
        "LEGAL_PAYLOADS' comprehension drifted"
    # ---- exec the builder's OWN wire model and check this file's decode inverts it exhaustively
    m = re.search(r"^def wire_byte4\(.*?(?=^LEGAL_PAYLOADS)", src, re.M | re.S)
    assert m, "wire_byte4() not found in build_v74_tva.py"
    ns = {"W_DAMP_NZ": W_DAMP_NZ, "STATE_MASK": STATE_MASK, "PAYLOAD_SHIFT": PAYLOAD_SHIFT,
          "PAYLOAD_KEEP_MASK": STATUS_MASK}
    exec(compile(m.group(0), "build_v74_tva.py:wire_byte4", "exec"), ns)
    wire = ns["wire_byte4"]
    for st in range(16):
        for v in (0x0000, 0x0001, 0xFFFF, 0x0040, 0xFFC0, 0x7FFF, 0x8000):
            for status in range(8):
                b = wire(v, st, status_bits=status)
                signed = v - 0x10000 if v & 0x8000 else v
                assert (b & PROBE_MASK) in LEGAL_PAYLOADS, f"payload 0x{b:02X} outside LEGAL"
                assert ((b & BIT_DAMP_NZ) != 0) == (signed != 0), "our bit7 decode is wrong"
                assert ((b >> PAYLOAD_SHIFT) & 0xF) == st, "our state decode is wrong"
                assert (b & STATUS_MASK) == status, "our status decode is wrong"
    assert len(LEGAL_PAYLOADS) == 32, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 32"
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


WATCH = (0x14A, 0x18F, 0x0E4, 0x1D0, 0x17C, 0x1FA, 0x30C, 0x1EA, 0x326, 0x39F, 0x324, 0x1AB)


def extract(paths):
    rows, events = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    e4hist = []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    co = {"t": [], "req": [], "can": []}
    # ⚠ accelerometer and gyroscope come out of ONE FIFO and share a timestamp, so they are one
    # 6-axis sample, not two independent streams. Field access copied verbatim from
    # `extract_r5d_cache.py` (route 5d = V74 flying CLEAN with this same probe).
    a_hw, a_mono, a_v, a_st = [], [], [], []
    g_hw, g_mono, g_v, g_st = [], [], [], []
    census = {}                 # (src, addr) -> [count, tmin, tmax]
    sec_bins = {}               # (src, addr) -> {int_second: count}
    seg_of_row = []
    seg_bounds = []
    t0 = None
    ud = []                     # any UDS/diagnostic traffic
    ps = {"t": [], "fault": [], "safety": [], "ign": []}

    for si, p in enumerate(paths):
        first_t = None
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if first_t is None:
                first_t = tm
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
                    if src in (0, 1, 2):
                        sb = sec_bins.setdefault(key, {})
                        sb[int(tm)] = sb.get(int(tm), 0) + 1
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
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
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
                                     # 🛑 RAW big-endian words, kept UNSCALED so the 0x7FFF
                                     # sentinel is testable exactly rather than through a float.
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
                    # `gyroUncalibrated` is the populated field on this fork; `gyro` is empty.
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
        seg_bounds.append((si, first_t))
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

    # ---- V74 probe decode --------------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["b7"] = ((p & BIT_DAMP_NZ) != 0).astype(float)
    d["state"] = ((p >> PAYLOAD_SHIFT) & 0xF).astype(float)      # ★ THE HEADLINE COLUMN
    d["status"] = (p & STATUS_MASK).astype(float)
    d["illegal"] = (~np.isin(p & PROBE_MASK, LEGAL_PAYLOADS)).astype(float)
    # 🛑 `illegal` is VACUOUS on V74 (all 32 payloads encodable). This is the real discriminator:
    # `gp-0x67fa` never holds 0, so state==0 means the cave never ran, and 2/12/13/14/15 are
    # outside the cell's measured literal value set entirely.
    d["state_impossible"] = (~np.isin((p >> PAYLOAD_SHIFT) & 0xF,
                                      sorted(STATE_VALUE_SET))).astype(float)
    # is this log even a V74? V75's thermometer can only emit 10 of the 32 payloads.
    d["v75_alpha"] = np.isin(p & PROBE_MASK, V75_ALPHABET).astype(float)
    # 0x1AB byte0 bit2 = the firmware's own DTC/fault-active flag, held onto the 0x14A grid.
    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan) \
        if len(r1ab_t) else np.full(len(d["t"]), np.nan)

    # ---- IMU ------------------------------------------------------------------------------------
    # 🛑 NOT resampled onto the 100 Hz CAN grid -- the raw ~101 Hz hardware lattice is kept so
    # transient work is possible. `at`/`gt` are the SENSOR's hardware clock mapped onto the CAN
    # time base by the median offset against logMonoTime, exactly as `extract_r5d_cache.py` does.
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
               a_hw_off=np.array([off_a]), g_hw_off=np.array([off_g]),
               a_off_sd=np.array([float(np.std(a_mono - a_hw)) if len(a_hw) else np.nan]),
               g_off_sd=np.array([float(np.std(g_mono - g_hw)) if len(g_hw) else np.nan]))
    # the requested aliases, same arrays under the brief's names
    imu.update(imu_t=at, imu_ax=imu["ax"], imu_ay=imu["ay"], imu_az=imu["az"],
               imu_gt=gt, imu_gx=imu["gx"], imu_gy=imu["gy"], imu_gz=imu["gz"])
    # ★ WHICH AXIS IS VERTICAL IS DERIVED FROM GRAVITY ON THIS ROUTE, not assumed. The kit's
    # established mapping is ax=vertical, ay=lateral, az=longitudinal (analyze_r47_imu.py:1564).
    if len(A):
        means = np.array([A[:, i].mean() for i in range(3)])
        vi = int(np.argmin(np.abs(np.abs(means) - 9.807)))
        vname = ("ax", "ay", "az")[vi]
        d["imu_vert"] = _grid(d["t"], at, A[:, vi])
        print(f"  IMU gravity means ax={means[0]:+.4f} ay={means[1]:+.4f} az={means[2]:+.4f} "
              f"m/s^2  -> VERTICAL = {vname} (|mean| {abs(means[vi]):.4f}, "
              f"{abs(means[vi]) / 9.807:.4f} g)")
    else:
        vname, vi = "", -1
        d["imu_vert"] = np.full(len(d["t"]), np.nan)
    imu["imu_vert_axis"] = np.array([vname])

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0

    # per-address per-second liveness matrix
    keys = sorted(sec_bins.keys())
    secs = sorted({s for kk in keys for s in sec_bins[kk]})
    smin, smax = (min(secs), max(secs)) if secs else (0, 0)
    mat = np.zeros((len(keys), smax - smin + 1), np.int32)
    for i, kk in enumerate(keys):
        for s, c in sec_bins[kk].items():
            mat[i, s - smin] = c
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT / "r61.npz", **d, **imu, e4hist=e4,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv,
        sc_t=sct, sc_tq_raw=np.array(sc_tq, float), sc_rq_raw=np.array(sc_rq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        ps_t=np.array(ps["t"], float) - t0, ps_fault=np.array(ps["fault"], float),
        ps_safety=np.array(ps["safety"], float), ps_ign=np.array(ps["ign"], float),
        live_keys=np.array([f"{s}:{a_:03X}" for s, a_ in keys]),
        live_mat=mat, live_sec0=np.array([smin - t0]),
        # 🛑 derived from the `seg` COLUMN, not from the first event's logMonoTime -- the latter
        # gave identical values (the first parseable event in each segment is not a CAN frame).
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([BUILD]), probe_rwd=np.array([RWD_NAME]))
    (OUT / "r61_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))
    (OUT / "r61_census.json").write_text(json.dumps(
        {f"{s}:{a_:03X}": {"n": c[0], "t0": c[1] - t0, "t1": c[2] - t0}
         for (s, a_), c in sorted(census.items())}, indent=1))
    (OUT / "r61_uds.json").write_text(json.dumps(
        [{"t": tt - t0, "src": s, "addr": f"{a_:X}", "dat": h} for tt, s, a_, h in ud], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) not in LEGAL_PAYLOADS}
    off = {int(v): int(c) for v, c in zip(b4u, b4c)
           if (((int(v) & PROBE_MASK) >> PAYLOAD_SHIFT) & 0xF) not in STATE_VALUE_SET}
    in75 = sum(int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) in V75_ALPHABET)
    print(f"\nroute 61: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print("  ILLEGAL payloads: " + (f"{ {hex(k): v for k, v in bad.items()} }" if bad
                                    else "NONE -- all inside V74's 32-payload alphabet (vacuous)"))
    print("  OFF-STATE-SET payloads: " + (f"{ {hex(k): v for k, v in off.items()} }" if off
                                          else "NONE"))
    print(f"  payloads inside V75's 10-payload thermometer alphabet: {in75} / {len(raw14_b4)} "
          f"({100.0 * in75 / max(1, len(raw14_b4)):.3f}%)")
    su, sc_ = np.unique(d["state"].astype(int), return_counts=True)
    print("  STATE histogram: " + " ".join(f"{v}:{c}" for v, c in zip(su, sc_)))
    print(f"  b7 duty {100 * d['b7'].mean():7.3f}%")
    print(f"  events {len(events)}  UDS frames {len(ud)}  0x1AB frames {len(r1ab_t)}")
    if len(at) > 1:
        da = np.diff(at)
        print(f"  IMU accel {len(at)} samples, median dt {1e3 * np.median(da):.4f} ms -> "
              f"{1 / np.median(da):.4f} Hz;  gyro {len(gt)} samples")
    return d


if __name__ == "__main__":
    argv = [int(x) for x in sys.argv[1:] if not x.startswith("--")]
    extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in (argv or SEGS)])
