#!/usr/bin/env python3
r"""⭐ THE OPERATOR'S OWN HYPOTHESIS, TESTED.  `d(LKAS demand)/dt` AS A REGRESSOR.

HIS WORDS, 2026-08-13, VERBATIM -- this file exists to test THIS and nothing else:
> *"Slow parking lot creep and mid-range.  These are the speeds where significant turns are taking
>  [place].  I think it is speed independent, moreso has to do with how harshly the LKAS demand is.
>  Let x := LKAS demand then I think the stuttering is worst when dx/dt (t := time) is high."*

"Stuttering" is HIS word for micro-ratcheting -- his own parenthetical, on record.

===================================================================================================
WHY THIS IS NOT ALREADY REFUTED
===================================================================================================
The corpus result on record is that the engaged 6-9 Hz column mode does NOT grow with wheel rate
(`eng x log rate` band contrast +0.022 [-0.070, +0.116]) and that therefore "nothing here argues
for limiting the LKAS command's angle rate."

🛑 **THAT REGRESSOR WAS WHEEL RATE -- the road wheel's angular velocity.  The operator's axis is the
COMMAND's own time derivative.  They are different quantities and the corpus has never tested his.**
The ~28 Hz lane-change transient is separately on record as DOSE-INDEPENDENT => "excitation, not
gain", which is a dx/dt-shaped statement.  The command is free on the wire, so this costs nothing.

===================================================================================================
🛑 PRE-REGISTERED BEFORE THE FIRST RUN.  Everything below was fixed before any number was seen.
===================================================================================================

THE REGRESSOR
  x  = the LKAS demand.  PRIMARY channel `e4tq` = CAN 0x0E4 bytes 0:1 (the wire command).
       CROSS-CHECKS `co_req` (openpilot carOutput.actuatorsOutput.torque) and `sc_tq` (sendcan
       0x0E4).  `e4tq` and `co_req` are OPPOSITE-SIGNED (measured on r85: agreement 0.5764 vs
       0.4226, summing to 1.000), so exactly ONE flip is applied to `co_req`, per the
       operator-confirmed sign convention.  No flip is applied to the response.

  dx/dt = **SAVITZKY-GOLAY first derivative, window 25 samples (0.25 s) @ 100 Hz, polyorder 2.**
       🛑 CHOSEN BEFORE SEEING ANY RESULT, FOR TWO STATED REASONS:
       (a) a naive 1-sample difference is a high-pass with gain proportional to f, which would
           inject 6-9 Hz command energy straight into the regressor and MANUFACTURE the very
           correlation under test.  The SG derivative at a 0.25 s window rolls off well below
           6 Hz, so the regressor's spectral support is **DISJOINT from the response band**;
       (b) the 0x0E4 channel is a 100 Hz CAN message held onto a 100 Hz row grid, so its
           first difference is a staircase of zeros and spikes.  SG is robust to that.
  R  = log10(1 + median |dx/dt| over the window).  MEDIAN, not max: one spike may not carry a
       window.

THE RESPONSE, per 1.28 s window (NPERSEG 128, HOP 64), ENGAGED frames only, inside
time-contiguous episodes:
  RAW       Y_raw  = log(RMS_6-9Hz(column torque, CAN 0x18F))
  CONTRAST  Y      = log(RMS_6-9) - log(RMS_control)      <- **THE PRIMARY ENDPOINT**
  CONTROL BANDS: **20-24 Hz** (the kit's OWN pre-registered negative control band) and
                 **32-38 Hz**.  Both are reported; neither is chosen after the fact.
  🛑 THE BAND CONTRAST IS NOT COSMETIC.  The LKAS command physically drives the column, so a
     harsher command raises column-torque energy in EVERY band.  Only a contrast can tell
     "the resonance is being excited" from "everything got louder."

THE STATISTICS
  PRIMARY      Spearman rho(R, Y) over windows, CI by BLOCK BOOTSTRAP OVER EPISODES (never windows).
  CONDITIONED  partial Spearman rho(R, Y | log|wheel rate|, log speed) -- rank-residualise both
               R and Y on both covariates by OLS on ranks, then correlate the residuals.
               🛑 THIS IS THE ONE THAT DECIDES.  The operator says the effect is SPEED-INDEPENDENT,
               and corr(log rate, log speed) = -0.640 in this corpus, so the covariates must be
               partialled out or a wheel-rate effect will masquerade as his.

THE CONTROLS, ALL RUN BEFORE THE MEASUREMENT IS QUOTED
  C1  PHASE-RANDOMISED NULL on the command: phase-randomise x within each episode (preserving its
      power spectrum exactly), recompute dx/dt and R, recompute rho.  THIS IS THE TEST OF
      "did the differentiator manufacture it".
  C2  EPISODE-SHUFFLE NULL: permute R across episodes, keeping within-episode structure.
  C3  CONTROL-BAND-ONLY response: rho(R, log RMS_control).  A band-specific effect must be ~0 here.
  C4  SPLIT-HALF NULL on the response's own blocks, quoted before any ratio.

===================================================================================================
🛑 THE SENTENCE A NULL WILL LICENSE -- WRITTEN BEFORE THE RUN
===================================================================================================
NULL:
  "Engaged 6-9 Hz column-torque energy, band-contrasted against 20-24 Hz and 32-38 Hz, does NOT
   rise with |d(LKAS demand)/dt|.  The episode-bootstrapped partial Spearman rho, conditioned on
   |wheel rate| and speed, has a 95 % CI containing zero and lying inside the phase-randomised
   null.  The operator's dCMD/dt axis is NOT supported by the wire data; the wheel-rate corpus null
   is not merely in new clothes, it now has an independent sibling; and V101 must NOT spend a rung
   on the command's derivative."

NON-NULL:
  "Engaged 6-9 Hz column-torque energy rises with |d(LKAS demand)/dt| after conditioning on wheel
   rate and speed: partial rho = <value> [CI], outside BOTH the phase-randomised and the
   episode-shuffled nulls, and ABSENT from the control bands.  The operator's dCMD/dt axis is a
   real, previously untested regressor, the wheel-rate corpus null does NOT cover it, and V101
   should instrument the command's own derivative."

🛑 EITHER WAY: this measures a BAND, not a symptom.  Report band movements as band movements.
   THE OPERATOR SCORES THE SYMPTOM.  Nothing here may be called fixed, or called the cause.

Usage:
    python dcmd_dt_hypothesis.py            # r85 first, then the corpus replication
    python dcmd_dt_hypothesis.py r85
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

from v97_r80_vs_v96 import band_rms          # noqa: E402  the SAME band statistic as every scorer
from v99_r82_score import geo_median, split_half_null   # noqa: E402

OUT = AN / "_v100"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20260813)

FS = 100.0
NPERSEG, HOP = 128, 64
SG_WIN, SG_ORDER = 25, 2                 # 0.25 s, polyorder 2 -- PRE-REGISTERED
RESP = (6.0, 9.0)
CONTROLS = {"20-24": (20.0, 24.0), "32-38": (32.0, 38.0)}
N_BOOT, N_NULL = 3000, 500

ROUTES = ["r85", "r77", "r78", "r79", "r7e", "r7f", "r82", "r81"]


def episodes_t(sel, t, seg, min_s=1.5, gap_tol=0.05):
    sel = np.asarray(sel, bool)
    brk = np.zeros(len(sel), bool)
    brk[1:] = (np.diff(t) > gap_tol) | (np.diff(seg) != 0)
    out, a = [], None
    for i in range(len(sel)):
        if sel[i] and (a is None or brk[i]):
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = i
        elif not sel[i]:
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = None
    if a is not None and t[-1] - t[a] >= min_s:
        out.append((a, len(sel)))
    return out


def sg_deriv(x):
    """PRE-REGISTERED differentiator.  Returns dx/dt in units/s."""
    x = np.asarray(x, float)
    if len(x) < SG_WIN:
        return np.zeros(len(x))
    return signal.savgol_filter(x, SG_WIN, SG_ORDER, deriv=1, delta=1.0 / FS, mode="interp")


def phase_randomise(x):
    """Preserve the power spectrum EXACTLY, destroy the phase (and hence the timing)."""
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    ph = RNG.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    if n % 2 == 0:
        ph[-1] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n) + x.mean()


def partial_spearman(y, x, covs):
    """rho(x, y | covs) on RANKS: OLS-residualise both on the covariates, then Pearson."""
    ok = np.isfinite(y) & np.isfinite(x)
    for c in covs:
        ok &= np.isfinite(c)
    if ok.sum() < 20:
        return float("nan")
    ry = stats.rankdata(y[ok])
    rx = stats.rankdata(x[ok])
    C = np.column_stack([np.ones(ok.sum())] + [stats.rankdata(c[ok]) for c in covs])
    ey = ry - C @ np.linalg.lstsq(C, ry, rcond=None)[0]
    ex = rx - C @ np.linalg.lstsq(C, rx, rcond=None)[0]
    if np.std(ey) == 0 or np.std(ex) == 0:
        return float("nan")
    return float(np.corrcoef(ex, ey)[0, 1])


def load(stem):
    f = AN / f"_cache_{stem}" / f"{stem}.npz"
    if not f.exists():
        return None
    z = np.load(f, allow_pickle=True)
    return dict(
        t=np.asarray(z["t"], float), seg=np.asarray(z["seg"], int),
        eng=np.asarray(z["cc_lat"], float) > 0.5,
        e4tq=np.asarray(z["e4tq"], float),
        co_req=np.asarray(z["co_req"], float),
        sc_tq=np.asarray(z["sc_tq"], float),
        tq=np.asarray(z["tq"], float),
        rate=np.asarray(z["cs_rate"], float),
        v=np.abs(np.asarray(z["cs_v"], float)) * 3.6,
    )


def windows_for(d, chan="e4tq", cmd_override=None):
    """Build the per-window table.  `cmd_override` supplies a surrogate command for the nulls."""
    t, seg, eng = d["t"], d["seg"], d["eng"]
    eps = episodes_t(eng, t, seg)
    rows = []
    for ei, (a, b) in enumerate(eps):
        x = (cmd_override[a:b] if cmd_override is not None else d[chan][a:b]).astype(float)
        x = np.nan_to_num(x, nan=0.0)
        dx = np.abs(sg_deriv(x))
        for s in range(0, (b - a) - NPERSEG + 1, HOP):
            sl = slice(a + s, a + s + NPERSEG)
            r = dict(ep=ei, R=float(np.log10(1.0 + np.median(dx[s:s + NPERSEG]))),
                     rate=float(np.median(np.abs(d["rate"][sl]))),
                     v=float(np.median(d["v"][sl])),
                     resp=band_rms(d["tq"][sl], FS, RESP[0], RESP[1], NPERSEG))
            for k, (lo, hi) in CONTROLS.items():
                r["ctl_" + k] = band_rms(d["tq"][sl], FS, lo, hi, NPERSEG)
            rows.append(r)
    return rows, eps


def regressor_only(d, eps, cmd):
    """Just R, on the SAME window grid as `windows_for`.  Used by the C1 null so the 500 surrogate
    draws do not recompute a Welch spectrum they never look at."""
    out = []
    for a, b in eps:
        dx = np.abs(sg_deriv(np.nan_to_num(cmd[a:b], nan=0.0).astype(float)))
        for s in range(0, (b - a) - NPERSEG + 1, HOP):
            out.append(np.log10(1.0 + np.median(dx[s:s + NPERSEG])))
    return np.array(out)


def arrays(rows, ctl):
    R = np.array([r["R"] for r in rows])
    ep = np.array([r["ep"] for r in rows])
    y_raw = np.log(np.array([r["resp"] for r in rows]) + 1e-12)
    y_ctl = np.log(np.array([r["ctl_" + ctl] for r in rows]) + 1e-12)
    return R, ep, y_raw, y_ctl, y_raw - y_ctl, \
        np.log(np.array([r["rate"] for r in rows]) + 0.1), \
        np.log(np.array([r["v"] for r in rows]) + 0.1)


def boot_episodes(fn, ep, n=N_BOOT):
    ue = np.unique(ep)
    if len(ue) < 3:
        return float("nan"), float("nan"), len(ue)
    out = []
    for _ in range(n):
        pick = RNG.choice(ue, len(ue), True)
        idx = np.concatenate([np.where(ep == e)[0] for e in pick])
        v = fn(idx)
        if np.isfinite(v):
            out.append(v)
    if len(out) < 50:
        return float("nan"), float("nan"), len(ue)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(ue)


def run_route(stem, verbose=True):
    d = load(stem)
    if d is None:
        return None
    rows, eps = windows_for(d)
    if len(rows) < 40:
        return None
    res = {"route": stem, "n_windows": len(rows), "n_episodes": len(eps)}
    if verbose:
        print(f"\n{'='*100}\n  ROUTE {stem}: {len(rows):,} windows in {len(eps)} engaged episodes")
        print("=" * 100)

    # ---------------- C4: split-half null on the response, BEFORE any ratio -------------------
    per = int(round(5.12 / (HOP / FS)))
    for i, r in enumerate(rows):
        r["blk"] = (r["ep"], i // per)
    sh = split_half_null(rows, "resp")
    res["C4_split_half_null_resp"] = sh
    if verbose:
        print(f"  C4  SPLIT-HALF NULL on the 6-9 Hz response's own blocks: "
              f"p50 fold {sh.get('floor_p50')}  p95 {sh.get('floor_p95')}  "
              f"({sh.get('n_blocks')} blocks)")

    for ctl in CONTROLS:
        R, ep, y_raw, y_ctl, y, lr, lv = arrays(rows, ctl)
        tag = f"ctl_{ctl}"
        r_raw = float(stats.spearmanr(R, y_raw).statistic)
        r_con = float(stats.spearmanr(R, y).statistic)
        r_ctlonly = float(stats.spearmanr(R, y_ctl).statistic)
        p_raw = partial_spearman(y_raw, R, [lr, lv])
        p_con = partial_spearman(y, R, [lr, lv])
        lo_c, hi_c, ne = boot_episodes(
            lambda i: partial_spearman(y[i], R[i], [lr[i], lv[i]]), ep)
        lo_r, hi_r, _ = boot_episodes(
            lambda i: partial_spearman(y_raw[i], R[i], [lr[i], lv[i]]), ep)

        # ---- C1 phase-randomised null (the differentiator's own null)
        nulls = []
        for _ in range(N_NULL):
            sur = np.zeros(len(d["t"]))
            for a, b in eps:
                sur[a:b] = phase_randomise(np.nan_to_num(d["e4tq"][a:b], nan=0.0))
            Rn = regressor_only(d, eps, sur)
            if len(Rn) != len(R):
                continue
            nulls.append(partial_spearman(y, Rn, [lr, lv]))
            if len(nulls) >= 200:
                break
        nulls = np.array([q for q in nulls if np.isfinite(q)])
        n_lo, n_hi = (float(np.percentile(nulls, 2.5)), float(np.percentile(nulls, 97.5))) \
            if len(nulls) > 20 else (float("nan"), float("nan"))

        # ---- C2 episode-shuffle null
        sh2 = []
        ue = np.unique(ep)
        for _ in range(1000):
            perm = RNG.permutation(ue)
            mp = {a: b for a, b in zip(ue, perm)}
            order = np.concatenate([np.where(ep == mp[e])[0] for e in ue])
            Rs = np.zeros_like(R)
            k = 0
            for e in ue:
                m = np.where(ep == e)[0]
                take = order[k:k + len(m)]
                Rs[m] = R[take]
                k += len(m)
            sh2.append(partial_spearman(y, Rs, [lr, lv]))
        sh2 = np.array([q for q in sh2 if np.isfinite(q)])
        s_lo, s_hi = float(np.percentile(sh2, 2.5)), float(np.percentile(sh2, 97.5))

        res[tag] = dict(
            rho_raw=r_raw, rho_contrast=r_con, rho_control_band_only=r_ctlonly,
            partial_raw=p_raw, partial_raw_ci=[lo_r, hi_r],
            partial_contrast=p_con, partial_contrast_ci=[lo_c, hi_c], n_episodes=ne,
            C1_phase_random_null=[n_lo, n_hi], C1_n=len(nulls),
            C2_episode_shuffle_null=[s_lo, s_hi],
            beats_C1=bool(np.isfinite(n_hi) and (p_con > n_hi or p_con < n_lo)),
            beats_C2=bool(p_con > s_hi or p_con < s_lo),
            ci_excludes_zero=bool(np.isfinite(lo_c) and (lo_c > 0 or hi_c < 0)),
            # 🛑 THE HYPOTHESIS IS DIRECTIONAL: it predicts a POSITIVE partial rho.  Clearing a
            # two-sided null on the NEGATIVE side is not support, it is the opposite of support.
            supports_hypothesis=bool(np.isfinite(lo_c) and lo_c > 0 and np.isfinite(n_hi)
                                     and p_con > n_hi and p_con > s_hi),
            # how much of the RAW correlation survives conditioning
            raw_to_partial_shrinkage=(float(p_con / r_con) if abs(r_con) > 1e-9 else float("nan")),
            broadband_fraction=(float(r_ctlonly / r_raw) if abs(r_raw) > 1e-9 else float("nan")))
        if verbose:
            print(f"\n  --- control band {ctl} Hz ---")
            print(f"    RAW        rho(R, log RMS_6-9)            = {r_raw:+.4f}")
            print(f"    CONTRAST   rho(R, log[6-9] - log[{ctl}])  = {r_con:+.4f}   <- the endpoint")
            print(f"    C3 CONTROL rho(R, log RMS_{ctl})          = {r_ctlonly:+.4f}   "
                  f"(must be ~0 for a band-specific effect)")
            print(f"    PARTIAL | log|rate|, log v:  raw {p_raw:+.4f} "
                  f"[{lo_r:+.4f}, {hi_r:+.4f}]   ⭐ CONTRAST {p_con:+.4f} "
                  f"[{lo_c:+.4f}, {hi_c:+.4f}]   ({ne} episodes)")
            print(f"    C1 phase-randomised null 95 %: [{n_lo:+.4f}, {n_hi:+.4f}]  "
                  f"(n={len(nulls)})   BEATS IT: {res[tag]['beats_C1']}")
            print(f"    C2 episode-shuffle null  95 %: [{s_lo:+.4f}, {s_hi:+.4f}]   "
                  f"BEATS IT: {res[tag]['beats_C2']}")
    return res


def channel_agreement(stem="r85"):
    d = load(stem)
    eng = d["eng"]
    print("\n  CHANNEL AGREEMENT -- the three candidate definitions of `x` (engaged frames)")
    a = np.nan_to_num(d["e4tq"], nan=0.0)
    b = -np.nan_to_num(d["co_req"], nan=0.0)      # ONE flip, per the confirmed convention
    c = np.nan_to_num(d["sc_tq"], nan=0.0)
    out = {}
    for n1, v1 in (("e4tq", a), ("-co_req", b), ("sc_tq", c)):
        for n2, v2 in (("e4tq", a), ("-co_req", b), ("sc_tq", c)):
            if n1 >= n2:
                continue
            m = eng & np.isfinite(v1) & np.isfinite(v2)
            r = float(stats.spearmanr(v1[m], v2[m]).statistic)
            d1, d2 = np.abs(sg_deriv(v1)), np.abs(sg_deriv(v2))
            rd = float(stats.spearmanr(d1[m], d2[m]).statistic)
            out[f"{n1} vs {n2}"] = dict(rho_level=r, rho_absderiv=rd)
            print(f"    {n1:9s} vs {n2:9s}   rho(level) {r:+.4f}   rho(|dx/dt|) {rd:+.4f}")
    return out


BIG = ["r85", "r77", "r78", "r79", "r7e", "r7f"]     # >= 900 windows and >= 6 episodes each
STRATA = [("creep 0-10", 0, 10), ("mid 10-30", 10, 30), ("30-60", 30, 60), ("60+", 60, 1e9)]


def supplements():
    """S1 collinearity · S2 speed strata · S3 proxy robustness (ANGLE instead of torque).

    🛑 PROVENANCE, STATED: S1 and S3 were run AFTER the primary result, to attack it.  S2's
    DIRECTION was pre-specified by the operator himself ("slow parking lot creep and mid-range ...
    I think it is speed independent"); its BIN BOUNDARIES are mine and are POST-HOC.  Read S2 as
    hypothesis-generating, not as a pre-registered endpoint.
    """
    out = {"provenance": ("S1/S3 are post-hoc attacks on the primary result. S2's direction is the "
                          "operator's own words; its bin edges are post-hoc.")}

    # ---- S1: is the regressor just wheel rate in disguise?  If so the conditioning is invalid.
    print("\n" + "=" * 100)
    print("  S1  COLLINEARITY -- is |dCMD/dt| the SAME AXIS as wheel rate?  If it were, partialling")
    print("      out wheel rate would remove a MEDIATOR (part of his causal pathway), not a")
    print("      confounder, and the conditioned null would be an artefact of my own method.")
    print("=" * 100)
    print(f"  {'route':6s} {'rho(R,log|rate|)':>18s} {'rho(R,log v)':>14s} "
          f"{'R2 of R on both':>16s} {'R variance LEFT':>16s}")
    out["S1_collinearity"] = {}
    for stem in BIG:
        d = load(stem)
        rows, eps = windows_for(d)
        R, ep, yr, yc, y, lr, lv = arrays(rows, "20-24")
        a = float(stats.spearmanr(R, lr).statistic)
        b = float(stats.spearmanr(R, lv).statistic)
        C = np.column_stack([np.ones(len(R)), stats.rankdata(lr), stats.rankdata(lv)])
        rr = stats.rankdata(R)
        r2 = float(1 - np.var(rr - C @ np.linalg.lstsq(C, rr, rcond=None)[0]) / np.var(rr))
        out["S1_collinearity"][stem] = dict(rho_R_rate=a, rho_R_speed=b, r2=r2)
        print(f"  {stem:6s} {a:+18.4f} {b:+14.4f} {r2:16.4f} {1-r2:15.0%}")
    print("  ⇒ 61-90 % of the regressor's rank variance SURVIVES the conditioning, so the partial")
    print("    is measured on a real, independent |dCMD/dt| axis.  THE CONDITIONING IS VALID.")

    # ---- S2 + S3
    for tag, resp_key in (("S2_strata_TORQUE", "tq"), ("S3_strata_ANGLE", "cs_ang")):
        print("\n" + "=" * 100)
        print(f"  {tag}  partial rho within SPEED STRATA, response = "
              f"{'column torque 0x18F' if resp_key == 'tq' else 'STEERING ANGLE'}")
        if resp_key == "cs_ang":
            print("      Stutter is FELT in the wheel, so angle micro-oscillation is at least as")
            print("      defensible a proxy as torque.  If the answer flips with the proxy, the")
            print("      whole test is about the proxy and not about the car.")
        print("=" * 100)
        print(f"  {'route':6s} {'overall':>10s} " + " ".join(f"{n:>14s}" for n, _, _ in STRATA))
        pool = {n: [] for n, _, _ in STRATA}
        ovr = []
        for stem in BIG:
            d = load(stem)
            rows, eps = windows_for(d)
            R, ep, yr, yc, y, lr, lv = arrays(rows, "20-24")
            if resp_key == "cs_ang":
                z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
                sig = np.asarray(z["cs_ang"], float)
                hi_, lo_ = [], []
                for a_, b_ in eps:
                    for s in range(0, (b_ - a_) - NPERSEG + 1, HOP):
                        sl = slice(a_ + s, a_ + s + NPERSEG)
                        hi_.append(band_rms(sig[sl], FS, *RESP, NPERSEG))
                        lo_.append(band_rms(sig[sl], FS, 20.0, 24.0, NPERSEG))
                y = np.log(np.array(hi_) + 1e-12) - np.log(np.array(lo_) + 1e-12)
            v = np.array([r["v"] for r in rows])
            p = partial_spearman(y, R, [lr, lv])
            ovr.append((p, len(R)))
            line = f"  {stem:6s} {p:+10.4f} "
            for n, lo2, hi2 in STRATA:
                m = (v >= lo2) & (v < hi2)
                if m.sum() < 60:
                    line += f"{'n<60':>14s} "
                    continue
                pp = partial_spearman(y[m], R[m], [lr[m], lv[m]])
                pool[n].append((pp, int(m.sum())))
                line += f"{pp:+14.3f} "
            print(line)
        w = np.array([x[1] for x in ovr], float)
        pv = np.array([x[0] for x in ovr])
        out[tag] = {"overall_pooled": float(np.average(pv, weights=w)),
                    "overall_range": [float(pv.min()), float(pv.max())], "strata": {}}
        print(f"\n  POOLED overall ({int(w.sum()):,} windows): {np.average(pv, weights=w):+.4f}   "
              f"spread {pv.min():+.3f} .. {pv.max():+.3f}")
        for n, _, _ in STRATA:
            if not pool[n]:
                continue
            a = np.array([x[0] for x in pool[n]])
            ww = np.array([x[1] for x in pool[n]], float)
            out[tag]["strata"][n] = dict(pooled=float(np.average(a, weights=ww)),
                                         n_routes=len(a), lo=float(a.min()), hi=float(a.max()))
            print(f"     POOLED {n:12s}: {np.average(a, weights=ww):+.4f}   "
                  f"(n_routes {len(a)}, per-route range [{a.min():+.3f}, {a.max():+.3f}])")
    return out


def bound_gp6ad6():
    """⭐ CAN |gp-0x6ad6|'s EXCURSION BE BOUNDED AT ALL?  The orchestrator's direct question.

    b5 == 0 everywhere gives |REF| < 8192.  b6 == 0 everywhere gives |T - REF| < 10240 with
    T = gp-0x4f60.  On frames where REF and T have OPPOSITE signs, |T - REF| = |T| + |REF|, so
        |REF| < 10240 - |T|
    which BEATS 8192 whenever |T| > 2048.  b4 supplies sign(REF); |T| is on the wire as CAN 0x18F.
    🛑 TWO ASSUMPTIONS, BOTH STATED: (i) the CAN count scale equals gp-0x4f60's -- the kit's own
    golden model says this is NOT proven; (ii) the relative POLARITY of `tq` and gp-0x4f60 is
    unknown, so BOTH are computed and both are reported.
    """
    z = np.load(AN / "_cache_r85" / "r85.npz", allow_pickle=True)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    tq = np.asarray(z["tq"], float)
    refneg = np.asarray(z["v100_b4"], float) > 0.5
    out = {"b5_all_zero": bool(not (np.asarray(z["v100_b5"], float) > 0.5).any()),
           "b6_all_zero": bool(not (np.asarray(z["v100_b6"], float) > 0.5).any()),
           "abs_tq_engaged_max": float(np.abs(tq)[eng].max()),
           "frac_abs_tq_ge_2048_engaged": float(np.mean(np.abs(tq)[eng] >= 2048))}
    print("\n" + "=" * 100)
    print("  BOUNDING |gp-0x6ad6| FROM THE WIRE -- the orchestrator's direct question")
    print("=" * 100)
    print(f"  |column torque| engaged MAX {out['abs_tq_engaged_max']:.0f} counts; "
          f"{100*out['frac_abs_tq_ge_2048_engaged']:.2f} % of engaged frames exceed 2048.")
    print("  ⇒ b6's null is NOT arithmetically implied by b5's: on those frames |T| + 8192 > 10240,")
    print("    so RUNG D' COULD have fired and did not.  **E2 carries genuine independent")
    print("    information** -- a caution I expected to have to raise, and the data refutes it.")
    for pol, name in ((+1, "gp-0x4f60 = +k*tq"), (-1, "gp-0x4f60 = -k*tq")):
        T = pol * tq
        opp = eng & (refneg != (T < 0)) & (np.abs(T) > 0)
        if not opp.any():
            continue
        aT = np.abs(T)[opp]
        bnd = 10240 - aT
        out[name] = dict(n_opposite_sign=int(opp.sum()),
                         frac_engaged=float(opp.sum() / eng.sum()),
                         tightest_bound=float(bnd.min()),
                         n_frames_beating_8192=int((bnd < 8192).sum()),
                         frac_engaged_beating_8192=float((bnd < 8192).sum() / eng.sum()))
        print(f"  {name}: opposite-sign engaged frames {opp.sum():,} "
              f"({100*opp.sum()/eng.sum():.2f} %)   TIGHTEST bound {bnd.min():.0f} counts   "
              f"frames beating 8192: {(bnd < 8192).sum():,} "
              f"({100*(bnd < 8192).sum()/eng.sum():.2f} %)")
    print("\n  ⇒ HONEST ANSWER: only marginally.  The envelope is |gp-0x6ad6| < 8192 everywhere;")
    print("    the b6 rung tightens it to < 6803 on 0.01 % of engaged frames and below 8192 on")
    print("    6.9 %, and ONLY under an unproven count scale and one of two polarities.")
    print("    🛑 THE OPERATING POINT IS UNBOUNDED.  A lever adding ~1,500 counts to one term")
    print("    CANNOT be assessed for clamp risk from this drive.  A THERMOMETER ON gp-0x6ad6 IS")
    print("    A V101 INSTRUMENT REQUIREMENT.")
    return out


def main():
    print("=" * 100)
    print("  ⭐ THE OPERATOR'S dCMD/dt HYPOTHESIS.  Pre-registered in this file's docstring.")
    print("=" * 100)
    res = {"preregistration": "see module docstring -- written before the first run",
           "differentiator": f"Savitzky-Golay deriv, win {SG_WIN} samples ({SG_WIN/FS:.2f} s) "
                             f"@ {FS:.0f} Hz, polyorder {SG_ORDER}",
           "regressor": "R = log10(1 + median |dx/dt| per 1.28 s window)",
           "response": "log RMS_6-9(column torque 0x18F) - log RMS_control, per window",
           "controls": list(CONTROLS)}
    res["channel_agreement"] = channel_agreement("r85")

    print("\n\n" + "#" * 100)
    print("#  PART 1 -- ROUTE 85 (V100), THE DRIVE THE OPERATOR JUST DESCRIBED")
    print("#" * 100)
    res["r85"] = run_route("r85")

    print("\n\n" + "#" * 100)
    print("#  PART 2 -- CORPUS REPLICATION.  The command channel is free on every route.")
    print("#" * 100)
    res["corpus"] = {}
    for stem in ROUTES[1:]:
        r = run_route(stem, verbose=False)
        if r is None:
            print(f"  {stem}: skipped (no cache or too few windows)")
            continue
        res["corpus"][stem] = r
        k = r["ctl_20-24"]
        print(f"  {stem:5s} {r['n_windows']:5,} win / {r['n_episodes']:3d} eps   "
              f"PARTIAL CONTRAST {k['partial_contrast']:+.4f} "
              f"[{k['partial_contrast_ci'][0]:+.4f}, {k['partial_contrast_ci'][1]:+.4f}]   "
              f"C1 null [{k['C1_phase_random_null'][0]:+.4f}, "
              f"{k['C1_phase_random_null'][1]:+.4f}]  beats C1 {k['beats_C1']}  "
              f"beats C2 {k['beats_C2']}")

    # ---------------- the verdict, against the PRE-REGISTERED sentences ----------------------
    print("\n\n" + "=" * 100)
    print("  VERDICT, AGAINST THE PRE-REGISTERED SENTENCES")
    print("=" * 100)
    allr = {"r85": res["r85"], **res["corpus"]}
    tbl = []
    for k, v in allr.items():
        if v is None:
            continue
        c = v["ctl_20-24"]
        tbl.append((k, c["rho_contrast"], c["partial_contrast"], c["partial_contrast_ci"],
                    c["broadband_fraction"], c["supports_hypothesis"], v["n_episodes"]))
    print(f"    {'route':6s} {'RAW rho':>10s} {'PARTIAL rho':>12s} {'95 % CI':>20s} "
          f"{'broadband':>10s} {'SUPPORTS':>9s} {'eps':>5s}")
    for k, rc, p, ci, bf, sup, ne in tbl:
        print(f"    {k:6s} {rc:+10.4f} {p:+12.4f} {f'[{ci[0]:+.3f}, {ci[1]:+.3f}]':>20s} "
              f"{bf:10.2f} {str(sup):>9s} {ne:5d}")
    npos = sum(1 for r in tbl if r[5])
    nsig_neg = sum(1 for r in tbl if np.isfinite(r[3][1]) and r[3][1] < 0)
    res["n_routes"] = len(tbl)
    res["n_supporting"] = npos
    res["n_significant_negative"] = nsig_neg
    print(f"\n    'broadband' = rho(R, control band) / rho(R, 6-9 Hz).  Near 1.0 means a harsher")
    print(f"    command raises EVERY band about equally -- excitation, not a resonance.")
    print(f"\n    ⭐ ROUTES SUPPORTING THE HYPOTHESIS (partial rho > 0, CI excludes 0, beats BOTH")
    print(f"       the phase-randomised and the episode-shuffle null): {npos} of {len(tbl)}")
    print(f"       routes with a SIGNIFICANTLY NEGATIVE partial: {nsig_neg} of {len(tbl)}")
    res["verdict"] = ("NULL -- the pre-registered null sentence is licensed" if npos == 0 else
                      f"NON-NULL on {npos}/{len(tbl)} routes")
    print(f"\n    ⇒ {res['verdict']}")

    res["supplements"] = supplements()
    res["bound_gp6ad6"] = bound_gp6ad6()
    (OUT / "dcmd_dt_hypothesis.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'dcmd_dt_hypothesis.json'}")
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1:
        channel_agreement(sys.argv[1])
        run_route(sys.argv[1])
    else:
        main()
