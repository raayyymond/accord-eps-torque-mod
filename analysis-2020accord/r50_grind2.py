#!/usr/bin/env python3
"""ROUTE 50 / V70 -- GRIND #2 (30-49 Hz burst census). Does the operator's *"seems GONE"* hold?

🛑 EXPOSURE BEFORE MECHANISM, AND POWER BEFORE ANY NULL. Route 50 is 181.6 s of which 61.6 s is
PARKED; engaged creep is 28.9 s and >= 50 km/h exposure is a few seconds. A zero-burst reading on
that much data is nearly guaranteed whatever the firmware does, so every null here is quoted with
the Poisson P(0) at the Kd=2.00 pool's own measured burst rate. **A null with P(0) = 0.1 is not
"gone"** -- the corner cell was already under-powered at P(0) = 0.128 on route 4f, which had four
times this route's exposure.

🛑🛑 AND THE PRIOR THAT MUST BE SAID FIRST: **V67 ALREADY ELIMINATED ENGAGED-CREEP GRIND #2**
(route 4a, 158.7 s armed, 0 bursts vs 7.62 expected, P(0) = 0.0005), and V69 replicated it. A clean
creep arm on V70 REPLICATES that; it is a non-regression result, never evidence that V70 removed
anything.

INSTRUMENT. `r47_orchestrator_checks._windows` UNCHANGED -- same 2.56 s window, same butter+hilbert
band envelope, same p99, same 500-count threshold that produced every prior route's burst count. The
newer tapered `_grind2_lib.win_env` is NOT substituted: the two differ by 1.4-1.9x and cross-
comparing them is a recorded error. That also inherits R47's `1/median(dt)` rate, which is common
mode across every pool by construction.

Writes `_r50_grind2.json`.  Usage: python r50_grind2.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r47_orchestrator_checks as R47  # noqa: E402
from _r31_common import load, sustained  # noqa: E402

CREEP = (0.3, 4.0)                     # the kit's creep window for the grind-#2 census (r4a ss6)
CORNER_EFF, CORNER_ANG = 1200.0, 100.0
HWY = 14.0                             # m/s
OUT = {}

POOLS = {
    "Kd=0     (V61 r31)":                     ["_cache_r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_cache_r2b", "_cache_r2c", "_cache_r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_cache_r37", "_cache_r3a", "_cache_r3b"],
    "Kd=gated (V67 r47 + V68 r4e)":           ["_cache_r47", "_cache_v68"],
    "Kd=4x<50 (V69 r4f)":                     ["_cache_r4f"],
    "Kd=2x<50 (V70 r50) *** THIS ROUTE ***":  ["_cache_r50"],
}
KD2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
V70 = "Kd=2x<50 (V70 r50) *** THIS ROUTE ***"


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


# =============================================================== ss1 exposure in SECONDS ==========
hdr("ss1  EXPOSURE IN SECONDS, from RAW FRAMES -- windows need 2.56 s of contiguity and would "
    "undercount a route that only clips a cell")
print(f"   creep = {CREEP[0]}-{CREEP[1]} m/s   corner = creep AND |sustained tq| >= {CORNER_EFF:.0f} "
      f"AND |angle| >= {CORNER_ANG:.0f} deg   highway = >= {HWY:.0f} m/s\n")
print(f"   {'pool':42s} {'total':>8s} {'creep':>8s} {'eng-creep':>10s} {'corner':>8s} "
      f"{'eng-corner':>11s} {'hwy':>8s} {'eng-hwy':>8s}")
expo = {}
for name, caches in POOLS.items():
    tot = cr = ecr = cor = ecor = hw = ehw = 0.0
    for c in caches:
        for p in sorted((ROOT / c).glob("*.npz")):
            if "_imu" in p.name or "_rpm" in p.name:
                continue
            d = dict(np.load(p))
            if "cs_v" not in d or "tq" not in d:
                continue
            fs = 1.0 / float(np.median(np.diff(d["t"])))
            dt = 1.0 / fs
            v = np.abs(np.asarray(d["cs_v"], float))
            eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
            ang = np.abs(np.asarray(d["ang"], float))
            eng = np.asarray(d.get("cc_lat", np.zeros_like(v)), float) > 0.5
            m_cr = (v >= CREEP[0]) & (v < CREEP[1])
            m_co = m_cr & (eff >= CORNER_EFF) & (ang >= CORNER_ANG)
            m_hw = v >= HWY
            tot += len(v) * dt
            cr += m_cr.sum() * dt
            ecr += (m_cr & eng).sum() * dt
            cor += m_co.sum() * dt
            ecor += (m_co & eng).sum() * dt
            hw += m_hw.sum() * dt
            ehw += (m_hw & eng).sum() * dt
    expo[name] = dict(tot=tot, creep=cr, eng_creep=ecr, corner=cor, eng_corner=ecor,
                      hwy=hw, eng_hwy=ehw)
    print(f"   {name:42s} {tot:8.1f} {cr:8.1f} {ecr:10.1f} {cor:8.1f} {ecor:11.1f} "
          f"{hw:8.1f} {ehw:8.1f}")
OUT["exposure_s"] = expo

# =============================================================== ss2 the burst census =============
hdr(f"ss2  THE BURST CENSUS -- windows with 40-49 Hz envelope p99 > {R47.BURST:.0f} counts")
print("   The V62/V65 creep bursts ran 2,000-4,000 counts, so the threshold sits far below them.")
print("   `n` counts 2.56 s windows at 50% overlap; `secs` is the window-covered exposure.\n")

rows = {}
for name, caches in POOLS.items():
    r = []
    for c in caches:
        r += R47._windows(c, name, lambda v: True)
    rows[name] = r


def census(sel, label, key="40-49"):
    print(f"\n   --- {label}")
    print(f"   {'pool':42s} {'arm':>9s} {'n':>5s} {'secs':>7s} {'max':>9s} {'p90':>8s} "
          f"{'p99':>8s} {'bursts':>7s} {'rate/s':>9s}")
    tab = {}
    for name in POOLS:
        for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
            s = [r for r in rows[name] if sel(r) and amf(r)]
            if not s:
                print(f"   {name:42s} {arm:>9s} {0:>5d} {0.0:>7.1f}       --       --       --"
                      f" {0:>7d} {0.0:>9.4f}")
                tab[f"{name}|{arm}"] = dict(n=0, secs=0.0, bursts=0)
                continue
            v = np.array([r[key] for r in s], float)
            secs = len(s) * R47.WIN_S / 2.0     # 50% overlap
            b = int((v > R47.BURST).sum())
            tab[f"{name}|{arm}"] = dict(n=len(s), secs=float(secs), mx=float(v.max()),
                                        p90=float(np.percentile(v, 90)),
                                        p99=float(np.percentile(v, 99)), bursts=b,
                                        rate=float(b / secs) if secs else np.nan)
            print(f"   {name:42s} {arm:>9s} {len(s):>5d} {secs:>7.1f} {v.max():>9.1f} "
                  f"{np.percentile(v, 90):>8.1f} {np.percentile(v, 99):>8.1f} {b:>7d} "
                  f"{b / secs:>9.4f}")
    return tab


cells = {}
cells["creep"] = census(lambda r: CREEP[0] <= r["v"] < CREEP[1], "CREEP 0.3-4.0 m/s")
cells["corner"] = census(lambda r: (CREEP[0] <= r["v"] < CREEP[1] and r["ang"] >= CORNER_ANG),
                         f"CORNER-lite (creep AND |angle| >= {CORNER_ANG:.0f} deg; "
                         f"the window record has no effort key)")
cells["hwy"] = census(lambda r: r["v"] >= HWY, f"HIGHWAY >= {HWY:.0f} m/s")
cells["all"] = census(lambda r: True, "ALL SPEEDS")
OUT["census"] = cells

# =============================================================== ss3 POWER ========================
hdr("ss3  ★★ POWER -- P(0) at the Kd=2.00 pool's OWN measured burst rate. A null with a large "
    "P(0) is NOT 'gone'.")
print("   expected = (Kd=2 burst rate in this cell) x (this route's exposure in that cell).")
print("   P(0) = Poisson probability of observing ZERO bursts if V70 behaved exactly like Kd=2.\n")
pw = {}
for cellname in ("creep", "corner", "hwy", "all"):
    tab = cells[cellname]
    print(f"   --- cell: {cellname}")
    print(f"   {'arm':>9s} {'Kd2 rate/s':>11s} {'V70 secs':>9s} {'V70 obs':>8s} {'expected':>9s} "
          f"{'P(0)':>9s}   verdict")
    for arm in ("ENGAGED", "manual"):
        k2 = tab.get(f"{KD2}|{arm}", {})
        v7 = tab.get(f"{V70}|{arm}", {})
        rate = k2.get("rate", np.nan)
        secs = v7.get("secs", 0.0)
        obs = v7.get("bursts", 0)
        if not np.isfinite(rate) or secs <= 0:
            print(f"   {arm:>9s} {rate if np.isfinite(rate) else float('nan'):>11.4f} "
                  f"{secs:>9.1f} {obs:>8d}        --        --   NO EXPOSURE / NO Kd2 RATE")
            pw[f"{cellname}|{arm}"] = dict(rate=float(rate), secs=float(secs), obs=int(obs))
            continue
        exp = rate * secs
        p0 = float(poisson.pmf(0, exp))
        need = float("inf") if rate <= 0 else -np.log(0.05) / rate
        verd = ("RESOLVED: gone at Kd2's rate (P(0) < 0.05)" if (p0 < 0.05 and obs == 0) else
                "REGRESSION (bursts present)" if obs > 0 else
                f"🛑 UNDERPOWERED -- need {need:.0f} s in this cell for P(0) < 0.05")
        pw[f"{cellname}|{arm}"] = dict(rate=float(rate), secs=float(secs), obs=int(obs),
                                       expected=float(exp), p0=p0, need_s=need)
        print(f"   {arm:>9s} {rate:>11.4f} {secs:>9.1f} {obs:>8d} {exp:>9.2f} {p0:>9.4f}   {verd}")
    print()
OUT["power"] = pw

# =============================================================== ss4 amplitude, not counts ========
hdr("ss4  AMPLITUDE instead of counts -- with 5 s of corner exposure a count test is hopeless, but "
    "the 40-49 Hz LEVEL is measurable on every window")
print("   p90 of the 40-49 Hz envelope p99, engaged, by speed cell, with an episode bootstrap.")
print("   🛑 This is a LEVEL statistic, not the burst detector -- a bursty phenomenon can leave the")
print("   level untouched. Read it as a bound on the tail, never as the census.\n")
RNG = np.random.default_rng(20260804)


def bootp90(v, ep, nb=3000):
    u = np.unique(ep)
    if len(u) < 2:
        return np.nan, np.nan, np.nan
    per = [v[ep == e] for e in u]
    dr = np.empty(nb)
    for i in range(nb):
        j = RNG.integers(0, len(per), len(per))
        dr[i] = np.percentile(np.concatenate([per[k] for k in j]), 90)
    return (float(np.percentile(v, 90)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)))


lvl = {}
for cellname, sel in (("creep", lambda r: CREEP[0] <= r["v"] < CREEP[1]),
                      ("hwy", lambda r: r["v"] >= HWY), ("all", lambda r: True)):
    print(f"   --- {cellname}, ENGAGED")
    print(f"   {'pool':42s} {'n':>5s} {'40-49 p90':>10s} {'[95% CI]':>20s} {'24-28 p90':>10s} "
          f"{'ratio 40-49/24-28':>18s}")
    for name in POOLS:
        s = [r for r in rows[name] if sel(r) and r["lat"] > 0.5]
        if len(s) < 4:
            print(f"   {name:42s} {len(s):>5d}   *** too few")
            continue
        v = np.array([r["40-49"] for r in s], float)
        w = np.array([r["24-28"] for r in s], float)
        ep = np.array([str(r["ep"]) for r in s])
        m, lo, hi = bootp90(v, ep)
        lvl[f"{cellname}|{name}"] = dict(n=len(s), p90=m, lo=lo, hi=hi,
                                         p90_2428=float(np.percentile(w, 90)))
        print(f"   {name:42s} {len(s):>5d} {m:>10.1f} [{lo:>8.1f},{hi:>9.1f}] "
              f"{np.percentile(w, 90):>10.1f} {m / max(np.percentile(w, 90), 1e-9):>18.3f}")
    print()
OUT["levels"] = lvl

(HERE / "_r50_grind2.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_r50_grind2.json'}")
