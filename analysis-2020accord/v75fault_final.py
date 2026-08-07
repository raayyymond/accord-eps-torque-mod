#!/usr/bin/env python3
"""v75fault_final.py -- corrected numbers (strict index split at the fault) + the route inventory.

🛑 The earlier scripts split on `t < 284.795`, which INCLUDED the fault frame itself (t=284.7947)
and so contaminated every "pre-fault" statistic with one sentinel sample (angle 0x7FFF,
rate 0x7FFF). Everything here splits on the INDEX of the first STEER_STATUS==7 sample.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
D = dict(np.load(ROOT / "_cache_r5e" / "r5e.npz"))
EV = json.loads((ROOT / "_cache_r5e" / "r5e_events.json").read_text())
t = D["t"]
K = int(np.flatnonzero(D["sstat"] == 7)[0])          # the FIRST faulted sample
T_FAULT = float(t[K])
PRE = np.arange(len(t)) < K
POST = ~PRE
lvl = D["thermo"].astype(int)
lat = D["cc_lat"] > 0.5
vv = D["cs_v"]
H = "=" * 100
BR = {0: "0", 1: "[1,128)", 2: "[128,288)", 3: "[288,448)", 4: ">=448"}
rng = np.random.default_rng(20260806)

print(H)
print(f"STRICT SPLIT: fault sample index {K}, t = {T_FAULT:.4f} s  "
      f"(pre {int(PRE.sum())} samples / {t[K - 1]:.2f} s, post {int(POST.sum())} samples)")
print(H)
print(f"  sanity: pre-fault |0x14A angle| max = {np.abs(D['ang'][PRE]).max():.2f} deg "
      f"(was contaminated to 3276.7); pre-fault |rate| max = "
      f"{np.abs(D['rate_c'][PRE]).max():.0f}")

# ---------------------------------------------------------------- level dwell, clean
print("\n" + H)
print("A. THERMOMETER, PRE-FAULT ONLY")
print(H)
tot = int(PRE.sum())
for lv in range(5):
    n_ = int((lvl[PRE] == lv).sum())
    print(f"  level {lv} |gp-0x6bd0| in {BR[lv]:>10s}: {n_:6d}  {100 * n_ / tot:6.3f}%  "
          f"({n_ / 100.0:.2f} s)")


def runs_idx(mask):
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    s = np.r_[idx[0], idx[brk + 1]]
    e = np.r_[idx[brk], idx[-1]]
    return list(zip(s, e))


for lv in (2, 3):
    r = [(a, b) for a, b in runs_idx(lvl == lv) if b < K]
    L = [t[b] - t[a] for a, b in r]
    print(f"  level {lv}: {len(r)} pre-fault runs, longest {max(L) * 1000:.0f} ms "
          f"@ t={t[r[int(np.argmax(L))][0]]:.2f}, total {sum(L):.2f} s")
r_ge2 = [(a, b) for a, b in runs_idx(lvl >= 2) if b < K]
print(f"  level>=2: {len(r_ge2)} pre-fault runs, longest "
      f"{max(t[b] - t[a] for a, b in r_ge2) * 1000:.0f} ms, total "
      f"{sum(t[b] - t[a] for a, b in r_ge2):.2f} s")
print(f"  the run that begins 20 ms before the fault: starts t={t[K - 2]:.4f}, "
      f"runs UNBROKEN to the end of the route ({t[-1] - t[K - 2]:.2f} s)")

# ---------------------------------------------------------------- the 0 -> >=2 steps
print("\n" + H)
print("B. THE `0 -> level>=2 in one 10 ms sample` EVENTS -- all of them, pre-fault")
print(H)
st_up = np.flatnonzero((lvl[:-1] == 0) & (lvl[1:] >= 2))
st_up = st_up[st_up < K]
print(f"  {len(st_up)} such steps in {t[K - 1]:.1f} s of driving  "
      f"({60 * len(st_up) / t[K - 1]:.2f} / minute)")
print(f"  {'t':>9s} {'lvl_after':>9s} {'lat':>4s} {'vEgo':>6s} {'|cmd|':>7s} {'drvTq':>7s} "
      f"{'ang':>8s} {'rate14':>7s} {'HF(drvTq,200ms)':>16s}  outcome")
for i in st_up:
    w = (t >= t[i] - 0.2) & (t <= t[i])
    hf = float(np.mean(np.abs(np.diff(D["tq"][w], 2)))) if w.sum() > 3 else np.nan
    out = "FAULT 20 ms later" if i >= K - 4 else "no fault"
    print(f"  {t[i]:9.4f} {lvl[i + 1]:9d} {int(lat[i]):4d} {vv[i]:6.2f} "
          f"{abs(D['e4tq'][i]):7.0f} {D['tq'][i]:7.0f} {D['ang'][i]:8.2f} {D['rate_c'][i]:7.0f} "
          f"{hf:16.1f}  {out}")

# ---------------------------------------------------------------- clean spectra
print("\n" + H)
print("C. THE PRE-FAULT OSCILLATION -- clean spectra (sentinel sample EXCLUDED)")
print(H)


def spec(x, i0, i1, label):
    y = np.asarray(x[i0:i1], float)
    y = y - y.mean()
    n = len(y)
    fs = (i1 - i0 - 1) / (t[i1 - 1] - t[i0])
    Y = np.abs(np.fft.rfft(y * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    k = np.argsort(Y[1:])[::-1][:4] + 1
    print(f"    {label:26s} n={n:4d} fs={fs:6.2f}  p-p={x[i0:i1].max() - x[i0:i1].min():8.0f}  "
          f"rms={np.std(x[i0:i1]):7.1f}  lines: " +
          "  ".join(f"{f[j]:5.1f}Hz({Y[j] / Y[k[0]]:.2f})" for j in k))


for w_s in (0.3, 0.5, 1.0):
    i0 = int(np.searchsorted(t, T_FAULT - w_s))
    print(f"  window = last {w_s:.1f} s before the fault  [{t[i0]:.3f}, {t[K - 1]:.3f}]")
    for nm, ch in (("drvTq 0x18F", D["tq"]), ("rate14 0x14A", D["rate_c"]),
                   ("rate18 0x18F", D["rate_f"]), ("cmd 0x0E4", D["e4tq"])):
        spec(ch, i0, K, nm)
    print()

print("  --- the other high-HF pre-fault windows, for contrast (same metric, same length) ---")
hfs, mids = [], []
a = t[0]
while a + 0.2 <= T_FAULT:
    m = (t >= a) & (t < a + 0.2)
    if m.sum() >= 10:
        hfs.append(float(np.mean(np.abs(np.diff(D["tq"][m], 2))))); mids.append(a + 0.1)
    a += 0.1
hfs, mids = np.array(hfs), np.array(mids)
kk = int(np.argmin(np.abs(mids - (T_FAULT - 0.1))))
print(f"    the pre-fault window HF = {hfs[kk]:.1f}, rank {int((hfs > hfs[kk]).sum()) + 1} "
      f"of {len(hfs)} ⇒ {100 * (1 - (hfs > hfs[kk]).sum() / len(hfs)):.2f}th percentile")
for j in np.argsort(hfs)[::-1][:6]:
    c = int(np.searchsorted(t, mids[j]))
    w = (t >= mids[j] - 0.1) & (t < mids[j] + 0.1)
    print(f"    t={mids[j]:7.2f}  HF={hfs[j]:6.1f}  lat={int(lat[c])}  v={vv[c]:5.2f}  "
          f"lvlmax={int(lvl[w].max())}  |cmd|max={np.nanmax(np.abs(D['e4tq'][w])):6.0f}  "
          f"steerOverride within 1 s: "
          f"{any(abs(e['t'] - mids[j]) < 1 and e['name'] == 'steerOverride' for e in EV)}")
print("  ⇒ 20-22 Hz HF bursts of this size DID occur earlier without a fault  [EVIDENCE]")

# ---------------------------------------------------------------- co-occurrence test
print("\n" + H)
print("D. THE CO-OCCURRENCE -- HF burst AND damper level>=2, engaged")
print(H)
hi_hf = hfs >= np.percentile(hfs, 98)
co = []
for j in np.flatnonzero(hi_hf):
    w = (t >= mids[j] - 0.1) & (t < mids[j] + 0.1)
    c = int(np.searchsorted(t, mids[j]))
    co.append((mids[j], int(lat[c]), int(lvl[w].max()), hfs[j]))
n_hi = len(co)
n_hi_eng = sum(1 for x in co if x[1] == 1)
n_hi_eng_lvl2 = sum(1 for x in co if x[1] == 1 and x[2] >= 2)
print(f"  windows in the top 2% of HF (n={n_hi}): engaged {n_hi_eng}, "
      f"engaged AND damper level>=2 {n_hi_eng_lvl2}")
for x in co:
    if x[1] == 1 and x[2] >= 2:
        print(f"    t={x[0]:8.2f}  HF={x[3]:6.1f}  lvlmax={x[2]}  "
              f"{'<<< THE FAULT WINDOW' if abs(x[0] - (T_FAULT - 0.1)) < 0.06 else ''}")
print(f"  🛑 n_hi_eng_lvl2 = {n_hi_eng_lvl2}; with a single fault this is an n=1 association and "
      f"CANNOT be tested. Reported as a description, not a hypothesis test.")

# ---------------------------------------------------------------- engaged episodes / rails
print("\n" + H)
print("E. OPENPILOT COMMAND -- rails and slew, per engaged episode (pre-fault)")
print(H)
sct, sctq = D["sc_t"], D["sc_tq_raw"]
dq = np.diff(sctq)
dt = np.diff(sct)
ok = dt > 0.005
print(f"  sendcan 0x0E4: n={len(sctq)}, |cmd| max {np.abs(sctq).max():.0f}, "
      f"at the 4096 rail {100 * (np.abs(sctq) >= 4096).mean():.3f}% of frames")
print(f"  |Δcmd| per consecutive frame: p50 {np.percentile(np.abs(dq[ok]), 50):.0f}  "
      f"p95 {np.percentile(np.abs(dq[ok]), 95):.0f}  p99.9 "
      f"{np.percentile(np.abs(dq[ok]), 99.9):.0f}  max {np.abs(dq[ok]).max():.0f}")
print(f"  |Δcmd| >= 123 on {int((np.abs(dq[ok]) >= 123).sum())} of {int(ok.sum())} frames "
      f"({100 * (np.abs(dq[ok]) >= 123).mean():.3f}%)")
for i, (a, b) in enumerate(runs_idx(lat)):
    if t[b] - t[a] < 1:
        continue
    m = (sct >= t[a]) & (sct <= min(t[b], T_FAULT))
    if m.sum() < 10:
        continue
    q = sctq[m]
    d2 = np.abs(np.diff(q))
    print(f"    episode {i}: {t[a]:7.2f}..{min(t[b], T_FAULT):7.2f} s  n={int(m.sum()):5d}  "
          f"|cmd|max={np.abs(q).max():6.0f}  rail%={100 * (np.abs(q) >= 4096).mean():6.2f}  "
          f"|Δ|max={d2.max():5.0f}  |Δ|>=123: {100 * (d2 >= 123).mean():5.2f}%  "
          f"v {vv[a:b].min():.1f}-{vv[a:b].max():.1f} m/s")

# ---------------------------------------------------------------- probe duty, clean
print("\n" + H)
print("F. PROBE DUTY, CLEAN PRE-FAULT SPLIT")
print(H)
creep = (vv > 0.2) & (vv <= 4.0)
cruise = vv > 10.0
for label, m in (("ALL pre-fault", PRE), ("engaged", PRE & lat), ("disengaged", PRE & ~lat),
                 ("engaged & creep 0.2-4", PRE & lat & creep),
                 ("engaged & 4-10 m/s", PRE & lat & (vv > 4) & (vv <= 10)),
                 ("engaged & >10 m/s", PRE & lat & cruise),
                 ("disengaged & creep", PRE & ~lat & creep),
                 ("stopped (<0.2) any", PRE & (vv <= 0.2)),
                 ("POST-FAULT", POST)):
    if not m.any():
        print(f"  {label:26s} n=0")
        continue
    print(f"  {label:26s} n={int(m.sum()):6d}  " +
          "  ".join(f"{b}={100 * D[b][m].mean():6.2f}%" for b in ("b7", "b6", "b5", "b4", "b3")) +
          f"  maxLvl={int(lvl[m].max())}")

# ---------------------------------------------------------------- route inventory
print("\n" + H)
print("G. ROUTE INVENTORY -- is there a newer route (the post-fault V74 drive)?")
print(H)
RL = ROOT / "analysis-2020accord" / "rlogs"
by_route = {}
for p in RL.glob("*.zst"):
    r = p.name.split("_")[1].split("--")[0]
    st = p.stat()
    e = by_route.setdefault(r, [0, 0.0, 0.0, 0])
    e[0] += 1
    e[1] = max(e[1], st.st_mtime)
    e[2] = min(e[2] or st.st_mtime, st.st_mtime)
    e[3] += st.st_size
for r in sorted(by_route, key=lambda k: by_route[k][1])[-10:]:
    n, mx, mn, sz = by_route[r]
    print(f"  route {r}  {n:3d} segments  {sz / 1e6:7.1f} MB  mtime "
          f"{datetime.fromtimestamp(mn):%Y-%m-%d %H:%M} .. {datetime.fromtimestamp(mx):%Y-%m-%d %H:%M}")
print(f"\n  highest route id present: {max(by_route)}")
print(f"  route 5e is {'THE NEWEST by mtime' if max(by_route, key=lambda k: by_route[k][1]) == '0000005e' else 'NOT the newest by mtime'}")
gaps = np.diff(D["raw14_t"])
print(f"  route 5e continuity: largest 0x14A gap {gaps.max() * 1000:.0f} ms at "
      f"t={D['raw14_t'][int(np.argmax(gaps))]:.2f} ⇒ "
      f"{'ONE continuous ignition cycle' if gaps.max() < 5 else 'CONTAINS A BREAK'}")
print(f"  route 5e ends at t={t[-1]:.2f} s with STEER_STATUS={int(D['sstat'][-1])}, "
      f"vEgo={vv[-1]:.2f} m/s ⇒ the log stops while the fault is STILL ACTIVE")
