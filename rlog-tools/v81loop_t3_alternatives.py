#!/usr/bin/env python3
"""T3 / T4 -- the ALTERNATIVES, on fully NATIVE timestamps (no gridding of any channel onto
another message's clock).

  L2    the transport delay openpilot's command actually experiences, measured DIRECTLY from the
        bus echo of its own frame. This is the number the energy-sign test turns on.
  B     the ORDER VETO, run FIRST and from MEASURED wheel rotation rather than an assumed
        circumference. 🛑 The record: this kit "has come close to publishing a wheel order as a
        firmware effect three times."
  C     the engaged-only damper's relay -- read from the V75/V81 probe byte the firmware itself
        transmits, so the damper's operating point is MEASURED, not modelled.
  A     an EPS-internal cycle openpilot echoes.
  T4    which way each hypothesis says the next build should move.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v81loop_lib import (CACHE, FS_NOM, band_env, coherence, lattice,  # noqa: E402
                         locate, prom_spectrum, resamp, welch_cross, wrap)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NAT = CACHE / "v81loop_native_s8.npz"
NF, HOP = 256, 64
EV = (38.0, 52.0)
RATE_FIX = 1.25
BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288, BIT_MAG448, BIT_BACKDRIVE = 0x80, 0x40, 0x20, 0x10, 0x08


def dd(t, *v):
    t = np.asarray(t, float)
    k = np.ones(len(t), bool)
    k[1:] = np.diff(t) > 0
    return (t[k],) + tuple(np.asarray(x, float)[k] for x in v)


def delay_fit(f, Pxy, lo, hi, C=None, cmin=0.3):
    m = (f >= lo) & (f <= hi)
    if C is not None:
        m &= C >= cmin
    if m.sum() < 3:
        return np.nan, np.nan, 0
    ph = np.unwrap(np.angle(Pxy[m]))
    w = np.abs(Pxy[m])
    A = np.vstack([f[m], np.ones(m.sum())]).T
    W = np.diag(w / w.sum())
    co = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ ph, rcond=None)[0]
    pred = A @ co
    r2 = 1 - np.sum(w * (ph - pred) ** 2) / max(
        np.sum(w * (ph - np.average(ph, weights=w)) ** 2), 1e-30)
    return -co[0] / (2 * np.pi), float(r2), int(m.sum())


def main():
    N = np.load(NAT)
    tau = lattice(EV[0], EV[1], FS_NOM)
    a = dd(N["a_t"], N["a_ang"], N["a_rc"], N["a_pr"])
    b = dd(N["b_t"], N["b_tq"], N["b_rt"])
    sc = dd(N["sc_t"], N["sc_v"])
    ec = dd(N["ec_t"], N["ec_v"])
    ang, rc, pr = (resamp(tau, a[0], a[i]) for i in (1, 2, 3))
    bar, rf = resamp(tau, b[0], b[1]), resamp(tau, b[0], b[2]) * RATE_FIX
    cmd, echo = resamp(tau, sc[0], sc[1]), resamp(tau, ec[0], ec[1])
    v = resamp(tau, *dd(N["cs_t"], N["cs_v"]))

    print("=" * 100)
    print("L2  TRANSPORT DELAY, measured on the SAME PAYLOAD out and back (native timestamps)")
    print("=" * 100)
    # (i) frame-matching: pair each sendcan value with the echo of the identical payload
    scv, ecv = sc[1], ec[1]
    lags = []
    j = 0
    for i in range(len(scv)):
        while j < len(ecv) and ec[0][j] < sc[0][i] - 0.002:
            j += 1
        for k in range(j, min(j + 6, len(ecv))):
            if ecv[k] == scv[i]:
                lags.append(ec[0][k] - sc[0][i])
                break
    lags = np.array(lags)
    print(f"  payload-matched pairs: {len(lags)} of {len(scv)} sendcan frames")
    print(f"    L2 = sendcan timestamp -> bus-echo timestamp:")
    print(f"      p05 {1e3 * np.percentile(lags, 5):6.2f}  p25 {1e3 * np.percentile(lags, 25):6.2f}"
          f"  MEDIAN {1e3 * np.median(lags):6.2f} ms  p75 {1e3 * np.percentile(lags, 75):6.2f}"
          f"  p95 {1e3 * np.percentile(lags, 95):6.2f}  mean {1e3 * lags.mean():6.2f}")
    # (ii) independent cross-spectral confirmation on the resampled pair
    f, Pxx, Pyy, Pxy, _ = welch_cross(cmd, echo, FS_NOM, NF, HOP)
    C = coherence(Pxx, Pyy, Pxy)
    t2, r2, nb = delay_fit(f, Pxy, 0.5, 40.0, C, 0.5)
    print(f"    cross-spectral pure-delay fit 0.5-40 Hz (coh>0.5, {nb} bins): "
          f"{1e3 * t2:.2f} ms, R2 {r2:.3f}")
    L2 = float(np.median(lags))
    print(f"  ==> L2 = {1e3 * L2:.2f} ms  =  {360 * 27.53 * L2:.0f} deg at 27.53 Hz")
    print(f"      🛑 This is publish -> echo-received. The command is on the WIRE somewhere inside")
    print(f"      it, so the true actuation delay is BOUNDED BY [0, {1e3 * L2:.1f}] ms and the")
    print(f"      energy test is swept over that whole range below.")

    print()
    print("=" * 100)
    print("B  ORDER VETO -- run FIRST, from MEASURED wheel rotation")
    print("=" * 100)
    # 🛑 `wheel_speeds_kph` returns km/h and the extractor multiplies by KMH = 1/3.6, so this
    # array is in METRES PER SECOND despite the name it inherited. Read as km/h it puts wheel
    # order 2 at 7.0 Hz and the veto looks harmlessly far away; in the correct units order 2 is
    # 25.2 Hz against an observed 27.5 Hz and the veto is very much live.
    wms = np.asarray(N["w_kph"], float)
    wt = np.asarray(N["w_t"], float)
    wm = (wt >= EV[0]) & (wt <= EV[1])
    vk = wms[wm].mean()
    print(f"  mean wheel speed over the event {vk:.2f} m/s = {vk * 3.6:.2f} km/h  "
          f"[cross-check vEgo {v.mean():.2f} m/s]")
    for circ, lab in ((2.073, "V57 tyre estimate"), (2.088, "V56 tyre estimate")):
        r1 = vk / circ
        print(f"    circumference {circ:.3f} m ({lab}): order 1 = {r1:6.2f} Hz   "
              f"order 2 = {2 * r1:6.2f} Hz   order 3 = {3 * r1:6.2f} Hz")
    print("  observed line 27.53 Hz  ==> ORDER 2 IS ONLY 9% AWAY. The veto must be decided on")
    print("  df/dv, not on the band centre.")
    # window-by-window f0 vs speed INSIDE the event: does the line track speed?
    rows = []
    for i in range(0, len(tau) - NF + 1, 32):
        sl = slice(i, i + NF)
        x = bar[sl] - bar[sl].mean()
        P = np.abs(np.fft.rfft(x * np.hanning(NF))) ** 2
        ff = np.fft.rfftfreq(NF, 1 / FS_NOM)
        f0, p0 = locate(ff, P, 22.0, 34.0)
        rows.append((float(np.mean(v[sl])), f0, p0,
                     band_env(np.asarray(bar[sl], float), FS_NOM, 24, 32)))
    rows = [r for r in rows if np.isfinite(r[1]) and r[2] > 3]
    V = np.array([r[0] for r in rows])
    F = np.array([r[1] for r in rows])
    W = np.array([r[2] for r in rows])
    print(f"\n  {len(rows)} windows with a prominent 22-34 Hz line inside the event")
    print(f"    speed span {V.min():.2f}-{V.max():.2f} m/s   f0 span {F.min():.2f}-{F.max():.2f} Hz")
    if len(rows) > 5 and np.ptp(V) > 0.5:
        # bootstrap the slope over BLOCKS (windows overlap 8x, so blocks of 8 -> ~2.6 s units)
        rng = np.random.default_rng(7)
        blk = np.arange(len(rows)) // 8
        ub = np.unique(blk)
        sl_ = []
        for _ in range(3000):
            pick = rng.choice(ub, len(ub))
            idx = np.concatenate([np.flatnonzero(blk == u) for u in pick])
            if np.ptp(V[idx]) < 0.3:
                continue
            sl_.append(np.polyfit(V[idx], F[idx], 1)[0])
        sl_ = np.array(sl_)
        s0 = np.polyfit(V, F, 1)[0]
        lo, hi = np.percentile(sl_, [2.5, 97.5])
        print(f"    df/dv = {s0:+.4f} Hz per m/s   95% CI [{lo:+.4f}, {hi:+.4f}]  "
              f"(block bootstrap, {len(ub)} blocks)")
        for nm, pred in (("order 1", 1 / 2.073), ("order 2", 2 / 2.073), ("order 3", 3 / 2.073)):
            inside = lo <= pred <= hi
            print(f"      {nm}: predicted df/dv = {pred:+.4f}   "
                  f"{'CONSISTENT -- veto FIRES' if inside else 'EXCLUDED by the CI'}")
        print(f"      order 0 (fixed frequency): predicted df/dv = 0.0000   "
              f"{'CONSISTENT' if lo <= 0 <= hi else 'EXCLUDED by the CI'}")
    print("\n  cross-check -- the line's frequency at the two ENDS of the speed range:")
    o = np.argsort(V)
    lo_i, hi_i = o[:max(len(o) // 4, 2)], o[-max(len(o) // 4, 2):]
    print(f"    slowest quartile v={V[lo_i].mean():.2f} m/s -> f0 = {F[lo_i].mean():.3f} Hz")
    print(f"    fastest quartile v={V[hi_i].mean():.2f} m/s -> f0 = {F[hi_i].mean():.3f} Hz")
    print(f"    order 2 would predict a shift of {(V[hi_i].mean() - V[lo_i].mean()) * 2 / 2.073:+.3f} Hz;"
          f" observed {F[hi_i].mean() - F[lo_i].mean():+.3f} Hz")

    print()
    print("=" * 100)
    print("C  THE ENGAGED-ONLY DAMPER -- read from the firmware's OWN probe byte (V75/V81 cave)")
    print("=" * 100)
    p = pr.astype(int)
    thermo = (((p & BIT_DAMP_NZ) != 0).astype(float) + ((p & BIT_MAG128) != 0)
              + ((p & BIT_MAG288) != 0) + ((p & BIT_MAG448) != 0))
    bd = ((p & BIT_BACKDRIVE) != 0).astype(float)
    ev = np.ones(len(tau), bool)
    print(f"  INSIDE the event ({EV[0]}-{EV[1]} s):")
    print(f"    damper thermometer levels 0/1/2/3/4 = "
          + " ".join(f"{100 * np.mean(thermo[ev] == L):.1f}%" for L in range(5)))
    print(f"    damper NON-ZERO {100 * np.mean(thermo[ev] >= 1):.1f}% of frames   "
          f"back-drive bit {100 * np.mean(bd[ev]):.1f}%")
    # the rest of segment 8, engaged, as the matched-speed contrast
    a_all = dd(N["a_t"], N["a_pr"])
    lat = resamp(np.asarray(a_all[0]), *dd(N["lat_t"], N["lat_v"])) > 0.5
    vv = resamp(np.asarray(a_all[0]), *dd(N["cs_t"], N["cs_v"]))
    pall = np.asarray(a_all[1]).astype(int)
    th_all = ((((pall & BIT_DAMP_NZ) != 0).astype(float) + ((pall & BIT_MAG128) != 0)
               + ((pall & BIT_MAG288) != 0) + ((pall & BIT_MAG448) != 0)))
    inev = (a_all[0] >= EV[0]) & (a_all[0] <= EV[1])
    out = lat & ~inev & (vv > 24)
    print(f"  OUTSIDE the event, same segment, engaged, v>24 m/s ({out.sum() / 100:.1f} s):")
    print(f"    damper thermometer levels 0/1/2/3/4 = "
          + " ".join(f"{100 * np.mean(th_all[out] == L):.1f}%" for L in range(5)))
    print(f"    damper NON-ZERO {100 * np.mean(th_all[out] >= 1):.1f}%")
    print("  If C is right, the damper's operating point inside the event should be visibly")
    print("  HIGHER / more often relayed than in matched-speed engaged driving that is quiet.")
    # does the damper bit MODULATE at the line frequency? a relay limit cycle must.
    f3, P1, P2, P3, _ = welch_cross(thermo - thermo.mean(), bar - bar.mean(), FS_NOM, NF, HOP)
    C3 = coherence(P1, P2, P3)
    j = int(np.argmin(np.abs(f3 - 27.53)))
    Pth = np.zeros(NF // 2 + 1)
    kk = 0
    for i in range(0, len(thermo) - NF + 1, HOP):
        Pth += np.abs(np.fft.rfft((thermo[i:i + NF] - thermo[i:i + NF].mean())
                                  * np.hanning(NF))) ** 2
        kk += 1
    Pth /= max(kk, 1)
    f0t, pt = locate(f3, Pth, 12.0, 45.0)
    print(f"  DAMPER STATE as a SIGNAL: its own most prominent 12-45 Hz line is at {f0t:.2f} Hz "
          f"(prom {pt:.1f})")
    print(f"    coherence(damper level, bar) at 27.53 Hz = {C3[j]:.3f}")
    print("    A relay limit cycle REQUIRES the relay to switch at the oscillation frequency, so a")
    print("    damper level that does not modulate at 27.53 Hz is direct evidence against C.")

    print()
    print("=" * 100)
    print("T1-CRUX (redone on native timestamps)  DOES OPENPILOT PUMP OR DAMP AT 27.53 Hz?")
    print("=" * 100)
    print("  Work rate on the column ~ Re<cmd(t-L), rate(t)>.  L is swept over [0, L2] because the")
    print("  command is on the wire somewhere inside that interval.  Only a sign that holds across")
    print("  the whole interval is a finding.")
    fq, Pc, Pr, Pcr, _ = welch_cross(cmd, rf, FS_NOM, NF, HOP)
    Ccr = coherence(Pc, Pr, Pcr)
    Ls = np.linspace(0, L2, 7)
    for lab, lo, hi in (("1-4 Hz (openpilot IS driving)", 1.0, 4.0),
                        ("6-10 Hz", 6.0, 10.0), ("24-32 Hz (INSTABILITY)", 24.0, 32.0)):
        m = (fq >= lo) & (fq <= hi)
        vals = []
        for L in Ls:
            cp = (Pcr[m] * np.conj(np.exp(-2j * np.pi * fq[m] * L))).sum()
            vals.append(cp.real / np.abs(Pcr[m]).sum())
        print(f"  {lab:>30}  " + " ".join(f"{x:+.2f}" for x in vals)
              + f"   coh {np.nanmean(Ccr[m]):.2f}")
    print(f"  {'L (ms) =':>30}  " + " ".join(f"{1e3 * L:+.2f}" for L in Ls))
    print("  NEGATIVE = the command opposes the column's motion => REMOVES energy => damping.")
    print("  POSITIVE = adds energy => pumping. The 1-4 Hz row is the calibration: that is the")
    print("  sign of openpilot genuinely steering, and it is L-insensitive by construction.")

    print()
    print("=" * 100)
    print("A  IS THE LINE PRESENT WITHOUT OPENPILOT'S COMMAND MOVING?  (A vs H1)")
    print("=" * 100)
    # split event windows by how much 24-32 Hz content the COMMAND carries; if the bar's line
    # survives where the command's is small, openpilot is not necessary to sustain it
    rec = []
    for i in range(0, len(tau) - NF + 1, 32):
        sl = slice(i, i + NF)
        rec.append((band_env(np.asarray(cmd[sl], float), FS_NOM, 24, 32),
                    band_env(np.asarray(bar[sl], float), FS_NOM, 24, 32),
                    float(np.mean(v[sl]))))
    rec = np.array(rec)
    q = np.percentile(rec[:, 0], [25, 50, 75])
    print(f"  {'cmd 24-32 quartile':>24} {'n':>4} {'cmd env':>9} {'bar env':>9} {'bar/cmd':>9}")
    edges = [0] + list(q) + [1e18]
    for i in range(4):
        m = (rec[:, 0] >= edges[i]) & (rec[:, 0] < edges[i + 1])
        if not m.any():
            continue
        print(f"  {'Q' + str(i + 1):>24} {int(m.sum()):>4} {rec[m, 0].mean():>9.1f} "
              f"{rec[m, 1].mean():>9.1f} {rec[m, 1].mean() / max(rec[m, 0].mean(), 1e-9):>9.2f}")
    print("  A rising bar/cmd ratio as the command's own line SHRINKS means the bar's oscillation")
    print("  does not need the command to be large -- i.e. openpilot is not the energy source.")

    (CACHE / "v81loop_t3.json").write_text(json.dumps(
        dict(L2_ms=float(1e3 * L2), f0_windows=[[float(x) for x in r] for r in rows],
             wheel_kph=float(vk)), indent=0))
    print(f"\n  wrote {CACHE / 'v81loop_t3.json'}")


if __name__ == "__main__":
    main()
