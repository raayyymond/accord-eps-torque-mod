# -*- coding: utf-8 -*-
"""Write the Galaxy toggle-config files for the Accord EPS TORQUE-MODE firmware (V293+) and its revert.

The fork side of a torque-map EPS image is NOT code any more (2026-09-13, operator's call): it is a
plain toggle config that Galaxy restores through Settings -> toggle backup -> Restore.  Everything the
Testing-Ground / preset patches did on the control path is expressible with params that already exist
on `raayyymond-StarPilot/StarPilot` @ `Dom`:

    AccordRatePlantFF   True -> False   bypasses the rate-plant feedforward branch in latcontrol_torque.py
                                        (AccordEpsGainScale / AccordEpsSpringScale / AccordFFRateGain are
                                        read only inside that branch, so they go inert with no separate gate)
    SteerKP             0.9  -> 0.3     controlsd writes pid._k_p = [[0],[SteerKP]] every frame
    AccordTorqueKi      0.30 -> 0.15    applied in latcontrol_torque.py on every Accord frame
    SteerFriction       0.01 -> 0.00    🛑 a STABILITY choice: this fork feeds get_friction the LSF-inflated
                                        error, so the compensator gain is (friction/0.30)*(1+lsf/Kp) and a
                                        LOWER Kp makes it WORSE; at friction 0 the loop gain is monotone in Kp
    SteerLatAccel       6.0  -> 6.0     carried over so the first drive is not also a gain change (NOT an
                                        identification -- the first V293 drive identifies it)
    ForceAutoTuneOff    True (pinned)   makes the SteerLatAccel / SteerFriction params the live ones
    ForceAutoTune       False (pinned)
    AdvancedLateralTune True (pinned)   the SteerKP / SteerFriction / SteerLatAccel toggles are read only
                                        under it
    KeepLearnedLatAccelOffset True      the learner's roll/mounting bias stays -- it is a property of the
                                        device and the road, not of the EPS firmware
    AccordTurnFFTaper   False (pinned)  a shaping choice that would bias the LAF identification

The files are DELTAS, not full backups, on purpose.  Galaxy's /api/toggles/restore applies exactly the
keys present in the file and leaves every other param alone (`_restore_toggle_values` in
starpilot/system/the_galaxy/the_galaxy.py); a full 526-key backup taken on 2026-09-10 would also drag
back SteerRatio 16.33 and LaneChangeSmoothing 6, which route 6f's initData shows the operator has since
moved to 16.88 and 4.

File format = what Galaxy itself writes (`backup_toggle_values`): {"format": "starpilot-toggle-backup",
"version": 1, "createdAt": ISO-8601, "settingsCount": N, "data": base64(xor(json, KEY))}, with the codec
from starpilot/system/the_galaxy/utilities.py (`encode_parameters` / `decode_parameters`,
XOR_KEY = "s8#pL3*Xj!aZ@dWq", character-wise).  The codec is checked here against the operator's own
2026-09-10 backup and its decoded copy before anything is written.

REV 2 (2026-09-13, after the first V293 drive, route 70 -- `V293-PLANT-IDENT-2026-09-13.md`): the plant is a
SPRING + Coulomb friction, and the fork's own spring feedforward (the `AccordRatePlantFF` branch) is the right
SHAPE once its tables are re-identified -- which is fork CODE (commit 66cf4454a on Dom: HONDA_ACCORD_EPS_G_V /
K_V; the 4 m/s knot bounded by route 70's own hands-off data, ADV-REV2 finding 3), because no single
AccordEpsSpringScale fits both below 8 m/s and above 12 m/s.  The rev-2 delta then:

    AccordRatePlantFF   False -> True    the spring feedforward, on the V293 tables (fork >= 66cf4454a REQUIRED)
    AccordEpsSpringScale / AccordEpsGainScale 1.0   the tables carry the identification; scales stay unity
    AccordFFRateGain    0.5 (pinned)     with the V293 tables 1/G IS the measured viscous term, but the move term is fed
                                         a planner-limited reference: at 1.0 the FF alone passed full scale for 0.34 s
                                         below 8 m/s on route 70's demand (adversarial replay); at 0.5 max 0.81
    SteerFriction       0.00 -> 0.011    measured Coulomb friction 0.010-0.012, in this toggle's own unit -- the
                                         only term that opposes the friction behind the operator's "snapping";
                                         describing-function check: no relay limit cycle below 0.0235 at 4.5 m/s
    SteerLatAccel       6.0 -> 14.0      in the plant-FF branch this scales ONLY P and I: the one lever on the
                                         low-speed loop gain (the hard-coded low-speed factor is ADDED to Kp, so
                                         SteerKP cannot reduce it; as flown PM -11 deg / Ms 12 at 4.5 m/s)
    SteerKP             0.3 -> 0.85      buys the hold stiffness at speed back after the LAF change (the
                                         operator's "loose"); the Ms <= 2 bound at >22 m/s is SteerKP <= 0.92
                                         at LAF 14 (Ms ~ 1/(1 - Kp_norm) with the 0.20-0.24 s dead time)
    AccordTorqueKi      0.15 -> 0.30     the live integral gain is Ki*(1 + lsf/Kp): 3x lower than flown at
                                         4.5 m/s (the wind-up band), 0.6x at speed; the FF now carries what the
                                         integrator's 38 % share was carrying
    KeepLearnedLatAccelOffset True -> False   the learner's offset is a restored cache (liveValid 0 % on route 70),
                                         -0.07 m/s^2; the larger +0.41 m/s^2 term in the command-vs-f gap is ROLL
                                         compensation (a persistent +2.4 deg estimated roll) that no toggle touches
    SteerDelay          0.2 (pinned)     tau_eq 0.19-0.34 s supports 0.20-0.22; not a lever worth a drive

Usage (from anywhere; Python = the bin_decompile conda env, invoked as `python`):
    python tools/make_galaxy_toggle_config.py            # writes the six files under analysis-2020accord/reference/
    python tools/make_galaxy_toggle_config.py --decode <file.json>   # prints a Galaxy backup's contents
"""
import base64
import datetime as _dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REF = os.path.join(KIT, "analysis-2020accord", "reference")

XOR_KEY = "s8#pL3*Xj!aZ@dWq"          # starpilot/system/the_galaxy/utilities.py, verbatim
FORMAT, VERSION = "starpilot-toggle-backup", 1

# ------------------------------------------------------------------------------------------------
# THE TWO CONFIGS.  Edit here and re-run; nothing else carries these numbers.
# ------------------------------------------------------------------------------------------------
TORQUE_MODE = {
    # the switch
    "AccordRatePlantFF": False,
    # the tune (all four PROVISIONAL until the first drive's identification)
    "SteerKP": 0.3,
    "AccordTorqueKi": 0.15,
    "SteerFriction": 0.0,
    "SteerLatAccel": 6.0,
    # pins -- already the operator's values on 2026-09-10 and on route 6f; restated so the file is
    # self-sufficient and the rlog's initData.params reads unambiguously
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "KeepLearnedLatAccelOffset": True,
    "AccordTurnFFTaper": False,
}

# the installed rate-servo tune, exactly as the 2026-09-10 backup and route 6f's initData carry it
RATE_SERVO_REVERT = {
    "AccordRatePlantFF": True,
    "SteerKP": 0.9,
    "AccordTorqueKi": 0.3,
    "SteerFriction": 0.01,
    "SteerLatAccel": 6.0,
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "KeepLearnedLatAccelOffset": True,
    "AccordTurnFFTaper": False,
}

# REV 2 -- the retune from the first V293 drive (route 70).  REQUIRES the fork at or after Dom 66cf4454a
# (the re-identified HONDA_ACCORD_EPS_G_V / K_V tables); on the old tables AccordRatePlantFF True under-holds
# x2.1 above 12 m/s.  Every value is a plain existing param; the scorer reads this file's decoded copy.
TORQUE_MODE_R2 = {
    "AccordRatePlantFF": True,
    "AccordEpsSpringScale": 1.0,
    "AccordEpsGainScale": 1.0,
    "AccordFFRateGain": 0.5,
    "SteerFriction": 0.011,
    "SteerLatAccel": 14.0,
    "SteerKP": 0.85,
    "AccordTorqueKi": 0.3,
    "KeepLearnedLatAccelOffset": False,
    "SteerDelay": 0.2,
    "UseAutoSteerDelay": False,
    # pins, as rev 1
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "AccordTurnFFTaper": False,
}

# REV 3 -- from the second V293 drive (route 71, rev 2 flown).  REQUIRES the fork at or after the 2026-09-14
# commit that adds the five Accord* keys below (hold map, hysteresis friction FF, 100 Hz rate loop, error notch,
# reference filter) -- on an older fork those keys are unknown to the params library and silently read their
# defaults, which are the same values, but the CODE that consumes them is absent, so the drive would be rev 2
# with SteerFriction 0 and Ki 0.6.  Attribute from initData.GitCommit.  Design: accord-eps-torque-mod
# docs/handoffs/2026-09/HANDOFF-2026-09-14-v293-rev3-*.md.
TORQUE_MODE_R3 = {
    "AccordRatePlantFF": True,
    "AccordHoldMap": True,            # measured saturating hold map (code) instead of the linear k/G tables
    "AccordEpsSpringScale": 1.0,
    "AccordEpsGainScale": 1.0,
    "AccordFFRateGain": 0.5,
    "AccordFrictionHyst": 0.015,      # static-friction feedforward (hysteresis on the desired angle)
    "SteerFriction": 0.0,             # the error relay OFF: it limit-cycled the 2 Hz steering mode at 2.34 Hz on route 71
    "AccordRateLoopGain": 0.0006,     # 100 Hz rate loop, torque per deg/s, tapered above 12 m/s
    "AccordErrorNotchQ": 1.0,         # notch on the P/I error at the mode frequency (1.0-2.1 Hz by speed)
    "AccordRefFilter": 0.12,          # 2 x 0.12 s reference shaping on the setpoint
    "SteerLatAccel": 14.0,
    "SteerKP": 0.85,
    "AccordTorqueKi": 0.6,            # 0.3 -> 0.6: the 'loose' recovery time on straights halves; margins unchanged
    "KeepLearnedLatAccelOffset": False,
    "SteerDelay": 0.2,
    "UseAutoSteerDelay": False,
    # pins, as rev 1 / rev 2
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "AccordTurnFFTaper": False,
}

# REV 3 -> REV 2 revert: the same keys back at their rev-2 values (the five new keys go to their OFF values,
# which is also what the old code path does when the keys are absent).
TORQUE_MODE_R3_REVERT_TO_R2 = dict(TORQUE_MODE_R2, **{
    "AccordHoldMap": False, "AccordFrictionHyst": 0.0, "AccordRateLoopGain": 0.0,
    "AccordErrorNotchQ": 0.0, "AccordRefFilter": 0.0,
})

# REV 4 -- from the third V293 session (routes 72 + 73, rev 3 flown, 2026-09-14).  REQUIRES the fork at or after the
# 2026-09-14 rev-4 commit (AccordTorqueKiHigh + the stock-sync fix + the relay gate).  What the two drives measured:
#   * route 72 (rev 3 exactly as written): the hold feedforward supplied 68-76 % of the torque at 8-30 m/s and the
#     P/I loop (Kp 0.85, Ki 0.6 through LAF 14) took ~2 s to make up the rest -> tracking 0.74-0.80 of the planner
#     at 0.2 Hz, 0.5 s lag = the operator's "loose".  The map's error is route-dependent (crown / wind / speed law:
#     x1.1-1.25 on routes 70/71, x1.3-1.7 on 72/73 at 4-12 deg), so the INTEGRAL gain, not the map, must absorb it.
#   * route 73 ran with SteerFriction = 0.212 (the stock value, back-filled by the fork's stock-param sync because
#     an explicit 0.0 counted as "unset"): a ~10x-Kp relay that tracked 2.5x better (rms 0.04-0.05 m/s^2) but
#     chattered at 4-4.7 Hz and put 21 % of hard-turn frames at the Honda rate cap = "jerky on hard turns".
# Design (kit v293r4_design.py, the identified plant): Ki 2.5 from 18 m/s cuts the 2 s residual of a 0.03-torque
# bias from 0.11-0.12 to 0.005-0.013 m/s^2 with Ms unchanged (1.75); Ki must stay 0.6 below 8 m/s (the lsf already
# multiplies it x7 there; 2.5 rings the 1 Hz mode).  Kp stays 0.85: 1.1 buys 6 % and costs PM 103 -> 62 deg at 26 m/s;
# 1.6 gives Ms 4.  UseAutoSteerDelay follows the operator's own 2026-09-14 choice (liveDelay read 0.274 s).
TORQUE_MODE_R4 = dict(TORQUE_MODE_R3, **{
    "AccordTorqueKiHigh": 2.5,        # integral gain from 18 m/s (AccordTorqueKi 0.6 below 8 m/s, linear between)
    "SteerFriction": 0.0,             # unchanged; the fork now keeps an explicit 0.0 AND ignores the relay under the hysteresis FF
    "UseAutoSteerDelay": True,        # the operator turned live delay learning on (routes 72/73: 0.274 s)
})

# REV 4 -> REV 3 revert: the new key off (flat Ki 0.6), everything else the rev-3 values.
TORQUE_MODE_R4_REVERT_TO_R3 = dict(TORQUE_MODE_R3, **{"AccordTorqueKiHigh": 0.0})

# REV 5 (2026-09-15, after route 75 = the real rev-4 drive): the DISTURBANCE OBSERVER replaces the integrator as the
# thing that takes out the hold-map / crown / friction residual.  Route 75 read: tracking gain 0.97-0.98 at every speed
# (rev 4 fixed the 0.74-0.80 of rev 3) but the planner error is still 20-30 % of the signal, 50-70 % of it below 0.3 Hz
# and a further 17-34 % in 0.3-1 Hz -- the band a P loop through a 60 ms round trip cannot stiffen (static stiffness
# 1 + Kp_t/k = 1.7) and the integrator only reaches at its own 0.2-0.5 Hz corner (the catch-up the operator feels).
# The observer estimates the unmodelled torque from the measured wheel state and the controller's own delayed output,
# w = hold(angle) + b(v) rate + J acc - u(t - 0.06), two poles at AccordDobHz, added to the feedforward.  Its loop
# closes through the MODEL MISMATCH only, so the corner sits above the integrator's without reference-path lag.
# Design (kit v293r5_design*.py, five plant worlds incl. b x0.15-8, hold x1.5, delays x1.5, J x1.5): planner-step
# overshoot 0.40-0.61 -> 0.16-0.25, hard-turn hold error -60..-80 %, 0.03-torque disturbance residual at 1 s
# 0.04-0.10 -> 0.00-0.03 m/s^2; cost = up to +45 % 1.6-3 Hz wheel-rate energy in hard turns IF the plant is the lightly
# damped one (the observer's model damping is the fork's 1/G(v); above its corner that mismatch de-damps the mode), which
# is why the corner is 0.6 Hz not 0.8 and Kp 1.0 not 1.2.  Ki drops to 0.3 flat (no schedule): the observer does its job
# 3-5x faster and without the variable delay the operator asked to avoid.  Kv 1e-3 (was 6e-4) damps 1-2.8 Hz.
# A model-PREDICTED rate damper was tested and REJECTED (divergent under damping mismatch at 26 m/s).
TORQUE_MODE_R5 = dict(TORQUE_MODE_R4, **{
    "AccordDobHz": 0.6,               # disturbance observer corner (Hz); 0 = off (rev-4 behaviour)
    "SteerKP": 1.0,                   # 0.85 -> 1.0 (1.2 buys little more and costs mode energy)
    "AccordTorqueKi": 0.3,            # 0.6 -> 0.3 flat: the observer replaces the slow integral action
    "AccordTorqueKiHigh": 0.0,        # schedule OFF (was 2.5 from 18 m/s)
    "AccordRateLoopGain": 0.001,      # 6e-4 -> 1e-3 torque per deg/s of wheel-rate error (tapered above 12 m/s as before)
})

# REV 5 -> REV 4 revert: observer off, rev-4 gains back.
TORQUE_MODE_R5_REVERT_TO_R4 = dict(TORQUE_MODE_R4, **{"AccordDobHz": 0.0})

# keys added to the fork AFTER the 2026-09-10 backup (so the typo guard cannot see them): the rev-3 set,
# declared in common/params_keys.h by the 2026-09-14 fork commit.  Galaxy's restore writes them like any other key.
NEW_KEYS_SINCE_BACKUP = {"AccordHoldMap", "AccordFrictionHyst", "AccordRateLoopGain", "AccordErrorNotchQ", "AccordRefFilter",
                         "AccordTorqueKiHigh", "AccordDobHz"}

FILES = (
    ("toggle-config_V293_torque_mode", TORQUE_MODE),
    ("toggle-config_V293_torque_mode_r2", TORQUE_MODE_R2),
    ("toggle-config_V293_torque_mode_r3", TORQUE_MODE_R3),
    ("toggle-config_V293_torque_mode_r3_REVERT_to_r2", TORQUE_MODE_R3_REVERT_TO_R2),
    ("toggle-config_V293_torque_mode_r4", TORQUE_MODE_R4),
    ("toggle-config_V293_torque_mode_r4_REVERT_to_r3", TORQUE_MODE_R4_REVERT_TO_R3),
    ("toggle-config_V293_torque_mode_r5", TORQUE_MODE_R5),
    ("toggle-config_V293_torque_mode_r5_REVERT_to_r4", TORQUE_MODE_R5_REVERT_TO_R4),
    ("toggle-config_V282_rate_servo_REVERT", RATE_SERVO_REVERT),
)


def xor_encrypt_decrypt(data, key):
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))


def encode_parameters(params_dict):
    return base64.b64encode(xor_encrypt_decrypt(json.dumps(params_dict), XOR_KEY).encode("utf-8")).decode("utf-8")


def decode_parameters(encoded):
    return json.loads(xor_encrypt_decrypt(base64.b64decode(encoded.encode("utf-8")).decode("utf-8"), XOR_KEY))


def galaxy_file(values):
    return {
        "format": FORMAT,
        "version": VERSION,
        "createdAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "settingsCount": len(values),
        "data": encode_parameters(values),
    }


def positive_control():
    """the codec must reproduce the operator's own backup -> its decoded copy, byte for byte in content."""
    enc = json.load(open(os.path.join(REF, "toggle-backup_latest_20260910.json"), encoding="utf-8"))
    dec = json.load(open(os.path.join(REF, "toggle-backup_latest_20260910.decoded.json"), encoding="utf-8"))
    got = decode_parameters(enc["data"])
    assert got == dec, "codec does not reproduce the operator's 2026-09-10 backup"
    assert enc["format"] == FORMAT and enc["version"] == VERSION and enc["settingsCount"] == len(dec)
    # and the reverse direction: re-encoding the decoded copy must decode back to itself
    assert decode_parameters(encode_parameters(dec)) == dec
    return dec


def main(argv):
    if len(argv) >= 2 and argv[1] == "--decode":
        d = json.load(open(argv[2], encoding="utf-8"))
        print(json.dumps(decode_parameters(d["data"]), indent=1, sort_keys=True))
        return 0
    backup = positive_control()
    print("codec positive control: OK (526-key 2026-09-10 backup round-trips)")
    for stem, values in FILES:
        for k in values:
            assert k in backup or k in NEW_KEYS_SINCE_BACKUP, "%s is not a key the operator's backup carries -- typo?" % k
        out = galaxy_file(values)
        assert decode_parameters(out["data"]) == values
        p = os.path.join(REF, stem + ".json")
        json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
        json.dump(values, open(os.path.join(REF, stem + ".decoded.json"), "w", encoding="utf-8"), indent=2)
        changed = {k: (backup.get(k, "<new key>"), v) for k, v in values.items() if backup.get(k) != v}
        print("wrote %s.json (+ .decoded.json): %d keys; differs from the 2026-09-10 backup in %d: %s"
              % (stem, len(values), len(changed), changed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
