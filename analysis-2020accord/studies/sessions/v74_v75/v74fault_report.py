#!/usr/bin/env python3
"""studies/sessions/v74_v75/v74fault_report.py -- answer the five V74/route-61 fault questions off `_scratch/cache/r61/r61.npz`.

1 build identity (V74 state alphabet vs V75 thermometer) · 2 is there a fault, and WHEN
3 engagement in the 10 s before it · 4 the `gp-0x67fa` state histogram · 5 damper-bit duty.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
CACHE = Path(os.environ.get("R61_CACHE", ROOT / "_scratch/cache/r61"))
D = dict(np.load(CACHE / "r61.npz", allow_pickle=False))
t = D["t"]
seg = D["seg"]
STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
V75_ALPHABET = [0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8]
SENTINEL = 0x7FFF


def seg_at(tt):
    i = int(np.searchsorted(t, tt))
    return int(seg[min(i, len(seg) - 1)])


def first_where(mask, tt):
    ix = np.flatnonzero(mask)
    return (float(tt[ix[0]]), int(ix[0])) if len(ix) else (None, None)


print("=" * 100)
print(f"ROUTE 61 -- {len(t)} samples, t {t[0]:.2f}..{t[-1]:.2f} s "
      f"({(t[-1] - t[0]) / 60:.1f} min), segs {int(seg.min())}..{int(seg.max())}")
sb = D["seg_bounds"]
print("  seg bounds: " + " ".join(f"{int(s)}:[{a:.1f},{b:.1f}]" for s, a, b in sb))

# ---- 1. BUILD IDENTITY ---------------------------------------------------------------------------
print("\n" + "=" * 100)
print("1. BUILD IDENTITY -- raw 0x14A byte4 histogram")
b4 = D["raw14_b4"].astype(int)
u, c = np.unique(b4, return_counts=True)
for v, n in zip(u, c):
    f = v & 0xF8
    print(f"   0x{v:02X}  n={n:8d} ({100.0 * n / len(b4):6.3f}%)   field=0x{f:02X}  "
          f"b7={(v >> 7) & 1}  state={(v >> 3) & 0xF:2d}  status={v & 7}"
          f"{'   <- state OUTSIDE V74 value set' if ((v >> 3) & 0xF) not in STATE_VALUE_SET else ''}"
          f"{'   [also in V75 alphabet]' if f in V75_ALPHABET else ''}")
n75 = int(sum(n for v, n in zip(u, c) if (v & 0xF8) in V75_ALPHABET))
states = sorted({int((v >> 3) & 0xF) for v in u})
print(f"   distinct states observed: {states}")
print(f"   frames whose field is inside V75's 10-payload thermometer alphabet: "
      f"{n75}/{len(b4)} = {100.0 * n75 / len(b4):.4f}%")
v74_only = [s for s in states if s not in (0, 1, 8, 9, 12, 13, 14, 15)]
print(f"   states V75 CANNOT produce that are present here: {v74_only}")
print(f"   VERDICT: {'V74' if v74_only else 'AMBIGUOUS / possibly V75'}  "
      f"(illegal payloads {int(D['illegal'].sum())}, off-state-set {int(D['state_impossible'].sum())})")

# ---- 2. IS THERE A FAULT? ------------------------------------------------------------------------
print("\n" + "=" * 100)
print("2. FAULT SIGNATURES")
r18t, r18st, r18b4 = D["raw18_t"], D["raw18_st"].astype(int), D["raw18_b4"].astype(int)
u18, c18 = np.unique(r18st, return_counts=True)
print("   a) bus STEER_STATUS (0x18F src1 byte4 7:4): " +
      " ".join(f"{v}:{n}" for v, n in zip(u18, c18)))
mode18 = int(u18[np.argmax(c18)])
tt, ii = first_where(r18st != mode18, r18t)
if tt is None:
    print(f"      NEVER leaves its modal value {mode18}")
else:
    print(f"      FIRST departure from modal {mode18}: t={tt:.4f} s  seg={seg_at(tt)}  "
          f"value={r18st[ii]}")
    # every transition
    ch = np.flatnonzero(np.diff(r18st) != 0)
    print(f"      {len(ch)} transitions; first 20: " +
          " ".join(f"[t={r18t[k + 1]:.3f} {r18st[k]}->{r18st[k + 1]}]" for k in ch[:20]))

print("   b) 0x14A sentinel 0x7FFF:")
tfault_cands = []
for nm, key in (("STEER_ANGLE", "ang_u16"), ("ANGLE_RATE", "rate_u16"), ("WHEEL_ANGLE", "wang_u16")):
    m = D[key].astype(int) == SENTINEL
    tt, ii = first_where(m, t)
    print(f"      {nm:12s} n={int(m.sum()):7d}  " +
          (f"FIRST t={tt:.4f} s seg={seg_at(tt)}" if tt is not None else "never"))
    if tt is not None:
        tfault_cands.append(("sentinel_" + nm, tt))

print("   c) 0x1AB byte0 bit2 (firmware DTC-active):")
b0 = D["raw1ab_b0"].astype(int)
r1t = D["raw1ab_t"]
dtc = (b0 >> 2) & 1
u1, c1 = np.unique(b0, return_counts=True)
print(f"      byte0 values: " + " ".join(f"0x{v:02X}:{n}" for v, n in zip(u1, c1)))
print(f"      bit2 duty {100.0 * dtc.mean():.4f}%  ({int(dtc.sum())}/{len(dtc)})")
tt, ii = first_where(dtc == 1, r1t)
if tt is not None:
    print(f"      FIRST set: t={tt:.4f} s  seg={seg_at(tt)}")
    tfault_cands.append(("dtc_1ab_bit2", tt))
    ch = np.flatnonzero(np.diff(dtc) != 0)
    print(f"      {len(ch)} transitions; first 20: " +
          " ".join(f"[t={r1t[k + 1]:.3f} {dtc[k]}->{dtc[k + 1]}]" for k in ch[:20]))
else:
    print("      NEVER sets")

print("   d) STEER_SENSOR_STATUS (0x14A byte4 bits 2:0, preserved through the probe):")
ss = D["status"].astype(int)
us, cs_ = np.unique(ss, return_counts=True)
print("      " + " ".join(f"{v}:{n}" for v, n in zip(us, cs_)))
modess = int(us[np.argmax(cs_)])
tt, ii = first_where(ss != modess, t)
if tt is not None:
    print(f"      FIRST departure from modal {modess}: t={tt:.4f} s seg={seg_at(tt)} -> {ss[ii]}")
    tfault_cands.append(("steer_sensor_status", tt))
    ch = np.flatnonzero(np.diff(ss) != 0)
    print(f"      {len(ch)} transitions; first 20: " +
          " ".join(f"[t={t[k + 1]:.3f} {ss[k]}->{ss[k + 1]}]" for k in ch[:20]))
else:
    print(f"      NEVER leaves {modess}")

print("\n   EARLIEST fault signature: " +
      (f"{min(tfault_cands, key=lambda x: x[1])}" if tfault_cands else "NONE FOUND"))
T_FAULT = min((x[1] for x in tfault_cands), default=None)

# openpilot events, and any UDS
ev = json.loads((CACHE / "r61_events.json").read_text())
names = {}
for e in ev:
    names[e["name"]] = names.get(e["name"], 0) + 1
print(f"\n   onroadEvents: {len(ev)} total, {len(names)} distinct")
for k, v in sorted(names.items(), key=lambda x: -x[1]):
    print(f"      {v:5d}  {k}")
if T_FAULT is not None:
    near = [e for e in ev if T_FAULT - 20 <= e["t"] <= T_FAULT + 20]
    print(f"   events within +-20 s of the fault ({len(near)}):")
    seen = set()
    for e in near:
        k = (e["name"], round(e["t"], 0))
        if k in seen:
            continue
        seen.add(k)
        print(f"      t={e['t']:9.3f}  {e['name']}")

# ---- 3. ENGAGEMENT AT THE FAULT ------------------------------------------------------------------
print("\n" + "=" * 100)
print("3. ENGAGEMENT")
lat, eng = D["cc_lat"], D["cs_eng"]
e4 = D["e4hist"]                       # t, torque, bit7, byte2
print(f"   whole route: latActive duty {100 * (lat > 0.5).mean():.3f}%  "
      f"cruiseState.enabled {100 * (eng > 0.5).mean():.3f}%  "
      f"0x0E4 b2b7 duty {100 * (e4[:, 2] > 0.5).mean():.3f}%" if len(e4) else "")
if T_FAULT is not None:
    for w in (10.0, 2.0):
        m = (t >= T_FAULT - w) & (t < T_FAULT)
        me = (e4[:, 0] >= T_FAULT - w) & (e4[:, 0] < T_FAULT) if len(e4) else np.zeros(0, bool)
        print(f"   [{w:.0f} s before fault] n={int(m.sum()):5d}  "
              f"latActive {100 * (lat[m] > 0.5).mean():7.3f}%  "
              f"cruiseEnabled {100 * (eng[m] > 0.5).mean():7.3f}%  "
              f"0x0E4 b2b7 {100 * (e4[me, 2] > 0.5).mean() if me.sum() else float('nan'):7.3f}% "
              f"(n={int(me.sum())})  vEgo {D['cs_v'][m].min():.2f}..{D['cs_v'][m].max():.2f} m/s  "
              f"|ang| max {np.abs(D['ang'][m]).max():.1f} deg  "
              f"steeringPressed {100 * (D['cs_press'][m] > 0.5).mean():.1f}%")
    m2 = (t >= T_FAULT) & (t < T_FAULT + 10)
    print(f"   [10 s AFTER fault] n={int(m2.sum()):5d}  "
          f"latActive {100 * (lat[m2] > 0.5).mean():7.3f}%  "
          f"cruiseEnabled {100 * (eng[m2] > 0.5).mean():7.3f}%  "
          f"vEgo {D['cs_v'][m2].min():.2f}..{D['cs_v'][m2].max():.2f} m/s")
    # last engagement transition before the fault
    le = (lat > 0.5).astype(int)
    ch = np.flatnonzero(np.diff(le) != 0)
    pre = ch[t[ch + 1] < T_FAULT]
    if len(pre):
        k = pre[-1]
        print(f"   last latActive transition before the fault: t={t[k + 1]:.3f} s "
              f"({le[k]}->{le[k + 1]}), {T_FAULT - t[k + 1]:.2f} s earlier")

# ---- 4. STATE HISTOGRAM --------------------------------------------------------------------------
print("\n" + "=" * 100)
print("4. STATE (`gp-0x67fa` & 0xF) HISTOGRAM")
st = D["state"].astype(int)


def hist(mask, label):
    if not mask.sum():
        print(f"   {label:28s} (empty)")
        return
    u_, c_ = np.unique(st[mask], return_counts=True)
    print(f"   {label:28s} n={int(mask.sum()):7d}  " +
          "  ".join(f"{v}:{n} ({100.0 * n / mask.sum():.3f}%)" for v, n in zip(u_, c_)))


hist(np.ones(len(st), bool), "WHOLE ROUTE")
hist(lat > 0.5, "ENGAGED (latActive)")
hist(lat <= 0.5, "MANUAL")
if T_FAULT is not None:
    hist((t >= T_FAULT - 5) & (t < T_FAULT), "5 s BEFORE fault")
    hist((t >= T_FAULT) & (t < T_FAULT + 5), "5 s AFTER fault")
    ch = np.flatnonzero(np.diff(st) != 0)
    near = ch[(t[ch + 1] > T_FAULT - 5) & (t[ch + 1] < T_FAULT + 5)]
    print(f"   state transitions within +-5 s of the fault ({len(near)}): " +
          " ".join(f"[t={t[k + 1]:.4f} {st[k]}->{st[k + 1]}]" for k in near[:40]))
ch = np.flatnonzero(np.diff(st) != 0)
print(f"   total state transitions over the route: {len(ch)}")
pairs = {}
for k in ch:
    pairs[(st[k], st[k + 1])] = pairs.get((st[k], st[k + 1]), 0) + 1
print("   transition pairs: " + "  ".join(f"{a}->{b}:{n}"
                                          for (a, b), n in sorted(pairs.items(), key=lambda x: -x[1])))

# ---- 5. DAMPER LIVENESS --------------------------------------------------------------------------
print("\n" + "=" * 100)
print("5. DAMPER-NONZERO BIT (b7 = gp-0x6bd0 != 0)")
b7 = D["b7"]
print(f"   overall  {100 * b7.mean():7.4f}%  ({int(b7.sum())}/{len(b7)})")
for lab, m in (("engaged (latActive)", lat > 0.5), ("manual", lat <= 0.5),
               ("engaged & moving >1 m/s", (lat > 0.5) & (D["cs_v"] > 1.0)),
               ("manual & moving >1 m/s", (lat <= 0.5) & (D["cs_v"] > 1.0))):
    print(f"   {lab:26s} {100 * b7[m].mean() if m.sum() else float('nan'):7.4f}%  (n={int(m.sum())})")
if T_FAULT is not None:
    for lab, m in (("5 s before fault", (t >= T_FAULT - 5) & (t < T_FAULT)),
                   ("5 s after fault", (t >= T_FAULT) & (t < T_FAULT + 5)),
                   ("after fault, whole tail", t >= T_FAULT)):
        print(f"   {lab:26s} {100 * b7[m].mean() if m.sum() else float('nan'):7.4f}%  "
              f"(n={int(m.sum())})")

# ---- extra: UDS ----------------------------------------------------------------------------------
uds = json.loads((CACHE / "r61_uds.json").read_text())
print(f"\n   UDS/diag frames captured: {len(uds)}")
addrs = {}
for u_ in uds:
    addrs[(u_["src"], u_["addr"])] = addrs.get((u_["src"], u_["addr"]), 0) + 1
for k, v in sorted(addrs.items(), key=lambda x: -x[1])[:12]:
    print(f"      src{k[0]} 0x{k[1]}: {v}")
print(f"\n   npz: {CACHE / 'r61.npz'}")
print("   columns: " + ", ".join(sorted(D.keys())))
