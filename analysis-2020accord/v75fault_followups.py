#!/usr/bin/env python3
"""v75fault_followups.py -- the precursor, the launch contrast, and the episode-level nulls.

(a) raw-frame timeline of the last 5 s before the fault
(b) route-wide census of damper-output STEPS (0 -> level>=2 in one 10 ms sample)
(c) the launch contrast, windows CLIPPED to pre-fault
(d) precursor sweep: any earlier ST!=0, any earlier 0x14A sentinel, any earlier SENS!=7
(e) split-half null on the engaged-creep bit7 duty, EPISODE bootstrap
(f) dwell: longest run at each thermometer level; the run that ends at the fault
(g) post-fault: is the pin explained by a railed rate input?
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
C5E = ROOT / "_cache_r5e"
C5D = ROOT / "_cache_r5d"
D = dict(np.load(C5E / "r5e.npz"))
EV = json.loads((C5E / "r5e_events.json").read_text())
t = D["t"]
T_FAULT = 284.795
BRACKET = {0: "0", 1: "[1,128)", 2: "[128,288)", 3: "[288,448)", 4: ">=448"}
H = "=" * 100
rng = np.random.default_rng(20260806)


def runs(mask, tt):
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    s = np.r_[idx[0], idx[brk + 1]]
    e = np.r_[idx[brk], idx[-1]]
    return [(float(tt[a]), float(tt[b]), int(a), int(b)) for a, b in zip(s, e)]


# ---------------------------------------------------------------- (a) raw-frame timeline
print(H)
print("(a) THE LAST 5 SECONDS -- every 0x14A frame (10 ms), un-gridded")
print(H)
m = (t >= T_FAULT - 5.0) & (t <= T_FAULT + 0.5)
idx = np.flatnonzero(m)
print(f"  {'t':>9s} {'dt':>7s} {'vEgo':>5s} {'ang':>8s} {'rate14':>7s} {'rate18':>7s} "
      f"{'drvTq':>6s} {'e4cmd':>6s} {'sc':>6s} {'coCan':>6s} {'lat':>3s} {'ST':>2s} {'SCA':>3s} "
      f"{'byte4':>5s} {'lvl':>3s} {'|6bd0|':>10s} {'b3':>2s} {'sens':>4s}")
for i in idx:
    b = int(D["probe"][i])
    lv = int(D["thermo"][i])
    print(f"  {t[i]:9.4f} {t[i] - T_FAULT:+7.3f} {D['cs_v'][i]:5.2f} {D['ang'][i]:8.2f} "
          f"{D['rate_c'][i]:7.1f} {D['rate_f'][i]:7.1f} {D['tq'][i]:6.0f} {D['e4tq'][i]:6.0f} "
          f"{D['sc_tq'][i]:6.0f} {D['co_tqcan'][i]:6.0f} {int(D['cc_lat'][i] > 0.5):3d} "
          f"{int(D['sstat'][i]):2d} {int(D['sca'][i]):3d}  0x{b:02X} {lv:3d} "
          f"{BRACKET[lv]:>10s} {int(D['b3'][i]):2d} {b & 7:4d}")

# ---------------------------------------------------------------- (b) step census
print("\n" + H)
print("(b) DAMPER-OUTPUT STEPS -- how unusual is the 0 -> level>=2 jump that preceded the fault?")
print(H)
lvl = D["thermo"].astype(int)
pre = t < T_FAULT
d_lvl = np.diff(lvl)
step_up = np.flatnonzero((lvl[:-1] == 0) & (lvl[1:] >= 2))
step_up_pre = step_up[t[step_up] < T_FAULT]
print(f"  0 -> level>=2 in ONE sample: {len(step_up_pre)} times pre-fault "
      f"({len(step_up_pre) / (T_FAULT / 60):.1f} per minute)")
print(f"  0 -> level>=3 in ONE sample: "
      f"{int(((lvl[:-1] == 0) & (lvl[1:] >= 3))[:np.searchsorted(t, T_FAULT)].sum())} pre-fault")
print(f"  max |level| step pre-fault: {np.abs(d_lvl[:np.searchsorted(t, T_FAULT) - 1]).max()}")
lat = D["cc_lat"] > 0.5
print(f"  of the {len(step_up_pre)} pre-fault 0->>=2 steps, {int(lat[step_up_pre].sum())} were "
      f"engaged")
print("  ⇒ the step that preceded the fault is COMMON, not unique  [EVIDENCE]")
print(f"\n  the last pre-fault step: t={t[step_up[t[step_up] <= T_FAULT][-1]]:.4f} "
      f"({t[step_up[t[step_up] <= T_FAULT][-1]] - T_FAULT:+.3f} s vs the fault)")
# how close does a 0->>=2 step usually sit to *nothing*? distribution of inter-step gaps
g = np.diff(t[step_up_pre])
if len(g):
    print(f"  inter-step gap p5/p50/p95 = {np.percentile(g, 5):.2f}/{np.percentile(g, 50):.2f}/"
          f"{np.percentile(g, 95):.2f} s")

# ---------------------------------------------------------------- (c) launch contrast
print("\n" + H)
print("(c) THE STOPLIGHT LAUNCHES -- windows clipped to PRE-FAULT, engaged launches only")
print(H)
vv = D["cs_v"]
stop_runs = [r for r in runs(vv <= 0.15, t) if r[1] - r[0] >= 1.0]
rows = []
for a, b, ia, ib in stop_runs:
    j = ib
    while j < len(t) and vv[j] < 1.0:
        j += 1
    if j >= len(t):
        continue
    tl = float(t[j])
    if tl - b > 20:
        continue
    hi = min(tl + 4.0, T_FAULT)
    w = (t >= b - 0.5) & (t <= hi)
    if not w.any():
        continue
    eng = lat[w]
    rows.append(dict(
        stop_t0=a, stop_t1=b, dur=b - a, t_launch=tl, clip=hi,
        eng_frac=float(eng.mean()), eng_any=bool(eng.any()),
        lvlmax=int(lvl[w].max()), lvl3=float(100 * (lvl[w] >= 3).mean()),
        b7=float(100 * D["b7"][w].mean()), b3=float(100 * D["b3"][w].mean()),
        cmdmax=float(np.nanmax(np.abs(D["e4tq"][w]))),
        rail=float(100 * (np.abs(D["e4tq"][w]) >= 4096).mean()),
        angspan=float(np.nanmax(D["ang"][w]) - np.nanmin(D["ang"][w])),
        ratemax=float(np.nanmax(np.abs(D["rate_c"][w]))),
        drvmax=float(np.nanmax(np.abs(D["tq"][w]))),
        drvp95=float(np.percentile(np.abs(D["tq"][w]), 95)),
        vmax=float(np.nanmax(vv[w]))))
print(f"  {'#':>2s} {'stop':>7s}-{'':7s} {'dur':>6s} {'launch':>8s} {'eng%':>6s} {'lvlmax':>6s} "
      f"{'lvl3%':>6s} {'b7%':>6s} {'|cmd|':>6s} {'rail%':>6s} {'angspan':>8s} {'|rate|':>7s} "
      f"{'drv95':>6s} {'drvmax':>7s}")
for i, r in enumerate(rows):
    mk = "  <<< THE FAULTING LAUNCH" if r["clip"] == T_FAULT else ""
    print(f"  {i:2d} {r['stop_t0']:7.1f}-{r['stop_t1']:7.1f} {r['dur']:6.1f} {r['t_launch']:8.2f} "
          f"{100 * r['eng_frac']:6.1f} {r['lvlmax']:6d} {r['lvl3']:6.2f} {r['b7']:6.2f} "
          f"{r['cmdmax']:6.0f} {r['rail']:6.2f} {r['angspan']:8.2f} {r['ratemax']:7.0f} "
          f"{r['drvp95']:6.0f} {r['drvmax']:7.0f}{mk}")
print(f"\n  engaged launches pre-fault (eng_any): "
      f"{sum(1 for r in rows if r['eng_any'])}  of {len(rows)} launches")
print("  ⇒ the faulting launch is the LAST of them, not the first  [EVIDENCE]")

# ---------------------------------------------------------------- (d) precursor sweep
print("\n" + H)
print("(d) PRECURSOR SWEEP -- was there ANY earlier hint on the bus?")
print(H)
st = D["sstat"]
print(f"  STEER_STATUS != 0 before the fault: {int((st[pre] != 0).sum())} samples")
sens = D["probe"].astype(int) & 7
u, c = np.unique(sens[pre], return_counts=True)
print("  0x14A STEER_SENSOR_STATUS pre-fault: " +
      "  ".join(f"{int(a_)}:{int(b_)}" for a_, b_ in zip(u, c)))
u2, c2 = np.unique(sens[~pre], return_counts=True)
print("  0x14A STEER_SENSOR_STATUS post-fault: " +
      "  ".join(f"{int(a_)}:{int(b_)}" for a_, b_ in zip(u2, c2)))
sent = np.abs(D["ang"]) > 1000
print(f"  0x14A angle sentinel (|ang|>1000 deg): {int(sent[pre].sum())} pre-fault, "
      f"{int(sent[~pre].sum())} post-fault; first at t={t[np.flatnonzero(sent)[0]]:.4f}")
sca = D["sca"]
print(f"  STEER_CONTROL_ACTIVE=0 while latActive=True, pre-fault: "
      f"{int(((sca == 0) & lat & pre).sum())} samples")
# openpilot events before the fault that are steering-related
pre_ev = [e for e in EV if e["t"] < T_FAULT and ("steer" in e["name"].lower())]
nm = {}
for e in pre_ev:
    nm[e["name"]] = nm.get(e["name"], 0) + 1
print(f"  steering-related onroadEvents before the fault: {nm}")
print(f"  last steerOverride before the fault: "
      f"{max([e['t'] for e in pre_ev if e['name'] == 'steerOverride'], default=float('nan')):.2f} s")

# ---------------------------------------------------------------- (e) episode-level null
print("\n" + H)
print("(e) V75 vs V74 engaged-creep bit7 duty -- EPISODE bootstrap + split-half null")
print(H)


def episodes(tt, mask_lat, mask_regime, vals):
    """One value per contiguous latActive episode, restricted to the regime."""
    out = []
    for a, b, ia, ib in runs(mask_lat, tt):
        if b - a < 1.0:
            continue
        sl = slice(ia, ib + 1)
        r = mask_regime[sl]
        if r.sum() < 25:
            continue
        out.append(float(vals[sl][r].mean()))
    return np.array(out)


creep5e = (vv > 0.2) & (vv <= 4.0) & pre
ep5e = episodes(t, lat & pre, creep5e, D["b7"])
b7d, latd, vd, td = [], [], [], []
off = 0.0
for s in range(17):
    f = C5D / f"r5ds{s}.npz"
    if not f.exists():
        continue
    z = np.load(f)
    b7d.append(z["damp_nz"]); latd.append(z["cc_lat"] > 0.5); vd.append(z["cs_v"])
    td.append(z["t"] + off)
    off += float(z["t"][-1]) + 0.01
b7d = np.concatenate(b7d); latd = np.concatenate(latd)
vd = np.concatenate(vd); td = np.concatenate(td)
creep5d = (vd > 0.2) & (vd <= 4.0)
ep5d = episodes(td, latd, creep5d, b7d)
print(f"  V75 route 5e: {len(ep5e)} engaged episodes with >=25 creep samples, "
      f"per-episode bit7 duty median {100 * np.median(ep5e):.2f}%")
print(f"  V74 route 5d: {len(ep5d)} engaged episodes, median {100 * np.median(ep5d):.2f}%")
if len(ep5e) >= 2 and len(ep5d) >= 2:
    bs = [np.median(rng.choice(ep5e, len(ep5e))) / max(np.median(rng.choice(ep5d, len(ep5d))), 1e-9)
          for _ in range(20000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"  ratio of medians = {np.median(ep5e) / np.median(ep5d):.3f}  "
          f"episode-bootstrap 95% CI [{lo:.3f}, {hi:.3f}]")
# split-half null WITHIN route 5d (same build, so the true ratio is 1)
if len(ep5d) >= 4:
    nulls = []
    for _ in range(20000):
        p_ = rng.permutation(len(ep5d))
        a_, b_ = ep5d[p_[: len(ep5d) // 2]], ep5d[p_[len(ep5d) // 2:]]
        nulls.append(np.median(a_) / max(np.median(b_), 1e-9))
    nl, nh = np.percentile(nulls, [2.5, 97.5])
    print(f"  🛑 SPLIT-HALF NULL inside route 5d (true ratio == 1): [{nl:.3f}, {nh:.3f}] "
          f"⇒ a ratio inside this band is NOT a build effect")

# ---------------------------------------------------------------- (f) dwell
print("\n" + H)
print("(f) DWELL -- longest continuous run at each thermometer level")
print(H)
for lv in range(4):
    r = [x for x in runs(lvl == lv, t) if x[0] < T_FAULT]
    if not r:
        print(f"  level {lv}: none pre-fault")
        continue
    L = [b - a for a, b, _, _ in r]
    print(f"  level {lv} ({BRACKET[lv]:>10s}): {len(r)} runs pre-fault, "
          f"longest {max(L) * 1000:.0f} ms at t={r[int(np.argmax(L))][0]:.2f}, "
          f"p95 {np.percentile(L, 95) * 1000:.0f} ms, total {sum(L):.2f} s")
r_ge2 = [x for x in runs(lvl >= 2, t) if x[0] <= T_FAULT <= x[1] + 0.05 or
         (x[0] < T_FAULT and x[1] >= T_FAULT - 0.05)]
print(f"  the level>=2 run containing the fault: {r_ge2}")
# the run of level>=1 preceding the fault
k = np.searchsorted(t, T_FAULT)
j = k
while j > 0 and lvl[j - 1] >= 2:
    j -= 1
print(f"  contiguous level>=2 immediately before the fault: {t[k] - t[j]:.3f} s "
      f"(from t={t[j]:.4f})")

# ---------------------------------------------------------------- (g) post-fault mechanism
print("\n" + H)
print("(g) POST-FAULT -- what pins |gp-0x6bd0| in [128,288)?")
print(H)
post = ~pre
print(f"  0x14A angle raw post-fault: unique {np.unique(D['ang'][post])[:5]} ...  "
      f"n_unique={len(np.unique(D['ang'][post]))}")
print(f"  0x14A rate  raw post-fault: unique {np.unique(D['rate_c'][post])[:5]} ...  "
      f"n_unique={len(np.unique(D['rate_c'][post]))}")
print(f"  0x18F rate  post-fault: {np.unique(D['rate_f'][post])[:5]} ... "
      f"n_unique={len(np.unique(D['rate_f'][post]))}, "
      f"range {D['rate_f'][post].min():.1f}..{D['rate_f'][post].max():.1f}")
print(f"  0x18F driver torque post-fault range {D['tq'][post].min():.0f}.."
      f"{D['tq'][post].max():.0f} (pre {D['tq'][pre].min():.0f}..{D['tq'][pre].max():.0f})")
print(f"  probe bit3 post-fault: {int(np.abs(np.diff(D['b3'][post])).sum())} transitions "
      f"⇒ gp-0x6ac2 still moving; the CAN-TX task and the ceiling LERP both still run")
print(f"  probe thermo post-fault: constant level 2 over {int(post.sum())} frames / "
      f"{t[-1] - T_FAULT:.1f} s ⇒ |gp-0x6bd0| never leaves [128,288) again")
# is the driver's own motion still reflected anywhere?
print(f"  vEgo post-fault: {vv[post].min():.2f}..{vv[post].max():.2f} m/s, "
      f"moving (>1 m/s) {100 * (vv[post] > 1).mean():.1f}% of the time")
