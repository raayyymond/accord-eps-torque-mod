#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_flags.py -- route-wide history of every byte that LATCHED at the fault.

`studies/sessions/v74_v75/v75fault_buschange.py` found the latched bytes inside +/-8 s. This walks the WHOLE route so the
claim "this byte was X for the entire drive and became Y at the fault, and never went back" is
[EVIDENCE] rather than an 8 s window.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages          # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_0000005e--857d0bd164"
D = dict(np.load(ROOT / "_scratch/cache/r5e" / "r5e.npz"))
T0 = float(D["t0_mono"][0])
t = D["t"]
K = int(np.flatnonzero((D["probe"].astype(int) & 7) == 4)[0])
T_FAULT = float(t[K])
H = "=" * 100

WATCH = {(1, 0x18F): [4, 5, 6], (1, 0x1AB): [0, 2], (1, 0x14A): [0, 2, 4, 5],
         (1, 0x1EA): None, (1, 0x30C): None}
RARE = {(0, 0x440), (2, 0x450), (2, 0x440), (0, 0x450), (130, 0x440), (130, 0x450)}

hist = defaultdict(list)          # (src,addr,byte) -> [(t, val)]
rare_t = defaultdict(list)
for s in range(7):
    p = RLOGDIR / f"{ROUTE}--{s}--rlog.zst"
    for evt in read_messages(p):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9 - T0
        for m in evt.can:
            key = (int(m.src), int(m.address))
            if key in RARE:
                rare_t[key].append((tm, bytes(m.dat).hex()))
                continue
            if key not in WATCH:
                continue
            d = bytes(m.dat)
            idxs = WATCH[key] if WATCH[key] is not None else range(len(d))
            for i in idxs:
                if i < len(d):
                    hist[(key[0], key[1], i)].append((tm, d[i]))
    print(f"  seg {s} scanned", flush=True)

print("\n" + H)
print("ROUTE-WIDE HISTORY OF THE LATCHED BYTES")
print(H)
for k in sorted(hist):
    src, addr, i = k
    a = np.array(hist[k], float)
    tt, vv = a[:, 0], a[:, 1].astype(int)
    pre = tt < T_FAULT
    up, cp = np.unique(vv[pre], return_counts=True)
    uq, cq = np.unique(vv[~pre], return_counts=True)
    print(f"\n  src{src} 0x{addr:03X} byte{i}   n={len(vv)}")
    print(f"    PRE  ({int(pre.sum()):6d}): " +
          " ".join(f"0x{int(a_):02X}:{int(b_)}" for a_, b_ in zip(up[:12], cp[:12])) +
          (" ..." if len(up) > 12 else ""))
    print(f"    POST ({int((~pre).sum()):6d}): " +
          " ".join(f"0x{int(a_):02X}:{int(b_)}" for a_, b_ in zip(uq[:12], cq[:12])) +
          (" ..." if len(uq) > 12 else ""))
    if len(up) and len(uq) and len(up) <= 4 and len(uq) <= 4 and not (set(up) & set(uq)):
        # exact first-change time
        j = int(np.flatnonzero(~np.isin(vv, up))[0])
        print(f"    ⇒ LATCHED, DISJOINT.  first non-pre value 0x{vv[j]:02X} at t={tt[j]:.4f} "
              f"({tt[j] - T_FAULT:+.4f} s vs the 0x14A fault frame)")

print("\n" + H)
print("RARE MESSAGES THAT APPEARED AT THE FAULT")
print(H)
for k in sorted(rare_t):
    src, addr = k
    v = rare_t[k]
    print(f"  src{src} 0x{addr:03X}: n={len(v)}  times " +
          " ".join(f"{x[0]:.2f}" for x in v[:20]) + (" ..." if len(v) > 20 else ""))
    if v:
        print(f"    payloads: " + "  ".join(sorted({x[1] for x in v})[:6]))

print("\n" + H)
print("RATE14 / DRVTQ AMPLITUDE RANKING -- the 200 ms ending at the last PRE-fault sample")
print(H)
for nm, ch in (("drvTq 0x18F", D["tq"]), ("rate14 0x14A", D["rate_c"]),
               ("rate18 0x18F", D["rate_f"])):
    pp, hf, mids = [], [], []
    a = t[0]
    while a + 0.2 <= T_FAULT:
        m = (t >= a) & (t < a + 0.2)
        if m.sum() >= 10:
            pp.append(float(ch[m].max() - ch[m].min()))
            hf.append(float(np.mean(np.abs(np.diff(ch[m], 2)))))
            mids.append(a + 0.1)
        a += 0.1
    pp, hf, mids = np.array(pp), np.array(hf), np.array(mids)
    j = int(np.argmax(mids))
    print(f"  {nm:14s} last window [{mids[j] - 0.1:.2f},{mids[j] + 0.1:.2f}]  "
          f"p-p={pp[j]:8.1f} (rank {int((pp > pp[j]).sum()) + 1}/{len(pp)}, "
          f"{100 * (1 - (pp > pp[j]).sum() / len(pp)):6.2f}pct)   "
          f"HF={hf[j]:7.1f} (rank {int((hf > hf[j]).sum()) + 1}/{len(hf)}, "
          f"{100 * (1 - (hf > hf[j]).sum() / len(hf)):6.2f}pct)")
