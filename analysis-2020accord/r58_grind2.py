#!/usr/bin/env python3
"""ROUTES 54 (V71B) and 58 (V71C) -- GRIND #2 (40-49 Hz), plus the 2x-harmonic test.

PRE-REGISTERED: route 58 shows grind #2 ENGAGED; route 54 does not.

★ ROUTE 58'S MANUAL ARM IS BYTE-FOR-BYTE STOCK. V71C's edits live behind the gp-0x6806 gate, so
every manual frame runs stock firmware -- same car, same day, same driver, same tyres, same road.
That makes "present engaged, absent manual" on route 58 a WITHIN-ROUTE contrast against stock, the
cleanest grind-#2 control in the corpus. It is exploited in §3 and quoted as the contemporaneous
stock reference everywhere else. ⚠ Its ONE limit, measured: route 58's manual arm never exceeds
20 km/h, so the stock control is CREEP-ONLY. There is no manual highway anywhere in the corpus.

INSTRUMENT for the burst census: `r47_orchestrator_checks._windows` UNCHANGED -- same 2.56 s window,
same butter+hilbert band envelope, same p99, same 500-count threshold that produced every prior
route's burst count. The newer tapered `_grind2_lib.win_env` is NOT substituted (they differ by
1.4-1.9x and cross-comparing them is a recorded error). That inherits R47's `1/median(dt)` rate,
which is common mode across every pool by construction and cannot bias a between-pool count.

Writes `_r58_grind2.json`.  Usage: python r58_grind2.py
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

CREEP = (0.3, 4.0)                     # the kit's creep window for the grind-#2 census (r4a §6)
CORNER_ANG = 100.0
HWY = 14.0                             # m/s
OUT = {}

POOLS = {
    "Kd=0     (V61 r31)":                     ["_cache_r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_cache_r2b", "_cache_r2c", "_cache_r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_cache_r37", "_cache_r3a", "_cache_r3b"],
    "Kd=gated (V67 r47 + V68 r4e)":           ["_cache_r47", "_cache_v68"],
    "Kd=4x<50 (V69 r4f)":                     ["_cache_r4f"],
    "Kd=2x<50 (V70 r50)":                     ["_cache_r50"],
    "V71B r54  r26 x2 UNGATED  ***":          ["_cache_r54"],
    "V71C r58  both arms GATED ***":          ["_cache_r58"],
}
KD2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
GATED = "Kd=gated (V67 r47 + V68 r4e)"
NEW = ["V71B r54  r26 x2 UNGATED  ***", "V71C r58  both arms GATED ***"]
# Parked segments: excluded from every cell so a stationary wheel cannot dilute a rate.
SKIP = {"_cache_r54": ("r54s10.npz", "r54s11.npz"),
        "_cache_r58": ("r58s12.npz", "r58s13.npz", "r58s14.npz", "r58s15.npz"),
        "_cache_r50": ("r50s0.npz",)}


def hdr(s):
    print(f"\n{'=' * 114}\n{s}\n{'=' * 114}")


# =============================================================== §1 exposure in SECONDS ===========
hdr("§1  EXPOSURE IN SECONDS from RAW FRAMES. Parked segments excluded (r54 s10-11, r58 s12-15, "
    "r50 s0).")
print(f"   creep = {CREEP[0]}-{CREEP[1]} m/s   corner = creep AND |angle| >= {CORNER_ANG:.0f} deg   "
      f"highway >= {HWY:.0f} m/s\n")
print(f"   {'pool':42s} {'total':>8s} {'creep':>8s} {'engCreep':>9s} {'manCreep':>9s} "
      f"{'corner':>8s} {'engCorner':>10s} {'hwy':>8s} {'engHwy':>8s} {'manHwy':>8s}")
expo = {}
for name, caches in POOLS.items():
    a = dict(tot=0.0, creep=0.0, eng_creep=0.0, man_creep=0.0, corner=0.0, eng_corner=0.0,
             hwy=0.0, eng_hwy=0.0, man_hwy=0.0)
    for c in caches:
        for p in sorted((ROOT / c).glob("*.npz")):
            if "_imu" in p.name or "_rpm" in p.name or p.name in SKIP.get(c, ()):
                continue
            d = dict(np.load(p))
            if "cs_v" not in d or "tq" not in d:
                continue
            fs = 1.0 / float(np.median(np.diff(d["t"])))
            dt = 1.0 / fs
            v = np.abs(np.asarray(d["cs_v"], float))
            ang = np.abs(np.asarray(d["ang"], float))
            eng = np.asarray(d.get("cc_lat", np.zeros_like(v)), float) > 0.5
            m_cr = (v >= CREEP[0]) & (v < CREEP[1])
            m_co = m_cr & (ang >= CORNER_ANG)
            m_hw = v >= HWY
            a["tot"] += len(v) * dt
            a["creep"] += m_cr.sum() * dt
            a["eng_creep"] += (m_cr & eng).sum() * dt
            a["man_creep"] += (m_cr & ~eng).sum() * dt
            a["corner"] += m_co.sum() * dt
            a["eng_corner"] += (m_co & eng).sum() * dt
            a["hwy"] += m_hw.sum() * dt
            a["eng_hwy"] += (m_hw & eng).sum() * dt
            a["man_hwy"] += (m_hw & ~eng).sum() * dt
    expo[name] = a
    print(f"   {name:42s} {a['tot']:8.1f} {a['creep']:8.1f} {a['eng_creep']:9.1f} "
          f"{a['man_creep']:9.1f} {a['corner']:8.1f} {a['eng_corner']:10.1f} {a['hwy']:8.1f} "
          f"{a['eng_hwy']:8.1f} {a['man_hwy']:8.1f}")
OUT["exposure_s"] = expo

# =============================================================== §2 the burst census ==============
hdr(f"§2  THE BURST CENSUS -- windows with 40-49 Hz envelope p99 > {R47.BURST:.0f} counts")
rows = {}
for name, caches in POOLS.items():
    r = []
    for c in caches:
        skip = SKIP.get(c, ())
        rr = R47._windows(c, name, lambda v: True)
        r += [x for x in rr if not any(s in str(x["ep"][0]) for s in skip)]
    rows[name] = r
    print(f"   {name:42s} {len(r):>6d} windows")


def census(sel, label, key="40-49"):
    print(f"\n   --- {label}")
    print(f"   {'pool':42s} {'arm':>8s} {'n':>5s} {'secs':>7s} {'max':>9s} {'p90':>8s} "
          f"{'p99':>8s} {'bursts':>7s} {'rate/s':>8s}")
    tab = {}
    for name in POOLS:
        for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5),
                         ("manual", lambda r: r["lat"] <= 0.5)):
            s = [r for r in rows[name] if sel(r) and amf(r)]
            if not s:
                tab[f"{name}|{arm}"] = dict(n=0, secs=0.0, bursts=0, rate=np.nan)
                print(f"   {name:42s} {arm:>8s} {0:>5d} {0.0:>7.1f}       --       --       --"
                      f" {0:>7d}       --")
                continue
            v = np.array([r[key] for r in s], float)
            secs = len(s) * R47.WIN_S / 2.0     # 50% overlap
            b = int((v > R47.BURST).sum())
            tab[f"{name}|{arm}"] = dict(n=len(s), secs=float(secs), mx=float(v.max()),
                                        p90=float(np.percentile(v, 90)),
                                        p99=float(np.percentile(v, 99)), bursts=b,
                                        rate=float(b / secs) if secs else np.nan)
            print(f"   {name:42s} {arm:>8s} {len(s):>5d} {secs:>7.1f} {v.max():>9.1f} "
                  f"{np.percentile(v, 90):>8.1f} {np.percentile(v, 99):>8.1f} {b:>7d} "
                  f"{b / secs:>8.4f}")
    return tab


cells = {}
cells["creep"] = census(lambda r: CREEP[0] <= r["v"] < CREEP[1], "CREEP 0.3-4.0 m/s")
cells["corner"] = census(lambda r: (CREEP[0] <= r["v"] < CREEP[1] and r["ang"] >= CORNER_ANG),
                         f"CORNER-lite (creep AND |angle| >= {CORNER_ANG:.0f} deg)")
cells["hwy"] = census(lambda r: r["v"] >= HWY, f"HIGHWAY >= {HWY:.0f} m/s")
cells["all"] = census(lambda r: True, "ALL SPEEDS")
OUT["census"] = cells

# =============================================================== §3 the within-route stock control =
hdr("§3  ★★ ROUTE 58's WITHIN-ROUTE STOCK CONTROL -- engaged (V71C) vs manual (byte-stock)")
print("   Same car, same day, same driver. The ONLY within-route firmware A/B for grind #2 in the")
print("   corpus. ⚠ Manual on route 58 is creep-only, so this is a CREEP contrast.\n")


def bootp(v, ep, q=90, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260804)
    u = np.unique(ep)
    if len(u) < 2:
        return float(np.percentile(v, q)), np.nan, np.nan
    per = [v[ep == e] for e in u]
    dr = np.empty(nb)
    for i in range(nb):
        j = rng.integers(0, len(per), len(per))
        dr[i] = np.percentile(np.concatenate([per[k] for k in j]), q)
    return (float(np.percentile(v, q)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)))


def boot_ratio(a, aep, b, bep, q=90, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260805)
    ua, ub = np.unique(aep), np.unique(bep)
    if len(ua) < 2 or len(ub) < 2:
        return np.nan, np.nan, np.nan
    pa = [a[aep == e] for e in ua]
    pb = [b[bep == e] for e in ub]
    dr = np.empty(nb)
    for i in range(nb):
        sa = np.concatenate([pa[k] for k in rng.integers(0, len(pa), len(pa))])
        sb = np.concatenate([pb[k] for k in rng.integers(0, len(pb), len(pb))])
        dr[i] = np.percentile(sa, q) / max(np.percentile(sb, q), 1e-9)
    pt = np.percentile(a, q) / max(np.percentile(b, q), 1e-9)
    return float(pt), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def split_null(v, ep, q=90, nb=800, rng=None):
    rng = rng or np.random.default_rng(20260806)
    u = np.unique(ep)
    if len(u) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = rng.permutation(len(u))
        h = len(u) // 2
        s1 = np.concatenate([v[ep == e] for e in u[p[:h]]])
        s2 = np.concatenate([v[ep == e] for e in u[p[h:2 * h]]])
        out.append(np.percentile(s1, q) / max(np.percentile(s2, q), 1e-9))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


wr = {}
for name in NEW + [GATED, KD2, "Kd=4x<50 (V69 r4f)", "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)"]:
    for cellname, sel in (("creep", lambda r: CREEP[0] <= r["v"] < CREEP[1]),
                          ("all", lambda r: True)):
        A = [r for r in rows[name] if sel(r) and r["lat"] > 0.5]
        B = [r for r in rows[name] if sel(r) and r["lat"] <= 0.5]
        if len(A) < 5 or len(B) < 5:
            print(f"   {name:42s} {cellname:<6} *** eng n={len(A)}, man n={len(B)} TOO FEW")
            continue
        for band in ("40-49", "24-28", "18-22"):
            a = np.array([r[band] for r in A], float)
            b = np.array([r[band] for r in B], float)
            aep = np.array([str(r["ep"]) for r in A])
            bep = np.array([str(r["ep"]) for r in B])
            pt, lo, hi = boot_ratio(a, aep, b, bep)
            nl = split_null(np.concatenate([a, b]), np.concatenate([aep, bep]))
            wr[f"{name}|{cellname}|{band}"] = dict(ratio=pt, lo=lo, hi=hi, nA=len(A), nB=len(B),
                                                   p90A=float(np.percentile(a, 90)),
                                                   p90B=float(np.percentile(b, 90)),
                                                   null_lo=nl[0], null_hi=nl[1])
            tag = ("" if not np.isfinite(nl[0]) else
                   ("INSIDE NULL" if nl[0] <= pt <= nl[1] else "*** OUTSIDE"))
            print(f"   {name:42s} {cellname:<6} {band:>6} eng/man p90 = {pt:>8.3f} "
                  f"[{lo:>7.3f},{hi:>9.3f}]  eng {np.percentile(a, 90):>8.1f} "
                  f"man {np.percentile(b, 90):>7.1f}  null[{nl[0]:.2f},{nl[1]:.2f}] {tag}")
        print()
OUT["within_route"] = wr

# =============================================================== §4 POWER =========================
hdr("§4  POWER -- P(0) at the reference pool's OWN burst rate. A null with a large P(0) is NOT gone.")
pw = {}
for refname, reftag in ((KD2, "Kd2"), (GATED, "gated V67/V68")):
    for cellname in ("creep", "corner", "hwy", "all"):
        tab = cells[cellname]
        print(f"\n   --- reference {reftag}, cell {cellname}")
        print(f"   {'route':42s} {'arm':>8s} {'ref rate/s':>11s} {'secs':>8s} {'obs':>5s} "
              f"{'expected':>9s} {'P(0)':>8s}   verdict")
        for name in NEW + ["Kd=4x<50 (V69 r4f)", "Kd=2x<50 (V70 r50)"]:
            for arm in ("ENGAGED", "manual"):
                rate = tab.get(f"{refname}|{arm}", {}).get("rate", np.nan)
                cur = tab.get(f"{name}|{arm}", {})
                secs, obs = cur.get("secs", 0.0), cur.get("bursts", 0)
                if not np.isfinite(rate) or secs <= 0:
                    print(f"   {name:42s} {arm:>8s} {'--':>11s} {secs:>8.1f} {obs:>5d} "
                          f"{'--':>9s} {'--':>8s}   NO EXPOSURE / NO REF RATE")
                    continue
                exp = rate * secs
                p0 = float(poisson.pmf(0, exp))
                need = float("inf") if rate <= 0 else -np.log(0.05) / rate
                verd = ("RESOLVED: gone at ref rate (P(0) < 0.05)" if (p0 < 0.05 and obs == 0)
                        else "PRESENT (bursts observed)" if obs > 0
                        else f"🛑 UNDERPOWERED -- need {need:.0f} s for P(0) < 0.05")
                pw[f"{reftag}|{cellname}|{name}|{arm}"] = dict(rate=float(rate), secs=float(secs),
                                                               obs=int(obs), expected=float(exp),
                                                               p0=p0, need_s=need)
                print(f"   {name:42s} {arm:>8s} {rate:>11.4f} {secs:>8.1f} {obs:>5d} "
                      f"{exp:>9.2f} {p0:>8.4f}   {verd}")
OUT["power"] = pw

# =============================================================== §5 levels ========================
hdr("§5  LEVELS -- p90 of the 40-49 Hz envelope p99, engaged, by cell, episode bootstrap")
print("   🛑 A LEVEL statistic, not the burst detector. Read as a bound on the tail.\n")
lvl = {}
for cellname, sel in (("creep", lambda r: CREEP[0] <= r["v"] < CREEP[1]),
                      ("hwy", lambda r: r["v"] >= HWY), ("all", lambda r: True)):
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        print(f"   --- {cellname}, {arm}")
        print(f"   {'pool':42s} {'n':>5s} {'40-49 p90':>10s} {'[95% CI]':>21s} {'24-28 p90':>10s} "
              f"{'ratio':>7s} {'v mean':>7s}")
        for name in POOLS:
            s = [r for r in rows[name] if sel(r) and amf(r)]
            if len(s) < 4:
                print(f"   {name:42s} {len(s):>5d}   *** too few")
                continue
            v = np.array([r["40-49"] for r in s], float)
            w = np.array([r["24-28"] for r in s], float)
            ep = np.array([str(r["ep"]) for r in s])
            m, lo, hi = bootp(v, ep)
            vm = float(np.mean([r["v"] for r in s]))
            lvl[f"{cellname}|{arm}|{name}"] = dict(n=len(s), p90=m, lo=lo, hi=hi,
                                                   p90_2428=float(np.percentile(w, 90)), v=vm)
            print(f"   {name:42s} {len(s):>5d} {m:>10.1f} [{lo:>9.1f},{hi:>10.1f}] "
                  f"{np.percentile(w, 90):>10.1f} "
                  f"{m / max(np.percentile(w, 90), 1e-9):>7.2f} {vm:>7.2f}")
        print()
OUT["levels"] = lvl

(ROOT / "_r58_grind2.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_r58_grind2.json'}")
