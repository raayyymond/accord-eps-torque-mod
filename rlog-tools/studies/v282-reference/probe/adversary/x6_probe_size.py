# -*- coding: utf-8 -*-
"""X6 -- THE PROBE'S HONEST SIZE, against the coherence that actually binds; and the readout floor.

X3 sized the probe against coh(Z,U).  That was too kind: the plant estimate is P = S_zm/S_zu, so its
variance is limited by the WORSE of coh(Z,U) and coh(Z,M), and coh(Z,M) is far lower.  Re-size against
it, and convert to what the operator would feel: peak commanded steering RATE at the band centre,
against the steering-rate content that band already carries.

Then the other half of the decision: the goal metric's own READ-BACK NOISE.  A probe that perfects
identification does nothing about whether one drive can score the result.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
BANDS = [("0.60-1.20", 0.60, 1.20), ("1.20-2.40", 1.20, 2.40), ("2.40-3.40", 2.40, 3.40),
         ("3.40-4.90", 3.40, 4.90)]
RTS = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
CT = 0.7
_W = float(np.sum(np.hanning(1024) ** 2))


def brms(X, s):
    return float(np.sqrt(2.0 * np.mean(np.sum(np.abs(X[:, s]) ** 2, axis=1)) / (1024 * _W)))


def main():
    print("=" * 126)
    print("1. THE PROBE SIZED AGAINST THE COHERENCE THAT BINDS THE PLANT ESTIMATE, coh(Z,M).")
    print("   Szz/Srr = (c*-c0)/((1-c*)c0), c* = 0.70.  SR pk is the peak steering RATE the probe")
    print("   alone commands at the band centre; 'today' is the route's own in-band steering-rate RMS.")
    for rt in RTS:
        L = A.load(rt)
        f, F, vm, am = A.spectra(L)
        idx = np.where(vm >= 15.0)[0]
        R, M, U = F["r"][idx], F["y"][idx], F["u"][idx]
        cf = lambda Aa, Bb: (np.abs(np.mean(np.conj(Aa) * Bb, axis=0)) ** 2 /
                             np.maximum(np.mean(np.abs(Aa) ** 2, axis=0) *
                                        np.mean(np.abs(Bb) ** 2, axis=0), 1e-300))
        czm, czu = cf(R, M), cf(R, U)
        m = L["act"] & np.isfinite(L["y"]) & np.isfinite(L["sa"]) & (L["v"] >= 15.0)
        k_sa = abs(float(np.polyfit(L["y"][m], L["sa"][m], 1)[0]))
        print(f"\n   --- {rt}   n {len(idx)}   d(angle)/d(lataccel) {k_sa:.2f} deg per m/s^2")
        print(f"   {'band':11s} {'coh(Z,M)':>9s} {'coh(Z,U)':>9s} {'Szz/Srr':>9s} {'ref rms':>9s} "
              f"{'probe rms':>10s} {'probe pk':>9s} {'SR pk deg/s':>12s} {'today SR rms':>13s} "
              f"{'x today':>8s}")
        for nm, lo, hi in BANDS:
            s = (f >= lo) & (f <= hi)
            c0 = float(np.mean(czm[s]))
            cu = float(np.mean(czu[s]))
            need = (CT - c0) / ((1 - CT) * max(c0, 1e-6))
            ref = brms(R, s)
            pr = ref * np.sqrt(max(need, 0.0))
            fc = 0.5 * (lo + hi)
            srpk = 2 * np.pi * fc * pr * np.sqrt(2) * k_sa
            srn = brms(F["sr"][idx], s)
            print(f"   {nm:11s} {c0:9.3f} {cu:9.3f} {need:9.1f} {ref:9.5f} {pr:10.5f} "
                  f"{pr*np.sqrt(2):9.5f} {srpk:12.2f} {srn:13.3f} {srpk/max(srn,1e-9):7.1f}x")
        del L, F
    print()
    print("   'x today' is the peak steering rate the probe commands divided by the RMS steering rate")
    print("   the band already carries.  The 1.8-3.5 Hz steering-rate RMS is the operator's own shake")
    print("   complaint, and rev 6.4 already runs x2.6-3.1 of V282 there.")

    print()
    print("=" * 126)
    print("2. THE READ-BACK FLOOR.  Per-RUN metric and a run-cluster bootstrap -- what one drive can")
    print("   actually resolve, independent of how well the loop is identified.")
    import v282cmp as V
    band = None
    runs = {}
    for rt in RTS + ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]:
        S = V.load(rt)
        m = (S["active"] & ~S["pressed"] & (S["v"] >= 15.0) & np.isfinite(S["setpoint"])
             & np.isfinite(S["la_pose"]) & np.isfinite(S["model"]) & np.isfinite(S["out"]))
        w = signal.get_window("hann", 1024)
        f = np.fft.rfftfreq(1024, A.DT)
        band = (f >= 0.15) & (f <= 2.4)
        for a, b in V.runs(m, S["t"], min_s=30.0):
            pe = px = 0.0
            nw = 0
            for s in range(a, b - 1024 + 1, 512):
                e = s + 1024
                if float(np.mean(S["sat"][s:e])) > 0.02:
                    continue
                X = np.fft.rfft(signal.detrend(np.nan_to_num(S["model"])[s:e]) * w)
                Y = np.fft.rfft(signal.detrend(np.nan_to_num(S["la_pose"])[s:e]) * w)
                pe += float(np.sum(np.abs((X - Y)[band]) ** 2))
                px += float(np.sum(np.abs(X[band]) ** 2))
                nw += 1
            if nw:
                runs.setdefault(rt, []).append((pe, px, nw))
        del S
    rng = np.random.default_rng(7)
    print(f"   {'route':24s} {'runs':>5s} {'J pooled':>9s}   per-run J")
    for rt, rr in runs.items():
        Jp = sum(r[0] for r in rr) / sum(r[1] for r in rr)
        print(f"   {rt:24s} {len(rr):5d} {Jp:9.3f}   " +
              " ".join(f"{r[0]/r[1]:.2f}" for r in rr))
    t64 = runs[RTS[0]] + runs[RTS[1]]
    bs = []
    for _ in range(4000):
        pick = [t64[i] for i in rng.integers(0, len(t64), len(t64))]
        bs.append(sum(p[0] for p in pick) / sum(p[1] for p in pick))
    bs = np.array(bs)
    print(f"\n   rev 6.4 pooled J {sum(p[0] for p in t64)/sum(p[1] for p in t64):.4f}   "
          f"run-cluster 95% CI [{np.percentile(bs,2.5):.3f}, {np.percentile(bs,97.5):.3f}]")
    for nm, tgt in (("ARM-KP3 (15.9%)", 1.2064), ("TIER B KP8 (49%)", 0.920),
                    ("TIER B KP12 (69%)", 0.740), ("TIER B KP16 (80%)", 0.650)):
        p = float(np.mean(bs <= tgt))
        print(f"      P(a 2-run drive with NOTHING CHANGED reads J <= {tgt:.3f}) = {p*100:5.1f}%"
              f"   <- {nm}")
    json.dump(dict(ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]),
              open(OUT / "x6.json", "w"), indent=1)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0, str(HERE.parents[1]))
    main()
