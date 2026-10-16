#!/usr/bin/env python3
"""LX-vs-operator slot inference from the wire (TRACE-2026-10-05-lx-rlog-slot-inference).

Reads ONLY the `_scratch/cache/<route>/lx_slot.npz` caches written by `extract_lx_slot.py` (seconds to run),
plus the STOCK image for the family curves.  Writes figures to `analysis-2020accord/figures/lx_slot/` and
prints every number the trace quotes.

Routes:
  LX   b308cfc5781b463d_000000a6--f3e9e379ee   2019 Accord LX, unknown EPS slot, stock firmware
  r97  75604b0a432fdc89_00000097--489d7896b3   operator's car, V9b STOCK flight (no cave, no cal edit, stock packer)
  r2b  75604b0a432fdc89_0000002b--7926e8f7e5   operator's car, V58 (V38 cal set + LKAS-only cells; stock 427 packer, mode-24 records byte-stock)
  r2c  75604b0a432fdc89_0000002c--eb219f392c   operator's car, V59 (same class as V58)
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
import struct
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(_repo)
CACHE = REPO / "_scratch" / "cache"
FIG = REPO / "analysis-2020accord" / "figures" / "lx_slot"
FIG.mkdir(parents=True, exist_ok=True)
STOCK = Path(_os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / \
    "analysis-2020accord" / "stock_fw_dump" / "code.bin"

ROUTES = {
    "LX (2019, stock)": "b308cfc5781b463d_000000a6--f3e9e379ee",
    "op r97 (2020, STOCK V9b)": "75604b0a432fdc89_00000097--489d7896b3",
    "op r2b (2020, V58)": "75604b0a432fdc89_0000002b--7926e8f7e5",
    "op r2c (2020, V59)": "75604b0a432fdc89_0000002c--eb219f392c",
}
COL = {"LX (2019, stock)": "#c0392b", "op r97 (2020, STOCK V9b)": "#1f4e79",
       "op r2b (2020, V58)": "#2e86c1", "op r2c (2020, V59)": "#5dade2"}
SPEED_BINS = [(0, 5), (5, 10), (10, 20), (20, 50)]
TQ_BINS = [0, 100, 200, 300, 400, 600, 800, 1200, 1600, 2000, 2500, 3000, 4000, 6000]
RNG = np.random.default_rng(0)


def hold(t_src, x_src, t_dst):
    i = np.clip(np.searchsorted(t_src, t_dst) - 1, 0, len(t_src) - 1)
    return x_src[i]


def load(route):
    z = np.load(CACHE / route / "lx_slot.npz")
    d = {k: z[k] for k in z.files if k != "meta"}
    t = d["t1ab"]
    d["v"] = hold(d["tcs"], d["vego"], t) if len(d["tcs"]) else np.full(len(t), np.nan)
    d["v158h"] = hold(d["t158"], d["v158"], t)
    d["tq"] = hold(d["t18f"], d["tq18f"], t).astype(float)
    d["ctrl1"] = hold(d["t18f"], d["ctrl"], t)
    d["status1"] = hold(d["t18f"], d["status"], t)
    d["lat1"] = hold(d["tcc"], d["lat"], t) if len(d["tcc"]) else np.zeros(len(t), int)
    # openpilot's own 0xE4 request (sendcan bus 1 => src 101), held onto the 0x1AB grid
    m = d["src_e4"] == 101
    d["req1"] = hold(d["te4"][m], d["req_e4"][m], t) if m.any() else np.zeros(len(t), int)
    d["pressed1"] = hold(d["tcs"], d["pressed"], t) if len(d["tcs"]) else np.zeros(len(t), int)
    # MANUAL = EPS says LKAS not active AND openpilot not lateral-active AND no steer request on the wire
    d["manual"] = (d["ctrl1"] == 0) & (d["lat1"] == 0) & (d["req1"] == 0)
    return d


def summarise(name, d):
    t = d["t1ab"]
    print(f"\n=== {name}  route {ROUTES[name]}")
    print(f"  0x1AB {len(t):,} frames @ {1/np.median(np.diff(t)):.1f} Hz | 0x18F {len(d['t18f']):,} | 0x14A {len(d['t14a']):,} "
          f"| carState {len(d['tcs']):,} | vEgo max {np.nanmax(d['vego']) if len(d['vego']) else float('nan'):.1f} m/s")
    mt = d["mt"]
    print(f"  0x1AB MOTOR_TORQUE: distinct {len(np.unique(mt))}, max {mt.max()}, mean {mt.mean():.2f}, "
          f"nonzero {100*(mt>0).mean():.1f} %, p50/p90/p99/p99.9 = {np.percentile(mt,[50,90,99,99.9]).round(1)}")
    b0 = d["b0_1ab"]; b2 = d["b2_1ab"]
    print(f"  0x1AB b0 values {dict(zip(*np.unique(b0, return_counts=True)))} | b0 bit2 (DTC) set {((b0>>2)&1).sum()} "
          f"| b0 bit7 CONFIG_VALID {((b0>>7)&1).mean():.3f} | b2 bit6 OUTPUT_DISABLED {((b2>>6)&1).sum()}")
    st = d["status"]
    print(f"  0x18F STEER_STATUS values {dict(zip(*np.unique(st, return_counts=True)))} | STEER_CONTROL_ACTIVE frac {d['ctrl'].mean():.3f} "
          f"| b5 bit4 set {d['b5b4'].sum()}")
    v18 = hold(d["t158"], d["v158"], d["t18f"])
    for s in np.unique(st):
        m = st == s
        print(f"    status {s}: n {m.sum():6d}  0x158 speed km/h p5/p50/p95 {np.percentile(v18[m],[5,50,95]).round(1)}")
    e30 = np.where((st[1:] == 0) & (st[:-1] == 3))[0]
    if len(e30):
        print(f"    3->0 release speed km/h: n {len(e30)} median {np.median(v18[e30+1]):.1f} (IQR {np.percentile(v18[e30+1],[25,75]).round(1)})")
    print(f"  0x18F |torque| p50/p90/p99/p99.9 {np.percentile(np.abs(d['tq18f']),[50,90,99,99.9]).round(0)} | "
          f"max |rate18f| {np.abs(d['rate18f']).max()} | max |0x14A rate| {np.abs(d['rate14a']).max()} | max |angle| {np.abs(d['ang']).max()*0.1:.0f} deg")
    print(f"  manual frac (0x1AB grid) {d['manual'].mean():.3f} | latActive frac {d['lat1'].mean():.3f} | OP req frac {d['req1'].mean():.3f}")
    # 0x14A rate vs 0x18F rate scale (both EPS-built): ratio of robust slopes
    r14 = hold(d["t14a"], d["rate14a"], d["t18f"]).astype(float); r18 = d["rate18f"].astype(float)
    m = np.abs(r18) > 200
    if m.sum() > 100:
        k = np.median(r14[m] / r18[m])
        print(f"  0x14A rate / 0x18F rate (|r18|>200): median ratio {k:.4f}  (n {m.sum()})")


def manual_relation(name, d):
    out = {}
    m0 = d["manual"] & np.isfinite(d["v"])
    for lo, hi in SPEED_BINS:
        m = m0 & (d["v"] >= lo) & (d["v"] < hi)
        a = np.abs(d["tq"][m]); y = d["mt"][m].astype(float)
        rows = []
        for k in range(len(TQ_BINS) - 1):
            s = (a >= TQ_BINS[k]) & (a < TQ_BINS[k + 1])
            if s.sum() >= 30:
                rows.append((0.5 * (TQ_BINS[k] + TQ_BINS[k + 1]), int(s.sum()), np.median(y[s]), np.mean(y[s]),
                             np.percentile(y[s], 90), (y[s] > 0).mean()))
        # slope of mean(mt) on |tq| by least squares through the origin on the raw frames + bootstrap CI
        if m.sum() > 200:
            slope = (a * y).sum() / (a * a).sum()
            bs = []
            idx = np.arange(len(a))
            for _ in range(300):
                j = RNG.choice(idx, len(idx))
                bs.append((a[j] * y[j]).sum() / (a[j] * a[j]).sum())
            ci = np.percentile(bs, [2.5, 97.5])
        else:
            slope, ci = np.nan, (np.nan, np.nan)
        out[(lo, hi)] = dict(n=int(m.sum()), rows=rows, slope=slope, ci=ci)
    return out


def family_curves():
    b = STOCK.read_bytes()
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]
    curves = {}
    for idx in (0, 10, 11, 24, 26):
        p = u32(0xCA154 + 4 * idx)
        n = u16(p)
        X = [u16(p + 2 + 2 * k) for k in range(n)]
        Y = [u16(p + 2 + 2 * n + 2 * k) for k in range(n)]
        curves[idx] = (p, X, Y)
    return curves


def main():
    data = {k: load(v) for k, v in ROUTES.items()}
    for k, d in data.items():
        summarise(k, d)

    # ---------- family curves from the stock image ----------
    cv = family_curves()
    print("\n=== base-assist boost-curve families (stock image, LE, @0xCA154 pointer array)")
    for idx, (p, X, Y) in cv.items():
        print(f"  idx {idx:2d} @{p:#x}  X {X}  Y {Y}")
    _, X10, Y10 = cv[10]; _, X24, Y24 = cv[24]
    xs = np.arange(0, 10241, 64)
    y10 = np.interp(xs, X10, Y10); y24 = np.interp(xs, X24, Y24)
    rel = (y24 - y10) / y10
    print(f"  family 24 vs 10 over 0..10240 column counts: rel diff min {rel.min()*100:+.2f} % max {rel.max()*100:+.2f} % "
          f"(abs max {np.abs(y24-y10).max():.0f} of ~650)")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    _, X0, Y0 = cv[0]
    ax.plot(X0, Y0, "-o", color="#999", lw=1, ms=3, label="idx 0 (slot 0 blank key, RISING family)")
    ax.plot(X10, Y10, "-o", color="#1f4e79", lw=2, ms=4, label="idx 10 (TVAA1 slot 2, LX hypothesis)")
    ax.plot(X24, Y24, "--s", color="#c0392b", lw=2, ms=4, label="idx 24 (TVCA4 slot 11, operator MEASURED)")
    ax.set_xlabel("column torque X (counts, record units)"); ax.set_ylabel("assist gain Y (record units)")
    ax.set_title("Base-assist boost-curve families from the STOCK image (byte-read, LE)")
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax2 = ax.twinx(); ax2.plot(xs, rel * 100, color="#e67e22", lw=1); ax2.set_ylabel("24 vs 10 (%)", color="#e67e22")
    ax2.set_ylim(-5, 5)
    fig.tight_layout(); fig.savefig(FIG / "fig1_family_curves_10_vs_24.png", dpi=130); plt.close(fig)

    # ---------- manual relation ----------
    rel_out = {k: manual_relation(k, d) for k, d in data.items()}
    print("\n=== MANUAL windows (EPS STEER_CONTROL_ACTIVE=0, latActive=0, no OP steer request): 0x1AB vs |0x18F| (raw wire counts)")
    for k, o in rel_out.items():
        print(f"  {k}")
        for sb, r in o.items():
            print(f"    speed {sb[0]:2d}-{sb[1]:2d} m/s  n {r['n']:6d}  slope mt/|tq| = {r['slope']*1e3:.3f}e-3  "
                  f"95% CI [{r['ci'][0]*1e3:.3f}, {r['ci'][1]*1e3:.3f}]e-3")
            for row in r["rows"]:
                print(f"       |tq| ~{row[0]:5.0f}  n {row[1]:5d}  mt med {row[2]:5.1f} mean {row[3]:6.2f} p90 {row[4]:6.1f} nonzero {row[5]*100:4.1f} %")

    fig, axes = plt.subplots(1, len(SPEED_BINS), figsize=(16, 4.2), sharey=True)
    for ax, sb in zip(axes, SPEED_BINS):
        for k, o in rel_out.items():
            r = o[sb]
            if not r["rows"]:
                continue
            xs_ = [row[0] for row in r["rows"]]; ys_ = [row[3] for row in r["rows"]]; p90 = [row[4] for row in r["rows"]]
            ax.plot(xs_, ys_, "-o", color=COL[k], ms=4, lw=1.8, label=f"{k} mean (n={r['n']})")
            ax.plot(xs_, p90, ":", color=COL[k], lw=1)
        ax.set_title(f"manual, {sb[0]}-{sb[1]} m/s"); ax.set_xlabel("|0x18F STEER_TORQUE_SENSOR| (raw counts)")
        ax.grid(alpha=.3); ax.set_yscale("symlog", linthresh=5)
    axes[0].set_ylabel("0x1AB MOTOR_TORQUE (10-bit, = |gp-0x6c18|*5>>3 on stock)\nsolid mean, dotted p90")
    axes[0].legend(fontsize=7)
    fig.suptitle("0x1AB vs driver column torque, MANUAL only: LX vs operator (stock + V58/V59 controls)")
    fig.tight_layout(); fig.savefig(FIG / "fig2_manual_1ab_vs_18f.png", dpi=130); plt.close(fig)

    # ---------- status-vs-speed and 0x18F torque distributions ----------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for k, d in data.items():
        a = np.abs(d["tq18f"]); a = a[a > 0]
        axes[0].hist(a, bins=np.linspace(0, 6000, 61), histtype="step", density=True, color=COL[k], label=k)
        v18 = hold(d["t158"], d["v158"], d["t18f"]); st = d["status"]
        for s, mk in ((0, "o"), (3, "s"), (4, "^")):
            m = st == s
            if m.sum():
                axes[1].scatter(np.full(m.sum(), list(ROUTES).index(k)) + 0.15 * (s / 4 - 0.5) + RNG.normal(0, .02, m.sum()),
                                v18[m], s=1, color=COL[k], marker=mk, alpha=.3)
    axes[0].set_xlabel("|0x18F STEER_TORQUE_SENSOR| raw counts"); axes[0].set_ylabel("density"); axes[0].legend(fontsize=7)
    axes[0].set_title("driver column torque distribution (all frames, nonzero)")
    axes[1].set_xticks(range(len(ROUTES))); axes[1].set_xticklabels([k.split(" (")[0] for k in ROUTES], fontsize=8)
    axes[1].set_ylabel("0x158 speed km/h"); axes[1].set_title("STEER_STATUS by speed (o=0, s=3 low-speed lockout, ^=4)")
    axes[1].set_ylim(-2, 60); axes[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "fig3_torque_hist_and_status.png", dpi=130); plt.close(fig)

    # ---------- 0x1AB onset: fraction nonzero vs |tq| at <5 m/s, all frames (manual) ----------
    fig, ax = plt.subplots(figsize=(7, 4))
    for k, d in data.items():
        m = d["manual"] & (d["v"] < 5)
        a = np.abs(d["tq"][m]); y = d["mt"][m]
        xs_, fr, mn = [], [], []
        for lo, hi in zip(TQ_BINS[:-1], TQ_BINS[1:]):
            s = (a >= lo) & (a < hi)
            if s.sum() >= 30:
                xs_.append(0.5 * (lo + hi)); fr.append((y[s] > 0).mean()); mn.append(y[s].mean())
        ax.plot(xs_, fr, "-o", color=COL[k], ms=4, label=k)
    ax.set_xlabel("|0x18F STEER_TORQUE_SENSOR| raw counts"); ax.set_ylabel("P(0x1AB MOTOR_TORQUE > 0)")
    ax.set_title("0x1AB dead-zone onset vs column torque, manual, < 5 m/s"); ax.grid(alpha=.3); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig4_1ab_onset.png", dpi=130); plt.close(fig)
    print(f"\nfigures -> {FIG}")


if __name__ == "__main__":
    main()
