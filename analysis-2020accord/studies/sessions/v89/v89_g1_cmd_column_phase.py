#!/usr/bin/env python3
"""studies/sessions/v89/v89_g1_cmd_column_phase.py -- is `0xC40D4`'s 2-pole EMA a MODEL OF THE PLANT LAG, or smoothing?

THE QUESTION.  If the EMA models the real assist->column lag, speeding it up CREATES an error
rather than removing one, and the proposed lever inverts.  If it is arbitrary smoothing, the
Branch A / Branch B mismatch is an accident and closing it is a genuine fix.

THE TEST.  Fit the empirical cmd -> column-torque phase over 2-25 Hz on route 73 (V88) and overlay
    H_A(f) = exp(-j*2*pi*f/1000) * [ alpha / (1 - (1-alpha)*exp(-j*2*pi*f/1000)) ]**2,  alpha = 573/4096
(2 poles + one 1 kHz transport tick; reproduces the recorded -36.06 deg at 7.79 Hz and -82.84 at 21.09).

🛑 THIS IS NOT A TRANSFER-FUNCTION MEASUREMENT.  The pre-registered bar for a decision-bearing
transfer claim is gamma^2 >= 0.8 over K >= 10 non-overlapping episodes, refuse below 0.5.  Route 73
reaches nothing like that.  The output is "the phase profile IS / IS NOT consistent with H_A", with
a CI, or "cannot separate the hypotheses".

INSTRUMENT CORRECTIONS, all measured from the cache rather than assumed:
 1. fs.  Whole-route (n-1)/span = 99.7055 Hz, but that is contaminated by 440 dropouts (6.64 s).
    PER SEGMENT the grid is 100.000 Hz to 4e-5.  1/median(dt) reads 101.06 -- wrong, as warned.
 2. The 0x18F / 0x14A stagger.  `t == raw14_t[1:]` and `sstat == raw18_st[:-1]`, so a ROW pairs
    0x18F frame i with 0x14A frame i+1, while median(raw18_t - raw14_t) at equal index is 0.000 ms.
    ⇒ `tq[i]` is really sampled at raw18_t[i] but LABELLED t[i] = raw14_t[i+1] -- one frame (~10 ms)
    late = 28 deg at 7.79 Hz.  Rather than shift indices, every channel is resampled from ITS OWN
    timestamps, which removes the question and the jitter together.
 3. raw14 off-by-one: only `(raw14_t, raw14_b4)` and `(t, probe)` are used, never crossed.

CONTROLS, run before the measurement:
 C0  KNOWN-DELAY INJECTION through the whole pipeline -- must recover -2*pi*f*tau.  Also injects
     H_A itself and checks it is recovered.  Validates resampling, stagger and sign convention.
 C1  the MANUAL arm.  `gp-0x6b98` carries base assist and base assist is a function of column
     torque, so this is a CLOSED LOOP and H1 = Pxy/Pxx estimates a mixture, not the forward plant.
 C2  shuffled-pairs null for coherence and phase.
 C3  per-band coherence reported next to every phase point.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[3].parent
CACHE = ROOT / "_scratch/cache/r73"
OUT = CACHE / "v89_g1_phase.json"
RNG = np.random.default_rng(890830)

FS = 100.0
NW, HOP = 512, 256
LSB = 8.0 / 5.0                      # 427 wire -> gp-0x6b98 counts (clamp(|v|*5>>3, 0, 0x3FF))
ALPHA = 573 / 4096.0
BANDS = [(2, 4), (4, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 25)]


def H_A(f, alpha=ALPHA, fs_fw=1000.0, poles=2, tick=1):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f, float) / fs_fw)
    return (z ** tick) * (alpha / (1 - (1 - alpha) * z)) ** poles


def build_grid():
    """Resample every channel from ITS OWN timestamps onto a per-segment uniform 100 Hz grid.
    Returns a list of segment dicts, each with a `bad` mask marking dropout-bridged samples."""
    z = np.load(CACHE / "r73.npz", allow_pickle=True)
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int)
    tab = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    k = np.argsort(tab, kind="stable")
    tab, wire = tab[k], wire[k]
    t18 = np.asarray(z["raw18_t"], float)
    rt = np.asarray(z["t"], float)
    assert np.allclose(rt, t14[1:]), "raw14 pairing"
    assert np.array_equal(np.asarray(z["sstat"], int), np.asarray(z["raw18_st"], int)[:len(rt)])
    # EXACT per-row payload time (FlightV89's method, adopted by the orchestrator 2026-08-10).
    # `0x14A` is processed before the co-logged `0x18F` (measured: 91.28% of co-logged events,
    # `rlog-tools/studies/v91-v94-dose/v89_i1_can_order.py`), so a row carries the last 0x18F strictly BEFORE it.
    # A per-route shift constant is wrong -- the index relation is a mixture on every route
    # (r73 runs 0 out to -7) while the AGE is flat at 9.93 ms. searchsorted gets it per row.
    _idx = np.clip(np.searchsorted(t18, t14[1:], side="left") - 1, 0, len(t18) - 1)
    tq_t = t18[_idx][:len(rt)]
    tq_v = np.asarray(z["tq"], float)
    assert np.all(np.diff(tq_t) >= 0), "payload_time must be monotone non-decreasing"
    payload_age = rt - tq_t
    sgn_t, sgn_v = t14, np.where(((b4 >> 7) & 1) == 1, -1.0, 1.0)
    mag_t, mag_v = tab, wire * LSB
    seg = np.asarray(z["seg"], int)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    sst = np.asarray(z["sstat"], float)
    v = np.asarray(z["cs_v"], float)

    def gap_bad(src_t, g, tol):
        j = np.clip(np.searchsorted(src_t, g), 1, len(src_t) - 1)
        j = np.where(np.abs(src_t[j - 1] - g) < np.abs(src_t[j] - g), j - 1, j)
        return np.abs(src_t[j] - g) > tol

    segs = []
    for s in sorted(set(seg.tolist())):
        m = seg == s
        t0, t1 = rt[m][0], rt[m][-1]
        n = int(round((t1 - t0) * FS)) + 1
        if n < 4 * NW:
            continue
        g = t0 + np.arange(n) / FS
        sg = np.interp(g, sgn_t, sgn_v)
        sg = np.where(sg >= 0, 1.0, -1.0)
        mg = np.interp(g, mag_t, mag_v)
        cmd = sg * mg
        tq = np.interp(g, tq_t, tq_v)
        # ⊕ payload_age > 20 ms flags dropout rows directly (0.7-0.9% on every route) -- screen
        #   them rather than assume them away.
        stale = np.interp(g, rt, payload_age) > 0.020
        bad = (gap_bad(sgn_t, g, 0.015) | gap_bad(tq_t, g, 0.015) | gap_bad(mag_t, g, 0.025)
               | stale)
        segs.append({"s": s, "t": g, "cmd": cmd, "tq": tq, "bad": bad,
                     "eng": np.interp(g, rt, eng.astype(float)) > 0.5,
                     "sst": np.interp(g, rt, sst),
                     "v": np.interp(g, rt, v),
                     "wire": np.interp(g, mag_t, wire.astype(float))})
    return segs


def wins(segs, engaged, vmin=0.0):
    """(x, y, key) per admissible window. key = (segment, 20 s sub-block) for the bootstrap."""
    out = []
    w = np.hanning(NW)
    for S in segs:
        n = len(S["t"])
        for i in range(0, n - NW + 1, HOP):
            sl = slice(i, i + NW)
            if S["bad"][sl].any() or (S["sst"][sl] != 0).any():
                continue
            e = S["eng"][sl].mean()
            if engaged and e < 0.999:
                continue
            if (not engaged) and e > 0.001:
                continue
            if S["v"][sl].mean() < vmin:
                continue
            x = S["cmd"][sl]
            y = S["tq"][sl]
            if not (np.isfinite(x).all() and np.isfinite(y).all()):
                continue
            x = (x - x.mean()) * w
            y = (y - y.mean()) * w
            out.append((np.fft.rfft(x), np.fft.rfft(y), (S["s"], i // (20 * int(FS))),
                        float(S["v"][sl].mean())))
    return out


FREQ = np.fft.rfftfreq(NW, 1.0 / FS)


def accumulate(W, idx=None):
    if idx is None:
        idx = range(len(W))
    Sxy = np.zeros(len(FREQ), complex)
    Sxx = np.zeros(len(FREQ))
    Syy = np.zeros(len(FREQ))
    for i in idx:
        X, Y = W[i][0], W[i][1]
        Sxy += np.conj(X) * Y
        Sxx += np.abs(X) ** 2
        Syy += np.abs(Y) ** 2
    return Sxy, Sxx, Syy


def band_stats(Sxy, Sxx, Syy):
    out = {}
    for lo, hi in BANDS:
        m = (FREQ >= lo) & (FREQ < hi)
        cxy = Sxy[m].sum()
        coh = float(abs(cxy) ** 2 / (Sxx[m].sum() * Syy[m].sum())) if Sxx[m].sum() > 0 else np.nan
        out["{}-{}".format(lo, hi)] = {"phase": float(np.degrees(np.angle(cxy))), "coh2": coh,
                                       "f": float(FREQ[m].mean())}
    return out


def boot_bands(W, nb=1500):
    keys = sorted({w[2] for w in W})
    idx = {k: [i for i, w in enumerate(W) if w[2] == k] for k in keys}
    acc = {"{}-{}".format(a, b): [] for a, b in BANDS}
    for _ in range(nb):
        pick = np.concatenate([idx[k] for k in
                               [keys[j] for j in RNG.integers(0, len(keys), len(keys))]])
        bs = band_stats(*accumulate(W, pick))
        for k in acc:
            acc[k].append(bs[k]["phase"])
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in acc.items()}


def main():
    rep = {}
    segs = build_grid()
    print("=" * 104)
    print("GRID -- per-segment uniform 100.000 Hz, every channel from its OWN timestamps")
    print("=" * 104)
    tot = sum(len(S["t"]) for S in segs)
    badf = sum(S["bad"].sum() for S in segs)
    print("  {} segments, {} samples, {:.1f} s;  dropout-bridged samples {} ({:.2%})".format(
        len(segs), tot, tot / FS, badf, badf / tot))

    # ---------------- C0: known-delay injection ----------------
    print("\n" + "=" * 104)
    print("C0 -- PIPELINE VALIDATION. Inject a KNOWN delay and a KNOWN H_A, recover them.")
    print("=" * 104)
    base = [dict(S) for S in segs]
    for tau_ms in (0.0, 10.0, 30.0):
        for S, B in zip(segs, base):
            d = int(round(tau_ms / 1000.0 * FS))
            y = np.roll(B["cmd"], d)
            y[:d] = B["cmd"][0]
            S["tq"] = y + 0.02 * np.std(B["cmd"]) * RNG.standard_normal(len(y))
        W = wins(segs, True)
        bs = band_stats(*accumulate(W))
        errs = []
        for (lo, hi) in BANDS:
            k = "{}-{}".format(lo, hi)
            want = -360.0 * bs[k]["f"] * tau_ms / 1000.0
            errs.append(bs[k]["phase"] - want)
        print("  delay {:5.1f} ms: recovered-minus-true phase, max |err| {:.2f} deg  "
              "(coh2 {:.3f}-{:.3f})  {}".format(
                  tau_ms, max(abs(e) for e in errs),
                  min(bs[k]["coh2"] for k in bs), max(bs[k]["coh2"] for k in bs),
                  "PASS" if max(abs(e) for e in errs) < 2.0 else "FAIL"))
    # inject H_A itself
    for S, B in zip(segs, base):
        X = np.fft.rfft(B["cmd"])
        f = np.fft.rfftfreq(len(B["cmd"]), 1.0 / FS)
        S["tq"] = np.fft.irfft(X * H_A(f), len(B["cmd"]))
    W = wins(segs, True)
    bs = band_stats(*accumulate(W))
    e = [bs["{}-{}".format(a, b)]["phase"] - np.degrees(np.angle(H_A(bs["{}-{}".format(a, b)]["f"])))
         for a, b in BANDS]
    print("  H_A injected : recovered-minus-H_A, max |err| {:.2f} deg   {}".format(
        max(abs(x) for x in e), "PASS" if max(abs(x) for x in e) < 2.0 else "FAIL"))
    print("  ** The pipeline recovers a known lag to <2 deg across 2-25 Hz. Sign convention:")
    print("     negative phase = column LAGS command. **")
    for S, B in zip(segs, base):
        S["tq"] = B["tq"]

    # ---------------- the measurement ----------------
    Weng = wins(segs, True)
    Wman = wins(segs, False)
    print("\n" + "=" * 104)
    print("EXPOSURE -- {} engaged windows / {} sub-blocks, {} manual / {} sub-blocks".format(
        len(Weng), len({w[2] for w in Weng}), len(Wman), len({w[2] for w in Wman})))
    print("  NW={} ({:.2f} s), hop {}, Hann, df={:.3f} Hz".format(
        NW, NW / FS, HOP, FREQ[1]))
    print("=" * 104)

    # C2 shuffled-pairs null, run before quoting anything
    print("\nC2 -- SHUFFLED-PAIRS NULL (x from one window, y from another sub-block)")
    keys = sorted({w[2] for w in Weng})
    nullc = {("{}-{}".format(a, b)): [] for a, b in BANDS}
    for _ in range(300):
        perm = RNG.permutation(len(Weng))
        Wsh = [(Weng[i][0], Weng[perm[i]][1], Weng[i][2], 0) for i in range(len(Weng))]
        bs = band_stats(*accumulate(Wsh))
        for k in nullc:
            nullc[k].append(bs[k]["coh2"])
    for k in nullc:
        print("   {:8s} shuffled coh2 p95 = {:.4f}".format(k, np.percentile(nullc[k], 95)))

    rep["bands"] = {}
    for lab, W in (("ENGAGED", Weng), ("MANUAL (C1 control)", Wman)):
        if len(W) < 12:
            print("\n  {}: only {} windows -- UNINTERPRETABLE".format(lab, len(W)))
            continue
        bs = band_stats(*accumulate(W))
        cis = boot_bands(W)
        print("\n  {}   n={} windows / {} sub-blocks".format(
            lab, len(W), len({w[2] for w in W})))
        print("   {:8s} {:>7s} {:>9s} {:>19s} {:>9s} {:>9s} {:>8s}".format(
            "band", "f Hz", "coh2", "phase [95% CI]", "H_A", "diff", "null p95"))
        rows = {}
        for a, b in BANDS:
            k = "{}-{}".format(a, b)
            f = bs[k]["f"]
            ha = float(np.degrees(np.angle(H_A(f))))
            lo, hi = cis[k]
            d = bs[k]["phase"] - ha
            flag = "" if bs[k]["coh2"] >= 0.5 else "  (coh<0.5: REFUSE)"
            print("   {:8s} {:7.2f} {:9.4f}  {:+7.1f} [{:+6.1f},{:+6.1f}] {:+9.1f} {:+9.1f} "
                  "{:8.4f}{}".format(k, f, bs[k]["coh2"], bs[k]["phase"], lo, hi, ha, d,
                                     np.percentile(nullc[k], 95), flag))
            rows[k] = {"f": f, "coh2": bs[k]["coh2"], "phase": bs[k]["phase"],
                       "ci": [lo, hi], "H_A": ha, "diff": d,
                       "null_coh_p95": float(np.percentile(nullc[k], 95))}
        rep["bands"][lab] = rows

    # ---------------- the naive pairing, to size correction 2 ----------------
    print("\n" + "=" * 104)
    print("SIZE OF THE STAGGER CORRECTION -- redo ENGAGED with the NAIVE row-index pairing")
    print("=" * 104)
    z = np.load(CACHE / "r73.npz", allow_pickle=True)
    rt = np.asarray(z["t"], float)
    for S in segs:
        S["tq"] = np.interp(S["t"], rt, np.asarray(z["tq"], float))
    bsn = band_stats(*accumulate(wins(segs, True)))
    for a, b in BANDS:
        k = "{}-{}".format(a, b)
        print("   {:8s} corrected {:+7.1f}   naive {:+7.1f}   shift {:+6.1f} deg".format(
            k, rep["bands"]["ENGAGED"][k]["phase"], bsn[k]["phase"],
            bsn[k]["phase"] - rep["bands"]["ENGAGED"][k]["phase"]))

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
