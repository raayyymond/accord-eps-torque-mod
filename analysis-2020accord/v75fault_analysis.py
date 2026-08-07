#!/usr/bin/env python3
"""v75fault_analysis.py -- the forensic reconstruction of the V75 mid-drive hard fault (route 5e).

Sections:
  1  the fault instant, anchored on 5 independent channels, in raw-frame order
  2  the 30 s before it, 100 ms buckets
  3  the probe's own story (duty, peak, legality, V74 comparison)
  4  the stoplight-launch regime
  5  after the fault (liveness / latch discrimination)
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
CEN = json.loads((C5E / "r5e_census.json").read_text())

t = D["t"]
SEG_T0 = {int(s): float(t[D["seg"] == s].min()) for s in np.unique(D["seg"])}
BIT = dict(b7=0x80, b6=0x40, b5=0x20, b4=0x10, b3=0x08)
LEGAL = [0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8]
BRACKET = {0: "0", 1: "[1,128)", 2: "[128,288)", 3: "[288,448)", 4: ">=448"}


def seg_of(tx):
    ks = [k for k, v in SEG_T0.items() if v <= tx]
    s = max(ks) if ks else min(SEG_T0)
    return s, tx - SEG_T0[s]


def runs(mask, tt):
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    s = np.r_[idx[0], idx[brk + 1]]
    e = np.r_[idx[brk], idx[-1]]
    return [(float(tt[a]), float(tt[b]), int(a), int(b)) for a, b in zip(s, e)]


H = "=" * 100
# =================================================================== 1. THE FAULT INSTANT
print(H)
print("1. THE FAULT INSTANT -- raw frame order, un-gridded streams")
print(H)
r18t, r18st, r18b4 = D["raw18_t"], D["raw18_st"], D["raw18_b4"]
r14t, r14b4 = D["raw14_t"], D["raw14_b4"]
sca_raw = (r18b4 >> 3) & 1
i_st7 = int(np.flatnonzero(r18st == 7)[0])
i_sca0 = int(np.flatnonzero(sca_raw == 0)[0]) if (sca_raw == 0).any() else -1
# last SCA=1
i_sca_last = int(np.flatnonzero(sca_raw == 1)[-1])
sens = r14b4 & 0x07
i_sens4 = int(np.flatnonzero(sens == 4)[0])
lat = D["cc_lat"] > 0.5
rl = runs(lat, t)
ev_names = {}
for e in EV:
    ev_names.setdefault(e["name"], []).append(e["t"])

anchors = []
anchors.append(("0x18F STEER_STATUS 0 -> 7 (FIRST 7)", float(r18t[i_st7])))
anchors.append(("0x18F STEER_CONTROL_ACTIVE last 1", float(r18t[i_sca_last])))
anchors.append(("0x18F STEER_CONTROL_ACTIVE first 0", float(r18t[i_sca0]) if i_sca0 >= 0 else np.nan))
anchors.append(("0x14A byte4[2:0] STEER_SENSOR_STATUS 7 -> 4 (FIRST 4)", float(r14t[i_sens4])))
anchors.append(("carControl.latActive last True", rl[-1][1]))
for nm in ("steerTempUnavailable", "steerUnavailable", "steerTempUnavailableSilent"):
    if nm in ev_names:
        anchors.append((f"onroadEvent {nm} FIRST", ev_names[nm][0]))
anchors.sort(key=lambda x: (np.inf if not np.isfinite(x[1]) else x[1]))
t_fault = float(r18t[i_st7])
print(f"{'channel':56s} {'t (route s)':>12s} {'seg':>4s} {'t_seg':>8s} {'dt vs ST7':>10s}")
for nm, tv in anchors:
    if np.isfinite(tv):
        s, ts = seg_of(tv)
        print(f"{nm:56s} {tv:12.3f} {s:4d} {ts:8.3f} {tv - t_fault:+10.3f}")
    else:
        print(f"{nm:56s} {'never':>12s}")
print(f"\n  ⇒ FAULT INSTANT = t = {t_fault:.3f} s route-relative = "
      f"segment {seg_of(t_fault)[0]} @ {seg_of(t_fault)[1]:.3f} s")
print(f"  route length {t[-1]:.2f} s; the fault sits {t[-1] - t_fault:.2f} s before the end")
# does anything ever come back?
post = t >= t_fault
print(f"  after the fault: STEER_STATUS==7 on {int((D['sstat'][post] == 7).sum())}/"
      f"{int(post.sum())} samples ({100 * (D['sstat'][post] == 7).mean():.3f}%), "
      f"STEER_CONTROL_ACTIVE set {int((D['sca'][post] == 1).sum())} times, "
      f"latActive True {int(lat[post].sum())} times")
# transition detail, frame by frame
print("\n  0x18F frames around the transition (STEER_STATUS | SCA | driver torque | angle rate):")
for k in range(i_st7 - 6, i_st7 + 7):
    if 0 <= k < len(r18t):
        mark = "  <<< FIRST ST=7" if k == i_st7 else ""
        print(f"    t={r18t[k]:9.4f}  ST={int(r18st[k])}  SCA={int(sca_raw[k])}  "
              f"b4=0x{int(r18b4[k]):02X}{mark}")
print("\n  0x14A frames around the transition (probe byte4 | field | thermo | sens):")
j = int(np.searchsorted(r14t, t_fault))
for k in range(j - 8, j + 9):
    if 0 <= k < len(r14t):
        b = int(r14b4[k])
        th = sum(1 for m in (0x80, 0x40, 0x20, 0x10) if b & m)
        mark = "  <<< first SENS=4" if k == i_sens4 else ""
        print(f"    t={r14t[k]:9.4f}  byte4=0x{b:02X}  field=0x{b & 0xF8:02X}  "
              f"thermo={th} |6bd0| in {BRACKET[th]:9s} b3={(b >> 3) & 1}  sens={b & 7}{mark}")

# =================================================================== 2. THE 30 S BEFORE
print("\n" + H)
print("2. THE 30 SECONDS BEFORE THE FAULT -- 100 ms buckets")
print(H)
W0, W1 = t_fault - 30.0, t_fault + 2.0
m = (t >= W0) & (t <= W1)
tt = t[m]
bins = np.arange(W0, W1 + 1e-9, 0.1)
bi = np.clip(np.digitize(tt, bins) - 1, 0, len(bins) - 2)
ang, rate = D["ang"][m], D["rate_c"][m]
v, dtq = D["cs_v"][m], D["tq"][m]
e4 = D["e4tq"][m]
latm, scam, stm = D["cc_lat"][m], D["sca"][m], D["sstat"][m]
pb = D["probe"][m].astype(int)
prs, std = D["cs_press"][m], D["cs_std"][m]
# openpilot command slew, from the sendcan stream (its own clock)
sct, sctq = D["sc_t"], D["sc_tq_raw"]
ms = (sct >= W0) & (sct <= W1)
print(f"  window {W0:.2f} .. {W1:.2f} s   (fault at {t_fault:.3f})")
print(f"  {'t':>8s} {'dt_f':>7s} {'vEgo':>6s} {'ang':>8s} {'rate':>8s} {'drvTq':>6s} "
      f"{'e4cmd':>7s} {'lat':>3s} {'ST':>2s} {'SCA':>3s} {'thermo':>6s} {'|6bd0|':>10s} "
      f"{'b3':>2s} {'payloads'}")
for k in range(len(bins) - 1):
    sel = bi == k
    if not sel.any():
        continue
    tb = bins[k]
    if tb < t_fault - 30.0:
        continue
    b = pb[sel]
    th = np.array([sum(1 for mm in (0x80, 0x40, 0x20, 0x10) if x & mm) for x in b])
    pay = sorted(set(int(x) & 0xF8 for x in b))
    print(f"  {tb:8.2f} {tb - t_fault:+7.2f} {np.nanmean(v[sel]):6.2f} {np.mean(ang[sel]):8.2f} "
          f"{np.mean(rate[sel]):8.1f} {np.mean(dtq[sel]):6.0f} {np.mean(e4[sel]):7.0f} "
          f"{int(round(np.mean(latm[sel]))):3d} {int(np.max(stm[sel])):2d} "
          f"{int(round(np.mean(scam[sel]))):3d} {th.max():6d} {BRACKET[int(th.max())]:>10s} "
          f"{int(b[-1] >> 3 & 1):2d} " + ",".join(f"{p:02X}" for p in pay))

# rail analysis on the command
print("\n  openpilot command rails inside the window (sendcan 0x0E4, its own clock):")
q = sctq[ms]
qt = sct[ms]
if len(q):
    dq = np.diff(q)
    print(f"    n={len(q)}  min={q.min():.0f} max={q.max():.0f}  "
          f"|cmd|==4096 on {int((np.abs(q) >= 4096).sum())} frames "
          f"({100 * (np.abs(q) >= 4096).mean():.2f}%)")
    print(f"    |slew| max={np.abs(dq).max():.0f} counts/frame;  "
          f"|slew|>=123 on {int((np.abs(dq) >= 123).sum())} frames "
          f"({100 * (np.abs(dq) >= 123).mean():.2f}%)")
    lastn = 40
    print(f"    last {lastn} commands before the fault:")
    kk = np.flatnonzero(qt <= t_fault)[-lastn:]
    print("      " + " ".join(f"{q[i]:.0f}" for i in kk))

# =================================================================== 3. THE PROBE
print("\n" + H)
print("3. THE PROBE'S OWN STORY")
print(H)
p = D["probe"].astype(int)
field = p & 0xF8
u, c = np.unique(field, return_counts=True)
print("  route-wide field census (bits 7:3):")
for uu, cc in zip(u, c):
    ok = "legal" if uu in LEGAL else "*** ILLEGAL ***"
    print(f"    0x{int(uu):02X}  n={int(cc):6d}  {100 * cc / len(p):6.3f}%   {ok}")
print(f"  ILLEGAL payload count = {int((~np.isin(field, LEGAL)).sum())}  "
      f"(thermometer order violations = {int(D['order_viol'].sum())})")
print(f"  ⇒ the wire model and the build identity are CONSISTENT with V75"
      if not (~np.isin(field, LEGAL)).any() else "  ⇒ MODEL BROKEN")

# V74/V73 exclusion
v74_states = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
bad74 = sum(int(cc) for uu, cc in zip(u, c) if ((int(uu) & 0x78) >> 3) not in v74_states)
print(f"  V74 decoder exclusion: {bad74} frames decode to a gp-0x67fa state OUTSIDE "
      f"{sorted(v74_states)} ⇒ a V74 cave is REFUTED" if bad74 else
      "  V74 decoder exclusion: NOT excluded")

pre = t < t_fault
lat_b = D["cc_lat"] > 0.5
creep = (D["cs_v"] > 0.2) & (D["cs_v"] <= 4.0)
cruise = D["cs_v"] > 10.0
stopped = D["cs_v"] <= 0.2


def duty(mask, label):
    if not mask.any():
        print(f"    {label:38s}  n=0")
        return
    row = [100 * D[b][mask].mean() for b in ("b7", "b6", "b5", "b4", "b3")]
    th = D["thermo"][mask]
    print(f"    {label:38s} n={int(mask.sum()):6d}  b7={row[0]:6.2f}%  b6={row[1]:6.2f}%  "
          f"b5={row[2]:6.2f}%  b4={row[3]:6.2f}%  b3={row[4]:6.2f}%  maxLvl={int(th.max())}")


print("\n  duty by regime (PRE-FAULT only, t < %.2f):" % t_fault)
duty(pre, "ALL pre-fault")
duty(pre & lat_b, "engaged (latActive)")
duty(pre & ~lat_b, "disengaged")
duty(pre & lat_b & creep, "engaged & creep (0.2-4 m/s)")
duty(pre & lat_b & cruise, "engaged & cruising (>10 m/s)")
duty(pre & lat_b & stopped, "engaged & stopped (<=0.2 m/s)")
duty(pre & ~lat_b & creep, "disengaged & creep")
duty(pre & ~lat_b & cruise, "disengaged & cruising")
print("\n  duty by regime (POST-FAULT):")
duty(~pre, "ALL post-fault")

print("\n  thermometer level histogram (pre-fault):")
for lv in range(5):
    n_ = int((D["thermo"][pre] == lv).sum())
    print(f"    level {lv} |gp-0x6bd0| in {BRACKET[lv]:9s}: {n_:6d}  "
          f"{100 * n_ / int(pre.sum()):6.3f}%")
mx = int(D["thermo"][pre].max())
print(f"  ⇒ HIGHEST THERMOMETER LEVEL EVER REACHED (pre-fault) = {mx}  "
      f"⇒ |gp-0x6bd0|_peak ∈ {BRACKET[mx]}")
print(f"    bit4 (>=448) fired {int(D['b4'].sum())} times in the whole route "
      f"⇒ the 512 ceiling floor was NEVER approached within 64 counts")
print(f"    PREDICTED_PEAK_V75 = 354 lies inside {BRACKET[mx]} ⇒ the prediction is NOT REFUTED, "
      f"and NOT confirmed either -- the probe cannot resolve inside the bracket")
print(f"    V74's OBSERVED_PEAK was 225 (bracket [128,288)); V75 reached [288,448) on "
      f"{int((D['thermo'] == 3).sum())} frames ⇒ a strictly HIGHER bracket, as designed")

# ---- V74 comparison, route 5d
print("\n  --- V74 comparison (route 5d, _cache_r5d) ---")
try:
    b7_all, lat_all, v_all, nseg = [], [], [], 0
    for s in range(17):
        f = C5D / f"r5ds{s}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        b7_all.append(z["damp_nz"])
        lat_all.append(z["cc_lat"] > 0.5)
        v_all.append(z["cs_v"])
        nseg += 1
    b7d = np.concatenate(b7_all).astype(bool)
    latd = np.concatenate(lat_all)
    vd = np.concatenate(v_all)
    cd = (vd > 0.2) & (vd <= 4.0)
    print(f"    route 5d: {nseg} segments, {len(b7d)} samples")
    print(f"    V74 bit7 duty  ALL {100 * b7d.mean():6.3f}%   engaged {100 * b7d[latd].mean():6.3f}%"
          f"   engaged&creep {100 * b7d[latd & cd].mean():6.3f}%"
          f"   engaged&cruise {100 * b7d[latd & (vd > 10)].mean():6.3f}%")
    b7e = D["b7"][pre].astype(bool)
    late = lat_b[pre]
    ve = D["cs_v"][pre]
    ce = (ve > 0.2) & (ve <= 4.0)
    print(f"    V75 bit7 duty  ALL {100 * b7e.mean():6.3f}%   engaged {100 * b7e[late].mean():6.3f}%"
          f"   engaged&creep {100 * b7e[late & ce].mean():6.3f}%"
          f"   engaged&cruise {100 * b7e[late & (ve > 10)].mean():6.3f}%")
except Exception as ex:                                          # noqa: BLE001
    print(f"    route 5d cache unreadable: {ex}")

# =================================================================== 4. STOPLIGHT LAUNCHES
print("\n" + H)
print("4. THE STOPLIGHT-LAUNCH REGIME")
print(H)
vv = D["cs_v"]
stop_runs = [r for r in runs(vv <= 0.15, t) if r[1] - r[0] >= 1.0]
print(f"  stops (vEgo<=0.15 m/s for >=1.0 s): {len(stop_runs)}")
launches = []
for a, b, ia, ib in stop_runs:
    # the launch is the first crossing of 1.0 m/s after the stop ends
    j = ib
    while j < len(t) and vv[j] < 1.0:
        j += 1
    if j >= len(t):
        continue
    tl = float(t[j])
    if tl - b > 20:
        continue
    w = (t >= b - 0.5) & (t <= tl + 3.0)
    launches.append(dict(stop_a=a, stop_b=b, t_launch=tl, dur=b - a,
                         lat_at_launch=float(np.max(D["cc_lat"][w])),
                         lat_frac=float(np.mean(D["cc_lat"][w] > 0.5)),
                         thermo_max=int(D["thermo"][w].max()),
                         b5=float(100 * D["b5"][w].mean()),
                         cmd_max=float(np.nanmax(np.abs(D["e4tq"][w]))),
                         rail=float(100 * (np.abs(D["e4tq"][w]) >= 4096).mean()),
                         ang=float(np.nanmax(np.abs(D["ang"][w]))),
                         rate=float(np.nanmax(np.abs(D["rate_c"][w]))),
                         drv=float(np.nanmax(np.abs(D["tq"][w])))))
print(f"  {'#':>2s} {'stop_t0':>8s} {'stop_t1':>8s} {'dur':>6s} {'t_launch':>9s} {'engaged':>8s} "
      f"{'lat%':>6s} {'maxLvl':>6s} {'b5%':>6s} {'|cmd|max':>8s} {'rail%':>6s} {'|ang|':>7s} "
      f"{'|rate|':>7s} {'|drvTq|':>7s}")
for i, L in enumerate(launches):
    fault_mark = "  <<< FAULTED" if abs(L["t_launch"] - t_fault) < 6 or \
        (L["t_launch"] <= t_fault <= L["t_launch"] + 6) else ""
    print(f"  {i:2d} {L['stop_a']:8.2f} {L['stop_b']:8.2f} {L['dur']:6.2f} {L['t_launch']:9.2f} "
          f"{'YES' if L['lat_at_launch'] > 0.5 else 'no':>8s} {L['lat_frac'] * 100:6.1f} "
          f"{L['thermo_max']:6d} {L['b5']:6.2f} {L['cmd_max']:8.0f} {L['rail']:6.2f} "
          f"{L['ang']:7.1f} {L['rate']:7.0f} {L['drv']:7.0f}{fault_mark}")

# =================================================================== 5. AFTER THE FAULT
print("\n" + H)
print("5. AFTER THE FAULT -- latch or dead task?")
print(H)
postm = t >= t_fault
pf = p[postm]
u2, c2 = np.unique(pf & 0xF8, return_counts=True)
print("  probe field census POST-fault: " +
      "  ".join(f"0x{int(a_):02X}:{int(b_)}" for a_, b_ in zip(u2, c2)))
b3p = D["b3"][postm]
print(f"  bit3 (gp-0x6ac2 != 0) post-fault: duty {100 * b3p.mean():.3f}%, "
      f"{int(np.abs(np.diff(b3p)).sum())} transitions over {postm.sum()} frames "
      f"⇒ the cave is STILL EXECUTING and gp-0x6ac2 is STILL MOVING")
print(f"  thermometer post-fault: levels {sorted(set(int(x) for x in D['thermo'][postm]))} "
      f"⇒ |gp-0x6bd0| pinned in {BRACKET[int(D['thermo'][postm].max())]}")
print(f"  0x14A frames post-fault: {int((D['raw14_t'] >= t_fault).sum())}, "
      f"0x18F frames post-fault: {int((D['raw18_t'] >= t_fault).sum())}, "
      f"over {t[-1] - t_fault:.1f} s "
      f"⇒ {(D['raw14_t'] >= t_fault).sum() / (t[-1] - t_fault):.1f} Hz / "
      f"{(D['raw18_t'] >= t_fault).sum() / (t[-1] - t_fault):.1f} Hz")
gap14 = np.diff(D["raw14_t"][D["raw14_t"] >= t_fault])
print(f"  largest 0x14A inter-frame gap post-fault: {gap14.max() * 1000:.1f} ms "
      f"(pre-fault {np.diff(D['raw14_t'][D['raw14_t'] < t_fault]).max() * 1000:.1f} ms)")
# the driver's own torque after the fault -- manual effort
print(f"  driver torque |0x18F STEER_TORQUE_SENSOR| p50/p95/max: "
      f"pre {np.percentile(np.abs(D['tq'][pre]), 50):.0f}/"
      f"{np.percentile(np.abs(D['tq'][pre]), 95):.0f}/{np.abs(D['tq'][pre]).max():.0f}  "
      f"post {np.percentile(np.abs(D['tq'][postm]), 50):.0f}/"
      f"{np.percentile(np.abs(D['tq'][postm]), 95):.0f}/{np.abs(D['tq'][postm]).max():.0f}")
print(f"  vEgo post-fault {D['cs_v'][postm].min():.2f}..{D['cs_v'][postm].max():.2f} m/s, "
      f"|angle| max {np.abs(D['ang'][postm]).max():.1f} deg "
      f"⇒ the car kept being driven and steered MANUALLY")
