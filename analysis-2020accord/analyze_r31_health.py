#!/usr/bin/env python3
"""V61 route `31` -- QUESTION A: flight-clean check + route structure.

Raw onroadEvents scan (never a filtered/derived event list), STEER_STATUS histogram from
0x18F byte4 bits 7:4, frame counts, bus rates, probe health, and the speed/engagement/gear
profile that the rest of the analysis conditions on.

Usage:  python analyze_r31_health.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from _r31_common import CACHE, GEAR, SEGS_31, fs_of, load, sustained  # noqa: E402

FLAGS = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
         "immediateDisable", "steerSaturated"]


def hdr(s):
    print(f"\n{'=' * 96}\n{s}\n{'=' * 96}")


def main():
    hdr("A1. RAW onroadEvents SCAN -- all 4 segments, every event name that appears")
    allev = Counter()
    per_seg = {}
    for s in SEGS_31:
        ev = json.loads((CACHE / f"r31s{s}_events.json").read_text())
        c = Counter(e["name"] for e in ev)
        per_seg[s] = (ev, c)
        allev.update(c)
    print(f"   {'event':30s} " + "".join(f"{'seg' + str(s):>9s}" for s in SEGS_31) + f"{'TOTAL':>9s}")
    for name, tot in allev.most_common():
        print(f"   {name:30s} " + "".join(f"{per_seg[s][1].get(name, 0):9d}" for s in SEGS_31)
              + f"{tot:9d}")

    print("\n   -- the six flags of record --")
    for fl in FLAGS:
        n = allev.get(fl, 0)
        mark = "  <-- !!" if n else ""
        print(f"   {fl:24s} {n:6d}{mark}")
        if n:
            for s in SEGS_31:
                hits = [e for e in per_seg[s][0] if e["name"] == fl]
                if hits:
                    print(f"        seg{s}: {len(hits)} at t="
                          f"{min(h['t'] for h in hits):.2f}..{max(h['t'] for h in hits):.2f} s"
                          f"  immediate={sum(h['immediate'] for h in hits)}"
                          f"  soft={sum(h['soft'] for h in hits)}")

    hdr("A2. STEER_STATUS (0x18F byte4 bits 7:4) -- ST==4 is the V42 state-4 governor")
    tot = Counter()
    for s in SEGS_31:
        d = load(s)
        c = Counter(d["sstat"].astype(int).tolist())
        tot.update(c)
        print(f"   seg{s}: " + "  ".join(f"ST={k}:{v}" for k, v in sorted(c.items())))
    n = sum(tot.values())
    print(f"\n   TOTAL {n} frames: " + "  ".join(f"ST={k}:{v} ({100*v/n:.3f}%)"
                                                for k, v in sorted(tot.items())))
    print(f"   *** ST==4 : {tot.get(4,0)} / {n}"
          + ("   <-- NONZERO, MAJOR FINDING" if tot.get(4, 0) else "   (clean, as V57/V58/V59)"))
    print(f"   *** ST==3 : {tot.get(3,0)} / {n}  (low-speed lockout; 0xC62EA=0 should suppress it)")
    if tot.get(3, 0):
        for s in SEGS_31:
            d = load(s)
            m = d["sstat"] == 3
            if m.any():
                print(f"        seg{s}: {m.sum()} frames, t={d['t'][m].min():.2f}..{d['t'][m].max():.2f} s,"
                      f" |v| {np.abs(d['cs_v'][m]).min():.3f}..{np.abs(d['cs_v'][m]).max():.3f} m/s,"
                      f" sca=1 in {int((d['sca'][m]==1).sum())}")

    hdr("A3. ROUTE STRUCTURE -- frames, rate, probe health, engagement, gear, speed")
    T = 0
    for s in SEGS_31:
        d = load(s)
        fs = fs_of(d)
        lat = d["cc_lat"] > 0.5
        sca = d["sca"] == 1
        agree = 100 * (lat == sca).mean()
        gc = Counter(d["cs_gear"].astype(int).tolist())
        T += len(d["t"])
        print(f"\n   seg{s}: {len(d['t'])} frames  {d['t'][-1]:.2f} s  fs={fs:.3f} Hz"
              f"  |v| {np.abs(d['cs_v']).min():.2f}..{np.abs(d['cs_v']).max():.2f} m/s")
        print(f"        probe: live {100*d['live'].mean():.2f}%  mono {100*d['mono'].mean():.3f}%"
              f"  fault {100*d['fault'].mean():.3f}%"
              f"  0x14A stock low bits &7==0b111 "
              f"{100*((d['probe'].astype(int) & 7) == 7).mean():.2f}%"
              f"  (0x18F bits2:0 spare==0 {100*(d['slow3']==0).mean():.2f}%)")
        print(f"        latActive {100*lat.mean():5.2f}%   SCA {100*sca.mean():5.2f}%"
              f"   agreement {agree:.2f}%")
        print(f"        gear: " + "  ".join(f"{GEAR[k]}:{v}" for k, v in sorted(gc.items())))
        print(f"        speed bins |v|: " + "  ".join(
            f"{lo}-{hi}:{int(((np.abs(d['cs_v'])>=lo)&(np.abs(d['cs_v'])<hi)).sum())}"
            for lo, hi in [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 8)]))
        sus = sustained(d["tq"], fs)
        print(f"        hands-off (sustained<=200): {int((sus<=200).sum())}"
              f"  |  raw |tq|<=200: {int((np.abs(d['tq'])<=200).sum())}   <- raw is the WRONG test")
    print(f"\n   TOTAL {T} frames across {len(SEGS_31)} segments")

    hdr("A4. THE FOUR ARMS THIS ROUTE SUPPORTS (|v| <= 5 m/s throughout)")
    arms = {"engaged FORWARD (D, latActive)": lambda d: (d["cs_gear"] == 2) & (d["cc_lat"] > 0.5),
            "manual  FORWARD (D, !latActive)": lambda d: (d["cs_gear"] == 2) & (d["cc_lat"] <= 0.5),
            "manual  REVERSE (R)": lambda d: d["cs_gear"] == 4,
            "PARK": lambda d: d["cs_gear"] == 1}
    print(f"   {'arm':34s} {'frames':>8s} {'s':>7s} {'moving>0.3':>11s} {'med|v|':>8s}"
          f" {'med|ang|':>9s} {'med eff':>8s}")
    for name, fn in arms.items():
        nf = ns = nm = 0
        vs, ags, effs = [], [], []
        for s in SEGS_31:
            d = load(s)
            fs = fs_of(d)
            m = fn(d)
            if not m.any():
                continue
            nf += int(m.sum()); ns += m.sum() / fs
            nm += int((m & (np.abs(d["cs_v"]) > 0.3)).sum())
            vs.append(np.abs(d["cs_v"][m])); ags.append(np.abs(d["ang"][m]))
            sus = np.full(len(d["t"]), np.nan)
            sus[m] = sustained(d["tq"][m], fs)
            effs.append(sus[m])
        if nf == 0:
            print(f"   {name:34s} {0:8d}")
            continue
        print(f"   {name:34s} {nf:8d} {ns:7.1f} {nm:11d}"
              f" {np.median(np.concatenate(vs)):8.2f} {np.median(np.concatenate(ags)):9.1f}"
              f" {np.median(np.concatenate(effs)):8.0f}")
    print("\n   note: 'moving' = |vEgo| > 0.3 m/s. vEgo is a MAGNITUDE on this platform -- it does")
    print("   not go negative in reverse (min over the route is -0.10, i.e. estimator noise at rest),")
    print("   so gearShifter is the only direction signal and it is used as such.")


if __name__ == "__main__":
    main()
