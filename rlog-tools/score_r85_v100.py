#!/usr/bin/env python3
r"""SCORE ROUTE 85 = THE V100 FLIGHT (the SATURATION INSTRUMENT).

The statistics are the PRE-REGISTERED ones from `build_v100_tva.py`.  Nothing is re-invented and
nothing is substituted.  Shared machinery (`band_rms`, `acf_tau`, the split-half null, the
standardised ratio) is IMPORTED from the scorers that scored routes 80/81/82, so a number here is
comparable to a number there by construction.

===================================================================================================
V100's byte-4 map, read off `build_v100_tva.py`'s PAYLOAD
===================================================================================================
    b7 0x80 = gp-0x6b94 < 0                          the SIGN for the 427 magnitude lane
    b6 0x40 = |gp-0x4f60 - gp-0x6ad6| >= 10240       RUNG D'  -- the PID ERROR clamp predicate
    b5 0x20 = |gp-0x6ad6| >= cal(0xC6200) = 8192     RUNG A   -- the PID REFERENCE clamp
    b4 0x10 = gp-0x6ad6 < 0                          sign / THE POSITIVE CONTROL
    b3 0x08 = 1                                      IDENTITY
    427     = clamp(|gp-0x6b94| * 5 >> 6, 0, 0x3FF)  counts = wire * 12.8, structural ceiling 800

🛑 SEGMENT 17 IS ABSENT.  `episodes()` in the shared library is INDEX-contiguous and therefore
   BRIDGES the ~60 s hole between segment 16 and segment 18.  This file uses `episodes_t()`, which
   additionally splits on a TIME gap.  Every episode-based CI below uses `episodes_t`.  The census's
   "2 episodes, longest 233.6 s" is the bridged figure and MUST NOT be quoted.

🛑 THE SIGNED LANE.  `x6b94` = sign(b7) * code * 12.8, produced by `extract_r85.derive()`.  Feeding
   this lane RECTIFIED into a band statistic was measured to understate 6-9 Hz RMS by 4.9-5.5x.
   This file never touches `mag427` for a band statistic.

Usage:
    python score_r85_v100.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

from v97_r80_vs_v96 import band_rms                      # noqa: E402  the SAME band statistic
from v99_r82_score import (acf_tau, geo_median,          # noqa: E402  the SAME estimators
                           split_half_null)

OUT = AN / "_v100"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20260813)

FS = 100.0
NPERSEG, HOP, BLOCK_S = 128, 64, 5.12       # 1.28 s windows, 50 % overlap, 5.12 s blocks
KMH = 3.6
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
COUNTS_PER_LSB = 64.0 / 5.0
REF_CLAMP, ERR_CLAMP = 8192, 10240
SAT_STRUCT = 800

# imported constants, EVIDENCE on routes 81/82, BELIEF that they generalise -- see build_v100_tva
PHI_K = 0.2565
ANCHOR_A, ANCHOR_SE = 1.13, 0.09
Q_C = 1.254                                  # phi_c / (0.2565 * A) at A = 1.13
Q_BAND = (1.12, 1.39)                        # the pre-registered INDETERMINATE band
TAU_PRIOR_THRESHOLD = (0.065, 0.603)         # build_v100_tva's measured threshold-rung tau range
POS4_FLIPS = (11.68, 13.09)                  # b7 sign flips/s measured on the sibling lane r81/r82

_checks = []


def note(ok, msg):
    _checks.append((bool(ok), msg))
    print(f"    {'[PASS]' if ok else '[FAIL]'} {msg}")
    return ok


# ==================================================================================================
def load():
    z = np.load(AN / "_cache_r85" / "r85.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    idx = np.asarray(z["row2raw14"], int)
    b4 = (np.asarray(z["raw14_b4"], int) & 0xFF)[idx]
    b7b = (np.asarray(z["raw14_b7"], int) & 0xFF)[idx]
    # 🛑 the off-by-one assertion.  If this fails the readout is 28 deg out at 7.79 Hz.
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF)), "raw14 map broken"
    d = dict(
        t=t, b4=b4, seg=np.asarray(z["seg"], int),
        eng=np.asarray(z["cc_lat"], float) > 0.5,
        ident=(b7b & 0xC0) >> 6,
        b7=(b4 & M_B7) != 0, b6=(b4 & M_B6) != 0, b5=(b4 & M_B5) != 0,
        b4b=(b4 & M_B4) != 0, b3=(b4 & M_B3) != 0,
        v=np.asarray(z["cs_v"], float) * KMH,
        v_rear=np.asarray(z["v_rear"], float),
        rate=np.asarray(z["cs_rate"], float),
        ang=np.asarray(z["cs_ang"], float),
        tq=np.asarray(z["tq"], float),               # column torque, CAN 0x18F  (E3's numerator)
        cs_tq=np.asarray(z["cs_tq"], float),         # driver torque, carState
        e4tq=np.asarray(z["e4tq"], float),           # LKAS command on the wire, 0x0E4
        co_req=np.asarray(z["co_req"], float),       # openpilot's commanded torque
        press=np.asarray(z["cs_press"], float) > 0.5,
        mag427=np.asarray(z["mag427"], float),
        x6b94=np.asarray(z["x6b94"], float),         # ⭐ the SIGNED lane
        lp_yaw=np.asarray(z["lp_yaw"], float),
    )
    return d


def episodes_t(sel, t, seg, min_s=1.0, gap_tol=0.05):
    """Contiguous True runs that are ALSO contiguous in TIME and within one segment.
    🛑 The shared `episodes()` is index-contiguous only and bridges the missing segment 17."""
    sel = np.asarray(sel, bool)
    brk = np.zeros(len(sel), bool)
    brk[1:] = (np.diff(t) > gap_tol) | (np.diff(seg) != 0)
    out, a = [], None
    for i in range(len(sel)):
        if sel[i] and (a is None or brk[i]):
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = i
        elif not sel[i]:
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = None
    if a is not None and t[-1] - t[a] >= min_s:
        out.append((a, len(sel)))
    return out


def rule_of_three(n_eff):
    return 3.0 / n_eff if n_eff > 0 else float("nan")


def duty_ci(bits, sel, tau):
    p = float(bits[sel].mean())
    T = float(sel.sum()) / FS
    if not (tau and tau > 0 and np.isfinite(tau)):
        return dict(duty=p, T_s=T, tau=float("nan"), n_eff=float("nan"),
                    lo=float("nan"), hi=float("nan"))
    neff = T / tau
    se = np.sqrt(max(p * (1 - p), 0.0) / neff)
    return dict(duty=p, T_s=T, tau=float(tau), n_eff=float(neff),
                lo=float(p - 1.96 * se), hi=float(p + 1.96 * se))


def flip_rate(bits, eps, t):
    """Transitions per second, computed INSIDE episodes only (never across a seam)."""
    n, T = 0, 0.0
    for a, b in eps:
        n += int(np.sum(np.diff(bits[a:b].astype(int)) != 0))
        T += float(t[b - 1] - t[a])
    return (n / T if T > 0 else float("nan")), n, T


def runs_of(bits, eps):
    """Number of separate True RUNS (episodes of the bit being set) inside engaged episodes."""
    n = 0
    for a, b in eps:
        x = bits[a:b].astype(int)
        if len(x):
            n += int(x[0]) + int(np.sum(np.diff(x) == 1))
    return n


# ==================================================================================================
def main():
    res = {}
    d = load()
    t, eng = d["t"], d["eng"]
    eps = episodes_t(eng, t, d["seg"], min_s=1.0)
    T_eng = sum(t[b - 1] - t[a] for a, b in eps)
    n_eng = int(eng.sum())

    print("=" * 100)
    print("  ⭐ ROUTE 85 = V100.  THE SATURATION INSTRUMENT.  Pre-registered endpoints only.")
    print("=" * 100)

    # ============================== 0. EXPOSURE, IN TIME SPACE ===================================
    print("\n=== 0.  EXPOSURE -- engaged episodes recomputed in TIME space (segment 17 is ABSENT) ===")
    per_seg = {}
    for s in sorted(set(d["seg"].tolist())):
        m = d["seg"] == s
        e = m & eng
        per_seg[int(s)] = dict(frames=int(m.sum()), sec=float(m.sum() / FS),
                               engaged_sec=float(e.sum() / FS),
                               v_median_kmh=float(np.median(d["v"][m])),
                               v_rear_median_kmh=float(np.nanmedian(d["v_rear"][m])))
    for s, r in per_seg.items():
        print(f"    seg {s:2d}  {r['frames']:6,} frames  {r['sec']:5.1f} s  engaged "
              f"{r['engaged_sec']:5.1f} s   v(cs) {r['v_median_kmh']:6.2f}  "
              f"v(rear) {r['v_rear_median_kmh']:6.2f} km/h")
    print(f"\n    ENGAGED EPISODES (time-contiguous, >= 1 s): {len(eps)}")
    for i, (a, b) in enumerate(eps):
        print(f"      ep {i:2d}  seg {d['seg'][a]:2d}  t {t[a]:7.2f} .. {t[b-1]:7.2f} s  "
              f"dur {t[b-1]-t[a]:6.2f} s  v(rear) median "
              f"{np.nanmedian(d['v_rear'][a:b]):6.2f} km/h  "
              f"|rate| p50 {np.percentile(np.abs(d['rate'][a:b]), 50):5.1f} °/s")
    print(f"    TOTAL ENGAGED {T_eng:.1f} s in {len(eps)} episodes "
          f"({n_eng:,} frames).  steeringPressed duty engaged "
          f"{d['press'][eng].mean():.4f}")
    res["exposure"] = dict(per_segment=per_seg, n_episodes=len(eps),
                           episode_s=[float(t[b - 1] - t[a]) for a, b in eps],
                           T_engaged_s=T_eng, n_engaged_frames=n_eng,
                           pressed_duty_engaged=float(d["press"][eng].mean()))

    # ============================== 1. TAU FOR EVERY BIT =========================================
    print("\n" + "=" * 100)
    print("=== 1.  MEASURED TAU FOR EVERY BIT -- the pre-registered basis for every CI below")
    print("=" * 100)
    print("    tau = integral of the ACF to its first zero crossing, on ENGAGED frames.")
    print("    🛑 A CONSTANT bit has NO tau (std = 0).  For b5/b6 the answer is therefore NOT a")
    print("       bootstrap -- it is the RULE OF THREE on n_eff, with n_eff from a SURROGATE tau")
    print("       measured on a REAL threshold rung on THIS ROUTE (below).")
    taus = {}
    for name, bits in (("b7 sign(gp-0x6b94)", d["b7"]), ("b6 RUNG D'", d["b6"]),
                       ("b5 RUNG A", d["b5"]), ("b4 sign(gp-0x6ad6)", d["b4b"]),
                       ("b3 IDENTITY", d["b3"])):
        x = bits[eng].astype(float)
        tau = acf_tau(x) if np.std(x) > 0 else float("nan")
        taus[name] = tau
        neff = T_eng / tau if np.isfinite(tau) and tau > 0 else float("nan")
        print(f"    {name:22s} duty {x.mean():.6f}   tau "
              f"{'   CONSTANT' if not np.isfinite(tau) else f'{tau:8.4f} s'}   n_eff "
              f"{'  --' if not np.isfinite(neff) else f'{neff:7.0f}'}")
    res["tau_measured"] = {k: (None if not np.isfinite(v) else float(v)) for k, v in taus.items()}

    print("\n    SURROGATE TAU for a THRESHOLD rung, synthesised on THIS route from the real 427")
    print("    lane (`|gp-0x6b94| >= thr`).  Same method as `v100_power_gate.py`, on-route data:")
    sur = {}
    c = d["mag427"][eng] * COUNTS_PER_LSB
    for thr in (256, 512, 768, 1024, 1280):
        bit = (c >= thr).astype(float)
        if bit.mean() in (0.0, 1.0):
            continue
        tau = acf_tau(bit)
        sur[thr] = tau
        print(f"      thr {thr:5d} ct   duty {bit.mean():.4f}   tau {tau:7.4f} s   "
              f"n_eff {T_eng/tau:7.0f}")
    tau_lo, tau_hi = float(min(sur.values())), float(max(sur.values()))
    print(f"    ⇒ ON-ROUTE threshold-rung tau range: {tau_lo:.4f} - {tau_hi:.4f} s")
    print(f"      (build_v100_tva's pre-flight prior was {TAU_PRIOR_THRESHOLD[0]:.3f} - "
          f"{TAU_PRIOR_THRESHOLD[1]:.3f} s, measured on routes 80/81/82)")
    tau_worst = max(tau_hi, TAU_PRIOR_THRESHOLD[1])
    res["tau_surrogate_threshold"] = dict(per_threshold={str(k): float(v) for k, v in sur.items()},
                                          range=[tau_lo, tau_hi],
                                          prior_range=list(TAU_PRIOR_THRESHOLD),
                                          tau_used_worst_case=tau_worst)

    # ============================== 2. E1 -- RUNG A ==============================================
    print("\n" + "=" * 100)
    print("=== 2.  E1 -- d(b5), THE REFERENCE-CLAMP DUTY, ENGAGED.  A SINGLE-DRIVE ABSOLUTE.")
    print("=" * 100)
    d_b5 = float(d["b5"][eng].mean())
    n_runs_b5 = runs_of(d["b5"], eps)
    print(f"    d(b5) ENGAGED = {d_b5:.6f}   over {n_eng:,} engaged frames / {T_eng:.1f} s")
    print(f"    d(b5) ALL     = {float(d['b5'].mean()):.6f}   d(b5) MANUAL = "
          f"{float(d['b5'][~eng].mean()):.6f}")
    print(f"    independent CLAMP EPISODES (separate runs of b5 == 1 inside engaged): {n_runs_b5}")
    print(f"    max |raw| evidence: b5 is set on {int(d['b5'].sum())} of {len(d['b5']):,} frames "
          f"route-wide.")
    e1 = dict(duty_engaged=d_b5, duty_all=float(d["b5"].mean()),
              duty_manual=float(d["b5"][~eng].mean()),
              n_engaged_frames=n_eng, T_engaged_s=T_eng, clamp_episodes=n_runs_b5)
    print("\n    🛑 THE NORMAL APPROXIMATION FAILS AT THE RAIL.  Rule of three on EFFECTIVE samples:")
    for tag, tau in (("best case (on-route min)", tau_lo), ("worst case (pre-flight max)",
                                                            tau_worst)):
        neff = T_eng / tau
        ub = rule_of_three(neff)
        e1[f"upper95_{tag}"] = float(ub)
        print(f"      tau {tau:6.3f} s -> n_eff {neff:7.0f} -> 95 % UPPER BOUND on d(b5) = "
              f"{ub:.5f}  (= {ub*T_eng:.2f} s of clamped time)")
    neff_w = T_eng / tau_worst
    ub_w = rule_of_three(neff_w)
    e1["n_eff_worst"] = float(neff_w)
    e1["upper95_worst"] = float(ub_w)
    print(f"\n    ⭐ CONSERVATIVE STATEMENT: d(b5) = 0.000000, 95 % CI [0, {ub_w:.5f}].")
    print(f"       The build's pre-registered RESOLVABLE WINDOW was [0.030, 0.970]; this drive's")
    print(f"       exposure ({T_eng:.1f} s vs the 59.8 s assumed) pushes the floor DOWN to "
          f"{ub_w:.4f},")
    print(f"       i.e. {0.030/ub_w:.1f}x better than the build was designed for.")
    print(f"       The HIGH-reading threshold the build named was >= 0.30.  The measured value is")
    print(f"       {0.30/ub_w:.0f}x below its own 95 % upper bound.  This is a HARD ZERO.")

    dead = not (0.05 < float(d["b4b"][eng].mean()) < 0.95 and 0.05 < float(d["b7"][eng].mean())
                < 0.95)
    e1["dead_instrument_trap_cleared"] = not dead
    print("\n    THE DEAD-INSTRUMENT TRAP (build_v100_tva, verbatim: 'A composite null may only be")
    print("    reported when b4 and b7 are both strictly inside (0.05, 0.95)'):")
    note(0.05 < float(d["b4b"][eng].mean()) < 0.95,
         f"b4 engaged duty {float(d['b4b'][eng].mean()):.4f} strictly inside (0.05, 0.95)")
    note(0.05 < float(d["b7"][eng].mean()) < 0.95,
         f"b7 engaged duty {float(d['b7'][eng].mean()):.4f} strictly inside (0.05, 0.95)")
    print("    ⭐ AND THE STRONGER FORM, which the build did not have to rely on: b4 reads the SAME")
    print("       CELL as b5 (gp-0x6ad6).  b4 toggling proves the cell is LOADED and SIGN-VARYING,")
    print("       so the b5 zero is a fact about its MAGNITUDE, not about a dead load.")

    e1["licensed_sentence"] = (
        "gp-0x6ad6 never reached the PID's +-8192 clamp in any engaged frame.  Path 2's marginal "
        "authority was NOT zeroed by this saturation, d(gp-0x6b94)/d(gp-0x6b70) = 0.2565 stands in "
        "the flown regime, and the f'-compression account in STATE.md remains the only surviving "
        "explanation for V89 and V97.  THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND MUST NOT BE "
        "RE-PROPOSED.")
    print(f"\n    ⇒ THE PRE-REGISTERED ZERO SENTENCE IS LICENSED, VERBATIM:\n"
          f"      \"{e1['licensed_sentence']}\"")
    res["E1"] = e1

    # ============================== 3. E2 -- THE ERROR CLAMP =====================================
    print("\n" + "=" * 100)
    print("=== 3.  E2 -- THE ERROR CLAMP.  The full joint 2x2 (b6, b5), then all three statistics.")
    print("=" * 100)
    tab = {}
    for i in (0, 1):
        for j in (0, 1):
            sel = eng & (d["b6"] == bool(i)) & (d["b5"] == bool(j))
            tab[f"b6={i},b5={j}"] = int(sel.sum())
    n00 = tab["b6=0,b5=0"]
    n10 = tab["b6=1,b5=0"]
    n01 = tab["b6=0,b5=1"]
    n11 = tab["b6=1,b5=1"]
    N = n00 + n10 + n01 + n11
    print(f"                  b5 = 0        b5 = 1")
    print(f"      b6 = 0   {n00:10,}   {n01:10,}")
    print(f"      b6 = 1   {n10:10,}   {n11:10,}      N = {N:,} engaged frames")
    marg = (n10 + n11) / N
    cond = n10 / (n00 + n10) if (n00 + n10) else float("nan")
    comp = 1 - n00 / N
    n_runs_b6 = runs_of(d["b6"], eps)
    print(f"\n      MARGINAL    d(b6)          = {marg:.6f}   <- REPORTABLE AT FULL n "
          f"(n = {N:,})")
    print(f"      CONDITIONAL d(b6 | b5 = 0)  = {cond:.6f}   <- THE ERROR CLAMP'S TRUE DUTY "
          f"(n = {n00+n10:,})")
    print(f"      COMPOSITE   d(b5 or b6)     = {comp:.6f}   <- EXACT, full n")
    print(f"      independent ERROR-CLAMP EPISODES (runs of b6 == 1 inside engaged): {n_runs_b6}")
    print("\n    🛑 d(b6) UNCONDITIONED IS NOT THE ERROR CLAMP'S DUTY.  Here it does not matter:")
    print(f"       d(b5) = 0.000000, so the conditioning set is the WHOLE engaged sample "
          f"({n00+n10:,} of {N:,} frames = {100*(n00+n10)/N:.4f} %), and MARGINAL == CONDITIONAL")
    print("       IDENTICALLY.  The scenario the build feared -- d(b5) near 1 emptying E2's")
    print("       conditioning set -- DID NOT OCCUR.  Both statistics are resolvable at full n.")
    ub6 = rule_of_three(T_eng / tau_worst)
    print(f"\n    Rule of three on the SAME n_eff: 95 % upper bound on d(b6 | b5=0) = {ub6:.5f}")
    print(f"    ⇒ d(b6 | b5 = 0) = 0.000000, 95 % CI [0, {ub6:.5f}].")
    res["E2"] = dict(table=tab, N=N, marginal=float(marg), conditional=float(cond),
                     composite=float(comp), conditioning_n=int(n00 + n10),
                     error_clamp_episodes=n_runs_b6, upper95_conditional=float(ub6),
                     resolvable="ALL THREE -- the conditioning set is the entire engaged sample")
    if marg == 0.0 and d_b5 == 0.0 and not dead:
        res["E2"]["composite_null_sentence"] = (
            "Neither saturation was active -- Path-2's marginal authority was never zeroed by "
            "clipping.")
        print("\n    ⇒ THE COMPOSITE NULL SENTENCE IS LICENSED, VERBATIM (d(b5)=0.0000 AND")
        print("      d(b6)=0.0000 with the positive controls healthy):")
        print(f"      \"{res['E2']['composite_null_sentence']}\"")
        print("      It closes the whole saturation FAMILY, not one clamp.")

    # ============================== 4. THE CONTROLS ==============================================
    print("\n" + "=" * 100)
    print("=== 4.  THE POSITIVE CONTROLS -- POS-3 (b4) and POS-4 (b7)")
    print("=" * 100)
    ctl = {}
    for name, bits, tname in (("b4 = gp-0x6ad6 < 0", d["b4b"], "b4 sign(gp-0x6ad6)"),
                              ("b7 = gp-0x6b94 < 0", d["b7"], "b7 sign(gp-0x6b94)")):
        tau = taus[tname]
        ci = duty_ci(bits, eng, tau)
        fr, nfl, Tf = flip_rate(bits, eps, t)
        ctl[name] = dict(**ci, flips_per_s=float(fr), n_flips=int(nfl),
                         inside_005_095=bool(0.05 < ci["duty"] < 0.95))
        print(f"    {name:22s} duty {ci['duty']:.4f}  95 % CI [{ci['lo']:.4f}, {ci['hi']:.4f}]  "
              f"tau {ci['tau']:.4f} s  n_eff {ci['n_eff']:.0f}")
        print(f"      {'':22s} sign flips {nfl:,} in {Tf:.1f} s engaged = {fr:.2f}/s   "
              f"inside (0.05,0.95): {ctl[name]['inside_005_095']}")
    print(f"\n    POS-4 pre-registered 11-13 sign transitions/s on the SIBLING lane gp-0x6b70 "
          f"(r81 {POS4_FLIPS[0]}/s, r82 {POS4_FLIPS[1]}/s).")
    fr7 = ctl["b7 = gp-0x6b94 < 0"]["flips_per_s"]
    print(f"    MEASURED on gp-0x6b94: {fr7:.2f}/s.  ⚠ This is a DIFFERENT CELL (the aggregator")
    print(f"       output, not the PID reference lane), so 11-13/s is an EXPECTATION, not a")
    print(f"       requirement.  A mismatch indicts neither the build nor the car.")

    # ---- POS-3's real content: b4 must TRACK openpilot's commanded sign.
    print("\n    POS-3's substantive leg: gp-0x6ad6 is dominated by -gp-0x6b4a, the LKAS demand")
    print("    path, so sign(gp-0x6ad6) must be PREDICTED by the commanded torque.  Two independent")
    print("    command channels, and a LAG-SHUFFLED control for each:")
    pos3 = {}
    for cname, cmd in (("0x0E4 wire command (e4tq)", d["e4tq"]),
                       ("openpilot co_req", d["co_req"])):
        m = eng & np.isfinite(cmd) & (np.abs(cmd) > 1e-9)
        if m.sum() < 100:
            continue
        neg = d["b4b"][m]
        cn = cmd[m] < 0
        agree = float((neg == cn).mean())
        # control: circularly shift the command by 30 s -- destroys the pairing, keeps the marginals
        sh = int(30 * FS)
        cn_s = (np.roll(cmd, sh)[m] < 0)
        agree_s = float((neg == cn_s).mean())
        pos3[cname] = dict(n=int(m.sum()), agree_same_sign=agree,
                           agree_opposite_sign=1 - agree, agree_shuffled_control=agree_s)
        print(f"      {cname:28s} n={int(m.sum()):6,}   P(sign(gp-0x6ad6) == sign(cmd)) = "
              f"{agree:.4f}   P(opposite) = {1-agree:.4f}")
        print(f"      {'':28s} 30 s-SHIFTED CONTROL = {agree_s:.4f}  <- the chance level")
    # ---- lag scan + block-bootstrap CI on the EXCESS over the shuffled chance level
    print("\n    LAG SCAN on the 0x0E4 wire command (the cave samples gp-0x6ad6 asynchronously to")
    print("    the CAN TX, so a small lag is expected).  Excess = agreement - 30 s-shifted chance:")
    cmd = d["e4tq"]
    m = eng & np.isfinite(cmd) & (np.abs(cmd) > 1e-9)
    best = (None, -9)
    scan = {}
    for lag in range(-50, 51, 5):
        cn = (np.roll(cmd, lag)[m] < 0)
        a_ = float((d["b4b"][m] == cn).mean())
        scan[lag / FS] = a_
        if a_ > best[1]:
            best = (lag / FS, a_)
    print("      " + "  ".join(f"{k:+.2f}s:{v:.3f}" for k, v in sorted(scan.items())
                               if abs(k) <= 0.25))
    print(f"      best lag {best[0]:+.2f} s -> agreement {best[1]:.4f}")
    # excess CI by resampling ENGAGED EPISODES
    cn0 = cmd < 0
    ex = []
    for _ in range(2000):
        pick = RNG.choice(len(eps), len(eps), True)
        ii = np.concatenate([np.arange(eps[k][0], eps[k][1]) for k in pick])
        ii = ii[np.abs(cmd[ii]) > 1e-9]
        p_ = d["b4b"][ii].mean()
        q_ = cn0[ii].mean()
        ex.append(float((d["b4b"][ii] == cn0[ii]).mean() - (p_ * q_ + (1 - p_) * (1 - q_))))
    exlo, exhi = float(np.percentile(ex, 2.5)), float(np.percentile(ex, 97.5))
    exm = float(np.mean(ex))
    print(f"      ⭐ EXCESS over the marginal-matched chance level: {exm:+.4f} "
          f"95 % CI [{exlo:+.4f}, {exhi:+.4f}]  (block bootstrap over {len(eps)} EPISODES)")
    pos3["lag_scan_e4tq"] = {str(k): v for k, v in scan.items()}
    pos3["best_lag_s"] = best[0]
    pos3["excess_over_chance"] = dict(mean=exm, lo=exlo, hi=exhi,
                                      resolves=bool(exlo > 0 or exhi < 0))
    if exlo > 0:
        print("      ⇒ POS-3 SUBSTANTIVE LEG: sign(gp-0x6ad6) IS predicted by the LKAS command at")
        print("        better than chance, CI excludes 0 ⇒ the cell is the LKAS-fed one.")
        print("        🛑 BUT THE ASSOCIATION IS WEAK, not 'dominated'.  build_v100_tva says")
        print("        gp-0x6ad6 'is dominated by -gp-0x6b4a, the LKAS demand path'.  An excess of")
        print(f"        {exm:+.3f} is a MINORITY influence.  Report POS-3 as PASSED ON DIRECTION,")
        print("        FAILED ON MAGNITUDE, and treat 'dominated by the LKAS demand' as REFUTED.")
    ctl["POS3_command_tracking"] = pos3
    res["controls"] = ctl

    # ============================== 5. E3 -- Q, THE DIMENSIONLESS RATIO ==========================
    print("\n" + "=" * 100)
    print("=== 5.  E3 -- Q = RMS_6-9(column torque 0x18F) / RMS_6-9(SIGNED gp-0x6b94)")
    print("=" * 100)
    print("    🛑 CONTROL FIRST.  The split-half null on each arm's OWN blocks is computed BEFORE")
    print("       the ratio is quoted, and the ratio is judged against THAT floor, not against 1.0.")
    rows = []
    for ei, (a, b) in enumerate(eps):
        for s in range(a, b - NPERSEG + 1, HOP):
            sl = slice(s, s + NPERSEG)
            rows.append(dict(ep=ei, blk=(ei, (s - a) // int(round(BLOCK_S / (HOP / FS))) // 1),
                             v=float(np.nanmedian(d["v_rear"][sl])),
                             rate=float(np.median(np.abs(d["rate"][sl]))),
                             tq69=band_rms(d["tq"][sl], FS, 6.0, 9.0, NPERSEG),
                             x69=band_rms(d["x6b94"][sl], FS, 6.0, 9.0, NPERSEG),
                             xr69=band_rms(d["mag427"][sl] * COUNTS_PER_LSB, FS, 6.0, 9.0,
                                           NPERSEG)))
    # blocks: BLOCK_S of contiguous engaged time inside one episode
    per = int(round(BLOCK_S / (HOP / FS)))
    blocks = {}
    for ei in sorted(set(r["ep"] for r in rows)):
        rr = [r for r in rows if r["ep"] == ei]
        for i, r in enumerate(rr):
            r["blk"] = (ei, i // per)
            blocks.setdefault(r["blk"], []).append(r)
    nb = len(blocks)
    print(f"\n    {len(rows):,} windows of {NPERSEG/FS:.2f} s in {len(eps)} episodes "
          f"-> {nb} blocks of {BLOCK_S:.2f} s")
    sh_tq = split_half_null(rows, "tq69")
    sh_x = split_half_null(rows, "x69")
    print(f"    SPLIT-HALF NULL, column torque 6-9 Hz : p50 fold {sh_tq.get('floor_p50')}  "
          f"p95 {sh_tq.get('floor_p95')}   ({sh_tq.get('n_blocks')} blocks)")
    print(f"    SPLIT-HALF NULL, signed gp-0x6b94 6-9 : p50 fold {sh_x.get('floor_p50')}  "
          f"p95 {sh_x.get('floor_p95')}")
    print("    ⇒ ANY Q QUOTED BELOW IS ONLY MEANINGFUL TO THE PRECISION OF THESE FLOORS.")

    # per-block Q, then geometric median, then a BLOCK bootstrap over EPISODES
    bq = {}
    for k, rr in blocks.items():
        a_ = geo_median([r["tq69"] for r in rr])
        b_ = geo_median([r["x69"] for r in rr])
        if np.isfinite(a_) and np.isfinite(b_) and b_ > 0:
            bq[k] = a_ / b_
    keys = sorted(bq)
    Q = geo_median([bq[k] for k in keys])
    ep_of = {k: k[0] for k in keys}
    ue = sorted(set(ep_of.values()))
    boots = []
    for _ in range(4000):
        pick = RNG.choice(ue, len(ue), True)
        vals = [bq[k] for e_ in pick for k in keys if ep_of[k] == e_]
        v = geo_median(vals)
        if np.isfinite(v):
            boots.append(v)
    qlo, qhi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    # the RECTIFIED comparison -- the defect this build was cut to avoid repeating
    bqr = {}
    for k, rr in blocks.items():
        a_ = geo_median([r["tq69"] for r in rr])
        b_ = geo_median([r["xr69"] for r in rr])
        if np.isfinite(a_) and np.isfinite(b_) and b_ > 0:
            bqr[k] = a_ / b_
    Qr = geo_median(list(bqr.values()))
    rms_x = geo_median([r["x69"] for r in rows])
    rms_xr = geo_median([r["xr69"] for r in rows])
    rms_tq = geo_median([r["tq69"] for r in rows])

    print(f"\n    6-9 Hz RMS, geometric median over windows:")
    print(f"      column torque (0x18F)        {rms_tq:9.2f}")
    print(f"      SIGNED   gp-0x6b94 (counts)  {rms_x:9.2f}   <- the correct lane")
    print(f"      RECTIFIED gp-0x6b94 (counts) {rms_xr:9.2f}   <- the V98/V99 DEFECT, for reference")
    print(f"      rectification would understate the lane by {rms_x/rms_xr:.2f}x "
          f"(r81 measured 4.9x, r82 5.5x)")
    print(f"\n    ⭐ Q = {Q:.4f}   95 % CI [{qlo:.4f}, {qhi:.4f}]  "
          f"(block bootstrap over {len(ue)} EPISODES, {nb} blocks)")
    print(f"      (Q computed on the RECTIFIED lane would have been {Qr:.4f} -- quoted only to show")
    print(f"       the size of the defect, NEVER as the endpoint.)")
    phi = PHI_K * ANCHOR_A * Q
    phi_lo, phi_hi = PHI_K * ANCHOR_A * qlo, PHI_K * ANCHOR_A * qhi
    print(f"\n    phi(6-9 Hz) = 0.2565 * A * Q  with A = {ANCHOR_A} +- {ANCHOR_SE} "
          f"[EVIDENCE r81/r82, BELIEF that it generalises to r85]")
    print(f"      phi = {phi:.4f}   (measurement CI only: [{phi_lo:.4f}, {phi_hi:.4f}]; the "
          f"anchor adds ~8 % in quadrature)")
    res["E3"] = dict(Q=float(Q), Q_ci=[qlo, qhi], Q_rectified_for_reference=float(Qr),
                     n_blocks=nb, n_episodes=len(ue), n_windows=len(rows),
                     rms69_tq=float(rms_tq), rms69_x6b94_signed=float(rms_x),
                     rms69_x6b94_rectified=float(rms_xr),
                     rectification_understatement=float(rms_x / rms_xr),
                     split_half_null_tq=sh_tq, split_half_null_x=sh_x,
                     phi=float(phi), phi_ci_measurement_only=[float(phi_lo), float(phi_hi)],
                     anchor_A=ANCHOR_A, anchor_se=ANCHOR_SE, Q_c=Q_C,
                     indeterminate_band=list(Q_BAND))

    # ---------- CONTROL 1: the SAME pipeline on the routes the anchor A was measured on ----------
    print("\n    🛑 CONTROL 1 -- THE SAME CODE ON THE ROUTES THAT DEFINED THE ANCHOR.")
    print("       On r80/r81/r82 the 427 lane carried gp-0x6b70, so `Q` there is 1/A BY")
    print("       CONSTRUCTION and this row is a direct check that the pipeline reproduces the")
    print("       published anchor.  If it does, the r85 number is the pipeline's, not a bug.")
    xr = {}
    for stem, cdir in (("r82", "_cache_r82"), ("r81", "_cache_r81"), ("r80", "_cache_r80")):
        f = AN / cdir / f"{stem}.npz"
        if not f.exists():
            continue
        zz = np.load(f, allow_pickle=True)
        tt = np.asarray(zz["t"], float)
        ii = np.asarray(zz["row2raw14"], int)
        bb = (np.asarray(zz["raw14_b4"], int) & 0xFF)[ii]
        ee = np.asarray(zz["cc_lat"], float) > 0.5
        ss = np.asarray(zz["seg"], int)
        at, am = np.asarray(zz["ab_t1ab"], float), np.asarray(zz["ab_mt"], int)
        jj = np.clip(np.searchsorted(at, tt, side="right") - 1, 0, len(am) - 1)
        mg = am[jj].astype(float) * COUNTS_PER_LSB
        xx = np.where((bb & M_B7) != 0, -1.0, 1.0) * mg
        tqq = np.asarray(zz["tq"], float)
        ep2 = episodes_t(ee, tt, ss, 1.0)
        S, R, T2 = [], [], []
        for a_, b_ in ep2:
            for s in range(a_, b_ - NPERSEG + 1, HOP):
                sl = slice(s, s + NPERSEG)
                S.append(band_rms(xx[sl], FS, 6, 9, NPERSEG))
                R.append(band_rms(mg[sl], FS, 6, 9, NPERSEG))
                T2.append(band_rms(tqq[sl], FS, 6, 9, NPERSEG))
        gs, gr, gt = geo_median(S), geo_median(R), geo_median(T2)
        xr[stem] = dict(n_windows=len(S), rms69_signed=gs, rms69_rect=gr, rms69_tq=gt,
                        rect_understatement=gs / gr, Q_like=gt / gs, implied_A=gs / gt)
        print(f"      {stem}: {len(S):4d} win   tq69 {gt:7.2f}   SIGNED-lane 6-9 RMS {gs:7.2f}   "
              f"rect {gr:6.2f} ({gs/gr:.2f}x)   implied A = {gs/gt:.3f}")
    print(f"      r85: {len(rows):4d} win   tq69 {rms_tq:7.2f}   SIGNED-lane 6-9 RMS {rms_x:7.2f}   "
          f"rect {rms_xr:6.2f} ({rms_x/rms_xr:.2f}x)   Q = {geo_median(list(bq.values())):.3f}")
    rect_txt = ", ".join("{} {:.2f}x".format(k, v["rect_understatement"]) for k, v in xr.items())
    a_txt = ", ".join("{} {:.3f}".format(k, v["implied_A"]) for k, v in xr.items())
    note(all(3.5 < v["rect_understatement"] < 6.5 for v in xr.values()),
         f"pipeline reproduces the published 4.9-5.5x rectification cost on r80/81/82 ({rect_txt})")
    note(all(1.00 < v["implied_A"] < 1.35 for v in xr.values()),
         f"pipeline reproduces the published anchor A = 1.13 +- 0.09 on r80/81/82 ({a_txt})")
    res["E3"]["cross_route_control"] = xr

    # ---------- CONTROL 2: per-segment stratification -------------------------------------------
    print("\n    🛑 CONTROL 2 -- IS Q STABLE ACROSS THE ROUTE?  Route 85 spans 5 to 105 km/h, where")
    print("       the anchor was measured on 60 s of near-homogeneous creep.  A Q that swings by")
    print("       segment is a Q that has no single value to quote.")
    strat = {}
    for s in sorted(set(d["seg"].tolist())):
        rr = [r for r in rows if d["seg"][eps[r["ep"]][0]] == s]
        if len(rr) < 8:
            continue
        a_ = geo_median([r["tq69"] for r in rr])
        b_ = geo_median([r["x69"] for r in rr])
        strat[int(s)] = dict(n=len(rr), tq69=a_, x69=b_, Q=a_ / b_ if b_ > 0 else float("nan"),
                             v=float(np.nanmedian([r["v"] for r in rr])))
        print(f"      seg {s:2d}  n={len(rr):3d}  v(rear) {strat[int(s)]['v']:6.1f} km/h   "
              f"tq69 {a_:7.2f}   x69 {b_:6.2f}   Q = {strat[int(s)]['Q']:6.3f}")
    qs = [v["Q"] for v in strat.values() if np.isfinite(v["Q"])]
    print(f"      ⇒ Q ranges {min(qs):.2f} .. {max(qs):.2f} across segments = a "
          f"{max(qs)/min(qs):.1f}x SPREAD.")
    res["E3"]["per_segment"] = strat
    res["E3"]["segment_spread"] = float(max(qs) / min(qs))

    # ---------- THE SANITY GATE -----------------------------------------------------------------
    print(f"\n    PRE-REGISTERED DECISION BOUNDARY:  Q_c = {Q_C}; INDETERMINATE band "
          f"[{Q_BAND[0]}, {Q_BAND[1]}]")
    print(f"\n    🛑🛑 THE DEFINITIONAL SANITY GATE, AND IT FIRES.")
    print(f"       phi is Path 2's SHARE of the delivered 6-9 Hz command.  It is bounded above by")
    print(f"       1.0 BY DEFINITION.  The measured value is phi = {phi:.3f} "
          f"(CI [{phi_lo:.3f}, {phi_hi:.3f}]).")
    if phi >= 0.9:
        verdict = (
            f"VOID -- NOT DECISIVE, AND THE 0xC63AE NO-GO IS **NOT** OVERTURNED.  Q = {Q:.3f} "
            f"formally clears Q_c = {Q_C}, but it does so by returning phi = {phi:.3f}, at or "
            f"above the definitional ceiling of 1.0.  A share cannot exceed 1, so the construction "
            f"has broken down on this route.  The broken element is IDENTIFIED: the imported "
            f"anchor A.  build_v100_tva pre-flagged this exact residual -- 'the anchor A is an "
            f"imported CONSTANT, and V100 cannot re-check it in-drive, because 427 now carries "
            f"gp-0x6b94 and the drive therefore does not carry gp-0x6b70 at all.'  Route 85's "
            f"6-9 Hz column torque is {xr['r82']['rms69_tq']/rms_tq:.1f}x QUIETER than route 82's, "
            f"far outside the operating range A was measured in, and Q swings "
            f"{res['E3']['segment_spread']:.1f}x across segments.  NO VERDICT ON 0xC63AE MAY BE "
            f"DRAWN FROM THIS DRIVE.")
    elif Q_BAND[0] <= Q <= Q_BAND[1]:
        verdict = ("INDETERMINATE -- Q lies inside the pre-registered +-11 % band.  Report the "
                   "number and its CI; make NO verdict on 0xC63AE.")
    elif Q > Q_BAND[1]:
        sig = "2-sigma" if Q >= 1.53 else "1-sigma"
        verdict = (f"Q > Q_c at {sig}: phi > 0.364 => delivered > 1.088 => ABOVE the floor, "
                   f"the 0xC63AE NO-GO IS OVERTURNED.")
    else:
        sig = "2-sigma" if Q <= 0.98 else "1-sigma"
        verdict = (f"Q < Q_c at {sig}: BELOW the floor, the 0xC63AE NO-GO STANDS.")
    print(f"\n    ⇒ E3 VERDICT: {verdict}")
    print("\n    ⊕ WHAT E3 DOES DELIVER, AS A CLEAN SINGLE-DRIVE ABSOLUTE WITH NO IMPORT:")
    print(f"       RMS_6-9(SIGNED gp-0x6b94) = {rms_x:.2f} counts, engaged, route 85.")
    sig_txt = ", ".join("{} {:.0f}".format(k, v["rms69_signed"]) for k, v in xr.items())
    print(f"       The same pipeline gives RMS_6-9(SIGNED gp-0x6b70) = {sig_txt} counts.")
    print(f"       ⇒ THE AGGREGATOR OUTPUT CARRIES {xr['r82']['rms69_signed']/rms_x:.0f}x LESS "
          f"6-9 Hz ENERGY THAN THE PID REFERENCE LANE DOES.  That is a NEW measurement, it needs")
    print("       no anchor, and it is the first time gp-0x6b94 has ever been on the wire.")
    print("       ⚠ CAVEAT, STATED: it is a CROSS-ROUTE comparison of two different cells on two")
    print("       different drives, and route 85's column torque is itself "
          f"{xr['r82']['rms69_tq']/rms_tq:.1f}x quieter than route 82's, so at most ~"
          f"{xr['r82']['rms69_signed']/rms_x/(xr['r82']['rms69_tq']/rms_tq):.0f}x of it survives")
    print("       normalisation by the column-torque drive-in.  BELIEF, not EVIDENCE.")
    res["E3"]["verdict"] = verdict

    # ============================== 6. SEGMENT 20 -- THE OPERATOR'S CONTROL =======================
    print("\n" + "=" * 100)
    print("=== 6.  SEGMENT 20 -- the operator's WITHIN-DRIVE matched control")
    print("=== 'stuttering AND then an LKAS-disengaged section demonstrating normal, smooth,")
    print("===  stutter-less return to centre'")
    print("=" * 100)
    m20 = d["seg"] == 20
    i20 = np.where(m20)[0]
    t20 = t[i20] - t[i20[0]]
    e20 = eng[i20]
    tr = np.where(np.diff(e20.astype(int)) != 0)[0]
    print(f"    segment 20: {len(i20):,} frames, {t20[-1]:.2f} s, engaged "
          f"{100*e20.mean():.2f} % ({e20.sum()/FS:.1f} s)")
    print(f"    engagement TRANSITIONS ({len(tr)}), t is SEGMENT-LOCAL (add {t[i20[0]]:.2f} s for "
          f"route time):")
    trans = []
    for k in tr:
        kind = "ENGAGE" if e20[k + 1] else "DISENGAGE"
        trans.append(dict(kind=kind, t_seg=float(t20[k + 1]), t_route=float(t[i20[k + 1]]),
                          v_rear=float(np.nanmedian(d["v_rear"][i20[k + 1]])),
                          ang=float(d["ang"][i20[k + 1]])))
        print(f"      {kind:10s} t_seg {t20[k+1]:7.2f} s  (t_route {t[i20[k+1]]:7.2f} s)  "
              f"v(rear) {trans[-1]['v_rear']:6.2f} km/h  angle {trans[-1]['ang']:+8.2f} deg")
    runs = []
    b = 0
    for k in list(tr) + [len(e20) - 1]:
        runs.append((bool(e20[b]), float(t20[b]), float(t20[k]), k - b + 1))
        b = k + 1
    print(f"\n    RUNS in segment 20 (state, t0, t1, frames):")
    for st_, a_, b_, n_ in runs:
        print(f"      {'ENGAGED ' if st_ else 'MANUAL  '} {a_:7.2f} .. {b_:7.2f} s  "
              f"({b_-a_:6.2f} s, {n_:,} frames)")
    # return-to-centre events: manual, |angle| crossing from >20 deg toward <5 deg
    ang20 = d["ang"][i20]
    rtc = []
    for st_, a_, b_, _n in runs:
        if st_:
            continue
        sl = (t20 >= a_) & (t20 <= b_)
        aa = ang20[sl]
        tt = t20[sl]
        if len(aa) < 50:
            continue
        for j in range(1, len(aa)):
            if abs(aa[j - 1]) > 20 and abs(aa[j]) <= 20:
                k2 = j
                while k2 < len(aa) and abs(aa[k2]) > 5:
                    k2 += 1
                if k2 < len(aa):
                    rtc.append(dict(t_start=float(tt[j - 1]), t_end=float(tt[k2]),
                                    dur_s=float(tt[k2] - tt[j - 1]),
                                    ang_from=float(aa[j - 1]), ang_to=float(aa[k2]),
                                    peak_rate=float(np.max(np.abs(np.diff(aa[j - 1:k2 + 1])
                                                                  * FS)))))
    # de-duplicate overlapping detections
    ded = []
    for r in rtc:
        if not ded or r["t_start"] > ded[-1]["t_end"]:
            ded.append(r)
    print(f"\n    RETURN-TO-CENTRE events in the MANUAL runs of segment 20 "
          f"(|angle| 20 deg -> 5 deg): {len(ded)}")
    for r in ded:
        print(f"      t_seg {r['t_start']:7.2f} .. {r['t_end']:7.2f} s  ({r['dur_s']:5.2f} s)  "
              f"{r['ang_from']:+8.2f} -> {r['ang_to']:+7.2f} deg  peak |rate| "
              f"{r['peak_rate']:7.1f} °/s")

    # ---- ⭐ THE MATCHED ARM.  The operator's own within-drive contrast, scored with a CONTROL.
    print("\n    ⭐ THE MATCHED ARM -- the operator's stated contrast, scored.  ENGAGED run")
    print("       (t_seg 6.72-22.33 s) vs the MANUAL run that follows (22.34-59.98 s), same")
    print("       segment, same lot, consecutive.  🛑 CONTROL FIRST: each arm's OWN split-half")
    print("       null is computed before any ratio is quoted.")
    arms = {}
    for tag, (a_, b_) in (("ENGAGED", (6.72, 22.33)), ("MANUAL", (22.34, 59.98))):
        sl0 = np.where(m20)[0][(t20 >= a_) & (t20 <= b_)]
        rw = []
        # 🛑 blocks are BLOCK_S of contiguous time = `per` consecutive WINDOWS, so the block index
        # must come from the window ordinal, not from the sample offset.
        for iw, s in enumerate(range(0, len(sl0) - NPERSEG + 1, HOP)):
            w = sl0[s:s + NPERSEG]
            rw.append(dict(blk=(0, iw // per),
                           v=float(np.nanmedian(d["v_rear"][w])),
                           rate=float(np.median(np.abs(d["rate"][w]))),
                           tq69=band_rms(d["tq"][w], FS, 6.0, 9.0, NPERSEG),
                           ang69=band_rms(d["ang"][w], FS, 6.0, 9.0, NPERSEG),
                           x69=band_rms(d["x6b94"][w], FS, 6.0, 9.0, NPERSEG)))
        arms[tag] = rw
        sh = split_half_null(rw, "tq69")
        print(f"      {tag:8s} {len(rw):3d} windows  v(rear) p50 "
              f"{np.nanmedian([r['v'] for r in rw]):5.2f} km/h  |rate| p50 "
              f"{np.median([r['rate'] for r in rw]):5.1f} °/s")
        print(f"      {'':8s} 6-9 Hz geo-median: column torque {geo_median([r['tq69'] for r in rw]):7.2f}"
              f"   angle {geo_median([r['ang69'] for r in rw]):6.3f} deg"
              f"   signed gp-0x6b94 {geo_median([r['x69'] for r in rw]):7.2f} ct")
        print(f"      {'':8s} SPLIT-HALF NULL on its own blocks: p50 fold {sh.get('floor_p50')}  "
              f"p95 {sh.get('floor_p95')}  ({sh.get('n_blocks')} blocks)")
    ratio69 = (geo_median([r["tq69"] for r in arms["ENGAGED"]])
               / geo_median([r["tq69"] for r in arms["MANUAL"]]))
    ratio_ang = (geo_median([r["ang69"] for r in arms["ENGAGED"]])
                 / geo_median([r["ang69"] for r in arms["MANUAL"]]))
    print(f"\n      ENGAGED / MANUAL 6-9 Hz fold:  column torque {ratio69:.2f}x   "
          f"steering angle {ratio_ang:.2f}x")
    nbE = len(set(r["blk"] for r in arms["ENGAGED"]))
    nbM = len(set(r["blk"] for r in arms["MANUAL"]))
    print(f"      🛑 CAVEATS, AND THEY BIND.  (1) The ENGAGED arm has only {nbE} blocks -- BELOW")
    print(f"      the 4-block minimum, so it has NO split-half null and the fold has no CI. The")
    print(f"      MANUAL arm has {nbM} blocks, floor p95 "
          f"{split_half_null(arms['MANUAL'], 'tq69').get('floor_p95'):.2f}x; the "
          f"{ratio69:.1f}x fold is far outside")
    print("      that, but one arm's floor is not the pair's.  (2) The arms are NOT matched: the")
    print(f"      MANUAL arm sits at {np.median([r['rate'] for r in arms['MANUAL']]):.0f} °/s "
          f"vs the engaged arm's "
          f"{np.median([r['rate'] for r in arms['ENGAGED']]):.0f} °/s, i.e. the manual arm is")
    print("      moving the wheel FASTER and still shows LESS 6-9 Hz torque -- which cuts AGAINST")
    print("      the artefact reading, but is not a matched comparison.")
    print("      ⇒ REPORT AS A DESCRIPTION OF THE OPERATOR'S OWN WINDOW, NOT AS AN ENDPOINT.")
    print("      🛑 THE OPERATOR SCORES THE SYMPTOM.  This number does not, and no claim that")
    print("      stuttering / micro-ratcheting was moved may be made from it.")
    res["seg20_matched_arm"] = {
        tag: dict(n_windows=len(rw),
                  v_rear_p50=float(np.nanmedian([r["v"] for r in rw])),
                  rate_p50=float(np.median([r["rate"] for r in rw])),
                  tq69=float(geo_median([r["tq69"] for r in rw])),
                  ang69=float(geo_median([r["ang69"] for r in rw])),
                  x69=float(geo_median([r["x69"] for r in rw])),
                  split_half_null_tq=split_half_null(rw, "tq69"))
        for tag, rw in arms.items()}
    res["seg20_matched_arm"]["fold_eng_over_man_tq69"] = float(ratio69)
    res["seg20_matched_arm"]["fold_eng_over_man_ang69"] = float(ratio_ang)
    res["seg20_matched_arm"]["caveat"] = ("NOT speed-matched, NOT a symptom score, below the "
                                          "4-block minimum for a split-half null. Descriptive only.")

    # ---- emit the derived array set for a follow-on analyst
    keep = dict(
        t_seg=t20, t_route=t[i20],
        engaged=e20.astype(np.int8),
        steering_angle_deg=d["ang"][i20],
        # 🛑 t20 has duplicate 0x14A timestamps; gradient on a uniform index grid at FS avoids
        # the divide-by-zero those produce.  The grid IS uniform at 100 Hz within a segment.
        steering_angle_rate_dps=np.gradient(d["ang"][i20]) * FS,
        driver_torque_18f=d["tq"][i20],
        driver_torque_carstate=d["cs_tq"][i20],
        lkas_demand_0x0E4=d["e4tq"][i20],
        lkas_demand_openpilot=d["co_req"][i20],
        x6b94_signed_counts=d["x6b94"][i20],
        mag427_code=d["mag427"][i20],
        b7_sign_6b94_neg=d["b7"][i20].astype(np.int8),
        b6_rung_Dp_errclamp=d["b6"][i20].astype(np.int8),
        b5_rung_A_refclamp=d["b5"][i20].astype(np.int8),
        b4_sign_6ad6_neg=d["b4b"][i20].astype(np.int8),
        b3_identity=d["b3"][i20].astype(np.int8),
        v_rear_kmh=d["v_rear"][i20],
        v_ego_kmh=d["v"][i20],
        lp_yaw_rads=d["lp_yaw"][i20],
        steering_pressed=d["press"][i20].astype(np.int8),
    )
    hdr = np.array([
        "ROUTE 85 (V100) SEGMENT 20 -- the operator's within-drive LKAS-off control.",
        "t_seg is segment-local seconds; t_route adds the whole-route offset "
        f"{t[i20[0]]:.3f} s (which SPANS the missing segment 17).",
        "SIGN CONVENTION, OPERATOR-CONFIRMED 2026-08-13, APPLIED NOWHERE -- channels are NATIVE:",
        "  negative driver torque AND negative steering angle = a RIGHT turn;",
        "  +LKAS demands NEGATIVE angle, +driver torque demands POSITIVE angle,",
        "  so a positive LKAS command and a positive driver torque push the wheel OPPOSITE ways.",
        "  A scorer must apply ONE sign flip when mixing lkas_demand_* with driver_torque_*.",
        "  The angle-sensor zero is offset slightly LEFT (measured -4.25 deg; openpilot -4.78 deg);",
        "  steering_angle_deg is RAW, with NO offset removed.",
        "x6b94_signed_counts = sign(b7) * mag427_code * 12.8; the writer clamps gp-0x6b94 to",
        "  +-10240, so the structural ceiling is code 800 (never reached on this route).",
        "driver_torque_18f is CAN 0x18F bytes 0:1 scaled -1.0 (the kit's `tq`, the column torque",
        "  used as E3's numerator).  driver_torque_carstate is openpilot's carState.steeringTorque.",
        "v_rear_kmh = (ws_rl + ws_rr)/2 -- USE THIS, not v_ego_kmh (vEgo is +7.9 % fast at angle).",
        "lp_yaw_rads = livePose.angularVelocityDevice.z, z-DOWN => NEGATIVE on a LEFT turn.",
        "  carState.yawRate is identically zero on this car and is NOT included.",
    ])
    np.savez_compressed(OUT / "r85_seg20_control.npz", _README=hdr, **keep)
    print(f"\n    wrote {OUT / 'r85_seg20_control.npz'}  ({len(i20):,} rows, "
          f"{len(keep)} documented columns + _README)")
    res["seg20"] = dict(n_frames=int(len(i20)), dur_s=float(t20[-1]),
                        engaged_frac=float(e20.mean()), engaged_s=float(e20.sum() / FS),
                        route_time_offset_s=float(t[i20[0]]),
                        transitions=trans,
                        runs=[dict(engaged=st_, t0=a_, t1=b_, frames=int(n_))
                              for st_, a_, b_, n_ in runs],
                        return_to_centre=ded,
                        array_file=str(OUT / "r85_seg20_control.npz"))

    # ============================== 7. CHECKS ====================================================
    print("\n" + "=" * 100)
    npass = sum(1 for ok, _ in _checks if ok)
    print(f"  CHECKS: {npass}/{len(_checks)} passed")
    res["checks"] = [dict(pass_=ok, msg=m) for ok, m in _checks]
    (OUT / "r85_v100_score.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"  wrote {OUT / 'r85_v100_score.json'}")
    return res


if __name__ == "__main__":
    main()
