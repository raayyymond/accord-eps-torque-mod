# -*- coding: utf-8 -*-
"""Build the IMPORTABLE A/B toggle config for the attribution drive.

MEASURED: rev 6.4 delivers 1.275 (0.15-0.30 Hz) and 1.333 (0.30-0.60 Hz) of the model's demand on
the highway. Goal is 1.000. Rev 5 measured 1.092 / 1.118 on the same metric.
NOT ESTABLISHED: which term causes it. The flown-config diff narrows it to AccordHoldLevel,
AccordFrictionHystBand, AccordRefFilter (0.12->0.06) or the rev 6 code changes.

AccordHoldLevel is a TOGGLE. One drive with it OFF settles in a single route what no amount of
further log analysis can. This writes that config -- ONE toggle changed from what flew, nothing else.

Positive control (codec) runs first, exactly as encode_r64.py does; nothing is written if it fails.
"""
import base64, json, os, sys

KIT = '/home/user/accord-eps-torque-mod'
REF = os.path.join(KIT, 'analysis-2020accord', 'reference')
SC  = os.path.dirname(os.path.abspath(__file__))
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1

def xor(d, k): return "".join(chr(ord(c) ^ ord(k[i % len(k)])) for i, c in enumerate(d))
def enc(d): return base64.b64encode(xor(json.dumps(d), XOR_KEY).encode()).decode()
def dec(e): return json.loads(xor(base64.b64decode(e.encode()).decode(), XOR_KEY))

# ---------------- POSITIVE CONTROL: round-trip every existing reference pair, both directions
pairs = 0
for f in sorted(os.listdir(REF)):
    if not f.endswith('.decoded.json'): continue
    ep = os.path.join(REF, f.replace('.decoded.json', '.json'))
    if not os.path.exists(ep): continue
    e = json.load(open(ep, encoding='utf-8')); d = json.load(open(os.path.join(REF, f), encoding='utf-8'))
    assert dec(e['data']) == d, 'decode mismatch on %s' % f
    assert dec(enc(d)) == d, 're-encode mismatch on %s' % f
    assert e['format'] == FORMAT and e['version'] == VERSION and e['settingsCount'] == len(d), f
    pairs += 1
print(f"POSITIVE CONTROL: codec reproduced {pairs} existing encoded/decoded reference pairs, both directions.")
if pairs == 0:
    sys.exit("no reference pair to validate against -- refusing to emit an unverified config")

# ---------------- the config that FLEW on 6c/6d, read from the rev 6.4 decoded config
flown = json.load(open(os.path.join(SC, 'toggle-config_V293_torque_mode_r64.decoded.json'), encoding='utf-8'))

# cross-check it against what the car actually logged in initData (ground truth)
LOGGED = {  # from routes 6c and 6d initData params
    'AccordRatePlantFF': True, 'AccordHoldMap': True, 'AccordHoldLevel': True,
    'AccordFrictionHystBand': True, 'AccordEpsSpringScale': 1.0, 'AccordEpsGainScale': 1.0,
    'AccordFFRateGain': 0.5, 'AccordFrictionHyst': 0.015, 'AccordRateLoopGain': 0.001,
    'AccordErrorNotchQ': 1.0, 'AccordRefFilter': 0.06, 'AccordTorqueKi': 0.3,
    'AccordTorqueKiHigh': 0.0, 'AccordDobHz': 0.6, 'AccordTurnFFTaper': False,
    'AccordDither': 0.0, 'AccordDitherGate': True, 'LaneCentering': True,
    'LaneChangeTurnGate': True, 'SteerLatAccel': 14.0,
}
bad = {k: (flown.get(k), v) for k, v in LOGGED.items() if k in flown and flown[k] != v}
print(f"CROSS-CHECK vs what the car logged: {len(LOGGED)} keys checked, {len(bad)} mismatches" +
      (f" -> {bad}" if bad else " (config on disk matches the flight)"))

# ---------------- ARM A: exactly what flew (the control)
armA = dict(flown)
# ---------------- ARM B: ONE toggle changed
armB = dict(flown); armB['AccordHoldLevel'] = False

diff = {k: (armA.get(k), armB.get(k)) for k in set(armA) | set(armB) if armA.get(k) != armB.get(k)}
print(f"\nARM A (control) = the flown rev 6.4 config, {len(armA)} settings")
print(f"ARM B (test)    = {len(armB)} settings; differences from A: {diff}")
assert len(diff) == 1, 'more than one toggle changed -- that would not be an attribution test'

for name, cfg in [('r64_ARM-A_asflown', armA), ('r64_ARM-B_holdlevel-off', armB)]:
    payload = {"format": FORMAT, "version": VERSION, "settingsCount": len(cfg), "data": enc(cfg)}
    p = os.path.join(SC, f'toggle-config_V293_{name}.json')
    json.dump(payload, open(p, 'w', encoding='utf-8'), indent=1)
    json.dump(cfg, open(p.replace('.json', '.decoded.json'), 'w', encoding='utf-8'), indent=1)
    # verify what we just wrote decodes back to what we meant
    back = dec(json.load(open(p, encoding='utf-8'))['data'])
    assert back == cfg, 'written file does not decode back to the intended config'
    print(f"  wrote {os.path.basename(p)}  ({len(cfg)} settings, verified by decoding the written file)")
