# -*- coding: utf-8 -*-
"""Apply the V294 fork revert to the operator's StarPilot clone (Dom).  Exact-string edits, each asserted to
match exactly once, so a drifted file fails loudly instead of being half-patched.  Idempotent-unsafe: run once."""
import json
import sys
from pathlib import Path

ROOT = Path("C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")


def patch(rel, subs):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for a, b in subs:
        n = s.count(a)
        assert n == 1, (rel, a[:70], n)
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"{rel}: {len(subs)} edit(s)")


patch("common/params_keys.h", [
    ('    {"AccordRatePlantFF", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},',
     "    // V294 (2026-09-20): the EPS is a torque map with a 1 kHz acceleration trim, not a rate servo -- the rate-plant\n"
     "    // feedforward's model no longer describes it, so it ships OFF (the generic torque-controller feedforward path).\n"
     '    {"AccordRatePlantFF", {PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}},'),
    ("    // stock_value (Safe Mode) = every term off; the defaults are the rev-3 flight settings.\n"
     '    {"AccordHoldMap", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordFrictionHyst", {PERSISTENT, FLOAT, "0.015", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordRateLoopGain", {PERSISTENT, FLOAT, "0.0006", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordErrorNotchQ", {PERSISTENT, FLOAT, "1.0", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordRefFilter", {PERSISTENT, FLOAT, "0.12", "0.0", 2, SETTINGS_SIMPLE}},',
     "    // stock_value (Safe Mode) = every term off.  V294 (2026-09-20): the DEFAULTS are the stock values too -- every\n"
     "    // torque-mode term is REVERTED (off) now that the EPS carries its own 1 kHz acceleration trim; the code and the\n"
     "    // toggles stay so any term can be turned back on from the road.  (Rev 3-6.4 defaults were the flight settings.)\n"
     '    {"AccordHoldMap", {PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordFrictionHyst", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordRateLoopGain", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordErrorNotchQ", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},\n'
     '    {"AccordRefFilter", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},'),
    ("    // stock_value 0 = flat AccordTorqueKi (the rev-3 behaviour).\n"
     '    {"AccordTorqueKiHigh", {PERSISTENT, FLOAT, "2.5", "0.0", 2, SETTINGS_SIMPLE}},',
     "    // 0 = flat AccordTorqueKi (the rev-3 behaviour; the V294 default).\n"
     '    {"AccordTorqueKiHigh", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},'),
    ('    {"AccordDobHz", {PERSISTENT, FLOAT, "0.6", "0.0", 2, SETTINGS_SIMPLE}},',
     '    {"AccordDobHz", {PERSISTENT, FLOAT, "0.0", "0.0", 2, SETTINGS_SIMPLE}},'),
    ('    {"AccordHoldLevel", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},',
     '    {"AccordHoldLevel", {PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}},'),
    ('    {"AccordFrictionHystBand", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},',
     '    {"AccordFrictionHystBand", {PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}},'),
    ('    {"AccordDitherGate", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},',
     '    {"AccordDitherGate", {PERSISTENT, BOOL, "1", "0", 2, SETTINGS_SIMPLE}},\n'
     "    // V294 (2026-09-20): cutoff (Hz) of the lateral-jerk low-pass in the Accord delay-compensation stage.  Rev 6 hard-coded\n"
     "    // 4.0 (measured: half the setpoint-chain lag of the generic 1.2, see HONDA_ACCORD_JERK_LP_HZ); it was the one\n"
     "    // torque-mode-era edit with no switch.  Default and stock 1.2 = the generic path, i.e. a full revert.\n"
     '    {"AccordJerkLpHz", {PERSISTENT, FLOAT, "1.2", "1.2", 2, SETTINGS_SIMPLE}},'),
])

patch("starpilot/common/starpilot_variables.py", [
    ('    toggle.accord_rate_plant_ff = self.get_value("AccordRatePlantFF", condition=is_honda_accord and known("AccordRatePlantFF"), default=True)',
     "    # V294 (2026-09-20): the EPS is a torque map + 1 kHz acceleration trim, not a rate servo; the plant FF ships OFF.\n"
     '    toggle.accord_rate_plant_ff = self.get_value("AccordRatePlantFF", condition=is_honda_accord and known("AccordRatePlantFF"), default=False)'),
    ('    toggle.accord_hold_map = self.get_value("AccordHoldMap", condition=is_honda_accord and known("AccordHoldMap"), default=True)\n'
     '    toggle.accord_friction_hyst = self.get_value("AccordFrictionHyst", cast=float, condition=is_honda_accord and known("AccordFrictionHyst"), default=0.015, min=0.0, max=0.05)\n'
     '    toggle.accord_rate_loop_gain = self.get_value("AccordRateLoopGain", cast=float, condition=is_honda_accord and known("AccordRateLoopGain"), default=0.0006, min=0.0, max=0.003)\n'
     '    toggle.accord_error_notch_q = self.get_value("AccordErrorNotchQ", cast=float, condition=is_honda_accord and known("AccordErrorNotchQ"), default=1.0, min=0.0, max=4.0)\n'
     '    toggle.accord_ref_filter = self.get_value("AccordRefFilter", cast=float, condition=is_honda_accord and known("AccordRefFilter"), default=0.12, min=0.0, max=0.5)\n',
     "    # V294 (2026-09-20): every torque-mode term defaults OFF (= its stock value).  The EPS now carries its own 1 kHz\n"
     "    # acceleration trim on the torque map; the fork runs the generic torque controller.  Each term stays switchable.\n"
     '    toggle.accord_hold_map = self.get_value("AccordHoldMap", condition=is_honda_accord and known("AccordHoldMap"), default=False)\n'
     '    toggle.accord_friction_hyst = self.get_value("AccordFrictionHyst", cast=float, condition=is_honda_accord and known("AccordFrictionHyst"), default=0.0, min=0.0, max=0.05)\n'
     '    toggle.accord_rate_loop_gain = self.get_value("AccordRateLoopGain", cast=float, condition=is_honda_accord and known("AccordRateLoopGain"), default=0.0, min=0.0, max=0.003)\n'
     '    toggle.accord_error_notch_q = self.get_value("AccordErrorNotchQ", cast=float, condition=is_honda_accord and known("AccordErrorNotchQ"), default=0.0, min=0.0, max=4.0)\n'
     '    toggle.accord_ref_filter = self.get_value("AccordRefFilter", cast=float, condition=is_honda_accord and known("AccordRefFilter"), default=0.0, min=0.0, max=0.5)\n'),
    ('    toggle.accord_torque_ki_high = self.get_value("AccordTorqueKiHigh", cast=float, condition=is_honda_accord and known("AccordTorqueKiHigh"), default=2.5, min=0.0, max=6.0)\n'
     "    # rev 5 (2026-09-15): disturbance-observer corner frequency; 0 = off (rev 4 behaviour)\n"
     '    toggle.accord_dob_hz = self.get_value("AccordDobHz", cast=float, condition=is_honda_accord and known("AccordDobHz"), default=0.6, min=0.0, max=3.0)\n'
     '    toggle.accord_hold_level = self.get_value("AccordHoldLevel", cast=bool, condition=is_honda_accord and known("AccordHoldLevel"), default=True)\n'
     '    toggle.accord_friction_hyst_band = self.get_value("AccordFrictionHystBand", cast=bool, condition=is_honda_accord and known("AccordFrictionHystBand"), default=True)\n',
     '    toggle.accord_torque_ki_high = self.get_value("AccordTorqueKiHigh", cast=float, condition=is_honda_accord and known("AccordTorqueKiHigh"), default=0.0, min=0.0, max=6.0)\n'
     "    # rev 5 (2026-09-15): disturbance-observer corner frequency; 0 = off\n"
     '    toggle.accord_dob_hz = self.get_value("AccordDobHz", cast=float, condition=is_honda_accord and known("AccordDobHz"), default=0.0, min=0.0, max=3.0)\n'
     '    toggle.accord_hold_level = self.get_value("AccordHoldLevel", cast=bool, condition=is_honda_accord and known("AccordHoldLevel"), default=False)\n'
     '    toggle.accord_friction_hyst_band = self.get_value("AccordFrictionHystBand", cast=bool, condition=is_honda_accord and known("AccordFrictionHystBand"), default=False)\n'
     "    # V294 (2026-09-20): the jerk low-pass cutoff of the delay-compensation stage, Accord only.  1.2 = the generic path\n"
     "    # (the revert); 4.0 = rev 6's measured value (half the setpoint-chain lag).  Bounded so the filter stays a smoother.\n"
     '    toggle.accord_jerk_lp_hz = self.get_value("AccordJerkLpHz", cast=float, condition=is_honda_accord and known("AccordJerkLpHz"), default=1.2, min=0.5, max=8.0)\n'),
])

patch("selfdrive/controls/lib/latcontrol_torque.py", [
    ("        # 38-frame difference that is already smooth.  See HONDA_ACCORD_JERK_LP_HZ for the measured chain response.\n"
     "        self.jerk_filter.update_alpha(1.0 / (2.0 * np.pi * max(HONDA_ACCORD_JERK_LP_HZ, 0.1)))",
     "        # 38-frame difference that is already smooth.  See HONDA_ACCORD_JERK_LP_HZ for the measured chain response.\n"
     "        # V294 (2026-09-20): the cutoff is the AccordJerkLpHz toggle; its default 1.2 is the generic path (reverted),\n"
     "        # 4.0 restores rev 6's measured value.  It was the one torque-mode-era edit with no switch.\n"
     '        jerk_lp_hz = float(getattr(starpilot_toggles, "accord_jerk_lp_hz", LP_FILTER_CUTOFF_HZ))\n'
     "        self.jerk_filter.update_alpha(1.0 / (2.0 * np.pi * max(jerk_lp_hz, 0.1)))"),
])

# the settings layout: AccordJerkLpHz right after AccordDitherGate in the Custom Patches section
p = ROOT / "starpilot/common/assets/device_settings_layout.json"
s = p.read_text(encoding="utf-8")
i = s.index('        "key": "AccordDitherGate",')
j = s.index("\n      },", i) + len("\n      },")
entry = """
      {
        "key": "AccordJerkLpHz",
        "label": "Accord: Jerk Low-Pass Cutoff (Hz)",
        "description": "Cutoff of the lateral-jerk low-pass inside the delay-compensation stage of the Accord torque controller. The stage setpoint = u(t-D) + F_j x (u(t) - u(t-D)) is an exact delay canceller when F_j = 1, so every bit of its residual lag and its 0.4-1 Hz gain bump comes from this one smoother. 1.2 Hz is the generic openpilot value (the V294 default: the full revert of the torque-mode revisions). 4.0 Hz is the value rev 6 measured on this car's setpoint chain (group lag at 0.25 Hz 0.271 -> 0.128 s at 19 m/s, flatter 0.5-0.7 Hz response) and hard-coded; it is offered here as a switch instead. Raise it only after the EPS change has been scored on its own.",
        "data_type": "float",
        "ui_type": "numeric",
        "min": 0.5,
        "max": 8.0,
        "step": 0.1,
        "precision": 1,
        "vehicle_makes": [
          "Honda"
        ],
        "settings_tier": "simple"
      },"""
s = s[:j] + entry + s[j:]
json.loads(s)
p.write_text(s, encoding="utf-8", newline="\n")
print("device_settings_layout.json: AccordJerkLpHz entry added, JSON parses")
