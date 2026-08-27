#!/usr/bin/env python3
"""studies/sessions/v89/v89_a6_leverb_discriminator.py -- does the engagement x rate interaction depend on LEVER B?

v89_a5 established [EVIDENCE]: engagement's amplification of the 6-9 Hz column mode GROWS with
wheel rate, band-specifically (`eng x log|rate|` at 6-9 Hz = +0.313 [+0.103, +0.490]; its band contrast vs the 32-38 Hz
control is +0.144 [-0.004, +0.267] -- SUGGESTIVE, not clear of its control).

That is a structural filter on candidate levers: the culprit must be BOTH engagement-gated AND
rate-driven. Exactly one thing in this firmware is known to be both -- **Lever B**, which repoints
r24's gain gate to `gp-0x6806` ("LKAS applying") and swaps the gain 2622 -> 5244 while it holds.
r24 is a 4-sample backward difference of column torque, i.e. a rate derivative.

  H_A  Lever B DRIVES the interaction  -> the interaction is LARGER on Lever-B routes.
                                          => V89 lowers r24's engaged arm. Every build has raised it.
  H_0  Lever B is irrelevant            -> the interaction is flat across the two groups.
                                          => r24 is exonerated and the mode is not command-side.

Both build flags are BYTE-DERIVED from each build's own plain image, never quoted:
    Lever B  :  0x3AA96 == 0xFB  AND  0xC6446 == 5244
    damper   :  FactorC mode-26 Y[0] != 0   (V74..V86B armed it; V87/V88 are Honda-stock)

The damper flag is carried as a covariate because the two partially co-occur across the corpus,
and a 6-9 Hz claim must not be allowed to ride on the damper state by accident.

ROUTE -> BUILD is DOCUMENTATION-DERIVED (BUILD-LINEAGE.md + each cache's `probe_build`, which
agree on all 12). 🛑 An rlog cannot identify its build from the version string -- every build
reports `fw='39990-TVA,A160'`. This is the weakest link in the analysis and is labelled as such.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3].parent
FWD = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
OUT = ROOT / "_scratch/cache/r73" / "v89_a6_leverb.json"
RNG = np.random.default_rng(890606)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088
FACTOR_C_PTRS = 0xC9E9C

# route -> build. Documentation-derived; each cache's own `probe_build` agrees on all 12.
# 🛑 r66 is present in BOTH _scratch/cache/r66 and _scratch/cache/r66x -- the same route. Loaded ONCE.
ROUTE_BUILD = {"r5e": "v75", "r61": "v74", "r65": "v76", "r66": "v80", "r67": "v81",
               "r68": "v83a", "r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b",
               "r71": "v87", "r73": "v88"}


def build_flags(tag):
    hits = sorted(FWD.glob(f"_{tag}_*_plain_image.bin"))
    if not hits:
        return None
    b = hits[0].read_bytes()
    lever_b = (b[0x3AA96] == 0xFB and struct.unpack_from("<H", b, 0xC6446)[0] == 5244)
    rec = struct.unpack_from("<I", b, FACTOR_C_PTRS + 26 * 4)[0]
    n = struct.unpack_from("<H", b, rec)[0]
    y0 = struct.unpack_from(f"<{n}h", b, rec + 2 + 2 * n)[0]
    return {"lever_b": bool(lever_b), "damper_y0": int(y0), "damper": bool(y0 != 0),
            "img": hits[0].name}


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


def load(route, path):
    z = np.load(path, allow_pickle=True)
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    tq, rate = np.asarray(z["tq"], float), np.asarray(z["rate_c"], float)
    v, eng = np.asarray(z["cs_v"], float), np.asarray(z["cc_lat"], float) > 0.5
    sst, seg = np.asarray(z["sstat"], float), np.asarray(z["seg"], int)
    sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
    g = np.isfinite(tq)
    lf = np.zeros_like(tq)
    if g.sum() > 30:
        lf[g] = sosfiltfilt(sos, tq[g])
    rows = []
    for s in range(0, len(t) - NW + 1, HOP):
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
        rows.append({"route": route, "seg": int(np.median(seg[sl])), "i0": s,
                     "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                     "e69": a, "e32": b})
    return rows


def blocks(rows):
    out, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP or r["eng"] != last["eng"]):
            cur += 1
        out.append(cur)
        last = r
    return np.array(out)


def main():
    flags = {}
    print("BUILD FLAGS, byte-derived from each build's own image")
    for rt, tag in ROUTE_BUILD.items():
        fl = build_flags(tag)
        flags[rt] = fl
        if fl is None:
            print(f"  {rt:5s} {tag:5s}  -- NO IMAGE, route dropped")
            continue
        print(f"  {rt:5s} {tag:5s}  LeverB={'YES' if fl['lever_b'] else ' no'}  "
              f"damper Y[0]={fl['damper_y0']:4d} ({'armed' if fl['damper'] else 'Honda'})")

    rows = []
    for rt in ROUTE_BUILD:
        if flags.get(rt) is None:
            continue
        cand = [p for p in ROOT.glob(f"_cache_{rt}*/{rt}.npz")]
        if not cand:
            print(f"  !! no cache for {rt}")
            continue
        rows += load(rt, sorted(cand)[0])          # ONE cache per route -- r66 is duplicated
    routes = sorted({r["route"] for r in rows})
    print(f"\n{len(rows)} windows over {len(routes)} routes: {routes}")

    lb = np.array([1.0 if flags[r["route"]]["lever_b"] else 0.0 for r in rows])
    dm = np.array([1.0 if flags[r["route"]]["damper"] else 0.0 for r in rows])
    eng = np.array([r["eng"] for r in rows])
    lr = np.log([r["rate"] for r in rows])
    lr_c = lr - lr.mean()
    lv = np.log([r["v"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    y69 = np.log([r["e69"] for r in rows])
    y32 = np.log([r["e32"] for r in rows])

    print(f"  Lever-B windows {int(lb.sum())} / non {int((1-lb).sum())}   "
          f"damper-armed {int(dm.sum())} / Honda {int((1-dm).sum())}   "
          f"corr(leverB, damper) = {np.corrcoef(lb, dm)[0,1]:+.3f}")

    # eng x log rate x LeverB, with the damper carried as its own interaction
    cols = [np.ones(len(rows)), eng, eng * lr_c, eng * lr_c * lb, eng * lb,
            eng * lr_c * dm, eng * dm, lr_c, lb, dm, lv, lh]
    names = ["const", "eng", "eng x lr", "eng x lr x LEVERB", "eng x LeverB",
             "eng x lr x damper", "eng x damper", "log rate", "LeverB", "damper",
             "log v", "log hands"]
    for rt in routes[1:]:
        cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
        names.append(f"route[{rt}]")
    X = np.column_stack(cols)
    fit = lambda y, Xm=X: np.linalg.lstsq(Xm, y, rcond=None)[0]
    b69, b32 = fit(y69), fit(y32)

    blk = blocks(rows)
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

    print(f"\n  {len(uq)} episode blocks\n")
    print("=" * 92)
    print("THE DISCRIMINATOR")
    print("=" * 92)
    print(f"  {'term':22s} {'6-9 Hz':>26s} {'32-38 Hz control':>26s}")
    rep = {"flags": {k: v for k, v in flags.items() if v}, "n": len(rows),
           "routes": routes, "blocks": int(len(uq)), "terms": {}}
    for i, nm in enumerate(names[:7]):
        c69 = [np.percentile(D69[:, i], 2.5), np.percentile(D69[:, i], 97.5)]
        c32 = [np.percentile(D32[:, i], 2.5), np.percentile(D32[:, i], 97.5)]
        star = " <<<" if "LEVERB" in nm else ""
        print(f"  {nm:22s} {b69[i]:+7.3f} [{c69[0]:+7.3f},{c69[1]:+7.3f}] "
              f"{b32[i]:+7.3f} [{c32[0]:+7.3f},{c32[1]:+7.3f}]{star}")
        rep["terms"][nm] = {"b69": float(b69[i]), "ci69": [float(x) for x in c69],
                            "b32": float(b32[i]), "ci32": [float(x) for x in c32]}

    k = names.index("eng x lr x LEVERB")
    d = D69[:, k] - D32[:, k]
    ci = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    print(f"\n  BAND CONTRAST on the Lever-B interaction: {b69[k]-b32[k]:+.3f} "
          f"[{ci[0]:+.3f}, {ci[1]:+.3f}]")
    # 🛑 POWER FIRST. A CI that is wider than the effect it is testing cannot exonerate anything.
    # v89_a5's main interaction contrast is +0.144 (DEDUPED); if this CI cannot exclude it,
    # NULL RESULT ON AN UNDERPOWERED TEST, not evidence of absence. Same trap as
    # feedback-a-falsifier-only-fires-if-it-could-have-fired.
    MAIN = 0.144
    halfwidth = (ci[1] - ci[0]) / 2.0
    powered = halfwidth < MAIN
    if ci[0] > 0:
        verdict = "H_A -- Lever B AMPLIFIES the rate interaction => V89 LOWERS r24's engaged arm"
    elif ci[1] < 0:
        verdict = "H_A INVERTED -- Lever B SUPPRESSES it => do NOT lower r24's engaged arm"
    elif powered:
        verdict = "H_0 -- Lever B does not modulate the interaction => r24 EXONERATED"
    else:
        verdict = ("INCONCLUSIVE -- UNDERPOWERED. The CI half-width "
                   f"({halfwidth:+.3f}) EXCEEDS the main effect being tested ({MAIN:+.3f}), so "
                   "this cannot distinguish 'no modulation' from 'modulation as large as the "
                   "whole effect'. 🛑 r24 is NOT exonerated.")
    print(f"  => {verdict}")
    print(f"     power: CI half-width {halfwidth:+.3f} vs main effect {MAIN:+.3f} -> "
          f"{'ADEQUATE' if powered else 'INADEQUATE'}")
    rep["contrast_leverb"] = {"d": float(b69[k] - b32[k]), "ci": ci, "verdict": verdict}

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
