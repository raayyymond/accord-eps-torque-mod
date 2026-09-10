# -*- coding: utf-8 -*-
"""studies/grind/powerS_sizing_dbit.py -- SIZING THE MINIMUM CAVE BIT FOR ROW S.

powerS_row_readability.py showed the within-drive control fails on ESTIMATOR VARIANCE, not on the
stratum labels, so the "which Kd knot is live" comparator bit does not buy readability.  This script
sizes the bit that WOULD: a threshold comparator on |D|, reported as a duty.

Mechanism (EVIDENCE, from the arithmetic): D = clip(floor(dE * Kd / 8), +-D_CLAMP).  BELOW the clamp
D is exactly proportional to Kd, so Kd 128 -> 96 multiplies |D| by 0.750 and
    duty_S(|D| >= T)  =  duty_base(|D| >= T / 0.750).
The base |D| distribution is taken from the kit's 1 kHz mirror (GI.simulate) over the measured V289
grinding episodes, so the DUTY NUMBERS are mirror-grade (BELIEF); the proportionality is arithmetic.

Agent `powerS` (SUBAGENT, orchestrator `main`), 2026-09-09.  Analysis only.
Run: python powerS_sizing_dbit.py    (writes _scratch/powerS_sizing_dbit.txt beside it)
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
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import grind1_census_v288_r5e as C88          # noqa: E402  registers V288
import wire_0xe4_20hz as WIRE                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402

assert C88 is not None
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
V289_ROUTES = ("r62_v289", "r63_v289")
V282_ROUTES = ("r39", "r3a", "r3c")
V288_TAG = "r5e_v288"
CACHE_P = os.path.join(SCR, "grind1_census_v289_r62_r63_cache.pkl")
V289_IMG = (LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-"
            "NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
CEN.IMG["V289"] = V289_IMG
for _t in V289_ROUTES:
    CEN.CELL_OF[_t] = "V289"
    CEN.GRP[_t] = "V289r1"
SCALE = 96.0 / 128.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    rng = np.random.default_rng(20260909)
    episodes = pickle.load(open(CACHE_P, "rb"))["episodes"]
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288", "V289")}
    tags = V289_ROUTES + (V282_ROUTES[0], V288_TAG)
    G = {t: WIRE.load_route(t, cells[CEN.CELL_OF[t]]) for t in tags}

    pr("=" * 140)
    pr("SIZING THE MINIMUM CAVE BIT FOR ROW S -- a threshold comparator on |D|, read as a duty")
    pr("=" * 140)
    pr("  Kd 128 -> 96 multiplies |D| by %.3f BELOW the D clamp (%d).  duty_S(|D|>=T) = duty_base(|D| >= T/%.3f)." % (
        SCALE, V.D_CLAMP, SCALE))
    pr("  Base |D| taken from the kit's 1 kHz mirror (GI.simulate) over the MEASURED grinding episodes.")
    pr("  [EVIDENCE: the proportionality is the decompiled arithmetic.  BELIEF: the duty values, which are mirror-grade.]")

    PER = {}
    for tag in tags:
        g = G[tag]
        c = cells[CEN.CELL_OF[tag]]
        rows = []
        for e in [x for x in episodes if x["tag"] == tag]:
            try:
                S = GI.simulate(g, e["a"], e["b"], c, kd=128)
            except Exception as ex:                                   # noqa: BLE001
                print("  skip %s %.1f: %s" % (tag, e["t0"], ex), flush=True)
                continue
            n0 = (e["a"] - S["seg"].start) * 10
            n1 = n0 + (e["b"] - e["a"]) * 10
            d = np.abs(S["D"])[n0:n1]
            if len(d) < 50:
                continue
            rows.append(dict(t0=e["t0"], dur=e["dur"], idx=float(np.median(S["idx"][n0:n1])),
                             d=d, drail=float(np.mean(d >= V.D_CLAMP))))
        PER[tag] = rows
        print("simulated %s: %d episodes" % (tag, len(rows)), flush=True)

    pr("\n1. THE |D| DISTRIBUTION IN GRINDING EPISODES (base Kd = 128, 1 kHz mirror)")
    pr("  %-12s %5s | %9s %9s %9s %9s | %s" % ("route", "n ep", "p25 |D|", "p50 |D|", "p75 |D|", "p90 |D|", "D-clamp bind duty"))
    ALLD = {}
    for tag in tags:
        if not PER[tag]:
            continue
        d = np.concatenate([r["d"] for r in PER[tag]])
        ALLD[tag] = d
        pr("  %-12s %5d | %9.0f %9.0f %9.0f %9.0f | %.4f" % (
            tag, len(PER[tag]), *np.percentile(d, [25, 50, 75, 90]), float(np.mean(d >= V.D_CLAMP))))

    pool = np.concatenate([ALLD[t] for t in V289_ROUTES if t in ALLD])
    pr("\n2. THE COMPARATOR, sized so the BASE duty sits near 0.5 (the precision sweet spot for a duty statistic)")
    pr("  %-10s | %-14s %-14s | %-10s %-10s | %s" % (
        "T (raw D)", "duty base", "duty at Kd 96", "abs shift", "rel shift", "note"))
    CAND = {}
    for q in (25, 40, 50, 60, 75, 90):
        T = float(np.percentile(pool, q))
        db = float(np.mean(pool >= T))
        ds = float(np.mean(pool >= T / SCALE))
        CAND[q] = (T, db, ds)
        pr("  %-10.0f | %-14.3f %-14.3f | %-10.3f %-10.3f | T = base p%d" % (T, db, ds, ds - db, ds / max(db, 1e-9) - 1, q))

    pr("\n3. PER-EPISODE PRECISION OF THAT DUTY -- the number that decides readability from ONE episode")
    pr("  For each candidate T: the duty computed per episode, its between-episode sd, and the")
    pr("  one-episode z of the predicted shift (|shift| / sd).  z >= 2 means one episode resolves it.")
    pr("  %-10s | %-9s %-9s %-9s | %-9s %-9s | %s" % (
        "T (raw D)", "duty p50", "sd(duty)", "n ep", "shift", "one-ep z", "episodes for z=2"))
    Z = {}
    for q in (25, 40, 50, 60, 75, 90):
        T, db, ds = CAND[q]
        per = np.array([float(np.mean(r["d"] >= T)) for tg in V289_ROUTES for r in PER.get(tg, [])], float)
        if len(per) < 3:
            continue
        sd = float(per.std(ddof=1))
        shift = ds - db
        z = abs(shift) / max(sd, 1e-9)
        need = max(1, int(np.ceil((2.0 / max(z, 1e-9)) ** 2)))
        Z[q] = [T, db, ds, sd, z, need]
        pr("  %-10.0f | %-9.3f %-9.3f %-9d | %-9.3f %-9.2f | %d" % (T, float(np.median(per)), sd, len(per), shift, z, need))

    pr("\n3b. THE PAIRED ESTIMATOR -- the one that actually works.  The unpaired sd above is dominated by")
    pr("   OPERATING-POINT variation, which cancels if the episode is compared against ITS OWN mirror.")
    pr("   For every episode the mirror is run TWICE on the SAME wire data, Kd 128 and Kd 96, giving two")
    pr("   PREDICTED duties.  The flown bit's measured duty then discriminates the two hypotheses on that")
    pr("   episode alone.  Discriminability = |d96 - d128| / (within-episode binomial SE at N_eff), where")
    pr("   N_eff = N (1-rho)/(1+rho) from the lag-1 autocorrelation of the comparator series at 100 Hz.")
    pr("  %-10s | %-11s %-11s %-11s | %-9s %-9s %-9s | %s" % (
        "T (raw D)", "d128 p50", "d96 p50", "|sep| p50", "N_eff p50", "SE p50", "paired z", "episodes for z=2"))
    PAIR = {}
    for q in (40, 50, 60, 75):
        T = CAND[q][0]
        seps, zs, neffs = [], [], []
        for tg in V289_ROUTES:
            g = G[tg]
            c = cells[CEN.CELL_OF[tg]]
            for e in [x for x in episodes if x["tag"] == tg]:
                try:
                    S128 = GI.simulate(g, e["a"], e["b"], c, kd=128)
                    S96 = GI.simulate(g, e["a"], e["b"], c, kd=96)
                except Exception:                                    # noqa: BLE001
                    continue
                n0 = (e["a"] - S128["seg"].start) * 10
                n1 = n0 + (e["b"] - e["a"]) * 10
                if n1 - n0 < 100:
                    continue
                # decimate the 1 kHz mirror to the 100 Hz frame the tap reports on
                b128 = (np.abs(S128["D"])[n0:n1:10] >= T).astype(float)
                b96 = (np.abs(S96["D"])[n0:n1:10] >= T).astype(float)
                d128, d96 = float(b128.mean()), float(b96.mean())
                sep = abs(d96 - d128)
                N = len(b128)
                x = b128 - b128.mean()
                rho = float(np.dot(x[:-1], x[1:]) / max(np.dot(x, x), 1e-12)) if N > 2 else 0.0
                rho = min(max(rho, 0.0), 0.95)
                neff = N * (1 - rho) / (1 + rho)
                p = 0.5 * (d128 + d96)
                se = float(np.sqrt(max(p * (1 - p), 1e-6) / max(neff, 1.0)))
                seps.append(sep); neffs.append(neff); zs.append(sep / se)
        if len(seps) < 3:
            continue
        seps, zs, neffs = np.array(seps), np.array(zs), np.array(neffs)
        zmed = float(np.median(zs))
        need = max(1, int(np.ceil((2.0 / max(zmed, 1e-9)) ** 2)))
        PAIR[q] = [T, zmed, float(np.median(seps)), float(np.median(neffs)), need]
        pr("  %-10.0f | %-11.3f %-11.3f %-11.3f | %-9.0f %-9.3f %-9.2f | %d" % (
            T, np.nan, np.nan, np.median(seps), np.median(neffs),
            np.median(seps) / max(zmed, 1e-9), zmed, need))
    pr("   (d128/d96 columns are per-episode and vary; the |sep| median is the discriminating quantity.)")

    pr("\n4. THE SAME QUESTION FOR THE DECAY ESTIMATOR, for comparison (from powerS_row_readability.py):")
    pr("  ln|gd| per-episode sd = 1.368 on 174 base episodes; target ln(2.29) = 0.829 => one-episode z = 0.43,")
    pr("  and 120 episodes PER ARM for 80 %% power with a valid test.")

    pr("\n5. WHAT THE BIT COSTS AND WHERE IT GOES")
    pr("  ONE bit on 0x14A byte 4 (b3-b7 are the cave's; b0-b2 are stock Honda).  The comparator is")
    pr("  |D| >= T with T a NEW 2-byte constant, or -- cheaper -- reuse the existing D clamp cell 0xC61B6")
    pr("  as the threshold by comparing against a shifted copy.  The tap already exists on this frame;")
    pr("  the cave must only add a compare and a bit-set.  [BELIEF until a tracer prices the cave.]")
    pr("  CAVEAT (EVIDENCE, arithmetic): a SIGN comparator on D would be BLIND to row S -- scaling Kd")
    pr("  does not change sign(D).  Only a MAGNITUDE comparator moves.  Any design that ships sign(D)")
    pr("  as the row-S instrument ships an uninterpretable null.")

    json.dump({"cand": {str(k): list(v) for k, v in CAND.items()},
               "z": {str(k): v for k, v in Z.items()}, "paired": {str(k): v for k, v in PAIR.items()},
               "scale": SCALE, "d_clamp": int(V.D_CLAMP)},
              open(os.path.join(SCR, "powerS_sizing_dbit.json"), "w"), indent=1)
    open(os.path.join(SCR, "powerS_sizing_dbit.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
