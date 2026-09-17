"""Per-route stats for verifying the s1_goal target-proposal finding under the CONFOUND lens.
Processes ONE route at a time (RAM discipline), writes results/<route>.json, then exits.
Computes, per speed bin and per band, per ach_key in {la_act, la_yaw}:
  - band_H gain (segments = usable runs within the speed bin)
  - tercile-by-demand-amplitude relative error (5 s chunks, bandpass model+achieved, RMS ratio)
  - median tracking lag (event_metrics cross-corr on 6 s sliding windows within usable runs)
usage: python route_stats.py <route>
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v282cmp as V

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

SPEED_BINS = {">22": (22, 99), "15-22": (15, 22), "8-15": (8, 15)}
BANDS = {"0.15-0.3": (0.15, 0.3), "0.3-0.6": (0.3, 0.6), "0.6-1.2": (0.6, 1.2)}
ACH_KEYS = ["la_act", "la_yaw", "la_pose"]


def bandpass(x, f1, f2):
    if f1 <= 0:
        f1 = 0.02
    sos = signal.butter(3, [f1, f2], btype="band", fs=V.FS, output="sos")
    return signal.sosfiltfilt(sos, np.nan_to_num(x))


def chunk_tercile_relerr(S, mask, ach_key, band, chunk_s=5.0):
    """Split usable runs into chunk_s windows, bandpass model+achieved, tercile by chunk RMS(model),
    return relative error (rms(y-x)/rms(x)) per tercile."""
    f1, f2 = band
    segs = V.runs(mask, S["t"], min_s=chunk_s)
    chunks = []
    n = int(chunk_s * V.FS)
    for a, b in segs:
        for i in range(a, b - n, n):
            x = S["model"][i:i + n]
            y = S[ach_key][i:i + n]
            if np.any(~np.isfinite(x)) or np.any(~np.isfinite(y)):
                continue
            xb = bandpass(x, f1, f2)
            yb = bandpass(y, f1, f2)
            rx = float(np.sqrt(np.mean(xb ** 2)))
            ry_err = float(np.sqrt(np.mean((yb - xb) ** 2)))
            chunks.append((rx, ry_err))
    if len(chunks) < 6:
        return None
    chunks.sort(key=lambda c: c[0])
    n3 = len(chunks) // 3
    if n3 < 1:
        return None
    terciles = {"low": chunks[:n3], "mid": chunks[n3:2 * n3], "high": chunks[2 * n3:]}
    out = {}
    for name, cs in terciles.items():
        rxs = np.array([c[0] for c in cs])
        res = np.array([c[1] for c in cs])
        # relative error = rms(err) / rms(demand), aggregated (not per-chunk-then-averaged, to avoid div-by-small)
        relerr = float(np.sqrt(np.mean(res ** 2)) / max(np.sqrt(np.mean(rxs ** 2)), 1e-6))
        out[name] = dict(relerr=relerr, n_chunks=len(cs), mean_rx=float(rxs.mean()))
    return out


def route_lag(S, mask, ach_key, win_s=6.0, maxlag_s=0.8):
    """Median cross-corr lag (s) over sliding, non-overlapping win_s windows within usable runs,
    restricted to windows where the model has decent RMS (>0.15 m/s^2) so the lag is well-defined."""
    segs = V.runs(mask, S["t"], min_s=win_s)
    n = int(win_s * V.FS)
    lags = []
    for a, b in segs:
        for i in range(a, b - n, n):
            x = np.nan_to_num(S["model"][i:i + n])
            y = np.nan_to_num(S[ach_key][i:i + n])
            if np.sqrt(np.mean(x ** 2)) < 0.15:
                continue
            em = V.event_metrics({"model": x, ach_key: y}, 0, n, ach_key=ach_key, maxlag_s=maxlag_s)
            lags.append(em["lag"])
    if len(lags) < 4:
        return None
    return dict(median=float(np.median(lags)), n=len(lags), p25=float(np.percentile(lags, 25)),
                p75=float(np.percentile(lags, 75)))


def main(route):
    S = V.load(route)
    meta = S["meta"]
    result = dict(route=route, meta=meta, speed_bins={})
    for spname, (vlo, vhi) in SPEED_BINS.items():
        mask = V.usable(S, vlo, vhi)
        sec = mask.sum() / V.FS
        spres = dict(usable_s=sec, bands={}, lag={})
        if sec < 20:
            result["speed_bins"][spname] = spres
            continue
        segs_by_run = V.runs(mask, S["t"], min_s=2.0)
        for bname, (f1, f2) in BANDS.items():
            bres = {}
            for ach in ACH_KEYS:
                # band_H gain
                hsegs = [(S["model"][a:b], S[ach][a:b]) for a, b in segs_by_run if (b - a) >= 256]
                h = V.band_H(hsegs, f1, f2) if hsegs else None
                terc = chunk_tercile_relerr(S, mask, ach, (f1, f2))
                bres[ach] = dict(H=h, tercile=terc)
            spres["bands"][bname] = bres
        for ach in ACH_KEYS:
            spres["lag"][ach] = route_lag(S, mask, ach)
        result["speed_bins"][spname] = spres
    outp = OUT / f"{route}.json"
    outp.write_text(json.dumps(result, indent=1, default=lambda o: None))
    print(f"wrote {outp}")


if __name__ == "__main__":
    main(sys.argv[1])
