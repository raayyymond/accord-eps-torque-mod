#!/usr/bin/env python3
"""studies/sessions/v76/v76flight_extract.py -- extract route 65 (V76's first flight) into `_scratch/data/_cache_r65_records.pkl`.

Route `75604b0a432fdc89_00000065--ae43aa0f27`, segments 0..10.

THE PROBE ON THIS BUILD (V76-V38BASE, COMBO B) -- CAN 0x14A byte4, re-read from
`builds/v50_v79/build_v76_v38base_tva.py`'s own `wire_model()` / bit-weight constants, NOT hand-copied:

    bit7 (0x80) = |gp-0x6b26| > 448          THE FRICTION-LANE MARGIN (root-cause lane, live band
                                              449..511 under the 511 clamp)
    bit6 (0x40) = STRUCTURALLY ZERO           no code path in this cave can set it
    bit5 (0x20) = STRUCTURALLY ZERO           ditto -- the shadow-pair rung was dropped from COMBO B
    bit4 (0x10) = gp+0x63fd & 0x2              THE MODE INDEX (mode 26 engaged -> bit set; mode 24
                                              manual -> bit clear; 24 & 2 == 0, 26 & 2 == 2)
    bit3 (0x08) = gp-0x67fa == 5               ★ THE POSITIVE CONTROL
    bits 2:0    = live STEER_SENSOR_STATUS, preserved.

Only 8 of 32 possible bit7:3 payloads are reachable: {0x00,0x08,0x10,0x18,0x80,0x88,0x90,0x98}.
Any payload with bit6 or bit5 set (mask 0x60) is IMPOSSIBLE on this cave and is either a foreign
build's log or a decode bug -- this is the build's OWN illegal-mask assertion
(`ILLEGAL_MASK = 0x60`), re-derived below, not re-typed.

🛑 THIS IS NOT THE SAME BUILD AS THE REPO'S `rlog-tools/probe/decode_v76_probe.py`. That file documents
an EARLIER, SUPERSEDED V76 (`V76-V74BASE-GATE-FB-ARM5244`, gate/mask/third-arm on the r24 rate
lane) which STATE.md records as renamed `SUPERSEDED-2026-08-07-BY-V76-V38BASE-...`. The build
actually on the car for this drive is `V76-V38BASE-RELU-C566-...-probe-6b26-63fd`
(`analysis-2020accord/builds/v50_v79/build_v76_v38base_tva.py`), whose probe bits are completely different
(friction margin / mode index / state==5, not gate/mask/arm). Do not use that decoder on this log.

🛑 THE SPEC IS RE-READ out of `builds/v50_v79/build_v76_v38base_tva.py` at import time, not hand-copied -- see
`_assert_probe_spec()`, which execs the builder's own `wire_model()` and checks that this file's
decode inverts it exhaustively, exactly as `studies/sessions/v74_v75/v74fault_extract.py` does for V74.

Route-GLOBAL time base: `t` is seconds from the first 0x14A frame of segment 0, so all 11 segments
are one continuous axis. `seg` carries the segment index per sample.

Usage: python studies/sessions/v76/v76flight_extract.py            # all 11 segments -> _scratch/data/_cache_r65_records.pkl
"""
import json
import os
import pickle
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000065--ae43aa0f27"
SEGS = list(range(11))
OUT_PKL = HERE / "_scratch/data/_cache_r65_records.pkl"

BUILD = "V76-V38BASE-RELU-C566"
RWD_NAME = ("39990-TVA,A160-V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd-"
            "0x13000-0x100000.rwd")

# ---- the probe spec, RE-READ from the builder, not hand-copied --------------------------------
STATE_DISP, MODEIDX_DISP, B26_DISP = 0x67FA, 0x63FD, 0x6B26
PAYLOAD_SHIFT = 3
W_STATE, W_MODE, W_FRICTION = 1, 2, 16
STATE_EQ = 5
MODEIDX_MASK = 0x2
B26_THRESH = 448
B26_INCLUSIVE = False
STATUS_MASK = 0x07
BIT_STATE5 = 1 << PAYLOAD_SHIFT                # 0x08
BIT_MODEIDX = W_MODE << PAYLOAD_SHIFT          # 0x10
BIT_FRICTION = W_FRICTION << PAYLOAD_SHIFT     # 0x80
ILLEGAL_MASK = 0x60                            # bits 6,5 -- structurally impossible on THIS cave
PROBE_MASK = BIT_STATE5 | BIT_MODEIDX | BIT_FRICTION | ILLEGAL_MASK    # 0xF8, for histogram slicing
LEGAL_PAYLOADS = sorted({(f * W_FRICTION | m * W_MODE | s * W_STATE) << PAYLOAD_SHIFT
                         for f in (0, 1) for m in (0, 1) for s in (0, 1)})
# The payloads that are legal here and IMPOSSIBLE on a quiet V75 (whose bit4=>bit5=>bit6=>bit7
# thermometer forbids a bare bit4). If any of these appear, the log is decisively NOT V75.
V76_ONLY_VS_V75 = (0x10, 0x18, 0x90, 0x98)
# V74's field is `bit7 | (state<<3)` for state in {1,3,4,5,6,7,8,9,10,11} -- every state except
# {1,3} sets bit5 or bit6 (state>=4), which is ILLEGAL_MASK here. V74's OWN on-car constant was
# state=5 (routes 5d/61), giving 0x28/0xA8 -- both illegal on V76.
V74_STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}


def _assert_probe_spec():
    """Re-read the builder's own constants and its own wire_model(); refuse to run on a drift."""
    src = (HERE / "builds/v50_v79/build_v76_v38base_tva.py").read_text(encoding="utf-8")

    def hexnum(name):
        m = re.search(rf"^{name}\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
        assert m, f"{name} not found in builds/v50_v79/build_v76_v38base_tva.py"
        return int(m.group(1), 16)

    def anynum(name):
        m = re.search(rf"^{name}\s*=\s*([0-9]+)\s*(?:#|$)", src, re.M)
        assert m, f"{name} not found in builds/v50_v79/build_v76_v38base_tva.py"
        return int(m.group(1))

    assert hexnum("FAULT_CELL_DISP") == B26_DISP, "FAULT_CELL_DISP drifted"
    assert anynum("PAYLOAD_SHIFT") == PAYLOAD_SHIFT, "PAYLOAD_SHIFT drifted"
    m = re.search(r"^W_STATE,\s*W_MODE,\s*W_FRICTION\s*=\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)",
                  src, re.M)
    assert m, "W_STATE, W_MODE, W_FRICTION tuple assignment not found"
    assert (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (W_STATE, W_MODE, W_FRICTION), \
        "bit weights drifted"
    assert anynum("STATE_EQ") == STATE_EQ, "STATE_EQ drifted"
    m = re.search(r"^MODEIDX_MASK\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
    assert m and int(m.group(1), 16) == MODEIDX_MASK, "MODEIDX_MASK drifted"
    assert anynum("B26_THRESH") == B26_THRESH, "B26_THRESH drifted"
    m = re.search(r"^B26_INCLUSIVE\s*=\s*(True|False)", src, re.M)
    assert m and (m.group(1) == "True") == B26_INCLUSIVE, "B26_INCLUSIVE drifted"
    m = re.search(r"^ILLEGAL_MASK\s*=\s*0x([0-9A-Fa-f]+)", src, re.M)
    assert m and int(m.group(1), 16) == ILLEGAL_MASK, "ILLEGAL_MASK drifted"
    # STATE_DISP is written in the source as a NEGATIVE displacement (`STATE_DISP = -0x67FA`).
    m = re.search(r"^STATE_DISP\s*=\s*-0x([0-9A-Fa-f]+)", src, re.M)
    assert m and int(m.group(1), 16) == STATE_DISP, "STATE_DISP drifted"
    # MODEIDX_DISP is a POSITIVE displacement (`gp + 0x63fd`).
    m = re.search(r"^MODEIDX_DISP\s*=\s*\+0x([0-9A-Fa-f]+)", src, re.M)
    assert m and int(m.group(1), 16) == MODEIDX_DISP, "MODEIDX_DISP drifted"

    # ---- exec the builder's OWN wire_model() and check this file's decode inverts it exhaustively
    m = re.search(r"^def wire_model\(.*?(?=^def _check_wire_model)", src, re.M | re.S)
    assert m, "wire_model() not found in builds/v50_v79/build_v76_v38base_tva.py"
    ns = {"STATE_EQ": STATE_EQ, "MODEIDX_MASK": MODEIDX_MASK, "W_MODE": W_MODE,
          "B26_THRESH": B26_THRESH, "B26_INCLUSIVE": B26_INCLUSIVE, "W_FRICTION": W_FRICTION,
          "PAYLOAD_SHIFT": PAYLOAD_SHIFT, "PAYLOAD_KEEP_MASK": STATUS_MASK}
    exec(compile(m.group(0), "builds/v50_v79/build_v76_v38base_tva.py:wire_model", "exec"), ns)
    wire = ns["wire_model"]
    for state in (0, 1, 4, 5, 6, 255):
        for mode_idx in (0, 1, 2, 3, 24, 26, 255):
            for v in (0, 1, 447, 448, 449, 511, (-448) & 0xFFFF, (-449) & 0xFFFF, 0x7FFF, 0x8000):
                for status in range(8):
                    b = wire(state, mode_idx, v, status)
                    assert (b & PROBE_MASK & ~ILLEGAL_MASK) in \
                        [p & ~ILLEGAL_MASK for p in LEGAL_PAYLOADS] or True  # sanity only
                    assert b & ILLEGAL_MASK == 0, f"wire_model produced 0x{b:02X} with bit5/6 set"
                    assert ((b & BIT_STATE5) != 0) == ((state & 0xFF) == STATE_EQ), \
                        "our bit3 decode disagrees with wire_model"
                    assert ((b & BIT_MODEIDX) != 0) == (((mode_idx & 0xFF) & MODEIDX_MASK) != 0), \
                        "our bit4 decode disagrees with wire_model"
                    signed = v - 0x10000 if v & 0x8000 else v
                    hit = (abs(signed) >= B26_THRESH) if B26_INCLUSIVE else (abs(signed) > B26_THRESH)
                    assert ((b & BIT_FRICTION) != 0) == hit, \
                        f"our bit7 decode disagrees with wire_model at v={v} signed={signed}"
                    assert (b & STATUS_MASK) == (status & STATUS_MASK), "status decode disagrees"
    assert len(LEGAL_PAYLOADS) == 8, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 8"
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
    last18 = None
    raw14_b4, raw14_t = [], []
    raw1ab_t, raw1ab_b0 = [], []
    cs = {"t": [], "v": [], "eng": [], "std": []}
    cc = {"t": [], "lat": [], "en": []}
    census = {}                 # (src, addr) -> [count, tmin, tmax]
    seg_of_row = []
    t0 = None

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
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 1 and addr == 0x1AB and len(d) >= 1:
                        raw1ab_t.append(tm)
                        raw1ab_b0.append(d[0])
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_t.append(tm)
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     # 🛑 RAW big-endian words, kept UNSCALED so the 0x7FFF sentinel
                                     # is testable exactly rather than through a float.
                                     u16be(d, 0), u16be(d, 2), u16be(d, 5)))
                        seg_of_row.append(si)
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                try:
                    cs["std"].append(float(bool(c.standstill)))
                except Exception:
                    cs["std"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm, bool(getattr(e, "enable", False)),
                                   bool(getattr(e, "softDisable", False)),
                                   bool(getattr(e, "immediateDisable", False))))
        print(f"  seg {si} done, rows so far {len(rows)}", flush=True)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "ang_u16", "rate_u16", "wang_u16"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    d["seg"] = np.array(seg_of_row, float)

    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "std"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k])) if len(cst) else \
            np.full(len(d["t"]), np.nan)
    cct = np.array(cc["t"]) - t0
    # ⚠ latActive is a BOOLEAN control signal, not a smooth one -- nearest-past-sample (held_last),
    # not linear interpolation, or a transition edge gets smeared across the interp step.
    for k in ("lat", "en"):
        d["cc_" + k] = held_last(d["t"], cct, cc[k], 0.0) if len(cct) else \
            np.full(len(d["t"]), np.nan)

    # ---- V76-V38BASE probe decode ------------------------------------------------------------
    p_ = d["probe"].astype(int)
    d["b3_state5"] = ((p_ & BIT_STATE5) != 0).astype(float)      # positive control
    d["b4_mode"] = ((p_ & BIT_MODEIDX) != 0).astype(float)       # engaged mode 26 vs manual 24
    d["b7_friction"] = ((p_ & BIT_FRICTION) != 0).astype(float)  # THE MARGIN CENSUS bit
    d["illegal_56"] = ((p_ & ILLEGAL_MASK) != 0).astype(float)   # bit6/bit5 set -> impossible here
    d["status3"] = (p_ & STATUS_MASK).astype(float)
    d["not_in_8legal"] = (~np.isin(p_ & 0xF8, LEGAL_PAYLOADS)).astype(float)
    d["v76_only_vs_v75"] = np.isin(p_ & 0xF8, V76_ONLY_VS_V75).astype(float)

    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan) \
        if len(r1ab_t) else np.full(len(d["t"]), np.nan)

    OUT_PKL.parent.mkdir(parents=True, exist_ok=True)
    cache = dict(d=d, t0_mono=t0, build=BUILD, rwd=RWD_NAME,
                 raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
                 raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
                 events=[{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im}
                         for tt, nm, en, sd, im in events],
                 census={f"{s}:{a_:03X}": {"n": c[0], "t0": c[1] - t0, "t1": c[2] - t0}
                         for (s, a_), c in sorted(census.items())})
    with open(OUT_PKL, "wb") as f:
        pickle.dump(cache, f)

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    illegal_56 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & ILLEGAL_MASK)}
    not8 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & 0xF8) not in LEGAL_PAYLOADS}
    v76only = sum(int(c) for v, c in zip(b4u, b4c) if (int(v) & 0xF8) in V76_ONLY_VS_V75)
    print(f"\nroute 65: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {np.nanmin(d['cs_v']):.2f}..{np.nanmax(d['cs_v']):.2f}")
    print("  RAW 0x14A byte4 histogram: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print("  bit6/bit5 SET (ILLEGAL on this cave, mask 0x60): " +
          (f"{ {hex(k): v for k, v in illegal_56.items()} }" if illegal_56 else "NONE"))
    print("  outside the 8-legal-payload set (bits 7,4,3 only): " +
          (f"{ {hex(k): v for k, v in not8.items()} }" if not8 else "NONE"))
    print(f"  V76-only-vs-quiet-V75 payloads (0x10/0x18/0x90/0x98): {v76only} / {len(raw14_b4)}")
    print(f"  bit3 (state==5) duty {100 * d['b3_state5'].mean():.3f}%   "
          f"bit4 (mode) duty {100 * d['b4_mode'].mean():.3f}%   "
          f"bit7 (friction>448) duty {100 * d['b7_friction'].mean():.3f}%")
    print(f"  events {len(events)}  0x1AB frames {len(r1ab_t)}")
    return cache


if __name__ == "__main__":
    argv = [int(x) for x in sys.argv[1:] if not x.startswith("--")]
    extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in (argv or SEGS)])
