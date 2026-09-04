#!/usr/bin/env python3
"""Extract V282 route `39` (00000039--f56039af87, 16 segments) signals to .npz caches.

Copied from extract/extract_r35_cache.py -- SAME grid, SAME decode conventions, SAME output field
names for every channel except the byte-4 probe decode (see below).  0x14A src1 arrivals carry the
probe byte and the two angle/rate words; 0x18F held-last supplies the torsion-bar channel +
STEER_STATUS; 0xE4 src 129 supplies the LKAS command and STEER_REQUEST.

*** THE PROBE DECODE IS NOT r35's. ***  extract_r35_cache.py decodes byte 4 as V64's
OSCILLATION-DETECTOR probe (bit7 = constant-1 LIVENESS, bit6/5 = gp-0x671a arm/count, bit4 =
gp-0x67df FSM, bit3 = gp-0x671d override).  That map belongs to V64 and to the OLD-EPOCH route 0x35
(`--77808fe7ce`, 2026-07-31).  This route is the NEW epoch (the dongle's route counter reset) and
carries V282, whose cave writes a completely different set of bits.  Carrying r35's decode across
would have produced five plausible, silently wrong boolean channels -- including a `live` field that
is really the SIGN of the 11-slot assist sum and would have read as ~50 % "dead cave".

V282 byte-4 map, read from analysis-2020accord/builds/v108_plus/build_v282_tva.py (the cave at
0xC4B34, four ld.h displacement halfwords re-pointed off V281 rev 3):

    bit 7 (0x80) = sign(gp-0x6b4c) < 0            the 11-slot LKAS assist sum      [V281r3, unchanged]
    bit 6 (0x40) = |gp-0x6ada (r24)| >= |gp-0x6b38 (T, the delivered LKAS-lane torque = 427 tap src)|
    bit 5 (0x20) = |gp-0x6ada (r24)| >= |gp-0x6b94 (aggregator sum, the motor-bound total)|
    bit 4 (0x10) = sign(gp-0x6ada = r24, base-assist rate lane) < 0                [V281r3, unchanged]
    bit 3 (0x08) = sign(gp-0x3680, a 32-bit cal/counter) < 0                       [V281r3, unchanged]
    bits 2:0     = never written by this cave

Bits 6 and 5 are V282's ONLY delta from V281 rev 3: on V281 rev 3 the same two bits carry
|gp-0x6b94| >= |gp-0x4f64| (bit 6) and |gp-0x6ae2| >= |gp-0x6b26| (bit 5) -- unrelated-cal
comparisons.  The bits are therefore PRESENT in both builds; only their DUTY discriminates.
V283 carries the identical cave, so byte 4 cannot separate V282 from V283 at all.

Usage:  python analysis-2020accord/extract/extract_r39_cache.py 0 1 2 ... 15
        (no args = all 16 segments)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000039--f56039af87"
NSEG = 16
OUT = Path(os.environ.get("R39_CACHE", ROOT / "_scratch/cache/r39"))

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
    # raw arrival timestamps, for the independent CAN-rate check
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: []}
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}

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
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        # Drop 0x14A arriving before the first 0x18F of the segment (one frame per
                        # segment). A single NaN propagates through the FFT and reads as "0
                        # hands-off frames" -- a plausible null rather than a visible error.
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
    for k in ("gear", "std"):                      # categorical / boolean -> hold, do not blend
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V282 r24-comparator probe decode ---------------------------------------------------
    # NOT r35/V64's map -- see the module docstring.  Field names are V282's, deliberately, so a
    # downstream script that asks for `armed`/`fsm`/`live` FAILS LOUDLY here instead of silently
    # reading a bit that means something else on this build.
    p = d["probe"].astype(int)
    assist_neg = ((p & 0x80) != 0)   # sign(gp-0x6b4c) < 0   -- 11-slot LKAS assist sum
    r24_ge_T = ((p & 0x40) != 0)     # |r24| >= |T| (gp-0x6b38, the delivered LKAS-lane torque)
    r24_ge_agg = ((p & 0x20) != 0)   # |r24| >= |aggregator sum| (gp-0x6b94, motor-bound total)
    r24_neg = ((p & 0x10) != 0)      # sign(r24 = gp-0x6ada) < 0
    c3680_neg = ((p & 0x08) != 0)    # sign(gp-0x3680) < 0
    d["assist_neg"] = assist_neg.astype(float)
    d["r24_ge_T"] = r24_ge_T.astype(float)
    d["r24_ge_agg"] = r24_ge_agg.astype(float)
    d["r24_neg"] = r24_neg.astype(float)
    d["c3680_neg"] = c3680_neg.astype(float)
    # bits 2:0 are the stock STEER_SENSOR_STATUS field this cave never writes.
    d["b4_low3"] = (p & 0x07).astype(float)
    # |r24| >= |agg| while NOT |r24| >= |T| requires |T| > |agg|, which is POSSIBLE (T is one
    # summand of agg and the summands can oppose), so this is a MEASUREMENT, not a decode fault.
    d["r24_dom_split"] = (r24_ge_agg & ~r24_ge_T).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}
    np.savez_compressed(OUT / f"{tag}.npz", **d, e4hist=e4, **rawout)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    fs = 1.0 / np.median(np.diff(d["t"]))
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      assist_neg {100 * d['assist_neg'].mean():.2f}%  "
          f"r24>=T {100 * d['r24_ge_T'].mean():.3f}%  "
          f"r24>=agg {100 * d['r24_ge_agg'].mean():.3f}%  "
          f"r24<0 {100 * d['r24_neg'].mean():.3f}%  "
          f"c3680<0 {100 * d['c3680_neg'].mean():.3f}%  low3 nz {int((d['b4_low3'] != 0).sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    segs = sys.argv[1:] or [str(i) for i in range(NSEG)]
    for s in segs:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"r39s{s}")
