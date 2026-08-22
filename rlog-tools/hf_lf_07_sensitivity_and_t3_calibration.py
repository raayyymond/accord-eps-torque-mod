#!/usr/bin/env python3
r"""THE CONTROL THAT `hf_lf_06` FAILED, FIXED -- AND WHAT AN ACTUAL AM RECORD LOOKS LIKE IN T3.

🛑 WHY THIS FILE EXISTS -- `hf_lf_06`'s T0 POSITIVE CONTROL DID NOT PASS
  `hf_lf_06` injected a known 8 Hz amplitude modulation onto the measured carrier and its own
  envelope-line statistic FAILED TO RECOVER IT at depth 0.15 AND at depth 0.35.  Under
  `feedback-run-the-control-before-the-measurement` that makes every T1 null in `hf_lf_06`
  UNINTERPRETABLE -- a statistic that cannot see a 35 % modulation cannot be quoted as evidence
  that there is no modulation.  Two causes, both diagnosed here rather than assumed:

  C1  🛑 THE NULL ABSORBED THE SIGNAL.  `phase_rand_band` randomises the phases of the whole
      carrier-centred band.  An AM'd carrier's sidebands live INSIDE that band, so randomising
      phase leaves three components still spaced exactly f_m apart -- and three tones spaced f_m
      apart beat at f_m regardless of their phases.  The surrogate therefore reproduces the very
      envelope line it is supposed to destroy.  `hf_lf_06`'s own numbers show it: at depth 0.35 the
      observed prominence is 4.84 and the NULL's own p95 is 5.13, five times the null p95 of the
      unmodulated case (2.13).  The null moved with the signal.
      ⇒ FIX: an EMPIRICAL FALSE-ALARM null -- the same max-local-prominence statistic evaluated
      over equal-width windows of the SAME envelope spectrum where no ratchet can live.  It cannot
      absorb the signal because it never touches the data.
  C2  DILUTION.  The synthetic was added at the amplitude of the REAL carrier, so a nominal depth
      m applied to only half the band energy is an effective depth of ~m/2.  Reported here as an
      EFFECTIVE depth so the sensitivity number means something.

WHAT THIS FILE DELIVERS
  S1  DETECTION FLOOR of the sideband statistic -- a depth ladder m = 0.05 ... 1.00, injected both
      CLEAN (onto a phase-randomised record, no competing real carrier) and REALISTIC (onto the
      real record).  Converts "no sidebands" into "amplitude modulation deeper than X is EXCLUDED".
  S2  DETECTION FLOOR of the fixed envelope-line statistic, same ladder.
  S3  🛑 T3 CALIBRATED AGAINST BOTH HYPOTHESES.  `hf_lf_06`'s discriminator is run on two synthetic
      records built from the REAL data:
        ONE-MECHANISM  the 6-12 Hz content is REPLACED by a demodulation of the carrier -- the
              carrier's own analytic envelope, high-passed into 6-12 Hz and scaled to the real
              6-12 Hz RMS.  This is what the operator's hypothesis looks like if it is true, with
              a rectifying nonlinearity supplying the demodulation.
        TWO-MECHANISM the 6-12 Hz content is replaced by an INDEPENDENT narrowband process of the
              same RMS, uncorrelated with the carrier.
      Whatever separates these two is the discriminator; whatever does not is discarded.  The real
      data is then read against the two calibrated values instead of against a guess.
  S4  SPECTRAL PEAK CENSUS 4-45 Hz.  A pair of lines separated by ~8 Hz would produce a genuine
      8 Hz envelope by BEATING -- a different mechanism from AM with the same felt result.  Listed
      so it is checked rather than assumed absent.

🛑 An arithmetic fact that no statistic can overturn, stated here because it bounds everything:
  for x = A(1 + m cos w_m t) cos w_c t the total SIDEBAND power is (m^2/2) x the carrier power and
  the power AT f_m is EXACTLY ZERO in any linear channel.  Measured 6-12 Hz RMS that EXCEEDS the
  21-28 Hz carrier RMS therefore cannot be a linear by-product of the carrier at any depth.

OUTPUT `rlog-tools/_hf_lf_sensitivity.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402
from hf_lf_06_envelope_discriminator import (CARRIER, CTRL1, ENVWIN, FREQ, FS, NSEG,  # noqa: E402
                                             RATCHET, ROUTE_LABEL, WIDE_HALF, analytic_env,
                                             band_rms, discriminator, episodes, hdr, parts,
                                             phase_rand_full, reg, sideband_score, welch_P)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEPTHS = (0.05, 0.10, 0.20, 0.35, 0.50, 0.75, 1.00)
FM = 8.0
ARMS = [("a5", "ENGAGED hwy", 70.0, 200.0), ("a5", "ENGAGED mid", 40.0, 70.0),
        ("a4", "ENGAGED hwy", 70.0, 200.0), ("9e", "ENGAGED hwy", 70.0, 200.0),
        ("96", "ENGAGED hwy", 70.0, 200.0), ("97", "ENGAGED mid", 40.0, 70.0)]
RNG0 = 987654


# ------------------------------------------------------- the FIXED envelope-line statistic ------
def _max_prom(P, lo, hi, half=1.5, gap=0.4):
    m = (FREQ >= lo) & (FREQ <= hi)
    best = (-1.0, np.nan)
    for i in np.flatnonzero(m):
        f0 = FREQ[i]
        bg = (np.abs(FREQ - f0) <= half) & (np.abs(FREQ - f0) > gap)
        if bg.sum() < 4:
            continue
        pr = P[i] / max(float(np.median(P[bg])), 1e-30)
        if pr > best[0]:
            best = (float(pr), float(f0))
    return best


def env_line_fixed(series, lo, hi, win=ENVWIN, fa_lo=16.0, fa_hi=45.0):
    """Max local prominence in `win`, against an EMPIRICAL FALSE-ALARM null: the same statistic on
    equal-width windows of the SAME envelope spectrum, over [fa_lo, fa_hi] where no ratchet lives.
    The null never touches the data, so -- unlike phase randomisation inside the carrier band -- it
    CANNOT absorb an amplitude modulation."""
    ne = [(e - e.mean()) / max(e.mean(), 1e-9) for e in (analytic_env(x, lo, hi) for x in series)]
    X = parts(ne)
    if not len(X):
        return None
    P = welch_P(X)
    prom, f = _max_prom(P, *win)
    w = win[1] - win[0]
    fa = []
    a = fa_lo
    while a + w <= fa_hi:
        fa.append(_max_prom(P, a, a + w)[0])
        a += w / 2.0
    fa = np.asarray([v for v in fa if v > 0])
    if not len(fa):
        return dict(prom=prom, f=f, fa_p95=np.nan, fa_med=np.nan, hit=False, n_fa=0)
    p95 = float(np.percentile(fa, 95))
    return dict(prom=prom, f=f, fa_p95=p95, fa_med=float(np.median(fa)),
                hit=bool(prom > p95), n_fa=int(len(fa)))


# ------------------------------------------------------- synthetic constructors -----------------
def make_am(car, fc, m, rng, clean):
    """Carrier at fc, amplitude-modulated at FM, added to the record (or to a phase-randomised
    version of it when `clean`, so nothing competes with it in the carrier band)."""
    amp = float(np.median([band_rms(x, *CARRIER) for x in car])) or 1.0
    out = []
    for x in car:
        base = phase_rand_full(np.asarray(x, float), rng) if clean else np.asarray(x, float)
        t = np.arange(len(x)) / FS
        s = amp * np.sqrt(2) * (1.0 + m * np.cos(2 * np.pi * FM * t)) \
            * np.cos(2 * np.pi * fc * t + rng.uniform(0, 2 * np.pi))
        out.append(base + s)
    return out, amp


def eff_depth(syn, fc, m):
    """Effective depth after dilution by whatever else is already in the carrier band."""
    inj = float(np.median([band_rms(x, *CARRIER) for x in syn]))
    return m  # nominal; the realistic-vs-clean pair below IS the dilution measurement


def bandlimit(x, lo, hi):
    X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    return np.fft.irfft(np.where((f >= lo) & (f < hi), X, 0.0), n=len(x))


def replace_band(x, lo, hi, new):
    """Strip [lo,hi) from x and substitute `new`, rescaled to the ORIGINAL band RMS."""
    x = np.asarray(x, float)
    keep = x - bandlimit(x, lo, hi)
    tgt = band_rms(x, lo, hi)
    nb = bandlimit(new, lo, hi)
    s = np.sqrt(np.mean(nb ** 2))
    return keep + (nb * (tgt / s) if s > 1e-12 else nb)


def synth_one_mechanism(eps, rng):
    """6-12 Hz REPLACED by a demodulation of the 21-28 Hz carrier -- what the operator's hypothesis
    looks like if it is TRUE (a rectifying nonlinearity turns the envelope into real 6-12 Hz)."""
    out = []
    for e in eps:
        x = np.asarray(e["tq"], float)
        env = analytic_env(x, *CARRIER)
        f = dict(e)
        f["tq"] = replace_band(x, *RATCHET, new=env - env.mean())
        out.append(f)
    return out


def synth_two_mechanism(eps, rng):
    """6-12 Hz REPLACED by an INDEPENDENT narrowband process of the same RMS."""
    out = []
    for e in eps:
        x = np.asarray(e["tq"], float)
        f = dict(e)
        f["tq"] = replace_band(x, *RATCHET, new=bandlimit(rng.standard_normal(len(x)), *RATCHET))
        out.append(f)
    return out


def peak_census(car, lo=4.0, hi=45.0, n=8):
    P = welch_P(parts(car))
    m = (FREQ >= lo) & (FREQ <= hi)
    idx = np.flatnonzero(m)
    pk = [i for i in idx[1:-1] if P[i] > P[i - 1] and P[i] > P[i + 1]]
    pk.sort(key=lambda i: -P[i])
    out = []
    for i in pk[:n]:
        f0 = FREQ[i]
        bg = (np.abs(FREQ - f0) <= 2.0) & (np.abs(FREQ - f0) > 0.5)
        out.append(dict(f=float(f0), prom=float(P[i] / max(float(np.median(P[bg])), 1e-30))))
    return out


# ------------------------------------------------------------------ main ------------------------
def main():
    out = {"depths": list(DEPTHS), "fm": FM, "arms": {}}
    for rt, lab, vlo, vhi in ARMS:
        if not reg(rt):
            continue
        eps = episodes(rt, engaged=True, vlo=vlo, vhi=vhi, minlen=NSEG)
        if len(eps) < 1:
            continue
        rng = np.random.default_rng(RNG0 + (abs(hash((rt, lab))) % 9973))
        car = [e["tq"] for e in eps]
        P = welch_P(parts(car))
        mhf = (FREQ >= 15.0) & (FREQ <= 35.0)
        fc = float(FREQ[mhf][np.argmax(P[mhf])])
        key = "%s %s" % (rt, lab)
        hdr("%s (%s)  %d ep, %.1f s, v=%.1f km/h   fc=%.2f Hz   injected f_m=%.1f Hz"
            % (key, ROUTE_LABEL.get(rt, rt), len(eps),
               sum(len(e["t"]) for e in eps) / FS, np.median([e["_v"] for e in eps]), fc, FM))
        rec = dict(fc=fc, n_ep=len(eps),
                   rms_car=float(np.median([band_rms(x, *CARRIER) for x in car])),
                   rms_rat=float(np.median([band_rms(x, *RATCHET) for x in car])),
                   rms_ctrl=float(np.median([band_rms(x, *CTRL1) for x in car])))
        print("  band RMS  carrier(21-28) %.4g   ratchet(6-12) %.4g   ratio rat/car %.2f   "
              "ctrl(32-38) %.4g" % (rec["rms_car"], rec["rms_rat"],
                                    rec["rms_rat"] / max(rec["rms_car"], 1e-9), rec["rms_ctrl"]))

        # ---- S4 peak census -------------------------------------------------------------
        rec["peaks"] = peak_census(car)
        print("  S4 top spectral peaks 4-45 Hz: "
              + "  ".join("%.2f(%.1f)" % (p["f"], p["prom"]) for p in rec["peaks"]))
        fs_ = [p["f"] for p in rec["peaks"]]
        near8 = sorted({round(abs(a - b), 2) for a in fs_ for b in fs_
                        if 6.0 <= abs(a - b) <= 12.0})
        print("     peak SEPARATIONS falling in 6-12 Hz (a beat would make a real envelope): %s"
              % (near8 if near8 else "NONE"))
        rec["peak_seps_6_12"] = near8

        # ---- S1/S2 sensitivity ladder ---------------------------------------------------
        lo_w, hi_w = max(fc - WIDE_HALF, 0.5), fc + WIDE_HALF
        base_env = env_line_fixed(car, lo_w, hi_w)
        base_sb = sideband_score(P, fc, FM)[0]
        print("  BASELINE (no injection): envelope line %.2f @ %.2f Hz vs false-alarm p95 %.2f %s"
              "   |   sideband %.2f"
              % (base_env["prom"], base_env["f"], base_env["fa_p95"],
                 "HIT" if base_env["hit"] else "no", base_sb))
        rec["baseline"] = dict(env=base_env, sideband=base_sb)
        print("  %-6s | %-38s | %-38s" % ("depth", "CLEAN  (injected onto phase-rand record)",
                                          "REALISTIC (injected onto real record)"))
        print("  %-6s | %-16s %-20s | %-16s %-20s"
              % ("m", "env line", "sideband", "env line", "sideband"))
        rec["ladder"] = []
        for m in DEPTHS:
            row = dict(m=m)
            for tag, clean in (("clean", True), ("real", False)):
                syn, amp = make_am(car, fc, m, np.random.default_rng(RNG0 + int(m * 1000)), clean)
                r = env_line_fixed(syn, lo_w, hi_w)
                Ps = welch_P(parts(syn))
                sb = sideband_score(Ps, fc, FM)[0]
                sbn = [sideband_score(welch_P(parts([phase_rand_full(x, rng) for x in syn])),
                                      fc, FM)[0] for _ in range(20)]
                row[tag] = dict(prom=r["prom"], f=r["f"], fa_p95=r["fa_p95"], hit=r["hit"],
                                sb=sb, sb_null_p95=float(np.percentile(sbn, 95)),
                                sb_hit=bool(sb > float(np.percentile(sbn, 95))))
            rec["ladder"].append(row)
            print("  %-6.2f | %5.2f@%5.2f %-4s  %5.2f vs %5.2f %-4s | "
                  "%5.2f@%5.2f %-4s  %5.2f vs %5.2f %-4s"
                  % (m,
                     row["clean"]["prom"], row["clean"]["f"],
                     "HIT" if row["clean"]["hit"] else "miss",
                     row["clean"]["sb"], row["clean"]["sb_null_p95"],
                     "HIT" if row["clean"]["sb_hit"] else "miss",
                     row["real"]["prom"], row["real"]["f"],
                     "HIT" if row["real"]["hit"] else "miss",
                     row["real"]["sb"], row["real"]["sb_null_p95"],
                     "HIT" if row["real"]["sb_hit"] else "miss"))
        floor = {}
        for tag in ("clean", "real"):
            for stat, k in (("env", "hit"), ("sb", "sb_hit")):
                hits = [r["m"] for r in rec["ladder"] if r[tag][k]]
                floor["%s_%s" % (tag, stat)] = float(min(hits)) if hits else None
        rec["detection_floor"] = floor
        print("  ⇒ DETECTION FLOOR (smallest m detected): clean env %s · clean sideband %s · "
              "real env %s · real sideband %s"
              % (floor["clean_env"], floor["clean_sb"], floor["real_env"], floor["real_sb"]))

        # ---- S3 T3 calibrated against BOTH hypotheses ------------------------------------
        real_t3 = discriminator(eps, np.random.default_rng(RNG0 + 1))
        one_t3 = discriminator(synth_one_mechanism(eps, rng), np.random.default_rng(RNG0 + 2))
        two_t3 = discriminator(synth_two_mechanism(eps, rng), np.random.default_rng(RNG0 + 3))
        rec["T3"] = dict(real=real_t3, one_mechanism=one_t3, two_mechanism=two_t3)
        print("  S3 T3 CALIBRATION -- the same discriminator on synthetic records built from THIS "
              "arm's own data")
        print("     %-16s %-12s %-12s %-12s %-22s" % ("record", "CARRIER r", "RATCHET r",
                                                      "CTRL r", "DELTA (b_car - b_ctrl)"))
        for nm, t3 in (("ONE-mechanism", one_t3), ("TWO-mechanism", two_t3), ("REAL DATA", real_t3)):
            if not t3:
                continue
            p_, s_ = t3["plain"], t3["slopes"]
            ci = s_.get("delta_ci")
            print("     %-16s %-12.4f %-12.4f %-12.4f %+.3f%s"
                  % (nm, p_["car_ratio"], p_["rat_ratio"], p_["c1_ratio"], s_["delta"],
                     "" if not ci else " [%+.3f,%+.3f]" % tuple(ci)))
        out["arms"][key] = rec

    (HERE / "_hf_lf_sensitivity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote", HERE / "_hf_lf_sensitivity.json")


if __name__ == "__main__":
    main()
