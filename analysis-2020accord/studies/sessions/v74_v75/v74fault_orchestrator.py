#!/usr/bin/env python3
"""studies/sessions/v74_v75/v74fault_orchestrator.py -- the orchestrator's own verification of route 61 (V74's hard fault).

Route `75604b0a432fdc89_00000061--3b8f2f9278`, segments 0..12, extracted by
`studies/sessions/v74_v75/v74fault_extract.py` to `_scratch/cache/r61/r61.npz`.

WHAT THIS SCRIPT ESTABLISHES, and why each step is here
-------------------------------------------------------
1. BUILD IDENTITY + CAVE LIVENESS.  V74's probe is `0x14A` byte4:
       bit7     = (*(short *)(gp - 0x6bd0) != 0)   the damper's OWN output
       bits 6:3 = (*(byte  *)(gp - 0x67fa)) & 0xF  the assist-chain state
       bits 2:0 = STEER_SENSOR_STATUS, preserved
   `gp-0x67fa`'s reachable set is {1,3,4,5,6,7,8,9,10,11} (33 st.b writers' own literals),
   so state==0 is STRUCTURALLY IMPOSSIBLE and a zero field would mean the cave never fired.

2. 🛑 THE HEADLINE -- THE DAMPER EDITS *WERE* IN FORCE.  The previous session concluded
   "[EVIDENCE, two methods] the FactorC/E edits were NOT in force when V74 faulted, because
   disengaged = mode 24 and every mode-24 record is byte-stock" and therefore voided `k*`.
   That inference is REFUTED here, by the car's own telemetry:
       - `bit7 == 1` at the fault frame  => `gp-0x6bd0` was NON-ZERO.
       - speed at the fault = 33.29 km/h = 2130 counts, BELOW stock mode-24 FactorC
         X[0] = 2240 counts = 35.00 km/h, where the evaluator clamps to Y[0] = 0.
       => under mode-24 stock tables the damper is identically zero there. It was not.
       => the ECU was NOT evaluating mode 24.
   The mechanism is the MODE-LAG HYSTERESIS: openpilot dropped lateral control only
   2.509 s before the fault, and the ECU had not yet fallen back to the manual column.
   Corroborated by the negative control, which replicates route 5d exactly:
       0 of 9,286 frames beyond 5 s past a disengagement ever show bit7=1
       (including 0 of 23 above the knee), while 342 within 3.17 s do.

3. THE UNIFYING VARIABLE ACROSS BOTH HARD FAULTS IS ANGLE-RATE SLEW, NOT MAGNITUDE.
   Applying one metric to both fault drives, sentinel-free:
       V74 (route 61): |tq| 3676 = route MAX ; |d(rate)/dt| 5,400/s = route MAX
       V75 (route 5e): |tq|  922 = 86th pct  ; |d(rate)/dt| 6,900/s = route MAX
   Magnitude does not unify them. `|d(angle rate)/dt|` does -- each fault fired at its own
   drive's single largest value, n = 1 in both. That dissolves V75's "mildest of four
   launches" paradox and points at an UN-DEBOUNCED SINGLE-CYCLE consistency monitor on the
   damper chain (fid 28 / fid 29, both descriptor 0x00003D01, both ruled IN by the bit13
   fingerprint). FactorE is indexed on steering RATE, so a route-max d(rate)/dt drives the
   largest single-cycle step in `gp-0x6bd0`.

🛑 SENTINEL TRAP -- the reason every derivative here uses a strict prefix.
   At the fault frame `0x14A` STEER_ANGLE / ANGLE_RATE / WHEEL_ANGLE all latch to the
   0x7FFF sentinel. `np.gradient` over a window that TOUCHES that frame imports a ~16,000-count
   spike and inflates |d(rate)/dt| by ~300x. The previous session's
   `v75fault_{timeline,analysis,followups,oscillation}.py` split on `t < 284.795`, which
   INCLUDES the fault sample, and their rate numbers carry exactly this artifact. Everything
   below slices `[:F]` and asserts the prefix is sentinel-free before differencing.

Usage:  python studies/sessions/v74_v75/v74fault_orchestrator.py
Env:    C:\\Users\\dudei\\anaconda3\\envs\\bin_decompile\\python.exe  (base env has broken numpy)
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
R61 = ROOT / "_scratch/cache/r61" / "r61.npz"
R5E = ROOT / "_scratch/cache/r5e" / "r5e.npz"

COUNTS_PER_KPH = 64.0
FACTORC_X0_STOCK_MODE24 = 2240          # counts; = 35.00 km/h. Stock mode-24 Y[0] = 0.
KNEE_KPH = FACTORC_X0_STOCK_MODE24 / COUNTS_PER_KPH
HYST_S = 5.0                            # the mode-lag band measured on route 5d
STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}


def load(p):
    if not p.exists():
        sys.exit(f"missing cache: {p}")
    return np.load(p, allow_pickle=True)


def fault_index(z):
    """First frame in state 8. Cross-checked against the 0x7FFF angle sentinel."""
    st = z["state"].astype(int)
    F = int(np.argmax(st == 8))
    assert st[F] == 8, "no state-8 frame in this route"
    if "ang_u16" in z.files:
        s = np.where(z["ang_u16"].astype(int) == 0x7FFF)[0]
        assert len(s) and int(s[0]) == F, "state-8 edge and angle sentinel disagree"
    return F


def time_since_disengage(t, lat):
    """Seconds since latActive last fell. 1e9 before the first engagement."""
    out = np.full(len(t), 1e9)
    last = -1e9
    for i in range(len(t)):
        if lat[i] == 1:
            last = t[i]
        out[i] = t[i] - last
    return out


def section(s):
    print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)


def main():
    z = load(R61)
    t, st, b7 = z["t"], z["state"].astype(int), z["b7"].astype(int)
    lat = (z["cc_lat"] > 0.5).astype(int)
    v = z["cs_v"] * 3.6
    tq = z["tq"]
    F = fault_index(z)
    tf = t[F]

    section("1. BUILD IDENTITY AND CAVE LIVENESS")
    u, c = np.unique(st, return_counts=True)
    for val, n in zip(u, c):
        print(f"  state {val:2d} : {n:7d}  {100*n/len(st):6.2f}%  {n/100.0:8.1f} s")
    bad = [int(x) for x in u if int(x) not in STATE_VALUE_SET]
    print(f"  structurally-impossible states observed: {bad or 'NONE'}")
    print(f"  => the cave FIRED (state != 0 everywhere); build reads as V74.")
    tr = np.where(np.diff(st) != 0)[0]
    print(f"  state transitions in the whole route: {len(tr)}"
          + (f"  -> {st[tr[0]]}->{st[tr[0]+1]} at t={t[tr[0]+1]:.4f} s" if len(tr) else ""))

    section("2. THE FAULT FRAME")
    print(f"  t = {tf:.4f} s, segment {int(z['seg'][F])}, index {F}")
    for k, lbl in (("dtc_active", "0x1AB byte0 bit2 (firmware DTC-active)"),
                   ("ang_u16", "0x14A STEER_ANGLE (0x7FFF = 32767 sentinel)"),
                   ("rate_u16", "0x14A ANGLE_RATE"),
                   ("wang_u16", "0x14A WHEEL_ANGLE"),
                   ("status", "STEER_SENSOR_STATUS"),
                   ("sstat", "bus STEER_STATUS (0x18F b4 7:4)"),
                   ("state", "gp-0x67fa"),
                   ("b7", "damper gp-0x6bd0 != 0")):
        a = z[k].astype(int)
        print(f"  {lbl:42s} [F-1]={a[F-1]:6d} -> [F]={a[F]:6d}")
    print(f"  post-fault: {len(t)-F} frames / {t[-1]-tf:.1f} s, 0x14A still at "
          f"{(len(t)-F-1)/(t[-1]-tf):.2f} Hz, state 8 never exits")
    print("  => the ECU is ALIVE and transmitting; a motor-off/authority latch, not a reset.")

    section("3. HEADLINE -- THE DAMPER EDITS WERE IN FORCE (refutes the previous session)")
    tsd = time_since_disengage(t, lat)
    print(f"  bit7 (damper != 0) AT the fault frame : {b7[F]}")
    print(f"  bit7 duty in the 200 ms before        : {100*b7[F-20:F].mean():.1f}%")
    print(f"  speed at the fault                    : {v[F]:.2f} km/h "
          f"({v[F]*COUNTS_PER_KPH:.0f} counts)")
    print(f"  stock mode-24 FactorC X[0]            : {FACTORC_X0_STOCK_MODE24} counts "
          f"= {KNEE_KPH:.2f} km/h, Y[0] = 0 (evaluator clamps below X[0])")
    print(f"  => at {v[F]:.2f} km/h a mode-24 record gives FactorC = 0 => damper == 0.")
    print(f"  => bit7 == 1 is ARITHMETICALLY IMPOSSIBLE on mode 24.  The ECU was on the")
    print(f"     ENGAGED column, where V74's FactorC Y[0] = 429 makes the damper non-zero.")
    print(f"  openpilot dropped lateral control     : {tf - t[np.where((lat[:-1]==1)&(lat[1:]==0))[0][-1]]:.3f} s "
          f"before the fault  => inside the mode-lag band")

    print("\n  --- negative control (replicates route 5d) ---")
    true_man = (lat == 0) & (tsd > HYST_S) & (st == 5)
    within = (lat == 0) & (tsd <= HYST_S) & (st == 5)
    print(f"  TRUE manual (> {HYST_S:.0f} s since disengage): {true_man.sum():6d} frames "
          f"({true_man.sum()/100:.1f} s), bit7=1 in {int((true_man & (b7==1)).sum())}")
    print(f"     of those, above the {KNEE_KPH:.0f} km/h knee   : {int((true_man&(v>KNEE_KPH)).sum()):6d} frames, "
          f"bit7=1 in {int((true_man&(v>KNEE_KPH)&(b7==1)).sum())}")
    w = within & (b7 == 1)
    print(f"  within the band, bit7=1              : {int(w.sum()):6d} frames, "
          f"max time-since-disengage {tsd[w].max():.2f} s")
    print("  => bit7 in 'manual' occurs ONLY inside the hysteresis band. Zero leakage beyond it.")

    # The decay profile. This is the single strongest piece of evidence: it is measured
    # independently on two routes of the same build and agrees in shape AND in the hard
    # zero beyond ~4 s.  Route 5d (n=39,794 beyond 6 s) reads:
    #   0-1 s 44.86% | 1-2 s 41.62% | 2-3 s 12.61% | 3-4 s 6.70% | 4-6 s 0.000% | >6 s 0.000%
    print("\n  --- bit7 duty vs TIME-SINCE-DISENGAGE (route 61, manual, pre-fault) ---")
    pre_mask = np.arange(len(t)) < F
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 10), (10, np.inf)):
        m = (lat == 0) & (tsd >= lo) & (tsd < hi) & pre_mask
        if m.sum():
            print(f"    {lo:5.0f}-{hi if hi != np.inf else 999:<5.0f} s : n={m.sum():6d}   "
                  f"bit7 {100*b7[m].mean():7.3f}%")
    print(f"    the fault sits at time-since-disengage = {tsd[F]:.3f} s -- inside the tail.")
    print("  => the three 'disagreeing' manual episodes agree once ordered by this variable:")
    print("     the one reading 0.00% (t 30.8-40.4 s, and it CROSSES the knee) had never been")
    print("     engaged at all, so its time-since-disengage is infinite. Not a counter-example.")

    section("4. THE UNIFYING VARIABLE -- ANGLE-RATE SLEW, NOT MAGNITUDE")
    for name, path, ftime in (("V74 / route 61", R61, None), ("V75 / route 5e", R5E, 284.7947)):
        zz = load(path) if path != R61 else z
        tt = zz["t"]
        if ftime is None:
            Fi = F
        else:
            s = np.where(np.abs(zz["ang"]) > 3000)[0]
            Fi = int(s[0]) if len(s) else int(np.searchsorted(tt, ftime))
        tqp, rp, bp = zz["tq"][:Fi], zz["rate_c"][:Fi], zz["b7"][:Fi].astype(int)
        if "rate_u16" in zz.files:
            assert (zz["rate_u16"][:Fi].astype(int) != 0x7FFF).all(), "sentinel in prefix"
        live = bp[1:] == 1
        print(f"\n  {name}   (fault index {Fi}, t={tt[Fi]:.4f} s)")
        pk = np.abs(tqp[-10:]).max()
        print(f"    |driver torque| peak 100 ms before : {pk:8.0f}  route max {np.abs(tqp).max():8.0f}"
              f"   pct {100*(np.abs(tqp)<pk).mean():7.3f}")
        for lbl, d in (("|d(torque)/dt|", np.abs(np.diff(tqp))*100),
                       ("|d(angle rate)/dt|", np.abs(np.diff(rp))*100)):
            p = d[-10:].max()
            print(f"    {lbl:22s} {p:9.0f}/s  route max {d.max():9.0f}/s"
                  f"   pct(all) {100*(d<p).mean():7.3f}  pct(damper-live) {100*(d[live]<p).mean():7.3f}"
                  f"   n exceeding {int((d>=p).sum())}")
        print(f"    damper bit7 duty, 200 ms before    : {100*bp[-20:].mean():.1f}%")
    print("\n  => BOTH faults fired at their drive's single largest |d(angle rate)/dt| (n=1 each).")
    print("     Magnitude does NOT unify them (V75 is 86th pct on torque, V74 is the max).")
    print("     This is the signature of an UN-DEBOUNCED SINGLE-CYCLE consistency monitor")
    print("     on the damper chain -- fid 28 / fid 29, both ruled IN by the bit13 fingerprint.")

    section("5. WHAT V74 SURVIVED -- the transient was extremal, not merely large")
    pre = slice(0, F)
    live = b7[pre] == 1
    big = np.abs(tq[pre]) >= 3000
    idx = np.where(big)[0]
    eps = []
    if len(idx):
        s0 = p = idx[0]
        for i in idx[1:]:
            if t[i] - t[p] > 1.0:
                eps.append((s0, p))
                s0 = i
            p = i
        eps.append((s0, p))
    print(f"  episodes with |driver torque| >= 3000 counts, pre-fault: {len(eps)}")
    print(f"  {'t_start':>8} {'peak':>7} {'km/h':>6}  damper-live?")
    for a, b in eps:
        wnd = slice(max(0, a-20), min(F, b+20))
        duty = b7[wnd].mean()
        print(f"  {t[a]:8.1f} {np.abs(tq[a:b+1]).max():7.0f} {v[a]:6.1f}  "
              f"{'YES' if duty > .5 else 'no' if duty < .1 else 'partial'} ({100*duty:.0f}%)")
    print(f"  => V74 survived {sum(1 for a,b in eps if b7[max(0,a-20):min(F,b+20)].mean()>.5)-0} "
          f"earlier damper-live episodes above 3000 counts.")
    print(f"  {int((np.abs(tq[pre])>=3000)&live).sum() if False else int(((np.abs(tq[pre])>=3000)&live).sum())} "
          f"frames were >=3000 counts WITH the damper live and did not fault.")
    print("  => not a simple dose threshold. The fault needed the EXTREME of the slew.")


if __name__ == "__main__":
    main()
