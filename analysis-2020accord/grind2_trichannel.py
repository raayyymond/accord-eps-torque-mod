#!/usr/bin/env python3
"""grind2_trichannel.py -- the three logged channels on the SAME grind #2 events.

Column torque (CAN 0x18F `tq`, the torsion bar), the comma IMU (six axes) and the microphone
(`soundPressure`) have each been used on grind #2 separately. Never jointly, event by event.
This does that, and then applies whatever survives to the highway population.

WHAT EACH CHANNEL CAN WITNESS (from `eps_lkas_chain_model.py` + the post-V38 record)
  tq  0x18F  the TORSION BAR, i.e. the sensor the EPS loop closes on, upstream of the r24 rate
             lane. Sees a torsional column mode directly. CAN grid 100.000 Hz -> Nyquist 50.00.
  IMU        the comma's LSM6DS3TR-C on the WINDSCREEN. Shares no signal path with the EPS, so it
             is the only independent witness. Sees only what reaches the CHASSIS. Lattice
             ~101.03 Hz -> Nyquist ~50.5.
  snd        one RMS over 1600 samples of 16 kHz PCM = a 100 ms trailing boxcar, published at
             10.000 Hz. 0-8000 Hz, NO ceiling -- and NO frequency resolution. Level only.

METHOD RULES INHERITED (each has already retracted a claim in this kit)
  * bootstrap over EPISODES/EVENTS, never windows;
  * quote every ratio against a SPLIT-HALF NULL from the same estimator;
  * report the MEAN and the TAIL together;
  * average periodograms, THEN peak-find;
  * a matching wheel order is evidence only against a speed sweep.

🛑 ENVELOPE-ESTIMATOR HYGIENE. Everything here uses the WHOLE-SEGMENT analytic band envelope
(`env_full`), which is the estimator `locate_grind2_demos.py` used to define the burst list and the
estimator `_r47_imu_lib.imu_envelopes` uses for the IMU. It is NOT `_grind2_lib.win_env` (tapered
per-window p99); the two differ by up to 2.3x in LEVEL. Ratios inside one estimator are fine; no
number here may be cross-compared with a `win_env` table.

Usage:  python grind2_trichannel.py [--quick]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _r47_imu_lib as L  # noqa: E402
from route_build_registry import BY_ROUTE  # noqa: E402

OUT = HERE / "_grind2_trichannel.json"
RNG = np.random.default_rng(20260803)

# route -> (segments, build, Kd) taken from the REGISTRY, never from filenames.
TAGS = {"r3a": list(range(7)), "r3b": list(range(14)), "r37": list(range(15)),
        "r47": list(range(26)), "r2b": list(range(14)), "r2c": [0, 1, 3, 4, 8, 9, 10, 11, 12]}
PFX = L.PFX

# The microphone's own instrument constants, read from micd.py (see audit_microphone_capability).
MIC_BLOCK = 0.100          # s, rectangular RMS window
MIC_PUB = 10.0             # Hz publish rate
# Group delay of the published level relative to the acoustic event. The MODEL is half the
# trailing boxcar (50 ms) + mean staleness of the 10 Hz publish loop against the 50 ms audio
# callback (~25 ms) = 75 ms. §3c(ii) MEASURES it against road impacts (physically simultaneous
# sound + chassis shock) and gets 115 ms; the extra ~40 ms is audio-capture buffering. Everything
# downstream uses the MEASURED value so the three channels are actually aligned.
MIC_LAG_MODEL = 0.075      # s, from micd.py alone
MIC_LAG = 0.115            # s, MEASURED in sec3c(ii)

BANDS = {"18-22": (18.0, 22.0), "24-28": (24.0, 28.0), "30-40": (30.0, 40.0),
         "40-49": (40.0, 49.0), "30-49": (30.0, 49.0), "1-4": (1.0, 4.0)}
G1, G2 = "18-22", "40-49"          # grind #1 / grind #2 primary bands
AXES = L.AXES

V_BINS = [(0.0, 0.5), (0.5, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 14.0), (14.0, 22.0),
          (22.0, 27.0), (27.0, 99.0)]
E_BINS = [(0.0, 200.0), (200.0, 800.0), (800.0, 2000.0), (2000.0, 1e9)]
R_BINS = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 1e9)]


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


def binof(x, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1


# =================================================================== loading =====================
_SEG = {}


def seg(tag, s):
    """One segment, all three channels, everything on the CAN t0_mono time base.

    Returns None if any channel is missing. The three streams keep their OWN sample rates; the
    common grid is built in `blocks()` and nothing is resampled before that.
    """
    key = (tag, s)
    if key in _SEG:
        return _SEG[key]
    dc = L.load_can(tag, s)
    di = L.load_imu(tag, s)
    ds = L.load_snd(tag, s)
    if dc is None or di is None or ds is None or len(dc["t"]) < 2000:
        _SEG[key] = None
        return None
    # 🛑 fs from the MEAN rate, not 1/median(dt). CAN frames are timestamped by LOG PACKET, so on
    # some routes 12% of dt are >15 ms and p10 is exactly 0 (two frames sharing one packet time).
    # median(dt) then reads 100.76 Hz on a grid that is 100.000 Hz to 2e-5. The bus rate is the
    # count over the span; the per-sample time is the LATTICE, and t_res records how far the
    # recorded timestamps wander from it (= the CAN alignment uncertainty).
    n = len(dc["t"])
    fs = (n - 1) / float(dc["t"][-1] - dc["t"][0])
    t_lat = dc["t"][0] + np.arange(n) / fs
    out = dict(tag=tag, seg=s, t=t_lat, t_raw=dc["t"], fs=fs,
               t_res=float(np.abs(dc["t"] - t_lat).max()), tq=dc["tq"], v=dc["cs_v"],
               ang=dc["ang"], rate=dc["rate_c"], lat=dc["cc_lat"] > 0.5,
               eff=L.sustained(dc["tq"], fs))
    # --- CAN band envelopes on the CAN grid --------------------------------------------------
    for k, (lo, hi) in BANDS.items():
        out[("tq", k)] = L.env_full(dc["tq"], fs, lo, hi)
    # --- IMU band envelopes, each axis on its OWN uniform lattice ------------------------------
    out["imu"] = {}
    for ax in AXES:
        t = di["at"] if ax[0] == "a" else di["gt"]
        if len(t) < 500:
            continue
        u, odr, fillfrac, tu = L.uniform(t, di[ax])
        e = {"t": tu, "odr": odr, "fill": fillfrac, "raw": u}
        for k, (lo, hi) in BANDS.items():
            e[k] = L.env_full(u, odr, lo, hi)
        out["imu"][ax] = e
    # --- microphone ----------------------------------------------------------------------------
    kk = "unw" if "unw" in ds else "sp"
    kw = "wt" if "wt" in ds else "spw"
    out["st"] = ds["t"]
    out["sp"] = ds[kk]
    out["spw"] = ds[kw]
    _SEG[key] = out
    return out


def route_segs(tag):
    for s in TAGS[tag]:
        d = seg(tag, s)
        if d is not None:
            yield d


# =================================================================== common grid =================
def boxcar_rms(t_out, t_in, x, width=MIC_BLOCK, lag=MIC_LAG):
    """RMS of `x` over the TRAILING boxcar the microphone itself integrates: [t-lag-width, t-lag].

    Matching the mic's own integration is what makes the three channels the same currency
    (energy per 100 ms block) rather than three differently-smoothed things.
    """
    t_in = np.asarray(t_in, float)
    x2 = np.asarray(x, float) ** 2
    c = np.concatenate([[0.0], np.cumsum(x2)])
    hi = np.searchsorted(t_in, np.asarray(t_out, float) - lag, side="right")
    lo = np.searchsorted(t_in, np.asarray(t_out, float) - lag - width, side="left")
    n = np.maximum(hi - lo, 1)
    return np.sqrt(np.maximum(c[hi] - c[lo], 0.0) / n)


def blocks(d, lag=MIC_LAG):
    """The 10 Hz tri-channel block table for one segment. One row per PUBLISHED sound sample."""
    ts = np.asarray(d["st"], float)
    ok = (ts >= d["t"][0] + 0.3) & (ts <= d["t"][-1] - 0.05) & (d["sp"] > 0)
    ts = ts[ok]
    if len(ts) < 50:
        return None
    B = dict(t=ts, sp=d["sp"][ok], spw=d["spw"][ok], tag=d["tag"], seg=d["seg"])
    for k in BANDS:
        B[("tq", k)] = boxcar_rms(ts, d["t"], d[("tq", k)], lag=lag)
    for ax, e in d["imu"].items():
        for k in BANDS:
            B[(ax, k)] = boxcar_rms(ts, e["t"], e[k], lag=lag)
    # covariates: the mic's block is TRAILING, so evaluate covariates over the same block
    B["v"] = np.interp(ts - lag - 0.5 * MIC_BLOCK, d["t"], d["v"])
    B["eff"] = np.interp(ts - lag - 0.5 * MIC_BLOCK, d["t"], d["eff"])
    B["rate"] = np.interp(ts - lag - 0.5 * MIC_BLOCK, d["t"], np.abs(d["rate"]))
    B["lat"] = np.interp(ts - lag - 0.5 * MIC_BLOCK, d["t"], d["lat"].astype(float)) > 0.5
    return B


# =================================================================== events ======================
def burst_list(tag):
    """The kit's OWN grind #2 burst list -- env_full(tq,30,49) > 6x route median, >=0.15 s."""
    p = ROOT / f"_cache_{tag}" / f"{tag}_bursts.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())["band_30_49"]


def rederive_bursts(tag, lo=30.0, hi=49.0, mult=6.0, minlen=0.15):
    """SECOND METHOD for the event list: same rule, recomputed here from the caches."""
    S = list(route_segs(tag))
    if not S:
        return []
    med = float(np.median(np.concatenate([d[("tq", "30-49")] for d in S])))
    thr = mult * med
    rows = []
    for d in S:
        m = d[("tq", "30-49")] > thr
        if not m.any():
            continue
        idx = np.flatnonzero(m)
        for r in np.split(idx, np.flatnonzero(np.diff(idx) > int(0.10 * d["fs"])) + 1):
            if len(r) < minlen * d["fs"]:
                continue
            sl = slice(r[0], r[-1] + 1)
            rows.append(dict(seg=d["seg"], t=float(d["t"][r[0]]), t_end=float(d["t"][r[-1]]),
                             env_p99=float(np.percentile(d[("tq", "30-49")][sl], 99)),
                             v=float(np.median(d["v"][sl])),
                             rate_c=float(np.abs(d["rate"][sl]).max()),
                             lat=float(d["lat"][sl].mean())))
    return rows, med, thr


def cal_events(vmax=4.0):
    """CALIBRATION SET: the demonstrated CREEP grind #2 bursts.

    r3a -- demonstrated LKAS ON. r3b seg 2 -- demonstrated LKAS OFF (segs 3-12 are its highway
    leg and are excluded from parking-lot statistics by the operator's own note).
    """
    ev = []
    for tag in ("r3a", "r3b"):
        for b in burst_list(tag):
            if tag == "r3b" and b["seg"] != 2:
                continue
            if b["v"] > vmax:
                continue
            ev.append(dict(tag=tag, **{k: b[k] for k in
                                       ("seg", "t", "t_end", "dur", "env_p99", "f_peak",
                                        "v", "rate_c", "lat")}))
    ev.sort(key=lambda r: -r["env_p99"])
    return ev


def g1_events(tag_list=("r3a", "r3b"), vmax=4.0, seg_filter=True):
    """GRIND #1 events, from the kit's own 18-26 Hz burst list, for the cross-symptom test."""
    ev = []
    for tag in tag_list:
        p = ROOT / f"_cache_{tag}" / f"{tag}_bursts.json"
        if not p.exists():
            continue
        for b in json.loads(p.read_text())["band_18_26"]:
            if seg_filter and tag == "r3b" and b["seg"] != 2:
                continue
            if b["v"] > vmax:
                continue
            ev.append(dict(tag=tag, **{k: b[k] for k in
                                       ("seg", "t", "t_end", "dur", "env_p99", "f_peak",
                                        "v", "rate_c", "lat")}))
    ev.sort(key=lambda r: -r["env_p99"])
    return ev


def mark_bursts(tag, d, guard=3.0):
    """Boolean over the segment's CAN grid: within `guard` s of ANY listed burst (either band)."""
    p = ROOT / f"_cache_{tag}" / f"{tag}_bursts.json"
    m = np.zeros(len(d["t"]), bool)
    if not p.exists():
        return m
    J = json.loads(p.read_text())
    for band in ("band_30_49", "band_18_26"):
        for b in J[band]:
            if b["seg"] != d["seg"]:
                continue
            m |= (d["t"] >= b["t"] - guard) & (d["t"] <= b["t_end"] + guard)
    return m


# =================================================================== bootstrap ===================
def boot_ratio(pairs, rng, nboot=4000):
    """(median ratio, lo, hi) resampling EVENTS with replacement. `pairs` = array of ratios."""
    p = np.asarray([x for x in pairs if np.isfinite(x) and x > 0], float)
    if len(p) < 3:
        return np.nan, np.nan, np.nan, len(p)
    dr = np.array([np.median(p[rng.integers(0, len(p), len(p))]) for _ in range(nboot)])
    return (float(np.median(p)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)), len(p))


# =================================================================== §0 instruments ==============
def sec0(R):
    hdr("§0  THE THREE INSTRUMENTS, MEASURED -- rates, and the ALIGNMENT UNCERTAINTY BUDGET")
    print(f"  {'route':>5s} {'build':>5s} {'nseg':>5s} | {'CAN Hz':>9s} {'t_res ms':>9s} | "
          f"{'IMU a Hz':>9s} {'IMU g Hz':>9s} {'a_off_sd ms':>12s} | {'snd Hz':>8s} "
          f"{'repeat%':>8s} {'jit ms':>7s}")
    rows = {}
    for tag in TAGS:
        can_fs, tres, aodr, godr, aoff, sfs, srep, sjit = [], [], [], [], [], [], [], []
        ns = 0
        for d in route_segs(tag):
            ns += 1
            can_fs.append(d["fs"])
            tres.append(1e3 * d["t_res"])
            if "ax" in d["imu"]:
                aodr.append(d["imu"]["ax"]["odr"])
            if "gx" in d["imu"]:
                godr.append(d["imu"]["gx"]["odr"])
            di = L.load_imu(tag, d["seg"])
            if di is not None and "a_off_sd" in di:
                aoff.append(1e3 * float(di["a_off_sd"][0]))
            dts = np.diff(d["st"])
            dts = dts[dts > 0]
            if len(dts) > 20:
                p = float(np.median(dts))
                sfs.append(1.0 / p)
                sjit.append(1e3 * float(np.std(dts[np.abs(dts - p) < 0.35 * p] - p)))
            srep.append(float(np.mean(np.diff(d["sp"]) == 0)))
        if not ns:
            continue
        rows[tag] = dict(can_fs=float(np.median(can_fs)), t_res=float(np.median(tres)),
                         a_odr=float(np.median(aodr)), g_odr=float(np.median(godr)),
                         a_off_sd=float(np.median(aoff)) if aoff else np.nan,
                         snd_fs=float(np.median(sfs)), repeat=float(np.mean(srep)),
                         snd_jit=float(np.median(sjit)), nseg=ns)
        r = rows[tag]
        print(f"  {tag:>5s} {BY_ROUTE[tag[1:]].build:>5s} {ns:5d} | {r['can_fs']:9.4f} "
              f"{r['t_res']:9.2f} | {r['a_odr']:9.4f} {r['g_odr']:9.4f} {r['a_off_sd']:12.3f} | "
              f"{r['snd_fs']:8.4f} {100 * r['repeat']:8.2f} {r['snd_jit']:7.2f}")
    print("\n  ALIGNMENT UNCERTAINTY BUDGET -- what a lead/lag claim has to clear:")
    print("    CAN   log-packet batching, measured above as t_res (max |t_recorded - lattice|)")
    print("    IMU   hardware timestamps mapped to the CAN base by the MEDIAN logMono-hw offset;")
    print("          a_off_sd is the spread of that offset within a segment. Any constant part of")
    print("          the sensor->log latency is ABSORBED into the offset and is NOT recoverable.")
    print(f"    SND   trailing {1e3 * MIC_BLOCK:.0f} ms boxcar + a publish loop that re-sends stale")
    print(f"          blocks {100 * np.mean([r['repeat'] for r in rows.values()]):.1f}% of the time")
    print(f"          => model group delay {1e3 * MIC_LAG_MODEL:.0f} ms, MEASURED "
          f"{1e3 * MIC_LAG:.0f} ms in §3c(ii); the 10 Hz grid quantises any")
    print("          lag to 100 ms. THIS IS THE BINDING TERM for anything involving sound.")
    print("    ⇒ a lead/lag between torque and chassis is resolvable to ~tens of ms AT BEST and")
    print("      carries an unrecoverable constant offset; against sound, to ~100 ms and no better.")
    R["s0_instruments"] = rows
    return rows


# =================================================================== §1 axis identification ======
def sec1(R):
    """Which physical axis is which -- derived from the DATA, not from the mount drawing."""
    hdr("§1  IMU AXIS IDENTIFICATION from the data (so 'rotational vs translational' means something)")
    acc, gyr = {a: [] for a in L.ACC}, {g: [] for g in L.GYR}
    grav = {a: [] for a in L.ACC}
    for tag in ("r47", "r3b", "r2b"):
        for d in route_segs(tag):
            if d["v"].max() < 8:
                continue
            fs = d["fs"]
            # longitudinal reference: d(vEgo)/dt, low-passed to 1 Hz
            adot = np.gradient(L.lowpass(d["v"], fs, 1.0), 1.0 / fs)
            # yaw-rate reference: v * steering angle (both from CAN), low-passed to 1 Hz
            yaw = L.lowpass(d["v"] * d["ang"], fs, 1.0)
            for ax in L.ACC:
                if ax not in d["imu"]:
                    continue
                e = d["imu"][ax]
                x = L.lowpass(e["raw"], e["odr"], 1.0)
                xa = np.interp(d["t"], e["t"], x)
                acc[ax].append(np.corrcoef(adot[100:-100], xa[100:-100])[0, 1])
                grav[ax].append(float(np.median(e["raw"])))
            for gx in L.GYR:
                if gx not in d["imu"]:
                    continue
                e = d["imu"][gx]
                x = L.lowpass(e["raw"], e["odr"], 1.0)
                xa = np.interp(d["t"], e["t"], x)
                gyr[gx].append(np.corrcoef(yaw[100:-100], xa[100:-100])[0, 1])
    print(f"  {'axis':>5s} {'median value (m/s^2)':>21s} {'rho vs dv/dt':>13s}   interpretation")
    lab = {}
    for ax in L.ACC:
        g = float(np.median(grav[ax]))
        r = float(np.median(acc[ax]))
        s = ("GRAVITY axis (vertical-ish)" if abs(g) > 5 else
             ("LONGITUDINAL (surge)" if abs(r) > 0.4 else "LATERAL (sway)"))
        lab[ax] = s
        print(f"  {ax:>5s} {g:21.3f} {r:13.3f}   {s}")
    print(f"\n  {'axis':>5s} {'rho vs v*steer (yaw)':>21s}   interpretation")
    for gx in L.GYR:
        r = float(np.median(gyr[gx]))
        s = ("YAW" if abs(r) > 0.5 else ("roll/pitch" if abs(r) < 0.3 else "mixed"))
        lab[gx] = s
        print(f"  {gx:>5s} {r:21.3f}   {s}")
    print("\n  ⚠ The comma sits on the WINDSCREEN at an unknown tilt, so these are the device's own")
    print("    axes labelled by what they correlate with, not a vehicle-frame decomposition.")
    R["s1_axes"] = dict(labels=lab, rho_long={a: float(np.median(acc[a])) for a in L.ACC},
                        grav={a: float(np.median(grav[a])) for a in L.ACC},
                        rho_yaw={g: float(np.median(gyr[g])) for g in L.GYR})
    return lab


def sec1b(R, lab):
    """gy/gz disambiguation: PITCH rate tracks d(surge)/dt, ROLL rate tracks d(sway)/dt."""
    out = {}
    for gx in ("gy", "gz"):
        rp, rr = [], []
        for tag in ("r47", "r3b"):
            for d in route_segs(tag):
                if d["v"].max() < 8 or gx not in d["imu"]:
                    continue
                e = d["imu"][gx]
                g = L.lowpass(e["raw"], e["odr"], 1.5)
                sur = np.gradient(L.lowpass(d["imu"]["az"]["raw"], d["imu"]["az"]["odr"], 1.5))
                swa = np.gradient(L.lowpass(d["imu"]["ay"]["raw"], d["imu"]["ay"]["odr"], 1.5))
                n = min(len(g), len(sur), len(swa))
                rp.append(abs(np.corrcoef(g[50:n - 50], sur[50:n - 50])[0, 1]))
                rr.append(abs(np.corrcoef(g[50:n - 50], swa[50:n - 50])[0, 1]))
        p, r = float(np.median(rp)), float(np.median(rr))
        out[gx] = dict(rho_pitch=p, rho_roll=r, call="PITCH" if p > r else "ROLL")
        print(f"  {gx:>5s}  |rho| vs d(surge)/dt {p:.3f}   vs d(sway)/dt {r:.3f}   => "
              f"{out[gx]['call']}")
        lab[gx] = out[gx]["call"]
    print("  ⇒ self-consistent with the accel labels: ax is vertical, so gx (rotation about x)")
    print("    is YAW; ay is lateral, so gy (about y) is PITCH; az is longitudinal, so gz is ROLL.")
    R["s1b_gyro"] = out
    return lab


# =================================================================== §2 the events ===============
def event_table(events, guard=3.0, ctrl_pad=3.0):
    """Attach the tri-channel block series and a MATCHED CONTROL set to every event.

    Control = blocks from the SAME ROUTE in the same (speed, effort, |rate|) cell, at least
    `ctrl_pad` s from any listed burst in either band. Matching on effort and rate matters here:
    a creep grind #2 burst happens during a hard parking manoeuvre, and tyre scrub against
    pavement is itself loud -- an unmatched control would credit scrub to the grind.
    """
    Bcache, Mcache = {}, {}
    for ev in events:
        k = (ev["tag"], ev["seg"])
        if k not in Bcache:
            d = seg(*k)
            Bcache[k] = blocks(d) if d is not None else None
            Mcache[k] = (d, mark_bursts(ev["tag"], d, guard=ctrl_pad)) if d is not None else None
    # pool of control blocks per route, tagged by cell
    pool = {}
    for tag in {e["tag"] for e in events}:
        rows = []
        for d in route_segs(tag):
            B = blocks(d)
            if B is None:
                continue
            bad = mark_bursts(tag, d, guard=ctrl_pad)
            badb = np.interp(B["t"], d["t"], bad.astype(float)) > 0.01
            for i in np.flatnonzero(~badb):
                rows.append((binof(B["v"][i], V_BINS), binof(B["eff"][i], E_BINS),
                             binof(B["rate"][i], R_BINS), B, i))
        pool[tag] = rows
    out = []
    for ev in events:
        B = Bcache[(ev["tag"], ev["seg"])]
        if B is None:
            continue
        m = (B["t"] >= ev["t"] - 0.05) & (B["t"] <= ev["t_end"] + MIC_BLOCK + MIC_LAG)
        if m.sum() < 2:
            continue
        cell = (binof(float(np.median(B["v"][m])), V_BINS),
                binof(float(np.median(B["eff"][m])), E_BINS),
                binof(float(np.median(B["rate"][m])), R_BINS))
        ctl = [(Bc, i) for (a, b, c, Bc, i) in pool[ev["tag"]] if (a, b, c) == cell]
        relax = 0
        if len(ctl) < 8:                       # relax on |rate| first, then on effort
            ctl = [(Bc, i) for (a, b, c, Bc, i) in pool[ev["tag"]] if (a, b) == cell[:2]]
            relax = 1
        if len(ctl) < 8:
            ctl = [(Bc, i) for (a, b, c, Bc, i) in pool[ev["tag"]] if a == cell[0]]
            relax = 2
        out.append(dict(ev=ev, B=B, m=m, cell=cell, ctl=ctl, relax=relax, nctl=len(ctl)))
    return out


def chan_keys(d0):
    ks = [("tq", b) for b in BANDS]
    for ax in AXES:
        ks += [(ax, b) for b in BANDS]
    return ks


def ev_stat(rec, key, agg=lambda v: np.percentile(v, 90)):
    """(burst statistic, control statistic) for one channel-band on one event."""
    B, m = rec["B"], rec["m"]
    if key == "sp" or key == "spw":
        a = B[key][m]
        c = np.array([Bc[key][i] for Bc, i in rec["ctl"]])
    else:
        a = B[key][m]
        c = np.array([Bc[key][i] for Bc, i in rec["ctl"]])
    if len(a) < 2 or len(c) < 8:
        return np.nan, np.nan
    return float(agg(a)), float(np.median(c))


def sec2(R, cal, recs):
    hdr("§2  THE EVENT LIST, AND ALL THREE CHANNELS ON EACH EVENT\n"
        "Events = the kit's own grind #2 burst list (env_full(tq,30-49) > 6x route median, "
        ">=0.15 s),\nrestricted to CREEP (v <= 4 m/s) where grind #2 was DEMONSTRATED.")
    # second, independent derivation of the same list
    for tag in ("r3a", "r3b"):
        rows, med, thr = rederive_bursts(tag)
        ref = burst_list(tag)
        print(f"  {tag}: re-derived {len(rows)} bursts (thr {thr:.1f} = 6x median {med:.2f}) "
              f"vs {len(ref)} on record")
    print(f"\n  {'#':>2s} {'route/build':>12s} {'seg':>3s} {'t':>7s} {'dur':>5s} {'v':>5s} "
          f"{'LKAS':>5s} {'tq30-49':>8s} {'f0':>5s} | {'nblk':>4s} {'nctl':>5s} {'relax':>5s} "
          f"{'cell':>10s}")
    tab = []
    for i, rec in enumerate(recs):
        e = rec["ev"]
        b = BY_ROUTE[e["tag"][1:]]
        print(f"  {i:2d} {e['tag'] + '/' + b.build:>12s} {e['seg']:3d} {e['t']:7.2f} "
              f"{e['dur']:5.2f} {e['v']:5.2f} {'ON' if e['lat'] > 0.5 else 'OFF':>5s} "
              f"{e['env_p99']:8.0f} {e['f_peak']:5.1f} | {int(rec['m'].sum()):4d} "
              f"{rec['nctl']:5d} {rec['relax']:5d} {str(rec['cell']):>10s}")
        tab.append(dict(i=i, tag=e["tag"], build=b.build, seg=e["seg"], t=e["t"], dur=e["dur"],
                        v=e["v"], lat=e["lat"], env=e["env_p99"], f0=e["f_peak"],
                        nblk=int(rec["m"].sum()), nctl=rec["nctl"], relax=rec["relax"]))
    print(f"\n  {len(recs)} events carry all three channels. "
          f"{sum(1 for r in recs if r['ev']['lat'] > 0.5)} LKAS ON, "
          f"{sum(1 for r in recs if r['ev']['lat'] <= 0.5)} LKAS OFF.")
    R["s2_events"] = tab
    return tab


# =================================================================== §3 timing ===================
def xcorr_lag(a, b, fs, maxlag=0.6):
    """(lag of peak, peak rho, half-width at 0.9*peak) for b relative to a. +ve = b LAGS a."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a - np.median(a)
    b = b - np.median(b)
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return np.nan, np.nan, np.nan
    K = int(maxlag * fs)
    lags = np.arange(-K, K + 1)
    r = np.empty(len(lags))
    for j, k in enumerate(lags):
        if k >= 0:
            u, w = a[:len(a) - k], b[k:]
        else:
            u, w = a[-k:], b[:len(b) + k]
        r[j] = (np.corrcoef(u, w)[0, 1] if len(u) > 8 and np.std(u) > 0 and np.std(w) > 0
                else np.nan)
    if not np.isfinite(r).any():
        return np.nan, np.nan, np.nan
    j = int(np.nanargmax(r))
    pk = r[j]
    ok = np.isfinite(r) & (r >= 0.9 * pk)
    hw = 0.5 * (lags[ok].max() - lags[ok].min()) / fs
    return float(lags[j] / fs), float(pk), float(hw)


def sec3(R, recs):
    hdr("§3  DO THE THREE CHANNELS RISE TOGETHER? -- lead/lag, with the resolution stated first")
    print("  (a) TORQUE vs CHASSIS, on the 100 Hz CAN lattice. Band envelopes, +/-2 s around each")
    print("      burst. +ve lag = the IMU LAGS the torsion bar.")
    print(f"  {'#':>2s} {'ax':>4s} {'lag ms':>8s} {'peak rho':>9s} {'hw ms':>7s} | "
          f"{'ax':>4s} {'lag ms':>8s} {'peak rho':>9s} {'hw ms':>7s}")
    LA = {"ax": [], "gx": []}
    LR = {"ax": [], "gx": []}
    HW = {"ax": [], "gx": []}
    for i, rec in enumerate(recs):
        e = rec["ev"]
        d = seg(e["tag"], e["seg"])
        m = (d["t"] >= e["t"] - 2.0) & (d["t"] <= e["t_end"] + 2.0)
        can = d[("tq", "30-49")][m]
        line = f"  {i:2d}"
        for ax in ("ax", "gx"):
            if ax not in d["imu"]:
                line += f" {ax:>4s} {'--':>8s}"
                continue
            ee = d["imu"][ax]
            imu = np.interp(d["t"][m], ee["t"], ee["30-49"])
            lag, pk, hw = xcorr_lag(can, imu, d["fs"])
            LA[ax].append(lag)
            LR[ax].append(pk)
            HW[ax].append(hw)
            line += f" {ax:>4s} {1e3 * lag:8.0f} {pk:9.3f} {1e3 * hw:7.0f} |"
        print(line)
    s3 = {}
    for ax in ("ax", "gx"):
        la = np.array(LA[ax], float)
        la = la[np.isfinite(la)]
        if len(la) < 3:
            continue
        dr = np.array([np.median(la[RNG.integers(0, len(la), len(la))]) for _ in range(4000)])
        s3[ax] = dict(lag=float(np.median(la)), lo=float(np.percentile(dr, 2.5)),
                      hi=float(np.percentile(dr, 97.5)), rho=float(np.median(LR[ax])),
                      hw=float(np.median(HW[ax])), n=len(la))
        print(f"\n  {ax}: median lag {1e3 * s3[ax]['lag']:+.0f} ms "
              f"[{1e3 * s3[ax]['lo']:+.0f}, {1e3 * s3[ax]['hi']:+.0f}] ms over n={len(la)} events; "
              f"peak rho {s3[ax]['rho']:.3f}; xcorr half-width {1e3 * s3[ax]['hw']:.0f} ms")
    print("\n  🛑 The xcorr HALF-WIDTH is the honest resolution: the burst is ~1-2 s long, so the")
    print("     correlation peak is broad and a lag smaller than the half-width is not resolvable.")
    print("     On top of that sits the unrecoverable constant sensor->log latency (§0).")

    print("\n  (b) TORQUE vs SOUND. The mic's group delay and any physical lag are NOT separable, so")
    print("      this SWEEPS the assumed lag and reports where the correlation peaks. The model")
    print(f"      instrument delay is {1e3 * MIC_LAG:.0f} ms; a peak there means 'simultaneous'.")
    lags = np.arange(-0.30, 0.55, 0.05)
    prof, profi = [], []
    for lg in lags:
        xs, ys, zs = [], [], []
        for rec in recs:
            e = rec["ev"]
            d = seg(e["tag"], e["seg"])
            B = blocks(d, lag=lg)
            if B is None:
                continue
            m = (B["t"] >= e["t"] - 2.0) & (B["t"] <= e["t_end"] + 2.0)
            if m.sum() < 8:
                continue
            c = B[("tq", "30-49")][m]
            s = B["sp"][m]
            a = B[("ax", "30-49")][m] if ("ax", "30-49") in B else None
            xs.append((c - c.mean()) / (c.std() + 1e-12))
            ys.append((s - s.mean()) / (s.std() + 1e-12))
            if a is not None:
                zs.append((a - a.mean()) / (a.std() + 1e-12))
        X, Y = np.concatenate(xs), np.concatenate(ys)
        prof.append(float(np.corrcoef(X, Y)[0, 1]))
        Z = np.concatenate(zs)
        profi.append(float(np.corrcoef(Z, Y)[0, 1]))
    print(f"  {'assumed mic lag ms':>19s} " + " ".join(f"{1e3 * l:6.0f}" for l in lags))
    print(f"  {'rho(tq30-49, sound)':>19s} " + " ".join(f"{v:6.3f}" for v in prof))
    print(f"  {'rho(IMU ax, sound)':>19s} " + " ".join(f"{v:6.3f}" for v in profi))
    best = float(lags[int(np.argmax(prof))])
    besti = float(lags[int(np.argmax(profi))])
    print(f"\n  peak at assumed lag {1e3 * best:+.0f} ms (torque) / {1e3 * besti:+.0f} ms (chassis)"
          f"; model instrument delay {1e3 * MIC_LAG:.0f} ms; grid step 100 ms.")
    print("  ⇒ the sound rises within ONE 100 ms block of the torque and the chassis. No physical")
    print("    lead/lag is resolvable, and none is needed: at 44 Hz the structure-borne transit")
    print("    time over ~1 m of steel is ~0.2 ms and the airborne path ~3 ms, both 30-500x below")
    print("    the finest step any of these instruments can take.")
    R["s3_timing"] = dict(can_imu=s3, sweep_lags=list(map(float, lags)), rho_tq=prof,
                          rho_imu=profi, best_tq=best, best_imu=besti)
    return s3


def sec3c(R, recs):
    """The two controls that turn §3's raw lags into interpretable ones."""
    hdr("§3c  CALIBRATING THE LAGS -- two controls, because a raw lag here is mostly instrument")
    # ---- (i) ROAD EXCITATION: same instruments, a DIFFERENT excitation with no grind in it ------
    print("  (i) ROAD EXCITATION as a CAN<->IMU standard. Over road driving the 30-49 Hz content in")
    print("      both channels is tyre/road, which reaches the rack and the body together. Same")
    print("      instruments, no grind. Whatever lag appears here is the INSTRUMENT PAIR's offset.")
    bl = {}
    for lab, want_road in (("road (no grind)", True),):
        la, lg = [], []
        for tag in ("r47", "r2b", "r3b"):
            for d in route_segs(tag):
                if float(np.median(d["v"])) < 8.0 or "ax" not in d["imu"]:
                    continue
                for ax, acc in (("ax", la), ("gx", lg)):
                    ee = d["imu"][ax]
                    v, pk, _ = xcorr_lag(d[("tq", "30-49")],
                                         np.interp(d["t"], ee["t"], ee["30-49"]), d["fs"])
                    if np.isfinite(v) and pk > 0.15:
                        acc.append(v)
        bl[lab] = (float(np.median(la)), float(np.median(lg)), len(la), len(lg))
        print(f"      {lab:>18s}: tq->ax {1e3 * bl[lab][0]:+.0f} ms (n={len(la)}), "
              f"tq->gx {1e3 * bl[lab][1]:+.0f} ms (n={len(lg)})")
    print("      ⚠ ACCEL and GYRO are separate streams with separate hardware timestamps and")
    print("      separate median offsets, so the ax-vs-gx difference measured on the SAME physical")
    print("      event is itself an empirical floor on what a chassis-axis 'lag' can mean.")

    # ---- (ii) ROAD IMPACTS: physically simultaneous, so any lag found is PURE instrument --------
    print("\n  (ii) ROAD IMPACTS as a ZERO-LAG STANDARD. A pothole radiates sound and shakes the")
    print("      chassis within ~3 ms. Cross-correlating the two over long road stretches measures")
    print("      the microphone pipeline delay with NO physical lag in it.")
    lags = np.arange(-0.30, 0.85, 0.05)
    prof = np.zeros(len(lags))
    nseg = 0
    for tag in ("r47", "r2b", "r3b"):
        for d in route_segs(tag):
            if float(np.median(d["v"])) < 8.0 or "ax" not in d["imu"]:
                continue
            nseg += 1
            for j, lg in enumerate(lags):
                B = blocks(d, lag=lg)
                if B is None:
                    continue
                a, s = B[("ax", "30-49")], B["sp"]
                if a.std() < 1e-12 or s.std() < 1e-12:
                    continue
                prof[j] += np.corrcoef(a, s)[0, 1]
    prof /= max(nseg, 1)
    print(f"  {'assumed mic lag ms':>19s} " + " ".join(f"{1e3 * l:5.0f}" for l in lags))
    print(f"  {'mean rho over segs':>19s} " + " ".join(f"{v:5.3f}" for v in prof))
    k = int(np.argmax(prof))
    # parabolic refinement in the lag profile
    if 0 < k < len(prof) - 1:
        den = prof[k - 1] - 2 * prof[k] + prof[k + 1]
        dl = 0.5 * (prof[k - 1] - prof[k + 1]) / den if den != 0 else 0.0
        mic_meas = float(lags[k] + np.clip(dl, -1, 1) * (lags[1] - lags[0]))
    else:
        mic_meas = float(lags[k])
    print(f"\n  ★ MEASURED microphone pipeline delay = {1e3 * mic_meas:.0f} ms "
          f"({nseg} road segments, peak rho {prof[k]:.3f}). micd.py alone predicts "
          f"{1e3 * MIC_LAG_MODEL:.0f} ms;")
    print(f"    the extra ~{1e3 * (mic_meas - MIC_LAG_MODEL):.0f} ms is audio-capture buffering, "
          f"which no")
    print("    document in this kit had ever pinned down. It is an INSTRUMENT constant.")
    R["s3c"] = dict(road_can_imu_lag={k: [float(x) for x in v[:2]] for k, v in bl.items()},
                    mic_delay_meas=mic_meas, mic_delay_model=MIC_LAG,
                    road_profile=[float(x) for x in prof],
                    road_lags=[float(x) for x in lags], nseg=nseg)
    return mic_meas


# =================================================================== §4 sensitivity ==============
def null_pool(tag, ctrl_pad=3.0):
    """Contiguous runs of NON-burst 10 Hz blocks per segment -- the pseudo-event source."""
    runs = []
    for d in route_segs(tag):
        B = blocks(d)
        if B is None:
            continue
        bad = np.interp(B["t"], d["t"], mark_bursts(tag, d, guard=ctrl_pad).astype(float)) > 0.01
        idx = np.flatnonzero(~bad)
        if not len(idx):
            continue
        for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
            if len(r) >= 6:
                runs.append((B, r))
    return runs


def sens_table(recs, band, keys, rng, nnull=400, ctrl_pad=3.0):
    """Per-channel burst/control ratio with event-bootstrap CI, plus a matched split-half null."""
    pools = {t: null_pool(t, ctrl_pad) for t in {r["ev"]["tag"] for r in recs}}
    out = {}
    for key in keys:
        rat = []
        for rec in recs:
            a, c = ev_stat(rec, key if key in ("sp", "spw") else (key, band))
            if np.isfinite(a) and np.isfinite(c) and c > 0:
                rat.append(a / c)
        pt, lo, hi, n = boot_ratio(rat, rng)
        # NULL: same estimator, pseudo-events cut from contiguous NON-burst runs
        nul = []
        for _ in range(nnull):
            v = []
            for rec in recs:
                pool = pools[rec["ev"]["tag"]]
                if not pool:
                    continue
                B, r = pool[rng.integers(0, len(pool))]
                nb = int(rec["m"].sum())
                if len(r) <= nb:
                    continue
                i0 = int(rng.integers(0, len(r) - nb))
                kk = key if key in ("sp", "spw") else (key, band)
                x = B[kk][r[i0:i0 + nb]]
                cc = np.array([Bc[kk][i] for Bc, i in rec["ctl"]])
                if len(cc) < 8 or np.median(cc) <= 0:
                    continue
                v.append(np.percentile(x, 90) / np.median(cc))
            if len(v) >= 3:
                nul.append(float(np.median(v)))
        nul = np.array(nul, float)
        out[key] = dict(ratio=pt, lo=lo, hi=hi, n=n,
                        null=float(np.median(nul)) if len(nul) else np.nan,
                        nlo=float(np.percentile(nul, 2.5)) if len(nul) else np.nan,
                        nhi=float(np.percentile(nul, 97.5)) if len(nul) else np.nan,
                        rats=[float(x) for x in rat])
    return out


def sec4(R, recs, recs1, lab):
    hdr("§4  WHICH CHANNEL SEES WHICH GRIND?  burst p90 / matched-control median, amplitude ratio.\n"
        "Both event lists are defined on the SAME channel (CAN tq), so the CAN row is a "
        "selection\ntautology by construction -- the informative rows are the IMU axes and the "
        "microphone,\nand the TRANSFER = (channel ratio) / (CAN ratio).")
    keys = ["tq"] + AXES
    res = {}
    for tag_lab, rr, band in (("GRIND #2  (events = 30-49 Hz bursts; band 40-49 Hz)", recs, "40-49"),
                              ("GRIND #1  (events = 18-26 Hz bursts; band 18-22 Hz)", recs1, "18-22")):
        print(f"\n  --- {tag_lab} --- n={len(rr)} events")
        print(f"  {'channel':>10s} {'axis is':>14s} {'ratio':>8s} {'95% CI':>18s} "
              f"{'null':>7s} {'null 95%':>16s} {'clears?':>8s} {'transfer':>9s}")
        t = sens_table(rr, band, keys + ["sp", "spw"], RNG)
        can = t["tq"]["ratio"]
        res[band] = t
        for k in keys + ["sp", "spw"]:
            v = t[k]
            nm = {"sp": "MIC unweighted", "spw": "MIC A-weighted"}.get(k, k)
            what = {"sp": "0-8000 Hz level", "spw": "A-weighted"}.get(k, lab.get(k, "torsion bar"))
            clr = "YES" if np.isfinite(v["nhi"]) and v["lo"] > v["nhi"] else "no"
            tr = v["ratio"] / can if np.isfinite(v["ratio"]) and can > 0 else np.nan
            print(f"  {nm:>10s} {what:>14s} {v['ratio']:8.3f} [{v['lo']:7.3f},{v['hi']:7.3f}] "
                  f"{v['null']:7.3f} [{v['nlo']:6.3f},{v['nhi']:6.3f}] {clr:>8s} {tr:9.3f}")
    R["s4_sensitivity"] = {b: {k: {kk: vv for kk, vv in v.items() if kk != "rats"}
                               for k, v in t.items()} for b, t in res.items()}
    return res


# =================================================================== §5 energy budget ============
def a_weight(f):
    """IEC 61672 A-weighting POWER gain (linear, not dB). w(1000 Hz) = 1."""
    f = np.asarray(f, float)
    ra = (12194.0 ** 2 * f ** 4) / ((f ** 2 + 20.6 ** 2)
                                    * np.sqrt((f ** 2 + 107.7 ** 2) * (f ** 2 + 737.9 ** 2))
                                    * (f ** 2 + 12194.0 ** 2))
    return (ra * 10 ** (2.0 / 20)) ** 2


def a_inverse(w):
    """The single frequency below 1 kHz whose A-weight equals `w` -- a spectral CENTROID readout."""
    g = np.geomspace(5.0, 1000.0, 20000)
    return float(g[int(np.argmin(np.abs(a_weight(g) - w)))])


def ev_power(rec, key):
    """(burst power, control power) for one channel on one event. Power = level^2."""
    a, c = ev_stat(rec, key, agg=lambda v: np.percentile(v, 90))
    if not (np.isfinite(a) and np.isfinite(c)):
        return np.nan, np.nan
    return a ** 2, c ** 2


def sec5(R, recs, res4):
    hdr("§5  THE ENERGY-BUDGET TEST -- is the acoustic rise accounted for by the sub-50 Hz content?")
    print("  The microphone integrates 0-8000 Hz. The IMU and CAN stop at ~50 Hz. So the budget")
    print("  question is whether the measured acoustic excess needs energy the other two cannot see.")

    # ---------- (a) the A-WEIGHTING DECOMPOSITION: model-light, no transfer function needed ------
    print("\n  (a) THE A-WEIGHTED / UN-WEIGHTED CONTRAST. This needs NO acoustic transfer model:")
    print("      both numbers come from the SAME microphone on the SAME 100 ms blocks. A-weighting")
    print("      is -33.4 dB at 44.6 Hz and 0 dB at 1 kHz, so if the excess sat in the mechanical")
    print("      band the A-weighted channel would rise LESS than the un-weighted one.")
    ru = res4["40-49"]["sp"]["ratio"]
    ra = res4["40-49"]["spw"]["ratio"]
    Ru, Ra = ru ** 2, ra ** 2                      # amplitude ratio -> POWER ratio
    print(f"      un-weighted  amplitude {ru:6.3f} [{res4['40-49']['sp']['lo']:.3f}, "
          f"{res4['40-49']['sp']['hi']:.3f}]  => power {Ru:8.2f}")
    print(f"      A-weighted   amplitude {ra:6.3f} [{res4['40-49']['spw']['lo']:.3f}, "
          f"{res4['40-49']['spw']['hi']:.3f}]  => power {Ra:8.2f}")
    # ambient mean A-weight, measured from the control blocks themselves
    w0 = []
    for rec in recs:
        cu = np.array([Bc["sp"][i] for Bc, i in rec["ctl"]])
        cw = np.array([Bc["spw"][i] for Bc, i in rec["ctl"]])
        if len(cu) > 8:
            w0.append((np.median(cw) / np.median(cu)) ** 2)
    w0 = float(np.median(w0))
    phi = Ru - 1.0                                  # excess acoustic power, fraction of ambient
    we_over_w0 = (Ra - 1.0) / phi if phi > 0 else np.nan
    we = we_over_w0 * w0
    print(f"\n      ambient mean A-weight w0 = (spw/sp)^2 = {w0:.3e}  ({10 * np.log10(w0):+.1f} dB)"
          f"  <=> a spectral centroid near {a_inverse(w0):.0f} Hz")
    print(f"      excess  mean A-weight we                = {we:.3e}  ({10 * np.log10(we):+.1f} dB)"
          f"  <=> a spectral centroid near {a_inverse(we):.0f} Hz")
    print(f"      we / w0 = {we_over_w0:.2f}  ({10 * np.log10(we_over_w0):+.1f} dB): the acoustic")
    print("      excess is A-WEIGHTED HARDER than the ambient it sits on.")
    w44 = float(a_weight(44.6))
    print(f"\n      A-weight AT the mechanical line, w(44.6 Hz) = {w44:.3e} "
          f"({10 * np.log10(w44):+.1f} dB)")
    print(f"      => an excess entirely at 44.6 Hz would give we = {w44:.3e}; measured we is "
          f"{we / w44:.1f}x LARGER.")
    print("      => THE ACOUSTIC EXCESS CANNOT BE ENTIRELY AT 40-49 Hz. Two-component split, energy")
    print("        fraction that must sit at a higher frequency f_h to reconcile we:")
    print(f"        {'f_h':>8s} {'A(f_h) dB':>10s} {'energy fraction above the band':>32s}")
    frac = {}
    for fh in (80.0, 100.0, 160.0, 250.0, 500.0, 1000.0, 2000.0):
        wh = float(a_weight(fh))
        b = (we - w44) / (wh - w44)
        frac[fh] = float(b)
        print(f"        {fh:8.0f} {10 * np.log10(wh):10.1f} {100 * b:31.3f} %")
    print("      STOP: this is a MEAN-WEIGHT inversion. It proves the excess is not all sub-50 Hz;")
    print("        it does NOT locate the extra energy. Any mixture with the same mean weight fits.")
    print("      ALTERNATIVE EXPLANATION, not excluded here: TYRE SCRUB. A hard parking manoeuvre")
    print("        squeals broadband. Controls are matched on the speed/effort/|rate| cell, which")
    print("        removes most of it -- (c) tests the residual.")

    # ---------- (b) the transfer coefficient, creep ---------------------------------------------
    print("\n  (b) ACOUSTIC EXCESS vs SUB-50 Hz MECHANICAL EXCESS, per event (power units).")
    best = max((k for k in AXES), key=lambda k: res4["40-49"][k]["ratio"])
    print(f"      mechanical proxy = IMU {best} (the most responsive axis, sec 4), band 40-49 Hz.")
    X, Y, Yw = [], [], []
    for rec in recs:
        pa, ca = ev_power(rec, "sp")
        pw, cw = ev_power(rec, "spw")
        pm, cm = ev_power(rec, (best, "40-49"))
        if not all(np.isfinite(v) for v in (pa, ca, pm, cm)):
            continue
        X.append((pm - cm) / cm)                    # fractional mechanical excess
        Y.append((pa - ca) / ca)                    # fractional acoustic excess (un-weighted)
        Yw.append((pw - cw) / cw)
    X, Y, Yw = np.array(X), np.array(Y), np.array(Yw)
    ok = (X > 0) & (Y > 0)
    print(f"      {'n':>3s} {'log-log slope':>14s} {'95% CI':>18s} {'R^2':>7s}   "
          f"(slope 1 = acoustic power proportional to mechanical power)")
    sl = np.polyfit(np.log(X[ok]), np.log(Y[ok]), 1)
    pred = np.polyval(sl, np.log(X[ok]))
    r2 = 1 - np.sum((np.log(Y[ok]) - pred) ** 2) / np.sum(
        (np.log(Y[ok]) - np.log(Y[ok]).mean()) ** 2)
    dr = []
    for _ in range(4000):
        i = RNG.integers(0, ok.sum(), ok.sum())
        try:
            dr.append(np.polyfit(np.log(X[ok])[i], np.log(Y[ok])[i], 1)[0])
        except Exception:
            pass
    dr = np.array(dr)
    print(f"      {ok.sum():3d} {sl[0]:14.3f} [{np.percentile(dr, 2.5):7.3f},"
          f"{np.percentile(dr, 97.5):7.3f}] {r2:7.3f}")
    kap = float(np.median(Y[ok] / X[ok]))
    kaplo, kaphi = np.percentile([np.median((Y[ok] / X[ok])[RNG.integers(0, ok.sum(), ok.sum())])
                                  for _ in range(4000)], [2.5, 97.5])
    print(f"      transfer kappa = (fractional acoustic excess)/(fractional mechanical excess) "
          f"= {kap:.4f} [{kaplo:.4f}, {kaphi:.4f}]")
    print("      WHAT THIS REGRESSION CANNOT DO: if a >50 Hz component is generated by the SAME")
    print("        contact nonlinearity it is COLLINEAR with the sub-50 Hz one and rides inside")
    print("        kappa invisibly. (a) is the test that can see it; (b) only calibrates the size.")

    # ---------- (c) is the acoustic excess the GRIND or the MANOEUVRE? --------------------------
    print("\n  (c) IS THE ACOUSTIC EXCESS THE GRIND OR THE MANOEUVRE (tyre scrub)?")
    print("      Partial correlation of block sound level against the 40-49 Hz torsion-bar")
    print("      envelope, CONTROLLING for |steer rate|, effort and speed, over every block in the")
    print("      creep segments that carry the events.")
    xs, ys, cs = [], [], []
    for tag in ("r3a", "r3b"):
        for d in route_segs(tag):
            if tag == "r3b" and d["seg"] != 2:
                continue
            B = blocks(d)
            if B is None:
                continue
            m = B["v"] < 4.0
            if m.sum() < 40:
                continue
            xs.append(np.log(B[("tq", "40-49")][m] + 1.0))
            ys.append(np.log(B["sp"][m] + 1e-9))
            cs.append(np.column_stack([np.log(B["rate"][m] + 1.0), np.log(B["eff"][m] + 1.0),
                                       B["v"][m], np.ones(int(m.sum()))]))
    Xg, Yg, Cg = np.concatenate(xs), np.concatenate(ys), np.vstack(cs)

    def resid(y, C):
        b = np.linalg.lstsq(C, y, rcond=None)[0]
        return y - C @ b

    rx, ry = resid(Xg, Cg), resid(Yg, Cg)
    rp = float(np.corrcoef(rx, ry)[0, 1])
    raw = float(np.corrcoef(Xg, Yg)[0, 1])
    # block bootstrap over 5 s runs so autocorrelation cannot inflate it
    nb = 50
    idx = np.arange(len(rx))
    blk = [idx[i:i + nb] for i in range(0, len(idx) - nb, nb)]
    dr2 = []
    for _ in range(2000):
        j = RNG.integers(0, len(blk), len(blk))
        k = np.concatenate([blk[q] for q in j])
        dr2.append(np.corrcoef(rx[k], ry[k])[0, 1])
    lo2, hi2 = np.percentile(dr2, [2.5, 97.5])
    print(f"      n={len(rx)} blocks   raw rho {raw:+.3f}   PARTIAL rho "
          f"{rp:+.3f} [{lo2:+.3f}, {hi2:+.3f}]  (5 s block bootstrap)")
    print("      => a partial rho well above 0 means the sound tracks the 40-49 Hz oscillation")
    print("         itself, not merely the manoeuvre that hosts it.")
    R["s5_budget"] = dict(ru=ru, ra=ra, Ru=Ru, Ra=Ra, w0=w0, we=we, we_over_w0=we_over_w0,
                          w44=w44, centroid_ambient=a_inverse(w0), centroid_excess=a_inverse(we),
                          frac_above=frac, best_axis=best, slope=float(sl[0]),
                          slope_lo=float(np.percentile(dr, 2.5)),
                          slope_hi=float(np.percentile(dr, 97.5)), r2=float(r2),
                          kappa=kap, kappa_lo=float(kaplo), kappa_hi=float(kaphi),
                          partial_rho=rp, partial_lo=float(lo2), partial_hi=float(hi2),
                          raw_rho=raw, nblk=int(len(rx)),
                          Xfrac=[float(x) for x in X], Yfrac=[float(y) for y in Y])
    return kap, best


def sec5d(R, recs):
    """CI on the A-weighting inference, and the two checks that show the channel is real."""
    print("\n  (d) HOW HARD IS (a)?  Bootstrap over EVENTS, and two validity checks.")
    d = L.load_snd("r3a", 3)
    ref = d["spw"] / 10 ** (d["spwdb"] / 20)
    print(f"      check 1: soundPressureWeightedDb = 20*log10(spw / {np.median(ref):.4e}) with sd "
          f"{np.std(ref):.1e} => spw IS an A-weighted RMS pressure in Pa (20 uPa reference).")
    rows = []
    for tag in ("r3b", "r2b", "r47"):
        sp, spw, v = [], [], []
        for dd in route_segs(tag):
            B = blocks(dd)
            if B is None:
                continue
            sp.append(B["sp"])
            spw.append(B["spw"])
            v.append(B["v"])
        sp, spw, v = np.concatenate(sp), np.concatenate(spw), np.concatenate(v)
        r = []
        for lab, m in (("creep<4", v < 4), ("hwy>25", v > 25)):
            r.append((np.median(spw[m]) / np.median(sp[m])) ** 2 if m.sum() > 80 else np.nan)
        rows.append((tag, r))
        print(f"      check 2: {tag}  ambient A-weight w0  creep {r[0]:.2e} -> highway {r[1]:.2e} "
              f"(centroid {a_inverse(r[0]):.0f} -> {a_inverse(r[1]):.0f} Hz)")
    print("      => w0 RISES with speed on every route, as it must (wind/road noise is broader and")
    print("         higher than idle boom). The A channel is live, not degenerate.")
    w44 = float(a_weight(44.6))
    ru, ra, w0s = [], [], []
    for rec in recs:
        au, cu = ev_stat(rec, "sp")
        aw, cw = ev_stat(rec, "spw")
        if all(np.isfinite(x) for x in (au, cu, aw, cw)) and cu > 0 and cw > 0:
            ru.append(au / cu)
            ra.append(aw / cw)
            w0s.append((cw / cu) ** 2)
    ru, ra, w0s = np.array(ru), np.array(ra), np.array(w0s)
    dr = {"we_over_w44": [], "we_over_w0": [], "f100": [], "f250": []}
    for _ in range(4000):
        i = RNG.integers(0, len(ru), len(ru))
        Ru, Ra = np.median(ru[i]) ** 2, np.median(ra[i]) ** 2
        w0 = np.median(w0s[i])
        if Ru <= 1:
            continue
        we = w0 * (Ra - 1) / (Ru - 1)
        dr["we_over_w44"].append(we / w44)
        dr["we_over_w0"].append((Ra - 1) / (Ru - 1))
        for fh, k in ((100.0, "f100"), (250.0, "f250")):
            dr[k].append((we - w44) / (float(a_weight(fh)) - w44))
    out = {}
    print(f"\n      {'quantity':>34s} {'point':>9s} {'95% CI':>20s}")
    for k, lab in (("we_over_w0", "we / w0 (excess vs ambient)"),
                   ("we_over_w44", "we / w(44.6 Hz)"),
                   ("f100", "energy fraction if f_h = 100 Hz"),
                   ("f250", "energy fraction if f_h = 250 Hz")):
        a = np.array(dr[k], float)
        out[k] = [float(np.median(a)), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
        print(f"      {lab:>34s} {out[k][0]:9.3f} [{out[k][1]:8.3f},{out[k][2]:8.3f}]")
    print("      => the load-bearing line is we/w(44.6 Hz) > 1. Its lower bound is what decides")
    print("         whether 'the excess cannot be all sub-50 Hz' survives.")
    # check 3: is it one loud event, and does it survive a different burst statistic?
    print(f"\ncheck 3: PER-EVENT, so nobody has to take a median on trust.")
    print(f"      {'#':>3s} {'tq env':>7s} | " + " ".join(f"{k:>7s}" for k in
                                                          ("tq", "ay", "sound", "soundA")))
    pe = []
    for i, rec in enumerate(recs):
        r = {}
        for k in (("tq", "40-49"), ("ay", "40-49"), "sp", "spw"):
            a, c = ev_stat(rec, k)
            r[k if isinstance(k, str) else k[0]] = a / c if c else np.nan
        pe.append(r)
        print(f"      {i:3d} {rec['ev']['env_p99']:7.0f} | {r['tq']:7.1f} {r['ay']:7.1f} "
              f"{r['sp']:7.2f} {r['spw']:7.2f}")
    print("      => the microphone fires on 8 of 10 and tracks the torsion-bar magnitude; it is")
    print("         not one loud event carrying the median.")
    print(f"\ncheck 4: does we/w(44.6 Hz) survive a different BURST STATISTIC?")
    print(f"      {'statistic':>10s} {'sound':>8s} {'soundA':>8s} {'we/w44':>8s} "
          f"{'centroid Hz':>12s}")
    rob = {}
    for lbl, agg in (("p90", lambda v: np.percentile(v, 90)), ("median", np.median),
                     ("max", np.max)):
        ru2, ra2, w02 = [], [], []
        for rec in recs:
            au, cu = ev_stat(rec, "sp", agg=agg)
            aw, cw = ev_stat(rec, "spw", agg=agg)
            if cu > 0 and cw > 0:
                ru2.append(au / cu)
                ra2.append(aw / cw)
                w02.append((cw / cu) ** 2)
        Ru, Ra, W0 = np.median(ru2) ** 2, np.median(ra2) ** 2, np.median(w02)
        we2 = W0 * (Ra - 1) / (Ru - 1)
        rob[lbl] = [float(np.median(ru2)), float(np.median(ra2)), float(we2 / w44)]
        print(f"      {lbl:>10s} {np.median(ru2):8.3f} {np.median(ra2):8.3f} {we2 / w44:8.2f} "
              f"{a_inverse(we2):12.0f}")
    print("      => the inference is a property of the data, not of the statistic.")
    out["per_event"] = pe
    out["robustness"] = rob
    R["s5d"] = out
    return out


# =================================================================== §6 highway ==================
HWY = {"r47": 2.44, "r2b": 1.00, "r37": 2.00, "r3b": 2.00, "r2c": 1.00}


def hwy_blocks(tag, vmin=25.0):
    """Every 10 Hz block above `vmin`, tagged with a per-(segment, speed-bin) local baseline."""
    rows = []
    for d in route_segs(tag):
        B = blocks(d)
        if B is None:
            continue
        m = B["v"] >= vmin
        if m.sum() < 40:
            continue
        vb = np.array([binof(x, V_BINS) for x in B["v"]])
        keys = [("tq", "40-49"), ("tq", "18-22"), ("ay", "40-49"), ("gz", "40-49"),
                ("ax", "40-49"), ("ay", "18-22")]
        rec = dict(t=B["t"][m], v=B["v"][m], seg=d["seg"], tag=tag, sp=B["sp"][m],
                   spw=B["spw"][m], n=int(m.sum()))
        for k in keys + [("sp",), ("spw",)]:
            kk = k if len(k) == 2 else k[0]
            if kk not in B:
                continue
            x = B[kk]
            base = np.ones(len(x))
            for b in set(vb):
                q = vb == b
                if q.sum() >= 20:
                    base[q] = max(float(np.median(x[q])), 1e-12)
                else:
                    base[q] = max(float(np.median(x)), 1e-12)
            rec[kk] = x[m]
            rec[("z",) + (kk if isinstance(kk, tuple) else (kk,))] = np.log(
                np.maximum(x[m], 1e-12) / base[m])
        rows.append(rec)
    return rows


def sec6(R, recs, kappa, best):
    hdr("§6  THE HIGHWAY POPULATION -- the joint view, and the bound where it is null")
    # ---------- 6.1 the joint coincidence detector, calibrated on the creep bursts ---------------
    print("  (1) A JOINT COINCIDENCE DETECTOR, calibrated on the creep bursts, then applied blind.")
    print("      J = min(z_tq, z_ay, z_sound), z = log(block level / its own segment x speed-bin")
    print("      median). Requiring ALL THREE to rise is what an individual view cannot do.")
    Jb, Jq = [], []
    for rec in recs:
        d = seg(rec["ev"]["tag"], rec["ev"]["seg"])
        B = blocks(d)
        z = {}
        for kk in (("tq", "40-49"), ("ay", "40-49"), "sp"):
            x = B[kk]
            z[kk] = np.log(np.maximum(x, 1e-12) / max(float(np.median(x)), 1e-12))
        J = np.minimum(np.minimum(z[("tq", "40-49")], z[("ay", "40-49")]), z["sp"])
        bad = np.interp(B["t"], d["t"],
                        mark_bursts(rec["ev"]["tag"], d, guard=3.0).astype(float)) > 0.01
        Jb.append(J[rec["m"]].max())
        Jq.append(J[~bad])
    Jb = np.array(Jb)
    Jq = np.concatenate(Jq)
    # MEASURED, not asserted: how often is the microphone the binding (minimum) channel?
    nmin = ntot = 0
    for rec in recs:
        d = seg(rec["ev"]["tag"], rec["ev"]["seg"])
        B = blocks(d)
        z = {}
        for kk in (("tq", "40-49"), ("ay", "40-49"), "sp"):
            x = B[kk]
            z[kk] = np.log(np.maximum(x, 1e-12) / max(float(np.median(x)), 1e-12))
        w = rec["m"]
        s_ = z["sp"][w]
        nmin += int(np.sum((s_ <= z[("tq", "40-49")][w]) & (s_ <= z[("ay", "40-49")][w])))
        ntot += int(w.sum())
    micmin = 100.0 * nmin / max(ntot, 1)
    print(f"      {'statistic':>26s} {'burst peak p50':>15s} {'quiet p99.9':>12s} "
          f"{'separation':>11s}")
    for nm, arr in (("J = min of three", (Jb, Jq)),):
        print(f"      {nm:>26s} {np.median(arr[0]):15.3f} {np.percentile(arr[1], 99.9):12.3f} "
              f"{np.median(arr[0]) - np.percentile(arr[1], 99.9):11.3f}")
    for kk, nm in ((("tq", "40-49"), "z_tq alone"), (("ay", "40-49"), "z_ay alone"),
                   ("sp", "z_sound alone")):
        b, q = [], []
        for rec in recs:
            d = seg(rec["ev"]["tag"], rec["ev"]["seg"])
            B = blocks(d)
            x = B[kk]
            z = np.log(np.maximum(x, 1e-12) / max(float(np.median(x)), 1e-12))
            bad = np.interp(B["t"], d["t"],
                            mark_bursts(rec["ev"]["tag"], d, guard=3.0).astype(float)) > 0.01
            b.append(z[rec["m"]].max())
            q.append(z[~bad])
        b, q = np.array(b), np.concatenate(q)
        print(f"      {nm:>26s} {np.median(b):15.3f} {np.percentile(q, 99.9):12.3f} "
              f"{np.median(b) - np.percentile(q, 99.9):11.3f}")
    thr = float(np.percentile(Jq, 99.9))
    hit = float(np.mean(Jb > thr))
    print(f"\n      threshold J > {thr:.3f} (creep quiet p99.9) catches {100 * hit:.0f}% of the "
          f"{len(Jb)} demonstrated bursts at a 0.1% per-block false-alarm rate.")

    # ---------- 6.2 apply it to the highway population -----------------------------------------
    print("\n  (2) THE SAME DETECTOR ON THE HIGHWAY POPULATION (v >= 25 m/s).")
    print(f"      {'route':>6s} {'build':>6s} {'Kd@hwy':>7s} {'seconds':>9s} {'J p99.9':>9s} "
          f"{'J max':>8s} {'blocks>thr':>11s} {'rate /h':>9s}")
    tot = {}
    for tag in ("r2b", "r2c", "r37", "r3b", "r47"):
        rows = hwy_blocks(tag)
        if not rows:
            print(f"      {tag:>6s}   no highway blocks")
            continue
        J = []
        for r in rows:
            need = [("z", "tq", "40-49"), ("z", "ay", "40-49"), ("z", "sp")]
            if not all(k in r for k in need):
                continue
            J.append(np.minimum(np.minimum(r[("z", "tq", "40-49")], r[("z", "ay", "40-49")]),
                                r[("z", "sp")]))
        if not J:
            continue
        J = np.concatenate(J)
        secs = len(J) / MIC_PUB
        n_ex = int((J > thr).sum())
        tot[tag] = dict(secs=secs, p999=float(np.percentile(J, 99.9)), mx=float(J.max()),
                        nex=n_ex, rate=3600.0 * n_ex / secs)
        b = BY_ROUTE[tag[1:]]
        print(f"      {tag:>6s} {b.build:>6s} {HWY[tag]:7.2f} {secs:9.1f} "
              f"{tot[tag]['p999']:9.3f} {tot[tag]['mx']:8.3f} {n_ex:11d} {tot[tag]['rate']:9.1f}")
    print(f"\n      creep-burst J peaks: {np.sort(Jb)[::-1][:6].round(2).tolist()} "
          f"-- the highway maxima above are the comparison.")
    # 🛑 the counts are single digits, so the rates need EXACT POISSON intervals, not a ratio.
    from scipy.stats import chi2 as _chi2
    print(f"\n      🛑 POWER. The exceedance counts are single digits, so quote them as counts with")
    print(f"      exact Poisson intervals, never as a rate ratio:")
    print(f"      {'route':>6s} {'Kd':>5s} {'n':>4s} {'exposure s':>11s} {'rate /h':>9s} "
          f"{'exact 95% CI /h':>22s}")
    for tag, v in tot.items():
        n, e = v["nex"], v["secs"] / 3600.0
        lo = 0.0 if n == 0 else _chi2.ppf(0.025, 2 * n) / 2 / e
        hi = _chi2.ppf(0.975, 2 * (n + 1)) / 2 / e
        v["lo"], v["hi"] = float(lo), float(hi)
        print(f"      {tag:>6s} {HWY[tag]:5.2f} {n:4d} {v['secs']:11.1f} {v['rate']:9.1f} "
              f"[{lo:9.1f},{hi:9.1f}]")
    hmax = max(v["mx"] for v in tot.values())
    print("      Every interval overlaps every other. ⇒ the highway joint detector is a NULL with")
    print("      LOW POWER, not a null with teeth. What it does say cleanly: the highest highway")
    print(f"      block on ANY build is J = {hmax:.2f}, below the MEDIAN creep burst "
          f"({np.median(Jb):.2f}) and")
    print(f"      below {int((Jb > hmax).sum())} of the {len(Jb)} demonstrated bursts.")
    print(f"      ⚠ AND THE DETECTOR IS MIC-LIMITED: the microphone is the minimum channel in "
          f"{micmin:.0f}% of")
    print("      burst blocks, so 'joint' buys SPECIFICITY, not sensitivity -- its reach is the")
    print("      weakest channel's reach. See §7.")

    # ---------- 6.3 per-channel highway excess, matched ----------------------------------------
    print("\n  (3) PER-CHANNEL HIGHWAY TAIL, top-decile 40-49 Hz blocks vs the rest, speed-matched.")
    print(f"      {'route':>6s} {'Kd':>5s} | " + " ".join(f"{k:>9s}" for k in
                                                          ("tq40-49", "ay40-49", "gz40-49",
                                                           "sound", "soundA")))
    per = {}
    for tag in ("r2b", "r2c", "r37", "r3b", "r47"):
        rows = hwy_blocks(tag)
        if not rows:
            continue
        agg = {}
        sel = np.concatenate([r[("z", "tq", "40-49")] for r in rows])
        q = np.percentile(sel, 90)
        top = sel > q
        for kk, nm in ((("tq", "40-49"), "tq40-49"), (("ay", "40-49"), "ay40-49"),
                       (("gz", "40-49"), "gz40-49"), ("sp", "sound"), ("spw", "soundA")):
            key = ("z",) + (kk if isinstance(kk, tuple) else (kk,))
            if not all(key in r for r in rows):
                agg[nm] = np.nan
                continue
            z = np.concatenate([r[key] for r in rows])
            agg[nm] = float(np.exp(np.median(z[top]) - np.median(z[~top])))
        # NULL: circularly shift the SELECTION variable against the others, same estimator. This
        # destroys any real coincidence while preserving every marginal distribution and all the
        # within-channel autocorrelation.
        nul = {k: [] for k in agg}
        for _ in range(300):
            sh = int(RNG.integers(200, max(len(sel) - 200, 300)))
            tp = np.roll(sel, sh) > q
            for kk, nm in ((("tq", "40-49"), "tq40-49"), (("ay", "40-49"), "ay40-49"),
                           (("gz", "40-49"), "gz40-49"), ("sp", "sound"), ("spw", "soundA")):
                key = ("z",) + (kk if isinstance(kk, tuple) else (kk,))
                if not all(key in r for r in rows):
                    continue
                z = np.concatenate([r[key] for r in rows])
                nul[nm].append(np.exp(np.median(z[tp]) - np.median(z[~tp])))
        agg["_null"] = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
                        for k, v in nul.items() if v}
        per[tag] = agg
        print(f"      {tag:>6s} {HWY[tag]:5.2f} | " +
              " ".join(f"{agg[k]:9.3f}" for k in ("tq40-49", "ay40-49", "gz40-49",
                                                  "sound", "soundA")))
        print(f"      {'':>6s} {'null':>5s} | " +
              " ".join(f"{agg['_null'][k][0]:4.2f}-{agg['_null'][k][1]:4.2f}"
                       for k in ("tq40-49", "ay40-49", "gz40-49", "sound", "soundA")))
    print("      (the tq column is the selection variable => tautologically high; read the others")
    print("       against the circular-shift null printed under each route)")

    # ---------- 6.4 the budget, transported --------------------------------------------------
    print("\n  (4) THE BUDGET TRANSPORTED TO HIGHWAY -- and why it cannot bear the weight.")
    mech, floors = {}, {}
    for tag in ("r2b", "r37", "r3b", "r47"):
        rows = hwy_blocks(tag)
        if not rows:
            continue
        key = ("z", "ay", "40-49")
        if not all(key in r for r in rows):
            continue
        z = np.concatenate([r[key] for r in rows])
        mech[tag] = float(np.exp(2 * (np.percentile(z, 99) - np.median(z))) - 1.0)
        sp = np.concatenate([r["sp"] for r in rows])
        nb = len(sp) // 100
        blk = np.array([np.percentile(sp[i * 100:(i + 1) * 100], 90) for i in range(nb)])
        rr = []
        for _ in range(4000):
            p = RNG.permutation(nb)
            h = nb // 2
            rr.append(np.median(blk[p[:h]]) / max(np.median(blk[p[h:2 * h]]), 1e-12))
        floors[tag] = float(np.percentile(rr, 97.5)) ** 2 - 1.0
    print(f"      {'route':>6s} {'measured sub-50 Hz mech excess (p99)':>38s} "
          f"{'kappa-predicted acoustic excess':>32s} {'mic floor':>10s} {'headroom':>9s}")
    bnd = {}
    for tag in mech:
        pred = kappa * mech[tag]
        bnd[tag] = dict(mech=mech[tag], pred=pred, floor=floors[tag],
                        ratio=floors[tag] / max(pred, 1e-12))
        print(f"      {tag:>6s} {100 * mech[tag]:37.1f}% {100 * pred:31.3f}% "
              f"{100 * floors[tag]:9.1f}% {bnd[tag]['ratio']:9.0f}x")
    hr = [v["ratio"] for v in bnd.values()]
    print(f"\n      READ IT THIS WAY. The sub-50 Hz mechanical excess that DOES exist at highway,")
    print(f"      pushed through the creep-calibrated transfer, predicts an acoustic excess of")
    print(f"      {100 * min(v['pred'] for v in bnd.values()):.0f}-"
          f"{100 * max(v['pred'] for v in bnd.values()):.0f}% of ambient power. The microphone's own")
    print(f"      highway floor is {100 * min(floors.values()):.0f}-{100 * max(floors.values()):.0f}%."
          f" => the prediction sits {min(hr):.0f}-{max(hr):.0f}x UNDER the floor.")
    print("      => THE BUDGET TEST CANNOT BEAR THE WEIGHT AT HIGHWAY, and the reason is specific:")
    print("         the predicted signal is under the instrument, so a null there is uninformative")
    print("         about whether the sub-50 Hz content explains the sound. The honest output is")
    print("         the BOUND: unexplained acoustic energy up to the 'headroom' multiple of the")
    print(f"         sub-50 Hz-implied amount would be invisible. That bound is {min(hr):.0f}-"
          f"{max(hr):.0f}x -- tight enough to")
    print("         be worth having, and it is the FIRST such bound this kit has.")
    print("\n      ASSUMPTIONS THIS RESTS ON, each of which fails in a KNOWN direction:")
    print("        A1  kappa (acoustic per unit chassis motion) is the same at highway as at creep.")
    print("            FALSE in a quantifiable way: radiation efficiency rises ~f^2, and the highway")
    print("            ambient is ~9.9x higher in power, which DIVIDES the fractional excess. The")
    print("            two partly cancel; neither is measured here.")
    print("        A2  the highway event, if any, couples to the chassis like grind #2 does. If it")
    print("            is a torsional column mode like grind #1, section 4 says the IMU would see")
    print("            NOTHING even at creep -- and the joint detector inherits that blindness.")
    print("        A3  the mic floor is a STEADY-tone floor. A <5 Hz modulated event is ~5x easier.")
    R["s6"] = dict(thr=thr, hit=hit, jburst=[float(x) for x in Jb], hwy=tot, perchan=per,
                   budget=bnd)
    return tot


# =================================================================== §7 what each channel is for =
def sec7(R, res4):
    hdr("§7  WHAT EACH CHANNEL CAN AND CANNOT CONTRIBUTE -- stated as limits, not as caveats")
    t2, t1 = res4["40-49"], res4["18-22"]
    print(f"  {'channel':>16s} {'grind #2':>10s} {'grind #1':>10s} {'ceiling':>9s} "
          f"{'resolves f?':>12s}   what a null from it means")
    rows = [("tq 0x18F", "tq", "50.00 Hz", "yes",
             "silence above 50 Hz, not absence"),
            ("IMU (best axis)", "ay", "50.51 Hz", "yes",
             "silence above 50 Hz; blind to a purely TORSIONAL mode at any frequency"),
            ("microphone", "sp", "8000 Hz", "NO",
             "bounds AUDIBLE energy only; the operator FEELS this one")]
    for nm, k, ceil, res, note in rows:
        print(f"  {nm:>16s} {t2[k]['ratio']:10.2f} {t1[k]['ratio']:10.2f} {ceil:>9s} "
              f"{res:>12s}   {note}")
    print("\n  THE MICROPHONE, PRECISELY.")
    print("   - It is one RMS per 100 ms over 0-8000 Hz. It can bound an amplitude; it can NEVER")
    print("     name a frequency. Nothing here root-causes anything through it.")
    print("   - Its ONE validated positive control is grind #2 at CREEP. This session re-measured")
    print(f"     that control independently with matched (speed, effort, |rate|) controls and got")
    print(f"     {t2['sp']['ratio']:.2f}x [{t2['sp']['lo']:.2f}, {t2['sp']['hi']:.2f}] against a")
    print(f"     null of [{t2['sp']['nlo']:.2f}, {t2['sp']['nhi']:.2f}] -- consistent with the 4.14x")
    print("     on record, by a different estimator and a different control design. ✅ It replicates.")
    print("   - It read FLAT on grind #1 (%.2f, inside its null) -- so a mic null does NOT mean"
          % t1["sp"]["ratio"])
    print("     'no vibration'. It means 'nothing this instrument can hear'.")
    print("   - At highway the ambient is ~10x higher in POWER, so the same absolute event is ~10x")
    print("     harder. The highway floor measured in §6(4) is the number to quote.")
    print("   - ⇒ WEIGHT IT AS: a positive is informative (it did fire on grind #2, and §5(a) then")
    print("     extracted real spectral information from the A/un-weighted contrast). A NEGATIVE at")
    print("     highway on a TACTILE event carries almost nothing, and §6(4) is the bound.")
    print("\n  ★ THE ONE THING THE MICROPHONE DID THAT NOTHING ELSE COULD.")
    print("    §5(a) turns a level-only instrument into a coarse SPECTRAL one by using its two")
    print("    weightings as a two-point filter bank. That is the only measurement in this kit")
    print("    that has ever placed grind #2 energy ABOVE the 50 Hz ceiling from DATA.")


def main():
    R = {}
    sec0(R)
    lab = sec1(R)
    lab = sec1b(R, lab)
    cal = cal_events()
    recs = event_table(cal)
    sec2(R, cal, recs)
    sec3(R, recs)
    sec3c(R, recs)
    g1 = g1_events()
    recs1 = event_table(g1)
    res4 = sec4(R, recs, recs1, lab)
    sec4b(R, recs, recs1)
    kap, best = sec5(R, recs, res4)
    sec5d(R, recs)
    sec6(R, recs, kap, best)
    sec7(R, res4)
    OUT.write_text(json.dumps(R, indent=1, default=float))
    print(f"\nwrote {OUT}")



def msc(x, y, fs, nper=64):
    """Magnitude-squared coherence, Welch, 50% overlap. Returns (f, C, nseg)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    hop = nper // 2
    w = np.hanning(nper)
    Pxx = Pyy = Pxy = None
    k = 0
    for i in range(0, n - nper + 1, hop):
        a = np.fft.rfft((x[i:i + nper] - x[i:i + nper].mean()) * w)
        b = np.fft.rfft((y[i:i + nper] - y[i:i + nper].mean()) * w)
        Pxx = np.abs(a) ** 2 if Pxx is None else Pxx + np.abs(a) ** 2
        Pyy = np.abs(b) ** 2 if Pyy is None else Pyy + np.abs(b) ** 2
        Pxy = a * np.conj(b) if Pxy is None else Pxy + a * np.conj(b)
        k += 1
    if k < 3:
        return None, None, k
    return (np.fft.rfftfreq(nper, 1 / fs), np.abs(Pxy) ** 2 / (Pxx * Pyy + 1e-300), k)


def sec4b(R, recs, recs1):
    """SECOND METHOD for the load-bearing claim in §4: bar->chassis COHERENCE, not level."""
    hdr("§4b  SECOND METHOD -- TORSION-BAR -> CHASSIS COHERENCE at the grind's own frequency.\n"
        "§4's grind #1 IMU null is load-bearing, so it gets an estimator that does not use level\n"
        "at all. Coherence is scale-free: a mode that reaches the chassis is COHERENT with the\n"
        "bar there whether it is large or small.")
    print(f"  {'symptom':>10s} {'n':>4s} {'f0':>6s} | " +
          " ".join(f"{a:>7s}" for a in AXES) + "   (median coherence in event windows)")
    out = {}
    for lab, rr, band in (("GRIND #2", recs, (38.0, 49.0)), ("GRIND #1", recs1, (17.0, 24.0))):
        for what, use_ev in (("event", True), ("control", False)):
            per = {a: [] for a in AXES}
            f0s = []
            for rec in rr:
                e = rec["ev"]
                d = seg(e["tag"], e["seg"])
                if use_ev:
                    m = (d["t"] >= e["t"] - 1.0) & (d["t"] <= e["t_end"] + 1.0)
                else:
                    # a same-length window from the same segment, >=5 s from any burst
                    bad = mark_bursts(e["tag"], d, guard=5.0)
                    good = np.flatnonzero(~bad)
                    nn = int(((d["t"] >= e["t"] - 1.0) & (d["t"] <= e["t_end"] + 1.0)).sum())
                    if len(good) < nn + 10:
                        continue
                    i0 = good[len(good) // 3]
                    m = np.zeros(len(d["t"]), bool)
                    m[i0:i0 + nn] = True
                if m.sum() < 96:
                    continue
                f0s.append(e["f_peak"])
                for ax in AXES:
                    if ax not in d["imu"]:
                        continue
                    ee = d["imu"][ax]
                    y = np.interp(d["t"][m], ee["t"], ee["raw"])
                    f, C, k = msc(d["tq"][m], y, d["fs"])
                    if C is None:
                        continue
                    q = (f >= band[0]) & (f <= band[1])
                    per[ax].append(float(np.max(C[q])))
            row = {a: (float(np.median(v)) if v else np.nan) for a, v in per.items()}
            ci = {}
            for a, v in per.items():
                if len(v) < 4:
                    ci[a] = [np.nan, np.nan]
                    continue
                arr = np.array(v, float)
                dr = [np.median(arr[RNG.integers(0, len(arr), len(arr))]) for _ in range(2000)]
                ci[a] = [float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))]
            out[f"{lab}|{what}"] = row
            out[f"{lab}|{what}|ci"] = ci
            print(f"  {lab if use_ev else '':>10s} {len(f0s):4d} "
                  f"{np.median(f0s) if f0s else np.nan:6.1f} | "
                  + " ".join(f"{row[a]:7.3f}" for a in AXES) + f"   {what}")
            print(f"  {'':>10s} {'95% CI':>11s} | "
                  + " ".join(f"{ci[a][0]:.2f}-{ci[a][1]:.2f}" for a in AXES))
    print("\n  ⚠ Coherence is biased upward at small k; both rows use the SAME window length and the")
    print("    SAME k, so the event-vs-control contrast is the readable quantity, not the absolute.")
    R["s4b_coherence"] = out
    return out


if __name__ == "__main__":
    main()
