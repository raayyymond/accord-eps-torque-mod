# -*- coding: utf-8 -*-
"""ARM-RF: rev 6.4 as flown, with the setpoint reference prefilter HALVED (AccordRefFilter 0.06 -> 0.03).

WHY (hsurface/, 2026-09-20). On the operator's own goal metric -- how closely achieved lateral acceleration tracks
the model's DESIRED lateral acceleration, with V282 as the reference for "good" -- torque mode's miss below 0.6 Hz
is almost entirely TIMING, not gain: the gain term is 0-3% of its own in-band error and the gain difference is zero
or in torque mode's favour below 0.3 Hz. Torque mode is +140 to +340 ms slower depending on the cell.

`AccordRefFilter` is two cascaded FirstOrderFilters on the setpoint (latcontrol_torque.py:164-165, 326), so its
group lag is 2*RC at low frequency. MEASURED on 15/15 routes carrying data, across three distinct flown values and
six commits, at unity magnitude (|H_xz| = 1.01-1.10, i.e. pure phase):
    ABSENT (all V282 reference routes, + r70/r71)  ->  12-18 ms
    RF 0.06 (r6c/r6d/r6e, rev 6.4)                 ->  117-124 ms   (2*RC predicts 120)
    RF 0.12 (r72/r73/r75/r76)                      ->  253 ms       (predicts 239)
Two independent methods put its share of the 0.15-0.60 Hz tracking-error gap at 47% (re-reference the metric to the
logged shaped setpoint) and 49% (the torque routes that flew with no filter at all read NRMSE 0.638 against V282's
0.434 and the RF-carrying revs' 0.849).

The filter DOES NOT EXIST in the reference fork: `accord_ref_filter` returns 0 hits at 0f98d8c75 and 57410c3b, the
commits all three V282 reference routes flew (verified by git grep). So this is not a tuning difference -- it is a
stage the reference never had.

WHY 0.03 AND NOT 0. The filter's stated purpose is to stop a planner step ringing the 1-2 Hz steering mode through
the feedforward and P. The top of the exposure-weighted gap ranking is exactly a 0.60-1.20 Hz over-delivery at
large demand (|H| 1.20 -> 2.15 at 8-15 m/s against V282's 1.20), and there the SAME toggle acts with the OPPOSITE
sign -- it is currently suppressing the fork's own reference-stage gain bump. Halving takes ~60 ms of the ~120 ms
back while leaving half the suppression in place. Removing it entirely re-arms an estimated ~+7% of 0.6-1.2 Hz
reference gain (NOT the ~+28% a naive read gives: rev 6.4 already carries HONDA_ACCORD_JERK_LP_HZ = 4.0, which the
V282-era commits did not) -- that figure is an LTI composition of measured legs, i.e. BELIEF, not EVIDENCE.

PRE-REGISTERED REVERT SIGNATURE, written before the drive: the 0.60-1.20 Hz / 8-22 m/s / large-demand cells, which
read |H| 1.88-2.15 today against V282's 1.18-1.20. If those rise, halve again or revert.
READOUT: 0.15-0.60 Hz NRMSE and model->achieved lag at 8-15, 15-22 and 22-40 m/s, against the V282 rows in
hsurface/surface/. The reference-stage leg (model -> logged desiredLateralAccel) must itself drop to ~60 ms; if it
does not, the toggle did not take and the drive must not be scored.
⚠ Record the flown jerk low-pass as well -- the sign of this toggle's effect reverses in the band that constant
shapes, so a result without it is uninterpretable there.

Exactly ONE setting differs from the as-flown config (asserted). Codec positive control runs first.
"""
import base64, json, os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1


def xor(d, k):
    return "".join(chr(ord(c) ^ ord(k[i % len(k)])) for i, c in enumerate(d))


def enc(d):
    return base64.b64encode(xor(json.dumps(d), XOR_KEY).encode()).decode()


def dec(e):
    return json.loads(xor(base64.b64decode(e.encode()).decode(), XOR_KEY))


pairs = 0
for f in sorted(os.listdir(REF)):
    if not f.endswith(".decoded.json"):
        continue
    ep = REF / f.replace(".decoded.json", ".json")
    if not ep.exists():
        continue
    e = json.load(open(ep, encoding="utf-8")); d = json.load(open(REF / f, encoding="utf-8"))
    assert dec(e["data"]) == d, f"decode mismatch {f}"
    assert dec(enc(d)) == d, f"re-encode mismatch {f}"
    assert e["format"] == FORMAT and e["version"] == VERSION and e["settingsCount"] == len(d), f
    pairs += 1
assert pairs > 0, "no reference pair to validate the codec against"
print(f"codec positive control: {pairs} reference pairs round-trip both directions")

flown = json.load(open(REF / "toggle-config_V293_r64_ARM-A_asflown.decoded.json", encoding="utf-8"))
assert flown["AccordDobHz"] == 0.6 and flown["AccordHoldLevel"] is True, "ARM-A is not the rev 6.4 as-flown config"
assert float(flown["AccordRefFilter"]) == 0.06, f"as-flown AccordRefFilter is {flown.get('AccordRefFilter')}, expected 0.06"

arm = dict(flown)
arm["AccordRefFilter"] = 0.03
diff = {k: (flown.get(k), arm.get(k)) for k in set(flown) | set(arm) if flown.get(k) != arm.get(k)}
assert diff == {"AccordRefFilter": (0.06, 0.03)}, diff
assert 0.0 <= arm["AccordRefFilter"] <= 0.5, "outside the toggle's declared bounds (starpilot_variables.py:836)"

name = "toggle-config_V293_r64_ARM-RF_prefilter-halved"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(arm), "data": enc(arm)},
          open(out, "w", encoding="utf-8"), indent=1)
json.dump(arm, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == arm, "written file does not decode to the intended config"
print(f"wrote {out.name}: {len(arm)} settings, one change {diff}, verified by decoding the written file")
print("  predicted reference-stage lag: 2*RC = 60 ms (from 120 ms). Gate this from the log before scoring.")
