#!/usr/bin/env python3
"""SECOND, INDEPENDENT METHOD for route `6e`'s load-bearing counts.

🛑 This file shares NOTHING with the cache pipeline except `rlog_parse.read_messages`.  It walks the
raw CAN bytes itself and re-derives, from scratch:

  * the `0x14A` byte-4 alphabet and per-bit duties          (vs the cache's `probe` field)
  * `STEER_STATUS` -- from `0x18F` byte4 7:4 AND from `0x399`, whichever exists on the bus
  * DTC-active frames from `0x1AB` byte0 bit2
  * 0x7FFF sentinels on `0x14A` and `0x18F`
  * **engaged seconds above 50 / 80 km/h using a DIFFERENT SPEED AND A DIFFERENT ENGAGEMENT SOURCE**
    than the cache: wheel speeds from `0x1D0` (not carState `vEgo`), and engagement from `0x18F`
    byte4 bit3 (not carControl `latActive`).  Both alternates are on record as agreeing with the
    cache's sources to 99.94-100% (`accord-lateral-engagement-signals`), so a disagreement here is
    a real finding, not a definition difference.

Everything is accumulated on the CAN frames' OWN arrival times -- no resampling, no interpolation.

Usage:
    python raw_scan_r6e.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import extract_r6e  # noqa: E402,F401  -- installs the truncation-tolerant reader
import rlog_parse   # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
STEM = "75604b0a432fdc89_0000006e--649c462a6e"
SEGS = range(8)
SENTINEL = 0x7FFF


def wheel_speeds_kph(d):
    fl = (d[0] << 7) | (d[1] >> 1)
    fr = ((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)
    rl = ((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)
    rr = ((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)
    return (fl + fr + rl + rr) * 0.01 / 4.0


def main():
    b4 = Counter()
    sstat_18f = Counter()
    sstat_399 = Counter()
    b0_1ab = Counter()
    addr_seen = Counter()
    sent14 = sent18 = 0
    n14 = n18 = 0
    # the alternate exposure pair, sampled at 0x1D0's own 50 Hz arrival
    ws_t, ws_v, ws_eng = [], [], []
    eng_18f = None
    t_first = t_last = None

    for s in SEGS:
        p = RLOGDIR / f"{STEM}--{s}--rlog.zst"
        for evt in rlog_parse.read_messages(p):
            try:
                if evt.which() != "can":
                    continue
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            for m in evt.can:
                src, addr, d = int(m.src), int(m.address), bytes(m.dat)
                addr_seen[(src, addr)] += 1
                if src != 1:
                    continue
                if addr == 0x14A and len(d) >= 7:
                    n14 += 1
                    b4[d[4]] += 1
                    sent14 += ((d[0] << 8) | d[1]) == SENTINEL
                    if t_first is None:
                        t_first = tm
                    t_last = tm
                elif addr == 0x18F and len(d) >= 5:
                    n18 += 1
                    sstat_18f[(d[4] >> 4) & 0x0F] += 1
                    eng_18f = (d[4] >> 3) & 1
                    sent18 += ((d[0] << 8) | d[1]) == SENTINEL
                elif addr == 0x399 and len(d) >= 1:
                    sstat_399[d[0]] += 1
                elif addr == 0x1AB and len(d) >= 1:
                    b0_1ab[d[0]] += 1
                elif addr == 0x1D0 and len(d) >= 8 and eng_18f is not None:
                    ws_t.append(tm)
                    ws_v.append(wheel_speeds_kph(d))
                    ws_eng.append(eng_18f)
        print(f"  seg {s}: 0x14A so far {n14:,}", flush=True)

    tot = sum(b4.values())
    print("\n" + "=" * 90)
    print("RAW SCAN -- independent of the cache")
    print("=" * 90)
    print(f"  0x14A frames on bus 1: {n14:,}   0x18F: {n18:,}   "
          f"span {t_last - t_first:.2f} s")
    print(f"  0x14A byte4 alphabet ({len(b4)} distinct):")
    for k in sorted(b4):
        print(f"    0x{k:02X}  {b4[k]:7,d}  {100 * b4[k] / tot:6.3f}%")
    duties = {f"b{i}": sum(c for v, c in b4.items() if v >> i & 1) / tot for i in (7, 6, 5, 4, 3)}
    print("  per-bit duty: " + "  ".join(f"{k} {v:.5f}" for k, v in duties.items()))
    viol_rate = sum(c for v, c in b4.items() if (v & 0x40) and not (v & 0x80))
    viol_fric = sum(c for v, c in b4.items() if (v & 0x20) and not (v & 0x10))
    print(f"  nesting violations: b6-not-b7 {viol_rate}   b5-not-b4 {viol_fric}")
    print(f"  fingerprint b3 clear: {sum(c for v, c in b4.items() if not v & 0x08)}")
    print(f"\n  STEER_STATUS from 0x18F byte4[7:4]: {dict(sorted(sstat_18f.items()))}")
    print(f"  0x399 frames on bus 1: {sum(sstat_399.values()):,}"
          + (f"  byte0 hist {dict(sorted(sstat_399.items()))}" if sstat_399 else
             "   -- 0x399 IS NOT PRESENT ON THIS BUS"))
    other399 = {k: v for k, v in addr_seen.items() if k[1] == 0x399}
    print(f"  0x399 across ALL srcs: {other399 if other399 else 'ABSENT ENTIRELY'}")
    print(f"  0x1AB byte0 hist: {{{', '.join(f'0x{k:02X}: {v:,}' for k, v in sorted(b0_1ab.items()))}}}")
    dtc = sum(c for v, c in b0_1ab.items() if v >> 2 & 1)
    print(f"  0x1AB DTC-active (bit2) frames: {dtc}")
    print(f"  0x7FFF sentinels: 0x14A {sent14}   0x18F {sent18}")

    # ---- the alternate exposure pair -------------------------------------------------------------
    wt = np.array(ws_t, float)
    wv = np.array(ws_v, float)
    we = np.array(ws_eng, bool)
    dtm = np.diff(wt, prepend=wt[0])
    dtm = np.clip(dtm, 0, 0.1)
    print(f"\n  ALTERNATE EXPOSURE -- speed from 0x1D0 wheel speeds, engagement from 0x18F b4 bit3")
    print(f"    0x1D0 frames {len(wt):,} over {wt[-1] - wt[0]:.2f} s   "
          f"engaged {we.mean():.4f} ({dtm[we].sum():.1f} s)")
    alt = {}
    for thr in (30, 50, 65, 80, 90, 100):
        m = wv >= thr
        alt[f"ge{thr}kmh_engaged_s"] = float(dtm[m & we].sum())
        print(f"    >= {thr:3d} km/h  total {dtm[m].sum():7.1f} s   ENGAGED {dtm[m & we].sum():7.1f} s")
    print(f"    speed km/h quantiles: " +
          "  ".join(f"p{q} {np.percentile(wv, q):.1f}" for q in (0, 25, 50, 75, 95, 100)))

    out = dict(frames_14A=n14, frames_18F=n18, span_s=float(t_last - t_first),
               alphabet={f"0x{k:02X}": v for k, v in sorted(b4.items())}, duties=duties,
               viol_b6_not_b7=viol_rate, viol_b5_not_b4=viol_fric,
               steer_status_18F={int(k): int(v) for k, v in sorted(sstat_18f.items())},
               frames_399=sum(sstat_399.values()),
               b0_1ab={f"0x{k:02X}": int(v) for k, v in sorted(b0_1ab.items())},
               dtc_active_frames=int(dtc), sentinel_14A=int(sent14), sentinel_18F=int(sent18),
               alt_exposure=alt,
               alt_engaged_s=float(dtm[we].sum()), alt_engaged_frac=float(we.mean()))
    (ROOT / "_cache_r6e" / "raw_scan_r6e.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {ROOT / '_cache_r6e' / 'raw_scan_r6e.json'}")


if __name__ == "__main__":
    main()
