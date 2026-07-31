#!/usr/bin/env python3
"""Extract V61 route `31` (00000031--0441e00d2b) signals to .npz caches.

Same grid and decode conventions as rlog-tools/extract_r2c_cache.py -- V61 carries V59's probe
UNCHANGED, so byte4 of 0x14A is the V59 thermometer:

    bit7 = 1                          LIVENESS (0 => cave did not fire; field==0 is VOID)
    bit6 = (gp-0x6ba6 <  0)           the 0xFFFF FAULT SENTINEL
    bit5 = ((gp-0x6ba6 >>  9) == 0)   index < 512
    bit4 = ((gp-0x6ba6 >> 10) == 0)   index < 1024
    bit3 = ((gp-0x6ba6 >> 11) == 0)   index < 2048
    bits 2:0 = stock STEER_SENSOR_STATUS, preserved

NEW vs 2c, and the reason this file exists rather than a --route flag on the old one:
    cs_gear     carState.gearShifter as the car.capnp enum ORDINAL (4 == reverse), carried
                HELD-LAST, never np.interp -- it is categorical and interpolating it invents
                gear 3.5 at every shift.
    cs_std      carState.standstill
    _events.json  raw onroadEvents name/timestamp dump for the flight-clean scan (question A).

Usage:  python extract_r31_cache.py 0 1 2 3
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
ROUTE = "75604b0a432fdc89_00000031--0441e00d2b"
OUT = Path(os.environ.get("R31_CACHE", ROOT / "_cache_r31"))

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
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        # Drop 0x14A arriving before the first 0x18F of the segment (one frame
                        # per segment). A single NaN propagates through the FFT and reads as
                        # "0 hands-off frames" -- a plausible null rather than a visible error.
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

    # ---- V59 thermometer decode (V61 carries it unchanged) ----------------------------------
    p = d["probe"].astype(int)
    d["live"] = ((p & 0x80) != 0).astype(float)
    d["fault"] = ((p & 0x40) != 0).astype(float)
    lt512 = ((p & 0x20) != 0)
    lt1024 = ((p & 0x10) != 0)
    lt2048 = ((p & 0x08) != 0)
    d["lt512"] = lt512.astype(float)
    d["lt1024"] = lt1024.astype(float)
    d["lt2048"] = lt2048.astype(float)
    d["mono"] = (~((lt512 & ~lt1024) | (lt1024 & ~lt2048))).astype(float)
    d["lvl"] = (3 - lt512.astype(int) - lt1024.astype(int) - lt2048.astype(int)).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    np.savez_compressed(OUT / f"{tag}.npz", **d, e4hist=e4)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    fs = 1.0 / np.median(np.diff(d["t"]))
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      mono {100 * d['mono'].mean():.3f}%  live {100 * d['live'].mean():.2f}%  "
          f"fault {100 * d['fault'].mean():.3f}%  "
          f"lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  sca {100 * (d['sca'] == 1).mean():.1f}%\n"
          f"      gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:]:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"r31s{s}")
