# -*- coding: utf-8 -*-
"""AccordFFRateGain: the saturation ceiling on logged V293 torque-mode demand.

Section 1  reproduce the fork's own number on route 70 (positive control for the whole exercise)
Section 2  gain sweep, all torque-mode routes, per speed band
Section 3  the two regimes -- dwell / low demand rate vs high-demand-rate transient
Section 4  what saturation DOES: clip episode lengths and what they coincide with
Section 5  the ceiling, and the below-8-m/s-only gating the design stream actually proposed

EXACTNESS.  Only ONE quantity is reconstructed: the move term
    move(gain) = clip(gain * angle_des_rate / G(v), -limit(v), +limit(v))
Everything else is taken from the log:
    ff_torque(gain)     = pid_log.f/LAF                  - (move(gain) - move(gain_flown))
    u_unclipped(gain)   = (p + i + f)/LAF                - (move(gain) - move(gain_flown))
    delivered(gain)     = clip(u_unclipped(gain), -1, +1)
so at the flown gain every number reduces to the logged one exactly.  `validate.py` shows the
reconstruction of the WHOLE ff reproduces pid_log.f/LAF to corr >= 0.999, slope 0.995-1.002,
rms 0.0003-0.0058 torque, with latAccelOffset OFF.

⚠ OPEN LOOP IN ONE PLACE ONLY: P, I and the observer are held at their logged values.  A real drive
at a higher gain would move them.  This is a REACH/SATURATION arithmetic question on logged demand,
not a prediction of the closed-loop response, and it is reported as such.

ANALYSIS ONLY.  Run: python sweep.py
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ffrecon as F                     # noqa: E402
import v282cmp as C                     # noqa: E402
from validate import load               # noqa: E402

CACHE = C.CACHE
FS = 100.0
GAINS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
FINE = [round(x, 3) for x in np.arange(0.5, 4.001, 0.05)]
BANDS = [(2.0, 8.0, "2-8"), (8.0, 15.0, "8-15"), (15.0, 99.0, ">15")]
# |angle_des_rate| regimes, deg/s of DESIRED wheel angle (the quantity the move term is fed)
DWELL_HI, TRANS_LO = 15.0, 75.0
HBINS = np.arange(0.0, 6.0005, 0.005)   # histogram of |torque| for pooled percentiles


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


LOG = []


def hist_stats(h, edges, qs=(0.99, 0.999)):
    """percentiles from a histogram of |torque| (bin width 0.005 -> resolution 0.005)."""
    n = h.sum()
    if n == 0:
        return {q: float("nan") for q in qs}
    cdf = np.cumsum(h) / n
    out = {}
    for q in qs:
        k = int(np.searchsorted(cdf, q))
        out[q] = float(edges[min(k + 1, len(edges) - 1)])
    return out


def longest_run(mask, t):
    """longest contiguous True stretch with no clock gap, in seconds"""
    best = 0.0
    n = len(mask)
    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < 4.0 / FS:
            j += 1
        best = max(best, (t[j] - t[i]) + 1.0 / FS)
        i = j + 1
    return best


def route_frames(rk, cfg, use_offset=False):
    """the per-frame quantities every section needs, for one route"""
    S = load(rk)
    tab = F.TABLES[cfg["commit"]]
    ad, adr, d_ad, dt = F.build_demand(S, cfg, use_offset)
    hold = F.hold_term(ad, S["v"], cfg, tab)
    G = np.interp(np.nan_to_num(S["v"]), tab["G_BP"], tab["G_V"])
    lim = F.move_limit(np.nan_to_num(S["v"]))
    r = adr / G                                       # move term per unit gain, before the clip
    mv0 = np.clip(cfg["gain"] * r, -lim, lim)         # the move term the drive actually ran
    laf = cfg["laf"]
    ff0 = S["f"] / laf                                # LOGGED feedforward torque
    u0 = (S["p"] + S["i"] + S["f"]) / laf             # LOGGED unclipped command (= -clip -> out)
    m = S["active"] & ~S["pressed"]
    return dict(t=S["t"], v=np.nan_to_num(S["v"]), sa=np.nan_to_num(S["sa"]), mask=m,
                ad=ad, adr=adr, hold=hold, r=r, lim=lim, mv0=mv0, ff0=ff0, u0=u0,
                sat=S["sat"], dt=dt, tag=cfg["tag"])


# =================================================================================================
# SECTION 1 -- reproduce the fork's own claim on route 70
# =================================================================================================
def section1():
    pr("=" * 118)
    pr("SECTION 1  REPRODUCTION OF THE FORK'S OWN NUMBER (positive control)")
    pr("=" * 118)
    pr("latcontrol_vehicle_tunes.py:179-183, written at commit 8c4051ce6:")
    pr("   \"at 1.0 the feedforward alone exceeded full scale for 0.34 s below 8 m/s on route 70's")
    pr("    own demand (max 1.13); at 0.5 the max is 0.81.\"")
    pr("Route 70 flew AccordRatePlantFF=0 (initData) -- the feedforward did NOT run on that drive, so")
    pr("this is necessarily an offline recomputation on route 70's logged demand, which is what we redo.")
    pr("The hold term is the LINEAR k(v)*angle/G(v) of that commit (the saturating hold map did not")
    pr("exist yet).  Two candidate K tables are tried: 8c4051ce6's (the bounded low-speed knots, which")
    pr("that commit introduced) and 4247cb09e's (the pre-bound knots route 70 itself shipped).")
    pr("")
    rk = "00000070--717f5a7866"
    base = dict(F.ROUTECFG[rk])
    pr(f"{'K table':12s} {'offset':7s} {'mask':16s} {'gain':>5s} {'max|FF|':>8s} {'sec>1.0':>8s} "
       f"{'p99|FF|':>8s} {'frames':>8s}  {'max|move|':>9s} {'max|hold|':>9s}")
    got = []
    for ktab in ("8c4051ce6", "4247cb09e"):
        cfg = dict(base)
        cfg["commit"] = ktab
        for use_off in (False, True):
            D = route_frames(rk, cfg, use_off)
            for mname, mm in (("engaged,!pressed", D["mask"]),
                              ("engaged", D["mask"] | (D["sat"] & False))):
                if mname == "engaged":
                    S = load(rk)
                    mm = S["active"]
                    del S
                sub = mm & (D["v"] >= 0.0) & (D["v"] < 8.0)
                if sub.sum() < 100:
                    continue
                for g in (0.5, 1.0):
                    mv = np.clip(g * D["r"], -D["lim"], D["lim"])
                    ffa = np.abs(D["hold"] + mv)
                    over = sub & (ffa > 1.0)
                    row = (ktab, "ON" if use_off else "OFF", mname, g, float(ffa[sub].max()),
                           float(over.sum() / FS), float(np.percentile(ffa[sub], 99)), int(sub.sum()),
                           float(np.abs(mv[sub]).max()), float(np.abs(D["hold"][sub]).max()))
                    got.append(row)
                    pr(f"{row[0]:12s} {row[1]:7s} {row[2]:16s} {row[3]:5.2f} {row[4]:8.3f} "
                       f"{row[5]:8.3f} {row[6]:8.3f} {row[7]:8d}  {row[8]:9.3f} {row[9]:9.3f}")
            del D
    pr("")
    # closest match to the claim (1.13 at gain 1.0, 0.34 s, 0.81 at gain 0.5)
    best, bd = None, 1e9
    for i, r1 in enumerate(got):
        if r1[3] != 1.0:
            continue
        mate = [r for r in got if r[:3] == r1[:3] and r[3] == 0.5]
        if not mate:
            continue
        d = abs(r1[4] - 1.13) / 1.13 + abs(r1[5] - 0.34) / 0.34 + abs(mate[0][4] - 0.81) / 0.81
        if d < bd:
            bd, best = d, (r1, mate[0])
    if best:
        a, b = best
        pr(f"CLOSEST VARIANT: K {a[0]}, latAccelOffset {a[1]}, mask {a[2]}")
        pr(f"   gain 1.0 -> max {a[4]:.3f} (claim 1.13, {100*(a[4]-1.13)/1.13:+.1f} %), "
           f"{a[5]:.3f} s above full scale (claim 0.34 s, {100*(a[5]-0.34)/0.34:+.1f} %)")
        pr(f"   gain 0.5 -> max {b[4]:.3f} (claim 0.81, {100*(b[4]-0.81)/0.81:+.1f} %)")
    pr("")


# =================================================================================================
# SECTION 2 -- the sweep
# =================================================================================================
def accumulate(routes):
    """per (gain, band): pooled histograms of |FF alone| and |total unclipped|, seconds over
    full scale, exact maxima, clip-binding fraction, longest clip episode, and the regime split."""
    A = {}
    for rk, cfg in routes:
        D = route_frames(rk, cfg)
        for lo, hi, bn in BANDS:
            bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
            if bm.sum() < 200:
                continue
            aadr = np.abs(D["adr"])
            regimes = (("all", bm),
                       ("dwell", bm & (aadr < DWELL_HI)),
                       ("mid", bm & (aadr >= DWELL_HI) & (aadr < TRANS_LO)),
                       ("trans", bm & (aadr >= TRANS_LO)))
            for g in GAINS:
                mv = np.clip(g * D["r"], -D["lim"], D["lim"])
                ffa = np.abs(D["hold"] + mv)
                u = D["u0"] - (mv - D["mv0"])
                ua = np.abs(u)
                clipd = np.abs(g * D["r"]) > D["lim"]
                for rn, rmask in regimes:
                    k = (g, bn, rn)
                    a = A.setdefault(k, dict(n=0, hff=np.zeros(len(HBINS) - 1), hu=np.zeros(len(HBINS) - 1),
                                             maxff=0.0, maxu=0.0, secff=0.0, secu=0.0, nclip=0,
                                             longest=0.0, per_route={}))
                    if rmask.sum() == 0:
                        continue
                    a["n"] += int(rmask.sum())
                    a["hff"] += np.histogram(np.minimum(ffa[rmask], HBINS[-2]), bins=HBINS)[0]
                    a["hu"] += np.histogram(np.minimum(ua[rmask], HBINS[-2]), bins=HBINS)[0]
                    a["maxff"] = max(a["maxff"], float(ffa[rmask].max()))
                    a["maxu"] = max(a["maxu"], float(ua[rmask].max()))
                    a["secff"] += float((rmask & (ffa > 1.0)).sum() / FS)
                    a["secu"] += float((rmask & (ua > 1.0)).sum() / FS)
                    a["nclip"] += int((rmask & clipd).sum())
                    a["longest"] = max(a["longest"], longest_run(rmask & (ua >= 1.0), D["t"]))
                    a["per_route"][D["tag"]] = dict(
                        sec_u=float((rmask & (ua > 1.0)).sum() / FS), maxu=float(ua[rmask].max()),
                        maxff=float(ffa[rmask].max()), n=int(rmask.sum()))
        del D
    return A


def section2(A):
    pr("=" * 118)
    pr("SECTION 2  GAIN SWEEP -- all torque-mode routes pooled, engaged and hands-off")
    pr("=" * 118)
    pr("|FF| = |hold + move| (the fork's own 'feedforward alone').  |TOTAL| = |p+i+f|/LAF, the command")
    pr("BEFORE the +/-1.0 clip, with P, I and the observer held at their logged values (open loop).")
    pr("Full scale = 1.0 torque (steer_max, latcontrol.py:17).")
    pr("")
    for lo, hi, bn in BANDS:
        if (GAINS[0], bn, "all") not in A:
            continue
        secs = A[(GAINS[0], bn, 'all')]['n'] / FS
        pr(f"--- speed {bn} m/s   ({secs:.0f} s engaged hands-off, move-term limit "
           f"{float(F.move_limit((lo+min(hi,30))/2)):.2f}) ---")
        pr(f"{'gain':>5s} {'max|FF|':>8s} {'p99|FF|':>8s} {'s |FF|>1':>9s} | {'max|TOT|':>9s} "
           f"{'p99|TOT|':>9s} {'p99.9':>7s} {'%>=1.0':>8s} {'s >1.0':>8s} {'longest s':>10s} "
           f"| {'% move clipped':>15s}")
        for g in GAINS:
            a = A.get((g, bn, "all"))
            if not a:
                continue
            qff = hist_stats(a["hff"], HBINS)
            qu = hist_stats(a["hu"], HBINS)
            fr = float(np.sum(a["hu"][HBINS[1:] > 1.0]) / max(a["n"], 1))
            pr(f"{g:5.2f} {a['maxff']:8.3f} {qff[0.99]:8.3f} {a['secff']:9.2f} | {a['maxu']:9.3f} "
               f"{qu[0.99]:9.3f} {qu[0.999]:7.3f} {100*fr:8.3f} {a['secu']:8.2f} {a['longest']:10.2f} "
               f"| {100.0*a['nclip']/max(a['n'],1):15.3f}")
        pr("")


def section3(A):
    pr("=" * 118)
    pr("SECTION 3  THE TWO REGIMES -- a gain can be safe at a dwell and ruinous on a transient")
    pr("=" * 118)
    pr(f"dwell = |angle_des_rate| < {DWELL_HI:.0f} deg/s   mid = {DWELL_HI:.0f}-{TRANS_LO:.0f}   "
       f"transient = >= {TRANS_LO:.0f} deg/s   (of the DESIRED wheel angle, the move term's input)")
    pr("")
    for lo, hi, bn in BANDS:
        if (GAINS[0], bn, "all") not in A:
            continue
        pr(f"--- speed {bn} m/s ---")
        pr(f"{'regime':10s} {'share%':>7s} {'sec':>8s} | " + " ".join(f"{'g=' + format(g, '.2f'):>26s}" for g in (0.5, 1.0, 2.0)))
        pr(f"{'':10s} {'':7s} {'':8s} | " + " ".join(f"{'max|FF|  max|TOT|  s>1.0':>26s}" for _ in (0.5, 1.0, 2.0)))
        ntot = A[(0.5, bn, "all")]["n"]
        for rn in ("dwell", "mid", "trans"):
            a0 = A.get((0.5, bn, rn))
            if not a0 or a0["n"] == 0:
                continue
            cells = []
            for g in (0.5, 1.0, 2.0):
                a = A[(g, bn, rn)]
                cells.append(f"{a['maxff']:8.3f} {a['maxu']:9.3f} {a['secu']:7.2f}")
            pr(f"{rn:10s} {100.0*a0['n']/ntot:7.2f} {a0['n']/FS:8.1f} | " + " ".join(f"{c:>26s}" for c in cells))
        pr("")


def section4(routes):
    pr("=" * 118)
    pr("SECTION 4  WHAT SATURATION DOES -- clip episodes, and what they coincide with")
    pr("=" * 118)
    pr("While |TOTAL| >= 1.0 the delivered command is stuck at the rail: for that whole stretch the")
    pr("output stops being a function of the demand or the error, i.e. the lateral loop is OPEN.")
    pr("")
    pr(f"{'gain':>5s} {'band':>6s} {'episodes':>9s} {'total s':>8s} {'longest s':>10s} {'median s':>9s} "
       f"{'p90 s':>7s} | {'median |angle| in episode':>26s} {'% with |angle|>30 deg':>22s}")
    acc = {}
    for rk, cfg in routes:
        D = route_frames(rk, cfg)
        for lo, hi, bn in BANDS:
            bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
            if bm.sum() < 200:
                continue
            for g in (0.5, 1.0, 1.5, 2.0):
                mv = np.clip(g * D["r"], -D["lim"], D["lim"])
                ua = np.abs(D["u0"] - (mv - D["mv0"]))
                m = bm & (ua >= 1.0)
                k = (g, bn)
                a = acc.setdefault(k, dict(durs=[], angs=[]))
                for i0, i1 in C.runs(m, D["t"], min_s=0.0):
                    a["durs"].append((i1 - i0) / FS)
                    a["angs"].append(float(np.median(np.abs(D["sa"][i0:i1]))))
        del D
    for g in (0.5, 1.0, 1.5, 2.0):
        for lo, hi, bn in BANDS:
            a = acc.get((g, bn))
            if not a or not a["durs"]:
                pr(f"{g:5.2f} {bn:>6s} {0:9d} {0.0:8.2f}")
                continue
            d = np.array(a["durs"])
            an = np.array(a["angs"])
            pr(f"{g:5.2f} {bn:>6s} {len(d):9d} {d.sum():8.2f} {d.max():10.2f} {np.median(d):9.3f} "
               f"{np.percentile(d, 90):7.3f} | {np.median(an):26.1f} {100.0*(an > 30).mean():22.1f}")
        pr("")


def section5(routes):
    pr("=" * 118)
    pr("SECTION 5  THE CEILING, and the below-8-m/s-only gating that was actually proposed")
    pr("=" * 118)
    pr("Three criteria, all on the pooled torque-mode routes:")
    pr("  A  the fork's own:  max |hold+move| <= 1.00 below 8 m/s  (feedforward alone never full scale)")
    pr("  B  with margin:     max |hold+move| <= 0.85 below 8 m/s  (15 % of the actuator kept in hand)")
    pr("  C  no new railing:  seconds of |TOTAL| >= 1.0 below 8 m/s no worse than the flown 0.5")
    pr("")
    # pooled fine sweep, below 8 and 8-15
    out = {}
    for rk, cfg in routes:
        D = route_frames(rk, cfg)
        for lo, hi, bn in ((2.0, 8.0, "2-8"), (8.0, 15.0, "8-15"), (15.0, 99.0, ">15")):
            bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
            if bm.sum() < 200:
                continue
            for g in FINE:
                mv = np.clip(g * D["r"], -D["lim"], D["lim"])
                ffa = np.abs(D["hold"] + mv)
                ua = np.abs(D["u0"] - (mv - D["mv0"]))
                k = (bn, g)
                o = out.setdefault(k, dict(maxff=0.0, secu=0.0, maxu=0.0, n=0))
                o["maxff"] = max(o["maxff"], float(ffa[bm].max()))
                o["maxu"] = max(o["maxu"], float(ua[bm].max()))
                o["secu"] += float((bm & (ua >= 1.0)).sum() / FS)
                o["n"] += int(bm.sum())
        del D
    for bn in ("2-8", "8-15", ">15"):
        if (bn, 0.5) not in out:
            continue
        base = out[(bn, 0.5)]["secu"]
        gA = max([g for g in FINE if out[(bn, g)]["maxff"] <= 1.00], default=None)
        gB = max([g for g in FINE if out[(bn, g)]["maxff"] <= 0.85], default=None)
        gC = max([g for g in FINE if out[(bn, g)]["secu"] <= base + 1e-9], default=None)
        pr(f"--- {bn} m/s   (flown 0.5 baseline: {base:.2f} s at the rail, "
           f"max |FF| {out[(bn,0.5)]['maxff']:.3f}, max |TOT| {out[(bn,0.5)]['maxu']:.3f})")
        pr(f"    ceiling A (|FF| <= 1.00): {gA}      ceiling B (|FF| <= 0.85): {gB}      "
           f"ceiling C (no new railing): {gC}")
        rows = [g for g in (0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0) if (bn, g) in out]
        pr(f"    {'gain':>5s} {'max|FF|':>8s} {'max|TOT|':>9s} {'s at rail':>10s} {'x baseline':>11s}")
        for g in rows:
            o = out[(bn, g)]
            pr(f"    {g:5.2f} {o['maxff']:8.3f} {o['maxu']:9.3f} {o['secu']:10.2f} "
               f"{(o['secu']/base if base > 0 else float('inf')):11.2f}")
        pr("")
    pr("GATED PROPOSAL (raise below 8 m/s only, keep 0.5 at and above 8):")
    pr("  the >=8 m/s rows above at gain 0.5 are then unchanged; only the 2-8 m/s rows move.")
    pr("  NOTE the discontinuity this creates: the gain steps at 8 m/s, so the move term jumps by")
    pr("  (g-0.5)*angle_des_rate/G(8) = (g-0.5)*angle_des_rate/438 torque when the speed crosses 8 m/s.")
    pr("  At 100 deg/s of desired-angle rate and g=2.0 that is a 0.34 torque step. A speed-interpolated")
    pr("  schedule, not a step, is the only form of this lever that does not add its own transient.")
    pr("")
    with open(os.path.join(HERE, "ceiling_fine.json"), "w") as fh:
        json.dump({f"{k[0]}|{k[1]}": v for k, v in out.items()}, fh, indent=1)


if __name__ == "__main__":
    routes = [(rk, cfg) for rk, cfg in F.ROUTECFG.items()
              if cfg["ff_live"] and (CACHE / f"{rk}.npz").exists()]
    pr(F._self_test())
    pr("")
    pr("torque-mode routes with the rate-plant feedforward LIVE (AccordRatePlantFF=1 in initData):")
    for rk, cfg in routes:
        pr(f"   {cfg['tag']:6s} {rk:24s} {cfg['rev']:22s} commit {cfg['commit']}  "
           f"gain {cfg['gain']}  LAF {cfg['laf']}")
    pr("")
    section1()
    A = accumulate(routes)
    section2(A)
    section3(A)
    del A
    section4(routes)
    section5(routes)
    with open(os.path.join(HERE, "SWEEP-OUT.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")
