#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_buschange.py -- byte-level change-point scan across EVERY CAN address at the fault.

Re-walks route 5e segment 4 only (the fault is at 43.02 s into it) and, for every (src, addr),
compares each payload byte's value set in [T-8, T) against (T, T+8]. Reports every byte that
changes and STAYS changed -- i.e. every latched fault flag anywhere on the bus.

Also dumps the corrected spectra (the 0x14A sentinel sample excluded) and the UDS inventory.
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from rlog_parse import read_messages          # noqa: E402

RLOG = (ROOT / "analysis-2020accord" / "rlogs" /
        "75604b0a432fdc89_0000005e--857d0bd164--4--rlog.zst")
D = dict(np.load(ROOT / "_scratch/cache/r5e" / "r5e.npz"))
T0_ROUTE = float(D["t0_mono"][0])
t = D["t"]
K = int(np.flatnonzero((D["probe"].astype(int) & 7) == 4)[0])
T_FAULT = float(t[K])
W = 8.0
H = "=" * 100
print(f"fault at route t={T_FAULT:.4f} s (0x14A sample {K}); scanning segment 4 "
      f"for latched byte changes in +/-{W:.0f} s")

pre = defaultdict(lambda: defaultdict(set))
post = defaultdict(lambda: defaultdict(set))
npre, npost = defaultdict(int), defaultdict(int)
for evt in read_messages(RLOG):
    try:
        if evt.which() != "can":
            continue
    except Exception:
        continue
    tm = evt.logMonoTime * 1e-9 - T0_ROUTE
    if tm < T_FAULT - W or tm > T_FAULT + W:
        continue
    side = pre if tm < T_FAULT else post
    cnt = npre if tm < T_FAULT else npost
    for m in evt.can:
        key = (int(m.src), int(m.address))
        d = bytes(m.dat)
        cnt[key] += 1
        for i, b in enumerate(d):
            side[key][i].add(b)

print("\n" + H)
print("LATCHED BYTE CHANGES -- byte value sets DISJOINT between the two 8 s halves")
print(H)
hits = 0
for key in sorted(set(pre) | set(post)):
    src, addr = key
    if src not in (0, 1, 2):
        continue
    a, b = pre.get(key, {}), post.get(key, {})
    if not a or not b:
        print(f"  src{src} 0x{addr:03X}: present {'BEFORE only' if a else 'AFTER only'} "
              f"(n {npre[key]} -> {npost[key]})  *** message appeared/disappeared ***")
        hits += 1
        continue
    for i in sorted(set(a) | set(b)):
        sa, sb = a.get(i, set()), b.get(i, set())
        if sa and sb and not (sa & sb):
            print(f"  src{src} 0x{addr:03X} byte{i}: "
                  f"{sorted(sa)[:6]}{'...' if len(sa) > 6 else ''} -> "
                  f"{sorted(sb)[:6]}{'...' if len(sb) > 6 else ''}   "
                  f"(n {npre[key]} / {npost[key]})")
            hits += 1
print(f"\n  {hits} latched byte changes across {len(set(pre) | set(post))} (src,addr) pairs")

print("\n" + H)
print("CORRECTED SPECTRA -- the 0x14A sentinel sample EXCLUDED (index K)")
print(H)
for w_s in (0.3, 0.5):
    i0 = int(np.searchsorted(t, T_FAULT - w_s))
    print(f"  window [{t[i0]:.3f}, {t[K - 1]:.3f}]  ({K - i0} samples, sentinel excluded)")
    for nm, ch in (("drvTq 0x18F", D["tq"]), ("rate14 0x14A", D["rate_c"]),
                   ("rate18 0x18F", D["rate_f"]), ("angle 0x14A", D["ang"])):
        y = np.asarray(ch[i0:K], float)
        y = y - y.mean()
        n = len(y)
        fs = (n - 1) / (t[K - 1] - t[i0])
        Y = np.abs(np.fft.rfft(y * np.hanning(n))) ** 2
        f = np.fft.rfftfreq(n, 1 / fs)
        k = np.argsort(Y[1:])[::-1][:4] + 1
        print(f"    {nm:14s} p-p={ch[i0:K].max() - ch[i0:K].min():8.1f} "
              f"rms={np.std(ch[i0:K]):8.1f}  lines: " +
              "  ".join(f"{f[j]:5.1f}Hz({Y[j] / Y[k[0]]:.2f})" for j in k))
    print()

print("  --- CONTRAST: the noisiest earlier burst (t=67.4-67.6 s), same treatment ---")
for c in (67.5, 259.5, 155.3):
    i0 = int(np.searchsorted(t, c - 0.15))
    i1 = int(np.searchsorted(t, c + 0.15))
    for nm, ch in (("drvTq", D["tq"]), ("rate14", D["rate_c"])):
        y = np.asarray(ch[i0:i1], float)
        y = y - y.mean()
        n = len(y)
        fs = (n - 1) / (t[i1 - 1] - t[i0])
        Y = np.abs(np.fft.rfft(y * np.hanning(n))) ** 2
        f = np.fft.rfftfreq(n, 1 / fs)
        k = np.argsort(Y[1:])[::-1][:3] + 1
        print(f"    t={c:6.2f} {nm:7s} p-p={ch[i0:i1].max() - ch[i0:i1].min():7.1f}  lines: " +
              "  ".join(f"{f[j]:5.1f}Hz({Y[j] / Y[k[0]]:.2f})" for j in k))
