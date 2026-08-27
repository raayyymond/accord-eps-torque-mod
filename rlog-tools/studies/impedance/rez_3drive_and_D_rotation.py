#!/usr/bin/env python3
r"""Extend the measured driving-point Re(Z) to 6-35 Hz on THREE drives, with controls, and rotate
the firmware D branch through the MEASURED phase to settle its sign in the grinding bands.

READ-ONLY.  Re-implements the frozen estimator's arithmetic (`_xspec` / `_band_transfer` /
`_wins` from rlog-tools/probe/decode_v90_probe.py) verbatim, but keeps PER-WINDOW, PER-BAND
accumulators so the whole thing can be episode-bootstrapped and split-half'd.

CONTROLS RUN BEFORE THE MEASUREMENT AND PRINTED FIRST:
  C1  reproduction of the frozen route-77 numbers, band by band
  C2  shuffled-pairs null (window i's torque against window j's rate)
  C3  phase-randomised surrogate (|Y(f)| preserved, phase iid uniform) -- the stronger null
  C4  split-half by EPISODE parity, within each drive
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
CACHE = ROOT / "analysis-2020accord" / "_scratch" / "cache"

RNG = np.random.default_rng(110_2026)
DEG2RAD = np.pi / 180.0
NW, HOP = 512, 256                 # the frozen 5.12 s window / 50 % hop
NBOOT = 4000

BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
         ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
# fine overlapping grid for the crossover
FINE = [(f"F{c:.1f}", c - 1.5, c + 1.5) for c in np.arange(14.0, 34.01, 0.5)]
ALL = BANDS + FINE

# ---- firmware-side branch transfers, from the image ------------------------------------------
FS_CTRL = 1000.0                   # control task tick, 1 kHz (pinned by D's own phase table)
KD_STOCK = 2048.0                  # cal(0xC6AE6)
POL = -1.0                         # gp-0x6752 = -1


def H_D(f, kd=KD_STOCK):
    """D branch, POL included.  H_D = POL*(Kd/1024)*(1 - z^-1),  aD = cal(0xC644A)=1024 = exact
    pass-through so the EMA is absent.  Reproduces the build's table: 0.09788 <-91.40 deg @7.79."""
    z1 = np.exp(-2j * np.pi * np.asarray(f, float) / FS_CTRL)
    return POL * (kd / 1024.0) * (1.0 - z1)


def H_P(f):
    return POL * 0.25 * np.ones_like(np.asarray(f, float), dtype=complex)


def H_I(f):
    """Pure accumulator, scaled so |H_I| = 0.0611 at 7.79 Hz (the build's tabulated value)."""
    z1 = np.exp(-2j * np.pi * np.asarray(f, float) / FS_CTRL)
    raw = 1.0 / (1.0 - z1)
    k = 0.0611 / abs(1.0 / (1.0 - np.exp(-2j * np.pi * 7.79 / FS_CTRL)))
    return POL * k * raw


# ---- data ------------------------------------------------------------------------------------
def runs_of(mask, t, min_n, max_gap=0.05):
    idx = np.flatnonzero(np.asarray(mask, bool))
    if not len(idx):
        return
    s = prev = idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > max_gap:
            if prev - s + 1 >= min_n:
                yield s, prev + 1
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        yield s, prev + 1


def load(route):
    z = np.load(CACHE / f"r{route}" / f"r{route}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    return dict(
        t=t,
        tq=np.asarray(z["tq"], float),                     # 0x18F bytes 0-1
        rate_f=np.asarray(z["rate_f"], float) * DEG2RAD,   # 0x18F bytes 2-3 -- SAME frame
        rate_c=np.asarray(z["rate_c"], float) * DEG2RAD,   # 0x14A -- the SKEWED control
        lat=np.asarray(z["cc_lat"], float) > 0.5,
        press=np.asarray(z["cs_press"], float) > 0.5,
        v=np.abs(np.asarray(z["cs_v"], float)),
        fs=1.0 / float(np.median(np.diff(t))),
    )


def accum(x, y, fs, extra_h=None):
    """Per-band scalars for ONE window, exactly the frozen estimator's arithmetic."""
    w = np.hanning(NW)
    X = np.fft.rfft((x - x.mean()) * w)
    Y = np.fft.rfft((y - y.mean()) * w)
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    Sxx = np.abs(X) ** 2
    Syy = np.abs(Y) ** 2
    Sxy = np.conj(X) * Y
    out = np.empty((len(ALL), 4), dtype=complex)
    for i, (_, lo, hi) in enumerate(ALL):
        m = (f >= lo) & (f <= hi)
        out[i, 0] = Sxx[m].sum()
        out[i, 1] = Syy[m].sum()
        out[i, 2] = Sxy[m].sum()
        out[i, 3] = (H_D(f[m]) * Sxy[m]).sum()      # <- the D-rotated cross spectrum
    return out, (f, Sxx, Syy, Sxy)


def build(route, arm="engaged", rate_key="rate_f"):
    d = load(route)
    v, lat, press = d["v"], d["lat"], d["press"]
    mask = {"engaged": lat & (~press) & (v > 0.5),
            "manual": (~lat) & (~press) & (v > 0.5),
            "engaged_on": lat & press & (v > 0.5),
            "manual_on": (~lat) & press & (v > 0.5)}[arm]
    t, tq, rate = d["t"], d["tq"], d[rate_key]
    A, ep, vs = [], [], []
    for k, (a, b) in enumerate(runs_of(mask, t, NW)):
        for i in range(0, (b - a) - NW + 1, HOP):
            sl = slice(a + i, a + i + NW)
            acc, _ = accum(rate[sl], tq[sl], d["fs"])
            A.append(acc)
            ep.append(k)
            vs.append(float(np.mean(np.abs(v[sl]))))
    return dict(route=route, arm=arm, fs=d["fs"], secs=float(mask.sum()) / d["fs"],
                A=(np.array(A) if A else np.zeros((0, len(ALL), 4), complex)),
                ep=np.array(ep, int), v=np.array(vs, float),
                n_ep=len(set(ep)))


def band_stats(A, idx=None):
    """Welch-aggregate a set of windows -> per-band Re(Z), |Z|, phase, coh2, and D's rotation."""
    S = A[idx].sum(axis=0) if idx is not None else A.sum(axis=0)
    sxx = np.real(S[:, 0])
    syy = np.real(S[:, 1])
    sxy = S[:, 2]
    hdsxy = S[:, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        rez = np.real(sxy) / sxx
        absz = np.abs(sxy) / sxx
        ph = np.degrees(np.angle(sxy))
        coh = np.abs(sxy) ** 2 / (sxx * syy)
        reZD = np.real(hdsxy) / sxx                 # D branch's own Re contribution, same units
        dnorm = -reZD / absz                        # D-SWEEP CONVENTION: negative == damping
    return dict(rez=rez, absz=absz, phase=ph, coh=coh, reZD=reZD, dnorm=dnorm, n=len(sxx))


def boot(A, ep, nboot=NBOOT):
    """Bootstrap over EPISODES (not windows)."""
    eps = np.unique(ep)
    byep = [np.flatnonzero(ep == e) for e in eps]
    out = {k: [] for k in ("rez", "absz", "phase", "coh", "reZD", "dnorm")}
    for _ in range(nboot):
        pick = RNG.integers(0, len(eps), len(eps))
        idx = np.concatenate([byep[p] for p in pick])
        s = band_stats(A, idx)
        for k in out:
            out[k].append(s[k])
    return {k: np.array(v) for k, v in out.items()}


def ci(arr, q=(2.5, 97.5)):
    return np.nanpercentile(arr, q[0], axis=0), np.nanpercentile(arr, q[1], axis=0)


NB = len(BANDS)
hdr = lambda s: print("\n" + "=" * 100 + f"\n{s}\n" + "=" * 100, flush=True)

# ==============================================================================================
if __name__ == "__main__":
    ROUTES = ["77", "78", "79"]

    hdr("CENSUS -- every arm, every route.  Windows of 5.12 s, >=1 per episode.")
    print(f"  {'route':7s} {'arm':12s} {'seconds':>9s} {'episodes':>9s} {'windows':>8s}")
    arms = {}
    for r in ROUTES:
        for a in ("engaged", "manual", "engaged_on", "manual_on"):
            b = build(r, a)
            arms[(r, a)] = b
            print(f"  r{r:6s} {a:12s} {b['secs']:9.1f} {b['n_ep']:9d} {len(b['A']):8d}")

    # ------------------------------------------------------------------ C1 reproduction
    hdr("C1  REPRODUCTION -- route 77 engaged, against the frozen v92_rez_extend.py output")
    s = band_stats(arms[("77", "engaged")]["A"])
    ref = {"2-4": (-1269.2, 1438.1, -152.0), "4-6": (-1418.5, 1944.2, -136.9),
           "6-9": (-3375.2, 5840.8, -125.3), "9-12": (-4593.1, 5650.7, -144.4),
           "12-16": (-3858.1, 3864.0, 176.8), "16-18": (-1610.7, 1941.7, 146.1),
           "18-22": (-652.5, 1296.1, 120.2), "22-26": (-267.8, 987.5, 105.7),
           "26-31": (232.9, 667.1, 69.6), "31-35": (772.9, 900.9, 30.9)}
    print(f"  {'band':7s} {'Re(Z) mine':>12s} {'frozen':>10s} {'|Z| mine':>10s} {'frozen':>9s} "
          f"{'ph mine':>9s} {'frozen':>8s} {'coh²':>7s}")
    ok = True
    for i, (nm, _, _) in enumerate(BANDS):
        a, b, c = ref[nm]
        ok &= abs(s["rez"][i] - a) < 1.0 and abs(s["phase"][i] - c) < 0.15
        print(f"  {nm:7s} {s['rez'][i]:12.1f} {a:10.1f} {s['absz'][i]:10.1f} {b:9.1f} "
              f"{s['phase'][i]:8.1f}° {c:7.1f}° {s['coh'][i]:7.3f}")
    print(f"\n  ⇒ REPRODUCES: {ok}")

    # ------------------------------------------------------------------ C2/C3 nulls
    hdr("C2/C3  NULLS.  C2 = shuffled pairs.  C3 = phase-randomised surrogate (|Y(f)| kept).")
    print("  Both are run on route 77 engaged, the arm every verdict rests on.")

    def nulls(route, arm):
        d = load(route)
        v, lat, press = d["v"], d["lat"], d["press"]
        mask = {"engaged": lat & (~press) & (v > 0.5),
                "manual": (~lat) & (~press) & (v > 0.5)}[arm]
        t, tq, rate = d["t"], d["tq"], d["rate_f"]
        wx, wy = [], []
        for a, b in runs_of(mask, t, NW):
            for i in range(0, (b - a) - NW + 1, HOP):
                sl = slice(a + i, a + i + NW)
                wx.append(rate[sl])
                wy.append(tq[sl])
        n = len(wx)
        idx = RNG.permutation(n)
        A2 = np.array([accum(wx[i], wy[(idx[i] + 1) % n], d["fs"])[0] for i in range(n)])
        w = np.hanning(NW)
        A3 = []
        for i in range(n):
            Y = np.fft.rfft((wy[i] - wy[i].mean()) * w)
            ph = RNG.uniform(-np.pi, np.pi, len(Y))
            ph[0] = 0.0
            Ys = np.abs(Y) * np.exp(1j * ph)
            ys = np.fft.irfft(Ys, NW)
            A3.append(accum(wx[i], ys / w.clip(1e-9), d["fs"])[0])
        return band_stats(A2), band_stats(np.array(A3)), n

    n2, n3, nw77 = nulls("77", "engaged")
    print(f"\n  {'band':7s} {'REAL Re(Z)':>12s} {'C2 shuf':>10s} {'C3 phrand':>11s} "
          f"| {'REAL coh²':>10s} {'C2 coh²':>9s} {'C3 coh²':>9s}   1/n = "
          f"{1.0/nw77:.4f}")
    for i, (nm, _, _) in enumerate(BANDS):
        print(f"  {nm:7s} {s['rez'][i]:12.1f} {n2['rez'][i]:10.1f} {n3['rez'][i]:11.1f} "
              f"| {s['coh'][i]:10.3f} {n2['coh'][i]:9.4f} {n3['coh'][i]:9.4f}")

    # ------------------------------------------------------------------ C4 split-half
    hdr("C4  SPLIT-HALF BY EPISODE PARITY, within each drive.  No pooling, no bootstrap.")
    for r in ROUTES:
        b = arms[(r, "engaged")]
        e = b["ep"]
        h0 = band_stats(b["A"], np.flatnonzero(e % 2 == 0))
        h1 = band_stats(b["A"], np.flatnonzero(e % 2 == 1))
        print(f"\n  route {r}: {b['n_ep']} episodes -> "
              f"{int((np.unique(e) % 2 == 0).sum())} / {int((np.unique(e) % 2 == 1).sum())}")
        print(f"    {'band':7s} {'Re(Z) even':>11s} {'Re(Z) odd':>11s} {'ph even':>9s} "
              f"{'ph odd':>8s} {'d even':>8s} {'d odd':>8s}")
        for i, (nm, _, _) in enumerate(BANDS):
            print(f"    {nm:7s} {h0['rez'][i]:11.1f} {h1['rez'][i]:11.1f} "
                  f"{h0['phase'][i]:8.1f}° {h1['phase'][i]:7.1f}° "
                  f"{h0['dnorm'][i]:8.4f} {h1['dnorm'][i]:8.4f}")

    # ------------------------------------------------------------------ MAIN, per drive
    hdr("MEASUREMENT 1 -- Re(Z), |Z|, phase, coherence.  PER DRIVE, engaged hands-off moving.")
    print("  🛑 |Z| is on `rate_f`, which reads 0.7996x true deg/s ⇒ every |Z| here is 1.2506x")
    print("     HIGH.  The TRUE column is |Z|/1.2506.  PHASE is untouched by a scale.")
    per = {}
    for r in ROUTES:
        b = arms[(r, "engaged")]
        st = band_stats(b["A"])
        bt = boot(b["A"], b["ep"])
        per[r] = (st, bt)
        print(f"\n  route {r} -- {len(b['A'])} windows / {b['n_ep']} episodes / {b['secs']:.0f} s")
        print(f"    {'band':7s} {'Re(Z)':>9s} {'[95% CI]':>21s} {'|Z|':>8s} {'|Z|true':>8s} "
              f"{'phase':>8s} {'[95% CI]':>18s} {'coh²':>6s}")
        lo, hi = ci(bt["rez"])
        plo, phi = ci(bt["phase"])
        for i, (nm, _, _) in enumerate(BANDS):
            print(f"    {nm:7s} {st['rez'][i]:9.0f} [{lo[i]:9.0f},{hi[i]:9.0f}] "
                  f"{st['absz'][i]:8.0f} {st['absz'][i]/1.2506:8.0f} "
                  f"{st['phase'][i]:7.1f}° [{plo[i]:7.1f},{phi[i]:7.1f}] {st['coh'][i]:6.3f}")

    # ------------------------------------------------------------------ POOLED
    hdr("MEASUREMENT 2 -- POOLED over the three calibration-identical drives, "
        "bootstrap over EPISODES")
    Ap = np.concatenate([arms[(r, "engaged")]["A"] for r in ROUTES])
    off, epp = 0, []
    for r in ROUTES:
        b = arms[(r, "engaged")]
        epp.append(b["ep"] + off)
        off += b["n_ep"]
    epp = np.concatenate(epp)
    sp = band_stats(Ap)
    bp = boot(Ap, epp)
    lo, hi = ci(bp["rez"])
    plo, phi = ci(bp["phase"])
    print(f"  {len(Ap)} windows / {len(np.unique(epp))} episodes / "
          f"{sum(arms[(r,'engaged')]['secs'] for r in ROUTES):.0f} s")
    print(f"\n  {'band':7s} {'Re(Z)':>9s} {'[95% CI]':>21s} {'P(<0)':>7s} {'|Z|true':>8s} "
          f"{'phase':>8s} {'[95% CI]':>18s} {'coh²':>6s}")
    for i, (nm, _, _) in enumerate(BANDS):
        p0 = float((bp["rez"][:, i] < 0).mean())
        print(f"  {nm:7s} {sp['rez'][i]:9.0f} [{lo[i]:9.0f},{hi[i]:9.0f}] {p0:7.3f} "
              f"{sp['absz'][i]/1.2506:8.0f} {sp['phase'][i]:7.1f}° "
              f"[{plo[i]:7.1f},{phi[i]:7.1f}] {sp['coh'][i]:6.3f}")

    # ------------------------------------------------------------------ CROSSOVER
    hdr("MEASUREMENT 3 -- the CROSSOVER frequency (Re(Z) = 0), 3 Hz sliding bands, "
        "bootstrap CI over episodes")

    def cross(S):
        r = np.real(S[NB:, 2]) / np.real(S[NB:, 0])
        c = np.array([float(x[0]) for x in
                      [(nm[1:],) for nm, _, _ in FINE]], float)
        for i in range(len(r) - 1):
            if r[i] < 0 <= r[i + 1]:
                return c[i] + (c[i + 1] - c[i]) * (-r[i]) / (r[i + 1] - r[i])
        return np.nan

    for tag, A, ep in [("r77", arms[("77", "engaged")]["A"], arms[("77", "engaged")]["ep"]),
                       ("r78", arms[("78", "engaged")]["A"], arms[("78", "engaged")]["ep"]),
                       ("r79", arms[("79", "engaged")]["A"], arms[("79", "engaged")]["ep"]),
                       ("POOLED", Ap, epp)]:
        pt = cross(A.sum(axis=0))
        eps = np.unique(ep)
        byep = [np.flatnonzero(ep == e) for e in eps]
        bs = []
        for _ in range(2000):
            pick = RNG.integers(0, len(eps), len(eps))
            bs.append(cross(A[np.concatenate([byep[p] for p in pick])].sum(axis=0)))
        bs = np.array(bs, float)
        bs = bs[np.isfinite(bs)]
        print(f"  {tag:7s} crossover = {pt:6.2f} Hz   95% CI "
              f"[{np.percentile(bs, 2.5):5.2f}, {np.percentile(bs, 97.5):5.2f}]  "
              f"({len(bs)}/2000 bootstraps had a crossing in 14-34 Hz)")

    # ------------------------------------------------------------------ D ROTATION
    hdr("MEASUREMENT 4 -- ROTATE THE D BRANCH THROUGH THE MEASURED PHASE\n"
        "  d = -Re(H_D(f)*Z(f))/|Z|, bin-by-bin inside each band, aggregated exactly like the\n"
        "  estimator.  CONVENTION = the kit's D-sweep convention: NEGATIVE d == DAMPING,\n"
        "  POSITIVE d == PUMPING.  (accord-anti-damping-is-not-the-pid states it explicitly.)")
    print(f"\n  {'band':7s} " + " ".join(f"{'r'+r:>9s}" for r in ROUTES) +
          f" {'POOLED':>9s} {'[95% CI]':>19s} {'P(damping)':>11s} {'verdict':>9s}")
    dlo, dhi = ci(bp["dnorm"])
    for i, (nm, _, _) in enumerate(BANDS):
        row = " ".join(f"{per[r][0]['dnorm'][i]:9.4f}" for r in ROUTES)
        pdamp = float((bp["dnorm"][:, i] < 0).mean())
        vd = "DAMPS" if sp["dnorm"][i] < 0 else "PUMPS"
        print(f"  {nm:7s} {row} {sp['dnorm'][i]:9.4f} [{dlo[i]:8.4f},{dhi[i]:8.4f}] "
              f"{pdamp:11.3f} {vd:>9s}")

    print("\n  Absolute contribution, ct·s/rad on the `rate_f` scale (divide by 1.2506 for true):")
    rlo, rhi = ci(bp["reZD"])
    print(f"  {'band':7s} {'-Re(Z_D) pooled':>16s} {'[95% CI]':>21s} "
          f"{'|Z| pooled':>11s} {'Re(Z) pooled':>13s}")
    for i, (nm, _, _) in enumerate(BANDS):
        print(f"  {nm:7s} {-sp['reZD'][i]:16.1f} [{-rhi[i]:9.1f},{-rlo[i]:9.1f}] "
              f"{sp['absz'][i]:11.1f} {sp['rez'][i]:13.1f}")

    # ------------------------------------------------------------------ P and I sanity
    hdr("SANITY -- reproduce the build's own +844 / +296 / -458 table from the 6-9 Hz row")
    f0, Z0 = 7.79, sp["absz"][2] * np.exp(1j * np.radians(sp["phase"][2]))
    Z77 = per["77"][0]["absz"][2] * np.exp(1j * np.radians(per["77"][0]["phase"][2]))
    for nm, H in (("P", H_P(f0)), ("I", H_I(f0)), ("D", H_D(f0))):
        h = complex(np.atleast_1d(H)[0])
        print(f"  {nm}:  |H| {abs(h):8.5f}  arg {np.degrees(np.angle(h)):+8.2f}°   "
              f"Re(Z*H) r77 = {np.real(Z77*h):+8.1f}   pooled = {np.real(Z0*h):+8.1f}")
    hs = complex(np.atleast_1d(H_P(f0))[0] + np.atleast_1d(H_I(f0))[0] +
                 np.atleast_1d(H_D(f0))[0])
    print(f"  P+I+D: |H| {abs(hs):8.5f}  arg {np.degrees(np.angle(hs)):+8.2f}°   "
          f"Re(Z*H) r77 = {np.real(Z77*hs):+8.1f}   pooled = {np.real(Z0*hs):+8.1f}")

    # ------------------------------------------------------------------ ROBUSTNESS
    hdr("ROBUSTNESS -- how big must an UN-MODELLED channel defect be to FLIP the verdict?")
    print("  The only thing that can flip d's sign is a rotation of the MEASURED phase.  Two\n"
          "  classes are swept: (a) a relative TRANSPORT DELAY tau between the tq and rate_f\n"
          "  fields inside the same 0x18F frame; (b) a single-pole LOW-PASS at fc on the torque\n"
          "  channel only (the candidate explanation for the un-modelled |Z| roll-off > 13 Hz).")
    fcent = {nm: 0.5 * (lo + hi) for nm, lo, hi in BANDS}
    fcent["6-9"] = 7.79
    KEY = ["6-9", "18-22", "26-31"]

    def d_at(nm, rot_deg):
        i = [b[0] for b in BANDS].index(nm)
        f = fcent[nm]
        h = complex(np.atleast_1d(H_D(f))[0])
        ph = np.radians(sp["phase"][i] + rot_deg)
        return -abs(h) * np.cos(ph + np.angle(h))

    print(f"\n  (a) TRANSPORT DELAY.  tau > 0 = torque field lags rate field (phase correction +wt)")
    print(f"      {'tau ms':>8s} " + " ".join(f"{k:>12s}" for k in KEY))
    for tau in (-15, -10, -6, -3, 0, 3, 6, 8.8, 10, 12, 15):
        vals = [d_at(k, 360.0 * fcent[k] * tau / 1000.0) for k in KEY]
        print(f"      {tau:8.1f} " + " ".join(
            f"{v:+8.4f} {'D' if v < 0 else 'P'} " for v in vals))
    print("      (D = damping, P = pumping, in the D-sweep convention)")

    print(f"\n  (b) SINGLE-POLE LOW-PASS on the torque channel, corner fc (correction = +atan(f/fc))")
    print(f"      {'fc Hz':>8s} " + " ".join(f"{k:>12s}" for k in KEY))
    for fc in (6, 8, 10, 13, 20, 30, 50, 1e6):
        vals = [d_at(k, np.degrees(np.arctan(fcent[k] / fc))) for k in KEY]
        print(f"      {fc:8.0f} " + " ".join(
            f"{v:+8.4f} {'D' if v < 0 else 'P'} " for v in vals))

    # ------------------------------------------------------------------ CHANNEL CONTROL
    hdr("CHANNEL CONTROL -- the same rotation computed on rate_c (0x14A), the SKEWED pair.\n"
        "  This is the documented sign-inverting choice.  Printed so the dependence is visible.")
    bc = build("77", "engaged", rate_key="rate_c")
    sc = band_stats(bc["A"])
    print(f"  {'band':7s} {'phase rate_f':>13s} {'phase rate_c':>13s} {'d rate_f':>10s} "
          f"{'d rate_c':>10s} {'coh_f':>7s} {'coh_c':>7s}")
    for i, (nm, _, _) in enumerate(BANDS):
        print(f"  {nm:7s} {per['77'][0]['phase'][i]:12.1f}° {sc['phase'][i]:12.1f}° "
              f"{per['77'][0]['dnorm'][i]:10.4f} {sc['dnorm'][i]:10.4f} "
              f"{per['77'][0]['coh'][i]:7.3f} {sc['coh'][i]:7.3f}")

    # ------------------------------------------------------------------ MANUAL ARM
    hdr("THE SECOND WAY IN -- is there a MANUAL hands-off arm on these routes?")
    for r in ROUTES:
        b = arms[(r, "manual")]
        print(f"  r{r}: manual hands-off moving = {b['secs']:.1f} s, {b['n_ep']} episodes, "
              f"{len(b['A'])} windows  -> {'SCOREABLE' if len(b['A']) >= 6 else '🛑 NOT SCOREABLE'}")
    Am = [arms[(r, "manual")] for r in ROUTES if len(arms[(r, "manual")]["A"])]
    tot = sum(len(a["A"]) for a in Am)
    print(f"  POOLED manual hands-off windows over all three drives: {tot}")
    if tot >= 6:
        Amc = np.concatenate([a["A"] for a in Am])
        sm = band_stats(Amc)
        print(f"\n  {'band':7s} {'Re(Z)':>10s} {'|Z|':>9s} {'phase':>8s} {'coh²':>7s}")
        for i, (nm, _, _) in enumerate(BANDS):
            print(f"  {nm:7s} {sm['rez'][i]:10.1f} {sm['absz'][i]:9.1f} "
                  f"{sm['phase'][i]:7.1f}° {sm['coh'][i]:7.3f}")
    print("\n  ENGAGED HANDS-ON (the symptom regime), for the record:")
    for r in ROUTES:
        b = arms[(r, "engaged_on")]
        print(f"  r{r}: {b['secs']:.1f} s, {b['n_ep']} episodes, {len(b['A'])} windows")
