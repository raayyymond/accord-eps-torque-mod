#!/usr/bin/env python3
"""Extract V65 route `3a` (0000003a--4e55c1e0f4) signals to .npz caches.

Same grid and decode conventions as extract/extract_r37_cache.py: 0x14A src1 arrivals carry the probe and
set the sample grid, 0x18F held-last supplies the torsion-bar channel + STEER_STATUS.

🛑 BYTE4 IS V65's SYMMETRIC SATURATION LADDER HERE -- **NOT** V59's boost-index thermometer (which
is what route 37 carried) and **NOT** V64's oscillation detector. The same five bits have now
carried three different meanings; reading one build's log with another build's decoder has already
cost this kit a session. V65 probes `gp-0x6b94`, the ten-lane aggregator output, hard-clipped to
+/-10240:

    bit7 = 1                        LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6b94 >= +8192       *** POSITIVE RAIL ***  (80% of the +10240 clip)
    bit5 = gp-0x6b94 >= +4096       positive, large        (40%)
    bit4 = gp-0x6b94 <= -4097       negative, large        (40%)
    bit3 = gp-0x6b94 <= -8193       *** NEGATIVE RAIL ***  (80%)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

EXACTLY FIVE PAYLOADS ARE REACHABLE (probe bits, mask 0xF8):
    0xE0 +RAIL   0xA0 +HALF   0x80 NEUTRAL   0x90 -HALF   0x98 -RAIL

🛑 NOT a thermometer. Three structural invariants, all guaranteed by the cave's arithmetic on ONE
register in ONE tick, and each one DETECTS a wrong build rather than merely finding it plausible:
    (a) bit6 => bit5                        >= +8192 implies >= +4096
    (b) bit3 => bit4                        <= -8193 implies <= -4097
    (c) NOT ((bit6|bit5) AND (bit4|bit3))   *** THE DISCRIMINATOR *** -- one value cannot be both
        positive and negative. V59 and V64 both light bits from "both sides" routinely; V65 cannot.
Violations are saved as `ladviol` and are a DECODE FAULT, never averaged in as a reading.

⚠ A CONSTANT 0x87 IS AMBIGUOUS WITH V64's NULL and must not be interpreted here.

🛑 THE RAW BYTE IS KEPT (`probe`) so the decode stays reproducible. No build-specific flag is the
only record of a frame.

WALL CLOCK. `clocks.wallTimeNanos` (unix epoch) is logged against logMonoTime, so each segment
gets a real wall-clock anchor rather than an assumed 60 s/segment cadence. Saved as `clk_mono`
(seconds relative to this segment's t=0) / `clk_wall` (absolute unix seconds), plus scalars
`t0_mono` (the absolute logMonoTime of t=0) and `wall_t0` (the fitted unix time at t=0).

Usage:  python extract/extract_r3a_cache.py 0 1 2
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
ROUTE = "75604b0a432fdc89_0000003a--4e55c1e0f4"
OUT = Path(os.environ.get("R3A_CACHE", ROOT / "_scratch/cache/r3a"))
TAG = "r3a"

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

    # ---- V65 four-level saturation ladder decode ---------------------------------------------
    # 🛑 `probe` above is the RAW byte4 and stays in the npz. Everything below is derived.
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    d["live"] = ((p & 0x80) != 0).astype(float)
    prail = ((p & 0x40) != 0)      # gp-0x6b94 >= +8192   *** POSITIVE RAIL ***
    phalf = ((p & 0x20) != 0)      # gp-0x6b94 >= +4096   positive, large
    nhalf = ((p & 0x10) != 0)      # gp-0x6b94 <= -4097   negative, large
    nrail = ((p & 0x08) != 0)      # gp-0x6b94 <= -8193   *** NEGATIVE RAIL ***
    d["prail"] = prail.astype(float)
    d["phalf"] = phalf.astype(float)
    d["nhalf"] = nhalf.astype(float)
    d["nrail"] = nrail.astype(float)
    pos_side, neg_side = prail | phalf, nhalf | nrail
    d["pos_side"] = pos_side.astype(float)
    d["neg_side"] = neg_side.astype(float)
    # signed LEVEL: +2 = +RAIL, +1 = +HALF, 0 = NEUTRAL, -1 = -HALF, -2 = -RAIL
    d["level"] = (prail.astype(int) + phalf.astype(int)
                  - nhalf.astype(int) - nrail.astype(int)).astype(float)
    # DECODE FAULT if nonzero -- (a) bit6&~bit5, (b) bit3&~bit4, (c) both sides at once
    d["ladviol"] = ((prail & ~phalf) | (nrail & ~nhalf) | (pos_side & neg_side)).astype(float)
    legal = {0xE0, 0xA0, 0x80, 0x90, 0x98}
    d["illegal"] = np.array([(int(v) & 0xF8) not in legal for v in p], float)

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
          f"      VOID(field==0) {void}  +RAIL {100 * d['prail'].mean():.3f}%  "
          f"+HALF {100 * d['phalf'].mean():.3f}%  -HALF {100 * d['nhalf'].mean():.3f}%  "
          f"-RAIL {100 * d['nrail'].mean():.3f}%  ladviol {int(d['ladviol'].sum())}  "
          f"illegal {int(d['illegal'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:]:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{TAG}s{s}")
