#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_extract.py -- extract route 5e (the V75 flight that HARD-FAULTED) to `_scratch/cache/r5e/`.

Route `75604b0a432fdc89_0000005e--857d0bd164`, segments 0..6.

THE PROBE ON THIS BUILD (V75) -- CAN 0x14A byte4, bits 7:3, a THERMOMETER on |gp-0x6bd0|:
    bit7 = (gp-0x6bd0 != 0)          damper output non-zero      -- the positive control, == V74's
    bit6 = (|gp-0x6bd0| >= 128)
    bit5 = (|gp-0x6bd0| >= 288)
    bit4 = (|gp-0x6bd0| >= 448)      near the 512 ceiling floor
    bit3 = (gp-0x6ac2  != 0)         the ceiling-LERP index / back-drive gate
    bits 2:0 = live STEER_SENSOR_STATUS, preserved.
Only 10 of the 32 payloads in 7:3 are structurally reachable (bit4=>bit5=>bit6=>bit7):
    {0x00,0x08,0x80,0x88,0xC0,0xC8,0xE0,0xE8,0xF0,0xF8}
An ILLEGAL payload therefore falsifies either the wire model or the build identity of the log.

🛑 The thresholds are read out of `builds/v50_v79/build_v75_tva.py` at import time, not hand-copied -- see
`_assert_probe_spec()`. If the builder's spec drifts, this extractor fails loudly.

Route-GLOBAL time base: `t` is seconds from the first 0x14A frame of segment 0, so the whole
7-segment drive is one continuous axis. `seg` carries the segment index per sample.

Usage: python studies/sessions/v74_v75/v75fault_extract.py            # all 7 segments -> _scratch/cache/r5e/r5e.npz
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
ROUTE = "75604b0a432fdc89_0000005e--857d0bd164"
SEGS = list(range(7))
OUT = Path(os.environ.get("R5E_CACHE", ROOT / "_scratch/cache/r5e"))

BUILD = "V75"
RWD_NAME = ("39990-TVA,A160-V75-V74BASE-ENGCOLS13-levers-CY0.566-magprobe-6bd0-thermo-6ac2-"
            "0x13000-0x100000.rwd")

# ---- the probe spec, RE-READ from the builder ----------------------------------------------------
BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288 = 0x80, 0x40, 0x20
BIT_MAG448, BIT_BACKDRIVE = 0x10, 0x08
PROBE_MASK = 0xF8
STATUS_MASK = 0x07
MAG_THRESHOLDS = (128, 288, 448)
LEGAL_PAYLOADS = [0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8]
PREDICTED_PEAK_V75 = 354
CEILING_FLOOR = 512


def _assert_probe_spec():
    """Re-read the builder's own constants; refuse to run on a drifted spec."""
    src = (HERE / "builds/v50_v79/build_v75_tva.py").read_text(encoding="utf-8")

    def num(name):
        m = re.search(rf"^{name}\s*=\s*([0-9]+)", src, re.M)
        assert m, f"{name} not found in builds/v50_v79/build_v75_tva.py"
        return int(m.group(1))

    m = re.search(r"^MAG_THRESHOLDS\s*=\s*\(([^)]*)\)", src, re.M)
    assert m, "MAG_THRESHOLDS not found"
    thr = tuple(int(x) for x in m.group(1).replace(" ", "").split(",") if x)
    assert thr == MAG_THRESHOLDS, f"MAG_THRESHOLDS drifted: {thr}"
    m = re.search(r"^PROBE_MASK\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
    assert m and int(m.group(1), 16) == PROBE_MASK, "PROBE_MASK drifted"
    assert num("PREDICTED_PEAK_V75") == PREDICTED_PEAK_V75, "PREDICTED_PEAK_V75 drifted"
    m = re.search(r"LEGAL_PAYLOADS\s*==\s*\[([^\]]*)\]", src)
    assert m, "the LEGAL_PAYLOADS assertion is not in the builder"
    legal = [int(x, 16) for x in m.group(1).replace(" ", "").split(",") if x]
    assert legal == LEGAL_PAYLOADS, f"legal payload set drifted: {[hex(x) for x in legal]}"
    m = re.search(r"^BIT_DAMP_NZ,\s*BIT_MAG128,\s*BIT_MAG288\s*=\s*([^\n]+)", src, re.M)
    assert m and tuple(int(x, 16) for x in m.group(1).split(",")) == \
        (BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288), "the high thermometer bits drifted"
    m = re.search(r"^BIT_MAG448,\s*BIT_BACKDRIVE\s*=\s*([^\n]+)", src, re.M)
    assert m and tuple(int(x, 16) for x in m.group(1).split(",")) == \
        (BIT_MAG448, BIT_BACKDRIVE), "bit4/bit3 drifted"
    return True


_assert_probe_spec()

# ---- the thermometer -> a magnitude BRACKET on |gp-0x6bd0| ---------------------------------------
# thermometer level 0..4; the bracket is [lo, hi) on |gp-0x6bd0|.
THERMO_BRACKET = {0: (0, 1), 1: (1, 128), 2: (128, 288), 3: (288, 448), 4: (448, None)}

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
KPH_TO_MS = 1.0 / 3.6


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


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


WATCH = (0x14A, 0x18F, 0x0E4, 0x1D0, 0x17C, 0x1FA, 0x30C, 0x1EA, 0x326, 0x39F, 0x324)


def extract(paths):
    rows, events = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    e4hist = []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    co = {"t": [], "req": [], "can": []}
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
             "e4tq", "e4req"]
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

    # ---- V75 probe decode --------------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["b7"] = ((p & BIT_DAMP_NZ) != 0).astype(float)
    d["b6"] = ((p & BIT_MAG128) != 0).astype(float)
    d["b5"] = ((p & BIT_MAG288) != 0).astype(float)
    d["b4"] = ((p & BIT_MAG448) != 0).astype(float)
    d["b3"] = ((p & BIT_BACKDRIVE) != 0).astype(float)
    d["thermo"] = (d["b7"] + d["b6"] + d["b5"] + d["b4"])
    d["illegal"] = (~np.isin(p & PROBE_MASK, LEGAL_PAYLOADS)).astype(float)
    # thermometer monotonicity, checked per sample (an order violation is an illegal payload too)
    d["order_viol"] = (((d["b6"] > d["b7"]) | (d["b5"] > d["b6"]) |
                        (d["b4"] > d["b5"]))).astype(float)
    d["damp_lo"] = np.array([THERMO_BRACKET[int(x)][0] for x in d["thermo"]], float)
    d["damp_hi"] = np.array([THERMO_BRACKET[int(x)][1] if THERMO_BRACKET[int(x)][1] is not None
                             else np.nan for x in d["thermo"]], float)

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
        OUT / "r5e.npz", **d, e4hist=e4,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        ws_t=wst, ws_kph=wsv,
        sc_t=sct, sc_tq_raw=np.array(sc_tq, float), sc_rq_raw=np.array(sc_rq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        ps_t=np.array(ps["t"], float) - t0, ps_fault=np.array(ps["fault"], float),
        ps_safety=np.array(ps["safety"], float), ps_ign=np.array(ps["ign"], float),
        live_keys=np.array([f"{s}:{a_:03X}" for s, a_ in keys]),
        live_mat=mat, live_sec0=np.array([smin - t0]),
        # 🛑 derived from the `seg` COLUMN, not from the first event's logMonoTime -- the latter
        # gave 7 identical values (the first parseable event in each segment is not a CAN frame).
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([BUILD]), probe_rwd=np.array([RWD_NAME]))
    (OUT / "r5e_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))
    (OUT / "r5e_census.json").write_text(json.dumps(
        {f"{s}:{a_:03X}": {"n": c[0], "t0": c[1] - t0, "t1": c[2] - t0}
         for (s, a_), c in sorted(census.items())}, indent=1))
    (OUT / "r5e_uds.json").write_text(json.dumps(
        [{"t": tt - t0, "src": s, "addr": f"{a_:X}", "dat": h} for tt, s, a_, h in ud], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) not in LEGAL_PAYLOADS}
    print(f"\nroute 5e: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print("  ILLEGAL payloads: " + (f"{ {hex(k): v for k, v in bad.items()} }" if bad
                                    else "NONE -- all inside V75's 10-payload alphabet"))
    for nm in ("b7", "b6", "b5", "b4", "b3"):
        print(f"  {nm} duty {100 * d[nm].mean():7.3f}%")
    print(f"  events {len(events)}  UDS frames {len(ud)}")
    return d


if __name__ == "__main__":
    argv = [int(x) for x in sys.argv[1:] if not x.startswith("--")]
    extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in (argv or SEGS)])
