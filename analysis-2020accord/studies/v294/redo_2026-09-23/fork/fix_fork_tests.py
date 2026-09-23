# -*- coding: utf-8 -*-
"""V294 redo (2026-09-23): give the five rev-6.4 Accord tests their toggles explicitly, guard LaneChangeTurnGate with
known(), and mark the kit's fork_revert_patch.py as a partial record. Exact-string edits, each asserted once."""
from pathlib import Path
FORK = Path("C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")
KIT = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")

def sub1(p, old, new):
    s = p.read_text(encoding="utf-8")
    assert s.count(old) == 1, (p, old[:60], s.count(old))
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")

t = FORK / "selfdrive/controls/tests/test_latcontrol.py"
HELPER = '''  @staticmethod
  def _rev64_accord_toggles(toggles):
    # V294 (2026-09-20, 54ff1ea39): every V293 torque-mode term now defaults to STOCK, so a test of the rev-6.4 law
    # must ask for it -- these are exactly the controller's pre-V294 getattr fallbacks (rev 6.4, 84766cdc5)
    toggles.accord_rate_plant_ff = True
    toggles.accord_hold_map = True
    toggles.accord_hold_level = True
    toggles.accord_friction_hyst = 0.015
    toggles.accord_friction_hyst_band = True
    toggles.accord_rate_loop_gain = 0.0006
    toggles.accord_ref_filter = 0.12
    toggles.accord_error_notch_q = 1.0
    toggles.accord_jerk_lp_hz = 4.0
    return toggles

  @staticmethod
  def _run_honda_accord_rate_plant(lat_accel_offset, seconds=2.0):
    controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
    TestLatControl._rev64_accord_toggles(toggles)
'''
sub1(t, '''  @staticmethod
  def _run_honda_accord_rate_plant(lat_accel_offset, seconds=2.0):
    controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
''', HELPER)
sub1(t, '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      toggles.accord_rate_loop_gain = gain
''', '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      TestLatControl._rev64_accord_toggles(toggles)
      toggles.accord_rate_loop_gain = gain
''')
sub1(t, '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      toggles.accord_dob_hz = dob_hz
''', '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      TestLatControl._rev64_accord_toggles(toggles)
      toggles.accord_dob_hz = dob_hz
''')
sub1(t, '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      toggles.accord_friction_hyst = hyst
''', '''      controller, VM, CS, params, toggles = TestLatControl._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)
      TestLatControl._rev64_accord_toggles(toggles)
      toggles.accord_friction_hyst = hyst
''')

v = FORK / "starpilot/common/starpilot_variables.py"
sub1(v, 'toggle.lane_change_turn_gate = self.get_value("LaneChangeTurnGate", cast=bool, condition=toggle.lane_changes, default=True)',
        'toggle.lane_change_turn_gate = self.get_value("LaneChangeTurnGate", cast=bool, condition=toggle.lane_changes and known("LaneChangeTurnGate"), default=True)')

k = KIT / "analysis-2020accord/studies/v294/fork_revert_patch.py"
s = k.read_text(encoding="utf-8")
note = ('# 🛑 PARTIAL RECORD (redo audit 2026-09-23): this script reproduces the params_keys.h, starpilot_variables.py and\n'
        '# device_settings_layout.json edits of Dom 54ff1ea39 exactly, but the commit ALSO carried three edits made by hand:\n'
        '# the 8 getattr fallback flips in selfdrive/controls/lib/latcontrol_torque.py, the AccordJerkLpHz key in\n'
        '# starpilot/common/safe_mode.py, and the test_device_settings_layout.py CUSTOM_PATCH_KEYS/pinned-default edits.\n'
        '# The commit is the record; this script is not a full replay.\n')
assert note not in s
first = s.index('\n', s.index('"""', s.index('"""') + 3)) + 1 if s.lstrip().startswith(('"""', '#', 'from', 'import')) else 0
lines = s.splitlines(keepends=True)
# insert after the module docstring (first line starting with """ that closes)
out = []; inserted = False; in_doc = False
for i, ln in enumerate(lines):
    out.append(ln)
    if not inserted:
        if ln.lstrip().startswith('"""') and not in_doc:
            in_doc = True
            if ln.strip().count('"""') >= 2 and len(ln.strip()) > 3:
                out.append(note); inserted = True
        elif in_doc and '"""' in ln:
            out.append(note); inserted = True
assert inserted
k.write_text("".join(out), encoding="utf-8", newline="\n")
print("ok")
