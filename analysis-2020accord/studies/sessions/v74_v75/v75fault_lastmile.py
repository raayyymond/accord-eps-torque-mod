#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_lastmile.py -- (i) the 0x450/0x440 warning frames at the fault, with payloads in time
order; (ii) the amplitude/HF ranking computed on windows that END at the last PRE-fault sample
(the earlier scripts' 0.1 s grid excluded the final 95 ms).
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages          # noqa: E402

D = dict(np.load(ROOT / "_scratch/cache/r5e" / "r5e.npz"))
T0 = float(D["t0_mono"][0])
t = D["t"]
K = int(np.flatnonzero((D["probe"].astype(int) & 7) == 4)[0])
T_FAULT = float(t[K])
H = "=" * 100

print(H)
print("(i) THE INSTRUMENT-CLUSTER WARNING CHANNEL 0x450 / 0x440 -- segment 4, in time order")
print(H)
RL = (ROOT / "analysis-2020accord" / "rlogs" /
      "75604b0a432fdc89_0000005e--857d0bd164--4--rlog.zst")
rows = []
for evt in read_messages(RL):
    try:
        if evt.which() != "can":
            continue
    except Exception:
        continue
    tm = evt.logMonoTime * 1e-9 - T0
    for m in evt.can:
        if int(m.address) in (0x440, 0x450):
            rows.append((tm, int(m.src), int(m.address), bytes(m.dat).hex()))
rows.sort()
for tm, src, addr, h in rows:
    print(f"  t={tm:9.4f} ({tm - T_FAULT:+8.4f} vs fault)  src{src:3d}  0x{addr:03X}  {h}")
print(f"  ⇒ {sum(1 for r in rows if r[0] > T_FAULT)} frames after the fault, "
      f"{sum(1 for r in rows if r[0] <= T_FAULT)} before, inside segment 4")

print("\n" + H)
print("(ii) SLIDING-WINDOW RANKING, windows ENDING at each sample (200 ms = 20 samples)")
print(H)
NW = 20
for nm, ch in (("drvTq 0x18F", D["tq"]), ("rate14 0x14A", D["rate_c"]),
               ("rate18 0x18F", D["rate_f"]), ("cmd 0x0E4", D["e4tq"])):
    x = np.asarray(ch[:K], float)
    ends = np.arange(NW, len(x) + 1)
    pp = np.array([x[e - NW:e].max() - x[e - NW:e].min() for e in ends])
    hf = np.array([np.mean(np.abs(np.diff(x[e - NW:e], 2))) for e in ends])
    j = len(ends) - 1                      # the window ending at the last pre-fault sample
    print(f"  {nm:13s} window [{t[ends[j] - NW]:.3f},{t[ends[j] - 1]:.3f}]  "
          f"p-p={pp[j]:8.1f} rank {int((pp > pp[j]).sum()) + 1:5d}/{len(pp)} "
          f"({100 * (1 - (pp > pp[j]).sum() / len(pp)):6.3f}pct)   "
          f"HF={hf[j]:7.1f} rank {int((hf > hf[j]).sum()) + 1:5d}/{len(hf)} "
          f"({100 * (1 - (hf > hf[j]).sum() / len(hf)):6.3f}pct)")
    top = np.argsort(hf)[::-1][:6]
    print(f"      top-6 HF windows end at t = " +
          "  ".join(f"{t[ends[i] - 1]:.2f}s({hf[i]:.0f})" for i in top))

# the joint condition, computed on the same end-aligned windows
x = np.asarray(D["tq"][:K], float)
r = np.asarray(D["rate_c"][:K], float)
lvl = D["thermo"][:K].astype(int)
lat = (D["cc_lat"][:K] > 0.5)
ends = np.arange(NW, len(x) + 1)
hf_t = np.array([np.mean(np.abs(np.diff(x[e - NW:e], 2))) for e in ends])
hf_r = np.array([np.mean(np.abs(np.diff(r[e - NW:e], 2))) for e in ends])
lv = np.array([lvl[e - NW:e].max() for e in ends])
lt = np.array([lat[e - NW:e].mean() > 0.5 for e in ends])
jf = len(ends) - 1
cond = (hf_t >= hf_t[jf]) & (hf_r >= hf_r[jf]) & (lv >= 2) & lt
print(f"\n  JOINT CONDITION (torque-HF >= the fault window's, rate-HF >= it, damper level >= 2, "
      f"engaged):\n    satisfied by {int(cond.sum())} of {len(ends)} end-aligned 200 ms windows "
      f"pre-fault (overlapping).")
# collapse overlapping windows into episodes
idx = np.flatnonzero(cond)
if len(idx):
    brk = np.flatnonzero(np.diff(idx) > NW)
    starts = np.r_[idx[0], idx[brk + 1]]
    endsx = np.r_[idx[brk], idx[-1]]
    print(f"    ⇒ {len(starts)} NON-OVERLAPPING episodes: " +
          "  ".join(f"{t[ends[a] - 1]:.2f}-{t[ends[b] - 1]:.2f}s" for a, b in zip(starts, endsx)))
    print("    🛑 exactly ONE of them ended in a fault ⇒ the joint condition is NOT sufficient; "
          "n=1 and untestable.")
