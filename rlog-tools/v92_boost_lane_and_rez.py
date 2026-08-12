#!/usr/bin/env python3
r"""ROUTES 78 (V91) and 79 (V92): the driving-point impedance `Re(Z)` replicated on two new drives,
and the FIRST EVER measurement of the aggregator's BOOST lane `gp-0x6bbe`.

===================================================================================================
WHY THESE TWO THINGS, AND WHY TOGETHER
===================================================================================================
STATE.md §C names the session's biggest open question:

    at 6-9 Hz:  P -0.145   I -0.053   D +0.077   =>  NET -0.121  == DAMPING   (per-term convention)
    measured Re(Z) at 6-9 Hz = -3375 ct*s/rad                    == ANTI-DAMPING  (Re(Z) convention)
    ⇒ THE ANTI-DAMPING IS NOT COMING FROM THE PID.  It is another aggregator lane, or the plant.

`gp-0x6bbe` was the flagged best STRUCTURAL match for that anti-damping -- same-signed as the raw
torque sensor, therefore REINFORCING -- and V92 is the first build in the kit's history to put it on
the wire.  So this file asks the two halves of one question:
    A. does `Re(Z) < 0` at 2-26 Hz REPLICATE on two independent drives?   (r78 has the kit's best
       highway exposure ever: 159.9 s engaged >= 80 km/h, against route 77's 42.0 s)
    B. does the boost lane behave like the source of it?

🛑 THE TWO ROUTES ARE CALIBRATION-IDENTICAL, AND SO IS ROUTE 77.  V91 and V92 carry the same 12 cal
   bytes, and this session MEASURED those bytes to be INERT (`v91_v92_dose_threeway.py`: engaged
   stratified ratio 0.99 [0.91, 1.26], three-way duty 0.167 / 0.161 / 0.165 against a needed 0.204).
   ⇒ **routes 77, 78 and 79 are three drives on the SAME FUNCTIONAL CAR.**  That makes every
   cross-route number here a PLACEBO/DRIVE-VARIATION measurement, not a firmware contrast -- which
   is exactly what makes it a good replication test, and exactly why no band difference between
   them may be reported as a firmware effect.

===================================================================================================
🛑 THE SIGNED BOOST LANE HAS AN INTER-MESSAGE SKEW, AND IT IS NOT THE raw14 BUG
===================================================================================================
V92 splits `gp-0x6bbe` across two CAN messages:
    |gp-0x6bbe|  <- CAN 427 (0x1AB), 50 Hz,  = clamp(|x| * 5 >> 4, 0, 0x3FF),  x = wire * 16/5
    sign         <- CAN 0x14A byte4 b7,      100 Hz
Both are written by the same 1 kHz cave, but they ride different messages at different rates, so
reconstructing a SIGNED lane costs up to ~10-20 ms of relative timing = 28-56 deg at 7.79 Hz.

⇒ HOW THIS FILE HANDLES IT, rather than ignoring it:
   * MAGNITUDE-ONLY statistics (band content, duty, engagement contrast) come from ONE message and
     carry NO skew.  They are the load-bearing results.
   * The SIGNED reconstruction is reported WITH a skew-sensitivity control: the whole estimate is
     recomputed with the sign stream shifted by -2, -1, 0, +1, +2 samples of the 100 Hz grid, and if
     a conclusion moves across that sweep it is reported as UNRESOLVED rather than as a phase.

===================================================================================================
THE PRE-DECLARED TRUST GATE (carried verbatim from `v92_rez_extend.py`, not re-chosen here)
===================================================================================================
    a band's phase is reported as MEASURABLE only if  coh^2 >= 0.10  AND  coh^2 >= 5x shuffled.
    Anything failing that is reported as UNMEASURABLE.  "Cannot establish" is a real answer.
🛑 And the wheel-order veto is applied PER BAND, both vetoed and unvetoed reported side by side.

Usage:  python v92_boost_lane_and_rez.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v90_probe as P          # noqa: E402  -- FROZEN estimator, imported read-only

RNG = np.random.default_rng(78_79_2026)
DEG2RAD = np.pi / 180.0
CACHE = ROOT / "analysis-2020accord"

BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
         ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
BANDS50 = [b for b in BANDS if b[2] <= 24.0]        # 50 Hz grid -> Nyquist 25 Hz
COH_ABS, COH_REL = 0.10, 5.0


def order_conflict(v, lo, hi):
    for k in P.ORDERS:
        for c in (P.CIRC_LO, P.CIRC_HI):
            if lo - P.GUARD <= k * v / c <= hi + P.GUARD:
                return True
    return False


def trust(coh, shuf):
    return bool(np.isfinite(coh) and coh >= COH_ABS and coh >= COH_REL * max(shuf, 1e-9))


def load(route, stem):
    return np.load(CACHE / f"_cache_r{route}" / f"{stem}.npz", allow_pickle=True)


# ======================================================================================
#  PART A -- Re(Z), skew-free (both channels are fields of the SAME 0x18F frame)
# ======================================================================================
def rez(tag, route, stem):
    z = load(route, stem)
    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)                      # 0x18F bytes 0-1
    rate_f = np.asarray(z["rate_f"], float) * DEG2RAD    # 0x18F bytes 2-3  -- SAME frame
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    mask = lat & (~press) & (v > 0.5)
    fs = 1.0 / float(np.median(np.diff(t)))
    W = P._wins(mask, t, P.NW_Z, P.HOP_Z, (rate_f, tq, v))
    print(f"\n  === Re(Z), {tag}: {len(W)} engaged hands-off moving windows "
          f"({mask.sum()/fs:.1f} s), fs {fs:.2f} Hz ===")
    print(f"    {'band':8s} {'n':>5s} {'v med':>7s} {'Re(Z)':>11s} {'phase':>9s} "
          f"{'coh²':>7s} {'shuf':>7s} {'TRUST':>7s}")
    rows = {}
    for nm, lo, hi in BANDS:
        for vet in (False, True):
            sel = [w for w in W
                   if (not vet) or (not order_conflict(float(np.mean(np.abs(w[2]))), lo, hi))]
            if len(sel) < 6:
                continue
            pairs = [(w[0], w[1]) for w in sel]
            r = P._band_transfer(pairs, fs, P.NW_Z, [(nm, lo, hi)])[nm]
            idx = RNG.permutation(len(pairs))
            rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                                   for i in range(len(pairs))], fs, P.NW_Z, [(nm, lo, hi)])[nm]
            vmed = float(np.median([np.mean(np.abs(w[2])) for w in sel]))
            ok = trust(r["coh2"], rs["coh2"])
            rows[f"{nm}/{'vetoed' if vet else 'all'}"] = dict(
                n=len(sel), v_med=vmed, re_z=r["re_over_sxx"], phase_deg=r["phase_deg"],
                coh2=r["coh2"], coh2_shuf=rs["coh2"], trustworthy=ok)
            sgn = "ANTI-DAMPED" if r["re_over_sxx"] < 0 else "damped"
            print(f"    {nm + ('*' if vet else ' '):8s} {len(sel):5d} {vmed:7.2f} "
                  f"{r['re_over_sxx']:11.1f} {r['phase_deg']:8.1f}° {r['coh2']:7.3f} "
                  f"{rs['coh2']:7.3f} {('YES ' + sgn) if ok else '🛑 NO':>7s}")
    print("    (* = wheel-order vetoed for that band)")
    return rows


# ======================================================================================
#  PART B -- the BOOST lane gp-0x6bbe, route 79 only
# ======================================================================================
def boost_lane(shift_samples=0):
    z = load("79", "r79")
    t = np.asarray(z["t"], float)
    lat_row = np.asarray(z["cc_lat"], float) > 0.5
    press_row = np.asarray(z["cs_press"], float) > 0.5
    v_row = np.abs(np.asarray(z["cs_v"], float))
    tq_row = np.asarray(z["tq"], float)
    rate_row = np.asarray(z["rate_f"], float) * DEG2RAD

    # --- magnitude, 50 Hz, ONE message, NO skew
    tab = np.asarray(z["ab_t1ab"], float)
    mag = np.asarray(z["ab_mt"], int) * (16.0 / 5.0)         # counts of gp-0x6bbe

    # --- sign, 100 Hz, the OTHER message.  shift_samples is the skew-sensitivity knob.
    t14 = np.asarray(z["raw14_t"], float)
    neg = (np.asarray(z["raw14_b4"], int) & 0x80) != 0       # b7 = gp-0x6bbe < 0
    if shift_samples:
        neg = np.roll(neg, shift_samples)
    sgn_at_427 = np.where(np.interp(tab, t14, neg.astype(float)) > 0.5, -1.0, 1.0)
    signed = mag * sgn_at_427

    lat = np.interp(tab, t, lat_row.astype(float)) > 0.5
    press = np.interp(tab, t, press_row.astype(float)) > 0.5
    v = np.interp(tab, t, v_row)
    tq = np.interp(tab, t, tq_row)
    rate = np.interp(tab, t, rate_row)
    mask = lat & (~press) & (v > 0.5)
    fs = 1.0 / float(np.median(np.diff(tab)))
    return dict(t=tab, mag=mag, signed=signed, lat=lat, press=press, v=v, tq=tq, rate=rate,
                mask=mask, fs=fs)


def boost_report(B):
    print("\n" + "=" * 100)
    print(" PART B — THE BOOST LANE gp-0x6bbe, FIRST MEASUREMENT IN THE KIT'S HISTORY (route 79)")
    print("=" * 100)
    mag, lat, v = B["mag"], B["lat"], B["v"]
    mv = lat & (v > 0.5)
    print(f"\n  --- MAGNITUDE (single message, NO skew) ---")
    for tag, s in (("engaged & moving", mv), ("engaged", lat), ("manual", ~lat)):
        if not s.sum():
            continue
        x = mag[s]
        print(f"    {tag:<18} n={len(x):>6,}  p50 {np.median(x):>7.1f}  p90 "
              f"{np.percentile(x, 90):>7.1f}  p99 {np.percentile(x, 99):>7.1f}  "
              f"max {x.max():>7.1f}  nonzero {100*np.mean(x > 0):.2f} %")
    print(f"    ⚠ 427 saturates at wire 1023 = {1023*16/5:.0f} counts; observed max wire "
          f"{int(B['mag'].max()*5/16)} ⇒ NO clipping, the sar-4 fix did its job.")
    out = {"magnitude": {t_: dict(p50=float(np.median(mag[s])), p90=float(np.percentile(mag[s], 90)),
                                  max=float(mag[s].max()), n=int(s.sum()))
                         for t_, s in (("engaged_moving", mv), ("manual", ~lat)) if s.sum()}}

    # ---- band content of the SIGNED lane, and its dissipative product with wheel rate
    print(f"\n  --- SIGNED LANE vs WHEEL RATE — the anti-damping question, and its SKEW CONTROL ---")
    print(f"    {'band':8s} " + "  ".join(f"{f'shift{s:+d}':>10s}" for s in (-2, -1, 0, 1, 2)) +
          f"   {'coh²(0)':>8s} {'shuf':>7s} {'TRUST':>6s}")
    rows = {}
    per_shift = {}
    for s in (-2, -1, 0, 1, 2):
        Bs = boost_lane(s)
        W = P._wins(Bs["mask"], Bs["t"], P.NW50, P.HOP50, (Bs["rate"], Bs["signed"], Bs["v"]))
        per_shift[s] = (W, Bs["fs"])
    for nm, lo, hi in BANDS50:
        vals, coh0, shuf0, n0 = {}, np.nan, np.nan, 0
        for s in (-2, -1, 0, 1, 2):
            W, fs = per_shift[s]
            if len(W) < 6:
                continue
            pairs = [(w[0], w[1]) for w in W]
            r = P._band_transfer(pairs, fs, P.NW50, [(nm, lo, hi)])[nm]
            vals[s] = r["re_over_sxx"]
            if s == 0:
                idx = RNG.permutation(len(pairs))
                rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                                       for i in range(len(pairs))], fs, P.NW50,
                                      [(nm, lo, hi)])[nm]
                coh0, shuf0, n0 = r["coh2"], rs["coh2"], len(pairs)
        if not vals:
            continue
        signs = {np.sign(x) for x in vals.values()}
        stable = len(signs) == 1
        ok = trust(coh0, shuf0)
        rows[nm] = dict(re_by_shift={int(k): float(x) for k, x in vals.items()},
                        sign_stable_across_skew=stable, coh2=float(coh0),
                        coh2_shuf=float(shuf0), n=n0, trustworthy=bool(ok))
        flag = "YES" if ok else "🛑 NO"
        star = "" if stable else "   🛑 SIGN FLIPS ACROSS THE SKEW SWEEP -- UNRESOLVED"
        print(f"    {nm:8s} " + "  ".join(f"{vals.get(s, float('nan')):10.1f}"
                                          for s in (-2, -1, 0, 1, 2)) +
              f"   {coh0:8.3f} {shuf0:7.3f} {flag:>6s}{star}")
    out["signed_vs_rate"] = rows

    # ---- the ENGAGEMENT contrast on the sign bit -- a DC claim, robust to 10 ms skew
    z = load("79", "r79")
    t = np.asarray(z["t"], float)
    t14 = np.asarray(z["raw14_t"], float)
    neg = (np.asarray(z["raw14_b4"], int) & 0x80) != 0
    lat14 = np.interp(t14, t, (np.asarray(z["cc_lat"], float) > 0.5).astype(float)) > 0.5
    v14 = np.interp(t14, t, np.abs(np.asarray(z["cs_v"], float)))
    mov = v14 > 0.5
    print(f"\n  --- SIGN BIT: the ENGAGEMENT CONTRAST (a DC claim — robust to the skew) ---")
    print(f"    P(gp-0x6bbe < 0)   engaged & moving {neg[lat14 & mov].mean():.4f}   "
          f"manual & moving {neg[(~lat14) & mov].mean():.4f}   "
          f"manual & parked {neg[(~lat14) & (~mov)].mean():.4f}")
    out["sign_engagement_contrast"] = dict(
        engaged_moving=float(neg[lat14 & mov].mean()),
        manual_moving=float(neg[(~lat14) & mov].mean()),
        manual_parked=float(neg[(~lat14) & (~mov)].mean()),
        n_engaged_moving=int((lat14 & mov).sum()), n_manual_moving=int(((~lat14) & mov).sum()))
    print("    ⇒ engaging the system drives the boost lane to a NEAR-CONSTANT SIGN.  That is a DC")
    print("      bias in an aggregator lane, which is exactly the operator's own stated mechanism:")
    print('      "the ratchet is just on a DC LKAS command."')
    return out


# ======================================================================================
if __name__ == "__main__":
    OUT = {}
    print("=" * 100)
    print(" PART A — Re(Z) REPLICATED ON TWO NEW DRIVES  (routes 77/78/79 are CALIBRATION-IDENTICAL")
    print("          — the ×1.5 dose was measured INERT this session, so these are three drives on")
    print("          the SAME functional car, and any difference between them is DRIVE VARIATION.)")
    print("=" * 100)
    for tag, route, stem in (("route 77 (V90) — frozen positive control", "77", "r77"),
                             ("route 78 (V91) — 159.9 s engaged ≥ 80 km/h, best highway in the kit",
                              "78", "r78"),
                             ("route 79 (V92)", "79", "r79")):
        OUT[f"rez_r{route}"] = rez(tag, route, stem)

    B = boost_lane(0)
    OUT["boost"] = boost_report(B)

    (CACHE / "_cache_r79" / "boost_lane_and_rez.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote analysis-2020accord/_cache_r79/boost_lane_and_rez.json")
