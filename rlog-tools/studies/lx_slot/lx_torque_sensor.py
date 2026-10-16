#!/usr/bin/env python3
"""LX vs operator TORQUE-SENSOR comparison (follow-up to TRACE-2026-10-05-lx-rlog-slot-inference §8).

Cache-only (`_scratch/cache/<route>/lx_slot.npz` from extract_lx_slot.py), runs in ~1 s.
  1. AT REST (vEgo == 0): 0x18F column-torque raw offset / p-p / max / histogram; 0x14A angle+rate; 0x1AB bytes.
  2. DRIVING, manual, speed bins: |0x18F| p50/p90/p99; torque vs |angle| and vs |rate| on shared axes; LX/operator
     ratio per bin with bootstrap CI -> scale vs offset vs harder-driving verdict.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
# --- END PATH BOOTSTRAP ----------------------------------------------------
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(_repo); CACHE = REPO / "_scratch" / "cache"; FIG = REPO / "analysis-2020accord" / "figures" / "lx_slot"
ROUTES = {"LX a6 (2019, stock)": "b308cfc5781b463d_000000a6--f3e9e379ee",
          "op r97 (STOCK V9b)": "75604b0a432fdc89_00000097--489d7896b3",
          "op r2b (V58)": "75604b0a432fdc89_0000002b--7926e8f7e5",
          "op r2c (V59)": "75604b0a432fdc89_0000002c--eb219f392c"}
COL = {"LX a6 (2019, stock)": "#c0392b", "op r97 (STOCK V9b)": "#1f4e79", "op r2b (V58)": "#2e86c1", "op r2c (V59)": "#85c1e9"}
RNG = np.random.default_rng(1)


def hold(ts, xs, t):
    return xs[np.clip(np.searchsorted(ts, t) - 1, 0, len(ts) - 1)]


def load(route):
    z = np.load(CACHE / route / "lx_slot.npz"); d = {k: z[k] for k in z.files if k != "meta"}
    t = d["t18f"]
    d["v"] = hold(d["tcs"], d["vego"], t); d["pressed"] = hold(d["tcs"], d["pressed"], t)
    d["ang"] = hold(d["t14a"], d["ang"], t).astype(float) * -0.1          # deg (DBC -0.1)
    d["r14"] = hold(d["t14a"], d["rate14a"], t).astype(float) * -1.0      # deg/s (DBC -1)
    d["lat"] = hold(d["tcc"], d["lat"], t) if len(d["tcc"]) else np.zeros(len(t), int)
    m = d["src_e4"] == 101
    d["req"] = hold(d["te4"][m], d["req_e4"][m], t) if m.any() else np.zeros(len(t), int)
    d["manual"] = (d["ctrl"] == 0) & (d["lat"] == 0) & (d["req"] == 0)
    d["tq"] = d["tq18f"].astype(float)
    d["mt"] = hold(d["t1ab"], d["mt"], t); d["b0"] = hold(d["t1ab"], d["b0_1ab"], t); d["b2"] = hold(d["t1ab"], d["b2_1ab"], t)
    return d


def runs(mask, t, min_s):
    """contiguous True runs of mask lasting >= min_s seconds -> list of index slices"""
    idx = np.flatnonzero(np.diff(np.r_[0, mask.astype(int), 0]))
    out = []
    for a, b in zip(idx[::2], idx[1::2]):
        if t[b - 1] - t[a] >= min_s:
            out.append(slice(a, b))
    return out


def main():
    D = {k: load(v) for k, v in ROUTES.items()}
    print("=== 1. AT REST (vEgo == 0 for >= 3 s, 0x18F torque |value| < 4000 i.e. not leaning on a stop; steeringPressed = 0)")
    rest = {}
    for k, d in D.items():
        m = (d["v"] == 0) & (d["pressed"] == 0) & (d["manual"])
        rs = runs(m, d["t18f"], 3.0)
        sel = np.zeros(len(d["tq"]), bool)
        for s in rs: sel[s] = True
        tq = d["tq"][sel]; rest[k] = tq
        q = np.percentile(tq, [0.1, 1, 50, 99, 99.9]) if len(tq) else [np.nan] * 5
        print(f"  {k:22s} runs {len(rs):3d} frames {sel.sum():6d} | torque mean {tq.mean():7.2f} median {np.median(tq):6.1f} std {tq.std():6.2f} "
              f"p0.1/p1/p99/p99.9 {q[0]:.0f}/{q[1]:.0f}/{q[3]:.0f}/{q[4]:.0f} max|.| {np.abs(tq).max():.0f} "
              f"| angle p50 {np.median(d['ang'][sel]):6.1f} rate |max| {np.abs(d['r14'][sel]).max():4.0f} rate18f |max| {np.abs(d['rate18f'][sel]).max():4.0f} "
              f"| 0x1AB mt nonzero {100*(d['mt'][sel]>0).mean():4.1f}% max {d['mt'][sel].max()} b0 {sorted(set(d['b0'][sel].tolist()))} b2&0x40 {int(((d['b2'][sel]>>6)&1).sum())}")
        # quiet-hands subset: |tq| < 300
        qh = tq[np.abs(tq) < 300]
        if len(qh): print(f"      quiet subset |tq|<300: n {len(qh)} mean {qh.mean():6.2f} p-p(p1..p99) {np.percentile(qh,99)-np.percentile(qh,1):.0f} std {qh.std():.2f}")
        # WHEEL-STILL subset: runs where the 0x14A rate never exceeds 1 deg/s and the fine rate never exceeds 8
        still = np.zeros(len(d["tq"]), bool)
        for r_ in rs:
            if np.abs(d["r14"][r_]).max() <= 1 and np.abs(d["rate18f"][r_]).max() <= 8:
                still[r_] = True
        if still.sum():
            ts_ = d["tq"][still]
            print(f"      WHEEL-STILL runs: frames {still.sum()} mean {ts_.mean():6.2f} median {np.median(ts_):5.0f} std {ts_.std():5.2f} p1/p99 {np.percentile(ts_,1):.0f}/{np.percentile(ts_,99):.0f} max|.| {np.abs(ts_).max():.0f} | distinct values {len(np.unique(ts_))}")
        else:
            print("      WHEEL-STILL runs: none")
        # first 5 s of the route
        f5 = d["t18f"] < 5.0
        print(f"      first 5 s of route: v p50 {np.median(d['v'][f5]):.2f} torque mean {d['tq'][f5].mean():.1f} max|.| {np.abs(d['tq'][f5]).max():.0f} status {sorted(set(d['status'][f5].tolist()))} mt max {d['mt'][f5].max()}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for k, tq in rest.items():
        axes[0].hist(tq, bins=np.arange(-400, 401, 8), histtype="step", density=True, color=COL[k], label=f"{k} n={len(tq)}")
        axes[1].hist(tq, bins=np.arange(-4000, 4001, 50), histtype="step", density=True, color=COL[k], log=True)
    axes[0].set_xlabel("0x18F STEER_TORQUE_SENSOR raw, at rest (vEgo=0, hands off per carState)"); axes[0].set_ylabel("density"); axes[0].legend(fontsize=7)
    axes[1].set_xlabel("same, full range (log density)"); axes[0].set_title("torque sensor AT REST"); axes[1].set_title("tails = hands on the wheel while parked")
    fig.tight_layout(); fig.savefig(FIG / "fig5_rest_torque_hist.png", dpi=130); plt.close(fig)

    print("\n=== 2. DRIVING, MANUAL, hands-on (|tq| > 50): |0x18F| percentiles and ratio LX/op per bin")
    SB = [(5, 10), (10, 20), (20, 50)]
    ABINS = [0, 5, 10, 20, 40, 80, 160, 320, 420]
    RBINS = [0, 10, 20, 40, 80, 160, 320, 640]
    tab = {}
    for k, d in D.items():
        tab[k] = {}
        for lo, hi in SB:
            m = d["manual"] & (d["v"] >= lo) & (d["v"] < hi) & (np.abs(d["tq"]) > 50)
            a = np.abs(d["tq"][m]); ang = np.abs(d["ang"][m]); r = np.abs(d["r14"][m])
            pc = np.percentile(a, [50, 90, 99]) if m.sum() > 50 else [np.nan] * 3
            print(f"  {k:22s} {lo:2d}-{hi:2d} m/s n {m.sum():6d} |tq| p50/p90/p99 {pc[0]:6.0f}/{pc[1]:6.0f}/{pc[2]:6.0f}")
            ba = [(0.5 * (x + y), np.median(a[(ang >= x) & (ang < y)]), ((ang >= x) & (ang < y)).sum()) for x, y in zip(ABINS[:-1], ABINS[1:]) if ((ang >= x) & (ang < y)).sum() >= 30]
            br = [(0.5 * (x + y), np.median(a[(r >= x) & (r < y)]), ((r >= x) & (r < y)).sum()) for x, y in zip(RBINS[:-1], RBINS[1:]) if ((r >= x) & (r < y)).sum() >= 30]
            tab[k][(lo, hi)] = dict(a=a, ang=ang, r=r, ba=ba, br=br)
    # ratio LX / r97 (and / r2b, r2c) per angle bin at matched speed, bootstrap CI on medians
    print("\n  ratio of MEDIAN |tq| LX / operator in matched (speed, |angle|) bins (bootstrap 95% CI):")
    lx = tab["LX a6 (2019, stock)"]
    for opk in list(ROUTES)[1:]:
        for sb in SB:
            L = lx[sb]; O = tab[opk][sb]
            for x, y in zip(ABINS[:-1], ABINS[1:]):
                ml = (L["ang"] >= x) & (L["ang"] < y); mo = (O["ang"] >= x) & (O["ang"] < y)
                if ml.sum() < 30 or mo.sum() < 30: continue
                al, ao = L["a"][ml], O["a"][mo]
                bs = [np.median(RNG.choice(al, len(al))) / np.median(RNG.choice(ao, len(ao))) for _ in range(300)]
                print(f"    LX/{opk:18s} {sb[0]:2d}-{sb[1]:2d} m/s |angle| {x:3d}-{y:3d} deg: {np.median(al)/np.median(ao):5.2f} "
                      f"[{np.percentile(bs,2.5):.2f}, {np.percentile(bs,97.5):.2f}]  (LX med {np.median(al):5.0f} n {ml.sum():5d} | op med {np.median(ao):5.0f} n {mo.sum():5d})")
    # physical relation: |tq| vs lateral-acceleration proxy  a_y ~ v^2 * angle / (SR * L), SR 16.3, L 2.83 m, manual, v > 3 m/s
    print("\n  |0x18F| vs lateral-acceleration proxy (v^2*|angle|/(16.3*2.83), m/s^2), manual, v > 3 m/s, hands-on |tq|>50:")
    LB = [0, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6]
    lat = {}
    for k, d in D.items():
        m = d["manual"] & (d["v"] > 3) & (np.abs(d["tq"]) > 50)
        ay = d["v"][m] ** 2 * np.abs(np.deg2rad(d["ang"][m])) / (16.3 * 2.83); a = np.abs(d["tq"][m])
        lat[k] = (ay, a)
        row = [(0.5 * (x + y), np.median(a[(ay >= x) & (ay < y)]), ((ay >= x) & (ay < y)).sum()) for x, y in zip(LB[:-1], LB[1:]) if ((ay >= x) & (ay < y)).sum() >= 30]
        print(f"  {k:22s} n {m.sum():6d}: " + "  ".join(f"ay~{c:.2f}: {md:.0f} (n{n})" for c, md, n in row))
    ayl, al = lat["LX a6 (2019, stock)"]
    for opk in list(ROUTES)[1:]:
        ayo, ao = lat[opk]
        for x, y in zip(LB[:-1], LB[1:]):
            ml = (ayl >= x) & (ayl < y); mo = (ayo >= x) & (ayo < y)
            if ml.sum() < 30 or mo.sum() < 30: continue
            bs = [np.median(RNG.choice(al[ml], ml.sum())) / np.median(RNG.choice(ao[mo], mo.sum())) for _ in range(300)]
            print(f"    LX/{opk:18s} ay {x:4.2f}-{y:4.2f}: ratio {np.median(al[ml])/np.median(ao[mo]):4.2f} [{np.percentile(bs,2.5):.2f}, {np.percentile(bs,97.5):.2f}]  LX {np.median(al[ml]):5.0f} n{ml.sum():5d} | op {np.median(ao[mo]):5.0f} n{mo.sum():4d}")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for k, (ay, a) in lat.items():
        row = [(0.5 * (x + y), np.median(a[(ay >= x) & (ay < y)])) for x, y in zip(LB[:-1], LB[1:]) if ((ay >= x) & (ay < y)).sum() >= 30]
        if row: ax.plot([r_[0] for r_ in row], [r_[1] for r_ in row], "-o", color=COL[k], ms=4, label=k)
    ax.set_xlabel("lateral-acceleration proxy v^2*|angle|/(SR*L)  [m/s^2]"); ax.set_ylabel("median |0x18F torque| raw"); ax.grid(alpha=.3); ax.legend(fontsize=7)
    ax.set_title("driver column torque vs lateral acceleration, manual, v > 3 m/s")
    fig.tight_layout(); fig.savefig(FIG / "fig7_driving_torque_vs_latacc.png", dpi=130); plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for j, sb in enumerate(SB):
        for k in ROUTES:
            T = tab[k][sb]
            if T["ba"]: axes[0, j].plot([p[0] for p in T["ba"]], [p[1] for p in T["ba"]], "-o", color=COL[k], ms=4, label=k)
            if T["br"]: axes[1, j].plot([p[0] for p in T["br"]], [p[1] for p in T["br"]], "-o", color=COL[k], ms=4, label=k)
        axes[0, j].set_title(f"manual {sb[0]}-{sb[1]} m/s: median |0x18F| vs |angle|"); axes[0, j].set_xlabel("|0x14A angle| deg"); axes[0, j].set_xscale("symlog", linthresh=10)
        axes[1, j].set_title(f"manual {sb[0]}-{sb[1]} m/s: median |0x18F| vs |rate|"); axes[1, j].set_xlabel("|0x14A rate| deg/s"); axes[1, j].set_xscale("symlog", linthresh=10)
        for ax in axes[:, j]: ax.grid(alpha=.3); ax.set_ylabel("median |torque| raw")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Torque sensor, manual driving: LX vs operator on the same axes (operator has almost no manual >5 m/s)")
    fig.tight_layout(); fig.savefig(FIG / "fig6_driving_torque_vs_angle_rate.png", dpi=130); plt.close(fig)
    print(f"\nfigures -> {FIG}")


if __name__ == "__main__":
    main()
