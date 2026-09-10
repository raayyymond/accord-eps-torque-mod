# -*- coding: utf-8 -*-
"""studies/grind/reconcile_v290.py -- RECONCILE the two V290 rankings.  Agent `reconcile`, 2026-09-09.
Analysis only: builds nothing, flashes nothing, sends nothing.

WHY THIS FILE EXISTS.  `design290b_candidates.py` (agent design290d) returned a NULL -- 0 of 384 on the joint
(notch, Q, fb pole) solve and 1 of 1152 on the constrained search, that one row being V282 itself.  `adv_v290_null.py`
(agent advnull) returned a candidate.  The structural claim under the disagreement is that design290b scores EVERY
filter in ONE placement: `Elec.__init__` folds `sumfilt` into `self.N`, `bracket()` uses `self.N`, and `bracket()` is
called by BOTH `R()` (the return ratio) and `fwd()` (the reference transfer).  So every row it scored puts the filter
in the command path as well as in the loop.  A filter on the FEEDBACK OPERAND has the SAME return ratio (identical
poles, zeta, Ms, PM, gate73, stability) but is absent from `fwd()`, so it does not spend capped-step authority.

WHAT THIS FILE DOES.  It subclasses design290b's own `Elec` with a `place` switch that is the ONLY difference, re-runs
design290b's OWN two search grids in the feedback placement with design290b's OWN scoring functions (`metrics`,
`step_lin`, `plant_free`, `gate73`, `poles_of`), and then scores one consistent decision table over the same plant
family.  Every number here is therefore directly comparable with `_scratch/design290b_cands.txt`.

Run:  python reconcile_v290.py            -> _scratch/reconcile_v290.txt (+ .json)
      python reconcile_v290.py table      -> the decision table only (skips the two grid re-runs)
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ----------------------------------------------------------------------------------------------- the ONE difference
class ElecP(D.Elec):
    """design290b's Elec with a placement switch.

    place='fwd'  -- identical to design290b's Elec in every respect (the filter is on the loop output S).
    place='fb'   -- the same filter multiplies the FEEDBACK OPERAND instead.  R() is untouched (a product of the
                    same blocks, so the return ratio and every pole/margin/gate derived from it are IDENTICAL);
                    fwd() drops the filter, because a feedback-path element is not in the reference transfer.
    Only valid with g == 0 and sbp is None (the post-lag terms genuinely ARE forward-path elements)."""

    def __init__(self, c, place="fwd", **kw):
        self.place = place
        super().__init__(c, **kw)
        if place == "fb":
            assert not self.g and self.sbp is None, "fb placement is only defined for pure loop filters"

    def fwd(self):
        if self.place == "fwd":
            return super().fwd()
        hn, hd = self.Hlag                                    # bracket() with N removed: g == 0, sbp is None
        num = A.pmul([0.0, 1.0], self.C[0], hn) * self.K * self.fade
        den = A.pmul(self.C[1], hd)
        if self.prefilter:
            num, den = A.pmul(num, self.prefilter[0]), A.pmul(den, self.prefilter[1])
        return num, den


def cellsfb(c282, fh=None, kp=None, kd=None):
    cc = dict(c282)
    if fh is not None:
        cc["fb_a"], cc["fb_b"] = D.dc_held_pole(fh)
    if kp is not None:
        cc["kp_Y"] = [int(kp)] * 5
    if kd is not None:
        cc["kd_Y"] = [int(kd)] * 4
    return cc


def fb_hz(c):
    """invert dc_held_pole: the -3 dB pole the integer a encodes."""
    return -D.FS * np.log(c["fb_a"] / 1024.0) / (2 * np.pi)


# ------------------------------------------------------------------------------------------------------- the family
def load_family():
    fam = json.load(open(os.path.join(SCR, "design290b_family.json")))
    stab = [p for p in fam if p["z289"] >= D.Z289_STABLE]
    burst = [p for p in stab if 0.02 <= p["z289"] <= 0.13]   # advnull's sub-family: consistent with the MEASURED
    return fam, stab, burst                                  # V289 burst decay zeta_eff 0.02-0.13


def score_over(el, el0, plants, base0, want_peaks=False):
    """design290b's own metrics(), aggregated.  base0 = per-plant metrics of el0 (V282), computed once."""
    z, f, ms, pk, dc, pm, t9, s14, s23, un = [], [], [], [], [], [], [], [], [], 0
    for k, pl in enumerate(plants):
        m = D.metrics(el, pl, el0)
        b = base0[k]
        z.append(m["z"]); f.append(m["f"]); ms.append(m["Ms"]); pm.append(m["pm"])
        pk.append(m["pkR"] / b["pkR"]); dc.append(m["dc"] / b["dc"]); t9.append(m["t90"])
        un += int(m["unst"])
        if want_peaks:
            s14.append(m["S1014"] / b["S1014"]); s23.append(m["S2230"] / b["S2230"])
    z = np.array(z); pk = np.array(pk)
    kw = int(np.nanargmin(z))
    r = dict(z_w=float(z[kw]), f_at_w=float(f[kw]), z_med=float(np.nanmedian(z)), f_med=float(np.nanmedian(f)),
             Ms_w=float(np.nanmax(ms)), pm_w=float(np.nanmin(pm)), pkR_med=float(np.median(pk)),
             pkR_w=float(np.min(pk)), dc_med=float(np.median(dc)), t90_med=float(np.nanmedian(t9)), unst=int(un))
    if want_peaks:
        r["S1014"] = float(np.nanmax(s14)); r["S2230"] = float(np.nanmax(s23))
    return r


def ring(z, f):
    """time for the ring to fall to 10 % of its start, in cycles and ms, at its own pole frequency."""
    if not np.isfinite(z) or z <= 0 or not np.isfinite(f) or f <= 0:
        return np.nan, np.nan
    c10 = np.log(10) / (2 * np.pi * z)
    return c10, 1e3 * c10 / f


# ---------------------------------------------------------------------------------------- TASK 1: the two re-runs
def rerun_joint(stab, c, c282):
    """design290b's section-4 grid, EXACTLY (np.arange(15.0,22.51,0.5) x Q x fb = 384), in the FEEDBACK placement.
    design290b used sub = fits[::max(1,len(fits)//120)]; with 121 stable fits that is all 121."""
    pr("")
    pr("=" * 152)
    pr("TASK 1a.  design290b's SECTION-4 JOINT SOLVE (notch f, Q, fb pole), RE-RUN IN THE FEEDBACK PLACEMENT")
    pr("          Same grid, same fits, same scoring functions.  design290b's forward-placement answer: 0 of 384 feasible.")
    pr("=" * 152)
    sub = stab[:: max(1, len(stab) // 120)]
    plants = [D.mkplant(p) for p in sub]
    el0 = ElecP(c282)
    base0 = [D.metrics(el0, pl, None) for pl in plants]
    grid = [(float(fc), float(Q), float(fh))
            for fc in np.arange(15.0, 22.51, 0.5) for Q in (1.5, 2.0, 3.0, 4.0)
            for fh in (16.53, 20.0, 25.0, 30.0, 35.0, 40.0)]
    t0 = time.time()
    res = []
    for fc, Q, fh in grid:
        b, aa, _ = D.rbj("notch", fc, Q)
        el = ElecP(cellsfb(c282, fh), place="fb", sumfilt=[(b, aa)])
        pf = D.plant_free(el, el0)
        s = score_over(el, el0, plants, base0)
        s.update(fc=fc, Q=Q, fh=fh, gate=pf["gate"], noise=pf["noise"])
        res.append(s)
    res.sort(key=lambda r: -r["z_w"])
    ok = [r for r in res if r["gate"] <= 1.01 and r["pkR_med"] >= 0.95 and r["unst"] == 0]
    pr("    %d combos on %d fits in %.0f s" % (len(res), len(sub), time.time() - t0))
    pr("    %-30s | %6s %6s | %6s | %6s %5s | %6s | %5s %5s | %5s | %s" % (
        "notch f / Q / fb pole", "z_min", "z_med", "PM_w", "f_med", "Ms", "gate73", "pkR_m", "pkR_w", "noise", "unst"))
    for r in res[:14]:
        pr("    %5.1f Hz  Q%.1f  fb %4.1f Hz        | %6.3f %6.3f | %+6.1f | %6.1f %5.2f | %6.3f | %5.2f %5.2f | %5.2f | %d" % (
            r["fc"], r["Q"], r["fh"], r["z_w"], r["z_med"], r["pm_w"], r["f_med"], r["Ms_w"], r["gate"],
            r["pkR_med"], r["pkR_w"], r["noise"], r["unst"]))
    pr("    FEASIBLE (gate<=1.01, pkR_med>=0.95, all stable): %d of %d   [design290b, forward placement: 0 of 384]" % (len(ok), len(res)))
    if ok:
        b = ok[0]
        pr("    best feasible by worst-case zeta: %.1f Hz Q%.1f fb %.1f Hz -- z_w %+.3f, z_med %+.3f, gate %.3f, pkR_med %.2f, noise x%.2f" % (
            b["fc"], b["Q"], b["fh"], b["z_w"], b["z_med"], b["gate"], b["pkR_med"], b["noise"]))
    return res, ok


def rerun_row9(stab, c, c282):
    """design290b's section-10 constrained search, EXACTLY the same 1152 combos, in the FEEDBACK placement.
    design290b used sub = fits[::max(1,len(fits)//60)] -> 61 fits ('1152 combos evaluated on 61 fits')."""
    pr("")
    pr("=" * 152)
    pr("TASK 1b.  design290b's SECTION-10 CONSTRAINED SEARCH, RE-RUN IN THE FEEDBACK PLACEMENT")
    pr("          design290b's forward-placement answer: 1 of 1152 passed the authority gates, and that row was V282.")
    pr("=" * 152)
    sub = stab[:: max(1, len(stab) // 60)]
    plants = [D.mkplant(p) for p in sub]
    el0 = ElecP(c282)
    base0 = [D.metrics(el0, pl, None) for pl in plants]
    LEADS = [None, (8.0, 40.0, None), (10.0, 50.0, None), (12.0, 36.0, None), (8.0, 40.0, 40.0), (10.0, 50.0, 50.0)]
    combos = []
    for kp in (248, 220, 200, 160):
        for kd in (128, 96):
            for nf in (None, (16.7, 3.0), (17.5, 2.0), (18.5, 1.5), (20.04, 3.0), (18.0, 1.0)):
                for fh in (16.53, 25.0, 35.0):
                    for fl in (5.05, 8.0, 12.0):
                        for ld in LEADS:
                            for g in (0.0, -1 / 8):
                                if nf is None and g != 0.0:
                                    continue
                                if ld is not None and (nf is not None or g != 0.0):
                                    continue
                                combos.append((kp, kd, nf, fh, fl, ld, g))
    t0 = time.time()
    res = []
    for kp, kd, nf, fh, fl, ld, g in combos:
        cc = cellsfb(c282, fh, kp, kd)
        if abs(fl - 5.05) > 0.01:
            cc["lag_a"], cc["lag_b"] = D.dc_held_lag(fl)
        sf = None
        if nf:
            b, aa, _ = D.rbj("notch", nf[0], nf[1]); sf = [(b, aa)]
        if ld:
            b, aa = D.leadlag(*ld); sf = [(b, aa)]
        # the post-lag term g is a genuine FORWARD-path element; those rows stay forward-placed
        place = "fwd" if (g or sf is None) else "fb"
        el = ElecP(cc, place=place, sumfilt=sf, g=g)
        pf = D.plant_free(el, el0)
        s = score_over(el, el0, plants, base0)
        s.update(name="Kp%d Kd%d %s fb%.0f lag%.1f%s%s [%s]" % (
            kp, kd, ("nt%.1fQ%.1f" % nf) if nf else "no-notch", fh, fl,
            (" lead%.0f/%.0f%s" % (ld[0], ld[1], "+lpf" if ld[2] else "")) if ld else "",
            (" n*%+.3f" % (-g)) if g else "", place), gate=pf["gate"], noise=pf["noise"])
        res.append(s)
    hard = [r for r in res if r["gate"] <= 1.01 and r["pkR_w"] >= 0.95 and r["unst"] == 0]
    pr("    %d combos on %d fits in %.0f s.  Passing the AUTHORITY gates (pkR_WORST >= 0.95, gate73 <= 1.01, all stable): %d"
       % (len(res), len(sub), time.time() - t0, len(hard)))
    pr("    Of those, PM_worst >= 40 deg: %d      zeta_worst >= 0.08: %d"
       % (sum(1 for r in hard if r["pm_w"] >= 40.0), sum(1 for r in hard if r["z_w"] >= 0.08)))
    HH = "    %-52s | %6s %6s | %6s | %5s | %6s | %5s %5s | %5s | %5s | %s"
    pr(HH % ("combo", "z_min", "z_med", "PM_w", "f_med", "gate73", "pkR_m", "pkR_w", "dc", "Ms", "unst"))
    for lab, rows, key in (("best worst-case zeta among rows PASSING the authority gates", hard, "z_w"),
                           ("best PM among rows PASSING the authority gates", hard, "pm_w")):
        pr("    -- %s --" % lab)
        for r in sorted(rows, key=lambda r: -r[key])[:10]:
            pr(HH % (r["name"][:52], "%+.3f" % r["z_w"], "%+.3f" % r["z_med"], "%+.1f" % r["pm_w"], "%.1f" % r["f_med"],
                     "%.3f" % r["gate"], "%.2f" % r["pkR_med"], "%.2f" % r["pkR_w"], "%.3f" % r["dc_med"],
                     "%.2f" % r["Ms_w"], r["unst"]))
    return res, hard


# ------------------------------------------------------------------------------------------- TASK 2: the decision table
def build_rows(c, c282):
    """(label, Elec, placement, bytes, class).  Every notch row is scored in BOTH placements where that is meaningful."""
    R = []

    def add(lab, el, place, byts, cls):
        R.append(dict(lab=lab, el=el, place=place, bytes=byts, cls=cls))

    add("V282 (the revert)", ElecP(c282), "-", "0 (revert)", "cal-only")
    add("V289 as flown (notch 20.04 Q3 on S + fb 25)", ElecP(c, notch289=True), "forward", "4 cal + cave", "cave")

    # advnull's rows, feedback placement, and the same element forward for contrast
    for fc, Q, fh in ((21.5, 1.5, 50.0), (21.5, 1.5, 40.0)):
        b, aa, _ = D.rbj("notch", fc, Q)
        add("advnull  notch %.1f Q%.1f + fb %.0f Hz  [FB]" % (fc, Q, fh),
            ElecP(cellsfb(c282, fh), place="fb", sumfilt=[(b, aa)]), "feedback", "4 cal + cave", "cave")
        add("   same element FORWARD (what design290b scored)",
            ElecP(cellsfb(c282, fh), sumfilt=[(b, aa)]), "forward", "4 cal + cave", "cave")

    # RE-AIMED at the 16-17 Hz crossing modenat2's reversal identifies
    for fc in (16.0, 16.5, 17.0, 17.5):
        for Q in (1.5, 2.0, 3.0):
            for fh in (40.0, 50.0):
                b, aa, _ = D.rbj("notch", fc, Q)
                add("RE-AIM   notch %.1f Q%.1f + fb %.0f Hz  [FB]" % (fc, Q, fh),
                    ElecP(cellsfb(c282, fh), place="fb", sumfilt=[(b, aa)]), "feedback", "4 cal + cave", "cave")

    # cal-only Kd rows (V282 fb pole)
    for kd in (112, 96, 80):
        add("Kd %d (cal-only, V282 fb pole)" % kd, ElecP(cellsfb(c282, None, None, kd)), "-", "2 cal", "cal-only")
    add("Kd 120 + fb 18 Hz (design290b's best feasible cell)",
        ElecP(cellsfb(c282, 18.0, None, 120)), "-", "4 cal", "cal-only")
    add("fb 25 Hz alone (V282 + V289's fb pole, no notch)", ElecP(c), "-", "2 cal", "cal-only")
    return R


def decision_table(c, c282, stab, burst):
    pr("")
    pr("=" * 190)
    pr("TASK 2.  ONE DECISION TABLE -- every genuinely distinct V290 candidate, scored consistently with design290b's")
    pr("         own metrics() / step_lin() / plant_free() over the SAME plant family.")
    pr("   zeta  = least-damped closed-loop pole 8-30 Hz.  FULL = the %d linear-stable-on-V289 fits;" % len(stab))
    pr("   SUB   = the %d of those also consistent with the MEASURED V289 burst decay (zeta_eff 0.02-0.13)." % len(burst))
    pr("   gate73 = 7 Hz strong-turn gate (<= 1.01 required).  pkR = capped-step peak rate vs V282 (>= 0.95 required).")
    pr("   dc = steady-state authority vs V282 (x1.00 required).  noise = rms|R| 30-500 Hz into the motor vs V282.")
    pr("   S1014 / S2230 = worst new-sensitivity-peak ratio vs V282 in 10-14 / 22-35 Hz.  ring = time to 10 %% at the median fit.")
    pr("=" * 190)
    plF = [D.mkplant(p) for p in stab]
    plS = [D.mkplant(p) for p in burst]
    el0 = ElecP(c282)
    bF = [D.metrics(el0, pl, None) for pl in plF]
    bS = [D.metrics(el0, pl, None) for pl in plS]
    rows = build_rows(c, c282)
    H = ("  %-50s %-8s | %7s %7s | %7s %7s | %6s | %5s %5s | %5s | %6s | %5s | %5s | %5s %5s | %4s | %6s %6s | %s")
    pr(H % ("candidate", "place", "zW-FULL", "zM-FULL", "zW-SUB", "zM-SUB", "gate73", "pkR_m", "pkR_w", "dc",
            "t90 ms", "Ms_w", "noise", "S1014", "S2230", "unst", "ring ms", "cycles", "bytes"))
    pr("  " + "-" * 186)
    out = []
    t0 = time.time()
    for r in rows:
        el = r["el"]
        pf = D.plant_free(el, el0)
        sF = score_over(el, el0, plF, bF, want_peaks=True)
        sS = score_over(el, el0, plS, bS, want_peaks=True)
        cyc, ms = ring(sF["z_med"], sF["f_med"])
        rec = dict(lab=r["lab"], place=r["place"], bytes=r["bytes"], cls=r["cls"], gate=pf["gate"], noise=pf["noise"],
                   ring_ms=ms, ring_cyc=cyc, **{"F_" + k: v for k, v in sF.items()}, **{"S_" + k: v for k, v in sS.items()})
        out.append(rec)
        pr(H % (r["lab"][:50], r["place"],
                "%+.3f" % sF["z_w"], "%+.3f" % sF["z_med"], "%+.3f" % sS["z_w"], "%+.3f" % sS["z_med"],
                "%.3f" % pf["gate"], "%.2f" % sF["pkR_med"], "%.2f" % sF["pkR_w"], "%.3f" % sF["dc_med"],
                "%.0f" % sF["t90_med"], "%.1f" % sF["Ms_w"], "%.2f" % pf["noise"],
                "%.1fx" % sF["S1014"], "%.1fx" % sF["S2230"], sF["unst"],
                ("%.0f" % ms) if np.isfinite(ms) else "n/a", ("%.1f" % cyc) if np.isfinite(cyc) else "n/a", r["bytes"]))
    pr("  scored %d rows in %.0f s" % (len(rows), time.time() - t0))
    return out


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    c, c282 = D.cells()
    fam, stab, burst = load_family()
    pr("reconcile_v290 -- image %s" % c["path"][:70])
    pr("  V289 cells: fb %d/%d (%.2f Hz)  lag %d/%d  gain %d  Kp %s  Kd %s" % (
        c["fb_a"], c["fb_b"], fb_hz(c), c["lag_a"], c["lag_b"], c["gain"], c["kp_Y"][0], c["kd_Y"][0]))
    pr("  V282 cells: fb %d/%d (%.2f Hz)" % (c282["fb_a"], c282["fb_b"], fb_hz(c282)))
    pr("  family: %d fits, %d linear-stable on V289 (zeta289 >= %.3f), %d of those also burst-consistent (0.02-0.13)"
       % (len(fam), len(stab), D.Z289_STABLE, len(burst)))

    res = {}
    if what in ("all", "task1"):
        jres, jok = rerun_joint(stab, c, c282)
        r9, hard = rerun_row9(stab, c, c282)
        res["joint_fb"] = jres[:40]
        res["joint_fb_feasible"] = jok[:40]
        res["row9_fb_hard"] = sorted(hard, key=lambda r: -r["z_w"])[:40]
    if what in ("all", "table", "task2"):
        res["table"] = decision_table(c, c282, stab, burst)

    tag = "" if what == "all" else "_" + what
    json.dump(res, open(os.path.join(SCR, "reconcile_v290%s.json" % tag), "w"), indent=0, default=float)
    open(os.path.join(SCR, "reconcile_v290%s.txt" % tag), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/reconcile_v290%s.txt" % tag)


if __name__ == "__main__":
    main()
