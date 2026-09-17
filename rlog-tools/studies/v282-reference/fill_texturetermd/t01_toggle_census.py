"""t01: per-route toggle census from initData (segment 0) of every torque-mode route. Also records gitCommit.
Params are stored as raw strings in initData.params; values that look like binary are hex-trimmed."""
import sys, glob, json, os
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
from rlog_parse import read_messages
R = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs/'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd/out/'
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd', '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
KEYS = ['SteerFriction', 'SteerKP', 'SteerKI', 'SteerLatAccel', 'SteerRatio', 'AccordRateLoopGain', 'AccordDobHz', 'AccordHoldLevel',
        'AccordFrictionHyst', 'AccordFrictionHystBand', 'AccordRefFilter', 'AccordDither', 'AccordDitherGate', 'AccordErrorNotchQ',
        'AccordTorqueKi', 'AccordTorqueKiHigh', 'AccordFFRateGain', 'AccordEpsGainScale', 'AccordEpsSpringScale', 'AccordHoldMap',
        'AccordRatePlantFF', 'ForceTorqueController', 'AccordTurnFFTaper']
res = {}
for rk in ROUTES:
    p = sorted(glob.glob(R + f'75604b0a432fdc89_{rk}--0--rlog.zst'))[0]
    out = {}
    for n, evt in enumerate(read_messages(p)):
        try:
            w = evt.which()
        except Exception:
            continue
        if w == 'initData':
            d = evt.initData
            out['__gitCommit'] = str(d.gitCommit)
            for e in d.params.entries:
                k = e.key if isinstance(e.key, str) else e.key.decode('utf8', 'ignore')
                v = e.value
                try:
                    v = v.decode('utf8') if isinstance(v, (bytes, bytearray)) else str(v)
                except Exception:
                    v = '<bin>'
                if len(v) < 80:
                    out[k] = v
            break
        if n > 20000:
            break
    res[rk] = out
    accord = sorted(k for k in out if 'ccord' in k)
    print(rk, out.get('__gitCommit', '?')[:10], 'accord keys:', len(accord))
allk = sorted(set(KEYS) | set(k for o in res.values() for k in o if 'ccord' in k or k.startswith('Steer')))
print(f"{'param':32s}" + ''.join(f"{r[:4]+r[-4:]:>14s}" for r in ROUTES))
for k in allk:
    vals = [res[r].get(k, '<absent>') for r in ROUTES]
    print(f"{k[:32]:32s}" + ''.join(f"{v[:13]:>14s}" for v in vals) + ('   *' if len(set(vals)) > 1 else ''))
json.dump({r: {k: res[r].get(k, '<absent>') for k in allk + ['__gitCommit']} for r in ROUTES}, open(OUT + 't01_toggles.json', 'w'), indent=1)
