#!/usr/bin/env python3
"""locate_grind2_demos.py -- find the grind #2 demonstration bursts on routes 3a / 3b.

Grind #2's reported signature: low speed while the DRIVER commands significant wheel turn,
regardless of LKAS engagement, "vibrates the whole car like a subwoofer".

⚠ ALIASING. The probe grid is ~100 Hz, so the 30-49 Hz band is the top half of the Nyquist
interval and any real content above 50 Hz folds into it. Every band figure here is a statement
about the SAMPLED signal, not a claim about a physical frequency.

Writes the per-window tables' companions: `<tag>_bursts.json` (contiguous burst extents) and
`<tag>_phase.json` (the parking-lot / road / highway split).

Usage:  python locate_grind2_demos.py r3a r3b
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from analyse_v65_routes import band_env, segs  # noqa: E402


def burst_detail(tag, S, lo, hi, thresh_mult=6.0, minlen=0.15):
    """Contiguous runs where the band envelope exceeds `thresh_mult` x the route median."""
    env, meta = {}, {}
    allv = []
    for s, d in S:
        fs = 1.0 / np.median(np.diff(d["t"]))
        e = band_env(d["tq"], fs, lo, hi)
        env[s] = e
        meta[s] = (d, fs)
        allv.append(e)
    med = float(np.median(np.concatenate(allv)))
    thr = thresh_mult * med
    rows = []
    for s, (d, fs) in meta.items():
        m = env[s] > thr
        if not m.any():
            continue
        idx = np.flatnonzero(m)
        for r in np.split(idx, np.flatnonzero(np.diff(idx) > int(0.10 * fs)) + 1):
            if len(r) < minlen * fs:
                continue
            sl = slice(r[0], r[-1] + 1)
            seg_t = d["t"][r[0]]
            # dominant frequency inside the burst, on the band-limited torsion-bar channel
            x = d["tq"][sl] - d["tq"][sl].mean()
            if len(x) >= 16:
                P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
                f = np.fft.rfftfreq(len(x), 1 / fs)
                k = (f >= lo) & (f <= hi)
                fpk = float(f[k][np.argmax(P[k])]) if k.any() else float("nan")
            else:
                fpk = float("nan")
            rows.append(dict(
                seg=int(s), t=float(seg_t), t_end=float(d["t"][r[-1]]),
                dur=float((r[-1] - r[0] + 1) / fs),
                wall=float(d["wall_t0"][0]) + float(seg_t),
                env_p99=float(np.percentile(env[s][sl], 99)), env_max=float(env[s][sl].max()),
                f_peak=fpk,
                v=float(np.median(d["cs_v"][sl])),
                absang=float(np.abs(d["ang"][sl]).max()),
                rate_c=float(np.abs(d["rate_c"][sl]).max()),
                tq_avg=float(np.abs(d["tq"][sl]).mean()), tq_max=float(np.abs(d["tq"][sl]).max()),
                lat=float((d["cc_lat"][sl] > 0.5).mean()),
                nonneutral=int((d["prail"][sl] + d["phalf"][sl] + d["nhalf"][sl]
                                + d["nrail"][sl] > 0).sum()),
            ))
    rows.sort(key=lambda q: -q["env_max"])
    print(f"\n-- {tag.upper()} {lo:.0f}-{hi:.0f} Hz BURSTS  (env > {thresh_mult:.0f}x route median "
          f"{med:.2f} = {thr:.1f}, min {minlen * 1000:.0f} ms) : {len(rows)} bursts --")
    print(f"   {'seg':>3s} {'t':>7s} {'dur':>6s} {'wall':>9s} {'envmax':>8s} {'f_pk':>6s} "
          f"{'vEgo':>5s} {'|ang|':>6s} {'rate':>6s} {'|tq|av':>7s} {'|tq|mx':>7s} {'lat':>5s} {'nn':>3s}")
    for r in rows[:25]:
        print(f"   {r['seg']:3d} {r['t']:6.2f}s {r['dur']:5.2f}s "
              f"{time.strftime('%H:%M:%S', time.localtime(r['wall'])):>9s} {r['env_max']:8.1f} "
              f"{r['f_peak']:6.1f} {r['v']:5.2f} {r['absang']:6.1f} {r['rate_c']:6.1f} "
              f"{r['tq_avg']:7.0f} {r['tq_max']:7.0f} {r['lat']:5.2f} {r['nonneutral']:3d}")
    return rows, med, thr


def phases(tag, S, bin_s=5.0):
    """Coarse speed timeline -> where the parking lot ends and the road/highway begins."""
    print(f"\n-- {tag.upper()} SPEED TIMELINE ({bin_s:.0f} s bins; 'x' = >14 m/s, '=' = 6-14, "
          f"'-' = 2-6, '.' = <2) --")
    out = []
    for s, d in S:
        fs = 1.0 / np.median(np.diff(d["t"]))
        n = int(bin_s * fs)
        line, w0 = "", float(d["wall_t0"][0])
        for i in range(0, len(d["t"]) - 1, n):
            v = float(np.median(d["cs_v"][i:i + n]))
            line += "x" if v > 14 else ("=" if v > 6 else ("-" if v > 2 else "."))
            out.append(dict(seg=int(s), t=float(d["t"][i]), wall=w0 + float(d["t"][i]),
                            v=v, lat=float((d["cc_lat"][i:i + n] > 0.5).mean())))
        latd = 100 * (d["cc_lat"] > 0.5).mean()
        rev = int((d["cs_gear"] == 4).sum())
        print(f"   seg {s:2d} {time.strftime('%H:%M:%S', time.localtime(w0))} |{line}|  "
              f"vmed {np.median(d['cs_v']):5.2f} vmax {d['cs_v'].max():5.2f}  lat {latd:5.1f}%"
              + (f"  REVERSE {rev} fr" if rev else ""))
    return out


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["r3a", "r3b"]):
        S = segs(tag)
        print(f"\n{'=' * 104}\n== {tag.upper()}\n{'=' * 104}")
        ph = phases(tag, S)
        hi, _, _ = burst_detail(tag, S, 30.0, 49.0)
        lo, _, _ = burst_detail(tag, S, 18.0, 26.0)
        (ROOT / f"_cache_{tag}" / f"{tag}_bursts.json").write_text(
            json.dumps({"band_30_49": hi, "band_18_26": lo}))
        (ROOT / f"_cache_{tag}" / f"{tag}_phase.json").write_text(json.dumps(ph))
        print(f"\n   -> _cache_{tag}/{tag}_bursts.json, _cache_{tag}/{tag}_phase.json")
