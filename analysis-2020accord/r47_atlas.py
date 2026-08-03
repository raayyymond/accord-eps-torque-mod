#!/usr/bin/env python3
"""r47_atlas.py -- the ROUTE ATLAS for V67 route `47` (75604b0a432fdc89_00000047--3e0b6134c0).

Every other route-47 workstream indexes into this. It answers "WHERE on this drive?" and nothing
else -- no spectra, no band energy, no build comparison. Those belong downstream and must consume
`_cache_r47/r47_maneuvers.json` so that every test is cut on the SAME episode bounds.

The operator's report this atlas has to be able to test:
  * "grind #2 seems mostly gone", but
  * "on a somewhat significant turn / changing lanes ON THE HIGHWAY there is sometimes a resonance
     that feels like grind #2", and it "is only on during LKAS-engaged", and
  * "might still be there somewhat at low speed, maybe just dampened".
So the deliverables are: highway lateral-manoeuvre episodes, a matched straight-cruise control set,
low-speed creep episodes split by engagement, and honest exposure seconds for all of it.

METHOD RULES (each has already retracted a claim in this kit -- see docs/STATE.md METHODOLOGY):

  ENGAGEMENT   carControl.latActive (`cc_lat`). NEVER cruiseState.enabled (`cs_eng`).
  EPISODES     Every episode emitted here lies ENTIRELY inside ONE contiguous run of the engagement
               mask and ONE speed regime. Downstream cuts FFT windows inside an episode; it must
               never cut across an engagement transition. Speed is applied only AFTER the
               engagement runs are cut, never before.
  MEAN+TAIL    Every episode carries p50 AND p95/peak of its covariates, because the mean and the
               tail have disagreed in sign on this data.
  WALL CLOCK   🛑 SEGMENT 0's `wall_t0` IS THE STALE PRE-NTP RTC (1751465105 = 2025-07-02, a year
               and 396 days off) and segment 25 has NO clocks message at all. Per-segment wall_t0
               is therefore UNUSABLE as written for those two. logMonoTime is one continuous boot
               clock across all 26 segments (t0_mono 37.93 -> 1539.46 s), so ONE offset fitted over
               the post-sync cluster covers the route. Same trap, same fix as r37_wallclock.py.

CHANNEL NOTES

  `ang`      0x14A bytes 0-1, i16be * -0.1  -> steering wheel angle, deg. Carries a real ~-4.5 deg
             OFFSET at highway cruise on a straight road (and -3.0 deg parked, engine off), so
             |ang| is NOT a turn measure. Everything here uses DEPARTURE from a +/-30 s running
             median baseline, which tracks the offset but not a manoeuvre.
  `rate_c`   0x14A bytes 2-3, i16be * -1.0  -> steering wheel rate, deg/s, quantised to 1.
  `cs_tq`    carState.steeringTorque -- the DRIVER's torque (counts).
  `cc_req`   carControl.actuators.torque, openpilot's normalised lateral command (-1..1).
  `e4tq`     0xE4 bytes 0-1 i16be -- the STEERING_CONTROL torque actually transmitted (counts).
  `g6806`    V67 probe bit6 = the LKAS deadband/engage gate. Reported per segment as an
             independent check on `cc_lat`; on this route they agree to <0.1%.

🛑 DUPLICATE TIMESTAMPS. 4,956 of the 150,327 samples (3.3%) share a logMonoTime with their
neighbour, because one `can` event batches several 0x14A frames. The frames are NOT duplicates --
150,327 frames over 1,495 s is the expected 100.5 Hz -- only the timestamps are quantised by
batching. So the grid is treated as UNIFORM at the per-segment fs, exactly as every periodogram in
this kit already does. Differentiating against `t_mono` instead divides by zero and silently
returns NaN for the rate at 3% of samples; the first draft of this file did precisely that and
reported `nan` peak rates for 5 of 16 manoeuvres.

Usage (from the repo root; the caches must already exist -- build them with
`python analysis-2020accord/extract_r47_cache.py 0 1 2 ... 25` if they do not):

    python analysis-2020accord/r47_atlas.py             # full atlas + write the JSON  (~90 s)
    python analysis-2020accord/r47_atlas.py --no-write  # print only
    python analysis-2020accord/r47_atlas.py --schema    # the JSON schema alone
    python analysis-2020accord/r47_atlas.py --verify    # re-derive every episode from the .npz
                                                        # files through `spans` alone and diff it
                                                        # against the emitted JSON (539 checks)

Set R47_CACHE to point the cache elsewhere; it defaults to <repo>/_cache_r47.
Output: _cache_r47/r47_maneuvers.json  (the schema is embedded in the file under "schema").
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

try:                                     # the kit's 🛑/⚠ markers vs the Windows cp1252 console
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(__import__("os").environ.get("R47_CACHE", ROOT / "_cache_r47"))
PFX = "r47s"
SEGS = list(range(26))
OUTJSON = CACHE / "r47_maneuvers.json"

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
PARK, DRIVE, REVERSE = 1.0, 2.0, 4.0

# ---------------------------------------------------------------- regime edges -----------------
# Speed regime edges, in m/s. Declared up front because the exposure table and every episode list
# below must use the SAME edges -- downstream tests are exposure-matched against this table.
V_STOP = 1.0        # below this the car is stopped / rolling to a stop
V_CREEP_HI = 4.0    # the operator's "low speed"; 1-4 m/s is the kit's creep band
V_STREET_HI = 20.0  # street | highway. NOT arbitrary: the route's speed histogram has a genuine
                    # empty valley here -- 19-22 m/s holds 401 of 150,327 samples (0.27%), against
                    # 2,436 in 18-19 and 2,548 in 24-25. Street tops out at 18.4 m/s, highway
                    # cruise sits at 25-33.5.
# 🛑 the bottom edge is -inf, not 0. vEgo goes to -0.11 m/s at 4,219 samples' worth of stops, and
# a 0.0 floor drops them from every row -- the first draft's partition was 31.2 s short of the
# route total for exactly this reason.
REGIMES = [("stop", -1e9, V_STOP), ("creep", V_STOP, V_CREEP_HI),
           ("street", V_CREEP_HI, V_STREET_HI), ("highway", V_STREET_HI, 1e9)]
E4_SAT = 4090.0     # |e4tq| at or above this is a SATURATED lateral command (the rail is 4096)
FWD = {2.0, 5.0, 6.0, 8.0, 9.0}     # gear ordinals that are forward motion (drive/sport/low/eco/M)

# ---------------------------------------------------------------- manoeuvre detector ------------
BASE_HALF_S = 30.0   # +/- half-width of the running-median angle baseline
SMOOTH_S = 0.30      # boxcar half-width for the 2-pass angle smoother (~2 Hz corner)
# Detection thresholds. |dev| at highway-engaged runs p90 = 2.13, p95 = 3.34, p99 = 8.51 deg, so
# 2.0 deg is roughly the p89 knee. The list is NOT threshold-fragile at the top: sweeping
# (DEV_HI, RATE_HI) over (2.5,5.0)/(2.2,4.5)/(2.0,4.0)/(1.8,3.5)/(1.5,3.0) gives 16/17/21/24/28
# episodes and the lane_change count saturates at 10 -- everything added below 2.0 is a soft
# "wander", and the ranking of the top ten is unchanged throughout.
DEV_HI = 2.0         # deg -- enter a manoeuvre
DEV_LO = 1.2         # deg -- leave it (hysteresis)
RATE_HI = 4.0        # deg/s on the smoothed rate -- alternative entry
MERGE_S = 1.5        # gaps shorter than this join one manoeuvre (a lane change is 2 rate pulses)
MIN_DUR_S = 1.0
MAX_DUR_S = 30.0     # a longer run is a sustained curve, kept but flagged

CTRL_DEV_MAX = 1.0     # deg -- a control window must stay this straight for its whole length
CTRL_RATE_MAX = 2.5    # deg/s on the smoothed rate
CTRL_RAWRATE_MAX = 20  # deg/s on the RAW 0x14A rate -- a single spike disqualifies the window
CTRL_VTOL = 2.0        # m/s -- speed-matching tolerance to the manoeuvre it is matched to

LOW_MIN_DUR_S = 1.5  # creep episodes shorter than this are not worth a downstream FFT window
# Two low-speed bands are emitted. 1-4 is the kit's creep band and the one the task asks for, but
# on this route it yields ONE engaged episode long enough for a single NFFT=256 window: the car
# passes through 1-4 m/s in ~2 s and the engagement-first cut (correctly) refuses to splice. 1-8
# m/s is the widest band that is still unambiguously "low speed" and it recovers 84 s engaged /
# 93 s manual. Both are tagged by `band`; a consumer picks, and says which.
LOW_BANDS = [(1.0, 4.0), (1.0, 8.0)]


# ================================================================ loading ========================
def load_all():
    """Concatenate all 26 segments onto ONE global grid keyed by absolute logMonoTime.

    Returns (d, seg_meta). `d` holds every cached channel plus:
        seg     segment index per sample
        t_seg   in-segment time (exactly the npz `t`, so a downstream slice indexes the npz)
        i_seg   in-segment sample index
        t_mono  absolute logMonoTime seconds (t0_mono + t)
        t_wall  unix seconds (t_mono + the fitted global offset)
        dt      that segment's median sample period -- the ONLY thing durations and the exposure
                table are summed from, because t_mono has batched duplicate timestamps.
    """
    parts, meta = [], {}
    mono_all, wall_all = [], []
    for s in SEGS:
        p = CACHE / f"{PFX}{s}.npz"
        if not p.exists():
            continue
        z = np.load(p)
        d = {k: z[k] for k in z.files}
        t0 = float(d["t0_mono"][0])
        n = len(d["t"])
        fs = 1.0 / float(np.median(np.diff(d["t"])))
        meta[s] = dict(t0_mono=t0, dur=float(d["t"][-1]), n=n, fs=fs)
        if len(d["clk_wall"]):
            mono_all.append(np.asarray(d["clk_mono"], float) + t0)
            wall_all.append(np.asarray(d["clk_wall"], float))
        parts.append((s, t0, n, d))

    off, off_sd, nsync, ntot, drift = fit_wall(np.concatenate(mono_all), np.concatenate(wall_all))

    keys = [k for k in parts[0][3] if parts[0][3][k].ndim == 1
            and len(parts[0][3][k]) == parts[0][2]]
    out = {k: np.concatenate([d[k] for _, _, _, d in parts]) for k in keys}
    out["seg"] = np.concatenate([np.full(n, s, float) for s, _, n, _ in parts])
    out["i_seg"] = np.concatenate([np.arange(n, dtype=float) for _, _, n, _ in parts])
    out["t_seg"] = out["t"].copy()
    out["t_mono"] = np.concatenate([d["t"] + t0 for _, t0, _, d in parts])
    out["t_wall"] = out["t_mono"] + off
    out["dt"] = np.concatenate([np.full(n, 1.0 / meta[s]["fs"]) for s, _, n, _ in parts])
    ordr = np.argsort(out["t_mono"], kind="stable")
    for k in out:
        out[k] = out[k][ordr]
    wall = dict(off=off, sd=off_sd, nsync=nsync, ntot=ntot, drift_ppm=drift * 1e6)
    return out, meta, wall


def fit_wall(mono, wall):
    """Constant unix-minus-mono offset over the POST-SYNC cluster only.

    Segment 0 straddles the NTP sync: its clocks samples carry the stale RTC and a naive median
    over all samples lands 34,212,428 s away from the truth. Split on the largest gap in the sorted
    offsets and keep the late cluster.
    """
    off = wall - mono
    o = np.sort(off)
    g = int(np.argmax(np.diff(o)))
    thr = 0.5 * (o[g] + o[g + 1]) if (o[g + 1] - o[g]) > 1.0 else -np.inf
    good = off > thr
    m, w = mono[good], wall[good]
    slope = float(np.polyfit(m, w - m, 1)[0])
    return (float(np.median(w - m)), float(np.std(w - m, ddof=1)), int(good.sum()), len(off),
            slope)


def hhmmss(u):
    return time.strftime("%H:%M:%S", time.localtime(u))


# ================================================================ signal helpers =================
def boxcar2(x, n):
    """Two-pass centred boxcar -- a gap-tolerant ~Gaussian smoother. No FFT, so no wrap-around at
    the ends and no assumption that the 26 concatenated segments form a perfectly uniform grid
    (the inter-segment gaps are ~0.020 s, two samples' worth)."""
    n = max(int(n) | 1, 1)
    if n <= 1:
        return np.asarray(x, float).copy()
    k = np.ones(n) / n
    pad = n // 2
    y = np.asarray(x, float)
    for _ in range(2):
        y = np.convolve(np.pad(y, pad, mode="edge"), k, mode="valid")
    return y


def running_median(x, t, half_s, dec_s=0.5):
    """Running median over +/- half_s, computed on a `dec_s` decimation and interpolated back.

    Tracks the steering-angle zero offset (which drifts: -0.1 deg at key-on, -4.5 deg at highway,
    -3.0 deg parked at the end) without absorbing a manoeuvre shorter than half_s.
    """
    x = np.asarray(x, float)
    t = np.asarray(t, float)
    edges = np.arange(t[0], t[-1] + dec_s, dec_s)
    idx = np.searchsorted(t, edges)
    cs, ce = idx[:-1], idx[1:]
    keep = ce > cs
    cs, ce = cs[keep], ce[keep]
    cm = np.array([np.median(x[a:b]) for a, b in zip(cs, ce)])
    ct = 0.5 * (edges[:-1] + edges[1:])[keep]
    h = max(int(round(half_s / dec_s)), 1)
    out = np.empty(len(cm))
    for i in range(len(cm)):
        out[i] = np.median(cm[max(0, i - h):i + h + 1])
    return np.interp(t, ct, out)


def runs(mask, t, max_gap=0.06):
    """Contiguous [a,b) index runs of `mask` with no sample gap > max_gap."""
    idx = np.flatnonzero(np.asarray(mask, bool))
    if not len(idx):
        return []
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > max_gap:
            out.append((s, prev + 1))
            s = i
        prev = i
    out.append((s, prev + 1))
    return out


def spans_of(d, a, b):
    """Per-segment slice bounds for a global [a,b) range, so a consumer can index the npz files
    directly. An episode that crosses a segment boundary yields two spans."""
    sg = d["seg"][a:b].astype(int)
    ii = d["i_seg"][a:b].astype(int)
    tt = d["t_seg"][a:b]
    out = []
    for s in np.unique(sg):
        m = sg == s
        out.append(dict(seg=int(s), i0=int(ii[m][0]), i1=int(ii[m][-1]) + 1,
                        t0=round(float(tt[m][0]), 3), t1=round(float(tt[m][-1]), 3)))
    return out


def cov(d, a, b, extra=None):
    """The covariate block every episode record carries. MEAN AND TAIL together, always."""
    sl = slice(a, b)
    v, ang, rate = d["cs_v"][sl], d["ang"][sl], d["rate_c"][sl]
    tq, dev = d["cs_tq"][sl], d["dev"][sl]
    n = b - a
    r = dict(
        n=int(n), dur=round(float(d["dt"][sl].sum()), 3),
        v_mean=round(float(v.mean()), 3), v_p50=round(float(np.median(v)), 3),
        v_min=round(float(v.min()), 3), v_max=round(float(v.max()), 3),
        ang_p50=round(float(np.median(np.abs(ang))), 2),
        ang_p95=round(float(np.percentile(np.abs(ang), 95)), 2),
        ang_peak=round(float(np.abs(ang).max()), 2),
        dev_p50=round(float(np.median(np.abs(dev))), 2),
        dev_p95=round(float(np.percentile(np.abs(dev), 95)), 2),
        dev_peak=round(float(np.abs(dev).max()), 2),
        dev_swing=round(float(dev.max() - dev.min()), 2),
        rate_p50=round(float(np.median(np.abs(rate))), 2),
        rate_p95=round(float(np.percentile(np.abs(rate), 95)), 2),
        rate_peak=round(float(np.abs(rate).max()), 2),
        arate_peak=round(float(np.abs(d["arate"][sl]).max()), 2),
        tq_p50=round(float(np.median(np.abs(tq))), 1),
        tq_p95=round(float(np.percentile(np.abs(tq), 95)), 1),
        tq_peak=round(float(np.abs(tq).max()), 1),
        lat_duty=round(float((d["cc_lat"][sl] > 0.5).mean()), 4),
        g6806_duty=round(float((d["g6806"][sl] > 0.5).mean()), 4),
        press_any=bool((d["cs_press"][sl] > 0.5).any()),
        press_duty=round(float((d["cs_press"][sl] > 0.5).mean()), 4),
        ccreq_p95=round(float(np.percentile(np.abs(d["cc_req"][sl]), 95)), 4),
        ccreq_peak=round(float(np.abs(d["cc_req"][sl]).max()), 4),
        e4tq_p95=round(float(np.percentile(np.abs(d["e4tq"][sl]), 95)), 1),
        e4tq_peak=round(float(np.abs(d["e4tq"][sl]).max()), 1),
        e4req_duty=round(float((d["e4req"][sl] > 0.5).mean()), 4),
        e4sat_duty=round(float((np.abs(d["e4tq"][sl]) >= E4_SAT).mean()), 4),
        arm1_duty=round(float((d["arm"][sl] == 1).mean()), 4),
        gear=GEAR[int(np.median(d["cs_gear"][sl]))],
        stop_duty=round(float((d["cs_v"][sl] < V_STOP).mean()), 4),
        illegal=int(d["illegal"][sl].sum()),
        t_wall=round(float(d["t_wall"][a]), 3), wall_hms=hhmmss(float(d["t_wall"][a])),
        t_mono=round(float(d["t_mono"][a]), 3),
        spans=spans_of(d, a, b),
    )
    if extra:
        r.update(extra)
    return r


# ================================================================ per-segment table ==============
def segment_table(d, meta, wall):
    print(f"\n{'=' * 132}\nPER-SEGMENT SUMMARY  --  route 47, V67, "
          f"{hhmmss(meta[0]['t0_mono'] + wall['off'])} .. "
          f"{hhmmss(meta[max(meta)]['t0_mono'] + meta[max(meta)]['dur'] + wall['off'])} local\n"
          f"{'=' * 132}")
    print(f"{'sg':>2s} {'wall':>8s} {'dur':>6s} {'n':>5s} {'fs':>6s} | "
          f"{'vmin':>5s} {'vp50':>5s} {'vmax':>5s} | {'lat%':>5s} {'g68%':>5s} | "
          f"{'|a|p50':>6s} {'|a|p95':>6s} | {'|r|p50':>6s} {'|r|p95':>6s} | "
          f"{'|tq|50':>6s} {'|tq|95':>6s} | {'prs%':>5s} | gears")
    rows = []
    for s in sorted(meta):
        m = d["seg"] == s
        v, ang, rate, tq = d["cs_v"][m], d["ang"][m], d["rate_c"][m], d["cs_tq"][m]
        lat = d["cc_lat"][m] > 0.5
        g68 = d["g6806"][m] > 0.5
        gr = d["cs_gear"][m]
        gh = {GEAR[int(x)]: int((gr == x).sum()) for x in np.unique(gr)}
        w0 = meta[s]["t0_mono"] + wall["off"]
        r = dict(seg=s, wall_start=round(w0, 3), wall_hms=hhmmss(w0),
                 t0_mono=round(meta[s]["t0_mono"], 3), dur=round(meta[s]["dur"], 2),
                 n=meta[s]["n"], fs=round(meta[s]["fs"], 2),
                 v_min=round(float(v.min()), 2), v_p50=round(float(np.median(v)), 2),
                 v_max=round(float(v.max()), 2),
                 lat_duty=round(100 * float(lat.mean()), 2),
                 g6806_duty=round(100 * float(g68.mean()), 2),
                 ang_p50=round(float(np.median(np.abs(ang))), 2),
                 ang_p95=round(float(np.percentile(np.abs(ang), 95)), 2),
                 rate_p50=round(float(np.median(np.abs(rate))), 2),
                 rate_p95=round(float(np.percentile(np.abs(rate), 95)), 2),
                 tq_p50=round(float(np.median(np.abs(tq))), 1),
                 tq_p95=round(float(np.percentile(np.abs(tq), 95)), 1),
                 press_duty=round(100 * float((d["cs_press"][m] > 0.5).mean()), 2),
                 gears=gh, illegal=int(d["illegal"][m].sum()),
                 field0=int((d["field"][m] == 0).sum()))
        rows.append(r)
        print(f"{s:2d} {r['wall_hms']:>8s} {r['dur']:6.2f} {r['n']:5d} {r['fs']:6.2f} | "
              f"{r['v_min']:5.2f} {r['v_p50']:5.2f} {r['v_max']:5.2f} | "
              f"{r['lat_duty']:5.1f} {r['g6806_duty']:5.1f} | "
              f"{r['ang_p50']:6.2f} {r['ang_p95']:6.2f} | "
              f"{r['rate_p50']:6.1f} {r['rate_p95']:6.1f} | "
              f"{r['tq_p50']:6.0f} {r['tq_p95']:6.0f} | {r['press_duty']:5.1f} | "
              + " ".join(f"{k}:{v}" for k, v in gh.items()))
    bad = sum(r["illegal"] + r["field0"] for r in rows)
    n = len(d["t"])
    lat = d["cc_lat"] > 0.5
    print(f"\nPROBE LIVENESS: illegal frames {bad} / {n}  -- "
          f"{'V67 gate probe is live on every segment' if bad == 0 else '🛑 DECODE FAULTS PRESENT'}")
    print(f"GATE CHECK: cc_lat == g6806 on {100 * float((lat == (d['g6806'] > 0.5)).mean()):.3f}% "
          f"of samples ({int((lat != (d['g6806'] > 0.5)).sum())} disagreements) -- the V67 probe "
          f"independently confirms the engagement mask.")
    arms = {int(k): int((d["arm"] == k).sum()) for k in np.unique(d["arm"])}
    print(f"RATE-LANE GAIN ARM (V67 priority ladder): {arms}  "
          f"[0 = stock mode-10 LERP, 1 = gp-0x6806 gate -> cal 0xC6446 = 5244 = 2.00x, "
          f"2 = gp-0x671d mask -> 1024, 3 = gp-0x671a -> 2048]")
    print(f"            gp-0x671d (the masking risk) fired on {100 * float(d['g671d'].mean()):.4f}% "
          f"of samples and gp-0x671a on {100 * float(d['g671a'].mean()):.4f}% -- BOTH IDENTICALLY "
          f"ZERO, so the ladder is BINARY on this route: arm 1 (2.00x) exactly while engaged, arm "
          f"0 (stock) exactly while not. ⇒ the engaged-vs-manual contrast on route 47 IS the "
          f"Kd 2.00x-vs-stock contrast, with no third state to confound it.")
    sat = np.abs(d["e4tq"]) >= E4_SAT
    print(f"COMMAND SATURATION: |e4tq| >= {E4_SAT:.0f} on {int(sat.sum())} samples, "
          f"{int((sat & (d['cs_v'] > V_STREET_HI)).sum())} of them at highway speed. e4tq is "
          f"EXACTLY 0 whenever e4req == 0, and e4req agrees with cc_lat on "
          f"{100 * float(((d['e4req'] > 0.5) == lat).mean()):.3f}% of samples.")
    return rows


# ================================================================ phases ========================
def phases(d):
    """Data-driven phase segmentation. NO operator prose is used.

    Per 1 s bin: (median vEgo, held gear, standstill duty) -> a regime label. Bins are then merged
    into phases, short phases (< MIN_PHASE_S) absorbed into the neighbour they resemble, and the
    parking-lot phases separated from street by their steering signature (|ang| p95) rather than
    by speed alone -- a stop light and a parking lot are both slow, but only one is at lock.
    """
    MIN_PHASE_S = 8.0
    t = d["t_mono"]
    edges = np.arange(t[0], t[-1], 1.0)
    idx = np.searchsorted(t, edges)
    bins = []
    for a, b in zip(idx[:-1], idx[1:]):
        if b <= a:
            continue
        v = float(np.median(d["cs_v"][a:b]))
        gr = float(np.median(d["cs_gear"][a:b]))
        bins.append(dict(a=int(a), b=int(b), v=v, gear=gr,
                         angp95=float(np.percentile(np.abs(d["ang"][a:b]), 95)),
                         lat=float((d["cc_lat"][a:b] > 0.5).mean())))

    def label(q):
        if q["gear"] == PARK:
            return "PARK"
        if q["gear"] == REVERSE:
            return "PARKING_LOT"
        if q["v"] >= V_STREET_HI:
            return "HIGHWAY"
        if q["v"] >= V_CREEP_HI:
            return "STREET"
        # slow in DRIVE: parking-lot manoeuvring is at lock, a traffic stop is not
        return "PARKING_LOT" if q["angp95"] > 90.0 else "STREET"

    for q in bins:
        q["lab"] = label(q)
    # median-of-5 smoothing on the label sequence kills single-bin flapping at a stop light
    L = [q["lab"] for q in bins]
    S = list(L)
    for i in range(len(L)):
        w = L[max(0, i - 2):i + 3]
        S[i] = max(set(w), key=w.count)
    for q, s in zip(bins, S):
        q["lab"] = s

    def group(bs):
        g = []
        for q in bs:
            if g and g[-1]["lab"] == q["lab"]:
                g[-1]["bins"].append(q)
            else:
                g.append(dict(lab=q["lab"], bins=[q]))
        return g

    ph = group(bins)
    # absorb short phases into the longer neighbour, then RE-GROUP -- absorbing a short phase can
    # leave two same-label phases adjacent, and the first draft left them split (the parking lot
    # came out as five phases instead of one).
    changed = True
    while changed and len(ph) > 1:
        changed = False
        for i, p in enumerate(ph):
            if len(p["bins"]) >= MIN_PHASE_S:
                continue
            j = (i - 1 if i > 0 and (i == len(ph) - 1
                 or len(ph[i - 1]["bins"]) >= len(ph[i + 1]["bins"])) else i + 1)
            for q in p["bins"]:                 # 🛑 RELABEL the absorbed bins. group() keys off
                q["lab"] = ph[j]["lab"]         # the bin's own label, so without this the
            ph[j]["bins"] += p["bins"]          # re-group undoes the absorption and the while
            ph[j]["bins"].sort(key=lambda q: q["a"])   # loop never terminates.
            ph.pop(i)
            ph = group(sorted([q for pp in ph for q in pp["bins"]], key=lambda q: q["a"]))
            changed = True
            break

    # ---- ramps -------------------------------------------------------------------------------
    # A ramp is NOT "a STREET phase next to a HIGHWAY phase" -- that swallowed 197 s of genuine
    # 10-18 m/s street driving into "RAMP_ON" in the first draft. It is the SPEED TRANSIT itself:
    # walk out of the HIGHWAY phase into its neighbour while the 1 s-binned speed keeps falling
    # (backwards) or rising (forwards), and cut there.
    # iterate the HIGHWAY phases back-to-front so the inserts below cannot shift an index we have
    # not visited yet
    for i in [k for k, p in enumerate(ph) if p["lab"] == "HIGHWAY"][::-1]:
        if i + 1 < len(ph) and ph[i + 1]["lab"] == "STREET":             # off-ramp
            bs = ph[i + 1]["bins"]
            k = 0
            while k + 1 < len(bs) and bs[k]["v"] > bs[k + 1]["v"] - 0.05 and bs[k]["v"] > V_CREEP_HI:
                k += 1
            if k >= MIN_PHASE_S:
                nb, ph[i + 1]["bins"] = bs[:k], bs[k:]
                ph.insert(i + 1, dict(lab="RAMP_OFF", bins=nb))
        if i > 0 and ph[i - 1]["lab"] == "STREET":                       # on-ramp
            bs = ph[i - 1]["bins"]
            k = len(bs)
            while k > 1 and bs[k - 1]["v"] > bs[k - 2]["v"] - 0.05 and bs[k - 2]["v"] > V_CREEP_HI:
                k -= 1
            if len(bs) - k >= MIN_PHASE_S:
                ph[i - 1]["bins"], nb = bs[:k], bs[k:]
                ph.insert(i, dict(lab="RAMP_ON", bins=nb))
    ph = [p for p in ph if p["bins"]]

    out = []
    for k, p in enumerate(ph):
        a, b = p["bins"][0]["a"], p["bins"][-1]["b"]
        lab = p["lab"]
        rec = dict(idx=k, phase=lab, i0=int(a), i1=int(b))
        rec.update({kk: vv2 for kk, vv2 in cov(d, a, b).items()
                    if kk in ("dur", "n", "v_mean", "v_p50", "v_min", "v_max", "ang_p50",
                              "ang_p95", "rate_p95", "tq_p50", "tq_p95", "lat_duty", "g6806_duty",
                              "press_duty", "stop_duty", "gear", "t_wall", "wall_hms", "t_mono",
                              "spans")})
        rec["gear_hist"] = {GEAR[int(x)]: int((d["cs_gear"][a:b] == x).sum())
                            for x in np.unique(d["cs_gear"][a:b])}
        out.append(rec)

    print(f"\n{'=' * 132}\nPHASE SEGMENTATION  (1 s bins -> label -> median-of-5 -> merge; "
          f"boundaries from speed/gear/steering only)\n{'=' * 132}")
    print(f"{'#':>2s} {'phase':>11s} {'wall':>8s} {'dur':>7s} | {'vmin':>5s} {'vp50':>5s} "
          f"{'vmax':>5s} | {'lat%':>5s} {'stop%':>5s} | {'|a|p95':>6s} {'|r|p95':>6s} "
          f"{'|tq|95':>6s} | spans (seg: t0..t1)")
    for r in out:
        sp = "  ".join(f"{s['seg']}:{s['t0']:.1f}-{s['t1']:.1f}" for s in r["spans"])
        print(f"{r['idx']:2d} {r['phase']:>11s} {r['wall_hms']:>8s} {r['dur']:7.1f} | "
              f"{r['v_min']:5.2f} {r['v_p50']:5.2f} {r['v_max']:5.2f} | "
              f"{100 * r['lat_duty']:5.1f} {100 * r['stop_duty']:5.1f} | {r['ang_p95']:6.1f} "
              f"{r['rate_p95']:6.1f} {r['tq_p95']:6.0f} | {sp}")
    return out


def phase_of(ph, i):
    for p in ph:
        if p["i0"] <= i < p["i1"]:
            return p["phase"]
    return "?"


def phase_edge(d, ph, a, b):
    """Seconds from the episode to the nearest phase boundary. 🛑 the most SEVERE manoeuvre on
    this route (M00) ends 0.1 s before the RAMP_OFF boundary -- it is the freeway exit, not a
    mid-cruise lane change, and a consumer ranking by severity would otherwise take the exit ramp
    as the exemplar of the operator's reported symptom."""
    e = [p["i0"] for p in ph] + [p["i1"] for p in ph]
    return round(float(min(d["dt"].mean() * abs(x - i) for x in e for i in (a, b))), 2)


# ================================================================ manoeuvres ====================
def maneuvers(d, ph):
    """Highway-speed, LKAS-engaged lateral manoeuvres -- the atlas's primary deliverable.

    Detection, in the order the kit's method rules require:
      1. cut contiguous runs of the ENGAGEMENT mask (cc_lat > 0.5);
      2. inside each run, keep the part that is also above V_STREET_HI (speed applied AFTER the
         engagement cut, per the creep-script convention);
      3. inside those, hysteresis-threshold |dev| (angle departure from the +/-30 s running median)
         with |arate| as an alternative entry, so both a lane change (two rate pulses, small net
         displacement) and a sustained curve (large displacement, small rate) are caught;
      4. merge detections separated by < MERGE_S -- a lane change is ONE manoeuvre, not two.
    """
    eng = d["cc_lat"] > 0.5
    hi = d["cs_v"] > V_STREET_HI
    dev, arate = d["dev"], d["arate"]
    hot = (np.abs(dev) > DEV_HI) | (np.abs(arate) > RATE_HI)
    warm = (np.abs(dev) > DEV_LO) | (np.abs(arate) > 0.5 * RATE_HI)

    eps, parent = [], {}
    for a, b in runs(eng, d["t_mono"]):
        for c, e in runs(hi[a:b], d["t_mono"][a:b]):
            c, e = a + c, a + e
            if e - c < 200:
                continue
            for u, w in _hyst(hot[c:e], warm[c:e], d["t_mono"][c:e]):
                eps.append((c + u, c + w))
                parent[(c + u, c + w)] = (c, e)      # the engaged+highway run it lives in

    # merge across short gaps -- a lane change is TWO rate pulses and ONE manoeuvre. Only merge
    # inside the same parent run, so a merge can never bridge an engagement transition.
    merged = []
    for a, b in eps:
        if (merged and parent[(a, b)] == merged[-1][2]
                and d["t_mono"][a] - d["t_mono"][merged[-1][1] - 1] < MERGE_S):
            merged[-1] = (merged[-1][0], b, merged[-1][2])
        else:
            merged.append((a, b, parent[(a, b)]))

    out = []
    for a, b, (pa, pb) in merged:
        dur = float(d["dt"][a:b].sum())
        if dur < MIN_DUR_S:
            continue
        r = cov(d, a, b)
        s = dev[a:b]
        fs = 1.0 / float(d["dt"][a])
        # SHAPE: a lane change returns to the baseline (net ~0, both signs present); a curve does
        # not. `reversal` = the departure changes sign by more than DEV_LO on both sides.
        rev = bool(s.max() > DEV_LO and s.min() < -DEV_LO)
        net = float(np.median(s[-max(int(0.2 * fs), 1):]) - np.median(s[:max(int(0.2 * fs), 1)]))
        jp = a + int(np.argmax(np.abs(d["arate"][a:b])))     # sharpest steering moment
        half = int(round(1.28 * fs))                         # -> a 2.56 s NFFT=256 core window
        c0, c1 = max(jp - half, pa), min(jp + half, pb)
        if c1 - c0 < 2 * half:                               # slide, don't shrink, if clipped
            c0 = max(min(c0, pb - 2 * half), pa)
            c1 = min(c0 + 2 * half, pb)
        r.update(
            kind=("lane_change" if rev else ("curve" if abs(net) > DEV_LO else "wander")),
            reversal=rev, dev_net=round(net, 2),
            dev_signed_peak=round(float(s[np.argmax(np.abs(s))]), 2),
            long_run=bool(dur > MAX_DUR_S),
            phase=phase_of(ph, (a + b) // 2), phase_edge_s=phase_edge(d, ph, a, b),
            # 🛑 a manoeuvre the DRIVER is muscling is a different experiment from one openpilot is
            # driving alone. Both are kept; downstream must not pool them silently.
            driver_active=bool(r["press_duty"] > 0.10 or r["tq_p50"] > 500.0),
            # severity PROXY: lateral acceleration under a bicycle model is proportional to
            # v^2 * steer-angle-departure. The constant (steering ratio / wheelbase) is NOT
            # asserted here, so this is an ORDERING statistic in deg*(m/s)^2/1000, not m/s^2.
            load_proxy=round(float(r["v_mean"] ** 2 * r["dev_peak"] / 1000.0), 3),
            i0=int(a), i1=int(b), regime="highway", eng=1,
            peak_i=int(jp), peak_t_rel=round(float(d["dt"][a:jp].sum()), 3),
            peak_seg=int(d["seg"][jp]), peak_t_seg=round(float(d["t_seg"][jp]), 3),
            run_i0=int(pa), run_i1=int(pb),
            core=dict(i0=int(c0), i1=int(c1), dur=round(float(d["dt"][c0:c1].sum()), 3),
                      spans=spans_of(d, c0, c1)))
        out.append(r)
    out.sort(key=lambda r: -r["load_proxy"])
    for k, r in enumerate(out):
        r["id"] = f"M{k:02d}"
    return out


def _hyst(hot, warm, t):
    """Hysteresis runs: open on `hot`, extend while `warm`, close when neither."""
    out = []
    for a, b in runs(warm, t):
        if not hot[a:b].any():
            continue
        out.append((a, b))
    return out


# ================================================================ controls ======================
def controls(d, mans, ph):
    """Straight-line highway-cruise windows matched 1:1 to the manoeuvres on duration and speed.

    Same engagement-first cut, same regime, same length; the ONLY difference is that |dev| and the
    smoothed rate stay below the control thresholds for the WHOLE window. Greedy nearest-speed
    matching, no reuse, no overlap with a manoeuvre or with another control.
    """
    eng = d["cc_lat"] > 0.5
    hi = d["cs_v"] > V_STREET_HI
    # 🛑 the RAW rate bound is not redundant with the smoothed one. Without it a window whose
    # smoothed |arate| never reaches 2.5 deg/s can still contain a 67 deg/s raw spike -- the first
    # draft's control C08 did exactly that, and a "straight cruise" control containing a steering
    # transient is worse than no control at all.
    quiet = ((np.abs(d["dev"]) < CTRL_DEV_MAX) & (np.abs(d["arate"]) < CTRL_RATE_MAX)
             & (np.abs(d["rate_c"]) <= CTRL_RAWRATE_MAX))
    fs = 1.0 / float(np.median(np.diff(d["t_mono"])))
    taken = np.zeros(len(d["t_mono"]), bool)
    for m in mans:
        taken[m["i0"]:m["i1"]] = True

    # candidate pool: every quiet stretch inside an engaged+highway run
    pool = []
    for a, b in runs(eng, d["t_mono"]):
        for c, e in runs(hi[a:b], d["t_mono"][a:b]):
            c, e = a + c, a + e
            for u, w in runs(quiet[c:e], d["t_mono"][c:e]):
                pool.append((c + u, c + w))

    out = []
    for m in sorted(mans, key=lambda r: -r["load_proxy"]):
        need = int(round(m["dur"] * fs))
        best = None
        for a, b in pool:
            for st in range(a, b - need + 1, max(int(0.5 * fs), 1)):
                en = st + need
                if taken[st:en].any():
                    continue
                vm = float(d["cs_v"][st:en].mean())
                if abs(vm - m["v_mean"]) > CTRL_VTOL:
                    continue
                sc = abs(vm - m["v_mean"])
                if best is None or sc < best[0]:
                    best = (sc, st, en)
        if best is None:
            continue
        _, st, en = best
        taken[st:en] = True
        r = cov(d, st, en)
        r.update(matched_to=m["id"], v_gap=round(float(r["v_mean"] - m["v_mean"]), 3),
                 dur_gap=round(float(r["dur"] - m["dur"]), 3),
                 i0=int(st), i1=int(en), regime="highway", eng=1, kind="straight_control",
                 phase=phase_of(ph, (st + en) // 2),
                 driver_active=bool(r["press_duty"] > 0.10 or r["tq_p50"] > 500.0))
        out.append(r)
    for k, r in enumerate(out):
        r["id"] = f"C{k:02d}"
    return out


# ================================================================ low speed =====================
def lowspeed(d, ph):
    """Low-speed episodes, split by engagement, over each band in LOW_BANDS.

    Engagement runs are cut FIRST (both polarities), then the low-speed sub-runs are taken inside
    them. Doing it the other way round shreds contiguity at every latActive transition and
    manufactures a null -- the mistake the creep-script convention exists to prevent.
    """
    eng = d["cc_lat"] > 0.5
    out = []
    for lo, hi in LOW_BANDS:
        band = f"{lo:.0f}-{hi:.0f}"
        creep = (d["cs_v"] >= lo) & (d["cs_v"] < hi)
        for e, mask in ((1, eng), (0, ~eng)):
            for a, b in runs(mask, d["t_mono"]):
                for c, w in runs(creep[a:b], d["t_mono"][a:b]):
                    c, w = a + c, a + w
                    if float(d["dt"][c:w].sum()) < LOW_MIN_DUR_S:
                        continue
                    r = cov(d, c, w)
                    r.update(eng=e, regime="lowspeed", band=band, i0=int(c), i1=int(w),
                             kind=("lowspeed_engaged" if e else "lowspeed_manual"),
                             phase=phase_of(ph, (c + w) // 2),
                             driver_active=bool(r["press_duty"] > 0.10 or r["tq_p50"] > 500.0),
                             # a downstream FFT window is NFFT=256 = 2.56 s; anything shorter
                             # cannot produce even one, whatever its duration says
                             fits_window=bool(r["dur"] >= 2.56),
                             run_i0=int(a), run_i1=int(b),
                             load_proxy=round(float(r["v_mean"] ** 2 * r["dev_peak"] / 1000.0), 4))
                    out.append(r)
    out.sort(key=lambda r: (r["band"], -r["eng"], -r["dur"]))
    for k, r in enumerate(out):
        r["id"] = f"L{k:03d}"
    return out


# ================================================================ exposure ======================
def exposure(d, ph):
    """Seconds in each (speed regime x engagement) cell, plus a phase x engagement cross-tab.

    🛑 Every downstream comparison on this route must be exposure-matched against THIS table. It is
    computed by summing per-sample dt (median dt per segment), not by counting samples at a nominal
    100 Hz, because fs ranges 99.35-101.41 across the 26 segments.
    """
    dt = d["dt"]
    eng = d["cc_lat"] > 0.5
    v, gr = d["cs_v"], d["cs_gear"]
    fwd = np.isin(gr, list(FWD))

    tab = {}
    print(f"\n{'=' * 132}\nEXPOSURE  (seconds; engagement = carControl.latActive; dt summed "
          f"per-sample at the per-segment fs, which varies 99.35-101.41 Hz)\n"
          f"🛑 the rows below are a strict PARTITION -- forward-gear rows are split by speed, "
          f"reverse and park/neutral are their own rows, and they sum to the route total.\n"
          f"{'=' * 132}")
    print(f"{'regime':>26s} {'v range m/s':>14s} | {'ENGAGED s':>11s} {'MANUAL s':>11s} "
          f"{'TOTAL s':>11s} | {'eng %':>6s}")

    def row(name, rng, m, key=None):
        te, tm = float(dt[m & eng].sum()), float(dt[m & ~eng].sum())
        tab[key or name] = dict(engaged=round(te, 2), manual=round(tm, 2), total=round(te + tm, 2))
        print(f"{name:>26s} {rng:>14s} | {te:11.2f} {tm:11.2f} {te + tm:11.2f} | "
              f"{100 * te / max(te + tm, 1e-9):6.1f}")
        return te + tm

    acc = 0.0
    for name, lo, hi in REGIMES:
        rng = (f">{lo:.0f}" if hi > 1e8 else f"<{hi:.0f}" if lo < -1e8 else f"{lo:.0f}-{hi:.0f}")
        acc += row(name, rng, fwd & (v >= lo) & (v < hi))
    acc += row("reverse", "-", gr == REVERSE)
    acc += row("park / neutral / unk", "-", ~fwd & (gr != REVERSE), key="park")
    te, tm = float(dt[eng].sum()), float(dt[~eng].sum())
    tab["ROUTE"] = dict(engaged=round(te, 2), manual=round(tm, 2), total=round(te + tm, 2))
    print(f"{'ROUTE TOTAL':>26s} {'-':>14s} | {te:11.2f} {tm:11.2f} {te + tm:11.2f} | "
          f"{100 * te / (te + tm):6.1f}")
    print(f"{'partition check':>26s} {'-':>14s} | rows sum to {acc:.2f} s vs route "
          f"{te + tm:.2f} s  (residual {acc - te - tm:+.3f} s)")

    # ---- which contrasts this route can actually carry -----------------------------------------
    # 🛑 stated BEFORE anyone runs a test on it. A contrast whose weaker arm is a handful of
    # seconds cannot produce a ratio distinguishable from a split-half null, and this kit has
    # already spent a session on a claim that rested on n = 1.
    print(f"\nTESTABILITY -- engaged vs manual, per regime (the weaker arm sets the power):")
    for name, _, _ in REGIMES:
        c = tab[name]
        w = min(c["engaged"], c["manual"])
        verdict = ("TESTABLE" if w >= 60 else "THIN, report the CI and the null" if w >= 20
                   else "NOT TESTABLE -- do not quote an engaged/manual ratio here")
        print(f"   {name:>8s}: engaged {c['engaged']:8.1f} s  manual {c['manual']:8.1f} s  "
              f"-> weaker arm {w:7.1f} s   {verdict}")
    print(f"   🛑 the HIGHWAY row has ZERO manual seconds: openpilot was engaged for every one of "
          f"the {tab['highway']['engaged']:.0f} s above 20 m/s. The operator's \"only during "
          f"LKAS-engaged\" CANNOT be tested at highway speed on this route -- there is no "
          f"disengaged highway driving to compare against. Test it against the MANOEUVRE vs "
          f"MATCHED-CONTROL contrast instead, which is fully within-engaged.")

    print(f"\n{'phase':>12s} | {'ENGAGED s':>11s} {'MANUAL s':>11s} {'TOTAL s':>11s} | {'eng %':>6s}")
    pt = {}
    for lab in sorted({p["phase"] for p in ph}):
        m = np.zeros(len(v), bool)
        for p in ph:
            if p["phase"] == lab:
                m[p["i0"]:p["i1"]] = True
        te, tm = float(dt[m & eng].sum()), float(dt[m & ~eng].sum())
        pt[lab] = dict(engaged=round(te, 2), manual=round(tm, 2), total=round(te + tm, 2))
        print(f"{lab:>12s} | {te:11.2f} {tm:11.2f} {te + tm:11.2f} | "
              f"{100 * te / max(te + tm, 1e-9):6.1f}")
    return dict(by_speed_regime=tab, by_phase=pt)


# ================================================================ schema ========================
SCHEMA = {
    "_about": "Route atlas for V67 route 47 (75604b0a432fdc89_00000047--3e0b6134c0). Written by "
              "analysis-2020accord/r47_atlas.py. Consumers: cut analysis windows INSIDE these "
              "episodes only; never across an engagement transition.",
    "_engagement": "eng / lat_duty are carControl.latActive. NEVER cruiseState.enabled.",
    "_indexing": "i0/i1 index the GLOBAL concatenated route array built by r47_atlas.load_all() "
                 "(all 26 segments, sorted by absolute logMonoTime). To index the .npz files "
                 "directly use `spans`: a list of {seg, i0, i1, t0, t1} where i0/i1 are sample "
                 "indices into _cache_r47/r47s<seg>.npz and t0/t1 are that segment's own `t`. An "
                 "episode that crosses a segment boundary has two spans; the ~0.020 s inter-"
                 "segment gap is smaller than the 0.06 s contiguity tolerance, so the episode is "
                 "genuinely contiguous.",
    "_wallclock": "t_wall is unix seconds = t_mono + a single global offset fitted over the "
                  "post-NTP-sync clocks cluster. Segment 0's own wall_t0 field is the STALE RTC "
                  "and segment 25 has none; do not use per-segment wall_t0 on this route.",
    "_channels": {
        "dev": "steering angle minus its +/-30 s running median -- the turn measure. Raw |ang| is "
               "NOT usable: the zero offset drifts (-0.1 deg at key-on, -4.5 deg at highway "
               "cruise on a straight road, -3.0 deg parked at shutdown).",
        "arate": "d/dt of the boxcar-smoothed angle, deg/s.",
        "rate_*": "the native 0x14A rate field (`rate_c`), deg/s, quantised to 1.",
        "tq_*": "carState.steeringTorque -- the DRIVER's torque, counts.",
        "ccreq_*": "carControl.actuators.torque, openpilot's normalised lateral command (-1..1).",
        "e4tq_*": "0xE4 bytes 0-1 -- the STEERING_CONTROL torque actually transmitted, counts. "
                  "READ IT WITH e4req_duty: e4tq is exactly 0 on every sample where "
                  "STEER_TORQUE_REQUEST is clear, so a zero here means 'not commanding', not "
                  "'commanding zero'. 0xE4 arrives at 100 Hz throughout with a max gap of 0.05 s, "
                  "so the held-last value in the cache is never meaningfully stale.",
        "e4sat_duty": "fraction of the episode with |e4tq| >= 4090, i.e. the lateral command at "
                      "its 4096 rail. ZERO at highway speed on this whole route -- all 2,714 "
                      "saturated samples are below 20 m/s.",
        "g6806_duty": "V67 probe bit6, the LKAS deadband/engage gate -- an independent check on "
                      "cc_lat (they agree to <0.1% on this route).",
        "arm1_duty": "fraction on V67 ladder arm 1 (gp-0x6806 gate -> cal 0xC6446 = 5244 = 2.00x "
                     "rate-lane gain). gp-0x671d and gp-0x671a are IDENTICALLY ZERO on this "
                     "route, so arm is binary: 1 while engaged, 0 (stock mode-10 LERP) otherwise.",
    },
    "_lists": {
        "phases": "Contiguous drive phases from speed/gear/steering only. phase in "
                  "{PARK, PARKING_LOT, STREET, RAMP_ON, HIGHWAY, RAMP_OFF}.",
        "maneuvers": "HIGHWAY-SPEED (vEgo > 20 m/s) LKAS-ENGAGED lateral manoeuvres. kind in "
                     "{lane_change, curve, wander}; lane_change = the angle departure reverses "
                     "sign. Sorted by load_proxy (severity) descending; `id` M00 = most severe.",
        "controls": "Straight-line highway-engaged windows, 1:1 matched to a manoeuvre on "
                    "duration and mean speed (see matched_to / v_gap). Non-overlapping with any "
                    "manoeuvre or with each other.",
        "lowspeed": "Low-speed episodes split by engagement (eng 1/0) over TWO bands, tagged by "
                    "`band`: '1-4' (the kit's creep band, asked for, but it yields ONE usable "
                    "engaged episode on this route -- the car crosses 1-4 m/s in ~2 s) and '1-8' "
                    "(84 s engaged / 93 s manual). Engagement runs are cut first, speed sub-runs "
                    "taken inside them. 🛑 EVERY manual low-speed episode is driver_active in "
                    "both bands, structurally -- with LKAS off at low speed the driver is the "
                    "steering input. Match on sustained effort inside any engaged-vs-manual "
                    "comparison or it measures the driver, not the firmware.",
    },
    "_fields": {
        "id": "stable episode id: M## manoeuvre, C## control, L### low-speed",
        "band": "low-speed list only: which LOW_BANDS band this episode was cut for.",
        "fits_window": "low-speed list only: dur >= 2.56 s, i.e. the episode can carry at least "
                       "one NFFT=256 window. A shorter episode is real but unanalysable.",
        "dur": "seconds", "n": "samples",
        "v_mean/v_p50/v_min/v_max": "vEgo m/s",
        "ang_p50/ang_p95/ang_peak": "|steering angle| deg (RAW, offset included)",
        "dev_p50/dev_p95/dev_peak": "|angle departure| deg -- use this, not ang_*",
        "dev_swing": "max(dev) - min(dev), deg -- the full excursion of a lane change",
        "dev_net": "end-minus-start departure, deg (~0 for a lane change, large for a curve)",
        "dev_signed_peak": "signed departure at the peak -- + / - is the turn direction",
        "rate_p50/rate_p95/rate_peak": "|rate_c| deg/s", "arate_peak": "|d(smoothed ang)/dt| deg/s",
        "tq_p50/tq_p95/tq_peak": "|driver torque| counts",
        "press_any/press_duty": "carState.steeringPressed",
        "load_proxy": "v_mean^2 * dev_peak / 1000 -- an ORDERING statistic proportional to lateral "
                      "acceleration under a bicycle model. The steering-ratio/wheelbase constant "
                      "is NOT asserted, so this is deg*(m/s)^2/1000, NOT m/s^2.",
        "driver_active": "true if steeringPressed > 10% of the episode or |driver torque| p50 > "
                         "500 counts. A manoeuvre the driver is muscling is a DIFFERENT "
                         "experiment from one openpilot drives alone -- do not pool them "
                         "silently.",
        "phase": "which drive phase the episode's midpoint falls in.",
        "phase_edge_s": "seconds from the episode to the nearest phase boundary. 🛑 M00, the most "
                        "severe manoeuvre on the route, sits 0.1 s from the RAMP_OFF boundary -- "
                        "it IS the freeway exit. Ranking by load_proxy and taking the top episode "
                        "as the exemplar of the operator's reported lane-change symptom would be "
                        "wrong; filter on phase_edge_s before doing that.",
        "peak_i / peak_seg / peak_t_seg / peak_t_rel": "the sharpest steering moment (argmax "
                                                       "|arate|), globally / in its segment / "
                                                       "seconds into the episode.",
        "core": "a 2.56 s (NFFT=256 at ~100 Hz) window centred on peak_i and clipped to the "
                "parent engaged+highway run -- for a burst-aligned FFT. Same {i0,i1,spans} "
                "convention as the episode itself.",
        "run_i0 / run_i1": "the contiguous engaged+highway run the episode lives inside. Any "
                           "window a consumer cuts must stay within these bounds.",
        "dur": "seconds, summed from the per-segment dt. NOT t[i1-1]-t[i0]: 3.3% of samples share "
               "a logMonoTime with their neighbour because one `can` event batches several 0x14A "
               "frames, so timestamp differences understate duration.",
        "illegal": "V67 probe decode faults inside the episode; must be 0.",
    },
    "_exposure": "seconds per (speed regime x engagement), a strict partition summing to the "
                 "route total. 🛑 HIGHWAY HAS ZERO MANUAL SECONDS -- openpilot was engaged for "
                 "all 821.6 s above 20 m/s, so 'engaged vs disengaged' is untestable at highway "
                 "speed on this route. Use maneuvers vs controls (within-engaged) instead. Creep "
                 "is 26.4 s engaged vs 83.2 s manual: thin, quote the CI and the split-half null.",
}


# ================================================================ main ==========================
def verify():
    """SECOND METHOD. Re-read the emitted JSON, slice the .npz files through `spans` ALONE -- no
    global array, no atlas code -- and recompute the covariates that do not depend on the running
    baseline. If a consumer following the documented schema gets different numbers from the ones
    in the file, the schema is wrong, and this kit has shipped wrong index bounds before.
    """
    doc = json.loads(OUTJSON.read_text())
    cache = {}

    def npz(s):
        if s not in cache:
            cache[s] = dict(np.load(CACHE / f"{PFX}{s}.npz").items())
        return cache[s]

    bad, n = [], 0
    for lst in ("maneuvers", "controls", "lowspeed"):
        for r in doc[lst]:
            v, ang, rate, tq, lat, dt = [], [], [], [], [], 0.0
            for sp in r["spans"]:
                z = npz(sp["seg"])
                a, b = sp["i0"], sp["i1"]
                assert abs(z["t"][a] - sp["t0"]) < 1e-3, (r["id"], "t0 mismatch")
                assert abs(z["t"][b - 1] - sp["t1"]) < 1e-3, (r["id"], "t1 mismatch")
                v.append(z["cs_v"][a:b]); ang.append(z["ang"][a:b])
                rate.append(z["rate_c"][a:b]); tq.append(z["cs_tq"][a:b])
                lat.append(z["cc_lat"][a:b])
                dt += (b - a) / (1.0 / float(np.median(np.diff(z["t"]))))
            v, ang, rate = np.concatenate(v), np.concatenate(ang), np.concatenate(rate)
            tq, lat = np.concatenate(tq), np.concatenate(lat)
            n += 1
            for name, got, want in (
                    ("n", len(v), r["n"]), ("dur", dt, r["dur"]),
                    ("v_mean", float(v.mean()), r["v_mean"]),
                    ("ang_peak", float(np.abs(ang).max()), r["ang_peak"]),
                    ("rate_peak", float(np.abs(rate).max()), r["rate_peak"]),
                    ("tq_p95", float(np.percentile(np.abs(tq), 95)), r["tq_p95"]),
                    ("lat_duty", float((lat > 0.5).mean()), r["lat_duty"])):
                if abs(got - want) > max(2e-2, 2e-3 * abs(want)):
                    bad.append(f"{r['id']}.{name}: npz-direct {got:.4f} vs json {want:.4f}")
    print(f"VERIFY: {n} episodes re-derived from the .npz files through `spans` alone, "
          f"7 covariates each ({7 * n} checks).")
    print("  -> ALL MATCH." if not bad else "  -> 🛑 MISMATCHES:\n     " + "\n     ".join(bad))
    return not bad


def main():
    if "--schema" in sys.argv:
        print(json.dumps(SCHEMA, indent=2))
        return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    d, meta, wall = load_all()
    fs = 1.0 / float(np.median(np.diff(d["t_mono"])))
    print(f"route 47: {len(d['t_mono'])} samples over {d['t_mono'][-1] - d['t_mono'][0]:.1f} s, "
          f"{len(meta)} segments, median fs {fs:.2f} Hz")
    print(f"WALL CLOCK: offset {wall['off']:.4f} s from {wall['nsync']}/{wall['ntot']} post-sync "
          f"clocks samples (sd {wall['sd']:.4f} s, drift {wall['drift_ppm']:+.1f} ppm). "
          f"{wall['ntot'] - wall['nsync']} STALE pre-NTP samples excluded -- all in segment 0.")
    print(f"            t=0 -> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d['t_wall'][0]))}"
          f" local")
    gaps = np.diff(d["t_mono"])
    print(f"CONTIGUITY: max inter-sample gap {gaps.max() * 1000:.1f} ms "
          f"({int((gaps > 0.06).sum())} gaps > 60 ms)")

    d["ang_s"] = boxcar2(d["ang"], int(SMOOTH_S * fs))
    d["base"] = running_median(d["ang"], d["t_mono"], BASE_HALF_S)
    d["dev"] = d["ang_s"] - d["base"]
    # 🛑 UNIFORM-GRID derivative. np.gradient(y, t_mono) divides by the zero dt of the 4,956
    # batch-duplicated timestamps and returns NaN. Sample spacing is the per-segment dt.
    d["arate"] = boxcar2(np.gradient(d["ang_s"]) / d["dt"], int(SMOOTH_S * fs))

    segrows = segment_table(d, meta, wall)
    ph = phases(d)
    mans = maneuvers(d, ph)
    ctrls = controls(d, mans, ph)
    lows = lowspeed(d, ph)
    exp = exposure(d, ph)

    print(f"\n{'=' * 132}\nHIGHWAY LATERAL MANOEUVRES  (vEgo > {V_STREET_HI:.0f} m/s AND "
          f"latActive; |dev| > {DEV_HI} deg or |arate| > {RATE_HI} deg/s, hysteresis to "
          f"{DEV_LO} deg, {MERGE_S} s merge)\n"
          f"ranked by load_proxy = v^2*dev_peak/1000 (ordering statistic, NOT m/s^2)\n{'=' * 132}")
    print(f"{'id':>4s} {'kind':>12s} {'phase':>8s} {'wall':>8s} {'sg':>3s} {'t_seg':>7s} "
          f"{'dur':>6s} {'vmean':>6s} | {'devpk':>6s} {'swing':>6s} {'net':>6s} | {'rpk':>5s} "
          f"{'arpk':>5s} | {'tq50':>5s} {'tq95':>5s} {'tqpk':>5s} {'DRV':>4s} | {'ccrq':>6s} "
          f"{'e4pk':>6s} | {'load':>6s}")
    for r in mans[:30]:
        sp = r["spans"][0]
        print(f"{r['id']:>4s} {r['kind']:>12s} {r['phase']:>8s} {r['wall_hms']:>8s} "
              f"{sp['seg']:3d} {sp['t0']:7.2f} {r['dur']:6.2f} {r['v_mean']:6.2f} | "
              f"{r['dev_peak']:6.2f} {r['dev_swing']:6.2f} {r['dev_net']:+6.2f} | "
              f"{r['rate_peak']:5.0f} {r['arate_peak']:5.1f} | "
              f"{r['tq_p50']:5.0f} {r['tq_p95']:5.0f} {r['tq_peak']:5.0f} "
              f"{'DRV' if r['driver_active'] else '.':>4s} | "
              f"{r['ccreq_peak']:6.3f} {r['e4tq_peak']:6.0f} | {r['load_proxy']:6.2f}")
    if len(mans) > 30:
        print(f"     ... {len(mans) - 30} more")
    nd = sum(r["driver_active"] for r in mans)
    print(f"\n{len(mans)} manoeuvres, {sum(r['dur'] for r in mans):.1f} s total. "
          f"{nd} are DRIVER-ACTIVE (steeringPressed > 10% or |tq| p50 > 500) and must not be "
          f"pooled with the {len(mans) - nd} openpilot-only ones without saying so. "
          f"By phase: " + ", ".join(f"{k}={sum(1 for r in mans if r['phase'] == k)}"
                                    for k in sorted({r['phase'] for r in mans})))
    print(f"Each carries `core`: a 2.56 s (NFFT=256) window centred on the sharpest steering "
          f"moment and clipped to its parent engaged+highway run -- use it for a burst-aligned "
          f"FFT, and `i0/i1` for the whole manoeuvre.")

    print(f"\n{'=' * 132}\nMATCHED STRAIGHT-CRUISE CONTROLS  (highway + latActive, |dev| < "
          f"{CTRL_DEV_MAX} deg and |arate| < {CTRL_RATE_MAX} deg/s throughout; "
          f"same duration, |dv| <= {CTRL_VTOL} m/s)\n{'=' * 132}")
    print(f"{'id':>4s} {'->man':>6s} {'wall':>8s} {'sg':>3s} {'t_seg':>7s} {'dur':>6s} "
          f"{'vmean':>6s} {'dv':>6s} | {'devpk':>6s} {'rpk':>5s} | {'tq50':>5s} {'tq95':>5s} | "
          f"{'ccrq':>6s} {'e4pk':>6s}")
    for r in ctrls[:30]:
        sp = r["spans"][0]
        print(f"{r['id']:>4s} {r['matched_to']:>6s} {r['wall_hms']:>8s} {sp['seg']:3d} "
              f"{sp['t0']:7.2f} {r['dur']:6.2f} {r['v_mean']:6.2f} {r['v_gap']:+6.2f} | "
              f"{r['dev_peak']:6.2f} {r['rate_peak']:5.0f} | {r['tq_p50']:5.0f} "
              f"{r['tq_p95']:5.0f} | {r['ccreq_peak']:6.3f} {r['e4tq_peak']:6.0f}")
    if len(ctrls) > 30:
        print(f"     ... {len(ctrls) - 30} more")
    ne, nc = len(mans), len(ctrls)
    if nc < ne:
        miss = [m["id"] for m in mans if m["id"] not in {c["matched_to"] for c in ctrls}]
        print(f"⚠ only {nc}/{ne} manoeuvres found a speed-matched, non-overlapping control at "
              f"|dv| <= {CTRL_VTOL} m/s. Unmatched: {', '.join(miss)}")
    else:
        print(f"all {ne} manoeuvres matched; control exposure {sum(c['dur'] for c in ctrls):.1f} s "
              f"vs manoeuvre {sum(m['dur'] for m in mans):.1f} s, "
              f"max |dv| {max(abs(c['v_gap']) for c in ctrls):.2f} m/s")

    for (lo, hi), (e, nm) in [(b, en) for b in LOW_BANDS for en in ((1, "ENGAGED"), (0, "MANUAL"))]:
        band = f"{lo:.0f}-{hi:.0f}"
        sub = [r for r in lows if r["eng"] == e and r["band"] == band]
        tot = sum(r["dur"] for r in sub)
        print(f"\n{'=' * 132}\nLOW-SPEED EPISODES  {band} m/s -- {nm}  "
              f"(>= {LOW_MIN_DUR_S} s): {len(sub)} episodes, {tot:.1f} s\n{'=' * 132}")
        print(f"{'id':>5s} {'phase':>11s} {'wall':>8s} {'sg':>3s} {'t_seg':>7s} {'dur':>6s} "
              f"{'vmean':>6s} | {'|a|p50':>6s} {'|a|p95':>6s} {'devpk':>6s} | {'rpk':>5s} | "
              f"{'tq50':>5s} {'tq95':>5s} {'prs%':>5s} {'DRV':>4s} | {'e4pk':>6s} {'sat%':>5s} "
              f"{'win':>4s}")
        for r in sub[:20]:
            sp = r["spans"][0]
            print(f"{r['id']:>5s} {r['phase']:>11s} {r['wall_hms']:>8s} {sp['seg']:3d} "
                  f"{sp['t0']:7.2f} {r['dur']:6.2f} {r['v_mean']:6.2f} | {r['ang_p50']:6.1f} "
                  f"{r['ang_p95']:6.1f} {r['dev_peak']:6.1f} | {r['rate_peak']:5.0f} | "
                  f"{r['tq_p50']:5.0f} {r['tq_p95']:5.0f} {100 * r['press_duty']:5.1f} "
                  f"{'DRV' if r['driver_active'] else '.':>4s} | {r['e4tq_peak']:6.0f} "
                  f"{100 * r['e4sat_duty']:5.1f} {'Y' if r['fits_window'] else '-':>4s}")
        if len(sub) > 20:
            print(f"      ... {len(sub) - 20} more")
        fw = [r for r in sub if r["fits_window"]]
        cl = [r for r in fw if not r["driver_active"]]
        print(f"  -> {len(fw)} of {len(sub)} are >= 2.56 s (one NFFT=256 window): "
              f"{sum(r['dur'] for r in fw):.1f} s. Of those, {len(cl)} are NOT driver-active: "
              f"{sum(r['dur'] for r in cl):.1f} s.")

    print(f"\n{'=' * 132}\n🛑 THE LOW-SPEED CONTRAST IS CONFOUNDED BY DRIVER TORQUE, IN BOTH "
          f"BANDS, AND THE CONFOUND IS STRUCTURAL\n{'=' * 132}")
    for lo, hi in LOW_BANDS:
        band = f"{lo:.0f}-{hi:.0f}"
        for e, nm in ((1, "engaged"), (0, " manual")):
            sub = [r for r in lows if r["eng"] == e and r["band"] == band and r["fits_window"]]
            drv = [r for r in sub if r["driver_active"]]
            print(f"   {band} m/s {nm}: {len(sub):2d} usable episodes, "
                  f"{sum(r['dur'] for r in sub):6.1f} s, of which {len(drv)} driver-active "
                  f"({sum(r['dur'] for r in drv):6.1f} s)")
    print("   EVERY manual low-speed episode on this route is driver-active, in every band. That "
          "is not\n   bad luck -- with LKAS off at low speed the driver IS the steering input, so "
          "a hands-light\n   manual arm cannot exist. Any engaged-vs-manual low-speed ratio "
          "therefore measures the DRIVER\n   unless it is matched on sustained effort (the kit's "
          "E_BINS convention) inside the comparison.\n   The 1-4 m/s band additionally has only "
          "ONE usable engaged episode; do not run it alone.")

    doc = dict(
        schema=SCHEMA,
        meta=dict(route="75604b0a432fdc89_00000047--3e0b6134c0", build="V67", tag="r47",
                  segments=sorted(meta), n_samples=len(d["t_mono"]), fs_median=round(fs, 3),
                  duration_s=round(float(d["t_mono"][-1] - d["t_mono"][0]), 2),
                  wall_offset=round(wall["off"], 4), wall_offset_sd=round(wall["sd"], 4),
                  wall_start=round(float(d["t_wall"][0]), 3),
                  wall_start_local=time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime(d["t_wall"][0])),
                  thresholds=dict(V_STOP=V_STOP, V_CREEP_HI=V_CREEP_HI, V_STREET_HI=V_STREET_HI,
                                  DEV_HI=DEV_HI, DEV_LO=DEV_LO, RATE_HI=RATE_HI, MERGE_S=MERGE_S,
                                  MIN_DUR_S=MIN_DUR_S, BASE_HALF_S=BASE_HALF_S,
                                  CTRL_DEV_MAX=CTRL_DEV_MAX, CTRL_RATE_MAX=CTRL_RATE_MAX,
                                  CTRL_VTOL=CTRL_VTOL, LOW_MIN_DUR_S=LOW_MIN_DUR_S),
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S")),
        segments=segrows, phases=ph, maneuvers=mans, controls=ctrls, lowspeed=lows, exposure=exp)
    if "--no-write" not in sys.argv:
        OUTJSON.write_text(json.dumps(doc, indent=1))
        print(f"\n-> {OUTJSON}  ({OUTJSON.stat().st_size / 1024:.0f} KB; "
              f"{len(ph)} phases, {len(mans)} manoeuvres, {len(ctrls)} controls, "
              f"{len(lows)} creep episodes)")


if __name__ == "__main__":
    main()
