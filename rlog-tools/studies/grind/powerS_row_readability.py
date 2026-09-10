# -*- coding: utf-8 -*-
"""studies/grind/powerS_row_readability.py -- IS ROW S READABLE FROM ONE SHORT DRIVE?

Row S = the V290 cal-only candidate: Kd LERP 0xE511C (slot 7, knots X = 0/11/22/32) Y[0..2] = 96,
Y[3] = 128.  Kd is cut below demand index 22, ramps 96 -> 128 over 22 < idx < 32, and is
BYTE-IDENTICAL to the base above idx 32.  The proposed instrument is the build's OWN
WITHIN-DRIVE CONTROL: episodes at low demand are TREATED, episodes above idx 32 are UNTREATED.

This script asks four questions and does NOT assume the answer to any of them:
  1  POWER      -- per-episode variance of the decay-rate estimator; episodes needed to see
                   582 -> 254 ms (a x2.29 decay-rate ratio); minutes of engaged driving that costs.
  2  STRATA     -- how the treated/untreated split actually lands per drive, and P(usable) from one.
  3  CONFOUND   -- on r39 (V282) and r5e_v288 (V288), where Kd is FLAT 128 everywhere, compare the
                   ring between idx<=22 and idx>=32 episodes.  Any difference there is CONFOUND.
                   That is the floor a V290 within-drive read must beat.
  4  DiD        -- the difference-in-differences the within-drive control actually buys.

Agent `powerS` (SUBAGENT, orchestrator `main`), 2026-09-09.  Analysis only: builds nothing, sends nothing.
Run: python powerS_row_readability.py   (writes _scratch/powerS_row_readability.txt beside it)
"""
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import grind1_census_v288_r5e as C88        # noqa: E402  registers CEN.IMG["V288"] / CELL_OF; main() not run
import wire_0xe4_20hz as WIRE                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
NB = 4000
V282_ROUTES = ("r39", "r3a", "r3c")
V288_TAG = "r5e_v288"
V289_ROUTES = ("r62_v289", "r63_v289")
ALL = V282_ROUTES + (V288_TAG,) + V289_ROUTES
CACHE_P = os.path.join(SCR, "grind1_census_v289_r62_r63_cache.pkl")
V289_IMG = (LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-"
            "NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
CEN.IMG["V289"] = V289_IMG
for _t in V289_ROUTES:
    CEN.CELL_OF[_t] = "V289"
    CEN.GRP[_t] = "V289r1"

# row S geometry (reqaxis: TRACE-2026-09-09-kp-kd-schedule-axis.md)
KD_X = np.array([0, 11, 22, 32], float)
KD_Y_BASE = np.array([128, 128, 128, 128], float)
KD_Y_S = np.array([96, 96, 96, 128], float)
IDX_TREAT_HI = 22.0     # fully treated at or below
IDX_UNTREAT_LO = 32.0   # byte-identical to base at or above
TARGET_RATIO = 582.0 / 254.0   # decay-rate ratio row S predicts in the treated stratum

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def kd_of(idx, Y):
    return np.interp(np.asarray(idx, float), KD_X, Y)


def ci(v, lo=2.5, hi=97.5):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return (np.nan, np.nan)
    return (float(np.percentile(v, lo)), float(np.percentile(v, hi)))


def main():
    rng = np.random.default_rng(20260909)
    CACHED = pickle.load(open(CACHE_P, "rb"))
    episodes = CACHED["episodes"]
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288", "V289")}
    G = {}
    for tag in ALL:
        G[tag] = WIRE.load_route(tag, cells[CEN.CELL_OF[tag]])
        # 0x14A byte-4 comparator bits onto the 0x18F frame axis (verbatim from the census's load_b4)
        pb4 = os.path.join(C20.CACHE, tag + "_b4.npz")
        if os.path.exists(pb4):
            B = dict(np.load(pb4))
            _, _, tn14, _ = C20.dejitter(B["t14b"].astype(float), 0.01, 100)
            b4 = B["b4"].astype(int)
            for n in range(8):
                G[tag]["bit%d" % n] = np.round(np.interp(G[tag]["t"], tn14, ((b4 >> n) & 1).astype(float))).astype(int)
        print("loaded %s" % tag, flush=True)

    pr("=" * 150)
    pr("IS ROW S READABLE FROM ONE SHORT DRIVE?  --  the within-drive control, tested against the base builds")
    pr("=" * 150)
    pr("row S = Kd LERP 0xE511C  X = %s  Y: base %s -> S %s   (byte-identical above idx %.0f)" % (
        list(KD_X.astype(int)), list(KD_Y_BASE.astype(int)), list(KD_Y_S.astype(int)), IDX_UNTREAT_LO))
    pr("delivered Kd at idx 0/11/22/26/32/40 : base %s ; row S %s" % (
        [int(v) for v in kd_of([0, 11, 22, 26, 32, 40], KD_Y_BASE)],
        [round(float(v), 1) for v in kd_of([0, 11, 22, 26, 32, 40], KD_Y_S)]))
    pr("target effect: decay rate |gd| x%.2f in the TREATED stratum (time-to-10 %% 582 -> 254 ms)" % TARGET_RATIO)

    # -------------------------------------------------------------- per-episode stratum from the BODY, not the onset
    for e in episodes:
        g = G[e["tag"]]
        idxb = g["idx"][e["a"]:e["b"]]
        e["idx_p50"] = float(np.median(idxb))
        e["f_lo"] = float(np.mean(idxb <= IDX_TREAT_HI))
        e["f_hi"] = float(np.mean(idxb >= IDX_UNTREAT_LO))
        e["f_mid"] = float(np.mean((idxb > IDX_TREAT_HI) & (idxb < IDX_UNTREAT_LO)))
        # the Kd the episode body would actually see under row S, and the dose it represents
        e["kd_S_p50"] = float(np.median(kd_of(idxb, KD_Y_S)))
        e["kd_S_mean"] = float(np.mean(kd_of(idxb, KD_Y_S)))
        e["kd_S_sd"] = float(np.std(kd_of(idxb, KD_Y_S)))
        # crossings of the knot at 32 within the body -- the parametric-modulation exposure
        cross = np.diff((idxb >= IDX_UNTREAT_LO).astype(int)) != 0
        e["xrate"] = float(cross.sum() / max(e["dur"], 1e-9))
        if e["f_lo"] >= 0.70:
            e["stratum"] = "TREATED"
        elif e["f_hi"] >= 0.70:
            e["stratum"] = "UNTREATED"
        else:
            e["stratum"] = "MIXED"
        e["zeta"] = abs(e["gd"]) / (2 * np.pi * e["f0"]) if np.isfinite(e["gd"]) and e["f0"] > 0 else np.nan

    ARMS = [("r39 (V282)", ("r39",)), ("V282pool", V282_ROUTES), ("r5e_v288 (V288)", (V288_TAG,)),
            ("r62_v289", ("r62_v289",)), ("r63_v289", ("r63_v289",)), ("V289pool", V289_ROUTES)]

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("2. THE STRATIFICATION AS IT ACTUALLY LANDS  (episode BODY median idx; TREATED = >=70 %% of body frames at idx<=22)")
    pr("=" * 150)
    pr("  %-16s %5s | %-28s | %-28s | %s" % ("arm", "n ep", "TREATED n (share)", "UNTREATED n (share)", "MIXED n (share)"))
    STR = {}
    for name, tags in ARMS:
        es = [e for e in episodes if e["tag"] in tags]
        STR[name] = es
        n = len(es)
        c = {k: sum(1 for e in es if e["stratum"] == k) for k in ("TREATED", "UNTREATED", "MIXED")}
        pr("  %-16s %5d | %10d (%4.0f %%)%12s | %10d (%4.0f %%)%12s | %6d (%4.0f %%)" % (
            name, n, c["TREATED"], 100 * c["TREATED"] / max(n, 1), "", c["UNTREATED"], 100 * c["UNTREATED"] / max(n, 1), "",
            c["MIXED"], 100 * c["MIXED"] / max(n, 1)))
    pr("\n  Per-episode detail, V289 routes (the build row S would replace):")
    pr("  %-10s %-9s %6s %6s %6s %8s %8s %7s %7s %7s %8s %8s %7s" % (
        "route", "class", "t0 s", "dur", "f0", "idx p50", "stratum", "f_lo", "f_mid", "f_hi", "gd /s", "zeta", "xing/s"))
    for e in sorted([e for e in episodes if e["tag"] in V289_ROUTES], key=lambda e: (e["tag"], e["t0"])):
        pr("  %-10s %-9s %6.1f %6.2f %6.1f %8.0f %8s %7.2f %7.2f %7.2f %8.2f %8.4f %7.1f" % (
            e["tag"], e["cls"], e["t0"], e["dur"], e["f0"], e["idx_p50"], e["stratum"][:8],
            e["f_lo"], e["f_mid"], e["f_hi"], e["gd"], e["zeta"], e["xrate"]))

    # exposure-weighted: what share of grinding SECONDS row S actually treats
    pr("\n  2b. Grinding-episode SECONDS by Kd the body would see under row S (this is the DOSE, not the label):")
    pr("  %-16s %9s | %9s %9s %9s | %s" % ("arm", "epi s", "s idx<=22", "s 22-32", "s idx>=32", "mean delivered Kd in episodes (base 128)"))
    for name, tags in ARMS:
        es = STR[name]
        s_lo = sum(e["dur"] * e["f_lo"] for e in es)
        s_mid = sum(e["dur"] * e["f_mid"] for e in es)
        s_hi = sum(e["dur"] * e["f_hi"] for e in es)
        tot = s_lo + s_mid + s_hi
        kdm = (sum(e["dur"] * e["kd_S_mean"] for e in es) / tot) if tot > 0 else np.nan
        pr("  %-16s %9.1f | %6.1f (%2.0f%%) %6.1f (%2.0f%%) %6.1f (%2.0f%%) | %.1f  (x%.3f of base)" % (
            name, tot, s_lo, 100 * s_lo / max(tot, 1e-9), s_mid, 100 * s_mid / max(tot, 1e-9),
            s_hi, 100 * s_hi / max(tot, 1e-9), kdm, kdm / 128.0))

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("3. THE CONFOUND FLOOR  --  r39/V282pool and r5e_v288 have Kd FLAT 128 EVERYWHERE.")
    pr("   Any idx<=22 vs idx>=32 difference there is CONFOUND, not treatment.  This is the floor a V290 read must beat.")
    pr("=" * 150)

    def strat_compare(es, label):
        A = [e for e in es if e["stratum"] == "TREATED"]
        B = [e for e in es if e["stratum"] == "UNTREATED"]
        rows = []
        for key, fn in (("f0 Hz", lambda e: e["f0"]),
                        ("env peak", lambda e: e["env"]),
                        ("dur s", lambda e: e["dur"]),
                        ("|gd| /s", lambda e: abs(e["gd"])),
                        ("zeta", lambda e: e["zeta"])):
            a = np.array([fn(e) for e in A], float); a = a[np.isfinite(a) & (a > 0)]
            b = np.array([fn(e) for e in B], float); b = b[np.isfinite(b) & (b > 0)]
            if len(a) < 2 or len(b) < 2:
                rows.append((key, len(a), len(b), np.nan, np.nan, np.nan, np.nan, np.nan))
                continue
            r = np.median(a) / np.median(b)
            bs = np.empty(NB)
            for i in range(NB):
                bs[i] = np.median(rng.choice(a, len(a))) / max(np.median(rng.choice(b, len(b))), 1e-12)
            lo, hi = ci(bs)
            rows.append((key, len(a), len(b), float(np.median(a)), float(np.median(b)), r, lo, hi))
        pr("\n  %s" % label)
        pr("  %-10s %5s %5s | %11s %11s | %8s %-22s %s" % (
            "metric", "n lo", "n hi", "p50 idx<=22", "p50 idx>=32", "ratio", "95 % CI (bootstrap)", "confound?"))
        for key, na, nb, ma, mb, r, lo, hi in rows:
            flag = "-" if not np.isfinite(r) else ("CONFOUND (CI excludes 1)" if (lo > 1 or hi < 1) else "not resolved")
            pr("  %-10s %5d %5d | %11s %11s | %8s %-22s %s" % (
                key, na, nb,
                "%.3f" % ma if np.isfinite(ma) else "-", "%.3f" % mb if np.isfinite(mb) else "-",
                "%.3f" % r if np.isfinite(r) else "-",
                "[%.3f, %.3f]" % (lo, hi) if np.isfinite(lo) else "-", flag))
        return {k: (r, lo, hi, na, nb) for k, na, nb, ma, mb, r, lo, hi in rows}

    CONF = {}
    CONF["r39"] = strat_compare(STR["r39 (V282)"], "r39 (V282)  -- Kd flat 128, so EVERY row below is confound")
    CONF["V282pool"] = strat_compare(STR["V282pool"], "V282pool (r39+r3a+r3c) -- Kd flat 128")
    CONF["r5e_v288"] = strat_compare(STR["r5e_v288 (V288)"], "r5e_v288 (V288) -- Kd flat 128")
    CONF["V289pool"] = strat_compare(STR["V289pool"], "V289pool (r62+r63) -- Kd flat 128 (the build row S would replace)")

    # pooled base (V282pool + V288) -- the best-powered estimate of the confound
    base_es = STR["V282pool"] + STR["r5e_v288 (V288)"]
    CONF["BASEpool"] = strat_compare(base_es, "BASE POOL (V282pool + V288, n=%d) -- THE CONFOUND FLOOR" % len(base_es))

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("1. POWER  --  per-episode variance of the decay-rate estimator, and episodes needed for x%.2f" % TARGET_RATIO)
    pr("=" * 150)
    pr("  The estimator is CEN.growth_fit's log-envelope fall slope gd (/s); zeta = |gd| / (2 pi f0).")
    pr("  Dispersion is quoted in LOG units because the hypothesis is multiplicative (x2.29).")
    pr("  %-16s %5s | %9s %9s %9s | %9s %9s | %s" % (
        "arm", "n", "p50 |gd|", "geo mean", "sd(ln|gd|)", "p25", "p75", "IQR ratio p75/p25"))
    LGD = {}
    for name, tags in ARMS:
        v = np.array([abs(e["gd"]) for e in STR[name]], float)
        v = v[np.isfinite(v) & (v > 0)]
        lv = np.log(v)
        LGD[name] = lv
        pr("  %-16s %5d | %9.3f %9.3f %9.3f | %9.3f %9.3f | %.2f" % (
            name, len(v), np.median(v), np.exp(lv.mean()), lv.std(ddof=1) if len(lv) > 1 else np.nan,
            np.percentile(v, 25), np.percentile(v, 75), np.percentile(v, 75) / max(np.percentile(v, 25), 1e-9)))

    # bootstrap-by-episode power simulation, the kit convention
    def power_sim(pool, n_treat, n_ctrl, ratio, nsim=1200):
        pool = np.asarray(pool, float)
        hits = 0
        for _ in range(nsim):
            a = rng.choice(pool, n_treat) + np.log(ratio)
            b = rng.choice(pool, n_ctrl)
            bs = np.median(rng.choice(a, (400, n_treat)), axis=1) - np.median(rng.choice(b, (400, n_ctrl)), axis=1)
            lo, hi = ci(bs)
            if lo > 0 or hi < 0:
                hits += 1
        return hits / nsim

    basepool_l = np.concatenate([LGD["V282pool"], LGD["r5e_v288 (V288)"]])
    pr("\n  1a. TWO-ARM power (treated stratum of the V290 drive vs an untreated control of the SAME size),")
    pr("      resampling the base pool's per-episode ln|gd| (n=%d, sd %.3f), test = bootstrap-by-episode CI excluding 1:" % (
        len(basepool_l), basepool_l.std(ddof=1)))
    pr("  NOTE: the FALSE-POSITIVE column (ratio = x1.00) is printed FIRST because for n <= 3 the bootstrap CI on a")
    pr("  median of 1-3 values has (near-)zero width -- it is a false-positive machine, and its 'power' is meaningless.")
    pr("  %6s | %8s | %8s %8s %8s %8s" % ("n/arm", "FPR x1.0", "x1.50", "x2.29", "x3.00", "x5.00"))
    NEEDED = {}
    for n in (1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120):
        fpr = power_sim(basepool_l, n, n, 1.0)
        row = [power_sim(basepool_l, n, n, r) for r in (1.5, TARGET_RATIO, 3.0, 5.0)]
        NEEDED[n] = [fpr] + row
        pr("  %6d | %8.2f | %8.2f %8.2f %8.2f %8.2f%s" % (n, fpr, *row, "   <-- INVALID TEST" if fpr > 0.10 else ""))
    n80 = next((n for n in sorted(NEEDED) if NEEDED[n][2] >= 0.80 and NEEDED[n][0] <= 0.10), None)
    pr("  => episodes per arm for 80 %% power at x%.2f WITH a valid test (FPR <= 0.10) : %s" % (
        TARGET_RATIO, n80 if n80 else "> 120"))

    # the n = 1 case stated honestly: no interval estimator exists, so quote the raw dispersion
    sd1 = basepool_l.std(ddof=1)
    pr("")
    pr("  1a-bis. THE n = 1 CASE, stated without a test.  The operator stops the drive at the first symptom, so the")
    pr("      realistic sample is ONE episode per stratum.  ln|gd| has per-episode sd = %.3f on the base pool, so the" % sd1)
    pr("      LOG RATIO of two single episodes has sd = %.3f (sqrt 2 x).  The target effect is ln(%.2f) = %.3f." % (
        sd1 * np.sqrt(2), TARGET_RATIO, np.log(TARGET_RATIO)))
    pr("      => the effect is %.2f sigma of a single-episode contrast.  P(the observed contrast even has the right SIGN)" % (
        np.log(TARGET_RATIO) / (sd1 * np.sqrt(2))))
    from math import erf
    z = np.log(TARGET_RATIO) / (sd1 * np.sqrt(2))
    pr("      = %.2f ; the 95 %% interval on a one-vs-one ratio spans x%.0f in EITHER direction." % (
        0.5 * (1 + erf(z / np.sqrt(2))), np.exp(1.96 * sd1 * np.sqrt(2))))

    # difference-in-differences: what the within-drive control actually buys
    pr("\n  1b. DIFFERENCE-IN-DIFFERENCES power -- the within-drive control is a 4-arm estimator")
    pr("      (treated_V290 / untreated_V290) / (treated_base / untreated_base).  All four arms carry the same per-episode noise.")

    def power_did(pool, n_per_arm, ratio, nsim=600):
        pool = np.asarray(pool, float)
        hits = 0
        for _ in range(nsim):
            arms = {k: rng.choice(pool, n_per_arm) for k in ("t90", "u90", "tb", "ub")}
            arms["t90"] = arms["t90"] + np.log(ratio)
            M = {k: np.median(rng.choice(v, (400, n_per_arm)), axis=1) for k, v in arms.items()}
            bs = (M["t90"] - M["u90"]) - (M["tb"] - M["ub"])
            lo, hi = ci(bs)
            if lo > 0 or hi < 0:
                hits += 1
        return hits / nsim
    pr("  %6s | %8s | %8s %8s %8s" % ("n/arm", "FPR x1.0", "x1.50", "x2.29", "x5.00"))
    DID = {}
    for n in (1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120, 200):
        fpr = power_did(basepool_l, n, 1.0)
        row = [power_did(basepool_l, n, r) for r in (1.5, TARGET_RATIO, 5.0)]
        DID[n] = [fpr] + row
        pr("  %6d | %8.2f | %8.2f %8.2f %8.2f%s" % (n, fpr, *row, "   <-- INVALID TEST" if fpr > 0.10 else ""))
    ndid = next((n for n in sorted(DID) if DID[n][2] >= 0.80 and DID[n][0] <= 0.10), None)
    pr("  => episodes PER ARM for 80 %% power on the DiD at x%.2f WITH a valid test : %s" % (
        TARGET_RATIO, ndid if ndid else "> 200"))

    # 1d. the DiD does not need a fresh base arm -- the base stratum ratio is ALREADY MEASURED (sec. 3).
    pr("")
    pr("  1d. USING THE MEASURED BASE STRATUM RATIO instead of a fresh base arm.  Sec. 3 already measured the")
    pr("      confound on 98 base episodes: |gd| idx<=22 / idx>=32 = %.3f [%.3f, %.3f].  A V290 drive therefore only" % (
        CONF["BASEpool"]["|gd| /s"][0], CONF["BASEpool"]["|gd| /s"][1], CONF["BASEpool"]["|gd| /s"][2]))
    pr("      needs TWO arms, but its answer must beat a correction factor whose OWN 95 %% interval spans x%.1f." % (
        CONF["BASEpool"]["|gd| /s"][2] / max(CONF["BASEpool"]["|gd| /s"][1], 1e-9)))
    corr_lo, corr_hi = CONF["BASEpool"]["|gd| /s"][1], CONF["BASEpool"]["|gd| /s"][2]
    pr("      Target = x%.2f.  Confound-corrected target band = x%.2f to x%.2f -- i.e. the base's own stratum" % (
        TARGET_RATIO, TARGET_RATIO * corr_lo, TARGET_RATIO * corr_hi))
    pr("      uncertainty ALONE straddles the effect.  [EVIDENCE: sec. 3 bootstrap, n = %d vs %d base episodes]" % (
        CONF["BASEpool"]["|gd| /s"][3], CONF["BASEpool"]["|gd| /s"][4]))

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("1c. WHAT THAT COSTS IN MINUTES  --  measured episode rates and the treated-stratum share")
    pr("=" * 150)
    pr("  %-16s %8s %10s %12s %14s %14s" % ("arm", "eng s", "n ep", "ep / eng h", "TREATED ep/h", "min for 1 TREATED ep"))
    RATES = {}
    for name, tags in ARMS:
        eng_s = sum(G[t]["eng"].sum() / FS for t in tags)
        es = STR[name]
        n = len(es)
        nt = sum(1 for e in es if e["stratum"] == "TREATED")
        r_all = 3600 * n / max(eng_s, 1e-9)
        r_t = 3600 * nt / max(eng_s, 1e-9)
        RATES[name] = (eng_s, n, nt, r_all, r_t)
        pr("  %-16s %8.0f %10d %12.0f %14.0f %14s" % (
            name, eng_s, n, r_all, r_t, "%.1f" % (60.0 / r_t) if r_t > 0 else "inf (0 seen)"))

    pr("\n  Minutes of ENGAGED driving needed, at each arm's measured TREATED-episode rate, for n episodes:")
    pr("  %-16s | %s" % ("arm", "  ".join("%5s" % ("%d ep" % n) for n in (1, 2, 3, 5, 8, 12, 20, 30, 50))))
    for name, _ in ARMS:
        r_t = RATES[name][4]
        if r_t <= 0:
            pr("  %-16s | %s" % (name, "  (0 treated episodes seen -- rate not estimable)"))
            continue
        pr("  %-16s | %s" % (name, "  ".join("%5.0f" % (60.0 * n / r_t) for n in (1, 2, 3, 5, 8, 12, 20, 30, 50))))

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("2c. P(USABLE READ FROM ONE SHORT DRIVE)  --  Poisson on the measured treated-episode rate")
    pr("=" * 150)
    pr("  A 'usable' read needs at least k episodes in the TREATED stratum AND at least k in the UNTREATED stratum")
    pr("  of the SAME drive.  Both counts are modelled Poisson at the measured per-arm rates (independent).")
    from math import exp, factorial

    def p_at_least(lmb, k):
        return 1.0 - sum(exp(-lmb) * lmb ** i / factorial(i) for i in range(k))
    PUSE = {}
    for name, _ in ARMS:
        eng_s, n, nt, r_all, r_t = RATES[name]
        nu = sum(1 for e in STR[name] if e["stratum"] == "UNTREATED")
        r_u = 3600 * nu / max(eng_s, 1e-9)
        pr("\n  %s   (measured: %d treated, %d untreated in %.0f engaged s)" % (name, nt, nu, eng_s))
        pr("    %-12s | %s" % ("drive length", "  ".join("k>=%d" % k for k in (1, 2, 3, 5, 8))))
        rows = {}
        for mins in (5, 10, 15, 20, 30, 60):
            lt, lu = r_t * mins / 60.0, r_u * mins / 60.0
            rows[mins] = [p_at_least(lt, k) * p_at_least(lu, k) for k in (1, 2, 3, 5, 8)]
            pr("    %-12s | %s" % ("%d min eng" % mins, "  ".join("%5.2f" % v for v in rows[mins])))
        PUSE[name] = rows

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("4. THE PARAMETRIC-MODULATION EXPOSURE (the hazard reconcile flagged) -- how often the body crosses idx 32")
    pr("=" * 150)
    pr("  %-16s %5s | %10s %10s %10s | %s" % ("arm", "n ep", "xing/s p50", "p90", "max", "share of episodes with >=1 crossing"))
    XING = {}
    for name, _ in ARMS:
        es = STR[name]
        x = np.array([e["xrate"] for e in es], float)
        if len(x) == 0:
            continue
        XING[name] = [float(np.median(x)), float(np.percentile(x, 90)), float(x.max()), float(np.mean(x > 0))]
        pr("  %-16s %5d | %10.1f %10.1f %10.1f | %.2f" % (
            name, len(x), np.median(x), np.percentile(x, 90), x.max(), float(np.mean(x > 0))))

    # ==============================================================================================
    pr("\n" + "=" * 150)
    pr("5. WOULD A CAVE BIT FIX IT?  Two separate questions -- (a) is the STRATIFICATION mis-measured,")
    pr("   and (b) is the DECAY ESTIMATOR too noisy?  Only (b) is what killed the read above.")
    pr("=" * 150)
    pr("  5a. The stratification is NOT a reconstruction problem.  scalecheck_x4_r62_r63.py re-derived idx")
    pr("      bit-exactly from the image and compared it to the kit's GI.demand_live on the SAME frames:")
    pr("      r62_v289 0.9985, r63_v289 0.9965, r5e_v288 0.9920 EXACT-INTEGER agreement, max |diff| = 1 LSB.")
    pr("      => a cave comparator bit reporting which Kd knot interval is live would replace a 99.7 percent-accurate")
    pr("      reconstruction with a 100 percent measurement.  It buys ~0.3 percent of frames.  It does NOT touch the variance")
    pr("      that made the read impossible.  [EVIDENCE: _scratch/scalecheck_x4_r62_r63.txt]")
    pr("")
    pr("  5b. The variance is in the DECAY ESTIMATOR.  For comparison, the per-episode dispersion of a 100 Hz")
    pr("      COMPARATOR-DUTY statistic (the class the r24 / notch-sign taps already ship) on the same episodes:")
    pr("  %-16s %-10s %5s | %9s %9s %9s | %s" % ("arm", "bit", "n ep", "duty p50", "sd(duty)", "sd/|mean|", "vs sd(ln|gd|) = %.2f" % basepool_l.std(ddof=1)))
    DUTY = {}
    for name, tags in ARMS:
        for bit in (4, 5, 6, 7):
            d = []
            for e in STR[name]:
                g = G[e["tag"]]
                b = g.get("bit%d" % bit)
                if b is None:
                    continue
                d.append(float(np.mean(b[e["a"]:e["b"]])))
            d = np.array(d, float)
            if len(d) < 5 or not np.isfinite(d).all():
                continue
            m, sd = float(np.median(d)), float(d.std(ddof=1))
            DUTY["%s/b%d" % (name, bit)] = [m, sd, len(d)]
            pr("  %-16s %-10s %5d | %9.3f %9.3f %9.3f |" % (name, "0x14A b%d" % bit, len(d), m, sd, sd / max(abs(np.mean(d)), 1e-9)))
    pr("      A duty is bounded in [0,1] and its per-episode sd above is the FULL between-episode spread, including")
    pr("      real operating-point variation.  Compare the decay estimator's sd(ln|gd|) = %.2f, i.e. a x%.0f spread." % (
        basepool_l.std(ddof=1), np.exp(basepool_l.std(ddof=1))))

    json.dump({
        "duty": DUTY,
        "confound": {k: {kk: list(vv) for kk, vv in v.items()} for k, v in CONF.items()},
        "rates": {k: list(v) for k, v in RATES.items()},
        "power_two_arm": {str(k): v for k, v in NEEDED.items()},
        "power_did": {str(k): v for k, v in DID.items()},
        "p_usable": PUSE, "xing": XING,
        "n80_two_arm": n80, "n80_did": ndid,
        "target_ratio": TARGET_RATIO,
        "strata": {name: {"n": len(STR[name]),
                          "TREATED": sum(1 for e in STR[name] if e["stratum"] == "TREATED"),
                          "UNTREATED": sum(1 for e in STR[name] if e["stratum"] == "UNTREATED"),
                          "MIXED": sum(1 for e in STR[name] if e["stratum"] == "MIXED")} for name, _ in ARMS},
        "episodes": [{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                      for k, v in e.items() if k in ("tag", "cls", "t0", "dur", "f0", "env", "gd", "gu",
                                                     "idx_p50", "f_lo", "f_mid", "f_hi", "stratum", "zeta", "xrate")}
                     for e in episodes],
    }, open(os.path.join(SCR, "powerS_row_readability.json"), "w"), indent=1)
    open(os.path.join(SCR, "powerS_row_readability.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
