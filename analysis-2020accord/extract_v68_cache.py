#!/usr/bin/env python3
"""Extract the two V68 routes -- `4c` (LKAS OFF) and `4e` (LKAS ON) -- to .npz caches.

These are the first V68 logs, and route `4c` is the first HIGHWAY-LKAS-OFF exposure in the whole
corpus: every prior route reads 0.0 s disengaged at every speed cut from 12 to 28 m/s, so the
operator's "only when engaged" report has never been testable. See docs/HANDOFF-2026-08-03 §4.

Decode is byte-for-byte extract_r4a_cache.py's, with ONE substantive change: the byte4 decoder.

🛑 BYTE4 IS BUILD-SPECIFIC -- six builds, six meanings. This decoder is the REVISED V68's, taken
from build_v68_tva.py's CELLS list (GATE_DISP 0x6806 / FSM_DISP 0x67DF / DETECT_DISP 0x671A at
BIT_GATE 0x40 / BIT_MASK 0x20 / BIT_RATE 0x10) -- NOT the superseded rate-axis probe whose .rwd is
prefixed SUPERSEDED-DO-NOT-FLASH:

    bit7 = 1                        LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6806 != 0           the LKAS deadband/engage gate  (V67's arm; unchanged)
    bit5 = gp-0x67df != 0           *** the detector FSM LEFT NEUTRAL: |gp-0x6c2c| crossed +-12800
    bit4 = gp-0x671a >= 1           *** ...and then REVERSED at least once (V67 tested >= 5)
    bit3 = 1 in EVERY frame         the BUILD-CLASS MARKER (`movea 0x88,r0,r7`)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

★★ bits 5 and 4 are the kit's ONLY above-50-Hz instrument. `gp-0x6c2c` is a BAND-PASS peaking near
61 Hz (1 Hz 0.05x · 21.09 Hz 1.00x · 45 Hz 1.54x · 61 Hz 1.61x · 100 Hz 1.43x · 200 Hz 0.94x), so
it is MORE sensitive above 50 Hz than at grind #1, exactly where CAN (Nyquist 50.00) and the comma
IMU (Nyquist 50.51) go deaf. Both cells hold >= 50 ms (the 0xC64DD 50-tick dwell), so a 100 Hz probe
catches them reliably.

🛑 BUILD IDENTITY, and it is the V64 lesson: V66/V67 emit bit3 = 0, V68 emits bit3 = 1 in every
frame, so the payload sets are DISJOINT and a log names its own firmware without the filename.
Exactly eight payloads are legal, all with bit7 AND bit3 set:
    0x8F 0x9F 0xAF 0xBF 0xCF 0xDF 0xEF 0xFF   (low nibble 7 = the preserved status bits)
If any frame carries bit3 == 0 this is NOT V68 and every statistic below is decoded wrong.

⚠ The bit5/bit4 ORDERING is an expectation, not an encoding guarantee. A reversal implies a
crossing, so bit4 => bit5 on the wire; but the two cells are cleared by different rules, so
bit4 && !bit5 is possible at a clear boundary. This decoder REPORTS that rate rather than
asserting it away.

Additions over the r4a schema, both for the lane-change question on `4e`:
    cs_lblink / cs_rblink   carState.leftBlinker / rightBlinker (held-last; lane-change marker)
    cs_lchg                 either blinker

Usage:  python extract_v68_cache.py            # both routes, all segments
        python extract_v68_cache.py 4c 4 5     # one route, chosen segments
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"

# route tag -> (route id, segments).  Both flew the SAME firmware, V68.
ROUTES = {
    "4c": ("75604b0a432fdc89_0000004c--d0ea3c14b4", [4, 5, 6, 7, 8]),      # LKAS OFF, manual
    "4e": ("75604b0a432fdc89_0000004e--11f5b814b6", [31, 32, 33, 34]),     # LKAS ON, highway
}
OUT = Path(os.environ.get("V68_CACHE", ROOT / "_cache_v68"))

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

# The eight reachable V68 payloads, low nibble 7. Asserted, not assumed.
LEGAL_B4 = {0x8F, 0x9F, 0xAF, 0xBF, 0xCF, 0xDF, 0xEF, 0xFF}


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def held_last(t_out, t_in, v_in, fill):
    """Zero-order hold. For CATEGORICAL channels; np.interp would fabricate intermediate codes."""
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    out = np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)])
    return out.astype(float)


def extract(paths, tag, t0=None):
    rows, e4hist, events = [], [], []
    last18, lastE4 = None, (0.0, 0)
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: []}
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and the byte4 histogram: every
    # 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw14_b4 = [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    clk = {"t": [], "w": []}
    init_wall = []
    snd = {"t": [], "sp": [], "spw": []}

    for p in paths:
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
                    if src == 1 and addr in raw:
                        raw[addr].append(tm)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
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
            elif w == "soundPressure":
                try:
                    m = evt.soundPressure
                    snd["t"].append(tm)
                    snd["sp"].append(float(m.soundPressure))
                    snd["spw"].append(float(m.soundPressureWeighted))
                except Exception:
                    for k in ("t", "sp", "spw"):
                        if len(snd[k]) > min(len(snd[j]) for j in ("t", "sp", "spw")):
                            snd[k].pop()
            elif w == "clocks":
                try:
                    wn = int(evt.clocks.wallTimeNanos)
                except Exception:
                    continue
                if wn > 0:
                    clk["t"].append(tm); clk["w"].append(wn * 1e-9)
            elif w == "initData":
                try:
                    wn = int(evt.initData.wallTimeNanos)
                except Exception:
                    wn = 0
                if wn > 0:
                    init_wall.append((tm, wn * 1e-9))
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

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    if t0 is None:
        t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V68 probe decode ---------------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & 0x80) != 0)
    g6806 = ((p & 0x40) != 0)      # bit6  the LKAS gate
    fsm = ((p & 0x20) != 0)        # bit5  gp-0x67df != 0   -- CROSSED +-T
    det = ((p & 0x10) != 0)        # bit4  gp-0x671a >= 1   -- and REVERSED
    cls = ((p & 0x08) != 0)        # bit3  V68 build-class marker: must be 1 in EVERY frame
    d["live"] = live.astype(float)
    d["g6806"] = g6806.astype(float)
    d["fsm67df"] = fsm.astype(float)
    d["det671a"] = det.astype(float)
    d["cls"] = cls.astype(float)
    # ILLEGAL on V68 = liveness clear, class marker clear, or a byte4 outside the eight payloads.
    b4ok = np.isin(p & 0xFF, sorted(LEGAL_B4))
    d["illegal"] = (~live | ~cls | ~b4ok).astype(float)
    # The ordering EXPECTATION, reported not asserted: a reversal implies a crossing.
    d["ord_viol"] = (det & ~fsm).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}

    clk_mono = np.array(clk["t"], float) - t0
    clk_wall = np.array(clk["w"], float)
    if len(clk_wall) >= 2:
        off = float(np.median(clk_wall - clk_mono))
        off_sd = float(np.std(clk_wall - clk_mono, ddof=1))
    elif len(clk_wall) == 1:
        off, off_sd = float(clk_wall[0] - clk_mono[0]), np.nan
    else:
        off, off_sd = np.nan, np.nan
    iw = np.array(init_wall, float).reshape(-1, 2)
    if len(iw):
        iw[:, 0] -= t0
    n_snd = min(len(snd["t"]), len(snd["sp"]), len(snd["spw"]))
    snd_t = np.array(snd["t"][:n_snd], float) - t0

    np.savez_compressed(
        OUT / f"{tag}.npz", **d, e4hist=e4, **rawout,
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
        snd_t=snd_t, snd_sp=np.array(snd["sp"][:n_snd], float),
        snd_spw=np.array(snd["spw"][:n_snd], float),
        raw18_st=np.array(raw18_st, np.int16), raw14_b4=np.array(raw14_b4, np.int16),
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]))
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    fs = 1.0 / np.median(np.diff(d["t"]))
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["field"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if int(v) not in LEGAL_B4}
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** ILLEGAL {bad_b4}" if bad_b4 else "   (all legal V68)") + "\n"
          f"      VOID {void}  bit3 CLASS {100 * d['cls'].mean():.3f}%  "
          f"bit6 gate {100 * d['g6806'].mean():.3f}%  "
          f"*** bit5 gp-0x67df {100 * d['fsm67df'].mean():.4f}%  "
          f"*** bit4 gp-0x671a {100 * d['det671a'].mean():.4f}%  "
          f"illegal {int(d['illegal'].sum())}  ord_viol {int(d['ord_viol'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"blinker {100 * (d['cs_lchg'] > 0.5).mean():.1f}%  "
          f"ST==4 {int((d['sstat'] == 4).sum())}  ST==3 {int((d['sstat'] == 3).sum())}  "
          f"mic {n_snd}  gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] in ROUTES:
        todo = [(args[0], [int(x) for x in args[1:]] or ROUTES[args[0]][1])]
    else:
        todo = [(k, v[1]) for k, v in ROUTES.items()]
    for tag, segs in todo:
        route = ROUTES[tag][0]
        for s in segs:
            extract([RLOGDIR / f"{route}--{s}--rlog.zst"], f"{tag}s{s}")
