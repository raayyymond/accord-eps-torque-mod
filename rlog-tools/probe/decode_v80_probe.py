#!/usr/bin/env python3
"""probe/decode_v80_probe.py -- route 66, the V80 flight: probe decode + the grinding census.

ROUTE `75604b0a432fdc89_00000066--276b942769`, segments 0..14.
OPERATOR'S ON-CAR REPORT: **the worst grinding ever**, loud, felt through the whole car, ~90% of
engaged time, at BOTH low and high speed, with noticeable vehicle instability.

WHAT V80 IS  (`analysis-2020accord/builds/v80_v107/build_v80_tva.py`)
-----------------------------------------------------
  EDIT 1  0x454FE  0xBA -> 0xB5      `bne` -> `br`  : restores V42's state-4 MACRO-ratchet fix
  EDIT 2  FactorC m26 Y[3] 908 -> 566  =>  Y = [566]*4, so the damper dose is SPEED-INDEPENDENT
  EDIT 3  FactorE m26 Y = [0, 897, 912, 927]  (inherited from V79, not rewritten)
  => dose(99 ct of rate) = 412 at EVERY speed = 2.000x V78 = 3.007x V75/V76.
     loop gain k = 4.1597 counts of gp-0x6bd0 per count of column rate -- the HIGHEST this kit has
     ever built. `builds/v80_v107/build_v80_tva.py` states in its own header that GATE 2 is NOT satisfied.

THE PROBE -- CAN 0x14A byte4, src 1.  🛑 BYTE-IDENTICAL TO V78 AND V79's CAVE.
------------------------------------------------------------------------------
    bit7 (0x80)  |gp-0x6bd0| >= 448      the damper output, SIGNED ld.h
    bit6 (0x40)  |gp-0x6bd0| >= 192      the dose meter -- sits ON the grind-#1 design point
    bit5 (0x20)  🛑 STRUCTURALLY ZERO    no instruction in this cave sets it
    bit4 (0x10)  gp+0x63fd & 0x2         the mode index (mode 26 engaged / 24 manual)
    bit3 (0x08)  gp-0x67fa == 5          ★ THE POSITIVE CONTROL
    bits 2:0     live STEER_SENSOR_STATUS, preserved
  Structural invariants: bit5 == 0 always; bit7 SET => bit6 SET (one materialised |value|).
  🛑 THE PROBE CANNOT SEPARATE V80 FROM V78 OR V79 -- the cave is the same 68 bytes and, below
  80 km/h, both rungs trip at the same rate on V79 and V80 by construction. The .rwd FILENAME is
  the pre-drive discriminator. What the probe CAN do is exclude V76-V38BASE absolutely (that cave
  cannot set bit6 or bit5 at all) and calibrate the damper surface against CAN steering rate.

METHOD -- the kit's standing rules, applied
-------------------------------------------
  · Sampling grid = 0x14A arrivals on src 1 (~100 Hz). 0x18F held-last onto it.
  · Spectra: Hann, per-window linear detrend, NFFT 256 (2.56 s, 0.3906 Hz bins), hop 128.
    Windows NEVER cross a segment boundary.
  · 🛑 BOOTSTRAP OVER EPISODES, NOT WINDOWS. Every CI here resamples contiguous engaged episodes.
  · 🛑 A SPLIT-HALF NULL is computed BEFORE any ratio is quoted, and a matched-speed manual null
    gives the "strong line" threshold.
  · 🛑 SPEED-MATCHED comparisons only. Every pooled ratio is also given stratified by speed bin,
    with a per-window speed census, because a moving wheel order smears differently across routes.
  · 🛑 Wheel order 1 = 0.489 * v Hz. Any line whose Theil-Sen slope on speed lands near k*0.489 is
    a TYRE, not firmware.
  · Engagement = carControl.latActive (held-last, not interpolated). cruiseState is NOT used.

Usage:
    python probe/decode_v80_probe.py extract [seg ...]     # -> _scratch/cache/r66/r66.npz
    python probe/decode_v80_probe.py surface               # damper trip rates from the built images
    python probe/decode_v80_probe.py report                # the census
    python probe/decode_v80_probe.py all
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
ANA = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ANA))

RLOGDIR = ANA / "rlogs"
ROUTE = "75604b0a432fdc89_00000066--276b942769"
SEGS = list(range(15))
OUT = Path(os.environ.get("R66_CACHE", ROOT / "_scratch/cache/r66"))
BASELINE_NPZ = ROOT / "_scratch/cache/r65" / "r65.npz"          # route 65 = V76, "flew clean"

BUILD = "V80"
RWD_NAME = ("39990-TVA,A160-V80-V79BASE-flatC566-ratchet454FE-dose412-probe-6bd0-63fd-67fa-"
            "0x13000-0x100000.rwd")
PLAIN_IMAGE = "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"

# ---------------------------------------------------------------------------------------------------
# THE PROBE SPEC -- re-read from builds/v50_v79/build_v78_tva.py (V80 carries that cave verbatim) and cross-checked
# against builds/v80_v107/build_v80_tva.py's own inheritance statement. A drift fails the run loudly.
# ---------------------------------------------------------------------------------------------------
PAYLOAD_SHIFT = 3
PAYLOAD_KEEP_MASK = 0x07
STATE_EQ = 5
MODEIDX_MASK = 0x2
DAMP_SHIFT = 6
DAMP_LO_THRESH, DAMP_HI_THRESH = 192, 448
W_STATE, W_MODE, W_DAMP_LO, W_DAMP_HI = 1, 2, 8, 16
BIT_STATE5, BIT_MODEIDX, BIT_DAMP_LO, BIT_DAMP_HI = 0x08, 0x10, 0x40, 0x80
ILLEGAL_BIT5 = 0x20                      # 🛑 structurally unreachable on this cave
PROBE_MASK = 0xF8
LEGAL_PAYLOAD_HI = {0x00, 0x08, 0x10, 0x18, 0x40, 0x48, 0x50, 0x58, 0xC0, 0xC8, 0xD0, 0xD8}
# The V76-V38BASE cave (route 65's build) can only set bits 7/4/3 -- bits 6 AND 5 are structurally
# zero there. Any bit6 on this route excludes it absolutely.
V76_IMPOSSIBLE_MASK = 0x60

SPEED_CTS_PER_KMH = 64.0
RATE_CTS_PER_DEGS = 4.7121


def _assert_probe_spec():
    """Re-read the builder's constants + exec its OWN wire_model(); refuse to run on a drift."""
    v78 = (ANA / "builds/v50_v79/build_v78_tva.py").read_text(encoding="utf-8")
    v80 = (ANA / "builds/v80_v107/build_v80_tva.py").read_text(encoding="utf-8")

    def pair(src, names, want):
        m = re.search(rf"^{re.escape(names)}\s*=\s*([0-9]+),\s*([0-9]+)", src, re.M)
        assert m and (int(m.group(1)), int(m.group(2))) == want, f"{names} drifted"

    pair(v78, "BIT_STATE5, W_STATE", (3, W_STATE))
    pair(v78, "BIT_MODEIDX, W_MODE", (4, W_MODE))
    pair(v78, "BIT_DAMP_LO, W_DAMP_LO", (6, W_DAMP_LO))
    pair(v78, "BIT_DAMP_HI, W_DAMP_HI", (7, W_DAMP_HI))
    pair(v78, "DAMP_LO_THRESH, DAMP_HI_THRESH", (DAMP_LO_THRESH, DAMP_HI_THRESH))
    for nm, want in (("STATE_EQ", STATE_EQ), ("DAMP_SHIFT", DAMP_SHIFT),
                     ("PAYLOAD_SHIFT", PAYLOAD_SHIFT)):
        m = re.search(rf"^{nm}\s*=\s*([0-9]+)", v78, re.M)
        assert m and int(m.group(1)) == want, f"{nm} drifted"
    m = re.search(r"^MODEIDX_MASK\s*=\s*0x([0-9A-Fa-f]+)", v78, re.M)
    assert m and int(m.group(1), 16) == MODEIDX_MASK, "MODEIDX_MASK drifted"
    m = re.search(r"^ILLEGAL_BIT5\s*=\s*0x([0-9A-Fa-f]+)", v78, re.M)
    assert m and int(m.group(1), 16) == ILLEGAL_BIT5, "ILLEGAL_BIT5 drifted"
    # 🛑 V80 must INHERIT the cave, not restate it.
    for line in ("BIT_DAMP_LO, BIT_DAMP_HI = V78.BIT_DAMP_LO, V78.BIT_DAMP_HI",
                 "DAMP_LO_THRESH, DAMP_HI_THRESH = V78.DAMP_LO_THRESH, V78.DAMP_HI_THRESH",
                 "LEGAL_PAYLOAD_HI = V78.LEGAL_PAYLOAD_HI",
                 "CAVE_EXTENT = V78.CAVE_EXTENT"):
        assert line in v80, f"builds/v80_v107/build_v80_tva.py no longer carries `{line}` -- re-derive the decode"

    m = re.search(r"^def wire_model\(.*?(?=^def _check_wire_model)", v78, re.M | re.S)
    assert m, "wire_model() not found in builds/v50_v79/build_v78_tva.py"
    ns = dict(STATE_EQ=STATE_EQ, MODEIDX_MASK=MODEIDX_MASK, W_MODE=W_MODE, DAMP_SHIFT=DAMP_SHIFT,
              W_DAMP_LO=W_DAMP_LO, W_DAMP_HI=W_DAMP_HI, DAMP_LO_THRESH=DAMP_LO_THRESH,
              DAMP_HI_THRESH=DAMP_HI_THRESH, PAYLOAD_SHIFT=PAYLOAD_SHIFT,
              PAYLOAD_KEEP_MASK=PAYLOAD_KEEP_MASK)
    exec(compile(m.group(0), "builds/v50_v79/build_v78_tva.py:wire_model", "exec"), ns)
    wire = ns["wire_model"]
    seen = set()
    for st in (0, 1, 4, 5, 6, 24, 26, 255):
        for md in (0, 1, 2, 3, 24, 26, 255):
            for v in (0, 1, 191, 192, 193, 447, 448, 449, 511, 512, 1024,
                      (-192) & 0xFFFF, (-448) & 0xFFFF, 0x8000, 0xFFFF):
                for status in range(8):
                    b = wire(st, md, v, status)
                    assert b & ILLEGAL_BIT5 == 0, f"wire_model emitted 0x{b:02X} with bit5 set"
                    assert not (b & BIT_DAMP_HI) or (b & BIT_DAMP_LO), "bit7 without bit6"
                    sv = v - 0x10000 if v & 0x8000 else v
                    assert bool(b & BIT_DAMP_HI) == (abs(sv) >= DAMP_HI_THRESH), "bit7 decode"
                    assert bool(b & BIT_DAMP_LO) == (abs(sv) >= DAMP_LO_THRESH), "bit6 decode"
                    assert bool(b & BIT_MODEIDX) == bool((md & 0xFF) & MODEIDX_MASK), "bit4 decode"
                    assert bool(b & BIT_STATE5) == ((st & 0xFF) == STATE_EQ), "bit3 decode"
                    assert (b & PAYLOAD_KEEP_MASK) == (status & PAYLOAD_KEEP_MASK), "status decode"
                    seen.add(b & PROBE_MASK)
    assert seen <= LEGAL_PAYLOAD_HI, f"payloads outside the legal set: {sorted(map(hex, seen))}"
    return True


_assert_probe_spec()

# ===================================================================================================
# EXTRACTION
# ===================================================================================================
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
    from rlog_parse import read_messages                                   # noqa: E402
    rows, events = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    cs = {k: [] for k in ("t", "v", "eng", "ang", "tq", "press", "gear", "std", "lblink", "rblink")}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    census, seg_of_row = {}, []

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
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm, bool(getattr(e, "enable", False)),
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
    # ⚠ latActive is BOOLEAN -- held-last, never interpolated, or a transition edge smears.
    for k in ("lat", "en"):
        d["cc_" + k] = held_last(d["t"], cct, cc[k], 0.0)
    d["cc_req"] = _grid(d["t"], cct, cc["req"])
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)
    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = _grid(d["t"], wst, wsv[:, i] * KPH_TO_MS) if len(wst) else \
            np.full(len(d["t"]), np.nan)

    # ---- V80 probe decode (V78 cave) -------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["b7_damp448"] = ((p & BIT_DAMP_HI) != 0).astype(float)
    d["b6_damp192"] = ((p & BIT_DAMP_LO) != 0).astype(float)
    d["b5_illegal"] = ((p & ILLEGAL_BIT5) != 0).astype(float)
    d["b4_mode"] = ((p & BIT_MODEIDX) != 0).astype(float)
    d["b3_state5"] = ((p & BIT_STATE5) != 0).astype(float)
    d["status3"] = (p & PAYLOAD_KEEP_MASK).astype(float)
    d["not_legal"] = (~np.isin(p & PROBE_MASK, sorted(LEGAL_PAYLOAD_HI))).astype(float)

    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan) \
        if len(r1ab_t) else np.full(len(d["t"]), np.nan)

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT / "r66.npz", **d,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv, sc_t=sct, sc_tq_raw=np.array(sc_tq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([BUILD]), probe_rwd=np.array([RWD_NAME]))
    (OUT / "r66_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))
    (OUT / "r66_census.json").write_text(json.dumps(
        {f"{s}:{a_:03X}": {"n": c[0], "t0": c[1] - t0, "t1": c[2] - t0}
         for (s, a_), c in sorted(census.items())}, indent=1))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    print(f"\nroute 66: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {np.nanmin(d['cs_v']):.2f}..{np.nanmax(d['cs_v']):.2f} m/s")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print(f"  bit5 (STRUCTURALLY unreachable) set in {int(d['b5_illegal'].sum())} frames")
    print(f"  bit7 duty {100 * d['b7_damp448'].mean():.3f}%  bit6 {100 * d['b6_damp192'].mean():.3f}%"
          f"  bit4 {100 * d['b4_mode'].mean():.3f}%  bit3 {100 * d['b3_state5'].mean():.3f}%")
    print(f"  events {len(events)}  0x1AB {len(r1ab_t)}")
    return d


# ===================================================================================================
# SPECTRAL MACHINERY -- conventions identical to studies/grind/analyze_r29_grinding.py so numbers compare
# ===================================================================================================
NFFT = 256
HOP = 128
BANDS = (("grind1", 18.0, 22.0), ("lanechg", 26.0, 30.0),
         ("grind2", 40.0, 49.0), ("ratchet", 6.0, 9.0),
         # ⊕ the union band. Route 66's two engaged lines (≈19 Hz and ≈27.3 Hz) are BOTH inside it,
         # and a human feels their SUM -- this is the band the "90% of the time" claim is scored on.
         ("wide1730", 17.0, 30.0),
         # 🛑 THE LEAKAGE CONTROL. `band_pp` band-limits with a RECTANGULAR in-band filter, so a
         # neighbouring line 100x stronger can bleed into a quiet band and be read as signal. This
         # empty guard sits BETWEEN route 66's two lines: if its p-p is comparable to grind1's, the
         # 18-22 Hz reading is contaminated; if it is well below, the two lines are separate.
         ("guard2225", 22.0, 25.0))
BAND_IDX = {b[0]: i for i, b in enumerate(BANDS)}
WHEEL_ORDER_HZ_PER_MS = 0.489        # circumference 2.08 m -- wheel order 1
CREEP_MAX_MS = 4.0


def band_peak(P, f, lo, hi, guard=1.0, half=10.0):
    """(peak Hz in band, band mean power, prominence vs a two-sided local floor)."""
    band = (f >= lo) & (f <= hi)
    ref = (((f >= max(1.5, lo - half)) & (f <= lo - guard)) |
           ((f >= hi + guard) & (f <= min(49.6, hi + half))))
    if not band.any() or ref.sum() < 4:
        return np.nan, np.nan, np.nan
    j = int(np.argmax(np.where(band, P, -np.inf)))
    fl = float(np.median(P[ref]))
    return float(f[j]), float(P[band].mean()), (float(P[j] / fl) if fl > 0 else np.nan)


def band_pp(x, lo, hi, fs):
    """Peak-to-peak of the band-limited reconstruction, in the channel's own units."""
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(n, 1 / fs)
    X[(f < lo) | (f > hi)] = 0.0
    y = np.fft.irfft(X, n=n)
    return float(y.max() - y.min())


def windows(d, fs, nfft=NFFT, hop=HOP):
    """Per-window record table. Windows never cross a segment boundary and never contain a NaN.

    Returns a structured dict of arrays. `chan` = the torsion bar (counts) -- the kit's anchor,
    with the fine angle rate (deg/s) carried alongside as the second channel.
    """
    t, seg = d["t"], d["seg"].astype(int)
    tq, rate = d["tq"], d["rate_f"]
    v, lat = d["cs_v"], d["cc_lat"] > 0.5
    ang = d["ang"]
    rec = {k: [] for k in ("i0", "t0", "t1", "seg", "tseg", "v", "vmin", "vmax", "lat",
                           "absrate", "abstq", "absang", "n")}
    for nm, _lo, _hi in BANDS:
        for ch in ("tq", "rt"):
            rec[f"P_{nm}_{ch}"] = []
            rec[f"f_{nm}_{ch}"] = []
            rec[f"pr_{nm}_{ch}"] = []
            rec[f"pp_{nm}_{ch}"] = []
    win = np.hanning(nfft)
    ramp = np.arange(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    seg_t0 = {s: t[seg == s].min() for s in np.unique(seg)}
    for s in np.unique(seg):
        idx = np.flatnonzero(seg == s)
        a0, a1 = idx[0], idx[-1] + 1
        for i in range(a0, a1 - nfft + 1, hop):
            sl = slice(i, i + nfft)
            x, r = tq[sl], rate[sl]
            if not (np.all(np.isfinite(x)) and np.all(np.isfinite(r))
                    and np.all(np.isfinite(v[sl]))):
                continue
            rec["i0"].append(i); rec["t0"].append(t[i]); rec["t1"].append(t[i + nfft - 1])
            rec["seg"].append(s); rec["tseg"].append(t[i] - seg_t0[s])
            rec["v"].append(float(v[sl].mean())); rec["vmin"].append(float(v[sl].min()))
            rec["vmax"].append(float(v[sl].max())); rec["lat"].append(float(lat[sl].mean()))
            rec["absrate"].append(float(np.abs(r).mean()))
            rec["abstq"].append(float(np.abs(x).mean()))
            rec["absang"].append(float(np.abs(ang[sl]).mean()))
            rec["n"].append(nfft)
            for ch, y in (("tq", x), ("rt", r)):
                c = np.polyfit(ramp, y, 1)
                P = np.abs(np.fft.rfft((y - np.polyval(c, ramp)) * win)) ** 2
                for nm, lo, hi in BANDS:
                    fp, bp, pr = band_peak(P, f, lo, hi)
                    rec[f"f_{nm}_{ch}"].append(fp)
                    rec[f"P_{nm}_{ch}"].append(bp)
                    rec[f"pr_{nm}_{ch}"].append(pr)
                    rec[f"pp_{nm}_{ch}"].append(band_pp(y, lo, hi, fs))
    return {k: np.asarray(vv, float) for k, vv in rec.items()}


def episodes_of(mask, minlen=1):
    m = np.asarray(mask, bool).astype(np.int8)
    dd = np.diff(np.concatenate(([0], m, [0])))
    return [(a, b) for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1))
            if b - a >= minlen]


def window_episode_id(W, sel=None, gap_windows=1):
    """Group the SELECTED windows into contiguous episodes -- the bootstrap unit. An episode breaks
    on a segment change or an index gap. Default selection = fully-engaged windows."""
    m = (W["lat"] >= 0.999) if sel is None else np.asarray(sel, bool)
    ids = np.full(len(m), -1, int)
    cur, last_i, last_s = -1, None, None
    for k in np.flatnonzero(m):
        if last_i is None or W["seg"][k] != last_s or (W["i0"][k] - last_i) > gap_windows * HOP:
            cur += 1
        ids[k] = cur
        last_i, last_s = W["i0"][k], W["seg"][k]
    return ids, cur + 1


def boot_mean_by_episode(vals, epi, nboot=4000, seed=80):
    """🛑 EPISODE bootstrap. Resamples whole episodes, not windows."""
    ue = np.unique(epi[epi >= 0])
    if len(ue) < 2:
        return np.nan, np.nan, np.nan
    per = [vals[epi == e] for e in ue]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    obs = float(np.mean(np.concatenate(per)))
    out = np.empty(nboot)
    n = len(per)
    for b in range(nboot):
        pick = rng.integers(0, n, n)
        out[b] = float(np.mean(np.concatenate([per[j] for j in pick])))
    return obs, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def split_half_null(vals, epi):
    """🛑 THE NOISE FLOOR FOR A RATIO. Split each episode in half and score half against half.
    Returns the distribution of first-half/second-half ratios (should straddle 1.0)."""
    out = []
    for e in np.unique(epi[epi >= 0]):
        x = vals[epi == e]
        x = x[np.isfinite(x)]
        if len(x) < 4:
            continue
        m = len(x) // 2
        a, b = float(np.mean(x[:m])), float(np.mean(x[m:]))
        if b > 0:
            out.append(a / b)
    return np.asarray(out, float)


def theilsen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3:
        return np.nan, np.nan
    n = len(x)
    if n > 400:                                  # cap the pair count; deterministic subsample
        sel = np.linspace(0, n - 1, 400).astype(int)
        x, y = x[sel], y[sel]
        n = len(x)
    i, j = np.triu_indices(n, 1)
    dx = x[j] - x[i]
    ok = np.abs(dx) > 1e-9
    if not ok.any():
        return np.nan, np.nan
    s = np.median((y[j] - y[i])[ok] / dx[ok])
    return float(s), float(np.median(y - s * x))


SPEED_BINS = [(0.0, 1.0), (1.0, 2.5), (2.5, 5.0), (5.0, 8.0), (8.0, 12.0), (12.0, 16.0),
              (16.0, 20.0), (20.0, 24.0), (24.0, 40.0)]


def hdr(s):
    print(f"\n{'=' * 104}\n{s}\n{'=' * 104}")


# ===================================================================================================
# THE DAMPER SURFACE -- what the probe bits mean in deg/s, computed from the BUILT IMAGES
# ===================================================================================================
def surface_report():
    hdr("0. THE DAMPER SURFACE -- what bit6/bit7 mean in COLUMN-RATE deg/s  [EVIDENCE, from images]")
    os.environ.setdefault("ACCORD_FIRMWARE_ROOT",
                          r"C:/Users/dudei/Desktop/Projects/accord-firmwares")
    try:
        import v76_surface as VS
        from firmware_paths import plain_image_path
    except Exception as e:                                        # pragma: no cover
        print(f"  ⚠ cannot load the surface evaluator ({e}) -- skipping. The probe decode below")
        print("    does not depend on this section.")
        return
    imgs = {}
    for tag, fn in (("V80", PLAIN_IMAGE),
                    ("V78", "_v78_v76base_ey1_449_dose206_plain_image.bin"),
                    ("V76", "_v76_v38base_relu_damper_plain_image.bin")):
        p = Path(plain_image_path(fn))
        if p.exists():
            imgs[tag] = VS.Surface(img=p.read_bytes(), mode=26)
    try:
        imgs["STOCK"] = VS.Surface(img=VS.load("stock"), mode=26)
    except Exception:
        pass
    if not imgs:
        print("  ⚠ no plain images found -- skipping.")
        return
    print(f"  {'build':7s} {'FactorC(creep..140)':>22s} | first |column rate| that trips each rung")
    print(f"  {'':7s} {'':>22s} | {'thr':>5s} " +
          " ".join(f"{str(k) + ' km/h':>12s}" for k in (5, 20, 60, 100, 140)))
    for tag, S in imgs.items():
        cs = [S.factorC(int(round(k * SPEED_CTS_PER_KMH))) for k in (5, 140)]
        for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
            cells = []
            for kmh in (5, 20, 60, 100, 140):
                sp = int(round(kmh * SPEED_CTS_PER_KMH))
                r = next((r for r in range(0x32C9) if S.mag(sp, r) >= thr), None)
                cells.append("  none" if r is None else f"{r:5d}ct/{r / RATE_CTS_PER_DEGS:5.1f}")
            lab = f"{cs[0]}..{cs[1]}" if thr == DAMP_LO_THRESH else ""
            print(f"  {tag if thr == DAMP_LO_THRESH else '':7s} {lab:>22s} | {thr:5d} " +
                  " ".join(f"{c:>12s}" for c in cells))
    print("  ⇒ bit6/bit7 are a 2-level quantiser on |column rate|. On V80 both are SPEED-INVARIANT")
    print("    (FactorC is flat 566); on V78/V76 they move with speed. That is the dose signature.")


# ===================================================================================================
# THE REPORT
# ===================================================================================================
def load(npz):
    z = np.load(npz, allow_pickle=True)
    return {k: z[k] for k in z.files}


def route_fs(d):
    """Mean sampling rate, per segment, then the route median. 🛑 never 1/median(dt)."""
    per = []
    for s in np.unique(d["seg"]):
        t = d["t"][d["seg"] == s]
        if len(t) > 2:
            per.append((len(t) - 1) / (t[-1] - t[0]))
    return float(np.median(per)), per


def inventory(d, fs, per_fs):
    hdr("1. ROUTE INVENTORY")
    n = len(d["t"])
    lat = d["cc_lat"] > 0.5
    sca = d["sca"] > 0.5
    v = d["cs_v"]
    dur = d["t"][-1] - d["t"][0]
    print(f"  segments {sorted(int(s) for s in np.unique(d['seg']))}   frames {n}   "
          f"t 0..{dur:.2f} s   fs {fs:.4f} Hz")
    print(f"  per-segment fs: " + " ".join(f"{x:.3f}" for x in per_fs))
    print(f"  ENGAGED (carControl.latActive): {int(lat.sum())} frames = {lat.sum() / fs:7.1f} s "
          f"= {100 * lat.mean():.2f}%")
    print(f"  0x18F STEER_CONTROL_ACTIVE     : {int(sca.sum())} frames = {100 * sca.mean():.2f}%  "
          f"(agreement with latActive {100 * (lat == sca).mean():.3f}%)")
    print(f"  vEgo {np.nanmin(v):.2f} .. {np.nanmax(v):.2f} m/s "
          f"({3.6 * np.nanmax(v):.1f} km/h)   mean {np.nanmean(v):.2f}")
    print(f"\n  speed census (frames):  {'bin m/s':>12s} {'all':>8s} {'%':>6s} {'engaged':>8s} "
          f"{'%eng':>6s} {'manual':>8s}")
    for lo, hi in SPEED_BINS:
        m = (v >= lo) & (v < hi)
        print(f"                          {f'{lo:g}-{hi:g}':>12s} {int(m.sum()):8d} "
              f"{100 * m.mean():5.1f}% {int((m & lat).sum()):8d} "
              f"{100 * (m & lat).sum() / max(1, lat.sum()):5.1f}% {int((m & ~lat).sum()):8d}")
    ep = episodes_of(lat, minlen=int(2 * fs))
    print(f"\n  ENGAGED EPISODES >= 2 s: {len(ep)}   total {sum(b - a for a, b in ep) / fs:.1f} s")
    print(f"    durations (s): " +
          " ".join(f"{(b - a) / fs:.1f}" for a, b in sorted(ep, key=lambda ab: -(ab[1] - ab[0]))[:20]))
    dtc = d.get("dtc_active")
    if dtc is not None and np.isfinite(dtc).any():
        tr = int(np.count_nonzero(np.diff(np.nan_to_num(dtc) > 0.5)))
        print(f"  0x1AB DTC-active flag: transitions {tr}, duty {100 * np.nanmean(dtc):.3f}%")
    st = Counter(int(x) for x in d["sstat"])
    print(f"  0x18F STEER_STATUS histogram (bits 7:4): {dict(st.most_common())}")
    sent = int(np.count_nonzero((d["ang_u16"].astype(int) == SENTINEL) |
                                (d["rate_u16"].astype(int) == SENTINEL)))
    print(f"  0x7FFF sentinels in 0x14A angle/rate: {sent}")
    evf = OUT / "r66_events.json"
    if evf.exists():
        ev = json.loads(evf.read_text())
        cnt = Counter(e["name"] for e in ev)
        print(f"  onroadEvents: {len(ev)} total, top: {dict(cnt.most_common(8))}")
    return lat, ep


def probe_report(d, fs, lat):
    hdr("5. THE V80 CAVE PROBE -- CAN 0x14A byte4  (bit7 |damp|>=448 · bit6 >=192 · bit5 ZERO · "
        "bit4 mode · bit3 state==5)")
    p = d["probe"].astype(int)
    n = len(p)
    hist = Counter(int(x) for x in p)
    print(f"  RAW byte4 value distribution ({len(hist)} distinct):")
    for val, c in hist.most_common():
        f_ = val & PROBE_MASK
        bits = "".join(str((val >> k) & 1) for k in (7, 6, 5, 4, 3))
        legal = "legal" if f_ in LEGAL_PAYLOAD_HI else "🛑 ILLEGAL"
        print(f"    0x{val:02X}  {c:8d}  {100 * c / n:6.3f}%   bits7:3={bits}  "
              f"status={val & 7}  {legal}")
    print(f"\n  🛑 STRUCTURAL CHECKS (these decide whether ANY number below is interpretable):")
    b5 = int((p & ILLEGAL_BIT5).astype(bool).sum())
    notleg = int(np.count_nonzero(~np.isin(p & PROBE_MASK, sorted(LEGAL_PAYLOAD_HI))))
    thermo = int(np.count_nonzero(((p & BIT_DAMP_HI) != 0) & ((p & BIT_DAMP_LO) == 0)))
    print(f"    bit5 set (structurally impossible on this cave) : {b5} / {n}")
    print(f"    payload outside the 12 legal values             : {notleg} / {n}")
    print(f"    bit7 SET while bit6 CLEAR (thermometer break)   : {thermo} / {n}")
    v76ish = int(np.count_nonzero((p & V76_IMPOSSIBLE_MASK) != 0))
    print(f"    bits 6|5 set (IMPOSSIBLE on route 65's V76-V38BASE cave): {v76ish} / {n}  "
          f"⇒ {'V76-V38BASE EXCLUDED' if v76ish else '⚠ V76-V38BASE NOT excluded from the bytes'}")
    print("    🛑 THE PROBE CANNOT SEPARATE V80 FROM V78/V79 -- the 68 cave bytes are identical and")
    print("       below 80 km/h both rungs trip at the same rate. The .rwd FILENAME is the")
    print(f"       discriminator: {RWD_NAME}")

    b7 = (p & BIT_DAMP_HI) != 0
    b6 = (p & BIT_DAMP_LO) != 0
    b4 = (p & BIT_MODEIDX) != 0
    b3 = (p & BIT_STATE5) != 0
    v = d["cs_v"]
    print(f"\n  PER-BIT DUTY BY SLICE")
    print(f"    {'slice':34s} {'n':>7s} {'bit7 >=448':>11s} {'bit6 >=192':>11s} "
          f"{'bit4 mode':>10s} {'bit3 st==5':>11s}")
    slices = [("all frames", np.ones(n, bool)), ("ENGAGED (latActive)", lat),
              ("manual", ~lat),
              ("ENGAGED creep <= 4 m/s", lat & (v <= CREEP_MAX_MS)),
              ("ENGAGED 4-15 m/s", lat & (v > CREEP_MAX_MS) & (v <= 15)),
              ("ENGAGED > 15 m/s", lat & (v > 15)),
              ("manual creep <= 4 m/s", (~lat) & (v <= CREEP_MAX_MS)),
              ("manual > 15 m/s", (~lat) & (v > 15))]
    for lab, m in slices:
        k = int(m.sum())
        if k < 128:
            print(f"    {lab:34s} {k:7d}   -- n < 128, refused --")
            continue
        print(f"    {lab:34s} {k:7d} {100 * b7[m].mean():10.3f}% {100 * b6[m].mean():10.3f}% "
              f"{100 * b4[m].mean():9.3f}% {100 * b3[m].mean():10.3f}%")

    # ---- the calibration: do the rungs behave like a quantiser on CAN column rate? ---------------
    print(f"\n  ★ THE RUNGS AGAINST CAN COLUMN RATE (0x18F fine rate, deg/s). V80's build asserts")
    print(f"    bit6 trips at ~10.0 deg/s and bit7 at ~22.9 deg/s, SPEED-INVARIANTLY.")
    ar = np.abs(d["rate_f"])
    print(f"    {'|rate| deg/s':>14s} {'n':>8s} {'bit6 duty':>10s} {'bit7 duty':>10s}")
    edges = [0, 2, 5, 8, 10, 12, 15, 20, 23, 26, 30, 40, 60, 100, 1e9]
    for a, bb in zip(edges[:-1], edges[1:]):
        m = (ar >= a) & (ar < bb)
        if m.sum() < 64:
            continue
        print(f"    {f'{a:g}-{bb:g}':>14s} {int(m.sum()):8d} {100 * b6[m].mean():9.2f}% "
              f"{100 * b7[m].mean():9.2f}%")
    print("    ⚠ CAN rate is 100 Hz and one sample can be a tick stale vs the 1 kHz damper, so a")
    print("      soft transition is EXPECTED. A hard step near the predicted rate confirms the")
    print("      surface is IN FORCE; a flat curve would mean it is not.")
    return b7, b6, b4, b3


def peak_table(f, P, fmin=0.8, fmax=49.5, halfwin=8.0, exclude=1.2, min_prom=2.5):
    """Every local maximum with its local-floor prominence and -3 dB Q. Convention copied from
    `analyze_r29_grinding.peak_table` so the numbers compare across the kit."""
    out = []
    df = f[1] - f[0]
    for j in range(1, len(P) - 1):
        if not (fmin <= f[j] <= fmax):
            continue
        if not (P[j] > P[j - 1] and P[j] >= P[j + 1]):
            continue
        near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
        if near.sum() < 5:
            continue
        floor = float(np.median(P[near]))
        prom = P[j] / floor if floor > 0 else np.inf
        if prom < min_prom:
            continue
        y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
        den = y0 - 2 * y1 + y2
        delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        f0 = f[j] + float(np.clip(delta, -0.5, 0.5)) * df
        half = P[j] / 2.0
        lo = hi = j
        while lo > 1 and P[lo] > half and P[lo - 1] < P[lo]:
            lo -= 1
        while hi < len(P) - 2 and P[hi] > half and P[hi + 1] < P[hi]:
            hi += 1
        bw = max(f[hi] - f[lo], df)
        out.append(dict(f=f0, P=float(P[j]), prom=float(prom), bw=float(bw), Q=float(f0 / bw)))
    out.sort(key=lambda r: -r["prom"])
    return out


def avg_spectrum(d, fs, sel, nfft=512):
    """Mean periodogram over non-overlapping nfft blocks taken ONLY inside contiguous runs of
    `sel` (masked concatenation splices discontinuities and manufactures broadband power)."""
    t, seg = d["t"], d["seg"].astype(int)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    win, ramp = np.hanning(nfft), np.arange(nfft)
    acc = {c: np.zeros(len(f)) for c in ("tq", "rt")}
    K = 0
    m = np.asarray(sel, bool)
    for s in np.unique(seg):
        ss = m & (seg == s)
        for a, b in episodes_of(ss, minlen=nfft):
            for i in range(a, b - nfft + 1, nfft):
                ok = True
                blocks = {}
                for c, x in (("tq", d["tq"]), ("rt", d["rate_f"])):
                    y = x[i:i + nfft]
                    if not np.all(np.isfinite(y)):
                        ok = False
                        break
                    cc = np.polyfit(ramp, y, 1)
                    blocks[c] = np.abs(np.fft.rfft((y - np.polyval(cc, ramp)) * win)) ** 2
                if not ok:
                    continue
                for c in acc:
                    acc[c] += blocks[c]
                K += 1
    if not K:
        return f, None, 0
    return f, {c: a / K for c, a in acc.items()}, K


def spectral_inventory(d, fs, lat):
    hdr("3b. AVERAGED SPECTRUM -- every line above 2.5x its local floor, by CONDITION and SPEED")
    v = d["cs_v"]
    conds = [("ENGAGED, all speeds", lat), ("manual, all speeds", ~lat),
             ("ENGAGED creep <= 4 m/s", lat & (v <= 4)),
             ("manual creep <= 4 m/s", (~lat) & (v <= 4)),
             ("ENGAGED 8-16 m/s", lat & (v > 8) & (v <= 16)),
             ("manual 8-16 m/s", (~lat) & (v > 8) & (v <= 16)),
             ("ENGAGED > 24 m/s", lat & (v > 24)),
             ("manual > 24 m/s", (~lat) & (v > 24))]
    for lab, m in conds:
        f, P, K = avg_spectrum(d, fs, m, nfft=512)
        if P is None or K < 2:
            print(f"\n  {lab:26s}  n={int(m.sum()):6d}  K={K}  -- no complete 5.12 s block --")
            continue
        print(f"\n  {lab:26s}  n={int(m.sum()):6d} frames  K={K} independent 5.12 s blocks  "
              f"mean v {np.nanmean(v[m]):.2f} m/s")
        for ch, cn in (("tq", "TORSION BAR"), ("rt", "ANGLE RATE")):
            pk = peak_table(f, P[ch])
            if not pk:
                print(f"    {cn:12s}  no line above 2.5x the local floor")
                continue
            print(f"    {cn:12s}  " + "  ".join(
                f"{r['f']:.2f}Hz(x{r['prom']:.0f},Q{r['Q']:.0f})" for r in pk[:7]))


def command_channel(d, fs, lat):
    """🛑 IS THE LINE IN OPENPILOT'S COMMAND, OR ONLY IN THE CAR?

    `sc_tq` is openpilot's own TX'd 0xE4 STEER_TORQUE on sendcan src 1, gridded onto the 0x14A
    lattice. If a line is in the BAR and the ANGLE RATE but NOT in the command, the loop that
    sustains it closes INSIDE the EPS + plant -- openpilot is not commanding the oscillation.
    That is the same test that placed the 7.79 Hz ratchet inside the EPS."""
    hdr("3c. IS THE OSCILLATION IN OPENPILOT'S COMMAND?  (sendcan 0x0E4 STEER_TORQUE vs the bar)")
    if "sc_tq" not in d or not np.isfinite(d["sc_tq"]).any():
        print("  ⚠ no sendcan 0x0E4 in this cache -- UNPOWERED, not a null.")
        return
    v = d["cs_v"]
    cmd = np.nan_to_num(d["sc_tq"], nan=0.0)
    seg = d["seg"].astype(int)
    nf = 512
    f = np.fft.rfftfreq(nf, 1 / fs)
    win, ramp = np.hanning(nf), np.arange(nf)
    for lab, m in (("ENGAGED > 24 m/s (the worst event)", lat & (v > 24)),
                   ("ENGAGED 8-16 m/s", lat & (v > 8) & (v <= 16)),
                   ("ENGAGED all speeds", lat)):
        accs = {"bar": np.zeros(len(f)), "cmd": np.zeros(len(f))}
        K = 0
        for s in np.unique(seg):
            for a, b in episodes_of(m & (seg == s), minlen=nf):
                for i in range(a, b - nf + 1, nf):
                    for k, x in (("bar", d["tq"]), ("cmd", cmd)):
                        y = x[i:i + nf]
                        c = np.polyfit(ramp, y, 1)
                        accs[k] += np.abs(np.fft.rfft((y - np.polyval(c, ramp)) * win)) ** 2
                    K += 1
        if K < 2:
            print(f"\n  {lab}: K={K} blocks -- too few.")
            continue
        print(f"\n  {lab}: K={K} independent 5.12 s blocks")
        for k in ("bar", "cmd"):
            P = accs[k] / K
            pk = peak_table(f, P)
            nm = "TORSION BAR" if k == "bar" else "OP COMMAND 0xE4"
            print(f"    {nm:16s} " + ("  ".join(f"{r['f']:.2f}Hz(x{r['prom']:.0f})"
                                                for r in pk[:6]) or "no line above 2.5x"))
            for bnm, lo, hi in BANDS:
                if bnm != "lanechg":
                    continue
                sel = (f >= lo) & (f <= hi)
                ref = ((f >= 12) & (f <= lo - 1)) | ((f >= hi + 1) & (f <= 40))
                print(f"      26-30 Hz band power {P[sel].mean():.5g}   "
                      f"band/out-of-band {P[sel].mean() / P[ref].mean():.2f}x")
    print("\n  🛑 A high band/out-of-band ratio in the BAR with a flat COMMAND means the EPS + plant")
    print("     closes the loop by itself. ⚠ openpilot's 0xE4 is TX'd at ~100 Hz and gridded here,")
    print("     so this bounds the command's content BELOW 50 Hz only.")


def perceived_grinding(W, fs):
    """★ THE '90% OF THE TIME' CLAIM, on the union band a human would call 'grinding'."""
    hdr("2e. THE '~90% OF ENGAGED TIME' CLAIM -- 17-30 Hz p-p on the torsion bar")
    eng = W["lat"] >= 0.999
    man = W["lat"] <= 0.001
    v = W["v"]
    pp = W["pp_wide1730_tq"]
    dt = HOP / fs
    print(f"  manual-window 17-30 Hz p-p distribution (the reference for 'is it there at all'):")
    print(f"    median {np.nanmedian(pp[man]):.1f}   p90 {np.nanpercentile(pp[man], 90):.1f}   "
          f"p95 {np.nanpercentile(pp[man], 95):.1f}   p99 {np.nanpercentile(pp[man], 99):.1f} counts")
    print(f"\n  fraction of ENGAGED windows (and seconds) above a fixed p-p threshold:")
    print(f"    {'thresh ct':>10s} {'%eng win':>9s} {'eng s':>8s} {'%manual win':>12s} {'man s':>8s}")
    for thr in (100, 200, 300, 500, 1000, 1500, 2000):
        fe = float(np.nanmean(pp[eng] > thr))
        fm = float(np.nanmean(pp[man] > thr))
        print(f"    {thr:10d} {100 * fe:8.1f}% {fe * eng.sum() * dt:8.1f} {100 * fm:11.1f}% "
              f"{fm * man.sum() * dt:8.1f}")
    print(f"\n  per SPEED BIN, fraction of engaged windows above the MANUAL p95 of that bin:")
    print(f"    {'speed m/s':>11s} {'nEng':>6s} {'nMan':>6s} {'man p95 pp':>11s} {'%eng above':>11s} "
          f"{'med eng pp':>11s}")
    tot_e = tot_a = 0
    for a, b in SPEED_BINS:
        me, mm = eng & (v >= a) & (v < b), man & (v >= a) & (v < b)
        if me.sum() < 4 or mm.sum() < 8:
            continue
        thr = float(np.nanpercentile(pp[mm], 95))
        k = int(np.nansum(pp[me] > thr))
        tot_e += int(me.sum()); tot_a += k
        print(f"    {f'{a:g}-{b:g}':>11s} {int(me.sum()):6d} {int(mm.sum()):6d} {thr:11.1f} "
              f"{100 * k / me.sum():10.1f}% {np.nanmedian(pp[me]):11.1f}")
    if tot_e:
        print(f"    {'POOLED':>11s} {tot_e:6d} {'':6s} {'':11s} {100 * tot_a / tot_e:10.1f}%")
    print(f"\n  PER SEGMENT (engaged windows only) -- where to look on the drive:")
    print(f"    {'seg':>4s} {'nEng':>5s} {'eng s':>7s} {'med v':>6s} {'med pp':>8s} {'p95 pp':>8s} "
          f"{'max pp':>8s} {'%>500ct':>8s} {'b7 duty':>8s}")
    for s in np.unique(W["seg"]):
        m = eng & (W["seg"] == s)
        if m.sum() < 2:
            continue
        print(f"    {int(s):4d} {int(m.sum()):5d} {m.sum() * dt:7.1f} {np.nanmedian(v[m]):6.2f} "
              f"{np.nanmedian(pp[m]):8.1f} {np.nanpercentile(pp[m], 95):8.1f} "
              f"{np.nanmax(pp[m]):8.1f} {100 * np.nanmean(pp[m] > 500):7.1f}% "
              f"{100 * np.nanmean(W['b7'][m]):7.1f}%")


def engagement_onset(d, fs, lat, win_s=4.0):
    hdr("2c. THE ENGAGEMENT TEST -- band power in the 4 s BEFORE vs the 4 s AFTER each latActive "
        "rising edge (and the mirror at each falling edge)")
    n = int(win_s * fs)
    nf = 256
    f = np.fft.rfftfreq(nf, 1 / fs)
    seg = d["seg"].astype(int)

    def bp(i0, i1):
        out = {}
        x = d["tq"][i0:i1]
        if len(x) < nf or not np.all(np.isfinite(x)):
            return None
        ramp = np.arange(nf)
        acc, K = np.zeros(len(f)), 0
        for i in range(0, len(x) - nf + 1, nf // 2):
            s = x[i:i + nf]
            c = np.polyfit(ramp, s, 1)
            acc += np.abs(np.fft.rfft((s - np.polyval(c, ramp)) * np.hanning(nf))) ** 2
            K += 1
        acc /= K
        for nm, lo, hi in BANDS:
            out[nm] = float(acc[(f >= lo) & (f <= hi)].mean())
        return out

    for edge, name in ((1, "RISING (manual -> ENGAGED)"), (-1, "FALLING (ENGAGED -> manual)")):
        dd = np.diff(lat.astype(np.int8))
        idx = np.flatnonzero(dd == edge) + 1
        rows = []
        for i in idx:
            if i - n < 0 or i + n >= len(lat):
                continue
            if seg[i - n] != seg[i + n - 1]:
                continue
            a = bp(i - n, i)
            b = bp(i, i + n)
            if a and b:
                rows.append((d["cs_v"][i], a, b))
        print(f"\n  {name}: {len(rows)} usable edges (both sides in one segment, {win_s:.0f} s each)")
        if not rows:
            continue
        print(f"    {'band':10s} {'before':>12s} {'after':>12s} {'ratio':>8s} "
              f"{'median per-edge ratio':>22s} {'n_up':>6s}")
        for nm, lo, hi in BANDS:
            A = np.array([r[1][nm] for r in rows])
            B = np.array([r[2][nm] for r in rows])
            rat = B / np.where(A > 0, A, np.nan)
            print(f"    {nm:10s} {A.mean():12.4g} {B.mean():12.4g} {B.mean() / A.mean():8.2f} "
                  f"{np.nanmedian(rat):22.2f} {int(np.nansum(rat > 1)):6d}")
    print("\n  🛑 Edges are few and each is ONE sample of a noisy quantity; the median per-edge")
    print("     ratio and the count above 1 are the honest statistics, not the mean-of-means.")


def grind_census(W, fs, label, baseline=None):
    hdr(f"2/3/4. GRINDING CENSUS -- {label}")
    epi, nepi = window_episode_id(W)
    mepi, nmepi = window_episode_id(W, W["lat"] <= 0.001)
    eng = W["lat"] >= 0.999
    man = W["lat"] <= 0.001
    v = W["v"]
    print(f"  windows {len(W['t0'])} of {NFFT / fs:.2f} s (hop {HOP / fs:.2f} s)   "
          f"ENGAGED {int(eng.sum())}   manual {int(man.sum())}   mixed "
          f"{int((~eng & ~man).sum())}   engaged EPISODES {nepi}")

    for ch, chname, unit in (("tq", "TORSION BAR 0x18F", "counts"),
                             ("rt", "ANGLE RATE 0x18F fine", "deg/s")):
        print(f"\n  ---- channel: {chname} ({unit}) " + "-" * 50)
        print(f"    {'band':10s} {'slice':22s} {'nwin':>6s} {'meanP':>11s} "
              f"{'[episode-boot 95% CI]':>27s} {'med prom':>9s} {'med pp':>9s} {'p95 pp':>9s}")
        for nm, lo, hi in BANDS:
            Pk, prk, ppk = f"P_{nm}_{ch}", f"pr_{nm}_{ch}", f"pp_{nm}_{ch}"
            for slab, m in (("ENGAGED", eng), ("manual", man),
                            ("ENGAGED creep<=4", eng & (v <= CREEP_MAX_MS)),
                            ("ENGAGED >15 m/s", eng & (v > 15))):
                if m.sum() < 4:
                    print(f"    {nm:10s} {slab:22s} {int(m.sum()):6d}   -- too few --")
                    continue
                base = mepi if slab == "manual" else epi
                e2 = np.where(m, base, -1)
                obs, lo_, hi_ = boot_mean_by_episode(W[Pk][m], e2[m])
                ci = f"[{lo_:9.4g}, {hi_:9.4g}]" if np.isfinite(lo_) else f"{'(1 episode)':>27s}"
                print(f"    {nm:10s} {slab:22s} {int(m.sum()):6d} {np.nanmean(W[Pk][m]):11.4g} "
                      f"{ci:>27s} {np.nanmedian(W[prk][m]):9.2f} {np.nanmedian(W[ppk][m]):9.1f} "
                      f"{np.nanpercentile(W[ppk][m], 95):9.1f}")

    # ---- the noise floor, computed BEFORE any ratio is quoted ------------------------------------
    print(f"\n  🛑 NOISE FLOOR -- SPLIT-HALF NULL over engaged episodes (first half / second half).")
    print(f"    A ratio inside this interval is NOT a detection.")
    print(f"    {'band':10s} {'chan':5s} {'n_epi':>6s} {'median':>8s} {'[2.5%, 97.5%]':>22s}")
    floors = {}
    for nm, lo, hi in BANDS:
        for ch in ("tq", "rt"):
            r = split_half_null(W[f"P_{nm}_{ch}"], np.where(eng, epi, -1))
            if len(r) < 3:
                print(f"    {nm:10s} {ch:5s} {len(r):6d}   -- too few episodes --")
                continue
            q = (float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5)))
            floors[(nm, ch)] = q
            print(f"    {nm:10s} {ch:5s} {len(r):6d} {np.median(r):8.3f} "
                  f"[{q[0]:9.3f}, {q[1]:9.3f}]")

    # ---- "strong line" census: engaged windows vs the SPEED-MATCHED manual prominence floor ------
    print(f"\n  ★ THE '90% OF THE TIME' CLAIM, QUANTIFIED. A window carries a STRONG LINE if its")
    print(f"    in-band prominence exceeds the 95th percentile of MANUAL windows in the SAME speed")
    print(f"    bin (the empirical noise floor). Per-speed-bin census, torsion bar.")
    print(f"    {'band':10s} {'speed m/s':>11s} {'nEng':>6s} {'nMan':>6s} {'prom95(man)':>12s} "
          f"{'%eng strong':>12s} {'med prom(eng)':>14s} {'med pp':>8s} {'p95 pp':>8s}")
    strong_frac = {}
    for nm, lo, hi in BANDS:
        tot_e = tot_s = 0
        for a, bb in SPEED_BINS:
            me = eng & (v >= a) & (v < bb)
            mm = man & (v >= a) & (v < bb)
            if me.sum() < 4:
                continue
            if mm.sum() >= 8:
                thr = float(np.nanpercentile(W[f"pr_{nm}_tq"][mm], 95))
            else:
                thr = np.nan
            if np.isfinite(thr):
                s = float(np.nanmean(W[f"pr_{nm}_tq"][me] > thr))
                tot_e += int(me.sum()); tot_s += int(np.nansum(W[f"pr_{nm}_tq"][me] > thr))
            else:
                s = np.nan
            print(f"    {nm:10s} {f'{a:g}-{bb:g}':>11s} {int(me.sum()):6d} {int(mm.sum()):6d} "
                  f"{thr:12.2f} {100 * s:11.1f}% {np.nanmedian(W[f'pr_{nm}_tq'][me]):14.2f} "
                  f"{np.nanmedian(W[f'pp_{nm}_tq'][me]):8.1f} "
                  f"{np.nanpercentile(W[f'pp_{nm}_tq'][me], 95):8.1f}")
        if tot_e:
            strong_frac[nm] = tot_s / tot_e
            print(f"    {nm:10s} {'ALL BINS':>11s} {tot_e:6d} {'':6s} {'':12s} "
                  f"{100 * tot_s / tot_e:11.1f}%  ⇐ speed-matched pooled")
        print()

    # ---- engaged vs manual, speed-matched --------------------------------------------------------
    print(f"  ★ ENGAGED / MANUAL BAND-POWER RATIO, PER SPEED BIN (torsion bar). 🛑 Never pool")
    print(f"    across bins without matching -- the speed distributions differ.")
    print(f"    {'band':10s} " + " ".join(f"{f'{a:g}-{b:g}':>9s}" for a, b in SPEED_BINS))
    for nm, lo, hi in BANDS:
        cells = []
        for a, bb in SPEED_BINS:
            me = eng & (v >= a) & (v < bb)
            mm = man & (v >= a) & (v < bb)
            if me.sum() < 4 or mm.sum() < 4:
                cells.append("     --")
                continue
            cells.append(f"{np.nanmean(W[f'P_{nm}_tq'][me]) / np.nanmean(W[f'P_{nm}_tq'][mm]):9.2f}")
        print(f"    {nm:10s} " + " ".join(f"{c:>9s}" for c in cells))

    # ---- dominant frequency + the speed-tracking test ---------------------------------------------
    hdr(f"3. DOMINANT FREQUENCY AND THE SPEED-TRACKING TEST -- {label}")
    print("  Averaged ENGAGED spectrum (torsion bar), whole route, and the top lines.")
    print(f"  {'band':10s} {'nwin':>6s} {'med f (Hz)':>11s} {'IQR f':>14s} "
          f"{'TheilSen df/dv':>15s} {'[epi-boot 95%]':>24s} {'wheel-order k':>14s}")
    rng = np.random.default_rng(80)
    for nm, lo, hi in BANDS:
        m = eng & np.isfinite(W[f"f_{nm}_tq"]) & (W[f"pr_{nm}_tq"] > 3.0)
        if m.sum() < 12:
            print(f"  {nm:10s} {int(m.sum()):6d}   -- too few strong windows for a slope --")
            continue
        fpk, vv = W[f"f_{nm}_tq"][m], v[m]
        s, _ = theilsen(vv, fpk)
        ue = np.unique(epi[m])
        ue = ue[ue >= 0]
        bs = []
        if len(ue) >= 3:
            for _ in range(600):
                pick = rng.integers(0, len(ue), len(ue))
                sel = np.concatenate([np.flatnonzero(m & (epi == ue[j])) for j in pick])
                if len(sel) < 6:
                    continue
                ss, _ = theilsen(v[sel], W[f"f_{nm}_tq"][sel])
                if np.isfinite(ss):
                    bs.append(ss)
        ci = (f"[{np.percentile(bs, 2.5):+8.4f}, {np.percentile(bs, 97.5):+8.4f}]"
              if len(bs) > 30 else f"{'(too few episodes)':>24s}")
        q1, q3 = np.nanpercentile(fpk, [25, 75])
        k = s / WHEEL_ORDER_HZ_PER_MS if np.isfinite(s) else np.nan
        print(f"  {nm:10s} {int(m.sum()):6d} {np.nanmedian(fpk):11.2f} [{q1:5.2f},{q3:5.2f}]  "
              f"{s:+15.4f} {ci:>24s} {k:14.2f}")
    print("  🛑 A slope near +0.489 Hz per m/s (k ~= 1) is WHEEL ORDER 1 -- a TYRE, not firmware.")
    print("     A slope statistically indistinguishable from 0 is a fixed plant/loop mode.")

    print("\n  ★ PEAK FREQUENCY BY SPEED BIN (engaged, torsion bar) -- the speed census that makes")
    print("    the averaged spectrum interpretable.")
    print(f"    {'band':10s} " + " ".join(f"{f'{a:g}-{b:g}':>9s}" for a, b in SPEED_BINS))
    for nm, lo, hi in BANDS:
        cells = []
        for a, bb in SPEED_BINS:
            m = eng & (v >= a) & (v < bb) & (W[f"pr_{nm}_tq"] > 3.0)
            cells.append(f"{np.nanmedian(W[f'f_{nm}_tq'][m]):9.2f}" if m.sum() >= 4 else "     --")
        print(f"    {nm:10s} " + " ".join(f"{c:>9s}" for c in cells))
    print(f"    {'wheelorder1':10s} " +
          " ".join(f"{WHEEL_ORDER_HZ_PER_MS * 0.5 * (a + b):9.2f}" for a, b in SPEED_BINS))

    # ---- worst windows ---------------------------------------------------------------------------
    hdr(f"4. WORST WINDOWS -- {label}   (t is ROUTE-GLOBAL; tseg is seconds into that segment)")
    for nm, lo, hi in BANDS:
        for key, kl in ((f"P_{nm}_tq", "band POWER"), (f"pp_{nm}_tq", "p-p COUNTS")):
            order = np.argsort(-np.nan_to_num(W[key], nan=-np.inf))[:6]
            print(f"\n  {nm} {lo:.0f}-{hi:.0f} Hz -- top 6 by {kl} (torsion bar)")
            print(f"    {'seg':>4s} {'tseg':>7s} {'t_route':>8s} {'P':>11s} {'pp ct':>8s} "
                  f"{'prom':>7s} {'f Hz':>7s} {'lat':>5s} {'v m/s':>6s} {'|rate|':>7s} {'|tq|':>6s}")
            for i in order:
                print(f"    {int(W['seg'][i]):4d} {W['tseg'][i]:7.2f} {W['t0'][i]:8.2f} "
                      f"{W[f'P_{nm}_tq'][i]:11.4g} {W[f'pp_{nm}_tq'][i]:8.1f} "
                      f"{W[f'pr_{nm}_tq'][i]:7.2f} {W[f'f_{nm}_tq'][i]:7.2f} "
                      f"{W['lat'][i]:5.2f} {W['v'][i]:6.2f} {W['absrate'][i]:7.1f} "
                      f"{W['abstq'][i]:6.0f}")

    # ---- band power vs time ------------------------------------------------------------------------
    hdr(f"2b. BAND POWER VS TIME -- {label}  (every 8th window = {8 * HOP / fs:.1f} s, torsion bar)")
    print(f"  {'seg':>4s} {'tseg':>7s} {'lat':>5s} {'v':>6s} " +
          " ".join(f"{nm:>11s}" for nm, _, _ in BANDS) + f" {'|rate|':>7s} {'b6%':>5s} {'b7%':>5s}")
    for i in range(0, len(W["t0"]), 8):
        print(f"  {int(W['seg'][i]):4d} {W['tseg'][i]:7.1f} {W['lat'][i]:5.2f} {W['v'][i]:6.2f} " +
              " ".join(f"{W[f'P_{nm}_tq'][i]:11.4g}" for nm, _, _ in BANDS) +
              f" {W['absrate'][i]:7.1f} " +
              (f"{100 * W['b6'][i]:4.0f}% {100 * W['b7'][i]:4.0f}%" if "b6" in W else "           "))
    return epi, eng, man, floors, strong_frac


def event_zoom(W, d, fs, nshow=3):
    """Contiguous dump of the worst engaged episodes -- so the operator can find them on the drive."""
    hdr("4b. THE WORST EPISODES, WINDOW BY WINDOW  (rank episodes by their mean 18-22 Hz power)")
    epi, nepi = window_episode_id(W)
    scores = []
    for e in range(nepi):
        m = epi == e
        if m.sum() < 3:
            continue
        scores.append((float(np.nanmean(W["P_grind1_tq"][m])), e, int(m.sum())))
    scores.sort(reverse=True)
    for sc, e, nn in scores[:nshow]:
        m = np.flatnonzero(epi == e)
        print(f"\n  EPISODE {e}: seg {int(W['seg'][m[0]])}  tseg {W['tseg'][m[0]]:.1f}.."
              f"{W['tseg'][m[-1]]:.1f} s  ({nn} windows = {nn * HOP / fs:.1f} s)  "
              f"v {W['v'][m].min():.1f}-{W['v'][m].max():.1f} m/s   mean P(18-22) {sc:.4g}")
        print(f"    {'tseg':>7s} {'t_route':>8s} {'v':>6s} {'|rate|':>7s} {'|tq|':>6s} "
              f"{'b6%':>5s} {'b7%':>5s} " +
              " ".join(f"{nm + ' pp':>11s}" for nm, _, _ in BANDS) +
              " " + " ".join(f"{nm + ' f':>8s}" for nm, _, _ in BANDS))
        for i in m:
            print(f"    {W['tseg'][i]:7.2f} {W['t0'][i]:8.2f} {W['v'][i]:6.2f} "
                  f"{W['absrate'][i]:7.1f} {W['abstq'][i]:6.0f} "
                  f"{100 * W['b6'][i]:4.0f}% {100 * W['b7'][i]:4.0f}% " +
                  " ".join(f"{W[f'pp_{nm}_tq'][i]:11.1f}" for nm, _, _ in BANDS) +
                  " " + " ".join(f"{W[f'f_{nm}_tq'][i]:8.2f}" for nm, _, _ in BANDS))


def damper_link(W):
    """Does the symptom track the DAMPER'S OWN SATURATION (bit7 duty), or just speed / rate?"""
    hdr("2d. DOES THE SYMPTOM TRACK THE DAMPER'S SATURATED REGIME?  (bit7 = |gp-0x6bd0| >= 448, "
        "which V80 reaches at only ~22.9 deg/s of column rate, SPEED-INVARIANTLY)")
    eng = W["lat"] >= 0.999
    print(f"  Spearman-style rank correlation over the {int(eng.sum())} fully-engaged windows:")
    print(f"    {'band':10s} {'log10 P vs b7 duty':>20s} {'vs b6 duty':>12s} {'vs |rate|':>11s} "
          f"{'vs v':>8s} {'vs |tq|':>9s}")

    def rk(x):
        x = np.asarray(x, float)
        o = np.argsort(np.argsort(x))
        return (o - o.mean()) / (o.std() + 1e-12)

    for nm, lo, hi in BANDS:
        y = np.log10(np.maximum(W[f"P_{nm}_tq"][eng], 1e-6))
        ry = rk(y)
        cols = [float(np.mean(ry * rk(W[k][eng]))) for k in ("b7", "b6", "absrate", "v", "abstq")]
        print(f"    {nm:10s} {cols[0]:20.3f} {cols[1]:12.3f} {cols[2]:11.3f} {cols[3]:8.3f} "
              f"{cols[4]:9.3f}")
    print("  ⚠ b7 duty, |rate| and v are all correlated with each other on this route -- these are")
    print("    ASSOCIATIONS, not a decomposition. [BELIEF, not EVIDENCE, on causal attribution.]")
    print(f"\n  Band power by bit7 DUTY bin (engaged windows, torsion bar):")
    print(f"    {'b7 duty':>10s} {'nwin':>6s} {'mean v':>7s} {'|rate|':>7s} " +
          " ".join(f"{nm:>12s}" for nm, _, _ in BANDS))
    for a, b in ((0, .01), (.01, .1), (.1, .3), (.3, .5), (.5, .7), (.7, 1.01)):
        m = eng & (W["b7"] >= a) & (W["b7"] < b)
        if m.sum() < 4:
            continue
        print(f"    {f'{a:.2f}-{b:.2f}':>10s} {int(m.sum()):6d} {W['v'][m].mean():7.2f} "
              f"{W['absrate'][m].mean():7.1f} " +
              " ".join(f"{np.nanmean(W[f'P_{nm}_tq'][m]):12.4g}" for nm, _, _ in BANDS))


def compare_baseline(W66, W65, fs):
    hdr("6. ROUTE 66 (V80) vs ROUTE 65 (V76, 'flew clean') -- SPEED-MATCHED, ENGAGED ONLY")
    print("  🛑 Different routes, different speed distributions. Every cell is a within-speed-bin")
    print("     ratio; the pooled figure re-weights bins by min(n66, n65) so neither route's speed")
    print("     mix drives the answer.")
    e66 = W66["lat"] >= 0.999
    e65 = W65["lat"] >= 0.999
    ep66, _ = window_episode_id(W66)
    ep65, _ = window_episode_id(W65)
    print("\n  🛑 SUPPORT PER CELL -- windows / EPISODES. A cell backed by ONE episode is a single")
    print("     event, not a rate; its ratio is reported but must never be bootstrapped.")
    print(f"    {'route':6s} " + " ".join(f"{f'{a:g}-{b:g}':>11s}" for a, b in SPEED_BINS))
    for tag, W, e, ep in (("r66", W66, e66, ep66), ("r65", W65, e65, ep65)):
        cells = []
        for a, b in SPEED_BINS:
            m = e & (W["v"] >= a) & (W["v"] < b)
            cells.append(f"{int(m.sum())}w/{len(set(int(x) for x in ep[m]))}e" if m.sum() else "--")
        print(f"    {tag:6s} " + " ".join(f"{c:>11s}" for c in cells))
    for ch in ("tq", "rt"):
        print(f"\n  channel {'torsion bar (counts)' if ch == 'tq' else 'angle rate (deg/s)'}")
        print(f"    {'band':10s} " + " ".join(f"{f'{a:g}-{b:g}':>9s}" for a, b in SPEED_BINS) +
              f" {'POOLED':>9s}")
        for nm, lo, hi in BANDS:
            cells, num, den = [], 0.0, 0.0
            for a, bb in SPEED_BINS:
                m6 = e66 & (W66["v"] >= a) & (W66["v"] < bb)
                m5 = e65 & (W65["v"] >= a) & (W65["v"] < bb)
                if m6.sum() < 4 or m5.sum() < 4:
                    cells.append("     --")
                    continue
                p6 = np.nanmean(W66[f"P_{nm}_{ch}"][m6])
                p5 = np.nanmean(W65[f"P_{nm}_{ch}"][m5])
                w = min(m6.sum(), m5.sum())
                num += w * p6
                den += w * p5
                cells.append(f"{p6 / p5:9.2f}")
            pooled = f"{num / den:9.2f}" if den > 0 else "     --"
            print(f"    {nm:10s} " + " ".join(f"{c:>9s}" for c in cells) + f" {pooled:>9s}")
    print("\n  ABSOLUTE band power, engaged, both routes (torsion bar), by speed bin:")
    print(f"    {'band':10s} {'route':6s} " + " ".join(f"{f'{a:g}-{b:g}':>10s}" for a, b in SPEED_BINS))
    for nm, lo, hi in BANDS:
        for tag, W, e in (("r66", W66, e66), ("r65", W65, e65)):
            cells = []
            for a, bb in SPEED_BINS:
                m = e & (W["v"] >= a) & (W["v"] < bb)
                cells.append(f"{np.nanmean(W[f'P_{nm}_tq'][m]):10.4g}" if m.sum() >= 4 else "        --")
            print(f"    {nm if tag == 'r66' else '':10s} {tag:6s} " + " ".join(cells))


def attach_probe_to_windows(W, d):
    """Per-window duty of bit6/bit7 so the timeline can carry the dose meter."""
    b6 = (d["probe"].astype(int) & BIT_DAMP_LO) != 0
    b7 = (d["probe"].astype(int) & BIT_DAMP_HI) != 0
    W["b6"] = np.array([b6[int(i):int(i) + NFFT].mean() for i in W["i0"]])
    W["b7"] = np.array([b7[int(i):int(i) + NFFT].mean() for i in W["i0"]])
    return W


def report():
    npz = OUT / "r66.npz"
    if not npz.exists():
        print(f"🛑 {npz} missing -- run `python probe/decode_v80_probe.py extract` first.")
        return 2
    d = load(npz)
    fs, per_fs = route_fs(d)
    print(f"ROUTE {ROUTE}   build {BUILD}")
    print(f"  {RWD_NAME}")
    lat, ep = inventory(d, fs, per_fs)
    probe_report(d, fs, lat)
    W = attach_probe_to_windows(windows(d, fs), d)
    grind_census(W, fs, "ROUTE 66 / V80")
    perceived_grinding(W, fs)
    spectral_inventory(d, fs, lat)
    command_channel(d, fs, lat)
    engagement_onset(d, fs, lat)
    damper_link(W)
    event_zoom(W, d, fs)
    if BASELINE_NPZ.exists():
        d65 = load(BASELINE_NPZ)
        fs65, _ = route_fs(d65)
        W65 = windows(d65, fs65)
        compare_baseline(W, W65, fs)
    else:
        print(f"\n⚠ baseline {BASELINE_NPZ} missing -- no V76 comparison.")
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "report"
    if cmd in ("extract", "all"):
        segs = [int(x) for x in argv[2:] if x.isdigit()] or SEGS
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst" for s in segs])
        if cmd == "extract":
            return 0
    if cmd == "surface":
        surface_report()
        return 0
    if cmd == "all":
        surface_report()
    return report()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
