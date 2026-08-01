#!/usr/bin/env python3
"""analyze_gp6806_gate.py -- is gp-0x6806 an LKAS-applying gate, and is it SLOW?

Source: V57's cave probe, CAN 0x14A byte4 bit6 = (gp-0x6806 == 0), 100 Hz, routes 28 + 29.
Caches built by rlog-tools/extract_v57_gate_cache.py.

Three questions, in the order they can kill the plan:
  A3  is gp-0x6806 non-zero while LKAS is OFF?         -> if yes, not an engagement gate
  A1  does it agree with latActive / SCA / 0xE4 req?   -> the joint distribution
  A2  how fast does it toggle, and is there 15-50 Hz energy in the bit?

*** 100 Hz sampling: Nyquist is 50 Hz. Anything above 50 Hz folds. A 60 Hz toggle would appear at
40 Hz. So "no energy in 15-50 Hz" bounds 15-50 directly AND bounds 50-85 by its alias image.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FS = 100.0
SEGS = [("r28", s) for s in (10, 11, 12, 13, 14)] + [("r29", s) for s in (0, 1)]

BIT_LIVE, BIT_GATE = 0x80, 0x40


def load(rt, s):
    z = np.load(ROOT / f"_cache_{rt}" / f"{rt}s{s}.npz")
    d = {k: z[k] for k in z.files}
    d["tag"] = f"{rt}s{s}"
    return d


def transitions(x):
    return int((np.diff(x.astype(int)) != 0).sum())


def welch(x, nfft=512, fs=FS):
    """Mean periodogram, 50% overlap, Hann. Returns (f, P, K)."""
    x = np.asarray(x, float)
    if len(x) < nfft:
        return None, None, 0
    x = x - x.mean()
    w = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    acc, k = np.zeros(len(f)), 0
    for i in range(0, len(x) - nfft + 1, nfft // 2):
        acc += np.abs(np.fft.rfft(x[i:i + nfft] * w)) ** 2
        k += 1
    return f, acc / k, k


def main():
    D = [load(rt, s) for rt, s in SEGS]

    # ---------- liveness ----------
    print("=" * 100)
    print("LIVENESS  (field = (byte4>>3)&0x1F ; field==0 => cave did not fire => VOID)")
    print(f"  {'seg':8s} {'n':>7s} {'void':>7s} {'bit7':>8s}  byte4 histogram")
    tot_void = 0
    for d in D:
        b4 = d["probe"].astype(int)
        field = (b4 >> 3) & 0x1F
        void = int((field == 0).sum())
        tot_void += void
        from collections import Counter
        h = "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(b4).most_common(5))
        print(f"  {d['tag']:8s} {len(b4):7d} {void:7d} {int((b4 & BIT_LIVE != 0).sum()):8d}  {h}")
    print(f"  TOTAL VOID = {tot_void}")
    if tot_void:
        print("  *** partial void -- void frames are EXCLUDED from every table below")

    # ---------- pooled arrays ----------
    def cat(k):
        return np.concatenate([d[k] for d in D])

    b4 = cat("probe").astype(int)
    live = ((b4 >> 3) & 0x1F) != 0
    gate = (b4 & BIT_GATE) != 0          # gp-0x6806 == 0
    nz = ~gate                            # gp-0x6806 != 0   <-- the candidate gate signal
    lat = cat("cc_lat") > 0.5
    sca = cat("sca").astype(int) == 1
    e4r = cat("e4req").astype(int) == 1
    v = cat("cs_v")
    tq = cat("tq")
    n = len(b4)

    print()
    print("=" * 100)
    print(f"A1  JOINT DISTRIBUTION -- (gp-0x6806 != 0) vs each engagement proxy   [live frames only, "
          f"n={int(live.sum())} of {n}]")
    L = live
    for name, ref in (("carControl.latActive", lat), ("0x18F b4 bit3 STEER_CONTROL_ACTIVE", sca),
                      ("0x0E4 b2 bit7 STEER_TORQUE_REQUEST", e4r)):
        a, b = nz[L], ref[L]
        tt, tf, ft, ff = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum()), int((~a & ~b).sum())
        agree = 100.0 * (tt + ff) / len(a)
        print(f"\n  vs {name}")
        print(f"      {'':22s} {'proxy=1':>10s} {'proxy=0':>10s}")
        print(f"      gp-0x6806 != 0 {tt:16d} {tf:10d}")
        print(f"      gp-0x6806 == 0 {ft:16d} {ff:10d}")
        print(f"      agreement = {agree:.4f}%   "
              f"(false-ON {tf} = nonzero while proxy off; false-OFF {ft} = zero while proxy on)")

    print("\n  per-segment agreement with latActive:")
    for d in D:
        bb = d["probe"].astype(int)
        lv = ((bb >> 3) & 0x1F) != 0
        g = ((bb & BIT_GATE) != 0)[lv]
        la = (d["cc_lat"] > 0.5)[lv]
        print(f"    {d['tag']:8s} n={lv.sum():5d}  nz={100*(~g).mean():6.2f}%  "
              f"lat={100*la.mean():6.2f}%  agree={100*((~g) == la).mean():7.3f}%")

    print()
    print("=" * 100)
    print("A3  IS gp-0x6806 NON-ZERO WHILE LKAS IS OFF?")
    for name, ref in (("latActive", lat), ("SCA", sca), ("0xE4 req", e4r)):
        off = L & ~ref
        on = L & ref
        print(f"  by {name:10s}: disengaged n={int(off.sum()):6d}  "
              f"gp-0x6806 != 0 in {int(nz[off].sum()):6d}  ({100*nz[off].mean():6.3f}%)   ||   "
              f"engaged n={int(on.sum()):6d}  != 0 in {100*nz[on].mean():7.3f}%")
    seg13 = [d for d in D if d["tag"] == "r28s13"][0]
    b13 = seg13["probe"].astype(int)
    l13 = ((b13 >> 3) & 0x1F) != 0
    nz13 = ((b13 & BIT_GATE) == 0)[l13]
    print(f"\n  CLEAN DISENGAGED CONTROL r28s13 (lat 0.0% for 60 s): n={int(l13.sum())}  "
          f"gp-0x6806 != 0 in {int(nz13.sum())} ({100*nz13.mean():.3f}%)")

    print()
    print("=" * 100)
    print("A2  TOGGLE RATE OF THE (gp-0x6806 != 0) BIT   *** THE CRITICAL ONE ***")
    print(f"  {'seg':8s} {'dur_s':>7s} {'trans':>7s} {'tr/s':>8s} | "
          f"{'eng n':>6s} {'eng tr':>7s} {'eng tr/s':>9s} | "
          f"{'creep n':>7s} {'creep tr':>9s} {'creep tr/s':>11s}")
    rows = []
    for d in D:
        bb = d["probe"].astype(int)
        lv = ((bb >> 3) & 0x1F) != 0
        g = (bb & BIT_GATE) != 0
        x = (~g)[lv]
        t = d["t"][lv]
        dur = t[-1] - t[0]
        tr = transitions(x)
        la = (d["cc_lat"] > 0.5)[lv]
        vv = d["cs_v"][lv]
        eng = la
        creep = la & (vv > 0.2) & (vv <= 5.35)
        # transitions *within* contiguous runs of the condition, so entering/leaving does not count
        def cond_tr(sel):
            if sel.sum() < 2:
                return 0, 0.0
            idx = np.flatnonzero(sel)
            brk = np.flatnonzero(np.diff(idx) != 1)
            starts = np.concatenate(([0], brk + 1))
            ends = np.concatenate((brk, [len(idx) - 1]))
            c, secs = 0, 0.0
            for a_, b_ in zip(starts, ends):
                seg = idx[a_:b_ + 1]
                if len(seg) < 2:
                    continue
                c += transitions(x[seg])
                secs += t[seg[-1]] - t[seg[0]]
            return c, secs
        etr, esec = cond_tr(eng)
        ctr, csec = cond_tr(creep)
        rows.append((d["tag"], dur, tr, x, t, eng, creep))
        print(f"  {d['tag']:8s} {dur:7.1f} {tr:7d} {tr/dur:8.3f} | "
              f"{int(eng.sum()):6d} {etr:7d} {etr/esec if esec else float('nan'):9.3f} | "
              f"{int(creep.sum()):7d} {ctr:9d} {ctr/csec if csec else float('nan'):11.3f}")

    # ---------- run lengths ----------
    print("\n  RUN LENGTHS of the non-zero state (pooled, live frames, per segment concatenated"
          " but runs not spliced):")
    runs_on, runs_off = [], []
    for tag, dur, tr, x, t, eng, creep in rows:
        if len(x) == 0:
            continue
        ch = np.flatnonzero(np.diff(x.astype(int)) != 0) + 1
        bounds = np.concatenate(([0], ch, [len(x)]))
        for a_, b_ in zip(bounds[:-1], bounds[1:]):
            (runs_on if x[a_] else runs_off).append((b_ - a_) / FS)
    for nm, r in (("non-zero (candidate gate ON)", runs_on), ("zero (gate OFF)", runs_off)):
        r = np.array(r)
        if len(r) == 0:
            continue
        print(f"    {nm:30s} n={len(r):5d}  min={r.min()*1000:8.1f} ms  "
              f"median={np.median(r)*1000:9.1f} ms  p90={np.percentile(r,90)*1000:9.1f} ms  "
              f"max={r.max():7.2f} s   frac<50ms={100*np.mean(r<0.05):5.2f}%")

    # ---------- spectrum ----------
    print("\n  SPECTRUM of the bit (Welch, nfft=512 -> 0.195 Hz bins, 50% overlap). Nyquist = 50 Hz.")
    print(f"  {'seg':8s} {'K':>4s} {'DC-excl peak':>14s} {'peak Hz':>9s} "
          f"{'15-50Hz pk':>11s} {'@Hz':>7s} {'prom vs 5-50 med':>18s} {'frac pwr>15Hz':>15s}")
    for tag, dur, tr, x, t, eng, creep in rows:
        f, P, K = welch(x.astype(float))
        if not K:
            print(f"  {tag:8s}  too short")
            continue
        m = f > 0.5
        j = int(np.argmax(np.where(m, P, -np.inf)))
        hb = (f >= 15) & (f <= 50)
        jh = int(np.argmax(np.where(hb, P, -np.inf)))
        med = np.median(P[(f >= 5) & (f <= 50)])
        frac = P[f >= 15].sum() / P[f > 0].sum()
        print(f"  {tag:8s} {K:4d} {P[j]:14.4g} {f[j]:9.2f} {P[jh]:11.4g} {f[jh]:7.2f} "
              f"{P[jh]/med if med > 0 else float('nan'):18.2f} {100*frac:14.3f}%")

    # engaged-only spectrum, longest contiguous engaged run per segment
    print("\n  SPECTRUM restricted to the LONGEST contiguous ENGAGED run per segment:")
    for tag, dur, tr, x, t, eng, creep in rows:
        idx = np.flatnonzero(eng)
        if len(idx) < 600:
            print(f"  {tag:8s}  no engaged run >= 6 s")
            continue
        brk = np.flatnonzero(np.diff(idx) != 1)
        starts = np.concatenate(([0], brk + 1))
        ends = np.concatenate((brk, [len(idx) - 1]))
        best = max(zip(starts, ends), key=lambda ab: ab[1] - ab[0])
        seg = idx[best[0]:best[1] + 1]
        xs = x[seg].astype(float)
        if len(xs) < 512:
            print(f"  {tag:8s}  longest engaged run only {len(xs)/FS:.1f} s")
            continue
        if xs.std() == 0:
            print(f"  {tag:8s}  engaged run {len(xs)/FS:5.1f} s: bit CONSTANT at {int(xs[0])} "
                  f"-- no spectrum exists (strongest possible 'slow' result)")
            continue
        f, P, K = welch(xs)
        hb = (f >= 15) & (f <= 50)
        jh = int(np.argmax(np.where(hb, P, -np.inf)))
        med = np.median(P[(f >= 5) & (f <= 50)])
        print(f"  {tag:8s}  engaged run {len(xs)/FS:5.1f} s  K={K}  transitions={transitions(x[seg])}  "
              f"15-50Hz peak {P[jh]:.4g} @ {f[jh]:.2f} Hz  prom {P[jh]/med:.2f}x")


if __name__ == "__main__":
    main()
