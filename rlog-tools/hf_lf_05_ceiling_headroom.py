#!/usr/bin/env python3
r"""H3 -- CAN THE RATE-SCHEDULED GOVERNOR CEILING ACTUALLY COLLAPSE AT HIGHWAY SPEED?

THE MECHANISM, as priced from the firmware this session (tracer report, 2026-08-22)
  bound = (gp-0x4f64 * authority_Q15) >> 15 ; clamp(gp-0x6b94, +-bound)   `0x453e0`-`0x453fe`
  gp-0x4f64 = clamp(table_Y(motor electrical rate), 0, 4762)              `FUN_0007b022`, 1 kHz
      table X = 1050 / 1700 / 2500 / 3700 / 4100      Y = 5325 / 3584 / 2406 / 1587 / 512
      clamped at BOTH ends -- exactly Y[0] below X[0], exactly Y[4] above X[4]
  index   = clamp(gp-0x6ac0, 0, 10000)
  gp-0x6ac0 = |IIR_54.8Hz(electrical rate)| >> 10     -- RECTIFIER AFTER the filter, tau 2.93 ms
      => a PEAK FOLLOWER, not an averager: a sustained 20-26 Hz oscillation drives it up and down
         at twice the carrier frequency rather than lifting a slow mean.
  conversion (tracer, marked EVIDENCE there): column_deg_per_s = gp-0x6ac0 / 4.71211
      => the ceiling starts to fall at 223 deg/s of COLUMN rate and bottoms out at 870 deg/s.

WHAT THIS FILE MEASURES -- the two headrooms that decide whether any of it can bite
  R1  RATE headroom.  The instantaneous |column rate| the ECU sees is not the median of `rate_c`;
      it is a peak follower of (low-frequency steering + the HF oscillation).  Reconstructed here
      as |LF(rate_c)| + envelope_HF(rate_c) and compared to the 223 deg/s knee.
  R2  DEMAND headroom.  On routes 85/95 -- and ONLY those two -- CAN 427 carries the real
      aggregator sum `gp-0x6b94` (`analysis-2020accord/check_427_alias.py`; on 96/97/9e the same
      key is a MISLABELLED ALIAS of the LANE).  How close does the demand get to +-4762 (ceiling
      at the top of the table) and to +-512 (ceiling at the bottom)?
  R3  A clipping SHAPE test on `tq` -- excess kurtosis and flat-top duty by rate bin.  Clipping
      flattens a distribution; a resonance does not.
  R4  STEER_STATUS / fault-channel transitions at highway speed -- a dropout that reaches the
      status word would be visible for free.

🛑 The clamp acts DOWNSTREAM of `gp-0x6b94`; 427 therefore carries the DEMAND, never the clamped
output.  So R2 can show the clamp MUST be biting, but it can never show that it is not.

OUTPUT `rlog-tools/_hf_lf_ceiling.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402
from hf_lf_03_envelope_coupling import analytic_env, episodes, reg, ROUTE_LABEL  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, KMH = L.FS, 3.6
ROUTES = ["9e", "97", "96", "85", "95"]
SUM_ROUTES = {"85", "95"}          # `check_427_alias.SUM_ROUTES` -- the whole allow-list
KNEE_DEGPS, FLOOR_DEGPS = 223.0, 870.0
BOUND_TOP, BOUND_BOT = 4762.0, 512.0
HF = (15.0, 35.0)


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108, flush=True)


def lowpass(x, fc=3.0):
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    X[f > fc] = 0.0
    return np.fft.irfft(X, n=len(x)) + x.mean()


def peak_rate(rate_c):
    """What the ECU's peak-following |rate| sees: |slow steering| + |the HF oscillation|.

    An UPPER bound on what a 100 Hz record can say about a 1 kHz peak follower -- the two terms
    are added at their worst-case alignment, which is the conservative direction for a headroom
    test.  ⚠ `rate_c` is the COLUMN rate; if the 20-26 Hz mode is motor-side behind the gear and
    torsion-bar compliance the motor's own rate can exceed this, and by an unmeasured factor.
    """
    x = np.asarray(rate_c, float)
    return np.abs(lowpass(x, 3.0)) + analytic_env(x, *HF)


def main():
    out = {}
    arms = [("ENGAGED hwy", True, 70.0, 200.0), ("manual hwy", False, 70.0, 200.0),
            ("ENGAGED mid", True, 40.0, 70.0), ("ENGAGED low", True, 0.0, 40.0)]
    for rt in ROUTES:
        if not reg(rt):
            continue
        out[rt] = {}
        for lab, eng, vlo, vhi in arms:
            eps = episodes(rt, engaged=eng, vlo=vlo, vhi=vhi, minlen=512)
            if not eps:
                continue
            rc = np.concatenate([e["rate_c"] for e in eps])
            pk = np.concatenate([peak_rate(e["rate_c"]) for e in eps])
            tq = np.concatenate([e["tq"] for e in eps])
            r = dict(label=lab, n_ep=len(eps), s=float(len(rc) / FS),
                     v_med=float(np.median([e["_v"] for e in eps])))
            r["rate"] = dict(
                p50=float(np.percentile(np.abs(rc), 50)), p99=float(np.percentile(np.abs(rc), 99)),
                max=float(np.max(np.abs(rc))),
                pk_p50=float(np.percentile(pk, 50)), pk_p99=float(np.percentile(pk, 99)),
                pk_max=float(np.max(pk)),
                frac_over_knee=float(np.mean(pk >= KNEE_DEGPS)),
                frac_over_floor=float(np.mean(pk >= FLOOR_DEGPS)),
                headroom_knee_over_p99=float(KNEE_DEGPS / max(np.percentile(pk, 99), 1e-9)))
            # R3 clipping shape of tq by rate bin
            shape = []
            for lo_, hi_ in ((0, 5), (5, 20), (20, 60), (60, 1e9)):
                m = (np.abs(rc) >= lo_) & (np.abs(rc) < hi_)
                if m.sum() < 500:
                    continue
                y = tq[m]
                y = y - y.mean()
                s = y.std()
                shape.append(dict(bin="%g-%g" % (lo_, hi_), n=int(m.sum()),
                                  kurt=float(np.mean((y / max(s, 1e-9)) ** 4) - 3.0),
                                  p999=float(np.percentile(np.abs(y), 99.9)),
                                  flat_duty=float(np.mean(np.abs(y) >=
                                                          0.98 * np.percentile(np.abs(y), 99.9)))))
            r["tq_shape"] = shape
            # R2 demand headroom -- only where 427 really carried the SUM
            if rt in SUM_ROUTES:
                sm = np.abs(np.concatenate([e["x6b94"] for e in eps]))
                r["demand"] = dict(p50=float(np.percentile(sm, 50)),
                                   p99=float(np.percentile(sm, 99)),
                                   p999=float(np.percentile(sm, 99.9)), max=float(sm.max()),
                                   frac_over_top=float(np.mean(sm >= BOUND_TOP)),
                                   frac_over_bottom=float(np.mean(sm >= BOUND_BOT)))
            else:
                r["demand"] = None
            # R4 status channel
            for k in ("sstat", "status", "dtc_active", "illegal"):
                if k in eps[0]:
                    v = np.concatenate([e[k] for e in eps])
                    r.setdefault("status", {})[k] = dict(
                        vals=sorted(set(np.round(v).astype(int).tolist()))[:8],
                        n_change=int(np.sum(np.diff(np.round(v)) != 0)))
            out[rt][lab] = r
            hdr("ROUTE %s (%s)  ARM %s  %d ep, %.1f s, v=%.1f km/h"
                % (rt, ROUTE_LABEL.get(rt, rt), lab, r["n_ep"], r["s"], r["v_med"]))
            q = r["rate"]
            print("  |rate_c| deg/s      p50 %7.2f  p99 %8.2f  max %8.2f"
                  % (q["p50"], q["p99"], q["max"]))
            print("  ECU peak-follower   p50 %7.2f  p99 %8.2f  max %8.2f   "
                  "| knee 223 deg/s is %.1fx the p99   frac>=knee %.5f  frac>=floor(870) %.5f"
                  % (q["pk_p50"], q["pk_p99"], q["pk_max"], q["headroom_knee_over_p99"],
                     q["frac_over_knee"], q["frac_over_floor"]))
            if r["demand"]:
                d = r["demand"]
                print("  DEMAND |gp-0x6b94|  p50 %7.1f  p99 %8.1f  p99.9 %8.1f  max %8.1f "
                      "| frac >= 4762 (top bound) %.5f   frac >= 512 (bottom bound) %.5f"
                      % (d["p50"], d["p99"], d["p999"], d["max"], d["frac_over_top"],
                         d["frac_over_bottom"]))
            else:
                print("  DEMAND: 427 carried the LANE on this route -- no sum available "
                      "(check_427_alias)")
            print("  tq shape by |rate_c|: %s"
                  % "  ".join("%s n=%d kurt=%+.2f flat=%.4f" % (s["bin"], s["n"], s["kurt"],
                                                                s["flat_duty"])
                              for s in r["tq_shape"]))
            if "status" in r:
                print("  status: %s" % "  ".join("%s vals=%s changes=%d"
                                                 % (k, v["vals"], v["n_change"])
                                                 for k, v in r["status"].items()))
    (HERE / "_hf_lf_ceiling.json").write_text(json.dumps(out, indent=1))
    print("\nwrote", HERE / "_hf_lf_ceiling.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
