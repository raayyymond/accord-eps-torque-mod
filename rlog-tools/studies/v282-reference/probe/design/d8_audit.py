# -*- coding: utf-8 -*-
"""d8 -- three audits that decide whether the d7 numbers may be quoted.

A. PARSEVAL.  d7 converted a summed |rfft|^2 to a time-domain band RMS with sqrt(sum)/256*sqrt(2).
   That is WRONG for a Hann window.  Verified numerically here against a synthetic signal of known
   band RMS, and the correct factor is used to re-state the wheel-rate cost.

B. COST TRANSFER.  d7 priced wheel rate as A*|P*S|/|T_zm| * |T_zsr|, a product of three transfers,
   two of which sit at coherence 0.01-0.16 in the margin band.  The direct command -> steering-rate
   transfer |S_U,SR|/S_UU is one step and should be far better conditioned.  Both are printed with
   their coherences, and the direct one is used.

C. THE 0xE4 DELIVERY CHANNEL.  The probe is added AFTER pid_log.output is written, so
        e4_cmd + 4089 * pid_log.output
   is the probe alone, on the wire, at 1-count resolution.  Measured here on a flown route: if that
   residual is small and white today, the probe will stand out of it by the ratio printed.
   1 count = 1/4089 = 2.446e-4 unit torque, which is also the quantiser floor for any tone.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import v282cmp as V   # noqa: E402
import lp_lib as LP   # noqa: E402

FS, NPS, G = 100.0, 1024, 256.0
DF = FS / NPS
E4_PER_UNIT = 4089.0
LSB = 1.0 / E4_PER_UNIT


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


# ---------------------------------------------------------------- A. Parseval
def parseval_factor():
    """Numeric: band RMS of a known signal vs sqrt(sum |rfft(detrend(x)*hann)|^2) over that band."""
    rng = np.random.default_rng(0)
    w = sg.get_window("hann", NPS)
    sos = sg.butter(6, [1.8, 3.5], btype="band", fs=FS, output="sos")
    x = sg.sosfiltfilt(sos, rng.standard_normal(NPS * 400))
    true_rms = float(np.sqrt(np.mean(x ** 2)))
    f = np.fft.rfftfreq(NPS, 1 / FS)
    b = (f >= 1.8) & (f <= 3.5)
    acc, nn = 0.0, 0
    for s in range(0, len(x) - NPS, NPS // 2):
        acc += np.abs(np.fft.rfft(sg.detrend(x[s:s + NPS]) * w)[b]) ** 2 @ np.ones(b.sum())
        nn += 1
    mean_sum = acc / nn
    return true_rms / np.sqrt(mean_sum), true_rms, mean_sum


if __name__ == "__main__":
    k, tr, ms = parseval_factor()
    print("A. PARSEVAL")
    print(f"   numeric factor  rms = K * sqrt(sum|X|^2)  ->  K = {k:.6f}")
    print(f"   analytic for Hann: 1/sqrt(N*sum(w^2)/2) = {1/np.sqrt(NPS*(3*NPS/8)/2):.6f}")
    print(f"   d7 used 1/256*sqrt(2) = {np.sqrt(2)/256:.6f}  ->  d7's 'today' column was "
          f"{(np.sqrt(2)/256)/k:.3f}x TOO LARGE\n")

    # ---------------------------------------------------------------- pooled T64 windows
    meta = json.load(open(F1 / "f1_meta.json"))
    routes = [r for r, g in LP.GROUPS.items() if g == "T64"]
    cols, sec = None, 0.0
    for r in routes:
        D = np.load(F1 / f"f1_{r}.npz")
        sel = D["vmed"] >= 15.0
        if cols is None:
            cols = {q: [] for q in ("Z", "M", "U", "UFB", "Y", "SR")}
            f = D["f"]
        for q in cols:
            cols[q].append(D[q][sel])
        sec += meta[r]["sec"]
        del D
    Zc, Mc, Uc, UFB, Yc, SRc = (np.concatenate(cols[q]) for q in ("Z", "M", "U", "UFB", "Y", "SR"))
    Ec = Zc - Mc
    Szz, Suu, Ssr = xs(Zc, Zc).real, xs(Uc, Uc).real, xs(SRc, SRc).real
    Tzsr = np.abs(xs(Zc, SRc) / Szz)
    Tzm = xs(Zc, Mc) / Szz
    P = xs(Zc, Mc) / xs(Zc, Uc)
    S = 1.0 / (1.0 + P * (xs(Zc, UFB) / xs(Zc, Ec)))
    Tusr = np.abs(xs(Uc, SRc) / Suu)          # DIRECT: deg/s of wheel rate per unit torque
    g_usr = coh(Uc, SRc)
    g_zsr = coh(Zc, SRc)

    D7 = np.load(OUT / "d7_ship.npz")
    KS, A = list(D7["ks"]), D7["amps"]

    print("B. COST TRANSFER, direct vs chained")
    print(f"   {'f Hz':>7s} {'|T_U,SR|':>9s} {'coh':>5s} | {'chained':>9s} {'coh(Z,SR)':>9s} | "
          f"{'A':>9s} {'cts':>5s} | {'rate DIRECT':>12s}")
    rate_direct = {}
    for kk, a in zip(KS, A):
        zeq = a * np.abs(P[kk] * S[kk]) / max(np.abs(Tzm[kk]), 1e-9)
        chained = zeq * Tzsr[kk]
        rate_direct[kk] = a * Tusr[kk]
        print(f"   {f[kk]:7.3f} {Tusr[kk]:9.2f} {g_usr[kk]:5.2f} | {chained:9.4f} {g_zsr[kk]:9.2f} | "
              f"{a:9.6f} {a/LSB:5.1f} | {rate_direct[kk]:12.4f}")

    print("\n   CORRECTED wheel-rate cost (direct transfer, correct Parseval)")
    for lo, hi, nm in [(0.60, 2.20, "CORE 0.6-2.2"), (1.80, 3.50, "SHAKE 1.8-3.5"),
                       (2.40, 5.60, "MARGIN 2.4-5.6"), (0.15, 0.60, "0.15-0.60")]:
        b = (f >= lo) & (f <= hi)
        now = k * np.sqrt(Ssr[b].sum())
        add = np.sqrt(sum(rate_direct[kk] ** 2 / 2 for kk in KS if lo <= f[kk] <= hi))
        print(f"     {nm:15s} today {now:7.4f} deg/s rms | probe adds {add:7.4f} "
              f"=> x{np.sqrt(now**2+add**2)/max(now,1e-9):5.3f}")

    # ---------------------------------------------------------------- C. the 0xE4 delivery channel
    print("\nC. 0xE4 DELIVERY CHANNEL")
    print(f"   1 count = {LSB:.6f} unit torque.  Tone sizes in counts are in the table above.")
    for r in routes[:1]:
        Ssig = V.load(r)
        m = Ssig["active"] & ~Ssig["pressed"] & (Ssig["v"] >= 15.0) & np.isfinite(Ssig["e4"]) & np.isfinite(Ssig["out"])
        resid = (Ssig["e4"] + E4_PER_UNIT * (-Ssig["out"]))[m]     # pid_log.output = -out
        resid2 = (Ssig["e4"] - E4_PER_UNIT * Ssig["out"])[m]
        best = resid if np.nanstd(resid) < np.nanstd(resid2) else resid2
        sgn = "+4089*(-out)" if np.nanstd(resid) < np.nanstd(resid2) else "-4089*out"
        print(f"   {r}: n={m.sum()}  residual e4 {sgn}: "
              f"median {np.nanmedian(best):+.2f} cts, std {np.nanstd(best):.2f} cts, "
              f"p1..p99 {np.nanpercentile(best,1):+.1f}..{np.nanpercentile(best,99):+.1f}")
        # per-bin noise floor of that residual, same transform
        w = sg.get_window("hann", NPS)
        segs = []
        for a0, b0 in V.runs(m, Ssig["t"], min_s=10.24):
            for s0 in range(a0, b0 - NPS + 1, NPS // 2):
                segs.append(np.abs(np.fft.rfft(sg.detrend(best[0:0]) * w)) if False else
                            np.abs(np.fft.rfft(sg.detrend(np.nan_to_num(
                                (Ssig["e4"] - E4_PER_UNIT * Ssig["out"])[s0:s0 + NPS])) * w)) ** 2)
        if segs:
            Sres = np.mean(segs, axis=0)
            print(f"   residual per-bin rms in counts, at the tone bins:")
            for kk, a in zip(KS, A):
                nf = np.sqrt(Sres[kk]) / G
                print(f"     {f[kk]:7.3f} Hz: tone {a/LSB:6.2f} cts | residual floor "
                      f"{nf:7.3f} cts | SNR {20*np.log10(max(a/LSB,1e-9)/max(nf,1e-9)):6.1f} dB")
        del Ssig
