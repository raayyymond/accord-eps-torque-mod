#!/usr/bin/env python3
"""analyze_r47_imu.py -- route 47 (V67) on the comma IMU, the kit's only EPS-independent witness.

Route 47 is the first CONDITIONAL-Kd drive: V67 makes the rate-lane x2 gain live only while the
firmware's own LKAS gate `gp-0x6806` is true. The operator reports grind #2 "mostly gone" at low
speed but a similar-feeling resonance appearing at HIGHWAY speed during lane changes / significant
turns, and only with LKAS engaged.

SECTIONS (select with argv, default all):
  rate     sample-rate table, the lattice fit, and whether the IMU grid breaks the CAN alias
  axis     which IMU axis is which VEHICLE axis, derived from the data, not assumed
  man      highway maneuver vs matched cruise -- does the chassis feel the highway resonance?
  ab       within-route g6806 A/B + the difference-in-differences against V65 (constant Kd)
  creep    low-speed band table, r47 by arm and versus r3a/r3b
  order    speed-dependence / wheel-order check on every line found
  hw       ★ the operator's highway report: V67's arm arithmetic + r47 vs r3b highway
  mode     same-or-different: r47 highway vs r3a/r3b creep (frequency, Q, axis loading)
  alias    can the IMU lattice break the CAN alias? measured, not assumed

Usage:  python analyze_r47_imu.py                # every section, ~25 min
        python analyze_r47_imu.py rate axis hw   # just those
Re-extract the caches first if they are missing (adds r47 to extract_imu_cache.py's tables):
        python extract_imu_cache.py r47          # 26 segments, ~40 s

🛑 TWO STRUCTURAL LIMITS OF THIS ROUTE, stated here so no table below is over-read:
  1. `g6806` == `cc_lat` in 99.983% of frames, so the within-route Kd A/B IS an engagement A/B.
  2. LKAS is engaged whenever the car MOVES, so the Kd=1 arm exists essentially only at a
     STANDSTILL: 34 s of gate-ON vs 92 s of gate-OFF overlap at 0.5-4 m/s, and none above 8 m/s.
  Route 47 therefore does NOT deliver the promised confound-free within-route dose A/B.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _r47_imu_lib as L  # noqa: E402

ROOT = HERE.parent
RNG = np.random.default_rng(20260802)
OUT = HERE / "_r47_imu_results.json"
RESULTS = {}

HIGHWAY = list(range(4, 18))        # segs 4-17: 22-34 m/s, LKAS engaged 100% of every frame
LOWSPD = [0, 18, 20, 22, 23, 24]    # parking lot / creep
STREET = [1, 2, 3, 19, 21]


# ==================================================================== 1. SAMPLE RATE ==============
def sec_rate():
    L.hdr("1. SAMPLE RATE AND THE LATTICE\n"
          "The dt MEAN and the dt MEDIAN disagree by ~1%: samples are DROPPED, not jittered. The\n"
          "MEDIAN is the hardware ODR; the MEAN is an artefact of the drops and must NOT be used as\n"
          "fs, because it would impose the wrong alias map.")
    print(f"  {'seg':>4s} | {'accel':>32s} | {'gyro':>32s}")
    print(f"  {'':>4s} | {'n':>5s} {'dt_med':>8s} {'1/med':>8s} {'ODRfit':>8s} | "
          f"{'n':>5s} {'dt_med':>8s} {'1/med':>8s} {'ODRfit':>8s} | {'fill':>6s} {'rms_us':>7s}")
    ra, rg, DA, DG, fills = [], [], [], [], []
    for s in L.SEGS["r47"]:
        d = L.load_imu("r47", s)
        if d is None or len(d["at"]) < 100:
            continue
        da, dg = np.diff(d["at"]), np.diff(d["gt"])
        _, oa, rmsa, _ = L.lattice(d["at"])
        _, og, _, _ = L.lattice(d["gt"])
        _, _, fill, _ = L.uniform(d["at"], d["ax"])
        ra.append(oa); rg.append(og); DA.append(da); DG.append(dg); fills.append(fill)
        print(f"  {s:4d} | {len(d['at']):5d} {1e3 * np.median(da):7.4f}m {1 / np.median(da):8.4f} "
              f"{oa:8.4f} | {len(d['gt']):5d} {1e3 * np.median(dg):7.4f}m {1 / np.median(dg):8.4f} "
              f"{og:8.4f} | {100 * fill:5.2f}% {1e6 * rmsa:7.1f}")
    DA, DG = np.concatenate(DA), np.concatenate(DG)
    ra, rg = np.array(ra), np.array(rg)
    print(f"\n  ROUTE-WIDE, n={len(DA) + 1} accel intervals")
    print(f"    accel  dt mean {1e3 * DA.mean():.4f} ms -> {1 / DA.mean():8.4f} Hz  "
          f"(the DROP-CONTAMINATED figure)")
    print(f"           dt med  {1e3 * np.median(DA):.4f} ms -> {1 / np.median(DA):8.4f} Hz  "
          f"(the HARDWARE ODR)")
    print(f"           dt sd {1e3 * DA.std():.4f} ms  p1 {1e3 * np.percentile(DA, 1):.4f}  "
          f"p99 {1e3 * np.percentile(DA, 99):.4f}  max {1e3 * DA.max():.3f} ms")
    print(f"           lattice ODR fit: mean {ra.mean():.5f} Hz  sd {ra.std():.5f}  "
          f"range {ra.min():.5f}..{ra.max():.5f}   spread {ra.max() - ra.min():.5f} Hz")
    print(f"           lattice fill {100 * np.mean(fills):.2f}%  "
          f"=> {100 * (1 - np.mean(fills)):.2f}% of lattice slots are DROPPED samples")
    print(f"    gyro   dt med  {1e3 * np.median(DG):.4f} ms -> {1 / np.median(DG):8.4f} Hz   "
          f"lattice ODR mean {rg.mean():.5f} sd {rg.std():.5f}")
    print(f"    gyro dt mean {1e3 * DG.mean():.4f} ms -> {1 / DG.mean():.4f} Hz "
          f"(gyro drops MORE often than accel: {100 * (1 - np.median(DG) / DG.mean()):.2f}% vs "
          f"{100 * (1 - np.median(DA) / DA.mean()):.2f}%)")

    print(f"\n  dt HISTOGRAM (accel, ms, top 12 by count):")
    vals, cnts = np.unique(np.round(DA * 1e3, 2), return_counts=True)
    for v, c in sorted(zip(vals, cnts), key=lambda q: -q[1])[:12]:
        print(f"      {v:8.2f} ms  n={c:7d}  ({100 * c / len(DA):5.2f}%)")
    print(f"  dt MODES (coarse, 1 ms bins): "
          + "  ".join(f"{v:.0f}ms x{c}" for v, c in
                      sorted(zip(*np.unique(np.round(DA * 1e3), return_counts=True)),
                             key=lambda q: -q[1])[:6]))

    # ---- the alias verdict ---------------------------------------------------------------------
    odr = float(ra.mean())
    sep = odr - 100.0
    print(f"\n  ---- ALIAS ----")
    print(f"  IMU hardware lattice {odr:.5f} Hz   CAN grid 100.000 Hz   separation "
          f"{sep:.4f} Hz PER ALIAS ORDER")
    print(f"  IMU Nyquist {odr / 2:.4f} Hz.  A line measured at f_obs is degenerate with:")
    for k in range(1, 4):
        print(f"      order {k}: {k * odr:.3f} +/- f_obs  ->  e.g. f_obs=45 Hz aliases with "
              f"{k * odr - 45:.2f} and {k * odr + 45:.2f} Hz")
    print(f"  Predicted (IMU - CAN) apparent peak shift by alias order:")
    for k, lab in ((0, "f < 50   (real, unaliased)"), (1, "50 < f < 100"), (-1, "100 < f < 150"),
                   (2, "150 < f < 200")):
        print(f"      {lab:28s} : {k * sep:+.4f} Hz")
    print(f"\n  🛑 The IMU rate is {sep:.3f} Hz from the CAN rate. IMU/CAN AGREEMENT THEREFORE DOES\n"
          f"     NOT RESOLVE THE ALIAS -- to read the order off a {sep:.3f} Hz shift the paired peak\n"
          f"     difference must be measured to sem << {sep / 3:.3f} Hz. `alias` below tests that;\n"
          f"     it is not assumed either way.")
    RESULTS["rate"] = dict(odr_accel=odr, odr_gyro=float(rg.mean()),
                           dt_mean_ms=float(1e3 * DA.mean()), dt_med_ms=float(1e3 * np.median(DA)),
                           spread=float(ra.max() - ra.min()), fill=float(np.mean(fills)),
                           separation=sep)
    return odr, float(rg.mean())


# ==================================================================== 2. AXIS ORIENTATION =========
def sec_axis(odr):
    L.hdr("2. AXIS ORIENTATION -- DERIVED FROM THE DATA, NOT ASSUMED\n"
          "A steering-driven torsional mode and a chassis/suspension mode load DIFFERENT axes, so\n"
          "the axis loading is diagnostic -- but only once each IMU axis is tied to a VEHICLE axis.\n"
          "Anchors: gravity (static), dv/dt (longitudinal), v*yawrate (lateral), steer (yaw).")
    accs, gs, lon, lat_, yaw = [], [], [], [], []
    for s in L.SEGS["r47"]:
        di, dc = L.load_imu("r47", s), L.load_can("r47", s)
        if di is None or dc is None or len(di["at"]) < 500:
            continue
        at = di["at"]
        v = L.lerp(at, dc["t"], dc["cs_v"])
        ang = L.lerp(at, dc["t"], dc["ang"])
        # low-pass everything to 2 Hz: these are rigid-body anchors, not vibration
        fs = odr
        def lp(x, fc=2.0):
            X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
            f = np.fft.rfftfreq(len(x), 1 / fs)
            X[f > fc] = 0
            return np.fft.irfft(X, n=len(x)) + np.mean(x)
        dv = np.gradient(lp(v, 1.0), at)                       # m/s^2 longitudinal
        # yaw rate from the bicycle model: steer angle / steer ratio / wheelbase * v
        yr = lp(ang, 1.0) * np.pi / 180.0 / 16.0 / 2.83 * v     # rad/s (sign per CAN convention)
        ay_pred = yr * v                                        # m/s^2 lateral
        accs.append([di[k].mean() for k in L.ACC])
        gs.append([di[k].mean() for k in L.GYR])
        lon.append([np.corrcoef(lp(di[k]), dv)[0, 1] for k in L.ACC])
        lat_.append([np.corrcoef(lp(di[k]), ay_pred)[0, 1] for k in L.ACC])
        gt = di["gt"]
        yr_g = np.interp(gt, at, yr)
        yaw.append([np.corrcoef(lp(di[k]), yr_g)[0, 1] for k in L.GYR])
    A, G = np.array(accs), np.array(gs)
    LO, LA, YW = np.array(lon), np.array(lat_), np.array(yaw)
    print(f"  STATIC (mean over {len(A)} segments) -- gravity picks the VERTICAL axis:")
    for i, k in enumerate(L.ACC):
        print(f"      {k}  mean {A[:, i].mean():+8.4f} m/s^2   |g| fraction "
              f"{abs(A[:, i].mean()) / 9.807:6.3f}")
    print(f"      |mean accel vector| = {np.linalg.norm(A.mean(0)):.4f} m/s^2 (gravity = 9.807)")
    for i, k in enumerate(L.GYR):
        print(f"      {k}  mean {G[:, i].mean():+9.5f} rad/s (bias)")
    print(f"\n  DYNAMIC correlations (median over segments, low-passed to 2 Hz):")
    print(f"      {'axis':>5s} {'vs dv/dt (LONG)':>17s} {'vs v*yawrate (LAT)':>19s}")
    for i, k in enumerate(L.ACC):
        print(f"      {k:>5s} {np.median(LO[:, i]):17.3f} {np.median(LA[:, i]):19.3f}")
    print(f"      {'axis':>5s} {'vs yaw rate':>17s}")
    for i, k in enumerate(L.GYR):
        print(f"      {k:>5s} {np.median(YW[:, i]):17.3f}")
    vert = L.ACC[int(np.argmax(np.abs(A.mean(0))))]
    long_ = L.ACC[int(np.argmax(np.abs(np.median(LO, 0))))]
    lat2 = L.ACC[int(np.argmax(np.abs(np.median(LA, 0))))]
    yaw_ = L.GYR[int(np.argmax(np.abs(np.median(YW, 0))))]
    print(f"\n  => VERTICAL ~ {vert}   LONGITUDINAL ~ {long_}   LATERAL ~ {lat2}   YAW ~ {yaw_}")
    print(f"  ⚠ The device is windshield-mounted and TILTED, so these are approximate body axes,\n"
          f"    not an orthogonal vehicle frame. Read the axis loading as 'which direction\n"
          f"    dominates', never as a calibrated projection.")
    RESULTS["axis"] = dict(vertical=vert, longitudinal=long_, lateral=lat2, yaw=yaw_,
                           gravity=[float(x) for x in A.mean(0)],
                           corr_long={k: float(np.median(LO[:, i])) for i, k in enumerate(L.ACC)},
                           corr_lat={k: float(np.median(LA[:, i])) for i, k in enumerate(L.ACC)},
                           corr_yaw={k: float(np.median(YW[:, i])) for i, k in enumerate(L.GYR)})
    return dict(vertical=vert, longitudinal=long_, lateral=lat2, yaw=yaw_)


# ==================================================================== EPISODE MACHINERY ===========
MAN_HI, MAN_LO, MAN_DIL, MIN_DUR = 1.0, 0.45, 0.4, 0.6


def maneuver_mask(dc, fs):
    """CAN-ONLY maneuver score. Deliberately never touches the IMU: the episodes are defined by the
    sensor that is NOT under test, so 'the IMU is loud where the IMU says it is loud' is impossible.

    score = max(|steer rate| / 2.5 deg/s, |steer angle deviation| / 1.0 deg)
    The angle is high-passed at 0.03 Hz first -- the sensor carries a ~4.5 deg standing offset on
    this car, so a raw bicycle-model lateral accel reads a constant 1.5 m/s^2 on a straight freeway
    and every episode qualifies. Confirmed on segs 4-17 before this detrend was added.
    """
    sr = np.abs(L.lowpass(dc["rate_c"], fs, 2.0) - np.median(dc["rate_c"]))
    ad = np.abs(dc["ang"] - L.lowpass(dc["ang"], fs, 0.03))
    return np.maximum(sr / 2.5, ad / 1.0)


def episodes_of(dc, fs, kind):
    """(a, b) index pairs on the CAN grid for 'man' (maneuvering) or 'cru' (straight cruise)."""
    ms = maneuver_mask(dc, fs)
    M = L.dilate(ms > MAN_HI, fs, MAN_DIL)
    if kind == "man":
        sel = M
    else:
        sel = (ms < MAN_LO) & ~L.dilate(M, fs, 0.8)
    return list(L.runs_of(sel, dc["t"], int(MIN_DUR * fs)))


def make_records(tag, segs, kind_fn, bands=None, axes=None, label=""):
    """One record per EPISODE per axis-band, carrying p95 / max / median of that band's envelope.

    `kind_fn(dc, fs) -> list of (name, t0, t1)` decides what an episode IS, so the same machinery
    serves the maneuver split, the g6806 arm split and the creep split without re-implementing the
    envelope path.
    """
    bands = bands or L.BANDS
    axes = axes or L.AXES
    out = []
    for s in segs:
        dc = L.load_can(tag, s)
        if dc is None or not L.have(tag, s):
            continue
        fs = 1.0 / np.median(np.diff(dc["t"]))
        E = L.imu_envelopes(tag, s, bands, axes)
        if E is None:
            continue
        cov = {c: L.can_on(E["t"][c], dc, fs) for c in ("a", "g")}
        for eid, (name, t0, t1) in enumerate(kind_fn(dc, fs)):
            r = dict(tag=tag, seg=int(s), kind=name, t0=float(t0), t1=float(t1),
                     dur=float(t1 - t0), ep=(tag, int(s), eid), label=label)
            ok = True
            for ax in axes:
                c = ax[0]
                m = (E["t"][c] >= t0) & (E["t"][c] <= t1)
                if m.sum() < 50:
                    ok = False
                    break
                for k in bands:
                    e = E[(ax, k)][m]
                    r[f"{ax}_{k}"] = float(np.percentile(e, 95))
                    r[f"{ax}_{k}_max"] = float(e.max())
                    r[f"{ax}_{k}_med"] = float(np.median(e))
                if c == "a":
                    for k in bands:                     # |a| magnitude across the 3 accel axes
                        v = np.sqrt(sum(E[(q, k)][m] ** 2 for q in L.ACC))
                        r[f"A_{k}"] = float(np.percentile(v, 95))
                        r[f"A_{k}_max"] = float(v.max())
                        r[f"A_{k}_med"] = float(np.median(v))
            if not ok:
                continue
            ma = (E["t"]["a"] >= t0) & (E["t"]["a"] <= t1)
            cv = cov["a"]
            r["v"] = float(np.mean(cv["v"][ma]))
            r["eff"] = float(np.mean(cv["eff"][ma]))
            r["angm"] = float(np.mean(cv["ang"][ma]))
            r["ratem"] = float(np.mean(cv["rate"][ma]))
            r["gate"] = float(np.mean(cv["gate"][ma]))
            r["lat"] = float(np.mean(cv["lat"][ma]))
            r["cell"] = (L.binof(r["v"], L.V_BINS), L.binof(r["eff"], L.E_BINS))
            r["blk"] = r["ep"]
            out.append(r)
    return out


COARSE_V = [(0.0, 2.0), (2.0, 4.0), (4.0, 10.0), (10.0, 20.0), (20.0, 99.0)]


def recell(rs, coarse):
    """Re-key the matching cell. `coarse` drops the effort axis and widens the speed bins.

    Used ONLY where the fine (speed x effort) cell leaves no jointly-occupied cell at all -- a
    coarse match that is honest about its width beats a `nan` that hides the imbalance. The speed
    distribution of both arms is printed alongside so the residual imbalance stays visible.
    """
    if not coarse:
        return rs
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = (L.binof(r["v"], COARSE_V),)
        out.append(q)
    return out


def band_table(A, B, nameA, nameB, axes, rng, fields=("", "_max", "_med"), bands=None,
               nboot=1500, note="", coarse=False, min_ep=2, min_win=5):
    """The kit's standard comparison: stratified episode-bootstrapped ratio per band per axis,
    quoted against that pool's OWN split-half null, with the MEAN(median) and the TAIL side by side.

    🛑 The mean and the tail have disagreed IN SIGN on this data, so both are always printed.
    """
    bands = bands or L.BORDER
    A, B = recell(A, coarse), recell(B, coarse)
    print(f"\n  {nameA}  (n_ep={len(L.episodes(A))})   vs   {nameB}  (n_ep={len(L.episodes(B))})"
          f"{('   ' + note) if note else ''}")
    print(f"    speed: A med {np.median([r['v'] for r in A]):.2f} "
          f"[{np.percentile([r['v'] for r in A], 10):.2f},"
          f"{np.percentile([r['v'] for r in A], 90):.2f}]  "
          f"B med {np.median([r['v'] for r in B]):.2f} "
          f"[{np.percentile([r['v'] for r in B], 10):.2f},"
          f"{np.percentile([r['v'] for r in B], 90):.2f}] m/s"
          f"{'   (COARSE cell: speed only)' if coarse else ''}")
    print(f"    {'axis':>4s} {'band':>6s} | {'p95 RATIO [95% CI]':>30s} | "
          f"{'max RATIO':>10s} | {'med RATIO':>10s} | {'split-half null':>24s} | {'v':>7s}")
    res = {}
    kw = dict(min_ep=min_ep, min_win=min_win)
    for ax in axes:
        for k in bands:
            row = []
            for suf in fields:
                f = f"{ax}_{k}{suf}"
                r, lo, hi, nc, na, nb, _ = L.cellwise(A, B, f, rng,
                                                      nboot=nboot if suf == "" else 0, **kw)
                row.append((r, lo, hi, nc))
            n0, nlo, nhi, nn = L.split_half_null(A + B, f"{ax}_{k}", rng, nrep=150, **kw)
            (r, lo, hi, nc) = row[0]
            verdict = ""
            if np.isfinite(r) and np.isfinite(nlo):
                verdict = "  <- OVER NULL" if (r > nhi or r < nlo) else ""
            print(f"    {ax:>4s} {k:>6s} | {r:8.3f}x [{lo:7.3f},{hi:7.3f}] c={nc:<2d} | "
                  f"{row[1][0]:9.3f}x | {row[2][0]:9.3f}x | "
                  f"{n0:6.3f}x [{nlo:6.3f},{nhi:6.3f}] | {nc:3d}c{verdict}")
            res[f"{ax}_{k}"] = dict(p95=row[0][:3], mx=row[1][0], med=row[2][0],
                                    null=(n0, nlo, nhi), ncell=nc)
    return res


# ==================================================================== 3. HIGHWAY MANEUVERS ========
def sec_man(ax_map):
    L.hdr("3. DOES THE CHASSIS FEEL THE HIGHWAY RESONANCE?\n"
          "Highway = segs 4-17 (22-34 m/s). LKAS is engaged in 100.00% of every frame there, so the\n"
          "Kd arm is CONSTANT across this comparison -- this section is purely maneuver vs cruise.\n"
          "Episodes are defined on CAN steering only; the IMU never votes on its own episodes.")

    def kf(dc, fs):
        out = []
        for a, b in episodes_of(dc, fs, "man"):
            out.append(("man", float(dc["t"][a]), float(dc["t"][b - 1])))
        for a, b in episodes_of(dc, fs, "cru"):
            out.append(("cru", float(dc["t"][a]), float(dc["t"][b - 1])))
        return out

    recs = make_records("r47", HIGHWAY, kf, label="hw")
    man = [r for r in recs if r["kind"] == "man"]
    cru = [r for r in recs if r["kind"] == "cru"]
    print(f"  MANEUVER episodes n={len(man)}  total {sum(r['dur'] for r in man):.0f} s  "
          f"median {np.median([r['dur'] for r in man]):.2f} s  "
          f"v {np.median([r['v'] for r in man]):.1f} m/s")
    print(f"  CRUISE   episodes n={len(cru)}  total {sum(r['dur'] for r in cru):.0f} s  "
          f"median {np.median([r['dur'] for r in cru]):.2f} s  "
          f"v {np.median([r['v'] for r in cru]):.1f} m/s")
    print(f"  driver effort: maneuver {np.median([r['eff'] for r in man]):.0f} vs "
          f"cruise {np.median([r['eff'] for r in cru]):.0f} counts   "
          f"(1-4 Hz is the validity check -- it SHOULD differ here, the driver IS steering)")
    r = band_table(man, cru, "r47 HIGHWAY MANEUVER", "r47 HIGHWAY STRAIGHT CRUISE",
                   L.AXES + ["A"], RNG,
                   note=f"[{ax_map['vertical']}=vert {ax_map['lateral']}=lat "
                        f"{ax_map['longitudinal']}=long {ax_map['yaw']}=yaw]")
    nz = norm_summary(r, L.AXES + ["A"], "HIGHWAY MANEUVER vs CRUISE, EXPOSURE-NORMALISED")
    print("\n  🛑 THE ANSWER TO 'DOES THE CHASSIS FEEL THE HIGHWAY RESONANCE DURING MANEUVERS'.\n"
          "  Raw, every band rises ~1.05-1.29x during maneuvers -- INCLUDING 1-4 Hz, which is the\n"
          "  driver/controller input band and must rise, because the driver IS steering. Once that\n"
          "  exposure is divided out, 40-49 Hz sits at ~0.76-1.00x: NO band-selective elevation on\n"
          "  ANY axis. So on the IMU, highway maneuvers do NOT produce a 40-49 Hz excess over\n"
          "  matched straight cruise. The whole spectrum simply lifts a little while steering.\n"
          "  ⚠ POWER: 152 maneuver vs 85 cruise episodes; the CIs here are tight and the split-half\n"
          "  null is ~[0.87,1.15], so this is a real null, not an underpowered one.")
    RESULTS["man"] = dict(n_man=len(man), n_cru=len(cru), table=r, norm=nz)
    return man, cru


# ==================================================================== 4. WHEEL ORDER ==============
def sec_order():
    L.hdr("4. SPEED DEPENDENCE / WHEEL-ORDER CHECK -- RUN BEFORE ANY 'NEW LINE' CLAIM\n"
          "Wheel circumference on this car is established at 2.073-2.088 m, so wheel order 1 is\n"
          "v / 2.08 Hz and order n is n*v / 2.08. This kit has ALREADY called a wheel order a\n"
          "firmware effect once (the '8.69 Hz line V56 introduced' was 0.489*v). A line that tracks\n"
          "speed as an integer order is TYRE/DRIVELINE, not the EPS, whatever else is true of it.")
    C = L.WHEEL_CIRC
    NF = 256
    vb = [(1.0, 3.0), (3.0, 6.0), (6.0, 10.0), (10.0, 14.0), (14.0, 20.0), (20.0, 24.0),
          (24.0, 27.0), (27.0, 29.0), (29.0, 31.0), (31.0, 32.5), (32.5, 40.0)]
    print(f"  {'v bin':>12s} {'v_med':>6s} {'K':>5s} | {'order1':>7s} {'order2':>7s} | "
          f"{'strongest prominent lines (f Hz : prominence : order f*C/v)':>60s}")
    tracks = {}
    for ax in ("az", "ax", "ay", "gx"):
        print(f"\n  --- axis {ax} ---")
        for lo, hi in vb:
            acc, K, vs = None, 0, []
            odr = 101.02
            for s in L.SEGS["r47"]:
                dc, di = L.load_can("r47", s), L.load_imu("r47", s)
                if dc is None or di is None or len(di["at"]) < 500:
                    continue
                t = di["at"] if ax[0] == "a" else di["gt"]
                u, odr, _, tu = L.uniform(t, di[ax])
                v = L.lerp(tu, dc["t"], dc["cs_v"])
                m = (v >= lo) & (v < hi)
                for a, b in L.runs_of(m, tu, NF):
                    for i in range(a, b - NF + 1, NF // 2):
                        P = L.periodogram(u[i:i + NF], odr, NF)
                        if P is None:
                            continue
                        acc = P if acc is None else acc + P
                        K += 1
                        vs.append(float(np.mean(v[i:i + NF])))
            if K < 10:
                continue
            P = acc / K
            f = np.fft.rfftfreq(NF, 1 / odr)
            vmed = float(np.median(vs))
            R = L.prom_spectrum(f, P)
            k = (f >= 4.0) & (f <= 49.5) & np.isfinite(R)
            idx = np.flatnonzero(k)[np.argsort(-R[k])[:4]]
            desc = "  ".join(f"{f[i]:5.1f}:{R[i]:4.1f}:o{f[i] * C / vmed:4.2f}" for i in idx)
            print(f"  {f'{lo:.0f}-{hi:.0f} m/s':>12s} {vmed:6.2f} {K:5d} | "
                  f"{vmed / C:7.2f} {2 * vmed / C:7.2f} | {desc}")
            tracks.setdefault(ax, []).append((vmed, [(float(f[i]), float(R[i])) for i in idx]))

    print(f"\n  ---- VERDICT 1: does the STRONGEST line track speed as an order? ----")
    print(f"  The single most prominent 4-49.5 Hz line per speed bin, v >= 20 m/s only. Below 20 m/s")
    print(f"  order 1 falls under ~10 Hz where the ratchet and road input live and the pick is not")
    print(f"  well determined -- including those bins was what made the first fit here nonsense.")
    ver = {}
    for ax, rows in tracks.items():
        pts = [(v, lines[0][0], lines[0][1]) for v, lines in rows if v >= 20]
        if len(pts) < 4:
            continue
        V = np.array([p[0] for p in pts]); F = np.array([p[1] for p in pts])
        kfit = float(np.sum(F * V / C) / np.sum((V / C) ** 2))
        r_ord = float(np.sqrt(np.mean((F - kfit * V / C) ** 2)))
        r_fix = float(np.sqrt(np.mean((F - F.mean()) ** 2)))
        sl = float(np.polyfit(V, F, 1)[0])
        print(f"    {ax}: n={len(pts)}  ORDER model k={kfit:.3f} rms={r_ord:.3f} Hz | "
              f"FIXED-f model rms={r_fix:.3f} Hz | free slope df/dv={sl:.4f} Hz/(m/s) "
              f"(order 1 predicts {1 / C:.4f})")
        print(f"       => {'WHEEL ORDER (tyre/driveline)' if r_ord < r_fix else 'FIXED FREQUENCY'}"
              f"   per-bin: " + "  ".join(f"v={v:.0f}:{f:.1f}Hz(o{f * C / v:.2f},p{p:.0f})"
                                          for v, f, p in pts))
        ver[ax] = dict(k=kfit, rms_order=r_ord, rms_fixed=r_fix, slope=sl,
                       pts=[(float(a), float(b), float(c)) for a, b, c in pts])

    print(f"\n  ---- VERDICT 2: prominence AT each predicted integer order ----")
    print(f"  🛑 THE ONE THAT MATTERS FOR GRIND #2: at highway speed, order 3 = 3v/{C} lands INSIDE")
    print(f"  40-49 Hz (v=28-34 m/s -> 40.4-49.0 Hz). Any 40-49 Hz 'highway resonance' must be")
    print(f"  cleared against order 3 before it can be attributed to the firmware.")
    NF2 = 512
    for ax in ("az", "ax", "ay", "gx"):
        print(f"\n  --- axis {ax} ---")
        print(f"    {'v bin':>10s} {'v':>6s} {'K':>4s} | " +
              " | ".join(f"{f'order {n}':>18s}" for n in (1, 2, 3)))
        for lo, hi in [(24.0, 27.0), (27.0, 29.0), (29.0, 31.0), (31.0, 32.5), (32.5, 40.0)]:
            acc, K, vs, odr = None, 0, [], 101.02
            for s in HIGHWAY:
                dc, di = L.load_can("r47", s), L.load_imu("r47", s)
                if dc is None or di is None or len(di["at"]) < 500:
                    continue
                t = di["at"] if ax[0] == "a" else di["gt"]
                u, odr, _, tu = L.uniform(t, di[ax])
                v = L.lerp(tu, dc["t"], dc["cs_v"])
                m = (v >= lo) & (v < hi)
                for a, b in L.runs_of(m, tu, NF2):
                    for i in range(a, b - NF2 + 1, NF2 // 2):
                        P = L.periodogram(u[i:i + NF2], odr, NF2)
                        if P is None:
                            continue
                        acc = P if acc is None else acc + P
                        K += 1
                        vs.append(float(np.mean(v[i:i + NF2])))
            if K < 6:
                continue
            P, f = acc / K, np.fft.rfftfreq(NF2, 1 / odr)
            R = L.prom_spectrum(f, P)
            vmed = float(np.median(vs))
            cells = []
            for n in (1, 2, 3):
                fo = n * vmed / C
                if fo > f[-1] - 1:
                    cells.append(f"{'> Nyquist':>18s}")
                    continue
                j = (np.abs(f - fo) <= 0.8) & np.isfinite(R)
                pr = float(np.nanmax(R[j])) if j.any() else np.nan
                fp = float(f[np.flatnonzero(j)[np.nanargmax(R[j])]]) if j.any() else np.nan
                cells.append(f"{fo:6.2f}Hz p={pr:5.1f}@{fp:5.1f}")
            print(f"    {f'{lo:.0f}-{hi:.0f}':>10s} {vmed:6.2f} {K:4d} | " + " | ".join(cells))
    RESULTS["order"] = dict(tracks={a: [(v, l) for v, l in r] for a, r in tracks.items()},
                            verdict=ver)


# ==================================================================== 5. THE Kd A/B ===============
BLK = 10.0          # seconds; the bootstrap unit inside a long engagement run


def arm_kf(maskkey, blk=BLK):
    """Episodes = ~10 s blocks nested inside contiguous runs of the arm mask.

    A whole engagement run here is 30-600 s, which leaves as few as 5 resampling units and a
    degenerate split-half null. 10 s is still far longer than the 1-3 s burst autocorrelation, so
    it does not manufacture significance.
    """
    def kf(dc, fs):
        m = dc[maskkey] > 0.5 if maskkey in dc else dc["cc_lat"] > 0.5
        out = []
        for name, sel in (("on", m), ("off", ~m)):
            for a, b in L.runs_of(sel, dc["t"], int(1.0 * fs)):
                t0, t1 = dc["t"][a], dc["t"][b - 1]
                n = max(1, int(round((t1 - t0) / blk)))
                edges = np.linspace(t0, t1, n + 1)
                for i in range(n):
                    if edges[i + 1] - edges[i] >= 0.6:
                        out.append((name, float(edges[i]), float(edges[i + 1])))
        return out
    return kf


def exposure(tag, maskkey):
    """Seconds in each (arm, speed bin). This table decides whether the A/B is answerable AT ALL."""
    vb = [("v<0.5", 0.0, 0.5), ("0.5-2", 0.5, 2.0), ("2-4", 2.0, 4.0), ("4-8", 4.0, 8.0),
          ("8-14", 8.0, 14.0), ("14-22", 14.0, 22.0), ("22+", 22.0, 99.0)]
    tot = {}
    for s in L.SEGS[tag]:
        d = L.load_can(tag, s)
        if d is None:
            continue
        dt = float(np.median(np.diff(d["t"])))
        g = (d[maskkey] if maskkey in d else d["cc_lat"]) > 0.5
        for nm, m in (("on", g), ("off", ~g)):
            for lab, lo, hi in vb:
                k = (nm, lab)
                tot[k] = tot.get(k, 0.0) + float(((d["cs_v"] >= lo) & (d["cs_v"] < hi) & m).sum()) * dt
    print(f"    {'speed':>8s} {'arm ON':>12s} {'arm OFF':>12s}   usable?")
    usable = []
    for lab, lo, hi in vb:
        a, b = tot.get(("on", lab), 0.0), tot.get(("off", lab), 0.0)
        u = "BOTH" if min(a, b) >= 20 else ("thin" if min(a, b) >= 5 else "--")
        if min(a, b) >= 5:
            usable.append((lo, hi))
        print(f"    {lab:>8s} {a:11.1f}s {b:11.1f}s   {u}")
    return tot, usable


def sec_ab(amap):
    L.hdr("5. WITHIN-ROUTE Kd A/B ON THE IMU  --  TWO CONFOUNDS, ONE OF THEM FATAL\n"
          "🛑 CONFOUND 1 (engagement). `g6806` == `cc_lat` in 150,302/150,327 frames (99.983%).\n"
          "   V67 gates Kd on the firmware's LKAS gate and that gate IS LKAS engagement, so a raw\n"
          "   arm ratio measures (Kd effect x engagement effect). Answerable by difference-in-\n"
          "   differences against V65, where the same split exists at CONSTANT Kd=2.\n"
          "🛑 CONFOUND 2 (speed) -- THE FATAL ONE. On this route LKAS is engaged whenever the car is\n"
          "   MOVING. The Kd=1 arm therefore exists almost only at a STANDSTILL. The exposure table\n"
          "   below is the actual answer to 'does route 47 contain both doses': it contains both,\n"
          "   but not at the same speed, so the promised within-route A/B is structurally\n"
          "   underpowered rather than merely noisy.")
    axes = ["ay", "az", "ax", "gx", "A"]
    print("\n  r47 EXPOSURE BY ARM AND SPEED (the gate is the firmware's own bit):")
    _, usable = exposure("r47", "g6806")
    print("\n  V65 r3a EXPOSURE (engagement split at constant Kd=2):")
    exposure("r3a", "cc_lat")
    print("\n  V65 r3b EXPOSURE:")
    exposure("r3b", "cc_lat")

    VLO, VHI, BL = 0.5, 4.0, 4.0
    print(f"\n  => The ONLY speed band with both r47 arms is {VLO}-{VHI} m/s. Everything below is\n"
          f"     restricted to it, with {BL:.0f} s bootstrap blocks (10 s leaves ~3 vs ~9 units and a\n"
          f"     degenerate null). Expect wide intervals; that is the honest power of this design.")

    def sub(rs):
        return [r for r in rs if VLO <= r["v"] < VHI]

    r47 = make_records("r47", L.SEGS["r47"], arm_kf("g6806", BL), label="r47")
    on47, off47 = sub([r for r in r47 if r["kind"] == "on"]), sub([r for r in r47 if r["kind"] == "off"])
    print(f"\n  r47 {VLO}-{VHI} m/s: gate ON n={len(on47)}  gate OFF n={len(off47)}")
    if len(on47) < 4 or len(off47) < 4:
        print("  ⇒ TOO FEW EPISODES. The within-route A/B is NOT ANSWERABLE on route 47.")
        RESULTS["ab"] = dict(answerable=False, n_on=len(on47), n_off=len(off47))
        return None, None, None, None
    ta = band_table(on47, off47, f"r47 gate ON (Kd=2) {VLO}-{VHI} m/s",
                    f"r47 gate OFF (Kd=1) {VLO}-{VHI} m/s", axes, RNG,
                    note="CONFOUNDED with engagement; UNDERPOWERED",
                    coarse=True, min_ep=3, min_win=3)

    v65 = []
    for tg in ("r3a", "r3b"):
        v65 += make_records(tg, L.SEGS[tg], arm_kf("cc_lat", BL), label=tg)
    on65, off65 = sub([r for r in v65 if r["kind"] == "on"]), sub([r for r in v65 if r["kind"] == "off"])
    print(f"\n  V65 {VLO}-{VHI} m/s: lat ON n={len(on65)}  lat OFF n={len(off65)}")
    tb = band_table(on65, off65, f"V65 lat ON (Kd=2) {VLO}-{VHI} m/s",
                    f"V65 lat OFF (Kd=2) {VLO}-{VHI} m/s", axes, RNG,
                    note="PURE ENGAGEMENT term -- Kd is 2 on BOTH sides",
                    coarse=True, min_ep=3, min_win=3)

    print(f"\n  ---- DIFFERENCE-IN-DIFFERENCES:  (r47 ON/OFF) / (V65 ON/OFF)  ----")
    print(f"  Kd is the ONLY term that differs between the two arm ratios, so the quotient is the")
    print(f"  Kd effect with the engagement effect divided out. ⚠ It is still a CROSS-ROUTE")
    print(f"  quantity: different roads, different speeds, different days. Read it as a direction")
    print(f"  and an order of magnitude, not a calibrated gain.")
    print(f"    {'axis':>4s} {'band':>6s} | {'r47 arm':>9s} | {'V65 arm':>9s} | {'DiD':>9s} | "
          f"{'V65 null':>20s}")
    did = {}
    for ax in axes:
        for k in L.BORDER:
            a = ta.get(f"{ax}_{k}", {}).get("p95", (np.nan,))[0]
            b = tb.get(f"{ax}_{k}", {}).get("p95", (np.nan,))[0]
            n = tb.get(f"{ax}_{k}", {}).get("null", (np.nan, np.nan, np.nan))
            if not (np.isfinite(a) and np.isfinite(b)):
                continue
            did[f"{ax}_{k}"] = a / b
            print(f"    {ax:>4s} {k:>6s} | {a:8.3f}x | {b:8.3f}x | {a / b:8.3f}x | "
                  f"{n[0]:5.2f}x [{n[1]:5.2f},{n[2]:5.2f}]")
    RESULTS["ab"] = dict(r47=ta, v65=tb, did=did,
                         n=dict(on47=len(on47), off47=len(off47), on65=len(on65),
                                off65=len(off65)))
    return on47, off47, on65, off65


# ==================================================================== 6. LOW SPEED ================
def sec_creep(amap):
    L.hdr("6. LOW SPEED -- WHERE GRIND #2 WAS ORIGINALLY DEMONSTRATED\n"
          "Creep = v < 4 m/s. r47 has both arms here (segs 0/18/20/22/23 are mixed), which is the\n"
          "ONLY place on the route where the gate actually toggles -- segs 4-17 are 100% engaged.\n"
          "🛑 The confound above still applies to the r47 arm split; the V65 comparison is the\n"
          "cross-build reading and carries the usual route/exposure noise.")
    axes = ["ay", "az", "ax", "gx", "A"]
    BL = 4.0
    r47 = [r for r in make_records("r47", L.SEGS["r47"], arm_kf("g6806", BL), label="r47")
           if r["v"] < 4.0]
    on47 = [r for r in r47 if r["kind"] == "on"]
    off47 = [r for r in r47 if r["kind"] == "off"]
    print(f"  r47 creep ({BL:.0f} s blocks): gate ON n={len(on47)}  gate OFF n={len(off47)}")
    print(f"  ⚠ EXPOSURE. Route 47 is a HIGHWAY route: only ~36 s of it is engaged creep, against\n"
          f"    819 s of engaged highway. The operator's 'low-speed grind #2 might just be dampened'\n"
          f"    is therefore NOT settleable from this route, whatever the tables below say -- there\n"
          f"    is not enough engaged creep on it to measure a 2.2x noise floor against.")
    if len(on47) >= 5 and len(off47) >= 5:
        band_table(on47, off47, "r47 CREEP gate ON (Kd=2)", "r47 CREEP gate OFF (Kd=1)",
                   axes, RNG, note="within-route, CONFOUNDED with engagement",
                   coarse=True, min_ep=3, min_win=3)

    v65 = []
    for tg in ("r3a", "r3b"):
        v65 += make_records(tg, L.SEGS[tg], arm_kf("cc_lat", BL), label=tg)
    on65 = [r for r in v65 if r["kind"] == "on" and r["v"] < 4.0]
    print(f"\n  V65 creep engaged n={len(on65)}   r47 creep gate-ON n={len(on47)}")
    tc = None
    if len(on47) >= 5 and len(on65) >= 5:
        tc = band_table(on47, on65, "r47 CREEP engaged (V67)",
                        "V65 CREEP engaged (r3a+r3b, Kd=2)", axes, RNG,
                        note="both engaged; V67 is 1.71-1.86x here vs V65's 2.00x -- cross-route",
                        coarse=True, min_ep=3, min_win=3)
        norm_summary(tc, axes, "r47 CREEP vs V65 CREEP, EXPOSURE-NORMALISED")
    else:
        print("  ⇒ too few episodes on one side; creep comparison NOT ANSWERABLE from route 47.")
    RESULTS["creep"] = dict(v67_vs_v65=tc, n=dict(on47=len(on47), off47=len(off47),
                                                  on65=len(on65)))
    return on47, off47, on65


# ==================================================================== 7. CROSS-BUILD HIGHWAY ======
def speed_kf(vlo, vhi, blk=BLK, need_lat=True):
    def kf(dc, fs):
        m = dc["cs_v"] >= vlo
        m &= dc["cs_v"] < vhi
        if need_lat:
            m &= (dc["g6806"] if "g6806" in dc else dc["cc_lat"]) > 0.5
        out = []
        for a, b in L.runs_of(m, dc["t"], int(1.0 * fs)):
            t0, t1 = dc["t"][a], dc["t"][b - 1]
            n = max(1, int(round((t1 - t0) / blk)))
            e = np.linspace(t0, t1, n + 1)
            for i in range(n):
                if e[i + 1] - e[i] >= 0.6:
                    out.append(("w", float(e[i]), float(e[i + 1])))
        return out
    return kf


def sec_hw(amap):
    L.hdr("7. THE OPERATOR'S HIGHWAY REPORT -- THE ONLY TEST THAT CAN ADDRESS IT\n"
          "🛑 THE ARITHMETIC FIRST. V67's arm is a SCALAR (cal 0xC6446 = 5244) replacing a mode-10\n"
          "LERP that RISES with speed, so the delivered multiplier is NOT V62/V65's flat 2.00x --\n"
          "recomputed here from v66_v67_explained.r24_gain_q10, not quoted from a docstring.")
    try:
        import v66_v67_explained as M
        ARM = 5244
        print(f"    {'km/h':>7s} {'speed_cts':>10s} {'stock LERP':>11s} {'V67 arm/LERP':>13s}")
        mult = {}
        for sc, kmh in [(0, 0.0), (460, 7.2), (640, 10.0), (1280, 20.0), (1920, 30.0),
                        (3200, 50.0), (4480, 70.0), (5760, 90.0), (6400, 100.0), (7040, 110.0)]:
            g = M.r24_gain_q10(sc, 128, 0, 0, 0)
            mult[kmh] = ARM / g
            print(f"    {kmh:7.1f} {sc:10d} {g:11.0f} {ARM / g:12.2f}x")
        print(f"\n  => V67 delivers {mult[7.2]:.2f}x at grind #1's 7.2 km/h design point but "
              f"{mult[90.0]:.2f}-{mult[110.0]:.2f}x at 90-110 km/h,")
        print(f"     where V62/V65's `sar 0x9` delivered a FLAT 2.00x. So at highway V67 runs about "
              f"{mult[100.0] / 2.0:.2f}x MORE")
        print(f"     rate-lane gain than V65 did. This is a real, pre-documented residual "
              f"(build_v67_tva.py lines 112-115),")
        print(f"     and it is ONE HALFWORD to retune. ⚠ the docstring says 'about 2.7x at road "
              f"speed'; recomputed it is")
        print(f"     {mult[100.0]:.2f}x at 100 km/h -- same direction, smaller magnitude.")
        RESULTS["v67_multiplier"] = {str(k): float(v) for k, v in mult.items()}
    except Exception as e:
        print(f"  (could not recompute the arm multiplier: {e})")

    print(f"\n  THE MEASUREMENT. r3b (V65, flat Kd=2.00) has 181 s of ENGAGED driving at v >= 22 m/s;\n"
          f"  r47 (V67) has 819 s. Both arms are LKAS-engaged, so engagement is matched and the only\n"
          f"  rate-lane difference is 2.00x vs ~2.4x. Speed is capped at 29 m/s -- r3b's maximum --\n"
          f"  so the comparison is inside a common speed range rather than across one.")
    axes = ["ay", "az", "ax", "gx", "A"]
    VLO, VHI = 22.0, 29.0
    a47 = make_records("r47", HIGHWAY, speed_kf(VLO, VHI), label="r47hw")
    a3b = make_records("r3b", L.SEGS["r3b"], speed_kf(VLO, VHI), label="r3bhw")
    print(f"\n  r47 {VLO}-{VHI} m/s engaged: n={len(a47)} episodes   "
          f"r3b: n={len(a3b)} episodes")
    if len(a47) < 4 or len(a3b) < 4:
        print("  ⇒ too few episodes; cross-build highway test NOT ANSWERABLE.")
        RESULTS["hw"] = dict(answerable=False)
        return
    th = band_table(a47, a3b, f"r47 HIGHWAY {VLO}-{VHI} m/s (V67, ~2.4x)",
                    f"r3b HIGHWAY {VLO}-{VHI} m/s (V65, 2.00x)", axes, RNG,
                    coarse=True, min_ep=3, min_win=3,
                    note="cross-route: different road/day, read with the null")

    print(f"\n  MID-SPEED 3-DOSE LADDER (14-22 m/s, engaged): V59/r2c is Kd=1, V65/r3b is Kd=2.00,\n"
          f"  V67/r47 is ~2.1x there. If the rate lane drives the band, the ordering should follow.")
    b47 = make_records("r47", L.SEGS["r47"], speed_kf(14.0, 22.0), label="r47m")
    b3b = make_records("r3b", L.SEGS["r3b"], speed_kf(14.0, 22.0), label="r3bm")
    b2c = make_records("r2c", L.SEGS["r2c"], speed_kf(14.0, 22.0), label="r2cm")
    print(f"    r47 n={len(b47)}  r3b n={len(b3b)}  r2c(Kd=1) n={len(b2c)}")
    if len(b2c) >= 4 and len(b47) >= 4:
        band_table(b47, b2c, "r47 14-22 m/s (V67 ~2.1x)", "r2c 14-22 m/s (V59 Kd=1)", axes, RNG,
                   coarse=True, min_ep=3, min_win=3, note="dose 2.1 vs 1")
    if len(b3b) >= 4 and len(b2c) >= 4:
        band_table(b3b, b2c, "r3b 14-22 m/s (V65 Kd=2.00)", "r2c 14-22 m/s (V59 Kd=1)", axes, RNG,
                   coarse=True, min_ep=3, min_win=3, note="dose 2.0 vs 1 -- the reference rung")
    nz = norm_summary(th, axes, "r47 HIGHWAY vs r3b HIGHWAY, EXPOSURE-NORMALISED")
    print("\n  🛑 HOW TO READ THIS, AND THE ALTERNATIVE THAT SURVIVES.\n"
          "  Every RAW band ratio is < 1 because r47's highway was a smoother road (1-4 Hz is\n"
          "  0.47-0.65x). Normalised by that exposure the picture is NOT a 40-49 Hz peak -- it is a\n"
          "  MONOTONE TILT: the ratio rises with frequency on every axis, reaching 2.0-2.3x at\n"
          "  40-49 Hz. A rate-lane gain increase does produce exactly that shape (the lane is a\n"
          "  4-sample finite difference, so its gain rises with frequency).\n"
          "  ⚠ BUT SO DOES PAVEMENT. Coarse surface texture drives high frequency while large-scale\n"
          "  roughness drives low frequency, and the two differ independently between roads. The\n"
          "  axis loading does not break the tie: the tilt is LARGEST on ax (VERTICAL, 2.32x), which\n"
          "  is where tyre/road input loads, and SMALLEST on az. A steering-driven torsional mode\n"
          "  should have favoured lateral/yaw. Raw and normalised also disagree about which axis\n"
          "  leads (raw: ay; normalised: ax), which is itself a sign the normalisation is carrying\n"
          "  the result. ⇒ SUGGESTIVE, NOT ESTABLISHED. The clean test is a same-road V65/V67\n"
          "  highway A/B, which route 47 cannot supply because it is 100% engaged above 22 m/s.")
    print("\n  ---- ROBUSTNESS: the 30-49 / 1-4 Hz TILT, PER SEGMENT ----")
    print("  One pooled ratio can be one bad stretch of road. If the tilt is real it should hold")
    print("  across INDEPENDENT segments (different miles of highway), not just in the pool.")
    tilt = {}
    for lab, recs in (("r47 (V67)", a47), ("r3b (V65)", a3b)):
        by = {}
        for r in recs:
            if r["A_1-4"] > 0:
                by.setdefault(r["seg"], []).append(r["A_30-49"] / r["A_1-4"])
        segs_ = sorted(by)
        vals = [float(np.median(by[s])) for s in segs_]
        print(f"    {lab:>10s} n_seg={len(segs_):2d}  median tilt {np.median(vals):.4f}  "
              f"range {min(vals):.4f}..{max(vals):.4f}")
        print(f"       per-seg: " + "  ".join(f"s{s}:{v:.3f}" for s, v in zip(segs_, vals)))
        tilt[lab] = vals
    if len(tilt) == 2:
        a, b = tilt["r47 (V67)"], tilt["r3b (V65)"]
        try:
            from scipy.stats import mannwhitneyu
            u, p = mannwhitneyu(a, b, alternative="two-sided")
            print(f"\n    Mann-Whitney over segments: U={u:.0f}  p={p:.4f}  "
                  f"(r47 median {np.median(a):.3f} vs r3b {np.median(b):.3f} "
                  f"= {np.median(a) / np.median(b):.2f}x)")
        except Exception:
            pass
        print(f"    🛑 DO NOT READ THAT p AS A BUILD COMPARISON. All 11 r47 segments are ONE trip on\n"
              f"    ONE road, and all 5 r3b segments are another; segments within a route share road\n"
              f"    type, tyres, temperature and load, so they are pseudo-replicates. The effective n\n"
              f"    for 'does the BUILD differ' is 2 ROUTES, not 16 segments. This is the same error\n"
              f"    the kit already made one level down (windows vs episodes), one level up.")
    RESULTS["hw"] = dict(answerable=True, table=th, norm=nz, n47=len(a47), n3b=len(a3b))


def norm_summary(tab, axes, title):
    """Each band's ratio DIVIDED BY that comparison's own 1-4 Hz ratio.

    🛑 THE MOST IMPORTANT COLUMN IN THIS FILE. A cross-route ratio carries the road: a smoother
    highway lowers EVERY band together. 1-4 Hz is driver/road input and carries no EPS mode, so it
    is the exposure yardstick. Only a band that moves RELATIVE to 1-4 Hz is a candidate firmware
    effect. On the r47-vs-r3b highway table the raw ratios are all < 1 (smoother road) and this
    normalisation is what reveals 40-49 Hz going the OTHER way.
    """
    print(f"\n  ---- {title}: band ratio / (that axis's own 1-4 Hz ratio) ----")
    print(f"    {'axis':>4s} | {'1-4 (exposure)':>15s} | " +
          " ".join(f"{b:>9s}" for b in L.BORDER[1:]))
    out = {}
    for ax in axes:
        base = tab.get(f"{ax}_1-4", {}).get("p95", (np.nan,))[0]
        if not np.isfinite(base) or base <= 0:
            continue
        cells = []
        for b in L.BORDER[1:]:
            r = tab.get(f"{ax}_{b}", {}).get("p95", (np.nan,))[0]
            cells.append(f"{r / base:8.2f}x" if np.isfinite(r) else "     --  ")
            out[f"{ax}_{b}"] = float(r / base) if np.isfinite(r) else None
        print(f"    {ax:>4s} | {base:14.3f}x | " + " ".join(f"{c:>9s}" for c in cells))
    return out


# ==================================================================== 8. SAME MODE? ===============
NFB = 256          # 2.53 s on the IMU lattice, 0.395 Hz bins -- matches the kit's CAN standard


def bursts_of(tag, segs, band, kfsel, thr_pct=90.0, ax="ay", nfft=NFB):
    """Top-amplitude WINDOWS of a pool, with peak frequency, prominence, Q and excursion width.

    🛑 NOT envelope-threshold runs. A 30-49 Hz band is 19 Hz WIDE, so its analytic envelope
    fluctuates on ~1/19 s and an excursion above any useful threshold lasts ~0.05 s = 2 carrier
    cycles. Measured directly: p95/0.15 s gave 1 burst on 819 s of highway and p99/0.15 s gave 0.
    Burst DURATION is therefore not identifiable in this band, and fixed windows are used instead
    so both pools are measured with the same instrument. `wid` below is the mean excursion width
    above the pool's own median and is reported ONLY as a shape statistic, not as a burst length.
    """
    lo, hi = L.BANDS[band]
    recs, pool = [], []
    for s in segs:
        dc, di = L.load_can(tag, s), L.load_imu(tag, s)
        if dc is None or di is None or len(di["at"]) < 500:
            continue
        fs = 1.0 / np.median(np.diff(dc["t"]))
        t = di["at"] if ax[0] == "a" else di["gt"]
        u, odr, _, tu = L.uniform(t, di[ax])
        e = L.env_full(u, odr, lo, hi)
        sel = kfsel(dc, fs, tu)
        if sel is None or sel.sum() < nfft:
            continue
        for a, b in L.runs_of(sel, tu, nfft):
            for i in range(a, b - nfft + 1, nfft // 2):
                amp = float(np.percentile(e[i:i + nfft], 95))
                recs.append((s, i, u, odr, tu, e, amp))
                pool.append(amp)
    if not recs:
        return []
    thr = float(np.percentile(pool, thr_pct))
    out = []
    for s, i, u, odr, tu, e, amp in recs:
        if amp < thr:
            continue
        P = L.periodogram(u[i:i + nfft], odr, nfft)
        if P is None:
            continue
        f = np.fft.rfftfreq(nfft, 1 / odr)
        f0, pr = L.locate(f, P, lo, hi)
        w = e[i:i + nfft]
        m = w > np.median(w)
        wid = float(np.mean([b_ - a_ for a_, b_ in L.runs_of(m, tu[i:i + nfft], 1)]) / odr) \
            if m.any() else np.nan
        out.append(dict(seg=int(s), t=float(tu[i]), f0=f0, prom=pr,
                        Q=L.q_of(f, P, f0), amp=amp, wid=wid))
    return out


def sec_mode(amap):
    L.hdr("8. IS THE HIGHWAY 40-49 Hz THE SAME MODE AS THE CREEP GRIND #2?\n"
          "Compared on peak frequency, Q, burst duration and axis loading. 🛑 Frequency is compared\n"
          "under a KNOWN alias ambiguity (both pools inherit the same one), so a MATCH means 'same\n"
          "apparent frequency', not 'same true frequency'. A MISMATCH is the stronger inference.")

    def hw_sel(dc, fs, tu):
        v = L.lerp(tu, dc["t"], dc["cs_v"])
        g = L.hold(tu, dc["t"], dc["g6806"] if "g6806" in dc else dc["cc_lat"])
        return (v >= 22.0) & (g > 0.5)

    def creep_sel(dc, fs, tu):
        v = L.lerp(tu, dc["t"], dc["cs_v"])
        g = L.hold(tu, dc["t"], dc["cc_lat"])
        return (v < 4.0) & (g > 0.5)

    rows = {}
    for lab, tag, segs, sel, ax in (
            ("r47 HIGHWAY (V67, engaged, v>=22)", "r47", HIGHWAY, hw_sel, "ay"),
            ("r3a CREEP (V65, engaged, v<4)", "r3a", L.SEGS["r3a"], creep_sel, "ay"),
            ("r3b CREEP (V65, engaged, v<4)", "r3b", L.SEGS["r3b"], creep_sel, "ay")):
        b = bursts_of(tag, segs, "30-49", sel, ax=ax)
        rows[lab] = b
        if not b:
            print(f"  {lab}: no bursts")
            continue
        f0 = np.array([r["f0"] for r in b], float)
        Q = np.array([r["Q"] for r in b], float)
        PR = np.array([r["prom"] for r in b], float)
        W = np.array([r["wid"] for r in b], float)
        f0, Q, PR, W = (x[np.isfinite(x)] for x in (f0, Q, PR, W))
        print(f"\n  {lab}   n_windows(top decile)={len(b)}")
        print(f"     peak f      med {np.median(f0):6.2f} Hz  IQR "
              f"[{np.percentile(f0, 25):.2f},{np.percentile(f0, 75):.2f}]  "
              f"sd {f0.std(ddof=1) if len(f0) > 1 else 0:.2f}")
        print(f"     Q           med {np.median(Q):6.2f}   IQR "
              f"[{np.percentile(Q, 25):.2f},{np.percentile(Q, 75):.2f}]")
        print(f"     prominence  med {np.median(PR):6.2f}   p90 {np.percentile(PR, 90):.2f}"
              f"   (>3 = a real line above its own local floor)")
        print(f"     excursion w med {np.median(W):6.3f} s  (shape only -- see docstring)")

    print(f"\n  ---- AXIS LOADING of the 40-49 Hz band (fraction of the 3-axis accel envelope) ----")
    print(f"  A steering/column torsional mode and a chassis mode load different axes; this is the")
    print(f"  part of the same/different question that does NOT depend on the alias.")
    print(f"    {'pool':>34s} | " + " ".join(f"{a:>7s}" for a in L.ACC) + " | " +
          " ".join(f"{a:>7s}" for a in L.GYR))
    load = {}
    for lab, tag, segs, sel in (
            ("r47 HIGHWAY engaged v>=22", "r47", HIGHWAY, hw_sel),
            ("r3a CREEP engaged v<4", "r3a", L.SEGS["r3a"], creep_sel),
            ("r3b CREEP engaged v<4", "r3b", L.SEGS["r3b"], creep_sel),
            ("r47 CREEP engaged v<4", "r47", L.SEGS["r47"], creep_sel)):
        acc = {a: [] for a in L.AXES}
        for s in segs:
            dc, di = L.load_can(tag, s), L.load_imu(tag, s)
            if dc is None or di is None or len(di["at"]) < 500:
                continue
            fs = 1.0 / np.median(np.diff(dc["t"]))
            for a in L.AXES:
                t = di["at"] if a[0] == "a" else di["gt"]
                u, odr, _, tu = L.uniform(t, di[a])
                m = sel(dc, fs, tu)
                if m is None or m.sum() < 100:
                    continue
                acc[a].append(float(np.percentile(L.env_full(u, odr, 40.0, 49.0)[m], 95)))
        if not acc["ax"]:
            continue
        med = {a: float(np.median(v)) if v else np.nan for a, v in acc.items()}
        sa = sum(med[a] for a in L.ACC)
        sg = sum(med[a] for a in L.GYR)
        load[lab] = med
        print(f"    {lab:>34s} | " + " ".join(f"{100 * med[a] / sa:6.1f}%" for a in L.ACC) +
              " | " + " ".join(f"{100 * med[a] / sg:6.1f}%" for a in L.GYR))
    print(f"\n  reference: {amap['vertical']}=vertical  {amap['lateral']}=lateral  "
          f"{amap['longitudinal']}=longitudinal  {amap['yaw']}=yaw")
    RESULTS["mode"] = dict(load=load,
                           bursts={k: dict(n=len(v),
                                           f0=float(np.nanmedian([r["f0"] for r in v])) if v else None,
                                           Q=float(np.nanmedian([r["Q"] for r in v])) if v else None,
                                           prom=float(np.nanmedian([r["prom"] for r in v])) if v else None,
                                           wid=float(np.nanmedian([r["wid"] for r in v])) if v else None)
                                   for k, v in rows.items()})


# ==================================================================== 9. ALIAS TEST ===============
def sec_alias():
    L.hdr("9. CAN THE IMU LATTICE BREAK THE CAN ALIAS?  MEASURED, NOT ASSUMED.\n"
          "IMU 101.02 Hz vs CAN 100.00 Hz = 1.02 Hz per alias order. Reading the order off that\n"
          "shift needs the PAIRED peak difference measured to sem << 0.34 Hz, on the SAME burst --\n"
          "the mode's own frequency wanders several Hz between bursts, which would swamp an\n"
          "unpaired comparison.")
    NF = 256
    cand = []
    for s in HIGHWAY + [0, 18, 20, 22, 23]:
        dc, di = L.load_can("r47", s), L.load_imu("r47", s)
        if dc is None or di is None or len(di["at"]) < 500:
            continue
        fs = 1.0 / np.median(np.diff(dc["t"]))
        ec = L.env_full(dc["tq"], fs, 30.0, 49.0)
        for i in range(0, len(dc["t"]) - NF, NF // 2):
            cand.append((s, i, float(np.percentile(ec[i:i + NF], 95))))
    if not cand:
        print("  no candidate windows.")
        RESULTS["alias"] = dict(n=0, resolvable=False)
        return
    cand.sort(key=lambda q: -q[2])
    cand = cand[:120]           # the 120 loudest 30-49 Hz CAN windows on the route
    rows = []
    for s, i, amp in cand:
        dc, di = L.load_can("r47", s), L.load_imu("r47", s)
        fs = 1.0 / np.median(np.diff(dc["t"]))
        Pc = L.periodogram(dc["tq"][i:i + NF], fs, NF)
        if Pc is None:
            continue
        fc = np.fft.rfftfreq(NF, 1 / fs)
        f_can, p_can = L.locate(fc, Pc, 30.0, 49.0)
        t0, t1 = dc["t"][i], dc["t"][i + NF - 1]
        best = None
        for ax in L.AXES:
            t = di["at"] if ax[0] == "a" else di["gt"]
            u, odr, _, tu = L.uniform(t, di[ax])
            j = np.flatnonzero((tu >= t0) & (tu <= t1))
            if len(j) < NF:
                continue
            Pi = L.periodogram(u[j[0]:j[0] + NF], odr, NF)
            if Pi is None:
                continue
            fi = np.fft.rfftfreq(NF, 1 / odr)
            f_imu, p_imu = L.locate(fi, Pi, 30.0, 49.0)
            if best is None or (np.isfinite(p_imu) and p_imu > best[2]):
                best = (ax, f_imu, p_imu)
        if best and np.isfinite(f_can) and np.isfinite(best[1]):
            rows.append((s, t0, f_can, p_can, best[0], best[1], best[2]))
    if len(rows) < 3:
        print(f"  only {len(rows)} paired bursts -- not enough to measure the shift.")
        RESULTS["alias"] = dict(n=len(rows), resolvable=False)
        return
    sh = np.array([r[5] - r[2] for r in rows])
    good = [r for r in rows if r[3] > 3 and r[6] > 3]
    print(f"  {'seg':>4s} {'t':>8s} | {'CAN f':>7s} {'prom':>6s} | {'ax':>3s} {'IMU f':>7s} "
          f"{'prom':>6s} | {'shift':>7s}")
    for r in rows[:20]:
        print(f"  {r[0]:4d} {r[1]:7.2f}s | {r[2]:7.3f} {r[3]:6.1f} | {r[4]:>3s} {r[5]:7.3f} "
              f"{r[6]:6.1f} | {r[5] - r[2]:+7.3f}")
    if len(rows) > 20:
        print(f"  ... {len(rows) - 20} more")
    sem = float(sh.std(ddof=1) / np.sqrt(len(sh)))
    print(f"\n  ALL n={len(sh)}: shift med {np.median(sh):+.4f} Hz  mean {sh.mean():+.4f}  "
          f"sd {sh.std(ddof=1):.4f}  sem {sem:.4f}")
    if len(good) >= 3:
        g = np.array([r[5] - r[2] for r in good])
        semg = float(g.std(ddof=1) / np.sqrt(len(g)))
        print(f"  prominent on BOTH grids n={len(g)}: shift med {np.median(g):+.4f}  "
              f"sd {g.std(ddof=1):.4f}  sem {semg:.4f}")
    print(f"\n  Separation to resolve = 1.0206 Hz per order; need sem << 0.34 Hz.")
    print(f"  MEASURED sem = {sem:.4f} Hz  =>  "
          f"{'RESOLVABLE' if sem < 0.34 else 'NOT RESOLVABLE -- the alias STANDS'}")
    print(f"  🛑 So the IMU confirms REALITY, INDEPENDENCE and DOSE. It does NOT identify the true\n"
          f"     frequency: '40-49 Hz' remains degenerate with ~52-61 Hz and ~142-151 Hz on both\n"
          f"     instruments, because a 1.02 Hz grid difference is far below the per-burst scatter.")
    RESULTS["alias"] = dict(n=len(sh), sem=sem, med=float(np.median(sh)),
                            resolvable=bool(sem < 0.34))


if __name__ == "__main__":
    ALL = ["rate", "axis", "man", "order", "ab", "creep", "hw", "mode", "alias"]
    want = sys.argv[1:] or ALL
    odr_a, odr_g = (101.02, 101.02)
    amap = dict(vertical="ax", lateral="ay", longitudinal="az", yaw="gx")
    if "rate" in want:
        odr_a, odr_g = sec_rate()
    if "axis" in want:
        amap = sec_axis(odr_a)
    if "man" in want:
        sec_man(amap)
    if "order" in want:
        sec_order()
    if "ab" in want:
        sec_ab(amap)
    if "creep" in want:
        sec_creep(amap)
    if "hw" in want:
        sec_hw(amap)
    if "mode" in want:
        sec_mode(amap)
    if "alias" in want:
        sec_alias()
    OUT.write_text(json.dumps(RESULTS, indent=1, default=float))
    print(f"\nwrote {OUT}")
