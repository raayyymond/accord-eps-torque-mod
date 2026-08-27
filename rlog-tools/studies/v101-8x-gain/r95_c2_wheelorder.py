#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- **C (part 2). THE WHEEL-ORDER TRAP, done per WINDOW.**

🛑 The kit's recorded trap: a spectral line at ~0.482*v_ms Hz is TYRE ORDER 1 (circumference
2.073-2.080 m, measured V57), not the firmware.  Averaged spectra need MATCHED speed distributions
or a moving wheel order manufactures a fake "line".

METHOD: slide a 256-sample Hann window (2.578 s, df = 0.388 Hz) over the CONTIGUOUS engaged runs,
50 % overlap.  Each window carries its OWN speed census (median v over the window, and the spread).
Windows are then binned by speed and their PSDs averaged WITHIN the bin, so every averaged spectrum
has a stated, narrow speed distribution.  The per-window peak frequency is then regressed on v.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
lat = L.engaged()
vms = np.abs(L.col("cs_v"))
vk = vms * 3.6
CIRC = 2.0765
ORDER1 = 1.0 / CIRC

NFFT = 256
STEP = NFFT // 2
WIN = np.hanning(NFFT)
FREQ = np.fft.rfftfreq(NFFT, 1 / FS)
DF = FREQ[1]
print(f"nfft={NFFT}  window {NFFT/FS:.3f} s  df={DF:.4f} Hz   FS={FS:.3f}")

CH = {"tq": L.col("tq"), "rate_f": L.col("rate_f"), "x6b94": L.col("x6b94"),
      "ang": L.col("ang"), "sc_tq": L.col("sc_tq")}


def _runs(mask, min_n):
    idx = np.where(mask)[0]
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                out.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        out.append((s, prev + 1))
    return out


# ---- build the window table
W = {"i0": [], "v_med": [], "v_iqr": [], "rate_med": [], "tq_abs_med": [], "cmd_abs_med": []}
PSD = {k: [] for k in CH}
tqa = np.abs(L.lowpass(L.col("tq"), FS, 3.0, mask=lat))
rate_abs = np.abs(L.col("rate_f"))
cmd_abs = np.abs(L.col("sc_tq"))

for a, b in _runs(lat, NFFT):
    for i in range(a, b - NFFT + 1, STEP):
        sl = slice(i, i + NFFT)
        v = vms[sl]
        W["i0"].append(i)
        W["v_med"].append(float(np.median(v)))
        W["v_iqr"].append(float(np.percentile(v, 75) - np.percentile(v, 25)))
        W["rate_med"].append(float(np.median(rate_abs[sl])))
        W["tq_abs_med"].append(float(np.nanmedian(tqa[sl])))
        W["cmd_abs_med"].append(float(np.median(cmd_abs[sl])))
        for k, x in CH.items():
            seg = x[sl]
            seg = np.nan_to_num(seg - np.nanmean(seg), nan=0.0)
            PSD[k].append(np.abs(np.fft.rfft(seg * WIN)) ** 2 / ((WIN ** 2).sum() * FS))

for k in W:
    W[k] = np.array(W[k], float)
for k in PSD:
    PSD[k] = np.array(PSD[k])
NW = len(W["i0"])
print(f"{NW} engaged windows  ({NW*STEP/FS:.1f} s of unique coverage)")

out = {"nfft": NFFT, "df": DF, "n_windows": NW, "order1_hz_per_ms": ORDER1}

# =====================================================================================
BINS = [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 20)]      # m/s
print("\n" + "=" * 108)
print("PER-SPEED-BIN AVERAGED PSD  --  peak in 4-13 Hz and in 15-32 Hz, with the tyre prediction")
print("=" * 108)


def pk(P, lo, hi):
    b = (FREQ >= lo) & (FREQ <= hi)
    fb, Pb = FREQ[b], P[b]
    i = int(np.argmax(Pb))
    med = float(np.median(P[(FREQ >= 2) & (FREQ <= 45)]))
    return float(fb[i]), float(Pb[i] / med)


for key in ("tq", "rate_f", "x6b94"):
    print(f"\n### {key}")
    print(f"    {'v m/s':>10s} {'n_win':>6s} {'sec':>6s} {'v med':>6s} {'v p10':>6s} {'v p90':>6s} "
          f"{'TYRE o1':>8s} | {'pk 4-13':>8s} {'xmed':>6s} {'Δ tyre':>7s} | {'pk 15-32':>9s} "
          f"{'xmed':>6s}")
    rows = []
    for lo, hi in BINS:
        m = (W["v_med"] >= lo) & (W["v_med"] < hi)
        if m.sum() < 4:
            continue
        P = PSD[key][m].mean(axis=0)
        vmed = float(np.median(W["v_med"][m]))
        f1, r1 = pk(P, 4.0, 13.0)
        f2, r2 = pk(P, 15.0, 32.0)
        tyre = vmed * ORDER1
        print(f"    {lo:4d}-{hi:<5d} {int(m.sum()):6d} {m.sum()*STEP/FS:6.1f} {vmed:6.2f} "
              f"{np.percentile(W['v_med'][m],10):6.2f} {np.percentile(W['v_med'][m],90):6.2f} "
              f"{tyre:8.2f} | {f1:8.2f} {r1:6.1f} {f1-tyre:+7.2f} | {f2:9.2f} {r2:6.1f}")
        rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), v_med=vmed, tyre_o1=tyre,
                         f_lo=f1, r_lo=r1, f_hi=f2, r_hi=r2))
    out.setdefault("bins", {})[key] = rows

# =====================================================================================
print("\n" + "=" * 108)
print("PER-WINDOW PEAK-FREQUENCY REGRESSION  f_peak = a*v_ms + b")
print("  TYRE ORDER 1 predicts a = +0.4816, b = 0.  A FIXED RESONANCE predicts a = 0.")
print("  Restricted to windows where the band peak is >= 6x the 2-45 Hz median (a real line).")
print("=" * 108)
for key in ("tq", "rate_f", "x6b94"):
    for band, (lo, hi) in (("4-13 Hz", (4.0, 13.0)), ("15-32 Hz", (15.0, 32.0))):
        fp, rr = [], []
        for w in range(NW):
            f0, r0 = pk(PSD[key][w], lo, hi)
            fp.append(f0)
            rr.append(r0)
        fp, rr = np.array(fp), np.array(rr)
        sel = rr >= 6.0
        if sel.sum() < 10:
            print(f"  {key:6s} {band:9s}  only {int(sel.sum())} qualifying windows -- SKIP")
            continue
        v = W["v_med"][sel]
        y = fp[sel]
        A = np.vstack([v, np.ones_like(v)]).T
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ beta
        # bootstrap the slope over windows spaced >= 1 window apart (blocks of 4 windows)
        rng = np.random.default_rng(7)
        idx = np.arange(len(v))
        blocks = [idx[i:i + 4] for i in range(0, len(idx), 4)]
        bs = []
        for _ in range(3000):
            j = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
            Ab = np.vstack([v[j], np.ones_like(v[j])]).T
            try:
                bs.append(np.linalg.lstsq(Ab, y[j], rcond=None)[0][0])
            except np.linalg.LinAlgError:
                pass
        blo, bhi = np.percentile(bs, [2.5, 97.5])
        r2 = 1 - np.var(res) / np.var(y)
        print(f"  {key:6s} {band:9s}  n={int(sel.sum()):4d}  slope {beta[0]:+7.4f} "
              f"[{blo:+.4f}, {bhi:+.4f}] Hz/(m/s)   intercept {beta[1]:6.2f} Hz   R2 {r2:5.3f}"
              f"   {'⇒ TYRE (slope brackets +0.4816)' if blo <= ORDER1 <= bhi else ''}"
              f"{'  ⇒ SPEED-INVARIANT (slope brackets 0)' if blo <= 0 <= bhi else ''}")
        out.setdefault("regress", []).append(
            dict(channel=key, band=band, n=int(sel.sum()), slope=float(beta[0]),
                 lo=float(blo), hi=float(bhi), intercept=float(beta[1]), r2=float(r2)))

np.savez_compressed(L.CACHE / "r95_windows.npz", freq=FREQ, **{f"psd_{k}": v for k, v in PSD.items()},
                    **{f"w_{k}": v for k, v in W.items()})
(L.CACHE / "r95_C2_wheelorder.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_C2_wheelorder.json'} and r95_windows.npz")
