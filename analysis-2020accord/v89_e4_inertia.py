#!/usr/bin/env python3
r"""THE OPERATOR'S NEW HYPOTHESIS, tested on routes 73/75/76.

    "The firmware does not account for the fact that a large LKAS motor torque, acting against the
     steering-wheel/column INERTIA, shows up on the column torque sensor as an apparent DRIVER
     torque in the OPPOSITE direction -- so the assist law fights its own overlay."

THREE TESTS, each with its control run FIRST.

T1  SIGN AND CORRELATION, command -> column, engaged, per band 0.2-12 Hz.
    🛑 CHANNEL CHOICE MATTERS AND STATE.md §3 IS THE REASON.  `gp-0x6b98` is the TOTAL motor command
    INCLUDING base assist, and base assist is a function of column torque, so a naive cmd<->column
    coherence is loop feedthrough (0.254 engaged vs 0.544 MANUAL, where the LKAS command is
    identically absent).  This file therefore uses **openpilot's own request on CAN 0x0E4** as the
    command: it is computed from the CAMERA and the planned path, NOT from the column torque, so it
    is EXOGENOUS to the EPS loop.  Its only path to the column is through the car.
    CONTROL A: the MANUAL arm -- openpilot keeps computing 0x0E4 while `latActive` is false, and the
        EPS ignores it.  Same signal, not applied.  That is the ideal placebo, and whether it exists
        is checked (not assumed) before it is used.
    CONTROL B: a circular TIME SHIFT of the command inside its own engagement run -- identical
        spectra, destroyed timing.

T2  IS THE APPARENT TORQUE MAGNITUDE-PROPORTIONAL OR RATE/ACCELERATION-PROPORTIONAL?
    An inertial reaction must scale with |d^2 cmd/dt^2| (or at least |d cmd/dt|); a friction /
    load-proportional mechanism scales with |cmd|.  Regress log e_6-9 on each, and jointly, with
    log e_32-38 as the control response.
    🛑 CONTROL: the three regressors are collinear by construction if the command's spectral SHAPE
    is constant.  Their pairwise correlations are printed BEFORE any coefficient is read.

T3  ORDER OF MAGNITUDE.  A pure inertia gives |T_bar / alpha| FLAT in frequency and a phase of ~0
    between T_bar and alpha (equivalently ~180 deg between T_bar and the wheel ANGLE).  That shape
    test is SCALE-FREE and is the informative half.  The absolute size needs a counts -> N.m scale,
    which opendbc does not carry ("tbd"), so the only anchor available is openpilot's own Honda
    `STEER_THRESHOLD = 1200` counts for "the driver is holding the wheel" ~ 1 N.m.  That is quoted
    with an explicit +-3x uncertainty and every derived number is flagged BELIEF.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))

import _r31_common as C31        # noqa: E402
import _grind2_lib as G          # noqa: E402
import _r4f_lib as R4F           # noqa: E402

R4F.install_fs()
RNG = np.random.default_rng(89_4444)
OUTJ = ROOT / "_cache_r75" / "v89_e4_inertia.json"

ARMS = {"V88/r73": (ROOT / "_cache_r73", "r73s", list(range(11))),
        "V89/r75": (ROOT / "_cache_r75", "r75s", list(range(16))),
        "V89/r76": (ROOT / "_cache_r76", "r76s", list(range(13)))}
NFFT, HOP = 256, 128
T1_BANDS = [(0.2, 1.0), (1.0, 3.0), (0.2, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0)]
# counts -> N.m anchor.  BELIEF, +-3x.  openpilot honda/values.py STEER_THRESHOLD = 1200 counts is
# the threshold at which the driver is judged to be holding the wheel; a nudge is ~1 N.m.
CT_PER_NM = 1200.0
J_COLUMN_LO, J_COLUMN_HI = 0.03, 0.05    # kg.m^2, steering wheel + upper column, passenger car
OUT = {}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def bp(x, fs, lo, hi):
    return filtfilt(*butter(2, [lo, hi], btype="band", fs=fs), np.asarray(x, float))


def load_arm(name):
    cache, pfx, segs = ARMS[name]
    out = []
    for s in segs:
        if not (cache / f"{pfx}{s}.npz").exists():
            continue
        d = C31.load(s, cache, pfx)
        out.append((s, d, R4F.fs_lattice(d) if hasattr(R4F, "fs_lattice") else 100.0))
    return out


def fs_of(d):
    from _r31_common import fs_of as f
    return f(d)


# =================================================================================================
# T1 -- SIGN AND CORRELATION
# =================================================================================================
def t1_windows(name, engaged, shift_s=0.0):
    """Per-window band correlation r(cmd, column torque) and cross-spectral phase."""
    cache, pfx, segs = ARMS[name]
    rows = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, cache, pfx)
        fs = fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        mask = lat if engaged else ~lat
        cmd_full = np.asarray(d["e4tq"], float)
        tq_full = np.asarray(d["tq"], float)
        for a, b in C31.runs_of(mask, d["t"], NFFT):
            c = cmd_full[a:b].copy()
            if shift_s:
                k = int(round(shift_s * fs)) % max(len(c), 1)
                c = np.roll(c, k)
            y = tq_full[a:b]
            if not (np.all(np.isfinite(c)) and np.all(np.isfinite(y))):
                continue
            filt = {}
            for lo, hi in T1_BANDS:
                filt[(lo, hi)] = (bp(c, fs, lo, hi), bp(y, fs, lo, hi))
            nwin = 0
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(i, i + NFFT)
                r = dict(build=name, seg=s, eng=int(engaged),
                         blk=(name, s, a, nwin // 8),
                         v=float(np.mean(np.abs(d["cs_v"][a + i:a + i + NFFT]))),
                         cmd_abs=float(np.mean(np.abs(c[sl]))))
                for (lo, hi), (cf, yf) in filt.items():
                    x, z = cf[sl], yf[sl]
                    sx, sz = np.std(x), np.std(z)
                    key = f"{lo}-{hi}"
                    r["r_" + key] = (float(np.mean((x - x.mean()) * (z - z.mean())) / (sx * sz))
                                     if sx > 0 and sz > 0 else np.nan)
                    # cross-spectral phase at the band's power-weighted centre
                    X, Z = np.fft.rfft(x * np.hanning(NFFT)), np.fft.rfft(z * np.hanning(NFFT))
                    f = np.fft.rfftfreq(NFFT, 1 / fs)
                    m = (f >= lo) & (f <= hi)
                    Sxz = np.sum(Z[m] * np.conj(X[m]))
                    r["ph_" + key] = float(np.degrees(np.angle(Sxz)))
                    r["coh_" + key] = float(np.abs(Sxz) ** 2 /
                                            (np.sum(np.abs(X[m]) ** 2) * np.sum(np.abs(Z[m]) ** 2))
                                            if m.any() else np.nan)
                nwin += 1
                rows.append(r)
    return rows


def boot_med(rs, key, nboot=2000):
    grp = {}
    for r in rs:
        v = r.get(key, np.nan)
        if np.isfinite(v):
            grp.setdefault(r["blk"], []).append(v)
    per = list(grp.values())
    if len(per) < 4:
        return np.nan, np.nan, np.nan, 0
    allv = np.concatenate([np.array(p) for p in per])
    dr = np.empty(nboot)
    for i in range(nboot):
        j = RNG.integers(0, len(per), len(per))
        dr[i] = np.median(np.concatenate([np.array(per[k]) for k in j]))
    return (float(np.median(allv)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)), len(allv))


def t1():
    hdr("T1  SIGN AND CORRELATION -- openpilot's 0x0E4 request (EXOGENOUS) vs the column torque\n"
        "    If the operator is right, the column carries a component ANTI-PHASE to the command,\n"
        "    i.e. r < 0 and phase near 180 deg, ENGAGED and NOT in the controls.")
    OUT["t1"] = {}
    sub("CONTROL A's precondition -- is openpilot's 0x0E4 request actually PRESENT while manual?")
    for name in ARMS:
        cache, pfx, segs = ARMS[name]
        d = C31.load(segs[0], cache, pfx)
        allm, alle = [], []
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            dd = C31.load(s, cache, pfx)
            lat = np.asarray(dd["cc_lat"], float) > 0.5
            alle.append(np.abs(dd["e4tq"])[lat])
            allm.append(np.abs(dd["e4tq"])[~lat])
        e = np.concatenate(alle)
        m = np.concatenate(allm)
        print(f"    {name:10s} |0x0E4| engaged median {np.median(e):7.1f} (n={len(e):,})   "
              f"MANUAL median {np.median(m):7.1f} (n={len(m):,})   "
              f"manual non-zero {100*np.mean(m > 0):.1f} %")
        OUT["t1"][f"e4_presence/{name}"] = dict(eng_med=float(np.median(e)),
                                                man_med=float(np.median(m)),
                                                man_nonzero=float(np.mean(m > 0)))

    for name in ARMS:
        sub(f"{name}")
        E = t1_windows(name, True)
        M = t1_windows(name, False)
        S = t1_windows(name, True, shift_s=5.0)
        print(f"    engaged {len(E)} windows   manual {len(M)}   time-shifted control {len(S)}")
        print(f"    {'band':>10s} | {'r ENGAGED [CI]':>26s} {'r MANUAL [CI]':>26s} "
              f"{'r SHIFTED [CI]':>26s} | {'phase eng':>10s} {'coh eng':>8s}")
        for lo, hi in T1_BANDS:
            k = f"{lo}-{hi}"
            re_ = boot_med(E, "r_" + k)
            rm = boot_med(M, "r_" + k)
            rs_ = boot_med(S, "r_" + k)
            ph = np.array([r["ph_" + k] for r in E if np.isfinite(r["ph_" + k])])
            phm = float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(ph)))))) if len(ph) else np.nan
            co = boot_med(E, "coh_" + k)
            print(f"    {k:>10s} | {re_[0]:7.3f} [{re_[1]:6.3f},{re_[2]:6.3f}] "
                  f"{rm[0]:7.3f} [{rm[1]:6.3f},{rm[2]:6.3f}] "
                  f"{rs_[0]:7.3f} [{rs_[1]:6.3f},{rs_[2]:6.3f}] | {phm:9.1f}° {co[0]:8.3f}")
            OUT["t1"][f"{name}/{k}"] = dict(r_eng=list(re_[:3]), r_man=list(rm[:3]),
                                            r_shift=list(rs_[:3]), phase_eng=phm,
                                            coh_eng=list(co[:3]))


# =================================================================================================
# T2 -- MAGNITUDE vs RATE vs ACCELERATION
# =================================================================================================
def t2_windows(name):
    cache, pfx, segs = ARMS[name]
    rows = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, cache, pfx)
        fs = fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        cmd = np.asarray(d["e4tq"], float)
        d1 = np.gradient(cmd) * fs
        d2 = np.gradient(d1) * fs
        tq = np.asarray(d["tq"], float)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        for a, b in C31.runs_of(lat, d["t"], NFFT):
            nwin = 0
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(a + i, a + i + NFFT)
                w = tq[sl]
                r = dict(build=name, seg=s, blk=(name, s, a, nwin // 8),
                         e69=G.win_env(w, fs, 6.0, 9.0, taper, cw),
                         e3238=G.win_env(w, fs, 32.0, 38.0, taper, cw),
                         x_mag=float(np.sqrt(np.mean(cmd[sl] ** 2))),
                         x_d1=float(np.sqrt(np.mean(d1[sl] ** 2))),
                         x_d2=float(np.sqrt(np.mean(d2[sl] ** 2))),
                         v=float(np.mean(np.abs(d["cs_v"][sl]))),
                         rate=float(np.mean(np.abs(d["rate_c"][sl]))))
                nwin += 1
                rows.append(r)
    return rows


def ols(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b


def t2():
    hdr("T2  IS IT MAGNITUDE- OR ACCELERATION-PROPORTIONAL?  Regress log e_6-9 (and the 32-38 Hz\n"
        "    CONTROL) on log rms|cmd|, log rms|dcmd/dt|, log rms|d2cmd/dt2| in the SAME windows.")
    W = []
    for name in ARMS:
        W += t2_windows(name)
    W = [r for r in W if all(np.isfinite(r[k]) and r[k] > 0
                             for k in ("e69", "e3238", "x_mag", "x_d1", "x_d2", "v", "rate"))]
    print(f"    {len(W)} engaged windows over all three routes")
    lm, l1, l2 = (np.log([r[k] for r in W]) for k in ("x_mag", "x_d1", "x_d2"))
    sub("🛑 CONTROL FIRST -- COLLINEARITY of the three regressors.  If these are ~1.0 the "
        "discriminator cannot work and no coefficient below may be read as causal.")
    for (na, xa), (nb, xb) in (((("mag"), lm), ("d1", l1)), (("mag", lm), ("d2", l2)),
                               (("d1", l1), ("d2", l2))):
        print(f"    corr(log {na:3s}, log {nb:3s}) = {np.corrcoef(xa, xb)[0,1]:+.4f}")
    OUT["t2_collinearity"] = dict(mag_d1=float(np.corrcoef(lm, l1)[0, 1]),
                                  mag_d2=float(np.corrcoef(lm, l2)[0, 1]),
                                  d1_d2=float(np.corrcoef(l1, l2)[0, 1]))

    dum = {n: np.array([1.0 if r["build"] == n else 0.0 for r in W]) for n in ARMS}
    lv = np.log([max(r["v"], 0.05) for r in W])
    lr = np.log([max(r["rate"], 0.05) for r in W])
    base = [dum[n] for n in ARMS] + [lv, lr]
    blks = np.array([str(r["blk"]) for r in W])
    ublk = np.unique(blks)
    idxof = {b: np.where(blks == b)[0] for b in ublk}

    def fit(y, cols, nboot=1500):
        X = np.column_stack(base + cols)
        b = ols(y, X)[len(base):]
        D = np.empty((nboot, len(cols)))
        for i in range(nboot):
            pick = np.concatenate([idxof[ublk[j]] for j in
                                   RNG.integers(0, len(ublk), len(ublk))])
            D[i] = ols(y[pick], X[pick])[len(base):]
        return b, np.percentile(D, 2.5, axis=0), np.percentile(D, 97.5, axis=0)

    OUT["t2"] = {}
    for resp, y in (("e_6-9 (RATCHET)", np.log([r["e69"] for r in W])),
                    ("e_32-38 (CONTROL)", np.log([r["e3238"] for r in W]))):
        sub(f"response = log {resp}   (route fixed effects + log v + log |rate| always included)")
        for tag, cols in (("|cmd|          alone", [lm]), ("|dcmd/dt|      alone", [l1]),
                          ("|d2cmd/dt2|    alone", [l2]),
                          ("all three JOINTLY", [lm, l1, l2])):
            b, lo, hi = fit(y, cols)
            names = (["mag"] if tag.startswith("|cmd|") else ["d1"] if tag.startswith("|dcmd")
                     else ["d2"] if tag.startswith("|d2") else ["mag", "d1", "d2"])
            txt = "   ".join(f"{n}: {bb:+.3f} [{l:+.3f},{h:+.3f}]"
                             for n, bb, l, h in zip(names, b, lo, hi))
            print(f"    {tag:22s} {txt}")
            OUT["t2"][f"{resp}/{tag.strip()}"] = {n: [float(bb), float(l), float(h)]
                                                  for n, bb, l, h in zip(names, b, lo, hi)}


# =================================================================================================
# T3 -- THE INERTIA'S OWN SIGNATURE AND SIZE
# =================================================================================================
def t3():
    hdr("T3  IS THE COLUMN TORQUE THE SHAPE OF AN INERTIAL REACTION?\n"
        "    A pure inertia gives |T_bar / alpha| FLAT in frequency and phase(T_bar, alpha) ~ 0.\n"
        "    That test is SCALE-FREE.  The absolute size then needs a counts->N.m anchor.")
    FB = [(2, 4), (4, 6), (6, 9), (9, 12), (12, 16), (16, 22), (26, 31)]
    OUT["t3"] = {}
    for name in ARMS:
        cache, pfx, segs = ARMS[name]
        acc = {f"{lo}-{hi}": [] for lo, hi in FB}
        phs = {f"{lo}-{hi}": [] for lo, hi in FB}
        angamp = {f"{lo}-{hi}": [] for lo, hi in FB}
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            d = C31.load(s, cache, pfx)
            fs = fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            th = np.radians(np.asarray(d["ang"], float))     # wheel angle, rad
            tq = np.asarray(d["tq"], float)                  # column torque, counts
            for a, b in C31.runs_of(lat, d["t"], NFFT):
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    w = np.hanning(NFFT)
                    TH = np.fft.rfft((th[sl] - th[sl].mean()) * w)
                    TQ = np.fft.rfft((tq[sl] - tq[sl].mean()) * w)
                    f = np.fft.rfftfreq(NFFT, 1 / fs)
                    AL = -((2 * np.pi * f) ** 2) * TH            # angular acceleration, rad/s^2
                    for lo, hi in FB:
                        m = (f >= lo) & (f <= hi)
                        pa = np.sum(np.abs(AL[m]) ** 2)
                        if pa <= 0:
                            continue
                        acc[f"{lo}-{hi}"].append(np.sqrt(np.sum(np.abs(TQ[m]) ** 2) / pa))
                        phs[f"{lo}-{hi}"].append(np.angle(np.sum(TQ[m] * np.conj(AL[m]))))
                        angamp[f"{lo}-{hi}"].append(
                            np.degrees(np.sqrt(np.sum(np.abs(TH[m]) ** 2)) / (NFFT / 2)))
        print(f"\n    {name}")
        print(f"    {'band Hz':>8s} {'|T/alpha| ct.s2/rad':>20s} {'-> J_eff kg.m2 (BELIEF)':>24s} "
              f"{'phase(T,alpha)':>15s} {'angle rms deg':>14s} {'n':>6s}")
        row = {}
        for lo, hi in FB:
            k = f"{lo}-{hi}"
            if len(acc[k]) < 20:
                continue
            J = float(np.median(acc[k]))
            ph = float(np.degrees(np.angle(np.mean(np.exp(1j * np.array(phs[k]))))))
            am = float(np.median(angamp[k]))
            print(f"    {k:>8s} {J:20.1f} {J/CT_PER_NM:24.4f} {ph:14.1f}° {am:14.4f} "
                  f"{len(acc[k]):6d}")
            row[k] = dict(ct_s2_per_rad=J, J_eff=J / CT_PER_NM, phase_deg=ph, ang_rms_deg=am,
                          n=len(acc[k]))
        OUT["t3"][name] = row
    print(f"\n    🛑 the quantisation floor: `ang` is 0.1 deg/LSB, so white quantisation noise "
          f"over a 3 Hz\n       slice of the 0-50 Hz band is ~{0.1/np.sqrt(12)*np.sqrt(3/50):.4f} "
          "deg rms.  Any row whose angle rms is\n       within ~3x of that is NOISE, not motion.")
    print(f"    🛑 counts->N.m anchor {CT_PER_NM:.0f} ct/N.m (openpilot honda STEER_THRESHOLD, "
          "+-3x).  BELIEF.")
    print(f"    ⊕ a real steering wheel + upper column is J ~ {J_COLUMN_LO}-{J_COLUMN_HI} kg.m2.")


if __name__ == "__main__":
    which = sys.argv[1:] or ["t1", "t2", "t3"]
    if "t1" in which:
        t1()
    if "t2" in which:
        t2()
    if "t3" in which:
        t3()
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
