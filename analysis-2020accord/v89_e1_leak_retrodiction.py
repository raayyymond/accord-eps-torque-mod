#!/usr/bin/env python3
"""v89_e1_leak_retrodiction.py -- retrodict the OBSERVER-LEAK hypothesis on already-flown data.

HYPOTHESIS (orchestrator, 2026-08-10). `FUN_0003b8f6`'s command branch is an EMA with
alpha_a = 0xC40D4/4096; `FUN_00038148`'s path-2 is an IIR1 with alpha_b = 0xC63AC/1024 = 102/1024.
The residual is their DIFFERENCE, so a fraction |H_cmd(f) - H_path2(f)| of the EPS's own command
leaks into the "disturbance" and is chased.  Lowering alpha_a (V86: 573 -> 286) RAISES the leak,
band-specifically and MONOTONICALLY DECREASING with frequency.

  predicted log-ratio of leak, 286 vs 573:  6-9 +0.879 | 18-22 +0.508 | 26-31 +0.329 | 32-38 +0.225
  => predicted BAND CONTRAST vs the 32-38 control: 6-9 +0.654 | 18-22 +0.283 | 26-31 +0.104
  These are UPPER BOUNDS: observed column energy moves only by the leak-driven FRACTION of it.

DESIGN.  alpha=286 exists on exactly ONE route (`6f`/V86).  alpha=573 on all 29 others.
Byte-verified from the images this session:
  V85 -> V86  = 68 B: 0xC40D4 573->286 (2 B control) + 62 B telemetry cave + 4 B CRC. SINGLE-VARIABLE.
  V85 -> V86B = 74 B: FactorC m26/m27 Y[0] (4 B control) + cave + 2 CRC blocks. alpha STAYS 573.
So {6e, 70} are alpha=573 and {6f} is alpha=286; 70 additionally arms the FactorC creep damper.

CONTROLS RUN BEFORE THE MEASUREMENT (kit rule):
  C1 within-route split-half null -> the resolution floor
  C2 6e-vs-70, a REAL build pair at CONSTANT alpha -> the build-to-build floor
  C3 the 32-38 Hz band contrast (note: the model itself predicts +0.225 there, so this
     control is NOT clean -- it BIASES THE CONTRAST DOWNWARD, i.e. conservative)
  C4 manual (LKAS-off) arm: alpha is not gated on engagement, so the leak must appear there too
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "_cache_r73" / "v89_c1_corpus.npy"
OUT = ROOT / "_cache_r73" / "v89_e1_leak.json"
RNG = np.random.default_rng(890810)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088
BANDS = {"6-9": (6.0, 9.0), "18-22": (18.0, 22.0), "26-31": (26.0, 31.0), "32-38": (32.0, 38.0)}
CTRL = "32-38"
PRED = {"6-9": 0.879, "18-22": 0.508, "26-31": 0.329, "32-38": 0.225}
ALPHA = {"r6e": 573, "r6f": 286, "r70": 573}
DAMPER_FC = {"r6e": 0, "r6f": 0, "r70": 1}      # FactorC m26/m27 Y[0] armed
VMAX_MATCH = 5.20                                # common speed support of 6f (5.38) / 70 (5.97)


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


def harvest(vmax, nmax_order=6):
    rows = []
    for rec in np.load(CORPUS, allow_pickle=True):
        rt = rec["route"]
        if rt not in ALPHA:
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
            if not (0.3 < vm < vmax) or rm < 1.0 or hm < 1.0:
                continue
            if any(order_hits(vm, lo, hi, nmax_order) for lo, hi in BANDS.values()):
                continue
            f, p = spec(tq[sl], fs)
            b = {k: brms(f, p, lo, hi) for k, (lo, hi) in BANDS.items()}
            if min(b.values()) <= 0:
                continue
            rows.append({"route": rt, "a286": 1.0 if ALPHA[rt] == 286 else 0.0,
                         "fc": float(DAMPER_FC[rt]), "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                         **{"e_" + k: b[k] for k in BANDS}})
    return rows


def blocks_of(rows):
    blk, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP or r["eng"] != last["eng"]):
            cur += 1
        blk.append(cur)
        last = r
    return np.array(blk)


def design(rows, extra_flag=None):
    n = len(rows)
    lv = np.log([r["v"] for r in rows])
    lr = np.log([r["rate"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    cols = [np.ones(n), np.array([r["a286"] for r in rows]),
            lv - lv.mean(), lr - lr.mean(), lh - lh.mean()]
    names = ["const", "A286", "log v", "log rate", "log hands"]
    if extra_flag is not None:
        cols.append(np.array([r[extra_flag] for r in rows]))
        names.append(extra_flag)
    return np.column_stack(cols), names


def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def boot(X, ys, blk, nb=3000):
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    out = {k: [] for k in ys}
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            d = {k: fit(X[pick], ys[k][pick]) for k in ys}
        except np.linalg.LinAlgError:
            continue
        for k in ys:
            out[k].append(d[k])
    return {k: np.array(v) for k, v in out.items()}


def ci(a, lo=2.5, hi=97.5):
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


def main():
    rep = {"pred_contrast": {k: PRED[k] - PRED[CTRL] for k in BANDS}}
    print("=" * 104)
    print("EXPOSURE CENSUS -- raw frames, before any window screen")
    print("=" * 104)
    cens = {}
    for rec in np.load(CORPUS, allow_pickle=True):
        rt = rec["route"]
        if rt not in ALPHA:
            continue
        c = cens.setdefault(rt, {"n": 0, "eng": 0, "vmax": 0.0, "eng_lo": 0, "eng_hi": 0})
        v = rec["v"]
        e = rec["eng"]
        c["n"] += len(v)
        c["eng"] += int(e.sum())
        c["vmax"] = max(c["vmax"], float(np.nanmax(v)))
        c["eng_lo"] += int((e & (v < VMAX_MATCH)).sum())
        c["eng_hi"] += int((e & (v >= VMAX_MATCH)).sum())
    for rt in sorted(cens):
        c = cens[rt]
        print("  {}  alpha={:4d} FactorC={}  {:6d} fr  eng {:6d}  v_max {:5.2f} m/s  "
              "eng<{} m/s {:6d} ({:4.1f} min)  eng>= {:6d} ({:4.1f} min)".format(
                  rt, ALPHA[rt], DAMPER_FC[rt], c["n"], c["eng"], c["vmax"], VMAX_MATCH,
                  c["eng_lo"], c["eng_lo"] / 6000, c["eng_hi"], c["eng_hi"] / 6000))
    rep["census"] = cens
    print("\n  ** 6e reaches {:.2f} m/s; 6f/70 are parking-lot. The MATCHED analysis is capped "
          "at v < {} m/s. **".format(cens["r6e"]["vmax"], VMAX_MATCH))

    rows = harvest(VMAX_MATCH)
    blk = blocks_of(rows)
    print("\nWINDOWS (v<{}, wheel-order veto orders 1-6 on ALL four bands, sstat==0, "
          "|rate|>1 deg/s, hands>1)".format(VMAX_MATCH))
    for rt in sorted(ALPHA):
        ii = [i for i, r in enumerate(rows) if r["route"] == rt]
        sub = [rows[i] for i in ii]
        print("  {}: {:5d} windows  (engaged {:.0f}, manual {:.0f})  blocks {}".format(
            rt, len(sub), sum(r["eng"] for r in sub), sum(1 - r["eng"] for r in sub),
            len(set(blk[ii])) if ii else 0))
    print("  TOTAL {} windows / {} episode blocks".format(len(rows), len(np.unique(blk))))
    rep["n_windows"] = len(rows)
    rep["n_blocks"] = int(len(np.unique(blk)))

    eng_rows = [r for r in rows if r["eng"] == 1.0]
    man_rows = [r for r in rows if r["eng"] == 0.0]

    # ---------------- C1: split-half null, within route, engaged ----------------
    print("\n" + "=" * 104)
    print("CONTROL C1 -- WITHIN-ROUTE SPLIT-HALF NULL (the resolution floor). Engaged windows.")
    print("=" * 104)
    rep["C1"] = {}
    for rt in sorted(ALPHA):
        idxs = [i for i, r in enumerate(rows) if r["route"] == rt and r["eng"] == 1.0]
        if len(idxs) < 20:
            print("  {}: too few engaged windows ({})".format(rt, len(idxs)))
            continue
        b = blk[idxs]
        uq = np.unique(b)
        y = {k: np.log([rows[i]["e_" + k] for i in idxs]) for k in BANDS}
        ds = {k: [] for k in BANDS}
        dcon = []
        for _ in range(2000):
            p = RNG.permutation(uq)
            h1 = set(p[: len(p) // 2])
            m1 = np.array([g in h1 for g in b])
            if m1.sum() < 5 or (~m1).sum() < 5:
                continue
            dd = {k: y[k][m1].mean() - y[k][~m1].mean() for k in BANDS}
            for k in BANDS:
                ds[k].append(dd[k])
            dcon.append(dd["6-9"] - dd[CTRL])
        for k in BANDS:
            lo, hi = ci(np.array(ds[k]))
            print("  {} {:6s} split-half log-diff  [{:+6.3f}, {:+6.3f}]  = ratio "
                  "[{:5.2f}, {:5.2f}]".format(rt, k, lo, hi, np.exp(lo), np.exp(hi)))
        lo, hi = ci(np.array(dcon))
        print("  {} 6-9 minus {} CONTRAST null  [{:+6.3f}, {:+6.3f}]   halfwidth {:.3f}   "
              "({} blocks)".format(rt, CTRL, lo, hi, (hi - lo) / 2, len(uq)))
        rep["C1"][rt] = {"contrast_null_ci": [lo, hi], "uq_blocks": int(len(uq))}

    # ---------------- C2: 6e vs 70, CONSTANT alpha ----------------
    print("\n" + "=" * 104)
    print("CONTROL C2 -- 6e vs 70: a REAL cross-build pair at CONSTANT alpha=573.")
    print("             (they differ by the FactorC creep damper, not by 0xC40D4)")
    print("=" * 104)
    sub = [r for r in eng_rows if r["route"] in ("r6e", "r70")]
    sb = blocks_of(sub)
    if len(sub) > 30:
        n = len(sub)
        lv = np.log([r["v"] for r in sub])
        lr = np.log([r["rate"] for r in sub])
        lh = np.log([r["hands"] for r in sub])
        X = np.column_stack([np.ones(n),
                             np.array([1.0 if r["route"] == "r70" else 0.0 for r in sub]),
                             lv - lv.mean(), lr - lr.mean(), lh - lh.mean()])
        ys = {k: np.log([r["e_" + k] for r in sub]) for k in BANDS}
        B = boot(X, ys, sb)
        obs = {k: fit(X, ys[k])[1] for k in BANDS}
        lo, hi = ci(B["6-9"][:, 1] - B[CTRL][:, 1])
        print("  n={} windows / {} blocks".format(n, len(np.unique(sb))))
        for k in BANDS:
            l, h = ci(B[k][:, 1])
            print("    r70-vs-r6e {:6s} {:+7.3f} [{:+6.3f},{:+6.3f}]".format(k, obs[k], l, h))
        print("    BAND CONTRAST 6-9 minus {}: {:+7.3f} [{:+6.3f},{:+6.3f}]   "
              "<-- BUILD-TO-BUILD FLOOR AT CONSTANT ALPHA".format(
                  CTRL, obs["6-9"] - obs[CTRL], lo, hi))
        rep["C2"] = {"contrast": float(obs["6-9"] - obs[CTRL]), "ci": [lo, hi],
                     "n": n, "blocks": int(len(np.unique(sb)))}

    # ---------------- MAIN: alpha=286 vs alpha=573 ----------------
    for label, rws in (("ENGAGED", eng_rows), ("MANUAL", man_rows)):
        print("\n" + "=" * 104)
        print("MEASUREMENT -- alpha=286 (6f) vs alpha=573 (6e + 70)   [{}]".format(label))
        print("=" * 104)
        if len(rws) < 40:
            print("  only {} windows -- SKIPPED".format(len(rws)))
            continue
        b = blocks_of(rws)
        X, names = design(rws, extra_flag="fc")
        ys = {k: np.log([r["e_" + k] for r in rws]) for k in BANDS}
        B = boot(X, ys, b)
        i = names.index("A286")
        obs = {k: fit(X, ys[k])[i] for k in BANDS}
        print("  n={} windows / {} blocks; alpha286 windows {}".format(
            len(rws), len(np.unique(b)), int(sum(r["a286"] for r in rws))))
        res = {}
        for k in BANDS:
            l, h = ci(B[k][:, i])
            print("    {:6s} A286 {:+7.3f} [{:+6.3f},{:+6.3f}]  = {:5.2f}x   "
                  "(model predicts {:+.3f} = {:.2f}x, an UPPER bound)".format(
                      k, obs[k], l, h, np.exp(obs[k]), PRED[k], np.exp(PRED[k])))
            res[k] = {"b": float(obs[k]), "ci": [l, h]}
        print()
        for k in ("6-9", "18-22", "26-31"):
            d = B[k][:, i] - B[CTRL][:, i]
            lo, hi = ci(d)
            o = obs[k] - obs[CTRL]
            pc = PRED[k] - PRED[CTRL]
            verd = "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"
            resolves = ("resolves the prediction" if (hi - lo) / 2 < abs(pc)
                        else "CANNOT RESOLVE the prediction")
            excl_pred = "and EXCLUDES it" if not (lo <= pc <= hi) else "and INCLUDES it"
            print("    CONTRAST {:6s} minus {}: {:+7.3f} [{:+6.3f},{:+6.3f}]  predicted {:+.3f}   "
                  "{}; {} {}".format(k, CTRL, o, lo, hi, pc, verd, resolves, excl_pred))
            res["contrast_" + k] = {"obs": float(o), "ci": [lo, hi], "pred": pc,
                                    "verdict": verd, "power": resolves,
                                    "excludes_pred": not (lo <= pc <= hi)}
        rep[label] = res

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
