#!/usr/bin/env python3
"""studies/telemetry/analyse_v65_routes.py -- flight-clean inventory + V65 ladder decode for routes 3a / 3b.

Reads the .npz caches written by extract/extract_r3a_cache.py / extract/extract_r3b_cache.py. All ladder semantics
are V65's (see those docstrings); the raw byte4 is re-decoded here from `probe`, never from a
pre-baked flag.

Usage:  python studies/telemetry/analyse_v65_routes.py r3a r3b
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
LEGAL = {0xE0: "+RAIL", 0xA0: "+HALF", 0x80: "NEUTRAL", 0x90: "-HALF", 0x98: "-RAIL"}
EVENT_KEYS = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
              "immediateDisable", "steerSaturated"]


def segs(tag):
    """Load the caches. ⚠ A segment logged BEFORE the device's clock synced carries a wall anchor
    that is off by years (wall_off_sd in the millions of seconds). Repair it from a neighbour at the
    known 60 s segment cadence rather than printing a plausible wrong local time."""
    out = []
    # `*_imu.npz` lives in the same directory on its own grid -- exclude it, it is not a CAN segment
    cands = [q for q in (ROOT / f"_cache_{tag}").glob(f"{tag}s*.npz")
             if not q.stem.endswith("_imu")]
    for p in sorted(cands, key=lambda q: int(q.stem.split("s")[-1])):
        out.append((int(p.stem.split("s")[-1]), dict(np.load(p))))
    good = [(s, float(d["wall_t0"][0])) for s, d in out
            if float(d["wall_off_sd"][0]) < 1.0 or not np.isfinite(float(d["wall_off_sd"][0]))]
    for s, d in out:
        sd = float(d["wall_off_sd"][0])
        d["wall_ok"] = np.array([0.0 if (np.isfinite(sd) and sd >= 1.0) else 1.0])
        if np.isfinite(sd) and sd >= 1.0 and good:
            ref_s, ref_w = min(good, key=lambda q: abs(q[0] - s))
            d["wall_t0"] = np.array([ref_w + 60.0 * (s - ref_s)])
    return out


def rate(ts):
    """Message rate from raw arrival timestamps: n / span, plus median inter-arrival."""
    if len(ts) < 2:
        return float("nan"), float("nan")
    return (len(ts) - 1) / (ts[-1] - ts[0]), float(np.median(np.diff(ts)))


def wall(d, off_override=None):
    o = float(d["wall_t0"][0]) if off_override is None else off_override
    return o


def band_env(x, fs, lo, hi):
    """Zero-phase FFT bandpass -> analytic envelope. NaN-guarded (one NaN in => all NaN out)."""
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.zeros_like(x)
    if bad.any():
        good = ~bad
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(good), x[good])
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(n, 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    # analytic signal from the one-sided spectrum: double the kept positive bins
    Z = np.zeros(n, complex)
    Z[:len(X)] = X * 2
    Z[0] = X[0]
    if n % 2 == 0:
        Z[len(X) - 1] = X[-1]
    return np.abs(np.fft.ifft(Z))


def alternations(pos, neg):
    """pos<->neg flips, SKIPPING neutral frames (counting neutral as a state doubles the rate)."""
    seq = []
    for s in np.where(pos, 1, np.where(neg, -1, 0)):
        if s == 0:
            continue
        if not seq or seq[-1] != s:
            seq.append(s)
    return max(0, len(seq) - 1), len(seq)


# =====================================================================================
def inventory(tag, S):
    print(f"\n{'=' * 108}\n== ROUTE {tag.upper()} -- FLIGHT-CLEAN INVENTORY  ({len(S)} segments)\n{'=' * 108}")
    print(f"{'seg':>3s} {'n':>6s} {'dur':>7s} {'fs':>6s} {'wall':>9s} | "
          f"{'vEgo min':>8s} {'med':>6s} {'max':>6s} | {'lat%':>6s} {'sca%':>6s} | "
          f"{'r14A':>6s} {'r18F':>6s} | {'ST=4':>6s} {'ST hist'}")
    tot = {}
    for s, d in S:
        n = len(d["t"])
        dur = d["t"][-1] - d["t"][0]
        fs = 1.0 / np.median(np.diff(d["t"]))
        r14, _ = rate(d["raw14A"])
        r18, _ = rate(d["raw18F"])
        st = Counter(d["sstat"].astype(int).tolist())
        w = (time.strftime("%H:%M:%S", time.localtime(float(d["wall_t0"][0])))
             + ("" if d["wall_ok"][0] else "*"))
        sthist = " ".join(f"{k}:{v}" for k, v in sorted(st.items()))
        print(f"{s:3d} {n:6d} {dur:6.2f}s {fs:6.2f} {w:>9s} | "
              f"{d['cs_v'].min():8.2f} {np.median(d['cs_v']):6.2f} {d['cs_v'].max():6.2f} | "
              f"{100 * (d['cc_lat'] > 0.5).mean():5.1f}% {100 * (d['sca'] == 1).mean():5.1f}% | "
              f"{r14:6.2f} {r18:6.2f} | {st.get(4, 0):6d} {sthist}")
        for k, v in st.items():
            tot[k] = tot.get(k, 0) + v
    print(f"    route STEER_STATUS totals: " + "  ".join(f"{k}:{v}" for k, v in sorted(tot.items()))
          + f"     ST==4 total = {tot.get(4, 0)}")

    print(f"\n-- GEARS (frames on the 100 Hz probe grid) --")
    print(f"{'seg':>3s} " + " ".join(f"{g:>9s}" for g in GEAR[:6]))
    gt = {}
    for s, d in S:
        c = Counter(d["cs_gear"].astype(int).tolist())
        print(f"{s:3d} " + " ".join(f"{c.get(i, 0):9d}" for i in range(6)))
        for k, v in c.items():
            gt[k] = gt.get(k, 0) + v
    print(f"tot " + " ".join(f"{gt.get(i, 0):9d}" for i in range(6)))

    print(f"\n-- onroadEvents --")
    print(f"{'seg':>3s} " + " ".join(f"{k:>21s}" for k in EVENT_KEYS) + f" {'other':>7s}")
    et = {k: 0 for k in EVENT_KEYS}
    allnames = Counter()
    for s, _ in S:
        ev = json.loads((ROOT / f"_cache_{tag}" / f"{tag}s{s}_events.json").read_text())
        c = Counter(e["name"] for e in ev)
        allnames.update(c)
        print(f"{s:3d} " + " ".join(f"{c.get(k, 0):21d}" for k in EVENT_KEYS)
              + f" {sum(v for k, v in c.items() if k not in EVENT_KEYS):7d}")
        for k in EVENT_KEYS:
            et[k] += c.get(k, 0)
    print(f"tot " + " ".join(f"{et[k]:21d}" for k in EVENT_KEYS))
    print(f"    all event names: {dict(allnames.most_common())}")
    return tot


# =====================================================================================
def ladder(tag, S):
    print(f"\n{'=' * 108}\n== ROUTE {tag.upper()} -- V65 SATURATION LADDER DECODE\n{'=' * 108}")
    p = np.concatenate([d["probe"].astype(int) for _, d in S])
    t = np.concatenate([d["t"] + 1000 * s for s, d in S])      # segment-disjoint time axis
    v = np.concatenate([d["cs_v"] for _, d in S])
    lat = np.concatenate([d["cc_lat"] for _, d in S]) > 0.5
    tq = np.concatenate([d["tq"] for _, d in S])
    n = len(p)

    field = (p >> 3) & 0x1F
    prail, phalf = (p & 0x40) != 0, (p & 0x20) != 0
    nhalf, nrail = (p & 0x10) != 0, (p & 0x08) != 0
    pos, neg = prail | phalf, nhalf | nrail

    print(f"\n-- LIVENESS ({n} frames) --")
    print(f"   field == 0 (CAVE DID NOT FIRE, VOID) : {int((field == 0).sum())} / {n}")
    print(f"   bit7 (liveness) set                  : {int(((p & 0x80) != 0).sum())} / {n}")

    print(f"\n-- THE 3 STRUCTURAL INVARIANTS (any violation => the build on the car is NOT V65) --")
    a = prail & ~phalf
    b = nrail & ~nhalf
    c = pos & neg
    illegal = np.array([(int(x) & 0xF8) not in LEGAL for x in p])
    print(f"   (a) bit6 & ~bit5           : {int(a.sum()):7d} / {n}  ({100 * a.mean():.4f}%)")
    print(f"   (b) bit3 & ~bit4           : {int(b.sum()):7d} / {n}  ({100 * b.mean():.4f}%)")
    print(f"   (c) positive AND negative  : {int(c.sum()):7d} / {n}  ({100 * c.mean():.4f}%)  <- DISCRIMINATOR")
    print(f"       payload not 1 of the 5 : {int(illegal.sum()):7d} / {n}  ({100 * illegal.mean():.4f}%)")

    print(f"\n-- RAW byte4 HISTOGRAM (all values seen) --")
    for val, cnt in sorted(Counter(p.tolist()).items()):
        print(f"   0x{val:02X}  {cnt:8d}  ({100 * cnt / n:7.4f}%)   probe=0x{val & 0xF8:02X} "
              f"[{LEGAL.get(val & 0xF8, '*** ILLEGAL ***')}]  status={val & 0x07}")
    print(f"\n-- PAYLOAD (probe bits, mask 0xF8) HISTOGRAM --")
    for val, cnt in sorted(Counter((p & 0xF8).tolist()).items()):
        print(f"   0x{val:02X}  {cnt:8d}  ({100 * cnt / n:7.4f}%)   {LEGAL.get(val, '*** ILLEGAL ***')}")

    # ⚠ A LITERALLY constant 0x87 is byte-identical to V64's null and cannot be interpreted. What
    # breaks that tie is not the 0x87 fraction but whether ANY other payload ever appears.
    n87 = int((p == 0x87).sum())
    others = sorted(set(p.tolist()) - {0x87})
    print(f"\n   byte4 == 0x87 : {n87} / {n} ({100 * n87 / n:.4f}%);  "
          f"non-0x87 frames: {n - n87};  distinct other values: "
          f"{[f'0x{x:02X}' for x in others] or 'NONE'}")
    if not others:
        print("   🛑 byte4 IS LITERALLY CONSTANT 0x87 -- byte-identical to V64's null. AMBIGUOUS.")
        print("      Under V64 that was 'the detector never armed'; under V65 it is the NEUTRAL")
        print("      bucket. The payload alone cannot separate them. STOP -- confirm the .rwd.")
    else:
        print("   byte4 is NOT constant, so it is not V64's frozen null. The ladder moved.")

    lvl = prail.astype(int) + phalf.astype(int) - nhalf.astype(int) - nrail.astype(int)
    names = [(2, "+RAIL"), (1, "+HALF"), (0, "NEUTRAL"), (-1, "-HALF"), (-2, "-RAIL")]

    def occ(label, sel):
        if sel.sum() == 0:
            print(f"   {label:34s} {0:8d}   (none)")
            return
        row = "  ".join(f"{int((lvl[sel] == k).sum()):7d}" for k, _ in names)
        pct = "  ".join(f"{100 * (lvl[sel] == k).mean():6.3f}%" for k, _ in names)
        print(f"   {label:34s} {int(sel.sum()):8d}  {row}")
        print(f"   {'':34s} {'':8s}  {pct}")

    print(f"\n-- OCCUPANCY BY LEVEL  (counts, then %) --")
    print(f"   {'condition':34s} {'n':>8s}  " + "  ".join(f"{nm:>7s}" for _, nm in names))
    occ("ALL", np.ones(n, bool))
    occ("ENGAGED (latActive)", lat)
    occ("NOT engaged", ~lat)
    print(f"\n-- OCCUPANCY BY SPEED BIN --")
    print(f"   {'condition':34s} {'n':>8s}  " + "  ".join(f"{nm:>7s}" for _, nm in names))
    for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 10), (10, 14), (14, 99)):
        sel = (v >= lo) & (v < hi)
        occ(f"v {lo}-{hi} m/s   ALL", sel)
        occ(f"v {lo}-{hi} m/s   ENGAGED", sel & lat)
        occ(f"v {lo}-{hi} m/s   manual", sel & ~lat)
    print(f"\n-- OCCUPANCY BY DRIVER EFFORT |steeringTorque| (0x18F torsion bar, raw counts) --")
    print(f"   {'condition':34s} {'n':>8s}  " + "  ".join(f"{nm:>7s}" for _, nm in names))
    at = np.abs(tq)
    for lo, hi in ((0, 100), (100, 200), (200, 400), (400, 800), (800, 1e9)):
        occ(f"|tq| {lo:.0f}-{hi:.0f}", (at >= lo) & (at < hi))

    print(f"\n-- ALTERNATION RATE (pos side <-> neg side; neutral skipped) --")
    print(f"   {'condition':34s} {'n':>8s} {'span':>9s} {'RAILalt/s':>10s} {'SIDEalt/s':>10s} "
          f"{'~Hz(side)':>10s} {'visits':>7s}")
    for label, sel in [("ALL", np.ones(n, bool)),
                       ("ENGAGED", lat), ("ENGAGED + creep (v<=5)", lat & (v <= 5)),
                       ("MANUAL", ~lat), ("MANUAL + creep (v<=5)", ~lat & (v <= 5))]:
        if sel.sum() < 2:
            print(f"   {label:34s}  (<2 frames)")
            continue
        ar, _ = alternations(prail[sel], nrail[sel])
        as_, vis = alternations(pos[sel], neg[sel])
        span = t[sel][-1] - t[sel][0]
        # span across concatenated segments is inflated by the 1000 s offsets; use frame count/fs
        span = sel.sum() / 100.0
        print(f"   {label:34s} {int(sel.sum()):8d} {span:8.1f}s {ar / span:10.4f} "
              f"{as_ / span:10.4f} {as_ / span / 2:10.4f} {vis:7d}")

    print(f"\n-- NON-NEUTRAL EPISODES (contiguous runs of level != 0) --")
    nz = lvl != 0
    if not nz.any():
        print("   NONE. The aggregator never left the NEUTRAL bucket on this route.")
        return
    idx = np.flatnonzero(nz)
    brk = np.flatnonzero(np.diff(idx) > 1)
    runs = np.split(idx, brk + 1)
    print(f"   {len(runs)} episodes, {int(nz.sum())} frames total")
    # map concatenated index back to (segment, t)
    bounds, acc = [], 0
    for s, d in S:
        bounds.append((acc, acc + len(d["t"]), s, d))
        acc += len(d["t"])
    print(f"   {'#':>3s} {'seg':>4s} {'t':>8s} {'nfr':>4s} {'dur':>6s} {'lvl':>10s} "
          f"{'vEgo':>6s} {'lat':>4s} {'|tq|max':>8s}")
    for i, r in enumerate(runs):
        i0 = r[0]
        seg, dd, off = None, None, None
        for lo, hi, s, d in bounds:
            if lo <= i0 < hi:
                seg, dd, off = s, d, lo
                break
        lv = sorted(set(lvl[r].tolist()))
        print(f"   {i:3d} {seg:4d} {dd['t'][i0 - off]:7.2f}s {len(r):4d} {len(r) / 100:5.2f}s "
              f"{str(lv):>10s} {v[i0]:6.2f} {int(lat[i0]):4d} {np.abs(tq[r]).max():8.0f}")


# =====================================================================================
def windows(tag, S, win=2.0, hop=0.5):
    """Rank 2 s windows by 30-49 Hz and 18-26 Hz envelope p99 on the torsion-bar channel."""
    print(f"\n{'=' * 108}\n== ROUTE {tag.upper()} -- WINDOW RANKING (torsion bar 0x18F b0:1, "
          f"{win:.0f}s windows, {hop:.1f}s hop)\n{'=' * 108}")
    rows = []
    for s, d in S:
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        e_hi = band_env(d["tq"], fs, 30.0, 49.0)
        e_lo = band_env(d["tq"], fs, 18.0, 26.0)
        e_r7 = band_env(d["tq"], fs, 5.0, 9.0)
        w0 = float(d["wall_t0"][0])
        nw = int(win * fs)
        step = max(1, int(hop * fs))
        # steering rate from the 0x14A angle-rate channel, and as d(ang)/dt for a second method.
        # ⚠ np.gradient(y, t) divides by zero on the duplicate timestamps this grid contains; use
        # the uniform 1/fs spacing instead.
        drate = np.gradient(d["ang"]) * fs
        for i in range(0, len(t) - nw, step):
            sl = slice(i, i + nw)
            rows.append(dict(
                seg=s, t=float(t[i]), wall=w0 + float(t[i]),
                p99_30_49=float(np.percentile(e_hi[sl], 99)),
                p99_18_26=float(np.percentile(e_lo[sl], 99)),
                p99_5_9=float(np.percentile(e_r7[sl], 99)),
                max_30_49=float(e_hi[sl].max()), max_18_26=float(e_lo[sl].max()),
                v=float(np.median(d["cs_v"][sl])), vmax=float(d["cs_v"][sl].max()),
                absang=float(np.abs(d["ang"][sl]).max()),
                rate_c=float(np.abs(d["rate_c"][sl]).max()),
                drate=float(np.abs(drate[sl]).max()),
                tq_sus=float(np.abs(d["tq"][sl]).mean()),
                tq_max=float(np.abs(d["tq"][sl]).max()),
                lat=float((d["cc_lat"][sl] > 0.5).mean()),
                gear=GEAR[int(np.median(d["cs_gear"][sl]))],
                lvlnz=float((d["prail"][sl] + d["phalf"][sl] + d["nhalf"][sl]
                             + d["nrail"][sl] > 0).mean()),
            ))
    out = ROOT / f"_cache_{tag}" / f"{tag}_windows.json"
    out.write_text(json.dumps(rows))
    print(f"   {len(rows)} windows -> {out}")

    for key in ("p99_30_49", "p99_18_26"):
        print(f"\n-- TOP 15 by {key} --")
        print(f"   {'seg':>3s} {'t':>7s} {'wall':>9s} {'vEgo':>6s} {'|ang|':>7s} "
              f"{'rate_c':>7s} {'drate':>7s} {'|tq|avg':>7s} {'|tq|max':>7s} {'lat':>5s} "
              f"{'30-49':>8s} {'18-26':>8s} {'5-9':>8s} {'gear':>7s}")
        for r in sorted(rows, key=lambda q: -q[key])[:15]:
            print(f"   {r['seg']:3d} {r['t']:6.2f}s "
                  f"{time.strftime('%H:%M:%S', time.localtime(r['wall'])):>9s} "
                  f"{r['v']:6.2f} {r['absang']:7.1f} {r['rate_c']:7.1f} {r['drate']:7.1f} "
                  f"{r['tq_sus']:7.0f} {r['tq_max']:7.0f} {r['lat']:5.2f} "
                  f"{r['p99_30_49']:8.1f} {r['p99_18_26']:8.1f} {r['p99_5_9']:8.1f} "
                  f"{r['gear']:>7s}")

    print(f"\n-- PER-SEGMENT BAND SUMMARY (p99 of the per-window p99, and the segment max) --")
    print(f"   {'seg':>3s} {'nwin':>5s} {'30-49 med':>10s} {'30-49 p95':>10s} {'30-49 max':>10s} "
          f"{'18-26 med':>10s} {'18-26 p95':>10s} {'18-26 max':>10s} {'5-9 max':>9s}")
    for s, _ in S:
        rs = [r for r in rows if r["seg"] == s]
        if not rs:
            continue
        h = np.array([r["p99_30_49"] for r in rs])
        lo = np.array([r["p99_18_26"] for r in rs])
        r7 = np.array([r["p99_5_9"] for r in rs])
        print(f"   {s:3d} {len(rs):5d} {np.median(h):10.1f} {np.percentile(h, 95):10.1f} "
              f"{h.max():10.1f} {np.median(lo):10.1f} {np.percentile(lo, 95):10.1f} "
              f"{lo.max():10.1f} {r7.max():9.1f}")
    return rows


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["r3a", "r3b"]):
        S = segs(tag)
        inventory(tag, S)
        ladder(tag, S)
        windows(tag, S)
