#!/usr/bin/env python3
"""v86_probe_physics.py -- what the V86 / V86B `gp-0x6b70` probe cave actually MEASURED.

🛑 THE BIT MAP IS IMPORTED FROM THE BUILDERS. Nothing here re-types a threshold or a weight.

Sections
  0  decode + identity re-derivation from `raw14_b4`, and the 5-BIN physical alphabet
  1  RELAY-vs-LINEAR, with its null   (the headline -- and its STRUCTURAL LIMIT)
  2  spectrum of the reconstructed 1.5-bit waveform, with a run-order surrogate
  3  the aggregator gate b4
  4  engaged/manual, route-vs-route with exposure control, Y[0] and clamp bounds
  5  WHAT DRIVES IT -- sign-agreement against every synchronous CAN channel
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import build_v86_tva as V86      # noqa: E402
import build_v86b_tva as V86B    # noqa: E402

ROUTES = {"6f": ("_cache_r6f", "r6f", V86), "70": ("_cache_r70", "r70", V86B)}
RNG = np.random.default_rng(20260808)

# 🛑 the five PHYSICAL bins. The wire CODE for the two small bins differs between the builds
# 🛑 (V86 0x58/0xD8, V86B 0x38/0xB8) but the BIN is the same predicate ⇒ cross-route comparison of
# 🛑 the BINS is legitimate; comparison of the raw codes is not.
BINS = ("big_neg", "small_neg", "zero", "small_pos", "big_pos")


def decode_route(tag):
    """Return the per-frame physical state, re-derived from raw byte4 via the BUILDER's decoder."""
    cdir, stem, MOD = ROUTES[tag]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = (z["probe"].astype(int) & 0xFF)          # the row grid: synchronous with every channel below
    dec = [MOD.decode_byte4(int(v)) for v in b4]
    assert all(d is not None for d in dec), "fingerprint clear on some frame"
    sign = np.array([d["sign"] for d in dec])
    nz = np.array([d["nonzero"] for d in dec])
    mag = np.array([d["mag"] for d in dec])
    gate = np.array([d["gate"] for d in dec])
    # ---- the two EXACT laws, re-checked here rather than trusted ----
    viol = int((sign & ~nz).sum()) + int((mag & ~nz).sum())
    assert viol == 0, f"{viol} nesting violations ⇒ this is not a {tag} log for {MOD.__name__}"
    # L in {-2,-1,0,+1,+2}:  -2 = v<=-65, -1 = -64..-1, 0 = v==0, +1 = 1..63, +2 = v>=+64
    L = np.zeros(len(b4), int)
    L[nz & ~sign & ~mag] = 1
    L[nz & ~sign & mag] = 2
    L[nz & sign & ~mag] = -1
    L[nz & sign & mag] = -2
    return z, b4, L, gate


# =====================================================================================================
# 1.  RELAY vs LINEAR  --  the big-sign-change gap statistic, and its null
# =====================================================================================================
def gap_stats(x, thr):
    """Big-band sign changes of `x` at level `thr`, and the SMALL-BAND GAP at each one.

    B = +1 where x >= thr, -1 where x <= -thr, 0 in the band. For every adjacent pair of opposite
    non-zero B values the GAP is the number of in-band frames strictly between them, i.e. the number
    of 100 Hz samples the signal spent inside (-thr, +thr) while changing sign.
      gap == 0  ⇒ the signal went from >= +thr to <= -thr in ONE sample: DISCONTINUOUS at 100 Hz.
    """
    B = np.zeros(len(x), np.int8)
    B[x >= thr] = 1
    B[x <= -thr] = -1
    idx = np.flatnonzero(B)
    if len(idx) < 2:
        return dict(n_events=0)
    bb, ii = B[idx], idx
    flip = np.flatnonzero(bb[:-1] != bb[1:])
    if not len(flip):
        return dict(n_events=0)
    gaps = ii[flip + 1] - ii[flip] - 1
    return dict(n_events=int(len(gaps)), frac_disc=float((gaps == 0).mean()),
                mean_gap=float(gaps.mean()), median_gap=float(np.median(gaps)),
                p90_gap=float(np.percentile(gaps, 90)),
                band_duty=float((B == 0).mean()), gaps=gaps)


def match_thr(x, target_mean_gap, lo=1e-9, hi=None):
    """Bisect `thr` so that a CONTINUOUS surrogate has the SAME mean small-band gap as the probe.

    ★ This is the whole null. Matching the mean gap holds the ONE quantity that trivially couples
    band-duty to crossing-rate, so what is left to compare -- P(gap == 0) -- is purely 'does it jump'.
    """
    hi = hi if hi is not None else float(np.nanmax(np.abs(x))) * 0.999
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        s = gap_stats(x, mid)
        g = s.get("mean_gap", 0.0) if s["n_events"] else 0.0
        if g < target_mean_gap:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def relay_section(tag, z, L):
    v_big_sign = np.where(np.abs(L) == 2, np.sign(L), 0).astype(float)  # +-1 on big, 0 in band
    probe_gaps = gap_stats(np.where(np.abs(L) == 2, np.sign(L) * 1000.0, np.sign(L) * 1.0), 500.0)
    out = {"probe": {k: v for k, v in probe_gaps.items() if k != "gaps"}}

    # ---- THE NULL: real, continuous, SAME-LOG, SAME-SAMPLE-TIMES signals ----
    surr = {}
    for name in ("rate_c", "tq", "rate_f", "ang", "cs_tq", "cs_rate", "e4tq"):
        if name not in z.files:
            continue
        x = np.asarray(z[name], float)
        if not np.isfinite(x).all() or np.nanstd(x) == 0:
            continue
        x = x - np.median(x)                       # a d.c. offset would fake 'never crosses'
        thr = match_thr(x, probe_gaps["mean_gap"])
        s = gap_stats(x, thr)
        if s["n_events"] < 30:
            continue
        surr[name] = dict(thr=float(thr), thr_over_rms=float(thr / np.std(x)),
                          n_events=s["n_events"], frac_disc=s["frac_disc"],
                          mean_gap=s["mean_gap"], median_gap=s["median_gap"],
                          band_duty=s["band_duty"])
    out["null_linear_surrogates"] = surr

    # ---- POSITIVE CONTROL: a HARD relay driven by the same real signals ----
    pos = {}
    for name in ("rate_c", "tq"):
        if name not in z.files:
            continue
        u = np.asarray(z[name], float)
        u = u - np.median(u)
        r = np.sign(u) * 1000.0                    # memoryless HARD relay, zero boundary layer
        s = gap_stats(r, 500.0)
        pos[f"relay({name})"] = dict(n_events=s["n_events"], frac_disc=s.get("frac_disc"),
                                     mean_gap=s.get("mean_gap"), band_duty=s.get("band_duty"))
    out["positive_control_hard_relay"] = pos

    # ---- the STRUCTURAL LIMIT, computed rather than asserted: a memoryless monotone f() applied to
    # ---- a continuous u only RELABELS the threshold. Demonstrate it on this log's own data.
    if "rate_c" in z.files:
        u = np.asarray(z["rate_c"], float) - np.median(z["rate_c"])
        thr_lin = match_thr(u, probe_gaps["mean_gap"])
        g_lin = gap_stats(u, thr_lin)
        # f(u) = 1000*sign(u)*|u/su|**0.25 -- strongly relay-SHAPED but still memoryless & monotone
        su = np.std(u) or 1.0
        f = 1000.0 * np.sign(u) * np.abs(u / su) ** 0.25
        thr_nl = match_thr(f, probe_gaps["mean_gap"])
        g_nl = gap_stats(f, thr_nl)
        out["memoryless_relabel_demo"] = dict(
            linear=dict(thr=float(thr_lin), frac_disc=g_lin["frac_disc"],
                        mean_gap=g_lin["mean_gap"], n_events=g_lin["n_events"]),
            compressive_p0p25=dict(thr=float(thr_nl), frac_disc=g_nl["frac_disc"],
                                   mean_gap=g_nl["mean_gap"], n_events=g_nl["n_events"]),
            note="matched mean gap ⇒ IDENTICAL frac_disc: a memoryless nonlinearity is INVISIBLE "
                 "to a single-threshold probe. This is a proof, not an opinion.")
    return out


# =====================================================================================================
# 2.  SPECTRUM of the reconstructed 1.5-bit waveform
# =====================================================================================================
def zoh_uniform(t, y, fs=100.0):
    grid = np.arange(t[0], t[-1], 1.0 / fs)
    k = np.searchsorted(t, grid, side="right") - 1
    return grid, y[np.clip(k, 0, len(y) - 1)]


def welch(x, fs, nper=1024):
    x = np.asarray(x, float)
    x = x - x.mean()
    step = nper // 2
    win = np.hanning(nper)
    segs = [x[i:i + nper] * win for i in range(0, len(x) - nper + 1, step)]
    if not segs:
        return np.array([]), np.array([])
    P = np.mean([np.abs(np.fft.rfft(s)) ** 2 for s in segs], axis=0)
    P /= (fs * (win ** 2).sum())
    return np.fft.rfftfreq(nper, 1 / fs), P


def run_order_surrogate(L):
    """Preserve the exact multiset of (level, run-length) pairs; destroy their ORDER.

    ⇒ marginal, run-length distribution and therefore the broadband envelope survive; any PERIODIC
    ordering does not. The right null for a heavily quantised series.
    """
    br = np.flatnonzero(np.diff(L)) + 1
    runs = np.split(L, br)
    order = RNG.permutation(len(runs))
    return np.concatenate([runs[i] for i in order])


def spectrum_section(tag, z, L, n_surr=200):
    t = np.asarray(z["t"], float)
    fs = 100.0
    out = {"fs_hz": fs, "note": "ZOH onto an exact 100 Hz grid from the real 0x14A arrival times"}
    _, Lg = zoh_uniform(t, L.astype(float), fs)
    f, P = welch(Lg, fs, 1024)
    # surrogate envelope
    S = np.empty((n_surr, len(P)))
    for i in range(n_surr):
        _, sg = zoh_uniform(t, run_order_surrogate(L).astype(float), fs)
        m = min(len(sg), len(Lg))
        _, ps = welch(sg[:m], fs, 1024)
        S[i, :len(ps)] = ps
    p95 = np.percentile(S, 95, axis=0)
    p50 = np.percentile(S, 50, axis=0)
    excess = P / np.maximum(p50, 1e-30)
    out["resolution_hz"] = float(f[1] - f[0])
    # the four bands the kit cares about
    bands = {"ratchet_7.79": (6.5, 9.5), "grind1_18_22": (18, 22), "limit_cycle_27.75": (26, 30),
             "lanechange_40_49": (40, 49)}
    bb = {}
    for name, (a, b) in bands.items():
        m = (f >= a) & (f <= b)
        if not m.any():
            continue
        j = np.argmax(P[m])
        fj = f[m][j]
        bb[name] = dict(peak_hz=float(fj), psd=float(P[m][j]),
                        surr_p95=float(p95[m][j]), excess_over_surr_median=float(excess[m][j]),
                        significant=bool(P[m][j] > p95[m][j]))
    out["bands"] = bb
    # the ten largest lines overall, with their surrogate significance
    ordr = np.argsort(P)[::-1]
    top = []
    for j in ordr[:400]:
        if f[j] < 0.4:
            continue
        top.append(dict(hz=float(f[j]), psd=float(P[j]), surr_p95=float(p95[j]),
                        excess=float(excess[j]), significant=bool(P[j] > p95[j])))
        if len(top) >= 12:
            break
    out["top_lines"] = top
    # reference: the same bands in the CONTINUOUS channels of the same log
    ref = {}
    for name in ("rate_c", "tq", "ang", "rate_f"):
        if name not in z.files:
            continue
        _, xg = zoh_uniform(t, np.asarray(z[name], float), fs)
        fr, Pr = welch(xg, fs, 1024)
        d = {}
        for bn, (a, b) in bands.items():
            m = (fr >= a) & (fr <= b)
            j = np.argmax(Pr[m])
            d[bn] = dict(peak_hz=float(fr[m][j]), psd=float(Pr[m][j]))
        ref[name] = d
    out["reference_channels"] = ref
    out["freq"] = f.tolist()
    out["psd"] = P.tolist()
    out["surr_p95"] = p95.tolist()
    return out


# =====================================================================================================
# 4.  exposure-controlled route comparison, and the Y[0] / clamp bounds
# =====================================================================================================
def strat_ratio(L, lat, v, vbins=(0, 1, 2, 3, 4, 99)):
    """mag/nonzero, stratified on (engagement x speed bin). Returns per-cell and cell weights."""
    nz = L != 0
    mg = np.abs(L) == 2
    cells = {}
    for e in (0, 1):
        for i in range(len(vbins) - 1):
            m = (lat == e) & (v >= vbins[i]) & (v < vbins[i + 1])
            if m.sum() < 100:
                continue
            n = int(nz[m].sum())
            cells[f"eng{e}_v{vbins[i]}-{vbins[i + 1]}"] = dict(
                n=int(m.sum()), nonzero=float(nz[m].mean()),
                mag=float(mg[m].mean()), mag_over_nonzero=float(mg[m].sum() / n) if n else None)
    return cells


def block_bootstrap(mask_num, mask_den, block, n=2000):
    """Block bootstrap of num/den over contiguous blocks (episode-scale, never single windows)."""
    nb = len(mask_num) // block
    if nb < 4:
        return None
    num = mask_num[:nb * block].reshape(nb, block).sum(1)
    den = mask_den[:nb * block].reshape(nb, block).sum(1)
    out = []
    for _ in range(n):
        k = RNG.integers(0, nb, nb)
        d = den[k].sum()
        out.append(num[k].sum() / d if d else np.nan)
    out = np.array(out, float)
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]


def analyse(tag):
    cdir, stem, MOD = ROUTES[tag]
    z, b4, L, gate = decode_route(tag)
    t = np.asarray(z["t"], float)
    lat = (np.asarray(z["cc_lat"], float) > 0.5).astype(int)
    v = np.asarray(z["cs_v"], float) * 3.6              # km/h
    n = len(L)
    nz, mg = (L != 0), (np.abs(L) == 2)

    res = {"route": tag, "build": MOD.__name__.replace("build_", "").replace("_tva", "").upper(),
           "frames": int(n), "duration_s": float(t[-1] - t[0]),
           "MAG_T": int(MOD.RELAY_T), "GATE_T": int(MOD.GATE_T),
           "clamp_0xC6200": 8192}
    res["bin_counts"] = {b: int(c) for b, c in
                         zip(BINS, [int((L == k).sum()) for k in (-2, -1, 0, 1, 2)])}
    res["bin_frac"] = {b: c / n for b, c in res["bin_counts"].items()}

    # ---- 1. RELAY vs LINEAR ----
    res["relay_vs_linear"] = relay_section(tag, z, L)

    # ---- 2. SPECTRUM ----
    sp = spectrum_section(tag, z, L)
    res["spectrum"] = {k: v2 for k, v2 in sp.items() if k not in ("freq", "psd", "surr_p95")}
    np.savez_compressed(ROOT / cdir / f"{stem}_probe_psd.npz",
                        freq=np.array(sp["freq"]), psd=np.array(sp["psd"]),
                        surr_p95=np.array(sp["surr_p95"]))

    # ---- 3. THE GATE ----
    res["gate_b4"] = dict(duty=float(gate.mean()), frames_clear=int((~gate).sum()),
                          frames=int(n),
                          predicate="gp-0x67ab < 2  (the aggregator optional-term gate byte)",
                          positive_control_available=False,
                          limitation="a stuck-1 read, a mis-targeted load or a cell that is simply "
                                     "never written would ALL read 1.0000. This rung establishes "
                                     "'the gate was not observed shut', NOT 'the load is correct'.")

    # ---- 4. engaged/manual, exposure, bounds ----
    em = {}
    for name, m in (("engaged", lat == 1), ("manual", lat == 0)):
        if m.sum() < 200:
            continue
        em[name] = dict(frames=int(m.sum()), frac=float(m.mean()),
                        nonzero=float(nz[m].mean()), mag=float(mg[m].mean()),
                        mag_over_nonzero=float(mg[m].sum() / nz[m].sum()),
                        sign_neg=float((L[m] < 0).mean()),
                        v_mean=float(np.nanmean(v[m])), v_med=float(np.nanmedian(v[m])))
    res["engaged_vs_manual"] = em
    res["strata"] = strat_ratio(L, lat, v)
    res["mag_over_nonzero"] = float(mg.sum() / nz.sum())
    res["mag_over_nonzero_ci95_block500"] = block_bootstrap(mg.astype(int), nz.astype(int), 500)
    res["sign_neg_duty"] = float((L < 0).mean())
    res["sign_neg_ci95_block500"] = block_bootstrap((L < 0).astype(int), np.ones(n, int), 500)
    res["speed_kmh"] = dict(mean=float(np.nanmean(v)), med=float(np.nanmedian(v)),
                            p90=float(np.nanpercentile(v, 90)), max=float(np.nanmax(v)))
    res["exposure"] = dict(engaged_frac=float(lat.mean()))

    # ---- Y[0] and clamp bounds ----
    small = int(((np.abs(L) == 1)).sum())
    res["lerp_Y0_bound"] = dict(
        small_band_frames=small, small_band_frac=small / n,
        conclusion=("Y[0] < 64 (STRICT): |gp-0x6b70| was observed inside [1,63] on "
                    f"{small:,} frames, which is UNREACHABLE if the LERP's floor were >= 64."),
        cannot_conclude="the probe has ONE threshold (64) and no rung below it, so Y[0] cannot be "
                        "separated from 0 anywhere in [0,63]. Do NOT quote a value.",
        clamp="b5 tests >= 64 only. Nothing here bounds |gp-0x6b70| from ABOVE, so whether the "
              "0xC6200 = 8192 clamp is ever reached is UNMEASURED, not 'not reached'.")

    # ---- 5. WHAT DRIVES THE SIGN ----
    res["sign_drivers"] = sign_drivers(z, L)
    return res, z, L, lat, v


# =====================================================================================================
# 5.  what does b7 (the sign) actually track?
# =====================================================================================================
def sign_drivers(z, L, lags=range(-10, 11)):
    s = np.sign(L).astype(float)
    live = s != 0
    out = {}
    for name in ("rate_c", "tq", "rate_f", "ang", "wang", "cs_tq", "cs_rate", "e4tq",
                 "sc_tq", "co_tqcan", "cs_yaw"):
        if name not in z.files:
            continue
        x = np.asarray(z[name], float)
        if not np.isfinite(x).all() or np.nanstd(x) == 0:
            continue
        x = x - np.median(x)
        best = None
        for lag in lags:
            xs = np.roll(x, lag)
            m = live.copy()
            if lag > 0:
                m[:lag] = False
            elif lag < 0:
                m[lag:] = False
            agree = float((np.sign(xs[m]) == s[m]).mean())
            agree = max(agree, 1 - agree)          # sign convention is unknown a priori
            if best is None or agree > best[1]:
                best = (int(lag), agree)
        out[name] = dict(best_lag_frames=best[0], best_lag_ms=best[0] * 10.0,
                         sign_agreement=best[1])
    # ★ static threshold vs SCHMITT (hysteresis) on the best driver -- 1 free parameter each
    if out:
        drv = max(out, key=lambda k: out[k]["sign_agreement"])
        x = np.asarray(z[drv], float)
        x = x - np.median(x)
        lag = out[drv]["best_lag_frames"]
        x = np.roll(x, lag)
        sgn = np.sign(L).astype(int)
        m = sgn != 0
        pol = 1 if (np.sign(x[m]) == sgn[m]).mean() >= 0.5 else -1
        xs, ys = pol * x[m], sgn[m]
        sd = np.std(xs) or 1.0
        stat = min(((np.sign(xs - c) != ys).mean(), float(c))
                   for c in np.linspace(-0.5 * sd, 0.5 * sd, 201))
        hyst = min((schmitt_err(xs, ys, h), float(h))
                   for h in np.linspace(0.0, 1.5 * sd, 151))
        out["_model_comparison"] = dict(
            driver=drv, polarity=int(pol), lag_frames=int(lag),
            static_threshold=dict(err=float(stat[0]), c=stat[1]),
            schmitt_hysteresis=dict(err=float(hyst[0]), h=hyst[1], h_over_sd=float(hyst[1] / sd)),
            verdict=("HYSTERETIC (memory)" if hyst[0] < stat[0] - 0.005 else
                     "no evidence of hysteresis over a static threshold"))
    return out


def schmitt_err(x, y, h):
    o = np.empty(len(x), np.int8)
    cur = 1
    for i, xi in enumerate(x):
        if xi > h:
            cur = 1
        elif xi < -h:
            cur = -1
        o[i] = cur
    return float((o != y).mean())


def main():
    allres = {}
    for tag in ("6f", "70"):
        res, z, L, lat, v = analyse(tag)
        cdir, stem, MOD = ROUTES[tag]
        name = "probe_v86_physics.json" if tag == "6f" else "probe_v86b_physics.json"
        (ROOT / cdir / name).write_text(json.dumps(res, indent=1), encoding="utf-8")
        allres[tag] = res
        print(f"wrote {cdir}/{name}")
    # ---- cross-route, EXPOSURE-CONTROLLED ----
    cross = cross_route(allres)
    (ROOT / "_cache_r6f" / "probe_v86_cross_route.json").write_text(
        json.dumps(cross, indent=1), encoding="utf-8")
    print(json.dumps(cross, indent=1)[:4000])
    return allres


def cross_route(allres):
    """Reweight both routes onto a COMMON (engagement x speed) census before comparing."""
    keys = sorted(set(allres["6f"]["strata"]) & set(allres["70"]["strata"]))
    w = {k: min(allres["6f"]["strata"][k]["n"], allres["70"]["strata"][k]["n"]) for k in keys}
    tot = sum(w.values()) or 1
    out = {"common_cells": keys,
           "note": "weights = per-cell min(n) across routes ⇒ neither route's own exposure drives it"}
    for tag in ("6f", "70"):
        S = allres[tag]["strata"]
        out[f"{tag}_raw_mag_over_nonzero"] = allres[tag]["mag_over_nonzero"]
        out[f"{tag}_raw_ci95"] = allres[tag]["mag_over_nonzero_ci95_block500"]
        out[f"{tag}_std_mag_over_nonzero"] = sum(
            w[k] * S[k]["mag_over_nonzero"] for k in keys) / tot
        out[f"{tag}_std_sign_neg"] = None
        out[f"{tag}_engaged_frac"] = allres[tag]["exposure"]["engaged_frac"]
        out[f"{tag}_speed"] = allres[tag]["speed_kmh"]
    out["raw_delta"] = out["70_raw_mag_over_nonzero"] - out["6f_raw_mag_over_nonzero"]
    out["standardised_delta"] = out["70_std_mag_over_nonzero"] - out["6f_std_mag_over_nonzero"]
    out["per_cell"] = {k: {"6f": allres["6f"]["strata"][k]["mag_over_nonzero"],
                           "70": allres["70"]["strata"][k]["mag_over_nonzero"],
                           "n_6f": allres["6f"]["strata"][k]["n"],
                           "n_70": allres["70"]["strata"][k]["n"]} for k in keys}
    return out


if __name__ == "__main__":
    main()
