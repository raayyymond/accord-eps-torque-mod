#!/usr/bin/env python3
"""V74 clean-flight baseline, route 5d -- state occupancy, engagement crosstab, transitions.

Read-only over `_scratch/cache/r5d/r5ds*.npz`. Two independent passes on every count that is load-bearing:
  A. the DECODED grid column `d["state"]`, which is `(probe & 0x78) >> 3` on the 0x14A row lattice;
  B. the RAW arrival array `d["raw14_b4"]`, every 0x14A src-1 frame exactly as it arrived, no grid,
     no hold, decoded here from scratch rather than reusing the extractor's arithmetic.
A and B have different lengths by construction (rows start at the first 0x18F), so they are genuinely
separate populations, not the same array twice.
"""
import json
import sys
from collections import Counter

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = "_scratch/cache/r5d"
PFX = "r5ds"
SEGS = list(range(17))

STATE_SHIFT, STATE_MASK, STATE_FIELD = 3, 0xF, 0x78
BIT_DAMP = 0x80
STATUS_MASK = 0x07
REACHABLE = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
UNREACHABLE = {0, 2, 12, 13, 14, 15}


def load(seg):
    return dict(np.load(f"{CACHE}/{PFX}{seg}.npz"))


def main():
    tot_frames = 0
    tot_sec = 0.0
    hist_dec = Counter()
    hist_raw = Counter()
    b4_raw = Counter()
    sec_by_state = Counter()
    # crosstab: state x engagement, on three independent engagement channels
    ct_lat = Counter()      # (state, latActive>0.5)
    ct_cruise = Counter()   # (state, cruiseState.enabled>0.5)
    ct_sca = Counter()      # (state, 0x18F b4 bit3)
    trans = Counter()       # (prev_state, state) within-segment, frame to frame
    trans_chg = Counter()   # only where prev != cur
    seg_rows = []
    state8_events = []

    for s in SEGS:
        d = load(s)
        t = d["t"]
        n = len(t)
        st = d["state"].astype(int)
        p = d["probe"].astype(int)
        # --- pass A sanity: the decoded column must equal a from-scratch decode of `probe`
        st_a = (p & STATE_FIELD) >> STATE_SHIFT
        assert np.array_equal(st, st_a), f"seg{s}: d['state'] != (probe&0x78)>>3"
        lat = d["cc_lat"] > 0.5
        cru = d["cs_eng"] > 0.5
        sca = d["sca"] == 1
        v = d["cs_v"]

        dur = float(t[-1] - t[0])
        dt = np.diff(t, prepend=t[0])
        dt[0] = np.median(dt[1:])
        tot_frames += n
        tot_sec += dur

        for val, c in zip(*np.unique(st, return_counts=True)):
            hist_dec[int(val)] += int(c)
            sec_by_state[int(val)] += float(dt[st == val].sum())
        for val, c in zip(*np.unique(st[lat], return_counts=True)):
            ct_lat[(int(val), True)] += int(c)
        for val, c in zip(*np.unique(st[~lat], return_counts=True)):
            ct_lat[(int(val), False)] += int(c)
        for val, c in zip(*np.unique(st[cru], return_counts=True)):
            ct_cruise[(int(val), True)] += int(c)
        for val, c in zip(*np.unique(st[~cru], return_counts=True)):
            ct_cruise[(int(val), False)] += int(c)
        for val, c in zip(*np.unique(st[sca], return_counts=True)):
            ct_sca[(int(val), True)] += int(c)
        for val, c in zip(*np.unique(st[~sca], return_counts=True)):
            ct_sca[(int(val), False)] += int(c)

        if n > 1:
            for a, b in zip(st[:-1], st[1:]):
                trans[(int(a), int(b))] += 1
                if a != b:
                    trans_chg[(int(a), int(b))] += 1

        # --- pass B: raw arrivals, decoded here, independent of the extractor
        raw = d["raw14_b4"].astype(int)
        for val, c in zip(*np.unique(raw, return_counts=True)):
            b4_raw[int(val)] += int(c)
            hist_raw[(int(val) & STATE_FIELD) >> STATE_SHIFT] += int(c)

        # --- state 8 census (decoded pass), with context
        i8 = np.flatnonzero(st == 8)
        for i in i8:
            state8_events.append(dict(seg=s, t=float(t[i]), v=float(v[i]),
                                      lat=bool(lat[i]), prev=int(st[i - 1]) if i else -1))

        seg_rows.append(dict(seg=s, n=n, dur=dur, states=dict(Counter(st.tolist())),
                             lat_pct=100.0 * lat.mean(), vmax=float(np.nanmax(v)),
                             damp_pct=100.0 * float(d["damp_nz"].mean())))

    print("=" * 88)
    print(f"ROUTE 5d / V74 -- {len(SEGS)} segments, {tot_frames} frames on the 0x14A lattice, "
          f"{tot_sec:.1f} s")
    print(f"                  raw-arrival pass: {sum(hist_raw.values())} 0x14A src1 frames")
    print("=" * 88)

    print("\n--- 1. STATE OCCUPANCY -----------------------------------------------------------")
    print(f"{'state':>6} {'A: decoded':>12} {'%':>9} {'seconds':>10} | {'B: raw arrivals':>16} "
          f"{'%':>9}  reachable?")
    nA, nB = sum(hist_dec.values()), sum(hist_raw.values())
    for k in sorted(set(hist_dec) | set(hist_raw)):
        a, b = hist_dec.get(k, 0), hist_raw.get(k, 0)
        tag = "yes" if k in REACHABLE else "*** UNREACHABLE ***"
        print(f"{k:>6} {a:>12} {100.0*a/nA:>8.4f}% {sec_by_state[k]:>9.2f}s | {b:>16} "
              f"{100.0*b/nB:>8.4f}%  {tag}")
    illegal_A = sum(c for k, c in hist_dec.items() if k in UNREACHABLE)
    illegal_B = sum(c for k, c in hist_raw.items() if k in UNREACHABLE)
    print(f"\n  frames at a STRUCTURALLY UNREACHABLE state: A={illegal_A}  B={illegal_B}")

    print("\n  RAW 0x14A byte4 alphabet (all values seen, whole route):")
    for k in sorted(b4_raw):
        st_ = (k & STATE_FIELD) >> STATE_SHIFT
        print(f"    0x{k:02X}  n={b4_raw[k]:>7}  damp={1 if k & BIT_DAMP else 0}  state={st_:>2}  "
              f"status={k & STATUS_MASK}")

    print("\n--- 2. STATE x ENGAGEMENT --------------------------------------------------------")
    for name, ct in (("carControl.latActive", ct_lat),
                     ("carState.cruiseState.enabled", ct_cruise),
                     ("0x18F b4 bit3 STEER_CONTROL_ACTIVE", ct_sca)):
        states = sorted({k[0] for k in ct})
        print(f"\n  {name}")
        print(f"    {'state':>6} {'ENGAGED':>12} {'MANUAL':>12} {'tot':>12}  {'%eng':>8}")
        for s_ in states:
            e, m = ct.get((s_, True), 0), ct.get((s_, False), 0)
            print(f"    {s_:>6} {e:>12} {m:>12} {e+m:>12}  {100.0*e/(e+m):>7.3f}%")
        e = sum(c for k, c in ct.items() if k[1])
        m = sum(c for k, c in ct.items() if not k[1])
        print(f"    {'TOT':>6} {e:>12} {m:>12} {e+m:>12}  {100.0*e/(e+m):>7.3f}%")

    print("\n--- 3. STATE 8 ON A CLEAN DRIVE --------------------------------------------------")
    print(f"  decoded pass  : state==8 on {hist_dec.get(8,0)} / {nA} frames")
    print(f"  raw-arrival   : state==8 on {hist_raw.get(8,0)} / {nB} frames")
    print(f"  raw byte4 values with state 8 (0x40..0x47 | damp 0xC0..0xC7): "
          f"{[hex(k) for k in b4_raw if ((k & STATE_FIELD) >> STATE_SHIFT) == 8] or 'NONE'}")
    for ev in state8_events[:20]:
        print(f"    seg{ev['seg']} t={ev['t']:.3f} v={ev['v']:.2f} lat={ev['lat']} "
              f"prev={ev['prev']}")

    print("\n--- 4. TRANSITION MATRIX ---------------------------------------------------------")
    print(f"  frame-to-frame pairs (within segment): {sum(trans.values())}")
    print("  ALL transitions where state CHANGED:")
    if not trans_chg:
        print("    NONE -- the state never changed on any frame boundary in the whole route.")
    for (a, b), c in sorted(trans_chg.items(), key=lambda kv: -kv[1]):
        print(f"    {a:>2} -> {b:<2}  n={c}")
    print("\n  predecessor distribution per state (from the changed-transition set + self-loops):")
    for tgt in sorted({b for _, b in trans}):
        preds = {a: c for (a, b), c in trans.items() if b == tgt}
        tot = sum(preds.values())
        pstr = "  ".join(f"{a}:{c} ({100.0*c/tot:.4f}%)" for a, c in sorted(preds.items()))
        print(f"    into {tgt:>2}: {pstr}")

    print("\n--- per-segment ------------------------------------------------------------------")
    print(f"  {'seg':>4} {'n':>7} {'dur':>8} {'lat%':>7} {'vmax':>7} {'damp%':>7}  states")
    for r in seg_rows:
        print(f"  {r['seg']:>4} {r['n']:>7} {r['dur']:>7.1f}s {r['lat_pct']:>6.1f}% "
              f"{r['vmax']:>6.2f} {r['damp_pct']:>6.2f}%  {r['states']}")

    json.dump(dict(frames=tot_frames, sec=tot_sec,
                   hist_decoded={str(k): v for k, v in hist_dec.items()},
                   hist_raw={str(k): v for k, v in hist_raw.items()},
                   byte4={hex(k): v for k, v in b4_raw.items()},
                   trans_changed={f"{a}->{b}": c for (a, b), c in trans_chg.items()},
                   state8_decoded=hist_dec.get(8, 0), state8_raw=hist_raw.get(8, 0)),
              open("v74base_state.json", "w"), indent=1)


if __name__ == "__main__":
    main()
