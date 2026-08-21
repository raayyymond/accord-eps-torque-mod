#!/usr/bin/env python3
r"""v103_r9e_f0.py -- THE PRE-REGISTERED ENDPOINT for route 9e (V103): `f0`, the Re(Z) zero crossing.

PRE-REGISTERED, `docs/SPEC-2026-08-20-band-definition.md` §4 + `HANDOFF-2026-08-20` §3:
    STOCK 1x  f0 = 21.90 Hz [21.08, 23.03]   n=102
    V100  4x  f0 = 23.61 Hz [23.22, 23.95]   n=22
    V102  6x  f0 = 24.90 Hz [24.63, 25.26]   n=51
    law: f0 ~ 21.3 + 0.60 x (gain multiple).  V103 is 6x => PREDICTED 24.9-25.0 Hz.
    Honda's dormant biquad was predicted to move f0 by 0.06-0.3 Hz -- BELOW the ~1 Hz resolution.
    THE DRIVE CARD SAYS SO IN ADVANCE: "we are predicting that we will NOT be able to see it."

🛑 MANDATORY COVARIATE (`HANDOFF` §3.6): report median |0x0E4| alongside f0, and f0 ADJUSTED for
   command.  The cross-build amplitude law is -1.93 Hz per e-fold of command; the within-V102 law is
   -1.28 Hz per e-fold (25.683 @ cmd 70.5 -> 24.694 @ cmd 152.25).  BOTH are reported.
   An f0 shift sitting on that slope is NOT evidence a lever touched the loop.

🛑 BOOTSTRAP UNIT.  The record's CIs were bootstrapped over WINDOWS at 50 % overlap, which
   understates them.  This file reports BOTH: `ep` = block bootstrap over ENGAGEMENT EPISODES
   (primary, per `feedback-episodes-not-windows`), `win` = the legacy window bootstrap, quoted only
   so the number is comparable to the published table.

Estimator imported READ-ONLY from `decode_v90_probe`; `rez_control.py` pins it to 0.00 %.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402
import decode_v90_probe as P      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(1030_2026)
ARMS = [("97", "STOCK 1x", 891), ("85", "V100 4x", 3564),
        ("96", "V102 6x", 5346), ("9e", "V103 6x", 5346)]
PUBLISHED = {"97": 21.90, "85": 23.61, "96": 24.90}
SLOPE_XBUILD = -1.93          # Hz per e-fold of |0x0E4|, cross-build pooled  (HANDOFF 3.6)
SLOPE_WITHIN = -1.28          # Hz per e-fold, within-V102 halves            (_rez_f0_vs_amplitude)
OUT = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def groups_with_cmd(route, hop=V.HOP_Z):
    """Episode-grouped windows carrying (rate_rad, tq, v, |e4tq|, |rate_c|)."""
    z = V.load(route)
    M = V.masks(z)
    m = M["eng"] & (~M["press"]) & M["moving"]
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    G = V.wins_by_episode(z, m, (np.asarray(z["rate_f"], float) * V.DEG2RAD,
                                 np.asarray(z["tq"], float), M["v"],
                                 np.abs(np.asarray(z["e4tq"], float)),
                                 np.abs(np.asarray(z["rate_c"], float))),
                          hop=hop)
    G = [[w for w in ep if V.VLO <= float(np.median(w[2])) < V.VHI] for ep in G]
    return [ep for ep in G if ep], fs


def f0_arm(route, lab, gain):
    G, fs = groups_with_cmd(route)
    W = [w for ep in G for w in ep]
    if len(W) < 8:
        print("\n  %-11s only %d windows -- NOT SCOREABLE" % (lab, len(W)))
        return None
    pairs = [(w[0], w[1]) for w in W]
    pt = V.f0_of(pairs, fs)
    bs_ep = V.boot_episode([[(w[0], w[1]) for w in ep] for ep in G], fs, V.f0_of,
                           nboot=400, rng=np.random.default_rng(7))
    bs_wn = V.boot_window(pairs, fs, V.f0_of, nboot=400, rng=np.random.default_rng(7))
    elo, ehi = V.ci(bs_ep)
    wlo, whi = V.ci(bs_wn)
    cmd = float(np.median([np.median(w[3]) for w in W]))
    cmd_all = float(np.median(np.concatenate([w[3] for w in W])))
    vmed = float(np.median([np.median(w[2]) for w in W]))
    rmed = float(np.median([np.median(w[4]) for w in W]))
    sec = len(W) * V.HOP_Z / fs      # 50 % overlap -> effective seconds
    r = dict(route=route, build=lab, gain=gain, n_win=len(W), n_episodes=len(G),
             eng_s_effective=float(sec), f0=pt,
             ep_lo=elo, ep_hi=ehi, win_lo=wlo, win_hi=whi,
             cmd_median_of_window_medians=cmd, cmd_median_pooled=cmd_all,
             v_median_ms=vmed, rate_c_median=rmed,
             published=PUBLISHED.get(route))
    print("\n  %-11s  n=%3d windows in %2d episodes (%.0f s)   f0 = %.2f Hz"
          % (lab, len(W), len(G), sec, pt))
    print("               95%% CI  EPISODE-block [%.2f, %.2f]  (width %.2f)   "
          "window-block [%.2f, %.2f]  (width %.2f)"
          % (elo, ehi, ehi - elo, wlo, whi, whi - wlo))
    print("               median |0x0E4| in-band = %.0f (window medians) / %.0f (pooled frames)   "
          "v p50 %.1f m/s   |rate_c| p50 %.1f" % (cmd, cmd_all, vmed, rmed))
    if PUBLISHED.get(route):
        print("               published %.2f Hz -- reproduction delta %+.3f Hz"
              % (PUBLISHED[route], pt - PUBLISHED[route]))
    return r


def main():
    hdr("PART 1 -- f0, EVERY ARM, RE-RUN THROUGH ONE ESTIMATOR.\n"
        "         engaged, HANDS-OFF, moving, 29-86 km/h.  5.12 s Hann windows, 50 % hop.")
    res = {}
    for rt, lab, g in ARMS:
        r = f0_arm(rt, lab, g)
        if r:
            res[rt] = r
    OUT["f0"] = res

    hdr("PART 2 -- THE ENDPOINT READ-OUT.  Lower f0 = better (stock 21.90 is the target).")
    print("  %-11s %6s %8s %10s %22s %22s %10s"
          % ("build", "gain", "x stock", "f0 Hz", "95% CI (episode)", "95% CI (window)",
             "med|0E4|"))
    for rt, lab, g in ARMS:
        if rt not in res:
            continue
        r = res[rt]
        print("  %-11s %6d %8.1f %10.2f  [%6.2f, %6.2f] (%4.2f)  [%6.2f, %6.2f] (%4.2f) %10.0f"
              % (lab, g, g / 891.0, r["f0"], r["ep_lo"], r["ep_hi"], r["ep_hi"] - r["ep_lo"],
                 r["win_lo"], r["win_hi"], r["win_hi"] - r["win_lo"],
                 r["cmd_median_of_window_medians"]))
    if "96" in res and "9e" in res:
        a, b = res["96"], res["9e"]
        d = b["f0"] - a["f0"]
        disj_ep = b["ep_lo"] > a["ep_hi"] or a["ep_lo"] > b["ep_hi"]
        print("\n  ⭐ V103 - V102 = %+.2f Hz   episode CIs %s"
              % (d, "DISJOINT" if disj_ep else "OVERLAP"))
        print("     (V103's biquad was PREDICTED to move f0 by 0.06-0.3 Hz, against ~1 Hz "
              "resolution -- a null here is the PRE-REGISTERED expectation, not a failure)")
        OUT["v103_minus_v102"] = dict(delta=float(d), disjoint_episode=bool(disj_ep))
    if "97" in res and "9e" in res:
        a, b = res["97"], res["9e"]
        print("  ⭐ V103 - STOCK = %+.2f Hz   episode CIs %s   (stock is the TARGET)"
              % (b["f0"] - a["f0"],
                 "DISJOINT" if (b["ep_lo"] > a["ep_hi"] or a["ep_lo"] > b["ep_hi"]) else "OVERLAP"))
        OUT["v103_minus_stock"] = float(b["f0"] - a["f0"])

    # ---------------------------------------------------------------- COMMAND COVARIATE
    hdr("PART 3 -- 🛑 THE MANDATORY COMMAND COVARIATE.  An f0 quoted without it is uninterpretable.\n"
        "         f0_adj = f0_obs - slope x (ln cmd_arm - ln cmd_ref).  Reference = V102's command.")
    if "9e" in res and "96" in res:
        cref = res["96"]["cmd_median_of_window_medians"]
        print("  reference command (V102 in-band median |0x0E4|) = %.0f" % cref)
        print("  %-11s %10s %10s %14s %14s"
              % ("build", "med|0E4|", "f0 obs", "f0 adj (-1.93)", "f0 adj (-1.28)"))
        adj = {}
        for rt, lab, g in ARMS:
            if rt not in res:
                continue
            r = res[rt]
            c = max(r["cmd_median_of_window_medians"], 1.0)
            e = np.log(c) - np.log(cref)
            a1 = r["f0"] - SLOPE_XBUILD * e
            a2 = r["f0"] - SLOPE_WITHIN * e
            adj[rt] = dict(cmd=c, efold_vs_ref=float(e), f0=r["f0"],
                           f0_adj_xbuild=float(a1), f0_adj_within=float(a2))
            print("  %-11s %10.0f %10.2f %14.2f %14.2f" % (lab, c, r["f0"], a1, a2))
        OUT["f0_command_adjusted"] = adj
        if "9e" in adj and "96" in adj:
            print("\n  ⭐ V103 - V102 AFTER command adjustment: %+.2f Hz (x-build law)   "
                  "%+.2f Hz (within-V102 law)"
                  % (adj["9e"]["f0_adj_xbuild"] - adj["96"]["f0_adj_xbuild"],
                     adj["9e"]["f0_adj_within"] - adj["96"]["f0_adj_within"]))
            print("     RAW delta was %+.2f Hz.  The command difference alone predicts %+.2f Hz "
                  "(x-build) / %+.2f Hz (within)."
                  % (res["9e"]["f0"] - res["96"]["f0"],
                     SLOPE_XBUILD * (adj["9e"]["efold_vs_ref"] - adj["96"]["efold_vs_ref"]),
                     SLOPE_WITHIN * (adj["9e"]["efold_vs_ref"] - adj["96"]["efold_vs_ref"])))

    # ---------------------------------------------------------------- WITHIN-ROUTE AMPLITUDE
    hdr("PART 4 -- WITHIN-ROUTE COMMAND STRATIFICATION on 9e.  Firmware is IDENTICAL across the\n"
        "         two arms by construction, so the contrast is clean.  Drive-card item ② .")
    G, fs = groups_with_cmd("9e")
    W = [w for ep in G for w in ep]
    amp = np.array([float(np.median(w[3])) for w in W])
    med = np.median(amp)
    strata = {}
    for nm, sel in (("LOW cmd", [w for w, a in zip(W, amp) if a <= med]),
                    ("HIGH cmd", [w for w, a in zip(W, amp) if a > med])):
        if len(sel) < 8:
            continue
        pr = [(w[0], w[1]) for w in sel]
        pt = V.f0_of(pr, fs)
        b = V.boot_window(pr, fs, V.f0_of, nboot=300, rng=np.random.default_rng(11))
        lo, hi = V.ci(b)
        strata[nm] = dict(n=len(sel), f0=pt, lo=lo, hi=hi,
                          cmd=float(np.median([np.median(w[3]) for w in sel])),
                          v=float(np.median([np.median(w[2]) for w in sel])),
                          rate=float(np.median([np.median(w[4]) for w in sel])))
        s = strata[nm]
        print("  %-9s n=%3d  |cmd| p50 %6.0f   v p50 %5.2f m/s   |rate_c| p50 %5.1f   "
              "f0 %.2f [%.2f, %.2f]" % (nm, s["n"], s["cmd"], s["v"], s["rate"],
                                        s["f0"], s["lo"], s["hi"]))
    if len(strata) == 2:
        a, b = strata["LOW cmd"], strata["HIGH cmd"]
        d = b["f0"] - a["f0"]
        e = np.log(b["cmd"] / max(a["cmd"], 1e-9))
        vr = b["v"] / max(a["v"], 1e-9)
        print("  ==> HIGH - LOW = %+.2f Hz over a %.2fx command range (%.3f e-folds) => "
              "%+.2f Hz/e-fold" % (d, b["cmd"] / max(a["cmd"], 1e-9), e, d / e if e else np.nan))
        print("      CIs %s   speed ratio %.2fx %s"
              % ("DISJOINT" if (b["lo"] > a["hi"] or a["lo"] > b["hi"]) else "OVERLAP", vr,
                 "(matched)" if 0.85 <= vr <= 1.18 else
                 "🛑 NOT matched -- partly a SPEED contrast"))
        print("      [V102's own within-route value was -0.99 Hz over 2.16x = -1.28 Hz/e-fold]")
        OUT["within_route_amplitude"] = dict(strata=strata, delta=float(d),
                                             per_efold=float(d / e) if e else None,
                                             speed_ratio=float(vr))

    # ---------------------------------------------------------------- SPLIT-HALF NULL
    hdr("PART 5 -- SPLIT-HALF NULL (run BEFORE any ratio is quoted).  Random halves of the SAME\n"
        "         episodes must give the same f0.  A large split-half spread voids the endpoint.")
    ne = len(G)
    d = []
    for k in range(200):
        r2 = np.random.default_rng(500 + k)
        idx = r2.permutation(ne)
        h1 = [w for i in idx[: ne // 2] for w in G[i]]
        h2 = [w for i in idx[ne // 2:] for w in G[i]]
        if len(h1) < 6 or len(h2) < 6:
            continue
        a = V.f0_of([(w[0], w[1]) for w in h1], fs)
        b = V.f0_of([(w[0], w[1]) for w in h2], fs)
        if np.isfinite(a) and np.isfinite(b):
            d.append(b - a)
    d = np.array(d)
    lo, hi = V.ci(d)
    print("  %d episode split-halves: |delta f0| p50 %.2f Hz  p90 %.2f Hz   95%% interval "
          "[%.2f, %.2f] Hz" % (len(d), np.median(np.abs(d)), np.percentile(np.abs(d), 90), lo, hi))
    print("  ==> the endpoint's OWN irreducible noise floor on this route is +-%.2f Hz.  "
          "Any claimed shift smaller than this is NOT resolvable." % (max(abs(lo), abs(hi))))
    OUT["split_half"] = dict(n=len(d), p50_abs=float(np.median(np.abs(d))),
                             p90_abs=float(np.percentile(np.abs(d), 90)),
                             lo=float(lo), hi=float(hi))

    # ---------------------------------------------------------------- BANDS + CONTROLS
    hdr("PART 6 -- Re(Z) IN FIXED BANDS, WITH THE PRE-DECLARED CONTROLS.\n"
        "         primary 22-26 · robustness 20-28 · legacy 21.5-25.5 · sign-stable control 6-9\n"
        "         · negative control 31-35 (NOT 26-31: that one tracks the dose).")
    BANDS = [("6-9", 6.0, 9.0), ("15-22", 15.0, 22.0), ("18-22", 18.0, 22.0),
             ("20-28", 20.0, 28.0), ("21.5-25.5", 21.5, 25.5), ("22-26", 22.0, 26.0),
             ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
    OUT["bands"] = {}
    for rt, lab, _g in ARMS:
        Gx, fsx = groups_with_cmd(rt)
        Wx = [w for ep in Gx for w in ep]
        if len(Wx) < 8:
            continue
        pr = [(w[0], w[1]) for w in Wx]
        eg = [[(w[0], w[1]) for w in ep] for ep in Gx]
        print("\n  --- %s, %d windows / %d episodes ---" % (lab, len(Wx), len(Gx)))
        print("      %-11s %11s %22s %8s %10s %8s   %s"
              % ("band", "Re(Z)", "95% CI (episode)", "coh2", "shuffled", "ratio", "sign"))
        idx = RNG.permutation(len(pr))
        for bn, lo_, hi_ in BANDS:
            r = P._band_transfer(pr, fsx, V.NW_Z, [("b", lo_, hi_)])["b"]
            sh = P._band_transfer([(pr[i][0], pr[(idx[i] + 1) % len(pr)][1])
                                   for i in range(len(pr))], fsx, V.NW_Z, [("b", lo_, hi_)])["b"]
            b = V.boot_episode(eg, fsx,
                               lambda p_, f_, L_=lo_, H_=hi_:
                               P._band_transfer(p_, f_, V.NW_Z, [("b", L_, H_)])["b"]["re_over_sxx"],
                               nboot=250, rng=np.random.default_rng(23))
            blo, bhi = V.ci(b)
            sig = "NEG" if bhi < 0 else ("POS" if blo > 0 else " . ")
            ratio = r["coh2"] / max(sh["coh2"], 1e-9)
            print("      %-11s %11.0f  [%8.0f,%8.0f] %8.3f %10.4f %8.1f   %s"
                  % (bn, r["re_over_sxx"], blo, bhi, r["coh2"], sh["coh2"], ratio, sig))
            OUT["bands"].setdefault(rt, {})[bn] = dict(
                re_z=float(r["re_over_sxx"]), lo=float(blo), hi=float(bhi),
                coh2=float(r["coh2"]), shuffled=float(sh["coh2"]), ratio=float(ratio), sign=sig)

    # ---------------------------------------------------------------- SIGN MAP
    hdr("PART 7 -- SLIDING 2 Hz SIGN MAP, 16-36 Hz.  The crossing's location, seen directly.")
    lo_edges = np.arange(16.0, 35.0, 1.0)
    OUT["sign_map"] = {}
    for rt, lab, _g in ARMS:
        Gx, fsx = groups_with_cmd(rt)
        Wx = [w for ep in Gx for w in ep]
        if len(Wx) < 8:
            continue
        pr = [(w[0], w[1]) for w in Wx]
        eg = [[(w[0], w[1]) for w in ep] for ep in Gx]
        row = []
        for lo_ in lo_edges:
            r = P._band_transfer(pr, fsx, V.NW_Z, [("b", lo_, lo_ + 2.0)])["b"]
            b = V.boot_episode(eg, fsx,
                               lambda p_, f_, L_=lo_:
                               P._band_transfer(p_, f_, V.NW_Z,
                                                [("b", L_, L_ + 2.0)])["b"]["re_over_sxx"],
                               nboot=150, rng=np.random.default_rng(31))
            blo, bhi = V.ci(b)
            row.append(dict(lo=float(lo_), re_z=float(r["re_over_sxx"]), lo_ci=float(blo),
                            hi_ci=float(bhi), coh2=float(r["coh2"]),
                            sig="N" if bhi < 0 else ("P" if blo > 0 else ".")))
        OUT["sign_map"][rt] = dict(build=lab, rows=row)
    print("      %-11s %s" % ("Hz", "".join("%4.0f" % x for x in lo_edges)))
    for rt, lab, _g in ARMS:
        if rt in OUT["sign_map"]:
            print("      %-11s %s" % (lab, "".join("%4s" % x["sig"]
                                                   for x in OUT["sign_map"][rt]["rows"])))
    print("      (N = 95 % CI entirely below zero = ANTI-DAMPED · P = entirely above = DAMPED)")

    Path(HERE / "_v103_r9e_f0.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _v103_r9e_f0.json")


if __name__ == "__main__":
    main()
