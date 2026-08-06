#!/usr/bin/env python3
"""Route `5d` (**V74**) -- GRIND #1 as a LIMIT CYCLE (duty x in-burst amplitude), and the
within-route damper dose-response against `bit7`.

🛑 WHY DUTY IS THE PRIMARY METRIC. [EVIDENCE, 8 routes] decomposing each build's median `e_18-22`
into duty x in-burst amplitude: duty spans 0.015 -> 0.958 (64x) while in-burst amplitude spans only
1232 -> 1533 (1.24x), against a 5.62x dose ladder. Successful builds stop the cycle STARTING; none
makes it smaller. So a median band energy is the wrong headline for grind #1 and `duty` is the right
one. The instrument is `nearcentre_relay.py` UNCHANGED: T = 600 counts of the 18-22 Hz p99 envelope
(1200 p-p, the corpus's own ratchet cut), engaged creep, restricted to the GRIND-ACTIVE regime
(window angle span 8-200 deg) so a duty question does not silently become an exposure question.

PART 2 is the strongest causal test available on one route: `bit7` = `(gp-0x6bd0 != 0)`, the base
damper's OWN output, per frame. Symptom in bit7=1 windows vs bit7=0 windows is a WITHIN-route
contrast and is immune to every route-to-route confound.
🛑 AND IT IS CONFOUNDED BY CONSTRUCTION: the damper's own input is a rate, so `bit7` duty rises with
steering rate, and steering rate drives the symptom. The contrast is therefore ONLY reported inside
matched rate bins, and the unmatched version is printed beside it to show how large the confound is.

Usage:  python r5d_duty.py [ep|blk]   ->  writes _r5d_duty.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r5d_lib as L  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(74074)
NBOOT = 3000
OUT = {"epkey": G.EPKEY}
PARK_5D = [2, 3, 9]
SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
ACTIVE_SB = (2, 3, 4)          # span 8-200 deg -- the grind-active regime
T_LIST = ((600.0, "T=600"), (1000.0, "T=1000"))

# ---------------------------------------------------------------- store ---------------------------
# `_nearcentre_lib.records()` stops at V72. Extend it with V73/r5a and V74/r5d through the IDENTICAL
# `augment_angle`, so `span` means the same thing on every arm.
PKL = ROOT / "_cache_r5d_nearcentre.pkl"
if PKL.exists():
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
else:
    store = dict(N.records())
    R = L.records()
    for b, park in (("V73/r5a", [17]), ("V74/r5d", PARK_5D)):
        rs = [dict(r) for r in R[b] if r["seg"] not in park]
        store[b] = N.augment_angle(rs, nfft=N.NFFT)
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)

LADDER = N.LADDER + ["V73/r5a", "V74/r5d"]
for b in LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["sb"] = G.binof(r["span"], SP)

ARMS = dict(N.ARMS)
ARMS["V73/r5a"] = ["V73/r5a"]
ARMS["V74/r5d"] = ["V74/r5d"]
ENGC = {b: N.eng_creep(store[b]) for b in LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in ARMS.items()}
ACTIVE = {k: [r for r in v if r["sb"] in ACTIVE_SB] for k, v in ARM.items()}
ORDER = ["V61 (kill)", "stock pool", "V72/r59", "V73/r5a", "V74/r5d", "V71C/r58", "V71B/r54",
         "V62+V65", "V69/r4f", "V70/r50", "V67+V68"]


def boot_units(rs, fn, key="e_18-22", nb=NBOOT):
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in ep.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return (np.nan,) * 3
    allv = np.concatenate(per)
    d = np.full(nb, np.nan)
    for i in range(nb):
        v = np.concatenate([per[j] for j in RNG.integers(0, len(per), len(per))])
        if len(v):
            d[i] = fn(v)
    return float(fn(allv)), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


# ================================================== 1. DUTY x IN-BURST AMPLITUDE ==================
N.hdr("1. ★★★ GRIND #1 -- DUTY x IN-BURST AMPLITUDE. Engaged creep (< 5.556 m/s), span 8-200 deg")
print(f"  resampling unit `{G.EPKEY}`. duty = fraction of windows with e_18-22 >= T; in-burst = the")
print("  median AMONG those windows. A limit cycle moves DUTY and leaves in-burst amplitude alone.\n")
res = {}
for T, tag in T_LIST:
    print(f"  --- {tag} ---")
    print(f"  {'arm':<12} {'n':>5} {'unit':>5} {'median all':>11} | {'duty':>6} {'[95% CI]':>16} | "
          f"{'in-burst p50':>13} {'v_med':>6}")
    for k in ORDER:
        rs = ACTIVE.get(k, [])
        nb = len({r[G.EPKEY] for r in rs})
        if len(rs) < 10 or nb < 3:
            print(f"  {k:<12} {len(rs):>5} {nb:>5}   *** UNDERPOWERED / EMPTY")
            res[f"{tag}|{k}"] = dict(n=len(rs), nb=nb, underpowered=True)
            continue
        v = G.col(rs, "e_18-22")
        v = v[np.isfinite(v)]
        burst = [r for r in rs if np.isfinite(r["e_18-22"]) and r["e_18-22"] >= T]
        duty, dlo, dhi = boot_units(rs, lambda x: float(np.mean(x >= T)))
        if len(burst) >= 5 and len({r[G.EPKEY] for r in burst}) >= 3:
            ib = boot_units(burst, np.median)[0]
        else:
            ib = np.nan
        res[f"{tag}|{k}"] = dict(n=len(rs), nb=nb, med=float(np.median(v)), duty=duty, dlo=dlo,
                                 dhi=dhi, inburst=ib, nburst=len(burst),
                                 vmed=float(np.median([r["v"] for r in rs])))
        print(f"  {k:<12} {len(rs):>5} {nb:>5} {np.median(v):>11.0f} | {duty:>6.3f} "
              f"[{dlo:>6.3f},{dhi:>7.3f}] | " +
              (f"{ib:>13.0f}" if np.isfinite(ib) else f"{'(' + str(len(burst)) + ' win)':>13}") +
              f" {res[f'{tag}|{k}']['vmed']:>6.2f}")
    print()
OUT["duty_amplitude"] = res

# the paired ratios that matter, with their own split-half nulls
N.hdr("2. V74's DUTY against its predecessors -- ratio, CI, and V74's own split-half null")
v74 = ACTIVE["V74/r5d"]
for T, tag in T_LIST:
    def dutyf(x, T=T):
        return float(np.mean(x >= T))
    d74 = boot_units(v74, dutyf)
    # split-half null on the SAME statistic, same unit
    eps = {}
    for r in v74:
        eps.setdefault(r[G.EPKEY], []).append(r)
    ks = list(eps)
    nulls = []
    for _ in range(400):
        p = RNG.permutation(len(ks))
        h = len(ks) // 2
        a = np.concatenate([G.col(eps[ks[i]], "e_18-22") for i in p[:h]])
        b = np.concatenate([G.col(eps[ks[i]], "e_18-22") for i in p[h:]])
        if len(a) and len(b) and dutyf(b) > 0:
            nulls.append(dutyf(a) / dutyf(b))
    nlo, nhi = (np.nanpercentile(nulls, [2.5, 97.5]) if len(nulls) > 20 else (np.nan, np.nan))
    print(f"  --- {tag} --- V74 duty {d74[0]:.3f} [{d74[1]:.3f}, {d74[2]:.3f}]   "
          f"split-half null on the DUTY RATIO [{nlo:.3f}, {nhi:.3f}]")
    for k in ("V73/r5a", "V72/r59", "V71C/r58", "V67+V68", "stock pool", "V62+V65"):
        rs = ACTIVE.get(k, [])
        if len(rs) < 10:
            continue
        eb = {}
        for r in rs:
            eb.setdefault(r[G.EPKEY], []).append(r)
        kb = list(eb)
        ka = list(eps)
        dr = np.full(2000, np.nan)
        for i in range(2000):
            a = np.concatenate([G.col(eps[ka[j]], "e_18-22")
                                for j in RNG.integers(0, len(ka), len(ka))])
            b = np.concatenate([G.col(eb[kb[j]], "e_18-22")
                                for j in RNG.integers(0, len(kb), len(kb))])
            if dutyf(b) > 0:
                dr[i] = dutyf(a) / dutyf(b)
        db = boot_units(rs, dutyf)
        pt = d74[0] / db[0] if db[0] else np.nan
        lo, hi = np.nanpercentile(dr, [2.5, 97.5])
        cl = "CLEARS" if (np.isfinite(nlo) and (lo > nhi or hi < nlo)) else "inside null"
        print(f"      vs {k:<12} other duty {db[0]:.3f}   ratio {pt:6.3f} [{lo:6.3f}, {hi:6.3f}] "
              f"  {cl}")
        OUT.setdefault("duty_ratio", {})[f"{tag}|{k}"] = dict(ratio=float(pt), lo=float(lo),
                                                              hi=float(hi), null=[float(nlo),
                                                                                  float(nhi)],
                                                              other=db[0], v74=d74[0], verdict=cl)
    print()

# ================================================== 3. THE bit7 DOSE-RESPONSE =====================
N.hdr("3. ★★★★ THE WITHIN-ROUTE DAMPER CONTRAST -- bit7 = (gp-0x6bd0 != 0), the damper's OWN output")
print("  🛑 CONFOUNDED BY CONSTRUCTION. The damper's input is a motor rate, so bit7 duty rises with")
print("  steering rate, and steering rate drives both symptoms. The unmatched split is printed")
print("  FIRST precisely to show the size of the confound; only the rate-matched rows are readable.")
print("  ⚠ And a further limit that no stratification fixes: `damp` is a DUTY, not a dose. bit7 says")
print("  the damper produced SOMETHING, never how much, so a within-route contrast can only ever")
print("  separate `damper active` from `damper idle` -- it cannot measure a dose-RESPONSE slope.\n")
eng = [r for r in store["V74/r5d"] if r["eng"] == 1 and np.isfinite(r.get("damp", np.nan))]
print(f"  engaged windows with a finite probe: {len(eng)}   damp duty distribution:")
dd = np.array([r["damp"] for r in eng])
for lo, hi in ((0.0, 0.05), (0.05, 0.35), (0.35, 0.65), (0.65, 0.95), (0.95, 1.01)):
    print(f"      damp in [{lo:.2f},{hi:.2f}): {int(((dd >= lo) & (dd < hi)).sum()):>4} windows")

RB = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 1e9)]
RN = ["0-4", "4-16", "16-32", "32+"]
VB = [(0.5, 4.0), (4.0, 9.4), (9.4, 18.7), (18.7, 40.0)]
VN = ["0.5-4", "4-9.4", "9.4-18.7", "18.7+"]
for key, kl in (("e_6-9", "MICRO RATCHET 6-9 Hz"), ("e_18-22", "GRIND #1 18-22 Hz"),
                ("e_24-28", "CONTROL 24-28 Hz")):
    print(f"\n  --- {kl} ---")
    hi_ = [r for r in eng if r["damp"] >= 0.5]
    lo_ = [r for r in eng if r["damp"] < 0.5]
    a, b = boot_units(hi_, np.median, key), boot_units(lo_, np.median, key)
    print(f"    UNMATCHED  damp>=0.5 n={len(hi_):>3} median {a[0]:8.1f}   "
          f"damp<0.5 n={len(lo_):>3} median {b[0]:8.1f}   ratio {a[0] / max(b[0], 1e-9):6.3f}")
    print(f"    {'rate bin':>9} {'speed bin':>10} {'n hi':>5} {'n lo':>5} {'median hi':>10} "
          f"{'median lo':>10} {'ratio':>7}")
    cells = []
    for (rlo, rhi), rn in zip(RB, RN):
        for (vlo, vhi), vn in zip(VB, VN):
            h = [r for r in hi_ if rlo <= r["rate_lp"] < rhi and vlo <= r["v"] < vhi]
            l = [r for r in lo_ if rlo <= r["rate_lp"] < rhi and vlo <= r["v"] < vhi]
            if len(h) < 6 or len(l) < 6:
                continue
            mh, ml = float(np.median(G.col(h, key))), float(np.median(G.col(l, key)))
            w = 1.0 / (1.0 / len(h) + 1.0 / len(l))
            cells.append((np.log(mh / ml), w, rn, vn, len(h), len(l), mh, ml))
            print(f"    {rn:>9} {vn:>10} {len(h):>5} {len(l):>5} {mh:>10.1f} {ml:>10.1f} "
                  f"{mh / ml:>7.3f}")
    if cells:
        num = sum(c[0] * c[1] for c in cells)
        den = sum(c[1] for c in cells)
        # episode bootstrap over the pooled cells
        dr = np.full(2000, np.nan)
        eph = {}
        for r in eng:
            eph.setdefault(r[G.EPKEY], []).append(r)
        kk = list(eph)
        for i in range(2000):
            samp = [r for j in RNG.integers(0, len(kk), len(kk)) for r in eph[kk[j]]]
            n2 = d2 = 0.0
            for (rlo, rhi), rn in zip(RB, RN):
                for (vlo, vhi), vn in zip(VB, VN):
                    h = [r for r in samp if r["damp"] >= 0.5 and rlo <= r["rate_lp"] < rhi
                         and vlo <= r["v"] < vhi]
                    l = [r for r in samp if r["damp"] < 0.5 and rlo <= r["rate_lp"] < rhi
                         and vlo <= r["v"] < vhi]
                    if len(h) < 6 or len(l) < 6:
                        continue
                    mh, ml = np.median(G.col(h, key)), np.median(G.col(l, key))
                    if mh > 0 and ml > 0:
                        w = 1.0 / (1.0 / len(h) + 1.0 / len(l))
                        n2 += w * np.log(mh / ml)
                        d2 += w
            if d2:
                dr[i] = np.exp(n2 / d2)
        lo95, hi95 = np.nanpercentile(dr, [2.5, 97.5])
        pt = float(np.exp(num / den))
        print(f"    ⇒ RATE+SPEED MATCHED, {len(cells)} cells:  damper-active / damper-idle = "
              f"{pt:.3f} [{lo95:.3f}, {hi95:.3f}]")
        OUT.setdefault("bit7", {})[key] = dict(matched=pt, lo=float(lo95), hi=float(hi95),
                                               cells=len(cells),
                                               unmatched=float(a[0] / max(b[0], 1e-9)))

with open(ROOT / f"_r5d_duty_{G.EPKEY}.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print(f"\nwrote _r5d_duty_{G.EPKEY}.json")
