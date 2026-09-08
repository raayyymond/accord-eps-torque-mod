# -*- coding: utf-8 -*-
"""studies/grind/wire_0xe4_slewcap.py -- addendum to wire_0xe4_20hz.py.  The 0xE4 command is slew-capped
by openpilot at STEER_DELTA * DT_CTRL * STEER_MAX = 3 * 0.01 * 4096 = 122.88 raw counts per 100 Hz frame
(opendbc honda carcontroller.py `rate_limit(...)`, verified in the operator's fork by the team-lead,
2026-09-07).  So the census's "top-1 % step >= 122 raw/frame" predicate IS the slew cap.

Question, from the team-lead:
  (a) fraction of frames ON THE CAP in grind #1 onsets vs engaged baseline
  (b) are onsets preceded by RUNS of consecutive capped frames (a ramp at the cap)?  run-length distribution
  (c) given the cap, what IS the command's cadence -- a continuous ramp, or hold-then-step?
This decides whether the staircase or the ramp-at-cap is what rings the EPS.

Same loading, same engagement definition and the same episode recipe as wire_0xe4_20hz.py.
ANALYSIS ONLY: builds nothing, sends nothing.

Run: python wire_0xe4_slewcap.py      (writes _scratch/wire_0xe4_slewcap.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import wire_0xe4_20hz as WIRE                 # noqa: E402  load_route, episodes_of, bandamp

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
LO, HI = 18.0, 22.0
ROUTES = ("r39", "r3a", "r3c")
CAP = 122            # |delta| in {122, 123} == on the 122.88 slew cap
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def runlens(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return np.flatnonzero(d == -1) - np.flatnonzero(d == 1)


def main():
    cells = GI.read_cells(WIRE.V282_IMG)
    G, EP = {}, {}
    for t in ROUTES:
        G[t] = WIRE.load_route(t, cells)
        eps, hot = WIRE.episodes_of(G[t])
        EP[t] = eps
        G[t]["hot"] = hot
        print("loaded %s: %d episodes" % (t, len(eps)), flush=True)

    pr("=" * 150)
    pr("THE 0xE4 SLEW CAP AND GRIND #1 ONSETS -- addendum to WIRE-0XE4-20HZ, V282 (r39/r3a/r3c)")
    pr("script wire_0xe4_slewcap.py, subagent `wire`, 2026-09-07.  Analysis only.")
    pr("=" * 150)

    # per-route derived arrays on the 0xE4 stream's own clock
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        d = np.diff(e["grid"])
        base = e["egrid"][1:] & e["egrid"][:-1]
        e["d"] = d
        e["base"] = base
        e["cap"] = base & (np.abs(d) >= CAP)
        # episode mask and episode ONSET instants, mapped onto the e4 clock
        e["hot"] = np.interp(e["tgrid"], g["t"], g["hot"].astype(float))[1:] > 0.5
        e["onsets"] = np.array([int(np.searchsorted(e["tgrid"], g["t"][a])) for a, b, f in EP[tag]])

    # ================================================================================== 0. the cap itself
    pr("\n0. THE CAP, READ FROM THE WIRE  [EVIDENCE]")
    pr("   openpilot: rate_limit(torque_cmd, last, -DELTA*DT, +DELTA*DT) with DELTA 3, DT 0.01, STEER_MAX")
    pr("   4096  =>  122.88 raw counts/frame.  Integer rounding puts the wall on 122 AND 123.")
    pr("   %-5s %9s | %s" % ("route", "n frames", "  ".join("|d|=%d" % v for v in range(119, 125))))
    for tag in ROUTES:
        e = G[tag]["e4"]
        a = np.abs(e["d"])[e["base"]]
        pr("   %-5s %9d | %s" % (tag, len(a), "  ".join("%6d" % (a == v).sum() for v in range(119, 125))))
    pr("   Nothing above 123 on any route; the 121->122 jump is ~30x.  '|d| >= 122' == 'on the cap'.")

    # ================================================================ (a) capped fraction, onsets vs baseline
    pr("\n" + "=" * 150)
    pr("(a) FRACTION OF FRAMES ON THE CAP -- grind #1 onsets vs engaged baseline  [EVIDENCE]")
    pr("=" * 150)
    pr("  Strata, all on the 0xE4 clock, lateral engaged, contiguous frames only:")
    pr("    onset +-0.5 s   the 101 frames centred on each episode onset")
    pr("    pre-onset       the 50 frames BEFORE each onset (causally prior to the line appearing)")
    pr("    episode body    every frame the census marks line-present")
    pr("    baseline        every engaged frame the census does NOT mark line-present")
    pr("  %-5s %-14s %9s %11s %11s %11s" %
       ("route", "stratum", "n frames", "frac capped", "vs baseline", "mean |d|"))
    ENR = {}
    for tag in ROUTES:
        e = G[tag]["e4"]
        n = len(e["d"])
        sel = {}
        w = np.zeros(n, bool)
        wp = np.zeros(n, bool)
        for i0 in e["onsets"]:
            w[max(0, i0 - 50):min(n, i0 + 51)] = True
            wp[max(0, i0 - 50):min(n, i0)] = True
        sel["onset +-0.5 s"] = e["base"] & w
        sel["pre-onset"] = e["base"] & wp
        sel["episode body"] = e["base"] & e["hot"]
        sel["baseline"] = e["base"] & ~e["hot"]
        fb = np.mean(np.abs(e["d"])[sel["baseline"]] >= CAP)
        ENR[tag] = fb
        for lab in ("onset +-0.5 s", "pre-onset", "episode body", "baseline"):
            s = sel[lab]
            fr = np.mean(np.abs(e["d"])[s] >= CAP)
            pr("  %-5s %-14s %9d %11.4f %11s %11.2f" %
               (tag, lab, s.sum(), fr, "%.1fx" % (fr / fb) if lab != "baseline" else "-",
                np.abs(e["d"])[s].mean()))
    pr("\n  Episode-LEVEL version (the census's own unit): does an onset have a capped frame nearby at all?")
    pr("  Baseline draws one instant per second of engaged time, so it is not dominated by the 100 Hz rate;")
    pr("  the CI resamples EPISODES (n=4000), exactly as the census does.")
    pr("  %-5s %7s %14s %14s %11s %-22s" %
       ("route", "n eps", "P(cap in +-0.5s)", "baseline P", "enrichment", "95 % CI (bootstrap)"))
    rng = np.random.default_rng(20260907)
    pooled_hit, pooled_base_n, pooled_base_k = [], 0, 0
    for tag in ROUTES:
        e = G[tag]["e4"]
        n = len(e["d"])
        hit = []
        for i0 in e["onsets"]:
            s = slice(max(0, i0 - 50), min(n, i0 + 51))
            hit.append(bool((e["base"][s] & (np.abs(e["d"])[s] >= CAP)).any()))
        hit = np.array(hit, bool)
        # baseline: 1 Hz-sampled engaged instants, same +-0.5 s window test
        idx = np.flatnonzero(e["base"])[::100]
        bh = np.array([bool((e["base"][max(0, i - 50):min(n, i + 51)] &
                             (np.abs(e["d"])[max(0, i - 50):min(n, i + 51)] >= CAP)).any()) for i in idx])
        pb = bh.mean()
        bs = np.array([hit[rng.integers(0, len(hit), len(hit))].mean() / pb for _ in range(4000)])
        pr("  %-5s %7d %14.3f %14.3f %11.2fx %-22s" %
           (tag, len(hit), hit.mean(), pb, hit.mean() / pb,
            "[%.2f, %.2f]x" % tuple(np.percentile(bs, (2.5, 97.5)))))
        pooled_hit.append(hit)
        pooled_base_n += len(bh)
        pooled_base_k += bh.sum()
    ph = np.concatenate(pooled_hit)
    pb = pooled_base_k / pooled_base_n
    bs = np.array([ph[rng.integers(0, len(ph), len(ph))].mean() / pb for _ in range(4000)])
    pr("  %-5s %7d %14.3f %14.3f %11.2fx %-22s" %
       ("POOL", len(ph), ph.mean(), pb, ph.mean() / pb,
        "[%.2f, %.2f]x" % tuple(np.percentile(bs, (2.5, 97.5)))))

    # ============================================================================ (b) capped RUNS
    pr("\n" + "=" * 150)
    pr("(b) ARE ONSETS PRECEDED BY RUNS AT THE CAP?  run-length distribution  [EVIDENCE]")
    pr("=" * 150)
    pr("\n(b1) Run-length distribution of consecutive capped frames, ALL engaged time")
    pr("  %-5s %8s %9s %8s %8s %8s %8s %8s %10s %12s" %
       ("route", "n runs", "frames", "len 1", "2", "3-4", "5-9", ">=10", "max len", "max dur ms"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        rl = runlens(e["cap"])
        if not len(rl):
            continue
        pr("  %-5s %8d %9d %8.3f %8.3f %8.3f %8.3f %8.3f %10d %12.0f" %
           (tag, len(rl), rl.sum(), np.mean(rl == 1), np.mean(rl == 2),
            np.mean((rl >= 3) & (rl <= 4)), np.mean((rl >= 5) & (rl <= 9)), np.mean(rl >= 10),
            rl.max(), rl.max() * e["P"] * 1000))
    pr("\n(b2) The longest capped RUN inside the 0.5 s before each onset, vs the same test at 1 Hz-sampled")
    pr("     engaged baseline instants")
    pr("  %-5s %-12s %7s %9s %9s %9s %9s %9s" %
       ("route", "stratum", "n", "P(run>=1)", "P(>=2)", "P(>=3)", "P(>=5)", "p90 len"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        n = len(e["d"])

        def longest(i):
            s = slice(max(0, i - 50), min(n, i))
            rl = runlens(e["cap"][s])
            return int(rl.max()) if len(rl) else 0
        on = np.array([longest(i) for i in e["onsets"]])
        bl = np.array([longest(i) for i in np.flatnonzero(e["base"])[::100]])
        for lab, a in (("pre-onset", on), ("baseline", bl)):
            pr("  %-5s %-12s %7d %9.3f %9.3f %9.3f %9.3f %9.0f" %
               (tag, lab, len(a), np.mean(a >= 1), np.mean(a >= 2), np.mean(a >= 3), np.mean(a >= 5),
                np.percentile(a, 90)))
    pr("\n(b3) Are the capped frames a RAMP (same sign) or a DITHER (alternating sign)?  Within every")
    pr("     capped run of length >= 2, the fraction of adjacent pairs whose delta has the SAME sign.")
    pr("  %-5s %10s %14s %16s %14s" %
       ("route", "runs >=2", "same-sign frac", "mean run excursion", "run rate deg/s equiv"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        d = e["d"]
        starts = np.flatnonzero(np.diff(np.r_[0, e["cap"].astype(int)]) == 1)
        ends = np.flatnonzero(np.diff(np.r_[e["cap"].astype(int), 0]) == -1) + 1
        same, tot, exc = 0, 0, []
        for a, b in zip(starts, ends):
            if b - a < 2:
                continue
            sg = np.sign(d[a:b])
            same += int((sg[1:] == sg[:-1]).sum())
            tot += len(sg) - 1
            exc.append(abs(d[a:b].sum()))
        pr("  %-5s %10d %14.4f %16.0f %14s" %
           (tag, len(exc), same / max(tot, 1), np.mean(exc) if exc else np.nan,
            "%.0f raw/s" % (CAP / e["P"])))

    # ============================================================================ (c) cadence
    pr("\n" + "=" * 150)
    pr("(c) WHAT THE CADENCE ACTUALLY IS, GIVEN THE CAP  [EVIDENCE]")
    pr("=" * 150)
    pr("  %-5s %-14s %9s %9s %9s %9s %9s %9s" %
       ("route", "stratum", "frac d=0", "p50 |d|", "p90 |d|", "frac cap", "sign flip", "|d| autoc"))
    pr("  ('sign flip' = fraction of adjacent nonzero deltas that reverse sign: 0 = pure ramp, 0.5 = dither.")
    pr("   '|d| autoc' = lag-1 autocorrelation of the SIGNED delta: +1 = smooth ramp, -1 = frame-to-frame")
    pr("   alternation, ~0 = independent steps.)")
    for tag in ROUTES:
        e = G[tag]["e4"]
        for lab, s in (("episode body", e["base"] & e["hot"]), ("baseline", e["base"] & ~e["hot"])):
            d = e["d"][s]
            nz = d[d != 0]
            sg = np.sign(nz)
            pr("  %-5s %-14s %9.3f %9.0f %9.0f %9.4f %9.3f %9.3f" %
               (tag, lab, np.mean(d == 0), np.percentile(np.abs(d), 50), np.percentile(np.abs(d), 90),
                np.mean(np.abs(d) >= CAP), np.mean(sg[1:] != sg[:-1]),
                float(np.corrcoef(d[1:], d[:-1])[0, 1])))
    pr("\n(c2) How much of the command's motion is delivered AT the cap?")
    pr("  %-5s %12s %14s %16s" % ("route", "frac frames", "frac of total", "frac of engaged"))
    pr("  %-5s %12s %14s %16s" % ("", "at the cap", "|d| travelled", "time in a run>=2"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        a = np.abs(e["d"])
        b = e["base"]
        rl = runlens(e["cap"])
        pr("  %-5s %12.4f %14.4f %16.4f" %
           (tag, np.mean(a[b] >= CAP), a[b & (a >= CAP)].sum() / a[b].sum(),
            rl[rl >= 2].sum() / b.sum() if len(rl) else 0.0))
    pr("\n(c3) Where does the command's 18-22 Hz line LIVE -- in capped stretches or uncapped ones?")
    pr("     2 s windows of engaged command, split by how much of the window is at the cap.")
    pr("  %-5s %-18s %7s %12s %12s" % ("route", "window cap fraction", "n win", "cmd 18-22 p50", "cmd p90"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        fs = 1.0 / e["P"]
        rows = {k: [] for k in ("0 (none)", "0-2 %", "2-10 %", ">10 %")}
        for a, b in C20.runs(e["egrid"], 200):
            for s in range(a, b - 200 + 1, 50):
                w = slice(s, s + 200)
                cf = np.mean(np.abs(e["d"][w]) >= CAP)
                amp = WIRE.bandamp(e["grid"][w], fs, LO, HI)
                k = "0 (none)" if cf == 0 else ("0-2 %" if cf < 0.02 else ("2-10 %" if cf < 0.10 else ">10 %"))
                rows[k].append(amp)
        for k in ("0 (none)", "0-2 %", "2-10 %", ">10 %"):
            if len(rows[k]) >= 5:
                pr("  %-5s %-18s %7d %12.1f %12.1f" %
                   (tag, k, len(rows[k]), np.median(rows[k]), np.percentile(rows[k], 90)))
            else:
                pr("  %-5s %-18s %7d   (thin)" % (tag, k, len(rows[k])))

    pr("\n(c4) CONTROL -- is that a LINE or just more of everything?  Same windows, but the 18-22 Hz")
    pr("     amplitude NORMALISED by the window's own 1-5 Hz content, and the line-to-shoulder ratio")
    pr("     (mean PSD 18-22 over the mean of 12-18 and 26-40).  A narrow LINE (the openpilot echo)")
    pr("     keeps a high shoulder ratio; broadband energy from the ramp corners does not.")
    pr("  %-5s %-18s %7s %14s %16s" %
       ("route", "window cap frac", "n win", "18-22 / 1-5 Hz", "line/shoulder"))
    for tag in ROUTES:
        e = G[tag]["e4"]
        fs = 1.0 / e["P"]
        rows = {k: [] for k in ("0 (none)", "0-2 %", "2-10 %", ">10 %")}
        for a, b in C20.runs(e["egrid"], 200):
            for s in range(a, b - 200 + 1, 50):
                w = slice(s, s + 200)
                cf = np.mean(np.abs(e["d"][w]) >= CAP)
                x = e["grid"][w]
                f, P = signal.welch(x - x.mean(), fs=fs, nperseg=200, detrend="linear")
                b18 = P[(f >= LO) & (f < HI)].mean()
                sh = 0.5 * (P[(f >= 12) & (f < 18)].mean() + P[(f >= 26) & (f < 40)].mean())
                lo5 = WIRE.bandamp(x, fs, 1.0, 5.0)
                amp = WIRE.bandamp(x, fs, LO, HI)
                k = "0 (none)" if cf == 0 else ("0-2 %" if cf < 0.02 else ("2-10 %" if cf < 0.10 else ">10 %"))
                rows[k].append((amp / max(lo5, 1e-9), b18 / max(sh, 1e-30)))
        for k in ("0 (none)", "0-2 %", "2-10 %", ">10 %"):
            if len(rows[k]) >= 5:
                r = np.array(rows[k])
                pr("  %-5s %-18s %7d %14.4f %16.2f" %
                   (tag, k, len(r), np.median(r[:, 0]), np.median(r[:, 1])))
            else:
                pr("  %-5s %-18s %7d   (thin)" % (tag, k, len(rows[k])))

    pr("\n(c5) DOES THE CAP DRIVE THE D TERM?  1 kHz mirror on the loudest episodes: of the ticks where")
    pr("     the D clamp BINDS, what fraction land on a command frame that was at the slew cap?")
    pr("  %-5s %-22s %9s %11s %13s %13s" %
       ("route", "episode", "drail", "cap frac", "P(cap|bind)", "enrichment"))
    ROWS = []
    for tag in ROUTES:
        g = G[tag]
        e = g["e4"]
        eps = sorted(EP[tag], key=lambda z: -GI.band(g["bar"][z[0]:z[1]], LO, HI, FS))[:5]
        capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float)) > 0.5
        for a, b, f0 in eps:
            if b - a < 100:
                continue
            o = GI.simulate(g, a, b, cells)
            n0, n1 = (a - o["seg"].start) * 10, (a - o["seg"].start) * 10 + (b - a) * 10
            dE = np.r_[0.0, np.diff(o["E"])]
            bind = (np.abs(dE * 128 / 8) > V.D_CLAMP)[n0:n1]
            cap1k = np.repeat(capf[a:b], 10)
            if bind.sum() < 5:
                pr("  %-5s %-22s %9.4f %11.4f %13s %13s" %
                   (tag, "%.1f-%.1f" % (g["tr"][a], g["tr"][b - 1]), o["drail"],
                    cap1k.mean(), "(n<5 binds)", "-"))
                continue
            pc = float(cap1k[bind].mean())
            pr("  %-5s %-22s %9.4f %11.4f %13.3f %13.1fx" %
               (tag, "%.1f-%.1f" % (g["tr"][a], g["tr"][b - 1]), o["drail"], cap1k.mean(), pc,
                pc / max(cap1k.mean(), 1e-9)))
            ROWS.append((pc, float(cap1k.mean())))
    if ROWS:
        R = np.array(ROWS)
        pr("  %-5s %-22s %9s %11.4f %13.3f %13.1fx" %
           ("POOL", "median", "", np.median(R[:, 1]), np.median(R[:, 0]),
            np.median(R[:, 0] / np.maximum(R[:, 1], 1e-9))))

    with open(os.path.join(SCR, "wire_0xe4_slewcap.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\n[written: _scratch/wire_0xe4_slewcap.txt]")


if __name__ == "__main__":
    main()
