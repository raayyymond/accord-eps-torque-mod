# -*- coding: utf-8 -*-
"""Attribution: read the flown fork params from EACH route's own initData, for all 16 cached routes.

The V282 reference routes (64/65/6c--2bc842dbac) and r72/r73 were never dumped; ffgain_ceiling/dump_params.py
covered only the torque revs.  ANALYSIS ONLY.  usage: python params_all.py
"""
import io, json, os, re, sys
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
          "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000070--717f5a7866", "00000071--f2c9d073a3", "00000072--8001fc3048",
          "00000073--79fd149dd8", "00000074--2bf17ca67d", "00000075--6c8687d5bd",
          "00000076--d0b7ea7e4d"]

WANT = ["AccordRatePlantFF", "AccordFFRateGain", "AccordHoldMap", "AccordHoldLevel",
        "AccordFrictionHyst", "AccordFrictionHystBand", "AccordRateLoopGain", "AccordDobHz",
        "AccordEpsGainScale", "AccordEpsSpringScale", "AccordVariableSteerRatio",
        "AccordTorqueKi", "AccordTorqueKiHigh", "AccordRefFilter", "AccordJerkLpHz",
        "AccordCurvatureLead", "AccordCurvatureLeadGain", "AccordTurnFFTaper",
        "SteerRatio", "CustomSteerRatio", "SteerLatAccel", "CustomLatAccel", "SteerFriction",
        "CustomFriction", "SteerKP", "CustomSteerKP", "ForceAutoTune", "ForceTorqueController",
        "LateralControlMode", "NNFF", "GitCommit", "GitBranch"]


def read_params(route, seg):
    path = os.path.join(RLOGS, "75604b0a432fdc89_%s--%d--rlog.zst" % (route, seg))
    if not os.path.exists(path):
        return None, "no seg %d" % seg
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    try:
        it = clog.Event.read_multiple_bytes(data)
    except Exception as e:
        return None, "read fail %s" % e
    n = 0
    while n < 6000:
        n += 1
        try:
            evt = next(it)
        except Exception:
            break
        try:
            if evt.which() != "initData":
                continue
        except Exception:
            continue
        out = {}
        for ent in evt.initData.params.entries:
            try:
                v = bytes(ent.value).decode("utf-8", "replace")
            except Exception:
                v = "<bin>"
            out[ent.key] = v[:90]
        return out, None
    return None, "no initData in first %d events" % n


ALL = {}
for route in ROUTES:
    p = err = None
    for s in (0, 1, 2, 3):
        p, err = read_params(route, s)
        if p is not None:
            break
    if p is None:
        print("%-24s FAILED: %s" % (route, err), flush=True)
        continue
    ALL[route] = {k: p.get(k, "ABSENT") for k in WANT}
    print("\n=== %s  (%d params) ===" % (route, len(p)), flush=True)
    for k in WANT:
        print("   %-26s %s" % (k, p.get(k, "ABSENT")), flush=True)

with open(os.path.join(HERE, "params_all.json"), "w") as fh:
    json.dump(ALL, fh, indent=1, sort_keys=True)
print("\nwrote params_all.json for %d routes" % len(ALL), flush=True)
