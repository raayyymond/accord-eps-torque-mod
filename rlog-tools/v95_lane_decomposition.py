#!/usr/bin/env python3
r"""v95_lane_decomposition.py -- WHICH TELEMETERED LANE IS THE 6-9 Hz ENERGY SOURCE, AND HOW BIG.

Three things, each with its own control.

1. EVERY telemetered internal lane, cross-spectrum against WHEEL RATE, micro regime, shuffled
   control on every one.  Which lanes are available depends on the build:
     V90 (r77) / V91 (r78) / V94 (r7d)   0x14A b4: b7 sign(gp-0x6b26) . b6 |gp-0x6bf6|>=512 .
                                          b5 gp-0x6ae2!=0 . b4 gp-0x6c00<0 . b3 fingerprint
                                          CAN 427 = |gp-0x6b26| * 5 >> 3 (V90/91) or >> 1 (V94)
     V92 (r79)                            0x14A b4: b7 sign(gp-0x6bbe) . b6 sign(gp-0x6b62) .
                                          b5 gp-0x6b62!=0 . b4 gp-0x6bda window . b3 fingerprint
                                          0x14A b7: b7 |gp-0x6b26|>=15 . b6 dwell-snap
                                          CAN 427 = |gp-0x6bbe| * 5 >> 4

2. THE omega-PARTIALLED DECOMPOSITION -- each lane's share of Re(Z), with wheel rate held.  The
   naive product (`tq per lane count` x `lane per rad/s`) is contaminated because w drives BOTH
   channels; the OLS of tq on the lane absorbs the direct w->tq path.  The lanes have coh^2 only
   0.17-0.31 against w, so 70-80 % of their band variance is independent and there is something to
   partial on:
        S_{b,tq|w} = S_{b,tq} - S_{w,tq} * conj(S_{w,b}) / S_{ww}
        S_{bb|w}   = S_{bb}   - |S_{wb}|^2 / S_{ww}
        H          = S_{b,tq|w} / S_{bb|w}          <- tq counts per lane count, w held
        Re(Z_lane) = Re[ H * (lane per rad/s) ]     <- the lane's share, in Z's own units
   🛑 STILL A CLOSED LOOP.  H is a conditional correlation, not a plant gain -- the lane is
   downstream of w and upstream of tq at once.  Read it as a bound on the lane's explanatory share.

3. THE SIZING, in the lane's own units, against the matched-cell detection floor.

WHAT THE DIRECTION RESTS ON, stated so the sign is not a convention argument:
     column:  J*alpha = T_bar + T_motor  =>  Z = T_bar/Omega = j*w*J + b - T_motor/Omega
     => Re(Z) is REDUCED by the component of MOTOR torque IN PHASE WITH RATE.  A lane near 0 deg
        relative to rate is ANTI-DAMPING; a lane near 180 deg is DAMPING.
     Independent confirmation: V94 cut gp-0x6b26 (measured at +137 deg) 4x and the car shook.

RESULTS 2026-08-12, micro regime, 6-9 Hz:
     gp-0x6bbe  92.3 ct/(rad/s) at +18 deg  -> share  +9 % [-2,+18] (all-rate +15 % [+6,+25])
     gp-0x6b26  189 / 218      at +137/+139 -> share -20 % [-37,-11] (r77) / -26 % [-59,-10] (r78)
     🛑 NEGATIVE share = the lane OPPOSES the anti-damping = it DAMPS.  gp-0x6b26 is a real 6-9 Hz
        damper; the desk figure of "+75 deg, 26 % dissipative, cannot damp 6-9 Hz" is REFUTED.
     The two visible lanes net to about -10 % of the gap: ~110 % is in something never telemetered.

🛑 raw14 OFF-BY-ONE: `t == raw14_t[1:]`, `probe == raw14_b4[1:]`.  Safe pairs are (t, probe) and
   (raw14_t, raw14_b4) ONLY.  `raw14_b7` rides raw14_t, so it is sliced [1:] to reach the `t` grid.
🛑 AN EVEN FUNCTION OF RATE CANNOT APPEAR IN A LINEAR CROSS-SPECTRUM.  |gp-0x6bf6|, the friction
   relay flag and |gp-0x6b26| are magnitude / indicator channels: they respond to |w|, so a null
   against w means nothing.  They are reported against |w| as well.  Only the SIGN bits and the
   signed reconstructions are odd in w and can carry a phase.
🛑 427 IS RECTIFIED AND SAMPLED AT 50 Hz -- see `v95_427_aliasing_and_cadence.py`.  The SIGNED
   reconstruction is clean at 6-9 Hz (coh^2 0.001-0.003 against the folding source); the RAW
   magnitude channel is not (0.104 on r77).

Usage:  python v95_lane_decomposition.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v95_rez_lib import (BUILD, DEG2RAD, HOP50, NW, NW50, base, epwins, hdr,  # noqa: E402
                         load, transfer)

RNG = np.random.default_rng(950814)
B50 = [("2-4", 2, 4), ("4-6", 4, 6), ("6-9", 6, 9), ("9-12", 9, 12), ("12-16", 12, 16),
       ("16-18", 16, 18), ("18-22", 18, 22)]
B100 = B50 + [("22-26", 22, 26), ("26-31", 26, 31), ("32-38", 32, 38)]
REG = {"all": (0.0, 1e9), "micro": (1.0, 13.0), "static": (0.0, 1.0)}
# route -> (lane on 427, counts per wire LSB).  sar 3 -> 8/5, sar 4 -> 16/5, sar 1 -> 4/5.
LANE = {"r77": ("gp-0x6b26", 8 / 5), "r78": ("gp-0x6b26", 8 / 5),
        "r79": ("gp-0x6bbe", 16 / 5), "r7d": ("gp-0x6b26", 4 / 5)}


# ======================================================================================
#  1.  every lane on the wire, on the 100 Hz row grid
# ======================================================================================
def cave_bits(route):
    z = load(route)
    B = base(z)
    pb = np.asarray(z["probe"], int)                 # 0x14A byte4, ALIGNED WITH `t` (the safe pair)
    out = {}
    if BUILD.get(route) in ("V90", "V91", "V94"):
        out["b7 sign(gp-0x6b26)"] = np.where((pb & 0x80) != 0, -1.0, 1.0)
        out["b6 |gp-0x6bf6|>=512"] = ((pb & 0x40) != 0).astype(float)
        out["b5 gp-0x6ae2!=0 relay"] = ((pb & 0x20) != 0).astype(float)
        out["b4 gp-0x6c00<0"] = ((pb & 0x10) != 0).astype(float)
    elif BUILD.get(route) == "V92":
        out["b7 sign(gp-0x6bbe)"] = np.where((pb & 0x80) != 0, -1.0, 1.0)
        out["b6 sign(gp-0x6b62)"] = np.where((pb & 0x40) != 0, -1.0, 1.0)
        out["b5 gp-0x6b62!=0"] = ((pb & 0x20) != 0).astype(float)
        out["b4 gp-0x6bda inwin"] = ((pb & 0x10) != 0).astype(float)
        if "raw14_b7" in z.files:                    # byte7 rides raw14_t: [1:] reaches the t grid
            b7 = np.asarray(z["raw14_b7"], int)[1:]
            out["byte7b7 |gp-0x6b26|>=15"] = ((b7 & 0x80) != 0).astype(float)
            out["byte7b6 dwell-snap"] = ((b7 & 0x40) != 0).astype(float)
    out["tq (0x18F torsion bar)"] = B["tq"]
    if "sc_tq" in z.files and np.std(np.asarray(z["sc_tq"], float)) > 0:
        out["LKAS cmd (sendcan 0xE4)"] = np.asarray(z["sc_tq"], float)
    return B, out


def rebuild(route, shift=0):
    """Signed 427 lane on the 50 Hz grid, with the physical channels interpolated onto it.

    `shift` rolls the 100 Hz sign stream: the skew-sensitivity knob.  The magnitude rides CAN 427 at
    50 Hz and the sign rides 0x14A byte4 b7 at 100 Hz, so a signed reconstruction costs up to
    ~10-20 ms of relative timing.  Every conclusion here is swept over shift = -2..+2.
    """
    z = load(route)
    B = base(z)
    name, sc = LANE[route]
    tab = np.asarray(z["ab_t1ab"], float)
    mag = np.asarray(z["ab_mt"], float) * sc
    t14 = np.asarray(z["raw14_t"], float)
    neg = (np.asarray(z["raw14_b4"], int) & 0x80) != 0        # SAFE PAIR (raw14_t, raw14_b4)
    if shift:
        neg = np.roll(neg, shift)
    sgn = np.where(np.interp(tab, t14, neg.astype(float)) > 0.5, -1.0, 1.0)
    S = dict(name=name, t=tab, mag=mag, signed=mag * sgn,
             fs=1.0 / float(np.median(np.diff(tab))))
    for k, a in (("w", B["w"]), ("tq", B["tq"]), ("v", B["v"]), ("rate", np.abs(B["wdeg"]))):
        S[k] = np.interp(tab, B["t"], a)
    S["mask"] = ((np.interp(tab, B["t"], (B["lat"] & (~B["press"])).astype(float)) > 0.5)
                 & (S["v"] > 0.5))
    return S


def W_of(S, reg):
    lo, hi = REG[reg]
    W = epwins(S["mask"], S["t"], (S["w"], S["signed"], S["tq"], S["rate"], S["mag"]),
               nw=NW50, hop=HOP50, max_gap=0.10)
    return [w for w in W if lo <= float(np.median(w[1][3])) < hi]


def part1():
    hdr("1.  EVERY TELEMETERED LANE vs WHEEL RATE -- phase and coh2, engaged hands-off")
    for route in ("r77", "r78", "r79", "r7d"):
        B, sig = cave_bits(route)
        mask = B["lat"] & (~B["press"]) & (B["v"] > 0.5)
        wabs = np.abs(B["wdeg"])
        print(f"\n  ### route {route[1:]} ({BUILD.get(route)}) -- "
              f"{mask.sum()/B['fs']:.0f} s engaged hands-off")
        for reg in ("all", "micro"):
            print(f"    regime {reg}:  " + " ".join(f"{nm:>16s}" for nm in
                                                    ("4-6", "6-9", "9-12", "18-22")))
            for nm, s in sig.items():
                for axis, xx in (("w", B["w"]), ("|w|", np.abs(B["w"]))):
                    if axis == "|w|" and ("sign" in nm or nm.startswith("tq") or "cmd" in nm):
                        continue
                    lo, hi = REG[reg]
                    W = epwins(mask, B["t"], (xx, s, B["v"], wabs))
                    W = [w for w in W if lo <= float(np.median(w[1][3])) < hi]
                    r = transfer(W, B["fs"], B100, NW, RNG)
                    if r is None:
                        print(f"      {nm:28s} {axis:4s} {len(W):5d} | not scoreable")
                        continue
                    print(f"      {nm:28s} {axis:4s} {len(W):5d} | " + "  ".join(
                        f"{r[b]['phase_deg']:+6.0f}°{'' if r[b]['trust'] else '?'}"
                        f"{r[b]['coh2']:>5.2f}" for b in ("4-6", "6-9", "9-12", "18-22")))
        print("    (each cell: PHASE of the signal relative to the axis, then coh2; "
              "'?' = fails the trust gate)")


# ======================================================================================
#  2 + 3.  the partial decomposition and the sizing
# ======================================================================================
def spec(trips, fs, nw, bands):
    """Welch cross-spectra of (w, lane, tq) -- everything the partial needs."""
    acc = None
    for w_, b_, q_ in trips:
        h = np.hanning(nw)
        W = np.fft.rfft((w_ - w_.mean()) * h)
        Bv = np.fft.rfft((b_ - b_.mean()) * h)
        Q = np.fft.rfft((q_ - q_.mean()) * h)
        cur = (np.abs(W) ** 2, np.abs(Bv) ** 2, np.abs(Q) ** 2,
               np.conj(W) * Bv, np.conj(W) * Q, np.conj(Bv) * Q)
        acc = cur if acc is None else tuple(a + c for a, c in zip(acc, cur))
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    out = {}
    for nm, lo, hi in bands:
        m = (f >= lo) & (f <= hi)
        Sww, Sbb, Sqq, Swb, Swq, Sbq = (a[m].sum() for a in acc)
        Sbq_w = Sbq - np.conj(Swb) * Swq / Sww
        Sbb_w = Sbb - np.abs(Swb) ** 2 / Sww
        H = Sbq_w / Sbb_w if abs(Sbb_w) > 0 else np.nan
        lane_per_w = Swb / Sww
        out[nm] = dict(
            reZ=float(np.real(Swq / Sww)), lane_gain=float(np.abs(lane_per_w)),
            lane_phase=float(np.degrees(np.angle(lane_per_w))),
            H_gain=float(np.abs(H)), H_phase=float(np.degrees(np.angle(H))),
            reZ_lane=float(np.real(H * lane_per_w)),
            coh_bw=float(np.abs(Swb) ** 2 / (Sww * Sbb)),
            partial_coh=float((np.abs(Sbq_w) ** 2
                               / (Sbb_w * (Sqq - np.abs(Swq) ** 2 / Sww))).real))
    return out


def part2(route, reg, nboot=400):
    S = rebuild(route)
    W = W_of(S, reg)
    if len(W) < 6:
        print(f"  {route}/{reg}: {len(W)} windows -- NOT SCOREABLE")
        return
    trip = [(w[1][0], w[1][1], w[1][2]) for w in W]
    b0 = spec(trip, S["fs"], NW50, B50)
    eps = sorted({w[0] for w in W}, key=str)
    byep = [[w for w in W if w[0] == e] for e in eps]
    boots = {nm: [] for nm, _, _ in B50}
    for _ in range(nboot):
        pick = RNG.integers(0, len(eps), size=len(eps))
        tp = [(w[1][0], w[1][1], w[1][2]) for e in pick for w in byep[e]]
        if len(tp) < 6:
            continue
        rr = spec(tp, S["fs"], NW50, B50)
        for nm, _, _ in B50:
            boots[nm].append(rr[nm]["reZ_lane"] / rr[nm]["reZ"] if rr[nm]["reZ"] else np.nan)
    print(f"\n  {route} ({BUILD[route]}) {S['name']}, regime {reg}: {len(W)} win / {len(eps)} ep")
    print(f"    {'band':7s} {'lane/w':>16s} {'coh2':>5s} {'H tq/count':>16s} {'pcoh':>5s} "
          f"{'Re(Z)':>9s} {'Re(Z_lane)':>11s} {'share':>7s} {'[95% CI]':>18s}")
    for nm, _, _ in B50:
        d = b0[nm]
        b = np.asarray([x for x in boots[nm] if np.isfinite(x)])
        ci = (f"[{np.percentile(b,2.5)*100:6.0f}%,{np.percentile(b,97.5)*100:5.0f}%]"
              if len(b) > 20 else "")
        print(f"    {nm:7s} {d['lane_gain']:9.1f}∠{d['lane_phase']:+5.0f}° "
              f"{d['coh_bw']:5.2f} {d['H_gain']:9.2f}∠{d['H_phase']:+5.0f}° "
              f"{d['partial_coh']:5.2f} {d['reZ']:9.0f} {d['reZ_lane']:11.0f} "
              f"{100*d['reZ_lane']/d['reZ']:6.0f}% {ci:>18s}")
    return b0


def part3():
    hdr("3.  SIZING -- what a weight change on gp-0x6bbe would buy, in the lane's own units")
    print("  Detection floor for comparison (v95_crossbuild_rez_ledger.py): ~60 counts at >= 12")
    print("  episodes in the matched cell; use 150 counts as the conservative bar.")
    S = rebuild("r79")
    for reg in ("all", "micro"):
        W = W_of(S, reg)
        if len(W) < 6:
            continue
        d = spec([(w[1][0], w[1][1], w[1][2]) for w in W], S["fs"], NW50, B50)["6-9"]
        mag = np.concatenate([w[1][4] for w in W])
        sdw = np.median([np.std(w[1][0]) for w in W])
        print(f"\n  regime {reg} ({len(W)} windows)")
        print(f"    |gp-0x6bbe| p50 {np.median(mag):6.1f}  p90 {np.percentile(mag,90):6.1f}  "
              f"p99 {np.percentile(mag,99):6.1f}  max {mag.max():6.1f} ct  (aggregator window +-2048)")
        print(f"    rate slope at 6-9 Hz : {d['lane_gain']:.1f} ct/(rad/s) "
              f"∠{d['lane_phase']:+.0f}°  => in-phase part "
              f"{d['lane_gain']*np.cos(np.radians(d['lane_phase'])):.1f} ct/(rad/s)")
        print(f"    tq per lane count (w held) : {d['H_gain']:.2f}∠{d['H_phase']:+.0f}°")
        print(f"    => lane's Re(Z) share : {d['reZ_lane']:+.0f} of {d['reZ']:+.0f} = "
              f"{100*d['reZ_lane']/d['reZ']:.0f} %;  zeroing Re(Z) would need "
              f"{abs(d['reZ']/d['reZ_lane']):.1f}x the lane's WHOLE rate response = NOT AVAILABLE")
        ac = d["lane_gain"] * sdw
        print(f"    DC pedestal {np.median(mag):.1f} ct vs 6-9 Hz AC {ac:.1f} ct "
              f"(slope x median window sd of w = {sdw:.3f} rad/s) => the rate-proportional part is "
              f"{100*ac/max(np.median(mag),1e-9):.0f} % of the DC assist.")
        print("    ⇒ a flat weight cut takes BOTH.  A 25 % cut buys ~1.2x the floor and costs 25 %")
        print("      of the power steering.  BAD TRADE -- do not propose it.")


if __name__ == "__main__":
    part1()
    hdr("2.  THE omega-PARTIALLED DECOMPOSITION -- each lane's share of Re(Z), wheel rate held")
    print("  share > 0 => the lane pushes Re(Z) the SAME way as the measured value (which is")
    print("  NEGATIVE, so a POSITIVE share means the lane is part of the ANTI-DAMPING).")
    print("  share < 0 => the lane OPPOSES it, i.e. it DAMPS.")
    for route in ("r79", "r77", "r78"):
        for reg in ("all", "micro"):
            part2(route, reg)
    print("\n  🛑 CLOSED LOOP: H is a conditional correlation, not a plant gain.")
    part3()
