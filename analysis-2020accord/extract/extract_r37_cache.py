#!/usr/bin/env python3
"""Extract V62 route `37` (00000037--6231e33f3d) signals to .npz caches.

Same grid and decode conventions as extract/extract_r31_cache.py / extract/extract_r35_cache.py: 0x14A src1
arrivals carry the probe and set the sample grid, 0x18F held-last supplies the torsion-bar
channel + STEER_STATUS.

🛑 BYTE4 IS V59's BOOST INDEX HERE, **NOT** V64's oscillation detector. V62 = V59 + two
single-instruction `sar 0xa -> sar 0x9` edits in FUN_0003aa2c (0x3AC20, 0x3AB76); the cave probe is
V59's, byte-for-byte. Applying V64's detector semantics to these frames decodes into plausible
nonsense (0x87 would read as "live, unarmed" instead of "live, index<2048 only").

    bit7 = 1                         LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = (gp-0x6ba6 <  0)          the 0xFFFF FAULT SENTINEL from FUN_0003b66a
    bit5 = ((gp-0x6ba6 >>  9) == 0)  index < 512   <- below X1: nothing modulates
    bit4 = ((gp-0x6ba6 >> 10) == 0)  index < 1024
    bit3 = ((gp-0x6ba6 >> 11) == 0)  index < 2048
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

🛑 A THERMOMETER, not three flags: the thresholds nest, so bit5 => bit4 => bit3 in every valid
frame. A violation is a DECODE FAULT (`thermviol`), never averaged in as a reading.

WALL CLOCK. `clocks.wallTimeNanos` (unix epoch) is logged against logMonoTime, so each segment
gets a real wall-clock anchor rather than an assumed 60 s/segment cadence. Saved as `clk_mono`
(seconds relative to this segment's t=0) / `clk_wall` (absolute unix seconds), plus scalars
`t0_mono` (the absolute logMonoTime of t=0) and `wall_t0` (the fitted unix time at t=0).

Usage:  python extract/extract_r37_cache.py 0 1 2
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
ROUTE = "75604b0a432fdc89_00000037--6231e33f3d"
OUT = Path(os.environ.get("R37_CACHE", ROOT / "_scratch/cache/r37"))

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
    for k in ("gear", "std"):                      # categorical / boolean -> hold, do not blend
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V59 boost-index thermometer decode --------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    d["live"] = ((p & 0x80) != 0).astype(float)
    fault = ((p & 0x40) != 0)      # gp-0x6ba6 < 0    -- the 0xFFFF fault sentinel
    lt512 = ((p & 0x20) != 0)      # index < 512      -- below X1, nothing modulates
    lt1k = ((p & 0x10) != 0)      # index < 1024
    lt2k = ((p & 0x08) != 0)      # index < 2048
    d["fault"] = fault.astype(float)
    d["lt512"] = lt512.astype(float)
    d["lt1024"] = lt1k.astype(float)
    d["lt2048"] = lt2k.astype(float)
    # thermometer LEVEL: 0 = index<512 (pinned) .. 3 = index>=2048 (deep on the curve)
    d["therm"] = (3 - lt512.astype(int) - lt1k.astype(int) - lt2k.astype(int)).astype(float)
    d["thermviol"] = ((lt512 & ~lt1k) | (lt1k & ~lt2k)).astype(float)   # DECODE FAULT if nonzero

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}

    # ---- wall clock ---------------------------------------------------------------------------
    clk_mono = np.array(clk["t"], float) - t0
    clk_wall = np.array(clk["w"], float)
    if len(clk_wall) >= 2:
        # offset is the robust statistic: wall - mono should be a constant (both are seconds).
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
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]))
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    fs = 1.0 / np.median(np.diff(d["t"]))
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["field"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      VOID(field==0) {void}  fault {100 * d['fault'].mean():.3f}%  "
          f"lt512 {100 * d['lt512'].mean():.2f}%  lt1024 {100 * d['lt1024'].mean():.2f}%  "
          f"lt2048 {100 * d['lt2048'].mean():.2f}%  thermviol {int(d['thermviol'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:]:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"r37s{s}")
