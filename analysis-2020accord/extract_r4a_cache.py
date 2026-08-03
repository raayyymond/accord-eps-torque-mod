#!/usr/bin/env python3
"""Extract route `4a` (0000004a--346bf31d97), segments 20-25, to .npz caches.

Route 4a is the SECOND V67 route (route 47 was the first). It was driven to close route 47's
open gap: only 22 s of ENGAGED-CREEP exposure, which left the grind-#2 engaged arm at P(0) = 0.35.

Decode is byte-for-byte the same as `extract_r47_cache.py` -- 0x14A src1 arrivals carry the probe
and set the sample grid, 0x18F held-last supplies the torsion-bar channel + STEER_STATUS. The
ONLY additions here are (a) `b3` kept as its own field because on this route bit3 is the BUILD
IDENTITY test, and (b) a raw 0x18F src-1 STEER_STATUS stream saved un-gridded, so the ST==4 /
ST==3 census has an independent second method that never touches the hold.

🛑 BYTE4 IS BUILD-SPECIFIC. Five bits have carried five different meanings across
V59/V64/V65/V66/V67/V68. This decoder is V67's:

    bit7 = 1                        LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6806 != 0           *** THE GATE ITSELF *** (LKAS deadband/engage gate)
    bit5 = gp-0x671d != 0           *** THE MASKING RISK *** (outranks the arm)
    bit4 = gp-0x671a >= 5           the THIRD arm (oscillation-detector latch)
    bit3 = 0                        UNUSED on V67 -- must be 0 in every frame
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

🛑 V68 (built, unflashed) sets bit3 in EVERY frame (`movea 0x88,r0,r7` -- bit7 liveness + bit3
build-class marker) and repoints bit4 onto the rate axis. So bit3 alone separates the two builds
without trusting the filename, and if bit3 is set anywhere the arm ladder below is the WRONG
decoder and every downstream statistic changes.

Arms resolve as a PRIORITY LADDER, saved as the integer `arm`:
    2 if bit5 (gp-0x671d)   gain pinned to cal 0xC6442 = 1024, BELOW stock
    1 elif bit6 (gp-0x6806) V67's arm, cal 0xC6446 = 5244 = 2.00x
    3 elif bit4 (gp-0x671a) cal 0xC6440 = 2048
    0 else                  stock mode-10 LERP

Usage:  python extract_r4a_cache.py 20 21 22 23 24 25
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
ROUTE = "75604b0a432fdc89_0000004a--346bf31d97"
OUT = Path(os.environ.get("R4A_CACHE", ROOT / "_cache_r4a"))
TAG = "r4a"
SEGS = [20, 21, 22, 23, 24, 25]

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]


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
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and for the byte4 histogram:
    # every 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw14_b4 = [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    clk = {"t": [], "w": []}
    init_wall = []

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
                try:
                    cs["press"].append(float(bool(c.steeringPressed)))
                except Exception:
                    cs["press"].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
                try:
                    cs["std"].append(float(bool(c.standstill)))
                except Exception:
                    cs["std"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)
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
    for k in ("gear", "std"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V67 gate probe decode ----------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & 0x80) != 0)
    g6806 = ((p & 0x40) != 0)      # *** THE GATE ***
    g671d = ((p & 0x20) != 0)      # *** THE MASK ***  outranks the arm
    g671a = ((p & 0x10) != 0)      # the THIRD arm
    unused = ((p & 0x08) != 0)     # V67: must be 0.  V68: always 1.  => BUILD IDENTITY
    d["live"] = live.astype(float)
    d["g6806"] = g6806.astype(float)
    d["g671d"] = g671d.astype(float)
    d["g671a"] = g671a.astype(float)
    d["unused"] = unused.astype(float)
    d["arm"] = np.where(g671d, 2, np.where(g6806, 1, np.where(g671a, 3, 0))).astype(float)
    d["illegal"] = (unused | ~live).astype(float)

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

    np.savez_compressed(
        OUT / f"{tag}.npz", **d, e4hist=e4, **rawout,
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
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
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4 values: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) + "\n"
          f"      VOID(field==0) {void}  bit6 gp-0x6806 {100 * d['g6806'].mean():.3f}%  "
          f"bit5 gp-0x671d {100 * d['g671d'].mean():.3f}%  "
          f"bit4 gp-0x671a {100 * d['g671a'].mean():.3f}%  "
          f"bit3 UNUSED {int(d['unused'].sum())}  illegal {int(d['illegal'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in (sys.argv[1:] or [str(x) for x in SEGS]):
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{TAG}s{s}")
