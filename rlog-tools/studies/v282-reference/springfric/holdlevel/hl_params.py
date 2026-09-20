"""STREAM holdlevel, step 1: re-read initData INDEPENDENTLY from the rlogs.

Does NOT use the fsr cache's params_json (which filters keys to a PK prefix list and keeps only the
FIRST initData seen across the whole route).  Here: every segment's initData, every param entry,
plus version / gitCommit / gitBranch / dirty, so that (a) a mid-route param change is visible and
(b) the fork build is pinned per route.

out/hl_params.json
"""
import sys, glob, os, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
FSR = HERE.parents[1] / 'fill_straightroad'
sys.path.insert(0, str(FSR))
from forkparse import read_messages

RL = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs"
ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]
# params we care about; ALL keys are captured but these get printed
WATCH = ["AccordHoldLevel", "AccordHoldMap", "AccordFrictionHyst", "AccordFrictionHystBand",
         "AccordDobHz", "AccordRatePlantFF", "AccordFFRateGain", "AccordRateLoopGain",
         "SteerFriction", "SteerFrictionStock", "SteerLatAccel", "SteerKP", "AccordTorqueKi",
         "AccordTorqueKiHigh", "AccordEpsSpringScale", "AccordEpsGainScale", "AccordRefFilter",
         "SteerRatio", "SteerDelay", "AccordDither", "AccordDitherGate", "AccordErrorNotchQ",
         "ForceTorqueController", "AccordTurnFFTaper", "AccordVariableSteerRatio", "SteerOffset",
         "LatSmoothSeconds", "AdvancedLateralTune", "HondaLateralPidKiScale", "HondaLateralPidKpScale"]


def seg(p):
    return int(os.path.basename(p).split("--")[2])


def read_init(path):
    """first initData in this segment file, or None"""
    n = 0
    for e in read_messages(path):
        if e.which() == "initData":
            d = e.initData
            P = {}
            try:
                for x in d.params.entries:
                    P[x.key] = bytes(x.value).decode(errors="replace")[:200]
            except Exception as ex:
                P['__err__'] = str(ex)
            meta = {}
            for f in ("version", "gitCommit", "gitBranch", "gitRemote", "dirty", "deviceType",
                      "gitCommitDate", "osVersion"):
                try:
                    meta[f] = str(getattr(d, f))
                except Exception:
                    pass
            return meta, P
        n += 1
        if n > 400:      # initData is at the head of a segment; bail out fast if not
            return None
    return None


if __name__ == '__main__':
    R = {}
    for rk in ROUTES:
        segs = sorted(glob.glob(f"{RL}/75604b0a432fdc89_{rk}--*--rlog.zst"), key=seg)
        want = [segs[0], segs[len(segs) // 2], segs[-1]]
        R[rk] = {}
        for p in want:
            s = seg(p)
            got = read_init(p)
            if got is None:
                print(f"  {rk} seg {s}: NO initData in first 400 msgs", flush=True)
                continue
            meta, P = got
            R[rk][s] = dict(meta=meta, params=P)
            print(f"  {rk} seg {s}: {len(P)} params, commit {meta.get('gitCommit','?')[:12]} "
                  f"branch {meta.get('gitBranch','?')} dirty {meta.get('dirty','?')}", flush=True)
    json.dump(R, open(HERE / 'out' / 'hl_params.json', 'w'), indent=1)

    print()
    print("=" * 110)
    hdr = 'param'.ljust(26) + ''.join(r[4:8].ljust(14) for r in ROUTES)
    print(hdr)
    for k in WATCH:
        row = k.ljust(26)
        for rk in ROUTES:
            segs = sorted(R[rk])
            vals = {R[rk][s]['params'].get(k, '--') for s in segs}
            v = list(vals)[0] if len(vals) == 1 else 'VARIES:' + '/'.join(sorted(vals))
            row += str(v)[:13].ljust(14)
        print(row)
    print()
    for f in ("gitCommit", "gitBranch", "dirty", "version"):
        row = f.ljust(26)
        for rk in ROUTES:
            vals = {R[rk][s]['meta'].get(f, '?') for s in sorted(R[rk])}
            v = list(vals)[0] if len(vals) == 1 else 'VARIES'
            row += str(v)[:13].ljust(14)
        print(row)
    print()
    print("keys present per route (count), and keys unique to one route:")
    allk = {}
    for rk in ROUTES:
        ks = set()
        for s in R[rk]:
            ks |= set(R[rk][s]['params'])
        allk[rk] = ks
        print(f"  {rk}: {len(ks)} keys")
    union = set().union(*allk.values())
    for k in sorted(union):
        have = [rk[4:8] for rk in ROUTES if k in allk[rk]]
        if len(have) < len(ROUTES):
            print(f"  MISSING from some: {k:34s} present on {have}")
