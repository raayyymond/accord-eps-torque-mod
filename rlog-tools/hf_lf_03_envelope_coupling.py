#!/usr/bin/env python3
r"""HF -> LF ENVELOPE COUPLING.  Does the amplitude of a high-frequency band oscillate slowly, and
is that slow oscillation locked to a low-frequency motion of the column?

THE OPERATOR'S CLAIM (2026-08-22): "the grind #3 at high speed is also somehow resulting in a
lower ratcheting-like mode of oscillation on the highway."

HYPOTHESES
  H1 amplitude modulation / relaxation -- envelope(HF) carries a LINE at f_LF and is phase-locked
                                          to the column's own LF motion
  H2 intermodulation / beating         -- two HF lines separated by f_LF      (`..._04_`)
  H3 rate-scheduled ceiling dropout    -- assist clipped by the motor-rate-scheduled bound
                                          `gp-0x4f64`                          (`..._05_`)
  H4 nothing                           -- the LF motion is independent

🛑 WHAT THE FIRST PASS OF THIS FILE GOT WRONG, RECORDED SO IT IS NOT REPEATED
  v1 used a phase-randomised surrogate as the null for BOTH statistics and got p = 0.005 in EVERY
  band including the pre-declared negative control, with the envelope peak pinned to the lowest
  analysed bin on every arm.  That is not a mechanism, it is NON-STATIONARITY: a driving record
  whose amplitude waxes and wanes rejects "stationary process with this PSD" by construction.
  Two fixes, both in force here:
    * the envelope-line statistic is a LOCAL PROMINENCE (peak over the local background of the
      envelope's OWN spectrum), which is blind to a smooth 1/f rise;
    * the coherence null is a CIRCULAR TIME SHIFT of the envelope against the reference, which
      preserves BOTH series' full structure -- burstiness included -- and destroys only their
      alignment.  That is the only null that isolates coupling from co-occurrence.

CONTROLS THAT RUN BEFORE ANY NUMBER IS QUOTED
  N1 phase-randomised-band surrogate  (for the prominence statistic; 200 draws)
  N2 circular-shift surrogate         (for every coherence; 200 draws, |lag| >= 5 s)
  N3 ARTEFACT arm -- jitter-interpolation HF regenerated on the REAL logged timestamps, through
     the IDENTICAL estimator.  `hf_lf_01` measured it at 0.4-8 % of band amplitude and it is BY
     CONSTRUCTION locked to the LF slope, i.e. it fakes H1.
  N4 CONTROL BAND 32-38 Hz  (⚠ wheel order 3 is 32.7-40.1 Hz at these speeds -- printed)
  N5 ARM CONTRAST engaged vs MANUAL at matched speed (only route 9e has manual highway, 28.6 s)
  N6 STOCK (route 97): absent on stock + present on V103 => it is ours

🛑 `e4tq` is REPORTED ONLY, never an independent variable (`STATE.md` 2026-08-22: openpilot's
command is not exogenous at 6-9 Hz).

OUTPUT `rlog-tools/_hf_lf_coupling.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTE_LABEL = {"97": "STOCK (V9b)", "9e": "V103", "96": "V102 6x", "85": "V100 4x"}
ROUTES = ["9e", "97", "96", "85"]
KMH, CIRC, FS = 3.6, 2.0805, L.FS

HF_BANDS = {"15-22": (15.0, 22.0), "20-30": (20.0, 30.0), "22-26": (22.0, 26.0),
            "26-31": (26.0, 31.0), "32-38": (32.0, 38.0), "40-49": (40.0, 49.0)}
CTRL_BAND = "32-38"
LF_LO, LF_HI = 0.25, 3.0
NSEG, HOP = 1024, 512       # 10.24 s -> 0.0977 Hz bins
NSURR = 200
CARRIER = "tq"
LFREFS = ("tq", "rate_c", "ang", "e4tq")
MIN_SHIFT_S = 5.0


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 112)
    print(s)
    print("=" * 112, flush=True)


# ------------------------------------------------------------------ blocks that keep native t ---
def blocks_with_native(rt):
    """`v102_xb_lib.blocks` but the NATIVE logged timestamps are kept -- the artefact arm needs
    them to reproduce the real interpolation error."""
    out = []
    for s in L.ROUTES[rt]["segs"]:
        d = L.load_seg(rt, s)
        t = d["t"]
        brk = np.nonzero(np.diff(t) > L.GAP_S)[0]
        for a, b in zip([0] + [int(x) + 1 for x in brk], [int(x) + 1 for x in brk] + [len(t)]):
            if b - a < 4 or t[b - 1] - t[a] < 2.0:
                continue
            tt = np.arange(t[a], t[b - 1], 1.0 / FS)
            blk = {"t": tt, "_seg": s, "_tnat": t[a:b]}
            for k, v in d.items():
                if k.startswith("_") or k == "t" or np.shape(v) != np.shape(t):
                    continue
                blk[k] = np.interp(tt, t[a:b], v[a:b])
            out.append(blk)
    return out


def episodes(rt, engaged=True, vlo=70.0, vhi=200.0, minlen=NSEG):
    out = []
    for blk in blocks_with_native(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        want = (eng if engaged else ~eng) & (v >= vlo) & (v < vhi)
        idx = np.nonzero(np.diff(want.astype(int)) != 0)[0] + 1
        for a, b in zip([0] + list(idx), list(idx) + [len(want)]):
            if not want[a] or (b - a) < minlen:
                continue
            ep = {k: np.asarray(blk[k], float)[a:b] for k in blk
                  if not k.startswith("_") and np.shape(blk[k]) == np.shape(blk["t"])}
            ep["_seg"], ep["_tnat"], ep["_v"] = blk["_seg"], blk["_tnat"], float(np.median(v[a:b]))
            out.append(ep)
    return out


# ------------------------------------------------------------------ estimators ------------------
def analytic_env(x, lo, hi, fs=FS):
    """TRUE analytic envelope -- NOT `_r31_common.band_envelope`, which is rectified."""
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1.0 / fs)
    Z = np.zeros(n, complex)
    m = (f >= lo) & (f < hi)
    Z[m] = 2.0 * X[m]
    return np.abs(np.fft.ifft(Z))


def phase_rand_band(x, lo, hi, rng, fs=FS):
    """Randomise the phases of [lo,hi) ONLY.  |X| untouched; all LF content untouched."""
    n = len(x)
    X = np.fft.rfft(np.asarray(x, float))
    f = np.fft.rfftfreq(n, 1.0 / fs)
    m = (f >= lo) & (f < hi)
    X = X.copy()
    X[m] = np.abs(X[m]) * np.exp(1j * rng.uniform(0, 2 * np.pi, int(m.sum())))
    return np.fft.irfft(X, n=n)


_W = np.hanning(NSEG)
_R = np.arange(NSEG, dtype=float)
_SCALE = float(np.mean(_W ** 2))
FREQ = np.fft.rfftfreq(NSEG, 1.0 / FS)


def parts(series):
    """Detrended Hann DFT of every NSEG segment of every episode, in episode order."""
    Xs = []
    for x in series:
        x = np.asarray(x, float)
        for s in range(0, len(x) - NSEG + 1, HOP):
            y = x[s:s + NSEG]
            c = np.polyfit(_R, y, 1)
            Xs.append(np.fft.rfft((y - (c[0] * _R + c[1])) * _W))
    return np.asarray(Xs)


def welch_P(X):
    P = (np.abs(X) ** 2).mean(0) * 2.0 / (NSEG ** 2) / _SCALE
    P[0] /= 2.0
    P[-1] /= 2.0
    return P


def coh_band(A, B, lo=LF_LO, hi=LF_HI):
    Sab = (A * np.conj(B)).mean(0)
    g = (np.abs(Sab) ** 2) / np.maximum((np.abs(A) ** 2).mean(0) * (np.abs(B) ** 2).mean(0), 1e-30)
    m = (FREQ >= lo) & (FREQ <= hi)
    return float(g[m].mean()), g, Sab


def prominence(P, lo=LF_LO, hi=LF_HI, half=0.75, gap=0.15):
    """Peak of P in [lo,hi] over the MEDIAN of its own local background.

    Blind to a smooth 1/f rise, which is what killed the v1 statistic.
    """
    m = (FREQ >= lo) & (FREQ <= hi)
    idx = np.flatnonzero(m)
    best, bf = 0.0, np.nan
    for i in idx:
        f0 = FREQ[i]
        bg = (np.abs(FREQ - f0) <= half) & (np.abs(FREQ - f0) > gap) & (FREQ > 0.05)
        if bg.sum() < 4:
            continue
        r = P[i] / max(float(np.median(P[bg])), 1e-30)
        if r > best:
            best, bf = r, f0
    return float(best), float(bf)


def norm_env(envs):
    return [(e - e.mean()) / max(e.mean(), 1e-9) for e in envs]


# ------------------------------------------------------------------ N3 the artefact arm ---------
def artefact_series(eps, fc_lf=12.0, seed=17):
    """Regenerate, per episode, the HF that jittery-timestamp interpolation manufactures out of
    <12 Hz content, using the arm's OWN low-frequency amplitude spectrum."""
    rng = np.random.default_rng(seed)
    Pw = welch_P(parts([e[CARRIER] for e in eps]))
    m = (FREQ > 0.05) & (FREQ <= fc_lf)
    f_c, amp_c = FREQ[m], np.sqrt(2.0 * Pw[m])
    ph = rng.uniform(0, 2 * np.pi, len(f_c))

    def ev(tt):
        return (amp_c[None, :] * np.cos(2 * np.pi * f_c[None, :] * tt[:, None]
                                        + ph[None, :])).sum(1)

    out = []
    for e in eps:
        u, tn = e["t"], e["_tnat"]
        tn = tn[(tn >= u[0] - 0.05) & (tn <= u[-1] + 0.05)]
        out.append(np.zeros_like(u) if len(tn) < 10 else np.interp(u, tn, ev(tn)) - ev(u))
    return out


# ------------------------------------------------------------------ one arm ---------------------
def score_arm(rt, eps, label, seed=0):
    rng = np.random.default_rng(seed)
    car = [e[CARRIER] for e in eps]
    art = artefact_series(eps)
    lens = [len(e["t"]) for e in eps]
    res = dict(label=label, n_ep=len(eps), s=float(sum(lens) / FS),
               v_med=float(np.median([e["_v"] for e in eps])),
               wo1=float(np.median([e["_v"] for e in eps]) / KMH / CIRC), bands={}, lf={})

    # ---- LF reference DFTs, and the LF presence test (does an LF oscillation exist at all?) ----
    ref_parts = {}
    for ref in LFREFS:
        if ref in eps[0]:
            ref_parts[ref] = parts([e[ref] for e in eps])
            P = welch_P(ref_parts[ref])
            mm = (FREQ >= LF_LO) & (FREQ <= LF_HI)
            pr, pf = prominence(P)
            res["lf"][ref] = dict(band_rms=float(np.sqrt(P[mm].sum())), prom=pr, f_prom=pf)

    envs_all = {}
    for bn, (lo, hi) in HF_BANDS.items():
        envs = [analytic_env(x, lo, hi) for x in car]
        envs_all[bn] = envs
        ne = norm_env(envs)
        Xe = parts(ne)
        Pe = welch_P(Xe)
        prom, fprom = prominence(Pe)
        mm = (FREQ >= LF_LO) & (FREQ <= LF_HI)
        mod = float(np.sqrt(2.0 * Pe[mm].sum()))

        # --- N1: prominence null, phases of THIS band randomised ---------------------------
        s_prom = np.empty(NSURR)
        for k in range(NSURR):
            se = [analytic_env(phase_rand_band(x, lo, hi, rng), lo, hi) for x in car]
            s_prom[k] = prominence(welch_P(parts(norm_env(se))))[0]

        # --- N2: coherence with circular-shift null ----------------------------------------
        cohs = {}
        for ref, Xr in ref_parts.items():
            obs, g, Sab = coh_band(Xe, Xr)
            mband = (FREQ >= LF_LO) & (FREQ <= LF_HI)
            ipk = int(np.flatnonzero(mband)[np.argmax(g[mband])])
            null = np.empty(NSURR)
            for k in range(NSURR):
                rolled = []
                for e_, L_ in zip(ne, lens):
                    lo_s = int(MIN_SHIFT_S * FS)
                    if L_ <= 2 * lo_s + 10:
                        sh = int(rng.integers(1, max(L_ - 1, 2)))
                    else:
                        sh = int(rng.integers(lo_s, L_ - lo_s))
                    rolled.append(np.roll(e_, sh))
                null[k] = coh_band(parts(rolled), Xr)[0]
            cohs[ref] = dict(obs=obs,
                             null_med=float(np.median(null)),
                             null_p95=float(np.percentile(null, 95)),
                             p=float((1 + np.sum(null >= obs)) / (NSURR + 1)),
                             f_peak=float(FREQ[ipk]), coh_peak=float(g[ipk]),
                             phase_deg=float(np.degrees(np.angle(Sab[ipk]))))
        # --- N3: artefact arm through the identical estimator -------------------------------
        aenv = [analytic_env(x, lo, hi) for x in art]
        Xa = parts(norm_env(aenv))
        a_c = {ref: coh_band(Xa, Xr)[0] for ref, Xr in ref_parts.items()}
        res["bands"][bn] = dict(
            env_mean=float(np.median([e.mean() for e in envs])),
            mod_band=mod, prom=prom, f_prom=fprom,
            prom_null_med=float(np.median(s_prom)), prom_null_p95=float(np.percentile(s_prom, 95)),
            prom_p=float((1 + np.sum(s_prom >= prom)) / (NSURR + 1)),
            coh=cohs, artefact_coh=a_c,
            artefact_amp_frac=float(np.median([x.mean() for x in aenv]) /
                                    max(np.median([x.mean() for x in envs]), 1e-12)),
            spec_f=[float(x) for x in FREQ[(FREQ > 0) & (FREQ <= 6.0)]],
            spec_P=[float(x) for x in Pe[(FREQ > 0) & (FREQ <= 6.0)]],
        )
    # ---- cross-band envelope coherence: does ONE slow process modulate several bands? ----
    res["xband"] = {}
    keys = list(HF_BANDS)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            Xa, Xb = parts(norm_env(envs_all[a])), parts(norm_env(envs_all[b]))
            res["xband"]["%s~%s" % (a, b)] = coh_band(Xa, Xb)[0]
    return res


def main():
    out = {}
    arms = [("ENGAGED hwy", True, 70.0, 200.0), ("manual hwy", False, 70.0, 200.0),
            ("ENGAGED mid", True, 40.0, 70.0), ("ENGAGED low", True, 0.0, 40.0),
            ("manual low", False, 0.0, 40.0)]
    for rt in ROUTES:
        if not reg(rt):
            continue
        out[rt] = {}
        for lab, eng, vlo, vhi in arms:
            eps = episodes(rt, engaged=eng, vlo=vlo, vhi=vhi)
            if not eps:
                continue
            r = score_arm(rt, eps, lab, seed=abs(hash((rt, lab))) % 10000)
            out[rt][lab] = r
            hdr("ROUTE %s (%s)   ARM %s   %d episodes, %.1f s, v=%.1f km/h "
                "(wheel orders %.1f / %.1f / %.1f Hz)"
                % (rt, ROUTE_LABEL.get(rt, rt), lab, r["n_ep"], r["s"], r["v_med"],
                   r["wo1"], 2 * r["wo1"], 3 * r["wo1"]))
            print("  LF (%.2f-%.1f Hz) presence: %s"
                  % (LF_LO, LF_HI, "  ".join("%s rms=%.3g prom=%.2f@%.2fHz"
                                             % (k, v["band_rms"], v["prom"], v["f_prom"])
                                             for k, v in r["lf"].items())))
            print("  %-6s %7s %6s | %-22s | %-34s | %s"
                  % ("band", "env", "mod", "ENVELOPE LINE (prominence)",
                     "coh2(env, tq_LF) obs/null95/p/art", "coh2(env, rate_c) obs/null95/p/art"))
            for bn, b in r["bands"].items():
                c1, c2 = b["coh"].get("tq", {}), b["coh"].get("rate_c", {})
                tag = "CTRL" if bn == CTRL_BAND else ""
                print("  %-6s %7.2f %6.3f | %5.2f@%4.2fHz null%5.2f p%.3f | "
                      "%.3f/%.3f/%.3f/%.3f | %.3f/%.3f/%.3f/%.3f %s"
                      % (bn, b["env_mean"], b["mod_band"], b["prom"], b["f_prom"],
                         b["prom_null_p95"], b["prom_p"],
                         c1.get("obs", np.nan), c1.get("null_p95", np.nan), c1.get("p", np.nan),
                         b["artefact_coh"].get("tq", np.nan),
                         c2.get("obs", np.nan), c2.get("null_p95", np.nan), c2.get("p", np.nan),
                         b["artefact_coh"].get("rate_c", np.nan), tag))
            print("  cross-band envelope coh2 (one slow process would raise ALL of these): %s"
                  % "  ".join("%s=%.3f" % (k, v) for k, v in r["xband"].items()))
    (HERE / "_hf_lf_coupling.json").write_text(json.dumps(out, indent=1))
    print("\nwrote", HERE / "_hf_lf_coupling.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
