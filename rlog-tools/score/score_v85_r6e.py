#!/usr/bin/env python3
"""Route `6e` / V85: BUILD IDENTITY, flight CENSUS + fault check, and the V85 PROBE DECODE.

Reads `_scratch/cache/r6e/r6e.npz` (written by `decode/extract_r6e.py`, which drives the corpus's own
`compare_v75_v76_v80_grind.extract66` verbatim).  The probe semantics are NOT reimplemented --
`decode_v85_probe.classify_log` is imported and is the thing that grants or refuses the decode.

Usage:
    python score/score_v85_r6e.py            # everything, to stdout + json into _scratch/cache/r6e/
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

from decode_v85_probe import NotV85, classify_log, model_threshold, report  # noqa: E402
from build_v85_tva import (BIT_FINGERPRINT, BIT_FRIC_HI, BIT_FRIC_LO, BIT_RATE_HI,  # noqa: E402
                           BIT_RATE_LO, FRIC_T_HI, FRIC_T_LO, NEW_SAT, OLD_SAT,
                           RATE_COUNTS_PER_DEG_S, RATE_T_HI, RATE_T_LO)

CACHE = ROOT / "_scratch/cache/r6e"
KMH = 3.6
SENTINEL_ANG = -3276.7            # 0x14A bytes 0:1 == 0x7FFF, after the extractor's *-0.1
SENTINEL_TQ = -32767.0            # 0x18F bytes 0:1 == 0x7FFF, after the extractor's *-1.0
# V84's OWN field alphabet on route 6d, quoted from `_scratch/cache/r6d/identity.json` -- the discriminator
V84_R6D_ALPHABET = {0x28, 0x38}


def _q(x, qs=(0, 5, 25, 50, 75, 95, 100)):
    return {f"p{q}": float(np.percentile(x, q)) for q in qs}


def main():
    z = np.load(CACHE / "r6e.npz")
    p = z["probe"].astype(int)
    t = z["t"]
    lat = z["cc_lat"] > 0.5
    v = np.abs(z["cs_v"])
    n = len(p)
    dt = 0.01                                   # the 0x14A frame period; 100 Hz packer

    out = {}

    # ==========================================================================================
    # 1.  IDENTITY -- parameter-free
    # ==========================================================================================
    print("=" * 96)
    print("1.  BUILD IDENTITY -- route 6e")
    print("=" * 96)
    vals, cnts = np.unique(p, return_counts=True)
    print(f"  raw 0x14A byte4 alphabet ({len(vals)} distinct over {n:,} frames):")
    for a, c in zip(vals, cnts):
        print(f"    0x{a:02X}  {c:7,d}  {100 * c / n:6.3f}%   "
              f"b7={int(bool(a & 0x80))} b6={int(bool(a & 0x40))} b5={int(bool(a & 0x20))} "
              f"b4={int(bool(a & 0x10))} b3={int(bool(a & 0x08))}  status={a & 0x07}")
    field = p & 0xF8
    duties = {f"b{b}": float(np.mean((p >> b) & 1)) for b in (7, 6, 5, 4, 3)}
    viol_rate = int(np.sum(((p & BIT_RATE_HI) != 0) & ((p & BIT_RATE_LO) == 0)))
    viol_fric = int(np.sum(((p & BIT_FRIC_HI) != 0) & ((p & BIT_FRIC_LO) == 0)))
    outside_v84 = int(np.sum(~np.isin(field, list(V84_R6D_ALPHABET))))
    print(f"\n  per-bit duty: " + "  ".join(f"{k} {d:.5f}" for k, d in duties.items()))
    print(f"  NESTING b6=>b7 violations : {viol_rate}  (structurally EXACT on V85; any >0 voids "
          f"the decode)")
    print(f"  NESTING b5=>b4 violations : {viol_fric}  (structurally EXACT on V85)")
    print(f"  frames with b7 set        : {int(np.sum((p & BIT_RATE_LO) != 0)):,}  "
          f"-- V84 had 0/68,236 on route 6d")
    print(f"  frames OUTSIDE V84's route-6d field alphabet {{0x28,0x38}}: {outside_v84:,} "
          f"({100 * outside_v84 / n:.3f}%)")
    fp_clear = int(np.sum((p & BIT_FINGERPRINT) == 0))
    print(f"  fingerprint b3 CLEAR frames: {fp_clear}")

    verdict = ("V85" if (fp_clear == 0 and viol_rate == 0 and viol_fric == 0
                         and duties["b7"] > 0.01) else "NOT-V85")
    print(f"\n  ==> VERDICT: {verdict}")
    out["identity"] = dict(route="6e", frames=n, alphabet={f"0x{a:02X}": int(c)
                                                           for a, c in zip(vals, cnts)},
                           field_hist={f"0x{a:02X}": int(c) for a, c in
                                       zip(*np.unique(field, return_counts=True))},
                           duties=duties, viol_b6_not_b7=viol_rate, viol_b5_not_b4=viol_fric,
                           fingerprint_clear=fp_clear, outside_v84_r6d_alphabet=outside_v84,
                           verdict=verdict)

    # ==========================================================================================
    # 2.  CENSUS + FAULT CHECK
    # ==========================================================================================
    print("\n" + "=" * 96)
    print("2.  CENSUS + FAULT CHECK")
    print("=" * 96)
    dur = float(t[-1] - t[0])
    eng_s = float(lat.sum() * dt)
    print(f"  frames {n:,}   wall {dur:.2f} s   engaged {lat.mean():.4f} ({eng_s:.1f} s)")
    print(f"  speed m/s: " + "  ".join(f"{k} {x:.2f}" for k, x in _q(v).items()))
    print(f"  speed km/h: " + "  ".join(f"{k} {x * KMH:.1f}" for k, x in _q(v).items()))
    for thr in (30, 50, 65, 80, 90, 100):
        m = v * KMH >= thr
        print(f"    >= {thr:3d} km/h: total {m.sum() * dt:7.1f} s   ENGAGED "
              f"{(m & lat).sum() * dt:7.1f} s")
        out.setdefault("exposure_s", {})[f"ge{thr}kmh"] = dict(
            total=float(m.sum() * dt), engaged=float((m & lat).sum() * dt))
    # engagement episodes
    d_lat = np.diff(lat.astype(int))
    starts = np.where(d_lat == 1)[0] + 1
    ends = np.where(d_lat == -1)[0] + 1
    if lat[0]:
        starts = np.r_[0, starts]
    if lat[-1]:
        ends = np.r_[ends, n]
    ep = (t[np.minimum(ends, n - 1)] - t[starts])
    print(f"  engagement episodes: {len(ep)} total, {int((ep >= 2.0).sum())} >= 2 s, "
          f"longest {ep.max() if len(ep) else 0:.2f} s")

    sst = z["sstat"].astype(int)
    su, sc = np.unique(sst, return_counts=True)
    print(f"  STEER_STATUS (0x18F byte4 nibble 7:4): "
          f"{{{', '.join(f'{int(a)}: {int(c):,}' for a, c in zip(su, sc))}}}")
    b0 = z["raw1ab_b0"].astype(int)
    dtc = (b0 >> 2) & 1
    print(f"  0x1AB frames {len(b0):,}   DTC-active (b0 bit2) frames {int(dtc.sum())}   "
          f"transitions {int(np.abs(np.diff(dtc)).sum()) if len(dtc) else 0}")
    print(f"  0x1AB byte0 hist: " +
          " ".join(f"0x{int(a):02X}:{int(c):,}" for a, c in zip(*np.unique(b0,
                                                                          return_counts=True))))
    s14 = int(np.sum(np.isclose(z["ang"], SENTINEL_ANG)))
    s18 = int(np.sum(np.isclose(z["tq"], SENTINEL_TQ)))
    print(f"  0x7FFF sentinels: 0x14A {s14}   0x18F {s18}")
    out["health"] = dict(route="6e", frames=n, duration_s=dur, engaged_frac=float(lat.mean()),
                         engaged_s=eng_s, episodes_total=int(len(ep)),
                         episodes_ge_2s=int((ep >= 2.0).sum()),
                         longest_episode_s=float(ep.max()) if len(ep) else 0.0,
                         v_min=float(v.min()), v_max=float(v.max()), v_mean=float(v.mean()),
                         v_quantiles_ms=_q(v),
                         steer_status_hist={int(a): int(c) for a, c in zip(su, sc)},
                         dtc_frames=int(len(b0)), dtc_active_frames=int(dtc.sum()),
                         dtc_transitions=int(np.abs(np.diff(dtc)).sum()) if len(dtc) else 0,
                         sentinel_14A=s14, sentinel_18F=s18,
                         truncated_segment="seg 7 rlog torn mid-message; 32,695 complete "
                                           "messages recovered, 16.7 s of data, 0 s engaged")

    # ---- per-window speed census (4 s windows), so a moving wheel order cannot masquerade ------
    W = int(4.0 / dt)
    nw = n // W
    rows = []
    for i in range(nw):
        s = slice(i * W, (i + 1) * W)
        rows.append((float(t[s][0]), float(v[s].mean() * KMH), float(v[s].min() * KMH),
                     float(v[s].max() * KMH), float(lat[s].mean())))
    W_ARR = np.array(rows, float)
    eng_w = W_ARR[W_ARR[:, 4] > 0.9]
    print(f"\n  per-window census: {nw} windows of 4.00 s; {len(eng_w)} fully-engaged (>90%)")
    edges = [0, 10, 20, 30, 40, 50, 65, 80, 95, 200]
    print("    engaged-window mean-speed histogram (km/h):")
    for a, b in zip(edges[:-1], edges[1:]):
        c = int(np.sum((eng_w[:, 1] >= a) & (eng_w[:, 1] < b)))
        print(f"      {a:3d}-{b:3d}: {c:4d} windows ({c * 4.0:6.1f} s)  " + "#" * min(c, 60))
    out["window_census"] = dict(window_s=4.0, n_windows=nw, n_engaged_windows=int(len(eng_w)),
                                engaged_speed_hist_kmh={f"{a}-{b}": int(np.sum(
                                    (eng_w[:, 1] >= a) & (eng_w[:, 1] < b)))
                                    for a, b in zip(edges[:-1], edges[1:])},
                                engaged_window_speed_spread_kmh=float(
                                    np.median(eng_w[:, 3] - eng_w[:, 2])) if len(eng_w) else None)

    # ==========================================================================================
    # 3.  THE V85 PROBE DECODE -- via the decoder that can REFUSE
    # ==========================================================================================
    print("\n" + "=" * 96)
    print("3.  V85 PROBE DECODE  (decode_v85_probe.classify_log -- it refuses a non-V85 log)")
    print("=" * 96)
    try:
        res = classify_log(p.tolist(), latactive=lat.tolist())
    except NotV85 as e:
        print(f"  🛑 REFUSED: {e}")
        out["probe"] = {"refused": str(e)}
        (CACHE / "v85_r6e_score.json").write_text(json.dumps(out, indent=1))
        return
    print(report(res))
    out["probe"] = {k: (float(x) if isinstance(x, (int, float, np.floating)) else x)
                    for k, x in res.items()}

    # ---- the same four rungs, stratified -------------------------------------------------------
    print("\n  STRATIFIED DUTIES (rows are disjoint):")
    hdr = f"    {'stratum':<22}{'n':>8}{'b7 rate>=64':>13}{'b6 rate>=512':>14}" \
          f"{'b5 fric>=8':>12}{'b4 fric>=2':>12}"
    print(hdr)
    strata = [("ALL", np.ones(n, bool)), ("engaged", lat), ("manual", ~lat)]
    for a, b in ((0, 2), (2, 5), (5, 10), (10, 20), (20, 30), (30, 100)):
        strata.append((f"eng v {a}-{b} m/s", lat & (v >= a) & (v < b)))
    strat = {}
    for name, m in strata:
        if m.sum() < 50:
            continue
        r = {"n": int(m.sum())}
        for bit, key in ((BIT_RATE_LO, "b7"), (BIT_RATE_HI, "b6"), (BIT_FRIC_HI, "b5"),
                         (BIT_FRIC_LO, "b4")):
            r[key] = float(np.mean((p[m] & bit) != 0))
        strat[name] = r
        print(f"    {name:<22}{r['n']:>8,}{r['b7']:>13.4f}{r['b6']:>14.4f}"
              f"{r['b5']:>12.4f}{r['b4']:>12.4f}")
    out["strata"] = strat

    # ---- IN-FORCE verdict ----------------------------------------------------------------------
    print("\n  IS THE 0xC40BC LEVER IN FORCE?")
    print(f"    b7 |rate| >= {RATE_T_LO} (> OLD sat {OLD_SAT}) duty {res['rate_lo']:.4f}"
          f"  ⇒ V84's relay would have been SATURATED on {100 * res['rate_lo']:.1f}% of frames")
    print(f"    b6 |rate| >= {RATE_T_HI} (> NEW sat {NEW_SAT}) duty {res['rate_hi']:.4f}"
          f"  ⇒ V85's relay is STILL saturated on {100 * res['rate_hi']:.1f}% of frames")
    if res["rate_lo"] > 0:
        print(f"    saturated-fraction reduction b7/b6 = {res['rate_lo'] / max(res['rate_hi'], 1e-12):.2f}x")
    print(f"    PRE-REGISTERED: b4 35-70% -> measured {100 * res['fric_lo']:.2f}%  "
          f"{'HIT' if 0.35 <= res['fric_lo'] <= 0.70 else 'MISS'}")
    print(f"    PRE-REGISTERED: b5 10-25% -> measured {100 * res['fric_hi']:.2f}%  "
          f"{'HIT' if 0.10 <= res['fric_hi'] <= 0.25 else 'MISS'}")
    out["preregistered"] = dict(b4=float(res["fric_lo"]), b4_hit=bool(0.35 <= res["fric_lo"] <= 0.70),
                                b5=float(res["fric_hi"]), b5_hit=bool(0.10 <= res["fric_hi"] <= 0.25),
                                b7=float(res["rate_lo"]), b6=float(res["rate_hi"]),
                                sat_reduction=float(res["rate_lo"] / res["rate_hi"])
                                if res["rate_hi"] else None)

    # ---- |model| bracket, with the margins so a tie is visible ---------------------------------
    print("\n  |model| BRACKET (a RANKING; rate and model are correlated):")
    for (fl, rl, thr_f, thr_r, why) in (
            ("fric_hi", "rate_hi", FRIC_T_HI, RATE_T_HI, "b5 > b6"),
            ("fric_lo", "rate_lo", FRIC_T_LO, RATE_T_LO, "b4 > b7"),
            ("fric_hi", "rate_lo", FRIC_T_HI, RATE_T_LO, "b5 > b7")):
        thr = model_threshold(thr_f, thr_r)
        a, b = res[fl], res[rl]
        print(f"    {why:<8s} |model| > {thr:.3f} : {str(a > b):<5s}  "
              f"({a:.4f} vs {b:.4f}, margin {a - b:+.4f})")

    print(f"\n  scale: {RATE_T_LO} ct = {RATE_T_LO / RATE_COUNTS_PER_DEG_S:.1f} deg/s · "
          f"{RATE_T_HI} ct = {RATE_T_HI / RATE_COUNTS_PER_DEG_S:.1f} deg/s")
    (CACHE / "v85_r6e_score.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {CACHE / 'v85_r6e_score.json'}")


if __name__ == "__main__":
    main()
