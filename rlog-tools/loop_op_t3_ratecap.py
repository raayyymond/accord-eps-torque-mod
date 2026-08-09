#!/usr/bin/env python3
"""T3 -- THE RATE-LIMIT-CYCLE HYPOTHESIS, and T4 -- THE PRE-REGISTERED FALSIFIER.

===================================================================================================
T3.  openpilot's command is hard-limited to 123 counts/frame (`0.03 * STEER_MAX`, `docs/STATE.md`
L1288, "zero frames exceeding") and to +/-4096 amplitude.  A rate limiter inside a feedback loop is
a classic limit-cycle generator whose frequency is set by the CAP AND THE AMPLITUDE, not by any
plant resonance.  The brief asks for this to be treated seriously and adversarially, so it is
stated as four falsifiable predictions and each is tested:

  P1  BINDING.  A rate-limit cycle requires the limiter to be ACTIVE.  If the cap essentially never
      binds in ringing windows, P1 fails and the hypothesis is dead.
  P2  PREFERENCE.  The ring must be over-represented in cap-binding windows.  (Necessary, weak --
      speed and steering effort confound it, so it is reported as association only.)
  P3  WAVEFORM.  A slew-limited oscillation is a TRIANGLE wave: its derivative is a SQUARE wave
      pinned at +/-cap.  So `diff(cmd)` must pile up at exactly +/-123 during a ring, and the
      command must carry a 3rd harmonic at 1/9 (-19.1 dB) of the fundamental.
  P4  AMPLITUDE-SET FREQUENCY -- the discriminating one.  For a triangle wave of peak-to-peak App
      at slew R counts/frame and rate fs, f = R*fs/(2*App).  A describing-function limit cycle's
      frequency therefore MOVES with amplitude; a plant resonance's does not.  Predicted f is
      computed per window from that window's own cap rate and command amplitude and regressed
      against the observed peak.

===================================================================================================
T4.  THE FALSIFIER, pre-registered in the brief before the data were looked at:

  "if the bar's 26-31 Hz content is present in windows where the command's 26-31 Hz content is at
   its noise floor, the command cannot be driving it.  Quantify with a conditional split, and state
   the bar/command ratio DISTRIBUTION rather than a single 15.8x point estimate."

  ⚠ Stated limitation, up front: if openpilot ECHOES the bar, then the command's band content is
  CAUSED by the bar's and the two are collinear by construction -- the split then cannot separate
  the hypotheses, it can only show they co-occur.  The split is therefore informative in ONE
  direction only: a bar ring at full amplitude in the LOWEST command quintile falsifies "the
  command drives"; co-occurrence falsifies nothing.  Reported accordingly.

Writes `_cache_loop_op/t3_ratecap.json`.
"""
import json
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WIN = 512           # 5.12 s analysis window, same as the spectral episodes
HOP = 256
RING = (26.0, 31.0)
G1 = (18.0, 22.0)
MR = (6.0, 9.0)


def band_rms(x, fs, lo, hi):
    n = len(x)
    X = np.fft.rfft((x - x.mean()) * np.hanning(n))
    f = np.fft.rfftfreq(n, 1 / fs)
    s = (f >= lo) & (f <= hi)
    # Hann-window power normalisation: sum|X|^2 * 2 / (n^2 * mean(w^2))
    w = np.hanning(n)
    return float(np.sqrt(2 * np.sum(np.abs(X[s]) ** 2) / (n ** 2 * np.mean(w ** 2))))


def peak_in(x, fs, lo, hi):
    n = len(x)
    X = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(n)))
    f = np.fft.rfftfreq(n, 1 / fs)
    s = (f >= lo) & (f <= hi)
    if not s.any():
        return np.nan, np.nan
    i = np.argmax(X[s])
    return float(f[s][i]), float(X[s][i])


def windows():
    """Every clean engaged 5.12 s window across all four routes, with its covariates."""
    rows = []
    for route in L.ROUTES:
        for d in L.load_route(route):
            fs = d["_fs"]
            fm = L.fill_mask(d, "bar")
            m = L.mask_engaged(d) & L.lattice_ok(d)
            n = len(d["t"])
            for i in range(0, n - WIN, HOP):
                sl = slice(i, i + WIN)
                if not m[sl].all() or fm[sl].mean() > 0.02:
                    continue
                if np.max(np.diff(d["t"][sl])) > L.LATTICE_GAP:
                    continue
                c = d["cmd"][sl].astype(float)
                b = d["bar"][sl].astype(float)
                dc = np.diff(c)
                fr, _ = peak_in(b, fs, *RING)
                fr_c, _ = peak_in(c, fs, *RING)
                rows.append(dict(
                    route=route, seg=int(d["_seg"]), i=i, v=float(np.mean(np.abs(d["cs_v"][sl]))),
                    cap_duty=float(np.mean(np.abs(dc) >= L.SLEW_CAP - 0.5)),
                    cap_n=int(np.sum(np.abs(dc) >= L.SLEW_CAP - 0.5)),
                    amp_duty=float(np.mean(np.abs(c) >= L.STEER_MAX - 0.5)),
                    cmd_sd=float(np.std(c)), cmd_pp=float(np.ptp(c)),
                    dc_absmax=float(np.max(np.abs(dc))), dc_absmean=float(np.mean(np.abs(dc))),
                    cmd_ring=band_rms(c, fs, *RING), bar_ring=band_rms(b, fs, *RING),
                    cmd_g1=band_rms(c, fs, *G1), bar_g1=band_rms(b, fs, *G1),
                    cmd_mr=band_rms(c, fs, *MR), bar_mr=band_rms(b, fs, *MR),
                    f_bar_ring=fr, f_cmd_ring=fr_c, fs=fs))
    return rows


def quintile_table(rows, key, ys, label, nq=5):
    v = np.array([r[key] for r in rows], float)
    qs = np.quantile(v, np.linspace(0, 1, nq + 1))
    qs[-1] += 1e-9
    print(f"\n  {label}  (split on {key}, n = {len(rows)})")
    hdr = "  " + f"{'quintile':>10} {'n':>5} " + " ".join(f"{y:>12}" for y in ys)
    print(hdr)
    tab = []
    for q in range(nq):
        s = [r for r, x in zip(rows, v) if qs[q] <= x < qs[q + 1]]
        if not s:
            continue
        row = dict(q=q + 1, lo=float(qs[q]), hi=float(qs[q + 1]), n=len(s))
        cells = []
        for y in ys:
            a = np.array([r[y] for r in s], float)
            row[y] = float(np.nanmedian(a))
            cells.append(f"{np.nanmedian(a):12.4g}")
        print(f"  {qs[q]:5.3g}-{qs[q+1]:<5.3g} {len(s):5d} " + " ".join(cells))
        tab.append(row)
    return tab


def boot_ratio_dist(rows, num, den):
    r = np.array([x[num] / x[den] for x in rows if x[den] > 0], float)
    r = r[np.isfinite(r)]
    return dict(n=len(r), p5=float(np.percentile(r, 5)), p25=float(np.percentile(r, 25)),
                p50=float(np.percentile(r, 50)), p75=float(np.percentile(r, 75)),
                p95=float(np.percentile(r, 95)), mean=float(r.mean()))


def main():
    out = {}
    rows = windows()
    print(f"=== {len(rows)} clean engaged 5.12 s windows across 4 builds")
    for route in L.ROUTES:
        s = [r for r in rows if r["route"] == route]
        print(f"    {route}: {len(s)}")

    # -------------------------------------------------------------------- P1 BINDING ------------
    cap = np.array([r["cap_duty"] for r in rows])
    dcm = np.array([r["dc_absmax"] for r in rows])
    print(f"\n=== P1 BINDING.  |d(cmd)| >= {L.SLEW_CAP:.0f} counts/frame")
    print(f"  window-median cap duty = {np.median(cap)*100:.3f}%   mean = {np.mean(cap)*100:.3f}%   "
          f"p95 = {np.percentile(cap,95)*100:.2f}%   max = {cap.max()*100:.2f}%")
    print(f"  windows with ANY capped frame: {np.mean(cap>0)*100:.1f}%   "
          f"with >5% capped: {np.mean(cap>0.05)*100:.1f}%")
    print(f"  ⚠ window max |d(cmd)| on the BATCH GRID: p50 {np.median(dcm):.0f} max {dcm.max():.0f} "
          f"-- exceeds the cap ONLY because a batch missing a 0x0E4 makes the diff span two\n"
          f"    transmitted frames.  The native-lattice figure is in P3 and is the real one.")
    out["P1"] = dict(cap_duty_median=float(np.median(cap)), cap_duty_mean=float(np.mean(cap)),
                     cap_duty_p95=float(np.percentile(cap, 95)), cap_duty_max=float(cap.max()),
                     frac_any=float(np.mean(cap > 0)), frac_gt5pct=float(np.mean(cap > 0.05)),
                     dcmd_absmax=float(dcm.max()))

    # -------------------------------------------------------------------- P2 PREFERENCE ---------
    print("\n=== P2 PREFERENCE.  Does the ring live in cap-binding windows?")
    out["P2"] = quintile_table(rows, "cap_duty",
                               ["bar_ring", "cmd_ring", "bar_g1", "cmd_g1", "v", "cmd_sd"],
                               "bar/cmd band rms (counts) by CAP-DUTY quintile")
    out["P2_speed"] = quintile_table(rows, "v", ["bar_ring", "cmd_ring", "cap_duty", "cmd_sd"],
                                     "the same, split on SPEED -- the confound")

    # -------------------------------------------------------------------- P3 WAVEFORM -----------
    print("\n=== P3 WAVEFORM.  A slew-limited oscillation is a TRIANGLE: d(cmd) pinned at +/-cap,")
    print("    and a 3rd harmonic at 1/9 = -19.1 dB of the fundamental.")
    top = sorted(rows, key=lambda r: -r["bar_ring"])[:max(20, len(rows) // 10)]
    # 🛑 MEASURED ON THE NATIVE 0x0E4 LATTICE, not the batch grid.  A batch that carries no 0x0E4
    # makes the batch-grid diff span TWO transmitted frames, which manufactures apparent slews of
    # up to 2x the cap (340 counts was observed that way) and would falsely refute the record's
    # "zero frames exceeding".  On the native sequence every diff is one transmitted frame.
    dc_all, dc_engaged = [], []
    for route in L.ROUTES:
        for d in L.load_route(route):
            ne = np.asarray(d["ne4_cmd"], float)
            nt = np.asarray(d["ne4_t"], float)
            if len(ne) < 10:
                continue
            good = np.diff(nt) < L.LATTICE_GAP
            dc = np.abs(np.diff(ne))[good]
            # engagement, held onto the native 0x0E4 lattice
            eng = np.interp(nt, d["t"], (d["cc_lat"] > 0.5).astype(float))[1:][good] > 0.5
            dc_all.append(dc)
            dc_engaged.append(dc[eng])
    dc_all = np.concatenate(dc_all)
    dc_all = np.concatenate(dc_engaged)
    print(f"  |d(cmd)| over ALL engaged frames (n = {len(dc_all)}):")
    for thr in (0, 1, 10, 50, 100, 122, 123):
        print(f"    >= {thr:4d}: {np.mean(dc_all >= thr)*100:6.2f}%", end="")
    print()
    print(f"    == 123 EXACTLY: {np.mean(dc_all == 123)*100:.3f}%   "
          f"(a triangle-wave limit cycle would sit here on ~100% of frames)")
    # 3rd-harmonic test on the strongest-ring windows
    h3 = []
    for r in top:
        route, seg, i = r["route"], r["seg"], r["i"]
        d = [x for x in L.load_route(route) if x["_seg"] == seg][0]
        c = d["cmd"][i:i + WIN].astype(float)
        f0, a0 = peak_in(c, r["fs"], *RING)
        if not np.isfinite(f0):
            continue
        _, a3 = peak_in(c, r["fs"], 3 * f0 - 1.0, 3 * f0 + 1.0)
        if a0 > 0 and np.isfinite(a3):
            h3.append(a3 / a0)
    h3 = np.array(h3)
    print(f"  3rd-harmonic ratio of the COMMAND in the {len(top)} strongest-ring windows: "
          f"median {np.median(h3):.4f}  (triangle = 0.1111, sine = 0)")
    print(f"    🛑 at 3 x 27.5 = 82.5 Hz the 100 Hz instrument is BLIND (aliased); the harmonic "
          f"read is at the alias, so this leg is UNRESOLVABLE and is reported as such.")
    out["P3"] = dict(dcmd_eq_cap_pct=float(np.mean(dc_all == 123) * 100),
                     dcmd_ge_cap_pct=float(np.mean(dc_all >= 123) * 100),
                     dcmd_ge100_pct=float(np.mean(dc_all >= 100) * 100),
                     h3_median=float(np.median(h3)) if len(h3) else None,
                     h3_note="3f0 = 82.5 Hz is above Nyquist -- UNRESOLVABLE at fs = 100 Hz")

    # -------------------------------------------------------------------- P4 f(amplitude) -------
    print("\n=== P4 AMPLITUDE-SET FREQUENCY -- the discriminating prediction.")
    print("    triangle at slew R counts/frame, peak-to-peak App:  f = R*fs / (2*App)")
    sel = [r for r in rows if r["cap_duty"] > 0.05 and np.isfinite(r["f_bar_ring"])]
    print(f"    {len(sel)} windows with cap duty > 5%")
    if sel:
        pred = np.array([L.SLEW_CAP * r["fs"] / (2 * r["cmd_pp"]) for r in sel])
        obs = np.array([r["f_bar_ring"] for r in sel])
        print(f"    predicted f: p5 {np.percentile(pred,5):.3f}  p50 {np.median(pred):.3f}  "
              f"p95 {np.percentile(pred,95):.3f} Hz")
        print(f"    observed bar ring peak: p5 {np.percentile(obs,5):.2f}  p50 {np.median(obs):.2f}"
              f"  p95 {np.percentile(obs,95):.2f} Hz")
        rr = np.corrcoef(pred, obs)[0, 1]
        print(f"    corr(predicted, observed) = {rr:+.4f}")
        out["P4"] = dict(n=len(sel), pred_p50=float(np.median(pred)), obs_p50=float(np.median(obs)),
                         corr=float(rr), pred_p5=float(np.percentile(pred, 5)),
                         pred_p95=float(np.percentile(pred, 95)))
    # amplitude-vs-frequency inside the ring band: does f move with the RING amplitude?
    rsel = [r for r in rows if np.isfinite(r["f_bar_ring"]) and r["bar_ring"] > 0]
    a = np.array([r["bar_ring"] for r in rsel]); fo = np.array([r["f_bar_ring"] for r in rsel])
    print(f"    corr(log ring amplitude, ring frequency) = "
          f"{np.corrcoef(np.log(a), fo)[0,1]:+.4f}  (n = {len(rsel)}) "
          f"-- a describing-function cycle REQUIRES a strong negative value")
    out["P4_amp_freq_corr"] = float(np.corrcoef(np.log(a), fo)[0, 1])

    # -------------------------------------------------------------------- T4 FALSIFIER ----------
    print("\n\n=== T4.  THE PRE-REGISTERED FALSIFIER")
    out["T4_ring"] = quintile_table(rows, "cmd_ring",
                                    ["bar_ring", "cmd_ring", "cap_duty", "v", "cmd_sd"],
                                    "BAR 26-31 rms by COMMAND 26-31 rms quintile")
    out["T4_g1"] = quintile_table(rows, "cmd_g1", ["bar_g1", "cmd_g1", "cap_duty", "v"],
                                  "BAR 18-22 rms by COMMAND 18-22 rms quintile")
    print("\n  bar/command band-rms RATIO DISTRIBUTION (replaces the single 15.8x point estimate):")
    for nm, num, den in (("26-31 Hz", "bar_ring", "cmd_ring"), ("18-22 Hz", "bar_g1", "cmd_g1"),
                         ("6-9 Hz", "bar_mr", "cmd_mr")):
        r = boot_ratio_dist(rows, num, den)
        print(f"    {nm}: n={r['n']}  p5 {r['p5']:.2f}  p25 {r['p25']:.2f}  "
              f"MEDIAN {r['p50']:.2f}  p75 {r['p75']:.2f}  p95 {r['p95']:.2f}")
        out[f"ratio_{nm.split()[0]}"] = r
    # the falsifier's own statement
    q1 = [r for r in rows if r["cmd_ring"] <= np.quantile([x["cmd_ring"] for x in rows], 0.2)]
    q5 = [r for r in rows if r["cmd_ring"] >= np.quantile([x["cmd_ring"] for x in rows], 0.8)]
    b1 = np.median([r["bar_ring"] for r in q1]); b5 = np.median([r["bar_ring"] for r in q5])
    c1 = np.median([r["cmd_ring"] for r in q1]); c5 = np.median([r["cmd_ring"] for r in q5])
    print(f"\n  FALSIFIER: bottom command quintile (cmd 26-31 = {c1:.2f} ct) -> bar "
          f"{b1:.2f} ct;  top ({c5:.2f} ct) -> bar {b5:.2f} ct.")
    print(f"    bar ratio top/bottom = {b5/b1:.2f}x  against a command ratio of {c5/c1:.2f}x")
    out["falsifier"] = dict(cmd_q1=float(c1), cmd_q5=float(c5), bar_q1=float(b1), bar_q5=float(b5),
                            bar_ratio=float(b5 / b1), cmd_ratio=float(c5 / c1))

    (L.CACHE / "t3_ratecap.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't3_ratecap.json'}")


if __name__ == "__main__":
    main()
