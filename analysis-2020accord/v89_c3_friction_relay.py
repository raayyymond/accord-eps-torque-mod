#!/usr/bin/env python3
"""v89_c3_friction_relay.py -- is the ENGAGEMENT-gated 6-9 Hz amplification the command-proportional
Coulomb relay?  And is `0xC40BC` = 6000 the lever that removes it?

WHAT v89_c2 ESTABLISHED on the full 30-route corpus (235 blocks):
    `eng` band contrast (6-9 minus 32-38) = +0.413 [+0.146, +0.667]  -- EXCLUDES 0
    => engaging LKAS multiplies the 6-9 Hz column mode by e^1.015 = 2.76x, and 1.51x MORE than it
       multiplies a 32-38 Hz control band. A CONSTANT, band-specific, engagement-gated amplification.
    `eng x log|rate|` contrast = +0.022 [-0.070, +0.116] -- NULL, and it REFUTES v89_a5's +0.144.
    => the amplification does NOT grow with wheel rate any faster than the control band does.
       🛑 There is therefore NO rate-dependent firmware term to attack, and NO reason to limit the
          LKAS command's angle rate. The operator's constraint is satisfied by the target itself.

WHY THAT POINTS AT A RELAY, and at ONE cell
On V87/V88 stock modes 24 == 26 are BYTE-IDENTICAL in all six factor families, so engaging changes
NO calibration. The only thing that changes is the LKAS command entering the aggregator. So a
constant 2.76x amplification that appears with engagement must come from the command's ENTRY moving
the loop through a nonlinearity.

`FUN_0003b8f6` is exactly that: a Coulomb relay whose output is PROPORTIONAL TO THE COMMAND. Its
`ratio` saturates against the gate `0xC40BC`, and at the stock gate it is pinned across 99.62% of
its range -- i.e. it behaves as a pure relay. Raising the gate widens the linear region and
DE-RELAYS it.

    0xC40BC = 600  on stock and on V87/V88 -- the car RIGHT NOW
    0xC40BC = 6000 on V85, V86, V86B only (routes 6e, 6f, 70)
    `STATE.md` says FREEZE AT 6000; the V87 rebase silently dropped it back to 600.

TEST: add a byte-derived FRIC flag (0xC40BC == 6000) and its interaction with engagement.
    H_A  de-relaying REDUCES the engagement-gated 6-9 Hz amplification
         => `eng x FRIC` band contrast is NEGATIVE  => restore 6000 on a V88 base.
    H_0  no effect => the relay is not the mechanism.
Power is reported explicitly: the flag lives on 3 routes, so a non-significant result is only
meaningful if the CI can resolve the +0.413 effect it is trying to remove.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FWD = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
CORPUS = ROOT / "_cache_r73" / "v89_c1_corpus.npy"
OUT = ROOT / "_cache_r73" / "v89_c3_friction.json"
RNG = np.random.default_rng(890808)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088
ROUTE_BUILD = {"4c": "v68", "4e": "v68", "r28": "v57", "r29": "v57", "r2b": "v58", "r2c": "v59",
               "r31": "v59", "r35": "v64", "r37": "v62", "r3a": "v65", "r3b": "v65", "r47": "v67",
               "r4f": "v69", "r50": "v70", "r58": "v71c", "r59": "v72", "r5a": "v73", "r5d": "v74",
               "r5e": "v75", "r61": "v74", "r65": "v76", "r66": "v80", "r67": "v81", "r68": "v83a",
               "r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b", "r71": "v87", "r73": "v88"}


def cell(tag, addr):
    h = sorted(FWD.glob(f"_{tag}_plain_image.bin")) or sorted(FWD.glob(f"_{tag}_*_plain_image.bin"))
    if not h:
        return None
    return struct.unpack_from("<H", h[0].read_bytes(), addr)[0]


def order_hits(v, lo, hi, nmax=6):
    if v <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        for n in range(1, nmax + 1):
            if lo <= n * v / circ < hi:
                return True
    return False


def spec(x, fs):
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    return np.fft.rfftfreq(len(x), 1.0 / fs), p


def brms(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def main():
    fric = {rt: (cell(b, 0xC40BC) == 6000) for rt, b in ROUTE_BUILD.items()}
    print("0xC40BC == 6000 (relay gate WIDE) on:",
          sorted(r for r, v in fric.items() if v) or "none")

    rows = []
    for rec in np.load(CORPUS, allow_pickle=True):
        rt = rec["route"]
        if rt not in fric or fric[rt] is None or rec["damper"] is None:
            continue
        fs = rec["fs"]
        tq, rate, v = rec["tq"], rec["rate"], rec["v"]
        eng, sst, seg = rec["eng"], rec["sst"], rec["seg"]
        sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        lf = np.zeros_like(tq)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, tq[g])
        for s in range(0, len(tq) - NW + 1, HOP):
            sl = slice(s, s + NW)
            e = eng[sl].mean()
            if not (e > 0.98 or e < 0.02):
                continue
            if (sst[sl] != 0).any() or not np.isfinite(tq[sl]).all():
                continue
            vm, rm = float(np.median(v[sl])), float(np.median(np.abs(rate[sl])))
            hm = float(np.median(np.abs(lf[sl])))
            if not (0.3 < vm < 8.0) or rm < 1.0 or hm < 1.0:
                continue
            if order_hits(vm, 6.0, 9.0) or order_hits(vm, 32.0, 38.0):
                continue
            f, p = spec(tq[sl], fs)
            a, b = brms(f, p, 6.0, 9.0), brms(f, p, 32.0, 38.0)
            if a <= 0 or b <= 0:
                continue
            rows.append({"route": rt, "fr": 1.0 if fric[rt] else 0.0,
                         "dm": 1.0 if rec["damper"] else 0.0,
                         "lb": 1.0 if rec["lever_b"] else 0.0,
                         "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0,
                         "v": vm, "rate": rm, "hands": hm, "e69": a, "e32": b})

    routes = sorted({r["route"] for r in rows})
    fr = np.array([r["fr"] for r in rows])
    eng = np.array([r["eng"] for r in rows])
    print(f"\n{len(rows)} windows / {len(routes)} routes;  FRIC=6000 windows {int(fr.sum())} "
          f"(engaged {int((fr*eng).sum())}), FRIC=600 {int((1-fr).sum())}")

    lr = np.log([r["rate"] for r in rows])
    lr_c = lr - lr.mean()
    lv = np.log([r["v"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    dm = np.array([r["dm"] for r in rows])
    lb = np.array([r["lb"] for r in rows])
    y69 = np.log([r["e69"] for r in rows])
    y32 = np.log([r["e32"] for r in rows])

    cols = [np.ones(len(rows)), eng, eng * fr, eng * dm, eng * lb, eng * lr_c,
            lr_c, fr, dm, lb, lv, lh]
    names = ["const", "eng", "eng x FRIC6000", "eng x damper", "eng x LeverB", "eng x lr",
             "log rate", "FRIC6000", "damper", "LeverB", "log v", "log hands"]
    for rt in routes[1:]:
        cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
        names.append(f"route[{rt}]")
    X = np.column_stack(cols)
    fit = lambda y, Xm=X: np.linalg.lstsq(Xm, y, rcond=None)[0]
    b69, b32 = fit(y69), fit(y32)

    blk, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP or r["eng"] != last["eng"]):
            cur += 1
        blk.append(cur)
        last = r
    blk = np.array(blk)
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D69, D32 = [], []
    for _ in range(3000):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D69.append(fit(y69[pick], X[pick]))
            D32.append(fit(y32[pick], X[pick]))
        except np.linalg.LinAlgError:
            pass
    D69, D32 = np.array(D69), np.array(D32)
    print(f"  {len(uq)} episode blocks\n")

    print("=" * 112)
    print("DOES 0xC40BC = 6000 REMOVE THE ENGAGEMENT-GATED 6-9 Hz AMPLIFICATION?")
    print("=" * 112)
    rep = {"n": len(rows), "routes": routes, "blocks": int(len(uq)), "terms": {}}
    for nm in ["eng", "eng x FRIC6000", "eng x damper", "eng x LeverB", "eng x lr", "log hands"]:
        i = names.index(nm)
        c69 = [np.percentile(D69[:, i], 2.5), np.percentile(D69[:, i], 97.5)]
        d = D69[:, i] - D32[:, i]
        cd = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
        obs = b69[i] - b32[i]
        excl = cd[0] > 0 or cd[1] < 0
        REF = 0.413
        tag = ("EXCLUDES 0" if excl else
               f"NULL, REFUTES {REF:+.3f}" if not (cd[0] <= -REF <= cd[1]) and nm.startswith("eng x")
               else "inconclusive")
        print(f"  {nm:16s} 6-9 {b69[i]:+7.3f} [{c69[0]:+6.3f},{c69[1]:+6.3f}]   "
              f"CONTRAST {obs:+7.3f} [{cd[0]:+6.3f},{cd[1]:+6.3f}]   {tag}")
        rep["terms"][nm] = {"b69": float(b69[i]), "contrast": float(obs),
                            "ci_contrast": cd, "verdict": tag}

    i_e, i_f = names.index("eng"), names.index("eng x FRIC6000")
    amp600 = np.exp(D69[:, i_e])
    amp6000 = np.exp(D69[:, i_e] + D69[:, i_f])
    print(f"\n  engaged/manual 6-9 Hz amplification:")
    print(f"    0xC40BC =  600 (STOCK, and the car now) : {np.median(amp600):5.2f}x "
          f"[{np.percentile(amp600,2.5):4.2f}, {np.percentile(amp600,97.5):5.2f}]")
    print(f"    0xC40BC = 6000 (V85/V86/V86B)           : {np.median(amp6000):5.2f}x "
          f"[{np.percentile(amp6000,2.5):4.2f}, {np.percentile(amp6000,97.5):5.2f}]")
    rep["amp_600"] = float(np.median(amp600))
    rep["amp_6000"] = float(np.median(amp6000))

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
