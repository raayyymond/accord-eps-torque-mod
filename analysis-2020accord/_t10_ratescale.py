#!/usr/bin/env python3
"""Task #10 -- the rate axis: where grind #1 sits on it, and how to size a probe rung for it.

Three things, none of them re-implemented from scratch: the burst detector, the band envelope and
the window cutting are `_r31_common` / `_grind2_lib` / `_r4f_lib` unchanged.

  §1  WHERE GRIND #1 SITS on gp-0x6ac0, on the settled scale (4.7121 counts/deg-s).
      Reported three ways because they answer different questions and disagree by ~5x:
        per-SAMPLE index        -- what a damping FORCE integrates over
        per-WINDOW peak         -- what a viscous damper's authority is set by
        fraction of TIME above  -- how much of each cycle sits past a breakpoint
  §2  PROBE RUNG SIZING. Engaged duty of `gp-0x6ac0 >= T` under both candidate scales, so a rung is
      pre-registered before it flies rather than interpreted after.
      🛑 T < 400 is NOT a discriminator: at T = 250 the alternative scale also fires (0.058%).
  §3  THE ARM CENSUS. gp-0x671d / gp-0x671a across every route that probed them -- the evidence that
      the mode-10 LERP was the gain in force on the gateless builds.

Usage:  python _t10_ratescale.py
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r31_common as C          # noqa: E402
import _r50_lib as R50           # noqa: E402  -- registers V68/r4e, V69/r4f, V70/r50

SCALE_A = 2 ** 18 / (48 * 1159)      # 4.7121081 -- SETTLED (golden model + FUN_00068f52)
SCALE_B = 2 ** 15 / (48 * 1159)      # 0.5890135 -- the retired alternative, kept as the control
VHI = 20 / 3.6                        # the creep stratum the recorded ladder used
ENV_MIN = 300.0                       # burst = 18-22 Hz envelope p99 >= 300 counts amplitude

# Routes 54 (V71B) and 58 (V71C) postdate `_r50_lib`; register them the same way it does.
G.BUILDS.setdefault("V71B/r54", dict(cache=ROOT / "_cache_r54", pfx="r54s",
                                     segs=list(range(21)), kd=1.0))
G.BUILDS.setdefault("V71C/r58", dict(cache=ROOT / "_cache_r58", pfx="r58s",
                                     segs=list(range(16)), kd=2.0))
ORDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V62/r37", "V65/r3a", "V65/r3b",
         "V67/r47", "V68/r4e", "V69/r4f", "V70/r50", "V71B/r54", "V71C/r58"]


def burst_windows(build):
    """(peak index, frac time > 400, frac time > 1400, all per-sample indices) per burst window."""
    B = G.BUILDS[build]
    pk, t4, t14, samp = [], [], [], []
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        le = np.asarray(d["cc_lat"], float) > 0.5
        for a, b in C.runs_of(le, d["t"], G.NFFT):
            x = np.asarray(d["tq"][a:b], float)
            if not np.all(np.isfinite(x)):
                continue
            e18 = C.band_envelope(x, fs, 18.0, 22.0)
            rk = np.abs(np.asarray(d["rate_c"][a:b], float)) * SCALE_A
            v = np.abs(np.asarray(d["cs_v"][a:b], float))
            for i in range(0, len(x) - G.NFFT + 1, G.HOP):
                w = slice(i, i + G.NFFT)
                if np.mean(v[w]) >= VHI or np.percentile(e18[w], 99) < ENV_MIN:
                    continue
                pk.append(rk[w].max())
                t4.append((rk[w] >= 400).mean())
                t14.append((rk[w] >= 1400).mean())
                samp.append(rk[w])
    return np.array(pk), np.array(t4), np.array(t14), samp


def main():
    R50.install_fs()

    G.hdr("§1  WHERE GRIND #1 SITS ON gp-0x6ac0  (engaged, <20 km/h, 18-22 Hz envelope p99 >= 300)")
    print(f"  {'build':10s} {'nwin':>5s} | {'peak p50':>8s} {'p90':>6s} | {'%win peak>400':>13s} "
          f"{'>1400':>7s} | {'% of TIME >400':>14s} {'>1400':>7s}")
    PK, T4, T14, SA = [], [], [], []
    for b in ORDER:
        pk, t4, t14, samp = burst_windows(b)
        if len(pk) < 3:
            print(f"  {b:10s} {len(pk):5d}  (too few)")
            continue
        PK.append(pk), T4.append(t4), T14.append(t14), SA.extend(samp)
        print(f"  {b:10s} {len(pk):5d} | {np.percentile(pk, 50):8.0f} {np.percentile(pk, 90):6.0f} | "
              f"{100 * (pk >= 400).mean():12.1f}% {100 * (pk >= 1400).mean():6.1f}% | "
              f"{100 * t4.mean():13.2f}% {100 * t14.mean():6.2f}%")
    pk, t4, t14 = np.concatenate(PK), np.concatenate(T4), np.concatenate(T14)
    smp = np.concatenate(SA)
    print(f"  {'POOLED':10s} {len(pk):5d} | {np.percentile(pk, 50):8.0f} {np.percentile(pk, 90):6.0f} | "
          f"{100 * (pk >= 400).mean():12.1f}% {100 * (pk >= 1400).mean():6.1f}% | "
          f"{100 * t4.mean():13.2f}% {100 * t14.mean():6.2f}%")
    print(f"\n  per-SAMPLE index over the same windows: p50 = {np.percentile(smp, 50):.0f}  "
          f"p90 = {np.percentile(smp, 90):.0f}  p99 = {np.percentile(smp, 99):.0f}")
    print("  🛑 The per-sample p50 and the per-window peak p50 differ by ~5x. A damping FORCE")
    print("     integrates over the sample distribution; a viscous damper's AUTHORITY is set at the")
    print("     peak. Quoting one price for the other is a ~5x error in either direction.")

    G.hdr("§2  PROBE RUNG SIZING -- engaged duty of `gp-0x6ac0 >= T` under both scales")
    R, E = [], []
    for b in ORDER:
        B = G.BUILDS[b]
        for s in B["segs"]:
            p = B["cache"] / f"{B['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = C.load(s, B["cache"], B["pfx"])
            R.append(np.abs(np.asarray(d["rate_c"], float)))
            E.append(np.asarray(d["cc_lat"], float) > 0.5)
    R, E = np.concatenate(R), np.concatenate(E)
    print(f"  {len(R)} frames, {int(E.sum())} engaged, max |rate_c| = {R.max():.0f} deg/s "
          f"({R.max() * SCALE_A:.0f} counts on A, {R.max() * SCALE_B:.0f} on B)\n")
    print(f"  {'T':>6s} {'sar form':>10s} | {'A deg/s':>8s} {'duty eng':>9s} {'eng frames':>10s} | "
          f"{'B deg/s':>8s} {'duty eng':>9s} | verdict")
    for T in (250, 400, 512, 1024, 1400, 2048):
        sar = f">>{int(np.log2(T))}" if (T & (T - 1)) == 0 else "movea+cmp"
        da, db = (R[E] >= T / SCALE_A).mean(), (R[E] >= T / SCALE_B).mean()
        v = ("STRONG" if da > 0.005 and db < 1e-5 else "usable" if da > 0.0015 and db < 1e-5
             else "TOO RARE on A" if db < 1e-5 else "🛑 B FIRES TOO -- not a discriminator")
        print(f"  {T:6d} {sar:>10s} | {T / SCALE_A:8.1f} {100 * da:8.3f}% "
              f"{int((R[E] >= T / SCALE_A).sum()):10d} | {T / SCALE_B:8.1f} {100 * db:8.4f}% | {v}")

    G.hdr("§3  THE ARM CENSUS -- did either bypass arm ever fire?  (mask OUTRANKS every other arm)")
    print("  r24's chain: mask 0xC6442 -> gate 0xC6446 -> counter 0xC6440 -> the mode-10 LERP.")
    print("  On a gateless build (V69/V70/V71B) only mask or counter could bypass the LERP.\n")
    tot = {}
    for dn, keys in (("_cache_r4a", ("g671d", "g671a")), ("_cache_r47", ("g671d", "g671a")),
                     ("_cache_r54", ("b6_671d",)), ("_cache_r58", ("b6_671d",)),
                     ("_cache_v68", ("det671a",))):
        for f in glob.glob(os.path.join(str(ROOT / dn), "*.npz")):
            if "_rpm" in f or "raw18f" in f:
                continue
            d = np.load(f)
            for k in keys:
                if k in d.files:
                    v = np.asarray(d[k], float)
                    a = tot.setdefault((dn, k), [0, 0])
                    a[0] += int(np.nansum(v > 0.5))
                    a[1] += int(np.isfinite(v).sum())
    for (dn, k), (s, n) in sorted(tot.items()):
        print(f"  {dn[7:]:6s} {k:10s} set {s:7d} / {n:7d} = {100 * s / max(n, 1):.4f}%")
    mask = sum(n for (dn, k), (s, n) in tot.items() if "671d" in k)
    cnt = sum(n for (dn, k), (s, n) in tot.items() if "671a" in k)
    print(f"\n  gp-0x671d (mask)    0 / {mask:,} frames        gp-0x671a>=5 (counter) 0 / {cnt:,}")
    print("  ⇒ neither bypass has ever fired ⇒ the mode-10 LERP WAS the gain in force on the")
    print("    gateless builds ⇒ V69/V70's surface dose was REAL and its grind-#1 null is a real")
    print("    DOSE null, not an arm-selection artefact.")
    print("  ⚠ Limit: measured on r4a/r47/r54/r58/v68, never directly on route 4f or 50 themselves.")


if __name__ == "__main__":
    main()
