# -*- coding: utf-8 -*-
"""studies/grind/basepick_v290.py -- WHAT BASE DOES V290 SIT ON?  Agent `basepick`, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

THE QUESTION.  Every V290 candidate so far was scored against a V282 revert, because reverting was the
pre-registered response to V289's revert signature.  But V289's notch DID what it was aimed at (18-22 Hz
band emptied, prevalence x34), and reverting hands that 20 Hz mode back.  So the option space is:

  A   V282 + scheduled Kd    (Kd record 0xE511C, X = 0,11,22,32; Y[0..2] = 96, Y[3] = 128)   2 or 6 cal bytes
  A'  same with Y[0..2] = 112                                                                 the gentler dose
  Ap  paramod's Y = [96, 96, 112, 128] -- same Y[0], half the ramp slope above idx 11
  B   V289 + scheduled Kd                                                                     6 cal bytes on V289
  B'  same with 112
  C   V282 + notch 21.5 Hz Q1.5 on the FEEDBACK OPERAND + fb pole 40 Hz (hook 0x28F4C, cave 0xC4C90)
  D   C + the scheduled Kd

THE SCHEDULE IS NOT A FLAT Kd, AND THAT IS THE WHOLE POINT.  The Kp/Kd LERP X axis is the DEMAND INDEX
(reference_accord_kp_kd_schedule_axis_is_the_demand_index; 1 idx LSB = 16.1257 wire 0xE4 counts).  MEASURED
idx populations (reference_accord_demand_index_distribution_on_the_wire, r62/r63/r5e):

    25 m/s cruise             idx p50 = 3      -> Kd = Y[0]        the ring lives here
    all engaged               idx p50 = 5      -> Kd = Y[0]
    grinding episodes         idx p50 = 8/46/37 -> STRADDLES the ramp (this is the honest risk)
    capped step (pkR)         idx p50 = 86-110 -> idx > X[3] = 32 -> Kd = Y[3] = 128, UNCHANGED
    low-speed full-lock turn  idx p50 = 74-123 -> idx > 32        -> Kd = Y[3] = 128, UNCHANGED   (the 7 Hz gate)

So the SMALL-SIGNAL columns (poles, zeta, Ms, min|1+L|, noise, new-peak) must be read at Kd = Y[0], while
the AUTHORITY columns (capped-step pkR, gate73, t90) must be read at Kd = 128 -- the two yardsticks sit
above the top knot.  This file reports BOTH, and marks which is which.  Scoring a scheduled Kd as a flat
Kd 96 (what `design290b`/`reconcile` did) is a factually wrong authority penalty, not a conservative one.

Everything else -- plant family, metrics(), step_lin(), plant_free(), the fb placement -- is `reconcile_v290`'s
and `design290b_candidates`' own machinery, unmodified, so every number is directly comparable.

Run:  python basepick_v290.py            -> _scratch/basepick_v290.txt (+ .json)
      python basepick_v290.py kd         -> the Kd-sweep interaction test only (fast)
"""
import json
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import adv_v290_physics as A              # noqa: E402
import design290b_candidates as D         # noqa: E402
import reconcile_v290 as RC               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ------------------------------------------------------------------------------------------ pole census helpers
BANDS = [(8.0, 12.0), (12.0, 15.0), (15.0, 18.0), (18.0, 22.0), (22.0, 26.0), (26.0, 30.0)]


def poles_pos(el, pl):
    """the closed-loop poles with s.imag > 0 (one per conjugate pair), as (f_Hz, zeta, |z|)."""
    n, d = D.Lpoly(el, pl)
    ch = A.padd(d, n)
    w = np.roots(ch[::-1])
    w = w[np.abs(w) > 1e-12]
    z = 1.0 / w
    s = np.log(z) * D.FS
    m = s.imag > 1e-9
    return s.imag[m] / (2 * np.pi), -s.real[m] / np.abs(s[m]), np.abs(z[m])


def pole_census(el, plants):
    """per 8-30 Hz band: how many of the fits put a closed-loop pole there, and its f / zeta distribution."""
    acc = {b: [] for b in BANDS}
    for pl in plants:
        f, zt, _ = poles_pos(el, pl)
        for ff, zz in zip(f, zt):
            for b in BANDS:
                if b[0] <= ff < b[1]:
                    acc[b].append((float(ff), float(zz)))
    out = []
    for b in BANDS:
        v = acc[b]
        if not v:
            continue
        fs = np.array([x[0] for x in v])
        zs = np.array([x[1] for x in v])
        out.append(dict(band="%.0f-%.0f" % b, n=len(v), frac=len(v) / float(len(plants)),
                        f_med=float(np.median(fs)), z_med=float(np.median(zs)), z_min=float(zs.min()),
                        z_max=float(zs.max())))
    return out


def ring(z, f):
    if not np.isfinite(z) or z <= 0 or not np.isfinite(f) or f <= 0:
        return np.nan, np.nan
    c10 = np.log(10) / (2 * np.pi * z)
    return c10, 1e3 * c10 / f


def agg(el, el0, plants, base0):
    """design290b's own metrics(), aggregated, plus min|1+L| and a 22-35 Hz new-peak column."""
    z, f, ms, vm, pk, dc, pm, wc, gm, t9, s14, s23, s35 = ([] for _ in range(13))
    un = 0
    FG = D.FG
    for k, pl in enumerate(plants):
        m = D.metrics(el, pl, el0)
        b = base0[k]
        z.append(m["z"]); f.append(m["f"]); ms.append(m["Ms"]); vm.append(m["vm"])
        pm.append(m["pm"]); wc.append(m["wc"]); gm.append(m["gm"])
        pk.append(m["pkR"] / b["pkR"]); dc.append(m["dc"] / b["dc"]); t9.append(m["t90"])
        un += int(m["unst"])
        s14.append(m["S1014"] / b["S1014"])
        S, _ = D.Sfun(el, pl, FG)
        S0, _ = D.Sfun(el0, pl, FG)
        mm = (FG >= 22) & (FG <= 35)
        s35.append(float(S[mm].max() / S0[mm].max()))
        s23.append(m["S2230"] / b["S2230"])
    z = np.array(z); pk = np.array(pk)
    kw = int(np.nanargmin(z))
    return dict(z_w=float(z[kw]), f_at_w=float(f[kw]), z_med=float(np.nanmedian(z)), f_med=float(np.nanmedian(f)),
                Ms_w=float(np.nanmax(ms)), vm_w=float(np.nanmin(vm)), pm_w=float(np.nanmin(pm)),
                wc_med=float(np.nanmedian(wc)), gm_w=float(np.nanmin(gm)),
                pkR_med=float(np.median(pk)), pkR_w=float(np.min(pk)), dc_med=float(np.median(dc)),
                t90_med=float(np.nanmedian(t9)), unst=int(un),
                S1014=float(np.nanmax(s14)), S2230=float(np.nanmax(s23)), S2235=float(np.nanmax(s35)))


# ------------------------------------------------------------------------------------------------- the candidates
def kd_cells(base, kd):
    cc = dict(base)
    cc["kd_Y"] = [int(kd)] * 4
    return cc


def notch_fb(c282, fc, Q, fh, kd=None):
    b, aa, _ = D.rbj("notch", fc, Q)
    return RC.ElecP(RC.cellsfb(c282, fh, None, kd), place="fb", sumfilt=[(b, aa)])


def build(c, c282):
    """(key, label, small-signal Elec (Kd = Y[0]), authority Elec (Kd = 128, the schedule's top knot), bytes, class)."""
    R = []

    def add(key, lab, el_ss, el_au, byts, cls, base):
        R.append(dict(key=key, lab=lab, ss=el_ss, au=el_au, bytes=byts, cls=cls, base=base))

    v282 = RC.ElecP(c282)
    v289 = RC.ElecP(c, notch289=True)
    add("V282", "V282 as flown (the revert)", v282, v282, "0", "cal-only", "V282")
    add("V289", "V289 rev 1 as flown (fwd notch 20.04 Q3 + fb 25)", v289, v289, "0", "cave", "V289")

    for tag, y0 in (("", 96), ("'", 112)):
        add("A" + tag, "A%s  V282 + scheduled Kd Y0=%d" % (tag, y0),
            RC.ElecP(kd_cells(c282, y0)), v282, "6 cal", "cal-only", "V282")
    add("Ap", "Ap  V282 + paramod Y=[96,96,112,128]",
        RC.ElecP(kd_cells(c282, 96)), v282, "6 cal", "cal-only", "V282")

    for tag, y0 in (("", 96), ("'", 112)):
        add("B" + tag, "B%s  V289 + scheduled Kd Y0=%d" % (tag, y0),
            RC.ElecP(kd_cells(c, y0), notch289=True), v289, "6 cal on V289", "cave+cal", "V289")

    for fh in (40.0, 50.0):
        add("C%d" % fh, "C   V282 + fb-operand notch 21.5 Q1.5 + fb %.0f Hz" % fh,
            notch_fb(c282, 21.5, 1.5, fh), notch_fb(c282, 21.5, 1.5, fh), "4 cal + cave", "cave", "V282")
        for tag, y0 in (("", 96), ("'", 112)):
            add("D%d%s" % (fh, tag), "D%s   C(fb %.0f) + scheduled Kd Y0=%d" % (tag, fh, y0),
                notch_fb(c282, 21.5, 1.5, fh, y0), notch_fb(c282, 21.5, 1.5, fh, 128),
                "10 cal + cave", "cave+cal", "V282")
    return R


# ------------------------------------------------------------------------------------------------- the Kd sweep
def kd_sweep(c, c282):
    """THE OPTION-B INTERACTION TEST.  D is the loop's lead element; on the V289 base the crossing already
    sits near 16.6 Hz.  Does cutting Kd there pull the crossover DOWN or destabilise it?  Swept on all
    three bases, over the burst-consistent sub-family."""
    pr("")
    pr("=" * 168)
    pr("TASK 1.  THE Kd INTERACTION TEST -- Kd swept on each base, over the burst-consistent SUB family (%d fits)." % len(SUBP))
    pr("         D is the loop's lead element.  wc = highest gain crossover of |L| (median over fits); PM at wc;")
    pr("         GM = worst gain margin; zeta_w / f_at_w = least-damped closed-loop pole 8-30 Hz.")
    pr("=" * 168)
    bases = [("V282 base (no notch, fb 16.53)", c282, False),
             ("V289 base (fwd notch 20.04 Q3, fb 25)", c, True),
             ("C base (fb-operand notch 21.5 Q1.5, fb 40)", c282, "fbnotch")]
    HH = "    %-42s %4s | %6s %6s | %6s %6s | %6s | %5s | %6s %6s | %5s %5s | %s"
    pr(HH % ("base", "Kd", "wc Hz", "PM deg", "z_w", "f@z_w", "z_med", "GM", "Ms_w", "1/|1+L|", "pkR_m", "gate", "unst"))
    rows = []
    for lab, cb, kind in bases:
        pr("    " + "-" * 160)
        for kd in (128, 120, 112, 104, 96, 80, 64):
            if kind == "fbnotch":
                el = notch_fb(cb, 21.5, 1.5, 40.0, kd)
                el0 = RC.ElecP(c282)
            else:
                el = RC.ElecP(kd_cells(cb, kd), notch289=bool(kind))
                el0 = RC.ElecP(c282)
            s = agg(el, el0, SUBP, BSUB)
            pf = D.plant_free(el, el0)
            rows.append(dict(base=lab, kd=kd, gate=pf["gate"], **s))
            pr(HH % (lab if kd == 128 else "", kd,
                     "%.1f" % s["wc_med"], "%+.0f" % s["pm_w"], "%+.3f" % s["z_w"], "%.1f" % s["f_at_w"],
                     "%+.3f" % s["z_med"], "%.2f" % s["gm_w"], "%.1f" % s["Ms_w"], "%.3f" % s["vm_w"],
                     "%.2f" % s["pkR_med"], "%.3f" % pf["gate"], s["unst"]))
    return rows


# --------------------------------------------------------------------------------------------- the decision table
def table(rows):
    pr("")
    pr("=" * 200)
    pr("TASK 2.  THE DECISION TABLE.  SMALL-SIGNAL columns are read at the schedule's Kd = Y[0] (the ring lives at")
    pr("         idx p50 3-5); AUTHORITY columns (pkR, gate73, t90) at Kd = Y[3] = 128, because the capped step")
    pr("         (idx p50 86-110) and the full-lock 7 Hz gate (idx p50 74-123) BOTH sit above the top knot X[3] = 32.")
    pr("         FULL = %d linear-stable-on-V289 fits.  SUB = %d of those also consistent with the MEASURED V289" % (len(FULLP), len(SUBP)))
    pr("         burst decay (zeta_eff 0.02-0.13).  dc is Kd-independent (the D term has no DC gain).")
    pr("=" * 200)
    H = ("  %-46s | %7s %7s | %7s %7s | %6s | %6s | %6s | %6s | %5s %5s | %6s | %5s | %5s | %5s %5s %5s | %4s | %7s %6s | %s")
    pr(H % ("candidate", "zW-FULL", "zM-FULL", "zW-SUB", "zM-SUB", "f@zW", "Ms_w", "m|1+L|", "gate73",
            "pkR_m", "pkR_w", "dc", "t90", "d3.9", "S1014", "S2230", "S2235", "unst", "ring ms", "cycles", "noise/bytes"))
    pr("  " + "-" * 196)
    out = []
    el0 = RC.ElecP(C282)
    for r in rows:
        sF = agg(r["ss"], el0, FULLP, BFULL)
        sS = agg(r["ss"], el0, SUBP, BSUB)
        au = agg(r["au"], el0, SUBP, BSUB) if r["au"] is not r["ss"] else sS
        pf = D.plant_free(r["ss"], el0)
        pfa = D.plant_free(r["au"], el0)
        cyc, ms = ring(sS["z_med"], sS["f_med"])
        cen = pole_census(r["ss"], SUBP)
        rec = dict(key=r["key"], lab=r["lab"], bytes=r["bytes"], cls=r["cls"], base=r["base"],
                   noise=pf["noise"], d39=pf["d39"], dlo=pf["dlo"], ring_ms=ms, ring_cyc=cyc,
                   gate_au=pfa["gate"], gate_ss=pf["gate"], census=cen,
                   **{"F_" + k: v for k, v in sF.items()}, **{"S_" + k: v for k, v in sS.items()},
                   **{"AU_" + k: v for k, v in au.items()})
        out.append(rec)
        pr(H % (r["lab"][:46],
                "%+.3f" % sF["z_w"], "%+.3f" % sF["z_med"], "%+.3f" % sS["z_w"], "%+.3f" % sS["z_med"],
                "%.1f" % sS["f_at_w"], "%.1f" % sS["Ms_w"], "%.3f" % sS["vm_w"], "%.3f" % pfa["gate"],
                "%.2f" % au["pkR_med"], "%.2f" % au["pkR_w"], "%.3f" % au["dc_med"], "%.0f" % au["t90_med"],
                "%+.1f" % pf["d39"], "%.1fx" % sS["S1014"], "%.1fx" % sS["S2230"], "%.1fx" % sS["S2235"],
                sS["unst"], ("%.0f" % ms) if np.isfinite(ms) else "n/a",
                ("%.1f" % cyc) if np.isfinite(cyc) else "n/a", "x%.2f / %s" % (pf["noise"], r["bytes"])))
    return out


def census_print(recs):
    pr("")
    pr("=" * 168)
    pr("TASK 3.  EVERY closed-loop pole 8-30 Hz, banded, over the burst-consistent SUB family (%d fits)." % len(SUBP))
    pr("         TWO OBJECTS ARE IN PLAY: the 18-22 Hz band (the line V282 carries and V289's notch emptied) and")
    pr("         the 15-18 Hz band (the crossing V289 created).  'frac' = share of fits placing a pole in the band.")
    pr("=" * 168)
    for r in recs:
        pr("  %s" % r["lab"])
        for b in r["census"]:
            pr("      %-8s Hz  frac %5.2f  f_med %5.2f  zeta med %+0.3f  [min %+0.3f, max %+0.3f]"
               % (b["band"], b["frac"], b["f_med"], b["z_med"], b["z_min"], b["z_max"]))


def notch_shapes(c):
    pr("")
    pr("=" * 168)
    pr("TASK 4.  WHAT EACH NOTCH ACTUALLY DOES TO THE LOOP GAIN (|N| in dB, Q14-rounded exactly as a build would).")
    pr("=" * 168)
    el289 = RC.ElecP(c, notch289=True)
    b15, a15, q15 = D.rbj("notch", 21.5, 1.5)
    fs = np.array([12.0, 14.0, 16.0, 16.6, 18.0, 20.0, 20.04, 21.5, 24.0, 28.0])
    n289 = np.abs(A.pev(el289.N[0], fs) / A.pev(el289.N[1], fs))
    nC = np.abs(A.pev(b15, fs) / A.pev(a15, fs))
    p289 = np.degrees(np.angle(A.pev(el289.N[0], fs) / A.pev(el289.N[1], fs)))
    pC = np.degrees(np.angle(A.pev(b15, fs) / A.pev(a15, fs)))
    pr("    f Hz   :  " + "  ".join("%7.1f" % f for f in fs))
    pr("    V289 |N| dB : " + "  ".join("%7.1f" % (20 * np.log10(v)) for v in n289))
    pr("    V289 arg    : " + "  ".join("%7.1f" % v for v in p289))
    pr("    C    |N| dB : " + "  ".join("%7.1f" % (20 * np.log10(v)) for v in nC))
    pr("    C    arg    : " + "  ".join("%7.1f" % v for v in pC))
    pr("    C Q14 ints  : b = %s   a = %s" % (q15[0], q15[1]))
    pr("    NOTE: V289's notch is 47.6 dB deep and 41.6 deg of skirt lag at 16 Hz -- that skirt is what spent the")
    pr("          margin at the 15-17 Hz crossing.  C's Q1.5 notch is shallow and its skirt at 16 Hz is far smaller.")


def main():
    global FULLP, SUBP, BFULL, BSUB, C282
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    c, c282 = D.cells()
    C282 = c282
    fam, stab, burst = RC.load_family()
    pr("basepick_v290 -- image %s" % c["path"][:75])
    pr("  V289 cells: fb %d/%d (%.2f Hz)  lag %d/%d  gain %d  Kp %s  Kd %s"
       % (c["fb_a"], c["fb_b"], RC.fb_hz(c), c["lag_a"], c["lag_b"], c["gain"], c["kp_Y"], c["kd_Y"]))
    pr("  V282 cells: fb %d/%d (%.2f Hz)" % (c282["fb_a"], c282["fb_b"], RC.fb_hz(c282)))
    pr("  Kd record 0xE511C  n=4  X = (0, 11, 22, 32)  Y = (128, 128, 128, 128)   [byte-read, both images]")
    pr("  family: %d fits, %d linear-stable on V289, %d burst-consistent" % (len(fam), len(stab), len(burst)))
    FULLP = [D.mkplant(p) for p in stab]
    SUBP = [D.mkplant(p) for p in burst]
    el0 = RC.ElecP(c282)
    t0 = time.time()
    BFULL = [D.metrics(el0, pl, None) for pl in FULLP]
    BSUB = [D.metrics(el0, pl, None) for pl in SUBP]
    pr("  V282 baselines computed in %.0f s" % (time.time() - t0))

    res = {}
    notch_shapes(c)
    if what in ("all", "kd"):
        res["kd_sweep"] = kd_sweep(c, c282)
    if what in ("all", "table"):
        rows = build(c, c282)
        recs = table(rows)
        census_print(recs)
        for r in recs:
            r.pop("el", None)
        res["table"] = recs
    tag = "" if what == "all" else "_" + what
    json.dump(res, open(os.path.join(SCR, "basepick_v290%s.json" % tag), "w"), indent=0, default=float)
    open(os.path.join(SCR, "basepick_v290%s.txt" % tag), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/basepick_v290%s.txt" % tag)


if __name__ == "__main__":
    main()
