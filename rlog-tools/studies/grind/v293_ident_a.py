# -*- coding: utf-8 -*-
"""v293_ident_a.py -- PART A: attribution and exposure for route 70 (V293's first flight).
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Answers: which toggles were actually in force (from initData.params AND from the 100 Hz torqueState
read, which survives a mid-route change), what the delay/params estimators said, how much laterally
engaged time there is and where in speed, and how many overrides / disengagements.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
pr = L.pr_factory(OUT)
g = L.load("r70_v293")
meta = g["meta"]
n = g["n"]
DT = 1.0 / L.FS

pr("=" * 102)
pr("V293 PLANT IDENTIFICATION -- PART A: ATTRIBUTION AND EXPOSURE")
pr("route %s   (%d segments)" % (meta["route"], len(meta["segments"])))
pr("=" * 102)

# ------------------------------------------------------------------------------------------------
pr("\nA1. THE TOGGLE CONFIG, key by key, from initData.params [EVIDENCE -- logged once at process start]")
EXPECT = {"AccordRatePlantFF": "0", "SteerKP": "0.3", "AccordTorqueKi": "0.15", "SteerFriction": "0.0",
          "SteerLatAccel": "6.0", "ForceAutoTuneOff": "1", "AdvancedLateralTune": "1",
          "AccordTurnFFTaper": "0"}
P = meta["params"]
pr("   %-28s %-12s %-12s %s" % ("key", "logged", "expected", "verdict"))
allok = True
for k, want in EXPECT.items():
    got = P.get(k, "<ABSENT>")
    try:
        ok = abs(float(got) - float(want)) < 1e-9
    except Exception:
        ok = str(got).strip() == want
    allok &= ok
    pr("   %-28s %-12s %-12s %s" % (k, got, want, "MATCH" if ok else "*** MISMATCH ***"))
pr("   -> toggle gate: %s" % ("PASS -- the torque config was installed" if allok else "FAIL"))
pr("\n   context params (not gated):")
for k in ("SteerRatio", "SteerDelay", "UseAutoSteerDelay", "AccordVariableSteerRatio",
          "ForceTorqueController", "ForceAutoTune", "AccordFFRateGain", "AccordEpsGainScale",
          "AccordEpsSpringScale", "GitBranch", "GitCommit", "GitCommitDate"):
    if k in P:
        pr("      %-28s = %s" % (k, str(P[k])[:60]))

# ------------------------------------------------------------------------------------------------
pr("\nA2. Kp READ AT 100 Hz from torqueState p/error [EVIDENCE -- pid.update sets p = k_p * error,")
pr("    and the fork logs pid_log.error = error_with_lsf, so p/error IS the live SteerKP]")
act = (g["cs_active"] > 0.5) & np.isfinite(g["p"]) & np.isfinite(g["err"]) & (np.abs(g["err"]) > 1e-6)
ratio = g["p"][act] / g["err"][act]
pr("    frames %d   median %.4f   IQR [%.4f, %.4f]   within 5%% of 0.300: %.1f%%"
   % (act.sum(), np.median(ratio), np.percentile(ratio, 25), np.percentile(ratio, 75),
      100.0 * np.mean(np.abs(ratio - 0.30) <= 0.015)))
pr("    -> kp gate (0.300 +- 0.03): %s" % ("PASS" if abs(np.median(ratio) - 0.30) <= 0.03 else "FAIL"))

pr("\nA3. FEEDFORWARD BRANCH -- median f / desiredLateralAccel  [friction 0 + rate-plant FF off => 1.000]")
fa = act & np.isfinite(g["f"]) & (np.abs(g["la_des"]) > 0.05)
fr = g["f"][fa] / g["la_des"][fa]
pr("    frames %d   median %.4f   IQR [%.4f, %.4f]" % (fa.sum(), np.median(fr),
                                                       np.percentile(fr, 25), np.percentile(fr, 75)))
pr("    -> branch gate (>= 0.75): %s" % ("PASS" if np.median(fr) >= 0.75 else "FAIL"))
A = np.vstack([g["la_des"][fa], np.ones(fa.sum())]).T
sl, ic = np.linalg.lstsq(A, g["f"][fa], rcond=None)[0]
pr("    whole-route regression f on D: slope %.4f  intercept %+.4f  (context only, not a gate)" % (sl, ic))

# is I ever non-zero?  Ki = 0.15 should integrate.
ia = act & np.isfinite(g["i"])
pr("\n    integrator: |i| p50 %.4f  p95 %.4f  max %.4f   (Ki = 0.15, so a live integrator)"
   % (np.percentile(np.abs(g["i"][ia]), 50), np.percentile(np.abs(g["i"][ia]), 95),
      np.max(np.abs(g["i"][ia]))))

# ------------------------------------------------------------------------------------------------
pr("\nA4. DELAY AND PARAMETER ESTIMATORS AS LOGGED [EVIDENCE -- liveDelay / liveParameters]")
D = g["raw"]
pr("    liveDelay.lateralDelay      : %s  (distinct %d)  -- the echoed SteerDelay toggle"
   % (np.unique(np.round(D["ld_delay"], 4))[:4], len(np.unique(np.round(D["ld_delay"], 4)))))
pr("    liveDelay.lateralDelayEstimate: %.4f .. %.4f  (distinct %d, validBlocks %d..%d)"
   % (D["ld_est"].min(), D["ld_est"].max(), len(np.unique(np.round(D["ld_est"], 4))),
      D["ld_blocks"].min(), D["ld_blocks"].max()))
pr("    liveParameters.steerRatio   : %.3f .. %.3f   (median %.3f)"
   % (D["lpar_sr"].min(), D["lpar_sr"].max(), np.median(D["lpar_sr"])))
pr("    liveParameters.stiffness    : %.4f .. %.4f   (median %.4f)"
   % (D["lpar_stiff"].min(), D["lpar_stiff"].max(), np.median(D["lpar_stiff"])))
pr("    liveParameters.angleOffset  : %.4f .. %.4f   (median %.4f)"
   % (D["lpar_ao"].min(), D["lpar_ao"].max(), np.median(D["lpar_ao"])))

# ------------------------------------------------------------------------------------------------
pr("\nA5. EXPOSURE  [EVIDENCE -- lateral engaged = 0xE4 STEER_REQUEST AND 0x18F SCA]")
tot = n * DT
eng = g["eng"]
lat = g["lat_active"] > 0.5
enb = g["enabled"] > 0.5
pr("    route wall time                 %8.1f s   (%.1f min)" % (tot, tot / 60.0))
pr("    carControl.enabled (any engage) %8.1f s   %5.1f%%" % (enb.sum() * DT, 100.0 * enb.mean()))
pr("    carControl.latActive            %8.1f s   %5.1f%%" % (lat.sum() * DT, 100.0 * lat.mean()))
pr("    LATERAL engaged on the wire     %8.1f s   %5.1f%%" % (eng.sum() * DT, 100.0 * eng.mean()))
pr("    longitudinal-only (enabled & not lateral) %5.1f s  -- the confound, excluded everywhere below"
   % ((enb & ~eng).sum() * DT))
pr("    agreement latActive vs wire-engaged: %.2f%% of frames" % (100.0 * np.mean(lat == eng)))

pr("\n    speed histogram of LATERALLY ENGAGED time:")
pr("    %-10s %10s %8s %10s %10s" % ("band m/s", "seconds", "% eng", "|angle| p50", "|angle| p95"))
for k, (lo, hi) in enumerate(L.BANDS):
    s = eng & (g["v"] >= lo) & (g["v"] < hi)
    if s.sum():
        pr("    %-10s %10.1f %7.1f%% %10.2f %10.2f"
           % (L.BANDNAME[k], s.sum() * DT, 100.0 * s.sum() / max(eng.sum(), 1),
              np.percentile(np.abs(g["ang"][s]), 50), np.percentile(np.abs(g["ang"][s]), 95)))
    else:
        pr("    %-10s %10.1f" % (L.BANDNAME[k], 0.0))
pr("    engaged speed: p05 %.1f  p50 %.1f  p95 %.1f  max %.1f m/s"
   % tuple(np.percentile(g["v"][eng], [5, 50, 95, 100])))

pr("\n    driver overrides and disengagements:")
pressed = g["press"] > 0.5
tr = np.diff(np.concatenate([[0], (eng & pressed).astype(int)]))
pr("    steeringPressed while laterally engaged: %.1f s (%.1f%% of engaged), %d distinct episodes"
   % ((eng & pressed).sum() * DT, 100.0 * (eng & pressed).sum() / max(eng.sum(), 1), (tr == 1).sum()))
de = np.diff(np.concatenate([[0], eng.astype(int)]))
pr("    lateral engage transitions: %d engages, %d disengages" % ((de == 1).sum(), (de == -1).sum()))
sat = g["sat"] > 0.5
pr("    torqueState.saturated while engaged: %.1f s (%.1f%% of engaged)"
   % ((eng & sat).sum() * DT, 100.0 * (eng & sat).sum() / max(eng.sum(), 1)))

pr("\n    CLEAN identification exposure (engaged, hands-off, unsaturated, 2 s recovery buffer),")
pr("    in stretches >= 12 s -- the mask tau_identify.py uses:")
m = L.clean_mask(g, hands_off=True)
st = L.stretches(m, int(12 * L.FS))
pr("    %-10s %10s %8s" % ("band m/s", "seconds", "stretches"))
tots = 0.0
for k, (lo, hi) in enumerate(L.BANDS):
    sec, cnt = 0.0, 0
    for (a, b) in st:
        vv = np.median(g["v"][a:b])
        if lo <= vv < hi:
            sec += (b - a) * DT; cnt += 1
    tots += sec
    pr("    %-10s %10.1f %8d" % (L.BANDNAME[k], sec, cnt))
pr("    %-10s %10.1f %8d" % ("TOTAL", tots, len(st)))

# ------------------------------------------------------------------------------------------------
pr("\nA6. THE 427 TAP AND THE COMMAND -- is the open-loop torque map on the wire? [EVIDENCE]")
with open(os.path.join(L.SCRATCH, "v293_surface.json")) as fh:
    S = json.load(fh)
sT = np.array(S["V293_T"], float); sT282 = np.array(S["V282_T"], float)
e = g["eng"] & np.isfinite(g["T"]) & np.isfinite(g["cmd"])
pr("    engaged tap frames (100 Hz grid) %d ; |tap| p50 %.0f p95 %.0f max %.0f counts"
   % (e.sum(), np.percentile(np.abs(g["T"][e]), 50), np.percentile(np.abs(g["T"][e]), 95),
      np.abs(g["T"][e]).max()))
pr("    |0xE4 cmd| p50 %.0f p95 %.0f max %.0f counts"
   % (np.percentile(np.abs(g["cmd"][e]), 50), np.percentile(np.abs(g["cmd"][e]), 95),
      np.abs(g["cmd"][e]).max()))
pr("    sign(tap) == sign(cmd) on %.3f of engaged frames with |cmd|>20  [the measured polarity is +]"
   % np.mean(np.sign(g["T"][e & (np.abs(g["cmd"]) > 20)]) == np.sign(g["cmd"][e & (np.abs(g["cmd"]) > 20)])))
# empirical map |tap| vs |cmd|, binned -- this IS the surface with the loop open
bins = np.arange(0, 4200, 100.0)
pr("\n    EMPIRICAL delivered-torque map, binned on |0xE4 cmd| (engaged, all speeds):")
pr("    %-12s %8s %10s %10s %10s %10s" % ("|cmd| bin", "n", "|tap| p50", "model V293", "model V282", "tap/cmd"))
ac, at = np.abs(g["cmd"][e]), np.abs(g["T"][e])
for i in range(len(bins) - 1):
    s = (ac >= bins[i]) & (ac < bins[i + 1])
    if s.sum() < 50:
        continue
    c_mid = 0.5 * (bins[i] + bins[i + 1])
    idxm = min(320, int(round(c_mid / 16.1876)))
    if bins[i] % 400 == 0 or bins[i] < 400:
        pr("    %-12s %8d %10.0f %10.0f %10.0f %10.4f"
           % ("%.0f-%.0f" % (bins[i], bins[i + 1]), s.sum(), np.median(at[s]), sT[idxm], sT282[idxm],
              np.median(at[s]) / max(c_mid, 1)))

# openpilot's actuators.torque -> 0xE4 counts, measured on the wire
oe = e & np.isfinite(g["op_torque"]) & (np.abs(g["op_torque"]) > 0.01)
A = np.vstack([g["op_torque"][oe], np.ones(oe.sum())]).T
sl2, ic2 = np.linalg.lstsq(A, g["cmd"][oe], rcond=None)[0]
pr("\n    0xE4 counts vs openpilot actuators.torque:  cmd = %.1f * torque %+.1f   R2 %.4f   n %d"
   % (sl2, ic2, L.r2(g["cmd"][oe], A @ [sl2, ic2]), oe.sum()))
pr("    (negative slope is the carcontroller's own sign flip: apply_torque = interp(-torque*STEER_MAX))")
pr("    |actuators.torque| p50 %.3f p95 %.3f max %.3f ; duty |torque|>=0.95 : %.2f%% of engaged"
   % (np.percentile(np.abs(g["op_torque"][e]), 50), np.percentile(np.abs(g["op_torque"][e]), 95),
      np.max(np.abs(g["op_torque"][e])), 100.0 * np.mean(np.abs(g["op_torque"][e]) >= 0.95)))

txt = "\n".join(OUT)
os.makedirs(L.SCRATCH, exist_ok=True)
with open(os.path.join(L.SCRATCH, "v293_ident_a.txt"), "w", encoding="utf-8") as fh:
    fh.write(txt)
print("\n[written] %s" % os.path.join(L.SCRATCH, "v293_ident_a.txt"))
