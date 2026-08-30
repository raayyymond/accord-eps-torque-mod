# -*- coding: utf-8 -*-
"""
FIND TOOLS THAT chdir AWAY AND THEN USE A KIT-ROOT-RELATIVE PATH.

Five probe decoders shared this defect: the PATH BOOTSTRAP block ends with `os.chdir(str(_d))`, which
moves to the package root (rlog-tools/ or analysis-2020accord/), and the tool then opens something
like 'analysis-2020accord/_scratch/cache/...', which is relative to the KIT ROOT.  The two do not
agree, so the tool reports a plausible "no cache" and exits 1.

** That failure mode is worse than a crash **, because it reads as a missing capture rather than a
bug -- which is exactly how it survived: a drive would have been flown and the probe unreadable.

The same bootstrap block is copy-pasted across score/, probe/, decode/ and verify/, so any tool that
combines it with a kit-root-relative literal has the bug latent.  This finds them.
"""
import io
import os
import re

ROOTS = ('rlog-tools', 'analysis-2020accord', 'tools', 'flashing-2020accord')
# literals that only resolve from the KIT ROOT
KITREL = re.compile(r"['\"](analysis-2020accord|rlog-tools|docs|memory|flashing-2020accord)/")
CHDIR = re.compile(r'os\.chdir\(')

bad, checked, chdirs = [], 0, 0
for root in ROOTS:
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('_scratch', 'archive', '__pycache__',
                                                        'cereal', 'ghidra_project')]
        for f in files:
            if not f.endswith('.py'):
                continue
            p = os.path.join(dirpath, f)
            try:
                s = io.open(p, encoding='utf-8').read()
            except Exception:
                continue
            if os.path.abspath(p) == os.path.abspath(__file__):
                continue          # the scanner matches its own regex literals
            checked += 1
            if not CHDIR.search(s):
                continue
            chdirs += 1
            # a chdir to an ABSOLUTE literal is fine -- it pins the cwd deliberately
            abs_chdir = re.search(r"os\.chdir\(\s*['\"][A-Za-z]:", s)
            hits = sorted(set(m.group(1) for m in KITREL.finditer(s)))
            if hits and not abs_chdir:
                bad.append((p, hits))

print('=' * 96)
print('  chdir / kit-root-relative-path MISMATCH SWEEP')
print('=' * 96)
print('  %d python files scanned, %d call os.chdir' % (checked, chdirs))
print()
if bad:
    for p, hits in bad:
        print('  ** SUSPECT ** %s' % p)
        print('        chdirs away, and references: %s' % ', '.join(hits))
else:
    print('  CLEAN -- no tool chdirs to a package root and then uses a kit-root-relative path.')
print()
print('  A chdir to an ABSOLUTE path is not flagged -- that pins the cwd on purpose.')

import sys
sys.exit(1 if bad else 0)
