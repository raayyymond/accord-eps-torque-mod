"""ADVERSARY A1 - read each route's FLOWN params from its own initData (fork schema), not from labels.

Purpose: find CONFOUNDS between the V282 reference group and the torque-mode group that would make the
|H| comparison non-commensurable. Anything that touches the INPUT channel (what the model asks for) is
fatal for a transfer-function comparison; anything that touches only the output is a build difference,
which is the thing being measured.

usage: python a1_params.py
"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY / "fill_straightroad"))
import forkparse  # noqa: E402

RLOGS = STUDY.parents[2] / "analysis-2020accord" / "rlogs"

ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]

# keys that can move the INPUT channel (model -> logged desiredCurvature) = fatal confounds
INPUT_KEYS = ["LaneCentering", "LaneCenterOffset", "LaneCenteringE2eAuthority", "LaneCenteringPauseOnSignal",
              "LaneChangeSmoothing", "LaneChangeTurnGate", "CurvatureHold", "TurnHold", "TurnDesires",
              "MaxDesiredAcceleration", "TurnSpeedController", "CurveSpeedController", "DynamicPathPlanning",
              "ModelLaboratory", "ModelSelection", "LateralManeuver", "AlwaysOnLateral"]
# keys that move the OUTPUT side only = the thing under test, not a confound
OUT_KEYS = ["SteerFriction", "SteerRatio", "SteerKP", "SteerKI", "LateralAccelFactor", "SteerLatAccel",
            "Accord", "ForceTorqueController", "TorqueDeadzone", "LatAccelOffset", "SteerMax"]


def params_of(route):
    p = RLOGS / f"75604b0a432fdc89_{route}--0--rlog.zst"
    for e in forkparse.read_messages(str(p)):
        if e.which() != "initData":
            continue
        d = e.initData
        out = {"gitCommit": str(d.gitCommit)[:9], "gitBranch": str(d.gitBranch),
               "dirty": bool(d.dirty), "version": str(d.version)}
        pr = {}
        for ent in d.params.entries:
            k = str(ent.key)
            try:
                v = bytes(ent.value)
            except Exception:
                continue
            if len(v) <= 64:
                try:
                    pr[k] = v.decode("utf8", "replace")
                except Exception:
                    pr[k] = repr(v)
        out["params"] = pr
        return out
    return None


if __name__ == "__main__":
    allp = {}
    for r in ROUTES:
        try:
            allp[r] = params_of(r)
            print(f"{r}  commit {allp[r]['gitCommit']} branch {allp[r]['gitBranch']} dirty={allp[r]['dirty']} "
                  f"nparams {len(allp[r]['params'])}", flush=True)
        except Exception as ex:
            print(f"{r}  FAILED {ex}", flush=True)
    (HERE / "a1_params.json").write_text(json.dumps(allp, indent=1))

    # report every key whose value is not identical across all routes, split input-side vs output-side
    keys = sorted({k for v in allp.values() if v for k in v["params"]})
    def bucket(k):
        if any(s.lower() in k.lower() for s in INPUT_KEYS):
            return "INPUT"
        if any(s.lower() in k.lower() for s in OUT_KEYS):
            return "OUTPUT"
        return "other"
    print("\n=== keys that DIFFER across routes (INPUT-side first) ===")
    for want in ("INPUT", "OUTPUT"):
        for k in keys:
            if bucket(k) != want:
                continue
            vals = {r: (allp[r]["params"].get(k) if allp[r] else None) for r in ROUTES}
            if len(set(map(str, vals.values()))) > 1:
                print(f"[{want}] {k}")
                for r in ROUTES:
                    print(f"        {r}  {vals[r]!r}")
