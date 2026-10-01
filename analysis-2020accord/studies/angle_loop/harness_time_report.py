# -*- coding: utf-8 -*-
"""harness_time_report.py -- writes reports/HARNESS-TIME-2026-09-30.md from the cached results of harness_time.py
(_scratch/angle_loop/harness-time/*.json).  Every number in the tables is read from those caches; the narrative
sections are fixed text written after reading them (2026-09-30) and say so.  ANALYSIS ONLY."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness_time as H  # noqa: E402

NARR = HERE / "_harness_time_narrative.md"     # optional hand-written sections, inserted verbatim if present


def _load_all():
    d1, d2 = H.load("flat_sweep.json"), H.load("refined_sweep.json")
    rows = d1["rows"] + d2["rows"]
    m2 = {(r["name"], r["v"]): r for r in d2["results"]}
    res = [dict(r, metrics={k: r["metrics"][k] + m2[(r["name"], r["v"])]["metrics"][k] for k in r["metrics"]})
           for r in d1["results"]]
    fin = H.load("final.json")
    rob = H.load("final_robust.json")
    return rows, res, d1["rows"], fin, rob


def f(x, nd=2):
    if x is None:
        return "-"
    x = float(x)
    if not np.isfinite(x):
        return "inf"
    return ("%%.%df" % nd) % x


def gate_str(g, i):
    return " ".join(("**%s**" % k) if not g[k][i] else k for k in H.GATES if not g[k][i]) or "ALL PASS"


def plant_table(o):
    fam = VP_family()
    o.write("| speed m/s | J T/(deg/s^2) | b T/(deg/s) | k T/deg | Fc T | Fs T | spring sat deg | transport ms | 2Fs/k deg |\n")
    o.write("|---|---|---|---|---|---|---|---|---|\n")
    for v in H.SPEEDS:
        p = fam["nominal"].at(v)
        o.write("| %g | %.2f | %.2f | %.1f | %.1f | %.1f | %.1f | %d | %.2f |\n" % (v, p.J, p.b, p.k, p.Fc, p.Fs, p.sat, p.tau_ms,
                                                                            2 * p.Fs / p.k))


def VP_family():
    import v294_plant as VP
    return VP.family()


def feas_table(o, rows, res):
    for strict in (True, False):
        T, sc = H.flat_scores(rows, res, strict=strict)
        o.write("\n**%s reading** (%d configurations; a cell counts the configurations that pass that gate at that speed)\n\n"
                % ("STRICT" if strict else "LINE-ONLY", len(rows)))
        o.write("| speed | " + " | ".join(H.GATES) + " | **all gates** | best configuration (cost-ranked) |\n")
        o.write("|---" * (len(H.GATES) + 3) + "|\n")
        for v in H.SPEEDS:
            g = sc[v]["gates"]
            ap = sc[v]["allpass"]
            b = int(np.argmin(np.where(ap, sc[v]["cost"], 1e9 + sc[v]["cost"])))
            fails = [k for k in H.GATES if not g[k][b]]
            o.write("| %g | " % v + " | ".join(str(int(g[k].sum())) for k in H.GATES) + " | **%d** | %s%s |\n" % (
                int(ap.sum()), rows[b]["label"], "" if not fails else " (fails: %s)" % ", ".join(fails)))


def landscape(o, rows, res, combos):
    T, sc = H.flat_scores(rows, res, strict=False)

    def find(kp, Ki, ICL, DB, Kd):
        for i, r in enumerate(rows):
            if (r["kpY"][0] == kp and len(set(r["kpY"])) == 1 and r["Ki"] == Ki and (Ki == 0 or (r["ICL"] == ICL and r["DB"] == DB))
                    and (r["kdY"][0] if r["d_rate"] else 0) == Kd and (r["oa"], r["ob"]) == (992, 507)):
                return i
        return None
    for (Ki, ICL, DB, Kd) in combos:
        o.write("\n**Ki %d, ICL %d, DB %d, Kd %d%s** -- per cell: tracking gain 0.2 Hz / 0.5 Hz · hold ratio · steady error deg · "
                "T 5-30 Hz rms in holds / in sinusoids (counts) · stick-slip events (sinusoid dwell-then-jump + hold slips)\n\n"
                % (Ki, ICL, DB, Kd, "" if Kd == 0 else " (edit 5)"))
        o.write("| speed | " + " | ".join("Kp %d" % k for k in H.KP_SWEEP) + " |\n")
        o.write("|---" * (len(H.KP_SWEEP) + 1) + "|\n")
        for v in H.SPEEDS:
            rh, st, s02, s05, ssm = [T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm")]
            cells = []
            for kp in H.KP_SWEEP:
                i = find(kp, Ki, ICL, DB, Kd)
                if i is None:
                    cells.append("-")
                    continue
                thh = max(rh["T_hf"][i], st["T_hf"][i])
                ths = max(s02["T_hf"][i], s05["T_hf"][i], ssm["T_hf"][i])
                ev = int(s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i])
                unstable = thh > 20 or (max(rh["hunt_p2p"][i], st["hunt_p2p"][i]) >= 1 and max(rh["hunt_rev"][i], st["hunt_rev"][i]) >= 4)
                cells.append(("UNSTABLE (T hf %.0f) " % thh if unstable else "") + "%s/%s · %s · %s · %s/%s · %d" % (
                    f(s02["track_gain"][i]), f(s05["track_gain"][i]), f(rh["hold_ratio"][i]), f(rh["ess_turn"][i]),
                    f(thh, 1), f(ths, 1), ev))
            o.write("| %g | " % v + " | ".join(cells) + " |\n")


def scorecard(o, rows, results, strict, names=None):
    T = {(r["name"], float(r["v"])): {k: np.array(v, float) for k, v in r["metrics"].items()} for r in results}
    kp = np.array([max(r["kpY"]) for r in rows])
    kd = np.array([max(r["kdY"]) if r["d_rate"] else 0 for r in rows])
    out = {}
    for v in H.SPEEDS:
        g, ap, c = H.per_speed_score(T, v, kp, kd, strict=strict)
        out[v] = (g, ap)
    o.write("| candidate | " + " | ".join("%g m/s" % v for v in H.SPEEDS) + " | speeds passing |\n")
    o.write("|---" * (len(H.SPEEDS) + 2) + "|\n")
    for i, r in enumerate(rows):
        cells = []
        n = 0
        for v in H.SPEEDS:
            g, ap = out[v]
            n += int(ap[i])
            cells.append("PASS" if ap[i] else "fail: " + ", ".join(k for k in H.GATES if not g[k][i]))
        o.write("| %s | " % r["label"] + " | ".join(cells) + " | **%d / 7** |\n" % n)
    return T


def detail(o, rows, T):
    keys = [("ess", "rh", "ess_turn", 2), ("hold", "rh", "hold_ratio", 3), ("tg 0.2", "s02", "track_gain", 3),
            ("tg 0.5", "s05", "track_gain", 3), ("ph 0.5 deg", "s05", "phase_deg", 1), ("+-1deg fit", "ssm", "fit_gain", 2),
            ("dj ev", None, None, 0), ("max snap", None, None, 2), ("stick %", "ssm", "stick_pct", 0),
            ("T hf hold", None, None, 1), ("T hf sin", None, None, 1), ("hunt p2p", None, None, 2),
            ("step ov %", "st", "overshoot_pct", 0), ("settle s", "st", "settle_s", 2), ("peak T", "rh", "peakT", 0),
            ("rail %", "rh", "rail_pct", 1), ("hard16", "rh", "hard16", 2), ("hard16 ref", "rh", "hard16_ref", 2)]
    for i, r in enumerate(rows):
        o.write("\n**%s**\n\n" % r["label"])
        o.write("| m/s | " + " | ".join(k[0] for k in keys) + " |\n")
        o.write("|---" * (len(keys) + 1) + "|\n")
        for v in H.SPEEDS:
            rh, st, s02, s05, ssm = [T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm")]
            cells = []
            for lab, sc_, m, nd in keys:
                if lab == "dj ev":
                    val = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
                elif lab == "max snap":
                    val = max(s02["dj_maxjump"][i], s05["dj_maxjump"][i], ssm["dj_maxjump"][i])
                elif lab == "T hf hold":
                    val = max(rh["T_hf"][i], st["T_hf"][i])
                elif lab == "T hf sin":
                    val = max(s02["T_hf"][i], s05["T_hf"][i], ssm["T_hf"][i])
                elif lab == "hunt p2p":
                    val = max(rh["hunt_p2p"][i], st["hunt_p2p"][i])
                else:
                    val = T[(sc_, v)][m][i]
                cells.append(f(val, nd))
            o.write("| %g | " % v + " | ".join(cells) + " |\n")


def safety(o, rows, T):
    o.write("| candidate | m/s | override (fade-only) peak T / overshoot deg / swing deg | override latch: overshoot no-e6 / e6 deg "
            "| sentinel L, 0xC63F6=16: peak T / s / excursion deg | sentinel L, =328 | sentinel R, =16: peak T / excursion | "
            "disengage excursion: send measured / send 0 |\n")
    o.write("|---|---|---|---|---|---|---|---|\n")
    for i, r in enumerate(rows):
        for v in H.SPEEDS:
            of, ol, oe = T[("ov_fade", v)], T[("ov_latch", v)], T[("ov_latch_e6", v)]
            a, b_, c_, d_ = T[("sen_L16", v)], T[("sen_L328", v)], T[("sen_R16", v)], T[("sen_R328", v)]
            dm, dz = T[("dis_meas", v)], T[("dis_zero", v)]
            o.write("| %s | %g | %d / %s / %s | %s / %s | %d / %s / %s | %d / %s / %s | %d / %s | %s / %s |\n" % (
                r["label"].split()[0], v, of["lurch_peakT"][i], f(of["lurch_overshoot"][i]), f(of["lurch_swing"][i]),
                f(ol["lurch_overshoot"][i]), f(oe["lurch_overshoot"][i]),
                a["sen_peakT"][i], f(a["sen_dur_s"][i]), f(a["sen_excursion"][i], 1),
                b_["sen_peakT"][i], f(b_["sen_dur_s"][i]), f(b_["sen_excursion"][i], 1),
                c_["sen_peakT"][i], f(c_["sen_excursion_abs"][i], 1), f(dm["dis_excursion"][i]), f(dz["dis_excursion"][i])))


def robust(o, rob):
    rows = rob["rows"]
    kp = np.array([max(r["kpY"]) for r in rows])
    kd = np.array([max(r["kdY"]) if r["d_rate"] else 0 for r in rows])
    by = {}
    for r in rob["results"]:
        by.setdefault(r["member"], []).append(r)
    o.write("| member | " + " | ".join(r["label"].split()[0] for r in rows) + " |\n")
    o.write("|---" * (len(rows) + 1) + "|\n")
    for mem in rob["members"]:
        res = by.get(mem, [])
        T = {(r["name"], float(r["v"])): {k: np.array(v, float) for k, v in r["metrics"].items()} for r in res}
        cells = []
        for i in range(len(rows)):
            n_ok, fl = 0, []
            for v in H.SPEEDS:
                # tracking-only scenarios: build a reduced gate set (stable, stick, deadzone, track, hold)
                rh, st, s02, s05, ssm = [T[(nm, v)] for nm in ("rh", "st", "s02", "s05", "ssm")]
                stable = not (rh["diverged"][i] or st["diverged"][i]) and not (
                    max(rh["hunt_p2p"][i], st["hunt_p2p"][i]) >= 0.2 and max(rh["hunt_rev"][i], st["hunt_rev"][i]) >= 2) \
                    and max(rh["T_hf"][i], st["T_hf"][i]) <= H.HF_LINE
                ev = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
                dz = rh["ess_turn"][i] <= max(0.3, 0.03 * H.A_TURN[v]) and ssm["fit_gain"][i] >= 0.8
                tr = (v < 8) or (min(s02["track_gain"][i], s05["track_gain"][i]) >= 0.95 and max(s02["track_gain"][i], s05["track_gain"][i]) <= 1.05)
                ho = (v < 8) or rh["hold_ratio"][i] >= 0.9
                ok = stable and ev == 0 and dz and tr and ho
                n_ok += int(ok)
                if not ok:
                    fl.append("%g:%s" % (v, "".join(c for c, b in (("U", not stable), ("S", ev > 0), ("D", not dz), ("T", not tr), ("H", not ho)) if b)))
            cells.append("%d/7 %s" % (n_ok, " ".join(fl)))
        o.write("| %s | " % mem + " | ".join(cells) + " |\n")


def outer_pi(o, rob):
    rows = rob["rows"]
    T = {(r["name"], float(r["v"])): {k: np.array(v, float) for k, v in r["metrics"].items()} for r in rob["results_pi"]}
    o.write("| candidate | m/s | tg 0.2 / 0.5 (inner, th vs th_sp received) | hold | T hf hold / sin | stick-slip events |\n")
    o.write("|---|---|---|---|---|---|\n")
    for i, r in enumerate(rows):
        for v in H.SPEEDS:
            rh, st, s02, s05, ssm = [T[(nm, v)] for nm in ("rh", "st", "s02", "s05", "ssm")]
            ev = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
            o.write("| %s | %g | %s / %s | %s | %s / %s | %d |\n" % (r["label"].split()[0], v, f(s02["track_gain"][i]), f(s05["track_gain"][i]),
                                                                  f(rh["hold_ratio"][i]), f(max(rh["T_hf"][i], st["T_hf"][i]), 1),
                                                                  f(max(s02["T_hf"][i], s05["T_hf"][i], ssm["T_hf"][i]), 1), int(ev)))


def hf20_table(o, rows):
    o.write("| candidate | max Kp | max Kd | P part | D part | |(P+D)/x| at 20 Hz | vs V295 3.85 |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        kp, kd = max(r["kpY"]), (max(r["kdY"]) if r["d_rate"] else 0)
        o.write("| %s | %d | %d | %.2f | %.2f | %.2f | %s |\n" % (r["label"].split()[0], kp, kd, H.hf20(kp), kd / 8.0, H.hf20(kp, kd),
                                                              "<=" if H.hf20(kp, kd) <= 3.85 else "**ABOVE**"))


def icl_table(o, rows, res):
    T = H.table(res, rows)

    def find(kp, Ki, ICL, DB, Kd):
        for i, r in enumerate(rows):
            if (r["kpY"][0] == kp and len(set(r["kpY"])) == 1 and r["Ki"] == Ki and r["ICL"] == ICL and r["DB"] == DB
                    and (r["kdY"][0] if r["d_rate"] else 0) == Kd and (r["oa"], r["ob"]) == (992, 507)):
                return i
    o.write("| family | ICL | " + " | ".join("%g m/s" % v for v in H.SPEEDS) + " |\n")
    o.write("|---" * (len(H.SPEEDS) + 2) + "|\n")
    for kp, kd in ((2500, 16), (1500, 0), (1200, 24)):
        for icl in (1024, 4096, 10240):
            i = find(kp, 1024, icl, 0, kd)
            if i is None:
                continue
            o.write("| Kp %d Ki 1024 DB 0 Kd %d | %d | " % (kp, kd, icl) + " | ".join(
                "%s deg / %d T / hold err %s" % (f(T[("ov_fade", v)]["lurch_overshoot"][i]), T[("ov_fade", v)]["lurch_peakT"][i],
                                                f(T[("rh", v)]["ess_turn"][i])) for v in H.SPEEDS) + " |\n")


def payoff_table(o):
    fin = H.load("final.json")
    p1, p2 = H.load("payoff.json"), H.load("payoff2.json")

    def tab(results, opts=None):
        T = {}
        for r in results:
            if opts is not None and r.get("opts", "{}") != opts:
                continue
            T[(r["name"], float(r["v"]))] = {k: np.array(v, float) for k, v in r["metrics"].items()}
        return T
    base = tab(fin["results"])
    bl = [r["label"].split()[0] for r in fin["rows"]]
    variants = [("in-place (0.1 deg setpoint and angle, 100 Hz hold)", None, None)]
    for d in (p1, p2):
        for op in d["variants"]:
            variants.append((op, d, op))
    for name in ("FLAT-T", "ANGLE-1", "SPEED-1"):
        o.write("\n**%s** -- T rms in 5-30 Hz during the three sinusoids (max) · stick-slip events · tracking 0.2/0.5 Hz\n\n" % name)
        o.write("| operand / setpoint option | " + " | ".join("%g m/s" % v for v in H.SPEEDS) + " |\n")
        o.write("|---" * (len(H.SPEEDS) + 1) + "|\n")
        for lab, d, op in variants:
            if d is None:
                T, i = base, bl.index(name)
            else:
                T = tab(d["results"], op)
                i = [r["label"].split()[0] for r in d["rows"]].index(name)
            cells = []
            for v in H.SPEEDS:
                rh, st, s02, s05, ssm = [T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm")]
                ev = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
                cells.append("%s · %d · %s/%s" % (f(max(s02["T_hf"][i], s05["T_hf"][i], ssm["T_hf"][i]), 1), int(ev),
                                                   f(s02["track_gain"][i]), f(s05["track_gain"][i])))
            o.write("| %s | " % lab + " | ".join(cells) + " |\n")


def guard_table(o):
    d = H.load("guard_a2.json")
    rows = d["rows"]
    T = {(r["name"], float(r["v"])): {k: np.array(v, float) for k, v in r["metrics"].items()} for r in d["results"]}
    o.write("| candidate / guard | m/s | override fade-only: overshoot deg | override latch: overshoot deg | sentinel L 16: peak T / s > 50 / "
            "excursion deg | sentinel L 328 | sentinel R 16: peak T | disengage excursion: measured / 0 |" + NL)
    o.write("|---|---|---|---|---|---|---|---|" + NL)
    for i, r in enumerate(rows):
        for v in H.SPEEDS:
            of, ol = T[("ov_fade", v)], T[("ov_latch", v)]
            a, b_, c_ = T[("sen_L16", v)], T[("sen_L328", v)], T[("sen_R16", v)]
            dm, dz = T[("dis_meas", v)], T[("dis_zero", v)]
            o.write("| %s | %g | %s | %s | %d / %s / %s | %d / %s / %s | %d | %s / %s |" % (
                r["label"], v, f(of["lurch_overshoot"][i]), f(ol["lurch_overshoot"][i]), a["sen_peakT"][i], f(a["sen_dur_s"][i]),
                f(a["sen_excursion"][i], 1), b_["sen_peakT"][i], f(b_["sen_dur_s"][i]), f(b_["sen_excursion"][i], 1),
                c_["sen_peakT"][i], f(dm["dis_excursion"][i]), f(dz["dis_excursion"][i])) + NL)


NL = chr(10)
NARR = {}
NARR["HEAD"] = r"""# HARNESS-TIME 2026-09-30 -- the zero-cave ANGLE LOOP, closed on the identified plant, exact at 1 kHz

**Agent:** `harness-time` (subagent). **Analysis only:** nothing was built, flashed or sent; no fork or firmware file was
touched; no Ghidra state was changed (one read-only `disassemble_bytes dry_run` of `0x29CF6-0x29EE4` on the V294 program).
**Script:** `analysis-2020accord/studies/angle_loop/harness_time.py` (this report's tables are written by
`harness_time_report.py` from its caches in `_scratch/angle_loop/harness-time/`). Fixed seeds, no network.
**Image:** V295 cal, hash-checked by `lane_mirror_v295.load_cal()` (sha256 `5c044d65...`), with the angle-loop cal edits
a `0xC63E8` = 0, b `0xC63EA` = 8192, C `0xC62E6` = 65535 and the in-place code edits (1)-(4) [+ (5) where Kd > 0, (6) where named].
Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**.

## 0. Bottom line

1. **The harness is exact where it claims to be.** EVIDENCE: the vectorised lane equals the byte-exact scalar mirror
   `lane_mirror_v295.lane_tick` (angle switches, pol = -1) on **144,000 ticks, 0 mismatches**, over 12 random configurations and
   every branch (skips, input bail, 0x7FFF sentinel, sign-hold gate blocks, driver fade, rail, int32 wraps, scalar and vector
   setpoint paths). Karnopp stick (39 < Fs 40 stays stuck, 41 moves), linear static gain and damped frequency to 0.001, the
   record's V295 20 Hz comparator (3.85) reproduced. **No int32 wrap occurred in any of the 1,000+ runs.**
2. **Without a cave the goal is NOT met.** EVIDENCE (sim, nominal family, 615 cal configurations incl. the brief's full grid):
   - **FLAT Kp** -- the best flat set (Kp 2500, Ki 1024, ICL 4096, DB 0, Kd 16) passes 12.5-30 m/s but at **3-8 m/s it is a
     3.9 Hz limit cycle of 10-14 deg peak-to-peak with ~1,900-2,700 T counts peak-to-peak** (section 5). Any flat Kp that is stable at
     3-8 m/s (Kp <= 1200-1500 with Kd 24-28) under-tracks at speed (0.2 Hz gain 0.72-0.89 at 19-30 m/s).
     **0 of 615 configurations pass every gate at 3 m/s under the strict reading; at most 4 of 7 speeds pass for any flat set
     (line-only).**
   - **ANGLE-INDEXED Kp** (cal-only, 5 knots on idx = |theta_sp|/1.61 deg) -- **at most 3/7 speeds** (line-only), 0-1/7 strict:
     |theta_sp| does not identify speed. A small-angle command at 3-8 m/s gets the highway knot and stick-slips or goes unstable
     (8 m/s: 4.6-4.8 counts rms 5-30 Hz in the holds); lowering the small-angle knot to the low-speed value breaks highway
     tracking (0.5 Hz gain 1.11-1.13 at 26-30 m/s, PI peaking).
3. **A SPEED schedule of Kp AND Kd is the first thing a cave must buy.** EVIDENCE (sim): SPEED-1 (Kp 1500/1200/1800/1500/2500
   at 3/5/12.5/19/26 m/s, Kd 28/24/24/0 at 3/5/8/12.5 m/s, Ki 1024, ICL 4096, DB 0) passes **6/7 speeds** under the line-only
   reading on the nominal plant; 8 m/s misses only the 0.5 Hz tracking gain (1.061 vs <= 1.05) by PI peaking -- curing that
   needs Ki scheduled too (no in-place Ki schedule exists). **BELIEF, needs a trace:** the Kp and Kd LERPs could be re-keyed on
   speed with two more in-place edits inside the map LERP that edit (4) makes dead (section 11) -- no cave.
4. **No candidate is robust across the identified family.** EVIDENCE (sim): SPEED-1 passes 6/7 on nominal, `tau0`, `+mode20Hz`,
   5/7 on `J_lo`, `+mode13Hz`, but only **1-3/7 on `J_hi`, `J_hi2`, `b_lo`, `b_hi`, `F_lo`, `F_hi`, `tau6`, `ms_free`, and 0/7 on
   `light_b`**. The failures are stick-slip at 3-5 m/s and the +-5 % tracking window. The full-resolution cave option (below)
   does **not** buy this margin back. The record's rule applies: a gain tuned to one member is not supported by this drive.
5. **TEXTURE: the 0.1 deg setpoint and the 0.1 deg feedback, times Kp, put 2-7 counts rms of 5-30 Hz torque into ordinary
   lane-keeping motion.** EVIDENCE (arithmetic + sim): one angle LSB is **0.01 x Kp T counts** (25 counts at Kp 2500; selftest 2:
   Kp 1000 gives 100 T per deg). SPEED-1 carries 4.1-4.6 counts rms at 26-30 m/s during a +-0.9 deg / 0.2 Hz correction.
   Neither fix alone removes it (0.025 deg setpoint: 2.3; 8x finer angle: 3.0; 1 kHz fresh operands: 4.2). **Only all four
   together -- a 0.025 deg setpoint, 1 kHz setpoint interpolation, an 8x finer angle and fresh 1 kHz operands -- bring it to
   0.6 counts** (section 10). Whether 4 counts rms is felt is UNKNOWN (no N.m scale exists in the kit; BELIEF threshold 2 counts,
   the record's quiet-cruise tap residual is 0.66-0.87 counts per 5 Hz band). Under the STRICT reading only 19 m/s passes for
   SPEED-1.
6. **Safety.** EVIDENCE (sim, lane-level): the **0xE4 fault sentinel** with the angle loop rails the lane for the whole ramp-down
   when it was already pushing that way: **0xC63F6 = 16: 2,100-2,290 T for 2.01 s, a 30-180 deg wheel excursion** (36.6 deg at
   26 m/s); **0xC63F6 = 328: ~1,100 T for 0.10 s, 2.1-6.6 deg**. Pushing the other way, the sign-hold gate blocks it (T <= 272).
   (The brief's "sp = 16384" is wrong: with edit (4) the sentinel loads as sp = **32767**, EVIDENCE `lane_mirror_v295 _claims`;
   P rails either way.) A parallel trace (`docs/traces/TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md`, NOT
   re-verified here) finds the pulse IS delivered and proposes **Fix A2, `0x29A56` `da 05` -> `b2 05`** (the PID runs iff ramp != 0
   AND request == 1). Simulated here (BELIEF on the byte semantics, EVIDENCE on the arithmetic): **A2 removes the pulse at every
   speed -- peak T = the pre-fault hold torque decaying (69-326 counts), <= 0.06 s above 50 counts, 0.0 deg excursion** -- and equals
   edit (6) on the latch path; it does not touch the reachable fade-only override. **The override release lurch is set by ICL, not by edit (6):** after a 1 s override holding the wheel 1.5 deg off
   at 26 m/s, ICL 1024 / 4096 / 10240 give 0.24 / 1.69 / 3.55 deg of overshoot past the setpoint; ICL 1024 costs 0.6-3.4 deg of
   hold error at 3-19 m/s. Edit (6) acts only on the latch path (STEER_STATUS 4/7, never seen engaged in the record) and halves
   that overshoot at 26-30 m/s (1.1-1.2 -> 0.5 deg).

**Verdict for the brief's question:** the goal's dead-zone / stick-slip and tracking criteria are **not met WITHOUT a cave** (flat or
angle-indexed Kp, Ki + ICL as the bound), on any reading. **WITH a speed schedule** they are met at 6 of 7 speeds on the nominal
plant (line-only reading), at 1 of 7 under the strict texture reading, and robustly on none. **Do not fly any of these as a
flight candidate.** FLAT-T in particular is a 3.9 Hz, +-5-7 deg oscillation below 8 m/s.
"""

NARR["SEC1"] = r"""
## 1. What the harness simulates

```
fork (100 Hz)            th_sp(t) = scenario reference, 100 Hz ZOH (outer = 'ff', stock LatControlAngle is a feedforward of
                         the planner's angle; nothing is fed back, so the 60 ms round trip does not act)
                         outer = 'pi' (section 8 only): th_sp = th_ref + c, c += (10 ms / 1.0 s) * (th_ref - th_wire[k-6]),
                         th_wire = the 0x14A angle ~60 ms old -- a stand-in for the path-level loop (BELIEF on its form)
                         inactive (disengage): sends the measured angle th_wire[k-6] (or 0 in 'dis_zero')
0xE4 -> FUN_00052676     raw = -round(10 th_sp); gp-0x69ae = clamp(-4 raw, +-16384); fault: 0x7FFF   (frame on tick % 10 == 0, BELIEF)
LKAS lane, 1 kHz         LaneVec == lane_mirror_v295.lane_tick(x_src='angle', fb_op='sum', sp_src='69ae', d_src 'E'|'rate',
                         i_reset_on_ramp0), pol = gp-0x6752 = -1, every cal LE from the V295 image, angle-loop cals a/b/C
                         E = 16 (th_sp - th) ; I, P (Kp LERP on idx), D, fade f, sum clamp, output lag 5.05 Hz, sign-hold gate,
                         x ramp, x 5346/32768, lane clamp 3072 -> T = gp-0x6b38 (rail 2461)
engage SM                ramp gp-0x69b0 / gp-0x6806 / gp-0x6805 per scenario: engaged 0x8000; disengage and fault -0xC63F6/tick;
                         override latch -0xC63F4 (328)/tick with the request held; re-engage +0xC63F8 (33)/tick
transport                2 ms (nominal member), u = -T  (T counts, + = left)
plant, 10 kHz sub-steps  J th'' + b th' + k sat tanh(th/sat) + Fc sgn(th') = u (+ hand), Karnopp: stuck while th' == 0 and
                         |u - spring| <= Fs; optional collocated two-mass mode (stress members)
sensors (slot 4)         gp-0x6a00 = round(10 th) (0.1 deg quantiser, BELIEF on its exact staircase -- the firmware is
                         ceil(linear) + trunc(VGR correction) on 1/32-LSB motor counts); gp-0x6a56 = round(8 (th[n]-th[n-3])/3 ms)
                         + N(0, 1.93 counts) (the record's standstill floor; the 3 ms former is the record's BELIEF);
                         BOTH sampled on tick % 10 == 4 AFTER the lane ran -> the lane sees a 100 Hz hold, age 1-10 ms
```

**Exactness evidence** (`python harness_time.py --selftest`, output verbatim):
"""

NARR["SEC3"] = r"""
## 3. Scenarios, metrics and the gates

Turn amplitude A per speed (deg of wheel): the brief's 90 / 30 / 3 at 3 / 8 / 26 m/s; interpolated at a similar lateral
acceleration elsewhere: **3: 90, 5: 50, 8: 30, 12.5: 12, 19: 5, 26: 3, 30: 2.5** (BELIEF on "hand-sized").

| scenario | what | length |
|---|---|---|
| `rh` ramp-and-hold | 0 -> +A (ramp 1 s; 2 s at 5 m/s; 3 s at 3 m/s), hold 3 s, -> -A, hold 3 s, -> 0, hold 2 s | 12.5-20.5 s |
| `s02`, `s05` | lane-keeping sinusoid +-0.3 A (27 / 15 / 9 / 3.6 / 1.5 / 0.9 / 0.75 deg) at 0.2 and 0.5 Hz, scored after the first cycle | 13 / 9.2 s |
| `ssm` | the straight-road correction: +-1 deg at 0.3 Hz at every speed | 10.3 s |
| `st` | step 0 -> A/2 and a 2.5 s hold | 3 s |
| `ov_fade` | hold A/2; driver grabs (hand 2000 T/deg, 30 T/(deg/s)) and pulls the wheel to 0 over 0.3 s, holds 1 s, releases; driver-torque word ramps to 2400 (fade at its 76/256 floor); request held; ramp stays 0x8000 | 6.8 s |
| `ov_latch`, `ov_latch_e6` | the same with the override LATCH: ramp -328/tick to 0 with the request held, +33/tick after release; without / with edit (6) | 6.8 s |
| `sen_L16`, `sen_L328`, `sen_R16`, `sen_R328` | hold +-A/2, then the 0xE4 fault sentinel (gp-0x69ae = 0x7FFF, request 0xFF, act 0, ramp -0xC63F6/tick) with 0xC63F6 = 16 or 328 | 6 s |
| `dis_meas`, `dis_zero` | hold A/2, then request drop (ramp -16/tick); the fork sends the measured angle / sends 0 | 5.5 s |

**Gates (per speed).** `stable`: no divergence, no hunting in the holds (theta p2p >= 0.2 deg with >= 2 reversals), and T rms in
5-30 Hz during the holds <= 2.0 counts (a lane-made LINE). `texture`: T rms 5-30 Hz during the three sinusoids <= 2.0 counts.
`stick`: zero stick-slip events -- the dwell-then-jump detector on the sinusoids (a 0.10 s-smoothed |rate| < 0.25 deg/s for
>= 100 ms while the reference moved >= 0.1 deg, then a snap to the next dwell >= max(2x the reference's change, 0.2 deg)) plus
slips inside the holds (stuck >= 100 ms, then >= 0.1 deg of motion). `deadzone`: hold error <= max(0.3 deg, 3 % of A) and the
+-1 deg correction executed (fit gain >= 0.8). `track` (>= 8 m/s): tracking gain (slope of the 100 Hz wire angle on the received
setpoint) in 0.95-1.05 at 0.2 AND 0.5 Hz. `hold` (>= 8 m/s): min hold ratio over the two turns >= 0.90. `hf20`: the record's
|(P+D)/x| at 20 Hz <= V295's 3.85. **STRICT** = all gates; **LINE-ONLY** = texture reported but not gated.
The goal's "<= V282" terms (dwell-then-jump, 1.6-3 Hz hard-turn energy) cannot be referenced in this sim (V282 is a rate loop
under the fork's torque controller, not simulated); the harness gates stick-slip at ZERO events and reports the 1.6-3 Hz energy
against the reference trajectory's own (BELIEF: zero events in a noise-free sim is a necessary, not a sufficient, condition).
"""

NARR["FEAS"] = r"""
The brief's grid (6 Kp x {Ki 0; Ki 256/1024 x ICL 1024/4096/10240 x DB 0/1/4} x Kd {0, 8, 16, 32} = 456) plus a refinement
(159: Kd 20-28 with Kp 1200-2000 at low speed, Kp 1800-3000 with Ki 512-2048 at speed, and a diagnostic output-lag pole of 10 / 20 Hz
-- a STRUCK lever in the record, BUILD-LINEAGE V287 "fires Honda's oscillation detector", run only to see what binds). The
lag-pole variants did **not** rescue 3-8 m/s (hold slips up to 13, hunting 0.2-23 deg) -- the 5 Hz output pole is not the
binding element (EVIDENCE, `refined_sweep.json`). Kd 32 always fails `hf20` (D alone is 4.0 > 3.85).
"""

NARR["LAND"] = r"""
Reading the landscape (EVIDENCE, sim): **without D, Kp >= 1500 is a ~4 Hz limit cycle at 3-8 m/s** (3.9 Hz measured on FLAT-T) (T 5-30 Hz 16-500 counts rms);
**Kp <= 900 is stable there but leaves a 5-10 deg hold error (P-only) or stick-slips (with I)**; at 19-30 m/s the P-only hold ratio
is 0.39-0.91 and only Ki ~1024 with Kp ~2500 tracks within +-5 %; **at Kp >= 4000 the highway holds limit-cycle on the angle LSB**
(1 LSB, 17-21 reversals per 1.5 s, T 5-30 Hz 6-14 counts). The binding pair is low-speed stability/stick-slip against highway
tracking, which no single (flat) gain satisfies.
"""

NARR["CANDS"] = r"""
Seven candidates were built from the sweeps and run through every scenario at every speed (`final.json`):
FLAT-T / FLAT-S are the best flat sets under the line-only / strict readings; FLAT-L is the 3 m/s winner flown flat;
ANGLE-1/2/3 are cal-only |theta_sp| schedules (knots at idx 0/3/7/18/31 = 0/5/12/30/50 deg) with the low-angle knot at the
highway (2500) or the low-speed (1500) value and Kd 24 or 28; SPEED-1/2 key Kp and Kd on gp-0x6a5e >> 8 (4 km/h per count;
3/5/8/12.5/19/26/30 m/s = keys 2/4/7/11/17/23/27), Ki 1024 / 640.
"""

NARR["CANDS2"] = r"""
**The best cal set per schedule type** (the cells as they would be written; record addresses read LE from the V295 image:
Kp = `0xCB994[7]` -> record `0xE5378` (count 5, X at `0xE537A`, Y at `0xE5384`; V295: X 0/68/112/136/208, Y 960 flat), Kd =
`0xCB7D4[7]` -> record `0xE511C` (count 4, X at `0xE511E`, Y at `0xE5126`; V295 Y 0). Common to all: a `0xC63E8` 0, b `0xC63EA`
8192, C `0xC62E6` 65535, edits (1)-(4) (+ (5) for Kd > 0), DCL `0xC61B6` 10240 when Kd > 0, and **`0xC63F6` 16 -> 328** for the
sentinel (section 6):

| schedule type | Kp record X / Y | Kd record X / Y | Ki `0xC63E6` | ICL `0xC61BA` | DB `0xC62E4` | nominal speeds passing (line-only / strict) |
|---|---|---|---|---|---|---|
| FLAT (line-only best) | any / 2500 flat | any / 16 flat | 1024 | 4096 | 0 | 4 / 0 -- 3.9 Hz limit cycle at 3-8 m/s |
| FLAT (strict best) | any / 500 flat | any / 16 flat | 256 | 10240 | 0 | 2 / 2 -- under-tracks at >= 12.5 m/s (0.5 Hz gain 0.17-0.80) |
| ANGLE-INDEXED (ANGLE-1) | idx 0/3/7/18/31 / 2500/1500/1800/1200/1200 | any / 24 flat | 1024 | 4096 | 0 | 3 / 0 |
| SPEED (SPEED-1; key = gp-0x6a5e >> 8) | 2/4/11/17/23 / 1500/1200/1800/1500/2500 | 2/4/7/11 / 28/24/24/0 | 1024 | 4096 | 0 | 6 / 1 |
| FULL per-speed cave (any gain per speed) | -- | -- | per speed | per speed | per speed | 7 / 4 (the per-speed bests in section 4) |

**What the two scorecards say.** No flat and no angle-indexed set passes more than 4/7 (line-only) or 2/7 (strict).
SPEED-1 is the only candidate that passes every speed band but one under the line-only reading. Lowering Ki to 640 (SPEED-2) to
remove the 8 m/s peaking breaks 3-8 m/s (stick-slip) and 19-30 m/s (tracking 0.86-0.91): **Ki is the one gain the speed
schedule cannot reach in place, and it is the one 8 m/s needs**.
"""

NARR["DETAIL"] = r"""
Columns: `ess` hold error at the end of the turns (deg); `hold` min hold ratio; `tg` tracking gain at 0.2 / 0.5 Hz; `ph 0.5` the
fitted phase of the wheel at 0.5 Hz (deg, negative = lag); `+-1deg fit` fitted gain on the +-1 deg correction; `dj ev` stick-slip
events (all detectors); `max snap` largest dwell-then-jump snap (deg); `stick %` frames stuck while the +-1 deg reference moves;
`T hf hold / sin` T rms 5-30 Hz in the holds / sinusoids (counts); `hunt p2p` angle p2p in the last 1.5 s of the holds; `step ov %`
and `settle s` of the A/2 step (band max(5 %, 0.2 deg)); `peak T`, `rail %` of `rh`; `hard16` 1.6-3 Hz wheel-rate rms over `rh`
(deg/s) and the reference's own (`hard16 ref`).
"""

NARR["SAFETY"] = r"""
EVIDENCE (sim, lane level). Columns per speed: the release lurch of a 1 s override with the fade at its floor (the reachable
case on this car: STEER_STATUS was measured identically 0 engaged, kit memory `accord-the-authority-ramp-five-rates`); the
override LATCH variant without / with edit (6); the 0xE4 fault sentinel with 0xC63F6 = 16 and 328 while holding a LEFT turn
(the lane pushing the sentinel's way) and a RIGHT turn; the disengage excursion (the wheel relaxing toward centre as the lane
fades -- a "send 0" fork is neutralised by the sign-hold gate, the two columns differ by <= 5 deg at 3 m/s and <= 0.1 deg at speed).

"""

NARR["SAFETY2"] = r"""
**The override lurch is an ICL question** (EVIDENCE, flat sweep; cells = overshoot past the setpoint after release, its peak T,
and the same set's turn-hold error):

"""

NARR["SAFETY3"] = r"""
Reading: the lurch is P (the full position error returns at release -- 45 deg at 3 m/s) plus the integrator wound behind the fade
(the fade multiplies the whole sum, not the accumulator). A small ICL removes the wound part at speed and costs the low-speed hold;
**an ICL that depends on speed, or an I that bleeds on driver torque, is a cave** (the trace's section 3.6). BELIEF: the fork
should also send the measured angle while the driver overrides and rate-limit back to the plan afterwards; that removes the P part.
The sentinel result does not depend on the tuning (P rails for any Kp >= 30): **0xC63F6 16 -> 328 cuts it from 2 s / 30-180 deg to
0.1 s / 2-7 deg** and also shortens every normal disengage to 0.1 s (the hold torque then drops in 0.1 s -- the dis columns
above are with 16).

### 6.1 Fix A2 of the parallel sentinel trace (`0x29A56` bne -> be; run iff ramp != 0 AND request == 1), simulated

EVIDENCE (sim, `guard_a2.json`; the guard's byte semantics are the parallel trace's, BELIEF here). Same scenarios, stock guard
versus A2, 0xC63F6 = 16 except where named:

"""

NARR["SAFETY4"] = r"""
Reading: with A2 the sentinel never reaches P (request 0xFF != 1), the lane skips, I is zeroed and the 5.05 Hz output lag decays
the pre-fault torque in ~0.1 s; a request drop does the same, so "send 0 vs send measured" stops mattering (identical columns) and
the wheel relaxes as the lane releases. **A2 is the better sentinel fix than 0xC63F6 = 328** (which still delivers ~1,100 T for
0.1 s, 2-7 deg). It does nothing for the fade-only override (request held, ramp full) -- that lurch stays an ICL question.
"""

NARR["ROBUST"] = r"""
Reading (EVIDENCE, sim): the in-place candidates are tuned on the nominal member and lose 3-6 speed bands on the stiffer-inertia,
lower-damping, higher/lower-friction and 6 ms-delay members; `light_b` (the PRIOR world, BELIEF) fails everywhere. Most failures are
`S` at 3-5 m/s and `T` (the +-5 % window) at 8-30 m/s. The 13 / 20 Hz two-mass stress modes cost little (SPEED-1 5-6/7).

**7.1 The same with the full-resolution cave option** (0.025 deg setpoint + 1 kHz interpolation + 8x angle + fresh 1 kHz operands,
`robust_cave.json`): it does **not** buy robustness back (SPEED-1 2-4/7 on the off-nominal members).

"""

NARR["OUTER"] = r"""
Reading (EVIDENCE within the stand-in, BELIEF on the stand-in itself): closing an integrating outer loop on the 60 ms-old wire
angle leaves tracking and hold intact but **adds stick-slip events at <= 12.5 m/s for every candidate** (SPEED-1: 4 / 7 / 3 / 2 at
3 / 5 / 8 / 12.5 m/s, against 0 open) -- two integrators against static friction. The fork side should not integrate angle error
at low speed.
"""

NARR["HF20"] = r"""
EVIDENCE (arithmetic, `hf20()`; selftest 5 reproduces V295's 3.85): the angle loop's P costs Kp x 6.2e-4 per x count at 20 Hz
(Kp 2500: 1.55), so P is never the 20 Hz problem; D on the 100 Hz rate costs Kd/8 and in quadrature caps Kd at ~28 with Kp 2500.
This comparator omits the 100 Hz hold and the output stage, common to every build compared (the record's form).
"""

NARR["PAYOFF"] = r"""
## 10. What a cave buys: the texture, operand by operand

EVIDENCE (sim, nominal member, `payoff.json` / `payoff2.json`). Options: `ang_mult` = the lane's angle at 0.1/ang_mult deg with
b = 8192/ang_mult (r26 = 16 theta unchanged; the +-12000 input gate then caps |theta| at 1200/ang_mult deg -- 150 deg at x8);
`fresh` = angle and rate operands refreshed every tick (gp-0x69ca / gp-0x6abe class) instead of held by slot 4; `sp_fine` = the
setpoint at 0.025 deg (what the handler's `shl 2` discards; needs the fork to send 4x finer and the handler not to multiply,
BELIEF); `sp_interp` = the setpoint ramped across each 10 ms frame at 1 kHz (V288's class of cave; one frame of delay).
"""

NARR["PAYOFF2"] = r"""
Reading: at 19-30 m/s the texture is **setpoint quantisation and feedback quantisation together**: the finer setpoint alone removes
~45 %, the finer angle alone ~30 %, the fresh operand alone ~0; all four together leave 0.6 counts. At 3 m/s it is neither: 6-7 counts remain under every option -- that is the
plant's own stick-slip transients against the 76-count low-speed friction (EVIDENCE: identical across operand options).
The fresh 1 kHz operand alone shrinks FLAT-T's 3-8 m/s limit cycle (T hf 200 -> 63-79 counts, hunting 10-14 -> 1-1.6 deg) but
does not stabilise it.
"""

NARR["TAIL"] = r"""
## 11. Leads, caveats and what would change the verdict

**Lead (BELIEF, needs a trace before anyone relies on it): a speed schedule without a cave.** From the Ghidra listing of
`0x29CF6-0x29EE4` (V294 program = V295 code, read-only dry-run disassembly): the Kp LERP is keyed by `r7` (`zxh r7` at
`0x29DE8`), the Kd LERP by `r22` (`mov r7,r22 ; zxb r22` at `0x29D10`, moved to `r13` at `0x29E92`). With edit (4) the map LERP at
`0x29CFC-0x29D68` computes only `r13` (the map Y), which edit (4) makes dead. So replacing `mov 0xc9a88,r16` (6 bytes at
`0x29CFC`) by `ld.bu -0x6a5d[gp],r7` (the high byte of the speed word, 4 km/h per count) + `br 0x29d10`, and `sld.hu 0x2,ep,r10`
at `0x29D18` by `br 0x29d6a`, would key BOTH schedules on speed with 8 bytes in place. Unverified: the odd-displacement `ld.bu`
encoding, branch targets into `0x29D02-0x29D18`, liveness of `ep/r6/r10/r16/r2` on the new path (they appear to be rewritten
before use at `0x29D6E`, `0x29D9C`, `0x29DCC` -- BELIEF), the readers of `gp-0x674B` / `gp-0x697A` (they would carry speed>>8),
and the speed word's behaviour on a voter fault (slews to 80 km/h, `gp-0x67f4` = 0). The harness's SPEED-1/2 runs are exactly
this edit's arithmetic (`key = 'speed'`; selftest 6).

**Caveats (each would move numbers, none is known to flip the verdict):**
- The plant is the r71b identification: J is identified only at 0-5 m/s, b and friction at speed carry the estimator's bias,
  and **the 0-5 m/s friction CI is +-129 counts** (V294-PLANT-IDENT-r71b.md). Every low-speed number here rests on it.
- Nothing above ~8 Hz is identified; the 13 / 20 Hz modes are stress members only.
- The angle quantiser is uniform (BELIEF: the firmware staircase is 0.1 deg steps with an occasional 2-count step near centre
  where the VGR correction increments -- it can only add texture).
- The rate former (3 ms window) and its sampling inside slot 4 are the record's BELIEF; the 0xE4 RX phase (tick % 10 == 0) is not
  traced.
- The driver in the override scenario is a stiff position source; the driver-torque word is scripted (no N.m scale exists).
- The outer loop is either a pure feedforward or a 1 s integrator stand-in; the real path-level loop is not modelled.
- The texture threshold (2 counts rms) is a BELIEF; the operator scores symptoms.
- "<= V282" terms of the goal are not computable here (V282 is not simulated).

## 12. Reproduce

```
cd analysis-2020accord/studies/angle_loop
python harness_time.py --selftest        # ~20 s
python harness_time.py --all             # selftest, sweep, refined, final(+robust, outer), payoff, payoff2, robust-cave,
                                         # guard-a2, report (~35 min with 9 worker processes on this PC)
python harness_time_report.py            # rewrite this report from the caches
```
Caches: `_scratch/angle_loop/harness-time/{selftest_out.txt, flat_sweep, refined_sweep, final, final_robust, payoff, payoff2,
robust_cave, guard_a2}.json` (repo-root `_scratch/`, gitignored, regenerable).
"""


def write_report():
    rows, res, rows_flat, fin, rob = _load_all()
    o = io.StringIO()
    o.write(NARR["HEAD"])
    o.write(NARR["SEC1"])
    st = H.OUT / "selftest_out.txt"
    o.write("\n```\n" + (st.read_text(encoding="utf-8") if st.exists() else "(run --selftest)\n") + "```\n")
    o.write("\n## 2. The plant used, per speed (`v294_plant.family()['nominal'].at(v)`, linear in speed between the fit knots "
            "3.1 / 8.0 / 11.9 / 17.0 / 26.9 m/s, flat outside; the spring saturation is the record's prior sat(v))\n\n")
    plant_table(o)
    o.write(NARR["SEC3"])
    o.write("\n## 4. The sweeps: which gate binds at which speed\n")
    o.write(NARR["FEAS"])
    feas_table(o, rows, res)
    o.write("\n### 4.1 The Kp landscape for four (Ki, ICL, DB, Kd) settings (line-only reading; the brief's grid)\n")
    landscape(o, rows, res, [(0, 0, 0, 0), (256, 4096, 0, 16), (1024, 4096, 0, 0), (1024, 4096, 0, 16)])
    o.write(NARR["LAND"])
    o.write("\n## 5. The candidates, one scorecard per schedule type\n")
    o.write(NARR["CANDS"])
    rows_f = fin["rows"]
    o.write("\n### 5.1 STRICT reading (texture gated)\n\n")
    T = scorecard(o, rows_f, fin["results"], strict=True)
    o.write("\n### 5.2 LINE-ONLY reading (texture reported, not gated)\n\n")
    scorecard(o, rows_f, fin["results"], strict=False)
    o.write(NARR["CANDS2"])
    o.write("\n### 5.3 Per-speed detail of every candidate\n")
    o.write(NARR["DETAIL"])
    detail(o, rows_f, T)
    o.write("\n## 6. Override, fault sentinel and disengage\n")
    o.write(NARR["SAFETY"])
    safety(o, rows_f, T)
    o.write("\n" + NARR["SAFETY2"])
    icl_table(o, rows, res)
    o.write(NARR["SAFETY3"])
    guard_table(o)
    o.write(NARR["SAFETY4"])
    o.write("\n## 7. Robustness across the plant family (tracking scenarios; gates U stable, S stick-slip, D dead zone, "
            "T tracking, H hold; texture not gated)\n\n")
    robust(o, rob)
    o.write("\n" + NARR["ROBUST"])
    rc = H.load("robust_cave.json")
    robust(o, dict(rows=rc["rows"], members=rc["members"], results=rc["results"]))
    o.write("\n## 8. The fork's outer loop closed (outer = 'pi', tau_o 1.0 s, 60 ms-old wire angle)\n\n")
    outer_pi(o, rob)
    o.write(NARR["OUTER"])
    o.write("\n## 9. The record's 20 Hz comparator per candidate\n\n")
    hf20_table(o, rows_f)
    o.write(NARR["HF20"])
    o.write(NARR["PAYOFF"])
    payoff_table(o)
    o.write(NARR["PAYOFF2"])
    o.write(NARR["TAIL"])
    txt = o.getvalue()
    H.REPORT.parent.mkdir(parents=True, exist_ok=True)
    H.REPORT.write_text(txt, encoding="utf-8")
    print("wrote %s (%d bytes)" % (H.REPORT, len(txt.encode("utf-8"))))


if __name__ == "__main__":
    write_report()
