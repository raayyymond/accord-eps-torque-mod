#!/usr/bin/env python3
r"""studies/v103-r9e/v103_r9e_census.py -- ROUTE 9e (V103): FAULT + IDENTITY + EXPOSURE census, per segment.

PART 1  fault sentinels, CONFIG_VALID, OUTPUT_DISABLED, DTC bit2, STEER_STATUS, onroadEvents
PART 2  identity -- V103's ONLY witness is a VARYING b3 (builds/v80_v107/build_v103_tva.py's own rule)
PART 3  exposure -- engaged s, episodes, speed, hands, wheel rate, the f0-band seconds, per segment
PART 4  the LKAS command distribution: |0x0E4| median/p90/max, rail duty, QUANTISATION
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = {}
DT = 0.01
RAIL = 4096.0                     # openpilot's own +-4096 command rail on 0x0E4


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    n = len(t)
    seg = np.asarray(z["seg"], int)
    fs = 1.0 / float(np.median(np.diff(t)))

    # ---------------------------------------------------------------- PART 1  FAULTS
    hdr("PART 1 -- FAULT CENSUS.  Any non-zero here voids everything downstream.")
    sent = np.asarray(z["sentinels"], int)
    cv = np.asarray(z["ab_config_valid"], int)
    od = np.asarray(z["ab_output_disabled"], int)
    d2 = np.asarray(z["ab_dtc_bit2"], int)
    ss = np.asarray(z["sstat"], int)
    su, sc = np.unique(ss, return_counts=True)
    ctr = np.asarray(z["ab_counter"], int)
    step = np.diff(ctr) % 4
    F = dict(
        sentinel_0x14A=int(sent[0]), sentinel_0x18F=int(sent[1]),
        n_1ab=int(len(cv)),
        config_valid_duty=float(cv.mean()), config_valid_n_zero=int((cv == 0).sum()),
        output_disabled_duty=float(od.mean()), output_disabled_n_one=int((od == 1).sum()),
        dtc_bit2_duty=float(d2.mean()), dtc_bit2_transitions=int((np.diff(d2) != 0).sum()),
        steer_status_hist={int(v): int(c) for v, c in zip(su, sc)},
        counter_step1_frac=float(np.mean(step == 1)),
        checksum_distinct=int(len(np.unique(np.asarray(z["ab_checksum"], int)))),
    )
    print("  0x7FFF sentinels: 0x14A %d   0x18F %d          (both MUST be 0)"
          % (F["sentinel_0x14A"], F["sentinel_0x18F"]))
    print("  0x1AB frames %d   CONFIG_VALID duty %.6f (%d zero frames)"
          % (F["n_1ab"], F["config_valid_duty"], F["config_valid_n_zero"]))
    print("  OUTPUT_DISABLED duty %.6f (%d frames set)   DTC bit2 duty %.6f (%d transitions)"
          % (F["output_disabled_duty"], F["output_disabled_n_one"],
             F["dtc_bit2_duty"], F["dtc_bit2_transitions"]))
    print("  0x1AB COUNTER +1 %.2f %%   CHECKSUM distinct %d/16"
          % (100 * F["counter_step1_frac"], F["checksum_distinct"]))
    print("  STEER_STATUS histogram (0x18F byte4 7:4): " +
          "  ".join("%d:%d (%.4f%%)" % (int(v), int(c), 100.0 * c / n) for v, c in zip(su, sc)))
    print("     0 = normal   3 = low-speed lockout (cal 0xC62EA ~5 km/h)   4 = state-4 governor")
    # OUTPUT_DISABLED / STEER_STATUS!=0 in time
    if F["output_disabled_n_one"]:
        abt = np.asarray(z["ab_t1ab"], float)
        w = np.where(od == 1)[0]
        runs = np.split(w, np.where(np.diff(w) != 1)[0] + 1)
        print("     OUTPUT_DISABLED runs: " + "  ".join(
            "t=%.1f-%.1f s (%d fr)" % (abt[r[0]], abt[r[-1]], len(r)) for r in runs[:12]))
        F["output_disabled_runs"] = [[float(abt[r[0]]), float(abt[r[-1]]), int(len(r))]
                                     for r in runs]
    if (ss != 0).any():
        w = np.where(ss != 0)[0]
        runs = np.split(w, np.where(np.diff(w) != 1)[0] + 1)
        print("     STEER_STATUS!=0 runs: " + "  ".join(
            "t=%.1f-%.1f s seg%d val=%d (%d fr)"
            % (t[r[0]], t[r[-1]], seg[r[0]], ss[r[0]], len(r)) for r in runs[:12]))
        F["steer_status_nonzero_runs"] = [[float(t[r[0]]), float(t[r[-1]]), int(seg[r[0]]),
                                           int(ss[r[0]]), int(len(r))] for r in runs]
    ev = json.loads((V.L.ROUTES["9e"]["cache"] / "r9e_events.json").read_text())
    from collections import Counter
    evc = Counter(e["name"] for e in ev)
    F["onroad_events"] = dict(evc)
    bad = {k: v for k, v in evc.items()
           if any(s in k.lower() for s in ("fault", "lka", "steer", "epsfault", "loststeer"))}
    print("  onroadEvents steering-related: %s" % (bad or "NONE"))
    F["verdict"] = ("CLEAN" if (F["sentinel_0x14A"] == 0 and F["sentinel_0x18F"] == 0
                                and F["config_valid_duty"] == 1.0
                                and F["dtc_bit2_duty"] == 0.0) else "FLAGGED")
    print("  ==> FAULT VERDICT: %s" % F["verdict"])
    OUT["faults"] = F

    # ---------------------------------------------------------------- PART 2  IDENTITY
    hdr("PART 2 -- IDENTITY.  V103's ONLY witness is a VARYING b3 (D_state sign).\n"
        "         byte7[7:6]==3 is shared with V101/V102; b3 constant-1 is V101, constant-0 is V102.\n"
        "         A b3 that takes BOTH values is structurally impossible on any predecessor.")
    ident = json.loads((V.L.ROUTES["9e"]["cache"] / "r9e_identity.json").read_text())
    print("  byte7[7:6] histogram %s   code-3 duty %.6f"
          % (ident["byte7_code_hist"], ident["byte7_code3_duty"]))
    print("  b3 duty %.6f   zeros %d   ones %d   VARIES = %s"
          % (ident["b3_duty"], ident["b3_n_zero"], ident["b3_n_one"], ident["b3_varies"]))
    print("  bit duties %s" % {k: round(v, 4) for k, v in ident["bit_duties"].items()})
    # b3 run-length: a real sign bit toggles on a physical timescale, a stuck/aliased one does not
    b3 = np.asarray(z["v103_b3"], float) > 0.5
    ch = np.where(np.diff(b3.astype(int)) != 0)[0]
    rl = np.diff(np.concatenate(([0], ch + 1, [len(b3)])))
    print("  b3 transitions %d over %.1f s => %.2f Hz mean toggle rate; run lengths "
          "p50 %.0f p90 %.0f max %d frames (10 ms each)"
          % (len(ch), t[-1], len(ch) / t[-1], np.percentile(rl, 50), np.percentile(rl, 90), rl.max()))
    ident["b3_transitions"] = int(len(ch))
    ident["b3_toggle_hz"] = float(len(ch) / t[-1])
    ident["b3_runlen_p50"] = float(np.percentile(rl, 50))
    ident["b3_runlen_max"] = int(rl.max())
    print("  ==> IDENTITY VERDICT: %s" % ("PASS -- THIS IS V103" if ident["identity_pass"]
                                          else "FAIL -- STOP"))
    OUT["identity"] = ident

    # ---------------------------------------------------------------- PART 3  EXPOSURE
    hdr("PART 3 -- EXPOSURE CENSUS.  Engagement from `latActive` (cruiseState is WRONG).")
    eng, press = M["eng"], M["press"]
    v = M["v"]                       # m/s, cs_v -- the estimator's own reference
    vr = M["v_rear"] * 3.6           # 🛑 `ws_*` are m/s (KMH = 1/3.6 in the extractor);
    #                                  multiply to km/h.  The extractor's own print label is WRONG.
    rate = M["rate"]                 # deg/s, 0x18F filtered wheel rate
    ang = np.abs(np.asarray(z["ang"], float))

    # cross-check the three engagement signals the kit trusts
    e4 = np.asarray(z["e4req"], float) > 0.5
    sca = np.asarray(z["sca"], float) > 0.5
    agree = dict(lat_vs_0x18F_b4b3=float(np.mean(eng == sca)),
                 lat_vs_0x0E4_b2b7=float(np.mean(eng == e4)),
                 sca_vs_e4=float(np.mean(sca == e4)))
    print("  engagement signal agreement: latActive vs 0x18F b4bit3 %.4f   vs 0x0E4 byte2 bit7 %.4f"
          % (agree["lat_vs_0x18F_b4b3"], agree["lat_vs_0x0E4_b2b7"]))

    hands_on_eng = float(press[eng].mean())
    E = dict(frames=int(n), seconds=float(n * DT), fs=float(fs),
             engaged_s=float(eng.sum() * DT), engaged_frac=float(eng.mean()),
             manual_s=float((~eng).sum() * DT),
             hands_on_frac_engaged=hands_on_eng,
             hands_on_s_engaged=float((eng & press).sum() * DT),
             engagement_agreement=agree)
    print("  %d frames  %.1f s (%.2f min)  grid %.2f Hz"
          % (n, n * DT, n * DT / 60, fs))
    print("  ENGAGED %.1f s (%.2f %%)   MANUAL %.1f s   HANDS-ON while engaged %.1f s (%.2f %%)"
          % (E["engaged_s"], 100 * E["engaged_frac"], E["manual_s"],
             E["hands_on_s_engaged"], 100 * hands_on_eng))

    # episodes
    eps = V.episodes(eng, t, min_len=1)
    eps_s = [(t[b - 1] - t[a]) for a, b in eps]
    E["n_episodes"] = len(eps)
    E["episode_seconds"] = [float(x) for x in eps_s]
    E["episodes_ge_5s"] = int(sum(1 for x in eps_s if x >= 5))
    E["episodes_ge_15s"] = int(sum(1 for x in eps_s if x >= 15))
    print("  engagement EPISODES: %d total  (>=5 s: %d, >=15 s: %d)  longest %.1f s   "
          "seconds: %s" % (len(eps), E["episodes_ge_5s"], E["episodes_ge_15s"], max(eps_s),
                           " ".join("%.0f" % x for x in sorted(eps_s, reverse=True)[:14])))

    def q(a, m):
        a = a[m]
        return dict(n=int(m.sum()), s=float(m.sum() * DT),
                    p10=float(np.percentile(a, 10)) if m.sum() else np.nan,
                    p50=float(np.percentile(a, 50)) if m.sum() else np.nan,
                    p90=float(np.percentile(a, 90)) if m.sum() else np.nan,
                    max=float(a.max()) if m.sum() else np.nan)

    E["speed_engaged_kmh_vrear"] = q(vr, eng)
    E["speed_engaged_kmh_cs_v"] = q(v * 3.6, eng)
    E["speed_all_kmh_vrear"] = q(vr, np.ones(n, bool))
    s = E["speed_engaged_kmh_vrear"]
    print("  ENGAGED speed (v_rear, km/h):  p10 %.1f  p50 %.1f  p90 %.1f  max %.1f"
          % (s["p10"], s["p50"], s["p90"], s["max"]))
    s2 = E["speed_engaged_kmh_cs_v"]
    print("  ENGAGED speed (cs_v  , km/h):  p10 %.1f  p50 %.1f  p90 %.1f  max %.1f   "
          "(the estimator's own reference)" % (s2["p10"], s2["p50"], s2["p90"], s2["max"]))

    E["rate_engaged_degs"] = q(rate, eng)
    r = E["rate_engaged_degs"]
    print("  ENGAGED |wheel rate| (deg/s): p10 %.2f  p50 %.2f  p90 %.2f  max %.1f"
          % (r["p10"], r["p50"], r["p90"], r["max"]))
    for lo, hi, nm in ((0, 1, "still <1"), (1, 13, "MICRO 1-13"), (13, 50, "RATCHET 13-50"),
                       (50, 1e9, "MACRO >50")):
        m = eng & (rate >= lo) & (rate < hi)
        E["rate_regime_" + nm.split()[0]] = float(m.sum() * DT)
        print("      %-16s %7.1f s engaged" % (nm, m.sum() * DT))

    # --- the f0 endpoint's own conditioning window
    band = eng & (~press) & (v > 0.5) & (v >= V.VLO) & (v < V.VHI)
    E["f0_band_s"] = float(band.sum() * DT)
    E["f0_band_handson_s"] = float((eng & press & (v >= V.VLO) & (v < V.VHI)).sum() * DT)
    print("  ⭐ f0 CONDITIONING (engaged, HANDS-OFF, 29-86 km/h by cs_v): %.1f s   "
          "[REQUIRE >=80 s, TARGET ~100 s]" % E["f0_band_s"])
    print("     same window but HANDS-ON (excluded): %.1f s" % E["f0_band_handson_s"])
    bp = V.episodes(band, t, min_len=V.NW_Z)
    E["f0_band_episodes"] = len(bp)
    E["f0_band_episode_s"] = [float(t[b - 1] - t[a]) for a, b in bp]
    print("     usable episodes (>=5.12 s contiguous): %d   seconds %s"
          % (len(bp), " ".join("%.0f" % x for x in E["f0_band_episode_s"])))

    # --- straight-line gripping (the ③ grip test)
    grip = eng & press & (np.abs(np.asarray(z["rate_f"], float)) < 3.0) & (ang < 15.0) & (v > 5.0)
    gr = V.episodes(grip, t, min_len=1)
    grs = [(t[b - 1] - t[a]) for a, b in gr]
    E["straight_grip_s"] = float(grip.sum() * DT)
    E["straight_grip_runs"] = len(gr)
    E["straight_grip_longest"] = float(max(grs)) if grs else 0.0
    E["straight_grip_ge_5s"] = int(sum(1 for x in grs if x >= 5))
    print("  ③ STRAIGHT-LINE GRIPPING (engaged, pressed, |rate|<3 deg/s, |ang|<15 deg, v>18 km/h):")
    print("     %.1f s in %d runs   longest %.1f s   runs >=5 s: %d   "
          "[V102 had 0 s, stock 24 s]" % (E["straight_grip_s"], len(gr),
                                          E["straight_grip_longest"], E["straight_grip_ge_5s"]))
    E["grip_rate_corr"] = float(np.corrcoef(press[eng].astype(float), rate[eng])[0, 1])
    print("     corr(pressed, |wheel rate|) engaged = %+.3f   [record: +0.59..+0.78 on every build]"
          % E["grip_rate_corr"])

    # --- high-steer-angle-rate engaged (the operator's ratcheting condition)
    for thr in (13.0, 25.0, 50.0, 100.0):
        m = eng & (rate >= thr)
        E["engaged_rate_ge_%d_s" % int(thr)] = float(m.sum() * DT)
    print("  HIGH STEER RATE engaged: >=13 %.1f s   >=25 %.1f s   >=50 %.1f s   >=100 %.1f s"
          % tuple(E["engaged_rate_ge_%d_s" % int(x)] for x in (13, 25, 50, 100)))

    # ---- PER SEGMENT
    print("\n  PER-SEGMENT BREAKDOWN  (v = v_rear km/h; f0-s = engaged hands-off 29-86 km/h)")
    print("   %3s %8s %7s %7s %7s %7s %7s %7s %7s %7s %7s"
          % ("seg", "frames", "sec", "eng_s", "hands%", "f0_s", "v_p50", "v_p90",
             "rate50", "r>=13s", "grip_s"))
    rows = []
    for s_ in sorted(np.unique(seg)):
        m = seg == s_
        me = m & eng
        row = dict(seg=int(s_), frames=int(m.sum()), sec=float(m.sum() * DT),
                   eng_s=float(me.sum() * DT),
                   hands_on_pct=float(100 * press[me].mean()) if me.sum() else np.nan,
                   f0_s=float((m & band).sum() * DT),
                   v_p50=float(np.percentile(vr[m], 50)),
                   v_p90=float(np.percentile(vr[m], 90)),
                   rate_p50=float(np.percentile(rate[me], 50)) if me.sum() else np.nan,
                   rate_ge13_s=float((me & (rate >= 13)).sum() * DT),
                   grip_s=float((m & grip).sum() * DT))
        rows.append(row)
        print("   %3d %8d %7.1f %7.1f %7.1f %7.1f %7.1f %7.1f %7.2f %7.1f %7.1f"
              % (row["seg"], row["frames"], row["sec"], row["eng_s"], row["hands_on_pct"],
                 row["f0_s"], row["v_p50"], row["v_p90"], row["rate_p50"],
                 row["rate_ge13_s"], row["grip_s"]))
    E["per_segment"] = rows
    OUT["exposure"] = E

    # ---------------------------------------------------------------- PART 4  COMMAND
    hdr("PART 4 -- THE LKAS COMMAND `0x0E4`.  Distribution, RAIL DUTY and QUANTISATION.\n"
        "         Decides whether widening openpilot's accepted range would buy finer control.")
    e4tq = np.asarray(z["e4tq"], float)          # i16be of 0x0E4 bytes 0:2, src 129 (bus 1 TX)
    sctq = np.asarray(z["sc_tq"], float)         # the same command off `sendcan`
    a = np.abs(e4tq[eng])
    C = dict(n_engaged=int(eng.sum()),
             median_abs=float(np.median(a)), p75_abs=float(np.percentile(a, 75)),
             p90_abs=float(np.percentile(a, 90)), p99_abs=float(np.percentile(a, 99)),
             max_abs=float(a.max()), mean_abs=float(a.mean()),
             rail=RAIL,
             rail_duty_ge_full=float(np.mean(a >= RAIL)),
             rail_duty_ge_99pct=float(np.mean(a >= 0.99 * RAIL)),
             rail_duty_ge_95pct=float(np.mean(a >= 0.95 * RAIL)),
             rail_duty_ge_90pct=float(np.mean(a >= 0.90 * RAIL)),
             rail_duty_ge_50pct=float(np.mean(a >= 0.50 * RAIL)),
             rail_duty_ge_25pct=float(np.mean(a >= 0.25 * RAIL)),
             rail_duty_ge_10pct=float(np.mean(a >= 0.10 * RAIL)),
             zero_duty=float(np.mean(a == 0)))
    print("  |0x0E4| ENGAGED (n=%d, %.1f s):  median %.0f   p75 %.0f   p90 %.0f   p99 %.0f   "
          "max %.0f   mean %.1f"
          % (C["n_engaged"], C["n_engaged"] * DT, C["median_abs"], C["p75_abs"], C["p90_abs"],
             C["p99_abs"], C["max_abs"], C["mean_abs"]))
    print("  RAIL DUTY vs openpilot's +-4096:")
    for k, lab in (("rail_duty_ge_full", ">= 4096 (AT the rail)"),
                   ("rail_duty_ge_99pct", ">= 4055 (99 %)"),
                   ("rail_duty_ge_95pct", ">= 3891 (95 %)"),
                   ("rail_duty_ge_90pct", ">= 3686 (90 %)"),
                   ("rail_duty_ge_50pct", ">= 2048 (50 %)"),
                   ("rail_duty_ge_25pct", ">= 1024 (25 %)"),
                   ("rail_duty_ge_10pct", ">=  410 (10 %)")):
        print("      %-24s %8.4f %%   (%8.1f s)" % (lab, 100 * C[k], C[k] * C["n_engaged"] * DT))
    print("      exactly zero            %8.4f %%   (%8.1f s)"
          % (100 * C["zero_duty"], C["zero_duty"] * C["n_engaged"] * DT))

    # QUANTISATION -- distinct codes and the step
    u = np.unique(e4tq[eng])
    d = np.diff(np.sort(u))
    d = d[d > 0]
    C["distinct_codes_engaged"] = int(len(u))
    C["code_min"] = float(u.min())
    C["code_max"] = float(u.max())
    C["step_min"] = float(d.min()) if len(d) else np.nan
    C["step_p50"] = float(np.median(d)) if len(d) else np.nan
    C["gcd_like_step"] = float(d.min()) if len(d) else np.nan
    # frame-to-frame increments -- the actual slew granularity openpilot uses
    de = np.diff(e4tq)
    dn = np.abs(de[np.abs(de) > 0])
    C["frame_delta_min"] = float(dn.min()) if len(dn) else np.nan
    C["frame_delta_p50"] = float(np.median(dn)) if len(dn) else np.nan
    C["frame_delta_p90"] = float(np.percentile(dn, 90)) if len(dn) else np.nan
    C["frame_delta_max"] = float(dn.max()) if len(dn) else np.nan
    print("  QUANTISATION: %d distinct codes engaged, range [%.0f, %.0f], smallest gap between "
          "adjacent observed codes %.0f, median gap %.0f"
          % (C["distinct_codes_engaged"], C["code_min"], C["code_max"],
             C["step_min"], C["step_p50"]))
    print("      frame-to-frame |delta| (nonzero): min %.0f  p50 %.0f  p90 %.0f  max %.0f"
          % (C["frame_delta_min"], C["frame_delta_p50"], C["frame_delta_p90"],
             C["frame_delta_max"]))
    print("      => the command is NOT quantisation-limited if min gap == 1 LSB and the "
          "distribution sits far from the rail.")
    # occupancy histogram in 256-wide bins
    hb = np.arange(0, RAIL + 257, 256)
    hh, _ = np.histogram(a, bins=hb)
    C["hist_256_bins"] = [int(x) for x in hh]
    print("      |cmd| occupancy in 256-wide bins (engaged):")
    for i in range(0, len(hh), 4):
        print("        " + "  ".join("%5d-%5d:%6.2f%%" % (hb[j], hb[j + 1], 100 * hh[j] / len(a))
                                     for j in range(i, min(i + 4, len(hh)))))
    # sanity: sendcan vs bus
    ok = np.isfinite(sctq) & np.isfinite(e4tq)
    C["sendcan_vs_bus_corr"] = float(np.corrcoef(sctq[ok & eng], e4tq[ok & eng])[0, 1])
    print("  sanity: corr(sendcan 0x0E4, bus 0x0E4) engaged = %.4f" % C["sendcan_vs_bus_corr"])
    OUT["command"] = C

    Path(HERE / "_scratch/out/_v103_r9e_census.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_census.json")


if __name__ == "__main__":
    main()
