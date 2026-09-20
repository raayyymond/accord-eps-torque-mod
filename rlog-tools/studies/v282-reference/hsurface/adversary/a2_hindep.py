"""ADVERSARY A2 - an INDEPENDENT re-derivation of the highway band |H|, written from scratch.

Nothing here imports v282cmp; the spectra, the windowing, the run segmentation and the masks are my own, so a
disagreement with the study's table is informative rather than circular. What I deliberately do differently:

  * FIXED window length for every group (the study's band_H picks nperseg from the SHORTEST run in whatever list
    it is handed, so a group whose shortest run is 41 s and a group whose shortest run is 90 s are measured with
    different resolution and different bias).
  * LINEAR detrend per window (the study removes only the run mean, so a slow drift leaks into the 0.08-0.25 Hz band).
  * per-window accumulation with BOTH magnitude-accumulated |Pxy| and complex-accumulated Pxy, because the study
    fixed bin-level phasor averaging but still sums the complex cross-spectrum ACROSS windows and runs before
    taking the modulus - if the phase differs window to window (different speed => different lag) that biases low.
  * the full tracking-error decomposition, so "gain" and "phase" are separated instead of being conflated in |H|.
  * three candidate output channels, so a channel artefact cannot masquerade as a build difference.

EVIDENCE method for every number printed: Welch/CSD by explicit FFT on logged, laterally-engaged, driver-hands-off
frames; no model, no simulator. This measures a closed-loop transfer from logged input to logged output.

usage: python a2_hindep.py [--nperseg 4096] [--minrun 41] [--hp 0]
out:   a2_spectra.npz (per route, per window), a2_out.txt
"""
import sys, json, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
FS = 100.0

GROUP = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64",
    "0000006e--6ca3e014fd": "T64B", "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4",
}
BANDS = [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]


def load_route(route):
    """My own loader. Everything resampled onto the controlsState clock by linear interpolation, same as the
    study, because that part is forced by the log; but I re-read the fields myself."""
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    t = D["t_cs"]

    def on_cs(tk, k):
        if tk not in D.files or k not in D.files or len(D[tk]) == 0:
            return np.full(len(t), np.nan)
        return np.interp(t, D[tk], D[k])

    v = on_cs("t_cst", "vego")
    S = dict(route=route, group=GROUP[route], t=t, v=v,
             lat_active=(D["cs_active"] > 0.5) & (on_cs("t_cc", "lat_active") > 0.5),
             pressed=on_cs("t_cst", "spress") > 0.5,
             x_model=D["cs_des_curv"] * v * v,        # logged desiredCurvature * v^2
             x_setpoint=D["cs_la_des"],               # controller's shaped/lead setpoint
             y_act=D["cs_la_act"],                    # controller's own achieved measurement
             y_pose=on_cs("t_pose", "pose_wz") * v,   # livePose yaw rate * v
             y_curv=D["cs_curv"] * v * v,             # controlsState.curvature * v^2 (angle-derived)
             sa=on_cs("t_cst", "sa_deg"), sr=on_cs("t_cst", "sr_deg"),
             out=D["cs_out"], sat=D["cs_sat"] > 0.5, roll=on_cs("t_lp", "roll"),
             ld=on_cs("t_ld", "ld_delay"))
    return S


def my_runs(mask, t, min_s, max_gap=0.04):
    """Contiguous True stretches with no clock gap. Written independently; cross-checked against v282cmp.runs
    in a3_crosscheck.py."""
    out = []
    i, n = 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < max_gap:
            j += 1
        if t[j] - t[i] >= min_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def windows(x, y, nps, hop):
    """Non-tapered slicing into windows; each window is detrended (linear) and Hann-tapered here."""
    w = np.hanning(nps)
    U = (w ** 2).sum()          # window power, for the one-sided PSD scale
    k = np.arange(nps)
    for s in range(0, len(x) - nps + 1, hop):
        xs, ys = x[s:s + nps], y[s:s + nps]
        if not (np.isfinite(xs).all() and np.isfinite(ys).all()):
            continue
        # linear detrend
        A = np.vstack([np.ones(nps), k]).T
        cx = np.linalg.lstsq(A, xs, rcond=None)[0]
        cy = np.linalg.lstsq(A, ys, rcond=None)[0]
        xd, yd = xs - A @ cx, ys - A @ cy
        X = np.fft.rfft(xd * w)
        Y = np.fft.rfft(yd * w)
        sc = 2.0 / (FS * U)
        yield (np.abs(X) ** 2 * sc, np.abs(Y) ** 2 * sc, (np.conj(X) * Y) * sc, s)


def highpass(x, fc):
    """Zero-phase 1st-order-squared Butterworth high pass, my own, applied identically to both channels."""
    from scipy import signal
    sos = signal.butter(2, fc, btype="high", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def collect(route, nps, minrun, vmin, hp, xkey="x_model", ykey="y_pose", ysign=1.0):
    S = load_route(route)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= vmin)
    x_all = np.nan_to_num(S[xkey])
    y_all = np.nan_to_num(S[ykey]) * ysign
    W = []
    for a, b in my_runs(m, S["t"], minrun):
        x, y = x_all[a:b], y_all[a:b]
        if hp > 0:
            x, y = highpass(x, hp), highpass(y, hp)
        for pxx, pyy, pxy, s in windows(x, y, nps, nps // 2):
            W.append(dict(pxx=pxx, pyy=pyy, pxy=pxy,
                          v=float(np.median(S["v"][a + s:a + s + nps])),
                          ang=float(np.median(np.abs(S["sa"][a + s:a + s + nps]))),
                          satfrac=float(np.mean(S["sat"][a + s:a + s + nps])),
                          ld=float(np.nanmedian(S["ld"][a + s:a + s + nps]))))
    meta = dict(nrun=len(my_runs(m, S["t"], minrun)), usable_s=float(m.sum() / FS),
                ld_med=float(np.nanmedian(S["ld"][m])) if m.any() else float("nan"),
                corr_pose_act=float(np.corrcoef(np.nan_to_num(S["y_pose"][m]), np.nan_to_num(S["y_act"][m]))[0, 1])
                if m.sum() > 100 else float("nan"))
    del S
    return W, meta


def band_stats(Ws, f, f1, f2):
    """Everything a band |H| needs, from a list of per-window periodograms.

    H_mag   : per-bin |Pxy| magnitude-averaged over windows then over the band (input-power weighted)
    H_phas  : the same with the complex cross-spectrum summed over windows first (the study's choice)
    R       : sqrt(Pyy/Pxx) - the amplitude ratio, phase-blind, noise-inflated: an upper bound on |H|
    coh     : magnitude-squared coherence
    ephase/egain/eincoh : the tracking-error power budget, all normalised by input power in band
    """
    if not Ws:
        return None
    sel = (f >= f1) & (f < f2)
    if sel.sum() < 1:
        return None
    Pxx = np.sum([w["pxx"] for w in Ws], axis=0)
    Pyy = np.sum([w["pyy"] for w in Ws], axis=0)
    Pxy_c = np.sum([w["pxy"] for w in Ws], axis=0)
    Pxy_m = np.sum([np.abs(w["pxy"]) for w in Ws], axis=0)
    n = len(Ws)
    wgt = Pxx[sel]
    Hm = Pxy_m[sel] / np.maximum(Pxx[sel], 1e-30)
    Hp = np.abs(Pxy_c[sel]) / np.maximum(Pxx[sel], 1e-30)
    coh = np.abs(Pxy_c[sel]) ** 2 / np.maximum(Pxx[sel] * Pyy[sel], 1e-30)
    Hc = Pxy_c[sel] / np.maximum(Pxx[sel], 1e-30)                 # complex per-bin estimate
    # error power budget, per bin, normalised by input power
    e_tot = (Pyy[sel] + Pxx[sel] - 2 * np.real(Pxy_c[sel])) / np.maximum(Pxx[sel], 1e-30)
    e_gain = (np.abs(Hc) - 1.0) ** 2
    e_phase = 2 * np.abs(Hc) * (1 - np.cos(np.angle(Hc)))
    e_incoh = (Pyy[sel] - np.abs(Pxy_c[sel]) ** 2 / np.maximum(Pxx[sel], 1e-30)) / np.maximum(Pxx[sel], 1e-30)
    av = lambda z: float(np.average(z, weights=wgt))
    return dict(H_mag=av(Hm), H_phas=av(Hp), R=float(np.sqrt(Pyy[sel].sum() / max(Pxx[sel].sum(), 1e-30))),
                coh=av(coh), phase_deg=float(np.degrees(np.angle(Pxy_c[sel].sum()))),
                nrmse=float(np.sqrt(av(e_tot))), e_gain=av(e_gain), e_phase=av(e_phase), e_incoh=av(e_incoh),
                nwin=n, in_rms=float(np.sqrt(np.sum(Pxx[sel]) * (f[1] - f[0]) / max(n, 1))),
                fbar=av(f[sel]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nperseg", type=int, default=4096)
    ap.add_argument("--minrun", type=float, default=41.0)
    ap.add_argument("--vmin", type=float, default=15.0)
    ap.add_argument("--hp", type=float, default=0.0)
    ap.add_argument("--ykey", default="y_pose")
    ap.add_argument("--xkey", default="x_model")
    ap.add_argument("--groups", default="V282,V282old,T64,T64B,T5,T4")
    a = ap.parse_args()
    nps = a.nperseg
    f = np.fft.rfftfreq(nps, 1 / FS)
    want = a.groups.split(",")

    per_route = {}
    metas = {}
    for r, g in GROUP.items():
        if g not in want:
            continue
        W, meta = collect(r, nps, a.minrun, a.vmin, a.hp, a.xkey, a.ykey)
        per_route[r] = W
        metas[r] = meta
        print(f"{r} {g:8s} runs>={a.minrun:.0f}s {meta['nrun']:3d}  windows {len(W):3d}  "
              f"usable>={a.vmin:.0f} {meta['usable_s']:6.0f} s  liveDelay med {meta['ld_med']:.3f} s  "
              f"corr(pose,act) {meta['corr_pose_act']:+.3f}", flush=True)

    print(f"\n=== band |H| {a.xkey} -> {a.ykey}, nperseg {nps} ({nps/FS:.1f} s), df {f[1]-f[0]:.4f} Hz, "
          f"minrun {a.minrun} s, v>={a.vmin}, hp {a.hp} ===")
    hdr = f"{'band':>12s} {'group':8s} {'nwin':>4s} {'Hmag':>6s} {'Hphas':>6s} {'R':>6s} {'coh':>5s} " \
          f"{'phase':>6s} {'NRMSE':>6s} {'egain':>6s} {'ephas':>6s} {'eincoh':>6s} {'fbar':>5s} {'inRMS':>6s}"
    print(hdr)
    table = {}
    for f1, f2 in BANDS:
        for g in want:
            Ws = [w for r, ws in per_route.items() if GROUP[r] == g for w in ws]
            st = band_stats(Ws, f, f1, f2)
            if not st:
                continue
            table[(f1, f2, g)] = st
            print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {st['nwin']:4d} {st['H_mag']:6.3f} {st['H_phas']:6.3f} "
                  f"{st['R']:6.3f} {st['coh']:5.3f} {st['phase_deg']:6.1f} {st['nrmse']:6.3f} "
                  f"{st['e_gain']:6.3f} {st['e_phase']:6.3f} {st['e_incoh']:6.3f} {st['fbar']:5.3f} {st['in_rms']:6.4f}")
        print()

    print("=== per ROUTE (leave-one-route-out material) ===")
    for f1, f2 in BANDS:
        for r in per_route:
            st = band_stats(per_route[r], f, f1, f2)
            if st:
                print(f"{f1:5.2f}-{f2:4.2f} {GROUP[r]:8s} {r} nwin {st['nwin']:3d} Hmag {st['H_mag']:6.3f} "
                      f"Hphas {st['H_phas']:6.3f} R {st['R']:6.3f} coh {st['coh']:5.3f} NRMSE {st['nrmse']:6.3f} "
                      f"inRMS {st['in_rms']:7.4f}")
        print()

    # per-window dump for the coherence-selection and amplitude-bias attacks
    rows = []
    for r, Ws in per_route.items():
        for iw, w in enumerate(Ws):
            rec = dict(route=r, group=GROUP[r], iw=iw, v=w["v"], ang=w["ang"], satfrac=w["satfrac"], ld=w["ld"])
            for f1, f2 in BANDS:
                st = band_stats([w], f, f1, f2)
                rec[f"H_{f1}"] = st["H_mag"]
                rec[f"coh_{f1}"] = st["coh"]
                rec[f"in_{f1}"] = st["in_rms"]
                rec[f"nrmse_{f1}"] = st["nrmse"]
            rows.append(rec)
    (HERE / f"a2_windows_n{nps}_hp{a.hp}_{a.ykey}.json").write_text(json.dumps(rows, indent=0))
    print(f"wrote {len(rows)} window records")


if __name__ == "__main__":
    main()
