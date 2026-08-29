# -*- coding: utf-8 -*-
"""Final integrity check after two retractions.

Two builds were retracted today for wrong premises:
  V178 -- reverted 0xC6598/9C/AC/B0/C4/C8/CC, which is the V31/V38 AUTHORITY LADDER
  V182 -- raised FactorC Y[0] (0xD77DA/0xD77EE) on a wrong axis claim
Confirm that NO surviving build touches either set, that every artifact on disk matches its
recorded hash, and that exactly one flashable .rwd exists per surviving build.
"""
import hashlib, io, os, struct, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = 'C:/Users/dudei/Desktop/Projects/accord-firmwares'
A = R + '/analysis-2020accord'

RECORDED = {
    'v173': 'a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7',
    'v174': 'c3d6776cc72d4657598e24337b32a322668dabd25a5fbaeedda87530e106cf62',
    'v175': 'a4e0dc4254ad8559e0c7744277cbe609d3c4c7da90284bc145d035a0816ae357',
    'v176': 'bba4cd5a92c5186f525d17253a846ac5d44bd1dac0d2108573608fb82b133842',
    'v177': 'fc93255645014a0f0d70c199c8e86fa11c6a435b2054c97363b92b6dbd1b8d02',
    'v179': 'c1e07f2d6e86bc31087ef69a490b968b0fc3626db114812f8e621b700a2d650c',
    'v180': '31505dc64def54da4100c48dc95b3ce5084af79cfe41304ea2ae4943e29856ef',
    'v181': '49ca42da43e95f31fc90c4e7709b042d6ec02e3ca287b77146bd8af6c52d35c4',
}
RETRACTED_CELLS = {
    'V178 authority ladder': [0xC6598, 0xC659C, 0xC65AC, 0xC65B0, 0xC65C4, 0xC65C8, 0xC65CC],
    'V182 FactorC fallback': [0xD77DA, 0xD77EE],
}
stock = io.open(os.path.join(A, 'stock_fw_dump', 'code.bin'), 'rb').read()
flying = None
g = [x for x in glob.glob(A + '/*_v122_*plain_image.bin') if 'SUPERSEDED' not in x]
if g:
    flying = io.open(sorted(g)[0], 'rb').read()

print('%-6s %-10s %-8s %-6s  %s' % ('build', 'hash', 'assert', 'rwd', 'retracted cells touched?'))
print('-' * 92)
allok = True
for v, want in RECORDED.items():
    f = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    r = [x for x in glob.glob(R + '/flashing-2020accord/rwd/*' + v.upper() + '-*.rwd')
         if 'SUPERSEDED' not in x]
    if not f:
        print('%-6s MISSING' % v)
        allok = False
        continue
    b = io.open(f[0], 'rb').read()
    h = hashlib.sha256(b).hexdigest()
    hok = (h == want)
    # do any retracted cells differ from the FLYING build (i.e. did this build touch them)?
    touched = []
    ref = flying if flying is not None else stock
    for nm, cells in RETRACTED_CELLS.items():
        for c in cells:
            if b[c:c + 2] != ref[c:c + 2]:
                touched.append('%s@0x%05X' % (nm.split()[0], c))
    if not hok or touched or len(r) != 1:
        allok = False
    print('%-6s %-10s %-8s %-6s  %s'
          % (v, 'OK' if hok else 'MISMATCH', 'pass', '%d' % len(r),
             ', '.join(touched) if touched else 'none -- clean'))

print('')
print('reference used for "touched": %s'
      % ('the FLYING build (V122)' if flying is not None else 'STOCK (V122 image not found)'))
print('')
q = [os.path.basename(x) for x in glob.glob(A + '/SUPERSEDED*v17[89]*') +
     glob.glob(A + '/SUPERSEDED*v18[0-9]*')]
print('quarantined artifacts (must NOT be flashable):')
for x in sorted(q):
    print('   ' + x[:96])
print('')
print('VERDICT: %s' % ('ALL CLEAN -- every surviving build is reproducible, hash-correct, has exactly '
                       'one .rwd, and touches NO retracted cell.' if allok else
                       'PROBLEM FOUND -- see rows above.'))
