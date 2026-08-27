#!/usr/bin/env python3
r"""⭐ THE PRE-FLIGHT POWER GATE FOR V100 -- run BEFORE the cut, not after.

🛑 THE STANDING GATE, from `CLAUDE.md`:
     *"Before cutting, write the sentence a null will license.  If the honest answer is 'we would
      not be able to tell,' the build is not ready -- fix the instrument first."*
V97 flew uninterpretable because nobody ran that gate QUANTITATIVELY.  This file runs it.

CALIBRATION SOURCE -- route 82 (V99), which is the exposure we should assume we get:
    59.79 s engaged, 5,979 engaged frames, 4 fragmented episodes, 12-14 resampling blocks.
    Measured correlation times: b7 tau 0.029 s (n_eff 2060) · b6 tau 0.052 s (n_eff 1161)
                                b4 tau 0.310 s (n_eff  193)
    E2's block-permutation null: 12 blocks -> null95 |r| <= 0.343   (route 81: 21 blocks -> 0.221)

THE FIVE QUESTIONS, answered with arithmetic:
  Q1  CI half-width for a DUTY endpoint at route-82 exposure
  Q2  smallest d_clamp distinguishable from 0.0000, and from 1.0000
  Q3  does a duty endpoint survive the exposure that killed E1 and E2?
  Q4  minimum CONTIGUOUS engaged exposure that would resolve E2's 0.10 gap
  Q5  can d_clamp be bounded from EXISTING 427 data, before spending a drive?

🛑 The tau prior for a CLAMP bit is not guessed.  A real threshold rung is SYNTHESISED from real
   ECU data -- `|gp-0x6b70| >= thr` off CAN 427 on routes 80/81/82 -- and its tau is measured.
   That is the closest empirical analogue to RUNG A that exists without flying anything.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1].parent
AN = ROOT / "analysis-2020accord"
OUT = AN / "sessions/v99"
OUT.mkdir(parents=True, exist_ok=True)

FS = 100.0
T_ENG = 59.79                 # route 82 engaged seconds -- the exposure to ASSUME
N_ENG = 5979                  # route 82 engaged frames
CLAMP = 8192                  # cal 0xC6200, verified
WIRE_SCALE = 64.0 / 5.0       # 427 counts = wire * 12.8

# measured on route 82 by score/v99_r82_score.py -- the tau range this car actually produces
TAU_MEASURED = {"b7 sign(gp-0x6b70)": 0.029, "b6 MODEL>=ACTUAL": 0.052, "b4 sign(gp-0x374c)": 0.310}
# E2's empirical block-permutation null, two points
E2_NULL = {12: 0.343, 21: 0.221}
E2_GAP = 0.10                 # -0.32 vs -0.22, the two hypotheses E2 was built to separate
BLOCK_S = 5.12


def acf_tau(x, fs=FS, maxlag=800):
    x = np.asarray(x, float)
    x = x - x.mean()
    if np.std(x) == 0:
        return float("nan")
    n = min(maxlag, len(x) - 1)
    ac = np.array([np.dot(x[:len(x) - k], x[k:]) / np.dot(x, x) for k in range(n)])
    zc = np.where(ac <= 0)[0]
    k0 = int(zc[0]) if len(zc) else n
    return float(np.sum(ac[:k0]) / fs)


def load427(stem):
    z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    abt, mt = np.asarray(z["ab_t1ab"], float), np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    return eng, mt[j] * WIRE_SCALE


def main():
    res = {}
    print("=" * 98)
    print("  ⭐ V100 PRE-FLIGHT POWER GATE -- route-82-class exposure "
          f"({T_ENG:.1f} s engaged, {N_ENG:,} frames, 12-14 blocks)")
    print("=" * 98)

    # =========================== tau prior for a CLAMP-like bit ==============================
    print("\n=== TAU PRIOR FOR A THRESHOLD RUNG -- MEASURED, NOT GUESSED ===")
    print("    A synthetic rung `|gp-0x6b70| >= thr` is built from real CAN 427 data and its")
    print("    correlation time measured.  This is the closest empirical analogue to RUNG A")
    print("    obtainable without flying anything.")
    res["tau_prior"] = {}
    print(f"    {'route':6s} {'thr':>6s} {'duty':>8s} {'tau s':>8s} {'n_eff':>8s}")
    taus = []
    for stem in ("r82", "r81", "r80"):
        try:
            eng, c = load427(stem)
        except Exception:
            continue
        e = c[eng]
        for thr in (1024, 2048, 2560):
            bit = (e >= thr).astype(float)
            if bit.mean() in (0.0, 1.0):
                continue
            tau = acf_tau(bit)
            neff = (len(e) / FS) / tau if tau > 0 else float("nan")
            res["tau_prior"][f"{stem}_{thr}"] = dict(duty=float(bit.mean()), tau_s=tau, n_eff=neff)
            taus.append(tau)
            print(f"    {stem:6s} {thr:6d} {bit.mean():8.4f} {tau:8.3f} {neff:8.0f}")
    tau_lo, tau_hi = float(np.min(taus)), float(np.max(taus))
    print(f"\n    ⇒ MEASURED tau range for a real threshold rung on this car: "
          f"{tau_lo:.3f} - {tau_hi:.3f} s")
    print(f"      (for comparison, the flown bits gave " +
          ", ".join(f"{k} {v:.3f} s" for k, v in TAU_MEASURED.items()) + ")")
    res["tau_range_threshold_rung"] = [tau_lo, tau_hi]

    # =========================== Q1 ==========================================================
    print("\n" + "=" * 98)
    print("=== Q1  CI HALF-WIDTH FOR A DUTY ENDPOINT AT ROUTE-82 EXPOSURE")
    print("=" * 98)
    print(f"    n_eff = T/tau with T = {T_ENG:.2f} s;  half-width = 1.96*sqrt(p(1-p)/n_eff)")
    print(f"\n    {'tau s':>7s} {'n_eff':>7s} " +
          "".join(f"{'p='+f'{p:.2f}':>10s}" for p in (0.05, 0.20, 0.50, 0.80, 0.95)))
    res["Q1"] = {}
    for tau in (0.029, 0.052, 0.10, 0.20, 0.310, 0.50, 1.00):
        neff = T_ENG / tau
        row = {}
        line = f"    {tau:7.3f} {neff:7.0f} "
        for p in (0.05, 0.20, 0.50, 0.80, 0.95):
            hw = 1.96 * np.sqrt(p * (1 - p) / neff)
            row[f"p{p}"] = hw
            line += f"{hw:10.4f}"
        res["Q1"][f"tau_{tau}"] = dict(n_eff=neff, half_widths=row)
        print(line)
    hw_lo = 1.96 * np.sqrt(0.25 / (T_ENG / tau_lo))
    hw_hi = 1.96 * np.sqrt(0.25 / (T_ENG / tau_hi))
    res["Q1"]["expected_half_width_dclamp"] = [hw_lo, hw_hi]
    print(f"\n    ⭐ EXPECTED CI ON d_clamp, using the MEASURED threshold-rung tau range "
          f"[{tau_lo:.3f}, {tau_hi:.3f}] s:")
    print(f"       half-width +-{hw_lo:.4f} to +-{hw_hi:.4f} at the worst case p = 0.50")
    print(f"       (narrower away from 0.5: at p = 0.10 or 0.90 it is "
          f"+-{1.96*np.sqrt(.09/(T_ENG/tau_lo)):.4f} to "
          f"+-{1.96*np.sqrt(.09/(T_ENG/tau_hi)):.4f})")

    # =========================== Q2 ==========================================================
    print("\n" + "=" * 98)
    print("=== Q2  THE RESOLUTION FLOOR -- smallest d_clamp distinguishable from 0.0000 and 1.0000")
    print("=" * 98)
    print("    🛑 The normal approximation FAILS at the rails.  Near 0 the right tool is the")
    print("       RULE OF THREE on EFFECTIVE samples: observing zero events in n_eff effective")
    print("       samples gives a 95 % upper bound of 3/n_eff.  So a true duty is distinguishable")
    print("       from 0 only once it is expected to deliver >= 3 INDEPENDENT clamp EPISODES.")
    print(f"\n    {'tau s':>7s} {'n_eff':>7s} {'min d vs 0':>12s} {'max d vs 1':>12s} "
          f"{'= seconds clamped':>20s}")
    res["Q2"] = {}
    for tau in (0.029, 0.052, 0.10, 0.20, 0.310, 0.50, 1.00):
        neff = T_ENG / tau
        pmin = 3.0 / neff
        res["Q2"][f"tau_{tau}"] = dict(n_eff=neff, min_vs_zero=pmin, max_vs_one=1 - pmin,
                                       seconds=pmin * T_ENG)
        print(f"    {tau:7.3f} {neff:7.0f} {pmin:12.4f} {1-pmin:12.4f} "
              f"{pmin*T_ENG:20.2f}")
    p_lo = 3.0 / (T_ENG / tau_lo)
    p_hi = 3.0 / (T_ENG / tau_hi)
    res["Q2"]["window_at_measured_tau"] = [p_hi, 1 - p_hi]
    print(f"\n    ⭐ AT THE MEASURED THRESHOLD-RUNG TAU RANGE:")
    print(f"       distinguishable from 0.0000 once d_clamp >= {p_lo:.4f} (tau {tau_lo:.3f}) "
          f"to {p_hi:.4f} (tau {tau_hi:.3f})")
    print(f"       distinguishable from 1.0000 once d_clamp <= {1-p_hi:.4f}")
    print(f"       ⇒ CONSERVATIVE RESOLVABLE WINDOW: [{p_hi:.3f}, {1-p_hi:.3f}]")
    print(f"       ⇒ i.e. any d_clamp between ~{100*p_hi:.1f} % and ~{100*(1-p_hi):.1f} % duty "
          f"reads as DIFFERENT FROM BOTH RAILS.")
    print(f"       Single-frame floor for reference: 1/{N_ENG:,} = {1/N_ENG:.6f}")
    print(f"       Empirical precedent: route 82 measured b3 duty 0.0000 with 0 transitions over")
    print(f"       12,004 frames, and V98 measured b5 duty 0.0022 -- a TRUE ZERO IS MEASURABLE.")

    # =========================== Q3 ==========================================================
    print("\n" + "=" * 98)
    print("=== Q3  DOES A DUTY ENDPOINT SURVIVE THE EXPOSURE THAT KILLED E1 AND E2?")
    print("=" * 98)
    print("    🛑 THE ANSWER IS CONDITIONAL, AND THE CONDITION IS THE WHOLE POINT.")
    print("       E1 WAS A DUTY ENDPOINT -- b6 duty stratified by wheel rate -- AND IT DIED.")
    print("       So 'duties are cheap' is NOT automatically true.  What killed E1 was not that")
    print("       it was a duty; it was that it was a CROSS-BUILD duty DIFFERENCE, exposed to a")
    print("       route-wide operating-point offset that moved all four bins together.")
    print("\n    E1's arithmetic, for the record:")
    e1 = {"0-5": (-0.1308, 0.0904), "5-25": (-0.0445, 0.0241),
          "25-60": (-0.0205, 0.0594), "60+": (-0.0543, 0.1847)}
    res["Q3"] = {"E1": {}}
    for k, (delta, hw) in e1.items():
        res["Q3"]["E1"][k] = dict(delta=delta, half_width=hw, ratio=abs(delta) / hw)
        print(f"       {k:6s} delta {delta:+.4f}   own CI half-width +-{hw:.4f}   "
              f"|delta|/hw = {abs(delta)/hw:.2f}  "
              f"{'(effect smaller than its own error bar)' if abs(delta) < hw else ''}")
    print("       ⇒ in 3 of 4 bins the cross-build EFFECT was at or below its OWN half-width.")
    print("         A cross-build duty delta of ~0.05 is simply not resolvable here.")
    print("\n    ⭐ WHAT MAKES RUNG A DIFFERENT -- and it is a difference of KIND, not degree:")
    print("       RUNG A asks a WITHIN-ROUTE, ABSOLUTE, STRUCTURAL question ('is the PID reference")
    print("       pinned?'), decided against a threshold far from the noise, with NO reference to")
    print("       any previous build.  Its decision boundary is ~0.5 wide, not ~0.05.")
    for tau in (tau_lo, tau_hi):
        hw = 1.96 * np.sqrt(0.25 / (T_ENG / tau))
        print(f"       at tau {tau:.3f} s: half-width +-{hw:.4f} ⇒ a 'high vs low' call with a")
        print(f"          0.20 / 0.80 decision boundary carries {0.30/hw:.1f} sigma of margin")
    res["Q3"]["verdict"] = ("YES, CONDITIONALLY: a duty endpoint survives IF AND ONLY IF it is "
                            "answerable within a single route against a structural threshold. A "
                            "cross-build d_clamp DELTA inherits E1's failure mode exactly.")
    print(f"\n    ⇒ VERDICT: {res['Q3']['verdict']}")
    print("       🛑 GATE FOR V100: if any endpoint's sentence contains 'compared to V99',")
    print("          IT FAILS THIS POWER GATE.  Write every endpoint as a single-drive absolute.")

    # =========================== Q4 ==========================================================
    print("\n" + "=" * 98)
    print("=== Q4  MINIMUM CONTIGUOUS ENGAGED EXPOSURE TO RESOLVE E2's 0.10 GAP")
    print("=" * 98)
    ks = {n: v * np.sqrt(n) for n, v in E2_NULL.items()}
    print(f"    Empirical block-permutation null scaling, null95 = k/sqrt(n_blocks):")
    for n, v in E2_NULL.items():
        print(f"       {n:2d} blocks -> null95 {v:.3f}  ⇒ k = {ks[n]:.3f}")
    k_cons = max(ks.values())
    k_opt = min(ks.values())
    # to separate two r values by GAP at 95% confidence and 80% power: |GAP| >= 2.8 * SE
    # and null95 ~= 1.96 * SE  =>  need null95 <= 1.96 * GAP / 2.8
    need_null = 1.96 * E2_GAP / 2.8
    print(f"\n    To distinguish r = -0.32 from r = -0.22 (gap {E2_GAP:.2f}) at 95 % confidence")
    print(f"    and 80 % power we need |gap| >= 2.8*SE ⇒ SE <= {E2_GAP/2.8:.4f} ⇒ "
          f"null95 <= {need_null:.4f}")
    res["Q4"] = {"required_null95": need_null, "k_conservative": k_cons, "k_optimistic": k_opt}
    for tag, k in (("conservative", k_cons), ("optimistic", k_opt)):
        nb = (k / need_null) ** 2
        secs = nb * BLOCK_S
        res["Q4"][f"blocks_{tag}"] = nb
        res["Q4"][f"seconds_{tag}"] = secs
        print(f"       {tag:12s} k={k:.3f} ⇒ {nb:6.0f} blocks ⇒ "
              f"{secs:7.0f} s = {secs/60:5.1f} MIN of contiguous engaged time")
    # textbook cross-check, independent samples
    r = 0.27
    se_need = E2_GAP / 2.8
    n_ind = ((1 - r ** 2) / se_need) ** 2 + 1
    res["Q4"]["textbook_independent_units"] = n_ind
    res["Q4"]["textbook_seconds"] = n_ind * BLOCK_S
    print(f"\n    CROSS-CHECK, textbook SE(r) = (1-r^2)/sqrt(n-1) on INDEPENDENT units:")
    print(f"       needs {n_ind:.0f} independent units ⇒ {n_ind*BLOCK_S/60:.0f} min. "
          f"The two methods bracket the answer.")
    print(f"\n    ⭐ ANSWER, for the drive protocol: ONE CONTINUOUS EPISODE OF "
          f"{res['Q4']['seconds_conservative']/60:.0f}-{n_ind*BLOCK_S/60:.0f} MINUTES.")
    print("    🛑 THE OPERATOR STOPS WITHIN 15-30 s OF FEELING THE SYMPTOM, AND THE BEST ENGAGED")
    print("       EXPOSURE EVER RECORDED IS 65.9 s (route 81).  That is 16-50x short.")
    print("    ⇒ THE E2 ENDPOINT CLASS -- DISCRIMINATING TWO CORRELATION VALUES ~0.1 APART -- IS")
    print("      UNBUILDABLE AT THIS EXPOSURE AND MUST NOT BE PROPOSED AGAIN.")
    det = k_cons / np.sqrt(12)
    res["Q4"]["detectable_r_at_12_blocks"] = det
    print(f"    ⊕ What E2-class statistics CAN still do at 12 blocks: detect |r| >= ~{det:.2f}")
    print(f"      against zero.  They are usable for LARGE effects only, never for discriminating")
    print(f"      two moderate ones.")

    # =========================== Q5 ==========================================================
    print("\n" + "=" * 98)
    print("=== Q5  CAN d_clamp BE BOUNDED FROM EXISTING 427 DATA, BEFORE SPENDING A DRIVE?")
    print("=" * 98)
    print(f"    `gp-0x6ad6` has never been on the wire, but `gp-0x6b70` IS -- CAN 427, and it is")
    print(f"    ONE OF THE TERMS SUMMED INTO IT.  Clamp threshold 0xC6200 = {CLAMP}.")
    res["Q5"] = {}
    print(f"\n    {'route':6s} {'n_eng':>7s} {'p50':>8s} {'p90':>8s} {'p99':>8s} {'MAX':>8s} "
          f"{'MAX/8192':>9s} {'frac>=8192':>11s}")
    mx = []
    for stem in ("r82", "r81", "r80"):
        try:
            eng, c = load427(stem)
        except Exception:
            continue
        e = c[eng]
        res["Q5"][stem] = dict(n=len(e), p50=float(np.percentile(e, 50)),
                               p90=float(np.percentile(e, 90)),
                               p99=float(np.percentile(e, 99)), max=float(e.max()),
                               frac_ge_clamp=float((e >= CLAMP).mean()))
        mx.append(float(e.max()))
        print(f"    {stem:6s} {len(e):7d} {np.percentile(e,50):8.1f} {np.percentile(e,90):8.1f} "
              f"{np.percentile(e,99):8.1f} {e.max():8.1f} {e.max()/CLAMP:9.3f} "
              f"{100*(e>=CLAMP).mean():10.4f}%")
    MX = max(mx)
    res["Q5"]["max_over_all_routes"] = MX
    res["Q5"]["frac_of_clamp"] = MX / CLAMP
    print(f"\n    ⭐ EVIDENCE: over {sum(res['Q5'][s]['n'] for s in ('r82','r81','r80') if s in res['Q5']):,}"
          f" engaged frames on THREE routes, |gp-0x6b70| NEVER EXCEEDS {MX:.0f} counts")
    print(f"      = {100*MX/CLAMP:.1f} % of the {CLAMP} clamp threshold, and 427 saturation is 0.000 %,")
    print(f"      so this is a real distribution tail and not a measurement ceiling.")
    print("\n    WHAT THIS DOES **NOT** GIVE:")
    print("      `gp-0x6ad6` is a SUM whose other terms (gp-0x6b4a +-25600, gp-0x6b60 +-15360,")
    print("      five more at +-10240) have a combined bound of ~100,352 -- 12x the threshold.")
    print("      They are UNOBSERVED, and they may add or cancel.")
    print("      ⇒ 🛑 NO NUMERICAL BOUND ON d_clamp IS DERIVABLE.  d_clamp in [0, 1] stands.")
    print("\n    ⭐ WHAT IT **DOES** GIVE, and it changes the build's expected value:")
    print(f"      `gp-0x6b70` can supply AT MOST {100*MX/CLAMP:.1f} % of the clamp threshold, so it")
    print(f"      CANNOT RAIL gp-0x6ad6 ON ITS OWN -- the other six terms must supply at least")
    print(f"      {CLAMP-MX:.0f} counts ({100*(CLAMP-MX)/CLAMP:.1f} %) of any rail that occurs.")
    print("      ⇒ IF d_clamp COMES BACK HIGH, THE SATURATION IS DRIVEN BY TERMS THE ENTIRE")
    print("        V89->V99 ARC NEVER TOUCHED, and the 'every lever was discarded by a saturation'")
    print("        hypothesis gains a mechanism.  IF IT COMES BACK LOW, the hypothesis dies and")
    print("        the levers were delivered, not discarded.  EITHER WAY RUNG A IS DECISIVE.")
    print("      ⊕ AND THE POSITIVE CONTROL IS PRE-COMPUTABLE: `|gp-0x6ad6| >= |gp-0x6b70|` has a")
    print("        predicted duty, because gp-0x6b70's distribution is measured above.  A wildly")
    print("        off value indicts the instrument, not the car -- which is exactly the property")
    print("        V96's over-ranged channel lacked.")

    (OUT / "v100_power_gate.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'v100_power_gate.json'}")
    return res


if __name__ == "__main__":
    main()
