#!/usr/bin/env python3
"""Extract V282 route `3c` (0000003c--927965c2b4, 13 segment files on disk) signals to .npz caches.

Copied VERBATIM from extract/extract_r39_cache.py -- SAME grid, SAME decode conventions, SAME
output field names.  Only ROUTE, OUT, the env-var name and the segment enumeration differ.

*** ROUTE-NUMBER COLLISION -- READ THIS BEFORE TOUCHING THE FILENAMES ***
The dongle's route counter RESET, so `3a` and `3b` each name TWO different drives in
`analysis-2020accord/rlogs/` (an OLD 2026-08-01 V65-era one and a NEW 2026-09-04 V282 one).
`3c` currently has only ONE route on disk -- `--927965c2b4`, 2026-09-04, V282 -- but the naming
here is kept parallel to `extract_r3a_v282_cache.py` so the epoch is never ambiguous.
Match on the FULL route id including the hash suffix, never on the `3c` counter alone.

*** ALL 13 SEGMENTS 0..12 ARE PRESENT. ***  The segment list is still enumerated from the
FILESYSTEM, never from range(N), and the present/missing split is written to `r3c_segments.json`.
Each segment is extracted with its OWN t0 (exactly as r39 does).

*** THE PROBE DECODE IS r39's, UNCHANGED. ***  V282 is on the car for r39, r3a and r3c alike (only
the openpilot tune changed between the three drives), so byte 4 carries the same five bits:

    bit 7 (0x80) = sign(gp-0x6b4c) < 0            the 11-slot LKAS assist sum      [V281r3, unchanged]
    bit 6 (0x40) = |gp-0x6ada (r24)| >= |gp-0x6b38 (T, the delivered LKAS-lane torque = 427 tap src)|
    bit 5 (0x20) = |gp-0x6ada (r24)| >= |gp-0x6b94 (aggregator sum, the motor-bound total)|
    bit 4 (0x10) = sign(gp-0x6ada = r24, base-assist rate lane) < 0                [V281r3, unchanged]
    bit 3 (0x08) = sign(gp-0x3680, a 32-bit cal/counter) < 0                       [V281r3, unchanged]
    bits 2:0     = never written by this cave

Do NOT carry r35/V64's oscillation-detector map or extract_r3a_cache.py's V65 saturation-ladder
map across -- the same five bits have now carried four different meanings.

Usage:  python analysis-2020accord/extract/extract_r3c_v282_cache.py 0 1 2 ...
        (no args = every segment file that exists on disk, plus the _segments.json descriptor)
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
ROUTE = "75604b0a432fdc89_0000003c--927965c2b4"
TAG = "r3c"
NSEG_NOMINAL = 13                      # 0..12, all present on disk
OUT = Path(os.environ.get("R3C_V282_CACHE",
                          ROOT / "analysis-2020accord" / "_scratch" / "cache" / "r3c"))

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


def present_segments():
    """Segment indices that ACTUALLY EXIST on disk, ascending.  Never assume contiguity."""
    found = {}
    for p in RLOGDIR.glob(f"{ROUTE}--*--rlog.zst"):
        try:
            found[int(p.name.split("--")[2])] = p
        except (IndexError, ValueError):
            continue
    return dict(sorted(found.items()))


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
    t0_mono = float(t0)
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
    # Field names are V282's, deliberately, so a downstream script that asks for `armed`/`fsm`/
    # `live` FAILS LOUDLY here instead of silently reading a bit that means something else.
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
    d["_t0_mono"] = t0_mono
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    found = present_segments()
    missing = [i for i in range(NSEG_NOMINAL) if i not in found]
    if missing:
        print(f"*** {len(missing)} segment file(s) ABSENT from disk: {missing} ***")
    segs = [int(s) for s in sys.argv[1:]] or sorted(found)
    meta = {}
    for s in segs:
        if s not in found:
            print(f"{TAG}s{s}: NO FILE ON DISK -- skipped")
            continue
        d = extract([found[s]], f"{TAG}s{s}")
        meta[str(s)] = dict(file=found[s].name, samples=int(len(d["t"])),
                            t0_mono=d["_t0_mono"],
                            dur_s=float(d["t"][-1] - d["t"][0]),
                            hi_mono=float(d["_t0_mono"] + d["t"][-1]))
    # Only rewrite the descriptor when the whole route was extracted in one go.
    if not sys.argv[1:]:
        order = sorted(int(k) for k in meta)
        gaps = []
        for a_, b_ in zip(order, order[1:]):
            gap = meta[str(b_)]["t0_mono"] - meta[str(a_)]["hi_mono"]
            gaps.append(dict(after_seg=a_, before_seg=b_, gap_s=round(gap, 3),
                             contiguous_index=(b_ == a_ + 1)))
        (OUT / f"{TAG}_segments.json").write_text(json.dumps(dict(
            route=ROUTE, tag=TAG, nseg_nominal=NSEG_NOMINAL,
            present=order, missing=missing, segments=meta, gaps=gaps,
            note=("Each segment cache carries its OWN t0 (t starts at 0). `gap_s` is the "
                  "wall-clock hole between consecutive PRESENT segments, measured on the raw "
                  "logMonoTime clock. A missing segment shows as a large gap_s with "
                  "contiguous_index=false; any caller that concatenates segments MUST insert it."),
        ), indent=1))
        print(f"wrote {OUT / (TAG + '_segments.json')}")
